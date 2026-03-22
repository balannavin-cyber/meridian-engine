@echo off
setlocal

cd /d C:\gammaenginepython

if not exist logs mkdir logs

echo ================================================== >> logs\start_merdian_intraday_supervisor.log
echo LAUNCH REQUEST %date% %time% >> logs\start_merdian_intraday_supervisor.log
echo ================================================== >> logs\start_merdian_intraday_supervisor.log

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$found = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match 'gamma_engine_supervisor\.py' }; if ($found) { exit 99 } else { exit 0 }"

if %errorlevel%==99 (
    echo Supervisor already running. Skipping new launch. >> logs\start_merdian_intraday_supervisor.log
    exit /b 0
)

echo Starting gamma_engine_supervisor.py >> logs\start_merdian_intraday_supervisor.log
start "MERDIAN_SUPERVISOR" /min cmd /c "cd /d C:\gammaenginepython && python C:\gammaenginepython\gamma_engine_supervisor.py >> C:\gammaenginepython\logs\gamma_engine_supervisor.log 2>&1"

echo Supervisor launch command issued. >> logs\start_merdian_intraday_supervisor.log
exit /b 0