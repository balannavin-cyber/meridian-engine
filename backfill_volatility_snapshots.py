#!/usr/bin/env python3
"""
backfill_volatility_snapshots.py — Stage 1 of ENH-97 historical backfill.

Builds historical implied vol cohort by inverse Black-Scholes from the
canonical 5-min pre-aggregated tables (Apr 2025 — Mar 2026), enabling
Phase 0b RR ratio study against a full-year cohort.

Reads:    hist_atm_option_bars_5m  (CE/PE close per ATM strike per 5m bar
                                     per expiry; UNIQUE (instrument_id,
                                     bar_ts, expiry_date); 27,082 rows total)
          hist_spot_bars_5m         (spot OHLC; UNIQUE (instrument_id, bar_ts);
                                     41,248 rows total)
Writes:   volatility_snapshots      (atm_iv_avg as PERCENTAGE POINTS,
                                     matching S29-locked convention; VIX
                                     columns NULL in backfill)

Why 5m source tables, not 1m:
    The 1m tables (hist_spot_bars_1m, hist_option_bars_1m) are documented
    as EXECUTION GRANULARITY ONLY per merdian_reference.json
    `1m_bars_execution_only` rule. The 5m tables are pre-aggregated to our
    cycle cadence, pair CE/PE per row, store atm_strike per bar, are
    properly indexed for our access pattern, and are orders of magnitude
    smaller (27K rows vs 54.8M).

Refs:
- ENH-97 (vol_analytics + RR ratio writer, Phase 0b enablement)
- ADR-002 v2 §P7 (vol-pricing principle)
- TD-095 (resolved S29 — atm_iv_avg storage is percentage_points)
- ENH-71 (write-contract: ExecutionLog instrumentation)
- CLAUDE.md B21 (unit-scale audit before magnitude consumers)
- CLAUDE.md B22 (cross-Python microsecond normalization)
- merdian_reference.json `1m_bars_execution_only` rule

Call signature:
    python backfill_volatility_snapshots.py \\
        --start 2025-04-01 --end 2026-03-07 \\
        [--mode gap-only|overwrite|verify] \\
        [--symbol NIFTY|SENSEX|both] \\
        [--dry-run]
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import traceback
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, Iterator

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore
from scipy.optimize import brentq  # type: ignore
from scipy.stats import norm  # type: ignore

from core.execution_log import ExecutionLog  # type: ignore


# ============================================================================
# Module-level constants
# ============================================================================

SCRIPT_NAME = "backfill_volatility_snapshots.py"

RISK_FREE_RATE = 0.065

# Spot instrument_id — both hist_*_5m tables key by this.
SPOT_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# 5-min cycle grid — 75 boundaries per trading day.
SESSION_START_IST = time(9, 15)
SESSION_END_IST   = time(15, 25)
CYCLE_INTERVAL_MIN = 5

IST_TZ_OFFSET = timedelta(hours=5, minutes=30)

VERIFY_DIVERGENCE_PCT = 0.05

IV_SIGMA_MIN = 0.001
IV_SIGMA_MAX = 5.0


# ============================================================================
# Cross-Python stdlib compat — per CLAUDE.md B22
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


# ============================================================================
# Cycle grid generation
# ============================================================================

def _iter_5min_boundaries(trade_date: date) -> Iterator[tuple[datetime, datetime]]:
    """
    Yield (read_ts, write_ts) tuples for 75 cycles of one trading day:
      read_ts:  IST-clock-time stamped with `+00:00` tz marker — matches
                bar_ts convention of hist_spot_bars_5m / hist_atm_option_bars_5m
      write_ts: real UTC — matches volatility_snapshots forward writer
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
# Black-Scholes pricing + inverse
# ============================================================================

def _bs_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def _bs_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return max(K - S, 0.0)
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def _implied_vol(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str,
) -> Optional[float]:
    if T <= 0 or market_price <= 0:
        return None

    if option_type == "CE":
        intrinsic = max(S - K * math.exp(-r * T), 0.0)
        pricer = _bs_call
    elif option_type == "PE":
        intrinsic = max(K * math.exp(-r * T) - S, 0.0)
        pricer = _bs_put
    else:
        return None

    if market_price < intrinsic - 0.01:
        return None

    def f(sigma: float) -> float:
        return pricer(S, K, T, r, sigma) - market_price

    try:
        f_lo = f(IV_SIGMA_MIN)
        f_hi = f(IV_SIGMA_MAX)
        if f_lo * f_hi > 0:
            return None
        return float(brentq(f, IV_SIGMA_MIN, IV_SIGMA_MAX, xtol=1e-5, maxiter=100))
    except (ValueError, RuntimeError):
        return None


def _compute_atm_iv_avg(
    ce_iv: Optional[float],
    pe_iv: Optional[float],
) -> Optional[float]:
    """Per merdian_reference.json: IV=0 filter; if CE IV=0 use PE IV (symmetric)."""
    ce_ok = ce_iv is not None and ce_iv > 0
    pe_ok = pe_iv is not None and pe_iv > 0
    if ce_ok and pe_ok:
        return (ce_iv + pe_iv) / 2.0
    if ce_ok:
        return ce_iv
    if pe_ok:
        return pe_iv
    return None


# ============================================================================
# Supabase I/O — per-day batched against canonical 5m tables
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


def _fetch_day_spot_bars(sb: Client, symbol: str, trade_date: date) -> dict[datetime, float]:
    """{bar_ts_ist_as_utc: close} from hist_spot_bars_5m. ~75 rows/day."""
    instrument_id = SPOT_INSTRUMENT_ID[symbol]
    day_start = f"{trade_date.isoformat()}T09:15:00+00:00"
    day_end = f"{trade_date.isoformat()}T15:30:00+00:00"
    resp = (
        sb.table("hist_spot_bars_5m")
        .select("bar_ts, close")
        .eq("instrument_id", instrument_id)
        .gte("bar_ts", day_start)
        .lte("bar_ts", day_end)
        .execute()
    )
    out: dict[datetime, float] = {}
    for r in (resp.data or []):
        if r.get("close") is None:
            continue
        out[_ts_from_str(r["bar_ts"])] = float(r["close"])
    return out


def _fetch_day_atm_option_bars(sb: Client, symbol: str, trade_date: date) -> dict[datetime, list[dict]]:
    """{bar_ts_ist_as_utc: [rows_per_expiry]} from hist_atm_option_bars_5m. ~150-225 rows/day."""
    instrument_id = SPOT_INSTRUMENT_ID[symbol]
    day_start = f"{trade_date.isoformat()}T09:15:00+00:00"
    day_end = f"{trade_date.isoformat()}T15:30:00+00:00"
    resp = (
        sb.table("hist_atm_option_bars_5m")
        .select("bar_ts, atm_strike, expiry_date, ce_close, pe_close")
        .eq("instrument_id", instrument_id)
        .gte("bar_ts", day_start)
        .lte("bar_ts", day_end)
        .execute()
    )
    by_ts: dict[datetime, list[dict]] = {}
    for r in (resp.data or []):
        try:
            ts = _ts_from_str(r["bar_ts"])
        except (KeyError, ValueError):
            continue
        by_ts.setdefault(ts, []).append(r)
    return by_ts


def _fetch_existing_volatility_keys(
    sb: Client, start_utc: datetime, end_utc: datetime
) -> set[tuple[str, str]]:
    """
    Pre-fetch existing (symbol, floored_ts) keys for gap-only mode.
    The ts is floored to 5-min boundary because forward writer rows have
    cycle-jitter (10-15s past boundary) while backfill writes on-boundary;
    flooring brings them to a common key.
    """
    existing: set[tuple[str, str]] = set()
    page_size = 1000
    offset = 0
    while True:
        resp = (
            sb.table("volatility_snapshots")
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
            try:
                floored = _floor_ts_to_5min(_ts_from_str(r["ts"])).isoformat()
            except (KeyError, ValueError):
                continue
            existing.add((r["symbol"], floored))
        if len(rows) < page_size:
            break
        offset += page_size
    return existing


def _batch_upsert_volatility_snapshots(sb: Client, payloads: list[dict]) -> int:
    """
    Batch UPSERT on (symbol, ts). Single HTTP request per call regardless
    of row count. Reduces request count for full-year backfill from ~32K
    single-row writes to ~1K batch writes, well under Supabase's HTTP/2
    server-side stream limit (~20K streams per connection).
    """
    if not payloads:
        return 0
    resp = (
        sb.table("volatility_snapshots")
        .upsert(payloads, on_conflict="symbol,ts")
        .execute()
    )
    return len(resp.data or [])


# ============================================================================
# Per-day processing
# ============================================================================

def _pick_current_week_row(
    candidates: list[dict], trade_date: date
) -> Optional[tuple[date, dict]]:
    """Smallest expiry_date >= trade_date. Returns (expiry, row)."""
    out: list[tuple[date, dict]] = []
    for r in candidates:
        try:
            exp = date.fromisoformat(str(r["expiry_date"]))
        except (ValueError, TypeError, KeyError):
            continue
        if exp >= trade_date:
            out.append((exp, r))
    if not out:
        return None
    out.sort(key=lambda x: x[0])
    return out[0]


def _process_day(
    sb: Client,
    symbol: str,
    trade_date: date,
    mode: str,
    dry_run: bool,
    existing_keys: set[tuple[str, str]],
    verify_compare: dict[tuple[str, str], float],
) -> dict:
    counters = {
        "cycles": 0, "written": 0, "skipped_existing": 0,
        "skipped_no_spot": 0, "skipped_no_options": 0,
        "skipped_no_expiry": 0, "skipped_iv_failed": 0,
        "verify_within": 0, "verify_divergent": 0,
        "verify_max_divergence": 0.0,
    }

    spot_bars = _fetch_day_spot_bars(sb, symbol, trade_date)
    if not spot_bars:
        counters["skipped_no_spot"] = 75
        return counters

    atm_bars_by_ts = _fetch_day_atm_option_bars(sb, symbol, trade_date)
    if not atm_bars_by_ts:
        counters["skipped_no_options"] = 75
        return counters

    pending_payloads: list[dict] = []  # accumulated for end-of-day batch upsert

    for read_ts, write_ts in _iter_5min_boundaries(trade_date):
        counters["cycles"] += 1

        spot = spot_bars.get(read_ts)
        if spot is None:
            for offset_min in (-5, 5, -10, 10):
                alt = read_ts + timedelta(minutes=offset_min)
                if alt in spot_bars:
                    spot = spot_bars[alt]
                    break
        if spot is None:
            counters["skipped_no_spot"] += 1
            continue

        candidates = atm_bars_by_ts.get(read_ts, [])
        if not candidates:
            counters["skipped_no_options"] += 1
            continue
        picked = _pick_current_week_row(candidates, trade_date)
        if picked is None:
            counters["skipped_no_expiry"] += 1
            continue
        expiry, atm_row = picked

        try:
            atm_strike = float(atm_row["atm_strike"])
        except (ValueError, TypeError, KeyError):
            counters["skipped_no_options"] += 1
            continue

        ce_price = float(atm_row["ce_close"]) if atm_row.get("ce_close") is not None else None
        pe_price = float(atm_row["pe_close"]) if atm_row.get("pe_close") is not None else None
        if ce_price is None and pe_price is None:
            counters["skipped_no_options"] += 1
            continue

        dte_days = (expiry - trade_date).days
        if dte_days < 0:
            counters["skipped_no_expiry"] += 1
            continue
        T = max(dte_days, 0.5) / 365.0

        ce_iv = _implied_vol(ce_price, spot, atm_strike, T, RISK_FREE_RATE, "CE") if ce_price else None
        pe_iv = _implied_vol(pe_price, spot, atm_strike, T, RISK_FREE_RATE, "PE") if pe_price else None

        atm_iv_decimal = _compute_atm_iv_avg(ce_iv, pe_iv)
        if atm_iv_decimal is None:
            counters["skipped_iv_failed"] += 1
            continue

        atm_iv_pct = atm_iv_decimal * 100.0
        ce_iv_pct = ce_iv * 100.0 if ce_iv is not None else None
        pe_iv_pct = pe_iv * 100.0 if pe_iv is not None else None
        iv_skew = (
            (ce_iv_pct - pe_iv_pct)
            if (ce_iv_pct is not None and pe_iv_pct is not None)
            else None
        )

        ts_str = write_ts.isoformat()
        key = (symbol, ts_str)

        if mode == "verify":
            existing_pct = verify_compare.get(key)
            if existing_pct is None:
                continue
            divergence = abs(atm_iv_pct - existing_pct) / max(abs(existing_pct), 1e-6)
            counters["verify_max_divergence"] = max(
                counters["verify_max_divergence"], divergence
            )
            if divergence > VERIFY_DIVERGENCE_PCT:
                counters["verify_divergent"] += 1
            else:
                counters["verify_within"] += 1
            continue

        if mode == "gap-only" and key in existing_keys:
            counters["skipped_existing"] += 1
            continue

        payload = {
            "ts": ts_str,
            "symbol": symbol,
            "expiry_date": expiry.isoformat(),
            "expiry_type": "WEEKLY",
            "dte": dte_days,
            "spot": spot,
            "atm_strike": int(atm_strike),
            "atm_call_iv": ce_iv_pct,
            "atm_put_iv": pe_iv_pct,
            "atm_iv_avg": atm_iv_pct,
            "iv_skew": iv_skew,
            "raw": {
                "backfill_session": "S29",
                "iv_method": "inverse_BS_brentq",
                "r": RISK_FREE_RATE,
                "iv_source_unit": "percentage_points",
                "atm_source": "hist_atm_option_bars_5m",
                "spot_source": "hist_spot_bars_5m",
                "dte_floor_days": 0.5,
                "atm_avg_rule": "(ce+pe)/2 with IV=0 fallback to single side",
            },
        }

        if dry_run:
            counters["written"] += 1
            continue

        pending_payloads.append(payload)

    # End-of-day batch upsert — single HTTP request for all cycles of this day.
    if pending_payloads and not dry_run and mode != "verify":
        n = _batch_upsert_volatility_snapshots(sb, pending_payloads)
        counters["written"] += n

    return counters


# ============================================================================
# Main
# ============================================================================

def _ist_to_utc(d: date, t: time) -> datetime:
    ist_naive = datetime.combine(d, t)
    return (ist_naive - IST_TZ_OFFSET).replace(tzinfo=timezone.utc)


def _floor_ts_to_5min(ts: datetime) -> datetime:
    """
    Floor a datetime to its enclosing 5-min boundary (UTC seconds-zero).

    The forward writer (compute_volatility_metrics_local.py) writes
    volatility_snapshots.ts inheriting from option_chain_snapshots.ts, which
    captures whenever the ingest cycle actually fires — typically 5–15
    seconds past the cron boundary. So forward rows have jittered ts like
    `09:56:08+00`, while this backfill writes boundary-aligned `09:55:00+00`.
    Flooring brings them to the same key for verify / gap-only alignment.
    """
    minute_floor = (ts.minute // 5) * 5
    return ts.replace(minute=minute_floor, second=0, microsecond=0)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Stage 1: hist_atm_option_bars_5m → volatility_snapshots"
    )
    p.add_argument("--start", required=True, type=date.fromisoformat)
    p.add_argument("--end", required=True, type=date.fromisoformat)
    p.add_argument("--mode", default="gap-only",
                   choices=["gap-only", "overwrite", "verify"])
    p.add_argument("--symbol", default="both",
                   choices=["NIFTY", "SENSEX", "both"])
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

    target_table = "volatility_snapshots"
    expected_writes = {} if args.dry_run or args.mode == "verify" else {target_table: estimated}

    log = ExecutionLog(
        script_name=SCRIPT_NAME,
        symbol=None if len(symbols) > 1 else symbols[0],
        expected_writes=expected_writes,
    )

    try:
        existing_keys: set[tuple[str, str]] = set()
        verify_compare: dict[tuple[str, str], float] = {}

        if args.mode == "gap-only":
            existing_keys = _fetch_existing_volatility_keys(sb, start_utc, end_utc)
        elif args.mode == "verify":
            # Paginate the verify comparison fetch to handle ranges larger
            # than 1000 rows (Supabase REST hard cap per request).
            page_size = 1000
            offset = 0
            while True:
                resp = (
                    sb.table("volatility_snapshots")
                    .select("symbol, ts, atm_iv_avg")
                    .gte("ts", start_utc.isoformat())
                    .lte("ts", end_utc.isoformat())
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                rows = resp.data or []
                if not rows:
                    break
                for r in rows:
                    if r.get("atm_iv_avg") is None:
                        continue
                    try:
                        floored = _floor_ts_to_5min(_ts_from_str(r["ts"])).isoformat()
                    except (KeyError, ValueError):
                        continue
                    verify_compare[(r["symbol"], floored)] = float(r["atm_iv_avg"])
                if len(rows) < page_size:
                    break
                offset += page_size

        totals = {
            "cycles": 0, "written": 0, "skipped_existing": 0,
            "skipped_no_spot": 0, "skipped_no_options": 0,
            "skipped_no_expiry": 0, "skipped_iv_failed": 0,
            "verify_within": 0, "verify_divergent": 0,
            "verify_max_divergence": 0.0,
        }

        current = args.start
        while current <= args.end:
            if current.weekday() < 5:
                for sym in symbols:
                    counters = _process_day(
                        sb, sym, current, args.mode, args.dry_run,
                        existing_keys, verify_compare,
                    )
                    for k in totals:
                        if k == "verify_max_divergence":
                            totals[k] = max(totals[k], counters[k])
                        else:
                            totals[k] += counters[k]
                    if not args.dry_run and args.mode != "verify" and counters["written"] > 0:
                        log.record_write(target_table, counters["written"])
            current += timedelta(days=1)

        notes = (
            f"mode={args.mode} symbols={','.join(symbols)} "
            f"range={args.start}..{args.end} cycles={totals['cycles']} "
            f"written={totals['written']} skipped_existing={totals['skipped_existing']} "
            f"skipped_no_spot={totals['skipped_no_spot']} "
            f"skipped_no_options={totals['skipped_no_options']} "
            f"skipped_no_expiry={totals['skipped_no_expiry']} "
            f"skipped_iv_failed={totals['skipped_iv_failed']}"
        )
        if args.mode == "verify":
            notes += (
                f" verify_within={totals['verify_within']} "
                f"verify_divergent={totals['verify_divergent']} "
                f"verify_max_divergence={totals['verify_max_divergence']:.4f}"
            )

        if args.mode == "verify":
            if totals["verify_divergent"] > 0:
                log.exit_with_reason("DATA_ERROR", exit_code=1, notes=notes)
                print(notes, file=sys.stderr)
                return 1
            log.complete(notes=notes)
            print(notes)
            return 0

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
