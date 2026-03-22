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


def fetch_shadow_rows_for_ist_date(replay_date: str) -> List[Dict[str, Any]]:
    # We fetch a broad UTC window and filter locally by IST date.
    start_utc = datetime.strptime(replay_date, "%Y-%m-%d").replace(tzinfo=IST).astimezone(UTC) - timedelta(hours=6)
    end_utc = start_utc + timedelta(days=2)

    params = {
        "select": "symbol,ts,action,confidence_score,live_action,live_confidence,created_at",
        "ts": f"gte.{start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "order": "created_at.desc",
        "limit": "1000",
    }
    rows = supabase_select("shadow_signal_snapshots_v3", params)

    filtered: List[Dict[str, Any]] = []
    for row in rows:
        ts = parse_ts(row.get("ts"))
        if ts is None:
            continue
        if ts.astimezone(IST).date().isoformat() == replay_date:
            filtered.append(row)

    return filtered


def dedupe_shadow_rows_latest(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for row in rows:
        symbol = row.get("symbol")
        ts = row.get("ts")
        created_at = parse_ts(row.get("created_at"))
        if not symbol or not ts or created_at is None:
            continue

        key = (str(symbol), str(ts))
        existing = latest_by_key.get(key)
        if existing is None:
            latest_by_key[key] = row
            continue

        existing_created_at = parse_ts(existing.get("created_at"))
        if existing_created_at is None or created_at > existing_created_at:
            latest_by_key[key] = row

    deduped = list(latest_by_key.values())
    deduped.sort(key=lambda r: (str(r.get("symbol")), str(r.get("ts"))))
    return deduped


def fetch_ohlc_rows_for_horizon(symbol: str, base_ts: datetime, max_minutes: int = 90) -> List[Dict[str, Any]]:
    start_ts = base_ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = supabase_select(
        "intraday_ohlc",
        {
            "select": "symbol,ts,close",
            "symbol": f"eq.{symbol}",
            "ts": f"gte.{start_ts}",
            "order": "ts.asc",
            "limit": "500",
        },
    )

    cutoff = base_ts + timedelta(minutes=max_minutes)
    filtered: List[Dict[str, Any]] = []
    for r in rows:
        ts = parse_ts(r.get("ts"))
        if ts is None:
            continue
        if ts <= cutoff:
            filtered.append(r)
    return filtered


def find_price_at_or_after(rows: List[Dict[str, Any]], target_ts: datetime) -> Optional[float]:
    for r in rows:
        ts = parse_ts(r.get("ts"))
        close = to_float(r.get("close"))
        if ts is None or close is None:
            continue
        if ts >= target_ts:
            return close
    return None


def has_horizon(rows: List[Dict[str, Any]], target_ts: datetime) -> bool:
    for r in rows:
        ts = parse_ts(r.get("ts"))
        if ts is None:
            continue
        if ts >= target_ts:
            return True
    return False


def classify_outcome(action: Optional[str], entry: Optional[float], future: Optional[float]) -> Optional[str]:
    if action is None or entry is None or future is None or entry == 0:
        return None

    move = (future - entry) / entry

    if action == "BUY_PE":
        return "WIN" if move < 0 else "LOSS"
    if action == "BUY_CE":
        return "WIN" if move > 0 else "LOSS"
    if action == "DO_NOTHING":
        return "NA"
    return None


def build_replay_row(shadow_row: Dict[str, Any], replay_date: str, require_min_horizon_minutes: int = 15) -> Optional[Dict[str, Any]]:
    symbol = str(shadow_row.get("symbol"))
    ts = parse_ts(shadow_row.get("ts"))
    created_at = parse_ts(shadow_row.get("created_at"))

    if not symbol or ts is None:
        return None

    spot_rows = fetch_ohlc_rows_for_horizon(symbol, ts, max_minutes=90)
    entry_spot = find_price_at_or_after(spot_rows, ts) if spot_rows else None

    target_5m = ts + timedelta(minutes=5)
    target_15m = ts + timedelta(minutes=15)
    target_30m = ts + timedelta(minutes=30)
    target_60m = ts + timedelta(minutes=60)

    horizon_5m_available = has_horizon(spot_rows, target_5m) if spot_rows else False
    horizon_15m_available = has_horizon(spot_rows, target_15m) if spot_rows else False
    horizon_30m_available = has_horizon(spot_rows, target_30m) if spot_rows else False
    horizon_60m_available = has_horizon(spot_rows, target_60m) if spot_rows else False

    if entry_spot is None:
        return {
            "replay_date": replay_date,
            "symbol": symbol,
            "ts": ts.isoformat(),
            "shadow_action": shadow_row.get("action"),
            "shadow_confidence": to_float(shadow_row.get("confidence_score")),
            "live_action": shadow_row.get("live_action"),
            "live_confidence": to_float(shadow_row.get("live_confidence")),
            "source_shadow_created_at": created_at.isoformat() if created_at else None,
            "entry_spot": None,
            "spot_5m": None,
            "spot_15m": None,
            "spot_30m": None,
            "spot_60m": None,
            "ret_5m": None,
            "ret_15m": None,
            "ret_30m": None,
            "ret_60m": None,
            "outcome_5m": None,
            "outcome_15m": None,
            "outcome_30m": None,
            "outcome_60m": None,
            "horizon_5m_available": False,
            "horizon_15m_available": False,
            "horizon_30m_available": False,
            "horizon_60m_available": False,
            "evaluation_status": "SKIPPED_NO_ENTRY",
        }

    if require_min_horizon_minutes == 15 and not horizon_15m_available:
        return {
            "replay_date": replay_date,
            "symbol": symbol,
            "ts": ts.isoformat(),
            "shadow_action": shadow_row.get("action"),
            "shadow_confidence": to_float(shadow_row.get("confidence_score")),
            "live_action": shadow_row.get("live_action"),
            "live_confidence": to_float(shadow_row.get("live_confidence")),
            "source_shadow_created_at": created_at.isoformat() if created_at else None,
            "entry_spot": round(entry_spot, 6),
            "spot_5m": None,
            "spot_15m": None,
            "spot_30m": None,
            "spot_60m": None,
            "ret_5m": None,
            "ret_15m": None,
            "ret_30m": None,
            "ret_60m": None,
            "outcome_5m": None,
            "outcome_15m": None,
            "outcome_30m": None,
            "outcome_60m": None,
            "horizon_5m_available": horizon_5m_available,
            "horizon_15m_available": horizon_15m_available,
            "horizon_30m_available": horizon_30m_available,
            "horizon_60m_available": horizon_60m_available,
            "evaluation_status": "SKIPPED_INSUFFICIENT_HORIZON",
        }

    spot_5m = find_price_at_or_after(spot_rows, target_5m) if horizon_5m_available else None
    spot_15m = find_price_at_or_after(spot_rows, target_15m) if horizon_15m_available else None
    spot_30m = find_price_at_or_after(spot_rows, target_30m) if horizon_30m_available else None
    spot_60m = find_price_at_or_after(spot_rows, target_60m) if horizon_60m_available else None

    def calc_ret(future_price: Optional[float]) -> Optional[float]:
        if future_price is None or entry_spot == 0:
            return None
        return (future_price - entry_spot) / entry_spot

    ret_5m = calc_ret(spot_5m)
    ret_15m = calc_ret(spot_15m)
    ret_30m = calc_ret(spot_30m)
    ret_60m = calc_ret(spot_60m)

    action = shadow_row.get("action")

    return {
        "replay_date": replay_date,
        "symbol": symbol,
        "ts": ts.isoformat(),
        "shadow_action": action,
        "shadow_confidence": to_float(shadow_row.get("confidence_score")),
        "live_action": shadow_row.get("live_action"),
        "live_confidence": to_float(shadow_row.get("live_confidence")),
        "source_shadow_created_at": created_at.isoformat() if created_at else None,

        "entry_spot": round(entry_spot, 6),

        "spot_5m": round(spot_5m, 6) if spot_5m is not None else None,
        "spot_15m": round(spot_15m, 6) if spot_15m is not None else None,
        "spot_30m": round(spot_30m, 6) if spot_30m is not None else None,
        "spot_60m": round(spot_60m, 6) if spot_60m is not None else None,

        "ret_5m": round(ret_5m, 12) if ret_5m is not None else None,
        "ret_15m": round(ret_15m, 12) if ret_15m is not None else None,
        "ret_30m": round(ret_30m, 12) if ret_30m is not None else None,
        "ret_60m": round(ret_60m, 12) if ret_60m is not None else None,

        "outcome_5m": classify_outcome(action, entry_spot, spot_5m),
        "outcome_15m": classify_outcome(action, entry_spot, spot_15m),
        "outcome_30m": classify_outcome(action, entry_spot, spot_30m),
        "outcome_60m": classify_outcome(action, entry_spot, spot_60m),

        "horizon_5m_available": horizon_5m_available,
        "horizon_15m_available": horizon_15m_available,
        "horizon_30m_available": horizon_30m_available,
        "horizon_60m_available": horizon_60m_available,

        "evaluation_status": "EVALUATED",
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python replay_shadow_for_date_local.py YYYY-MM-DD")
        return 1

    replay_date = sys.argv[1]
    try:
        datetime.strptime(replay_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        return 1

    print("========================================================================")
    print("MERDIAN - replay_shadow_for_date_local")
    print("========================================================================")
    print(f"Replay date (IST): {replay_date}")

    raw_shadow_rows = fetch_shadow_rows_for_ist_date(replay_date)
    print(f"Fetched raw shadow rows for date: {len(raw_shadow_rows)}")

    shadow_rows = dedupe_shadow_rows_latest(raw_shadow_rows)
    print(f"Deduped shadow rows for date: {len(shadow_rows)}")

    out_rows: List[Dict[str, Any]] = []

    for shadow_row in shadow_rows:
        symbol = shadow_row.get("symbol")
        ts = shadow_row.get("ts")
        created_at = shadow_row.get("created_at")
        print("------------------------------------------------------------------------")
        print(f"Replaying {symbol} @ {ts} | shadow_created_at={created_at}")

        out = build_replay_row(shadow_row, replay_date, require_min_horizon_minutes=15)
        if out is None:
            print("No replay row produced.")
            continue

        out_rows.append(out)
        for k, v in out.items():
            print(f"{k}={v}")

    if not out_rows:
        print("No replay rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Writing rows to public.shadow_replay_v1 ...")
    inserted = supabase_insert("shadow_replay_v1", out_rows)
    print(f"Inserted rows returned by Supabase: {len(inserted)}")
    print("REPLAY SHADOW FOR DATE COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())