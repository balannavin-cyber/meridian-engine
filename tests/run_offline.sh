#!/usr/bin/env bash
# S90 / AM-1 — every offline check in one command. No database, no network.
# 12 steps as of S95. Every step's exit code is checked and ANY non-zero is a FAIL,
# including a step's own rule-23 refusal (exit 2) — a refusal is never a skip.
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
echo "== 1/12 contract runner unit tests";   python3 tests/test_check_contracts_shadow.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 2/12 seeded defects on golden day"; python3 tests/replay/test_replay_seeded.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 3/12 replay vs pinned statuses";    python3 tests/replay/replay_contracts.py --check | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 4/12 ledger child runs (S90_CHILD_RUN)"; python3 tests/test_execution_log_child.py 2>/dev/null | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 5/12 CAS close slot pick (S90_CAS_SLOT_PICK)"; python3 tests/test_cas_close_slot_pick.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 6/12 CAS recon auto-correct (two sources)"; python3 tests/test_cas_recon_autocorrect.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 7/12 cycle-history ts fraction widths (ENH-133 _ist_date)"; python3 tests/test_cycle_history_ts_parse.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S91: TD-S91-NEW-2 site 2 (marker writer parse_ts) and the orchestrator-monitor alert
# gate. Both are pure-Python, no fixtures and no golden days, so neither contributes to
# the rule 23 memory ceiling -- they are in this suite for the single-command property.
echo "== 8/12 marker writer ts fraction widths (TD-S91-NEW-2 site 2)"; python3 tests/test_marker_ts_parse.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 9/12 orchestrator monitor alert gate + dedupe"; python3 tests/test_monitor_orchestrator_gate.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S92: TD-S91-NEW-2 site 7 / TD-S91-NEW-6. core.ts_parse is the shared PostgREST
# timestamp parser; this exercises widths 0-6, Z, offsets, naive and malformed input,
# and the five real wire strings from 2026-10-08 including the rows[0] of that day's
# three DATA_ERROR basis runs. Pure Python, no fixtures, no golden day -- it adds
# nothing to the rule 23 memory ceiling.
echo "== 10/12 core.ts_parse shared ts parser (TD-S91-NEW-2 site 7)"; python3 tests/test_ts_parse_core.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S93: P6 / ENH-140 offline DEX recompute. UNLIKE steps 8-10 this one DOES load a golden
# day -- tests/golden/2026-10-01_SENSEX, 31,914 chain rows over 81 cycles -- so it is the
# first addition since S90 that moves this suite's memory profile, and it is the reason the
# rule 23 ceiling is not decoration. Wired in only after its first standalone pass
# (2026-10-09 17:45:28 IST); an unrun test in a single-command suite puts a test nobody has
# seen green in front of the next person who runs it.
#
# MEASURED 2026-10-09, 11 steps under ( ulimit -v 700000 ): peak RSS 293,000 kB for the
# whole suite, 110,856 kB for this step alone, wall 1:11 / 0.89 s. Stated as what it is --
# `ulimit -v` caps ADDRESS SPACE, not RSS, so these are not the quantity the ceiling
# constrains and they are not headroom. The evidence the ceiling is not breached is that the
# run exits 0 under it; RSS is recorded only so a future regression has a baseline to be
# compared against.
#
# A NON-ZERO EXIT IS A FAILURE HERE, INCLUDING 2, and that was PROVED rather than assumed:
# a copy of this file with step 11 replaced by a stub exiting 2 printed OFFLINE FAIL and
# exited 1. The test carries its own rule 23 guard and returns 2 in-window, which the
# `-eq 0` test below turns into rc=1 -- never a skip. In practice this suite's own guard
# refuses first and identically (both block Mon-Fri 08:30-15:40 IST), so the test's guard
# binds only when it is run standalone; the two agreeing is what makes a refusal here mean
# the suite was mis-invoked rather than that the clocks disagree.
#
# This step WRITES docs/research/s93_priority/p6/expected/dex_standing_book_1001_SENSEX.csv
# on every run. That path is gitignored (.gitignore:43 `*.csv`), so running the suite leaves
# no git noise -- but it is not a read-only step, unlike every other one here.
echo "== 11/12 DEX recompute vs golden day (S93 / ENH-140 P6)"; python3 tests/test_dex_recompute.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S95: P3a (roadmap P3 = R2.2 + R2.3, phase a). Offline invariants I1-I4 asserted, I5-I6 descriptive,
# on ALL six golden days -- the first step that loads every fixture, so it is the step the rule 23
# ceiling exists for. Read-only: it writes nothing. Wired in only after its standalone pass on the box
# (2026-10-10 12:02 IST, file hash f861b0a5, P3A PASS, exit 0), per the S93 precedent above.
# Its own seeded mutants run inside it; S95 fixed the PE-sign mutant, which had been a silent no-op
# (strike '72000.0' vs '72000' string compare, then a vendor-gap PE leg on 2026-08-27 NIFTY), and
# added MUTANT NOT APPLIED so an unchanged mutant can no longer pass as caught.
# MEASURED standalone 2026-10-10 under ( ulimit -v 700000 ): ~17 s, peak RSS 224,216 kB (workspace run).
echo "== 12/12 P3a invariants + independent recompute, six golden days (S95)"; python3 -I tests/test_p3a_invariants.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
exit $rc
