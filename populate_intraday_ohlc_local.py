from __future__ import annotations

import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_supabase_config() -> Tuple[str, Dict[str, str]]:
    url = get_env("SUPABASE_URL").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY fallback).")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    return url, headers


def supabase_select(
    table_name: str,
    params: Dict[str, str],
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    base_url, headers = get_supabase_config()
    url = f"{base_url}/rest/v1/{table_name}?{urlencode(params)}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase SELECT failed ({resp.status_code}) on {table_name}: {resp.text}")
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected SELECT response type from {table_name}: {type(data)}")
    return data


def supabase_insert(table_name: str, rows: List[Dict[str, Any]], timeout: int = 60) -> List[Dict[str, Any]]:
    if not rows:
        return []

    base_url, headers = get_supabase_config()
    url = f"{base_url}/rest/v1/{table_name}"
    resp = requests.post(url, headers=headers, json=rows, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase INSERT failed ({resp.status_code}) on {table_name}: {resp.text}")

    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def fetch_recent_spot_rows(symbol: str, days_back: int = 5) -> List[Dict[str, Any]]:
    since = (utc_now() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: List[Dict[str, Any]] = []
    offset = 0
    limit = 1000

    while True:
        batch = supabase_select(
            "market_spot_snapshots",
            {
                "select": "ts,symbol,spot,created_at",
                "symbol": f"eq.{symbol}",
                "ts": f"gte.{since}",
                "order": "ts.asc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    return rows


def floor_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def ist_session_date(dt_utc: datetime) -> str:
    return dt_utc.astimezone(IST).date().isoformat()


def bucket_rows_to_1m(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, datetime], List[Tuple[datetime, float]]]:
    buckets: Dict[Tuple[str, datetime], List[Tuple[datetime, float]]] = defaultdict(list)

    for r in rows:
        ts = parse_ts(r.get("ts"))
        spot = to_float(r.get("spot"))
        symbol = r.get("symbol")
        if ts is None or spot is None or not symbol:
            continue

        minute_bucket = floor_to_minute(ts)
        key = (str(symbol), minute_bucket)
        buckets[key].append((ts, spot))

    return buckets


def build_ohlc_rows(rows: List[Dict[str, Any]], candle_size: int = 1) -> List[Dict[str, Any]]:
    if candle_size != 1:
        raise ValueError("This weekend block currently supports candle_size=1 only.")

    buckets = bucket_rows_to_1m(rows)
    if not buckets:
        return []

    sorted_keys = sorted(buckets.keys(), key=lambda x: (x[0], x[1]))

    by_symbol_day: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for symbol, minute_bucket in sorted_keys:
        ticks = sorted(buckets[(symbol, minute_bucket)], key=lambda x: x[0])
        prices = [p for _, p in ticks]
        if not prices:
            continue

        o = prices[0]
        h = max(prices)
        l = min(prices)
        c = prices[-1]

        candle = {
            "ts": minute_bucket.isoformat(),
            "symbol": symbol,
            "open": round(o, 6),
            "high": round(h, 6),
            "low": round(l, 6),
            "close": round(c, 6),
            "volume": None,
            "session_high": None,
            "session_low": None,
            "candle_size": candle_size,
        }

        day_key = (symbol, ist_session_date(minute_bucket))
        by_symbol_day[day_key].append(candle)

    out_rows: List[Dict[str, Any]] = []

    for (symbol, _day), candles in by_symbol_day.items():
        candles.sort(key=lambda x: x["ts"])

        running_high: Optional[float] = None
        running_low: Optional[float] = None

        for candle in candles:
            high = to_float(candle["high"])
            low = to_float(candle["low"])

            if high is not None:
                running_high = high if running_high is None else max(running_high, high)
            if low is not None:
                running_low = low if running_low is None else min(running_low, low)

            candle["session_high"] = round(running_high, 6) if running_high is not None else None
            candle["session_low"] = round(running_low, 6) if running_low is not None else None
            out_rows.append(candle)

    out_rows.sort(key=lambda x: (x["symbol"], x["ts"]))
    return out_rows


def main() -> int:
    print("========================================================================")
    print("MERDIAN - populate_intraday_ohlc_local")
    print("========================================================================")

    all_rows: List[Dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        print("------------------------------------------------------------------------")
        print(f"Fetching spot rows for {symbol}")
        rows = fetch_recent_spot_rows(symbol, days_back=5)
        print(f"Fetched rows: {len(rows)}")
        all_rows.extend(rows)

    if not all_rows:
        print("No spot rows fetched. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Building 1-minute OHLC rows...")
    ohlc_rows = build_ohlc_rows(all_rows, candle_size=1)
    print(f"Prepared OHLC rows: {len(ohlc_rows)}")

    if not ohlc_rows:
        print("No OHLC rows prepared. Exiting with code 1.")
        return 1

    # Print latest few rows per symbol
    latest_by_symbol: Dict[str, Dict[str, Any]] = {}
    for row in ohlc_rows:
        latest_by_symbol[row["symbol"]] = row

    for symbol in ["NIFTY", "SENSEX"]:
        row = latest_by_symbol.get(symbol)
        if row:
            print("------------------------------------------------------------------------")
            print(f"Latest OHLC row for {symbol}")
            for k, v in row.items():
                print(f"{k}={v}")

    print("------------------------------------------------------------------------")
    print("Writing rows to public.intraday_ohlc ...")
    inserted = supabase_insert("intraday_ohlc", ohlc_rows)
    print(f"Inserted rows returned by Supabase: {len(inserted)}")
    print("POPULATE INTRADAY OHLC COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())