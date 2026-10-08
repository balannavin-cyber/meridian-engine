# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S91 / AM-2 (Agentic Meridian Session 2) — 2026-10-06 → 2026-10-07 (Tuesday–Wednesday, live
session).** Two parts. **Part 1** folded the AM-1 post-close delta into the registers and
codified two operator rulings (`f455e97`, docs only). **Part 2 — this close — shipped two
live fixes and diagnosed a third defect that had been filed on an impression.** This block
points; the detail lives in the files named.

**Three commits, `b48532e` → `6a5c0e2` + this close. All pushed; the box is current.**

| Commit | What |
|---|---|
| `bcadfa6` · `67a91ce` | *(part 1)* TD-S91-NEW-1 `_ist_date` fraction padding, writer + reconciler; R1.6 seeded cases 5–11; rule 23 guard in `run_offline.sh` |
| `b48532e` | **TD-S91-NEW-2 site 2** — `build_market_spot_session_markers.py` `parse_ts` pads 1/2/4/5-digit fractions. 10-05 and 10-06 had **no marker rows at all**; both backfilled. Test step 8/9 |
| `6a5c0e2` | **TD-S91-NEW-12** — the orchestrator monitor's Telegram flood. Gated on trading day **and** the orchestrator's own crontab window; one condition key, 30-min re-notify, 10-tick hold-down, UNKNOWN ticks inert. Test step 9/9, 54 cells |

**What was established**

1. **An alert channel that was instrumented and unreadable at the same time.**
   `monitor_orchestrator_health.py` sent on `*/1` 24×7 while the orchestrator runs `*/5
   03-09` UTC: ~1,000 sends a night, chat **4.1k unread and MUTED** — and the 09:10 IST
   wsfeed preflight alert (**TD-S91-NEW-3**) **did fire, at 09:10:04 IST**, into that muted
   chat. The incident needed no new instrumentation. Replay of the real 2026-10-07 day:
   **835 → 14 sends.**
2. **Gating was not enough, and only a replay showed it.** The in-band condition changes on
   **119 adjacent minute pairs**, so a 30-minute re-notify engaged **zero** times; two keys
   with immediate recovery would still have sent **148**. A first test passed **40/40** over
   that design because its scenarios came from the spec and the real sequence is neither
   flat failure nor clean recovery. One key + a 10-tick hold-down → 14; **one key alone
   measures 93**, so the hold-down carries the larger half.
3. **TD-S91-NEW-6 was filed as "exits 1 every cycle" and is 21 of 84 = 25 %, in two
   mechanisms** — 12 structural `SKIPPED_NO_INPUT` (08:31–09:26 IST, futures capture starts
   09:30) + 9 `DATA_ERROR` `no_rows` (09:41…14:56 IST). The code path is now exact:
   `no_rows ⟺ parse_ts(rows[0]["ts"]) is None`. **The mechanism is open between two
   candidates** — the unpadded fraction (a 7th TD-S91-NEW-2 site, `compute_basis_context_local.py:61`)
   and a NULL `ts` reaching `rows[0]` through `order=ts.desc`'s NULLS FIRST. **The observed
   12.5 % matches the single-timestamp rate (9.91 %), but the path needs both symbols in one
   cycle, whose independent rate is 0.98 % — P(X ≥ 9) = 4.14 × 10⁻⁸.** So the rate agreement
   is not evidence; one discriminating read is owed.
4. **TD-S91-NEW-1's fix is deployed and unverified by any cycle.** Pulled to the box
   **12:23:53 UTC** (file mtime matches); the orchestrator's last cycle of the day was
   **09:55 UTC**, so all 34 of its failures **predate the deploy**. Today's log is evidence
   about the old artefact. **77/77 on 2026-10-08 09:05–09:25 IST is the first real test.**
5. **TD-S91-NEW-7 verified** — the owed post-15:40 run happened: `( ulimit -v 700000; bash
   tests/run_offline.sh )` → **`OFFLINE PASS`, 9/9**, with step 2 (the file that OOM-killed
   the box) completing inside the ceiling. Under `ulimit -v` a memory regression now **fails
   the suite** instead of killing the box.
6. **ENH-98 T1 = PASS on the A5 arm** (SENSEX dte 1, 10:15:59 IST; `exact/365` ATM **0.0716**
   / NEAR **0.0369**, ATM rows **28 ≥ 10**), against a pre-registration hashed **before** the
   read (`2a978967f956…`). **T1 is no longer the L7/L8 blocker; a PASS does not build the
   views.** The S89 pre-committed DROP is **moot, not discharged** — S90-A never created
   them. Open: NIFTY **`r_eff` 3.08 %** to check against T3's definition (TD-S89-NEW-3).

**Corrections to my own work — §D.47, 5 rows, all REFUTED.** Three mine, one an advisory
claim I acted on untested, one filed-and-contradicted the same day. **The one to carry,
D.47.3:** I estimated one-key-alone at "≈14 sends" where a replay was available; it measures
**93**, and ≈14 is what the *combined* fix delivers — so the estimate would have validated a
weaker fix. **An estimate that coincides with the right answer for the wrong configuration is
indistinguishable from a measurement until someone measures.**

**Registers touched:** `tech_debt.md` (**TD-S91-NEW-12…18 filed**; **-1** → FIX DEPLOYED,
**-2** → 1 of 7 fixed + 7th site, **-3** → the alert fired and was missed, **-6** → corrected
and diagnosed, **-7** → VERIFIED), Assumption Register **§D.47**, Enhancement Register
(**ENH-98 S91 block**), `CURRENT.md` (S89 → `CURRENT_history.md`, byte equality asserted at
8,079 B / sha256 `e2bec976…`), `session_log.md`, `merdian_reference.json` **v70**,
`CLAUDE.md` footer **v1.64**, **S92 starter**. Sources:
`scratch/s91/telegram_flood_findings_S91.md`, `scratch/s91/basis_context_findings_S91.md`.

**No ADR filed; no DDL applied; no data migration.** Two rulings are owed (below).

## NEXT SESSION PICKS UP

**S92 starter: `docs/session_notes/S92_dev_starter.md`. VERIFY FIRST — four things shipped
this session and none of them is verified.**

1. **Thu 2026-10-08 — the verification block. Do this before anything else.**

   | When (IST) | Check | PASS looks like |
   |---|---|---|
   | 09:05–09:25 | `gex_cycle_history` front leg vs `gamma_metrics` | **77 of 77**, not 64 — **TD-S91-NEW-1** closes on it |
   | after 15:30 | orchestrator contract-met rate for the day | **≈ 75 %** (63/84) against 54.8 % on 10-07 — this is a **prediction**; a miss means `bcadfa6` is not doing on the box what it did offline, or a third cause exists |
   | 16:10 | `market_spot_session_markers` row written **by cron**, not by hand | a row for 10-08 — **TD-S91-NEW-2** site 2 proven on the live path |
   | end of day | Telegram volume, **after unmuting the chat** | **≈ 14 in-session sends**, no overnight traffic — **TD-S91-NEW-12** closes on it. Until the chat is unmuted the fix is unproven where it matters |

2. **Two operator rulings owed:** **`SKIPPED_NO_INPUT` → exit 0** (TD-S91-NEW-15 — 12 daily
   false-failed cycles, mechanism settled, fix is a ruling not an investigation) and
   **Doc Protocol v5** (drafted at S90, still not ruled).
3. **The basis discriminating read** (TD-S91-NEW-6): raw `ts` strings per symbol for the
   newest `index_futures_snapshots` row across several cycles, plus whether the column is
   nullable. Fraction → widths {1,2,4,5}; NULL → a null at `rows[0]`.
4. **`validate_compute_contracts.py` — DUE before Tue 2026-10-20** (TD-S91-NEW-13). ~168
   Telegram messages on a weekday holiday, and 10-20 is the next one. Fix is the same shape
   as `6a5c0e2`: calendar gate + 30-min dedupe. **TD-S91-NEW-14** (`:170` asserts a cycle
   skip that never happens) travels with it.
5. **08:40 IST Zerodha early-mode preflight — design agreed, NOT built** (TD-S91-NEW-3). It
   must **exercise** the token, not check its presence.
6. **Stage B** of the agentic layer · **R1.10 scrip-map sync (ROADSTAR)** ·
   **`build_ict_htf_zones` re-run** · **Marketview Pin/Flows — a parallel session**.
7. **Dated carries:** **~Tue 2026-10-13** drop the S90-H backup tables after a clean week
   (TD-S90-NEW-11) · **Tue 2026-10-20** the first live test of R0.8, no chain rows written
   and `cycle_health` CLOSED (TD-S89-NEW-1 closes on it, and TD-S91-NEW-13 must land first).
8. **Remaining TD-S91-NEW-2 sites:** 1, 3, 4, 5, 6, 7 — and the shared `core/` timestamp
   helper, which is the actual fix. **Any re-sweep must walk the orchestrator's step list as
   well as the crontab**: site 7 was invisible to the original grep for exactly that reason.
9. **NIFTY L9 stage-1 max-pain arm** (TD-S80-NEW-1), pre-registered before any read —
   carried from S89 through S90 and S91, still owed.

## OPERATOR RULINGS, S91

**All rulings live in `docs/research/s91_agentic/rulings_s91.md`**, the single source. This
table points and does not restate.

| # | Topic |
|---|---|
| **S91-A** | No fixture-suite run 08:30–15:40 IST, and every run under an explicit `ulimit -v` → `CLAUDE.md` rule 23 |
| **S91-B** | One Claude Code session per tree, and never root one in `~/meridian-engine` → `CLAUDE.md` rule 24 |
| **S91-C** | Monitor dedupe: **30-min re-notify** (the "60 min → 1 send" in the original brief was arithmetically impossible and was withdrawn) |
| **S91-D** | Monitor flapping: implement **both** one-key **and** a hold-down of **10 consecutive clear ticks** — two cycles, because one *successful* cycle spans 5 ticks of the look-back |
| **S91-E** | A probe failure is **UNKNOWN**, not a clear tick: skip both the send and the hold-down that minute |
| **Owed** | `SKIPPED_NO_INPUT` → exit 0 · Doc Protocol v5 |

## Previous session S90 / AM-1

**S90 / AM-1 (Agentic Meridian Session 1) — 2026-10-05 (Monday, live session) → 2026-10-06 05:20 IST.**
The first build session of the agentic layer: Stage 0 (spine) and the first Stage 1/2 harness
items, built beside the live system. **AM-n numbering starts here; S-numbers continue in parallel
(AM-1 = S90).** This block points and does not restate. Progress lives in **one** place, the
tracker `docs/research/s90_agentic/agentic_layer_roadmap_S90.md` (v2.7, §3 Status/Session
columns, each with linked evidence); rulings in `docs/research/s90_agentic/rulings_s90.md`
(S90-A…I); the decision in **ADR-031**. Closed **hybrid** by operator ruling: the protocol files
carry short pointer entries, and Doc Protocol v5 is drafted for ruling, not adopted.

**What was established**

1. **ADR-031 FILED and ACCEPTED (S90-C)** — the spine: data contracts with generated checks; one
   status enum (`OK/DEGRADED/STALE/MISSING/CLOSED/NOT_COMPUTED/UNKNOWN`) propagated down the
   lineage; provenance (**D3a: via `run_id` → ledger**, S90-I); rules read as-of, write path closed
   to anon (S90-E); closed days are rows; a new table states RLS in its own DDL and is checked
   after apply; `script_execution_log` is the one ledger and `merdian_ro` can read it.
2. **Production changed — 15 commits `38a0a84..ca79717`, all pushed, production fast-forwarded**
   (the last at **2026-10-06 04:53 IST, pre-market, by operator choice** over the after-16:00 rule):
   contract runner in shadow every 5 minutes writing `cycle_health` (R1.2); ENH-133
   `gex_cycle_history` applied, writer wired, reconciler scheduled (R0.4, ADR-030 front leg only
   per S90-B); the runner and every chain/gamma/vol/history writer write ledger rows carrying
   `run_id`/`product`/`status` (R0.7, R0.3); closed days written as rows and the chain ingest and
   spot capture moved onto the shared calendar gate (R0.8) — **R01-F5, a repeat of 10-02 on
   2026-10-20, closed before its date**; WCB reads live LTP (S90-G); the EOD sweep runs a full lap
   and stamps dates in IST, with a one-time +1 day migration of two tables (S90-H); six golden days
   frozen in `tests/golden/` (R2.1).
3. **Database, applied in the SQL editor** (files in `sql/`, prefix `2026-10-05_s90` /
   `2026-10-06_s90`): status enum, `data_contracts` (14), `product_lineage` (12), `cycle_health`;
   `update_parameter()` revoked from PUBLIC/anon/authenticated; `get_parameter_num(key, as_of)`;
   health views; ledger columns + `v_run_trace` + `v_provenance_coverage_daily`; `merdian_ro`
   read policies on `script_execution_log`, `merdian_parameters`, `dhan_scripmaster`; the
   dealer-flow sign fix (MV-1); DH-905 remap.
4. **Marketview live check found 12 items (MV-1…12); MV-1/2/3/5/9 fixed, MV-4 partly** —
   `docs/research/s90_agentic/marketview_live_check_S90.md`. The frontend fixes are deployed from
   `~/meridian-connect` **`265ceb0`, which is NOT in GitHub** (TD-S90-NEW-2).
5. **Twelve spine findings, R01-F1…F12** (`R0.1_spine_inventory_S90.md` §11): the orchestrator
   wrote no ledger row (F1, fixed); `equity_eod` / `breadth_indicators_daily` dates one day early
   since 2025-07 (F10, fixed); the EOD sweep covered only part of the universe each day (F11,
   fixed); **DH-905, S67's "structural" 97.83 % ceiling, was stale IDs from series changes** (F12,
   cured by hand: 28 remapped, 4 deactivated, 0 unmapped).

**Corrections to my own work — §D.46, 13 rows.** The one to carry: **the Supabase SQL editor does
not run a `BEGIN … temp table … COMMIT` script as one transaction in one session** — the DH-905
remap landed while the editor reported `42P01` (§D.46.8). Gated multi-step writes go in **one
`DO` block**.

**Registers touched:** `tech_debt.md` (**TD-S90-NEW-1…11** + S90 status footer on six existing
TDs), Assumption Register **§D.46**, Decision Index (**+ADR-031**, marker → `ADR-032+`),
Enhancement Register (ENH-133 row, change log, Part 6 footer), System Map **§S90**, Deployment
Topology **§S90**, `merdian_reference.json` **v68**, `CLAUDE.md` **v1.62**, ADR-030 S90
annotation, `CURRENT_history.md` (S88 moved). **Doc Protocol v5 DRAFT** at
`docs/operational/MERDIAN_Documentation_Protocol_v5_DRAFT.md`.

## AM-1 post-close (2026-10-06 → 10-07)

**The delta after the AM-1 close**, folded into the registers at AM-2 / S91 (docs only). This
block **points**; the detail lives in the registers named. Ten commits, `699398f..490b088`,
`490b088` is HEAD.

| Commit | What |
|---|---|
| `699398f` | Name correction in prose, titles and commit prefixes; identifiers unchanged (`CLAUDE.md` rule 20, ruling **S90-K**) |
| `16f1378` | Deploy window by risk class (ruling **S90-J**); Marketview `/staging/` in `deploy/nginx` |
| `47c795c` · `8f0007f` | Tick freeze every 5 min, 10-day retention — answers **TD-S90-NEW-4**; roadmap **R2.7** |
| `a80176e` | Replay harness v0: `replay_contracts.py --check` over 6 golden days + `tests/run_offline.sh` (**R2.1**) |
| `df80dec` | Per-leg ledger rows (`log_child_run`, ADR-031 D3a/D7) so chain provenance can reach 100 % (**R0.3**) |
| `6d9f4f7` | CAS close picks the close-slot bar, not the last bar (**TD-S90-NEW-12**) |
| `2e66d4f` | Spot contract session end 15:15 via `data_contracts.session_end_ist` (ruling **S90-L**, **R1.2**) |
| `1708a1c` | CAS reconciliation, two-source auto-correct, scheduled 08:50 IST (ruling **S90-M**) |
| `490b088` | EOD sweep on its own cursor row + cursor-moved guard (**TD-S90-NEW-14**) |

**Marketview:** three further commits in `~/meridian-connect` — `eda1ca0`, `c53dbea`, `255cca0` —
and **live = staging = `origin/main` = `255cca0`** (measured 2026-10-07), which **closes
TD-S90-NEW-2**.

**Database and data writes:** `sql/2026-10-06_s90_spot_session_end.sql` applied; **58 CAS close
bars backfilled** plus 2026-10-06 captured live, **3 SENSEX bars hand-corrected**; DH-905 remaps
verified at **1,379 / 1,381 = 99.86 %** coverage on 10-01.

**New TD IDs: TD-S90-NEW-12 / -13 / -14** (`tech_debt.md`, prepended, plus an AM-2 addendum on the
S90 status footer). **New rulings S90-K / -L / -M** (`rulings_s90.md`, the single source). Roadmap
**v2.8**. `merdian_reference.json` **v69**.

## NEXT SESSION PICKS UP — as S90 left it (SUPERSEDED by the S91 list above)

**Dated, today first.**

1. **Wed 2026-10-07 — verify the AM-1 post-close deploys. None of this is verified yet.**

   | When (IST) | Check | PASS looks like |
   |---|---|---|
   | 08:50 | first scheduled CAS reconciliation, `logs/cas_recon.log` | every day MATCH; no MISMATCH and no auto-correct needed — **closes TD-S90-NEW-12** |
   | 09:30 | `v_provenance_coverage_daily` after the first cycles | chain at **100 %** (was 52 % — one `run_id` per N legs) — **R0.3** exit |
   | 15:20 / 15:25 | `cycle_health` for `market_spot_snapshots` | **OK**, judged at the product's own `session_end_ist`, not MISSING — **R1.2**, ruling **S90-L** |
   | 16:10 | the `equity_eod_aws` lap | **`[S90_CURSOR_GUARD]` count 0** in `logs/eod.log`, and EOD coverage near 100 % of the active universe |
   | 10:15:59 | **A4 re-run, SENSEX dte 1** (item 3 below) | per its own pre-commitment — if T1 refuses, the L7/L8 views are DROPped |

   Also still owed from the 10-06 list, unverified here: ENH-133 first live rows (G1–G3,
   A(c)–A(e), R1–R6), WCB moving on live ticks (S90-G), and `v_run_trace` for the latest cycle
   (R0.7). Runbook `docs/research/s90_agentic/runbook_2026-10-06_1600.md` §5.
2. **NIFTY L9 stage-1 max-pain arm** (TD-S80-NEW-1), pre-registered before any
   read — carried from S89.
3. **Wed 2026-10-07, 10:15:59 IST — A4 re-run, SENSEX dte 1** — carried from S89. **The ENH-98
   L7/L8 views were NOT applied in S90** (S90-A scoped the apply to ENH-133), so the
   pre-committed DROP has nothing to drop until they are.
4. **~Tue 2026-10-13 — drop the S90-H backup tables** after a clean week (TD-S90-NEW-11).
5. **Tue 2026-10-20 (holiday) — the first live test of R0.8:** no chain rows written,
   `cycle_health` CLOSED (TD-S89-NEW-1 closes on it).

**Undated — the tracker is the list** (roadmap §3). Next by its order: R1.10 scrip-map sync ·
push Marketview (deploy key) · R0.6 authenticated Settings write + `config_version` · R1.7 status
on Home (needs the browser read-path decision) · R0.7 fold the ADR-029 file ledger · the ~26
other inline calendar gates · R1.6 against the fixture files · R2.1 diff in the deploy path ·
**Doc Protocol v5 ruling** · ENH-133 tier (still operator-to-assign). S89's undated list stands
below.

## OPERATOR RULINGS, S90

**All rulings live in `docs/research/s90_agentic/rulings_s90.md`**, the single source.

| # | Topic |
|---|---|
| **S90-A / S90-F** | ENH-133 applied 10-05; writer wired the same night (F amends A) |
| **S90-B** | ADR-030 D1: front leg (W1) only until a W2 compute path is ruled |
| **S90-C** | ADR-031 accepted (roadmap A-8) |
| **S90-D** | Stages 0–2 inside parity scope (A-5); parity closes at the Stage 2 exit |
| **S90-E** | `update_parameter()` revoked from PUBLIC/anon/authenticated; Settings read-only |
| **S90-G** | WCB: fix the writer (live LTP over the prior close, no stale fallback) |
| **S90-H** | EOD dates: IST ingest + one-time +1 day migration |
| **S90-I** | ADR-031 D3a: provenance via `run_id` → ledger |
| **Close mode** | Hybrid close (2026-10-06 05:21 IST): the tracker holds progress; protocol files point; Doc Protocol v5 drafted, not ruled |
