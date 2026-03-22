$ErrorActionPreference = "Stop"

$base = "C:\GammaEnginePython"
$python = Join-Path $base ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

$logDir = Join-Path $base "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$logFile = Join-Path $logDir "run_iv_context_once.log"

"==================================================" | Out-File $logFile -Append -Encoding utf8
"IV CONTEXT TASK START $(Get-Date)" | Out-File $logFile -Append -Encoding utf8
"==================================================" | Out-File $logFile -Append -Encoding utf8

Push-Location $base
try {
    & $python ".\compute_iv_context_local.py" *>> $logFile
    if ($LASTEXITCODE -ne 0) {
        throw "compute_iv_context_local.py failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

"IV CONTEXT TASK END $(Get-Date)" | Out-File $logFile -Append -Encoding utf8
"" | Out-File $logFile -Append -Encoding utf8
