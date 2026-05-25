"""diag_active_intraday_zones.py — list ACTIVE rows in ict_zones."""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"],
)

rows = (
    sb.table("ict_zones")
      .select("symbol, trade_date, session_bar_ts, pattern_type, "
              "zone_high, zone_low, status, ict_tier, mtf_context")
      .eq("status", "ACTIVE")
      .order("session_bar_ts", desc=True)
      .limit(20)
      .execute()
      .data
)

print(f"{len(rows)} ACTIVE intraday zones in ict_zones:\n")
print(f"  {'sym':<7} {'date':<11} {'time':<6} {'pattern':<10} "
      f"{'zone':<22} {'tier':<6} {'mtf':<10}")
print("  " + "-" * 80)
for r in rows:
    sym = r["symbol"]
    td  = r["trade_date"]
    tm  = r["session_bar_ts"][11:16] if r.get("session_bar_ts") else "?"
    pt  = r["pattern_type"]
    zl  = float(r["zone_low"])
    zh  = float(r["zone_high"])
    tier = r.get("ict_tier") or "?"
    mtf  = r.get("mtf_context") or "?"
    zone_str = f"{zl:.0f}-{zh:.0f}"
    print(f"  {sym:<7} {td:<11} {tm:<6} {pt:<10} {zone_str:<22} "
          f"{tier:<6} {mtf:<10}")
