<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/MR_PIN2_close_inputs.md -->
# MR-PIN2 close inputs (written Sun 2026-11-22 ~20:40 IST on the operator's "Time for EOS documentation"; series MR-PIN = Board pin accuracy; next session MR-PIN3)

MR-PIN2 ran Fri 2026-11-20 to Sun 2026-11-22. Read with: `ruling_pin_definition_2026-11-21.md`, `pin_behaviour_v5_result_2026-11-21.md`, `pin_live_replay_v2_result_2026-11-21.md`, `pin_vs_followup_result_2026-11-22.md`, `gamma_pipeline_audit_prereg_FROZEN_2026-11-22.md`, `gamma_pipeline_audit_result_2026-11-22.md`, `pin_fix_scope_DRAFT_2026-11-21.md` (now the engine proposal), `2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql`. Figures below were printed by Claude Code or pasted by the operator.

**Nothing is authorised for production, the Board, `gamma.py` or any signal gate.** The gross-pin view is a proposal for a *shadow* view; the one-gamma net is evidence for the engine's greeks study, not a build. No ADR/TD/ENH ID was minted by this lane; every ID below is `TD-PIN2-NEW-k` (lane prefix, Rule 14) or `PROPOSED-ID`. The only production change in the series is the operator's own grant and policy on `fyers_futures_bars_1m` (section 4).

## 1. Results this stretch

| Item | Result | Where |
|---|---|---|
| Pin definition ruled | Textbook pin (gross gamma x total OI) is the reference; the Board's net-peak "pin" is a different quantity. Label "Pin Band" stays unchanged (operator, 22 Nov). | `ruling_pin_definition_2026-11-21.md` |
| Live replay v2 | Frozen pass rule applied to the one-gamma-per-strike (VS) candidate against the live Board pin. | `pin_live_replay_v2_result_2026-11-21.md` |
| VS follow-up | A1-A4 and Pin-Band findings; VS view order matches the `vs_scores` ranking on dry run. | `pin_vs_followup_result_2026-11-22.md` |
| **Gamma pipeline audit (frozen, 22 Nov)** | Frozen rule section 6 (BETTER only if all four clauses hold on both symbols): **BETTER on NIFTY and SENSEX.** Own per-strike solve (K) is the reference. | `gamma_pipeline_audit_result_2026-11-22.md` |
| Decomposition (post-hoc, labelled so) | Zero-filling alone does not help: B2 (zero-or-missing filled from the sibling leg) delivers -2 % to +7 % of the improvement and worsens total-net error. The defect is **lopsided call/put gammas**, not blanks. The vendor field is never missing, only present as "0.0". The seven adverse days are days production was unusually good; no column separates them. | same |
| One-gamma net | Net gamma built on one gamma per strike is evidence for the engine's greeks study (R9), not a build proposal. Longer-term candidate: own per-strike solve. | `pin_fix_scope_DRAFT_2026-11-21.md` section 4 |
| Gate trace | Only `gamma_metrics.regime` gates `trade_allowed`. The Board flip is `v_gex_repriced_flip.flip` (ENH-131), not `gamma_metrics.flip_level`. Walls come from raw OI with sigma from the newest `volatility_snapshots.atm_iv_avg` (no age bound). | box `fix/proposal/trace.md` |
| Signal path status | Read of what builds and runs the signal path; inconsistencies are in section 5 rows 12-15. | box `fix/proposal/signal_path_status.md` |

Audit integrity: self-test 85 passes plus mutation detected; `self_test_b.py` 20/20; box `SHA256SUMS` 23 files, verifies. Frozen prereg sha256 `93ab228ff20aa9e8477f0f27353349cc2ade23d057144825e9825daba5d49269`. Box hashes: results.md `024562bb0c15223255dce712e7b79d1b78d5b13865db99bb0c08c83c426b3bc3`, runs.csv `8363b69c...5a76f100`, decomp.md `046ad0df0c018bac1e3f2d233b28fad4cf87fe266ec0fd72ad49087a71df3301`, runs_decomp.csv `81d0abeba5b6fa31cbe1f8360fdb1445650017b2e673dc0866814f1e616bf847`, PROMPT.md `dd08b496cdff075ba76b5e64661a0a728b0fe4127f0dd6eb7f6486cef6002d19`.

## 2. Method facts and rulings (this stretch)

- Four "pin" quantities: (a) gross pin = gamma x (OIc+OIp) (proposed); (b) net peak of either sign (Board Pin, `pin_leader_strike`, /tape anchor, "Top-strike share"); (c) largest positive net strike (`max_gamma_strike`, band start); (d) Pin Band (`v_gex_strike_pin_zone`, positive-only walk, tau 0.3). The Board's "Gross |Gamma|" tile is Sum abs(net per strike), not gross exposure.
- Constructions: P production (two vendor gammas, zero legs contribute 0); VS one gamma per strike (mean of gc, gp when both > 0; the positive one if the other is 0 or NULL; 0 if neither); K own per-strike solve (Black-76 IV of the OTM leg against the median forward, r = 0, T in minutes to 15:30 IST on expiry); B1 missing-only fill (identical to P because the field is never missing); B2 zero-or-missing filled from the sibling leg.
- Operator rulings: proceed with VS as the preferred shadow pin methodology (shadow, not live); "Pin Band" label unchanged; the `trade_allowed` / LONG_GAMMA / NO_FLIP gate is an artifact of the early "Buy CE / Buy PE signals only" era, ignore it as a pin-lane item, and registers that still describe it as current need updating; flip computation has changed along the way; "if not in PK, dig it out of the repo".
- Query discipline held all stretch: catalog first; plain EXPLAIN gate; one symbol-day per query; 5 s sleeps; stop at first error or any query over 10 s; live `ts` is timestamptz, history `bar_ts` is IST-labelled +00.

## 3. State at close

- The Claude Code pin session (tmux 0, "Pin behaviour study", manual mode) is idle at its prompt; its suggested line is not the operator's.
- Shadow view: SQL file is a DRAFT (revision 2 = VS), **not run anywhere**; SELECT dry run on 22 Nov: plan clean, 2.93 s, 135 rows. Revision 3 is requested of the engine (section 5 row 1). Operator applies only after the engine authors a `sql/` file.
- Box research folders are **on a pushed branch, not on `main`**: `meridian-engine` branch `pin/records-pin2`, commit `1d71970de3b3ed9294cd4325ac2dda105b224156` (parent `origin/main` `0b9aa1051aba66217f559a7baf2031c5cac5ea7c`), pushed 2026-11-23 ~05:57 IST, `ls-remote` sha matches. `e1-e3-e10` is still unmerged and was only read. The **35 PK files are in no git branch** (no PK export route; PK has no download).
- PK: knowledge_size 1,740,885 / 2,000,000 (87.0 %) at close start, above the 85 % prune line (PK Protocol P7).

## 4. Operator actions owed

- **R4: undo the `merdian_ro` SELECT grant and policy on `fyers_futures_bars_1m`** (operator action in the SQL editor; recorded as ruled in engine intake I001):
  `DROP POLICY ro_select_merdian ON public.fyers_futures_bars_1m;`
  `REVOKE SELECT ON public.fyers_futures_bars_1m FROM merdian_ro;`
  Status: **RAN by the operator Mon 2026-11-23 ~05:05 IST**; the editor returned "Success. No rows returned". Not yet confirmed by a catalog read (policy and grant gone): do that read once at PIN3 open before relying on it.
- Box git route (section 7 of this file): worktree off `main`, commit the lane records, push.

## 5. Engine intake (for the next engine doc-close; v5.1 Rule 13)

Only changes to engine-owned facts. Lane-local results stay above. Labels: EVIDENCED / VERIFY (give the read) / DECIDE (operator choice needed). Engine objects named are as read in the registers this session.

| # | Fact (one line, with figure and unit) | Engine object | Target register | Proposed ID | Label | Evidence |
|---|---|---|---|---|---|---|
| 1 | Gross-pin shadow view (VS rule) proposed; revision 3 asked: legs-supplied column, per-run count of in-set strikes with OI and no gamma, `sql/` file with live COMMENT and GRANT, md5 registration (Rule 25), data_contracts entry (ADR-031), per-1 % wrapper (ADR-032) if it reaches the Board. Shadow = ten trading days incl. at least 2 expiry days per symbol, evening read-only replay, pass = replay-v2 rule (>= 95 % pooled clear-lead; >= 90 % of days meeting 95 % / 85 %); share outside the Pin Band reported not judged. Board switch is a separate decision needing an order-flow lane note first (STREAMS X1). | `v_gex_strike_rank` family; Board | ENH / sql | PROPOSED-ID | DECIDE | `pin_fix_scope_DRAFT_2026-11-21.md` sections 3, 7, 8; the SQL draft |
| 2 | Frozen audit: one-gamma-per-strike beats production on NIFTY and SENSEX against the own-solve reference; defect is lopsided call/put gammas, not blank fields (field never missing, "0.0" present). | `gamma.py:42,50-52,54-55,719-730`; `gex_strike_snapshots` | Assumption Register | PROPOSED-ID | EVIDENCED | `gamma_pipeline_audit_result_2026-11-22.md` |
| 3 | One-gamma net (G2) is evidence for the R9 greeks / forward study; longer-term candidate is an own per-strike solve. Not a build. | greeks study (engine lane) | ENH / study | PROPOSED-ID | DECIDE | `pin_fix_scope_DRAFT_2026-11-21.md` section 4 |
| 4 | Precision work item: provenance of the stored gamma precision against `raw` unconfirmed. | `gex_strike_snapshots` / `raw` | TD | TD-PIN2-NEW-1 | VERIFY (read `raw` vs stored) | box `fix/proposal/trace.md` |
| 5 | Board "Gross |Gamma|" tile = Sum abs(net per strike), not gross exposure (label names a different quantity). | Board | TD | TD-PIN2-NEW-2 | EVIDENCED | follow-up result; scope section 6 |
| 6 | `hhi_net` feeds `conc_top1_share` (:388), shown as "Top-strike share"; it is net-based. | Board | TD | TD-PIN2-NEW-3 | EVIDENCED | scope section 6 |
| 7 | `latest_gamma_walls` is referenced but not defined where read. | Board / views | TD | TD-PIN2-NEW-4 | VERIFY (catalog read) | trace.md |
| 8 | Walls fall outside the corridor on about one run in four; frozen-OI runs move any pin; 2026-08-25 runs have no chain legs. | `gex_strike_snapshots` | TD | TD-PIN2-NEW-5 | VERIFY (rerun the count) | scope section 6; audit result limits |
| 9 | Some Board tiles carry "COMMENT not live" (documented in the draft SQL, not in the live catalog). | Board views | TD | TD-PIN2-NEW-6 | VERIFY (catalog read) | scope section 6 |
| 10 | Vendor reason for zero gammas on ITM legs; whether leg gamma and OI are the same moment. Both unknown. | vendor ingest | TD | TD-PIN2-NEW-7 | VERIFY (vendor ticket) | audit result limits |
| 11 | The `trade_allowed` gate (`gamma_metrics.regime`: LONG_GAMMA / NO_FLIP) is a leftover from the Buy-CE / Buy-PE-only era (operator, 22 Nov). Registers still record it as current: ADR-007 Decision Index row :64; `merdian_reference.json` `build_trade_signal_local` ACTIVE / ENH-35 and alert daemon "RUNNING PID 19636"; Assumption Register D.2, D.9, D.13; System Map :180 vs Topology :204 "Shadow signals". Registers to be updated. | registers | Decision Index / reference / AR / Map / Topology | PROPOSED-ID | DECIDE (and VERIFY each line against current state) | operator ruling 12:03 and 12:07 IST; trace.md |
| 12 | `eod_health_check` expects >= 60 rows; the reads show about 2. | signal path | TD | TD-PIN2-NEW-8 | VERIFY | signal_path_status.md |
| 13 | `merdian_order_placer.py` is missing from `merdian_reference.json`. | reference json | TD | TD-PIN2-NEW-9 | VERIFY | signal_path_status.md |
| 14 | Unknown which host runs the live signal path; `build_shadow_signal_v3` scheduling unknown; whether the Local scheduler runs the dashboard and trade logger; `signal_v4` existence; whether the builder should still run every cycle. | Topology / schedulers | TD | TD-PIN2-NEW-10 | VERIFY | signal_path_status.md |
| 15 | Board "regime" string vs `gamma_metrics.regime`: unconfirmed same object. Board flip is `v_gex_repriced_flip.flip` (ENH-131); engine `flip_level` is pooled constructions and is not shown. Effect of vendor per-leg IV on the repriced flip unmeasured. | Board | Map / TD | TD-PIN2-NEW-11 | VERIFY | trace.md |
| 16 | Engine finding: OOM hang on the box on 21 Nov, no swap, `ulimit` did not protect the box. | box | Topology / TD | TD-PIN2-NEW-12 | EVIDENCED | I001 (engine intake) |
| 18 | The root `.gitignore` excludes `*.log`, `*.csv` and `*.txt` repo-wide (lines 33, 43, 44), so `git add` silently drops research records of those types: 1,255 of 3,528 in this commit. Worked around under `docs/research/pin_proof/` only with a negation file. | repo root `.gitignore` | TD / `.claude/rules/data-access.md` | TD-PIN2-NEW-13 | EVIDENCED | commit `1d71970` `.gitignore`; box check-ignore |
| 17 | ADR-024 Amend A, ENH-125, ENH-122 and the manual need correction of what they say about the pin (net vs gross). | ADR-024 / ENH / manual | ADR / ENH | PROPOSED-ID | VERIFY | scope section 3 |

Blocks another lane? **Yes: row 1 (Board switch) needs an order-flow lane note first** (STREAMS X1); also enter in `STREAMS.md` section 3. Rows 3 and 15 feed the engine's greeks study (also FOI3 item 1).
Git: box research records committed at `1d71970de3b3ed9294cd4325ac2dda105b224156` on `pin/records-pin2` (pushed, **not merged to `main`**; merge is the operator's or the next engine close's call). The 35 PK-only records are **held** by the missing PK-to-box route (section 7).

## 6. Owed list and carry items

1. R4 undo: run 23 Nov ~05:05 IST (section 4); catalog confirmation read still owed.
2. Merge `pin/records-pin2` to `main` (operator or engine close); get the 35 PK files into git; then P4 steps 4-6.
3. Mid-price re-run of K (deferred).
4. Parked predictive tests P1d and P1c.
5. MR-PIN1 close inputs section 5 items 8-9 (register items; D-5a pointers) and step 2 of the Board list (D6/N12, D8/N11, D5/K1, N13, labels, A1/A2).
6. Shadow plan steps once the engine authors the `sql/` file: evening read-only replay record (B, V2 comparator, VS, K).
7. VS vs Pin Band remains unmeasured (the shadow reports it).
8. Layer 3 (dealer positioning interpretation, "dampening / amplifying") untested; sign convention assumed.
9. Whether any other one-gamma rule beats the mean: untested.

## 7. PK delta (PK Protocol v1, P4)

knowledge_size at close: 1,748,877 / 2,000,000 (87.4 %), above the 85 % prune line (checked after the two close files were written).
**Step reached: 3 of 7 for the box research folders; 2 of 7 for the 35 PK files.** Step 4 cannot pass until `pin/records-pin2` is merged to `main` and the 35 PK files are in git. Steps 5-7 wait on that.
Commit: `meridian-engine` branch `pin/records-pin2`, `1d71970de3b3ed9294cd4325ac2dda105b224156`, 3,530 files all under `docs/research/pin_proof/` (3,528 records + `MANIFEST.md` + a scoped `.gitignore`). Pushed, not on `main` (the branch that counts, P2.3). Box worktree `~/meridian-pin-records` and the local branch remain in place.
Committed: `fix/audit` 21, `fix/proposal` 6, `fix/view` 18, `fix/replay_v2` 768, `fix/followup` 43, `lookback_v5` 2,489, `gamma_inputs` 180. Left on the box: 748 raw dumps over 40 KB (626 `.txt`, 117 `.jsonl`, 5 `.csv`; 390,432,680 bytes), listed in `MANIFEST.md` with size and sha256. Kept despite 40 KB: `lookback_v5/SHA256SUMS`, `fix/replay_v2/SHA256SUMS`, `lookback_v5/analyze_v5.py`, `MANIFEST.md`. Checks: `sha256sum -c` 4,204 OK / 0 FAILED; `cmp` 3,528 identical; secret-pattern scan 0 matches across 3,530 files (3,528 read; 809 control matches); 0 `.pyc`; 0 dumps leaked.
**Finding for the engine (also an intake row):** the root `.gitignore` excludes `*.log` (line 33), `*.csv` (43) and `*.txt` (44) everywhere, which silently dropped 1,255 of the 3,528 records; fixed with a negation under `docs/research/pin_proof/` only, not `git add -f`. The same silent drop will hit any other research folder that holds those types.

| PK path (claude/pin/) | Action | In git (P4 step 4) | Note |
|---|---|---|---|
| MR_PIN2_close_inputs.md | ADDED | no | KEEP |
| MR_PIN3_session_prompt.md | ADDED | no | KEEP |
| gamma_pipeline_audit_result_2026-11-22.md | KEPT | no | KEEP; replaced in place after decomposition |
| gamma_pipeline_audit_prereg_FROZEN_2026-11-22.md | KEPT | no | KEEP |
| pin_vs_followup_result_2026-11-22.md | KEPT | no | KEEP |
| pin_fix_scope_DRAFT_2026-11-21.md | REPLACED (earlier this stretch) | no | KEEP; now the engine proposal |
| 2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql | KEPT | no | KEEP |
| pin_live_replay_v2_result_2026-11-21.md | KEPT | no | KEEP |
| pin_live_replay_prereg_v2_FROZEN_2026-11-21.md | KEPT | no | KEEP (pass rule the shadow reuses) |
| pin_behaviour_v5_result_2026-11-21.md, pin_behaviour_study_v5_FROZEN_2026-11-21.md | KEPT | no | KEEP |
| ruling_pin_definition_2026-11-21.md, ruling_D5a_reopen_2026-11-20.md | KEPT | no | KEEP (current and previous session rulings) |
| gamma_rate_sensitivity_result_2026-11-20.md | KEPT | no | KEEP until the engine takes it into I-002 |
| MR_PIN2_session_prompt.md | CARRIED | no | **GO** once in git (replaced by PIN3 prompt) |
| MR_PIN1_close_inputs.md | CARRIED | no | **GO** once in git (previous close) |
| cc_prompt_pin_vs_followup.md, cc_prompt_pin_live_replay.md, cc_prompt_pin_live_replay_v2.md, cc_prompt_pin_fix_stage0_code_read.md, cc_prompt_pin_behaviour_A_step0.md, cc_prompt_pin_behaviour_B_data_pull.md, cc_prompt_pin_behaviour_C_measures.md, cc_prompt_gamma_rate_sensitivity_run.md, cc_prompt_gamma_inputs_check.md, cc_prompt_pin2_box_state_check.md, cc_prompt_pin_proof_stage1.md | CARRIED | no | **GO** once in git (executed prompts, P3.6) |
| pin_live_replay_result_2026-11-21.md, pin_live_replay_prereg_FROZEN_2026-11-21.md | CARRIED | no | **GO** once in git (v1, superseded by v2) |
| pin_behaviour_study_v4_FROZEN_2026-11-20.md, pin_behaviour_step0_result_2026-11-21.md | CARRIED | no | **GO** once in git (superseded by v5) |
| gamma_rate_sensitivity_design_v2_FROZEN_2026-11-20.md, pin_proof_prereg_DRAFT_2026-11-19.md | CARRIED | no | **GO** once in git (executed; results live in result docs) |
| partA_results_2026-11-19.md, partB_results_2026-11-20.md | CARRIED | no | **GO** once in git. The PK copies are not byte-equal to the box originals (`gamma_inputs/`): commit the PK copies under their own names, do not overwrite the originals. |

Carried (not in git, still in PK): every row above; reason for all: the 35 PK files are in no git branch (PK has no download and the box cannot read PK; a same-name search of both box trees and `origin/main` found 0 of the 28 older records). Clears at the PIN3 open once an export route is found and the files are committed and merged to `main`. Nothing was deleted from PK at this close. **Do not delete any path before `git ls-files --error-unmatch` prints it** (P4 step 4).
Requests to other lanes (also in STREAMS.md section 3): row 1, order-flow lane note (X1) before any Board switch.

Git route: the box research folders are done through step 3 (above). For the 35 PK files the route below stays open: step 2 needs them on the box first. Candidate for PIN3: test whether the chat can export PK files to a download; otherwise paste blocks for the 7 chat-written files. Original route (box that holds `~/meridian-cc`, bash; confirm the time is outside 08:30-15:40 IST Mon-Fri first):
1. `git fetch`; `git worktree add ../meridian-pin-records origin/main -b pin/records-pin2`.
2. Copy byte for byte into `docs/research/pin_proof/` (same relative names as PK): every file in the table above. Box research files already under `docs/research/pin_proof/` (audit, proposal, view dry run, replay, lookback, gamma_inputs) go in as they are, minus `__pycache__`, with `SHA256SUMS` re-verified first.
3. `git add <explicit paths>`; commit; push; merge to `main` per P8 (or hand to the next engine close through intake). Record the sha.
4. `git fetch` then `git ls-files --error-unmatch <every GO path at docs/research/pin_proof/...>` on `origin/main`; delete from PK only the paths it prints.
5. `project_info`: no GO path remains, no path twice, record knowledge_size.

## 8. Things I got wrong in MR-PIN2 (so they are not repeated)

- Planned a first self-test that re-implemented the arithmetic it was meant to check; rebuilt around `measure_run` with a mutation check.
- Gave a hand figure (E_shape_P 0.345196) that was wrong; exact 88/255 = 0.345098.
- Told the operator the proposal rewrite could go to CC; PK is chat-only and CC never writes PK.
- Cited E-02 / D-06 as pending when the registers show D-06 done and the three-zone model superseded.
- Conflated the two flips (Board repriced flip vs `gamma_metrics.flip_level`).
- Called zero gammas "blank/missing" when the field is never missing, only "0.0".
- Added a result-doc PK write beyond "no new PK files" and disclosed it.
- Combined a `pkill`, a patch and a launch in one command and killed my own shell; one action per command, verify exactly one runner.
- Was too ready to agree: the operator said "You don't have to readily agree with me". Disagree where the evidence does.

## 9. Binding rules (carry unchanged)

- "Don't guess, answer only if sure." Read docs before asking the operator to check anything; if not in PK, the repo holds it.
- Claude Code's suggested next-prompt lines (the `❯ ...` lines) are not the operator's decision.
- Operator-only first. Pre-registration before the first outcome query; one look; nothing altered after test data is seen. Rule 0: a check must be able to fail for the reason it names; units on every figure; denominators on every count.
- No secrets in chat, repo or logs. Reads on the box through `bin/roq.sh` as `merdian_ro`; the `fyers_loader` login is never used; grants and policies are the operator's action in the SQL editor; Claude does not run SQL on production. One CC session per tree; no box analysis 08:30-15:40 IST Mon-Fri; every run under `ulimit -v`; `python3 -B`, no `.pyc` in a sealed folder.
- Every CC prompt carries its conditions inside it, exact text. At a CC permission screen the operator answers with the bare option number plus a short explanation.
- Session close is when the operator says so; no reminders. Never mention sleep or rest; never suggest pausing or ending.
- PK (binding, `claude/MERDIAN_PK_Protocol_v1.md`): lane=pin; write only in `claude/pin/`; replace in place, no `_v2` working copies; no reference-product name (write "the parity target").
