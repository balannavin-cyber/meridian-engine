import subprocess
import time
from datetime import datetime, timedelta
import pytz
import os
import sys

from trading_calendar import is_trading_day, get_today_session

PYTHON_EXE = sys.executable
SCRIPT_PATH = r"C:\GammaEnginePython\ingest_ad_intraday_local.py"
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
    return open_time, close_time, session


def market_is_open(now_ist: datetime):
    open_time, close_time, _ = get_market_window(now_ist)
    return open_time <= now_ist <= close_time


def seconds_until_next_minute(now_ist: datetime) -> int:
    next_run = now_ist.replace(second=0, microsecond=0) + timedelta(minutes=1)
    delta = (next_run - now_ist).total_seconds()
    return max(1, int(delta))


def run_ingest():
    timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"ad_intraday_{timestamp}.log")

    print("--------------------------------------------------")
    print("Running 1-minute A/D ingest")
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

    print("Finished run")
    return process.returncode


print("===========================================================")
print("Gamma Engine - 1-Minute A/D Session Runner")
print("Runs every 1 minute during market hours")
print("Calendar-controlled, not weekday-controlled")
print("===========================================================")
print("Using Python executable:", PYTHON_EXE)

if not is_trading_day():
    print("Today is not an open trading session according to trading_calendar.json")
    print("Exiting runner.")
    sys.exit(0)

while True:
    now_ist = datetime.now(IST)
    open_time, close_time, session = get_market_window(now_ist)

    print(f"Now (IST): {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        f"Session window: {open_time.strftime('%H:%M')} to {close_time.strftime('%H:%M')} IST | "
        f"Special session: {session.get('special_session', False)} | "
        f"Notes: {session.get('notes', '')}"
    )

    if now_ist > close_time:
        print("Market session is over — exiting runner.")
        break

    if now_ist < open_time:
        wait_sec = int((open_time - now_ist).total_seconds())
        print(f"Session not open yet — sleeping {wait_sec} seconds until open.")
        time.sleep(max(1, wait_sec))
        continue

    rc = run_ingest()
    if rc != 0:
        print(f"A/D ingest exited with code {rc}.")
    else:
        print("A/D ingest completed successfully.")

    now_ist = datetime.now(IST)
    if now_ist > close_time:
        print("Market session is over after this run — exiting runner.")
        break

    wait_sec = seconds_until_next_minute(now_ist)
    print(f"Sleeping {wait_sec} seconds until next 1-minute boundary.")
    time.sleep(wait_sec)