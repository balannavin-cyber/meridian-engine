"""
MERDIAN Pre-flight Check — 2026-04-24
Runs 5 go/no-go checks. Exits non-zero if any FAIL.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()

IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)

fails = []
warns = []

def ok(msg):   print(f"  OK   {msg}")
def warn(msg): warns.append(msg); print(f"  WARN {msg}")
def fail(msg): fails.append(msg); print(f"  FAIL {msg}")

print(f"MERDIAN pre-flight — {now_ist:%Y-%m-%d %H:%M:%S IST}")
print()

# 1. Supabase reachable
print("[1] Supabase connectivity")
try:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    r = sb.table("market_spot_snapshots").select("symbol", count="exact").limit(1).execute()
    ok(f"Supabase responsive; market_spot_snapshots has {r.count} rows")
except Exception as e:
    fail(f"Supabase query failed: {type(e).__name__}: {e}")
    print("\n".join(f"  {f}" for f in fails))
    sys.exit(1)

# 2. Kite token valid (REST auth)
print()
print("[2] Kite token validity")
try:
    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=os.environ["ZERODHA_API_KEY"])
    kite.set_access_token(os.environ["ZERODHA_ACCESS_TOKEN"])
    p = kite.profile()
    ok(f"Kite AUTH OK — user: {p.get('user_name')}")
except Exception as e:
    fail(f"Kite AUTH failed: {type(e).__name__}: {e}")

# 3. equity_intraday_last freshness — will 09:05 cron be able to write?
print()
print("[3] equity_intraday_last state (will 09:05 cron write fresh data?)")
try:
    r = sb.table("equity_intraday_last").select("ticker,ts", count="exact").order("ts", desc=True).limit(1).execute()
    if r.count and r.data:
        latest = datetime.fromisoformat(r.data[0]["ts"].replace("Z", "+00:00")).astimezone(IST)
        age_hrs = (now_ist - latest).total_seconds() / 3600
        ok(f"Table has {r.count} rows; latest ts {latest:%Y-%m-%d %H:%M IST} (age {age_hrs:.1f}h)")
        if age_hrs > 48:
            warn(f"Latest reference is {age_hrs:.0f}h old — cron at 09:05 will refresh it (expected)")
    else:
        warn("Table empty — cron at 09:05 will do first population")
except Exception as e:
    fail(f"equity_intraday_last check failed: {type(e).__name__}: {e}")

# 4. ICT HTF zones for today
print()
print("[4] ICT HTF zones ready for today")
try:
    r = sb.table("ict_htf_zones").select("symbol,timeframe,pattern_type", count="exact").eq("status", "ACTIVE").execute()
    tfs = {}
    syms = {}
    for row in r.data:
        tf = row.get("timeframe", "?")
        sym = row.get("symbol", "?")
        tfs[tf] = tfs.get(tf, 0) + 1
        syms[sym] = syms.get(sym, 0) + 1
    if r.count >= 6:
        ok(f"{r.count} active zones — by timeframe {tfs}, by symbol {syms}")
    else:
        warn(f"Only {r.count} active zones — expected 6+ (some W/D) — by timeframe {tfs}")
except Exception as e:
    fail(f"ict_htf_zones check failed: {type(e).__name__}: {e}")

# 5. script_execution_log recent activity (instrumentation alive?)
print()
print("[5] script_execution_log recent activity")
try:
    cutoff = (now_ist - timedelta(hours=24)).isoformat()
    r = sb.table("script_execution_log").select("script_name,started_at,exit_reason", count="exact").gte("started_at", cutoff).order("started_at", desc=True).limit(5).execute()
    if r.count and r.count > 0:
        ok(f"{r.count} executions in last 24h; most recent:")
        for row in r.data[:3]:
            print(f"       {row.get('started_at','?')[:19]}  {row.get('script_name','?'):40s}  {row.get('exit_reason','?')}")
    else:
        warn("No script executions logged in last 24h (may be pre-market dead zone)")
except Exception as e:
    fail(f"script_execution_log check failed: {type(e).__name__}: {e}")

# Summary
print()
print("=" * 60)
if fails:
    print(f"PRE-FLIGHT FAIL — {len(fails)} critical issue(s):")
    for f in fails:
        print(f"  - {f}")
    sys.exit(1)
elif warns:
    print(f"PRE-FLIGHT PASS WITH WARNINGS — {len(warns)} warning(s):")
    for w in warns:
        print(f"  - {w}")
    sys.exit(0)
else:
    print("PRE-FLIGHT PASS — all 5 checks clean.")
    sys.exit(0)
