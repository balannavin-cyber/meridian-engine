# ============================================================================
# register_ict_htf_zones_task.ps1
# ----------------------------------------------------------------------------
# MERDIAN F3 - register MERDIAN_ICT_HTF_Zones_0845 scheduled task.
# Daily Mon-Fri 08:45 IST (machine local time, assumed IST).
# Wraps run_ict_htf_zones_daily.bat -> build_ict_htf_zones.py --timeframe both
# Closes TD-017. ENH-71 instrumented; surfaces in script_execution_log.
# Pattern mirrors MERDIAN_Spot_MTF_Rollup_1600 (Session 9, TD-019 closure).
# Registered Session 11 (2026-04-28).
#
# Idempotent: safely re-runnable. Existing task is unregistered before
# re-creation.
#
# Usage (from C:\GammaEnginePython):
#   powershell -ExecutionPolicy Bypass -File register_ict_htf_zones_task.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

$TaskName = "MERDIAN_ICT_HTF_Zones_0845"
$BatPath  = "C:\GammaEnginePython\run_ict_htf_zones_daily.bat"

# --- preflight: wrapper must exist before registration -----------------------
if (-not (Test-Path $BatPath)) {
    Write-Host ""
    Write-Host "ERROR: wrapper not found at $BatPath"
    Write-Host "  Place run_ict_htf_zones_daily.bat in C:\GammaEnginePython\ first."
    Write-Host ""
    exit 1
}
Write-Host "Wrapper present: $BatPath"

# --- idempotency: remove existing task if present ----------------------------
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Existing task '$TaskName' found - unregistering before re-registration"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# --- trigger: weekly Mon-Fri at 08:45 (machine local time) -------------------
$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "08:45"

# --- action: invoke the BAT wrapper ------------------------------------------
$Action = New-ScheduledTaskAction -Execute $BatPath

# --- settings ----------------------------------------------------------------
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

# --- principal: current user, runs only when logged on -----------------------
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive

$Description = "MERDIAN F3 - daily ICT HTF zone rebuild (W+D timeframes via --timeframe both). Closes TD-017. ENH-71 instrumented. Registered Session 11 (2026-04-28)."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Trigger $Trigger `
    -Action $Action `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description | Out-Null

Write-Host ""
Write-Host "Registered: $TaskName"
Write-Host ""

# --- verify registration -----------------------------------------------------
Get-ScheduledTaskInfo -TaskName $TaskName |
    Format-List TaskName, LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns

Write-Host ""
Write-Host "Smoke-test the task right now:"
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
Write-Host "  Start-Sleep -Seconds 30"
Write-Host "  Get-ScheduledTaskInfo -TaskName $TaskName | Format-List"
Write-Host ""
Write-Host "Then verify in Supabase:"
Write-Host "  SELECT script_name, host, exit_reason, contract_met,"
Write-Host "         expected_writes, actual_writes, duration_ms, started_at"
Write-Host "    FROM script_execution_log"
Write-Host "   WHERE script_name='build_ict_htf_zones.py'"
Write-Host "   ORDER BY started_at DESC LIMIT 3;"
Write-Host ""
