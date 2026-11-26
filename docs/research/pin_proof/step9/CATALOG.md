# Step 9 catalog (P1) — COMPLETE, a to e

**Run:** Thu 2026-11-26, 06:35–07:30 IST. Read-only, through `bin/roq.sh` as `merdian_ro`.
**Design:** `PREREG.md` (sha256 `eef1981…a73f0`) as amended by `PREREG_A1.md`
(sha256 `792b1fb342172caee297e275da66906dadd74163af9758c31e6947a0413557cb`).
**Items c, d and e were read after A1 was approved.** Item b's `gex_cycle_history`
measurement is kept below; it is the fact A1 exists for
(`STOPPED_P1b_gex_cycle_history_2026-11-26.md`).
No outcome figure read. One look unused.

## How `bin/roq.sh` is invoked here

From the script's own header (credential lines not read, not printed):

```
roq.sh < query.sql
roq.sh query.sql
printf '%s' 'SELECT 1;' | roq.sh
roq.sh --skip-verb-guard        (proves items 1-3; not used here)
```

Connects as `merdian_ro` (SELECT only). `PGOPTIONS` sets
`default_transaction_read_only=on` and `statement_timeout=30s` as backend startup options,
re-issued as an SQL prelude. A client-side write-verb guard refuses INSERT / UPDATE /
DELETE / TRUNCATE / DROP / ALTER / CREATE / GRANT / REVOKE / COPY outside a comment or
string literal. EXPLAIN is detected and printed tuples-only, unaligned. Exit codes:
0 ok, 2 usage / credential / guard refusal, other = psql's own.

Credential lives in `$HOME/.merdian_ro_env`, mode 600, outside every git tree, sourced only
inside a subshell and decomposed into libpq `PG*` variables so it never appears in argv.
Not read by this session.

## a. Columns and indexes of the five parent tables

Raw: `out/p1a_cols.txt` (107 rows, `pg_attribute`), `out/p1a_idx.txt` (20 rows,
`pg_indexes`). All five are `relkind = 'r'` (ordinary tables).

| Relation | Columns the design uses |
|---|---|
| `gex_run_v2` | `run_id` uuid, `symbol` text, `ts` timestamptz, `expiry_date` date, `dte` int, `spot` numeric, `net_cr` float8, `net_top_share` float8, `gross_band_cr` float8, `gross_top_share` float8, `gross_hhi` float8, `n_map` int, `n_zero` int, `n_dup_legs` int, `rule_version` text |
| `gex_strike_v2` | `run_id`, `symbol`, `ts`, `expiry_date`, `dte`, `strike` numeric, `spot` numeric, `oi_call` numeric, `oi_put` numeric, `gamma_strike` float8, `gamma_legs` text, `in_map` bool, `in_band` bool, `net_cr` float8, `gross_cr` float8, `rule_version` text |
| `gex_cycle_history` | `symbol`, `expiry_date`, `ts`, `run_id`, `dte` int, `spot` numeric, `net_gex` numeric, `pin_leader_strike` numeric, `conc_top1_share` numeric, `conc_hhi` numeric, `top5_share`, `max_pain_strike`, `flip_level`, `session_gate_state` text |
| `gex_strike_snapshots` | `run_id`, `symbol`, `ts`, `expiry_date`, `dte` int NOT NULL, `strike` numeric, `spot` numeric, `oi_call` bigint, `oi_put` bigint, `gex_cr` numeric NOT NULL, `gamma_call` float8, `gamma_put` float8 |
| `p3b2_invariant_checks` | `kind` text, `symbol`, `expiry_date`, `run_id`, `ts`, `check_id` text, `status` text, `n_checked`, `n_fail`, `max_abs_diff`, `detail` jsonb, `fn_version` |

Indexes the pull would use (all btree):

- `gex_run_v2_symbol_ts_ix (symbol, ts DESC)`; unique `(run_id, symbol, expiry_date)`
- `gex_strike_v2_symbol_ts_ix (symbol, ts DESC)`; unique `(run_id, strike, expiry_date)`
- `gex_cycle_history_pk (symbol, expiry_date, ts)`; `ix_gex_cycle_history_run (run_id)`
- `gex_strike_snapshots`: `ix_gex_strike_snap_sym_ts (symbol, ts DESC)`,
  `idx_gss_symbol_ts_strike (symbol, ts DESC, strike)`, unique `(run_id, strike, expiry_date)`
- `p3b2_invariant_checks_ts_ix (ts)`; unique `(symbol, expiry_date, run_id, check_id)`
  **partial, `WHERE kind = 'check'`**

## b. Privileges, RLS, and the 2026-08-27 counts

`merdian_ro` has SELECT on all five. Every policy applying to `merdian_ro` is PERMISSIVE,
`cmd = SELECT`, `qual = true` — no row filtering.

| Relation | SELECT for merdian_ro | RLS | policies | policy for merdian_ro |
|---|---|---|---|---|
| `gex_cycle_history` | true | **off** | 0 | — (RLS off: the GRANT is the boundary) |
| `gex_run_v2` | true | on | 1 | `gex_run_v2_ro_select`, qual true |
| `gex_strike_snapshots` | true | on | 5 | `merdian_ro_select`, qual true |
| `gex_strike_v2` | true | on | 1 | `gex_strike_v2_ro_select`, qual true |
| `p3b2_invariant_checks` | true | on | 1 | `p3b2_invariant_checks_ro_select`, qual true |

EXPLAIN gate on the five count templates (`out/p1b_explain_counts.txt`): **PASS** — all
Index Only Scan / Index Scan, no Seq Scan, largest scan estimate 9,850
(`gex_strike_snapshots`), all under 20,000.

Counts, `symbol = 'NIFTY'`, `ts` in `[2026-08-27 00:00+05:30, 2026-08-28 00:00+05:30)`
(`out/p1b_counts.txt`):

| Relation | rows | elapsed |
|---|---|---|
| `gex_run_v2` | 83 | 2.57 s |
| `gex_strike_v2` | 8,715 | 2.71 s |
| **`gex_cycle_history`** | **0** | 2.55 s |
| `gex_strike_snapshots` | 8,715 | 2.62 s |
| `p3b2_invariant_checks` | 498 | 2.53 s |

`gex_cycle_history` extent, whole table: NIFTY 2,772 rows, SENSEX 2,771, both
2026-10-05 15:20:06 → 2026-11-25 15:40:06 IST, 34 distinct days. On 2026-11-25 NIFTY:
87 rows, 87 distinct `run_id`, 1 distinct `expiry_date` — where rows exist the
`(run_id, symbol)` join is 1:1 and one expiry leg is stored per run. The zero is the data,
not the reader (SELECT granted, RLS off, 0 policies). **This is what A1 replaces**: under
A1.2 the V1 run-level figures are computed from `gex_strike_snapshots`, and
`gex_cycle_history` is used only by the non-stop controls C1a, C2 and C7, on the runs that
have a row there.

## c. The views behind `conc_top1_share` and `conc_hhi` — description only (A1.3)

Writer: `write_gex_cycle_history_local.py`. `conc_top1_share` is loaded from
`v_gex_concentration.hhi_net` (`:388`), and `conc_hhi` from `derive_rank_fields`
(`merdian_compute/cycle.py:103-108`) over the rows of `v_gex_strike_rank`
(`:152-157`). Raw definitions: `out/p1c_v_gex_concentration.txt`,
`out/p1c_v_gex_strike_rank.txt`.

1. **`conc_top1_share`** is `max(abs(gex_cr)) / NULLIF(sum(abs(gex_cr)), 0)` per
   `(run_id, symbol, expiry_date)` over `gex_strike_snapshots` — the top-1 share, despite
   the view column being named `hhi_net`; this reads the same as A1.2's F4.
2. **`conc_hhi`** is `sum(share_of_abs^2)` over the rows of `v_gex_strike_rank`, whose
   `share_of_abs` is `abs(gex_cr) / NULLIF(sum(abs(gex_cr)) OVER (PARTITION BY run_id,
   symbol, expiry_date), 0)` with `WHERE gex_cr <> 0` (a zero row adds 0 to both sides);
   this reads the same as A1.2's F5.

No like-for-like decision is taken here — **C7 measures it** (A1.3). One difference is
already visible and is not a defect: `v_gex_strike_rank`'s rank tie-break is
`ORDER BY abs(gex_cr) DESC, strike`, i.e. the **lower** strike, where A1.2's F3 tie rule is
the strike **nearer spot, then** the lower strike. C2 compares against
`pin_leader_strike`, which is rank 1 of that view, so a tie can differ legitimately.

## d. Every figure of section 4, as amended, is buildable — PASS

| Figure | V1 side | V2 side |
|---|---|---|
| F1 / F2 net, r | `sum(gex_cr)`, `sum(abs(gex_cr))` over `gex_strike_snapshots` | `gex_run_v2.net_cr`; r from `gex_strike_v2.net_cr` |
| F3 net peak | `strike`, `spot`, `gex_cr` (gss) | `gex_strike_v2.net_cr`, `in_map`, `strike`, `spot` |
| F3b largest positive | `gex_cr > 0` (gss) | `net_cr > 0` (`gex_strike_v2`) |
| F4 top share | `max(abs(gex_cr))/sum(abs(gex_cr))` (gss) | `gex_run_v2.net_top_share` |
| F5 HHI | `sum((abs(gex_cr)/sum(abs))^2)` (gss) | `gex_strike_v2.net_cr` |
| F6 strike level | `gex_cr` per `strike` (gss) | `net_cr` per `strike` (`gex_strike_v2`) |
| F7 guard beyond 5 % | `gamma_call`, `gamma_put`, `strike`, `spot`, `gex_cr` (gss) | — |
| Clock time (§3) | `gex_strike_snapshots.ts` | — |
| Stamp | — | `gex_run_v2.rule_version = 'v2-1.2-gss'` |
| C3 (stop) | — | `gex_run_v2.net_cr` vs `sum(gex_strike_v2.net_cr)` |
| C6 (stop) | `symbol`, `expiry_date`, `ts` (gss) | same (`gex_run_v2`, `gex_strike_v2`) |
| dte (A1.2, joins C6 as a stop) | `gex_strike_snapshots.dte` (int, NOT NULL) | `gex_run_v2.dte` (int) |
| V1 chain-check stratum | `p3b2_invariant_checks`, `check_id = 'V1'` | — |

**`dte` exists in both `gex_strike_snapshots` (NOT NULL) and `gex_run_v2`.** No figure of
section 4 as amended lacks a column. No stop.

## e. `gamma_metrics` (for C1b) — catalog only

Raw: `out/p1e_catalog.txt`. `relkind = 'r'`, 27 columns. Relevant:
`id` uuid NOT NULL, `ts` timestamptz NOT NULL, `symbol` text NOT NULL, `expiry_date` date
NOT NULL, `spot` numeric, **`net_gex` numeric**, `dte` int, `max_gamma_strike` numeric,
`flip_level` numeric, `gamma_concentration` numeric, **`run_id` uuid (nullable)**,
`created_at` timestamptz NOT NULL.

Indexes: `gamma_metrics_pkey btree (id)`; `idx_gm_ts_symbol_expiry btree (ts DESC, symbol,
expiry_date)`; `uix_gamma_metrics_symbol_ts btree (symbol, ts)`;
**`uix_gm_run btree (run_id)` — UNIQUE, so at most one row per non-null `run_id`.**

Privileges: `has_table_privilege('merdian_ro', 'public.gamma_metrics', 'SELECT')` = true;
RLS **on**, 4 policies, of which `merdian_ro_select` is `cmd = SELECT`, `qual = true`
(the others are `anon` ×2 and `marketview_ro`). No row filtering for `merdian_ro`.

EXPLAIN gate (`out/p1e_explain*`, both **PASS**, no Seq Scan):

- count + distinct `run_id`, NIFTY 2026-08-27: Index Scan on
  `uix_gamma_metrics_symbol_ts`, estimate **126** rows.
- min/max `ts` per symbol, written as four scalar subqueries: Index Only Scan (and
  Backward) under `Limit`, largest node estimate **12,702** rows.

Reads:

| Read | Result |
|---|---|
| NIFTY, 2026-08-27 | 83 rows, 83 non-null `run_id`, 83 distinct `run_id`, 1 `expiry_date`, 83 non-null `net_gex` |
| NIFTY extent | 2026-06-12 10:28:39.95 → 2026-11-25 15:40:06.37 IST |
| SENSEX extent | 2026-06-10 16:25:05.21 → 2026-11-25 15:40:06.32 IST |

**C1b can run, joined on `run_id`** (unique `uix_gm_run` gives at most one row per run; on
2026-08-27 NIFTY the 83 rows carry 83 distinct non-null `run_id`, matching
`gex_run_v2`'s 83).

**Coverage limit for C1b, to be carried into the result (A1.4):** `gamma_metrics` starts
2026-06-12 (NIFTY) / 2026-06-10 (SENSEX), so runs from 2026-05-25 to about 2026-06-09/11
have no row there and are outside C1b, as A1.3's "on the runs that have a row there"
allows. The exact k of n is reported by the run, not assumed here.
