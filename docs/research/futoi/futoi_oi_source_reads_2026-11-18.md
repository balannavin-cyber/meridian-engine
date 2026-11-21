# Futures OI source reads — 2026-11-18

Read-only reads of the futures tables, run through `bin/roq.sh` as `merdian_ro`,
one query per invocation, fed on stdin, at the pinned 30 s statement timeout
(never raised). Nothing was written to the database. No query timed out.

This file is **outside** the `SHA256SUMS` manifest of the closed M1/M2 run; that
manifest was not regenerated.

Each section states what the read shows and nothing more.

---

## 1. Column lists

### `historical_index_futures_1m`

| column_name | data_type |
|---|---|
| id | uuid |
| ts | timestamp with time zone |
| symbol | text |
| contract_code | text |
| security_id | text |
| expiry_date | date |
| ltp | numeric |
| open_interest | bigint |
| volume | bigint |
| basis | numeric |
| basis_pct | numeric |
| source | text |
| created_at | timestamp with time zone |

### `index_futures_snapshots`

| column_name | data_type |
|---|---|
| id | bigint |
| ts | timestamp with time zone |
| symbol | text |
| contract_symbol | text |
| expiry_date | date |
| expiry_type | text |
| spot_price | numeric |
| futures_price | numeric |
| basis | numeric |
| basis_pct | numeric |
| source | text |
| raw | jsonb |
| created_at | timestamp with time zone |

**What this shows.** `historical_index_futures_1m` carries an `open_interest`
column; `index_futures_snapshots` does not carry one at all. The two tables share
`ts`, `symbol`, `expiry_date`, `basis`, `basis_pct`, `source` and `created_at`.
`index_futures_snapshots` carries `spot_price` and `futures_price` as separate
columns and a `raw` jsonb; `historical_index_futures_1m` carries a single `ltp`
plus `volume`, `contract_code` and `security_id`.

---

## 2. `index_futures_snapshots` — the three most recent rows

| id | ts | symbol | contract_symbol | expiry_date | expiry_type | spot_price | futures_price | basis | basis_pct | source | created_at | raw is null |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 33261 | 2026-11-18 10:30:06.278572+00 | NIFTY | NIFTY NOV FUT | 2026-11-23 | *(empty)* | 25227.95 | 25234.3 | 6.349999999998545 | 0.025170495422729727 | dhan_ltp_dynamic_contract_resolution | 2026-11-18 10:30:06.546742+00 | f |
| 33262 | 2026-11-18 10:30:06.278572+00 | SENSEX | SENSEX NOV  FUT | 2026-11-26 | *(empty)* | 82031.81 | 82096.3 | 64.49000000000524 | 0.0786158442682238 | dhan_ltp_dynamic_contract_resolution | 2026-11-18 10:30:06.546742+00 | f |
| 33260 | 2026-11-18 10:10:07.808078+00 | NIFTY | NIFTY NOV FUT | 2026-11-23 | *(empty)* | 25227.95 | 25234.3 | 6.349999999998545 | 0.025170495422729727 | dhan_ltp_dynamic_contract_resolution | 2026-11-18 10:10:08.109424+00 | f |

**What this shows.** The two most recent rows share one `ts` and differ by
symbol. `source` is `dhan_ltp_dynamic_contract_resolution` on all three.
`expiry_type` is empty on all three. `raw` is non-null on all three.
`contract_symbol` for SENSEX contains two spaces (`SENSEX NOV  FUT`). The NIFTY
`spot_price`, `futures_price`, `basis` and `basis_pct` are identical at
10:10:07 and 10:30:06.

### `raw` keys and value types

Identical across all three rows:

| key | value_type |
|---|---|
| display_name | string |
| expiry_date | string |
| marketfeed_segment | string |
| security_id | number |
| spot_security_id | number |
| spot_source | string |

### One full `raw` value (id 33261)

```json
{
    "expiry_date": "2026-11-23",
    "security_id": 61471,
    "spot_source": "dhan_ltp_idx_i_same_request",
    "display_name": "NIFTY NOV FUT",
    "spot_security_id": 13,
    "marketfeed_segment": "NSE_FNO"
}
```

**What this shows.** `raw` holds six keys, all scalars, with no nested object or
array. It carries no open-interest key. `spot_source` records that the spot was
taken from the same request as the futures quote.

---

## 3. `historical_index_futures_1m` — open_interest coverage by symbol and month

| symbol | ym | rows | oi_not_null | oi_gt_zero | ts_min | ts_max |
|---|---|---|---|---|---|---|
| NIFTY | 2026-03 | 1334 | 0 | 0 | 2026-03-19 09:58:04.018308+00 | 2026-03-30 10:30:09.902094+00 |
| NIFTY | 2026-06 | 8 | 0 | 0 | 2026-06-18 10:30:06.872834+00 | 2026-06-30 10:30:06.646402+00 |
| NIFTY | 2026-07 | 22 | 0 | 0 | 2026-07-01 10:30:07.92422+00 | 2026-07-30 10:30:04.213125+00 |
| NIFTY | 2026-08 | 17 | 0 | 0 | 2026-08-03 10:30:04.880161+00 | 2026-08-31 10:30:04.971999+00 |
| NIFTY | 2026-09 | 21 | 0 | 0 | 2026-09-01 10:30:05.077561+00 | 2026-09-30 10:30:06.295267+00 |
| NIFTY | 2026-10 | 20 | 0 | 0 | 2026-10-01 10:30:06.825681+00 | 2026-10-30 10:30:06.407066+00 |
| NIFTY | 2026-11 | 12 | 0 | 0 | 2026-11-02 10:30:06.73073+00 | 2026-11-18 10:30:06.278572+00 |
| SENSEX | 2026-03 | 1334 | 0 | 0 | 2026-03-19 09:58:04.018308+00 | 2026-03-30 10:30:09.902094+00 |
| SENSEX | 2026-06 | 8 | 0 | 0 | 2026-06-18 10:30:06.872834+00 | 2026-06-30 10:30:06.646402+00 |
| SENSEX | 2026-07 | 22 | 0 | 0 | 2026-07-01 10:30:07.92422+00 | 2026-07-30 10:30:04.213125+00 |
| SENSEX | 2026-08 | 19 | 0 | 0 | 2026-08-03 10:30:04.880161+00 | 2026-08-31 10:30:04.971999+00 |
| SENSEX | 2026-09 | 21 | 0 | 0 | 2026-09-01 10:30:05.077561+00 | 2026-09-30 10:30:06.295267+00 |
| SENSEX | 2026-10 | 20 | 0 | 0 | 2026-10-01 10:30:06.825681+00 | 2026-10-30 10:30:06.407066+00 |
| SENSEX | 2026-11 | 12 | 0 | 0 | 2026-11-02 10:30:06.73073+00 | 2026-11-18 10:30:06.278572+00 |

**What this shows.** 14 groups. `oi_not_null` is **0** and `oi_gt_zero` is **0**
in every group: the `open_interest` column is null on every row of this table.
Months present are 2026-03 and 2026-06 through 2026-11; there is no 2026-04 or
2026-05 group. NIFTY and SENSEX share identical `ts_min` and `ts_max` in every
month, and identical row counts in every month except 2026-08 (NIFTY 17,
SENSEX 19). The 2026-03 group holds 1334 rows against 8–22 in each later month.

---

## 4. Tables matching `%fyers%` or `%fut%`

```
table_schema, table_name,                   table_type
public,       hist_future_bars_1m,          BASE TABLE
public,       historical_index_futures_1m,  BASE TABLE
public,       index_futures_snapshots,      BASE TABLE
```

**What this shows.** Three tables match, all in `public`, all base tables —
**none visible to `merdian_ro` via `information_schema.tables`** has `fyers` in
its name. The three matches are the two already read above plus
`hist_future_bars_1m`. See §6: the catalog read through `pg_class` returns more
relations than this, because `information_schema` shows only relations the
calling role holds a privilege on.

### `hist_future_bars_1m` columns

| column_name | data_type |
|---|---|
| id | uuid |
| instrument_id | uuid |
| trade_date | date |
| bar_ts | timestamp with time zone |
| expiry_date | date |
| contract_series | smallint |
| open | numeric |
| high | numeric |
| low | numeric |
| close | numeric |
| volume | bigint |
| oi | bigint |
| ingest_batch_id | uuid |
| is_pre_market | boolean |
| is_leap | boolean |

**What this shows.** The open-interest column here is named **`oi`**, not
`open_interest`. There is no `symbol` column — the instrument is carried as
`instrument_id` (uuid). It carries `contract_series` and OHLC, which neither
other table has.

### `hist_future_bars_1m` — open-interest coverage by symbol and month

`instrument_id` mapped to symbol in SQL: `9992f600-…` → NIFTY,
`73a1390a-…` → SENSEX. Grouped on `trade_date`.

| symbol | ym | rows | oi_not_null | oi_gt_zero | ts_min | ts_max |
|---|---|---|---|---|---|---|
| NIFTY | 2025-04 | 20381 | 20381 | 20381 | 2025-04-01 09:15:59+00 | 2025-04-30 15:30:59+00 |
| NIFTY | 2025-05 | 22561 | 22561 | 22558 | 2025-05-02 09:15:59+00 | 2025-05-30 15:30:59+00 |
| NIFTY | 2025-06 | 22384 | 22384 | 22384 | 2025-06-02 09:15:59+00 | 2025-06-30 15:30:59+00 |
| NIFTY | 2025-07 | 23651 | 23651 | 23651 | 2025-07-01 09:15:59+00 | 2025-07-31 15:30:59+00 |
| NIFTY | 2025-08 | 19752 | 19752 | 19749 | 2025-08-01 09:15:59+00 | 2025-08-29 15:30:59+00 |
| NIFTY | 2025-09 | 22588 | 22588 | 22588 | 2025-09-01 09:15:59+00 | 2025-09-30 15:30:59+00 |
| NIFTY | 2025-10 | 21306 | 21306 | 21306 | 2025-10-01 09:15:59+00 | 2025-10-31 15:29:59+00 |
| NIFTY | 2025-11 | 19847 | 19847 | 19846 | 2025-11-03 09:15:59+00 | 2025-11-28 15:29:59+00 |
| NIFTY | 2025-12 | 22999 | 22999 | 22999 | 2025-12-01 09:15:59+00 | 2025-12-31 15:30:59+00 |
| NIFTY | 2026-01 | 21291 | 21291 | 21290 | 2026-01-01 09:15:59+00 | 2026-01-30 15:30:59+00 |
| NIFTY | 2026-02 | 22147 | 22147 | 22147 | 2026-02-01 09:15:59+00 | 2026-02-27 15:30:59+00 |
| NIFTY | 2026-03 | 21219 | 21219 | 21219 | 2026-03-02 09:15:59+00 | 2026-03-30 15:30:59+00 |
| SENSEX | 2025-05 | 9520 | 9520 | 9513 | 2025-05-02 09:17:59+00 | 2025-05-30 15:29:59+00 |
| SENSEX | 2025-06 | 9400 | 9400 | 9389 | 2025-06-02 09:15:59+00 | 2025-06-30 15:29:59+00 |
| SENSEX | 2026-01 | 7845 | 7845 | 7844 | 2026-01-01 09:07:59+00 | 2026-01-30 15:29:59+00 |
| SENSEX | 2026-02 | 7923 | 7923 | 7920 | 2026-02-01 09:15:59+00 | 2026-02-27 15:29:59+00 |
| SENSEX | 2026-03 | 10106 | 10106 | 10104 | 2026-03-02 09:07:59+00 | 2026-03-30 15:29:59+00 |

**What this shows.** 17 groups. `oi_not_null` equals `rows` in every group: `oi`
is non-null on every row. `oi_gt_zero` is below `rows` in 9 of the 17 groups, by
1 to 11 rows. NIFTY covers 2025-04 through 2026-03 continuously. SENSEX appears
in 5 months only — 2025-05, 2025-06, 2026-01, 2026-02, 2026-03 — with no rows in
2025-04 or in 2025-07 through 2025-12. Several `ts_max` values are `15:30:59`
and several are `15:29:59`. Two SENSEX groups have a `ts_min` of `09:07:59`.

---

## 5. Why `historical_index_futures_1m.open_interest` is null on every row

**Answered from code only.** The writer is in the repo. No inference is made
beyond what the quoted lines say.

**The writer.** `archive_market_tape_history.py`, function `archive_futures()`:

```
archive_market_tape_history.py:119   def archive_futures() -> int:
archive_market_tape_history.py:123           row = _latest_row_by_symbol("index_futures_snapshots", symbol)
archive_market_tape_history.py:153                   "open_interest": row.get("open_interest") or row.get("oi"),
archive_market_tape_history.py:157                   "source": "run_market_tape_1m",
archive_market_tape_history.py:161       _upsert_rows(
archive_market_tape_history.py:162           "historical_index_futures_1m",
archive_market_tape_history.py:164           on_conflict="symbol,ts",
```

So every row of `historical_index_futures_1m` is built from **a row of
`index_futures_snapshots`** (`:123`), and `open_interest` is set at `:153` by
reading the keys `open_interest` then `oi` off that source row.

**The source row has neither key.** `index_futures_snapshots` has 13 columns
(§1): `id, ts, symbol, contract_symbol, expiry_date, expiry_type, spot_price,
futures_price, basis, basis_pct, source, raw, created_at`. Neither
`open_interest` nor `oi` is among them, so both `row.get()` calls at `:153`
return `None` and the expression yields `None`.

**The source table's own writer never collects open interest.**
`capture_index_futures_snapshot_local.py` builds the rows it inserts:

```
capture_index_futures_snapshot_local.py:25    #   public.index_futures_snapshots.
capture_index_futures_snapshot_local.py:370           rows.append(
capture_index_futures_snapshot_local.py:372                   "ts": capture_ts,
capture_index_futures_snapshot_local.py:377                   "futures_price": futures_price,
capture_index_futures_snapshot_local.py:380                   "source": "dhan_ltp_dynamic_contract_resolution",
capture_index_futures_snapshot_local.py:381                   "raw": {
capture_index_futures_snapshot_local.py:382                       "security_id": contract["security_id"],
capture_index_futures_snapshot_local.py:383                       "marketfeed_segment": contract["marketfeed_segment"],
capture_index_futures_snapshot_local.py:384                       "display_name": contract["display_name"],
capture_index_futures_snapshot_local.py:385                       "expiry_date": contract["expiry_date"],
capture_index_futures_snapshot_local.py:386                       "spot_source": "dhan_ltp_idx_i_same_request",
capture_index_futures_snapshot_local.py:387                       "spot_security_id": INDEX_SECURITY_IDS[symbol],
capture_index_futures_snapshot_local.py:443       supabase_insert_rows("index_futures_snapshots", rows)
```

The row literal at `:370-390` contains **no open-interest field**, and the `raw`
payload at `:381-388` holds six keys, none of them open interest — which matches
the six keys measured in §2.

**The feed.** `source` is `"dhan_ltp_dynamic_contract_resolution"` at capture
(`capture_index_futures_snapshot_local.py:380`) and the `raw` key `spot_source`
records `"dhan_ltp_idx_i_same_request"` (`:386`). The archiver **overwrites**
`source` with `"run_market_tape_1m"` when it writes the historical row
(`archive_market_tape_history.py:157`), so the historical table does not carry
the capturing feed's own source string.

**What this shows.** The null is not a load failure. The column is populated by
an expression (`:153`) that reads two keys which the source row does not have,
because the capture path that produces that source row
(`capture_index_futures_snapshot_local.py:370-390`) is an LTP capture that never
requests or stores open interest. Nothing in the quoted code writes a non-null
`open_interest` to `historical_index_futures_1m`.

---

## 6. Catalog read through `pg_class`, with `merdian_ro` select privilege

```
nspname, relname,                                relkind, ro_can_select
public,  fyers_chain_bars_1m,                    r,       f
public,  fyers_chain_bars_1m_pkey,               i,       f
public,  fyers_chain_bars_3m,                    r,       f
public,  fyers_chain_bars_3m_pkey,               i,       f
public,  fyers_chain_bars_3m_underlying_ts_idx,  i,       f
public,  fyers_futures_bars_1m,                  r,       f
public,  fyers_futures_bars_1m_pkey,             i,       f
public,  fyers_futures_bars_1m_underlying_ts_idx,i,       f
public,  hist_future_bars_1m,                    r,       t
public,  hist_future_bars_1m_pkey,               i,       f
public,  hist_future_bars_unique,                i,       f
public,  historical_index_futures_1m,            r,       t
public,  historical_index_futures_1m_pkey,       i,       f
public,  historical_index_futures_1m_symbol_ts_key, i,    f
public,  idx_hist_fut_symbol_ts,                 i,       f
public,  idx_hist_future_ts,                     i,       f
public,  idx_index_futures_snapshots_created_at, i,       f
public,  idx_index_futures_snapshots_symbol_ts,  i,       f
public,  index_futures_snapshots,                r,       t
public,  index_futures_snapshots_id_seq,         S,       f
public,  index_futures_snapshots_pkey,           i,       f
```

**What this shows.** 21 relations match, of which 6 are ordinary tables
(`relkind = r`); the rest are indexes (`i`) and one sequence (`S`).

**Three Fyers tables exist and were not visible in §4:**
`fyers_chain_bars_1m`, `fyers_chain_bars_3m` and `fyers_futures_bars_1m`, all
`relkind = r` in `public`. §4's `information_schema.tables` read did not return
them because `information_schema` lists only relations the calling role holds a
privilege on; `pg_class` is not filtered that way.

**`has_table_privilege('merdian_ro', …, 'select')` is `f` — false — on all three
Fyers tables.** It is `t` only on `hist_future_bars_1m`,
`historical_index_futures_1m` and `index_futures_snapshots`, the three already
read in this file.

**`merdian_ro` cannot read any Fyers table, so the read stops here.** No
columns and no open-interest coverage are reported for
`fyers_chain_bars_1m`, `fyers_chain_bars_3m` or `fyers_futures_bars_1m`. No
privilege was escalated and no other role was used.

---

*Produced 2026-11-18. Eight queries, each a separate `roq.sh` invocation on
stdin, plus repo greps for §5. No database write, no role change, no privilege
escalation. No file written outside `docs/research/futoi/`. The closed run's
`SHA256SUMS` was not regenerated and does not cover this file.*
