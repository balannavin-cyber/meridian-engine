$ErrorActionPreference = "Stop"

$baseDir = "C:\gammaenginepython"
$logDir  = Join-Path $baseDir "logs"
$logPath = Join-Path $logDir "start_merdian_intraday_supervisor_ps.log"
$supervisorScript = Join-Path $baseDir "gamma_engine_supervisor.py"
$stdoutLog = Join-Path $logDir "gamma_engine_supervisor.out.log"
$stderrLog = Join-Path $logDir "gamma_engine_supervisor.err.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

Add-Content -Path $logPath -Value "=================================================="
Add-Content -Path $logPath -Value ("PS LAUNCH REQUEST " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Add-Content -Path $logPath -Value "=================================================="

if (-not (Test-Path $supervisorScript)) {
    Add-Content -Path $logPath -Value "ERROR: Supervisor script not found: $supervisorScript"
    exit 1
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match 'gamma_engine_supervisor\.py'
}

if ($existing) {
    Add-Content -Path $logPath -Value "Supervisor already running. Skipping new launch."
    exit 0
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Add-Content -Path $logPath -Value "ERROR: python command not found in PATH."
    exit 1
}

$pythonExe = $pythonCmd.Source
Add-Content -Path $logPath -Value ("Using python: " + $pythonExe)

$proc = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList @($supervisorScript) `
    -WorkingDirectory $baseDir `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 2

$check = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(\.exe)?$' -and $_.CommandLine -match 'gamma_engine_supervisor\.py'
}

if ($check) {
    Add-Content -Path $logPath -Value ("Supervisor launched successfully. PID=" + $proc.Id)
    exit 0
} else {
    Add-Content -Path $logPath -Value "ERROR: Launch command issued but supervisor process not found after 2 seconds."
    exit 1
}