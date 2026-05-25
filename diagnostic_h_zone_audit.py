"""
diagnostic_h_zone_audit.py

DIAGNOSTIC — H zone existence in ict_htf_zones

Question:
    Are H-timeframe zones being written to ict_htf_zones at all? When was the
    last one created? How many ACTIVE / BREACHED / EXPIRED right now?

Why:
    Session 13 explicitly added `--timeframe H` to run_ict_htf_zones_daily.bat.
    ENH-84 added a dashboard refresh button that calls --timeframe H.
    ADR-003 Phase 1 v2 found ZERO H zones ACTIVE despite this. Need to know
    whether the detector writes anything at all, or whether everything gets
    expired/breached on next run.

Output:
    - Summary table: timeframe x status counts
    - H-specific listing: every H zone ever, sorted by created_at desc
    - Most recent created_at per timeframe
    - Days-since-last-H-zone metric

Author: Session 15 batch v2.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, date

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_all_zones(sb) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        r = (sb.table("ict_htf_zones")
             .select("*")
             .order("created_at", desc=True)
             .range(offset, offset + PAGE_SIZE - 1)
             .execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 50_000:
            break
    return rows


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def main():
    sb = get_client()
    print("=" * 78)
    print("DIAGNOSTIC — H zone existence audit")
    print("=" * 78)

    rows = fetch_all_zones(sb)
    print(f"Total ict_htf_zones rows (all time, all status): {len(rows)}")
    print()

    # === Summary: timeframe x status ===
    grid = defaultdict(int)
    timeframes = set()
    statuses = set()
    last_created_per_tf = {}
    for r in rows:
        tf = (r.get("timeframe") or "?").upper()
        st = (r.get("status") or "?").upper()
        grid[(tf, st)] += 1
        timeframes.add(tf)
        statuses.add(st)
        ca = parse_dt(r.get("created_at"))
        if ca is not None:
            prev = last_created_per_tf.get(tf)
            if prev is None or ca > prev:
                last_created_per_tf[tf] = ca

    print("Counts by timeframe x status:")
    statuses_sorted = sorted(statuses)
    print(f"{'TF':<6}", end="")
    for s in statuses_sorted:
        print(f"{s:>12}", end="")
    print(f"{'TOTAL':>10}")
    for tf in sorted(timeframes):
        print(f"{tf:<6}", end="")
        total = 0
        for s in statuses_sorted:
            n = grid.get((tf, s), 0)
            total += n
            print(f"{n:>12}", end="")
        print(f"{total:>10}")
    print()

    # === Most recent created_at per timeframe ===
    print("Most recent created_at per timeframe:")
    now = datetime.now(last_created_per_tf.get(next(iter(last_created_per_tf), None), datetime.now()).tzinfo if last_created_per_tf else None)
    if last_created_per_tf:
        try:
            now = max(last_created_per_tf.values())  # use latest as 'reference now'
        except ValueError:
            pass
    for tf in sorted(last_created_per_tf):
        ts = last_created_per_tf[tf]
        # days_since uses the latest known created_at as 'now' to avoid tz issues
        delta_days = (now - ts).total_seconds() / 86400
        flag = " <- STALE" if delta_days > 7 else ""
        print(f"  {tf:<6} last created_at = {ts.isoformat()}  ({delta_days:+.1f} days vs latest in table){flag}")
    print()

    # === H-specific listing ===
    h_rows = [r for r in rows if (r.get("timeframe") or "").upper() == "H"]
    print(f"All H zones ever written: {len(h_rows)}")
    if h_rows:
        print(f"{'idx':<5} {'symbol':<8} {'pattern':<12} {'status':<10} "
              f"{'low':>10} {'high':>10} {'valid_from':<12} {'valid_to':<12} {'created_at':<27}")
        for i, r in enumerate(h_rows[:50]):  # cap display
            print(f"{i:<5} {(r.get('symbol') or '?'):<8} "
                  f"{(r.get('pattern_type') or '?'):<12} "
                  f"{(r.get('status') or '?'):<10} "
                  f"{r.get('zone_low', '-')!s:>10} "
                  f"{r.get('zone_high', '-')!s:>10} "
                  f"{(r.get('valid_from') or '-')!s:<12} "
                  f"{(r.get('valid_to') or '-')!s:<12} "
                  f"{(r.get('created_at') or '-')!s:<27}")
        if len(h_rows) > 50:
            print(f"... ({len(h_rows) - 50} more H zones not displayed)")
    else:
        print("  -> NONE. The H detector has never written a row to ict_htf_zones.")
    print()

    # === Diagnosis ===
    print("=" * 78)
    print("DIAGNOSIS:")
    n_h = len(h_rows)
    n_h_active = grid.get(("H", "ACTIVE"), 0)
    n_h_breached = grid.get(("H", "BREACHED"), 0)
    n_h_expired = grid.get(("H", "EXPIRED"), 0)
    if n_h == 0:
        print("  H detector writes NOTHING. Investigate build_ict_htf_zones.py")
        print("  --timeframe H code path. Likely: detector returns 0 candidates,")
        print("  threshold mis-calibrated, or H aggregation from 5m bars is failing.")
    elif n_h_active == 0 and (n_h_breached + n_h_expired) > 0:
        print("  H detector writes zones but they all get marked BREACHED/EXPIRED")
        print("  on subsequent runs. Possible: validity windows too short, or")
        print("  recheck_breached_zones() over-aggressive on H timeframe.")
    elif n_h_active > 0:
        print("  H zones exist and are ACTIVE. ADR-003 Phase 1 v2 missed them.")
        print("  Investigate why client-side filter excluded them.")
    else:
        print("  Unclassified state.")
    print("=" * 78)


if __name__ == "__main__":
    main()
