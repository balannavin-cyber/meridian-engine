import subprocess
import time
from datetime import datetime, timedelta
import pytz
import os
import sys

from trading_calendar import is_trading_day, get_today_session

PYTHON_EXE = sys.executable
SCRIPT_PATH = r"C:\GammaEnginePython\ingest_breadth_intraday_local.py"
COVERAGE_SCRIPT = r"C:\GammaEnginePython\coverage_check.py"
LOG_DIR = r"C:\GammaEnginePython\logs"

IST = pytz.timezone("Asia/Kolkata")


def parse_hhmm_to_dt(now_ist: datetime, hhmm: str) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return now_ist.replace(hour=hour, minute=minute, second=0, microsecond=0)


def get_market_window(now_ist: datetime):
    session = get_today_session()
    if not session:
        raise RuntimeError("No trading calendar entry found for today")

    open_time = parse_hhmm_to_dt(now_ist, session.get("open_time", "09:15"))
    close_time = parse_hhmm_to_dt(now_ist, session.get("close_time", "15:30"))
    final_eod_time = parse_hhmm_to_dt(now_ist, session.get("final_eod_ltp_time", "16:15"))

    return open_time, close_time, final_eod_time, session


def market_is_open(now_ist: datetime):
    open_time, close_time, _, _ = get_market_window(now_ist)
    return open_time <= now_ist <= close_time


def seconds_until_next_15m_boundary(now_ist: datetime) -> int:
    next_minute = ((now_ist.minute // 15) + 1) * 15
    if next_minute >= 60:
        next_run = now_ist.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_run = now_ist.replace(minute=next_minute, second=0, microsecond=0)

    delta = (next_run - now_ist).total_seconds()
    return max(1, int(delta))


def run_coverage_check() -> str:
    process = subprocess.run(
        [PYTHON_EXE, COVERAGE_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    return process.stdout or ""


def run_ingest(run_label: str):
    timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"intraday_breadth_{run_label}_{timestamp}.log")

    print("--------------------------------------------------")
    print("Running intraday breadth ingest")
    print("Run label :", run_label)
    print("Timestamp :", timestamp)
    print("Python exe:", PYTHON_EXE)
    print("Log file  :", log_file)
    print("--------------------------------------------------")

    with open(log_file, "w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [PYTHON_EXE, SCRIPT_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line.strip())
            log.write(line)

        process.wait()

        log.write("\n" + "-" * 80 + "\n")
        log.write("COVERAGE CHECK\n")
        log.write("-" * 80 + "\n")

        coverage_output = run_coverage_check()
        print("-" * 72)
        print("Coverage after run")
        print(coverage_output)
        log.write(coverage_output)

    print("Finished run")
    return process.returncode


print("===========================================================")
print("Gamma Engine - Intraday Breadth Session Runner")
print("Runs every 15 minutes during market hours")
print("Also runs one final EOD LTP snapshot at session final time")
print("Coverage check runs after every execution")
print("Calendar-controlled, not weekday-controlled")
print("===========================================================")
print("Using Python executable:", PYTHON_EXE)

if not is_trading_day():
    print("Today is not an open trading session according to trading_calendar.json")
    print("Exiting runner.")
    sys.exit(0)

final_eod_done = False

while True:
    now_ist = datetime.now(IST)
    open_time, close_time, final_eod_time, session = get_market_window(now_ist)

    print(f"Now (IST): {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        f"Session window: {open_time.strftime('%H:%M')} to {close_time.strftime('%H:%M')} IST | "
        f"Final EOD LTP: {final_eod_time.strftime('%H:%M')} IST | "
        f"Special session: {session.get('special_session', False)} | "
        f"Notes: {session.get('notes', '')}"
    )

    if market_is_open(now_ist):
        rc = run_ingest("market_hours")
        if rc != 0:
            print(f"Ingest script exited with code {rc}.")
        else:
            print("Ingest completed successfully.")

        now_ist = datetime.now(IST)
        if now_ist <= close_time:
            wait_sec = seconds_until_next_15m_boundary(now_ist)
            print(f"Sleeping {wait_sec} seconds until next 15-minute boundary.")
            time.sleep(wait_sec)
            continue

    now_ist = datetime.now(IST)
    if now_ist > close_time and not final_eod_done:
        if now_ist < final_eod_time:
            wait_sec = int((final_eod_time - now_ist).total_seconds())
            print(f"Market closed. Waiting {wait_sec} seconds for final EOD LTP run.")
            time.sleep(max(1, wait_sec))
            continue

        if now_ist >= final_eod_time:
            # If runner is started too late in the evening, do not back-run final EOD.
            if now_ist > final_eod_time + timedelta(minutes=30):
                print("Runner started well after final EOD LTP window. Exiting without back-running.")
                break

            rc = run_ingest("final_eod_ltp")
            final_eod_done = True

            if rc != 0:
                print(f"Final EOD LTP ingest exited with code {rc}.")
            else:
                print("Final EOD LTP ingest completed successfully.")

            print("Final EOD LTP run completed — exiting runner.")
            break

    if now_ist < open_time:
        wait_sec = int((open_time - now_ist).total_seconds())
        print(f"Session not open yet — sleeping {wait_sec} seconds until open.")
        time.sleep(max(1, wait_sec))
        continue

    if final_eod_done:
        print("Session complete — exiting runner.")
        break

    print("No action needed — sleeping 60 seconds.")
    time.sleep(60)