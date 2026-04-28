from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
# Just pull one row to see what columns exist
r = sb.table("ict_htf_zones").select("*").limit(1).execute()
if r.data:
    print("Columns on ict_htf_zones:")
    for k in r.data[0].keys():
        print(f"  {k}: {r.data[0][k]}")
else:
    print("Table is empty")
