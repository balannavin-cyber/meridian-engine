<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/MR_PIN3_close_inputs.md -->
# MR-PIN3 close inputs (written Wed 2026-11-25, evening, on the operator's "build/update the EOS docs", 19:57 IST message; series MR-PIN = Board pin accuracy; next session MR-PIN4)

MR-PIN3 ran Sun 2026-11-22 (evening) to Wed 2026-11-25. Read with: `TRACKER.md` (the one tracker; this file does not repeat its steps), `to_engine_LATEST.md` (pin lane to engine, rewritten 19:55 IST), `claude/engine_to_pin_LATEST.md` (engine to pin lane, 19:45 IST), `b2_backfill_check_result_2026-11-25.md`, `v2_rule_conformance_result_v12_2026-11-25.md`, `v2_rule_conformance_addendum_v12_FROZEN_2026-11-25.md`, `v2_rule_conformance_prereg_FROZEN_2026-11-25.md`, `pin_monitor_prereg_FROZEN_2026-11-24.md`, `pin_monitor_build_record_2026-11-24.md`, `ruling_shadow_dropped_2026-11-23.md`. Figures below were printed by Claude Code, by the pin lane's own code, or pasted by the operator.

**What is live (operator-promoted, 25 Nov about 18:08 IST):** Board `d7642c2`: the Pin tile shows the gross pin, the old pin is shown as "Net peak", old flip-based outputs are labelled legacy/unvalidated, the Board Flip is labelled experimental, manual v0.6. **Nothing else of the gamma source fix is live.** Not approved: the writer hook, scheduling the `p3b2` job, the `v_gex2_*` views, any Board tile move to V2 figures.

## 1. Results this session

| Item | Result | Where |
|---|---|---|
| Order check on revision 3 of `v_gex_strike_rank_gross` (23 Nov) | PASS. Revision 3 applied by the operator 23 Nov (`sql/2026-11-23_s107_v_gex_strike_rank_gross.sql`, md5 `2e94b918e1d13a1a4383bf7d3bf8026c`) | `order_check_rev3_prereg_FROZEN_2026-11-23.md`; box `fix/order_check_rev3/`, main `5a96195` |
| Ten-day shadow | Dropped by the operator, 23 Nov 20:48 IST | `ruling_shadow_dropped_2026-11-23.md` |
| Pin monitor | Design approved and frozen 24 Nov; built 24 Nov (self-test 210 pass, 0 fail); first recorded day **Wed 25 Nov done, exit 0, 25 hashes OK** | `pin_monitor_prereg_FROZEN_2026-11-24.md`, `pin_monitor_build_record_2026-11-24.md`; box `~/meridian-cc/docs/research/pin_proof/monitor/` |
| Monitor day 1 (recorded, not judged; one day) | NIFTY: front expiry 1 Dec (dte 6), gross pin 26000, Board pin 26000, close 25819.25, pin equals Board pin on 42 of 75 runs, pin outside the Pin Band on 33 of 75. SENSEX: front expiry 26 Nov (dte 1), gross pin 84000, Board pin 85000, close 83938.28, pin equals Board pin on 11 of 75 runs, outside the band on 55 of 75. The "Board pin" in the monitor is the Board pin as the monitor reads it for that day; the switch happened after the 14:30 pin time. | box day folder; files not yet committed |
| V-2: engine's V2 code against rule v1.1 and v1.2, independent implementation | **PASS** at `a9982c7` (v1.1, on the box), at `a9b38bc` (v1.2) and again at `25747092c77c385e3e5d539a8a1829c1227b6bc6` (package r4, `gamma_v2.py` sha256 `ba611363f28ed8c3d89ccc3c3f0bfb99c87fb077d16c081f36d40f298bac4e95`). 486 chain runs and 313 stored-row runs, 0 mismatches, engine self-test 28 mutants | `v2_rule_conformance_*` files (prereg `b1a156a8...7361d`, v1.2 addendum `90f491e1...81d2`) |
| V-2 coverage on the six golden days | 65,721 strike rows; both legs gamma 20,227; call only 17,424; put only 6,803; guarded-both 282; not in map 20,985. Other-leg OI now counts on 16,695 of 44,736 in-map strikes (37 %); the guard removed 4,289 legs; net exactly 0 on 363 rows; duplicate, edge and error runs 0 | `v2_rule_conformance_result_v12_2026-11-25.md` |
| Tables, one-day backfill, B2 | Tables applied by the operator about 19:15 IST. B1 backfill 2026-08-27: 166 runs, 23,323 strike rows, 0 input errors. **B2 PASS**: 156 of 156 fixture runs agree; largest relative difference 4.5e-13 | `b2_backfill_check_result_2026-11-25.md` |
| Flip options and containment (advisor pack) | Delivered to the operator 25 Nov; Option D ruled. Corrections to the first note: the Board Flip filters legs with `gamma IS NOT NULL AND gamma <> 0` so it inherits the blank-gamma gap, has no value at dte 0 | pin lane workspace file `advisor_pack_flip_2026-11-25.md` (git copy owed; not in PK) |
| Dealer side (P2) | Pro holds 23 / inverted 113 / mixed 204 of 340 dates; Pro + FII 0 / 231 / 109; Client 226 / 0 / 114. Verdict REGIME-DEPENDENT; dates are not independent (OI carries over), NSE only. The Board's sign looks more like the client book than a dealer proxy; ADR-015 already says the stored quantity is "positioning gamma, not dealer gamma". Not evidence that the sign is inverted | advisor pack section 5 |

## 2. Rulings and decisions this session (all operator unless marked)

- 23 Nov 20:48: ten-day shadow dropped; a standing measurement discipline instead.
- 24 Nov: monitor design approved (pin taken at 14:30 IST, forward only, first day 25 Nov; both parts, review threshold as recommended). Fix gamma at the source, one gamma per strike, leave the Board Flip alone for now, unify on own-computed gammas later. The primary (gross) pin keeps the name "Pin".
- 25 Nov 09:19: **Option D, versioned isolation**: V1 legacy untouched; V2 in new module `merdian_compute/gamma_v2.py` and new tables `gex_strike_v2`, `gex_run_v2`; no V2 flip, regime, expansion or pin score. Old regime, expansion probability, pin score and dealer flow simulation labelled legacy/unvalidated now. Dealer-positioning wording: case by case, "maybe nothing changes". Flip replacement study: parked until the build is done.
- 25 Nov 09:23: Board Pin switches to the gross pin now; tile shows strike, share and lead; state and conviction sit under the "Net peak" line.
- 25 Nov 09:35: backfill the V2 tables from stored per-strike rows (yes); read-only access to the Board repo for the engine lane; Lovable version check; secret scan of the Board repo first (done: 320 commits, only the anon key in a tracked `.env`, no service key).
- 25 Nov 09:48: the independent conformance check approved; covers engine authoring and fixture-day tests only. Applying SQL, new tables, writer hook, backfill and Board changes each came back to the operator.
- 25 Nov 18:50: no shadow; order is tables, one-day backfill, full backfill, then the old-against-new comparison, then the operator's decision ("I agree. Lets go"). Writer hook, `v_gex2_*` views and Board tiles wait on that decision.
- 25 Nov 19:50 (pin lane's ruling at the operator's request; boundary awaits the operator's approval with the step 9 pre-registration): keep every stored run in the V2 tables, no market-hours filter in the backfill; filter by clock time in the comparison.
- 25 Nov: B3 (full backfill) cleared once B2 passed. The operator started it about 19:57 IST; the pin lane does not know its outcome at this close.

## 3. State at close

- **Git:** `main` last read at `934fe44`. The pin lane's V2 check files sit on branch `pin/v2-check` (Windows worktree `C:\wt-v2`; box detached worktree `~/meridian-v2-check` at `8adbeea`). That branch also carries the engine's package commits (`a9b38bc`, `25747092`), left there by the pin lane's decision. **Do not merge `pin/v2-check` into `main` as it stands**; the engine moves its own files, and the pin lane's files go out on a records branch (section 7).
- **Pin lane files that exist only in the pin lane's workspace** (not in git, not all in PK): v1.2 check code and logs, the B2 files, `advisor_pack_flip_2026-11-25.md`. Section 7 packs them.
- **Box:** Claude Code session tmux `0` in `~/meridian-cc` (manual mode) last known idle; its suggested prompt lines are not the operator's. Monitor day-1 files are in the day folder, uncommitted.
- **Database (engine-applied):** `v_gex_pin_gross` (owner rights; SELECT to authenticated, marketview_ro, merdian_ro; service_role full), `gex_strike_v2`, `gex_run_v2`, `p3b2_invariant_checks`, `p3b2_sweep`. No job scheduled.
- **PK:** see section 7.

## 4. Operator actions owed

1. B3 outcome: the engine reports it in `engine_to_pin_LATEST.md`; five items asked for in `to_engine_LATEST.md` section 3.
2. Git route for this close (section 7): Windows PowerShell block, then one box check.
3. Thu 26 Nov after 09:20 IST: the Board look in market hours (with the engine's short list).
4. Thu 26 Nov after 16:30 IST: monitor day 2. The combined prompt is **not written yet** (see MR-PIN4 prompt, item 4).
5. Approve the step 9 pre-registration when the pin lane brings it, including the clock-time boundary.

## 5. Engine intake (for the next engine doc-close; v5.1 Rule 13)

Labels: EVIDENCED / VERIFY / DECIDE. IDs are `TD-PIN3-NEW-k` or `PROPOSED-ID`. Items the engine already holds from MR-PIN2 (intake rows 1 to 18 of `MR_PIN2_close_inputs.md`) are not repeated; whether the engine took them is in its I-002 and not known to this lane.

| # | Fact | Engine object | Target register | Proposed ID | Label | Evidence |
|---|---|---|---|---|---|---|
| 1 | Board Pin is now the gross pin (`v_gex_pin_gross`); the old pin is shown as "Net peak" (`gex_cycle_history.pin_leader_strike`, unchanged); legacy and experimental labels live; manual v0.6; Board `d7642c2`, live about 18:08 IST 25 Nov | Board, `v_gex_pin_gross` | System Map, ADR-024 Amend A, ENH-125, ENH-122 | PROPOSED-ID | EVIDENCED | operator promotion; pin read on staging; monitor |
| 2 | An order-flow lane note (STREAMS X1) was a stated condition for any Board switch. The switch is live; how X1 was met is not in the pin lane's record | STREAMS | STREAMS section 3 | PROPOSED-ID | VERIFY | MR-PIN2 intake row 1; `ruling_shadow_dropped_2026-11-23.md` |
| 3 | Option D (versioned isolation) and rule v1.2 are ruled; V-2 PASS at three commits; B2 PASS for 2026-08-27 | ADR-033 draft, `gamma_v2.py`, `gex_strike_v2`, `gex_run_v2` | ADR-033, Data Inventory, System Map | engine-minted | EVIDENCED | the V-2 and B2 result files |
| 4 | ADR-033 section 4 should say the Pin tile (view) and the V2 table (rule) give one number except on a run with duplicate leg rows or a negative OI, where V4 fails by design | ADR-033 | ADR-033 | | DECIDE | `to_engine_LATEST.md` section 4 |
| 5 | Stored runs per symbol on 2026-08-27: 83 (08:35 to 15:20 at five-minute steps, then 15:40; none at 15:25, 15:30, 15:35). Eight runs before 09:15. OI stale until the 09:20 run; 08:35 to 08:45 identical. Whether other days have the same run set is not read | `gex_strike_snapshots`, `gex_cycle_history` | Data Inventory | TD-PIN3-NEW-1 | EVIDENCED for one day; VERIFY for the rest | `b2_backfill_check_result_2026-11-25.md` |
| 6 | The Board Flip (`v_gex_repriced_flip`) filters legs with `gamma IS NOT NULL AND gamma <> 0`, so it inherits the blank-gamma gap; no value at dte 0 | Board view | TD, Assumption Register | TD-PIN3-NEW-2 | EVIDENCED | advisor pack section 3 |
| 7 | The Pin detail panel quotes P1 (n = 85) without saying it was measured on the earlier net pin; the "#2" rule beside the net-rank readout; manual line for the two labels | Board | TD, manual | TD-PIN3-NEW-3 | VERIFY (read the panel text) | `to_engine_LATEST.md` section 4 |
| 8 | Dealer-positioning wording: stored quantity is positioning gamma, not dealer gamma; P2 verdict REGIME-DEPENDENT. Wording to be decided case by case, nothing changes meanwhile | Board, manual | Decision Index, manual | PROPOSED-ID | DECIDE | advisor pack section 5 |
| 9 | Removal of the legacy-labelled outputs (regime, expansion probability, pin score, dealer flow simulation) from the Board is planned for one release later | Board | ENH | PROPOSED-ID | DECIDE | tracker, Goal 3 step 3 |
| 10 | The pin monitor exists (daily record, forward only from 25 Nov); scheduling it later would be an intake row. The shadow condition (ENH-149 text, STREAMS X10) was withdrawn 23 Nov | monitor, ENH-149 | ENH-149, STREAMS | | VERIFY (engine told?) | `pin_monitor_build_record_2026-11-24.md`; `ruling_shadow_dropped_2026-11-23.md` |
| 11 | The engine's guard and promote scripts in git are faulty versions (lacked the proxy build settings; caught on staging); the engine is to replace them | deploy scripts | TD | | VERIFY | engine's own report, 25 Nov |

Blocks another lane? Row 2 needs an answer from the engine; nothing else. Git: pin lane records not yet committed at this close (section 7).

## 6. Owed list and carry items for MR-PIN4

1. Finish P4 (section 7).
2. B3 outcome and the checks that follow it: the five items in `to_engine_LATEST.md` section 3.
3. Step 9: pre-register the old-against-new comparison; operator approves before it runs. Known constraints: select runs by clock time; main set 09:15 to 15:30 IST (boundary to be approved), pre-open and post-close runs reported separately; the fixture-day facts in `b2_backfill_check_result_2026-11-25.md`; Rule 0 (units, denominators); one look.
4. Monitor day 2 (Thu 26 Nov after 16:30 IST): write the combined CC prompt (run the day; record the pin switch, 25 Nov 2026 about 18:08 IST, Board `d7642c2`, in `monitor/build/DECISIONS.md`; push the day's small files to a records branch; large strike files stay on the box with their hashes committed). Commit the day-1 files with it.
5. Carried from MR-PIN2, untouched this session: R4 catalog confirmation read (the policy `ro_select_merdian` and the `merdian_ro` grant on `fyers_futures_bars_1m` gone); mid-price re-run of K; precision provenance against `raw`; parked predictive tests P1d and P1c; "does the gross pin attract price" (the monitor collects the evidence; no test run); MR-PIN1 close inputs section 5 items 8 and 9; step 2 of the Board list (D6/N12, D8/N11, D5/K1, N13, labels, A1/A2) and the rest of the Board discrepancy list.
6. Open, not blocking: Pin Band follows the gross pin or not; gross-pin state and conviction; flip study (parked); dealer wording case by case.

## 7. PK delta (PK Protocol v1, P4)

knowledge_size at close: 1,722,784 / 2,000,000 (86.1 %), measured after the close files were written (this line's own edit moves it by under 1 KB). Above the 85 % prune line (1,700,000); the GO files below bring it down once they are in git.
**Step reached: 2 of 7.** Step 1 (list) and step 2 (sort) done. Steps 3 to 7 wait on the operator's git route below. Nothing was deleted from PK at this close. **Do not delete any path before `git ls-files`/`git cat-file -e` prints it on `origin/main` (P4 step 4).**

Sort (the folder is `claude/pin/`):

| PK path | Action | Class | Note |
|---|---|---|---|
| MR_PIN3_close_inputs.md | ADDED | KEEP | |
| MR_PIN4_session_prompt.md | ADDED | KEEP | |
| TRACKER.md | REPLACED | KEEP | standing, replaced in place |
| to_engine_LATEST.md | REPLACED | KEEP | standing relay note |
| b2_backfill_check_result_2026-11-25.md | ADDED | KEEP | |
| v2_rule_conformance_prereg_FROZEN_2026-11-25.md, v2_rule_conformance_addendum_v12_FROZEN_2026-11-25.md, v2_rule_conformance_result_v12_2026-11-25.md | KEPT | KEEP | the rule check the comparison builds on |
| pin_monitor_prereg_FROZEN_2026-11-24.md, pin_monitor_build_record_2026-11-24.md | KEPT | KEEP | the monitor is running |
| ruling_shadow_dropped_2026-11-23.md, ruling_pin_definition_2026-11-21.md | KEPT | KEEP | rulings of this and the previous session |
| v2_rule_conformance_result_2026-11-25.md | KEPT | GO once in git | v1.1 result, superseded by v1.2 |
| order_check_rev3_prereg_FROZEN_2026-11-23.md | KEPT | GO once in git | executed; PASS recorded above |
| MR_PIN3_session_prompt.md | KEPT | GO once in git | replaced by the MR-PIN4 prompt |
| MR_PIN2_close_inputs.md | KEPT | GO once in git | previous close; its open items are carried in section 6 |
| gamma_pipeline_audit_prereg_FROZEN_2026-11-22.md, gamma_pipeline_audit_result_2026-11-22.md, pin_vs_followup_result_2026-11-22.md, pin_live_replay_prereg_v2_FROZEN_2026-11-21.md, pin_live_replay_v2_result_2026-11-21.md, pin_behaviour_study_v5_FROZEN_2026-11-21.md, pin_behaviour_v5_result_2026-11-21.md, gamma_rate_sensitivity_result_2026-11-20.md, ruling_D5a_reopen_2026-11-20.md | KEPT | GO once in git | PIN2-era results nothing reads now |
| pin_fix_scope_DRAFT_2026-11-21.md, 2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql | KEPT | GO once in git | the proposal is built and applied; shadow dropped |

**Git route (the pin lane's records go on a branch off `main`; merging to `main` is the operator's call, P8):**
- The pin lane packed one zip for the operator in this chat: `pin3_records_2026-11-25.zip`, laid out under `docs/research/pin_proof/`. It holds this close's new and replaced PK files, the five PK-only PIN3 files, and the files that exist only in the pin lane's workspace (`v2_check_v12/`, the B2 files, `advisor_pack_flip_2026-11-25.md`), with a `MANIFEST_SHA256SUMS`.
- The operator commits it from Windows PowerShell on a new worktree and pushes branch `pin/records-pin3`, merges it, then runs the box check: for every PK path above, `git cat-file -e origin/main:docs/research/pin_proof/<name>` prints IN or MISSING. The pin lane deletes only the GO paths that print IN (step 5), runs `project_info` (step 6) and rewrites this section with the final size (step 7).
- How the zip's copies were made: the files written in this chat (this close's five, and the v1.2 files) are byte-equal to PK (PK's version token equals the file's sha256). The five PK-only PIN3 files (`ruling_shadow_dropped_2026-11-23.md`, `order_check_rev3_prereg_FROZEN_2026-11-23.md`, `pin_monitor_prereg_FROZEN_2026-11-24.md`, `pin_monitor_build_record_2026-11-24.md`, `v2_rule_conformance_result_2026-11-25.md`) were exported by reading them from PK and writing them twice independently; the two copies are identical, and the v1.1 result also matches its recorded sha256 `ec16f43e...5ce3`. PK shows no hash for a file, so equality of the other four with the PK text is not machine-verified. The frozen files in PK were not rewritten.
- Root `.gitignore` drops `*.log`, `*.csv`, `*.txt` (TD-PIN2-NEW-13); a scoped negation under `docs/research/pin_proof/` was committed in MR-PIN2. The route checks the staged count against the manifest before committing.

Carried (not in git, still in PK): every path above until the check prints IN. Reason: the git route is the operator's action after this close. Clears at the MR-PIN4 open or when the operator pastes the check output.
Requests to other lanes (also in STREAMS.md section 3): none new beyond intake rows 2 and 10.

## 8. Things I got wrong in MR-PIN3 (so they are not repeated)

- Said the Board Flip is free of the vendor-gamma problem; it filters on vendor gamma, so it inherits the gap. Corrected in the advisor pack.
- Predicted `pg_get_viewdef` plain form would give the pretty-form value; the engine's read showed otherwise.
- Recommended a legacy block on the old map (option B); the advisor showed the mixed-row defect; withdrew it and backed D.
- Told the operator wall movement would be measured; walls and max pain are OI-only.
- Sent the operator to Lovable's publish panel for the version check without reading the Deployment Topology; the live Board is built on the box (staging, then promote). First marker grep covered only `index-*.js`; the Tape chunk is lazy.
- Gave a commit sequence that referred the operator to another note; he ran it in the wrong folder (`C:\Users\balan`). Give the whole sequence in one message. A stray folder `C:\Users\balan\docs\research\pin_proof\v2_check` remains; remove with `Remove-Item -Recurse $HOME\docs\research\pin_proof\v2_check`.
- Wrote "owed to you" the wrong way round in the V-2 result note.
- The note carrying the ADR edits and wrapper check 4f never reached the engine; moved into the standing PK note.
- Planned the old-against-new comparison before any table existed; the operator's question ("if we are backfilling and comparing then why shadow?") showed that was over-cautious.
- Passed the engine's code at `a9b38bc`, then the engine changed it (package r4); re-ran the frozen comparison at `2574709`. Re-run the frozen check after every code change, not only at the first pass.
- Let the SQL editor's 100-row cap truncate a verification read; set read sizes under 100 rows from the start.

## 9. Binding rules (carry unchanged)

- "Don't guess, answer only if sure." Disagree where the evidence does. Read docs before asking the operator to check anything; if not in PK, the repo holds it.
- Claude Code's `❯ ...` suggested-prompt lines are not the operator's decision.
- Operator-only first. Pre-registration before the first outcome query; one look; nothing altered after test data is seen. Rule 0: a check must be able to fail for the reason it names; units on every figure; denominators on every count.
- No secrets in chat, repo or logs. Reads on the box through `bin/roq.sh` as `merdian_ro`; the `fyers_loader` login is never used; grants and policies are the operator's action in the SQL editor; Claude does not run SQL on production. One CC session per tree; no box analysis 08:30-15:40 IST Mon-Fri; every run under `ulimit -v`; `python3 -B`, no `.pyc` in a sealed folder. One action per command; confirm exactly one runner. `~/meridian-engine` holds `.env` and is never touched; never print bundle or `/var/www` file content.
- Query discipline: catalog first; plain EXPLAIN gate; one symbol-day per query; 5 s sleeps; stop at first error or any query over 10 s; reads under 100 rows per statement.
- Every CC prompt carries its conditions inside it, exact text. At a CC permission screen the operator answers with the bare option number plus the pin lane's explanation; never "allow access", "don't ask again" or "auto mode".
- The operator wants exact numbered steps and commands, and complete self-contained messages: no "fetch from the other note", no jumping ahead of an approval. He needs one overall tracker (`TRACKER.md`) and fewer relays between lanes.
- Session close is when the operator says so; no reminders. Never mention sleep or rest; never suggest pausing or ending.
- PK (binding, `claude/MERDIAN_PK_Protocol_v1.md`): lane=pin; write only in `claude/pin/`; replace in place; no reference-product name (write "the parity target").
