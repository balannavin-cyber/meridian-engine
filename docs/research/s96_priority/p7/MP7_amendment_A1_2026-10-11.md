# M-P7 pre-registration — Amendment A1 (query shape only)

| Field | Value |
|---|---|
| **Amends** | `MP7_flow_badge_prereg_2026-10-11.md`, blob `5813af540df15d542ddb5f509585cba08c9fef83` (commit `d909559`). **That file is not edited.** |
| **Filed** | 2026-10-11, before any Part 1 data was returned. |
| **Changes** | `mp7/mp7_status.sql` and `mp7/mp7_cycles.sql`, the front-expiry subquery only. |
| **Does not change** | Sample, session / front / anchor definitions, leg arithmetic, badge rule, verdict cut, scorer. |

## What happened

The first run (2026-10-11 ~18:21 IST, `~/meridian-cc` at `d909559`) stopped on its first date: the
2026-08-24 status query hit `roq.sh`'s 30 s statement timeout. **No status or cycle row was returned**, so
no session status, flow, book or sign from the sample has been seen. Part 0 had already run: 0a printed no
range in the window and 1 visible row; 0b printed the live book (settled 15:10:07) and P5 anchors
(NIFTY 08:30:08, SENSEX 08:35:05) for 2026-10-09 — control inputs, not outcomes, and not yet compared.

`EXPLAIN` (no ANALYZE) of the 2026-08-24 status query: the front-expiry
`min(c.expiry_date) … WHERE symbol, ts range, expiry_date >= d` ran as an **Index Scan on
`idx_ocs_symbol_expiry_strike_type`** with `Index Cond: (symbol, expiry_date >= session_date)` and ts left as
a filter — **cost 294,617** — walking the symbol's index in expiry order until a row satisfies the ts range.
The anchor `min(ts)` already ranged on `idx_ocs_ts_symbol_expiry` (Index Only Scan Backward, cost 322).

## The change

`min(expiry_date)` over the same predicates becomes `min()` over a `SELECT DISTINCT expiry_date` of the same
predicates. The two are equal by definition (min of a set equals min of its distinct values). DISTINCT needs
every matching row, so the planner's cheap path is the ts range — the `v_dex_standing_book` `legs` CTE shape,
measured there at 61 ms.

## Evidence the change is shape only

On the synthetic fixture (local Postgres 16.15, `mp7/fixture/`), v1 and A1 output compared byte for byte on
six dates covering every status (NOT_SESSION frozen and calendar-closed, NO_PREOPEN, ANCHORED, and a date with
no rows): **identical**, both files, row counts 3 / 1 / 3 / 1 / 3 / 1 / 3 / 1 / 3 / 147 / 3 / 147; the
independent recompute still agrees at max abs diff 0 on 146 cycles. A first comparison ran against a stopped
local server and reported "same" on two empty outputs; it was discarded and re-run with row counts printed,
because a check that compares nothing passes.

**On the box, before the re-run:** `EXPLAIN` both files for 2026-08-24 and 2026-10-09 and confirm no
`option_chain_snapshots` node is an Index Scan on `idx_ocs_symbol_expiry_strike_type` with ts as a filter.
