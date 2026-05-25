# diag_preopen_task.ps1
# Diagnose why MERDIAN_PreOpen LastTaskResult=1 on last fire (2026-05-01)
# Run as Administrator from C:\GammaEnginePython.

Write-Host "=== MERDIAN_PreOpen Task Diagnostics ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1] Task definition" -ForegroundColor Yellow
$task = Get-ScheduledTask -TaskName MERDIAN_PreOpen
$task | Format-List TaskName, State, Description
Write-Host "Action:" -ForegroundColor Yellow
$task.Actions | Format-List Execute, Arguments, WorkingDirectory
Write-Host "Trigger:" -ForegroundColor Yellow
$task.Triggers | Format-List Enabled, StartBoundary, DaysOfWeek

Write-Host "[2] Last run state" -ForegroundColor Yellow
$task | Get-ScheduledTaskInfo |
    Format-List LastRunTime, LastTaskResult, NextRunTime, NumberOfMissedRuns

Write-Host "[3] LastTaskResult decoder" -ForegroundColor Yellow
$ltr = ($task | Get-ScheduledTaskInfo).LastTaskResult
$decoded = switch ($ltr) {
    0 { "0x0 SUCCESS" }
    1 { "0x1 generic non-zero exit -- usually means the called script returned exit code 1, OR Python interpreter failed to launch" }
    2 { "0x2 file not found" }
    267011 { "0x41303 task has not yet run" }
    2147750687 { "0x41301 task already running (single-instance block)" }
    2147750671 { "0x41311 task service not running" }
    default { "unrecognized; raw=$ltr" }
}
Write-Host "  $ltr -> $decoded"

Write-Host "[4] Recent task event-log entries (last 20)" -ForegroundColor Yellow
try {
    Get-WinEvent -FilterHashtable @{
        LogName = 'Microsoft-Windows-TaskScheduler/Operational'
        StartTime = (Get-Date).AddDays(-7)
    } -ErrorAction Stop |
        Where-Object { $_.Message -match 'MERDIAN_PreOpen' } |
        Select-Object -First 20 TimeCreated, Id, LevelDisplayName, Message |
        Format-Table -Wrap -AutoSize
} catch {
    Write-Host "  Could not read event log: $_" -ForegroundColor DarkGray
}

Write-Host "[5] Is the wrapper script reachable?" -ForegroundColor Yellow
$exe = $task.Actions[0].Execute
$args = $task.Actions[0].Arguments
Write-Host "  Execute = $exe"
Write-Host "  Args    = $args"

# Try to extract the .py path from Arguments
$pyPath = $null
if ($args -match '([A-Za-z]:[\\/][^"]+\.py)') { $pyPath = $matches[1] }
elseif ($args -match '([^"\s]+\.py)')         { $pyPath = $matches[1] }
if ($pyPath) {
    Write-Host "  Wrapper .py path: $pyPath"
    if (Test-Path $pyPath) {
        Write-Host "    EXISTS" -ForegroundColor Green
    } else {
        Write-Host "    MISSING ON DISK" -ForegroundColor Red
    }
}

Write-Host "[6] Recent log files that might capture script output" -ForegroundColor Yellow
$logDir = "C:\GammaEnginePython\logs"
if (Test-Path $logDir) {
    Get-ChildItem $logDir -File |
        Where-Object { $_.Name -match '(premarket|preopen|pre_open|spot_1m|capture)' -or
                       $_.LastWriteTime -gt (Get-Date).AddDays(-7) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 10 |
        Format-Table Name, Length, LastWriteTime -AutoSize
} else {
    Write-Host "  $logDir does not exist" -ForegroundColor DarkGray
}

Write-Host "[7] Manual dry-run of the action (captures stdout/stderr)" -ForegroundColor Yellow
Write-Host "  Running: $exe $args" -ForegroundColor DarkGray
try {
    $p = Start-Process -FilePath $exe -ArgumentList $args `
        -RedirectStandardOutput "C:\GammaEnginePython\diagnostics\preopen_dryrun_stdout.txt" `
        -RedirectStandardError  "C:\GammaEnginePython\diagnostics\preopen_dryrun_stderr.txt" `
        -NoNewWindow -PassThru -Wait
    Write-Host "  Exit code: $($p.ExitCode)" -ForegroundColor $(if ($p.ExitCode -eq 0) { 'Green' } else { 'Red' })
    Write-Host "  --- stdout (last 30 lines) ---"
    if (Test-Path "C:\GammaEnginePython\diagnostics\preopen_dryrun_stdout.txt") {
        Get-Content "C:\GammaEnginePython\diagnostics\preopen_dryrun_stdout.txt" -Tail 30
    }
    Write-Host "  --- stderr (last 30 lines) ---"
    if (Test-Path "C:\GammaEnginePython\diagnostics\preopen_dryrun_stderr.txt") {
        Get-Content "C:\GammaEnginePython\diagnostics\preopen_dryrun_stderr.txt" -Tail 30
    }
} catch {
    Write-Host "  Manual run threw: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
