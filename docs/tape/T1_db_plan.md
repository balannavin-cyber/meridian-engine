# Tape T1-db — Supabase sidecar tables, contracts, access, offline loader (plan)

Phase T1-db of the MERIDIAN tape layer. Worktree `C:\wt-tape-b`, branch `tape/t1-db`, cut from `tape/t1b` at `2335026`.
Planned on Opus 2026-11-03; build on Sonnet in the same session (no `/clear` between).

**Pre-registration v0.2** (sha256 `71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800`) binds this phase:
the sidecar stores the tape side (`tape_minute`, `tape_strike_cycle`, `tape_events`, `tape_daily_report`) and the chain
side (`tape_chain_events`, `tape_chain_runs`) as **separate relations**. No view, function, trigger, generated column or
loader step joins them. The scoring SQL (a later phase, hashed before its first run) is the only join.

**Scope (binding).** Claude writes the migration SQL, the post-apply check and the loader. Claude never connects to the
database, never reads `.env`, never calls Supabase. The operator applies and runs. Tests use fakes. Nothing here is
imported by `services/tape_runner/` or shipped by `install.sh`. No order placement code.

---

## 0. Housekeeping (measured 2026-11-03, before any code)

```
PASS git status --porcelain empty
PASS git log --oneline -1 = 2335026 tape T1b: cycle aggregator, tape event candidates, merged chain events (offline)
     (== tape/t1b head == tape-staging/tape/t1b head)
PASS git remote -v:
     origin        https://github.com/balannavin-cyber/meridian-engine.git (fetch/push)   -- never pushed
     tape-staging  https://github.com/balannavin-cyber/meridian-tape-staging.git (fetch/push) -- tape/* only
```

### 0.1 What was read, and what it says

| Source | What it fixes for this phase |
|---|---|
| ADR-031 (claude-side, **not in the repo**) | Rules taken from the prompt's restatement: D1 contracts, D3/D3a provenance per row, D6 access. Nothing else is assumed. |
| `sql/` naming convention | `YYYY-MM-DD_<session-or-phase>_<subject>.sql`; header says AUTHORED / APPLIED; `COMMENT` and `GRANT` ship as **live statements** (S81 rule), never commentary. |
| Most recent new-table migration: `sql/2026-10-03_s89_gex_cycle_history.sql` | `CREATE TABLE IF NOT EXISTS` inside `BEGIN…COMMIT`; per-column `COMMENT`s; `REVOKE ALL … FROM anon` then `GRANT SELECT … TO merdian_ro`. It deliberately did **not** enable RLS. |
| ADR-031 access precedent: `sql/2026-10-05_s90_apply_S90E_r05_r11.sql` | `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY … FOR SELECT TO merdian_ro USING (true)` + `REVOKE ALL … FROM anon, authenticated` + `GRANT SELECT … TO merdian_ro`; ends with a one-result-set post-apply check (`relrowsecurity`, policy count, `has_table_privilege('anon', …)`). Its header answers the editor's RLS prompt: *"the DDL already enables it WITH a merdian_ro policy — either answer leaves the same end state."* Policy naming since S100-K: `merdian_ro_select`. |
| `data_contracts` DDL (same file, lines 37-57) + `session_end_ist` (`2026-10-06_s90_spot_session_end.sql`) | Columns: `product` PK `'<relation>:<scope>'`, `relation_name`, `scope_symbol`, `scope_col`, `time_col`, `grain text[]`, `cadence_min`, `freshness_sla_min`, `expected_per_cycle jsonb`, `movement_cols text[]`, `movement_window_cycles`, `calendar`, `tier smallint IN (1,2,3)` (3 = research), `writer`, `owner`, `access_rls IN ('ENABLED_WITH_RO_POLICY','DISABLED_BY_DESIGN','UNVERIFIED')`, `valid_from/valid_to`, `change_reason`, `session_end_ist`. `product_lineage(product, requires)` — **both columns FK to `data_contracts.product`**. |
| `check_contracts_shadow.py` | See §1.3 for exactly what it can and cannot evaluate for a daily product. |
| `core/execution_log.py` | One ledger row per invocation; opening row `RUNNING`, finalised by `complete()` / `exit_with_reason()`; fields `run_id`, `product` (= `product_relation[:symbol]`), `kind='run'` (hard-coded), `git_sha` (**short** sha, from `core/`'s repo), `status` derived by `_ledger_status`. **It calls `load_dotenv()` at import** — so the loader imports it lazily and tests never import it. `contract_met` is a floor test (`actual < expected`, `:345-351`) — Rule 0 clause 1; the loader's exactness comes from its own read-back, not from `contract_met`. |
| `core/supabase_client.py` | `select / insert / upsert / delete / rpc` over PostgREST; no transactions, no count. `core.config` hardcodes `C:\GammaEnginePython\.env` and loads it at import — imported lazily for the same reason. Exact count = `Prefer: count=exact` + `Content-Range`, as `check_contracts_shadow.count_exact` does. |
| Existing post-apply access check | No standalone one; the S90-E closing `SELECT` is the pattern. Role-scoped reads must run in **one execution** with `current_user` in the result set (S84 settled rule). |
| T1a/T1b column lists | `merdian_compute/tape/minute.py:30 COLS` (20), `cycle.py:17 CYCLE_COLS` (29), `events.py:28 EVENT_COLS` (9), `chain_events.py:25 EVENT_COLS` (9), `chain_events.py:26 RUN_COLS` (10). The DDL is asserted against these tuples by import, never retyped. |
| `services/tape_runner/recorder.py:695 daily_report()` | Fields actually written by the runner: per symbol `packets`, `feed_gaps_gt10s/60s` (lists), `uploads{ok,retried,failed_attempts,failed}`, `clock_skew{median_s,…}`, `subscribed_count`; day-level `reconnects`, `reconnect_attempts`, `disconnects`, `restarts`, `closed`. **Not written:** `completeness_pct`, `segments`, `connects`, `watchdog_trips`, `frame_errors` (§1.1 says where each comes from). |

### 0.2 Facts measured on generator output (not assumed)

Running `gen_day → process_day → cycle_day` and `gen_chain → chain_events_day` into the scratchpad:

1. `tape_minute.csv` **already carries** `expiry`, `strike`, `opt_type`, `role` (from the token map, T1a). FUT rows have
   `strike` = `expiry` = `opt_type` = empty.
2. `tape_strike_cycle.csv` FUT rows have `strike` and `expiry` empty, `leg = FUT`. `T` and `first_seen_T` are ISO
   `…+05:30`. There is **no day column**.
3. `tape_events.csv` writes `strike or ""` and `exp or ""` — NULL for FUT events.
4. `chain_runs.csv` has its own `run_id` column (the gamma/chain run) — it **collides** with the provenance `run_id`.
5. The T1a manifest's `inputs[]` lists `session/<day>/daily_report_<day>.json` and `subscriptions_*.json` with sha256;
   the T1b cycle manifest lists `in/tape_minute.csv` and `session/subscriptions_*.json`; the chain manifest lists
   `gex_strike_snapshots_<SYM>.csv` (in the parent of `--chain`, as on disk at `C:\tape_data\chain_2026-11-02\`).

Facts 2–3 make the prompt's grain **impossible as a PRIMARY KEY** for `tape_strike_cycle` and `tape_events`
(PK columns are NOT NULL). Resolution in §1.1. Fact 4 forces a rename.

---

## 1. Design

### 1.1 Relations — `sql/2026-11-03_tape_t1db_sidecar.sql` (one file, idempotent, additive)

One transaction. First statement is a `DO` block that **raises** unless `server_version_num >= 150000`
(`UNIQUE NULLS NOT DISTINCT` needs PG 15); nothing is created on an older server.

**Single source of the column set:** `services/tape_db/tape_schema.py` imports the five tuples above and declares,
per table, only (a) the **renames** (CSV name → DB name), (b) the **added** key/derived columns, (c) the provenance
block, (d) a type for every DB column. Every CSV column not renamed keeps its name. The loader builds rows from this
module; the `db-ddl-columns` guard parses the SQL and asserts column names **and types** equal it.

Renames (Postgres folds `T` to `t`, so case-bearing names are renamed explicitly):

| Table | Renames | Added |
|---|---|---|
| `tape_minute` | `day→trading_day`, `sym→symbol`, `token→instrument_token`, `minute→minute_ist` (`HH:MM` → `<day>T<HH:MM>:00+05:30`) | — |
| `tape_strike_cycle` | `token→instrument_token`, `T→ts_ist`, `first_seen_T→first_seen_ts_ist` | `trading_day` |
| `tape_events` | `detail_json→detail` (jsonb) | `trading_day` |
| `tape_chain_events` | — | `trading_day` |
| `tape_chain_runs` | `run_id→chain_run_id` (fact 4) | `trading_day` |
| `tape_daily_report` | not CSV-sourced — columns listed below | — |

Provenance on every table (ADR-031 D3/D3a): `run_id uuid NOT NULL` (one per `load_day` invocation),
`code_sha text NOT NULL` (`git rev-parse HEAD`, full 40 hex, read at run time), `source text NOT NULL`
(`'tape_offline_v1'`), `config_version text` (NULL — **owed**, comment says so), `loaded_at timestamptz NOT NULL` (UTC,
one value per run).

Types: quantities / counts / OI / tokens `bigint`; ratios and floats (`vwap`, `balance_*`, `resting_imb`,
`classified_share_5`, `magnitude`, chain `prev_value`/`new_value`) `double precision`; strikes `numeric` (exact,
e.g. 25012.5); `expiry`/`trading_day` `date`; `minute_ist`, `ts_ist`, `exch_ts_max`, `first_seen_ts_ist`
`timestamptz`; `in_window` `boolean`; `net_sign` `smallint`; `merged_n`, `n_strikes`, `minutes_present_5` `integer`;
`chain_run_id` `text` (a foreign identifier, stored verbatim); text otherwise.

Keys (deviation from the prompt's grain, forced by facts 2–3):

| Table | PRIMARY KEY | Spec grain kept as |
|---|---|---|
| `tape_minute` | `(symbol, trading_day, instrument_token, minute_ist)` | = spec |
| `tape_strike_cycle` | `(symbol, trading_day, instrument_token, ts_ist)` — token *is* the strike-leg identity | `UNIQUE NULLS NOT DISTINCT (symbol, trading_day, expiry, strike, leg, ts_ist)` |
| `tape_events` | none (no NOT-NULL natural key exists for FUT rows; no surrogate, because an identity column is a generated column) | `UNIQUE NULLS NOT DISTINCT (symbol, trading_day, expiry, strike, leg, kind, ts_ist, side)` |
| `tape_chain_events` | `(symbol, trading_day, expiry, kind, ts_ist, strike)` | = spec |
| `tape_chain_runs` | `(symbol, trading_day, expiry, ts_ist)` | = spec |
| `tape_daily_report` | `(symbol, trading_day)` | = spec |

The `UNIQUE` on `tape_strike_cycle` also asserts that no two tokens map to one strike-leg on a day — a token-map
conflict then fails the insert loudly.

`tape_daily_report` columns and their **sources** (every value is read from a manifest-verified file; absent → NULL,
never 0 — ADR-020 / "NULL is a gap, never a zero"):

| Column | Source |
|---|---|
| `packets` bigint | `daily_report.symbols[S].packets` |
| `gaps_gt_10s`, `gaps_gt_60s` int | `len(symbols[S].feed_gaps_gt10s / _gt60s)` |
| `uploads_ok`, `uploads_retried`, `uploads_failed` int | `symbols[S].uploads.{ok,retried,failed}` |
| `skew_median_s` double | `symbols[S].clock_skew.median_s` |
| `reconnects`, `disconnects` int | day-level (same value on both symbol rows — the runner does not split them) |
| `segments` int | count of T1a-manifest `inputs[]` paths `S/<day>/…` that `replay.parse_seg_name` accepts |
| `g3_verdict` text, `classified_share_early/late` double | `g3_report.symbols[S].verdict`, `.verdict_detail.early/late.share_pct` |
| `g3` jsonb | `g3_report.symbols[S]` |
| `report` jsonb | the full raw `daily_report_<day>.json` |
| `completeness_pct` double | **NULL — owed.** Pre-registration rule 4 defines it; that definition is not in the repo and T1-db does not invent one. |
| `connects` int | **NULL — owed** (runner does not write it; T0.1). |
| `watchdog_trips`, `frame_errors` int | **NULL — owed until T0.1**, as the prompt says. |

Every table gets a `COMMENT ON TABLE` naming writer `services/tape_db/load_day.py`, owner operator, tier research,
the pre-registration hash, and the separation rule; owed columns get `COMMENT ON COLUMN … 'OWED: …'`.

Indexes: none beyond the keys (every PK/UNIQUE leads with `symbol, trading_day`; the loader filters on `trading_day`
— add `ix_<t>_trading_day` on each table, cheap and it serves delete/count by day).

### 1.2 Access (ADR-031 D6) — same migration

Per table: `ALTER TABLE … ENABLE ROW LEVEL SECURITY;` a `DO` block that creates policy `merdian_ro_select … FOR SELECT
TO merdian_ro USING (true)` only if absent (CREATE POLICY has no IF NOT EXISTS); `REVOKE ALL … FROM anon,
authenticated;` `GRANT SELECT … TO merdian_ro;`. The service role (the loader) bypasses RLS. Nothing else is granted.

**Post-apply check** `services/tape_db/check_tape_access.sql` — SQL editor, postgres, **one execution**:
`BEGIN; SET LOCAL ROLE merdian_ro;` then one `SELECT` returning one row per table with `current_user`, a real read
`(SELECT count(*) FROM public.<t>)`, `relrowsecurity`, policy count, the one policy's `cmd`/roles, `has_table_privilege`
for merdian_ro SELECT and for anon / authenticated across all seven privileges, and a final column
`'<t> ACCESS PASS'` / `'<t> ACCESS FAIL (<which>)'`. `COMMIT;`. If merdian_ro cannot read a table the statement errors
— that is the loud FAIL; a zero count is *not* a failure before the first load (the probe proves privilege, not data).
What would make it fail: RLS off, zero or two policies, a policy not `SELECT`/`merdian_ro`, any anon/authenticated
privilege, merdian_ro without SELECT, or a read refused; `current_user` must read `merdian_ro` or every PASS is void.

### 1.3 Contracts (ADR-031 D1) — `sql/2026-11-03_tape_t1db_contracts.sql`, generated

**What `check_contracts_shadow.py` supports for a daily product** (`cadence_min >= 1440`):

| Requirement | Runner? | How it is entered |
|---|---|---|
| presence | yes | newest `time_col` row exists for the scope |
| "one load per trading day" | **partly** | `time_col = 'trading_day'` (a date: `read_product` bounds it by IST date); `freshness_sla_min = 1440` → `allowed = 1` trading day behind via `previous_trading_day`. It reads OK while the newest day is D-1, MISSING from two trading days behind. |
| "by 20:00 IST" | **no** — daily products have no time-of-day freshness and `session_end_ist` is applied only to intraday products | **NOT_COMPUTED**, stated in `change_reason` |
| rows on the newest day in a range | yes — `count_exact` on `time_col = newest` vs `expected_per_cycle.rows` | upper bound computed (below) |
| "rows per minute == subscribed instruments that minute" | **no** — the shape check counts the whole day, not per minute | **NOT_COMPUTED** |
| movement on `buy_qty` | **no** — `own_status` skips movement when `is_daily` | `movement_cols '{}'`; **NOT_COMPUTED** |
| calendar | daily products are never CLOSED-gated | `calendar` stored (`NSE_FO` NIFTY, `BSE_FO` SENSEX) for the record |

The runner is not extended in this phase.

Rows (all `tier 3`, `writer 'services/tape_db/load_day.py'`, `access_rls 'ENABLED_WITH_RO_POLICY'`,
`time_col 'trading_day'`, `cadence_min 1440`, `freshness_sla_min 1440`, `scope_col 'symbol'`, `INSERT … ON CONFLICT
(product) DO NOTHING`):

- `tape_minute:{NIFTY,SENSEX}` — `rows [1, H_min]`, `H_min` = Σ over the minutes spanned by day-1 `tape_minute.csv`
  for S of |tokens of S subscribed (union of the day-1 `subscriptions_*.json`, `added_minute ≤ m`)|. Derivation: a
  minute row exists only for a subscribed token, so day-1 rows cannot exceed `H_min`; it is the structural ceiling,
  written beside the number. The lower bound 1 adds nothing beyond presence and is labelled as such — **rows-per-minute
  completeness is NOT_COMPUTED**, not represented by the 1.
- `tape_strike_cycle:{…}` — `rows [1, 75 × N_tokens]` (75 = 5-minute bins 09:20…15:30, `cycle.py:13-15`; rows begin at
  `first_seen_T`, so 75 per token is a ceiling).
- `tape_daily_report:{…}` — `rows [1, 1]` (exact).
- Lineage needs its endpoints registered (FK): `tape_events:{…}`, `tape_chain_events:{…}`, `tape_chain_runs:{…}`.
  Events have no expected count (`expected_per_cycle '{}'`); **a zero-event day is valid**, so their freshness can
  false-MISSING after two consecutive zero-event trading days — said in `change_reason`. `tape_chain_runs` is never
  empty on a trading day (≈ 75 runs) → `rows [1, 75 × 2]` (two expiries ceiling; computed from day-1 `chain_runs.csv`
  by the script and asserted ≤ the ceiling).
- `product_lineage`: `tape_strike_cycle:S ← tape_minute:S`, `tape_events:S ← tape_strike_cycle:S`,
  `tape_chain_events:S ← tape_chain_runs:S`, for S ∈ {NIFTY, SENSEX}. No edge crosses tape ↔ chain.

**Expected values are computed, never recalled:** `services/tape_db/contract_seed.py --out … --cyc … --chain …
--session …` reads only the day-1 files (manifest-verified, same code path as the loader), computes every number above,
and writes the SQL with each derivation and the input sha256s in comments. A test runs it on the fixture and feeds the
emitted contract to `check_contracts_shadow.own_status` (pure) — OK on the fixture, DEGRADED with one row over the
ceiling — so the runner is shown to understand the fields, not assumed to.

### 1.4 Loader — `services/tape_db/load_day.py`

```
python services/tape_db/load_day.py --day 2026-11-02 --out C:\tape_data\out_2026-11-02 \
  --cyc C:\tape_data\cyc_2026-11-02 --chain C:\tape_data\chain_2026-11-02\events \
  --session C:\tape_data\2026-11-02\session [--replace]
```

Stdlib + the engine's `SupabaseClient` + `ExecutionLog`, both imported **inside** `main()` (they load `.env` at
import). `main(argv, client=None, ledger_factory=None, git_sha=None)` — tests inject fakes; production passes nothing.
Exit 0 PASS · 1 LOAD FAIL · 2 usage / refused (existing day) · 3 manifest refused.

Steps, each printing one line:

1. `MANIFEST PASS|FAIL out|cyc|chain` — for each `run_manifest.json`: `args.day == --day`; every `outputs[name]`
   sha256 == the file on disk; T1a `inputs[]` under `session/<day>/` == files under `--session` (or
   `--session/<day>`); cycle `in/tape_minute.csv` == `--out/tape_minute.csv` and `session/*` == the subscriptions
   files; chain `inputs[]` == files in the parent of `--chain`. Any mismatch or missing file → exit 3, **no client
   call at all**.
2. Parse CSVs → typed rows via `tape_schema` (every `tape_minute.day == --day`, else exit 3). Build daily-report rows.
3. `EXISTING <table> rows=<n>` — `count_exact(<t>, trading_day=eq.<day>)` per table. Any > 0 without `--replace` →
   `REFUSED: day exists (use --replace)`, exit 2, **zero writes** (the ledger is not opened: nothing was touched).
4. Open the ledger: `ExecutionLog("load_day.py", expected_writes={t: n_csv}, run_id=<uuid4>,
   product_relation="tape_day")` → `product = 'tape_day'`, `kind = 'run'`.
5. With `--replace`: `SUPERSEDED <table> run_ids=[…]` (distinct `run_id` read before delete, paged ≤ 1,000), then
   `DELETE <table> trading_day=<day>` per table and a re-count that must be 0. **Not atomic:** PostgREST has no
   multi-request transaction and the engine client has none; a crash mid-replace leaves a partial day, which the
   read-back in step 7 reports and a second `--replace` repairs. Superseded run_ids go to the ledger `notes`.
6. `INSERT <table> rows=<n> batches=<k>` — plain `insert`, batches ≤ 1,000. **Deviation: insert, not upsert.** Upsert
   merges a duplicate key silently (S54: *upserts can mask write loss*); with refuse-or-delete-first there is never a
   legitimate conflict, so a conflict must be an error.
7. `LOAD PASS <table> rows=<n> == csv=<n>` / `LOAD FAIL <table> rows=<n> != csv=<m>` — `count_exact` per table for the
   day after loading. Any FAIL → exit 1.
8. Ledger: all PASS → `complete()` (SUCCESS → status OK). Any FAIL → `exit_with_reason("DATA_ERROR", 1, …)` → status
   **MISSING** — `merdian_status` has no `FAIL` value, so the prompt's `status=FAIL` maps to `DATA_ERROR`/`MISSING`
   (ADR-031 D2 vocabulary). `notes` (json): day, code_sha, dirty flag, the three manifests' sha256 and code shas,
   superseded run_ids, per-table counts.

Every row: `run_id`, `code_sha`, `source='tape_offline_v1'`, `config_version=NULL`, `loaded_at`. Tables named by the
loader: the six `tape_*` only (`script_execution_log` is written by `ExecutionLog`, never named directly). No `select`
with an embedded resource, no string naming two relations — the loader cannot join.

---

## 2. Build (Sonnet) — tester first

Files: `services/tape_db/{tape_schema,load_day,contract_seed}.py`, `services/tape_db/check_tape_access.sql`,
`sql/2026-11-03_tape_t1db_sidecar.sql`, `sql/2026-11-03_tape_t1db_contracts.sql`, `tests/tape_t1db/fake_client.py`,
`tests/test_tape_t1db.py`, `tests/tape_t1db_mutants.py`, `tests/run_offline.sh`.

**Fixtures.** Reuse, don't write new generators: `tests/tape_t1a/gen_day.build_day` → `process_day` → `out_`;
`cycle_day` over it → `cyc_`; `tests/tape_t1b/gen_chain.write` → `chain_<day>/` → `chain_events_day --out
chain_<day>/events --day <day>`. `gen_chain.DAY` is 2026-11-03 and `gen_day` defaults to 2026-11-02: build the day
with a `Spec(day=gen_chain.DAY)` if the Spec allows it, else pass the day the generator actually produced to every tool
and the loader (state which in the test). Every table must get ≥ 1 row: if the `gen_day` path yields 0 tape events
(observed with the default Spec), use the Spec's `events` option; if none yields CONC/THIN, the events-table guard
runs on `gen_cycle.build` → `cycle_day` with its own T1a-shaped wrapper and the test says so. Variants: corrupted
manifest (one output byte flipped after the manifest is written); pre-existing day (fake pre-seeded).

**Fake client.** Records `(op, table, filters, rows)` for every call; holds rows per table in memory; `count_exact`
answers from what it holds; `delete` removes by filter; options: `drop_one_row_of=<table>` (keeps all but one row of
the first insert) and `preseed={table: rows}`. **Fake ledger**: records construction args, `record_write`, `notes`,
the finalising call. Tests import neither `core.config` nor `core.execution_log` and assert both are absent from
`sys.modules` at the end.

| Guard | PASS means | Mutant (5/5 caught, control passes 5/5) |
|---|---|---|
| `db-ddl-columns` | per table, SQL column set **and types** == `tape_schema` (CSV tuples by import + renames + added + provenance), exactly; every CSV column mapped once | `M-T1DB-COLUMN-DROPPED` (delete the `vwap` line) |
| `db-ddl-access` | per table: `ENABLE ROW LEVEL SECURITY`, exactly one `merdian_ro` SELECT policy, `REVOKE ALL … FROM anon, authenticated`, `GRANT SELECT … TO merdian_ro`; same set named in `check_tape_access.sql` | `M-T1DB-NO-REVOKE`, `M-T1DB-RLS-OFF` |
| `db-no-join` | migration + loader + seed: no `JOIN`, no `CREATE VIEW/FUNCTION/TRIGGER`, no `GENERATED`, no `\blead(_\|\b)`, `coverage`, `agreement`, `straddle`, `\batm\b`; no string literal naming a `tape_` and a `tape_chain_` relation together; no PostgREST embed `name(` | `M-T1DB-JOIN-VIEW` (append a view joining `tape_minute` and `tape_chain_events`) |
| `load-manifest` | corrupted manifest → exit 3, fake saw **0 calls** | `M-T1DB-MANIFEST-IGNORED` |
| `load-counts` | rows inserted per table == CSV rows; six `LOAD PASS` lines; `drop_one_row_of` → `LOAD FAIL`, exit 1, ledger DATA_ERROR | `M-T1DB-COUNT-SKIPPED` |
| `load-replace` | pre-seeded day without `--replace` → exit 2, 0 writes, no ledger; with `--replace` → deletes before inserts, superseded run_id in ledger notes, new run_id on every row | `M-T1DB-SILENT-OVERWRITE` |
| `load-provenance` | every inserted row has `run_id` (== ledger run_id), `code_sha` == `git rev-parse HEAD` of the worktree, `source`, `loaded_at`; exactly one ledger constructed and finalised once | `M-T1DB-NO-LEDGER` |
| `load-tables-only` | AST: every first argument to a client method is a `tape_*` table from `tape_schema` | `M-T1DB-WRITES-GEX` |
| `t1db-isolated` | `services/tape_runner/*` imports nothing from `services.tape_db` / `services.tape_offline`; `install.sh` archives only `services/__init__.py services/tape_runner`; no `.env` read (core modules absent from `sys.modules`) | `M-T1DB-RUNNER-IMPORTS` |

Unit checks (no mutant): typed conversion of empty strings → NULL; `HH:MM` → `+05:30`; `in_window` → bool;
`contract_seed` on the fixture → `own_status` OK, one row over the ceiling → DEGRADED; `check_tape_access.sql` names
all six tables.

`tests/run_offline.sh`: **36 → 38** steps (`37/38 tape T1-db guards`, `38/38 tape T1-db mutants`), appended after
step 36, header count updated. Mutants run `--repeat 5`.

---

## 3. Operator commands (to be finalised in the build report)

1. Apply `sql/2026-11-03_tape_t1db_sidecar.sql` — **Supabase SQL editor**, postgres, one execution (the engine's
   usual path; `bin/roq.sh` is merdian_ro and cannot create). If the editor offers to enable RLS, accept: the DDL
   enables it with a policy, so either answer ends in the same state (S90 precedent).
2. Run `services/tape_db/check_tape_access.sql` in the editor → six lines `tape_… ACCESS PASS`, `current_user =
   merdian_ro`.
3. Apply `sql/2026-11-03_tape_t1db_contracts.sql` (after step 2).
4. `load_day.py` for 2026-11-02 and 2026-11-03 (PowerShell, `Tee-Object`, Rule 21) → six `LOAD PASS` lines each.
5. Read-back: rows per table per day + distinct run_id per table per day, one query, pasted back.

## 4. Open decision for the operator (one)

`contract_seed.py` must read the day-1 files under `C:\tape_data\` (read-only: CSVs, manifests, subscriptions, no
`.env`, no network) to compute the contract values. **Default: the build session runs it and commits the generated
SQL** with the input sha256s in its header. If reading `C:\tape_data` from this session is out of scope, say so and
the build ships the script plus a placeholder-free command for the operator instead.

## 5. Slips / deviations recorded at plan time

- PK on `tape_strike_cycle` is token-grain and `tape_events` has no PK; the spec grain is a `UNIQUE NULLS NOT
  DISTINCT` (FUT rows have NULL strike/expiry). Requires PG ≥ 15; the migration refuses otherwise.
- `tape_minute` gets no extra `expiry/strike/leg` columns: T1a already writes `expiry`, `strike`, `opt_type`, `role`
  from the token map; leg = `FUT` if role FUT else `opt_type` is derivable and not duplicated.
- `chain_runs.run_id` stored as `chain_run_id`.
- Insert, not upsert (S54).
- `status=FAIL` → `DATA_ERROR` / `MISSING` (no FAIL in `merdian_status`).
- Replace is not atomic (no transaction over PostgREST).
- Contracts for `tape_events`, `tape_chain_events`, `tape_chain_runs` added because `product_lineage` FKs require them.
- `completeness_pct`, `connects`, `watchdog_trips`, `frame_errors`, `config_version` stored NULL, owed.

---

## 6. Build record (2026-11-03, same session; built on Opus — the model switch is the operator's)

Operator ruling on §4: **yes** — `contract_seed.py` ran read-only on `C:\tape_data` (CSVs, manifests, subscriptions;
no `.env`, no network) and its SQL is committed with the input sha256s in its header.

| File | Role |
|---|---|
| `services/tape_db/tape_schema.py` | the one definition: imported CSV tuples + renames + added + provenance + types + keys |
| `services/tape_db/sidecar_sql.py` | renders the migration and the access check from it (deterministic; a unit check asserts the committed files equal the render) |
| `sql/2026-11-03_tape_t1db_sidecar.sql` | the migration (6 tables, RLS, one `merdian_ro_select` policy each, REVOKE anon/authenticated, GRANT merdian_ro, comments) |
| `services/tape_db/check_tape_access.sql` | post-apply check, one execution, `SET LOCAL ROLE merdian_ro`, one `ACCESS PASS/FAIL` line per table |
| `services/tape_db/contract_seed.py` → `sql/2026-11-03_tape_t1db_contracts.sql` | 12 contracts + 6 lineage edges, computed from day 2026-11-02 |
| `services/tape_db/load_day.py` | the loader |
| `tests/tape_t1db/fake_client.py`, `tests/test_tape_t1db.py`, `tests/tape_t1db_mutants.py` | fakes, 9 guards + 15 unit checks, 10 mutants |

Day-1 seed (measured by `contract_seed.py`, 2026-11-02; ceilings derived from the inputs, never from the counts):

| | NIFTY | SENSEX |
|---|---|---|
| subscribed tokens (union of `subscriptions_085501/090000.json`) | 84 | 64 |
| `tape_minute` rows / ceiling (span) | 32,146 / 33,600 (09:00–15:39) | 24,652 / 25,610 (08:00–15:39) |
| rows per minute (measured) | 80.365 of 84 | 53.591 of 64 |
| `tape_strike_cycle` rows / ceiling (75 × tokens) | 6,225 / 6,300 | 4,725 / 4,800 |
| `tape_chain_runs` rows / ceiling (distinct (ts, expiry) in the export) | 87 / 87 | 87 / 87 |
| `tape_events` / `tape_chain_events` rows | 402 / 35 | 170 / 13 |

The same run is evidence for the loader's first two steps on real data: `load_day.verify_manifests` accepted all three
day-1 manifests against the files on disk, and `load_day.build_all` typed every row of every real CSV without error.

### 6.1 Build-time slips

- **Package moved: `services/tape_offline/` → `services/tape_db/`** (loader, seed, schema, renderer, access check).
  The prompt and §1–§3 named `services/tape_offline/`, but the T1a guards `proc-isolated` and `proc-no-outcomes` hold
  every module in that directory to stdlib-only with no database or chain identifiers. The first commit (`883ff3a`)
  put the loader there and turned T1a red (10/12). Widening those guards would loosen a standing gate, so the T1-db
  code moved to its own package — the T1b precedent of `services/tape_chain/`. `install.sh` still archives only
  `services/__init__.py services/tape_runner`, so `services/tape_db` is not shipped either. Paths in this document
  were updated to match; the row `source` value stays `tape_offline_v1`, as the prompt specified.

- **`services/tape_db/__init__.py` was silently ignored** by `.gitignore` `_*.py` (git status clean, file untracked,
  S68). Fixed with a negation line beside T1b's `!services/tape_chain/__init__.py`, never `git add -f`.
- **T0 suite on Windows: environmental, not a regression.** `tests/test_tape_t0.py` exits 15 with no output on this
  Local Windows machine. Per the operator, CC A measured the same on a clean `a1636b9` export the same afternoon, and
  the T0 suite passed 21/21 guards and 12/12 units on the retail box at `1682b52`. T1-db changes no T0 file. T1a
  (12/12, 9/9), T1b (14/14, 5/5) and T1-db (9/9, 15/15) pass here after the package move.
- **Fixture plumbing.** The `gen_day` path produces 0 CONC/THIN candidates (measured with windows up to 09:15–11:00,
  15–23 s per build), so the events fixture uses `gen_cycle`'s planted day as `tape_minute.csv`; that fixture's T1a
  `run_manifest.json` is re-hashed by the test (stated in `tests/test_tape_t1db.py` and in the manifest itself as
  `test_plumbing`). The manifest guard runs on the all-real fixture.
- **Mutant copies are not git checkouts**, so the code_sha lookup is injected into `load_day.main(git=…)` by the test
  from `TAPE_T1DB_HEAD`; in the real tree the guard compares against `git rev-parse HEAD` with no injection.
- **`tape_chain_runs` ceiling == measured (87 / 87)** — the ceiling is the export's run count, so a later day with more
  gamma runs reads DEGRADED: a day-1 proposal (A-11), said in `change_reason`.
- **`core.autocrlf=true`**: `tests/run_offline.sh` is CRLF in the working tree, LF in the index; the edit preserved
  CRLF. New files are LF.
- **Rule 23**: built ~15:10 IST on a weekday; `test_tape_t1db.py` / `tape_t1db_mutants.py` ran under the R-1 Local
  override (`TAPE_RULE23_OVERRIDE_R1=1`). `tests/run_offline.sh` has no override and was not run end to end in-window.

## 7. Operator commands (PowerShell / SQL editor, in order)

1. **Apply the migration** — Supabase SQL editor (postgres), paste all of `sql/2026-11-03_tape_t1db_sidecar.sql`, run
   once. If the editor offers to enable RLS, accept it: the DDL already enables RLS with a policy, so either answer ends
   in the same state. **If the editor reports any error, do not assume nothing landed** (S90 AM-1): the file is
   idempotent — re-run it, then run step 2. A server below PostgreSQL 15 is refused by the first `DO` block.
2. **Access check** — paste `services/tape_db/check_tape_access.sql`, run once. Expected, six lines, `role_now =
   merdian_ro`, `rows_readable_by_ro = 0`:
   ```
   tape_chain_events ACCESS PASS
   tape_chain_runs ACCESS PASS
   tape_daily_report ACCESS PASS
   tape_events ACCESS PASS
   tape_minute ACCESS PASS
   tape_strike_cycle ACCESS PASS
   ```
3. **Contracts** — paste `sql/2026-11-03_tape_t1db_contracts.sql`, run once → `tape_contracts = 12`, `tape_edges = 6`.
4. **Load** (from the worktree, on the pushed head):
   ```powershell
   cd C:\wt-tape-b
   git status --porcelain ; git log --oneline -1
   $env:PYTHONIOENCODING = "utf-8"
   python services\tape_db\load_day.py --day 2026-11-02 --out C:\tape_data\out_2026-11-02 --cyc C:\tape_data\cyc_2026-11-02 --chain C:\tape_data\chain_2026-11-02\events --session C:\tape_data\2026-11-02\session 2>&1 | Tee-Object -FilePath "C:\tape_data\load_2026-11-02_$(Get-Date -Format yyyyMMdd_HHmm).log"
   ```
   Expected for 2026-11-02 (sums of the day-1 seed above):
   ```
   LOAD PASS tape_minute rows=56798 == csv=56798
   LOAD PASS tape_strike_cycle rows=10950 == csv=10950
   LOAD PASS tape_events rows=572 == csv=572
   LOAD PASS tape_chain_runs rows=174 == csv=174
   LOAD PASS tape_chain_events rows=48 == csv=48
   LOAD PASS tape_daily_report rows=2 == csv=2
   TAPE T1-DB LOAD PASS day=2026-11-02 run_id=<uuid> code_sha=<head>
   ```
   2026-11-03: `C:\tape_data` holds no 2026-11-03 outputs yet; run T1a / T1b for the day first, then the same command
   with `2026-11-03` throughout. Its expected counts are the `PARSED <table> rows=<n>` lines the loader prints before
   it touches the database; each `LOAD PASS` must repeat them. A second run of either day without `--replace` must
   print `REFUSED: trading_day … already loaded` and exit 2.
5. **Read-back** — SQL editor, paste the result back (counts only; no tape-side row meets a chain-side row):
   ```sql
   SELECT 'tape_minute' AS t, trading_day, count(*) AS n, count(DISTINCT run_id) AS runs FROM public.tape_minute GROUP BY 2
   UNION ALL SELECT 'tape_strike_cycle', trading_day, count(*), count(DISTINCT run_id) FROM public.tape_strike_cycle GROUP BY 2
   UNION ALL SELECT 'tape_events', trading_day, count(*), count(DISTINCT run_id) FROM public.tape_events GROUP BY 2
   UNION ALL SELECT 'tape_chain_runs', trading_day, count(*), count(DISTINCT run_id) FROM public.tape_chain_runs GROUP BY 2
   UNION ALL SELECT 'tape_chain_events', trading_day, count(*), count(DISTINCT run_id) FROM public.tape_chain_events GROUP BY 2
   UNION ALL SELECT 'tape_daily_report', trading_day, count(*), count(DISTINCT run_id) FROM public.tape_daily_report GROUP BY 2
   UNION ALL SELECT 'ledger ' || status::text || ' ' || exit_reason || ' ' || coalesce(git_sha, '?'), trade_date, 1, 0
     FROM public.script_execution_log WHERE script_name = 'load_day.py' AND product = 'tape_day'
   ORDER BY 1, 2;
   ```
