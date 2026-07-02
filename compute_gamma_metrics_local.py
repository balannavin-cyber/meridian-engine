from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# S41 P0.a -- Dhan REST for India VIX live fetch (security_id=21, IDX_I segment).
# Mirrors capture_market_spot_snapshot.py pattern for index quotes. Aliased
# to avoid colliding with `requests` elsewhere in the codebase namespace.
import requests as _requests_for_vix

# ENH-72 write-contract layer. See docs/MERDIAN_Master_V19.docx governance
# rule `script_execution_log_contract`. Pattern mirrored from
# ingest_option_chain_local.py and capture_spot_1m.py.
from core.execution_log import ExecutionLog


# ============================================================
# MERDIAN - compute_gamma_metrics_local.py
#
# Purpose:
#   1. Read one option-chain batch from option_chain_snapshots via run_id
#   2. Filter out unusable rows (gamma == 0 or oi <= 0)
#   3. Build signed strike exposure map
#   4. Compute a genuine flip level only if a real zero-crossing exists
#   5. If no zero-crossing exists, write flip_level = NULL
#   6. E-02: add gamma_zone using canonical flip_distance_pct
#
# V18B additions (Track 2 SMDM infrastructure):
#   7. straddle_velocity — rate of change of straddle_atm vs prior run
#   8. otm_oi_velocity   — rate of change of OTM OI vs prior run
#   9. spot_vs_range     — spot position within session high-low range
#  10. run_type          — FULL / PARTIAL (passed as optional CLI arg)
# ============================================================


UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


def _load_env() -> Client:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip().strip('"').strip("'")

    if not supabase_url:
        raise RuntimeError("SUPABASE_URL not found in environment or .env")

    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY not found in environment or .env")

    if not supabase_url.startswith(("http://", "https://")):
        raise RuntimeError(
            f"SUPABASE_URL is invalid: {supabase_url!r}. It must start with https://"
        )

    return create_client(supabase_url, service_role_key)


SUPABASE: Client = _load_env()

# S41 P0.a -- Dhan endpoint constants for India VIX fetch. Credentials are
# read lazily from env at call time (NOT module init) so backfill / shadow
# pipelines that never fetch VIX do not require these to be set.
_DHAN_LTP_URL = "https://api.dhan.co/v2/marketfeed/ltp"
_INDIA_VIX_SEGMENT = "IDX_I"
_INDIA_VIX_SECURITY_ID = 21


def _rows(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    data = getattr(result, "data", None)
    if data is None:
        return []
    return data if isinstance(data, list) else []


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
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


def is_uuid_like(value: str) -> bool:
    return bool(UUID_RE.match(value.strip()))


def signed_gamma_exposure(row: dict[str, Any], spot: float) -> float:
    gamma = to_float(row.get("gamma"))
    oi = to_float(row.get("oi"))
    option_type = str(row.get("option_type", "")).upper()
    strike = to_float(row.get("strike"))

    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0

    # TD-NEW-2 Part A: reject deep-ITM rows with spurious gamma.
    # Options >5% from spot should have near-zero gamma in reality.
    # Threshold 5e-5 is ~5x typical ATM gamma; well outside legitimate
    # deep-ITM values. Dhan started returning gamma=7e-5 at strike 21,250
    # CE with spot 24,200 on 2026-05-08, polluting the flip-level walk.
    if strike > 0 and abs(strike - spot) / spot > 0.05:
        if abs(gamma) > 5e-5:
            return 0.0

    base = gamma * oi * (spot ** 2) / 1e7  # TD-NEW-3: store in Crore
    return -base if option_type == "PE" else base


@dataclass
class GammaMetricsResult:
    run_id: str
    symbol: str
    ts: str
    expiry_date: str | None
    spot: float
    net_gex: float
    gamma_concentration: float | None
    flip_level: float | None
    flip_distance: float | None
    flip_distance_pct: float | None
    gamma_zone: str | None
    straddle_atm: float | None
    straddle_slope: float | None
    regime: str
    expansion_probability: float | None
    # V18B additions
    straddle_velocity: float | None
    otm_oi_velocity: float | None
    spot_vs_range: float | None
    run_type: str
    # S41 P0.a -- India VIX live + max_gamma_strike materialized + Pin Risk Score.
    vix: float | None = None
    max_gamma_strike: float | None = None
    pin_risk_score: float | None = None
    # ENH-80 (S37) v2 — per-strike GEX row list, built in compute_gamma_metrics.
    gss_rows: list[dict[str, Any]] | None = None


def fetch_option_chain_rows(run_id: str, expected_symbol: str | None = None) -> list[dict[str, Any]]:
    page_size = 1000
    offset = 0
    out: list[dict[str, Any]] = []

    while True:
        query = SUPABASE.table("option_chain_snapshots").select("*").eq("run_id", run_id)

        if expected_symbol:
            query = query.eq("symbol", expected_symbol.upper())

        result = query.range(offset, offset + page_size - 1).execute()
        batch = _rows(result)

        if not batch:
            break

        out.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    return out


def fetch_symbols_for_run_id(run_id: str) -> dict[str, int]:
    result = (
        SUPABASE.table("option_chain_snapshots")
        .select("symbol")
        .eq("run_id", run_id)
        .limit(5000)
        .execute()
    )
    rows = _rows(result)

    counts: dict[str, int] = {}
    for row in rows:
        sym = str(row.get("symbol", "")).upper()
        counts[sym] = counts.get(sym, 0) + 1
    return counts


def filter_usable_option_rows(option_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable: list[dict[str, Any]] = []
    for row in option_rows:
        gamma = to_float(row.get("gamma"))
        oi = to_float(row.get("oi"))
        if gamma != 0.0 and oi > 0.0:
            usable.append(row)
    return usable


def infer_symbol(option_rows: list[dict[str, Any]], expected_symbol: str | None = None) -> str:
    symbols = sorted({str(r.get("symbol", "")).upper() for r in option_rows if r.get("symbol")})

    if expected_symbol:
        expected_symbol = expected_symbol.upper()
        if symbols and symbols != [expected_symbol]:
            raise RuntimeError(
                f"Option rows contain symbol(s) {symbols}, expected only {expected_symbol}"
            )
        return expected_symbol

    if not symbols:
        raise RuntimeError("Could not infer symbol from option rows")
    if len(symbols) > 1:
        raise RuntimeError(f"Multiple symbols found in option rows for one run_id: {symbols}")
    return symbols[0]


def infer_spot(option_rows: list[dict[str, Any]]) -> float:
    spots = [to_float(r.get("spot")) for r in option_rows if to_float(r.get("spot")) > 0]
    if not spots:
        raise RuntimeError("No valid spot values found in option rows")
    return spots[0]


def infer_expiry_date(option_rows: list[dict[str, Any]]) -> str | None:
    expiries = [str(r.get("expiry_date")) for r in option_rows if r.get("expiry_date")]
    return expiries[0] if expiries else None


def infer_ts(option_rows: list[dict[str, Any]]) -> str:
    ts_values = [r.get("ts") or r.get("created_at") for r in option_rows if r.get("ts") or r.get("created_at")]
    if not ts_values:
        return datetime.now(timezone.utc).isoformat()
    return as_iso_ts(max(ts_values))


def infer_strike_step(option_rows: list[dict[str, Any]]) -> float | None:
    strikes = sorted({to_float(r.get("strike")) for r in option_rows if to_float(r.get("strike")) > 0})
    if len(strikes) < 2:
        return None

    diffs: list[float] = []
    for i in range(1, len(strikes)):
        diff = strikes[i] - strikes[i - 1]
        if diff > 0:
            diffs.append(diff)

    return min(diffs) if diffs else None


def compute_net_gex(option_rows: list[dict[str, Any]], spot: float) -> float:
    return sum(signed_gamma_exposure(r, spot) for r in option_rows)


def build_strike_exposure_map(option_rows: list[dict[str, Any]], spot: float) -> dict[float, float]:
    strike_map: dict[float, float] = {}
    for row in option_rows:
        strike = to_float(row.get("strike"))
        if strike <= 0:
            continue
        strike_map[strike] = strike_map.get(strike, 0.0) + signed_gamma_exposure(row, spot)
    return dict(sorted(strike_map.items(), key=lambda x: x[0]))


def compute_gamma_concentration(strike_map: dict[float, float]) -> float | None:
    if not strike_map:
        return None

    total_abs = sum(abs(v) for v in strike_map.values())
    if total_abs <= 0:
        return None

    max_abs = max(abs(v) for v in strike_map.values())
    return max_abs / total_abs if max_abs > 0 else None


# TD-S62-NEW (S63) dominance floor for the SHORT-gamma per-strike walk:
# ignore strikes whose |GEX| is a negligible fraction of the peak, so a single
# tiny opposite-sign strike cannot create a false sign boundary. 0.01 = 1%.
_FLIP_DOMINANCE_EPS_FRAC = 0.01


def _flip_short_gamma_perstrike(strikes: list[float], strike_map: dict[float, float], spot: float) -> float | None:
    """TD-S62-NEW: per-strike signed-GEX sign boundary nearest spot.

    Used only under NEGATIVE gamma, where the cumulative-from-min_strike sum
    has no near-spot zero-crossing (net is negative) and the legacy walk falls
    through to a spurious deep-tail level (SENSEX 2026-07-01: ~71,500 vs spot
    ~76,900). The per-strike sign boundary is the operative pit->wall level
    near spot (StockMojo Gamma Flip 76,847 / Net-GEX-Cross 76,812).
    """
    values = [strike_map[s] for s in strikes]
    max_abs = max(abs(v) for v in values)
    if max_abs <= 0.0:
        return None
    eps = _FLIP_DOMINANCE_EPS_FRAC * max_abs
    sig = [(s, v) for s, v in zip(strikes, values) if abs(v) >= eps]
    if len(sig) < 2:
        return None
    crossings: list[float] = []
    for i in range(1, len(sig)):
        s_prev, v_prev = sig[i - 1]
        s_curr, v_curr = sig[i]
        if v_prev == 0.0:
            crossings.append(s_prev)
        elif v_curr == 0.0:
            crossings.append(s_curr)
        elif (v_prev < 0.0 < v_curr) or (v_prev > 0.0 > v_curr):
            denom = v_curr - v_prev
            if denom != 0.0:
                frac = -v_prev / denom
                crossings.append(s_prev + frac * (s_curr - s_prev))
    if not crossings:
        return None
    return min(crossings, key=lambda x: abs(x - spot))


def compute_flip_level(strike_map: dict[float, float], spot: float | None = None) -> float | None:
    """Find the operational gamma flip strike.

    Regime-conditional (TD-S62-NEW, S63):
      * net_gex >= 0 (LONG gamma): the cumulative-from-min_strike walk-from-ATM
        introduced by TD-NEW-2 Part B -- UNCHANGED. This path already resolves
        near spot on clean data (SENSEX 2026-07-01 healthy: 76,975 / 77,453).
      * net_gex <  0 (SHORT gamma): the per-strike sign boundary nearest spot
        (_flip_short_gamma_perstrike). The cumulative walk has no near-spot
        crossing under NEGATIVE gamma and returns a spurious deep-tail level;
        the per-strike boundary is the operative near-spot flip.

    net_gex == sum(strike_map.values()); no signature change. LONG-gamma cycles
    run the identical code they ran before this patch -- zero regression by
    construction.

    spot=None keeps the legacy bottom-up cumulative walk for backward
    compatibility with callers that don't pass spot (production passes spot).
    """
    if not strike_map:
        return None

    strikes = sorted(strike_map.keys())
    if len(strikes) < 2:
        return None

    # Legacy fallback: caller didn't supply spot. Preserve original behavior.
    if spot is None or spot <= 0:
        running = 0.0
        cumulative_points: list[tuple[float, float]] = []
        for strike in strikes:
            running += strike_map[strike]
            cumulative_points.append((strike, running))
        for i in range(1, len(cumulative_points)):
            strike_prev, cum_prev = cumulative_points[i - 1]
            strike_curr, cum_curr = cumulative_points[i]
            if cum_prev == 0.0:
                return strike_prev
            if cum_curr == 0.0:
                return strike_curr
            if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
                denom = cum_curr - cum_prev
                if denom == 0:
                    return None
                frac = -cum_prev / denom
                return strike_prev + frac * (strike_curr - strike_prev)
        return None

    net_gex = sum(strike_map.values())

    # SHORT gamma: per-strike sign boundary (TD-S62-NEW).
    if net_gex < 0.0:
        return _flip_short_gamma_perstrike(strikes, strike_map, spot)

    # LONG gamma: unchanged cumulative walk-from-ATM (TD-NEW-2 Part B).
    cumulative_points = []
    running = 0.0
    for strike in strikes:
        running += strike_map[strike]
        cumulative_points.append((strike, running))

    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    candidates: list[float] = []

    for i in range(atm_idx, 0, -1):
        strike_curr, cum_curr = cumulative_points[i]
        strike_prev, cum_prev = cumulative_points[i - 1]
        if cum_prev == 0.0:
            candidates.append(strike_prev)
            break
        if cum_curr == 0.0:
            candidates.append(strike_curr)
            break
        if (cum_prev < 0.0 < cum_curr) or (cum_prev > 0.0 > cum_curr):
            denom = cum_curr - cum_prev
            if denom != 0:
                frac = -cum_prev / denom
                candidates.append(strike_prev + frac * (strike_curr - strike_prev))
            break

    for i in range(atm_idx, len(cumulative_points) - 1):
        strike_curr, cum_curr = cumulative_points[i]
        strike_next, cum_next = cumulative_points[i + 1]
        if cum_curr == 0.0:
            candidates.append(strike_curr)
            break
        if cum_next == 0.0:
            candidates.append(strike_next)
            break
        if (cum_curr < 0.0 < cum_next) or (cum_curr > 0.0 > cum_next):
            denom = cum_next - cum_curr
            if denom != 0:
                frac = -cum_curr / denom
                candidates.append(strike_curr + frac * (strike_next - strike_curr))
            break

    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(x - spot))


def find_atm_strike(option_rows: list[dict[str, Any]], spot: float) -> float | None:
    strikes = sorted({to_float(r.get("strike")) for r in option_rows if to_float(r.get("strike")) > 0})
    if not strikes:
        return None
    return min(strikes, key=lambda s: abs(s - spot))


def compute_straddle_atm(option_rows: list[dict[str, Any]], spot: float) -> float | None:
    atm_strike = find_atm_strike(option_rows, spot)
    if atm_strike is None:
        return None

    ce_ltp = None
    pe_ltp = None

    for row in option_rows:
        strike = to_float(row.get("strike"))
        opt_type = str(row.get("option_type", "")).upper()
        if strike != atm_strike:
            continue
        if opt_type == "CE":
            ce_ltp = to_float(row.get("ltp"), default=0.0)
        elif opt_type == "PE":
            pe_ltp = to_float(row.get("ltp"), default=0.0)

    if ce_ltp is None or pe_ltp is None:
        return None

    return ce_ltp + pe_ltp


def compute_straddle_slope(option_rows: list[dict[str, Any]], spot: float) -> float | None:
    atm_strike = find_atm_strike(option_rows, spot)
    strike_step = infer_strike_step(option_rows)

    if atm_strike is None or strike_step is None or strike_step <= 0:
        return None

    lower = atm_strike - strike_step
    upper = atm_strike + strike_step

    def straddle_for_strike(target_strike: float) -> float | None:
        ce_ltp = None
        pe_ltp = None

        for row in option_rows:
            strike = to_float(row.get("strike"))
            opt_type = str(row.get("option_type", "")).upper()
            if strike != target_strike:
                continue
            if opt_type == "CE":
                ce_ltp = to_float(row.get("ltp"), default=0.0)
            elif opt_type == "PE":
                pe_ltp = to_float(row.get("ltp"), default=0.0)

        if ce_ltp is None or pe_ltp is None:
            return None
        return ce_ltp + pe_ltp

    lower_straddle = straddle_for_strike(lower)
    atm_straddle = straddle_for_strike(atm_strike)
    upper_straddle = straddle_for_strike(upper)

    if lower_straddle is None or atm_straddle is None or upper_straddle is None:
        return None

    return ((upper_straddle - atm_straddle) + (atm_straddle - lower_straddle)) / 2.0


def compute_expansion_probability(
    gamma_concentration: float | None,
    flip_distance_pct: float | None,
    net_gex: float,
) -> float | None:
    if gamma_concentration is None:
        return None

    score = 45.0 if net_gex < 0 else 20.0

    if gamma_concentration >= 0.25:
        score += 20.0
    elif gamma_concentration >= 0.15:
        score += 12.0
    else:
        score += 5.0

    if flip_distance_pct is not None:
        if flip_distance_pct < 0.5:
            score += 20.0
        elif flip_distance_pct < 1.5:
            score += 10.0
        else:
            score += 2.0

    return max(0.0, min(100.0, score))


def determine_regime(net_gex: float, flip_level: float | None) -> str:
    if flip_level is None:
        return "NO_FLIP"
    return "LONG_GAMMA" if net_gex >= 0 else "SHORT_GAMMA"


def determine_gamma_zone(flip_distance_pct: float | None) -> str | None:
    if flip_distance_pct is None:
        return None
    if flip_distance_pct < 0.5:
        return "HIGH_GAMMA"
    if flip_distance_pct < 1.5:
        return "MID_GAMMA"
    return "LOW_GAMMA"


# ---------------------------------------------------------------------------
# V18B: Velocity and range helpers
# ---------------------------------------------------------------------------

def fetch_prior_gamma_metrics(symbol: str, current_ts: str) -> dict[str, Any] | None:
    """
    Fetch the most recent gamma_metrics row for symbol before current_ts.
    Returns None if no prior row exists (first run of session).
    Used for straddle_velocity and otm_oi_velocity computation.
    """
    try:
        result = (
            SUPABASE.table(TARGET_TABLE)
            .select("straddle_atm,ts")
            .eq("symbol", symbol)
            .lt("ts", current_ts)
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = _rows(result)
        return rows[0] if rows else None
    except Exception:
        return None


def compute_straddle_velocity(
    current_straddle: float | None,
    prior_row: dict[str, Any] | None,
) -> float | None:
    """
    Rate of change of ATM straddle vs prior run.
    Negative = IV compressing. NULL on first run of session.
    Expressed as absolute point change (not percentage) to match spec.
    """
    if current_straddle is None or prior_row is None:
        return None
    prior_straddle = prior_row.get("straddle_atm")
    if prior_straddle is None:
        return None
    try:
        return round(float(current_straddle) - float(prior_straddle), 4)
    except (TypeError, ValueError):
        return None


def compute_otm_oi_velocity(
    option_rows: list[dict[str, Any]],
    spot: float,
    prior_row: dict[str, Any] | None,
    otm_steps: int = 2,
) -> float | None:
    """
    Rate of change of OTM OI vs prior run.
    Computes total OI at strikes >= otm_steps away from ATM on the
    directionally relevant side, compares to prior run's stored value.
    Returns pct change (0.10 = 10% increase). NULL on first run.

    Per SMDM spec: OTM_OI_VELOCITY_THRESHOLD = 0.10 (10% increase triggers alert).
    """
    if prior_row is None:
        return None

    strike_step = infer_strike_step(option_rows)
    atm_strike = find_atm_strike(option_rows, spot)

    if strike_step is None or atm_strike is None or strike_step <= 0:
        return None

    otm_threshold = atm_strike + (otm_steps * strike_step)

    # Sum OI for deep OTM CE strikes (squeeze accumulation is on CE side on expiry day)
    current_otm_oi = sum(
        to_float(r.get("oi"))
        for r in option_rows
        if to_float(r.get("strike")) >= otm_threshold
        and str(r.get("option_type", "")).upper() == "CE"
    )

    # Prior OTM OI stored in raw JSONB if available
    prior_raw = prior_row.get("raw") or {}
    prior_otm_oi = None
    if isinstance(prior_raw, dict):
        prior_otm_oi = prior_raw.get("otm_oi_snapshot")

    if prior_otm_oi is None or float(prior_otm_oi) <= 0:
        # Can't compute velocity without prior — store current for next run
        return None

    try:
        velocity = (current_otm_oi - float(prior_otm_oi)) / float(prior_otm_oi)
        return round(velocity, 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def fetch_spot_vs_range(symbol: str, current_ts: str) -> float | None:
    """
    Spot position within today's session high-low range from intraday_ohlc.
    0.0 = at session low, 1.0 = at session high.
    NULL if intraday_ohlc has no data for this symbol yet.
    """
    try:
        result = (
            SUPABASE.table("intraday_ohlc")
            .select("close,session_high,session_low")
            .eq("symbol", f"{symbol}_SPOT")
            .lte("ts", current_ts)
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = _rows(result)
        if not rows:
            return None

        row = rows[0]
        close = to_float(row.get("close"), default=0.0)
        session_high = to_float(row.get("session_high"), default=0.0)
        session_low = to_float(row.get("session_low"), default=0.0)

        if session_high <= session_low or session_high == 0.0:
            return None

        ratio = (close - session_low) / (session_high - session_low)
        return round(max(0.0, min(1.0, ratio)), 4)

    except Exception:
        return None


def compute_otm_oi_snapshot(
    option_rows: list[dict[str, Any]],
    spot: float,
    otm_steps: int = 2,
) -> float | None:
    """
    Current OTM OI snapshot — stored in raw{} for next run's velocity computation.
    """
    strike_step = infer_strike_step(option_rows)
    atm_strike = find_atm_strike(option_rows, spot)

    if strike_step is None or atm_strike is None or strike_step <= 0:
        return None

    otm_threshold = atm_strike + (otm_steps * strike_step)

    return sum(
        to_float(r.get("oi"))
        for r in option_rows
        if to_float(r.get("strike")) >= otm_threshold
        and str(r.get("option_type", "")).upper() == "CE"
    )


# ---------------------------------------------------------------------------
# S41 P0.a -- India VIX live fetch (Dhan REST marketfeed/ltp)
# ---------------------------------------------------------------------------

def fetch_india_vix() -> float | None:
    """S41 P0.a -- Fetch live India VIX via Dhan marketfeed/ltp.

    Returns float VIX value (e.g. 14.32) on success, None on any failure.
    Failure modes (token expired / 429 / network / unexpected payload) all
    return None silently -- VIX is context, not gate. The gamma cycle MUST
    NOT fail because VIX fetch failed.

    Dhan scrip master row (verified S41 2026-05-30 via api-scrip-master-detailed.csv):
        EXCH_ID=NSE, SECURITY_ID=21, INSTRUMENT=INDEX, SYMBOL_NAME=INDIA VIX
    """
    dhan_client_id = os.getenv("DHAN_CLIENT_ID", "").strip()
    dhan_token = os.getenv("DHAN_API_TOKEN", "").strip()
    if not dhan_client_id or not dhan_token:
        return None
    try:
        response = _requests_for_vix.post(
            _DHAN_LTP_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": dhan_token,
                "client-id": dhan_client_id,
            },
            json={_INDIA_VIX_SEGMENT: [_INDIA_VIX_SECURITY_ID]},
            timeout=10,
        )
        if response.status_code != 200:
            return None
        body = response.json()
        if not isinstance(body, dict) or body.get("status") != "success":
            return None
        last_price = (
            body.get("data", {})
                .get(_INDIA_VIX_SEGMENT, {})
                .get(str(_INDIA_VIX_SECURITY_ID), {})
                .get("last_price")
        )
        return float(last_price) if last_price is not None else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# S41 P0.a -- max_gamma_strike + Pin Risk Score helpers
# ---------------------------------------------------------------------------

def compute_max_gamma_strike(strike_map: dict[float, float]) -> float | None:
    """S41 P0.a FIX-1 -- strike with maximum POSITIVE gex_cr (PIN candidate).

    Pin Risk Score requires the strike where dealers are LONG gamma
    (positive net gex_cr); these strikes are the operative magnets for
    spot pinning. Amplifying strikes (negative gex_cr) are the OPPOSITE
    force -- they accelerate spot away from themselves, not toward them.

    Aligns with the ENH-81 v_gex_strike_pin_zone SQL view convention which
    filters `WHERE gex_cr > 0` before identifying the peak. Marketview
    surfaces this same value as 'MAX gamma STRIKE' / 'STRONGEST DAMPEN'.

    Returns None when no positive-GEX strike exists in the map -- an
    extreme SHORT_GAMMA regime where dealers have no long-gamma anchor;
    pin semantics undefined. compute_pin_risk_score handles this via
    its existing renormalization path (spot_proximity_factor dropped).

    Tie-break: lower strike wins (sorted ascending key iteration).
    """
    if not strike_map:
        return None
    positive_strikes = {k: v for k, v in strike_map.items() if v > 0}
    if not positive_strikes:
        return None
    return max(positive_strikes.items(), key=lambda kv: kv[1])[0]


def fetch_recent_max_gamma_strikes(
    symbol: str, current_ts: str, n: int = 5
) -> list[float]:
    """S41 P0.a FIX-1 -- fetch PIN-candidate max-gamma strike for last `n` cycles.

    Reads `gex_strike_snapshots`, filtered to POSITIVE gex_cr only (PIN
    candidate convention -- see compute_max_gamma_strike docstring). Each
    cycle's per-strike argmax over positive-GEX rows is computed in Python
    after a bounded Supabase fetch.

    Returns empty list if no history available OR if no cycle in the
    window had any positive-GEX strikes (extreme SHORT_GAMMA regime).

    Note: the current cycle's gex_strike_snapshots row is NOT yet written
    when this runs inside compute_gamma_metrics -- that's intentional, the
    sustained-time factor compares CURRENT (in-memory) to PRIOR (persisted)
    cycles, never self.
    """
    try:
        result = (
            SUPABASE.table(GSS_TARGET_TABLE)
            .select("ts,strike,gex_cr")
            .eq("symbol", symbol)
            .lt("ts", current_ts)
            .gt("gex_cr", 0)  # S41 FIX-1: PIN candidates only (dealer-long-gamma)
            .order("ts", desc=True)
            .limit(n * 250)  # ~200 strikes/cycle ceiling; trimmed in Python
            .execute()
        )
        rows = _rows(result)
        if not rows:
            return []
        # Group by ts, pick argmax(positive gex_cr) per group, return last n in time order.
        by_ts: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            by_ts.setdefault(str(r.get("ts")), []).append(r)
        sorted_ts = sorted(by_ts.keys(), reverse=True)[:n]
        out: list[float] = []
        for ts_key in sorted_ts:
            strikes_in_cycle = by_ts[ts_key]
            # All rows here have gex_cr > 0; max returns the pin candidate.
            top = max(strikes_in_cycle, key=lambda r: to_float(r.get("gex_cr")))
            s = to_float(top.get("strike"))
            if s > 0:
                out.append(s)
        return out
    except Exception:
        return []


def compute_pin_risk_score(
    gamma_concentration: float | None,
    expansion_probability: float | None,
    spot: float,
    max_gamma_strike: float | None,
    strike_step: float | None,
    recent_max_strikes: list[float],
) -> float | None:
    """S41 P0.a -- additive-weighted Pin Risk Score, 0-100.

    Weights (operator-confirmed S41):
        gamma_concentration       weight 0.30 (0-1 input)
        spot_proximity_factor     weight 0.30 (0-1 derived)
        sustained_time_factor     weight 0.20 (0-1 derived; dropped + renorm if N<3)
        (1 - expansion_prob/100)  weight 0.20 (0-1 derived)

    Renormalization: if sustained_time_factor is unavailable (N<3 prior
    cycles) OR spot_proximity_factor is unavailable (missing strike data),
    the corresponding weight is dropped and remaining weights are
    re-normalized to sum to 1.0. This preserves comparability across
    cycles with varying history depth.

    None propagation: if gamma_concentration OR expansion_probability is
    None, the score is None -- these are core positioning measures with
    no reasonable default.

    Output: 0-100 rounded to 2 decimals, clamped at boundaries.
    """
    if gamma_concentration is None or expansion_probability is None:
        return None

    # spot_proximity_factor: 1 at max-gamma-strike, decays linearly to 0 at
    # 3 strike-steps away. Strike-step normalization handles NIFTY 50pt vs
    # SENSEX 100pt without hardcoding.
    spot_proximity_factor: float | None = None
    if (
        max_gamma_strike is not None
        and strike_step is not None
        and strike_step > 0
        and spot > 0
    ):
        proximity_distance_strikes = abs(spot - max_gamma_strike) / strike_step
        spot_proximity_factor = max(0.0, 1.0 - proximity_distance_strikes / 3.0)

    # sustained_time_factor: fraction of last N prior cycles where the
    # max-gamma strike was within +/- 1 strike-step of CURRENT max-gamma
    # strike. Requires N>=3 prior cycles for the factor to be meaningful
    # (15-min window minimum given 5-min cadence).
    sustained_time_factor: float | None = None
    if (
        max_gamma_strike is not None
        and strike_step is not None
        and len(recent_max_strikes) >= 3
    ):
        within_one_strike = sum(
            1 for s in recent_max_strikes if abs(s - max_gamma_strike) <= strike_step
        )
        sustained_time_factor = within_one_strike / len(recent_max_strikes)

    # expansion_probability is stored 0-100 by compute_expansion_probability;
    # complement gives 0-1 contraction-likelihood (high = pin-supportive).
    expansion_complement = 1.0 - (float(expansion_probability) / 100.0)

    # Assemble components and renormalize over available weights.
    components: list[tuple[float, float]] = []  # (weight, value)
    components.append((0.30, float(gamma_concentration)))
    if spot_proximity_factor is not None:
        components.append((0.30, spot_proximity_factor))
    if sustained_time_factor is not None:
        components.append((0.20, sustained_time_factor))
    components.append((0.20, expansion_complement))

    weight_total = sum(w for w, _ in components)
    if weight_total <= 0:
        return None
    score_01 = sum(w * v for w, v in components) / weight_total
    score_100 = 100.0 * score_01
    return round(max(0.0, min(100.0, score_100)), 2)


# ---------------------------------------------------------------------------
# Core compute function — unchanged interface, extended output
# ---------------------------------------------------------------------------

def compute_gamma_metrics(
    run_id: str,
    expected_symbol: str | None = None,
    run_type: str = "FULL",
) -> GammaMetricsResult:
    option_rows_raw = fetch_option_chain_rows(run_id, expected_symbol=expected_symbol)

    if not option_rows_raw:
        available = fetch_symbols_for_run_id(run_id)
        if expected_symbol:
            raise RuntimeError(
                f"No option_chain_snapshots rows found for run_id={run_id}, symbol={expected_symbol}. "
                f"Available symbols for this run_id: {available}"
            )
        raise RuntimeError(f"No option_chain_snapshots rows found for run_id={run_id}")

    symbol = infer_symbol(option_rows_raw, expected_symbol=expected_symbol)
    spot = infer_spot(option_rows_raw)
    expiry_date = infer_expiry_date(option_rows_raw)
    ts = infer_ts(option_rows_raw)

    option_rows = filter_usable_option_rows(option_rows_raw)
    if not option_rows:
        raise RuntimeError(
            f"All option rows were filtered out as unusable for run_id={run_id}, symbol={symbol}"
        )

    strike_map = build_strike_exposure_map(option_rows, spot)
    net_gex = compute_net_gex(option_rows, spot)
    gamma_concentration = compute_gamma_concentration(strike_map)
    flip_level = compute_flip_level(strike_map, spot)

    if flip_level is None:
        flip_distance = None
        flip_distance_pct = None
    else:
        flip_distance = spot - flip_level
        flip_distance_pct = abs(flip_distance) / spot * 100.0 if spot > 0 else None

    gamma_zone = determine_gamma_zone(flip_distance_pct)
    straddle_atm = compute_straddle_atm(option_rows, spot)
    straddle_slope = compute_straddle_slope(option_rows, spot)
    expansion_probability = compute_expansion_probability(gamma_concentration, flip_distance_pct, net_gex)
    regime = determine_regime(net_gex, flip_level)

    # ENH-80 (S37) v2 — per-strike GEX row build (ADR-015 schema v2).
    gss_rows = build_gss_rows(option_rows_raw, spot, symbol, ts, expiry_date, run_id)

    # V18B: velocity and range fields
    prior_row = fetch_prior_gamma_metrics(symbol, ts)
    straddle_velocity = compute_straddle_velocity(straddle_atm, prior_row)
    otm_oi_velocity = compute_otm_oi_velocity(option_rows, spot, prior_row)
    spot_vs_range = fetch_spot_vs_range(symbol, ts)

    # S41 P0.a -- India VIX + max_gamma_strike + Pin Risk Score.
    # VIX is live-fetched (Dhan); failure returns None silently.
    # max_gamma_strike derived from in-memory strike_map (no Supabase round-trip).
    # Pin Risk Score requires sustained-time factor: queries last 5 cycles of
    # gex_strike_snapshots BEFORE current ts (current cycle not yet persisted).
    vix = fetch_india_vix()
    max_gamma_strike = compute_max_gamma_strike(strike_map)
    strike_step = infer_strike_step(option_rows)
    recent_max_strikes = fetch_recent_max_gamma_strikes(symbol, ts, n=5)
    pin_risk_score = compute_pin_risk_score(
        gamma_concentration=gamma_concentration,
        expansion_probability=expansion_probability,
        spot=spot,
        max_gamma_strike=max_gamma_strike,
        strike_step=strike_step,
        recent_max_strikes=recent_max_strikes,
    )

    return GammaMetricsResult(
        run_id=run_id,
        symbol=symbol,
        ts=ts,
        expiry_date=expiry_date,
        spot=spot,
        net_gex=net_gex,
        gamma_concentration=gamma_concentration,
        flip_level=flip_level,
        flip_distance=flip_distance,
        flip_distance_pct=flip_distance_pct,
        gamma_zone=gamma_zone,
        straddle_atm=straddle_atm,
        straddle_slope=straddle_slope,
        regime=regime,
        expansion_probability=expansion_probability,
        straddle_velocity=straddle_velocity,
        otm_oi_velocity=otm_oi_velocity,
        spot_vs_range=spot_vs_range,
        run_type=run_type,
        vix=vix,                                 # S41 P0.a
        max_gamma_strike=max_gamma_strike,       # S41 P0.a
        pin_risk_score=pin_risk_score,           # S41 P0.a
        gss_rows=gss_rows,  # ENH-80 (S37) v2
    )


def _dte_from_ts(result):
    """TD-NEW-4 (S28): compute DTE as (expiry - result.ts.date()) in IST.

    Replaces prior `date.today()` reference which silently broke backfill
    correctness. Live writes unaffected (result.ts is ~= now within seconds).
    Self-contained: local imports avoid module-level import changes.
    """
    if not result.expiry_date:
        return None
    from datetime import date as _date, datetime as _dt, timezone as _tz, timedelta as _td
    _IST = _tz(_td(hours=5, minutes=30))
    ts = result.ts
    if isinstance(ts, str):
        # TD-NEW-13 (S28): normalize microseconds to 6 digits for Python 3.10 compat.
        # AWS runs Python 3.10 which rejects non-3/6-digit microseconds in fromisoformat.
        # Supabase serializes with variable precision (2-7 digits).
        import re as _re
        _ts = ts.replace("Z", "+00:00")
        _m = _re.match(r"^(.+)\.(\d+)(\+\d{2}:\d{2}|\-\d{2}:\d{2})$", _ts)
        if _m:
            _base, _frac, _tz = _m.groups()
            _frac = (_frac + "000000")[:6]
            _ts = f"{_base}.{_frac}{_tz}"
        ts_dt = _dt.fromisoformat(_ts)
    else:
        ts_dt = ts
    if ts_dt.tzinfo is None:
        ts_dt = ts_dt.replace(tzinfo=_IST)
    as_of = ts_dt.astimezone(_IST).date()
    return (_date.fromisoformat(result.expiry_date) - as_of).days


def upsert_gamma_metrics(result: GammaMetricsResult) -> dict[str, Any]:
    # Compute OTM OI snapshot for next run's velocity calculation
    # We re-fetch here only if needed — stored in raw for continuity
    otm_oi_snapshot = None
    try:
        option_rows_raw = fetch_option_chain_rows(result.run_id, expected_symbol=result.symbol)
        option_rows = filter_usable_option_rows(option_rows_raw)
        if option_rows:
            otm_oi_snapshot = compute_otm_oi_snapshot(option_rows, result.spot)
    except Exception:
        pass

    payload = {
        "run_id": result.run_id,
        "symbol": result.symbol,
        "ts": result.ts,
        "expiry_date": result.expiry_date,
        "dte": _dte_from_ts(result),
        "spot": result.spot,
        "net_gex": result.net_gex,
        "gamma_concentration": result.gamma_concentration,
        "flip_level": result.flip_level,
        "flip_distance": result.flip_distance,
        "flip_distance_pct": result.flip_distance_pct,
        "gamma_zone": result.gamma_zone,
        "straddle_atm": result.straddle_atm,
        "straddle_slope": result.straddle_slope,
        "regime": result.regime,
        "expansion_probability": result.expansion_probability,
        # V18B additions
        "straddle_velocity": result.straddle_velocity,
        "otm_oi_velocity": result.otm_oi_velocity,
        "spot_vs_range": result.spot_vs_range,
        "run_type": result.run_type,
        # S41 P0.a -- VIX + max_gamma_strike + Pin Risk Score
        "vix": result.vix,
        "max_gamma_strike": result.max_gamma_strike,
        "pin_risk_score": result.pin_risk_score,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw": {
            "builder": "compute_gamma_metrics_local.py",
            "builder_version": "V18B_SMDM_VELOCITY_V1",
            "gamma_zone_policy": {
                "HIGH_GAMMA_lt_pct": 0.5,
                "MID_GAMMA_lt_pct": 1.5,
                "LOW_GAMMA_gte_pct": 1.5,
                "canonical_distance_field": "flip_distance_pct",
            },
            "otm_oi_snapshot": otm_oi_snapshot,
        },
    }

    response = SUPABASE.table(TARGET_TABLE).upsert(payload, on_conflict="symbol,ts").execute()
    rows = _rows(response)
    return rows[0] if rows else payload


# =====================================================================
# ENH-80 (S37) v2 — per-strike GEX (gex_strike_snapshots) helpers
# ADR-015 schema v2: gamma_call + gamma_put split, no derived booleans.
# Peak / flip / pin semantics move to query-time views (ADR-015 §F2).
# =====================================================================

def build_gss_rows(
    option_rows_raw: list[dict[str, Any]],
    spot: float,
    symbol: str,
    ts: str,
    expiry_date: str | None,
    run_id: str,
) -> list[dict[str, Any]]:
    """ENH-80 (S37) v2 — build per-strike rows for gex_strike_snapshots.

    Schema v2 per ADR-015: stores gamma_call + gamma_put split (IV skew
    preserved at strike resolution) and drops is_local_max / is_flip_zone /
    is_pin_candidate_bool (derivations now live in query-time views).

    Iterates over option_rows_raw (pre-filter) so oi_call / oi_put reflect
    full-chain OI even when gamma=0 rows are present. signed_gamma_exposure
    handles its own filtering (deep-ITM rejection per TD-NEW-2 Part A;
    gamma=0 or oi<=0 returns 0). Sum of gex_cr across returned rows MUST
    equal compute_net_gex(option_rows, spot) within rounding — falsification
    rule from ADR-014 §2.5 (retained in ADR-015). Zero-noise strikes (no OI
    either side AND no GEX contribution) are dropped.
    """
    if not option_rows_raw or spot <= 0:
        return []

    # dte reuses _dte_from_ts via SimpleNamespace stand-in; single source
    # of truth for IST DTE math.
    from types import SimpleNamespace
    dte = _dte_from_ts(SimpleNamespace(ts=ts, expiry_date=expiry_date))

    per_strike: dict[float, dict[str, Any]] = {}
    for row in option_rows_raw:
        strike = to_float(row.get("strike"))
        if strike <= 0:
            continue
        opt_type = str(row.get("option_type", "")).upper()
        oi = int(to_float(row.get("oi"), default=0.0))
        gamma_raw = to_float(row.get("gamma"))
        gex_contrib = signed_gamma_exposure(row, spot)

        bucket = per_strike.setdefault(strike, {
            "strike": strike,
            "gex_cr": 0.0,
            "oi_call": 0,
            "oi_put": 0,
            "gamma_call": None,
            "gamma_put": None,
        })
        bucket["gex_cr"] += gex_contrib
        if opt_type == "CE":
            bucket["oi_call"] += oi
            if bucket["gamma_call"] is None and gamma_raw != 0.0:
                bucket["gamma_call"] = gamma_raw
        elif opt_type == "PE":
            bucket["oi_put"] += oi
            if bucket["gamma_put"] is None and gamma_raw != 0.0:
                bucket["gamma_put"] = gamma_raw

    rows: list[dict[str, Any]] = []
    for strike in sorted(per_strike.keys()):
        b = per_strike[strike]
        if b["oi_call"] == 0 and b["oi_put"] == 0 and b["gex_cr"] == 0.0:
            continue
        rows.append({
            "run_id": run_id,
            "symbol": symbol,
            "ts": ts,
            "expiry_date": expiry_date,
            "dte": dte,
            "strike": float(strike),
            "spot": float(spot),
            "gamma_call": b["gamma_call"],
            "gamma_put": b["gamma_put"],
            "oi_call": b["oi_call"],
            "oi_put": b["oi_put"],
            "gex_cr": float(b["gex_cr"]),
        })

    return rows


def upsert_gex_strike_snapshots(result: GammaMetricsResult) -> int:
    """ENH-80 (S37) v2 — bulk upsert per-strike rows to gex_strike_snapshots.

    Idempotent via UNIQUE (run_id, strike, expiry_date) — retries within
    one run_id UPSERT in place rather than duplicate. Returns the count of
    rows sent for log.record_write.
    """
    rows = result.gss_rows or []
    if not rows:
        return 0
    SUPABASE.table(GSS_TARGET_TABLE).upsert(
        rows, on_conflict="run_id,strike,expiry_date"
    ).execute()
    return len(rows)


# TD-NEW-12 (S28): shadow-vs-live table separation.
# AWS shadow runner passes --shadow to redirect writes to gamma_metrics_shadow.
# Local invocations omit it and write to gamma_metrics.
# Reads (fetch_prior_gamma_metrics) ALSO redirected — shadow pipeline reads its own history.
USE_SHADOW = "--shadow" in sys.argv
if USE_SHADOW:
    sys.argv = [a for a in sys.argv if a != "--shadow"]
TARGET_TABLE = "gamma_metrics_shadow" if USE_SHADOW else "gamma_metrics"

# ENH-80 (S37) v2 — per-strike GEX shadow-aware target (ADR-015).
# Companion to TARGET_TABLE. Shadow DDL is out of scope for S37; AWS
# shadow runs will error against the shadow table until ADR-006
# execution lands it. Local production writes proceed unchanged.
GSS_TARGET_TABLE = "gex_strike_snapshots_shadow" if USE_SHADOW else "gex_strike_snapshots"


def parse_args(argv: list[str]) -> tuple[str, Optional[str], str]:
    """
    Supports:
        compute_gamma_metrics_local.py <run_id>
        compute_gamma_metrics_local.py <run_id> <symbol>
        compute_gamma_metrics_local.py <symbol> <run_id>
        compute_gamma_metrics_local.py <run_id> <symbol> PARTIAL
        compute_gamma_metrics_local.py <run_id> PARTIAL
    """
    # Defensive: strip --shadow if it made it here (module-level should handle it)
    argv = [a for a in argv if a != "--shadow"]
    
    if len(argv) not in {2, 3, 4}:
        raise RuntimeError(
            "Usage: python compute_gamma_metrics_local.py <run_id> [symbol] [FULL|PARTIAL]"
        )

    run_type = "FULL"
    args = argv[1:]

    # Extract run_type if present
    if args[-1].upper() in {"FULL", "PARTIAL"}:
        run_type = args[-1].upper()
        args = args[:-1]

    if len(args) == 1:
        run_id = args[0].strip()
        if not is_uuid_like(run_id):
            raise RuntimeError("Single-argument mode requires a UUID run_id")
        return run_id, None, run_type

    a = args[0].strip()
    b = args[1].strip()

    if is_uuid_like(a) and not is_uuid_like(b):
        return a, b.upper(), run_type
    if is_uuid_like(b) and not is_uuid_like(a):
        return b, a.upper(), run_type
    if is_uuid_like(a) and is_uuid_like(b):
        return a, None, run_type

    raise RuntimeError("Could not determine run_id from arguments")


def _classify_exception(err: Exception) -> tuple[str, int]:
    """
    Map an exception to (exit_reason, exit_code) for ExecutionLog.

    SKIPPED_NO_INPUT: the upstream ingest wrote nothing for this run_id.
                     This is NOT this script's fault -- surface it as a
                     different failure class so dashboards don't flag it
                     against compute_gamma_metrics.
    DATA_ERROR:      every other domain-level failure (empty usable rows,
                     no spot, symbol mismatch, Supabase rejects the upsert).
    """
    msg = str(err)
    if "No option_chain_snapshots rows found" in msg:
        return ("SKIPPED_NO_INPUT", 1)
    return ("DATA_ERROR", 1)


def main() -> int:
    # Parse CLI args BEFORE opening an ExecutionLog row. A usage error is
    # an operator/integration bug, not a pipeline failure, and should not
    # pollute script_execution_log with RUNNING rows that never resolve.
    try:
        run_id, expected_symbol, run_type = parse_args(sys.argv)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 2

    # ── ENH-72 write-contract declaration ────────────────────────────────────
    # Contract: this invocation writes exactly 1 row to gamma_metrics via
    # UPSERT on (symbol, ts). Floor = expected = 1.
    #
    # Symbol is set to expected_symbol if provided by the caller; otherwise
    # None until inferred from the chain rows inside compute_gamma_metrics.
    # We update log.symbol in-place after inference so the final PATCH row
    # carries the real symbol. Opening RUNNING row may have symbol=null for
    # ~500ms in the one-arg case -- acceptable; atexit crash coverage takes
    # priority over opening-row completeness.
    log = ExecutionLog(
        script_name="compute_gamma_metrics_local.py",
        expected_writes={TARGET_TABLE: 1, GSS_TARGET_TABLE: 1},  # ENH-80 (S37) v2
        symbol=expected_symbol,
        notes=f"run_id={run_id} run_type={run_type}",
    )

    try:
        result = compute_gamma_metrics(
            run_id,
            expected_symbol=expected_symbol,
            run_type=run_type,
        )
    except Exception as e:
        reason, code = _classify_exception(e)
        return log.exit_with_reason(
            reason,
            exit_code=code,
            error_message=f"compute_gamma_metrics failed: {e}",
        )

    # Backfill the symbol onto the log row now that we know it. set_symbol()
    # issues a PATCH to script_execution_log updating the symbol column on
    # the RUNNING row before the final complete()/exit_with_reason() PATCH
    # lands. Added to ExecutionLog in Session 3 for run_id-contract scripts
    # (gamma, volatility, momentum) that discover symbol after the first
    # Supabase read rather than at CLI parse time.
    log.set_symbol(result.symbol)

    try:
        upserted = upsert_gamma_metrics(result)
    except Exception as e:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"upsert_gamma_metrics failed: {e}",
        )

    # The upsert returns the row (or at minimum the payload we sent).
    # Either way, one row landed in gamma_metrics.
    log.record_write(TARGET_TABLE, 1)

    # ENH-80 (S37) v2 — per-strike GEX upsert (strict path; fail loud).
    try:
        gss_n = upsert_gex_strike_snapshots(result)
    except Exception as e:
        return log.exit_with_reason(
            "DATA_ERROR",
            exit_code=1,
            error_message=f"upsert_gex_strike_snapshots failed: {e}",
        )
    log.record_write(GSS_TARGET_TABLE, gss_n)
    print(f"gex_strike_snapshots_rows_written={gss_n}")

    print("=" * 72)
    print("MERDIAN - Local Python compute_gamma_metrics")
    print("=" * 72)
    print(f"run_id={result.run_id}")
    print(f"symbol={result.symbol}")
    print(f"run_type={result.run_type}")
    print(f"upserted_id={upserted.get('id')}")
    print(f"net_gex={result.net_gex}")
    print(f"gamma_concentration={result.gamma_concentration}")
    print(f"flip_level={result.flip_level}")
    print(f"flip_distance={result.flip_distance}")
    print(f"flip_distance_pct={result.flip_distance_pct}")
    print(f"gamma_zone={result.gamma_zone}")
    print(f"straddle_atm={result.straddle_atm}")
    print(f"straddle_slope={result.straddle_slope}")
    print(f"straddle_velocity={result.straddle_velocity}")
    print(f"otm_oi_velocity={result.otm_oi_velocity}")
    print(f"spot_vs_range={result.spot_vs_range}")
    print(f"regime={result.regime}")
    print(f"expansion_probability={result.expansion_probability}")
    # S41 P0.a
    print(f"vix={result.vix}")
    print(f"max_gamma_strike={result.max_gamma_strike}")
    print(f"pin_risk_score={result.pin_risk_score}")
    print("=" * 72)

    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
