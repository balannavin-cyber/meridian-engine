# patch_ict_task_add_hourly.ps1 v2
# Inserts --timeframe H run BEFORE exit /b line in run_ict_htf_zones_daily.bat

$BatFile = "C:\GammaEnginePython\run_ict_htf_zones_daily.bat"
$content = Get-Content $BatFile -Raw

if ($content -like "*--timeframe H*") {
    Write-Host "Already patched."
    exit 0
}

$hourly_line = "python build_ict_htf_zones.py --timeframe H >> logs\task_output.log 2>&1`r`n"
$content = $content -replace "exit /b %RC%", ($hourly_line + "exit /b %RC%")

[System.IO.File]::WriteAllText($BatFile, $content)
Write-Host "Patched: $BatFile"
Get-Content $BatFile
