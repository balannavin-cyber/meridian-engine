"""
ENH-93 Replay Harness — Time injection & market-hours guard.

Purpose:
  - Single source of truth for replay timestamp parsing.
  - Hard guard preventing replay execution during live market hours.

Used by:
  - replay_runner_for_date.py (entry-point hard guard)
  - All 7 replay_*.py pipeline scripts (timestamp injection via CLI arg)
  - replay_chain_reconstructor.py (timestamp utilities)

NOT used by:
  - Any live script. Live code is import-blind to this module.

Author: Session 23 (2026-05-08)
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Optional


IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

MARKET_GUARD_START_IST = dt_time(hour=8, minute=0)
MARKET_GUARD_END_IST = dt_time(hour=16, minute=30)


def parse_replay_ts(ts_str: str) -> datetime:
    if not ts_str or not isinstance(ts_str, str):
        raise ValueError(f"Replay timestamp must be a non-empty string, got: {ts_str!r}")
    normalized = ts_str.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise ValueError(
            f"Cannot parse replay timestamp {ts_str!r}: {e}. "
            f"Expected ISO format like '2026-05-07T09:15:00+05:30'."
        ) from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def replay_today_ist(replay_ts: datetime) -> date:
    if replay_ts.tzinfo is None:
        raise ValueError("replay_ts must be timezone-aware")
    return replay_ts.astimezone(IST).date()


def to_iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware before ISO conversion")
    return dt.astimezone(UTC).isoformat()


def assert_outside_market_hours(now: Optional[datetime] = None) -> None:
    if now is None:
        now = datetime.now(IST)
    elif now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    else:
        now = now.astimezone(IST)

    weekday = now.weekday()
    if weekday >= 5:
        return

    current_time = now.time()
    if MARKET_GUARD_START_IST <= current_time < MARKET_GUARD_END_IST:
        raise RuntimeError(
            f"REPLAY BLOCKED: {now.strftime('%Y-%m-%d %H:%M:%S IST')} falls within "
            f"market-hours guard window ({MARKET_GUARD_START_IST.strftime('%H:%M')}-"
            f"{MARKET_GUARD_END_IST.strftime('%H:%M')} IST on trading days). "
            f"Replay must run outside market hours only. "
            f"Earliest allowed today: {MARKET_GUARD_END_IST.strftime('%H:%M')} IST."
        )
    return


def _self_test() -> int:
    print("=" * 60)
    print("replay_clock.py self-test")
    print("=" * 60)

    ts = parse_replay_ts("2026-05-07T09:15:00+05:30")
    assert ts.tzinfo is UTC, f"Expected UTC tz, got {ts.tzinfo}"
    assert ts.hour == 3 and ts.minute == 45, f"IST 09:15 should be UTC 03:45, got {ts}"
    print(f"  [PASS] parse IST-tagged: 2026-05-07T09:15:00+05:30 -> {ts}")

    ts = parse_replay_ts("2026-05-07T03:45:00Z")
    assert ts.hour == 3, f"Expected hour 3, got {ts.hour}"
    print(f"  [PASS] parse Z-suffix:    2026-05-07T03:45:00Z -> {ts}")

    ts = parse_replay_ts("2026-05-07T03:45:00")
    assert ts.tzinfo is UTC, f"Expected UTC tz on naive input, got {ts.tzinfo}"
    print(f"  [PASS] parse naive:       2026-05-07T03:45:00 -> {ts}")

    try:
        parse_replay_ts("not-a-date")
        print("  [FAIL] parse should have rejected 'not-a-date'")
        return 1
    except ValueError:
        print("  [PASS] parse rejects malformed input")

    ts = parse_replay_ts("2026-05-07T18:00:00Z")
    d = replay_today_ist(ts)
    assert d == date(2026, 5, 7), f"Expected 2026-05-07, got {d}"
    print(f"  [PASS] replay_today_ist:  UTC 18:00 -> IST date {d}")

    ts = parse_replay_ts("2026-05-07T19:00:00Z")
    d = replay_today_ist(ts)
    assert d == date(2026, 5, 8), f"Expected 2026-05-08, got {d}"
    print(f"  [PASS] replay_today_ist:  UTC 19:00 -> IST date {d} (midnight crossing)")

    sat_noon = datetime(2026, 5, 9, 12, 0, 0, tzinfo=IST)
    try:
        assert_outside_market_hours(now=sat_noon)
        print("  [PASS] guard allows Saturday 12:00 IST")
    except RuntimeError as e:
        print(f"  [FAIL] guard wrongly blocked Saturday: {e}")
        return 1

    tue_noon = datetime(2026, 5, 12, 12, 0, 0, tzinfo=IST)
    try:
        assert_outside_market_hours(now=tue_noon)
        print("  [FAIL] guard should have blocked Tuesday 12:00 IST")
        return 1
    except RuntimeError:
        print("  [PASS] guard blocks Tuesday 12:00 IST")

    tue_early = datetime(2026, 5, 12, 8, 1, 0, tzinfo=IST)
    try:
        assert_outside_market_hours(now=tue_early)
        print("  [FAIL] guard should have blocked Tuesday 08:01 IST")
        return 1
    except RuntimeError:
        print("  [PASS] guard blocks Tuesday 08:01 IST (lower bound)")

    tue_close = datetime(2026, 5, 12, 16, 30, 0, tzinfo=IST)
    try:
        assert_outside_market_hours(now=tue_close)
        print("  [PASS] guard allows Tuesday 16:30 IST (upper bound exclusive)")
    except RuntimeError as e:
        print(f"  [FAIL] guard wrongly blocked Tuesday 16:30 IST: {e}")
        return 1

    tue_evening = datetime(2026, 5, 12, 17, 0, 0, tzinfo=IST)
    try:
        assert_outside_market_hours(now=tue_evening)
        print("  [PASS] guard allows Tuesday 17:00 IST")
    except RuntimeError as e:
        print(f"  [FAIL] guard wrongly blocked Tuesday 17:00 IST: {e}")
        return 1

    tue_predawn = datetime(2026, 5, 12, 7, 0, 0, tzinfo=IST)
    try:
        assert_outside_market_hours(now=tue_predawn)
        print("  [PASS] guard allows Tuesday 07:00 IST")
    except RuntimeError as e:
        print(f"  [FAIL] guard wrongly blocked Tuesday 07:00 IST: {e}")
        return 1

    print("=" * 60)
    print("All 12 self-tests PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(_self_test())