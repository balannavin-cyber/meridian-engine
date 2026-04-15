#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import os
from supabase import create_client
sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])

for symbol in ['NIFTY', 'SENSEX']:
    r = sb.table('ict_htf_zones').select(
        'symbol,timeframe,pattern_type,zone_low,zone_high,source_bar_date'
    ).eq('symbol', symbol).eq('status', 'ACTIVE').order('zone_low', desc=True).execute()

    print(f"\n{symbol} — {len(r.data)} active zones (high to low):")
    print(f"  {'TF':<4} {'Pattern':<12} {'Zone':<20} {'Formed'}")
    print(f"  {'-'*55}")
    for z in r.data:
        zone_str = f"{float(z['zone_low']):,.0f}-{float(z['zone_high']):,.0f}"
        print(f"  {z['timeframe']:<4} {z['pattern_type']:<12} {zone_str:<20} {z['source_bar_date']}")
