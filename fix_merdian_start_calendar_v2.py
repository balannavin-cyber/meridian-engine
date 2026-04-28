#!/usr/bin/env python3
"""
fix_merdian_start_calendar_v2.py
=================================
Robust version — finds ensure_calendar_row() by line scanning,
replaces the entire function body. No unicode string matching.
"""
import shutil
from pathlib import Path

TARGET = Path("merdian_start.py")
BACKUP = Path("merdian_start.py.bak_calendar_fix")

NEW_FN = '''\
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
'''


def find_function_bounds(lines: list, fn_name: str) -> tuple:
    """
    Find start and end line indices of a top-level function definition.
    Returns (start_idx, end_idx) where end_idx is exclusive.
    Returns (-1, -1) if not found.
    """
    start = -1
    for i, line in enumerate(lines):
        if line.startswith(f"def {fn_name}("):
            start = i
            break

    if start == -1:
        return -1, -1

    # Find end: next top-level def/class or end of file
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line and not line[0].isspace() and (
            line.startswith("def ") or
            line.startswith("class ") or
            line.startswith("if __name__")
        ):
            return start, i

    return start, len(lines)


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    if "OI-17 fix" in source or "Read-before-write: never overwrite" in source:
        print("Fix already applied — no changes made.")
        return 0

    lines = source.splitlines(keepends=True)
    start, end = find_function_bounds(lines, "ensure_calendar_row")

    if start == -1:
        print("ERROR: ensure_calendar_row() not found in merdian_start.py")
        return 1

    print(f"Found ensure_calendar_row() at lines {start+1}-{end} (0-indexed: {start}-{end})")

    # Backup
    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    # Replace function
    new_lines = lines[:start] + [NEW_FN + "\n"] + lines[end:]
    patched = "".join(new_lines)

    TARGET.write_text(patched, encoding="utf-8")

    # Verify
    result = TARGET.read_text(encoding="utf-8")
    if "Read-before-write: never overwrite" in result and "ensure_calendar_row" in result:
        print(f"Patched: {TARGET}")
        print("Verification: OK")
        print()
        print("ensure_calendar_row() now:")
        print("  1. Reads existing row first")
        print("  2. is_open=False (holiday) -> preserves it, prints holiday name")
        print("  3. is_open=True -> already correct, no change")
        print("  4. No row -> inserts using weekday rule")
        return 0
    else:
        print("ERROR: Verification failed — restoring backup.")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
