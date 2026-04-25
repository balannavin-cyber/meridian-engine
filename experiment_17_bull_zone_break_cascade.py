#!/usr/bin/env python3
"""
experiment_17_bull_zone_break_cascade.py

MERDIAN Experiment 17 -- BULL Zone Break-Below as Rejection Cascade

Question:
    When NIFTY/SENSEX 5m close prints below the lower edge of an active
    W BULL_FVG or W BULL_OB by >= 0.1%, is the subsequent return statistically
    more bearish than baseline?

Origin:
    2026-04-24 NIFTY price action -- open inside W BULL_FVG 24,074-24,241,
    broke below, cascaded -275 pts to 23,898 EOD. Spec recorded in
    docs/research/MERDIAN_Experiment_Compendium_v1.md, "Experiment 17
    (PROPOSED)" section.

Pass criteria (any of):
    - T+30m mean return <= -0.3%   (baseline ~0%)
    - T+60m mean return <= -0.5%
    - T+EOD mean return <= -0.6%
    - T+EOD return < 0 in >= 65% of cases

Schema confirmed 2026-04-25 against live Supabase:
    ict_htf_zones (16 cols incl. zone_low, zone_high, valid_from, valid_to,
                   broken_at_date, status, symbol, timeframe, pattern_type)
    hist_spot_bars_5m (NIFTY 20,654 bars / SENSEX 20,594 bars,
                       period 2025-04-01 .. 2026-04-15)

Universe period note:
    Reduced from spec's 2024-01..2026-04 (28 months) to actual 2025-04-01..
    2026-04-15 (12.5 months). Sample target >= 30 events still feasible.

Outputs:
    experiment_17_events.csv           -- one row per detected break event
    experiment_17_baseline_buckets.csv -- per-bar T+N returns for baseline
    stdout verdict block ready to paste into the Compendium
"""

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# ---- Config -----------------------------------------------------------------

BREAK_THRESHOLD_FRAC = 0.001  # 0.1% below zone_low
BARS_30M = 6                  # 6 x 5m
BARS_60M = 12                 # 12 x 5m
PATTERNS = ("BULL_FVG", "BULL_OB")
TIMEFRAME = "W"
SYMBOLS = ("NIFTY", "SENSEX")
PAGE = 1000

OUT_DIR = Path(__file__).parent
OUT_EVENTS = OUT_DIR / "experiment_17_events.csv"
OUT_BASELINE = OUT_DIR / "experiment_17_baseline_buckets.csv"

# ---- Supabase ---------------------------------------------------------------

def get_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        sys.exit("[FATAL] SUPABASE_URL / SUPABASE_(SERVICE_ROLE_)KEY not set")
    return create_client(url, key)


def fetch_bars(sb) -> pd.DataFrame:
    """Pull all 5m bars for NIFTY + SENSEX. Sorted by symbol, bar_ts."""
    rows = []
    for sym in SYMBOLS:
        offset = 0
        while True:
            res = (
                sb.table("hist_spot_bars_5m")
                .select("symbol,bar_ts,open,high,low,close")
                .eq("symbol", sym)
                .order("bar_ts")
                .range(offset, offset + PAGE - 1)
                .execute()
            )
            chunk = res.data or []
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < PAGE:
                break
            offset += PAGE
    df = pd.DataFrame(rows)
    df["bar_ts"] = pd.to_datetime(df["bar_ts"], utc=True).dt.tz_convert(None)
    df["bar_date"] = df["bar_ts"].dt.date
    df["tod_bucket"] = df["bar_ts"].dt.strftime("%H:%M")
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col])
    df = df.sort_values(["symbol", "bar_ts"]).reset_index(drop=True)
    return df


def fetch_zones(sb) -> pd.DataFrame:
    """All W BULL_FVG/BULL_OB zones, any status, both symbols."""
    rows = []
    for pat in PATTERNS:
        res = (
            sb.table("ict_htf_zones")
            .select(
                "id,symbol,timeframe,pattern_type,"
                "zone_high,zone_low,"
                "valid_from,valid_to,broken_at_date,status"
            )
            .eq("timeframe", TIMEFRAME)
            .eq("pattern_type", pat)
            .execute()
        )
        rows.extend(res.data or [])
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ("valid_from", "valid_to", "broken_at_date"):
        df[col] = pd.to_datetime(df[col]).dt.date
    df["zone_low"] = pd.to_numeric(df["zone_low"])
    df["zone_high"] = pd.to_numeric(df["zone_high"])
    return df

# ---- Core logic -------------------------------------------------------------

def find_break_events(bars: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """
    For each (bar, zone) pair where:
      bar.symbol == zone.symbol
      AND bar.bar_date in [zone.valid_from, zone.valid_to]
      AND (zone.broken_at_date is null OR bar.bar_date <= zone.broken_at_date)
      AND bar.close < zone.zone_low * (1 - 0.001)
      AND prev bar (same symbol) close >= zone.zone_low

    Register only the FIRST qualifying bar per zone (no double-counting;
    relies on the direction filter to suppress post-break same-day bars).
    """
    if zones.empty or bars.empty:
        return pd.DataFrame()

    bars = bars.copy()
    bars["prev_close"] = bars.groupby("symbol")["close"].shift(1)

    events = []
    for _, z in zones.iterrows():
        threshold = float(z["zone_low"]) * (1 - BREAK_THRESHOLD_FRAC)
        sym_bars = bars[bars["symbol"] == z["symbol"]]
        if sym_bars.empty:
            continue

        in_window = sym_bars["bar_date"].between(z["valid_from"], z["valid_to"])

        broken = z["broken_at_date"]
        if pd.isna(broken):
            not_yet_broken = pd.Series(True, index=sym_bars.index)
        else:
            not_yet_broken = sym_bars["bar_date"] <= broken

        broke_below = sym_bars["close"] < threshold
        came_from_above = sym_bars["prev_close"] >= float(z["zone_low"])

        candidates = sym_bars[
            in_window & not_yet_broken & broke_below & came_from_above
        ]
        if candidates.empty:
            continue

        first = candidates.iloc[0]
        events.append({
            "zone_id": z["id"],
            "symbol": z["symbol"],
            "pattern_type": z["pattern_type"],
            "zone_low": float(z["zone_low"]),
            "zone_high": float(z["zone_high"]),
            "zone_status_today": z["status"],
            "valid_from": z["valid_from"],
            "valid_to": z["valid_to"],
            "broken_at_date": z["broken_at_date"],
            "break_bar_ts": first["bar_ts"],
            "break_bar_close": float(first["close"]),
            "prev_bar_close": float(first["prev_close"]),
            "tod_bucket": first["tod_bucket"],
            "break_threshold": threshold,
        })
    return pd.DataFrame(events)


def attach_outcomes(events: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    """For each event compute T+30m / T+60m / T+EOD returns vs break-bar close."""
    if events.empty:
        return events

    events = events.copy()
    events["bar_date"] = pd.to_datetime(events["break_bar_ts"]).dt.date

    sym_indexed = {}
    for sym in SYMBOLS:
        sb = (
            bars[bars["symbol"] == sym]
            .sort_values("bar_ts")
            .reset_index(drop=True)
        )
        ts_to_idx = {ts: i for i, ts in enumerate(sb["bar_ts"])}
        sym_indexed[sym] = (sb, ts_to_idx)

    t30, t60, eod_ret = [], [], []
    for _, e in events.iterrows():
        sb, idx_map = sym_indexed[e["symbol"]]
        i = idx_map.get(e["break_bar_ts"])
        if i is None:
            t30.append(np.nan); t60.append(np.nan); eod_ret.append(np.nan)
            continue
        c0 = float(e["break_bar_close"])

        c30 = float(sb.iloc[i + BARS_30M]["close"]) if i + BARS_30M < len(sb) else np.nan
        c60 = float(sb.iloc[i + BARS_60M]["close"]) if i + BARS_60M < len(sb) else np.nan

        same_day = sb[(sb["bar_date"] == e["bar_date"]) & (sb.index >= i)]
        ce = float(same_day.iloc[-1]["close"]) if not same_day.empty else np.nan

        t30.append((c30 / c0 - 1) if not np.isnan(c30) else np.nan)
        t60.append((c60 / c0 - 1) if not np.isnan(c60) else np.nan)
        eod_ret.append((ce / c0 - 1) if not np.isnan(ce) else np.nan)

    events["ret_t30m"] = t30
    events["ret_t60m"] = t60
    events["ret_eod"] = eod_ret
    return events


def build_baseline(bars: pd.DataFrame) -> pd.DataFrame:
    """
    For every 5m bar compute (ret_t30m, ret_t60m, ret_eod). The set of all such
    rows is the baseline universe. Time-of-day buckets let us match an event
    to a bucket-conditioned baseline distribution.

    Note: baseline includes the event bars themselves; with thousands of bars
    and dozens of events the dilution is < 1% and ignorable.
    """
    rows = []
    for sym in SYMBOLS:
        sb = bars[bars["symbol"] == sym].sort_values("bar_ts").reset_index(drop=True)
        closes = sb["close"].to_numpy()
        dates = sb["bar_date"].to_numpy()
        tods = sb["tod_bucket"].to_numpy()

        eod_close_by_date = (
            sb.groupby("bar_date")["close"].last().to_dict()
        )

        for i in range(len(sb)):
            c0 = closes[i]
            d0 = dates[i]
            c30 = closes[i + BARS_30M] if i + BARS_30M < len(sb) else np.nan
            c60 = closes[i + BARS_60M] if i + BARS_60M < len(sb) else np.nan
            ce = eod_close_by_date.get(d0, np.nan)

            rows.append({
                "symbol": sym,
                "tod_bucket": tods[i],
                "ret_t30m": (c30 / c0 - 1) if not pd.isna(c30) else np.nan,
                "ret_t60m": (c60 / c0 - 1) if not pd.isna(c60) else np.nan,
                "ret_eod": (ce / c0 - 1) if not pd.isna(ce) else np.nan,
            })
    return pd.DataFrame(rows)


def compute_verdict(events: pd.DataFrame, baseline: pd.DataFrame) -> dict:
    """Apply Pass criteria from Compendium spec."""
    if events.empty:
        return {"verdict": "NO_DATA", "n": 0}

    bucket_means = (
        baseline.groupby(["symbol", "tod_bucket"])
        .agg(b30=("ret_t30m", "mean"),
             b60=("ret_t60m", "mean"),
             beod=("ret_eod", "mean"))
        .reset_index()
    )
    merged = events.merge(bucket_means, on=["symbol", "tod_bucket"], how="left")

    n = len(events)
    mean30 = events["ret_t30m"].mean()
    mean60 = events["ret_t60m"].mean()
    meaneod = events["ret_eod"].mean()
    eod_neg_pct = (events["ret_eod"] < 0).mean()

    base30 = merged["b30"].mean()
    base60 = merged["b60"].mean()
    baseeod = merged["beod"].mean()

    pass_30 = bool(mean30 <= -0.003)
    pass_60 = bool(mean60 <= -0.005)
    pass_eod = bool(meaneod <= -0.006)
    pass_eod_neg = bool(eod_neg_pct >= 0.65)
    any_pass = any([pass_30, pass_60, pass_eod, pass_eod_neg])

    return {
        "verdict": "PASS" if any_pass else "FAIL",
        "n": int(n),
        "mean_t30m": float(mean30),
        "mean_t60m": float(mean60),
        "mean_eod": float(meaneod),
        "eod_negative_pct": float(eod_neg_pct),
        "baseline_t30m": float(base30) if pd.notna(base30) else None,
        "baseline_t60m": float(base60) if pd.notna(base60) else None,
        "baseline_eod": float(baseeod) if pd.notna(baseeod) else None,
        "delta_t30m_vs_baseline": float(mean30 - base30) if pd.notna(base30) else None,
        "delta_t60m_vs_baseline": float(mean60 - base60) if pd.notna(base60) else None,
        "delta_eod_vs_baseline": float(meaneod - baseeod) if pd.notna(baseeod) else None,
        "checks": {
            "t30m_le_-0.3pct": pass_30,
            "t60m_le_-0.5pct": pass_60,
            "eod_le_-0.6pct": pass_eod,
            "eod_neg_ge_65pct": pass_eod_neg,
        },
    }


def print_verdict(v: dict, events: pd.DataFrame) -> None:
    print()
    print("=" * 72)
    print("EXPERIMENT 17 -- VERDICT")
    print("=" * 72)
    if v["verdict"] == "NO_DATA":
        print("  NO_DATA -- zero break events found. Check zone universe / threshold.")
        return

    pct = lambda x: f"{x * 100:+.3f}%" if x is not None else "  n/a"

    print(f"  N events: {v['n']}")
    print(f"  Symbol breakdown: "
          f"{events['symbol'].value_counts().to_dict()}")
    print(f"  Pattern breakdown: "
          f"{events['pattern_type'].value_counts().to_dict()}")
    print()
    print(f"  Mean ret  T+30m: {pct(v['mean_t30m'])}     "
          f"baseline: {pct(v['baseline_t30m'])}     "
          f"delta: {pct(v['delta_t30m_vs_baseline'])}")
    print(f"  Mean ret  T+60m: {pct(v['mean_t60m'])}     "
          f"baseline: {pct(v['baseline_t60m'])}     "
          f"delta: {pct(v['delta_t60m_vs_baseline'])}")
    print(f"  Mean ret  T+EOD: {pct(v['mean_eod'])}     "
          f"baseline: {pct(v['baseline_eod'])}     "
          f"delta: {pct(v['delta_eod_vs_baseline'])}")
    print(f"  T+EOD return < 0: {v['eod_negative_pct'] * 100:.1f}% of events")
    print()
    print("  Pass criteria:")
    for k, val in v["checks"].items():
        print(f"    {k:<22s}: {'PASS' if val else 'FAIL'}")
    print()
    print(f"  OVERALL: {v['verdict']}")
    print("=" * 72)


def main():
    print("=" * 72)
    print("MERDIAN Experiment 17 -- BULL Zone Break-Below as Rejection Cascade")
    print(f"  Run at: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 72)

    sb = get_supabase()

    print("\n[1/5] Fetching 5m bars...")
    bars = fetch_bars(sb)
    print(f"      {len(bars):,} bars  "
          f"period {bars['bar_ts'].min()} -> {bars['bar_ts'].max()}")
    print(f"      per-symbol: {bars['symbol'].value_counts().to_dict()}")

    print("\n[2/5] Fetching W BULL_FVG/BULL_OB zones (any status)...")
    zones = fetch_zones(sb)
    print(f"      {len(zones)} zones  "
          f"status: {zones['status'].value_counts().to_dict() if not zones.empty else 'none'}  "
          f"pattern: {zones['pattern_type'].value_counts().to_dict() if not zones.empty else 'none'}")

    print("\n[3/5] Detecting break events (close < zone_low * 0.999, "
          "lifecycle-correct, direction-filtered, first-per-zone)...")
    events = find_break_events(bars, zones)
    print(f"      {len(events)} break events found")

    print("\n[4/5] Computing T+30m / T+60m / T+EOD outcomes...")
    events = attach_outcomes(events, bars)
    if not events.empty:
        events.to_csv(OUT_EVENTS, index=False)
        print(f"      events written to {OUT_EVENTS.name}")

    print("\n[5/5] Building time-of-day baseline...")
    baseline = build_baseline(bars)
    baseline.to_csv(OUT_BASELINE, index=False)
    print(f"      {len(baseline):,} baseline rows written to {OUT_BASELINE.name}")

    v = compute_verdict(events, baseline)
    print_verdict(v, events)


if __name__ == "__main__":
    main()
