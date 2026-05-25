#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ob_pcr_oos.py
=======================
Out-of-sample validation for the PCR-stratified OB precision result.

PROTOCOL
--------
1. Load the existing PCR detail CSV (ob_pcr_detail_<run>.csv).
2. Split entries temporally:
     TRAIN  : entry_ts in [2025-04-01, 2025-10-31]   (7 months)
     TEST   : entry_ts in [2025-11-01, 2026-03-31]   (5 months)
   No randomization. Calendar order = real out-of-sample structure.
3. Compute PCR tertile thresholds (33rd / 67th percentile) FROM TRAIN COHORT
   ONLY, per symbol.
4. Apply those train-derived thresholds to BOTH halves to classify entries
   as LOW / MID / HIGH.
5. Compute precision + wrong-way per cell on each half.
6. Side-by-side comparison.

HYPOTHESIS UNDER TEST
---------------------
The SENSEX BEAR_OB + MID PCR cell showed +43.9pp spread (precision 60.3%,
wrong-way 16.4%, N=116) on the full cohort. Does it preserve on TEST? If
yes -> real pattern. If train edge >> test edge -> garden of forking paths
on the original result.

Same question applies to any cell that looked elevated in the full-cohort
matrix. Verdict per cell: PRESERVED / DECAYED / REVERSED.

INPUTS
------
output_canonical_ict/ob_pcr_detail_<run>.csv

OUTPUTS
-------
output_canonical_ict/ob_pcr_oos_train_summary_<run>.csv
output_canonical_ict/ob_pcr_oos_test_summary_<run>.csv
output_canonical_ict/ob_pcr_oos_verdict_<run>.csv
Console: train/test matrices side-by-side + verdict table
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


def find_latest_pcr_detail(out_dir: Path) -> tuple[Path, str]:
    files = list(out_dir.glob("ob_pcr_detail_*.csv"))
    if not files:
        sys.exit(f"ERROR: no ob_pcr_detail_*.csv in {out_dir.absolute()} — run canonical_ob_pcr.py first")
    latest = max(files, key=lambda f: f.stat().st_mtime)
    # extract run_tag from filename
    rest = latest.stem[len("ob_pcr_detail_"):]
    return latest, rest


def assign_tertiles_from_thresholds(df: pd.DataFrame, value_col: str,
                                     thresholds: dict, label_col: str) -> pd.DataFrame:
    """thresholds = {symbol: (p33, p67)}"""
    out = df.copy()
    out[label_col] = "NO_DATA"
    for sym, (p33, p67) in thresholds.items():
        mask = (out["symbol"] == sym) & out[value_col].notna()
        def cls(v):
            if pd.isna(v):
                return "NO_DATA"
            if v < p33:
                return "LOW"
            if v > p67:
                return "HIGH"
            return "MID"
        out.loc[mask, label_col] = out.loc[mask, value_col].apply(cls)
    return out


def summary_for(df: pd.DataFrame, tertile_col: str) -> pd.DataFrame:
    valid = df[df[tertile_col].isin(["LOW", "MID", "HIGH"])]
    if valid.empty:
        return pd.DataFrame()
    grp = valid.groupby(["symbol", "primitive_type", tertile_col])
    s = grp.agg(
        n=("matched", "size"),
        n_match=("matched", "sum"),
        n_wrong=("wrong_way", "sum"),
    ).reset_index()
    s["precision_pct"] = (s["n_match"] / s["n"] * 100).round(1)
    s["wrong_way_pct"] = (s["n_wrong"] / s["n"] * 100).round(1)
    s["spread_pp"] = (s["precision_pct"] - s["wrong_way_pct"]).round(1)
    return s


def print_matrix(s: pd.DataFrame, tertile_col: str, label: str):
    if s.empty:
        print(f"\n>>> {label}: (no data)")
        return
    print(f"\n>>> {label}")
    order = [c for c in ["LOW", "MID", "HIGH"] if c in s[tertile_col].unique()]
    for value, name in [("precision_pct", "PRECISION %"),
                         ("n", "N entries"),
                         ("wrong_way_pct", "WRONG-WAY %"),
                         ("spread_pp", "SPREAD pp")]:
        pv = s.pivot_table(index=["symbol", "primitive_type"],
                            columns=tertile_col, values=value, aggfunc="first")
        cols = [c for c in order if c in pv.columns]
        pv = pv[cols]
        if value == "n":
            pv = pv.astype("Int64")
        print(f"\n{name}")
        print(pv.to_string())


def build_verdict(train: pd.DataFrame, test: pd.DataFrame,
                   tertile_col: str, min_n: int = 30,
                   strong_edge_pp: float = 25.0,
                   weak_edge_pp: float = 10.0) -> pd.DataFrame:
    """For each (symbol, primitive_type, tertile) cell, classify the train->test transition."""
    if train.empty or test.empty:
        return pd.DataFrame()
    merged = train.merge(
        test,
        on=["symbol", "primitive_type", tertile_col],
        how="outer",
        suffixes=("_train", "_test"),
    )
    rows = []
    for _, r in merged.iterrows():
        train_n = int(r.get("n_train", 0) or 0)
        test_n = int(r.get("n_test", 0) or 0)
        train_spread = float(r.get("spread_pp_train", 0) or 0)
        test_spread = float(r.get("spread_pp_test", 0) or 0)
        train_prec = float(r.get("precision_pct_train", 0) or 0)
        test_prec = float(r.get("precision_pct_test", 0) or 0)
        train_adequate = train_n >= min_n
        test_adequate = test_n >= min_n

        # Classify
        if not (train_adequate and test_adequate):
            verdict = "INSUFFICIENT_N"
        elif train_spread >= strong_edge_pp:
            # Train showed edge — did test preserve?
            if test_spread >= strong_edge_pp * 0.6:
                verdict = "PRESERVED"
            elif test_spread >= weak_edge_pp:
                verdict = "DECAYED"
            elif test_spread > -weak_edge_pp:
                verdict = "DEAD"
            else:
                verdict = "REVERSED"
        elif train_spread >= weak_edge_pp:
            # Train weak — test should show at least weak
            if test_spread >= weak_edge_pp:
                verdict = "WEAK_BOTH"
            elif test_spread > -weak_edge_pp:
                verdict = "NULL"
            else:
                verdict = "REVERSED"
        elif train_spread <= -weak_edge_pp:
            # Train anti-edge — interesting if test reproduces
            if test_spread <= -weak_edge_pp:
                verdict = "ANTI_EDGE_PRESERVED"
            else:
                verdict = "NULL"
        else:
            # Train near zero — anything in test is noise
            verdict = "NULL"

        rows.append({
            "symbol": r["symbol"],
            "primitive_type": r["primitive_type"],
            "tertile": r[tertile_col],
            "train_n": train_n,
            "train_prec": train_prec,
            "train_spread": train_spread,
            "test_n": test_n,
            "test_prec": test_prec,
            "test_spread": test_spread,
            "verdict": verdict,
        })
    out = pd.DataFrame(rows)
    return out.sort_values(["symbol", "primitive_type", "tertile"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcr-variant", default="near", choices=["near", "total"],
                    help="which PCR variant to test (near or total)")
    args = ap.parse_args()

    detail_path, run_tag = find_latest_pcr_detail(OUT_DIR)
    print(f"loaded detail file: {detail_path.name}  (run_tag={run_tag})")
    df = pd.read_csv(detail_path)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"])
    pcr_col = f"pcr_{args.pcr_variant}"
    tertile_col = f"tertile_{args.pcr_variant}_oos"
    if pcr_col not in df.columns:
        sys.exit(f"ERROR: {pcr_col} not in detail CSV")
    # only keep rows with valid PCR + matched/wrong attached
    df = df[df[pcr_col].notna()].copy()
    df["matched"] = df["matched"].astype(bool)
    df["wrong_way"] = df["wrong_way"].astype(bool)
    print(f"  total rows with valid {pcr_col}: {len(df)}")

    train = df[(df["entry_ts"] >= TRAIN_START) & (df["entry_ts"] <= TRAIN_END)].copy()
    test = df[(df["entry_ts"] >= TEST_START) & (df["entry_ts"] <= TEST_END)].copy()
    print(f"  TRAIN [{TRAIN_START.date()} -> {TRAIN_END.date()}] : {len(train)} rows")
    print(f"  TEST  [{TEST_START.date()} -> {TEST_END.date()}]   : {len(test)} rows")
    if train.empty or test.empty:
        sys.exit("ERROR: one half is empty")

    # Compute tertile thresholds FROM TRAIN COHORT per symbol
    print("\n--- TRAIN-derived tertile thresholds (33rd / 67th percentile) ---")
    thresholds = {}
    for sym in train["symbol"].unique():
        vals = train.loc[train["symbol"] == sym, pcr_col].dropna()
        if vals.empty:
            continue
        p33 = float(vals.quantile(1/3))
        p67 = float(vals.quantile(2/3))
        thresholds[sym] = (p33, p67)
        print(f"  [{sym}] LOW <{p33:.3f} / MID / HIGH >{p67:.3f}  (train n={len(vals)})")

    # Apply train thresholds to both halves
    train = assign_tertiles_from_thresholds(train, pcr_col, thresholds, tertile_col)
    test = assign_tertiles_from_thresholds(test, pcr_col, thresholds, tertile_col)

    train_s = summary_for(train, tertile_col)
    test_s = summary_for(test, tertile_col)

    if not train_s.empty:
        train_s.to_csv(OUT_DIR / f"ob_pcr_oos_train_summary_{run_tag}.csv", index=False)
    if not test_s.empty:
        test_s.to_csv(OUT_DIR / f"ob_pcr_oos_test_summary_{run_tag}.csv", index=False)

    print("\n" + "=" * 78)
    print(f"TRAIN COHORT  [{TRAIN_START.date()} -> {TRAIN_END.date()}]")
    print("=" * 78)
    print_matrix(train_s, tertile_col, f"PCR_{args.pcr_variant} (TRAIN)")

    print("\n" + "=" * 78)
    print(f"TEST COHORT  [{TEST_START.date()} -> {TEST_END.date()}]")
    print("  (tertile thresholds derived from TRAIN only — applied to TEST as-is)")
    print("=" * 78)
    print_matrix(test_s, tertile_col, f"PCR_{args.pcr_variant} (TEST)")

    # Verdict table
    verdict = build_verdict(train_s, test_s, tertile_col)
    if not verdict.empty:
        verdict.to_csv(OUT_DIR / f"ob_pcr_oos_verdict_{run_tag}.csv", index=False)
        print("\n" + "=" * 78)
        print("VERDICT TABLE (cell-by-cell train vs test)")
        print("=" * 78)
        print(verdict.to_string(index=False))

        # Specific focus on cells that were elevated in the full-cohort run
        focus_cells = [
            ("SENSEX", "BEAR_OB", "MID"),  # the headline cell
            ("NIFTY",  "BULL_OB", "MID"),  # secondary
            ("NIFTY",  "BEAR_OB", "LOW"),  # anti-edge candidate
        ]
        print("\n--- FOCUS CELLS (originally elevated in full-cohort run) ---")
        for sym, prim, t in focus_cells:
            r = verdict[(verdict["symbol"] == sym)
                        & (verdict["primitive_type"] == prim)
                        & (verdict["tertile"] == t)]
            if r.empty:
                print(f"  {sym} {prim} {t}: (no row)")
                continue
            r = r.iloc[0]
            print(f"  {sym} {prim} {t}: train(N={r['train_n']}, "
                  f"prec={r['train_prec']:.1f}%, spread={r['train_spread']:+.1f}pp)  ->  "
                  f"test(N={r['test_n']}, prec={r['test_prec']:.1f}%, "
                  f"spread={r['test_spread']:+.1f}pp)  [{r['verdict']}]")

    print(f"\noutputs: {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
