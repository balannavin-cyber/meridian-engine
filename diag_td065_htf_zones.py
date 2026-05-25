"""
diag_td065_htf_zones.py
=======================
Diagnostic for TD-065 (was OI-11) -- HTF zone rebuild automation status.

Three checks:
  (1) hist_ict_htf_zones D-timeframe row freshness: when were the most
      recent D zones created?
  (2) D zone count by trade_date for last 14 days: did rebuild fire daily?
  (3) Same for H-timeframe (the .bat runs both --timeframe both AND
      --timeframe H, so we should see fresh H rows too).

Note: the .bat is observed to call build_ict_htf_zones.py --timeframe both
TWICE -- once with `both`, once with `H` separately. Worth flagging as
likely-redundant in tech_debt.md; H is part of `both`.

Output: stdout AND C:\\GammaEnginePython\\diagnostics\\td065_htf_zones.txt
"""
from __future__ import annotations
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
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

OUT = Path(r"C:\GammaEnginePython\diagnostics\td065_htf_zones.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)

buf: list[str] = []
def out(s: str = "") -> None:
    buf.append(s); print(s, flush=True)


out("=" * 60)
out("TD-065 (was OI-11) HTF ZONE REBUILD AUTOMATION STATUS")
out("=" * 60)

# ---- 1. Most recent D zones across both indices ----
out("\n[1] Most recent D zones (hist_ict_htf_zones, timeframe=D)")
out("-" * 60)
try:
    r = (sb.table("hist_ict_htf_zones")
         .select("*", count="exact")
         .eq("timeframe", "D")
         .order("created_at", desc=True)
         .limit(10)
         .execute())
    out(f"  Total D rows in table: {r.count}")
    out("  10 most recent (by created_at):")
    for row in (r.data or [])[:10]:
        sym = row.get("symbol", "?")
        ptype = row.get("pattern_type", "?")
        td = row.get("trade_date", "?")
        ca = row.get("created_at", "?")
        out(f"    {ca}  {sym:8s}  pattern={ptype:12s}  trade_date={td}")
except Exception as e:
    out(f"  ERROR: {e}")

# ---- 2. D zone activity by created_at date (last 14 days) ----
out("\n[2] D zone created_at activity, last 14 days")
out("-" * 60)
since = (date.today() - timedelta(days=14)).isoformat()
try:
    # Fetch all D rows with created_at >= since (paginated)
    all_rows = []
    offset = 0
    page = 1000
    while True:
        rr = (sb.table("hist_ict_htf_zones")
              .select("created_at,symbol,pattern_type,trade_date")
              .eq("timeframe", "D")
              .gte("created_at", since)
              .order("created_at", desc=True)
              .range(offset, offset + page - 1)
              .execute())
        rows = rr.data or []
        all_rows.extend(rows)
        if len(rows) < page:
            break
        offset += page
    by_day = defaultdict(int)
    for row in all_rows:
        ca = row.get("created_at", "")
        day = ca[:10] if len(ca) >= 10 else "?"
        by_day[day] += 1
    out(f"  D rows created in last 14 days: {len(all_rows)}")
    out(f"  Distinct creation days: {len(by_day)}")
    out("  Day-by-day:")
    for d in sorted(by_day.keys(), reverse=True):
        out(f"    {d}  rows={by_day[d]}")
    # Flag missing weekdays
    out("")
    out("  Expected weekdays in window:")
    today = date.today()
    expected_days = []
    for i in range(14):
        d = today - timedelta(days=i)
        if d.weekday() < 5:  # Mon-Fri
            expected_days.append(d.isoformat())
    missing = [d for d in expected_days if d not in by_day]
    if missing:
        out(f"  *** Weekdays with NO D-zone creation: {missing}")
    else:
        out("  All weekdays in window have D-zone activity.")
except Exception as e:
    out(f"  ERROR: {e}")

# ---- 3. H zone activity (same window) ----
out("\n[3] H zone created_at activity, last 14 days")
out("-" * 60)
try:
    all_rows_h = []
    offset = 0
    while True:
        rr = (sb.table("hist_ict_htf_zones")
              .select("created_at")
              .eq("timeframe", "H")
              .gte("created_at", since)
              .order("created_at", desc=True)
              .range(offset, offset + page - 1)
              .execute())
        rows = rr.data or []
        all_rows_h.extend(rows)
        if len(rows) < page:
            break
        offset += page
    by_day_h = defaultdict(int)
    for row in all_rows_h:
        ca = row.get("created_at", "")
        day = ca[:10] if len(ca) >= 10 else "?"
        by_day_h[day] += 1
    out(f"  H rows created in last 14 days: {len(all_rows_h)}")
    for d in sorted(by_day_h.keys(), reverse=True)[:10]:
        out(f"    {d}  rows={by_day_h[d]}")
except Exception as e:
    out(f"  ERROR: {e}")

# ---- 4. W zone activity (sanity) ----
out("\n[4] W zone created_at activity, last 14 days (sanity)")
out("-" * 60)
try:
    rr = (sb.table("hist_ict_htf_zones")
          .select("created_at,timeframe", count="exact")
          .eq("timeframe", "W")
          .gte("created_at", since)
          .order("created_at", desc=True)
          .limit(20)
          .execute())
    out(f"  W rows created in last 14 days: {rr.count}")
    if rr.data:
        for row in rr.data[:5]:
            out(f"    {row.get('created_at','?')}")
except Exception as e:
    out(f"  ERROR: {e}")

OUT.write_text("\n".join(buf), encoding="utf-8")
out(f"\n[written to: {OUT}]")
