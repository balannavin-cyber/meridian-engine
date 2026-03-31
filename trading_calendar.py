from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


CALENDAR_FILE = Path(r"C:\GammaEnginePython\trading_calendar.json")
IST = ZoneInfo("Asia/Kolkata")


class TradingCalendarError(RuntimeError):
    """Base class for trading calendar errors."""


class MissingSessionConfigError(TradingCalendarError):
    """Raised when the calendar has no entry for a required date."""


class InvalidSessionConfigError(TradingCalendarError):
    """Raised when a calendar entry is malformed."""


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


def _parse_time(value: str | None, field_name: str, default_value: str) -> time:
    raw = value or default_value
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError as exc:
        raise InvalidSessionConfigError(
            f"Invalid time '{raw}' for field '{field_name}'. Expected HH:MM."
        ) from exc


def load_calendar() -> list[dict]:
    if not CALENDAR_FILE.exists():
        raise TradingCalendarError(f"trading_calendar.json not found at {CALENDAR_FILE}")

    with CALENDAR_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sessions = data.get("sessions", [])
    if not isinstance(sessions, list):
        raise InvalidSessionConfigError("Calendar file must contain a top-level 'sessions' list.")

    return sessions


def get_session_for_date(date_str: str) -> dict:
    for session in load_calendar():
        if session.get("date") == date_str:
            return session
    raise MissingSessionConfigError(
        f"No trading calendar entry found for {date_str}. "
        f"Update {CALENDAR_FILE.name} before starting market-sensitive runners."
    )


def build_session_config(session: dict) -> SessionConfig:
    date_str = session.get("date")
    if not date_str:
        raise InvalidSessionConfigError("Session entry is missing required field 'date'.")

    is_open = bool(session.get("is_open", False))

    # Centralized session defaults for MERDIAN.
    # These can later be overridden per-day in trading_calendar.json if needed.
    monitor_start_time = _parse_time(
        session.get("monitor_start_time"), "monitor_start_time", "09:00"
    )
    premarket_ref_time = _parse_time(
        session.get("premarket_ref_time"), "premarket_ref_time", "09:08"
    )
    open_time = _parse_time(session.get("open_time"), "open_time", "09:15")
    close_time = _parse_time(session.get("close_time"), "close_time", "15:30")
    postmarket_ref_time = _parse_time(
        session.get("postmarket_ref_time"), "postmarket_ref_time", "16:00"
    )
    final_eod_ltp_time = _parse_time(
        session.get("final_eod_ltp_time"), "final_eod_ltp_time", "16:15"
    )

    if is_open:
        ordered = [
            ("monitor_start_time", monitor_start_time),
            ("premarket_ref_time", premarket_ref_time),
            ("open_time", open_time),
            ("close_time", close_time),
            ("postmarket_ref_time", postmarket_ref_time),
            ("final_eod_ltp_time", final_eod_ltp_time),
        ]
        for i in range(len(ordered) - 1):
            left_name, left_time = ordered[i]
            right_name, right_time = ordered[i + 1]
            if left_time >= right_time:
                raise InvalidSessionConfigError(
                    f"Session '{date_str}' has invalid ordering: "
                    f"{left_name} ({left_time}) must be earlier than "
                    f"{right_name} ({right_time})."
                )

    return SessionConfig(
        date=date_str,
        is_open=is_open,
        monitor_start_time=monitor_start_time,
        premarket_ref_time=premarket_ref_time,
        open_time=open_time,
        close_time=close_time,
        postmarket_ref_time=postmarket_ref_time,
        final_eod_ltp_time=final_eod_ltp_time,
        special_session=bool(session.get("special_session", False)),
        notes=str(session.get("notes", "")),
    )


def get_session_config_for_date(date_str: str) -> SessionConfig:
    return build_session_config(get_session_for_date(date_str))


def get_today_session_config(now: datetime | None = None) -> SessionConfig:
    current = now or now_ist()
    date_str = current.strftime("%Y-%m-%d")
    return get_session_config_for_date(date_str)


def is_trading_day(now: datetime | None = None) -> bool:
    cfg = get_today_session_config(now)
    return cfg.is_open


def get_session_times(now: datetime | None = None) -> dict[str, str | bool]:
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
        print("MERDIAN - Trading Calendar Check")
        print("=" * 72)
        print("Now:", current.strftime("%Y-%m-%d %H:%M:%S %Z"))
        print("Date:", cfg.date)
        print("Trading day:", cfg.is_open)
        print("Session state:", current_session_state(current))
        print("Session config:")
        print("  monitor_start_time :", cfg.monitor_start_time.strftime("%H:%M"))
        print("  premarket_ref_time :", cfg.premarket_ref_time.strftime("%H:%M"))
        print("  open_time          :", cfg.open_time.strftime("%H:%M"))
        print("  close_time         :", cfg.close_time.strftime("%H:%M"))
        print("  postmarket_ref_time:", cfg.postmarket_ref_time.strftime("%H:%M"))
        print("  final_eod_ltp_time :", cfg.final_eod_ltp_time.strftime("%H:%M"))
        print("  special_session    :", cfg.special_session)
        print("  notes              :", cfg.notes)
    except Exception as exc:
        print("=" * 72)
        print("MERDIAN - Trading Calendar Check FAILED")
        print("=" * 72)
        print(str(exc))
        raise