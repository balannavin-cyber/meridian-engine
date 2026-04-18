#!/usr/bin/env python3
"""Debug trade_date distribution in hist_spot_bars_5m."""
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

INST_ID = "9992f600-51b3-4009-b487-f878692a0bc5"

# Check trade_date distribution in spot 5m
print("=== trade_date distribution in hist_spot_bars_5m (NIFTY) ===")
r = sb.table("hist_spot_bars_5m").select("trade_date").eq(
    "instrument_id", INST_ID).order("trade_date").execute()
from collections import Counter
counts = Counter(row["trade_date"] for row in r.data)
print(f"Total rows: {len(r.data)}")
print(f"Distinct dates: {len(counts)}")
print(f"Null dates: {counts.get(None, 0)}")
print(f"First 5 dates: {sorted(k for k in counts if k)[:5]}")
print(f"Last 5 dates:  {sorted(k for k in counts if k)[-5:]}")
print(f"Rows per date sample: {dict(list(sorted(counts.items()))[:3])}")

# Check a late date
print("\n=== Checking late date 2026-03-01 ===")
r2 = sb.table("hist_spot_bars_5m").select("trade_date,bar_ts,close").eq(
    "instrument_id", INST_ID).eq("trade_date","2026-03-01").limit(3).execute()
print(f"Rows for 2026-03-01: {len(r2.data)}")

# Check by bar_ts range instead
print("\n=== Checking rows by bar_ts (2026-03 range) ===")
r3 = sb.table("hist_spot_bars_5m").select("trade_date,bar_ts,close").eq(
    "instrument_id", INST_ID).gte("bar_ts","2026-03-01").lte(
    "bar_ts","2026-03-05").limit(5).execute()
print(f"Rows in 2026-03 range: {len(r3.data)}")
for row in r3.data:
    print(f"  trade_date={row['trade_date']} bar_ts={row['bar_ts']}")

# Load expiries safely per-date chunk
print("\n=== Expiry dates (safe query) ===")
r4 = sb.table("hist_option_bars_1m").select("expiry_date").eq(
    "instrument_id", INST_ID).eq("trade_date","2025-10-15").limit(5).execute()
print(f"Sample expiry from 2025-10-15: {[r['expiry_date'] for r in r4.data]}")

r5 = sb.table("hist_option_bars_1m").select("expiry_date").eq(
    "instrument_id", INST_ID).eq("trade_date","2026-01-15").limit(5).execute()
print(f"Sample expiry from 2026-01-15: {[r['expiry_date'] for r in r5.data]}")
