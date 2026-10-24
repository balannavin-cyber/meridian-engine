# S98 doc-close inputs — status footers, new rows, Assumption Register, S98-B build state

Working doc for the S98 doc-close, carried into S99 as its first item. Rulings live in `claude/rulings_s98.md`
(S98-A … S98-E, S98-E.1) and the ranked table in `claude/s98_reconciliation_table.md`; both are cited by id here, not
restated. Nothing here is applied; the registers are edited at doc-close. S98 ended 2026-10-23 ~18:00 IST.

---

## 1. Status footers owed (one paragraph each, bodies unedited)

- **TD-S97-NEW-4 → ROOT CAUSE FOUND, fix built (not deployed).** R1a: the 15:40 γ row is written by the next session's
  first cycle (39/41 days since 08-24; confirmed live 2026-10-23 as A4). R41: every γ cycle computes the previous cycle's
  chain run — 76/76 rows per symbol on 2026-10-23, `created_at − ts` 303–318 s — because the runner starts in the same
  minute as the ingest it reads. Fix (a) re-scoped by S98-E / S98-E.1 to a cycle wait (`ts ≥` 5-min floor, poll 5 s, 120 s,
  timeout → exit 1 `SKIPPED_NO_INPUT` with cycle floor + newest ts per symbol in `error_message`), plus the 15:30/15:35/15:40
  cron line. Built and tested S98 (§4); apply + deploy S99. (b) (`actual_writes {}`) stays open.
- **TD-S94-NEW-4 → retention measured intact** (2026-10-23 04:51 IST): the chain table starts 08-24 — its first row, not a
  pruned floor; nothing has been deleted.
- **TD-S92-NEW-5 → CLOSED by TD-S95-NEW-2** (S96-J backfill, 2026-10-12; S97-E). Confirmed S98: the 10-02 row reads
  `false / Mahatma Gandhi Jayanti`, `notes = closed (S96 TD-S95-NEW-2 backfill, NSE holiday)`. S98-C's calendar INSERT
  was a no-op; the Rule 13 range `HOLIDAY-FROZEN-CHAIN-2026-10-02` was inserted (registry 4, new 1).
- **TD-S97-NEW-12 → 10-21 filled; breadth short.** A3 read 2026-10-23 17:02 IST: 10-21 written; `breadth_indicators_daily`
  31 rows short of `equity_eod` for that date (see table row). Re-read after the next EOD before any backfill.
- **TD-S97-NEW-13 → RE-SCOPED** (S98-D amended, no write): the 10-21 close exists (`dhan_charts_historical`, 15:29 IST,
  NIFTY 22811.35 / SENSEX 73709.69, created 10-22 08:50 IST by `backfill_cas_close_from_daily.py --auto-correct`). The
  10-22 "prev close missing" was read after that row existed → defect is the board's client-side prev-close read in
  `meridian-connect`, not data.
- **TD-S97-NEW-7, -20, -2 (S97 fixes) → live confirmations** per Part A (A1/A2) — record the A1/A2 outcomes as read
  2026-10-23 16:10–17:02 IST.
- **`tech_debt.md`:989's γ statement → superseded by R1a/R41.**
- **Tracker §2.1:** unchanged except the P4 lost-session note (SENSEX dte-1 on 10-21).

## 2. New rows (from the reconciliation table and the S98-B build; register as TDs at doc-close)

Table rows R38–R41 (SPOT lag by construction; "gap filled" wrong; breadth-ingest overlap with NULL status; runner reads
the previous chain run) are in `claude/s98_reconciliation_table.md`. Added by the build read 17:33–17:37 IST
(`rulings_s98.md` § New rows):

| Row | What | Home |
|---|---|---|
| R42 | `parse_orchestrator_window` returns the FIRST matching crontab line silently (`monitor_orchestrator_health.py`:231–256). A second runner line inserted above the first collapses the monitor band to 15:40–15:45 IST with no warning. Should union all matches or raise on >1. | TD, monitor change + test |
| R43 | `ingest_participant_positioning.py`:11 calls `SKIPPED_NO_INPUT` a BENIGN skip; `merdian_pipeline_alert_daemon.py`:64–71 alerts on it. Whether those alerts fired is unread (S97 Telegram outage). | TD, read first |
| R44 | `merdian_daily_audit.py`:518–525 labels every non-zero exit a "crash", ignoring `exit_reason`. | TD |
| R45 | Runner docstring :35–36 described an uninstalled schedule (`03,…,10`, `timeout 90`). Corrected inside the S98-B patch. | closes with S98-B |
| R46 | One missing symbol costs the full 120 s wait (T4). Ruled acceptable (120 + ~132 s < 300 s). | recorded, no TD |
| R47 | `core/execution_log.py`:90 claims `VALID_EXIT_REASONS` mirrors the CHECK constraint in `20260420_script_execution_log.sql`; T9 checks the runner against the frozenset, not the live constraint. Unverified link. | one SQL read (S99 step) |
| R48 | `run_ingest.sh` `set -e` makes its `rc=$?` unreachable (design note §0 out-of-scope). | TD |
| R49 | Monitor alarms on `exit_code` only, never `exit_reason` (:435–446): any non-zero skip pages CRITICAL. Behaviour, not defect — recorded so a future "benign skip" with exit 1 is not added unknowingly. | note in monitor TD family |

## 3. Assumption Register — §D.52 (corrections to my own work)

| # | What I stated or assumed | What was measured | Lesson |
|---|---|---|---|
| D.52.1 | S98-C pre-check would read `cal_rows_1002 = 0` (from TD-S92-NEW-5's 10-09 measurement) | 1 — the S96-J backfill had written it on 10-12 | Read the current value before writing an expected one from a register |
| D.52.2 | Marketview at `.com` | NXDOMAIN; host is `marketview.meridianalpha.in` | — |
| D.52.3 | Pre-open read: SENSEX 73,249 reported as a level | It was the previous close shown pre-open; not labelled as such | Label the provenance of every figure in a live read |
| D.52.4 | The 15:40 γ row was a hypothesis about the orchestrator | Confirmed 39/41 days, then live (A4); R41 found the general one-run lag | — |
| D.52.5 | Live monitoring at 5-min cadence held all session | Gap 12:34 → 15:58 IST (notification delayed) | A missed tick is reported when found, not smoothed over |
| D.52.6 | Design note D3: a new `STALE_INPUT` reason | Not in `VALID_EXIT_REASONS`; would have filed as `CRASH` → `UNKNOWN`. Caught by CC's read of the ledger, not by the stubbed test | A mocked collaborator agrees with the code; verify vocabulary against the real module (now T9) |
| D.52.7 | S98-B test assertions (my review) | CC's draft had two contradictory asserts (blanket `+00:00` vs newest-ts echo) and a mutant anchor that a refactor moved; both caught in review before a run | Re-derive every mutant anchor after an extraction refactor |

## 4. S98-B build state at EOS (2026-10-23 ~18:00 IST, tree `~/meridian-cc`)

- **Not applied, not committed, crontab untouched.** Live `run_merdian_shadow_runner_aws.py` 14,464 bytes.
- `scratch/s98/patch_s98b_runner.py` — Canon-v3, 5 anchors count==1, marker `S98_CYCLE_WAIT`, dry-run default.
- `scratch/s98/dryrun/run_merdian_shadow_runner_aws.py` — 22,400 bytes; 9 required functions + 5 constants + marker PASS.
- `tests/test_runner_cycle_wait.py` — T1–T9, mutants M (ts filter deleted → T2, T3), R (reason → `STALE_INPUT` → T2, T3,
  T9), Z (`isoformat()` → T7, T2, T3). Final run under `ulimit -v 700000`: **9 cells PASS; 3 mutants, 8 mutant cells,
  0 survivors; EXIT 0.** Driver aborts if any `must_fail` name matches no cell. `retry_call` stub keyword-only, mirroring
  `gamma_engine_retry_utils.py`:10–19.
- Hashes: see §6 (filled from CC's EOS output).

## 5. Commits made in S98

- `6b5ca9f` tests/run_offline.sh step 13 (test_contract_check_s97.py) — C1.
- `3532c72` sql/2026-10-12_s97_applied_reconstructed.sql — C2.
- `c3fc35c` docs/lovable_prompts/s97/lovable_prompt_s97_help_route.md (sha256 3010a482d043…) — C3.
- Still to commit at doc-close: `rulings_s98.md`, `s98_reconciliation_table.md`, `S98-B_cycle_wait_design_2026-10-23.md`
  (with an S98-E.1 amendment note), this file.

## 6. EOS hashes

Measured 2026-10-23 ~18:00 IST, `~/meridian-cc`. Final run: 9 cells, 0 failing; 3 mutants, 8 mutant cells, 0 surviving;
`RUNNER CYCLE WAIT ALL PASS`, EXIT 0. `git status --short`: new untracked `scratch/s98/`, `tests/test_runner_cycle_wait.py`;
no tracked file modified; no `_PRE_S98` backup on disk (`--apply` never ran).

| File | sha256 |
|---|---|
| `scratch/s98/patch_s98b_runner.py` | `b208b08ba962fbf208279d41d388f7a922fc2fd1f78c1aac931e531cd65ff7de` |
| `scratch/s98/dryrun/run_merdian_shadow_runner_aws.py` | `188702c8280878612c5c35b66d9116debc562e48e12d94c65519a3362faa5f2e` |
| `tests/test_runner_cycle_wait.py` | `d9e770f5e3c52514033b6c8d47a728851822d7a71b27b25a97351b15ff057817` |
| `run_merdian_shadow_runner_aws.py` (live, unpatched) | `617c3f6f61be8c64e9dfc08bd325ae54df10db2520df642f0598384f2ba079ae` |

The build exists only on the box, untracked, in `~/meridian-cc`.
