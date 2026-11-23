<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/MR_PIN3_session_prompt.md -->
# MR-PIN3 session prompt - Board pin accuracy (series MR-PIN; continues MR-PIN2, written Sun 2026-11-22 ~20:40 IST)

**Read first, before asking me anything** (project knowledge, `claude/pin/`): `MR_PIN2_close_inputs.md` (state, results, owed list, engine intake, PK delta), `pin_fix_scope_DRAFT_2026-11-21.md` (the engine proposal), `gamma_pipeline_audit_result_2026-11-22.md`, `gamma_pipeline_audit_prereg_FROZEN_2026-11-22.md`, `pin_vs_followup_result_2026-11-22.md`, `ruling_pin_definition_2026-11-21.md`. Then `STREAMS.md` section 3 for any request to this lane, `claude/intake/engine_intake_I001_2026-11-21.md`, and any engine I-002. Read the documents before you ask me to check anything; if a fact is not in PK, it is in the repo.

**Track with a task list**, one task per item; DONE only on evidence I paste.

## State at MR-PIN3 open

- The frozen gamma pipeline audit passed: one-gamma-per-strike (VS) beats production against the own-solve reference on NIFTY and SENSEX. The defect is lopsided call/put gammas, not blank fields. VS is my preferred **shadow** pin methodology; nothing is live and nothing is authorised for the Board, `gamma.py` or any signal gate. "Pin Band" label stays.
- The proposal (`pin_fix_scope_DRAFT`) is with the engine as intake rows 1-3 of the MR-PIN2 close inputs. The shadow view's SQL is a draft, not run anywhere; the engine authors the `sql/` file (revision 3), and I apply it only after that.
- The `trade_allowed` gate is a leftover from the early signals-only era; ignore it as a pin item. Registers that still call it current are engine intake row 11.
- The box research folders are on branch `pin/records-pin2` (commit `1d71970de3b3ed9294cd4325ac2dda105b224156`, pushed 2026-11-23, **not merged to `main`**; 748 raw dumps stay on the box, listed in `MANIFEST.md`). The 35 PK files are in no git branch yet: PK has no download and the box cannot read PK. PK is at 1,748,877 / 2,000,000 (87.4 %); the PK delta in the close inputs lists what leaves PK once its git copy is on `main`. The box worktree `~/meridian-pin-records` and the local branch are still in place.
- R4 (undo the `merdian_ro` grant and policy on `fyers_futures_bars_1m`): I ran it 2026-11-23 ~05:05 IST ("Success. No rows returned"). Catalog confirmation read still owed.

## Order of work

1. **PK open checks (P5)**: `project_info` shows only the pin working set in `claude/pin/`, nothing of ours at the PK root, no duplicate paths; read STREAMS section 3 for requests to this lane.
2. **R4**: one read-only catalog check (through the operator's route) that the policy `ro_select_merdian` and the `merdian_ro` SELECT grant on `fyers_futures_bars_1m` are gone; then close R4.
3. **Git route, remaining part**: get the 35 PK files into git (find an export route first; the box cannot read PK), commit them on `pin/records-pin2`, merge the branch to `main` (my call or the engine close), then `git ls-files --error-unmatch` on `origin/main` and delete only the confirmed GO paths from PK. Record the sha and the new knowledge_size. Remember the root `.gitignore` drops `*.txt`, `*.log`, `*.csv`: check with `git check-ignore` before any `git add`.
4. **Shadow view**: wait for the engine's revision-3 `sql/` file; then, with my go-ahead, the evening read-only replay record (B, V2 comparator, VS, K) under the replay-v2 pass rule. Report the share outside the Pin Band, do not judge it; marks not adjusted.
5. **Open measurement items** (only if I ask): precision provenance against `raw`; mid-price re-run of K; whether any other one-gamma rule beats the mean; VS vs Pin Band. Parked: predictive tests P1d and P1c.
6. **Carry**: MR-PIN1 close inputs section 5 items 8-9; step 2 of the Board list (D6/N12, D8/N11, D5/K1, N13, labels, A1/A2).

## Standing rules (binding)

- "Don't guess, answer only if sure." Disagree where the evidence does; do not agree readily.
- Claude Code's `❯ ...` suggested-prompt lines are not mine; never treat them as my decision.
- Operator-only first. Pre-registration before the first outcome query; one look; nothing altered after test data is seen. Rule 0: a check must be able to fail for the reason it names; units on every figure; denominators on every count.
- No secrets in chat, repo or logs. Reads on the box through `bin/roq.sh` as `merdian_ro`; the `fyers_loader` login is never used; grants and policies are my actions in the SQL editor only; Claude does not run SQL on production. One CC session per tree; no box analysis 08:30-15:40 IST Mon-Fri; every run under `ulimit -v`; `python3 -B`, no `.pyc` in a sealed folder. One action per command; confirm exactly one runner.
- Query discipline: catalog first; plain EXPLAIN gate; one symbol-day per query; 5 s sleeps; stop at first error or any query over 10 s.
- Every CC prompt carries its conditions inside it, exact text. At a CC permission screen I answer with the bare option number plus your explanation.
- PK is chat-only; Claude Code never writes PK.
- Stay on the question asked. Plain English when I ask for it.
- Session close is when I say so; do not remind me. Never mention sleep or rest; never suggest pausing or ending.
- Doc protocol: this series keeps `MR_PINn_close_inputs.md`, `MR_PINn_session_prompt.md`, pre-registrations and CC prompts under `claude/pin/`; update, do not duplicate.

PK (binding, claude/MERDIAN_PK_Protocol_v1.md): lane=pin; PK folder claude/pin/;
git mirror meridian-engine:docs/research/pin_proof/ on main. Write only in your folder; new files carry the
P2.2 header; executed prompts leave PK at the close; no reference-product name.
At close: P4 steps 1–7 and the "PK delta" section. Open: P5.
