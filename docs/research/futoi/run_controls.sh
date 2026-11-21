#!/bin/sh
# Phase 2: controls C1-C4 (pre-registration section 5).
# One command: pull hist_gamma_metrics for C3, re-run the self-test, then the
# controls. Exits 3 if any control fails, in which case STOPPED.md is written
# and nothing in sections 3, 4 or 7 is computed.
#
# No pipeline carries the controls' exit status: /bin/sh has no PIPESTATUS, and
# a `| tee` would report tee's success as the control's. The log is written by
# redirection and printed afterwards.
set -eu
cd "$(dirname "$0")/../../.."
ROQ=./bin/roq.sh
D=docs/research/futoi
TS=$(date -u +%Y%m%d_%H%M)

echo "=== phase 2: controls ==="
echo "--- chain extraction completeness ---"
have=$(cut -d, -f2 "$D/data/session_chain.csv" | tail -n +2 | sort -u | wc -l)
want=$(wc -l < "$D/data/sessions.txt")
echo "sessions in session_chain.csv: $have of $want"
if [ "$have" -lt "$want" ]; then
  echo "REFUSING to run controls on an incomplete extraction."
  exit 2
fi

echo "--- pulling hist_gamma_metrics for C3 ---"
{ printf "\\set lo '2025-04-01'\n\\set hi '2026-03-30'\n"; \
  cat "$D/sql/extract_gamma_metrics.sql"; } \
  | "$ROQ" > "$D/data/gamma_metrics.csv" 2> "$D/logs/extract_gamma_metrics.err"
echo "gamma_metrics rows: $(( $(wc -l < "$D/data/gamma_metrics.csv") - 1 ))"

echo "--- self-test (gates --score; Part 0 step 5) ---"
rc=0
( ulimit -v 700000; python3 "$D/futoi_selftest.py" ) > "$D/logs/selftest_$TS.log" 2>&1 || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "SELFTEST FAILED -- see $D/logs/selftest_$TS.log"
  tail -20 "$D/logs/selftest_$TS.log"
  exit 4
fi
tail -1 "$D/logs/selftest_$TS.log"

echo "--- controls C1-C4 ---"
rc=0
( ulimit -v 700000; python3 "$D/futoi_controls.py" ) > "$D/logs/controls_$TS.log" 2>&1 || rc=$?
cat "$D/logs/controls_$TS.log"
echo "controls exit=$rc"
exit $rc
