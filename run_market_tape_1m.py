from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from trading_calendar import (
    MissingSessionConfigError,
    TradingCalendarError,
    current_session_state,
    get_today_session_config,
    now_ist,
)


# ============================================================================
# MERDIAN - Session-Controlled Market Tape Runner
# ----------------------------------------------------------------------------
# Purpose:
#   Run the market tape layer using one shared session-control authority.
#
# Session events:
#   - 09:08 IST : premarket reference capture (spot + futures + archive)
#   - 09:15 IST : regular market opens
#   - 15:30 IST : close reference satisfied by final regular-session cycle
#   - 16:00 IST : postmarket reference capture (spot + futures + archive)
#
# Regular-session cycle sequence:
#   1. capture_market_spot_snapshot_local.py
#   2. capture_index_futures_snapshot_local.py
#   3. ingest_option_chain_local.py NIFTY ATM_ONLY
#   4. ingest_option_chain_local.py SENSEX ATM_ONLY
#   5. archive_market_tape_history.py
#
# Consolidation:
#   - Separate 1-minute option_execution_price_history path removed
#   - 1-minute options now use canonical option_chain_snapshots via ATM_ONLY mode
# ============================================================================


BASE_DIR = Path(r"C:\GammaEnginePython")
RUNTIME_DIR = BASE_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "market_tape_session_state.json"

SPOT_SCRIPT = str(BASE_DIR / "capture_market_spot_snapshot_local.py")
FUTURES_SCRIPT = str(BASE_DIR / "capture_index_futures_snapshot_local.py")
OPTION_CHAIN_SCRIPT = str(BASE_DIR / "ingest_option_chain_local.py")
ARCHIVE_SCRIPT = str(BASE_DIR / "archive_market_tape_history.py")

PREMARKET_EVENT = "premarket_ref"
OPEN_EVENT = "open_ref"
CLOSE_EVENT = "close_ref"
POSTMARKET_EVENT = "postmarket_ref"

EVENT_STATUS_PENDING = "pending"
EVENT_STATUS_DONE = "done"
EVENT_STATUS_MISSED = "missed"

PREMARKET_WINDOW_SECONDS = 90
POSTMARKET_WINDOW_SECONDS = 90


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def default_state(trade_date: str) -> dict:
    return {
        "trade_date": trade_date,
        "events": {
            PREMARKET_EVENT: {"status": EVENT_STATUS_PENDING, "updated_at": None},
            OPEN_EVENT: {"status": EVENT_STATUS_PENDING, "updated_at": None},
            CLOSE_EVENT: {"status": EVENT_STATUS_PENDING, "updated_at": None},
            POSTMARKET_EVENT: {"status": EVENT_STATUS_PENDING, "updated_at": None},
        },
    }


def normalize_event_value(value) -> dict:
    if isinstance(value, dict):
        status = str(value.get("status", EVENT_STATUS_PENDING))
        updated_at = value.get("updated_at")
        if status not in {EVENT_STATUS_PENDING, EVENT_STATUS_DONE, EVENT_STATUS_MISSED}:
            status = EVENT_STATUS_PENDING
        return {"status": status, "updated_at": updated_at}

    if isinstance(value, bool):
        return {
            "status": EVENT_STATUS_DONE if value else EVENT_STATUS_PENDING,
            "updated_at": None,
        }

    return {"status": EVENT_STATUS_PENDING, "updated_at": None}


def normalize_state(state: dict, trade_date: str) -> dict:
    normalized = default_state(trade_date)

    if not isinstance(state, dict):
        return normalized

    if state.get("trade_date") != trade_date:
        return normalized

    incoming_events = state.get("events", {})
    if not isinstance(incoming_events, dict):
        return normalized

    for key in [PREMARKET_EVENT, OPEN_EVENT, CLOSE_EVENT, POSTMARKET_EVENT]:
        normalized["events"][key] = normalize_event_value(incoming_events.get(key))

    return normalized


def load_state(trade_date: str) -> dict:
    ensure_runtime_dir()

    if not STATE_FILE.exists():
        state = default_state(trade_date)
        save_state(state)
        return state

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            raw_state = json.load(f)
    except Exception:
        state = default_state(trade_date)
        save_state(state)
        return state

    state = normalize_state(raw_state, trade_date)
    save_state(state)
    return state


def save_state(state: dict) -> None:
    ensure_runtime_dir()
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def set_event_status(state: dict, event_name: str, status: str) -> None:
    state["events"][event_name] = {
        "status": status,
        "updated_at": now_ist().isoformat(),
    }
    save_state(state)


def get_event_status(state: dict, event_name: str) -> str:
    event = normalize_event_value(state.get("events", {}).get(event_name))
    return str(event.get("status", EVENT_STATUS_PENDING))


def is_event_pending(state: dict, event_name: str) -> bool:
    return get_event_status(state, event_name) == EVENT_STATUS_PENDING


def seconds_to_next_minute() -> float:
    now_epoch = time.time()
    return max(0.1, 60 - (now_epoch % 60))


def run_script(args: list[str], label: str) -> int:
    print("-" * 72)
    print(f"[RUN] {label} :: {' '.join(args)}")
    print("-" * 72)

    result = subprocess.run(
        args,
        check=False,
    )

    print(f"[EXIT] {label} | returncode={result.returncode}")
    return result.returncode


def run_reference_capture(event_name: str) -> tuple[int, int, int | None]:
    print("=" * 72)
    print(f"[REFERENCE EVENT] {event_name} | {now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 72)

    rc_spot = run_script([sys.executable, SPOT_SCRIPT], "spot")
    rc_futures = run_script([sys.executable, FUTURES_SCRIPT], "futures")

    rc_archive: int | None = None
    if rc_spot == 0 and rc_futures == 0:
        print("[INFO] Spot and futures succeeded. Running tape archival.")
        rc_archive = run_script([sys.executable, ARCHIVE_SCRIPT], "archive_market_tape_history")
    else:
        print(
            f"[WARN] Skipping tape archival because prerequisites failed "
            f"(spot={rc_spot}, futures={rc_futures})."
        )

    print("=" * 72)
    print(
        f"[REFERENCE EVENT COMPLETE] {event_name} | "
        f"spot={rc_spot} | futures={rc_futures} | "
        f"archive={rc_archive if rc_archive is not None else 'SKIPPED'}"
    )
    print("=" * 72)

    return rc_spot, rc_futures, rc_archive


def run_regular_cycle() -> tuple[int, int, int, int, int | None]:
    print("=" * 72)
    print(f"[CYCLE START] {now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 72)

    rc_spot = run_script([sys.executable, SPOT_SCRIPT], "spot")
    rc_futures = run_script([sys.executable, FUTURES_SCRIPT], "futures")
    rc_nifty_atm = run_script(
        [sys.executable, OPTION_CHAIN_SCRIPT, "NIFTY", "ATM_ONLY"],
        "ingest_option_chain NIFTY ATM_ONLY",
    )
    rc_sensex_atm = run_script(
        [sys.executable, OPTION_CHAIN_SCRIPT, "SENSEX", "ATM_ONLY"],
        "ingest_option_chain SENSEX ATM_ONLY",
    )

    rc_archive: int | None = None
    if rc_spot == 0 and rc_futures == 0:
        print("[INFO] Spot and futures succeeded. Running tape archival.")
        rc_archive = run_script([sys.executable, ARCHIVE_SCRIPT], "archive_market_tape_history")
    else:
        print(
            f"[WARN] Skipping tape archival because prerequisites failed "
            f"(spot={rc_spot}, futures={rc_futures})."
        )

    print("=" * 72)
    print(
        f"[CYCLE END] spot={rc_spot} | futures={rc_futures} | "
        f"nifty_atm={rc_nifty_atm} | sensex_atm={rc_sensex_atm} | "
        f"archive={rc_archive if rc_archive is not None else 'SKIPPED'} | "
        f"time={now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )
    print("=" * 72)

    return rc_spot, rc_futures, rc_nifty_atm, rc_sensex_atm, rc_archive


def within_window(current: datetime, target: datetime, window_seconds: int) -> bool:
    return target <= current < (target + timedelta(seconds=window_seconds))


def should_run_premarket_ref(state: dict, now_dt: datetime) -> bool:
    cfg = get_today_session_config(now_dt)
    return (
        cfg.is_open
        and is_event_pending(state, PREMARKET_EVENT)
        and within_window(now_dt, cfg.premarket_ref_dt, PREMARKET_WINDOW_SECONDS)
    )


def should_run_regular_session(now_dt: datetime) -> bool:
    return current_session_state(now_dt) == "REGULAR_SESSION"


def should_run_postmarket_ref(state: dict, now_dt: datetime) -> bool:
    cfg = get_today_session_config(now_dt)
    return (
        cfg.is_open
        and is_event_pending(state, POSTMARKET_EVENT)
        and within_window(now_dt, cfg.postmarket_ref_dt, POSTMARKET_WINDOW_SECONDS)
    )


def should_exit_for_day(state: dict, now_dt: datetime) -> bool:
    cfg = get_today_session_config(now_dt)
    return (
        cfg.is_open
        and now_dt > (cfg.postmarket_ref_dt + timedelta(seconds=POSTMARKET_WINDOW_SECONDS))
        and not is_event_pending(state, POSTMARKET_EVENT)
    )


def mark_missed_events_if_needed(state: dict, now_dt: datetime) -> None:
    cfg = get_today_session_config(now_dt)

    if (
        is_event_pending(state, PREMARKET_EVENT)
        and now_dt >= (cfg.premarket_ref_dt + timedelta(seconds=PREMARKET_WINDOW_SECONDS))
    ):
        print("[WARN] Premarket reference window missed. Marking event as MISSED.")
        set_event_status(state, PREMARKET_EVENT, EVENT_STATUS_MISSED)

    if is_event_pending(state, OPEN_EVENT) and now_dt > cfg.open_dt:
        print("[WARN] Open reference was not explicitly captured. Marking event as MISSED.")
        set_event_status(state, OPEN_EVENT, EVENT_STATUS_MISSED)

    if is_event_pending(state, CLOSE_EVENT) and now_dt > cfg.close_dt:
        print("[WARN] Close reference was not satisfied during regular session. Marking event as MISSED.")
        set_event_status(state, CLOSE_EVENT, EVENT_STATUS_MISSED)

    if (
        is_event_pending(state, POSTMARKET_EVENT)
        and now_dt >= (cfg.postmarket_ref_dt + timedelta(seconds=POSTMARKET_WINDOW_SECONDS))
    ):
        print("[WARN] Postmarket reference window missed. Marking event as MISSED.")
        set_event_status(state, POSTMARKET_EVENT, EVENT_STATUS_MISSED)


def print_startup_banner() -> None:
    print("=" * 72)
    print("MERDIAN - Session-Controlled Market Tape Runner")
    print("=" * 72)
    print(f"[INFO] Interpreter: {sys.executable}")
    print(f"[INFO] Base dir: {BASE_DIR}")
    print(f"[INFO] Session state file: {STATE_FILE}")
    print(f"[INFO] Premarket window seconds: {PREMARKET_WINDOW_SECONDS}")
    print(f"[INFO] Postmarket window seconds: {POSTMARKET_WINDOW_SECONDS}")
    print("[INFO] Options path consolidated to canonical option_chain_snapshots via ATM_ONLY mode.")


def main() -> int:
    print_startup_banner()

    while True:
        current = now_ist()

        try:
            cfg = get_today_session_config(current)
        except MissingSessionConfigError as exc:
            print("=" * 72)
            print("[FATAL] Trading calendar coverage missing for today.")
            print(str(exc))
            print("[FATAL] Exiting market tape runner.")
            print("=" * 72)
            return 2
        except TradingCalendarError as exc:
            print("=" * 72)
            print("[FATAL] Trading calendar configuration error.")
            print(str(exc))
            print("[FATAL] Exiting market tape runner.")
            print("=" * 72)
            return 2

        state = load_state(cfg.date)
        mark_missed_events_if_needed(state, current)

        session_state = current_session_state(current)

        print("-" * 72)
        print(
            f"[HEARTBEAT] now={current.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
            f"state={session_state} | "
            f"events={state['events']}"
        )
        print("-" * 72)

        if not cfg.is_open:
            print(f"[INFO] Trading calendar marks {cfg.date} as CLOSED. Exiting runner.")
            return 0

        if should_run_premarket_ref(state, current):
            rc_spot, rc_futures, _ = run_reference_capture(PREMARKET_EVENT)
            if rc_spot == 0 and rc_futures == 0:
                set_event_status(state, PREMARKET_EVENT, EVENT_STATUS_DONE)
            else:
                print("[WARN] Premarket reference capture failed inside valid window; marking MISSED.")
                set_event_status(state, PREMARKET_EVENT, EVENT_STATUS_MISSED)
            time.sleep(5)
            continue

        if should_run_regular_session(current):
            rc_spot, rc_futures, _, _, _ = run_regular_cycle()

            if rc_spot == 0 and rc_futures == 0:
                if current >= cfg.open_dt and is_event_pending(state, OPEN_EVENT):
                    print("[INFO] Marking OPEN reference as satisfied by this regular-session cycle.")
                    set_event_status(state, OPEN_EVENT, EVENT_STATUS_DONE)

                if current >= cfg.close_dt and is_event_pending(state, CLOSE_EVENT):
                    print("[INFO] Marking CLOSE reference as satisfied by this regular-session cycle.")
                    set_event_status(state, CLOSE_EVENT, EVENT_STATUS_DONE)

            sleep_seconds = seconds_to_next_minute()
            print(f"[SLEEP] Sleeping {sleep_seconds:.2f} seconds to next minute boundary.")
            time.sleep(sleep_seconds)
            continue

        if should_run_postmarket_ref(state, current):
            rc_spot, rc_futures, _ = run_reference_capture(POSTMARKET_EVENT)
            if rc_spot == 0 and rc_futures == 0:
                set_event_status(state, POSTMARKET_EVENT, EVENT_STATUS_DONE)
            else:
                print("[WARN] Postmarket reference capture failed inside valid window; marking MISSED.")
                set_event_status(state, POSTMARKET_EVENT, EVENT_STATUS_MISSED)
            time.sleep(5)
            continue

        if should_exit_for_day(state, current):
            print("=" * 72)
            print(f"[INFO] Session complete for {cfg.date}. Exiting market tape runner.")
            print("=" * 72)
            return 0

        if cfg.monitor_start_dt <= current < cfg.open_dt:
            print("[IDLE] Premarket monitoring window. Waiting for premarket/open events.")
            time.sleep(5)
        elif cfg.close_dt <= current <= (cfg.postmarket_ref_dt + timedelta(seconds=POSTMARKET_WINDOW_SECONDS)):
            print("[IDLE] Post-close monitoring window. Waiting for postmarket reference event.")
            time.sleep(5)
        else:
            print("[IDLE] Outside monitored session window.")
            time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())