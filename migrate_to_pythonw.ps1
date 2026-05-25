<#
.SYNOPSIS
  Migrate MERDIAN_* Task Scheduler entries from .bat/.ps1 wrappers to direct pythonw.exe calls.
  Closes TD-061 (window-suppression) and TD-063 (MultipleInstances=IgnoreNew defense-in-depth).

.DESCRIPTION
  Walks every MERDIAN_* task. For each:
    - If already on pythonw.exe         : only tightens settings.
    - If in explicit skip list          : only tightens settings (complex .ps1 supervisor/observer).
    - If wrapper .bat/.ps1 calls python : re-registers as `pythonw.exe <script.py>`.
    - If wrapper has 0 or >1 python calls : only tightens settings, skips action rewrite.
  Settings tightened on every task: Hidden, MultipleInstances=IgnoreNew, battery flags, 30-min timeout.
  Every mutated task is backed up to backups\scheduler\<ts>\<TaskName>.xml first.

.PARAMETER Apply
  Actually apply changes. Without -Apply the script only prints the migration plan.

.PARAMETER BasePath
  Path to MERDIAN repo. Default C:\GammaEnginePython.

.EXAMPLE
  .\migrate_to_pythonw.ps1                 # DRY-RUN — prints plan, mutates nothing
  .\migrate_to_pythonw.ps1 -Apply          # Commits changes

.NOTES
  Requires Administrator. Run from an elevated PowerShell session.
  Rollback per task: Register-ScheduledTask -Xml (Get-Content backups\scheduler\<ts>\<name>.xml -Raw) -TaskName <name> -Force
#>

[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$BasePath = 'C:\GammaEnginePython'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# ---- Admin check
$identity  = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Run elevated PowerShell (Administrator)."
    exit 1
}

# ---- Discover pythonw.exe from an existing migrated task
function Get-PythonwPath {
    foreach ($refName in @('MERDIAN_Spot_1M','MERDIAN_Live_Dashboard','MERDIAN_HB_Watchdog','MERDIAN_PreOpen')) {
        $ref = Get-ScheduledTask -TaskName $refName -ErrorAction SilentlyContinue
        if ($null -eq $ref) { continue }
        $exec = $ref.Actions[0].Execute
        if ($exec -and ($exec -like '*pythonw*') -and (Test-Path $exec)) {
            return $exec
        }
        # Bare 'pythonw.exe' — resolve via where.exe
        if ($exec -like '*pythonw*') {
            $resolved = (& where.exe pythonw.exe 2>$null) | Select-Object -First 1
            if ($resolved) { return $resolved }
        }
    }
    $resolved = (& where.exe pythonw.exe 2>$null) | Select-Object -First 1
    if ($resolved) { return $resolved }
    throw "Could not locate pythonw.exe. Edit script to set explicit path."
}
$PythonwExe = Get-PythonwPath
Write-Host "[INFO] pythonw.exe resolved: $PythonwExe" -ForegroundColor Cyan
Write-Host "[INFO] BasePath: $BasePath" -ForegroundColor Cyan

# ---- Migration plan: task -> wrapper file (relative to BasePath) to inspect
$plan = [ordered]@{
    'MERDIAN_Daily_Audit'               = 'run_daily_audit.bat'
    'MERDIAN_ICT_HTF_Zones_0845'        = 'run_ict_htf_zones_daily.bat'        # Multi-step post-S28 (zones + Pine) — expect SKIP_MULTI_STEP
    'MERDIAN_IV_Context_0905'           = 'run_iv_context_once.ps1'
    'MERDIAN_PO3_SessionBias_1005'      = 'run_po3_session_bias_once.bat'
    'MERDIAN_Spot_MTF_Rollup_1600'      = 'run_spot_mtf_rollup_once.bat'
    'MERDIAN_Market_Close_Capture'      = 'run_market_close_capture_once.bat'
    'MERDIAN_Post_Market_1600_Capture'  = 'run_post_market_capture_once.bat'
    'MERDIAN_Session_Markers_1602'      = 'run_market_spot_session_markers_once.bat'
    'MERDIAN_EOD_Breadth_Refresh'       = 'run_eod_breadth_refresh.ps1'
}

# Tasks where we never rewrite the action — only tighten settings.
$settingsOnly = @(
    'MERDIAN_Intraday_Supervisor_Start',   # merdian_morning_start.ps1 — supervisor; manual review
    'MERDIAN_Watchdog'                     # watchdog_check.ps1 — passive observer
)

# ---- Backup directory
$ts        = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path $BasePath "backups\scheduler\$ts"
if ($Apply) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Write-Host "[INFO] Backup dir: $backupDir" -ForegroundColor Cyan
}

# ---- Extract python invocation from a .bat or .ps1 wrapper
function Get-PythonInvocationFromWrapper {
    param([string]$WrapperPath)

    if (-not (Test-Path $WrapperPath)) {
        return [pscustomobject]@{ Status = 'MISSING'; }
    }

    $content = Get-Content $WrapperPath -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        return [pscustomobject]@{ Status = 'EMPTY'; }
    }

    $lines = $content -split "`r?`n" |
             Where-Object { $_.Trim() -ne '' } |
             Where-Object { $_.Trim() -notmatch '^(@?REM\b|::|rem\b|#)' }

    $found = @()
    foreach ($line in $lines) {
        # Match an interpreter call:  [optional path]python[w][.exe]  <something>.py  [args...]
        if ($line -match '(^|[\s"])(?<py>[A-Za-z0-9_\-\\\:\.]*python[w]?(\.exe)?)\s+(?<script>[A-Za-z0-9_\-\\\:\.]+\.py)(?<rest>(\s+\S+)*)\s*$') {
            $found += [pscustomobject]@{
                Script = $Matches['script']
                Args   = ($Matches['rest']).Trim()
                Line   = $line.Trim()
            }
        }
    }

    if ($found.Count -eq 0) { return [pscustomobject]@{ Status = 'NO_PY' } }
    if ($found.Count -gt 1) { return [pscustomobject]@{ Status = 'MULTI'; Count = $found.Count; Lines = ($found.Line -join ' | ') } }
    return [pscustomobject]@{ Status = 'OK'; Script = $found[0].Script; Args = $found[0].Args }
}

# ---- Build settings (applied to every MERDIAN_* task)
function New-MerdianSettings {
    New-ScheduledTaskSettingsSet `
        -Hidden `
        -MultipleInstances IgnoreNew `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::FromMinutes(30))
}

# ---- Enumerate all MERDIAN_* tasks
$allMerdian = @(Get-ScheduledTask -TaskName 'MERDIAN_*')
Write-Host ""
Write-Host "[INFO] Found $($allMerdian.Count) MERDIAN_* tasks" -ForegroundColor Cyan

# ---- Build report
$report = @()
foreach ($task in $allMerdian) {
    $name    = $task.TaskName
    $execNow = if ($task.Actions.Count -gt 0) { $task.Actions[0].Execute } else { '' }
    $argsNow = if ($task.Actions.Count -gt 0) { $task.Actions[0].Arguments } else { '' }
    $state   = $task.State

    $entry = [pscustomobject]@{
        Task        = $name
        State       = $state
        Decision    = ''
        CurrentExec = $execNow
        NewArgs     = ''
        Note        = ''
    }

    # 1) Already on pythonw -> settings only
    if ($execNow -and ($execNow -like '*pythonw*')) {
        $entry.Decision = 'SETTINGS_ONLY (already pythonw)'
        $report += $entry
        continue
    }

    # 2) Explicit skip list -> settings only
    if ($settingsOnly -contains $name) {
        $entry.Decision = 'SETTINGS_ONLY (manual: complex wrapper)'
        $entry.Note     = 'Action left alone'
        $report += $entry
        continue
    }

    # 3) In migration plan -> introspect wrapper
    if ($plan.Contains($name)) {
        $wrapperRel = $plan[$name]
        $wrapperAbs = Join-Path $BasePath $wrapperRel
        $inv        = Get-PythonInvocationFromWrapper -WrapperPath $wrapperAbs

        switch ($inv.Status) {
            'MISSING' {
                $entry.Decision = 'SKIP_NO_WRAPPER'
                $entry.Note     = "Wrapper file not found: $wrapperAbs"
            }
            'EMPTY' {
                $entry.Decision = 'SKIP_EMPTY_WRAPPER'
                $entry.Note     = "Wrapper empty: $wrapperAbs"
            }
            'NO_PY' {
                $entry.Decision = 'SKIP_NO_PY'
                $entry.Note     = "Wrapper has no 'python <script>.py' line: $wrapperRel"
            }
            'MULTI' {
                $entry.Decision = 'SKIP_MULTI_STEP'
                $entry.Note     = "Wrapper has $($inv.Count) python invocations: $($inv.Lines)"
            }
            'OK' {
                $entry.Decision = 'MIGRATE_TO_PYTHONW'
                $entry.NewArgs  = if ($inv.Args) { "$($inv.Script) $($inv.Args)" } else { $inv.Script }
                $entry.Note     = "Wrapper: $wrapperRel"
            }
        }
        $report += $entry
        continue
    }

    # 4) Not in plan and not pythonw -> review
    $entry.Decision = 'UNHANDLED (review)'
    $entry.Note     = 'Not in migration plan; only settings will be tightened.'
    $report += $entry
}

# ---- Print plan
Write-Host ""
$report | Sort-Object Decision, Task | Format-Table -AutoSize -Wrap Task, State, Decision, NewArgs, Note | Out-String | Write-Host

$migrateCount     = ($report | Where-Object { $_.Decision -eq 'MIGRATE_TO_PYTHONW' }).Count
$settingsOnlyCount = ($report | Where-Object { $_.Decision -like 'SETTINGS_ONLY*' -or $_.Decision -like 'SKIP_*' -or $_.Decision -like 'UNHANDLED*' }).Count
Write-Host "[SUMMARY] MIGRATE: $migrateCount   |   SETTINGS-ONLY/SKIP: $settingsOnlyCount" -ForegroundColor Yellow

# ---- DRY-RUN exit
if (-not $Apply) {
    Write-Host ""
    Write-Host "[DRY-RUN] Nothing changed. Re-run with -Apply to commit." -ForegroundColor Yellow
    return
}

# ---- Apply phase
Write-Host ""
Write-Host "[APPLY] Committing changes..." -ForegroundColor Green

foreach ($entry in $report) {
    $name = $entry.Task

    # Backup current task XML
    try {
        $xml = Export-ScheduledTask -TaskName $name
        $backupFile = Join-Path $backupDir "$name.xml"
        $xml | Out-File -FilePath $backupFile -Encoding utf8
        Write-Host "[BACKUP] $name -> $backupFile" -ForegroundColor DarkGray
    } catch {
        Write-Warning "[BACKUP-FAIL] $name : $_"
        continue
    }

    # Build new settings
    $settings = New-MerdianSettings

    try {
        if ($entry.Decision -eq 'MIGRATE_TO_PYTHONW') {
            $newAction = New-ScheduledTaskAction `
                -Execute $PythonwExe `
                -Argument $entry.NewArgs `
                -WorkingDirectory $BasePath
            Set-ScheduledTask -TaskName $name -Action $newAction -Settings $settings | Out-Null
            Write-Host "[APPLY] $name : action -> pythonw.exe $($entry.NewArgs) ; Hidden+IgnoreNew" -ForegroundColor Green
        } else {
            Set-ScheduledTask -TaskName $name -Settings $settings | Out-Null
            Write-Host "[APPLY] $name : settings tightened (Hidden + IgnoreNew)" -ForegroundColor Cyan
        }
    } catch {
        Write-Warning "[APPLY-FAIL] $name : $_"
    }
}

Write-Host ""
Write-Host "[DONE] Migration complete. Backups in $backupDir" -ForegroundColor Green
Write-Host "       Rollback single task: Register-ScheduledTask -Xml (Get-Content `"$backupDir\<name>.xml`" -Raw) -TaskName <name> -Force" -ForegroundColor Gray
