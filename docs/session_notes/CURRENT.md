# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S99 — 2026-10-23 evening → 10-24 ~07:25 IST.** S98 (2026-10-23 ~03:57 → ~18:00 IST) did not close, so this close
covers both; it was run in S100. S98-B deployed; the three streams became one list; the WCB writer stops writing when it
has no input. This block points; the detail lives in the files named. Rulings: `docs/research/s92_parity/rulings_s99.md`
(S99-A…I, the single source). **Progress lives in the tracker**, `docs/registers/agentic_layer_roadmap_S90.md` (v2.16),
and **its §2.2 is the single list** of open work.

**`origin/main` — all pushed.** `2edd25f` (S98-B) · `7d8f7d1` (S99 one stream) · `3706435` (R2/R21) · this close.
Local = GitHub = `~/meridian-engine` = `~/meridian-cc` at `3706435` before this close (box route, S99-A). Crontab 69
lines: runner lines 13 (`*/5 03-09`) and 69 (`0,5,10 10`, the closing cycles); the no-symbol WCB line removed (backups
`~/crontab.bak-S98B-2026-10-23`, `~/crontab.bak-S99R21-2026-10-24`). Marketview unchanged (`04fcd05`).

**What was established**

1. **S98-B deployed `2edd25f`** — the γ runner waits (120 s, poll 5 s) for its own cycle's chain run and exits 1
   `SKIPPED_NO_INPUT` without one; closing cycles 15:30 / 15:35 / 15:40 IST. The monitor window is unchanged at
   (180, 595, 5, {1..5}) (S99-B). Live PASS owed Monday 10-26 (NEXT 1).
2. **One list (S99-C).** Pass 2 read every open TD: 46 closed, 37 duplicates, 15 obsolete, 109 parked (68 signal / ICT,
   22 history, 10 with a named trigger, 9 agentic), the rest kept as rows of tracker §2.2 beside pass 1's. Agentic
   Stages 3–6 ON HOLD (S99-D); the ICT stream ranks after agentic (S99-G); the two S1 credential rotations follow B1
   (S99-E); retail scoping in tracker §2.3 (S99-F; the counsel question stays open).
3. **WCB (S99-H / S99-I, `3706435`):** no row and exit 0 `SKIPPED_NO_INPUT` on a stale breadth `ts` or no priced
   constituent; the 12 zero rows deleted (`zero_rows_left 0`). TD-S97-NEW-8, -9 and -10 closed.
4. **S98's measurements:** R41 — every γ cycle computed the previous chain run (76/76 rows per symbol, lag 303–318 s);
   R1a — the 15:40 γ row was written the next morning on 39 of 41 days; the 2026-10-02 Rule 13 range inserted (S98-C);
   the 10-21 close already written by the 08:50 reconciler (S98-D amended, no write); R47 verified (11 = 11 exit reasons).
5. **`tech_debt.md` split** (ruling S100-A, `docs/research/s92_parity/rulings_s100.md`): open entries stay in
   `docs/registers/tech_debt.md`; closed, duplicate, obsolete, parked and resolved entries moved verbatim to
   `docs/registers/tech_debt_history.md`. S98's rows R38–R49 are homed in tracker §2.2, not filed as TDs (S100-B).

**Corrections to my own work:** Assumption Register **§D.52** (S98, 7 rows) and **§D.53** (S99, 7 rows). The one to
carry: an expected value is computed on the tree about to be checked, never recalled (D.53.1, D.53.3).

**Security:** TD-S99-NEW-1 — an AWS access key ID sits in the public repo (no secret key found); rotation or a history
rewrite is the operator's call (tracker §2.2 BS).

**No ADR filed or amended; rules 0–24 unchanged.** System Map §S98–S99 (schedule change); Deployment Topology unchanged.

## NEXT SESSION PICKS UP

1. **Mon 2026-10-26, after 15:45 IST — the S98-B / S99-H live read:** γ `created_at − ts` median < 60 s per symbol; no
   row written on a later IST date than its `ts`; three closing γ rows per symbol; the 08:30 ledger row on 10-26 runs;
   runner `exit_code ≠ 0` = 0 (any `SKIPPED_NO_INPUT` read against the ingest ledger first); one `[CYCLE WAIT]` line per
   cycle; WCB: no row on Friday's 15:24 `ts` at 08:31, a real row at 15:40. PASS closes TD-S97-NEW-4, TD-S82-NEW-1 and
   TD-S82-NEW-2.
2. **Before Mon 07:45 IST — R4**, the 08:25 IST pre-open probe (tracker §2.2 B1).
3. **Then tracker §2.2 in its order:** B1 → BS-1 (credential rotations) → B2 → B3 → B4 → B5 → B6; BR and the rest of BS
   before any retail build.
4. **Disposition owed:** four entries open by their own Status that pass 2's keyword test missed (§2.2 B4, "Pass-2
   misses").

## OPERATOR RULINGS, S99

**All rulings live in `docs/research/s92_parity/rulings_s99.md`**, the single source.

| # | Topic |
|---|---|
| **S99-A** | S98-B committed by the box route |
| **S99-B** | Monitor window PASS = identical to the baseline, plus the negative control |
| **S99-C** | Pass 2 adopted as mapped; all 68 signal / ICT items parked |
| **S99-D** | Agentic MERIDIAN on hold; Stages 3–6 ON HOLD |
| **S99-E** | The two S1 credential rotations right after B1 |
| **S99-F** | Retail scoping inputs; the regulatory question open |
| **S99-G** | The ICT stream after agentic |
| **S99-H** | WCB: no input → no row, exit 0 `SKIPPED_NO_INPUT` |
| **S99-I** | Delete the 12 zero WCB rows |

## Previous session S98

**S98 — 2026-10-23 ~03:57 → ~18:00 IST.** S97's live confirmations read; the three streams reconciled into one ranked
table; R41 found; S98-B designed, built and tested on the box. No close of its own — closed with S99. Rulings:
`docs/research/s92_parity/rulings_s98.md` (S98-A…E, S98-E.1). Working docs: `docs/research/s98/`.

**Commits:** `6b5ca9f` (contract-check test wired, step 13) · `3532c72` (S97 applied SQL reconstructed in `sql/`) ·
`c3fc35c` (S97 help-round record). The S98-B build stayed untracked in `~/meridian-cc` until S99 (`2edd25f`).

**What was established**

1. **S97's fixes held live on 2026-10-23:** the monitor logged 0 "not firing", 0 RECOVERED, 422 OK; the contract check
   sent no spot alarm and closed the 10-09 episode with one `[CLEAR]`; EOD wrote 10-21 (breadth 31 rows short).
2. **One ranked table (S98-A):** S97's TDs, the parity-target evaluation's MERIDIAN-side findings and the tracker, rows
   R1–R41 with one home each (`docs/research/s98/s98_reconciliation_table.md`).
3. **R1a and R41:** the first cycle of every session wrote the previous session's 15:40 γ row; every cycle computed the
   previous chain run. S98-B (ship coupled) and S98-E / S98-E.1 (wait for the cycle's run; closing cycles; timeout →
   exit 1 `SKIPPED_NO_INPUT`).
4. **Operator writes:** the 2026-10-02 Rule 13 range (S98-C; the calendar row already existed); S98-D amended to no
   write.

## OPERATOR RULINGS, S98

**All rulings live in `docs/research/s92_parity/rulings_s98.md`**, the single source.

| # | Topic |
|---|---|
| **S98-A** | Adopt the reconciliation table as written |
| **S98-B** | Runner age guard and the 15:40 γ schedule ship coupled |
| **S98-C** | 2026-10-02: Rule 13 range and calendar row |
| **S98-D** | 10-21: the close only (amended: no write) |
| **S98-E** | S98-B design D1–D3 |
| **S98-E.1** | Timeout reason `SKIPPED_NO_INPUT`; the closing line appended after the runner line |
