#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ob_gamma_zone.py
==========================
OB precision/wrong-way stratified by spot position relative to a gamma
concentration zone derived from per-strike option chain data.

The directional pointer being tested: spot's position relative to the strike
range where dealers carry the most absolute gamma exposure.

States measured per entry:
  BELOW_ZONE  : spot strictly below the concentration range
  IN_ZONE     : spot inside the concentration range (inclusive)
  ABOVE_ZONE  : spot strictly above the concentration range

The matrix produced per symbol x HTF tier x direction:
                     BELOW_ZONE   IN_ZONE   ABOVE_ZONE
  BULL_OB
  BEAR_OB
  precision, wrong-way, N for every cell.

ZERO PRIOR
----------
This script imports nothing from MERDIAN production. It does NOT use
gamma_metrics.net_gex, gamma_metrics.flip_level, or any gamma engine output.
Per-strike GEX is derived directly from option_chain_snapshots in this script,
sidestepping every MERDIAN gamma-engine bug history (TD-NEW-2 flip-finder
fragility, TD-NEW-3 Cr unit, TD-S30-CANDIDATE-1 live writer regression).

INPUTS
------
output_canonical_ict/entries_<SYMBOL>_<RUNTAG>.csv  (from canonical_ict_recall.py)
output_canonical_ict/moves_<SYMBOL>_<RUNTAG>.csv    (same)
Supabase option_chain_snapshots                      (raw vendor data, primary capture)

OUTPUTS
-------
output_canonical_ict/ob_gamma_zone_detail_<SYMBOL>_<RUN>.csv
output_canonical_ict/ob_gamma_zone_summary_<SYMBOL>_<RUN>.csv
output_canonical_ict/ob_gamma_zone_combined_<RUN>.csv
Console: per-symbol coverage report + 2x3 precision matrices

USAGE
-----
  python canonical_ob_gamma_zone.py            # auto-detect latest run, default tier T1
  python canonical_ob_gamma_zone.py --tier T1 --run 20260519_0628
  python canonical_ob_gamma_zone.py --tier T0  # see baseline; T1 cleaner per prior result
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
ZONE_MASS_THRESHOLD = 0.50          # top 50% of |signed contribution|
SNAPSHOT_LOOKBACK_MIN = 30          # entry uses latest snapshot in last 30 min before entry_ts


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
# Option chain coverage probe
# ==========================================================================

def probe_chain_coverage(sb, symbol: str) -> dict:
    """Get min/max ts and row count for symbol in option_chain_snapshots."""
    # Use postgrest count head=True to get total without payload
    resp = (sb.table("option_chain_snapshots")
              .select("ts", count="exact")
              .eq("symbol", symbol)
              .order("ts", desc=False)
              .limit(1)
              .execute())
    if not resp.data:
        return {"n_rows": 0, "min_ts": None, "max_ts": None}
    min_ts = resp.data[0]["ts"]
    resp_max = (sb.table("option_chain_snapshots")
                  .select("ts")
                  .eq("symbol", symbol)
                  .order("ts", desc=True)
                  .limit(1)
                  .execute())
    max_ts = resp_max.data[0]["ts"] if resp_max.data else None
    n_rows = resp.count if resp.count is not None else 0
    return {"n_rows": n_rows, "min_ts": min_ts, "max_ts": max_ts}


# ==========================================================================
# Per-entry gamma zone computation
# ==========================================================================

def fetch_chain_snapshot_for(sb, symbol: str, entry_ts: pd.Timestamp,
                             lookback_min: int = SNAPSHOT_LOOKBACK_MIN) -> pd.DataFrame:
    """
    Pull the latest option_chain_snapshots row(s) for symbol with ts
    in [entry_ts - lookback_min, entry_ts]. Returns DataFrame with strike + greeks.
    """
    end_utc = pd.Timestamp(entry_ts).tz_localize(IST).tz_convert("UTC")
    start_utc = end_utc - pd.Timedelta(minutes=lookback_min)
    resp = (sb.table("option_chain_snapshots")
              .select("ts, strike, option_type, oi, gamma, last_price")
              .eq("symbol", symbol)
              .gte("ts", start_utc.isoformat())
              .lte("ts", end_utc.isoformat())
              .order("ts", desc=True)
              .limit(2000)
              .execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    # Keep only the single most-recent snapshot (one ts may have hundreds of strikes)
    latest_ts = df["ts"].max()
    df = df[df["ts"] == latest_ts].copy()
    return df


def compute_gamma_zone(chain: pd.DataFrame, spot: float,
                       mass_threshold: float = ZONE_MASS_THRESHOLD) -> dict:
    """
    Per-strike signed GEX contribution = gamma * oi * spot^2 * 100 / 1e7  (Crore).
    Sign convention: CE adds positive contribution (dealers typically short CEs
    they sold to buyers => dealer is long gamma on CE positions held by retail).
    PE adds negative contribution.

    Concentration zone: contiguous strike range containing the top mass_threshold
    fraction (default 50%) of total |signed contribution|, walked outward from
    the strike with maximum |signed contribution|.

    Returns: dict with zone_low_strike, zone_high_strike, peak_strike, zone_signed_mass,
             total_abs_mass, spot_state (BELOW_ZONE/IN_ZONE/ABOVE_ZONE).
    """
    if chain.empty:
        return {"zone_low_strike": None, "zone_high_strike": None,
                "peak_strike": None, "spot_state": "NO_DATA",
                "zone_signed_mass": None, "total_abs_mass": None}

    df = chain.copy()
    df["gamma"] = pd.to_numeric(df["gamma"], errors="coerce")
    df["oi"] = pd.to_numeric(df["oi"], errors="coerce")
    df = df.dropna(subset=["gamma", "oi", "strike"])
    df["strike"] = df["strike"].astype(float)
    df["oi"] = df["oi"].astype(float)
    df["gamma"] = df["gamma"].astype(float)

    # Per-row contribution magnitude (always positive)
    df["contrib_abs"] = df["gamma"] * df["oi"] * (spot ** 2) * 100.0 / 1e7

    # Apply sign by option_type
    sign_map = {"CE": 1.0, "PE": -1.0, "Call": 1.0, "Put": -1.0}
    df["sign"] = df["option_type"].map(sign_map).fillna(0.0)
    df["contrib_signed"] = df["sign"] * df["contrib_abs"]

    # Aggregate to per-strike net signed contribution
    grp = df.groupby("strike", as_index=False).agg(
        signed=("contrib_signed", "sum"),
        absmag=("contrib_abs", "sum"),
    )
    if grp.empty or grp["absmag"].sum() == 0:
        return {"zone_low_strike": None, "zone_high_strike": None,
                "peak_strike": None, "spot_state": "NO_MASS",
                "zone_signed_mass": None, "total_abs_mass": None}

    grp = grp.sort_values("strike").reset_index(drop=True)
    total_abs = float(grp["absmag"].sum())

    # The zone is built on |net signed| per strike (a "gamma wall" is a net long or short cluster)
    grp["net_abs"] = grp["signed"].abs()
    peak_idx = int(grp["net_abs"].idxmax())
    peak_strike = float(grp.loc[peak_idx, "strike"])

    # Walk outward symmetrically from peak until cumulative net_abs >= mass_threshold * sum(net_abs)
    target = mass_threshold * float(grp["net_abs"].sum())
    lo = hi = peak_idx
    acc = float(grp.loc[peak_idx, "net_abs"])
    while acc < target and (lo > 0 or hi < len(grp) - 1):
        # Expand toward the neighbor with larger net_abs
        left_val = float(grp.loc[lo - 1, "net_abs"]) if lo > 0 else -1.0
        right_val = float(grp.loc[hi + 1, "net_abs"]) if hi < len(grp) - 1 else -1.0
        if left_val >= right_val and lo > 0:
            lo -= 1
            acc += float(grp.loc[lo, "net_abs"])
        elif hi < len(grp) - 1:
            hi += 1
            acc += float(grp.loc[hi, "net_abs"])
        else:
            break

    zlo = float(grp.loc[lo, "strike"])
    zhi = float(grp.loc[hi, "strike"])
    zone_signed = float(grp.loc[lo:hi, "signed"].sum())

    if spot < zlo:
        state = "BELOW_ZONE"
    elif spot > zhi:
        state = "ABOVE_ZONE"
    else:
        state = "IN_ZONE"

    return {"zone_low_strike": zlo, "zone_high_strike": zhi,
            "peak_strike": peak_strike, "spot_state": state,
            "zone_signed_mass": zone_signed, "total_abs_mass": total_abs}


# ==========================================================================
# Precision computation
# ==========================================================================

def precision_per_entry(entries: pd.DataFrame, moves: pd.DataFrame,
                        lookforward_min: int) -> pd.DataFrame:
    """For each entry, attach matched/wrong_way booleans against the moves cohort."""
    if entries.empty:
        return entries
    moves = moves.copy()
    moves["ist"] = pd.to_datetime(moves["ist"])
    moves_up = moves[moves["direction"] == "UP"].sort_values("ist")["ist"].values.astype("datetime64[ns]")
    moves_dn = moves[moves["direction"] == "DOWN"].sort_values("ist")["ist"].values.astype("datetime64[ns]")

    out = entries.copy()
    out["entry_ts"] = pd.to_datetime(out["entry_ts"])
    matched = []
    wrong = []
    for _, e in out.iterrows():
        ets = pd.Timestamp(e["entry_ts"])
        end = ets + timedelta(minutes=lookforward_min)
        ets_np = np.datetime64(ets.to_datetime64())
        end_np = np.datetime64(end.to_datetime64())
        if e["direction"] == "BULL":
            mat = moves_up
            ant = moves_dn
        else:
            mat = moves_dn
            ant = moves_up
        m = False
        w = False
        if mat.size:
            i_lo = np.searchsorted(mat, ets_np, side="left")
            i_hi = np.searchsorted(mat, end_np, side="right")
            m = bool(i_hi > i_lo)
        if ant.size:
            i_lo = np.searchsorted(ant, ets_np, side="left")
            i_hi = np.searchsorted(ant, end_np, side="right")
            w = bool(i_hi > i_lo)
        matched.append(m)
        wrong.append(w)
    out["matched"] = matched
    out["wrong_way"] = wrong
    return out


# ==========================================================================
# Main per-symbol orchestration
# ==========================================================================

def run_for_symbol(sb, symbol: str, run_tag: str, tier: str,
                   mode: str = "RETURN") -> pd.DataFrame:
    print(f"\n=== {symbol} === (tier={tier}, mode={mode})")

    entries_path = OUT_DIR / f"entries_{symbol}_{run_tag}.csv"
    moves_path = OUT_DIR / f"moves_{symbol}_{run_tag}.csv"
    if not entries_path.exists() or not moves_path.exists():
        print(f"  missing input CSV; skip")
        return pd.DataFrame()

    entries = pd.read_csv(entries_path)
    moves = pd.read_csv(moves_path)

    # Coerce alignment booleans
    for c in [c for c in entries.columns if c.startswith("align_")]:
        entries[c] = entries[c].map(lambda v: str(v).lower() in ("true", "1", "1.0"))

    # Filter to OBs only, at requested tier, mode RETURN, with valid entry_ts
    ob_mask = entries["primitive_type"].isin(["BULL_OB", "BEAR_OB"])
    entries = entries[ob_mask
                      & (entries["mode"] == mode)
                      & (entries[f"align_{tier}"])].copy()
    print(f"  OB entries at {tier}/{mode}: {len(entries)}")
    if entries.empty:
        return entries

    # Coverage probe
    cov = probe_chain_coverage(sb, symbol)
    print(f"  option_chain_snapshots coverage: n={cov['n_rows']} "
          f"min={cov['min_ts']} max={cov['max_ts']}")

    # Restrict entries to dates covered by chain snapshots
    entries["entry_ts"] = pd.to_datetime(entries["entry_ts"])
    if cov["min_ts"] and cov["max_ts"]:
        cov_min = pd.to_datetime(cov["min_ts"]).tz_convert(IST).tz_localize(None)
        cov_max = pd.to_datetime(cov["max_ts"]).tz_convert(IST).tz_localize(None)
        before = len(entries)
        entries = entries[(entries["entry_ts"] >= cov_min)
                          & (entries["entry_ts"] <= cov_max)].copy()
        print(f"  after chain-coverage clip: {len(entries)}  (dropped {before - len(entries)})")

    if entries.empty:
        return entries

    # For each entry, fetch latest chain snapshot, compute zone, attach state.
    print(f"  computing gamma zones for {len(entries)} entries ...", end="", flush=True)
    import time as _t
    t0 = _t.time()
    zone_rows = []
    for i, e in entries.reset_index(drop=True).iterrows():
        chain = fetch_chain_snapshot_for(sb, symbol, e["entry_ts"])
        z = compute_gamma_zone(chain, float(e["spot_at_entry"]))
        zone_rows.append(z)
        if (i + 1) % 100 == 0:
            print(".", end="", flush=True)
    print(f" {_t.time()-t0:.1f}s")

    zdf = pd.DataFrame(zone_rows)
    entries = entries.reset_index(drop=True)
    for c in zdf.columns:
        entries[c] = zdf[c]

    # Precision per entry
    entries = precision_per_entry(entries, moves, PRECISION_LOOKFORWARD_MIN)

    # Save detail
    entries["symbol"] = symbol
    entries.to_csv(OUT_DIR / f"ob_gamma_zone_detail_{symbol}_{run_tag}.csv", index=False)

    # Summary
    valid = entries[entries["spot_state"].isin(["BELOW_ZONE", "IN_ZONE", "ABOVE_ZONE"])]
    print(f"  entries with valid gamma zone state: {len(valid)} / {len(entries)}")
    if valid.empty:
        return pd.DataFrame()

    grp = valid.groupby(["primitive_type", "spot_state"])
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
    summary.to_csv(OUT_DIR / f"ob_gamma_zone_summary_{symbol}_{run_tag}.csv", index=False)

    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    ap.add_argument("--tier", default="T1", choices=["T0", "T1", "T2", "T3"])
    ap.add_argument("--mode", default="RETURN", choices=["RETURN", "FORMATION"])
    args = ap.parse_args()

    if not OUT_DIR.exists():
        sys.exit(f"ERROR: {OUT_DIR.absolute()} missing — run canonical_ict_recall.py first")

    run_tag = args.run or find_latest_run_tag(OUT_DIR)
    syms = list_symbols_for_run(OUT_DIR, run_tag)
    sb = _connect_supabase()

    print("=" * 78)
    print(f"canonical_ob_gamma_zone  run={run_tag}  tier={args.tier}  mode={args.mode}")
    print(f"  symbols       = {syms}")
    print(f"  zone def      = top {int(ZONE_MASS_THRESHOLD*100)}% of |net signed GEX| per strike")
    print(f"  precision     = qualifying move in matching direction within "
          f"{PRECISION_LOOKFORWARD_MIN}min of entry_ts")
    print(f"  snapshot      = latest option_chain_snapshot in last "
          f"{SNAPSHOT_LOOKBACK_MIN}min before entry_ts")
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
    combined.to_csv(OUT_DIR / f"ob_gamma_zone_combined_{run_tag}.csv", index=False)

    print("\n" + "=" * 78)
    print(f"OB x GAMMA-ZONE PRECISION MATRIX  (tier={args.tier}, mode={args.mode})")
    print("=" * 78)
    pv = combined.pivot_table(index=["symbol", "primitive_type"],
                              columns="spot_state",
                              values="precision_pct", aggfunc="first").round(1)
    # Reorder columns
    desired = [c for c in ["BELOW_ZONE", "IN_ZONE", "ABOVE_ZONE"] if c in pv.columns]
    pv = pv[desired]
    print(pv.to_string())

    print("\nN entries per cell:")
    npv = combined.pivot_table(index=["symbol", "primitive_type"],
                               columns="spot_state",
                               values="n", aggfunc="first").astype("Int64")
    npv = npv[desired]
    print(npv.to_string())

    print("\nWrong-way % per cell:")
    wpv = combined.pivot_table(index=["symbol", "primitive_type"],
                               columns="spot_state",
                               values="wrong_way_pct", aggfunc="first").round(1)
    wpv = wpv[desired]
    print(wpv.to_string())

    print(f"\noutputs: {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
