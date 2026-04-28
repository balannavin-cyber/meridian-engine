#!/usr/bin/env python3
"""
fix_enh46a_signal_alerts.py

Adds tradable-signal alerting to merdian_pipeline_alert_daemon.py.

Session 9 (2026-04-26) closure of Item 4 of TD-022 follow-up parking lot.
Daemon currently alerts only on infrastructure failures (script_execution_log
exit reasons). Operator confirmed empirically zero awareness of any of the
1,017 BUY_PE rows + 1 BUY_CE row produced over 21 trade days.

What this patch does
--------------------
1. Adds a second polling path: signal_snapshots WHERE action!='DO_NOTHING'
   AND trade_allowed=true.
2. Adds a separate watermark (last_alerted_signal_ts) so the signal poll
   is decoupled from the script-log poll.
3. Adds format_signal_alert() with distinct heading.
4. Hooks into run_cycle() so both paths run every poll cycle.
5. Reuses existing send_telegram(), state file, log file, env vars.

Per CLAUDE.md:
- File written, not python -c.
- ast.parse() validates output before write.
- Backup preserved at .pre_enh46a.bak.
- Idempotent: re-running detects already-patched and no-ops.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\merdian_pipeline_alert_daemon.py")
BACKUP = TARGET.with_suffix(TARGET.suffix + ".pre_enh46a.bak")


# ── Replacement 1: add SIGNAL_ALERT_ACTIONS constant near the existing ALERT_EXIT_REASONS ──
OLD_CONSTANTS = '''ALERT_EXIT_REASONS = (
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
DAEMON_SCRIPT_NAME = "merdian_pipeline_alert_daemon"'''

NEW_CONSTANTS = '''ALERT_EXIT_REASONS = (
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

# ENH-46-A: tradable-signal alerts. signal_snapshots rows matching
# action IN SIGNAL_ALERT_ACTIONS AND trade_allowed=true generate a
# Telegram alert distinct from the infrastructure-alert path.
SIGNAL_ALERT_ACTIONS = ("BUY_CE", "BUY_PE")
SIGNAL_LOOKBACK_MINUTES = 15
SIGNAL_MAX_BATCH = 20

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
DAEMON_SCRIPT_NAME = "merdian_pipeline_alert_daemon"'''


# ── Replacement 2: extend init_watermark_if_missing to also init signal watermark ──
OLD_INIT_WATERMARK_TAIL = '''    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state.setdefault("alerts_sent_total", 0)
    state.setdefault("heartbeats_sent_total", 0)
    save_state(state)
    return state'''

NEW_INIT_WATERMARK_TAIL = '''    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state.setdefault("alerts_sent_total", 0)
    state.setdefault("heartbeats_sent_total", 0)
    state.setdefault("signal_alerts_sent_total", 0)

    # ENH-46-A: signal-table watermark. Initialise to MAX(ts) at startup so
    # we don't blast historical PE rows on first run; matches script-log init.
    if not state.get("last_alerted_signal_ts"):
        try:
            res = (
                sb.table("signal_snapshots")
                .select("ts")
                .order("ts", desc=True)
                .limit(1)
                .execute()
            )
            srows = res.data or []
            if srows:
                state["last_alerted_signal_ts"] = srows[0]["ts"]
                log(f"[INIT] signal watermark set to {state['last_alerted_signal_ts']}")
            else:
                state["last_alerted_signal_ts"] = datetime.now(timezone.utc).isoformat()
                log("[INIT] signal_snapshots empty; signal watermark set to now")
        except Exception as e:
            state["last_alerted_signal_ts"] = datetime.now(timezone.utc).isoformat()
            log(f"[INIT] signal watermark fetch failed ({e}); fallback to now")

    save_state(state)
    return state'''


# ── Replacement 3: add fetch_new_tradable_signals + format_signal_alert + run_signal_cycle ──
# Insert after fetch_new_finishes() and before run_cycle().
OLD_BEFORE_RUN_CYCLE = '''# --- Cycle -------------------------------------------------------------------

def run_cycle(state: dict) -> int:'''

NEW_BEFORE_RUN_CYCLE = '''# --- ENH-46-A: signal alerting ----------------------------------------------

def fetch_new_tradable_signals(watermark_iso: str) -> list[dict]:
    """Fetch signal_snapshots rows newer than watermark with action!=DO_NOTHING
    AND trade_allowed=true. Bounded by SIGNAL_LOOKBACK_MINUTES on cold start."""
    cutoff_iso = (
        datetime.now(timezone.utc) - timedelta(minutes=SIGNAL_LOOKBACK_MINUTES)
    ).isoformat()
    after = max(watermark_iso, cutoff_iso)
    res = (
        sb.table("signal_snapshots")
        .select(
            "id,ts,symbol,action,trade_allowed,confidence_score,"
            "direction_bias,gamma_regime,breadth_regime,spot,"
            "atm_strike,dte,expiry_date"
        )
        .gt("ts", after)
        .in_("action", list(SIGNAL_ALERT_ACTIONS))
        .eq("trade_allowed", True)
        .order("ts")
        .limit(SIGNAL_MAX_BATCH * 4)
        .execute()
    )
    return res.data or []


def format_signal_alert(row: dict) -> str:
    sym = row.get("symbol", "?")
    action = row.get("action", "?")
    ts_str = _truncate(row.get("ts"), 19).replace("T", " ")
    conf = row.get("confidence_score")
    spot = row.get("spot")
    atm = row.get("atm_strike")
    dte = row.get("dte")
    expiry = row.get("expiry_date")
    gamma = row.get("gamma_regime")
    breadth = row.get("breadth_regime")
    direction = row.get("direction_bias")

    parts = [
        f"📈 MERDIAN Trade Signal: {sym} {action}",
        f"Time: {ts_str}",
    ]
    if spot is not None:
        parts.append(f"Spot: {spot}")
    if atm is not None:
        parts.append(f"ATM: {atm}    DTE: {dte}    Expiry: {expiry}")
    if conf is not None:
        parts.append(f"Confidence: {conf}")
    if direction:
        parts.append(f"Direction: {direction}")
    regime_bits = []
    if gamma:
        regime_bits.append(f"gamma={gamma}")
    if breadth:
        regime_bits.append(f"breadth={breadth}")
    if regime_bits:
        parts.append("Regime: " + "  ".join(regime_bits))
    parts.append("trade_allowed=TRUE")
    return "\\n".join(parts)


def run_signal_cycle(state: dict) -> int:
    """Poll signal_snapshots for new tradable rows and alert. Returns count
    of Telegram alerts sent this cycle. Fully decoupled from script-log poll."""
    watermark = state.get("last_alerted_signal_ts") or datetime.now(timezone.utc).isoformat()
    try:
        rows = fetch_new_tradable_signals(watermark)
    except Exception as e:
        log(f"[SIG ERR] fetch failed: {e}")
        return 0

    if not rows:
        return 0

    alerts_sent = 0
    new_watermark = watermark

    for row in rows:
        ts_val = row.get("ts")
        if not ts_val:
            continue
        if ts_val > new_watermark:
            new_watermark = ts_val
        if alerts_sent >= SIGNAL_MAX_BATCH:
            log(f"[SIG WARN] batch cap {SIGNAL_MAX_BATCH} hit; remaining rows alert next cycle")
            new_watermark = ts_val
            break
        msg = format_signal_alert(row)
        if send_telegram(msg):
            alerts_sent += 1
            log(f"[SIG ALERT] {row.get('symbol')} {row.get('action')} ts={ts_val}")
        else:
            log(f"[SIG RETRY-NEXT] {row.get('symbol')} {row.get('action')} ts={ts_val} (Telegram failed)")
            return alerts_sent

    state["last_alerted_signal_ts"] = new_watermark
    if alerts_sent > 0:
        state["signal_alerts_sent_total"] = state.get("signal_alerts_sent_total", 0) + alerts_sent
        state["last_signal_alert_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return alerts_sent


# --- Cycle -------------------------------------------------------------------

def run_cycle(state: dict) -> int:'''


# ── Replacement 4: hook run_signal_cycle into the daemon main loop ──
OLD_DAEMON_LOOP = '''    while True:
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
            log(f"[ERR] cycle: {e}\\n{traceback.format_exc()}")
        time.sleep(POLL_SECS)'''

NEW_DAEMON_LOOP = '''    while True:
        try:
            n = run_cycle(state)
            if n > 0:
                log(f"sent {n} alert(s)")
            sn = run_signal_cycle(state)
            if sn > 0:
                log(f"sent {sn} signal alert(s)")
            if time.time() - last_heartbeat >= HEARTBEAT_SECS:
                if write_heartbeat_row(state):
                    last_heartbeat = time.time()
        except KeyboardInterrupt:
            log("daemon stopped (KeyboardInterrupt)")
            return 0
        except Exception as e:
            log(f"[ERR] cycle: {e}\\n{traceback.format_exc()}")
        time.sleep(POLL_SECS)'''


# ── Replacement 5: also hook into --once mode for easy testing ──
OLD_ONCE = '''def cmd_once() -> int:
    state = init_watermark_if_missing(load_state())
    n = run_cycle(state)
    log(f"[ONCE] alerts sent: {n}")
    return 0'''

NEW_ONCE = '''def cmd_once() -> int:
    state = init_watermark_if_missing(load_state())
    n = run_cycle(state)
    log(f"[ONCE] infra alerts sent: {n}")
    sn = run_signal_cycle(state)
    log(f"[ONCE] signal alerts sent: {sn}")
    return 0'''


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] Target not found: {TARGET}", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotency guard
    if "ENH-46-A" in src or "fetch_new_tradable_signals" in src:
        print(f"[SKIP] {TARGET.name} already contains ENH-46-A markers. No-op.")
        return 0

    replacements = [
        ("Replacement 1 (constants)",          OLD_CONSTANTS,          NEW_CONSTANTS),
        ("Replacement 2 (init_watermark)",     OLD_INIT_WATERMARK_TAIL, NEW_INIT_WATERMARK_TAIL),
        ("Replacement 3 (signal-cycle funcs)", OLD_BEFORE_RUN_CYCLE,   NEW_BEFORE_RUN_CYCLE),
        ("Replacement 4 (daemon loop)",        OLD_DAEMON_LOOP,        NEW_DAEMON_LOOP),
        ("Replacement 5 (cmd_once)",           OLD_ONCE,               NEW_ONCE),
    ]

    new_src = src
    for label, old, new in replacements:
        if old not in new_src:
            print(f"[FAIL] {label}: anchor not found verbatim.", file=sys.stderr)
            print(f"       First 200 chars expected:", file=sys.stderr)
            print(f"       {repr(old[:200])}", file=sys.stderr)
            return 2
        new_src = new_src.replace(old, new, 1)
        print(f"[OK] {label} applied.")

    # Sanity: each marker appears once
    expected_markers = {
        "fetch_new_tradable_signals": 2,   # def + call inside run_signal_cycle
        "def run_signal_cycle":       1,
        "def format_signal_alert":    1,
        "SIGNAL_ALERT_ACTIONS":       3,   # comment ref + tuple def + .in_(...) usage
        "ENH-46-A":                   3,   # comment in constants + init_watermark + section header
    }
    for marker, expected_count in expected_markers.items():
        actual = new_src.count(marker)
        if actual != expected_count:
            print(f"[FAIL] marker '{marker}' count = {actual}, expected {expected_count}",
                  file=sys.stderr)
            return 3

    # ast.parse validation
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        print(f"[FAIL] ast.parse() rejected patched source: {e}", file=sys.stderr)
        return 4

    # Backup, then write
    if not BACKUP.exists():
        BACKUP.write_text(src, encoding="utf-8")
        print(f"[OK] Backup saved: {BACKUP}")
    else:
        print(f"[OK] Backup already exists: {BACKUP} (not overwriting)")

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"[OK] Patched: {TARGET}")
    print(f"     Original size: {len(src):,} bytes")
    print(f"     Patched size:  {len(new_src):,} bytes")
    print(f"     Delta:         +{len(new_src) - len(src):,} bytes")
    print()
    print("Next steps:")
    print(f"  1. python -m py_compile {TARGET}")
    print(f"  2. python {TARGET} --test    # confirms Telegram still works")
    print(f"  3. python {TARGET} --once    # runs both poll paths once")
    print(f"  4. Restart the daemon process (per merdian_pm.py / Task Scheduler)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
