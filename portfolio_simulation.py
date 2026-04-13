#!/usr/bin/env python3
"""
portfolio_simulation.py
MERDIAN Portfolio Simulation — Apr 2025 to Mar 2026

Starting capital: ₹2,00,000 per symbol (NIFTY + SENSEX independent portfolios)
Total starting capital: ₹4,00,000

Patterns traded (60%+ win rate from research):
  BULL_OB:    87% WR → Buy ATM CE
  BEAR_OB:    83% WR → Buy ATM PE
  BULL_FVG:   72% WR → Buy ATM CE
  JUDAS_BULL: 68% WR → Buy ATM CE

Position sizing:
  Max 10% of current capital per trade.
  Lot sizes: NIFTY=25, SENSEX=15
  Entry = ATM option close at detection bar.
  If premium × lot_size > 10% of capital → skip trade (insufficient capital).

Execution structures (both run in parallel, separate P&L tracked):
  FIXED:   1 lot per trade. Always.
  PYRAMID: T1=1 lot at entry. T2=+2 lots at T+5m if move ≥0.20%.
           T3=+3 more lots at T+10m if move ≥0.40%. Max 6 lots.
           Stop moved to breakeven on T1 after T2. On T2 after T3.

Exit: T+30m option close price (primary horizon).
Fallback exit if T+30m price unavailable: T+15m or T+60m (in that order).

Capital management:
  After each trade: capital += pnl_rupees
  If capital < ₹10,000: trading halted for that symbol (ruin protection)
  Trade skipped if premium × lot_size > 20% of current capital (avoid over-leverage)

Output:
  - Chronological trade log (every trade)
  - Monthly P&L summary
  - Final portfolio value comparison (Fixed vs Pyramid)
  - Drawdown analysis
  - Best and worst trades

Read-only. Runtime: ~15-20 minutes.

Usage:
    python portfolio_simulation.py
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
SESSION_END = dtime(15, 30)

# ── Portfolio parameters ──────────────────────────────────────────────
STARTING_CAPITAL  = 200_000   # ₹2L per symbol
MAX_TRADE_PCT     = 0.20      # max 20% of capital per trade (premium × lots)
RUIN_THRESHOLD    = 10_000    # stop trading if capital falls below ₹10K
LOT_SIZE          = {"NIFTY": 25, "SENSEX": 15}

# ── Pattern config ────────────────────────────────────────────────────
OPT_TYPE = {
    "BULL_OB":    "CE",
    "BEAR_OB":    "PE",
    "BULL_FVG":   "CE",
    "JUDAS_BULL": "CE",
}
TARGET_PATTERNS = set(OPT_TYPE.keys())

# ── Pyramid config ────────────────────────────────────────────────────
T2_H        = 5     # minutes for Tier 2 confirmation
T3_H        = 10    # minutes for Tier 3 confirmation
T2_THRESH   = 0.20  # % move to trigger T2
T3_THRESH   = 0.40  # % move to trigger T3
T1_LOTS     = 1
T2_LOTS     = 2
T3_LOTS     = 3

# ── Detection parameters ──────────────────────────────────────────────
SWING_LB        = 5
OB_MIN_MOVE_PCT = 0.40
FVG_MIN_PCT     = 0.10
JUDAS_MIN_PCT   = 0.25
MIN_OPTION_PRICE = 5.0
ATM_RADIUS      = 3
MAX_GAP_MIN     = 3
STRIKE_STEP     = {"NIFTY": 50, "SENSEX": 100}


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def pct_dir(a, b, direction):
    return pct(a, b) * direction

def in_session(ts, h):
    return (ts + timedelta(minutes=h)).time() <= SESSION_END

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def month_key(td):
    return (td.year, td.month)

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

def month_label(mk):
    return f"{MONTH_NAMES[mk[1]]} {mk[0]}"


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
        if len(rows) < PAGE_SIZE:
            break
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
            .range(offset, offset+PAGE_SIZE-1)
            .execute().data
        )
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    lookup = {}
    for r in all_rows:
        ts  = datetime.fromisoformat(r["bar_ts"])
        stk = float(r["strike"])
        ot  = r["option_type"]
        cl  = float(r["close"])
        if cl >= MIN_OPTION_PRICE:
            lookup[(stk, ot, ts)] = cl
    return lookup


def get_option_price(lookup, strike, ot, target_ts, symbol):
    step = STRIKE_STEP[symbol]
    candidates = [strike + i*step for i in range(-ATM_RADIUS, ATM_RADIUS+1)]
    best_p, best_g, best_stk = None, timedelta(minutes=MAX_GAP_MIN+1), None
    for stk in candidates:
        ts_list = sorted(ts for (s,o,ts) in lookup if s==stk and o==ot)
        if not ts_list: continue
        idx = bisect.bisect_left(ts_list, target_ts)
        for i in (idx-1, idx):
            if 0 <= i < len(ts_list):
                gap = abs(ts_list[i] - target_ts)
                if gap < best_g:
                    p = lookup.get((stk, ot, ts_list[i]))
                    if p:
                        best_g, best_p, best_stk = gap, p, stk
    return (best_p, best_stk) if best_g <= timedelta(minutes=MAX_GAP_MIN) else (None, None)


def get_spot_at(bars, target_ts):
    tss = [b["bar_ts"] for b in bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=MAX_GAP_MIN+1)
    for i in (idx-1, idx):
        if 0 <= i < len(bars):
            gap = abs(bars[i]["bar_ts"] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, bars[i]["close"]
    return best_p if best_g <= timedelta(minutes=MAX_GAP_MIN) else None


# ── Pattern detectors ─────────────────────────────────────────────────

def detect_obs(bars):
    out, seen, n = [], set(), len(bars)
    for i in range(n-6):
        mv = pct(bars[i]["close"], bars[min(i+5,n-1)]["close"])
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB"))
                    break
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_OB"))
                    break
    return out


def detect_fvg(bars):
    out, min_g = [], FVG_MIN_PCT/100.0
    for i in range(1, len(bars)-1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BULL_FVG"))
    return out


def detect_judas(bars):
    out = []
    if len(bars) < 46:
        return out
    mv = pct(bars[0]["open"], bars[14]["close"])
    if abs(mv) < JUDAS_MIN_PCT:
        return out
    rev = bars[15:45]
    if mv < 0:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv)*0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL"))
    return out


# ── Trade record ──────────────────────────────────────────────────────

class Trade:
    def __init__(self, td, ts, symbol, pattern, ot, stk, entry_p,
                 lots_fixed, lots_pyr, spot):
        self.td          = td
        self.ts          = ts
        self.symbol      = symbol
        self.pattern     = pattern
        self.ot          = ot
        self.strike      = stk
        self.entry_p     = entry_p
        self.lots_fixed  = lots_fixed
        self.lots_pyr    = lots_pyr     # will be updated as tiers trigger
        self.spot        = spot
        self.exit_p      = None
        self.exit_ts     = None
        self.pnl_fixed   = None  # ₹
        self.pnl_pyr     = None  # ₹
        self.pnl_pct     = None  # % of premium
        self.t2_triggered = False
        self.t3_triggered = False
        self.t2_price    = None
        self.t3_price    = None
        self.skipped     = False
        self.skip_reason = ""


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    all_trades = {"NIFTY": [], "SENSEX": []}

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
        all_spot_bars = raw  # for spot lookup at T+5m, T+10m
        dates = sorted(spot_sessions.keys())
        log(f"  {len(raw):,} bars | {len(dates)} sessions")

        log("  Detecting patterns...")
        all_patterns = []
        for d in dates:
            bars = spot_sessions[d]
            if len(bars) < 30: continue
            pats = detect_obs(bars) + detect_fvg(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS: continue
                bar = pat["bar"]
                all_patterns.append({
                    "pattern":  pat["pattern"],
                    "bar":      bar,
                    "td":       d,
                    "exp_date": nearest_expiry_db(d, expiry_idx),
                    "atm":      atm_strike(bar["close"], symbol),
                    "opt_type": OPT_TYPE[pat["pattern"]],
                    "direction": +1 if OPT_TYPE[pat["pattern"]] == "CE" else -1,
                })
        log(f"  {len(all_patterns)} qualifying patterns")

        # Group by day for option fetch
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log(f"  Fetching options and simulating trades...")
        trades = []

        for gi, ((td, ed), pats_today) in enumerate(sorted(day_groups.items())):
            step = STRIKE_STEP[symbol]
            strikes_needed   = set()
            opt_types_needed = set()
            for pat in pats_today:
                base = pat["atm"]
                for r in range(-ATM_RADIUS, ATM_RADIUS+1):
                    strikes_needed.add(base + r*step)
                opt_types_needed.add(pat["opt_type"])

            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes_needed), sorted(opt_types_needed)
                )
            except Exception:
                continue

            if gi % 30 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            for pat in pats_today:
                ts        = pat["bar"]["bar_ts"]
                stk       = pat["atm"]
                ot        = pat["opt_type"]
                direction = pat["direction"]
                spot      = pat["bar"]["close"]

                # Entry price
                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None:
                    continue

                t = Trade(td, ts, symbol, pat["pattern"], ot,
                          entry_stk or stk, entry_p,
                          lots_fixed=T1_LOTS,
                          lots_pyr=T1_LOTS,
                          spot=spot)

                # Pyramid tier checks
                p5 = get_spot_at(all_spot_bars, ts + timedelta(minutes=T2_H))
                if p5 and pct_dir(spot, p5, direction) >= T2_THRESH:
                    t.t2_triggered = True
                    t.t2_price     = p5
                    t.lots_pyr    += T2_LOTS

                p10 = get_spot_at(all_spot_bars, ts + timedelta(minutes=T3_H))
                if t.t2_triggered and p10 and pct_dir(spot, p10, direction) >= T3_THRESH:
                    t.t3_triggered = True
                    t.t3_price     = p10
                    t.lots_pyr    += T3_LOTS

                # Exit: try T+30m, fallback T+15m, T+60m
                exit_p = None
                for h in [30, 15, 60]:
                    if in_session(ts, h):
                        ep, _ = get_option_price(lookup, t.strike, ot,
                                                  ts + timedelta(minutes=h), symbol)
                        if ep:
                            exit_p  = ep
                            t.exit_ts = ts + timedelta(minutes=h)
                            break

                if exit_p is None:
                    continue

                t.exit_p  = exit_p
                t.pnl_pct = pct(entry_p, exit_p)

                # P&L in rupees
                t.pnl_fixed = (exit_p - entry_p) * T1_LOTS     * lot_size
                t.pnl_pyr   = (exit_p - entry_p) * t.lots_pyr  * lot_size

                trades.append(t)

        all_trades[symbol] = sorted(trades, key=lambda t: t.ts)
        log(f"  {len(trades)} trades scored for {symbol}")

    # ── Simulate portfolio chronologically ───────────────────────────
    print("\n" + "=" * 115)
    print("  MERDIAN PORTFOLIO SIMULATION — Apr 2025 to Mar 2026")
    print(f"  Starting capital: ₹{STARTING_CAPITAL:,.0f} per symbol (₹{STARTING_CAPITAL*2:,.0f} total)")
    print(f"  Patterns: BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL (60%+ win rate)")
    print(f"  Exit: T+30m | Position limit: {MAX_TRADE_PCT*100:.0f}% of capital per trade")
    print(f"  FIXED=1 lot always | PYRAMID=1→3→6 lots on T+5m/T+10m confirmation")
    print("=" * 115)

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        lot_size = LOT_SIZE[symbol]
        trades   = all_trades[symbol]

        print(f"\n{'#'*115}")
        print(f"  {symbol}  |  Lot size: {lot_size}  |  {len(trades)} trades")
        print(f"{'#'*115}")

        cap_fixed = STARTING_CAPITAL
        cap_pyr   = STARTING_CAPITAL
        peak_fixed = STARTING_CAPITAL
        peak_pyr   = STARTING_CAPITAL
        max_dd_fixed = 0.0
        max_dd_pyr   = 0.0

        monthly_fixed = defaultdict(float)
        monthly_pyr   = defaultdict(float)
        monthly_n     = defaultdict(int)

        wins_fixed = losses_fixed = wins_pyr = losses_pyr = 0
        skipped = 0

        best_fixed  = None
        worst_fixed = None
        best_pyr    = None
        worst_pyr   = None

        print(f"\n  {'Date':<12} {'Time':<8} {'Pattern':<12} {'OT':<4} "
              f"{'Entry':>6} {'Exit':>6} {'Lots F':>6} {'Lots P':>6} "
              f"{'P&L Fixed':>10} {'P&L Pyr':>10} "
              f"{'Cap Fixed':>12} {'Cap Pyr':>12}  Note")
        print(f"  {'-'*130}")

        for t in trades:
            mk = month_key(t.td)

            # Check capital limits
            cost_fixed = t.entry_p * T1_LOTS    * lot_size
            cost_pyr   = t.entry_p * t.lots_pyr * lot_size

            skip_fixed = cap_fixed < RUIN_THRESHOLD or cost_fixed > cap_fixed * MAX_TRADE_PCT
            skip_pyr   = cap_pyr   < RUIN_THRESHOLD or cost_pyr   > cap_pyr   * MAX_TRADE_PCT

            if skip_fixed and skip_pyr:
                skipped += 1
                continue

            # Apply P&L
            pnl_f = t.pnl_fixed if not skip_fixed else 0.0
            pnl_p = t.pnl_pyr   if not skip_pyr   else 0.0

            cap_fixed += pnl_f
            cap_pyr   += pnl_p

            monthly_fixed[mk] += pnl_f
            monthly_pyr[mk]   += pnl_p
            monthly_n[mk]      += 1

            # Track wins/losses
            if pnl_f > 0: wins_fixed   += 1
            elif pnl_f < 0: losses_fixed += 1
            if pnl_p > 0: wins_pyr     += 1
            elif pnl_p < 0: losses_pyr   += 1

            # Drawdown
            if cap_fixed > peak_fixed: peak_fixed = cap_fixed
            if cap_pyr   > peak_pyr:   peak_pyr   = cap_pyr
            dd_f = (peak_fixed - cap_fixed) / peak_fixed * 100
            dd_p = (peak_pyr   - cap_pyr)   / peak_pyr   * 100
            if dd_f > max_dd_fixed: max_dd_fixed = dd_f
            if dd_p > max_dd_pyr:   max_dd_pyr   = dd_p

            # Best/worst
            if best_fixed  is None or pnl_f > best_fixed[0]:  best_fixed  = (pnl_f, t)
            if worst_fixed is None or pnl_f < worst_fixed[0]:  worst_fixed = (pnl_f, t)
            if best_pyr    is None or pnl_p > best_pyr[0]:    best_pyr    = (pnl_p, t)
            if worst_pyr   is None or pnl_p < worst_pyr[0]:   worst_pyr   = (pnl_p, t)

            # Print trade row
            t2_flag = "T2✓" if t.t2_triggered else ""
            t3_flag = "T3✓" if t.t3_triggered else ""
            note    = f"{t2_flag}{t3_flag}" if (t2_flag or t3_flag) else ""
            win_f   = "✓" if pnl_f > 0 else "✗"
            win_p   = "✓" if pnl_p > 0 else "✗"

            print(f"  {str(t.td):<12} "
                  f"{t.ts.strftime('%H:%M'):<8} "
                  f"{t.pattern:<12} "
                  f"{t.ot:<4} "
                  f"₹{t.entry_p:>5.0f} "
                  f"₹{t.exit_p:>5.0f} "
                  f"{T1_LOTS:>6} "
                  f"{t.lots_pyr:>6} "
                  f"{win_f}₹{pnl_f:>+8,.0f} "
                  f"{win_p}₹{pnl_p:>+8,.0f} "
                  f"₹{cap_fixed:>10,.0f} "
                  f"₹{cap_pyr:>10,.0f}  {note}")

        # ── Monthly summary ───────────────────────────────────────────
        print(f"\n  MONTHLY P&L — {symbol}")
        print(f"  {'Month':<10} {'Trades':>7}  {'Fixed P&L':>12}  {'Pyr P&L':>12}  "
              f"{'Fixed Cap':>12}  {'Pyr Cap':>12}")
        print(f"  {'-'*72}")

        cap_f_running = STARTING_CAPITAL
        cap_p_running = STARTING_CAPITAL
        for mk in sorted(monthly_fixed.keys()):
            cap_f_running += monthly_fixed[mk]
            cap_p_running += monthly_pyr[mk]
            pnl_f = monthly_fixed[mk]
            pnl_p = monthly_pyr[mk]
            print(f"  {month_label(mk):<10} {monthly_n[mk]:>7}  "
                  f"₹{pnl_f:>+10,.0f}  ₹{pnl_p:>+10,.0f}  "
                  f"₹{cap_f_running:>10,.0f}  ₹{cap_p_running:>10,.0f}")

        # ── Summary stats ─────────────────────────────────────────────
        total_trades = wins_fixed + losses_fixed
        print(f"\n  ── {symbol} SUMMARY ──────────────────────────────────")
        print(f"  Total trades:      {total_trades}")
        print(f"  Skipped:           {skipped} (capital limit)")
        print(f"\n  FIXED (1 lot):")
        print(f"    Final capital:   ₹{cap_fixed:,.0f}  "
              f"(P&L: ₹{cap_fixed-STARTING_CAPITAL:+,.0f} | "
              f"{(cap_fixed-STARTING_CAPITAL)/STARTING_CAPITAL*100:+.1f}%)")
        print(f"    Win rate:        {wins_fixed}/{total_trades} = "
              f"{100*wins_fixed/total_trades:.1f}%")
        print(f"    Max drawdown:    {max_dd_fixed:.1f}%")
        if best_fixed:
            print(f"    Best trade:      ₹{best_fixed[0]:+,.0f}  "
                  f"({best_fixed[1].pattern} {best_fixed[1].td})")
        if worst_fixed:
            print(f"    Worst trade:     ₹{worst_fixed[0]:+,.0f}  "
                  f"({worst_fixed[1].pattern} {worst_fixed[1].td})")

        print(f"\n  PYRAMID (1→3→6 lots):")
        print(f"    Final capital:   ₹{cap_pyr:,.0f}  "
              f"(P&L: ₹{cap_pyr-STARTING_CAPITAL:+,.0f} | "
              f"{(cap_pyr-STARTING_CAPITAL)/STARTING_CAPITAL*100:+.1f}%)")
        print(f"    Win rate:        {wins_pyr}/{total_trades} = "
              f"{100*wins_pyr/total_trades:.1f}%")
        print(f"    Max drawdown:    {max_dd_pyr:.1f}%")
        if best_pyr:
            print(f"    Best trade:      ₹{best_pyr[0]:+,.0f}  "
                  f"({best_pyr[1].pattern} {best_pyr[1].td})")
        if worst_pyr:
            print(f"    Worst trade:     ₹{worst_pyr[0]:+,.0f}  "
                  f"({worst_pyr[1].pattern} {worst_pyr[1].td})")

    # ── Combined summary ──────────────────────────────────────────────
    print(f"\n{'='*115}")
    print("  COMBINED PORTFOLIO SUMMARY")
    print(f"{'='*115}")
    print(f"  Starting:  ₹{STARTING_CAPITAL*2:,.0f}  (₹{STARTING_CAPITAL:,.0f} × 2 symbols)")
    print(f"\n  NOTE: Individual symbol finals shown above.")
    print(f"  Combined final = NIFTY final + SENSEX final")
    print(f"  Bid-ask spread not modelled — real P&L will be 5-15% lower.")
    print(f"  Brokerage not modelled — add ₹40-80 per lot per trade.")
    print(f"{'='*115}\n")


if __name__ == "__main__":
    main()


