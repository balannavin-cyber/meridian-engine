"""
diag_td065_h_zones_in_live_table.py

H-zone presence check across BOTH potential write destinations:
  - hist_ict_htf_zones  (historical aggregate, written by build_ict_htf_zones.py)
  - ict_zones           (live intraday session-scoped, written by runner)

Hypothesis: live runner writes H zones to ict_zones during the session;
the build_ict_htf_zones.py --timeframe H call is vestigial/no-data.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

dotenv = Path(r"C:\GammaEnginePython\.env")
if dotenv.exists():
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from supabase import create_client
sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
)


def out(s: str) -> None:
    print(s, flush=True)


out("=" * 60)
out("H-zone destination check")
out("=" * 60)

# ---- 1. hist_ict_htf_zones (aggregate) ----
out("\n[1] hist_ict_htf_zones, timeframe=H")
out("-" * 60)
try:
    r = (sb.table("hist_ict_htf_zones")
         .select("created_at,symbol,pattern_type", count="exact")
         .eq("timeframe", "H")
         .order("created_at", desc=True)
         .limit(5)
         .execute())
    out(f"  Total H rows in hist_ict_htf_zones: {r.count}")
    for row in (r.data or [])[:5]:
        out(f"    {row.get('created_at','?')}  {row.get('symbol','?')}  "
            f"{row.get('pattern_type','?')}")
except Exception as e:
    out(f"  ERROR: {e}")

# ---- 2. ict_zones (live intraday, session-scoped) ----
out("\n[2] ict_zones (live intraday session table), timeframe=H")
out("-" * 60)
try:
    r = (sb.table("ict_zones")
         .select("*", count="exact")
         .eq("timeframe", "H")
         .order("created_at", desc=True)
         .limit(10)
         .execute())
    out(f"  Total H rows in ict_zones: {r.count}")
    if r.data:
        out("  10 most recent:")
        for row in r.data[:10]:
            out(f"    {row.get('created_at','?')}  {row.get('symbol','?')}  "
                f"{row.get('pattern_type','?')}  zone={row.get('zone_low','?')}-"
                f"{row.get('zone_high','?')}")
    else:
        out("  (no rows)")
except Exception as e:
    out(f"  ERROR: {e}")

# ---- 3. ict_zones - what timeframes does it actually have ----
out("\n[3] ict_zones distinct timeframes (last 1000 rows by created_at)")
out("-" * 60)
try:
    from collections import Counter
    r = (sb.table("ict_zones")
         .select("timeframe,created_at")
         .order("created_at", desc=True)
         .limit(1000)
         .execute())
    rows = r.data or []
    tf_count = Counter(row.get("timeframe", "?") for row in rows)
    out(f"  Sampled {len(rows)} most recent ict_zones rows. Timeframe distribution:")
    for tf, n in sorted(tf_count.items(), key=lambda kv: -kv[1]):
        out(f"    {tf}: {n}")
    if rows:
        out(f"  created_at range in sample: "
            f"{rows[-1].get('created_at','?')} -> {rows[0].get('created_at','?')}")
except Exception as e:
    out(f"  ERROR: {e}")
