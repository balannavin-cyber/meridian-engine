@echo off
setlocal

cd /d C:\GammaEnginePython

if not exist logs mkdir logs

echo ================================================== >> logs\run_post_market_capture_once.log
echo TASK START %date% %time% >> logs\run_post_market_capture_once.log
echo ================================================== >> logs\run_post_market_capture_once.log

python C:\GammaEnginePython\capture_market_spot_snapshot_local.py >> logs\run_post_market_capture_once.log 2>&1

echo TASK END %date% %time% >> logs\run_post_market_capture_once.log
echo. >> logs\run_post_market_capture_once.log
