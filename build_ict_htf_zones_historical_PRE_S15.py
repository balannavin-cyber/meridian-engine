#!/usr/bin/env python3
"""
build_ict_htf_zones_historical.py
===================================
ENH-53: Backfill historical ICT HTF zones for all 247 trading sessions.

For each trading date in hist_spot_bars_1m, computes what D and W zones
were valid ON THAT DATE using only data available as-of that date
(no lookahead). Writes to hist_ict_htf_zones table.

This gives experiments and backtests accurate ICT zone context for every
historical session — not today's backward-looking zones.

New table: hist_ict_htf_zones
Schema mirrors ict_htf_zones + as_of_date column.

DDL (run in Supabase SQL editor first):
    CREATE TABLE IF NOT EXISTS public.hist_ict_htf_zones (
        id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        as_of_date      date NOT NULL,
        symbol          text NOT NULL,
        timeframe       text NOT NULL,
        pattern_type    text NOT NULL,
        direction       integer NOT NULL,
        zone_high       numeric NOT NULL,
        zone_low        numeric NOT NULL,
        valid_from      date NOT NULL,
        valid_to        date NOT NULL,
        source_bar_date text NOT NULL,
        status          text NOT NULL DEFAULT 'ACTIVE',
        created_at      timestamptz DEFAULT now()
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_hist_ict_htf_zones_key
        ON public.hist_ict_htf_zones
        (as_of_date, symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low);
    CREATE INDEX IF NOT EXISTS idx_hist_ict_htf_zones_date_sym
        ON public.hist_ict_htf_zones (as_of_date, symbol);

Usage:
    python build_ict_htf_zones_historical.py              # full backfill
    python build_ict_htf_zones_historical.py --dry-run    # preview only
    python build_ict_htf_zones_historical.py --symbol NIFTY
    python build_ict_htf_zones_historical.py --from-date 2025-10-01

SESSION 15 PATCH (2026-05-01):
    - S1.a fix: added BEAR_FVG detection in detect_weekly_zones()
      (mirror of existing BULL_FVG branch; symmetric ICT definition).
    - S1.b fix: added BULL_FVG and BEAR_FVG detection in detect_daily_zones()
      (new code path, did not exist previously).
    - New constant FVG_D_MIN_PCT (0.10%) controls D-timeframe FVG threshold
      independently of W-timeframe (FVG_MIN_PCT, 0.15%).
    - Daily FVG validity_to extended to target_date + 5 trading days
      (D-FVG zones live longer than D-OB; this is a deliberate ICT convention).
    - All non-S1 bugs catalogued during review (D-OB definition mismatch,
      D-zone single-day validity for non-FVG, fixed +/-20 PDH/PDL band,
      status never updated) are intentionally LEFT UNCHANGED in this patch.
      They are tracked separately as TD candidates.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from itertools import groupby
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE       = 1_000
OB_MIN_MOVE_PCT = 0.40   # % move to qualify as OB-generating
FVG_MIN_PCT     = 0.15   # % gap size for weekly FVG
FVG_D_MIN_PCT   = 0.10   # % gap size for daily FVG (S1.b: new constant)
WEEKLY_LOOKBACK = 52     # weeks of history to use for weekly zones
DAILY_LOOKBACK  = 60     # days of history for daily zones
D_FVG_VALID_DAYS = 5     # daily FVG validity window in calendar days

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def pct(a: float, b: float) -> float:
    return 100.0 * (b - a) / a if a else 0.0


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_end(d: date) -> date:
    return d - timedelta(days=d.weekday()) + timedelta(days=4)


# ── Data loading ──────────────────────────────────────────────────────────────

def fetch_paginated(sb, table, filters, select, order="bar_ts"):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select).order(order).range(
            offset, offset + PAGE_SIZE - 1)
        for method, *args in filters:
            q = getattr(q, method)(*args)
        rows = None
        for attempt in range(4):
            try:
                rows = q.execute().data
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def load_all_daily_ohlcv(sb, inst_id: str) -> dict:
    """
    Load ALL daily OHLCV from hist_spot_bars_1m for one instrument.
    Returns dict: {date_str: {date, open, high, low, close}}
    Sorted by date ascending.
    """
    log(f"  Loading all daily bars from hist_spot_bars_1m...")
    rows = fetch_paginated(
        sb, "hist_spot_bars_1m",
        [("eq", "instrument_id", inst_id),
         ("eq", "is_pre_market", False)],
        "bar_ts, trade_date, open, high, low, close",
        order="bar_ts"
    )
    log(f"  Fetched {len(rows):,} 1-min bars")

    daily = {}
    for k, g in groupby(rows, key=lambda r: r["trade_date"]):
        bars = list(g)
        daily[k] = {
            "date":  date.fromisoformat(k),
            "open":  float(bars[0]["open"]),
            "high":  max(float(b["high"]) for b in bars),
            "low":   min(float(b["low"])  for b in bars),
            "close": float(bars[-1]["close"]),
        }

    log(f"  Built {len(daily)} daily bars")
    return daily


def get_trading_dates(daily_ohlcv: dict) -> list[date]:
    """Return sorted list of all trading dates."""
    return sorted(date.fromisoformat(d) for d in daily_ohlcv.keys())


# ── Zone detection (reused from build_ict_htf_zones.py) ──────────────────────

def build_weekly_bars(daily_ohlcv: dict) -> list[dict]:
    weekly = defaultdict(list)
    for d_str, bar in daily_ohlcv.items():
        d  = bar["date"]
        wk = week_start(d)
        weekly[wk].append(bar)

    result = []
    for wk, bars in sorted(weekly.items()):
        bars.sort(key=lambda b: b["date"])
        result.append({
            "week_start": wk,
            "week_end":   week_end(wk),
            "open":       bars[0]["open"],
            "high":       max(b["high"] for b in bars),
            "low":        min(b["low"]  for b in bars),
            "close":      bars[-1]["close"],
            "n_days":     len(bars),
        })
    return result


def detect_weekly_zones(weekly_bars: list, symbol: str, as_of: date) -> list[dict]:
    zones = []
    n = len(weekly_bars)

    for i in range(1, n):
        curr = weekly_bars[i]
        prev = weekly_bars[i - 1]

        # Only include zones that are valid as of the target date
        if curr["week_start"] > as_of:
            break

        valid_from = curr["week_start"]
        valid_to   = curr["week_end"]
        src_date   = prev["week_end"]

        # PDH / PDL
        zones.append({
            "as_of_date":     str(as_of),
            "symbol":         symbol,
            "timeframe":      "W",
            "pattern_type":   "PDH",
            "direction":      -1,
            "zone_high":      prev["high"] + 20,
            "zone_low":       prev["high"] - 20,
            "valid_from":     str(valid_from),
            "valid_to":       str(valid_to),
            "source_bar_date": str(src_date),
            "status":         "ACTIVE",
        })
        zones.append({
            "as_of_date":     str(as_of),
            "symbol":         symbol,
            "timeframe":      "W",
            "pattern_type":   "PDL",
            "direction":      +1,
            "zone_high":      prev["low"] + 20,
            "zone_low":       prev["low"] - 20,
            "valid_from":     str(valid_from),
            "valid_to":       str(valid_to),
            "source_bar_date": str(src_date),
            "status":         "ACTIVE",
        })

        curr_move = pct(curr["open"], curr["close"])
        prev_move = pct(prev["open"], prev["close"])

        if curr_move >= OB_MIN_MOVE_PCT and prev_move < 0:
            zones.append({
                "as_of_date":     str(as_of),
                "symbol":         symbol,
                "timeframe":      "W",
                "pattern_type":   "BULL_OB",
                "direction":      +1,
                "zone_high":      max(prev["open"], prev["close"]),
                "zone_low":       min(prev["open"], prev["close"]),
                "valid_from":     str(valid_from),
                "valid_to":       str(valid_to + timedelta(weeks=4)),
                "source_bar_date": str(src_date),
                "status":         "ACTIVE",
            })

        if curr_move <= -OB_MIN_MOVE_PCT and prev_move > 0:
            zones.append({
                "as_of_date":     str(as_of),
                "symbol":         symbol,
                "timeframe":      "W",
                "pattern_type":   "BEAR_OB",
                "direction":      -1,
                "zone_high":      max(prev["open"], prev["close"]),
                "zone_low":       min(prev["open"], prev["close"]),
                "valid_from":     str(valid_from),
                "valid_to":       str(valid_to + timedelta(weeks=4)),
                "source_bar_date": str(src_date),
                "status":         "ACTIVE",
            })

        if i >= 2:
            two_prev = weekly_bars[i - 2]
            ref = curr["open"]

            # === BULL_FVG: gap-up imbalance (existing) ===
            # 3-bar structure: two_prev high < curr low, with curr displacing up.
            # The FVG is the gap between two_prev high and curr low.
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "as_of_date":     str(as_of),
                        "symbol":         symbol,
                        "timeframe":      "W",
                        "pattern_type":   "BULL_FVG",
                        "direction":      +1,
                        "zone_high":      curr["low"],
                        "zone_low":       two_prev["high"],
                        "valid_from":     str(valid_from),
                        "valid_to":       str(valid_to + timedelta(weeks=4)),
                        "source_bar_date": str(src_date),
                        "status":         "ACTIVE",
                    })

            # === S1.a FIX: BEAR_FVG ===
            # 3-bar structure: two_prev low > curr high, with curr displacing down.
            # The FVG is the gap between curr high and two_prev low.
            if two_prev["low"] > curr["high"]:
                gap_pct = (two_prev["low"] - curr["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "as_of_date":     str(as_of),
                        "symbol":         symbol,
                        "timeframe":      "W",
                        "pattern_type":   "BEAR_FVG",
                        "direction":      -1,
                        "zone_high":      two_prev["low"],
                        "zone_low":       curr["high"],
                        "valid_from":     str(valid_from),
                        "valid_to":       str(valid_to + timedelta(weeks=4)),
                        "source_bar_date": str(src_date),
                        "status":         "ACTIVE",
                    })

    return zones


def detect_daily_zones(daily_ohlcv: dict, symbol: str, target_date: date) -> list[dict]:
    dates = sorted(daily_ohlcv.keys())
    zones = []

    target_str  = str(target_date)
    prior_dates = [d for d in dates if d < target_str]
    if not prior_dates:
        return zones

    prior_str = prior_dates[-1]
    prior     = daily_ohlcv[prior_str]
    valid_from = str(target_date)
    valid_to   = str(target_date)
    src_date   = prior_str

    # === PDH / PDL (existing) ===
    zones.append({
        "as_of_date":     str(target_date),
        "symbol":         symbol,
        "timeframe":      "D",
        "pattern_type":   "PDH",
        "direction":      -1,
        "zone_high":      prior["high"] + 10,
        "zone_low":       prior["high"] - 10,
        "valid_from":     valid_from,
        "valid_to":       valid_to,
        "source_bar_date": src_date,
        "status":         "ACTIVE",
    })
    zones.append({
        "as_of_date":     str(target_date),
        "symbol":         symbol,
        "timeframe":      "D",
        "pattern_type":   "PDL",
        "direction":      +1,
        "zone_high":      prior["low"] + 10,
        "zone_low":       prior["low"] - 10,
        "valid_from":     valid_from,
        "valid_to":       valid_to,
        "source_bar_date": src_date,
        "status":         "ACTIVE",
    })

    # === D-OB (existing; non-standard ICT def — flagged S2.a, NOT changed) ===
    prior_move = pct(prior["open"], prior["close"])

    if prior_move >= OB_MIN_MOVE_PCT:
        zones.append({
            "as_of_date":     str(target_date),
            "symbol":         symbol,
            "timeframe":      "D",
            "pattern_type":   "BULL_OB",
            "direction":      +1,
            "zone_high":      max(prior["open"], prior["close"]),
            "zone_low":       min(prior["open"], prior["close"]),
            "valid_from":     valid_from,
            "valid_to":       valid_to,
            "source_bar_date": src_date,
            "status":         "ACTIVE",
        })

    if prior_move <= -OB_MIN_MOVE_PCT:
        zones.append({
            "as_of_date":     str(target_date),
            "symbol":         symbol,
            "timeframe":      "D",
            "pattern_type":   "BEAR_OB",
            "direction":      -1,
            "zone_high":      max(prior["open"], prior["close"]),
            "zone_low":       min(prior["open"], prior["close"]),
            "valid_from":     valid_from,
            "valid_to":       valid_to,
            "source_bar_date": src_date,
            "status":         "ACTIVE",
        })

    # === S1.b FIX: D-FVG detection (new, both directions) ===
    # Need 3 consecutive prior daily candles. The FVG is the gap created by
    # the middle candle's displacement that leaves an imbalance between the
    # outer two.
    #
    # Convention: K = oldest, K+1 = displacement bar, K+2 = newest prior bar.
    # The FVG zone references K (oldest) and K+2 (newest) for boundaries.
    # source_bar_date is K+1 (the bar that created the imbalance).
    if len(prior_dates) >= 3:
        k_str   = prior_dates[-3]   # oldest of the 3
        k1_str  = prior_dates[-2]   # displacement bar
        k2_str  = prior_dates[-1]   # newest prior (== prior_str above)
        k       = daily_ohlcv[k_str]
        k1      = daily_ohlcv[k1_str]
        k2      = daily_ohlcv[k2_str]
        ref     = k1["open"]

        # D-FVG zones get a 5-day validity window (longer than D-OB which is 1d)
        d_fvg_valid_to = str(target_date + timedelta(days=D_FVG_VALID_DAYS))

        # BULL_FVG (D): gap-up imbalance.
        # K.high < K2.low, with K1 being a strong upward displacement.
        # The FVG is the gap [K.high, K2.low].
        if k["high"] < k2["low"]:
            gap_pct = (k2["low"] - k["high"]) / ref * 100
            if gap_pct >= FVG_D_MIN_PCT:
                zones.append({
                    "as_of_date":     str(target_date),
                    "symbol":         symbol,
                    "timeframe":      "D",
                    "pattern_type":   "BULL_FVG",
                    "direction":      +1,
                    "zone_high":      k2["low"],
                    "zone_low":       k["high"],
                    "valid_from":     valid_from,
                    "valid_to":       d_fvg_valid_to,
                    "source_bar_date": k1_str,
                    "status":         "ACTIVE",
                })

        # BEAR_FVG (D): gap-down imbalance.
        # K.low > K2.high, with K1 being a strong downward displacement.
        # The FVG is the gap [K2.high, K.low].
        if k["low"] > k2["high"]:
            gap_pct = (k["low"] - k2["high"]) / ref * 100
            if gap_pct >= FVG_D_MIN_PCT:
                zones.append({
                    "as_of_date":     str(target_date),
                    "symbol":         symbol,
                    "timeframe":      "D",
                    "pattern_type":   "BEAR_FVG",
                    "direction":      -1,
                    "zone_high":      k["low"],
                    "zone_low":       k2["high"],
                    "valid_from":     valid_from,
                    "valid_to":       d_fvg_valid_to,
                    "source_bar_date": k1_str,
                    "status":         "ACTIVE",
                })

    return zones


# ── DB write ──────────────────────────────────────────────────────────────────

def upsert_zones(sb, zones: list, dry_run: bool = False) -> int:
    if not zones:
        return 0

    if dry_run:
        log(f"  DRY RUN — would write {len(zones)} zones")
        for z in zones[:3]:
            log(f"    {z['as_of_date']} {z['symbol']} {z['timeframe']} "
                f"{z['pattern_type']} {z['zone_low']:.0f}-{z['zone_high']:.0f}")
        return 0

    written = 0
    batch_size = 100
    for i in range(0, len(zones), batch_size):
        batch = zones[i:i + batch_size]
        for attempt in range(4):
            try:
                sb.table("hist_ict_htf_zones").upsert(
                    batch,
                    on_conflict="as_of_date,symbol,timeframe,pattern_type,"
                                "source_bar_date,zone_high,zone_low"
                ).execute()
                written += len(batch)
                break
            except Exception as e:
                if attempt == 3:
                    log(f"  ERROR writing batch: {e}")
                time.sleep(2 ** attempt)

    return written


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical ICT HTF zones for all trading dates"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing to DB")
    parser.add_argument("--symbol", choices=["NIFTY", "SENSEX", "both"],
                        default="both")
    parser.add_argument("--from-date", default=None,
                        help="Start from this date (YYYY-MM-DD). Default: all dates.")
    parser.add_argument("--ddl", action="store_true",
                        help="Print DDL and exit")
    args = parser.parse_args()

    if args.ddl:
        print("""
-- Run this in Supabase SQL editor before first run:
CREATE TABLE IF NOT EXISTS public.hist_ict_htf_zones (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    as_of_date      date NOT NULL,
    symbol          text NOT NULL,
    timeframe       text NOT NULL,
    pattern_type    text NOT NULL,
    direction       integer NOT NULL,
    zone_high       numeric NOT NULL,
    zone_low        numeric NOT NULL,
    valid_from      date NOT NULL,
    valid_to        date NOT NULL,
    source_bar_date text NOT NULL,
    status          text NOT NULL DEFAULT 'ACTIVE',
    created_at      timestamptz DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_hist_ict_htf_zones_key
    ON public.hist_ict_htf_zones
    (as_of_date, symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low);
CREATE INDEX IF NOT EXISTS idx_hist_ict_htf_zones_date_sym
    ON public.hist_ict_htf_zones (as_of_date, symbol);
        """)
        return

    symbols = ["NIFTY", "SENSEX"] if args.symbol == "both" else [args.symbol]
    from_date = date.fromisoformat(args.from_date) if args.from_date else None

    log("=" * 60)
    log("MERDIAN — Historical ICT HTF Zone Backfill")
    log("S15 patch: BEAR_FVG (W) + BULL_FVG/BEAR_FVG (D) detection added")
    log("DRY RUN — no writes" if args.dry_run else "LIVE — writing to hist_ict_htf_zones")
    log("=" * 60)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    total_written = 0

    for symbol in symbols:
        inst_id = INSTRUMENTS[symbol]
        log(f"\n{'='*20} {symbol} {'='*20}")

        # Load ALL daily OHLCV once
        daily_ohlcv = load_all_daily_ohlcv(sb, inst_id)
        trading_dates = get_trading_dates(daily_ohlcv)

        if from_date:
            trading_dates = [d for d in trading_dates if d >= from_date]

        log(f"  Trading dates to process: {len(trading_dates)}")
        log(f"  Range: {trading_dates[0]} -> {trading_dates[-1]}")

        symbol_written = 0

        for i, td in enumerate(trading_dates):
            # Build as-of snapshot — only data available before this date
            # For weekly: all weeks up to and including the week before td
            # For daily: all days before td

            # Daily OHLCV available as-of td (excludes td itself — prior day is latest)
            asof_daily = {
                k: v for k, v in daily_ohlcv.items()
                if date.fromisoformat(k) < td
            }

            if not asof_daily:
                continue

            all_zones = []

            # Daily zones
            d_zones = detect_daily_zones(asof_daily, symbol, td)
            all_zones.extend(d_zones)

            # Weekly zones — use weekly lookback from td
            lookback_start = td - timedelta(weeks=WEEKLY_LOOKBACK)
            weekly_daily = {
                k: v for k, v in asof_daily.items()
                if date.fromisoformat(k) >= lookback_start
            }
            if weekly_daily:
                weekly_bars = build_weekly_bars(weekly_daily)
                w_zones = detect_weekly_zones(weekly_bars, symbol, td)
                all_zones.extend(w_zones)

            n = upsert_zones(sb, all_zones, dry_run=args.dry_run)
            symbol_written += n

            if (i + 1) % 20 == 0 or i == len(trading_dates) - 1:
                log(f"  [{i+1}/{len(trading_dates)}] {td} — "
                    f"{len(all_zones)} zones | total written: {symbol_written}")

        log(f"  {symbol} complete: {symbol_written} zone-rows written")
        total_written += symbol_written

    log("\n" + "=" * 60)
    log(f"Backfill complete. {total_written} total zone-rows written.")
    log("Verify: SELECT as_of_date, symbol, COUNT(*) FROM hist_ict_htf_zones")
    log("        GROUP BY as_of_date, symbol ORDER BY as_of_date LIMIT 10;")
    log("=" * 60)


if __name__ == "__main__":
    main()
