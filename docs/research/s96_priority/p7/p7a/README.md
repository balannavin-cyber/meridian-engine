# P7a — `v_dex_flow_vs_book` (ruling S96-A)

DDL: `sql/2026-10-11_s96_v_dex_flow_vs_book.sql` (Sections 1–4). Flow numbers only, no badge column
(M-P7 BUILD is conditional on the untraded-leg guard, TD-S95-NEW-1 (c)).

| file | what |
|---|---|
| `p7a_body_cost.sql` | the view body as a plain query, for costing through `bin/roq.sh` before apply |
| `roles.sql`, `zero_oi.sql`, `nextday.sql` | fixture additions used by the S96 test (local Postgres only): the three roles, a deep-ITM PE whose OI went to 0 (exercises the zero-OI gap branch), next-day pre-open rows (exercises the join guard) |

Fixture result (S96): see the DDL header. The fixture base is `../mp7/fixture/` (`schema.sql`, `gen.py`).
