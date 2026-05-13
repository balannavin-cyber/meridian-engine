#!/usr/bin/env python3
"""
compute_vol_analytics_local.py — ENH-97 vol_analytics writer.

Per ADR-002 v2 §P7 vol-pricing principle:
    realized_vol_10 — annualised σ from 10 prior 5-min spot bar log returns (50 min)
    realized_vol_30 — annualised σ from 30 prior 5-min spot bar log returns (150 min)
    implied_vol_atm — sourced from volatility_snapshots.atm_iv_avg for matching cycle
                      (fallback: direct compute from option_chain_snapshots ATM rows)
    rr_ratio        — realized_vol_30 / implied_vol_atm
    rr_regime       — HIGH (>1.2) / FAIR (0.85-1.2) / LOW (0.4-0.85) / COMPRESSED (<0.4)

Refs:
- ENH-97 (S28 P2 PROPOSED filing)
- ADR-002 v2 §P7 (vol-pricing) + §Schema (vol_analytics table DDL)
- Assumption Register §D.10.1 (RR independent edge LIVE pending Phase 0b)
- Assumption Register §D.11.1 (shadow architecture: physical separation via
                                TARGET_TABLE routing, not host-column narrative)
- Assumption Register §D.11.3 (cross-Python microsecond normalization)
- CLAUDE.md B22 (cross-Python Python 3.10/3.12 fromisoformat compatibility)
- ENH-71 (write-contract: ExecutionLog instrumentation)

Call signature:
    python compute_vol_analytics_local.py <run_id>           # → vol_analytics (Local)
    python compute_vol_analytics_local.py <run_id> --shadow  # → vol_analytics_shadow (AWS)

Pipeline position (in options runner):
    Step N: depends on option_chain_snapshots (for run_id → symbol+ts lookup)
            and on volatility_snapshots (for implied_vol_atm); should run after
            compute_volatility_metrics_local.py (Step 5).
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

# Project-local imports
from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore

from core.execution_log import ExecutionLog  # type: ignore — ENH-71 helper


# ============================================================================
# Module-level constants
# ============================================================================

SCRIPT_NAME = "compute_vol_analytics_local.py"

# Realized-vol windows (5-min bars).
WINDOW_FAST_BARS = 10   # 50 min  — fast diagnostic horizon
WINDOW_SLOW_BARS = 30   # 150 min — RR regime-stable numerator

# Annualisation factor for σ on 5-min bars:
#   trading days/year = 252; 5-min bars/trading day = 75 (09:15–15:30 IST = 6h15m)
#   σ_annual = σ_per_bar × sqrt(252 × 75)
BARS_PER_TRADING_DAY = 75
ANNUALIZATION_FACTOR = math.sqrt(252 * BARS_PER_TRADING_DAY)  # ≈ 137.48

# RR regime thresholds — per ADR-002 v2 §P7.
# Boundary inclusivity: HIGH strict >; COMPRESSED strict <; 0.85 belongs to FAIR;
# 0.4 belongs to LOW.
RR_HIGH_MIN = 1.20
RR_FAIR_MIN = 0.85
RR_LOW_MIN  = 0.40

# IV-source tolerance: volatility_snapshots.ts may not match option_chain_snapshots.ts
# to the second; accept matches within this window.
IV_LOOKUP_TOLERANCE = timedelta(seconds=120)

# Target-table routing — set in main() based on --shadow flag.
# Per Assumption Register §D.11.1: physical separation, not host-column narrative.
TARGET_TABLE: str = "vol_analytics"  # default Local; overridden by --shadow


# ============================================================================
# Cross-Python stdlib compat — per CLAUDE.md B22 + Assumption Register §D.11.3
# ============================================================================

_MICROSECOND_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


def _normalize_microseconds(ts_str: str) -> str:
    """
    Normalise the microsecond fraction in an ISO-8601 timestamp string to exactly
    6 digits before passing to datetime.fromisoformat().

    Python 3.10 stdlib `fromisoformat()` accepts only 3- or 6-digit microsecond
    fractions; Python 3.12 is permissive. Supabase serialises PostgreSQL
    timestamps with variable precision (2–7 digits common). Local Python 3.12
    smoke can pass on a 3/6-digit-only sample while AWS Python 3.10 then fails
    on production data with non-3/6-digit timestamps. (TD-NEW-13 lesson.)

    This helper pads with trailing zeros if shorter, truncates if longer;
    leaves the timezone suffix unchanged.
    """
    m = _MICROSECOND_RE.search(ts_str)
    if m is None:
        return ts_str  # no fractional seconds; nothing to normalise
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6:
        return ts_str  # already canonical
    if len(frac) < 6:
        frac6 = frac.ljust(6, "0")
    else:
        frac6 = frac[:6]
    return _MICROSECOND_RE.sub(f".{frac6}{tz}", ts_str)


def _ts_from_str(ts_str: str) -> datetime:
    """Parse an ISO-8601 timestamp string (any microsecond precision)."""
    norm = _normalize_microseconds(ts_str.replace("Z", "+00:00"))
    return datetime.fromisoformat(norm)


# ============================================================================
# Vol-pricing computation
# ============================================================================

def _compute_realized_vol(closes: list[float], window: int) -> Optional[float]:
    """
    Annualised realised volatility from the last `window` close prices.

    Requires `window + 1` closes (yields `window` log returns).
    Returns None if insufficient history.
    """
    if len(closes) < window + 1:
        return None
    tail = closes[-(window + 1):]
    log_returns = [math.log(tail[i] / tail[i - 1]) for i in range(1, len(tail))]
    n = len(log_returns)
    if n < 2:
        return None
    mean = sum(log_returns) / n
    variance = sum((r - mean) ** 2 for r in log_returns) / (n - 1)  # sample variance
    sigma_per_bar = math.sqrt(variance)
    return sigma_per_bar * ANNUALIZATION_FACTOR


def _classify_regime(rr: Optional[float]) -> Optional[str]:
    """Map RR ratio → regime per ADR-002 v2 §P7 thresholds."""
    if rr is None:
        return None
    if rr > RR_HIGH_MIN:
        return "HIGH"
    if rr >= RR_FAIR_MIN:
        return "FAIR"
    if rr >= RR_LOW_MIN:
        return "LOW"
    return "COMPRESSED"


# ============================================================================
# Supabase I/O
# ============================================================================

def _load_supabase_client() -> Client:
    """Standard dotenv → create_client pattern matching peer writers.

    Canonical env var name per `merdian_reference.json` .env schema:
        SUPABASE_SERVICE_ROLE_KEY  (used by Dhan token writer + outage runbook)
    Fallback names accepted for portability against older scripts.
    """
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env "
            "(checked also: SUPABASE_SERVICE_KEY, SUPABASE_KEY as fallbacks)"
        )
    return create_client(url, key)


def _lookup_cycle(sb: Client, run_id: str) -> Optional[dict]:
    """
    Resolve run_id → (symbol, ts, spot) from option_chain_snapshots.
    Returns None if no rows.
    """
    resp = (
        sb.table("option_chain_snapshots")
        .select("symbol, ts, spot")
        .eq("run_id", run_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return None
    r = rows[0]
    return {
        "symbol": r["symbol"],
        "ts": _ts_from_str(r["ts"]),
        "spot": float(r["spot"]) if r.get("spot") is not None else None,
    }


def _fetch_recent_closes(sb: Client, symbol: str, ts: datetime, n_bars: int) -> list[float]:
    """
    Fetch up to `n_bars + 1` most-recent 5-min spot closes at-or-before `ts`,
    return chronologically (oldest → newest).
    """
    resp = (
        sb.table("hist_spot_bars_5m")
        .select("bar_ts, close")
        .eq("symbol", symbol)
        .lte("bar_ts", ts.isoformat())
        .order("bar_ts", desc=True)
        .limit(n_bars + 1)
        .execute()
    )
    rows = resp.data or []
    # Reverse to chronological order.
    return [float(r["close"]) for r in reversed(rows) if r.get("close") is not None]


def _fetch_implied_vol_atm(sb: Client, symbol: str, ts: datetime) -> tuple[Optional[float], bool]:
    """
    Fetch implied_vol_atm for (symbol, ts) from volatility_snapshots.atm_iv_avg.
    Returns (iv_decimal, fallback_used).

    Unit normalisation: volatility_snapshots.atm_iv_avg is stored as
    PERCENTAGE POINTS (e.g., 18.07 means 18.07% IV); this function divides
    by 100.0 to return DECIMAL FRACTION (0.1807), matching the convention
    of realized_vol_10 / realized_vol_30 computed locally. rr_ratio is then
    a dimensionless ratio of two decimal fractions, comparable to
    ADR-002 v2 §P7 thresholds (1.2 / 0.85 / 0.4).

    The percentage-vs-decimal ambiguity was filed S24 as TD-095. Empirical
    audit S29 via direct SELECT confirmed percentage-points storage on
    live cohort; resolves TD-095. (B21 lesson application — verify column
    unit convention against source-of-truth before magnitude-consuming gates.)

    Lookup strategy:
      1. Exact (symbol, ts) match — preferred.
      2. Within ±IV_LOOKUP_TOLERANCE window — nearest by absolute time delta.
      3. None — caller decides whether to invoke option_chain fallback (which
         we do not implement here; left as TODO unless Phase 0b shows the
         volatility_snapshots path has NULL coverage in the historical cohort).
    """
    lower = (ts - IV_LOOKUP_TOLERANCE).isoformat()
    upper = (ts + IV_LOOKUP_TOLERANCE).isoformat()
    resp = (
        sb.table("volatility_snapshots")
        .select("ts, atm_iv_avg")
        .eq("symbol", symbol)
        .gte("ts", lower)
        .lte("ts", upper)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return (None, False)

    # Nearest by absolute Δt.
    def _delta(row: dict) -> float:
        return abs((_ts_from_str(row["ts"]) - ts).total_seconds())

    nearest = min(rows, key=_delta)
    iv_raw = nearest.get("atm_iv_avg")
    if iv_raw is None:
        return (None, False)

    # Normalise percentage points → decimal fraction (TD-095 resolution).
    iv_decimal = float(iv_raw) / 100.0
    return (iv_decimal, False)


def _upsert_vol_analytics(sb: Client, payload: dict) -> int:
    """
    Idempotent UPSERT into TARGET_TABLE (vol_analytics or vol_analytics_shadow).
    Returns number of rows written (1 on success).

    Per Assumption Register §D.11.1: TARGET_TABLE is the routing mechanism;
    same payload schema regardless of target.
    """
    resp = (
        sb.table(TARGET_TABLE)
        .upsert(payload, on_conflict="symbol,ts")
        .execute()
    )
    rows = resp.data or []
    return len(rows)


# ============================================================================
# Main
# ============================================================================

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="ENH-97 vol_analytics writer — RR ratio + regime per ADR-002 v2 §P7"
    )
    p.add_argument("run_id", type=str, help="UUID of option_chain_snapshots run_id")
    p.add_argument(
        "--shadow",
        action="store_true",
        help="Route writes to vol_analytics_shadow (AWS shadow path; D.11.1 invariant)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute and log but do not UPSERT (DRY_RUN exit_reason)",
    )
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    # Validate run_id is a UUID early — argparse type wouldn't catch malformed.
    try:
        UUID(args.run_id)
    except (ValueError, AttributeError):
        print(f"[ERROR] run_id must be a valid UUID; got {args.run_id!r}", file=sys.stderr)
        return 2

    # Target-table routing per D.11.1.
    global TARGET_TABLE
    TARGET_TABLE = "vol_analytics_shadow" if args.shadow else "vol_analytics"

    sb = _load_supabase_client()

    # Resolve cycle first so we can populate symbol on ExecutionLog row.
    cycle = _lookup_cycle(sb, args.run_id)
    if cycle is None:
        # No row found for this run_id; emit a SKIPPED_NO_INPUT row with empty
        # expected_writes (contract_met=TRUE because nothing was expected).
        log = ExecutionLog(
            script_name=SCRIPT_NAME,
            symbol=None,
            expected_writes={},
        )
        log.exit_with_reason(
            "SKIPPED_NO_INPUT",
            exit_code=0,
            notes=f"run_id={args.run_id} not found in option_chain_snapshots",
        )
        return 0

    symbol = cycle["symbol"]
    ts = cycle["ts"]

    # Expected writes: 1 row to TARGET_TABLE. Empty if dry-run.
    expected_writes = {} if args.dry_run else {TARGET_TABLE: 1}

    log = ExecutionLog(
        script_name=SCRIPT_NAME,
        symbol=symbol,
        expected_writes=expected_writes,
    )

    try:
        # --- Realized vol ---
        closes = _fetch_recent_closes(sb, symbol, ts, n_bars=WINDOW_SLOW_BARS)
        rv10 = _compute_realized_vol(closes, WINDOW_FAST_BARS)
        rv30 = _compute_realized_vol(closes, WINDOW_SLOW_BARS)

        # --- Implied vol ---
        iv, iv_fallback = _fetch_implied_vol_atm(sb, symbol, ts)

        # --- RR + regime ---
        if rv30 is not None and iv is not None and iv > 0:
            rr = rv30 / iv
        else:
            rr = None
        regime = _classify_regime(rr)

        # --- Diagnostic raw payload ---
        raw = {
            "realized_source": "hist_spot_bars_5m.close",
            "realized_unit": "decimal_fraction",  # 0.10 = 10% annualised
            "iv_source": "volatility_snapshots.atm_iv_avg",
            "iv_source_unit_native": "percentage_points",  # 18.07 = 18.07%
            "iv_unit_after_normalisation": "decimal_fraction",  # divided by 100.0
            "iv_normalisation_ref": "TD-095 resolution S29 / CLAUDE.md B21",
            "iv_fallback_used": iv_fallback,
            "bars_available": len(closes),
            "bars_used_10": min(len(closes), WINDOW_FAST_BARS + 1),
            "bars_used_30": min(len(closes), WINDOW_SLOW_BARS + 1),
            "annualization_factor": ANNUALIZATION_FACTOR,
            "regime_thresholds": {
                "HIGH": RR_HIGH_MIN,
                "FAIR_LOW": RR_FAIR_MIN,
                "COMPRESSED": RR_LOW_MIN,
            },
            "run_id": args.run_id,
            "target_table": TARGET_TABLE,
            "dry_run": args.dry_run,
        }

        # --- Build payload ---
        payload = {
            "ts": ts.astimezone(timezone.utc).isoformat(),
            "symbol": symbol,
            "realized_vol_10": rv10,
            "realized_vol_30": rv30,
            "implied_vol_atm": iv,
            "rr_ratio": rr,
            "rr_regime": regime,
            "raw": raw,
        }

        # --- Insufficient history is not a failure — it's a partial row ---
        # We still write the row (with NULLs where appropriate); rr_regime is
        # NULL because the CHECK constraint only allows the four named values.
        # contract_met will still be TRUE so long as actual_writes matches.

        if args.dry_run:
            log.exit_with_reason(
                "DRY_RUN",
                exit_code=0,
                notes=(
                    f"DRY_RUN {symbol} {ts.isoformat()} "
                    f"rv10={rv10} rv30={rv30} iv={iv} rr={rr} regime={regime} "
                    f"→ {TARGET_TABLE} (NOT WRITTEN)"
                ),
            )
            return 0

        # --- UPSERT ---
        n_written = _upsert_vol_analytics(sb, payload)
        log.record_write(TARGET_TABLE, n_written)

        if n_written < 1:
            log.exit_with_reason(
                "DATA_ERROR",
                exit_code=1,
                notes=f"UPSERT returned 0 rows for {symbol} {ts.isoformat()}",
            )
            return 1

        # --- Success ---
        log.complete(
            notes=(
                f"{symbol} {ts.isoformat()} "
                f"rv10={rv10} rv30={rv30} iv={iv} rr={rr} regime={regime} "
                f"→ {TARGET_TABLE}"
            )
        )
        return 0

    except Exception as exc:  # noqa: BLE001 — top-level catch for CRASH classification
        tb = traceback.format_exc()
        log.exit_with_reason(
            "CRASH",
            exit_code=2,
            notes=f"unhandled exception in {SCRIPT_NAME}",
            error_message=tb[:4000],  # keep stack trace bounded
        )
        print(tb, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
