#!/usr/bin/env bash
# S90 / AM-1 — every offline check in one command. No database, no network.
# 27 steps as of S102. Every step's exit code is checked and ANY non-zero is a FAIL,
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
echo "== 1/27 contract runner unit tests";   python3 tests/test_check_contracts_shadow.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 2/27 seeded defects on golden day"; python3 tests/replay/test_replay_seeded.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 3/27 replay vs pinned statuses";    python3 tests/replay/replay_contracts.py --check | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 4/27 ledger child runs (S90_CHILD_RUN)"; python3 tests/test_execution_log_child.py 2>/dev/null | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 5/27 CAS close slot pick (S90_CAS_SLOT_PICK)"; python3 tests/test_cas_close_slot_pick.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 6/27 CAS recon auto-correct (two sources)"; python3 tests/test_cas_recon_autocorrect.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 7/27 cycle-history ts fraction widths (ENH-133 _ist_date)"; python3 tests/test_cycle_history_ts_parse.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S91: TD-S91-NEW-2 site 2 (marker writer parse_ts) and the orchestrator-monitor alert
# gate. Both are pure-Python, no fixtures and no golden days, so neither contributes to
# the rule 23 memory ceiling -- they are in this suite for the single-command property.
echo "== 8/27 marker writer ts fraction widths (TD-S91-NEW-2 site 2)"; python3 tests/test_marker_ts_parse.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 9/27 orchestrator monitor alert gate + dedupe"; python3 tests/test_monitor_orchestrator_gate.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S92: TD-S91-NEW-2 site 7 / TD-S91-NEW-6. core.ts_parse is the shared PostgREST
# timestamp parser; this exercises widths 0-6, Z, offsets, naive and malformed input,
# and the five real wire strings from 2026-10-08 including the rows[0] of that day's
# three DATA_ERROR basis runs. Pure Python, no fixtures, no golden day -- it adds
# nothing to the rule 23 memory ceiling.
echo "== 10/27 core.ts_parse shared ts parser (TD-S91-NEW-2 site 7)"; python3 tests/test_ts_parse_core.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
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
echo "== 11/27 DEX recompute vs golden day (S93 / ENH-140 P6)"; python3 tests/test_dex_recompute.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S95: P3a (roadmap P3 = R2.2 + R2.3, phase a). Offline invariants I1-I4 asserted, I5-I6 descriptive,
# on ALL six golden days -- the first step that loads every fixture, so it is the step the rule 23
# ceiling exists for. Read-only: it writes nothing. Wired in only after its standalone pass on the box
# (2026-10-10 12:02 IST, file hash f861b0a5, P3A PASS, exit 0), per the S93 precedent above.
# Its own seeded mutants run inside it; S95 fixed the PE-sign mutant, which had been a silent no-op
# (strike '72000.0' vs '72000' string compare, then a vendor-gap PE leg on 2026-08-27 NIFTY), and
# added MUTANT NOT APPLIED so an unchanged mutant can no longer pass as caught.
# MEASURED standalone 2026-10-10 under ( ulimit -v 700000 ): ~17 s, peak RSS 224,216 kB (workspace run).
# MEASURED full suite 2026-10-23 05:29 IST, 13 steps, ( ulimit -v 700000 ): wall 1:48, peak RSS 331,740 kB, exit 0.
echo "== 12/27 P3a invariants + independent recompute, six golden days (S95)"; python3 -I tests/test_p3a_invariants.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S98: S97-N / TD-S97-NEW-7 — the contract check's spot condition (09:15-15:15 IST window,
# 3-min threshold, clear-on-pass, `74b45ce`). Pure Python: requests.get and the state file are
# mocked, no fixtures and no golden day, so it adds nothing to the rule 23 memory ceiling --
# same class as steps 8-10, not steps 11-12.
#
# PLAIN `python3`, NOT step 12's `python3 -I`, and that is MEASURED not stylistic. `-I` implies
# -E/-s, which drops ~/.local/lib/python3.10/site-packages from sys.path; `dotenv` exists ONLY
# there, so under -I the dedupe path logs "state unavailable (No module named 'dotenv')" and
# three dedupe cells FAIL -- a failure about the interpreter flag, not about the contract check.
# Measured 2026-10-23 05:23 IST standalone under ( ulimit -v 700000 ): `-I` -> 3 FAIL, exit 1;
# plain -> ALL PASS, exit 0. Step 12 can use -I because test_p3a_invariants.py is stdlib-only.
#
# Appended AFTER step 12's pipeline-and-test pair, never between one and its test (TD-S93-NEW-1:
# the ${PIPESTATUS[0]} idiom is positional, so an insertion inside a pair silently disarms it).
echo "== 13/27 contract check spot condition (S97-N / TD-S97-NEW-7)"; python3 tests/test_contract_check_s97.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S99: S98-B / rulings S98-E, S98-E.1 -- the shadow runner's cycle wait (ts >= the 5-min cycle
# floor, poll 5 s, wait 120 s, timeout -> exit 1 SKIPPED_NO_INPUT). Pure Python: the runner is
# loaded from source with dotenv, the Supabase client, the execution log, the calendar gate and
# retry utils stubbed; no fixtures and no golden day -- same class as steps 8-10 and 13. Carries
# its own mutants M / R / Z. Targets the LIVE runner (repointed from the S98 dry-run copy, S99 A4).
# Plain `python3`, as step 13 (not measured under -I). Appended AFTER step 13, never inside a
# pair (TD-S93-NEW-1).
echo "== 14/27 shadow runner cycle wait (S98-B / TD-S97-NEW-4)"; python3 tests/test_runner_cycle_wait.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S99: R2 / TD-S97-NEW-9, -10 (rulings S99-H, S99-I) -- the WCB writer's no-input guard: write only
# when the breadth ts is <= 10 min old AND >= 1 constituent is priced, else exit 0 SKIPPED_NO_INPUT.
# Pure Python: the writer is loaded from source with the Supabase client, the execution log and retry
# utils stubbed; core.ts_parse is real. No fixtures, no golden day -- same class as steps 8-10, 13, 14.
# Carries its own mutants M1-M3. Appended AFTER step 14, never inside a pair (TD-S93-NEW-1).
echo "== 15/27 WCB writer no-input guard (S99 R2 / TD-S97-NEW-9)"; python3 tests/test_wcb_no_input.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100_R3_HUNG: R3 / TD-S97-NEW-3 -- the orchestrator monitor's hung-run probe (unfinished ledger rows
# started more than HUNG_MIN = 6 min ago today -> CRITICAL under its own key). Pure Python: the monitor is
# loaded from source with Telegram blanked and every ledger read injected or `requests.get` mocked. Carries
# its own mutants M1-M5. Appended AFTER step 15, never inside a pair (TD-S93-NEW-1).
echo "== 16/27 orchestrator monitor hung-run probe (S100 R3 / TD-S97-NEW-3)"; python3 tests/test_monitor_hung_run.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100_R42_UNION: R42 (ruling S100-C) -- the monitor window is the union of every runner crontab line when
# that union is one uniform-step run on one set of weekdays (else a loud fallback). Parses the committed
# docs/registers/aws_crontab.txt against an independent expansion. Carries its own mutants M1-M3.
# Appended AFTER step 16, never inside a pair (TD-S93-NEW-1).
echo "== 17/27 orchestrator monitor window = union of runner lines (S100 R42)"; python3 tests/test_monitor_window_union.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100_R4_PROBE: R4 (ruling S100-E) -- preopen_probe.py, the 09:09 IST broker access check (Dhan expiry list,
# LTP, intraday; Kite profile). Pure Python: every broker, sender, calendar and ledger is a stub. Carries its own
# mutants M1-M6. Appended AFTER step 17, never inside a pair (TD-S93-NEW-1).
echo "== 18/27 pre-open broker access probe (S100 R4)"; python3 tests/test_preopen_probe.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100_WSFEED_RETRY: R4 / TD-S80-NEW-17 (ruling S100-F) -- the wsfeed retry script and the deduped preflight /
# OnFailure alert. Runs the real bash scripts in a temp engine dir with systemctl, curl, date and python3 stubbed.
# Carries its own mutants M1-M4. Appended AFTER step 18, never inside a pair (TD-S93-NEW-1).
echo "== 19/27 wsfeed retry + deduped preflight alert (S100 R4 / TD-S80-NEW-17)"; python3 tests/test_wsfeed_retry.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100_R40_BREADTH: R40 (ruling S100-I) -- ingest_breadth_from_ticks.py: holiday gate, no ticks -> no row and
# exit 0, ledger via core.execution_log. Writer loaded from source with supabase / dotenv / ledger / calendar stubbed.
# Carries its own mutants M1-M3 and a no-op control M4. Appended AFTER step 19 (TD-S93-NEW-1).
echo "== 20/27 breadth-from-ticks writer (S100 R40)"; python3 tests/test_breadth_from_ticks.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100_CHAIN_5XX: TD-S81-NEW-11 -- the chain ingest retries a Dhan 5xx at most twice per call (429 unchanged, auth
# fails fast). Predicates taken from the ingest source by ast, driven through the real retry_call. Mutants M1-M3.
# Appended AFTER step 20, never inside a pair (TD-S93-NEW-1).
echo "== 21/27 chain ingest Dhan 5xx retry (S100 / TD-S81-NEW-11)"; python3 tests/test_chain_dhan_retry.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100 R19 (TD-S97-NEW-11): the daily breadth builder fills a complete EOD date that a later date overtook
# before it was built (10-08, 10-15). Builder loaded from source, HTTP helpers stubbed. Mutants M1-M3.
# Appended AFTER step 21, never inside a pair (TD-S93-NEW-1).
echo "== 22/27 daily breadth gap-fill (S100 R19 / TD-S97-NEW-11)"; python3 tests/test_breadth_daily_gapfill.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S100-M (b): SUBSCRIPTION_LAPSED -- Dhan 806 / DH-902 is a lapsed plan, not a dead token (chain ingest, spot 1m,
# CAS close, pre-open probe, core, alert daemon, CHECK DDL). Real 10-21 error texts. Mutants M1-M6.
# Appended AFTER step 22, never inside a pair (TD-S93-NEW-1).
echo "== 23/27 Dhan plan lapse -> SUBSCRIPTION_LAPSED (S100-M / TD-S97-NEW-21 b)"; python3 tests/test_subscription_lapsed.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S101_IMPORT_PURITY: retail scope §1.3 -- `import merdian_compute` reads no env, imports no
# supabase / requests / dotenv / core, opens no socket (empty-env -I child with three tripwires),
# then calls one exported function. Mutants M1-M6, each must trip its own wire. Pure Python, no
# fixtures, no golden day. Appended AFTER step 23, never inside a pair (TD-S93-NEW-1).
echo "== 24/27 merdian_compute import purity (S101 / retail scope §1.3)"; python3 tests/test_merdian_compute_import_purity.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S101_CONTRACT: the surface retail depends on -- 26 signatures + GammaMetricsResult field order,
# and the Board core recomputed from each golden chain by merdian_compute ALONE vs the value production
# wrote (313 rows x 11 fields; pin_risk_score on the 291 rows with a full in-day 5-cycle window).
# Loads all six golden days: same rule-23 class as step 12, and like step 12 stdlib-only under -I.
# Mutants M1-M5. Appended AFTER step 24, never inside a pair (TD-S93-NEW-1).
echo "== 25/27 merdian_compute contract vs production golden rows (S101 / retail scope §1.3)"; python3 -I tests/test_merdian_compute_contract.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S102_R48: run_ingest.sh reports the ingest rc on its END line and exits with it -- a COPY of the
# wrapper in a temp dir with a stub .env and a stub ingest (the real .env is never read, rule 19).
# Mutant M1 = the pre-S102 capture. Appended AFTER step 25, never inside a pair (TD-S93-NEW-1).
echo "== 26/27 run_ingest.sh rc on the END line (S102 / tracker 2.2 R48)"; python3 tests/test_run_ingest_rc.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
# S102_TD_S77_NEW_8: refresh_equity_intraday_last.py writes its ledger row through core.execution_log (no
# hand-rolled insert), labels a Kite token error TOKEN_EXPIRED, declares its 1000-row floor, and imports cleanly.
# Stubs only. Mutants M1-M4. Appended AFTER step 26, never inside a pair (TD-S93-NEW-1).
echo "== 27/27 refresh_equity_intraday_last ledger via core.execution_log (S102 / TD-S77-NEW-8)"; python3 tests/test_refresh_equity_intraday_last.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
exit $rc
