# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S92 — 2026-10-08 → 2026-10-09 (Thursday–Friday, live sessions).** The parity programme driven
to closure, a post-parity priority track ruled, its first item pre-registered and part-run, and
the operator's 3D experiment authored as an optional view. This block points; the detail lives
in the files named. Rulings: `docs/research/s92_parity/rulings_s92.md` (S92-A…J, the single source).

**meridian-engine — all pushed.** `9b7d03b` S92-A + ADR-025 Amendment C · `e0b9d03` / `0965755` /
`0c36c7e` TD-S91-NEW-15, -13, -14 · `f60708d` / `0eceee1` / `bd91d27` / `146a324` `core/ts_parse.py`
and TD-S91-NEW-2 site 7 / TD-S91-NEW-6 · `5f51231` S92-C…F + `v_pin_board` · `8853539` ADR-025 C7/C8 ·
`e85cf7a` R2.4 · **`579d273` ADR-025 Amendment D — parity CLOSED** · `1606305` S92-I · `b70a025` /
`698dc93` P1 pre-registration, SQL and scorer · `a34a312` S92-J · this close.
**meridian-connect:** `5563bb7` Pin/Flows design pass · **`1deeb87` L13 bind — live** · branch
`lab-3d` `78fb26e` (the 3D experiment, not on `main`).

**What was established**

1. **Hedgewall parity is CLOSED** (ADR-025 **Amendment D**, `579d273`). BUILT **13 of 14**, L11
   DECLINED-ON-EVIDENCE, PENDING 0 (C8); the live board renders every BUILT layer (C3 at `255cca0`,
   C7 at `5563bb7` / `1deeb87`); R2.4 reported. D3 deviations standing at close: L7/L8 flow-vs-book
   (D-4, PPC-1), L12 pressure leg (D-5a), SENSEX L13 (TD-S84-NEW-4). The S92-A pause on harness
   work ended with it.
2. **R2.4 reported, not gating** (`docs/research/s92_parity/r24/`): 40 fixtures from the reference's
   own screenshots, 199 field scores, read twice blind. Pin = MERIDIAN's leader or in its top 5 in
   **20 of 26**; net GEX sign **17 of 21**; walls **8 of 17**; HHI runs **~2×** in the reference
   (a narrower strike window, not a different ranking); flip comparable only to the legacy
   `flip_level`; ± peaks unresolved (n = 8).
3. **Presentation through Lovable without trusting it.** Guard v2 (path allowlist, one named read,
   credential and L78-1 scans, tsc + build) and a read-only ACL fingerprint, identical across all
   three rounds. The guard **stopped one build** — the operator's 3D experiment, kept on `lab-3d`.
4. **The S91 defects moved from diagnosed to fixed — none yet verified by a live cycle.**
   `core/ts_parse.py` is the shared PostgREST timestamp parser (41 asserted cells, run_offline step
   10/10); **TD-S91-NEW-6's mechanism is settled** — a trimmed fraction, NULL is impossible
   (`is_nullable = NO`) — and fixed at site 7; **TD-S91-NEW-15** basis skip exits 0 (S92-B, that call
   site only); **TD-S91-NEW-13/14** validator trading-day gate + per-key dedupe.
5. **Post-parity priority track, ruling S92-I** — roadmap §2.1, P1–P8, each followed to DONE or
   DECLINED-ON-EVIDENCE. **P1 (level test) is pre-registered** (`P1_level_test_prereg_2026-10-09.md`,
   `git hash-object 7a708a64…`) with SQL and scorer committed before any outcome query. Part 1
   passed: **N = 85 NIFTY / 84 SENSEX**, split fixed at 2026-08-26 / 08-27, no grid, spot or expiry
   failures, no contamination range. **Part 3 and Part 2 are owed after 15:40 IST.**
6. **S92-J — the 3D view, optional.** `v_gex_strike_terrain` authored (settled run per session,
   NULL `gex_cr` where no gamma, ENH-123 pain by running sums); on a synthetic fixture: max pain
   28/28 against `gex_pin_maxpain_history`, ACL anon=r / merdian_ro=r, 90 ms. Lovable prompt and a
   one-time guard that fails if three.js reaches the 2D bundle. **Not yet applied.**

**Corrections to my own work.** The P1 Part 2 extract was committed as one statement that took
**49 s** on a fixture; it was rebuilt on temp tables (**3 s, identical output**) **before** it was run
against the database. A side-chat candidate list carried L7/L8 as "not started" the morning they
went live; corrected against ADR-025 C7 before it reached the tracker. The P1 pre-registration's
leader tie-break differs from `v_gex_strike_rank`'s **on exact ties only**; recorded in
`p1/README.md`, and Part 2 reports `ties_at_rank3`.

**Registers touched:** ADR-025 (Amendments C and D), Decision Index, `rulings_s92.md` (S92-A…J),
roadmap §2.1 and R2.4, Enhancement Register (clause-3 rows; **ENH-139** filed for S92-J),
`tech_debt.md` (TD-S92-NEW-1…4; S92 status on TD-S91-NEW-2, -6, -13, -14, -15),
`merdian_reference.json` **v71**, `CLAUDE.md` **v1.65**, `CURRENT_history.md` (S90 moved),
`session_log.md`, **S93 starter**.

## NEXT SESSION PICKS UP

**S93 starter: `docs/session_notes/S93_dev_starter.md`.**

1. **P1, today after 15:40 IST** — Part 3 (`p1_part3_replay_check.sql`, expect zero rows), then
   Part 2 as one execution, export JSON → `p1_score.py` → result doc → **the S92-I decision point**
   (if the levels do not beat the null, P2–P8 are re-planned before more is built).
2. **S92-J** — apply `sql/2026-10-09_s92_v_gex_strike_terrain.sql` §1–3, run §4a–4d each alone;
   then ACL fingerprint, BASE, the Lovable prompt, `mv_lovable_guard_lab3d.sh`, a `/staging/` read
   against the view, promote. Closes TD-S92-NEW-2.
3. **Verifications owed — none is recorded as done:**

   | Check | PASS looks like | Closes |
   |---|---|---|
   | basis step on 10-09, the first full day of `bd91d27` | **0 DATA_ERROR** runs | TD-S91-NEW-6 |
   | basis step 08:31–09:26 IST on 10-09 | the 12 no-input cycles **exit 0**, `exit_reason` still `SKIPPED_NO_INPUT` | TD-S91-NEW-15 (basis site) |
   | `gex_cycle_history` front leg vs `gamma_metrics` | **77 of 77** | TD-S91-NEW-1 |
   | Telegram, chat **unmuted** | ≈ 14 in-session sends, none overnight | TD-S91-NEW-12 |
   | **Tue 2026-10-20** (weekday holiday) | validator silent; no chain rows; `cycle_health` CLOSED | TD-S91-NEW-13, TD-S89-NEW-1 / R0.8 |

4. **Rulings owed:** whether a BUILT layer that later breaks **reopens parity** or is an ordinary
   defect on its register (left open by Amendment D) · **Doc Protocol v5** (drafted S90).
5. **P2–P8** per roadmap §2.1, after P1's decision point. Dev documents for them (ENH entries for
   the DEX standing book P6 and the flow leg P7, design notes for P2 / P4) **wait on P1** — operator
   sequencing, 2026-10-09.
6. **TD-S92-NEW-1** (*"contracts"* wording — a Lovable layout pass) · **-3** (cited probe missing from
   git) · **-4** (`authenticated` privileges on the S92 views; S92-J's view already revokes them).
7. **Dated:** ~Tue 2026-10-13 drop the S90-H backup tables (TD-S90-NEW-11).
8. **Carried:** TD-S91-NEW-2 sites 1, 3, 4, 5, 6 → adopt `core.ts_parse` · TD-S91-NEW-3 08:40 IST
   Zerodha preflight (design agreed, not built) · TD-S80-NEW-1 NIFTY L9 stage-1 arm.

## OPERATOR RULINGS, S92

**All rulings live in `docs/research/s92_parity/rulings_s92.md`**, the single source.

| # | Topic |
|---|---|
| **S92-A** | Parity closes on ADR-025 D1 + the P6 render pass; R2.4 inside parity, reported not gating (amends S90-D) |
| **S92-B** | `SKIPPED_NO_INPUT` → exit 0 at the basis call site only |
| **S92-C…F** | L7/L8 badge and D-4 as a D3 deviation; the Pin tab reads `v_pin_board`; L12 disposition |
| **S92-G / -H** | L13 binds `v_oi_rotation_since_open`; SENSEX L13 withheld |
| **S92-I** | Post-parity priority track P1–P8, followed to conclusion |
| **S92-J** | The 3D view, optional at `/board/3d`, reading one view |

## Previous session S91 / AM-2

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

## NEXT SESSION PICKS UP — as S91 left it (SUPERSEDED by the S92 list above)

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
