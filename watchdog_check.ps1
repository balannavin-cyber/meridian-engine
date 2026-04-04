# MERDIAN Watchdog — checks if supervisor process is alive
# Runs every 5 minutes via MERDIAN_Watchdog scheduled task
# Only acts during market hours per trading_calendar

$BASE_DIR = "C:\GammaEnginePython"
$LOG = "$BASE_DIR\logs\watchdog.log"
$ENV_FILE = "$BASE_DIR\.env"

function Write-Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $LOG -Value $line
}

# Check trading calendar — only act if today is a trading day
$calendar_file = "$BASE_DIR\trading_calendar.json"
if (Test-Path $calendar_file) {
    $today = (Get-Date).ToUniversalTime().AddHours(5).AddMinutes(30).ToString("yyyy-MM-dd")
    $calendar = Get-Content $calendar_file | ConvertFrom-Json
    $today_entry = $calendar | Where-Object { $_.trade_date -eq $today }
    if (-not $today_entry -or $today_entry.is_open -eq $false) {
        Write-Log "SKIP - trading_calendar says today ($today) is not a trading day"
        exit 0
    }
}

# Only act during market hours 09:00-15:35 IST
$ist_now = (Get-Date).ToUniversalTime().AddHours(5).AddMinutes(30)
$market_start = $ist_now.Date.AddHours(9)
$market_end   = $ist_now.Date.AddHours(15).AddMinutes(35)
if ($ist_now -lt $market_start -or $ist_now -gt $market_end) {
    Write-Log "SKIP - outside market hours ($($ist_now.ToString('HH:mm')) IST)"
    exit 0
}

# Load .env for Telegram
$env_vars = @{}
Get-Content $ENV_FILE | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
        $env_vars[$matches[1].Trim()] = $matches[2].Trim()
    }
}
$BOT_TOKEN = $env_vars["TELEGRAM_BOT_TOKEN"]
$CHAT_ID   = $env_vars["TELEGRAM_CHAT_ID"]

function Send-Telegram($msg) {
    if ($BOT_TOKEN -and $CHAT_ID) {
        $url = "https://api.telegram.org/bot$BOT_TOKEN/sendMessage"
        $body = @{ chat_id = $CHAT_ID; text = $msg } | ConvertTo-Json
        Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json" -ErrorAction SilentlyContinue
    }
}

# Check if supervisor is running
$supervisor = Get-Process -Name python* -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*gamma_engine_supervisor*" }

if ($supervisor) {
    Write-Log "OK - supervisor running (PID $($supervisor.Id))"
} else {
    Write-Log "ALERT - supervisor not found during market hours. Restarting."
    Send-Telegram "⚠️ MERDIAN WATCHDOG: supervisor not found during market hours. Restarting now."
    Start-ScheduledTask -TaskName "MERDIAN_Intraday_Supervisor_Start"
    Write-Log "Restart triggered."
}
