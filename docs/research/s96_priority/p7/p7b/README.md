# P7b — `v_gex_greeks_l2_leg` (S96-F) and `v_delta_drift_flow_vs_book` (S96-G)

DDL and checks: `sql/2026-10-12_s96_v_gex_greeks_l2_leg.sql` (Sections A, B, C). Base view first; the flow view
is designed separately (S96-F E4).

| file | what |
|---|---|
| `base_body_cost.sql` | the base view body as a plain query, for costing through `bin/roq.sh` before Section A |
| `fixture_setup.sql` | on a copy of the mp7 fixture DB: `index_futures_snapshots` (r = 6.5 %, 09:20–15:40 every 5 min on 2026-10-09) and vendor gamma = Black-Scholes gamma at the vendor iv |
| `flow_body_cost.sql` | the flow view body as a plain query, for costing through `bin/roq.sh` before its apply |
| `flow_plant_removal.sql`, `flow_plant_gap.sql` | flow-view fixture branches (run inside a rolled-back transaction): a PE side closed to zero OI at the latest ts; a CE side made unpriceable (iv 0) |
| `fixture_plants.sql` | at the NIFTY latest ts, front leg: a deep-ITM guarded strike (gamma 1e-4 at spot × 1.08), a far small-gamma strike (spot × 0.92, kept), a zero-OI strike (priceable, not in the leg set) |

Fixture run (local Postgres 16, `CREATE DATABASE p7b TEMPLATE mp7`, then `fixture_setup.sql`, `fixture_plants.sql`, the
S89 file's Sections 1–5): results in the DDL header.

Flow view DDL and checks: `sql/2026-10-12_s96_v_delta_drift_flow_vs_book.sql`; fixture results in its header.
