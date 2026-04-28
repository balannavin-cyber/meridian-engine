#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

r = sb.table('signal_snapshots').select('symbol,ts,dte,expiry_date').order('ts', desc=True).limit(5).execute()
print('=== SPO-01: DTE in signal_snapshots ===')
for row in r.data:
    print(f"  {row['symbol']} | ts={str(row['ts'])[11:16]} | dte={row['dte']} | expiry={row['expiry_date']}")

nulls = [r for r in r.data if r['dte'] is None]
print(f"\n  DTE null count in last 5 rows: {len(nulls)}")
print("  SPO-01 STATUS:", "OPEN - DTE still null" if len(nulls) == len(r.data) else "CLOSED - DTE populated" if not nulls else "PARTIAL")
