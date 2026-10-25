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
# S101_MERDIAN_COMPUTE: pure compute lives in merdian_compute/gamma.py (moved byte-identical, S101);
# re-imported under the same names so every caller is unchanged.
from merdian_compute.gamma import (  # noqa: E402,F401
    to_float,
    as_iso_ts,
    signed_gamma_exposure,
    GammaMetricsResult,
    filter_usable_option_rows,
    infer_symbol,
    infer_spot,
    infer_expiry_date,
    infer_ts,
    infer_strike_step,
    compute_net_gex,
    build_strike_exposure_map,
    compute_gamma_concentration,
    _FLIP_DOMINANCE_EPS_FRAC,
    _flip_short_gamma_perstrike,
    compute_flip_level,
    find_atm_strike,
    compute_straddle_atm,
    compute_straddle_slope,
    compute_expansion_probability,
    determine_regime,
    determine_gamma_zone,
    compute_straddle_velocity,
    compute_otm_oi_velocity,
    compute_otm_oi_snapshot,
    compute_max_gamma_strike,
    compute_pin_risk_score,
    _dte_from_ts,
    build_gss_rows,
    prepare_gamma_inputs,  # S101_C2_GAMMA_CORE
    compute_gamma_core,
)


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


def is_uuid_like(value: str) -> bool:
    return bool(UUID_RE.match(value.strip()))


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

    inputs = prepare_gamma_inputs(option_rows_raw, run_id, expected_symbol=expected_symbol)
    symbol, ts = inputs["symbol"], inputs["ts"]

    # S101_C2_GAMMA_CORE: the history reads stay here, in their original order; the computation is
    # merdian_compute.gamma.compute_gamma_core (pure), which retail calls with its own history.
    prior_row = fetch_prior_gamma_metrics(symbol, ts)
    spot_vs_range = fetch_spot_vs_range(symbol, ts)
    vix = fetch_india_vix()
    recent_max_strikes = fetch_recent_max_gamma_strikes(symbol, ts, n=5)

    return compute_gamma_core(
        **inputs,
        run_type=run_type,
        prior_row=prior_row,
        spot_vs_range=spot_vs_range,
        vix=vix,
        recent_max_strikes=recent_max_strikes,
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
        run_id=run_id, product_relation="gamma_metrics",  # S90_R07_LEDGER
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
