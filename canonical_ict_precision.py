#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ict_precision.py
==========================
Precision pass for canonical_ict_recall.py outputs.

Pairs with canonical_ict_recall.py's recall pass. The recall pass asked:
  "Of all qualifying 30m moves, what fraction had a matching entry fire
   in [move_ts - 15m, move_ts]?"

This pass asks the symmetric question:
  "Of all entries that fired (per tier + mode), what fraction were followed
   by a qualifying 30m move in matching direction within
   [entry_ts, entry_ts + 15m]?"

The recall + precision pair gives the full picture:
  - Recall  measures coverage of moves
  - Precision measures signal quality of entries
  - Both at every HTF discipline tier (T0..T4)

DEFINITION OF MATCH
-------------------
Entry direction -> Move direction mapping: BULL -> UP, BEAR -> DOWN.

For each entry at entry_ts with direction D:
  - matched     = exists qualifying move with direction D in [entry_ts, entry_ts+15m]
  - wrong_way   = exists qualifying move with OPPOSITE direction in same window
  - no_move     = neither
(Note: matched and wrong_way can both be True if price went both ways within the
window. That's reported as a separate column.)

This precision is structurally paired with the recall pass — it does NOT use
spot bars; it uses the already-extracted move cohort. The window symmetry is
deliberate: a recall match at +0..15min before a move equals a precision match
at -15..0min before that same move.

INPUTS
------
output_canonical_ict/entries_<SYMBOL>_<RUNTAG>.csv
output_canonical_ict/moves_<SYMBOL>_<RUNTAG>.csv

OUTPUTS
-------
output_canonical_ict/precision_detail_<SYMBOL>_<RUNTAG>.csv
output_canonical_ict/precision_summary_<SYMBOL>_<RUNTAG>.csv
output_canonical_ict/precision_by_pattern_<SYMBOL>_<RUNTAG>.csv
output_canonical_ict/precision_combined_<RUNTAG>.csv
Console: Precision matrix + Recall-vs-Precision pairing + F1 + per-pattern table

USAGE
-----
  python canonical_ict_precision.py                  # auto-detect latest run
  python canonical_ict_precision.py --run 20260519_0545
"""

from __future__ import annotations
import argparse
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path("output_canonical_ict")
PRECISION_LOOKFORWARD_MIN = 15   # symmetric to recall_lookback_min in main script
TIERS = ("T0", "T1", "T2", "T3", "T4")
MODES = ("RETURN", "FORMATION")


def find_latest_run_tag(out_dir: Path) -> str:
    files = list(out_dir.glob("entries_*_*.csv"))
    tags = set()
    for f in files:
        stem = f.stem  # entries_NIFTY_20260519_0545
        parts = stem.split("_")
        if len(parts) >= 4:
            tag = "_".join(parts[-2:])
            tags.add(tag)
    if not tags:
        sys.exit(f"ERROR: no entries_*.csv files in {out_dir.absolute()} — run canonical_ict_recall.py first")
    return sorted(tags)[-1]


def list_symbols_for_run(out_dir: Path, run_tag: str) -> list:
    files = list(out_dir.glob(f"entries_*_{run_tag}.csv"))
    syms = []
    for f in files:
        stem = f.stem  # entries_NIFTY_20260519_0545
        # Symbol is between "entries_" prefix and run_tag suffix
        rest = stem[len("entries_"):]
        sym = rest[:rest.rfind("_" + run_tag.split("_")[0])]
        syms.append(sym)
    return syms


def compute_precision_detail(entries: pd.DataFrame, moves: pd.DataFrame,
                             symbol: str, lookforward_min: int) -> pd.DataFrame:
    """
    For each entry x tier x mode x direction, check if a qualifying move with
    matching (and counter) direction started in [entry_ts, entry_ts + lookforward].
    """
    if entries.empty:
        return pd.DataFrame()

    entries = entries.copy()
    entries["entry_ts"] = pd.to_datetime(entries["entry_ts"])
    moves = moves.copy()
    moves["ist"] = pd.to_datetime(moves["ist"])

    # Sorted arrays of move timestamps per direction (numpy datetime64 for fast searchsorted)
    moves_up = (moves[moves["direction"] == "UP"]
                .sort_values("ist")["ist"].values.astype("datetime64[ns]"))
    moves_dn = (moves[moves["direction"] == "DOWN"]
                .sort_values("ist")["ist"].values.astype("datetime64[ns]"))

    rows = []
    for mode in MODES:
        em = entries[entries["mode"] == mode]
        for tier in TIERS:
            et = em[em[f"align_{tier}"]]
            if et.empty:
                continue
            for direction in ("BULL", "BEAR"):
                etd = et[et["direction"] == direction]
                if etd.empty:
                    continue
                match_arr = moves_up if direction == "BULL" else moves_dn
                anti_arr  = moves_dn if direction == "BULL" else moves_up

                for _, e in etd.iterrows():
                    ets = pd.Timestamp(e["entry_ts"])
                    end = ets + timedelta(minutes=lookforward_min)
                    ets_np = np.datetime64(ets.to_datetime64())
                    end_np = np.datetime64(end.to_datetime64())

                    if match_arr.size:
                        lo_m = np.searchsorted(match_arr, ets_np, side="left")
                        hi_m = np.searchsorted(match_arr, end_np, side="right")
                        matched = bool(hi_m > lo_m)
                    else:
                        matched = False
                    if anti_arr.size:
                        lo_a = np.searchsorted(anti_arr, ets_np, side="left")
                        hi_a = np.searchsorted(anti_arr, end_np, side="right")
                        wrong = bool(hi_a > lo_a)
                    else:
                        wrong = False

                    rows.append({
                        "symbol": symbol,
                        "primitive_type": e["primitive_type"],
                        "primitive_tf": e.get("primitive_tf"),
                        "direction": direction,
                        "mode": mode,
                        "tier": tier,
                        "entry_ts": ets,
                        "matched": matched,
                        "wrong_way": wrong,
                        "no_move": (not matched) and (not wrong),
                        "both_directions": matched and wrong,
                    })
    return pd.DataFrame(rows)


def precision_summary(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return detail
    grp = detail.groupby(["symbol", "direction", "mode", "tier"])
    s = grp.agg(
        n_entries=("matched", "size"),
        n_match=("matched", "sum"),
        n_wrong=("wrong_way", "sum"),
        n_no_move=("no_move", "sum"),
        n_both=("both_directions", "sum"),
    ).reset_index()
    s["precision_pct"] = (s["n_match"] / s["n_entries"] * 100).round(2)
    s["wrong_way_pct"] = (s["n_wrong"] / s["n_entries"] * 100).round(2)
    s["no_move_pct"] = (s["n_no_move"] / s["n_entries"] * 100).round(2)
    return s


def precision_by_pattern(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return detail
    grp = detail.groupby(["symbol", "primitive_type", "mode", "tier"])
    s = grp.agg(
        n_entries=("matched", "size"),
        n_match=("matched", "sum"),
        n_wrong=("wrong_way", "sum"),
    ).reset_index()
    s["precision_pct"] = (s["n_match"] / s["n_entries"] * 100).round(2)
    s["wrong_way_pct"] = (s["n_wrong"] / s["n_entries"] * 100).round(2)
    return s


def merge_recall_summary(recall_files: list) -> pd.DataFrame:
    if not recall_files:
        return pd.DataFrame()
    dfs = [pd.read_csv(f) for f in recall_files]
    return pd.concat(dfs, ignore_index=True)


def f1(p: float, r: float) -> float:
    if (p + r) <= 0:
        return 0.0
    return round(2 * p * r / (p + r), 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None, help="run_tag YYYYMMDD_HHMM (default: latest)")
    ap.add_argument("--lookforward", type=int, default=PRECISION_LOOKFORWARD_MIN)
    args = ap.parse_args()

    if not OUT_DIR.exists():
        sys.exit(f"ERROR: {OUT_DIR.absolute()} not found")

    run_tag = args.run or find_latest_run_tag(OUT_DIR)
    syms = list_symbols_for_run(OUT_DIR, run_tag)
    if not syms:
        sys.exit(f"ERROR: no symbols found for run {run_tag}")

    print("=" * 78)
    print(f"canonical_ict_precision  run={run_tag}")
    print(f"  symbols       = {syms}")
    print(f"  lookforward   = {args.lookforward}min")
    print(f"  out_dir       = {OUT_DIR.absolute()}")
    print("=" * 78)

    all_detail = []
    all_summary = []
    all_pattern = []

    for sym in syms:
        entries_path = OUT_DIR / f"entries_{sym}_{run_tag}.csv"
        moves_path = OUT_DIR / f"moves_{sym}_{run_tag}.csv"
        if not entries_path.exists() or not moves_path.exists():
            print(f"  [{sym}] SKIP missing input file ({entries_path.exists()}, {moves_path.exists()})")
            continue
        print(f"\n--- {sym} ---")
        entries = pd.read_csv(entries_path)
        moves = pd.read_csv(moves_path)
        # CSV bool columns sometimes come in as strings — coerce
        for c in [c for c in entries.columns if c.startswith("align_")]:
            entries[c] = entries[c].map(lambda v: str(v).lower() in ("true", "1", "1.0"))
        print(f"  entries loaded : {len(entries)}")
        print(f"  moves loaded   : {len(moves)}")

        detail = compute_precision_detail(entries, moves, sym, args.lookforward)
        summary = precision_summary(detail)
        pattern = precision_by_pattern(detail)

        if not detail.empty:
            detail.to_csv(OUT_DIR / f"precision_detail_{sym}_{run_tag}.csv", index=False)
        if not summary.empty:
            summary.to_csv(OUT_DIR / f"precision_summary_{sym}_{run_tag}.csv", index=False)
        if not pattern.empty:
            pattern.to_csv(OUT_DIR / f"precision_by_pattern_{sym}_{run_tag}.csv", index=False)

        all_detail.append(detail)
        all_summary.append(summary)
        all_pattern.append(pattern)

    if not all_summary or all(s.empty for s in all_summary):
        print("\nno precision summaries produced; exiting.")
        return

    combined = pd.concat([s for s in all_summary if not s.empty], ignore_index=True)
    combined.to_csv(OUT_DIR / f"precision_combined_{run_tag}.csv", index=False)

    combined_pattern = pd.concat([s for s in all_pattern if not s.empty], ignore_index=True)
    combined_pattern.to_csv(OUT_DIR / f"precision_by_pattern_combined_{run_tag}.csv", index=False)

    # =========================================================================
    # Console output: precision matrix
    # =========================================================================
    print("\n" + "=" * 78)
    print(f"PRECISION MATRIX  ( precision % = n_match / n_entries, lookforward={args.lookforward}min )")
    print("=" * 78)
    for mode in MODES:
        print(f"\n>>> mode = {mode}   {'(strict canon)' if mode=='RETURN' else '(upper bound)'}")
        pv = (combined[combined["mode"] == mode]
              .pivot_table(index=["symbol", "direction"], columns="tier",
                           values="precision_pct", aggfunc="first")
              .round(1))
        if not pv.empty:
            print(pv.to_string())
            n_pv = (combined[combined["mode"] == mode]
                    .pivot_table(index=["symbol", "direction"], columns="tier",
                                 values="n_entries", aggfunc="first")
                    .astype("Int64"))
            print("\nn_entries (denominator):")
            print(n_pv.to_string())

    # =========================================================================
    # Console output: wrong-way rate
    # =========================================================================
    print("\n" + "=" * 78)
    print("WRONG-WAY RATE  ( % of entries where OPPOSITE-direction move qualified in window )")
    print("=" * 78)
    for mode in MODES:
        print(f"\n>>> mode = {mode}")
        pv = (combined[combined["mode"] == mode]
              .pivot_table(index=["symbol", "direction"], columns="tier",
                           values="wrong_way_pct", aggfunc="first")
              .round(1))
        if not pv.empty:
            print(pv.to_string())

    # =========================================================================
    # Console output: Recall vs Precision side-by-side + F1
    # =========================================================================
    recall_files = list(OUT_DIR.glob(f"recall_summary_*_{run_tag}.csv"))
    if recall_files:
        recall_combined = merge_recall_summary(recall_files)
        print("\n" + "=" * 78)
        print("RECALL vs PRECISION  (paired by symbol x direction x mode x tier)")
        print("=" * 78)
        merged = recall_combined.merge(
            combined[["symbol", "direction", "mode", "tier",
                      "precision_pct", "n_entries"]],
            on=["symbol", "direction", "mode", "tier"], how="outer"
        )
        merged["recall_pct"] = merged["recall_pct"].fillna(0)
        merged["precision_pct"] = merged["precision_pct"].fillna(0)
        merged["f1"] = merged.apply(lambda r: f1(r["precision_pct"], r["recall_pct"]), axis=1)
        for mode in MODES:
            print(f"\n>>> mode = {mode}")
            view = (merged[merged["mode"] == mode]
                    .sort_values(["symbol", "direction", "tier"])
                    [["symbol", "direction", "tier",
                      "n_moves", "n_matched", "recall_pct",
                      "n_entries", "precision_pct", "f1"]]
                    .reset_index(drop=True))
            if not view.empty:
                print(view.to_string(index=False))
        merged.to_csv(OUT_DIR / f"recall_vs_precision_{run_tag}.csv", index=False)
    else:
        print("\n(no recall_summary_*.csv files found — skipping recall pairing)")

    # =========================================================================
    # Console output: per-pattern precision
    # =========================================================================
    print("\n" + "=" * 78)
    print("PRECISION BY PRIMITIVE TYPE  (RETURN mode only)")
    print("=" * 78)
    pat_ret = combined_pattern[combined_pattern["mode"] == "RETURN"]
    if not pat_ret.empty:
        pv = (pat_ret.pivot_table(index=["symbol", "primitive_type"],
                                   columns="tier", values="precision_pct",
                                   aggfunc="first").round(1))
        print(pv.to_string())
        print("\nn_entries (denominator):")
        n_pv = (pat_ret.pivot_table(index=["symbol", "primitive_type"],
                                     columns="tier", values="n_entries",
                                     aggfunc="first").astype("Int64"))
        print(n_pv.to_string())

    print(f"\nall outputs : {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
