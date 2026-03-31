@echo off
setlocal

cd /d C:\GammaEnginePython

if not exist logs mkdir logs

echo ================================================== >> logs\run_market_spot_session_markers_once.log
echo TASK START %date% %time% >> logs\run_market_spot_session_markers_once.log
echo ================================================== >> logs\run_market_spot_session_markers_once.log

python C:\GammaEnginePython\build_market_spot_session_markers.py >> logs\run_market_spot_session_markers_once.log 2>&1

echo TASK END %date% %time% >> logs\run_market_spot_session_markers_once.log
echo. >> logs\run_market_spot_session_markers_once.log
