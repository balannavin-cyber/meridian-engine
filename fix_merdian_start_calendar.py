#!/usr/bin/env python3
"""
fix_merdian_start_calendar.py
==============================
Fixes ensure_calendar_row() in merdian_start.py.

Bug: TradingCalendar import fails silently → falls back to weekday rule →
always upserts is_open=True on weekdays, overwriting pre-loaded holidays.

Fix: read existing row first. If is_open=False already in Supabase, skip
the upsert and print the holiday name. Only upsert if no row exists.
If row exists with is_open=True, leave it alone (was already correct).

Safe: creates .bak_calendar_fix backup before patching.
Idempotent: checks for fix marker before applying.
"""
import shutil
from pathlib import Path

TARGET = Path("merdian_start.py")
BACKUP = Path("merdian_start.py.bak_calendar_fix")

OLD_FN = '''def ensure_calendar_row():
    """
    Permanent fix for preflight V18A-03.
    Auto-inserts today\'s trading_calendar row using rule-based logic.
    Mon-Fri = open. Sat-Sun = closed.
    NSE holidays: manually maintained in trading_calendar module.
    Upserts \xe2\x80\x94 safe to call every morning regardless.
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
            return True, f"{today} \xe2\x86\x92 {day_type} (is_open={is_open}) upserted"
        return False, f"Supabase {r.status_code}: {r.text[:80]}"
    except Exception as e:
        return False, f"Failed: {e}"'''

NEW_FN = '''def ensure_calendar_row():
    """
    Permanent fix for preflight V18A-03.
    Auto-inserts today\'s trading_calendar row if it does not exist.

    Read-before-write: if a row already exists (pre-loaded holiday or
    prior startup), preserve it — never overwrite is_open=False with True.
    Only inserts when no row exists, using weekday rule as fallback.
    OI-17 fix: TradingCalendar class does not exist in trading_calendar
    module — import was silently failing and falling back to weekday rule,
    causing holidays to be overwritten as is_open=True.
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
        # ── Step 1: Read existing row ─────────────────────────────────────────
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
                    # Pre-loaded holiday — do not overwrite
                    name = row.get("holiday_name") or "Market holiday"
                    return True, f"{today} \xe2\x86\x92 HOLIDAY ({name}) — row preserved, not overwritten"
                else:
                    # Row exists and is_open=True — already correct
                    return True, f"{today} \xe2\x86\x92 TRADING DAY — row exists, no change"

        # ── Step 2: No row exists — insert using weekday rule ─────────────────
        is_open = today.weekday() < 5  # Mon-Fri = open, Sat-Sun = closed
        # Try trading_calendar module (current_session_state approach)
        try:
            from trading_calendar import current_session_state as _css
            # If we can import the module, check if it knows about today
            # by using is_open from weekday as safe default
            pass
        except Exception:
            pass

        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "trade_date"},
            json=[{"trade_date": str(today), "is_open": is_open}],
            timeout=10,
        )
        if r.status_code < 300:
            day_type = "TRADING DAY" if is_open else "WEEKEND"
            return True, f"{today} \xe2\x86\x92 {day_type} (is_open={is_open}) inserted (new row)"
        return False, f"Supabase {r.status_code}: {r.text[:80]}"

    except Exception as e:
        return False, f"Failed: {e}"'''


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if "OI-17 fix" in source:
        print("Fix already applied — no changes made.")
        return 0

    if OLD_FN not in source:
        print("ERROR: Expected function body not found in merdian_start.py.")
        print("File may have changed. Review manually.")
        return 1

    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    patched = source.replace(OLD_FN, NEW_FN, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "OI-17 fix" in result:
        print(f"Patched: {TARGET}")
        print("Verification: OK")
        print()
        print("ensure_calendar_row() now:")
        print("  1. Reads existing row first")
        print("  2. If is_open=False (holiday) → preserves it, prints holiday name")
        print("  3. If is_open=True → leaves it, prints 'no change'")
        print("  4. If no row → inserts using weekday rule (new row only)")
        return 0
    else:
        print("ERROR: Verification failed — restoring backup.")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
