# diag_preopen_render_v2.py — save in C:\GammaEnginePython
import sys
sys.path.insert(0, r'C:\GammaEnginePython')
from datetime import datetime, timezone, timedelta
import json

# Replicate get_preopen_status() logic but for a specific past trading day
IST = timezone(timedelta(hours=5, minutes=30))
TARGET_DATE = "2026-05-08"  # Friday — known to have 09:08 row

# Re-import the helpers
from merdian_live_dashboard import sb_get, parse_ist_dt

# Same SQL pattern as get_preopen_status(), but anchored to TARGET_DATE
target_ist = datetime.strptime(TARGET_DATE, "%Y-%m-%d").replace(tzinfo=IST)
target_start_utc = target_ist.astimezone(timezone.utc).isoformat()
target_end_ist = target_ist.replace(hour=23, minute=59, second=59)
target_end_utc = target_end_ist.astimezone(timezone.utc).isoformat()

rows = sb_get(
    "market_spot_snapshots",
    f"select=ts,spot,symbol&ts=gte.{target_start_utc}&ts=lt.{target_end_utc}&order=ts.asc&limit=200",
)
print(f"Total rows fetched for {TARGET_DATE}: {len(rows)}")

captured = []
for row in rows:
    dt = parse_ist_dt(row.get("ts", ""))
    if (
        dt
        and dt.strftime("%Y-%m-%d") == TARGET_DATE
        and dt.hour == 9
        and dt.minute < 15
    ):
        captured.append({
            "ts": dt.strftime("%H:%M:%S"),
            "spot": row.get("spot"),
            "symbol": row.get("symbol"),
        })

result = {"captured": len(captured) > 0, "count": len(captured), "rows": captured[:6]}
print(f"\nget_preopen_status()-equivalent for {TARGET_DATE}:")
print(json.dumps(result, indent=2, default=str))

# Also dump the first 5 raw rows + their parsed IST datetime, to see if the filter is working
print(f"\nFirst 5 rows raw + parsed IST:")
for row in rows[:5]:
    raw_ts = row.get("ts", "")
    dt = parse_ist_dt(raw_ts)
    print(f"  raw={raw_ts}  parsed_ist={dt}  hour={dt.hour if dt else 'N/A'}  minute={dt.minute if dt else 'N/A'}")