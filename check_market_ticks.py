#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
from collections import Counter

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

# Count by instrument type
r = sb.table('market_ticks').select('instrument_type,symbol').gte('ts','2026-04-15T03:30:00').execute()
print(f'Total ticks today: {len(r.data)}')

types = Counter(row['instrument_type'] for row in r.data)
print('By type:', dict(types))

syms = Counter(row['symbol'] for row in r.data)
print('Top symbols:', dict(sorted(syms.items(), key=lambda x: -x[1])[:10]))

# Sample latest
r2 = sb.table('market_ticks').select(
    'ts,symbol,instrument_type,strike,last_price,open_interest,volume'
).gte('ts','2026-04-15T03:30:00').order('ts',desc=True).limit(8).execute()

print('\nLatest ticks:')
for row in r2.data:
    ts = str(row['ts'])[11:19]
    sym = row['symbol']
    itype = row['instrument_type']
    strike = row['strike']
    ltp = row['last_price']
    oi = row['open_interest']
    vol = row['volume']
    print(f'  {ts} | {sym} | {itype} | strike={strike} | ltp={ltp} | oi={oi} | vol={vol}')

# Check time range
r3 = sb.table('market_ticks').select('ts').gte('ts','2026-04-15T03:30:00').order('ts').limit(1).execute()
r4 = sb.table('market_ticks').select('ts').gte('ts','2026-04-15T03:30:00').order('ts',desc=True).limit(1).execute()
if r3.data and r4.data:
    print(f'\nFirst tick: {r3.data[0]["ts"][11:19]} UTC')
    print(f'Last tick:  {r4.data[0]["ts"][11:19]} UTC')
