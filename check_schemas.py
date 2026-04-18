#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

print("=== hist_market_state columns ===")
r = sb.table("hist_market_state").select("*").limit(1).execute()
if r.data: print(list(r.data[0].keys()))

print("\n=== hist_spot_bars_1m columns ===")
r2 = sb.table("hist_spot_bars_1m").select("*").limit(1).execute()
if r2.data: print(list(r2.data[0].keys()))
