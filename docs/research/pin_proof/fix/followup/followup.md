<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/followup/followup.md -->

# VS follow-up — POST-HOC diagnostics

**POST-HOC. Not frozen measures, no pass marks.** Source: `fix/replay_v2/runs.csv` (9,719 runs) and the chain pulls under `fix/replay_v2/chain/`. Market runs are 09:15–15:29 IST unless stated. Steps: NIFTY 50, SENSEX 100.

## A1 — expiry days (dte_cal = 0) — POST-HOC

| symbol | date | SEEN | mkt runs | clear-lead | VS=K clear | V2=K clear | VS=K all valid | med abs(VS−S) | med abs(B−S) | B present |
|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-09-01 | UNSEEN | 74 | 62 | 100.0% (62/62) | 98.4% (61/62) | 98.6% (73/74) | 0.36 | - | 0/74 |
| NIFTY | 2026-09-08 | UNSEEN | 74 | 70 | 100.0% (70/70) | 98.6% (69/70) | 97.3% (72/74) | 0.44 | - | 0/74 |
| NIFTY | 2026-09-15 | UNSEEN | 74 | 58 | 100.0% (58/58) | 96.6% (56/58) | 98.6% (73/74) | 0.66 | - | 0/74 |
| NIFTY | 2026-09-22 | UNSEEN | 66 | 61 | 98.4% (60/61) | 98.4% (60/61) | 97.0% (64/66) | 0.41 | - | 0/66 |
| NIFTY | 2026-09-29 | UNSEEN | 74 | 70 | 100.0% (70/70) | 100.0% (70/70) | 100.0% (74/74) | 0.49 | - | 0/74 |
| NIFTY | 2026-10-06 | UNSEEN | 74 | 65 | 100.0% (65/65) | 100.0% (65/65) | 95.9% (71/74) | 0.28 | 1.62 | 58/74 |
| NIFTY | 2026-10-13 | UNSEEN | 74 | 63 | 100.0% (63/63) | 98.4% (62/63) | 98.6% (73/74) | 0.33 | 1.10 | 74/74 |
| NIFTY | 2026-10-19 | UNSEEN | 74 | 67 | 98.5% (66/67) | 97.0% (65/67) | 97.3% (72/74) | 0.61 | 1.52 | 74/74 |
| NIFTY | 2026-10-27 | UNSEEN | 75 | 63 | 92.1% (58/63) | 90.5% (57/63) | 93.3% (70/75) | 0.61 | 1.25 | 75/75 |
| NIFTY | 2026-11-03 | UNSEEN | 75 | 69 | 98.6% (68/69) | 95.7% (66/69) | 98.7% (74/75) | 0.49 | 1.31 | 75/75 |
| NIFTY | 2026-11-09 | UNSEEN | 75 | 65 | 100.0% (65/65) | 100.0% (65/65) | 100.0% (75/75) | 0.42 | 1.81 | 75/75 |
| NIFTY | 2026-11-17 | SEEN | 75 | 63 | 96.8% (61/63) | 96.8% (61/63) | 94.7% (71/75) | 0.45 | 1.33 | 75/75 |
| **NIFTY** | **pooled** | — | **884** | **776** | **98.7% (766/776)** | **97.6% (757/776)** | **97.5% (862/884)** | **0.45** | **1.44** | **506/884** |
| SENSEX | 2026-08-27 | UNSEEN | 74 | 46 | 87.0% (40/46) | 63.0% (29/46) | 81.1% (60/74) | 0.71 | - | 0/74 |
| SENSEX | 2026-09-03 | UNSEEN | 74 | 53 | 100.0% (53/53) | 98.1% (52/53) | 94.6% (70/74) | 0.83 | - | 0/74 |
| SENSEX | 2026-09-10 | UNSEEN | 74 | 67 | 100.0% (67/67) | 100.0% (67/67) | 98.6% (73/74) | 0.52 | - | 0/74 |
| SENSEX | 2026-09-17 | UNSEEN | 74 | 57 | 100.0% (57/57) | 100.0% (57/57) | 97.3% (72/74) | 0.46 | - | 0/74 |
| SENSEX | 2026-09-24 | UNSEEN | 74 | 68 | 98.5% (67/68) | 97.1% (66/68) | 97.3% (72/74) | 0.78 | - | 0/74 |
| SENSEX | 2026-10-01 | UNSEEN | 74 | 57 | 100.0% (57/57) | 100.0% (57/57) | 97.3% (72/74) | 0.78 | - | 0/74 |
| SENSEX | 2026-10-08 | UNSEEN | 74 | 51 | 100.0% (51/51) | 100.0% (51/51) | 93.2% (69/74) | 0.70 | 2.33 | 74/74 |
| SENSEX | 2026-10-15 | UNSEEN | 73 | 53 | 100.0% (53/53) | 100.0% (53/53) | 98.6% (72/73) | 0.77 | 2.22 | 73/73 |
| SENSEX | 2026-10-22 | UNSEEN | 73 | 64 | 98.4% (63/64) | 98.4% (63/64) | 98.6% (72/73) | 1.09 | 2.42 | 73/73 |
| SENSEX | 2026-10-29 | UNSEEN | 75 | 46 | 100.0% (46/46) | 100.0% (46/46) | 97.3% (73/75) | 0.67 | 1.97 | 75/75 |
| SENSEX | 2026-11-05 | UNSEEN | 75 | 56 | 100.0% (56/56) | 92.9% (52/56) | 100.0% (75/75) | 1.25 | 1.72 | 75/75 |
| SENSEX | 2026-11-12 | UNSEEN | 75 | 69 | 100.0% (69/69) | 100.0% (69/69) | 100.0% (75/75) | 0.81 | 3.02 | 75/75 |
| SENSEX | 2026-11-19 | SEEN | 75 | 59 | 100.0% (59/59) | 98.3% (58/59) | 98.7% (74/75) | 0.60 | 2.35 | 75/75 |
| **SENSEX** | **pooled** | — | **964** | **746** | **98.9% (738/746)** | **96.5% (720/746)** | **96.4% (929/964)** | **0.73** | **2.27** | **520/964** |

## A2 — near-ties (K lead < 5 %), all 58 days — POST-HOC

| symbol | runs | VS = K | abs(VS−K) ≤1 step | ≤2 steps | median | max |
|---|---|---|---|---|---|---|
| NIFTY | 585 | 87.9% (514/585) | 89.4% (523/585) | 97.8% (572/585) | 0.00 | 8.00 |
| SENSEX | 576 | 91.1% (525/576) | 94.1% (542/576) | 96.0% (553/576) | 0.00 | 10.00 |

VS's strike ranked by **K's own score**, on the same near-tie runs (compute_run re-run from the chain pulls, one symbol-day at a time):

| symbol | near-tie runs | VS is K's 1st | K's 2nd | 1st or 2nd | lower | not scored |
|---|---|---|---|---|---|---|
| NIFTY | 585 | 87.9% (514/585) | 12.0% (70/585) | 99.8% (584/585) | 0.2% (1/585) | 0 |
| SENSEX | 576 | 91.1% (525/576) | 8.5% (49/576) | 99.7% (574/576) | 0.3% (2/576) | 0 |

## A4 — symbol-days where VS misses either day mark — POST-HOC

Marks: 95 % of clear-lead runs, 85 % of all valid market runs.

| symbol | date | SEEN | dte@open | mkt | clear-lead | VS clear | VS all | V2 clear | F clear | med R | med BL | med FB | frozen | med abs(VS−K) where differ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-08-27 | UNSEEN | 5 | 74 | 36 | 100.0% | 83.8% | 94.4% | 80.6% | 0.7958 | 0.0167 | 1.25 | 0 | 2.0 |
| NIFTY | 2026-09-28 | UNSEEN | 1 | 74 | 38 | 89.5% | 66.2% | 86.8% | 97.4% | 0.7353 | 0.0667 | 0.80 | 0 | 2.0 |
| NIFTY | 2026-10-27 | UNSEEN | 0 | 75 | 63 | 92.1% | 93.3% | 90.5% | 90.5% | 1.0088 | 0.0095 | 0.02 | 0 | 1.0 |
| SENSEX | 2026-08-26 | UNSEEN | 1 | 74 | 74 | 64.9% | 64.9% | 64.9% | 97.3% | 0.7363 | 0.0116 | 1.16 | 0 | 2.0 |
| SENSEX | 2026-08-27 | UNSEEN | 0 | 74 | 46 | 87.0% | 81.1% | 63.0% | 78.3% | 0.9323 | 0.0196 | 0.51 | 0 | 1.0 |

Symbol-days missing at least one VS mark: NIFTY 3 of 58, SENSEX 2 of 58.


Market runs that day: 75. Stored pin-band rows matched by run_id: **0** (see B3). The band_lo / band_hi columns are therefore shown as `-` on every row; they are NOT reconstructed.

`X` marks a pin outside the stored corridor [put wall, call wall].

| ts IST | S | B | X | V2 | VS | X | K | K lead | put wall | call wall | band_lo | band_hi | frozen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 | 81949.55 | 82500 |   | 82000 | 82000 |   | 82000 | 0.4771 | 81000 | 83500 | - | - | N |
| 09:30 | 81700.62 | 81500 |   | 82000 | 82000 |   | 82000 | 0.2710 | 81000 | 82500 | - | - | N |
| 09:45 | 82052.42 | 82500 |   | 82000 | 82000 |   | 82000 | 0.4178 | 81500 | 82500 | - | - | N |
| 10:00 | 82250.77 | 82500 |   | 82000 | 82000 |   | 82000 | 0.2249 | 81000 | 83500 | - | - | Y |
| 10:15 | 82230.53 | 82000 |   | 82200 | 82200 |   | 82200 | 0.0215 | 81500 | 83000 | - | - | N |
| 10:30 | 82115.07 | 82000 |   | 82200 | 82200 |   | 82200 | 0.0007 | 81500 | 82500 | - | - | N |
| 10:45 | 82205.00 | 82500 |   | 82000 | 82000 |   | 82000 | 0.2805 | 81000 | 83000 | - | - | Y |
| 11:00 | 82223.34 | 82500 |   | 82000 | 82000 |   | 82000 | 0.2347 | 82000 | 83000 | - | - | Y |
| 11:15 | 82265.18 | 82500 |   | 82000 | 82000 |   | 82000 | 0.1792 | 82000 | 83000 | - | - | Y |
| 11:30 | 82314.71 | 82500 |   | 82000 | 82000 |   | 82000 | 0.0271 | 82000 | 83000 | - | - | Y |
| 11:45 | 82359.79 | 82000 |   | 82300 | 82300 |   | 82300 | 0.1727 | 82000 | 82500 | - | - | N |
| 12:00 | 82491.94 | 82500 |   | 82500 | 82500 |   | 82500 | 0.4021 | 82000 | 83500 | - | - | Y |
| 12:15 | 82462.16 | 82000 |   | 82500 | 82500 |   | 82500 | 0.0713 | 82000 | 82500 | - | - | N |
| 12:30 | 82476.21 | 82500 |   | 82500 | 82500 |   | 82500 | 0.3917 | 82000 | 83500 | - | - | Y |
| 12:45 | 82485.65 | 82500 |   | 82500 | 82500 |   | 82500 | 0.4263 | 82000 | 83500 | - | - | Y |
| 13:00 | 82522.61 | 82000 |   | 82500 | 82500 |   | 82500 | 0.3017 | 82000 | 83000 | - | - | N |
| 13:15 | 82457.77 | 82000 |   | 82500 | 82500 |   | 82500 | 0.2195 | 82000 | 83000 | - | - | N |
| 13:30 | 82508.58 | 82300 |   | 82500 | 82500 |   | 82500 | 0.2808 | 82000 | 83000 | - | - | N |
| 13:45 | 82569.56 | 82400 |   | 82500 | 82500 |   | 82500 | 0.2735 | 82000 | 83000 | - | - | N |
| 14:00 | 82576.14 | 82500 |   | 82500 | 82500 |   | 82500 | 0.1276 | 82000 | 83000 | - | - | N |
| 14:15 | 82743.48 | 82500 |   | 82700 | 82700 |   | 82700 | 0.1787 | 82500 | 83000 | - | - | N |
| 14:30 | 82847.57 | 82700 |   | 82800 | 83000 |   | 83000 | 0.0725 | 82500 | 83000 | - | - | N |
| 14:45 | 82832.24 | 83000 |   | 82800 | 82800 |   | 83000 | 0.0069 | 82500 | 83000 | - | - | N |
| 15:00 | 82831.80 | 83000 |   | 82800 | 82800 |   | 82800 | 0.1613 | 82600 | 83000 | - | - | N |
| 15:15 | 82960.86 | 83100 | X | 83000 | 83000 |   | 83000 | 0.2215 | 82500 | 83000 | - | - | N |

Counts over ALL market runs of SENSEX 2026-11-19:

| quantity | value |
|---|---|
| B outside [put wall, call wall] | 2.7% (2/75) |
| VS outside [put wall, call wall] | 0.0% (0/75) |
| K outside [put wall, call wall] | 0.0% (0/75) |
| frozen runs | 22.7% (17/75) |
| pin changes, B | 32 (over 75 runs) |
| pin changes, VS | 19 (over 75 runs) |
| pin changes, K | 19 (over 75 runs) |

## B — the pin band — POST-HOC

**B1. Definition.** `public.v_gex_strike_pin_zone`, defined in `~/meridian-engine/sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql:30` (`CREATE OR REPLACE VIEW`, file is 125 lines). The band-deciding lines are the `peak` CTE (`:74-82`), the recursive `walk` CTE (`:83-112`) and the final aggregate (`:113-124`):

```sql
 77:            scoped.strike AS peak_strike,
 78:            scoped.gex_cr AS peak_gex_cr,
 79:            COALESCE(get_parameter_num('pin.tau.'::text || scoped.symbol), 0.3) AS tau
 80:           FROM scoped
 81:          WHERE scoped.gex_cr > 0::numeric
 82:          ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr DESC, (abs(scoped.strike - scoped.spot))
 83:        ), walk AS (
 88:            p.peak_strike AS strike,
 96:         SELECT g.run_id,
105:                CASE
106:                    WHEN g.strike < w_1.strike THEN '-1'::integer
107:                    ELSE 1
108:                END AS direction
109:           FROM walk w_1
110:             JOIN scoped g ON ... AND ((w_1.direction = ANY (ARRAY[0, -1])) AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001
110:                                   OR (w_1.direction = ANY (ARRAY[0, 1]))  AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001)
112:          WHERE g.gex_cr > 0::numeric AND g.gex_cr >= (w_1.tau * w_1.peak_gex_cr)
118:    min(strike) AS pin_lower,
119:    max(strike) AS pin_upper,
120:    count(*) AS n_strikes,
123:    (array_agg(strike ORDER BY gex_cr DESC))[1] AS peak_pin_strike,
124:    max(tau) AS tau_used
```

It walks on **`gex_cr` SIGN-FILTERED to positive only** — `WHERE scoped.gex_cr > 0` both at the peak (`:81`) and at every walk step (`:112`), so a negative-`gex_cr` strike stops the walk and can never be inside the band.

**tau** is the walk's stopping fraction of the peak: a neighbouring strike joins the band only while `gex_cr >= tau * peak_gex_cr` (`:112`), with `tau = COALESCE(get_parameter_num('pin.tau.'||symbol), 0.3)` (`:79`) — i.e. 0.3 by default, per-symbol overridable, and reported back as `tau_used`.

**B2. Stored per run_id — YES, but not in `gex_cycle_history`.**

| table | columns matching band/zone/pin/lo/hi/low/high/peak |
|---|---|
| `gex_cycle_history` | `pin_leader_strike` (17), `gamma_at_pin` (18), `conc_hhi` (25), `pin_state` (27), `pin_state_reason` (28) — **no band low/high** |
| `gex_pin_maxpain_history` | `peak_pin_strike` (8), **`pin_lower` (9)**, **`pin_upper` (10)**, `pin_n_strikes` (11), `peak_pin_gex_cr` (12) |

Band low and high per run_id ARE stored, in **`public.gex_pin_maxpain_history`**, columns **`pin_lower`** and **`pin_upper`**, keyed `UNIQUE (symbol, run_id, expiry_date)` (`gex_pin_maxpain_history_symbol_run_id_expiry_date_key`).

**B3. Pulled, and the result is zero rows.**

| symbol-day | band rows returned |
|---|---|
| NIFTY 2026-11-16 | 0 |
| NIFTY 2026-11-17 | 0 |
| NIFTY 2026-11-18 | 0 |
| NIFTY 2026-11-19 | 0 |
| NIFTY 2026-11-20 | 0 |
| SENSEX 2026-11-16 | 0 |
| SENSEX 2026-11-17 | 0 |
| SENSEX 2026-11-18 | 0 |
| SENSEX 2026-11-19 | 0 |
| SENSEX 2026-11-20 | 0 |
| **all ten** | **0** |

All ten symbol-days returned **0 rows**, each query gated (Index Scan using `gex_pin_maxpain_history_symbol_run_id_expiry_date_key`, estimate 1 row, no Seq Scan), rc 0, empty stderr, 2.51–2.77 s. So the per-run-id join, the outside-band counts and the median band width asked for in B3 are **NOT COMPUTABLE** on these days, and the `band_lo` / `band_hi` columns in A3 are empty.

**The table is not empty overall, but its extent is UNMEASURED.** The only plan available for a whole-table `min(ts)/max(ts)` probe is a **Seq Scan on `gex_pin_maxpain_history`**, which the gate forbids, so that query was not run. The rejected plan's own row estimate was 11,808, which is a planner estimate and not a count; nothing here establishes which dates the table does cover.

