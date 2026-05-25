"""
diag_pine_zones_audit.py — pre-Pine-regeneration audit.

The existing Pine script (2026-04-30) has zero BEAR_OB and BEAR_FVG zones
across both NIFTY and SENSEX. Two possible reasons:
  (a) ict_htf_zones legitimately has no BEAR-side zones for the current
      proximity window (within 5% of spot)
  (b) the generator filters them out, or they exist far from spot in T3

This audit shows what's actually in ict_htf_zones for NIFTY and SENSEX
right now, by direction and proximity tier. After this run, we know
whether the issue is data availability or generator logic.

Read-only. ~5 sec.
"""

import os
from datetime import date, datetime, timezone
from collections import Counter, defaultdict

from dotenv import load_dotenv
from supabase import create_client


def main():
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    today = date.today().isoformat()

    print("=" * 72)
    print(f"  ict_htf_zones audit (today={today})")
    print("=" * 72)

    for symbol in ("NIFTY", "SENSEX"):
        # Pull active zones valid for today
        rows = (
            sb.table("ict_htf_zones")
              .select("id, symbol, timeframe, pattern_type, direction, "
                      "zone_high, zone_low, status, valid_from, valid_to, "
                      "created_at")
              .eq("symbol", symbol)
              .eq("status", "ACTIVE")
              .lte("valid_from", today)
              .gte("valid_to", today)
              .order("created_at", desc=True)
              .execute()
              .data
        )

        # Get current spot from market_state_snapshots
        ms = (
            sb.table("market_state_snapshots")
              .select("spot")
              .eq("symbol", symbol)
              .order("ts", desc=True)
              .limit(1)
              .execute()
              .data
        )
        spot = float(ms[0]["spot"]) if ms else None

        print(f"\n── {symbol} (spot={spot}) ── {len(rows)} active zones")
        print("-" * 72)

        if not rows:
            print("  (no zones)")
            continue

        # Classify each zone by proximity tier
        # T1: D zones always + W within 2% of spot
        # T2: W zones 2-5% from spot
        # T3: W zones >5% (ghost, no label in Pine)
        by_pt_tf = defaultdict(list)
        for r in rows:
            pt = r["pattern_type"]
            tf = r["timeframe"]
            zh = float(r["zone_high"])
            zl = float(r["zone_low"])
            mid = (zh + zl) / 2
            if spot:
                dist_pct = abs(mid - spot) / spot * 100
            else:
                dist_pct = None

            if tf == "D":
                tier = "T1"
            elif tf == "W":
                if dist_pct is None:
                    tier = "?"
                elif dist_pct <= 2:
                    tier = "T1"
                elif dist_pct <= 5:
                    tier = "T2"
                else:
                    tier = "T3"
            else:  # H
                tier = "T1"

            by_pt_tf[(pt, tf, tier)].append({
                "zh": zh, "zl": zl, "dist_pct": dist_pct,
                "valid_from": r["valid_from"],
                "created_at": r["created_at"][:10] if r["created_at"] else "",
            })

        # Print summary by pattern_type
        print(f"  {'Pattern':<12} {'TF':<3} {'Tier':<5} {'N':>3} "
              f"{'Sample (zone_low-zone_high, dist%)':<50}")
        print(f"  {'-' * 75}")
        for (pt, tf, tier), zs in sorted(by_pt_tf.items()):
            sample = zs[0]
            sample_str = f"{sample['zl']:.0f}-{sample['zh']:.0f}"
            if sample["dist_pct"] is not None:
                sample_str += f" ({sample['dist_pct']:.1f}%)"
            print(f"  {pt:<12} {tf:<3} {tier:<5} {len(zs):>3} {sample_str:<50}")

        # Highlight BEAR-side zones specifically
        bear_zones = [
            (pt, tf, tier, zs) for (pt, tf, tier), zs in by_pt_tf.items()
            if "BEAR" in pt
        ]
        bear_total = sum(len(zs) for _, _, _, zs in bear_zones)
        print(f"\n  BEAR-side zones (BULL_OB / BEAR_OB / BEAR_FVG): {bear_total}")
        if bear_zones:
            print(f"    by tier:")
            for pt, tf, tier, zs in bear_zones:
                for z in zs[:3]:
                    print(f"      {pt:<10} {tf} {tier} "
                          f"{z['zl']:.2f}-{z['zh']:.2f} "
                          f"({z['dist_pct']:.2f}% from spot) "
                          f"valid={z['valid_from']}")

    print()
    print("=" * 72)
    print("  Done.")
    print("=" * 72)


if __name__ == "__main__":
    main()
