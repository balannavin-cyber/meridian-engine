# Pin behaviour study: how does each pin definition behave across the option history? v5 (FROZEN 2026-11-21, MR-PIN2 step 4)

**Lane:** engine (Board pin). **Status:** FROZEN on the operator's ruling "B" (2026-11-21 07:34 IST), by sha256 recorded outside this file. A later change is a new version with its own hash.
**Supersedes:** v4 (sha256 69ca9686…1338), under which only Step 0 ran. Step 0's result stands and is the basis of the changes: `pin_behaviour_step0_result_2026-11-21.md`.
**Rests on:** Stage 1 of `pin_proof_prereg_DRAFT_2026-11-19.md`; `ruling_D5a_reopen_2026-11-20.md`; `gamma_rate_sensitivity_result_2026-11-20.md`; `engine_note_pin_basis_and_vendor_greeks_2026-11-18.md`.
**Authorises nothing for the Board or production.** Read-only. Nothing is written to the database.

## 0. What changed from v4, and why

1. **Gamma.** Step 0 (0d) found the textbook pin on NIFTY is the same strike under the v4 gamma and the stored OTM-leg gamma on 33 of 36 minutes (91.7 %, under the 95 % bar). The detail check (`lookback_v4/out/_0d_detail.log`, sha256 23562cd2…2d59) showed 11 disagreeing minutes across both symbols and both rules: 6 are near-ties (lead under 5 %), 5 are not (leads 5.9 % to 21.4 %) and come from the two gammas having different shapes across strikes. The v4 gamma uses one volatility for all strikes. **Operator ruling B: the primary gamma is per-strike (each strike's own volatility); the one-volatility gamma is kept as a second column and the disagreement between them is itself measured (M9).**
2. **Window.** Option bars exist contiguously from 2025-04-01 to 2026-03-30 only: 247 sessions per symbol. The study runs on those. Three stray days in May 2026 are left out. The case days 2026-11-18 and 2026-11-19 are not in this history.
3. **Walls.** The Board's rule was read from source (`sql/2026-09-15_s79_v_gex_strike_walls.sql`): raw-OI argmax inside a ±1.5σ band. It replaces the v4 fallback.
4. **M7** now covers every session (the whole window is before the old cut-off). **No holdout remains** in this history for the parked predictive test (§9).

## 1. Question (the operator's)

The Board pin was built when only a few weeks of data existed. It does not match its own definition: the manual says "largest share of gross gamma", the code ranks on the absolute value of the net, and blank or mismatched vendor gamma is magnified by the netting. **Build each pin definition correctly on the twelve months of 1-minute option history and describe how it behaves, by the same route for each.** The output is what to expect from each pin on a normal day and the basis for the operator to pick one. A description: no pass or fail. Measures are fixed here before the run.

## 2. Pins (per run; ties: nearer to spot, then lower strike)

With g_K one gamma per strike (§3), C_K and P_K call and put OI, S spot:
- **T, textbook pin:** argmax g_K·(C_K + P_K).
- **PW1, PW2, pressure pin:** argmax g_K·(C_K + P_K)·exp(−(K − S)² / (2·(w·σ_rem)²)), w = 1.0 and 0.5 (D-5a terms 1 and 2; MERIDIAN's own construction).
- **N, the Board's rule on clean inputs (reference):** argmax g_K·|C_K − P_K|.
- **ATM (reference line):** S rounded to the strike grid.
- **Score** = the quantity inside the argmax. **Lead** = (top − second) / top.
- **Walls (the Board's rule, reconstructed):** among strikes with |K − S| <= 1.5·σ_wall, call wall = the strike with the largest call OI (> 0), put wall = the largest put OI (> 0). σ_wall = S·σ_atm·√(max(dte_cal, 1)/252), dte_cal = calendar days from trade date to expiry. The view has no tie-break; the study uses nearer to spot, then lower strike. The band parameter is read from the database if readable (default 1.5). Differences from the live Board: the Board uses the vendor's ATM IV; the study uses σ_atm from §3.

## 3. Data and gamma

- `hist_option_bars_1m` (bar close, oi), `hist_spot_bars_1m` (spot). `bar_ts` is IST clock time labelled UTC at :59; read as IST, never converted.
- **Window:** sessions with option bars from 2025-04-01 to 2026-03-30 (247 per symbol by Step 0). Symbols never pooled.
- **Runs:** every 15 minutes from 09:30 to 15:15 IST (24 per session), at the exact bar; a minute with no bar is absent and counted.
- **Front expiry:** the smallest expiry_date on or after the trade date at that minute (expiry day included).
- **Strike set:** front-expiry strikes with |K/S − 1| <= 0.05 and oi > 0 on at least one leg.
- **T (time):** calendar minutes from the run to 15:30 IST on expiry day, over 525,600.
- **σ_atm (one per run):** the volatility that prices the ATM straddle (call close + put close at the strike nearest S; Black-Scholes, forward = S, r = 0; bisection on σ in [0.01, 5.0] to 1e-6). If that strike lacks either price, the next nearest strike with both; counted. σ_rem = S·σ_atm·√T.
- **F (forward, one per run):** the median of K + C_close − P_close over the three strikes nearest S that have both closes > 0. No rate is assumed.
- **Primary gamma, per strike (g_K):** σ_K = the Black-76 implied volatility of the strike's out-of-the-money leg against F (K >= F the call, K < F the put), from its bar close, r = 0, same bisection. g_K = φ(d1) / (F·σ_K·√T), d1 = [ln(F/K) + σ_K²·T/2] / (σ_K·√T). Used for both legs. **Fallback:** if the OTM leg has no close > 0 or the solve finds no bracket, σ_K = σ_atm for that strike; fallbacks are counted per run and reported.
- **Second gamma, one volatility (g_K^flat):** as v4: φ(d1) / (S·σ_atm·√T) with forward = S. Every pin is also computed under it.
- Computed inside the study. This is the same repair a production fix would make (one volatility per strike from the OTM leg, forward from the market); the study does not build that fix.
- **DTE buckets, in sessions:** 0 (expiry day), 1, 2, 3+. Strike step: NIFTY 50, SENSEX 100.

## 4. Preconditions for the data pull (Prompt B)

- Session list taken from Step 0's measured output, not written by hand.
- EXPLAIN-gated, one symbol-day per query, sleeps, stop at first gate failure, error or query over 10 s, no retry. Each query also returns, per run minute, the count of legs in the band computed in SQL; the analysis asserts the legs received equal that count (so a row cap cannot pass silently).
- Rule 25 check of `v_gex_strike_walls` (catalog read) and the `wall.band` parameters: reported; "not verified" is a stated result, not a stop.

## 5. Measures (Prompt C, disk only). Per symbol, per pin, per DTE bucket; median, p10, p90 or shares; denominators on every count

- **M1, where it sits.** Signed and absolute distance from spot in strike steps and in σ_rem. Share within 1 step of spot. Share where the pin is the ATM strike.
- **M2, walls.** Share of runs with the pin outside [put wall, call wall]; share where it equals a wall; share of runs with spot outside the corridor (context).
- **M3, changes.** Changes per session. Hold length in runs. Share of changes made on a lead under 5 % at the run before the change. Share of there-and-back changes (A to B to A within 3 runs).
- **M4, following spot.** Over 60-minute windows in which the ATM strike moved 2 steps or more: share where the pin moved the same way by at least 1 step, stayed, or moved the other way.
- **M5, sign.** Share of runs where the pin's own strike has g_K·(C_K − P_K) below zero.
- **M6, concentration.** Pin score as a share of the total; lead over the second strike; share of runs with lead under 5 %.
- **M7, closing in on the settle strike.** Distance in steps from the pin to the strike nearest the last spot bar's close on expiry day, by DTE bucket and, on expiry day, by hour; the same line for ATM beside it.
- **M8, agreement between pins.** Pairwise share of runs where two pins are the same strike.
- **M9, dependence on the gamma.** Share of runs where a pin under the per-strike gamma differs from the same pin under the one-volatility gamma, with the size in steps, split by lead (under 5 %, 5 % and over). Fallback counts.
- All of M1 to M8 are reported under the primary gamma; M1, M3 and M6 are repeated under the second gamma.

## 6. Expected, written now so it can be wrong

- T sits within one step of spot on most runs at DTE 0-1 and drifts to an OI-heavy strike at 3+.
- N sits furthest from spot, follows spot least, and is negative-gamma on a fifth or more of runs.
- PW2 is the ATM strike on most runs; PW1 sits between T and ATM.
- Changes on thin leads are common for every pin.
- M9: T differs between the two gammas on 5-10 % of runs, mostly at 3+ DTE.

## 7. What this cannot say

- Whether any pin tells the reader more than spot does (§9).
- Dealer side: every definition uses OI, not inventory (P2: regime-dependent).
- Anything after 2026-03-30, including the observed days of November 2026.
- Thin strikes: an OTM bar close can be an old print; it enters that strike's own σ_K. The fallback count and M9 bound the effect.
- The live Board's past readings (vendor gamma; stored from 2026-05-25 only).

## 8. What a result authorises

The operator picks a definition (or none). Any Board change is a separate proposal and ruling. The production gamma fix stays step 4 of the MR-PIN1 order.

## 9. Parked: does the chosen pin carry information?

To be pre-registered separately on the pin the operator picks: existence (do expiry-day closes sit nearer a strike than other days); settle (pin against the ATM strike); drift (signed move toward the pin, with a trend split). **This history has no sessions left for a holdout.** A later test needs either new option history after 2026-03-30 (a backfill is a production write and needs its own ruling) or the live `gex_strike_snapshots` OI from 2026-05-25 (not examined for this purpose). P1c (regime to realised range) stays a separate pre-registration after the pin.

## 10. Who runs what

Claude Code on the engine box, writing only under `~/meridian-cc/docs/research/pin_proof/lookback_v5/`; no git writes in that tree (shared with the e1-e3-e10 session); read-only through `bin/roq.sh` as `merdian_ro`; `ulimit -v 700000`; `python3 -B`; outside 08:30-15:40 IST on trading days. **Prompt B:** the data pull (about 494 symbol-day queries, run detached; about two hours). **Prompt C:** the measures, disk only, after the pull's finish line.
