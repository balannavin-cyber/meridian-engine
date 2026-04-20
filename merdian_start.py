#!/usr/bin/env python3
"""
merdian_start.py  --  MERDIAN Morning Startup
==============================================
Single command replaces all manual PS window starts.

What it does:
  Step 0: Auto-insert trading_calendar row (permanent V18A-03 fix)
  Step 1: Kill all existing MERDIAN processes (clean slate)
  Step 2: Start health_monitor, signal_dashboard, supervisor (background)
  Step 3: Show status with PIDs

No terminal windows needed. All logs in logs/pm_<name>.log

Usage:
    python merdian_start.py           # full startup
    python merdian_start.py --status  # status only, no start
"""

import sys, os, time, requests
from datetime import date, datetime, timezone
sys.path.insert(0, r'C:\GammaEnginePython')
import merdian_pm as pm

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

STATUS_ONLY  = '--status' in sys.argv
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def ensure_calendar_row():
    """
    Permanent fix for preflight V18A-03.
    Read-before-write: never overwrite a pre-loaded holiday row.
    OI-17 fix: TradingCalendar class did not exist in trading_calendar
    module — import was failing silently, falling back to weekday rule,
    overwriting holidays as is_open=True.
    """
    today = date.today()

    if not SUPABASE_URL or not SUPABASE_KEY:
        return False, "Supabase credentials missing"

    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }

    try:
        # Step 1: Read existing row first
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers=headers,
            params={"trade_date": f"eq.{today}", "select": "trade_date,is_open,holiday_name"},
            timeout=10,
        )
        if r.status_code < 300:
            rows = r.json()
            if rows:
                row = rows[0]
                if not row.get("is_open", True):
                    # Pre-loaded holiday - do not overwrite
                    name = row.get("holiday_name") or "Market holiday"
                    return True, f"{today} -> HOLIDAY ({name}) -- row preserved, not overwritten"
                else:
                    # Row exists and is_open=True - already correct
                    return True, f"{today} -> TRADING DAY -- row exists, no change"

        # Step 2: No row exists - insert using weekday rule
        is_open = today.weekday() < 5   # Mon-Fri open, Sat-Sun closed
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "trade_date"},
            json=[{"trade_date": str(today), "is_open": is_open}],
            timeout=10,
        )
        if r.status_code < 300:
            day_type = "TRADING DAY" if is_open else "WEEKEND"
            return True, f"{today} -> {day_type} (is_open={is_open}) inserted (new row)"
        return False, f"Supabase {r.status_code}: {r.text[:80]}"

    except Exception as e:
        return False, f"Failed: {e}"

def main():
    print()
    print('  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—')
    print('  â•‘  MERDIAN Morning Startup                         â•‘')
    print(f'  â•‘  {datetime.now().strftime("%Y-%m-%d %H:%M:%S"):<46}â•‘')
    print('  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•')

    if STATUS_ONLY:
        pm.print_status()
        return

    # â”€â”€ Step 0: Calendar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\n  [Step 0] Trading calendar auto-insert...')
    ok, msg = ensure_calendar_row()
    print(f'    {"âœ“" if ok else "âš "}  {msg}')
    if not ok:
        print('    WARNING: Calendar insert failed. Preflight may show V18A-03 error.')
        print('    Manually run in Supabase:')
        print(f'    INSERT INTO trading_calendar (trade_date, is_open)')
        print(f'    VALUES (\'{date.today()}\', true) ON CONFLICT (trade_date) DO UPDATE SET is_open=true;')

    # â”€â”€ Step 1: Clean slate â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\n  [Step 1] Stopping all existing MERDIAN processes...')
    results = pm.stop_all()
    for name, msg in results:
        print(f'    â€¢ {name}: {msg}')
    time.sleep(1.0)

    # â”€â”€ Step 2: Start â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\n  [Step 2] Starting processes...')
    all_ok = True
    for name in ['health_monitor', 'signal_dashboard', 'supervisor', 'exit_monitor']:
        ok, msg = pm.start(name)
        print(f'    {"âœ“" if ok else "âœ—"}  {name}: {msg}')
        if not ok:
            all_ok = False
        time.sleep(0.5)

    # â”€â”€ Step 3: Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print('\n  [Step 3] Status:')
    time.sleep(1.5)
    pm.print_status()

    print('  Quick reference:')
    print('    http://localhost:8765  â€” Health Monitor')
    print('    http://localhost:8766  â€” Signal Dashboard')
    print()
    print('    python merdian_status.py   â€” check processes')
    print('    python merdian_stop.py     â€” stop everything')
    print()
    if not all_ok:
        print('  âš  Some processes failed. Check logs/ directory.')
    print()

if __name__ == '__main__':
    main()

