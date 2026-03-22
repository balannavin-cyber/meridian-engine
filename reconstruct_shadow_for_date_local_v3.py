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

MOMENTUM_LOOKBACK_MIN = 90
OPTIONS_FLOW_LOOKBACK_MIN = 90
IV_CONTEXT_LOOKBACK_MIN = 1440
SMDM_LOOKBACK_MIN = 90


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


def minutes_between(later: Optional[datetime], earlier: Optional[datetime]) -> Optional[float]:
    if later is None or earlier is None:
        return None
    return round((later - earlier).total_seconds() / 60.0, 3)


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


def latest_row_within_window(
    rows: List[Dict[str, Any]],
    symbol: str,
    target_ts: datetime,
    max_lookback_minutes: int,
) -> Optional[Dict[str, Any]]:
    candidates: List[Tuple[datetime, Dict[str, Any]]] = []
    lower_bound = target_ts - timedelta(minutes=max_lookback_minutes)

    for row in rows:
        if str(row.get("symbol")) != symbol:
            continue
        row_ts = parse_ts(row.get("ts"))
        if row_ts is None:
            continue
        if lower_bound <= row_ts <= target_ts:
            candidates.append((row_ts, row))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def extract_gamma_regime(market_state: Dict[str, Any]) -> Optional[str]:
    gf = market_state.get("gamma_features") or {}
    return gf.get("gamma_regime")


def extract_breadth_regime(market_state: Dict[str, Any]) -> Optional[str]:
    bf = market_state.get("breadth_features") or {}
    regime = bf.get("breadth_regime")
    if regime:
        return regime
    wcb = market_state.get("wcb_features") or {}
    return wcb.get("wcb_regime")


def decide_shadow_signal_reconstructed(
    symbol: str,
    market_state: Dict[str, Any],
    momentum_v2: Optional[Dict[str, Any]],
    options_flow: Optional[Dict[str, Any]],
    iv_context: Optional[Dict[str, Any]],
    smdm: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    reasons: List[str] = []
    cautions: List[str] = []

    gamma_regime = extract_gamma_regime(market_state)
    breadth_regime = extract_breadth_regime(market_state)

    momentum_regime_v2 = momentum_v2.get("momentum_regime") if momentum_v2 else None
    ret_session = to_float(momentum_v2.get("ret_session")) if momentum_v2 else None

    pcr_regime = options_flow.get("pcr_regime") if options_flow else None
    flow_regime = options_flow.get("flow_regime") if options_flow else None
    skew_regime = options_flow.get("skew_regime") if options_flow else None
    put_call_ratio = to_float(options_flow.get("put_call_ratio")) if options_flow else None
    pe_vol_oi_ratio = to_float(options_flow.get("pe_vol_oi_ratio")) if options_flow else None
    chain_iv_skew = to_float(options_flow.get("chain_iv_skew")) if options_flow else None

    iv_rank = to_float(iv_context.get("iv_rank")) if iv_context else None
    iv_regime = iv_context.get("iv_regime") if iv_context else None
    vix_trend = iv_context.get("vix_trend") if iv_context else None
    iv_context_low_conf = bool(iv_context.get("low_confidence")) if iv_context else None

    smdm_squeeze_active = bool(smdm.get("squeeze_active")) if smdm else False
    smdm_pattern = smdm.get("pattern") if smdm else None
    smdm_score = to_int(smdm.get("squeeze_score")) if smdm else None

    confidence = 30
    direction_bias = "NEUTRAL"
    action = "DO_NOTHING"
    trade_allowed = False

    if gamma_regime:
        reasons.append(f"Gamma regime is {gamma_regime}")
    if breadth_regime:
        reasons.append(f"Breadth regime is {breadth_regime}")
    if momentum_regime_v2:
        reasons.append(f"Momentum v2 regime is {momentum_regime_v2}")
    if flow_regime:
        reasons.append(f"Options flow regime is {flow_regime}")
    if skew_regime:
        reasons.append(f"Skew regime is {skew_regime}")
    if iv_regime:
        reasons.append(f"IV regime is {iv_regime}")

    bearish_points = 0
    bullish_points = 0

    if breadth_regime == "BEARISH":
        bearish_points += 3
    elif breadth_regime == "BULLISH":
        bullish_points += 3

    if momentum_regime_v2 == "DOWN":
        bearish_points += 3
    elif momentum_regime_v2 == "UP":
        bullish_points += 3

    if gamma_regime == "SHORT_GAMMA":
        bearish_points += 1
        bullish_points += 1
        cautions.append("Short gamma can amplify directional movement")
    elif gamma_regime == "LONG_GAMMA":
        cautions.append("Long gamma may dampen directional follow-through")
    elif gamma_regime == "NO_FLIP":
        reasons.append("No valid gamma flip is available from current chain structure")

    if flow_regime == "PE_ACTIVE":
        bearish_points += 2
    elif flow_regime == "CE_ACTIVE":
        bullish_points += 2

    if skew_regime == "FEAR":
        bearish_points += 2
    elif skew_regime == "COMPLACENCY":
        bullish_points += 1

    if pcr_regime == "BEARISH":
        bearish_points += 1
    elif pcr_regime == "BULLISH":
        bullish_points += 1

    if iv_regime == "IV_HIGH":
        confidence -= 6
        cautions.append("IV regime is high; outright premium buying is less attractive")
    elif iv_regime == "IV_ELEVATED":
        confidence -= 3
        cautions.append("IV regime is elevated")

    if iv_context_low_conf:
        cautions.append("IV context is bootstrap-low-confidence")

    if smdm_squeeze_active:
        confidence -= 8
        cautions.append("SMDM squeeze is active")
    if smdm_pattern and smdm_pattern != "NONE":
        cautions.append(f"SMDM pattern detected: {smdm_pattern}")

    if ret_session is not None:
        if ret_session <= -0.002:
            bearish_points += 1
        elif ret_session >= 0.002:
            bullish_points += 1

    if bearish_points >= bullish_points + 2:
        direction_bias = "BEARISH"
        action = "BUY_PE"
        confidence += 10 + bearish_points * 3
        reasons.append("Composite reconstructed direction is bearish")
    elif bullish_points >= bearish_points + 2:
        direction_bias = "BULLISH"
        action = "BUY_CE"
        confidence += 10 + bullish_points * 3
        reasons.append("Composite reconstructed direction is bullish")
    else:
        direction_bias = "NEUTRAL"
        action = "DO_NOTHING"
        confidence += 2
        cautions.append("Composite alignment is not strong enough")

    confidence = max(0, min(100, int(round(confidence))))
    trade_allowed = action != "DO_NOTHING" and confidence >= 55

    if not trade_allowed and action != "DO_NOTHING":
        cautions.append("Reconstructed confidence threshold not met for execution")

    return {
        "action": action,
        "trade_allowed": trade_allowed,
        "confidence_score": confidence,
        "direction_bias": direction_bias,

        "momentum_regime_v2": momentum_regime_v2,
        "ret_session": round(ret_session, 12) if ret_session is not None else None,

        "pcr_regime": pcr_regime,
        "flow_regime": flow_regime,
        "skew_regime": skew_regime,
        "put_call_ratio": round(put_call_ratio, 6) if put_call_ratio is not None else None,
        "pe_vol_oi_ratio": round(pe_vol_oi_ratio, 6) if pe_vol_oi_ratio is not None else None,
        "chain_iv_skew": round(chain_iv_skew, 6) if chain_iv_skew is not None else None,

        "iv_rank": round(iv_rank, 4) if iv_rank is not None else None,
        "iv_regime": iv_regime,
        "vix_trend": vix_trend,
        "iv_context_low_conf": iv_context_low_conf,

        "smdm_squeeze_active": smdm_squeeze_active,
        "smdm_pattern": smdm_pattern,
        "smdm_score": smdm_score,

        "gamma_regime": gamma_regime,
        "breadth_regime": breadth_regime,

        "reasons": reasons,
        "cautions": cautions,
    }


def classify_coverage(
    momentum_v2: Optional[Dict[str, Any]],
    options_flow: Optional[Dict[str, Any]],
    iv_context: Optional[Dict[str, Any]],
    smdm: Optional[Dict[str, Any]],
) -> Tuple[str, bool, bool]:
    has_momentum = momentum_v2 is not None
    has_options_flow = options_flow is not None
    has_iv_context = iv_context is not None
    has_smdm = smdm is not None

    core_ok = has_momentum and has_options_flow and has_iv_context
    smdm_ok = has_smdm

    if not has_momentum:
        return "MISSING_MOMENTUM", False, smdm_ok
    if not has_options_flow:
        return "MISSING_OPTIONS_FLOW", False, smdm_ok
    if not has_iv_context:
        return "MISSING_IV_CONTEXT", False, smdm_ok
    if has_smdm:
        return "FULL_CORE_PLUS_SMDM", True, True
    return "FULL_CORE_COVERAGE", True, False


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python reconstruct_shadow_for_date_local_v3.py YYYY-MM-DD")
        return 1

    reconstruction_date = sys.argv[1]
    try:
        datetime.strptime(reconstruction_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        return 1

    print("========================================================================")
    print("MERDIAN - reconstruct_shadow_for_date_local_v3")
    print("========================================================================")
    print(f"Reconstruction date (IST): {reconstruction_date}")

    market_states_raw = fetch_rows_for_ist_date("market_state_snapshots", reconstruction_date)
    momentum_rows_raw = fetch_rows_for_ist_date("momentum_snapshots_v2", reconstruction_date)
    options_flow_rows_raw = fetch_rows_for_ist_date("options_flow_snapshots", reconstruction_date)
    iv_context_rows_raw = fetch_rows_for_ist_date("iv_context_snapshots", reconstruction_date)
    smdm_rows_raw = fetch_rows_for_ist_date("smdm_snapshots", reconstruction_date)

    market_states = dedupe_latest_by_symbol_ts(market_states_raw)
    momentum_rows = dedupe_latest_by_symbol_ts(momentum_rows_raw)
    options_flow_rows = dedupe_latest_by_symbol_ts(options_flow_rows_raw)
    iv_context_rows = dedupe_latest_by_symbol_ts(iv_context_rows_raw)
    smdm_rows = dedupe_latest_by_symbol_ts(smdm_rows_raw)

    print(f"market_state raw={len(market_states_raw)} deduped={len(market_states)}")
    print(f"momentum_v2 raw={len(momentum_rows_raw)} deduped={len(momentum_rows)}")
    print(f"options_flow raw={len(options_flow_rows_raw)} deduped={len(options_flow_rows)}")
    print(f"iv_context raw={len(iv_context_rows_raw)} deduped={len(iv_context_rows)}")
    print(f"smdm raw={len(smdm_rows_raw)} deduped={len(smdm_rows)}")

    out_rows: List[Dict[str, Any]] = []
    skipped_non_core = 0

    for market_state in market_states:
        symbol = str(market_state.get("symbol") or "")
        ts = parse_ts(market_state.get("ts"))
        if not symbol or ts is None:
            continue

        momentum_v2 = latest_row_within_window(momentum_rows, symbol, ts, MOMENTUM_LOOKBACK_MIN)
        options_flow = latest_row_within_window(options_flow_rows, symbol, ts, OPTIONS_FLOW_LOOKBACK_MIN)
        iv_context = latest_row_within_window(iv_context_rows, symbol, ts, IV_CONTEXT_LOOKBACK_MIN)
        smdm = latest_row_within_window(smdm_rows, symbol, ts, SMDM_LOOKBACK_MIN)

        coverage_status, core_ok, smdm_available = classify_coverage(
            momentum_v2=momentum_v2,
            options_flow=options_flow,
            iv_context=iv_context,
            smdm=smdm,
        )

        if not core_ok:
            skipped_non_core += 1
            print("------------------------------------------------------------------------")
            print(f"Skipping {symbol} @ {market_state.get('ts')} | coverage_status={coverage_status}")
            continue

        momentum_ts = parse_ts(momentum_v2.get("ts")) if momentum_v2 else None
        options_flow_ts = parse_ts(options_flow.get("ts")) if options_flow else None
        iv_context_ts = parse_ts(iv_context.get("ts")) if iv_context else None
        smdm_ts = parse_ts(smdm.get("ts")) if smdm else None

        reconstructed = decide_shadow_signal_reconstructed(
            symbol=symbol,
            market_state=market_state,
            momentum_v2=momentum_v2,
            options_flow=options_flow,
            iv_context=iv_context,
            smdm=smdm,
        )

        row = {
            "reconstruction_date": reconstruction_date,
            "symbol": symbol,
            "ts": ts.isoformat(),

            "coverage_status": coverage_status,
            "core_coverage_ok": core_ok,
            "smdm_available": smdm_available,

            "action": reconstructed["action"],
            "trade_allowed": reconstructed["trade_allowed"],
            "confidence_score": reconstructed["confidence_score"],
            "direction_bias": reconstructed["direction_bias"],

            "momentum_regime_v2": reconstructed["momentum_regime_v2"],
            "ret_session": reconstructed["ret_session"],

            "pcr_regime": reconstructed["pcr_regime"],
            "flow_regime": reconstructed["flow_regime"],
            "skew_regime": reconstructed["skew_regime"],
            "put_call_ratio": reconstructed["put_call_ratio"],
            "pe_vol_oi_ratio": reconstructed["pe_vol_oi_ratio"],
            "chain_iv_skew": reconstructed["chain_iv_skew"],

            "iv_rank": reconstructed["iv_rank"],
            "iv_regime": reconstructed["iv_regime"],
            "vix_trend": reconstructed["vix_trend"],
            "iv_context_low_conf": reconstructed["iv_context_low_conf"],

            "smdm_squeeze_active": reconstructed["smdm_squeeze_active"],
            "smdm_pattern": reconstructed["smdm_pattern"],
            "smdm_score": reconstructed["smdm_score"],

            "gamma_regime": reconstructed["gamma_regime"],
            "breadth_regime": reconstructed["breadth_regime"],

            "source_market_state_ts": market_state.get("ts"),
            "source_momentum_ts": momentum_v2.get("ts") if momentum_v2 else None,
            "source_options_flow_ts": options_flow.get("ts") if options_flow else None,
            "source_iv_context_ts": iv_context.get("ts") if iv_context else None,
            "source_smdm_ts": smdm.get("ts") if smdm else None,

            "source_momentum_age_min": minutes_between(ts, momentum_ts),
            "source_options_flow_age_min": minutes_between(ts, options_flow_ts),
            "source_iv_context_age_min": minutes_between(ts, iv_context_ts),
            "source_smdm_age_min": minutes_between(ts, smdm_ts),

            "reasons": reconstructed["reasons"],
            "cautions": reconstructed["cautions"],
        }

        out_rows.append(row)

        print("------------------------------------------------------------------------")
        print(f"Reconstructed row for {symbol} @ {market_state.get('ts')}")
        print(f"coverage_status={coverage_status}")
        print(f"action={row['action']}")
        print(f"trade_allowed={row['trade_allowed']}")
        print(f"confidence_score={row['confidence_score']}")
        print(f"direction_bias={row['direction_bias']}")
        print(f"momentum_regime_v2={row['momentum_regime_v2']} | source_ts={row['source_momentum_ts']} | age_min={row['source_momentum_age_min']}")
        print(f"flow_regime={row['flow_regime']} | source_ts={row['source_options_flow_ts']} | age_min={row['source_options_flow_age_min']}")
        print(f"skew_regime={row['skew_regime']}")
        print(f"iv_regime={row['iv_regime']} | source_ts={row['source_iv_context_ts']} | age_min={row['source_iv_context_age_min']}")
        print(f"smdm_pattern={row['smdm_pattern']} | source_ts={row['source_smdm_ts']} | age_min={row['source_smdm_age_min']}")
        print(f"gamma_regime={row['gamma_regime']}")
        print(f"breadth_regime={row['breadth_regime']}")

    print("------------------------------------------------------------------------")
    print(f"Skipped rows due to missing core coverage: {skipped_non_core}")
    print(f"Prepared rows with full core coverage: {len(out_rows)}")

    if not out_rows:
        print("No reconstruction rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Writing rows to public.shadow_reconstruction_v3 ...")
    inserted = supabase_insert("shadow_reconstruction_v3", out_rows)
    print(f"Inserted rows returned by Supabase: {len(inserted)}")
    print("RECONSTRUCT SHADOW FOR DATE V3 COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())