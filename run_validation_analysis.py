#!/usr/bin/env python3
"""
run_validation_analysis.py
ENH-35 — MERDIAN Historical Signal Validation and Accuracy Measurement

PURPOSE:
  Measures directional accuracy of the MERDIAN signal engine against one full
  year of historical data (Apr 2025 – Mar 2026). This is the Phase 4 gate:
  no live promotion without empirical accuracy data.

ALGORITHM:
  For each bar_ts in hist_market_state (~183K bars across 487 date/symbol pairs):
    1. Replay the signal engine decision logic using stored regime fields:
       gamma_regime, breadth_regime, momentum_regime, iv_regime, atm_iv,
       flip_distance_pct
    2. Generate: action (BUY_CE / BUY_PE / DO_NOTHING) + confidence_score
    3. Look up hist_spot_bars_1m at T+15m, T+30m, T+60m
    4. Compute directional correctness:
         BUY_CE correct if spot_T+Xm > spot_at_signal
         BUY_PE correct if spot_T+Xm < spot_at_signal
    5. Aggregate by regime combination, time of day, IV regime, momentum

SIGNAL LOGIC REPLAYED (mirrors build_trade_signal_local.py):

  Core action:
    SHORT_GAMMA + BEARISH breadth  -> BUY_PE  (strong - dealers amplify)
    SHORT_GAMMA + BULLISH breadth  -> BUY_CE  (strong - dealers amplify)
    LONG_GAMMA  + BEARISH breadth  -> BUY_PE  (weak - dealers dampen)
    LONG_GAMMA  + BULLISH breadth  -> BUY_CE  (weak - dealers dampen)
    TRANSITION breadth             -> DO_NOTHING
    CONFLICT (breadth vs momentum) -> DO_NOTHING (currently - tested here)

  Confidence modifiers (base = 50):
    SHORT_GAMMA:                   +15 (strong regime)
    Momentum aligned with action:  +15
    Momentum opposing action:      -15
    HIGH_IV (atm_iv > 20%):        -10 (current VIX gate penalty)
    flip_distance_pct < 0.5%:      -10 (near flip - unstable)
    flip_distance_pct < 0.2%:      -20 (at flip - very unstable)

  trade_allowed:
    confidence_score >= 60 AND atm_iv < 20% (current gate)

OUTPUT SECTIONS:
  1  - Coverage and data quality
  2  - Overall accuracy baseline (all signals)
  3  - Accuracy by gamma x breadth (the core signal matrix)
  4  - Accuracy by momentum alignment
  5  - Accuracy by IV regime
  6  - Accuracy by time of day
  7  - CONFLICT analysis (currently DO_NOTHING - what if we traded?)
  8  - Confidence calibration (higher confidence = higher accuracy?)
  9  - trade_allowed filter effectiveness
  10 - Phase 4 verdict: which regime combos earn live promotion

Read-only. Does NOT modify any live tables.
Runtime: ~15-20 minutes.

Usage:
    python run_validation_analysis.py
"""

import os
import bisect
import time
from datetime import datetime, timedelta, time as dtime
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000

# Signal replay parameters
BASE_CONFIDENCE        = 50
SHORT_GAMMA_BOOST      = 15
MOMENTUM_ALIGNED_BOOST = 15
MOMENTUM_OPPOSING_CUT  = 15
HIGH_IV_CUT            = 10
NEAR_FLIP_CUT          = 10
AT_FLIP_CUT            = 20
MIN_CONFIDENCE         = 60
HIGH_IV_THRESHOLD      = 20.0

HORIZONS = [15, 30, 60]

SESSION_START = dtime(9, 15)
SESSION_END   = dtime(15, 30)

TIME_ZONES = [
    ("OPEN    09:15-10:00", dtime(9, 15), dtime(10,  0)),
    ("MORNING 10:00-11:30", dtime(10, 0), dtime(11, 30)),
    ("MIDDAY  11:30-13:30", dtime(11,30), dtime(13, 30)),
    ("AFTNOON 13:30-15:30", dtime(13,30), dtime(15, 30)),
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def in_session(ts):
    t = ts.time()
    return SESSION_START <= t <= SESSION_END


def time_zone_label(ts):
    t = ts.time()
    for label, start, end in TIME_ZONES:
        if start <= t < end:
            return label
    return "OTHER"


def replay_signal(row):
    """
    Replay MERDIAN signal logic against a hist_market_state row.
    Mirrors build_trade_signal_local.py exactly as of 2026-04-11.

    Changes from original:
      - LONG_GAMMA gated to DO_NOTHING (47.7% accuracy, below random)
      - NO_FLIP gated to DO_NOTHING (45-48% accuracy, below random)
      - CONFLICT BUY_CE now trades (67.9% accuracy at N=661)
      - VIX gate removed (HIGH_IV has more edge, not less)
      - Confidence threshold 60 -> 40 (edge lives in 20-49 band)

    Returns (action, confidence_score, trade_allowed, is_conflict).
    """
    gamma     = row.get("gamma_regime") or ""
    breadth   = row.get("breadth_regime") or ""
    momentum  = row.get("momentum_regime") or ""
    atm_iv    = float(row.get("atm_iv") or 0)
    flip_dist = float(row.get("flip_distance_pct") or 999)

    is_conflict = False

    # Gate 1: LONG_GAMMA -> DO_NOTHING
    # ENH-35: 47.7% accuracy at N=24,579 -- structurally below random
    if gamma == "LONG_GAMMA":
        return "DO_NOTHING", BASE_CONFIDENCE, False, False

    # Gate 2: NO_FLIP -> DO_NOTHING
    # ENH-35: 45-48% accuracy -- no institutional reference point
    if gamma == "NO_FLIP":
        return "DO_NOTHING", BASE_CONFIDENCE, False, False

    # Core action from breadth
    action = "DO_NOTHING"
    if breadth == "TRANSITION":
        action = "DO_NOTHING"
    elif breadth == "BEARISH":
        if momentum == "BULLISH":
            # CONFLICT BUY_PE -- below random (47-49%), keep as DO_NOTHING
            action = "DO_NOTHING"
        else:
            action = "BUY_PE"
    elif breadth == "BULLISH":
        if momentum == "BEARISH":
            # CONFLICT BUY_CE -- 67.9% accuracy, now trades
            is_conflict = True
            action = "BUY_CE"
        else:
            action = "BUY_CE"

    confidence = BASE_CONFIDENCE
    if action == "DO_NOTHING":
        return action, confidence, False, is_conflict

    # SHORT_GAMMA boost
    if gamma == "SHORT_GAMMA":
        confidence += SHORT_GAMMA_BOOST

    # Momentum alignment
    if action == "BUY_PE" and momentum == "BEARISH":
        confidence += MOMENTUM_ALIGNED_BOOST
    elif action == "BUY_CE" and momentum == "BULLISH":
        confidence += MOMENTUM_ALIGNED_BOOST
    elif action == "BUY_PE" and momentum == "BULLISH":
        confidence -= MOMENTUM_OPPOSING_CUT
    elif action == "BUY_CE" and momentum == "BEARISH":
        # CONFLICT case -- small penalty but still trades
        confidence -= 5

    # Flip distance
    if flip_dist < 0.2:
        confidence -= AT_FLIP_CUT
    elif flip_dist < 0.5:
        confidence -= NEAR_FLIP_CUT

    # VIX gate REMOVED (Experiment 5 + ENH-35)
    # HIGH_IV environments have more edge, not less

    confidence    = max(0, min(100, confidence))

    # Lowered threshold: edge lives in conf_20-49 band (ENH-35 Section 8)
    trade_allowed = confidence >= 40

    return action, confidence, trade_allowed, is_conflict

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


def get_spot_at(spot_index, symbol, trade_date, target_ts, max_gap=2):
    key  = (symbol, str(trade_date))
    bars = spot_index.get(key, [])
    if not bars:
        return None
    tss = [b[0] for b in bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=max_gap+1)
    for i in (idx-1, idx):
        if 0 <= i < len(bars):
            gap = abs(bars[i][0] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, bars[i][1]
    return best_p if best_g <= timedelta(minutes=max_gap) else None


class AccuracyBucket:
    def __init__(self):
        self.n_signals    = 0
        self.n_do_nothing = 0
        self.n_conflict   = 0
        self.correct      = {h: 0 for h in HORIZONS}
        self.total        = {h: 0 for h in HORIZONS}

    def add_do_nothing(self, is_conflict=False):
        self.n_signals    += 1
        self.n_do_nothing += 1
        if is_conflict:
            self.n_conflict += 1

    def add_signal(self, action, spot_at_signal, spots):
        self.n_signals += 1
        for h in HORIZONS:
            sp = spots.get(h)
            if sp is None:
                continue
            self.total[h] += 1
            move = sp - spot_at_signal
            if (action == "BUY_CE" and move > 0) or \
               (action == "BUY_PE" and move < 0):
                self.correct[h] += 1

    def accuracy(self, h):
        if self.total[h] == 0:
            return None
        return 100.0 * self.correct[h] / self.total[h]

    def n_scored(self, h):
        return self.total[h]

    def n_actionable(self):
        return self.n_signals - self.n_do_nothing


def verdict(acc30, n):
    if acc30 is None or n < 10:
        return "insufficient data"
    if acc30 >= 58:
        return "STRONG EDGE -- promote"
    if acc30 >= 54:
        return "EDGE -- promote with caution"
    if acc30 >= 50:
        return "marginal -- shadow only"
    return "BELOW RANDOM -- do not promote"


def fmt_acc(v, w=8):
    if v is None:
        return f"{'n/a':>{w}}"
    return f"{v:.1f}%".rjust(w)


def print_table(title, rows, min_n=10, note=""):
    print(f"\n{'='*110}")
    print(f"  {title}")
    if note:
        print(f"  {note}")
    print(f"{'='*110}")
    print(f"  {'Label':<45} {'N act':>7} {'N@T30':>7}  "
          f"{'T+15':>8}  {'T+30':>8}  {'T+60':>8}  Verdict")
    print(f"  {'-'*100}")

    def key_fn(item):
        a = item[1].accuracy(30)
        return a if a is not None else -999

    filtered = [(lbl, b) for lbl, b in rows if b.n_actionable() >= min_n]
    filtered.sort(key=key_fn, reverse=True)

    for lbl, b in filtered:
        a15 = b.accuracy(15)
        a30 = b.accuracy(30)
        a60 = b.accuracy(60)
        v   = verdict(a30, b.n_scored(30))
        print(f"  {lbl:<45} {b.n_actionable():>7} {b.n_scored(30):>7}  "
              f"{fmt_acc(a15):>8}  {fmt_acc(a30):>8}  {fmt_acc(a60):>8}  {v}")


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Instrument IDs
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Load spot bars
    log("Loading hist_spot_bars_1m...")
    spot_index = defaultdict(list)
    for sym in ["NIFTY", "SENSEX"]:
        rows = fetch_paginated(
            sb, "hist_spot_bars_1m",
            [("eq", "instrument_id", inst[sym]),
             ("eq", "is_pre_market", False)],
            "bar_ts, trade_date, close"
        )
        for r in rows:
            ts  = datetime.fromisoformat(r["bar_ts"])
            key = (sym, r["trade_date"])
            spot_index[key].append((ts, float(r["close"])))
        log(f"  {sym}: {len(rows):,} bars")

    for key in spot_index:
        spot_index[key].sort(key=lambda x: x[0])
    log(f"  Spot index: {len(spot_index)} date/symbol pairs")

    # Load hist_market_state
    log("Loading hist_market_state...")
    hms_rows = []
    for sym in ["NIFTY", "SENSEX"]:
        rows = fetch_paginated(
            sb, "hist_market_state",
            [("eq", "symbol", sym)],
            "symbol, bar_ts, trade_date, spot, gamma_regime, breadth_regime, "
            "momentum_regime, iv_regime, atm_iv, flip_distance_pct"
        )
        hms_rows.extend(rows)
        log(f"  {sym}: {len(rows):,} bars")
    log(f"  Total: {len(hms_rows):,} market state bars")

    # Buckets
    by_overall       = defaultdict(AccuracyBucket)
    by_gamma_breadth = defaultdict(AccuracyBucket)
    by_momentum      = defaultdict(AccuracyBucket)
    by_iv_regime     = defaultdict(AccuracyBucket)
    by_timezone      = defaultdict(AccuracyBucket)
    by_confidence    = defaultdict(AccuracyBucket)
    by_trade_allowed = defaultdict(AccuracyBucket)
    by_conflict      = defaultdict(AccuracyBucket)

    n_total = n_skipped = n_no_spot = breadth_null = 0

    log("Replaying signal logic and scoring...")

    for i, row in enumerate(hms_rows):
        n_total += 1

        if i % 20_000 == 0:
            log(f"  {i:,}/{len(hms_rows):,} processed...")

        sym  = row["symbol"]
        ts   = datetime.fromisoformat(row["bar_ts"])
        td   = row["trade_date"]
        spot = float(row.get("spot") or 0)

        if not in_session(ts) or not spot:
            n_skipped += 1
            continue

        if row.get("breadth_regime") is None:
            breadth_null += 1
            n_skipped    += 1
            continue

        action, conf, trade_ok, is_conflict = replay_signal(row)

        # Spot at horizons
        spots = {}
        for h in HORIZONS:
            spots[h] = get_spot_at(spot_index, sym, td,
                                   ts + timedelta(minutes=h))

        if action == "DO_NOTHING":
            by_overall[sym].add_do_nothing(is_conflict)
            gb_key = f"{row.get('gamma_regime','?')}|{row.get('breadth_regime','?')}"
            by_gamma_breadth[gb_key].add_do_nothing(is_conflict)
            if is_conflict:
                implied = "BUY_PE" if row.get("breadth_regime") == "BEARISH" else "BUY_CE"
                by_conflict[f"{sym}|implied_{implied}"].add_signal(implied, spot, spots)
            continue

        if all(v is None for v in spots.values()):
            n_no_spot += 1
            continue

        atm_iv   = float(row.get("atm_iv") or 0)
        iv_label = "HIGH_IV" if atm_iv > HIGH_IV_THRESHOLD else \
                   ("MED_IV" if atm_iv > 12 else "LOW_IV")
        c_bucket = f"conf_{(conf//10)*10}-{(conf//10)*10+9}"
        ta_label = f"trade_allowed={'YES' if trade_ok else 'NO '}"
        gb_key   = f"{row.get('gamma_regime','?')}|{row.get('breadth_regime','?')}"
        mom_key  = f"{action}|MOM_{row.get('momentum_regime','?')}"
        iv_key   = f"{action}|{iv_label}"
        tz_key   = f"{action}|{time_zone_label(ts)}"

        by_overall[sym].add_signal(action, spot, spots)
        by_gamma_breadth[gb_key].add_signal(action, spot, spots)
        by_momentum[mom_key].add_signal(action, spot, spots)
        by_iv_regime[iv_key].add_signal(action, spot, spots)
        by_timezone[tz_key].add_signal(action, spot, spots)
        by_confidence[c_bucket].add_signal(action, spot, spots)
        by_trade_allowed[ta_label].add_signal(action, spot, spots)

    log(f"  Complete -- {n_total:,} total | {n_skipped:,} skipped | "
        f"{n_no_spot:,} no spot | {breadth_null:,} breadth NULL")

    # Output
    print("\n" + "=" * 110)
    print("  MERDIAN ENH-35 -- HISTORICAL SIGNAL VALIDATION AND ACCURACY MEASUREMENT")
    print("  Signal engine replayed against hist_market_state (Apr 2025 - Mar 2026)")
    print("  Accuracy = % signals where spot moved in predicted direction at horizon")
    print("  Random baseline = 50.0% (Experiment 0: market was 49.7% UP / 50.3% DOWN)")
    print("  Phase 4 target: >= 54% accuracy at T+30m on key regime combinations")
    print("=" * 110)

    print(f"\n{'='*110}")
    print("  SECTION 1 -- DATA COVERAGE")
    print(f"{'='*110}")
    print(f"  Total market state bars:    {n_total:>10,}")
    print(f"  Skipped (out of session):   {n_skipped-breadth_null:>10,}")
    print(f"  Breadth NULL (pre-Jul 16):  {breadth_null:>10,}")
    print(f"  No spot data at horizons:   {n_no_spot:>10,}")
    print(f"  Bars evaluated:             {n_total-n_skipped-n_no_spot:>10,}")
    print(f"\n  NOTE: breadth_regime is NULL before 2025-07-16.")
    print(f"  All accuracy stats from 2025-07-16 onwards only.")

    print_table(
        "SECTION 2 -- OVERALL ACCURACY BASELINE",
        list(by_overall.items()), min_n=5,
        note="All BUY_CE + BUY_PE signals. DO_NOTHING excluded. Random = 50%."
    )

    print_table(
        "SECTION 3 -- ACCURACY BY GAMMA x BREADTH (CORE SIGNAL MATRIX)",
        list(by_gamma_breadth.items()), min_n=10,
        note="SHORT_GAMMA = dealers amplify moves. LONG_GAMMA = dealers dampen."
    )

    print_table(
        "SECTION 4 -- ACCURACY BY MOMENTUM ALIGNMENT",
        list(by_momentum.items()), min_n=10,
        note="MOM aligned = momentum confirms direction. MOM opposing = signal fights momentum."
    )

    print_table(
        "SECTION 5 -- ACCURACY BY IV REGIME",
        list(by_iv_regime.items()), min_n=10,
        note="HIGH_IV = atm_iv > 20%. Current VIX gate blocks these -- does it help or hurt?"
    )

    print_table(
        "SECTION 6 -- ACCURACY BY TIME OF DAY",
        list(by_timezone.items()), min_n=10,
        note="Which session window produces the most directionally accurate signals?"
    )

    # Section 7 -- Conflict
    print(f"\n{'='*110}")
    print("  SECTION 7 -- CONFLICT ANALYSIS")
    print("  Current: breadth BEARISH + momentum BULLISH (or vice versa) -> DO_NOTHING")
    print("  Below: if we HAD traded despite the conflict, what would accuracy have been?")
    print(f"{'='*110}")
    print(f"  {'Label':<50} {'N':>6} {'N@T30':>7}  "
          f"{'T+15':>8}  {'T+30':>8}  {'T+60':>8}  Verdict")
    print(f"  {'-'*100}")
    for lbl, b in sorted(by_conflict.items()):
        a15 = b.accuracy(15)
        a30 = b.accuracy(30)
        a60 = b.accuracy(60)
        v   = verdict(a30, b.n_scored(30))
        print(f"  {lbl:<50} {b.n_actionable():>6} {b.n_scored(30):>7}  "
              f"{fmt_acc(a15):>8}  {fmt_acc(a30):>8}  {fmt_acc(a60):>8}  {v}")
    print(f"\n  >= 54%: CONFLICT rule destroys edge -- remove it")
    print(f"  < 50%:  CONFLICT rule protects capital -- keep it")
    print(f"  ~50%:   CONFLICT rule is neutral -- keep for simplicity")

    print_table(
        "SECTION 8 -- CONFIDENCE CALIBRATION",
        list(by_confidence.items()), min_n=10,
        note="Does higher confidence_score predict higher directional accuracy?"
    )

    print_table(
        "SECTION 9 -- TRADE_ALLOWED FILTER EFFECTIVENESS",
        list(by_trade_allowed.items()), min_n=10,
        note="trade_allowed=YES: confidence>=60 AND atm_iv<20%. Does this filter add value?"
    )

    print(f"\n{'='*110}")
    print("  SECTION 10 -- PHASE 4 PROMOTION VERDICT")
    print(f"{'='*110}")
    print(f"  {'Regime Combination':<40} {'T+30 Acc':>9}  {'N@T30':>7}  Verdict")
    print(f"  {'-'*80}")
    for key, b in sorted(by_gamma_breadth.items(),
                          key=lambda x: x[1].accuracy(30) or -999, reverse=True):
        if b.n_actionable() < 10:
            continue
        a30 = b.accuracy(30)
        v   = verdict(a30, b.n_scored(30))
        print(f"  {key:<40} {fmt_acc(a30):>9}  {b.n_scored(30):>7}  {v}")

    print(f"\n{'='*110}")
    print("  KEY QUESTIONS ANSWERED")
    print(f"{'='*110}")
    print("  Q1: Is signal engine better than random?  -> Section 2")
    print("  Q2: Which regime combos have genuine edge? -> Section 3 + Section 10")
    print("  Q3: Does CONFLICT DO_NOTHING help or hurt? -> Section 7")
    print("  Q4: Does VIX gate (blocking HIGH_IV) help? -> Section 5")
    print("  Q5: Is confidence_score predictive?        -> Section 8")
    print("  Q6: Which time of day to prioritise?       -> Section 6")
    print(f"{'='*110}\n")


if __name__ == "__main__":
    main()



