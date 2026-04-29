@echo off
REM run_po3_session_bias_once.bat
REM ENH-75: PO3 Live Session Bias Detection wrapper for Task Scheduler
REM Task: MERDIAN_PO3_SessionBias_1005  (Mon-Fri 10:05 IST)

cd /d C:\GammaEnginePython

"C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe" ^
    detect_po3_session_bias.py ^
    >> logs\po3_bias.log 2>&1
