"""
diag_td060_local_repro.py — option B from Session 17 fork.

Local reproduction of the runner's detect() call against a historical
session where Exp 15 found OBs. Discriminates three hypotheses:

  H_DETECT  Runner-shape detect() returns 0 OBs even when Exp 15-shape does.
            Invocation difference is the bug. Fix is in detect() or
            in how the runner calls it.

  H_WRITE   Both shapes return identical OBs.
            detect() works fine; write_new_zones() is silently failing.
            Need live instrumentation (option A) to confirm.

  H_DATA    Neither shape returns the OBs Exp 15 found.
            Live/recent data differs from the year-long Exp 15 cohort
            in some way (column population, schema drift, etc.).
            Investigate data layer.

Reads the most recent Exp 15 trade dump, finds dates with OBs, and
runs the runner's detect() path against that date's bars. Compares
against Exp 15's invocation shape on the same bars.

Read-only. ~10 sec runtime. No DB writes.

Usage:
    python diag_td060_local_repro.py
    python diag_td060_local_repro.py exp15_trades_20260503_1342.csv
"""

import os
import sys
import csv
import glob
from datetime import datetime, date, timedelta, timezone
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

# Import the production code paths we're testing
from detect_ict_patterns import ICTDetector, Bar, HTFZone


PAGE_SIZE = 1_000
IST = ZoneInfo("Asia/Kolkata")


def fetch_paginated(sb, table, filters, select, order="bar_ts"):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select).order(order).range(
            offset, offset + PAGE_SIZE - 1)
        for method, *args in filters:
            q = getattr(q, method)(*args)
        rows = q.execute().data
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def find_latest_dump():
    candidates = sorted(glob.glob("exp15_trades_*.csv"))
    return candidates[-1] if candidates else None


def find_known_ob_date(csv_path):
    """Find the most recent (date, symbol) pair from Exp 15 dump that had
    BULL_OB or BEAR_OB firings. Returns list of (date_str, symbol, count) tuples
    sorted by OB count descending — pick the highest-yield day to test."""
    by_day_sym = defaultdict(lambda: Counter())
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pt = row.get("pattern_type")
            if pt in ("BULL_OB", "BEAR_OB"):
                key = (row.get("td"), row.get("symbol"))
                by_day_sym[key][pt] += 1
    ranked = sorted(
        by_day_sym.items(),
        key=lambda x: -(x[1]["BULL_OB"] + x[1]["BEAR_OB"]),
    )
    return ranked[:5]  # top 5 highest-OB days


def load_session_bars(sb, inst_id, trade_date_str):
    raw = fetch_paginated(
        sb, "hist_spot_bars_1m",
        [("eq", "instrument_id", inst_id),
         ("eq", "trade_date", trade_date_str),
         ("eq", "is_pre_market", False)],
        "bar_ts, trade_date, open, high, low, close",
    )
    bars = [
        Bar(
            bar_ts=datetime.fromisoformat(r["bar_ts"]),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            trade_date=date.fromisoformat(r["trade_date"]),
        )
        for r in raw
    ]
    return bars


def load_prior_hl(sb, inst_id, trade_date_str):
    td = date.fromisoformat(trade_date_str)
    for days_back in range(1, 6):
        d = td - timedelta(days=days_back)
        rows = (
            sb.table("hist_spot_bars_1m")
              .select("high, low")
              .eq("instrument_id", inst_id)
              .eq("trade_date", str(d))
              .eq("is_pre_market", False)
              .execute().data
        )
        if rows:
            return (max(float(r["high"]) for r in rows),
                    min(float(r["low"]) for r in rows))
    return None, None


def load_htf_zones(sb, symbol, trade_date_str):
    rows = (
        sb.table("ict_htf_zones")
          .select("id, symbol, timeframe, pattern_type, direction, "
                  "zone_high, zone_low, status")
          .eq("symbol", symbol)
          .eq("status", "ACTIVE")
          .lte("valid_from", trade_date_str)
          .gte("valid_to", trade_date_str)
          .execute().data
    )
    return [
        HTFZone(
            id=r["id"], symbol=r["symbol"], timeframe=r["timeframe"],
            pattern_type=r["pattern_type"], direction=int(r["direction"]),
            zone_high=float(r["zone_high"]), zone_low=float(r["zone_low"]),
            status=r["status"],
        )
        for r in rows
    ]


def runner_shape_detect(detector, bars, atm_iv, htf_zones, prior_high, prior_low):
    """Replicates the runner's detect() call: pass full session bars."""
    return detector.detect(
        bars=bars,
        atm_iv=atm_iv,
        htf_zones=htf_zones,
        prior_high=prior_high,
        prior_low=prior_low,
    )


def exp15_shape_detect(detector, bars, atm_iv, htf_zones, prior_high, prior_low):
    """Replicates Exp 15's invocation: incremental window per pat_idx.
    Aggregates patterns across all incremental calls, dedups by (type, bar_ts)."""
    seen_keys = set()
    all_patterns = []
    POWER_HOUR = (15, 0)  # IST

    for pat_idx in range(10, len(bars)):
        bar = bars[pat_idx]
        # Mirror exp15's power-hour break (uses bar.bar_ts.time() converted)
        # Local-time conversion: bar_ts is UTC; IST is +5:30
        try:
            ist_ts = bar.bar_ts.astimezone(IST)
            if (ist_ts.hour, ist_ts.minute) >= POWER_HOUR:
                break
        except Exception:
            pass

        start = max(0, pat_idx - 10)
        window = bars[start:pat_idx + 1]
        patterns = detector.detect(
            bars=window,
            atm_iv=atm_iv,
            htf_zones=htf_zones,
            prior_high=prior_high,
            prior_low=prior_low,
        )
        for p in patterns:
            key = (p.pattern_type, p.bar_ts)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            all_patterns.append(p)
    return all_patterns


def summarise(patterns, label):
    pt_count = Counter(p.pattern_type for p in patterns)
    tier_count = Counter(p.ict_tier for p in patterns)
    print(f"\n  {label}: {len(patterns)} patterns")
    print(f"    by pattern_type: {dict(pt_count)}")
    print(f"    by tier:         {dict(tier_count)}")
    if patterns:
        print(f"    sample (first 3):")
        for p in patterns[:3]:
            print(f"      {p.pattern_type:<10} {p.ict_tier:<6} "
                  f"bar_ts={p.bar_ts.isoformat()} "
                  f"zone={p.zone_low:.0f}-{p.zone_high:.0f}")


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else find_latest_dump()
    if not csv_path or not os.path.exists(csv_path):
        print(f"ERROR: Exp 15 CSV not found ({csv_path})")
        print("Pass path as arg, or place in CWD.")
        sys.exit(1)

    print("=" * 72)
    print("  TD-060 local reproduction — invocation-shape vs write-path")
    print("  Source CSV:", csv_path)
    print("=" * 72)

    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    # ── Find candidate dates ──────────────────────────────────────────
    candidates = find_known_ob_date(csv_path)
    if not candidates:
        print("\nNo BULL_OB / BEAR_OB rows in Exp 15 dump. Cannot reproduce.")
        sys.exit(1)

    print("\n[Top OB-firing day-symbol pairs from Exp 15 dump:]")
    for (td_str, sym), c in candidates:
        print(f"  {td_str}  {sym:<7}  BULL_OB={c['BULL_OB']}  BEAR_OB={c['BEAR_OB']}")

    # Pick the top one
    (test_td, test_sym), _ = candidates[0]
    print(f"\nReproducing on: {test_td} / {test_sym}")
    print("-" * 72)

    # ── Get instrument_id ─────────────────────────────────────────────
    inst_rows = (
        sb.table("instruments")
          .select("id")
          .eq("symbol", test_sym)
          .execute().data
    )
    inst_id = inst_rows[0]["id"]

    # ── Load data ─────────────────────────────────────────────────────
    bars = load_session_bars(sb, inst_id, test_td)
    print(f"  Loaded {len(bars)} session bars for {test_sym} {test_td}")

    prior_high, prior_low = load_prior_hl(sb, inst_id, test_td)
    print(f"  prior_high={prior_high}, prior_low={prior_low}")

    htf_zones = load_htf_zones(sb, test_sym, test_td)
    print(f"  Loaded {len(htf_zones)} active HTF zones")
    htf_by_pt = Counter(z.pattern_type for z in htf_zones)
    print(f"    HTF by pattern_type: {dict(htf_by_pt)}")

    detector = ICTDetector(symbol=test_sym)

    # ── Run both invocation shapes ────────────────────────────────────
    print("\n" + "─" * 72)
    print("  RUNNER-shape detect() — full session bars passed in")
    print("─" * 72)
    runner_patterns = runner_shape_detect(
        detector, bars, None, htf_zones, prior_high, prior_low
    )
    summarise(runner_patterns, "Runner-shape result")

    print("\n" + "─" * 72)
    print("  EXP15-shape detect() — incremental window per pat_idx")
    print("─" * 72)
    exp15_patterns = exp15_shape_detect(
        detector, bars, None, htf_zones, prior_high, prior_low
    )
    summarise(exp15_patterns, "Exp15-shape result")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  VERDICT")
    print("=" * 72)
    runner_obs = sum(
        1 for p in runner_patterns
        if p.pattern_type in ("BULL_OB", "BEAR_OB")
    )
    exp15_obs = sum(
        1 for p in exp15_patterns
        if p.pattern_type in ("BULL_OB", "BEAR_OB")
    )
    expected_obs = candidates[0][1]["BULL_OB"] + candidates[0][1]["BEAR_OB"]
    print(f"  Exp 15 dump expected OBs on this day: {expected_obs}")
    print(f"  Runner-shape returned OBs:            {runner_obs}")
    print(f"  Exp15-shape returned OBs:             {exp15_obs}")
    print()
    if runner_obs == 0 and exp15_obs > 0:
        print("  → H_DETECT confirmed.")
        print("    detect() returns OBs only when called incrementally.")
        print("    The runner's full-session invocation suppresses them.")
        print("    Likely culprit: check_from = max(0, len(bars) - 10) inside")
        print("    detect() filters out OBs whose CANDLE index sits before")
        print("    the last 10 bars, even if the IMPULSE bar is recent.")
        print("    Fix: change runner's invocation to incremental, OR change")
        print("    detect()'s filter to use impulse-bar idx not candle-bar idx.")
    elif runner_obs > 0 and exp15_obs > 0:
        print("  → H_WRITE likely. detect() works in both shapes.")
        print("    Need write-path instrumentation (option A) to find the")
        print("    actual write failure. Deploy patch_td060_runner_instrumentation.py.")
    elif runner_obs == 0 and exp15_obs == 0:
        print("  → H_DATA. Neither shape returns the OBs Exp 15 saw.")
        print("    Local data layer differs from Exp 15 cohort. Investigate")
        print("    bar coverage, prior_high availability, htf_zone matching.")
    else:
        print("  → Anomalous. Runner returns more OBs than Exp 15-shape.")
        print("    Implausible — investigate test correctness.")
    print("=" * 72)


if __name__ == "__main__":
    main()
