#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merdian_pipeline_alert_daemon.py — ENH-73 MVP (with self-heartbeat)

Polls public.script_execution_log every N seconds. Sends a Telegram alert
when a script row finishes with a contract violation or hard-failure exit_reason.

Self-heartbeat:
    Every HEARTBEAT_INTERVAL_SECS (600s = 10 min by default), the daemon writes
    a SUCCESS row to script_execution_log under script_name=
    'merdian_pipeline_alert_daemon'. This makes daemon liveness visible from the
    DB / dashboard. If the heartbeat stops appearing, the daemon is down.

    Heartbeat self-rows pass through the alert filter as expected (SUCCESS +
    contract_met=true → not alerted) and only advance the watermark.

Modes:
    --test   send one test Telegram and exit
    --once   run one polling cycle and exit (no heartbeat)
    default  poll forever every POLL_INTERVAL_SECS, with periodic heartbeats

Environment:
    SUPABASE_URL                  required
    SUPABASE_SERVICE_ROLE_KEY     required (or SUPABASE_KEY fallback)
    TELEGRAM_BOT_TOKEN            required
    TELEGRAM_CHAT_ID              required
    PIPELINE_ALERT_POLL_SECS      optional (default 60)
    PIPELINE_ALERT_HEARTBEAT_SECS optional (default 600)

State:
    runtime/pipeline_alert_state.json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from supabase import create_client

# --- Config ------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
STATE_PATH = REPO_ROOT / "runtime" / "pipeline_alert_state.json"
LOG_PATH = REPO_ROOT / "logs" / "pipeline_alert_daemon.log"

DEFAULT_POLL_SECS = 60
DEFAULT_HEARTBEAT_SECS = 600   # 10 min
LOOKBACK_MINUTES = 60
MAX_BATCH = 50

ALERT_EXIT_REASONS = (
    "TOKEN_EXPIRED",
    "DATA_ERROR",
    "DEPENDENCY_MISSING",
    "CRASH",
    "TIMEOUT",
    "SKIPPED_NO_INPUT",
)
SUPPRESS_EXIT_REASONS = (
    "HOLIDAY_GATE",
    "OFF_HOURS",
    "DRY_RUN",
    "RUNNING",
)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
DAEMON_SCRIPT_NAME = "merdian_pipeline_alert_daemon"

# --- Bootstrap ---------------------------------------------------------------

load_dotenv(REPO_ROOT / ".env")

def _need(env_name: str) -> str:
    val = os.environ.get(env_name)
    if not val:
        sys.exit(f"[FATAL] {env_name} not set in environment")
    return val

SUPABASE_URL = _need("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
if not SUPABASE_KEY:
    sys.exit("[FATAL] neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_KEY set")

TG_TOKEN = _need("TELEGRAM_BOT_TOKEN")
TG_CHAT = _need("TELEGRAM_CHAT_ID")

POLL_SECS = int(os.environ.get("PIPELINE_ALERT_POLL_SECS", DEFAULT_POLL_SECS))
HEARTBEAT_SECS = int(os.environ.get("PIPELINE_ALERT_HEARTBEAT_SECS", DEFAULT_HEARTBEAT_SECS))
HOST = socket.gethostname()

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Logging -----------------------------------------------------------------

def log(msg: str) -> None:
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# --- State -------------------------------------------------------------------

def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"[WARN] state file unreadable, starting fresh: {e}")
        return {}

def save_state(state: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        log(f"[WARN] could not save state: {e}")

def init_watermark_if_missing(state: dict) -> dict:
    if state.get("last_alerted_finished_at"):
        return state
    log("[INIT] No watermark — fetching MAX(finished_at) to skip historicals")
    try:
        res = (
            sb.table("script_execution_log")
            .select("finished_at")
            .not_.is_("finished_at", "null")
            .order("finished_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows:
            wm = rows[0]["finished_at"]
            log(f"[INIT] watermark set to {wm}")
            state["last_alerted_finished_at"] = wm
        else:
            wm = datetime.now(timezone.utc).isoformat()
            log(f"[INIT] table empty — watermark set to now ({wm})")
            state["last_alerted_finished_at"] = wm
    except Exception as e:
        wm = datetime.now(timezone.utc).isoformat()
        log(f"[INIT] watermark fetch failed ({e}); fallback to now ({wm})")
        state["last_alerted_finished_at"] = wm
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state.setdefault("alerts_sent_total", 0)
    state.setdefault("heartbeats_sent_total", 0)
    save_state(state)
    return state

# --- Telegram ----------------------------------------------------------------

def send_telegram(message: str) -> bool:
    try:
        url = TELEGRAM_API.format(token=TG_TOKEN)
        r = requests.post(
            url,
            json={"chat_id": TG_CHAT, "text": message, "disable_web_page_preview": True},
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log(f"[TG ERROR] HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        log(f"[TG ERROR] {e}")
        return False

# --- Self-heartbeat ----------------------------------------------------------

def write_heartbeat_row(state: dict) -> bool:
    """Insert a SUCCESS row marking daemon liveness. Returns True on success."""
    try:
        now = datetime.now(timezone.utc)
        row = {
            "invocation_id": str(uuid.uuid4()),
            "script_name": DAEMON_SCRIPT_NAME,
            "host": HOST,
            "trade_date": now.date().isoformat(),
            "started_at": now.isoformat(),
            "finished_at": now.isoformat(),
            "duration_ms": 0,
            "exit_code": 0,
            "exit_reason": "SUCCESS",
            "contract_met": True,
            "expected_writes": {"heartbeat": 1},
            "actual_writes": {"heartbeat": 1},
            "notes": "ENH-73 daemon liveness heartbeat",
        }
        sb.table("script_execution_log").insert(row).execute()
        state["heartbeats_sent_total"] = state.get("heartbeats_sent_total", 0) + 1
        state["last_heartbeat_at"] = now.isoformat()
        save_state(state)
        log(f"[HB] heartbeat written (#{state['heartbeats_sent_total']})")
        return True
    except Exception as e:
        log(f"[HB] heartbeat write failed: {e}")
        return False

# --- Alert criteria + formatting --------------------------------------------

def should_alert(row: dict) -> bool:
    er = row.get("exit_reason")
    cm = row.get("contract_met")
    name = row.get("script_name")
    # Suppress alerts on our own heartbeat rows defensively (they shouldn't
    # match anyway since they're SUCCESS+contract_met=true, but belt+braces)
    if name == DAEMON_SCRIPT_NAME:
        return False
    if er in SUPPRESS_EXIT_REASONS:
        return False
    if er in ALERT_EXIT_REASONS:
        return True
    if er == "SUCCESS" and cm is False:
        return True
    return False

def _truncate(s: Any, n: int) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"

def format_alert(row: dict) -> str:
    name = row.get("script_name", "?")
    started = _truncate(row.get("started_at"), 19).replace("T", " ")
    finished = _truncate(row.get("finished_at"), 19).replace("T", " ")
    er = row.get("exit_reason", "?")
    cm = row.get("contract_met")
    contract_str = "MET" if cm else ("VIOLATED" if cm is False else "n/a")
    err = _truncate(row.get("error_message"), 240)
    expected = row.get("expected_writes") or {}
    actual = row.get("actual_writes") or {}
    sym = row.get("symbol")
    host = row.get("host")

    parts = [
        "🚨 MERDIAN Pipeline Alert",
        f"Script: {name}",
    ]
    if sym:
        parts.append(f"Symbol: {sym}")
    parts.append(f"Started:  {started}")
    parts.append(f"Finished: {finished}")
    parts.append(f"Exit: {er}    Contract: {contract_str}")
    if expected != actual and (expected or actual):
        parts.append(f"Expected: {expected}")
        parts.append(f"Actual:   {actual}")
    if err:
        parts.append(f"Error: {err}")
    if host:
        parts.append(f"Host: {host}")
    return "\n".join(parts)

# --- DB query ----------------------------------------------------------------

def fetch_new_finishes(watermark_iso: str) -> list[dict]:
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)).isoformat()
    after = max(watermark_iso, cutoff_iso)
    res = (
        sb.table("script_execution_log")
        .select(
            "id,invocation_id,script_name,host,symbol,trade_date,"
            "started_at,finished_at,duration_ms,exit_code,exit_reason,"
            "contract_met,expected_writes,actual_writes,error_message,git_sha"
        )
        .gt("finished_at", after)
        .not_.is_("finished_at", "null")
        .order("finished_at")
        .limit(MAX_BATCH * 4)
        .execute()
    )
    return res.data or []

# --- Cycle -------------------------------------------------------------------

def run_cycle(state: dict) -> int:
    watermark = state.get("last_alerted_finished_at") or datetime.now(timezone.utc).isoformat()
    try:
        rows = fetch_new_finishes(watermark)
    except Exception as e:
        log(f"[ERR] fetch failed: {e}")
        return 0

    if not rows:
        return 0

    alerts_sent = 0
    new_watermark = watermark

    for row in rows:
        finished = row.get("finished_at")
        if not finished:
            continue
        if finished > new_watermark:
            new_watermark = finished
        if not should_alert(row):
            continue
        if alerts_sent >= MAX_BATCH:
            log(f"[WARN] batch cap {MAX_BATCH} hit; remaining rows alert next cycle")
            new_watermark = finished
            break
        msg = format_alert(row)
        if send_telegram(msg):
            alerts_sent += 1
            log(f"[ALERT] {row.get('script_name')} :: {row.get('exit_reason')} :: invocation_id={row.get('invocation_id')}")
        else:
            log(f"[RETRY-NEXT] {row.get('script_name')} :: {row.get('invocation_id')} (Telegram failed)")
            return alerts_sent

    state["last_alerted_finished_at"] = new_watermark
    if alerts_sent > 0:
        state["alerts_sent_total"] = state.get("alerts_sent_total", 0) + alerts_sent
        state["last_alert_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return alerts_sent

# --- Mode handlers -----------------------------------------------------------

def cmd_test() -> int:
    msg = (
        "🧪 MERDIAN Pipeline Alert Daemon — test\n"
        f"Time: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Host: {HOST}\n"
        "If you see this, ENH-73 alert delivery is working."
    )
    log("[TEST] sending test Telegram")
    ok = send_telegram(msg)
    log(f"[TEST] result: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

def cmd_once() -> int:
    state = init_watermark_if_missing(load_state())
    n = run_cycle(state)
    log(f"[ONCE] alerts sent: {n}")
    return 0

def cmd_daemon() -> int:
    log(f"daemon starting (poll={POLL_SECS}s, heartbeat={HEARTBEAT_SECS}s, host={HOST})")
    state = init_watermark_if_missing(load_state())
    log(f"watermark: {state.get('last_alerted_finished_at')}")

    # Write startup heartbeat immediately so external monitors see "alive"
    write_heartbeat_row(state)
    last_heartbeat = time.time()

    while True:
        try:
            n = run_cycle(state)
            if n > 0:
                log(f"sent {n} alert(s)")
            if time.time() - last_heartbeat >= HEARTBEAT_SECS:
                if write_heartbeat_row(state):
                    last_heartbeat = time.time()
        except KeyboardInterrupt:
            log("daemon stopped (KeyboardInterrupt)")
            return 0
        except Exception as e:
            log(f"[ERR] cycle: {e}\n{traceback.format_exc()}")
        time.sleep(POLL_SECS)

# --- Main --------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="MERDIAN ENH-73 pipeline alert daemon")
    p.add_argument("--test", action="store_true", help="Send one test Telegram and exit")
    p.add_argument("--once", action="store_true", help="Run one polling cycle and exit (no heartbeat)")
    args = p.parse_args()

    if args.test:
        return cmd_test()
    if args.once:
        return cmd_once()
    return cmd_daemon()

if __name__ == "__main__":
    sys.exit(main())
