#!/usr/bin/env python3
"""
build_ict_htf_zones.py
ENH-37 — MERDIAN ICT Higher-Timeframe Zone Builder

Builds weekly and daily ICT zones from hist_spot_bars_1m and writes
them to ict_htf_zones. Runs offline (not in the live runner cycle).

Schedule:
  Weekly zones:  Sunday night (or Monday pre-market) — one run per week
  Daily zones:   Pre-market each morning at 08:45 IST

Weekly zones built from:
  - Weekly OB: the last bearish/bullish candle before a strong weekly move
  - Weekly FVG: price gaps at the weekly open/close level
  - PDH/PDL: Prior week high and low (key liquidity levels)

Daily zones built from:
  - Daily OB: last session's key order block
  - PDH/PDL: Prior day high and low
  - Asia high/low (pre-market range — approximated from first 30 bars)

Usage:
  python build_ict_htf_zones.py --timeframe W   # build weekly zones
  python build_ict_htf_zones.py --timeframe D   # build daily zones
  python build_ict_htf_zones.py                 # build both

Read: hist_spot_bars_1m
Write: ict_htf_zones (upsert — safe to rerun)
"""

import os
import sys
import time
import argparse
from datetime import datetime, date, timedelta
from collections import defaultdict
from itertools import groupby

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000

# ── Config ────────────────────────────────────────────────────────────
OB_MIN_MOVE_PCT = 0.40  # % weekly/daily move to qualify as OB-generating
FVG_MIN_PCT     = 0.15  # % gap size for weekly FVG (larger than intraday)

EXPIRY_WD = {"NIFTY": 1, "SENSEX": 1}  # both Tuesday post-Sep 2025

# How many weeks/days back to build zones for
WEEKLY_LOOKBACK = 8   # 8 weeks of weekly zones
DAILY_LOOKBACK  = 5   # 5 days of daily zones


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def week_start(d):
    """Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())

def week_end(d):
    """Friday of the week containing date d."""
    return d - timedelta(days=d.weekday()) + timedelta(days=4)


# ── Data loading ──────────────────────────────────────────────────────

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


def load_daily_ohlcv(sb, inst_id, from_date, to_date):
    """
    Build daily OHLCV from hist_spot_bars_1m.
    Returns dict: {trade_date: {open, high, low, close, date}}
    """
    rows = fetch_paginated(
        sb, "hist_spot_bars_1m",
        [("eq", "instrument_id", inst_id),
         ("eq", "is_pre_market", False),
         ("gte", "trade_date", str(from_date)),
         ("lte", "trade_date", str(to_date))],
        "bar_ts, trade_date, open, high, low, close"
    )

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

    return daily


# ── Weekly zone detection ─────────────────────────────────────────────

def build_weekly_bars(daily_ohlcv):
    """
    Aggregate daily OHLCV into weekly bars.
    Returns list of weekly bar dicts sorted by week_start.
    """
    weekly = defaultdict(list)
    for d_str, bar in daily_ohlcv.items():
        d    = bar["date"]
        wk   = week_start(d)
        weekly[wk].append(bar)

    result = []
    for wk, bars in sorted(weekly.items()):
        bars.sort(key=lambda b: b["date"])
        result.append({
            "week_start": wk,
            "week_end":   week_end(wk),
            "open":       bars[0]["open"],
            "high":       max(b["high"]  for b in bars),
            "low":        min(b["low"]   for b in bars),
            "close":      bars[-1]["close"],
            "n_days":     len(bars),
        })

    return result


def detect_weekly_zones(weekly_bars, symbol):
    """
    Detect weekly-level ICT zones.
    Returns list of zone dicts ready for ict_htf_zones upsert.
    """
    zones = []
    n     = len(weekly_bars)

    for i in range(1, n):
        curr = weekly_bars[i]
        prev = weekly_bars[i - 1]

        # Week labels
        valid_from = curr["week_start"]
        valid_to   = curr["week_end"]
        src_date   = prev["week_end"]  # zone formed in prior week

        # ── Prior Week High / Low (liquidity levels) ──────────────────
        zones.append({
            "symbol":       symbol,
            "timeframe":    "W",
            "pattern_type": "PDH",
            "direction":    -1,         # PDH = resistance = bearish zone
            "zone_high":    prev["high"] + 20,  # small buffer
            "zone_low":     prev["high"] - 20,
            "valid_from":   str(valid_from),
            "valid_to":     str(valid_to),
            "source_bar_date": str(src_date),
            "status":       "ACTIVE",
        })
        zones.append({
            "symbol":       symbol,
            "timeframe":    "W",
            "pattern_type": "PDL",
            "direction":    +1,         # PDL = support = bullish zone
            "zone_high":    prev["low"] + 20,
            "zone_low":     prev["low"] - 20,
            "valid_from":   str(valid_from),
            "valid_to":     str(valid_to),
            "source_bar_date": str(src_date),
            "status":       "ACTIVE",
        })

        # ── Weekly Order Blocks ───────────────────────────────────────
        # Strong bullish week after bearish prior week → BULL_OB
        curr_move = pct(curr["open"], curr["close"])
        prev_move = pct(prev["open"], prev["close"])

        if curr_move >= OB_MIN_MOVE_PCT and prev_move < 0:
            # Bullish impulse week — prior bearish week is the OB
            zones.append({
                "symbol":       symbol,
                "timeframe":    "W",
                "pattern_type": "BULL_OB",
                "direction":    +1,
                "zone_high":    max(prev["open"], prev["close"]),
                "zone_low":     min(prev["open"], prev["close"]),
                "valid_from":   str(valid_from),
                "valid_to":     str(valid_to + timedelta(weeks=4)),  # persist 4 weeks
                "source_bar_date": str(src_date),
                "status":       "ACTIVE",
            })

        if curr_move <= -OB_MIN_MOVE_PCT and prev_move > 0:
            # Bearish impulse week — prior bullish week is the OB
            zones.append({
                "symbol":       symbol,
                "timeframe":    "W",
                "pattern_type": "BEAR_OB",
                "direction":    -1,
                "zone_high":    max(prev["open"], prev["close"]),
                "zone_low":     min(prev["open"], prev["close"]),
                "valid_from":   str(valid_from),
                "valid_to":     str(valid_to + timedelta(weeks=4)),
                "source_bar_date": str(src_date),
                "status":       "ACTIVE",
            })

        # ── Weekly FVG ────────────────────────────────────────────────
        if i >= 2:
            two_prev = weekly_bars[i - 2]
            ref = curr["open"]
            # Bullish FVG: gap between two_prev.high and curr.low
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "W",
                        "pattern_type": "BULL_FVG",
                        "direction":    +1,
                        "zone_high":    curr["low"],
                        "zone_low":     two_prev["high"],
                        "valid_from":   str(valid_from),
                        "valid_to":     str(valid_to + timedelta(weeks=4)),
                        "source_bar_date": str(src_date),
                        "status":       "ACTIVE",
                    })

    return zones


# ── Daily zone detection ──────────────────────────────────────────────

def detect_daily_zones(daily_ohlcv, symbol, target_date):
    """
    Detect daily-level ICT zones for the upcoming session (target_date).
    Looks at the prior trading day.
    Returns list of zone dicts.
    """
    dates = sorted(daily_ohlcv.keys())
    zones = []

    # Find prior day
    target_str = str(target_date)
    prior_dates = [d for d in dates if d < target_str]
    if not prior_dates:
        return zones

    prior_str = prior_dates[-1]
    prior     = daily_ohlcv[prior_str]

    valid_from = str(target_date)
    valid_to   = str(target_date)
    src_date   = prior_str

    # ── Prior Day High / Low ──────────────────────────────────────────
    zones.append({
        "symbol":       symbol,
        "timeframe":    "D",
        "pattern_type": "PDH",
        "direction":    -1,
        "zone_high":    prior["high"] + 10,
        "zone_low":     prior["high"] - 10,
        "valid_from":   valid_from,
        "valid_to":     valid_to,
        "source_bar_date": src_date,
        "status":       "ACTIVE",
    })
    zones.append({
        "symbol":       symbol,
        "timeframe":    "D",
        "pattern_type": "PDL",
        "direction":    +1,
        "zone_high":    prior["low"] + 10,
        "zone_low":     prior["low"] - 10,
        "valid_from":   valid_from,
        "valid_to":     valid_to,
        "source_bar_date": src_date,
        "status":       "ACTIVE",
    })

    # ── Prior Day Order Block ─────────────────────────────────────────
    prior_move = pct(prior["open"], prior["close"])

    if prior_move >= OB_MIN_MOVE_PCT:
        # Prior day was bullish — use prior day open candle as OB zone
        zones.append({
            "symbol":       symbol,
            "timeframe":    "D",
            "pattern_type": "BULL_OB",
            "direction":    +1,
            "zone_high":    max(prior["open"], prior["close"]),
            "zone_low":     min(prior["open"], prior["close"]),
            "valid_from":   valid_from,
            "valid_to":     valid_to,
            "source_bar_date": src_date,
            "status":       "ACTIVE",
        })

    if prior_move <= -OB_MIN_MOVE_PCT:
        zones.append({
            "symbol":       symbol,
            "timeframe":    "D",
            "pattern_type": "BEAR_OB",
            "direction":    -1,
            "zone_high":    max(prior["open"], prior["close"]),
            "zone_low":     min(prior["open"], prior["close"]),
            "valid_from":   valid_from,
            "valid_to":     valid_to,
            "source_bar_date": src_date,
            "status":       "ACTIVE",
        })

    return zones


# ── DB write ──────────────────────────────────────────────────────────

def upsert_zones(sb, zones, dry_run=False):
    """
    Upsert zones into ict_htf_zones.
    Deduplicates on (symbol, timeframe, pattern_type, source_bar_date,
    zone_high, zone_low).
    """
    if not zones:
        log("  No zones to write.")
        return 0

    if dry_run:
        log(f"  DRY RUN — would write {len(zones)} zones")
        for z in zones[:5]:
            log(f"    {z['symbol']} {z['timeframe']} {z['pattern_type']} "
                f"{z['zone_low']:.0f}-{z['zone_high']:.0f} "
                f"[{z['valid_from']}]")
        return 0

    written = 0
    batch_size = 50
    for i in range(0, len(zones), batch_size):
        batch = zones[i:i + batch_size]
        for attempt in range(4):
            try:
                sb.table("ict_htf_zones").upsert(
                    batch,
                    on_conflict="symbol,timeframe,pattern_type,"
                                "source_bar_date,zone_high,zone_low"
                ).execute()
                written += len(batch)
                break
            except Exception as e:
                if attempt == 3:
                    log(f"  ERROR writing batch {i}: {e}")
                time.sleep(2 ** attempt)

    return written


# ── Expire old zones ──────────────────────────────────────────────────

def expire_old_zones(sb, symbol, today, dry_run=False):
    """
    Mark zones with valid_to < today as EXPIRED.
    """
    if dry_run:
        log("  DRY RUN — would expire old zones")
        return

    try:
        sb.table("ict_htf_zones").update({
            "status": "EXPIRED",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("symbol", symbol).lt(
            "valid_to", str(today)
        ).eq("status", "ACTIVE").execute()
        log(f"  Expired old {symbol} zones before {today}")
    except Exception as e:
        log(f"  Warning: could not expire old zones: {e}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", choices=["W", "D", "both"],
                        default="both",
                        help="W=weekly, D=daily, both=all")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print zones without writing to DB")
    parser.add_argument("--date", default=str(date.today()),
                        help="Target date for daily zones (YYYY-MM-DD)")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date)
    do_weekly   = args.timeframe in ("W", "both")
    do_daily    = args.timeframe in ("D", "both")
    dry_run     = args.dry_run

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    total_written = 0

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        # Expire stale zones
        expire_old_zones(sb, symbol, target_date, dry_run)

        # Load OHLCV
        lookback_days = max(
            WEEKLY_LOOKBACK * 7 + 7,
            DAILY_LOOKBACK + 3
        )
        from_date = target_date - timedelta(days=lookback_days)
        log(f"  Loading daily OHLCV {from_date} → {target_date}...")

        daily_ohlcv = load_daily_ohlcv(
            sb, inst[symbol], from_date, target_date
        )
        log(f"  {len(daily_ohlcv)} trading days loaded")

        if do_weekly:
            log("  Building weekly zones...")
            weekly_bars = build_weekly_bars(daily_ohlcv)
            log(f"  {len(weekly_bars)} weekly bars")

            # Only last WEEKLY_LOOKBACK weeks
            weekly_bars = weekly_bars[-WEEKLY_LOOKBACK:]
            w_zones = detect_weekly_zones(weekly_bars, symbol)
            log(f"  Detected {len(w_zones)} weekly zones")

            n = upsert_zones(sb, w_zones, dry_run)
            log(f"  Written {n} weekly zones")
            total_written += n

        if do_daily:
            log("  Building daily zones...")
            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
            log(f"  Detected {len(d_zones)} daily zones")

            n = upsert_zones(sb, d_zones, dry_run)
            log(f"  Written {n} daily zones")
            total_written += n

    log(f"\nDone — {total_written} total zones written to ict_htf_zones")

    if not dry_run:
        log("\nVerify:")
        for symbol in ["NIFTY", "SENSEX"]:
            rows = (sb.table("ict_htf_zones")
                    .select("timeframe, pattern_type, zone_low, zone_high, "
                            "valid_from, valid_to, status")
                    .eq("symbol", symbol)
                    .eq("status", "ACTIVE")
                    .order("valid_from", desc=True)
                    .limit(10)
                    .execute().data)
            log(f"  {symbol}: {len(rows)} active HTF zones")
            for r in rows[:5]:
                log(f"    {r['timeframe']} {r['pattern_type']:10s} "
                    f"{float(r['zone_low']):,.0f}-{float(r['zone_high']):,.0f} "
                    f"[{r['valid_from']} → {r['valid_to']}]")


if __name__ == "__main__":
    main()
