#!/usr/bin/env python3
"""
fix_enh46a_init_bug.py

Bug fix for fix_enh46a_signal_alerts.py.

Original ENH-46-A patch put the signal-watermark init INSIDE
init_watermark_if_missing() AFTER the early-return-on-existing-state
guard. Result: when the daemon restarted with a pre-existing state.json
(holding only the OLD script-log watermark), the function returned early
and the new ENH-46-A signal-watermark + counter were never initialised.

This patch:
1. Removes the ENH-46-A block from inside init_watermark_if_missing()
   (where it was unreachable on warm starts).
2. Adds a new function init_signal_watermark_if_missing() that runs
   independently and is called from all three command paths
   (cmd_test, cmd_once, cmd_daemon).
3. Idempotent. Re-running is a no-op.

Discovered via post-deploy verification 2026-04-26 14:11 IST after
synthetic signal_snapshots row failed to trigger a Telegram alert.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

TARGET = Path(r"C:\GammaEnginePython\merdian_pipeline_alert_daemon.py")
BACKUP = TARGET.with_suffix(TARGET.suffix + ".pre_enh46a_initbug.bak")


# ── Replacement 1: remove the broken ENH-46-A block from init_watermark_if_missing ──
OLD_INIT_BROKEN = '''    state["started_at"] = datetime.now(timezone.utc).isoformat()
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

NEW_INIT_FIXED = '''    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state.setdefault("alerts_sent_total", 0)
    state.setdefault("heartbeats_sent_total", 0)
    save_state(state)
    return state


def init_signal_watermark_if_missing(state: dict) -> dict:
    """ENH-46-A: independent of script-log watermark. Runs on every command
    path so warm-start daemons (with existing state.json holding only the
    script-log watermark) still pick up signal-alerting on first poll.

    Initialises last_alerted_signal_ts to MAX(ts) in signal_snapshots so we
    don't blast historical PE rows on first run.
    """
    state.setdefault("signal_alerts_sent_total", 0)
    if state.get("last_alerted_signal_ts"):
        return state
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


# ── Replacement 2: cmd_once must call signal-watermark init too ──
OLD_CMD_ONCE = '''def cmd_once() -> int:
    state = init_watermark_if_missing(load_state())
    n = run_cycle(state)
    log(f"[ONCE] infra alerts sent: {n}")
    sn = run_signal_cycle(state)
    log(f"[ONCE] signal alerts sent: {sn}")
    return 0'''

NEW_CMD_ONCE = '''def cmd_once() -> int:
    state = init_watermark_if_missing(load_state())
    state = init_signal_watermark_if_missing(state)
    n = run_cycle(state)
    log(f"[ONCE] infra alerts sent: {n}")
    sn = run_signal_cycle(state)
    log(f"[ONCE] signal alerts sent: {sn}")
    return 0'''


# ── Replacement 3: cmd_daemon must call signal-watermark init too ──
OLD_CMD_DAEMON_HEAD = '''def cmd_daemon() -> int:
    log(f"daemon starting (poll={POLL_SECS}s, heartbeat={HEARTBEAT_SECS}s, host={HOST})")
    state = init_watermark_if_missing(load_state())
    log(f"watermark: {state.get('last_alerted_finished_at')}")'''

NEW_CMD_DAEMON_HEAD = '''def cmd_daemon() -> int:
    log(f"daemon starting (poll={POLL_SECS}s, heartbeat={HEARTBEAT_SECS}s, host={HOST})")
    state = init_watermark_if_missing(load_state())
    state = init_signal_watermark_if_missing(state)
    log(f"watermark: {state.get('last_alerted_finished_at')}")
    log(f"signal watermark: {state.get('last_alerted_signal_ts')}")'''


def main() -> int:
    if not TARGET.exists():
        print(f"[FAIL] Target not found: {TARGET}", file=sys.stderr)
        return 1

    src = TARGET.read_text(encoding="utf-8")

    # Idempotency: if the new init function already exists, no-op.
    if "def init_signal_watermark_if_missing" in src:
        print(f"[SKIP] {TARGET.name} already contains init_signal_watermark_if_missing. No-op.")
        return 0

    replacements = [
        ("Replacement 1 (split init function)", OLD_INIT_BROKEN, NEW_INIT_FIXED),
        ("Replacement 2 (cmd_once init call)", OLD_CMD_ONCE,    NEW_CMD_ONCE),
        ("Replacement 3 (cmd_daemon init call)", OLD_CMD_DAEMON_HEAD, NEW_CMD_DAEMON_HEAD),
    ]

    new_src = src
    for label, old, new in replacements:
        if old not in new_src:
            print(f"[FAIL] {label}: anchor not found verbatim.", file=sys.stderr)
            print(f"       First 300 chars expected:", file=sys.stderr)
            print(f"       {repr(old[:300])}", file=sys.stderr)
            return 2
        new_src = new_src.replace(old, new, 1)
        print(f"[OK] {label} applied.")

    # Sanity checks
    assert new_src.count("def init_signal_watermark_if_missing") == 1
    assert new_src.count("init_signal_watermark_if_missing(state)") == 2  # called from cmd_once + cmd_daemon
    assert new_src.count('state.setdefault("signal_alerts_sent_total", 0)') == 1

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

    TARGET.write_text(new_src, encoding="utf-8")
    print(f"[OK] Patched: {TARGET}")
    print(f"     Original size: {len(src):,} bytes")
    print(f"     Patched size:  {len(new_src):,} bytes")
    print()
    print("Next steps:")
    print(f"  1. python -m py_compile {TARGET}")
    print(f"  2. Kill running daemon (PID currently 33108) and restart")
    print(f"  3. Check state.json contains last_alerted_signal_ts")
    print(f"  4. Insert synthetic signal_snapshots row, wait 90s, expect Telegram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
