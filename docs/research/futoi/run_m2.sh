#!/bin/sh
# Phase 4: M2 (pre-registration section 4). Outcome-computing.
# Refuses to score unless the self-test passes and all four controls passed --
# both re-checked inside futoi_m2.py, not taken on trust from an earlier run.
#
# No pipeline carries the exit status: /bin/sh has no PIPESTATUS, and a `| tee`
# would report tee's success as the scorer's. The log is written by redirection
# and printed afterwards.
set -eu
cd "$(dirname "$0")/../../.."
D=docs/research/futoi
TS=$(date -u +%Y%m%d_%H%M)

echo "=== phase 4: M2 ==="
if [ -f "$D/STOPPED.md" ]; then
  echo "STOPPED.md is present -- a control failed. Refusing to score M2."
  exit 2
fi
rc=0
( ulimit -v 700000; python3 "$D/futoi_m2.py" --score ) > "$D/logs/m2_$TS.log" 2>&1 || rc=$?
cat "$D/logs/m2_$TS.log"
echo "m2 exit=$rc"
exit $rc
