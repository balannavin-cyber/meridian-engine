#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Get column names first
r = sb.table('market_state_snapshots').select('*').limit(1).execute()
if r.data:
    print("Columns:", list(r.data[0].keys()))
    row = r.data[0]
    # Find DTE and expiry related columns
    for k, v in row.items():
        if any(x in k.lower() for x in ['dte', 'expiry', 'ts', 'time', 'strike']):
            print(f"  {k}: {v}")
else:
    print("No rows found")
