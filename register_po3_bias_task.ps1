# register_po3_bias_task.ps1
# ENH-75: Register MERDIAN_PO3_SessionBias_1005 in Windows Task Scheduler

$TaskName  = "MERDIAN_PO3_SessionBias_1005"
$ScriptDir = "C:\GammaEnginePython"
$BatFile   = "$ScriptDir\run_po3_session_bias_once.bat"
$LogDir    = "$ScriptDir\logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
    Write-Host "Created log directory: $LogDir"
}

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "10:05AM"

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`""

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Trigger   $trigger `
    -Action    $action `
    -Settings  $settings `
    -Principal $principal `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered:  $TaskName"
Write-Host "Next run:    $($info.NextRunTime)"
