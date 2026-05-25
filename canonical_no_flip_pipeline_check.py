#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_no_flip_pipeline_check.py
====================================
Data-quality diagnostic for the Feb 2026 NO_FLIP spike surfaced by
canonical_no_flip_falsify.py. Operates directly on gamma_metrics; does not
depend on the OB cohort.

OBSERVED ANOMALY
----------------
From the falsification pass joined cohort (OB entries × gamma_metrics):
  NIFTY NO_FLIP rate by month: 2025-04 5.4%, 2025-05 30.9%, 2025-06 3.7%,
                                ..., 2026-02 42.4%, 2026-03 30.9%
  SENSEX similar; Feb-Mar 2026 spike to 30-55%.

The Feb 2026 spike is INSIDE the uniform vendor data window (Apr 2025 - Mar
2026). It's not a Kite-to-vendor data switch. What changed?

DIAGNOSTIC HYPOTHESES
---------------------
H1. Live writer regression: live compute_gamma_metrics_local.py started writing
    (or restarted) in Feb 2026 with the TD-S30-CANDIDATE-1 unit regression.
    Signature: net_gex magnitude spike from Cr range to trillions; created_at
    near-realtime; row count surge.
H2. Algorithm change in flip-finder: a code change made the walk-from-ATM
    fail more often. Signature: NO_FLIP rate up but magnitude stable;
    created_at distribution unchanged.
H3. Strike-base coverage changed in source data: vendor data refresh narrowed
    the per-cycle strike range or option_chain_snapshots ingest changed.
    Signature: NO_FLIP up, magnitude stable, NO_FLIP heavily concentrated at
    session-open times (where strike base is naturally thinner).
H4. Backfill re-run: someone re-ran backfill_gamma_metrics_to_main.py with a
    different methodology. Signature: created_at burst in narrow window;
    backward-dated ts; net_gex in Cr range; NO_FLIP rate change.

The script measures all four signatures.

OUTPUTS
-------
output_canonical_ict/no_flip_pipeline_<run>.txt
Console: monthly tables + boundary diagnostics + verdict
"""

from __future__ import annotations
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
OUT_DIR = Path("output_canonical_ict")


def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    for v in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
        if os.environ.get(v):
            return create_client(url, os.environ[v])
    sys.exit("ERROR: SUPABASE_URL + key not in .env")


def fetch_gamma_full(sb, symbol: str, start: str, end: str) -> pd.DataFrame:
    """Pull gamma_metrics over [start, end] with all columns we need for diagnostic."""
    rows = []
    page = 0
    print(f"  [{symbol}] fetching gamma_metrics ...", end="", flush=True)
    while True:
        resp = (sb.table("gamma_metrics")
                  .select("ts, created_at, regime, gamma_zone, net_gex, flip_level, "
                          "spot, expiry_date")
                  .eq("symbol", symbol)
                  .gte("ts", start)
                  .lte("ts", end)
                  .order("ts")
                  .range(page * 1000, page * 1000 + 999)
                  .execute())
        if not resp.data:
            break
        rows.extend(resp.data)
        if len(resp.data) < 1000:
            break
        page += 1
        if page % 10 == 0:
            print(".", end="", flush=True)
    print(f" {len(rows)} rows")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, format="ISO8601")
    df["ist"] = df["ts"].dt.tz_convert(IST).dt.tz_localize(None)
    df["month"] = df["ist"].dt.to_period("M").astype(str)
    df["hour_minute"] = df["ist"].dt.hour * 60 + df["ist"].dt.minute
    df["create_ts_gap_hours"] = (df["created_at"] - df["ts"]).dt.total_seconds() / 3600.0
    return df


def emit(buf, line=""):
    print(line)
    buf.append(line)


def section_a_monthly_breakdown(buf, df: pd.DataFrame, symbol: str):
    emit(buf, "\n" + "=" * 78)
    emit(buf, f"SECTION A — {symbol} MONTHLY BREAKDOWN")
    emit(buf, "=" * 78)

    monthly = df.groupby("month").agg(
        n_rows=("ts", "size"),
        n_no_flip=("regime", lambda x: (x == "NO_FLIP").sum()),
        n_long=("regime", lambda x: (x == "LONG_GAMMA").sum()),
        n_short=("regime", lambda x: (x == "SHORT_GAMMA").sum()),
        n_flip_null=("flip_level", lambda x: x.isna().sum()),
        n_regime_null=("regime", lambda x: x.isna().sum()),
        median_abs_net_gex=("net_gex", lambda x: float(x.dropna().abs().median()) if x.notna().any() else np.nan),
        max_abs_net_gex=("net_gex", lambda x: float(x.dropna().abs().max()) if x.notna().any() else np.nan),
        median_create_gap_hr=("create_ts_gap_hours", "median"),
    ).reset_index()
    monthly["no_flip_pct"] = (monthly["n_no_flip"] / monthly["n_rows"] * 100).round(1)
    monthly["flip_null_pct"] = (monthly["n_flip_null"] / monthly["n_rows"] * 100).round(1)

    cols = ["month", "n_rows", "n_no_flip", "no_flip_pct",
            "n_flip_null", "flip_null_pct",
            "median_abs_net_gex", "max_abs_net_gex", "median_create_gap_hr"]
    emit(buf, monthly[cols].to_string(index=False))

    # Detect magnitude regime shift
    emit(buf, "\n--- Magnitude regime detection (net_gex order-of-magnitude per month) ---")
    monthly["log10_med"] = np.log10(monthly["median_abs_net_gex"].replace(0, np.nan))
    log_min = monthly["log10_med"].min()
    log_max = monthly["log10_med"].max()
    emit(buf, f"  log10 median |net_gex| range across months: [{log_min:.1f}, {log_max:.1f}]")
    if log_max - log_min > 3:
        emit(buf, "  *** RANGE > 3 orders of magnitude — strong indicator of unit regression boundary ***")
    else:
        emit(buf, "  range OK (no unit boundary detected)")
    # Identify the boundary month (largest log-diff between consecutive months)
    monthly_sorted = monthly.sort_values("month").reset_index(drop=True)
    monthly_sorted["log10_jump"] = monthly_sorted["log10_med"].diff().abs()
    if monthly_sorted["log10_jump"].notna().any():
        max_jump_idx = monthly_sorted["log10_jump"].idxmax()
        emit(buf, f"  largest month-to-month log10 jump: {monthly_sorted.loc[max_jump_idx, 'log10_jump']:.2f}")
        emit(buf, f"  between {monthly_sorted.loc[max(0,max_jump_idx-1), 'month']} "
                  f"-> {monthly_sorted.loc[max_jump_idx, 'month']}")


def section_b_no_flip_correlations(buf, df: pd.DataFrame, symbol: str):
    emit(buf, "\n" + "=" * 78)
    emit(buf, f"SECTION B — {symbol} NO_FLIP MECHANICAL CORRELATIONS")
    emit(buf, "=" * 78)

    # Does regime=NO_FLIP ALWAYS coincide with flip_level NULL?
    nf = df[df["regime"] == "NO_FLIP"]
    nf_flip_null = nf["flip_level"].isna().sum()
    nf_flip_notnull = nf["flip_level"].notna().sum()
    emit(buf, f"\nNO_FLIP rows: {len(nf)} total")
    emit(buf, f"  with flip_level NULL    : {nf_flip_null} ({nf_flip_null/max(len(nf),1)*100:.1f}%)")
    emit(buf, f"  with flip_level non-NULL: {nf_flip_notnull} "
              f"({nf_flip_notnull/max(len(nf),1)*100:.1f}%)")
    if nf_flip_notnull > 0:
        emit(buf, "  (non-NULL flip_level with NO_FLIP regime suggests additional classifier logic "
                  "beyond just null-flip)")

    # Inverse: rows with flip_level NULL — what's the regime distribution?
    fn = df[df["flip_level"].isna()]
    emit(buf, f"\nflip_level NULL rows: {len(fn)} total")
    if len(fn) > 0:
        emit(buf, fn["regime"].value_counts(dropna=False).to_string())


def section_c_time_of_day_shift(buf, df: pd.DataFrame, symbol: str):
    emit(buf, "\n" + "=" * 78)
    emit(buf, f"SECTION C — {symbol} TIME-OF-DAY DISTRIBUTION OF NO_FLIP (BY MONTH)")
    emit(buf, "=" * 78)

    nf = df[df["regime"] == "NO_FLIP"].copy()
    if nf.empty:
        emit(buf, "no NO_FLIP rows; skip")
        return

    # Bucket time-of-day
    def bucket(hm):
        if hm < 10 * 60:
            return "1_early_0915_1000"
        if hm < 12 * 60:
            return "2_mid_1000_1200"
        if hm < 14 * 60:
            return "3_afternoon_1200_1400"
        return "4_late_1400_1530"
    nf["tod_bucket"] = nf["hour_minute"].apply(bucket)

    by_month_tod = nf.groupby(["month", "tod_bucket"]).size().unstack(fill_value=0)
    by_month_total = nf.groupby("month").size()
    by_month_tod_pct = (by_month_tod.div(by_month_total, axis=0) * 100).round(1)
    emit(buf, "\n--- NO_FLIP entries by month x time-of-day (counts) ---")
    emit(buf, by_month_tod.to_string())
    emit(buf, "\n--- NO_FLIP entries by month x time-of-day (% of that month's NO_FLIP) ---")
    emit(buf, by_month_tod_pct.to_string())


def section_d_created_at_provenance(buf, df: pd.DataFrame, symbol: str):
    emit(buf, "\n" + "=" * 78)
    emit(buf, f"SECTION D — {symbol} WRITE PROVENANCE (created_at vs ts gap)")
    emit(buf, "=" * 78)
    emit(buf, "Gap near 0 = live write (writer ran ~immediately after ts).")
    emit(buf, "Gap of days/weeks/months = backfill write (later compute on historical ts).")

    monthly_gap = df.groupby("month")["create_ts_gap_hours"].agg(
        ["count", "median", "min", "max",
         lambda x: float(np.percentile(x.dropna(), 95)) if x.notna().any() else np.nan]
    ).rename(columns={"<lambda_0>": "p95"})
    emit(buf, "\n--- create_ts_gap (hours) by month ---")
    emit(buf, monthly_gap.round(2).to_string())

    # Identify months where most rows are backfill (gap > 1 day) vs live (gap < 1 hour)
    df["is_backfill"] = df["create_ts_gap_hours"] > 24
    df["is_live"] = df["create_ts_gap_hours"] < 1
    write_class = df.groupby("month").agg(
        n_total=("ts", "size"),
        n_backfill=("is_backfill", "sum"),
        n_live=("is_live", "sum"),
    ).reset_index()
    write_class["backfill_pct"] = (write_class["n_backfill"] / write_class["n_total"] * 100).round(1)
    write_class["live_pct"] = (write_class["n_live"] / write_class["n_total"] * 100).round(1)
    emit(buf, "\n--- write classification (live vs backfill) per month ---")
    emit(buf, write_class.to_string(index=False))


def section_e_verdict(buf, df: pd.DataFrame, symbol: str):
    emit(buf, "\n" + "=" * 78)
    emit(buf, f"SECTION E — {symbol} HYPOTHESIS EVALUATION")
    emit(buf, "=" * 78)

    monthly = df.groupby("month").agg(
        n_rows=("ts", "size"),
        n_no_flip=("regime", lambda x: (x == "NO_FLIP").sum()),
        median_abs_net_gex=("net_gex", lambda x: float(x.dropna().abs().median()) if x.notna().any() else np.nan),
        median_gap=("create_ts_gap_hours", "median"),
    ).reset_index()
    monthly["no_flip_pct"] = (monthly["n_no_flip"] / monthly["n_rows"] * 100).round(1)

    # Pre/post boundary at 2026-02-01
    pre = monthly[monthly["month"] < "2026-02"]
    post = monthly[monthly["month"] >= "2026-02"]

    emit(buf, f"\nMonths pre-Feb-2026 : {len(pre)}")
    emit(buf, f"Months post-Feb-2026: {len(post)}")
    if pre.empty or post.empty:
        emit(buf, "Insufficient data on one side; skip verdict")
        return

    pre_nf = pre["no_flip_pct"].median()
    post_nf = post["no_flip_pct"].median()
    pre_mag = pre["median_abs_net_gex"].median()
    post_mag = post["median_abs_net_gex"].median()
    pre_gap = pre["median_gap"].median()
    post_gap = post["median_gap"].median()

    emit(buf, f"\n  NO_FLIP rate    : pre median {pre_nf:.1f}% -> post median {post_nf:.1f}%  "
              f"(delta {post_nf - pre_nf:+.1f}pp)")
    emit(buf, f"  |net_gex| median: pre {pre_mag:.2e}      -> post {post_mag:.2e}      "
              f"(ratio {post_mag/pre_mag if pre_mag else float('inf'):.2e})")
    emit(buf, f"  create-ts gap   : pre {pre_gap:.1f}hr        -> post {post_gap:.1f}hr        "
              f"(delta {post_gap - pre_gap:+.1f}hr)")

    emit(buf, "\nHypothesis evaluation:")
    mag_ratio = post_mag / pre_mag if pre_mag else float('inf')
    if mag_ratio > 100 or mag_ratio < 0.01:
        emit(buf, "  H1 (live writer Cr regression): SUPPORTED by magnitude ratio "
                  f"{mag_ratio:.2e}")
    else:
        emit(buf, "  H1 (live writer Cr regression): NOT supported "
                  f"(magnitude ratio {mag_ratio:.2f} within plausible range)")

    if post_nf - pre_nf > 10 and abs(mag_ratio - 1.0) < 100:
        emit(buf, "  H2 (algorithm change): CONSISTENT — NO_FLIP up, magnitude stable")
    else:
        emit(buf, "  H2 (algorithm change): not the cleanest match")

    if pre_gap > 24 and post_gap < 1:
        emit(buf, "  H4 (backfill->live switch): SUPPORTED — gap collapsed from days to ~realtime")
    elif pre_gap < 1 and post_gap < 1:
        emit(buf, "  H4 (backfill->live switch): both periods look live")
    elif pre_gap > 24 and post_gap > 24:
        emit(buf, "  H4 (backfill->live switch): both periods look backfilled")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-01")
    ap.add_argument("--end", default="2026-05-19")
    ap.add_argument("--run-tag", default=None,
                    help="for output filename only; defaults to current timestamp")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sb = _connect_supabase()
    run_tag = args.run_tag or datetime.now().strftime("%Y%m%d_%H%M")

    buf = []
    emit(buf, "=" * 78)
    emit(buf, f"NO_FLIP PIPELINE INVESTIGATION  run={run_tag}")
    emit(buf, f"  window = {args.start} -> {args.end}")
    emit(buf, "=" * 78)

    for sym in ("NIFTY", "SENSEX"):
        emit(buf, f"\n\n{'#' * 78}")
        emit(buf, f"# {sym}")
        emit(buf, f"{'#' * 78}")
        df = fetch_gamma_full(sb, sym, args.start, args.end)
        if df.empty:
            emit(buf, "(no rows)")
            continue
        section_a_monthly_breakdown(buf, df, sym)
        section_b_no_flip_correlations(buf, df, sym)
        section_c_time_of_day_shift(buf, df, sym)
        section_d_created_at_provenance(buf, df, sym)
        section_e_verdict(buf, df, sym)

    report_path = OUT_DIR / f"no_flip_pipeline_{run_tag}.txt"
    report_path.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nreport saved: {report_path}")
    print("done.")


if __name__ == "__main__":
    main()
