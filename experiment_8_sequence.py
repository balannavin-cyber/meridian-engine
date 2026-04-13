#!/usr/bin/env python3
"""
experiment_8_sequence.py
MERDIAN Experiment 8 — Pre-Pattern Sequence Detection

HYPOTHESIS:
  ICT patterns (OBs, FVGs) have a 70-87% win rate overall.
  The 13-30% that fail — can we identify them in advance?
  The 3 bars BEFORE a pattern forms contain information about its quality.

  A losing BULL_OB likely has different preceding characteristics
  than a winning BULL_OB:
    - Was there a prior liquidity sweep (sweep of prior low)?
    - Was momentum already bullish (reducing reversal probability)?
    - Was the OB formed during the best time zone (morning session)?
    - Was the prior move large enough to create genuine imbalance?

THIS EXPERIMENT MEASURES:
  For each OB and FVG, looks at the 3 bars preceding the pattern bar:
  
  1. PRIOR SWEEP — did price sweep the prior session high/low in the
     last 5 bars before the pattern? A sweep creates the liquidity pool
     that makes the subsequent institutional move meaningful.

  2. MOMENTUM CONTEXT — were the 3 preceding bars trending against the
     pattern direction (necessary for a genuine reversal)?
     BULL_OB needs preceding bearish momentum (at least 2 of 3 bars down)
     BEAR_OB needs preceding bullish momentum (at least 2 of 3 bars up)

  3. IMPULSE SIZE — was the pattern preceded by a strong impulsive move?
     Measures: sum of |returns| of 3 bars before OB bar.
     Strong impulse = market moved decisively before the OB formed.

  4. TIME ZONE — when in the session did the pattern fire?
     Morning (09:15-11:00) vs midday vs afternoon vs power hour.

  Combinations of these four are tested against option P&L from
  hist_option_bars_1m to find the highest-quality filter.

RESULT:
  A filter rule set that, when applied, lifts win rate from ~80% to ~90%+
  on the highest-quality setups, while avoiding the structural losers.

Read-only. Runtime: ~20-25 minutes (needs options data).

Usage:
    python experiment_8_sequence.py
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

# ── Pattern config ────────────────────────────────────────────────────
OPT_TYPE = {"BULL_OB": "CE", "BEAR_OB": "PE", "BULL_FVG": "CE"}
TARGET_PATTERNS = set(OPT_TYPE.keys())
DIRECTION = {"BULL_OB": +1, "BEAR_OB": -1, "BULL_FVG": +1}

# ── Instrument conventions ────────────────────────────────────────────
STRIKE_STEP      = {"NIFTY": 50, "SENSEX": 100}
MIN_OPTION_PRICE = 5.0
ATM_RADIUS       = 3
MAX_GAP_MIN      = 5

# ── Detection parameters ──────────────────────────────────────────────
OB_MIN_MOVE_PCT = 0.40
FVG_MIN_PCT     = 0.10

# ── Sequence parameters ───────────────────────────────────────────────
LOOKBACK_BARS   = 3     # bars before pattern to analyze
SWEEP_LOOKBACK  = 5     # bars before pattern to check for prior sweep
SWEEP_MIN_PCT   = 0.10  # % beyond prior session H/L to qualify as sweep
STRONG_IMPULSE  = 0.30  # sum of |returns| in lookback to qualify as strong

# ── Time zones ────────────────────────────────────────────────────────
TIME_ZONES = [
    ("OPEN    09:15-10:00", dtime(9,15),  dtime(10, 0)),
    ("MORNING 10:00-11:30", dtime(10, 0), dtime(11,30)),
    ("MIDDAY  11:30-13:30", dtime(11,30), dtime(13,30)),
    ("AFTNOON 13:30-15:30", dtime(13,30), dtime(15,30)),
]

def time_zone(ts):
    t = ts.time()
    for label, start, end in TIME_ZONES:
        if start <= t < end: return label
    return "OTHER"


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

def compute_sequence_features(bars, pat_idx, direction, prior_high, prior_low):
    """
    For a pattern at bars[pat_idx], compute the 4 sequence features
    from the preceding bars.

    Returns dict of features:
      prior_sweep:     True if price swept prior H/L in last SWEEP_LOOKBACK bars
      momentum_aligned: True if preceding bars showed counter-direction momentum
                        (needed for reversal setup)
      impulse_strong:  True if sum(|returns|) in last LOOKBACK_BARS >= STRONG_IMPULSE
      time_zone:       session time zone label
    """
    features = {}
    n = pat_idx

    # Time zone
    features["time_zone"] = time_zone(bars[pat_idx]["bar_ts"])

    # Momentum: are preceding bars moving counter to pattern direction?
    # BULL_OB (direction=+1) needs preceding bearish bars (price falling)
    # BEAR_OB (direction=-1) needs preceding bullish bars (price rising)
    if n >= LOOKBACK_BARS:
        preceding = bars[n-LOOKBACK_BARS:n]
        counter_bars = 0
        for b in preceding:
            move = b["close"] - b["open"]
            if direction == +1 and move < 0:   counter_bars += 1  # bearish bar
            if direction == -1 and move > 0:   counter_bars += 1  # bullish bar
        features["momentum_aligned"] = counter_bars >= 2
    else:
        features["momentum_aligned"] = False

    # Impulse strength: sum of absolute returns in preceding bars
    if n >= LOOKBACK_BARS:
        preceding = bars[n-LOOKBACK_BARS:n]
        total_move = sum(abs(pct(b["open"], b["close"])) for b in preceding)
        features["impulse_strong"] = total_move >= STRONG_IMPULSE
        features["impulse_pct"]    = total_move
    else:
        features["impulse_strong"] = False
        features["impulse_pct"]    = 0.0

    # Prior sweep: did price breach prior session H/L in lookback window?
    sweep_start = max(0, n - SWEEP_LOOKBACK)
    sweep_bars  = bars[sweep_start:n+1]
    swept = False
    if prior_high and prior_low:
        for b in sweep_bars:
            if direction == +1 and prior_low and \
               pct(prior_low, b["low"]) * -1 >= SWEEP_MIN_PCT:
                swept = True; break
            if direction == -1 and prior_high and \
               pct(prior_high, b["high"]) >= SWEEP_MIN_PCT:
                swept = True; break
    features["prior_sweep"] = swept

    return features


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


# ── P&L bucket ────────────────────────────────────────────────────────

class SeqBucket:
    def __init__(self):
        self.n   = 0
        self.nod = 0
        self.pnl = {h: [] for h in HORIZONS}

    def add_no_data(self): self.n += 1; self.nod += 1

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
                    exp=wr*aw+(1-wr)*al)

    def exp30(self):
        s = self.stats(30)
        return s["exp"] if s else -999


def fmt(v, w=9):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(w)


def print_table(title, rows, min_n=5):
    print(f"\n{'='*110}")
    print(f"  {title}")
    print(f"{'='*110}")
    print(f"  {'Label':<45} {'N':>5} {'Nod':>4}  "
          f"{'T+15 Exp':>10}  {'T+30 Exp':>10}  {'T+60 Exp':>10}  "
          f"{'WR':>6}  Verdict")
    print(f"  {'-'*100}")

    rows = [(lbl, b) for lbl, b in rows if b.n >= min_n]
    rows.sort(key=lambda x: x[1].exp30(), reverse=True)

    for lbl, b in rows:
        s15 = b.stats(15)
        s30 = b.stats(30)
        s60 = b.stats(60)
        verdict = ""
        if s30:
            if s30["exp"] > 30 and s30["wr"] > 80:
                verdict = "STRONG FILTER ◄◄"
            elif s30["exp"] > 5:
                verdict = "USEFUL FILTER ◄"
            elif s30["exp"] < -5:
                verdict = "AVOID ▼"
        print(f"  {lbl:<45} {b.n:>5} {b.nod:>4}  "
              f"{fmt(s15['exp'] if s15 else None):>10}  "
              f"{fmt(s30['exp'] if s30 else None):>10}  "
              f"{fmt(s60['exp'] if s60 else None):>10}  "
              f"{(str(round(s30['wr']))+'%' if s30 else 'n/a'):>6}  {verdict}")


# ── Pattern detectors ─────────────────────────────────────────────────

def detect_obs_with_idx(bars):
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


def detect_fvg_with_idx(bars):
    out, min_g = [], FVG_MIN_PCT/100.0
    for i in range(1, len(bars)-1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BULL_FVG"))
    return out


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Buckets — indexed by filter combination
    by_baseline    = defaultdict(SeqBucket)   # pattern only
    by_sweep       = defaultdict(SeqBucket)   # pattern|sweep(Y/N)
    by_momentum    = defaultdict(SeqBucket)   # pattern|momentum(Y/N)
    by_impulse     = defaultdict(SeqBucket)   # pattern|impulse(Y/N)
    by_timezone    = defaultdict(SeqBucket)   # pattern|timezone
    by_combo       = defaultdict(SeqBucket)   # pattern|sweep|momentum|impulse

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
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

        log("  Detecting patterns + computing features...")
        all_patterns = []

        for i, d in enumerate(dates):
            bars = spot_sessions[d]
            if len(bars) < 30: continue

            # Prior session high/low for sweep detection
            if i > 0:
                prior = spot_sessions.get(dates[i-1], [])
                prior_high = max(b["high"] for b in prior) if prior else None
                prior_low  = min(b["low"]  for b in prior) if prior else None
            else:
                prior_high = prior_low = None

            pats = detect_obs_with_idx(bars) + detect_fvg_with_idx(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS: continue
                bar     = pat["bar"]
                idx     = pat["bar_idx"]
                direct  = DIRECTION[pat["pattern"]]
                feats   = compute_sequence_features(
                    bars, idx, direct, prior_high, prior_low
                )
                all_patterns.append({
                    "pattern":   pat["pattern"],
                    "bar":       bar,
                    "bar_idx":   idx,
                    "td":        d,
                    "exp_date":  nearest_expiry_db(d, expiry_idx),
                    "atm":       atm_strike(bar["close"], symbol),
                    "opt_type":  OPT_TYPE[pat["pattern"]],
                    "features":  feats,
                })

        log(f"  {len(all_patterns)} patterns with features")

        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log(f"  Fetching options for {len(day_groups)} groups...")

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
                    pk = pat["pattern"]
                    by_baseline[pk].add_no_data()
                continue

            if gi % 30 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            for pat in pats_today:
                ts  = pat["bar"]["bar_ts"]
                stk = pat["atm"]
                ot  = pat["opt_type"]
                pk  = pat["pattern"]
                f   = pat["features"]

                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None:
                    by_baseline[pk].add_no_data()
                    continue

                pnl_dict = {}
                for h in HORIZONS:
                    if not in_session(ts, h):
                        pnl_dict[h] = None; continue
                    exit_p, _ = get_option_price(
                        lookup, entry_stk or stk, ot,
                        ts + timedelta(minutes=h), symbol
                    )
                    pnl_dict[h] = pct(entry_p, exit_p) if exit_p else None

                # Keys
                sw  = "SWEEP"   if f["prior_sweep"]     else "NO_SWEEP"
                mo  = "MOM_YES" if f["momentum_aligned"] else "MOM_NO"
                imp = "IMP_STR" if f["impulse_strong"]   else "IMP_WEK"
                tz  = f["time_zone"]
                combo = f"{sw}|{mo}|{imp}"

                by_baseline[pk].add(pnl_dict)
                by_sweep   [f"{pk}|{sw}"].add(pnl_dict)
                by_momentum[f"{pk}|{mo}"].add(pnl_dict)
                by_impulse [f"{pk}|{imp}"].add(pnl_dict)
                by_timezone[f"{pk}|{tz}"].add(pnl_dict)
                by_combo   [f"{pk}|{combo}"].add(pnl_dict)

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 110)
    print("  MERDIAN EXPERIMENT 8 — PRE-PATTERN SEQUENCE DETECTION")
    print("  Can the 3 bars before a pattern predict its quality?")
    print(f"  Lookback: {LOOKBACK_BARS} bars | Sweep lookback: {SWEEP_LOOKBACK} bars")
    print(f"  Strong impulse threshold: {STRONG_IMPULSE}% cumulative move")
    print(f"  Sweep threshold: {SWEEP_MIN_PCT}% beyond prior session H/L")
    print("=" * 110)

    print_table("SECTION 1 — BASELINE (no sequence filter)",
                [(k,v) for k,v in by_baseline.items()], min_n=5)

    print_table("SECTION 2 — PRIOR SWEEP FILTER\n"
                "  SWEEP = price breached prior session H/L in last 5 bars\n"
                "  Does a prior sweep improve OB quality?",
                [(k,v) for k,v in by_sweep.items()], min_n=5)

    print_table("SECTION 3 — MOMENTUM ALIGNMENT FILTER\n"
                "  MOM_YES = preceding bars showed counter-direction momentum\n"
                "  (BULL_OB needs 2+ bearish bars before it, BEAR_OB needs bullish)",
                [(k,v) for k,v in by_momentum.items()], min_n=5)

    print_table("SECTION 4 — IMPULSE STRENGTH FILTER\n"
                f"  IMP_STR = sum of |returns| in {LOOKBACK_BARS} preceding bars >= {STRONG_IMPULSE}%\n"
                "  Does a strong preceding move predict a better OB?",
                [(k,v) for k,v in by_impulse.items()], min_n=5)

    print_table("SECTION 5 — TIME ZONE FILTER\n"
                "  Which session window produces the strongest patterns?",
                [(k,v) for k,v in by_timezone.items()], min_n=5)

    print_table("SECTION 6 — COMBINED FILTER (sweep|momentum|impulse)\n"
                "  Highest-conviction setups: all three filters aligned",
                [(k,v) for k,v in by_combo.items()], min_n=5)

    # Filter effectiveness summary
    print(f"\n{'='*110}")
    print("  SECTION 7 — FILTER LIFT SUMMARY")
    print("  How much does each filter add over baseline?")
    print(f"{'='*110}")
    print(f"  {'Pattern':<12}  {'Baseline':>10}  {'+Sweep':>8}  "
          f"{'+Momentum':>11}  {'+Impulse':>10}  Best filter")
    print(f"  {'-'*75}")

    for pat in sorted(TARGET_PATTERNS):
        base  = by_baseline.get(pat)
        sw_y  = by_sweep.get(f"{pat}|SWEEP")
        mo_y  = by_momentum.get(f"{pat}|MOM_YES")
        imp_y = by_impulse.get(f"{pat}|IMP_STR")

        base_e  = base.stats(30)["exp"]  if base  and base.stats(30)  else None
        sw_e    = sw_y.stats(30)["exp"]  if sw_y  and sw_y.stats(30)  else None
        mo_e    = mo_y.stats(30)["exp"]  if mo_y  and mo_y.stats(30)  else None
        imp_e   = imp_y.stats(30)["exp"] if imp_y and imp_y.stats(30) else None

        filters = {"Sweep": sw_e, "Momentum": mo_e, "Impulse": imp_e}
        best_f  = max(filters, key=lambda k: filters[k] or -999)
        best_e  = filters[best_f]
        lift    = (best_e - base_e) if (best_e and base_e) else None

        print(f"  {pat:<12}  {fmt(base_e):>10}  {fmt(sw_e):>8}  "
              f"{fmt(mo_e):>11}  {fmt(imp_e):>10}  "
              f"{best_f}: {fmt(best_e)} "
              f"({'lift: '+fmt(lift) if lift else 'n/a'})")

    print(f"\n{'='*110}")
    print("  INTERPRETATION")
    print("  Strong filter: adds >10% to expectancy AND lifts WR above 85%")
    print("  If SWEEP|MOM_YES|IMP_STR combo shows >100% expectancy with >90% WR,")
    print("  add it as a signal quality check in the MERDIAN signal engine.")
    print("  Lower-quality OBs (no sweep, no momentum alignment) → skip or reduce size.")
    print(f"{'='*110}\n")


if __name__ == "__main__":
    main()


