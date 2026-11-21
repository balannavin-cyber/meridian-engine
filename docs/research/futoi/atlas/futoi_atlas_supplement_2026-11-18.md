# Atlas supplement — 2026-11-18

Exploration. No verdict. Nothing here is a finding until confirmed once on unseen data.

Produced by re-running the same row builders and the same study code in process, so every figure matches the main document's code path. The main document is unchanged. Read-only; no database access.

---

## Shortlist, mirrored pairs collapsed — top 15   [exploratory]

The main document's SHORTLIST is unchanged. Here a C1 `set=rest` cell is dropped as the exact negation of its `set=large` twin: **2** such mirror rows removed. Eligible cells after collapsing: **350**.

Ranking is unchanged: |effect| ÷ half-width of its own 95 % interval. **A shortlist drawn from many cuts is biased upward** — these are the extreme tail of 3664 cells and nothing here is a finding.

| # | study | definition | outcome | n windows | n (complement) | n sessions | effect | 95% CI | |eff|/hw | F vs F1 | both halves | expiry removed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C1 | set=large, metric=intraday_range | rngnext | 25 | 218 | 25 | +48.725 bp | [+27.152, +69.296] | 2.31 | n/a | n/a | n/a |
| 2 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=all day | retnext | 80 | 26 | 57 | -102.927 bp | [-156.376, -54.347] | 2.02 | yes | yes | yes |
| 3 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=all day | contnext | 80 | 26 | 57 | -102.927 bp | [-156.376, -54.347] | 2.02 | yes | yes | yes |
| 4 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=all day | hitnext | 80 | 26 | 57 | -0.395 rate | [-0.582, -0.183] | 1.98 | yes | yes | yes |
| 5 | C1 | set=large, metric=abs_ret | rngnext | 25 | 218 | 25 | +44.692 bp | [+22.309, +68.499] | 1.94 | n/a | n/a | n/a |
| 6 | A3 | oi=F, subset=all, pair=SB vs LU | retnext | 87 | 34 | 87 | -67.568 bp | [-105.332, -31.317] | 1.83 | yes | yes | yes |
| 7 | A3 | oi=F, subset=all, pair=SB vs LU | contnext | 87 | 34 | 87 | +67.568 bp | [+31.317, +105.332] | 1.83 | yes | yes | yes |
| 8 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=to 11:30 | retnext | 31 | 7 | 29 | -107.058 bp | [-168.401, -49.492] | 1.80 | yes | yes | yes |
| 9 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=to 11:30 | contnext | 31 | 7 | 29 | -107.058 bp | [-168.401, -49.492] | 1.80 | yes | yes | yes |
| 10 | A1 | step=15, oi=F, subset=no-expiry, strength=strong, pair=SB vs LU, tod=11:30-13:30 | hitnext | 132 | 26 | 73 | +0.359 rate | [+0.140, +0.543] | 1.78 | yes | yes | yes |
| 11 | C3 | oi=F1, pair=LB vs SC | contnext | 39 | 38 | 33 | -87.078 bp | [-136.710, -38.766] | 1.78 | yes | yes | n/a |
| 12 | A2 | step=15, oi=F1, subset=all, prev=LB, cur=SC | nxt_cont30 | 238 | 854 | 155 | -3.553 bp | [-5.828, -1.485] | 1.64 | yes | yes | yes |
| 13 | A1 | step=15, oi=F, subset=all, strength=strong, pair=SB vs LU, tod=11:30-13:30 | hitnext | 150 | 28 | 82 | +0.314 rate | [+0.105, +0.490] | 1.64 | yes | yes | yes |
| 14 | A1 | step=15, oi=F1, subset=all, strength=strong, pair=LB vs SC, tod=11:30-13:30 | hitnext | 145 | 119 | 92 | -0.212 rate | [-0.339, -0.077] | 1.62 | yes | yes | yes |
| 15 | A1 | step=15, oi=F, subset=no-expiry, strength=all, pair=LB vs SC, tod=11:30-13:30 | retnext | 373 | 164 | 164 | -33.758 bp | [-54.579, -12.458] | 1.60 | yes | yes | yes |

## The A1 neighbourhood of `LB vs SC`, outcome `retnext`   [exploratory]

The main shortlist's A1 entries are all step=60, OI=F, no-expiry, strong, LB vs SC, all day. Below: that cell's two sides counted separately, then the SAME contrast at every step, both OI series and both subsets, at strength `strong` and `all`. Effects are LB minus SC in bp.

| step | OI | subset | strength | n LB | sess LB | n SC | sess SC | effect (bp) | 95% CI | excl zero |
|---|---|---|---|---|---|---|---|---|---|---|
| 15 | F | all | strong | 429 | 150 | 148 | 98 | -16.746 | [-40.302, +6.185] | no |
| 15 | F | all | all | 1406 | 244 | 637 | 200 | -15.569 | [-27.637, -2.567] | yes |
| 15 | F | no-expiry | strong | 373 | 135 | 131 | 86 | -22.806 | [-49.087, +1.900] | no |
| 15 | F | no-expiry | all | 1251 | 222 | 585 | 182 | -20.771 | [-34.346, -7.583] | yes |
| 15 | F1 | all | strong | 428 | 174 | 361 | 158 | -27.441 | [-48.743, -7.961] | yes |
| 15 | F1 | all | all | 1569 | 243 | 1291 | 236 | -13.297 | [-23.462, -3.154] | yes |
| 15 | F1 | no-expiry | strong | 401 | 162 | 301 | 141 | -16.116 | [-38.100, +5.324] | no |
| 15 | F1 | no-expiry | all | 1453 | 222 | 1144 | 215 | -8.566 | [-18.485, +1.814] | no |
| 30 | F | all | strong | 206 | 105 | 57 | 47 | -46.973 | [-84.475, -10.389] | yes |
| 30 | F | all | all | 708 | 228 | 301 | 150 | -17.709 | [-34.202, -1.281] | yes |
| 30 | F | no-expiry | strong | 181 | 93 | 56 | 46 | -55.687 | [-93.678, -18.328] | yes |
| 30 | F | no-expiry | all | 632 | 207 | 283 | 139 | -23.539 | [-40.547, -6.802] | yes |
| 30 | F1 | all | strong | 194 | 109 | 191 | 119 | -29.666 | [-55.576, -2.978] | yes |
| 30 | F1 | all | all | 775 | 233 | 662 | 221 | -18.213 | [-30.282, -6.980] | yes |
| 30 | F1 | no-expiry | strong | 178 | 100 | 162 | 105 | -21.337 | [-48.290, +8.205] | no |
| 30 | F1 | no-expiry | all | 720 | 216 | 589 | 201 | -13.684 | [-25.738, -1.844] | yes |
| 60 | F | all | strong | 95 | 65 | 28 | 26 | -82.399 | [-137.384, -34.196] | yes |
| 60 | F | all | all | 379 | 186 | 146 | 100 | -22.998 | [-42.103, -4.129] | yes |
| 60 | F | no-expiry | strong | 80 | 57 | 26 | 24 | -102.927 | [-156.376, -54.347] | yes |
| 60 | F | no-expiry | all | 334 | 165 | 136 | 93 | -31.117 | [-50.397, -11.464] | yes |
| 60 | F1 | all | strong | 86 | 68 | 90 | 71 | -57.393 | [-95.139, -22.887] | yes |
| 60 | F1 | all | all | 395 | 202 | 341 | 178 | -20.408 | [-36.341, -5.505] | yes |
| 60 | F1 | no-expiry | strong | 80 | 62 | 77 | 62 | -50.792 | [-90.144, -13.391] | yes |
| 60 | F1 | no-expiry | all | 370 | 189 | 298 | 159 | -15.130 | [-30.713, +0.139] | no |

## Study B — every cell whose interval excludes zero   [exploratory]

22 of 120 Study B cells.

| clock | subset | quintile contrast | outcome | n | sessions | effect (bp) | 95% CI |
|---|---|---|---|---|---|---|---|
| 10:00:59 | all | Q4 vs the other four | ret_next | 48 | 48 | +32.518 | [+7.760, +57.032] |
| 10:00:59 | no-expiry | Q4 vs the other four | ret_next | 43 | 43 | +29.631 | [+4.246, +54.986] |
| 10:00:59 | all | Q4 vs the other four | rng_next | 49 | 49 | -14.407 | [-26.107, -1.871] |
| 10:00:59 | no-expiry | Q4 vs the other four | rng_next | 44 | 44 | -13.775 | [-26.839, -0.533] |
| 10:00:59 | no-expiry | Q5 vs the other four | ret_to_close | 45 | 45 | -15.810 | [-31.173, -0.232] |
| 10:00:59 | all | Q5 vs the other four | rng_next | 49 | 49 | -14.065 | [-25.049, -3.943] |
| 10:00:59 | no-expiry | Q5 vs the other four | rng_next | 45 | 45 | -12.229 | [-22.744, -1.206] |
| 12:00:59 | no-expiry | Q1 vs the other four | rng_next | 45 | 45 | +20.367 | [+0.048, +42.922] |
| 12:00:59 | all | Q2 vs the other four | ret_to_close | 49 | 49 | -14.760 | [-27.101, -1.961] |
| 12:00:59 | no-expiry | Q2 vs the other four | ret_to_close | 44 | 44 | -13.494 | [-26.373, -0.967] |
| 12:00:59 | no-expiry | Q4 vs the other four | rng_next | 44 | 44 | -13.303 | [-26.651, -0.380] |
| 12:00:59 | all | Q5 vs the other four | rng_next | 49 | 49 | -15.799 | [-26.511, -5.840] |
| 12:00:59 | no-expiry | Q5 vs the other four | rng_next | 45 | 45 | -11.758 | [-22.860, -0.505] |
| 14:00:59 | all | Q1 vs the other four | rng_next | 50 | 50 | +21.844 | [+2.489, +43.956] |
| 14:00:59 | no-expiry | Q1 vs the other four | rng_next | 45 | 45 | +24.735 | [+4.614, +47.577] |
| 14:00:59 | all | Q3 vs the other four | ret_to_close | 49 | 49 | -7.745 | [-15.245, -0.307] |
| 14:00:59 | all | Q4 vs the other four | rng_next | 48 | 48 | -12.339 | [-24.401, -1.200] |
| 14:00:59 | no-expiry | Q4 vs the other four | rng_next | 44 | 44 | -12.671 | [-25.987, -0.603] |
| 14:00:59 | all | Q5 vs the other four | rng_next | 49 | 49 | -15.414 | [-26.551, -4.315] |
| 14:00:59 | no-expiry | Q5 vs the other four | rng_next | 45 | 45 | -12.927 | [-24.673, -1.401] |
| 15:29:59 | all | Q2 vs the other four | rng_next | 49 | 49 | +15.012 | [+0.640, +31.287] |
| 15:29:59 | no-expiry | Q2 vs the other four | rng_next | 44 | 44 | +16.355 | [+1.040, +33.087] |

---

*Exploration. No verdict. Read-only run; no database write, no commit.*
