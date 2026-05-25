#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_straddle_slope_schema_probe.py
==========================================
Why does Section E say 84 raw bars but Section D says 0 valid straddle minutes?
This script tests the leading hypothesis: option_type values in
hist_option_bars_1m are NOT "CE"/"PE" as assumed.

Outputs:
  1. Distinct option_type values + counts (from a 1000-row sample)
  2. Distinct expiry_date counts (sanity)
  3. For one specific INSUFFICIENT event from the prior run, full chain dump
     in the [T-15, T] window at ATM strike — every row, every column.

USAGE
-----
  python canonical_straddle_slope_schema_probe.py
"""

from __future__ import annotations
import os
import sys
from datetime import timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


IST = timezone(timedelta(hours=5, minutes=30))
OUT_DIR = Path("output_canonical_ict")
STRIKE_GRID = {"NIFTY": 50.0, "SENSEX": 100.0}


def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    for v in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
        if os.environ.get(v):
            return create_client(url, os.environ[v])
    sys.exit("ERROR: SUPABASE_URL + key not in .env")


def main():
    sb = _connect_supabase()

    print("=" * 78)
    print("STEP 1: DISTINCT option_type VALUES IN hist_option_bars_1m")
    print("=" * 78)
    resp = (sb.table("hist_option_bars_1m")
              .select("option_type")
              .limit(1000)
              .execute())
    df = pd.DataFrame(resp.data)
    print(f"  sample size: {len(df)}")
    print("\nvalue_counts:")
    print(df["option_type"].value_counts(dropna=False).to_string())

    print("\n" + "=" * 78)
    print("STEP 2: COLUMN NAMES (peek at single row)")
    print("=" * 78)
    resp = sb.table("hist_option_bars_1m").select("*").limit(1).execute()
    if resp.data:
        print("columns:", list(resp.data[0].keys()))
        print("\nsample row:")
        for k, v in resp.data[0].items():
            print(f"  {k}: {repr(v)}")

    print("\n" + "=" * 78)
    print("STEP 3: FULL CHAIN DUMP FOR ONE INSUFFICIENT EVENT")
    print("=" * 78)
    # Load the INSUFFICIENT cohort from prior diagnostic CSV
    diag_files = list(OUT_DIR.glob("straddle_diag_insuff_*.csv"))
    event_csvs = list(OUT_DIR.glob("straddle_slope_event_*.csv"))
    if not (diag_files and event_csvs):
        print("  prior diagnostic CSVs not found; skip step 3")
        return

    event_csv = max(event_csvs, key=lambda f: f.stat().st_mtime)
    events_df = pd.read_csv(event_csv)
    events_df["t_move"] = pd.to_datetime(events_df["t_move"])
    insuff = events_df[events_df["state"] == "INSUFFICIENT_BARS"]
    if insuff.empty:
        print("  no INSUFFICIENT events; skip")
        return

    # Pick a NIFTY one for predictable strike grid
    nifty_insuff = insuff[insuff["symbol"] == "NIFTY"]
    if nifty_insuff.empty:
        sample = insuff.iloc[0]
    else:
        sample = nifty_insuff.iloc[0]
    sym = sample["symbol"]
    t_move = pd.Timestamp(sample["t_move"])
    t_ambient = t_move - pd.Timedelta(minutes=15)
    atm_strike = float(sample.get("atm_strike")) if pd.notna(sample.get("atm_strike")) else None
    print(f"  picked event: {sym} {sample['direction']} at {t_move}")
    print(f"  atm_strike from prior run: {atm_strike}")

    if atm_strike is None:
        # Need to resolve spot first
        print("  (atm_strike was NaN; cannot do full chain dump without re-fetching spot)")
        return

    q_low = t_ambient.strftime("%Y-%m-%d %H:%M:%S+00:00")
    q_hi = t_move.strftime("%Y-%m-%d %H:%M:%S+00:00")
    print(f"\n  querying hist_option_bars_1m with:")
    print(f"    strike = {atm_strike}")
    print(f"    bar_ts BETWEEN {q_low} AND {q_hi}")
    resp = (sb.table("hist_option_bars_1m")
              .select("*")
              .eq("strike", atm_strike)
              .gte("bar_ts", q_low)
              .lte("bar_ts", q_hi)
              .order("bar_ts")
              .limit(500)
              .execute())
    chain = pd.DataFrame(resp.data)
    print(f"\n  rows returned: {len(chain)}")
    if chain.empty:
        return

    print("\n  full chain dump (every row, every column):")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)
    print(chain.to_string(index=False))

    print("\n  option_type values in this dump:")
    print(chain["option_type"].value_counts(dropna=False).to_string())
    print("\n  expiry_date values in this dump:")
    if "expiry_date" in chain.columns:
        print(chain["expiry_date"].value_counts(dropna=False).to_string())

    print("\n  bar_ts range:")
    print(f"    min: {chain['bar_ts'].min()}")
    print(f"    max: {chain['bar_ts'].max()}")
    print(f"    n distinct: {chain['bar_ts'].nunique()}")

    # Premium availability
    if "open" in chain.columns and "close" in chain.columns:
        chain["mid"] = 0.5 * (pd.to_numeric(chain["open"], errors="coerce")
                                 + pd.to_numeric(chain["close"], errors="coerce"))
        print(f"\n  premium midpoint stats: n_finite={chain['mid'].notna().sum()}, "
              f"median={chain['mid'].median():.2f}, "
              f"min={chain['mid'].min():.2f}, max={chain['mid'].max():.2f}")


if __name__ == "__main__":
    main()
