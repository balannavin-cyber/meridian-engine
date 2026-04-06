"""
trading_calendar.py — MERDIAN Trading Calendar

Design principles:
- NSE is open every weekday EXCEPT declared holidays.
- Weekends are always closed. No row needed.
- Holidays are the ONLY thing stored in trading_calendar.json.
- No row insertion required for normal trading days. Ever.
- Adding a holiday = add one entry to the holidays list. That's it.
- Special sessions (muhurat etc.) are stored separately and override the default.

trading_calendar.json structure:
{
    "holidays": [
        {"date": "2026-04-14", "name": "Dr. Ambedkar Jayanti"},
        {"date": "2026-04-18", "name": "Good Friday"}
    ],
    "special_sessions": [
        {
            "date": "2025-11-01",
            "name": "Muhurat Trading",
            "open_time": "18:15",
            "close_time": "18:30"
        }
    ]
}

Default session times (all normal trading days):
    monitor_start  : 09:00
    premarket_ref  : 09:08
    open           : 09:15
    close          : 15:30
    postmarket_ref : 16:00
    final_eod_ltp  : 16:15
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import os

CALENDAR_FILE = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_calendar.json"))
IST = ZoneInfo("Asia/Kolkata")

# Default session times — apply to every normal trading day
DEFAULT_MONITOR_START  = time(9,  0)
DEFAULT_PREMARKET_REF  = time(9,  8)
DEFAULT_OPEN           = time(9, 15)
DEFAULT_CLOSE          = time(15, 30)
DEFAULT_POSTMARKET_REF = time(16,  0)
DEFAULT_FINAL_EOD_LTP  = time(16, 15)


class TradingCalendarError(RuntimeError):
    """Base class for trading calendar errors."""


class MissingSessionConfigError(TradingCalendarError):
    """Kept for backward compatibility — raised only for truly unconfigurable dates."""


class InvalidSessionConfigError(TradingCalendarError):
    """Raised when calendar file is malformed."""


@dataclass(frozen=True)
class SessionConfig:
    date: str
    is_open: bool
    monitor_start_time: time
    premarket_ref_time: time
    open_time: time
    close_time: time
    postmarket_ref_time: time
    final_eod_ltp_time: time
    special_session: bool
    notes: str

    def dt(self, t: time) -> datetime:
        d = datetime.strptime(self.date, "%Y-%m-%d").date()
        return datetime.combine(d, t, tzinfo=IST)

    @property
    def monitor_start_dt(self) -> datetime:
        return self.dt(self.monitor_start_time)

    @property
    def premarket_ref_dt(self) -> datetime:
        return self.dt(self.premarket_ref_time)

    @property
    def open_dt(self) -> datetime:
        return self.dt(self.open_time)

    @property
    def close_dt(self) -> datetime:
        return self.dt(self.close_time)

    @property
    def postmarket_ref_dt(self) -> datetime:
        return self.dt(self.postmarket_ref_time)

    @property
    def final_eod_ltp_dt(self) -> datetime:
        return self.dt(self.final_eod_ltp_time)


def now_ist() -> datetime:
    return datetime.now(IST)


def _parse_time(value: str, field_name: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise InvalidSessionConfigError(
            f"Invalid time '{value}' for field '{field_name}'. Expected HH:MM."
        ) from exc


def _load_calendar_data() -> dict:
    """Load and validate trading_calendar.json."""
    if not CALENDAR_FILE.exists():
        raise TradingCalendarError(
            f"trading_calendar.json not found at {CALENDAR_FILE}. "
            f"Create it with an empty holidays list: {{\"holidays\": [], \"special_sessions\": []}}"
        )
    with CALENDAR_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise InvalidSessionConfigError("trading_calendar.json must be a JSON object.")
    if "holidays" not in data:
        raise InvalidSessionConfigError(
            "trading_calendar.json must contain a 'holidays' key. "
            "Even if there are no holidays, include: {\"holidays\": [], \"special_sessions\": []}"
        )
    return data


def _get_holidays() -> set[str]:
    """Return the set of NSE holiday dates as YYYY-MM-DD strings."""
    data = _load_calendar_data()
    holidays = data.get("holidays", [])
    if not isinstance(holidays, list):
        raise InvalidSessionConfigError("'holidays' must be a list.")
    result = set()
    for entry in holidays:
        date_str = entry.get("date")
        if not date_str:
            raise InvalidSessionConfigError(f"Holiday entry missing 'date': {entry}")
        result.add(date_str)
    return result


def _get_special_sessions() -> dict[str, dict]:
    """Return special session overrides keyed by YYYY-MM-DD."""
    data = _load_calendar_data()
    specials = data.get("special_sessions", [])
    if not isinstance(specials, list):
        raise InvalidSessionConfigError("'special_sessions' must be a list.")
    result = {}
    for entry in specials:
        date_str = entry.get("date")
        if not date_str:
            raise InvalidSessionConfigError(f"Special session entry missing 'date': {entry}")
        result[date_str] = entry
    return result


def _is_weekday(date_str: str) -> bool:
    """Return True if date is Monday–Friday."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.weekday() < 5  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday


def get_session_config_for_date(date_str: str) -> SessionConfig:
    """
    Return SessionConfig for any date.

    Rules:
    1. Weekend → closed, default times
    2. NSE holiday → closed, default times
    3. Special session → open, custom times from special_sessions list
    4. Everything else → open, default times

    No manual date insertion ever required.
    """
    holidays = _get_holidays()
    specials = _get_special_sessions()

    # Rule 1: Weekend
    if not _is_weekday(date_str):
        return SessionConfig(
            date=date_str,
            is_open=False,
            monitor_start_time=DEFAULT_MONITOR_START,
            premarket_ref_time=DEFAULT_PREMARKET_REF,
            open_time=DEFAULT_OPEN,
            close_time=DEFAULT_CLOSE,
            postmarket_ref_time=DEFAULT_POSTMARKET_REF,
            final_eod_ltp_time=DEFAULT_FINAL_EOD_LTP,
            special_session=False,
            notes="Weekend",
        )

    # Rule 2: NSE holiday
    if date_str in holidays:
        holiday_name = next(
            (h.get("name", "NSE Holiday") for h in _load_calendar_data().get("holidays", [])
             if h.get("date") == date_str),
            "NSE Holiday"
        )
        return SessionConfig(
            date=date_str,
            is_open=False,
            monitor_start_time=DEFAULT_MONITOR_START,
            premarket_ref_time=DEFAULT_PREMARKET_REF,
            open_time=DEFAULT_OPEN,
            close_time=DEFAULT_CLOSE,
            postmarket_ref_time=DEFAULT_POSTMARKET_REF,
            final_eod_ltp_time=DEFAULT_FINAL_EOD_LTP,
            special_session=False,
            notes=holiday_name,
        )

    # Rule 3: Special session (muhurat etc.)
    if date_str in specials:
        s = specials[date_str]
        open_time  = _parse_time(s.get("open_time",  "09:15"), "open_time")
        close_time = _parse_time(s.get("close_time", "15:30"), "close_time")
        return SessionConfig(
            date=date_str,
            is_open=True,
            monitor_start_time=open_time,
            premarket_ref_time=open_time,
            open_time=open_time,
            close_time=close_time,
            postmarket_ref_time=close_time,
            final_eod_ltp_time=close_time,
            special_session=True,
            notes=s.get("name", "Special Session"),
        )

    # Rule 4: Normal trading day
    return SessionConfig(
        date=date_str,
        is_open=True,
        monitor_start_time=DEFAULT_MONITOR_START,
        premarket_ref_time=DEFAULT_PREMARKET_REF,
        open_time=DEFAULT_OPEN,
        close_time=DEFAULT_CLOSE,
        postmarket_ref_time=DEFAULT_POSTMARKET_REF,
        final_eod_ltp_time=DEFAULT_FINAL_EOD_LTP,
        special_session=False,
        notes="Normal trading day",
    )


def get_today_session_config(now: datetime | None = None) -> SessionConfig:
    current = now or now_ist()
    return get_session_config_for_date(current.strftime("%Y-%m-%d"))


# Backward-compatible alias — existing code calls this
def get_session_for_date(date_str: str) -> dict:
    """
    Backward-compatible shim. Returns a dict matching the old format.
    Callers that used get_session_for_date() directly still work.
    """
    cfg = get_session_config_for_date(date_str)
    return {
        "date": cfg.date,
        "is_open": cfg.is_open,
        "monitor_start_time": cfg.monitor_start_time.strftime("%H:%M"),
        "premarket_ref_time": cfg.premarket_ref_time.strftime("%H:%M"),
        "open_time": cfg.open_time.strftime("%H:%M"),
        "close_time": cfg.close_time.strftime("%H:%M"),
        "postmarket_ref_time": cfg.postmarket_ref_time.strftime("%H:%M"),
        "final_eod_ltp_time": cfg.final_eod_ltp_time.strftime("%H:%M"),
        "special_session": cfg.special_session,
        "notes": cfg.notes,
    }


def build_session_config(session: dict) -> SessionConfig:
    """
    Backward-compatible shim. Old code that called build_session_config(dict)
    can continue to work. We re-derive from the date in the dict.
    """
    date_str = session.get("date")
    if not date_str:
        raise InvalidSessionConfigError("Session dict missing 'date'.")
    return get_session_config_for_date(date_str)


def is_trading_day(now: datetime | None = None) -> bool:
    return get_today_session_config(now).is_open


def get_session_times(now: datetime | None = None) -> dict:
    cfg = get_today_session_config(now)
    return {
        "monitor_start": cfg.monitor_start_time.strftime("%H:%M"),
        "premarket_ref": cfg.premarket_ref_time.strftime("%H:%M"),
        "open": cfg.open_time.strftime("%H:%M"),
        "close": cfg.close_time.strftime("%H:%M"),
        "postmarket_ref": cfg.postmarket_ref_time.strftime("%H:%M"),
        "final_ltp": cfg.final_eod_ltp_time.strftime("%H:%M"),
        "special": cfg.special_session,
        "notes": cfg.notes,
    }


def current_session_state(now: datetime | None = None) -> str:
    current = now or now_ist()
    cfg = get_today_session_config(current)

    if not cfg.is_open:
        return "CLOSED"

    one_minute = timedelta(minutes=1)

    if current < cfg.monitor_start_dt:
        return "CLOSED"
    if cfg.monitor_start_dt <= current < cfg.premarket_ref_dt:
        return "PREMARKET_MONITOR"
    if cfg.premarket_ref_dt <= current < min(cfg.open_dt, cfg.premarket_ref_dt + one_minute):
        return "PREMARKET_REF_DUE"
    if cfg.premarket_ref_dt + one_minute <= current < cfg.open_dt:
        return "OPEN_WAIT"
    if cfg.open_dt <= current < cfg.close_dt:
        return "REGULAR_SESSION"
    if cfg.close_dt <= current < min(cfg.postmarket_ref_dt, cfg.close_dt + one_minute):
        return "CLOSE_REF_DUE"
    if cfg.close_dt + one_minute <= current < cfg.postmarket_ref_dt:
        return "POST_CLOSE_WAIT"
    if cfg.postmarket_ref_dt <= current < cfg.postmarket_ref_dt + one_minute:
        return "POSTMARKET_REF_DUE"
    return "POSTMARKET_COMPLETE"


def is_regular_session(now: datetime | None = None) -> bool:
    return current_session_state(now) == "REGULAR_SESSION"


def is_premarket_ref_due(now: datetime | None = None) -> bool:
    return current_session_state(now) == "PREMARKET_REF_DUE"


def is_close_ref_due(now: datetime | None = None) -> bool:
    return current_session_state(now) == "CLOSE_REF_DUE"


def is_postmarket_ref_due(now: datetime | None = None) -> bool:
    return current_session_state(now) == "POSTMARKET_REF_DUE"


if __name__ == "__main__":
    try:
        current = now_ist()
        cfg = get_today_session_config(current)
        print("=" * 72)
        print("MERDIAN - Trading Calendar")
        print("=" * 72)
        print(f"Now              : {current.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Date             : {cfg.date}")
        print(f"Trading day      : {cfg.is_open}")
        print(f"Session state    : {current_session_state(current)}")
        print(f"Notes            : {cfg.notes}")
        if cfg.is_open:
            print(f"  monitor_start  : {cfg.monitor_start_time.strftime('%H:%M')}")
            print(f"  premarket_ref  : {cfg.premarket_ref_time.strftime('%H:%M')}")
            print(f"  open           : {cfg.open_time.strftime('%H:%M')}")
            print(f"  close          : {cfg.close_time.strftime('%H:%M')}")
            print(f"  postmarket_ref : {cfg.postmarket_ref_time.strftime('%H:%M')}")
            print(f"  final_eod_ltp  : {cfg.final_eod_ltp_time.strftime('%H:%M')}")
    except Exception as exc:
        print("MERDIAN - Trading Calendar FAILED")
        print(str(exc))
        raise
