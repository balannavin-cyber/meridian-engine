# MR-PIN2 step 3 — gates G0 and G1

Pair set, **fixed here and reused unchanged in step 3**: front-expiry strikes within 1 % of spot (Part B B3 band and definition) carrying stored call gamma > 0 **and** put gamma > 0. Per-day median pools the day's three minutes' per-strike ratios into one list (conventions.md).

Solver: the backfill's own `implied_vol_vec` / `bs_gamma_vec`, extracted verbatim by `extract_bs_copy.py` into `bs_backfill_copy.py` — **not** `core/bs_engine.py`, which the backfill never calls.

## G0 — reproduce Part B from stored gamma

| sym | day | median stored | pairs | in band | Part B published | abs diff |
|---|---|---|---|---|---|---|
| NIFTY | 2025-04-01 | 0.8976 | 29 | NO | 0.8976 | 0.000030 |
| NIFTY | 2025-05-02 | 1.1066 | 29 | NO | 1.1066 | 0.000013 |
| NIFTY | 2025-06-02 | 0.9641 | 29 | YES | 0.9641 | 0.000044 |
| NIFTY | 2025-07-01 | 0.9428 | 30 | NO | 0.9428 | 0.000015 |
| NIFTY | 2025-08-01 | 1.0883 | 30 | NO | 1.0883 | 0.000020 |
| NIFTY | 2025-09-01 | 0.8817 | 24 | NO | 0.8817 | 0.000015 |
| NIFTY | 2025-10-01 | 0.9090 | 30 | NO | 0.9090 | 0.000019 |
| NIFTY | 2025-11-03 | 0.8116 | 28 | NO | 0.8116 | 0.000041 |
| NIFTY | 2025-12-01 | 0.9898 | 29 | YES | 0.9898 | 0.000037 |
| NIFTY | 2026-01-01 | 1.0427 | 32 | YES | 1.0427 | 0.000035 |
| NIFTY | 2026-02-01 | 1.0203 | 30 | YES | 1.0203 | 0.000021 |
| NIFTY | 2026-03-04 | 1.0094 | 30 | YES | 1.0094 | 0.000026 |
| SENSEX | 2025-04-02 | 0.9819 | 44 | YES | 0.9819 | 0.000046 |
| SENSEX | 2025-05-02 | 1.1340 | 48 | NO | 1.1340 | 0.000047 |
| SENSEX | 2025-06-02 | 1.0030 | 49 | YES | 1.0030 | 0.000010 |
| SENSEX | 2025-07-02 | 1.0613 | 49 | NO | 1.0613 | 0.000027 |
| SENSEX | 2025-08-01 | 1.0830 | 48 | NO | 1.0830 | 0.000008 |
| SENSEX | 2025-09-01 | 0.8380 | 48 | NO | 0.8380 | 0.000025 |
| SENSEX | 2025-10-03 | 0.9564 | 48 | YES | 0.9564 | 0.000027 |
| SENSEX | 2025-11-03 | 0.7816 | 47 | NO | 0.7816 | 0.000050 |
| SENSEX | 2025-12-01 | 0.8966 | 52 | NO | 0.8966 | 0.000043 |
| SENSEX | 2026-01-02 | 0.9883 | 50 | YES | 0.9883 | 0.000007 |
| SENSEX | 2026-02-01 | 1.0025 | 48 | YES | 1.0025 | 0.000008 |
| SENSEX | 2026-03-02 | 0.9827 | 48 | YES | 0.9827 | 0.000037 |

**G0 PASS NIFTY** — in-band 5 of 12, Part B 5 of 12; per-day medians off the published value by > 1e-4: 0.
**G0 PASS SENSEX** — in-band 6 of 12, Part B 6 of 12; per-day medians off the published value by > 1e-4: 0.

## G1 — replicate the stored solve at r = 0.065

| sym | legs | inside tol | share | γ miss p50 | p90 | max | IV miss (vp) p50 | p90 | max | solver fail |
|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 700 | 700 | 100.000 % | 0.00e+00 | 0.00e+00 | 4.44e-16 | 2.36e-05 | 4.38e-05 | 4.98e-05 | 0 |
| SENSEX | 1158 | 1158 | 100.000 % | 0.00e+00 | 0.00e+00 | 4.44e-16 | 2.64e-05 | 4.59e-05 | 5.00e-05 | 0 |

| sym | day | median stored | median re-solved | abs diff | within 0.005 |
|---|---|---|---|---|---|
| NIFTY | 2025-04-01 | 0.897570 | 0.897570 | 0.00e+00 | YES |
| NIFTY | 2025-05-02 | 1.106587 | 1.106587 | 0.00e+00 | YES |
| NIFTY | 2025-06-02 | 0.964144 | 0.964144 | 0.00e+00 | YES |
| NIFTY | 2025-07-01 | 0.942785 | 0.942785 | 0.00e+00 | YES |
| NIFTY | 2025-08-01 | 1.088320 | 1.088320 | 0.00e+00 | YES |
| NIFTY | 2025-09-01 | 0.881685 | 0.881685 | 0.00e+00 | YES |
| NIFTY | 2025-10-01 | 0.908981 | 0.908981 | 0.00e+00 | YES |
| NIFTY | 2025-11-03 | 0.811641 | 0.811641 | 0.00e+00 | YES |
| NIFTY | 2025-12-01 | 0.989763 | 0.989763 | 0.00e+00 | YES |
| NIFTY | 2026-01-01 | 1.042665 | 1.042665 | 0.00e+00 | YES |
| NIFTY | 2026-02-01 | 1.020279 | 1.020279 | 0.00e+00 | YES |
| NIFTY | 2026-03-04 | 1.009374 | 1.009374 | 0.00e+00 | YES |
| SENSEX | 2025-04-02 | 0.981946 | 0.981946 | 0.00e+00 | YES |
| SENSEX | 2025-05-02 | 1.134047 | 1.134047 | 0.00e+00 | YES |
| SENSEX | 2025-06-02 | 1.003010 | 1.003010 | 0.00e+00 | YES |
| SENSEX | 2025-07-02 | 1.061327 | 1.061327 | 0.00e+00 | YES |
| SENSEX | 2025-08-01 | 1.082992 | 1.082992 | 0.00e+00 | YES |
| SENSEX | 2025-09-01 | 0.837975 | 0.837975 | 0.00e+00 | YES |
| SENSEX | 2025-10-03 | 0.956373 | 0.956373 | 0.00e+00 | YES |
| SENSEX | 2025-11-03 | 0.781650 | 0.781650 | 0.00e+00 | YES |
| SENSEX | 2025-12-01 | 0.896643 | 0.896643 | 0.00e+00 | YES |
| SENSEX | 2026-01-02 | 0.988307 | 0.988307 | 1.11e-16 | YES |
| SENSEX | 2026-02-01 | 1.002492 | 1.002492 | 0.00e+00 | YES |
| SENSEX | 2026-03-02 | 0.982663 | 0.982663 | 0.00e+00 | YES |

### IV_TOL noise floor (conventions.md)

`100 * IV_TOL / vega` in vol points, every pair-set leg at r = 0.065. No figure is asserted a priori; these are measured.

| sym | legs | vp p50 | vp p90 | vp max | returned on budget, not tolerance |
|---|---|---|---|---|---|
| NIFTY | 700 | 0.0001 | 0.0002 | 0.0008 | 0 of 700 |
| SENSEX | 1158 | 0.0000 | 0.0001 | 0.0001 | 0 of 1158 |

**G1 PASS NIFTY** — (a) 100.000 % of legs inside |Δγ/γ| ≤ 0.005 and |ΔIV| ≤ 0.05 vol points (need ≥ 99 %); (b) all 12 per-day medians within 0.005: yes.
**G1 PASS SENSEX** — (a) 100.000 % of legs inside |Δγ/γ| ≤ 0.005 and |ΔIV| ≤ 0.05 vol points (need ≥ 99 %); (b) all 12 per-day medians within 0.005: yes.

**Gate outcome: G0 PASS, G1 PASS.** Step 3 proceeds.
