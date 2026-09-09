# Build-readiness inventory — Hedgewall-class options analytics layer

**Date measured:** 2026-09-09 · **Access:** PostgREST service-role only. No `psql`, no DB
password, no arbitrary-SQL RPC. Read-only throughout: no writes, no DDL, no RPC invocation.

Every number cites the query that produced it. Counts are `count=exact` unless labelled
otherwise. Presence is a day-scoped `limit=1` probe returning real rows or a real empty list.
A `57014` is never recorded as an absence. Recursive greps use `/usr/bin/grep`, because
`grep` is a shell function in this environment that filters recursive results.

Inventory only. No fixes and no recommendations appear anywhere in this document.

---

## 1. Storage

### 1.1 What could not be measured

**`pg_total_relation_size` is not obtainable on this access path.** It requires SQL against
the catalog; PostgREST exposes only the `public` tables, not `pg_class`, and none of the 38
published RPCs wraps a size function. Object queried and refused: `pg_class` is absent from
the PostgREST OpenAPI definitions entirely, so there is no endpoint to call. **No size figure
appears below, and none was estimated from column types** — that would be inference, not
measurement. Row counts are given instead.

### 1.2 Row counts

`GET /<table>?select=*&limit=0` with `Prefer: count=exact`, run 2026-09-09.

**Feed side** — tables a build would read:

| table | rows | method |
|---|---:|---|
| `option_chain_snapshots` | 694,368 | exact |
| `historical_option_chain_snapshots` | 3,211,515 | exact |
| `hist_option_bars_1m` | 54,815,936 | planned (exact exceeded the statement timeout) |
| `hist_option_greeks_1m` | 19,250,486 | exact |
| `hist_spot_bars_1m` | 286,630 | exact |
| `hist_spot_bars_5m` | 46,854 | exact |
| `hist_spot_bars_15m` | 16,024 | exact |
| `market_spot_snapshots` | 75,556 | exact |
| `historical_market_spot_1m` | 2,778 | exact |
| `hist_atm_option_bars_5m` | 27,082 | exact |
| `hist_atm_option_bars_15m` | 9,601 | exact |
| `instruments` | 2 | exact |
| `trading_calendar` | 218 | exact |

**Receive side** — tables a build would write to or extend:

| table | rows | method |
|---|---:|---|
| `gex_strike_snapshots` | 1,445,930 | exact |
| `gamma_metrics` | 9,807 | exact |
| `gamma_metrics_shadow` | 1,952 | exact |
| `hist_gamma_metrics` | 182,461 | exact |
| `volatility_snapshots` | 46,853 | exact |
| `hist_volatility_snapshots` | 181,104 | exact |
| `vol_analytics` | 24,759 | exact |
| `hist_pattern_signals` | 7,484 | exact |
| `ict_primitives` | 19,573 | exact |
| `ict_primitive_outcomes` | 19,571 | exact |

One count is not exact. `hist_option_bars_1m` returns `57014` on `count=exact` (measured at
8.4s in the S75 data inventory), so the figure shown is the PostgREST `count=planned` planner
estimate. It is labelled as such and is **not** treated as an exact count. The table is not
absent and the count is not zero — the exact count is simply not obtainable within the
statement timeout.

### 1.3 What a 12-month per-strike GEX backfill would add

The arithmetic is built from measured rows-per-day on `gex_strike_snapshots`, the table such
a backfill would write to. Eight complete recent trading days, both symbols, `count=exact`
for rows and full client-side paging for distinct `ts` and distinct `strike`:

| day | symbol | rows | cycles (distinct ts) | distinct strikes | rows per cycle |
|---|---|---:|---:|---:|---:|
| 2026-08-05 | NIFTY | 9,266 | 82 | 113 | 113.0 |
| 2026-08-05 | SENSEX | 12,865 | 83 | 155 | 155.0 |
| 2026-08-12 | NIFTY | 8,715 | 83 | 105 | 105.0 |
| 2026-08-12 | SENSEX | 12,096 | 84 | 144 | 144.0 |
| 2026-08-19 | NIFTY | 10,043 | 83 | 121 | 121.0 |
| 2026-08-19 | SENSEX | 11,122 | 83 | 134 | 134.0 |
| 2026-08-26 | NIFTY | 8,715 | 83 | 105 | 105.0 |
| 2026-08-26 | SENSEX | 14,608 | 83 | 176 | 176.0 |
| 2026-09-02 | NIFTY | 6,797 | 82 | 83 | 82.9 |
| 2026-09-02 | SENSEX | 10,660 | 82 | 130 | 130.0 |
| 2026-09-03 | NIFTY | 7,111 | 83 | 86 | 85.7 |
| 2026-09-03 | SENSEX | 10,790 | 83 | 130 | 130.0 |
| 2026-09-04 | NIFTY | 7,298 | 84 | 87 | 86.9 |
| 2026-09-04 | SENSEX | 10,530 | 83 | 130 | 126.9 |
| 2026-09-07 | NIFTY | 7,134 | 82 | 87 | 87.0 |
| 2026-09-07 | SENSEX | 11,016 | 81 | 136 | 136.0 |

**NIFTY** — rows/day median **8,006** (min 6,797, max 10,043); cycles/day median 83 (min 82, max 84).

**SENSEX** — rows/day median **11,069** (min 10,530, max 14,608); cycles/day median 83 (min 81, max 84).

Combined both symbols: **19,076 rows per trading day**.

**The day count.** `trading_calendar` cannot supply it: measured, it holds 218 rows spanning
`2026-03-25` to `2027-01-29` (`?select=trade_date&order=trade_date.asc|desc&limit=1`), so it
begins after the data window starts and returns only 110 `is_open=true` rows for
`2025-09-09..2026-09-09`. The measured trading-day series used instead is from the S75 data
inventory, which day-probed `hist_spot_bars_1m` — the only relation covering
`2025-04-01..2026-09-08` for both symbols — and found **356 NIFTY / 355 SENSEX** trading days
across those 17.3 months, i.e. **≈247 per 12 months**.

Two arithmetics, both from measured inputs:

| basis | days per symbol | NIFTY rows | SENSEX rows | total added |
|---|---:|---:|---:|---:|
| 12 calendar months at the measured rate | 247 | 1,977,606 | 2,734,043 | **4,711,648** |
| the 299 days the S75 data inventory found COMPUTABLE NOW | 299 | 2,393,944 | 3,309,631 | **5,703,574** |

`gex_strike_snapshots` currently holds **1,445,930** rows covering 2026-05-25 to 2026-09-08. A
12-month backfill at the measured rate would therefore multiply it by roughly
**3.3×**; the 299-day basis by **3.9×**.

The 299-day figure is the stricter one: it counts only days where the S75 data inventory
measured a per-strike gamma source to exist. The 247-day figure counts trading days
irrespective of whether a source covers them, which §3 addresses.


---

## 2. Compute

### 2.1 The read-only boundary, and what it excludes

`compute_gamma_metrics_local.py` has **no `--dry-run` flag**. `/usr/bin/grep -nE
"add_argument|dry.run|DRY_RUN|--shadow|sys.argv"` returns only the `--shadow` handling at
L1211–1216, and `--shadow` does not suppress writing — it redirects the write to
`gamma_metrics_shadow`, which is still a write to the production database.

So `main()` was **not** invoked. Instead `compute_gamma_metrics(run_id, expected_symbol)`
(L919) was called directly. That function performs the entire fetch-and-compute path —
`fetch_option_chain_rows`, `filter_usable_option_rows`, `build_strike_exposure_map`,
`compute_net_gex`, `compute_gamma_concentration`, `compute_flip_level`,
`compute_straddle_atm`, `compute_straddle_slope`, the velocity helpers,
`fetch_prior_gamma_metrics`, `fetch_spot_vs_range`, `fetch_india_vix`,
`fetch_recent_max_gamma_strikes`, `compute_pin_risk_score`, and the ENH-80 per-strike row
build — and returns a result object.

The two writes, `upsert_gamma_metrics` (L1050) and `upsert_gex_strike_snapshots` (L1194),
are called only from `main()` at L1337 onward and were **not executed**.

**Therefore every timing below excludes write cost.** It is fetch + compute only. What is
excluded, in volume terms, is one `gamma_metrics` row plus the per-strike rows for that
cycle — measured in §1.3 at a median of 105 (NIFTY) and 135 (SENSEX) strikes per cycle.

### 2.2 Measured per-invocation cost

Six real chains — three trading days × two symbols — each computed five times, 30
invocations total. `run_id` values taken from `option_chain_snapshots`, which is the table
the script reads by `run_id`.

```
GET /option_chain_snapshots?select=run_id,symbol,ts&ts=gte.<day>&ts=lt.<day>T23:59:59
    &symbol=eq.<sym>&order=ts.asc&limit=1
then: compute_gamma_metrics(run_id, expected_symbol=sym)   x5, time.perf_counter()
```

| day | symbol | n | median | min | max |
|---|---|---:|---:|---:|---:|
| 2026-09-07 | NIFTY | 5 | 2.494 s | 2.482 s | 2.572 s |
| 2026-09-07 | SENSEX | 5 | 2.472 s | 2.454 s | 2.509 s |
| 2026-09-04 | NIFTY | 5 | 2.507 s | 2.501 s | 2.826 s |
| 2026-09-04 | SENSEX | 5 | 2.496 s | 2.471 s | 2.608 s |
| 2026-09-03 | NIFTY | 5 | 2.493 s | 2.482 s | 2.562 s |
| 2026-09-03 | SENSEX | 5 | 2.498 s | 2.459 s | 2.522 s |

**Pooled: n=30, median 2.498 s, mean 2.517 s, min 2.454 s, max 2.826 s.**

The distribution is tight — the full range across 30 invocations is 372 ms, and NIFTY and
SENSEX medians differ by 35 ms despite SENSEX carrying ~30% more strikes per cycle. Cost
is dominated by the round-trips, not by strike count.

### 2.3 Extrapolation

Using the measured median of 2.498 s per invocation and the measured cadence from §1.3
(median 83 cycles per day per symbol):

| basis | invocations | at 2.498 s median | wall-clock, serial |
|---|---:|---:|---:|
| one symbol-day | 83 | 207 s | 3.5 min |
| 299 days × 2 symbols × 83 cycles | 49,634 | 123,986 s | **34.4 hours** |
| 247 days × 2 symbols × 83 cycles | 41,002 | 102,423 s | **28.5 hours** |

Three properties of this number, stated so it is not read as more than it is:

- **It excludes write cost entirely** (§2.1). Every invocation in a real backfill would
  additionally upsert one `gamma_metrics` row and ~105–135 `gex_strike_snapshots` rows.
- **It is serial.** No concurrency was measured, and no claim is made about how the figure
  scales with parallel workers.
- **It was measured against `option_chain_snapshots`**, whose reachable history is bounded
  by retention (§4). Chains outside that window are not readable by this code path at all,
  so the extrapolation describes compute cost, not feasibility over the full 299 days.

---

## 3. Era stitching

Every calendar month from the earliest data (2025-04) to today (2026-09), against the five
relations that carry a per-strike intraday chain. Day-scoped `limit=1` probes establish which
weekdays hold rows and whether gamma / spot are non-null anywhere in the month. Cadence and
strike breadth are measured on one **representative day** per month per symbol — the median
populated weekday — by paging that day in full and counting distinct values client-side,
because PostgREST has no `DISTINCT`.

**Unresolved cells: zero.** 24 cells initially failed on the harness's own 60,000-row paging
guard — an instrument limit, not a database limit and not an absence. They were re-measured
with the guard raised to 400,000 and all 24 resolved; the largest legitimately needed ~211,000
rows for a single symbol-day.

### 3.1 The five sources

| relation | strike dim | gamma | spot | symbol key |
|---|---|---|---|---|
| `hist_option_bars_1m` | strike + option_type | column present | **no spot column** | `instrument_id` |
| `hist_option_greeks_1m` | strike + option_type | column present | **no spot column** | `instrument_id` |
| `historical_option_chain_snapshots` | strike + option_type | column present | `spot` | `symbol` |
| `option_chain_snapshots` | strike + option_type | column present | `spot` | `symbol` |
| `gex_strike_snapshots` | strike | `gamma_call`/`gamma_put` | `spot` | `symbol` |

Neither `hist_option_bars_1m` nor `hist_option_greeks_1m` has a spot column — verified against
their live column lists, not their names. A build using either must join spot from
`hist_spot_bars_1m` on `(instrument_id, bar_ts)`.

### 3.2 Month by month

`ts/day` is distinct timestamps on the representative day; `strikes` is distinct strike values
on that same day, across all expiries present.

| month | source | sym | days with rows | ts/day | strikes | gamma | spot |
|---|---|---|---:|---:|---:|---|---|
| 2025-04 | `hob_1m` | NIFTY | 19 | 376 | 118 | no | — *(no column)* |
| 2025-04 | `hob_1m` | SENSEX | 19 | 375 | 139 | no | — *(no column)* |
| 2025-04 | `hog_1m` | NIFTY | 14 | 1 * | 101 | **yes** | — *(no column)* |
| 2025-04 | `hog_1m` | SENSEX | 13 | 1 * | 136 | **yes** | — *(no column)* |
| 2025-05 | `hob_1m` | NIFTY | 21 | 376 | 143 | no | — *(no column)* |
| 2025-05 | `hob_1m` | SENSEX | 21 | 376 | 193 | no | — *(no column)* |
| 2025-05 | `hog_1m` | NIFTY | 17 | 1 * | 95 | **yes** | — *(no column)* |
| 2025-05 | `hog_1m` | SENSEX | 17 | 1 * | 193 | **yes** | — *(no column)* |
| 2025-06 | `hob_1m` | NIFTY | 21 | 376 | 144 | no | — *(no column)* |
| 2025-06 | `hob_1m` | SENSEX | 20 | 375 | 208 | no | — *(no column)* |
| 2025-06 | `hog_1m` | NIFTY | 17 | 1 * | 83 | **yes** | — *(no column)* |
| 2025-06 | `hog_1m` | SENSEX | 16 | 1 * | 166 | **yes** | — *(no column)* |
| 2025-07 | `hob_1m` | NIFTY | 23 | 376 | 116 | no | — *(no column)* |
| 2025-07 | `hob_1m` | SENSEX | 23 | 375 | 144 | no | — *(no column)* |
| 2025-07 | `hog_1m` | NIFTY | 18 | 1 * | 90 | **yes** | — *(no column)* |
| 2025-07 | `hog_1m` | SENSEX | 18 | 1 * | 162 | **yes** | — *(no column)* |
| 2025-08 | `hob_1m` | NIFTY | 19 | 376 | 110 | no | — *(no column)* |
| 2025-08 | `hob_1m` | SENSEX | 19 | 375 | 144 | no | — *(no column)* |
| 2025-08 | `hog_1m` | NIFTY | 15 | 1 * | 91 | **yes** | — *(no column)* |
| 2025-08 | `hog_1m` | SENSEX | 15 | 1 * | 140 | **yes** | — *(no column)* |
| 2025-09 | `hob_1m` | NIFTY | 22 | 376 | 110 | no | — *(no column)* |
| 2025-09 | `hob_1m` | SENSEX | 22 | 375 | 169 | no | — *(no column)* |
| 2025-09 | `hog_1m` | NIFTY | 17 | 1 * | 84 | **yes** | — *(no column)* |
| 2025-09 | `hog_1m` | SENSEX | 18 | 1 * | 168 | **yes** | — *(no column)* |
| 2025-10 | `hob_1m` | NIFTY | 21 | 376 | 105 | no | — *(no column)* |
| 2025-10 | `hob_1m` | SENSEX | 21 | 375 | 181 | no | — *(no column)* |
| 2025-10 | `hog_1m` | NIFTY | 17 | 1 * | 87 | **yes** | — *(no column)* |
| 2025-10 | `hog_1m` | SENSEX | 16 | 1 * | 183 | **yes** | — *(no column)* |
| 2025-11 | `hob_1m` | NIFTY | 19 | 376 | 118 | no | — *(no column)* |
| 2025-11 | `hob_1m` | SENSEX | 19 | 375 | 177 | no | — *(no column)* |
| 2025-11 | `hog_1m` | NIFTY | 15 | 1 * | 89 | **yes** | — *(no column)* |
| 2025-11 | `hog_1m` | SENSEX | 15 | 1 * | 172 | **yes** | — *(no column)* |
| 2025-12 | `hob_1m` | NIFTY | 22 | 376 | 113 | no | — *(no column)* |
| 2025-12 | `hob_1m` | SENSEX | 22 | 375 | 178 | no | — *(no column)* |
| 2025-12 | `hog_1m` | NIFTY | 17 | 1 * | 81 | **yes** | — *(no column)* |
| 2025-12 | `hog_1m` | SENSEX | 18 | 1 * | 174 | **yes** | — *(no column)* |
| 2026-01 | `hob_1m` | NIFTY | 20 | 376 | 101 | no | — *(no column)* |
| 2026-01 | `hob_1m` | SENSEX | 20 | 375 | 175 | no | — *(no column)* |
| 2026-01 | `hog_1m` | NIFTY | 16 | 1 * | 85 | **yes** | — *(no column)* |
| 2026-01 | `hog_1m` | SENSEX | 15 | 1 * | 175 | **yes** | — *(no column)* |
| 2026-02 | `hob_1m` | NIFTY | 20 | 376 | 117 | no | — *(no column)* |
| 2026-02 | `hob_1m` | SENSEX | 20 | 375 | 234 | no | — *(no column)* |
| 2026-02 | `hog_1m` | NIFTY | 16 | 1 * | 93 | **yes** | — *(no column)* |
| 2026-02 | `hog_1m` | SENSEX | 16 | 1 * | 234 | **yes** | — *(no column)* |
| 2026-03 | `hob_1m` | NIFTY | 19 | 376 | 160 | no | — *(no column)* |
| 2026-03 | `hob_1m` | SENSEX | 19 | 375 | 250 | no | — *(no column)* |
| 2026-03 | `hog_1m` | NIFTY | 14 | 1 * | 136 | **yes** | — *(no column)* |
| 2026-03 | `hog_1m` | SENSEX | 15 | 1 * | 245 | **yes** | — *(no column)* |
| 2026-03 | `HOCS` | NIFTY | 5 | 9 | 277 | **yes** | **yes** |
| 2026-03 | `HOCS` | SENSEX | 6 | 9 | 303 | **yes** | **yes** |
| 2026-04 | `HOCS` | NIFTY | 20 | 68 | 249 | **yes** | **yes** |
| 2026-04 | `HOCS` | SENSEX | 20 | 64 | 247 | **yes** | **yes** |
| 2026-05 | `hob_1m` | NIFTY | 2 | 375 | 11 | no | — *(no column)* |
| 2026-05 | `hob_1m` | SENSEX | 2 | 375 | 11 | no | — *(no column)* |
| 2026-05 | `HOCS` | NIFTY | 19 | 42 | 235 | **yes** | **yes** |
| 2026-05 | `HOCS` | SENSEX | 19 | 43 | 201 | **yes** | **yes** |
| 2026-05 | `GSS` | NIFTY | 4 | 74 | 106 | **yes** | **yes** |
| 2026-05 | `GSS` | SENSEX | 4 | 74 | 263 | **yes** | **yes** |
| 2026-06 | `HOCS` | NIFTY | 2 | 74 | 235 | **yes** | **yes** |
| 2026-06 | `HOCS` | SENSEX | 3 | 73 | 191 | **yes** | **yes** |
| 2026-06 | `GSS` | NIFTY | 18 | 83 | 103 | **yes** | **yes** |
| 2026-06 | `GSS` | SENSEX | 19 | 44 | 175 | **yes** | **yes** |
| 2026-07 | `GSS` | NIFTY | 23 | 83 | 93 | **yes** | **yes** |
| 2026-07 | `GSS` | SENSEX | 23 | 83 | 166 | **yes** | **yes** |
| 2026-08 | `OCS` | NIFTY | 6 | 86 | 231 | **yes** | **yes** |
| 2026-08 | `OCS` | SENSEX | 6 | 86 | 196 | **yes** | **yes** |
| 2026-08 | `GSS` | NIFTY | 21 | 64 | 105 | **yes** | **yes** |
| 2026-08 | `GSS` | SENSEX | 21 | 64 | 134 | **yes** | **yes** |
| 2026-09 | `OCS` | NIFTY | 6 | 87 | 227 | **yes** | **yes** |
| 2026-09 | `OCS` | SENSEX | 6 | 86 | 170 | **yes** | **yes** |
| 2026-09 | `GSS` | NIFTY | 6 | 84 | 87 | **yes** | **yes** |
| 2026-09 | `GSS` | SENSEX | 6 | 83 | 130 | **yes** | **yes** |

`*` `hist_option_greeks_1m` is keyed on `trade_date` in this sweep because ordering by its
`bar_ts` returns `57014`, so the ts/day column reads 1 (one distinct date per day) and is a
measurement artefact, not the table's cadence. Measured separately with a `trade_date` filter
and client-side dedupe of `bar_ts`:

```
2025-06-16  NIFTY 376   SENSEX 375
2025-10-16  NIFTY 376   SENSEX 0      (day not covered by the sidecar)
2026-01-15  NIFTY 0     SENSEX 0      (day not covered)
2026-03-16  NIFTY 359   SENSEX 375
```

So the sidecar is 1-minute, like the chain it sits beside, on the days it covers.

### 3.3 Months where no source qualifies for a per-strike GEX

A source qualifies if it carries a strike dimension **and** non-null gamma. Naming the
specific object checked in each case:

| month | what each source returned | qualifies? |
|---|---|---|
| 2025-04 → 2026-03 | `hist_option_bars_1m` gamma **no** on every probed day; `hist_option_greeks_1m` gamma **yes** but on 13–18 of the ~20 weekdays only; `HOCS`/`OCS`/`GSS` zero rows | **partial** — only on sidecar days |
| 2026-04 | `hist_option_bars_1m` zero rows (22 weekdays probed); `hist_option_greeks_1m` zero rows; `HOCS` gamma **yes**, 20 days; `OCS`/`GSS` zero rows | yes, via HOCS |
| 2026-05 | `hist_option_bars_1m` 2 days, gamma **no**; `HOCS` 19 days gamma **yes**; `GSS` 4 days gamma **yes** | yes |
| 2026-06 | `HOCS` 2–3 days; `GSS` 18–19 days gamma **yes** | yes |
| 2026-07 | `GSS` 23 days gamma **yes**; every other source zero rows | yes, GSS only |
| 2026-08, 2026-09 | `OCS` 6 days + `GSS` 21/6 days, both gamma **yes** | yes |

**No calendar month in the range has zero qualifying sources.** The 2025-04 → 2026-03 era
qualifies only on the days `hist_option_greeks_1m` covers — 193 NIFTY / 192 SENSEX days
against 246 / 245 days where the chain has rows, per the S75 data inventory.

### 3.4 Boundaries where cadence or strike coverage changes between sources

| boundary | what changes |
|---|---|
| **2026-03-16** | `HOCS` begins while `hist_option_bars_1m` / `hist_option_greeks_1m` are still running. Cadence drops from **~376/day (1-minute)** to **9/day** in the partial first month, then 64–68/day. Strike breadth *rises*: NIFTY 160 → 277, SENSEX 250 → 303. |
| **2026-03-30** | `hist_option_greeks_1m` stops. This is the last date any 1-minute gamma source exists. |
| **2026-04-01** | `hist_option_bars_1m` has zero rows for the whole month; it resumes for exactly 2 days in May. HOCS is the only chain source in April. |
| **2026-05-25** | `GSS` begins, overlapping HOCS. Cadence differs between them on the same days — HOCS 42–43/day, GSS 74/day. Strike breadth differs sharply: HOCS 235/201, GSS 106/263. |
| **2026-06-03** | `HOCS` stops. `GSS` is the sole source for 2026-06-04 → 2026-08-23. |
| **2026-08-24** | `OCS` begins, overlapping GSS. OCS carries ~2× the strikes of GSS on the same days (NIFTY 231 vs 105, SENSEX 196 vs 134) at similar cadence (86 vs 64–84). |

The strike-breadth differences at the 2026-05-25 and 2026-08-24 boundaries are the largest
discontinuities in the table. `GSS` holds one row per strike; `HOCS` and `OCS` hold one row
per strike **per option type**, and `GSS` is a computed product of a chain rather than a
capture of one, so the two are not counting the same thing.


---

## 4. Retention

### 4.1 The enumeration is complete, and it required the SQL editor

**Every pg_cron job was enumerated with its `prosrc`.** The operator ran
`cron.job LEFT JOIN pg_proc` on the command, in the Supabase SQL editor, returning every
job with its schedule, active flag and function body.

**Result: exactly two jobs delete anything.**

| jobid | schedule | active | what it deletes |
|---|---|---|---|
| **19** | `30 12 * * *` | yes | four targets — see §4.2 |
| **46** | `*/30 * * * 1-5` | yes | `DELETE FROM public.market_ticks WHERE ts < now() - interval '1 hour'` |

Every other job is one of two shapes, neither of which deletes:

- `net.http_post` to an edge function;
- `build_market_breadth_latest`, whose `prosrc` reads `equity_eod` and calls
  `build_market_breadth_daily`, with no delete statement.

**This could not be obtained through PostgREST**, which is worth recording because it
determines how the question must be asked next time. The objects queried and their
responses:

```
GET /rest/v1/job              -> 404 PGRST205  Could not find the table 'public.job'
GET /rest/v1/job_run_details  -> 404 PGRST205
GET /rest/v1/cron_job         -> 404 PGRST205
GET /rest/v1/cron.job         -> 404 PGRST205
```

The `cron` schema is not among the schemas PostgREST exposes, no RPC in the published list
of 38 wraps a catalog read, and `pg_proc` is likewise absent from the OpenAPI definitions.
Anything about pg_cron requires the SQL editor; that is a standing constraint on this
access path, not a one-off.

### 4.2 The four-target cleanup — jobid 19

Supplied by the operator, read from `pg_proc.prosrc` in the Supabase SQL editor:

```
pg_cron jobid 19, active, schedule "30 12 * * *"      -- 12:30 UTC daily
command:  select public.cleanup_gamma_engine_data();
```

| target table | predicate | interval | effect |
|---|---|---|---|
| `option_chain_snapshots` | `created_at <` | 90 days | hard delete |
| `option_chain_snapshots` | `created_at` between 90 and 14 days ago | — | deletes every row **except** `extract(hour from created_at)=10 AND extract(minute from created_at)=0` |
| `raw_ingest_log` | `ts <` | 14 days | hard delete |
| `gamma_metrics` | `created_at <` | 90 days | hard delete |

Note the predicate column differs between them: `created_at` for the two snapshot tables
and for `gamma_metrics`, `ts` for `raw_ingest_log`.

### 4.3 Corroboration in the data

Both rules are visible without reading the function. Cycles per day in
`option_chain_snapshots` across its entire range, `count=exact` for rows and full paging
for distinct `ts`:

| date | age at measurement | rows | distinct ts |
|---|---:|---:|---:|
| 2026-08-24 | 16 d | 880 | **2** |
| 2026-08-25 | 15 d | 880 | **2** |
| 2026-08-26 | 14 d | 73,444 | **172** |
| 2026-08-27 | 13 d | 73,444 | 172 |
| 2026-08-28 | 12 d | 68,972 | 172 |
| 2026-08-31 | 9 d | 68,170 | 170 |
| 2026-09-01 | 8 d | 68,972 | 172 |
| 2026-09-02 | 7 d | 66,810 | 170 |
| 2026-09-03 | 6 d | 68,112 | 172 |
| 2026-09-04 | 5 d | 68,738 | 173 |
| 2026-09-07 | 2 d | 67,490 | 170 |
| 2026-09-08 | 1 d | 68,456 | 172 |

The break is exactly at 14 days. Days aged 15 and 16 hold **2** distinct timestamps — one
10:00 UTC snapshot for each of the two symbols — against 170–173 for every day inside the
window. 2026-08-29/30 and 2026-09-05/06 are Saturdays and Sundays and hold zero rows.

`raw_ingest_log`'s lower bound is `2026-08-26T03:46:01`, which is 14 days before the
measurement date. That matches its stated interval exactly.

### 4.4 Which build source tables are trimmed, and which are not

Measured lower bounds, with age at 2026-09-09:

| table | min | age | trimmed? |
|---|---|---:|---|
| `option_chain_snapshots` | 2026-08-24T10:00:05 | 16 d | **yes** — named in jobid 19; 90-day delete + 14-day thinning, both corroborated in §4.3 |
| `gamma_metrics` | 2026-06-10T10:55:05 | 91 d | **yes** — named in jobid 19; the S75 capture recorded its lower bound advancing within one day |
| `raw_ingest_log` | 2026-08-26T03:46:01 | 14 d | **yes** — named in jobid 19 |
| `historical_option_chain_snapshots` | 2026-03-16T09:51:09 | 177 d | **no** — named in no pg_cron job; retains rows 177 days old |
| `gex_strike_snapshots` | 2026-05-25T09:56:07 | 107 d | **no** — named in no pg_cron job; retains rows 107 days old |
| `market_spot_snapshots` | 2026-02-15T03:51:40 | 206 d | **no** — named in no pg_cron job; retains 206-day-old rows |
| `volatility_snapshots` | 2025-04-01T03:45:00 | 526 d | **no** — named in no pg_cron job; retains 526-day-old rows |
| `hist_option_bars_1m` | 2025-04-01T09:15:59 | 526 d | **no** — named in no pg_cron job; retains 526-day-old rows |
| `hist_option_greeks_1m` | 2025-04-01 | 526 d | **no** — named in no pg_cron job; retains 526-day-old rows |
| `hist_spot_bars_1m` | 2025-04-01 | 526 d | **no** — named in no pg_cron job; retains 526-day-old rows |
| `hist_gamma_metrics` | 2025-04-01 | 526 d | **no** — named in no pg_cron job; retains 526-day-old rows |

The "not trimmed" claims rest on the complete job enumeration in §4.1 — these tables are
named in **no** pg_cron job that deletes — corroborated by the positive measurement that
each retains data well past any 90-day boundary. Only jobs 19 and 46 delete anything, so
there is no longer-interval job that could be trimming them.

Jobid 46 is the other deleter: `*/30 * * * 1-5`, `DELETE FROM public.market_ticks WHERE ts
< now() - interval '1 hour'`. `market_ticks` is not a source for this build.

One non-deleting job carries a defect worth recording. Jobid 30 (`38 3 * * 1-5`, active)
builds its header with `jsonb_build_object('Content-Type','application/json','<secret>')`
— three arguments to a function taking alternating key/value pairs, so the secret is a key
with no value. It is a `net.http_post` job and deletes nothing.

---

## 5. Cadence

### 5.1 What the variation actually is

Every trading day of two months, `gex_strike_snapshots`, distinct `ts` per symbol by full
client-side paging:

**2026-08** — 82, 83, 83, 83, 82, 82, 83, 83, 84, **64**, 81, 83, 83, 83, 84, 83, 83, 83,
83, 82 (NIFTY), and **73** on 08-03. SENSEX tracks NIFTY within ±1 on every day.

**2026-06** — 72, 74, **0, 0, 1, 0**, 28, 12, **0**, 16, 47, 49, 45, 83, 83, 82, 83, 84,
83, **15**, 84, 84 (NIFTY).

So the steady state is **82–84 cycles per day per symbol**, which is what a 5-minute
cadence over the 03:00–09:59 UTC cron window produces (7 hours × 12 = 84). The 47–75 band
is not a separate regime; it is the ramp in mid-June plus isolated short days.

### 5.2 Correlation 1 — the retention thinning does not explain it

The 14-day thinning in §4.3 applies to `option_chain_snapshots` and reduces an affected
day to **2** distinct timestamps, not to 47–75. `gex_strike_snapshots` is named in **no**
pg_cron job that deletes (§4.1, complete enumeration) and retains 107-day-old rows, so no
thinning or trimming of any kind acts on the table these cadence figures come from.
**Ruled out by measurement, not by argument.**

### 5.3 Correlation 2 — the trading calendar explains one day and refutes itself on the rest

`GET /trading_calendar?select=trade_date,is_open,holiday_name,is_special_session,open_time,close_time&trade_date=in.(...)`:

| date | cycles | `is_open` | open/close |
|---|---:|---|---|
| 2026-06-26 | 15 | **false** | null / null |
| 2026-06-01 | 72 | true | 09:15 / 15:30 |
| 2026-06-15 | 47 | true | 09:15 / 15:30 |
| 2026-06-16 | 49 | true | 09:15 / 15:30 |
| 2026-06-17 | 45 | true | 09:15 / 15:30 |
| 2026-08-03 | 73 | true | 09:15 / 15:30 |
| 2026-08-17 | 64 | true | 09:15 / 15:30 |

One day is explained: **2026-06-26 is `is_open=false` and the pipeline wrote 15 cycles
anyway.** Every other low day carries `is_open=true` with standard 09:15–15:30 hours, so
the calendar does not account for them. `is_special_session` is `false` on all of them, so
no short-session mechanism is recorded either.

Two dates in the sample have **no row at all** in `trading_calendar` —
`?trade_date=eq.2026-06-09` and `eq.2026-06-12` each return zero rows. Both are days with
partial cycle counts (28 and 16). The table's own coverage begins 2026-03-25, so it cannot
speak to any date before that.

### 5.4 Correlation 3 — the execution log explains it exactly

`script_execution_log` holds **228,220 rows** (`count=exact`) and does instrument both the
writer and the ingest. Runs per day, with exit reasons, against cycles written:

| date | `compute_gamma_metrics_local.py` runs | exit reasons | cycles (N+S) |
|---|---:|---|---:|
| 2026-08-19 | 168 | SUCCESS 168 | 83 + 83 = 166 |
| 2026-08-18 | 164 | SUCCESS 164 | 81 + 81 = 162 |
| 2026-08-03 | 146 | SUCCESS 146 | 73 + 73 = **146** |
| 2026-08-17 | 130 | SUCCESS 130 | 64 + 64 = **128** |
| 2026-06-18 | 168 | SUCCESS 168 | 83 + 83 = 166 |
| 2026-06-17 | 168 | SUCCESS 168 | 45 + 44 = 89 |
| 2026-06-16 | 89 | SUCCESS 89 | 49 + 36 = 85 |
| 2026-06-15 | 84 | SUCCESS 84 | 47 + 25 = 72 |
| 2026-06-01 | 296 | **SUCCESS 146, DATA_ERROR 150** | 72 + 74 = **146** |
| 2026-06-26 | 36 | SUCCESS 36 | 15 + 15 = 30 |
| 2026-06-10 | 40 | SUCCESS 39, SKIPPED_NO_INPUT 1 | 12 + 9 = 21 |

**Cycles written track successful writer invocations.** 2026-08-03 is the cleanest case:
146 runs, 146 SUCCESS, 146 cycles. 2026-06-01 is the most informative: 296 invocations of
which **150 exited `DATA_ERROR`**, and exactly the 146 successes appear as cycles.

So the answer to the variation is that the writer ran fewer times, or ran and failed —
not that anything removed rows afterwards. The mid-June band (45–49) coincides with days
where the writer ran 84–168 times against a steady-state 168.

### 5.5 A measurement of mine that was wrong

While hunting the `gamma_metrics` deleter, I measured `script_execution_log` and reported
that it showed "four distinct `script_name` values in the last 30 days", offering it as
weak evidence that no cleanup script runs. **That figure is wrong.** It came from
`?select=script_name&started_at=gte.<30d>&limit=1000`, which returns an arbitrary
unordered 1,000 rows out of **228,220** — a paging artefact, not a census. The table is
well instrumented, and both `compute_gamma_metrics_local.py` and
`ingest_option_chain_local.py` appear in it, which is what made §5.4 possible at all.

Two things about where that error did and did not land, both checked rather than assumed:

- It was **not** written into `capture_s75.md`. `/usr/bin/grep -c "script_execution_log"`
  returns 0 against both the working tree and the committed blob
  (`git show b5886d4:docs/session_notes/capture_s75.md`). The claim was made in session
  and did not reach the register.
- The conclusion it was offered for — that no cleanup script runs on the host — stands,
  but for a different and stronger reason: §4.1's complete pg_cron enumeration shows the
  deleter is a database job with no script at all. The conclusion survived; the evidence
  originally given for it did not support it.

---

## 6. Vendor greeks

### 6.1 The date range where `hist_option_bars_1m` carries non-null gamma and iv

**There is none.** Stratified re-verification, one representative populated weekday per
month across the table's entire range, both symbols, day-scoped `limit=1` probes with
`57014` resolved by narrowing to half- then quarter-day scope:

```
GET /hist_option_bars_1m?select=gamma&bar_ts=gte.<day>&bar_ts=lt.<day+1>
    &instrument_id=eq.<uuid>&gamma=not.is.null&limit=1
```

| month | rep day | gamma | iv | oi |
|---|---|---|---|---|
| 2025-04 | 2025-04-02 | no | no | **yes** |
| 2025-05 | 2025-05-05 | no | no | yes |
| 2025-06 | 2025-06-03 | no | no | yes |
| 2025-07 | 2025-07-02 | no | no | yes |
| 2025-08 | 2025-08-04 | no | no | yes |
| 2025-09 | 2025-09-02 | no | no | yes |
| 2025-10 | 2025-10-03 | no | no | yes |
| 2025-11 | 2025-11-04 | no | no | yes |
| 2025-12 | 2025-12-02 | no | no | yes |
| 2026-01 | 2026-01-02 | no | no | yes |
| 2026-02 | 2026-02-03 | no | no | yes |
| 2026-03 | 2026-03-04 | no | no | yes |
| 2026-04 | — | *no populated weekday found in 22 probes* | | |
| 2026-05 | 2026-05-07 | no | no | yes |

**Unresolved cells: zero.** Both symbols returned identical results on every month.

This agrees with the exhaustive sweep in the S75 data inventory, which probed **all 289
weekdays** from 2025-04-01 to 2026-05-08 for both symbols and found gamma and iv non-null
on **zero** of them, with two initially-timed-out cells (2025-05-28 and 2025-06-26, NIFTY)
resolved to false at half-day scope.

`oi` is non-null on every populated day. The columns exist in the table — they are listed
in its live column set — and hold no non-null value anywhere in its range.

### 6.2 Which source covers which era

| era | per-strike gamma source | cadence | spot |
|---|---|---|---|
| 2025-04-01 → 2026-03-30 | `hist_option_greeks_1m` — 193 NIFTY / 192 SENSEX days out of 246 / 245 chain days | 1-minute (359–376 distinct `bar_ts` per covered day) | not in table; join `hist_spot_bars_1m` on `(instrument_id, bar_ts)` |
| 2026-03-16 → 2026-06-03 | `historical_option_chain_snapshots` | 9/day in the partial first month, then 42–68/day | `spot` in the same row |
| 2026-05-25 → present | `gex_strike_snapshots` | 82–84/day steady state | `spot` in the same row |
| 2026-08-24 → present | `option_chain_snapshots` | ~86/day, subject to 14-day thinning to 1/day (§4.3) | `spot` in the same row |

`hist_option_bars_1m` covers 2025-04-01 → 2026-05-07 and supplies **open interest, strike,
option_type, expiry and premium** across that range — it is a source for everything except
the greeks. Its `oi` is what `hist_option_greeks_1m`'s gamma must be joined to, on
`(instrument_id, bar_ts, expiry_date, strike, option_type)`; both tables carry all five.
