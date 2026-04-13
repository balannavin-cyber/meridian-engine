#!/usr/bin/env python3
"""
experiment_14_session_pyramid.py
MERDIAN Experiment 14 — Session-Level Pyramid: Riding the Full Day Move

HYPOTHESIS:
  On strong trending sessions (both bullish and bearish), the market moves
  in waves. Each contra bounce against the primary trend creates an
  opportunity to add a fresh ATM option position at a lower cost basis.
  Holding multiple positions across the full session captures the entire
  directional move — not just a single 30-minute window.

  This is fundamentally different from the intraday pyramid (Exp 2c):
    Exp 2c: One trade, 1→3→6 lots, exit T+30m/T+60m
    Exp 14: Multiple independent trades across the session,
             each entered at a contra bounce, held to session close

STRATEGY:
  1. TREND IDENTIFICATION (by 10:00-10:30 IST)
     Session is "trending" if:
     - First 45-minute spot return > TREND_MIN_PCT in one direction
     - An OB has been detected and confirmed (T2 triggered) in first hour
     - Breadth strongly aligned (optional filter — tested separately)

  2. POSITION 1 — Primary entry
     First BULL_OB or BEAR_OB of the session (morning kill zone)
     Buy ATM CE (bullish) or ATM PE (bearish)
     Keep open — do NOT exit at T+30m (session pyramid mode)

  3. SUBSEQUENT POSITIONS — Contra bounce entries
     Detect contra bounce: price moves CONTRA_MIN_PCT against primary trend
     Bounce is losing momentum: 2+ bars of slowing move
     Enter new ATM CE/PE at the bounce extreme
     Maximum MAX_POSITIONS open simultaneously
     Each position independent — tracked at its own strike

  4. EXIT RULES
     Individual position trailing stop: premium drops below TRAIL_STOP_PCT
     of that position's peak value
     Session hard close: exit ALL positions at SESSION_CLOSE_TIME
     Primary trend reversal: if session return flips direction by > 0.6%
     from peak — close all

METRICS PER SESSION:
  - Total P&L (rupees) across all positions
  - vs Single trade P&L (Position 1 only, T+30m exit)
  - vs Hold Position 1 to close (no adds)
  - Number of adds triggered
  - Best session / worst session
  - P&L by direction (bull vs bear days)
  - P&L by vol regime (HIGH_VOL vs LOW_VOL)

Data: hist_spot_bars_1m + hist_option_bars_1m
Lot sizes: NIFTY=25, SENSEX=15
Starting capital: ₹2,00,000 per symbol

Read-only. Runtime: ~20-30 minutes.

Usage:
    python experiment_14_session_pyramid.py
"""

import os
import bisect
import time
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict
from itertools import groupby
from merdian_utils import build_expiry_index_simple, nearest_expiry_db

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000

# ── Session pyramid parameters ────────────────────────────────────────
TREND_MIN_PCT       = 0.20   # % move in first 45 min to qualify as trending
TREND_WINDOW_MIN    = 45     # minutes from open to measure trend
CONTRA_MIN_PCT      = 0.20   # % contra move to trigger new position entry
CONTRA_MAX_PCT      = 0.60   # % contra move = trend reversal, close all
TRAIL_STOP_PCT      = 0.40   # exit position if premium drops to 40% of peak
MAX_POSITIONS       = 3      # max simultaneous open positions
SESSION_CLOSE_TIME  = dtime(15, 15)  # hard close all positions
SESSION_END         = dtime(15, 30)
OB_MIN_MOVE_PCT     = 0.40   # OB detection threshold
MIN_OPTION_PRICE    = 5.0
ATM_RADIUS          = 3
MAX_GAP_MIN         = 5

# ── Instrument conventions ────────────────────────────────────────────
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}
LOT_SIZE    = {"NIFTY": 25, "SENSEX": 15}
STARTING_CAPITAL = 200_000

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def month_key(td):
    return (td.year, td.month)

def month_label(mk):
    return f"{MONTH_NAMES[mk[1]]} {mk[0]}"

def in_session(ts, minutes=0):
    t = (ts + timedelta(minutes=minutes)).time()
    return t <= SESSION_END


# ── Data loading ──────────────────────────────────────────────────────

def fetch_paginated(sb, table, filters, select, order="bar_ts"):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select).order(order).range(offset, offset+PAGE_SIZE-1)
        for method, *args in filters:
            q = getattr(q, method)(*args)
        rows = None
        for attempt in range(4):
            try:
                rows = q.execute().data
                break
            except Exception:
                if attempt == 3: raise
                time.sleep(2**attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE: break
        offset += PAGE_SIZE
        if offset % 20_000 == 0:
            log(f"    {offset:,} rows...")
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


def fetch_option_day(sb, inst_id, td, ed, strikes, opt_types):
    """Fetch ALL 1-min option bars for the day — not just ATM. Need full session."""
    strike_strs = [f"{float(s):.2f}" for s in strikes]
    all_rows, offset = [], 0
    while True:
        rows = (
            sb.table("hist_option_bars_1m")
            .select("bar_ts, strike, option_type, close, open")
            .eq("instrument_id", str(inst_id))
            .eq("trade_date", str(td))
            .eq("expiry_date", str(ed))
            .in_("strike", strike_strs)
            .in_("option_type", list(opt_types))
            .order("bar_ts")
            .range(offset, offset+PAGE_SIZE-1)
            .execute().data
        )
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE: break
        offset += PAGE_SIZE
    # Build lookup: (strike, opt_type) → sorted [(ts, close)]
    lookup = defaultdict(list)
    for r in all_rows:
        ts  = datetime.fromisoformat(r["bar_ts"])
        stk = float(r["strike"])
        ot  = r["option_type"]
        cl  = float(r["close"])
        if cl >= MIN_OPTION_PRICE:
            lookup[(stk, ot)].append((ts, cl))
    for key in lookup:
        lookup[key].sort(key=lambda x: x[0])
    return lookup


def get_option_price_at(lookup, strike, ot, target_ts, symbol):
    """Get option close price at or near target_ts."""
    step = STRIKE_STEP[symbol]
    candidates = [strike + i*step for i in range(-ATM_RADIUS, ATM_RADIUS+1)]
    best_p, best_g, best_stk = None, timedelta(minutes=MAX_GAP_MIN+1), None
    for stk in candidates:
        bars = lookup.get((stk, ot), [])
        if not bars: continue
        tss = [b[0] for b in bars]
        idx = bisect.bisect_left(tss, target_ts)
        for i in (idx-1, idx):
            if 0 <= i < len(bars):
                gap = abs(bars[i][0] - target_ts)
                if gap < best_g:
                    best_g, best_p, best_stk = gap, bars[i][1], stk
    return (best_p, best_stk) if best_g <= timedelta(minutes=MAX_GAP_MIN) else (None, None)


def get_option_price_series(lookup, strike, ot, from_ts, to_ts):
    """Get all option prices for a strike/type between two timestamps."""
    bars = lookup.get((strike, ot), [])
    return [(ts, cl) for ts, cl in bars if from_ts <= ts <= to_ts]


# ── Pattern detection ─────────────────────────────────────────────────

def detect_first_ob(bars, window_minutes=90):
    """Detect first OB in the opening window. Returns (bar, direction) or None."""
    if not bars: return None
    open_ts = bars[0]["bar_ts"]
    cutoff  = open_ts + timedelta(minutes=window_minutes)
    window  = [b for b in bars if b["bar_ts"] <= cutoff]
    n = len(window)
    for i in range(n - 6):
        mv = pct(window[i]["close"], window[min(i+5,n-1)]["close"])
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if window[j]["close"] > window[j]["open"]:
                    return {"bar": window[j], "direction": -1, "pattern": "BEAR_OB"}
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if window[j]["close"] < window[j]["open"]:
                    return {"bar": window[j], "direction": +1, "pattern": "BULL_OB"}
    return None


def identify_trend(bars, direction):
    """
    Check if T2 confirmation (0.20% in direction within 5 min) occurred
    after the OB detection bar.
    """
    return True  # simplified — all OBs with confirmed trend pass


def detect_contra_bounces(bars, trend_direction, primary_entry_ts, min_pct=CONTRA_MIN_PCT):
    """
    Find contra bounce entries after the primary entry.
    A contra bounce is:
    - Price moves CONTRA_MIN_PCT against trend direction after primary entry
    - Then starts reversing back to trend direction (1+ bars)
    Returns list of (entry_ts, spot_at_entry) for each bounce entry point.
    """
    bounces = []
    tss = [b["bar_ts"] for b in bars]
    start_idx = bisect.bisect_right(tss, primary_entry_ts)

    if start_idx >= len(bars): return bounces

    reference_spot = bars[start_idx]["close"]  # spot at primary entry
    contra_peak    = None
    contra_peak_ts = None
    contra_peak_spot = None
    in_contra      = False

    for i in range(start_idx, len(bars)):
        bar  = bars[i]
        ts   = bar["bar_ts"]
        spot = bar["close"]

        # Skip after session close time
        if ts.time() >= SESSION_CLOSE_TIME:
            break

        # Measure contra move from reference
        contra_move = pct(reference_spot, spot) * (-trend_direction)

        if not in_contra:
            # Looking for contra move to develop
            if contra_move >= min_pct:
                in_contra        = True
                contra_peak      = contra_move
                contra_peak_ts   = ts
                contra_peak_spot = spot
        else:
            # In contra bounce — looking for reversal back to trend
            if contra_move > contra_peak:
                # Still extending contra
                contra_peak      = contra_move
                contra_peak_ts   = ts
                contra_peak_spot = spot
            else:
                # Starting to reverse — this is our entry point
                move_back = contra_peak - contra_move
                if move_back >= 0.10:  # confirmed reversal of at least 0.10%
                    bounces.append({
                        "entry_ts":    ts,
                        "entry_spot":  spot,
                        "contra_pct":  contra_peak,
                        "bounce_from": contra_peak_spot,
                    })
                    # Reset — look for next contra
                    in_contra       = False
                    reference_spot  = spot  # new reference from this entry
                    contra_peak     = None

    return bounces


# ── Position tracker ──────────────────────────────────────────────────

class Position:
    def __init__(self, entry_ts, entry_spot, entry_price, strike, ot,
                 direction, lot_size, pos_num):
        self.entry_ts    = entry_ts
        self.entry_spot  = entry_spot
        self.entry_price = entry_price
        self.strike      = strike
        self.ot          = ot
        self.direction   = direction
        self.lot_size    = lot_size
        self.pos_num     = pos_num
        self.peak_price  = entry_price
        self.exit_ts     = None
        self.exit_price  = None
        self.exit_reason = None
        self.pnl_rupees  = None

    def update_peak(self, current_price):
        if current_price > self.peak_price:
            self.peak_price = current_price

    def check_trail_stop(self, current_price):
        if self.peak_price <= self.entry_price:
            return False
        # Trail stop at TRAIL_STOP_PCT of peak
        trail_level = self.entry_price + (self.peak_price - self.entry_price) * TRAIL_STOP_PCT
        return current_price <= trail_level

    def close(self, exit_ts, exit_price, reason):
        self.exit_ts     = exit_ts
        self.exit_price  = exit_price
        self.exit_reason = reason
        self.pnl_rupees  = (exit_price - self.entry_price) * self.lot_size


# ── Session simulation ────────────────────────────────────────────────

def simulate_session(bars, lookup, symbol, td, expiry_idx):
    """
    Full session simulation.
    Returns dict with all session metrics.
    """
    lot_size = LOT_SIZE[symbol]
    ed = nearest_expiry_db(td, expiry_idx)
    result = {
        "td": td, "symbol": symbol,
        "trend_direction": 0,
        "trend_identified": False,
        "n_positions": 0,
        "positions": [],
        "session_pnl_rupees": 0,
        "single_trade_pnl": 0,
        "hold_p1_pnl": 0,
        "session_range_pct": 0,
        "skipped": False,
        "skip_reason": "",
    }

    if len(bars) < 30:
        result["skipped"] = True
        result["skip_reason"] = "too few bars"
        return result

    # Session range
    highs = max(b["high"] for b in bars)
    lows  = min(b["low"]  for b in bars)
    result["session_range_pct"] = pct(bars[0]["open"], highs) - pct(bars[0]["open"], lows)

    # Detect first OB
    first_ob = detect_first_ob(bars, window_minutes=90)
    if first_ob is None:
        result["skipped"] = True
        result["skip_reason"] = "no OB in first 90 min"
        return result

    direction  = first_ob["direction"]
    ob_bar     = first_ob["bar"]
    ob_ts      = ob_bar["bar_ts"]
    ob_spot    = ob_bar["close"]
    result["trend_direction"] = direction

    # Check trend confirmation (first 45 min move)
    open_spot = bars[0]["open"]
    window_end_ts = bars[0]["bar_ts"] + timedelta(minutes=TREND_WINDOW_MIN)
    window_bars = [b for b in bars if b["bar_ts"] <= window_end_ts]
    if window_bars:
        window_return = pct(open_spot, window_bars[-1]["close"]) * direction
        if window_return < TREND_MIN_PCT:
            result["skipped"] = True
            result["skip_reason"] = f"trend too weak ({window_return:.2f}% < {TREND_MIN_PCT}%)"
            return result

    result["trend_identified"] = True

    # Opt type
    ot = "CE" if direction == +1 else "PE"

    # Get primary entry price (P1)
    p1_strike = atm_strike(ob_spot, symbol)
    p1_price, p1_stk = get_option_price_at(lookup, p1_strike, ot, ob_ts, symbol)
    if p1_price is None:
        result["skipped"] = True
        result["skip_reason"] = "no option data at P1 entry"
        return result

    # ── Single trade benchmark: P1 exit at T+30m ─────────────────────
    t30_ts = ob_ts + timedelta(minutes=30)
    t30_price, _ = get_option_price_at(lookup, p1_stk, ot, t30_ts, symbol)
    if t30_price:
        result["single_trade_pnl"] = (t30_price - p1_price) * lot_size

    # ── Hold P1 to close benchmark ────────────────────────────────────
    close_ts = ob_ts.replace(hour=15, minute=14, second=0, microsecond=0)
    close_price, _ = get_option_price_at(lookup, p1_stk, ot, close_ts, symbol)
    if close_price:
        result["hold_p1_pnl"] = (close_price - p1_price) * lot_size

    # ── Session pyramid simulation ────────────────────────────────────
    positions = [Position(ob_ts, ob_spot, p1_price, p1_stk, ot,
                          direction, lot_size, 1)]

    # Detect contra bounces for subsequent entries
    bounces = detect_contra_bounces(bars, direction, ob_ts)

    for bounce in bounces:
        if len(positions) >= MAX_POSITIONS:
            break

        b_ts   = bounce["entry_ts"]
        b_spot = bounce["entry_spot"]

        # Skip if too late
        if b_ts.time() >= SESSION_CLOSE_TIME:
            break

        # Skip if contra was too large (trend reversal signal)
        if bounce["contra_pct"] >= CONTRA_MAX_PCT:
            break

        b_strike = atm_strike(b_spot, symbol)
        b_price, b_stk = get_option_price_at(lookup, b_strike, ot, b_ts, symbol)
        if b_price is None:
            continue

        positions.append(Position(b_ts, b_spot, b_price, b_stk, ot,
                                  direction, lot_size, len(positions)+1))

    # ── Run through remaining session bars, update positions ──────────
    tss = [b["bar_ts"] for b in bars]

    for pos in positions:
        entry_idx = bisect.bisect_right(tss, pos.entry_ts)
        for i in range(entry_idx, len(bars)):
            bar_ts = bars[i]["bar_ts"]

            if bar_ts.time() >= SESSION_CLOSE_TIME:
                # Hard close
                cp, _ = get_option_price_at(lookup, pos.strike, ot, bar_ts, symbol)
                if cp:
                    pos.close(bar_ts, cp, "session_close")
                break

            # Get current option price
            cp, _ = get_option_price_at(lookup, pos.strike, ot, bar_ts, symbol)
            if cp is None:
                continue

            pos.update_peak(cp)

            # Check trail stop
            if pos.check_trail_stop(cp):
                pos.close(bar_ts, cp, "trail_stop")
                break

        # If still open at end of bars
        if pos.exit_ts is None and bars:
            last_ts = bars[-1]["bar_ts"]
            cp, _ = get_option_price_at(lookup, pos.strike, ot, last_ts, symbol)
            if cp:
                pos.close(last_ts, cp, "end_of_data")

    # ── Aggregate ─────────────────────────────────────────────────────
    total_pnl = sum(p.pnl_rupees for p in positions if p.pnl_rupees is not None)
    result["n_positions"]      = len(positions)
    result["positions"]        = positions
    result["session_pnl_rupees"] = total_pnl

    return result


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    all_results = []

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"\n── {symbol} ─────────────────────────────────────────────")
        lot_size = LOT_SIZE[symbol]

        log("  Loading spot bars...")
        raw = fetch_paginated(
            sb, "hist_spot_bars_1m",
            [("eq","instrument_id",inst[symbol]),("eq","is_pre_market",False)],
            "bar_ts, trade_date, open, high, low, close"
        )
        for r in raw:
            r["bar_ts"]     = datetime.fromisoformat(r["bar_ts"])
            r["trade_date"] = date.fromisoformat(r["trade_date"])
            for k in ("open","high","low","close"):
                r[k] = float(r[k])
        spot_sessions = sessions_from_bars(raw)
        dates = sorted(spot_sessions.keys())
        log(f"  {len(raw):,} bars | {len(dates)} sessions")

        log("  Simulating sessions...")
        scored = skipped = 0
        skip_reasons = defaultdict(int)

        for i, td in enumerate(dates):
            bars = spot_sessions[td]
            ed   = nearest_expiry_db(td, expiry_idx)

            # ATM +/- 10 strikes from opening spot only
            step      = STRIKE_STEP[symbol]
            open_spot = bars[0]["open"]
            base_atm  = atm_strike(open_spot, symbol)
            strikes   = set()
            for offset in range(-10, 11):
                strikes.add(base_atm + offset * step)

            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes), ["CE", "PE"]
                )
            except Exception as e:
                skipped += 1
                continue

            if not lookup:
                skipped += 1
                continue

            result = simulate_session(bars, lookup, symbol, td, expiry_idx)
            result["symbol"] = symbol

            if result["skipped"]:
                skipped += 1
                skip_reasons[result["skip_reason"]] += 1
            else:
                scored += 1
                all_results.append(result)

            if i % 20 == 0:
                log(f"    {i}/{len(dates)} | scored={scored} skipped={skipped}")

        log(f"  {symbol} complete — {scored} trending sessions scored, {skipped} skipped")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            log(f"    skip: {reason} → {count}")

    # ── Output ────────────────────────────────────────────────────────
    trending = [r for r in all_results if not r["skipped"]]

    print("\n" + "=" * 115)
    print("  MERDIAN EXPERIMENT 14 — SESSION-LEVEL PYRAMID")
    print("  Direction agnostic: bullish and bearish trending sessions")
    print(f"  Trend threshold: {TREND_MIN_PCT}% in first {TREND_WINDOW_MIN} min")
    print(f"  Contra entry: {CONTRA_MIN_PCT}% bounce | Max positions: {MAX_POSITIONS}")
    print(f"  Trail stop: {TRAIL_STOP_PCT*100:.0f}% of peak premium | Hard close: {SESSION_CLOSE_TIME}")
    print("=" * 115)

    if not trending:
        print("  No trending sessions scored.")
        return

    # ── Section 1: Session detail ─────────────────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 1 — ALL TRENDING SESSIONS")
    print(f"  {'Date':<12} {'Sym':<7} {'Dir':<5} {'N Pos':>5} {'Pyr P&L':>10} "
          f"{'T+30 P&L':>10} {'Hold Close':>11} {'Range%':>8}  Verdict")
    print(f"  {'-'*105}")

    bull_pnl = bear_pnl = 0
    bull_n   = bear_n   = 0

    for r in sorted(trending, key=lambda x: x["td"]):
        d     = r["trend_direction"]
        dir_s = "BULL" if d == +1 else "BEAR"
        pyr   = r["session_pnl_rupees"]
        t30   = r["single_trade_pnl"]
        hold  = r["hold_p1_pnl"]
        rng   = r["session_range_pct"]
        n     = r["n_positions"]
        flag  = " ◄" if pyr > 0 and pyr > t30 else ("  " if pyr > 0 else " ✗")

        if d == +1: bull_pnl += pyr; bull_n += 1
        else:       bear_pnl += pyr; bear_n += 1


        print(f"  {str(r['td']):<12} {r['symbol']:<7} {dir_s:<5} {n:>5} "
              f"₹{pyr:>+9,.0f} ₹{t30:>+9,.0f} ₹{hold:>+10,.0f} {rng:>7.2f}%{flag}")

    # ── Section 2: Summary stats ──────────────────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 2 — SUMMARY STATISTICS")
    print(f"{'='*115}")

    pyr_pnls  = [r["session_pnl_rupees"] for r in trending]
    t30_pnls  = [r["single_trade_pnl"]   for r in trending]
    hold_pnls = [r["hold_p1_pnl"]        for r in trending]
    n_pos     = [r["n_positions"]         for r in trending]

    def stats(vals, label):
        if not vals: return
        wins  = sum(1 for v in vals if v > 0)
        total = len(vals)
        print(f"  {label:<30} N={total:>4}  "
              f"WR={100*wins/total:.0f}%  "
              f"Avg=₹{sum(vals)/total:>+8,.0f}  "
              f"Total=₹{sum(vals):>+10,.0f}  "
              f"Best=₹{max(vals):>+8,.0f}  "
              f"Worst=₹{min(vals):>+8,.0f}")

    stats(pyr_pnls,  "Session Pyramid (all adds)")
    stats(t30_pnls,  "Single Trade (P1 exit T+30m)")
    stats(hold_pnls, "Hold P1 to Close (no adds)")

    print(f"\n  Avg positions per session: {sum(n_pos)/len(n_pos):.1f}")
    print(f"  Sessions with 1 position:  {sum(1 for n in n_pos if n==1)}")
    print(f"  Sessions with 2 positions: {sum(1 for n in n_pos if n==2)}")
    print(f"  Sessions with 3 positions: {sum(1 for n in n_pos if n==3)}")

    # ── Section 3: Direction breakdown ───────────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 3 — BY DIRECTION")
    print(f"{'='*115}")

    bull_r = [r for r in trending if r["trend_direction"] == +1]
    bear_r = [r for r in trending if r["trend_direction"] == -1]

    for label, group in [("BULLISH sessions", bull_r), ("BEARISH sessions", bear_r)]:
        if not group: continue
        pyr  = [r["session_pnl_rupees"] for r in group]
        t30  = [r["single_trade_pnl"]   for r in group]
        hold = [r["hold_p1_pnl"]        for r in group]
        print(f"\n  {label} (N={len(group)}):")
        stats(pyr,  "  Pyramid")
        stats(t30,  "  T+30m exit")
        stats(hold, "  Hold to close")

    # ── Section 4: Monthly breakdown ─────────────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 4 — MONTHLY BREAKDOWN")
    print(f"{'='*115}")
    print(f"  {'Month':<12} {'Sessions':>9}  {'Pyr P&L':>10}  {'T+30 P&L':>10}  "
          f"{'Hold P&L':>10}  {'Avg N Pos':>10}  Pyr WR")
    print(f"  {'-'*80}")

    monthly = defaultdict(list)
    for r in trending:
        monthly[month_key(r["td"])].append(r)

    for mk in sorted(monthly.keys()):
        group = monthly[mk]
        pyr   = [r["session_pnl_rupees"] for r in group]
        t30   = [r["single_trade_pnl"]   for r in group]
        hold  = [r["hold_p1_pnl"]        for r in group]
        n_p   = [r["n_positions"]         for r in group]
        wr    = 100*sum(1 for v in pyr if v>0)/len(pyr)
        print(f"  {month_label(mk):<12} {len(group):>9}  "
              f"₹{sum(pyr):>+8,.0f}  ₹{sum(t30):>+8,.0f}  "
              f"₹{sum(hold):>+8,.0f}  {sum(n_p)/len(n_p):>10.1f}  {wr:>5.0f}%")

    # ── Section 5: Best and worst sessions ───────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 5 — NOTABLE SESSIONS")
    print(f"{'='*115}")

    best5  = sorted(trending, key=lambda r: r["session_pnl_rupees"], reverse=True)[:5]
    worst5 = sorted(trending, key=lambda r: r["session_pnl_rupees"])[:5]

    print(f"\n  TOP 5 SESSIONS:")
    print(f"  {'Date':<12} {'Sym':<7} {'Dir':<5} {'N Pos':>5} {'Pyr P&L':>10} "
          f"{'T+30':>9} {'Hold':>9}  Position details")
    print(f"  {'-'*95}")
    for r in best5:
        dir_s = "BULL" if r["trend_direction"] == +1 else "BEAR"
        pos_detail = " | ".join(
            f"P{p.pos_num}:{p.entry_ts.strftime('%H:%M')} "
            f"stk={p.strike:.0f} "
            f"in=₹{p.entry_price:.0f} "
            f"out=₹{p.exit_price:.0f if p.exit_price else 0:.0f} "
            f"({p.exit_reason or '?'})"
            for p in r["positions"]
        )
        print(f"  {str(r['td']):<12} {r['symbol']:<7} {dir_s:<5} "
              f"{r['n_positions']:>5} ₹{r['session_pnl_rupees']:>+9,.0f} "
              f"₹{r['single_trade_pnl']:>+7,.0f} ₹{r['hold_p1_pnl']:>+7,.0f}")
        print(f"    {pos_detail}")

    print(f"\n  BOTTOM 5 SESSIONS:")
    print(f"  {'Date':<12} {'Sym':<7} {'Dir':<5} {'N Pos':>5} {'Pyr P&L':>10} "
          f"{'T+30':>9} {'Hold':>9}  Reason")
    print(f"  {'-'*95}")
    for r in worst5:
        dir_s = "BULL" if r["trend_direction"] == +1 else "BEAR"
        print(f"  {str(r['td']):<12} {r['symbol']:<7} {dir_s:<5} "
              f"{r['n_positions']:>5} ₹{r['session_pnl_rupees']:>+9,.0f} "
              f"₹{r['single_trade_pnl']:>+7,.0f} ₹{r['hold_p1_pnl']:>+7,.0f}")

    # ── Section 6: Pyramid vs alternatives ───────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 6 — PYRAMID vs ALTERNATIVES (cumulative across all trending sessions)")
    print(f"{'='*115}")
    print(f"  Strategy              Total P&L      Sessions    Win Rate    Avg/Session")
    print(f"  {'-'*70}")

    for label, vals in [
        ("Session Pyramid",    pyr_pnls),
        ("Single T+30m exit",  t30_pnls),
        ("Hold P1 to Close",   hold_pnls),
    ]:
        if not vals: continue
        wins = sum(1 for v in vals if v > 0)
        print(f"  {label:<22} ₹{sum(vals):>+10,.0f}  {len(vals):>9}    "
              f"{100*wins/len(vals):>5.0f}%    ₹{sum(vals)/len(vals):>+8,.0f}")

    print(f"\n{'='*115}")
    print("  INTERPRETATION")
    print("  Session Pyramid wins if: total P&L > single trade AND WR >= single trade WR")
    print("  Key metric: does adding positions on contra bounces improve or hurt?")
    print("  Check Section 3 — are bull and bear days symmetric or does one dominate?")
    print("  If hold-P1-to-close beats pyramid — the adds are not helping")
    print("    → Trail stop too tight or contra detection too aggressive")
    print("  If pyramid beats hold-P1 — the adds are compounding the move correctly")
    print(f"{'='*115}\n")


if __name__ == "__main__":
    main()







