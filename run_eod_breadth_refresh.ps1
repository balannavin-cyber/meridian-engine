$logFile = "C:\GammaEnginePython\logs\eod_breadth_refresh.log"
$python = "C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe"
$scriptDir = "C:\GammaEnginePython"

Add-Content $logFile "=================================================="
Add-Content $logFile "EOD BREADTH REFRESH START $(Get-Date)"
Add-Content $logFile "=================================================="

Set-Location $scriptDir

& $python run_equity_eod_until_done.py *>> $logFile

Add-Content $logFile "EOD BREADTH REFRESH END $(Get-Date)"
