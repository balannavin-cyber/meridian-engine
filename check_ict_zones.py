from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

# Distinct status values - see what's actually in use
r_all = sb.table("ict_htf_zones").select("status", count="exact").execute()
statuses = {}
for row in r_all.data:
    s = row.get("status", "NULL")
    statuses[s] = statuses.get(s, 0) + 1
print(f"All statuses: {statuses}")
print()

# Active zones only
r = sb.table("ict_htf_zones").select("*", count="exact").eq("status", "ACTIVE").execute()
print(f"Total ACTIVE zones: {r.count}")
tfs = {}
for row in r.data:
    tf = row.get("timeframe", "?")
    tfs[tf] = tfs.get(tf, 0) + 1
print(f"By timeframe: {tfs}")
print()
print("All active zones by symbol / timeframe:")
for row in sorted(r.data, key=lambda x: (x.get("symbol",""), x.get("timeframe",""), x.get("zone_low") or 0)):
    sym = row.get("symbol","?")
    tf = row.get("timeframe","?")
    pat = row.get("pattern_type","?")
    lo = row.get("zone_low","?")
    hi = row.get("zone_high","?")
    src = row.get("source_bar_date","?")
    vfrom = row.get("valid_from","?")
    vto = row.get("valid_to","?")
    print(f"  {sym:8s} {tf:3s} {pat:10s} {lo}-{hi}  src={src}  valid={vfrom} to {vto}")
