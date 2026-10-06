# ADR-031 — The spine: data contracts, one status vocabulary, provenance, one ledger, effective-dated config

| Field | Value |
|---|---|
| Status | **ACCEPTED** — ruling **S90-C**, 2026-10-05 17:38 IST (`docs/research/s90_agentic/rulings_s90.md`), on roadmap ruling A-8. Drafted Session 90 (AM-1), 2026-10-05. **Amendment D3a ACCEPTED** 2026-10-06 05:05 IST (ruling S90-I). D4.3 ruled S90-E |
| Number | **ADR-031, confirmed at the S90 (AM-1) doc-close** — the Decision Index marker read `ADR-031+` and advances to `ADR-032+` |
| Roadmap item | **R0.2** (RO). Governs R0.3, R0.5, R0.6, R0.7, R0.8 and every Stage 1 check |
| Evidence base | `docs/research/s90_agentic/R0.1_spine_inventory_S90.md` (findings R01-F1…F9, gap list) · `docs/research/s90_agentic/marketview_live_check_S90.md` (MV-1…MV-12) · P1/P4/P5 outputs in `~/meridian-cc/scratch/s90/` |
| Builds on, does not supersede | ADR-016 (parameters), ADR-018 D2 / ADR-023 (fail to absent; consumer-cadence floors), ADR-020 (absence is not a verdict), ADR-021 (latest-run scoping), ADR-029 (ledger, routing), ADR-030 (per-cycle history, write-and-flag) |

---

## Why this ADR exists

Every harness stage after Stage 0 needs the same five conventions: what a data product promises, what state it is in, where a row came from, where events are recorded, and which rule values were in force. Today each is either missing or held in several places that disagree. S90 measured the cost on one day:

- **A writer can be "fresh" and wrong all session.** `weighted_constituent_breadth_snapshots` wrote a new `ts` every 5 minutes on 2026-10-05 with values identical to 2026-10-01 15:40, because its inputs are a once-a-day prior close and a daily table stalled at 2026-09-29 (R01-F9). Health showed it green.
- **A holiday passes row and timestamp checks.** 2026-10-02 wrote 79,680 / 63,412 chain rows at **one** spot (P4). Only a movement check sees it.
- **A green checker can be the checker's fault.** Health reported OVERALL CRITICAL on 5 false stales (wrong cadence, no calendar) — MV-4.
- **The run record cannot answer "what ran".** The orchestrator imports `ExecutionLog` and never constructs one (R01-F1); `script_execution_log` is unreadable to `merdian_ro` (TD-S81-NEW-16); a third ledger lives outside git (`/home/ssm-user/merdian_ledger/ledger.jsonl`).
- **Config has a public write path and no read-as-of.** `update_parameter` is executable by `anon` (R01-F4); the S89 seed could not reach its reader for a one-token mismatch (R01-F2).
- **A new table's access state is not what its DDL says.** `gex_cycle_history` came up with RLS on and zero policies, and `authenticated=rm`, though the DDL enables neither (R0.4, S90): the SQL editor offered RLS at run time and default privileges granted `authenticated`.

None of these is a bug in one script. Each is a convention nobody owns. This ADR makes each one owned, in one place.

---

## D1 — Every data product has a contract, and checks are generated from contracts

**Decision.** A table `data_contracts` holds one row per **product** (a relation × a scope, e.g. `option_chain_snapshots × NIFTY`). A check runner reads the contracts and generates the checks. **No hand-written per-table check is added after this ADR**; existing ones migrate as their product gets a contract.

Each contract declares:

| Field | Meaning | S90 case it would have caught |
|---|---|---|
| `grain` | key columns of one row | — |
| `expected_per_cycle` | rows, distinct strikes, distinct expiries per cycle (ranges) | ENH-133 W2 absent by schema (R01-F7) |
| `cadence` | writer cadence | — |
| `freshness_sla` | **calibrated to the consumer's cadence**, not the writer's (ADR-023 A1.2) | MV-4 false stales |
| `movement` | columns that must change across N cycles in an open session | 10-02 frozen spot; WCB frozen values |
| `required_inputs` | upstream products, with their own contracts (lineage) | WCB: fresh `ts`, stale inputs |
| `calendar` | which instrument calendar decides OPEN / CLOSED (D5) | MV-4 weekend/holiday stales |
| `tier` | core / context / research (roadmap §5.3) | — |
| `writer`, `owner` | script and accountable owner | R01-F1 |
| `access` | RLS stated, `merdian_ro` readable, `anon` none (D6) | ENH-133 X4 |

**A product's freshness is the worst of its own `ts` and its required inputs' freshness.** A row stamped now from an input stamped last week is STALE. This is the rule the WCB case breaks.

**Rejected — hand-written checks per table.** That is what exists (TD-S69-NEW-2, TD-S82-NEW-3, `eod_health_check.py`, Marketview Health's `TRACKED_WRITERS`), and it produced three checkers with three cadence tables, none calendar-aware. A new symbol or source must be configuration, not code.

**Rejected — a freshness check on `ts` alone.** It passes 10-02 and WCB. Freshness is necessary, not sufficient (ADR-023 Consequences).

## D2 — One status vocabulary, carried down the lineage

**Decision.** One Postgres enum, used by every check, layer and screen:

| Status | Meaning |
|---|---|
| `OK` | Complete, fresh and moving, from the primary source |
| `DEGRADED` | Partial, or answered by a secondary source; usable with a flag |
| `STALE` | Rows arrived but nothing moved, **or** a required input is stale |
| `MISSING` | Nothing usable; an explicit gap row is written |
| `CLOSED` | The product's own calendar says closed now; expected, never a failure |
| `NOT_COMPUTED` | A computed layer whose required inputs failed; carries a reason |
| `UNKNOWN` | No fresh status exists (the checker itself is late or dead). **Never rendered as OK** (roadmap risk 6) |

**Propagation:** an input that is `MISSING`, `STALE` or `NOT_COMPUTED` makes its dependant **`STALE`** (the dependant's rows exist but rest on bad inputs); an `UNKNOWN` input propagates as `UNKNOWN`, a `DEGRADED` one as `DEGRADED`; `CLOSED` inputs impose nothing. The dependant's status is the worse of that and its own. Order: `MISSING` > `NOT_COMPUTED` > `STALE` > `UNKNOWN` > `DEGRADED` > `OK`. (Implemented and tested in `check_contracts_shadow.py`.)

**Existing vocabularies map, they are not renamed in place.** `gex_cycle_history.session_gate_state` (`OPEN` / `FROZEN` / `PRE_TICK`) stays as the stored fact; its status is derived (`FROZEN` → `STALE` on an open calendar day, `CLOSED` on a closed one). `script_execution_log.exit_reason` values (`SKIPPED_NO_INPUT`, `OFF_HOURS`, `TOKEN_EXPIRED`, `DATA_ERROR`) are causes, not statuses, and stay.

**Rejected — per-product status words.** The board, Health and the signal stream already speak three dialects (MV-10: the signal stream and the board disagree on regime because they read different runs, and nothing on screen says which is current).

## D3 — Provenance on every new row of a capture or compute product

**Decision.** New rows of contracted products carry:

| Column | Content |
|---|---|
| `run_id` | the cycle's run (already on most capture tables) |
| `source` | vendor and endpoint (`dhan_charts_intraday`, `kite_ohlc`, `backfill`) |
| `code_sha` | git commit of the writer at deploy time (from the environment, set by the deploy, never typed) |
| `config_version` | identifies the parameter set read (D4) |
| `as_of` | for computed rows: the instant the inputs were read as of |

**Additive only.** Columns are added nullable; history is **not** backfilled (never mutate stored history, roadmap risk 11). R0.3's exit is 100 % coverage **of new rows**, measured by query.

**Hand-typed builder constants are superseded, not deleted.** `raw.builder_version = "V18B_SMDM_VELOCITY_V1"` (`compute_gamma_metrics_local.py:1101-1102`) stays for continuity; `code_sha` becomes the authority.

**Amendment D3a (S90, 2026-10-06, ACCEPTED — ruling S90-I):** for any relation that carries `run_id` (chain, gamma, strike GEX, volatility via `source_run_id`, cycle history), provenance is satisfied by the join `run_id → script_execution_log (git_sha, script_name, product, status)` once D7's `run_id` column is filled; no `code_sha`/`source` columns are added to those tables. Direct columns remain required only where a relation has no `run_id`. `config_version` is unchanged (still owed). Measured by `v_provenance_coverage_daily` (target 100 % of new runs). Why: one ExecutionLog change instead of five live-writer schema changes, and the ledger is already the record of who wrote what.

**Rejected — provenance in `raw` jsonb.** It is never annotated (data-access rule) and cannot be indexed or required.

## D4 — Rules are effective-dated data, read as-of, written by one closed path

**Decision.** `merdian_parameters` (ADR-016, live schema `value_num/text/bool/jsonb`) is the only home for tunable values.

1. **Read as-of.** A read function takes `as_of` (`get_parameter_num(key, as_of)`); the current signature becomes `as_of = now()`. Replaying a day reads the rules as they were that day (principle 7).
2. **`config_version`** for D3 is the newest `valid_from` among the keys a writer read, recorded per row.
3. **Write path is closed to `anon`.** `update_parameter()` loses `EXECUTE` for `PUBLIC` and `anon`; Marketview Settings writes through an authenticated route. **This needs its own ruling** (R01-F4: a plain revoke breaks Settings today) and must land before any live consumer acts on a parameter. `core/pin_state.py` reads the 8 `pin_state.*` keys seeded on 2026-10-05, so that point is near.
4. **Every write records who and why** (`changed_by` passed explicitly; today Marketview records `'operator'` for every change).

**Safety interlocks are code constants, not parameters** (roadmap risk 14): a parameter read can fail open.

## D5 — Calendars: absence is not a verdict, closed days are written, CLOSED is a status

**Decision.**
1. Each contract names a calendar (`NSE_FO`, `BSE_FO`, later per-instrument for Stage 3b).
2. **Closed days are written as rows** (`is_open = false`, `holiday_name`), not left absent. The seeder writes them; until it does, dated belt rows (S90: 2026-10-20, 2026-11-10).
3. **Every gate reads `core/trading_calendar_gate.py`** (ADR-020). The inline copies in `ingest_option_chain_local.py:293-327` and `capture_spot_1m_v2.py:265-290` read no row as open and are migrated (R0.8). S68 counted ~28 inline gates.
4. A product outside its calendar's session is `CLOSED`, never `STALE`.

## D6 — A new table states its access in its own DDL, and the apply is checked

**Decision.** Every new-table migration:
1. States RLS explicitly. **Default: `ENABLE ROW LEVEL SECURITY` plus a `merdian_ro` `SELECT` policy in the same migration**; `DISABLE` only with a reason in the DDL comment. The SQL editor's run-time RLS prompt is answered to match the DDL.
2. `REVOKE ALL … FROM anon, authenticated` unless a consumer needs them, named in the comment (R01-F8: `anon=rm` on six base tables; ENH-133: `authenticated=rm` from default privileges).
3. Is followed by the post-apply access check (`merdian_ro` reads, `anon` cannot, RLS as declared). The check is part of acceptance, not optional.

**Why the default is RLS on with a policy.** It holds even when a revoke is forgotten. RLS off is safe only while every grant is right, and S90 showed default privileges adding one nobody wrote.

## D7 — One ledger, keyed by run, readable by the observer

**Decision.** `script_execution_log` is extended into the single ledger. **No fifth log** (principle 11).

1. Add `kind` (`run` · `check` · `gap` · `incident` · `ruling` · `model_call`), `product`, `status` (D2), and `run_id` as the correlation key alongside `invocation_id`.
2. The ADR-029 file ledger (`ledger.jsonl`, writer outside git) and ENH-71 `record_write` fold into it; the file ledger becomes an export, not a source.
3. **`merdian_ro` gets a read policy on it** (TD-S81-NEW-16). The observer must be able to read the record it judges; today it reads 0 rows and cannot distinguish "did not run" from "cannot see" (P5: 0 rows for a script whose log shows it ran).
4. **Every scheduled writer writes a ledger row, including the orchestrator** (R01-F1). A writer with no row is `UNKNOWN`, not `OK`.
5. One query traces a Home read to its capture run (R0.7 exit).

**Rejected — a new `ledger` table.** Seventeen writers already write `script_execution_log`; a new table splits the record during migration and doubles the observer's work.

---

## What this ADR does not decide

- **Scope admission** (ruling A-5): whether Stages 0–2 sit inside parity.
- **Thresholds and N values** (A-11): SLO targets, movement windows, freshness SLAs per product. Contracts hold them as parameters (D4); this ADR sets the shape only.
- **The WCB repair** (R01-F9): a writer change, ruled separately. Under this ADR it would show `STALE` from the first cycle.
- **Retention**: ADR-030 D2 stands for `gex_cycle_history`; other tables are R1.9's.

## Build order this ADR implies

1. **R0.5** status enum + lineage table (SC).
2. **R1.1** `data_contracts` seeded for core products: chain per symbol, spot, ticks, strike GEX, gamma, cycle history, WCB (SC, shadow).
3. **R1.2** generated-check runner in shadow, writing `cycle_health` (SC). First fixtures: 10-02 (movement), 10-05 WCB (input freshness), a weekend (CLOSED).
4. **R0.7** ledger columns + `merdian_ro` policy; orchestrator row (LIVE, after the close).
5. **R0.3** provenance columns, nullable, writer by writer (LIVE).
6. **R0.6** parameter as-of read + closed write path (needs the D4.3 ruling).
7. **R0.8** gates onto `core/trading_calendar_gate.py`; seeder writes closed days (LIVE).

## Consequences

- **Nothing changes in production on acceptance.** Every step above is its own change with its own risk class (roadmap §11.3).
- **Marketview Health is replaced, not patched further**, once `cycle_health` exists: it reads statuses instead of computing its own cadence table (MV-4).
- **History stays as it is.** Old rows have no provenance and no status; queries that span the boundary say so.
- **Cost:** one runner every cycle, read-mostly. Its compute time is stated against R1.9 before it runs live.

## Governance language

> **Every data product has a contract; checks are generated from contracts, never hand-written per table.** One status vocabulary (`OK`, `DEGRADED`, `STALE`, `MISSING`, `CLOSED`, `NOT_COMPUTED`, `UNKNOWN`) is carried down the lineage as the worst of a product's own and its inputs' status, `CLOSED` excluded; freshness includes input freshness and movement. New rows carry `run_id`, `source`, `code_sha`, `config_version`. Rules are effective-dated, read as-of, and written only through a closed path. Closed days are rows. A new table states RLS and grants in its own DDL and is checked after apply. `script_execution_log` is the one ledger and the observer can read it. (ADR-031, S90, accepted.)

## Cross-references

ADR-016 · ADR-018 D2 · ADR-020 · ADR-021 · ADR-023 (+ A1.2) · ADR-029 · ADR-030 · TD-S69-NEW-2 · TD-S81-NEW-16 · TD-S82-NEW-3 · TD-S89-NEW-1 · TD-S89-NEW-2 · R01-F1…F9 · MV-4, MV-9, MV-10 · `rulings_s90.md` (S90-A, S90-B).
