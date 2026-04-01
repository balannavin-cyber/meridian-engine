from __future__ import annotations

"""
detect_structural_manipulation.py
==================================
MERDIAN -- Structural Manipulation Detection Module (SMDM)

Implements SMDM Spec V7 against V18 live system.
Writes to structural_alerts table only.
Does NOT touch smdm_snapshots -- that table is owned by compute_smdm_local.py.

Pipeline position:
    After compute_smdm_local.py, before build_shadow_signal_v3_local.py.

Run modes:
    python detect_structural_manipulation.py NIFTY
    python detect_structural_manipulation.py NIFTY <run_id>
    python detect_structural_manipulation.py NIFTY PARTIAL

SMDM Spec V7 patterns implemented:
    Expiry day (DTE=0):
        EXPIRY_SQUEEZE -- 5-condition weighted score, alert at >= 4.0
    Non-expiry (DTE >= 1):
        GAMMA_PINNING, STOP_HUNT, OPENING_GAP, ROLLOVER_WINDOW
"""

import os
import sys
import re
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

# ---------------------------------------------------------------------------
# Configurable thresholds (Spec V7 Section 9)
# ---------------------------------------------------------------------------

SQUEEZE_ALERT_THRESHOLD         = 4.0
OTM_BLEED_THRESHOLD             = 0.75
STRADDLE_BLEED_THRESHOLD        = 0.40
STRADDLE_VELOCITY_FAST_BLEED    = -0.04
STRADDLE_BLEED_FAST_THRESHOLD   = 0.30
FLIP_PROXIMITY_THRESHOLD        = 0.003
OTM_OI_VELOCITY_THRESHOLD       = 0.10
VIX_STRADDLE_RATIO_HIGH         = 1.08
STOP_HUNT_BREADTH_SCORE_DROP    = -15.0
STOP_HUNT_VOLUME_RATIO_LOW      = 0.70
OPENING_GAP_THRESHOLD           = 0.005
OI_SIGNIFICANCE_THRESHOLD       = 50_000
ROLLOVER_DTE_WINDOW_MIN         = 3
ROLLOVER_DTE_WINDOW_MAX         = 5
MIN_OTM_DISTANCE_STEPS          = 2
SQUEEZE_WINDOW_START_HOUR       = 12
SQUEEZE_WINDOW_START_MIN        = 30
SQUEEZE_WINDOW_END_HOUR         = 14
SQUEEZE_WINDOW_END_MIN          = 30


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def get_supabase_config() -> Tuple[str, Dict[str, str]]:
    url = get_env("SUPABASE_URL").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or \
          os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    return url, headers


def supabase_select(
    table: str,
    params: Dict[str, str],
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    url, headers = get_supabase_config()
    full_url = f"{url}/rest/v1/{table}?{urlencode(params)}"
    resp = requests.get(full_url, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase SELECT failed ({resp.status_code}) on {table}: {resp.text[:300]}"
        )
    data = resp.json()
    return data if isinstance(data, list) else []


def supabase_upsert(
    table: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    if not rows:
        return []
    url, headers = get_supabase_config()
    full_url = f"{url}/rest/v1/{table}?on_conflict={on_conflict}"
    resp = requests.post(full_url, headers=headers, json=rows, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Supabase UPSERT failed ({resp.status_code}) on {table}: {resp.text[:300]}"
        )
    data = resp.json()
    if isinstance(data, list):
        return data
    return [data] if isinstance(data, dict) else []


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------

def to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        r = float(v)
        return None if (math.isnan(r) or math.isinf(r)) else r
    except Exception:
        return None


def to_int(v: Any) -> Optional[int]:
    try:
        return int(float(v)) if v is not None else None
    except Exception:
        return None


def parse_ts(v: Any) -> Optional[datetime]:
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

def fetch_latest(table: str, symbol: str, columns: str = "*") -> Optional[Dict[str, Any]]:
    rows = supabase_select(table, {
        "select": columns,
        "symbol": f"eq.{symbol}",
        "order": "created_at.desc",
        "limit": "1",
    })
    return rows[0] if rows else None


def fetch_recent_breadth(symbol: str, limit: int = 3) -> List[Dict[str, Any]]:
    # market_breadth_intraday is a single-universe table with no symbol column
    rows = supabase_select("market_breadth_intraday", {
        "select": "breadth_score,ts",
        "order": "ts.desc",
        "limit": str(limit),
    })
    return sorted(rows, key=lambda r: r.get("ts") or "")


def fetch_option_chain_for_run(run_id: str, symbol: str) -> List[Dict[str, Any]]:
    if not run_id:
        return []
    rows = supabase_select("option_chain_snapshots", {
        "select": "strike,option_type,ltp,oi,iv,spot",
        "run_id": f"eq.{run_id}",
        "symbol": f"eq.{symbol}",
        "limit": "2000",
    })
    return rows


def fetch_latest_intraday_ohlc(symbol: str) -> Optional[Dict[str, Any]]:
    rows = supabase_select("intraday_ohlc", {
        "select": "close,open,session_high,session_low,ts",
        "symbol": f"eq.{symbol}_SPOT",
        "order": "ts.desc",
        "limit": "1",
    })
    return rows[0] if rows else None


def fetch_prior_close(symbol: str) -> Optional[float]:
    rows = supabase_select("intraday_ohlc", {
        "select": "close,ts",
        "symbol": f"eq.{symbol}_SPOT",
        "order": "ts.desc",
        "limit": "100",
    })
    if not rows:
        return None
    latest_ts = parse_ts(rows[0].get("ts"))
    if latest_ts:
        today = latest_ts.date()
        for row in rows[1:]:
            row_ts = parse_ts(row.get("ts"))
            if row_ts and row_ts.date() < today:
                return to_float(row.get("close"))
    return None


def is_first_run_of_session(symbol: str, current_ts: datetime) -> bool:
    today_start = current_ts.replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    rows = supabase_select("structural_alerts", {
        "select": "id",
        "symbol": f"eq.{symbol}",
        "ts": f"gte.{today_start}",
        "limit": "1",
    })
    return len(rows) == 0


def get_atm_open_ltp(symbol: str, option_type: str, atm_strike: float) -> Optional[float]:
    rows = supabase_select("option_chain_snapshots", {
        "select": "ltp,created_at",
        "symbol": f"eq.{symbol}",
        "strike": f"eq.{atm_strike}",
        "option_type": f"eq.{option_type}",
        "order": "created_at.asc",
        "limit": "1",
    })
    return to_float(rows[0].get("ltp")) if rows else None


# ---------------------------------------------------------------------------
# ATM / strike helpers
# ---------------------------------------------------------------------------

def find_atm_strike(option_rows: List[Dict[str, Any]], spot: float) -> Optional[float]:
    strikes = sorted({
        to_float(r.get("strike")) for r in option_rows
        if to_float(r.get("strike")) and (to_float(r.get("strike")) or 0) > 0
    })
    if not strikes:
        return None
    return min(strikes, key=lambda s: abs(s - spot))


def infer_strike_step(option_rows: List[Dict[str, Any]]) -> Optional[float]:
    strikes = sorted({
        to_float(r.get("strike")) for r in option_rows
        if to_float(r.get("strike")) and (to_float(r.get("strike")) or 0) > 0
    })
    if len(strikes) < 2:
        return None
    diffs = [
        strikes[i] - strikes[i-1]
        for i in range(1, len(strikes))
        if strikes[i] > strikes[i-1]
    ]
    return min(diffs) if diffs else None


# ---------------------------------------------------------------------------
# IST time helpers
# ---------------------------------------------------------------------------

def ist_time(ts: datetime) -> Tuple[int, int]:
    ist_offset = timedelta(hours=5, minutes=30)
    ist_ts = ts.astimezone(UTC) + ist_offset
    return ist_ts.hour, ist_ts.minute


def in_squeeze_window(ts: datetime) -> bool:
    h, m = ist_time(ts)
    after_start = (
        h > SQUEEZE_WINDOW_START_HOUR or
        (h == SQUEEZE_WINDOW_START_HOUR and m >= SQUEEZE_WINDOW_START_MIN)
    )
    before_end = (
        h < SQUEEZE_WINDOW_END_HOUR or
        (h == SQUEEZE_WINDOW_END_HOUR and m <= SQUEEZE_WINDOW_END_MIN)
    )
    return after_start and before_end


def time_window_score(ts: datetime) -> float:
    if in_squeeze_window(ts):
        return 1.0
    h, m = ist_time(ts)
    total_mins = h * 60 + m
    window_start_mins = SQUEEZE_WINDOW_START_HOUR * 60 + SQUEEZE_WINDOW_START_MIN
    if window_start_mins - 30 <= total_mins < window_start_mins:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# Expiry squeeze conditions
# ---------------------------------------------------------------------------

def cond_otm_bleed(
    option_rows: List[Dict[str, Any]],
    spot: float,
    symbol: str,
    morning_direction: str,
    straddle_velocity: Optional[float],
) -> Tuple[bool, float]:
    atm_strike = find_atm_strike(option_rows, spot)
    strike_step = infer_strike_step(option_rows)
    if atm_strike is None or strike_step is None:
        return False, 0.0

    threshold = STRADDLE_BLEED_THRESHOLD
    if straddle_velocity is not None and straddle_velocity < STRADDLE_VELOCITY_FAST_BLEED:
        threshold = STRADDLE_BLEED_FAST_THRESHOLD

    otm_opt_type = "CE" if morning_direction == "DOWN" else "PE"
    otm_strike = (
        atm_strike - (MIN_OTM_DISTANCE_STEPS * strike_step)
        if otm_opt_type == "PE"
        else atm_strike + (MIN_OTM_DISTANCE_STEPS * strike_step)
    )

    current_ltp = None
    for r in option_rows:
        if (to_float(r.get("strike")) == otm_strike and
                str(r.get("option_type", "")).upper() == otm_opt_type):
            current_ltp = to_float(r.get("ltp"))
            break

    if current_ltp is None:
        return False, 0.0

    open_ltp = get_atm_open_ltp(symbol, otm_opt_type, otm_strike)
    if open_ltp is None or open_ltp <= 0:
        return False, 0.0

    bleed_pct = (open_ltp - current_ltp) / open_ltp
    return bleed_pct >= OTM_BLEED_THRESHOLD, round(bleed_pct, 4)


def cond_straddle_bleed(
    straddle_atm: Optional[float],
    symbol: str,
    spot: float,
    option_rows: List[Dict[str, Any]],
    straddle_velocity: Optional[float],
) -> bool:
    if straddle_atm is None:
        return False

    atm_strike = find_atm_strike(option_rows, spot)
    if atm_strike is None:
        return False

    ce_open = get_atm_open_ltp(symbol, "CE", atm_strike)
    pe_open = get_atm_open_ltp(symbol, "PE", atm_strike)
    if ce_open is None or pe_open is None or (ce_open + pe_open) <= 0:
        return False

    open_straddle = ce_open + pe_open
    bleed_pct = (open_straddle - straddle_atm) / open_straddle

    threshold = STRADDLE_BLEED_THRESHOLD
    if straddle_velocity is not None and straddle_velocity < STRADDLE_VELOCITY_FAST_BLEED:
        threshold = STRADDLE_BLEED_FAST_THRESHOLD

    return bleed_pct >= threshold


def cond_flip_proximity(flip_distance_pct: Optional[float]) -> bool:
    if flip_distance_pct is None:
        return False
    return flip_distance_pct <= (FLIP_PROXIMITY_THRESHOLD * 100)


def cond_short_gamma(regime: Optional[str]) -> bool:
    return str(regime or "").upper() == "SHORT_GAMMA"


def compute_expiry_squeeze_score(
    gamma_row: Dict[str, Any],
    option_rows: List[Dict[str, Any]],
    symbol: str,
    current_ts: datetime,
    run_type: str,
) -> Tuple[float, str, Dict[str, bool], float]:
    spot = to_float(gamma_row.get("spot")) or 0.0
    straddle_atm = to_float(gamma_row.get("straddle_atm"))
    straddle_velocity = to_float(gamma_row.get("straddle_velocity"))
    flip_distance_pct = to_float(gamma_row.get("flip_distance_pct"))
    regime = gamma_row.get("regime")

    ohlc = fetch_latest_intraday_ohlc(symbol)
    morning_direction = "FLAT"
    if ohlc:
        close = to_float(ohlc.get("close")) or 0.0
        open_price = to_float(ohlc.get("open")) or 0.0
        if close > open_price * 1.002:
            morning_direction = "UP"
        elif close < open_price * 0.998:
            morning_direction = "DOWN"

    c_otm, otm_bleed_pct = cond_otm_bleed(
        option_rows, spot, symbol, morning_direction, straddle_velocity
    )
    c_straddle = cond_straddle_bleed(
        straddle_atm, symbol, spot, option_rows, straddle_velocity
    )
    c_flip = cond_flip_proximity(flip_distance_pct)
    tw_score = time_window_score(current_ts)
    c_time = tw_score > 0
    c_short_gamma = cond_short_gamma(regime)

    score = 0.0
    if c_otm:
        score += 1.0
    if c_straddle:
        score += 1.0
    if c_flip:
        score += 1.0
    score += tw_score
    if c_short_gamma:
        score += 1.0

    # VIX confirmation
    vix = to_float(gamma_row.get("vix"))
    if vix and straddle_atm and vix > 0:
        ratio = straddle_atm / vix
        if ratio >= VIX_STRADDLE_RATIO_HIGH:
            score += 0.5

    conditions = {
        "cond_otm_bleed": c_otm,
        "cond_straddle_bleed": c_straddle,
        "cond_flip_proximity": c_flip,
        "cond_time_window": c_time,
        "cond_short_gamma": c_short_gamma,
    }

    confidence = "FULL" if run_type == "FULL" else "PARTIAL"
    return round(min(score, 5.0), 2), confidence, conditions, otm_bleed_pct


# ---------------------------------------------------------------------------
# Non-expiry patterns
# ---------------------------------------------------------------------------

def detect_gamma_pinning(
    gamma_row: Dict[str, Any],
    breadth_rows: List[Dict[str, Any]],
) -> bool:
    flip_pct = to_float(gamma_row.get("flip_distance_pct"))
    if flip_pct is None or flip_pct > 0.2:
        return False
    if len(breadth_rows) < 2:
        return False
    scores = [to_float(r.get("breadth_score")) for r in breadth_rows[-2:]]
    if any(s is None for s in scores):
        return False
    return abs(scores[-1] - scores[-2]) < 3.0


def detect_stop_hunt(
    gamma_row: Dict[str, Any],
    breadth_rows: List[Dict[str, Any]],
    intraday_ohlc: Optional[Dict[str, Any]],
) -> Tuple[bool, Optional[float], Optional[float]]:
    net_gex = to_float(gamma_row.get("net_gex")) or 0.0
    if net_gex <= 0:
        return False, None, None
    if len(breadth_rows) < 2:
        return False, None, None
    scores = [to_float(r.get("breadth_score")) for r in breadth_rows[-2:]]
    if any(s is None for s in scores):
        return False, None, None
    breadth_change = scores[-1] - scores[-2]
    if breadth_change >= STOP_HUNT_BREADTH_SCORE_DROP:
        return False, None, None
    move_volume_ratio = STOP_HUNT_VOLUME_RATIO_LOW if intraday_ohlc else None
    return True, round(breadth_change, 2), move_volume_ratio


def detect_opening_gap(
    symbol: str,
    option_rows: List[Dict[str, Any]],
    spot: float,
    current_ts: datetime,
) -> Tuple[bool, Optional[float], Optional[float]]:
    if not is_first_run_of_session(symbol, current_ts):
        return False, None, None
    prior_close = fetch_prior_close(symbol)
    if prior_close is None or prior_close <= 0:
        return False, None, None
    gap_pct = (spot - prior_close) / prior_close
    if abs(gap_pct) < OPENING_GAP_THRESHOLD:
        return False, None, None
    gap_direction = 1 if gap_pct > 0 else -1
    target_strike = None
    max_oi = 0.0
    for r in option_rows:
        strike = to_float(r.get("strike")) or 0.0
        oi = to_float(r.get("oi")) or 0.0
        opt_type = str(r.get("option_type", "")).upper()
        if oi < OI_SIGNIFICANCE_THRESHOLD:
            continue
        if gap_direction > 0 and opt_type == "CE" and strike > spot:
            if oi > max_oi:
                max_oi = oi
                target_strike = strike
        elif gap_direction < 0 and opt_type == "PE" and strike < spot:
            if oi > max_oi:
                max_oi = oi
                target_strike = strike
    if target_strike is None:
        return False, None, None
    return True, round(gap_pct, 4), target_strike


def detect_rollover_window(
    dte: Optional[int],
    breadth_rows: List[Dict[str, Any]],
) -> bool:
    if dte is None or not (ROLLOVER_DTE_WINDOW_MIN <= dte <= ROLLOVER_DTE_WINDOW_MAX):
        return False
    if len(breadth_rows) < 3:
        return False
    scores = [to_float(r.get("breadth_score")) for r in breadth_rows[-3:]]
    if any(s is None for s in scores):
        return False
    up = scores[1] > scores[0] and scores[2] > scores[1]
    down = scores[1] < scores[0] and scores[2] < scores[1]
    return up or down


# ---------------------------------------------------------------------------
# Cautions
# ---------------------------------------------------------------------------

def build_cautions(
    dte: Optional[int],
    squeeze_score: float,
    squeeze_alert: bool,
    score_confidence: str,
    conditions: Dict[str, bool],
    gamma_pinning: bool,
    stop_hunt: bool,
    opening_gap: bool,
    rollover_window: bool,
    otm_oi_velocity: Optional[float],
    vix_straddle_ratio: Optional[float],
    straddle_velocity: Optional[float],
    breadth_score_change: Optional[float],
) -> List[str]:
    cautions = []
    if dte == 0:
        if squeeze_alert:
            cautions.append(
                f"EXPIRY SQUEEZE ALERT -- score={squeeze_score:.1f}/5.0 ({score_confidence})"
            )
        elif squeeze_score >= 3.0:
            cautions.append(f"Expiry squeeze building -- score={squeeze_score:.1f}/5.0")
        if conditions.get("cond_otm_bleed"):
            cautions.append("OTM bleed threshold exceeded -- cheap OTMs available")
        if conditions.get("cond_straddle_bleed"):
            cautions.append("Straddle collapsed -- IV crush in progress")
        if straddle_velocity is not None and straddle_velocity < STRADDLE_VELOCITY_FAST_BLEED:
            cautions.append("STRADDLE BLEED ACCELERATING")
        if conditions.get("cond_flip_proximity"):
            cautions.append("Spot within 0.3% of gamma flip -- dealer amplification risk")
        if conditions.get("cond_time_window"):
            cautions.append("In squeeze window (12:30-14:30 IST) -- minimum liquidity")
        if otm_oi_velocity is not None and otm_oi_velocity >= OTM_OI_VELOCITY_THRESHOLD:
            cautions.append(
                f"OTM OI velocity spike -- {otm_oi_velocity:.1%} increase (pre-squeeze accumulation)"
            )
        if vix_straddle_ratio is not None and vix_straddle_ratio >= VIX_STRADDLE_RATIO_HIGH:
            cautions.append("VIX/straddle divergence -- straddle rich relative to VIX")
    if gamma_pinning:
        cautions.append("GAMMA PINNING ACTIVE -- spot gravitating toward flip level")
    if stop_hunt:
        if breadth_score_change is not None:
            cautions.append(
                f"STOP HUNT RISK -- breadth collapsed {breadth_score_change:.1f}pts vs LONG_GAMMA"
            )
        else:
            cautions.append("STOP HUNT RISK -- breadth/gamma divergence detected")
    if opening_gap:
        cautions.append("OPENING GAP -- gap toward high-OI strike detected")
    if rollover_window:
        cautions.append("ROLLOVER WINDOW -- institutional futures rolling likely")
    if otm_oi_velocity is not None and otm_oi_velocity >= OTM_OI_VELOCITY_THRESHOLD and dte != 0:
        cautions.append(
            f"OTM OI velocity spike -- {otm_oi_velocity:.1%} increase (standalone alert)"
        )
    return cautions


# ---------------------------------------------------------------------------
# Main detection
# ---------------------------------------------------------------------------

def detect(
    symbol: str,
    run_id: Optional[str] = None,
    run_type: str = "FULL",
) -> Optional[Dict[str, Any]]:
    current_ts = datetime.now(UTC)

    gamma_row = fetch_latest(
        "gamma_metrics", symbol,
        "regime,net_gex,flip_level,flip_distance_pct,straddle_atm,"
        "straddle_velocity,otm_oi_velocity,spot_vs_range,run_id,"
        "run_type,vix,spot,gamma_concentration,raw"
    )
    if not gamma_row:
        print(f"  [{symbol}] No gamma_metrics row -- skipping")
        return None

    effective_run_id = run_id or str(gamma_row.get("run_id") or "")
    spot = to_float(gamma_row.get("spot")) or 0.0
    straddle_velocity = to_float(gamma_row.get("straddle_velocity"))
    otm_oi_velocity = to_float(gamma_row.get("otm_oi_velocity"))

    breadth_rows = fetch_recent_breadth(symbol, limit=3)
    intraday_ohlc = fetch_latest_intraday_ohlc(symbol)
    option_rows = fetch_option_chain_for_run(effective_run_id, symbol) if effective_run_id else []

    vol_row = fetch_latest(
        "volatility_snapshots", symbol, "atm_iv_vs_vix_spread,india_vix,atm_iv_avg,dte"
    )
    # dte lives in volatility_snapshots, not gamma_metrics
    dte = to_int(vol_row.get("dte")) if vol_row else None
    vix_straddle_ratio = None
    if vol_row:
        vix = to_float(vol_row.get("india_vix"))
        atm_iv = to_float(vol_row.get("atm_iv_avg"))
        if vix and atm_iv and vix > 0:
            vix_straddle_ratio = round(atm_iv / vix, 4)

    # Expiry squeeze
    squeeze_score = 0.0
    score_confidence = "FULL"
    conditions: Dict[str, bool] = {}
    squeeze_alert = False
    otm_bleed_pct_val = None

    if dte == 0:
        squeeze_score, score_confidence, conditions, otm_bleed_pct_val = \
            compute_expiry_squeeze_score(
                gamma_row, option_rows, symbol, current_ts, run_type
            )
        squeeze_alert = False if run_type == "PARTIAL" else (
            squeeze_score >= SQUEEZE_ALERT_THRESHOLD
        )

    # Non-expiry patterns
    gamma_pinning = False
    stop_hunt_risk = False
    opening_gap_alert = False
    rollover_window_flag = False
    breadth_score_change = None
    move_volume_ratio = None
    opening_gap_pct = None
    gap_target_strike = None

    if dte is None or dte > 0:
        gamma_pinning = detect_gamma_pinning(gamma_row, breadth_rows)
        stop_hunt_risk, breadth_score_change, move_volume_ratio = detect_stop_hunt(
            gamma_row, breadth_rows, intraday_ohlc
        )
        opening_gap_alert, opening_gap_pct, gap_target_strike = detect_opening_gap(
            symbol, option_rows, spot, current_ts
        )
        rollover_window_flag = detect_rollover_window(dte, breadth_rows)

    cautions = build_cautions(
        dte=dte,
        squeeze_score=squeeze_score,
        squeeze_alert=squeeze_alert,
        score_confidence=score_confidence,
        conditions=conditions,
        gamma_pinning=gamma_pinning,
        stop_hunt=stop_hunt_risk,
        opening_gap=opening_gap_alert,
        rollover_window=rollover_window_flag,
        otm_oi_velocity=otm_oi_velocity,
        vix_straddle_ratio=vix_straddle_ratio,
        straddle_velocity=straddle_velocity,
        breadth_score_change=breadth_score_change,
    )

    return {
        "run_id": effective_run_id or None,
        "symbol": symbol,
        "ts": current_ts.isoformat(),
        "run_type": run_type,
        "dte": dte,
        "squeeze_score": squeeze_score if dte == 0 else None,
        "squeeze_alert": squeeze_alert,
        "score_confidence": score_confidence if dte == 0 else None,
        "cond_otm_bleed": conditions.get("cond_otm_bleed"),
        "cond_straddle_bleed": conditions.get("cond_straddle_bleed"),
        "cond_flip_proximity": conditions.get("cond_flip_proximity"),
        "cond_time_window": conditions.get("cond_time_window"),
        "cond_short_gamma": conditions.get("cond_short_gamma"),
        "straddle_velocity": straddle_velocity,
        "otm_oi_velocity": otm_oi_velocity,
        "vix_straddle_ratio": vix_straddle_ratio,
        "otm_bleed_pct": otm_bleed_pct_val,
        "gamma_pinning": gamma_pinning,
        "stop_hunt_risk": stop_hunt_risk,
        "opening_gap_alert": opening_gap_alert,
        "rollover_window": rollover_window_flag,
        "cautions": cautions,
        "breadth_score_change": breadth_score_change,
        "move_volume_ratio": move_volume_ratio,
        "opening_gap_pct": opening_gap_pct,
        "gap_target_strike": gap_target_strike,
        "created_at": current_ts.isoformat(),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 72)
    print("MERDIAN -- detect_structural_manipulation")
    print("=" * 72)

    if len(sys.argv) < 2:
        print("Usage: python detect_structural_manipulation.py <symbol> [run_id] [FULL|PARTIAL]")
        return 1

    symbol = sys.argv[1].upper()
    run_id = None
    run_type = "FULL"

    UUID_RE = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    for arg in sys.argv[2:]:
        if UUID_RE.match(arg.strip()):
            run_id = arg.strip()
        elif arg.upper() in {"FULL", "PARTIAL"}:
            run_type = arg.upper()

    print(f"symbol={symbol}  run_type={run_type}  run_id={run_id or 'from gamma_metrics'}")

    row = detect(symbol, run_id=run_id, run_type=run_type)
    if row is None:
        print(f"No row produced for {symbol}")
        return 1

    print(f"squeeze_alert={row['squeeze_alert']}")
    print(f"squeeze_score={row['squeeze_score']}")
    print(f"dte={row['dte']}")
    print(f"gamma_pinning={row['gamma_pinning']}")
    print(f"stop_hunt_risk={row['stop_hunt_risk']}")
    print(f"opening_gap_alert={row['opening_gap_alert']}")
    print(f"rollover_window={row['rollover_window']}")
    print(f"straddle_velocity={row['straddle_velocity']}")
    print(f"otm_oi_velocity={row['otm_oi_velocity']}")
    print(f"cautions={row['cautions']}")

    result = supabase_upsert("structural_alerts", [row], on_conflict="symbol,ts,run_type")
    print(f"Upserted {len(result)} row(s) to structural_alerts")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
