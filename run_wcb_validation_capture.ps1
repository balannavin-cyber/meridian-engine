$ErrorActionPreference = "Stop"

Write-Host "========================================================================"
Write-Host "MERDIAN - WCB Validation Capture Runner"
Write-Host "========================================================================"
Write-Host ""

Write-Host "[1/6] Building WCB snapshot for NIFTY..."
python .\build_wcb_snapshot_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_wcb_snapshot_local.py NIFTY failed" }
Write-Host ""

Write-Host "[2/6] Building WCB snapshot for SENSEX..."
python .\build_wcb_snapshot_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_wcb_snapshot_local.py SENSEX failed" }
Write-Host ""

Write-Host "[3/6] Building market state for NIFTY..."
python .\build_market_state_snapshot_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_market_state_snapshot_local.py NIFTY failed" }
Write-Host ""

Write-Host "[4/6] Building market state for SENSEX..."
python .\build_market_state_snapshot_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_market_state_snapshot_local.py SENSEX failed" }
Write-Host ""

Write-Host "[5/6] Building trade signal for NIFTY..."
python .\build_trade_signal_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_trade_signal_local.py NIFTY failed" }
Write-Host ""

Write-Host "[6/6] Building trade signal for SENSEX..."
python .\build_trade_signal_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_trade_signal_local.py SENSEX failed" }
Write-Host ""

Write-Host "========================================================================"
Write-Host "MERDIAN - WCB Validation Capture Runner completed successfully"
Write-Host "========================================================================"