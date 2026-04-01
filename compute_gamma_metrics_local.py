from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


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

    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0

    base = gamma * oi * (spot ** 2)
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


def compute_flip_level(strike_map: dict[float, float]) -> float | None:
    if not strike_map:
        return None

    strikes = sorted(strike_map.keys())
    cumulative_points: list[tuple[float, float]] = []

    running = 0.0
    for strike in strikes:
        running += strike_map[strike]
        cumulative_points.append((strike, running))

    if len(cumulative_points) < 2:
        return None

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
            SUPABASE.table("gamma_metrics")
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
    flip_level = compute_flip_level(strike_map)

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

    # V18B: velocity and range fields
    prior_row = fetch_prior_gamma_metrics(symbol, ts)
    straddle_velocity = compute_straddle_velocity(straddle_atm, prior_row)
    otm_oi_velocity = compute_otm_oi_velocity(option_rows, spot, prior_row)
    spot_vs_range = fetch_spot_vs_range(symbol, ts)

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
    )


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

    response = SUPABASE.table("gamma_metrics").upsert(payload, on_conflict="symbol,ts").execute()
    rows = _rows(response)
    return rows[0] if rows else payload


def parse_args(argv: list[str]) -> tuple[str, Optional[str], str]:
    """
    Supports:
        compute_gamma_metrics_local.py <run_id>
        compute_gamma_metrics_local.py <run_id> <symbol>
        compute_gamma_metrics_local.py <symbol> <run_id>
        compute_gamma_metrics_local.py <run_id> <symbol> PARTIAL
        compute_gamma_metrics_local.py <run_id> PARTIAL
    """
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


def main() -> None:
    run_id, expected_symbol, run_type = parse_args(sys.argv)

    result = compute_gamma_metrics(run_id, expected_symbol=expected_symbol, run_type=run_type)
    upserted = upsert_gamma_metrics(result)

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
    print("=" * 72)


if __name__ == "__main__":
    main()
