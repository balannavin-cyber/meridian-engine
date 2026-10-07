#!/usr/bin/env bash
# S90 / AM-1 — every offline check in one command. No database, no network.
#   ( ulimit -v 700000; bash tests/run_offline.sh )   -> exit 0 only if all pass
# NOT any hour, and not without a memory ceiling: see the rule 23 guard below. Exit 2 is a
# refusal to run (nothing was tested); exit 1 is a real test failure.
set -uo pipefail
cd "$(dirname "$0")/.."

# ---- CLAUDE.md rule 23 guard (ruling S91-A) — no override flag ---------------------------
# Two refusals, each for its own reason:
#   unlimited RLIMIT_AS -> a memory regression OOM-kills the box instead of failing the suite
#                          (TD-S91-NEW-7: two kills at 08:51 and 08:58 IST on 2026-10-07)
#   08:30 <= t < 15:40 IST, Mon-Fri -> the suite contends with the live capture chain
# The window is half-open at the top, so the suite becomes runnable AT 15:40 — that is the
# post-15:40 run TD-S91-NEW-7 owes. A holiday inside the window waits for the evening.
rule23_guard() {
  if [ "$(ulimit -v)" = "unlimited" ]; then
    echo "REFUSED: rule 23 — run under ( ulimit -v 700000; … )"
    return 2
  fi
  local ist dow hhmm
  ist=$(TZ=Asia/Kolkata date +%u/%H%M)
  dow=${ist%%/*}
  hhmm=$((10#${ist##*/}))
  if [ "$dow" -le 5 ] && [ "$hhmm" -ge 830 ] && [ "$hhmm" -lt 1540 ]; then
    echo "REFUSED: rule 23 — fixture suite blocked 08:30–15:40 IST on weekdays"
    return 2
  fi
  return 0
}
rule23_guard || exit $?

rc=0
echo "== 1/9 contract runner unit tests";   python3 tests/test_check_contracts_shadow.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 2/9 seeded defects on golden day"; python3 tests/replay/test_replay_seeded.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 3/9 replay vs pinned statuses";    python3 tests/replay/replay_contracts.py --check | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 4/9 ledger child runs (S90_CHILD_RUN)"; python3 tests/test_execution_log_child.py 2>/dev/null | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 5/9 CAS close slot pick (S90_CAS_SLOT_PICK)"; python3 tests/test_cas_close_slot_pick.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 6/9 CAS recon auto-correct (two sources)"; python3 tests/test_cas_recon_autocorrect.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 7/9 cycle-history ts fraction widths (ENH-133 _ist_date)"; python3 tests/test_cycle_history_ts_parse.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S91: TD-S91-NEW-2 site 2 (marker writer parse_ts) and the orchestrator-monitor alert
# gate. Both are pure-Python, no fixtures and no golden days, so neither contributes to
# the rule 23 memory ceiling -- they are in this suite for the single-command property.
echo "== 8/9 marker writer ts fraction widths (TD-S91-NEW-2 site 2)"; python3 tests/test_marker_ts_parse.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 9/9 orchestrator monitor alert gate + dedupe"; python3 tests/test_monitor_orchestrator_gate.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
exit $rc
