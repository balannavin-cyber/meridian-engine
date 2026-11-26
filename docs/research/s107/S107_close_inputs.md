<!-- pk: lane=engine; git=meridian-engine:docs/research/s107/S107_close_inputs.md -->
# Engine S107 close inputs (written Thu 2026-11-26 about 10:30 IST on the operator's "EOS document"; next session S108)

S107 ran Sat 2026-11-21 to Thu 2026-11-26. Read with `docs/session_notes/CURRENT.md` (the S107 block),
`docs/research/s107/rulings_s107.md`, `docs/registers/intake/I002.md` and `I003.md`,
`docs/research/s107/engine_to_pin_LATEST.md`. This file does not repeat them.

## 1. What this close is, and what it is not

- **Built and tested in a read-only clone.** The engine chat cannot push. The close is one package: the engine's 18
  S107 files taken from branch `pin/v2-check` at `2574709` by path, five new documents under
  `docs/research/s107/`, intake `I003.md`, and `scripts/patch_s107_docclose.py` with its payload, which edits 20
  register files (every anchor asserted to occur once; end-of-line style preserved; the CURRENT roll asserted
  byte-identical).
- **Tested on a scratch tree at `6a69dbe`:** dry run clean, apply clean, a second run refuses (already applied);
  `merdian_reference.json` parses and only the three version keys and the new addendum differ;
  `tests/test_gamma_v2_selftest.py` ends `SELFTEST PASS -- 28 mutants`; `tests/test_merdian_compute_contract.py`
  ends `CONTRACT ALL PASS`; no diff against `main` for `merdian_compute/gamma.py` or
  `compute_gamma_metrics_local.py`.
- **Not verified here:** `tests/test_merdian_compute_import_purity.py` (offline step 24). In the chat's sandbox it
  fails on unmodified `main` too, because the sandbox's own Python start-up reads an environment variable and trips
  the test's wire. The operator runs it on Local as a gate before the commit. `gamma_v2.py` imports only
  `__future__`, `decimal` and `typing`, and the package's `__init__` does not import it.
- **Not run:** the full `tests/run_offline.sh`.

## 2. Open at this close (the short list; detail in CURRENT)

1. The `script_execution_log` read (TD-S107-NEW-6) — asked, not returned.
2. The operator's market-hours look at the live Board — owed from 26 Nov 09:20 IST, not reported.
3. The pin lane's step 9, then the operator's decision on V2.
4. Operator decisions: ADR-033 status; PUBLIC grants (TD-S107-NEW-3); the signal builder (TD-PIN2-NEW-10); box
   memory (TD-PIN2-NEW-12).
5. The merge of `engine/s107-close`. Its sha goes into CURRENT at the S108 open.

## 3. Things I got wrong in S107 (so they are not repeated)

- Expected values written from memory or from a fixture and given to others to check against (the `tape_w` grant
  lines; 156 runs for a day that holds 166). Assumption Register §D.62.1, §D.62.2.
- Board deploy scripts without the proxy build settings; a bundle audit so broad it matched library text; a
  retention step that would have deleted five backups. §D.62.3, TD-S107-NEW-1.
- A package committed without having the operator print the branch. §D.62.5.
- The note to the order-flow lane that STREAMS X1 required before a Board pin change was not written before it.
  §D.62.4.
- A `.gitignore` rule (`/apply_*.py`) silently dropped a file from a commit; the tables file first lacked the
  `service_role` grants; the backfill first listed runs from a table with a retention job and skipped weekends.
  All three were found by reading before anything ran on production.

## 4. PK delta (PK Protocol v1.1, P6 with P4 for the engine folder)

knowledge_size when the close opened: 1,702,983 / 2,000,000 (85.1 %).
After the engine's deletions and additions below, before this file: **1,690,763 / 2,000,000 (84.5 %)** (`project_info`, 26 Nov about 10:15 IST; no path appears twice).
**Step reached: P4 steps 1, 2, 4 (path check by file name against `origin/main`), 5 and 6 for the files below; step 3 (commit) is the operator's merge of this close.**

| PK path | Action | Mirror path | In git | Note |
|---|---|---|---|---|
| `claude/rulings_s107.md` | ADDED | `meridian-engine:docs/research/s107/rulings_s107.md` | with this close | Tier C |
| `claude/S108_session_prompt.md` | ADDED | `…/s107/S108_session_prompt.md` | with this close | Tier C |
| `claude/S107_close_inputs.md` | ADDED | `…/s107/S107_close_inputs.md` | with this close | this file |
| `claude/engine_note_board_pin_switch_for_ofl_2026-11-26.md` | ADDED | `…/s107/` same name | with this close | Tier C; leaves PK at the S108 close once OFL10 has read it |
| `claude/engine_to_pin_LATEST.md` | REPLACED (deleted, then written) | `…/s107/engine_to_pin_LATEST.md` | with this close | standing note to the pin lane; byte-equal to the git file at this close |
| `claude/engine_e1_e3_e10_deploy_and_first_live_drop_2026-11-21.md` | DELETED | `docs/research/s106/` same name | yes | |
| `claude/rulings_s104.md` | DELETED | `docs/research/s92_parity/rulings_s104.md` | yes | |
| `claude/S104_session_prompt.md` | DELETED | `docs/research/s104/` same name | yes | |
| `claude/S103_close_inputs.md` | DELETED | `docs/research/s103/` same name | yes | |
| `claude/2026-10-30_s102_gex_per_1pct_views.sql` | DELETED | `sql/` same name | yes | |
| `claude/gex_unit_inventory_S102.md` | DELETED | `docs/research/s102/` same name | yes | |
| `claude/P4_charm_sign_prereg_2026-10-10.md` | DELETED | `docs/research/s94_priority/` same name | yes | |
| `claude/engine_study_vendor_greeks_convention_DRAFT_2026-11-19.md`, `claude/engine_note_pin_basis_and_vendor_greeks_2026-11-18.md` | KEPT | `docs/research/s106/` | yes | the greeks study is open (R9) |
| `claude/parity_eval/06_parity_target_posts_2026-11-15_to_17.md`, `claude/parity_eval/S100_status_vs_final_report.md`, `claude/MERDIAN_Parity_Target_Spec.md` | KEPT | in git | yes | latest parity records |
| `claude/intake/engine_intake_I001_2026-11-21.md` | CARRIED | `docs/registers/intake/I001.md` (different name) | by content, not by path | delete at S108 once compared |
| `claude/adr032_sweep_engine_90_report.md`, `adr032_sweep_engine_95_diff.md`, `adr032_sweep_retail_90_report.md` | CARRIED (transition T3) | `docs/research/s104/` | **no** | no route from this chat to copy a PK file to git byte for byte |
| `claude/anon_plug_RESULT_S104.md`, `anon_phase2_design_S104.md`, `anon_exposure_plan_S104.md`, `brief_marketview_anon_key_exposure.md`, `muhurat_2026-11-08_checklist.md`, `paper_trades_SENSEX_08Oct_expiry.md`, `paper_trades_SENSEX_15Oct_expiry.md`, `ref_2026-10-01_SENSEX_0DTE.md`, `target_read_Mar-Oct2026.md`, `target_read_implications_S88.md`, `parity_dovetail_and_post_parity_plan_S89.md`, `retail_scope_draft_2026-10-25.md`, `marketview_user_manual_v04_DRAFT.md`, `pk_extract_s100.py`, `board_accuracy_discrepancies_2026-11-19.md`, `board_accuracy_log_2026-11-19.md`; `claude/parity_eval/parity_target_final_report_2026-10-19.md`, `04_author_read.md`, `00_inventory.md` | CARRIED (transition T4) | `docs/research/s<N>/`, `docs/research/parity_eval/` | **no** | same reason; 19 files |

Carried (not in git, still in PK): 22 engine files plus the I-001 copy. **Reason:** the engine chat can read a PK
file and can write to PK, but has no way to place a PK file's bytes into git except retyping it, which is not byte
for byte. **What clears it:** the operator downloads these 22 files from the project and drops them in the close
worktree at the mirror paths (or a later session is given a route); then they are deleted from PK. Several name the
reference product and need the P3.4 substitution in their git copy, which is one more reason not to retype them here.

**Tier A and B refresh (P6 steps 2 and 3), the operator's upload after the merge.** Changed in git by this close:
`CLAUDE.md`, `CLAUDE_history.md`, `tech_debt` (PK name `tech_debt_LATEST.md`), `MERDIAN_Enhancement_Register`
(`…_LATEST.md`), `merdian_reference` (`…_LATEST.json`), `MERDIAN_Assumption_Register.md`, `MERDIAN_System_Map.md`,
`MERDIAN_Deployment_Topology.md`, `MERDIAN_Data_Inventory.md`, `MERDIAN_Decision_Index.md`,
`agentic_layer_roadmap_S90.md`, `CURRENT.md`, `STREAMS.md`, `claude/session_log.md`; new Tier B: `ADR-033`.
Their growth in git is about 82,000 bytes. **Expected knowledge_size after the refresh: about 1,780,000 (89 %)** —
under the 90 % hard stop, above the 85 % prune line. Delete each PK copy before uploading its replacement (P3.3).

**Whole-PK audit (P6 step 5), from `project_info`:**

| Check | Result |
|---|---|
| (a) duplicate paths | none |
| (b) files at the PK root outside Tier A/B | none found |
| (c) lane folders against their last PK delta | **OFL:** more than 50 order-flow files are still at `claude/` root (`MR_OFL1`–`8`, `rulings_mr_ofl*`, `tape_*`, `cc_prompt_tape_*`, `lovable_prompt_tape_*`, `2b_writer_plan`, `Q1_upsert_gate_plan`), as its OFL9 delta says (step 2 of 7). **Retail:** about 61 files carried, as its S13 delta says; `claude/retail_scope_draft_2026-10-25.md` sits at the engine root and is retail's. **Pin:** `old_vs_new_prereg_DRAFT_2026-11-25.md`, `old_vs_new_prereg_A1_PROPOSED_2026-11-26.md` and `pin_monitor_review_addendum_DRAFT_2026-11-26.md` are superseded by their FROZEN versions. **FOI:** unchanged since FOI2 |
| (d) budget | 84.5 % now; about 89 % after the Tier A refresh |

Requests to other lanes (also STREAMS §3 by this note; the engine deletes no lane's file):
- **OFL10:** run P4 first; the order-flow files at `claude/` root are the largest prunable set in PK.
- **MR-S14:** move the carried retail set first, as its S13 delta already says.
- **MR-PIN4:** drop the three superseded drafts at its close once their git copies exist.
