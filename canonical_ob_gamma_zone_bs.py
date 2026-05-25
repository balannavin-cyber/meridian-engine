#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ob_gamma_zone_bs.py
=============================
Path B: per-strike gamma concentration zones derived from BS-inverted IV on
hist_option_bars_1m premium midpoints over the Apr 2025 - Mar 2026 vendor window.

This sidesteps every MERDIAN gamma-engine concern:
  - TD-NEW-2 flip-finder fragility: we don't compute flip_level.
  - TD-NEW-3 Cr unit regression: we compute units ourselves.
  - TD-S30-CANDIDATE-1 live-writer regression: we don't read from gamma_metrics.
  - NO_FLIP heterogeneity: we don't use a regime classifier at all.

The hypothesis is per-strike: find the contiguous strike range carrying the
top 50% of |signed GEX| mass, classify spot's position BELOW / IN / ABOVE
that range, stratify OB precision by position.

TIMEZONE NOTE (TD-087)
----------------------
hist_option_bars_1m.bar_ts stores IST clock value tagged as UTC. To query for
bars at IST 10:30, the stored value is '<date> 10:30:00+00'. We use IST clock
as the query value directly. hist_spot_bars_1m is UTC-correct so we convert.

BS INVERSION
------------
Newton-Raphson on premium = BS(spot, strike, T, r, sigma). Initial guess 0.20.
Tolerance 1e-4 on premium. Bounds [0.05, 2.0]. Max 30 iterations.
Risk-free rate r = 0.065 (India 91-day T-bill); gamma is not very sensitive to
r for short-dated options.

Premium midpoint = (open + close) / 2. Avoids HL wick artifacts.

NUMERICAL GUARDS
----------------
- Premium midpoint < 5 paise: skip strike-leg (too thin to invert)
- IV outside [0.05, 2.0]: skip strike-leg
- BS doesn't converge: skip strike-leg
- OI <= 0 or null: skip strike-leg
- DTE == 0: skip the entry entirely (gamma diverges as T->0)

EXPIRY SELECTION
----------------
Smallest expiry_date >= bar_date. The near-term weekly is what carries the
dealer hedging force; far expiries contribute negligible gamma.

VENDOR WINDOW CLIP
------------------
Entries clipped to [2025-04-01, 2026-03-31] per operator confirmation that
this is the uniform-vendor-data window. Earlier or later entries dropped.

USAGE
-----
  python canonical_ob_gamma_zone_bs.py
  python canonical_ob_gamma_zone_bs.py --tier T1 --mode RETURN
  python canonical_ob_gamma_zone_bs.py --tier T0   # baseline, more N

INPUTS
------
output_canonical_ict/entries_<SYMBOL>_<RUN>.csv
output_canonical_ict/moves_<SYMBOL>_<RUN>.csv
Supabase hist_option_bars_1m (vendor data)

OUTPUTS
-------
output_canonical_ict/ob_gamma_zone_bs_detail_<SYMBOL>_<RUN>.csv
output_canonical_ict/ob_gamma_zone_bs_summary_<SYMBOL>_<RUN>.csv
output_canonical_ict/ob_gamma_zone_bs_combined_<RUN>.csv
Console: coverage report + 2x3 precision/wrong-way matrix per symbol
"""

from __future__ import annotations
import argparse
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


# ==========================================================================
# Constants
# ==========================================================================

IST = timezone(timedelta(hours=5, minutes=30))
OUT_DIR = Path("output_canonical_ict")

VENDOR_WINDOW_START = pd.Timestamp("2025-04-01")
VENDOR_WINDOW_END = pd.Timestamp("2026-03-31 23:59:59")

PRECISION_LOOKFORWARD_MIN = 15
STRIKE_WINDOW_PCT = 0.03     # ±3% of spot — gamma-active range
ZONE_MASS_THRESHOLD = 0.50   # top 50% of |signed contribution|

# Black-Scholes
RISK_FREE_RATE = 0.065       # India 91-day T-bill, annualized
DAYS_PER_YEAR = 365.0
BS_MAX_ITER = 30
BS_PREMIUM_TOL = 1e-4
IV_MIN = 0.05
IV_MAX = 2.0
PREMIUM_FLOOR = 0.05         # 5 paise; below this BS inversion is unstable


# ==========================================================================
# Supabase
# ==========================================================================

def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    for v in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
        if os.environ.get(v):
            return create_client(url, os.environ[v])
    sys.exit("ERROR: SUPABASE_URL + key not in .env")


# ==========================================================================
# Run-tag + symbol discovery (reused pattern)
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
# Black-Scholes core
# ==========================================================================

def _norm_cdf(x: float) -> float:
    """Standard normal CDF using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _bs_price(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
    """Black-Scholes European option price (no dividends)."""
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K) if is_call else max(0.0, K - S)
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    if is_call:
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def _bs_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Vega (sensitivity of price to sigma). Same for call and put."""
    if T <= 0 or sigma <= 0:
        return 0.0
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    return S * _norm_pdf(d1) * sqrtT


def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Gamma (second derivative of price wrt spot). Same for call and put."""
    if T <= 0 or sigma <= 0:
        return 0.0
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    return _norm_pdf(d1) / (S * sigma * sqrtT)


def invert_iv(price: float, S: float, K: float, T: float, r: float,
              is_call: bool) -> float | None:
    """Newton-Raphson IV inversion. Returns None on non-convergence or bounds violation."""
    if price < PREMIUM_FLOOR or T <= 0 or S <= 0 or K <= 0:
        return None
    intrinsic = max(0.0, S - K) if is_call else max(0.0, K - S)
    if price < intrinsic:
        return None  # premium below intrinsic — bad data
    sigma = 0.20  # initial guess
    for _ in range(BS_MAX_ITER):
        bs = _bs_price(S, K, T, r, sigma, is_call)
        diff = bs - price
        if abs(diff) < BS_PREMIUM_TOL:
            if IV_MIN <= sigma <= IV_MAX:
                return sigma
            return None
        vega = _bs_vega(S, K, T, r, sigma)
        if vega < 1e-8:
            return None
        sigma = sigma - diff / vega
        # Bound clamping during iteration to prevent runaway
        if sigma < 0.001 or sigma > 5.0:
            return None
    return None  # didn't converge


# ==========================================================================
# Per-entry data fetch + zone computation
# ==========================================================================

def fetch_chain_bars_for(sb, bar_ts_ist: pd.Timestamp, spot: float,
                          strike_window_pct: float = STRIKE_WINDOW_PCT) -> pd.DataFrame:
    """
    Pull hist_option_bars_1m rows at bar_ts_ist for strikes within
    ±strike_window_pct of spot, all option types, all expiries available.
    
    TD-087: hist_option_bars_1m.bar_ts stores IST clock value tagged as UTC.
    We query by passing IST clock as the UTC-labeled timestamp directly.
    """
    strike_lo = spot * (1.0 - strike_window_pct)
    strike_hi = spot * (1.0 + strike_window_pct)
    # IST clock value formatted as UTC ISO string (per TD-087 storage convention)
    query_ts = bar_ts_ist.strftime("%Y-%m-%d %H:%M:%S+00:00")
    resp = (sb.table("hist_option_bars_1m")
              .select("bar_ts, expiry_date, strike, option_type, open, high, low, close, oi")
              .eq("bar_ts", query_ts)
              .gte("strike", strike_lo)
              .lte("strike", strike_hi)
              .limit(2000)
              .execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    return df


def compute_zone_for_entry(chain: pd.DataFrame, spot: float,
                            bar_date: pd.Timestamp.date) -> dict:
    """
    From a raw chain dataframe (multiple expiries, CE+PE per strike), pick the
    near-term expiry, BS-invert IV per strike-leg, compute signed gamma
    contribution per strike, identify the gamma concentration zone, classify
    spot's position.

    Returns dict with: zone_low_strike, zone_high_strike, peak_strike,
    spot_state, total_abs_mass, zone_signed_mass, n_strikes_used,
    near_expiry, dte, n_skipped.
    """
    out = {
        "zone_low_strike": None, "zone_high_strike": None, "peak_strike": None,
        "spot_state": "NO_DATA", "total_abs_mass": None, "zone_signed_mass": None,
        "n_strikes_used": 0, "near_expiry": None, "dte": None, "n_skipped": 0,
    }
    if chain.empty:
        return out

    df = chain.copy()
    df["strike"] = df["strike"].astype(float)
    df["expiry_date"] = pd.to_datetime(df["expiry_date"]).dt.date
    df["oi"] = pd.to_numeric(df["oi"], errors="coerce")
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["strike", "expiry_date", "oi", "open", "close"])
    df = df[df["oi"] > 0]
    if df.empty:
        out["spot_state"] = "NO_OI"
        return out

    # Pick near-term expiry: smallest expiry_date >= bar_date
    future_expiries = sorted({e for e in df["expiry_date"] if e >= bar_date})
    if not future_expiries:
        out["spot_state"] = "NO_FUTURE_EXPIRY"
        return out
    near_expiry = future_expiries[0]
    dte_days = (near_expiry - bar_date).days
    if dte_days <= 0:
        out["spot_state"] = "EXPIRY_DAY"
        return out

    out["near_expiry"] = str(near_expiry)
    out["dte"] = dte_days

    sub = df[df["expiry_date"] == near_expiry].copy()
    if sub.empty:
        return out

    T = dte_days / DAYS_PER_YEAR
    r = RISK_FREE_RATE

    rows = []
    n_skipped = 0
    for _, row in sub.iterrows():
        K = float(row["strike"])
        is_call = row["option_type"] in ("CE", "Call", "C")
        is_put = row["option_type"] in ("PE", "Put", "P")
        if not (is_call or is_put):
            n_skipped += 1
            continue
        prem = 0.5 * (float(row["open"]) + float(row["close"]))
        if prem < PREMIUM_FLOOR:
            n_skipped += 1
            continue
        iv = invert_iv(prem, spot, K, T, r, is_call)
        if iv is None:
            n_skipped += 1
            continue
        gamma = _bs_gamma(spot, K, T, r, iv)
        # Per-leg signed contribution in Crore
        sign = 1.0 if is_call else -1.0
        contrib_signed = sign * gamma * float(row["oi"]) * (spot ** 2) * 100.0 / 1e7
        rows.append({"strike": K, "option_type": row["option_type"],
                     "iv": iv, "gamma": gamma, "oi": float(row["oi"]),
                     "contrib_signed": contrib_signed,
                     "contrib_abs": abs(contrib_signed)})

    out["n_skipped"] = n_skipped
    if not rows:
        out["spot_state"] = "NO_VALID_LEGS"
        return out
    legs = pd.DataFrame(rows)
    out["n_strikes_used"] = legs["strike"].nunique()

    # Aggregate per strike (sum CE and PE)
    grp = legs.groupby("strike", as_index=False).agg(signed=("contrib_signed", "sum"),
                                                       absmag=("contrib_abs", "sum"))
    grp = grp.sort_values("strike").reset_index(drop=True)
    total_abs = float(grp["absmag"].sum())
    if total_abs == 0:
        return out
    out["total_abs_mass"] = total_abs

    # Zone: walk outward from strike of max |net signed| until cumulative net_abs >= 50% of total_net_abs
    grp["net_abs"] = grp["signed"].abs()
    target = ZONE_MASS_THRESHOLD * float(grp["net_abs"].sum())
    peak_idx = int(grp["net_abs"].idxmax())
    out["peak_strike"] = float(grp.loc[peak_idx, "strike"])

    lo = hi = peak_idx
    acc = float(grp.loc[peak_idx, "net_abs"])
    while acc < target and (lo > 0 or hi < len(grp) - 1):
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
    out["zone_low_strike"] = zlo
    out["zone_high_strike"] = zhi
    out["zone_signed_mass"] = float(grp.loc[lo:hi, "signed"].sum())

    if spot < zlo:
        out["spot_state"] = "BELOW_ZONE"
    elif spot > zhi:
        out["spot_state"] = "ABOVE_ZONE"
    else:
        out["spot_state"] = "IN_ZONE"

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
# Per-symbol orchestration
# ==========================================================================

def run_for_symbol(sb, symbol: str, run_tag: str, tier: str, mode: str) -> pd.DataFrame:
    import time as _t
    print(f"\n=== {symbol} === (tier={tier}, mode={mode})")
    entries_path = OUT_DIR / f"entries_{symbol}_{run_tag}.csv"
    moves_path = OUT_DIR / f"moves_{symbol}_{run_tag}.csv"
    if not (entries_path.exists() and moves_path.exists()):
        print("  missing input CSVs; skip")
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
    # Clip to vendor window
    n_before = len(entries)
    entries = entries[(entries["entry_ts"] >= VENDOR_WINDOW_START)
                      & (entries["entry_ts"] <= VENDOR_WINDOW_END)].copy()
    print(f"  after vendor-window clip [{VENDOR_WINDOW_START.date()} -> "
          f"{VENDOR_WINDOW_END.date()}] : {len(entries)} (dropped {n_before - len(entries)})")
    if entries.empty:
        return pd.DataFrame()

    # Per-entry zone computation
    print(f"  computing per-strike gamma zones for {len(entries)} entries ...", end="", flush=True)
    t0 = _t.time()
    zone_rows = []
    for i, e in entries.reset_index(drop=True).iterrows():
        ets = pd.Timestamp(e["entry_ts"])
        spot = float(e["spot_at_entry"])
        chain = fetch_chain_bars_for(sb, ets, spot)
        z = compute_zone_for_entry(chain, spot, ets.date())
        zone_rows.append(z)
        if (i + 1) % 50 == 0:
            print(".", end="", flush=True)
    print(f" {_t.time()-t0:.1f}s")

    zdf = pd.DataFrame(zone_rows)
    entries = entries.reset_index(drop=True)
    for c in zdf.columns:
        entries[c] = zdf[c]

    # State distribution before precision
    state_counts = entries["spot_state"].value_counts().to_dict()
    print(f"  spot_state distribution: {state_counts}")

    # Attach precision
    entries = attach_precision(entries, moves, PRECISION_LOOKFORWARD_MIN)
    entries["symbol"] = symbol
    entries.to_csv(OUT_DIR / f"ob_gamma_zone_bs_detail_{symbol}_{run_tag}.csv", index=False)

    valid = entries[entries["spot_state"].isin(["BELOW_ZONE", "IN_ZONE", "ABOVE_ZONE"])].copy()
    print(f"  entries with valid zone state: {len(valid)} / {len(entries)}")
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
    summary.to_csv(OUT_DIR / f"ob_gamma_zone_bs_summary_{symbol}_{run_tag}.csv", index=False)
    return summary


def print_matrix(combined: pd.DataFrame, value: str, label: str, col_order: list):
    print(f"\n>>> {label}")
    pv = combined.pivot_table(index=["symbol", "primitive_type"],
                              columns="spot_state", values=value, aggfunc="first")
    cols = [c for c in col_order if c in pv.columns]
    if not cols:
        print("  (no data)")
        return
    pv = pv[cols]
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
    print(f"canonical_ob_gamma_zone_bs  run={run_tag}  tier={args.tier}  mode={args.mode}")
    print(f"  symbols          = {syms}")
    print(f"  vendor window    = [{VENDOR_WINDOW_START.date()} -> {VENDOR_WINDOW_END.date()}]")
    print(f"  strike window    = +/-{STRIKE_WINDOW_PCT*100:.0f}% of spot")
    print(f"  zone threshold   = top {int(ZONE_MASS_THRESHOLD*100)}% of |net signed GEX| mass")
    print(f"  precision lookfwd= {PRECISION_LOOKFORWARD_MIN}min")
    print(f"  BS r             = {RISK_FREE_RATE}")
    print(f"  TD-087 timezone  = bar_ts queried as IST-clock-as-UTC")
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
    combined.to_csv(OUT_DIR / f"ob_gamma_zone_bs_combined_{run_tag}.csv", index=False)

    print("\n" + "=" * 78)
    print(f"OB x GAMMA ZONE (BS-DERIVED)  tier={args.tier}  mode={args.mode}")
    print("=" * 78)
    order = ["BELOW_ZONE", "IN_ZONE", "ABOVE_ZONE"]
    print_matrix(combined, "precision_pct", "PRECISION %", order)
    print_matrix(combined, "n", "N entries", order)
    print_matrix(combined, "wrong_way_pct", "WRONG-WAY %", order)

    print(f"\noutputs: {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
