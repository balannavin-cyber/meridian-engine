<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/order_check_rev3_prereg_FROZEN_2026-11-23.md -->
# Order check on revision 3 of v_gex_strike_rank_gross - pre-registration (FROZEN 2026-11-23 15:03 IST on the operator's "approved")

Written Mon 2026-11-23 ~10:30 IST, MR-PIN3; frozen unchanged from the draft on the operator's approval at 15:03 IST. No data read yet. Owed by the pin lane to the engine (I-002 report, 10:05 IST): revision 3 (`sql/2026-11-23_s107_v_gex_strike_rank_gross.sql`, md5 `2e94b918e1d13a1a4383bf7d3bf8026c`, applied by the operator 2026-11-23) adds columns, so the revision-2 order check no longer covers it. The engine's own evidence (scratch Postgres 16: revision 3 = revision 2 on 119 of 119 rows over 19 shared columns) does not test the new columns and does not test the view against an independent computation.

## What is checked
The view's ranking and new columns against an independent recomputation from the option-chain legs (`option_chain_snapshots` via the replay's `qR_run` shape, restricted to one run_id), a different source table than the view's `gex_strike_snapshots`. Not an outcome study; no pin-quality claim is made or judged. Nothing is authorised for the Board.

## Design
- Target: the latest run per symbol (NIFTY, SENSEX), read after 15:40 IST on a trading day and before the next trading day's first run. Freeze both run_ids at the first read. If the view's run_id differs between its read and the independent read, abort and redo; never mix runs.
- Reads: read-only through `bin/roq.sh` as `merdian_ro`. Catalog first (view columns), plain EXPLAIN gate, one symbol per query, 5 s sleeps, stop at the first error or any query over 10 s.
- Independent side (Python, `python3 -B`, `ulimit -v`): from the chain legs of the frozen run_id, rebuild per (symbol, expiry): gamma_strike (mean of the two leg gammas when both > 0; the one that is > 0; none), gamma_legs (both / call_only / put_only / none), gross_cr = gamma_strike x (oi_call + oi_put) x spot^2 / 1e7, the 5 % band `abs(strike/spot - 1) <= 0.05`, rank by gross_cr desc, then nearer to spot, then lower strike, lead_rel = (top - second)/top, n_ranked, n_in_set, n_oi_no_gamma (in-set strikes with OI > 0 and no gamma on either leg).

## Pass rule (fixed before the run; each clause can fail)
Per symbol and expiry, over the rows the view returns:
1. Strike sequence of strike_rank 1..10 (or all ranked, if fewer) identical to the independent sequence. Any difference = FAIL.
2. n_ranked, n_in_set, n_oi_no_gamma equal exactly; gamma_legs equal on every compared row. Any difference = FAIL.
3. lead_rel equal within 1e-9 relative. Any difference = FAIL.
4. The independent side and the view give the same set of (symbol, expiry) pairs. A pair present on one side only = FAIL.
Reported, not judged: maximum relative difference of gross_cr per symbol-expiry (stored gamma precision is an open item, TD-PIN2-NEW-1); rows compared per symbol-expiry (denominators); for the live run, the counts of call_only, put_only and n_oi_no_gamma.
Overall PASS = clauses 1 to 4 hold on both symbols. One look; nothing changed after the data is seen.

## Rule 0: can each clause fail for the reason it names?
- Self-test before any live read, on a synthetic fixture that includes (a) a strike with OI and no gamma, (b) a call_only and a put_only strike, (c) a tie on gross_cr, (d) a strike just outside 5 %. Mutation controls: swap the tie-break; drop the OI filter in n_oi_no_gamma; widen the band to 6 %. Each mutant must make at least one clause FAIL, or the check is void.
- Stated limit: the fixture tests the independent Python, not the view. The view's new columns are tested on live data only if the live run has n_oi_no_gamma > 0 or a call_only / put_only strike. If both symbols show zero for all three, the report says "new columns not exercised by live data" and clause 2 is not claimed for them. A further test of the view body over one historic run is an operator decision, not part of this pre-registration.

## Outputs
Folder `~/meridian-cc/docs/research/pin_proof/fix/order_check_rev3/`: `PREREG.md` (this text as received, with its sha256 recorded in the report), self-test result, view reads, independent reads, comparison table, report, `SHA256SUMS`; no `.pyc`; raw dumps over 40 KB stay on the box and are listed in `MANIFEST.md` with sha256. Commit to git by the lane's usual route (branch off `main`, PR, merge by the operator).
