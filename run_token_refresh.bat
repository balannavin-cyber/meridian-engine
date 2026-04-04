@echo off
cd /d C:\GammaEnginePython
python refresh_dhan_token.py >> logs\dhan_token_refresh.log 2>&1
if %ERRORLEVEL% EQU 0 (
    python sync_token_to_aws.py >> logs\dhan_token_refresh.log 2>&1
)
