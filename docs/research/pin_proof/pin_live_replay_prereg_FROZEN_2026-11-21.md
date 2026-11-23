<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_live_replay_prereg_FROZEN_2026-11-21.md -->
# Pin live replay: design (FROZEN), 2026-11-21

Session MR-PIN2. Lane: pin. Written before any query in it is run. Approved as written by the operator 2026-11-21 17:57 IST and frozen by sha256 (recorded in the CC prompt and the result); any later change is a new version. Read-only; authorises nothing for the Board or production.

Basis: `ruling_pin_definition_2026-11-21.md`, `pin_fix_scope_DRAFT_2026-11-21.md`, box `fix/stage0_code_read.md` (sha256 008e90a0…2c611), `engine_note_pin_basis_and_vendor_greeks_2026-11-18.md`, `board_accuracy_discrepancies_2026-11-19.md`.

## 1. Questions

- Q1. On the days the Board pin was seen to misbehave, where does the textbook pin sit, computed from the live chain the Board itself used?
- Q2. Which construction is enough for the fix: gross ranking on the vendor's stored gammas, a flat own gamma, or the per-strike own gamma?
- Q3. How often does the textbook pin change on live data, and how many of those changes fall on frozen-OI runs?

## 2. Data

- Days: 2026-11-16, 11-17, 11-18, 11-19. NIFTY and SENSEX separately, never pooled. Every front-expiry run of each day (Part A counted 87, 78, 87, 87 per symbol).
- Runs: `gamma_metrics` (one row per front-expiry `run_id`) joined to `option_chain_snapshots` on `run_id` and `expiry_date`, as in Part A.
- Per leg: `strike`, `option_type`, `ltp`, `oi`, `gamma` (vendor), `spot`, `ts`. Spot of a run = first positive per-leg `spot`, as production takes it.
- Strike set: |K/S − 1| ≤ 0.05 with `oi > 0` on at least one leg (same as the v5 study), for every construction.
- Board pin per run: `gex_cycle_history.pin_leader_strike` for the same `run_id`.
- Walls per run, in this order of preference, decided by reading the catalog before any data: (i) wall columns stored in `gex_cycle_history`, if it has them; (ii) the Board's rule recomputed with `volatility_snapshots.atm_iv_avg` for that run; (iii) the Board's rule with the study's straddle volatility. The one used is stated in the result.
- Time to expiry: minutes from the run's `ts` (IST clock) to 15:30 IST on the expiry date, ÷ 525,600. A run with T ≤ 0 gets no pin and is counted.

## 3. Constructions (pin = highest score; ties: nearer to spot, then lower strike)

| Name | Score per strike |
|---|---|
| B | the Board's stored pin (not recomputed) |
| V2 | vendor γ_call·OI_call + vendor γ_put·OI_put (a blank vendor gamma counts as zero; this is what a view on the stored columns would give) |
| V1 | one vendor gamma per strike × (OI_call + OI_put); the gamma is the out-of-the-money leg's, or the other leg's if that is zero; a strike with both zero scores zero |
| F | flat own gamma × (OI_call + OI_put), as `g_flat` in the v5 study |
| K | per-strike own gamma × (OI_call + OI_put), as `g` in the v5 study (the ruled construction) |

F and K come from `lookback_v5/analyze_v5.py` `compute_run`, imported unchanged (sha256 of the file recorded). Its `self_tests()` must return all-pass on the box before any data is read; otherwise stop.

## 4. Measures (every figure with its n; per symbol and per symbol-day)

- M-a. For B, V2, V1, F, K: median |pin − S| in strike steps; share of runs with pin = at-the-money strike; share of wall-defined runs with the pin outside [put wall, call wall]; number of pin changes per day; number of distinct pin strikes per day.
- M-b. Agreement with K: share of runs on the same strike for V2, V1 and F, over all runs and split by K's lead (< 5 %, ≥ 5 %; lead = (top − second) ÷ top, as in the study). Where they differ: median difference in steps.
- M-c. The two observed episodes, stated plainly: NIFTY 2026-11-18 (B held 25,500 while spot fell): the strikes K took and its median distance from spot against B's. SENSEX 2026-11-19 (expiry day): share of runs outside the corridor for B and for K.
- M-d. Frozen runs: a run is frozen if its total call OI and total put OI over the whole front-expiry chain both equal those of the day's first run at or after 09:15 IST, and it is not that run. Count per symbol-day. For K: share of pin changes where the run before or after the change is frozen.
- M-e. Data quality: runs with no Board pin row, runs invalid in `compute_run` by reason, fallback strikes, runs with T ≤ 0, legs with `oi > 0` and `ltp ≤ 0`.

## 5. Decision rule, fixed now

- "V2 is enough" if, on each symbol separately, V2 = K on at least 95 % of runs where K's lead is ≥ 5 % and on at least 85 % of all valid runs. The same test, separately, for V1 and for F.
- If V2 passes: the fix can be a gross-ranking view on stored columns, with no new job. If only V1 passes: a view that takes one gamma per strike. If only F passes: a small job with the flat solve. If none passes: the per-strike job as scoped.
- If more than one passes, the simplest in the order V2, V1, F is preferred.
- Q1 and Q3 have no pass mark; they are reported.

## 6. What this cannot say

- Four days, one expiry cycle each, both with an expiry day inside; a trend-down day (18 Nov) and a trend-up day (19 Nov). It is a check on the observed days, not a sample of the three months the table holds.
- K is not a truth: agreement with K says a simpler construction reproduces the ruled one, not that either is right.
- Nothing here relates a pin to later price.

## 7. Conduct

Reads only through `bin/roq.sh` as `merdian_ro`; catalog reads first; plain EXPLAIN gate (no Seq Scan, no scan estimate over 20,000) on each query shape; one symbol-day per query, 5 s sleeps, stop at the first failure or any query over 10 s, no retry. Every run under `ulimit -v 700000` with `python3 -B`; one symbol-day in memory at a time. No git write. Output only under `docs/research/pin_proof/fix/replay/`. Not run 08:30–15:40 IST Mon–Fri.
