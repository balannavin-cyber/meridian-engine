@echo off
REM ============================================================================
REM run_ict_htf_zones_daily.bat
REM ----------------------------------------------------------------------------
REM MERDIAN F3 - daily ICT HTF zone refresh
REM Wraps build_ict_htf_zones.py --timeframe both
REM Triggered by Task Scheduler MERDIAN_ICT_HTF_Zones_0845
REM   Daily Mon-Fri 08:45 IST
REM Closes TD-017 (build_ict_htf_zones.py had no scheduled invocation)
REM ENH-71 instrumented; surfaces in script_execution_log
REM Logs appended to logs\task_output.log (mirrors existing convention)
REM Registered Session 11 (2026-04-28)
REM ============================================================================

cd /d C:\GammaEnginePython

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

if not exist logs mkdir logs

echo. >> logs\task_output.log
echo === %DATE% %TIME% MERDIAN_ICT_HTF_Zones_0845 START === >> logs\task_output.log

python build_ict_htf_zones.py --timeframe both >> logs\task_output.log 2>&1
set RC=%ERRORLEVEL%

echo === %DATE% %TIME% MERDIAN_ICT_HTF_Zones_0845 END (rc=%RC%) === >> logs\task_output.log

python build_ict_htf_zones.py --timeframe H >> logs\task_output.log 2>&1

exit /b %RC%

