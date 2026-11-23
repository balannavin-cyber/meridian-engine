<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/order_check_rev3/results.md -->

# Order check on revision 3 of v_gex_strike_rank_gross - RESULT

Design frozen in `PREREG.md` sha256 `da7440d119945e236136296b2db2a3f0ca86149ecefdfcaf01a668363a1fced7`. Self-test 38/38 with all three named mutants making a clause FAIL, run before any live read. One look; no clause added, relaxed or reordered after the data was seen.

## Pre-data clarification and stated limits

**Ranking condition `gross_cr > 0`.** Operator ruling 2026-11-23 20:00 IST, made AFTER the NIFTY view EXPLAIN gate and BEFORE any data read. Basis: the pin lane's own revision-2 draft `2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql` (`WHERE gross_cr > 0`), which is where `n_ranked` was defined. PREREG left the zero-gross case unstated, so this is a clarification and not a relaxation: an in-set strike carrying a gamma but zero total OI has `gross_cr = 0` and is NOT ranked. Only the ranking condition in `indep.measure()` changed. One in-set fixture strike with gamma > 0 and zero OI on both legs was added to exercise that condition, the hand expectations were recomputed, and the full self-test was re-run: **38/38**, with all three named mutants still each making at least one clause FAIL.

**Stated limits.**

1. The fixture tests the independent Python and the clause evaluator. It does NOT test the view.
2. The live view is identified by `pg_get_viewdef` length **5281** and md5 **aa4946064341c1d1ae835819d8cba858**. File-to-live identity against `sql/2026-11-23_s107_v_gex_strike_rank_gross.sql` was NOT established -- the engine tree was out of scope for this task -- so CLAUDE.md Rule 25 is unsatisfied and nothing here claims the object checked is that file.

## The frozen runs

| symbol | expiry | run_id | ts IST | dte | view spot | chain spot_min | spot_max | distinct spot | chain legs |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-11-23 | `85ba488d-7bd2-4333-af0c-03591f902694` | 2026-11-23 15:40:06 | 0 | 25349.65 | 25349.65 | 25349.65 | 1 | 564 |
| SENSEX | 2026-11-26 | `d875b416-7b1d-4e34-bfc4-0ba077ac1af2` | 2026-11-23 15:40:06 | 3 | 82435.99 | 82435.99 | 82435.99 | 1 | 528 |

**Condition 1, run_id re-read after the independent read:** NIFTY ROWS=1 returned=`85ba488d-7bd2-4333-af0c-03591f902694` frozen=`85ba488d-7bd2-4333-af0c-03591f902694` -> PASS · SENSEX ROWS=1 returned=`d875b416-7b1d-4e34-bfc4-0ba077ac1af2` frozen=`d875b416-7b1d-4e34-bfc4-0ba077ac1af2` -> PASS. Neither symbol's latest run_id moved between the view read and the leg read, so no run was discarded and no redo was needed.

## Per symbol and expiry

| symbol | expiry | rows compared | legs rows | gross rows | clause 1 | clause 2 | clause 3 | max rel gross diff |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-11-23 | 10 | 48 | 48 | PASS | PASS | PASS | 4.04258e-15 |
| SENSEX | 2026-11-26 | 10 | 82 | 82 | PASS | PASS | PASS | 3.93386e-15 |

Clause 4 (same set of (symbol, expiry) pairs): **PASS** - view [('NIFTY', '2026-11-23'), ('SENSEX', '2026-11-26')], independent [('NIFTY', '2026-11-23'), ('SENSEX', '2026-11-26')].

## The three counts, view vs independent

| symbol | expiry | n_ranked V | n_ranked I | n_in_set V | n_in_set I | n_oi_no_gamma V | n_oi_no_gamma I | equal |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-11-23 | 48 | 48 | 51 | 51 | 3 | 3 | yes |
| SENSEX | 2026-11-26 | 82 | 82 | 82 | 82 | 0 | 0 | yes |

## lead_rel

Tolerance 1e-09 relative, fixed by PREREG.

| symbol | expiry | lead_rel view | lead_rel independent | rel diff | clause 3 |
|---|---|---|---|---|---|
| NIFTY | 2026-11-23 | 0.978822477103292 | 0.978822477103292 | 0 | PASS |
| SENSEX | 2026-11-26 | 0.131689459283006 | 0.1316894592830062 | 1.68612e-15 | PASS |

## Ranked sequence, rank 1..10

**NIFTY 2026-11-23** - clause 1 PASS

```
view        [25350, 25400, 25300, 25500, 25450, 25550, 25600, 25250, 25650, 25200]
independent [25350, 25400, 25300, 25500, 25450, 25550, 25600, 25250, 25650, 25200]
```

**SENSEX 2026-11-26** - clause 1 PASS

```
view        [83000, 82500, 83500, 84000, 82000, 81500, 82700, 82800, 81000, 84500]
independent [83000, 82500, 83500, 84000, 82000, 81500, 82700, 82800, 81000, 84500]
```

## Were the new columns exercised by live data?

| symbol | expiry | call_only | put_only | n_oi_no_gamma | n_gamma_zero_oi (indep) |
|---|---|---|---|---|---|
| NIFTY | 2026-11-23 | 2 | 20 | 3 | 0 |
| SENSEX | 2026-11-26 | 2 | 15 | 0 | 0 |

Per column:

- `gamma_legs`: **exercised** - `call_only + put_only = 39` across the two symbols (4 call_only, 35 put_only). Clause 2 is claimed for it.
- `n_oi_no_gamma`: **exercised** - greater than zero on at least one symbol (maximum 3). Clause 2 is claimed for it.

## Verdict

- clause1: **PASS**
- clause2: **PASS**
- clause3: **PASS**
- clause4: **PASS**

**OVERALL: PASS**

