# M10 stage 1 -- constant sigma versus constant percent

Generated 2026-09-21. **Zero database requests** -- computed entirely from `.m1_era1_cycles.json` (102 measured era-1 cycles).

## What would falsify a positive result

A real sigma-distance effect means the threshold shares vary **monotonically** across sigma-distance terciles. Non-monotone buckets, or a spread inside sampling noise at these N, is no effect. The brief's gate for stage 2 is a spread wider than **10 percentage points at DTE 1**.

## The coupling: this is largely the IV split under another name

For a strike at 1% of spot, `sigma_distance = 0.01*S / (S * IV/100 / sqrt(252)) = sqrt(252)/IV` -- a deterministic function of ATM IV alone. The only independent variation is grid rounding, which differs by symbol: NIFTY rounds 240 points to a 50-point grid, SENSEX rounds 800 points to a 100-point grid.

| symbol | leg | corr(sigma_dist, 1/IV) | sigma-dist terciles | min | max |
|---|---|---:|---|---:|---:|
| NIFTY | OTM_CE | 0.987 | 1.34 / 1.73 | 0.62 | 2.36 |
| NIFTY | OTM_PE | 0.984 | 1.33 / 1.78 | 0.65 | 2.45 |
| SENSEX | OTM_CE | 0.992 | 1.36 / 1.74 | 0.64 | 2.29 |
| SENSEX | OTM_PE | 0.992 | 1.35 / 1.70 | 0.66 | 2.39 |

A correlation at or near 1.000 means this table is the M1 IV-regime split relabelled, and is **not** independent corroboration of it.

## M10.A  The question: spread between FAR and NEAR tercile at DTE 1

`far` = largest sigma-distance (lowest IV). Spread = far minus near, in percentage points.

| symbol | leg | thr | near | mid | far | spread (far-near) | monotone? |
|---|---|---|---:|---:|---:|---:|---|
| NIFTY | OTM_PE | >=50% | 72% | 71% | 75% | +3 pp | NO |
| NIFTY | OTM_PE | >=60% | 67% | 65% | 62% | -4 pp | yes |
| NIFTY | OTM_PE | >=70% | 56% | 53% | 62% | +7 pp | NO |
| NIFTY | OTM_PE | >=80% | 50% | 47% | 44% | -6 pp | yes |
| NIFTY | OTM_CE | >=50% | 72% | 76% | 75% | +3 pp | NO |
| NIFTY | OTM_CE | >=60% | 67% | 71% | 62% | -4 pp | NO |
| NIFTY | OTM_CE | >=70% | 50% | 65% | 62% | +12 pp | NO |
| NIFTY | OTM_CE | >=80% | 50% | 41% | 56% | +6 pp | NO |
| SENSEX | OTM_PE | >=50% | 65% | 80% | 56% | -8 pp | NO |
| SENSEX | OTM_PE | >=60% | 59% | 73% | 50% | -9 pp | NO |
| SENSEX | OTM_PE | >=70% | 59% | 67% | 50% | -9 pp | NO |
| SENSEX | OTM_PE | >=80% | 47% | 67% | 38% | -10 pp | NO |
| SENSEX | OTM_CE | >=50% | 59% | 67% | 69% | +10 pp | yes |
| SENSEX | OTM_CE | >=60% | 53% | 67% | 69% | +16 pp | yes |
| SENSEX | OTM_CE | >=70% | 35% | 67% | 69% | +33 pp | yes |
| SENSEX | OTM_CE | >=80% | 35% | 67% | 69% | +33 pp | yes |

**4 of 16** DTE-1 cells show a spread wider than the 10 pp stage-2 gate. **6 of 16** are monotone across the three buckets.

## M10.B  Full threshold shares by sigma-distance bucket and DTE

Pooled state (tested and untested together) -- the ex-ante view. `N*` marks N < 20.

| symbol | leg | bucket | DTE | N | >=50% | >=60% | >=70% | >=80% |
|---|---|---|---|---:|---:|---:|---:|---:|
| NIFTY | OTM_CE | all | DTE5 | 1* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_CE | all | DTE4 | 36 | 6% | 6% | 3% | 0% |
| NIFTY | OTM_CE | all | DTE3 | 49 | 35% | 20% | 10% | 2% |
| NIFTY | OTM_CE | all | DTE2 | 51 | 47% | 41% | 27% | 16% |
| NIFTY | OTM_CE | all | DTE1 | 51 | 75% | 67% | 59% | 49% |
| NIFTY | OTM_CE | all | DTE0 | 49 | 84% | 84% | 84% | 84% |
| NIFTY | OTM_CE | all | EXP1300 | 51 | 80% | 80% | 78% | 76% |
| NIFTY | OTM_CE | near | DTE5 | 1* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_CE | near | DTE4 | 12* | 8% | 8% | 8% | 0% |
| NIFTY | OTM_CE | near | DTE3 | 17* | 35% | 24% | 18% | 0% |
| NIFTY | OTM_CE | near | DTE2 | 18* | 44% | 44% | 44% | 22% |
| NIFTY | OTM_CE | near | DTE1 | 18* | 72% | 67% | 50% | 50% |
| NIFTY | OTM_CE | near | DTE0 | 18* | 72% | 72% | 72% | 72% |
| NIFTY | OTM_CE | near | EXP1300 | 18* | 72% | 72% | 72% | 67% |
| NIFTY | OTM_CE | mid | DTE4 | 12* | 8% | 8% | 0% | 0% |
| NIFTY | OTM_CE | mid | DTE3 | 17* | 18% | 6% | 6% | 0% |
| NIFTY | OTM_CE | mid | DTE2 | 17* | 47% | 35% | 18% | 12% |
| NIFTY | OTM_CE | mid | DTE1 | 17* | 76% | 71% | 65% | 41% |
| NIFTY | OTM_CE | mid | DTE0 | 17* | 94% | 94% | 94% | 94% |
| NIFTY | OTM_CE | mid | EXP1300 | 17* | 94% | 94% | 88% | 88% |
| NIFTY | OTM_CE | far | DTE4 | 12* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_CE | far | DTE3 | 15* | 53% | 33% | 7% | 7% |
| NIFTY | OTM_CE | far | DTE2 | 16* | 50% | 44% | 19% | 12% |
| NIFTY | OTM_CE | far | DTE1 | 16* | 75% | 62% | 62% | 56% |
| NIFTY | OTM_CE | far | DTE0 | 14* | 86% | 86% | 86% | 86% |
| NIFTY | OTM_CE | far | EXP1300 | 16* | 75% | 75% | 75% | 75% |
| NIFTY | OTM_PE | all | DTE5 | 1* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_PE | all | DTE4 | 36 | 3% | 0% | 0% | 0% |
| NIFTY | OTM_PE | all | DTE3 | 49 | 31% | 24% | 16% | 2% |
| NIFTY | OTM_PE | all | DTE2 | 51 | 59% | 57% | 49% | 24% |
| NIFTY | OTM_PE | all | DTE1 | 51 | 73% | 65% | 57% | 47% |
| NIFTY | OTM_PE | all | DTE0 | 49 | 76% | 76% | 76% | 76% |
| NIFTY | OTM_PE | all | EXP1300 | 51 | 73% | 71% | 71% | 71% |
| NIFTY | OTM_PE | near | DTE5 | 1* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_PE | near | DTE4 | 13* | 8% | 0% | 0% | 0% |
| NIFTY | OTM_PE | near | DTE3 | 17* | 29% | 24% | 18% | 6% |
| NIFTY | OTM_PE | near | DTE2 | 18* | 44% | 44% | 44% | 22% |
| NIFTY | OTM_PE | near | DTE1 | 18* | 72% | 67% | 56% | 50% |
| NIFTY | OTM_PE | near | DTE0 | 18* | 78% | 78% | 78% | 78% |
| NIFTY | OTM_PE | near | EXP1300 | 18* | 78% | 78% | 78% | 78% |
| NIFTY | OTM_PE | mid | DTE4 | 13* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_PE | mid | DTE3 | 17* | 29% | 24% | 24% | 0% |
| NIFTY | OTM_PE | mid | DTE2 | 17* | 59% | 59% | 47% | 29% |
| NIFTY | OTM_PE | mid | DTE1 | 17* | 71% | 65% | 53% | 47% |
| NIFTY | OTM_PE | mid | DTE0 | 17* | 82% | 82% | 82% | 82% |
| NIFTY | OTM_PE | mid | EXP1300 | 17* | 65% | 65% | 65% | 65% |
| NIFTY | OTM_PE | far | DTE4 | 10* | 0% | 0% | 0% | 0% |
| NIFTY | OTM_PE | far | DTE3 | 15* | 33% | 27% | 7% | 0% |
| NIFTY | OTM_PE | far | DTE2 | 16* | 75% | 69% | 56% | 19% |
| NIFTY | OTM_PE | far | DTE1 | 16* | 75% | 62% | 62% | 44% |
| NIFTY | OTM_PE | far | DTE0 | 14* | 64% | 64% | 64% | 64% |
| NIFTY | OTM_PE | far | EXP1300 | 16* | 75% | 69% | 69% | 69% |
| SENSEX | OTM_CE | all | DTE5 | 2* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_CE | all | DTE4 | 37 | 8% | 5% | 3% | 0% |
| SENSEX | OTM_CE | all | DTE3 | 48 | 33% | 23% | 10% | 4% |
| SENSEX | OTM_CE | all | DTE2 | 50 | 58% | 54% | 48% | 42% |
| SENSEX | OTM_CE | all | DTE1 | 48 | 65% | 62% | 56% | 56% |
| SENSEX | OTM_CE | all | DTE0 | 50 | 80% | 80% | 80% | 80% |
| SENSEX | OTM_CE | all | EXP1300 | 46 | 78% | 76% | 76% | 70% |
| SENSEX | OTM_CE | near | DTE5 | 1* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_CE | near | DTE4 | 11* | 9% | 9% | 9% | 0% |
| SENSEX | OTM_CE | near | DTE3 | 15* | 27% | 20% | 13% | 7% |
| SENSEX | OTM_CE | near | DTE2 | 17* | 41% | 35% | 29% | 29% |
| SENSEX | OTM_CE | near | DTE1 | 17* | 59% | 53% | 35% | 35% |
| SENSEX | OTM_CE | near | DTE0 | 17* | 82% | 82% | 82% | 82% |
| SENSEX | OTM_CE | near | EXP1300 | 16* | 81% | 75% | 75% | 69% |
| SENSEX | OTM_CE | mid | DTE5 | 1* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_CE | mid | DTE4 | 13* | 15% | 8% | 0% | 0% |
| SENSEX | OTM_CE | mid | DTE3 | 17* | 29% | 29% | 12% | 6% |
| SENSEX | OTM_CE | mid | DTE2 | 17* | 65% | 59% | 53% | 41% |
| SENSEX | OTM_CE | mid | DTE1 | 15* | 67% | 67% | 67% | 67% |
| SENSEX | OTM_CE | mid | DTE0 | 17* | 88% | 88% | 88% | 88% |
| SENSEX | OTM_CE | mid | EXP1300 | 14* | 79% | 79% | 79% | 71% |
| SENSEX | OTM_CE | far | DTE4 | 13* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_CE | far | DTE3 | 16* | 44% | 19% | 6% | 0% |
| SENSEX | OTM_CE | far | DTE2 | 16* | 69% | 69% | 62% | 56% |
| SENSEX | OTM_CE | far | DTE1 | 16* | 69% | 69% | 69% | 69% |
| SENSEX | OTM_CE | far | DTE0 | 16* | 69% | 69% | 69% | 69% |
| SENSEX | OTM_CE | far | EXP1300 | 16* | 75% | 75% | 75% | 69% |
| SENSEX | OTM_PE | all | DTE5 | 2* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_PE | all | DTE4 | 37 | 3% | 0% | 0% | 0% |
| SENSEX | OTM_PE | all | DTE3 | 48 | 25% | 21% | 6% | 2% |
| SENSEX | OTM_PE | all | DTE2 | 50 | 38% | 36% | 32% | 22% |
| SENSEX | OTM_PE | all | DTE1 | 48 | 67% | 60% | 58% | 50% |
| SENSEX | OTM_PE | all | DTE0 | 50 | 82% | 82% | 82% | 82% |
| SENSEX | OTM_PE | all | EXP1300 | 46 | 85% | 80% | 78% | 72% |
| SENSEX | OTM_PE | near | DTE5 | 1* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_PE | near | DTE4 | 11* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_PE | near | DTE3 | 15* | 27% | 13% | 0% | 0% |
| SENSEX | OTM_PE | near | DTE2 | 17* | 47% | 41% | 35% | 18% |
| SENSEX | OTM_PE | near | DTE1 | 17* | 65% | 59% | 59% | 47% |
| SENSEX | OTM_PE | near | DTE0 | 17* | 88% | 88% | 88% | 88% |
| SENSEX | OTM_PE | near | EXP1300 | 16* | 88% | 75% | 75% | 75% |
| SENSEX | OTM_PE | mid | DTE5 | 1* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_PE | mid | DTE4 | 12* | 0% | 0% | 0% | 0% |
| SENSEX | OTM_PE | mid | DTE3 | 17* | 35% | 35% | 12% | 6% |
| SENSEX | OTM_PE | mid | DTE2 | 17* | 41% | 41% | 35% | 29% |
| SENSEX | OTM_PE | mid | DTE1 | 15* | 80% | 73% | 67% | 67% |
| SENSEX | OTM_PE | mid | DTE0 | 17* | 82% | 82% | 82% | 82% |
| SENSEX | OTM_PE | mid | EXP1300 | 15* | 93% | 93% | 93% | 80% |
| SENSEX | OTM_PE | far | DTE4 | 14* | 7% | 0% | 0% | 0% |
| SENSEX | OTM_PE | far | DTE3 | 16* | 12% | 12% | 6% | 0% |
| SENSEX | OTM_PE | far | DTE2 | 16* | 25% | 25% | 25% | 19% |
| SENSEX | OTM_PE | far | DTE1 | 16* | 56% | 50% | 50% | 38% |
| SENSEX | OTM_PE | far | DTE0 | 16* | 75% | 75% | 75% | 75% |
| SENSEX | OTM_PE | far | EXP1300 | 15* | 73% | 73% | 67% | 60% |

## Inherited caveats

This reads the cache written at 08:02, which predates three fixes:

- **whole-stamp rejection** -- a stamp lost to one stale leg lost all legs, so OTM N here is lower than it will be after per-leg rejection;
- **Muhurat still counted as a trading day** -- DTE is inflated by one for any cycle containing 2025-10-21;
- the HELD_ATM rename, which is irrelevant here since M10 uses only the OTM legs.

None of the three plausibly reverses a monotonic spread, but all three shift N and DTE labels slightly. Re-run after the era-1 re-sweep lands.

