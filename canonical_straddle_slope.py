#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_straddle_slope.py
============================
Tests whether the ATM straddle premium slope in the 15-min buildup BEFORE a
large move is systematically different from random-baseline slopes.

INTUITION
---------
A rising straddle premium = the option market is pricing in MORE expected
movement (implied vol expanding). A falling premium = vol contraction (theta
+ IV decay winning). If the option market "leads" spot, straddle slopes
should be elevated before large directional moves. If the option market
reacts AFTER spot, pre-move slopes should look like random minutes.

METHOD
------
Per event (large-move or baseline):
  1. Fetch spot at T-15min. Round to grid (NIFTY 50pt, SENSEX 100pt) -> ATM strike.
  2. Fetch CE + PE option bars for that ATM strike, near-term expiry,
     across the [T-15, T] window from hist_option_bars_1m.
  3. Compute straddle premium per minute = mid(CE) + mid(PE).
  4. Slope = linear regression coefficient of premium (Rs) vs minute offset.
     Normalized slope = (premium_end - premium_start) / premium_start.

For each event, percentile-rank its normalized slope against the baseline
distribution. Median event percentile = the diagnostic.

PLOTS (PNG)
-----------
- 2x2 grid: histograms of event-slope-percentiles in baseline distribution
  (NIFTY UP, NIFTY DOWN, SENSEX UP, SENSEX DOWN). If events lead spot,
  histograms skew right (toward 100).
- Scatter: event normalized slope vs |move_size|, colored by direction.

INPUTS
------
output_canonical_ict/large_move_events_<RUN>.csv  (from stage 1-3)
Supabase hist_spot_bars_1m, hist_option_bars_1m

OUTPUTS
-------
output_canonical_ict/straddle_slope_event_<RUN>.csv
output_canonical_ict/straddle_slope_baseline_<RUN>.csv
output_canonical_ict/straddle_slope_plot_<RUN>.png
output_canonical_ict/straddle_slope_report_<RUN>.txt
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

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


IST = timezone(timedelta(hours=5, minutes=30))
OUT_DIR = Path("output_canonical_ict")

AMBIENT_LOOKBACK_MIN = 15
STRIKE_GRID = {"NIFTY": 50.0, "SENSEX": 100.0}
PREMIUM_FLOOR = 0.50    # 50 paise; below this premium series is unreliable
MIN_POINTS_FOR_SLOPE = 5

VENDOR_WINDOW_START = pd.Timestamp("2025-04-01")
VENDOR_WINDOW_END = pd.Timestamp("2026-03-31 23:59:59")

BASELINE_EXCLUSION_MIN = 30


def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    for v in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
        if os.environ.get(v):
            return create_client(url, os.environ[v])
    sys.exit("ERROR: SUPABASE_URL + key not in .env")


def _resolve_instrument_ids(sb, symbols: list) -> dict:
    out = {}
    for s in symbols:
        resp = (sb.table("hist_spot_bars_5m")
                  .select("instrument_id")
                  .eq("symbol", s)
                  .limit(1)
                  .execute())
        if resp.data:
            out[s] = resp.data[0]["instrument_id"]
    return out


def find_latest_events(out_dir: Path) -> tuple[Path, str]:
    files = list(out_dir.glob("large_move_events_*.csv"))
    if not files:
        sys.exit(f"ERROR: no large_move_events_*.csv — run canonical_large_move_profile.py first")
    latest = max(files, key=lambda f: f.stat().st_mtime)
    rest = latest.stem[len("large_move_events_"):]
    return latest, rest


# ==========================================================================
# Fetch helpers — spot + option bars
# ==========================================================================

def fetch_spot_at_ist(sb, instrument_id: str, t_ist: pd.Timestamp) -> float | None:
    """Best-effort spot lookup across both IST-as-UTC and true-UTC era conventions."""
    t_low = t_ist - pd.Timedelta(minutes=2)
    t_hi = t_ist + pd.Timedelta(minutes=2)
    q_low = t_low.strftime("%Y-%m-%d %H:%M:%S+00:00")
    q_hi = t_hi.strftime("%Y-%m-%d %H:%M:%S+00:00")
    resp = (sb.table("hist_spot_bars_1m")
              .select("bar_ts, close")
              .eq("instrument_id", instrument_id)
              .gte("bar_ts", q_low)
              .lte("bar_ts", q_hi)
              .order("bar_ts")
              .limit(10)
              .execute())
    if resp.data:
        return float(resp.data[0]["close"])
    t_low_utc = t_low.tz_localize(IST).tz_convert("UTC")
    t_hi_utc = t_hi.tz_localize(IST).tz_convert("UTC")
    resp = (sb.table("hist_spot_bars_1m")
              .select("bar_ts, close")
              .eq("instrument_id", instrument_id)
              .gte("bar_ts", t_low_utc.isoformat())
              .lte("bar_ts", t_hi_utc.isoformat())
              .order("bar_ts")
              .limit(10)
              .execute())
    if resp.data:
        return float(resp.data[0]["close"])
    return None


def fetch_straddle_window(sb, t_start: pd.Timestamp, t_end: pd.Timestamp,
                           atm_strike: float, bar_date) -> pd.DataFrame:
    """
    Fetch CE + PE bars at atm_strike across [t_start, t_end], pick near-term expiry.
    Returns df with columns: minute_offset, ce_mid, pe_mid, straddle.
    """
    q_low = t_start.strftime("%Y-%m-%d %H:%M:%S+00:00")
    q_hi = t_end.strftime("%Y-%m-%d %H:%M:%S+00:00")
    resp = (sb.table("hist_option_bars_1m")
              .select("bar_ts, expiry_date, option_type, open, close")
              .eq("strike", atm_strike)
              .gte("bar_ts", q_low)
              .lte("bar_ts", q_hi)
              .limit(500)
              .execute())
    if not resp.data:
        return pd.DataFrame()
    df = pd.DataFrame(resp.data)
    df["bar_ts"] = pd.to_datetime(df["bar_ts"], format="ISO8601")
    df["bar_ts"] = df["bar_ts"].dt.tz_localize(None) if df["bar_ts"].dt.tz is not None else df["bar_ts"]
    df["expiry_date"] = pd.to_datetime(df["expiry_date"]).dt.date
    for c in ("open", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "close"])
    df["mid"] = 0.5 * (df["open"] + df["close"])
    df = df[df["mid"] >= PREMIUM_FLOOR]
    if df.empty:
        return pd.DataFrame()

    # Pick smallest expiry with DTE > 0 (skip same-day expiry, which has DTE=0)
    future = sorted({e for e in df["expiry_date"] if e >= bar_date})
    near = None
    for e in future:
        if (e - bar_date).days > 0:
            near = e
            break
    if near is None:
        return pd.DataFrame()
    df = df[df["expiry_date"] == near]
    if df.empty:
        return pd.DataFrame()

    # Pivot: bar_ts x option_type -> mid
    df["is_call"] = df["option_type"].isin(["CE", "Call", "C"])
    df["is_put"] = df["option_type"].isin(["PE", "Put", "P"])
    ce = df[df["is_call"]].groupby("bar_ts")["mid"].first().rename("ce_mid")
    pe = df[df["is_put"]].groupby("bar_ts")["mid"].first().rename("pe_mid")
    merged = pd.concat([ce, pe], axis=1).dropna()
    if merged.empty:
        return pd.DataFrame()
    merged = merged.sort_index()
    merged["straddle"] = merged["ce_mid"] + merged["pe_mid"]
    merged = merged.reset_index().rename(columns={"bar_ts": "ts"})
    start_ts = merged["ts"].min()
    merged["minute_offset"] = (merged["ts"] - start_ts).dt.total_seconds() / 60.0
    return merged


# ==========================================================================
# Slope computation per event
# ==========================================================================

def compute_slope_for_event(sb, instrument_id: str, symbol: str,
                              t_ambient: pd.Timestamp, t_move: pd.Timestamp) -> dict:
    out = {
        "atm_strike": None, "n_points": 0,
        "premium_start": None, "premium_end": None,
        "slope_per_min": None, "normalized_slope": None, "abs_change": None,
        "state": "OK",
    }
    if not (VENDOR_WINDOW_START <= t_move <= VENDOR_WINDOW_END):
        out["state"] = "OUTSIDE_VENDOR_WINDOW"
        return out
    spot_t_ambient = fetch_spot_at_ist(sb, instrument_id, t_ambient)
    if spot_t_ambient is None:
        out["state"] = "NO_SPOT"
        return out
    grid = STRIKE_GRID[symbol]
    atm_strike = round(spot_t_ambient / grid) * grid
    out["atm_strike"] = float(atm_strike)
    straddle = fetch_straddle_window(sb, t_ambient, t_move, atm_strike, t_move.date())
    if straddle.empty or len(straddle) < MIN_POINTS_FOR_SLOPE:
        out["state"] = "INSUFFICIENT_BARS"
        out["n_points"] = len(straddle)
        return out
    out["n_points"] = len(straddle)
    minutes = straddle["minute_offset"].values
    premiums = straddle["straddle"].values
    # Linear regression slope (Rs/min)
    slope, _ = np.polyfit(minutes, premiums, 1)
    out["slope_per_min"] = float(slope)
    out["premium_start"] = float(premiums[0])
    out["premium_end"] = float(premiums[-1])
    out["abs_change"] = float(premiums[-1] - premiums[0])
    out["normalized_slope"] = float((premiums[-1] - premiums[0]) / premiums[0]) if premiums[0] > 0 else None
    return out


# ==========================================================================
# Baseline sampling
# ==========================================================================

def sample_baseline(events: pd.DataFrame, n_samples: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    event_ts = pd.to_datetime(events["t_move"]).values.astype("datetime64[ns]")
    t_min = pd.Timestamp(event_ts.min()).date()
    t_max = pd.Timestamp(event_ts.max()).date()
    days = pd.bdate_range(start=t_min, end=t_max)
    parts = []
    for d in days:
        start = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=30)  # 9:30 to skip very early sparse
        end = pd.Timestamp(d) + pd.Timedelta(hours=15, minutes=15)   # 15:15 to skip very late sparse
        parts.append(pd.date_range(start=start, end=end, freq="1min"))
    all_minutes = pd.DatetimeIndex(np.concatenate([p.values for p in parts]))
    all_ns = all_minutes.values.astype("datetime64[ns]")
    excl_mask = np.zeros(len(all_ns), dtype=bool)
    excl_delta = np.timedelta64(BASELINE_EXCLUSION_MIN, "m")
    for ets in event_ts:
        excl_mask |= (all_ns >= ets - excl_delta) & (all_ns <= ets + excl_delta)
    valid = all_minutes[~excl_mask]
    if len(valid) < n_samples:
        n_samples = len(valid)
    idx = rng.choice(len(valid), size=n_samples, replace=False)
    chosen = valid[idx]
    return pd.DataFrame({
        "t_ambient": chosen - pd.Timedelta(minutes=AMBIENT_LOOKBACK_MIN),
        "t_move": chosen,
    })


# ==========================================================================
# Plotting
# ==========================================================================

def make_plot(events_df: pd.DataFrame, baseline_df: pd.DataFrame, run_tag: str):
    if not HAS_MPL:
        print("matplotlib not installed; skipping plot")
        return
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    syms = sorted(events_df["symbol"].unique())
    for col_i, sym in enumerate(syms):
        # Top row: histogram of event normalized slope (UP / DOWN) overlaid with baseline
        ax = axes[0, col_i]
        b_vals = baseline_df.loc[(baseline_df["symbol"] == sym)
                                  & baseline_df["normalized_slope"].notna(),
                                  "normalized_slope"].values
        e_up = events_df.loc[(events_df["symbol"] == sym)
                              & (events_df["direction"] == "UP")
                              & events_df["normalized_slope"].notna(),
                              "normalized_slope"].values
        e_dn = events_df.loc[(events_df["symbol"] == sym)
                              & (events_df["direction"] == "DOWN")
                              & events_df["normalized_slope"].notna(),
                              "normalized_slope"].values
        if len(b_vals):
            ax.hist(b_vals, bins=40, alpha=0.4, label=f"baseline N={len(b_vals)}",
                    color="gray", density=True)
        if len(e_up):
            ax.hist(e_up, bins=30, alpha=0.5, label=f"event UP N={len(e_up)}",
                    color="green", density=True)
        if len(e_dn):
            ax.hist(e_dn, bins=30, alpha=0.5, label=f"event DOWN N={len(e_dn)}",
                    color="red", density=True)
        ax.axvline(0, color="black", linestyle="--", linewidth=0.5)
        ax.set_title(f"{sym}: normalized straddle slope [T-15, T]")
        ax.set_xlabel("(premium_end - premium_start) / premium_start")
        ax.set_ylabel("density")
        ax.legend()
        ax.set_xlim(-0.5, 0.5)

        # Middle row: scatter event slope vs |move_size|
        ax = axes[1, col_i]
        sub = events_df[(events_df["symbol"] == sym) & events_df["normalized_slope"].notna()]
        for direction, color in [("UP", "green"), ("DOWN", "red")]:
            s = sub[sub["direction"] == direction]
            ax.scatter(s["normalized_slope"], s["abs_move"], alpha=0.5,
                       label=direction, color=color, s=10)
        ax.axvline(0, color="black", linestyle="--", linewidth=0.5)
        ax.set_title(f"{sym}: event slope vs move size")
        ax.set_xlabel("normalized straddle slope (pre-move)")
        ax.set_ylabel("|net_30m| at move (pts)")
        ax.legend()

    # Last column: percentile-rank histograms
    for col_i, sym in enumerate(syms):
        ax = axes[0, 2] if col_i == 0 else axes[1, 2]
        # event-percentile-rank-in-baseline
        b_vals = baseline_df.loc[(baseline_df["symbol"] == sym)
                                  & baseline_df["normalized_slope"].notna(),
                                  "normalized_slope"].values
        if len(b_vals) == 0:
            ax.set_title(f"{sym}: no baseline")
            continue
        b_sorted = np.sort(b_vals)
        e_sub = events_df[(events_df["symbol"] == sym)
                          & events_df["normalized_slope"].notna()]
        ranks_up = []
        ranks_dn = []
        for _, r in e_sub.iterrows():
            pct = float(np.searchsorted(b_sorted, r["normalized_slope"], side="right")) / len(b_sorted) * 100
            if r["direction"] == "UP":
                ranks_up.append(pct)
            else:
                ranks_dn.append(pct)
        if ranks_up:
            ax.hist(ranks_up, bins=20, alpha=0.5, label=f"UP (med={np.median(ranks_up):.1f})",
                    color="green", range=(0, 100))
        if ranks_dn:
            ax.hist(ranks_dn, bins=20, alpha=0.5, label=f"DOWN (med={np.median(ranks_dn):.1f})",
                    color="red", range=(0, 100))
        ax.axvline(50, color="black", linestyle="--", linewidth=0.5)
        ax.set_title(f"{sym}: event slope percentile rank in baseline")
        ax.set_xlabel("percentile (0=lowest, 100=highest vs baseline)")
        ax.set_ylabel("count")
        ax.legend()

    plt.tight_layout()
    path = OUT_DIR / f"straddle_slope_plot_{run_tag}.png"
    plt.savefig(path, dpi=120)
    print(f"  plot saved: {path}")
    plt.close()


# ==========================================================================
# Main
# ==========================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-baseline-mult", type=float, default=1.0)
    args = ap.parse_args()

    events_path, run_tag = find_latest_events(OUT_DIR)
    print(f"loaded events: {events_path.name}  (run_tag={run_tag})")
    events_all = pd.read_csv(events_path)
    events_all["t_ambient"] = pd.to_datetime(events_all["t_ambient"])
    events_all["t_move"] = pd.to_datetime(events_all["t_move"])

    sb = _connect_supabase()
    syms = sorted(events_all["symbol"].unique())
    inst_ids = _resolve_instrument_ids(sb, syms)

    # ----- Per-event slope -----
    print("\n=== EVENT COHORT SLOPES ===")
    event_rows = []
    for sym in syms:
        sub = events_all[events_all["symbol"] == sym].copy()
        print(f"  [{sym}] computing slopes for {len(sub)} events ...", end="", flush=True)
        import time as _t
        t0 = _t.time()
        for i, ev in sub.reset_index(drop=True).iterrows():
            r = compute_slope_for_event(sb, inst_ids[sym], sym,
                                          pd.Timestamp(ev["t_ambient"]),
                                          pd.Timestamp(ev["t_move"]))
            r["symbol"] = sym
            r["direction"] = ev["direction"]
            r["abs_move"] = abs(float(ev["net_30m_at_move"]))
            r["t_move"] = ev["t_move"]
            event_rows.append(r)
            if (i + 1) % 50 == 0:
                print(".", end="", flush=True)
        print(f" {_t.time()-t0:.1f}s")
    events_df = pd.DataFrame(event_rows)
    events_df.to_csv(OUT_DIR / f"straddle_slope_event_{run_tag}.csv", index=False)
    states = events_df["state"].value_counts().to_dict()
    print(f"  state distribution: {states}")

    # ----- Baseline -----
    print("\n=== BASELINE COHORT SLOPES ===")
    baseline_rows = []
    for sym in syms:
        sym_events = events_all[events_all["symbol"] == sym]
        n_target = int(len(sym_events) * args.n_baseline_mult)
        bsamples = sample_baseline(sym_events, n_target)
        print(f"  [{sym}] baseline samples: {len(bsamples)}")
        if bsamples.empty:
            continue
        import time as _t
        t0 = _t.time()
        for i, b in bsamples.reset_index(drop=True).iterrows():
            r = compute_slope_for_event(sb, inst_ids[sym], sym,
                                          pd.Timestamp(b["t_ambient"]),
                                          pd.Timestamp(b["t_move"]))
            r["symbol"] = sym
            r["direction"] = "BASELINE"
            r["abs_move"] = None
            r["t_move"] = b["t_move"]
            baseline_rows.append(r)
            if (i + 1) % 50 == 0:
                print(".", end="", flush=True)
        print(f"  [{sym}] done in {_t.time()-t0:.1f}s")
    baseline_df = pd.DataFrame(baseline_rows)
    baseline_df.to_csv(OUT_DIR / f"straddle_slope_baseline_{run_tag}.csv", index=False)
    states_b = baseline_df["state"].value_counts().to_dict()
    print(f"  baseline state distribution: {states_b}")

    # ----- Stats report -----
    buf = []
    def emit(line=""):
        print(line); buf.append(line)
    emit("=" * 78)
    emit(f"STRADDLE SLOPE ANALYSIS  run={run_tag}")
    emit("=" * 78)

    for sym in syms:
        emit(f"\n--- {sym} ---")
        bvals = baseline_df.loc[(baseline_df["symbol"] == sym)
                                 & baseline_df["normalized_slope"].notna(),
                                 "normalized_slope"].values
        if len(bvals) == 0:
            emit("  no baseline data")
            continue
        b_med = float(np.median(bvals))
        b_q25 = float(np.percentile(bvals, 25))
        b_q75 = float(np.percentile(bvals, 75))
        emit(f"  baseline normalized_slope: n={len(bvals)} median={b_med:+.4f} "
             f"q25={b_q25:+.4f} q75={b_q75:+.4f}")

        b_sorted = np.sort(bvals)
        for direction in ["UP", "DOWN"]:
            evals = events_df.loc[(events_df["symbol"] == sym)
                                   & (events_df["direction"] == direction)
                                   & events_df["normalized_slope"].notna(),
                                   "normalized_slope"].values
            if len(evals) == 0:
                emit(f"  events {direction}: no data")
                continue
            e_med = float(np.median(evals))
            # Percentile-in-baseline for each event
            ranks = np.searchsorted(b_sorted, evals, side="right") / len(b_sorted) * 100
            rank_med = float(np.median(ranks))
            rank_q25 = float(np.percentile(ranks, 25))
            rank_q75 = float(np.percentile(ranks, 75))
            sig = "STRONG" if abs(rank_med - 50) >= 15 else ("WEAK" if abs(rank_med - 50) >= 7 else "NULL")
            emit(f"  events {direction:<5}: n={len(evals)} median_slope={e_med:+.4f}  "
                 f"percentile_rank median={rank_med:.1f} (q25={rank_q25:.1f} q75={rank_q75:.1f})  [{sig}]")

    emit("\nInterpretation:")
    emit("  percentile_rank = where event slope sits in baseline slope distribution")
    emit("  50 = typical (no signal)")
    emit("  >65 = event slopes systematically HIGHER than baseline (vol expansion before move)")
    emit("  <35 = event slopes systematically LOWER than baseline (vol contraction before move — counterintuitive)")
    emit("  STRONG label: |median - 50| >= 15 pp.  WEAK: 7-15 pp.  NULL: <7 pp.")

    report_path = OUT_DIR / f"straddle_slope_report_{run_tag}.txt"
    report_path.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nreport: {report_path}")

    if HAS_MPL:
        print("\n=== PLOTTING ===")
        make_plot(events_df, baseline_df, run_tag)
    else:
        print("(matplotlib not installed; skipping plot. pip install matplotlib to enable.)")

    print("done.")


if __name__ == "__main__":
    main()
