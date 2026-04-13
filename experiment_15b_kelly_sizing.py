#!/usr/bin/env python3
"""
experiment_15b_kelly_sizing.py
MERDIAN Experiment 15b -- Pure ICT Trade Universe x Four Sizing Strategies

Uses the exact same ICT detection as Experiment 15:
  - ICTDetector with W/D/H zone simulation
  - BEAR_OB, BULL_OB, BULL_FVG, JUDAS_BULL
  - No MERDIAN regime gates

Adds T2/T3 pyramid confirmation to each trade (spot move check at T+5m / T+10m)
then applies four parallel sizing strategies from Experiment 16:

  A -- Original 1->2->3 flat (baseline)
  B -- User tiered: 7->14->21 on TIER1+TIER2, 1->2->3 on TIER3
  C -- Half Kelly tiered: 50% / 40% / 20% of sizing capital per tier
  D -- Full Kelly tiered: 100% / 80% / 40% of sizing capital per tier

Capital ceiling (liquidity constraint):
  Sizing capital frozen at INR 25L
  Hard cap: sizing never exceeds INR 50L equivalent
  Profits accumulate above 25L but don't increase lot sizes

Compounding:
  Each trade P&L updates all four capital states independently
  Floor: INR 2L (minimum sizing base after drawdown)
  No floor reset -- losses reduce capital permanently

Starting capital: INR 2,00,000 per index per strategy

Output:
  Section 1 -- Strategy comparison (A vs B vs C vs D)
  Section 2 -- Monthly compounding curve (all 4)
  Section 3 -- Tier contribution breakdown
  Section 4 -- Drawdown analysis
  Section 5 -- Best and worst sessions
  Section 6 -- MTF context breakdown by strategy
  Section 7 -- Verdict

Runtime: ~3-5 hours (same detection pass as Exp 15, faster output).

Usage:
    python experiment_15b_kelly_sizing.py
"""

import os
import bisect
import time
import math
from datetime import datetime, date, timedelta, time as dtime
from collections import defaultdict
from itertools import groupby
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client

from detect_ict_patterns import (
    ICTDetector, Bar, HTFZone,
    OB_MIN_MOVE_PCT, FVG_MIN_PCT,
    MORNING_START, MIDDAY_START, POWER_HOUR,
    pct,
)
from build_ict_htf_zones import (
    build_weekly_bars, detect_weekly_zones, detect_daily_zones,
    aggregate_to_hourly,
)
from merdian_utils import build_expiry_index_simple, nearest_expiry_db

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE        = 1_000
STARTING_CAPITAL = 200_000
CAPITAL_FLOOR    = 200_000
CAPITAL_SCALE_START = 2_500_000   # INR 25L -- freeze sizing here
CAPITAL_HARD_CAP    = 5_000_000   # INR 50L -- absolute ceiling
RUIN_THRESHOLD   =  10_000

LOT_SIZE   = {"NIFTY": 75, "SENSEX": 20}  # NIFTY: 75 (Apr-Dec 2025), 65 from Jan 2026. Using 75 (majority of year). SENSEX: 20 from early 2025.
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}
ATM_RADIUS  = 3
MAX_GAP_MIN = 5
MIN_OPTION_PRICE = 5.0
SESSION_CLOSE    = dtime(15, 15)
WEEKLY_LOOKBACK  = 8

# Pyramid confirmation
T2_MIN    = 5      # minutes
T3_MIN    = 10
T2_THRESH = 0.20   # % spot move to confirm T2
T3_THRESH = 0.40   # % spot move to confirm T3

# Strategy A: flat 1->2->3 regardless of tier
STRAT_A = (1, 2, 3)   # T1 lots, T2 add, T3 add -> max 6

# Strategy B: tiered fixed lots
STRAT_B_TIER12 = (7, 14, 21)  # max 42 for TIER1+2
STRAT_B_TIER3  = (1,  2,  3)  # max  6 for TIER3

# Half Kelly (C) and Full Kelly (D) fractions by ICT tier
HALF_KELLY = {"TIER1": 0.50, "TIER2": 0.40, "TIER3": 0.20}
FULL_KELLY = {"TIER1": 1.00, "TIER2": 0.80, "TIER3": 0.40}

STRATEGIES = ["A", "B", "C", "D"]
STRAT_NAMES = {
    "A": "Original flat 1->2->3",
    "B": "User tiered 7->14->21 (T1+2), 1->2->3 (T3)",
    "C": "Half Kelly tiered (optimal)",
    "D": "Full Kelly tiered (aggressive)",
}

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Utilities ──────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def month_label(d):
    return f"{MONTH_NAMES[d.month]} {d.year}"

def effective_sizing_capital(capital):
    """Apply liquidity ceiling: freeze sizing at 25L, cap at 50L."""
    eff = max(capital, CAPITAL_FLOOR)
    if eff <= CAPITAL_SCALE_START:
        return eff
    return CAPITAL_SCALE_START   # freeze -- don't grow lots above 25L


def kelly_lots(capital, kelly_fraction, entry_price, lot_size):
    """
    Compute T1/T2/T3 lot counts using Half or Full Kelly fraction.
    Pyramid ratio maintained: T1:T2_add:T3_add = 1:2:3 (total 6 units).
    """
    sizing_cap    = effective_sizing_capital(max(capital, CAPITAL_FLOOR))
    target_deploy = sizing_cap * kelly_fraction
    total_units   = 6   # 1+2+3
    base_lot      = max(1, int(target_deploy / (total_units * entry_price * lot_size)))
    return base_lot, base_lot * 2, base_lot * 3   # T1, T2_add, T3_add


# ── Data loading ───────────────────────────────────────────────────────

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


def get_option_price_at(lookup, strike, ot, target_ts, symbol):
    step = STRIKE_STEP[symbol]
    candidates = [strike + i * step for i in range(-ATM_RADIUS, ATM_RADIUS + 1)]
    best_p, best_g = None, timedelta(minutes=MAX_GAP_MIN + 1)
    for stk in candidates:
        bars = lookup.get((stk, ot), [])
        if not bars: continue
        tss = [b[0] for b in bars]
        idx = bisect.bisect_left(tss, target_ts)
        for i in (idx - 1, idx):
            if 0 <= i < len(bars):
                gap = abs(bars[i][0] - target_ts)
                if gap < best_g:
                    best_g, best_p = gap, bars[i][1]
    return best_p if best_g <= timedelta(minutes=MAX_GAP_MIN) else None


def get_spot_at(all_bars, target_ts):
    tss = [b["bar_ts"] for b in all_bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=MAX_GAP_MIN + 1)
    for i in (idx - 1, idx):
        if 0 <= i < len(all_bars):
            gap = abs(all_bars[i]["bar_ts"] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, all_bars[i]["close"]
    return best_p if best_g <= timedelta(minutes=MAX_GAP_MIN) else None


# ── HTF zone builder (same as Exp 15) ─────────────────────────────────

def build_simulated_htf_zones(daily_ohlcv, intraday_bars_today, symbol, td):
    zones = []

    weekly_bars = build_weekly_bars(daily_ohlcv)
    weekly_bars = weekly_bars[-WEEKLY_LOOKBACK:]
    w_zone_dicts = detect_weekly_zones(weekly_bars, symbol)
    for z in w_zone_dicts:
        valid_from = date.fromisoformat(z["valid_from"])
        valid_to   = date.fromisoformat(z["valid_to"])
        if valid_from <= td <= valid_to:
            zones.append(HTFZone(
                id=f"W_{z['pattern_type']}_{z['zone_high']:.0f}",
                symbol=symbol, timeframe="W",
                pattern_type=z["pattern_type"],
                direction=int(z["direction"]),
                zone_high=float(z["zone_high"]),
                zone_low=float(z["zone_low"]),
                status="ACTIVE",
            ))

    # OI-07: detect_daily_zones compares keys with str target — needs str-keyed dict
    _daily_str = {str(k): v for k, v in daily_ohlcv.items()}
    d_zone_dicts = detect_daily_zones(_daily_str, symbol, str(td))
    for z in d_zone_dicts:
        zones.append(HTFZone(
            id=f"D_{z['pattern_type']}_{z['zone_high']:.0f}",
            symbol=symbol, timeframe="D",
            pattern_type=z["pattern_type"],
            direction=int(z["direction"]),
            zone_high=float(z["zone_high"]),
            zone_low=float(z["zone_low"]),
            status="ACTIVE",
        ))

    if intraday_bars_today:
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
            if curr_move >= OB_MIN_MOVE_PCT and prev["close"] < prev["open"]:
                zones.append(HTFZone(
                    id=f"H_BULL_OB_{prev['hour_start'].strftime('%H%M')}",
                    symbol=symbol, timeframe="H", pattern_type="BULL_OB",
                    direction=+1,
                    zone_high=max(prev["open"], prev["close"]),
                    zone_low=min(prev["open"], prev["close"]),
                    status="ACTIVE",
                ))
            if curr_move <= -OB_MIN_MOVE_PCT and prev["close"] > prev["open"]:
                zones.append(HTFZone(
                    id=f"H_BEAR_OB_{prev['hour_start'].strftime('%H%M')}",
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


# ── Portfolio state ────────────────────────────────────────────────────

class PortfolioState:
    def __init__(self, name):
        self.name    = name
        self.capital = STARTING_CAPITAL
        self.peak    = STARTING_CAPITAL
        self.max_dd  = 0.0
        self.wins    = 0
        self.losses  = 0
        self.monthly_pnl = defaultdict(float)
        self.monthly_n   = defaultdict(int)
        self.session_pnl = defaultdict(float)
        self.tier_pnl    = defaultdict(float)
        self.tier_n      = defaultdict(int)
        self.tier_wins   = defaultdict(int)
        self.mtf_pnl     = defaultdict(float)
        self.mtf_n       = defaultdict(int)
        self.mtf_wins    = defaultdict(int)
        self.best_trade  = None
        self.worst_trade = None

    def apply(self, pnl, td, tier, mtf, desc):
        self.capital += pnl
        mk = (td.year, td.month)
        self.monthly_pnl[mk] += pnl
        self.monthly_n[mk]   += 1
        self.session_pnl[td] += pnl
        self.tier_pnl[tier]  += pnl
        self.tier_n[tier]    += 1
        self.mtf_pnl[mtf]   += pnl
        self.mtf_n[mtf]     += 1
        if pnl > 0:
            self.wins += 1
            self.tier_wins[tier] += 1
            self.mtf_wins[mtf]  += 1
        else:
            self.losses += 1
        if self.capital > self.peak:
            self.peak = self.capital
        dd = (self.peak - self.capital) / self.peak * 100
        if dd > self.max_dd:
            self.max_dd = dd
        if self.best_trade is None or pnl > self.best_trade[0]:
            self.best_trade = (pnl, desc, td)
        if self.worst_trade is None or pnl < self.worst_trade[0]:
            self.worst_trade = (pnl, desc, td)

    @property
    def total_trades(self): return self.wins + self.losses

    @property
    def wr(self): return 100 * self.wins / self.total_trades if self.total_trades else 0

    @property
    def return_pct(self): return 100 * (self.capital - STARTING_CAPITAL) / STARTING_CAPITAL

    @property
    def ret_per_dd(self): return self.return_pct / self.max_dd if self.max_dd else float("inf")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    states = {}   # (symbol, strategy) -> PortfolioState
    for symbol in ["NIFTY", "SENSEX"]:
        for s in STRATEGIES:
            states[(symbol, s)] = PortfolioState(f"{symbol}-{s}")

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")
        lot_size = LOT_SIZE[symbol]

        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"  {len(expiry_idx)} expiry dates indexed")

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
        all_bars      = raw
        dates         = sorted(spot_sessions.keys())
        log(f"  {len(raw):,} bars | {len(dates)} sessions")

        daily_ohlcv = {}
        for d, bars in spot_sessions.items():
            daily_ohlcv[d] = {
                "date":  d,
                "open":  float(bars[0]["open"]),
                "high":  max(float(b["high"]) for b in bars),
                "low":   min(float(b["low"])  for b in bars),
                "close": float(bars[-1]["close"]),
            }
        dates_sorted = sorted(daily_ohlcv.keys())

        detector = ICTDetector(symbol=symbol)
        scored = skipped = total_trades = 0

        for i, td in enumerate(dates):
            bars_raw = spot_sessions[td]
            ed       = nearest_expiry_db(td, expiry_idx)
            if ed is None:
                skipped += 1
                continue

            prior_dates = [d for d in dates_sorted if d < td]
            prior_high  = daily_ohlcv[prior_dates[-1]]["high"] if prior_dates else None
            prior_low   = daily_ohlcv[prior_dates[-1]]["low"]  if prior_dates else None

            if len([d for d in dates_sorted if d < td]) < 5:
                skipped += 1
                continue

            # Convert to Bar objects
            bars = [Bar(
                bar_ts=r["bar_ts"] if isinstance(r["bar_ts"], datetime)
                       else datetime.fromisoformat(r["bar_ts"]),
                open=float(r["open"]), high=float(r["high"]),
                low=float(r["low"]),  close=float(r["close"]),
                trade_date=td,
            ) for r in bars_raw]

            if len(bars) < 30:
                skipped += 1
                continue

            # Fetch option data for this session
            open_spot = bars[0].open
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

            scored += 1
            seen_keys = set()

            for pat_idx in range(10, len(bars)):
                bar = bars[pat_idx]
                if bar.bar_ts.time() >= POWER_HOUR:
                    break

                htf_zones = build_simulated_htf_zones(
                    daily_ohlcv, bars[:pat_idx], symbol, td)

                start   = max(0, pat_idx - 10)
                patterns = detector.detect(
                    bars=bars[start:pat_idx + 1],
                    atm_iv=None,
                    htf_zones=htf_zones,
                    prior_high=prior_high,
                    prior_low=prior_low,
                )

                for pattern in patterns:
                    key = (pattern.pattern_type, pattern.bar_ts)
                    if key in seen_keys: continue
                    if pattern.bar_ts.time() >= POWER_HOUR: continue
                    if pattern.ict_tier == "SKIP": continue
                    seen_keys.add(key)

                    # Map ICT tier to strategy tier label
                    tier = pattern.ict_tier   # "TIER1" or "TIER2"

                    entry_strike = atm_strike(pattern.spot_at_detection, symbol)
                    entry_price  = get_option_price_at(
                        lookup, entry_strike, pattern.opt_type,
                        pattern.bar_ts, symbol)
                    if entry_price is None: continue

                    # T+30m exit price
                    t30_price = get_option_price_at(
                        lookup, entry_strike, pattern.opt_type,
                        pattern.bar_ts + timedelta(minutes=30), symbol)
                    if t30_price is None: continue

                    # T2/T3 spot confirmations
                    spot_entry = pattern.spot_at_detection
                    direction  = pattern.direction
                    p5  = get_spot_at(all_bars,
                                      pattern.bar_ts + timedelta(minutes=T2_MIN))
                    p10 = get_spot_at(all_bars,
                                      pattern.bar_ts + timedelta(minutes=T3_MIN))

                    pct_dir = lambda s, e: 100*(e-s)/s * direction
                    t2_ok = p5  is not None and pct_dir(spot_entry, p5)  >= T2_THRESH
                    t3_ok = t2_ok and p10 is not None and pct_dir(spot_entry, p10) >= T3_THRESH

                    desc   = f"{pattern.pattern_type}|{tier}|{pattern.mtf_context}"
                    mtf    = pattern.mtf_context

                    # ── Strategy A -- flat 1->2->3 ────────────────────
                    t1a, t2a, t3a = STRAT_A
                    lots_a = t1a
                    if t2_ok: lots_a += t2a
                    if t3_ok: lots_a += t3a
                    pnl_a = (t30_price - entry_price) * lots_a * lot_size
                    states[(symbol,"A")].apply(pnl_a, td, tier, mtf, desc)

                    # ── Strategy B -- user tiered ─────────────────────
                    cap_b = states[(symbol,"B")].capital
                    scale = min(1.0, effective_sizing_capital(cap_b) / CAPITAL_SCALE_START)
                    if tier in ("TIER1","TIER2"):
                        t1b = max(1, int(STRAT_B_TIER12[0] * scale))
                        t2b = max(1, int(STRAT_B_TIER12[1] * scale))
                        t3b = max(1, int(STRAT_B_TIER12[2] * scale))
                    else:
                        t1b, t2b, t3b = STRAT_B_TIER3
                    lots_b = t1b
                    if t2_ok: lots_b += t2b
                    if t3_ok: lots_b += t3b
                    pnl_b = (t30_price - entry_price) * lots_b * lot_size
                    states[(symbol,"B")].apply(pnl_b, td, tier, mtf, desc)

                    # ── Strategy C -- Half Kelly ───────────────────────
                    cap_c  = states[(symbol,"C")].capital
                    kf_c   = HALF_KELLY.get(tier, HALF_KELLY["TIER2"])
                    t1c, t2c_add, t3c_add = kelly_lots(cap_c, kf_c, entry_price, lot_size)
                    lots_c = t1c
                    if t2_ok: lots_c += t2c_add
                    if t3_ok: lots_c += t3c_add
                    pnl_c = (t30_price - entry_price) * lots_c * lot_size
                    states[(symbol,"C")].apply(pnl_c, td, tier, mtf, desc)

                    # ── Strategy D -- Full Kelly ───────────────────────
                    cap_d  = states[(symbol,"D")].capital
                    kf_d   = FULL_KELLY.get(tier, FULL_KELLY["TIER2"])
                    t1d, t2d_add, t3d_add = kelly_lots(cap_d, kf_d, entry_price, lot_size)
                    lots_d = t1d
                    if t2_ok: lots_d += t2d_add
                    if t3_ok: lots_d += t3d_add
                    pnl_d = (t30_price - entry_price) * lots_d * lot_size
                    states[(symbol,"D")].apply(pnl_d, td, tier, mtf, desc)

                    total_trades += 1

            if i % 20 == 0:
                log(f"    {i}/{len(dates)} | scored={scored} | trades={total_trades} | "
                    f"A=₹{states[(symbol,'A')].capital:,.0f} "
                    f"B=₹{states[(symbol,'B')].capital:,.0f} "
                    f"C=₹{states[(symbol,'C')].capital:,.0f} "
                    f"D=₹{states[(symbol,'D')].capital:,.0f}")

        log(f"  Complete -- {scored} sessions | {total_trades} trades")

    # ── OUTPUT ─────────────────────────────────────────────────────────

    W   = 120
    SEP = "=" * W

    print(f"\n{SEP}")
    print("  MERDIAN EXPERIMENT 15b -- PURE ICT TRADE UNIVERSE x FOUR SIZING STRATEGIES")
    print("  Same ICT detection as Exp 15 (W/D/H zones, ICTDetector)")
    print("  Four strategies with T2/T3 pyramid confirmation and INR 25L/50L ceiling")
    print("  Starting: INR 2,00,000 per index | T+30m exit | Compounding")
    print(f"{SEP}")

    # ── Section 1 -- Strategy comparison ──────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 1 -- STRATEGY COMPARISON SUMMARY")
    print(f"{SEP}")
    print(f"  {'Strategy':<46} {'Final Cap':>12} {'Return':>8} {'MaxDD':>7} "
          f"{'Ret/DD':>8} {'WR':>6} {'Trades':>7}")
    print(f"  {'-'*100}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}:")
        for s in STRATEGIES:
            st  = states[(symbol, s)]
            rdd = f"{st.ret_per_dd:.1f}x" if st.max_dd > 0 else "inf"
            print(f"    [{s}] {STRAT_NAMES[s]:<42} "
                  f"₹{st.capital:>10,.0f}  "
                  f"{st.return_pct:>+7.1f}%  "
                  f"{st.max_dd:>5.1f}%  "
                  f"{rdd:>8}  "
                  f"{st.wr:>5.1f}%  "
                  f"{st.total_trades:>6}")

    print(f"\n  COMBINED (NIFTY + SENSEX):")
    for s in STRATEGIES:
        total = states[("NIFTY",s)].capital + states[("SENSEX",s)].capital
        ret   = 100 * (total - STARTING_CAPITAL*2) / (STARTING_CAPITAL*2)
        dd    = max(states[("NIFTY",s)].max_dd, states[("SENSEX",s)].max_dd)
        rdd   = f"{ret/dd:.1f}x" if dd > 0 else "inf"
        print(f"    [{s}] {STRAT_NAMES[s]:<42} "
              f"₹{total:>10,.0f}  {ret:>+7.1f}%  DD={dd:.1f}%  Ret/DD={rdd}")

    # ── Section 2 -- Monthly curve ─────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 2 -- MONTHLY COMPOUNDING CURVE")
    print(f"{SEP}")

    for symbol in ["NIFTY","SENSEX"]:
        print(f"\n  {symbol}:")
        print(f"  {'Month':<10} {'N':>4}  "
              f"{'[A]':>13} {'[B]':>13} {'[C]':>13} {'[D]':>13}")
        print(f"  {'-'*62}")
        all_months = set()
        for s in STRATEGIES:
            all_months.update(states[(symbol,s)].monthly_pnl.keys())
        cap_run = {s: STARTING_CAPITAL for s in STRATEGIES}
        for mk in sorted(all_months):
            n = states[(symbol,"A")].monthly_n.get(mk, 0)
            for s in STRATEGIES:
                cap_run[s] += states[(symbol,s)].monthly_pnl.get(mk, 0)
            lbl = month_label(date(mk[0], mk[1], 1))
            print(f"  {lbl:<10} {n:>4}  "
                  f"₹{cap_run['A']:>11,.0f}  "
                  f"₹{cap_run['B']:>11,.0f}  "
                  f"₹{cap_run['C']:>11,.0f}  "
                  f"₹{cap_run['D']:>11,.0f}")

    # ── Section 3 -- Tier breakdown ────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 3 -- TIER CONTRIBUTION BREAKDOWN")
    print(f"{SEP}")

    for symbol in ["NIFTY","SENSEX"]:
        print(f"\n  {symbol}:")
        for tier in ["TIER1","TIER2"]:
            print(f"\n    {tier}:")
            for s in STRATEGIES:
                st   = states[(symbol,s)]
                n    = st.tier_n.get(tier, 0)
                wins = st.tier_wins.get(tier, 0)
                pnl  = st.tier_pnl.get(tier, 0)
                wr   = 100*wins/n if n else 0
                avg  = pnl/n if n else 0
                print(f"      [{s}]  N={n:>4}  WR={wr:>5.1f}%  "
                      f"Total=₹{pnl:>+11,.0f}  Avg=₹{avg:>+8,.0f}")

    # ── Section 4 -- Drawdown ──────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 4 -- DRAWDOWN ANALYSIS")
    print(f"{SEP}")

    for symbol in ["NIFTY","SENSEX"]:
        print(f"\n  {symbol}:")
        print(f"  {'Strategy':<46} {'MaxDD':>7} {'Peak Cap':>13} "
              f"{'Worst Trade':>13}")
        print(f"  {'-'*83}")
        for s in STRATEGIES:
            st    = states[(symbol,s)]
            worst = f"₹{st.worst_trade[0]:+,.0f}" if st.worst_trade else "n/a"
            print(f"  [{s}] {STRAT_NAMES[s]:<42} "
                  f"{st.max_dd:>5.1f}%  "
                  f"₹{st.peak:>11,.0f}  "
                  f"{worst:>13}")

    # ── Section 5 -- Best and worst sessions ───────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 5 -- BEST AND WORST SESSIONS [Strategy D]")
    print(f"{SEP}")

    for symbol in ["NIFTY","SENSEX"]:
        print(f"\n  {symbol}:")
        st_d = states[(symbol,"D")]
        best = sorted(st_d.session_pnl.items(), key=lambda x: x[1], reverse=True)[:5]
        print("  Best sessions:")
        for td, pnl in best:
            row = f"    {str(td)}  D=₹{pnl:>+10,.0f}"
            for s in ["A","B","C"]:
                row += f"  {s}=₹{states[(symbol,s)].session_pnl.get(td,0):>+9,.0f}"
            print(row)
        worst = sorted(st_d.session_pnl.items(), key=lambda x: x[1])[:3]
        print("  Worst sessions:")
        for td, pnl in worst:
            row = f"    {str(td)}  D=₹{pnl:>+10,.0f}"
            for s in ["A","B","C"]:
                row += f"  {s}=₹{states[(symbol,s)].session_pnl.get(td,0):>+9,.0f}"
            print(row)

    # ── Section 6 -- MTF context breakdown ────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 6 -- MTF CONTEXT BREAKDOWN (combined NIFTY+SENSEX)")
    print(f"{SEP}")

    for mtf in ["VERY_HIGH","HIGH","MEDIUM","LOW"]:
        print(f"\n  {mtf}:")
        for s in STRATEGIES:
            total_pnl = (states[("NIFTY",s)].mtf_pnl.get(mtf,0) +
                         states[("SENSEX",s)].mtf_pnl.get(mtf,0))
            total_n   = (states[("NIFTY",s)].mtf_n.get(mtf,0) +
                         states[("SENSEX",s)].mtf_n.get(mtf,0))
            total_w   = (states[("NIFTY",s)].mtf_wins.get(mtf,0) +
                         states[("SENSEX",s)].mtf_wins.get(mtf,0))
            wr  = 100*total_w/total_n if total_n else 0
            avg = total_pnl/total_n if total_n else 0
            print(f"    [{s}]  N={total_n:>4}  WR={wr:>5.1f}%  "
                  f"Total=₹{total_pnl:>+11,.0f}  Avg=₹{avg:>+8,.0f}")

    # ── Section 7 -- Verdict ───────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 7 -- VERDICT")
    print(f"{SEP}")

    combined = {}
    for s in STRATEGIES:
        cap  = states[("NIFTY",s)].capital + states[("SENSEX",s)].capital
        ret  = 100*(cap - STARTING_CAPITAL*2)/(STARTING_CAPITAL*2)
        dd   = max(states[("NIFTY",s)].max_dd, states[("SENSEX",s)].max_dd)
        rdd  = ret/dd if dd > 0 else float("inf")
        combined[s] = {"cap": cap, "ret": ret, "dd": dd, "rdd": rdd}

    best_ret = max(STRATEGIES, key=lambda s: combined[s]["ret"])
    best_rdd = max(STRATEGIES, key=lambda s: combined[s]["rdd"])
    min_dd   = min(STRATEGIES, key=lambda s: combined[s]["dd"])

    print(f"\n  Comparison with Exp 15 baseline (1 lot flat, no pyramid):")
    print(f"    Exp 15 NIFTY:  ₹651,308  (+225.7%)")
    print(f"    Exp 15 SENSEX: ₹792,669  (+296.3%)")
    print(f"    Exp 15 Total:  ₹1,443,977 (+261.0%)")

    print(f"\n  Four strategy results (with T2/T3 pyramid, INR 25L ceiling):")
    for s in STRATEGIES:
        print(f"    [{s}] Return={combined[s]['ret']:>+8.1f}%  "
              f"DD={combined[s]['dd']:>5.1f}%  "
              f"Ret/DD={combined[s]['rdd']:>8.1f}x  "
              f"Final=₹{combined[s]['cap']:>12,.0f}  -- {STRAT_NAMES[s]}")

    print(f"\n  Highest return:  [{best_ret}]  {combined[best_ret]['ret']:+.1f}%")
    print(f"  Best Ret/DD:     [{best_rdd}]  {combined[best_rdd]['rdd']:.1f}x")
    print(f"  Lowest DD:       [{min_dd}]  {combined[min_dd]['dd']:.1f}%")
    print(f"\n  Note: costs not modelled. Real P&L ~85-92% of above.")
    print(f"\n{SEP}\n")


if __name__ == "__main__":
    main()
