from __future__ import annotations

import math
import os
import sys
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


def supabase_upsert(
    table_name: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    """
    UPSERT rows into Supabase using merge-duplicates resolution.
    Replaces the previous INSERT which caused duplicate key errors when
    both NIFTY and SENSEX cycles ran within the same timestamp bucket.
    Conflict key: symbol,ts (uq_momentum_snapshots_v2_symbol_ts)
    """
    if not rows:
        return []

    base_url, headers = get_supabase_config()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    url = f"{base_url}/rest/v1/{table_name}"
    resp = requests.post(
        url,
        headers=headers,
        json=rows,
        params={"on_conflict": on_conflict},
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase UPSERT failed ({resp.status_code}) on {table_name}: {resp.text}")
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def fetch_recent_spot_rows(symbol: str, hours_back: int = 8) -> List[Dict[str, Any]]:
    since = (utc_now() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = supabase_select(
        "market_spot_snapshots",
        {
            "select": "ts,symbol,spot,created_at",
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{since}",
            "order": "ts.asc",
            "limit": "1000",
        },
    )
    return rows


def fetch_latest_momentum_row(symbol: str) -> Optional[Dict[str, Any]]:
    rows = supabase_select(
        "momentum_snapshots",
        {
            "select": "ts,symbol,ret_5m,ret_15m,ret_30m,ret_60m,price_vs_vwap_pct,vwap_slope,atm_straddle_change,source,created_at",
            "symbol": f"eq.{symbol}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def get_session_open_price(rows: List[Dict[str, Any]]) -> Optional[float]:
    if not rows:
        return None

    by_ist_date: Dict[str, List[Tuple[datetime, float]]] = {}
    for r in rows:
        ts = parse_ts(r.get("ts"))
        spot = to_float(r.get("spot"))
        if ts is None or spot is None:
            continue
        d = ts.astimezone(IST).date().isoformat()
        by_ist_date.setdefault(d, []).append((ts, spot))

    if not by_ist_date:
        return None

    latest_date = sorted(by_ist_date.keys())[-1]
    same_day = sorted(by_ist_date[latest_date], key=lambda x: x[0])
    return same_day[0][1] if same_day else None


def get_latest_spot(rows: List[Dict[str, Any]]) -> Tuple[Optional[datetime], Optional[float]]:
    valid = []
    for r in rows:
        ts = parse_ts(r.get("ts"))
        spot = to_float(r.get("spot"))
        if ts is not None and spot is not None:
            valid.append((ts, spot))
    if not valid:
        return None, None
    latest = sorted(valid, key=lambda x: x[0])[-1]
    return latest


def classify_momentum_regime(
    ret_5m: Optional[float],
    ret_15m: Optional[float],
    ret_30m: Optional[float],
    ret_60m: Optional[float],
    ret_session: Optional[float],
) -> str:
    weights = {
        "ret_5m": 1.0,
        "ret_15m": 1.5,
        "ret_30m": 2.0,
        "ret_60m": 2.5,
        "ret_session": 3.0,
    }

    values = {
        "ret_5m": ret_5m,
        "ret_15m": ret_15m,
        "ret_30m": ret_30m,
        "ret_60m": ret_60m,
        "ret_session": ret_session,
    }

    score = 0.0
    total_weight = 0.0

    for key, val in values.items():
        if val is None:
            continue
        w = weights[key]
        total_weight += w
        if val > 0:
            score += w
        elif val < 0:
            score -= w

    if total_weight == 0:
        return "NEUTRAL"

    normalized = score / total_weight
    if normalized >= 0.25:
        return "UP"
    if normalized <= -0.25:
        return "DOWN"
    return "NEUTRAL"


def build_row(symbol: str) -> Optional[Dict[str, Any]]:
    live_row = fetch_latest_momentum_row(symbol)
    if not live_row:
        print(f"No live momentum row found for {symbol}")
        return None

    spot_rows = fetch_recent_spot_rows(symbol, hours_back=8)
    if not spot_rows:
        print(f"No spot history found for {symbol}")
        return None

    latest_ts = parse_ts(live_row.get("ts"))
    if latest_ts is None:
        latest_ts = parse_ts(live_row.get("created_at"))
    if latest_ts is None:
        latest_ts = utc_now()

    _, latest_spot = get_latest_spot(spot_rows)
    session_open_spot = get_session_open_price(spot_rows)

    ret_session = None
    if latest_spot is not None and session_open_spot not in (None, 0):
        ret_session = (latest_spot - session_open_spot) / session_open_spot

    ret_5m = to_float(live_row.get("ret_5m"))
    ret_15m = to_float(live_row.get("ret_15m"))
    ret_30m = to_float(live_row.get("ret_30m"))
    ret_60m = to_float(live_row.get("ret_60m"))
    price_vs_vwap_pct = to_float(live_row.get("price_vs_vwap_pct"))
    vwap_slope = to_float(live_row.get("vwap_slope"))

    momentum_regime = classify_momentum_regime(
        ret_5m=ret_5m,
        ret_15m=ret_15m,
        ret_30m=ret_30m,
        ret_60m=ret_60m,
        ret_session=ret_session,
    )

    row = {
        "ts": latest_ts.isoformat(),
        "symbol": symbol,
        "ret_5m": round(ret_5m, 12) if ret_5m is not None else None,
        "ret_15m": round(ret_15m, 12) if ret_15m is not None else None,
        "ret_30m": round(ret_30m, 12) if ret_30m is not None else None,
        "ret_60m": round(ret_60m, 12) if ret_60m is not None else None,
        "ret_session": round(ret_session, 12) if ret_session is not None else None,
        "price_vs_vwap_pct": round(price_vs_vwap_pct, 12) if price_vs_vwap_pct is not None else None,
        "vwap_slope": round(vwap_slope, 12) if vwap_slope is not None else None,
        "momentum_regime": momentum_regime,
    }
    return row


def main() -> int:
    print("========================================================================")
    print("MERDIAN - compute_momentum_features_v2_local")
    print("========================================================================")

    out_rows: List[Dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        print("------------------------------------------------------------------------")
        print(f"Building momentum v2 row for {symbol}")
        row = build_row(symbol)
        if row is None:
            continue
        out_rows.append(row)
        for k, v in row.items():
            print(f"{k}={v}")

    if not out_rows:
        print("No output rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Writing rows to public.momentum_snapshots_v2 ...")
    inserted = supabase_upsert("momentum_snapshots_v2", out_rows, on_conflict="symbol,ts")
    print(f"Upserted rows returned by Supabase: {len(inserted)}")
    print("COMPUTE MOMENTUM FEATURES V2 COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())