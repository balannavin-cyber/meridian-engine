# CURRENT.md — MERIDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S89 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** **S86 at the S88 doc-close**, **S87 at the S89 doc-close** and **S88 at the S90 / AM-1 doc-close**, each moved verbatim rather than retyped — the S87 move asserted byte-identical at **19,184 B**, sha256 `52b9364b…` on both sides. **S89 moved at the S91 close**, asserted byte-identical at **8,079 B**, sha256 `e2bec976…` on both sides. **S90 (with the AM-1 post-close block) moved at the S92 close**, asserted byte-identical at **9,482 B**, sha256 `8466bfbb…` on both sides. **S91 / AM-2 moved at the S93 close**, asserted byte-identical at **9,208 B**, sha256 `d5dc4e19…` on both sides. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S93 — 2026-10-09 (Friday, live session).** P1 scored and returned **NO on both arms**, which
is the S92-I decision point; P6 authored, tested and committed but **not applied**; three S91
defects verified; one shared parser widened. This block points; the detail lives in the files
named. Rulings: `docs/research/s92_parity/rulings_s93.md` (S93-A, S93-B).

**`origin/main` — all pushed; production tree `~/meridian-engine` pull owed** (operator,
`git pull --ff-only`). `cf40b95` `core/ts_parse.py` accepts the psql `+HH` offset · `333fc33`
the P6 offline test adopts `core.ts_parse`, first run · `71cd100` wired in as `run_offline.sh`
step **11/11** · `62de679` **P1 scored** · this close.
**meridian-connect: untouched** (live stays `417e966`).

**What was established**

1. **P1 (level test) is DONE and the answer is NO.** A-NIFTY holdout **−0.116**, 97.5 %
   [−0.365, 0.102]; B-NIFTY holdout **−0.0867**, [−0.282, 0.0902]. Both intervals include zero
   **and** both holdout means are below half their calibration means, so each fails §5.8 on
   both limbs. The null is the pre-registration's §5.5 offset-preserving null, in its words:
   *"Each level's side of spot and its distance in σ are preserved; only 'these are today's
   strikes' is broken."* Pre-registration `7a708a64…` unchanged and unamended. Result doc:
   `docs/research/s92_priority/P1_level_test_result_2026-10-09.md`.
2. **Two post-hoc patterns are recorded and marked unclaimable.** Calibration *e* positive and
   holdout *e* negative in **7 of 8** primary rows; `e_dA` positive at DTE 0–1 and negative at
   DTE 4+ in all four cells. Both are read off the data that produced the NO, after seeing it;
   (a) is what a calibration-fitted effect leaves when it does not transfer. A DTE-conditioned
   test is a **new** pre-registration, never an amendment.
3. **P6 is AUTHORED — NOT APPLIED (S93-A).** The view, design note and offline test are in git;
   no `CREATE`/`COMMENT`/`GRANT` has been issued. **ENH-140 stays UNFILED** pending S93-B.
   Roadmap §2.1's P6 row now says so. Its Section 4 checks, 4i included, are **unrun** because
   there is no live object.
4. **The offline suite is 11 steps and the DEX test is in it.** Wired only after its first
   standalone pass. A non-zero exit — including the test's own rule-23 refusal, exit 2 — is a
   FAIL, proved by a mutant stub: `OFFLINE FAIL`, suite exit 1. Peak RSS 293,000 kB under
   `ulimit -v 700000`; **the ceiling was not raised**.
5. **Three S91 verifications closed on measured evidence** (operator-run `roq.sh` reads):
   **TD-S91-NEW-6** 0 `DATA_ERROR` over 84 runs → **CLOSES**; **TD-S91-NEW-15** 12/12 no-input
   basis cycles exit 0 → basis site verified (`run_merdian_shadow_runner_aws.py:364` **stays
   open**); **TD-S91-NEW-1** `gex_cycle_history` front leg vs `gamma_metrics` **78/78** (10-08)
   and **77/77** (10-09).
6. **`core/ts_parse.py` widened, in its own commit.** There are **two wires, not one**:
   PostgREST renders UTC as `+00:00`, psql as `+00`, and `bin/roq.sh` is psql — so golden
   fixtures exported via `roq.sh` carry a form the shared parser returned **None** on (the
   `2026-10-01_SENSEX` fixture did — the P6 test's first run died on it). `norm_offset`
   added, stated as the module's one piece of new logic. Widening proved by re-parsing the
   corpus through the pre-S93 body: **23 inputs byte-identical, 7 newly accepted**.

**Corrections to my own work.** The first run of the P6 test **failed on the fixture's
timestamp format** and reached no assertion — `ast.parse` and `py_compile` cannot see a string
format, so "compiled, not run" bought nothing here. Four documents said view check **4i points
at the expected CSV**; 4i reads two *live* exports and never opens it. The test still cited
**4d "(additivity, in SQL)"** for the leg totals after 4d's additivity arms had been relabelled
arithmetic-sanity-only. I claimed one heredoc invocation is what 4i's `run_id` check **depends
on** — psql runs each statement in autocommit with its own snapshot, so it narrows the race and
the set-equality assertion is the guard. Three statements drafted into the P1 result doc were
struck before writing, each false against the scorer output: a "nearer zero than any other"
claim, `n = 17` for the smallest DTE bucket (it is **15**), and an uncited "clean" over four
preconditions. An EOL check written in text mode **could not report CRLF at all** and was redone
in binary. A `PIPESTATUS` demo and an `awk` range gate each measured nothing and were rebuilt.

**Registers touched:** `rulings_s93.md` (**new**, S93-A / S93-B), roadmap §2.1 (P1 → DONE, P6 →
AUTHORED — NOT APPLIED, decision point), `tech_debt.md` (**TD-S93-NEW-1…3 filed**; TD-S91-NEW-1,
-6, -15 verified), Enhancement Register (Part 8 note; **no id minted**), P6 design note (§4.3,
§7, carry 9), `p1/README.md`, `CURRENT.md` (S91 / AM-2 → `CURRENT_history.md`, byte equality
asserted at **9,208 B** / sha256 `d5dc4e19…`), `session_log.md`.

**No ADR filed, none amended. No DDL applied. No data migration.** One ruling is owed: S93-B.

## NEXT SESSION PICKS UP

1. **S93-B — the P2–P8 re-plan ruling. This is the gate on everything below.** P1 returned NO
   on both arms, which is the S92-I decision point: *"the operator re-plans everything below
   before more is built."* Nothing further is built until it is made.
2. **Pull the production tree** — `~/meridian-engine`, `git pull --ff-only` to `62de679` plus
   this close. Four commits are on `origin/main` and the box has none of them; `core/ts_parse.py`
   is shared code, so until the pull the box runs the pre-S93 parser. Preflight compares the two
   hashes (rule 2), so this is also the gate on any live run.
3. **DEX view apply — ONLY if S93-B allows it.** Sections 1→3 as **one execution**, then
   Section 4 including **4i** (export the view and the chain for the same `run_id`s, then
   `python3 tests/test_dex_recompute.py --compare --view <csv> --chain <csv>`). The file is
   `sql/2026-10-09_s93_v_dex_standing_book.sql`; nothing in it has touched the database.
4. **Telegram, chat unmuted** — ≈ 14 in-session sends, none overnight. **TD-S91-NEW-12** closes
   on it and is still not recorded as done.
5. **3D view** — check it after a full live session, then delete
   `/var/www/marketview.bak-1deeb87` (the S92-J rollback copy).
6. **Tue 2026-10-20 (weekday holiday)** — validator silent; no chain rows; `cycle_health`
   CLOSED. **TD-S91-NEW-13**, **TD-S89-NEW-1 / R0.8**.
7. **~Tue 2026-10-13** — drop the S90-H backup tables (**TD-S90-NEW-11**).
8. **Rulings owed:** **S\*** the re-priced zero-Δ level (P6 §5.2) · **vendor delta vs an
   in-house Black–Scholes delta** (P6 carry 8 — note §4.3: on the 10-01 dte-0 fixture, 112/112
   gap rows carry `iv = 0`, so a BS delta would fill none of them) · **ADR-015's
   sign-convention gloss**, inverted against the ADR-014 §2.3 it claims to carry unchanged
   (P6 §3.1, carry 7) · whether a BUILT layer that later breaks **reopens parity** (left open by
   ADR-025 Amendment D) · **Doc Protocol v5** (drafted S90, still not ruled).
9. **Filed this session:** **TD-S93-NEW-1** (`run_offline.sh`'s positional `PIPESTATUS` — eleven
   mechanical edits) · **-2** (`.gitignore:43 *.csv` hides the DEX expected table; a negation
   rule, never `git add -f`) · **-3** (P1 §6.6 has no artefact).
10. **Carried:** TD-S91-NEW-2 sites 1, 3, 4, 5, 6 → adopt `core.ts_parse` · TD-S91-NEW-3
    08:40 IST Zerodha preflight (design agreed, not built) · TD-S80-NEW-1 NIFTY L9 stage-1 arm ·
    TD-S92-NEW-1 / -3 / -4 / -5 / -6.

## OPERATOR RULINGS, S93

**All rulings live in `docs/research/s92_parity/rulings_s93.md`**, the single source.

| # | Topic |
|---|---|
| **S93-A** | P6 authored, tested and committed ahead of P1's decision point, and **not applied**; ENH-140 stays unfiled |
| **S93-B** | **OWED** — the P2–P8 re-plan after P1 returned NO on both arms |

## Previous session S92

**S92 — 2026-10-08 → 2026-10-09 (Thursday–Friday, live sessions).** The parity programme driven
to closure, a post-parity priority track ruled, its first item pre-registered and part-run, and
the operator's 3D experiment authored as an optional view. This block points; the detail lives
in the files named. Rulings: `docs/research/s92_parity/rulings_s92.md` (S92-A…J, the single source).

**meridian-engine — all pushed.** `9b7d03b` S92-A + ADR-025 Amendment C · `e0b9d03` / `0965755` /
`0c36c7e` TD-S91-NEW-15, -13, -14 · `f60708d` / `0eceee1` / `bd91d27` / `146a324` `core/ts_parse.py`
and TD-S91-NEW-2 site 7 / TD-S91-NEW-6 · `5f51231` S92-C…F + `v_pin_board` · `8853539` ADR-025 C7/C8 ·
`e85cf7a` R2.4 · **`579d273` ADR-025 Amendment D — parity CLOSED** · `1606305` S92-I · `b70a025` /
`698dc93` P1 pre-registration, SQL and scorer · `a34a312` S92-J · `eb69ac4` close · **post-close
delta:** `9f7cc30` / `e9f65fd` view fixes and live verification · this delta (S92-J live).
**meridian-connect:** `5563bb7` Pin/Flows design pass · `1deeb87` L13 bind · **`417e966` optional 3D view —
live 2026-10-09 ~11:20 IST** (S92-J; base `1deeb87`; rollback copy `/var/www/marketview.bak-1deeb87`).

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
6. **S92-J — the 3D view, optional, LIVE** (`meridian-connect` `417e966`, ~11:20 IST 10-09).
   `v_gex_strike_terrain` applied and verified live: 14 sessions per symbol as anon; pain curve
   equal to ENH-123 `v_gex_max_pain` strike for strike (NIFTY 54 / SENSEX 85, 0 mismatches); ACL
   anon=r / merdian_ro=r. Lovable round under `mv_lovable_guard_lab3d.sh 1deeb87`: guard PASS (one
   read of the view, no raw-table reads, three.js absent from the 672 KB entry chunk); **ACL
   fingerprint identical before and after** (relations 344, anon_public_privs 250,
   anon_writable_objs 0); `/staging/` read against SQL — 14 sessions 09-21 → 10-09, peak |γ|
   5,802,384 / 6,344,113, expiry days, NULL holes (28 / 75 cells), max pain 22500 / 72400 on the
   10:55 run — all equal; 375 px no sideways scroll; legend "optional view". Promoted from the
   checked commit with no pull. **Closes TD-S92-NEW-2.** Install snag filed as TD-S92-NEW-6.

**Corrections to my own work.** The P1 Part 2 extract was committed as one statement that took
**49 s** on a fixture; it was rebuilt on temp tables (**3 s, identical output**) **before** it was run
against the database. A side-chat candidate list carried L7/L8 as "not started" the morning they
went live; corrected against ADR-025 C7 before it reached the tracker. The P1 pre-registration's
leader tie-break differs from `v_gex_strike_rank`'s **on exact ties only**; recorded in
`p1/README.md`, and Part 2 reports `ties_at_rank3`. **Post-close:** the first live apply of
`v_gex_strike_terrain` showed **13** sessions (10-02, a holiday with no calendar row and only a 15:40
run, was ranked) — fixed to rank only dates with a settled run (`9f7cc30`, TD-S92-NEW-5); check 4c
compared nothing live (`gex_pin_maxpain_history` ends 09-18) and was replaced by an ENH-123
comparison, and the fixture-only "28/28" claim corrected in ENH-139 (`e9f65fd`); a guard hash was
stated before it was computed and corrected in chat (actual `09979feaf0f5145a`).

**Registers touched:** ADR-025 (Amendments C and D), Decision Index, `rulings_s92.md` (S92-A…J),
roadmap §2.1 and R2.4, Enhancement Register (clause-3 rows; **ENH-139** filed for S92-J),
`tech_debt.md` (TD-S92-NEW-1…4; S92 status on TD-S91-NEW-2, -6, -13, -14, -15),
`merdian_reference.json` **v71**, `CLAUDE.md` **v1.65**, `CURRENT_history.md` (S90 moved),
`session_log.md`, **S93 starter**. **Post-close delta:** CURRENT, session_log, `tech_debt.md`
(TD-S92-NEW-2 → Resolved; TD-S92-NEW-5, -6), ENH-139 → LIVE, `rulings_s92.md` S92-J, reference
`_s92_addendum.post_close_delta`, `CLAUDE.md` footer, S93 starter §2, `lovable_prompts/s92/README.md`.

## NEXT SESSION PICKS UP — as S92 left it (SUPERSEDED by the S93 list above)

**S93 starter: `docs/session_notes/S93_dev_starter.md`.**

1. **P1, today after 15:40 IST** — Part 3 (`p1_part3_replay_check.sql`, expect zero rows), then
   Part 2 as one execution, export JSON → `p1_score.py` → result doc → **the S92-I decision point**
   (if the levels do not beat the null, P2–P8 are re-planned before more is built).
2. **S92-J — DONE** (live `417e966`; TD-S92-NEW-2 resolved). Residuals: TD-S92-NEW-6 (box install
   path); delete `/var/www/marketview.bak-1deeb87` once live has run a full session.
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
   git) · **-4** (`authenticated` privileges on the S92 views; S92-J's view already revokes them) ·
   **-5** (no `trading_calendar` row for 10-02 — one-row insert, operator's call) · **-6** (box has no
   bun; guards' `npm ci --silent` hides install failures).
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

