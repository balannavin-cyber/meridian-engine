#!/bin/sh
# Phase 3: M1 (pre-registration section 3). Outcome-computing.
# Refuses to score unless the self-test passes and all four controls passed --
# both re-checked inside futoi_m1.py, not taken on trust from an earlier run.
set -eu
cd "$(dirname "$0")/../../.."
D=docs/research/futoi
TS=$(date -u +%Y%m%d_%H%M)

echo "=== phase 3: M1 ==="
if [ -f "$D/STOPPED.md" ]; then
  echo "STOPPED.md is present -- a control failed. Refusing to score M1."
  exit 2
fi
rc=0
( ulimit -v 700000; python3 "$D/futoi_m1.py" --score ) > "$D/logs/m1_$TS.log" 2>&1 || rc=$?
cat "$D/logs/m1_$TS.log"
echo "m1 exit=$rc"
exit $rc
