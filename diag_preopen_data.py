"""
diag_preopen_data.py
====================
TD-064 (was C-07b) data diagnostic.

Verifies whether pre-market rows are actually being written. Reads
hist_spot_bars_1m for last 30 days, counts is_pre_market=True rows by
trade_date and instrument_id, plots time-of-day distribution.

Output -> stdout AND C:\\GammaEnginePython\\diagnostics\\td064_preopen_data.txt
"""
from __future__ import annotations
import os
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

# ---- env ----
dotenv = Path(r"C:\GammaEnginePython\.env")
if dotenv.exists():
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from supabase import create_client
sb = create_client(
    os.environ["SUPABASE_URL"],
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
)

OUT = Path(r"C:\GammaEnginePython\diagnostics\td064_preopen_data.txt")
OUT.parent.mkdir(parents=True, exist_ok=True)

INSTRUMENT_ID_TO_SYMBOL = {
    "9992f600-51b3-4009-b487-f878692a0bc5": "NIFTY",
    "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71": "SENSEX",
}

IST = timezone(timedelta(hours=5, minutes=30))

buf: list[str] = []
def out(s: str = "") -> None:
    buf.append(s)
    print(s, flush=True)


out("=" * 60)
out("TD-064 PRE-MARKET DATA STATE")
out("=" * 60)

# ---- 1. Total is_pre_market rows in last 30 days ----
out("\n[1] Pre-market rows in hist_spot_bars_1m (last 30 days)")
out("-" * 60)
since = (date.today() - timedelta(days=30)).isoformat()
try:
    r = (sb.table("hist_spot_bars_1m")
         .select("trade_date,bar_ts,instrument_id,is_pre_market", count="exact")
         .eq("is_pre_market", True)
         .gte("trade_date", since)
         .order("trade_date", desc=True)
         .order("bar_ts", desc=True)
         .limit(1000)
         .execute())
    total = r.count
    rows = r.data or []
    out(f"  Total pre-market rows since {since}: {total}")
    out(f"  Returned (capped 1000): {len(rows)}")
except Exception as e:
    out(f"  ERROR: {e}")
    rows = []
    total = 0

# ---- 2. Group by trade_date and symbol ----
out("\n[2] Pre-market rows by trade_date x symbol")
out("-" * 60)
by_day_sym: dict = defaultdict(lambda: defaultdict(int))
ts_by_day_sym: dict = defaultdict(lambda: defaultdict(list))
for row in rows:
    sym = INSTRUMENT_ID_TO_SYMBOL.get(row["instrument_id"], row["instrument_id"][:8])
    by_day_sym[row["trade_date"]][sym] += 1
    ts_by_day_sym[row["trade_date"]][sym].append(row["bar_ts"])

for d in sorted(by_day_sym.keys(), reverse=True)[:15]:
    parts = [f"{sym}={by_day_sym[d][sym]:>3}" for sym in sorted(by_day_sym[d].keys())]
    out(f"  {d}  {'  '.join(parts)}")

# ---- 3. Time-of-day distribution (last 5 days) ----
out("\n[3] Time-of-day of pre-market rows (last 5 days, IST)")
out("-" * 60)
recent_5_days = sorted(by_day_sym.keys(), reverse=True)[:5]
for d in recent_5_days:
    out(f"  {d}:")
    for sym in sorted(ts_by_day_sym[d].keys()):
        timestamps = ts_by_day_sym[d][sym]
        # Convert UTC to IST and show range
        ist_times = []
        for ts_str in timestamps:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ist = ts.astimezone(IST)
                ist_times.append(ist.strftime("%H:%M:%S"))
            except Exception:
                pass
        if ist_times:
            ist_times.sort()
            out(f"    {sym}: N={len(ist_times)}  first={ist_times[0]}  last={ist_times[-1]}")

# ---- 4. Are there ANY rows in 09:00-09:14 IST window for last 5 days? ----
out("\n[4] Rows in the C-07b critical window (09:00-09:14 IST)")
out("-" * 60)
critical_window_count = 0
critical_examples = []
for d in recent_5_days:
    for sym in ts_by_day_sym[d].keys():
        for ts_str in ts_by_day_sym[d][sym]:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                ist = ts.astimezone(IST)
                if ist.hour == 9 and ist.minute < 15:
                    critical_window_count += 1
                    if len(critical_examples) < 10:
                        critical_examples.append(f"{d} {sym} {ist.strftime('%H:%M:%S')}")
            except Exception:
                pass

out(f"  Critical-window (09:00-09:14 IST) row count last 5 days: {critical_window_count}")
if critical_examples:
    out("  Examples:")
    for ex in critical_examples[:10]:
        out(f"    {ex}")
if critical_window_count == 0:
    out("  *** NO ROWS in the window MERDIAN_PreOpen is supposed to populate. ***")
    out("  *** This confirms TD-064: pre-open capture is not landing data. ***")

# ---- 5. Check market_spot_snapshots also (alternative pre-open destination) ----
out("\n[5] Alternative table: market_spot_snapshots in same window")
out("-" * 60)
try:
    # market_spot_snapshots: ts is full timestamp
    since_ts = (datetime.now(IST) - timedelta(days=5)).astimezone(timezone.utc).isoformat()
    r2 = (sb.table("market_spot_snapshots")
          .select("ts,symbol,spot", count="exact")
          .gte("ts", since_ts)
          .order("ts", desc=True)
          .limit(500)
          .execute())
    out(f"  Total rows last 5 days: {r2.count}")
    # Filter to 09:00-09:14 IST
    pre_count = 0
    examples = []
    for row in (r2.data or []):
        try:
            ts = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
            ist = ts.astimezone(IST)
            if ist.hour == 9 and ist.minute < 15:
                pre_count += 1
                if len(examples) < 10:
                    examples.append(f"{ist.strftime('%Y-%m-%d %H:%M:%S')}  {row.get('symbol','?')}={row.get('spot','?')}")
        except Exception:
            pass
    out(f"  In 09:00-09:14 IST window: {pre_count}")
    for ex in examples:
        out(f"    {ex}")
    if pre_count == 0:
        out("  *** No pre-open data in market_spot_snapshots either. ***")
except Exception as e:
    out(f"  ERROR: {e}")

OUT.write_text("\n".join(buf), encoding="utf-8")
out(f"\n[written to: {OUT}]")
