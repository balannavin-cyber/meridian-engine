from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# MERDIAN - compute_gamma_metrics_local.py
# Full-file replacement
#
# Purpose:
#   1. Read one option-chain batch from option_chain_snapshots via run_id
#   2. FILTER OUT unusable rows (gamma == 0 or oi <= 0)
#   3. Build signed strike exposure map
#   4. Compute a genuine flip level ONLY if a real zero-crossing exists
#   5. If no zero-crossing exists, write flip_level = NULL
#
# Key permanent fix in this version:
#   - NO "min strike" fallback
#   - zero-gamma / zero-OI rows are excluded before flip computation
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


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
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


def signed_gamma_exposure(row: dict[str, Any], spot: float) -> float:
    """
    Dealer-style signed gamma exposure proxy.

    Convention used in MERDIAN docs:
      exposure ~ gamma * OI * spot^2
      CE positive
      PE negative
    """
    gamma = to_float(row.get("gamma"))
    oi = to_float(row.get("oi"))
    option_type = str(row.get("option_type", "")).upper()

    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0

    base = gamma * oi * (spot ** 2)

    if option_type == "PE":
        return -base
    return base


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
    straddle_atm: float | None
    straddle_slope: float | None
    regime: str
    expansion_probability: float | None


# -----------------------------
# Data fetch
# -----------------------------
def fetch_option_chain_rows(run_id: str, expected_symbol: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch all rows for one run_id.
    If expected_symbol is provided, filter by that symbol.
    """
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
    """
    Diagnostic helper for clearer error messages.
    """
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


# -----------------------------
# Chain cleaning / metrics
# -----------------------------
def filter_usable_option_rows(option_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Permanent integrity fix:
      keep only rows with gamma != 0 and oi > 0
    """
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

    diffs = []
    for i in range(1, len(strikes)):
        diff = strikes[i] - strikes[i - 1]
        if diff > 0:
            diffs.append(diff)

    if not diffs:
        return None

    return min(diffs)


def build_strike_exposure_map(option_rows: list[dict[str, Any]], spot: float) -> dict[float, float]:
    """
    Aggregate signed gamma exposure by strike.
    """
    strike_map: dict[float, float] = {}

    for row in option_rows:
        strike = to_float(row.get("strike"))
        if strike <= 0.0:
            continue

        exposure = signed_gamma_exposure(row, spot)
        if exposure == 0.0:
            continue

        strike_map[strike] = strike_map.get(strike, 0.0) + exposure

    return dict(sorted(strike_map.items(), key=lambda kv: kv[0]))


def compute_flip_level(strike_map: dict[float, float]) -> float | None:
    """
    Compute zero-crossing of cumulative exposure across strikes.

    Permanent fix:
      - If no real zero-crossing exists, return None
      - DO NOT fall back to min strike
    """
    if len(strike_map) < 2:
        return None

    ordered = sorted(strike_map.items(), key=lambda kv: kv[0])

    cumulative_points: list[tuple[float, float]] = []
    running = 0.0

    for strike, exposure in ordered:
        running += exposure
        cumulative_points.append((strike, running))

    prev_strike, prev_cum = cumulative_points[0]

    if prev_cum == 0.0:
        return float(prev_strike)

    for strike, cum in cumulative_points[1:]:
        if cum == 0.0:
            return float(strike)

        sign_changed = (prev_cum < 0.0 < cum) or (prev_cum > 0.0 > cum)
        if sign_changed:
            # Linear interpolation between the two cumulative points
            denom = cum - prev_cum
            if denom == 0:
                return float(strike)

            frac = (0.0 - prev_cum) / denom
            interpolated = prev_strike + frac * (strike - prev_strike)
            return float(interpolated)

        prev_strike, prev_cum = strike, cum

    # Permanent fix: no fake fallback
    return None


def compute_gamma_concentration(strike_map: dict[float, float], spot: float, strike_step: float | None) -> float | None:
    """
    Share of absolute exposure concentrated near ATM.
    """
    if not strike_map:
        return None

    total_abs = sum(abs(v) for v in strike_map.values())
    if total_abs <= 0:
        return None

    if not strike_step or strike_step <= 0:
        window = 3
        near_abs = 0.0
        ordered = sorted(strike_map.items(), key=lambda kv: abs(kv[0] - spot))
        for _, exposure in ordered[:window]:
            near_abs += abs(exposure)
        return near_abs / total_abs

    near_abs = 0.0
    for strike, exposure in strike_map.items():
        if abs(strike - spot) <= (3 * strike_step):
            near_abs += abs(exposure)

    return near_abs / total_abs


def compute_straddle_atm(option_rows: list[dict[str, Any]], spot: float) -> tuple[float | None, float | None]:
    """
    Returns:
      (straddle_atm, straddle_slope)

    straddle_slope here is an approximate local slope:
      upper_neighbor_straddle - lower_neighbor_straddle
    """
    strikes = sorted({to_float(r.get("strike")) for r in option_rows if to_float(r.get("strike")) > 0})
    if not strikes:
        return None, None

    atm_strike = min(strikes, key=lambda s: abs(s - spot))

    def ltp_for(strike: float, option_type: str) -> float | None:
        candidates = [
            r for r in option_rows
            if to_float(r.get("strike")) == strike
            and str(r.get("option_type", "")).upper() == option_type
        ]
        if not candidates:
            return None

        # Prefer positive LTP if available
        positive = [to_float(r.get("ltp")) for r in candidates if to_float(r.get("ltp")) > 0]
        if positive:
            return positive[0]

        vals = [to_float(r.get("ltp")) for r in candidates]
        return vals[0] if vals else None

    atm_ce = ltp_for(atm_strike, "CE")
    atm_pe = ltp_for(atm_strike, "PE")

    if atm_ce is None or atm_pe is None:
        return None, None

    straddle_atm = atm_ce + atm_pe

    strike_step = infer_strike_step(option_rows)
    if not strike_step:
        return straddle_atm, None

    lower_strike = atm_strike - strike_step
    upper_strike = atm_strike + strike_step

    lower_ce = ltp_for(lower_strike, "CE")
    lower_pe = ltp_for(lower_strike, "PE")
    upper_ce = ltp_for(upper_strike, "CE")
    upper_pe = ltp_for(upper_strike, "PE")

    lower_straddle = (lower_ce + lower_pe) if (lower_ce is not None and lower_pe is not None) else None
    upper_straddle = (upper_ce + upper_pe) if (upper_ce is not None and upper_pe is not None) else None

    if lower_straddle is None or upper_straddle is None:
        return straddle_atm, None

    straddle_slope = upper_straddle - lower_straddle
    return straddle_atm, straddle_slope


def compute_expansion_probability(
    gamma_concentration: float | None,
    flip_distance_pct: float | None,
    net_gex: float,
) -> float | None:
    """
    Lightweight placeholder probability proxy.
    Keeps field populated without pretending false precision.
    """
    if gamma_concentration is None:
        return None

    # Base probability rises when concentration is low and flip is close.
    base = 0.50

    if flip_distance_pct is not None:
        if flip_distance_pct < 0.5:
            base += 0.20
        elif flip_distance_pct < 1.5:
            base += 0.10
        else:
            base -= 0.05

    # Lower concentration implies easier expansion
    base += max(0.0, 0.20 - gamma_concentration) * 0.75

    # Short gamma mildly increases expansion tendency
    if net_gex < 0:
        base += 0.05

    return max(0.0, min(1.0, base))


def determine_regime(net_gex: float, flip_level: float | None) -> str:
    """
    Keep regime honest.
    If no valid flip exists, mark that explicitly.
    """
    if flip_level is None:
        return "NO_FLIP"

    if net_gex > 0:
        return "LONG_GAMMA"
    if net_gex < 0:
        return "SHORT_GAMMA"
    return "NEUTRAL_GAMMA"


# -----------------------------
# Core compute
# -----------------------------
def compute(run_id: str, expected_symbol: str | None = None) -> GammaMetricsResult:
    option_rows = fetch_option_chain_rows(run_id, expected_symbol=expected_symbol)

    if not option_rows:
        available = fetch_symbols_for_run_id(run_id)
        raise RuntimeError(
            f"No option_chain_snapshots rows found for run_id={run_id}"
            + (f" and symbol={expected_symbol}" if expected_symbol else "")
            + f". Available symbols for this run_id: {available}"
        )

    symbol = infer_symbol(option_rows, expected_symbol=expected_symbol)
    spot = infer_spot(option_rows)
    expiry_date = infer_expiry_date(option_rows)
    ts = infer_ts(option_rows)

    raw_count = len(option_rows)
    usable_rows = filter_usable_option_rows(option_rows)
    usable_count = len(usable_rows)

    if not usable_rows:
        raise RuntimeError(
            f"No usable option rows after filtering zero gamma / zero OI for run_id={run_id}, symbol={symbol}. "
            f"raw_rows={raw_count}, usable_rows={usable_count}"
        )

    strike_step = infer_strike_step(usable_rows)
    strike_map = build_strike_exposure_map(usable_rows, spot)

    if not strike_map:
        raise RuntimeError(
            f"Usable rows remained after filtering, but strike exposure map is empty for run_id={run_id}, symbol={symbol}"
        )

    net_gex = sum(strike_map.values())
    flip_level = compute_flip_level(strike_map)

    if flip_level is None:
        flip_distance = None
        flip_distance_pct = None
    else:
        flip_distance = spot - flip_level
        flip_distance_pct = abs(flip_distance) / spot * 100.0 if spot > 0 else None

    gamma_concentration = compute_gamma_concentration(strike_map, spot, strike_step)
    straddle_atm, straddle_slope = compute_straddle_atm(option_rows, spot)
    expansion_probability = compute_expansion_probability(gamma_concentration, flip_distance_pct, net_gex)
    regime = determine_regime(net_gex, flip_level)

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
        straddle_atm=straddle_atm,
        straddle_slope=straddle_slope,
        regime=regime,
        expansion_probability=expansion_probability,
    )


# -----------------------------
# Database write
# -----------------------------
def upsert_gamma_metrics(result: GammaMetricsResult) -> None:
    row = {
        "run_id": result.run_id,
        "ts": result.ts,
        "symbol": result.symbol,
        "expiry_date": result.expiry_date,
        "spot": result.spot,
        "net_gex": result.net_gex,
        "gamma_concentration": result.gamma_concentration,
        "flip_level": result.flip_level,
        "flip_distance": result.flip_distance,
        "flip_distance_pct": result.flip_distance_pct,
        "straddle_atm": result.straddle_atm,
        "straddle_slope": result.straddle_slope,
        "vix": None,
        "breadth_regime": None,
        "expansion_probability": result.expansion_probability,
        "regime": result.regime,
    }

    SUPABASE.table("gamma_metrics").upsert(row, on_conflict="run_id").execute()


# -----------------------------
# CLI
# -----------------------------
def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("Usage: python compute_gamma_metrics_local.py <run_id> [symbol]")
        sys.exit(1)

    run_id = sys.argv[1]
    expected_symbol = sys.argv[2].upper() if len(sys.argv) == 3 else None

    result = compute(run_id, expected_symbol=expected_symbol)
    upsert_gamma_metrics(result)

    print("Gamma metrics upsert complete.")
    print(f"run_id={result.run_id}")
    print(f"symbol={result.symbol}")
    print(f"ts={result.ts}")
    print(f"spot={result.spot}")
    print(f"net_gex={result.net_gex}")
    print(f"gamma_concentration={result.gamma_concentration}")
    print(f"flip_level={result.flip_level}")
    print(f"flip_distance={result.flip_distance}")
    print(f"flip_distance_pct={result.flip_distance_pct}")
    print(f"straddle_atm={result.straddle_atm}")
    print(f"straddle_slope={result.straddle_slope}")
    print(f"expansion_probability={result.expansion_probability}")
    print(f"regime={result.regime}")


if __name__ == "__main__":
    main()