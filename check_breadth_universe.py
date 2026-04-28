#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Check breadth_universe_sets
r = sb.table('breadth_universe_sets').select('*').limit(3).execute()
if r.data:
    print(f"breadth_universe_sets columns: {list(r.data[0].keys())}")
    for row in r.data:
        print(f"  {row}")
else:
    print("breadth_universe_sets: no rows")

# Check what tables exist with 'breadth' in name
# Also check equity_intraday_last for structure
r2 = sb.table('equity_intraday_last').select('*').limit(2).execute()
if r2.data:
    print(f"\nequity_intraday_last columns: {list(r2.data[0].keys())}")
    for row in r2.data:
        print(f"  {row}")
