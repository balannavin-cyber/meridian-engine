#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_large_move_baseline.py
=================================
Stage 4: random-baseline comparison for the large-move profile findings.

The profile script (canonical_large_move_profile.py) characterized the ambient
state preceding large moves. But "feature is common in event cohort" doesn't
mean predictive — the feature might just be common in any market minute.

This script samples a random-baseline cohort (non-event minutes from the same
trading-day range) and captures the same features. Then computes:
  - Difference in feature frequencies (event_pct - baseline_pct)
  - Bootstrap 95% CI on the difference
  - Verdict per feature: SIGNIFICANT / TRENDING / NULL

CANDIDATE PATTERNS FROM PROFILE OUTPUT
---------------------------------------
1. SHORT_GAMMA over-represented on DOWN events (8pp on SENSEX, 4pp on NIFTY)
2. LONG->SHORT regime flips concentrated on DOWN moves (11% SENSEX DOWN vs 5% UP)
3. PCR rises during SENSEX UP moves (+0.021 mean delta)

If any survive baseline scrutiny, they're real signal. Profile output also
showed canonical OB/FVG ABSENT in 84-99% of buildup windows; baseline comparison
will quantify whether even that low rate is below market base rate.

PROTOCOL
--------
1. Load large_move_events_<run>.csv from stage 1-3.
2. For each symbol, enumerate trading minutes in event date range. Exclude
   minutes within ±30min of any event. Random-sample N matching events count.
3. For each baseline minute: capture same features (window: OB/FVG presence;
   snapshot: regime, PCR at t-15/t/t+15).
4. Bootstrap CI on event - baseline differences for each candidate finding.
5. Print verdict table.

Same Supabase fetch shape as stage 1-3. Runtime similar (~30-40 min).

OUTPUTS
-------
output_canonical_ict/large_move_baseline_events_<RUN>.csv
output_canonical_ict/large_move_baseline_verdict_<RUN>.txt
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

EVENT_EXCLUSION_WINDOW_MIN = 30
AMBIENT_LOOKBACK_MIN = 15
POST_LOOKFORWARD_MIN = 15
PCR_STRIKE_WINDOW_PCT = 0.10
OI_FLOOR = 100
GAMMA_LOOKBACK_MIN = 15

VENDOR_WINDOW_START = pd.Timestamp("2025-04-01")
VENDOR_WINDOW_END = pd.Timestamp("2026-03-31 23:59:59")

BOOTSTRAP_ITER = 1000
CI_LEVEL = 0.95


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


# ==========================================================================
# Baseline sampling
# ==========================================================================

def sample_baseline_minutes(symbol_events: pd.DataFrame, n_samples: int,
                             seed: int = 42) -> pd.DataFrame:
    """
    Sample random non-event trading minutes from the event date range.
    Excludes minutes within ±EVENT_EXCLUSION_WINDOW_MIN of any event timestamp.
    """
    rng = np.random.default_rng(seed)
    if symbol_events.empty:
        return pd.DataFrame()

    event_ts = pd.to_datetime(symbol_events["t_move"]).values.astype("datetime64[ns]")
    t_min = pd.Timestamp(event_ts.min()).date()
    t_max = pd.Timestamp(event_ts.max()).date()

    # Enumerate all session minutes across business days in range
    days = pd.bdate_range(start=t_min, end=t_max)
    parts = []
    for d in days:
        # IST session 09:15 to 15:30
        start = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=15)
        end = pd.Timestamp(d) + pd.Timedelta(hours=15, minutes=30)
        parts.append(pd.date_range(start=start, end=end, freq="1min"))
    all_minutes = pd.DatetimeIndex(np.concatenate([p.values for p in parts]))
    all_ns = all_minutes.values.astype("datetime64[ns]")

    # Exclusion window around each event
    excl_mask = np.zeros(len(all_ns), dtype=bool)
    excl_delta = np.timedelta64(EVENT_EXCLUSION_WINDOW_MIN, "m")
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
        "t_post": chosen + pd.Timedelta(minutes=POST_LOOKFORWARD_MIN),
    })


# ==========================================================================
# Feature capture (mirrors stage 1-3)
# ==========================================================================

def attach_window_features(events: pd.DataFrame, entries: pd.DataFrame) -> pd.DataFrame:
    out = events.copy()
    if entries.empty:
        for c in ["has_BULL_OB", "has_BEAR_OB", "has_BULL_FVG", "has_BEAR_FVG"]:
            out[c] = False
        out["max_htf_tier"] = "T0"
        return out
    entries = entries[entries["mode"] == "RETURN"].copy()
    entries["entry_ts"] = pd.to_datetime(entries["entry_ts"])
    entries = entries.sort_values("entry_ts").reset_index(drop=True)
    e_ts = entries["entry_ts"].values.astype("datetime64[ns]")
    e_type = entries["primitive_type"].values
    align_cols = [c for c in entries.columns if c.startswith("align_")]
    tier_arr = entries[align_cols].values

    rows = []
    for _, ev in out.iterrows():
        ta = np.datetime64(pd.Timestamp(ev["t_ambient"]).to_datetime64())
        tm = np.datetime64(pd.Timestamp(ev["t_move"]).to_datetime64())
        i_lo = np.searchsorted(e_ts, ta, side="left")
        i_hi = np.searchsorted(e_ts, tm, side="right")
        sub_types = e_type[i_lo:i_hi]
        sub_tiers = tier_arr[i_lo:i_hi]
        r = {
            "has_BULL_OB": bool((sub_types == "BULL_OB").any()),
            "has_BEAR_OB": bool((sub_types == "BEAR_OB").any()),
            "has_BULL_FVG": bool((sub_types == "BULL_FVG").any()),
            "has_BEAR_FVG": bool((sub_types == "BEAR_FVG").any()),
        }
        max_tier = "T0"
        if sub_tiers.size > 0:
            for tier_name in ["T0", "T1", "T2", "T3", "T4"]:
                col = f"align_{tier_name}"
                if col in align_cols:
                    idx = align_cols.index(col)
                    if sub_tiers[:, idx].any():
                        max_tier = tier_name
        r["max_htf_tier"] = max_tier
        rows.append(r)
    feat = pd.DataFrame(rows).reset_index(drop=True)
    return pd.concat([out.reset_index(drop=True), feat], axis=1)


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


def fetch_pcr_at(sb, t_ist: pd.Timestamp, spot_hint) -> float | None:
    if not (VENDOR_WINDOW_START <= t_ist <= VENDOR_WINDOW_END):
        return None
    if spot_hint is None or pd.isna(spot_hint):
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


def fetch_spot_at(sb, instrument_id: str, t_ist: pd.Timestamp) -> float | None:
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


def attach_snapshot_features(sb, events: pd.DataFrame, instrument_id: str,
                              gamma: pd.DataFrame, label: str) -> pd.DataFrame:
    import time as _t
    out = events.copy()
    n = len(out)
    print(f"  [{label}] snapshot features for {n} samples ...", end="", flush=True)
    t0 = _t.time()
    for slice_name, ts_col in [("ambient", "t_ambient"), ("move", "t_move"), ("post", "t_post")]:
        regimes, pcrs = [], []
        for _, ev in out.iterrows():
            t = pd.Timestamp(ev[ts_col])
            regimes.append(lookup_regime(gamma, t))
            spot = fetch_spot_at(sb, instrument_id, t)
            pcrs.append(fetch_pcr_at(sb, t, spot) if spot else None)
        out[f"regime_{slice_name}"] = regimes
        out[f"pcr_{slice_name}"] = pcrs
    print(f" {_t.time()-t0:.1f}s")
    return out


# ==========================================================================
# Bootstrap-based difference CIs
# ==========================================================================

def bootstrap_diff(event_vals, baseline_vals, stat_fn,
                    n_iter: int = BOOTSTRAP_ITER, ci: float = CI_LEVEL,
                    seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    e = np.asarray(event_vals)
    b = np.asarray(baseline_vals)
    if len(e) == 0 or len(b) == 0:
        return {"n_event": len(e), "n_baseline": len(b),
                "event_stat": None, "baseline_stat": None,
                "diff": None, "ci_lo": None, "ci_hi": None, "verdict": "NO_DATA"}
    e_stat = float(stat_fn(e))
    b_stat = float(stat_fn(b))
    diffs = []
    for _ in range(n_iter):
        es = rng.choice(e, size=len(e), replace=True)
        bs = rng.choice(b, size=len(b), replace=True)
        diffs.append(float(stat_fn(es)) - float(stat_fn(bs)))
    diffs = np.array(diffs)
    lo = float(np.percentile(diffs, (1 - ci) / 2 * 100))
    hi = float(np.percentile(diffs, (1 + ci) / 2 * 100))
    if lo > 0 or hi < 0:
        verdict = "SIGNIFICANT"
    elif (lo > -abs(e_stat - b_stat) * 0.3) or (hi < abs(e_stat - b_stat) * 0.3):
        verdict = "TRENDING"
    else:
        verdict = "NULL"
    return {"n_event": int(len(e)), "n_baseline": int(len(b)),
            "event_stat": e_stat, "baseline_stat": b_stat,
            "diff": e_stat - b_stat, "ci_lo": lo, "ci_hi": hi, "verdict": verdict}


def emit(buf, line=""):
    print(line)
    buf.append(line)


def print_test(buf, name: str, result: dict, fmt: str = "{:.3f}"):
    if result["verdict"] == "NO_DATA":
        emit(buf, f"  {name:<50}  NO DATA")
        return
    s = (f"  {name:<50}  "
         f"event={fmt.format(result['event_stat'])}  "
         f"baseline={fmt.format(result['baseline_stat'])}  "
         f"diff={fmt.format(result['diff'])}  "
         f"95%CI=[{fmt.format(result['ci_lo'])}, {fmt.format(result['ci_hi'])}]  "
         f"N_e={result['n_event']} N_b={result['n_baseline']}  "
         f"[{result['verdict']}]")
    emit(buf, s)


# ==========================================================================
# Main
# ==========================================================================

def find_latest_events(out_dir: Path) -> tuple[Path, str]:
    files = list(out_dir.glob("large_move_events_*.csv"))
    if not files:
        sys.exit(f"ERROR: no large_move_events_*.csv — run canonical_large_move_profile.py first")
    latest = max(files, key=lambda f: f.stat().st_mtime)
    rest = latest.stem[len("large_move_events_"):]
    return latest, rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-baseline-mult", type=float, default=1.0,
                    help="baseline samples per event (default 1x)")
    args = ap.parse_args()

    events_path, run_tag = find_latest_events(OUT_DIR)
    print(f"loaded events: {events_path.name}  (run_tag={run_tag})")
    events_all = pd.read_csv(events_path)
    events_all["t_ambient"] = pd.to_datetime(events_all["t_ambient"])
    events_all["t_move"] = pd.to_datetime(events_all["t_move"])
    events_all["t_post"] = pd.to_datetime(events_all["t_post"])
    print(f"  total events: {len(events_all)}")

    sb = _connect_supabase()
    syms = sorted(events_all["symbol"].unique())
    inst_ids = _resolve_instrument_ids(sb, syms)

    baselines_all = []
    for sym in syms:
        print(f"\n=== {sym} BASELINE SAMPLING ===")
        sym_events = events_all[events_all["symbol"] == sym]
        n_target = int(len(sym_events) * args.n_baseline_mult)
        baseline = sample_baseline_minutes(sym_events, n_target)
        print(f"  baseline samples: {len(baseline)}")
        if baseline.empty:
            continue

        # Load entries CSV for window features
        entries_path = OUT_DIR / f"entries_{sym}_{run_tag}.csv"
        if not entries_path.exists():
            print("  missing entries CSV; skip")
            continue
        entries = pd.read_csv(entries_path)
        for c in [c for c in entries.columns if c.startswith("align_")]:
            entries[c] = entries[c].map(lambda v: str(v).lower() in ("true", "1", "1.0"))
        baseline = attach_window_features(baseline, entries)

        # Gamma range
        g_start = baseline["t_ambient"].min() - pd.Timedelta(hours=1)
        g_end = baseline["t_post"].max() + pd.Timedelta(hours=1)
        gamma = fetch_gamma_range(sb, sym, g_start, g_end)
        print(f"  gamma_metrics for window: {len(gamma)} rows")

        baseline = attach_snapshot_features(sb, baseline, inst_ids.get(sym), gamma, sym)
        baseline["symbol"] = sym
        baselines_all.append(baseline)

    if not baselines_all:
        print("\nno baseline; exit")
        return
    baseline_all = pd.concat(baselines_all, ignore_index=True)
    baseline_all.to_csv(OUT_DIR / f"large_move_baseline_events_{run_tag}.csv", index=False)
    print(f"\nsaved baseline CSV ({len(baseline_all)} rows)")

    # =====================================================================
    # Verdict reporting
    # =====================================================================
    buf = []
    emit(buf, "=" * 78)
    emit(buf, f"LARGE MOVE BASELINE COMPARISON  run={run_tag}")
    emit(buf, f"  bootstrap iter = {BOOTSTRAP_ITER}, CI = {int(CI_LEVEL*100)}%")
    emit(buf, "=" * 78)

    for sym in syms:
        emit(buf, "\n" + "#" * 78)
        emit(buf, f"# {sym}")
        emit(buf, "#" * 78)
        sym_events = events_all[events_all["symbol"] == sym]
        sym_baseline = baseline_all[baseline_all["symbol"] == sym]
        if sym_events.empty or sym_baseline.empty:
            continue

        # ----- TEST GROUP 1: Primitive presence (window features) -----
        emit(buf, "\n--- 1. PRIMITIVE PRESENCE in buildup window (events vs baseline) ---")
        for prim in ["has_BULL_OB", "has_BEAR_OB", "has_BULL_FVG", "has_BEAR_FVG"]:
            for direction in ["UP", "DOWN", "ANY"]:
                if direction == "ANY":
                    e_vals = sym_events[prim].astype(int).values
                else:
                    e_vals = sym_events[sym_events["direction"] == direction][prim].astype(int).values
                b_vals = sym_baseline[prim].astype(int).values
                res = bootstrap_diff(e_vals, b_vals, np.mean)
                print_test(buf, f"{prim} ({direction})", res, fmt="{:.3f}")

        # ----- TEST GROUP 2: Regime distribution at T-15 -----
        emit(buf, "\n--- 2. REGIME at T-15min (events vs baseline) ---")
        for regime in ["LONG_GAMMA", "SHORT_GAMMA", "NO_FLIP"]:
            for direction in ["UP", "DOWN", "ANY"]:
                if direction == "ANY":
                    e_sub = sym_events
                else:
                    e_sub = sym_events[sym_events["direction"] == direction]
                e_vals = (e_sub["regime_ambient"].astype(str) == regime).astype(int).values
                b_vals = (sym_baseline["regime_ambient"].astype(str) == regime).astype(int).values
                res = bootstrap_diff(e_vals, b_vals, np.mean)
                print_test(buf, f"regime_ambient = {regime} ({direction})", res, fmt="{:.3f}")

        # ----- TEST GROUP 3: Regime flip rate -----
        emit(buf, "\n--- 3. REGIME FLIP T-15 -> T+15 (events vs baseline) ---")
        valid_regimes = ["LONG_GAMMA", "SHORT_GAMMA", "NO_FLIP"]
        def flip_indicator(df):
            mask = (df["regime_ambient"].astype(str).isin(valid_regimes)) & \
                   (df["regime_post"].astype(str).isin(valid_regimes))
            sub = df[mask]
            return ((sub["regime_ambient"].astype(str) != sub["regime_post"].astype(str))
                    .astype(int).values)
        for direction in ["UP", "DOWN", "ANY"]:
            if direction == "ANY":
                e_sub = sym_events
            else:
                e_sub = sym_events[sym_events["direction"] == direction]
            e_vals = flip_indicator(e_sub)
            b_vals = flip_indicator(sym_baseline)
            res = bootstrap_diff(e_vals, b_vals, np.mean)
            print_test(buf, f"any regime flip ({direction})", res, fmt="{:.3f}")

        # LONG->SHORT specifically
        def long_to_short(df):
            mask = (df["regime_ambient"].astype(str).isin(valid_regimes)) & \
                   (df["regime_post"].astype(str).isin(valid_regimes))
            sub = df[mask]
            return ((sub["regime_ambient"].astype(str) == "LONG_GAMMA") &
                    (sub["regime_post"].astype(str) == "SHORT_GAMMA")).astype(int).values
        for direction in ["UP", "DOWN", "ANY"]:
            if direction == "ANY":
                e_sub = sym_events
            else:
                e_sub = sym_events[sym_events["direction"] == direction]
            e_vals = long_to_short(e_sub)
            b_vals = long_to_short(sym_baseline)
            res = bootstrap_diff(e_vals, b_vals, np.mean)
            print_test(buf, f"LONG_GAMMA -> SHORT_GAMMA flip ({direction})", res, fmt="{:.3f}")

        # ----- TEST GROUP 4: PCR delta during window -----
        emit(buf, "\n--- 4. PCR_near DELTA T-15 -> T+15 (events vs baseline) ---")
        def pcr_delta_vals(df):
            mask = df["pcr_ambient"].notna() & df["pcr_post"].notna()
            sub = df[mask]
            return (sub["pcr_post"].astype(float) - sub["pcr_ambient"].astype(float)).values
        for direction in ["UP", "DOWN", "ANY"]:
            if direction == "ANY":
                e_sub = sym_events
            else:
                e_sub = sym_events[sym_events["direction"] == direction]
            e_vals = pcr_delta_vals(e_sub)
            b_vals = pcr_delta_vals(sym_baseline)
            res = bootstrap_diff(e_vals, b_vals, np.median)
            print_test(buf, f"PCR_near delta MEDIAN ({direction})", res, fmt="{:+.4f}")
            res_m = bootstrap_diff(e_vals, b_vals, np.mean)
            print_test(buf, f"PCR_near delta MEAN ({direction})", res_m, fmt="{:+.4f}")

        # ----- TEST GROUP 5: PCR ambient level -----
        emit(buf, "\n--- 5. PCR_near LEVEL at T-15 (events vs baseline) ---")
        def pcr_ambient_vals(df):
            return df["pcr_ambient"].dropna().astype(float).values
        for direction in ["UP", "DOWN", "ANY"]:
            if direction == "ANY":
                e_sub = sym_events
            else:
                e_sub = sym_events[sym_events["direction"] == direction]
            e_vals = pcr_ambient_vals(e_sub)
            b_vals = pcr_ambient_vals(sym_baseline)
            res = bootstrap_diff(e_vals, b_vals, np.median)
            print_test(buf, f"PCR_near ambient MEDIAN ({direction})", res, fmt="{:.4f}")

    report_path = OUT_DIR / f"large_move_baseline_verdict_{run_tag}.txt"
    report_path.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nfull report: {report_path}")
    print("done.")


if __name__ == "__main__":
    main()
