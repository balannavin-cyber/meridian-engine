# P1c — Does a pinned, positive-γ morning go with a smaller realised range? Pre-registration

| Field | Value |
|---|---|
| **Status** | **PRE-REGISTERED.** Committed with `p1c/p1c_regime_extract.sql` and `p1c/p1c_score.py` **before** the predictor extract runs. Its `git hash-object` is recorded in the result doc. |
| **Track item** | Roadmap §2.1 **P1c** (ruling **S94-B**; order 3rd under S94-A). Risk class **RO**. |
| **Design choices** | The four choices were proposed in S94 at 09:20 IST, and the operator went ahead with them: reuse P1's sample and split; "pinned-positive" = net γ > 0 and true HHI ≥ its calibration median; outcome = range in σ; NIFTY primary, P1's two-limb rule. |

## 1. The question

The premium-selling read rests on one claim: **when net γ is positive and concentrated, the day's
realised range is small relative to what the market priced.** P1 asked a different question
(do levels *locate* the extremes?) and answered NO. P1c asks the question the style actually
depends on. The Assumption Register's dampening row reads *"VALIDATED indirectly"* from directional
win rates (Exp 17/19), not from range. Roadmap §7.2 lists this exact test card.

## 2. Sample — reused from P1, with its history disclosed

- **Sessions:** P1's eligible sessions, unchanged. **N = 85 NIFTY, 84 SENSEX**, from 2026-05-25 (P1
  pre-registration `7a708a64…`, Part 1b). P1 already verified grid, one spot per run, front expiry,
  same-day IV and ≥ 300 minutes on each.
- **Split:** P1's own split (the `sess_ix ≤ n_cal` calibration half). That is **56 / 56 in
  calibration** and the remainder in holdout, so 29 NIFTY / 28 SENSEX. The scorer asserts both counts.
- **Disclosure.** P1's scorer computed each session's `hi` and `lo`, and P1's result was read in
  S93. **Range by regime has never been computed or viewed.** P1 never read net γ or HHI, and no
  P1 table splits by them. This is the disclosure; it is not a claim that the data is unseen.

## 3. Definitions (fixed at commit)

- **t0:** P1's t0, the first `gex_strike_snapshots` run with `ts` in [09:15, 10:15) IST. The scorer
  asserts that the predictor's t0 equals P1's `ats_ist` for every session, to the second.
- **Predictors, at t0, front expiry only** (nearest `expiry_date` ≥ session date, as in P1):
  - net γ = Σ `gex_cr` (equal to `gamma_metrics.net_gex` by the ADR-014 §2.5 falsification rule);
  - **true HHI** = Σ (|gex_cr| / Σ|gex_cr|)² over the run's front-expiry strikes. This is the
    Herfindahl, **not** `gamma_concentration`, which is the top-1 share (tech_debt note, S89).
- **Pinned-positive (PP):** net γ > 0 **and** HHI ≥ the **calibration-half median** of HHI for that
  symbol. The median is computed on calibration only, so the holdout never sets its own threshold.
- **Outcome:** range in σ = (`hi` − `lo`) / `sigma_d`, read from P1's committed extract
  (`part2_extract_2026-10-09.json`, md5 `70be3c52…`), `anchor = t0`. `hi` / `lo` are P1's H and L over
  (t0, 15:15) IST, with the auction excluded. The scorer **asserts**
  `sigma_d = s0 · iv0/100 · √(1/252)` for every session, within **10⁻³ relative**. That is P1's own
  formula (`p1_part2_extract.sql:146`), and the tolerance is derived from P1's export rounding
  (`sigma_d` to 0.01 ≈ 3 × 10⁻⁵ rel; `iv0` to 0.01 ≈ 5 × 10⁻⁴ rel). A wrong formula differs by ≥ 20 %.
  Calibration is P1's `sess_ix ≤ n_cal` (`p1_score.py:170`); `hi` / `lo` are P1's `max(spot)` /
  `min(spot)` (`p1_part2_extract.sql:188`).
- **Effect:** e = mean range σ (other sessions) − mean range σ (PP). Positive means PP days are calmer.

## 4. What is read, and when

The **only new database read** is `p1c/p1c_regime_extract.sql`: predictors at t0, through
`bin/roq.sh`. It reads no outcome. The outcome comes from P1's committed extract. So **no
outcome query is run for P1c at all.**

## 5. Test and verdict (fixed at commit)

- **Primary: NIFTY** (as in P1). SENSEX is computed identically and reported **descriptively**.
- **Holdout** e with a **95 % percentile bootstrap** interval, resampling sessions within each
  group: 10,000 resamples, seed 20261010. That is 95 % rather than P1's 97.5 % because there is one
  primary test, not two.
- **YES** ⟺ calibration e > 0 **and** the holdout CI excludes 0 (lower bound > 0) **and** holdout
  e ≥ ½ × calibration e. This is P1 §5.8's two-limb rule. Otherwise **NO**, with the failing
  limb named.
- **INCONCLUSIVE** if either holdout group has **fewer than 8** sessions. Below that, a bootstrap of
  a group mean is too coarse to carry a verdict. The threshold is set from method, not data.
- **Descriptive, no verdict:** SENSEX; mean range σ by net γ sign alone and by DTE bucket
  (0 / 1 / 2–3 / 4+, as reporting strata only, never a selection, per P1 §5.1).

## 6. Limits

- **n is small**: the NIFTY holdout is about 29 sessions, split into two groups.
- **Range in σ measures realised vs implied**, so a YES says PP days were calm **relative to IV0**.
  It does not say they were calm in points.
- **Regime at t0 only.** It uses the previous session's OI (P1 §6 note) and does not track the
  intraday regime.
- **Positioning γ, not dealer γ** (P2: REGIME-DEPENDENT). P1c tests whether the board's number
  sorts days. It does not test why.
- **A YES is not a trade rule.** Any use as a gate or a sizing input is its own ruling.
