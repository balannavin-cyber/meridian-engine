# Operator rulings — Session 98

Single source for the S98 rulings. Other documents point here and do not restate them. Sits beside `rulings_s92.md` …
`rulings_s97.md` in `docs/research/s92_parity/`. S98 opened 2026-10-23 ~03:57 IST.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S98-A** | 2026-10-23 ~06:27 IST | Part B — the three-stream reconciliation | **Adopt `claude/s98_reconciliation_table.md` as written**: every row takes its stated kind, one home and recommendation; the dropped list stands; the proposed order (§3) is the work order. In particular: **TD-S97-NEW-17 absorbs manual findings F-1 and F-7** (the manual points to the TD); TD-S97-NEW-18 = coverage G25; manual F-2…F-6 become R33–R36; the carried list (CURRENT NEXT item 7) stays carried. Registers are updated at the S98 close. | The table (§1 overlap tests O1–O4, rows R1–R37, X1, P4, P8), built from S97's TDs, the 10-13 → 10-19 evaluation and the tracker; box reads 2026-10-23 04:40–05:19 IST. Operator: "Adopt as written". |
| **S98-B** | 2026-10-23 ~06:27 IST | R1 + R6 — TD-S97-NEW-4 fix (a) and the γ schedule | **Ship coupled**: the runner's age guard (refuse run_ids not from today's session, exit non-zero with a reason) **and** the orchestrator schedule extended to the 15:40 chain run, as **one capture-path change** in the S90-J window, with a replay check and a written rollback. | `gamma_metrics`: 39 rows per symbol since 08-24, all stamped 15:40 IST and all written at the next session's 08:30 / 08:40 (control: 0 same-day); code path `run_merdian_shadow_runner_aws.py`:89–137 (no age guard, deliberate), cron `*/5 03-09` UTC vs ingest to 15:40 IST. Fix (a) alone would remove the only path that writes γ on the close. Operator: "Ship coupled". |
| **S98-C** | 2026-10-23 ~06:27 IST | R37 — 2026-10-02 (Gandhi Jayanti) | **Both operator writes**: one Rule 13 range for 2026-10-02 over `option_chain_snapshots`, `gex_strike_snapshots`, `gamma_metrics` (both symbols), and TD-S92-NEW-5's closed `trading_calendar` row. Operator SQL in the editor, ending with its own verification SELECT. | Chain: 83 frozen cycles (`tech_debt.md`:986–987); γ: one run per symbol at 15:40 (spot 22421.95 / 71909.7) and two FULL rows written 2026-10-05 08:40 IST by the first-cycle reuse; registry readable by `merdian_ro` (3 rows), none covering 10-02. Operator: "Both writes". |
| **S98-D** | 2026-10-23 ~06:27 IST | R20 — 2026-10-21 (Dhan Data API lapse) | **Backfill the 10-21 close only**, from Dhan's daily candle, tagged as backfilled; the 1-min spot is not backfilled. The SENSEX dte-1 session lost to P4 is recorded in P4's count (no back-fill under P4 §6). | TD-S97-NEW-13; the 10-22 board's OPEN · GAP tile read "prev close missing". Operator: "Close only". |

| **S98-E** | 2026-10-23 ~17:15 IST | S98-B design — `claude/S98-B_cycle_wait_design_2026-10-23.md` (after R41: every γ cycle computes the previous chain run, 76/76 per symbol, lag 303–318 s) | **The runner waits for its own cycle's chain run** (`ts ≥` the 5-min cycle floor, poll 5 s): **D1 wait 120 s; D2 closing cycles 15:30 / 15:35 / 15:40; D3 timeout → exit 1 `STALE_INPUT`, no fallback.** Offline test `tests/test_runner_cycle_wait.py` (T1–T6 + mutant) wired as step 14/14; S90-J window; crontab backed up before the one-line add; live PASS Monday 2026-10-26 per design §6. | Design note §1 code read 17:12 IST; operator: all three as recommended. |

| **S98-E.1** | 2026-10-23 ~17:38 IST | Amends S98-E D3 and fixes D2's delivery, after CC's build read (17:33–17:37 IST) | **D3: timeout exits 1 with reason `SKIPPED_NO_INPUT`** (not a new `STALE_INPUT`); `error_message` carries the cycle floor and each symbol's newest chain `ts`. **D2: the closing cycles go in as a second cron line appended after the existing runner line**; right after the edit, `parse_orchestrator_window` is run against `crontab -l` and must read 03:10–10:00 UTC, else roll back. The closing cycles are outside the monitor band and covered by the alert daemon. | `core/execution_log.py`:91–103: `STALE_INPUT` is not in `VALID_EXIT_REASONS` (CHECK in `20260420_script_execution_log.sql`) and :283–291 coerce it to `CRASH` → `UNKNOWN`. `monitor_orchestrator_health.py`:435–446 alarms on `exit_code != 0` alone; `merdian_pipeline_alert_daemon.py`:64–71 lists `SKIPPED_NO_INPUT` in `ALERT_EXIT_REASONS`. `parse_orchestrator_window` (:231–256) returns the **first** matching line: appended = window unchanged, inserted above = window collapses to 15:40–15:45 IST. CC's alternative `*/5 03-10` rejected: 15:45–16:25 cycles find no chain → nightly CRITICAL. Operator: both as recommended. |

## Consequences recorded at ruling time

- **Work order (S98-A §3):** R1+R6 (per S98-B) → R2 / R21 → R3 after A1 → R4; R5 (close print now reads the 15:40 chain
  spot, per O1 as corrected) → reads R7 / R8 / R10 / R18 / R36 → R9, R19 after A3, R22–R24, R34 / R35 → wording batch
  (R14, R15, R17, R33, R5 labels) with manual v0.4 → pre-registered R12 / R13.
- **Owed at doc-close:** status footers on TD-S97-NEW-4 (R1a evidence and the 39/41 count), TD-S94-NEW-4 (retention
  measured intact, 2026-10-23 04:51 IST), TD-S92-NEW-5 (closed by S98-C if applied), `tech_debt.md`:989's γ statement
  (superseded by R1a); tracker §2.1 unchanged except the P4 lost-session note.
- **Applied by this file:** nothing.

## Applied after ruling

- **S98-C, 2026-10-23 ~06:32 IST (operator, SQL editor).** Range `HOLIDAY-FROZEN-CHAIN-2026-10-02` inserted:
  verification `registry_total 4`, `range_new 1`. **The calendar INSERT was a no-op:** pre-check read
  `cal_rows_1002 = 1` (expected 0 — taken from TD-S92-NEW-5's 2026-10-09 measurement, not read first; §D.52.1), and
  the existing row already reads `false / Mahatma Gandhi Jayanti`. **Writer confirmed 06:33 IST:** `notes`
  = `closed (S96 TD-S95-NEW-2 backfill, NSE holiday)` — so **TD-S92-NEW-5 was fixed on 2026-10-12 by the S96-J backfill**
  and its register entry is stale; footer at the close: CLOSED by TD-S95-NEW-2 (S96-J / S97-E), confirmed S98.
- **S98-D amended by the operator, 2026-10-23 ~06:47 IST: no write.** Box read 06:45 IST (`/tmp/s98_close.txt`):
  `market_spot_snapshots` already holds the 10-21 close — one row per symbol at 15:29 IST, `source_table =
  dhan_charts_historical`, NIFTY 22811.35 / SENSEX 73709.69, `created_at` 2026-10-22 08:50 IST, written by the existing
  `backfill_cas_close_from_daily.py --auto-correct` (cron 08:50 IST). S98-D is **satisfied by the reconciler**.
  **TD-S97-NEW-13 re-scoped** at the close: the 10-22 board's "prev close missing" was read at 10:03 IST, after that row
  existed, so the defect is the **board's prev-close read** (client-side in `meridian-connect`; no view in `sql/`
  serves a spot prev close), not a data gap. First test: today's OPEN · GAP tile after 09:15 IST (10-22 has a normal
  16:00 `dhan_idx_i` row). Also found: the 16:00 futures leg exits 1 on holidays (10-20 Dussehra: `spot=0 | futures=1`),
  so the wrapper logs "MARKET CLOSE CAPTURE FAILED" every holiday — folded into R2 (calendar-blind writers).

## New rows for the reconciliation table (from the S98-B build read, 2026-10-23 17:33–17:37 IST)

- **R42** `parse_orchestrator_window` takes the first matching crontab line silently (`monitor_orchestrator_health.py`:231–256);
  should union all matching lines or raise on >1. Monitor change, own test.
- **R43** `ingest_participant_positioning.py`:11 calls `SKIPPED_NO_INPUT` a BENIGN skip; the daemon alerts on it
  (`merdian_pipeline_alert_daemon.py`:70). Whether those alerts fired is unread (S97 Telegram outage, 44b8b96).
- **R44** `merdian_daily_audit.py`:518–525 labels every non-zero exit a "crash", ignoring `exit_reason`.
- **R45** `run_merdian_shadow_runner_aws.py`:35–36 docstring describes a schedule (`03,…,10`, timeout 90) that is not
  installed — corrected in the S98-B patch.
- **R46** One missing symbol costs the full 120 s wait (T4); ruled acceptable (120 + ~132 s < 300 s), no early break.
