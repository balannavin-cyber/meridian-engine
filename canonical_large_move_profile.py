#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_large_move_profile.py
================================
Move-conditional analysis: given that a 100pt+ NIFTY or 300pt+ SENSEX move
happened in a 30-min window, characterize the ambient state in the 15-min
buildup AND track evolution during the move.

This INVERTS the prior tests. Every previous test was OB-conditional:
"given OB fired, what predicts direction?" This test is move-conditional:
"given a large move occurred, what was the surrounding state?"

THREE STAGES IN ONE SCRIPT
--------------------------
Stage 1: Identify large-move events (after threshold + deduplication)
Stage 2: Capture ambient features at T-15min (15min before move start)
Stage 3: Capture features at T and T+15 to track evolution during the move

Stage 4 (replicability / baseline comparison) needs a separate script with
random-baseline sampling, which is what discriminates "common features in
large-move precursors" from "common features in any market minute." Run this
first; stage 4 is justified only if stages 1-3 surface a meaningful pattern.

EVENT DEDUPLICATION
-------------------
The existing moves CSV has every minute whose forward 30-min move qualified.
A single 100pt move generates ~20-30 such timestamps. We collapse them to
single events using a non-overlapping 30-min window walk: take the first
qualifying minute, mark anything within 30min as part of the same event,
advance to the next qualifying minute outside that window.

FEATURE SET
-----------
Window features (asked over [t-15min, t]):
  - has_BULL_OB / has_BEAR_OB / has_BULL_FVG / has_BEAR_FVG
  - max_htf_tier (highest tier any primitive was aligned at: T0/T1/T2/T3)

Snapshot features (at t):
  - gamma_regime (LONG_GAMMA / SHORT_GAMMA / NO_FLIP) — sign-only, regression-safe
  - pcr_near (PE_OI / CE_OI on near-term expiry, ±10% strike window)
  - session_bucket (time-of-day)
  - day_of_week

For stage 3 evolution, snapshot features are captured at three timestamps:
  T_AMBIENT (t-15), T_MOVE (t), T_POST (t+15)

VENDOR WINDOW
-------------
Event detection runs across the full canonical_ict_recall.py date range.
PCR fetches are clipped to vendor window [2025-04-01, 2026-03-31]; outside
that, pcr_near is set to NO_DATA. Gamma_regime is fetched for the full range.

INPUTS
------
output_canonical_ict/entries_<SYMBOL>_<RUN>.csv  (canonical primitives + HTF alignment)
output_canonical_ict/moves_<SYMBOL>_<RUN>.csv     (all qualifying 50pt/150pt moves)
Supabase gamma_metrics, hist_option_bars_1m

OUTPUTS
-------
output_canonical_ict/large_move_events_<RUN>.csv
output_canonical_ict/large_move_profile_<RUN>.txt
Console: event counts + ambient feature distributions + evolution tables
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

LARGE_MOVE_THRESHOLDS = {"NIFTY": 100.0, "SENSEX": 300.0}
EVENT_DEDUP_WINDOW_MIN = 30      # non-overlapping window walk
AMBIENT_LOOKBACK_MIN = 15         # T-15 for buildup features
POST_MOVE_LOOKFORWARD_MIN = 15    # T+15 for evolution snapshot
PCR_STRIKE_WINDOW_PCT = 0.10
OI_FLOOR = 100
GAMMA_LOOKBACK_MIN = 15

VENDOR_WINDOW_START = pd.Timestamp("2025-04-01")
VENDOR_WINDOW_END = pd.Timestamp("2026-03-31 23:59:59")


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
# Run-tag discovery
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
# Stage 1: identify and deduplicate large-move events
# ==========================================================================

def identify_events(moves: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """
    Filter moves to |net_30m| >= threshold. Deduplicate to non-overlapping events.
    Returns one row per event: t_move (first qualifying minute), direction, net_30m at t_move.
    """
    if moves.empty or "net_30m" not in moves.columns:
        return pd.DataFrame()
    df = moves.copy()
    df["ist"] = pd.to_datetime(df["ist"])
    df["abs_move"] = df["net_30m"].abs()
    qual = df[df["abs_move"] >= threshold].sort_values("ist").reset_index(drop=True)
    if qual.empty:
        return pd.DataFrame()

    # Non-overlapping window walk
    events = []
    last_event_end = pd.Timestamp.min
    for _, r in qual.iterrows():
        t = pd.Timestamp(r["ist"])
        if t > last_event_end:
            events.append(r)
            last_event_end = t + pd.Timedelta(minutes=EVENT_DEDUP_WINDOW_MIN)
    out = pd.DataFrame(events).reset_index(drop=True)
    out = out.rename(columns={"ist": "t_move", "direction": "direction",
                                "net_30m": "net_30m_at_move"})
    out["t_ambient"] = out["t_move"] - pd.Timedelta(minutes=AMBIENT_LOOKBACK_MIN)
    out["t_post"] = out["t_move"] + pd.Timedelta(minutes=POST_MOVE_LOOKFORWARD_MIN)
    return out[["t_ambient", "t_move", "t_post", "direction", "net_30m_at_move", "abs_move"]]


# ==========================================================================
# Stage 2: window features from entries CSV (no Supabase fetch needed)
# ==========================================================================

def attach_window_features(events: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    """
    For each event, compute window features over [t_ambient, t_move]:
      - has_BULL_OB, has_BEAR_OB, has_BULL_FVG, has_BEAR_FVG (boolean)
      - max_htf_tier_T0/T1/T2/T3 (any entry aligned at this tier in window)
    Uses entries CSV (already has primitive_type + align_T0..T3 columns).
    """
    out = events.copy()
    if entries.empty:
        for c in ["has_BULL_OB", "has_BEAR_OB", "has_BULL_FVG", "has_BEAR_FVG",
                  "max_htf_tier"]:
            out[c] = None
        return out

    entries = entries.copy()
    entries["entry_ts"] = pd.to_datetime(entries["entry_ts"])
    # Use only RETURN mode for primitive presence (consistent with prior tests)
    entries = entries[entries["mode"] == "RETURN"]
    # Restrict to T0+ (no filter; T0 = no HTF gate, T1+ = aligned at >= H)
    e_ts = entries["entry_ts"].values
    e_type = entries["primitive_type"].values
    align_cols = [c for c in entries.columns if c.startswith("align_")]
    tier_arr = entries[align_cols].values  # bool array

    rows = []
    for _, ev in out.iterrows():
        ta = pd.Timestamp(ev["t_ambient"])
        tm = pd.Timestamp(ev["t_move"])
        # entries in [ta, tm]
        ta_np = np.datetime64(ta.to_datetime64())
        tm_np = np.datetime64(tm.to_datetime64())
        i_lo = np.searchsorted(e_ts, ta_np, side="left")
        i_hi = np.searchsorted(e_ts, tm_np, side="right")
        sub_types = e_type[i_lo:i_hi]
        sub_tiers = tier_arr[i_lo:i_hi]
        r = {
            "has_BULL_OB": bool((sub_types == "BULL_OB").any()),
            "has_BEAR_OB": bool((sub_types == "BEAR_OB").any()),
            "has_BULL_FVG": bool((sub_types == "BULL_FVG").any()),
            "has_BEAR_FVG": bool((sub_types == "BEAR_FVG").any()),
        }
        # max_htf_tier = highest tier any entry in window was aligned at
        max_tier = "T0"
        if sub_tiers.size > 0:
            for tier_idx, tier_name in enumerate(["T0", "T1", "T2", "T3", "T4"]):
                col_idx = align_cols.index(f"align_{tier_name}") if f"align_{tier_name}" in align_cols else -1
                if col_idx < 0:
                    continue
                if sub_tiers[:, col_idx].any():
                    max_tier = tier_name
        r["max_htf_tier"] = max_tier
        rows.append(r)
    feat = pd.DataFrame(rows).reset_index(drop=True)
    return pd.concat([out.reset_index(drop=True), feat], axis=1)


# ==========================================================================
# Stage 3: snapshot features at multiple time slices
# ==========================================================================

def fetch_gamma_range(sb, symbol: str, start_ist: pd.Timestamp,
                      end_ist: pd.Timestamp) -> pd.DataFrame:
    start_utc = start_ist.tz_localize(IST).tz_convert("UTC")
    end_utc = end_ist.tz_localize(IST).tz_convert("UTC")
    rows = []
    page = 0
    while True:
        resp = (sb.table("gamma_metrics")
                  .select("ts, regime")
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
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    df["ist"] = df["ts"].dt.tz_convert(IST).dt.tz_localize(None)
    return df.sort_values("ist").reset_index(drop=True)


def lookup_regime(gamma: pd.DataFrame, t: pd.Timestamp,
                   lookback_min: int = GAMMA_LOOKBACK_MIN) -> str:
    if gamma.empty:
        return "NO_DATA"
    arr = gamma["ist"].values.astype("datetime64[ns]")
    t_np = np.datetime64(pd.Timestamp(t).to_datetime64())
    idx = np.searchsorted(arr, t_np, side="right") - 1
    if idx < 0:
        return "NO_DATA"
    lag_sec = (t_np - arr[idx]).astype("timedelta64[s]").astype(float)
    if lag_sec > lookback_min * 60:
        return "STALE"
    r = gamma["regime"].iloc[idx]
    return str(r) if r is not None else "NULL"


def fetch_pcr_at(sb, t_ist: pd.Timestamp, spot_hint: float | None) -> float | None:
    """
    Compute PCR_near at exact bar_ts.
    Requires a spot estimate to filter strike range. If spot_hint is None, we
    pull spot from hist_spot_bars_1m first (one extra fetch).
    """
    if not (VENDOR_WINDOW_START <= t_ist <= VENDOR_WINDOW_END):
        return None
    if spot_hint is None:
        # Fall back: skip — caller should supply spot
        return None
    strike_lo = spot_hint * (1.0 - PCR_STRIKE_WINDOW_PCT)
    strike_hi = spot_hint * (1.0 + PCR_STRIKE_WINDOW_PCT)
    query_ts = t_ist.strftime("%Y-%m-%d %H:%M:%S+00:00")
    resp = (sb.table("hist_option_bars_1m")
              .select("expiry_date, strike, option_type, oi")
              .eq("bar_ts", query_ts)
              .gte("strike", strike_lo)
              .lte("strike", strike_hi)
              .limit(2000)
              .execute())
    if not resp.data:
        return None
    df = pd.DataFrame(resp.data)
    df["oi"] = pd.to_numeric(df["oi"], errors="coerce")
    df = df[df["oi"] >= OI_FLOOR].dropna(subset=["oi"])
    if df.empty:
        return None
    df["expiry_date"] = pd.to_datetime(df["expiry_date"]).dt.date
    bar_date = t_ist.date()
    future = sorted({e for e in df["expiry_date"] if e >= bar_date})
    if not future:
        return None
    near = future[0]
    if (near - bar_date).days <= 0:
        return None
    near_df = df[df["expiry_date"] == near]
    ce_oi = float(near_df.loc[near_df["option_type"].isin(["CE", "Call", "C"]), "oi"].sum())
    pe_oi = float(near_df.loc[near_df["option_type"].isin(["PE", "Put", "P"]), "oi"].sum())
    if ce_oi <= 0:
        return None
    return pe_oi / ce_oi


def fetch_spot_at(sb, symbol: str, t_ist: pd.Timestamp, instrument_id: str) -> float | None:
    """Fetch spot close from hist_spot_bars_1m at the bar_ts."""
    # hist_spot_bars_1m timezone: pre-2026-04-07 era stored IST-as-UTC, post correct UTC.
    # We are dealing with both eras. Try a flexible window approach: query bar_ts
    # within ±2min of target (handles era ambiguity).
    t_low = t_ist - pd.Timedelta(minutes=2)
    t_hi = t_ist + pd.Timedelta(minutes=2)
    # Attempt 1: IST-as-UTC labeling
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
    # Attempt 2: convert IST to true UTC and try again
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


def session_bucket(t: pd.Timestamp) -> str:
    hm = t.hour * 60 + t.minute
    if hm < 10 * 60:
        return "1_early_0915_1000"
    if hm < 12 * 60:
        return "2_mid_1000_1200"
    if hm < 14 * 60:
        return "3_afternoon_1200_1400"
    return "4_late_1400_1530"


def attach_snapshot_features(sb, events: pd.DataFrame, symbol: str,
                              instrument_id: str, gamma: pd.DataFrame) -> pd.DataFrame:
    """
    For each event, capture snapshot features at three timestamps:
    t_ambient (T-15), t_move (T), t_post (T+15).
    """
    import time as _t
    out = events.copy()
    n = len(out)
    print(f"  [{symbol}] capturing snapshot features for {n} events ...", end="", flush=True)
    t0 = _t.time()
    cols = {}
    for slice_name, ts_col in [("ambient", "t_ambient"), ("move", "t_move"), ("post", "t_post")]:
        regimes = []
        pcrs = []
        for _, ev in out.iterrows():
            t = pd.Timestamp(ev[ts_col])
            regimes.append(lookup_regime(gamma, t))
            # spot at this t (best-effort)
            spot = fetch_spot_at(sb, symbol, t, instrument_id)
            pcr = fetch_pcr_at(sb, t, spot) if spot is not None else None
            pcrs.append(pcr)
        cols[f"regime_{slice_name}"] = regimes
        cols[f"pcr_{slice_name}"] = pcrs
    for c, v in cols.items():
        out[c] = v
    out["session_bucket"] = out["t_move"].apply(lambda t: session_bucket(pd.Timestamp(t)))
    out["day_of_week"] = out["t_move"].apply(lambda t: pd.Timestamp(t).day_name())
    print(f" {_t.time()-t0:.1f}s")
    return out


# ==========================================================================
# Instrument ID resolution (reused from canonical_ict_recall)
# ==========================================================================

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


# ==========================================================================
# Reporting
# ==========================================================================

def emit(buf, line=""):
    print(line)
    buf.append(line)


def stage_4_profile(buf, events_all: pd.DataFrame):
    """Print ambient feature distributions per symbol per direction.
    This is descriptive, not yet a replicability test."""
    emit(buf, "\n" + "=" * 78)
    emit(buf, "STAGE 2 — AMBIENT FEATURE DISTRIBUTIONS AT T-15min (BUILDUP STATE)")
    emit(buf, "=" * 78)

    for sym in events_all["symbol"].unique():
        sub = events_all[events_all["symbol"] == sym]
        if sub.empty:
            continue
        emit(buf, f"\n--- {sym} ---")
        # Window features (per direction)
        emit(buf, "\nBuildup-window primitive presence by direction (% of events with ≥1 of each):")
        win_cols = ["has_BULL_OB", "has_BEAR_OB", "has_BULL_FVG", "has_BEAR_FVG"]
        by_dir = sub.groupby("direction")[win_cols].mean().mul(100).round(1)
        emit(buf, by_dir.to_string())

        emit(buf, "\nMax HTF tier in buildup window:")
        emit(buf, sub.groupby("direction")["max_htf_tier"].value_counts().unstack(fill_value=0).to_string())

        emit(buf, "\nRegime at T-15 (gamma_metrics, sign-only):")
        emit(buf, sub.groupby("direction")["regime_ambient"].value_counts().unstack(fill_value=0).to_string())

        emit(buf, "\nPCR_near at T-15 distribution (numerical):")
        for direction, g in sub.groupby("direction"):
            v = g["pcr_ambient"].dropna()
            if v.empty:
                emit(buf, f"  direction={direction}: no PCR data")
                continue
            emit(buf, f"  direction={direction}: n={len(v)} "
                     f"median={v.median():.3f} q25={v.quantile(.25):.3f} "
                     f"q75={v.quantile(.75):.3f}")

        emit(buf, "\nSession bucket distribution:")
        emit(buf, sub.groupby("direction")["session_bucket"].value_counts().unstack(fill_value=0).to_string())

        emit(buf, "\nDay-of-week distribution:")
        emit(buf, sub.groupby("direction")["day_of_week"].value_counts().unstack(fill_value=0).to_string())


def stage_3_evolution(buf, events_all: pd.DataFrame):
    """Track snapshot features T-15 → T → T+15."""
    emit(buf, "\n" + "=" * 78)
    emit(buf, "STAGE 3 — EVOLUTION DURING THE MOVE (T-15 -> T -> T+15)")
    emit(buf, "=" * 78)

    for sym in events_all["symbol"].unique():
        sub = events_all[events_all["symbol"] == sym]
        emit(buf, f"\n--- {sym} ---")

        # Regime transitions
        emit(buf, "\nRegime transition T-15 -> T+15 (count per direction):")
        for direction, g in sub.groupby("direction"):
            emit(buf, f"\n  direction={direction}:")
            trans = g.groupby(["regime_ambient", "regime_post"]).size().reset_index(name="n")
            trans = trans.sort_values("n", ascending=False)
            emit(buf, trans.to_string(index=False))

        # PCR shift
        emit(buf, "\nPCR_near shift T-15 -> T+15 (median delta per direction):")
        for direction, g in sub.groupby("direction"):
            both_valid = g[g["pcr_ambient"].notna() & g["pcr_post"].notna()]
            if both_valid.empty:
                emit(buf, f"  direction={direction}: no paired PCR data")
                continue
            delta = both_valid["pcr_post"] - both_valid["pcr_ambient"]
            emit(buf, f"  direction={direction}: n={len(delta)} "
                     f"median_delta={delta.median():+.4f} "
                     f"mean_delta={delta.mean():+.4f}")


# ==========================================================================
# Main
# ==========================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=None)
    args = ap.parse_args()

    run_tag = args.run or find_latest_run_tag(OUT_DIR)
    syms = list_symbols_for_run(OUT_DIR, run_tag)
    sb = _connect_supabase()
    inst_ids = _resolve_instrument_ids(sb, syms)

    print("=" * 78)
    print(f"canonical_large_move_profile  run={run_tag}")
    print(f"  symbols     = {syms}")
    print(f"  thresholds  = NIFTY {LARGE_MOVE_THRESHOLDS['NIFTY']}pt / "
          f"SENSEX {LARGE_MOVE_THRESHOLDS['SENSEX']}pt over 30min")
    print(f"  dedup       = non-overlapping {EVENT_DEDUP_WINDOW_MIN}min window")
    print(f"  ambient T   = move_ts - {AMBIENT_LOOKBACK_MIN}min")
    print(f"  post T      = move_ts + {POST_MOVE_LOOKFORWARD_MIN}min")
    print(f"  PCR window  = +/-{PCR_STRIKE_WINDOW_PCT*100:.0f}% (vendor [{VENDOR_WINDOW_START.date()} -> {VENDOR_WINDOW_END.date()}])")
    print("=" * 78)

    all_events = []
    for sym in syms:
        print(f"\n=== {sym} ===")
        entries_path = OUT_DIR / f"entries_{sym}_{run_tag}.csv"
        moves_path = OUT_DIR / f"moves_{sym}_{run_tag}.csv"
        if not (entries_path.exists() and moves_path.exists()):
            print("  missing CSVs; skip")
            continue
        entries = pd.read_csv(entries_path)
        moves = pd.read_csv(moves_path)
        for c in [c for c in entries.columns if c.startswith("align_")]:
            entries[c] = entries[c].map(lambda v: str(v).lower() in ("true", "1", "1.0"))

        threshold = LARGE_MOVE_THRESHOLDS.get(sym, 100.0)
        ev = identify_events(moves, threshold)
        print(f"  qualifying moves (|net_30m| >= {threshold}): "
              f"{(moves['net_30m'].abs() >= threshold).sum() if 'net_30m' in moves.columns else 0}")
        print(f"  distinct events after dedup ({EVENT_DEDUP_WINDOW_MIN}min): {len(ev)}")
        if ev.empty:
            continue

        ev = attach_window_features(ev, entries)

        # Fetch gamma range to cover all event timestamps with buffer
        g_start = (ev["t_ambient"].min() - pd.Timedelta(hours=1))
        g_end = (ev["t_post"].max() + pd.Timedelta(hours=1))
        gamma = fetch_gamma_range(sb, sym, g_start, g_end)
        print(f"  gamma_metrics for window: {len(gamma)} rows")

        ev = attach_snapshot_features(sb, ev, sym, inst_ids.get(sym), gamma)
        ev["symbol"] = sym
        all_events.append(ev)

    if not all_events:
        print("\nno events; exit")
        return

    events_all = pd.concat(all_events, ignore_index=True)
    events_all.to_csv(OUT_DIR / f"large_move_events_{run_tag}.csv", index=False)
    print(f"\nsaved events CSV: large_move_events_{run_tag}.csv  ({len(events_all)} rows)")

    buf = []
    emit(buf, "=" * 78)
    emit(buf, f"LARGE MOVE PROFILING  run={run_tag}")
    emit(buf, f"  N events per symbol/direction:")
    counts = events_all.groupby(["symbol", "direction"]).size().unstack(fill_value=0)
    emit(buf, counts.to_string())
    emit(buf, "=" * 78)

    stage_4_profile(buf, events_all)
    stage_3_evolution(buf, events_all)

    emit(buf, "\n" + "=" * 78)
    emit(buf, "NOTE ON REPLICABILITY (STAGE 4 — DEFERRED)")
    emit(buf, "=" * 78)
    emit(buf, "The distributions above describe what's COMMON among large-move precursors,")
    emit(buf, "but a feature can be 'common' without being predictive — the market spends")
    emit(buf, "most minutes in similar states. To claim a replicable pattern, the same")
    emit(buf, "features need to be measured on a RANDOM-BASELINE cohort of non-event")
    emit(buf, "minutes, then compared. That's the next script.")
    emit(buf, "")
    emit(buf, "Read this output as: 'here's the ambient profile.' Then look for")
    emit(buf, "  - Asymmetries between UP and DOWN cohorts (suggests directional signal)")
    emit(buf, "  - Concentrations differing strongly from intuitive null (e.g., 95% in")
    emit(buf, "    LONG_GAMMA at T-15 when LONG_GAMMA is only 70% of all market minutes)")
    emit(buf, "  - Evolution patterns (regime flip during move, PCR shift, etc.)")

    report_path = OUT_DIR / f"large_move_profile_{run_tag}.txt"
    report_path.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nfull report : {report_path}")
    print("done.")


if __name__ == "__main__":
    main()
