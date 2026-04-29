# register_ws_feed_task.ps1
# Registers MERDIAN_WS_Feed_0900 -- starts ws_feed_zerodha.py at 09:00 IST Mon-Fri

$TaskName  = "MERDIAN_WS_Feed_0900"
$ScriptDir = "C:\GammaEnginePython"
$LogDir    = "$ScriptDir\logs"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Write the bat launcher
$BatContent = "@echo off`r`ncd /d C:\GammaEnginePython`r`n`"C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe`" ws_feed_zerodha.py >> logs\ws_feed_zerodha.log 2>&1`r`n"
$BatFile = "$ScriptDir\run_ws_feed_zerodha.bat"
[System.IO.File]::WriteAllText($BatFile, $BatContent)
Write-Host "BAT written: $BatFile"

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "09:00AM"

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`""

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 8) `
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
Write-Host "BAT file:    $BatFile"
