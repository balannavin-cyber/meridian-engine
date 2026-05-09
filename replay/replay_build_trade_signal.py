"""
replay.replay_build_trade_signal — Replay mirror of build_trade_signal_local.py.

Differences from build_trade_signal_local.py:
  1. Reads market_state_snapshots_replay, options_flow_snapshots_replay, 
     ict_zones_replay (filtered by ts <= replay_ts and trade_date = replay_date).
  2. Reads po3_session_state LIVE filtered by replay_date (immutable past).
  3. Reads capital_tracker LIVE (current capital — acceptable, replay tests 
     signal logic not historical capital state).
  4. Writes signal_snapshots_replay.
  5. CLI: --replay-ts, --symbol.
  6. Power-hour time gate uses replay_ts IST hour, NOT wall-clock.
  7. ICT enrichment uses replay_date, not date.today().

ALL GATES PRESERVED: ENH-53, ENH-55, ENH-76, ENH-77, ENH-78, DTE, VIX 
elevation, power-hour, LONG_GAMMA, NO_FLIP, signal_v4 logic. Replay reproduces
live signal-generation logic faithfully on _replay upstream data.

Live impact: ZERO writes to live. READS po3_session_state, capital_tracker
(immutable past / current state — same pattern as other replay scripts).

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from replay.replay_clock import IST, parse_replay_ts, replay_today_ist, to_iso_utc
from replay.replay_execution_log import ExecutionLog


load_dotenv()
SIGNAL_V4_ENABLED: bool = os.getenv("MERDIAN_SIGNAL_V4", "1").strip() == "1"


SUPABASE: Optional[Client] = None
_SUPABASE_INIT_ERROR: Optional[Exception] = None


def _load_env() -> Client:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")
    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found")
    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not found")
    return create_client(supabase_url, service_role_key)


def _ensure_supabase() -> Client:
    global SUPABASE, _SUPABASE_INIT_ERROR
    if SUPABASE is not None:
        return SUPABASE
    if _SUPABASE_INIT_ERROR is not None:
        raise _SUPABASE_INIT_ERROR
    try:
        SUPABASE = _load_env()
        return SUPABASE
    except Exception as e:
        _SUPABASE_INIT_ERROR = e
        raise


try:
    SUPABASE = _load_env()
except Exception as e:
    _SUPABASE_INIT_ERROR = e


def _rows(result: Any) -> list[dict]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
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


def latest_market_state_replay(symbol: str, replay_ts_iso: str) -> dict[str, Any]:
    """REPLAY: read market_state_snapshots_replay latest at-or-before replay_ts."""
    result = (
        SUPABASE.table("market_state_snapshots_replay")
        .select("*")
        .eq("symbol", symbol.upper())
        .lte("ts", replay_ts_iso)
        .order("ts", desc=True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = _rows(result)
    if not rows:
        raise RuntimeError(f"No market_state_snapshots_replay row for symbol={symbol} at/before {replay_ts_iso}")
    return rows[0]


def prefer(*values: Any) -> Any:
    for v in values:
        if v is not None and v != "":
            return v
    return None


def get_gamma_regime(gamma_features: dict) -> str:
    return str(prefer(gamma_features.get("gamma_regime"), gamma_features.get("regime"), "UNKNOWN")).upper()


def get_breadth_regime(breadth_features: dict) -> str:
    return str(prefer(breadth_features.get("breadth_regime"), "UNKNOWN")).upper()


def get_volatility_regime(vol_features: dict) -> str:
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


def get_momentum_direction(momentum_features: dict) -> str:
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
    if breadth_regime == "BULLISH" and momentum_direction == "BEARISH":
        return "BULLISH"
    if breadth_regime == "BEARISH" and momentum_direction == "BULLISH":
        return "NEUTRAL"
    if breadth_regime == "TRANSITION":
        return "NEUTRAL"
    return "NEUTRAL"


def infer_direction_bias_v4(momentum_direction: str) -> str:
    if momentum_direction == "BULLISH":
        return "BULLISH"
    if momentum_direction == "BEARISH":
        return "BEARISH"
    return "NEUTRAL"


def derive_entry_quality(confidence: float, direction_bias: str, gamma_regime: str) -> str:
    if direction_bias == "NEUTRAL":
        return "NO_TRADE"
    if confidence >= 75:
        return "A" if gamma_regime == "SHORT_GAMMA" else "B"
    if confidence >= 60:
        return "B" if gamma_regime == "SHORT_GAMMA" else "C"
    return "D"


def _get_po3_bias_replay(sb, symbol: str, replay_date_str: str) -> str:
    """REPLAY: read live po3_session_state for replay_date (immutable past)."""
    try:
        rows = (
            sb.table("po3_session_state")
              .select("po3_session_bias")
              .eq("symbol", symbol)
              .eq("trade_date", replay_date_str)
              .execute()
              .data
        )
        if rows:
            return rows[0].get("po3_session_bias", "PO3_NONE") or "PO3_NONE"
    except Exception:
        pass
    return "PO3_NONE"


def build_signal_replay(symbol: str, replay_ts: datetime) -> tuple[dict, dict]:
    """Build signal row with replay-context upstream reads. Returns (row, flags)."""
    flags = {"ict_failed": False, "enh06_failed": False}

    symbol = symbol.upper()
    replay_ts_iso = to_iso_utc(replay_ts)
    replay_date = replay_today_ist(replay_ts)
    replay_date_str = replay_date.isoformat()

    state = latest_market_state_replay(symbol, replay_ts_iso)

    gamma_features = state.get("gamma_features") or {}
    breadth_features = state.get("breadth_features") or {}
    vol_features = state.get("volatility_features") or {}
    momentum_features = state.get("momentum_features") or {}

    ts = as_iso_ts(state.get("ts"))
    market_state_ts = ts
    dte = to_int(state.get("dte"))
    spot = to_float(state.get("spot"))

    expiry_date = state.get("expiry_date")
    expiry_type = state.get("expiry_type")
    source_run_id = state.get("source_run_id") or state.get("run_id") or state.get("gamma_run_id")

    atm_strike = to_int(vol_features.get("atm_strike"))
    atm_call_iv = to_float(vol_features.get("atm_call_iv"))
    atm_put_iv = to_float(vol_features.get("atm_put_iv"))
    atm_iv_avg = to_float(vol_features.get("atm_iv_avg"))
    iv_skew = to_float(vol_features.get("iv_skew"))
    india_vix = to_float(vol_features.get("india_vix"))
    vix_change = to_float(vol_features.get("vix_change"))
    vix_regime = prefer(vol_features.get("vix_regime"), vol_features.get("vix_context_regime"))

    # REPLAY: options flow from _replay table, latest at-or-before replay_ts
    def _fetch_options_flow_replay(sym: str) -> dict:
        try:
            rows = (SUPABASE.table("options_flow_snapshots_replay")
                    .select("pcr_regime,skew_regime,flow_regime,"
                            "put_call_ratio,chain_iv_skew,ce_vol_oi_ratio,pe_vol_oi_ratio")
                    .eq("symbol", sym)
                    .lte("ts", replay_ts_iso)
                    .order("ts", desc=True)
                    .limit(1)
                    .execute().data)
            return rows[0] if rows else {}
        except Exception:
            return {}

    _flow = _fetch_options_flow_replay(symbol)
    pcr_regime = _flow.get("pcr_regime")
    skew_regime = _flow.get("skew_regime")
    flow_regime = _flow.get("flow_regime")
    put_call_ratio = to_float(_flow.get("put_call_ratio"))
    chain_iv_skew = to_float(_flow.get("chain_iv_skew"))

    wcb_regime = breadth_features.get("wcb_regime")
    wcb_score = to_float(breadth_features.get("wcb_score"))
    wcb_alignment = breadth_features.get("wcb_alignment")
    wcb_weight_coverage_pct = to_float(breadth_features.get("wcb_weight_coverage_pct"))

    breadth_score = to_float(breadth_features.get("breadth_score"))

    net_gex = to_float(gamma_features.get("net_gex"))
    gamma_concentration = to_float(gamma_features.get("gamma_concentration"))
    flip_level = to_float(gamma_features.get("flip_level"))
    flip_distance = to_float(gamma_features.get("flip_distance"))
    straddle_atm = to_float(gamma_features.get("straddle_atm"))
    straddle_slope = to_float(gamma_features.get("straddle_slope"))

    ret_session = to_float(momentum_features.get("ret_session"))

    gamma_regime = get_gamma_regime(gamma_features)
    breadth_regime = get_breadth_regime(breadth_features)
    volatility_regime = get_volatility_regime(vol_features)
    momentum_direction = get_momentum_direction(momentum_features)

    reasons: list[str] = []
    cautions: list[str] = []

    reasons.append(f"Gamma regime is {gamma_regime}")
    reasons.append(f"Breadth regime is {breadth_regime}")
    reasons.append(f"Momentum direction is {momentum_direction}")

    if SIGNAL_V4_ENABLED:
        direction_bias = infer_direction_bias_v4(momentum_direction)
        reasons.append("ENH-53: direction_bias from momentum only (V4)")
    else:
        direction_bias = infer_direction_bias(breadth_regime, momentum_direction)

    if direction_bias == "BEARISH":
        reasons.append("Breadth and momentum are aligned bearish")
    elif direction_bias == "BULLISH":
        reasons.append("Breadth and momentum are aligned bullish")
    else:
        reasons.append("Breadth and momentum alignment is unclear")

    confidence = 40.0
    if not SIGNAL_V4_ENABLED:
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 20.0

    action: str = "DO_NOTHING"
    trade_allowed: bool = True

    # Gamma treatment
    if gamma_regime == "SHORT_GAMMA":
        reasons.append("Short gamma can amplify directional moves")
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 8.0
    elif gamma_regime == "LONG_GAMMA":
        cautions.append("LONG_GAMMA gated — historical accuracy below random (ENH-35)")
        trade_allowed = False
    elif gamma_regime == "NO_FLIP":
        cautions.append("NO_FLIP gated — no gamma flip reference (ENH-35)")
        trade_allowed = False
    else:
        cautions.append("Gamma regime is unavailable or unknown")

    if gamma_concentration is not None:
        if gamma_concentration >= 0.25:
            reasons.append("Gamma concentration is supportive")
            confidence += 4.0
        elif gamma_concentration <= 0.05:
            cautions.append("Gamma concentration is low")

    flip_distance_pct = to_float(gamma_features.get("flip_distance_pct"))
    if flip_distance_pct is not None:
        if flip_distance_pct < 0.5:
            cautions.append("Spot is very near gamma flip")
        elif flip_distance_pct < 1.5:
            cautions.append("Spot is moderately near gamma flip")
        else:
            cautions.append("Spot is relatively far from gamma flip")

    if straddle_slope is not None:
        if straddle_slope > 0:
            cautions.append("ATM straddle is expanding")
        elif straddle_slope < 0:
            cautions.append("ATM straddle is compressing")
        else:
            cautions.append("ATM straddle slope is relatively flat")

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

    ret_15m = to_float(momentum_features.get("ret_15m"))
    ret_30m = to_float(momentum_features.get("ret_30m"))
    if ret_15m is not None and ret_15m < 0:
        cautions.append("ret_15m shows premium compression")
    if ret_30m is not None and ret_30m < 0:
        cautions.append("ret_30m shows premium compression")

    # Options flow modifiers (action is still DO_NOTHING here; live has same quirk)
    if pcr_regime and action in ("BUY_PE", "BUY_CE"):
        if (pcr_regime == "BEARISH" and action == "BUY_PE"):
            confidence += 5.0
            reasons.append(f"PCR confirms bearish bias (pcr_regime={pcr_regime})")
        elif (pcr_regime == "BULLISH" and action == "BUY_CE"):
            confidence += 5.0
            reasons.append(f"PCR confirms bullish bias (pcr_regime={pcr_regime})")
        elif (pcr_regime == "BEARISH" and action == "BUY_CE"):
            confidence -= 4.0
            cautions.append(f"PCR contradicts bullish bias (pcr_regime={pcr_regime})")
        elif (pcr_regime == "BULLISH" and action == "BUY_PE"):
            confidence -= 4.0
            cautions.append(f"PCR contradicts bearish bias (pcr_regime={pcr_regime})")

    if skew_regime and action in ("BUY_PE", "BUY_CE"):
        if skew_regime == "FEAR" and action == "BUY_PE":
            confidence += 4.0
            reasons.append("IV skew shows FEAR — confirms PE setup")
        elif skew_regime == "GREED" and action == "BUY_CE":
            confidence += 4.0
            reasons.append("IV skew shows GREED — confirms CE setup")
        elif skew_regime == "FEAR" and action == "BUY_CE":
            cautions.append("IV skew FEAR contradicts CE setup")
        elif skew_regime == "GREED" and action == "BUY_PE":
            cautions.append("IV skew GREED contradicts PE setup")

    if flow_regime and action in ("BUY_PE", "BUY_CE"):
        if flow_regime == "PE_ACTIVE" and action == "BUY_PE":
            confidence += 3.0
            reasons.append("Options flow PE_ACTIVE confirms bearish setup")
        elif flow_regime == "CE_ACTIVE" and action == "BUY_CE":
            confidence += 3.0
            reasons.append("Options flow CE_ACTIVE confirms bullish setup")
        elif flow_regime == "PE_ACTIVE" and action == "BUY_CE":
            cautions.append("Options flow PE_ACTIVE contradicts CE setup")
        elif flow_regime == "CE_ACTIVE" and action == "BUY_PE":
            cautions.append("Options flow CE_ACTIVE contradicts PE setup")

    basis_pct = to_float(gamma_features.get("basis_pct"))
    if basis_pct is not None:
        if basis_pct > 0.5:
            cautions.append(f"Futures in premium vs spot (basis_pct={basis_pct:.2f}%)")
        elif basis_pct < -0.5:
            cautions.append(f"Futures in discount vs spot (basis_pct={basis_pct:.2f}%)")

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

    confidence = max(0.0, min(100.0, confidence))

    if direction_bias == "BEARISH":
        action = "BUY_PE"
        reasons.append("Direction bias is BEARISH")
    elif direction_bias == "BULLISH":
        action = "BUY_CE"
        reasons.append("Direction bias is BULLISH")
    else:
        action = "DO_NOTHING"
        cautions.append("No directional bias available")

    # V4 block
    if SIGNAL_V4_ENABLED and action in ("BUY_CE", "BUY_PE"):
        if ret_session is not None and abs(ret_session) > 0.0005:
            opposed = (
                (action == "BUY_CE" and ret_session < -0.0005)
                or (action == "BUY_PE" and ret_session > 0.0005)
            )
            aligned = (
                (action == "BUY_CE" and ret_session > 0.0005)
                or (action == "BUY_PE" and ret_session < -0.0005)
            )
            if opposed:
                cautions.append(
                    f"ENH-55: Momentum opposition block — {action} "
                    f"opposes ret_session={ret_session:.4f}"
                )
                action = "DO_NOTHING"
                trade_allowed = False
                direction_bias = "NEUTRAL"
            elif aligned:
                confidence += 10.0
                reasons.append(f"ENH-55: Momentum aligned (+10) — ret_session={ret_session:.4f}")

        if action in ("BUY_CE", "BUY_PE"):
            if breadth_regime == "BULLISH" and action == "BUY_CE":
                confidence += 5.0
                reasons.append("ENH-53: Breadth aligned (+5) — BULLISH breadth, BUY_CE")
            elif breadth_regime == "BEARISH" and action == "BUY_PE":
                confidence += 5.0
                reasons.append("ENH-53: Breadth aligned (+5) — BEARISH breadth, BUY_PE")

        confidence = max(0.0, min(100.0, confidence))

    if action != "DO_NOTHING" and confidence < 40.0:
        trade_allowed = False
        cautions.append("Confidence threshold not met for trade execution")

    if india_vix is not None and india_vix >= 20:
        cautions.append(f"India VIX elevated at {india_vix:.1f} — monitoring only")

    # REPLAY: power-hour gate uses replay_ts IST hour, NOT wall-clock
    replay_ts_ist = replay_ts.astimezone(IST)
    if replay_ts_ist.hour >= 15:
        action = "DO_NOTHING"
        trade_allowed = False
        cautions.append("Power hour gate: signals after 15:00 IST excluded")

    entry_quality = derive_entry_quality(confidence, direction_bias, gamma_regime)

    out = {
        "ts": ts,
        "market_state_ts": market_state_ts,
        "symbol": symbol,
        "source_run_id": source_run_id,
        "expiry_date": expiry_date,
        "expiry_type": expiry_type,
        "dte": dte,
        "spot": spot,
        "atm_strike": atm_strike,
        "atm_call_iv": atm_call_iv,
        "atm_put_iv": atm_put_iv,
        "atm_iv_avg": atm_iv_avg,
        "iv_skew": iv_skew,
        "action": action,
        "trade_allowed": trade_allowed,
        "entry_quality": entry_quality,
        "confidence_score": round(confidence, 1),
        "direction_bias": direction_bias,
        "gamma_regime": gamma_regime,
        "breadth_regime": breadth_regime,
        "breadth_score": breadth_score,
        "volatility_regime": volatility_regime,
        "vix_regime": vix_regime,
        "india_vix": india_vix,
        "vix_change": vix_change,
        "net_gex": net_gex,
        "gamma_concentration": gamma_concentration,
        "flip_level": flip_level,
        "flip_distance": flip_distance,
        "straddle_atm": straddle_atm,
        "straddle_slope": straddle_slope,
        "wcb_regime": wcb_regime,
        "wcb_score": wcb_score,
        "wcb_alignment": wcb_alignment,
        "wcb_weight_coverage_pct": wcb_weight_coverage_pct,
        "reasons": reasons,
        "cautions": cautions,
    }

    if "raw" not in out:
        out["raw"] = {}
    out["raw"].update({
        "pcr_regime": pcr_regime,
        "skew_regime": skew_regime,
        "flow_regime": flow_regime,
        "put_call_ratio": put_call_ratio,
        "chain_iv_skew": chain_iv_skew,
        "basis_pct": basis_pct,
        "signal_v4": SIGNAL_V4_ENABLED,
        "ret_session": ret_session,
        "builder": "replay_build_trade_signal.py",
        "builder_version": "REPLAY_V1",
        "replay_ts": replay_ts_iso,
        "replay_date": replay_date_str,
    })

    # ICT enrichment from ict_zones_replay (filtered by replay_date)
    try:
        from detect_ict_patterns import enrich_signal_with_ict
        _ict_rows = (SUPABASE.table("ict_zones_replay")
                     .select("id,pattern_type,direction,zone_high,zone_low,"
                             "status,ict_tier,ict_size_mult,mtf_context,detected_at_ts,"
                             "ict_lots_t1,ict_lots_t2,ict_lots_t3")
                     .eq("symbol", symbol)
                     .eq("trade_date", replay_date_str)
                     .eq("status", "ACTIVE")
                     .execute().data)
        out = enrich_signal_with_ict(out, _ict_rows, float(spot or 0))
        if _ict_rows:
            out['ict_lots_t1'] = _ict_rows[0].get('ict_lots_t1')
            out['ict_lots_t2'] = _ict_rows[0].get('ict_lots_t2')
            out['ict_lots_t3'] = _ict_rows[0].get('ict_lots_t3')
        else:
            out['ict_lots_t1'] = None
            out['ict_lots_t2'] = None
            out['ict_lots_t3'] = None
    except Exception:
        flags["ict_failed"] = True
        out["ict_pattern"] = "NONE"
        out["ict_tier"] = "NONE"
        out["ict_size_mult"] = 1.0
        out["ict_mtf_context"] = "NONE"
        out["ict_lots_t1"] = None
        out["ict_lots_t2"] = None
        out["ict_lots_t3"] = None

    # ENH-06 capital check (uses live capital_tracker — current state OK)
    try:
        from merdian_utils import (
            effective_sizing_capital, estimate_lot_cost, KELLY_FRACTIONS_C as _KF
        )
        _cap_rows = (SUPABASE.table("capital_tracker")
                     .select("capital")
                     .eq("symbol", symbol)
                     .limit(1)
                     .execute().data)
        _raw_capital = float(_cap_rows[0]["capital"]) if _cap_rows else 200_000
        _eff_capital = effective_sizing_capital(_raw_capital)
        _tier = out.get("ict_tier", "NONE")
        _kelly_frac = _KF.get(_tier, 0.20)
        _allocated = _eff_capital * _kelly_frac
        _lot_cost = estimate_lot_cost(
            symbol, float(spot or 0), float(atm_iv_avg or 16.0), float(dte or 2),
        )
        _active_lots = out.get("ict_lots_t1") or out.get("ict_lots_t2") or out.get("ict_lots_t3")
        _capital_ok = True
        if _active_lots and _lot_cost and _lot_cost > 0:
            _deployed = _active_lots * _lot_cost
            if _deployed > _allocated * 1.10:
                _tier_key = {"TIER1": "ict_lots_t1", "TIER2": "ict_lots_t2", "TIER3": "ict_lots_t3"}.get(_tier)
                if _tier_key:
                    out[_tier_key] = 1
                cautions.append(
                    f"ENH-06: {_active_lots} lots (INR {_deployed:,.0f}) "
                    f"exceeds allocation (INR {_allocated:,.0f}) -- reduced to 1 lot"
                )
                _capital_ok = False
            else:
                reasons.append(
                    f"ENH-06: Capital OK -- {_active_lots} lots x "
                    f"INR {_lot_cost:,.0f} = INR {_deployed:,.0f}"
                )
        if _raw_capital < 50_000:
            cautions.append(f"ENH-06: Low capital INR {_raw_capital:,.0f} -- minimum sizing")
        out["raw"].update({
            "enh06_capital_raw": _raw_capital,
            "enh06_capital_eff": _eff_capital,
            "enh06_allocated": _allocated,
            "enh06_lot_cost": _lot_cost,
            "enh06_capital_ok": _capital_ok,
        })
    except Exception as _e06:
        flags["enh06_failed"] = True
        cautions.append(f"ENH-06: Capital check skipped ({_e06})")

    # PO3 session bias from live (immutable past for replay_date)
    out["po3_session_bias"] = _get_po3_bias_replay(SUPABASE, symbol, replay_date_str)

    # ENH-76 / ENH-77 / ENH-78 gates — use replay_ts IST, not wall-clock
    try:
        replay_hh = replay_ts_ist.hour
        replay_mm = replay_ts_ist.minute
        tot_mins = replay_hh * 60 + replay_mm
        ict76 = out.get("ict_pattern", "NONE")
        po3_76 = out.get("po3_session_bias", "PO3_NONE")

        # ENH-76: BEAR_OB MIDDAY 11:30-13:30 IST
        in_midday = (11 * 60 + 30) <= tot_mins < (13 * 60 + 30)
        if in_midday and ict76 == "BEAR_OB" and action == "BUY_PE":
            if po3_76 != "PO3_BEARISH":
                action = "DO_NOTHING"
                trade_allowed = False
                out["action"] = "DO_NOTHING"
                out["trade_allowed"] = False
                cautions.append(
                    f"ENH-76: BEAR_OB MIDDAY blocked -- po3_session_bias={po3_76} (requires PO3_BEARISH)"
                )
            else:
                cautions.append(
                    "ENH-76: BEAR_OB MIDDAY CONFIRMED -- po3_session_bias=PO3_BEARISH (88.2% WR, Exp 40)"
                )

        # ENH-77: BULL_OB AFTERNOON 13:30-15:00 IST
        in_aft = (13 * 60 + 30) <= tot_mins < (15 * 60 + 0)
        if in_aft and ict76 == "BULL_OB" and action == "BUY_CE":
            if symbol == "NIFTY":
                action = "DO_NOTHING"
                trade_allowed = False
                out["action"] = "DO_NOTHING"
                out["trade_allowed"] = False
                cautions.append("ENH-77: BULL_OB AFTERNOON NIFTY hard skip -- 50% WR (Exp 40)")
            elif symbol == "SENSEX":
                if po3_76 != "PO3_BULLISH":
                    action = "DO_NOTHING"
                    trade_allowed = False
                    out["action"] = "DO_NOTHING"
                    out["trade_allowed"] = False
                    cautions.append(
                        f"ENH-77: BULL_OB AFTERNOON SENSEX blocked -- po3_session_bias={po3_76} "
                        "(requires PO3_BULLISH)"
                    )
                else:
                    cautions.append(
                        "ENH-77: BULL_OB AFTERNOON SENSEX CONFIRMED -- "
                        "po3_session_bias=PO3_BULLISH (73.7% WR, Exp 40)"
                    )
    except Exception as _e7677:
        cautions.append(f"ENH-76/77: time gate skipped ({_e7677})")

    # ENH-78: DTE<3 PDH PO3_BEARISH -> current-week PE rule
    po3_78 = out.get("po3_session_bias", "PO3_NONE")
    enh78_active = (
        po3_78 == "PO3_BEARISH"
        and dte is not None
        and 1 <= dte <= 2
        and action == "BUY_PE"
    )
    if enh78_active:
        if dte == 1:
            trade_allowed = True
            out["trade_allowed"] = True
            confidence += 12.0
            confidence = max(0.0, min(100.0, confidence))
            out["confidence_score"] = round(confidence, 1)
            out["cautions"][:] = [c for c in out.get("cautions", []) if "DTE gate" not in c]
            out["reasons"].append(
                "ENH-78: DTE=1 gate lifted -- PO3_BEARISH PDH sweep, "
                "current-week PE (90.9% EOD WR, Exp 35D)"
            )
        else:
            out["reasons"].append(
                "ENH-78: DTE=2 PDH sweep confirmed -- current-week PE (90.9% EOD WR, Exp 35D)"
            )
        out["cautions"].append("ENH-78: Stop = 40% of entry premium OR price re-takes PDH")
        out["raw"]["enh78_triggered"] = True
        out["raw"]["enh78_dte"] = dte
        out["raw"]["enh78_stop_note"] = "40pct_premium_or_pdh_reclaim"
    elif dte is not None and 1 <= dte <= 2 and action == "BUY_PE":
        out["raw"]["enh78_triggered"] = False

    return out, flags


def insert_signal_replay(row: dict) -> None:
    SUPABASE.table("signal_snapshots_replay").insert(row).execute()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="replay_build_trade_signal")
    parser.add_argument("--replay-ts", required=True)
    parser.add_argument("--symbol", required=True, choices=["NIFTY", "SENSEX"])
    return parser.parse_args(argv)


def main() -> int:
    try:
        args = parse_args(sys.argv[1:])
    except SystemExit:
        raise

    try:
        replay_ts = parse_replay_ts(args.replay_ts)
    except ValueError as e:
        print(f"[ERROR] Invalid --replay-ts: {e}", file=sys.stderr)
        return 2

    symbol = args.symbol.upper()
    notes_prefix = f"signal_v4={SIGNAL_V4_ENABLED} replay_ts={args.replay_ts}"

    log = ExecutionLog(
        script_name="replay_build_trade_signal.py",
        expected_writes={"signal_snapshots_replay": 1},
        symbol=symbol,
        notes=notes_prefix,
    )

    try:
        _ensure_supabase()
    except Exception as e:
        return log.exit_with_reason("DEPENDENCY_MISSING", 1, error_message=f"Supabase init failed: {e}")

    try:
        row, flags = build_signal_replay(symbol, replay_ts)
    except RuntimeError as e:
        msg = str(e)
        if "No market_state_snapshots_replay row" in msg:
            return log.exit_with_reason("SKIPPED_NO_INPUT", 1, error_message=msg)
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"build_signal_replay RuntimeError: {msg}")
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"build_signal_replay unexpected: {e}")

    try:
        insert_signal_replay(row)
    except Exception as e:
        return log.exit_with_reason("DATA_ERROR", 1, error_message=f"signal_snapshots_replay insert failed: {e}")

    print("=" * 72)
    print("MERDIAN REPLAY - replay_build_trade_signal")
    print("=" * 72)
    print(f"replay_ts={args.replay_ts}")
    print(f"symbol={row.get('symbol')}")
    print(f"ts={row.get('ts')}")
    print(f"action={row.get('action')}")
    print(f"trade_allowed={row.get('trade_allowed')}")
    print(f"confidence_score={row.get('confidence_score')}")
    print(f"direction_bias={row.get('direction_bias')}")
    print(f"gamma_regime={row.get('gamma_regime')}")
    print(f"entry_quality={row.get('entry_quality')}")
    print(f"ict_pattern={row.get('ict_pattern')}")
    print(f"po3_session_bias={row.get('po3_session_bias')}")
    print(f"signal_v4={SIGNAL_V4_ENABLED}")

    log.record_write("signal_snapshots_replay", 1)

    completion_parts = [notes_prefix]
    if flags.get("ict_failed"):
        completion_parts.append("ict_failed=true")
    if flags.get("enh06_failed"):
        completion_parts.append("enh06_failed=true")
    completion_parts.append(f"action={row.get('action')}")

    return log.complete(notes=" ".join(completion_parts))


if __name__ == "__main__":
    sys.exit(main())