from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


UTC = timezone.utc


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


def fetch_latest_row(table_name: str, symbol: str, extra_select: Optional[str] = None) -> Optional[Dict[str, Any]]:
    select_cols = extra_select or "*"
    rows = supabase_select(
        table_name,
        {
            "select": select_cols,
            "symbol": f"eq.{symbol}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


def fetch_latest_wcb_row(symbol: str) -> Optional[Dict[str, Any]]:
    index_symbol = symbol
    rows = supabase_select(
        "weighted_constituent_breadth_snapshots",
        {
            "select": "*",
            "index_symbol": f"eq.{index_symbol}",
            "order": "created_at.desc",
            "limit": "1",
        },
    )
    return rows[0] if rows else None


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


def make_json_array(items: List[str]) -> List[str]:
    return items


def decide_shadow_signal(
    symbol: str,
    market_state: Dict[str, Any],
    live_signal: Optional[Dict[str, Any]],
    momentum_v2: Optional[Dict[str, Any]],
    options_flow: Optional[Dict[str, Any]],
    iv_context: Optional[Dict[str, Any]],
    smdm: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    reasons: List[str] = []
    cautions: List[str] = []

    gamma_regime = extract_gamma_regime(market_state)
    breadth_regime = extract_breadth_regime(market_state)

    live_action = live_signal.get("action") if live_signal else None
    live_confidence = to_int(live_signal.get("confidence_score")) if live_signal else None

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
    vol_features = market_state.get("volatility_features") or {}
    india_vix = float(vol_features["india_vix"]) if vol_features.get("india_vix") is not None else None
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

    # Breadth
    if breadth_regime == "BEARISH":
        bearish_points += 3
    elif breadth_regime == "BULLISH":
        bullish_points += 3

    # Momentum v2
    if momentum_regime_v2 == "DOWN":
        bearish_points += 3
    elif momentum_regime_v2 == "UP":
        bullish_points += 3

    # Gamma
    if gamma_regime == "SHORT_GAMMA":
        bearish_points += 1
        bullish_points += 1
        cautions.append("Short gamma can amplify directional movement")
    elif gamma_regime == "LONG_GAMMA":
        cautions.append("Long gamma may dampen directional follow-through")
    elif gamma_regime == "NO_FLIP":
        reasons.append("No valid gamma flip is available from current chain structure")

    # Options flow
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

    # IV context
    if iv_regime == "IV_HIGH":
        confidence -= 6
        cautions.append("IV regime is high; outright premium buying is less attractive")
    elif iv_regime == "IV_ELEVATED":
        confidence -= 3

    # E-03: India VIX confidence penalty
    if india_vix is not None and india_vix > 20:
        confidence -= 8
        cautions.append(f"India VIX elevated ({india_vix:.1f} > 20) — confidence penalised")
        cautions.append("IV regime is elevated")

    if iv_context_low_conf:
        cautions.append("IV context is bootstrap-low-confidence")

    # SMDM placeholder
    if smdm_squeeze_active:
        confidence -= 8
        cautions.append("SMDM squeeze is active")
    if smdm_pattern and smdm_pattern != "NONE":
        cautions.append(f"SMDM pattern detected: {smdm_pattern}")

    # ret_session
    if ret_session is not None:
        if ret_session <= -0.002:
            bearish_points += 1
        elif ret_session >= 0.002:
            bullish_points += 1

    # Build direction
    if bearish_points >= bullish_points + 2:
        direction_bias = "BEARISH"
        action = "BUY_PE"
        confidence += 10 + bearish_points * 3
        reasons.append("Composite shadow direction is bearish")
    elif bullish_points >= bearish_points + 2:
        direction_bias = "BULLISH"
        action = "BUY_CE"
        confidence += 10 + bullish_points * 3
        reasons.append("Composite shadow direction is bullish")
    else:
        direction_bias = "NEUTRAL"
        action = "DO_NOTHING"
        confidence += 2
        cautions.append("Composite alignment is not strong enough")

    # If live and shadow differ, document it
    if live_action and live_action != action:
        reasons.append(f"Shadow decision differs from live action ({live_action} -> {action})")

    # Confidence normalization
    confidence = max(0, min(100, int(round(confidence))))

    # Trade allowed threshold
    trade_allowed = action != "DO_NOTHING" and confidence >= 55

    if not trade_allowed and action != "DO_NOTHING":
        cautions.append("Shadow confidence threshold not met for execution")

    # E-03: India VIX panic gate
    if india_vix is not None and india_vix > 25:
        trade_allowed = False
        cautions.append(f"India VIX panic gate active ({india_vix:.1f} > 25) — trade blocked")

    ts = market_state.get("ts") or utc_now().isoformat()

    row = {
        "ts": ts,
        "symbol": symbol,
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

        "live_action": live_action,
        "live_confidence": live_confidence,

        "reasons": make_json_array(reasons),
        "cautions": make_json_array(cautions),
    }

    return row


def main() -> int:
    print("========================================================================")
    print("MERDIAN - build_shadow_signal_v3_local")
    print("========================================================================")

    output_rows: List[Dict[str, Any]] = []

    for symbol in ["NIFTY", "SENSEX"]:
        print("------------------------------------------------------------------------")
        print(f"Building shadow v3 row for {symbol}")

        market_state = fetch_latest_row("market_state_snapshots", symbol)
        if not market_state:
            print(f"Skipping {symbol}: no market_state_snapshots row found.")
            continue

        live_signal = fetch_latest_row("signal_snapshots", symbol)
        momentum_v2 = fetch_latest_row("momentum_snapshots_v2", symbol)
        options_flow = fetch_latest_row("options_flow_snapshots", symbol)
        iv_context = fetch_latest_row("iv_context_snapshots", symbol)
        smdm = fetch_latest_row("smdm_snapshots", symbol)

        row = decide_shadow_signal(
            symbol=symbol,
            market_state=market_state,
            live_signal=live_signal,
            momentum_v2=momentum_v2,
            options_flow=options_flow,
            iv_context=iv_context,
            smdm=smdm,
        )

        output_rows.append(row)
        for k, v in row.items():
            print(f"{k}={json.dumps(v) if isinstance(v, (list, dict, bool)) else v}")

    if not output_rows:
        print("No output rows prepared. Exiting with code 1.")
        return 1

    print("------------------------------------------------------------------------")
    print("Writing rows to public.shadow_signal_snapshots_v3 ...")
    inserted = supabase_insert("shadow_signal_snapshots_v3", output_rows)
    print(f"Inserted rows returned by Supabase: {len(inserted)}")
    print("BUILD SHADOW SIGNAL V3 COMPLETED")
    return 0


if __name__ == "__main__":
    sys.exit(main())