@echo off
setlocal

cd /d C:\gammaenginepython

if not exist logs mkdir logs

echo ================================================== >> logs\run_merdian_state_stack_once.log
echo TASK START %date% %time% >> logs\run_merdian_state_stack_once.log
echo ================================================== >> logs\run_merdian_state_stack_once.log

python C:\gammaenginepython\run_merdian_state_stack_once.py >> logs\run_merdian_state_stack_once.log 2>&1

echo TASK END %date% %time% >> logs\run_merdian_state_stack_once.log
echo. >> logs\run_merdian_state_stack_once.log

endlocal
