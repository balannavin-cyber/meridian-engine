from __future__ import annotations

import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from core.supabase_client import SupabaseClient


IST = timezone(timedelta(hours=5, minutes=30))

MAX_CYCLE_AGE_SECONDS = 420
MAX_SYMBOL_TS_GAP_SECONDS = 180

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def _parse_ts(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _format_ist(ts):
    if ts is None:
        return "None"
    return ts.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def _get_latest_row(sb, table, symbol):
    rows = sb.select(
        table=table,
        filters={"symbol": f"eq.{symbol}"},
        order="ts.desc",
        limit=1,
    )
    if not rows:
        return None
    return rows[0]


def _latest_signal_row(sb, symbol):
    return _get_latest_row(sb, "signal_snapshots", symbol)


def _status_from_rows(now_utc, nifty_row, sensex_row):
    problems = []

    nifty_ts = _parse_ts(nifty_row.get("ts")) if nifty_row else None
    sensex_ts = _parse_ts(sensex_row.get("ts")) if sensex_row else None

    if nifty_ts is None:
        problems.append("NIFTY signal missing")
    if sensex_ts is None:
        problems.append("SENSEX signal missing")

    if problems:
        return "DOWN", problems, nifty_ts, sensex_ts

    nifty_age = (now_utc - nifty_ts).total_seconds()
    sensex_age = (now_utc - sensex_ts).total_seconds()
    symbol_gap = abs((nifty_ts - sensex_ts).total_seconds())

    if nifty_age > MAX_CYCLE_AGE_SECONDS:
        problems.append(f"NIFTY stale ({nifty_age:.0f}s)")
    if sensex_age > MAX_CYCLE_AGE_SECONDS:
        problems.append(f"SENSEX stale ({sensex_age:.0f}s)")
    if symbol_gap > MAX_SYMBOL_TS_GAP_SECONDS:
        problems.append(f"NIFTY/SENSEX gap too large ({symbol_gap:.0f}s)")

    if problems:
        return "ATTENTION", problems, nifty_ts, sensex_ts

    return "HEALTHY", [], nifty_ts, sensex_ts


def _send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram env vars missing"

    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
    }
    url = base_url + "?" + urllib.parse.urlencode(payload)

    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            body = response.read().decode("utf-8", errors="ignore")
        return True, body
    except Exception as exc:
        return False, str(exc)


def _local_alert():
    try:
        import winsound
        winsound.Beep(1000, 500)
        winsound.Beep(1200, 500)
        winsound.Beep(1500, 700)
        return
    except Exception:
        pass

    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


def _build_message(status, problems, nifty_row, sensex_row, nifty_ts, sensex_ts):
    nifty_action = nifty_row.get("action") if nifty_row else None
    sensex_action = sensex_row.get("action") if sensex_row else None

    lines = [
        f"GAMMA ENGINE ALERT: {status}",
        f"NIFTY last cycle: {_format_ist(nifty_ts)} | action={nifty_action}",
        f"SENSEX last cycle: {_format_ist(sensex_ts)} | action={sensex_action}",
    ]

    if problems:
        lines.append("Issues:")
        for p in problems:
            lines.append(f"- {p}")

    return "\n".join(lines)


def main():
    sb = SupabaseClient()
    now_utc = datetime.now(timezone.utc)

    nifty_row = _latest_signal_row(sb, "NIFTY")
    sensex_row = _latest_signal_row(sb, "SENSEX")

    status, problems, nifty_ts, sensex_ts = _status_from_rows(now_utc, nifty_row, sensex_row)

    print(f"GAMMA ENGINE STATUS: {status}")
    print(f"Last NIFTY cycle: {_format_ist(nifty_ts)}")
    print(f"Last SENSEX cycle: {_format_ist(sensex_ts)}")

    if problems:
        print("Notes:")
        for p in problems:
            print(f"- {p}")

    if status == "HEALTHY":
        return

    _local_alert()

    message = _build_message(
        status=status,
        problems=problems,
        nifty_row=nifty_row,
        sensex_row=sensex_row,
        nifty_ts=nifty_ts,
        sensex_ts=sensex_ts,
    )

    ok, detail = _send_telegram(message)

    if ok:
        print("Telegram alert sent.")
    else:
        print(f"Telegram alert failed: {detail}")


if __name__ == "__main__":
    main()