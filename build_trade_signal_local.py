from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# MERDIAN - build_trade_signal_local.py
# Full-file replacement
#
# Purpose:
#   Build one signal_snapshots row for a given symbol using the
#   latest market_state_snapshots row.
#
# Permanent repair in this version:
#   - Handles gamma_regime = NO_FLIP honestly
#   - Never fabricates flip-distance interpretation when flip is NULL
#   - Does NOT add "far from gamma flip" cautions if no flip exists
#   - Keeps action and trade_allowed separate
#
# V18.1 fix (Track 1 regression repair):
#   - Restores spot, atm_strike, expiry_date, dte, atm_call_iv,
#     atm_put_iv, atm_iv_avg, iv_skew, entry_quality, source_run_id,
#     india_vix, vix_change, vix_regime, wcb_* fields to output dict.
#     These were present in early signals (IDs 23-35) but dropped
#     during a full-file replacement. Required for premium outcome
#     measurement layer.
# ============================================================


# -----------------------------
# Environment / Supabase client
# -----------------------------
def _load_env() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")

    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not found in environment or .env")

    if not supabase_url.startswith("http://") and not supabase_url.startswith("https://"):
        raise RuntimeError(
            f"SUPABASE_URL is invalid: {supabase_url!r}. It must start with https://"
        )

    return create_client(supabase_url, service_role_key)


SUPABASE: Client = _load_env()


# -----------------------------
# Helpers
# -----------------------------
def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def as_iso_ts(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    return datetime.now(timezone.utc).isoformat()


def latest_market_state(symbol: str) -> dict[str, Any]:
    result = (
        SUPABASE.table("market_state_snapshots")
        .select("*")
        .eq("symbol", symbol.upper())
        .order("ts", desc=True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    if not rows:
        raise RuntimeError(f"No market_state_snapshots row found for symbol={symbol}")
    return rows[0]


def prefer(*values: Any) -> Any:
    for v in values:
        if v is not None and v != "":
            return v
    return None


# -----------------------------
# Feature extraction
# -----------------------------
def get_gamma_regime(gamma_features: dict[str, Any]) -> str:
    return str(prefer(gamma_features.get("gamma_regime"), gamma_features.get("regime"), "UNKNOWN")).upper()


def get_breadth_regime(breadth_features: dict[str, Any]) -> str:
    return str(prefer(breadth_features.get("breadth_regime"), "UNKNOWN")).upper()


def get_volatility_regime(vol_features: dict[str, Any]) -> str:
    explicit = prefer(vol_features.get("volatility_regime"), vol_features.get("vix_regime"))
    if explicit:
        explicit_u = str(explicit).upper()
        if explicit_u in {"HIGH_IV", "NORMAL_IV", "LOW_IV"}:
            return explicit_u
        if explicit_u == "HIGH":
            return "HIGH_IV"
        if explicit_u == "LOW":
            return "LOW_IV"
        return explicit_u

    atm_iv_avg = to_float(vol_features.get("atm_iv_avg"))
    india_vix = to_float(vol_features.get("india_vix"))

    if atm_iv_avg is not None and india_vix is not None:
        if atm_iv_avg > india_vix * 1.15:
            return "HIGH_IV"
        if atm_iv_avg < india_vix * 0.85:
            return "LOW_IV"
    return "NORMAL_IV"


def get_momentum_direction(momentum_features: dict[str, Any]) -> str:
    explicit = prefer(momentum_features.get("momentum_regime"), momentum_features.get("momentum_direction"))
    if explicit:
        explicit_u = str(explicit).upper()
        if explicit_u in {"BULLISH", "UP"}:
            return "BULLISH"
        if explicit_u in {"BEARISH", "DOWN"}:
            return "BEARISH"
        if explicit_u in {"NEUTRAL", "FLAT"}:
            return "NEUTRAL"

    ret_session = to_float(momentum_features.get("ret_session"))
    ret_15m = to_float(momentum_features.get("ret_15m"))
    ret_30m = to_float(momentum_features.get("ret_30m"))

    if ret_session is not None:
        if ret_session > 0:
            return "BULLISH"
        if ret_session < 0:
            return "BEARISH"

    score = 0
    for v in (ret_15m, ret_30m):
        if v is None:
            continue
        if v > 0:
            score += 1
        elif v < 0:
            score -= 1

    if score > 0:
        return "BULLISH"
    if score < 0:
        return "BEARISH"
    return "NEUTRAL"


def infer_direction_bias(breadth_regime: str, momentum_direction: str) -> str:
    if breadth_regime == "BEARISH" and momentum_direction == "BEARISH":
        return "BEARISH"
    if breadth_regime == "BULLISH" and momentum_direction == "BULLISH":
        return "BULLISH"
    if breadth_regime == "TRANSITION":
        return "NEUTRAL"
    return "NEUTRAL"


def derive_entry_quality(confidence: float, direction_bias: str, gamma_regime: str) -> str:
    """Derive entry quality label from confidence and regime context."""
    if direction_bias == "NEUTRAL":
        return "NO_TRADE"
    if confidence >= 75:
        return "A" if gamma_regime == "SHORT_GAMMA" else "B"
    if confidence >= 60:
        return "B" if gamma_regime == "SHORT_GAMMA" else "C"
    return "D"


# -----------------------------
# Scoring
# -----------------------------
def build_signal(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()
    state = latest_market_state(symbol)

    gamma_features = state.get("gamma_features") or {}
    breadth_features = state.get("breadth_features") or {}
    vol_features = state.get("volatility_features") or {}
    momentum_features = state.get("momentum_features") or {}

    ts = as_iso_ts(state.get("ts"))
    market_state_ts = ts
    dte = to_int(state.get("dte"))
    spot = to_float(state.get("spot"))

    # --- Expiry context ---
    expiry_date = state.get("expiry_date")
    expiry_type = state.get("expiry_type")
    source_run_id = state.get("source_run_id") or state.get("run_id")

    # --- ATM / IV context from vol_features ---
    atm_strike = to_int(vol_features.get("atm_strike"))
    atm_call_iv = to_float(vol_features.get("atm_call_iv"))
    atm_put_iv = to_float(vol_features.get("atm_put_iv"))
    atm_iv_avg = to_float(vol_features.get("atm_iv_avg"))
    iv_skew = to_float(vol_features.get("iv_skew"))

    # --- VIX fields ---
    india_vix = to_float(vol_features.get("india_vix"))
    vix_change = to_float(vol_features.get("vix_change"))
    vix_regime = prefer(
        vol_features.get("vix_regime"),
        vol_features.get("vix_context_regime"),
    )

    # --- WCB fields ---
    wcb_regime = breadth_features.get("wcb_regime")
    wcb_score = to_float(breadth_features.get("wcb_score"))
    wcb_alignment = breadth_features.get("wcb_alignment")
    wcb_weight_coverage_pct = to_float(breadth_features.get("wcb_weight_coverage_pct"))

    # --- Breadth score ---
    breadth_score = to_float(breadth_features.get("breadth_score"))

    # --- Gamma fields for output ---
    net_gex = to_float(gamma_features.get("net_gex"))
    gamma_concentration = to_float(gamma_features.get("gamma_concentration"))
    flip_level = to_float(gamma_features.get("flip_level"))
    flip_distance = to_float(gamma_features.get("flip_distance"))
    straddle_atm = to_float(gamma_features.get("straddle_atm"))
    straddle_slope = to_float(gamma_features.get("straddle_slope"))

    gamma_regime = get_gamma_regime(gamma_features)
    breadth_regime = get_breadth_regime(breadth_features)
    volatility_regime = get_volatility_regime(vol_features)
    momentum_direction = get_momentum_direction(momentum_features)

    reasons: list[str] = []
    cautions: list[str] = []

    reasons.append(f"Gamma regime is {gamma_regime}")
    reasons.append(f"Breadth regime is {breadth_regime}")
    reasons.append(f"Momentum direction is {momentum_direction}")

    direction_bias = infer_direction_bias(breadth_regime, momentum_direction)

    if direction_bias == "BEARISH":
        reasons.append("Breadth and momentum are aligned bearish")
    elif direction_bias == "BULLISH":
        reasons.append("Breadth and momentum are aligned bullish")
    else:
        reasons.append("Breadth and momentum alignment is unclear")

    confidence = 40.0

    # Breadth + momentum alignment
    if direction_bias in {"BULLISH", "BEARISH"}:
        confidence += 20.0

    # Gamma treatment
    if gamma_regime == "SHORT_GAMMA":
        reasons.append("Short gamma can amplify directional moves")
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 8.0
    elif gamma_regime == "LONG_GAMMA":
        cautions.append("Long gamma may dampen directional follow-through")
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence -= 8.0
    elif gamma_regime == "NO_FLIP":
        reasons.append("No valid gamma flip is available from current chain structure")
    else:
        cautions.append("Gamma regime is unavailable or unknown")

    # Gamma concentration
    if gamma_concentration is not None:
        if gamma_concentration >= 0.25:
            reasons.append("Gamma concentration is supportive")
            confidence += 4.0
        elif gamma_concentration <= 0.05:
            cautions.append("Gamma concentration is low")

    # Flip caution only if flip exists
    flip_distance_pct = to_float(gamma_features.get("flip_distance_pct"))
    if flip_distance_pct is not None:
        if flip_distance_pct < 0.5:
            cautions.append("Spot is very near gamma flip")
        elif flip_distance_pct < 1.5:
            cautions.append("Spot is moderately near gamma flip")
        else:
            cautions.append("Spot is relatively far from gamma flip")

    # Straddle context
    if straddle_slope is not None:
        if straddle_slope > 0:
            cautions.append("ATM straddle is expanding")
        elif straddle_slope < 0:
            cautions.append("ATM straddle is compressing")
        else:
            cautions.append("ATM straddle slope is relatively flat")

    # Volatility context
    if india_vix is not None:
        cautions.append(f"India VIX is {india_vix:.2f}")

    if vix_regime:
        cautions.append(f"India VIX regime is {str(vix_regime).upper()}")

    if volatility_regime == "HIGH_IV":
        cautions.append("Volatility regime is HIGH_IV")
        cautions.append("IV is elevated for outright premium buying")
        confidence -= 8.0

    if atm_iv_avg is not None and india_vix is not None and atm_iv_avg > india_vix * 1.15:
        cautions.append("ATM IV is significantly above India VIX")
        confidence -= 4.0

    # Momentum premium compression notes
    ret_15m = to_float(momentum_features.get("ret_15m"))
    ret_30m = to_float(momentum_features.get("ret_30m"))
    if ret_15m is not None and ret_15m < 0:
        cautions.append("ret_15m shows premium compression")
    if ret_30m is not None and ret_30m < 0:
        cautions.append("ret_30m shows premium compression")

    # DTE gating
    trade_allowed = True
    if dte is not None:
        if dte <= 0:
            cautions.append("Market state uses already-expired contract context")
            cautions.append("DTE gate blocks trade")
            trade_allowed = False
            confidence -= 20.0
        elif dte <= 1:
            cautions.append("One-day-to-expiry raises gamma/theta risk")
            cautions.append("DTE gate blocks trade")
            trade_allowed = False
            confidence -= 12.0
        elif dte <= 2:
            cautions.append("Weekly expiry can be more volatile")

    # Confidence floor/cap
    confidence = max(0.0, min(100.0, confidence))

    # Decide action independent of trade_allowed
    if direction_bias == "BEARISH":
        action = "BUY_PE"
        reasons.append("Direction bias is BEARISH")
    elif direction_bias == "BULLISH":
        action = "BUY_CE"
        reasons.append("Direction bias is BULLISH")
    else:
        action = "DO_NOTHING"
        cautions.append("No directional bias available")

    # Final trade gate
    if action != "DO_NOTHING" and confidence < 60.0:
        trade_allowed = False
        cautions.append("Confidence threshold not met for trade execution")

    # Optional additional high-VIX block
    if india_vix is not None and india_vix >= 20:
        cautions.append("High India VIX reduces options-buy attractiveness")
        trade_allowed = False

    # Entry quality
    entry_quality = derive_entry_quality(confidence, direction_bias, gamma_regime)

    out = {
        # Timestamps and identity
        "ts": ts,
        "market_state_ts": market_state_ts,
        "symbol": symbol,
        "source_run_id": source_run_id,

        # Expiry context
        "expiry_date": expiry_date,
        "expiry_type": expiry_type,
        "dte": dte,

        # Spot and ATM
        "spot": spot,
        "atm_strike": atm_strike,
        "atm_call_iv": atm_call_iv,
        "atm_put_iv": atm_put_iv,
        "atm_iv_avg": atm_iv_avg,
        "iv_skew": iv_skew,

        # Signal output
        "action": action,
        "trade_allowed": trade_allowed,
        "entry_quality": entry_quality,
        "confidence_score": round(confidence, 1),
        "direction_bias": direction_bias,

        # Regime context
        "gamma_regime": gamma_regime,
        "breadth_regime": breadth_regime,
        "breadth_score": breadth_score,
        "volatility_regime": volatility_regime,
        "vix_regime": vix_regime,

        # VIX fields
        "india_vix": india_vix,
        "vix_change": vix_change,

        # Gamma detail
        "net_gex": net_gex,
        "gamma_concentration": gamma_concentration,
        "flip_level": flip_level,
        "flip_distance": flip_distance,
        "straddle_atm": straddle_atm,
        "straddle_slope": straddle_slope,

        # WCB fields
        "wcb_regime": wcb_regime,
        "wcb_score": wcb_score,
        "wcb_alignment": wcb_alignment,
        "wcb_weight_coverage_pct": wcb_weight_coverage_pct,

        # Narrative
        "reasons": reasons,
        "cautions": cautions,
    }

    return out


def insert_signal(row: dict[str, Any]) -> None:
    SUPABASE.table("signal_snapshots").insert(row).execute()


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python build_trade_signal_local.py <symbol>")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    row = build_signal(symbol)
    insert_signal(row)

    print("Signal snapshot insert complete.")
    print(f"symbol={row.get('symbol')}")
    print(f"ts={row.get('ts')}")
    print(f"action={row.get('action')}")
    print(f"trade_allowed={row.get('trade_allowed')}")
    print(f"confidence_score={row.get('confidence_score')}")
    print(f"spot={row.get('spot')}")
    print(f"atm_strike={row.get('atm_strike')}")
    print(f"expiry_date={row.get('expiry_date')}")
    print(f"dte={row.get('dte')}")
    print(f"entry_quality={row.get('entry_quality')}")
    print(f"gamma_regime={row.get('gamma_regime')}")


if __name__ == "__main__":
    main()
