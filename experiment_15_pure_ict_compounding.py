#!/usr/bin/env python3
"""
experiment_15_pure_ict_compounding.py
MERDIAN Experiment 15 — Pure ICT Compounding Simulation

Tests the ICT pattern framework in isolation — no MERDIAN regime signals,
no gamma gate, no breadth gate, no VIX gate, no confidence score.

Signal source:   ICT patterns only (BEAR_OB, BULL_OB, BULL_FVG, JUDAS_BULL)
Context:         Simulated W/D/H zones from hist_spot_bars_1m
                 (same logic as build_ict_htf_zones.py — directly comparable
                  to what the live ENH-37 system will see)
Sequence filter: IMP_STR=SKIP, MOM_YES=TIER1, MORNING=TIER1
Exit:            T+30m (empirically validated) vs ICT structure break
Compounding:     Session profits added to deployed capital
                 Losses absorbed — capital stays at reduced level (no floor reset)
Sizing:          TIER1=1.5x base, TIER2=1.0x, SKIP=0x
Starting:        INR 2,00,000 per index (INR 4,00,000 total)

KEY RESEARCH QUESTION:
  Does the 1H zone layer (MEDIUM context) add measurable edge over
  daily zones (HIGH) alone? And how does each MTF context tier
  perform when isolated?

  VERY_HIGH (inside weekly zone): institutionally proven
  HIGH      (inside daily zone):  session-proven, pre-market
  MEDIUM    (inside 1H zone):     nascent, same-session
  LOW       (no zone):            unconfluenced

Output:
  Section 1  — Session-by-session P&L + compounding curve
  Section 2  — Compounding summary (peak, drawdown, recovery)
  Section 3  — By pattern type (BEAR_OB vs BULL_OB vs FVG vs JUDAS)
  Section 4  — By MTF context tier (VERY_HIGH / HIGH / MEDIUM / LOW)
  Section 5  — 1H zone reliability: MEDIUM vs HIGH vs VERY_HIGH edge
  Section 6  — By sequence tier (TIER1 vs TIER2)
  Section 7  — T+30m exit vs ICT structure break exit
  Section 8  — Verdict

Read-only. Runtime: ~4-6 hours.

Usage:
    python experiment_15_pure_ict_compounding.py
"""

import os
import sys
import bisect
import time
from datetime import datetime, date, timedelta, time as dtime
from collections import defaultdict
from itertools import groupby
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client

from detect_ict_patterns import (
    ICTDetector, Bar, HTFZone,
    OB_MIN_MOVE_PCT, FVG_MIN_PCT,
    MORNING_START, MIDDAY_START, POWER_HOUR,
    pct, time_zone_label, iv_size_mult,
    compute_sequence_features, assign_tier, get_mtf_context,
    DIRECTION, OPT_TYPE,
)
from build_ict_htf_zones import (
    build_weekly_bars, detect_weekly_zones, detect_daily_zones,
    aggregate_to_hourly,
)
from merdian_utils import build_expiry_index_simple, nearest_expiry_db

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000

# ── Experiment parameters ─────────────────────────────────────────────
STARTING_CAPITAL   = 200_000   # INR 2L per index
LOT_SIZE           = {"NIFTY": 25, "SENSEX": 15}
STRIKE_STEP        = {"NIFTY": 50, "SENSEX": 100}
ATM_RADIUS         = 3
MIN_OPTION_PRICE   = 5.0
MAX_GAP_MIN        = 5
WEEKLY_LOOKBACK    = 8
DAILY_LOOKBACK     = 5
SESSION_CLOSE      = dtime(15, 15)

# Compounding: profits added to capital, losses absorbed (no floor reset)
# TIER1 = 1.5x base lots, TIER2 = 1.0x, SKIP = 0
TIER_MULT = {"TIER1": 1.5, "TIER2": 1.0, "SKIP": 0.0}

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",
               6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def month_label(d):
    return f"{MONTH_NAMES[d.month]} {d.year}"

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
                if attempt == 3: raise
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


def get_option_price_at(lookup, strike, ot, target_ts, symbol):
    step = STRIKE_STEP[symbol]
    candidates = [strike + i*step for i in range(-ATM_RADIUS, ATM_RADIUS+1)]
    best_p, best_g = None, timedelta(minutes=MAX_GAP_MIN+1)
    for stk in candidates:
        bars = lookup.get((stk, ot), [])
        if not bars:
            continue
        tss = [b[0] for b in bars]
        idx = bisect.bisect_left(tss, target_ts)
        for i in (idx-1, idx):
            if 0 <= i < len(bars):
                gap = abs(bars[i][0] - target_ts)
                if gap < best_g:
                    best_g, best_p = gap, bars[i][1]
    return best_p if best_g <= timedelta(minutes=MAX_GAP_MIN) else None


def fetch_option_day(sb, inst_id, td, ed, strikes, opt_types):
    strike_strs = [f"{float(s):.2f}" for s in strikes]
    all_rows, offset = [], 0
    while True:
        rows = (
            sb.table("hist_option_bars_1m")
            .select("bar_ts, strike, option_type, close")
            .eq("instrument_id", str(inst_id))
            .eq("trade_date", str(td))
            .eq("expiry_date", str(ed))
            .in_("strike", strike_strs)
            .in_("option_type", list(opt_types))
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute().data
        )
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
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


# ── HTF zone simulation ───────────────────────────────────────────────

def build_simulated_htf_zones(daily_ohlcv, intraday_bars_today, symbol, td):
    """
    Simulate W/D/H zones from hist_spot_bars_1m using the same logic
    as build_ict_htf_zones.py. Returns list[HTFZone].

    This makes the experiment directly comparable to live ENH-37 output.
    """
    zones = []

    # ── Weekly zones (from last WEEKLY_LOOKBACK weeks) ────────────────
    weekly_bars = build_weekly_bars(daily_ohlcv)
    weekly_bars = weekly_bars[-WEEKLY_LOOKBACK:]
    w_zone_dicts = detect_weekly_zones(weekly_bars, symbol)
    for z in w_zone_dicts:
        valid_from = date.fromisoformat(z["valid_from"])
        valid_to   = date.fromisoformat(z["valid_to"])
        if valid_from <= td <= valid_to:
            zones.append(HTFZone(
                id=f"W_{z['pattern_type']}_{z['zone_high']:.0f}",
                symbol=symbol,
                timeframe="W",
                pattern_type=z["pattern_type"],
                direction=int(z["direction"]),
                zone_high=float(z["zone_high"]),
                zone_low=float(z["zone_low"]),
                status="ACTIVE",
            ))

    # ── Daily zones (from prior session) ─────────────────────────────
    d_zone_dicts = detect_daily_zones(daily_ohlcv, symbol, td)
    for z in d_zone_dicts:
        zones.append(HTFZone(
            id=f"D_{z['pattern_type']}_{z['zone_high']:.0f}",
            symbol=symbol,
            timeframe="D",
            pattern_type=z["pattern_type"],
            direction=int(z["direction"]),
            zone_high=float(z["zone_high"]),
            zone_low=float(z["zone_low"]),
            status="ACTIVE",
        ))

    # ── 1H zones (from completed hours so far today) ──────────────────
    # Use intraday bars already seen up to detection point
    if intraday_bars_today:
        from datetime import timezone, timedelta as td_delta
        IST = timezone(td_delta(hours=5, minutes=30))

        hourly_raw = aggregate_to_hourly([
            {"bar_ts": b.bar_ts.isoformat(), "open": b.open,
             "high": b.high, "low": b.low, "close": b.close}
            for b in intraday_bars_today
        ])

        n = len(hourly_raw)
        for i in range(1, n):
            curr = hourly_raw[i]
            prev = hourly_raw[i - 1]
            curr_move = pct(curr["open"], curr["close"])
            prev_move = pct(prev["open"], prev["close"])

            if curr_move >= OB_MIN_MOVE_PCT and prev["close"] < prev["open"]:
                zones.append(HTFZone(
                    id=f"H_BULL_OB_{prev['hour_start'].strftime('%H%M')}_{prev['close']:.0f}",
                    symbol=symbol, timeframe="H", pattern_type="BULL_OB",
                    direction=+1,
                    zone_high=max(prev["open"], prev["close"]),
                    zone_low=min(prev["open"], prev["close"]),
                    status="ACTIVE",
                ))
            if curr_move <= -OB_MIN_MOVE_PCT and prev["close"] > prev["open"]:
                zones.append(HTFZone(
                    id=f"H_BEAR_OB_{prev['hour_start'].strftime('%H%M')}_{prev['close']:.0f}",
                    symbol=symbol, timeframe="H", pattern_type="BEAR_OB",
                    direction=-1,
                    zone_high=max(prev["open"], prev["close"]),
                    zone_low=min(prev["open"], prev["close"]),
                    status="ACTIVE",
                ))

            if i >= 2:
                two_prev = hourly_raw[i - 2]
                ref = curr["open"]
                if two_prev["high"] < curr["low"]:
                    gap_pct = (curr["low"] - two_prev["high"]) / ref * 100
                    if gap_pct >= FVG_MIN_PCT:
                        zones.append(HTFZone(
                            id=f"H_BULL_FVG_{curr['hour_start'].strftime('%H%M')}",
                            symbol=symbol, timeframe="H", pattern_type="BULL_FVG",
                            direction=+1,
                            zone_high=curr["low"],
                            zone_low=two_prev["high"],
                            status="ACTIVE",
                        ))

    return zones


# ── ICT structure break exit ──────────────────────────────────────────

def find_structure_break_exit(bars, entry_idx, direction, entry_spot,
                              zone_low, zone_high, lookup, strike, ot, symbol):
    """
    ICT structure break exit:
    BEAR trade: exit when spot closes ABOVE zone high (structure broken)
    BULL trade: exit when spot closes BELOW zone low (structure broken)
    Also exit at SESSION_CLOSE.
    Returns (exit_ts, exit_price, exit_reason)
    """
    tss = [b.bar_ts for b in bars]
    for i in range(entry_idx + 1, len(bars)):
        bar = bars[i]
        if bar.bar_ts.time() >= SESSION_CLOSE:
            cp = get_option_price_at(lookup, strike, ot, bar.bar_ts, symbol)
            return bar.bar_ts, cp, "structure_break_session_close"

        if direction == -1 and bar.close > zone_high:
            cp = get_option_price_at(lookup, strike, ot, bar.bar_ts, symbol)
            return bar.bar_ts, cp, "structure_broken_bear"
        if direction == +1 and bar.close < zone_low:
            cp = get_option_price_at(lookup, strike, ot, bar.bar_ts, symbol)
            return bar.bar_ts, cp, "structure_broken_bull"

    # End of data
    if bars:
        last = bars[-1]
        cp = get_option_price_at(lookup, strike, ot, last.bar_ts, symbol)
        return last.bar_ts, cp, "end_of_data"
    return None, None, "no_exit"


# ── Trade result dataclass ────────────────────────────────────────────

@dataclass
class TradeResult:
    td:           date
    symbol:       str
    pattern_type: str
    direction:    int
    ot:           str
    ict_tier:     str
    mtf_context:  str
    htf_timeframe: str         # W | D | H | NONE
    time_zone:    str
    entry_ts:     datetime
    entry_price:  float
    strike:       float
    entry_spot:   float
    zone_high:    float
    zone_low:     float
    capital_deployed: float
    lots:         int

    # T+30m exit
    exit_t30_ts:    Optional[datetime] = None
    exit_t30_price: Optional[float]    = None
    pnl_t30:        Optional[float]    = None

    # ICT structure break exit
    exit_ictexit_ts:    Optional[datetime] = None
    exit_ictexit_price: Optional[float]    = None
    exit_ictexit_reason: Optional[str]     = None
    pnl_ict:            Optional[float]    = None

    # Sequence
    mom_aligned:    bool = False
    impulse_strong: bool = False
    has_prior_sweep: bool = False


# ── Session simulator ─────────────────────────────────────────────────

def simulate_session(bars_raw, daily_ohlcv, lookup, symbol, td,
                     expiry_idx, capital):
    """
    Run pure ICT simulation for one session.
    Returns list[TradeResult].
    """
    lot_size = LOT_SIZE[symbol]
    ed = nearest_expiry_db(td, expiry_idx)
    if ed is None:
        return []

    # Convert raw bars to Bar objects
    bars = [Bar(
        bar_ts=r["bar_ts"] if isinstance(r["bar_ts"], datetime) else datetime.fromisoformat(r["bar_ts"]),
        open=float(r["open"]), high=float(r["high"]),
        low=float(r["low"]), close=float(r["close"]),
        trade_date=td,
    ) for r in bars_raw]

    if len(bars) < 30:
        return []

    # Prior session high/low
    dates_sorted = sorted(daily_ohlcv.keys())
    prior_dates  = [d for d in dates_sorted if d < str(td)]
    prior_high = prior_low = None
    if prior_dates:
        pd = daily_ohlcv[prior_dates[-1]]
        prior_high, prior_low = pd["high"], pd["low"]

    results = []
    tss     = [b.bar_ts for b in bars]
    seen_bar_ts = set()

    detector = ICTDetector(symbol=symbol)

    # Process bars incrementally — detect patterns as they form
    # Build 1H zones only from bars completed before pattern detection point
    for pat_idx in range(10, len(bars)):
        bar = bars[pat_idx]

        if bar.bar_ts.time() >= POWER_HOUR:
            break

        # Build HTF zones using all bars up to this point
        # This simulates what the live system would see at this moment
        htf_zones = build_simulated_htf_zones(
            daily_ohlcv,
            bars[:pat_idx],    # only completed bars — no lookahead
            symbol, td
        )

        # Detect patterns on last 10 bars ending at pat_idx
        start = max(0, pat_idx - 10)
        window_bars = bars[start:pat_idx + 1]
        patterns = detector.detect(
            bars=window_bars,
            atm_iv=None,
            htf_zones=htf_zones,
            prior_high=prior_high,
            prior_low=prior_low,
        )

        for pattern in patterns:
            # Dedup: one trade per (pattern_type, bar_ts)
            key = (pattern.pattern_type, pattern.bar_ts)
            if key in seen_bar_ts:
                continue
            if pattern.bar_ts.time() >= POWER_HOUR:
                continue
            if pattern.ict_tier == "SKIP":
                continue
            seen_bar_ts.add(key)

            # Which timeframe gave the MTF context?
            htf_tf = "NONE"
            if pattern.htf_zone_id:
                for z in htf_zones:
                    if z.id == pattern.htf_zone_id:
                        htf_tf = z.timeframe
                        break

            # Position sizing: tier × IV scaling × capital
            tier_mult = TIER_MULT.get(pattern.ict_tier, 1.0)
            base_lots = max(1, int(capital / 100_000))  # 1 lot per 1L
            lots      = max(1, int(base_lots * tier_mult))

            # Entry
            entry_strike = atm_strike(pattern.spot_at_detection, symbol)
            entry_price  = get_option_price_at(
                lookup, entry_strike, pattern.opt_type, pattern.bar_ts, symbol)
            if entry_price is None:
                continue

            capital_deployed = entry_price * lots * lot_size

            # Find bar index of entry
            try:
                entry_idx = tss.index(pattern.bar_ts)
            except ValueError:
                # Approximate
                entry_idx = bisect.bisect_left(tss, pattern.bar_ts)
                if entry_idx >= len(bars):
                    continue

            # T+30m exit
            t30_ts    = pattern.bar_ts + timedelta(minutes=30)
            t30_price = get_option_price_at(
                lookup, entry_strike, pattern.opt_type, t30_ts, symbol)
            pnl_t30 = None
            if t30_price:
                pnl_t30 = (t30_price - entry_price) * lots * lot_size

            # ICT structure break exit
            ict_ts, ict_price, ict_reason = find_structure_break_exit(
                bars, entry_idx, pattern.direction,
                pattern.spot_at_detection,
                pattern.zone_low, pattern.zone_high,
                lookup, entry_strike, pattern.opt_type, symbol
            )
            pnl_ict = None
            if ict_price:
                pnl_ict = (ict_price - entry_price) * lots * lot_size

            results.append(TradeResult(
                td=td, symbol=symbol,
                pattern_type=pattern.pattern_type,
                direction=pattern.direction,
                ot=pattern.opt_type,
                ict_tier=pattern.ict_tier,
                mtf_context=pattern.mtf_context,
                htf_timeframe=htf_tf,
                time_zone=pattern.time_zone,
                entry_ts=pattern.bar_ts,
                entry_price=entry_price,
                strike=entry_strike,
                entry_spot=pattern.spot_at_detection,
                zone_high=pattern.zone_high,
                zone_low=pattern.zone_low,
                capital_deployed=capital_deployed,
                lots=lots,
                exit_t30_ts=t30_ts,
                exit_t30_price=t30_price,
                pnl_t30=pnl_t30,
                exit_ictexit_ts=ict_ts,
                exit_ictexit_price=ict_price,
                exit_ictexit_reason=ict_reason,
                pnl_ict=pnl_ict,
                mom_aligned=pattern.mom_aligned,
                impulse_strong=pattern.impulse_strong,
                has_prior_sweep=pattern.has_prior_sweep,
            ))

    return results


# ── Stats helper ──────────────────────────────────────────────────────

def stats_block(trades, pnl_key="pnl_t30"):
    vals = [getattr(t, pnl_key) for t in trades
            if getattr(t, pnl_key) is not None]
    if not vals:
        return "N=0"
    wins = sum(1 for v in vals if v > 0)
    wr   = 100 * wins / len(vals)
    avg  = sum(vals) / len(vals)
    tot  = sum(vals)
    return (f"N={len(vals):>4}  WR={wr:>5.1f}%  "
            f"Avg=₹{avg:>+8,.0f}  Total=₹{tot:>+10,.0f}  "
            f"Best=₹{max(vals):>+8,.0f}  Worst=₹{min(vals):>+8,.0f}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    all_trades   = []
    capital_state = {"NIFTY": STARTING_CAPITAL, "SENSEX": STARTING_CAPITAL}
    session_log  = []   # (td, symbol, n_trades, session_pnl_t30, capital_start, capital_end)

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        # Expiry index
        log("  Building expiry index...")
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"  {len(expiry_idx)} weekly expiries found")

        # Load full year spot bars
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

        # Build daily OHLCV dict (for HTF zone simulation)
        daily_ohlcv = {}
        for td_str, bars in spot_sessions.items():
            daily_ohlcv[str(td_str)] = {
                "date":  td_str,
                "open":  float(bars[0]["open"]),
                "high":  max(float(b["high"]) for b in bars),
                "low":   min(float(b["low"])  for b in bars),
                "close": float(bars[-1]["close"]),
            }

        capital = capital_state[symbol]
        scored = skipped = 0

        for i, td in enumerate(dates):
            bars_raw = spot_sessions[td]
            ed       = nearest_expiry_db(td, expiry_idx)
            if ed is None:
                skipped += 1
                continue

            # Fetch options (ATM ± 10 from opening spot)
            open_spot = float(bars_raw[0]["open"])
            step      = STRIKE_STEP[symbol]
            base_atm  = atm_strike(open_spot, symbol)
            strikes   = {base_atm + off * step for off in range(-10, 11)}

            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed, sorted(strikes), ["CE","PE"])
            except Exception:
                skipped += 1
                continue
            if not lookup:
                skipped += 1
                continue

            # Need at least some prior days for HTF zones
            prior_day_count = sum(1 for d in daily_ohlcv if str(d) < str(td))
            if prior_day_count < 5:
                skipped += 1
                continue

            trades = simulate_session(
                bars_raw, daily_ohlcv, lookup, symbol, td, expiry_idx, capital)

            session_pnl_t30 = sum(t.pnl_t30 for t in trades
                                  if t.pnl_t30 is not None)
            n = len(trades)
            cap_start = capital

            # Compounding: add profits, absorb losses (no floor reset)
            if session_pnl_t30 > 0:
                capital += session_pnl_t30
            else:
                capital += session_pnl_t30   # stays reduced, no reset

            session_log.append((td, symbol, n, session_pnl_t30,
                                 cap_start, capital))
            all_trades.extend(trades)
            scored += 1

            if i % 20 == 0:
                log(f"    {i}/{len(dates)} | scored={scored} | "
                    f"capital=₹{capital:,.0f} | trades_so_far={len(all_trades)}")

        capital_state[symbol] = capital
        log(f"  Complete — {scored} sessions | {len([t for t in all_trades if t.symbol==symbol])} trades | "
            f"Final capital ₹{capital:,.0f}")

    # ── Output ────────────────────────────────────────────────────────

    nifty_trades  = [t for t in all_trades if t.symbol == "NIFTY"]
    sensex_trades = [t for t in all_trades if t.symbol == "SENSEX"]

    W = 115
    SEP = "=" * W

    print(f"\n{SEP}")
    print(f"  MERDIAN EXPERIMENT 15 — PURE ICT COMPOUNDING SIMULATION")
    print(f"  No MERDIAN gates. ICT patterns only: BEAR_OB, BULL_OB, BULL_FVG, JUDAS_BULL")
    print(f"  Starting capital: ₹{STARTING_CAPITAL:,.0f} per index | Compounding: profits added, losses absorbed")
    print(f"  Context: W/D/H zones simulated from hist_spot_bars_1m (same logic as live ENH-37)")
    print(f"{SEP}")

    # ── Section 1 — Session log ───────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 1 — SESSION-BY-SESSION COMPOUNDING (T+30m exit)")
    print(f"{'='*115}")
    print(f"  {'Date':<12} {'Sym':<7} {'N':>4} {'Session P&L':>12} "
          f"{'Capital Start':>14} {'Capital End':>14}  {'Move'}")
    print(f"  {'-'*105}")

    for (td, sym, n, pnl, cap_s, cap_e) in sorted(session_log, key=lambda x: (x[1], x[0])):
        if n == 0:
            continue
        arrow = "▲" if pnl > 0 else "▼"
        print(f"  {str(td):<12} {sym:<7} {n:>4} "
              f"₹{pnl:>+11,.0f} ₹{cap_s:>13,.0f} ₹{cap_e:>13,.0f}  {arrow}")

    # ── Section 2 — Compounding summary ──────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 2 — COMPOUNDING SUMMARY")
    print(f"{SEP}")

    for symbol in ["NIFTY", "SENSEX"]:
        sl = [(r[3], r[4], r[5]) for r in session_log if r[1] == symbol and r[2] > 0]
        if not sl:
            continue
        caps = [STARTING_CAPITAL] + [r[2] for r in sl]
        peak = max(caps)
        trough = min(caps)
        final = caps[-1]
        gain  = final - STARTING_CAPITAL
        pct_gain = 100 * gain / STARTING_CAPITAL

        # Max drawdown from peak
        max_dd = 0
        peak_so_far = STARTING_CAPITAL
        for c in caps:
            peak_so_far = max(peak_so_far, c)
            dd = peak_so_far - c
            max_dd = max(max_dd, dd)

        print(f"\n  {symbol}:")
        print(f"    Starting capital:  ₹{STARTING_CAPITAL:>10,.0f}")
        print(f"    Final capital:     ₹{final:>10,.0f}  ({pct_gain:+.1f}%)")
        print(f"    Peak capital:      ₹{peak:>10,.0f}")
        print(f"    Max drawdown:      ₹{max_dd:>10,.0f}  ({100*max_dd/peak:.1f}% from peak)")
        print(f"    Sessions with trades: {len(sl)}")
        print(f"    Profitable sessions:  {sum(1 for p,_,_ in sl if p > 0)}")

    # ── Section 3 — By pattern type ───────────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 3 — BY PATTERN TYPE (T+30m exit)")
    print(f"{SEP}")
    print(f"  {'Pattern':<15} {stats_block([], 'pnl_t30')[:3]}  Stats")
    print(f"  {'-'*100}")

    for pt in ["BEAR_OB", "BULL_OB", "BULL_FVG", "JUDAS_BULL"]:
        trades = [t for t in all_trades if t.pattern_type == pt]
        if trades:
            print(f"  {pt:<15} {stats_block(trades, 'pnl_t30')}")

    # ── Section 4 — By MTF context ────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 4 — BY MTF CONTEXT (T+30m exit)")
    print(f"  KEY QUESTION: Does 1H zone (MEDIUM) add genuine edge?")
    print(f"{SEP}")
    print(f"  {'Context':<12} {'HTF Source':<10} {''}")
    print(f"  {'-'*100}")

    for ctx in ["VERY_HIGH", "HIGH", "MEDIUM", "LOW"]:
        trades = [t for t in all_trades if t.mtf_context == ctx]
        htf_tf = "W" if ctx=="VERY_HIGH" else "D" if ctx=="HIGH" else "H" if ctx=="MEDIUM" else "NONE"
        if trades:
            print(f"  {ctx:<12} [{htf_tf}]      {stats_block(trades, 'pnl_t30')}")

    # ── Section 5 — 1H zone reliability ──────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 5 — 1H ZONE RELIABILITY DEEP DIVE")
    print(f"  MEDIUM context = 1H OB/FVG detected during same session")
    print(f"{SEP}")

    medium_trades = [t for t in all_trades if t.mtf_context == "MEDIUM"]
    print(f"\n  All MEDIUM context trades: {stats_block(medium_trades, 'pnl_t30')}")

    print(f"\n  MEDIUM by pattern type:")
    for pt in ["BEAR_OB","BULL_OB","BULL_FVG","JUDAS_BULL"]:
        trades = [t for t in medium_trades if t.pattern_type == pt]
        if trades:
            print(f"    {pt:<15} {stats_block(trades, 'pnl_t30')}")

    print(f"\n  MEDIUM by time zone:")
    for tz in ["OPEN","MORNING","MIDDAY","AFTNOON"]:
        trades = [t for t in medium_trades if t.time_zone == tz]
        if trades:
            print(f"    {tz:<15} {stats_block(trades, 'pnl_t30')}")

    print(f"\n  MEDIUM vs HIGH vs VERY_HIGH by pattern:")
    for pt in ["BEAR_OB","BULL_OB"]:
        print(f"\n    {pt}:")
        for ctx in ["VERY_HIGH","HIGH","MEDIUM","LOW"]:
            trades = [t for t in all_trades
                      if t.pattern_type == pt and t.mtf_context == ctx]
            if trades:
                print(f"      {ctx:<12} {stats_block(trades, 'pnl_t30')}")

    # ── Section 6 — By tier ───────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 6 — BY SIGNAL TIER (T+30m exit)")
    print(f"  TIER1 = Morning + MOM_YES + IMP_WEK | TIER2 = all other qualifying")
    print(f"{SEP}")

    for tier in ["TIER1","TIER2"]:
        trades = [t for t in all_trades if t.ict_tier == tier]
        if trades:
            print(f"  {tier}   {stats_block(trades, 'pnl_t30')}")

    # ── Section 7 — T+30m vs ICT structure break ──────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 7 — EXIT COMPARISON: T+30m vs ICT STRUCTURE BREAK")
    print(f"  ICT exit: hold until spot closes through zone boundary, or session close")
    print(f"{SEP}")

    t30_trades  = [t for t in all_trades if t.pnl_t30  is not None]
    ict_trades  = [t for t in all_trades if t.pnl_ict  is not None]

    print(f"  T+30m exit:          {stats_block(t30_trades, 'pnl_t30')}")
    print(f"  ICT structure break: {stats_block(ict_trades, 'pnl_ict')}")

    print(f"\n  Exit comparison by context:")
    for ctx in ["VERY_HIGH","HIGH","MEDIUM","LOW"]:
        t30 = [t for t in t30_trades if t.mtf_context == ctx]
        ict = [t for t in ict_trades if t.mtf_context == ctx]
        if t30:
            t30_tot = sum(t.pnl_t30 for t in t30 if t.pnl_t30)
            ict_tot = sum(t.pnl_ict for t in ict if t.pnl_ict)
            better  = "T+30m" if t30_tot >= ict_tot else "ICT exit"
            print(f"  {ctx:<12} T+30m=₹{t30_tot:>+10,.0f}  "
                  f"ICT=₹{ict_tot:>+10,.0f}  → {better}")

    # ── Section 8 — Verdict ───────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  SECTION 8 — VERDICT")
    print(f"{SEP}")

    total_t30   = sum(t.pnl_t30 for t in all_trades if t.pnl_t30 is not None)
    total_ict   = sum(t.pnl_ict for t in all_trades if t.pnl_ict is not None)
    nifty_final = capital_state["NIFTY"]
    sensex_final= capital_state["SENSEX"]
    total_final = nifty_final + sensex_final
    total_start = STARTING_CAPITAL * 2

    print(f"\n  Starting capital (total):  ₹{total_start:>10,.0f}")
    print(f"  Final capital (total):     ₹{total_final:>10,.0f}  "
          f"({100*(total_final-total_start)/total_start:+.1f}%)")
    print(f"    NIFTY:  ₹{nifty_final:>10,.0f}")
    print(f"    SENSEX: ₹{sensex_final:>10,.0f}")
    print(f"")
    print(f"  Total trades scored:  {len(all_trades)}")
    print(f"  T+30m total P&L:      ₹{total_t30:>+10,.0f}")
    print(f"  ICT exit total P&L:   ₹{total_ict:>+10,.0f}")
    print(f"")

    # 1H verdict
    medium = [t for t in all_trades if t.mtf_context == "MEDIUM"]
    high   = [t for t in all_trades if t.mtf_context == "HIGH"]
    very_high = [t for t in all_trades if t.mtf_context == "VERY_HIGH"]

    med_tot  = sum(t.pnl_t30 for t in medium if t.pnl_t30)
    high_tot = sum(t.pnl_t30 for t in high   if t.pnl_t30)
    vh_tot   = sum(t.pnl_t30 for t in very_high if t.pnl_t30)

    print(f"  1H ZONE VERDICT:")
    if medium:
        med_wr = 100*sum(1 for t in medium if (t.pnl_t30 or 0)>0)/len(medium)
        print(f"    MEDIUM (1H zone):    N={len(medium):>4}  "
              f"WR={med_wr:.1f}%  Total=₹{med_tot:>+10,.0f}")
    if high:
        h_wr = 100*sum(1 for t in high if (t.pnl_t30 or 0)>0)/len(high)
        print(f"    HIGH (daily zone):   N={len(high):>4}  "
              f"WR={h_wr:.1f}%  Total=₹{high_tot:>+10,.0f}")
    if very_high:
        vh_wr = 100*sum(1 for t in very_high if (t.pnl_t30 or 0)>0)/len(very_high)
        print(f"    VERY_HIGH (weekly):  N={len(very_high):>4}  "
              f"WR={vh_wr:.1f}%  Total=₹{vh_tot:>+10,.0f}")

    if medium and high:
        if med_tot > 0 and med_wr > 50:
            print(f"\n  ★ 1H zones ADD EDGE — MEDIUM context is profitable")
            print(f"    Recommend: keep MEDIUM in live MTF hierarchy")
        elif med_tot < 0:
            print(f"\n  ✗ 1H zones DESTROY EDGE — MEDIUM context is unprofitable")
            print(f"    Recommend: remove MEDIUM context from live signal (use D/W only)")
        else:
            print(f"\n  ~ 1H zones NEUTRAL — MEDIUM context breaks even")
            print(f"    Recommendation: keep for diversity but do not size up on MEDIUM")

    print(f"\n{SEP}\n")


if __name__ == "__main__":
    main()
