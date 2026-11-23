## A3 — SENSEX 2026-11-19, every third market run — POST-HOC

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

