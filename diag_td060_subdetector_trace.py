"""
diag_td060_subdetector_trace.py — call sub-detectors directly.

The previous repro returned 0 patterns from BOTH invocation shapes on a
day where Exp 15 found 11 OBs. That eliminates invocation-shape AND
write-path; the issue is somewhere INSIDE detect() or in the inputs.

This script bypasses detect() entirely and calls the underlying
detect_obs() / detect_fvg() / detect_judas() functions directly. They're
pure functions — given bars, they return candidates regardless of HTF
zones, atm_iv, time-zone, or any other context.

If sub-detectors return the expected ~11 OBs on this day's bars,
the problem is in detect()'s filtering (check_from, power-hour gate,
seq-feature short-circuit, or the dedup `seen` set).

If sub-detectors also return 0, the problem is in the bars themselves —
some shape difference between Exp 15's bars and what we're loading now.

Read-only. ~5 sec. Same Feb 01 / NIFTY test.
"""

import os
import sys
from datetime import datetime, date, timedelta, timezone
from collections import Counter

from dotenv import load_dotenv
from supabase import create_client

from detect_ict_patterns import (
    Bar, ICTDetector,
    detect_obs, detect_fvg, detect_judas,
    OB_MIN_MOVE_PCT, FVG_MIN_PCT, pct,
)

PAGE_SIZE = 1_000


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


def main():
    print("=" * 72)
    print("  TD-060 sub-detector trace — bypass detect() filters")
    print("=" * 72)

    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    # Use Feb 01 / NIFTY (top OB day from Exp 15 dump)
    test_td = "2026-02-01"
    test_sym = "NIFTY"

    inst_rows = (
        sb.table("instruments")
          .select("id")
          .eq("symbol", test_sym)
          .execute().data
    )
    inst_id = inst_rows[0]["id"]

    raw = fetch_paginated(
        sb, "hist_spot_bars_1m",
        [("eq", "instrument_id", inst_id),
         ("eq", "trade_date", test_td),
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

    print(f"\n[1] Loaded {len(bars)} bars for {test_sym} {test_td}")
    print(f"    First: {bars[0].bar_ts.isoformat()}  O={bars[0].open}  C={bars[0].close}")
    print(f"    Last:  {bars[-1].bar_ts.isoformat()}  O={bars[-1].open}  C={bars[-1].close}")
    print(f"    Day range: high={max(b.high for b in bars):.2f}  "
          f"low={min(b.low for b in bars):.2f}")

    # Prior session H/L
    prior_high = prior_low = None
    for days_back in range(1, 6):
        d = date.fromisoformat(test_td) - timedelta(days=days_back)
        rows = (
            sb.table("hist_spot_bars_1m")
              .select("high, low")
              .eq("instrument_id", inst_id)
              .eq("trade_date", str(d))
              .eq("is_pre_market", False)
              .execute().data
        )
        if rows:
            prior_high = max(float(r["high"]) for r in rows)
            prior_low = min(float(r["low"]) for r in rows)
            break
    print(f"    Prior H/L: {prior_high} / {prior_low}")

    # ── Sub-detectors ─────────────────────────────────────────────────
    print("\n[2] Sub-detector results (full bars, no filters)")
    print("-" * 72)

    ob_results = detect_obs(bars, prior_high, prior_low)
    print(f"    detect_obs:   {len(ob_results)} candidates")
    pt_count = Counter(pt for _, pt in ob_results)
    print(f"      by type:    {dict(pt_count)}")
    if ob_results[:5]:
        print(f"      first 5 (idx, type):")
        for idx, pt in ob_results[:5]:
            b = bars[idx]
            print(f"        idx={idx:>3}  {pt}  bar_ts={b.bar_ts.isoformat()}  "
                  f"OHLC={b.open:.2f}/{b.high:.2f}/{b.low:.2f}/{b.close:.2f}")

    fvg_results = detect_fvg(bars)
    print(f"\n    detect_fvg:   {len(fvg_results)} candidates")
    pt_count = Counter(pt for _, pt in fvg_results)
    print(f"      by type:    {dict(pt_count)}")
    if fvg_results[:5]:
        print(f"      first 5:")
        for idx, pt in fvg_results[:5]:
            print(f"        idx={idx:>3}  {pt}  bar_ts={bars[idx].bar_ts.isoformat()}")

    judas_results = detect_judas(bars)
    print(f"\n    detect_judas: {len(judas_results)} candidates")

    # ── ICTDetector.detect() with full session ────────────────────────
    print("\n[3] ICTDetector.detect() — full session, no atm_iv, no htf_zones")
    print("-" * 72)
    detector = ICTDetector(symbol=test_sym)
    patterns = detector.detect(
        bars=bars,
        atm_iv=None,
        htf_zones=[],
        prior_high=prior_high,
        prior_low=prior_low,
    )
    print(f"    detect() returned: {len(patterns)} patterns")
    if patterns:
        pt_count = Counter(p.pattern_type for p in patterns)
        print(f"      by pattern_type: {dict(pt_count)}")
        for p in patterns[:5]:
            print(f"        {p.pattern_type:<10} idx-via-bar_ts={p.bar_ts.isoformat()}  "
                  f"tier={p.ict_tier}  size={p.ict_size_mult}x")

    # ── Verbose detect() filter trace ────────────────────────────────
    print("\n[4] detect() filter analysis")
    print("-" * 72)
    n = len(bars)
    check_from = max(0, n - 10)
    print(f"    n={n}, check_from={check_from} "
          f"(only candidates with idx >= {check_from} survive)")
    print(f"    OB candidates at idx >= {check_from}:")
    surviving_ob = [(i, pt) for i, pt in ob_results if i >= check_from]
    print(f"      count: {len(surviving_ob)}")
    for i, pt in surviving_ob[:10]:
        print(f"        idx={i}  {pt}  bar_ts={bars[i].bar_ts.isoformat()}")

    print(f"\n    FVG candidates at idx >= {check_from}:")
    surviving_fvg = [(i, pt) for i, pt in fvg_results if i >= check_from]
    print(f"      count: {len(surviving_fvg)}")

    # ── Verdict ───────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  VERDICT")
    print("=" * 72)
    if len(ob_results) > 0 and len(patterns) == 0:
        print(f"  Sub-detectors find {len(ob_results)} OBs and {len(fvg_results)} FVGs.")
        print(f"  detect() returns 0.")
        print(f"  → check_from filter eliminates ALL of them.")
        print(f"    Specifically: {len(ob_results)} OBs detected, 0 with idx >= {check_from}.")
        print(f"    This is the bug. detect() should filter by IMPULSE bar")
        print(f"    proximity, not OB-CANDLE bar proximity.")
    elif len(ob_results) > 0 and len(patterns) > 0:
        ptn_pt = Counter(p.pattern_type for p in patterns)
        print(f"  Sub-detectors: {len(ob_results)} OBs, {len(fvg_results)} FVGs")
        print(f"  detect():     {dict(ptn_pt)}")
        print(f"  → some patterns survive. Investigate which are dropped and why.")
    elif len(ob_results) == 0 and len(fvg_results) == 0:
        print(f"  Sub-detectors return ZERO. Bars must differ from Exp 15 cohort.")
        print(f"  Investigate hist_spot_bars_1m schema or column drift since Exp 15 ran.")
    else:
        print(f"  Anomalous result. Inspect output above manually.")
    print("=" * 72)


if __name__ == "__main__":
    main()
