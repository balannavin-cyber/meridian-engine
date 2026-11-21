# Atlas follow-ups — 2026-11-18

Exploration. No verdict. Nothing here is a finding until confirmed once on unseen data.

Read-only; no database access. Same row builders and the same session-clustered percentile bootstrap (2000 resamples, seed 20261118) as the main document. Intervals are descriptive.

---

## 1. A1 `LB vs SC` on `retnext`, matched on move size   [exploratory]

Steps 60 and 30, OI = F, subset = no-expiry. First each side's own mean same-session return to close (`retclose`, bp) and mean |dP| (index points), so the two sides' move sizes are visible. Then the LB-minus-SC contrast computed **within terciles of `retclose`**, the terciles cut on the pooled LB∪SC rows of that cell.

### Side profiles

| step | strength | side | n | sessions | mean retclose (bp) | mean \|dP\| (pts) |
|---|---|---|---|---|---|---|
| 60 | strong | LB | 80 | 57 | -8.259 | 70.71 |
| 60 | strong | SC | 26 | 24 | +5.752 | 86.08 |
| 60 | all | LB | 334 | 165 | -2.464 | 41.84 |
| 60 | all | SC | 136 | 93 | +0.832 | 47.99 |
| 30 | strong | LB | 181 | 93 | -4.532 | 51.57 |
| 30 | strong | SC | 56 | 46 | +2.799 | 70.15 |
| 30 | all | LB | 632 | 207 | -1.886 | 30.47 |
| 30 | all | SC | 283 | 139 | -0.814 | 35.54 |

### LB minus SC within terciles of same-session return to close

| step | strength | tercile of retclose | retclose range (bp) | n LB | n SC | sessions | effect (bp) | 95% CI | excl zero |
|---|---|---|---|---|---|---|---|---|---|
| 60 | strong | T1 | -inf .. -18.4 | 31 | 5 | 25 | -93.939 | [-177.762, +14.024] | no |
| 60 | strong | T2 | -18.4 .. +4.0 | 23 | 12 | 20 | -74.005 | [-160.029, -2.168] | yes |
| 60 | strong | T3 | +4.0 .. +inf | 26 | 9 | 22 | -124.209 | [-197.455, -56.726] | yes |
| 60 | all | T1 | -inf .. -9.2 | 119 | 38 | 83 | -40.336 | [-71.311, -7.755] | yes |
| 60 | all | T2 | -9.2 .. +7.1 | 109 | 47 | 73 | -16.842 | [-49.745, +11.507] | no |
| 60 | all | T3 | +7.1 .. +inf | 106 | 51 | 67 | -17.412 | [-48.471, +13.999] | no |
| 30 | strong | T1 | -inf .. -19.5 | 63 | 16 | 48 | -60.213 | [-113.385, -6.069] | yes |
| 30 | strong | T2 | -19.5 .. +8.7 | 61 | 18 | 47 | -49.610 | [-105.669, -0.421] | yes |
| 30 | strong | T3 | +8.7 .. +inf | 57 | 22 | 31 | -34.525 | [-88.481, +26.039] | no |
| 30 | all | T1 | -inf .. -11.5 | 222 | 83 | 114 | -19.386 | [-49.609, +11.630] | no |
| 30 | all | T2 | -11.5 .. +9.6 | 211 | 94 | 116 | -15.277 | [-37.182, +3.717] | no |
| 30 | all | T3 | +9.6 .. +inf | 199 | 106 | 82 | -18.790 | [-48.327, +10.956] | no |

## 2. The mirror: `SB vs LU` on `retnext`, full grid   [exploratory]

Same 24-cell grid as the `LB vs SC` neighbourhood: step × OI series × subset × strength. Effects are SB minus LU in bp.

| step | OI | subset | strength | n SB | sess SB | n LU | sess LU | effect (bp) | 95% CI | excl zero |
|---|---|---|---|---|---|---|---|---|---|---|
| 15 | F | all | strong | 536 | 171 | 94 | 73 | -39.522 | [-73.292, -6.222] | yes |
| 15 | F | all | all | 1597 | 240 | 543 | 198 | -17.944 | [-35.578, -1.894] | yes |
| 15 | F | no-expiry | strong | 464 | 151 | 85 | 66 | -45.189 | [-81.713, -12.589] | yes |
| 15 | F | no-expiry | all | 1426 | 218 | 508 | 179 | -23.045 | [-40.501, -6.492] | yes |
| 15 | F1 | all | strong | 512 | 184 | 301 | 156 | -33.495 | [-55.036, -11.683] | yes |
| 15 | F1 | all | all | 1732 | 244 | 1230 | 237 | -17.479 | [-29.483, -5.234] | yes |
| 15 | F1 | no-expiry | strong | 472 | 170 | 248 | 141 | -25.273 | [-45.722, -3.842] | yes |
| 15 | F1 | no-expiry | all | 1619 | 222 | 1079 | 217 | -13.272 | [-24.619, -2.049] | yes |
| 30 | F | all | strong | 303 | 131 | 41 | 31 | -53.566 | [-109.018, -8.933] | yes |
| 30 | F | all | all | 828 | 232 | 243 | 145 | -19.185 | [-37.755, -1.133] | yes |
| 30 | F | no-expiry | strong | 253 | 113 | 37 | 27 | -61.101 | [-121.860, -8.142] | yes |
| 30 | F | no-expiry | all | 731 | 211 | 231 | 134 | -25.711 | [-44.513, -7.976] | yes |
| 30 | F1 | all | strong | 285 | 135 | 152 | 90 | -45.129 | [-73.986, -15.732] | yes |
| 30 | F1 | all | all | 898 | 232 | 578 | 208 | -19.374 | [-34.182, -5.017] | yes |
| 30 | F1 | no-expiry | strong | 262 | 125 | 122 | 79 | -33.676 | [-63.315, -3.028] | yes |
| 30 | F1 | no-expiry | all | 842 | 214 | 500 | 190 | -15.027 | [-29.221, -1.322] | yes |
| 60 | F | all | strong | 169 | 99 | 18 | 17 | -69.602 | [-145.561, -6.272] | yes |
| 60 | F | all | all | 431 | 192 | 98 | 73 | -27.536 | [-52.263, -3.562] | yes |
| 60 | F | no-expiry | strong | 144 | 86 | 16 | 15 | -81.361 | [-162.104, -11.259] | yes |
| 60 | F | no-expiry | all | 386 | 173 | 93 | 68 | -31.084 | [-55.258, -8.063] | yes |
| 60 | F1 | all | strong | 161 | 102 | 64 | 49 | -45.956 | [-86.399, -8.682] | yes |
| 60 | F1 | all | all | 456 | 195 | 266 | 151 | -27.546 | [-45.595, -10.016] | yes |
| 60 | F1 | no-expiry | strong | 148 | 95 | 47 | 39 | -26.217 | [-67.268, +12.869] | no |
| 60 | F1 | no-expiry | all | 428 | 184 | 230 | 137 | -22.262 | [-39.567, -5.400] | yes |

## 3. A3 day level — both pairs on next-session return   [exploratory]

Class from close-to-close dP and dOI; the outcome is the next session's return in bp. Effects are the first class minus the second.

| OI | subset | contrast | n days | n comp days | sessions | effect (bp) | 95% CI | excl zero |
|---|---|---|---|---|---|---|---|---|
| F | all | LB vs SC | 57 | 62 | 57 | -38.757 | [-67.881, -10.501] | yes |
| F | all | SB vs LU | 87 | 34 | 87 | -67.568 | [-105.332, -31.317] | yes |
| F | no-expiry | LB vs SC | 57 | 50 | 57 | -38.303 | [-71.392, -7.246] | yes |
| F | no-expiry | SB vs LU | 86 | 25 | 86 | -50.356 | [-95.597, -13.623] | yes |
| F1 | all | LB vs SC | 37 | 84 | 37 | -24.957 | [-56.479, +6.585] | no |
| F1 | all | SB vs LU | 56 | 65 | 56 | -33.039 | [-64.715, +1.540] | no |
| F1 | no-expiry | LB vs SC | 28 | 81 | 28 | -28.712 | [-68.277, +8.948] | no |
| F1 | no-expiry | SB vs LU | 54 | 57 | 54 | -29.618 | [-66.195, +4.419] | no |

## 4. Study B — dev against calendar date, and half-year splits   [exploratory]

### Spearman of `dev` against calendar date, per clock

Date as its ordinal. Descriptive rank association; no p-value.

| clock | subset | n | Spearman ρ (dev vs date) |
|---|---|---|---|
| 10:00:59 | all | 245 | +0.2198 |
| 12:00:59 | all | 245 | +0.1618 |
| 14:00:59 | all | 246 | +0.1602 |
| 15:29:59 | all | 245 | +0.1117 |
| 10:00:59 | no-expiry | 223 | +0.2089 |
| 12:00:59 | no-expiry | 223 | +0.1424 |
| 14:00:59 | no-expiry | 224 | +0.1485 |
| 15:29:59 | no-expiry | 223 | +0.1323 |

### Q1 / Q4 / Q5 `rng_next` contrasts by half-year

Quintiles of `dev` are cut **within each half-year**, so a quintile is relative to its own period. Effect is that quintile minus the other four in the same half-year, in bp.

| half-year | clock | subset | quintile | n | sessions | effect (bp) | 95% CI | excl zero |
|---|---|---|---|---|---|---|---|---|
| Apr–Sep 2025 | 10:00:59 | all | Q1 | 25 | 25 | -1.286 | [-20.917, +24.186] | no |
| Apr–Sep 2025 | 10:00:59 | all | Q4 | 25 | 25 | +4.219 | [-14.458, +22.206] | no |
| Apr–Sep 2025 | 10:00:59 | all | Q5 | 25 | 25 | -12.177 | [-26.725, +2.930] | no |
| Apr–Sep 2025 | 12:00:59 | all | Q1 | 25 | 25 | -3.897 | [-23.508, +21.193] | no |
| Apr–Sep 2025 | 12:00:59 | all | Q4 | 25 | 25 | -10.534 | [-25.813, +6.978] | no |
| Apr–Sep 2025 | 12:00:59 | all | Q5 | 25 | 25 | -0.656 | [-16.707, +15.802] | no |
| Apr–Sep 2025 | 14:00:59 | all | Q1 | 25 | 25 | -3.516 | [-23.998, +21.587] | no |
| Apr–Sep 2025 | 14:00:59 | all | Q4 | 25 | 25 | +1.839 | [-13.839, +18.094] | no |
| Apr–Sep 2025 | 14:00:59 | all | Q5 | 25 | 25 | -15.008 | [-30.999, +1.631] | no |
| Apr–Sep 2025 | 15:29:59 | all | Q1 | 25 | 25 | +3.425 | [-17.533, +30.091] | no |
| Apr–Sep 2025 | 15:29:59 | all | Q4 | 25 | 25 | +6.300 | [-10.039, +22.662] | no |
| Apr–Sep 2025 | 15:29:59 | all | Q5 | 25 | 25 | +1.303 | [-19.604, +24.251] | no |
| Apr–Sep 2025 | 10:00:59 | no-expiry | Q1 | 23 | 23 | -2.359 | [-22.677, +23.525] | no |
| Apr–Sep 2025 | 10:00:59 | no-expiry | Q4 | 23 | 23 | +6.268 | [-12.996, +25.907] | no |
| Apr–Sep 2025 | 10:00:59 | no-expiry | Q5 | 23 | 23 | -9.674 | [-25.163, +7.146] | no |
| Apr–Sep 2025 | 12:00:59 | no-expiry | Q1 | 23 | 23 | -0.886 | [-21.514, +25.258] | no |
| Apr–Sep 2025 | 12:00:59 | no-expiry | Q4 | 23 | 23 | -10.561 | [-27.960, +7.191] | no |
| Apr–Sep 2025 | 12:00:59 | no-expiry | Q5 | 23 | 23 | +1.556 | [-15.522, +19.938] | no |
| Apr–Sep 2025 | 14:00:59 | no-expiry | Q1 | 23 | 23 | -0.073 | [-22.989, +28.173] | no |
| Apr–Sep 2025 | 14:00:59 | no-expiry | Q4 | 23 | 23 | +3.655 | [-13.231, +20.393] | no |
| Apr–Sep 2025 | 14:00:59 | no-expiry | Q5 | 23 | 23 | -12.246 | [-28.060, +4.565] | no |
| Apr–Sep 2025 | 15:29:59 | no-expiry | Q1 | 23 | 23 | +5.571 | [-16.388, +33.073] | no |
| Apr–Sep 2025 | 15:29:59 | no-expiry | Q4 | 23 | 23 | +7.699 | [-9.563, +25.460] | no |
| Apr–Sep 2025 | 15:29:59 | no-expiry | Q5 | 23 | 23 | -3.252 | [-23.188, +17.955] | no |
| Oct 2025–Mar 2026 | 10:00:59 | all | Q1 | 24 | 24 | +24.379 | [-0.224, +50.333] | no |
| Oct 2025–Mar 2026 | 10:00:59 | all | Q4 | 24 | 24 | -17.457 | [-33.945, +0.552] | no |
| Oct 2025–Mar 2026 | 10:00:59 | all | Q5 | 24 | 24 | -20.380 | [-34.408, -6.649] | yes |
| Oct 2025–Mar 2026 | 12:00:59 | all | Q1 | 25 | 25 | +45.644 | [+19.759, +77.801] | yes |
| Oct 2025–Mar 2026 | 12:00:59 | all | Q4 | 24 | 24 | -17.972 | [-33.721, -0.979] | yes |
| Oct 2025–Mar 2026 | 12:00:59 | all | Q5 | 24 | 24 | -20.469 | [-35.545, -6.081] | yes |
| Oct 2025–Mar 2026 | 14:00:59 | all | Q1 | 25 | 25 | +47.810 | [+21.310, +78.788] | yes |
| Oct 2025–Mar 2026 | 14:00:59 | all | Q4 | 24 | 24 | -16.165 | [-31.834, +1.525] | no |
| Oct 2025–Mar 2026 | 14:00:59 | all | Q5 | 25 | 25 | -21.576 | [-35.354, -7.185] | yes |
| Oct 2025–Mar 2026 | 15:29:59 | all | Q1 | 24 | 24 | +36.098 | [+12.458, +60.717] | yes |
| Oct 2025–Mar 2026 | 15:29:59 | all | Q4 | 24 | 24 | -12.061 | [-29.529, +6.564] | no |
| Oct 2025–Mar 2026 | 15:29:59 | all | Q5 | 24 | 24 | -12.647 | [-29.019, +4.778] | no |
| Oct 2025–Mar 2026 | 10:00:59 | no-expiry | Q1 | 22 | 22 | +19.258 | [-6.812, +47.375] | no |
| Oct 2025–Mar 2026 | 10:00:59 | no-expiry | Q4 | 22 | 22 | -18.343 | [-36.667, -0.596] | yes |
| Oct 2025–Mar 2026 | 10:00:59 | no-expiry | Q5 | 22 | 22 | -19.866 | [-34.821, -5.599] | yes |
| Oct 2025–Mar 2026 | 12:00:59 | no-expiry | Q1 | 22 | 22 | +46.836 | [+16.881, +80.611] | yes |
| Oct 2025–Mar 2026 | 12:00:59 | no-expiry | Q4 | 22 | 22 | -17.362 | [-34.775, -0.848] | yes |
| Oct 2025–Mar 2026 | 12:00:59 | no-expiry | Q5 | 22 | 22 | -20.229 | [-35.824, -4.655] | yes |
| Oct 2025–Mar 2026 | 14:00:59 | no-expiry | Q1 | 22 | 22 | +48.889 | [+17.465, +84.433] | yes |
| Oct 2025–Mar 2026 | 14:00:59 | no-expiry | Q4 | 22 | 22 | -14.659 | [-32.254, +2.336] | no |
| Oct 2025–Mar 2026 | 14:00:59 | no-expiry | Q5 | 22 | 22 | -21.766 | [-37.071, -6.403] | yes |
| Oct 2025–Mar 2026 | 15:29:59 | no-expiry | Q1 | 22 | 22 | +37.769 | [+12.579, +64.961] | yes |
| Oct 2025–Mar 2026 | 15:29:59 | no-expiry | Q4 | 22 | 22 | -4.240 | [-22.782, +17.303] | no |
| Oct 2025–Mar 2026 | 15:29:59 | no-expiry | Q5 | 22 | 22 | -15.605 | [-33.043, +2.809] | no |

---

*Exploration. No verdict. Read-only; no database write, no commit.*
