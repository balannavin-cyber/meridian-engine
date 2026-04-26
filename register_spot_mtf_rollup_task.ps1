<#
.SYNOPSIS
  Register MERDIAN_Spot_MTF_Rollup_1600 -- daily 5m/15m spot-bar rollup.

.DESCRIPTION
  TD-019 / TD-023 closure (Session 9, 2026-04-26).

  Schedules build_spot_bars_mtf.py to run at 16:00 IST Mon-Fri via the
  run_spot_mtf_rollup_once.bat wrapper. Pattern matches existing tasks
  (MERDIAN_Market_Close_Capture, MERDIAN_Post_Market_1600_Capture).

  Idempotent: if a task with the same name already exists, it is
  unregistered first. Safe to re-run.

  Run from an elevated PowerShell prompt (Administrator). Task Scheduler
  task creation requires admin on most Windows machines.

.PARAMETER WhatIf
  Preview what would happen without registering. Use first time:
    .\register_spot_mtf_rollup_task.ps1 -WhatIf

.NOTES
  Why 16:00 IST:
    Markets close 15:30 IST. capture_spot_1m.py runs to 15:31 IST.
    16:00 leaves 29 min buffer for any in-flight 1m writes / network
    blips, and stays well clear of the 16:00 MERDIAN_Post_Market_1600
    task (which runs different scripts; no resource contention but
    cleaner to space them).
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $TaskName = "MERDIAN_Spot_MTF_Rollup_1600",
    [string] $WorkDir  = "C:\GammaEnginePython",
    [string] $BatName  = "run_spot_mtf_rollup_once.bat",
    [string] $LogPath  = "logs\task_output.log",
    [string] $TimeOfDay = "16:00",
    [string[]] $DaysOfWeek = @("Monday","Tuesday","Wednesday","Thursday","Friday")
)

$ErrorActionPreference = "Stop"

# -- Pre-flight --------------------------------------------------------------
$batPath = Join-Path $WorkDir $BatName
if (-not (Test-Path $batPath)) {
    Write-Error "Wrapper not found: $batPath. Place run_spot_mtf_rollup_once.bat in $WorkDir before running this."
    exit 1
}

$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    Write-Error "python.exe not on PATH. Cannot register task -- verify Python install."
    exit 2
}
Write-Host "[OK] python found at: $pythonExe"
Write-Host "[OK] wrapper found:   $batPath"

# Build the action: powershell -> Start-Process cmd -> bat -> log redirect.
# Mirrors run_market_close_capture_once.bat task action exactly.
$actionCommand = "Start-Process cmd -ArgumentList '/c $batPath >> $LogPath 2>&1' -WindowStyle Hidden -Wait"
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"$actionCommand`"" `
    -WorkingDirectory $WorkDir

# Trigger: weekly Mon-Fri at TimeOfDay.
$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek $DaysOfWeek `
    -At $TimeOfDay

# Settings: don't run if missed; allow on battery; stop after 30 min hung.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

# Run as current user, regardless of whether logged in.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

$task = New-ScheduledTask `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "TD-019/TD-023 closure: daily 5m/15m spot-bar rollup. ENH-71 instrumented; surfaces in script_execution_log."

# -- Idempotency: unregister if exists ---------------------------------------
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    if ($PSCmdlet.ShouldProcess($TaskName, "Unregister existing task")) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[OK] Removed existing task: $TaskName"
    }
}

# -- Register ----------------------------------------------------------------
if ($PSCmdlet.ShouldProcess($TaskName, "Register new task")) {
    Register-ScheduledTask -TaskName $TaskName -InputObject $task | Out-Null
    Write-Host "[OK] Registered: $TaskName"
    Write-Host "     Schedule: Weekly $($DaysOfWeek -join ',') at $TimeOfDay"
    Write-Host "     Action:   $batPath  (>> $LogPath)"
    Write-Host ""
    Write-Host "Verify with:"
    Write-Host "  Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State"
    Write-Host "  Get-ScheduledTaskInfo -TaskName $TaskName"
    Write-Host ""
    Write-Host "Force a one-off run (optional smoke test):"
    Write-Host "  Start-ScheduledTask -TaskName $TaskName"
    Write-Host "  Then check: SELECT * FROM script_execution_log WHERE script_name='build_spot_bars_mtf.py' ORDER BY started_at DESC LIMIT 2;"
}
