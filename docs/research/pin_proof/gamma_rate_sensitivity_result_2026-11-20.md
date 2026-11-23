# Gamma rate sensitivity: result (MR-PIN2 step 3, 2026-11-20)

**Design:** `claude/pin/gamma_rate_sensitivity_design_v2_FROZEN_2026-11-20.md`, sha256 a9d0b7c5c3dbfbd1739096a81c138cc7caefc5c094d454d28c3fd9d6ffad612e. **Run prompt:** `claude/pin/cc_prompt_gamma_rate_sensitivity_run.md`.
**Box output:** `~/meridian-cc/docs/research/pin_proof/gamma_inputs/sens/` (conventions.md, gates.md, results.md, per_minute.csv, per_day.csv, analyze_sens.py, bs_backfill_copy.py, extract_bs_copy.py, run_sens.sh, gate_explain.py, queries/, _qS_*.txt, _sens_run.log, _sens_run_analysis.log). Single run, rc = 0, 2026-11-20 ~17:16 IST. Not yet sealed (manifest rebuilt once at the end of MR-PIN2).
**Figures below are as printed by Claude Code on the box.**

## Verdicts (per symbol, design §7)

| | NIFTY | SENSEX |
|---|---|---|
| Verdict | **FAIL** | **FAIL** ("not shown with this futures source", design §10) |
| Verdict minutes | 36 of 36 | 26 of 36 (12 of 12 days kept a minute) |
| In band before → after (verdict minutes) | 5 → 5 of 12 | 7 → 9 of 12 |
| Out of band after vs allowance floor(2n/12) = 2 | 7 > 2 | 3 > 2 |
| Days that left the band | 1 (2026-01-01) | 0 |
| Solver failures | 0 of 700 legs | 0 of 1,158 legs |
| All 72 minutes (no verdict) | 5 → 5 of 12 | 6 → 8 of 12 |
| C-flat (one rate, no verdict) | 4 of 12 at 7.0113 % a year | 7 of 12 at 8.4309 % a year |
| r_m, % a year (median, min, max) | 7.0113, 2.8884, 10.2403 | 7.9545, 1.7194, 11.5076 |

No r_m outside −5 % to +20 % a year. SENSEX verdict-minute and all-72 readings agree on the 10-of-12 bar.

## Gates and preconditions

- Step 0: four input hashes match; the four backfill conventions confirmed (spot = `hist_spot_bars_1m.close` same bar_ts; R_FLAT 0.065; T = calendar days / 365, whole days; price = bar close). The backfill does **not** call `core/bs_engine.py`; it carries its own vectorised solver. Per the operator's recorded clarification, the re-solve used that solver, extracted by AST (11 of 11 segments byte-equal, no free names). `iv` and `gamma` are unconstrained numeric. Rule 13: no contamination range names the three relations.
- Step 1a: Part H selection re-run is byte-identical to `_partH_analysis.txt`; 72 of 72 rows; F missing 0, fut_dte < 3 0, next contract 0.
- Run log: 24 OK, 0 FAIL, 0 STOP, 3.383 to 6.819 s per query, last line `ALL 24 DONE` (asserted in code before analysis).
- **G0 PASS** both: NIFTY 5 of 12, SENSEX 6 of 12, 0 of 24 per-day medians off Part B by more than 1e-4.
- **G1 PASS** both: NIFTY 700 of 700 legs, SENSEX 1,158 of 1,158 within tolerance; max |Δγ/γ| 4.4e-16, max |ΔIV| 5.0e-5 vol points; all 24 per-day medians within 0.005. The replication is exact.

## Reading

- **NIFTY:** replacing the flat 6.5 % with the futures-implied rate leaves the in-band count at 5 of 12 and moves one day out. The flat rate is not the main cause of the NIFTY call/put gamma gap on this sample.
- **SENSEX:** 7 → 9 of 12, one day short of the bar, with no day leaving the band. The rate explains part of the SENSEX gap; not enough to pass. Recorded as "not shown with this futures source" (thin SENSEX futures; 10 zero-volume minutes excluded).
- **C-flat** scored no better than per-minute r_m (NIFTY worse than before). A better single flat rate would not fix it either.
- What remains untested as the cause: bar closes instead of mids (and non-synchronous call, put and spot closes within the minute), no intraday time decay, the calendar-day T convention. None was measured here.

## Consequence (pre-agreed, design §10)

Both symbols take the fallback: the pin look-back uses the stored own-solved gamma (flat 6.5 %), **one gamma per strike (the OTM leg)**, with the call/put gamma disagreement disclosed (Part B: failing days 5.7 % to 21.8 % from parity). The forward-rate question goes into the production gamma scoping, now with the finding that the rate alone does not close the gap for NIFTY.

## Noted during the run

- A tracked file, `refresh_dhan_token.py` in `~/meridian-cc`, shows as modified. This run wrote only under `sens/`; the modification is from elsewhere (another session or the token routine). Not investigated.
- The design's wording "the re-solve calls `core/bs_engine.py`" was wrong (the backfill never calls it). Recorded as a clarification in `sens/conventions.md`; no gate or threshold changed.
- The advisor's figure "IV_TOL ≈ 0.1 vol points" was wrong (IV_TOL is a price residual). Withdrawn; the run measured the noise per leg.
