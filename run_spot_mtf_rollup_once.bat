@echo off
REM -------------------------------------------------------------------------
REM run_spot_mtf_rollup_once.bat
REM
REM Wrapper for the daily 5m/15m spot-bar rollup. Invoked by Task Scheduler
REM task MERDIAN_Spot_MTF_Rollup_1600 at 16:00 IST Mon-Fri.
REM
REM Pattern matches existing MERDIAN tasks (run_market_close_capture_once.bat,
REM run_post_market_capture_once.bat). Logs go to logs\task_output.log via
REM the calling task's redirect.
REM
REM TD-019 / TD-023 closure: replaces the previous "no automation, manual
REM run only" state. ENH-71 instrumentation in build_spot_bars_mtf.py
REM ensures every invocation surfaces in script_execution_log.
REM -------------------------------------------------------------------------

cd /d "C:\GammaEnginePython"

echo [%DATE% %TIME%] === MERDIAN_Spot_MTF_Rollup_1600 START ===
python build_spot_bars_mtf.py
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] === MERDIAN_Spot_MTF_Rollup_1600 END (exit=%RC%) ===

exit /b %RC%
