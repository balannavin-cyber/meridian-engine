#!/usr/bin/env python3
"""
fix_process_control_final.py
============================
Fixes the dual-control-plane problem once and for all.

WHAT THIS DOES
--------------
Part A — Python scripts: adds holiday gate to 4 Task Scheduler scripts
  1. build_market_spot_session_markers.py
  2. capture_market_spot_snapshot_local.py
  3. compute_iv_context_local.py
  4. run_equity_eod_until_done.py

Part B — PowerShell: generates fix_task_scheduler.ps1
  Run that script from an ADMIN PowerShell to:
  - Fix MERDIAN_Intraday_Supervisor_Start → calls merdian_start.py (kills dual-supervisor)
  - Fix MERDIAN_Spot_1M → disables run-when-missed (kills flash)

Run from C:\\GammaEnginePython\\
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

# ── Holiday gate function — inserted into every patched script ────────────────
# Self-contained: loads dotenv itself, uses only stdlib + requests.
# Fail-open: returns True on any error so scripts still run if calendar unreachable.

GATE_FN = '''\
def _is_market_open_today() -> bool:
    """Holiday gate: check trading_calendar. Fail-open on any error."""
    try:
        import os as _os
        try:
            from dotenv import load_dotenv as _lde
            _lde()
        except ImportError:
            pass
        import requests as _req
        from datetime import datetime as _dt, timezone as _tz
        from zoneinfo import ZoneInfo as _ZI
        _url = _os.getenv("SUPABASE_URL", "").rstrip("/")
        _key = _os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not _url or not _key:
            return True  # can't check — allow run
        _today = _dt.now(_tz.utc).astimezone(_ZI("Asia/Kolkata")).date().isoformat()
        _r = _req.get(
            f"{_url}/rest/v1/trading_calendar",
            headers={"apikey": _key, "Authorization": f"Bearer {_key}"},
            params={"trade_date": f"eq.{_today}", "select": "is_open,open_time"},
            timeout=10,
        )
        if _r.status_code == 200:
            _rows = _r.json()
            if _rows:
                _row = _rows[0]
                return bool(_row.get("is_open", True)) and _row.get("open_time") is not None
        return True  # no row — allow run
    except Exception:
        return True  # error — allow run

'''

# ── Patches — (file, backup_suffix, idempotency_marker, insert_before, gate_call) ──

PATCHES = [
    {
        "file": "build_market_spot_session_markers.py",
        "backup": ".bak_holiday_gate",
        "marker": "_is_market_open_today",
        # Insert gate at top of main(), before arg parse
        "anchor": '    if len(sys.argv) > 2:\n        fail("Usage: python .\\\\build_market_spot_session_markers.py [YYYY-MM-DD]")',
        "gate_call": (
            '    # ── Holiday gate ───────────────────────────────────────────────────────\n'
            '    if not _is_market_open_today():\n'
            '        print("[HOLIDAY GATE] Market closed — build_market_spot_session_markers exiting.")\n'
            '        return\n'
            '    # ────────────────────────────────────────────────────────────────────────\n\n'
        ),
        # gate function injection: insert before 'def main'
        "fn_anchor": "def main() -> None:",
    },
    {
        "file": "capture_market_spot_snapshot_local.py",
        "backup": ".bak_holiday_gate",
        "marker": "_is_market_open_today",
        # Insert in capture_once(), before fetch call
        "anchor": "    payload = fetch_idx_i_ltp_payload_with_retry()",
        "gate_call": (
            '    # ── Holiday gate ───────────────────────────────────────────────────────\n'
            '    if not _is_market_open_today():\n'
            '        print("[HOLIDAY GATE] Market closed — capture_market_spot_snapshot exiting.")\n'
            '        return 0\n'
            '    # ────────────────────────────────────────────────────────────────────────\n\n'
        ),
        "fn_anchor": "def capture_once() -> int:",
    },
    {
        "file": "compute_iv_context_local.py",
        "backup": ".bak_holiday_gate",
        "marker": "_is_market_open_today",
        # Insert in main(), before data fetch
        "anchor": "    rows = select_all_volatility_rows(days_back=400)",
        "gate_call": (
            '    # ── Holiday gate ───────────────────────────────────────────────────────\n'
            '    if not _is_market_open_today():\n'
            '        print("[HOLIDAY GATE] Market closed — compute_iv_context exiting.")\n'
            '        return 0\n'
            '    # ────────────────────────────────────────────────────────────────────────\n\n'
        ),
        "fn_anchor": "def main() -> int:",
    },
    {
        "file": "run_equity_eod_until_done.py",
        "backup": ".bak_holiday_gate",
        "marker": "_is_market_open_today",
        # Insert in main(), before session_id / main loop
        "anchor": "    session_id = now_stamp()",
        "gate_call": (
            '    # ── Holiday gate ───────────────────────────────────────────────────────\n'
            '    # Task Scheduler fires Mon-Fri regardless. Gate prevents holiday runs.\n'
            '    # For manual catch-up on non-trading days, call ingest scripts directly.\n'
            '    if not _is_market_open_today():\n'
            '        print("[HOLIDAY GATE] Market closed — run_equity_eod_until_done exiting.")\n'
            '        return\n'
            '    # ────────────────────────────────────────────────────────────────────────\n\n'
        ),
        "fn_anchor": "def main():",
    },
]

# ── Task Scheduler fix — PowerShell script (run from admin prompt) ────────────

PS1_CONTENT = r'''# fix_task_scheduler.ps1
# Run from an ADMIN PowerShell prompt.
# Fixes two Task Scheduler problems:
#   1. MERDIAN_Intraday_Supervisor_Start now calls merdian_start.py (not gamma_engine_supervisor.py)
#   2. MERDIAN_Spot_1M: disable run-when-missed (stops the flash on non-trading-day boundaries)

$BASE   = "C:\GammaEnginePython"
$PYTHON = "C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe"
$LOG    = "$BASE\logs\task_merdian_start.log"

Write-Host "=== MERDIAN Task Scheduler Fix ===" -ForegroundColor Cyan

# ── 1. Create merdian_morning_start.ps1 ──────────────────────────────────────
$morningScript = @"
`$BASE   = "C:\GammaEnginePython"
`$PYTHON = "C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe"
`$LOG    = "`$BASE\logs\task_merdian_start.log"

Add-Content `$LOG "=================================================="
Add-Content `$LOG "MERDIAN Morning Start `$(Get-Date)"
Add-Content `$LOG "=================================================="

Set-Location `$BASE
`$env:PYTHONIOENCODING = "utf-8"
& `$PYTHON "`$BASE\merdian_start.py" *>> `$LOG

Add-Content `$LOG "MERDIAN Morning Start END `$(Get-Date)"
"@

$morningPs1 = "$BASE\merdian_morning_start.ps1"
$morningScript | Out-File $morningPs1 -Encoding utf8
Write-Host "  Created: $morningPs1" -ForegroundColor Green

# ── 2. Update MERDIAN_Intraday_Supervisor_Start ───────────────────────────────
try {
    $action = New-ScheduledTaskAction `
        -Execute "PowerShell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$BASE\merdian_morning_start.ps1`""

    Set-ScheduledTask -TaskName "MERDIAN_Intraday_Supervisor_Start" -Action $action
    Write-Host "  MERDIAN_Intraday_Supervisor_Start -> merdian_morning_start.ps1" -ForegroundColor Green
} catch {
    Write-Host "  ERROR updating MERDIAN_Intraday_Supervisor_Start: $_" -ForegroundColor Red
}

# ── 3. Fix MERDIAN_Spot_1M: disable run-when-missed ──────────────────────────
try {
    $task     = Get-ScheduledTask -TaskName "MERDIAN_Spot_1M"
    $settings = $task.Settings
    $settings.StartWhenAvailable = $false
    Set-ScheduledTask -TaskName "MERDIAN_Spot_1M" -Settings $settings
    Write-Host "  MERDIAN_Spot_1M: StartWhenAvailable = false" -ForegroundColor Green
} catch {
    Write-Host "  ERROR updating MERDIAN_Spot_1M: $_" -ForegroundColor Red
}

# ── 4. Also fix MERDIAN_PreOpen same way ─────────────────────────────────────
try {
    $task     = Get-ScheduledTask -TaskName "MERDIAN_PreOpen"
    $settings = $task.Settings
    $settings.StartWhenAvailable = $false
    Set-ScheduledTask -TaskName "MERDIAN_PreOpen" -Settings $settings
    Write-Host "  MERDIAN_PreOpen: StartWhenAvailable = false" -ForegroundColor Green
} catch {
    Write-Host "  ERROR updating MERDIAN_PreOpen: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Done. Verify with: Get-ScheduledTask 'MERDIAN_Intraday_Supervisor_Start' | Get-ScheduledTaskInfo ===" -ForegroundColor Cyan
'''


# ── Patcher logic ─────────────────────────────────────────────────────────────

def patch_file(spec: dict) -> bool:
    path = BASE / spec["file"]
    backup = BASE / (spec["file"] + spec["backup"])

    if not path.exists():
        print(f"  SKIP — not found: {path.name}")
        return False

    source = path.read_text(encoding="utf-8")

    if spec["marker"] in source:
        print(f"  SKIP — gate already present: {path.name}")
        return True

    # Verify anchors exist
    if spec["anchor"] not in source:
        print(f"  ERROR — gate anchor not found in {path.name}")
        print(f"          Expected: {spec['anchor'][:60]!r}")
        return False

    if spec["fn_anchor"] not in source:
        print(f"  ERROR — fn anchor not found in {path.name}")
        return False

    # Backup
    shutil.copy2(path, backup)

    # 1. Inject gate function before the function that contains the gate call
    patched = source.replace(
        spec["fn_anchor"],
        GATE_FN + spec["fn_anchor"],
        1,  # only first occurrence
    )

    # 2. Inject gate call before anchor line
    patched = patched.replace(
        spec["anchor"],
        spec["gate_call"] + spec["anchor"],
        1,
    )

    path.write_text(patched, encoding="utf-8")

    # Verify
    result = path.read_text(encoding="utf-8")
    if spec["marker"] in result:
        print(f"  OK — patched: {path.name}  (backup: {spec['file'] + spec['backup']})")
        return True
    else:
        print(f"  ERROR — verification failed, restoring backup: {path.name}")
        shutil.copy2(backup, path)
        return False


def write_ps1() -> Path:
    ps1_path = BASE / "fix_task_scheduler.ps1"
    ps1_path.write_text(PS1_CONTENT, encoding="utf-8")
    return ps1_path


def main() -> int:
    print("=" * 70)
    print("MERDIAN — Process Control Final Fix")
    print("=" * 70)

    # Part A — Python script patches
    print("\nPart A — Adding holiday gates to Task Scheduler scripts")
    print("-" * 70)

    results = []
    for spec in PATCHES:
        results.append(patch_file(spec))

    ok = sum(results)
    print(f"\n  {ok}/{len(PATCHES)} scripts patched successfully.")

    # Part B — PowerShell script for Task Scheduler
    print("\nPart B — Task Scheduler fix")
    print("-" * 70)
    ps1 = write_ps1()
    print(f"  Generated: {ps1}")
    print()
    print("  *** Run this from an ADMIN PowerShell prompt: ***")
    print(f"  PowerShell -ExecutionPolicy Bypass -File \"{ps1}\"")
    print()
    print("  This will:")
    print("    - Fix MERDIAN_Intraday_Supervisor_Start → merdian_start.py")
    print("    - Fix MERDIAN_Spot_1M: no longer fires on missed triggers")
    print("    - Fix MERDIAN_PreOpen: same")

    print()
    print("=" * 70)
    if ok == len(PATCHES):
        print("Part A complete. Run the admin PowerShell for Part B.")
    else:
        print("Some patches failed — check errors above.")
    print("=" * 70)
    return 0 if ok == len(PATCHES) else 1


if __name__ == "__main__":
    sys.exit(main())
