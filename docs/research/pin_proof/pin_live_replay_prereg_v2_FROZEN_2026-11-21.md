<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_live_replay_prereg_v2_FROZEN_2026-11-21.md -->
# Pin live replay v2: the whole chain table (FROZEN), 2026-11-21

Session MR-PIN2. Lane: pin. New version of `pin_live_replay_prereg_FROZEN_2026-11-21.md` (v1, sha256 cbad76e1…f91139), which stays as it is with its result. Written before any v2 query is run. Approved as written by the operator 2026-11-21 20:57 IST and frozen by sha256 (recorded in the CC prompt and the result). Read-only; authorises nothing for the Board or production.

## 1. Why a v2

v1 covered four days and passed the vendor view (V2). One added day (2026-11-20) put V2 under a mark on each index, by margins of a few runs. Five days, with runs five minutes apart, cannot rank the constructions. The chain table holds every run since 2026-08-24. v2 runs the same comparison on all of it and looks for what makes a day like 20 Nov differ.

## 2. Questions

- Q1. Across about 60 trading days, how often does each simpler construction land on the ruled pin's strike, day by day?
- Q2. When a simpler construction differs from the ruled pin, which input fault goes with it: the vendor's call/put gamma mismatch, blank vendor legs, the forward, days to expiry, or the time of day?
- Q3. Which construction is enough for the fix?

## 3. Data

- Every weekday from 2026-08-25 to 2026-11-20, NIFTY and SENSEX separately, never pooled across symbols. A weekday with no front-expiry run is counted as empty, not a failure. A symbol-day with fewer than 60 valid market-hours runs is reported and left out of the day counts.
- Runs, legs, spot, Board pin, stored walls, strike set, time to expiry: exactly as v1 (same query template, same scorer).
- Added per run: `volatility_snapshots.atm_iv_avg`, newest row at or before the run's `ts` for the symbol (the rule `v_gex_strike_rank` uses), with its age in minutes.
- The five days already seen (16–20 Nov) are included and marked SEEN. Headline figures and the decision rule use the UNSEEN days only.

## 4. Constructions (pin = highest score; ties: nearer to spot, then lower strike)

| Name | Score per strike | Could be built as |
|---|---|---|
| B | the Board's stored pin | (current) |
| V2 | vendor γ_call·OI_call + vendor γ_put·OI_put, blank = 0 | a view on stored columns |
| VS | one vendor gamma per strike × (OI_call + OI_put); the gamma is the mean of the two legs when both are > 0, the non-zero one when one is blank, zero when both are | a view on stored columns |
| FV | φ(d1) × (OI_call + OI_put), d1 = ln(S/K)/(σ√T) + σ√T/2, σ = stored `atm_iv_avg`/100, T as v1. No vendor per-leg gamma is used | a view on stored columns |
| F | flat own gamma × (OI_call + OI_put), σ solved from the at-the-money straddle (v5 study `g_flat`) | a small job |
| K | per-strike own gamma × (OI_call + OI_put) (v5 study `g`); the ruled construction | the per-strike job |

F and K from `analyze_v5.py` `compute_run`, unchanged (sha256 4958435201740e86acb9791781abe764a4df42d09eefab987e7bcbd805086979); its self-tests must pass first. V2 from `score_replay.py` unchanged. VS and FV are new code: each gets planted-chain self-tests shown before any data is scored (VS: a strike where VS and V2 must differ; FV: the planted chain of the v5 study, where FV must return 25,100; a run with no `atm_iv_avg` gets no FV pin and is counted).

## 5. Measures

Clock segments (IST): pre-open (before 09:15), market (09:15–15:29), post-close (15:30 and after). Every figure with its n.

- M1. Per symbol-day, market runs: for V2, VS, FV, F, the share of runs on K's strike, over runs with K's lead ≥ 5 % and over all valid runs. Then across days, per symbol: median, 10th percentile, minimum, and the number of days meeting both marks (95 % and 85 %), for UNSEEN days and for all days.
- M2. The same shares pooled over all market runs of the UNSEEN days per symbol, and separately for pre-open and post-close runs.
- M3. For B, V2, VS, FV, F, K, market runs, per symbol: median abs(pin − S) in steps; share with pin = at-the-money strike; share outside the stored corridor; median pin changes per day.
- M4. Diagnostics per run, market runs:
  - R = median over strikes within 1 % of spot with both vendor gammas > 0 of (vendor γ_call ÷ vendor γ_put);
  - BL = share of open interest in the strike set sitting on legs with oi > 0 and a blank vendor gamma;
  - FB = (forward − spot) in strike steps, forward as `compute_run` takes it;
  - DTE = calendar days to expiry (0, 1, 2, 3+);
  - IVA = age of `atm_iv_avg` in minutes.
- M5. Agreement with K for V2, VS, FV and F, market runs with K's lead ≥ 5 %, per symbol, split by: abs(ln R) in [0, 0.1), [0.1, 0.3), [0.3, ∞); BL in [0, 2 %), [2 %, 5 %), [5 %, ∞); abs(FB) in [0, 0.5), [0.5, 1), [1, ∞); DTE bucket; IVA in [0, 10), [10, 60), [60, ∞) for FV.
- M6. The ten symbol-days with the lowest V2 agreement (market, lead ≥ 5 %): date, DTE at the open, median R, median BL, median FB, and the agreement of VS, FV and F that day. 2026-11-20 is shown beside them whatever its rank.
- M7. Frozen runs: as v1, but counted only among runs after the reference run. Per symbol: days with any, share of market runs frozen, and the share of K's pin changes next to a frozen run.
- M8. Data quality: empty weekdays, short days, runs with no Board row, invalid runs by reason, runs with no `atm_iv_avg`, fallback strikes, legs with oi > 0 and ltp ≤ 0, runs with ambiguous spot.

## 6. Decision rule, fixed now

On market runs of UNSEEN days, per symbol, a construction is enough if both hold:
1. pooled over those days it is on K's strike on at least 95 % of runs with K's lead ≥ 5 %;
2. on at least 90 % of those days it meets both day marks (95 % of clear-lead runs, 85 % of all valid runs).

It must hold on both symbols. If more than one construction is enough, the first in the order V2, VS, FV, F is taken. If none is, the fix is the per-strike job as scoped. M4–M6 carry no pass mark.

Changes from v1's rule, stated: market runs only (pre-open and post-close reported apart, because prices outside the session are not live); a day-level condition is added; V1 is replaced by VS; FV is new.

## 7. What this cannot say

- K is the ruled construction, not a truth. Agreement with it measures closeness to the ruling.
- M5 shows association between a fault and a disagreement, not cause; the bins were fixed here to keep it honest, not because they are known to be the right cuts.
- About three months, one market regime. Nothing here relates a pin to later price.

## 8. Conduct

As v1, plus: check free disk first and stop under 1 GB; one symbol-day per query, 5 s sleeps, stop at the first error or any query over 10 s, no retry; empty days are logged and do not stop the loop; the loop is started detached and writes `ALL <n> DONE`; scoring holds one symbol-day in memory; every run under `ulimit -v 700000` with `python3 -B`; no git write; output only under `docs/research/pin_proof/fix/replay_v2/`; not run 08:30–15:40 IST Mon–Fri. The `volatility_snapshots` read is catalog-checked and EXPLAIN-gated before use. Two stops for review: after self-tests and one scored symbol-day, and after the pull before the analysis.
