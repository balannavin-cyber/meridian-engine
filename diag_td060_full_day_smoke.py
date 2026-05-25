"""
diag_td060_full_day_smoke.py — full-day cycle simulator for F4 patch.

Single-cycle smoke (last 30 bars of session) returned 0 patterns on
Feb 01 / NIFTY because the day's pattern formation clustered around noon,
not in the closing auction. That's a coverage gap in the smoke, not the patch.

This script simulates what the runner does across the FULL day:
  - Every 5 minutes from 09:20 IST to 15:25 IST (matches runner cadence)
  - At each cycle, pass detect() the bars-so-far sliced to last 30
  - Aggregate patterns across all cycles, dedup by (pattern_type, bar_ts)
  - Compare to sub-detector ground truth (14 OBs + 13 FVGs)

Read-only. ~5 sec runtime.
"""

import os
import sys
from datetime import datetime, date, timedelta, timezone
from collections import Counter
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

from detect_ict_patterns import ICTDetector, Bar, detect_obs, detect_fvg


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


def main():
    print("=" * 72)
    print("  TD-060 F4 patch full-day smoke")
    print("  Simulates runner cadence (5 min cycles) for Feb 01 / NIFTY")
    print("=" * 72)

    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    test_td  = "2026-02-01"
    test_sym = "NIFTY"

    inst_id = (
        sb.table("instruments").select("id").eq("symbol", test_sym)
          .execute().data[0]["id"]
    )

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
    print(f"\n  Loaded {len(bars)} session bars")

    # Prior session H/L (skip-pre-market rolling lookup)
    prior_high = prior_low = None
    for days_back in range(1, 6):
        d = date.fromisoformat(test_td) - timedelta(days=days_back)
        prev = (
            sb.table("hist_spot_bars_1m")
              .select("high, low")
              .eq("instrument_id", inst_id)
              .eq("trade_date", str(d))
              .eq("is_pre_market", False)
              .execute().data
        )
        if prev:
            prior_high = max(float(r["high"]) for r in prev)
            prior_low  = min(float(r["low"])  for r in prev)
            break

    detector = ICTDetector(symbol=test_sym)

    # ── Ground truth from sub-detectors ──────────────────────────────
    gt_obs = detect_obs(bars, prior_high, prior_low)
    gt_fvg = detect_fvg(bars)
    gt_ob_keys = set((bars[i].bar_ts, pt) for i, pt in gt_obs)
    gt_fvg_keys = set((bars[i].bar_ts, pt) for i, pt in gt_fvg)
    print(f"  Ground truth (sub-detectors): "
          f"{len(gt_obs)} OBs, {len(gt_fvg)} FVGs")

    # ── Simulate runner cadence: 5 min cycles ────────────────────────
    # Runner runs at :15, :20, :25, ... IST. Match that.
    bars_sorted = sorted(bars, key=lambda b: b.bar_ts)
    cycles_run = 0
    aggregate_seen = set()  # set of (pattern_type, bar_ts)

    # First cycle has data starting from 09:15. Each subsequent cycle
    # adds ~5 bars. Step through cycle endpoints in 5-bar increments
    # (= 5 minutes of 1-min bars).
    for cycle_end_idx in range(10, len(bars_sorted) + 1, 5):
        bars_so_far = bars_sorted[:cycle_end_idx]
        # F4 patch behaviour: pass last 30 bars only
        patterns = detector.detect(
            bars=bars_so_far[-30:],
            atm_iv=None,
            htf_zones=[],
            prior_high=prior_high,
            prior_low=prior_low,
        )
        cycles_run += 1
        for p in patterns:
            aggregate_seen.add((p.pattern_type, p.bar_ts))

    print(f"\n  Simulated {cycles_run} 5-min cycles")
    print(f"  Aggregate unique patterns across all cycles: {len(aggregate_seen)}")

    # ── Coverage analysis ────────────────────────────────────────────
    seen_obs  = set((ts, pt) for pt, ts in aggregate_seen
                    if pt in ("BULL_OB", "BEAR_OB"))
    seen_fvgs = set((ts, pt) for pt, ts in aggregate_seen
                    if pt in ("BULL_FVG", "BEAR_FVG"))

    ob_coverage  = len(seen_obs  & gt_ob_keys)
    fvg_coverage = len(seen_fvgs & gt_fvg_keys)

    print(f"\n  OB coverage:  {ob_coverage} / {len(gt_obs)} "
          f"({100*ob_coverage/max(len(gt_obs),1):.0f}%)")
    print(f"  FVG coverage: {fvg_coverage} / {len(gt_fvg)} "
          f"({100*fvg_coverage/max(len(gt_fvg),1):.0f}%)")

    pt_count = Counter(pt for pt, ts in aggregate_seen)
    print(f"\n  Patterns by type: {dict(pt_count)}")

    missing_obs  = gt_ob_keys  - seen_obs
    missing_fvgs = gt_fvg_keys - seen_fvgs
    if missing_obs:
        print(f"\n  Missed OBs ({len(missing_obs)}):")
        for ts, pt in sorted(missing_obs):
            print(f"    {pt:<10} {ts.isoformat()}")
    if missing_fvgs:
        print(f"\n  Missed FVGs ({len(missing_fvgs)}):")
        for ts, pt in sorted(missing_fvgs):
            print(f"    {pt:<10} {ts.isoformat()}")

    # ── Verdict ──────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  VERDICT")
    print("=" * 72)
    total_gt = len(gt_obs) + len(gt_fvg)
    total_seen = ob_coverage + fvg_coverage
    pct = 100 * total_seen / max(total_gt, 1)
    print(f"  Coverage: {total_seen} / {total_gt} ({pct:.0f}%)")
    if pct >= 80:
        print(f"  → F4 patch works. >80% pattern coverage across simulated runner cycles.")
        print(f"    Rename + AWS deploy approved.")
    elif pct >= 50:
        print(f"  → F4 patch partially works. {pct:.0f}% coverage.")
        print(f"    Patterns at far-from-end-of-day still missed. Consider")
        print(f"    increasing window from 30 to 60 bars before deploy.")
    else:
        print(f"  → F4 patch insufficient. {pct:.0f}% coverage.")
        print(f"    Investigate further before deploy.")
    print("=" * 72)


if __name__ == "__main__":
    main()
