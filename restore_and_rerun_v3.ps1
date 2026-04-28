# ============================================================================
# restore_and_rerun_v3.ps1
# ----------------------------------------------------------------------------
# F3 / Path A helper.
#
# Restores build_ict_htf_zones.py from its .pre_f3.bak and re-runs the v3
# patch. The restore step makes target byte-identical to the backup, then
# v3's "reuse existing backup" branch triggers (since byte-identical), so
# the backup file is preserved throughout -- if v3 fails for any reason
# the original is still on disk.
#
# Usage (from C:\GammaEnginePython):
#   .\restore_and_rerun_v3.ps1
# ============================================================================

$ErrorActionPreference = "Stop"

$Target = "build_ict_htf_zones.py"
$Backup = "build_ict_htf_zones.py.pre_f3.bak"
$Patch  = "fix_f3_instrument_build_ict_htf_zones_v3.py"

Write-Host "F3 Path A: restore target from backup, run v3 patch"
Write-Host "(backup preserved throughout; v3 reuses it via byte-identical match)"
Write-Host ""

if (-not (Test-Path $Backup)) {
    Write-Host "ERROR: backup not found at $Backup"
    Write-Host "  Cannot restore. Aborting."
    exit 1
}
if (-not (Test-Path $Patch)) {
    Write-Host "ERROR: v3 patch script not found at $Patch"
    Write-Host "  Save fix_f3_instrument_build_ict_htf_zones_v3.py here first."
    exit 1
}
if (-not (Test-Path $Target)) {
    Write-Host "ERROR: target not found at $Target"
    exit 1
}

Write-Host ("Step 1/2: restoring {0} from {1}..." -f $Target, $Backup)
Copy-Item -Force -Path $Backup -Destination $Target
$tSize = (Get-Item $Target).Length
$bSize = (Get-Item $Backup).Length
if ($tSize -ne $bSize) {
    Write-Host ("ERROR: post-restore size mismatch (target={0}, backup={1})" -f $tSize, $bSize)
    exit 1
}
Write-Host ("  OK: target restored to {0} bytes (matches backup)" -f $tSize)
Write-Host ""

Write-Host "Step 2/2: running v3 patch..."
Write-Host ""
python $Patch
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "F3 Path A complete. Next: smoke test"
    Write-Host "  python build_ict_htf_zones.py --dry-run"
} else {
    Write-Host ("v3 exited rc={0}. Inspect output above. Backup is at {1}." -f $rc, $Backup)
}
exit $rc
