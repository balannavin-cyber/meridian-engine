# start_supervisor_clean.ps1
# Kills any existing gamma_engine_supervisor.py process before starting a new one.
# Used by MERDIAN_Intraday_Supervisor_Start scheduled task.

$BASE = "C:\GammaEnginePython"
$LOG  = "$BASE\logs\supervisor_start.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $msg" | Out-File $LOG -Append -Encoding utf8
    Write-Host "[$ts] $msg"
}

Log "=== Supervisor clean start ==="

# Find and kill any Python process running gamma_engine_supervisor.py
$existing = Get-WmiObject Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*gamma_engine_supervisor*" }

foreach ($proc in $existing) {
    Log "Killing old supervisor PID=$($proc.ProcessId) started=$($proc.CreationDate)"
    try {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        Log "Killed PID=$($proc.ProcessId)"
    } catch {
        Log "Failed to kill PID=$($proc.ProcessId): $_"
    }
}

if (-not $existing) {
    Log "No existing supervisor process found"
}

Start-Sleep -Seconds 2

# Set encoding and start fresh supervisor
$env:PYTHONIOENCODING = "utf-8"
$python = "python"

Log "Starting fresh supervisor..."
Start-Process -FilePath $python `
    -ArgumentList "$BASE\gamma_engine_supervisor.py" `
    -WorkingDirectory $BASE `
    -WindowStyle Hidden `
    -NoNewWindow

Log "Supervisor launched"
