# PK pruning audit — S104 (2026-10-31) — running record, LIST ONLY

Scope: 195 project docs + 1 file (`Ashwin_Badrinath_analysis_Mar-Oct2026.pdf` — a file, listed, not touched).
Method: every doc read; category per doc; evidence (superseding doc + how compared, inbound referrers via project_search, where content survives) mandatory for any non-KEEP row. Nothing deleted until the operator says "delete batch N".

Categories: KEEP-core | KEEP-retail | DUPLICATE-of | SUPERSEDED-by | STALE | UNKNOWN | DEFERRED (candidate, but not until the S103 doc-close runs).

Facts the audit leans on (read this session):
- Doc-closes that have RUN: S98+S99 (`3ad5c81`, in S100), S100 (`7b91d1a`, in S101), S101 (`3abb83f`, in S102), S102 (`762e4d7`, in S103 Part A; CURRENT.md S102 block, CLAUDE.md v1.74, session_log S102 entry). **S103 doc-close has NOT run** — S103_close_inputs, rulings_s103 + addendum, S104 prompt and everything the S104 prompt names are live.
- Operator precedent (S99_close_inputs §7): "The S97–S99 session prompts and S97 close inputs stay deleted (superseded)." Closed-session prompts/close inputs are deleted after their doc-close lands.
- Register copies in PK are LATEST extracts (`tech_debt_LATEST.md`, `MERDIAN_Enhancement_Register_LATEST.md`, `merdian_reference_LATEST.json`) + full `CLAUDE_history.md`, `agentic_layer_roadmap_S90.md`, `claude/CURRENT.md`, `claude/session_log.md` (S100 prompt Part A; re-uploaded 10-30 after the S102 close).
- Git paths named by the docs themselves: session close inputs → `docs/research/s<N>/`; rulings → `docs/research/s92_parity/rulings_s<N>.md` (S92+), `docs/research/s90_agentic/rulings_s90.md`, `docs/research/s91_agentic/rulings_s91.md`; Lovable rounds → `docs/lovable_prompts/s<N>/`; applied SQL → `sql/`; S96 design notes → `docs/research/s96_priority/{p7,guard,p3b}/`; P1 result → `docs/research/s92_priority/`.

## Family C1 — session prompts / close inputs (claude/)

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| claude/S104_session_prompt.md | S104 carry-forward prompt + command appendix A1–A7 (written 10-31 09:11) | KEEP-core | live | keep |
| claude/S103_close_inputs.md | S103 close inputs (state at 09:11 10-31, facts, TDs to file, Monday checks) | KEEP-core | S103 doc-close not run | keep |
| claude/S103_session_prompt.md | S103 prompt: S102 doc-close Part A, six engine bundles Part B, R19/§2.2 Part C | DEFERRED → SUPERSEDED-by claude/S104_session_prompt.md + claude/S103_close_inputs.md | Part A ran (`762e4d7`, CURRENT.md S102 block); Part B ran (rulings_s103 "Engine state at 20:03": `f63368a…b2a5ce6` six bundles, suite 29/29); Part C items carried in S104 prompt action list 6. Git: not committed (session prompts never are). Precedent: S97–S99 prompts deleted after their close. | propose delete AFTER the S103 doc-close lands (same precedent) |
| claude/S102_session_prompt.md | S102 prompt: S101 doc-close, carried reads, §2.2 | SUPERSEDED-by claude/CURRENT.md (S101+S102 blocks), claude/S103_session_prompt.md | S101 doc-close ran `3abb83f` (session_log S102 entry, CURRENT.md "Previous session S101"); every Part B/C item restated in S102_close_inputs §3 and CURRENT.md NEXT. Not in git (prompts never committed). Referrers: S102_close_inputs §4 ("From S101 §5 / S102 prompt") — pointer only, content restated there. | delete batch 1 |
| claude/S102_close_inputs.md | S102 close inputs (state, six bundles table, ADR-032 D1 evidence, TDs, §D.56 1–16) | SUPERSEDED-by git `docs/research/s102/S102_close_inputs.md` + registers (CURRENT.md S102 block cites that path; TD-S102-NEW-1…8 filed; §D.56 filed; CLAUDE.md v1.74) | S102 close ran in S103 Part A per CURRENT.md ("closed in S103 Part A … Evidence and findings: `docs/research/s102/S102_close_inputs.md`"). Referrers: S103_session_prompt (itself a candidate), rulings_s102 ("Rulings owed: see S102_close_inputs §4" — those owed rulings were taken as S103-A…L, rulings_s103 "Mapping" para), CURRENT.md (cites the git path, not the PK copy). | delete batch 1 |
| claude/S101_session_prompt.md | S101 prompt: retail interface packaging (merdian_compute) + Monday Part C | SUPERSEDED-by claude/CURRENT.md (S101 block → CURRENT_history), rulings_s101 | S101 close ran `3abb83f`; Part A built (`11f2cbe`…`4a1d8e1`), Part B/C done (S101_close_inputs §2). Not in git. Referrers: none found by project_search beyond S101_close_inputs ("Next: S102_session_prompt"). | delete batch 1 |
| claude/S101_close_inputs.md | S101 close inputs (evidence table, findings, §D.55 1–25) | SUPERSEDED-by git `docs/research/s101/S101_close_inputs.md` + registers (TD-S101-NEW-1…17, §D.55, CLAUDE.md v1.73 rule 25) | rulings_s101 header: "Evidence and findings: S101_close_inputs.md (→ docs/research/s101/ at the doc-close)"; session_log S102 entry confirms `3abb83f` applied with TD-S101-NEW-1…17 and §D.55. Referrers: rulings_s101 (pointer to the git path), S102_session_prompt (candidate). | delete batch 1 |
| claude/S100_session_prompt.md | S100 prompt: S98+S99 doc-close, weekend build list, Monday Part C | SUPERSEDED-by rulings_s100 + CURRENT.md/session_log (S100 entry) | S98+S99 close ran `3ad5c81` (S100_close_inputs commits table; session_log S100 entry); Part B items ruled S100-A…S; PK model paragraph restated in S99_close_inputs §7 and S100-A. Referrers: S99_close_inputs §7 ("see S100_session_prompt Part A and pk_extract_s99.py") — pointer; S100_close_inputs none. | delete batch 1 |
| claude/S100_close_inputs.md | S100 close inputs (commits table, Marketview rounds, SQL applied, TD footers, §D.54) | SUPERSEDED-by registers (session_log S100 entry lists every commit, TDs, §D.54; CURRENT_history S100 block) | S100 close ran `7b91d1a` (S101_session_prompt "HEAD 7b91d1a (S100 doc-close)"; session_log S101 entry). Git copy: not stated in the doc; the S101 prompt pattern commits `docs/research/s<N>/` close inputs from S101 on — S100's git path UNVERIFIED → content survives in the registers (session_log entry is a full restatement). Referrers: none by project_search except S100_partC_additions (candidate). | delete batch 1 (content survives in registers; no separate git copy claimed) |
| claude/S100_partC_additions.md | Monday 10-26 Part C read list additions (S100-M/N/R/Q.1/S checks) | SUPERSEDED-by claude/S101_close_inputs.md §2 (every check read and PASSed 10-27/10-28) → itself superseded by git/registers | Checks executed and recorded (S101_close_inputs board reads rows). Referrer: S100_close_inputs ("Part C additions — partC_additions.md") only. | delete batch 1 |
| claude/S99_close_inputs.md | S99 close inputs (commits, footers, TD-S99-NEW-1, §D.53, delivery route, PK model) | SUPERSEDED-by registers (`3ad5c81`: session_log S99 entry, TD-S99-NEW-1, §D.53) | S98+S99 close ran `3ad5c81` (S100_close_inputs, session_log). §6 delivery route = ruling S99-A (rulings_s99, kept) and A7 of the S104 prompt. §7 PK model = restated in S100 prompt / S100-A. Referrers: S100_session_prompt (candidate). | delete batch 1 |
| claude/S98_close_inputs.md | S98 close inputs (footers, R42–R49 rows, §D.52, S98-B build state, EOS hashes) | SUPERSEDED-by git `docs/research/s98/S98_close_inputs.md` (S99_close_inputs §5 names it for commit at the close) + registers (`3ad5c81`: §D.52, R38–R49 homed in tracker §2.2 per S100-B) | S98-B build state obsolete (deployed `2edd25f`). Referrers: S99_close_inputs §5, S100_session_prompt (both candidates). | delete batch 1 |

## Family C2 — rulings (all KEEP-core, never proposed)

| path | what it is | category |
|---|---|---|
| claude/rulings_s103.md | S103-A…L + findings + round 1 record + engine state 20:03 | KEEP-core |
| claude/rulings_s103_addendum_rounds_2_3.md | S103 rounds 2–3, S103-M…T, `s103v`, ADR-032 study rulings, S103-T amendment; to merge at S103 close | KEEP-core |
| claude/rulings_s102.md | S102-A…F | KEEP-core |
| claude/rulings_s101.md | S101-A…H | KEEP-core |
| claude/rulings_s100.md | S100-A…S, Q.1 | KEEP-core |
| claude/rulings_s99.md | S99-A…I + applied-after | KEEP-core |
| claude/rulings_s98.md | S98-A…E, E.1 + R42–R46 | KEEP-core |
| claude/rulings_s97.md | S97-A…N | KEEP-core |
| claude/rulings_s96.md | S96-A…J | KEEP-core |
| claude/rulings_s95.md | S95-A…G (Doc Protocol v5 adopted, S95-E) | KEEP-core |
| claude/rulings_s94.md | S94-A…I | KEEP-core |
| claude/rulings_s92.md | S92-A…J | KEEP-core |
| claude/rulings_s90.md | S90-A…J | KEEP-core |
| rulings_s93.md (root) | S93-A/B | KEEP-core (root-level placement noted; no claude/ duplicate exists) |
| rulings_s91.md (root) | S91-A…E | KEEP-core (same) |
| rulings_s87.md (root) | S87 routing / ADR-029 rulings #1–#18 | KEEP-core (same) |

## Family C3 — claude/ research, design and working docs (S88–S100)

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| claude/B3_reads_2026-10-24.md | S100 B3 reads on past data: R10, R8, R7, R18 findings (10-24) | SUPERSEDED-by git `docs/research/s100/B3_reads_2026-10-24.md` (path stated in S100_close_inputs "Findings (B3 reads)") + rulings_s100 (S100-N/P basis) | Findings absorbed into rulings S100-N, S100-P and the S100 session_log entry. Referrer: claude/parity_eval/S100_status_vs_final_report.md "Evidence:" line (pointer to the PK path). | delete batch 2 (pointer in S100_status_vs_final_report then resolves to the git path) |
| claude/pk_extract_s100.py | PK extract generator, S100 (its docstring: "supersedes pk_extract_s99.py"); used for the 10-30 re-upload | KEEP-core | live tool | keep |
| claude/pk_extract_s99.py | PK extract generator, S99 version (tracker-id-filtered tech_debt extract) | SUPERSEDED-by claude/pk_extract_s100.py | s100 docstring states the supersession; the S100-A split made the tech_debt filter obsolete. Referrers: S99_close_inputs §7, S100_session_prompt Part A (both batch-1 candidates). Content: a generator, superseded; nothing to preserve. | delete batch 2 |
| claude/S98-B_cycle_wait_design_2026-10-23.md | S98-B design note DRAFT (runner waits for its own cycle's chain run; D1–D3 for ruling) | SUPERSEDED-by rulings_s98 (S98-E, S98-E.1 amend D3/D2) + git `docs/research/s98/` (S99_close_inputs §5 commits it with amendment notes) + deployed `2edd25f` | Design decided and shipped; the note's §5 step 1 superseded by S99-A, §6 live PASS taken in S101. Referrers: S98_close_inputs, S99_close_inputs (batch 1), rulings_s98 (cites it as the ruled design — pointer survives as the git path). | delete batch 2 |
| claude/s98_reconciliation_table.md | S98 reconciliation table DRAFT: O1–O4 overlap tests, rows R1–R41 (+R16 instance), dropped list, proposed order | SUPERSEDED-by tracker §2.2 (`agentic_layer_roadmap_S90.md` in PK — S100-B: "Tracker §2.2 is their home") + git `docs/research/s98/` (S99_close_inputs §5) | Adopted as written (S98-A); every R-row homed in §2.2 at `7d8f7d1`/`3ad5c81`. Referrers: rulings_s98 (S98-A basis, pointer), S98_close_inputs, S100_status_vs_final_report (R-ids only). **Caveat:** the R-row *statements* (R5, R38 …) are cited by id in S104 prompt item 6; confirm the tracker §2.2 rows carry the statement text before deleting (I did not open the 300 KB tracker). | UNKNOWN → operator: delete only if tracker §2.2 carries the R-row text |
| claude/D4_classification_design_note_2026-10-12.md | D-4 classified-flow design note; status RULED S96-I = DECLINED-ON-EVIDENCE | SUPERSEDED-by rulings_s96 (S96-I) + git `docs/research/s96_priority/p7/D4_classification_design_note_2026-10-12.md` (named in S96-I basis) | Nothing built; decision recorded in rulings_s96 and CLAUDE.md settled line (D-4 deviation). Referrers: rulings_s96 (git path). | delete batch 2 |
| claude/live_read_pack_2026-10-12.md | P7 live market-hours read pack (4 roq queries + PASS rule) | STALE (P7 DONE on the 10-12 read, session_log S97 "P7 DONE"); the pack's queries are one-off | Git: "pack committed" (session_log S96 entry: "P7 DONE on the first market-hours read (pack committed)"). Referrers: none found. | delete batch 2 |
| claude/P3b_invariant_sidecar_design_note_2026-10-12.md | P3b sidecar design note; RULED S96-H; fixture result §6 | SUPERSEDED-by rulings_s96 (S96-H) + git `docs/research/s96_priority/p3b/P3b_invariant_sidecar_design_note_2026-10-12.md` (named in S96-H basis) + applied DDL `sql/2026-10-12_s96_p3b_invariant_checks.sql`; P3 DONE (session_log S97) | Referrers: rulings_s96 (git path). | delete batch 2 |
| claude/guard_survey_result_2026-10-11.md | Untraded-leg guard survey result (TD-S95-NEW-1 (c)); ruled S96-D | SUPERSEDED-by rulings_s96 (S96-D) + git `docs/research/s96_priority/guard/guard_survey_result_2026-10-11.md` (named in S96-D basis) | Referrers: rulings_s96 (git path). | delete batch 2 |
| claude/MP7_flow_badge_result_2026-10-11.md | M-P7 result: BUILD (qualified), pinned outputs | SUPERSEDED-by rulings_s96 (S96-B/E verdict applied) + git (`docs/research/s96_priority/p7/`; the prereg's commit `d909559` and amendment `9460d5d` are in git; result doc committed per S95-F practice) | Referrers: rulings_s96 (S96-E basis). Git path of the result not literally stated in the doc — content survives in rulings_s96 S96-E and the session_log S96 entry ("M-P7 scored BUILD"). | delete batch 2 (flag: git path inferred, not read) |
| claude/MP7_flow_badge_prereg_2026-10-11_DRAFT.md | M-P7 pre-registration (DRAFT label; committed as `MP7_flow_badge_prereg_2026-10-11.md`, blob `5813af5…`, commit `d909559` per the result doc) | DUPLICATE-of git `docs/research/s96_priority/p7/MP7_flow_badge_prereg_2026-10-11.md` (rulings_s96 "Next" names the path) | The committed file is the registered artefact (hash recorded); the PK DRAFT is the pre-commit copy. Referrers: MP7 result (batch 2). | delete batch 2 |
| claude/P7_flow_vs_book_design_note_2026-10-11_DRAFT.md | P7 design note; status RULED S96-A D1–D7 | SUPERSEDED-by rulings_s96 (S96-A) + git `docs/research/s96_priority/p7/P7_flow_vs_book_design_note_2026-10-11.md` (S96-A basis names it) | Referrers: D4 note, MP7 prereg (both batch 2), rulings_s96 (git path). | delete batch 2 |
| claude/P1c_regime_range_result_2026-10-10.md | P1c result: INCONCLUSIVE (10-10) | SUPERSEDED-by git (`c17e30d`, session_log S94 entry: "P1c DONE = INCONCLUSIVE (`c17e30d`; `abde07ca…`)") + rulings_s94 / tracker §2.1 | Referrers: none found beyond session_log (git hash). | delete batch 2 |
| claude/P4_charm_sign_prereg_2026-10-10.md | P4 pre-registration, ACCRUING (scored ~13 weeks out, ~mid-Jan 2027) | KEEP-core (live pre-registration; committed `cde0e0b` per session_log S94, but it is the active study's definition and is cited by s98 table / P8 gate) | Referrers: s98_reconciliation_table, rulings_s94/95 (git hash). Keep in PK until P4 is scored. | keep |
| claude/P2_dealer_side_result_2026-10-10.md | P2 result: REGIME-DEPENDENT (10-10) | SUPERSEDED-by git (`2dbf8a4`, session_log S94) + rulings_s94 (S94-F caveat) + Assumption Register dealer-sign row | Referrers: none found beyond session_log. | delete batch 2 |
| claude/paper_trades_SENSEX_15Oct_expiry.md | Operator's paper-trade log, SENSEX 15-Oct expiry (Day 1 only) | UNKNOWN | Operator's own trading record; no git path stated; not a MERIDIAN artefact; not referenced by any doc found. Related to the S/R premium-selling experiment memory. | ask operator (keep or "evidence only") |
| claude/paper_trades_SENSEX_08Oct_expiry.md | Operator's paper-trade log, SENSEX 08-Oct expiry (week 1, rules 1–7, replay) | UNKNOWN | As above; referenced by the 15-Oct log ("week-1 working rules"). | ask operator |
| claude/MERDIAN_Documentation_Protocol_v5_DRAFT.md | Doc Protocol v5 DRAFT (S90), Rule 3 + Rule 7 replacements | KEEP-core | ADOPTED by S95-E ("v5 replaces v4 Rules 3 and 7 as drafted (`MERDIAN_Documentation_Protocol_v5_DRAFT.md`)"); no non-draft copy exists in PK (project_search "Documentation_Protocol_v5" → this file only); CLAUDE.md v1.74 footer says "Doc Protocol v5". It is the in-force text despite the DRAFT name. Note: its header still says "DRAFT — v4 remains in force" — stale header, worth a one-line edit at a doc-close, not a delete. | keep |
| claude/DH-905_scrip_map_remap_S90.md | DH-905 stale scrip-map IDs finding + remap table (S90) | SUPERSEDED-by `sql/2026-10-06_s90_dh905_scrip_map_remap.sql` (named in the doc) + TD-S90-NEW-1 + roadmap R1.10 | Still relevant context for S103-H (exchange renames) — but S103 rulings cite TD-S90-NEW-1, not this doc. Referrers: none found. | delete batch 2 (content in sql/ + TD) |
| claude/marketview_live_check_S90.md | S90 first live Marketview check MV-1…MV-12 with fix log | STALE (S90 state; every MV item fixed or filed as TD; board since rebuilt through S100–S103) | Git: S90 working docs were committed under `docs/research/s90_agentic/` (rulings_s90 git path pattern); not literally stated in this doc. Referrers: paper_trades_08Oct ("from S90 live check"), rulings_s90 (S90-G basis "MV-9"). | delete batch 2 (flag: git path inferred) |
| claude/ref_2026-10-01_SENSEX_0DTE.md | Reference day 2026-10-01 SENSEX 0DTE: phases, findings, 76-cycle readings | KEEP-core | Explicitly a reference ("Consolidated so the day can be returned to"); the R2.1 golden day #1 expected-output reference; cited by D4 note, parity_dovetail, S88 docs. No git path stated. | keep |

## Family C4 — claude/ S84–S90 design, inventory and reference docs

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| claude/R0.1_spine_inventory_S90.md | S90 spine inventory DRAFT: core products table, ledger, parameters, health outputs, ENH-133 apply limits, wall-clock audit, gap list, findings R01-F1…F12 (all CONFIRMED / FIXED) | STALE (S90 state at `0f2901e`; every finding fixed or filed — R01-F1 `6e13a7f`, F3 ADR-031 D7.3, F9 S90-G, F10 S90-H, F11 `2de6282`, F12 DH-905; gap list → ADR-031 / roadmap Stage 0) | Content survives in ADR-031 (S90-C basis "S90 evidence R01-F1…F9"), rulings_s90, roadmap, TDs. Git path not stated in the doc (S90 working docs sit under `docs/research/s90_agentic/` per the rulings_s90 git path) — **inferred, not read**. Referrers: rulings_s90 (R01-F ids). Still a useful reference table of products/RLS — operator's call. | UNKNOWN → propose delete only after confirming the git copy exists (`git ls-files docs/research/s90_agentic/`) |
| claude/R2.1_golden_day_1_design_S90.md | R2.1 golden-day fixture design + freeze evidence (6 fixtures, 20 MB in git `e528a8d`) | SUPERSEDED-by the fixtures themselves (`tests/golden/*`, committed `e528a8d`) + roadmap R2.1 row | Git path of the design note not stated (inferred `docs/research/s90_agentic/`). Referrers: ref_2026-10-01 §8 (roadmap table, by item not file), none by filename. | delete batch 3 (flag: git copy inferred) |
| claude/parity_dovetail_and_post_parity_plan_S89.md | S89 PROPOSAL: dovetail the target read into parity; D-1…D-6 (all RULED S89, dispositions annotated); post-parity Q1–Q3 tracks; replay tests R1–R8 | STALE (parity CLOSED 2026-10-09; D-1…D-6 ruled; canonical `docs/research/s89_rulings/rulings_s89.md` in git; post-parity order replaced by S92-I P1–P8 and tracker §2.2) | Referrers: ref_2026-10-01 §9 (KEEP doc — pointer "post-parity replay"), D4 note, P7 draft (batch 2), ENH-133 proposal. Git path not stated. **Note: `rulings_s89.md` is NOT in PK** (only in git) — this doc's foot carries the S89 dispositions table; if deleted, the S89 rulings are git-only. | UNKNOWN → operator (rulings content of S89 lives only here in PK) |
| claude/ENH-133_schema_proposal_S89.md | ENH-133 schema PROPOSAL (grain, columns, session gate, retention, rulings owed 1–5) | SUPERSEDED-by ADR-030 + the spec in git (`ENH-133_schema_spec_S89.md`, which CLAUDE.md's ADR-030 settled line names as the schema's home) + S90-A/B rulings | Referrers: none by filename (parity_dovetail by topic). | delete batch 3 |
| claude/pressure_leg_decline_S89.md | L12 pressure leg DECLINED-ON-EVIDENCE summary; **its own header: "This project copy is the summary; canonical, number-exact record in the repo `docs/research/s89_rulings/pressure_leg_decline_S89.md` (0179abf)"** | DUPLICATE-of (summary of) git `docs/research/s89_rulings/pressure_leg_decline_S89.md` | Self-declared. Referrers: parity_dovetail dispositions (git path), CLAUDE.md settled line (D-5a by id). | delete batch 3 |
| claude/post_parity_candidates_S89.md | Candidates A (1-min repricing pass) and B (MTF leverage context), PROPOSED, ENH ids to mint at S89 close | SUPERSEDED-by Enhancement Register (ids minted at the S89 close per its own "Next action") + git `docs/research/post_parity_candidates.md` (named in parity_dovetail D-4 disposition) | Referrers: parity_dovetail, target_read_implications. Enhancement Register LATEST (Parts 1–3) in PK should carry the two ENH blocks — not verified by me. | delete batch 3 (verify the two ENH ids exist in the register first) |
| claude/target_read_implications_S88.md | S88 note: how the target's author reads; corrections; parity consequences (→ D-1…D-6); #202 straddle-gate test DRAFT (never stamped); S/R experiment notes | UNKNOWN | Proposals ruled at S89; the #202 test design was never pre-registered; ties to the operator's S/R premium-selling experiment and his study of the author (which he values). Referrers: ref_2026-10-01 (KEEP), parity_dovetail, post_parity_candidates. Git path not stated. | ask operator |
| claude/target_read_Mar-Oct2026.md | Verbatim text extraction of the operator's PDF `Ashwin_Badrinath_analysis_Mar-Oct2026.pdf` (product name replaced) | KEEP-core (reference; text twin of the project file) | Cited by rulings_s100 (S100-Q basis), parity_dovetail, post_parity_candidates, P7 design. The PDF itself is the project file (listed, untouched). | keep |
| claude/parity_board_design.md | S84/S85 whole-board design A–G (approved 2026-10-01 with R1–R4); §H never written | STALE (parity CLOSED; the board was built through S89–S103 Lovable rounds; design decisions superseded by rulings S92+ and the live board) | Referrers: parity_dovetail (batch 3/UNKNOWN), parity_render_contract.md (root), MERDIAN_Hedgewall_Parity_Spec? (not checked). Git path not stated → **PK-only risk**: S94-E precedent archived PK-only docs to `docs/registers/archive/pk_only_2026-10-10/` before deleting. | delete batch 3 only after archiving to git (S94-E route) |
| claude/parity_target_render_study.md | S84 render study of the parity target (A–F), captured 2026-09-25 | STALE (parity CLOSED; design consumed) | Referrers: rulings_s100 S100-Q basis ("render study L6"), parity_board_design, parity_render_contract. "Working notes not uploaded"; git path not stated → PK-only risk. | delete batch 3 only after archiving to git (S94-E route); pointer in rulings_s100 stays as history |
| claude/lovable_prompt_s97_help_route.md | S97 `/help`→`/manual` Lovable round, full record, DONE 2026-10-13 | SUPERSEDED-by git `docs/lovable_prompts/s97/lovable_prompt_s97_help_route.md` (committed `c3fc35c`, S98_close_inputs §5) | Referrers: s98_reconciliation_table (sources), lovable_prompt_s97_dealer_wording (sibling). | delete batch 3 |
| claude/lovable_prompt_s97_dealer_wording.md | S97-A dealer-wording Lovable round, promoted `04fcd05` | SUPERSEDED-by git `docs/lovable_prompts/s97/lovable_prompt_s97_dealer_wording.md` (named in rulings_s97 S97-A basis) | Referrers: rulings_s97 (git path). | delete batch 3 |

## Family E — claude/retail/** (PROTECTED: KEEP-retail by default; flags listed separately for the operator's ruling)

Read in full this pass: glossary_v0.1.json, glossary_v0.2.json, MR_S4_session_prompt.md, rulings_mr_s4.md, MR_S3_close_inputs.md, cc_prompt_u1_1.md, cc_prompt_u1_3.md, retail_scope_v0.4.md, day_plan_2026-10-26.md, and (outside retail/) claude/retail_scope_draft_2026-10-25.md. The rest are KEEP-retail by rule and were not opened this pass (no delete can arise from them).

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| claude/retail/MR_S4_session_prompt.md | MR-S4 prompt (state at open, order of work, rules, PK file hashes) | KEEP-retail | live session (MR-S4 close not run) | keep |
| claude/retail/rulings_mr_s4.md | MR-S4 run sheet (items 1–10), rulings, findings, assumption register | KEEP-retail | live | keep |
| claude/retail/MR_S3_close_inputs.md | MR-S3 handoff: state, done, open work, rulings owed, lessons | KEEP-retail | cited by MR_S4 prompt (hash-verified at open) | keep |
| claude/retail/glossary_v0.2.json | Glossary v0.2 (25 entries; `rules` gains the no-link clause; `varsity_url` field reserved) — sha `5642d8ea…` | KEEP-retail | pinned by cc_prompt_u1_1 §0.5 and copied into `packages/glossary` (rulings_mr_s4 item 7/8) | keep |
| claude/retail/glossary_v0.1.json | Glossary v0.1 — **entries byte-identical to v0.2** (compared: all 25 `id/term/what/why/deeper/varsity` fields equal; only `version` and the `rules` string differ) | FLAG-for-ruling: earlier VERSION of glossary_v0.2.json | rulings_mr_s4 "Varsity links" ruling states the identity ("entries byte-identical to v0.1"). Referrers: MR_S4_session_prompt (hash list, read-first list), rulings_mr_s4 (hash at open), lovable_prompt_5a (attached to Lovable as `src/lib/glossary_v0.1.json`). The Lovable prototype still carries v0.1 (prototype only). | operator ruling (keep as the prototype's pinned copy, or delete as superseded by v0.2) |
| claude/retail/cc_prompt_u1_1.md | CC prompt U1.1 (shell, tokens, strings, 404/500, switcher, glossary package); executed → PR 36 merged `d95caf1` | KEEP-retail | distinct unit from u1_3 (not a revision; there is no u1_2 — U1.2 deferred). Executed; MR-S4 ledger cites it. Candidate for archiving at the MR-S4 close, not now. | keep |
| claude/retail/cc_prompt_u1_3.md | CC prompt U1.3 (auth screens); PR 37 in progress | KEEP-retail | live | keep |
| claude/retail/retail_scope_v0.4.md | Retail scope v0.4, RULED (MR-S1), history v0.2→v0.4 | KEEP-retail | cited by MR_S4 prompt | keep |
| claude/retail_scope_draft_2026-10-25.md (outside retail/) | Retail scope **v0.3 DRAFT** (S100 discussion, for ruling) | FLAG-for-ruling: earlier VERSION of claude/retail/retail_scope_v0.4.md | Compared: v0.4 = v0.3 + §0 billing entity, §1.0 spike result, §1.0a re-measured fees + broker-terms finding, §1.1a `board.replay`, §1.2.1 wording lint, §3 P0 step 0, §4 rulings R-1…R-11, §7 status; every v0.3 section survives in v0.4 (v0.4 header: "History: v0.2 … v0.3 …"). Referrers: none found by name (tracker §2.3 "points here" per v0.3 §8 — the v0.4 header says the file moved to `retail-platform/docs/`). | operator ruling (delete as superseded by v0.4) |
| claude/retail/day_plan_2026-10-26.md | One-day run sheet for Mon 2026-10-26 (engine + retail lanes) + the H2 plan prompt | FLAG-for-ruling: STALE (the day has passed; engine items recorded in S101_close_inputs; H2 built per harness_plan / MR-S2) | Referrers: none found. Retail-protected, so flagged, not proposed. | operator ruling |
| claude/retail/rulings_mr_s3.md | MR-S3 ledger | KEEP-retail | not opened (protected) | keep |
| claude/retail/rulings_mr_s2.md | MR-S2 ledger | KEEP-retail | not opened | keep |
| claude/retail/rulings_mr_s1.md | MR-S1 rulings R-1…R-11 | KEEP-retail | not opened; cited by retail_scope_v0.4 §4 | keep |
| claude/retail/MR_S3_session_prompt.md | MR-S3 prompt | KEEP-retail | not opened; closed session — same class as engine prompts; archive only at an MR close | keep |
| claude/retail/MR_S2_session_prompt.md | MR-S2 prompt | KEEP-retail | not opened; same | keep |
| claude/retail/MR_S2_close_inputs.md | MR-S2 handoff | KEEP-retail | not opened | keep |
| claude/retail/MR_S1_close_inputs.md | MR-S1 handoff | KEEP-retail | not opened | keep |
| claude/retail/orderflow_recorder_decisions.md | Order-flow recorder decisions (parked; hash `5e751da7…`) | KEEP-retail | pinned by MR_S4 prompt | keep |
| claude/retail/engine_ref_ddl_O4_2026-10-26.sql | Engine reference DDL (O4) | KEEP-retail | protected (engine_ref_ddl named in the brief) | keep |
| claude/retail/tech_debt_retail.md | TD-MR-1…57 register | KEEP-retail | register | keep |
| claude/retail/O1_view_provenance_2026-10-26.md | O1 view provenance read (10-26) | KEEP-retail | not opened | keep |
| claude/retail/harness_plan.md | Agent-run harness plan (H1–H2) | KEEP-retail | cited by MR_S4 prompt | keep |
| claude/retail/p1_cost_mr_s1.md | P1 cost measurement (MR-S1) | KEEP-retail | not opened | keep |
| claude/retail/p0_starter_spike_mr_s1.md | P0 starter selection spike (Makerkit lite pick) | KEEP-retail | cited by retail_scope_v0.4 §1.0 | keep |
| claude/retail/runbooks/RB1_razorpay_kyc.md … RB6_sandbox_repos_supabase.md | Six operator runbooks (Razorpay KYC, AWS account, Kite Connect, Dhan API, domain, sandbox/repos/Supabase) | KEEP-retail | runbooks | keep |
| claude/retail/wording-lint/lint.ts, lint.test.ts | Wording-lint prototype (moves into retail-meridian at P1 per scope §1.2.1) | KEEP-retail | cited by retail_scope_v0.4 §1.2.1 | keep |
| claude/retail/lovable_prompt_5a.md | Lovable prompt 5a (Γ per-1 % fixes; built and published 12:02 IST 10-30) | KEEP-retail | cited by rulings_mr_s4 item 4 | keep |
| claude/retail/cc_port_brief_v0.1.md | CC port brief v0.1 DRAFT (P-1…P-6; four rulings owed) | KEEP-retail | cited by rulings_mr_s4 item 6 | keep |

## Family D — claude/parity_eval/ (the 13→19 Oct parity-target trial evaluation)

Read in full: parity_target_final_report_2026-10-19.md, S100_status_vs_final_report.md, 00_inventory.md. The final report (§0 and its header) names every other file as evidence and cites them by code (H1–H9, D2-n, D3-n, D4-n, #1–#29, F1–F7); s98_reconciliation_table absorbed the MERIDIAN-side findings into R1–R41 (S98-A); S100_status tracks the §7/§8 items. **No git path is stated for any file in this folder** (they were written in parallel chats) → PK-only; the S94-E route (archive to `docs/registers/archive/pk_only_<date>/` or `docs/research/parity_eval/`, `sha256sum -c`, then delete) is the safe disposal. The operator values the author-read material (04_author_read; memory: "Navin considers that read more important than what the target's screens show").

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| parity_eval/parity_target_final_report_2026-10-19.md | Final report S97 trial: scope, answer, objectives, layer table, scored forward numbers, adopt/test/don't, 13 MERIDIAN defects, owed | KEEP-core (the consolidated record; cited by s98 table, rulings_s100 S100-S "final report A2/A4/A5", S100_status) | PK-only | keep (and archive to git at a doc-close) |
| parity_eval/S100_status_vs_final_report.md | Status of the final report's A/T/N and defects 1–13 as at S100 | KEEP-core (cites rulings_s100, B3_reads, S100_close_inputs; after batch 1/2 its two PK pointers resolve to git paths — note at the S103 close) | PK-only | keep |
| parity_eval/00_inventory.md | Live terminal inventory (shell, 26-pane catalogue, workspaces, settings, What's-new, data calls) | KEEP-core (reference; final report §3 "Shell"/"Data source" rows point to it) | PK-only | keep |
| parity_eval/04_author_read.md | The author's reads 13–16 Oct (final report §5.4 source) | UNKNOWN | not opened; operator-valued material | ask operator (recommend keep) |
| parity_eval/03_findings.md | Pre-open findings F1–F7 (GEX unit, flip, HHI, pin, direction, walls) | UNKNOWN | not opened; F1 is cited by ADR-032 Context ("Measured S97 (F1, `claude/parity_eval/03_findings.md`)") → a live pointer from the ADR | keep (cited by ADR-032) |
| parity_eval/08_defect_verification_15Oct.md | Defect table #1–#29 with labels (final report §3 tally) | UNKNOWN | not opened; cited by final report and s98 table | ask operator (recommend archive to git, keep until then) |
| parity_eval/01_cockpit_schema.md | Schema of the target's `cockpit` payload (one read, 13 Oct) | UNKNOWN | not opened; final report §0 "one payload read"; R31 dropped the target-only comparisons | ask operator (archive candidate) |
| parity_eval/02_capture_log_2026-10-15.md | Capture log (checkpoints) 15 Oct | UNKNOWN | not opened; raw evidence behind D3-n | ask operator (archive candidate) |
| parity_eval/05_delta_positioning_NIFTY_1246.md | Delta positioning read NIFTY 12:46 | UNKNOWN | not opened; evidence for F5/#1 | ask operator (archive candidate) |
| parity_eval/06_nifty_pin_scorecard_13Oct.md | NIFTY 13 Oct pin scorecard (final report §5.1 source) | UNKNOWN | not opened | ask operator (archive candidate) |
| parity_eval/07_owed_sql_14Oct.md | Owed SQL Q1–Q5b (R31: only R7/R8/R10/R18 parts run — all done per S100_status §9; the rest dropped) | STALE (every surviving question answered in B3_reads / S100_status §9; the rest dropped by R31) | not opened in full; disposition stated by S100_status §9 | delete batch 4 after archive (or operator "evidence only") |
| parity_eval/parity_target_day1_2026-10-13.md … day4_2026-10-16.md | Day reports H1–H9, D2-n, D3-n, D4-n (final report's evidence base) | UNKNOWN | not opened; cited by code throughout the final report and s98 table | ask operator (recommend archive to git as a set, then prune) |
| parity_eval/parity_eval_starter_day7_2026-10-19.md | Day-7 (19 Oct) starter — the day that was never run (final report §0) | STALE (Day 5/7 not run; trial expired) | not opened in full | delete batch 4 after archive |

## Family F — S102/S103 Lovable rounds, guards, SQL, ADR-032 working docs

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| claude/ADR-032-DRAFT-gex-stored-unit.md | ADR-032 draft (D1 RULED+LIVE record; D2–D5 PROPOSED) | KEEP-core (ADR; never proposed). **Note:** filed to `docs/decisions/ADR-032-gex-stored-unit.md` at the S102 close; the PK copy is the pre-filing draft and is now behind rulings_s103 (D2–D5 RULED in form, S103-P…T). Cited by MR_S4_session_prompt (retail read-first list). At the S103 doc-close: replace with the filed, amended ADR. | keep |
| claude/gex_unit_inventory_S102.md | Γ unit inventory v2 (bound by ADR-032; git `docs/research/s102/`) | KEEP-core (cited by CURRENT.md, ADR-032, MR_S4 prompt) | not re-opened | keep |
| claude/2026-10-30_s102_gex_per_1pct_views.sql | D1 DDL, seven `_1pct` wrappers + T1–T5 (git `sql/…`) | KEEP-core (cited by MR_S4 prompt read-first list; CURRENT.md) | not re-opened | keep (retail-cited) |
| claude/lovable_prompt_s102_gamma_per_1pct.md | Round 1 board prompt (7 files, 41 replacements, table W) | KEEP-retail-by-citation (MR_S4 prompt read-first list) — git `docs/lovable_prompts/s102/` | not re-opened | keep until the MR-S4 close drops the citation |
| claude/lovable_prompt_s102b_legacy_per_1pct.md | Round 2 legacy-pages prompt (10 replacements) + operator notes; promoted in `30998f2` | SUPERSEDED-by git `docs/lovable_prompts/s102/lovable_prompt_s102b_legacy_per_1pct.md` (S103 prompt Part A item 6, executed at `762e4d7`) + ADR-032 D1 record | Referrers: S102_close_inputs (batch 1), ADR-032-DRAFT (Board row, names both prompts — pointer survives as the git path), S103_session_prompt. | delete batch 4 |
| claude/mv_lovable_guard_s102.sh | Round-1 guard (seven `_1pct` views allowlist) | SUPERSEDED-by git `docs/lovable_prompts/s102/` (same commit) | one-time round guard; round promoted. Referrers: S102_close_inputs, ADR-032 record (by name). | delete batch 4 |
| claude/mv_lovable_guard_s102b.sh | Round-2 guard (sha `00767d95…`) | SUPERSEDED-by git (same) | Referrers: s102b prompt (batch 4), ADR-032 record. Compared with s102.sh: same v2 skeleton, different allowlist/views/fingerprint — successive round copies, not versions of one live script. | delete batch 4 |
| claude/s102_manual_v05.sh | Manual v0.5 build script (18 anchored edits, `edits_man.py`) | SUPERSEDED-by git `docs/lovable_prompts/s102/s102_manual_v05.sh` + the v0.5 source landed in `docs/marketview_manual/` at the S102 close (S103 prompt Part A item 7) | Referrers: S102_close_inputs, ADR-032 record, S103_session_prompt. | delete batch 4 |
| claude/lovable_prompt_s103_health_token_skew_expiry.md | S103 round 1 prompt (S103-A, S103-C) — promoted `05f556c` | KEEP-core until the S103 doc-close (named in rulings_s103 round-1 record) | S103 close not run; git copy lands with it | DEFERRED (batch after the S103 close, with the S103 guards) |
| claude/mv_lovable_guard_s103.sh | S103 round 1 guard | KEEP-core until the S103 doc-close | same | DEFERRED |
| claude/mv_promote_s103.sh | S103 promote script (refusing block; pattern reused for r16/r20) | KEEP-core until the S103 doc-close | same | DEFERRED |
| claude/lovable_prompt_s103_r16_freeze_button.md, claude/mv_lovable_guard_s103r16.sh | Round 2 (S103-I) prompt + guard — live `2f3c2f0` | KEEP-core until the S103 doc-close (named in the addendum) | same | DEFERRED |
| claude/lovable_prompt_s103_r20_prev_close.md, claude/mv_lovable_guard_s103r20.sh, claude/2026-10-30_s103_v_close_print.sql | Round 3 (S103-J) prompt + guard + `v_close_print` DDL — live `6f14a92` | KEEP-core until the S103 doc-close (named in the addendum; the SQL is the applied view's record → `sql/` at the close) | same | DEFERRED (the .sql stays until its `sql/` commit is confirmed) |
| claude/2026-10-31_s103_adr032_s1_unit_comments.sql | ADR-032 S1 COMMENT SQL (committed `8b58e54`; project copy named by the S104 prompt step B) | KEEP-core | named by the S104 prompt | keep |
| claude/adr032_f0_k1_k3_records_2026-10-31.md, claude/adr032_fallback_plan_S103.md, claude/adr032_s5_s6_impact_study_S103.md, claude/cc_prompt_adr032_sweep_engine_box.md, claude/cc_prompt_adr032_sweep_retail_box.md | ADR-032 F0 record, fallback plan, §5/§6 study, two CC sweep prompts | KEEP-core (all named by the S104 prompt) | live | keep |

## Family A — root-level docs (registers, protocols, runbooks, rules files, CASEs, research results)

Never-propose classes (registers, CLAUDE.md, runbooks, protocols) are listed for completeness and marked **not opened** where I did not read them this session; their category follows from the operator's rule, not from a content read.

| path | what it is | category | evidence | action |
|---|---|---|---|---|
| CLAUDE.md | v1.74 live operating file (read this session) | KEEP-core | never-propose class | keep |
| CLAUDE_history.md | LATEST extract, S103 upload 2026-10-30 | KEEP-core | register/LATEST class | keep |
| tech_debt_LATEST.md | LATEST extract 2026-10-30 | KEEP-core | never-propose | keep |
| MERDIAN_Enhancement_Register_LATEST.md | LATEST extract 2026-10-30 | KEEP-core | never-propose | keep |
| merdian_reference_LATEST.json | LATEST extract 2026-10-30 | KEEP-core | never-propose | keep |
| agentic_layer_roadmap_S90.md | roadmap, re-uploaded 2026-10-30 with the LATEST set | KEEP-core | uploaded by the S103 pk_extract batch (same timestamp as the LATEST files) → live | keep |
| MERDIAN_Decision_Index.md | §D decision index (not opened) | KEEP-core | register class | keep |
| MERDIAN_Assumption_Register.md | assumption register (not opened) | KEEP-core | register class | keep |
| MERDIAN_System_Map.md | system map (not opened) | KEEP-core | register class; ADR-026 names it in the chunking design | keep |
| MERDIAN_Data_Inventory.md | data inventory (not opened) | KEEP-core | register class | keep |
| MERDIAN_Deployment_Topology.md | topology (not opened) | KEEP-core | register class | keep |
| MERDIAN_Hedgewall_Parity_Spec.md | parity spec (not opened) | KEEP-core | cited by parity_render_contract as `docs/registers/MERDIAN_<REDACTED>_Parity_Spec.md`; register class | keep |
| MERDIAN_Governance_Framework.md | governance (not opened) | KEEP-core | protocol class | keep |
| MERDIAN_ClaudeCode_Guardrails.md | CC guardrails (not opened) | KEEP-core | protocol class | keep |
| MERDIAN_Testing_Protocol_v1.md | testing protocol (not opened) | KEEP-core | protocol class | keep |
| MERDIAN_Documentation_Protocol_v4.md | Doc Protocol v4 | KEEP-core | v5 DRAFT replaces only Rules 3 and 7 and says so; v4 remains the base text | keep |
| claude/MERDIAN_Documentation_Protocol_v5_DRAFT.md | v5 (in force despite the DRAFT name; adopted S95-E) | KEEP-core | — | keep |
| MERDIAN_Session_Management_v1.md | 2026-03-31 session-hygiene protocol (resume block, 20-exchange checkpoint, one-concern rule); companion to Documentation Protocol **v1** | SUPERSEDED-by CLAUDE.md session rules + Doc Protocol v4/v5 (session prompt → close inputs → rulings cycle replaced the resume-block/scratchpad cadence) | Referrers: none found in project_search (n=6). Git path **not stated** (footer says only "Commit to Git"); durable copy unverified → **UNKNOWN (ask)**: confirm it sits under `docs/` before any delete | ask |
| MERDIAN_Live_Trading_Log_v1.md | 2026-05-04 live trading log — one entry (#001 OB rejection) + empty template; git home `docs/trading_logs/` stated in header | STALE (no entry since May; no live doc cites it; the discretionary-trading thread moved to paper_trades_* and target_read docs) | Git path stated in the doc header → durable copy named. Referrers: none in project_search (merdian_reference may list the file — not checked) | delete batch 4 |
| P1_level_test_result_2026-10-09.md | P1 level test RESULT (S93): A-NIFTY NO, B-NIFTY NO; scorer output verbatim | SUPERSEDED-by git `docs/research/s92_priority/` (prereg, input json, scorer and README all cited there; result file inferred to sit beside them — **path inferred, not stated**) | Referrers: CLAUDE.md footer and rulings_s94 cite the verdict; S93 doc-close ran (`3ad5c81` era). Verdict text survives in rulings_s93/CLAUDE.md | delete batch 2 (confirm git path first) |
| WS3.1_baseline.md | S87 routing-baseline measurement record (phase_c.py generated; 7-defect table; §7 derived requirements for ADR-029) | UNKNOWN (ask) | Footer: "no transcript, snapshot or report file is committed" → **PK-only**. ADR-029 is built on it (§7 "requirements this baseline implies for ADR-029") — pointer not verified by opening ADR-029. If ADR-029 is self-contained: archive to git (S94-E route) then batch 3; else KEEP-core | ask |
| inventory.md | S85 RAG feasibility measurement (corpus, chunking, embed-model memory) | KEEP-core | **Referrers: ADR-026 (§2, §4 "inventory.md §2/§4") and ADR-027-DRAFT (§4, §5 "measured in inventory.md §1/§5a/§5b")** — two live ADRs cite it by name and section | keep |
| parity_render_contract.md | S84 measure-only read contract for 18 DB objects + front-end at `a408fb4`; P1–P7 proposed TDs "not filed" | STALE (parity CLOSED; front end and views have moved through S85–S103; P1–P7 were filed at S84 close as TD-S84-NEW-*) | Git path **not stated** (scratch at `scratch/s84_contract/`, "nothing in this document is filed") → PK-only risk. Referrers: parity_board_design, parity_target_render_study (both batch-3 archive-first) | delete batch 3 only after archiving to git (S94-E route), together with its two referrers |
| README.md | docs/research README (not re-opened; cites capture_s75.md etc.) | KEEP-core | index doc for `docs/research/` | keep |
| SKILL.md | doc-close skill (read this session) | KEEP-core | live skill | keep |
| registers.md | `.claude/rules` file (relocated verbatim from CLAUDE.md at S86, ADR-028) | KEEP-core | CLAUDE.md "Where the rest of this file went" points to it | keep |
| python-writers.md | `.claude/rules` file (S86 relocation) | KEEP-core | same | keep |
| research.md | `.claude/rules` file (S86 relocation) | KEEP-core | same | keep |
| ops-shell.md | `.claude/rules` file (S86 relocation) | KEEP-core | same | keep |
| schedulers.md | `.claude/rules` file (S86 relocation) | KEEP-core | same | keep |
| data-access.md | `.claude/rules` file (S86 relocation) | KEEP-core | same | keep |
| sql-views.md | `.claude/rules` file (S86 relocation) | KEEP-core | same | keep |
| runbook_recover_disk_full_lockout.md | runbook (not opened) | KEEP-core | runbook class; paired with CASE-2026-09-22-disk-full | keep |
| runbook_aws_cli_file_operations.md | runbook (not opened) | KEEP-core | runbook class | keep |
| runbook_disaster_rebuild.md | runbook (not opened) | KEEP-core | runbook class | keep |
| runbook_data_backfill_internet_outage.md | runbook (not opened) | KEEP-core | runbook class | keep |
| runbook_update_kite_flow.md | runbook (not opened) | KEEP-core | runbook class | keep |
| CASE-2026-09-22-anon-privilege-exposure.md | CASE record (not opened) | KEEP-core | CASE class | keep |
| CASE-2026-09-22-disk-full-access-lockout.md | CASE record (not opened) | KEEP-core | CASE class | keep |
| rulings_s87.md / rulings_s91.md / rulings_s93.md | root-level rulings (no claude/ twin) | KEEP-core | rulings never proposed | keep |
| claude/marketview_user_manual_v04_DRAFT.md | Marketview user manual v0.4 DRAFT (2026-10-24; not opened) | KEEP-core | `/manual` route content source (S97 help route); no later version in PK | keep |
| claude/session_log.md, claude/CURRENT.md | governance (read) | KEEP-core | never-propose | keep |

## Family B — ADRs (all KEEP-core by rule; none opened this session unless noted)

ADR-001, -002, -006, -008, -015, -016, -017, -018, -019, -020, -021, -022, -023, -024, -025, -026 (read via search hit), -027-DRAFT (read via search hit), -028, -029, -030, claude/ADR-031, claude/ADR-032-DRAFT — **22 docs, all keep**. Note for the S103 close (not a prune item): the filed ADR-032 exists in git; the PK copy is still the DRAFT and should be replaced, not deleted.

## Project file (not a doc)

`Ashwin_Badrinath_analysis_Mar-Oct2026.pdf` — listed, untouched. Text twin `claude/target_read_Mar-Oct2026.md` is KEEP-core.

## Summary (195 docs + 1 file)

| category | count | notes |
|---|---|---|
| KEEP-core | ~97 | registers, ADRs (22), rulings (17), rules files, runbooks, CASEs, protocols, S104/S103 live docs, ADR-032 working set, accruing prereg (P4) |
| KEEP-retail (protected) | 27 | everything under claude/retail/** + retail_scope_draft; 3 flagged for ruling (not counted as candidates) |
| delete batch 1 — closed session prompts / close inputs | 9 | each superseded by its rulings_s<N> + a run doc-close commit; S99 §7 precedent |
| delete batch 2 — S94–S100 research/design docs | 15 | git path named by the doc or its rulings; 3 flagged "git path inferred" |
| delete batch 3 — S84–S90 docs | 9 | 3 are PK-only → archive to git first (S94-E route) |
| delete batch 4 — S102 Lovable set + stale parity_eval + Live Trading Log | 7 | 2 parity_eval items archive-first |
| DEFERRED until the S103 doc-close | 10 | S103_session_prompt + 9 S103 round files |
| UNKNOWN — operator decides | 18 | 8 claude/ + root docs, 10 parity_eval (recommend: archive the parity_eval set to git as one commit, then prune) |
| retail flags for ruling | 3 | glossary_v0.1.json, retail_scope_draft_2026-10-25, retail/day_plan_2026-10-26 |
| project file | 1 | Ashwin_Badrinath PDF — untouched |

Delete protocol: nothing deleted until the operator answers "delete batch N"; then `project_delete` one batch at a time and re-list with `project_info` to confirm.

## Execution record (2026-10-31)

| batch | deleted | PK count after | where the content lives |
|---|---|---|---|
| 1 (9) | 10:0x IST | 186 | S100–S102 session prompts archived first at `docs/research/s100|s101|s102/S10N_session_prompt.md`, commit `8f9d466`; the six close-inputs/prompts already tracked in git (ls-files verified) |
| 2 (15) | 10:0x IST | 178 (list confirmed) | `docs/research/s98/`, `s90_agentic/`, `s92_priority/`, `s96_priority/{p7,guard,p3b}/` |
| 3 (9) | 16:29–16:30 IST | 169 | three PK-only docs archived first at `docs/registers/archive/pk_only_2026-10-31/` (commit `2b69506`, `SHA256SUMS` verified on the box); `post_parity_candidates_S89` confirmed in git as `docs/research/post_parity_candidates.md` — **its Candidates A/B still have no ENH ids in the register (Part 1 ends ENH-145): S103 doc-close item**; the rest under `docs/research/s89_rulings/`, `s90_agentic/`, `docs/lovable_prompts/s97/` |
| 4 (7) | 16:31 IST | 162 | `parity_eval/07_owed_sql_14Oct.md` and `parity_eval_starter_day7_2026-10-19.md` in the same `pk_only_2026-10-31` archive (`2b69506`); S102 Lovable set under `docs/lovable_prompts/s102/` + guards in `bin/`; Live Trading Log under `docs/trading_logs/` |

Archive commit `2b69506` note: `parity_render_contract.md` was CRLF in PK and is archived LF-normalised (stated in the commit message); the other four are byte-identical.

### UNKNOWN rulings (operator, 16:35 IST: "as recommended"; retail flags explicitly NOT acted on)

| ruling | docs | action taken |
|---|---|---|
| delete | `claude/s98_reconciliation_table.md` | deleted 16:37 (tracker §2.2 + git `docs/research/s98/`) |
| keep | `claude/paper_trades_SENSEX_08Oct_expiry.md`, `claude/paper_trades_SENSEX_15Oct_expiry.md`, `claude/parity_dovetail_and_post_parity_plan_S89.md`, `claude/target_read_implications_S88.md`, `claude/parity_eval/04_author_read.md`, `claude/parity_eval/03_findings.md` | untouched |
| archive → delete | `MERDIAN_Session_Management_v1.md`, `WS3.1_baseline.md`, `claude/R0.1_spine_inventory_S90.md` (archive chosen over the unverified git copy), `claude/parity_eval/{01_cockpit_schema, 02_capture_log_2026-10-15, 05_delta_positioning_NIFTY_1246, 06_nifty_pin_scorecard_13Oct, 08_defect_verification_15Oct, parity_target_day1…day4}.md` (12 docs) | archived at `docs/registers/archive/pk_only_2026-10-31b/` with `SHA256SUMS`, commit **`232a3bc`** (12/12 OK on the box; all four trees at `232a3bc`); deleted from PK 18:13 IST |
| retail flags (3) | `claude/retail/glossary_v0.1.json`, `claude/retail_scope_draft_2026-10-25.md`, `claude/retail/day_plan_2026-10-26.md` | **not acted on** (operator instruction) |

PK after this step: **149 docs** (162 − 1 − 12). Still open: 10 DEFERRED until the S103 doc-close; the 3 retail flags (untouched); root-level `cc_prompt_adr032_sweep_retail_box.md` stray duplicate of `claude/cc_prompt_adr032_sweep_retail_box.md` (offer: delete root dup).

### S103 doc-close deletions (2026-11-01, after `9d26281` landed on all four trees)

The ten DEFERRED docs are deleted from PK after the S103 doc-close (`9d26281`) and the follow-up docs commit that archives the one doc git did not hold (`S103_session_prompt`). **Where each can be found:**

| PK doc (deleted) | Git home (engine repo `balannavin-cyber/meridian-engine`) |
|---|---|
| claude/S103_session_prompt.md | `docs/research/s103/S103_session_prompt.md` (follow-up docs commit; session prompts were never committed before — archived here per the batch-1 precedent) |
| claude/lovable_prompt_s103_health_token_skew_expiry.md | `docs/lovable_prompts/s103/` (`9d26281`) |
| claude/mv_lovable_guard_s103.sh | `docs/lovable_prompts/s103/` (`9d26281`; sha256 `b5434d6e…` verified equal to the hash recorded in rulings_s103) |
| claude/mv_promote_s103.sh | `docs/lovable_prompts/s103/` (`9d26281`) |
| claude/lovable_prompt_s103_r16_freeze_button.md | `docs/lovable_prompts/s103/` (`9d26281`) |
| claude/mv_lovable_guard_s103r16.sh | `docs/lovable_prompts/s103/` (`9d26281`; sha256 `a6b16eb0…` verified) |
| claude/lovable_prompt_s103_r20_prev_close.md | `docs/lovable_prompts/s103/` (`9d26281`) |
| claude/mv_lovable_guard_s103r20.sh | `docs/lovable_prompts/s103/` (`9d26281`; sha256 `1493a786…` verified) |
| claude/2026-10-30_s103_v_close_print.sql | `sql/2026-10-30_s103_v_close_print.sql` (`9d26281`) |
| claude/rulings_s103_addendum_rounds_2_3.md | merged into `docs/research/s92_parity/rulings_s103.md` (`9d26281`; PK `claude/rulings_s103.md` replaced by the merged file) |

Kept in PK (reference for the next session, git copies at `9d26281`): S103_close_inputs, S104_session_prompt, adr032_f0_k1_k3_records, adr032_fallback_plan, adr032_s5_s6_impact_study, the two CC sweep prompts, the sweep Phase-1/90-report/95-diff records, 2026-10-31_s103_adr032_s1_unit_comments.sql, and the filed `ADR-032-gex-stored-unit.md` (the DRAFT `claude/ADR-032-DRAFT-gex-stored-unit.md` is replaced by it).

Copy-fidelity note: the git copies of the S103/S104 working docs were transcribed from PK by a helper, not copied byte-for-byte; the three guard scripts and the key hashes in the F0 record, impact study, sweep records and rulings were verified mechanically. The audit file itself is byte-identical (`cmp`). Any doubt about a script is resolved against the operator's Downloads copy.
