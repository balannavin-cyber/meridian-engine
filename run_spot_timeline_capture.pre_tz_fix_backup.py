@'
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from capture_market_spot_snapshot_local import capture_once


# India Standard Time = UTC+05:30
# Fixed offset avoids dependency on tzdata / zoneinfo package data.
IST = timezone(timedelta(hours=5, minutes=30))

MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

CAPTURE_INTERVAL_SECONDS = 60


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def session_open_dt(ref: datetime) -> datetime:
    return ref.replace(
        hour=MARKET_OPEN_HOUR,
        minute=MARKET_OPEN_MINUTE,
        second=0,
        microsecond=0,
    )


def session_close_dt(ref: datetime) -> datetime:
    return ref.replace(
        hour=MARKET_CLOSE_HOUR,
        minute=MARKET_CLOSE_MINUTE,
        second=0,
        microsecond=0,
    )


def is_weekday(ref: datetime) -> bool:
    return ref.weekday() < 5


def in_market_session(ref: datetime) -> bool:
    if not is_weekday(ref):
        return False
    return session_open_dt(ref) <= ref <= session_close_dt(ref)


def next_capture_boundary(ref: datetime) -> datetime:
    base = ref.replace(second=0, microsecond=0)

    if CAPTURE_INTERVAL_SECONDS == 60:
        if ref.second == 0 and ref.microsecond == 0:
            return base
        return base + timedelta(minutes=1)

    elapsed = ref.minute * 60 + ref.second
    next_elapsed = ((elapsed // CAPTURE_INTERVAL_SECONDS) + 1) * CAPTURE_INTERVAL_SECONDS
    next_minute = next_elapsed // 60
    next_second = next_elapsed % 60

    return ref.replace(
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(minutes=next_minute, seconds=next_second)


def sleep_until(target: datetime) -> None:
    while True:
        now = now_ist()
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 1.0))


def run() -> None:
    print("=" * 72)
    print("MERDIAN - Spot Timeline Capture Runner")
    print("=" * 72)
    print(f"Capture interval: {CAPTURE_INTERVAL_SECONDS} seconds")
    print("Session window: 09:15-15:30 IST")
    print("Timezone mode: fixed IST (UTC+05:30)")
    print("-" * 72)

    while True:
        now = now_ist()

        if not in_market_session(now):
            print(f"[IDLE] Outside market session | now={now.isoformat()}")
            time.sleep(60)
            continue

        target = next_capture_boundary(now)
        if target > now:
            print(f"[WAIT] Sleeping until next boundary | target={target.isoformat()}")
            sleep_until(target)

        run_ts = now_ist()
        if not in_market_session(run_ts):
            continue

        print(f"[RUN ] Capturing spot snapshot | now={run_ts.isoformat()}")
        try:
            capture_once()
        except Exception as exc:
            print(f"[ERR ] Spot capture failed: {exc}")

        time.sleep(1)


if __name__ == "__main__":
    run()
'@ | Set-Content .\run_spot_timeline_capture.py