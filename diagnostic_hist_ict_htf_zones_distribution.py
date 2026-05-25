"""
diagnostic_hist_ict_htf_zones_distribution.py

Quick check: is BEAR_FVG missing from hist_ict_htf_zones (upstream zone bug)
or from build_hist_pattern_signals_5m.py (downstream signal bug)?

Reads hist_ict_htf_zones, prints pattern_type x timeframe distribution.
If BEAR_FVG count is 0 -> upstream zone-builder is broken.
If BEAR_FVG count > 0 -> build_hist_pattern_signals_5m.py is broken
(filtering them out, even though zones_by_date check accepts them).
"""
from __future__ import annotations
import os
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000


def main():
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
    )

    print("=" * 78)
    print("hist_ict_htf_zones distribution — pattern_type x timeframe")
    print("=" * 78)

    # Schema check first
    r = sb.table("hist_ict_htf_zones").select("*").limit(1).execute()
    if not r.data:
        print("[FATAL] hist_ict_htf_zones is empty.")
        return
    cols = list(r.data[0].keys())
    print(f"Columns ({len(cols)}): {cols}")
    print()

    # Pull all rows, count
    counts = Counter()
    by_pt = Counter()
    by_tf = Counter()
    by_sym = Counter()
    offset = 0
    while True:
        rr = (sb.table("hist_ict_htf_zones")
              .select("pattern_type, timeframe, symbol")
              .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = rr.data or []
        for row in batch:
            pt = row.get("pattern_type") or "NULL"
            tf = row.get("timeframe") or "NULL"
            sym = row.get("symbol") or "NULL"
            counts[(pt, tf)] += 1
            by_pt[pt] += 1
            by_tf[tf] += 1
            by_sym[sym] += 1
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            break

    print(f"Total rows: {sum(by_pt.values()):,}")
    print()
    print("By pattern_type:")
    for pt, n in by_pt.most_common():
        flag = ""
        if "BEAR" in pt.upper():
            flag = "  <- BEAR-flavoured"
        if "FVG" in pt.upper():
            flag += "  [FVG]"
        print(f"  {pt:<24} {n:>10}{flag}")
    print()
    print("By timeframe:")
    for tf, n in by_tf.most_common():
        print(f"  {tf:<24} {n:>10}")
    print()
    print("By symbol:")
    for sym, n in by_sym.most_common():
        print(f"  {sym:<24} {n:>10}")
    print()
    print("Cross-tab (pattern_type x timeframe):")
    print(f"{'pattern_type':<14} {'timeframe':<10} {'count':>10}")
    for (pt, tf), n in sorted(counts.items()):
        print(f"{pt:<14} {tf:<10} {n:>10}")
    print()

    bear_fvg_count = by_pt.get("BEAR_FVG", 0)
    bull_fvg_count = by_pt.get("BULL_FVG", 0)
    print("=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"BULL_FVG zones: {bull_fvg_count}")
    print(f"BEAR_FVG zones: {bear_fvg_count}")
    if bear_fvg_count == 0 and bull_fvg_count > 0:
        print()
        print("==> BUG IS UPSTREAM in the zone-builder script (whichever populates")
        print("    hist_ict_htf_zones). build_hist_pattern_signals_5m.py is INNOCENT")
        print("    -- it would emit BEAR_FVG signals if BEAR_FVG zones existed.")
        print()
        print("Next: find the zone-builder script. Likely candidates:")
        print("    Get-ChildItem -Recurse -Filter *.py | Select-String 'hist_ict_htf_zones'")
    elif bear_fvg_count > 0:
        print()
        print("==> BUG IS DOWNSTREAM in build_hist_pattern_signals_5m.py.")
        print("    BEAR_FVG zones exist but signals are not being emitted.")
        print("    Investigate the zone-loop / dispatch logic in that script.")
    else:
        print()
        print("==> Both BULL_FVG and BEAR_FVG zones absent. Different problem.")
    print("=" * 78)


if __name__ == "__main__":
    main()
