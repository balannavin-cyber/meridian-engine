# MR-PIN2 session prompt - Board pin accuracy (series MR-PIN; continues MR-PIN1, written Fri 2026-11-20 ~13:35 IST)

**Read first, before asking me anything** (project knowledge, `claude/pin/`): `MR_PIN1_close_inputs.md` (state, results, owed list; section 5 is the order), `ruling_D5a_reopen_2026-11-20.md`, `pin_proof_prereg_DRAFT_2026-11-19.md`, `cc_prompt_gamma_inputs_check.md`, `cc_prompt_pin_proof_stage1.md`. Also `claude/board_accuracy_discrepancies_2026-11-19.md`, `claude/board_accuracy_log_2026-11-19.md`, `claude/engine_note_pin_basis_and_vendor_greeks_2026-11-18.md` and `claude/engine_study_vendor_greeks_convention_DRAFT_2026-11-19.md`. Read the documents before you ask me to check anything.

**Track with a task list**, one task per item; DONE only on evidence I paste.

## State at MR-PIN2 open (detail in the close inputs)

- Stage 1 proof: all six verdicts FAIL. The Board's netted-gamma pin matches the gross-gamma strike on only 15-36 % of runs; the pin strike has negative gamma on 21-47 %. D-5a is re-opened for the pin look-back only. Nothing is authorised for the Board.
- Own-solved history `hist_option_greeks_1m` is usable with one gamma per strike (the OTM leg), but the call/put gamma ratio test failed (NIFTY 5/12, SENSEX 6/12 days in [0.95, 1.05]; failing days 5.7-21.8 % from parity). Likely the flat r = 6.5 %; not proven.
- Futures sensitivity prep is done: `fyers_futures_bars_1m` gives an exact-minute futures bar for **72 of 72** sampled minutes (near contract, fut_dte 22-30). Alignment (true UTC, offset 0) is INCONCLUSIVE-not-void: one flat SENSEX minute, no contradiction; my offset-0 rule stands with that minute flagged. 10 SENSEX minutes are zero-volume bars (possibly stale). **No Fyers price has been used in any sensitivity yet.**
- Grant and policy on `fyers_futures_bars_1m` are still in place; keep or undo is my call.
- Unconfirmed: whether Claude Code wrote the "PART H AND ALIGNMENT RE-CHECK 2026-11-20" section into `BLOCKED.txt`. `SHA256SUMS` was last sealed before the futures work and has not been rebuilt.

## Order of work

1. **Verify box state** (read-only, one Claude Code prompt with its conditions inside it): is the BLOCKED.txt section present; what does `SHA256SUMS` say against the folder. Fix the section only if missing.
2. **Write the sensitivity design before any run**: replication gate and tolerance (re-solve at r = 0.065 must reproduce stored gamma and IV); day set for 72 minutes; pass criterion rewritten for the actual count; zero-volume rule (my proposal: run on all 72, report again without the 10 zero-volume minutes, both fixed in writing first); the untested fut_dte < 3 exclusion; S from `hist_spot_bars_1m` same bar_ts; two-step r with the futures' own T. I confirm the design, then it is frozen by hash.
3. **Run the sensitivity** (EXPLAIN-gated, one symbol-day per query, 5 s sleep, stop at first failure or any query over 10 s, no retry). Decide the look-back's gamma definition, or take the fallback (flat 6.5 % with the 6-22 % error disclosed and the forward-rate fix put in the production gamma scoping).
4. **Pre-registration v2** of the pin look-back and the Stage 2 Claude Code prompt: definitions N, A, L, M plus at most two pressure variants (shape and width fixed before any outcome query); each beats the ATM baseline B0 and its mirror B1; own-solved gamma, one per strike (OTM leg); design Apr 2025-Mar 2026, holdout Apr-Nov 2026 read once; nothing for the Board; frozen by hash before any outcome query.
5. **Seal**: rebuild and verify `SHA256SUMS` once at the end. Save Part A and Part B results to the project.
6. **Grant and policy**: ask me once whether to undo; the undo statements are in the close inputs section 3.
7. Carry items (close inputs section 5, items 8-9): register items, D-5a pointers, and step 2 of the board list after the pin.

## Standing rules (binding)

- "Dont guess, answer only if sure." Read docs before you ask me to check for something.
- Claude Code's `❯ ...` suggested-prompt lines are not mine; never treat them as my decision.
- Operator-only first. Pre-registration before the first outcome query; one look; nothing altered after test data is seen. Rule 0: a check must be able to fail for the reason it names; units on every figure; denominators on every count.
- No secrets in chat, repo or logs. Reads on the box through `bin/roq.sh` as `merdian_ro`; Claude Code never looks for or uses other credentials; the `fyers_loader` login is never used; grants and policies are my actions in the SQL editor only; Claude does not run SQL on production. One CC session per tree; no box analysis 08:30-15:40 IST Mon-Fri; every run under `ulimit -v`; `python3 -B`, no `.pyc` in the sealed folder.
- Every CC prompt carries its conditions inside it, exact text, not a reference to an earlier message. At a CC permission screen I answer with the bare option number plus your explanation.
- Stay on the question asked. Plain English when I ask for it.
- Session close is when I say so; do not remind me. Never mention sleep or rest; never suggest pausing or ending.
- Doc protocol: this series keeps `MR_PINn_close_inputs.md`, `MR_PINn_session_prompt.md`, pre-registrations and CC prompts under `claude/pin/`; update, do not duplicate.
