from __future__ import annotations

import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


IST_OFFSET = timedelta(hours=5, minutes=30)
IST = timezone(IST_OFFSET)


@dataclass
class DailyIvPoint:
    trade_date_ist: str
    symbol: str
    atm_iv_avg: Optional[float]
    india_vix: Optional[float]


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
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ist_now() -> datetime:
    return utc_now().astimezone(IST)


def ist_date_str(dt_utc: datetime) -> str:
    return dt_utc.astimezone(IST).date().isoformat()


def to_postgrest_utc_z(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_iv_regime(iv_rank: Optional[float]) -> Optional[str]:
    if iv_rank is None:
        return None
    if iv_rank < 25:
        return "IV_LOW"
    if iv_rank < 60:
        return "IV_NORMAL"
    if iv_rank < 80:
        return "IV_ELEVATED"
    return "IV_HIGH"


def classify_vix_trend(vix_5d_avg: Optional[float], vix_20d_avg: Optional[float]) -> Optional[str]:
    if vix_5d_avg is None or vix_20d_avg is None:
        return None
    diff = vix_5d_avg - vix_20d_avg
    if diff > 0.25:
        return "RISING"
    if diff < -0.25:
        return "FALLING"
    return "FLAT"


def percentile_rank(values: List[float], current: float) -> Optional[float]:
    if not values:
        return None
    below_or_equal = sum(1 for v in values if v <= current)
    return round((below_or_equal / len(values)) * 100.0, 4)


def avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


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


def select_all_volatility_rows(days_back: int = 400) -> List[Dict[str, Any]]:
    base_url, headers = get_supabase_config()
    since_utc = utc_now() - timedelta(days=days_back)
    since_iso = to_postgrest_utc_z(since_utc)

    rows: List[Dict[str, Any]] = []
    offset = 0
    limit = 1000

    while True:
        params = {
            "select": "ts,symbol,atm_iv_avg,india_vix",
            "ts": f"gte.{since_iso}",
            "order": "ts.asc",
            "limit": str(limit),
            "offset": str(offset),
        }

        url = f"{base_url}/rest/v1/volatility_snapshots?{urlencode(params)}"

        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Supabase SELECT failed ({resp.status_code}): {resp.text}")

        batch = resp.json()
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected SELECT response type: {type(batch)}")

        rows.extend(batch)

        if len(batch) < limit:
            break

        offset += limit

    return rows


def insert_rows(table_name: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []

    base_url, headers = get_supabase_config()
    url = f"{base_url}/rest/v1/{table_name}"

    resp = requests.post(url, headers=headers, json=rows, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase INSERT failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def build_daily_series(rows: List[Dict[str, Any]]) -> Dict[str, List[DailyIvPoint]]:
    latest_by_symbol_day: Dict[Tuple[str, str], Tuple[datetime, DailyIvPoint]] = {}

    for row in rows:
        symbol = row.get("symbol")
        ts = parse_ts(row.get("ts"))
        if not symbol or ts is None:
            continue

        trade_date = ist_date_str(ts)
        key = (str(symbol), trade_date)

        point = DailyIvPoint(
            trade_date_ist=trade_date,
            symbol=str(symbol),
            atm_iv_avg=to_float(row.get("atm_iv_avg")),
            india_vix=to_float(row.get("india_vix")),
        )

        existing = latest_by_symbol_day.get(key)
        if existing is None or ts > existing[0]:
            latest_by_symbol_day[key] = (ts, point)

    grouped: Dict[str, List[DailyIvPoint]] = defaultdict(list)
    for _, value in latest_by_symbol_day.items():
        point = value[1]
        grouped[point.symbol].append(point)

    for symbol in grouped:
        grouped[symbol].sort(key=lambda x: x.trade_date_ist)

    return grouped


def compute_row_for_symbol(symbol: str, points: List[DailyIvPoint]) -> Optional[Dict[str, Any]]:
    if not points:
        return None

    current = points[-1]
    current_iv = current.atm_iv_avg
    if current_iv is None:
        return None

    iv_values = [p.atm_iv_avg for p in points if p.atm_iv_avg is not None]
    vix_values = [p.india_vix for p in points if p.india_vix is not None]

    if not iv_values:
        return None

    iv_52w_high = max(iv_values)
    iv_52w_low = min(iv_values)

    if iv_52w_high == iv_52w_low:
        iv_rank = 50.0
    else:
        iv_rank = ((current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low)) * 100.0
        iv_rank = max(0.0, min(100.0, iv_rank))

    iv_percentile = percentile_rank(iv_values, current_iv)
    vix_5d_avg = avg(vix_values[-5:]) if vix_values else None
    vix_20d_avg = avg(vix_values[-20:]) if vix_values else None

    history_days = len(iv_values)
    low_confidence = history_days < 60

    ts_ist = datetime.combine(ist_now().date(), time(9, 5), tzinfo=IST)
    ts_utc = ts_ist.astimezone(timezone.utc)

    row = {
        "ts": ts_utc.isoformat(),
        "symbol": symbol,
        "current_atm_iv": round(current_iv, 6),
        "iv_52w_high": round(iv_52w_high, 6),
        "iv_52w_low": round(iv_52w_low, 6),
        "iv_rank": round(iv_rank, 4) if iv_rank is not None else None,
        "iv_percentile": round(iv_percentile, 4) if iv_percentile is not None else None,
        "iv_regime": classify_iv_regime(iv_rank),
        "vix_5d_avg": round(vix_5d_avg, 6) if vix_5d_avg is not None else None,
        "vix_20d_avg": round(vix_20d_avg, 6) if vix_20d_avg is not None else None,
        "vix_trend": classify_vix_trend(vix_5d_avg, vix_20d_avg),
        "history_days": history_days,
        "low_confidence": low_confidence,
    }
    return row


def main() -> int:
    print("========================================================================")
    print("MERDIAN - compute_iv_context_local")
    print("========================================================================")

    rows = select_all_volatility_rows(days_back=400)
    print(f"Fetched volatility rows: {len(rows)}")

    grouped = build_daily_series(rows)
    print(f"Symbols found: {sorted(grouped.keys())}")

    output_rows: List[Dict[str, Any]] = []
    for symbol in sorted(grouped.keys()):
        out = compute_row_for_symbol(symbol, grouped[symbol])
        if out is not None:
            output_rows.append(out)
            print("------------------------------------------------------------------------")
            print(f"Prepared IV context row for {symbol}")
            for k, v in out.items():
                print(f"{k}={v}")

    if not output_rows:
        print("No IV context rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Writing rows to public.iv_context_snapshots ...")
    inserted = insert_rows("iv_context_snapshots", output_rows)
    print(f"Inserted rows returned by Supabase: {len(inserted)}")
    print("COMPUTE IV CONTEXT COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())