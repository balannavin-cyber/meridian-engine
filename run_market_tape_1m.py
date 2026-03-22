from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================================
# MERDIAN - 1 Minute Market Tape Runner
# ----------------------------------------------------------------------------
# Purpose:
#   Run the live tape layer during market hours.
#
# Sequence each cycle:
#   1. capture_market_spot_snapshot_local.py
#   2. capture_index_futures_snapshot_local.py
#   3. ingest_option_execution_price_history_v2.py
#   4. archive_market_tape_history.py   <-- added
#
# Market session:
#   Monday-Friday
#   09:15 to 15:30 IST
#
# Notes:
#   - Sleeps to the next 1-minute boundary
#   - Runs only during market hours
#   - Executes scripts sequentially
#   - Tape archival runs only if spot + futures succeed
# ============================================================================


IST = ZoneInfo("Asia/Kolkata")

SPOT_SCRIPT = r"C:\gammaenginepython\capture_market_spot_snapshot_local.py"
FUTURES_SCRIPT = r"C:\gammaenginepython\capture_index_futures_snapshot_local.py"
EXECUTION_SCRIPT = r"C:\gammaenginepython\ingest_option_execution_price_history_v2.py"
ARCHIVE_SCRIPT = r"C:\GammaEnginePython\archive_market_tape_history.py"

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


def now_ist() -> datetime:
    return datetime.now(IST)


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def is_market_hours(dt: datetime) -> bool:
    if not is_weekday(dt):
        return False

    current_minutes = dt.hour * 60 + dt.minute
    open_minutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
    close_minutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

    return open_minutes <= current_minutes <= close_minutes


def seconds_to_next_minute() -> float:
    now = time.time()
    return 60 - (now % 60)


def run_script(script_path: str) -> int:
    print("-" * 72)
    print(f"[RUN] {script_path}")
    print("-" * 72)

    result = subprocess.run(
        [sys.executable, script_path],
        check=False,
    )

    print(f"[EXIT] {script_path} | returncode={result.returncode}")
    return result.returncode


def run_cycle() -> None:
    print("=" * 72)
    print(f"[CYCLE START] {now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 72)

    rc1 = run_script(SPOT_SCRIPT)
    rc2 = run_script(FUTURES_SCRIPT)
    rc3 = run_script(EXECUTION_SCRIPT)

    rc4: int | None = None
    if rc1 == 0 and rc2 == 0:
        print("[INFO] Spot and futures succeeded. Running tape archival.")
        rc4 = run_script(ARCHIVE_SCRIPT)
    else:
        print(
            f"[WARN] Skipping tape archival because prerequisites failed "
            f"(spot={rc1}, futures={rc2})."
        )

    print("=" * 72)
    print(
        f"[CYCLE END] spot={rc1} | futures={rc2} | execution={rc3} | "
        f"archive={rc4 if rc4 is not None else 'SKIPPED'} | "
        f"time={now_ist().strftime('%Y-%m-%d %H:%M:%S %Z')}"
    )
    print("=" * 72)


def main() -> int:
    print("=" * 72)
    print("MERDIAN - 1 Minute Market Tape Runner")
    print("=" * 72)
    print(
        f"[INFO] Market window: {MARKET_OPEN_HOUR:02d}:{MARKET_OPEN_MINUTE:02d} "
        f"to {MARKET_CLOSE_HOUR:02d}:{MARKET_CLOSE_MINUTE:02d} IST"
    )
    print("[INFO] Cycle sequence: spot -> futures -> execution_v2 -> tape_archive")

    while True:
        current_time = now_ist()

        if is_market_hours(current_time):
            run_cycle()
            sleep_seconds = seconds_to_next_minute()
            print(f"[SLEEP] Sleeping {sleep_seconds:.2f} seconds to next minute boundary.")
            time.sleep(sleep_seconds)
        else:
            print(
                f"[IDLE] Outside market hours | now={current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
            time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())