$ErrorActionPreference = "Stop"

Write-Host "========================================================================"
Write-Host "MERDIAN - Shadow Validation Capture Runner"
Write-Host "========================================================================"
Write-Host ""

Write-Host "[1/8] Building WCB snapshot for NIFTY..."
python .\build_wcb_snapshot_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_wcb_snapshot_local.py NIFTY failed" }
Write-Host ""

Write-Host "[2/8] Building WCB snapshot for SENSEX..."
python .\build_wcb_snapshot_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_wcb_snapshot_local.py SENSEX failed" }
Write-Host ""

Write-Host "[3/8] Building market state for NIFTY..."
python .\build_market_state_snapshot_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_market_state_snapshot_local.py NIFTY failed" }
Write-Host ""

Write-Host "[4/8] Building market state for SENSEX..."
python .\build_market_state_snapshot_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_market_state_snapshot_local.py SENSEX failed" }
Write-Host ""

Write-Host "[5/8] Building baseline trade signal for NIFTY..."
python .\build_trade_signal_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_trade_signal_local.py NIFTY failed" }
Write-Host ""

Write-Host "[6/8] Building baseline trade signal for SENSEX..."
python .\build_trade_signal_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_trade_signal_local.py SENSEX failed" }
Write-Host ""

Write-Host "[7/8] Building shadow signal for NIFTY..."
python .\build_shadow_signal_local.py NIFTY
if ($LASTEXITCODE -ne 0) { throw "build_shadow_signal_local.py NIFTY failed" }
Write-Host ""

Write-Host "[8/8] Building shadow signal for SENSEX..."
python .\build_shadow_signal_local.py SENSEX
if ($LASTEXITCODE -ne 0) { throw "build_shadow_signal_local.py SENSEX failed" }
Write-Host ""

Write-Host "========================================================================"
Write-Host "MERDIAN - Shadow Validation Capture Runner completed successfully"
Write-Host "Shadow policy currently active in build_shadow_signal_local.py:"
Write-Host "WCB_SHADOW_V2"
Write-Host "========================================================================"