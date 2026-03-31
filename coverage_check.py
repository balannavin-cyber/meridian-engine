import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    sys.exit(1)

SUPABASE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

PAGE_SIZE = 1000
COMPLETE_EOD_THRESHOLD_PCT = 95.0
RECENT_EOD_CANDIDATE_DAYS = 10


def table_url(name: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{name}"


def classify(pct: float) -> str:
    if pct >= 98.0:
        return "GREEN"
    if pct >= 95.0:
        return "AMBER"
    return "RED"


def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    r = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"Expected list response from {url}, got: {type(data)}")
    return data


def get_active_universe_count() -> int:
    total = 0
    offset = 0

    while True:
        params = {
            "select": "ticker",
            "exchange": "eq.NSE",
            "is_active": "eq.true",
            "dhan_security_id": "not.is.null",
            "order": "ticker.asc",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        rows = get_json(table_url("dhan_scrip_map"), params=params)
        total += len(rows)

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return total


def get_latest_available_eod_trade_date() -> Optional[str]:
    params = {
        "select": "trade_date",
        "order": "trade_date.desc",
        "limit": "1",
    }
    rows = get_json(table_url("equity_eod"), params=params)
    if not rows:
        return None
    return rows[0].get("trade_date")


def get_recent_eod_rows(start_date: str) -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "select": "ticker,trade_date",
            "trade_date": f"gte.{start_date}",
            "order": "trade_date.desc,ticker.asc",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        rows = get_json(table_url("equity_eod"), params=params)
        all_rows.extend(rows)

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return all_rows


def get_latest_complete_eod_coverage(
    active_universe: int,
) -> Tuple[Optional[str], Optional[str], int, int, float]:
    latest_available = get_latest_available_eod_trade_date()
    if not latest_available:
        return None, None, 0, active_universe, 0.0

    latest_dt = datetime.strptime(latest_available, "%Y-%m-%d").date()
    start_dt = latest_dt - timedelta(days=RECENT_EOD_CANDIDATE_DAYS)
    rows = get_recent_eod_rows(start_dt.isoformat())

    by_date: Dict[str, set[str]] = defaultdict(set)
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        trade_date = str(row.get("trade_date") or "").strip()
        if ticker and trade_date:
            by_date[trade_date].add(ticker)

    candidate_dates = sorted(by_date.keys(), reverse=True)
    selected_date: Optional[str] = None
    selected_count = 0

    for trade_date in candidate_dates:
        count_for_date = len(by_date[trade_date])
        pct = (count_for_date / active_universe * 100.0) if active_universe else 0.0
        if pct >= COMPLETE_EOD_THRESHOLD_PCT:
            selected_date = trade_date
            selected_count = count_for_date
            break

    if selected_date is None:
        latest_count = len(by_date.get(latest_available, set()))
        latest_pct = (latest_count / active_universe * 100.0) if active_universe else 0.0
        return latest_available, None, latest_count, active_universe, round(latest_pct, 2)

    pct = (selected_count / active_universe * 100.0) if active_universe else 0.0
    return latest_available, selected_date, selected_count, active_universe, round(pct, 2)


def get_latest_intraday_ts() -> Optional[str]:
    params = {
        "select": "ts",
        "order": "ts.desc",
        "limit": "1",
    }
    rows = get_json(table_url("equity_intraday_last"), params=params)
    if not rows:
        return None
    return rows[0].get("ts")


def count_intraday_rows_at_ts(ts_value: str) -> int:
    total = 0
    offset = 0

    while True:
        params = {
            "select": "ticker",
            "ts": f"eq.{ts_value}",
            "order": "ticker.asc",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        rows = get_json(table_url("equity_intraday_last"), params=params)
        total += len(rows)

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return total


def get_intraday_ltp_coverage(active_universe: int) -> Tuple[Optional[str], int, int, float]:
    latest_ts = get_latest_intraday_ts()
    if not latest_ts:
        return None, 0, active_universe, 0.0

    count_latest = count_intraday_rows_at_ts(latest_ts)
    pct = (count_latest / active_universe * 100.0) if active_universe else 0.0
    return latest_ts, count_latest, active_universe, round(pct, 2)


def get_intraday_breadth_coverage(active_universe: int) -> Tuple[Optional[str], int, int, float]:
    rows = get_json(table_url("latest_market_breadth_intraday"))
    if not rows:
        return None, 0, active_universe, 0.0

    row = rows[0]
    ts = row.get("ts")
    universe_count = int(row.get("universe_count") or 0)
    pct = (universe_count / active_universe * 100.0) if active_universe else 0.0
    return ts, universe_count, active_universe, round(pct, 2)


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Coverage Check")
    print("=" * 72)

    active_universe = get_active_universe_count()
    print(f"Active mapped NSE universe: {active_universe}")

    latest_available_eod_date, selected_eod_date, eod_have, eod_total, eod_pct = get_latest_complete_eod_coverage(active_universe)
    print(f"Latest available EOD date : {latest_available_eod_date}")
    print(f"Selected EOD coverage date: {selected_eod_date}")
    print(f"EOD coverage              : {eod_have}/{eod_total} = {eod_pct:.2f}% [{classify(eod_pct)}]")

    ltp_ts, ltp_have, ltp_total, ltp_pct = get_intraday_ltp_coverage(active_universe)
    print(f"Intraday LTP ts           : {ltp_ts}")
    print(f"Intraday LTP              : {ltp_have}/{ltp_total} = {ltp_pct:.2f}% [{classify(ltp_pct)}]")

    bts, breadth_have, breadth_total, breadth_pct = get_intraday_breadth_coverage(active_universe)
    print(f"Intraday breadth ts       : {bts}")
    print(f"Intraday breadth          : {breadth_have}/{breadth_total} = {breadth_pct:.2f}% [{classify(breadth_pct)}]")


if __name__ == "__main__":
    main()