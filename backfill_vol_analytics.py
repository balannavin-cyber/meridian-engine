#!/usr/bin/env python3
"""
backfill_vol_analytics.py — Stage 2 of ENH-97 historical backfill.

Consumes the Stage 1 backfilled volatility_snapshots cohort (Apr 2025 -)
plus realized vol from hist_spot_bars_5m, computes rr_ratio + rr_regime
per cycle per ADR-002 v2 §P7, batch-writes to vol_analytics.

Reads:   hist_spot_bars_5m         (realized vol source — full year coverage)
         volatility_snapshots      (implied vol source — Stage 1 backfilled
                                    Apr 2025 → today; mixed methodology:
                                    backfilled via inverse BS, forward via
                                    broker IV. Documented divergence accepted.)
Writes:  vol_analytics             (rr_ratio + rr_regime; same schema as
                                    forward writer compute_vol_analytics_local.py)

Key algorithmic constants (matches compute_vol_analytics_local.py):
  WINDOW_FAST_BARS = 10  (50-min realized vol)
  WINDOW_SLOW_BARS = 30  (150-min — RR numerator)
  ANNUALIZATION_FACTOR = sqrt(252 × 75)
  IV plausibility gate: [IV_MIN_PCT, IV_MAX_PCT] = [5, 80] percentage points
    Per Path A decision S29: rows outside this band produce rr_regime=NULL
    (cohort cleaning for inverse-BS tail artifacts in backfilled rows; ~7%
    of cohort affected, dominated by deep-OTM/near-zero-premium failures).
  Regime: HIGH > 1.2, FAIR 0.85-1.2, LOW 0.4-0.85, COMPRESSED < 0.4

Refs:
- ENH-97 (vol_analytics + RR ratio writer)
- ADR-002 v2 §P7 (vol-pricing principle)
- CLAUDE.md B21 (unit-scale audit; B22 cross-Python compat)
- ENH-71 (write-contract instrumentation)

Call signature:
    python backfill_vol_analytics.py \\
        --start 2025-04-01 --end 2026-03-30 \\
        [--mode gap-only|overwrite] \\
        [--symbol NIFTY|SENSEX|both] \\
        [--dry-run]
"""
from __future__ import annotations

import argparse
import bisect
import math
import os
import re
import sys
import traceback
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, Iterator

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore

from core.execution_log import ExecutionLog  # type: ignore


# ============================================================================
# Constants — must match compute_vol_analytics_local.py
# ============================================================================

SCRIPT_NAME = "backfill_vol_analytics.py"

WINDOW_FAST_BARS = 10
WINDOW_SLOW_BARS = 30

BARS_PER_TRADING_DAY = 75
ANNUALIZATION_FACTOR = math.sqrt(252 * BARS_PER_TRADING_DAY)  # ≈ 137.48

RR_HIGH_MIN = 1.20
RR_FAIR_MIN = 0.85
RR_LOW_MIN  = 0.40

# IV plausibility gate (percentage points) — Path A cohort cleaning S29.
IV_MIN_PCT = 5.0
IV_MAX_PCT = 80.0

# Spot instrument_id resolution.
SPOT_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# 5-min cycle grid.
SESSION_START_IST = time(9, 15)
SESSION_END_IST   = time(15, 25)
CYCLE_INTERVAL_MIN = 5

IST_TZ_OFFSET = timedelta(hours=5, minutes=30)


# ============================================================================
# Cross-Python stdlib compat
# ============================================================================

_MICROSECOND_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


def _normalize_microseconds(ts_str: str) -> str:
    m = _MICROSECOND_RE.search(ts_str)
    if m is None:
        return ts_str
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6:
        return ts_str
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MICROSECOND_RE.sub(f".{frac6}{tz}", ts_str)


def _ts_from_str(ts_str: str) -> datetime:
    norm = _normalize_microseconds(ts_str.replace("Z", "+00:00"))
    return datetime.fromisoformat(norm)


def _floor_ts_to_5min(ts: datetime) -> datetime:
    """Floor to 5-min boundary; matches Stage 1 alignment convention."""
    minute_floor = (ts.minute // 5) * 5
    return ts.replace(minute=minute_floor, second=0, microsecond=0)


# ============================================================================
# Cycle grid
# ============================================================================

def _iter_5min_boundaries(trade_date: date) -> Iterator[tuple[datetime, datetime]]:
    """
    Yield (read_ts, write_ts) — read_ts is IST-clock-as-UTC (matches
    hist_spot_bars_5m); write_ts is real UTC (matches vol_analytics).
    """
    cur_ist = datetime.combine(trade_date, SESSION_START_IST)
    end_ist = datetime.combine(trade_date, SESSION_END_IST)
    step = timedelta(minutes=CYCLE_INTERVAL_MIN)
    while cur_ist <= end_ist:
        read_ts = cur_ist.replace(tzinfo=timezone.utc)
        write_ts = (cur_ist - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)
        yield (read_ts, write_ts)
        cur_ist += step


# ============================================================================
# Realized vol — log-return stdev × annualisation
# ============================================================================

def _compute_realized_vol(closes: list[float], window: int) -> Optional[float]:
    """Annualised realised vol from the last `window` closes. Returns decimal."""
    if len(closes) < window + 1:
        return None
    tail = closes[-(window + 1):]
    log_returns = [math.log(tail[i] / tail[i - 1]) for i in range(1, len(tail))]
    n = len(log_returns)
    if n < 2:
        return None
    mean = sum(log_returns) / n
    variance = sum((r - mean) ** 2 for r in log_returns) / (n - 1)
    return math.sqrt(variance) * ANNUALIZATION_FACTOR


def _classify_regime(rr: Optional[float]) -> Optional[str]:
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
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
        )
    return create_client(url, key)


def _fetch_day_closes_with_warmup(
    sb: Client, symbol: str, trade_date: date, limit: int = 200,
) -> tuple[list[datetime], list[float]]:
    """
    Fetch the most-recent `limit` 5m closes at-or-before session end for one
    (symbol, trade_date). Returns (bar_ts_list, close_list) chronologically
    sorted — typical: 75 bars from today + 125 from prior trading day(s) for
    realized-vol warmup history. Single query per day per symbol.
    """
    instrument_id = SPOT_INSTRUMENT_ID[symbol]
    # Session-end read_ts in IST-clock-as-UTC (matches hist_spot_bars_5m convention)
    session_end_read = datetime.combine(trade_date, SESSION_END_IST).replace(
        tzinfo=timezone.utc
    )
    resp = (
        sb.table("hist_spot_bars_5m")
        .select("bar_ts, close")
        .eq("instrument_id", instrument_id)
        .lte("bar_ts", session_end_read.isoformat())
        .order("bar_ts", desc=True)
        .limit(limit)
        .execute()
    )
    rows = resp.data or []
    bar_tses: list[datetime] = []
    closes: list[float] = []
    # Reverse for chronological order.
    for r in reversed(rows):
        if r.get("close") is None:
            continue
        try:
            ts = _ts_from_str(r["bar_ts"])
            close = float(r["close"])
        except (KeyError, ValueError, TypeError):
            continue
        bar_tses.append(ts)
        closes.append(close)
    return bar_tses, closes


def _fetch_day_iv_map(sb: Client, symbol: str, trade_date: date) -> dict[datetime, float]:
    """
    Fetch all volatility_snapshots IVs for one (symbol, trade_date), keyed by
    floored 5-min boundary (real UTC). Resolves Stage 1's mix of
    boundary-aligned backfilled rows + jittered forward-writer rows into a
    common lookup.
    """
    # Real-UTC day range: 03:45 UTC = 09:15 IST market open, etc.
    day_start = _ist_to_utc(trade_date, SESSION_START_IST)
    day_end = _ist_to_utc(trade_date, SESSION_END_IST) + timedelta(minutes=5)

    out: dict[datetime, float] = {}
    page_size = 1000
    offset = 0
    while True:
        resp = (
            sb.table("volatility_snapshots")
            .select("ts, atm_iv_avg")
            .eq("symbol", symbol)
            .gte("ts", day_start.isoformat())
            .lte("ts", day_end.isoformat())
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break
        for r in rows:
            iv = r.get("atm_iv_avg")
            if iv is None:
                continue
            try:
                floored = _floor_ts_to_5min(_ts_from_str(r["ts"]))
            except (KeyError, ValueError):
                continue
            # If multiple rows fall in the same 5-min bucket (forward writer
            # ran twice; or backfill + forward overlap), keep the first.
            out.setdefault(floored, float(iv))
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _fetch_existing_vol_analytics_keys(
    sb: Client, start_utc: datetime, end_utc: datetime
) -> set[tuple[str, str]]:
    """Existing (symbol, ts) keys for gap-only mode. ts is already boundary-aligned in vol_analytics."""
    existing: set[tuple[str, str]] = set()
    page_size = 1000
    offset = 0
    while True:
        resp = (
            sb.table("vol_analytics")
            .select("symbol, ts")
            .gte("ts", start_utc.isoformat())
            .lte("ts", end_utc.isoformat())
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break
        for r in rows:
            existing.add((r["symbol"], r["ts"]))
        if len(rows) < page_size:
            break
        offset += page_size
    return existing


def _batch_upsert_vol_analytics(sb: Client, payloads: list[dict]) -> int:
    if not payloads:
        return 0
    resp = (
        sb.table("vol_analytics")
        .upsert(payloads, on_conflict="symbol,ts")
        .execute()
    )
    return len(resp.data or [])


# ============================================================================
# Per-day processing
# ============================================================================

def _process_day(
    sb: Client,
    symbol: str,
    trade_date: date,
    mode: str,
    dry_run: bool,
    existing_keys: set[tuple[str, str]],
) -> dict:
    counters = {
        "cycles": 0, "written": 0, "skipped_existing": 0,
        "skipped_no_iv": 0, "skipped_iv_implausible": 0,
        "skipped_insufficient_bars": 0,
    }

    iv_by_floored_ts = _fetch_day_iv_map(sb, symbol, trade_date)
    if not iv_by_floored_ts:
        counters["skipped_no_iv"] = 75
        return counters

    # Pre-fetch day's closes + warmup history once. Per-cycle slicing via bisect.
    bar_tses, closes = _fetch_day_closes_with_warmup(sb, symbol, trade_date)
    if not bar_tses:
        counters["skipped_insufficient_bars"] = 75
        return counters

    pending_payloads: list[dict] = []

    for read_ts, write_ts in _iter_5min_boundaries(trade_date):
        counters["cycles"] += 1

        iv_pct = iv_by_floored_ts.get(write_ts)
        if iv_pct is None:
            counters["skipped_no_iv"] += 1
            continue

        if iv_pct < IV_MIN_PCT or iv_pct > IV_MAX_PCT:
            counters["skipped_iv_implausible"] += 1
            continue

        iv_decimal = iv_pct / 100.0

        # In-memory slice: find rightmost bar_ts <= read_ts; take up to that index.
        idx = bisect.bisect_right(bar_tses, read_ts) - 1
        if idx < WINDOW_SLOW_BARS:
            counters["skipped_insufficient_bars"] += 1
            continue
        window_closes = closes[: idx + 1]

        rv10 = _compute_realized_vol(window_closes, WINDOW_FAST_BARS)
        rv30 = _compute_realized_vol(window_closes, WINDOW_SLOW_BARS)
        if rv30 is None:
            counters["skipped_insufficient_bars"] += 1
            continue

        rr = rv30 / iv_decimal
        regime = _classify_regime(rr)

        ts_str = write_ts.isoformat()
        key = (symbol, ts_str)

        if mode == "gap-only" and key in existing_keys:
            counters["skipped_existing"] += 1
            continue

        payload = {
            "ts": ts_str,
            "symbol": symbol,
            "realized_vol_10": rv10,
            "realized_vol_30": rv30,
            "implied_vol_atm": iv_decimal,
            "rr_ratio": rr,
            "rr_regime": regime,
            "raw": {
                "backfill_session": "S29",
                "iv_source": "volatility_snapshots.atm_iv_avg",
                "iv_source_unit_native": "percentage_points",
                "iv_unit_after_normalisation": "decimal_fraction",
                "iv_plausibility_gate": [IV_MIN_PCT, IV_MAX_PCT],
                "realized_source": "hist_spot_bars_5m.close",
                "bars_used_10": min(idx + 1, WINDOW_FAST_BARS + 1),
                "bars_used_30": min(idx + 1, WINDOW_SLOW_BARS + 1),
                "annualization_factor": ANNUALIZATION_FACTOR,
                "regime_thresholds": {
                    "HIGH": RR_HIGH_MIN,
                    "FAIR_LOW": RR_FAIR_MIN,
                    "COMPRESSED": RR_LOW_MIN,
                },
            },
        }

        if dry_run:
            counters["written"] += 1
            continue

        pending_payloads.append(payload)

    if pending_payloads and not dry_run:
        n = _batch_upsert_vol_analytics(sb, pending_payloads)
        counters["written"] += n

    return counters


# ============================================================================
# Main
# ============================================================================

def _ist_to_utc(d: date, t: time) -> datetime:
    ist_naive = datetime.combine(d, t)
    return (ist_naive - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Stage 2: volatility_snapshots → vol_analytics (rr_ratio + regime)"
    )
    p.add_argument("--start", required=True, type=date.fromisoformat)
    p.add_argument("--end", required=True, type=date.fromisoformat)
    p.add_argument("--mode", default="gap-only", choices=["gap-only", "overwrite"])
    p.add_argument("--symbol", default="both", choices=["NIFTY", "SENSEX", "both"])
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if args.end < args.start:
        print(f"[ERROR] --end {args.end} < --start {args.start}", file=sys.stderr)
        return 2

    symbols = ["NIFTY", "SENSEX"] if args.symbol == "both" else [args.symbol]
    sb = _load_supabase_client()

    start_utc = _ist_to_utc(args.start, SESSION_START_IST)
    end_utc = _ist_to_utc(args.end, SESSION_END_IST)

    n_days = (args.end - args.start).days + 1
    estimated = n_days * 75 * len(symbols)

    target_table = "vol_analytics"
    expected_writes = {} if args.dry_run else {target_table: estimated}

    log = ExecutionLog(
        script_name=SCRIPT_NAME,
        symbol=None if len(symbols) > 1 else symbols[0],
        expected_writes=expected_writes,
    )

    try:
        existing_keys: set[tuple[str, str]] = set()
        if args.mode == "gap-only":
            existing_keys = _fetch_existing_vol_analytics_keys(sb, start_utc, end_utc)

        totals = {
            "cycles": 0, "written": 0, "skipped_existing": 0,
            "skipped_no_iv": 0, "skipped_iv_implausible": 0,
            "skipped_insufficient_bars": 0,
        }

        current = args.start
        while current <= args.end:
            if current.weekday() < 5:
                for sym in symbols:
                    counters = _process_day(
                        sb, sym, current, args.mode, args.dry_run, existing_keys,
                    )
                    for k in totals:
                        totals[k] += counters[k]
                    if not args.dry_run and counters["written"] > 0:
                        log.record_write(target_table, counters["written"])
            current += timedelta(days=1)

        notes = (
            f"mode={args.mode} symbols={','.join(symbols)} "
            f"range={args.start}..{args.end} cycles={totals['cycles']} "
            f"written={totals['written']} skipped_existing={totals['skipped_existing']} "
            f"skipped_no_iv={totals['skipped_no_iv']} "
            f"skipped_iv_implausible={totals['skipped_iv_implausible']} "
            f"skipped_insufficient_bars={totals['skipped_insufficient_bars']}"
        )

        if args.dry_run:
            log.exit_with_reason("DRY_RUN", exit_code=0, notes=notes)
            print(notes)
            return 0

        log.complete(notes=notes)
        print(notes)
        return 0

    except Exception:
        tb = traceback.format_exc()
        log.exit_with_reason(
            "CRASH",
            exit_code=2,
            notes=f"unhandled exception in {SCRIPT_NAME}",
            error_message=tb[:4000],
        )
        print(tb, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
