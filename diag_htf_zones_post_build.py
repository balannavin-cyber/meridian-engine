"""
diag_htf_zones_post_build.py — diagnose where the OB/FVGs went.

build_ict_htf_zones reported "Detected 39 weekly zones (35 OB/FVG +
4 PDH/PDL)" then verified showed only 1 OB/FVG active per symbol.

This script reads ict_htf_zones grouped by (pattern_type, status) for
both symbols, so we can tell whether:
  (a) Detection wrote 35 OB/FVG zones, breach-recheck flipped them to
      BREACHED legitimately (because price has moved through them since
      they formed) — NO BUG, expected behavior
  (b) Detection found something different than 35; verify count mismatch
      points to a detection-level filter we should investigate

Read-only. ~3 sec.
"""

import os
from datetime import date
from collections import Counter

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
    print(f"  ict_htf_zones audit — what was written, what survived breach")
    print(f"  Date: {today}")
    print("=" * 72)

    for symbol in ("NIFTY", "SENSEX"):
        # Pull every zone written or modified TODAY (created_at OR updated_at
        # within today). This captures zones that were just written by today's
        # build_ict_htf_zones run.
        rows = (
            sb.table("ict_htf_zones")
              .select("id, timeframe, pattern_type, direction, "
                      "zone_high, zone_low, status, valid_from, valid_to, "
                      "created_at, updated_at")
              .eq("symbol", symbol)
              .gte("updated_at", today + "T00:00:00")
              .execute()
              .data
        )

        print(f"\n── {symbol} ── {len(rows)} zones touched today")
        print("-" * 72)

        if not rows:
            print("  (none)")
            continue

        # Group by (pattern_type, timeframe, status)
        groups = Counter()
        active_zones = []
        for r in rows:
            key = (r["pattern_type"], r["timeframe"], r["status"])
            groups[key] += 1
            if r["status"] == "ACTIVE":
                active_zones.append(r)

        print(f"  {'Pattern':<12} {'TF':<3} {'Status':<10} {'N':>3}")
        print(f"  {'-' * 50}")
        for (pt, tf, st), n in sorted(groups.items()):
            tag = ""
            if "BEAR" in pt:
                tag = "  ← BEAR-side"
            print(f"  {pt:<12} {tf:<3} {st:<10} {n:>3}{tag}")

        # Highlight what's ACTIVE for tomorrow's chart
        print(f"\n  Zones ACTIVE for tomorrow: {len(active_zones)}")
        if active_zones:
            for z in active_zones:
                pt = z["pattern_type"]
                tf = z["timeframe"]
                zh = float(z["zone_high"])
                zl = float(z["zone_low"])
                vf = z.get("valid_from", "?")
                print(f"    {tf} {pt:<10} {zl:.0f}-{zh:.0f}  valid_from={vf}")

    # Summary verdict
    print()
    print("=" * 72)
    print("  Interpretation guide:")
    print("    If most OB/FVG zones for today are status=BREACHED and a")
    print("    small number are ACTIVE, breach-recheck did its job —")
    print("    those zones were violated by price action since they formed.")
    print("    NO BUG; this is expected when running the builder against")
    print("    months/weeks of data.")
    print()
    print("    If most OB/FVG zones are status=EXPIRED or missing entirely,")
    print("    then either detection or another filter is broken.")
    print("=" * 72)


if __name__ == "__main__":
    main()
