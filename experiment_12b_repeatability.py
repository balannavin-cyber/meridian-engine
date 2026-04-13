#!/usr/bin/env python3
"""
experiment_12b_repeatability.py
MERDIAN Experiment 12b — Repeatability by Volatility Regime

REVISION of Experiment 12 based on Experiment 0 findings.

Experiment 0 finding: The assumed phase boundaries (BULL Apr-Sep, CORRECTION
Sep-Dec, BEAR Jan-Mar) were empirically wrong. The market spent 10 of 12 months
in NEUTRAL territory at the 1-minute level. Only Nov 2025 was BULL (55.6% UP)
and Mar 2026 was BEAR (55.3% DOWN) — single months, insufficient for repeatability.

NEW GROUPING — Volatility regime (from Experiment 0 large_move%):

  LOW_VOL:  Jul 2025 – Oct 2025  (large_move% 0.0–0.3%)
            Grinding, mean-reverting market. Options cheap.
            Hardest environment for option buyers.

  MID_VOL:  May 2025, Jun 2025, Nov 2025, Dec 2025  (0.2–2.2%)
            Moderate volatility. Normal options environment.

  HIGH_VOL: Apr 2025, Jan 2026, Feb 2026, Mar 2026  (1.5–4.2%)
            Volatile, large moves. Options expensive but rewarding.
            Best environment for option buyers.

This tests: do the 60%+ WR patterns (BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL)
maintain their edge across different volatility environments?

COVERAGE FIX:
  Before scoring each day, checks if the option lookup returned any data.
  Tracks coverage rate per vol regime so we know how much data we actually have.
  Only reports results where N_scored >= 5 (after no-data exclusions).

Read-only. Runtime: ~20-25 minutes.

Usage:
    python experiment_12b_repeatability.py
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

PAGE_SIZE   = 1_000
HORIZONS    = [15, 30, 60]
SESSION_END = dtime(15, 30)

# ── Volatility regime assignment ──────────────────────────────────────
# Based on Experiment 0 large_move% (>0.5% at T+30m) per month
VOL_REGIME = {
    # HIGH_VOL months (large_move% > 1.5%)
    (2025,  4): "HIGH_VOL",   # Apr 2025: 4.2%
    (2026,  1): "HIGH_VOL",   # Jan 2026: 1.5%
    (2026,  2): "HIGH_VOL",   # Feb 2026: 2.0%
    (2026,  3): "HIGH_VOL",   # Mar 2026: 4.2%
    # MID_VOL months (0.2–2.2%)
    (2025,  5): "MID_VOL",    # May 2025: 2.2%
    (2025,  6): "MID_VOL",    # Jun 2025: 1.2%
    (2025, 11): "MID_VOL",    # Nov 2025: 0.3%
    (2025, 12): "MID_VOL",    # Dec 2025: 0.0% (borderline)
    # LOW_VOL months (0.0–0.2%)
    (2025,  7): "LOW_VOL",    # Jul 2025: 0.2%
    (2025,  8): "LOW_VOL",    # Aug 2025: 0.0%
    (2025,  9): "LOW_VOL",    # Sep 2025: 0.2%
    (2025, 10): "LOW_VOL",    # Oct 2025: 0.1%
}

VOL_ORDER = ["HIGH_VOL", "MID_VOL", "LOW_VOL"]

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

def vol_regime(td):
    return VOL_REGIME.get((td.year, td.month), "UNKNOWN")

def month_label(td):
    return f"{MONTH_NAMES[td.month]} {td.year}"

# ── Pattern config ────────────────────────────────────────────────────
OPT_TYPE = {
    "BULL_OB":    "CE",
    "BEAR_OB":    "PE",
    "BULL_FVG":   "CE",
    "JUDAS_BULL": "CE",
}
TARGET_PATTERNS = set(OPT_TYPE.keys())

# ── Instrument conventions ────────────────────────────────────────────
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}
EXPIRY_WD   = {"NIFTY": 3, "SENSEX": 1}
MIN_OPTION_PRICE = 5.0
ATM_RADIUS  = 3
MAX_GAP_MIN = 3

# ── Detection parameters ──────────────────────────────────────────────
SWING_LB        = 5
OB_MIN_MOVE_PCT = 0.40
FVG_MIN_PCT     = 0.10
JUDAS_MIN_PCT   = 0.25


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


# ── P&L aggregation ───────────────────────────────────────────────────

class PnlBucket:
    def __init__(self):
        self.n_detected = 0   # patterns detected
        self.n_no_data  = 0   # no option price found
        self.n_scored   = 0   # actually scored
        self.pnl        = {h: [] for h in HORIZONS}

    def add_no_data(self):
        self.n_detected += 1
        self.n_no_data  += 1

    def add(self, pnl_dict):
        self.n_detected += 1
        self.n_scored   += 1
        for h in HORIZONS:
            if pnl_dict.get(h) is not None:
                self.pnl[h].append(pnl_dict[h])

    def coverage_pct(self):
        if self.n_detected == 0: return None
        return 100 * self.n_scored / self.n_detected

    def stats(self, h):
        v = self.pnl[h]
        if not v: return None
        wins = [x for x in v if x > 0]
        loss = [x for x in v if x <= 0]
        wr   = len(wins)/len(v)
        aw   = sum(wins)/len(wins) if wins else 0.0
        al   = sum(loss)/len(loss) if loss else 0.0
        return dict(n=len(v), wr=wr*100,
                    avg=sum(v)/len(v),
                    exp=wr*aw+(1-wr)*al,
                    best=max(v), worst=min(v))

    def exp30(self):
        s = self.stats(30)
        return s["exp"] if s else -999


def fmt(v, w=9):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(w)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Buckets
    # (pattern, vol_regime) → PnlBucket
    by_pat_vol   = defaultdict(PnlBucket)
    # (pattern) → PnlBucket (overall baseline)
    by_pattern   = defaultdict(PnlBucket)
    # (vol_regime) → PnlBucket (all patterns combined)
    by_vol       = defaultdict(PnlBucket)
    # (pattern, month_label) → PnlBucket (granular monthly)
    by_pat_month = defaultdict(PnlBucket)
    # coverage tracker per (vol_regime)
    coverage     = defaultdict(lambda: {"detected":0, "scored":0, "days":0, "days_with_data":0})

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")

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

        log("  Detecting patterns + fetching options...")
        day_groups = defaultdict(list)

        for d in dates:
            bars = spot_sessions[d]
            if len(bars) < 30: continue
            pats = detect_obs(bars) + detect_fvg(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS: continue
                bar = pat["bar"]
                vr  = vol_regime(d)
                day_groups[(d, nearest_expiry(d, symbol), vr)].append({
                    "pattern":  pat["pattern"],
                    "bar":      bar,
                    "td":       d,
                    "atm":      atm_strike(bar["close"], symbol),
                    "opt_type": OPT_TYPE[pat["pattern"]],
                    "vol_reg":  vr,
                    "month":    month_label(d),
                })

        total_groups = len(day_groups)
        for gi, ((td, ed, vr), pats_today) in enumerate(sorted(day_groups.items())):
            step = STRIKE_STEP[symbol]
            strikes_needed   = set()
            opt_types_needed = set()
            for pat in pats_today:
                base = pat["atm"]
                for r in range(-ATM_RADIUS, ATM_RADIUS+1):
                    strikes_needed.add(base + r*step)
                opt_types_needed.add(pat["opt_type"])

            coverage[vr]["days"] += 1

            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes_needed), sorted(opt_types_needed)
                )
            except Exception:
                for pat in pats_today:
                    by_pat_vol[f"{pat['pattern']}|{vr}"].add_no_data()
                    by_pattern[pat["pattern"]].add_no_data()
                    by_vol[vr].add_no_data()
                    by_pat_month[f"{pat['pattern']}|{pat['month']}"].add_no_data()
                    coverage[vr]["detected"] += 1
                continue

            # Check if lookup has any data at all
            has_data = len(lookup) > 0
            if has_data:
                coverage[vr]["days_with_data"] += 1

            if gi % 30 == 0:
                log(f"    {gi}/{total_groups} groups | vol={vr} | "
                    f"data={'YES' if has_data else 'NO'}")

            for pat in pats_today:
                ts  = pat["bar"]["bar_ts"]
                stk = pat["atm"]
                ot  = pat["opt_type"]
                vr_ = pat["vol_reg"]
                pk  = pat["pattern"]
                ml  = pat["month"]

                coverage[vr_]["detected"] += 1

                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None:
                    by_pat_vol[f"{pk}|{vr_}"].add_no_data()
                    by_pattern[pk].add_no_data()
                    by_vol[vr_].add_no_data()
                    by_pat_month[f"{pk}|{ml}"].add_no_data()
                    continue

                coverage[vr_]["scored"] += 1

                pnl_dict = {}
                for h in HORIZONS:
                    if not in_session(ts, h):
                        pnl_dict[h] = None
                        continue
                    exit_p, _ = get_option_price(
                        lookup, entry_stk or stk, ot,
                        ts + timedelta(minutes=h), symbol
                    )
                    pnl_dict[h] = pct(entry_p, exit_p) if exit_p else None

                by_pat_vol[f"{pk}|{vr_}"].add(pnl_dict)
                by_pattern[pk].add(pnl_dict)
                by_vol[vr_].add(pnl_dict)
                by_pat_month[f"{pk}|{ml}"].add(pnl_dict)

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 118)
    print("  MERDIAN EXPERIMENT 12b — REPEATABILITY BY VOLATILITY REGIME")
    print("  Revised from Exp 12 based on Experiment 0 empirical phase findings.")
    print("  Market spent 10/12 months NEUTRAL. Phase grouping replaced by VOL regime.")
    print()
    print("  HIGH_VOL: Apr 2025, Jan-Mar 2026  (large_move% > 1.5%)")
    print("  MID_VOL:  May, Jun, Nov, Dec 2025  (0.2–2.2%)")
    print("  LOW_VOL:  Jul-Oct 2025             (0.0–0.2%)")
    print("=" * 118)

    # ── Coverage report ───────────────────────────────────────────────
    print(f"\n{'='*118}")
    print("  SECTION 0 — DATA COVERAGE BY VOLATILITY REGIME")
    print("  Coverage = % of detected patterns that had option price data")
    print("  Low coverage = option bars sparse for that period")
    print(f"{'='*118}")
    print(f"  {'Vol Regime':<12} {'Days':>6}  {'Days w/data':>12}  "
          f"{'Coverage%':>10}  {'Detected':>9}  {'Scored':>8}  {'Score%':>8}")
    print(f"  {'-'*75}")
    for vr in VOL_ORDER:
        c = coverage[vr]
        d_pct  = 100*c["days_with_data"]/c["days"] if c["days"] else 0
        sc_pct = 100*c["scored"]/c["detected"]      if c["detected"] else 0
        print(f"  {vr:<12} {c['days']:>6}  {c['days_with_data']:>12}  "
              f"{d_pct:>9.1f}%  {c['detected']:>9}  "
              f"{c['scored']:>8}  {sc_pct:>7.1f}%")

    # ── Baseline ──────────────────────────────────────────────────────
    print(f"\n{'='*118}")
    print("  SECTION 1 — BASELINE: All vol regimes combined")
    print(f"{'='*118}")
    print(f"  {'Pattern':<15} {'N det':>6} {'N scored':>9} {'Cov%':>6}  "
          f"{'T+15 Exp':>10}  {'T+30 Exp':>10}  {'T+60 Exp':>10}  {'WR':>6}")
    print(f"  {'-'*85}")
    for pat in sorted(TARGET_PATTERNS):
        b = by_pattern.get(pat)
        if not b: continue
        s = b.stats(30)
        cov = b.coverage_pct()
        flag = " ◄" if s and s["exp"] > 5 else (" ▼" if s and s["exp"] < 0 else "  ")
        print(f"  {pat:<15} {b.n_detected:>6} {b.n_scored:>9} "
              f"{fmt(cov,5):>6}  "
              f"{fmt(b.stats(15)['exp'] if b.stats(15) else None):>10}  "
              f"{fmt(s['exp'] if s else None):>10}{flag} "
              f"{fmt(b.stats(60)['exp'] if b.stats(60) else None):>10}  "
              f"{(str(round(s['wr']))+'%' if s else 'n/a'):>6}")

    # ── Pattern × Vol regime ──────────────────────────────────────────
    print(f"\n{'='*118}")
    print("  SECTION 2 — PATTERN × VOLATILITY REGIME")
    print("  Key question: Does edge hold in LOW_VOL (grinding) as well as HIGH_VOL?")
    print(f"{'='*118}")
    print(f"  {'Label':<28} {'N det':>6} {'Scored':>7} {'Cov%':>6}  "
          f"{'T+15 Exp':>10}  {'T+30 Exp':>10}  {'T+60 Exp':>10}  "
          f"{'WR':>6}  Verdict")
    print(f"  {'-'*105}")

    for pat in sorted(TARGET_PATTERNS):
        for vr in VOL_ORDER:
            key = f"{pat}|{vr}"
            b   = by_pat_vol.get(key)
            if not b or b.n_detected < 3: continue
            s   = b.stats(30)
            cov = b.coverage_pct()
            verdict = ""
            if s:
                if s["exp"] > 20 and s["wr"] > 70:
                    verdict = "STRONG EDGE ◄◄"
                elif s["exp"] > 5:
                    verdict = "EDGE ◄"
                elif s["exp"] < -5:
                    verdict = "AVOID ▼"
                else:
                    verdict = "noise"
            print(f"  {key:<28} {b.n_detected:>6} {b.n_scored:>7} "
                  f"{fmt(cov,5):>6}  "
                  f"{fmt(b.stats(15)['exp'] if b.stats(15) else None):>10}  "
                  f"{fmt(s['exp'] if s else None):>10}  "
                  f"{fmt(b.stats(60)['exp'] if b.stats(60) else None):>10}  "
                  f"{(str(round(s['wr']))+'%' if s else 'n/a'):>6}  {verdict}")
        print()

    # ── Vol regime aggregate ──────────────────────────────────────────
    print(f"\n{'='*118}")
    print("  SECTION 3 — VOL REGIME AGGREGATE (all patterns combined)")
    print("  Overall options environment quality by volatility period")
    print(f"{'='*118}")
    print(f"  {'Vol Regime':<12} {'Scored':>8}  {'T+15 Exp':>10}  "
          f"{'T+30 Exp':>10}  {'T+60 Exp':>10}  {'WR':>6}  Character")
    print(f"  {'-'*80}")
    for vr in VOL_ORDER:
        b = by_vol.get(vr)
        if not b: continue
        s = b.stats(30)
        char = ""
        if s:
            if s["exp"] > 15: char = "Excellent options env"
            elif s["exp"] > 5: char = "Good options env"
            elif s["exp"] > 0: char = "Marginal"
            else: char = "Poor options env"
        print(f"  {vr:<12} {b.n_scored:>8}  "
              f"{fmt(b.stats(15)['exp'] if b.stats(15) else None):>10}  "
              f"{fmt(s['exp'] if s else None):>10}  "
              f"{fmt(b.stats(60)['exp'] if b.stats(60) else None):>10}  "
              f"{(str(round(s['wr']))+'%' if s else 'n/a'):>6}  {char}")

    # ── Monthly granular ──────────────────────────────────────────────
    print(f"\n{'='*118}")
    print("  SECTION 4 — MONTHLY GRANULAR (BULL_OB and BEAR_OB only)")
    print("  Tracks the two strongest patterns month by month")
    print(f"{'='*118}")

    # Get all months present
    all_months = sorted(set(
        key.split("|")[1]
        for key in by_pat_month
        if key.startswith("BULL_OB|") or key.startswith("BEAR_OB|")
    ), key=lambda m: datetime.strptime(m, "%b %Y"))

    for pat in ["BULL_OB", "BEAR_OB"]:
        print(f"\n  {pat}:")
        print(f"  {'Month':<12} {'N det':>6} {'Scored':>7} {'Cov%':>6}  "
              f"{'T+30 Exp':>10}  {'WR':>6}")
        print(f"  {'-'*55}")
        for ml in all_months:
            key = f"{pat}|{ml}"
            b   = by_pat_month.get(key)
            if not b or b.n_detected == 0: continue
            s   = b.stats(30)
            vr  = next((v for (yr,mo),v in VOL_REGIME.items()
                        if f"{MONTH_NAMES[mo]} {yr}" == ml), "?")
            flag = " ◄" if s and s["exp"] > 5 else (" ▼" if s and s["exp"] < 0 else "  ")
            cov  = b.coverage_pct()
            print(f"  {ml:<12} {b.n_detected:>6} {b.n_scored:>7} "
                  f"{fmt(cov,5):>6}  "
                  f"{fmt(s['exp'] if s else None):>10}{flag}  "
                  f"{(str(round(s['wr']))+'%' if s else 'n/a'):>6}  [{vr}]")

    # ── Repeatability verdict ─────────────────────────────────────────
    print(f"\n{'='*118}")
    print("  REPEATABILITY VERDICT")
    print("  STRUCTURAL = edge in all 3 vol regimes with sufficient coverage")
    print("  VOL-DEPENDENT = only works in HIGH or LOW vol, not both")
    print("  COVERAGE GAP = insufficient data in one or more regimes to conclude")
    print(f"{'='*118}")
    print(f"  {'Pattern':<16} {'HIGH_VOL Exp':>14}  {'MID_VOL Exp':>13}  "
          f"{'LOW_VOL Exp':>13}  {'Regimes>5%':>12}  Verdict")
    print(f"  {'-'*90}")

    for pat in sorted(TARGET_PATTERNS):
        exps     = {}
        coverage_ok = {}
        for vr in VOL_ORDER:
            key = f"{pat}|{vr}"
            b   = by_pat_vol.get(key)
            if b and b.n_scored >= 5:
                s = b.stats(30)
                exps[vr]        = s["exp"] if s else None
                coverage_ok[vr] = True
            else:
                exps[vr]        = None
                coverage_ok[vr] = False

        n_with_edge     = sum(1 for v in exps.values() if v is not None and v > 5)
        n_with_coverage = sum(1 for v in coverage_ok.values() if v)

        if n_with_coverage < 2:
            verdict = "COVERAGE GAP — cannot conclude"
        elif n_with_edge >= 3:
            verdict = "STRUCTURAL ★★★"
        elif n_with_edge == 2:
            verdict = "LIKELY STRUCTURAL ★★"
        elif n_with_edge == 1:
            verdict = "VOL-DEPENDENT ★"
        else:
            verdict = "NO EDGE across regimes"

        print(f"  {pat:<16} "
              f"{fmt(exps.get('HIGH_VOL')):>14}  "
              f"{fmt(exps.get('MID_VOL')):>13}  "
              f"{fmt(exps.get('LOW_VOL')):>13}  "
              f"{'★'*n_with_edge+'·'*(3-n_with_edge):>12}  "
              f"{verdict}")

    print(f"\n{'='*118}")
    print("  NOTES")
    print("  LOW_VOL coverage may be limited — if N_scored < 10, treat as indicative only")
    print("  HIGH_VOL includes both Apr 2025 (bullish vol) and Jan-Mar 2026 (bearish vol)")
    print("  This tests whether patterns work in volatile conditions regardless of direction")
    print(f"{'='*118}\n")


if __name__ == "__main__":
    main()
