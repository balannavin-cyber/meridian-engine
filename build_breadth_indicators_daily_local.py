from __future__ import annotations

import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

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
UNIVERSE_ID = "excel_v1"
LOOKBACK_CALENDAR_DAYS = 120


def jdump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def table_url(name: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{name}"


def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    r = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f"Expected list response from {url}, got: {type(data)}")
    return data


def post_json(url: str, rows: List[Dict[str, Any]], params: Optional[Dict[str, Any]] = None) -> requests.Response:
    headers = dict(SUPABASE_HEADERS)
    headers["Prefer"] = "resolution=merge-duplicates"
    r = requests.post(url, headers=headers, params=params, json=rows, timeout=120)
    r.raise_for_status()
    return r


def get_active_universe() -> List[str]:
    tickers: List[str] = []
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
        print(f"Universe page fetched | offset={offset} | rows={len(rows)}")

        if not rows:
            break

        for row in rows:
            ticker = str(row.get("ticker") or "").strip().upper()
            if ticker:
                tickers.append(ticker)

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return sorted(set(tickers))


def get_latest_eod_trade_date() -> str:
    params = {
        "select": "trade_date",
        "order": "trade_date.desc",
        "limit": "1",
    }
    rows = get_json(table_url("equity_eod"), params=params)
    if not rows or not rows[0].get("trade_date"):
        raise RuntimeError("Could not determine latest trade_date from equity_eod")
    return str(rows[0]["trade_date"])


def get_eod_rows_from_date(start_date: str) -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "select": "ticker,trade_date,close",
            "trade_date": f"gte.{start_date}",
            "order": "ticker.asc,trade_date.asc",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        rows = get_json(table_url("equity_eod"), params=params)
        print(f"EOD page fetched | offset={offset} | rows={len(rows)}")

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return all_rows


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def rolling_mean(values: List[float], window: int) -> Optional[float]:
    if len(values) < window:
        return None
    return sum(values[-window:]) / float(window)


def pct_change(current: float, base: Optional[float]) -> Optional[float]:
    if base is None or base == 0:
        return None
    return ((current / base) - 1.0) * 100.0


def build_daily_rows(
    universe_tickers: List[str],
    latest_trade_date: str,
    eod_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_ticker: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for row in eod_rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        trade_date = str(row.get("trade_date") or "").strip()
        close_val = safe_float(row.get("close"))

        if not ticker or not trade_date or close_val is None:
            continue

        by_ticker[ticker].append(
            {
                "ticker": ticker,
                "trade_date": trade_date,
                "close": close_val,
            }
        )

    out_rows: List[Dict[str, Any]] = []
    missing_tickers: List[str] = []

    for ticker in universe_tickers:
        history = by_ticker.get(ticker, [])
        if not history:
            missing_tickers.append(ticker)
            continue

        history = sorted(history, key=lambda x: x["trade_date"])
        latest_row = history[-1]

        if latest_row["trade_date"] != latest_trade_date:
            # Skip stale tickers for this rebuild date
            continue

        closes = [float(x["close"]) for x in history]
        current_close = closes[-1]
        prev_close = closes[-2] if len(closes) >= 2 else None

        dma10 = rolling_mean(closes, 10)
        dma20 = rolling_mean(closes, 20)
        dma40 = rolling_mean(closes, 40)

        close_21 = closes[-21] if len(closes) >= 21 else None
        close_41 = closes[-41] if len(closes) >= 41 else None

        flag_up4 = False
        flag_dn4 = False
        if prev_close is not None and prev_close != 0:
            day_pct = pct_change(current_close, prev_close)
            flag_up4 = bool(day_pct is not None and day_pct >= 4.0)
            flag_dn4 = bool(day_pct is not None and day_pct <= -4.0)

        m25_pct = pct_change(current_close, close_21)
        m50_pct = pct_change(current_close, close_41)

        row = {
            "universe_id": UNIVERSE_ID,
            "ticker": ticker,
            "trade_date": latest_trade_date,
            "close": current_close,
            "prev_close": prev_close,
            "dma10": dma10,
            "dma20": dma20,
            "dma40": dma40,
            "above_10": bool(dma10 is not None and current_close > dma10),
            "above_20": bool(dma20 is not None and current_close > dma20),
            "above_40": bool(dma40 is not None and current_close > dma40),
            "dma10_gt_20": bool(dma10 is not None and dma20 is not None and dma10 > dma20),
            "dma20_gt_40": bool(dma20 is not None and dma40 is not None and dma20 > dma40),
            "flag_up4": flag_up4,
            "flag_dn4": flag_dn4,
            "flag_up25": bool(m25_pct is not None and m25_pct >= 25.0),
            "flag_dn25": bool(m25_pct is not None and m25_pct <= -25.0),
            "flag_up50": bool(m50_pct is not None and m50_pct >= 50.0),
            "flag_dn50": bool(m50_pct is not None and m50_pct <= -50.0),
        }
        out_rows.append(row)

    print(f"Tickers missing any EOD history: {len(missing_tickers)}")
    return out_rows


def chunk_list(items: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def upsert_breadth_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    url = table_url("breadth_indicators_daily")
    chunks = chunk_list(rows, 500)

    for idx, chunk in enumerate(chunks, start=1):
        post_json(
            url,
            chunk,
            params={"on_conflict": "universe_id,ticker,trade_date"},
        )
        print(f"[OK] upsert chunk {idx}/{len(chunks)} | rows={len(chunk)}")


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Local Python build_breadth_indicators_daily")
    print("=" * 72)

    latest_trade_date = get_latest_eod_trade_date()
    print(f"Latest EOD trade date: {latest_trade_date}")

    latest_dt = datetime.strptime(latest_trade_date, "%Y-%m-%d").date()
    start_dt = latest_dt - timedelta(days=LOOKBACK_CALENDAR_DAYS)
    start_date = start_dt.isoformat()

    universe_tickers = get_active_universe()
    print(f"Active mapped NSE universe: {len(universe_tickers)}")

    eod_rows = get_eod_rows_from_date(start_date)
    print(f"EOD rows fetched for rebuild window: {len(eod_rows)}")

    daily_rows = build_daily_rows(
        universe_tickers=universe_tickers,
        latest_trade_date=latest_trade_date,
        eod_rows=eod_rows,
    )

    print(f"Daily breadth rows prepared: {len(daily_rows)}")
    if daily_rows:
        print("Sample row:")
        print(jdump(daily_rows[0]))

    upsert_breadth_rows(daily_rows)

    print("-" * 72)
    print("BUILD BREADTH INDICATORS DAILY COMPLETED")
    print(f"trade_date rebuilt: {latest_trade_date}")
    print(f"rows upserted     : {len(daily_rows)}")


if __name__ == "__main__":
    main()