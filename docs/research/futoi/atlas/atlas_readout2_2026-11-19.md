# Atlas readout 2 — 2026-11-19

Exploration. No verdict. Nothing here is a finding until confirmed once on unseen data.

Read-only; no database access. Tables only.

---

## Provenance — read from the code   [exploratory]

### (a) How a calendar week is keyed for the block bootstrap

| item | value |
|---|---|
| key function | `iso_week()` — `atlas_readout2.py:42` |
| key expression | ``"%04d-W%02d" % (y, w)`` from `dt.date.fromisoformat(d).isocalendar()` — `atlas_readout2.py:44` |
| cluster selector | `BY_WEEK` — `atlas_readout2.py:86` |
| resampler | `boot_diff_by(..., cluster)` — `atlas_readout2.py:47` |
| sessions in the window | 247 |
| **distinct ISO weeks** | **53** |
| first / last week | 2025-W14 / 2026-W14 |
| sessions per week | min 1, median 5, max 5 |

### (b) The trailing-20-session window

| item | value |
|---|---|
| slice | `prior = sessions[max(0, i - 20):i]` — `atlas_readout2.py:137` |
| end of window | the slice upper bound is `i`, **exclusive**, so the window's last session is `sessions[i-1]` — the PRIOR session. The session being classified, `sessions[i]`, is never in its own window. |
| returns used | `rets[x]` = close-to-close log return INTO session `x`, i.e. ln P(x)/P(x−1) — `atlas_readout2.py:134` |
| realised vol | sample sd of those returns — `atlas_readout2.py:141` |
| trailing return | `sum(rr)`, the sum of the log returns in the window, = ln P(d−1)/P(d−21) — `atlas_readout2.py:142` |
| minimum returns required | 10 — `atlas_readout2.py:139` |
| sessions with a trailing value | 236 of 247 |

### (c) One worked example row for item 3

| field | value |
|---|---|
| session classified | 2025-04-21 |
| its trailing window, first session | 2025-04-01 |
| its trailing window, last session | 2025-04-17 |
| sessions in the window | 11 |
| the classified session is inside its own window | **no** — 2025-04-21 > 2025-04-17 |
| trailing 20-session realised vol | 0.016151 |
| tercile cut points | 0.005946, 0.006921 |
| tercile assigned | **T3** |
| trailing 20-session return | +0.022520 |
| its own class / dOI sign | LB / dOI>0 |
| its own next-session return | +12.430 bp |
| ISO week used for the block bootstrap | 2025-W17 |

---

## 1. Pooled OI-sign contrast — (LB+SB) vs (SC+LU) on `retnext`   [exploratory]

Price sign is NOT held fixed here: both groups contain both price signs, so the contrast is the sign of dOI alone. Rows must carry a real class, so FLAT and MISSING are excluded. Session CI resamples sessions; week-block CI resamples whole ISO calendar weeks. 2000 resamples, seed 20261118.

| slice | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|
| step 15 · F · all | 3003 | 1180 | 245 | 52 | -16.515 | [-28.672, -4.138] | [-28.242, -5.053] |
| step 30 · F · all | 1536 | 544 | 245 | 52 | -18.370 | [-31.920, -4.747] | [-30.681, -6.058] |
| step 60 · F · all | 810 | 244 | 240 | 52 | -23.971 | [-39.856, -7.010] | [-39.014, -9.611] |
| day · F · all | 144 | 96 | 240 | 52 | -46.112 | [-69.464, -24.816] | [-66.669, -25.695] |
| step 15 · F · no-expiry | 2677 | 1093 | 223 | 52 | -21.717 | [-34.881, -8.993] | [-34.128, -9.814] |
| step 30 · F · no-expiry | 1363 | 514 | 223 | 52 | -24.735 | [-37.965, -11.030] | [-37.516, -12.058] |
| step 60 · F · no-expiry | 720 | 229 | 218 | 52 | -30.067 | [-47.949, -13.446] | [-46.410, -13.971] |
| day · F · no-expiry | 143 | 75 | 218 | 52 | -39.121 | [-63.203, -16.947] | [-62.760, -16.772] |
| step 15 · F1 · all | 3301 | 2521 | 245 | 52 | -15.372 | [-24.696, -5.953] | [-24.600, -6.396] |
| step 30 · F1 · all | 1673 | 1240 | 245 | 52 | -18.823 | [-29.737, -7.401] | [-30.160, -8.025] |
| step 60 · F1 · all | 851 | 607 | 244 | 52 | -23.377 | [-37.406, -9.621] | [-38.046, -9.371] |
| day · F1 · all | 93 | 149 | 242 | 52 | -27.052 | [-49.483, -4.565] | [-48.923, -5.584] |
| step 15 · F1 · no-expiry | 3072 | 2223 | 223 | 52 | -10.949 | [-19.829, -1.982] | [-18.753, -3.216] |
| step 30 · F1 · no-expiry | 1562 | 1089 | 223 | 52 | -14.535 | [-25.422, -3.698] | [-25.152, -4.809] |
| step 60 · F1 · no-expiry | 798 | 528 | 222 | 52 | -18.179 | [-31.107, -5.552] | [-32.164, -4.162] |
| day · F1 · no-expiry | 82 | 138 | 220 | 52 | -26.584 | [-50.505, -2.908] | [-49.549, -4.516] |

**Strong windows only, steps 30 and 60**

| slice | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|
| step 30 strong · F · all | 509 | 98 | 182 | 52 | -51.368 | [-83.089, -23.414] | [-82.259, -20.863] |
| step 60 strong · F · all | 264 | 46 | 150 | 50 | -73.559 | [-124.247, -27.176] | [-115.620, -31.761] |
| step 30 strong · F · no-expiry | 434 | 93 | 163 | 52 | -61.113 | [-92.959, -30.022] | [-92.845, -28.112] |
| step 60 strong · F · no-expiry | 224 | 42 | 135 | 50 | -90.119 | [-142.206, -41.662] | [-134.459, -45.406] |
| step 30 strong · F1 · all | 479 | 343 | 226 | 52 | -37.708 | [-58.332, -16.931] | [-59.452, -15.258] |
| step 60 strong · F1 · all | 247 | 154 | 193 | 52 | -51.266 | [-80.681, -23.403] | [-76.810, -24.472] |
| step 30 strong · F1 · no-expiry | 440 | 284 | 204 | 52 | -28.825 | [-49.066, -8.483] | [-48.332, -7.377] |
| step 60 strong · F1 · no-expiry | 228 | 124 | 175 | 52 | -40.862 | [-73.155, -11.422] | [-67.192, -14.307] |

## 2. Day level, F — by calendar month, and with 2026-02-01..2026-03-30 removed   [exploratory]

| month | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|
| 2025-04 | 11 | 7 | 18 | 5 | -49.394 | [-165.173, +58.337] | [-125.302, +35.818] |
| 2025-05 | 13 | 8 | 21 | 5 | -88.789 | [-208.199, +4.011] | [-251.067, +17.661] |
| 2025-06 | 14 | 7 | 21 | 5 | +10.130 | [-53.992, +82.569] | [-15.289, +52.059] |
| 2025-07 | 14 | 9 | 23 | 5 | -9.156 | [-43.495, +27.414] | [-42.038, +19.210] |
| 2025-08 | 10 | 9 | 19 | 5 | -43.754 | [-103.251, +15.090] | [-140.517, +27.852] |
| 2025-09 | 14 | 8 | 22 | 5 | -37.076 | [-88.577, +5.690] | [-97.790, -1.717] |
| 2025-10 | 6 | 10 | 16 | 5 | -3.196 | [-64.711, +62.303] | [-53.418, +66.857] |
| 2025-11 | 8 | 11 | 19 | 4 | -32.756 | [-87.322, +17.210] | [-94.898, +34.586] |
| 2025-12 | 12 | 10 | 22 | 5 | -34.666 | [-80.347, +13.070] | [-60.515, -11.406] |
| 2026-01 | 15 | 5 | 20 | 5 | -62.450 | [-139.413, +17.973] | [-149.106, +40.434] |
| 2026-02 | 11 | 10 | 21 | 5 | -48.621 | [-137.324, +32.286] | [-117.532, +25.913] |
| 2026-03 | 16 | 2 | 18 | 4 | -160.715 | [-244.302, -79.863] | [-235.346, -131.403] |

| slice | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|
| day · F · all months | 144 | 96 | 240 | 52 | -46.112 | [-69.464, -24.816] | [-66.669, -25.695] |
| day · F · 2026-02-01..2026-03-30 REMOVED | 117 | 84 | 201 | 44 | -36.446 | [-57.964, -13.915] | [-58.051, -15.839] |

## 3. Day level, F — within trailing-20-session terciles   [exploratory]

Both trailing quantities use data up to the **prior close only**: realised volatility is the sd of the 20 close-to-close log returns ending at d−1, and the trailing return is ln P(d−1)/P(d−21). Neither reads the session being classified.


**Terciles of trailing 20-session realised volatility** — cut points 0.005946 and 0.006921

| tercile | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|
| T1 | 45 | 34 | 79 | 22 | -39.449 | [-67.643, -9.809] | [-61.614, -16.115] |
| T2 | 42 | 31 | 73 | 22 | -13.529 | [-39.586, +12.745] | [-38.622, +11.552] |
| T3 | 52 | 26 | 78 | 19 | -81.486 | [-133.405, -34.824] | [-132.089, -31.992] |

**Terciles of trailing 20-session return** — cut points -0.000266 and 0.015791

| tercile | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|
| T1 | 48 | 31 | 79 | 28 | -66.680 | [-106.642, -24.516] | [-102.550, -29.971] |
| T2 | 46 | 29 | 75 | 30 | -22.725 | [-52.327, +8.088] | [-48.900, +1.602] |
| T3 | 45 | 31 | 76 | 26 | -45.241 | [-85.709, -9.666] | [-87.966, -13.895] |

## 4. Study B `rng_next`, Q1 and Q5 vs the other four   [exploratory]

Clocks 12:00:59 and 14:00:59. Quintiles of `dev` are cut within each slice. Session and week-block intervals side by side.


**With 2026-02-01..2026-03-30 removed**

| clock | subset | quintile | n | n comp | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|---|---|
| 12:00:59 | all | Q1 | 41 | 164 | 205 | 44 | +16.319 | [-3.275, +38.525] | [-5.527, +43.825] |
| 12:00:59 | all | Q5 | 41 | 164 | 205 | 44 | -10.509 | [-21.618, +0.347] | [-22.130, +1.267] |
| 14:00:59 | all | Q1 | 42 | 163 | 205 | 44 | +10.816 | [-7.287, +32.851] | [-8.865, +35.989] |
| 14:00:59 | all | Q5 | 41 | 164 | 205 | 44 | -13.269 | [-24.176, -1.742] | [-25.160, -0.929] |
| 12:00:59 | no-expiry | Q1 | 38 | 148 | 186 | 44 | +14.291 | [-4.421, +37.057] | [-8.274, +44.015] |
| 12:00:59 | no-expiry | Q5 | 37 | 149 | 186 | 44 | -7.295 | [-18.149, +3.817] | [-19.761, +4.801] |
| 14:00:59 | no-expiry | Q1 | 38 | 148 | 186 | 44 | +13.484 | [-6.363, +36.434] | [-8.517, +41.266] |
| 14:00:59 | no-expiry | Q5 | 38 | 148 | 186 | 44 | -8.969 | [-21.024, +2.311] | [-21.957, +4.599] |

**Within terciles of trailing 20-session realised volatility (prior close only)**

| clock | subset | vol tercile | quintile | n | n comp | sessions | weeks | effect (bp) | session CI | week-block CI |
|---|---|---|---|---|---|---|---|---|---|---|
| 12:00:59 | all | T1 | Q1 | 16 | 62 | 78 | 22 | -2.323 | [-17.136, +12.778] | [-17.436, +14.088] |
| 12:00:59 | all | T1 | Q5 | 16 | 62 | 78 | 22 | -0.486 | [-15.422, +14.600] | [-13.859, +13.355] |
| 12:00:59 | all | T2 | Q1 | 16 | 62 | 78 | 23 | +1.385 | [-14.877, +19.840] | [-12.585, +31.536] |
| 12:00:59 | all | T2 | Q5 | 16 | 62 | 78 | 23 | -0.090 | [-12.239, +11.445] | [-13.895, +12.925] |
| 12:00:59 | all | T3 | Q1 | 16 | 61 | 77 | 18 | +8.474 | [-26.229, +47.577] | [-30.041, +43.466] |
| 12:00:59 | all | T3 | Q5 | 16 | 61 | 77 | 18 | -17.300 | [-42.238, +8.056] | [-39.647, +4.963] |
| 14:00:59 | all | T1 | Q1 | 16 | 63 | 79 | 22 | +2.135 | [-12.545, +17.240] | [-13.196, +19.235] |
| 14:00:59 | all | T1 | Q5 | 16 | 63 | 79 | 22 | -9.378 | [-25.165, +6.985] | [-28.094, +12.913] |
| 14:00:59 | all | T2 | Q1 | 16 | 61 | 77 | 22 | -2.775 | [-17.071, +14.407] | [-15.025, +25.824] |
| 14:00:59 | all | T2 | Q5 | 16 | 61 | 77 | 22 | +4.006 | [-7.782, +15.780] | [-8.476, +17.622] |
| 14:00:59 | all | T3 | Q1 | 16 | 61 | 77 | 18 | +28.312 | [-9.244, +67.034] | [-6.600, +63.505] |
| 14:00:59 | all | T3 | Q5 | 16 | 61 | 77 | 18 | -10.605 | [-33.814, +12.326] | [-30.709, +8.028] |
| 12:00:59 | no-expiry | T1 | Q1 | 15 | 56 | 71 | 22 | -1.461 | [-18.016, +14.552] | [-17.349, +16.678] |
| 12:00:59 | no-expiry | T1 | Q5 | 14 | 57 | 71 | 22 | +4.314 | [-11.327, +20.866] | [-6.983, +16.752] |
| 12:00:59 | no-expiry | T2 | Q1 | 14 | 56 | 70 | 22 | -1.167 | [-18.400, +19.694] | [-17.768, +34.545] |
| 12:00:59 | no-expiry | T2 | Q5 | 14 | 56 | 70 | 22 | +2.211 | [-10.864, +14.370] | [-12.579, +17.251] |
| 12:00:59 | no-expiry | T3 | Q1 | 15 | 56 | 71 | 18 | +15.240 | [-20.083, +51.825] | [-23.819, +51.495] |
| 12:00:59 | no-expiry | T3 | Q5 | 14 | 57 | 71 | 18 | -14.485 | [-40.826, +11.270] | [-38.201, +11.591] |
| 14:00:59 | no-expiry | T1 | Q1 | 15 | 56 | 71 | 22 | +2.785 | [-13.365, +19.259] | [-13.025, +20.990] |
| 14:00:59 | no-expiry | T1 | Q5 | 14 | 57 | 71 | 22 | -5.348 | [-21.376, +11.932] | [-25.939, +18.263] |
| 14:00:59 | no-expiry | T2 | Q1 | 15 | 55 | 70 | 22 | -1.132 | [-15.992, +17.555] | [-14.967, +32.127] |
| 14:00:59 | no-expiry | T2 | Q5 | 14 | 56 | 70 | 22 | +1.920 | [-9.910, +14.396] | [-12.367, +16.488] |
| 14:00:59 | no-expiry | T3 | Q1 | 15 | 56 | 71 | 18 | +20.174 | [-16.514, +58.383] | [-15.132, +47.701] |
| 14:00:59 | no-expiry | T3 | Q5 | 14 | 57 | 71 | 18 | -6.934 | [-32.681, +17.479] | [-30.988, +16.074] |

---

*Exploration. No verdict. Read-only; no database write, no commit.*
