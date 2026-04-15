#!/usr/bin/env python3
"""
build_ict_htf_zones.py
ENH-37 â€” MERDIAN ICT Higher-Timeframe Zone Builder

Builds weekly and daily ICT zones from hist_spot_bars_1m and writes
them to ict_htf_zones. Runs offline (not in the live runner cycle).

Schedule:
  Weekly zones:  Sunday night (or Monday pre-market) â€” one run per week
  Daily zones:   Pre-market each morning at 08:45 IST

Weekly zones built from:
  - Weekly OB: the last bearish/bullish candle before a strong weekly move
  - Weekly FVG: price gaps at the weekly open/close level
  - PDH/PDL: Prior week high and low (key liquidity levels)

Daily zones built from:
  - Daily OB: last session's key order block
  - PDH/PDL: Prior day high and low
  - Asia high/low (pre-market range â€” approximated from first 30 bars)

Usage:
  python build_ict_htf_zones.py --timeframe W   # build weekly zones
  python build_ict_htf_zones.py --timeframe D   # build daily zones
  python build_ict_htf_zones.py                 # build both

Read: hist_spot_bars_1m
Write: ict_htf_zones (upsert â€” safe to rerun)
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

# â”€â”€ Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
OB_MIN_MOVE_PCT = 0.40  # % weekly/daily move to qualify as OB-generating
FVG_MIN_PCT     = 0.15  # % gap size for weekly FVG (larger than intraday)

EXPIRY_WD = {"NIFTY": 1, "SENSEX": 1}  # both Tuesday post-Sep 2025

# How many weeks/days back to build zones for
WEEKLY_LOOKBACK = 52   # 8 weeks of weekly zones
DAILY_LOOKBACK  = 60   # 5 days of daily zones


# â”€â”€ Utilities â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€ Data loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€ Weekly zone detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

        # â”€â”€ Prior Week High / Low (liquidity levels) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Weekly Order Blocks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Strong bullish week after bearish prior week â†’ BULL_OB
        curr_move = pct(curr["open"], curr["close"])
        prev_move = pct(prev["open"], prev["close"])

        if curr_move >= OB_MIN_MOVE_PCT and prev_move < 0:
            # Bullish impulse week â€” prior bearish week is the OB
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
            # Bearish impulse week â€” prior bullish week is the OB
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

        # â”€â”€ Weekly FVG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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


# â”€â”€ Daily zone detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ Prior Day High / Low â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Prior Day Order Block â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    prior_move = pct(prior["open"], prior["close"])

    if prior_move >= OB_MIN_MOVE_PCT:
        # Prior day was bullish â€” use prior day open candle as OB zone
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


# â”€â”€ DB write â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


# ── Breach detection ──────────────────────────────────────────────────────────

def filter_breached_zones(zones: list, daily_ohlcv: dict, as_of: str) -> list:
    """
    ICT-aligned zone filter. Two rules:

    1. OBs and FVGs — keep if unmitigated relative to current price:
         BULL_OB / BULL_FVG: current_spot > zone_high  (support below price)
         BEAR_OB / BEAR_FVG: current_spot < zone_low   (resistance above price)

    2. PDH / PDL — keep nearest 2 above + 2 below current price only.
         ICT: most recent unmitigated PDH/PDL is highest priority.
         Older ones are superseded by newer structure.
    """
    sorted_dates = sorted(k for k in daily_ohlcv.keys() if k <= as_of)
    if not sorted_dates:
        return zones
    current_spot = daily_ohlcv[sorted_dates[-1]]["close"]

    ob_fvg = []
    pdh_above = []  # resistance PDH/PDL above current price
    pdl_below = []  # support PDH/PDL below current price

    for zone in zones:
        zone_high = float(zone["zone_high"])
        zone_low  = float(zone["zone_low"])
        pattern   = zone.get("pattern_type", "")
        direction = zone.get("direction", 0)

        if pattern in ("BULL_OB", "BULL_FVG"):
            # Support: valid if current price is above the zone
            if current_spot > zone_high:
                ob_fvg.append(zone)

        elif pattern in ("BEAR_OB", "BEAR_FVG"):
            # Resistance: valid if current price is below the zone
            if current_spot < zone_low:
                ob_fvg.append(zone)

        elif pattern == "PDH":
            # PDH = resistance level
            if current_spot < zone_low:
                # Above current price — potential overhead resistance
                pdh_above.append((zone_low, zone))
            # PDH below current price = already surpassed, skip

        elif pattern == "PDL":
            # PDL = support level
            if current_spot > zone_high:
                # Below current price — potential support
                pdl_below.append((zone_high, zone))
            # PDL above current price = doesn't make sense, skip

        else:
            # Unknown pattern type — keep
            ob_fvg.append(zone)

    # Sort PDH by proximity to current price (nearest first) — take top 2
    pdh_above.sort(key=lambda x: x[0])          # ascending = nearest first
    nearest_pdh = [z for _, z in pdh_above[:2]]

    # Sort PDL by proximity to current price (nearest first = highest PDL) — take top 2
    pdl_below.sort(key=lambda x: x[0], reverse=True)  # descending = nearest first
    nearest_pdl = [z for _, z in pdl_below[:2]]

    return ob_fvg + nearest_pdh + nearest_pdl
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
        log(f"  DRY RUN â€” would write {len(zones)} zones")
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


# â”€â”€ Expire old zones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def expire_old_zones(sb, symbol, today, dry_run=False):
    """
    Mark zones with valid_to < today as EXPIRED.
    """
    if dry_run:
        log("  DRY RUN â€” would expire old zones")
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


# â”€â”€ Main â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", choices=["W", "D", "H", "both"],
                        default="both",
                        help="W=weekly, D=daily, H=1H intraday, both=W+D")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print zones without writing to DB")
    parser.add_argument("--date", default=str(date.today()),
                        help="Target date (YYYY-MM-DD)")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date)
    do_weekly   = args.timeframe in ("W", "both")
    do_daily    = args.timeframe in ("D", "both")
    do_1h       = args.timeframe == "H"
    dry_run     = args.dry_run

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    total_written = 0

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"-- {symbol} ---")

        if do_1h:
            log("  Building 1H intraday zones...")
            h_zones = detect_1h_zones(sb, inst[symbol], symbol, target_date)
            log(f"  Detected {len(h_zones)} 1H zones")
            n = upsert_zones(sb, h_zones, dry_run)
            log(f"  Written {n} 1H zones")
            total_written += n
            continue

        expire_old_zones(sb, symbol, target_date, dry_run)

        lookback_days = max(WEEKLY_LOOKBACK * 7 + 7, DAILY_LOOKBACK + 3)
        from_date = target_date - timedelta(days=lookback_days)
        log(f"  Loading daily OHLCV {from_date} -> {target_date}...")
        daily_ohlcv = load_daily_ohlcv(sb, inst[symbol], from_date, target_date)
        log(f"  {len(daily_ohlcv)} trading days loaded")

        if do_weekly:
            log("  Building weekly zones...")
            weekly_bars = build_weekly_bars(daily_ohlcv)
            weekly_bars = weekly_bars[-WEEKLY_LOOKBACK:]
            w_zones = detect_weekly_zones(weekly_bars, symbol)
            w_zones = filter_breached_zones(w_zones, daily_ohlcv, str(target_date))
            log(f"  Detected {len(w_zones)} weekly zones (after breach filter)")
            n = upsert_zones(sb, w_zones, dry_run)
            log(f"  Written {n} weekly zones")
            total_written += n

        if do_daily:
            log("  Building daily zones...")
            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
            d_zones = filter_breached_zones(d_zones, daily_ohlcv, str(target_date))
            log(f"  Detected {len(d_zones)} daily zones (after breach filter)")
            n = upsert_zones(sb, d_zones, dry_run)
            log(f"  Written {n} daily zones")
            total_written += n

    log(f"Done -- {total_written} total zones written to ict_htf_zones")

    if not dry_run:
        log("Verify:")
        for symbol in ["NIFTY", "SENSEX"]:
            rows = (sb.table("ict_htf_zones")
                    .select("timeframe, pattern_type, zone_low, zone_high, valid_from, status")
                    .eq("symbol", symbol).eq("status", "ACTIVE")
                    .order("valid_from", desc=True).limit(10).execute().data)
            log(f"  {symbol}: {len(rows)} active HTF zones")
            for r in rows[:5]:
                log(f"    {r['timeframe']} {r['pattern_type']:10s} "
                    f"{float(r['zone_low']):,.0f}-{float(r['zone_high']):,.0f}")


if __name__ == "__main__":

    main()


# â”€â”€ 1H Zone Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Added for ENH-37 â€” 1H zones provide MEDIUM context for intraday signals
# MTF hierarchy: W=VERY_HIGH, D=HIGH, H=MEDIUM, none=LOW

def aggregate_to_hourly(intraday_bars):
    """
    Aggregate 1M spot bars into hourly OHLCV bars.
    Groups bars by hour (IST = UTC+5:30).
    Returns list of hourly bar dicts sorted by hour_start.
    """
    from datetime import timezone, timedelta as td
    IST = timezone(td(hours=5, minutes=30))

    hourly = defaultdict(list)
    for b in intraday_bars:
        ts     = datetime.fromisoformat(b["bar_ts"])
        ts_ist = ts.astimezone(IST)
        # Group by hour start (truncate to hour)
        hour_key = ts_ist.replace(minute=0, second=0, microsecond=0)
        hourly[hour_key].append(b)

    result = []
    for hour_start, bars in sorted(hourly.items()):
        bars.sort(key=lambda b: b["bar_ts"])
        result.append({
            "hour_start": hour_start,
            "open":       float(bars[0]["open"]),
            "high":       max(float(b["high"]) for b in bars),
            "low":        min(float(b["low"])  for b in bars),
            "close":      float(bars[-1]["close"]),
            "n_bars":     len(bars),
        })

    return result


def detect_1h_zones(sb, inst_id, symbol, trade_date):
    """
    Detect 1H ICT zones from today's intraday bars.
    Builds zones from each completed hourly bar.
    Only processes completed hours â€” current incomplete hour excluded.

    Returns list of zone dicts for ict_htf_zones upsert.
    """
    from datetime import timezone, timedelta as td
    IST = timezone(td(hours=5, minutes=30))

    # Fetch today's intraday bars
    rows = fetch_paginated(
        sb, "hist_spot_bars_1m",
        [("eq", "instrument_id", str(inst_id)),
         ("eq", "is_pre_market", False),
         ("eq", "trade_date", str(trade_date))],
        "bar_ts, trade_date, open, high, low, close"
    )

    if not rows:
        return []

    hourly_bars = aggregate_to_hourly(rows)
    now_ist     = datetime.now(IST)
    current_hour = now_ist.replace(minute=0, second=0, microsecond=0)

    # Only use completed hours (exclude current incomplete hour)
    completed = [h for h in hourly_bars if h["hour_start"] < current_hour]

    if len(completed) < 2:
        return []  # Need at least 2 hours for OB detection

    zones = []
    valid_from = str(trade_date)
    valid_to   = str(trade_date)
    n = len(completed)

    for i in range(1, n):
        curr = completed[i]
        prev = completed[i - 1]
        src_date = str(trade_date)

        curr_move = pct(curr["open"], curr["close"])
        prev_move = pct(prev["open"], prev["close"])

        # 1H BULL_OB: bearish candle (prev) before bullish impulse (curr)
        if curr_move >= OB_MIN_MOVE_PCT and prev["close"] < prev["open"]:
            zones.append({
                "symbol":       symbol,
                "timeframe":    "H",
                "pattern_type": "BULL_OB",
                "direction":    +1,
                "zone_high":    max(prev["open"], prev["close"]),
                "zone_low":     min(prev["open"], prev["close"]),
                "valid_from":   valid_from,
                "valid_to":     valid_to,
                "source_bar_date": src_date,
                "status":       "ACTIVE",
            })

        # 1H BEAR_OB: bullish candle (prev) before bearish impulse (curr)
        if curr_move <= -OB_MIN_MOVE_PCT and prev["close"] > prev["open"]:
            zones.append({
                "symbol":       symbol,
                "timeframe":    "H",
                "pattern_type": "BEAR_OB",
                "direction":    -1,
                "zone_high":    max(prev["open"], prev["close"]),
                "zone_low":     min(prev["open"], prev["close"]),
                "valid_from":   valid_from,
                "valid_to":     valid_to,
                "source_bar_date": src_date,
                "status":       "ACTIVE",
            })

        # 1H BULL_FVG: gap between prev-prev high and curr low
        if i >= 2:
            two_prev = completed[i - 2]
            ref = curr["open"]
            if two_prev["high"] < curr["low"]:
                gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "H",
                        "pattern_type": "BULL_FVG",
                        "direction":    +1,
                        "zone_high":    curr["low"],
                        "zone_low":     two_prev["high"],
                        "valid_from":   valid_from,
                        "valid_to":     valid_to,
                        "source_bar_date": src_date,
                        "status":       "ACTIVE",
                    })

    # Session high/low as liquidity reference
    if completed:
        session_high = max(h["high"] for h in completed)
        session_low  = min(h["low"]  for h in completed)

        zones.append({
            "symbol":       symbol,
            "timeframe":    "H",
            "pattern_type": "PDH",
            "direction":    -1,
            "zone_high":    session_high + 10,
            "zone_low":     session_high - 10,
            "valid_from":   valid_from,
            "valid_to":     valid_to,
            "source_bar_date": src_date,
            "status":       "ACTIVE",
        })
        zones.append({
            "symbol":       symbol,
            "timeframe":    "H",
            "pattern_type": "PDL",
            "direction":    +1,
            "zone_high":    session_low + 10,
            "zone_low":     session_low - 10,
            "valid_from":   valid_from,
            "valid_to":     valid_to,
            "source_bar_date": src_date,
            "status":       "ACTIVE",
        })

    return zones


