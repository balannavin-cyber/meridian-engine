# start_supervisor_clean.ps1
# Kills any existing gamma_engine_supervisor.py process before starting a new one.
# Used by MERDIAN_Intraday_Supervisor_Start scheduled task.
$BASE   = "C:\GammaEnginePython"
$LOG    = "$BASE\logs\supervisor_start.log"
$PYTHON = "C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe"
$SCRIPT = "$BASE\gamma_engine_supervisor.py"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $msg" | Out-File $LOG -Append -Encoding utf8
    Write-Host "[$ts] $msg"
}

Log "=== Supervisor clean start ==="

# ── Kill any existing supervisor ──────────────────────────────────────
$existing = Get-WmiObject Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*gamma_engine_supervisor*" }

foreach ($proc in $existing) {
    Log "Killing old supervisor PID=$($proc.ProcessId)"
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

# ── Start fresh supervisor ────────────────────────────────────────────
# FIX R-05: -NoNewWindow and -WindowStyle cannot be used together.
# Use -NoNewWindow only (runs in background without a visible window).
$env:PYTHONIOENCODING = "utf-8"

Log "Starting fresh supervisor..."

$proc = Start-Process `
    -FilePath $PYTHON `
    -ArgumentList $SCRIPT `
    -WorkingDirectory $BASE `
    -NoNewWindow `
    -PassThru

Start-Sleep -Seconds 3

# ── Verify it actually started ────────────────────────────────────────
if ($proc -and -not $proc.HasExited) {
    Log "Supervisor launched OK — PID=$($proc.Id)"
} else {
    Log "ERROR — Supervisor process failed to start or exited immediately"
    exit 1
}
