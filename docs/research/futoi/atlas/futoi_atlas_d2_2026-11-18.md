# Atlas Study D2 — OI at the wall strike, band 0.15 %

Exploration. No verdict. Nothing here is a finding until confirmed once on unseen data.

D2 was absent from the main atlas document, which carries D1 only. This file adds it for band 0.15 % alone. The extraction ran **one query per approach leg** against `hist_option_bars_1m`, each scoped to one `trade_date`, one expiry, one strike, one option type and the window (approach_min − 30, approach_min]; `sql/extract_wall_oi_d2.sql`. 79 legs queried, 0 failed, 0 timeouts.

Approaches before **09:45:59** are reported as **OPEN** and measured from the prior session's close, because a 30-minute pre-approach window would reach before the session start. Approaches at or after 09:45:59 are **INTRADAY**, measured over the 30 minutes before. The two are never pooled.

| Field | Value |
|---|---|
| Approach legs in the band | 79 |
| OPEN (before 09:45:59) | 45 |
| INTRADAY (09:45:59 or later) | 34 |
| Legs with bars < 25 | 41 — flagged, kept |
| Edge-flagged legs | 0 |
| Legs on an expiry-flagged session | 9 |
| Intervals | session-clustered percentile bootstrap, 2000 resamples, seed 20261118. **Descriptive** |

---

### D2 · band 0.15 % · OPEN · futures series dF   [exploratory]

| denominator | n |
|---|---|
| approaches in the band, OPEN | 45 |
| carrying a futures-OI value and a wall-OI change | 45 |

Both OI changes run from the **prior session's close** to the approach minute. No new query was needed.


**Put walls** — 28 approaches over 28 sessions.

| wall-strike OI | dF | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 4 | 4 | 0.750 |
| rising | falling | 17 | 17 | 0.412 |
| falling | rising | 0 | 0 | — |
| falling | falling | 7 | 7 | 0.429 |

Difference, **wall-strike OI rising minus falling**: **+0.048** 95% CI [-0.391, +0.476] (2000 resamples, seed 20261118, 21 clusters). Levels 0.476 (rising, n=21) vs 0.429 (falling, n=7) — levels, not effects.


**Call walls** — 17 approaches over 17 sessions.

| wall-strike OI | dF | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 0 | 0 | — |
| rising | falling | 10 | 10 | 0.400 |
| falling | rising | 0 | 0 | — |
| falling | falling | 7 | 7 | 0.429 |

Difference, **wall-strike OI rising minus falling**: **-0.029** 95% CI [-0.528, +0.457] (2000 resamples, seed 20261118, 10 clusters). Levels 0.400 (rising, n=10) vs 0.429 (falling, n=7) — levels, not effects.


### D2 · band 0.15 % · OPEN · futures series dF1   [exploratory]

| denominator | n |
|---|---|
| approaches in the band, OPEN | 45 |
| carrying a futures-OI value and a wall-OI change | 45 |

Both OI changes run from the **prior session's close** to the approach minute. No new query was needed.


**Put walls** — 28 approaches over 28 sessions.

| wall-strike OI | dF1 | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 5 | 5 | 0.600 |
| rising | falling | 16 | 16 | 0.438 |
| falling | rising | 0 | 0 | — |
| falling | falling | 7 | 7 | 0.429 |

Difference, **wall-strike OI rising minus falling**: **+0.048** 95% CI [-0.391, +0.476] (2000 resamples, seed 20261118, 21 clusters). Levels 0.476 (rising, n=21) vs 0.429 (falling, n=7) — levels, not effects.


**Call walls** — 17 approaches over 17 sessions.

| wall-strike OI | dF1 | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 2 | 2 | 1.000 |
| rising | falling | 8 | 8 | 0.250 |
| falling | rising | 0 | 0 | — |
| falling | falling | 7 | 7 | 0.429 |

Difference, **wall-strike OI rising minus falling**: **-0.029** 95% CI [-0.528, +0.457] (2000 resamples, seed 20261118, 10 clusters). Levels 0.400 (rising, n=10) vs 0.429 (falling, n=7) — levels, not effects.


### D2 · band 0.15 % · INTRADAY · futures series dF   [exploratory]

| denominator | n |
|---|---|
| approaches in the band, INTRADAY | 34 |
| carrying a futures-OI value and a wall-OI change | 24 |
| dropped — no dF value | 10 |
| legs with bars < 25 among those used | 0 — flagged, kept |

Both OI changes run over the **30 minutes before** the approach minute.


**Put walls** — 16 approaches over 16 sessions.

| wall-strike OI | dF | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 7 | 7 | 0.571 |
| rising | falling | 0 | 0 | — |
| falling | rising | 7 | 7 | 0.000 |
| falling | falling | 2 | 2 | 0.000 |

Difference, **wall-strike OI rising minus falling**: **+0.571** 95% CI [+0.200, +1.000] (2000 resamples, seed 20261118, 7 clusters). Levels 0.571 (rising, n=7) vs 0.000 (falling, n=9) — levels, not effects.


**Call walls** — 8 approaches over 8 sessions.

| wall-strike OI | dF | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 1 | 1 | 0.000 |
| rising | falling | 2 | 2 | 0.000 |
| falling | rising | 2 | 2 | 0.500 |
| falling | falling | 3 | 3 | 0.333 |

Difference, **wall-strike OI rising minus falling**: **-0.400** 95% CI [-0.857, +0.000] (2000 resamples, seed 20261118, 3 clusters). Levels 0.000 (rising, n=3) vs 0.400 (falling, n=5) — levels, not effects.


### D2 · band 0.15 % · INTRADAY · futures series dF1   [exploratory]

| denominator | n |
|---|---|
| approaches in the band, INTRADAY | 34 |
| carrying a futures-OI value and a wall-OI change | 34 |
| legs with bars < 25 among those used | 0 — flagged, kept |

Both OI changes run over the **30 minutes before** the approach minute.


**Put walls** — 24 approaches over 24 sessions.

| wall-strike OI | dF1 | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 10 | 10 | 0.600 |
| rising | falling | 4 | 4 | 0.500 |
| falling | rising | 6 | 6 | 0.000 |
| falling | falling | 3 | 3 | 0.000 |

Difference, **wall-strike OI rising minus falling**: **+0.571** 95% CI [+0.300, +0.833] (2000 resamples, seed 20261118, 14 clusters). Levels 0.571 (rising, n=14) vs 0.000 (falling, n=10) — levels, not effects.


**Call walls** — 10 approaches over 10 sessions.

| wall-strike OI | dF1 | n approaches | n sessions | break rate |
|---|---|---|---|---|
| rising | rising | 3 | 3 | 0.333 |
| rising | falling | 2 | 2 | 0.000 |
| falling | rising | 1 | 1 | 0.000 |
| falling | falling | 4 | 4 | 0.500 |

Difference, **wall-strike OI rising minus falling**: **-0.200** 95% CI [-0.751, +0.400] (2000 resamples, seed 20261118, 5 clusters). Levels 0.200 (rising, n=5) vs 0.400 (falling, n=5) — levels, not effects.


---

*Exploration. No verdict. Read-only; the only database access was the 79-leg extraction. No new query was made for the OPEN regime.*
