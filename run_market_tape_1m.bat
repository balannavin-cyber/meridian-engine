@'
@echo off
setlocal

cd /d C:\gammaenginepython

if not exist logs mkdir logs

echo ================================================== >> logs\run_market_tape_1m.log
echo TASK START %date% %time% >> logs\run_market_tape_1m.log
echo ================================================== >> logs\run_market_tape_1m.log

python C:\gammaenginepython\run_market_tape_1m.py >> logs\run_market_tape_1m.log 2>&1

echo TASK END %date% %time% >> logs\run_market_tape_1m.log
echo. >> logs\run_market_tape_1m.log

endlocal
'@ | Set-Content C:\gammaenginepython\run_market_tape_1m.bat