#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ob_pcr.py
===================
Test put-call ratio (OI-based) as a directional pointer on canonical OB
entries. Independent of gamma engine entirely.

PCR (positioning indicator):
  PCR_near  = sum(PE.oi @ near-term expiry) / sum(CE.oi @ near-term expiry)
  PCR_total = sum(PE.oi all expiries in strike window) / sum(CE.oi all expiries)

Conventional interpretation (contrarian framing):
  PCR HIGH  (>~1.2) -> more puts -> bearish positioning -> contrarian bullish
  PCR LOW   (<~0.8) -> more calls -> bullish positioning -> contrarian bearish
  PCR MID         -> balanced positioning

We use cohort-derived tertiles (33rd / 67th percentile thresholds per symbol)
rather than fixed thresholds — clean test, no parameter tuning, balanced N
per cell by construction.

ZERO PRIOR
----------
This test uses only raw OI from hist_option_bars_1m. No gamma engine outputs,
no flip_level, no regime classifier. Sidesteps every concern raised in the
gamma branch (NO_FLIP heterogeneity, Cr unit regression, etc.).

TIMEZONE
--------
hist_option_bars_1m.bar_ts stores IST clock value tagged as UTC (TD-087).
We query by passing IST clock as UTC-labeled string.

VENDOR WINDOW
-------------
Clipped to [2025-04-01, 2026-03-31] per operator clarification — uniform
vendor data window for primary tables.

USAGE
-----
  python canonical_ob_pcr.py
  python canonical_ob_pcr.py --tier T1 --mode RETURN
  python canonical_ob_pcr.py --tier T0
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

VENDOR_WINDOW_START = pd.Timestamp("2025-04-01")
VENDOR_WINDOW_END = pd.Timestamp("2026-03-31 23:59:59")

PRECISION_LOOKFORWARD_MIN = 15
STRIKE_WINDOW_PCT = 0.10     # ±10% — broader than BS test; PCR is positioning, not greeks
OI_FLOOR = 100               # below this, the leg is dead and shouldn't count


def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    for v in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
        if os.environ.get(v):
            return create_client(url, os.environ[v])
    sys.exit("ERROR: SUPABASE_URL + key not in .env")


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
# Per-entry PCR computation
# ==========================================================================

def fetch_oi_for(sb, bar_ts_ist: pd.Timestamp, spot: float,
                  strike_window_pct: float = STRIKE_WINDOW_PCT) -> pd.DataFrame:
    """
    Pull hist_option_bars_1m OI rows at bar_ts_ist for strikes within
    ±strike_window_pct of spot, all option types, all expiries.
    
    TD-087: query bar_ts as IST clock value formatted as UTC ISO.
    """
    strike_lo = spot * (1.0 - strike_window_pct)
    strike_hi = spot * (1.0 + strike_window_pct)
    query_ts = bar_ts_ist.strftime("%Y-%m-%d %H:%M:%S+00:00")
    resp = (sb.table("hist_option_bars_1m")
              .select("expiry_date, strike, option_type, oi")
              .eq("bar_ts", query_ts)
              .gte("strike", strike_lo)
              .lte("strike", strike_hi)
              .limit(2000)
              .execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["strike"] = df["strike"].astype(float)
    df["expiry_date"] = pd.to_datetime(df["expiry_date"]).dt.date
    df["oi"] = pd.to_numeric(df["oi"], errors="coerce")
    df = df.dropna(subset=["oi"])
    df = df[df["oi"] >= OI_FLOOR]
    return df


def compute_pcr_for_entry(chain: pd.DataFrame, bar_date) -> dict:
    """
    Compute PCR_near (near-term expiry) and PCR_total (all expiries).
    """
    out = {"pcr_near": None, "pcr_total": None,
           "ce_oi_near": 0, "pe_oi_near": 0,
           "ce_oi_total": 0, "pe_oi_total": 0,
           "near_expiry": None, "dte": None,
           "pcr_state": "NO_DATA"}
    if chain.empty:
        return out

    df = chain.copy()
    # Normalize option_type
    df["is_call"] = df["option_type"].isin(["CE", "Call", "C"])
    df["is_put"] = df["option_type"].isin(["PE", "Put", "P"])
    df = df[df["is_call"] | df["is_put"]]
    if df.empty:
        return out

    # Pick near-term expiry: smallest expiry_date >= bar_date
    future_expiries = sorted({e for e in df["expiry_date"] if e >= bar_date})
    if not future_expiries:
        out["pcr_state"] = "NO_FUTURE_EXPIRY"
        return out
    near = future_expiries[0]
    dte = (near - bar_date).days
    if dte <= 0:
        out["pcr_state"] = "EXPIRY_DAY"
        return out

    out["near_expiry"] = str(near)
    out["dte"] = dte

    # Near-term PCR
    near_df = df[df["expiry_date"] == near]
    ce_near = float(near_df.loc[near_df["is_call"], "oi"].sum())
    pe_near = float(near_df.loc[near_df["is_put"], "oi"].sum())
    out["ce_oi_near"] = ce_near
    out["pe_oi_near"] = pe_near
    if ce_near > 0:
        out["pcr_near"] = pe_near / ce_near

    # Total (all expiries in window) PCR
    ce_total = float(df.loc[df["is_call"], "oi"].sum())
    pe_total = float(df.loc[df["is_put"], "oi"].sum())
    out["ce_oi_total"] = ce_total
    out["pe_oi_total"] = pe_total
    if ce_total > 0:
        out["pcr_total"] = pe_total / ce_total

    if out["pcr_near"] is not None and out["pcr_total"] is not None:
        out["pcr_state"] = "OK"
    elif out["pcr_near"] is None and ce_near == 0:
        out["pcr_state"] = "NO_CE_NEAR"
    else:
        out["pcr_state"] = "PARTIAL"
    return out


# ==========================================================================
# Precision attach (reused pattern)
# ==========================================================================

def attach_precision(entries: pd.DataFrame, moves: pd.DataFrame,
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
            m = bool(np.searchsorted(mat, end_np, side="right") > np.searchsorted(mat, ets_np, side="left"))
        if ant.size:
            w = bool(np.searchsorted(ant, end_np, side="right") > np.searchsorted(ant, ets_np, side="left"))
        matched.append(m); wrong.append(w)
    out["matched"] = matched
    out["wrong_way"] = wrong
    return out


# ==========================================================================
# Tertile classification
# ==========================================================================

def assign_tertiles(entries: pd.DataFrame, value_col: str, label_col: str) -> pd.DataFrame:
    """Per-symbol tertile split on value_col (33rd / 67th percentile)."""
    out = entries.copy()
    out[label_col] = "NO_DATA"
    for sym in out["symbol"].unique():
        mask = (out["symbol"] == sym) & out[value_col].notna()
        vals = out.loc[mask, value_col].astype(float)
        if vals.empty:
            continue
        p33 = float(vals.quantile(1/3))
        p67 = float(vals.quantile(2/3))
        def cls(v):
            if pd.isna(v):
                return "NO_DATA"
            if v < p33:
                return "LOW"
            if v > p67:
                return "HIGH"
            return "MID"
        out.loc[mask, label_col] = out.loc[mask, value_col].apply(cls)
        print(f"  [{sym}] {value_col} tertiles: LOW <{p33:.3f} / MID / HIGH >{p67:.3f}  "
              f"(n_with_value={mask.sum()})")
    return out


# ==========================================================================
# Per-symbol orchestration
# ==========================================================================

def run_for_symbol(sb, symbol: str, run_tag: str, tier: str, mode: str) -> pd.DataFrame:
    import time as _t
    print(f"\n=== {symbol} === (tier={tier}, mode={mode})")
    entries_path = OUT_DIR / f"entries_{symbol}_{run_tag}.csv"
    moves_path = OUT_DIR / f"moves_{symbol}_{run_tag}.csv"
    if not (entries_path.exists() and moves_path.exists()):
        print("  missing CSVs; skip")
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
    n_before = len(entries)
    entries = entries[(entries["entry_ts"] >= VENDOR_WINDOW_START)
                      & (entries["entry_ts"] <= VENDOR_WINDOW_END)].copy()
    print(f"  after vendor-window clip: {len(entries)} (dropped {n_before - len(entries)})")
    if entries.empty:
        return pd.DataFrame()

    # Per-entry PCR
    print(f"  fetching OI + computing PCR for {len(entries)} entries ...", end="", flush=True)
    t0 = _t.time()
    rows = []
    for i, e in entries.reset_index(drop=True).iterrows():
        ets = pd.Timestamp(e["entry_ts"])
        spot = float(e["spot_at_entry"])
        chain = fetch_oi_for(sb, ets, spot)
        r = compute_pcr_for_entry(chain, ets.date())
        rows.append(r)
        if (i + 1) % 50 == 0:
            print(".", end="", flush=True)
    print(f" {_t.time()-t0:.1f}s")

    pdf = pd.DataFrame(rows)
    entries = entries.reset_index(drop=True)
    for c in pdf.columns:
        entries[c] = pdf[c]

    state_counts = entries["pcr_state"].value_counts().to_dict()
    print(f"  pcr_state distribution: {state_counts}")

    entries = attach_precision(entries, moves, PRECISION_LOOKFORWARD_MIN)
    entries["symbol"] = symbol
    return entries


def precision_matrix(combined: pd.DataFrame, pcr_col: str, label: str):
    valid = combined[combined[pcr_col].isin(["LOW", "MID", "HIGH"])].copy()
    if valid.empty:
        print(f"\n>>> {label} : (no valid rows)")
        return
    grp = valid.groupby(["symbol", "primitive_type", pcr_col])
    s = grp.agg(
        n=("matched", "size"),
        n_match=("matched", "sum"),
        n_wrong=("wrong_way", "sum"),
    ).reset_index()
    s["precision_pct"] = (s["n_match"] / s["n"] * 100).round(1)
    s["wrong_way_pct"] = (s["n_wrong"] / s["n"] * 100).round(1)

    print(f"\n>>> {label}")
    pv_p = s.pivot_table(index=["symbol", "primitive_type"], columns=pcr_col,
                          values="precision_pct", aggfunc="first")
    pv_n = s.pivot_table(index=["symbol", "primitive_type"], columns=pcr_col,
                          values="n", aggfunc="first").astype("Int64")
    pv_w = s.pivot_table(index=["symbol", "primitive_type"], columns=pcr_col,
                          values="wrong_way_pct", aggfunc="first")
    order = [c for c in ["LOW", "MID", "HIGH"] if c in pv_p.columns]
    pv_p = pv_p[order]
    pv_n = pv_n[order]
    pv_w = pv_w[order]
    print("\nPRECISION %")
    print(pv_p.to_string())
    print("\nN entries")
    print(pv_n.to_string())
    print("\nWRONG-WAY %")
    print(pv_w.to_string())


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
    print(f"canonical_ob_pcr  run={run_tag}  tier={args.tier}  mode={args.mode}")
    print(f"  symbols       = {syms}")
    print(f"  vendor window = [{VENDOR_WINDOW_START.date()} -> {VENDOR_WINDOW_END.date()}]")
    print(f"  strike window = +/-{STRIKE_WINDOW_PCT*100:.0f}% of spot")
    print(f"  OI floor      = {OI_FLOOR}")
    print(f"  source        = hist_option_bars_1m (vendor data, no gamma engine)")
    print(f"  tertiles      = cohort-derived per symbol (33rd/67th percentile)")
    print("=" * 78)

    all_entries = []
    for sym in syms:
        e = run_for_symbol(sb, sym, run_tag, args.tier, args.mode)
        if e is not None and not e.empty:
            all_entries.append(e)

    if not all_entries:
        print("\nno entries processed; exit")
        return

    combined = pd.concat(all_entries, ignore_index=True)

    # Assign per-symbol tertiles for both PCR variants
    print("\n--- tertile assignment ---")
    combined = assign_tertiles(combined, "pcr_near", "tertile_near")
    combined = assign_tertiles(combined, "pcr_total", "tertile_total")

    combined.to_csv(OUT_DIR / f"ob_pcr_detail_{run_tag}.csv", index=False)

    print("\n" + "=" * 78)
    print("OB x PCR_NEAR (near-term expiry only)")
    print("=" * 78)
    precision_matrix(combined, "tertile_near", "PCR_NEAR tertile")

    print("\n" + "=" * 78)
    print("OB x PCR_TOTAL (all expiries in ±10% strike window)")
    print("=" * 78)
    precision_matrix(combined, "tertile_total", "PCR_TOTAL tertile")

    # Sanity: PCR distribution per symbol
    print("\n" + "=" * 78)
    print("PCR DISTRIBUTION SANITY (per symbol)")
    print("=" * 78)
    for sym in syms:
        sub = combined[combined["symbol"] == sym]
        for col in ("pcr_near", "pcr_total"):
            vals = sub[col].dropna()
            if vals.empty:
                continue
            print(f"  {sym} {col}: n={len(vals)} "
                  f"median={vals.median():.3f} "
                  f"q25={vals.quantile(0.25):.3f} "
                  f"q75={vals.quantile(0.75):.3f} "
                  f"min={vals.min():.3f} "
                  f"max={vals.max():.3f}")

    print(f"\noutputs: {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
