# fix_task_scheduler.ps1
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
