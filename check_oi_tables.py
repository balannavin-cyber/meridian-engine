#!/usr/bin/env python3
"""Check which option chain tables exist and what OI data is available."""
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

candidates = [
    "option_chain_snapshots",
    "hist_option_bars_1m",
    "latest_option_chain_snapshots",
    "historical_option_chain_snapshots",
]

for t in candidates:
    try:
        r = sb.table(t).select("*").limit(1).execute()
        if r.data:
            cols = list(r.data[0].keys())
            oi_cols = [c for c in cols if "oi" in c.lower() or "interest" in c.lower() or "volume" in c.lower() or "strike" in c.lower()]
            print(f"\n{t}:")
            print(f"  Columns: {cols}")
            print(f"  OI/Strike cols: {oi_cols}")
            # Count rows
            r2 = sb.table(t).select("*", count="exact").limit(1).execute()
            print(f"  Total rows: {r2.count}")
        else:
            print(f"\n{t}: empty")
    except Exception as e:
        print(f"\n{t}: {str(e)[:80]}")
