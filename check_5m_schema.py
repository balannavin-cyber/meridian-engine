from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

# Get one row to learn schema
r = sb.table("hist_spot_bars_5m").select("*").limit(1).execute()
if r.data:
    print("hist_spot_bars_5m columns:")
    for k, v in r.data[0].items():
        print(f"  {k}: {v}")
else:
    print("hist_spot_bars_5m is empty")
