from __future__ import annotations

import subprocess
import time
from datetime import datetime, timedelta

# CONFIG
START_TIME = "09:15"
END_TIME = "15:30"
OPTION_CHAIN_INTERVAL_MIN = 5


def _now():
    return datetime.now()


def _today_time(hhmm: str):
    h, m = map(int, hhmm.split(":"))
    now = _now()
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def _sleep_until(target: datetime):
    while _now() < target:
        time.sleep(1)


def _run(cmd: list[str]):
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {cmd} -> {e}")


def main():
    print("===================================================")
    print("MERDIAN — Day-1 Historical Archival Runner")
    print("===================================================")

    start_dt = _today_time(START_TIME)
    end_dt = _today_time(END_TIME)

    print(f"Waiting for market open: {start_dt}")
    _sleep_until(start_dt)

    print("Market open. Starting archival loop.")

    next_option_chain_run = start_dt

    while _now() <= end_dt:
        loop_start = _now()

        print(f"\n[{loop_start}] Running 1-minute archival...")

        # 1️⃣ Spot + Futures archival (every minute)
        _run(["python", "archive_market_tape_history.py"])

        # 2️⃣ Option chain archival (every 5 min)
        if _now() >= next_option_chain_run:
            print(f"[{_now()}] Running option chain ingestion + archival...")

            # STEP A — run your existing ingestion
            result = subprocess.run(
                ["python", "ingest_option_chain_local.py"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Attempt to extract run_id from stdout
                output = result.stdout.strip()
                print(output)

                # VERY IMPORTANT: adjust parsing if your script prints differently
                run_id = None
                for line in output.splitlines():
                    if "run_id" in line.lower():
                        run_id = line.split()[-1]

                if run_id:
                    print(f"Archiving run_id={run_id}")
                    _run(["python", "archive_option_chain_history.py", run_id])
                else:
                    print("[WARN] Could not extract run_id from ingestion output")
            else:
                print("[ERROR] Option chain ingestion failed")

            next_option_chain_run += timedelta(minutes=OPTION_CHAIN_INTERVAL_MIN)

        # sleep to next minute boundary
        next_minute = (loop_start + timedelta(minutes=1)).replace(second=0, microsecond=0)
        _sleep_until(next_minute)

    print("\nMarket closed. Archival runner stopped.")


if __name__ == "__main__":
    main()