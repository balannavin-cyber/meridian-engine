# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. **S92 moved at the S94 close**, asserted byte-identical at **9,049 B**, sha256 `6f45dd8b…` on both sides. **S93 moved at the S95 close**, asserted byte-identical at **8,092 B**, sha256 `c84882be…` on both sides. **S94 moved at the S96 close**, asserted byte-identical at **8,326 B**, sha256 `0537ac73…` on both sides. **S95 moved at the S97 close**, asserted byte-identical at **4,816 B**, sha256 `f63116f5…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S100 — Saturday 2026-10-24 07:39 IST → Sunday 10-25.** Part A closed S98 + S99 (`3ad5c81`); Part B built and shipped
the weekend list; Part C is Monday 2026-10-26. This block points; the detail lives in the files named. Rulings:
`docs/research/s92_parity/rulings_s100.md` (S100-A…S, Q.1; the single source). **Progress lives in the tracker**,
`docs/registers/agentic_layer_roadmap_S90.md` (v2.17), and **its §2.2 is the single list** of open work.

**`origin/main` — all pushed.** `3ad5c81` (S98 + S99 close) · `3070682` (R3) · `b29f320` (R42) · `9e24792` / `4769565` /
`d91295b` (R4) · `f213d22` (R40, TD-S81-NEW-11) · `9c5f50c` (R19) · `418a75b` (S100-M b) · `08b25a8` (manual v0.4, round
records, B3 reads) · this close. Box route (S99-A). Crontab 70 lines: Dhan token refresh 08:20 IST (`50 2`, S100-G),
`preopen_probe.py` 09:09 IST (`39 3`, S100-E). Monitor window (180, 610, 5, {1..5}) (S100-C, supersedes S99-B's 595).
Offline suite **23 steps**. **Marketview live `f964e40`** (bundle `index-BFOk56iL.js`); **`27c0e17`** (in-app manual v0.4,
`manual.json` sha256 `489a135e62ce…`) on `/staging/`, its promote given at the close and not yet read back.

**What was established**

1. **Monitoring and pre-open (B1).** The monitor flags a hung orchestrator run (`3070682`, TD-S97-NEW-3) and its window
   is the union of every runner crontab line, so the closing cycles are watched (`b29f320`, S100-C). One broker-access
   probe at 09:09 IST pages on failure; a wsfeed retry timer with deduped alerts (`9e24792`, S100-E / S100-F). The
   alert daemon and the daily audit have not run on AWS since 2026-06-11 / 06-07 — recorded dead, revival a BO row
   (S100-D). The 12 `pg_cron` jobs calling the retired Edge Functions are inactive (S100-H, TD-S90-NEW-14).
2. **Writers (B1, B4).** Breadth-from-ticks writes no row and exits 0 on no ticks, with a holiday gate and a ledger row
   (`f213d22`, S100-I; the overlap lock deferred); the chain ingest retries a Dhan 5xx twice (TD-S81-NEW-11). The daily
   breadth builder fills a complete EOD date a later date overtook (`9c5f50c`, R19; 10-08 1,377 and 10-15 1,373 rows
   backfilled, no October date short). A Dhan 806 / DH-902 plan lapse now logs `SUBSCRIPTION_LAPSED`, not
   `TOKEN_EXPIRED` (`418a75b`, S100-M b; exit reasons 11 → 12).
3. **Operator SQL.** R22 calendar repair; `data_contamination_ranges.symbols text[]` (S100-J; the Rule 13 symbol test is
   in `CLAUDE.md`); `merdian_ro_select` on the 51 RLS tables no policy reached (S100-K; 56 policies, audit 0); the exit
   reason CHECK widened (S100-M). Records in `sql/`.
4. **Board (meridian-connect, six rounds, `docs/lovable_prompts/s100/`).** Health untracks the ICT writer (S100-M a);
   legacy pages take Board's previous close and spot (S100-N, R34 / R18); Context IV skew = the view's skew (S100-P,
   R35); the pocket word named local with net γ beside it (S100-Q / Q.1, R17 step 1); Spot label held / close and dealer
   wording D1–D7 (S100-R, R5 label part, R14); session-state strip, stale window to 15:45, basis names its spot (S100-S,
   final report A2 / A4 / A5). Backup retention: newest 3 `.bak-*` plus the named `PRE_*` (S100-L).
5. **Reads (B3, `docs/research/s100/B3_reads_2026-10-24.md`).** R7 ours right (15:20 vs 15:40); R8 last-trade bounce,
   2–4 bp on both indices, no capture defect; R10 by construction; R18 three figures reproduced, one defect fixed by
   S100-N. Final report status: `docs/research/s100/S100_status_vs_final_report.md`.
6. **Dispositions (S100-O).** Muhurat is not captured, by decision (ADR-020 amended; engine and gate docstrings
   corrected); TD-S80-NEW-19 superseded by v5 Rule 3; ADR-004 Amendment C dated note; TD-S90-NEW-12 closed on the
   reconciliation read. Γ = aggregate exposure, γ = per-option gamma (S100-R C; `CLAUDE.md` settled decision).
7. **Docs.** Marketview user manual v0.4 (`docs/marketview_manual/`); help pack `board_bundle` points at the top-level
   board chunk.

**Filed:** TD-S100-NEW-1…6 — the futures rows keep the 15:15 spot through the closing window (stored basis wrong at
15:30–15:40); loading states rendered as values; two unimported components; docs cite the dead bare-IP board URL; the
CAS close backfill logs DH-902 as `DATA_ERROR`; and the legacy pages' two-session change (filed and closed, S100-N).

**Corrections to my own work:** Assumption Register **§D.54** (S100, 23 rows). The one to carry: a count, a bound or a
diff size is computed before it is stated — this session stated five from memory or estimate and each was wrong.

**Security:** TD-S99-NEW-1 and BS-1 stand (operator actions). A 15-character `x-cron-secret` prefix reached the chat in a
log read — treat it as disclosed; its deletion rides with the Edge Function ruling.

**ADR-020 amended (S100-O); ADR-004 §15 dated note; rules 0–24 unchanged.** System Map §S100; Deployment Topology §S100.

## NEXT SESSION PICKS UP

1. **Mon 2026-10-26 — Part C, the live reads.** (a) The S98-B / S99-H read after 15:45 IST, as S99 wrote it: γ
   `created_at − ts` median < 60 s per symbol; no row on a later IST date than its `ts`; three closing γ rows per symbol;
   the 08:30 ledger row runs; runner `exit_code ≠ 0` = 0 (any `SKIPPED_NO_INPUT` read against the ingest ledger first);
   one `[CYCLE WAIT]` line per cycle; WCB no row on Friday's 15:24 `ts` at 08:31 and a real row at 15:40. PASS closes
   TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2. (b) The 08:20 refresh and the 09:09 probe run (TD-S97-NEW-5 closes on a clean
   probe); the wsfeed starts on its own (TD-S80-NEW-17). (c) The S100 board reads in
   `docs/research/s100/S100_partC_additions.md` (Health, S100-N discriminating read, R19 after EOD, S100-R / Q.1 / S).
2. **Operator, before Monday's open:** BS-1 — Dhan TOTP re-enrolment and PIN change, the `.env` update by hidden prompt,
   then `refresh_dhan_token.py` and `preopen_probe.py --check`. Read back the `27c0e17` promote (the in-app manual).
3. **Then tracker §2.2 in its order:** B1 (R48 / R49, the ledger row, the R40 overlap) → BS-1 → B2 (R5 close print on the
   15:40 cycle, R20; TD-S100-NEW-1 first) → B3 (R16 + R36, chain data) → B4 → B5 (R15, R11 + R39) → B6 (R12 with S100-Q
   step 2, R13); BR and the rest of BS before any retail build.

## OPERATOR RULINGS, S100

**All rulings live in `docs/research/s92_parity/rulings_s100.md`**, the single source.

| # | Topic |
|---|---|
| **S100-A** | `tech_debt.md` split: open entries / history |
| **S100-B** | R38–R49 homed in tracker §2.2, no TDs |
| **S100-C** | Monitor window = union of runner lines, contiguous only |
| **S100-D** | Alert daemon and daily audit recorded dead; design later |
| **S100-E** | One broker-access probe at 09:09 IST |
| **S100-F** | wsfeed retry timer plus deduped alert |
| **S100-G** | Dhan token refresh at 08:20 IST |
| **S100-H** | Deactivate the 12 Edge Function cron jobs |
| **S100-I** | Breadth-from-ticks: no ticks → no row, exit 0 |
| **S100-J** | `data_contamination_ranges.symbols text[]` |
| **S100-K** | `merdian_ro_select` on the 51 RLS tables |
| **S100-L** | Marketview backups: newest 3 plus named `PRE_*` |
| **S100-M** | Health untracks the ICT writer; `SUBSCRIPTION_LAPSED`; CRITICAL display only |
| **S100-N** | Legacy pages: Board's previous close and spot |
| **S100-O** | Pass-2 misses: Muhurat not captured; v5 Rule 3; ADR-004 erratum |
| **S100-P** | Context IV skew = the view's skew |
| **S100-Q / Q.1** | Pocket word local, net γ beside it; then R12 |
| **S100-R** | Spot label, dealer wording D1–D7, Γ kept |
| **S100-S** | Session-state strip, stale window to 15:45, basis names its spot |

## Previous session S99

**S99 — 2026-10-23 evening → 10-24 ~07:25 IST** (with S98, closed in S100 Part A, `3ad5c81`). S98-B deployed `2edd25f`;
pass 2 made tracker §2.2 the single list (S99-C); agentic Stages 3–6 on hold (S99-D); the WCB writer writes nothing
without input (`3706435`, S99-H / S99-I). The full blocks for S98 and S99 are in `docs/registers/CURRENT_history.md`.

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
