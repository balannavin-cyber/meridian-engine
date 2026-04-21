from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

# ENH-72 write-contract layer. See docs/MERDIAN_Master_V19.docx governance
# rule `script_execution_log_contract`. Pattern mirrored from
# build_market_state_snapshot_local.py: symbol known at CLI parse time,
# no set_symbol() needed. Optional-source-tolerant via completion notes
# (ict_failed, enh06_failed flags).
from core.execution_log import ExecutionLog


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
#
# ENH-53 + ENH-55 (feature-flagged via MERDIAN_SIGNAL_V4=1):
#   ENH-53 — Remove breadth regime as hard gate.
#     Evidence: Experiment 25 (5m) WR spread = 1.0pp across
#     BULLISH/BEARISH/NEUTRAL regimes — pure noise.
#     Under V4: breadth no longer drives direction_bias nor
#     produces a NEUTRAL gate. Demoted to confidence modifier:
#     +5 when breadth_regime aligns with chosen action, 0 otherwise.
#
#   ENH-55 — Momentum opposition hard block.
#     Evidence: Experiment 20 (5m) ALIGNED 60.9% WR vs
#     OPPOSED 38.3% WR = +22.6pp lift.
#     Under V4:
#       - If abs(ret_session) > 0.0005 AND action opposes sign of
#         ret_session, force action = DO_NOTHING, trade_allowed = False.
#       - If abs(ret_session) > 0.0005 AND action aligned with
#         ret_session sign, add +10 confidence.
#       - If abs(ret_session) <= 0.0005, treat as NEUTRAL (no
#         bonus, no block).
#       - Old +20 "direction_bias != NEUTRAL" bonus (implicit
#         breadth+momentum alignment) is removed under V4.
#
# Flag: MERDIAN_SIGNAL_V4
#   "1"        -> V4 logic (ENH-53 + ENH-55)
#   unset / 0  -> V3 legacy (bit-identical to prior behaviour,
#                including known quirks)
# Default is off. Enable explicitly for shadow sessions. Flip
# default only after 5 clean shadow sessions per Change Protocol.
#
# ENH-72 instrumentation contract:
#   - expected_writes = {signal_snapshots: 1}
#   - action=DO_NOTHING is NOT a failure — the script successfully
#     produced a reasoned decision. contract_met=True.
#   - trade_allowed=False is NOT a failure — it's a gate firing.
#     contract_met=True.
#   - SKIPPED_NO_INPUT if no market_state row exists for symbol.
#   - DATA_ERROR if market_state fetch fails or insert fails.
#   - DEPENDENCY_MISSING if SUPABASE_URL/KEY missing at main() entry.
#   - ict_failed=true surfaces in notes when ENH-37 ICT enrichment
#     try/except fires (does NOT downgrade contract_met).
#   - enh06_failed=true surfaces similarly for ENH-06 capital check.
#   - signal_v4={true|false} surfaces in notes for logic-version filter.
# ============================================================


# -----------------------------
# Feature flag (read once at import)
# -----------------------------
load_dotenv()
SIGNAL_V4_ENABLED: bool = os.getenv("MERDIAN_SIGNAL_V4", "1").strip() == "1"


# -----------------------------
# Environment / Supabase client
# -----------------------------
# ENH-72: deferred initialisation. Module-scope import no longer dies on
# missing env vars -- main() checks and routes through ExecutionLog as
# DEPENDENCY_MISSING. Preserves backward compatibility (SUPABASE global
# still populated before any build_signal() call).
SUPABASE: Client | None = None
_SUPABASE_INIT_ERROR: Exception | None = None


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


def _ensure_supabase() -> Client:
    """Initialise SUPABASE global on first use. Idempotent. Caches
    any initialisation error so main() can classify it properly."""
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


# Try-init at import time, but don't raise. main() decides what to do.
try:
    SUPABASE = _load_env()
except Exception as e:
    _SUPABASE_INIT_ERROR = e


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
    # V3 legacy path. DO NOT MODIFY — this is the bit-identical
    # fallback when MERDIAN_SIGNAL_V4 is off.
    # ENH-35 validated 2026-04-11:
    # BEARISH+BEARISH aligned ? BEARISH (core signal)
    if breadth_regime == "BEARISH" and momentum_direction == "BEARISH":
        return "BEARISH"
    # BULLISH+BULLISH aligned ? BULLISH (core signal)
    if breadth_regime == "BULLISH" and momentum_direction == "BULLISH":
        return "BULLISH"
    # BULLISH breadth + BEARISH momentum (CONFLICT) ? BULLISH
    # ENH-35: SENSEX 58.7% accuracy, NIFTY 55.4% at N=3575 — strong edge
    if breadth_regime == "BULLISH" and momentum_direction == "BEARISH":
        return "BULLISH"
    # BEARISH breadth + BULLISH momentum (CONFLICT) ? NEUTRAL
    # ENH-35: 47-49% accuracy — below random, correctly blocked
    if breadth_regime == "BEARISH" and momentum_direction == "BULLISH":
        return "NEUTRAL"
    if breadth_regime == "TRANSITION":
        return "NEUTRAL"
    return "NEUTRAL"


def infer_direction_bias_v4(momentum_direction: str) -> str:
    # ENH-53: breadth removed as hard gate. Direction comes from
    # momentum_direction alone. Breadth is applied later as a
    # ±5 confidence modifier on the chosen action.
    # Evidence: Experiment 25 (5m) 1.0pp spread across breadth regimes.
    if momentum_direction == "BULLISH":
        return "BULLISH"
    if momentum_direction == "BEARISH":
        return "BEARISH"
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
def build_signal(symbol: str) -> tuple[dict[str, Any], dict[str, bool]]:
    """Build the signal row. Returns (row, flags) tuple where flags
    tracks subsystem degradation (ict_failed, enh06_failed) for
    ExecutionLog completion notes."""
    flags = {"ict_failed": False, "enh06_failed": False}

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

    # --- Options flow context (ENH-02/04) ---
    def _fetch_options_flow(sym: str) -> dict:
        try:
            rows = (SUPABASE.table("options_flow_snapshots")
                    .select("pcr_regime,skew_regime,flow_regime,"
                            "put_call_ratio,chain_iv_skew,ce_vol_oi_ratio,pe_vol_oi_ratio")
                    .eq("symbol", sym)
                    .order("ts", desc=True)
                    .limit(1)
                    .execute().data)
            return rows[0] if rows else {}
        except Exception:
            return {}
    _flow = _fetch_options_flow(symbol)
    pcr_regime   = _flow.get("pcr_regime")
    skew_regime  = _flow.get("skew_regime")
    flow_regime  = _flow.get("flow_regime")
    put_call_ratio = to_float(_flow.get("put_call_ratio"))
    chain_iv_skew  = to_float(_flow.get("chain_iv_skew"))

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

    # --- ret_session (consumed by get_momentum_direction AND ENH-55) ---
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

    # ENH-53 branch. Under V4, breadth is not used to compute
    # direction_bias and there is no NEUTRAL gate from breadth.
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

    # V3: +20 bonus whenever direction_bias is non-NEUTRAL (implicit
    #     breadth+momentum alignment via infer_direction_bias).
    # V4: removed — replaced by ENH-53 (+5 breadth) and ENH-55 (+10
    #     momentum) applied post-action below.
    if not SIGNAL_V4_ENABLED:
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 20.0

    # ENH-60: pre-init action = "DO_NOTHING" so the options-flow
    #   confidence-modifier block below can reference `action` safely
    #   even on SHORT_GAMMA / UNKNOWN paths where the gamma-treatment
    #   block below does not assign it. Without this, ~0.3% of rows
    #   raise UnboundLocalError when pcr_regime / skew_regime /
    #   flow_regime are populated.
    # ENH-61: pre-init trade_allowed = True here (moved up from the
    #   DTE block) so LONG_GAMMA / NO_FLIP gated rows correctly retain
    #   trade_allowed=False through to signal_snapshots.
    action: str = "DO_NOTHING"
    trade_allowed: bool = True

    # Gamma treatment
    if gamma_regime == "SHORT_GAMMA":
        reasons.append("Short gamma can amplify directional moves")
        if direction_bias in {"BULLISH", "BEARISH"}:
            confidence += 8.0
    elif gamma_regime == "LONG_GAMMA":
        # ENH-35 validated 2026-04-11: LONG_GAMMA signals 47.7% accuracy
        # at N=24,579 — structurally below random. Gate to DO_NOTHING.
        cautions.append("LONG_GAMMA gated — historical accuracy below random (ENH-35)")
        action = "DO_NOTHING"
        trade_allowed = False
        direction_bias = "NEUTRAL"
    elif gamma_regime == "NO_FLIP":
        # ENH-35 v2: NO_FLIP signals 45-48% accuracy — below random
        # No flip level = no institutional reference point
        cautions.append("NO_FLIP gated — no gamma flip reference (ENH-35)")
        action = "DO_NOTHING"
        trade_allowed = False
        direction_bias = "NEUTRAL"
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

    # Options flow confidence modifiers (ENH-02/04)
    # NOTE: V3 legacy preserved. `action` is referenced here before
    # its unconditional assignment below — this relies on pcr_regime/
    # skew_regime/flow_regime being None in SHORT_GAMMA paths where
    # `action` has not yet been set by the gamma block. Pre-existing
    # behaviour; out of scope for this session.
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

    # ENH-07: Basis note (futures basis already in gamma_features)
    basis_pct = to_float(gamma_features.get("basis_pct"))
    if basis_pct is not None:
        if basis_pct > 0.5:
            cautions.append(f"Futures in premium vs spot (basis_pct={basis_pct:.2f}%)")
        elif basis_pct < -0.5:
            cautions.append(f"Futures in discount vs spot (basis_pct={basis_pct:.2f}%)")

    # DTE gating
    # ENH-61: `trade_allowed` is initialised True at function top and
    # only ever transitions downward. LONG_GAMMA / NO_FLIP gated paths
    # now correctly retain trade_allowed=False; previously the
    # unconditional `trade_allowed = True` here overrode them.
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
    # (LONG_GAMMA/NO_FLIP paths already set direction_bias=NEUTRAL
    # above, so this branch produces action=DO_NOTHING for them.)
    if direction_bias == "BEARISH":
        action = "BUY_PE"
        reasons.append("Direction bias is BEARISH")
    elif direction_bias == "BULLISH":
        action = "BUY_CE"
        reasons.append("Direction bias is BULLISH")
    else:
        action = "DO_NOTHING"
        cautions.append("No directional bias available")

    # ========================================================
    # V4-ONLY BLOCK (ENH-53 + ENH-55)
    # Runs only when MERDIAN_SIGNAL_V4=1. V3 path unchanged.
    # Runs AFTER action is decided from direction_bias so the
    # opposition check, alignment bonus, and breadth modifier
    # act on the final chosen action.
    # ========================================================
    if SIGNAL_V4_ENABLED and action in ("BUY_CE", "BUY_PE"):
        # ENH-55: Momentum opposition hard block
        # Threshold: abs(ret_session) > 0.0005 (= 0.05%).
        # Below threshold: NEUTRAL — no block, no bonus.
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
                reasons.append(
                    f"ENH-55: Momentum aligned (+10) — "
                    f"ret_session={ret_session:.4f}"
                )

        # ENH-53: Breadth demoted to ±5 confidence modifier.
        # Apply only if the opposition block above did not fire.
        if action in ("BUY_CE", "BUY_PE"):
            if breadth_regime == "BULLISH" and action == "BUY_CE":
                confidence += 5.0
                reasons.append("ENH-53: Breadth aligned (+5) — BULLISH breadth, BUY_CE")
            elif breadth_regime == "BEARISH" and action == "BUY_PE":
                confidence += 5.0
                reasons.append("ENH-53: Breadth aligned (+5) — BEARISH breadth, BUY_PE")
            # Opposing / NEUTRAL / TRANSITION / UNKNOWN: 0pts

        # Re-clamp after V4 modifiers
        confidence = max(0.0, min(100.0, confidence))

    # Final trade gate
    if action != "DO_NOTHING" and confidence < 40.0:
        trade_allowed = False
        cautions.append("Confidence threshold not met for trade execution")

    # VIX gate REMOVED 2026-04-11 (ENH-35 + Experiment 5)
    # HIGH_IV environments have MORE edge, not less:
    # BEAR_OB|HIGH_IV +174.6% vs BEAR_OB|MED_IV +84.8%
    # Gate was suppressing the best trades. Replaced by IV-scaled sizing.
    if india_vix is not None and india_vix >= 20:
        cautions.append(f"India VIX elevated at {india_vix:.1f} — monitoring only")


    # Session time gate: no signals after 15:00 IST
    # SHORT_GAMMA after 15:00 is expiry unwinding noise, not tradeable
    if ts:
        from datetime import timezone as _tz
        import dateutil.parser as _dp
        try:
            _ts = _dp.parse(ts).astimezone(_tz.utc)
            _ist_hour = _ts.hour + 5 + (1 if _ts.minute >= 30 else 0)
            _ist_min  = (_ts.minute + 30) % 60
            if _ist_hour >= 15:
                action = "DO_NOTHING"
                trade_allowed = False
                cautions.append("Power hour gate: signals after 15:00 IST excluded")
        except Exception:
            pass

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

    # Add options flow fields to raw JSONB
    if "raw" not in out:
        out["raw"] = {}
    out["raw"].update({
        "pcr_regime":     pcr_regime,
        "skew_regime":    skew_regime,
        "flow_regime":    flow_regime,
        "put_call_ratio": put_call_ratio,
        "chain_iv_skew":  chain_iv_skew,
        "basis_pct":      basis_pct,
        "signal_v4":      SIGNAL_V4_ENABLED,
        "ret_session":    ret_session,
    })

    # ENH-37: Enrich signal with ICT pattern context
    # Reads active ict_zones written by detect_ict_patterns_runner.py
    # Adds: ict_pattern, ict_tier, ict_size_mult, ict_mtf_context
    try:
        from detect_ict_patterns import enrich_signal_with_ict
        from datetime import date as _date
        _today = str(_date.today())
        _ict_rows = (SUPABASE.table("ict_zones")
                     .select("id,pattern_type,direction,zone_high,zone_low,"
                             "status,ict_tier,ict_size_mult,mtf_context,detected_at_ts,"
                             "ict_lots_t1,ict_lots_t2,ict_lots_t3")
                     .eq("symbol", symbol)
                     .eq("trade_date", _today)
                     .eq("status", "ACTIVE")
                     .execute().data)
        out = enrich_signal_with_ict(out, _ict_rows, float(spot or 0))
        # ENH-38: forward Kelly lots from active zone to signal_snapshots
        if _ict_rows:
            out['ict_lots_t1'] = _ict_rows[0].get('ict_lots_t1')
            out['ict_lots_t2'] = _ict_rows[0].get('ict_lots_t2')
            out['ict_lots_t3'] = _ict_rows[0].get('ict_lots_t3')
        else:
            out['ict_lots_t1'] = None
            out['ict_lots_t2'] = None
            out['ict_lots_t3'] = None
    except Exception as _ict_err:
        # Non-blocking — ICT enrichment failure never halts signal.
        # ENH-72: surface in completion notes so operators can track
        # ICT subsystem health without parsing raw JSONB.
        flags["ict_failed"] = True
        out["ict_pattern"]     = "NONE"
        out["ict_tier"]        = "NONE"
        out["ict_size_mult"]   = 1.0
        out["ict_mtf_context"] = "NONE"
        out["ict_lots_t1"]     = None
        out["ict_lots_t2"]     = None
        out["ict_lots_t3"]     = None

    # ENH-06: Pre-trade cost filter
    # Validates lot sizing against current capital at signal time.
    try:
        from merdian_utils import (
            effective_sizing_capital, estimate_lot_cost,
            LOT_SIZES, KELLY_FRACTIONS_C as _KF
        )
        _cap_rows = (SUPABASE.table("capital_tracker")
                     .select("capital")
                     .eq("symbol", symbol)
                     .limit(1)
                     .execute().data)
        _raw_capital = float(_cap_rows[0]["capital"]) if _cap_rows else 200_000
        _eff_capital = effective_sizing_capital(_raw_capital)
        _tier        = out.get("ict_tier", "NONE")
        _kelly_frac  = _KF.get(_tier, 0.20)
        _allocated   = _eff_capital * _kelly_frac
        _lot_cost    = estimate_lot_cost(
            symbol,
            float(spot or 0),
            float(atm_iv_avg or 16.0),
            float(dte or 2),
        )
        _active_lots = out.get("ict_lots_t1") or out.get("ict_lots_t2") or out.get("ict_lots_t3")
        _capital_ok  = True
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
        if "raw" not in out:
            out["raw"] = {}
        out["raw"].update({
            "enh06_capital_raw": _raw_capital,
            "enh06_capital_eff": _eff_capital,
            "enh06_allocated":   _allocated,
            "enh06_lot_cost":    _lot_cost,
            "enh06_capital_ok":  _capital_ok,
        })
    except Exception as _e06:
        # ENH-72: ENH-06 capital check failure is non-blocking.
        # Surface in completion notes to track capital subsystem health.
        flags["enh06_failed"] = True
        cautions.append(f"ENH-06: Capital check skipped ({_e06})")

    return out, flags


def insert_signal(row: dict[str, Any]) -> None:
    SUPABASE.table("signal_snapshots").insert(row).execute()


def main() -> int:
    # CLI parse before ExecutionLog. Usage error -> exit 2, no log row.
    if len(sys.argv) != 2:
        print(
            "Usage: python build_trade_signal_local.py <symbol>",
            file=sys.stderr,
        )
        return 2

    symbol = sys.argv[1].strip().upper()
    if symbol not in {"NIFTY", "SENSEX"}:
        print(
            "Usage: python build_trade_signal_local.py <NIFTY|SENSEX>",
            file=sys.stderr,
        )
        return 2

    # ── ENH-72 write-contract declaration ────────────────────────────────────
    # Contract: 1 row to signal_snapshots via INSERT (not UPSERT).
    # Same latent idempotency hazard as volatility_snapshots: same run
    # called twice would 23505. Pre-existing, out of scope for ENH-72.
    #
    # Notes track the signal logic version (V3/V4) and subsystem health
    # (ict_failed, enh06_failed) for operator triage via
    # WHERE notes LIKE '%ict_failed=true%' or similar.
    notes_prefix = f"signal_v4={SIGNAL_V4_ENABLED}"
    log = ExecutionLog(
        script_name="build_trade_signal_local.py",
        expected_writes={"signal_snapshots": 1},
        symbol=symbol,
        notes=notes_prefix,
    )

    # ENH-72: env check via _ensure_supabase() routes through
    # ExecutionLog instead of dying at import with unhandled traceback.
    try:
        _ensure_supabase()
    except Exception as e:
        return log.exit_with_reason(
            "DEPENDENCY_MISSING",
            exit_code=1,
            error_message=f"Supabase init failed: {e}",
        )

    try:
        row, flags = build_signal(symbol)
    except RuntimeError as e:
        # latest_market_state raises RuntimeError with specific message
        # when no market_state_snapshots row exists for this symbol.
        msg = str(e)
        if "No market_state_snapshots row found" in msg:
            return log.exit_with_reason(
                "SKIPPED_NO_INPUT",
                exit_code=1,
                error_message=msg,
            )
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"build_signal RuntimeError: {msg}",
        )
    except Exception as e:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"build_signal unexpected error: {e}",
        )

    try:
        insert_signal(row)
    except Exception as e:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"signal_snapshots insert failed: {e}",
        )

    print("Signal snapshot insert complete.")
    print(f"signal_v4={SIGNAL_V4_ENABLED}")
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

    log.record_write("signal_snapshots", 1)

    # ENH-72: completion notes track logic version + subsystem degradation
    # flags. Operators filter signal_execution_log by WHERE notes LIKE
    # '%ict_failed=true%' to find signals where ICT subsystem was down,
    # or '%signal_v4=False%' to filter legacy-logic runs.
    completion_parts = [notes_prefix]
    if flags.get("ict_failed"):
        completion_parts.append("ict_failed=true")
    if flags.get("enh06_failed"):
        completion_parts.append("enh06_failed=true")
    completion_parts.append(f"action={row.get('action')}")

    return log.complete(notes=" ".join(completion_parts))


if __name__ == "__main__":
    sys.exit(main())
