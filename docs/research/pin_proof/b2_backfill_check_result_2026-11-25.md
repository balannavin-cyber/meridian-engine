<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/b2_backfill_check_result_2026-11-25.md -->
# B2: independent check of the one-day V2 backfill, 2026-08-27 (MR-PIN3, Wed 2026-11-25, 19:50 IST): PASS

Step 7 of the tracker (Goal 2). Read with `v2_rule_conformance_result_v12_2026-11-25.md` and the engine's `engine_to_pin_LATEST.md` (19:45) sections 1 to 3.

## What was checked
The rows the engine's backfill wrote to `gex_strike_v2` and `gex_run_v2` for 2026-08-27 (B1: 166 runs, 23,323 strike rows, 0 input errors), against per-run aggregates the pin lane built from the fixture's stored rows with its own v1.2 implementation (`v2_indep.py`). Both symbols, 78 fixture runs each.

## Pass criteria
Fixed in the chat before the database output was seen (message of 19:48 IST); not frozen as a file. Counts and OI totals exact; sums to nine significant figures (limit 1e-9 relative); every row stamped `v2-1.2-gss`; all 156 fixture runs present; runs not in the fixture listed, not compared.

## Result
| Item | Result |
|---|---|
| Runs returned by the database read | 166 (83 NIFTY, 83 SENSEX), no repeated `run_id` |
| Fixture runs compared | 156 of 156 |
| Counts (rows, in map, in band, both, call only, put only, `n_map`, `n_zero`) | Exact on all 156 |
| OI totals, calls and puts | Exact on all 156 |
| Largest relative difference in any sum | 4.513e-13 |
| Stamps | `v2-1.2-gss` on every strike row and run row |
| Runs in the database and not in the fixture | 10 (08:35 to 08:55 IST, five per symbol); listed, not compared |

## Limits
- A totals check: per-run totals, including strike-weighted ones, not each strike row. A wrong row would have to leave ten totals unchanged to pass.
- The 10 early runs are covered only by the engine's own V1 recompute from the chain, not by the pin lane.
- One day. Input errors (d) and (e) on real data are not exercised.
- The database output came in two pastes because the SQL editor stops at 100 rows (NIFTY 83 + SENSEX 17, then SENSEX from 10:00 IST, 66 rows).

## Facts about the stored day (for step 9, the old-against-new comparison)
- Stored runs: 08:35 to 15:20 IST at five-minute steps, then 15:40. No run at 15:25, 15:30, 15:35 (this day only; other days not read).
- The fixture's 78 are 09:00 to 15:20 (77) plus 15:40. So the fixture includes 09:00, 09:05, 09:10 and the 15:40 run; the five it lacks are 08:35 to 08:55.
- Before 09:15 there are 8 runs per symbol, not 5.
- NIFTY call OI is 127,699,520 from the 08:50 run to the 09:15 run, then 138,681,660 at 09:20. SENSEX call OI 43,481,980 to 09:15, 59,048,200 at 09:20. OI is stale until the 09:20 run.
- 08:35, 08:40, 08:45 are identical in every figure on NIFTY and SENSEX.
- Ruling (operator accepted the pin lane's recommendation, 25 Nov): keep every stored run in the V2 tables; the step 9 comparison selects by clock time (main set 09:15 to 15:30 IST, boundary to be approved with its pre-registration) and reports the other runs separately.

## Files and hashes (pin lane workspace; git copy owed, `docs/research/pin_proof/v2_check_v12/`)
| File | sha256 |
|---|---|
| `b2_expected_2026-08-27.json` (expected per-run aggregates, 78 runs per symbol) | `d99aa037b56426a679192480aaf277950c409a736ca4beba115b1712df37dffa` |
| `b2_compare.py` | `a86405938dcaccc59fd5c3d98d48e03a93dc7b9e8fd468017b78d4dadd77aa30` |
| `b2_db_2026-08-27.json` (the two database pastes, merged) | `5bdcf8c8c2e729632d281c030f76653a6c47af75494ef5b9255b4bd182389159` |
| `b2_run_2026-11-25.log` | `29e9dad9c11d8d0ae0be03ad963ad5ebfa0735ed92b1df2630663295fce7cc67` |
