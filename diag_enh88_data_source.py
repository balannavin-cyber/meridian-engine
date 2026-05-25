"""
diag_enh88_data_source.py — pre-rename verification for ENH-88.

Run BEFORE renaming build_trade_signal_local_PATCHED.py to canonical.
Determines whether the helper's chosen data source (signal_snapshots
filtered by ict_pattern='BULL_OB' AND trade_allowed=True) actually
contains historical rows. If not, we pivot the helper before deploy.

Three questions answered, one printout. Read-only. Runtime ~3 seconds.
"""

import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from supabase import create_client


def main():
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    print("=" * 64)
    print("  ENH-88 data-source verification")
    print("=" * 64)

    # Q1 — is signal_snapshots being written at all?
    last = (
        sb.table("signal_snapshots")
          .select("ts")
          .order("ts", desc=True)
          .limit(1)
          .execute()
          .data
    )
    print(f"\n[Q1] Last signal_snapshots ts: "
          f"{last[0]['ts'] if last else '(none)'}")

    # Q2 — distribution of ict_pattern × trade_allowed in last 14 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    rows = []
    offset = 0
    while True:
        batch = (
            sb.table("signal_snapshots")
              .select("ict_pattern, trade_allowed")
              .gte("ts", cutoff)
              .range(offset, offset + 999)
              .execute()
              .data
        )
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    print(f"\n[Q2] signal_snapshots last 14d total rows: {len(rows)}")
    if rows:
        c = Counter(
            (r.get("ict_pattern"), r.get("trade_allowed")) for r in rows
        )
        print("     ict_pattern x trade_allowed counts:")
        for (pat, ta), n in sorted(c.items(), key=lambda x: -x[1]):
            print(f"       {str(pat):<12} trade_allowed={ta!s:<5} {n:>5}")

    # Q3 — BULL_OB rows ever in signal_snapshots (any trade_allowed)
    bull_ob_ever = (
        sb.table("signal_snapshots")
          .select("ts, symbol, trade_allowed, action")
          .eq("ict_pattern", "BULL_OB")
          .order("ts", desc=True)
          .limit(10)
          .execute()
          .data
    )
    print(f"\n[Q3] signal_snapshots BULL_OB rows ever (sample of 10):")
    print(f"     count returned: {len(bull_ob_ever)}")
    for r in bull_ob_ever:
        print(f"       {r['ts']}  {r['symbol']:<7} "
              f"trade_allowed={r['trade_allowed']!s:<5} action={r['action']}")

    # Q4 — ict_zones table contents (the orphan?)
    ict_zones = (
        sb.table("ict_zones")
          .select("pattern_type, status")
          .limit(2000)
          .execute()
          .data
    )
    print(f"\n[Q4] ict_zones total rows fetched: {len(ict_zones)}")
    if ict_zones:
        c = Counter(
            (r.get("pattern_type"), r.get("status")) for r in ict_zones
        )
        print("     pattern_type x status counts:")
        for (pat, st), n in sorted(c.items(), key=lambda x: -x[1]):
            print(f"       {str(pat):<14} status={str(st):<10} {n:>5}")

    # Q5 — ict_htf_zones BULL_OB by timeframe (the canonical fallback?)
    htf_bull_ob = (
        sb.table("ict_htf_zones")
          .select("timeframe, status, valid_from, valid_to")
          .eq("pattern_type", "BULL_OB")
          .order("created_at", desc=True)
          .limit(500)
          .execute()
          .data
    )
    print(f"\n[Q5] ict_htf_zones BULL_OB rows fetched: {len(htf_bull_ob)}")
    if htf_bull_ob:
        c = Counter(
            (r.get("timeframe"), r.get("status")) for r in htf_bull_ob
        )
        print("     timeframe x status counts:")
        for (tf, st), n in sorted(c.items(), key=lambda x: -x[1]):
            print(f"       tf={str(tf):<3} status={str(st):<10} {n:>5}")
        latest = htf_bull_ob[0]
        print(f"     most recent BULL_OB: tf={latest.get('timeframe')} "
              f"valid_from={latest.get('valid_from')} "
              f"valid_to={latest.get('valid_to')} "
              f"status={latest.get('status')}")

    # Verdict
    print("\n" + "=" * 64)
    print("  VERDICT")
    print("=" * 64)
    n_bull_ob_ss = sum(
        1 for r in rows if r.get("ict_pattern") == "BULL_OB"
    )
    n_bull_ob_ss_ta = sum(
        1 for r in rows
        if r.get("ict_pattern") == "BULL_OB" and r.get("trade_allowed")
    )
    n_ictz_bullob = sum(
        1 for r in ict_zones if r.get("pattern_type") == "BULL_OB"
    )
    n_htfz_bullob = len(htf_bull_ob)

    print(f"  BULL_OB in signal_snapshots last 14d:        {n_bull_ob_ss:>5}")
    print(f"  ... with trade_allowed=True:                 {n_bull_ob_ss_ta:>5}")
    print(f"  BULL_OB in ict_zones (any time):             {n_ictz_bullob:>5}")
    print(f"  BULL_OB in ict_htf_zones (recent 500):       {n_htfz_bullob:>5}")
    print()
    if n_bull_ob_ss_ta > 0:
        print("  → signal_snapshots IS the right source. ENH-88 helper")
        print("    works as designed. Proceed with rename.")
    elif n_bull_ob_ss > 0:
        print("  → signal_snapshots HAS BULL_OB rows but trade_allowed=True")
        print("    filter is too strict. Recommend: relax helper to drop")
        print("    the trade_allowed filter (count detections, not executions).")
    elif n_ictz_bullob > 0:
        print("  → signal_snapshots has NO BULL_OB rows but ict_zones DOES.")
        print("    ENH-37 enrichment may be broken. Investigate before rename.")
        print("    OR: pivot helper to query ict_zones directly.")
    elif n_htfz_bullob > 0:
        print("  → signal_snapshots has NO BULL_OB rows. ict_zones has none")
        print("    either. ict_htf_zones IS the canonical source per TD-047.")
        print("    Pivot helper to query ict_htf_zones (timeframe='H' for")
        print("    1H BULL_OB, matching Section 18 evidence cohort).")
    else:
        print("  → No BULL_OB found anywhere. Either ICT runner isn't")
        print("    writing, or column names differ. Investigate before deploy.")
    print("=" * 64)


if __name__ == "__main__":
    main()
