#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_straddle_slope_diagnostic.py
=======================================
Investigate the 57% INSUFFICIENT_BARS loss rate in canonical_straddle_slope.py.

Three failure modes possible:
  A. Strike-grid mismatch: ATM strike (rounded to 50pt NIFTY / 100pt SENSEX)
     happens to fall on a strike with no/sparse bars, even though ATM±1 has
     full bars. Vendor data may not be uniform 50pt grid for all NIFTY expiries.
  B. Premium floor too strict: bars exist but mid premium <0.50 (deep ITM or
     deep OTM on a strike that drifted from ATM as spot moved).
  C. Genuine data sparsity: no liquid option data at all in the window.

PROTOCOL
--------
1. Load straddle_slope_event_<run>.csv (has state column).
2. Profile loss by symbol / direction / month / time-of-day.
3. Sample N INSUFFICIENT_BARS events. For each, query option bars at:
   - ATM±0 (original)
   - ATM±1 strike (nearest above/below)
   - ATM±2 strikes
   - With premium floors: 0.05, 0.20, 0.50 (original)
   Report how many bars come back per (strike offset, floor) combo.
4. Sanity check: same diagnostic on 30 OK events for control.
5. Recovery rate per setting: % of previously-INSUFFICIENT events that now have
   >=5 valid bars under each (strike_offset, premium_floor) combo.
6. Prescriptive verdict: what config recovers the most loss with least risk.

USAGE
-----
  python canonical_straddle_slope_diagnostic.py
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
STRIKE_GRID = {"NIFTY": 50.0, "SENSEX": 100.0}
SAMPLE_SIZE = 60   # of INSUFFICIENT_BARS events to probe
OK_SAMPLE_SIZE = 30


def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    for v in ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY"):
        if os.environ.get(v):
            return create_client(url, os.environ[v])
    sys.exit("ERROR: SUPABASE_URL + key not in .env")


def find_latest_event_csv(out_dir: Path) -> tuple[Path, str]:
    files = list(out_dir.glob("straddle_slope_event_*.csv"))
    if not files:
        sys.exit("ERROR: no straddle_slope_event_*.csv — run canonical_straddle_slope.py first")
    latest = max(files, key=lambda f: f.stat().st_mtime)
    rest = latest.stem[len("straddle_slope_event_"):]
    return latest, rest


def session_bucket(t: pd.Timestamp) -> str:
    hm = t.hour * 60 + t.minute
    if hm < 10 * 60:
        return "1_early_0915_1000"
    if hm < 12 * 60:
        return "2_mid_1000_1200"
    if hm < 14 * 60:
        return "3_afternoon_1200_1400"
    return "4_late_1400_1530"


def fetch_option_bars_at_strike(sb, t_start: pd.Timestamp, t_end: pd.Timestamp,
                                  strike: float) -> pd.DataFrame:
    """Pull all CE+PE bars for one strike across the window."""
    q_low = t_start.strftime("%Y-%m-%d %H:%M:%S+00:00")
    q_hi = t_end.strftime("%Y-%m-%d %H:%M:%S+00:00")
    resp = (sb.table("hist_option_bars_1m")
              .select("bar_ts, expiry_date, option_type, open, close")
              .eq("strike", strike)
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
    return df


def fetch_spot_at_ist(sb, instrument_id: str, t_ist: pd.Timestamp) -> float | None:
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


def probe_event(sb, instrument_id: str, symbol: str,
                t_ambient_iso: str, t_move_iso: str) -> dict:
    """Try ATM-2..ATM+2 with multiple premium floors. Returns count of valid
    straddle minutes per (offset, floor) combo."""
    t_ambient = pd.Timestamp(t_ambient_iso)
    t_move = pd.Timestamp(t_move_iso)
    spot = fetch_spot_at_ist(sb, instrument_id, t_ambient)
    if spot is None:
        return {"spot_found": False}

    grid = STRIKE_GRID[symbol]
    atm_strike = round(spot / grid) * grid
    bar_date = t_move.date()

    out = {"spot_found": True, "atm_strike": atm_strike, "spot_at_ambient": spot}

    for offset in [-2, -1, 0, 1, 2]:
        strike = atm_strike + offset * grid
        bars = fetch_option_bars_at_strike(sb, t_ambient, t_move, strike)
        if bars.empty:
            for floor in [0.05, 0.20, 0.50]:
                out[f"off{offset:+d}_floor{floor:.2f}_n_straddle"] = 0
            out[f"off{offset:+d}_n_raw_bars"] = 0
            continue

        # Pick near-term expiry
        future = sorted({e for e in bars["expiry_date"] if e >= bar_date})
        if not future:
            for floor in [0.05, 0.20, 0.50]:
                out[f"off{offset:+d}_floor{floor:.2f}_n_straddle"] = 0
            out[f"off{offset:+d}_n_raw_bars"] = len(bars)
            continue
        near = future[0]
        if (near - bar_date).days <= 0:
            for floor in [0.05, 0.20, 0.50]:
                out[f"off{offset:+d}_floor{floor:.2f}_n_straddle"] = 0
            out[f"off{offset:+d}_n_raw_bars"] = len(bars)
            continue

        sub = bars[bars["expiry_date"] == near]
        out[f"off{offset:+d}_n_raw_bars"] = len(sub)
        out[f"off{offset:+d}_median_mid"] = float(sub["mid"].median()) if len(sub) else None

        # For each floor, count valid straddle minutes (CE+PE both present, mid>=floor)
        for floor in [0.05, 0.20, 0.50]:
            sub_f = sub[sub["mid"] >= floor]
            ce = sub_f[sub_f["option_type"].isin(["CE", "Call", "C"])].groupby("bar_ts")["mid"].first()
            pe = sub_f[sub_f["option_type"].isin(["PE", "Put", "P"])].groupby("bar_ts")["mid"].first()
            n_straddle = len(set(ce.index) & set(pe.index))
            out[f"off{offset:+d}_floor{floor:.2f}_n_straddle"] = n_straddle
    return out


def emit(buf, line=""):
    print(line); buf.append(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    event_csv, run_tag = find_latest_event_csv(OUT_DIR)
    print(f"loaded: {event_csv.name}  (run_tag={run_tag})")
    df = pd.read_csv(event_csv)
    df["t_move"] = pd.to_datetime(df["t_move"])

    # Also need t_ambient — recompute from t_move
    df["t_ambient"] = df["t_move"] - pd.Timedelta(minutes=15)

    sb = _connect_supabase()
    inst_ids = _resolve_instrument_ids(sb, df["symbol"].unique().tolist())

    # ----- Section A: loss profile -----
    buf = []
    emit(buf, "=" * 78)
    emit(buf, f"STRADDLE SLOPE DIAGNOSTIC  run={run_tag}")
    emit(buf, "=" * 78)
    emit(buf, "\nA. STATE DISTRIBUTION")
    state_counts = df["state"].value_counts()
    emit(buf, state_counts.to_string())
    emit(buf, f"\n  total events: {len(df)}")
    insuff_pct = 100.0 * (df["state"] == "INSUFFICIENT_BARS").sum() / len(df)
    emit(buf, f"  INSUFFICIENT_BARS rate: {insuff_pct:.1f}%")

    # ----- Section B: loss distribution -----
    emit(buf, "\nB. LOSS DISTRIBUTION (INSUFFICIENT_BARS)")
    insuff = df[df["state"] == "INSUFFICIENT_BARS"].copy()
    insuff["month"] = pd.to_datetime(insuff["t_move"]).dt.to_period("M").astype(str)
    insuff["session"] = pd.to_datetime(insuff["t_move"]).apply(session_bucket)
    emit(buf, "\n  by symbol x direction:")
    emit(buf, insuff.groupby(["symbol", "direction"]).size().unstack(fill_value=0).to_string())
    emit(buf, "\n  by month (symbol):")
    emit(buf, insuff.groupby(["symbol", "month"]).size().unstack(fill_value=0).to_string())
    emit(buf, "\n  by session bucket (symbol):")
    emit(buf, insuff.groupby(["symbol", "session"]).size().unstack(fill_value=0).to_string())

    # Same for OK to compare distributions
    ok = df[df["state"] == "OK"].copy()
    ok["month"] = pd.to_datetime(ok["t_move"]).dt.to_period("M").astype(str)
    ok["session"] = pd.to_datetime(ok["t_move"]).apply(session_bucket)
    emit(buf, "\n  OK distribution by session bucket (for comparison):")
    emit(buf, ok.groupby(["symbol", "session"]).size().unstack(fill_value=0).to_string())

    # Loss rate = INSUFFICIENT / (INSUFFICIENT + OK + NO_SPOT) per session — exclude OUTSIDE_VENDOR
    in_range = df[df["state"] != "OUTSIDE_VENDOR_WINDOW"].copy()
    in_range["session"] = pd.to_datetime(in_range["t_move"]).apply(session_bucket)
    loss = in_range.groupby(["symbol", "session"]).agg(
        n=("state", "size"),
        n_insuff=("state", lambda s: (s == "INSUFFICIENT_BARS").sum()),
    ).reset_index()
    loss["loss_pct"] = (loss["n_insuff"] / loss["n"] * 100).round(1)
    emit(buf, "\n  loss rate by session bucket (within vendor window):")
    emit(buf, loss.to_string(index=False))

    # ----- Section C: probe sample of INSUFFICIENT events -----
    emit(buf, "\nC. RECOVERY PROBE")
    emit(buf, f"  Sampling {SAMPLE_SIZE} INSUFFICIENT_BARS events for re-probe")
    emit(buf, f"  Sampling {OK_SAMPLE_SIZE} OK events for control")

    # Balance the sample across symbol/direction
    insuff_sample = []
    for sym in df["symbol"].unique():
        sub = insuff[insuff["symbol"] == sym]
        n_pick = min(SAMPLE_SIZE // 2, len(sub))
        if n_pick > 0:
            picks = sub.sample(n=n_pick, random_state=args.seed)
            insuff_sample.append(picks)
    insuff_sample = pd.concat(insuff_sample, ignore_index=True) if insuff_sample else pd.DataFrame()

    ok_sample = []
    for sym in df["symbol"].unique():
        sub = ok[ok["symbol"] == sym]
        n_pick = min(OK_SAMPLE_SIZE // 2, len(sub))
        if n_pick > 0:
            picks = sub.sample(n=n_pick, random_state=args.seed)
            ok_sample.append(picks)
    ok_sample = pd.concat(ok_sample, ignore_index=True) if ok_sample else pd.DataFrame()

    print(f"\n  probing {len(insuff_sample)} INSUFFICIENT events...", end="", flush=True)
    import time as _t
    t0 = _t.time()
    insuff_probes = []
    for _, ev in insuff_sample.iterrows():
        r = probe_event(sb, inst_ids[ev["symbol"]], ev["symbol"],
                         ev["t_ambient"].isoformat(), ev["t_move"].isoformat())
        r["symbol"] = ev["symbol"]
        r["direction"] = ev["direction"]
        r["t_move"] = ev["t_move"]
        insuff_probes.append(r)
    print(f" {_t.time()-t0:.1f}s")
    insuff_df = pd.DataFrame(insuff_probes)

    print(f"  probing {len(ok_sample)} OK events (control)...", end="", flush=True)
    t0 = _t.time()
    ok_probes = []
    for _, ev in ok_sample.iterrows():
        r = probe_event(sb, inst_ids[ev["symbol"]], ev["symbol"],
                         ev["t_ambient"].isoformat(), ev["t_move"].isoformat())
        r["symbol"] = ev["symbol"]
        r["direction"] = ev["direction"]
        r["t_move"] = ev["t_move"]
        ok_probes.append(r)
    print(f" {_t.time()-t0:.1f}s")
    ok_df = pd.DataFrame(ok_probes)

    # Save raw probe data
    insuff_df.to_csv(OUT_DIR / f"straddle_diag_insuff_{run_tag}.csv", index=False)
    ok_df.to_csv(OUT_DIR / f"straddle_diag_ok_{run_tag}.csv", index=False)

    # ----- Section D: recovery rate per config -----
    emit(buf, "\nD. RECOVERY RATE PER (STRIKE_OFFSET, PREMIUM_FLOOR) CONFIG")
    emit(buf, "  recovery = % of probed INSUFFICIENT events where config gives >=5 valid straddle minutes")

    configs = []
    for offset in [0, 1, -1, 2, -2]:
        for floor in [0.50, 0.20, 0.05]:
            col = f"off{offset:+d}_floor{floor:.2f}_n_straddle"
            if col in insuff_df.columns:
                pass_insuff = (insuff_df[col] >= 5).sum()
                pass_ok = (ok_df[col] >= 5).sum() if col in ok_df.columns else None
                configs.append({
                    "config": f"ATM{offset:+d}, floor>={floor:.2f}",
                    "insuff_recovered": pass_insuff,
                    "insuff_pct": round(100.0 * pass_insuff / max(len(insuff_df), 1), 1),
                    "ok_passing": pass_ok,
                    "ok_pct": round(100.0 * pass_ok / max(len(ok_df), 1), 1) if pass_ok is not None else None,
                })
    cfg_df = pd.DataFrame(configs)
    emit(buf, cfg_df.to_string(index=False))

    # Combined: take best-of any nearby strike
    emit(buf, "\nD2. BEST-OF-NEIGHBORS (use nearest strike with >=5 valid bars at floor 0.50)")
    def best_of(probe_df, offsets=[0, 1, -1, 2, -2], floor=0.50):
        cols = [f"off{o:+d}_floor{floor:.2f}_n_straddle" for o in offsets]
        cols = [c for c in cols if c in probe_df.columns]
        if not cols:
            return 0
        return (probe_df[cols].max(axis=1) >= 5).sum()
    for floor in [0.50, 0.20, 0.05]:
        insuff_rec = best_of(insuff_df, floor=floor)
        ok_rec = best_of(ok_df, floor=floor)
        emit(buf, f"  ATM±2 best-of, floor>={floor:.2f}: "
                  f"INSUFFICIENT recovered={insuff_rec}/{len(insuff_df)} ({100.0*insuff_rec/max(len(insuff_df),1):.1f}%)  "
                  f"OK still pass={ok_rec}/{len(ok_df)} ({100.0*ok_rec/max(len(ok_df),1):.1f}%)")

    # ----- Section E: where IS the data on INSUFFICIENT events -----
    emit(buf, "\nE. RAW BAR PRESENCE BY OFFSET (INSUFFICIENT events)")
    emit(buf, "  median raw bar count at each strike offset (any premium, any expiry, near-term filter applied)")
    raw_stats = []
    for offset in [-2, -1, 0, 1, 2]:
        col = f"off{offset:+d}_n_raw_bars"
        if col in insuff_df.columns:
            v = insuff_df[col].dropna()
            raw_stats.append({
                "offset": offset,
                "n_with_data": int((v > 0).sum()),
                "n_zero": int((v == 0).sum()),
                "median_bars": float(v.median()) if len(v) else None,
                "max_bars": float(v.max()) if len(v) else None,
            })
    emit(buf, pd.DataFrame(raw_stats).to_string(index=False))

    emit(buf, "\n  median premium midpoint by offset (INSUFFICIENT events):")
    prem_stats = []
    for offset in [-2, -1, 0, 1, 2]:
        col = f"off{offset:+d}_median_mid"
        if col in insuff_df.columns:
            v = insuff_df[col].dropna()
            prem_stats.append({
                "offset": offset,
                "n": int(len(v)),
                "median_premium": float(v.median()) if len(v) else None,
                "q25": float(v.quantile(0.25)) if len(v) else None,
                "q75": float(v.quantile(0.75)) if len(v) else None,
            })
    emit(buf, pd.DataFrame(prem_stats).to_string(index=False))

    # ----- Section F: verdict -----
    emit(buf, "\n" + "=" * 78)
    emit(buf, "F. PRESCRIPTION")
    emit(buf, "=" * 78)
    emit(buf, "Read together: which config recovers most INSUFFICIENT without inflating OK rate")
    emit(buf, "  - If recovery jumps from ATM+0 to ATM±1/2 best-of: it's a strike-grid alignment issue")
    emit(buf, "  - If recovery jumps when floor drops 0.50->0.05: it's a thin-premium issue")
    emit(buf, "  - If neither helps much: it's genuine data sparsity, not fixable")

    report_path = OUT_DIR / f"straddle_diag_report_{run_tag}.txt"
    report_path.write_text("\n".join(buf), encoding="utf-8")
    print(f"\nreport: {report_path}")
    print("done.")


if __name__ == "__main__":
    main()
