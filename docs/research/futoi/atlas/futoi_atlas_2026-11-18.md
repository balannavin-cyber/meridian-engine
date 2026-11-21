# Futures OI atlas — NIFTY, 2025-04-01 … 2026-03-30

Exploration. No verdict. Nothing here is a finding until confirmed once on unseen data.

| Field | Value |
|---|---|
| Window | 2025-04-01 … 2026-03-30, **NIFTY only**. Nothing after 2026-03-30 is read; the Stage 1 holdout stays sealed |
| Clock | vendor clock as-is (:59 stamps), no conversion between tables. The 15:30 bar is never used |
| Series | P = series-1 futures close · S = spot close · F = OI series 1+2+3 (None if any missing) · F1 = series-1 OI |
| Expiry days | futures expiry days and the session after are **flagged, not dropped**; every table is given with and without them |
| Intervals | session-clustered percentile bootstrap of a mean, 2,000 resamples, seed 20261118. **Descriptive** — an interval excluding zero is not a test result |
| Medians | point estimates **without** an interval (READINGS R11) |
| Sessions | 247 · 15-min windows 5928 · 30-min 2964 · 60-min 1482 · day rows 245 · basis rows 988 · walls 245 |

Readings that resolve every open choice are in `READINGS.md`; what this run takes on trust is in `NOT_VERIFIED.md`.

K1 ran as the gate for this document; its output is in `logs/checks_*.log` and in this run's own log.

Sessions excluded from Study D walls: 1.
- 2025-10-23 (walls would come from 2025-10-21) — prior tag-B bar is 14:45:59, not 15:29:59

---

## A1 — class anatomy over non-overlapping windows   [exploratory]

Windows of 15 / 30 / 60 minutes from 09:15, full grid windows only (24 / 12 / 6 per session; the ragged 15:15–15:29 tail is not a window). dP and dOI are measured start→end; the outcome starts at the window end. FLAT (a measured zero) and MISSING (uncomputable) are counted separately and never merged into a class.

Contrasts hold the **price sign fixed**: **LB vs SC** (both dP>0) and **SB vs LU** (both dP<0), so the difference isolates the sign of dOI rather than an up-window/down-window asymmetry. SC vs LB and LU vs SB are the same contrasts with the sign flipped and are not repeated.

### A1.0 Composition — every class counted, including FLAT and MISSING

| step | OI | subset | LB | SC | SB | LU | FLAT | MISSING | total |
|---|---|---|---|---|---|---|---|---|---|
| 15 | F | all | 1422 | 640 | 1625 | 544 | 21 | 1676 | 5928 |
| 15 | F | no-expiry | 1263 | 586 | 1436 | 509 | 20 | 1562 | 5376 |
| 15 | F1 | all | 1580 | 1299 | 1747 | 1244 | 38 | 20 | 5928 |
| 15 | F1 | no-expiry | 1463 | 1147 | 1628 | 1081 | 37 | 20 | 5376 |
| 30 | F | all | 720 | 301 | 840 | 243 | 11 | 849 | 2964 |
| 30 | F | no-expiry | 640 | 283 | 735 | 231 | 9 | 790 | 2688 |
| 30 | F1 | all | 783 | 666 | 903 | 585 | 17 | 10 | 2964 |
| 30 | F1 | no-expiry | 727 | 590 | 845 | 501 | 15 | 10 | 2688 |
| 60 | F | all | 384 | 146 | 438 | 98 | 2 | 414 | 1482 |
| 60 | F | no-expiry | 337 | 136 | 389 | 93 | 2 | 387 | 1344 |
| 60 | F1 | all | 398 | 343 | 459 | 270 | 6 | 6 | 1482 |
| 60 | F1 | no-expiry | 373 | 298 | 431 | 230 | 6 | 6 | 1344 |


### A1 step=15 min · OI=F · all windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 605 | 228 | rng60 | +2.006 bp | [-1.345, +5.306] | 34.777 vs 32.771 | difference |
| LB vs SC | to 11:30 | 605 | 228 | cont30 | +0.339 bp | [-2.256, +2.975] | -0.428 vs -0.767 | difference |
| LB vs SC | to 11:30 | 605 | 228 | hit30 | -0.005 rate | [-0.085, +0.073] | 0.469 vs 0.474 | difference |
| LB vs SC | 11:30-13:30 | 431 | 185 | rng60 | -0.476 bp | [-4.847, +3.339] | 32.157 vs 32.633 | difference |
| LB vs SC | 11:30-13:30 | 431 | 185 | cont30 | -0.580 bp | [-3.097, +1.775] | -0.062 vs 0.518 | difference |
| LB vs SC | 11:30-13:30 | 431 | 185 | hit30 | -0.015 rate | [-0.097, +0.065] | 0.466 vs 0.481 | difference |
| LB vs SC | after 13:30 | 386 | 198 | rng60 | -2.791 bp | [-6.937, +0.830] | 25.657 vs 28.448 | difference |
| LB vs SC | after 13:30 | 263 | 165 | cont30 | -0.701 bp | [-4.874, +3.594] | -1.525 vs -0.824 | difference |
| LB vs SC | after 13:30 | 263 | 165 | hit30 | -0.034 rate | [-0.131, +0.070] | 0.430 vs 0.464 | difference |
| LB vs SC | all day | 1422 | 246 | rng60 | +0.025 bp | [-2.655, +2.488] | 31.507 vs 31.482 | difference |
| LB vs SC | all day | 1299 | 242 | cont30 | -0.155 bp | [-1.833, +1.424] | -0.529 vs -0.374 | difference |
| LB vs SC | all day | 1299 | 242 | hit30 | -0.014 rate | [-0.065, +0.039] | 0.460 vs 0.474 | difference |
| SB vs LU | to 11:30 | 693 | 221 | rng60 | +0.137 bp | [-3.495, +3.729] | 35.634 vs 35.497 | difference |
| SB vs LU | to 11:30 | 693 | 221 | cont30 | +1.355 bp | [-2.206, +4.673] | 0.205 vs -1.150 | difference |
| SB vs LU | to 11:30 | 693 | 221 | hit30 | +0.013 rate | [-0.073, +0.093] | 0.496 vs 0.484 | difference |
| SB vs LU | 11:30-13:30 | 447 | 186 | rng60 | +0.491 bp | [-3.719, +4.491] | 32.774 vs 32.283 | difference |
| SB vs LU | 11:30-13:30 | 447 | 186 | cont30 | +2.292 bp | [-1.768, +6.375] | 0.310 vs -1.983 | difference |
| SB vs LU | 11:30-13:30 | 447 | 186 | hit30 | +0.118 rate | [+0.022, +0.214] | 0.488 vs 0.370 | difference |
| SB vs LU | after 13:30 | 485 | 200 | rng60 | +2.594 bp | [-1.005, +6.132] | 26.672 vs 24.078 | difference |
| SB vs LU | after 13:30 | 315 | 170 | cont30 | +3.813 bp | [+0.384, +7.341] | 2.006 vs -1.807 | difference |
| SB vs LU | after 13:30 | 315 | 170 | hit30 | +0.081 rate | [-0.029, +0.188] | 0.581 vs 0.500 | difference |
| SB vs LU | all day | 1625 | 242 | rng60 | +1.216 bp | [-1.245, +3.678] | 32.172 vs 30.956 | difference |
| SB vs LU | all day | 1455 | 240 | cont30 | +2.193 bp | [+0.042, +4.108] | 0.627 vs -1.566 | difference |
| SB vs LU | all day | 1455 | 240 | hit30 | +0.061 rate | [+0.009, +0.115] | 0.512 vs 0.451 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F · all windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 535 | 205 | rng60 | +1.352 bp | [-2.392, +5.038] | 34.549 vs 33.197 | difference |
| LB vs SC | to 11:30 | 535 | 205 | cont30 | +0.692 bp | [-2.230, +3.485] | -0.505 vs -1.196 | difference |
| LB vs SC | to 11:30 | 535 | 205 | hit30 | +0.009 rate | [-0.077, +0.089] | 0.469 vs 0.460 | difference |
| LB vs SC | 11:30-13:30 | 378 | 165 | rng60 | -0.564 bp | [-4.862, +3.746] | 31.871 vs 32.435 | difference |
| LB vs SC | 11:30-13:30 | 378 | 165 | cont30 | -0.252 bp | [-3.257, +2.416] | -0.082 vs 0.170 | difference |
| LB vs SC | 11:30-13:30 | 378 | 165 | hit30 | +0.003 rate | [-0.084, +0.089] | 0.458 vs 0.455 | difference |
| LB vs SC | after 13:30 | 350 | 180 | rng60 | -3.694 bp | [-8.103, +0.161] | 25.141 vs 28.834 | difference |
| LB vs SC | after 13:30 | 236 | 149 | cont30 | -0.722 bp | [-5.188, +3.771] | -1.812 vs -1.090 | difference |
| LB vs SC | after 13:30 | 236 | 149 | hit30 | -0.029 rate | [-0.131, +0.074] | 0.424 vs 0.453 | difference |
| LB vs SC | all day | 1263 | 223 | rng60 | -0.584 bp | [-3.333, +2.105] | 31.140 vs 31.724 | difference |
| LB vs SC | all day | 1149 | 219 | cont30 | +0.117 bp | [-1.688, +1.790] | -0.634 vs -0.751 | difference |
| LB vs SC | all day | 1149 | 219 | hit30 | -0.001 rate | [-0.053, +0.051] | 0.456 vs 0.457 | difference |
| SB vs LU | to 11:30 | 611 | 200 | rng60 | -0.726 bp | [-4.214, +2.703] | 34.732 vs 35.457 | difference |
| SB vs LU | to 11:30 | 611 | 200 | cont30 | +0.504 bp | [-2.949, +4.022] | -0.544 vs -1.048 | difference |
| SB vs LU | to 11:30 | 611 | 200 | hit30 | -0.001 rate | [-0.087, +0.084] | 0.484 vs 0.486 | difference |
| SB vs LU | 11:30-13:30 | 393 | 165 | rng60 | +0.279 bp | [-4.078, +4.263] | 32.895 vs 32.617 | difference |
| SB vs LU | 11:30-13:30 | 393 | 165 | cont30 | +2.657 bp | [-1.447, +6.681] | 0.730 vs -1.927 | difference |
| SB vs LU | 11:30-13:30 | 393 | 165 | hit30 | +0.126 rate | [+0.030, +0.218] | 0.496 vs 0.370 | difference |
| SB vs LU | after 13:30 | 432 | 179 | rng60 | +2.960 bp | [-0.995, +6.615] | 26.463 vs 23.503 | difference |
| SB vs LU | after 13:30 | 283 | 151 | cont30 | +4.249 bp | [+0.719, +7.854] | 1.610 vs -2.639 | difference |
| SB vs LU | after 13:30 | 283 | 151 | hit30 | +0.085 rate | [-0.034, +0.205] | 0.569 vs 0.484 | difference |
| SB vs LU | all day | 1436 | 219 | rng60 | +0.739 bp | [-1.737, +3.137] | 31.742 vs 31.002 | difference |
| SB vs LU | all day | 1287 | 217 | cont30 | +1.989 bp | [-0.158, +4.046] | 0.319 vs -1.670 | difference |
| SB vs LU | all day | 1287 | 217 | hit30 | +0.059 rate | [+0.006, +0.116] | 0.507 vs 0.448 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F · strong windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 187 | 114 | rng60 | +5.707 bp | [-0.430, +11.801] | 40.803 vs 35.096 | difference |
| LB vs SC | to 11:30 | 187 | 114 | cont30 | +0.928 bp | [-4.330, +6.442] | -0.698 vs -1.626 | difference |
| LB vs SC | to 11:30 | 187 | 114 | hit30 | +0.025 rate | [-0.132, +0.188] | 0.439 vs 0.414 | difference |
| LB vs SC | 11:30-13:30 | 138 | 84 | rng60 | +1.933 bp | [-5.935, +9.546] | 38.903 vs 36.970 | difference |
| LB vs SC | 11:30-13:30 | 138 | 84 | cont30 | -4.319 bp | [-10.072, +1.086] | -0.350 vs 3.969 | difference |
| LB vs SC | 11:30-13:30 | 138 | 84 | hit30 | -0.126 rate | [-0.294, +0.038] | 0.428 vs 0.553 | difference |
| LB vs SC | after 13:30 | 112 | 74 | rng60 | -4.675 bp | [-11.823, +2.089] | 28.837 vs 33.512 | difference |
| LB vs SC | after 13:30 | 75 | 55 | cont30 | -2.928 bp | [-9.587, +3.868] | -0.628 vs 2.300 | difference |
| LB vs SC | after 13:30 | 75 | 55 | hit30 | +0.011 rate | [-0.188, +0.206] | 0.480 vs 0.469 | difference |
| LB vs SC | all day | 437 | 152 | rng60 | +1.917 bp | [-2.785, +6.430] | 37.136 vs 35.219 | difference |
| LB vs SC | all day | 400 | 149 | cont30 | -1.775 bp | [-5.235, +1.938] | -0.565 vs 1.210 | difference |
| LB vs SC | all day | 400 | 149 | hit30 | -0.032 rate | [-0.135, +0.073] | 0.443 vs 0.474 | difference |
| SB vs LU | to 11:30 | 233 | 120 | rng60 | -4.376 bp | [-13.643, +4.830] | 40.916 vs 45.292 | difference |
| SB vs LU | to 11:30 | 233 | 120 | cont30 | +5.070 bp | [-3.319, +13.296] | -0.046 vs -5.116 | difference |
| SB vs LU | to 11:30 | 233 | 120 | hit30 | +0.043 rate | [-0.130, +0.223] | 0.481 vs 0.438 | difference |
| SB vs LU | 11:30-13:30 | 153 | 83 | rng60 | -2.169 bp | [-14.750, +8.572] | 38.948 vs 41.117 | difference |
| SB vs LU | 11:30-13:30 | 153 | 83 | cont30 | +2.338 bp | [-5.689, +13.567] | 2.423 vs 0.085 | difference |
| SB vs LU | 11:30-13:30 | 153 | 83 | hit30 | +0.020 rate | [-0.161, +0.220] | 0.556 vs 0.536 | difference |
| SB vs LU | after 13:30 | 169 | 104 | rng60 | +2.944 bp | [-4.183, +9.428] | 31.239 vs 28.296 | difference |
| SB vs LU | after 13:30 | 105 | 78 | cont30 | +8.663 bp | [+1.329, +15.917] | 3.912 vs -4.750 | difference |
| SB vs LU | after 13:30 | 105 | 78 | hit30 | +0.165 rate | [-0.068, +0.389] | 0.619 vs 0.455 | difference |
| SB vs LU | all day | 555 | 173 | rng60 | -0.474 bp | [-5.911, +5.274] | 37.427 vs 37.901 | difference |
| SB vs LU | all day | 491 | 164 | cont30 | +4.812 bp | [-0.023, +10.276] | 1.570 vs -3.242 | difference |
| SB vs LU | all day | 491 | 164 | hit30 | +0.058 rate | [-0.050, +0.170] | 0.534 vs 0.476 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F · strong windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 164 | 102 | rng60 | +4.865 bp | [-2.124, +11.532] | 40.430 vs 35.566 | difference |
| LB vs SC | to 11:30 | 164 | 102 | cont30 | +1.484 bp | [-3.984, +7.321] | -1.062 vs -2.546 | difference |
| LB vs SC | to 11:30 | 164 | 102 | hit30 | +0.042 rate | [-0.118, +0.214] | 0.427 vs 0.385 | difference |
| LB vs SC | 11:30-13:30 | 119 | 74 | rng60 | +1.784 bp | [-8.247, +10.859] | 38.812 vs 37.027 | difference |
| LB vs SC | 11:30-13:30 | 119 | 74 | cont30 | -5.094 bp | [-11.612, +0.973] | 0.191 vs 5.285 | difference |
| LB vs SC | 11:30-13:30 | 119 | 74 | hit30 | -0.142 rate | [-0.315, +0.040] | 0.437 vs 0.579 | difference |
| LB vs SC | after 13:30 | 95 | 64 | rng60 | -5.102 bp | [-12.243, +2.414] | 28.798 vs 33.900 | difference |
| LB vs SC | after 13:30 | 64 | 46 | cont30 | -3.823 bp | [-10.960, +3.594] | -1.569 vs 2.255 | difference |
| LB vs SC | after 13:30 | 64 | 46 | hit30 | -0.029 rate | [-0.254, +0.181] | 0.438 vs 0.467 | difference |
| LB vs SC | all day | 378 | 136 | rng60 | +1.529 bp | [-3.519, +6.748] | 36.997 vs 35.468 | difference |
| LB vs SC | all day | 347 | 133 | cont30 | -1.860 bp | [-5.491, +1.863] | -0.726 vs 1.134 | difference |
| LB vs SC | all day | 347 | 133 | hit30 | -0.034 rate | [-0.147, +0.078] | 0.432 vs 0.467 | difference |
| SB vs LU | to 11:30 | 193 | 103 | rng60 | -5.951 bp | [-15.697, +4.237] | 39.785 vs 45.737 | difference |
| SB vs LU | to 11:30 | 193 | 103 | cont30 | +3.886 bp | [-4.792, +12.678] | -1.736 vs -5.622 | difference |
| SB vs LU | to 11:30 | 193 | 103 | hit30 | +0.003 rate | [-0.189, +0.195] | 0.451 vs 0.448 | difference |
| SB vs LU | 11:30-13:30 | 132 | 73 | rng60 | -1.864 bp | [-15.512, +9.810] | 39.362 vs 41.227 | difference |
| SB vs LU | 11:30-13:30 | 132 | 73 | cont30 | +3.016 bp | [-5.422, +15.338] | 2.507 vs -0.509 | difference |
| SB vs LU | 11:30-13:30 | 132 | 73 | hit30 | +0.053 rate | [-0.134, +0.269] | 0.553 vs 0.500 | difference |
| SB vs LU | after 13:30 | 144 | 88 | rng60 | +5.807 bp | [-1.126, +12.297] | 31.291 vs 25.484 | difference |
| SB vs LU | after 13:30 | 88 | 66 | cont30 | +9.612 bp | [+3.044, +16.094] | 3.013 vs -6.599 | difference |
| SB vs LU | after 13:30 | 88 | 66 | hit30 | +0.158 rate | [-0.100, +0.417] | 0.602 vs 0.444 | difference |
| SB vs LU | all day | 469 | 152 | rng60 | -0.151 bp | [-6.224, +6.359] | 37.058 vs 37.209 | difference |
| SB vs LU | all day | 413 | 145 | cont30 | +4.674 bp | [-0.287, +10.694] | 0.632 vs -4.042 | difference |
| SB vs LU | all day | 413 | 145 | hit30 | +0.050 rate | [-0.061, +0.173] | 0.516 vs 0.466 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F1 · all windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 592 | 222 | rng60 | +2.055 bp | [-0.523, +4.550] | 33.732 vs 31.677 | difference |
| LB vs SC | to 11:30 | 592 | 222 | cont30 | +0.095 bp | [-1.932, +2.209] | -0.532 vs -0.627 | difference |
| LB vs SC | to 11:30 | 592 | 222 | hit30 | -0.033 rate | [-0.100, +0.030] | 0.454 vs 0.487 | difference |
| LB vs SC | 11:30-13:30 | 551 | 211 | rng60 | +2.067 bp | [-0.833, +5.137] | 29.813 vs 27.745 | difference |
| LB vs SC | 11:30-13:30 | 551 | 211 | cont30 | -0.300 bp | [-2.006, +1.288] | 0.045 vs 0.344 | difference |
| LB vs SC | 11:30-13:30 | 551 | 211 | hit30 | -0.011 rate | [-0.074, +0.049] | 0.483 vs 0.493 | difference |
| LB vs SC | after 13:30 | 437 | 202 | rng60 | -0.491 bp | [-2.912, +1.878] | 24.885 vs 25.376 | difference |
| LB vs SC | after 13:30 | 305 | 177 | cont30 | -0.309 bp | [-2.786, +2.237] | -1.255 vs -0.946 | difference |
| LB vs SC | after 13:30 | 305 | 177 | hit30 | +0.012 rate | [-0.070, +0.083] | 0.449 vs 0.437 | difference |
| LB vs SC | all day | 1580 | 245 | rng60 | +1.407 bp | [-0.342, +3.219] | 29.918 vs 28.512 | difference |
| LB vs SC | all day | 1448 | 245 | cont30 | -0.125 bp | [-1.352, +1.155] | -0.465 vs -0.340 | difference |
| LB vs SC | all day | 1448 | 245 | hit30 | -0.014 rate | [-0.053, +0.027] | 0.464 vs 0.478 | difference |
| SB vs LU | to 11:30 | 682 | 223 | rng60 | +0.741 bp | [-2.209, +3.637] | 33.605 vs 32.864 | difference |
| SB vs LU | to 11:30 | 682 | 223 | cont30 | -0.291 bp | [-2.592, +2.081] | -0.199 vs 0.092 | difference |
| SB vs LU | to 11:30 | 682 | 223 | hit30 | -0.037 rate | [-0.096, +0.019] | 0.484 vs 0.521 | difference |
| SB vs LU | 11:30-13:30 | 559 | 214 | rng60 | +2.505 bp | [-0.041, +5.276] | 30.637 vs 28.133 | difference |
| SB vs LU | 11:30-13:30 | 559 | 214 | cont30 | +0.766 bp | [-1.448, +2.964] | 0.458 vs -0.308 | difference |
| SB vs LU | 11:30-13:30 | 559 | 214 | hit30 | +0.029 rate | [-0.042, +0.094] | 0.479 vs 0.451 | difference |
| SB vs LU | after 13:30 | 506 | 208 | rng60 | +2.230 bp | [-0.628, +4.919] | 26.075 vs 23.845 | difference |
| SB vs LU | after 13:30 | 362 | 190 | cont30 | +1.666 bp | [-0.705, +4.017] | 0.956 vs -0.710 | difference |
| SB vs LU | after 13:30 | 362 | 190 | hit30 | +0.036 rate | [-0.047, +0.112] | 0.536 vs 0.500 | difference |
| SB vs LU | all day | 1747 | 246 | rng60 | +2.031 bp | [+0.161, +3.902] | 30.475 vs 28.443 | difference |
| SB vs LU | all day | 1603 | 246 | cont30 | +0.540 bp | [-0.912, +1.939] | 0.291 vs -0.250 | difference |
| SB vs LU | all day | 1603 | 246 | hit30 | +0.003 rate | [-0.035, +0.043] | 0.494 vs 0.491 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F1 · all windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 547 | 206 | rng60 | +2.560 bp | [-0.124, +5.309] | 33.801 vs 31.241 | difference |
| LB vs SC | to 11:30 | 547 | 206 | cont30 | +0.627 bp | [-1.589, +2.798] | -0.587 vs -1.214 | difference |
| LB vs SC | to 11:30 | 547 | 206 | hit30 | -0.017 rate | [-0.088, +0.055] | 0.453 vs 0.470 | difference |
| LB vs SC | 11:30-13:30 | 505 | 193 | rng60 | +2.655 bp | [-0.512, +5.851] | 29.715 vs 27.061 | difference |
| LB vs SC | 11:30-13:30 | 505 | 193 | cont30 | -0.492 bp | [-2.129, +1.180] | 0.006 vs 0.498 | difference |
| LB vs SC | 11:30-13:30 | 505 | 193 | hit30 | -0.016 rate | [-0.083, +0.049] | 0.475 vs 0.491 | difference |
| LB vs SC | after 13:30 | 411 | 188 | rng60 | -0.725 bp | [-3.304, +1.574] | 24.557 vs 25.282 | difference |
| LB vs SC | after 13:30 | 283 | 163 | cont30 | -0.491 bp | [-2.865, +2.005] | -1.468 vs -0.977 | difference |
| LB vs SC | after 13:30 | 283 | 163 | hit30 | +0.003 rate | [-0.077, +0.085] | 0.442 vs 0.438 | difference |
| LB vs SC | all day | 1463 | 223 | rng60 | +1.719 bp | [-0.163, +3.503] | 29.794 vs 28.074 | difference |
| LB vs SC | all day | 1335 | 223 | cont30 | -0.028 bp | [-1.329, +1.316] | -0.550 vs -0.521 | difference |
| LB vs SC | all day | 1335 | 223 | hit30 | -0.011 rate | [-0.054, +0.032] | 0.459 vs 0.470 | difference |
| SB vs LU | to 11:30 | 633 | 204 | rng60 | +0.599 bp | [-2.442, +3.494] | 32.875 vs 32.276 | difference |
| SB vs LU | to 11:30 | 633 | 204 | cont30 | -0.708 bp | [-3.138, +1.608] | -0.766 vs -0.059 | difference |
| SB vs LU | to 11:30 | 633 | 204 | hit30 | -0.029 rate | [-0.093, +0.035] | 0.480 vs 0.509 | difference |
| SB vs LU | 11:30-13:30 | 521 | 193 | rng60 | +2.815 bp | [+0.041, +5.755] | 30.571 vs 27.756 | difference |
| SB vs LU | 11:30-13:30 | 521 | 193 | cont30 | +0.923 bp | [-1.485, +3.258] | 0.701 vs -0.222 | difference |
| SB vs LU | 11:30-13:30 | 521 | 193 | hit30 | +0.054 rate | [-0.014, +0.124] | 0.489 vs 0.436 | difference |
| SB vs LU | after 13:30 | 474 | 194 | rng60 | +2.920 bp | [+0.050, +5.826] | 26.073 vs 23.152 | difference |
| SB vs LU | after 13:30 | 338 | 176 | cont30 | +2.064 bp | [-0.279, +4.643] | 0.731 vs -1.332 | difference |
| SB vs LU | after 13:30 | 338 | 176 | hit30 | +0.034 rate | [-0.048, +0.119] | 0.524 vs 0.490 | difference |
| SB vs LU | all day | 1628 | 223 | rng60 | +2.214 bp | [+0.326, +4.031] | 30.157 vs 27.943 | difference |
| SB vs LU | all day | 1492 | 223 | cont30 | +0.513 bp | [-0.939, +2.015] | 0.085 vs -0.428 | difference |
| SB vs LU | all day | 1492 | 223 | hit30 | +0.015 rate | [-0.024, +0.056] | 0.493 vs 0.478 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F1 · strong windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 167 | 111 | rng60 | +1.041 bp | [-4.578, +6.352] | 39.595 vs 38.554 | difference |
| LB vs SC | to 11:30 | 167 | 111 | cont30 | -0.982 bp | [-5.295, +3.567] | -0.794 vs 0.188 | difference |
| LB vs SC | to 11:30 | 167 | 111 | hit30 | -0.049 rate | [-0.170, +0.077] | 0.443 vs 0.492 | difference |
| LB vs SC | 11:30-13:30 | 145 | 92 | rng60 | +1.746 bp | [-4.904, +7.759] | 35.435 vs 33.689 | difference |
| LB vs SC | 11:30-13:30 | 145 | 92 | cont30 | -1.008 bp | [-4.799, +2.660] | 1.468 vs 2.476 | difference |
| LB vs SC | 11:30-13:30 | 145 | 92 | hit30 | -0.006 rate | [-0.128, +0.108] | 0.510 vs 0.517 | difference |
| LB vs SC | after 13:30 | 119 | 85 | rng60 | -1.556 bp | [-6.851, +3.601] | 29.996 vs 31.552 | difference |
| LB vs SC | after 13:30 | 83 | 62 | cont30 | -2.445 bp | [-7.757, +2.817] | -1.971 vs 0.475 | difference |
| LB vs SC | after 13:30 | 83 | 62 | hit30 | -0.009 rate | [-0.154, +0.139] | 0.410 vs 0.419 | difference |
| LB vs SC | all day | 431 | 175 | rng60 | +0.749 bp | [-3.191, +4.271] | 35.545 vs 34.796 | difference |
| LB vs SC | all day | 395 | 169 | cont30 | -1.284 bp | [-4.110, +1.435] | -0.211 vs 1.073 | difference |
| LB vs SC | all day | 395 | 169 | hit30 | -0.021 rate | [-0.099, +0.054] | 0.461 vs 0.482 | difference |
| SB vs LU | to 11:30 | 206 | 119 | rng60 | +0.059 bp | [-6.432, +6.740] | 39.642 vs 39.583 | difference |
| SB vs LU | to 11:30 | 206 | 119 | cont30 | +2.186 bp | [-2.531, +7.293] | -0.045 vs -2.231 | difference |
| SB vs LU | to 11:30 | 206 | 119 | hit30 | -0.063 rate | [-0.182, +0.057] | 0.466 vs 0.529 | difference |
| SB vs LU | 11:30-13:30 | 170 | 105 | rng60 | -1.897 bp | [-7.438, +3.634] | 36.559 vs 38.456 | difference |
| SB vs LU | 11:30-13:30 | 170 | 105 | cont30 | +1.891 bp | [-4.540, +7.801] | 2.136 vs 0.245 | difference |
| SB vs LU | 11:30-13:30 | 170 | 105 | hit30 | +0.064 rate | [-0.058, +0.194] | 0.529 vs 0.465 | difference |
| SB vs LU | after 13:30 | 144 | 99 | rng60 | +1.387 bp | [-4.834, +7.197] | 31.875 vs 30.488 | difference |
| SB vs LU | after 13:30 | 99 | 76 | cont30 | -0.104 bp | [-5.653, +5.629] | 0.784 vs 0.888 | difference |
| SB vs LU | after 13:30 | 99 | 76 | hit30 | -0.025 rate | [-0.181, +0.133] | 0.515 vs 0.541 | difference |
| SB vs LU | all day | 520 | 186 | rng60 | +0.366 bp | [-3.351, +4.120] | 36.483 vs 36.117 | difference |
| SB vs LU | all day | 475 | 178 | cont30 | +1.416 bp | [-1.923, +4.775] | 0.909 vs -0.507 | difference |
| SB vs LU | all day | 475 | 178 | hit30 | -0.010 rate | [-0.087, +0.063] | 0.499 vs 0.509 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=15 min · OI=F1 · strong windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 158 | 105 | rng60 | +1.356 bp | [-4.895, +7.424] | 39.725 vs 38.369 | difference |
| LB vs SC | to 11:30 | 158 | 105 | cont30 | -0.439 bp | [-5.026, +4.170] | -0.843 vs -0.404 | difference |
| LB vs SC | to 11:30 | 158 | 105 | hit30 | -0.040 rate | [-0.165, +0.089] | 0.437 vs 0.477 | difference |
| LB vs SC | 11:30-13:30 | 133 | 85 | rng60 | +1.823 bp | [-5.691, +8.608] | 35.552 vs 33.729 | difference |
| LB vs SC | 11:30-13:30 | 133 | 85 | cont30 | -1.045 bp | [-4.876, +2.702] | 1.760 vs 2.805 | difference |
| LB vs SC | 11:30-13:30 | 133 | 85 | hit30 | +0.001 rate | [-0.127, +0.130] | 0.511 vs 0.510 | difference |
| LB vs SC | after 13:30 | 113 | 80 | rng60 | -2.303 bp | [-8.350, +3.117] | 29.990 vs 32.292 | difference |
| LB vs SC | after 13:30 | 78 | 57 | cont30 | -3.256 bp | [-8.627, +2.168] | -2.007 vs 1.249 | difference |
| LB vs SC | after 13:30 | 78 | 57 | hit30 | -0.042 rate | [-0.199, +0.106] | 0.385 vs 0.427 | difference |
| LB vs SC | all day | 404 | 163 | rng60 | +0.699 bp | [-3.548, +4.729] | 35.628 vs 34.930 | difference |
| LB vs SC | all day | 369 | 157 | cont30 | -1.324 bp | [-4.265, +1.592] | -0.151 vs 1.173 | difference |
| LB vs SC | all day | 369 | 157 | hit30 | -0.023 rate | [-0.105, +0.057] | 0.453 vs 0.475 | difference |
| SB vs LU | to 11:30 | 184 | 107 | rng60 | -1.087 bp | [-7.828, +5.861] | 38.676 vs 39.763 | difference |
| SB vs LU | to 11:30 | 184 | 107 | cont30 | +0.969 bp | [-3.650, +5.749] | -1.628 vs -2.597 | difference |
| SB vs LU | to 11:30 | 184 | 107 | hit30 | -0.050 rate | [-0.171, +0.073] | 0.457 vs 0.506 | difference |
| SB vs LU | 11:30-13:30 | 156 | 95 | rng60 | -0.706 bp | [-6.937, +5.355] | 37.372 vs 38.078 | difference |
| SB vs LU | 11:30-13:30 | 156 | 95 | cont30 | +2.490 bp | [-4.702, +9.353] | 2.528 vs 0.039 | difference |
| SB vs LU | 11:30-13:30 | 156 | 95 | hit30 | +0.090 rate | [-0.036, +0.221] | 0.538 vs 0.448 | difference |
| SB vs LU | after 13:30 | 137 | 93 | rng60 | +3.123 bp | [-3.339, +9.159] | 31.908 vs 28.786 | difference |
| SB vs LU | after 13:30 | 94 | 72 | cont30 | +2.338 bp | [-3.110, +7.773] | 0.759 vs -1.579 | difference |
| SB vs LU | after 13:30 | 94 | 72 | hit30 | +0.011 rate | [-0.156, +0.177] | 0.511 vs 0.500 | difference |
| SB vs LU | all day | 477 | 171 | rng60 | +0.587 bp | [-3.256, +4.500] | 36.306 vs 35.719 | difference |
| SB vs LU | all day | 434 | 163 | cont30 | +1.711 bp | [-1.994, +5.370] | 0.383 vs -1.328 | difference |
| SB vs LU | all day | 434 | 163 | hit30 | +0.016 rate | [-0.060, +0.092] | 0.498 vs 0.482 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F · all windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 297 | 181 | rng60 | +2.587 bp | [-1.523, +6.623] | 34.671 vs 32.084 | difference |
| LB vs SC | to 11:30 | 297 | 181 | cont30 | +0.594 bp | [-2.500, +3.878] | 0.420 vs -0.174 | difference |
| LB vs SC | to 11:30 | 297 | 181 | hit30 | +0.002 rate | [-0.102, +0.102] | 0.502 vs 0.500 | difference |
| LB vs SC | 11:30-13:30 | 213 | 139 | rng60 | +2.978 bp | [-3.841, +8.563] | 32.788 vs 29.810 | difference |
| LB vs SC | 11:30-13:30 | 213 | 139 | cont30 | -3.660 bp | [-7.885, +0.052] | -0.404 vs 3.256 | difference |
| LB vs SC | 11:30-13:30 | 213 | 139 | hit30 | -0.040 rate | [-0.158, +0.081] | 0.493 vs 0.533 | difference |
| LB vs SC | after 13:30 | 210 | 147 | rng60 | -0.514 bp | [-5.964, +4.511] | 24.493 vs 25.007 | difference |
| LB vs SC | after 13:30 | 153 | 121 | cont30 | +0.416 bp | [-5.630, +6.412] | -2.600 vs -3.016 | difference |
| LB vs SC | after 13:30 | 153 | 121 | hit30 | -0.073 rate | [-0.220, +0.075] | 0.379 vs 0.452 | difference |
| LB vs SC | all day | 720 | 230 | rng60 | +1.787 bp | [-1.514, +4.908] | 31.146 vs 29.359 | difference |
| LB vs SC | all day | 663 | 229 | cont30 | -0.848 bp | [-3.508, +1.588] | -0.541 vs 0.306 | difference |
| LB vs SC | all day | 663 | 229 | hit30 | -0.029 rate | [-0.102, +0.044] | 0.471 vs 0.500 | difference |
| SB vs LU | to 11:30 | 323 | 175 | rng60 | +3.240 bp | [-1.472, +7.945] | 35.385 vs 32.145 | difference |
| SB vs LU | to 11:30 | 323 | 175 | cont30 | -0.016 bp | [-4.259, +3.945] | 0.863 vs 0.879 | difference |
| SB vs LU | to 11:30 | 323 | 175 | hit30 | +0.123 rate | [+0.006, +0.238] | 0.533 vs 0.409 | difference |
| SB vs LU | 11:30-13:30 | 236 | 139 | rng60 | -2.569 bp | [-9.334, +3.856] | 32.156 vs 34.725 | difference |
| SB vs LU | 11:30-13:30 | 236 | 139 | cont30 | +0.551 bp | [-4.153, +5.798] | 0.202 vs -0.349 | difference |
| SB vs LU | 11:30-13:30 | 236 | 139 | hit30 | +0.035 rate | [-0.100, +0.169] | 0.462 vs 0.426 | difference |
| SB vs LU | after 13:30 | 281 | 166 | rng60 | -1.506 bp | [-8.506, +4.683] | 25.850 vs 27.356 | difference |
| SB vs LU | after 13:30 | 191 | 138 | cont30 | +3.519 bp | [-1.140, +8.332] | 2.023 vs -1.497 | difference |
| SB vs LU | after 13:30 | 191 | 138 | hit30 | +0.028 rate | [-0.107, +0.164] | 0.545 vs 0.516 | difference |
| SB vs LU | all day | 840 | 234 | rng60 | +0.136 bp | [-3.472, +3.345] | 31.288 vs 31.152 | difference |
| SB vs LU | all day | 750 | 231 | cont30 | +1.130 bp | [-1.712, +3.810] | 0.950 vs -0.180 | difference |
| SB vs LU | all day | 750 | 231 | hit30 | +0.068 rate | [-0.010, +0.145] | 0.513 vs 0.445 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F · all windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 269 | 164 | rng60 | +1.880 bp | [-2.642, +5.936] | 34.336 vs 32.456 | difference |
| LB vs SC | to 11:30 | 269 | 164 | cont30 | +1.424 bp | [-1.837, +4.728] | 0.874 vs -0.551 | difference |
| LB vs SC | to 11:30 | 269 | 164 | hit30 | +0.010 rate | [-0.100, +0.122] | 0.506 vs 0.496 | difference |
| LB vs SC | 11:30-13:30 | 182 | 122 | rng60 | +2.636 bp | [-4.346, +8.589] | 32.420 vs 29.784 | difference |
| LB vs SC | 11:30-13:30 | 182 | 122 | cont30 | -3.789 bp | [-8.119, +0.464] | -0.993 vs 2.796 | difference |
| LB vs SC | 11:30-13:30 | 182 | 122 | hit30 | -0.039 rate | [-0.162, +0.084] | 0.467 vs 0.506 | difference |
| LB vs SC | after 13:30 | 189 | 133 | rng60 | -0.144 bp | [-5.889, +5.071] | 24.824 vs 24.968 | difference |
| LB vs SC | after 13:30 | 139 | 110 | cont30 | -0.557 bp | [-6.749, +6.024] | -3.105 vs -2.547 | difference |
| LB vs SC | after 13:30 | 139 | 110 | hit30 | -0.099 rate | [-0.255, +0.052] | 0.367 vs 0.466 | difference |
| LB vs SC | all day | 640 | 208 | rng60 | +1.453 bp | [-2.136, +4.858] | 30.982 vs 29.529 | difference |
| LB vs SC | all day | 590 | 207 | cont30 | -0.712 bp | [-3.394, +1.877] | -0.639 vs 0.072 | difference |
| LB vs SC | all day | 590 | 207 | hit30 | -0.031 rate | [-0.108, +0.042] | 0.461 vs 0.492 | difference |
| SB vs LU | to 11:30 | 278 | 155 | rng60 | +2.972 bp | [-1.902, +7.823] | 34.783 vs 31.811 | difference |
| SB vs LU | to 11:30 | 278 | 155 | cont30 | -0.702 bp | [-4.889, +3.393] | 0.428 vs 1.130 | difference |
| SB vs LU | to 11:30 | 278 | 155 | hit30 | +0.103 rate | [-0.013, +0.224] | 0.522 vs 0.419 | difference |
| SB vs LU | 11:30-13:30 | 212 | 123 | rng60 | -2.419 bp | [-9.202, +4.561] | 32.270 vs 34.689 | difference |
| SB vs LU | 11:30-13:30 | 212 | 123 | cont30 | +0.389 bp | [-4.475, +5.521] | 0.000 vs -0.389 | difference |
| SB vs LU | 11:30-13:30 | 212 | 123 | hit30 | +0.038 rate | [-0.099, +0.179] | 0.462 vs 0.424 | difference |
| SB vs LU | after 13:30 | 245 | 147 | rng60 | -0.804 bp | [-8.155, +5.860] | 25.471 vs 26.275 | difference |
| SB vs LU | after 13:30 | 168 | 123 | cont30 | +4.690 bp | [-0.213, +9.516] | 2.423 vs -2.266 | difference |
| SB vs LU | after 13:30 | 168 | 123 | hit30 | +0.048 rate | [-0.104, +0.197] | 0.548 vs 0.500 | difference |
| SB vs LU | all day | 735 | 212 | rng60 | +0.215 bp | [-3.520, +3.698] | 30.954 vs 30.740 | difference |
| SB vs LU | all day | 658 | 209 | cont30 | +1.047 bp | [-1.772, +3.900] | 0.800 vs -0.247 | difference |
| SB vs LU | all day | 658 | 209 | hit30 | +0.067 rate | [-0.008, +0.148] | 0.509 vs 0.442 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F · strong windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 81 | 63 | rng60 | +0.854 bp | [-11.861, +12.651] | 39.916 vs 39.062 | difference |
| LB vs SC | to 11:30 | 81 | 63 | cont30 | +4.439 bp | [-5.589, +15.083] | -1.175 vs -5.614 | difference |
| LB vs SC | to 11:30 | 81 | 63 | hit30 | +0.007 rate | [-0.236, +0.250] | 0.457 vs 0.450 | difference |
| LB vs SC | 11:30-13:30 | 64 | 53 | rng60 | +4.005 bp | [-6.173, +13.208] | 37.481 vs 33.476 | difference |
| LB vs SC | 11:30-13:30 | 64 | 53 | cont30 | -4.916 bp | [-13.435, +2.012] | -0.905 vs 4.011 | difference |
| LB vs SC | 11:30-13:30 | 64 | 53 | hit30 | +0.019 rate | [-0.246, +0.268] | 0.469 vs 0.450 | difference |
| LB vs SC | after 13:30 | 64 | 53 | rng60 | -2.252 bp | [-13.046, +7.965] | 30.646 vs 32.898 | difference |
| LB vs SC | after 13:30 | 50 | 44 | cont30 | -3.743 bp | [-15.165, +6.774] | -2.652 vs 1.092 | difference |
| LB vs SC | after 13:30 | 50 | 44 | hit30 | -0.158 rate | [-0.467, +0.142] | 0.380 vs 0.538 | difference |
| LB vs SC | all day | 209 | 107 | rng60 | +1.068 bp | [-6.004, +7.808] | 36.332 vs 35.264 | difference |
| LB vs SC | all day | 195 | 104 | cont30 | -1.128 bp | [-7.455, +4.871] | -1.465 vs -0.337 | difference |
| LB vs SC | all day | 195 | 104 | hit30 | -0.031 rate | [-0.193, +0.121] | 0.441 vs 0.472 | difference |
| SB vs LU | to 11:30 | 122 | 84 | rng60 | -11.192 bp | [-27.214, +5.613] | 40.749 vs 51.941 | difference |
| SB vs LU | to 11:30 | 122 | 84 | cont30 | +7.199 bp | [-10.486, +25.235] | 1.211 vs -5.989 | difference |
| SB vs LU | to 11:30 | 122 | 84 | hit30 | +0.291 rate | [-0.028, +0.580] | 0.541 vs 0.250 | difference |
| SB vs LU | 11:30-13:30 | 84 | 58 | rng60 | +3.231 bp | [-8.272, +15.215] | 38.503 vs 35.271 | difference |
| SB vs LU | 11:30-13:30 | 84 | 58 | cont30 | +2.104 bp | [-7.371, +12.934] | 1.575 vs -0.529 | difference |
| SB vs LU | 11:30-13:30 | 84 | 58 | hit30 | -0.038 rate | [-0.329, +0.251] | 0.500 vs 0.538 | difference |
| SB vs LU | after 13:30 | 107 | 75 | rng60 | -5.968 bp | [-22.703, +9.013] | 29.883 vs 35.851 | difference |
| SB vs LU | after 13:30 | 74 | 58 | cont30 | +1.205 bp | [-9.733, +14.074] | 3.662 vs 2.457 | difference |
| SB vs LU | after 13:30 | 74 | 58 | hit30 | -0.032 rate | [-0.364, +0.293] | 0.568 vs 0.600 | difference |
| SB vs LU | all day | 313 | 133 | rng60 | -3.945 bp | [-11.927, +4.887] | 36.432 vs 40.377 | difference |
| SB vs LU | all day | 280 | 128 | cont30 | +3.516 bp | [-4.949, +14.005] | 1.968 vs -1.548 | difference |
| SB vs LU | all day | 280 | 128 | hit30 | +0.079 rate | [-0.122, +0.304] | 0.536 vs 0.457 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F · strong windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 73 | 57 | rng60 | -0.157 bp | [-13.290, +11.418] | 38.905 vs 39.062 | difference |
| LB vs SC | to 11:30 | 73 | 57 | cont30 | +5.133 bp | [-5.149, +16.435] | -0.481 vs -5.614 | difference |
| LB vs SC | to 11:30 | 73 | 57 | hit30 | +0.016 rate | [-0.237, +0.259] | 0.466 vs 0.450 | difference |
| LB vs SC | 11:30-13:30 | 56 | 46 | rng60 | +4.056 bp | [-6.349, +14.786] | 37.533 vs 33.476 | difference |
| LB vs SC | 11:30-13:30 | 56 | 46 | cont30 | -4.991 bp | [-13.695, +2.369] | -0.980 vs 4.011 | difference |
| LB vs SC | 11:30-13:30 | 56 | 46 | hit30 | -0.004 rate | [-0.273, +0.253] | 0.446 vs 0.450 | difference |
| LB vs SC | after 13:30 | 53 | 44 | rng60 | -0.704 bp | [-12.801, +10.280] | 32.161 vs 32.866 | difference |
| LB vs SC | after 13:30 | 43 | 38 | cont30 | -5.405 bp | [-17.008, +5.499] | -2.351 vs 3.053 | difference |
| LB vs SC | after 13:30 | 43 | 38 | hit30 | -0.188 rate | [-0.518, +0.141] | 0.395 vs 0.583 | difference |
| LB vs SC | all day | 182 | 94 | rng60 | +1.222 bp | [-6.170, +8.157] | 36.519 vs 35.297 | difference |
| LB vs SC | all day | 172 | 92 | cont30 | -1.199 bp | [-7.398, +4.961] | -1.111 vs 0.088 | difference |
| LB vs SC | all day | 172 | 92 | hit30 | -0.039 rate | [-0.200, +0.122] | 0.442 vs 0.481 | difference |
| SB vs LU | to 11:30 | 95 | 68 | rng60 | -12.910 bp | [-30.046, +6.288] | 40.325 vs 53.234 | difference |
| SB vs LU | to 11:30 | 95 | 68 | cont30 | +5.694 bp | [-13.686, +26.231] | -0.168 vs -5.862 | difference |
| SB vs LU | to 11:30 | 95 | 68 | hit30 | +0.243 rate | [-0.101, +0.553] | 0.516 vs 0.273 | difference |
| SB vs LU | 11:30-13:30 | 70 | 49 | rng60 | +4.130 bp | [-7.596, +17.799] | 39.401 vs 35.271 | difference |
| SB vs LU | 11:30-13:30 | 70 | 49 | cont30 | +1.871 bp | [-7.421, +13.695] | 1.343 vs -0.529 | difference |
| SB vs LU | 11:30-13:30 | 70 | 49 | hit30 | -0.038 rate | [-0.333, +0.300] | 0.500 vs 0.538 | difference |
| SB vs LU | after 13:30 | 90 | 64 | rng60 | -4.625 bp | [-23.973, +13.192] | 30.405 vs 35.030 | difference |
| SB vs LU | after 13:30 | 64 | 51 | cont30 | +2.224 bp | [-10.920, +19.344] | 3.323 vs 1.100 | difference |
| SB vs LU | after 13:30 | 64 | 51 | hit30 | -0.025 rate | [-0.456, +0.358] | 0.547 vs 0.571 | difference |
| SB vs LU | all day | 255 | 114 | rng60 | -3.957 bp | [-12.887, +5.981] | 36.570 vs 40.527 | difference |
| SB vs LU | all day | 229 | 109 | cont30 | +3.323 bp | [-6.037, +14.616] | 1.270 vs -2.053 | difference |
| SB vs LU | all day | 229 | 109 | hit30 | +0.068 rate | [-0.146, +0.310] | 0.520 vs 0.452 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F1 · all windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 267 | 169 | rng60 | +2.027 bp | [-1.410, +5.380] | 33.454 vs 31.427 | difference |
| LB vs SC | to 11:30 | 267 | 169 | cont30 | +0.764 bp | [-1.947, +3.548] | 0.665 vs -0.099 | difference |
| LB vs SC | to 11:30 | 267 | 169 | hit30 | +0.051 rate | [-0.028, +0.129] | 0.524 vs 0.473 | difference |
| LB vs SC | 11:30-13:30 | 270 | 174 | rng60 | +3.665 bp | [-0.174, +7.373] | 30.036 vs 26.371 | difference |
| LB vs SC | 11:30-13:30 | 270 | 174 | cont30 | -1.575 bp | [-3.967, +0.637] | -0.117 vs 1.458 | difference |
| LB vs SC | 11:30-13:30 | 270 | 174 | hit30 | -0.051 rate | [-0.142, +0.037] | 0.493 vs 0.543 | difference |
| LB vs SC | after 13:30 | 246 | 167 | rng60 | -1.163 bp | [-4.343, +2.150] | 22.691 vs 23.853 | difference |
| LB vs SC | after 13:30 | 177 | 139 | cont30 | -0.133 bp | [-3.265, +3.158] | -1.505 vs -1.373 | difference |
| LB vs SC | after 13:30 | 177 | 139 | hit30 | -0.044 rate | [-0.142, +0.058] | 0.395 vs 0.439 | difference |
| LB vs SC | all day | 783 | 235 | rng60 | +1.594 bp | [-0.636, +3.719] | 28.894 vs 27.300 | difference |
| LB vs SC | all day | 714 | 231 | cont30 | -0.314 bp | [-2.137, +1.476] | -0.169 vs 0.146 | difference |
| LB vs SC | all day | 714 | 231 | hit30 | -0.010 rate | [-0.064, +0.043] | 0.480 vs 0.490 | difference |
| SB vs LU | to 11:30 | 306 | 175 | rng60 | +2.558 bp | [-1.501, +6.281] | 34.083 vs 31.525 | difference |
| SB vs LU | to 11:30 | 306 | 175 | cont30 | -1.245 bp | [-4.143, +1.679] | 0.647 vs 1.892 | difference |
| SB vs LU | to 11:30 | 306 | 175 | hit30 | -0.019 rate | [-0.114, +0.074] | 0.520 vs 0.539 | difference |
| SB vs LU | 11:30-13:30 | 294 | 166 | rng60 | -0.430 bp | [-5.798, +5.859] | 29.862 vs 30.292 | difference |
| SB vs LU | 11:30-13:30 | 294 | 166 | cont30 | +1.975 bp | [-0.631, +4.572] | 1.128 vs -0.847 | difference |
| SB vs LU | 11:30-13:30 | 294 | 166 | hit30 | +0.092 rate | [+0.002, +0.184] | 0.493 vs 0.401 | difference |
| SB vs LU | after 13:30 | 302 | 187 | rng60 | -0.638 bp | [-4.458, +2.836] | 24.750 vs 25.388 | difference |
| SB vs LU | after 13:30 | 223 | 167 | cont30 | +0.998 bp | [-2.145, +4.033] | 0.840 vs -0.158 | difference |
| SB vs LU | after 13:30 | 223 | 167 | hit30 | -0.034 rate | [-0.136, +0.067] | 0.498 vs 0.532 | difference |
| SB vs LU | all day | 902 | 234 | rng60 | +0.780 bp | [-1.725, +3.126] | 29.582 vs 28.802 | difference |
| SB vs LU | all day | 823 | 232 | cont30 | +0.572 bp | [-1.148, +2.402] | 0.871 vs 0.299 | difference |
| SB vs LU | all day | 823 | 232 | hit30 | +0.015 rate | [-0.040, +0.070] | 0.504 vs 0.490 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F1 · all windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 250 | 159 | rng60 | +2.786 bp | [-0.742, +6.333] | 33.634 vs 30.848 | difference |
| LB vs SC | to 11:30 | 250 | 159 | cont30 | +0.993 bp | [-2.099, +3.859] | 0.803 vs -0.190 | difference |
| LB vs SC | to 11:30 | 250 | 159 | hit30 | +0.047 rate | [-0.039, +0.133] | 0.520 vs 0.473 | difference |
| LB vs SC | 11:30-13:30 | 248 | 161 | rng60 | +4.253 bp | [-0.014, +8.183] | 29.932 vs 25.679 | difference |
| LB vs SC | 11:30-13:30 | 248 | 161 | cont30 | -2.040 bp | [-4.645, +0.493] | -0.525 vs 1.515 | difference |
| LB vs SC | 11:30-13:30 | 248 | 161 | hit30 | -0.074 rate | [-0.171, +0.025] | 0.468 vs 0.542 | difference |
| LB vs SC | after 13:30 | 229 | 155 | rng60 | -1.244 bp | [-4.723, +2.395] | 22.700 vs 23.944 | difference |
| LB vs SC | after 13:30 | 163 | 128 | cont30 | -0.232 bp | [-3.446, +3.548] | -1.483 vs -1.251 | difference |
| LB vs SC | after 13:30 | 163 | 128 | hit30 | -0.051 rate | [-0.151, +0.063] | 0.399 vs 0.450 | difference |
| LB vs SC | all day | 727 | 217 | rng60 | +2.034 bp | [-0.288, +4.249] | 28.927 vs 26.893 | difference |
| LB vs SC | all day | 661 | 213 | cont30 | -0.409 bp | [-2.291, +1.487] | -0.259 vs 0.150 | difference |
| LB vs SC | all day | 661 | 213 | hit30 | -0.021 rate | [-0.077, +0.037] | 0.470 vs 0.492 | difference |
| SB vs LU | to 11:30 | 282 | 159 | rng60 | +2.981 bp | [-1.111, +6.802] | 33.537 vs 30.556 | difference |
| SB vs LU | to 11:30 | 282 | 159 | cont30 | -1.475 bp | [-4.507, +1.643] | 0.443 vs 1.918 | difference |
| SB vs LU | to 11:30 | 282 | 159 | hit30 | +0.012 rate | [-0.076, +0.110] | 0.525 vs 0.513 | difference |
| SB vs LU | 11:30-13:30 | 278 | 155 | rng60 | -0.173 bp | [-5.947, +6.146] | 29.864 vs 30.036 | difference |
| SB vs LU | 11:30-13:30 | 278 | 155 | cont30 | +2.390 bp | [-0.137, +5.218] | 1.058 vs -1.331 | difference |
| SB vs LU | 11:30-13:30 | 278 | 155 | hit30 | +0.109 rate | [+0.019, +0.198] | 0.489 vs 0.380 | difference |
| SB vs LU | after 13:30 | 284 | 176 | rng60 | -0.239 bp | [-4.085, +3.529] | 24.490 vs 24.729 | difference |
| SB vs LU | after 13:30 | 211 | 158 | cont30 | +1.627 bp | [-1.433, +4.622] | 1.032 vs -0.595 | difference |
| SB vs LU | after 13:30 | 211 | 158 | hit30 | -0.030 rate | [-0.139, +0.075] | 0.498 vs 0.528 | difference |
| SB vs LU | all day | 844 | 215 | rng60 | +1.089 bp | [-1.288, +3.470] | 29.283 vs 28.194 | difference |
| SB vs LU | all day | 771 | 213 | cont30 | +0.827 bp | [-1.089, +2.725] | 0.826 vs -0.002 | difference |
| SB vs LU | all day | 771 | 213 | hit30 | +0.033 rate | [-0.023, +0.090] | 0.505 vs 0.471 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F1 · strong windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 70 | 57 | rng60 | +3.854 bp | [-3.788, +11.279] | 37.718 vs 33.864 | difference |
| LB vs SC | to 11:30 | 70 | 57 | cont30 | +3.173 bp | [-2.358, +8.720] | -0.784 vs -3.958 | difference |
| LB vs SC | to 11:30 | 70 | 57 | hit30 | -0.002 rate | [-0.166, +0.167] | 0.471 vs 0.474 | difference |
| LB vs SC | 11:30-13:30 | 64 | 54 | rng60 | +6.844 bp | [-0.056, +14.259] | 37.841 vs 30.997 | difference |
| LB vs SC | 11:30-13:30 | 64 | 54 | cont30 | -2.300 bp | [-6.754, +2.259] | -0.424 vs 1.876 | difference |
| LB vs SC | 11:30-13:30 | 64 | 54 | hit30 | -0.030 rate | [-0.186, +0.127] | 0.484 vs 0.515 | difference |
| LB vs SC | after 13:30 | 60 | 51 | rng60 | +2.945 bp | [-3.390, +9.096] | 30.154 vs 27.209 | difference |
| LB vs SC | after 13:30 | 48 | 43 | cont30 | -2.085 bp | [-8.500, +4.722] | -3.643 vs -1.558 | difference |
| LB vs SC | after 13:30 | 48 | 43 | hit30 | -0.148 rate | [-0.355, +0.060] | 0.312 vs 0.460 | difference |
| LB vs SC | all day | 194 | 109 | rng60 | +4.893 bp | [+0.496, +9.122] | 35.419 vs 30.526 | difference |
| LB vs SC | all day | 182 | 105 | cont30 | -0.406 bp | [-3.624, +2.859] | -1.411 vs -1.005 | difference |
| LB vs SC | all day | 182 | 105 | hit30 | -0.052 rate | [-0.154, +0.046] | 0.434 vs 0.486 | difference |
| SB vs LU | to 11:30 | 106 | 77 | rng60 | -1.996 bp | [-11.639, +6.382] | 40.051 vs 42.047 | difference |
| SB vs LU | to 11:30 | 106 | 77 | cont30 | -3.522 bp | [-11.006, +3.559] | 1.450 vs 4.972 | difference |
| SB vs LU | to 11:30 | 106 | 77 | hit30 | -0.062 rate | [-0.232, +0.112] | 0.566 vs 0.628 | difference |
| SB vs LU | 11:30-13:30 | 97 | 72 | rng60 | +2.301 bp | [-5.561, +11.790] | 34.394 vs 32.093 | difference |
| SB vs LU | 11:30-13:30 | 97 | 72 | cont30 | +2.941 bp | [-2.413, +8.381] | 1.490 vs -1.451 | difference |
| SB vs LU | 11:30-13:30 | 97 | 72 | hit30 | +0.028 rate | [-0.150, +0.209] | 0.505 vs 0.477 | difference |
| SB vs LU | after 13:30 | 85 | 68 | rng60 | -0.707 bp | [-7.253, +5.739] | 29.213 vs 29.919 | difference |
| SB vs LU | after 13:30 | 66 | 58 | cont30 | -1.010 bp | [-7.608, +5.560] | 0.581 vs 1.592 | difference |
| SB vs LU | after 13:30 | 66 | 58 | hit30 | -0.184 rate | [-0.369, +0.012] | 0.424 vs 0.608 | difference |
| SB vs LU | all day | 288 | 137 | rng60 | +1.072 bp | [-3.695, +5.742] | 34.947 vs 33.875 | difference |
| SB vs LU | all day | 269 | 135 | cont30 | -0.424 bp | [-4.323, +3.352] | 1.251 vs 1.675 | difference |
| SB vs LU | all day | 269 | 135 | hit30 | -0.063 rate | [-0.167, +0.038] | 0.509 vs 0.572 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=30 min · OI=F1 · strong windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 64 | 52 | rng60 | +3.758 bp | [-4.000, +11.986] | 37.226 vs 33.467 | difference |
| LB vs SC | to 11:30 | 64 | 52 | cont30 | +3.432 bp | [-2.497, +9.567] | -0.577 vs -4.009 | difference |
| LB vs SC | to 11:30 | 64 | 52 | hit30 | -0.001 rate | [-0.176, +0.176] | 0.469 vs 0.469 | difference |
| LB vs SC | 11:30-13:30 | 58 | 49 | rng60 | +7.581 bp | [-0.472, +15.486] | 38.216 vs 30.635 | difference |
| LB vs SC | 11:30-13:30 | 58 | 49 | cont30 | -2.512 bp | [-7.275, +2.195] | -0.819 vs 1.693 | difference |
| LB vs SC | 11:30-13:30 | 58 | 49 | hit30 | -0.060 rate | [-0.220, +0.101] | 0.448 vs 0.508 | difference |
| LB vs SC | after 13:30 | 56 | 48 | rng60 | +2.604 bp | [-3.748, +8.706] | 30.205 vs 27.601 | difference |
| LB vs SC | after 13:30 | 44 | 40 | cont30 | -2.929 bp | [-9.425, +4.213] | -3.854 vs -0.925 | difference |
| LB vs SC | after 13:30 | 44 | 40 | hit30 | -0.158 rate | [-0.373, +0.062] | 0.318 vs 0.476 | difference |
| LB vs SC | all day | 178 | 100 | rng60 | +4.859 bp | [-0.350, +9.646] | 35.340 vs 30.480 | difference |
| LB vs SC | all day | 166 | 96 | cont30 | -0.627 bp | [-4.076, +2.719] | -1.530 vs -0.903 | difference |
| LB vs SC | all day | 166 | 96 | hit30 | -0.065 rate | [-0.178, +0.039] | 0.422 vs 0.487 | difference |
| SB vs LU | to 11:30 | 94 | 69 | rng60 | -4.549 bp | [-15.226, +5.895] | 39.057 vs 43.605 | difference |
| SB vs LU | to 11:30 | 94 | 69 | cont30 | -4.733 bp | [-12.977, +3.680] | 0.431 vs 5.164 | difference |
| SB vs LU | to 11:30 | 94 | 69 | hit30 | -0.054 rate | [-0.233, +0.138] | 0.564 vs 0.618 | difference |
| SB vs LU | 11:30-13:30 | 89 | 66 | rng60 | +1.830 bp | [-6.902, +12.074] | 35.093 vs 33.263 | difference |
| SB vs LU | 11:30-13:30 | 89 | 66 | cont30 | +4.532 bp | [-1.132, +10.470] | 1.916 vs -2.615 | difference |
| SB vs LU | 11:30-13:30 | 89 | 66 | hit30 | +0.069 rate | [-0.115, +0.246] | 0.517 vs 0.447 | difference |
| SB vs LU | after 13:30 | 81 | 65 | rng60 | +0.472 bp | [-7.378, +8.241] | 29.742 vs 29.270 | difference |
| SB vs LU | after 13:30 | 64 | 56 | cont30 | -0.205 bp | [-7.469, +6.732] | 0.529 vs 0.734 | difference |
| SB vs LU | after 13:30 | 64 | 56 | hit30 | -0.173 rate | [-0.393, +0.028] | 0.422 vs 0.595 | difference |
| SB vs LU | all day | 264 | 126 | rng60 | +0.354 bp | [-5.122, +5.532] | 34.862 vs 34.509 | difference |
| SB vs LU | all day | 247 | 124 | cont30 | +0.043 bp | [-4.159, +4.340] | 0.991 vs 0.948 | difference |
| SB vs LU | all day | 247 | 124 | hit30 | -0.040 rate | [-0.148, +0.072] | 0.510 vs 0.550 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F · all windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 162 | 132 | rng60 | +6.963 bp | [+1.969, +11.517] | 32.812 vs 25.848 | difference |
| LB vs SC | to 11:30 | 162 | 132 | cont30 | -2.404 bp | [-6.562, +1.411] | -1.507 vs 0.896 | difference |
| LB vs SC | to 11:30 | 162 | 132 | hit30 | -0.128 rate | [-0.281, +0.021] | 0.426 vs 0.554 | difference |
| LB vs SC | 11:30-13:30 | 116 | 92 | rng60 | +1.764 bp | [-6.254, +8.915] | 32.725 vs 30.960 | difference |
| LB vs SC | 11:30-13:30 | 116 | 92 | cont30 | -4.934 bp | [-10.854, +0.380] | -0.936 vs 3.997 | difference |
| LB vs SC | 11:30-13:30 | 116 | 92 | hit30 | -0.126 rate | [-0.296, +0.049] | 0.483 vs 0.609 | difference |
| LB vs SC | after 13:30 | 106 | 91 | rng60 | +5.525 bp | [+0.104, +11.014] | 24.583 vs 19.057 | difference |
| LB vs SC | after 13:30 | 59 | 59 | cont30 | +0.347 bp | [-7.115, +8.081] | -2.547 vs -2.894 | difference |
| LB vs SC | after 13:30 | 59 | 59 | hit30 | +0.004 rate | [-0.260, +0.252] | 0.373 vs 0.368 | difference |
| LB vs SC | all day | 384 | 188 | rng60 | +5.101 bp | [+1.572, +8.537] | 30.514 vs 25.412 | difference |
| LB vs SC | all day | 337 | 179 | cont30 | -2.973 bp | [-6.517, +0.158] | -1.493 vs 1.480 | difference |
| LB vs SC | all day | 337 | 179 | hit30 | -0.109 rate | [-0.212, -0.003] | 0.436 vs 0.545 | difference |
| SB vs LU | to 11:30 | 166 | 132 | rng60 | -2.188 bp | [-10.434, +5.004] | 32.894 vs 35.082 | difference |
| SB vs LU | to 11:30 | 166 | 132 | cont30 | +1.981 bp | [-4.772, +8.586] | 0.688 vs -1.293 | difference |
| SB vs LU | to 11:30 | 166 | 132 | hit30 | +0.116 rate | [-0.067, +0.288] | 0.548 vs 0.432 | difference |
| SB vs LU | 11:30-13:30 | 122 | 97 | rng60 | -3.751 bp | [-10.730, +3.633] | 31.467 vs 35.217 | difference |
| SB vs LU | 11:30-13:30 | 122 | 97 | cont30 | +1.142 bp | [-4.951, +8.002] | 0.266 vs -0.876 | difference |
| SB vs LU | 11:30-13:30 | 122 | 97 | hit30 | +0.066 rate | [-0.196, +0.312] | 0.516 vs 0.450 | difference |
| SB vs LU | after 13:30 | 150 | 124 | rng60 | -1.764 bp | [-11.660, +6.378] | 21.318 vs 23.082 | difference |
| SB vs LU | after 13:30 | 58 | 58 | cont30 | +2.950 bp | [-6.094, +14.650] | -1.975 vs -4.925 | difference |
| SB vs LU | after 13:30 | 58 | 58 | hit30 | -0.117 rate | [-0.369, +0.123] | 0.483 vs 0.600 | difference |
| SB vs LU | all day | 438 | 194 | rng60 | -1.557 bp | [-6.945, +3.559] | 28.532 vs 30.089 | difference |
| SB vs LU | all day | 346 | 179 | cont30 | +2.221 bp | [-2.263, +7.403] | 0.093 vs -2.128 | difference |
| SB vs LU | all day | 346 | 179 | hit30 | +0.045 rate | [-0.075, +0.173] | 0.526 vs 0.481 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F · all windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 148 | 118 | rng60 | +6.530 bp | [+1.646, +11.404] | 32.427 vs 25.897 | difference |
| LB vs SC | to 11:30 | 148 | 118 | cont30 | -1.693 bp | [-5.870, +2.192] | -1.057 vs 0.636 | difference |
| LB vs SC | to 11:30 | 148 | 118 | hit30 | -0.129 rate | [-0.286, +0.031] | 0.439 vs 0.569 | difference |
| LB vs SC | 11:30-13:30 | 99 | 79 | rng60 | +1.333 bp | [-7.156, +8.959] | 32.454 vs 31.121 | difference |
| LB vs SC | 11:30-13:30 | 99 | 79 | cont30 | -5.736 bp | [-12.202, -0.141] | -1.360 vs 4.376 | difference |
| LB vs SC | 11:30-13:30 | 99 | 79 | hit30 | -0.159 rate | [-0.337, +0.017] | 0.455 vs 0.614 | difference |
| LB vs SC | after 13:30 | 90 | 77 | rng60 | +5.281 bp | [-0.561, +11.274] | 24.428 vs 19.147 | difference |
| LB vs SC | after 13:30 | 50 | 50 | cont30 | +0.490 bp | [-7.472, +8.545] | -1.174 vs -1.665 | difference |
| LB vs SC | after 13:30 | 50 | 50 | hit30 | -0.012 rate | [-0.305, +0.263] | 0.400 vs 0.412 | difference |
| LB vs SC | all day | 337 | 166 | rng60 | +4.746 bp | [+1.000, +8.424] | 30.299 vs 25.552 | difference |
| LB vs SC | all day | 297 | 158 | cont30 | -2.933 bp | [-6.579, +0.440] | -1.178 vs 1.756 | difference |
| LB vs SC | all day | 297 | 158 | hit30 | -0.125 rate | [-0.234, -0.014] | 0.438 vs 0.562 | difference |
| SB vs LU | to 11:30 | 146 | 115 | rng60 | -3.094 bp | [-11.475, +4.575] | 32.250 vs 35.344 | difference |
| SB vs LU | to 11:30 | 146 | 115 | cont30 | +2.149 bp | [-4.720, +9.061] | 0.765 vs -1.384 | difference |
| SB vs LU | to 11:30 | 146 | 115 | hit30 | +0.126 rate | [-0.057, +0.303] | 0.555 vs 0.429 | difference |
| SB vs LU | 11:30-13:30 | 106 | 84 | rng60 | -3.417 bp | [-10.253, +4.045] | 31.800 vs 35.217 | difference |
| SB vs LU | 11:30-13:30 | 106 | 84 | cont30 | +1.133 bp | [-4.944, +7.567] | 0.257 vs -0.876 | difference |
| SB vs LU | 11:30-13:30 | 106 | 84 | hit30 | +0.078 rate | [-0.181, +0.322] | 0.528 vs 0.450 | difference |
| SB vs LU | after 13:30 | 137 | 112 | rng60 | -1.644 bp | [-12.350, +6.907] | 20.967 vs 22.612 | difference |
| SB vs LU | after 13:30 | 54 | 54 | cont30 | +2.100 bp | [-6.923, +14.892] | -1.791 vs -3.891 | difference |
| SB vs LU | after 13:30 | 54 | 54 | hit30 | -0.185 rate | [-0.432, +0.089] | 0.481 vs 0.667 | difference |
| SB vs LU | all day | 389 | 174 | rng60 | -1.961 bp | [-7.742, +3.667] | 28.154 vs 30.114 | difference |
| SB vs LU | all day | 306 | 161 | cont30 | +2.001 bp | [-2.728, +6.810] | 0.138 vs -1.863 | difference |
| SB vs LU | all day | 306 | 161 | hit30 | +0.040 rate | [-0.084, +0.165] | 0.533 vs 0.493 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F · strong windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 35 | 33 | rng60 | +12.391 bp | [+3.083, +22.342] | 37.523 vs 25.132 | difference |
| LB vs SC | to 11:30 | 35 | 33 | cont30 | -6.344 bp | [-14.626, +1.479] | -5.196 vs 1.147 | difference |
| LB vs SC | to 11:30 | 35 | 33 | hit30 | -0.157 rate | [-0.575, +0.250] | 0.343 vs 0.500 | difference |
| LB vs SC | 11:30-13:30 | 33 | 31 | rng60 | -7.086 bp | [-24.295, +9.234] | 37.671 vs 44.757 | difference |
| LB vs SC | 11:30-13:30 | 33 | 31 | cont30 | -6.669 bp | [-26.182, +10.231] | -3.629 vs 3.040 | difference |
| LB vs SC | 11:30-13:30 | 33 | 31 | hit30 | -0.117 rate | [-0.541, +0.306] | 0.455 vs 0.571 | difference |
| LB vs SC | after 13:30 | 30 | 29 | rng60 | +2.215 bp | [-9.841, +14.469] | 27.591 vs 25.376 | difference |
| LB vs SC | after 13:30 | 17 | 17 | cont30 | -9.485 bp | [-18.521, +0.529] | -8.704 vs 0.781 | difference |
| LB vs SC | after 13:30 | 17 | 17 | hit30 | -0.490 rate | [-0.889, -0.033] | 0.176 vs 0.667 | difference |
| LB vs SC | all day | 98 | 67 | rng60 | +4.381 bp | [-4.043, +12.462] | 34.532 vs 30.152 | difference |
| LB vs SC | all day | 85 | 61 | cont30 | -6.963 bp | [-14.856, +0.133] | -5.290 vs 1.673 | difference |
| LB vs SC | all day | 85 | 61 | hit30 | -0.218 rate | [-0.448, +0.039] | 0.353 vs 0.571 | difference |
| SB vs LU | to 11:30 | 68 | 63 | rng60 | -10.467 bp | [-29.546, +5.930] | 37.668 vs 48.135 | difference |
| SB vs LU | to 11:30 | 68 | 63 | cont30 | +6.023 bp | [-12.700, +25.556] | -0.782 vs -6.805 | difference |
| SB vs LU | to 11:30 | 68 | 63 | hit30 | +0.015 rate | [-0.371, +0.408] | 0.515 vs 0.500 | difference |
| SB vs LU | 11:30-13:30 | 47 | 42 | rng60 | +3.561 bp | [-4.493, +14.617] | 35.565 vs 32.003 | difference |
| SB vs LU | 11:30-13:30 | 47 | 42 | cont30 | -2.124 bp | [-12.080, +7.767] | 1.729 vs 3.853 | difference |
| SB vs LU | 11:30-13:30 | 47 | 42 | hit30 | +0.117 rate | [-0.434, +0.679] | 0.617 vs 0.500 | difference |
| SB vs LU | after 13:30 | 59 | 53 | rng60 | -22.200 bp | [-62.108, +5.056] | 24.843 vs 47.043 | difference |
| SB vs LU | after 13:30 | 22 | 22 | cont30 | +11.367 bp | [-0.100, +19.791] | 2.216 vs -9.151 | difference |
| SB vs LU | after 13:30 | 22 | 22 | hit30 | +0.295 rate | [-0.358, +0.682] | 0.545 vs 0.250 | difference |
| SB vs LU | all day | 174 | 101 | rng60 | -11.435 bp | [-26.556, +0.846] | 32.751 vs 44.186 | difference |
| SB vs LU | all day | 137 | 87 | cont30 | +5.288 bp | [-4.312, +16.776] | 0.561 vs -4.727 | difference |
| SB vs LU | all day | 137 | 87 | hit30 | +0.117 rate | [-0.160, +0.397] | 0.555 vs 0.438 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F · strong windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 31 | 29 | rng60 | +11.090 bp | [+0.723, +22.104] | 36.667 vs 25.577 | difference |
| LB vs SC | to 11:30 | 31 | 29 | cont30 | -6.747 bp | [-15.538, +1.389] | -4.772 vs 1.976 | difference |
| LB vs SC | to 11:30 | 31 | 29 | hit30 | -0.217 rate | [-0.652, +0.206] | 0.355 vs 0.571 | difference |
| LB vs SC | 11:30-13:30 | 25 | 24 | rng60 | -6.951 bp | [-22.408, +10.159] | 37.805 vs 44.757 | difference |
| LB vs SC | 11:30-13:30 | 25 | 24 | cont30 | -6.966 bp | [-26.304, +10.493] | -3.926 vs 3.040 | difference |
| LB vs SC | 11:30-13:30 | 25 | 24 | hit30 | -0.131 rate | [-0.572, +0.316] | 0.440 vs 0.571 | difference |
| LB vs SC | after 13:30 | 25 | 25 | rng60 | +3.408 bp | [-10.150, +16.740] | 29.614 vs 26.206 | difference |
| LB vs SC | after 13:30 | 15 | 15 | cont30 | -9.972 bp | [-20.187, +2.039] | -8.187 vs 1.785 | difference |
| LB vs SC | after 13:30 | 15 | 15 | hit30 | -0.600 rate | [-0.938, -0.121] | 0.200 vs 0.800 | difference |
| LB vs SC | all day | 81 | 58 | rng60 | +3.810 bp | [-5.417, +12.338] | 34.842 vs 31.031 | difference |
| LB vs SC | all day | 71 | 52 | cont30 | -7.513 bp | [-15.647, +0.346] | -5.196 vs 2.317 | difference |
| LB vs SC | all day | 71 | 52 | hit30 | -0.279 rate | [-0.526, -0.017] | 0.352 vs 0.632 | difference |
| SB vs LU | to 11:30 | 53 | 51 | rng60 | -10.743 bp | [-29.028, +5.474] | 37.392 vs 48.135 | difference |
| SB vs LU | to 11:30 | 53 | 51 | cont30 | +5.877 bp | [-13.182, +25.218] | -0.928 vs -6.805 | difference |
| SB vs LU | to 11:30 | 53 | 51 | hit30 | +0.028 rate | [-0.355, +0.413] | 0.528 vs 0.500 | difference |
| SB vs LU | 11:30-13:30 | 40 | 36 | rng60 | +3.639 bp | [-4.624, +15.080] | 35.642 vs 32.003 | difference |
| SB vs LU | 11:30-13:30 | 40 | 36 | cont30 | -3.694 bp | [-14.207, +6.368] | 0.160 vs 3.853 | difference |
| SB vs LU | 11:30-13:30 | 40 | 36 | hit30 | +0.075 rate | [-0.488, +0.632] | 0.575 vs 0.500 | difference |
| SB vs LU | after 13:30 | 52 | 47 | rng60 | -25.611 bp | [-109.253, +8.273] | 24.136 vs 49.747 | difference |
| SB vs LU | after 13:30 | 19 | 19 | cont30 | +6.452 bp | [-5.310, +18.164] | 2.381 vs -4.072 | difference |
| SB vs LU | after 13:30 | 19 | 19 | hit30 | +0.026 rate | [-0.632, +0.684] | 0.526 vs 0.500 | difference |
| SB vs LU | all day | 145 | 87 | rng60 | -12.350 bp | [-29.309, +1.359] | 32.155 vs 44.505 | difference |
| SB vs LU | all day | 112 | 74 | cont30 | +3.391 bp | [-7.960, +16.889] | 0.022 vs -3.369 | difference |
| SB vs LU | all day | 112 | 74 | hit30 | +0.045 rate | [-0.241, +0.357] | 0.545 vs 0.500 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F1 · all windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 145 | 125 | rng60 | +2.254 bp | [-2.261, +6.789] | 30.918 vs 28.664 | difference |
| LB vs SC | to 11:30 | 145 | 125 | cont30 | +0.440 bp | [-3.194, +3.875] | -1.018 vs -1.458 | difference |
| LB vs SC | to 11:30 | 145 | 125 | hit30 | -0.024 rate | [-0.148, +0.104] | 0.441 vs 0.465 | difference |
| LB vs SC | 11:30-13:30 | 129 | 104 | rng60 | +2.406 bp | [-2.816, +7.391] | 30.056 vs 27.650 | difference |
| LB vs SC | 11:30-13:30 | 129 | 104 | cont30 | -1.620 bp | [-5.710, +2.116] | -0.069 vs 1.551 | difference |
| LB vs SC | 11:30-13:30 | 129 | 104 | hit30 | -0.070 rate | [-0.189, +0.053] | 0.512 vs 0.582 | difference |
| LB vs SC | after 13:30 | 124 | 110 | rng60 | -0.457 bp | [-5.715, +4.391] | 21.167 vs 21.624 | difference |
| LB vs SC | after 13:30 | 68 | 68 | cont30 | -3.219 bp | [-9.591, +2.369] | -4.089 vs -0.871 | difference |
| LB vs SC | after 13:30 | 68 | 68 | hit30 | -0.070 rate | [-0.235, +0.093] | 0.309 vs 0.379 | difference |
| LB vs SC | all day | 398 | 203 | rng60 | +1.493 bp | [-1.379, +4.411] | 27.601 vs 26.107 | difference |
| LB vs SC | all day | 342 | 191 | cont30 | -1.177 bp | [-3.654, +1.299] | -1.271 vs -0.094 | difference |
| LB vs SC | all day | 342 | 191 | hit30 | -0.055 rate | [-0.129, +0.021] | 0.442 vs 0.497 | difference |
| SB vs LU | to 11:30 | 150 | 121 | rng60 | -2.583 bp | [-7.881, +2.349] | 31.236 vs 33.819 | difference |
| SB vs LU | to 11:30 | 150 | 121 | cont30 | -1.498 bp | [-6.122, +2.961] | -0.255 vs 1.242 | difference |
| SB vs LU | to 11:30 | 150 | 121 | hit30 | -0.010 rate | [-0.153, +0.127] | 0.520 vs 0.530 | difference |
| SB vs LU | 11:30-13:30 | 152 | 119 | rng60 | +4.434 bp | [-0.562, +10.121] | 31.053 vs 26.619 | difference |
| SB vs LU | 11:30-13:30 | 152 | 119 | cont30 | +0.231 bp | [-3.129, +3.951] | 1.210 vs 0.980 | difference |
| SB vs LU | 11:30-13:30 | 152 | 119 | hit30 | +0.076 rate | [-0.056, +0.206] | 0.513 vs 0.437 | difference |
| SB vs LU | after 13:30 | 157 | 132 | rng60 | -2.130 bp | [-7.456, +2.408] | 20.066 vs 22.196 | difference |
| SB vs LU | after 13:30 | 63 | 63 | cont30 | +1.417 bp | [-3.817, +7.335] | -1.215 vs -2.632 | difference |
| SB vs LU | after 13:30 | 63 | 63 | hit30 | +0.012 rate | [-0.163, +0.199] | 0.476 vs 0.464 | difference |
| SB vs LU | all day | 459 | 196 | rng60 | +0.160 bp | [-2.798, +2.961] | 27.355 vs 27.194 | difference |
| SB vs LU | all day | 365 | 179 | cont30 | +0.008 bp | [-2.659, +2.473] | 0.189 vs 0.181 | difference |
| SB vs LU | all day | 365 | 179 | hit30 | +0.032 rate | [-0.049, +0.111] | 0.510 vs 0.478 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F1 · all windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 136 | 117 | rng60 | +3.372 bp | [-1.375, +8.167] | 31.149 vs 27.777 | difference |
| LB vs SC | to 11:30 | 136 | 117 | cont30 | -0.090 bp | [-3.801, +3.692] | -1.107 vs -1.016 | difference |
| LB vs SC | to 11:30 | 136 | 117 | hit30 | -0.056 rate | [-0.191, +0.077] | 0.434 vs 0.490 | difference |
| LB vs SC | 11:30-13:30 | 123 | 99 | rng60 | +3.624 bp | [-1.786, +8.901] | 30.305 vs 26.681 | difference |
| LB vs SC | 11:30-13:30 | 123 | 99 | cont30 | -1.800 bp | [-6.277, +2.172] | -0.164 vs 1.637 | difference |
| LB vs SC | 11:30-13:30 | 123 | 99 | hit30 | -0.085 rate | [-0.213, +0.043] | 0.496 vs 0.581 | difference |
| LB vs SC | after 13:30 | 114 | 101 | rng60 | -0.741 bp | [-6.070, +4.488] | 20.775 vs 21.516 | difference |
| LB vs SC | after 13:30 | 60 | 60 | cont30 | -5.093 bp | [-12.418, +0.915] | -3.973 vs 1.120 | difference |
| LB vs SC | after 13:30 | 60 | 60 | hit30 | -0.115 rate | [-0.295, +0.074] | 0.317 vs 0.431 | difference |
| LB vs SC | all day | 373 | 190 | rng60 | +2.263 bp | [-0.956, +5.320] | 27.700 vs 25.437 | difference |
| LB vs SC | all day | 319 | 179 | cont30 | -1.780 bp | [-4.594, +0.747] | -1.282 vs 0.497 | difference |
| LB vs SC | all day | 319 | 179 | hit30 | -0.080 rate | [-0.159, +0.004] | 0.436 vs 0.516 | difference |
| SB vs LU | to 11:30 | 142 | 114 | rng60 | -2.449 bp | [-8.364, +2.831] | 30.858 vs 33.307 | difference |
| SB vs LU | to 11:30 | 142 | 114 | cont30 | -2.693 bp | [-7.438, +1.987] | -0.461 vs 2.232 | difference |
| SB vs LU | to 11:30 | 142 | 114 | hit30 | -0.045 rate | [-0.185, +0.102] | 0.514 vs 0.559 | difference |
| SB vs LU | 11:30-13:30 | 141 | 110 | rng60 | +5.921 bp | [+0.634, +11.913] | 31.298 vs 25.378 | difference |
| SB vs LU | 11:30-13:30 | 141 | 110 | cont30 | +1.109 bp | [-2.445, +4.598] | 1.053 vs -0.056 | difference |
| SB vs LU | 11:30-13:30 | 141 | 110 | hit30 | +0.111 rate | [-0.029, +0.249] | 0.511 vs 0.400 | difference |
| SB vs LU | after 13:30 | 148 | 124 | rng60 | -1.694 bp | [-6.942, +3.291] | 20.173 vs 21.867 | difference |
| SB vs LU | after 13:30 | 61 | 61 | cont30 | +1.453 bp | [-3.868, +7.726] | -0.964 vs -2.417 | difference |
| SB vs LU | after 13:30 | 61 | 61 | hit30 | -0.005 rate | [-0.195, +0.182] | 0.475 vs 0.480 | difference |
| SB vs LU | all day | 431 | 185 | rng60 | +0.939 bp | [-2.001, +3.915] | 27.333 vs 26.394 | difference |
| SB vs LU | all day | 344 | 169 | cont30 | -0.068 bp | [-2.718, +2.435] | 0.070 vs 0.138 | difference |
| SB vs LU | all day | 344 | 169 | hit30 | +0.029 rate | [-0.057, +0.117] | 0.506 vs 0.477 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F1 · strong windows · all   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 27 | 26 | rng60 | +3.226 bp | [-7.969, +15.593] | 38.220 vs 34.994 | difference |
| LB vs SC | to 11:30 | 27 | 26 | cont30 | -2.757 bp | [-11.131, +5.263] | -5.668 vs -2.911 | difference |
| LB vs SC | to 11:30 | 27 | 26 | hit30 | -0.107 rate | [-0.367, +0.154] | 0.333 vs 0.440 | difference |
| LB vs SC | 11:30-13:30 | 33 | 32 | rng60 | +1.172 bp | [-8.784, +11.380] | 36.357 vs 35.185 | difference |
| LB vs SC | 11:30-13:30 | 33 | 32 | cont30 | -7.173 bp | [-17.974, +2.688] | -2.915 vs 4.258 | difference |
| LB vs SC | 11:30-13:30 | 33 | 32 | hit30 | -0.121 rate | [-0.363, +0.124] | 0.485 vs 0.606 | difference |
| LB vs SC | after 13:30 | 27 | 27 | rng60 | +5.373 bp | [-4.942, +16.035] | 27.347 vs 21.974 | difference |
| LB vs SC | after 13:30 | 14 | 14 | cont30 | +2.300 bp | [-10.568, +15.325] | -4.061 vs -6.361 | difference |
| LB vs SC | after 13:30 | 14 | 14 | hit30 | +0.045 rate | [-0.303, +0.384] | 0.357 vs 0.312 | difference |
| LB vs SC | all day | 87 | 69 | rng60 | +3.888 bp | [-2.409, +10.331] | 34.139 vs 30.251 | difference |
| LB vs SC | all day | 74 | 61 | cont30 | -3.677 bp | [-10.864, +2.725] | -4.136 vs -0.460 | difference |
| LB vs SC | all day | 74 | 61 | hit30 | -0.081 rate | [-0.242, +0.082] | 0.405 vs 0.486 | difference |
| SB vs LU | to 11:30 | 59 | 56 | rng60 | -6.245 bp | [-18.467, +4.896] | 35.894 vs 42.138 | difference |
| SB vs LU | to 11:30 | 59 | 56 | cont30 | +2.233 bp | [-8.275, +13.353] | -0.106 vs -2.339 | difference |
| SB vs LU | to 11:30 | 59 | 56 | hit30 | -0.012 rate | [-0.246, +0.226] | 0.559 vs 0.571 | difference |
| SB vs LU | 11:30-13:30 | 48 | 41 | rng60 | +5.496 bp | [-6.170, +20.256] | 37.798 vs 32.302 | difference |
| SB vs LU | 11:30-13:30 | 48 | 41 | cont30 | +0.859 bp | [-6.739, +8.913] | 4.013 vs 3.154 | difference |
| SB vs LU | 11:30-13:30 | 48 | 41 | hit30 | +0.146 rate | [-0.113, +0.417] | 0.646 vs 0.500 | difference |
| SB vs LU | after 13:30 | 55 | 53 | rng60 | -0.268 bp | [-12.008, +10.094] | 24.771 vs 25.039 | difference |
| SB vs LU | after 13:30 | 27 | 27 | cont30 | -0.600 bp | [-7.576, +6.101] | -0.220 vs 0.380 | difference |
| SB vs LU | after 13:30 | 27 | 27 | hit30 | -0.057 rate | [-0.375, +0.279] | 0.481 vs 0.538 | difference |
| SB vs LU | all day | 162 | 103 | rng60 | +0.115 bp | [-5.799, +6.048] | 32.682 vs 32.566 | difference |
| SB vs LU | all day | 134 | 88 | cont30 | +0.996 bp | [-4.636, +6.570] | 1.347 vs 0.350 | difference |
| SB vs LU | all day | 134 | 88 | hit30 | +0.038 rate | [-0.130, +0.203] | 0.575 vs 0.537 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

### A1 step=60 min · OI=F1 · strong windows · no-expiry   [exploratory]

| contrast | time of day  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB vs SC | to 11:30 | 26 | 25 | rng60 | +3.400 bp | [-10.608, +16.550] | 37.870 vs 34.469 | difference |
| LB vs SC | to 11:30 | 26 | 25 | cont30 | -3.328 bp | [-11.951, +5.024] | -4.675 vs -1.347 | difference |
| LB vs SC | to 11:30 | 26 | 25 | hit30 | -0.130 rate | [-0.417, +0.147] | 0.346 vs 0.476 | difference |
| LB vs SC | 11:30-13:30 | 30 | 29 | rng60 | +2.270 bp | [-9.614, +13.919] | 36.926 vs 34.655 | difference |
| LB vs SC | 11:30-13:30 | 30 | 29 | cont30 | -9.349 bp | [-21.630, +1.339] | -3.109 vs 6.240 | difference |
| LB vs SC | 11:30-13:30 | 30 | 29 | hit30 | -0.176 rate | [-0.437, +0.079] | 0.467 vs 0.643 | difference |
| LB vs SC | after 13:30 | 25 | 25 | rng60 | +4.222 bp | [-6.641, +15.258] | 27.464 vs 23.242 | difference |
| LB vs SC | after 13:30 | 13 | 13 | cont30 | +1.928 bp | [-10.850, +15.200] | -2.763 vs -4.691 | difference |
| LB vs SC | after 13:30 | 13 | 13 | hit30 | +0.027 rate | [-0.333, +0.400] | 0.385 vs 0.357 | difference |
| LB vs SC | all day | 81 | 63 | rng60 | +3.854 bp | [-2.351, +10.568] | 34.308 vs 30.454 | difference |
| LB vs SC | all day | 69 | 56 | cont30 | -4.916 bp | [-12.526, +2.070] | -3.634 vs 1.282 | difference |
| LB vs SC | all day | 69 | 56 | hit30 | -0.118 rate | [-0.284, +0.055] | 0.406 vs 0.524 | difference |
| SB vs LU | to 11:30 | 54 | 52 | rng60 | -9.400 bp | [-26.481, +4.221] | 35.194 vs 44.594 | difference |
| SB vs LU | to 11:30 | 54 | 52 | cont30 | -1.809 bp | [-13.069, +11.193] | -0.676 vs 1.133 | difference |
| SB vs LU | to 11:30 | 54 | 52 | hit30 | -0.111 rate | [-0.387, +0.173] | 0.556 vs 0.667 | difference |
| SB vs LU | 11:30-13:30 | 44 | 37 | rng60 | +8.920 bp | [-4.437, +24.797] | 38.896 vs 29.976 | difference |
| SB vs LU | 11:30-13:30 | 44 | 37 | cont30 | +4.215 bp | [-4.710, +13.341] | 3.639 vs -0.576 | difference |
| SB vs LU | 11:30-13:30 | 44 | 37 | hit30 | +0.256 rate | [-0.062, +0.549] | 0.614 vs 0.357 | difference |
| SB vs LU | after 13:30 | 51 | 49 | rng60 | +0.844 bp | [-15.637, +12.003] | 24.809 vs 23.965 | difference |
| SB vs LU | after 13:30 | 25 | 25 | cont30 | +0.659 bp | [-4.518, +6.233] | 0.471 vs -0.188 | difference |
| SB vs LU | after 13:30 | 25 | 25 | hit30 | -0.076 rate | [-0.458, +0.317] | 0.480 vs 0.556 | difference |
| SB vs LU | all day | 149 | 96 | rng60 | +0.393 bp | [-6.536, +6.589] | 32.732 vs 32.339 | difference |
| SB vs LU | all day | 123 | 81 | cont30 | +0.910 bp | [-5.389, +7.712] | 1.100 vs 0.190 | difference |
| SB vs LU | all day | 123 | 81 | hit30 | +0.035 rate | [-0.156, +0.228] | 0.561 vs 0.526 | difference |

*Each row is the first class of the pair MINUS the second, both at the same price sign. Printed: cont30, rng60, hit30; all 14 outcomes per cell are computed and in `data/cells.csv`.*

## A2 — transitions between consecutive windows   [exploratory]

The previous window's class against the current one, and the **next** window's 30-minute continuation in bp (signed, so the effect is the level). SC → LB and LU → SB are called out below each table.


### A2 step=15 min · OI=F · all   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 362 | 160 | nxt_cont30 | +0.699 bp | [-1.286, +2.730] | 0.353 vs -0.346 | difference |
| LB → SC | 138 | 106 | nxt_cont30 | -4.072 bp | [-7.406, -0.861] | -3.675 vs 0.397 | difference |
| LB → SB | 439 | 184 | nxt_cont30 | -0.570 bp | [-2.520, +1.463] | -0.651 vs -0.080 | difference |
| LB → LU | 93 | 74 | nxt_cont30 | -1.569 bp | [-5.398, +1.973] | -1.473 vs 0.096 | difference |
| SC → LB | 78 | 65 | nxt_cont30 | +1.060 bp | [-2.478, +4.271] | 0.882 vs -0.178 | difference |
| SC → SC | 125 | 77 | nxt_cont30 | +2.434 bp | [-0.702, +5.332] | 0.910 vs -1.524 | difference |
| SC → SB | 128 | 103 | nxt_cont30 | +0.515 bp | [-2.132, +3.322] | 0.156 vs -0.359 | difference |
| SC → LU | 118 | 86 | nxt_cont30 | +0.367 bp | [-2.892, +3.559] | -0.045 vs -0.412 | difference |
| SB → LB | 473 | 191 | nxt_cont30 | -0.891 bp | [-2.882, +1.022] | -0.572 vs 0.319 | difference |
| SB → SC | 100 | 83 | nxt_cont30 | +1.742 bp | [-2.096, +5.648] | 0.506 vs -1.236 | difference |
| SB → SB | 481 | 175 | nxt_cont30 | +1.363 bp | [-0.596, +3.250] | 0.485 vs -0.878 | difference |
| SB → LU | 80 | 68 | nxt_cont30 | +0.517 bp | [-4.619, +6.105] | 0.110 vs -0.407 | difference |
| LU → LB | 102 | 79 | nxt_cont30 | -0.153 bp | [-3.277, +2.815] | -0.234 vs -0.081 | difference |
| LU → SC | 88 | 72 | nxt_cont30 | +0.486 bp | [-2.816, +3.704] | -0.458 vs -0.944 | difference |
| LU → SB | 88 | 79 | nxt_cont30 | -3.485 bp | [-8.131, +1.025] | -3.516 vs -0.031 | difference |
| LU → LU | 81 | 58 | nxt_cont30 | +0.748 bp | [-2.927, +4.469] | 0.289 vs -0.459 | difference |

**SC → LB**: n=78 over 65 sessions. Next-window cont30 **+1.060 bp against other transitions into LB**, 95% CI [-2.478, +4.271]. Raw levels 0.882 vs -0.178 bp (levels, not effects).

**LU → SB**: n=88 over 79 sessions. Next-window cont30 **-3.485 bp against other transitions into SB**, 95% CI [-8.131, +1.025]. Raw levels -3.516 vs -0.031 bp (levels, not effects).

### A2 step=15 min · OI=F · no-expiry   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 316 | 141 | nxt_cont30 | +0.867 bp | [-1.296, +3.171] | 0.417 vs -0.451 | difference |
| LB → SC | 123 | 96 | nxt_cont30 | -3.652 bp | [-7.454, -0.196] | -3.303 vs 0.348 | difference |
| LB → SB | 384 | 163 | nxt_cont30 | -0.789 bp | [-2.933, +1.376] | -1.362 vs -0.573 | difference |
| LB → LU | 84 | 66 | nxt_cont30 | -1.039 bp | [-4.932, +2.717] | -1.214 vs -0.175 | difference |
| SC → LB | 66 | 56 | nxt_cont30 | +0.710 bp | [-2.669, +4.317] | 0.514 vs -0.196 | difference |
| SC → SC | 116 | 71 | nxt_cont30 | +1.990 bp | [-1.224, +5.256] | 0.684 vs -1.306 | difference |
| SC → SB | 112 | 91 | nxt_cont30 | +1.519 bp | [-1.532, +4.717] | 0.471 vs -1.047 | difference |
| SC → LU | 117 | 85 | nxt_cont30 | +0.411 bp | [-3.059, +3.848] | -0.153 vs -0.564 | difference |
| SB → LB | 418 | 171 | nxt_cont30 | -0.683 bp | [-2.832, +1.349] | -0.507 vs 0.175 | difference |
| SB → SC | 88 | 73 | nxt_cont30 | +1.567 bp | [-2.649, +5.916] | 0.487 vs -1.080 | difference |
| SB → SB | 419 | 157 | nxt_cont30 | +1.111 bp | [-0.855, +3.127] | -0.233 vs -1.343 | difference |
| SB → LU | 69 | 58 | nxt_cont30 | -0.128 bp | [-5.881, +5.920] | -0.529 vs -0.400 | difference |
| LU → LB | 94 | 71 | nxt_cont30 | -0.816 bp | [-3.958, +2.311] | -0.874 vs -0.058 | difference |
| LU → SC | 84 | 68 | nxt_cont30 | +0.609 bp | [-2.859, +4.012] | -0.260 vs -0.869 | difference |
| LU → SB | 83 | 74 | nxt_cont30 | -3.082 bp | [-7.966, +1.466] | -3.703 vs -0.621 | difference |
| LU → LU | 78 | 55 | nxt_cont30 | +0.684 bp | [-3.166, +4.578] | 0.105 vs -0.579 | difference |

**SC → LB**: n=66 over 56 sessions. Next-window cont30 **+0.710 bp against other transitions into LB**, 95% CI [-2.669, +4.317]. Raw levels 0.514 vs -0.196 bp (levels, not effects).

**LU → SB**: n=83 over 74 sessions. Next-window cont30 **-3.082 bp against other transitions into SB**, 95% CI [-7.966, +1.466]. Raw levels -3.703 vs -0.621 bp (levels, not effects).

### A2 step=15 min · OI=F1 · all   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 391 | 177 | nxt_cont30 | +0.486 bp | [-1.252, +2.266] | 0.422 vs -0.064 | difference |
| LB → SC | 238 | 155 | nxt_cont30 | -3.553 bp | [-5.828, -1.485] | -3.166 vs 0.387 | difference |
| LB → SB | 481 | 197 | nxt_cont30 | +0.234 bp | [-1.761, +2.325] | -0.767 vs -1.000 | difference |
| LB → LU | 203 | 137 | nxt_cont30 | +0.474 bp | [-2.039, +2.918] | 1.056 vs 0.582 | difference |
| SC → LB | 164 | 119 | nxt_cont30 | +0.243 bp | [-1.890, +2.465] | 0.294 vs 0.051 | difference |
| SC → SC | 335 | 150 | nxt_cont30 | +0.932 bp | [-1.051, +2.828] | 0.259 vs -0.674 | difference |
| SC → SB | 219 | 157 | nxt_cont30 | -0.212 bp | [-2.295, +1.962] | -1.100 vs -0.888 | difference |
| SC → LU | 370 | 177 | nxt_cont30 | -1.484 bp | [-3.490, +0.551] | -0.269 vs 1.215 | difference |
| SB → LB | 539 | 206 | nxt_cont30 | -0.823 bp | [-2.611, +0.904] | -0.401 vs 0.422 | difference |
| SB → SC | 205 | 146 | nxt_cont30 | +2.315 bp | [+0.144, +4.591] | 1.493 vs -0.822 | difference |
| SB → SB | 519 | 185 | nxt_cont30 | -0.096 bp | [-1.653, +1.554] | -0.982 vs -0.886 | difference |
| SB → LU | 167 | 126 | nxt_cont30 | -0.107 bp | [-3.058, +2.726] | 0.587 vs 0.694 | difference |
| LU → LB | 209 | 148 | nxt_cont30 | +0.525 bp | [-1.546, +2.828] | 0.523 vs -0.003 | difference |
| LU → SC | 314 | 161 | nxt_cont30 | +0.265 bp | [-1.264, +1.913] | -0.199 vs -0.464 | difference |
| LU → SB | 195 | 139 | nxt_cont30 | -0.020 bp | [-3.283, +2.941] | -0.938 vs -0.918 | difference |
| LU → LU | 280 | 132 | nxt_cont30 | +1.417 bp | [-0.690, +3.616] | 1.704 vs 0.287 | difference |

**SC → LB**: n=164 over 119 sessions. Next-window cont30 **+0.243 bp against other transitions into LB**, 95% CI [-1.890, +2.465]. Raw levels 0.294 vs 0.051 bp (levels, not effects).

**LU → SB**: n=195 over 139 sessions. Next-window cont30 **-0.020 bp against other transitions into SB**, 95% CI [-3.283, +2.941]. Raw levels -0.938 vs -0.918 bp (levels, not effects).

### A2 step=15 min · OI=F1 · no-expiry   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 358 | 166 | nxt_cont30 | +0.902 bp | [-0.871, +2.800] | 0.793 vs -0.109 | difference |
| LB → SC | 222 | 144 | nxt_cont30 | -3.293 bp | [-5.585, -1.181] | -3.223 vs 0.070 | difference |
| LB → SB | 445 | 183 | nxt_cont30 | +0.267 bp | [-1.725, +2.400] | -0.955 vs -1.221 | difference |
| LB → LU | 184 | 123 | nxt_cont30 | -0.180 bp | [-2.524, +2.308] | 0.376 vs 0.556 | difference |
| SC → LB | 143 | 105 | nxt_cont30 | -0.085 bp | [-2.406, +2.377] | 0.085 vs 0.170 | difference |
| SC → SC | 293 | 133 | nxt_cont30 | +0.916 bp | [-1.081, +2.963] | -0.047 vs -0.963 | difference |
| SC → SB | 200 | 141 | nxt_cont30 | -0.182 bp | [-2.364, +2.027] | -1.285 vs -1.103 | difference |
| SC → LU | 325 | 158 | nxt_cont30 | -0.676 bp | [-2.735, +1.482] | 0.089 vs 0.764 | difference |
| SB → LB | 503 | 190 | nxt_cont30 | -1.202 bp | [-3.057, +0.797] | -0.538 vs 0.664 | difference |
| SB → SC | 187 | 132 | nxt_cont30 | +2.487 bp | [+0.163, +4.920] | 1.320 vs -1.167 | difference |
| SB → SB | 491 | 175 | nxt_cont30 | -0.077 bp | [-1.774, +1.471] | -1.179 vs -1.102 | difference |
| SB → LU | 147 | 111 | nxt_cont30 | -0.016 bp | [-3.162, +3.378] | 0.505 vs 0.521 | difference |
| LU → LB | 196 | 137 | nxt_cont30 | +0.826 bp | [-1.295, +3.181] | 0.851 vs 0.025 | difference |
| LU → SC | 265 | 143 | nxt_cont30 | +0.006 bp | [-1.651, +1.641] | -0.682 vs -0.687 | difference |
| LU → SB | 176 | 126 | nxt_cont30 | -0.157 bp | [-3.536, +2.733] | -1.266 vs -1.110 | difference |
| LU → LU | 237 | 115 | nxt_cont30 | +0.964 bp | [-1.259, +3.167] | 1.227 vs 0.263 | difference |

**SC → LB**: n=143 over 105 sessions. Next-window cont30 **-0.085 bp against other transitions into LB**, 95% CI [-2.406, +2.377]. Raw levels 0.085 vs 0.170 bp (levels, not effects).

**LU → SB**: n=176 over 126 sessions. Next-window cont30 **-0.157 bp against other transitions into SB**, 95% CI [-3.536, +2.733]. Raw levels -1.266 vs -1.110 bp (levels, not effects).

### A2 step=30 min · OI=F · all   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 180 | 96 | nxt_cont30 | -1.820 bp | [-4.640, +1.129] | -1.051 vs 0.769 | difference |
| LB → SC | 60 | 51 | nxt_cont30 | -3.224 bp | [-7.209, +0.637] | -1.260 vs 1.963 | difference |
| LB → SB | 194 | 136 | nxt_cont30 | +2.225 bp | [-0.437, +4.961] | 0.963 vs -1.262 | difference |
| LB → LU | 47 | 45 | nxt_cont30 | +6.831 bp | [+1.514, +13.052] | 3.200 vs -3.631 | difference |
| SC → LB | 43 | 41 | nxt_cont30 | -2.435 bp | [-6.785, +1.651] | -2.136 vs 0.299 | difference |
| SC → SC | 56 | 39 | nxt_cont30 | +4.666 bp | [-0.372, +9.945] | 4.224 vs -0.443 | difference |
| SC → SB | 49 | 49 | nxt_cont30 | +0.406 bp | [-4.968, +6.114] | -0.047 vs -0.453 | difference |
| SC → LU | 44 | 37 | nxt_cont30 | -1.881 bp | [-8.906, +3.930] | -3.003 vs -1.122 | difference |
| SB → LB | 210 | 143 | nxt_cont30 | +2.533 bp | [-0.033, +5.108] | 1.489 vs -1.044 | difference |
| SB → SC | 39 | 36 | nxt_cont30 | -1.701 bp | [-8.011, +4.472] | -0.410 vs 1.291 | difference |
| SB → SB | 231 | 121 | nxt_cont30 | -1.981 bp | [-4.635, +0.697] | -1.496 vs 0.485 | difference |
| SB → LU | 39 | 34 | nxt_cont30 | +1.661 bp | [-4.157, +7.482] | -0.378 vs -2.039 | difference |
| LU → LB | 41 | 38 | nxt_cont30 | +0.056 bp | [-5.754, +5.621] | 0.129 vs 0.073 | difference |
| LU → SC | 34 | 33 | nxt_cont30 | +0.028 bp | [-3.591, +3.707] | 0.963 vs 0.935 | difference |
| LU → SB | 35 | 34 | nxt_cont30 | -1.082 bp | [-7.728, +5.450] | -1.421 vs -0.340 | difference |
| LU → LU | 31 | 23 | nxt_cont30 | -8.641 bp | [-19.693, -0.956] | -8.613 vs 0.027 | difference |

**SC → LB**: n=43 over 41 sessions. Next-window cont30 **-2.435 bp against other transitions into LB**, 95% CI [-6.785, +1.651]. Raw levels -2.136 vs 0.299 bp (levels, not effects).

**LU → SB**: n=35 over 34 sessions. Next-window cont30 **-1.082 bp against other transitions into SB**, 95% CI [-7.728, +5.450]. Raw levels -1.421 vs -0.340 bp (levels, not effects).

### A2 step=30 min · OI=F · no-expiry   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 158 | 86 | nxt_cont30 | -2.226 bp | [-5.248, +0.797] | -1.671 vs 0.555 | difference |
| LB → SC | 56 | 48 | nxt_cont30 | -3.502 bp | [-7.677, +0.678] | -1.539 vs 1.963 | difference |
| LB → SB | 170 | 121 | nxt_cont30 | +2.180 bp | [-0.743, +5.065] | 0.898 vs -1.282 | difference |
| LB → LU | 43 | 41 | nxt_cont30 | +6.450 bp | [+1.004, +12.504] | 2.230 vs -4.220 | difference |
| SC → LB | 39 | 38 | nxt_cont30 | -2.187 bp | [-6.925, +2.386] | -2.266 vs -0.079 | difference |
| SC → SC | 53 | 36 | nxt_cont30 | +4.748 bp | [-0.588, +10.390] | 4.182 vs -0.567 | difference |
| SC → SB | 48 | 48 | nxt_cont30 | +0.279 bp | [-5.206, +6.054] | -0.199 vs -0.478 | difference |
| SC → LU | 42 | 35 | nxt_cont30 | -2.161 bp | [-8.849, +3.809] | -3.991 vs -1.830 | difference |
| SB → LB | 186 | 126 | nxt_cont30 | +3.059 bp | [+0.221, +5.765] | 1.422 vs -1.637 | difference |
| SB → SC | 34 | 31 | nxt_cont30 | -1.671 bp | [-8.301, +5.222] | -0.495 vs 1.176 | difference |
| SB → SB | 193 | 105 | nxt_cont30 | -1.905 bp | [-4.691, +0.700] | -1.525 vs 0.381 | difference |
| SB → LU | 38 | 33 | nxt_cont30 | +2.031 bp | [-3.769, +7.985] | -0.889 vs -2.920 | difference |
| LU → LB | 37 | 34 | nxt_cont30 | -0.600 bp | [-6.954, +5.359] | -0.829 vs -0.229 | difference |
| LU → SC | 34 | 33 | nxt_cont30 | +0.133 bp | [-3.762, +3.745] | 0.963 vs 0.830 | difference |
| LU → SB | 33 | 32 | nxt_cont30 | -1.072 bp | [-7.976, +5.281] | -1.440 vs -0.368 | difference |
| LU → LU | 31 | 23 | nxt_cont30 | -7.756 bp | [-18.517, +0.056] | -8.613 vs -0.858 | difference |

**SC → LB**: n=39 over 38 sessions. Next-window cont30 **-2.187 bp against other transitions into LB**, 95% CI [-6.925, +2.386]. Raw levels -2.266 vs -0.079 bp (levels, not effects).

**LU → SB**: n=33 over 32 sessions. Next-window cont30 **-1.072 bp against other transitions into SB**, 95% CI [-7.976, +5.281]. Raw levels -1.440 vs -0.368 bp (levels, not effects).

### A2 step=30 min · OI=F1 · all   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 168 | 100 | nxt_cont30 | -2.046 bp | [-4.579, +0.667] | -1.787 vs 0.258 | difference |
| LB → SC | 130 | 107 | nxt_cont30 | -1.364 bp | [-3.639, +0.945] | -0.384 vs 0.980 | difference |
| LB → SB | 197 | 136 | nxt_cont30 | -0.069 bp | [-2.251, +2.149] | 0.053 vs 0.123 | difference |
| LB → LU | 103 | 85 | nxt_cont30 | +3.319 bp | [-0.452, +7.374] | 2.189 vs -1.130 | difference |
| SC → LB | 92 | 77 | nxt_cont30 | +0.236 bp | [-2.523, +3.011] | -0.131 vs -0.367 | difference |
| SC → SC | 165 | 94 | nxt_cont30 | +0.528 bp | [-1.672, +2.667] | 0.992 vs 0.463 | difference |
| SC → SB | 110 | 100 | nxt_cont30 | +1.612 bp | [-1.654, +5.175] | 1.436 vs -0.176 | difference |
| SC → LU | 143 | 103 | nxt_cont30 | +0.019 bp | [-2.862, +2.716] | -0.340 vs -0.359 | difference |
| SB → LB | 230 | 148 | nxt_cont30 | +1.482 bp | [-1.059, +4.074] | 0.568 vs -0.914 | difference |
| SB → SC | 91 | 79 | nxt_cont30 | +2.264 bp | [-1.053, +5.550] | 2.495 vs 0.231 | difference |
| SB → SB | 246 | 125 | nxt_cont30 | -1.319 bp | [-3.655, +0.856] | -0.711 vs 0.608 | difference |
| SB → LU | 82 | 73 | nxt_cont30 | +0.033 bp | [-3.024, +3.061] | -0.326 vs -0.359 | difference |
| LU → LB | 94 | 82 | nxt_cont30 | +0.252 bp | [-3.415, +3.543] | -0.118 vs -0.371 | difference |
| LU → SC | 126 | 88 | nxt_cont30 | -1.013 bp | [-3.703, +1.803] | -0.130 vs 0.883 | difference |
| LU → SB | 87 | 77 | nxt_cont30 | +0.830 bp | [-2.605, +4.029] | 0.818 vs -0.011 | difference |
| LU → LU | 112 | 73 | nxt_cont30 | -3.184 bp | [-6.936, +0.438] | -2.726 vs 0.458 | difference |

**SC → LB**: n=92 over 77 sessions. Next-window cont30 **+0.236 bp against other transitions into LB**, 95% CI [-2.523, +3.011]. Raw levels -0.131 vs -0.367 bp (levels, not effects).

**LU → SB**: n=87 over 77 sessions. Next-window cont30 **+0.830 bp against other transitions into SB**, 95% CI [-2.605, +4.029]. Raw levels 0.818 vs -0.011 bp (levels, not effects).

### A2 step=30 min · OI=F1 · no-expiry   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 150 | 92 | nxt_cont30 | -2.402 bp | [-5.059, +0.258] | -2.029 vs 0.372 | difference |
| LB → SC | 119 | 98 | nxt_cont30 | -1.716 bp | [-4.097, +0.665] | -0.759 vs 0.957 | difference |
| LB → SB | 188 | 129 | nxt_cont30 | +0.217 bp | [-1.882, +2.374] | -0.105 vs -0.322 | difference |
| LB → LU | 97 | 80 | nxt_cont30 | +3.463 bp | [-0.403, +7.447] | 2.194 vs -1.269 | difference |
| SC → LB | 78 | 67 | nxt_cont30 | +0.627 bp | [-2.457, +3.543] | 0.236 vs -0.391 | difference |
| SC → SC | 149 | 85 | nxt_cont30 | +0.899 bp | [-1.467, +3.304] | 1.116 vs 0.217 | difference |
| SC → SB | 104 | 95 | nxt_cont30 | +1.718 bp | [-1.573, +5.365] | 1.166 vs -0.552 | difference |
| SC → LU | 120 | 89 | nxt_cont30 | -0.974 bp | [-4.151, +2.004] | -1.051 vs -0.078 | difference |
| SB → LB | 218 | 139 | nxt_cont30 | +1.402 bp | [-1.201, +3.940] | 0.532 vs -0.870 | difference |
| SB → SC | 82 | 71 | nxt_cont30 | +2.685 bp | [-0.950, +6.422] | 2.713 vs 0.028 | difference |
| SB → SB | 231 | 119 | nxt_cont30 | -1.130 bp | [-3.453, +1.236] | -0.950 vs 0.181 | difference |
| SB → LU | 75 | 66 | nxt_cont30 | -0.359 bp | [-3.443, +2.777] | -0.673 vs -0.314 | difference |
| LU → LB | 90 | 79 | nxt_cont30 | +0.484 bp | [-3.415, +4.310] | 0.103 vs -0.381 | difference |
| LU → SC | 107 | 77 | nxt_cont30 | -1.463 bp | [-4.465, +1.261] | -0.610 vs 0.852 | difference |
| LU → SB | 77 | 67 | nxt_cont30 | -0.226 bp | [-3.682, +3.182] | -0.451 vs -0.226 | difference |
| LU → LU | 88 | 63 | nxt_cont30 | -2.198 bp | [-6.347, +1.258] | -2.074 vs 0.124 | difference |

**SC → LB**: n=78 over 67 sessions. Next-window cont30 **+0.627 bp against other transitions into LB**, 95% CI [-2.457, +3.543]. Raw levels 0.236 vs -0.391 bp (levels, not effects).

**LU → SB**: n=77 over 67 sessions. Next-window cont30 **-0.226 bp against other transitions into SB**, 95% CI [-3.682, +3.182]. Raw levels -0.451 vs -0.226 bp (levels, not effects).

### A2 step=60 min · OI=F · all   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 78 | 50 | nxt_cont30 | -4.745 bp | [-8.646, -0.629] | -2.642 vs 2.103 | difference |
| LB → SC | 21 | 21 | nxt_cont30 | +0.695 bp | [-5.853, +7.884] | -1.736 vs -2.431 | difference |
| LB → SB | 70 | 67 | nxt_cont30 | -1.133 bp | [-5.857, +3.441] | -1.677 vs -0.544 | difference |
| LB → LU | 19 | 18 | nxt_cont30 | -14.558 bp | [-29.802, -1.402] | -3.504 vs 11.053 | difference |
| SC → LB | 19 | 18 | nxt_cont30 | -2.151 bp | [-9.292, +5.157] | -1.799 vs 0.352 | difference |
| SC → SC | 18 | 14 | nxt_cont30 | +1.595 bp | [-5.259, +8.577] | -1.035 vs -2.630 | difference |
| SC → SB | 9 | 9 | nxt_cont30 | +4.785 bp | [-7.766, +17.544] | 3.533 vs -1.252 | difference |
| SC → LU | 13 | 12 | nxt_cont30 | +15.161 bp | [-1.295, +36.971] | 15.449 vs 0.288 | difference |
| SB → LB | 72 | 67 | nxt_cont30 | +4.147 bp | [+0.498, +8.011] | 2.693 vs -1.454 | difference |
| SB → SC | 24 | 24 | nxt_cont30 | -3.178 bp | [-13.023, +4.881] | -4.329 vs -1.151 | difference |
| SB → SB | 84 | 58 | nxt_cont30 | -0.114 bp | [-5.334, +5.161] | -1.061 vs -0.948 | difference |
| SB → LU | 9 | 9 | nxt_cont30 | +0.378 bp | [-20.595, +23.106] | 5.068 vs 4.690 | difference |
| LU → LB | 19 | 19 | nxt_cont30 | +4.043 bp | [-3.588, +12.645] | 3.769 vs -0.274 | difference |
| LU → SC | 8 | 8 | nxt_cont30 | +2.645 bp | [-7.522, +11.877] | 0.121 vs -2.524 | difference |
| LU → SB | 10 | 10 | nxt_cont30 | +1.198 bp | [-6.918, +9.317] | 0.126 vs -1.072 | difference |
| LU → LU | 3 | 2 | nxt_cont30 | +5.577 bp | [-14.749, +39.051] | 9.964 vs 4.387 | difference |

**SC → LB**: n=19 over 18 sessions. Next-window cont30 **-2.151 bp against other transitions into LB**, 95% CI [-9.292, +5.157]. Raw levels -1.799 vs 0.352 bp (levels, not effects).

**LU → SB**: n=10 over 10 sessions. Next-window cont30 **+1.198 bp against other transitions into SB**, 95% CI [-6.918, +9.317]. Raw levels 0.126 vs -1.072 bp (levels, not effects).

### A2 step=60 min · OI=F · no-expiry   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 73 | 46 | nxt_cont30 | -4.124 bp | [-8.253, +0.046] | -1.977 vs 2.147 | difference |
| LB → SC | 19 | 19 | nxt_cont30 | +1.506 bp | [-5.581, +8.997] | -1.463 vs -2.969 | difference |
| LB → SB | 58 | 57 | nxt_cont30 | -1.778 bp | [-6.545, +3.180] | -1.830 vs -0.051 | difference |
| LB → LU | 18 | 17 | nxt_cont30 | -13.331 bp | [-28.972, +0.473] | -3.673 vs 9.658 | difference |
| SC → LB | 17 | 16 | nxt_cont30 | -2.292 bp | [-10.338, +6.395] | -1.714 vs 0.578 | difference |
| SC → SC | 16 | 12 | nxt_cont30 | +2.368 bp | [-5.719, +9.929] | -0.744 vs -3.112 | difference |
| SC → SB | 8 | 8 | nxt_cont30 | +2.342 bp | [-10.470, +16.829] | 1.473 vs -0.869 | difference |
| SC → LU | 12 | 11 | nxt_cont30 | +12.711 bp | [-3.008, +34.347] | 13.024 vs 0.313 | difference |
| SB → LB | 59 | 55 | nxt_cont30 | +4.100 bp | [+0.002, +8.366] | 2.996 vs -1.104 | difference |
| SB → SC | 22 | 22 | nxt_cont30 | -4.810 bp | [-15.188, +4.136] | -5.711 vs -0.901 | difference |
| SB → SB | 73 | 51 | nxt_cont30 | +0.982 bp | [-4.427, +6.479] | -0.243 vs -1.225 | difference |
| SB → LU | 9 | 9 | nxt_cont30 | +1.429 bp | [-18.748, +23.335] | 5.068 vs 3.639 | difference |
| LU → LB | 18 | 18 | nxt_cont30 | +2.990 bp | [-4.959, +11.676] | 3.012 vs 0.022 | difference |
| LU → SC | 8 | 8 | nxt_cont30 | +3.022 bp | [-7.814, +12.600] | 0.121 vs -2.901 | difference |
| LU → SB | 10 | 10 | nxt_cont30 | +0.932 bp | [-7.846, +9.337] | 0.126 vs -0.806 | difference |
| LU → LU | 3 | 2 | nxt_cont30 | +6.482 bp | [-13.615, +41.152] | 9.964 vs 3.482 | difference |

**SC → LB**: n=17 over 16 sessions. Next-window cont30 **-2.292 bp against other transitions into LB**, 95% CI [-10.338, +6.395]. Raw levels -1.714 vs 0.578 bp (levels, not effects).

**LU → SB**: n=10 over 10 sessions. Next-window cont30 **+0.932 bp against other transitions into SB**, 95% CI [-7.846, +9.337]. Raw levels 0.126 vs -0.806 bp (levels, not effects).

### A2 step=60 min · OI=F1 · all   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 66 | 45 | nxt_cont30 | -5.402 bp | [-8.967, -2.040] | -3.129 vs 2.273 | difference |
| LB → SC | 43 | 43 | nxt_cont30 | -3.002 bp | [-8.011, +1.976] | -3.051 vs -0.049 | difference |
| LB → SB | 58 | 56 | nxt_cont30 | -0.446 bp | [-4.210, +3.132] | -0.635 vs -0.189 | difference |
| LB → LU | 38 | 37 | nxt_cont30 | +0.818 bp | [-5.186, +5.864] | 0.584 vs -0.234 | difference |
| SC → LB | 33 | 33 | nxt_cont30 | +2.606 bp | [-2.087, +7.565] | 2.699 vs 0.093 | difference |
| SC → SC | 63 | 44 | nxt_cont30 | +0.319 bp | [-4.174, +4.815] | -0.536 vs -0.855 | difference |
| SC → SB | 26 | 26 | nxt_cont30 | +2.394 bp | [-2.973, +7.950] | 1.780 vs -0.615 | difference |
| SC → LU | 48 | 45 | nxt_cont30 | +1.558 bp | [-5.615, +9.051] | 1.007 vs -0.551 | difference |
| SB → LB | 75 | 70 | nxt_cont30 | +2.897 bp | [-0.440, +6.108] | 2.343 vs -0.554 | difference |
| SB → SC | 41 | 41 | nxt_cont30 | -4.534 bp | [-11.065, +0.928] | -4.276 vs 0.258 | difference |
| SB → SB | 85 | 56 | nxt_cont30 | -0.186 bp | [-3.931, +3.470] | -0.424 vs -0.238 | difference |
| SB → LU | 26 | 26 | nxt_cont30 | -0.162 bp | [-12.104, +12.433] | -0.141 vs 0.022 | difference |
| LU → LB | 29 | 29 | nxt_cont30 | +1.270 bp | [-3.966, +6.956] | 1.605 vs 0.335 | difference |
| LU → SC | 38 | 37 | nxt_cont30 | +7.634 bp | [+2.641, +13.199] | 5.319 vs -2.315 | difference |
| LU → SB | 38 | 38 | nxt_cont30 | -0.854 bp | [-6.248, +4.405] | -1.012 vs -0.157 | difference |
| LU → LU | 26 | 20 | nxt_cont30 | -3.216 bp | [-10.036, +4.062] | -2.619 vs 0.597 | difference |

**SC → LB**: n=33 over 33 sessions. Next-window cont30 **+2.606 bp against other transitions into LB**, 95% CI [-2.087, +7.565]. Raw levels 2.699 vs 0.093 bp (levels, not effects).

**LU → SB**: n=38 over 38 sessions. Next-window cont30 **-0.854 bp against other transitions into SB**, 95% CI [-6.248, +4.405]. Raw levels -1.012 vs -0.157 bp (levels, not effects).

### A2 step=60 min · OI=F1 · no-expiry   [exploratory]

Effect is the pair's next-window cont30 **minus the other transitions into the same `cur`** — current class held fixed, previous class varied — so the contrast isolates what the previous class adds, and the sample's drift cancels.

| prev → cur  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB → LB | 63 | 44 | nxt_cont30 | -5.467 bp | [-9.356, -1.735] | -3.213 vs 2.255 | difference |
| LB → SC | 39 | 39 | nxt_cont30 | -2.236 bp | [-7.683, +3.124] | -2.438 vs -0.203 | difference |
| LB → SB | 54 | 52 | nxt_cont30 | -0.848 bp | [-4.818, +2.976] | -0.926 vs -0.078 | difference |
| LB → LU | 37 | 36 | nxt_cont30 | +0.541 bp | [-5.725, +6.133] | 0.612 vs 0.071 | difference |
| SC → LB | 30 | 30 | nxt_cont30 | +2.594 bp | [-2.338, +7.699] | 2.660 vs 0.067 | difference |
| SC → SC | 57 | 39 | nxt_cont30 | +1.796 bp | [-2.932, +6.899] | 0.408 vs -1.387 | difference |
| SC → SB | 24 | 24 | nxt_cont30 | +0.830 bp | [-4.481, +7.006] | 0.414 vs -0.417 | difference |
| SC → LU | 37 | 36 | nxt_cont30 | -0.172 bp | [-8.490, +9.049] | 0.125 vs 0.297 | difference |
| SB → LB | 71 | 67 | nxt_cont30 | +2.972 bp | [-0.484, +6.404] | 2.349 vs -0.623 | difference |
| SB → SC | 38 | 38 | nxt_cont30 | -5.098 bp | [-12.108, +0.691] | -4.635 vs 0.463 | difference |
| SB → SB | 80 | 53 | nxt_cont30 | +0.486 bp | [-3.427, +4.194] | -0.028 vs -0.515 | difference |
| SB → LU | 25 | 25 | nxt_cont30 | +0.647 bp | [-11.399, +13.577] | 0.751 vs 0.104 | difference |
| LU → LB | 29 | 29 | nxt_cont30 | +1.335 bp | [-3.682, +6.976] | 1.605 vs 0.269 | difference |
| LU → SC | 26 | 26 | nxt_cont30 | +6.785 bp | [+0.408, +13.321] | 4.935 vs -1.850 | difference |
| LU → SB | 36 | 36 | nxt_cont30 | -0.249 bp | [-5.742, +5.522] | -0.517 vs -0.268 | difference |
| LU → LU | 18 | 14 | nxt_cont30 | -1.448 bp | [-8.564, +5.768] | -0.983 vs 0.465 | difference |

**SC → LB**: n=30 over 30 sessions. Next-window cont30 **+2.594 bp against other transitions into LB**, 95% CI [-2.338, +7.699]. Raw levels 2.660 vs 0.067 bp (levels, not effects).

**LU → SB**: n=36 over 36 sessions. Next-window cont30 **-0.249 bp against other transitions into SB**, 95% CI [-5.742, +5.522]. Raw levels -0.517 vs -0.268 bp (levels, not effects).

## A3 — day level   [exploratory]

Class from close-to-close dP and dOI; the outcome is the **next** session. Every effect is a difference against the PAIRED class at the same price sign (LB vs SC, SB vs LU).


### A3 OI=F · all   [exploratory]

Composition (counts only): LB 58 · SC 62 · SB 87 · LU 34 · FLAT 0 · MISSING 4

Contrasts hold the price sign fixed: LB vs SC, SB vs LU.

| contrast  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB vs SC | 57 | 57 | retnext | -38.757 bp | [-67.881, -10.501] | -27.273 vs 11.484 | difference |
| LB vs SC | 57 | 57 | contnext | -38.757 bp | [-67.881, -10.501] | -27.273 vs 11.484 | difference |
| LB vs SC | 58 | 58 | rngnext | +11.734 bp | [-4.108, +27.859] | 88.816 vs 77.082 | difference |
| SB vs LU | 87 | 87 | retnext | -67.568 bp | [-105.332, -31.317] | -15.876 vs 51.692 | difference |
| SB vs LU | 87 | 87 | contnext | +67.568 bp | [+31.317, +105.332] | 15.876 vs -51.692 | difference |
| SB vs LU | 87 | 87 | rngnext | +12.983 bp | [-7.102, +31.755] | 100.534 vs 87.551 | difference |

**Runs of the same day class** — contnext against the same class's other run lengths

| class | run length  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB | 1 | 44 | 44 | contnext | +4.898 bp | [-48.257, +62.658] | -26.156 vs -31.054 | difference |
| LB | 2 | 9 | 9 | contnext | -31.286 bp | [-101.673, +38.690] | -53.619 vs -22.334 | difference |
| LB | 3+ | 4 | 4 | contnext | +50.537 bp | [+8.132, +91.751] | 19.717 vs -30.820 | difference |
| SC | 1 | 45 | 45 | contnext | +12.456 bp | [-24.932, +47.118] | 14.899 vs 2.443 | difference |
| SC | 2 | 13 | 13 | contnext | +6.579 bp | [-32.856, +49.919] | 16.683 vs 10.105 | difference |
| SC | 3+ | 4 | 4 | contnext | -59.136 bp | [-80.255, -36.672] | -43.837 vs 15.299 | difference |
| SB | 1 | 48 | 48 | contnext | +23.049 bp | [-14.767, +59.194] | 26.208 vs 3.159 | difference |
| SB | 2 | 24 | 24 | contnext | +11.609 bp | [-31.949, +57.129] | 24.282 vs 12.673 | difference |
| SB | 3+ | 15 | 15 | contnext | -56.205 bp | [-93.979, -17.872] | -30.639 vs 25.566 | difference |
| LU | 1 | 31 | 31 | contnext | -19.151 bp | [-118.673, +99.006] | -53.382 vs -34.231 | difference |
| LU | 2 | 3 | 3 | contnext | +19.151 bp | [-98.310, +122.400] | -34.231 vs -53.382 | difference |

### A3 OI=F · no-expiry   [exploratory]

Composition (counts only): LB 58 · SC 50 · SB 86 · LU 25 · FLAT 0 · MISSING 4

Contrasts hold the price sign fixed: LB vs SC, SB vs LU.

| contrast  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB vs SC | 57 | 57 | retnext | -38.303 bp | [-71.392, -7.246] | -27.273 vs 11.029 | difference |
| LB vs SC | 57 | 57 | contnext | -38.303 bp | [-71.392, -7.246] | -27.273 vs 11.029 | difference |
| LB vs SC | 58 | 58 | rngnext | +10.597 bp | [-8.287, +27.865] | 88.816 vs 78.219 | difference |
| SB vs LU | 86 | 86 | retnext | -50.356 bp | [-95.597, -13.623] | -15.338 vs 35.017 | difference |
| SB vs LU | 86 | 86 | contnext | +50.356 bp | [+13.623, +95.597] | 15.338 vs -35.017 | difference |
| SB vs LU | 86 | 86 | rngnext | +20.440 bp | [-2.246, +39.899] | 100.513 vs 80.073 | difference |

**Runs of the same day class** — contnext against the same class's other run lengths

| class | run length  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB | 1 | 44 | 44 | contnext | +4.898 bp | [-48.257, +62.658] | -26.156 vs -31.054 | difference |
| LB | 2 | 9 | 9 | contnext | -31.286 bp | [-101.673, +38.690] | -53.619 vs -22.334 | difference |
| LB | 3+ | 4 | 4 | contnext | +50.537 bp | [+8.132, +91.751] | 19.717 vs -30.820 | difference |
| SC | 1 | 37 | 37 | contnext | +14.696 bp | [-30.937, +55.725] | 14.850 vs 0.154 | difference |
| SC | 2 | 10 | 10 | contnext | +1.588 bp | [-47.458, +54.490] | 12.300 vs 10.712 | difference |
| SC | 3+ | 3 | 3 | contnext | -54.639 bp | [-80.491, -29.219] | -40.331 vs 14.308 | difference |
| SB | 1 | 47 | 47 | contnext | +22.286 bp | [-15.214, +58.767] | 25.445 vs 3.159 | difference |
| SB | 2 | 24 | 24 | contnext | +12.406 bp | [-31.429, +56.929] | 24.282 vs 11.876 | difference |
| SB | 3+ | 15 | 15 | contnext | -55.690 bp | [-94.431, -16.382] | -30.639 vs 25.052 | difference |
| LU | 1 | 23 | 23 | contnext | -59.115 bp | [-125.572, +4.278] | -39.747 vs 19.368 | difference |
| LU | 2 | 2 | 2 | contnext | +59.115 bp | [-4.223, +122.025] | 19.368 vs -39.747 | difference |

### A3 OI=F1 · all   [exploratory]

Composition (counts only): LB 38 · SC 84 · SB 56 · LU 65 · FLAT 0 · MISSING 2

Contrasts hold the price sign fixed: LB vs SC, SB vs LU.

| contrast  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB vs SC | 37 | 37 | retnext | -24.957 bp | [-56.479, +6.585] | -23.260 vs 1.697 | difference |
| LB vs SC | 37 | 37 | contnext | -24.957 bp | [-56.479, +6.585] | -23.260 vs 1.697 | difference |
| LB vs SC | 38 | 38 | rngnext | +6.742 bp | [-9.865, +23.425] | 87.632 vs 80.890 | difference |
| SB vs LU | 56 | 56 | retnext | -33.039 bp | [-64.715, +1.540] | -14.638 vs 18.401 | difference |
| SB vs LU | 56 | 56 | contnext | +33.039 bp | [-1.540, +64.715] | 14.638 vs -18.401 | difference |
| SB vs LU | 56 | 56 | rngnext | +13.025 bp | [-4.565, +30.956] | 103.883 vs 90.858 | difference |

**Runs of the same day class** — contnext against the same class's other run lengths

| class | run length  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB | 1 | 30 | 30 | contnext | -15.240 bp | [-67.805, +39.770] | -26.143 vs -10.903 | difference |
| LB | 2 | 5 | 5 | contnext | +0.173 bp | [-64.991, +73.133] | -23.111 vs -23.283 | difference |
| LB | 3+ | 2 | 2 | contnext | +45.324 bp | [+17.844, +75.133] | 19.614 vs -25.710 | difference |
| SC | 1 | 55 | 55 | contnext | +1.978 bp | [-36.552, +38.261] | 2.380 vs 0.402 | difference |
| SC | 2 | 19 | 19 | contnext | -3.862 bp | [-46.232, +40.601] | -1.291 vs 2.571 | difference |
| SC | 3+ | 10 | 10 | contnext | +2.182 bp | [-41.802, +46.335] | 3.620 vs 1.438 | difference |
| SB | 1 | 32 | 32 | contnext | +18.547 bp | [-29.946, +71.011] | 22.586 vs 4.040 | difference |
| SB | 2 | 15 | 15 | contnext | +8.945 bp | [-55.355, +73.177] | 21.187 vs 12.242 | difference |
| SB | 3+ | 9 | 9 | contnext | -46.679 bp | [-105.626, +10.942] | -24.539 vs 22.140 | difference |
| LU | 1 | 52 | 52 | contnext | +4.830 bp | [-42.675, +52.327] | -17.435 vs -22.265 | difference |
| LU | 2 | 10 | 10 | contnext | +10.542 bp | [-34.182, +53.574] | -9.481 vs -20.023 | difference |
| LU | 3+ | 3 | 3 | contnext | -48.725 bp | [-188.779, +79.355] | -64.877 vs -16.152 | difference |

### A3 OI=F1 · no-expiry   [exploratory]

Composition (counts only): LB 29 · SC 81 · SB 54 · LU 57 · FLAT 0 · MISSING 2

Contrasts hold the price sign fixed: LB vs SC, SB vs LU.

| contrast  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB vs SC | 28 | 28 | retnext | -28.712 bp | [-68.277, +8.948] | -29.397 vs -0.685 | difference |
| LB vs SC | 28 | 28 | contnext | -28.712 bp | [-68.277, +8.948] | -29.397 vs -0.685 | difference |
| LB vs SC | 29 | 29 | rngnext | +9.840 bp | [-8.625, +29.498] | 91.397 vs 81.557 | difference |
| SB vs LU | 54 | 54 | retnext | -29.618 bp | [-66.195, +4.419] | -19.206 vs 10.412 | difference |
| SB vs LU | 54 | 54 | contnext | +29.618 bp | [-4.419, +66.195] | 19.206 vs -10.412 | difference |
| SB vs LU | 54 | 54 | rngnext | +15.120 bp | [-2.597, +33.598] | 103.674 vs 88.554 | difference |

**Runs of the same day class** — contnext against the same class's other run lengths

| class | run length  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| LB | 1 | 21 | 21 | contnext | -24.658 bp | [-87.017, +35.389] | -35.562 vs -10.903 | difference |
| LB | 2 | 5 | 5 | contnext | +7.653 bp | [-69.887, +81.238] | -23.111 vs -30.764 | difference |
| LB | 3+ | 2 | 2 | contnext | +52.782 bp | [+18.376, +89.532] | 19.614 vs -33.167 | difference |
| SC | 1 | 53 | 53 | contnext | +2.696 bp | [-36.023, +37.957] | 0.247 vs -2.449 | difference |
| SC | 2 | 19 | 19 | contnext | -0.792 bp | [-44.022, +44.238] | -1.291 vs -0.499 | difference |
| SC | 3+ | 9 | 9 | contnext | -4.734 bp | [-47.046, +43.736] | -4.892 vs -0.159 | difference |
| SB | 1 | 30 | 30 | contnext | +27.299 bp | [-23.792, +79.574] | 31.339 vs 4.040 | difference |
| SB | 2 | 15 | 15 | contnext | +2.743 bp | [-59.643, +72.550] | 21.187 vs 18.444 | difference |
| SB | 3+ | 9 | 9 | contnext | -52.494 bp | [-112.245, +1.386] | -24.539 vs 27.955 | difference |
| LU | 1 | 47 | 47 | contnext | -21.731 bp | [-57.750, +14.380] | -14.224 vs 7.507 | difference |
| LU | 2 | 8 | 8 | contnext | +22.902 bp | [-12.279, +57.128] | 9.276 vs -13.626 | difference |
| LU | 3+ | 2 | 2 | contnext | +11.234 bp | [-60.606, +83.045] | 0.428 vs -10.806 | difference |

## B — basis against its usual level   [exploratory]

b = (P − S)/S in **bp of S** at 10:00:59, 12:00:59, 14:00:59 and 15:29:59. The norm is the median b at the same trading days to series-1 expiry and the same clock time, **leaving out the session's own expiry cycle**. dev = b − norm, in bp. Quintiles are of dev within each clock. rng_next is unsigned and given as a difference against the other quintiles.


### B · all   [exploratory]

| clock | quintile  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| 10:00:59 | Q1 | 49 | 49 | ret_to_close | -5.422 bp | [-24.884, +12.119] | -7.081 vs -1.659 | difference |
| 10:00:59 | Q1 | 49 | 49 | ret_next | +21.495 bp | [-9.782, +53.945] | 15.974 vs -5.521 | difference |
| 10:00:59 | Q1 | 49 | 49 | rng_next | +4.488 bp | [-11.863, +21.537] | 93.483 vs 88.994 | difference |
| 10:00:59 | Q2 | 49 | 49 | ret_to_close | +10.379 bp | [-5.900, +27.781] | 5.559 vs -4.819 | difference |
| 10:00:59 | Q2 | 48 | 48 | ret_next | -24.545 bp | [-52.920, +3.275] | -20.884 vs 3.662 | difference |
| 10:00:59 | Q2 | 48 | 48 | rng_next | +12.219 bp | [-3.985, +28.611] | 99.710 vs 87.492 | difference |
| 10:00:59 | Q3 | 49 | 49 | ret_to_close | -4.911 bp | [-19.525, +9.975] | -6.672 vs -1.762 | difference |
| 10:00:59 | Q3 | 49 | 49 | ret_next | -12.800 bp | [-44.970, +16.497] | -11.406 vs 1.394 | difference |
| 10:00:59 | Q3 | 49 | 49 | rng_next | +11.953 bp | [-4.094, +30.820] | 99.448 vs 87.495 | difference |
| 10:00:59 | Q4 | 49 | 49 | ret_to_close | +11.627 bp | [-3.821, +27.905] | 6.558 vs -5.069 | difference |
| 10:00:59 | Q4 | 48 | 48 | ret_next | +32.518 bp | [+7.760, +57.032] | 24.908 vs -7.610 | difference |
| 10:00:59 | Q4 | 49 | 49 | rng_next | -14.407 bp | [-26.107, -1.871] | 78.382 vs 92.789 | difference |
| 10:00:59 | Q5 | 49 | 49 | ret_to_close | -11.673 bp | [-26.797, +4.049] | -12.082 vs -0.409 | difference |
| 10:00:59 | Q5 | 49 | 49 | ret_next | -16.545 bp | [-38.577, +5.736] | -14.396 vs 2.150 | difference |
| 10:00:59 | Q5 | 49 | 49 | rng_next | -14.065 bp | [-25.049, -3.943] | 78.655 vs 92.720 | difference |
| 12:00:59 | Q1 | 49 | 49 | ret_to_close | +7.057 bp | [-8.185, +20.601] | 3.592 vs -3.465 | difference |
| 12:00:59 | Q1 | 49 | 49 | ret_next | +13.748 bp | [-19.727, +49.804] | 9.789 vs -3.959 | difference |
| 12:00:59 | Q1 | 49 | 49 | rng_next | +16.264 bp | [-3.306, +38.608] | 102.894 vs 86.629 | difference |
| 12:00:59 | Q2 | 49 | 49 | ret_to_close | -14.760 bp | [-27.101, -1.961] | -13.862 vs 0.898 | difference |
| 12:00:59 | Q2 | 48 | 48 | ret_next | -10.499 bp | [-38.518, +17.157] | -9.612 vs 0.887 | difference |
| 12:00:59 | Q2 | 48 | 48 | rng_next | +6.714 bp | [-7.805, +22.503] | 95.289 vs 88.575 | difference |
| 12:00:59 | Q3 | 49 | 49 | ret_to_close | +10.605 bp | [-4.046, +25.676] | 6.431 vs -4.175 | difference |
| 12:00:59 | Q3 | 49 | 49 | ret_next | -2.733 bp | [-31.864, +26.124] | -3.369 vs -0.636 | difference |
| 12:00:59 | Q3 | 49 | 49 | rng_next | +0.370 bp | [-13.628, +15.419] | 90.192 vs 89.821 | difference |
| 12:00:59 | Q4 | 49 | 49 | ret_to_close | -8.211 bp | [-18.211, +2.379] | -8.623 vs -0.412 | difference |
| 12:00:59 | Q4 | 48 | 48 | ret_next | +17.472 bp | [-8.777, +43.322] | 12.834 vs -4.638 | difference |
| 12:00:59 | Q4 | 49 | 49 | rng_next | -7.446 bp | [-19.371, +4.854] | 83.945 vs 91.391 | difference |
| 12:00:59 | Q5 | 49 | 49 | ret_to_close | +5.308 bp | [-5.542, +16.507] | 2.193 vs -3.116 | difference |
| 12:00:59 | Q5 | 49 | 49 | ret_next | -17.881 bp | [-39.062, +2.851] | -15.462 vs 2.419 | difference |
| 12:00:59 | Q5 | 49 | 49 | rng_next | -15.799 bp | [-26.511, -5.840] | 77.269 vs 93.068 | difference |
| 14:00:59 | Q1 | 50 | 50 | ret_to_close | -4.091 bp | [-14.097, +5.573] | -4.906 vs -0.815 | difference |
| 14:00:59 | Q1 | 50 | 50 | ret_next | +9.481 bp | [-23.488, +44.269] | 6.344 vs -3.138 | difference |
| 14:00:59 | Q1 | 50 | 50 | rng_next | +21.844 bp | [+2.489, +43.956] | 107.264 vs 85.419 | difference |
| 14:00:59 | Q2 | 49 | 49 | ret_to_close | +2.256 bp | [-7.879, +12.352] | 0.155 vs -2.101 | difference |
| 14:00:59 | Q2 | 49 | 49 | ret_next | +12.519 bp | [-14.852, +38.514] | 8.808 vs -3.711 | difference |
| 14:00:59 | Q2 | 49 | 49 | rng_next | -0.921 bp | [-12.666, +12.263] | 89.159 vs 90.081 | difference |
| 14:00:59 | Q3 | 49 | 49 | ret_to_close | -7.745 bp | [-15.245, -0.307] | -7.846 vs -0.101 | difference |
| 14:00:59 | Q3 | 48 | 48 | ret_next | -2.332 bp | [-32.473, +24.483] | -3.058 vs -0.726 | difference |
| 14:00:59 | Q3 | 48 | 48 | rng_next | +6.407 bp | [-8.477, +22.492] | 95.042 vs 88.635 | difference |
| 14:00:59 | Q4 | 48 | 48 | ret_to_close | +5.630 bp | [-1.496, +13.043] | 2.877 vs -2.753 | difference |
| 14:00:59 | Q4 | 47 | 47 | ret_next | -6.402 bp | [-30.937, +19.306] | -6.351 vs 0.051 | difference |
| 14:00:59 | Q4 | 48 | 48 | rng_next | -12.339 bp | [-24.401, -1.200] | 79.984 vs 92.323 | difference |
| 14:00:59 | Q5 | 49 | 49 | ret_to_close | +4.100 bp | [-3.663, +12.067] | 1.630 vs -2.470 | difference |
| 14:00:59 | Q5 | 49 | 49 | ret_next | -13.644 bp | [-36.717, +8.250] | -12.080 vs 1.565 | difference |
| 14:00:59 | Q5 | 49 | 49 | rng_next | -15.414 bp | [-26.551, -4.315] | 77.577 vs 92.991 | difference |
| 15:29:59 | Q1 | 49 | 49 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q1 | 48 | 48 | ret_next | +10.826 bp | [-23.273, +45.549] | 7.501 vs -3.325 | difference |
| 15:29:59 | Q1 | 48 | 48 | rng_next | +7.463 bp | [-9.418, +24.682] | 95.890 vs 88.428 | difference |
| 15:29:59 | Q2 | 49 | 49 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q2 | 49 | 49 | ret_next | -5.495 bp | [-36.754, +24.381] | -5.574 vs -0.079 | difference |
| 15:29:59 | Q2 | 49 | 49 | rng_next | +15.012 bp | [+0.640, +31.287] | 101.893 vs 86.881 | difference |
| 15:29:59 | Q3 | 49 | 49 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q3 | 49 | 49 | ret_next | +17.002 bp | [-8.179, +40.346] | 12.387 vs -4.615 | difference |
| 15:29:59 | Q3 | 49 | 49 | rng_next | -6.645 bp | [-19.977, +9.660] | 84.585 vs 91.230 | difference |
| 15:29:59 | Q4 | 49 | 49 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q4 | 49 | 49 | ret_next | -14.196 bp | [-38.044, +9.305] | -12.520 vs 1.676 | difference |
| 15:29:59 | Q4 | 49 | 49 | rng_next | -7.207 bp | [-19.803, +6.343] | 84.136 vs 91.343 | difference |
| 15:29:59 | Q5 | 49 | 49 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q5 | 48 | 48 | ret_next | -8.096 bp | [-33.766, +18.198] | -7.683 vs 0.412 | difference |
| 15:29:59 | Q5 | 49 | 49 | rng_next | -8.507 bp | [-20.401, +4.312] | 83.097 vs 91.604 | difference |

**Spearman ρ of dev against each outcome** (descriptive, no p-value)

| clock | outcome | n | ρ |
|---|---|---|---|
| 10:00:59 | ret_to_close | 245 | -0.0424 |
| 10:00:59 | ret_next | 243 | -0.0292 |
| 10:00:59 | rng_next | 244 | -0.0980 |
| 12:00:59 | ret_to_close | 245 | +0.0107 |
| 12:00:59 | ret_next | 243 | -0.0699 |
| 12:00:59 | rng_next | 244 | -0.1179 |
| 14:00:59 | ret_to_close | 245 | +0.0966 |
| 14:00:59 | ret_next | 243 | -0.1087 |
| 14:00:59 | rng_next | 244 | -0.1381 |
| 15:29:59 | ret_to_close | 245 | +nan |
| 15:29:59 | ret_next | 243 | -0.0988 |
| 15:29:59 | rng_next | 244 | -0.1001 |

### B · no-expiry   [exploratory]

| clock | quintile  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| 10:00:59 | Q1 | 45 | 45 | ret_to_close | -4.367 bp | [-24.342, +13.963] | -5.739 vs -1.372 | difference |
| 10:00:59 | Q1 | 45 | 45 | ret_next | +28.791 bp | [-1.940, +60.829] | 16.994 vs -11.797 | difference |
| 10:00:59 | Q1 | 45 | 45 | rng_next | +2.885 bp | [-13.107, +22.197] | 92.319 vs 89.434 | difference |
| 10:00:59 | Q2 | 44 | 44 | ret_to_close | +14.676 bp | [-2.023, +32.582] | 9.527 vs -5.149 | difference |
| 10:00:59 | Q2 | 44 | 44 | ret_next | -22.226 bp | [-53.530, +8.041] | -23.782 vs -1.556 | difference |
| 10:00:59 | Q2 | 44 | 44 | rng_next | +9.038 bp | [-7.552, +25.853] | 97.271 vs 88.232 | difference |
| 10:00:59 | Q3 | 45 | 45 | ret_to_close | -4.054 bp | [-20.593, +11.763] | -5.489 vs -1.435 | difference |
| 10:00:59 | Q3 | 45 | 45 | ret_next | -25.658 bp | [-57.059, +2.767] | -26.418 vs -0.760 | difference |
| 10:00:59 | Q3 | 45 | 45 | rng_next | +14.001 bp | [-2.851, +34.142] | 101.191 vs 87.190 | difference |
| 10:00:59 | Q4 | 44 | 44 | ret_to_close | +9.968 bp | [-7.314, +26.827] | 5.748 vs -4.220 | difference |
| 10:00:59 | Q4 | 43 | 43 | ret_next | +29.631 bp | [+4.246, +54.986] | 17.931 vs -11.700 | difference |
| 10:00:59 | Q4 | 44 | 44 | rng_next | -13.775 bp | [-26.839, -0.533] | 78.959 vs 92.734 | difference |
| 10:00:59 | Q5 | 45 | 45 | ret_to_close | -15.810 bp | [-31.173, -0.232] | -14.873 vs 0.937 | difference |
| 10:00:59 | Q5 | 45 | 45 | ret_next | -9.912 bp | [-33.454, +14.625] | -13.864 vs -3.952 | difference |
| 10:00:59 | Q5 | 45 | 45 | rng_next | -12.229 bp | [-22.744, -1.206] | 80.255 vs 92.483 | difference |
| 12:00:59 | Q1 | 45 | 45 | ret_to_close | +7.756 bp | [-9.079, +22.085] | 4.083 vs -3.673 | difference |
| 12:00:59 | Q1 | 45 | 45 | ret_next | +19.771 bp | [-16.500, +58.868] | 9.803 vs -9.968 | difference |
| 12:00:59 | Q1 | 45 | 45 | rng_next | +20.367 bp | [+0.048, +42.922] | 106.273 vs 85.906 | difference |
| 12:00:59 | Q2 | 44 | 44 | ret_to_close | -13.494 bp | [-26.373, -0.967] | -12.939 vs 0.554 | difference |
| 12:00:59 | Q2 | 44 | 44 | ret_next | -1.219 bp | [-30.632, +26.465] | -6.938 vs -5.719 | difference |
| 12:00:59 | Q2 | 44 | 44 | rng_next | +0.328 bp | [-13.334, +15.008] | 90.279 vs 89.951 | difference |
| 12:00:59 | Q3 | 45 | 45 | ret_to_close | +10.311 bp | [-5.204, +27.534] | 6.122 vs -4.189 | difference |
| 12:00:59 | Q3 | 45 | 45 | ret_next | -14.331 bp | [-45.351, +15.728] | -17.387 vs -3.056 | difference |
| 12:00:59 | Q3 | 45 | 45 | rng_next | +4.149 bp | [-11.824, +20.255] | 93.327 vs 89.179 | difference |
| 12:00:59 | Q4 | 44 | 44 | ret_to_close | -8.835 bp | [-19.552, +1.858] | -9.200 vs -0.365 | difference |
| 12:00:59 | Q4 | 43 | 43 | ret_next | +12.063 bp | [-11.669, +36.276] | 3.766 vs -8.297 | difference |
| 12:00:59 | Q4 | 44 | 44 | rng_next | -13.303 bp | [-26.651, -0.380] | 79.338 vs 92.640 | difference |
| 12:00:59 | Q5 | 45 | 45 | ret_to_close | +3.889 bp | [-7.862, +15.524] | 0.996 vs -2.893 | difference |
| 12:00:59 | Q5 | 45 | 45 | ret_next | -15.898 bp | [-39.499, +6.825] | -18.636 vs -2.738 | difference |
| 12:00:59 | Q5 | 45 | 45 | rng_next | -11.758 bp | [-22.860, -0.505] | 80.630 vs 92.388 | difference |
| 14:00:59 | Q1 | 45 | 45 | ret_to_close | -6.330 bp | [-16.851, +2.301] | -6.243 vs 0.087 | difference |
| 14:00:59 | Q1 | 45 | 45 | ret_next | +18.674 bp | [-17.907, +57.760] | 8.928 vs -9.746 | difference |
| 14:00:59 | Q1 | 45 | 45 | rng_next | +24.735 bp | [+4.614, +47.577] | 109.759 vs 85.024 | difference |
| 14:00:59 | Q2 | 45 | 45 | ret_to_close | +6.908 bp | [-3.931, +18.912] | 4.323 vs -2.584 | difference |
| 14:00:59 | Q2 | 45 | 45 | ret_next | +0.602 bp | [-26.740, +26.959] | -5.481 vs -6.083 | difference |
| 14:00:59 | Q2 | 45 | 45 | rng_next | -1.613 bp | [-14.911, +12.446] | 88.728 vs 90.341 | difference |
| 14:00:59 | Q3 | 44 | 44 | ret_to_close | -6.393 bp | [-13.523, +0.889] | -6.322 vs 0.071 | difference |
| 14:00:59 | Q3 | 44 | 44 | ret_next | -3.440 bp | [-32.925, +24.972] | -8.719 vs -5.279 | difference |
| 14:00:59 | Q3 | 44 | 44 | rng_next | +2.303 bp | [-12.959, +19.042] | 91.864 vs 89.561 | difference |
| 14:00:59 | Q4 | 44 | 44 | ret_to_close | +4.090 bp | [-3.543, +11.913] | 2.093 vs -1.998 | difference |
| 14:00:59 | Q4 | 43 | 43 | ret_next | -8.026 bp | [-35.055, +18.550] | -12.433 vs -4.406 | difference |
| 14:00:59 | Q4 | 44 | 44 | rng_next | -12.671 bp | [-25.987, -0.603] | 79.845 vs 92.516 | difference |
| 14:00:59 | Q5 | 45 | 45 | ret_to_close | +1.686 bp | [-6.101, +10.174] | 0.156 vs -1.531 | difference |
| 14:00:59 | Q5 | 45 | 45 | ret_next | -8.137 bp | [-31.627, +15.395] | -12.448 vs -4.311 | difference |
| 14:00:59 | Q5 | 45 | 45 | rng_next | -12.927 bp | [-24.673, -1.401] | 79.697 vs 92.624 | difference |
| 15:29:59 | Q1 | 45 | 45 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q1 | 45 | 45 | ret_next | +12.470 bp | [-22.897, +49.107] | 3.982 vs -8.489 | difference |
| 15:29:59 | Q1 | 45 | 45 | rng_next | +7.619 bp | [-9.210, +26.745] | 96.097 vs 88.478 | difference |
| 15:29:59 | Q2 | 44 | 44 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q2 | 44 | 44 | ret_next | -10.678 bp | [-43.701, +20.933] | -14.523 vs -3.844 | difference |
| 15:29:59 | Q2 | 44 | 44 | rng_next | +16.355 bp | [+1.040, +33.087] | 103.144 vs 86.789 | difference |
| 15:29:59 | Q3 | 45 | 45 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q3 | 45 | 45 | ret_next | +15.359 bp | [-10.277, +40.111] | 6.285 vs -9.074 | difference |
| 15:29:59 | Q3 | 45 | 45 | rng_next | -5.568 bp | [-19.950, +12.682] | 85.572 vs 91.139 | difference |
| 15:29:59 | Q4 | 44 | 44 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q4 | 44 | 44 | ret_next | -14.771 bp | [-42.969, +9.100] | -17.804 vs -3.033 | difference |
| 15:29:59 | Q4 | 44 | 44 | rng_next | -8.036 bp | [-22.122, +7.230] | 83.565 vs 91.601 | difference |
| 15:29:59 | Q5 | 45 | 45 | ret_to_close | +0.000 bp | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| 15:29:59 | Q5 | 44 | 44 | ret_next | -2.854 bp | [-28.568, +24.098] | -8.249 vs -5.395 | difference |
| 15:29:59 | Q5 | 45 | 45 | rng_next | -10.231 bp | [-22.797, +3.058] | 81.849 vs 92.080 | difference |

**Spearman ρ of dev against each outcome** (descriptive, no p-value)

| clock | outcome | n | ρ |
|---|---|---|---|
| 10:00:59 | ret_to_close | 223 | -0.0883 |
| 10:00:59 | ret_next | 222 | -0.0286 |
| 10:00:59 | rng_next | 223 | -0.0693 |
| 12:00:59 | ret_to_close | 223 | -0.0180 |
| 12:00:59 | ret_next | 222 | -0.0730 |
| 12:00:59 | rng_next | 223 | -0.1056 |
| 14:00:59 | ret_to_close | 223 | +0.0709 |
| 14:00:59 | ret_next | 222 | -0.1033 |
| 14:00:59 | rng_next | 223 | -0.1230 |
| 15:29:59 | ret_to_close | 223 | +nan |
| 15:29:59 | ret_next | 222 | -0.0791 |
| 15:29:59 | rng_next | 223 | -0.0980 |

## C — large moves on any day   [exploratory]

C1: the top decile of |close-to-close return| and, separately, of intraday range (both on P). C2: the top 5 % of |30-minute return|. Each set is set beside all other days or windows, which is the complement for every unsigned outcome here.


### C1 top decile |close-to-close return|   [exploratory]

Cut at the 90th percentile = 341.8000. Large n=25 days over 25 sessions; rest n=218.

**BEFORE — rank-biserial separation** (+1 large always above rest, 0 none)

| variable | n large | n rest | rank-biserial |
|---|---|---|---|
| dF_60 | 24 | 178 | +0.0557 |
| dF1_60 | 25 | 218 | +0.1593 |
| dF_prev | 25 | 216 | +0.2281 |
| dF1_prev | 25 | 218 | +0.2690 |
| basis_dev | 25 | 217 | -0.2136 |
| g_mean | 17 | 163 | +0.1649 |

*`g_mean` exists only for the 182 sessions M2 kept — see NOT_VERIFIED §5; its denominator is the `n` column above.*

**DURING — class composition**

| set | LB | SC | SB | LU | FLAT | MISSING |
|---|---|---|---|---|---|---|
| large | 5 | 6 | 13 | 1 | 0 | 0 |
| rest | 53 | 56 | 74 | 33 | 0 | 2 |

**AFTER — next-session outcome**

| set  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| large | 25 | 25 | retnext | +41.001 bp | [-17.545, +92.909] | 35.353 vs -5.648 | difference |
| large | 25 | 25 | contnext | +19.807 bp | [-34.211, +75.650] | 13.239 vs -6.568 | difference |
| large | 25 | 25 | rngnext | +44.692 bp | [+22.309, +68.499] | 130.003 vs 85.311 | difference |
| rest | 217 | 217 | retnext | -41.001 bp | [-91.896, +12.747] | -5.648 vs 35.353 | difference |
| rest | 217 | 217 | contnext | -19.807 bp | [-78.718, +34.990] | -6.568 vs 13.239 | difference |
| rest | 218 | 218 | rngnext | -44.692 bp | [-67.044, -19.983] | 85.311 vs 130.003 | difference |

### C1 top decile intraday range   [exploratory]

Cut at the 90th percentile = 148.3790. Large n=25 days over 25 sessions; rest n=219.

**BEFORE — rank-biserial separation** (+1 large always above rest, 0 none)

| variable | n large | n rest | rank-biserial |
|---|---|---|---|
| dF_60 | 25 | 177 | +0.0251 |
| dF1_60 | 25 | 218 | +0.0158 |
| dF_prev | 25 | 216 | +0.2404 |
| dF1_prev | 25 | 218 | -0.0378 |
| basis_dev | 25 | 217 | -0.3253 |
| g_mean | 18 | 162 | +0.0274 |

*`g_mean` exists only for the 182 sessions M2 kept — see NOT_VERIFIED §5; its denominator is the `n` column above.*

**DURING — class composition**

| set | LB | SC | SB | LU | FLAT | MISSING |
|---|---|---|---|---|---|---|
| large | 5 | 6 | 12 | 2 | 0 | 0 |
| rest | 53 | 56 | 75 | 32 | 0 | 3 |

**AFTER — next-session outcome**

| set  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| large | 25 | 25 | retnext | +39.176 bp | [-13.299, +89.072] | 33.717 vs -5.459 | difference |
| large | 25 | 25 | contnext | -6.051 bp | [-60.072, +46.423] | -9.948 vs -3.897 | difference |
| large | 25 | 25 | rngnext | +48.725 bp | [+27.152, +69.296] | 133.622 vs 84.896 | difference |
| rest | 217 | 217 | retnext | -39.176 bp | [-87.603, +13.063] | -5.459 vs 33.717 | difference |
| rest | 217 | 217 | contnext | +6.051 bp | [-47.569, +58.074] | -3.897 vs -9.948 | difference |
| rest | 218 | 218 | rngnext | -48.725 bp | [-69.162, -28.441] | 84.896 vs 133.622 | difference |

### C2 top 5 % of |30-minute return| · OI=F   [exploratory]

Cut at |dP| ≥ 84.41 index points. Large n=148 windows over 88 sessions; rest n=2806.

| set  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| large | 135 | 84 | cont30 | +1.345 bp | [-2.103, +4.847] | 1.589 vs 0.245 | difference |
| large | 128 | 81 | cont60 | -2.006 bp | [-8.585, +4.627] | -1.870 vs 0.137 | difference |
| large | 148 | 88 | contclose | -1.805 bp | [-12.373, +12.082] | -1.149 vs 0.656 | difference |
| large | 145 | 87 | contnext | -0.347 bp | [-16.276, +17.039] | 0.576 vs 0.923 | difference |
| large | 135 | 84 | hit30 | -0.018 rate | [-0.107, +0.065] | 0.474 vs 0.492 | difference |
| large | 128 | 81 | hit60 | -0.075 rate | [-0.168, +0.011] | 0.414 vs 0.489 | difference |
| large | 148 | 88 | hitclose | +0.009 rate | [-0.081, +0.096] | 0.527 vs 0.518 | difference |
| large | 145 | 87 | hitnext | -0.024 rate | [-0.105, +0.060] | 0.490 vs 0.514 | difference |
| rest | 2559 | 247 | cont30 | -1.345 bp | [-4.909, +2.203] | 0.245 vs 1.589 | difference |
| rest | 2320 | 246 | cont60 | +2.006 bp | [-4.130, +8.274] | 0.137 vs -1.870 | difference |
| rest | 2789 | 246 | contclose | +1.805 bp | [-11.115, +13.155] | 0.656 vs -1.149 | difference |
| rest | 2770 | 245 | contnext | +0.347 bp | [-17.026, +16.863] | 0.923 vs 0.576 | difference |
| rest | 2559 | 247 | hit30 | +0.018 rate | [-0.069, +0.108] | 0.492 vs 0.474 | difference |
| rest | 2320 | 246 | hit60 | +0.075 rate | [-0.011, +0.165] | 0.489 vs 0.414 | difference |
| rest | 2789 | 246 | hitclose | -0.009 rate | [-0.100, +0.080] | 0.518 vs 0.527 | difference |
| rest | 2770 | 245 | hitnext | +0.024 rate | [-0.057, +0.110] | 0.514 vs 0.490 | difference |

### C3 large windows by class · OI=F   [exploratory]

Contrasts hold the price sign fixed: LB vs SC, SB vs LU.

| contrast  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB vs SC | 48 | 41 | cont30 | +6.645 bp | [-5.339, +17.749] | 2.018 vs -4.627 | difference |
| LB vs SC | 46 | 40 | cont60 | -1.997 bp | [-20.978, +18.135] | -6.848 vs -4.851 | difference |
| LB vs SC | 51 | 42 | contclose | -16.913 bp | [-42.098, +8.942] | -5.377 vs 11.536 | difference |
| LB vs SC | 49 | 41 | contnext | -31.167 bp | [-83.913, +18.041] | 13.166 vs 44.333 | difference |
| LB vs SC | 48 | 41 | hit30 | +0.070 rate | [-0.200, +0.300] | 0.479 vs 0.409 | difference |
| LB vs SC | 46 | 40 | hit60 | -0.051 rate | [-0.353, +0.241] | 0.370 vs 0.421 | difference |
| LB vs SC | 51 | 42 | hitclose | -0.196 rate | [-0.422, +0.029] | 0.471 vs 0.667 | difference |
| LB vs SC | 49 | 41 | hitnext | -0.135 rate | [-0.380, +0.106] | 0.490 vs 0.625 | difference |
| SB vs LU | 46 | 36 | cont30 | +7.051 bp | [-10.967, +28.743] | 4.692 vs -2.359 | difference |
| SB vs LU | 45 | 35 | cont60 | -9.184 bp | [-39.230, +25.373] | 0.815 vs 9.999 | difference |
| SB vs LU | 52 | 41 | contclose | +22.793 bp | [-20.233, +74.326] | -1.078 vs -23.872 | difference |
| SB vs LU | 51 | 40 | contnext | +49.941 bp | [-41.035, +162.759] | -21.424 vs -71.365 | difference |
| SB vs LU | 46 | 36 | hit30 | +0.122 rate | [-0.267, +0.519] | 0.522 vs 0.400 | difference |
| SB vs LU | 45 | 35 | hit60 | -0.033 rate | [-0.403, +0.386] | 0.467 vs 0.500 | difference |
| SB vs LU | 52 | 41 | hitclose | +0.194 rate | [-0.147, +0.542] | 0.558 vs 0.364 | difference |
| SB vs LU | 51 | 40 | hitnext | +0.068 rate | [-0.303, +0.373] | 0.431 vs 0.364 | difference |

### C2 top 5 % of |30-minute return| · OI=F1   [exploratory]

Cut at |dP| ≥ 84.41 index points. Large n=148 windows over 88 sessions; rest n=2806.

| set  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| large | 135 | 84 | cont30 | +1.345 bp | [-2.103, +4.847] | 1.589 vs 0.245 | difference |
| large | 128 | 81 | cont60 | -2.006 bp | [-8.585, +4.627] | -1.870 vs 0.137 | difference |
| large | 148 | 88 | contclose | -1.805 bp | [-12.373, +12.082] | -1.149 vs 0.656 | difference |
| large | 145 | 87 | contnext | -0.347 bp | [-16.276, +17.039] | 0.576 vs 0.923 | difference |
| large | 135 | 84 | hit30 | -0.018 rate | [-0.107, +0.065] | 0.474 vs 0.492 | difference |
| large | 128 | 81 | hit60 | -0.075 rate | [-0.168, +0.011] | 0.414 vs 0.489 | difference |
| large | 148 | 88 | hitclose | +0.009 rate | [-0.081, +0.096] | 0.527 vs 0.518 | difference |
| large | 145 | 87 | hitnext | -0.024 rate | [-0.105, +0.060] | 0.490 vs 0.514 | difference |
| rest | 2559 | 247 | cont30 | -1.345 bp | [-4.909, +2.203] | 0.245 vs 1.589 | difference |
| rest | 2320 | 246 | cont60 | +2.006 bp | [-4.130, +8.274] | 0.137 vs -1.870 | difference |
| rest | 2789 | 246 | contclose | +1.805 bp | [-11.115, +13.155] | 0.656 vs -1.149 | difference |
| rest | 2770 | 245 | contnext | +0.347 bp | [-17.026, +16.863] | 0.923 vs 0.576 | difference |
| rest | 2559 | 247 | hit30 | +0.018 rate | [-0.069, +0.108] | 0.492 vs 0.474 | difference |
| rest | 2320 | 246 | hit60 | +0.075 rate | [-0.011, +0.165] | 0.489 vs 0.414 | difference |
| rest | 2789 | 246 | hitclose | -0.009 rate | [-0.100, +0.080] | 0.518 vs 0.527 | difference |
| rest | 2770 | 245 | hitnext | +0.024 rate | [-0.057, +0.110] | 0.514 vs 0.490 | difference |

### C3 large windows by class · OI=F1   [exploratory]

Contrasts hold the price sign fixed: LB vs SC, SB vs LU.

| contrast  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|------|---|---|---|---|---|---|
| LB vs SC | 37 | 32 | cont30 | +11.618 bp | [+1.566, +21.218] | 5.580 vs -6.038 | difference |
| LB vs SC | 35 | 31 | cont60 | +5.290 bp | [-10.977, +22.034] | -4.252 vs -9.542 | difference |
| LB vs SC | 40 | 34 | contclose | -9.845 bp | [-31.193, +13.218] | -5.275 vs 4.570 | difference |
| LB vs SC | 39 | 33 | contnext | -87.078 bp | [-136.710, -38.766] | -17.224 vs 69.854 | difference |
| LB vs SC | 37 | 32 | hit30 | +0.179 rate | [-0.063, +0.406] | 0.541 vs 0.361 | difference |
| LB vs SC | 35 | 31 | hit60 | -0.004 rate | [-0.244, +0.239] | 0.371 vs 0.375 | difference |
| LB vs SC | 40 | 34 | hitclose | -0.115 rate | [-0.325, +0.095] | 0.475 vs 0.590 | difference |
| LB vs SC | 39 | 33 | hitnext | -0.274 rate | [-0.498, -0.048] | 0.410 vs 0.684 | difference |
| SB vs LU | 44 | 33 | cont30 | +6.926 bp | [-5.661, +20.442] | 5.648 vs -1.279 | difference |
| SB vs LU | 43 | 32 | cont60 | -1.617 bp | [-20.869, +19.073] | 3.045 vs 4.662 | difference |
| SB vs LU | 49 | 37 | contclose | +28.499 bp | [-8.291, +61.310] | 6.272 vs -22.227 | difference |
| SB vs LU | 49 | 37 | contnext | +67.994 bp | [-0.633, +145.680] | -8.930 vs -76.925 | difference |
| SB vs LU | 44 | 33 | hit30 | +0.078 rate | [-0.214, +0.381] | 0.523 vs 0.444 | difference |
| SB vs LU | 43 | 32 | hit60 | +0.021 rate | [-0.259, +0.302] | 0.465 vs 0.444 | difference |
| SB vs LU | 49 | 37 | hitclose | +0.242 rate | [-0.037, +0.494] | 0.592 vs 0.350 | difference |
| SB vs LU | 49 | 37 | hitnext | +0.154 rate | [-0.126, +0.406] | 0.469 vs 0.316 | difference |

## D — walls from the chain, read with futures OI   [exploratory]

Walls are fixed from the **prior** session's close, front expiry: the call wall is the strike with the largest CE OI at or above the prior spot close, the put wall the largest PE OI at or below. An approach is the first minute S comes within the band of a wall **from the inside**. BREAK if S at 15:29:59 is beyond the wall by ≥ 0.10 %, else HOLD.

Break rate and maximum excursion are unsigned, so each conditioned row is a **difference against the complementary condition** (F rising minus F falling; a tercile minus the other two). The unconditional `all` row has no complement and is printed as a level only.

**2025-10-21 is excluded from walls** (its tag-B bar is 14:45:59, not the close), removing the walls for **2025-10-23**. Walls are built for **245** sessions, not 246.

**Edge sessions are flagged**: on 11 sessions the call wall is the highest strike the vendor lists and on 13 the put wall is the lowest. Every table is given with and without them.

> **D2 (OI at the wall strike) was not computed in this run; Study D is D1 only.** D2 requires the change in OI at the wall strike itself over the 30 minutes before the approach, which needs a per-approach-session read of `hist_option_bars_1m`. No such extraction was made, and the chain data this run holds (`session_chain.csv` tag B) carries per-strike OI only at each session's CLOSE — one bar per session — so it cannot supply an intraday 30-minute change. The conditioning below is on **futures** OI alone. There is no 2x2 of option-strike OI against futures OI anywhere in this document.


### D band = 0.10 %   [exploratory]

**Sessions producing NO approach, by wall distance**

| side | wall distance | no approach | sessions in bucket | share |
|---|---|---|---|---|
| call | <=2% | 85 | 109 | 78.0% |
| call | 2-4% | 59 | 59 | 100.0% |
| call | >4% | 77 | 77 | 100.0% |
| put | <=2% | 81 | 125 | 64.8% |
| put | 2-4% | 61 | 62 | 98.4% |
| put | >4% | 58 | 58 | 100.0% |

**Break rate and excursion · with edge · all**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 24 | 24 | break_rate | +0.417 rate | — | — | level, not an effect |
| call | all | 24 | 24 | max_excursion_pct | +0.238 % | — | — | level, not an effect |
| call | F rising | 5 | 5 | break_rate | +0.200 rate | [-0.400, +0.800] | 0.400 vs 0.200 | difference |
| call | F rising | 5 | 5 | max_excursion_pct | +0.137 % | [-0.078, +0.339] | 0.200 vs 0.063 | difference |
| call | F falling | 5 | 5 | break_rate | -0.200 rate | [-0.800, +0.400] | 0.200 vs 0.400 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.137 % | [-0.338, +0.077] | 0.063 vs 0.200 | difference |
| call | F T1 | 4 | 4 | break_rate | -0.083 rate | [-0.600, +0.583] | 0.250 vs 0.333 | difference |
| call | F T1 | 4 | 4 | max_excursion_pct | -0.106 % | [-0.300, +0.137] | 0.068 vs 0.174 | difference |
| call | F T2 | 3 | 3 | break_rate | +0.048 rate | [-0.556, +0.778] | 0.333 vs 0.286 | difference |
| call | F T2 | 3 | 3 | max_excursion_pct | +0.024 % | [-0.190, +0.279] | 0.148 vs 0.124 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.048 rate | [-0.571, +0.778] | 0.333 vs 0.286 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.097 % | [-0.117, +0.341] | 0.199 vs 0.102 | difference |
| call | F1 rising | 6 | 6 | break_rate | +0.000 rate | [-0.571, +0.514] | 0.333 vs 0.333 | difference |
| call | F1 rising | 6 | 6 | max_excursion_pct | +0.046 % | [-0.143, +0.238] | 0.157 vs 0.111 | difference |
| call | F1 falling | 6 | 6 | break_rate | +0.000 rate | [-0.571, +0.556] | 0.333 vs 0.333 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.046 % | [-0.243, +0.139] | 0.111 vs 0.157 | difference |
| call | F1 T1 | 4 | 4 | break_rate | +0.250 rate | [-0.375, +0.881] | 0.500 vs 0.250 | difference |
| call | F1 T1 | 4 | 4 | max_excursion_pct | +0.020 % | [-0.191, +0.229] | 0.147 vs 0.127 | difference |
| call | F1 T2 | 4 | 4 | break_rate | -0.500 rate | [-0.857, -0.143] | 0.000 vs 0.500 | difference |
| call | F1 T2 | 4 | 4 | max_excursion_pct | -0.157 % | [-0.300, -0.023] | 0.029 vs 0.186 | difference |
| call | F1 T3 | 4 | 4 | break_rate | +0.250 rate | [-0.375, +0.857] | 0.500 vs 0.250 | difference |
| call | F1 T3 | 4 | 4 | max_excursion_pct | +0.137 % | [-0.074, +0.337] | 0.225 vs 0.088 | difference |
| put | all | 45 | 45 | break_rate | +0.467 rate | — | — | level, not an effect |
| put | all | 45 | 45 | max_excursion_pct | +0.287 % | — | — | level, not an effect |
| put | F rising | 15 | 15 | break_rate | +0.283 rate | [-0.354, +0.733] | 0.533 vs 0.250 | difference |
| put | F rising | 15 | 15 | max_excursion_pct | +0.083 % | [-0.283, +0.322] | 0.304 vs 0.220 | difference |
| put | F falling | 4 | 4 | break_rate | -0.283 rate | [-0.714, +0.383] | 0.250 vs 0.533 | difference |
| put | F falling | 4 | 4 | max_excursion_pct | -0.083 % | [-0.316, +0.313] | 0.220 vs 0.304 | difference |
| put | F T1 | 7 | 7 | break_rate | -0.298 rate | [-0.693, +0.156] | 0.286 vs 0.583 | difference |
| put | F T1 | 7 | 7 | max_excursion_pct | -0.144 % | [-0.351, +0.091] | 0.195 vs 0.339 | difference |
| put | F T2 | 6 | 6 | break_rate | +0.282 rate | [-0.235, +0.734] | 0.667 vs 0.385 | difference |
| put | F T2 | 6 | 6 | max_excursion_pct | +0.016 % | [-0.239, +0.276] | 0.297 vs 0.281 | difference |
| put | F T3 | 6 | 6 | break_rate | +0.038 rate | [-0.500, +0.550] | 0.500 vs 0.462 | difference |
| put | F T3 | 6 | 6 | max_excursion_pct | +0.140 % | [-0.044, +0.334] | 0.382 vs 0.242 | difference |
| put | F1 rising | 16 | 16 | break_rate | +0.277 rate | [-0.197, +0.675] | 0.562 vs 0.286 | difference |
| put | F1 rising | 16 | 16 | max_excursion_pct | -0.021 % | [-0.231, +0.162] | 0.247 vs 0.269 | difference |
| put | F1 falling | 7 | 7 | break_rate | -0.277 rate | [-0.667, +0.167] | 0.286 vs 0.562 | difference |
| put | F1 falling | 7 | 7 | max_excursion_pct | +0.021 % | [-0.177, +0.228] | 0.269 vs 0.247 | difference |
| put | F1 T1 | 8 | 8 | break_rate | -0.350 rate | [-0.716, +0.048] | 0.250 vs 0.600 | difference |
| put | F1 T1 | 8 | 8 | max_excursion_pct | -0.013 % | [-0.195, +0.186] | 0.245 vs 0.258 | difference |
| put | F1 T2 | 7 | 7 | break_rate | -0.071 rate | [-0.539, +0.382] | 0.429 vs 0.500 | difference |
| put | F1 T2 | 7 | 7 | max_excursion_pct | -0.144 % | [-0.361, +0.081] | 0.154 vs 0.297 | difference |
| put | F1 T3 | 8 | 8 | break_rate | +0.417 rate | [-0.008, +0.786] | 0.750 vs 0.333 | difference |
| put | F1 T3 | 8 | 8 | max_excursion_pct | +0.147 % | [-0.052, +0.334] | 0.350 vs 0.203 | difference |

**Break rate and excursion · with edge · no-expiry**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 21 | 21 | break_rate | +0.381 rate | — | — | level, not an effect |
| call | all | 21 | 21 | max_excursion_pct | +0.198 % | — | — | level, not an effect |
| call | F rising | 5 | 5 | break_rate | +0.200 rate | [-0.400, +0.800] | 0.400 vs 0.200 | difference |
| call | F rising | 5 | 5 | max_excursion_pct | +0.137 % | [-0.078, +0.339] | 0.200 vs 0.063 | difference |
| call | F falling | 5 | 5 | break_rate | -0.200 rate | [-0.800, +0.400] | 0.200 vs 0.400 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.137 % | [-0.338, +0.077] | 0.063 vs 0.200 | difference |
| call | F T1 | 4 | 4 | break_rate | -0.083 rate | [-0.600, +0.583] | 0.250 vs 0.333 | difference |
| call | F T1 | 4 | 4 | max_excursion_pct | -0.106 % | [-0.300, +0.137] | 0.068 vs 0.174 | difference |
| call | F T2 | 3 | 3 | break_rate | +0.048 rate | [-0.556, +0.778] | 0.333 vs 0.286 | difference |
| call | F T2 | 3 | 3 | max_excursion_pct | +0.024 % | [-0.190, +0.279] | 0.148 vs 0.124 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.048 rate | [-0.571, +0.778] | 0.333 vs 0.286 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.097 % | [-0.117, +0.341] | 0.199 vs 0.102 | difference |
| call | F1 rising | 5 | 5 | break_rate | +0.067 rate | [-0.556, +0.633] | 0.400 vs 0.333 | difference |
| call | F1 rising | 5 | 5 | max_excursion_pct | +0.074 % | [-0.130, +0.286] | 0.185 vs 0.111 | difference |
| call | F1 falling | 6 | 6 | break_rate | -0.067 rate | [-0.667, +0.542] | 0.333 vs 0.400 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.074 % | [-0.289, +0.123] | 0.111 vs 0.185 | difference |
| call | F1 T1 | 4 | 4 | break_rate | +0.214 rate | [-0.429, +0.812] | 0.500 vs 0.286 | difference |
| call | F1 T1 | 4 | 4 | max_excursion_pct | +0.004 % | [-0.212, +0.208] | 0.147 vs 0.143 | difference |
| call | F1 T2 | 3 | 3 | break_rate | -0.500 rate | [-0.857, -0.143] | 0.000 vs 0.500 | difference |
| call | F1 T2 | 3 | 3 | max_excursion_pct | -0.153 % | [-0.302, +0.000] | 0.033 vs 0.186 | difference |
| call | F1 T3 | 4 | 4 | break_rate | +0.214 rate | [-0.444, +0.857] | 0.500 vs 0.286 | difference |
| call | F1 T3 | 4 | 4 | max_excursion_pct | +0.127 % | [-0.092, +0.343] | 0.225 vs 0.098 | difference |
| put | all | 39 | 39 | break_rate | +0.487 rate | — | — | level, not an effect |
| put | all | 39 | 39 | max_excursion_pct | +0.284 % | — | — | level, not an effect |
| put | F rising | 12 | 12 | break_rate | +0.333 rate | [-0.346, +0.786] | 0.583 vs 0.250 | difference |
| put | F rising | 12 | 12 | max_excursion_pct | +0.064 % | [-0.337, +0.314] | 0.284 vs 0.220 | difference |
| put | F falling | 4 | 4 | break_rate | -0.333 rate | [-0.769, +0.333] | 0.250 vs 0.583 | difference |
| put | F falling | 4 | 4 | max_excursion_pct | -0.064 % | [-0.324, +0.347] | 0.220 vs 0.284 | difference |
| put | F T1 | 6 | 6 | break_rate | -0.533 rate | [-0.900, -0.067] | 0.167 vs 0.700 | difference |
| put | F T1 | 6 | 6 | max_excursion_pct | -0.189 % | [-0.404, +0.083] | 0.150 vs 0.339 | difference |
| put | F T2 | 5 | 5 | break_rate | +0.436 rate | [-0.083, +0.833] | 0.800 vs 0.364 | difference |
| put | F T2 | 5 | 5 | max_excursion_pct | +0.210 % | [-0.066, +0.435] | 0.412 vs 0.203 | difference |
| put | F T3 | 5 | 5 | break_rate | +0.145 rate | [-0.446, +0.710] | 0.600 vs 0.455 | difference |
| put | F T3 | 5 | 5 | max_excursion_pct | -0.004 % | [-0.250, +0.228] | 0.266 vs 0.270 | difference |
| put | F1 rising | 14 | 14 | break_rate | +0.238 rate | [-0.255, +0.687] | 0.571 vs 0.333 | difference |
| put | F1 rising | 14 | 14 | max_excursion_pct | -0.034 % | [-0.280, +0.179] | 0.224 vs 0.258 | difference |
| put | F1 falling | 6 | 6 | break_rate | -0.238 rate | [-0.691, +0.250] | 0.333 vs 0.571 | difference |
| put | F1 falling | 6 | 6 | max_excursion_pct | +0.034 % | [-0.185, +0.285] | 0.258 vs 0.224 | difference |
| put | F1 T1 | 7 | 7 | break_rate | -0.330 rate | [-0.750, +0.133] | 0.286 vs 0.615 | difference |
| put | F1 T1 | 7 | 7 | max_excursion_pct | -0.002 % | [-0.213, +0.224] | 0.233 vs 0.235 | difference |
| put | F1 T2 | 6 | 6 | break_rate | -0.238 rate | [-0.691, +0.267] | 0.333 vs 0.571 | difference |
| put | F1 T2 | 6 | 6 | max_excursion_pct | -0.125 % | [-0.374, +0.148] | 0.147 vs 0.272 | difference |
| put | F1 T3 | 7 | 7 | break_rate | +0.549 rate | [+0.110, +0.900] | 0.857 vs 0.308 | difference |
| put | F1 T3 | 7 | 7 | max_excursion_pct | +0.117 % | [-0.114, +0.327] | 0.311 vs 0.193 | difference |

**Break rate and excursion · without edge · all**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 24 | 24 | break_rate | +0.417 rate | — | — | level, not an effect |
| call | all | 24 | 24 | max_excursion_pct | +0.238 % | — | — | level, not an effect |
| call | F rising | 5 | 5 | break_rate | +0.200 rate | [-0.400, +0.800] | 0.400 vs 0.200 | difference |
| call | F rising | 5 | 5 | max_excursion_pct | +0.137 % | [-0.078, +0.339] | 0.200 vs 0.063 | difference |
| call | F falling | 5 | 5 | break_rate | -0.200 rate | [-0.800, +0.400] | 0.200 vs 0.400 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.137 % | [-0.338, +0.077] | 0.063 vs 0.200 | difference |
| call | F T1 | 4 | 4 | break_rate | -0.083 rate | [-0.600, +0.583] | 0.250 vs 0.333 | difference |
| call | F T1 | 4 | 4 | max_excursion_pct | -0.106 % | [-0.300, +0.137] | 0.068 vs 0.174 | difference |
| call | F T2 | 3 | 3 | break_rate | +0.048 rate | [-0.556, +0.778] | 0.333 vs 0.286 | difference |
| call | F T2 | 3 | 3 | max_excursion_pct | +0.024 % | [-0.190, +0.279] | 0.148 vs 0.124 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.048 rate | [-0.571, +0.778] | 0.333 vs 0.286 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.097 % | [-0.117, +0.341] | 0.199 vs 0.102 | difference |
| call | F1 rising | 6 | 6 | break_rate | +0.000 rate | [-0.571, +0.514] | 0.333 vs 0.333 | difference |
| call | F1 rising | 6 | 6 | max_excursion_pct | +0.046 % | [-0.143, +0.238] | 0.157 vs 0.111 | difference |
| call | F1 falling | 6 | 6 | break_rate | +0.000 rate | [-0.571, +0.556] | 0.333 vs 0.333 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.046 % | [-0.243, +0.139] | 0.111 vs 0.157 | difference |
| call | F1 T1 | 4 | 4 | break_rate | +0.250 rate | [-0.375, +0.881] | 0.500 vs 0.250 | difference |
| call | F1 T1 | 4 | 4 | max_excursion_pct | +0.020 % | [-0.191, +0.229] | 0.147 vs 0.127 | difference |
| call | F1 T2 | 4 | 4 | break_rate | -0.500 rate | [-0.857, -0.143] | 0.000 vs 0.500 | difference |
| call | F1 T2 | 4 | 4 | max_excursion_pct | -0.157 % | [-0.300, -0.023] | 0.029 vs 0.186 | difference |
| call | F1 T3 | 4 | 4 | break_rate | +0.250 rate | [-0.375, +0.857] | 0.500 vs 0.250 | difference |
| call | F1 T3 | 4 | 4 | max_excursion_pct | +0.137 % | [-0.074, +0.337] | 0.225 vs 0.088 | difference |
| put | all | 45 | 45 | break_rate | +0.467 rate | — | — | level, not an effect |
| put | all | 45 | 45 | max_excursion_pct | +0.287 % | — | — | level, not an effect |
| put | F rising | 15 | 15 | break_rate | +0.283 rate | [-0.354, +0.733] | 0.533 vs 0.250 | difference |
| put | F rising | 15 | 15 | max_excursion_pct | +0.083 % | [-0.283, +0.322] | 0.304 vs 0.220 | difference |
| put | F falling | 4 | 4 | break_rate | -0.283 rate | [-0.714, +0.383] | 0.250 vs 0.533 | difference |
| put | F falling | 4 | 4 | max_excursion_pct | -0.083 % | [-0.316, +0.313] | 0.220 vs 0.304 | difference |
| put | F T1 | 7 | 7 | break_rate | -0.298 rate | [-0.693, +0.156] | 0.286 vs 0.583 | difference |
| put | F T1 | 7 | 7 | max_excursion_pct | -0.144 % | [-0.351, +0.091] | 0.195 vs 0.339 | difference |
| put | F T2 | 6 | 6 | break_rate | +0.282 rate | [-0.235, +0.734] | 0.667 vs 0.385 | difference |
| put | F T2 | 6 | 6 | max_excursion_pct | +0.016 % | [-0.239, +0.276] | 0.297 vs 0.281 | difference |
| put | F T3 | 6 | 6 | break_rate | +0.038 rate | [-0.500, +0.550] | 0.500 vs 0.462 | difference |
| put | F T3 | 6 | 6 | max_excursion_pct | +0.140 % | [-0.044, +0.334] | 0.382 vs 0.242 | difference |
| put | F1 rising | 16 | 16 | break_rate | +0.277 rate | [-0.197, +0.675] | 0.562 vs 0.286 | difference |
| put | F1 rising | 16 | 16 | max_excursion_pct | -0.021 % | [-0.231, +0.162] | 0.247 vs 0.269 | difference |
| put | F1 falling | 7 | 7 | break_rate | -0.277 rate | [-0.667, +0.167] | 0.286 vs 0.562 | difference |
| put | F1 falling | 7 | 7 | max_excursion_pct | +0.021 % | [-0.177, +0.228] | 0.269 vs 0.247 | difference |
| put | F1 T1 | 8 | 8 | break_rate | -0.350 rate | [-0.716, +0.048] | 0.250 vs 0.600 | difference |
| put | F1 T1 | 8 | 8 | max_excursion_pct | -0.013 % | [-0.195, +0.186] | 0.245 vs 0.258 | difference |
| put | F1 T2 | 7 | 7 | break_rate | -0.071 rate | [-0.539, +0.382] | 0.429 vs 0.500 | difference |
| put | F1 T2 | 7 | 7 | max_excursion_pct | -0.144 % | [-0.361, +0.081] | 0.154 vs 0.297 | difference |
| put | F1 T3 | 8 | 8 | break_rate | +0.417 rate | [-0.008, +0.786] | 0.750 vs 0.333 | difference |
| put | F1 T3 | 8 | 8 | max_excursion_pct | +0.147 % | [-0.052, +0.334] | 0.350 vs 0.203 | difference |

**Break rate and excursion · without edge · no-expiry**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 21 | 21 | break_rate | +0.381 rate | — | — | level, not an effect |
| call | all | 21 | 21 | max_excursion_pct | +0.198 % | — | — | level, not an effect |
| call | F rising | 5 | 5 | break_rate | +0.200 rate | [-0.400, +0.800] | 0.400 vs 0.200 | difference |
| call | F rising | 5 | 5 | max_excursion_pct | +0.137 % | [-0.078, +0.339] | 0.200 vs 0.063 | difference |
| call | F falling | 5 | 5 | break_rate | -0.200 rate | [-0.800, +0.400] | 0.200 vs 0.400 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.137 % | [-0.338, +0.077] | 0.063 vs 0.200 | difference |
| call | F T1 | 4 | 4 | break_rate | -0.083 rate | [-0.600, +0.583] | 0.250 vs 0.333 | difference |
| call | F T1 | 4 | 4 | max_excursion_pct | -0.106 % | [-0.300, +0.137] | 0.068 vs 0.174 | difference |
| call | F T2 | 3 | 3 | break_rate | +0.048 rate | [-0.556, +0.778] | 0.333 vs 0.286 | difference |
| call | F T2 | 3 | 3 | max_excursion_pct | +0.024 % | [-0.190, +0.279] | 0.148 vs 0.124 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.048 rate | [-0.571, +0.778] | 0.333 vs 0.286 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.097 % | [-0.117, +0.341] | 0.199 vs 0.102 | difference |
| call | F1 rising | 5 | 5 | break_rate | +0.067 rate | [-0.556, +0.633] | 0.400 vs 0.333 | difference |
| call | F1 rising | 5 | 5 | max_excursion_pct | +0.074 % | [-0.130, +0.286] | 0.185 vs 0.111 | difference |
| call | F1 falling | 6 | 6 | break_rate | -0.067 rate | [-0.667, +0.542] | 0.333 vs 0.400 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.074 % | [-0.289, +0.123] | 0.111 vs 0.185 | difference |
| call | F1 T1 | 4 | 4 | break_rate | +0.214 rate | [-0.429, +0.812] | 0.500 vs 0.286 | difference |
| call | F1 T1 | 4 | 4 | max_excursion_pct | +0.004 % | [-0.212, +0.208] | 0.147 vs 0.143 | difference |
| call | F1 T2 | 3 | 3 | break_rate | -0.500 rate | [-0.857, -0.143] | 0.000 vs 0.500 | difference |
| call | F1 T2 | 3 | 3 | max_excursion_pct | -0.153 % | [-0.302, +0.000] | 0.033 vs 0.186 | difference |
| call | F1 T3 | 4 | 4 | break_rate | +0.214 rate | [-0.444, +0.857] | 0.500 vs 0.286 | difference |
| call | F1 T3 | 4 | 4 | max_excursion_pct | +0.127 % | [-0.092, +0.343] | 0.225 vs 0.098 | difference |
| put | all | 39 | 39 | break_rate | +0.487 rate | — | — | level, not an effect |
| put | all | 39 | 39 | max_excursion_pct | +0.284 % | — | — | level, not an effect |
| put | F rising | 12 | 12 | break_rate | +0.333 rate | [-0.346, +0.786] | 0.583 vs 0.250 | difference |
| put | F rising | 12 | 12 | max_excursion_pct | +0.064 % | [-0.337, +0.314] | 0.284 vs 0.220 | difference |
| put | F falling | 4 | 4 | break_rate | -0.333 rate | [-0.769, +0.333] | 0.250 vs 0.583 | difference |
| put | F falling | 4 | 4 | max_excursion_pct | -0.064 % | [-0.324, +0.347] | 0.220 vs 0.284 | difference |
| put | F T1 | 6 | 6 | break_rate | -0.533 rate | [-0.900, -0.067] | 0.167 vs 0.700 | difference |
| put | F T1 | 6 | 6 | max_excursion_pct | -0.189 % | [-0.404, +0.083] | 0.150 vs 0.339 | difference |
| put | F T2 | 5 | 5 | break_rate | +0.436 rate | [-0.083, +0.833] | 0.800 vs 0.364 | difference |
| put | F T2 | 5 | 5 | max_excursion_pct | +0.210 % | [-0.066, +0.435] | 0.412 vs 0.203 | difference |
| put | F T3 | 5 | 5 | break_rate | +0.145 rate | [-0.446, +0.710] | 0.600 vs 0.455 | difference |
| put | F T3 | 5 | 5 | max_excursion_pct | -0.004 % | [-0.250, +0.228] | 0.266 vs 0.270 | difference |
| put | F1 rising | 14 | 14 | break_rate | +0.238 rate | [-0.255, +0.687] | 0.571 vs 0.333 | difference |
| put | F1 rising | 14 | 14 | max_excursion_pct | -0.034 % | [-0.280, +0.179] | 0.224 vs 0.258 | difference |
| put | F1 falling | 6 | 6 | break_rate | -0.238 rate | [-0.691, +0.250] | 0.333 vs 0.571 | difference |
| put | F1 falling | 6 | 6 | max_excursion_pct | +0.034 % | [-0.185, +0.285] | 0.258 vs 0.224 | difference |
| put | F1 T1 | 7 | 7 | break_rate | -0.330 rate | [-0.750, +0.133] | 0.286 vs 0.615 | difference |
| put | F1 T1 | 7 | 7 | max_excursion_pct | -0.002 % | [-0.213, +0.224] | 0.233 vs 0.235 | difference |
| put | F1 T2 | 6 | 6 | break_rate | -0.238 rate | [-0.691, +0.267] | 0.333 vs 0.571 | difference |
| put | F1 T2 | 6 | 6 | max_excursion_pct | -0.125 % | [-0.374, +0.148] | 0.147 vs 0.272 | difference |
| put | F1 T3 | 7 | 7 | break_rate | +0.549 rate | [+0.110, +0.900] | 0.857 vs 0.308 | difference |
| put | F1 T3 | 7 | 7 | max_excursion_pct | +0.117 % | [-0.114, +0.327] | 0.311 vs 0.193 | difference |

### D band = 0.15 %   [exploratory]

**Sessions producing NO approach, by wall distance**

| side | wall distance | no approach | sessions in bucket | share |
|---|---|---|---|---|
| call | <=2% | 82 | 109 | 75.2% |
| call | 2-4% | 59 | 59 | 100.0% |
| call | >4% | 77 | 77 | 100.0% |
| put | <=2% | 74 | 125 | 59.2% |
| put | 2-4% | 61 | 62 | 98.4% |
| put | >4% | 58 | 58 | 100.0% |

**Break rate and excursion · with edge · all**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 27 | 27 | break_rate | +0.370 rate | — | — | level, not an effect |
| call | all | 27 | 27 | max_excursion_pct | +0.198 % | — | — | level, not an effect |
| call | F rising | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F rising | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F falling | 5 | 5 | break_rate | -0.133 rate | [-0.857, +0.500] | 0.200 vs 0.333 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.112 % | [-0.440, +0.141] | 0.020 vs 0.133 | difference |
| call | F T1 | 3 | 3 | break_rate | -0.400 rate | [-1.000, +0.000] | 0.000 vs 0.400 | difference |
| call | F T1 | 3 | 3 | max_excursion_pct | -0.208 % | [-0.412, -0.010] | -0.068 vs 0.141 | difference |
| call | F T2 | 2 | 2 | break_rate | +0.333 rate | [-0.352, +1.000] | 0.500 vs 0.167 | difference |
| call | F T2 | 2 | 2 | max_excursion_pct | +0.120 % | [-0.121, +0.343] | 0.152 vs 0.033 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F1 rising | 4 | 4 | break_rate | -0.083 rate | [-0.625, +0.583] | 0.250 vs 0.333 | difference |
| call | F1 rising | 4 | 4 | max_excursion_pct | +0.005 % | [-0.221, +0.253] | 0.093 vs 0.087 | difference |
| call | F1 falling | 6 | 6 | break_rate | +0.083 rate | [-0.571, +0.667] | 0.333 vs 0.250 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.005 % | [-0.268, +0.226] | 0.087 vs 0.093 | difference |
| call | F1 T1 | 4 | 4 | break_rate | -0.083 rate | [-0.625, +0.600] | 0.250 vs 0.333 | difference |
| call | F1 T1 | 4 | 4 | max_excursion_pct | -0.118 % | [-0.341, +0.137] | 0.018 vs 0.137 | difference |
| call | F1 T2 | 3 | 3 | break_rate | +0.048 rate | [-0.556, +0.778] | 0.333 vs 0.286 | difference |
| call | F1 T2 | 3 | 3 | max_excursion_pct | +0.094 % | [-0.145, +0.387] | 0.155 vs 0.061 | difference |
| call | F1 T3 | 3 | 3 | break_rate | +0.048 rate | [-0.571, +0.778] | 0.333 vs 0.286 | difference |
| call | F1 T3 | 3 | 3 | max_excursion_pct | +0.041 % | [-0.209, +0.336] | 0.118 vs 0.077 | difference |
| put | all | 52 | 52 | break_rate | +0.404 rate | — | — | level, not an effect |
| put | all | 52 | 52 | max_excursion_pct | +0.231 % | — | — | level, not an effect |
| put | F rising | 14 | 14 | break_rate | +0.286 rate | [+0.071, +0.538] | 0.286 vs 0.000 | difference |
| put | F rising | 14 | 14 | max_excursion_pct | +0.239 % | [+0.056, +0.429] | 0.186 vs -0.053 | difference |
| put | F falling | 2 | 2 | break_rate | -0.286 rate | [-0.533, -0.071] | 0.000 vs 0.286 | difference |
| put | F falling | 2 | 2 | max_excursion_pct | -0.239 % | [-0.429, -0.054] | -0.053 vs 0.186 | difference |
| put | F T1 | 6 | 6 | break_rate | -0.133 rate | [-0.528, +0.328] | 0.167 vs 0.300 | difference |
| put | F T1 | 6 | 6 | max_excursion_pct | -0.129 % | [-0.393, +0.192] | 0.076 vs 0.205 | difference |
| put | F T2 | 5 | 5 | break_rate | +0.218 rate | [-0.273, +0.787] | 0.400 vs 0.182 | difference |
| put | F T2 | 5 | 5 | max_excursion_pct | +0.053 % | [-0.241, +0.371] | 0.193 vs 0.140 | difference |
| put | F T3 | 5 | 5 | break_rate | -0.073 rate | [-0.500, +0.429] | 0.200 vs 0.273 | difference |
| put | F T3 | 5 | 5 | max_excursion_pct | +0.088 % | [-0.219, +0.404] | 0.217 vs 0.129 | difference |
| put | F1 rising | 16 | 16 | break_rate | +0.089 rate | [-0.367, +0.492] | 0.375 vs 0.286 | difference |
| put | F1 rising | 16 | 16 | max_excursion_pct | -0.008 % | [-0.251, +0.227] | 0.173 vs 0.182 | difference |
| put | F1 falling | 7 | 7 | break_rate | -0.089 rate | [-0.500, +0.373] | 0.286 vs 0.375 | difference |
| put | F1 falling | 7 | 7 | max_excursion_pct | +0.008 % | [-0.220, +0.247] | 0.182 vs 0.173 | difference |
| put | F1 T1 | 8 | 8 | break_rate | -0.125 rate | [-0.500, +0.278] | 0.250 vs 0.375 | difference |
| put | F1 T1 | 8 | 8 | max_excursion_pct | -0.030 % | [-0.255, +0.191] | 0.143 vs 0.173 | difference |
| put | F1 T2 | 8 | 8 | break_rate | -0.125 rate | [-0.500, +0.278] | 0.250 vs 0.375 | difference |
| put | F1 T2 | 8 | 8 | max_excursion_pct | -0.088 % | [-0.306, +0.138] | 0.104 vs 0.193 | difference |
| put | F1 T3 | 8 | 8 | break_rate | +0.250 rate | [-0.188, +0.681] | 0.500 vs 0.250 | difference |
| put | F1 T3 | 8 | 8 | max_excursion_pct | +0.119 % | [-0.125, +0.356] | 0.242 vs 0.124 | difference |

**Break rate and excursion · with edge · no-expiry**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 24 | 24 | break_rate | +0.333 rate | — | — | level, not an effect |
| call | all | 24 | 24 | max_excursion_pct | +0.158 % | — | — | level, not an effect |
| call | F rising | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F rising | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F falling | 5 | 5 | break_rate | -0.133 rate | [-0.857, +0.500] | 0.200 vs 0.333 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.112 % | [-0.440, +0.141] | 0.020 vs 0.133 | difference |
| call | F T1 | 3 | 3 | break_rate | -0.400 rate | [-1.000, +0.000] | 0.000 vs 0.400 | difference |
| call | F T1 | 3 | 3 | max_excursion_pct | -0.208 % | [-0.412, -0.010] | -0.068 vs 0.141 | difference |
| call | F T2 | 2 | 2 | break_rate | +0.333 rate | [-0.352, +1.000] | 0.500 vs 0.167 | difference |
| call | F T2 | 2 | 2 | max_excursion_pct | +0.120 % | [-0.121, +0.343] | 0.152 vs 0.033 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F1 rising | 3 | 3 | break_rate | +0.000 rate | [-0.625, +0.750] | 0.333 vs 0.333 | difference |
| call | F1 rising | 3 | 3 | max_excursion_pct | +0.031 % | [-0.231, +0.331] | 0.118 vs 0.087 | difference |
| call | F1 falling | 6 | 6 | break_rate | +0.000 rate | [-0.750, +0.625] | 0.333 vs 0.333 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.031 % | [-0.340, +0.219] | 0.087 vs 0.118 | difference |
| call | F1 T1 | 3 | 3 | break_rate | -0.500 rate | [-1.000, -0.125] | 0.000 vs 0.500 | difference |
| call | F1 T1 | 3 | 3 | max_excursion_pct | -0.248 % | [-0.423, -0.062] | -0.068 vs 0.180 | difference |
| call | F1 T2 | 3 | 3 | break_rate | +0.500 rate | [-0.250, +1.000] | 0.667 vs 0.167 | difference |
| call | F1 T2 | 3 | 3 | max_excursion_pct | +0.217 % | [-0.040, +0.440] | 0.242 vs 0.025 | difference |
| call | F1 T3 | 3 | 3 | break_rate | +0.000 rate | [-0.625, +0.750] | 0.333 vs 0.333 | difference |
| call | F1 T3 | 3 | 3 | max_excursion_pct | +0.031 % | [-0.231, +0.331] | 0.118 vs 0.087 | difference |
| put | all | 46 | 46 | break_rate | +0.413 rate | — | — | level, not an effect |
| put | all | 46 | 46 | max_excursion_pct | +0.222 % | — | — | level, not an effect |
| put | F rising | 11 | 11 | break_rate | +0.273 rate | [+0.000, +0.545] | 0.273 vs 0.000 | difference |
| put | F rising | 11 | 11 | max_excursion_pct | +0.186 % | [-0.014, +0.388] | 0.133 vs -0.053 | difference |
| put | F falling | 2 | 2 | break_rate | -0.273 rate | [-0.576, +0.000] | 0.000 vs 0.273 | difference |
| put | F falling | 2 | 2 | max_excursion_pct | -0.186 % | [-0.394, +0.021] | -0.053 vs 0.133 | difference |
| put | F T1 | 5 | 5 | break_rate | -0.050 rate | [-0.500, +0.475] | 0.200 vs 0.250 | difference |
| put | F T1 | 5 | 5 | max_excursion_pct | -0.049 % | [-0.338, +0.320] | 0.075 vs 0.123 | difference |
| put | F T2 | 4 | 4 | break_rate | -0.333 rate | [-0.647, +0.000] | 0.000 vs 0.333 | difference |
| put | F T2 | 4 | 4 | max_excursion_pct | -0.061 % | [-0.328, +0.194] | 0.063 vs 0.123 | difference |
| put | F T3 | 4 | 4 | break_rate | +0.389 rate | [-0.167, +1.000] | 0.500 vs 0.111 | difference |
| put | F T3 | 4 | 4 | max_excursion_pct | +0.115 % | [-0.221, +0.475] | 0.184 vs 0.069 | difference |
| put | F1 rising | 14 | 14 | break_rate | +0.024 rate | [-0.452, +0.467] | 0.357 vs 0.333 | difference |
| put | F1 rising | 14 | 14 | max_excursion_pct | -0.017 % | [-0.279, +0.234] | 0.140 vs 0.157 | difference |
| put | F1 falling | 6 | 6 | break_rate | -0.024 rate | [-0.471, +0.500] | 0.333 vs 0.357 | difference |
| put | F1 falling | 6 | 6 | max_excursion_pct | +0.017 % | [-0.222, +0.302] | 0.157 vs 0.140 | difference |
| put | F1 T1 | 7 | 7 | break_rate | -0.071 rate | [-0.471, +0.389] | 0.286 vs 0.357 | difference |
| put | F1 T1 | 7 | 7 | max_excursion_pct | -0.024 % | [-0.260, +0.220] | 0.116 vs 0.140 | difference |
| put | F1 T2 | 7 | 7 | break_rate | -0.286 rate | [-0.643, +0.139] | 0.143 vs 0.429 | difference |
| put | F1 T2 | 7 | 7 | max_excursion_pct | -0.060 % | [-0.303, +0.215] | 0.092 vs 0.152 | difference |
| put | F1 T3 | 7 | 7 | break_rate | +0.357 rate | [-0.105, +0.800] | 0.571 vs 0.214 | difference |
| put | F1 T3 | 7 | 7 | max_excursion_pct | +0.084 % | [-0.153, +0.315] | 0.188 vs 0.104 | difference |

**Break rate and excursion · without edge · all**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 27 | 27 | break_rate | +0.370 rate | — | — | level, not an effect |
| call | all | 27 | 27 | max_excursion_pct | +0.198 % | — | — | level, not an effect |
| call | F rising | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F rising | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F falling | 5 | 5 | break_rate | -0.133 rate | [-0.857, +0.500] | 0.200 vs 0.333 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.112 % | [-0.440, +0.141] | 0.020 vs 0.133 | difference |
| call | F T1 | 3 | 3 | break_rate | -0.400 rate | [-1.000, +0.000] | 0.000 vs 0.400 | difference |
| call | F T1 | 3 | 3 | max_excursion_pct | -0.208 % | [-0.412, -0.010] | -0.068 vs 0.141 | difference |
| call | F T2 | 2 | 2 | break_rate | +0.333 rate | [-0.352, +1.000] | 0.500 vs 0.167 | difference |
| call | F T2 | 2 | 2 | max_excursion_pct | +0.120 % | [-0.121, +0.343] | 0.152 vs 0.033 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F1 rising | 4 | 4 | break_rate | -0.083 rate | [-0.625, +0.583] | 0.250 vs 0.333 | difference |
| call | F1 rising | 4 | 4 | max_excursion_pct | +0.005 % | [-0.221, +0.253] | 0.093 vs 0.087 | difference |
| call | F1 falling | 6 | 6 | break_rate | +0.083 rate | [-0.571, +0.667] | 0.333 vs 0.250 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.005 % | [-0.268, +0.226] | 0.087 vs 0.093 | difference |
| call | F1 T1 | 4 | 4 | break_rate | -0.083 rate | [-0.625, +0.600] | 0.250 vs 0.333 | difference |
| call | F1 T1 | 4 | 4 | max_excursion_pct | -0.118 % | [-0.341, +0.137] | 0.018 vs 0.137 | difference |
| call | F1 T2 | 3 | 3 | break_rate | +0.048 rate | [-0.556, +0.778] | 0.333 vs 0.286 | difference |
| call | F1 T2 | 3 | 3 | max_excursion_pct | +0.094 % | [-0.145, +0.387] | 0.155 vs 0.061 | difference |
| call | F1 T3 | 3 | 3 | break_rate | +0.048 rate | [-0.571, +0.778] | 0.333 vs 0.286 | difference |
| call | F1 T3 | 3 | 3 | max_excursion_pct | +0.041 % | [-0.209, +0.336] | 0.118 vs 0.077 | difference |
| put | all | 52 | 52 | break_rate | +0.404 rate | — | — | level, not an effect |
| put | all | 52 | 52 | max_excursion_pct | +0.231 % | — | — | level, not an effect |
| put | F rising | 14 | 14 | break_rate | +0.286 rate | [+0.071, +0.538] | 0.286 vs 0.000 | difference |
| put | F rising | 14 | 14 | max_excursion_pct | +0.239 % | [+0.056, +0.429] | 0.186 vs -0.053 | difference |
| put | F falling | 2 | 2 | break_rate | -0.286 rate | [-0.533, -0.071] | 0.000 vs 0.286 | difference |
| put | F falling | 2 | 2 | max_excursion_pct | -0.239 % | [-0.429, -0.054] | -0.053 vs 0.186 | difference |
| put | F T1 | 6 | 6 | break_rate | -0.133 rate | [-0.528, +0.328] | 0.167 vs 0.300 | difference |
| put | F T1 | 6 | 6 | max_excursion_pct | -0.129 % | [-0.393, +0.192] | 0.076 vs 0.205 | difference |
| put | F T2 | 5 | 5 | break_rate | +0.218 rate | [-0.273, +0.787] | 0.400 vs 0.182 | difference |
| put | F T2 | 5 | 5 | max_excursion_pct | +0.053 % | [-0.241, +0.371] | 0.193 vs 0.140 | difference |
| put | F T3 | 5 | 5 | break_rate | -0.073 rate | [-0.500, +0.429] | 0.200 vs 0.273 | difference |
| put | F T3 | 5 | 5 | max_excursion_pct | +0.088 % | [-0.219, +0.404] | 0.217 vs 0.129 | difference |
| put | F1 rising | 16 | 16 | break_rate | +0.089 rate | [-0.367, +0.492] | 0.375 vs 0.286 | difference |
| put | F1 rising | 16 | 16 | max_excursion_pct | -0.008 % | [-0.251, +0.227] | 0.173 vs 0.182 | difference |
| put | F1 falling | 7 | 7 | break_rate | -0.089 rate | [-0.500, +0.373] | 0.286 vs 0.375 | difference |
| put | F1 falling | 7 | 7 | max_excursion_pct | +0.008 % | [-0.220, +0.247] | 0.182 vs 0.173 | difference |
| put | F1 T1 | 8 | 8 | break_rate | -0.125 rate | [-0.500, +0.278] | 0.250 vs 0.375 | difference |
| put | F1 T1 | 8 | 8 | max_excursion_pct | -0.030 % | [-0.255, +0.191] | 0.143 vs 0.173 | difference |
| put | F1 T2 | 8 | 8 | break_rate | -0.125 rate | [-0.500, +0.278] | 0.250 vs 0.375 | difference |
| put | F1 T2 | 8 | 8 | max_excursion_pct | -0.088 % | [-0.306, +0.138] | 0.104 vs 0.193 | difference |
| put | F1 T3 | 8 | 8 | break_rate | +0.250 rate | [-0.188, +0.681] | 0.500 vs 0.250 | difference |
| put | F1 T3 | 8 | 8 | max_excursion_pct | +0.119 % | [-0.125, +0.356] | 0.242 vs 0.124 | difference |

**Break rate and excursion · without edge · no-expiry**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 24 | 24 | break_rate | +0.333 rate | — | — | level, not an effect |
| call | all | 24 | 24 | max_excursion_pct | +0.158 % | — | — | level, not an effect |
| call | F rising | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F rising | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F falling | 5 | 5 | break_rate | -0.133 rate | [-0.857, +0.500] | 0.200 vs 0.333 | difference |
| call | F falling | 5 | 5 | max_excursion_pct | -0.112 % | [-0.440, +0.141] | 0.020 vs 0.133 | difference |
| call | F T1 | 3 | 3 | break_rate | -0.400 rate | [-1.000, +0.000] | 0.000 vs 0.400 | difference |
| call | F T1 | 3 | 3 | max_excursion_pct | -0.208 % | [-0.412, -0.010] | -0.068 vs 0.141 | difference |
| call | F T2 | 2 | 2 | break_rate | +0.333 rate | [-0.352, +1.000] | 0.500 vs 0.167 | difference |
| call | F T2 | 2 | 2 | max_excursion_pct | +0.120 % | [-0.121, +0.343] | 0.152 vs 0.033 | difference |
| call | F T3 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F T3 | 3 | 3 | max_excursion_pct | +0.112 % | [-0.139, +0.422] | 0.133 vs 0.020 | difference |
| call | F1 rising | 3 | 3 | break_rate | +0.000 rate | [-0.625, +0.750] | 0.333 vs 0.333 | difference |
| call | F1 rising | 3 | 3 | max_excursion_pct | +0.031 % | [-0.231, +0.331] | 0.118 vs 0.087 | difference |
| call | F1 falling | 6 | 6 | break_rate | +0.000 rate | [-0.750, +0.625] | 0.333 vs 0.333 | difference |
| call | F1 falling | 6 | 6 | max_excursion_pct | -0.031 % | [-0.340, +0.219] | 0.087 vs 0.118 | difference |
| call | F1 T1 | 3 | 3 | break_rate | -0.500 rate | [-1.000, -0.125] | 0.000 vs 0.500 | difference |
| call | F1 T1 | 3 | 3 | max_excursion_pct | -0.248 % | [-0.423, -0.062] | -0.068 vs 0.180 | difference |
| call | F1 T2 | 3 | 3 | break_rate | +0.500 rate | [-0.250, +1.000] | 0.667 vs 0.167 | difference |
| call | F1 T2 | 3 | 3 | max_excursion_pct | +0.217 % | [-0.040, +0.440] | 0.242 vs 0.025 | difference |
| call | F1 T3 | 3 | 3 | break_rate | +0.000 rate | [-0.625, +0.750] | 0.333 vs 0.333 | difference |
| call | F1 T3 | 3 | 3 | max_excursion_pct | +0.031 % | [-0.231, +0.331] | 0.118 vs 0.087 | difference |
| put | all | 46 | 46 | break_rate | +0.413 rate | — | — | level, not an effect |
| put | all | 46 | 46 | max_excursion_pct | +0.222 % | — | — | level, not an effect |
| put | F rising | 11 | 11 | break_rate | +0.273 rate | [+0.000, +0.545] | 0.273 vs 0.000 | difference |
| put | F rising | 11 | 11 | max_excursion_pct | +0.186 % | [-0.014, +0.388] | 0.133 vs -0.053 | difference |
| put | F falling | 2 | 2 | break_rate | -0.273 rate | [-0.576, +0.000] | 0.000 vs 0.273 | difference |
| put | F falling | 2 | 2 | max_excursion_pct | -0.186 % | [-0.394, +0.021] | -0.053 vs 0.133 | difference |
| put | F T1 | 5 | 5 | break_rate | -0.050 rate | [-0.500, +0.475] | 0.200 vs 0.250 | difference |
| put | F T1 | 5 | 5 | max_excursion_pct | -0.049 % | [-0.338, +0.320] | 0.075 vs 0.123 | difference |
| put | F T2 | 4 | 4 | break_rate | -0.333 rate | [-0.647, +0.000] | 0.000 vs 0.333 | difference |
| put | F T2 | 4 | 4 | max_excursion_pct | -0.061 % | [-0.328, +0.194] | 0.063 vs 0.123 | difference |
| put | F T3 | 4 | 4 | break_rate | +0.389 rate | [-0.167, +1.000] | 0.500 vs 0.111 | difference |
| put | F T3 | 4 | 4 | max_excursion_pct | +0.115 % | [-0.221, +0.475] | 0.184 vs 0.069 | difference |
| put | F1 rising | 14 | 14 | break_rate | +0.024 rate | [-0.452, +0.467] | 0.357 vs 0.333 | difference |
| put | F1 rising | 14 | 14 | max_excursion_pct | -0.017 % | [-0.279, +0.234] | 0.140 vs 0.157 | difference |
| put | F1 falling | 6 | 6 | break_rate | -0.024 rate | [-0.471, +0.500] | 0.333 vs 0.357 | difference |
| put | F1 falling | 6 | 6 | max_excursion_pct | +0.017 % | [-0.222, +0.302] | 0.157 vs 0.140 | difference |
| put | F1 T1 | 7 | 7 | break_rate | -0.071 rate | [-0.471, +0.389] | 0.286 vs 0.357 | difference |
| put | F1 T1 | 7 | 7 | max_excursion_pct | -0.024 % | [-0.260, +0.220] | 0.116 vs 0.140 | difference |
| put | F1 T2 | 7 | 7 | break_rate | -0.286 rate | [-0.643, +0.139] | 0.143 vs 0.429 | difference |
| put | F1 T2 | 7 | 7 | max_excursion_pct | -0.060 % | [-0.303, +0.215] | 0.092 vs 0.152 | difference |
| put | F1 T3 | 7 | 7 | break_rate | +0.357 rate | [-0.105, +0.800] | 0.571 vs 0.214 | difference |
| put | F1 T3 | 7 | 7 | max_excursion_pct | +0.084 % | [-0.153, +0.315] | 0.188 vs 0.104 | difference |

### D band = 0.25 %   [exploratory]

**Sessions producing NO approach, by wall distance**

| side | wall distance | no approach | sessions in bucket | share |
|---|---|---|---|---|
| call | <=2% | 78 | 109 | 71.6% |
| call | 2-4% | 59 | 59 | 100.0% |
| call | >4% | 77 | 77 | 100.0% |
| put | <=2% | 67 | 125 | 53.6% |
| put | 2-4% | 61 | 62 | 98.4% |
| put | >4% | 58 | 58 | 100.0% |

**Break rate and excursion · with edge · all**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 31 | 31 | break_rate | +0.323 rate | — | — | level, not an effect |
| call | all | 31 | 31 | max_excursion_pct | +0.144 % | — | — | level, not an effect |
| call | F rising | 3 | 3 | break_rate | +0.000 rate | [-0.800, +0.750] | 0.333 vs 0.333 | difference |
| call | F rising | 3 | 3 | max_excursion_pct | -0.120 % | [-0.431, +0.328] | -0.004 vs 0.116 | difference |
| call | F falling | 3 | 3 | break_rate | +0.000 rate | [-0.800, +0.800] | 0.333 vs 0.333 | difference |
| call | F falling | 3 | 3 | max_excursion_pct | +0.120 % | [-0.334, +0.444] | 0.116 vs -0.004 | difference |
| call | F T1 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F T1 | 2 | 2 | max_excursion_pct | +0.156 % | [-0.220, +0.456] | 0.161 vs 0.004 | difference |
| call | F T2 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F T2 | 2 | 2 | max_excursion_pct | +0.253 % | [-0.077, +0.586] | 0.225 vs -0.028 | difference |
| call | F T3 | 2 | 2 | break_rate | -0.500 rate | [-1.000, +0.000] | 0.000 vs 0.500 | difference |
| call | F T3 | 2 | 2 | max_excursion_pct | -0.409 % | [-0.608, -0.240] | -0.216 vs 0.193 | difference |
| call | F1 rising | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F1 rising | 3 | 3 | max_excursion_pct | +0.058 % | [-0.274, +0.431] | 0.083 vs 0.026 | difference |
| call | F1 falling | 5 | 5 | break_rate | -0.133 rate | [-0.857, +0.500] | 0.200 vs 0.333 | difference |
| call | F1 falling | 5 | 5 | max_excursion_pct | -0.058 % | [-0.436, +0.259] | 0.026 vs 0.083 | difference |
| call | F1 T1 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F1 T1 | 3 | 3 | max_excursion_pct | +0.111 % | [-0.173, +0.362] | 0.116 vs 0.006 | difference |
| call | F1 T2 | 2 | 2 | break_rate | -0.333 rate | [-0.750, +0.000] | 0.000 vs 0.333 | difference |
| call | F1 T2 | 2 | 2 | max_excursion_pct | -0.210 % | [-0.454, +0.036] | -0.111 vs 0.100 | difference |
| call | F1 T3 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F1 T3 | 3 | 3 | max_excursion_pct | +0.058 % | [-0.274, +0.431] | 0.083 vs 0.026 | difference |
| put | all | 59 | 59 | break_rate | +0.356 rate | — | — | level, not an effect |
| put | all | 59 | 59 | max_excursion_pct | +0.181 % | — | — | level, not an effect |
| put | F rising | 12 | 12 | break_rate | +0.083 rate | [+0.000, +0.273] | 0.083 vs 0.000 | difference |
| put | F rising | 12 | 12 | max_excursion_pct | +0.005 % | [-0.114, +0.148] | 0.030 vs 0.026 | difference |
| put | F falling | 1 | 1 | break_rate | -0.083 rate | [-0.273, +0.000] | 0.000 vs 0.083 | difference |
| put | F falling | 1 | 1 | max_excursion_pct | -0.005 % | [-0.142, +0.118] | 0.026 vs 0.030 | difference |
| put | F T1 | 5 | 5 | break_rate | -0.125 rate | [-0.400, +0.000] | 0.000 vs 0.125 | difference |
| put | F T1 | 5 | 5 | max_excursion_pct | -0.129 % | [-0.338, +0.055] | -0.049 vs 0.080 | difference |
| put | F T2 | 4 | 4 | break_rate | -0.111 rate | [-0.375, +0.000] | 0.000 vs 0.111 | difference |
| put | F T2 | 4 | 4 | max_excursion_pct | -0.176 % | [-0.374, +0.015] | -0.091 vs 0.084 | difference |
| put | F T3 | 4 | 4 | break_rate | +0.250 rate | [+0.000, +0.800] | 0.250 vs 0.000 | difference |
| put | F T3 | 4 | 4 | max_excursion_pct | +0.319 % | [+0.034, +0.626] | 0.251 vs -0.068 | difference |
| put | F1 rising | 12 | 12 | break_rate | +0.083 rate | [-0.333, +0.500] | 0.333 vs 0.250 | difference |
| put | F1 rising | 12 | 12 | max_excursion_pct | +0.097 % | [-0.157, +0.349] | 0.153 vs 0.056 | difference |
| put | F1 falling | 8 | 8 | break_rate | -0.083 rate | [-0.467, +0.333] | 0.250 vs 0.333 | difference |
| put | F1 falling | 8 | 8 | max_excursion_pct | -0.097 % | [-0.343, +0.165] | 0.056 vs 0.153 | difference |
| put | F1 T1 | 7 | 7 | break_rate | -0.022 rate | [-0.429, +0.438] | 0.286 vs 0.308 | difference |
| put | F1 T1 | 7 | 7 | max_excursion_pct | -0.043 % | [-0.301, +0.239] | 0.086 vs 0.129 | difference |
| put | F1 T2 | 6 | 6 | break_rate | -0.190 rate | [-0.571, +0.267] | 0.167 vs 0.357 | difference |
| put | F1 T2 | 6 | 6 | max_excursion_pct | -0.051 % | [-0.336, +0.270] | 0.078 vs 0.129 | difference |
| put | F1 T3 | 7 | 7 | break_rate | +0.198 rate | [-0.250, +0.667] | 0.429 vs 0.231 | difference |
| put | F1 T3 | 7 | 7 | max_excursion_pct | +0.091 % | [-0.164, +0.343] | 0.173 vs 0.082 | difference |

**Break rate and excursion · with edge · no-expiry**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 27 | 27 | break_rate | +0.296 rate | — | — | level, not an effect |
| call | all | 27 | 27 | max_excursion_pct | +0.115 % | — | — | level, not an effect |
| call | F rising | 2 | 2 | break_rate | +0.167 rate | [-0.750, +1.000] | 0.500 vs 0.333 | difference |
| call | F rising | 2 | 2 | max_excursion_pct | -0.028 % | [-0.444, +0.388] | 0.089 vs 0.116 | difference |
| call | F falling | 3 | 3 | break_rate | -0.167 rate | [-1.000, +0.750] | 0.333 vs 0.500 | difference |
| call | F falling | 3 | 3 | max_excursion_pct | +0.028 % | [-0.388, +0.459] | 0.116 vs 0.089 | difference |
| call | F1 rising | 1 | 1 | break_rate | +0.800 rate | [+0.400, +1.000] | 1.000 vs 0.200 | difference |
| call | F1 rising | 1 | 1 | max_excursion_pct | +0.396 % | [+0.246, +0.558] | 0.422 vs 0.026 | difference |
| call | F1 falling | 5 | 5 | break_rate | -0.800 rate | [-1.000, -0.333] | 0.200 vs 1.000 | difference |
| call | F1 falling | 5 | 5 | max_excursion_pct | -0.396 % | [-0.555, -0.241] | 0.026 vs 0.422 | difference |
| call | F1 T1 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F1 T1 | 2 | 2 | max_excursion_pct | +0.104 % | [-0.238, +0.390] | 0.161 vs 0.057 | difference |
| call | F1 T2 | 2 | 2 | break_rate | -0.500 rate | [-1.000, +0.000] | 0.000 vs 0.500 | difference |
| call | F1 T2 | 2 | 2 | max_excursion_pct | -0.300 % | [-0.557, -0.055] | -0.108 vs 0.192 | difference |
| call | F1 T3 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F1 T3 | 2 | 2 | max_excursion_pct | +0.196 % | [-0.129, +0.522] | 0.223 vs 0.026 | difference |
| put | all | 53 | 53 | break_rate | +0.358 rate | — | — | level, not an effect |
| put | all | 53 | 53 | max_excursion_pct | +0.167 % | — | — | level, not an effect |
| put | F rising | 10 | 10 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F rising | 10 | 10 | max_excursion_pct | -0.071 % | [-0.152, +0.038] | -0.045 vs 0.026 | difference |
| put | F falling | 1 | 1 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F falling | 1 | 1 | max_excursion_pct | +0.071 % | [-0.024, +0.150] | 0.026 vs -0.045 | difference |
| put | F T1 | 4 | 4 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F T1 | 4 | 4 | max_excursion_pct | -0.019 % | [-0.176, +0.109] | -0.051 vs -0.031 | difference |
| put | F T2 | 3 | 3 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F T2 | 3 | 3 | max_excursion_pct | -0.074 % | [-0.199, +0.040] | -0.092 vs -0.018 | difference |
| put | F T3 | 4 | 4 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F T3 | 4 | 4 | max_excursion_pct | +0.083 % | [-0.132, +0.343] | 0.014 vs -0.069 | difference |
| put | F1 rising | 10 | 10 | break_rate | +0.050 rate | [-0.390, +0.462] | 0.300 vs 0.250 | difference |
| put | F1 rising | 10 | 10 | max_excursion_pct | +0.047 % | [-0.217, +0.295] | 0.102 vs 0.056 | difference |
| put | F1 falling | 8 | 8 | break_rate | -0.050 rate | [-0.500, +0.375] | 0.250 vs 0.300 | difference |
| put | F1 falling | 8 | 8 | max_excursion_pct | -0.047 % | [-0.316, +0.221] | 0.056 vs 0.102 | difference |
| put | F1 T1 | 6 | 6 | break_rate | +0.083 rate | [-0.357, +0.583] | 0.333 vs 0.250 | difference |
| put | F1 T1 | 6 | 6 | max_excursion_pct | +0.031 % | [-0.245, +0.334] | 0.102 vs 0.071 | difference |
| put | F1 T2 | 6 | 6 | break_rate | -0.167 rate | [-0.545, +0.292] | 0.167 vs 0.333 | difference |
| put | F1 T2 | 6 | 6 | max_excursion_pct | +0.016 % | [-0.250, +0.328] | 0.092 vs 0.076 | difference |
| put | F1 T3 | 6 | 6 | break_rate | +0.083 rate | [-0.375, +0.600] | 0.333 vs 0.250 | difference |
| put | F1 T3 | 6 | 6 | max_excursion_pct | -0.048 % | [-0.296, +0.206] | 0.050 vs 0.097 | difference |

**Break rate and excursion · without edge · all**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 31 | 31 | break_rate | +0.323 rate | — | — | level, not an effect |
| call | all | 31 | 31 | max_excursion_pct | +0.144 % | — | — | level, not an effect |
| call | F rising | 3 | 3 | break_rate | +0.000 rate | [-0.800, +0.750] | 0.333 vs 0.333 | difference |
| call | F rising | 3 | 3 | max_excursion_pct | -0.120 % | [-0.431, +0.328] | -0.004 vs 0.116 | difference |
| call | F falling | 3 | 3 | break_rate | +0.000 rate | [-0.800, +0.800] | 0.333 vs 0.333 | difference |
| call | F falling | 3 | 3 | max_excursion_pct | +0.120 % | [-0.334, +0.444] | 0.116 vs -0.004 | difference |
| call | F T1 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F T1 | 2 | 2 | max_excursion_pct | +0.156 % | [-0.220, +0.456] | 0.161 vs 0.004 | difference |
| call | F T2 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F T2 | 2 | 2 | max_excursion_pct | +0.253 % | [-0.077, +0.586] | 0.225 vs -0.028 | difference |
| call | F T3 | 2 | 2 | break_rate | -0.500 rate | [-1.000, +0.000] | 0.000 vs 0.500 | difference |
| call | F T3 | 2 | 2 | max_excursion_pct | -0.409 % | [-0.608, -0.240] | -0.216 vs 0.193 | difference |
| call | F1 rising | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F1 rising | 3 | 3 | max_excursion_pct | +0.058 % | [-0.274, +0.431] | 0.083 vs 0.026 | difference |
| call | F1 falling | 5 | 5 | break_rate | -0.133 rate | [-0.857, +0.500] | 0.200 vs 0.333 | difference |
| call | F1 falling | 5 | 5 | max_excursion_pct | -0.058 % | [-0.436, +0.259] | 0.026 vs 0.083 | difference |
| call | F1 T1 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F1 T1 | 3 | 3 | max_excursion_pct | +0.111 % | [-0.173, +0.362] | 0.116 vs 0.006 | difference |
| call | F1 T2 | 2 | 2 | break_rate | -0.333 rate | [-0.750, +0.000] | 0.000 vs 0.333 | difference |
| call | F1 T2 | 2 | 2 | max_excursion_pct | -0.210 % | [-0.454, +0.036] | -0.111 vs 0.100 | difference |
| call | F1 T3 | 3 | 3 | break_rate | +0.133 rate | [-0.500, +0.857] | 0.333 vs 0.200 | difference |
| call | F1 T3 | 3 | 3 | max_excursion_pct | +0.058 % | [-0.274, +0.431] | 0.083 vs 0.026 | difference |
| put | all | 59 | 59 | break_rate | +0.356 rate | — | — | level, not an effect |
| put | all | 59 | 59 | max_excursion_pct | +0.181 % | — | — | level, not an effect |
| put | F rising | 12 | 12 | break_rate | +0.083 rate | [+0.000, +0.273] | 0.083 vs 0.000 | difference |
| put | F rising | 12 | 12 | max_excursion_pct | +0.005 % | [-0.114, +0.148] | 0.030 vs 0.026 | difference |
| put | F falling | 1 | 1 | break_rate | -0.083 rate | [-0.273, +0.000] | 0.000 vs 0.083 | difference |
| put | F falling | 1 | 1 | max_excursion_pct | -0.005 % | [-0.142, +0.118] | 0.026 vs 0.030 | difference |
| put | F T1 | 5 | 5 | break_rate | -0.125 rate | [-0.400, +0.000] | 0.000 vs 0.125 | difference |
| put | F T1 | 5 | 5 | max_excursion_pct | -0.129 % | [-0.338, +0.055] | -0.049 vs 0.080 | difference |
| put | F T2 | 4 | 4 | break_rate | -0.111 rate | [-0.375, +0.000] | 0.000 vs 0.111 | difference |
| put | F T2 | 4 | 4 | max_excursion_pct | -0.176 % | [-0.374, +0.015] | -0.091 vs 0.084 | difference |
| put | F T3 | 4 | 4 | break_rate | +0.250 rate | [+0.000, +0.800] | 0.250 vs 0.000 | difference |
| put | F T3 | 4 | 4 | max_excursion_pct | +0.319 % | [+0.034, +0.626] | 0.251 vs -0.068 | difference |
| put | F1 rising | 12 | 12 | break_rate | +0.083 rate | [-0.333, +0.500] | 0.333 vs 0.250 | difference |
| put | F1 rising | 12 | 12 | max_excursion_pct | +0.097 % | [-0.157, +0.349] | 0.153 vs 0.056 | difference |
| put | F1 falling | 8 | 8 | break_rate | -0.083 rate | [-0.467, +0.333] | 0.250 vs 0.333 | difference |
| put | F1 falling | 8 | 8 | max_excursion_pct | -0.097 % | [-0.343, +0.165] | 0.056 vs 0.153 | difference |
| put | F1 T1 | 7 | 7 | break_rate | -0.022 rate | [-0.429, +0.438] | 0.286 vs 0.308 | difference |
| put | F1 T1 | 7 | 7 | max_excursion_pct | -0.043 % | [-0.301, +0.239] | 0.086 vs 0.129 | difference |
| put | F1 T2 | 6 | 6 | break_rate | -0.190 rate | [-0.571, +0.267] | 0.167 vs 0.357 | difference |
| put | F1 T2 | 6 | 6 | max_excursion_pct | -0.051 % | [-0.336, +0.270] | 0.078 vs 0.129 | difference |
| put | F1 T3 | 7 | 7 | break_rate | +0.198 rate | [-0.250, +0.667] | 0.429 vs 0.231 | difference |
| put | F1 T3 | 7 | 7 | max_excursion_pct | +0.091 % | [-0.164, +0.343] | 0.173 vs 0.082 | difference |

**Break rate and excursion · without edge · no-expiry**

| side | condition  n | sessions | outcome | effect (diff vs complement) | 95% CI | levels: cell vs comp (not effects) | kind |
|---|------|---|---|---|---|---|---|
| call | all | 27 | 27 | break_rate | +0.296 rate | — | — | level, not an effect |
| call | all | 27 | 27 | max_excursion_pct | +0.115 % | — | — | level, not an effect |
| call | F rising | 2 | 2 | break_rate | +0.167 rate | [-0.750, +1.000] | 0.500 vs 0.333 | difference |
| call | F rising | 2 | 2 | max_excursion_pct | -0.028 % | [-0.444, +0.388] | 0.089 vs 0.116 | difference |
| call | F falling | 3 | 3 | break_rate | -0.167 rate | [-1.000, +0.750] | 0.333 vs 0.500 | difference |
| call | F falling | 3 | 3 | max_excursion_pct | +0.028 % | [-0.388, +0.459] | 0.116 vs 0.089 | difference |
| call | F1 rising | 1 | 1 | break_rate | +0.800 rate | [+0.400, +1.000] | 1.000 vs 0.200 | difference |
| call | F1 rising | 1 | 1 | max_excursion_pct | +0.396 % | [+0.246, +0.558] | 0.422 vs 0.026 | difference |
| call | F1 falling | 5 | 5 | break_rate | -0.800 rate | [-1.000, -0.333] | 0.200 vs 1.000 | difference |
| call | F1 falling | 5 | 5 | max_excursion_pct | -0.396 % | [-0.555, -0.241] | 0.026 vs 0.422 | difference |
| call | F1 T1 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F1 T1 | 2 | 2 | max_excursion_pct | +0.104 % | [-0.238, +0.390] | 0.161 vs 0.057 | difference |
| call | F1 T2 | 2 | 2 | break_rate | -0.500 rate | [-1.000, +0.000] | 0.000 vs 0.500 | difference |
| call | F1 T2 | 2 | 2 | max_excursion_pct | -0.300 % | [-0.557, -0.055] | -0.108 vs 0.192 | difference |
| call | F1 T3 | 2 | 2 | break_rate | +0.250 rate | [-0.600, +1.000] | 0.500 vs 0.250 | difference |
| call | F1 T3 | 2 | 2 | max_excursion_pct | +0.196 % | [-0.129, +0.522] | 0.223 vs 0.026 | difference |
| put | all | 53 | 53 | break_rate | +0.358 rate | — | — | level, not an effect |
| put | all | 53 | 53 | max_excursion_pct | +0.167 % | — | — | level, not an effect |
| put | F rising | 10 | 10 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F rising | 10 | 10 | max_excursion_pct | -0.071 % | [-0.152, +0.038] | -0.045 vs 0.026 | difference |
| put | F falling | 1 | 1 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F falling | 1 | 1 | max_excursion_pct | +0.071 % | [-0.024, +0.150] | 0.026 vs -0.045 | difference |
| put | F T1 | 4 | 4 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F T1 | 4 | 4 | max_excursion_pct | -0.019 % | [-0.176, +0.109] | -0.051 vs -0.031 | difference |
| put | F T2 | 3 | 3 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F T2 | 3 | 3 | max_excursion_pct | -0.074 % | [-0.199, +0.040] | -0.092 vs -0.018 | difference |
| put | F T3 | 4 | 4 | break_rate | +0.000 rate | [+0.000, +0.000] | 0.000 vs 0.000 | difference |
| put | F T3 | 4 | 4 | max_excursion_pct | +0.083 % | [-0.132, +0.343] | 0.014 vs -0.069 | difference |
| put | F1 rising | 10 | 10 | break_rate | +0.050 rate | [-0.390, +0.462] | 0.300 vs 0.250 | difference |
| put | F1 rising | 10 | 10 | max_excursion_pct | +0.047 % | [-0.217, +0.295] | 0.102 vs 0.056 | difference |
| put | F1 falling | 8 | 8 | break_rate | -0.050 rate | [-0.500, +0.375] | 0.250 vs 0.300 | difference |
| put | F1 falling | 8 | 8 | max_excursion_pct | -0.047 % | [-0.316, +0.221] | 0.056 vs 0.102 | difference |
| put | F1 T1 | 6 | 6 | break_rate | +0.083 rate | [-0.357, +0.583] | 0.333 vs 0.250 | difference |
| put | F1 T1 | 6 | 6 | max_excursion_pct | +0.031 % | [-0.245, +0.334] | 0.102 vs 0.071 | difference |
| put | F1 T2 | 6 | 6 | break_rate | -0.167 rate | [-0.545, +0.292] | 0.167 vs 0.333 | difference |
| put | F1 T2 | 6 | 6 | max_excursion_pct | +0.016 % | [-0.250, +0.328] | 0.092 vs 0.076 | difference |
| put | F1 T3 | 6 | 6 | break_rate | +0.083 rate | [-0.375, +0.600] | 0.333 vs 0.250 | difference |
| put | F1 T3 | 6 | 6 | max_excursion_pct | -0.048 % | [-0.296, +0.206] | 0.050 vs 0.097 | difference |

---

## CUTS LEDGER   [exploratory]

Every cell computed, printed or not. A cell is one (subset × definition × outcome) with its own interval. **Every effect is a difference against the cell's complement**, for signed and unsigned outcomes alike, so the sample's common drift cancels. A cell with no complement is recorded as a **level** and cannot exclude zero by construction.

| study | cells | levels only | testable | intervals excluding zero |
|---|---|---|---|---|
| A1 | 2688 | 0 | 2688 | 300 |
| A2 | 192 | 0 | 192 | 18 |
| A3 | 72 | 0 | 70 | 16 |
| B | 120 | 0 | 120 | 22 |
| C1 | 12 | 0 | 12 | 4 |
| C2 | 32 | 0 | 32 | 0 |
| C3 | 32 | 0 | 32 | 3 |
| D | 516 | 48 | 468 | 40 |
| **total** | **3664** | **48** | **3614** | **403** |

Testable cells (a real effect, n > 0): **3614**. Expected to exclude zero by chance alone at 5 %: **180.7**. Observed: **403**.

**A1 by family.** A1's cells are the same windows re-cut across strengths, subsets, time-of-day buckets and outcomes, so one structure appears as many correlated cells. Counting instead by **(contrast, step, OI series) family**: **12** families carry at least one testable cell, and **12** of them carry at least one interval excluding zero, against **300** A1 cells excluding zero.

- LB vs SC · step 15 · OI F — has an interval excluding zero
- LB vs SC · step 15 · OI F1 — has an interval excluding zero
- LB vs SC · step 30 · OI F — has an interval excluding zero
- LB vs SC · step 30 · OI F1 — has an interval excluding zero
- LB vs SC · step 60 · OI F — has an interval excluding zero
- LB vs SC · step 60 · OI F1 — has an interval excluding zero
- SB vs LU · step 15 · OI F — has an interval excluding zero
- SB vs LU · step 15 · OI F1 — has an interval excluding zero
- SB vs LU · step 30 · OI F — has an interval excluding zero
- SB vs LU · step 30 · OI F1 — has an interval excluding zero
- SB vs LU · step 60 · OI F — has an interval excluding zero
- SB vs LU · step 60 · OI F1 — has an interval excluding zero

These cells are **not independent** — they share rows across window lengths, OI series, subsets, time-of-day buckets and outcomes — so the chance expectation is a reference point for sizing the search, not a null distribution, and the comparison is not a test.

**Robustness recomputation failures: none.**


## SHORTLIST   [exploratory]

**A shortlist drawn from many cuts is biased upward.** These ten were selected *because* they are the most extreme among 3664 cells; selecting on the statistic guarantees the estimates here overstate whatever is real. Nothing in this list is a finding.

Every effect here is a **difference against the cell's complement**, not a level, so the sample's market drift is cancelled rather than counted.

**Ranking: |effect| ÷ half-width of its own 95 % interval.** This is unit-free, so bp, rate and %% cells compete on one scale and no per-unit quota is needed. Level-only cells are excluded by construction.

| # | study | definition | outcome | n | sessions | effect | 95% CI | |eff|/half-width | F vs F1 | both halves | expiry removed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | C1 | set=rest, metric=intraday_range | rngnext | 218 | 218 | -48.725 bp | [-69.162, -28.441] | 2.39 | n/a | n/a | n/a |
| 2 | C1 | set=large, metric=intraday_range | rngnext | 25 | 25 | +48.725 bp | [+27.152, +69.296] | 2.31 | n/a | n/a | n/a |
| 3 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=all day | retnext | 80 | 57 | -102.927 bp | [-156.376, -54.347] | 2.02 | yes | yes | yes |
| 4 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=all day | contnext | 80 | 57 | -102.927 bp | [-156.376, -54.347] | 2.02 | yes | yes | yes |
| 5 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=all day | hitnext | 80 | 57 | -0.395 rate | [-0.582, -0.183] | 1.98 | yes | yes | yes |
| 6 | C1 | set=large, metric=abs_ret | rngnext | 25 | 25 | +44.692 bp | [+22.309, +68.499] | 1.94 | n/a | n/a | n/a |
| 7 | C1 | set=rest, metric=abs_ret | rngnext | 218 | 218 | -44.692 bp | [-67.044, -19.983] | 1.90 | n/a | n/a | n/a |
| 8 | A3 | oi=F, subset=all, pair=SB vs LU | retnext | 87 | 87 | -67.568 bp | [-105.332, -31.317] | 1.83 | yes | yes | yes |
| 9 | A3 | oi=F, subset=all, pair=SB vs LU | contnext | 87 | 87 | +67.568 bp | [+31.317, +105.332] | 1.83 | yes | yes | yes |
| 10 | A1 | step=60, oi=F, subset=no-expiry, strength=strong, pair=LB vs SC, tod=to 11:30 | retnext | 31 | 29 | -107.058 bp | [-168.401, -49.492] | 1.80 | yes | yes | yes |

Eligibility: interval excludes zero, n sessions ≥ 20, and the cell is a real effect (signed level, or unsigned difference against a complement). Eligible cells: **352**; the ten above are the extreme tail of that set.


---

*Exploration. No verdict. Nothing here is a finding until confirmed once on unseen data. Read-only run: no database write, no commit, no branch, no push. Every query through `bin/roq.sh` as `merdian_ro`; every Python process under `ulimit -v 700000`.*
