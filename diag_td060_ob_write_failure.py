"""
diag_td060_ob_write_failure.py — surface the actual write error.

The runner's write_new_zones() catches all errors in a per-row try/except
that only log()s the message. The error has been printed and lost across
hundreds of cycles. This script reproduces a single OB write attempt
synchronously and PROPAGATES the error, so we can see what Postgres
actually says.

Then runs an introspection query against information_schema to pull
column types and constraints so we can read the schema directly.

Read-only, except for one synthetic upsert with a session_bar_ts in the
year 2099 (so it can't possibly conflict with real data and is trivially
identifiable). At end, deletes the synthetic row if it was written.

Runtime ~5 seconds.
"""

import os
import json
from datetime import datetime, date, timezone

from dotenv import load_dotenv
from supabase import create_client


def main():
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    print("=" * 70)
    print("  TD-060 BULL_OB write-failure diagnostic")
    print("=" * 70)

    # ── Part 1: information_schema dump for ict_zones ─────────────────
    print("\n[1] ict_zones column schema")
    print("-" * 70)
    try:
        # Supabase doesn't expose information_schema via REST by default,
        # but the Postgres function pg_typeof() can be invoked via RPC if
        # configured. Easier: fetch one existing row + try probing types
        # by inspection. Actually, simplest is to just select one row
        # and inspect Python types of values.
        sample = (
            sb.table("ict_zones")
              .select("*")
              .limit(1)
              .execute()
              .data
        )
        if sample:
            print(f"     sample row columns ({len(sample[0])} cols):")
            for k, v in sorted(sample[0].items()):
                tn = type(v).__name__
                vstr = str(v)[:50] if v is not None else "NULL"
                print(f"       {k:<28} {tn:<10} {vstr}")
        else:
            print("     ict_zones is empty -- can't sample column types")
    except Exception as e:
        print(f"     ERROR fetching sample: {e}")

    # ── Part 2: try a real BULL_OB upsert and read the error ──────────
    print("\n[2] Synthetic BULL_OB upsert attempt (will propagate error)")
    print("-" * 70)

    # Build a row that mirrors what ICTPattern.to_db_row() emits for an OB.
    # session_bar_ts in year 2099 to guarantee no conflict with real data.
    synthetic_ts = "2099-12-31T10:00:00+00:00"
    bull_ob_row = {
        "symbol":              "NIFTY",
        "trade_date":          "2099-12-31",
        "detected_at_ts":      synthetic_ts,
        "session_bar_ts":      synthetic_ts,
        "pattern_type":        "BULL_OB",
        "direction":           1,
        "opt_type":            "CE",
        "zone_high":           24000.0,
        "zone_low":            23990.0,
        "spot_at_detection":   24000.0,
        "ict_tier":            "TIER2",
        "ict_size_mult":       1.0,
        "has_prior_sweep":     False,
        "mom_aligned":         False,
        "impulse_strong":      False,
        "time_zone":           "MORNING",
        "mtf_context":         "LOW",
        "htf_zone_id":         None,
        "atm_iv_at_detection": None,
        "status":              "ACTIVE",
    }
    print(f"     row: pattern_type=BULL_OB, direction=1, opt_type=CE, ")
    print(f"          session_bar_ts={synthetic_ts}")

    try:
        result = (
            sb.table("ict_zones")
              .upsert(bull_ob_row,
                      on_conflict="symbol,session_bar_ts,pattern_type")
              .execute()
        )
        print(f"     ✓ BULL_OB write SUCCEEDED.")
        print(f"       returned data: {result.data}")
        print(f"       → Schema accepts BULL_OB. Gap must be runtime.")

        # Clean up the synthetic row
        try:
            sb.table("ict_zones").delete().eq(
                "session_bar_ts", synthetic_ts
            ).execute()
            print(f"     ✓ Cleaned up synthetic row.")
        except Exception as e:
            print(f"     ! Couldn't clean up synthetic row: {e}")
            print(f"       Manual cleanup: DELETE FROM ict_zones "
                  f"WHERE session_bar_ts = '{synthetic_ts}';")

    except Exception as e:
        print(f"     ✗ BULL_OB write FAILED.")
        print(f"       Exception type: {type(e).__name__}")
        print(f"       Message: {e}")
        # Try to extract structured error info
        for attr in ("code", "message", "details", "hint", "args"):
            v = getattr(e, attr, None)
            if v is not None:
                print(f"       .{attr}: {v}")

    # ── Part 3: same probe for BEAR_OB ────────────────────────────────
    print("\n[3] Synthetic BEAR_OB upsert attempt")
    print("-" * 70)
    bear_ob_row = dict(bull_ob_row,
                       pattern_type="BEAR_OB",
                       direction=-1,
                       opt_type="PE",
                       session_bar_ts="2099-12-31T10:01:00+00:00")
    try:
        result = (
            sb.table("ict_zones")
              .upsert(bear_ob_row,
                      on_conflict="symbol,session_bar_ts,pattern_type")
              .execute()
        )
        print(f"     ✓ BEAR_OB write SUCCEEDED.")
        try:
            sb.table("ict_zones").delete().eq(
                "session_bar_ts", "2099-12-31T10:01:00+00:00"
            ).execute()
        except Exception:
            pass
    except Exception as e:
        print(f"     ✗ BEAR_OB write FAILED.")
        print(f"       Exception type: {type(e).__name__}")
        print(f"       Message: {e}")
        for attr in ("code", "message", "details", "hint", "args"):
            v = getattr(e, attr, None)
            if v is not None:
                print(f"       .{attr}: {v}")

    # ── Part 4: existing BULL_FVG row count for sanity ────────────────
    print("\n[4] ict_zones row count by pattern_type (sanity check)")
    print("-" * 70)
    for pt in ("BULL_FVG", "BEAR_FVG", "BULL_OB", "BEAR_OB", "JUDAS_BULL"):
        rows = (
            sb.table("ict_zones")
              .select("id")
              .eq("pattern_type", pt)
              .limit(1000)
              .execute()
              .data
        )
        print(f"     {pt:<12} {len(rows):>5}")

    print("\n" + "=" * 70)
    print("  Done. Read the error in [2] / [3] above for diagnosis.")
    print("=" * 70)


if __name__ == "__main__":
    main()
