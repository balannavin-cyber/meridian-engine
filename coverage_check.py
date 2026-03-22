import os
import sys
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


def get_eod_coverage() -> Tuple[Optional[str], int, int, float]:
    rows = get_json(table_url("breadth_coverage_latest"))
    if not rows:
        return None, 0, 0, 0.0

    row = rows[0]
    return (
        row.get("trade_date"),
        int(row.get("tickers_with_eod") or 0),
        int(row.get("active_universe") or 0),
        float(row.get("coverage_pct") or 0.0),
    )


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

    eod_date, eod_have, eod_total, eod_pct = get_eod_coverage()
    print(f"EOD coverage date  : {eod_date}")
    print(f"EOD coverage       : {eod_have}/{eod_total} = {eod_pct:.2f}% [{classify(eod_pct)}]")

    ltp_ts, ltp_have, ltp_total, ltp_pct = get_intraday_ltp_coverage(active_universe)
    print(f"Intraday LTP ts    : {ltp_ts}")
    print(f"Intraday LTP       : {ltp_have}/{ltp_total} = {ltp_pct:.2f}% [{classify(ltp_pct)}]")

    bts, breadth_have, breadth_total, breadth_pct = get_intraday_breadth_coverage(active_universe)
    print(f"Intraday breadth ts: {bts}")
    print(f"Intraday breadth   : {breadth_have}/{breadth_total} = {breadth_pct:.2f}% [{classify(breadth_pct)}]")


if __name__ == "__main__":
    main()