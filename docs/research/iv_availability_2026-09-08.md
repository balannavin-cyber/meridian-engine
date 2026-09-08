# iv / straddle / volatility column availability

**Date measured:** 2026-09-08 · **Access:** PostgREST service-role only. No `psql`, no DB
password, no arbitrary-SQL RPC.

Every number cites the query that produced it. Where a count is zero it is written as zero.

---

## 1. Exact column lists, from the live database

Taken from the live PostgREST OpenAPI document (`GET /rest/v1/`), which is generated from
the catalog and therefore lists columns that hold no non-null value in any row. Each list was
cross-checked against the keys of a sampled row (`?select=*&limit=1`); for all four tables
the two agree exactly, with no column in one and not the other.

### `option_chain_snapshots` — 21 columns

Sampled row returned 21 keys; columns in OpenAPI but absent from the
sample: 0; in the sample but absent from OpenAPI: 0.

| # | column | type |
|---:|---|---|
| 1 | `id` | uuid |
| 2 | `ts` | timestamp with time zone |
| 3 | `symbol` | text |
| 4 | `expiry_date` | date |
| 5 | `spot` | numeric |
| 6 | `strike` | numeric |
| 7 | `option_type` | text |
| 8 | `ltp` | numeric |
| 9 | `bid` | numeric |
| 10 | `ask` | numeric |
| 11 | `oi` | numeric |
| 12 | `oi_change` | numeric |
| 13 | `volume` | numeric |
| 14 | `iv` | numeric |
| 15 | `delta` | numeric |
| 16 | `gamma` | numeric |
| 17 | `theta` | numeric |
| 18 | `vega` | numeric |
| 19 | `raw` | jsonb |
| 20 | `created_at` | timestamp with time zone |
| 21 | `run_id` | uuid |

### `gex_strike_snapshots` — 14 columns

Sampled row returned 14 keys; columns in OpenAPI but absent from the
sample: 0; in the sample but absent from OpenAPI: 0.

| # | column | type |
|---:|---|---|
| 1 | `id` | uuid |
| 2 | `run_id` | uuid |
| 3 | `symbol` | text |
| 4 | `ts` | timestamp with time zone |
| 5 | `expiry_date` | date |
| 6 | `dte` | integer |
| 7 | `strike` | numeric |
| 8 | `spot` | numeric |
| 9 | `oi_call` | bigint |
| 10 | `oi_put` | bigint |
| 11 | `gex_cr` | numeric |
| 12 | `created_at` | timestamp with time zone |
| 13 | `gamma_call` | double precision |
| 14 | `gamma_put` | double precision |

### `gamma_metrics` — 27 columns

Sampled row returned 27 keys; columns in OpenAPI but absent from the
sample: 0; in the sample but absent from OpenAPI: 0.

| # | column | type |
|---:|---|---|
| 1 | `id` | uuid |
| 2 | `ts` | timestamp with time zone |
| 3 | `symbol` | text |
| 4 | `expiry_date` | date |
| 5 | `spot` | numeric |
| 6 | `net_gex` | numeric |
| 7 | `gamma_concentration` | numeric |
| 8 | `flip_level` | numeric |
| 9 | `flip_distance` | numeric |
| 10 | `straddle_atm` | numeric |
| 11 | `straddle_slope` | numeric |
| 12 | `vix` | numeric |
| 13 | `breadth_regime` | text |
| 14 | `expansion_probability` | numeric |
| 15 | `regime` | text |
| 16 | `created_at` | timestamp with time zone |
| 17 | `run_id` | uuid |
| 18 | `flip_distance_pct` | numeric |
| 19 | `gamma_zone` | text |
| 20 | `raw` | jsonb |
| 21 | `straddle_velocity` | numeric |
| 22 | `otm_oi_velocity` | numeric |
| 23 | `spot_vs_range` | numeric |
| 24 | `run_type` | text |
| 25 | `dte` | integer |
| 26 | `max_gamma_strike` | numeric |
| 27 | `pin_risk_score` | numeric |

### `volatility_snapshots` — 36 columns

Sampled row returned 36 keys; columns in OpenAPI but absent from the
sample: 0; in the sample but absent from OpenAPI: 0.

| # | column | type |
|---:|---|---|
| 1 | `id` | bigint |
| 2 | `ts` | timestamp with time zone |
| 3 | `symbol` | text |
| 4 | `expiry_date` | date |
| 5 | `expiry_type` | text |
| 6 | `dte` | integer |
| 7 | `spot` | numeric |
| 8 | `atm_strike` | integer |
| 9 | `atm_call_iv` | numeric |
| 10 | `atm_put_iv` | numeric |
| 11 | `atm_iv_avg` | numeric |
| 12 | `iv_skew` | numeric |
| 13 | `source_run_id` | uuid |
| 14 | `raw` | jsonb |
| 15 | `created_at` | timestamp with time zone |
| 16 | `india_vix` | numeric |
| 17 | `vix_change` | numeric |
| 18 | `vix_regime` | text |
| 19 | `vix_context_regime` | text |
| 20 | `vix_level_bucket` | text |
| 21 | `vix_percentile` | numeric |
| 22 | `vix_change_5m` | numeric |
| 23 | `vix_change_15m` | numeric |
| 24 | `vix_change_30m` | numeric |
| 25 | `vix_change_since_open` | numeric |
| 26 | `vix_pct_change_since_open` | numeric |
| 27 | `vix_intraday_velocity` | text |
| 28 | `vix_change_1d` | numeric |
| 29 | `vix_change_3d` | numeric |
| 30 | `vix_change_5d` | numeric |
| 31 | `vix_pct_change_1d` | numeric |
| 32 | `vix_interday_velocity` | text |
| 33 | `vix_percentile_regime` | text |
| 34 | `vix_direction` | text |
| 35 | `vix_slope` | numeric |
| 36 | `atm_iv_vs_vix_spread` | numeric |

---

## 2. Which of these columns are in scope

The audit asks for `iv`, `straddle_atm`, `straddle_slope`, and any volatility-related column.
Membership was decided by reading the lists above, not the table names.

| table | columns measured | count |
|---|---|---:|
| `option_chain_snapshots` | `iv`, `vega` | 2 |
| `gex_strike_snapshots` | — | **0** |
| `gamma_metrics` | `straddle_atm`, `straddle_slope`, `straddle_velocity`, `vix` | 4 |
| `volatility_snapshots` | `atm_call_iv`, `atm_put_iv`, `atm_iv_avg`, `iv_skew`, `atm_iv_vs_vix_spread`, `india_vix`, `vix_change`, `vix_regime`, `vix_context_regime`, `vix_level_bucket`, `vix_percentile`, `vix_change_5m`, `vix_change_15m`, `vix_change_30m`, `vix_change_since_open`, `vix_pct_change_since_open`, `vix_intraday_velocity`, `vix_change_1d`, `vix_change_3d`, `vix_change_5d`, `vix_pct_change_1d`, `vix_interday_velocity`, `vix_percentile_regime`, `vix_direction`, `vix_slope` | 25 |

Three points about scope, each read off the lists in §1:

- **`gex_strike_snapshots` contains no `iv` column, no `straddle_atm`, no `straddle_slope`,
  and no volatility column of any kind.** Its 14 columns are `id`, `run_id`, `symbol`, `ts`,
  `expiry_date`, `dte`, `strike`, `spot`, `oi_call`, `oi_put`, `gex_cr`, `created_at`,
  `gamma_call`, `gamma_put`. It contributes zero columns to §3 and is not measured there.
- **`gamma_metrics` contains no `iv` column.** It carries `vix` (a numeric) and the three
  straddle columns. `iv` appears in `option_chain_snapshots` and, as ATM aggregates, in
  `volatility_snapshots`.
- `vega` is included for `option_chain_snapshots` because it is the volatility sensitivity
  in that table; `delta`, `gamma` and `theta` are present too but are not volatility columns
  and were not measured.

---

## 3. Non-null coverage, per month per symbol

### Method

```
rows      GET /<table>?select=*&limit=0&ts=gte.<month>&ts=lt.<next>&symbol=eq.<sym>
                Prefer: count=exact
non-null  ... &<column>=not.is.null            Prefer: count=exact
presence  GET /<table>?select=<column>&ts=gte.<day>&ts=lt.<day+1>&symbol=eq.<sym>
                &<column>=not.is.null&limit=1
```

Rules the sweep enforced:

- **`count=planned` is never used.** A planner floor of 1 over an all-NULL column is not a
  row, so every count here is `count=exact`.
- **A `57014` is never recorded as an absence.** Any cell that timed out at month scope is
  re-run day by day and the day-level exact counts summed. No cell in this sweep required
  that fallback — every month-scoped count returned.
- **Every zero is confirmed independently.** For each column-month whose exact count is 0,
  a day-scoped `limit=1` probe is run across every day of that month. **462 zero cells were
  produced and all 462 were confirmed by a probe that returned a real empty list.** Zero
  disagreed, and zero were missing a probe.
- The sweep asserts `unresolved == []` before writing; it printed `UNRESOLVED: []`.

Months were probed from one month before each table's discovered minimum to one month after
its maximum, so a real edge outside the range would appear rather than be excluded.

### Discovered bounds

| table | ts column | min | max |
|---|---|---|---|
| `option_chain_snapshots` | `ts` | 2026-08-24T10:00:05.366368+00:00 | 2026-09-08T10:10:04.167144+00:00 |
| `gex_strike_snapshots` | `ts` | 2026-05-25T09:56:07.707025+00:00 | 2026-09-08T09:50:06.404415+00:00 |
| `gamma_metrics` | `ts` | 2026-06-10T10:55:05.214937+00:00 | 2026-09-08T09:50:06.404415+00:00 |
| `volatility_snapshots` | `ts` | 2025-04-01T03:45:00+00:00 | 2026-09-08T09:50:06.404415+00:00 |

**One bound moved during this session and that affects how these are read.** The flip audit,
run earlier the same day, measured `gamma_metrics` min as `2026-06-09T10:55:05.326819+00:00`.
This sweep measured `2026-06-10T10:55:05.214937+00:00`. Re-checked directly:

```
GET /gamma_metrics?select=ts,symbol&ts=gte.2026-06-09&ts=lt.2026-06-10&limit=3  -> []
GET /gamma_metrics?select=ts,symbol&ts=gte.2026-06-10&ts=lt.2026-06-11&limit=2
   -> [{'ts':'2026-06-10T10:55:05.214937+00:00','symbol':'SENSEX'}]
GET /gamma_metrics?select=*&limit=0   Prefer: count=exact  -> */9807
```

2026-06-09 held rows a few hours earlier and holds zero now, while the total row count rose.
`gamma_metrics` is being trimmed at the tail as it grows at the head, so its "full history"
is a moving window and the figures below are a snapshot as of 2026-09-08. The other three
tables were not re-checked for this behaviour and no claim is made about them.

### 3.1 `option_chain_snapshots` — `iv`, `vega`

| month | symbol | rows | non-null `iv` | % | non-null `vega` | % |
|---|---|---:|---:|---:|---:|---:|
| 2026-08 | NIFTY | 159,442 | 159,442 | 100.0% | 159,442 | 100.0% |
| 2026-08 | SENSEX | 126,348 | 126,348 | 100.0% | 126,348 | 100.0% |
| 2026-09 | NIFTY | 233,818 | 233,818 | 100.0% | 233,818 | 100.0% |
| 2026-09 | SENSEX | 174,760 | 174,760 | 100.0% | 174,760 | 100.0% |

`iv` and `vega` are non-null on every row in both months, both symbols. 2026-07 and 2026-10
were probed and return zero rows for both symbols, which bounds the table rather than
indicating anything about the columns.

### 3.2 `gamma_metrics` — `straddle_atm`, `straddle_slope`, `straddle_velocity`, `vix`

This table has **no `iv` column**; see §1. `vix` is its only volatility column.

| month | symbol | rows | `straddle_atm` | `straddle_slope` | `straddle_velocity` | `vix` |
|---|---|---:|---:|---:|---:|---:|
| 2026-06 | NIFTY | 824 | 818 (99.3%) | 796 (96.6%) | 813 (98.7%) | 806 (97.8%) |
| 2026-06 | SENSEX | 791 | 787 (99.5%) | 778 (98.4%) | 784 (99.1%) | 790 (99.9%) |
| 2026-07 | NIFTY | 1,893 | 1,884 (99.5%) | 1,832 (96.8%) | 1,879 (99.3%) | 1,863 (98.4%) |
| 2026-07 | SENSEX | 1,893 | 1,881 (99.4%) | 1,850 (97.7%) | 1,871 (98.8%) | 1,892 (99.9%) |
| 2026-08 | NIFTY | 1,709 | 1,699 (99.4%) | 1,664 (97.4%) | 1,695 (99.2%) | 1,669 (97.7%) |
| 2026-08 | SENSEX | 1,708 | 1,702 (99.6%) | 1,689 (98.9%) | 1,697 (99.4%) | 1,704 (99.8%) |
| 2026-09 | NIFTY | 496 | 491 (99.0%) | 485 (97.8%) | 488 (98.4%) | 491 (99.0%) |
| 2026-09 | SENSEX | 493 | 490 (99.4%) | 488 (99.0%) | 488 (99.0%) | 493 (100.0%) |

All four are populated on 96–100% of rows in every month. None is ever zero, and none is
ever complete: the shortfall is a handful of rows per month rather than a block.

### 3.3 `volatility_snapshots` — 25 columns across 18 months

The 25 columns fall into two groups that behave differently, so they are shown separately.
The grouping is by measured behaviour, not by name: `atm_iv_vs_vix_spread` is placed with
the VIX group because its coverage matches that group exactly and not the IV group.

#### 3.3a The four ATM IV columns

| month | symbol | rows | `atm_iv_avg` | `atm_put_iv` | `atm_call_iv` | `iv_skew` |
|---|---|---:|---:|---:|---:|---:|
| 2025-04 | NIFTY | 991 | 991 (100.0%) | 991 (100.0%) | 938 (94.7%) | 938 (94.7%) |
| 2025-04 | SENSEX | 704 | 704 (100.0%) | 704 (100.0%) | 678 (96.3%) | 678 (96.3%) |
| 2025-05 | NIFTY | 1,240 | 1,240 (100.0%) | 1,240 (100.0%) | 1,136 (91.6%) | 1,136 (91.6%) |
| 2025-05 | SENSEX | 929 | 929 (100.0%) | 929 (100.0%) | 922 (99.2%) | 922 (99.2%) |
| 2025-06 | NIFTY | 1,258 | 1,258 (100.0%) | 1,258 (100.0%) | 1,258 (100.0%) | 1,258 (100.0%) |
| 2025-06 | SENSEX | 942 | 942 (100.0%) | 942 (100.0%) | 942 (100.0%) | 942 (100.0%) |
| 2025-07 | NIFTY | 1,511 | 1,511 (100.0%) | 1,511 (100.0%) | 1,332 (88.2%) | 1,332 (88.2%) |
| 2025-07 | SENSEX | 1,238 | 1,238 (100.0%) | 1,238 (100.0%) | 1,212 (97.9%) | 1,212 (97.9%) |
| 2025-08 | NIFTY | 1,308 | 1,308 (100.0%) | 1,308 (100.0%) | 1,300 (99.4%) | 1,300 (99.4%) |
| 2025-08 | SENSEX | 1,033 | 1,033 (100.0%) | 1,033 (100.0%) | 1,013 (98.1%) | 1,013 (98.1%) |
| 2025-09 | NIFTY | 1,538 | 1,538 (100.0%) | 1,538 (100.0%) | 1,321 (85.9%) | 1,321 (85.9%) |
| 2025-09 | SENSEX | 1,344 | 1,344 (100.0%) | 1,344 (100.0%) | 1,336 (99.4%) | 1,336 (99.4%) |
| 2025-10 | NIFTY | 1,291 | 1,291 (100.0%) | 1,291 (100.0%) | 1,139 (88.2%) | 1,139 (88.2%) |
| 2025-10 | SENSEX | 762 | 762 (100.0%) | 762 (100.0%) | 760 (99.7%) | 760 (99.7%) |
| 2025-11 | NIFTY | 1,244 | 1,244 (100.0%) | 1,244 (100.0%) | 1,242 (99.8%) | 1,242 (99.8%) |
| 2025-11 | SENSEX | 973 | 973 (100.0%) | 973 (100.0%) | 939 (96.5%) | 939 (96.5%) |
| 2025-12 | NIFTY | 1,456 | 1,456 (100.0%) | 1,456 (100.0%) | 1,316 (90.4%) | 1,316 (90.4%) |
| 2025-12 | SENSEX | 1,142 | 1,142 (100.0%) | 1,142 (100.0%) | 1,078 (94.4%) | 1,078 (94.4%) |
| 2026-01 | NIFTY | 1,216 | 1,216 (100.0%) | 1,216 (100.0%) | 1,180 (97.0%) | 1,180 (97.0%) |
| 2026-01 | SENSEX | 874 | 874 (100.0%) | 874 (100.0%) | 871 (99.7%) | 871 (99.7%) |
| 2026-02 | NIFTY | 1,264 | 1,264 (100.0%) | 1,264 (100.0%) | 1,264 (100.0%) | 1,264 (100.0%) |
| 2026-02 | SENSEX | 974 | 974 (100.0%) | 974 (100.0%) | 961 (98.7%) | 961 (98.7%) |
| 2026-03 | NIFTY | 1,217 | 1,217 (100.0%) | 1,217 (100.0%) | 1,215 (99.8%) | 1,215 (99.8%) |
| 2026-03 | SENSEX | 1,003 | 1,003 (100.0%) | 1,003 (100.0%) | 1,003 (100.0%) | 1,003 (100.0%) |
| 2026-04 | NIFTY | 2,087 | 2,087 (100.0%) | 2,087 (100.0%) | 2,087 (100.0%) | 2,087 (100.0%) |
| 2026-04 | SENSEX | 2,093 | 2,093 (100.0%) | 2,093 (100.0%) | 2,093 (100.0%) | 2,093 (100.0%) |
| 2026-05 | NIFTY | 2,545 | 2,545 (100.0%) | 2,545 (100.0%) | 2,545 (100.0%) | 2,545 (100.0%) |
| 2026-05 | SENSEX | 2,561 | 2,561 (100.0%) | 2,561 (100.0%) | 2,561 (100.0%) | 2,561 (100.0%) |
| 2026-06 | NIFTY | 979 | 979 (100.0%) | 979 (100.0%) | 979 (100.0%) | 979 (100.0%) |
| 2026-06 | SENSEX | 946 | 946 (100.0%) | 946 (100.0%) | 946 (100.0%) | 946 (100.0%) |
| 2026-07 | NIFTY | 1,891 | 1,891 (100.0%) | 1,891 (100.0%) | 1,891 (100.0%) | 1,891 (100.0%) |
| 2026-07 | SENSEX | 1,893 | 1,893 (100.0%) | 1,893 (100.0%) | 1,893 (100.0%) | 1,893 (100.0%) |
| 2026-08 | NIFTY | 1,709 | 1,709 (100.0%) | 1,709 (100.0%) | 1,709 (100.0%) | 1,709 (100.0%) |
| 2026-08 | SENSEX | 1,708 | 1,708 (100.0%) | 1,708 (100.0%) | 1,708 (100.0%) | 1,708 (100.0%) |
| 2026-09 | NIFTY | 496 | 496 (100.0%) | 496 (100.0%) | 496 (100.0%) | 496 (100.0%) |
| 2026-09 | SENSEX | 493 | 493 (100.0%) | 493 (100.0%) | 493 (100.0%) | 493 (100.0%) |

`atm_iv_avg` and `atm_put_iv` are non-null on **100% of rows in all 18 months**, both
symbols. `atm_call_iv` and `iv_skew` are equal to each other in every one of the 36
symbol-months and fall short of 100% in the earlier ones — 938 of 991 rows in 2025-04
NIFTY is the lowest. They first reach 100% in a single month at 2026-02 NIFTY (1,264 of
1,264) but not for both symbols together until **2026-04**; 2026-02 SENSEX is 961 of 974
and 2026-03 NIFTY is 1,215 of 1,217. From 2026-04 onward both are at 100% in every month.

#### 3.3b The 21 VIX-dependent columns

These 21 move together. Across the populated era the spread between the best- and
worst-covered of them within a single symbol-month is at most 31 rows, except 2026-06
(110 NIFTY, 76 SENSEX). The per-month minimum and maximum across all 21 are therefore
given rather than 21 near-identical columns.

| month | symbol | rows | min across the 21 | max across the 21 | max as % of rows |
|---|---|---:|---:|---:|---:|
| 2025-04 | NIFTY | 991 | 0 | 0 | 0.0% |
| 2025-04 | SENSEX | 704 | 0 | 0 | 0.0% |
| 2025-05 | NIFTY | 1,240 | 0 | 0 | 0.0% |
| 2025-05 | SENSEX | 929 | 0 | 0 | 0.0% |
| 2025-06 | NIFTY | 1,258 | 0 | 0 | 0.0% |
| 2025-06 | SENSEX | 942 | 0 | 0 | 0.0% |
| 2025-07 | NIFTY | 1,511 | 0 | 0 | 0.0% |
| 2025-07 | SENSEX | 1,238 | 0 | 0 | 0.0% |
| 2025-08 | NIFTY | 1,308 | 0 | 0 | 0.0% |
| 2025-08 | SENSEX | 1,033 | 0 | 0 | 0.0% |
| 2025-09 | NIFTY | 1,538 | 0 | 0 | 0.0% |
| 2025-09 | SENSEX | 1,344 | 0 | 0 | 0.0% |
| 2025-10 | NIFTY | 1,291 | 0 | 0 | 0.0% |
| 2025-10 | SENSEX | 762 | 0 | 0 | 0.0% |
| 2025-11 | NIFTY | 1,244 | 0 | 0 | 0.0% |
| 2025-11 | SENSEX | 973 | 0 | 0 | 0.0% |
| 2025-12 | NIFTY | 1,456 | 0 | 0 | 0.0% |
| 2025-12 | SENSEX | 1,142 | 0 | 0 | 0.0% |
| 2026-01 | NIFTY | 1,216 | 0 | 0 | 0.0% |
| 2026-01 | SENSEX | 874 | 0 | 0 | 0.0% |
| 2026-02 | NIFTY | 1,264 | 0 | 0 | 0.0% |
| 2026-02 | SENSEX | 974 | 0 | 0 | 0.0% |
| 2026-03 | NIFTY | 1,217 | 262 | 293 | 24.1% |
| 2026-03 | SENSEX | 1,003 | 255 | 285 | 28.4% |
| 2026-04 | NIFTY | 2,087 | 2,067 | 2,087 | 100.0% |
| 2026-04 | SENSEX | 2,093 | 2,073 | 2,093 | 100.0% |
| 2026-05 | NIFTY | 2,545 | 2,526 | 2,545 | 100.0% |
| 2026-05 | SENSEX | 2,561 | 2,542 | 2,561 | 100.0% |
| 2026-06 | NIFTY | 979 | 869 | 979 | 100.0% |
| 2026-06 | SENSEX | 946 | 870 | 946 | 100.0% |
| 2026-07 | NIFTY | 1,891 | 1,869 | 1,891 | 100.0% |
| 2026-07 | SENSEX | 1,893 | 1,872 | 1,893 | 100.0% |
| 2026-08 | NIFTY | 1,709 | 1,688 | 1,709 | 100.0% |
| 2026-08 | SENSEX | 1,708 | 1,688 | 1,708 | 100.0% |
| 2026-09 | NIFTY | 496 | 490 | 496 | 100.0% |
| 2026-09 | SENSEX | 493 | 487 | 493 | 100.0% |

**Every one of the 21 is zero in every month from 2025-04 through 2026-02** — eleven months,
both symbols. That is 462 column-months at zero, and each was confirmed by a day-scoped
`limit=1` probe returning a real empty list rather than being inferred from the count.

The first non-null value in the group, located directly:

```
GET /volatility_snapshots?select=ts,india_vix,atm_iv_avg&symbol=eq.NIFTY
    &india_vix=not.is.null&order=ts.asc&limit=1
   -> 2026-03-09T08:49:45.984901+00:00  india_vix 23.36  atm_iv_avg 36.643

same for SENSEX
   -> 2026-03-09T08:50:25.283299+00:00  india_vix 23.36  atm_iv_avg 35.364
```

2026-03 is the transition month — 293 of 1,217 NIFTY rows and 285 of 1,003 SENSEX rows carry
`india_vix`. From 2026-04 onward the best-covered of the 21 is at **100.0% of rows in every
month**, both symbols; the worst-covered ranges from **88.8%** (2026-06 NIFTY) to 99.3%.

#### 3.3c All 25 columns, whole history

Totals over the 46,853 rows measured across 2025-04-01 to 2026-09-08, both symbols pooled.

| column | non-null | % of rows |
|---|---:|---:|
| `atm_call_iv` | 45,757 | 97.7% |
| `atm_put_iv` | 46,853 | 100.0% |
| `atm_iv_avg` | 46,853 | 100.0% |
| `iv_skew` | 45,757 | 97.7% |
| `atm_iv_vs_vix_spread` | 19,918 | 42.5% |
| `india_vix` | 19,979 | 42.6% |
| `vix_change` | 19,979 | 42.6% |
| `vix_regime` | 19,979 | 42.6% |
| `vix_context_regime` | 19,978 | 42.6% |
| `vix_level_bucket` | 19,978 | 42.6% |
| `vix_percentile` | 19,978 | 42.6% |
| `vix_change_5m` | 19,816 | 42.3% |
| `vix_change_15m` | 19,808 | 42.3% |
| `vix_change_30m` | 19,796 | 42.3% |
| `vix_change_since_open` | 19,606 | 41.8% |
| `vix_pct_change_since_open` | 19,606 | 41.8% |
| `vix_intraday_velocity` | 19,808 | 42.3% |
| `vix_change_1d` | 19,978 | 42.6% |
| `vix_change_3d` | 19,978 | 42.6% |
| `vix_change_5d` | 19,978 | 42.6% |
| `vix_pct_change_1d` | 19,978 | 42.6% |
| `vix_interday_velocity` | 19,978 | 42.6% |
| `vix_percentile_regime` | 19,918 | 42.5% |
| `vix_direction` | 19,918 | 42.5% |
| `vix_slope` | 19,762 | 42.2% |

Rows measured: 46,853.

### 3.4 `gex_strike_snapshots`

Not measured in this section, because §1 establishes it has no `iv`, no `straddle_atm`, no
`straddle_slope` and no volatility column among its 14 columns. Its row coverage over
2026-04 to 2026-10 was still swept as a control and returns rows in 2026-05 through 2026-09
for both symbols, with zero rows in the probed months either side.

