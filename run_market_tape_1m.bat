@echo off
setlocal

cd /d C:\GammaEnginePython

if not exist logs mkdir logs

set "PYTHON_EXE=C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe"
set "LOG_FILE=C:\GammaEnginePython\logs\run_market_tape_1m.log"

echo ================================================== >> "%LOG_FILE%"
echo TASK START %date% %time% >> "%LOG_FILE%"
echo ================================================== >> "%LOG_FILE%"

"%PYTHON_EXE%" -u C:\GammaEnginePython\run_market_tape_1m.py >> "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo EXIT CODE %EXIT_CODE% >> "%LOG_FILE%"
echo TASK END %date% %time% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

endlocal & exit /b %EXIT_CODE%