import json
from datetime import datetime
from pathlib import Path
import pytz

CALENDAR_FILE = Path(r"C:\GammaEnginePython\trading_calendar.json")
IST = pytz.timezone("Asia/Kolkata")


def load_calendar():
    if not CALENDAR_FILE.exists():
        raise RuntimeError("trading_calendar.json not found")

    with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("sessions", [])


def get_session_for_date(date_str: str):
    sessions = load_calendar()
    for s in sessions:
        if s.get("date") == date_str:
            return s
    return None


def get_today_session():
    today = datetime.now(IST).strftime("%Y-%m-%d")
    return get_session_for_date(today)


def is_trading_day():
    session = get_today_session()
    if not session:
        return False
    return bool(session.get("is_open", False))


def get_session_times():
    session = get_today_session()
    if not session:
        return None

    return {
        "open": session.get("open_time", "09:15"),
        "close": session.get("close_time", "15:30"),
        "final_ltp": session.get("final_eod_ltp_time", "16:15"),
        "special": session.get("special_session", False),
        "notes": session.get("notes", "")
    }


if __name__ == "__main__":
    today = datetime.now(IST).strftime("%Y-%m-%d")
    session = get_today_session()

    print("=" * 72)
    print("Gamma Engine - Trading Calendar Check")
    print("=" * 72)
    print("Today:", today)
    print("Trading day:", is_trading_day())

    if session:
        print("Session config:", session)
    else:
        print("No session found for today")