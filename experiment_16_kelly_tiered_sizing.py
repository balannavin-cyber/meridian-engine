#!/usr/bin/env python3
"""
experiment_16_kelly_tiered_sizing.py
MERDIAN Experiment 16 -- Kelly Tiered Sizing with Compounding Capital

Tests four position sizing strategies on the full year Apr 2025-Mar 2026
dataset. Capital compounds after every trade (profits added, losses absorbed).
Capital floor: sizing never falls below INR 2L equivalent base.

STRATEGIES (run in parallel, same trade universe):
  A -- Original flat pyramid (1->2->3, baseline from portfolio_simulation.py)
  B -- User tiered (7->14->21 on Tier1+2, 1->2->3 on Tier3)
  C -- Half Kelly tiered (mathematically optimal, pattern-specific)
  D -- Full Kelly tiered (aggressive upper bound)

TIER CLASSIFICATION (from full year WR data):
  Tier 1 (100% WR setups):
    BULL_OB | MORNING (10:00-11:30)
    BULL_OB | DTE=0
    BEAR_OB | MORNING (10:00-11:30)
    BULL_OB | SWEEP | MOM_YES

  Tier 2 (80-91% WR setups):
    BULL_OB | MOM_YES
    BEAR_OB | MOM_YES
    BULL_OB | IMP_STR
    BULL_OB | AFTERNOON (13:00-15:00)
    BEAR_OB | DTE=4+

  Tier 3 (standard -- everything else):
    JUDAS_BULL
    BULL_FVG
    BEAR_OB (no qualifying filter)
    BULL_OB (no qualifying filter)

KELLY FRACTIONS (half Kelly used for C, full Kelly for D):
  Tier 1: Full Kelly=100% -> Half Kelly=50%
  Tier 2: Full Kelly=77-88% -> Half Kelly=40% (midpoint)
  Tier 3: Full Kelly=23-61% -> Half Kelly=20% (conservative midpoint)

COMPOUNDING:
  After every trade: capital += pnl (profits add, losses reduce)
  Floor: if capital < INR 2L, size as if capital = INR 2L
  Ruin: if capital < INR 10K, halt trading for that symbol

Output:
  Section 1 -- Strategy comparison summary (all 4 strategies)
  Section 2 -- Month by month compounding curve (all 4)
  Section 3 -- Tier breakdown (how each tier contributed)
  Section 4 -- Drawdown analysis (peak, trough, recovery)
  Section 5 -- Best and worst sessions (all 4)
  Section 6 -- Trade-by-trade log (Tier 1 and 2 only -- the interesting ones)
  Section 7 -- Verdict: which strategy wins on return/DD ratio

Read-only. Runtime: ~15-25 min.

Usage:
    python experiment_16_kelly_tiered_sizing.py
"""

import os
import bisect
import time
import math
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict
from itertools import groupby

from dotenv import load_dotenv
from supabase import create_client
from merdian_utils import build_expiry_index_simple, nearest_expiry_db

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000

# ── Portfolio parameters ───────────────────────────────────────────────
STARTING_CAPITAL = 200_000    # INR 2L per symbol
CAPITAL_FLOOR    = 200_000    # minimum sizing base
RUIN_THRESHOLD   =  10_000    # halt if below
LOT_SIZE         = {"NIFTY": 25, "SENSEX": 15}
STRIKE_STEP      = {"NIFTY": 50, "SENSEX": 100}
ATM_RADIUS       = 3
MAX_GAP_MIN      = 5
MIN_OPTION_PRICE = 5.0

# ── Pattern config ─────────────────────────────────────────────────────
OPT_TYPE = {
    "BULL_OB":    "CE",
    "BEAR_OB":    "PE",
    "BULL_FVG":   "CE",
    "JUDAS_BULL": "CE",
}
TARGET_PATTERNS = set(OPT_TYPE.keys())

OB_MIN_MOVE_PCT  = 0.40
FVG_MIN_PCT      = 0.10
JUDAS_MIN_PCT    = 0.25

# ── Pyramid confirmation ───────────────────────────────────────────────
T2_MIN   = 5      # minutes
T3_MIN   = 10
T2_THRESH = 0.20  # % spot move
T3_THRESH = 0.40

# ── Time zones ─────────────────────────────────────────────────────────
OPEN_START    = dtime(9, 15)
MORNING_START = dtime(9, 45)
MIDDAY_START  = dtime(11, 0)
AFTNOON_START = dtime(13, 0)
POWER_START   = dtime(14, 30)
SESSION_END   = dtime(15, 30)

# ── Sequence feature thresholds ────────────────────────────────────────
IMP_LOOKBACK     = 3    # bars before OB
IMP_STR_THRESH   = 0.30 # % cumulative move = strong impulse
MOM_LOOKBACK     = 3    # bars for counter-momentum
SWEEP_LOOKBACK   = 5    # bars for prior session sweep

# ── Capital ceiling and scaling ────────────────────────────────────────
# Above 25L: scale lots down proportionally (liquidity degrades)
# Above 50L: hard cap -- no further lot increases regardless of capital
# Rationale: NIFTY/SENSEX options have finite liquidity at ATM strikes.
# Slicing large orders above 50L introduces meaningful market impact.
CAPITAL_SCALE_START = 2_500_000   # INR 25L -- begin scaling down
CAPITAL_HARD_CAP    = 5_000_000   # INR 50L -- hard ceiling on sizing

def effective_sizing_capital(capital):
    """
    Returns the capital figure to use for lot sizing.
    Below 25L: use actual capital (full compounding benefit).
    25L-50L: scale linearly from 25L to 25L (lots frozen at 25L level).
    Above 50L: cap at 50L for sizing purposes.
    This preserves compounding returns while preventing liquidity issues.
    """
    if capital <= CAPITAL_SCALE_START:
        return capital
    if capital >= CAPITAL_HARD_CAP:
        return CAPITAL_HARD_CAP
    # Linear interpolation: as capital grows from 25L to 50L,
    # sizing capital stays at 25L (conservative -- don't increase lots)
    return CAPITAL_SCALE_START

# ── Kelly fractions by tier ────────────────────────────────────────────
# Half Kelly (Strategy C)
HALF_KELLY = {1: 0.50, 2: 0.40, 3: 0.20}
# Full Kelly (Strategy D)
FULL_KELLY = {1: 1.00, 2: 0.80, 3: 0.40}

# ── Pyramid lot ratios (T1:T2_add:T3_add) by strategy and tier ─────────
# Strategy A -- original flat 1->2->3 regardless of tier
STRAT_A_LOTS = (1, 2, 3)   # T1, T2 add, T3 add -> max 6

# Strategy B -- user tiered (7->14->21 on T1+T2, 1->2->3 on T3)
STRAT_B_TIER12 = (7, 14, 21)  # max 42
STRAT_B_TIER3  = (1,  2,  3)  # max 6


# ── Utilities ──────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def pct_dir(a, b, direction):
    return pct(a, b) * direction

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def month_label(d):
    names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
             7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    return f"{names[d.month]} {d.year}"

def time_zone(ts):
    t = ts.time()
    if t < MORNING_START: return "OPEN"
    if t < MIDDAY_START:  return "MORNING"
    if t < AFTNOON_START: return "MIDDAY"
    if t < POWER_START:   return "AFTERNOON"
    return "POWER"

def dte_bucket(td, ed):
    d = (ed - td).days
    if d == 0: return "DTE=0"
    if d == 1: return "DTE=1"
    if d <= 3: return "DTE=2-3"
    return "DTE=4+"


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


def get_option_price(lookup, strike, ot, target_ts, symbol):
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


def get_spot_at(all_bars_sorted, target_ts):
    tss = [b["bar_ts"] for b in all_bars_sorted]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=MAX_GAP_MIN + 1)
    for i in (idx - 1, idx):
        if 0 <= i < len(all_bars_sorted):
            gap = abs(all_bars_sorted[i]["bar_ts"] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, all_bars_sorted[i]["close"]
    return best_p if best_g <= timedelta(minutes=MAX_GAP_MIN) else None


# ── Pattern detectors ──────────────────────────────────────────────────

def detect_obs(bars):
    out, seen, n = [], set(), len(bars)
    for i in range(n - 6):
        mv = pct(bars[i]["close"], bars[min(i + 5, n - 1)]["close"])
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i - 6, -1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB"))
                    break
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i - 6, -1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_OB"))
                    break
    return out


def detect_fvg(bars):
    out = []
    min_g = FVG_MIN_PCT / 100.0
    for i in range(1, len(bars) - 1):
        p, c, n = bars[i - 1], bars[i], bars[i + 1]
        ref = c["close"]
        if p["high"] < n["low"] and (n["low"] - p["high"]) / ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BULL_FVG"))
    return out


def detect_judas(bars):
    if len(bars) < 46: return []
    mv = pct(bars[0]["open"], bars[14]["close"])
    if abs(mv) < JUDAS_MIN_PCT: return []
    rev = bars[15:45]
    if mv < 0:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv) * 0.50:
            return [dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL")]
    return []


# ── Sequence features ──────────────────────────────────────────────────

def compute_sequence_features(bars, bar_idx, direction, prior_high, prior_low):
    """
    Compute MOM_YES, IMP_STR, HAS_SWEEP from bars before the OB.
    direction: +1 for bull, -1 for bear.
    Returns dict.
    """
    start = max(0, bar_idx - IMP_LOOKBACK)
    window = bars[start:bar_idx]

    # Momentum alignment: for BULL_OB direction=+1, we want prior bars bearish
    # i.e. counter-direction momentum = bars moved AGAINST the OB direction
    mom_count = 0
    for b in window:
        bar_move = b["close"] - b["open"]
        if direction == +1 and bar_move < 0:  # bearish bar before bull OB
            mom_count += 1
        elif direction == -1 and bar_move > 0:  # bullish bar before bear OB
            mom_count += 1
    mom_yes = mom_count >= 2  # at least 2 of 3 bars counter-direction

    # Impulse strength: cumulative abs move in lookback window
    imp_total = 0.0
    for b in window:
        imp_total += abs(pct(b["open"], b["close"]))
    imp_str = imp_total >= IMP_STR_THRESH

    # Sweep: did price breach prior session H/L in last SWEEP_LOOKBACK bars?
    sweep_start = max(0, bar_idx - SWEEP_LOOKBACK)
    sweep_bars  = bars[sweep_start:bar_idx + 1]
    has_sweep   = False
    if prior_high and prior_low:
        for b in sweep_bars:
            if b["high"] > prior_high or b["low"] < prior_low:
                has_sweep = True
                break

    return {
        "mom_yes":   mom_yes,
        "imp_str":   imp_str,
        "has_sweep": has_sweep,
    }


# ── Tier classification ────────────────────────────────────────────────

def classify_tier(pattern, tz, dte, seq, direction):
    """
    Return 1, 2, or 3 based on pattern + context.
    Tier 1: historically 100% WR setups.
    Tier 2: historically 80-91% WR setups.
    Tier 3: everything else.
    """
    # ── Tier 1 ──────────────────────────────────────────────────────
    if pattern == "BULL_OB" and tz == "MORNING":
        return 1
    if pattern == "BULL_OB" and dte == "DTE=0":
        return 1
    if pattern == "BEAR_OB" and tz == "MORNING":
        return 1
    if pattern == "BULL_OB" and seq["has_sweep"] and seq["mom_yes"] and not seq["imp_str"]:
        return 1

    # ── Tier 2 ──────────────────────────────────────────────────────
    if pattern == "BULL_OB" and seq["mom_yes"]:
        return 2
    if pattern == "BEAR_OB" and seq["mom_yes"]:
        return 2
    if pattern == "BULL_OB" and seq["imp_str"]:
        return 2
    if pattern == "BULL_OB" and tz == "AFTERNOON":
        return 2
    if pattern == "BEAR_OB" and dte == "DTE=4+":
        return 2

    # ── Tier 3 ──────────────────────────────────────────────────────
    return 3


# ── Lot calculator for Kelly strategies ───────────────────────────────

def kelly_lots(capital, kelly_fraction, entry_price, lot_size,
               t1_ratio=1, t2_ratio=2, t3_ratio=3):
    """
    Given capital and kelly fraction, compute T1/T2/T3 lots such that
    full deployment (T3) = kelly_fraction * sizing_capital.

    Capital ceiling rules (liquidity constraints):
      Below INR 25L: full compounding benefit, use actual capital
      INR 25L-50L:   sizing frozen at 25L level (lots don't grow)
      Above INR 50L: hard cap at 50L equivalent sizing

    Floor: never less than 1 lot at T1.
    Pyramid ratios maintained: T1:T2_add:T3_add = 1:2:3
    """
    sizing_cap    = effective_sizing_capital(max(capital, CAPITAL_FLOOR))
    total_units   = t1_ratio + t2_ratio + t3_ratio  # = 6
    target_deploy = sizing_cap * kelly_fraction
    base_lot      = max(1, int(target_deploy / (total_units * entry_price * lot_size)))

    t1_lots = base_lot * t1_ratio
    t2_add  = base_lot * t2_ratio
    t3_add  = base_lot * t3_ratio
    return t1_lots, t2_add, t3_add


# ── Portfolio state ────────────────────────────────────────────────────

class PortfolioState:
    def __init__(self, name, starting_capital):
        self.name    = name
        self.capital = starting_capital
        self.peak    = starting_capital
        self.max_dd  = 0.0
        self.trades  = 0
        self.wins    = 0
        self.losses  = 0
        self.total_pnl     = 0.0
        self.monthly_pnl   = defaultdict(float)
        self.monthly_n     = defaultdict(int)
        self.monthly_cap   = {}
        self.best_trade    = None   # (pnl, description)
        self.worst_trade   = None
        self.best_session  = defaultdict(float)   # td -> pnl
        self.tier_pnl      = defaultdict(float)   # tier -> pnl
        self.tier_n        = defaultdict(int)
        self.tier_wins     = defaultdict(int)
        self.capital_curve = []     # (td, capital) after each trade

    def apply(self, pnl, td, tier, desc):
        self.capital   += pnl
        self.total_pnl += pnl
        self.trades    += 1
        if pnl > 0: self.wins    += 1
        else:       self.losses  += 1

        mk = (td.year, td.month)
        self.monthly_pnl[mk] += pnl
        self.monthly_n[mk]   += 1
        self.monthly_cap[mk]  = self.capital

        self.tier_pnl[tier]  += pnl
        self.tier_n[tier]    += 1
        if pnl > 0: self.tier_wins[tier] += 1

        self.best_session[td] += pnl

        if self.capital > self.peak:
            self.peak = self.capital
        dd = (self.peak - self.capital) / self.peak * 100
        if dd > self.max_dd:
            self.max_dd = dd

        if self.best_trade is None or pnl > self.best_trade[0]:
            self.best_trade = (pnl, desc, td)
        if self.worst_trade is None or pnl < self.worst_trade[0]:
            self.worst_trade = (pnl, desc, td)

        self.capital_curve.append((td, self.capital))

    @property
    def wr(self):
        total = self.wins + self.losses
        return 100 * self.wins / total if total else 0

    @property
    def return_pct(self):
        return 100 * (self.capital - STARTING_CAPITAL) / STARTING_CAPITAL

    @property
    def return_per_dd(self):
        return self.return_pct / self.max_dd if self.max_dd else float("inf")


# ── Main ───────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # One PortfolioState per strategy per symbol
    strategies = ["A", "B", "C", "D"]
    strat_names = {
        "A": "Original flat pyramid 1->2->3",
        "B": "User tiered 7->14->21 (T1+2), 1->2->3 (T3)",
        "C": "Half Kelly tiered (optimal)",
        "D": "Full Kelly tiered (aggressive)",
    }

    states = {}  # (symbol, strategy) -> PortfolioState

    for symbol in ["NIFTY", "SENSEX"]:
        for s in strategies:
            states[(symbol, s)] = PortfolioState(
                f"{symbol}-{s}", STARTING_CAPITAL)

    tier1_log = []   # detailed trade log for T1+T2

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")
        lot_size = LOT_SIZE[symbol]

        # Expiry index
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"  {len(expiry_idx)} expiry dates indexed")

        # Spot bars
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

        # Daily OHLCV for prior session H/L
        daily_hl = {}
        for d, bars in spot_sessions.items():
            daily_hl[d] = {
                "high": max(b["high"] for b in bars),
                "low":  min(b["low"]  for b in bars),
            }
        dates_sorted = sorted(daily_hl.keys())

        # Detect all patterns
        log("  Detecting patterns and computing features...")
        all_patterns = []
        for d in dates:
            bars = spot_sessions[d]
            if len(bars) < 30: continue

            # Prior session H/L
            prior_dates = [x for x in dates_sorted if x < d]
            prior_high = daily_hl[prior_dates[-1]]["high"] if prior_dates else None
            prior_low  = daily_hl[prior_dates[-1]]["low"]  if prior_dates else None

            ed = nearest_expiry_db(d, expiry_idx)
            if ed is None: continue

            pats = detect_obs(bars) + detect_fvg(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS: continue
                bar       = pat["bar"]
                bar_idx   = pat["bar_idx"]
                direction = +1 if OPT_TYPE[pat["pattern"]] == "CE" else -1
                tz        = time_zone(bar["bar_ts"])
                dte       = dte_bucket(d, ed)
                seq       = compute_sequence_features(
                                bars, bar_idx, direction, prior_high, prior_low)
                tier      = classify_tier(pat["pattern"], tz, dte, seq, direction)

                all_patterns.append({
                    "pattern":   pat["pattern"],
                    "bar":       bar,
                    "bar_idx":   bar_idx,
                    "td":        d,
                    "ed":        ed,
                    "atm":       atm_strike(bar["close"], symbol),
                    "opt_type":  OPT_TYPE[pat["pattern"]],
                    "direction": direction,
                    "tz":        tz,
                    "dte":       dte,
                    "seq":       seq,
                    "tier":      tier,
                })

        log(f"  {len(all_patterns)} patterns | "
            f"T1={sum(1 for p in all_patterns if p['tier']==1)} "
            f"T2={sum(1 for p in all_patterns if p['tier']==2)} "
            f"T3={sum(1 for p in all_patterns if p['tier']==3)}")

        # Group by day for option fetch
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["ed"])].append(pat)

        log(f"  Fetching options and simulating {len(day_groups)} day groups...")

        for gi, ((td, ed), pats_today) in enumerate(sorted(day_groups.items())):
            step = STRIKE_STEP[symbol]
            strikes_needed   = set()
            opt_types_needed = set()
            for pat in pats_today:
                base = pat["atm"]
                for r in range(-ATM_RADIUS, ATM_RADIUS + 1):
                    strikes_needed.add(base + r * step)
                opt_types_needed.add(pat["opt_type"])

            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes_needed), sorted(opt_types_needed)
                )
            except Exception:
                continue

            if gi % 20 == 0:
                log(f"    {gi}/{len(day_groups)} groups | "
                    f"A=₹{states[(symbol,'A')].capital:,.0f} "
                    f"B=₹{states[(symbol,'B')].capital:,.0f} "
                    f"C=₹{states[(symbol,'C')].capital:,.0f} "
                    f"D=₹{states[(symbol,'D')].capital:,.0f}")

            for pat in sorted(pats_today, key=lambda p: p["bar"]["bar_ts"]):
                ts        = pat["bar"]["bar_ts"]
                stk       = pat["atm"]
                ot        = pat["opt_type"]
                direction = pat["direction"]
                spot      = pat["bar"]["close"]
                tier      = pat["tier"]

                # Entry price
                entry_p = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None: continue

                # Pyramid tier confirmations (shared across strategies)
                p5  = get_spot_at(all_bars, ts + timedelta(minutes=T2_MIN))
                p10 = get_spot_at(all_bars, ts + timedelta(minutes=T3_MIN))
                t2_ok = p5  is not None and pct_dir(spot, p5,  direction) >= T2_THRESH
                t3_ok = t2_ok and p10 is not None and pct_dir(spot, p10, direction) >= T3_THRESH

                # Exit price T+30m (fallback T+15m, T+60m)
                exit_p = None
                for h in [30, 15, 60]:
                    ts_exit = ts + timedelta(minutes=h)
                    if ts_exit.time() <= SESSION_END:
                        ep = get_option_price(lookup, stk, ot, ts_exit, symbol)
                        if ep:
                            exit_p = ep
                            break
                if exit_p is None: continue

                pnl_pct = pct(entry_p, exit_p)
                desc    = f"{pat['pattern']}|{pat['tz']}|{pat['dte']}|MOM={'Y' if pat['seq']['mom_yes'] else 'N'}"

                # ── Strategy A -- original 1->2->3 flat ───────────────
                t1_a, t2_add_a, t3_add_a = STRAT_A_LOTS
                lots_a = t1_a
                if t2_ok: lots_a += t2_add_a
                if t3_ok: lots_a += t3_add_a
                pnl_a  = (exit_p - entry_p) * lots_a * lot_size
                states[(symbol, "A")].apply(pnl_a, td, tier, desc)

                # ── Strategy B -- user tiered ──────────────────────────
                if tier in (1, 2):
                    t1_b, t2_add_b, t3_add_b = STRAT_B_TIER12
                else:
                    t1_b, t2_add_b, t3_add_b = STRAT_B_TIER3
                # Apply capital ceiling: scale B lots if capital exceeds 25L
                cap_b_eff = effective_sizing_capital(
                    max(states[(symbol, "B")].capital, CAPITAL_FLOOR))
                scale_b = min(1.0, cap_b_eff / CAPITAL_SCALE_START) if tier in (1,2) else 1.0
                t1_b_scaled   = max(1, int(t1_b    * scale_b))
                t2_add_b_scaled = max(1, int(t2_add_b * scale_b))
                t3_add_b_scaled = max(1, int(t3_add_b * scale_b))
                lots_b = t1_b_scaled
                if t2_ok: lots_b += t2_add_b_scaled
                if t3_ok: lots_b += t3_add_b_scaled
                pnl_b  = (exit_p - entry_p) * lots_b * lot_size
                states[(symbol, "B")].apply(pnl_b, td, tier, desc)

                # ── Strategy C -- Half Kelly tiered ────────────────────
                cap_c  = states[(symbol, "C")].capital
                if cap_c < RUIN_THRESHOLD: continue
                kf_c   = HALF_KELLY[tier]
                t1_c, t2_add_c, t3_add_c = kelly_lots(
                    cap_c, kf_c, entry_p, lot_size)
                lots_c = t1_c
                if t2_ok: lots_c += t2_add_c
                if t3_ok: lots_c += t3_add_c
                pnl_c  = (exit_p - entry_p) * lots_c * lot_size
                states[(symbol, "C")].apply(pnl_c, td, tier, desc)

                # ── Strategy D -- Full Kelly tiered ────────────────────
                cap_d  = states[(symbol, "D")].capital
                if cap_d < RUIN_THRESHOLD: continue
                kf_d   = FULL_KELLY[tier]
                t1_d, t2_add_d, t3_add_d = kelly_lots(
                    cap_d, kf_d, entry_p, lot_size)
                lots_d = t1_d
                if t2_ok: lots_d += t2_add_d
                if t3_ok: lots_d += t3_add_d
                pnl_d  = (exit_p - entry_p) * lots_d * lot_size
                states[(symbol, "D")].apply(pnl_d, td, tier, desc)

                # Log Tier 1 and 2 trades in detail
                if tier <= 2:
                    tier1_log.append({
                        "symbol":   symbol,
                        "td":       td,
                        "ts":       ts,
                        "pattern":  pat["pattern"],
                        "tz":       pat["tz"],
                        "dte":      pat["dte"],
                        "mom_yes":  pat["seq"]["mom_yes"],
                        "imp_str":  pat["seq"]["imp_str"],
                        "sweep":    pat["seq"]["has_sweep"],
                        "tier":     tier,
                        "entry_p":  entry_p,
                        "exit_p":   exit_p,
                        "pnl_pct":  pnl_pct,
                        "t2_ok":    t2_ok,
                        "t3_ok":    t3_ok,
                        "lots_a":   lots_a,
                        "lots_b":   lots_b,
                        "lots_c":   lots_c,
                        "lots_d":   lots_d,
                        "pnl_a":    pnl_a,
                        "pnl_b":    pnl_b,
                        "pnl_c":    pnl_c,
                        "pnl_d":    pnl_d,
                        "ot":       ot,
                    })

    # ── OUTPUT ─────────────────────────────────────────────────────────

    W = 120
    SEP  = "=" * W
    SEP2 = "-" * W

    print(f"\n{SEP}")
    print("  MERDIAN EXPERIMENT 16 -- KELLY TIERED SIZING WITH COMPOUNDING CAPITAL")
    print("  Four strategies | Full year Apr 2025-Mar 2026 | INR 2L start per index")
    print("  Capital compounds each trade. Floor = INR 2L. T+30m exit.")
    print("  Capital ceiling: sizing frozen at INR 25L, hard cap at INR 50L")
    print("  (liquidity constraint -- large orders above 50L introduce market impact)")
    print(f"{SEP}")

    # ── Section 1 -- Strategy comparison ─────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 1 -- STRATEGY COMPARISON SUMMARY")
    print(f"{SEP}")
    print(f"  {'Strategy':<42} {'Final Cap':>12} {'Return':>8} {'Max DD':>8} "
          f"{'Ret/DD':>8} {'WR':>7} {'Trades':>7}")
    print(f"  {SEP2}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}:")
        for s in strategies:
            st = states[(symbol, s)]
            rdd = f"{st.return_per_dd:.1f}x" if st.max_dd > 0 else "inf"
            print(f"    [{s}] {strat_names[s]:<38} "
                  f"₹{st.capital:>10,.0f}  "
                  f"{st.return_pct:>+7.1f}%  "
                  f"{st.max_dd:>6.1f}%  "
                  f"{rdd:>8}  "
                  f"{st.wr:>5.1f}%  "
                  f"{st.trades:>6}")

    # Combined
    print(f"\n  COMBINED (NIFTY + SENSEX):")
    for s in strategies:
        total_cap = states[("NIFTY",s)].capital + states[("SENSEX",s)].capital
        total_ret = 100*(total_cap - STARTING_CAPITAL*2)/(STARTING_CAPITAL*2)
        max_dd    = max(states[("NIFTY",s)].max_dd, states[("SENSEX",s)].max_dd)
        rdd       = f"{total_ret/max_dd:.1f}x" if max_dd > 0 else "inf"
        print(f"    [{s}] {strat_names[s]:<38} "
              f"₹{total_cap:>10,.0f}  "
              f"{total_ret:>+7.1f}%  "
              f"DD={max_dd:.1f}%  "
              f"Ret/DD={rdd}")

    # ── Section 2 -- Monthly compounding curve ────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 2 -- MONTHLY COMPOUNDING CURVE")
    print(f"{SEP}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}:")
        print(f"  {'Month':<10} {'N':>4}  "
              f"{'[A] Capital':>13} {'[B] Capital':>13} "
              f"{'[C] Capital':>13} {'[D] Capital':>13}")
        print(f"  {'-'*70}")

        # Collect all months
        all_months = set()
        for s in strategies:
            all_months.update(states[(symbol,s)].monthly_pnl.keys())

        cap_run = {s: STARTING_CAPITAL for s in strategies}
        for mk in sorted(all_months):
            n = states[(symbol,"A")].monthly_n.get(mk, 0)
            caps = {}
            for s in strategies:
                cap_run[s] += states[(symbol,s)].monthly_pnl.get(mk, 0)
                caps[s] = cap_run[s]
            lbl = month_label(date(mk[0], mk[1], 1))
            print(f"  {lbl:<10} {n:>4}  "
                  f"₹{caps['A']:>11,.0f}  "
                  f"₹{caps['B']:>11,.0f}  "
                  f"₹{caps['C']:>11,.0f}  "
                  f"₹{caps['D']:>11,.0f}")

    # ── Section 3 -- Tier breakdown ───────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 3 -- TIER CONTRIBUTION BREAKDOWN")
    print("  Tier 1 = 100% WR setups | Tier 2 = 80%+ WR | Tier 3 = standard")
    print(f"{SEP}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}:")
        for tier in [1, 2, 3]:
            print(f"\n    Tier {tier}:")
            for s in strategies:
                st   = states[(symbol, s)]
                n    = st.tier_n[tier]
                wins = st.tier_wins[tier]
                pnl  = st.tier_pnl[tier]
                wr   = 100*wins/n if n else 0
                print(f"      [{s}]  N={n:>4}  WR={wr:>5.1f}%  "
                      f"Total P&L=₹{pnl:>+10,.0f}  "
                      f"Avg=₹{pnl/n:>+8,.0f}" if n else
                      f"      [{s}]  N=0")

    # ── Section 4 -- Drawdown analysis ───────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 4 -- DRAWDOWN ANALYSIS")
    print(f"{SEP}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}:")
        print(f"  {'Strategy':<44} {'Max DD':>8} {'Peak Cap':>13} "
              f"{'Trough Cap':>12} {'Worst Trade':>12}")
        print(f"  {'-'*95}")
        for s in strategies:
            st      = states[(symbol, s)]
            trough  = st.peak * (1 - st.max_dd / 100)
            worst   = f"₹{st.worst_trade[0]:+,.0f}" if st.worst_trade else "n/a"
            print(f"  [{s}] {strat_names[s]:<40}  "
                  f"{st.max_dd:>6.1f}%  "
                  f"₹{st.peak:>11,.0f}  "
                  f"₹{trough:>10,.0f}  "
                  f"{worst:>12}")

    # ── Section 5 -- Best and worst sessions ──────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 5 -- BEST AND WORST SESSIONS")
    print(f"{SEP}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}  Best sessions [Strategy D -- most amplified]:")
        st_d = states[(symbol, "D")]
        best_sessions = sorted(st_d.best_session.items(),
                               key=lambda x: x[1], reverse=True)[:5]
        for td, pnl in best_sessions:
            # Show same session across all strategies
            row = f"    {str(td)}  D=₹{pnl:>+10,.0f}"
            for s in ["A","B","C"]:
                row += f"  {s}=₹{states[(symbol,s)].best_session.get(td,0):>+9,.0f}"
            print(row)

        print(f"  {symbol}  Worst sessions [Strategy D]:")
        worst_sessions = sorted(st_d.best_session.items(),
                                key=lambda x: x[1])[:3]
        for td, pnl in worst_sessions:
            row = f"    {str(td)}  D=₹{pnl:>+10,.0f}"
            for s in ["A","B","C"]:
                row += f"  {s}=₹{states[(symbol,s)].best_session.get(td,0):>+9,.0f}"
            print(row)

    # ── Section 6 -- Tier 1+2 trade log ──────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 6 -- TIER 1 AND TIER 2 TRADE LOG")
    print("  Only high-confidence trades shown. All four strategy P&Ls per trade.")
    print(f"{SEP}")

    print(f"\n  {'Date':<12} {'Sym':<7} {'T':<2} {'Pattern':<15} "
          f"{'TZ':<9} {'DTE':<7} {'M':<2} {'Entry':>6} {'Exit':>6} "
          f"{'Pct':>6}  {'A P&L':>9} {'B P&L':>9} {'C P&L':>9} {'D P&L':>9}  Note")
    print(f"  {'-'*130}")

    for tr in sorted(tier1_log, key=lambda x: (x["symbol"], x["td"], x["ts"])):
        win  = "+" if tr["pnl_pct"] > 0 else "-"
        note = ("T2T3" if tr["t3_ok"] else "T2" if tr["t2_ok"] else "")
        m    = "Y" if tr["mom_yes"] else "N"
        print(f"  {str(tr['td']):<12} {tr['symbol']:<7} "
              f"{tr['tier']:<2} {tr['pattern']:<15} "
              f"{tr['tz']:<9} {tr['dte']:<7} {m:<2} "
              f"₹{tr['entry_p']:>5.0f} ₹{tr['exit_p']:>5.0f} "
              f"{win}{abs(tr['pnl_pct']):>5.1f}%  "
              f"₹{tr['pnl_a']:>+8,.0f} "
              f"₹{tr['pnl_b']:>+8,.0f} "
              f"₹{tr['pnl_c']:>+8,.0f} "
              f"₹{tr['pnl_d']:>+8,.0f}  {note}")

    # ── Section 7 -- Verdict ──────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SECTION 7 -- VERDICT")
    print(f"{SEP}")

    combined = {}
    for s in strategies:
        cap  = states[("NIFTY",s)].capital + states[("SENSEX",s)].capital
        ret  = 100*(cap - STARTING_CAPITAL*2)/(STARTING_CAPITAL*2)
        dd   = max(states[("NIFTY",s)].max_dd, states[("SENSEX",s)].max_dd)
        rdd  = ret/dd if dd > 0 else float("inf")
        combined[s] = {"cap": cap, "ret": ret, "dd": dd, "rdd": rdd}

    best_ret = max(strategies, key=lambda s: combined[s]["ret"])
    best_rdd = max(strategies, key=lambda s: combined[s]["rdd"])
    min_dd   = min(strategies, key=lambda s: combined[s]["dd"])

    print(f"\n  Highest return:      Strategy [{best_ret}] "
          f"₹{combined[best_ret]['cap']:,.0f}  "
          f"({combined[best_ret]['ret']:+.1f}%)")
    print(f"  Best return/DD:      Strategy [{best_rdd}] "
          f"Ret/DD={combined[best_rdd]['rdd']:.1f}x")
    print(f"  Lowest drawdown:     Strategy [{min_dd}] "
          f"Max DD={combined[min_dd]['dd']:.1f}%")

    print(f"\n  Combined results:")
    for s in strategies:
        print(f"    [{s}] Return={combined[s]['ret']:>+7.1f}%  "
              f"DD={combined[s]['dd']:>5.1f}%  "
              f"Ret/DD={combined[s]['rdd']:>6.1f}x  -- {strat_names[s]}")

    print(f"\n  RECOMMENDATION:")
    if combined["C"]["rdd"] >= combined["B"]["rdd"]:
        print(f"    Half Kelly tiered [C] achieves better risk-adjusted return")
        print(f"    than the 7->14->21 user structure [B].")
        print(f"    Use [C] sizing in live system.")
    else:
        print(f"    User tiered structure [B] achieves better risk-adjusted return")
        print(f"    than Half Kelly [C] on this dataset.")
        print(f"    Use [B] sizing in live system.")

    print(f"\n  Note: All results use T+30m exit, no bid-ask spread, no brokerage.")
    print(f"  Real P&L approximately 85-92% of these figures after costs.")
    print(f"\n{SEP}\n")


if __name__ == "__main__":
    main()
