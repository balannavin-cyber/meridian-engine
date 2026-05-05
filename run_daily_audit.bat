@echo off
cd /d C:\GammaEnginePython
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
if not exist logs mkdir logs
echo. >> logs\task_output.log
echo === %DATE% %TIME% MERDIAN_Daily_Audit START === >> logs\task_output.log
python merdian_daily_audit.py >> logs\task_output.log 2>&1
set RC=%ERRORLEVEL%
echo === %DATE% %TIME% MERDIAN_Daily_Audit END (rc=%RC%) === >> logs\task_output.log
exit /b %RC%
