@echo off
REM ============================================================================
REM run_ict_htf_zones_daily.bat  (TD-065 v2 fix)
REM ----------------------------------------------------------------------------
REM MERDIAN F3 - daily ICT HTF zone refresh
REM Wraps build_ict_htf_zones.py for W+D and H zones (separate calls required).
REM Triggered by Task Scheduler MERDIAN_ICT_HTF_Zones_0845
REM   Daily Mon-Fri 08:45 IST
REM Closes TD-017 (build_ict_htf_zones.py had no scheduled invocation)
REM ENH-71 instrumented; surfaces in script_execution_log
REM Logs appended to logs\task_output.log
REM Registered Session 11 (2026-04-28); fixed Session 18 (2026-05-04, TD-065)
REM
REM TWO INVOCATIONS REQUIRED -- VERIFIED FROM SOURCE:
REM   build_ict_htf_zones.py L649-651:
REM     do_weekly = args.timeframe in ("W", "both")
REM     do_daily  = args.timeframe in ("D", "both")
REM     do_1h     = args.timeframe == "H"        <-- H ONLY when explicitly H
REM   So `--timeframe both` does NOT include H. H needs its own call.
REM
REM TD-065 v2 FIXES (Session 18, 2026-05-04):
REM   1. Original bat captured rc AFTER first call but BEFORE second call,
REM      so any failure in the H-only call exited rc=0 (silent fail).
REM      Now: each call has its own rc captured, both logged.
REM   2. Wrapper exits with WORST rc -- non-zero if either call failed.
REM   3. Per-call START/END markers so log readers can tell which call failed.
REM ============================================================================

cd /d C:\GammaEnginePython

set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

if not exist logs mkdir logs

echo. >> logs\task_output.log
echo === %DATE% %TIME% MERDIAN_ICT_HTF_Zones_0845 START === >> logs\task_output.log

REM ---- Call 1: W+D zones ----
echo --- %DATE% %TIME% [WD] start --- >> logs\task_output.log
python build_ict_htf_zones.py --timeframe both >> logs\task_output.log 2>&1
set RC_WD=%ERRORLEVEL%
echo --- %DATE% %TIME% [WD] end (rc=%RC_WD%) --- >> logs\task_output.log

REM ---- Call 2: H zones ----
echo --- %DATE% %TIME% [H] start --- >> logs\task_output.log
python build_ict_htf_zones.py --timeframe H >> logs\task_output.log 2>&1
set RC_H=%ERRORLEVEL%
echo --- %DATE% %TIME% [H] end (rc=%RC_H%) --- >> logs\task_output.log

REM ---- Final rc: worst of the two ----
set RC=%RC_WD%
if %RC_H% GTR %RC% set RC=%RC_H%

echo === %DATE% %TIME% MERDIAN_ICT_HTF_Zones_0845 END (rc_wd=%RC_WD% rc_h=%RC_H% final=%RC%) === >> logs\task_output.log

exit /b %RC%
