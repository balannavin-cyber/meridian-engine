# Pin behaviour study: how does each pin definition behave across the option history? v4 (FROZEN 2026-11-20, MR-PIN2 step 4)

**Lane:** engine (Board pin). **Status:** FROZEN on the operator's "lets do this" (2026-11-20 18:47 IST), by sha256 recorded outside this file. A later change is a new version with its own hash.
**Supersedes:** the v2 and v3 pre-registration drafts of the same day (neither frozen nor run). v3's predictive tests are parked in §9.
**Rests on:** Stage 1 of `pin_proof_prereg_DRAFT_2026-11-19.md` (all six verdicts FAIL); `ruling_D5a_reopen_2026-11-20.md`; `gamma_rate_sensitivity_result_2026-11-20.md`; `engine_note_pin_basis_and_vendor_greeks_2026-11-18.md`; `board_accuracy_discrepancies_2026-11-19.md`.
**Authorises nothing for the Board or production.** Read-only. Nothing is written to the database.

## 1. Question (the operator's, 2026-11-20)

The Board pin was built when only a few weeks of data existed. It does not match its own definition: the manual says "largest share of gross gamma", the code ranks on the absolute value of the net (calls minus puts), and blank or mismatched vendor gamma is magnified by the netting. Now about 15 months of 1-minute option history exist.

**So: build each pin definition correctly on that history and describe how it behaves, by the same route for each.** The output is what to expect from each pin on a normal day, and the basis for the operator to pick one. This is a description. There is no pass or fail. The measures are fixed here before the run so that nothing is chosen afterwards.

## 2. Pins (per run; ties: nearer to spot, then lower strike)

With g_K one gamma per strike (§3), C_K and P_K call and put OI, S spot:
- **T, textbook pin:** argmax g_K·(C_K + P_K). Absolute gamma, both sides added: the published definition and what the Board manual describes.
- **PW1, PW2, pressure pin:** argmax g_K·(C_K + P_K)·exp(−(K − S)² / (2·(w·σ_rem)²)), w = 1.0 and 0.5. Gamma concentration weighted toward strikes near spot. The parity target's own formula is undisclosed; these are MERIDIAN's construction with two widths, fixed here (D-5a terms 1 and 2).
- **N, the Board's rule on clean inputs (reference):** argmax g_K·|C_K − P_K|. This is the Board's ranking rule with the gamma repaired. It is not a replay of the stored Board pin.
- **ATM (reference line):** S rounded to the strike grid.
- **Score** of a pin = the quantity inside its argmax. **Lead** = (top score − second score) / top score.
- **Walls:** call wall and put wall as the Board defines them; Prompt A reads the view source in `sql/` and reports the rule. If it cannot be read, the study uses: call wall = largest call OI at or above the ATM strike, put wall = largest put OI at or below it, and says so.

## 3. Data and conventions

- `hist_option_bars_1m` (bar close, oi) and `hist_spot_bars_1m` (spot). `bar_ts` is IST clock time labelled UTC at :59; read as IST, never converted.
- **Window:** every session with data from 2025-04-01 to 2026-11-19, both symbols, never pooled.
- **Runs:** every 15 minutes from 09:30 to 15:15 IST where a spot bar exists.
- **Front expiry:** the smallest expiry_date on or after the trade date in the option bars at that minute (expiry day included).
- **Strike set:** front-expiry strikes with |K/S − 1| <= 0.05 and oi > 0 on at least one leg.
- **Gamma, computed inside the study, one per strike, used for both legs:** g_K = φ(d1) / (S·σ·√T), d1 = [ln(S/K) + σ²T/2] / (σ√T), r = 0. σ = the volatility that prices the ATM straddle (call close + put close at the strike nearest S, forward = S; bisection on σ in [0.01, 5.0] to 1e-6). T = calendar minutes from the run to 15:30 IST on expiry day, over 525,600. σ_rem = S·σ·√T.
- **DTE buckets, in sessions:** 0 (expiry day), 1, 2, 3+.
- **Strike step:** confirmed from the data (expected NIFTY 50, SENSEX 100).

## 4. Step 0: checks before the run (Prompt A; no later price is read)

- **0a. Coverage by month, per symbol:** sessions with spot bars; sessions with front-expiry option bars; the expiry dates; whether expiry-day bars exist for the expiring contract; clock time of the last spot bar per session (the 2026-11-07 engine note records a 15:14-15:29 hole).
- **0b. Contamination (Rule 13)** for the two relations.
- **0c. Does stored OI move intraday?** On the 24 sample days already on disk (`gamma_inputs/sens/_qS_*.txt`): total OI at 10:00, 12:30 and 15:00. If it does not move on most days, every pin is a day-level object and the results say so.
- **0d. Gamma robustness** (same 72 minutes on disk, no new query): the strike chosen by T and by N under (i) the in-study gamma, (ii) stored OTM-leg gamma, (iii) stored call-leg gamma, (iv) stored put-leg gamma. Reported as agreement shares with disagreement sizes in steps. If T under (i) and (ii) agree on under 95 % of minutes for a symbol, Prompt B waits for the operator.
- **0e. Wall rule** read from the view source.

## 5. Measures (Prompt B). Per symbol, per pin, per DTE bucket; median, p10, p90 or shares; denominators on every count

- **M1, where it sits.** Signed and absolute distance from spot, in strike steps and in σ_rem. Share of runs within 1 step of spot. Share of runs where the pin is the ATM strike.
- **M2, walls.** Share of runs with the pin outside [put wall, call wall]; share where it equals a wall.
- **M3, changes.** Changes per session. Hold length in runs. Share of changes made on a lead under 5 % at the run before the change. Share of there-and-back changes (A to B to A within 3 runs).
- **M4, following spot.** Over 60-minute windows in which the ATM strike moved 2 steps or more: share where the pin moved the same way by at least 1 step, stayed, or moved the other way.
- **M5, sign.** Share of runs where the pin's own strike has g_K·(C_K − P_K) below zero (the Board would call it amplifying).
- **M6, concentration.** Pin score as a share of the total over the strike set; lead over the second strike.
- **M7, closing in on the settle strike.** Distance in steps from the pin to the strike nearest the last spot bar's close on expiry day, by DTE bucket and, on expiry day, by hour; the same line for ATM beside it. **Sessions up to 2026-03-31 only**, so later sessions stay unread for the parked predictive test (§9).
- **M8, agreement.** Pairwise share of runs where two pins are the same strike.
- **Case days.** 2026-11-18 and 2026-11-19, if covered: each pin by run for both symbols, beside the Board readings recorded in the engine note and the accuracy log.

## 6. Expected, written now so it can be wrong

- T sits within one step of spot on most runs at DTE 0-1 and drifts out to an OI-heavy strike at 3+.
- N sits furthest from spot, is outside the walls least (it tends to be a wall), follows spot least, and is negative-gamma on a fifth or more of runs.
- PW2 is the ATM strike on most runs; PW1 sits between T and ATM.
- Changes on thin leads are common for every pin; fewest for T at short DTE.
- 0d: T agrees across the four gammas on at least 95 % of minutes; N less.

## 7. What this cannot say

- Whether any pin tells the reader more than spot does (parked, §9).
- Dealer side: every definition uses OI, not inventory (P2: regime-dependent).
- The live Board's past readings: its stored pin used vendor gamma and exists only from 2026-05-25.
- Thin strikes: bar closes can be old prints; they enter gamma only through the ATM straddle.

## 8. What a result authorises

The operator picks a definition (or none). Any Board change is a separate proposal and ruling. The production gamma fix (one gamma per strike, blank leg no longer zero) stays step 4 of the MR-PIN1 order.

## 9. Parked: does the chosen pin carry information? (from the withdrawn v3)

To be pre-registered separately, on the pin the operator picks: (a) existence: do expiry-day closes sit nearer a strike than other days; (b) settle: pin against the ATM strike; (c) drift: signed move toward the pin (equivalently, pin against its mirror), with a with-trend and against-trend split; candidates that track spot cannot earn "attracts". Holdout 2026-04-01 onward, read once. P1c (regime to realised range) stays a separate pre-registration after the pin.

## 10. Who runs what

Claude Code on the engine box, writing only under `~/meridian-cc/docs/research/pin_proof/lookback_v4/`; no git writes in that tree (shared with the e1-e3-e10 session); read-only through `bin/roq.sh` as `merdian_ro`; `ulimit -v 700000`; `python3 -B`; outside 08:30-15:40 IST on trading days. EXPLAIN-gated, sleep between queries, stop at first failure or any query over 10 s, no retry. **Prompt A:** Step 0. **Prompt B:** the full run (one symbol-day per query; expect a few hours), only after the operator has read Step 0 and says the box is free.
