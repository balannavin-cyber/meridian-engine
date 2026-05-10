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

SESSION 15 PATCH (2026-05-01) — mirrors historical builder patches:
  - S1.a fix: W BEAR_FVG detection added in detect_weekly_zones().
  - S1.b fix: D BULL_FVG and D BEAR_FVG detection added in
              detect_daily_zones() (new code path).
  - 1H BEAR_FVG: parallel fix in detect_1h_zones() (same root cause as W).
  - New constant FVG_D_MIN_PCT (0.10%) for D timeframe.
  - New constant D_FVG_VALID_DAYS (5) for D-FVG validity window.
  - filter_breached_zones() unchanged — already symmetric in pattern_type
    handling; will treat new BEAR_FVG entries correctly.
  - recheck_breached_zones() unchanged — already iterates BULL_FVG / BEAR_FVG
    in its update sets.
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

# ENH-71 instrumentation (added Session 11, F3 / TD-017 close)
from core.execution_log import ExecutionLog

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000

# ── Config ───────────────────────────────────────────────────────────────────
OB_MIN_MOVE_PCT = 0.40  # % weekly/daily move to qualify as OB-generating
FVG_MIN_PCT     = 0.15  # % gap size for weekly / 1H FVG
FVG_D_MIN_PCT   = 0.10  # % gap size for daily FVG (S1.b: new constant)

EXPIRY_WD = {"NIFTY": 1, "SENSEX": 1}  # both Tuesday post-Sep 2025

# How many weeks/days back to build zones for
WEEKLY_LOOKBACK = 52   # 52 weeks of weekly zones
DAILY_LOOKBACK  = 60   # 60 days of daily zones
D_FVG_VALID_DAYS = 5   # daily FVG validity window in calendar days


# ── Utilities ────────────────────────────────────────────────────────────────

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


# ── Data loading ─────────────────────────────────────────────────────────────

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


# ── Weekly zone detection ────────────────────────────────────────────────────

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


# TD-070 (Session 21, 2026-05-06): unbreached-anchor lookback helper.
# Spec: 8-week lookback, most-recent-opposing, body-low/body-high breach test.
TD070_LOOKBACK_WEEKS = 8


def _find_unbreached_anchor(weekly_bars, i, direction):
    """Find the most recent unbreached opposing-direction weekly bar in the
    8-week lookback window before bar i.

    Args:
        weekly_bars: list of weekly bar dicts with open/high/low/close/week_end.
        i:           index of the impulse (current) bar in weekly_bars.
        direction:   "BULL" -> looking for bearish anchor; "BEAR" -> bullish.

    Returns:
        The anchor bar dict if found and unbreached. None otherwise.

    Breach rule (body-based, TD-070 spec):
        BULL anchor (bearish bar) is breached if ANY intervening bar K+1..i-1
            has low < anchor body_low (= min(open, close)).
        BEAR anchor (bullish bar) is breached if ANY intervening bar K+1..i-1
            has high > anchor body_high (= max(open, close)).

    Backward-compat: when the prior bar (i-1) is opposing, no intervening bars
    exist; the anchor is vacuously unbreached. Behavior matches pre-TD-070 code.
    """
    if direction not in ("BULL", "BEAR"):
        raise ValueError(f"direction must be BULL or BEAR, got {direction!r}")

    start = max(0, i - TD070_LOOKBACK_WEEKS)
    # Walk K from i-1 down to start (most recent first).
    for k in range(i - 1, start - 1, -1):
        anchor = weekly_bars[k]

        # Filter to the right anchor direction.
        if direction == "BULL":
            is_anchor = anchor["close"] < anchor["open"]   # bearish bar
        else:  # BEAR
            is_anchor = anchor["close"] > anchor["open"]   # bullish bar

        if not is_anchor:
            continue

        # Check breach by intervening bars k+1 .. i-1 (may be empty).
        body_low  = min(anchor["open"], anchor["close"])
        body_high = max(anchor["open"], anchor["close"])
        breached = False
        for j in range(k + 1, i):
            interv = weekly_bars[j]
            if direction == "BULL":
                if interv["low"] < body_low:
                    breached = True
                    break
            else:  # BEAR
                if interv["high"] > body_high:
                    breached = True
                    break

        if not breached:
            return anchor
        # else continue scanning further back

    return None


def _dedup_zones_by_conflict_key(zones):
    """Dedup zones list by the upsert ON CONFLICT key.

    TD-070 v2 (Session 21, 2026-05-06): when multiple impulse weeks find
    the same unbreached anchor via _find_unbreached_anchor(), both produce
    OB zones with identical (symbol, timeframe, pattern_type,
    source_bar_date, zone_high, zone_low). upsert_zones() ON CONFLICT
    matches that exact key, so the batched upsert fails with Postgres 21000
    (cannot affect row a second time).

    Resolution: collapse duplicates to the entry with the earliest
    valid_from. Zone is "published" the moment the first impulse confirms
    it; subsequent impulses are re-confirmations of the same zone.
    """
    seen = {}
    for z in zones:
        key = (
            z["symbol"],
            z["timeframe"],
            z["pattern_type"],
            z["source_bar_date"],
            z["zone_high"],
            z["zone_low"],
        )
        if key not in seen or z["valid_from"] < seen[key]["valid_from"]:
            seen[key] = z
    return list(seen.values())


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

        # ── Weekly Order Blocks ──────────────────────────────────────
        # Strong bullish week after bearish prior week → BULL_OB
        curr_move = pct(curr["open"], curr["close"])
        prev_move = pct(prev["open"], prev["close"])

        # TD-070: 8-week unbreached-anchor lookback for BULL_OB.
        # Find most recent bearish week in i-1 .. max(0, i-8) that is unbreached
        # by intervening weeks (no intervening low < anchor body_low).
        if curr_move >= OB_MIN_MOVE_PCT:
            anchor = _find_unbreached_anchor(weekly_bars, i, direction="BULL")
            if anchor is not None:
                zones.append({
                    "symbol":       symbol,
                    "timeframe":    "W",
                    "pattern_type": "BULL_OB",
                    "direction":    +1,
                    "zone_high":    max(anchor["open"], anchor["close"]),
                    "zone_low":     min(anchor["open"], anchor["close"]),
                    "valid_from":   str(valid_from),
                    "valid_to":     None,  # ADR-005 / TD-079: D/W OB expire only on price-breach
                    "source_bar_date": str(anchor["week_end"]),
                    "status":       "ACTIVE",
                })

        # TD-070: 8-week unbreached-anchor lookback for BEAR_OB (symmetric).
        # Find most recent bullish week in i-1 .. max(0, i-8) that is unbreached
        # by intervening weeks (no intervening high > anchor body_high).
        if curr_move <= -OB_MIN_MOVE_PCT:
            anchor = _find_unbreached_anchor(weekly_bars, i, direction="BEAR")
            if anchor is not None:
                zones.append({
                    "symbol":       symbol,
                    "timeframe":    "W",
                    "pattern_type": "BEAR_OB",
                    "direction":    -1,
                    "zone_high":    max(anchor["open"], anchor["close"]),
                    "zone_low":     min(anchor["open"], anchor["close"]),
                    "valid_from":   str(valid_from),
                    "valid_to":     None,  # ADR-005 / TD-079: D/W OB expire only on price-breach
                    "source_bar_date": str(anchor["week_end"]),
                    "status":       "ACTIVE",
                })

        # ── Weekly FVG ────────────────────────────────────────────────
        if i >= 2:
            two_prev = weekly_bars[i - 2]
            ref = curr["open"]

            # === BULL_FVG: gap-up imbalance (existing) ===
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
                        "valid_to":     None,  # ADR-005 / TD-079: D/W FVG expire only on price-breach
                        "source_bar_date": str(src_date),
                        "status":       "ACTIVE",
                    })

            # === S1.a FIX: BEAR_FVG ===
            # 3-bar structure: two_prev low > curr high, with curr displacing down.
            # The FVG is the gap between curr high and two_prev low.
            if two_prev["low"] > curr["high"]:
                gap_pct = (two_prev["low"] - curr["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "W",
                        "pattern_type": "BEAR_FVG",
                        "direction":    -1,
                        "zone_high":    two_prev["low"],
                        "zone_low":     curr["high"],
                        "valid_from":   str(valid_from),
                        "valid_to":     None,  # ADR-005 / TD-079: D/W FVG expire only on price-breach
                        "source_bar_date": str(src_date),
                        "status":       "ACTIVE",
                    })

    # TD-070 v2 (Session 21): dedup by upsert conflict key. Multiple impulse
    # weeks finding the same unbreached anchor produce duplicate OB rows
    # that crash the batched upsert (Postgres 21000). See helper docstring.
    zones = _dedup_zones_by_conflict_key(zones)

    return zones


# ── Daily zone detection ─────────────────────────────────────────────────────

def detect_daily_zones(daily_ohlcv, symbol, target_date):
    """
    Detect daily-level ICT zones for the upcoming session (target_date).
    Looks at the prior trading day for PDH/PDL/OB; needs 3 prior days for
    D-FVG (S1.b).
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
    # NOTE: D-OB definition uses the prior bar itself as the OB (non-standard
    # ICT). Flagged S2.a during code review; intentionally NOT changed in
    # this patch. Tracked separately as TD candidate.
    prior_move = pct(prior["open"], prior["close"])

    if prior_move >= OB_MIN_MOVE_PCT:
        zones.append({
            "symbol":       symbol,
            "timeframe":    "D",
            "pattern_type": "BULL_OB",
            "direction":    +1,
            "zone_high":    max(prior["open"], prior["close"]),
            "zone_low":     min(prior["open"], prior["close"]),
            "valid_from":   valid_from,
            "valid_to":     None,  # ADR-005 / TD-079: D/W OB expire only on price-breach
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
            "valid_to":     None,  # ADR-005 / TD-079: D/W OB expire only on price-breach
            "source_bar_date": src_date,
            "status":       "ACTIVE",
        })

    # === S1.b FIX: D-FVG detection (new, both directions) ============
    # Need 3 consecutive prior daily candles (K, K+1, K+2). Same convention
    # as historical patch:
    #   K   = oldest of the 3 (prior_dates[-3])
    #   K+1 = displacement bar (prior_dates[-2])
    #   K+2 = newest prior     (prior_dates[-1])
    # source_bar_date is K+1 (the bar that created the imbalance).
    # D-FVG zones get a longer validity window than D-OB (5 days vs 1).
    if len(prior_dates) >= 3:
        k_str   = prior_dates[-3]
        k1_str  = prior_dates[-2]
        k2_str  = prior_dates[-1]
        k       = daily_ohlcv[k_str]
        k1      = daily_ohlcv[k1_str]
        k2      = daily_ohlcv[k2_str]
        ref     = k1["open"]

        d_fvg_valid_to = str(target_date + timedelta(days=D_FVG_VALID_DAYS))

        # BULL_FVG (D): gap-up imbalance.
        if k["high"] < k2["low"]:
            gap_pct = (k2["low"] - k["high"]) / ref * 100
            if gap_pct >= FVG_D_MIN_PCT:
                zones.append({
                    "symbol":       symbol,
                    "timeframe":    "D",
                    "pattern_type": "BULL_FVG",
                    "direction":    +1,
                    "zone_high":    k2["low"],
                    "zone_low":     k["high"],
                    "valid_from":   valid_from,
                    "valid_to":     None,  # ADR-005 / TD-079: D/W FVG expire only on price-breach
                    "source_bar_date": k1_str,
                    "status":       "ACTIVE",
                })

        # BEAR_FVG (D): gap-down imbalance.
        if k["low"] > k2["high"]:
            gap_pct = (k["low"] - k2["high"]) / ref * 100
            if gap_pct >= FVG_D_MIN_PCT:
                zones.append({
                    "symbol":       symbol,
                    "timeframe":    "D",
                    "pattern_type": "BEAR_FVG",
                    "direction":    -1,
                    "zone_high":    k["low"],
                    "zone_low":     k2["high"],
                    "valid_from":   valid_from,
                    "valid_to":     None,  # ADR-005 / TD-079: D/W FVG expire only on price-breach
                    "source_bar_date": k1_str,
                    "status":       "ACTIVE",
                })

    return zones


# ── DB write ──────────────────────────────────────────────────────────────────


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


def recheck_breached_zones(sb, symbol, daily_ohlcv, as_of, dry_run=False):
    """
    TD-030 fix (Session 11): mark ACTIVE zones BREACHED when current spot
    has passed through their price level.

    Previously, only expire_old_zones() cleaned up stale zones (by valid_to
    date). Zones mitigated mid-session stayed ACTIVE indefinitely, so
    detect_ict_patterns_runner.py queried them as valid even after spot had
    already traded through them.

    Breach logic mirrors filter_breached_zones():
      BULL_OB / BULL_FVG / PDL: valid if current_spot > zone_high.
        BREACHED if current_spot <= zone_high (price inside or below zone).
      BEAR_OB / BEAR_FVG / PDH: valid if current_spot < zone_low.
        BREACHED if current_spot >= zone_low (price inside or above zone).
    """
    sorted_dates = sorted(k for k in daily_ohlcv.keys() if k <= as_of)
    if not sorted_dates:
        log(f"  TD-030: no OHLCV for {symbol} as_of {as_of} -- skipping breach recheck")
        return

    current_spot = daily_ohlcv[sorted_dates[-1]]["close"]
    log(f"  Rechecking breached zones for {symbol} @ spot {current_spot:,.1f}")

    if dry_run:
        log(f"  DRY RUN -- would mark BREACHED where spot passed through zone")
        return

    try:
        # BULL_OB / BULL_FVG / PDL: BREACHED if zone_high >= current_spot
        # (current_spot <= zone_high means price is at or below the zone)
        for pattern in ("BULL_OB", "BULL_FVG", "PDL"):
            sb.table("ict_htf_zones").update({
                "status": "BREACHED",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("symbol", symbol).eq("status", "ACTIVE").eq(
                "pattern_type", pattern
            ).gte("zone_high", float(current_spot)).execute()

        # BEAR_OB / BEAR_FVG / PDH: BREACHED if zone_low <= current_spot
        # (current_spot >= zone_low means price is at or above the zone)
        for pattern in ("BEAR_OB", "BEAR_FVG", "PDH"):
            sb.table("ict_htf_zones").update({
                "status": "BREACHED",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("symbol", symbol).eq("status", "ACTIVE").eq(
                "pattern_type", pattern
            ).lte("zone_low", float(current_spot)).execute()

        log(f"  TD-030: breach recheck done for {symbol}")
    except Exception as e:
        log(f"  Warning: could not recheck breached zones for {symbol}: {e}")


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


# ── Expire old zones ────────────────────────────────────────────────────────

def expire_old_zones(sb, symbol, today, dry_run=False):
    """
    Mark W and D zones with valid_to < today as EXPIRED.

    TD-071 (Session 21, 2026-05-06):
      - Widened from ACTIVE-only to status-agnostic. BREACHED zones past
        valid_to now correctly transition to EXPIRED instead of staying
        BREACHED forever (date is the semantic check, not status).
      - Restricted to W and D timeframes. H (intraday) zones use 1-day
        validity (valid_to = trade_date); their expiry basis is unclear
        and intentionally not handled here. See TD-050.
      - Added .neq("status", "EXPIRED") idempotency guard so rerunning
        does not bump updated_at on already-expired rows.
    """
    if dry_run:
        log("  DRY RUN — would expire old W/D zones (status-agnostic)")
        return

    try:
        sb.table("ict_htf_zones").update({
            "status": "EXPIRED",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("symbol", symbol).lt(
            "valid_to", str(today)
        ).in_(
            "timeframe", ["W", "D", "H"]
        ).neq(
            "status", "EXPIRED"
        ).execute()
        log(f"  Expired old W/D/H {symbol} zones before {today}")
    except Exception as e:
        log(f"  Warning: could not expire old zones: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

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

    # ENH-71 instrumentation (added Session 11, F3 / TD-017 close)
    log_exec = ExecutionLog(
        script_name="build_ict_htf_zones.py",
        expected_writes={} if args.dry_run else {"ict_htf_zones": 1},
        symbol=None,
        dry_run=args.dry_run,
        notes=f"timeframe={args.timeframe} date={args.date}",
    )

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
            log_exec.record_write("ict_htf_zones", n)
            log(f"  Written {n} 1H zones")
            total_written += n
            continue

        # TD-071 (Session 21): expire_old_zones moved to AFTER recheck.
        # Old order (expire-first) operated on stale data, leaving
        # BREACHED zones past valid_to permanently BREACHED. New order
        # is detect -> upsert(ACTIVE) -> recheck(price-breach) -> expire(date).

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
            # TD-031 fix: OB/FVG written unconditionally -- fresh structure
            # regardless of overnight recovery. PDH/PDL still proximity-filtered.
            _w_ob  = [z for z in w_zones if z["pattern_type"] not in ("PDH", "PDL")]
            _w_pdl = filter_breached_zones(
                [z for z in w_zones if z["pattern_type"] in ("PDH", "PDL")],
                daily_ohlcv, str(target_date)
            )
            w_zones = _w_ob + _w_pdl
            log(f"  Detected {len(w_zones)} weekly zones ({len(_w_ob)} OB/FVG + {len(_w_pdl)} PDH/PDL)")
            n = upsert_zones(sb, w_zones, dry_run)
            log_exec.record_write("ict_htf_zones", n)
            log(f"  Written {n} weekly zones")
            total_written += n

        if do_daily:
            log("  Building daily zones...")
            d_zones = detect_daily_zones(daily_ohlcv, symbol, target_date)
            # TD-031 fix: same as weekly -- OB/FVG unconditional.
            _d_ob  = [z for z in d_zones if z["pattern_type"] not in ("PDH", "PDL")]
            _d_pdl = filter_breached_zones(
                [z for z in d_zones if z["pattern_type"] in ("PDH", "PDL")],
                daily_ohlcv, str(target_date)
            )
            d_zones = _d_ob + _d_pdl
            log(f"  Detected {len(d_zones)} daily zones ({len(_d_ob)} OB/FVG + {len(_d_pdl)} PDH/PDL)")
            n = upsert_zones(sb, d_zones, dry_run)
            log_exec.record_write("ict_htf_zones", n)
            log(f"  Written {n} daily zones")
            total_written += n

        # TD-030 fix (reordered): recheck AFTER upserts so status=ACTIVE
        # upsert does not overwrite BREACHED set by recheck.
        recheck_breached_zones(sb, symbol, daily_ohlcv, str(target_date), dry_run)

        # TD-071 (Session 21): expire-by-date runs LAST, against ALL zones
        # (both ACTIVE and BREACHED). Restricted to W/D timeframes.
        expire_old_zones(sb, symbol, target_date, dry_run)

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

    # ENH-71 instrumentation (added Session 11, F3 / TD-017 close)
    raise SystemExit(log_exec.complete(notes=f"{total_written} zones written"))




# ── 1H Zone Detection ────────────────────────────────────────────────────────
# Added for ENH-37 — 1H zones provide MEDIUM context for intraday signals
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
    Only processes completed hours — current incomplete hour excluded.

    Returns list of zone dicts for ict_htf_zones upsert.

    SESSION 15 PATCH: added BEAR_FVG branch (mirror of existing BULL_FVG).
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
                "valid_to":     str(trade_date + timedelta(days=7)),  # ADR-005 / TD-079: 1H OB 1-week tactical fallback
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
                "valid_to":     str(trade_date + timedelta(days=7)),  # ADR-005 / TD-079: 1H OB 1-week tactical fallback
                "source_bar_date": src_date,
                "status":       "ACTIVE",
            })

        # 1H FVG: gap detection between prev-prev and curr (both directions)
        if i >= 2:
            two_prev = completed[i - 2]
            ref = curr["open"]

            # 1H BULL_FVG (existing): gap-up imbalance
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
                        "valid_to":     str(trade_date + timedelta(days=7)),  # ADR-005 / TD-079: 1H FVG 1-week tactical fallback
                        "source_bar_date": src_date,
                        "status":       "ACTIVE",
                    })

            # === SESSION 15 PATCH: 1H BEAR_FVG (gap-down imbalance) ===
            # 3-bar structure: two_prev low > curr high, with curr displacing down.
            if two_prev["low"] > curr["high"]:
                gap_pct = (two_prev["low"] - curr["high"]) / ref * 100
                if gap_pct >= FVG_MIN_PCT:
                    zones.append({
                        "symbol":       symbol,
                        "timeframe":    "H",
                        "pattern_type": "BEAR_FVG",
                        "direction":    -1,
                        "zone_high":    two_prev["low"],
                        "zone_low":     curr["high"],
                        "valid_from":   valid_from,
                        "valid_to":     str(trade_date + timedelta(days=7)),  # ADR-005 / TD-079: 1H FVG 1-week tactical fallback
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

# OI-27 fix (2026-04-21): __main__ guard moved from mid-file to end.
# Previously the guard ran main() before detect_1h_zones / aggregate_to_hourly
# were defined (they appear below the original guard position), causing
# `python build_ict_htf_zones.py --timeframe H` to fail with NameError.
# Moving to end ensures all module-scope functions are defined before
# main() executes. Import path via `from build_ict_htf_zones import ...`
# was unaffected since imports don't trigger __main__ block.
if __name__ == "__main__":
    main()
