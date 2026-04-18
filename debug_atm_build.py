#!/usr/bin/env python3
"""Debug: trace exactly where build_atm_option_bars_mtf.py drops to 0 rows."""
from dotenv import load_dotenv; load_dotenv()
import os
from datetime import datetime, date, timedelta
from collections import defaultdict
from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

INST_ID = "9992f600-51b3-4009-b487-f878692a0bc5"  # NIFTY
TICK    = 50

# Step 1: Check spot 5m
print("=== Step 1: spot 5m ===")
r = sb.table("hist_spot_bars_5m").select("trade_date,bar_ts,close").eq(
    "instrument_id", INST_ID).order("bar_ts").limit(3).execute()
print(f"Rows: {len(r.data)}")
for row in r.data: print(" ", row)

# Step 2: Get trade dates
dates = sorted(set(r2["trade_date"] for r2 in sb.table("hist_spot_bars_5m").select(
    "trade_date").eq("instrument_id", INST_ID).execute().data))
print(f"\n=== Step 2: {len(dates)} trade dates ===")
print(f"First: {dates[0]}  Last: {dates[-1]}")

# Step 3: Check expiry dates
print("\n=== Step 3: expiry dates ===")
exp_rows = sb.table("hist_option_bars_1m").select("expiry_date").eq(
    "instrument_id", INST_ID).limit(100).execute().data
expiry_dates = sorted(set(date.fromisoformat(r["expiry_date"])
                          for r in exp_rows if r.get("expiry_date")))
print(f"  {len(expiry_dates)} unique expiries: {expiry_dates[:5]}")

# Step 4: Test one specific date
test_date = "2025-10-15"
print(f"\n=== Step 4: test date {test_date} ===")

# Get first spot bar for this date
spot_r = sb.table("hist_spot_bars_5m").select("bar_ts,close").eq(
    "instrument_id", INST_ID).eq("trade_date", test_date).order("bar_ts").limit(1).execute()
if not spot_r.data:
    print("NO SPOT BARS for this date")
else:
    first_bar = spot_r.data[0]
    spot_close = float(first_bar["close"])
    atm = round(round(spot_close / TICK) * TICK, 0)
    print(f"  First bar: {first_bar['bar_ts']} close={spot_close} ATM={atm}")

    # Step 5: Find nearest expiry
    td = date.fromisoformat(test_date)
    future_exp = [e for e in expiry_dates if e >= td]
    exp = min(future_exp) if future_exp else None
    print(f"  Nearest expiry: {exp}")

    # Step 6: Query option bars
    lo = atm - TICK * 2
    hi = atm + TICK * 2
    print(f"  Querying strikes {lo}-{hi}...")
    opt_r = sb.table("hist_option_bars_1m").select(
        "bar_ts,strike,option_type,open,high,low,close,volume,oi"
    ).eq("instrument_id", INST_ID).eq("trade_date", test_date).gte(
        "strike", str(lo)).lte("strike", str(hi)).eq(
        "is_pre_market", False).limit(10).execute()
    print(f"  Option bars found: {len(opt_r.data)}")
    for row in opt_r.data[:3]:
        print(f"    {row['bar_ts']} strike={row['strike']} {row['option_type']} close={row['close']}")

    if opt_r.data:
        # Step 7: Test bucket matching
        print(f"\n=== Step 5: bucket matching ===")
        bar_ts = first_bar["bar_ts"]
        bucket_dt = datetime.fromisoformat(bar_ts.replace("Z", "+00:00"))
        next_bucket = bucket_dt + timedelta(minutes=5)
        print(f"  5m bucket: {bucket_dt} -> {next_bucket}")

        for opt in opt_r.data[:3]:
            odt = datetime.fromisoformat(opt["bar_ts"].replace("Z", "+00:00"))
            odt_floored = odt.replace(second=0, microsecond=0)
            in_bucket = bucket_dt <= odt_floored < next_bucket
            print(f"  opt {opt['bar_ts']} floored={odt_floored} in_bucket={in_bucket}")
    else:
        print("  NO OPTION BARS — check is_pre_market filter or strike range")
        # Try without is_pre_market
        opt_r2 = sb.table("hist_option_bars_1m").select(
            "bar_ts,strike,option_type,close,is_pre_market"
        ).eq("instrument_id", INST_ID).eq("trade_date", test_date).gte(
            "strike", str(lo)).lte("strike", str(hi)).limit(5).execute()
        print(f"  Without is_pre_market filter: {len(opt_r2.data)} rows")
        for row in opt_r2.data:
            print(f"    {row}")
