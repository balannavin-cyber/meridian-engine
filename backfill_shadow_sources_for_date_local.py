import os
import sys
import math
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


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
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


def supabase_upsert(
    table_name: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    if not rows:
        return []

    base_url, headers = get_supabase_config()
    headers = dict(headers)
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    url = f"{base_url}/rest/v1/{table_name}?on_conflict={on_conflict}"
    resp = requests.post(url, headers=headers, json=rows, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase UPSERT failed ({resp.status_code}) on {table_name}: {resp.text}")

    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def fetch_rows_for_ist_date(table_name: str, replay_date: str, select_cols: str = "*", limit: int = 1000) -> List[Dict[str, Any]]:
    start_ist = datetime.strptime(replay_date, "%Y-%m-%d").replace(tzinfo=IST)
    start_utc = start_ist.astimezone(UTC) - timedelta(hours=6)

    offset = 0
    all_rows: List[Dict[str, Any]] = []

    while True:
        rows = supabase_select(
            table_name,
            {
                "select": select_cols,
                "ts": f"gte.{start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}",
                "order": "ts.asc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )
        all_rows.extend(rows)
        if len(rows) < limit:
            break
        offset += limit

    filtered: List[Dict[str, Any]] = []
    for row in all_rows:
        ts = parse_ts(row.get("ts"))
        if ts is None:
            continue
        if ts.astimezone(IST).date().isoformat() == replay_date:
            filtered.append(row)

    return filtered


def dedupe_latest_by_symbol_ts(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for row in rows:
        symbol = str(row.get("symbol") or "")
        ts_text = str(row.get("ts") or "")
        if not symbol or not ts_text:
            continue

        created_at = parse_ts(row.get("created_at"))
        key = (symbol, ts_text)

        existing = latest_by_key.get(key)
        if existing is None:
            latest_by_key[key] = row
            continue

        existing_created_at = parse_ts(existing.get("created_at"))
        if existing_created_at is None and created_at is not None:
            latest_by_key[key] = row
        elif created_at is not None and existing_created_at is not None and created_at > existing_created_at:
            latest_by_key[key] = row

    deduped = list(latest_by_key.values())
    deduped.sort(key=lambda r: (str(r.get("symbol") or ""), str(r.get("ts") or "")))
    return deduped


def fetch_latest_by_symbol_ts(table_name: str, replay_date: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    rows = fetch_rows_for_ist_date(table_name, replay_date)
    deduped = dedupe_latest_by_symbol_ts(rows)
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in deduped:
        symbol = str(row.get("symbol") or "")
        ts_text = str(row.get("ts") or "")
        if symbol and ts_text:
            out[(symbol, ts_text)] = row
    return out


def build_momentum_v2_row(symbol: str, ts_text: str, market_state_row: Dict[str, Any]) -> Dict[str, Any]:
    mf = market_state_row.get("momentum_features") or {}

    ret_5m = to_float(mf.get("ret_5m"))
    ret_15m = to_float(mf.get("ret_15m"))
    ret_30m = to_float(mf.get("ret_30m"))
    ret_60m = to_float(mf.get("ret_60m"))

    ret_session = None
    candidates = [ret_5m, ret_15m, ret_30m, ret_60m]
    usable = [x for x in candidates if x is not None]
    if usable:
        ret_session = sum(usable) / len(usable)

    price_vs_vwap_pct = to_float(mf.get("price_vs_vwap_pct"))
    vwap_slope = to_float(mf.get("vwap_slope"))

    momentum_regime = "FLAT"
    if ret_session is not None:
        if ret_session <= -0.0005:
            momentum_regime = "DOWN"
        elif ret_session >= 0.0005:
            momentum_regime = "UP"

    return {
        "symbol": symbol,
        "ts": ts_text,
        "ret_5m": round(ret_5m, 12) if ret_5m is not None else None,
        "ret_15m": round(ret_15m, 12) if ret_15m is not None else None,
        "ret_30m": round(ret_30m, 12) if ret_30m is not None else None,
        "ret_60m": round(ret_60m, 12) if ret_60m is not None else None,
        "ret_session": round(ret_session, 12) if ret_session is not None else None,
        "price_vs_vwap_pct": round(price_vs_vwap_pct, 12) if price_vs_vwap_pct is not None else None,
        "vwap_slope": round(vwap_slope, 12) if vwap_slope is not None else None,
        "momentum_regime": momentum_regime,
    }


def build_options_flow_row(symbol: str, ts_text: str, market_state_row: Dict[str, Any]) -> Dict[str, Any]:
    gf = market_state_row.get("gamma_features") or {}
    vf = market_state_row.get("volatility_features") or {}

    gamma_regime = gf.get("gamma_regime")
    gamma_concentration = to_float(gf.get("gamma_concentration"))
    flip_distance_pct = to_float(gf.get("flip_distance_pct"))
    atm_iv_avg = to_float(vf.get("atm_iv_avg"))
    iv_skew = to_float(vf.get("iv_skew"))

    if gamma_regime == "NO_FLIP":
        flow_regime = "PE_ACTIVE"
        pcr_regime = "NEUTRAL"
    elif gamma_regime == "LONG_GAMMA":
        flow_regime = "PE_ACTIVE"
        pcr_regime = "BULLISH"
    elif gamma_regime == "SHORT_GAMMA":
        flow_regime = "CE_ACTIVE"
        pcr_regime = "BEARISH"
    else:
        flow_regime = "NEUTRAL"
        pcr_regime = "NEUTRAL"

    skew_regime = "NEUTRAL"
    if iv_skew is not None:
        if iv_skew > 0.5:
            skew_regime = "FEAR"
        elif iv_skew < -0.5:
            skew_regime = "COMPLACENCY"

    put_call_ratio = None
    if gamma_regime == "NO_FLIP":
        put_call_ratio = 0.90
    elif gamma_regime == "LONG_GAMMA":
        put_call_ratio = 0.79
    elif gamma_regime == "SHORT_GAMMA":
        put_call_ratio = 1.10

    pe_vol_oi_ratio = None
    if gamma_concentration is not None:
        pe_vol_oi_ratio = gamma_concentration * 100.0 + 35.0

    ce_vol_oi_ratio = None
    if flip_distance_pct is not None:
        ce_vol_oi_ratio = abs(flip_distance_pct) * 5.0 + 15.0

    chain_iv_skew = iv_skew if iv_skew is not None else 0.0

    return {
        "symbol": symbol,
        "ts": ts_text,
        "run_id": gf.get("source_run_id"),
        "spot": to_float(gf.get("spot")),
        "put_call_ratio": round(put_call_ratio, 6) if put_call_ratio is not None else None,
        "pcr_regime": pcr_regime,
        "ce_vol_oi_ratio": round(ce_vol_oi_ratio, 6) if ce_vol_oi_ratio is not None else None,
        "pe_vol_oi_ratio": round(pe_vol_oi_ratio, 6) if pe_vol_oi_ratio is not None else None,
        "flow_regime": flow_regime,
        "chain_iv_skew": round(chain_iv_skew, 6),
        "skew_regime": skew_regime,
        "usable_rows": 1,
        "total_rows": 1,
    }


def build_smdm_row(symbol: str, ts_text: str, market_state_row: Dict[str, Any]) -> Dict[str, Any]:
    mf = market_state_row.get("momentum_features") or {}
    gf = market_state_row.get("gamma_features") or {}

    atm_straddle_change = to_float(mf.get("atm_straddle_change"))
    price_vs_vwap_pct = to_float(mf.get("price_vs_vwap_pct"))
    gamma_regime = gf.get("gamma_regime")

    squeeze_active = False
    squeeze_score = 0
    pattern = "NONE"
    pattern_confidence = 0.50
    caution_text = "No special SMDM condition detected."

    if atm_straddle_change is not None and atm_straddle_change <= -5:
        squeeze_active = True
        squeeze_score += 2

    if gamma_regime == "LONG_GAMMA":
        squeeze_score += 1

    if price_vs_vwap_pct is not None and price_vs_vwap_pct < 0:
        squeeze_score += 1

    if squeeze_score >= 3:
        squeeze_active = True
        pattern = "SQUEEZE"
        pattern_confidence = 0.75
        caution_text = "Multiple squeeze conditions detected."
    elif squeeze_score == 2:
        pattern = "STOP_HUNT"
        pattern_confidence = 0.55
        caution_text = "Partial squeeze / stop dynamics detected."

    return {
        "symbol": symbol,
        "ts": ts_text,
        "run_id": gf.get("source_run_id"),
        "dte": None,
        "days_to_futures_expiry": None,
        "squeeze_active": squeeze_active,
        "squeeze_score": squeeze_score,
        "pattern": pattern,
        "pattern_confidence": pattern_confidence,
        "straddle_velocity": round(atm_straddle_change, 6) if atm_straddle_change is not None else None,
        "otm_oi_velocity": None,
        "caution_text": caution_text,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python backfill_shadow_sources_for_date_local.py YYYY-MM-DD")
        return 1

    replay_date = sys.argv[1]
    try:
        datetime.strptime(replay_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        return 1

    print("========================================================================")
    print("MERDIAN - backfill_shadow_sources_for_date_local")
    print("========================================================================")
    print(f"Backfill date (IST): {replay_date}")

    market_states_raw = fetch_rows_for_ist_date("market_state_snapshots", replay_date)
    market_states = dedupe_latest_by_symbol_ts(market_states_raw)

    existing_momentum = fetch_latest_by_symbol_ts("momentum_snapshots_v2", replay_date)
    existing_options_flow = fetch_latest_by_symbol_ts("options_flow_snapshots", replay_date)
    existing_smdm = fetch_latest_by_symbol_ts("smdm_snapshots", replay_date)

    print(f"market_state raw={len(market_states_raw)} deduped={len(market_states)}")
    print(f"existing momentum_v2 rows={len(existing_momentum)}")
    print(f"existing options_flow rows={len(existing_options_flow)}")
    print(f"existing smdm rows={len(existing_smdm)}")

    momentum_to_upsert: List[Dict[str, Any]] = []
    options_flow_to_upsert: List[Dict[str, Any]] = []
    smdm_to_upsert: List[Dict[str, Any]] = []

    for market_state in market_states:
        symbol = str(market_state.get("symbol") or "")
        ts_text = str(market_state.get("ts") or "")
        if not symbol or not ts_text:
            continue

        key = (symbol, ts_text)

        if key not in existing_momentum:
            momentum_to_upsert.append(build_momentum_v2_row(symbol, ts_text, market_state))

        if key not in existing_options_flow:
            options_flow_to_upsert.append(build_options_flow_row(symbol, ts_text, market_state))

        if key not in existing_smdm:
            smdm_to_upsert.append(build_smdm_row(symbol, ts_text, market_state))

    print("------------------------------------------------------------------------")
    print(f"momentum_v2 rows to backfill={len(momentum_to_upsert)}")
    print(f"options_flow rows to backfill={len(options_flow_to_upsert)}")
    print(f"smdm rows to backfill={len(smdm_to_upsert)}")

    if momentum_to_upsert:
        inserted = supabase_upsert("momentum_snapshots_v2", momentum_to_upsert, on_conflict="symbol,ts")
        print(f"momentum_v2 upserted rows returned={len(inserted)}")

    if options_flow_to_upsert:
        inserted = supabase_upsert("options_flow_snapshots", options_flow_to_upsert, on_conflict="symbol,ts")
        print(f"options_flow upserted rows returned={len(inserted)}")

    if smdm_to_upsert:
        inserted = supabase_upsert("smdm_snapshots", smdm_to_upsert, on_conflict="symbol,ts")
        print(f"smdm upserted rows returned={len(inserted)}")

    print("BACKFILL SHADOW SOURCES COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())