<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/gamma_pipeline_audit_prereg_FROZEN_2026-11-22.md -->
# Gamma pipeline audit: frozen design, 2026-11-22

Session MR-PIN2. Written 2026-11-22 08:25 IST, before any net-gamma figure has been computed or seen. One look. Nothing in sections 3 to 7 is altered after the first figure is seen. The operator's approval and its time are recorded in the result document, not here, so this file's hash does not change.

Nothing in this audit is authorised for the Board or production.

## 1. Why

The pin test (`pin_live_replay_v2_result_2026-11-21.md`) showed that the vendor's two gammas per strike (call and put), and blank gammas, mislead a gross calculation that keeps them apart. Everything the Board builds on the netted quantity `gex_cr` uses the same two gammas. This audit measures the size of that fault through the gamma pipeline, and tests whether one gamma per strike gives a net closer to the reference.

## 2. Three layers, kept apart

| Layer | What it is | What this audit can say |
|---|---|---|
| 1. Gross gamma | gamma x (call OI + put OI) per strike | Profile error against the reference |
| 2. Net gamma | gamma x (call OI - put OI) per strike, calls counted positive and puts negative | Arithmetic error against the reference, GIVEN that sign convention |
| 3. Dealer-positioning interpretation | "dampening / amplifying", who holds what | NOTHING. Not tested here. The reference is a reference for gamma only. |

A good result on layers 1 and 2 does not validate layer 3.

## 3. Data and grain

- Files already on the engine box: `docs/research/pin_proof/fix/replay_v2/chain/` (58 days, 2026-08-24 to 2026-11-20). No database read for the measures.
- Runs: market runs, 09:15 to 15:29 IST. Symbols NIFTY and SENSEX, each reported separately.
- Grain: one gamma record per symbol, expiry, strike and run timestamp. Strike set: abs(K/S - 1) <= 0.05 with OI > 0 on at least one leg. Step: 50 (NIFTY), 100 (SENSEX).
- These 58 days were used to choose VS for the pin. No net figure from them has been computed or seen.

## 4. Quantities, per run and strike k

- `gc`, `gp`: vendor gamma of the call and put leg; blank or <= 0 counts as 0. `OIc`, `OIp`: open interest.
- `gVS`: mean of gc and gp when both > 0; the one that is > 0 when the other is not; 0 when neither.
- `gK`: the reference, own per-strike gamma exactly as in replay v2 (forward = median of K + C - P over the three strikes nearest spot; Black-76 implied vol of the out-of-the-money leg, r = 0; T = minutes to 15:30 IST on expiry / 525,600). Flag `fallback` where the solve fell back to at-the-money vol.
- Production replica P: net_P = gc x OIc - gp x OIp ; gross_P = gc x OIc + gp x OIp. A leg with gamma 0 or OI <= 0 contributes 0, as `merdian_compute/gamma.py:42`.
- Proposed N: net_N = gVS x (OIc - OIp) ; gross_N = gVS x (OIc + OIp).
- Reference R: net_R = gK x (OIc - OIp) ; gross_R = gK x (OIc + OIp).
- Sums over k are over the strike set of that run. GR = sum of gross_R.

The common factor spot^2 / 1e7 is left out; every measure is a ratio.

## 5. Measures

Each is computed per run, then reported per symbol as mean, median and 90th percentile over runs, with the number of runs; and per day (mean over the day's runs).

**Input (vendor)**
- I1. Blank rate: share of legs with OI > 0 whose gamma is blank or <= 0. By count and OI-weighted. Split by leg (in-the-money / out-of-the-money), by abs(K/S - 1) bucket (0-1, 1-2, 2-3, 3-5 %), by time (09:15-10:00, 10:00-14:00, 14:00-15:29), by expiry day / other day.
- I2. Call/put ratio gc/gp where both > 0: median, 10th and 90th percentile, share outside [0.8, 1.25]. Same splits, plus by (forward - spot)/step bucket (< -1, -1 to 1, > 1).

**Grain**
- G1. Distinct expiries per run. G2. Distinct snapshot timestamps among the legs of a run and their spread in seconds. G3. Duplicate (expiry, strike, leg) records in a run. If the files do not carry what a check needs, the check is reported NOT MEASURABLE, not estimated.

**Layer 2, net**
- N1. Production sign error. Over strikes with OIc != OIp: share where sign(net_P) differs from sign(OIc - OIp), split into "wrong sign" and "zero". By count and weighted by gross_R. Split by cause: a blank leg / both gammas present. (For N this is 0 by construction; it is not a test of N.)
- N2. Raw magnitude error: E_raw(X) = sum abs(net_X - net_R) / GR, X in {P, N}.
- N3. Shape error: each profile divided by its own gross total; E_shape(X) = sum abs(net_X / sum gross_X - net_R / GR). Range 0 to 2.
- N4. Total net: T_X = sum net_X / sum gross_X. Error abs(T_X - T_R). Share of runs with sign(T_X) != sign(T_R), over all runs and over runs with abs(T_R) >= 0.05.
- N5. Peaks: (a) strike with the largest positive net; (b) strike with the largest abs(net). Tie-break nearer to spot, then lower strike. Share of runs where X's strike = R's, and median abs gap in steps; over all runs and over runs where R's lead (top - second)/top >= 5 %.

**Layer 1, gross**
- L1. Gross shape error: sum abs(gross_X / sum gross_X - gross_R / GR), X in {P, N}.

**Reference quality**
- K1. Share of strikes, and of GR, where `fallback` is set. N2, N3, N4, L1 are reported twice: all strikes, and strikes without `fallback` only.

## 6. Rule (can fail)

For each symbol, N is BETTER than P on the net if all four hold on the all-strikes figures:
1. mean and median of E_raw(N) are both lower than those of E_raw(P);
2. mean and median of E_shape(N) are both lower than those of E_shape(P);
3. mean and median of abs(T_N - T_R) are both lower than those of abs(T_P - T_R);
4. on runs where R's lead >= 5 %, N's agreement with R is not lower than P's on both peaks of N5.

Result: BETTER only if all four hold for BOTH symbols; otherwise NOT BETTER. The sizes are reported beside the result, so "better but still poor" is visible. No absolute bar is set.

## 7. What is not a test

N1 for N; the consumer list; I1, I2, G1-G3, K1, L1. They are descriptive.

## 8. Limits

- P is a replica from the chain files, not the stored `gex_cr`. The replica is checked against stored `gex_cr` on the latest run only.
- The reference uses last-traded prices.
- The sign convention is assumed, not tested (layer 3).
