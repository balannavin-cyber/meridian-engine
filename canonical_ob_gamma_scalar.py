#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ob_gamma_scalar.py
============================
OB precision/wrong-way stratified by scalar gamma regime (LONG_GAMMA /
SHORT_GAMMA / NO_FLIP), derived from gamma_metrics.regime.

This is the cheap-smoke-test version of the per-strike gamma zone test. If
scalar regime carves OB precision meaningfully here, per-strike concentration
zones (Path B, BS-derived) are worth building. If scalar is flat, per-strike
is unlikely to rescue a signal that the coarser version missed.

WHY THIS IS SAFE TO USE DESPITE TD-S30-CANDIDATE-1
---------------------------------------------------
The live writer regression (live gamma_metrics net_gex magnitudes ~10^7 too
large vs backfill) affects MAGNITUDE only. regime is derived from the
SIGN of net_gex (>=0 LONG, <0 SHORT, NO_FLIP for no zero-crossing). Sign is
unit-invariant; regime classification is correct in both live and backfilled
rows. We use only the regime column, never net_gex magnitude.

NOTE ON TABLE CHOICE
--------------------
gamma_metrics (live + backfilled-to-main) is preferred over hist_gamma_metrics
because it has the broader coverage. backfill_gamma_metrics_to_main.py
(S29-close) added gap-fill rows. Either would give correct regime; we use
gamma_metrics for coverage.

INPUTS
------
output_canonical_ict/entries_<SYMBOL>_<RUNTAG>.csv
output_canonical_ict/moves_<SYMBOL>_<RUNTAG>.csv
Supabase gamma_metrics

OUTPUTS
-------
output_canonical_ict/ob_gamma_scalar_detail_<SYMBOL>_<RUN>.csv
output_canonical_ict/ob_gamma_scalar_summary_<SYMBOL>_<RUN>.csv
output_canonical_ict/ob_gamma_scalar_combined_<RUN>.csv
Console: coverage report + 2-axis matrices for regime and gamma_zone

USAGE
-----
  python canonical_ob_gamma_scalar.py
  python canonical_ob_gamma_scalar.py --tier T1
  python canonical_ob_gamma_scalar.py --tier T0    # baseline, largest N
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
PRECISION_LOOKFORWARD_MIN = 15
GAMMA_LOOKBACK_MIN = 15   # find latest gamma_metrics row in this window before entry_ts


# ==========================================================================
# Supabase
# ==========================================================================

def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    candidates = [
        "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY",
    ]
    key = None
    for v in candidates:
        if os.environ.get(v):
            key = os.environ[v]
            break
    if not (url and key):
        sys.exit("ERROR: SUPABASE_URL + key not in .env")
    return create_client(url, key)


# ==========================================================================
# Run-tag + symbol discovery
# ==========================================================================

def find_latest_run_tag(out_dir: Path) -> str:
    files = list(out_dir.glob("entries_*_*.csv"))
    tags = set()
    for f in files:
        parts = f.stem.split("_")
        if len(parts) >= 4:
            tags.add("_".join(parts[-2:]))
    if not tags:
        sys.exit(f"ERROR: no entries_*.csv in {out_dir.absolute()}")
    return sorted(tags)[-1]


def list_symbols_for_run(out_dir: Path, run_tag: str) -> list:
    files = list(out_dir.glob(f"entries_*_{run_tag}.csv"))
    syms = []
    for f in files:
        rest = f.stem[len("entries_"):]
        sym = rest[:rest.rfind("_" + run_tag.split("_")[0])]
        syms.append(sym)
    return syms


# ==========================================================================
# Gamma data fetch
# ==========================================================================

def fetch_gamma_metrics(sb, symbol: str, start_ist: pd.Timestamp,
                         end_ist: pd.Timestamp) -> pd.DataFrame:
    """
    Fetch all gamma_metrics rows for [start_ist, end_ist].
    Page through Supabase 1000-row limit.
    Convert ts (UTC) -> IST naive for in-memory join.
    """
    start_utc = start_ist.tz_localize(IST).tz_convert("UTC")
    end_utc = end_ist.tz_localize(IST).tz_convert("UTC")
    rows = []
    page = 0
    print(f"  [{symbol}] fetching gamma_metrics {start_ist.date()}..{end_ist.date()}",
          end="", flush=True)
    while True:
        resp = (sb.table("gamma_metrics")
                  .select("ts, regime, gamma_zone, net_gex")
                  .eq("symbol", symbol)
                  .gte("ts", start_utc.isoformat())
                  .lte("ts", end_utc.isoformat())
                  .order("ts")
                  .range(page * 1000, page * 1000 + 999)
                  .execute())
        if not resp.data:
            break
        rows.extend(resp.data)
        if len(resp.data) < 1000:
            break
        page += 1
        if page % 5 == 0:
            print(".", end="", flush=True)
    print(f" {len(rows)} rows")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    df["ist"] = df["ts"].dt.tz_convert(IST).dt.tz_localize(None)
    df = df.sort_values("ist").reset_index(drop=True)
    return df


# ==========================================================================
# Attach gamma regime to each entry (in-memory join, searchsorted)
# ==========================================================================

def attach_gamma_to_entries(entries: pd.DataFrame, gamma: pd.DataFrame,
                             lookback_min: int = GAMMA_LOOKBACK_MIN) -> pd.DataFrame:
    """
    For each entry, find latest gamma row with ist in [entry_ts - lookback_min, entry_ts].
    If none found, attach 'NO_DATA' for regime/zone.
    """
    out = entries.copy()
    out["entry_ts"] = pd.to_datetime(out["entry_ts"])
    if gamma.empty:
        out["regime"] = "NO_DATA"
        out["gamma_zone"] = "NO_DATA"
        out["gamma_lag_min"] = np.nan
        return out

    g_ts = gamma["ist"].values.astype("datetime64[ns]")
    g_regime = gamma["regime"].values
    g_zone = gamma["gamma_zone"].values

    regimes = []
    zones = []
    lags = []
    for ets in out["entry_ts"]:
        ets_np = np.datetime64(pd.Timestamp(ets).to_datetime64())
        # find rightmost gamma row with ts <= entry_ts
        idx = np.searchsorted(g_ts, ets_np, side="right") - 1
        if idx < 0:
            regimes.append("NO_DATA"); zones.append("NO_DATA"); lags.append(np.nan); continue
        lag_sec = (ets_np - g_ts[idx]).astype("timedelta64[s]").astype(float)
        if lag_sec > lookback_min * 60:
            regimes.append("STALE"); zones.append("STALE"); lags.append(lag_sec / 60.0); continue
        regimes.append(str(g_regime[idx]) if g_regime[idx] is not None else "NULL")
        zones.append(str(g_zone[idx]) if g_zone[idx] is not None else "NULL")
        lags.append(lag_sec / 60.0)
    out["regime"] = regimes
    out["gamma_zone"] = zones
    out["gamma_lag_min"] = lags
    return out


# ==========================================================================
# Precision computation (reused pattern)
# ==========================================================================

def precision_per_entry(entries: pd.DataFrame, moves: pd.DataFrame,
                         lookforward_min: int) -> pd.DataFrame:
    if entries.empty:
        return entries
    moves = moves.copy()
    moves["ist"] = pd.to_datetime(moves["ist"])
    moves_up = moves[moves["direction"] == "UP"].sort_values("ist")["ist"].values.astype("datetime64[ns]")
    moves_dn = moves[moves["direction"] == "DOWN"].sort_values("ist")["ist"].values.astype("datetime64[ns]")

    out = entries.copy()
    out["entry_ts"] = pd.to_datetime(out["entry_ts"])
    matched, wrong = [], []
    for _, e in out.iterrows():
        ets = pd.Timestamp(e["entry_ts"])
        end = ets + timedelta(minutes=lookforward_min)
        ets_np = np.datetime64(ets.to_datetime64())
        end_np = np.datetime64(end.to_datetime64())
        mat, ant = (moves_up, moves_dn) if e["direction"] == "BULL" else (moves_dn, moves_up)
        m = w = False
        if mat.size:
            i_lo = np.searchsorted(mat, ets_np, side="left")
            i_hi = np.searchsorted(mat, end_np, side="right")
            m = bool(i_hi > i_lo)
        if ant.size:
            i_lo = np.searchsorted(ant, ets_np, side="left")
            i_hi = np.searchsorted(ant, end_np, side="right")
            w = bool(i_hi > i_lo)
        matched.append(m); wrong.append(w)
    out["matched"] = matched
    out["wrong_way"] = wrong
    return out


# ==========================================================================
# Per-symbol orchestration
# ==========================================================================

def run_for_symbol(sb, symbol: str, run_tag: str, tier: str, mode: str = "RETURN") -> pd.DataFrame:
    print(f"\n=== {symbol} ===  (tier={tier}, mode={mode})")

    entries_path = OUT_DIR / f"entries_{symbol}_{run_tag}.csv"
    moves_path = OUT_DIR / f"moves_{symbol}_{run_tag}.csv"
    if not entries_path.exists() or not moves_path.exists():
        print(f"  missing CSVs; skip")
        return pd.DataFrame()
    entries = pd.read_csv(entries_path)
    moves = pd.read_csv(moves_path)
    for c in [c for c in entries.columns if c.startswith("align_")]:
        entries[c] = entries[c].map(lambda v: str(v).lower() in ("true", "1", "1.0"))

    ob_mask = entries["primitive_type"].isin(["BULL_OB", "BEAR_OB"])
    entries = entries[ob_mask
                      & (entries["mode"] == mode)
                      & (entries[f"align_{tier}"])].copy()
    print(f"  OB entries at {tier}/{mode}: {len(entries)}")
    if entries.empty:
        return pd.DataFrame()
    entries["entry_ts"] = pd.to_datetime(entries["entry_ts"])

    # Fetch gamma_metrics over the entry date range (with buffer)
    start = entries["entry_ts"].min() - pd.Timedelta(days=1)
    end = entries["entry_ts"].max() + pd.Timedelta(days=1)
    gamma = fetch_gamma_metrics(sb, symbol, start, end)
    if not gamma.empty:
        print(f"  gamma_metrics range : {gamma['ist'].min()} -> {gamma['ist'].max()}")
        regime_counts = gamma["regime"].value_counts(dropna=False).to_dict()
        print(f"  regime distribution in raw gamma : {regime_counts}")

    entries = attach_gamma_to_entries(entries, gamma)
    entries = precision_per_entry(entries, moves, PRECISION_LOOKFORWARD_MIN)

    # Coverage report on the joined cohort
    join_counts = entries["regime"].value_counts(dropna=False).to_dict()
    print(f"  joined cohort regime counts : {join_counts}")

    entries["symbol"] = symbol
    entries.to_csv(OUT_DIR / f"ob_gamma_scalar_detail_{symbol}_{run_tag}.csv", index=False)

    # Restrict to rows with valid regime (drop NO_DATA, STALE, NULL)
    valid = entries[entries["regime"].isin(["LONG_GAMMA", "SHORT_GAMMA", "NO_FLIP"])].copy()
    print(f"  entries with valid regime : {len(valid)} of {len(entries)}")
    if valid.empty:
        return pd.DataFrame()

    grp = valid.groupby(["primitive_type", "regime"])
    summary = grp.agg(
        n=("matched", "size"),
        n_match=("matched", "sum"),
        n_wrong=("wrong_way", "sum"),
    ).reset_index()
    summary["precision_pct"] = (summary["n_match"] / summary["n"] * 100).round(2)
    summary["wrong_way_pct"] = (summary["n_wrong"] / summary["n"] * 100).round(2)
    summary["symbol"] = symbol
    summary["tier"] = tier
    summary["mode"] = mode

    # Also stratify by gamma_zone (intensity classifier, NOT directional —
    # see Assumption Register D.2: three-zone behavioral role superseded; field
    # kept for research. Test included for completeness.)
    valid_z = entries[entries["gamma_zone"].isin(["HIGH_GAMMA", "MID_GAMMA", "LOW_GAMMA"])].copy()
    if not valid_z.empty:
        grp_z = valid_z.groupby(["primitive_type", "gamma_zone"])
        summary_z = grp_z.agg(
            n=("matched", "size"),
            n_match=("matched", "sum"),
            n_wrong=("wrong_way", "sum"),
        ).reset_index()
        summary_z["precision_pct"] = (summary_z["n_match"] / summary_z["n"] * 100).round(2)
        summary_z["wrong_way_pct"] = (summary_z["n_wrong"] / summary_z["n"] * 100).round(2)
        summary_z["symbol"] = symbol
        summary_z["tier"] = tier
        summary_z["mode"] = mode
        summary_z["axis"] = "gamma_zone"
        summary["axis"] = "regime"
        # Rename so both axes share an "axis_value" column for clean concat
        summary = summary.rename(columns={"regime": "axis_value"})
        summary_z = summary_z.rename(columns={"gamma_zone": "axis_value"})
        summary = pd.concat([summary, summary_z], ignore_index=True)
    else:
        summary["axis"] = "regime"
        summary = summary.rename(columns={"regime": "axis_value"})

    summary.to_csv(OUT_DIR / f"ob_gamma_scalar_summary_{symbol}_{run_tag}.csv", index=False)
    return summary


def print_matrix(df: pd.DataFrame, axis: str, value: str, label: str,
                 col_order=None):
    print(f"\n>>> {label}  (axis = {axis})")
    sub = df[df["axis"] == axis]
    if sub.empty:
        print("  (no data)")
        return
    pv = sub.pivot_table(index=["symbol", "primitive_type"],
                         columns="axis_value", values=value, aggfunc="first")
    if pv.empty:
        print("  (empty pivot)")
        return
    if col_order:
        avail = [c for c in col_order if c in pv.columns]
        if avail:
            pv = pv[avail]
    if value in ("precision_pct", "wrong_way_pct"):
        pv = pv.round(1)
    else:
        pv = pv.astype("Int64")
    print(pv.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--tier", default="T1", choices=["T0", "T1", "T2", "T3"])
    ap.add_argument("--mode", default="RETURN", choices=["RETURN", "FORMATION"])
    args = ap.parse_args()

    if not OUT_DIR.exists():
        sys.exit(f"ERROR: {OUT_DIR.absolute()} missing")

    run_tag = args.run or find_latest_run_tag(OUT_DIR)
    syms = list_symbols_for_run(OUT_DIR, run_tag)
    sb = _connect_supabase()

    print("=" * 78)
    print(f"canonical_ob_gamma_scalar  run={run_tag}  tier={args.tier}  mode={args.mode}")
    print(f"  symbols       = {syms}")
    print(f"  source table  = gamma_metrics  (regime is sign-only, unit-invariant)")
    print(f"  gamma lookback = {GAMMA_LOOKBACK_MIN}min before entry_ts")
    print(f"  precision     = qualifying move in matching direction within "
          f"{PRECISION_LOOKFORWARD_MIN}min")
    print("=" * 78)

    summaries = []
    for sym in syms:
        s = run_for_symbol(sb, sym, run_tag, args.tier, args.mode)
        if s is not None and not s.empty:
            summaries.append(s)

    if not summaries:
        print("\nno summaries; exit")
        return

    combined = pd.concat(summaries, ignore_index=True)
    combined.to_csv(OUT_DIR / f"ob_gamma_scalar_combined_{run_tag}.csv", index=False)

    print("\n" + "=" * 78)
    print(f"OB x GAMMA REGIME (LONG / SHORT / NO_FLIP)  tier={args.tier}, mode={args.mode}")
    print("=" * 78)
    regime_order = ["LONG_GAMMA", "SHORT_GAMMA", "NO_FLIP"]
    print_matrix(combined, "regime", "precision_pct", "PRECISION %", regime_order)
    print_matrix(combined, "regime", "n", "N entries", regime_order)
    print_matrix(combined, "regime", "wrong_way_pct", "WRONG-WAY %", regime_order)

    print("\n" + "=" * 78)
    print(f"OB x GAMMA INTENSITY (HIGH / MID / LOW)  tier={args.tier}, mode={args.mode}")
    print("  NOTE: gamma_zone is intensity, not directional — see Assumption Register D.2")
    print("=" * 78)
    zone_order = ["HIGH_GAMMA", "MID_GAMMA", "LOW_GAMMA"]
    print_matrix(combined, "gamma_zone", "precision_pct", "PRECISION %", zone_order)
    print_matrix(combined, "gamma_zone", "n", "N entries", zone_order)
    print_matrix(combined, "gamma_zone", "wrong_way_pct", "WRONG-WAY %", zone_order)

    print(f"\noutputs: {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
