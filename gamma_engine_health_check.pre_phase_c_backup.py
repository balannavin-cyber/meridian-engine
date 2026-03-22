from datetime import datetime, timedelta, timezone
from core.supabase_client import SupabaseClient

IST = timezone(timedelta(hours=5, minutes=30))

MAX_CYCLE_AGE_SECONDS = 420
MAX_SYMBOL_TS_GAP_SECONDS = 180


def _parse_ts(ts):
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _format_ist(ts):
    if ts is None:
        return "None"
    return ts.astimezone(IST).strftime("%H:%M:%S IST")


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


def _latest_signal_ts(sb, symbol):
    row = _get_latest_row(sb, "signal_snapshots", symbol)
    if not row:
        return None
    return _parse_ts(row.get("ts"))


def _status_from_lags(now_utc, nifty_ts, sensex_ts):
    problems = []

    if nifty_ts is None:
        problems.append("NIFTY missing")
    if sensex_ts is None:
        problems.append("SENSEX missing")

    if problems:
        return "DOWN", problems

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
        return "ATTENTION", problems

    return "HEALTHY", []


def _next_5min_boundary_ist(now_ist):
    floored_minute = (now_ist.minute // 5) * 5
    floored = now_ist.replace(minute=floored_minute, second=0, microsecond=0)
    if floored <= now_ist:
        floored = floored + timedelta(minutes=5)
    return floored


def main():
    sb = SupabaseClient()
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(IST)

    nifty_ts = _latest_signal_ts(sb, "NIFTY")
    sensex_ts = _latest_signal_ts(sb, "SENSEX")

    status, problems = _status_from_lags(now_utc, nifty_ts, sensex_ts)
    next_cycle_ist = _next_5min_boundary_ist(now_ist)

    print(f"GAMMA ENGINE STATUS: {status}")
    print(f"Last NIFTY cycle: {_format_ist(nifty_ts)}")
    print(f"Last SENSEX cycle: {_format_ist(sensex_ts)}")
    print(f"Next expected cycle: {next_cycle_ist.strftime('%H:%M:%S IST')}")

    if problems:
        print("Notes:")
        for problem in problems:
            print(f"- {problem}")


if __name__ == "__main__":
    main()