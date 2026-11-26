# Step 9 provenance: facts fixed before the run

**Written:** Thu 2026-11-26, before any data query. MR-PIN4, step 9.
**These are inputs, not results.** They are the operator-supplied answer to the
pre-registration's section 5 "provenance period" requirement (`PREREG.md` §5), and they
were fixed before the first database read of this session.

## Writer periods: ONE

The engine compared the row-building code of `gex_strike_snapshots` as syntax trees at
every commit that touched the writer from 2026-05-25 to 2026-11-25 and found no change.

The pin lane checked this independently on 2026-11-26 from the public repository:

- the production log (`script_execution_log`) names **114 distinct repository HEADs** for
  the **19,608** logged writer runs in the period;
- they map to **8 versions** of the writer file(s);
- the eight functions `build_gss_rows`, `signed_gamma_exposure`, `to_float`, `infer_spot`,
  `fetch_option_chain_rows`, `filter_usable_option_rows`, `upsert_gex_strike_snapshots` and
  `_dte_from_ts` are **identical as syntax trees in all 8**;
- and the call `build_gss_rows(option_rows_raw, spot, symbol, ts, expiry_date, run_id)` with
  `spot = infer_spot(option_rows_raw)` is **the same in all 8**.

## Logged runs whose HEAD is not vouched: 6 of 19,608

- Five at HEAD `a5163c4` on 2026-05-25 and 2026-05-26 — that commit does not descend from
  `a776d8a`, the commit that introduced the writer.
- One with a blank HEAD on 2026-06-01.
- All six on the Windows host.

## Host

- The Windows machine wrote from 2026-05-25 to 2026-06-05 (738 logged runs).
- The AWS box wrote from 2026-06-09 (18,870 logged runs).
- Same repository.

## Limits that cannot be removed

- A logged HEAD says nothing about uncommitted edits in the working tree on that day.
- The log holds 19,608 writer runs against 19,050 stored runs, and the reason for the 558
  extra is not known.
- The log does not tie a logged run to a `run_id`.

## Consequence for section 5 of the design

**One provenance period.**

In the result's provenance table also print, as a stated limit and not as a stratum, the
three dates 2026-05-25, 2026-05-26 and 2026-06-01 with, for each date and symbol, runs,
runs with V1 status OK and runs NOT_COMPUTED, under the heading:

> dates holding a logged run whose HEAD is not vouched
