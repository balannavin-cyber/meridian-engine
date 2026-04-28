#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Check signal_snapshots from Apr 13 live session
r = sb.table('signal_snapshots').select(
    'symbol,ts,dte,expiry_date,atm_strike,action'
).gte('ts', '2026-04-13T00:00:00').lte('ts', '2026-04-13T23:59:59').order('ts', desc=False).limit(10).execute()

print(f"Apr 13 signal_snapshots rows: {len(r.data)}")
for row in r.data:
    print(f"  {row['symbol']} | {str(row['ts'])[11:16]} | dte={row['dte']} | expiry={row['expiry_date']} | action={row['action']}")

# Also check market_state_snapshots from Apr 13
r2 = sb.table('market_state_snapshots').select(
    'symbol,ts,dte,expiry_date'
).gte('ts', '2026-04-13T00:00:00').lte('ts', '2026-04-13T23:59:59').order('ts', desc=False).limit(5).execute()

print(f"\nApr 13 market_state_snapshots rows: {len(r2.data)}")
for row in r2.data:
    print(f"  {row['symbol']} | {str(row['ts'])[11:16]} | dte={row['dte']} | expiry={row['expiry_date']}")
