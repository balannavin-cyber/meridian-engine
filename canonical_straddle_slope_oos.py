#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_straddle_slope_oos.py
================================
Temporal out-of-sample validation for the straddle slope finding.

PROTOCOL
--------
1. Load straddle_slope_event_<run>.csv and straddle_slope_baseline_<run>.csv
   from the bug-fixed run of canonical_straddle_slope.py.
2. Split temporally:
     TRAIN  : t_move in [2025-04-01, 2025-10-31]   (7 months)
     TEST   : t_move in [2025-11-01, 2026-03-31]   (5 months)
3. Build percentile-rank scale from TRAIN BASELINE ONLY:
     train_baseline_slopes = baseline events in train period
     For any event slope, its percentile rank = searchsorted in train_baseline_slopes
4. Apply this TRAIN-derived scale to BOTH train and test event cohorts.
5. Compare median event-percentile-rank in train vs test per (symbol, direction).

FOCUS CELL
----------
SENSEX DOWN — only cell that landed WEAK (+8pp above baseline) in the
post-fix full-cohort run. Tests whether this is real signal or full-cohort
overstatement (the failure mode that broke the PCR cell at OOS).

VERDICT TAXONOMY
----------------
For each cell with N>=30 on both halves:
  PRESERVED   : train rank>=55 AND test rank>=55 (signal holds both ways)
  DECAYED     : train rank>=55, test rank in [50, 55)
  DEAD        : train rank>=55, test rank in (45, 50)
  REVERSED    : train rank>=55, test rank<45
  WEAK_BOTH   : both halves in [52, 60) (consistent weak)
  NULL        : both halves in (45, 55)
  ANTI        : both halves < 45

INPUTS
------
output_canonical_ict/straddle_slope_event_<RUN>.csv  (from post-fix run)
output_canonical_ict/straddle_slope_baseline_<RUN>.csv

OUTPUTS
-------
output_canonical_ict/straddle_slope_oos_verdict_<RUN>.csv
Console: side-by-side train/test percentile-rank stats
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


OUT_DIR = Path("output_canonical_ict")

TRAIN_START = pd.Timestamp("2025-04-01")
TRAIN_END = pd.Timestamp("2025-10-31 23:59:59")
TEST_START = pd.Timestamp("2025-11-01")
TEST_END = pd.Timestamp("2026-03-31 23:59:59")


def find_latest_event_csv(out_dir: Path) -> tuple[Path, str]:
    files = list(out_dir.glob("straddle_slope_event_*.csv"))
    if not files:
        sys.exit("ERROR: no straddle_slope_event_*.csv — run canonical_straddle_slope.py (post-fix) first")
    latest = max(files, key=lambda f: f.stat().st_mtime)
    rest = latest.stem[len("straddle_slope_event_"):]
    return latest, rest


def classify_verdict(train_rank: float, train_n: int,
                     test_rank: float, test_n: int,
                     min_n: int = 30) -> str:
    if train_n < min_n or test_n < min_n:
        return "INSUFFICIENT_N"
    if train_rank >= 55 and test_rank >= 55:
        return "PRESERVED"
    if train_rank >= 55 and test_rank >= 50:
        return "DECAYED"
    if train_rank >= 55 and test_rank > 45:
        return "DEAD"
    if train_rank >= 55:
        return "REVERSED"
    if 52 <= train_rank < 60 and 52 <= test_rank < 60:
        return "WEAK_BOTH"
    if train_rank < 45 and test_rank < 45:
        return "ANTI"
    return "NULL"


def main():
    ap = argparse.ArgumentParser()
    args = ap.parse_args()

    event_path, run_tag = find_latest_event_csv(OUT_DIR)
    baseline_path = OUT_DIR / f"straddle_slope_baseline_{run_tag}.csv"
    if not baseline_path.exists():
        sys.exit(f"ERROR: {baseline_path} not found")

    events = pd.read_csv(event_path)
    baseline = pd.read_csv(baseline_path)
    print(f"loaded events: {event_path.name}  (run_tag={run_tag})")
    print(f"loaded baseline: {baseline_path.name}")

    events["t_move"] = pd.to_datetime(events["t_move"])
    baseline["t_move"] = pd.to_datetime(baseline["t_move"])

    # Filter to OK state + valid normalized_slope
    events = events[(events["state"] == "OK") & events["normalized_slope"].notna()].copy()
    baseline = baseline[(baseline["state"] == "OK") & baseline["normalized_slope"].notna()].copy()
    print(f"  valid events: {len(events)}")
    print(f"  valid baseline: {len(baseline)}")

    # Temporal split
    events["period"] = "OTHER"
    events.loc[(events["t_move"] >= TRAIN_START) & (events["t_move"] <= TRAIN_END), "period"] = "TRAIN"
    events.loc[(events["t_move"] >= TEST_START) & (events["t_move"] <= TEST_END), "period"] = "TEST"
    baseline["period"] = "OTHER"
    baseline.loc[(baseline["t_move"] >= TRAIN_START) & (baseline["t_move"] <= TRAIN_END), "period"] = "TRAIN"
    baseline.loc[(baseline["t_move"] >= TEST_START) & (baseline["t_move"] <= TEST_END), "period"] = "TEST"

    print(f"\n  events  TRAIN={len(events[events['period']=='TRAIN'])}  TEST={len(events[events['period']=='TEST'])}  OTHER={len(events[events['period']=='OTHER'])}")
    print(f"  baseline TRAIN={len(baseline[baseline['period']=='TRAIN'])}  TEST={len(baseline[baseline['period']=='TEST'])}  OTHER={len(baseline[baseline['period']=='OTHER'])}")

    # Compute TRAIN-derived percentile scale per symbol
    syms = sorted(events["symbol"].unique())
    print("\n--- TRAIN baseline percentile scales ---")
    train_scales = {}
    for sym in syms:
        train_b = baseline[(baseline["symbol"] == sym) & (baseline["period"] == "TRAIN")]["normalized_slope"].values
        if len(train_b) < 30:
            print(f"  [{sym}] TRAIN baseline too thin (n={len(train_b)}); skip")
            continue
        train_scales[sym] = np.sort(train_b)
        print(f"  [{sym}] TRAIN baseline n={len(train_b)} "
              f"median={np.median(train_b):+.4f} q25={np.percentile(train_b,25):+.4f} q75={np.percentile(train_b,75):+.4f}")

    # Compute percentile ranks for events using TRAIN scales
    def rank_in(scale, val):
        return float(np.searchsorted(scale, val, side="right")) / len(scale) * 100

    rows = []
    for sym in syms:
        if sym not in train_scales:
            continue
        scale = train_scales[sym]
        for direction in ["UP", "DOWN"]:
            for period in ["TRAIN", "TEST"]:
                sub = events[(events["symbol"] == sym)
                              & (events["direction"] == direction)
                              & (events["period"] == period)]
                if sub.empty:
                    continue
                ranks = np.array([rank_in(scale, v) for v in sub["normalized_slope"].values])
                rows.append({
                    "symbol": sym,
                    "direction": direction,
                    "period": period,
                    "n_events": len(ranks),
                    "median_rank": round(float(np.median(ranks)), 1),
                    "q25_rank": round(float(np.percentile(ranks, 25)), 1),
                    "q75_rank": round(float(np.percentile(ranks, 75)), 1),
                    "median_slope": round(float(np.median(sub["normalized_slope"])), 4),
                })

    rank_df = pd.DataFrame(rows)
    rank_df.to_csv(OUT_DIR / f"straddle_slope_oos_detail_{run_tag}.csv", index=False)

    # Build verdict per (symbol, direction)
    print("\n" + "=" * 78)
    print("STRADDLE SLOPE OOS RESULTS  (TRAIN baseline used for both halves' percentile rank)")
    print("=" * 78)
    print(f"\n  TRAIN: [{TRAIN_START.date()} -> {TRAIN_END.date()}]")
    print(f"  TEST:  [{TEST_START.date()} -> {TEST_END.date()}]")

    print("\nPercentile-rank distributions per (symbol, direction, period):")
    print(rank_df.to_string(index=False))

    # Verdict per cell
    verdicts = []
    for sym in syms:
        for direction in ["UP", "DOWN"]:
            train_row = rank_df[(rank_df["symbol"] == sym)
                                 & (rank_df["direction"] == direction)
                                 & (rank_df["period"] == "TRAIN")]
            test_row = rank_df[(rank_df["symbol"] == sym)
                                & (rank_df["direction"] == direction)
                                & (rank_df["period"] == "TEST")]
            if train_row.empty or test_row.empty:
                continue
            t = train_row.iloc[0]
            te = test_row.iloc[0]
            v = classify_verdict(t["median_rank"], t["n_events"],
                                  te["median_rank"], te["n_events"])
            verdicts.append({
                "symbol": sym,
                "direction": direction,
                "train_n": int(t["n_events"]),
                "train_rank": t["median_rank"],
                "test_n": int(te["n_events"]),
                "test_rank": te["median_rank"],
                "rank_delta": round(te["median_rank"] - t["median_rank"], 1),
                "verdict": v,
            })
    vdf = pd.DataFrame(verdicts)
    vdf.to_csv(OUT_DIR / f"straddle_slope_oos_verdict_{run_tag}.csv", index=False)

    print("\nVERDICT TABLE:")
    print(vdf.to_string(index=False))

    # Focus on SENSEX DOWN
    print("\n" + "=" * 78)
    print("FOCUS: SENSEX DOWN (the WEAK cell from post-fix full-cohort run)")
    print("=" * 78)
    focus = vdf[(vdf["symbol"] == "SENSEX") & (vdf["direction"] == "DOWN")]
    if focus.empty:
        print("  (no row found)")
    else:
        r = focus.iloc[0]
        print(f"  TRAIN: N={r['train_n']}, median rank={r['train_rank']}")
        print(f"  TEST:  N={r['test_n']},  median rank={r['test_rank']}")
        print(f"  DELTA: {r['rank_delta']:+}pp  ({r['verdict']})")
        if r["verdict"] == "PRESERVED":
            print("\n  -> SENSEX DOWN signal PRESERVED on held-out test half.")
            print("     Combined with Stage 4 findings (regime flip rate, LONG->SHORT flip),")
            print("     this is a coherent multi-axis pre-move signature for SENSEX DOWN moves.")
        elif r["verdict"] in ("DECAYED", "DEAD"):
            print("\n  -> SENSEX DOWN signal weakened on test half. Full-cohort overstated.")
            print("     Findings are best read as descriptive characterization, not predictive edge.")
        elif r["verdict"] == "REVERSED":
            print("\n  -> SENSEX DOWN signal REVERSED on test. Full-cohort was forking-paths.")
        elif r["verdict"] == "WEAK_BOTH":
            print("\n  -> SENSEX DOWN borderline-significant on both halves. Real but marginal.")
        else:
            print(f"\n  -> {r['verdict']}: see verdict table above for context.")

    print(f"\noutputs: {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
