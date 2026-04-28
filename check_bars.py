from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

# Check if there's a 1H bars table
for tbl in ["hist_spot_bars_1h", "hist_spot_bars_60m", "hist_spot_bars_5m"]:
    try:
        r = sb.table(tbl).select("symbol,ts", count="exact").order("ts", desc=True).limit(3).execute()
        print(f"{tbl}: {r.count} rows")
        for row in r.data:
            print(f"  latest: {row.get('symbol')} {row.get('ts')}")
    except Exception as e:
        print(f"{tbl}: {type(e).__name__}: {str(e)[:120]}")
    print()
