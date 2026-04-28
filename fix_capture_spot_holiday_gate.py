#!/usr/bin/env python3
"""
fix_capture_spot_holiday_gate.py
=================================
Adds a trading calendar holiday gate to capture_spot_1m.py.

Gate logic: at the top of main(), after env var validation, check
trading_calendar for today's is_open flag via Supabase REST.
If is_open=False (or row missing with no open_time), exit 0 cleanly.
This prevents Task Scheduler from writing stale data on market holidays.

Usage:
    python fix_capture_spot_holiday_gate.py

Safe: creates .bak_holiday_gate backup before patching.
Idempotent: checks if gate already present before applying.
"""
import shutil
from pathlib import Path

TARGET = Path("capture_spot_1m.py")
BACKUP = Path("capture_spot_1m.py.bak_holiday_gate")

# ── The gate code to insert ───────────────────────────────────────────────────
# Placed right after the env var validation block in main(), before fetch_spots()
# Uses the existing sb_headers() helper and requests import — no new dependencies.

GATE_CODE = '''    # ── Holiday gate (ENH-36 fix) ─────────────────────────────────────────────
    # Check trading_calendar before hitting Dhan API.
    # Exit 0 cleanly on holidays — no data written, no error logged.
    try:
        from zoneinfo import ZoneInfo as _ZI
        _today = str(datetime.now(timezone.utc).astimezone(_ZI("Asia/Kolkata")).date())
        _cal_url = f"{SUPABASE_URL}/rest/v1/trading_calendar"
        _cal_r = requests.get(
            _cal_url,
            headers=sb_headers(),
            params={"trade_date": f"eq.{_today}", "select": "is_open,open_time"},
            timeout=10,
        )
        if _cal_r.status_code == 200:
            _rows = _cal_r.json()
            if _rows:
                _row = _rows[0]
                if not _row.get("is_open", True) or _row.get("open_time") is None:
                    print(f"[{_today}] Market holiday — capture_spot_1m exiting cleanly.")
                    return 0
            # No row in calendar: allow run (merdian_start.py will upsert later)
    except Exception as _e:
        print(f"  [WARN] Calendar check failed (proceeding): {_e}")
    # ── End holiday gate ───────────────────────────────────────────────────────

'''

# ── Anchor: insert AFTER the env var validation block, BEFORE fetch_spots ────
# The anchor is the print statement that immediately follows env var checks.
ANCHOR = '    print(f"[{now_utc.strftime(\'%H:%M:%S UTC\')}] capture_spot_1m.py")\n'
INSERT_AFTER = ANCHOR


def main():
    if not TARGET.exists():
        print(f"ERROR: {TARGET} not found. Run from C:\\GammaEnginePython\\")
        return 1

    source = TARGET.read_text(encoding="utf-8")

    # Idempotency check
    if "Holiday gate" in source or "holiday_gate" in source:
        print("Gate already present — no changes made.")
        return 0

    if ANCHOR not in source:
        print("ERROR: Anchor line not found in capture_spot_1m.py.")
        print("File may have changed. Review manually.")
        print(f"Expected anchor:\n{ANCHOR!r}")
        return 1

    # Backup
    shutil.copy2(TARGET, BACKUP)
    print(f"Backup: {BACKUP}")

    # Insert gate AFTER the anchor line
    patched = source.replace(ANCHOR, ANCHOR + "\n" + GATE_CODE)

    TARGET.write_text(patched, encoding="utf-8")
    print(f"Patched: {TARGET}")

    # Verify
    result = TARGET.read_text(encoding="utf-8")
    if "Holiday gate" in result:
        print("Verification: gate present. Done.")
        return 0
    else:
        print("ERROR: Verification failed — restoring backup.")
        shutil.copy2(BACKUP, TARGET)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
