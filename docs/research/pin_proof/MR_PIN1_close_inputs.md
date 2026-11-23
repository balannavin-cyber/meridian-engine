# MR-PIN1 close inputs (written Fri 2026-11-20 ~13:35 IST on the operator's "EOS document"; series MR-PIN = Board pin accuracy, step 1 of the 19 Nov board-accuracy discrepancy list; next session MR-PIN2)

MR-PIN1 ran Thu 2026-11-19 to Fri 2026-11-20 ~13:35 IST. Read with: `board_accuracy_discrepancies_2026-11-19.md`, `board_accuracy_log_2026-11-19.md`, `pin_proof_prereg_DRAFT_2026-11-19.md`, `cc_prompt_pin_proof_stage1.md`, `ruling_D5a_reopen_2026-11-20.md`, `cc_prompt_gamma_inputs_check.md`, `engine_note_pin_basis_and_vendor_greeks_2026-11-18.md`, `engine_study_vendor_greeks_convention_DRAFT_2026-11-19.md`. Figures below were printed by Claude Code or pasted by the operator. Part A and Part B result texts live in the repo (box, `docs/research/pin_proof/gamma_inputs/`); they were NOT copied into the project this session (owed, section 5).

**Nothing is authorised for the Board. No engine code changed. No production change was made by this session except the operator's own grant and policy on `fyers_futures_bars_1m` (section 3).** No ADR/TD/ENH ID was minted by the advisor in this session.

## 1. Results this session

| Item | Result | Where |
|---|---|---|
| Pin proof, Stage 1 | All six verdicts FAIL. The Board's netted-gamma pin matches the gross-gamma strike on only 15-36 % of runs; the pin strike has negative gamma on 21-47 % of runs. | `pin_proof_prereg_DRAFT_2026-11-19.md`, box pin_proof folder |
| Ruling D-5a | Re-opened for the pin look-back only (2026-11-20). Nothing for the Board. | `ruling_D5a_reopen_2026-11-20.md` |
| Part A (sealed) | Origin of the blank gamma legs. Compute treats a blank gamma leg as zero (one blank leg per strike). Full text is in the repo folder; not restated here. | box `gamma_inputs/` |
| Part B (sealed) | Own-solved history `hist_option_greeks_1m` is usable **with one gamma per strike (the OTM leg)**. Call/put gamma ratio test FAIL: NIFTY 5 of 12 days and SENSEX 6 of 12 days inside [0.95, 1.05]; failing days are 5.7 % to 21.8 % from parity. Likely cause (not yet proven): flat r = 6.5 %; other candidates are bar closes instead of mids, no intraday time decay, calendar-day T. | box `gamma_inputs/` |
| Futures coverage (this session) | **72 of 72** sampled minutes (24 symbol-days x 10:00, 12:30, 15:00 IST) have a Fyers futures bar at the exact true-UTC instant. Near-month contract every time; fut_dte 22 to 30. F missing 0, unstable (fut_dte < 3) 0, ties 0, next-contract-used 0. | box `_partH_analysis.txt` |
| Zero-volume bars | 10 of 36 SENSEX minutes (7 at 12:30, 2 at 15:00, 1 at 10:00); NIFTY 0. SENSEX volumes at the chosen expiry are small (20 to 200 lots, one 1,060). Several closes are round numbers (80500, 80770, 84400). Interpretation: possibly stale prices; a 0.1 % F error moves implied r about 1.5 points at 25 days to expiry. | same |
| Alignment re-check (two more days) | **ALIGNMENT INCONCLUSIVE, not void**: SENSEX 2026-03-02 10:00 has SENSEX26MARFUT 80880.50 at both offset 0 and +60 (flat print), so offset 0 is not singled out there; F is identical under either. Other five minutes exact and unique at offset 0 to the nearest-expiry contract. NIFTY 2026-03-04: hist series 1, 2, 3 = MAR, APR, MAY one-to-one, 9 of 9, non-matches 101-267 points away. | box `_alignment_v2_recheck.txt` |

## 2. Data and method facts established

- Futures sources for the 24 sampled days: `hist_future_bars_1m` (NIFTY 36/36 minutes, 12/12 days, series 1/2/3, expiry_date NULL on all 104 rows; SENSEX 15/36 minutes on 5/12 days, series 0, expiry present; missing SENSEX days 2025-04-02, 07-02, 08-01, 09-01, 10-03, 11-03, 12-01); `historical_index_futures_1m` starts 2026-03-19 (useless for the window); `hist_basis_context` derived from hist futures, adds no coverage; **`fyers_futures_bars_1m` covers all 24 days** (795,544 rows est.; underlyings NIFTY, SENSEX; Jan/Feb 2025 to Oct 2026; columns underlying, symbol, expiry_date NOT NULL, ts timestamptz, open/high/low/close, volume, oi, source; indexes (underlying, ts) and (underlying, expiry_date, ts)).
- **Fyers ts is true UTC** (session 03:45-09:59 UTC = 09:15-15:29 IST), bars labelled at second :00; `hist_*` tables label the IST clock as +00:00 at :59. Alignment: Fyers instant = IST sampled minute minus 5 h 30 m, offset 0. Verified on NIFTY 2025-04-01, SENSEX 2025-05-02 and re-checked on NIFTY 2026-03-04, SENSEX 2026-03-02 (INCONCLUSIVE on one flat SENSEX minute, no contradiction).
- `fyers_futures_bars_1m` has row-level security enabled (not forced). A grant alone returned zero rows silently; the operator added both a SELECT grant and a policy `ro_select_merdian` on 2026-11-20.
- **FUTURES CONTRACT RULE** (in `BLOCKED.txt`, written before any Fyers price was used): F = close of the Fyers bar at the exact instant, no neighbour fill. CONTRACT = among contracts holding a bar at that instant, smallest expiry_date >= IST trade date (by expiry, not series). Missing F: minute excluded and counted. fut_dte < 3: unstable, excluded and counted. Next contract used: counted, not excluded. Volume reported, zero-volume flagged. T_fut = (expiry_date - IST trade date)/365. r = ln(F/S)/T_fut, S = `hist_spot_bars_1m` close at the same IST-labelled bar_ts. r is a net carry figure (dividends inside).
- Sensitivity method (not yet run): two-step. (1) r = ln(F/S)/T_fut once per minute using the futures' own T. (2) Re-solve the option at T_opt with that r. Using T_opt in step 1 would inflate r about 4x to 23x. **Replication gate first**: the re-solve at r = 0.065 must reproduce the stored gamma and IV on the same legs to a stated tolerance, same spot, before r changes. Report the within-1 %-of-spot call/put gamma ratio median per day before and after against [0.95, 1.05]. Untested alternative: options-implied forward from the ATM pair only (C - P = e^(-rT)(F - K)); must be tested on strikes 1-3 % away, otherwise circular.
- Query discipline used for all box reads: `bin/roq.sh` as `merdian_ro`; EXPLAIN gate (no ANALYZE, `ulimit -v 700000`, fail on any sequential scan or scan estimate over 20,000; literal bounds because CTE bounds give planner defaults); one symbol-day per query, 5 s sleep, stop at first failure or any query over 10 s, no retries.
- Run precondition clause 4 (last log line = ALL 24 DONE) was waived by the operator: the marker went to task stdout, not `_partH_run.log` (loop script bug). Evidence: 24 OK, 0 FAIL, 0 STOP, 2.530-3.049 s, 1,219 raw lines, 12 days per symbol.

## 3. State of the box and operator actions

- Directory: `~/meridian-cc/docs/research/pin_proof/gamma_inputs/`. `SHA256SUMS` was last sealed 49/49 **before** the futures work; it has NOT been rebuilt. Rebuild command used before: `find . -type f ! -name SHA256SUMS | sed 's|^\./||' | sort | xargs sha256sum`. New files since the seal include q09-q14, q13b, qF/qG/qH templates, analyze_partF.py, analyze_partG.py, analyze_partH.py, analyze_alignment.py, analyze_alignment_v2.py, the _q*, _part*, _alignment* outputs (including `_partH_raw.txt`, `_partH_run.log`, `_partH_analysis.txt`, `_alignment_v2_recheck.txt`), the explain plans and `BLOCKED.txt` (edited). No `__pycache__` exists (verified; use `python3 -B`, never `py_compile` in the sealed folder).
- **UNCONFIRMED at close**: the operator was given a prompt to add a section "PART H AND ALIGNMENT RE-CHECK 2026-11-20" to `BLOCKED.txt` (six points: coverage run, coverage result, alignment re-check, operator decision, status, new files). Whether Claude Code wrote it is not known. First action next session: check for that heading by grep (read docs first).
- **Operator decision recorded in that prompt (if sent):** the offset-0 rule stands; SENSEX 2026-03-02 10:00 flagged not independently confirmed; any SENSEX sensitivity result carries the caveat that SENSEX alignment rests on the 2025-05-02 test plus two unambiguous minutes in the re-check.
- Grant and policy on `fyers_futures_bars_1m` (operator action, 2026-11-20, SQL editor) are **still in place**. Undo: `DROP POLICY ro_select_merdian ON public.fyers_futures_bars_1m;` and `REVOKE SELECT ON public.fyers_futures_bars_1m FROM merdian_ro;`. Keeping or undoing is the operator's call after the work; the advisor leaned toward undoing.
- Claude Code runs as the read-only `merdian_ro`; the `fyers_loader` login (full read/write) must never be used; grants/policies are operator actions only; nothing is deleted or changed in production by Claude.

## 4. Operator rulings this session

- Order: (1) origin of blank gamma legs, (2) is own-solved history clean enough, (3) pin look-back pre-registration v2, (4) production gamma fix scoped from 1-2.
- D-5a re-opened for the look-back only; terms in `ruling_D5a_reopen_2026-11-20.md`.
- Futures: grant read on `fyers_futures_bars_1m` "Allow. Take all precautions". Try Fyers futures (1) and keep the flat 6.5 % history with its error disclosed (2) before trying the options-implied forward (3).
- Waived run-precondition clause 4 (section 2). Offset-0 rule stands (section 3).
- Fallback agreed: if the futures sensitivity cannot be run or fails, keep flat-rate gamma with the 6-22 % error disclosed and put the forward-rate fix in the production gamma scoping.

## 5. Owed, in order (for MR-PIN2)

1. Confirm `BLOCKED.txt` section (section 3) and the state of `SHA256SUMS`; read-only grep first.
2. **Write the sensitivity design in writing before any run**: replication gate and tolerance; day set (sized to 72 usable minutes, 36 per symbol; the earlier criterion "in-band days rise to at least 10 of 12 per symbol and no previously in-band day leaves the band" must be rewritten for the actual count); pass criterion; **zero-volume rule (proposed, not yet confirmed by the operator): run on all 72 minutes, report a second time without the 10 zero-volume minutes, both fixed in writing before any price is used**; note the fut_dte < 3 exclusion is untested by this data; S from `hist_spot_bars_1m` same bar_ts; EXPLAIN-gated, one symbol-day per query, 5 s sleep, stop at first failure or 10 s, no retry.
3. Run the sensitivity; decide the look-back's gamma definition from it (or take the fallback).
4. Pre-registration v2 of the pin look-back and the Stage 2 Claude Code prompt: definitions N, A, L, M plus at most two pressure variants (shape and width fixed before any outcome query); each must beat the ATM baseline B0 and its mirror B1; own-solved gamma, one gamma per strike (OTM leg); design Apr 2025-Mar 2026, holdout Apr-Nov 2026 read once; nothing authorised for the Board; frozen by hash before any outcome query.
5. Rebuild and verify `SHA256SUMS` once at the end; save inline analysis as files.
6. Operator decision: keep or undo the grant and policy.
7. Save Part A and Part B results to the project (they live in the repo only).
8. Register/close items to carry: timezone contradiction in `backfill_basis_context.py` (docstring/DDL vs `IST_SHIFT = 0`); unexplained `hist_future_bars_1m` SENSEX 05-06 expiry row; `expected_writes` floor-of-1 (`compute_gamma_metrics_local.py:582`); Rule 25 md5 instability across PG 17; vendor/ingest ticket; D-5a re-open pointers (Enhancement Register ENH-125 block, `docs/research/s89_rulings/pressure_leg_decline_S89.md`, session rulings file).
9. After the pin: step 2 of the board list (D6/N12, D8/N11, D5/K1, N13, labels, A1/A2) and the operator-run SQL still owed.

## 6. Things I got wrong in MR-PIN1 (so they are not repeated)

- Proposed sampled minutes without noting Fyers' true-UTC clock until a visibility query showed first ts 03:45.
- Suggested SENSEX 2025-04-02 for the alignment trial though it has no hist counterpart (2025-05-02 is the right day).
- Wrote a precondition gate against a log file while the loop echoed its marker elsewhere (my loop script); a gate must be checked against where the marker is actually written.
- Suggested rank-pairing for the NIFTY alignment check, which assumes the mapping under test; exact close equality is the better pairing.
- Let a `py_compile` syntax check go toward a sealed folder; it writes a `.pyc`. Use `ast.parse` and `python3 -B`.
- BLOCKED.txt overstatements corrected during the session: "NO usable source", "trips the 20,000-row gate by construction", "re-run reproduces the same output", "measured in q13" for operator-reported RLS state, "360 per contract", "Supabase SQL editor", "only catalog reads".

## 7. Binding rules (carry unchanged)

- "Dont guess, answer only if sure." Read docs before asking the operator to check anything.
- Claude Code's suggested next-prompt lines (the `❯ ...` lines) are not the operator's; never treat them as his decision.
- Operator-only first. Pre-registration before the first outcome query; one look; nothing altered after test data is seen. Rule 0: a check must be able to fail for the reason it names; units on every figure; denominators on every count.
- No secrets in chat, repo or logs. Reads on the box through `bin/roq.sh` as `merdian_ro`; Claude does not run SQL on production. One CC session per tree; no box analysis 08:30-15:40 IST Mon-Fri; every run under `ulimit -v`.
- Every CC prompt carries its conditions inside it (exact text, not a reference to an earlier message). At a CC permission screen the operator answers with the bare option number and a short explanation.
- Session close is when the operator says so; no reminders. Never mention sleep or rest; never suggest pausing or ending.
- Doc protocol: this series keeps `MR_PINn_close_inputs.md`, `MR_PINn_session_prompt.md`, pre-registrations and CC prompts under `claude/pin/`; update, do not duplicate.
