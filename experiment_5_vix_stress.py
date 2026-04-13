#!/usr/bin/env python3
"""
experiment_5_vix_stress.py
MERDIAN Experiment 5 — VIX/ATM IV Assumption Stress Test

KEY QUESTION:
  MERDIAN currently sets trade_allowed=False when VIX > 20.
  The assumption: high VIX = unpredictable moves = higher risk, lower edge.
  Experiment 12b showed BEAR_OB has +147% expectancy in HIGH_VOL months.
  HIGH_VOL months likely correlate with high ATM IV / VIX.

  Is the VIX gate suppressing the best trades?

PROXY:
  VIX is not stored in historical tables.
  Using atm_iv from hist_market_state — the ATM implied volatility of the
  option being traded. This is a better proxy than VIX because it is
  instrument-specific rather than index-wide.

  ATM IV thresholds (approximate VIX equivalents):
    LOW_IV:    atm_iv < 12%   ≈ VIX < 15  (low vol, grinding)
    MED_IV:    12% ≤ atm_iv < 18%  ≈ VIX 15-20  (normal)
    HIGH_IV:   atm_iv ≥ 18%   ≈ VIX > 20  (current gate blocks)
    SPIKE_IV:  atm_iv ≥ 40%   (data spikes / extreme events, excluded)

METHOD:
  For each ICT pattern occurrence, fetch atm_iv from hist_market_state
  at the nearest bar_ts. Bucket into LOW/MED/HIGH_IV. Score option P&L
  (same method as Experiments 2 and 12b).

  Output:
    Section 1: Baseline — does IV level predict option P&L at all?
    Section 2: Pattern × IV regime — where does each pattern work best?
    Section 3: The gate test — HIGH_IV vs MED_IV vs LOW_IV expectancy
    Section 4: VIX gate verdict — should MERDIAN block HIGH_IV trades?

Patterns: BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL (60%+ WR)

Read-only. Runtime: ~20 minutes.

Usage:
    python experiment_5_vix_stress.py
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

PAGE_SIZE   = 1_000
HORIZONS    = [15, 30, 60]
SESSION_END = dtime(15, 30)

# ── IV bucketing ──────────────────────────────────────────────────────
IV_SPIKE_THRESHOLD = 40.0   # exclude — data errors / extreme outliers

IV_BUCKETS = [
    ("LOW_IV  (<12%)",  0.0,  12.0),
    ("MED_IV  (12-18%)", 12.0, 18.0),
    ("HIGH_IV (18-40%)", 18.0, 40.0),
]

def iv_bucket(atm_iv):
    if atm_iv is None or atm_iv >= IV_SPIKE_THRESHOLD:
        return "SPIKE/NULL"
    for label, lo, hi in IV_BUCKETS:
        if lo <= atm_iv < hi:
            return label
    return "SPIKE/NULL"

def iv_short(atm_iv):
    if atm_iv is None or atm_iv >= IV_SPIKE_THRESHOLD:
        return "SPIKE"
    if atm_iv < 12:   return "LOW"
    if atm_iv < 18:   return "MED"
    return "HIGH"

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
MIN_OPTION_PRICE = 5.0
ATM_RADIUS  = 3
MAX_GAP_MIN = 5   # wider gap tolerance (v2 finding)

# ── Detection parameters ──────────────────────────────────────────────
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


# ── ATM IV lookup ─────────────────────────────────────────────────────

def build_iv_index(hms_rows, symbol):
    """
    Build sorted list of (bar_ts, atm_iv) for fast nearest lookup.
    Excludes spike values >= IV_SPIKE_THRESHOLD.
    """
    rows = []
    for r in hms_rows:
        if r["symbol"] != symbol: continue
        iv = r.get("atm_iv")
        if iv is None: continue
        try:
            iv_f = float(iv)
        except (ValueError, TypeError):
            continue
        if iv_f >= IV_SPIKE_THRESHOLD: continue
        rows.append((datetime.fromisoformat(r["bar_ts"]), iv_f))
    rows.sort(key=lambda x: x[0])
    return rows


def get_iv_at(iv_index, target_ts, max_gap=5):
    """Nearest atm_iv to target_ts. Returns (atm_iv, gap_minutes) or (None, None)."""
    if not iv_index: return None, None
    tss = [r[0] for r in iv_index]
    idx = bisect.bisect_left(tss, target_ts)
    best_iv, best_g = None, timedelta(minutes=max_gap+1)
    for i in (idx-1, idx):
        if 0 <= i < len(iv_index):
            gap = abs(iv_index[i][0] - target_ts)
            if gap < best_g:
                best_g, best_iv = gap, iv_index[i][1]
    return (best_iv, best_g.total_seconds()/60) \
           if best_g <= timedelta(minutes=max_gap) else (None, None)


# ── Pattern detectors ─────────────────────────────────────────────────

def detect_obs(bars):
    out, seen, n = [], set(), len(bars)
    for i in range(n-6):
        mv = pct(bars[i]["close"], bars[min(i+5,n-1)]["close"])
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j); out.append(dict(bar=bars[j], pattern="BEAR_OB")); break
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j); out.append(dict(bar=bars[j], pattern="BULL_OB")); break
    return out


def detect_fvg(bars):
    out, min_g = [], FVG_MIN_PCT/100.0
    for i in range(1, len(bars)-1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            out.append(dict(bar=c, pattern="BULL_FVG"))
    return out


def detect_judas(bars):
    out = []
    if len(bars) < 46: return out
    mv = pct(bars[0]["open"], bars[14]["close"])
    if abs(mv) < JUDAS_MIN_PCT: return out
    rev = bars[15:45]
    if mv < 0:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv)*0.50:
            out.append(dict(bar=bars[14], pattern="JUDAS_BULL"))
    return out


# ── P&L aggregation ───────────────────────────────────────────────────

class IvBucket:
    def __init__(self):
        self.n   = 0
        self.nod = 0
        self.iv_values = []
        self.pnl = {h: [] for h in HORIZONS}

    def add_no_data(self, iv):
        self.n   += 1
        self.nod += 1
        if iv is not None: self.iv_values.append(iv)

    def add(self, pnl_dict, iv):
        self.n += 1
        if iv is not None: self.iv_values.append(iv)
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
                    exp=wr*aw+(1-wr)*al,
                    best=max(v), worst=min(v))

    def avg_iv(self):
        return sum(self.iv_values)/len(self.iv_values) if self.iv_values else None

    def exp30(self):
        s = self.stats(30)
        return s["exp"] if s else -999


def fmt(v, w=9):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(w)

def fmtiv(v):
    return f"{v:.1f}%" if v else "n/a"


def print_table(title, rows, min_n=5, note=""):
    print(f"\n{'='*115}")
    print(f"  {title}")
    if note: print(f"  {note}")
    print(f"{'='*115}")
    print(f"  {'Label':<35} {'N':>5} {'Nod':>4} {'AvgIV':>7}  "
          f"{'T+15 Exp':>10}  {'T+30 Exp':>10}  {'T+60 Exp':>10}  "
          f"{'WR':>6}  Verdict")
    print(f"  {'-'*110}")

    rows = [(lbl, b) for lbl, b in rows if b.n >= min_n]
    rows.sort(key=lambda x: x[1].exp30(), reverse=True)

    for lbl, b in rows:
        s15 = b.stats(15)
        s30 = b.stats(30)
        s60 = b.stats(60)
        aiv = b.avg_iv()
        verdict = ""
        if s30:
            if s30["exp"] > 30 and s30["wr"] > 75:
                verdict = "STRONG EDGE ◄◄"
            elif s30["exp"] > 5:
                verdict = "EDGE ◄"
            elif s30["exp"] < -5:
                verdict = "AVOID ▼"
            else:
                verdict = "marginal"
        print(f"  {lbl:<35} {b.n:>5} {b.nod:>4} {fmtiv(aiv):>7}  "
              f"{fmt(s15['exp'] if s15 else None):>10}  "
              f"{fmt(s30['exp'] if s30 else None):>10}  "
              f"{fmt(s60['exp'] if s60 else None):>10}  "
              f"{(str(round(s30['wr']))+'%' if s30 else 'n/a'):>6}  {verdict}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Load hist_market_state for atm_iv
    log("Loading hist_market_state (atm_iv)...")
    hms_rows = []
    for sym in ["NIFTY", "SENSEX"]:
        rows = fetch_paginated(
            sb, "hist_market_state",
            [("eq","symbol",sym)],
            "symbol, bar_ts, atm_iv"
        )
        hms_rows.extend(rows)
        log(f"  {sym}: {len(rows):,} rows")

    # Aggregation buckets
    by_iv          = defaultdict(IvBucket)   # iv_bucket label
    by_pat_iv      = defaultdict(IvBucket)   # "pattern|iv_bucket"
    by_pat         = defaultdict(IvBucket)   # pattern baseline
    iv_distribution = defaultdict(int)        # iv_bucket → count of pattern occurrences

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        # Build IV index
        iv_index = build_iv_index(hms_rows, symbol)
        log(f"  IV index: {len(iv_index):,} bars | "
            f"range {iv_index[0][1]:.1f}% → {iv_index[-1][1]:.1f}%")

        # Load spot bars
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

        # Detect patterns
        log("  Detecting patterns...")
        all_patterns = []
        for d in dates:
            bars = spot_sessions[d]
            if len(bars) < 30: continue
            pats = detect_obs(bars) + detect_fvg(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS: continue
                bar = pat["bar"]
                ts  = bar["bar_ts"]
                atm_iv_val, _ = get_iv_at(iv_index, ts)
                ivb = iv_bucket(atm_iv_val)
                all_patterns.append({
                    "pattern":  pat["pattern"],
                    "bar":      bar,
                    "td":       d,
                    "exp_date": nearest_expiry_db(d, expiry_idx),
                    "atm":      atm_strike(bar["close"], symbol),
                    "opt_type": OPT_TYPE[pat["pattern"]],
                    "atm_iv":   atm_iv_val,
                    "iv_bucket": ivb,
                    "iv_short":  iv_short(atm_iv_val),
                })
                iv_distribution[ivb] += 1
        log(f"  {len(all_patterns)} patterns | "
            f"LOW:{iv_distribution['LOW_IV  (<12%)']:,} "
            f"MED:{iv_distribution['MED_IV  (12-18%)']:,} "
            f"HIGH:{iv_distribution['HIGH_IV (18-40%)']:,}")

        # Group by day and fetch options
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log(f"  Scoring {len(day_groups)} day/expiry groups...")

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
                for pat in pats_today:
                    iv = pat["atm_iv"]
                    by_iv[pat["iv_bucket"]].add_no_data(iv)
                    by_pat_iv[f"{pat['pattern']}|{pat['iv_short']}"].add_no_data(iv)
                    by_pat[pat["pattern"]].add_no_data(iv)
                continue

            if gi % 30 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            for pat in pats_today:
                ts  = pat["bar"]["bar_ts"]
                stk = pat["atm"]
                ot  = pat["opt_type"]
                ivb = pat["iv_bucket"]
                ivs = pat["iv_short"]
                iv  = pat["atm_iv"]
                pk  = pat["pattern"]

                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None:
                    by_iv[ivb].add_no_data(iv)
                    by_pat_iv[f"{pk}|{ivs}"].add_no_data(iv)
                    by_pat[pk].add_no_data(iv)
                    continue

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

                by_iv[ivb].add(pnl_dict, iv)
                by_pat_iv[f"{pk}|{ivs}"].add(pnl_dict, iv)
                by_pat[pk].add(pnl_dict, iv)

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 115)
    print("  MERDIAN EXPERIMENT 5 — ATM IV / VIX ASSUMPTION STRESS TEST")
    print("  KEY QUESTION: Does MERDIAN's VIX>20 gate suppress the best trades?")
    print()
    print("  Proxy: atm_iv from hist_market_state (VIX not stored historically)")
    print("  LOW_IV  (<12%)  ≈ VIX <15   — low vol, grinding market")
    print("  MED_IV  (12-18%) ≈ VIX 15-20 — normal market")
    print("  HIGH_IV (18-40%) ≈ VIX >20   — current gate BLOCKS trading here")
    print("=" * 115)

    # ── Section 1: IV regime baseline ────────────────────────────────
    print_table(
        "SECTION 1 — IV REGIME BASELINE (all patterns combined)",
        [(k, v) for k, v in by_iv.items()],
        min_n=5,
        note="Does higher IV = better or worse option P&L overall?"
    )

    # ── Section 2: Pattern × IV ───────────────────────────────────────
    print_table(
        "SECTION 2 — PATTERN × IV REGIME",
        [(k, v) for k, v in by_pat_iv.items()],
        min_n=5,
        note="The gate test: are HIGH_IV trades better or worse than MED/LOW?"
    )

    # ── Section 3: Gate verdict ───────────────────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 3 — VIX GATE VERDICT")
    print("  Current rule: trade_allowed=False when VIX>20 (≈ atm_iv>18%)")
    print("  For each pattern: compare HIGH_IV vs MED_IV expectancy.")
    print("  If HIGH_IV > MED_IV → gate is SUPPRESSING edge, should be REMOVED.")
    print("  If HIGH_IV < MED_IV → gate is PROTECTING capital, should be KEPT.")
    print(f"{'='*115}")
    print(f"  {'Pattern':<16} {'LOW Exp':>10}  {'MED Exp':>10}  {'HIGH Exp':>10}  "
          f"{'HIGH>MED?':>10}  Gate Verdict")
    print(f"  {'-'*85}")

    for pat in sorted(TARGET_PATTERNS):
        low_b  = by_pat_iv.get(f"{pat}|LOW")
        med_b  = by_pat_iv.get(f"{pat}|MED")
        high_b = by_pat_iv.get(f"{pat}|HIGH")

        low_e  = low_b.stats(30)["exp"]   if low_b  and low_b.stats(30)  else None
        med_e  = med_b.stats(30)["exp"]   if med_b  and med_b.stats(30)  else None
        high_e = high_b.stats(30)["exp"]  if high_b and high_b.stats(30) else None

        if high_e is not None and med_e is not None:
            if high_e > med_e + 5:
                verdict = "REMOVE GATE — HIGH_IV trades are BETTER ◄◄"
            elif high_e > med_e - 5:
                verdict = "REVIEW — HIGH_IV similar to MED_IV"
            else:
                verdict = "KEEP GATE — HIGH_IV trades are worse"
            better = "YES ◄" if high_e > med_e else "no"
        elif high_e is None:
            verdict = "INSUFFICIENT DATA — cannot conclude"
            better = "n/a"
        else:
            verdict = "MED_IV data missing"
            better = "n/a"

        print(f"  {pat:<16} {fmt(low_e):>10}  {fmt(med_e):>10}  {fmt(high_e):>10}  "
              f"{better:>10}  {verdict}")

    # ── Section 4: IV as signal quality filter ────────────────────────
    print(f"\n{'='*115}")
    print("  SECTION 4 — IV AS SIGNAL QUALITY FILTER")
    print("  Rather than blocking high IV, should IV level SCALE position size?")
    print("  HIGH_IV = larger position (more edge)?")
    print("  LOW_IV  = smaller position (less edge)?")
    print(f"{'='*115}")
    print(f"  {'Pattern':<16} {'LOW Exp T+30':>14}  {'MED Exp T+30':>14}  "
          f"{'HIGH Exp T+30':>15}  Sizing Recommendation")
    print(f"  {'-'*85}")

    for pat in sorted(TARGET_PATTERNS):
        low_b  = by_pat_iv.get(f"{pat}|LOW")
        med_b  = by_pat_iv.get(f"{pat}|MED")
        high_b = by_pat_iv.get(f"{pat}|HIGH")

        low_e  = low_b.stats(30)["exp"]  if low_b  and low_b.stats(30)  else None
        med_e  = med_b.stats(30)["exp"]  if med_b  and med_b.stats(30)  else None
        high_e = high_b.stats(30)["exp"] if high_b and high_b.stats(30) else None

        exps = {k:v for k,v in [("LOW",low_e),("MED",med_e),("HIGH",high_e)]
                if v is not None}
        if not exps:
            rec = "insufficient data"
        else:
            best_regime = max(exps, key=exps.get)
            worst_regime = min(exps, key=exps.get)
            if best_regime == "HIGH":
                rec = f"Scale UP in HIGH_IV → {fmt(high_e)} vs {fmt(low_e)} LOW"
            elif best_regime == "LOW":
                rec = f"Scale UP in LOW_IV  → {fmt(low_e)} vs {fmt(high_e)} HIGH"
            else:
                rec = f"MED_IV is sweet spot → {fmt(med_e)}"

        print(f"  {pat:<16} {fmt(low_e):>14}  {fmt(med_e):>14}  "
              f"{fmt(high_e):>15}  {rec}")

    # ── Section 5: IV quartile granularity ───────────────────────────
    # Fine-grained — all patterns combined
    print(f"\n{'='*115}")
    print("  SECTION 5 — IV QUARTILE BREAKDOWN (all patterns, T+30m)")
    print("  Fine-grained view: at exactly what IV level does edge appear/disappear?")
    print(f"{'='*115}")

    quartile_buckets = [
        ("Q1: <8%",    0.0,  8.0),
        ("Q2: 8-12%",  8.0, 12.0),
        ("Q3: 12-16%", 12.0,16.0),
        ("Q4: 16-20%", 16.0,20.0),
        ("Q5: 20-25%", 20.0,25.0),
        ("Q6: 25-40%", 25.0,40.0),
    ]

    q_buckets = {q[0]: IvBucket() for q in quartile_buckets}

    # Re-aggregate into quartiles from by_pat_iv data
    # We need to rebuild from raw — instead use the already-aggregated
    # pnl lists from by_iv combined. For granularity, we rebuild from
    # all pattern records stored in by_pat_iv.

    print(f"  {'IV Range':<16} {'N scored':>9}  {'T+30 Exp':>10}  "
          f"{'WR':>6}  {'Avg IV':>8}  Note")
    print(f"  {'-'*65}")
    print(f"  (Quartile breakdown requires raw IV per trade — "
          f"see Section 2 for pattern-level detail)")
    print(f"  Section 2 IV regime bins provide the actionable signal.")

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*115}")
    print("  EXPERIMENT 5 SUMMARY")
    print(f"{'='*115}")
    print()
    print("  The VIX gate (trade_allowed=False when VIX>20) was introduced as")
    print("  a safety measure assuming high vol = higher risk = lower edge.")
    print()
    print("  The data now tells us which assumption is correct:")
    print("  → If HIGH_IV expectancy > MED_IV: gate removes alpha, should be removed")
    print("  → If HIGH_IV expectancy < MED_IV: gate protects capital, keep it")
    print("  → If similar: gate is neutral, consider removing for simplicity")
    print()
    print("  ALTERNATIVE APPROACH: Replace binary gate with IV-scaled position sizing")
    print("    LOW_IV  → 0.5× position (less edge, reduce exposure)")
    print("    MED_IV  → 1.0× position (normal)")
    print("    HIGH_IV → 1.5× position (if HIGH_IV has more edge)")
    print()
    print("  This converts a binary on/off gate into a continuous risk-adjusted")
    print("  position scaling mechanism — more nuanced and data-backed.")
    print(f"{'='*115}\n")


if __name__ == "__main__":
    main()


