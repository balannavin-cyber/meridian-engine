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
    Auto-inserts today's trading_calendar row using rule-based logic.
    Mon-Fri = open. Sat-Sun = closed.
    NSE holidays: manually maintained in trading_calendar module.
    Upserts — safe to call every morning regardless.
    """
    today   = date.today()
    is_open = today.weekday() < 5  # weekday rule as fallback

    # Use trading_calendar module if available (handles NSE holidays)
    try:
        from trading_calendar import TradingCalendar
        cal     = TradingCalendar()
        is_open = cal.is_trading_day(today)
    except Exception:
        pass

    if not SUPABASE_URL or not SUPABASE_KEY:
        return False, "Supabase credentials missing"

    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "resolution=merge-duplicates",
            },
            params={"on_conflict": "trade_date"},
            json=[{"trade_date": str(today), "is_open": is_open}],
            timeout=10,
        )
        if r.status_code < 300:
            day_type = "TRADING DAY" if is_open else "HOLIDAY/WEEKEND"
            return True, f"{today} → {day_type} (is_open={is_open}) upserted"
        return False, f"Supabase {r.status_code}: {r.text[:80]}"
    except Exception as e:
        return False, f"Failed: {e}"


def main():
    print()
    print('  ╔══════════════════════════════════════════════════╗')
    print('  ║  MERDIAN Morning Startup                         ║')
    print(f'  ║  {datetime.now().strftime("%Y-%m-%d %H:%M:%S"):<46}║')
    print('  ╚══════════════════════════════════════════════════╝')

    if STATUS_ONLY:
        pm.print_status()
        return

    # ── Step 0: Calendar ──────────────────────────────────────────────────────
    print('\n  [Step 0] Trading calendar auto-insert...')
    ok, msg = ensure_calendar_row()
    print(f'    {"✓" if ok else "⚠"}  {msg}')
    if not ok:
        print('    WARNING: Calendar insert failed. Preflight may show V18A-03 error.')
        print('    Manually run in Supabase:')
        print(f'    INSERT INTO trading_calendar (trade_date, is_open)')
        print(f'    VALUES (\'{date.today()}\', true) ON CONFLICT (trade_date) DO UPDATE SET is_open=true;')

    # ── Step 1: Clean slate ───────────────────────────────────────────────────
    print('\n  [Step 1] Stopping all existing MERDIAN processes...')
    results = pm.stop_all()
    for name, msg in results:
        print(f'    • {name}: {msg}')
    time.sleep(1.0)

    # ── Step 2: Start ─────────────────────────────────────────────────────────
    print('\n  [Step 2] Starting processes...')
    all_ok = True
    for name in ['health_monitor', 'signal_dashboard', 'supervisor']:
        ok, msg = pm.start(name)
        print(f'    {"✓" if ok else "✗"}  {name}: {msg}')
        if not ok:
            all_ok = False
        time.sleep(0.5)

    # ── Step 3: Status ────────────────────────────────────────────────────────
    print('\n  [Step 3] Status:')
    time.sleep(1.5)
    pm.print_status()

    print('  Quick reference:')
    print('    http://localhost:8765  — Health Monitor')
    print('    http://localhost:8766  — Signal Dashboard')
    print()
    print('    python merdian_status.py   — check processes')
    print('    python merdian_stop.py     — stop everything')
    print()
    if not all_ok:
        print('  ⚠ Some processes failed. Check logs/ directory.')
    print()

if __name__ == '__main__':
    main()
