#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_no_flip_falsify.py
============================
Falsification battery for the NO_FLIP edge claim from canonical_ob_gamma_scalar.py.

The scalar test showed NO_FLIP cells had 50-68% precision on three of four
symbol-primitive combinations. Before treating that as edge, we test whether
NO_FLIP is a homogeneous category at all.

KEY CONTEXT
-----------
NO_FLIP does NOT mean "no zero-crossing in the book." It means the flip-finding
algorithm could not bracket a flip in the strikes examined. Causes include
narrow strike base, sparse OI in wings, spurious deep-ITM gamma (TD-NEW-2
pre-S27), and the methodology drift between backfill (bottom-up walk, never
patched) and live (walk-from-ATM, patched S27 commit 241f943).

If NO_FLIP cycles cluster on data-quality-bad windows or on trending sessions
with large baseline moves, the precision uplift is not a positioning signal —
it's an artifact.

CHECKS
------
A. NO_FLIP homogeneity:
   - Is regime='NO_FLIP' == flip_level IS NULL?
   - Time-of-day distribution
   - Month-of-year distribution (vs TD-NEW-2 broken window Apr-May 2026)
   - Pre-S27 vs post-S27 date split

B. Move-size confound:
   - Per trade_date, median absolute 30min move size on the day
   - Stratify NO_FLIP cohort by day-move-size quartile
   - If precision uniformly elevated only on big-move days -> artifact

C. Re-stratify NO_FLIP precision by sub-category:
   - flip_level NULL vs not
   - early/mid/late session
   - pre-S27 vs post-S27 calendar
   - Re-compute precision per sub-cell

INPUTS
------
output_canonical_ict/ob_gamma_scalar_detail_<SYMBOL>_<RUN>.csv
output_canonical_ict/moves_<SYMBOL>_<RUN>.csv

OUTPUTS
-------
output_canonical_ict/no_flip_falsify_<RUN>.txt  (full report)
Console: condensed findings

USAGE
-----
  python canonical_no_flip_falsify.py
  python canonical_no_flip_falsify.py --run 20260519_0628
"""

from __future__ import annotations
import argparse
import sys
from datetime import datetime, date
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path("output_canonical_ict")
S27_PATCH_DATE = pd.Timestamp("2026-05-12")  # commit 241f943 close of S27
TD_NEW_2_WINDOW_START = pd.Timestamp("2026-05-08")
TD_NEW_2_WINDOW_END = pd.Timestamp("2026-05-12")


def find_latest_run_tag(out_dir: Path) -> str:
    files = list(out_dir.glob("ob_gamma_scalar_detail_*_*.csv"))
    tags = set()
    for f in files:
        parts = f.stem.split("_")
        if len(parts) >= 6:
            tags.add("_".join(parts[-2:]))
    if not tags:
        files = list(out_dir.glob("entries_*_*.csv"))
        for f in files:
            parts = f.stem.split("_")
            if len(parts) >= 4:
                tags.add("_".join(parts[-2:]))
    if not tags:
        sys.exit(f"ERROR: no detail or entries CSVs in {out_dir.absolute()}")
    return sorted(tags)[-1]


def session_bucket(ts: pd.Timestamp) -> str:
    h = ts.hour
    m = ts.minute
    minutes = h * 60 + m
    if minutes < 10 * 60:
        return "early_0915_1000"
    if minutes < 13 * 60:
        return "mid_1000_1300"
    if minutes < 14 * 60 + 30:
        return "afternoon_1300_1430"
    return "late_1430_1530"


def emit(buf, line=""):
    print(line)
    buf.append(line)


def precision_summary(df: pd.DataFrame, group_cols: list, min_n: int = 20) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    grp = df.groupby(group_cols)
    s = grp.agg(
        n=("matched", "size"),
        n_match=("matched", "sum"),
        n_wrong=("wrong_way", "sum"),
    ).reset_index()
    s["precision_pct"] = (s["n_match"] / s["n"] * 100).round(1)
    s["wrong_way_pct"] = (s["n_wrong"] / s["n"] * 100).round(1)
    s["adequate_n"] = s["n"] >= min_n
    return s


def section_a_homogeneity(buf, detail_all: pd.DataFrame):
    emit(buf, "\n" + "=" * 78)
    emit(buf, "SECTION A — IS NO_FLIP A HOMOGENEOUS CATEGORY?")
    emit(buf, "=" * 78)

    nf = detail_all[detail_all["regime"] == "NO_FLIP"].copy()
    if nf.empty:
        emit(buf, "no NO_FLIP rows; skip section")
        return
    emit(buf, f"\nTotal NO_FLIP rows in joined cohort: {len(nf)}")

    # Time-of-day distribution
    nf["entry_ts"] = pd.to_datetime(nf["entry_ts"])
    nf["session_bucket"] = nf["entry_ts"].apply(session_bucket)
    tod = nf.groupby(["symbol", "session_bucket"]).size().unstack(fill_value=0)
    emit(buf, "\n--- Time-of-day distribution of NO_FLIP entries ---")
    emit(buf, tod.to_string())

    # Month distribution
    nf["month"] = nf["entry_ts"].dt.to_period("M").astype(str)
    by_month = nf.groupby(["symbol", "month"]).size().unstack(fill_value=0)
    emit(buf, "\n--- Monthly distribution of NO_FLIP entries ---")
    emit(buf, by_month.to_string())

    # Pre-S27 vs post-S27 patch
    nf["pre_s27_patch"] = nf["entry_ts"] < S27_PATCH_DATE
    split = nf.groupby(["symbol", "pre_s27_patch"]).size().unstack(fill_value=0)
    emit(buf, "\n--- Pre-S27-patch (before 2026-05-12) vs post-patch entry counts ---")
    emit(buf, split.to_string())

    # Compare NO_FLIP rate per month against total entries per month
    detail_all["entry_ts"] = pd.to_datetime(detail_all["entry_ts"])
    detail_all["month"] = detail_all["entry_ts"].dt.to_period("M").astype(str)
    total_by_month = detail_all.groupby(["symbol", "month"]).size().unstack(fill_value=0)
    nf_rate = (by_month / total_by_month * 100).round(1)
    emit(buf, "\n--- NO_FLIP rate per month (% of OB entries in that month) ---")
    emit(buf, nf_rate.to_string())


def section_b_move_size_confound(buf, detail_all: pd.DataFrame, moves_by_sym: dict):
    emit(buf, "\n" + "=" * 78)
    emit(buf, "SECTION B — MOVE-SIZE CONFOUND CHECK")
    emit(buf, "=" * 78)
    emit(buf, "Hypothesis: NO_FLIP precision is high because those days happened to "
              "have larger moves regardless of OB structure.")

    # Compute per trade_date move-size median
    detail_all["entry_ts"] = pd.to_datetime(detail_all["entry_ts"])
    detail_all["trade_date"] = detail_all["entry_ts"].dt.date.astype(str)

    for sym, moves in moves_by_sym.items():
        if moves.empty:
            continue
        moves = moves.copy()
        moves["ist"] = pd.to_datetime(moves["ist"])
        moves["trade_date"] = moves["ist"].dt.date.astype(str)
        moves["abs_move"] = moves["net_30m"].abs() if "net_30m" in moves.columns else np.nan
        # Median absolute move per date (fallback to count if size unavailable)
        if "abs_move" in moves.columns and moves["abs_move"].notna().any():
            per_day = moves.groupby("trade_date").agg(
                median_abs_move=("abs_move", "median"),
                n_qualifying_moves=("abs_move", "size"),
            ).reset_index()
            metric = "median_abs_move"
        else:
            per_day = moves.groupby("trade_date").size().reset_index(name="n_qualifying_moves")
            per_day["median_abs_move"] = per_day["n_qualifying_moves"]  # proxy
            metric = "n_qualifying_moves"

        # Quartile-bin days by metric
        per_day["day_quartile"] = pd.qcut(
            per_day[metric], q=4, labels=["Q1_smallest", "Q2", "Q3", "Q4_largest"],
            duplicates="drop"
        ).astype(str)

        d_sym = detail_all[detail_all["symbol"] == sym].copy()
        d_sym = d_sym.merge(per_day[["trade_date", "day_quartile"]], on="trade_date", how="left")
        d_sym["regime"] = d_sym["regime"].astype(str)

        # Compare NO_FLIP precision per day-quartile vs non-NO_FLIP precision
        nf_summary = precision_summary(
            d_sym[d_sym["regime"] == "NO_FLIP"],
            ["primitive_type", "day_quartile"], min_n=10
        )
        non_nf_summary = precision_summary(
            d_sym[d_sym["regime"].isin(["LONG_GAMMA", "SHORT_GAMMA"])],
            ["primitive_type", "day_quartile"], min_n=10
        )
        emit(buf, f"\n--- {sym} : NO_FLIP precision by day-{metric}-quartile ---")
        if not nf_summary.empty:
            emit(buf, nf_summary.to_string(index=False))
        else:
            emit(buf, "(no rows)")
        emit(buf, f"\n--- {sym} : LONG/SHORT precision by day-{metric}-quartile (control) ---")
        if not non_nf_summary.empty:
            emit(buf, non_nf_summary.to_string(index=False))
        else:
            emit(buf, "(no rows)")


def section_c_restratify(buf, detail_all: pd.DataFrame):
    emit(buf, "\n" + "=" * 78)
    emit(buf, "SECTION C — RE-STRATIFY NO_FLIP PRECISION BY SUB-CATEGORY")
    emit(buf, "=" * 78)

    nf = detail_all[detail_all["regime"] == "NO_FLIP"].copy()
    if nf.empty:
        emit(buf, "no NO_FLIP rows; skip")
        return
    nf["entry_ts"] = pd.to_datetime(nf["entry_ts"])
    nf["session_bucket"] = nf["entry_ts"].apply(session_bucket)
    nf["pre_s27_patch"] = nf["entry_ts"] < S27_PATCH_DATE
    nf["in_td_new_2_window"] = (nf["entry_ts"] >= TD_NEW_2_WINDOW_START) & (nf["entry_ts"] < TD_NEW_2_WINDOW_END)

    # By session bucket
    emit(buf, "\n--- C.1 NO_FLIP precision by session bucket ---")
    s1 = precision_summary(nf, ["symbol", "primitive_type", "session_bucket"], min_n=10)
    if not s1.empty:
        emit(buf, s1.to_string(index=False))

    # By pre/post S27 patch
    emit(buf, "\n--- C.2 NO_FLIP precision pre/post S27 patch (boundary: 2026-05-12) ---")
    s2 = precision_summary(nf, ["symbol", "primitive_type", "pre_s27_patch"], min_n=10)
    if not s2.empty:
        emit(buf, s2.to_string(index=False))

    # By TD-NEW-2 broken window
    emit(buf, "\n--- C.3 NO_FLIP precision inside vs outside TD-NEW-2 broken window "
              "(2026-05-08 to 2026-05-12) ---")
    s3 = precision_summary(nf, ["symbol", "primitive_type", "in_td_new_2_window"], min_n=10)
    if not s3.empty:
        emit(buf, s3.to_string(index=False))

    # Calendar-year split
    nf["year"] = nf["entry_ts"].dt.year
    emit(buf, "\n--- C.4 NO_FLIP precision by calendar year ---")
    s4 = precision_summary(nf, ["symbol", "primitive_type", "year"], min_n=10)
    if not s4.empty:
        emit(buf, s4.to_string(index=False))


def section_d_verdict(buf, detail_all: pd.DataFrame):
    """Aggregate verdict: does NO_FLIP edge survive the slicings?"""
    emit(buf, "\n" + "=" * 78)
    emit(buf, "SECTION D — VERDICT TABLE")
    emit(buf, "=" * 78)
    emit(buf, "For each (symbol, primitive) where NO_FLIP showed elevated precision,")
    emit(buf, "is there a homogeneous sub-cell (N >= 30) that preserves the edge?")

    nf = detail_all[detail_all["regime"] == "NO_FLIP"].copy()
    if nf.empty:
        return
    nf["entry_ts"] = pd.to_datetime(nf["entry_ts"])
    nf["session_bucket"] = nf["entry_ts"].apply(session_bucket)
    nf["pre_s27_patch"] = nf["entry_ts"] < S27_PATCH_DATE
    nf["year"] = nf["entry_ts"].dt.year

    # For each (symbol, primitive_type), find sub-cells with N>=30
    for (sym, prim), sub in nf.groupby(["symbol", "primitive_type"]):
        overall_n = len(sub)
        overall_prec = sub["matched"].mean() * 100
        overall_wrong = sub["wrong_way"].mean() * 100
        emit(buf, f"\n  {sym} {prim}  (overall N={overall_n}, "
                  f"precision={overall_prec:.1f}%, wrong-way={overall_wrong:.1f}%)")

        # Try each stratification dimension; report sub-cells with N>=30
        for dim in ["session_bucket", "pre_s27_patch", "year"]:
            for val, g in sub.groupby(dim):
                if len(g) < 30:
                    continue
                p = g["matched"].mean() * 100
                w = g["wrong_way"].mean() * 100
                spread = p - w
                tag = "EDGE" if spread > 25 else ("WEAK" if spread > 10 else "FAIL")
                emit(buf,
                     f"    {dim}={val:<25}  N={len(g):<5}  "
                     f"prec={p:5.1f}%  wrong={w:5.1f}%  spread={spread:+5.1f}pp  [{tag}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    args = ap.parse_args()

    run_tag = args.run or find_latest_run_tag(OUT_DIR)
    detail_files = sorted(OUT_DIR.glob(f"ob_gamma_scalar_detail_*_{run_tag}.csv"))
    if not detail_files:
        sys.exit(f"ERROR: no detail CSVs for run {run_tag}; run canonical_ob_gamma_scalar.py first")

    moves_by_sym = {}
    for f in OUT_DIR.glob(f"moves_*_{run_tag}.csv"):
        rest = f.stem[len("moves_"):]
        sym = rest[:rest.rfind("_" + run_tag.split("_")[0])]
        moves_by_sym[sym] = pd.read_csv(f)

    dfs = [pd.read_csv(f) for f in detail_files]
    detail_all = pd.concat(dfs, ignore_index=True)
    print(f"loaded {len(detail_all)} detail rows from {len(detail_files)} symbols (run={run_tag})")

    buf = []
    emit(buf, "=" * 78)
    emit(buf, f"NO_FLIP FALSIFICATION — run={run_tag}")
    emit(buf, f"  inputs   = {[f.name for f in detail_files]}")
    emit(buf, f"  S27 patch boundary date = {S27_PATCH_DATE.date()}")
    emit(buf, "=" * 78)

    section_a_homogeneity(buf, detail_all)
    section_b_move_size_confound(buf, detail_all, moves_by_sym)
    section_c_restratify(buf, detail_all)
    section_d_verdict(buf, detail_all)

    report_path = OUT_DIR / f"no_flip_falsify_{run_tag}.txt"
    report_path.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nfull report : {report_path}")
    print("done.")


if __name__ == "__main__":
    main()
