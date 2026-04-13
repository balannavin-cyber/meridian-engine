#!/usr/bin/env python3
"""
experiment_11_12_regime_intersection.py
MERDIAN Experiment 11 + 12 — ICT × MERDIAN Regime + Repeatability

EXPERIMENT 11 — ICT geometry × MERDIAN regime intersection
  For each ICT pattern occurrence, joins to hist_market_state at the
  same bar_ts to get the live gamma_regime, breadth_regime, momentum_regime.
  Measures option P&L by pattern × regime combination.

  Key question: Does BULL_OB in LONG_GAMMA outperform BULL_OB in SHORT_GAMMA?
  Does the MERDIAN regime state at pattern time predict option outcome quality?

EXPERIMENT 12 — Repeatability across market phases
  Splits the full year into three distinct market phases:
    BULL:       2025-04-01 → 2025-09-15  (NIFTY 22000→25500, sustained rally)
    CORRECTION: 2025-09-16 → 2025-12-31  (NIFTY 25500→23500, correction)
    BEAR:       2026-01-01 → 2026-03-30  (NIFTY 23500→22000, sustained decline)

  A pattern that only works in one phase is describing that phase, not a signal rule.
  A pattern that works across all three phases is structurally valid.

  Key question: Do OBs and Judas swings hold their edge across all three phases?
  Which regime combinations are phase-dependent vs universal?

Patterns tested: BEAR_OB, BULL_OB, JUDAS_BEAR, JUDAS_BULL, BULL_FVG, BEAR_FVG
Option P&L: ATM CE (bullish) / ATM PE (bearish), same methodology as Experiment 2
No futures — options only per decision to drop futures complexity.

Read-only. Runtime: ~15-20 minutes.

Usage:
    python experiment_11_12_regime_intersection.py
"""

import os
import bisect
import time
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict
from itertools import groupby

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000
HORIZONS  = [15, 30, 60]
SESSION_END = dtime(15, 30)

# ── Market phases (Experiment 12) ─────────────────────────────────────
PHASES = {
    "BULL":       (date(2025,  4,  1), date(2025,  9, 15)),
    "CORRECTION": (date(2025,  9, 16), date(2025, 12, 31)),
    "BEAR":       (date(2026,  1,  1), date(2026,  3, 30)),
}

# ── Instrument conventions ────────────────────────────────────────────
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}
EXPIRY_WD   = {"NIFTY": 3, "SENSEX": 1}

OPT_TYPE = {
    "BEAR_OB": "PE", "BEAR_FVG": "PE", "JUDAS_BEAR": "PE",
    "BULL_OB": "CE", "BULL_FVG": "CE", "JUDAS_BULL": "CE",
}
TARGET_PATTERNS = set(OPT_TYPE.keys())

# ── Detection parameters ──────────────────────────────────────────────
SWING_LB        = 5
OB_MIN_MOVE_PCT = 0.40
FVG_MIN_PCT     = 0.10
JUDAS_MIN_PCT   = 0.25
MIN_OPTION_PRICE = 5.0
ATM_RADIUS      = 3
MAX_GAP_MIN     = 3


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def in_session(ts, h):
    return (ts + timedelta(minutes=h)).time() <= SESSION_END

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def nearest_expiry(td, symbol):
    wd = EXPIRY_WD[symbol]
    return td + timedelta(days=(wd - td.weekday()) % 7)

def compute_dte(td, symbol):
    return (EXPIRY_WD[symbol] - td.weekday()) % 7

def dte_bucket(dte):
    if dte == 0: return "DTE=0"
    if dte == 1: return "DTE=1"
    if dte <= 3: return "DTE=2-3"
    return "DTE=4+"

def market_phase(td):
    for phase, (start, end) in PHASES.items():
        if start <= td <= end:
            return phase
    return "UNKNOWN"


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


# ── Pattern detectors ─────────────────────────────────────────────────

def find_swings(bars, lb=SWING_LB):
    swings, n = [], len(bars)
    for i in range(lb, n-lb):
        w = range(i-lb, i+lb+1)
        h, l = bars[i]["high"], bars[i]["low"]
        if all(bars[j]["high"] <= h for j in w if j != i):
            swings.append((i,"HIGH",h))
        if all(bars[j]["low"]  >= l for j in w if j != i):
            swings.append((i,"LOW",l))
    return swings


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
        if p["low"] > n["high"] and (p["low"]-n["high"])/ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BEAR_FVG"))
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
    if mv > 0:
        if pct(bars[14]["close"], min(b["low"] for b in rev)) <= -mv*0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BEAR"))
    else:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv)*0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL"))
    return out


# ── hist_market_state lookup ──────────────────────────────────────────

def build_regime_index(hms_rows):
    """
    Build a lookup: symbol → sorted list of (bar_ts, gamma_regime, breadth_regime, momentum_regime)
    For fast nearest-bar regime lookup.
    NOTE: bar_ts stored as IST with +00:00 offset — use datetime directly.
    """
    index = defaultdict(list)
    for r in hms_rows:
        ts = datetime.fromisoformat(r["bar_ts"])
        index[r["symbol"]].append((
            ts,
            r.get("gamma_regime")    or "UNKNOWN",
            r.get("breadth_regime")  or "NO_BREADTH",
            r.get("momentum_regime") or "UNKNOWN",
        ))
    for sym in index:
        index[sym].sort(key=lambda x: x[0])
    return index


def get_regime_at(regime_index, symbol, target_ts, max_gap_min=5):
    """
    Find the MERDIAN regime (gamma/breadth/momentum) nearest to target_ts.
    Returns (gamma_regime, breadth_regime, momentum_regime) or None.
    """
    rows = regime_index.get(symbol, [])
    if not rows:
        return None
    tss = [r[0] for r in rows]
    idx = bisect.bisect_left(tss, target_ts)
    best, best_g = None, timedelta(minutes=max_gap_min+1)
    for i in (idx-1, idx):
        if 0 <= i < len(rows):
            gap = abs(rows[i][0] - target_ts)
            if gap < best_g:
                best_g, best = gap, rows[i]
    return best[1:] if best and best_g <= timedelta(minutes=max_gap_min) else None


# ── P&L aggregation ───────────────────────────────────────────────────

class PnlBucket:
    def __init__(self):
        self.n       = 0
        self.no_data = 0
        self.pnl     = {h: [] for h in HORIZONS}

    def add_no_data(self):
        self.n += 1
        self.no_data += 1

    def add(self, pnl_dict):
        self.n += 1
        for h in HORIZONS:
            if pnl_dict.get(h) is not None:
                self.pnl[h].append(pnl_dict[h])

    def stats(self, h):
        v = self.pnl[h]
        if not v: return None
        wins = [x for x in v if x > 0]
        loss = [x for x in v if x <= 0]
        wr   = len(wins)/len(v)
        aw   = sum(wins)/len(wins) if wins else 0.0
        al   = sum(loss)/len(loss) if loss else 0.0
        return dict(n=len(v), wr=wr*100, avg=sum(v)/len(v),
                    exp=wr*aw+(1-wr)*al, best=max(v), worst=min(v))

    def exp30(self):
        s = self.stats(30)
        return s["exp"] if s else -999


def fmt(v, w=9):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(w)


def print_table(title, rows_data, min_n=5, note=""):
    print(f"\n{'='*115}")
    print(f"  {title}")
    if note:
        print(f"  {note}")
    print(f"{'='*115}")
    print(f"  {'Label':<45} {'N':>5} {'NoD':>4}  "
          f"{'T+15 Exp':>10}  {'T+30 Exp':>10}  {'T+60 Exp':>10}  "
          f"{'T+30 WR':>8}  {'T+30 Avg':>10}")
    print(f"  {'-'*110}")

    rows = [(label, b) for label,b in rows_data if b.n >= min_n]
    rows.sort(key=lambda x: x[1].exp30(), reverse=True)

    for label, b in rows:
        s15 = b.stats(15)
        s30 = b.stats(30)
        s60 = b.stats(60)
        flag = " ◄" if s30 and s30["exp"] > 5 else (" ▼" if s30 and s30["exp"] < 0 else "  ")
        print(f"  {label:<45} {b.n:>5} {b.no_data:>4}  "
              f"{fmt(s15['exp'] if s15 else None):>10}  "
              f"{fmt(s30['exp'] if s30 else None):>10}{flag} "
              f"{fmt(s60['exp'] if s60 else None):>10}  "
              f"{(str(round(s30['wr']))+'%' if s30 else 'n/a'):>8}  "
              f"{fmt(s30['avg'] if s30 else None):>10}")

    if not rows:
        print("  (no rows above minimum N)")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # ── Load hist_market_state (both symbols) ─────────────────────────
    log("Loading hist_market_state...")
    hms_rows = []
    for sym in ["NIFTY", "SENSEX"]:
        rows = fetch_paginated(
            sb, "hist_market_state",
            [("eq","symbol",sym)],
            "symbol, bar_ts, gamma_regime, breadth_regime, momentum_regime"
        )
        hms_rows.extend(rows)
        log(f"  {sym}: {len(rows):,} rows")
    regime_index = build_regime_index(hms_rows)
    log(f"  Regime index built for {list(regime_index.keys())}")

    # ── Aggregation buckets ───────────────────────────────────────────
    # Experiment 11: pattern × gamma_regime × breadth_regime
    by_pat_gamma   = defaultdict(PnlBucket)   # "pattern|gamma"
    by_pat_bread   = defaultdict(PnlBucket)   # "pattern|breadth"
    by_pat_mom     = defaultdict(PnlBucket)   # "pattern|momentum"
    by_pat_combo   = defaultdict(PnlBucket)   # "pattern|gamma|breadth|momentum"

    # Experiment 12: pattern × market phase
    by_pat_phase   = defaultdict(PnlBucket)   # "pattern|phase"
    by_phase_gamma = defaultdict(PnlBucket)   # "phase|gamma" (all patterns combined)

    # Baseline
    by_pattern     = defaultdict(PnlBucket)   # pattern only

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        # Load spot bars
        log("  Loading spot bars...")
        raw_bars = fetch_paginated(
            sb, "hist_spot_bars_1m",
            [("eq","instrument_id",inst[symbol]),("eq","is_pre_market",False)],
            "bar_ts, trade_date, open, high, low, close"
        )
        for r in raw_bars:
            r["bar_ts"]     = datetime.fromisoformat(r["bar_ts"])
            r["trade_date"] = date.fromisoformat(r["trade_date"])
            for k in ("open","high","low","close"):
                r[k] = float(r[k])
        spot_sessions = sessions_from_bars(raw_bars)
        dates = sorted(spot_sessions.keys())
        log(f"  {len(raw_bars):,} bars | {len(dates)} sessions")

        # Detect patterns
        log("  Detecting patterns...")
        all_patterns = []
        for d in dates:
            bars = spot_sessions[d]
            if len(bars) < 30:
                continue
            pats = detect_obs(bars) + detect_fvg(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS:
                    continue
                bar   = pat["bar"]
                spot  = bar["close"]
                dte   = compute_dte(d, symbol)
                phase = market_phase(d)
                all_patterns.append({
                    "pattern":  pat["pattern"],
                    "bar":      bar,
                    "td":       d,
                    "exp_date": nearest_expiry(d, symbol),
                    "atm":      atm_strike(spot, symbol),
                    "opt_type": OPT_TYPE[pat["pattern"]],
                    "dte":      dte,
                    "dteb":     dte_bucket(dte),
                    "phase":    phase,
                    "symbol":   symbol,
                })

        log(f"  {len(all_patterns)} patterns detected")

        # Fetch options and score
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log(f"  Fetching options for {len(day_groups)} day/expiry groups...")

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
            except Exception as e:
                log(f"    WARNING {td}: {e}")
                for pat in pats_today:
                    k = pat["pattern"]
                    by_pattern[k].add_no_data()
                continue

            if gi % 40 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            for pat in pats_today:
                ts        = pat["bar"]["bar_ts"]
                stk       = pat["atm"]
                ot        = pat["opt_type"]
                pat_name  = pat["pattern"]
                phase     = pat["phase"]

                # Get MERDIAN regime at pattern bar
                regime = get_regime_at(regime_index, symbol, ts)
                if regime:
                    gamma_r, bread_r, mom_r = regime
                else:
                    gamma_r, bread_r, mom_r = "UNKNOWN", "NO_BREADTH", "UNKNOWN"

                # Option entry
                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None:
                    by_pattern[pat_name].add_no_data()
                    by_pat_gamma[f"{pat_name}|{gamma_r}"].add_no_data()
                    by_pat_bread[f"{pat_name}|{bread_r}"].add_no_data()
                    by_pat_mom[f"{pat_name}|{mom_r}"].add_no_data()
                    by_pat_combo[f"{pat_name}|{gamma_r}|{bread_r}|{mom_r}"].add_no_data()
                    by_pat_phase[f"{pat_name}|{phase}"].add_no_data()
                    by_phase_gamma[f"{phase}|{gamma_r}"].add_no_data()
                    continue

                # P&L at each horizon
                pnl_dict = {}
                for h in HORIZONS:
                    if not in_session(ts, h):
                        pnl_dict[h] = None
                        continue
                    exit_p, _ = get_option_price(
                        lookup, entry_stk, ot,
                        ts + timedelta(minutes=h), symbol
                    )
                    pnl_dict[h] = pct(entry_p, exit_p) if exit_p else None

                # Record into all buckets
                by_pattern[pat_name].add(pnl_dict)
                by_pat_gamma[f"{pat_name}|{gamma_r}"].add(pnl_dict)
                by_pat_bread[f"{pat_name}|{bread_r}"].add(pnl_dict)
                by_pat_mom[f"{pat_name}|{mom_r}"].add(pnl_dict)
                by_pat_combo[f"{pat_name}|{gamma_r}|{bread_r}|{mom_r}"].add(pnl_dict)
                by_pat_phase[f"{pat_name}|{phase}"].add(pnl_dict)
                by_phase_gamma[f"{phase}|{gamma_r}"].add(pnl_dict)

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 115)
    print("  MERDIAN EXPERIMENT 11 + 12")
    print("  Exp 11: ICT pattern × MERDIAN regime (gamma/breadth/momentum at bar time)")
    print("  Exp 12: Pattern repeatability across market phases (BULL/CORRECTION/BEAR)")
    print("  Options P&L only. No futures.")
    print("=" * 115)

    # ── Exp 11: Baseline ─────────────────────────────────────────────
    print_table(
        "BASELINE — Pattern P&L (all regimes, all phases)",
        [(k,v) for k,v in by_pattern.items()],
        min_n=5
    )

    # ── Exp 11: Pattern × Gamma regime ───────────────────────────────
    print_table(
        "EXP 11A — PATTERN × GAMMA REGIME",
        [(k,v) for k,v in by_pat_gamma.items()],
        min_n=5,
        note="Does BULL_OB in LONG_GAMMA outperform BULL_OB in SHORT_GAMMA/NO_FLIP?"
    )

    # ── Exp 11: Pattern × Breadth regime ─────────────────────────────
    print_table(
        "EXP 11B — PATTERN × BREADTH REGIME",
        [(k,v) for k,v in by_pat_bread.items()],
        min_n=5,
        note="Note: NO_BREADTH = before 2025-07-16 (breadth proxy not available)"
    )

    # ── Exp 11: Pattern × Momentum regime ────────────────────────────
    print_table(
        "EXP 11C — PATTERN × MOMENTUM REGIME",
        [(k,v) for k,v in by_pat_mom.items()],
        min_n=5,
        note="Does momentum alignment at pattern time predict option outcome?"
    )

    # ── Exp 11: Full combo ────────────────────────────────────────────
    print_table(
        "EXP 11D — FULL REGIME COMBO: pattern|gamma|breadth|momentum  (min N=10)",
        [(k,v) for k,v in by_pat_combo.items()],
        min_n=10,
        note="Highest-conviction setups where all three MERDIAN regimes align with ICT pattern"
    )

    # ── Exp 12: Pattern × Market phase ───────────────────────────────
    print_table(
        "EXP 12A — PATTERN × MARKET PHASE  (Repeatability test)",
        [(k,v) for k,v in by_pat_phase.items()],
        min_n=5,
        note="BULL=Apr-Sep25 | CORRECTION=Sep-Dec25 | BEAR=Jan-Mar26 | UNKNOWN=outside range"
    )

    # ── Exp 12: Phase × Gamma (all patterns) ─────────────────────────
    print_table(
        "EXP 12B — MARKET PHASE × GAMMA REGIME  (all patterns combined)",
        [(k,v) for k,v in by_phase_gamma.items()],
        min_n=10,
        note="Does LONG_GAMMA regime have consistent options edge across all market phases?"
    )

    # ── Exp 12: Repeatability summary ────────────────────────────────
    print(f"\n{'='*115}")
    print("  EXP 12 REPEATABILITY SUMMARY")
    print("  A pattern is structurally valid if it shows edge (Exp>5%) in 2 of 3 phases.")
    print("  A pattern showing edge in only 1 phase is describing that phase, not a rule.")
    print(f"{'='*115}")
    print(f"  {'Pattern':<20} {'BULL Exp':>10}  {'CORR Exp':>10}  {'BEAR Exp':>10}  "
          f"{'Phases>5%':>10}  Verdict")
    print(f"  {'-'*80}")

    for pat in sorted(TARGET_PATTERNS):
        exps = {}
        for phase in ["BULL","CORRECTION","BEAR"]:
            key = f"{pat}|{phase}"
            b   = by_pat_phase.get(key)
            s   = b.stats(30) if b else None
            exps[phase] = s["exp"] if s else None

        phases_with_edge = sum(1 for v in exps.values() if v is not None and v > 5)
        verdict = (
            "STRUCTURAL — works across phases" if phases_with_edge >= 2 else
            "PHASE-DEPENDENT — caution"        if phases_with_edge == 1 else
            "NO EDGE — avoid"
        )
        print(f"  {pat:<20} "
              f"{fmt(exps.get('BULL')):>10}  "
              f"{fmt(exps.get('CORRECTION')):>10}  "
              f"{fmt(exps.get('BEAR')):>10}  "
              f"{'★'*phases_with_edge + '·'*(3-phases_with_edge):>10}  "
              f"{verdict}")

    print(f"\n{'='*115}")
    print("  INTERPRETATION GUIDE")
    print("  Exp 11: Look for patterns where regime alignment consistently lifts expectancy")
    print("          Best setup: pattern + LONG_GAMMA + BEARISH breadth + BEARISH momentum")
    print("          for bearish trades, or vice versa for bullish")
    print("  Exp 12: Structural patterns (2+ phases) are candidates for signal rules")
    print("          Phase-dependent patterns need market phase detection before trading")
    print(f"{'='*115}\n")


if __name__ == "__main__":
    main()
