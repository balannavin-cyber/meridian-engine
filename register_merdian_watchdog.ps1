# register_merdian_watchdog.ps1
# Registers MERDIAN_Watchdog Task Scheduler job (TD-062 active fix).
# Runs every 15 minutes, IgnoreNew, pythonw.exe, --kill enabled.
#
# Run as Administrator.
#
# Usage:
#   .\register_merdian_watchdog.ps1
#   .\register_merdian_watchdog.ps1 -IntervalMinutes 10 -DryRun
#   .\register_merdian_watchdog.ps1 -PythonW "C:\Python312\pythonw.exe"

param(
    [string]$ScriptPath = "C:\GammaEnginePython\merdian_watchdog.py",
    [string]$PythonW = $null,                # auto-detect if null
    [int]$IntervalMinutes = 15,
    [switch]$NoKill,                          # register in dry-run sweep mode
    [switch]$DryRun                           # show plan, don't register
)

$ErrorActionPreference = "Stop"

# Auto-detect pythonw.exe from one of the migrated MERDIAN_* tasks if not given
if (-not $PythonW) {
    $sample = Get-ScheduledTask | Where-Object {
        $_.TaskName -like "MERDIAN_*" -and $_.Actions[0].Execute -match "pythonw\.exe$"
    } | Select-Object -First 1
    if ($sample) {
        $PythonW = $sample.Actions[0].Execute
        Write-Host "Auto-detected pythonw.exe from $($sample.TaskName): $PythonW" -ForegroundColor Cyan
    } else {
        # Fall back to PATH lookup
        $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
        if ($cmd) {
            $PythonW = $cmd.Source
            Write-Host "Auto-detected pythonw.exe from PATH: $PythonW" -ForegroundColor Cyan
        } else {
            Write-Host "Could not auto-detect pythonw.exe. Pass -PythonW <path> explicitly." -ForegroundColor Red
            exit 1
        }
    }
}

if (-not (Test-Path $PythonW)) {
    Write-Host "pythonw.exe not found at: $PythonW" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $ScriptPath)) {
    Write-Host "Watchdog script not found at: $ScriptPath" -ForegroundColor Yellow
    Write-Host "(Will still register; ensure the script is deployed before next trigger)" -ForegroundColor Yellow
}

$killArg = if ($NoKill) { "" } else { " --kill" }
$argument = "`"$ScriptPath`"$killArg"

Write-Host "Plan:" -ForegroundColor Cyan
Write-Host "  TaskName    : MERDIAN_Watchdog"
Write-Host "  Execute     : $PythonW"
Write-Host "  Argument    : $argument"
Write-Host "  Interval    : every $IntervalMinutes min, indefinitely"
Write-Host "  WorkingDir  : $(Split-Path $ScriptPath)"
Write-Host "  MultipleInst: IgnoreNew"
Write-Host "  ExecTimeout : 5 min"

if ($DryRun) {
    Write-Host "DRY RUN -- not registering." -ForegroundColor Yellow
    return
}

$action = New-ScheduledTaskAction `
    -Execute $PythonW `
    -Argument $argument `
    -WorkingDirectory (Split-Path $ScriptPath)

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
# RepetitionDuration omitted -> repeats indefinitely on modern Windows;
# if the platform requires explicit duration, set to ([TimeSpan]::MaxValue) or 99999 days.

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

# Unregister existing if present (idempotent)
$existing = Get-ScheduledTask -TaskName "MERDIAN_Watchdog" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Existing MERDIAN_Watchdog task found -- unregistering for clean re-register..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName "MERDIAN_Watchdog" -Confirm:$false
}

Register-ScheduledTask `
    -TaskName "MERDIAN_Watchdog" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "TD-062 active fix: sweeps heartbeats, kills stuck MERDIAN_* task instances. See merdian_watchdog.py." `
    -Force | Out-Null

Write-Host "MERDIAN_Watchdog registered." -ForegroundColor Green
Write-Host "First fire in ~1 minute. Logs: C:\GammaEnginePython\heartbeats\watchdog.log"
