#!/usr/bin/env python3
"""
MERDIAN AWS Shadow Runner
Session-controlled AWS shadow path aligned to local V17D1 / V17E guard model.

AWS remains SHADOW ONLY.
Local Windows remains the live signal path.

Design:
- Uses trading_calendar as the single session authority
- Enforces:
    Guard 1: trading_calendar is_open
    Guard 2: regular-session state only
    Guard 3: breadth coverage >= 95%
    Guard 4: latest LTP snapshot age <= 20 minutes
- Keeps AWS shadow on the same analytics path:
    breadth -> WCB -> ingest -> gamma -> volatility -> momentum -> market state -> live signal
- Sends minimum Telegram alert on runner FATAL crash
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from trading_calendar import (
    MissingSessionConfigError,
    TradingCalendarError,
    current_session_state,
    get_today_session_config,
    now_ist,
)

IST = timezone(timedelta(hours=5, minutes=30))

SYMBOLS = ["NIFTY", "SENSEX"]
WCB_SYMBOLS = ["NIFTY", "SENSEX"]

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
RUNTIME_DIR = BASE_DIR / "runtime"
LOCK_FILE = RUNTIME_DIR / "aws_shadow_runner.lock"
PID_FILE = RUNTIME_DIR / "aws_shadow_runner.pid"
STATE_FILE = RUNTIME_DIR / "aws_shadow_runner_state.json"
LOG_FILE = LOG_DIR / "aws_shadow_runner.log"

TIMEOUT_BREADTH_SECONDS = 300
TIMEOUT_WCB_SECONDS = 300
TIMEOUT_SINGLE_STEP_SECONDS = 300

PYTHON_BIN = sys.executable or "python3"

MIN_COVERAGE_TO_PROCEED = 95.0
MAX_ALLOWED_LTP_AGE_MINUTES = 20

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}\b"
)

COVERAGE_RE = re.compile(r"Coverage:\s*([0-9]+(?:\.[0-9]+)?)%")
ROWS_UPSERTED_RE = re.compile(r"Rows upserted:\s*([0-9]+)")

_SHUTDOWN = False


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    ts = now_ist().strftime("%Y-%m-%d %H:%M:%S %Z")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _send_telegram(message: str) -> tuple[bool, str]:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram env vars missing"

    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }
    url = base_url + "?" + urllib.parse.urlencode(payload)

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            body = response.read().decode("utf-8", errors="ignore")
        return True, body
    except Exception as exc:
        return False, str(exc)


def send_fatal_telegram(error_text: str) -> None:
    now_local = now_ist().strftime("%Y-%m-%d %H:%M:%S IST")
    message = "\n".join(
        [
            "MERDIAN AWS SHADOW RUNNER FATAL",
            f"Time: {now_local}",
            f"Host path: {BASE_DIR}",
            f"Error: {error_text}",
        ]
    )
    ok, detail = _send_telegram(message)
    if ok:
        log("Telegram crash alert sent.")
    else:
        log(f"Telegram crash alert failed: {detail}")


def acquire_lock() -> None:
    if LOCK_FILE.exists():
        try:
            existing_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except Exception:
            existing_pid = None

        if existing_pid:
            try:
                os.kill(existing_pid, 0)
                raise RuntimeError(
                    f"Lock file exists and process appears alive (pid={existing_pid}). "
                    "Refusing to start duplicate AWS shadow runner."
                )
            except OSError:
                log(f"Stale lock detected for pid={existing_pid}; removing stale lock.")
                LOCK_FILE.unlink(missing_ok=True)
        else:
            log("Malformed lock file detected; removing.")
            LOCK_FILE.unlink(missing_ok=True)

    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def release_lock() -> None:
    LOCK_FILE.unlink(missing_ok=True)
    PID_FILE.unlink(missing_ok=True)


def update_state(status: str, extra: Optional[dict] = None) -> None:
    payload = {
        "component": "aws_shadow_runner",
        "pid": os.getpid(),
        "status": status,
        "ts_ist": now_ist().isoformat(),
    }
    if extra:
        payload.update(extra)
    write_json(STATE_FILE, payload)


@dataclass
class StepResult:
    ok: bool
    returncode: int
    duration_sec: float
    stdout_tail: str
    stderr_tail: str
    stdout_full: str
    stderr_full: str


def tail_text(text: str, max_chars: int = 2000) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def run_step(
    args: list[str],
    timeout_seconds: int,
    step_name: str,
    symbol: Optional[str] = None,
) -> StepResult:
    start = time.time()
    cmd_display = " ".join(args)

    if symbol:
        log(f"START {step_name} [{symbol}] :: {cmd_display}")
    else:
        log(f"START {step_name} :: {cmd_display}")

    try:
        proc = subprocess.run(
            args,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
        duration = time.time() - start
        stdout_full = proc.stdout or ""
        stderr_full = proc.stderr or ""
        stdout_tail = tail_text(stdout_full)
        stderr_tail = tail_text(stderr_full)

        if proc.returncode == 0:
            if symbol:
                log(f"OK    {step_name} [{symbol}] in {duration:.1f}s")
            else:
                log(f"OK    {step_name} in {duration:.1f}s")
            if stdout_tail:
                log(f"{step_name} stdout tail: {stdout_tail}")
            return StepResult(
                True,
                proc.returncode,
                duration,
                stdout_tail,
                stderr_tail,
                stdout_full,
                stderr_full,
            )

        if symbol:
            log(f"FAIL  {step_name} [{symbol}] rc={proc.returncode} in {duration:.1f}s")
        else:
            log(f"FAIL  {step_name} rc={proc.returncode} in {duration:.1f}s")
        if stdout_tail:
            log(f"{step_name} stdout tail: {stdout_tail}")
        if stderr_tail:
            log(f"{step_name} stderr tail: {stderr_tail}")
        return StepResult(
            False,
            proc.returncode,
            duration,
            stdout_tail,
            stderr_tail,
            stdout_full,
            stderr_full,
        )

    except subprocess.TimeoutExpired as exc:
        duration = time.time() - start
        stdout_full = exc.stdout or ""
        stderr_full = exc.stderr or ""
        stdout_tail = tail_text(stdout_full)
        stderr_tail = tail_text(stderr_full)
        if symbol:
            log(f"TIMEOUT {step_name} [{symbol}] after {duration:.1f}s")
        else:
            log(f"TIMEOUT {step_name} after {duration:.1f}s")
        if stdout_tail:
            log(f"{step_name} stdout tail before timeout: {stdout_tail}")
        if stderr_tail:
            log(f"{step_name} stderr tail before timeout: {stderr_tail}")
        return StepResult(
            False,
            124,
            duration,
            stdout_tail,
            stderr_tail,
            stdout_full,
            stderr_full,
        )


def require_env(keys: list[str]) -> None:
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Use canonical AWS env load: set -a ; . ./.env ; set +a"
        )


def extract_run_id(stdout_text: str) -> Optional[str]:
    match = re.search(
        r"Run ID:\s*([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        stdout_text or "",
    )
    return match.group(1) if match else None


def get_supabase_headers() -> dict[str, str]:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


def supabase_select(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    url = f"{base}/rest/v1/{path}"
    resp = requests.get(url, headers=get_supabase_headers(), params=params, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Supabase SELECT failed ({resp.status_code}) on {path}: {resp.text}")
    data = resp.json()
    return data if isinstance(data, list) else []


def fetch_latest_equity_intraday_ts() -> Optional[datetime]:
    rows = supabase_select(
        "equity_intraday_last",
        {
            "select": "ts",
            "order": "ts.desc",
            "limit": "1",
        },
    )
    if not rows:
        return None
    return parse_ts_utc(rows[0].get("ts"))


def extract_breadth_coverage(stdout_text: str) -> Optional[float]:
    match = COVERAGE_RE.search(stdout_text or "")
    if not match:
        return None
    try:
        return float(match.group(1))
    except Exception:
        return None


def extract_rows_upserted(stdout_text: str) -> Optional[int]:
    match = ROWS_UPSERTED_RE.search(stdout_text or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def latest_ltp_is_stale(ts_value: Optional[datetime]) -> bool:
    if ts_value is None:
        return True
    age = utc_now() - ts_value
    return age > timedelta(minutes=MAX_ALLOWED_LTP_AGE_MINUTES)


def guard_trading_calendar() -> tuple[bool, Optional[Any], str]:
    current = now_ist()
    try:
        cfg = get_today_session_config(current)
    except MissingSessionConfigError as exc:
        return False, None, f"Trading calendar coverage missing for today: {exc}"
    except TradingCalendarError as exc:
        return False, None, f"Trading calendar configuration error: {exc}"

    if not cfg.is_open:
        return False, cfg, f"Trading calendar marks {cfg.date} as CLOSED."

    return True, cfg, "OPEN"


def guard_session_state() -> tuple[bool, str]:
    current = now_ist()
    try:
        state = current_session_state(current)
    except (MissingSessionConfigError, TradingCalendarError) as exc:
        return False, f"Could not resolve session state: {exc}"

    if state != "REGULAR_SESSION":
        return False, f"Current session state is {state}, not REGULAR_SESSION."
    return True, state


def guard_breadth_coverage(breadth_stdout: str) -> tuple[bool, str, Optional[float], Optional[int]]:
    coverage_pct = extract_breadth_coverage(breadth_stdout)
    rows_upserted = extract_rows_upserted(breadth_stdout)

    if rows_upserted is not None and rows_upserted <= 0:
        return False, f"Rows upserted = {rows_upserted}", coverage_pct, rows_upserted

    if coverage_pct is None:
        return False, "Could not parse coverage from ingest_breadth_intraday_local.py output", None, rows_upserted

    if coverage_pct < MIN_COVERAGE_TO_PROCEED:
        return False, f"Coverage {coverage_pct:.2f}% below minimum {MIN_COVERAGE_TO_PROCEED:.2f}%", coverage_pct, rows_upserted

    return True, "OK", coverage_pct, rows_upserted


def guard_ltp_staleness() -> tuple[bool, str, Optional[str]]:
    latest_ts = fetch_latest_equity_intraday_ts()
    if latest_ltp_is_stale(latest_ts):
        age_text = "unknown"
        if latest_ts is not None:
            age_minutes = (utc_now() - latest_ts).total_seconds() / 60.0
            age_text = f"{age_minutes:.1f} minutes"
        return False, f"Latest equity_intraday_last snapshot is stale (age={age_text})", latest_ts.isoformat() if latest_ts else None

    return True, "OK", latest_ts.isoformat() if latest_ts else None


def run_wcb_refresh() -> bool:
    for symbol in WCB_SYMBOLS:
        if _SHUTDOWN:
            log(f"Shutdown requested before build_wcb_snapshot_local.py [{symbol}]")
            return False

        result = run_step(
            [PYTHON_BIN, "build_wcb_snapshot_local.py", symbol],
            TIMEOUT_WCB_SECONDS,
            "build_wcb_snapshot_local.py",
            symbol=symbol,
        )
        if not result.ok:
            return False

    return True


def run_symbol_pipeline(symbol: str) -> bool:
    ingest_result = run_step(
        [PYTHON_BIN, "ingest_option_chain_local.py", symbol],
        TIMEOUT_SINGLE_STEP_SECONDS,
        "ingest_option_chain_local.py",
        symbol=symbol,
    )
    if not ingest_result.ok:
        return False

    run_id = extract_run_id(ingest_result.stdout_full)
    if not run_id:
        log(f"FAIL  Could not extract run_id from ingest output for {symbol}")
        return False

    log(f"Resolved run_id for {symbol}: {run_id}")

    gamma_result = run_step(
        [PYTHON_BIN, "compute_gamma_metrics_local.py", run_id, symbol],
        TIMEOUT_SINGLE_STEP_SECONDS,
        "compute_gamma_metrics_local.py",
        symbol=symbol,
    )
    if not gamma_result.ok:
        return False

    volatility_result = run_step(
        [PYTHON_BIN, "compute_volatility_metrics_local.py", run_id],
        TIMEOUT_SINGLE_STEP_SECONDS,
        "compute_volatility_metrics_local.py",
        symbol=symbol,
    )
    if not volatility_result.ok:
        return False

    remaining_sequence = [
        ("build_momentum_features_local.py", [PYTHON_BIN, "build_momentum_features_local.py", symbol]),
        ("build_market_state_snapshot_local.py", [PYTHON_BIN, "build_market_state_snapshot_local.py", symbol]),
        ("build_trade_signal_local.py", [PYTHON_BIN, "build_trade_signal_local.py", symbol]),
    ]

    for step_name, args in remaining_sequence:
        if _SHUTDOWN:
            log(f"Shutdown requested before {step_name} [{symbol}]")
            return False
        result = run_step(args, TIMEOUT_SINGLE_STEP_SECONDS, step_name, symbol=symbol)
        if not result.ok:
            return False

    return True



def write_cycle_status_to_supabase(cycle_ok: bool, breadth_coverage, per_symbol: dict, last_error: str = "") -> None:
    try:
        import json as _json
        supabase_url = os.environ.get("SUPABASE_URL", "").strip()
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not supabase_url or not supabase_key:
            return
        payload_value = _json.dumps({
            "cycle_ok": cycle_ok,
            "breadth_coverage": breadth_coverage,
            "per_symbol": per_symbol,
            "last_error": last_error,
            "cycle_time_ist": now_ist().strftime("%Y-%m-%d %H:%M:%S IST"),
        })
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        payload = {
            "config_key": "aws_shadow_cycle_status",
            "config_value": payload_value,
            "updated_at": "now()",
            "updated_by": "aws_shadow_runner",
        }
        requests.post(
            f"{supabase_url}/rest/v1/system_config",
            headers=headers,
            json=payload,
            timeout=10,
        )
    except Exception as e:
        log(f"WARNING: Failed to write cycle status to Supabase (non-fatal): {e}")

def run_cycle() -> bool:
    cycle_start = now_ist()
    log("============================================================")
    log(f"START AWS SHADOW CYCLE @ {cycle_start.isoformat()}")

    update_state("RUNNING", {"cycle_start_ist": cycle_start.isoformat()})

    calendar_ok, cfg, calendar_msg = guard_trading_calendar()
    if not calendar_ok:
        log(f"GUARD 1 STOP: {calendar_msg}")
        update_state(
            "WAITING_FOR_SESSION" if cfg is not None else "ERROR",
            {
                "failed_guard": "trading_calendar",
                "guard_message": calendar_msg,
            },
        )
        return False

    session_ok, session_msg = guard_session_state()
    if not session_ok:
        log(f"GUARD 2 STOP: {session_msg}")
        update_state(
            "WAITING_FOR_SESSION",
            {
                "failed_guard": "session_state",
                "guard_message": session_msg,
            },
        )
        return False

    breadth = run_step(
        [PYTHON_BIN, "ingest_breadth_intraday_local.py"],
        TIMEOUT_BREADTH_SECONDS,
        "ingest_breadth_intraday_local.py",
    )
    if not breadth.ok:
        update_state("ERROR", {"failed_step": "ingest_breadth_intraday_local.py"})
        return False

    coverage_ok, coverage_msg, coverage_pct, rows_upserted = guard_breadth_coverage(breadth.stdout_full)
    if not coverage_ok:
        log(f"GUARD 3 STOP: {coverage_msg}")
        update_state(
            "ERROR",
            {
                "failed_guard": "coverage",
                "guard_message": coverage_msg,
                "coverage_pct": coverage_pct,
                "rows_upserted": rows_upserted,
            },
        )
        return False

    stale_ok, stale_msg, latest_ltp_ts = guard_ltp_staleness()
    if not stale_ok:
        log(f"GUARD 4 STOP: {stale_msg}")
        update_state(
            "ERROR",
            {
                "failed_guard": "staleness",
                "guard_message": stale_msg,
                "latest_equity_intraday_ts": latest_ltp_ts,
            },
        )
        return False

    wcb_ok = run_wcb_refresh()
    if not wcb_ok:
        update_state("ERROR", {"failed_step": "build_wcb_snapshot_local.py"})
        return False

    overall_ok = True
    per_symbol: dict[str, str] = {}

    for symbol in SYMBOLS:
        if _SHUTDOWN:
            log(f"Shutdown requested before pipeline for {symbol}")
            overall_ok = False
            break
        ok = run_symbol_pipeline(symbol)
        per_symbol[symbol] = "OK" if ok else "FAILED"
        overall_ok = overall_ok and ok

    cycle_end = now_ist()
    duration = (cycle_end - cycle_start).total_seconds()

    update_state(
        "IDLE" if overall_ok else "ERROR",
        {
            "cycle_start_ist": cycle_start.isoformat(),
            "cycle_end_ist": cycle_end.isoformat(),
            "cycle_duration_sec": duration,
            "per_symbol": per_symbol,
            "last_cycle_ok": overall_ok,
            "coverage_pct": coverage_pct,
            "rows_upserted": rows_upserted,
            "latest_equity_intraday_ts": latest_ltp_ts,
        },
    )

    if overall_ok:
        log(f"END   AWS SHADOW CYCLE OK in {duration:.1f}s | {per_symbol}")
    else:
        log(f"END   AWS SHADOW CYCLE WITH FAILURES in {duration:.1f}s | {per_symbol}")

    write_cycle_status_to_supabase(
        cycle_ok=overall_ok,
        breadth_coverage=coverage_pct,
        per_symbol=per_symbol,
        last_error="" if overall_ok else f"Cycle failed. per_symbol={per_symbol}",
    )

    return overall_ok


def handle_shutdown(signum, frame) -> None:
    global _SHUTDOWN
    _SHUTDOWN = True
    log(f"Received signal {signum}; graceful shutdown requested.")
    update_state("STOPPING", {"signal": signum})


def main() -> int:
    ensure_dirs()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    require_env(
        [
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
            "DHAN_CLIENT_ID",
            "DHAN_API_TOKEN",
        ]
    )

    acquire_lock()
    try:
        log("AWS shadow runner starting.")
        log("AWS is SHADOW ONLY. Local Windows remains the live signal path.")
        update_state("STARTING")

        while not _SHUTDOWN:
            current = now_ist()

            try:
                cfg = get_today_session_config(current)
            except MissingSessionConfigError as exc:
                log(f"FATAL: Trading calendar coverage missing for today: {exc}")
                update_state("FATAL", {"error": str(exc)})
                return 2
            except TradingCalendarError as exc:
                log(f"FATAL: Trading calendar configuration error: {exc}")
                update_state("FATAL", {"error": str(exc)})
                return 2

            if not cfg.is_open:
                log(f"Trading calendar marks {cfg.date} as CLOSED. Exiting runner.")
                update_state(
                    "CLOSED_DAY",
                    {
                        "trade_date": str(cfg.date),
                        "reason": "trading_calendar is_open = false",
                    },
                )
                return 0

            session_state = current_session_state(current)

            if session_state != "REGULAR_SESSION":
                if current < cfg.open_dt:
                    log(
                        f"Waiting for regular session start. "
                        f"Now={current.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                        f"open_dt={cfg.open_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                        f"state={session_state}"
                    )
                    update_state(
                        "WAITING_FOR_SESSION",
                        {
                            "now_ist": current.isoformat(),
                            "open_dt_ist": cfg.open_dt.isoformat(),
                            "session_state": session_state,
                        },
                    )
                    wait_seconds = min(5.0, max(0.5, (cfg.open_dt - current).total_seconds()))
                    time.sleep(wait_seconds)
                    continue

                log(
                    f"Outside regular session. "
                    f"Now={current.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                    f"close_dt={cfg.close_dt.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
                    f"state={session_state}. Exiting runner cleanly."
                )
                update_state(
                    "STOPPED",
                    {
                        "now_ist": current.isoformat(),
                        "close_dt_ist": cfg.close_dt.isoformat(),
                        "session_state": session_state,
                    },
                )
                return 0

            cycle_ok = run_cycle()

            if _SHUTDOWN:
                break

            boundary = (now_ist().replace(second=0, microsecond=0) + timedelta(minutes=5))
            boundary = boundary.replace(minute=(boundary.minute // 5) * 5)

            log(
                f"Cycle result={'OK' if cycle_ok else 'ERROR'} | "
                f"sleeping until next 5-minute boundary {boundary.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            remaining = max(0.5, (boundary - now_ist()).total_seconds())
            time.sleep(remaining)

        log("AWS shadow runner stopped gracefully.")
        update_state("STOPPED")
        return 0

    finally:
        release_lock()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        error_text = str(exc)
        log(f"FATAL: {error_text}")
        update_state("FATAL", {"error": error_text})
        send_fatal_telegram(error_text)
        release_lock()
        raise
