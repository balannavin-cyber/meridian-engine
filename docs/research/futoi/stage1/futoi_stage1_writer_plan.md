# Plan: `capture_futures_oi_1m` — Stage 1 writer plan

## Context

**Why this exists.** The FOI lane has finished Stage 0a (field probe + far-month probe, 2026-11-28) and
`docs/registers/STREAMS.md:18` marks the next step as live ingest. Stage 1 is the writer: one row per
index-futures contract per minute into a new operator-only table `public.futures_oi_1m`, built to the
discipline of the tape 2b writer rather than to the discipline of the engine's existing futures capture.

That last clause is the whole point. The nearest existing writer,
`capture_index_futures_snapshot_local.py`, has **no `ExecutionLog` row, no holiday gate, no lot size, and
a naive local-clock date gating contract resolution** (`capture_index_futures_snapshot_local.py:1-16`
imports no `core.*`; `:96-101` `today_iso_local()` is `datetime.now()` with no `ZoneInfo`, consumed at
`:165`). A new writer modelled on it would inherit all four. The tape 2b writer
(`origin/tape/live-l2` @ `d1f9ba2`) is the opposite case: a confined write path, start-up refusals, a
stop latch that survives restart, 35 guards and 195 mutants.

**Intended outcome of this plan file.** A plan the engine can build from red-first, and the operator can
rule on, without any further design decisions being taken inside the build.

### The one action this plan authorises

Write the body below to **`docs/research/futoi/stage1/futoi_stage1_writer_plan.md`** (one new file, no
code, no DDL applied, no commit, no database write). Nothing else.

> Note on paths: plan mode restricts edits to this plan file, so the deliverable's content is held here
> verbatim and written to the repo path on approval.

### Discrepancies found while planning — read before ruling

1. **Two of the "fixed facts" are not in the Stage 0a documents.** The instruction says not to mark them
   TO CONFIRM, so they are carried below as *operator-supplied*, and labelled as such:
   - *"scheduled Dhan marketfeed calls are ltp only, at second `:00`"* — the **ltp-only** half is
     established (`futoi_stage0a_fields_2026-11-28.md:65`: quote call sites 0, ohlc 0, `wss://` 0). The
     **`:00` second** half is explicitly disclaimed at `futoi_stage0a_fields_2026-11-28.md:77`: "The IST
     offsets in §f4 are cron *firing* times; the second within the minute at which each POST is actually
     sent was not measured."
   - *"`dhan_scripmaster` can lack the far month for up to ~15 days after a monthly expiry"* — the phrase
     and the figure appear nowhere. What the docs carry is the `1,15` cron line
     (`futoi_stage0a_farmonth_2026-11-28.md:6`), the computed last firing 2026-11-15 07:00 IST (`:9`),
     and an explicit refusal to treat it as observed (`:9`: "The '2026-11-15 run' is a **computed**
     firing date, not an observed run").
   The design does not depend on either, so nothing changes; they are flagged because a plan that cites
   a document for something the document disclaims is the §D.62.1 defect.
2. **Box memory.** The brief says 1.9 GB, no swap. Measured on this host, this session: `free -m` →
   total **3836** MB, free 2511, **Swap 0**; `nproc` → 2; `python3 -V` → **3.10.12**. The no-swap half
   holds. **Q-OP-1 RULED: deploy here; the two memory numbers come from a rule applied to the replay
   gate's measured peak RSS, not from a guess (§3 table, G6a).**
3. **`pg_default_acl` still grants `anon` ALL on new `public` relations** — but only for objects owned by
   `supabase_admin`. Measured: `pg_default_acl` row (`supabase_admin`, `public`, `r`) =
   `{postgres=arwdDxtm/…,anon=arwdDxtm/…,authenticated=…,service_role=…}`, while
   `tape_live_cycle.relacl` = `{postgres=…,service_role=…,tape_ro=r,merdian_ro=r,tape_w=arw}` with **no
   anon entry** (created by `postgres`, for which there is no `pg_default_acl` row in `public`). So the
   DDL must be applied as `postgres` **and** carry an explicit `REVOKE` as a live statement, with a
   post-apply `relacl` read. This is the fourth-recurrence class of rule 26 / `§D.81`.
4. **`tape_live_*` has no `data_contracts` row.** Measured: `SELECT … FROM public.data_contracts WHERE
   relation_name LIKE 'tape_live%'` → **0 rows**, while the four tables exist with RLS on. ADR-031's
   "every data product has a contract" is unsatisfied there. `futures_oi_1m` ships its contract rows in
   the same batch as its DDL, and the apply step reads them back.
5. **`docs/research/futoi/stage0/` is untracked** (`git status --porcelain` → `?? docs/research/futoi/stage0/`),
   and `.gitignore:43-44` ignores `*.csv` and `*.txt`. This plan cites those files; until they are
   tracked the citations resolve to nothing. **Q-OP-9 RULED: committed with `git add -f` at the lane
   close, on the operator's word (G0).**
6. **A claim in the first draft was wrong and is withdrawn.** It said the existing orchestrator
   monitor's hung-run probe would see a dead futoi process. Measured: the probe is scoped to one
   `script_name` (`monitor_orchestrator_health.py:121`, `:463`) and does not. §3.1 replaces the claim
   with the measurement, the engine intake item (Q-EN-7) and what the writer does meanwhile.
7. **Two more arithmetic errors in the first draft, both fixed.** §7.8 expected 8 table/column comments
   against a §7.6 that wrote 7 — a total that could not be reached; and §8.1 said "one connection for
   the day" when the sink runs one `psql` per grid point. The second error mattered: once connections
   are per-grid-point, a concurrent `--check` against `CONNECTION LIMIT 1` can raise `53300`, which is
   stop-tier and would latch — so `--check` is now refused during a session (§8.1, Q-OP-11).

---

# BODY TO BE WRITTEN TO `docs/research/futoi/stage1/futoi_stage1_writer_plan.md`

# FOI Stage 1 — `capture_futures_oi_1m`: writer plan

Lane: FOI (futures OI). Stage: 1 (live writer). Written: 2026-11-28. Branch base: `b24ff39`
(`git rev-parse HEAD` == `git merge-base HEAD origin/main`). Pattern copied from the tape 2b writer at
`origin/tape/live-l2` @ `d1f9ba2`; every tape citation below is against that ref.

**Nothing in this plan has been built. No DDL is applied, no role exists** (measured: `to_regclass('public.futures_oi_1m')`
→ NULL; `pg_roles` where `rolname='futoi_w'` → 0; `tape_w` → 1).

---

## 1. What the writer does

A call to `POST https://api.dhan.co/v2/marketfeed/quote` each minute from **09:15 to 15:30 IST
inclusive**, plus one at **15:40 IST**, each at **second `:30`**; body
`{"NSE_FNO":[…],"BSE_FNO":[…]}`; headers `Accept`, `Content-Type`, `access-token`, `client-id`
(`futoi_dhan_quote_probe_fields.py:54`, `:130-134`, `:189-197`). Up to three monthly contracts per symbol
for NIFTY and SENSEX. Each response's 17-key per-contract block
(`futoi_stage0a_fields_2026-11-28.md:12`) becomes one row per contract per minute, appended to a dated
local CSV and then upserted into `public.futures_oi_1m` as the role `futoi_w`.

Call count per day: `(15:30 − 09:15) + 1 = 376`, plus the 15:40 call = **377**. Rows per day: 377 ×
contracts resolved. With the 3+3 the exchange lists, 2,262. With the 2+2 the table holds **today**
(measured, §3), **1,508**.

Off by default in two independent ways (§5).

---

## 2. Fixed facts this plan is built on

Each is cited; the two operator-supplied ones are labelled.

| # | Fact | Source |
|---|---|---|
| F1 | `POST /v2/marketfeed/quote`, body `{"<segment>":[<int security_id>,…]}`, headers `Accept` / `Content-Type` / `access-token` / `client-id`; segments `NSE_FNO` (NIFTY) and `BSE_FNO` (SENSEX) | `futoi_dhan_quote_probe_fields.py:54`, `:130-134`, `:189-197`; segments `:77`,`:81`; `futoi_stage0a_fields_2026-11-28.md:35` |
| F2 | 17 keys per block under `data.<segment>.<security_id>`, identical on 4/4 instruments × 3/3 responses; response key is a **string**, request value an **int** | `futoi_stage0a_fields_2026-11-28.md:12`; `futoi_dhan_quote_probe_fields.py:133`, `:179-183`; `sample_response_fields.json:4,83,164,243` |
| F3 | `oi` and `volume` are **index units**, not contracts: `oi mod LOT_SIZE == 0` and `volume mod LOT_SIZE == 0` on 4/4 instruments × 3/3 samples | `futoi_stage0a_fields_2026-11-28.md:23-28`, `:30` |
| F4 | `LOT_SIZE` differs **between contracts of one index**: SENSEX DEC **20**, SENSEX JAN **25**; NIFTY **65** on all three months. Store the lot per row | `futoi_stage0a_fields_2026-11-28.md:46-47`, `:68`; `futoi_stage0a_farmonth_2026-11-28.md:16-18` |
| F5 | `last_trade_time` is `DD/MM/YYYY HH:MM:SS`, string, **no timezone marker, no sub-second**; the zone is **not established** and IST is not asserted | `futoi_stage0a_fields_2026-11-28.md:21`, `:74` |
| F6 | An absent key is an **empty cell, never 0**; no key was observed absent, but `oi_day_high`/`oi_day_low` read a genuine `0` on both SENSEX legs | `futoi_dhan_quote_probe_fields.py:285-286`; `futoi_stage0a_fields_2026-11-28.md:21`, `:76` |
| F7 | The engine reaches **only** `/v2/marketfeed/ltp`: quote call sites 0, ohlc 0, `wss://` 0 | `futoi_stage0a_fields_2026-11-28.md:65` |
| F8 | Engine marketfeed cron firings: `*/5` + 15:30/15:35/15:40 (futures, gamma/VIX), 09:09 (pre-open probe), 09:11 (spot markers) | `futoi_stage0a_fields_2026-11-28.md:58-63` |
| F9 | **Operator-supplied**: those scheduled calls land at second `:00`. The writer calls at `:30`. *The Stage 0a doc disclaims the second-level claim at `futoi_stage0a_fields_2026-11-28.md:77`.* | operator |
| F10 | **Operator-supplied**: `dhan_scripmaster` can lack the far month for up to ~15 days after a monthly expiry. *What the docs carry is the `1,15` cron (`futoi_stage0a_farmonth_2026-11-28.md:6`) and a computed, unobserved 2026-11-15 firing (`:9`).* | operator |
| F11 | Writer writes what resolves, never substitutes, and records how many resolved | operator |
| F12 | Operator rulings on the role: `futoi_w`, INSERT+UPDATE on `futures_oi_1m` only, no DELETE/TRUNCATE, RLS to the IST trading day, `statement_timeout` 15 s, `CONNECTION LIMIT 1`; credential in its own env file, mode 600, never `.env`, argv, logs or chat; engine authors all DDL/role/grant SQL, operator applies | operator |
| F13 | No rate limit for `/quote` is established anywhere; no 429/401/403/DH-901/DH-904 was ever observed (0 of 3 and 0 of 1) | `futoi_stage0a_fields_2026-11-28.md:10`, `:73`; `futoi_stage0a_farmonth_2026-11-28.md:27` |

### Measured in this session (via `bin/roq.sh` as `merdian_ro`)

| # | Measurement | Value |
|---|---|---|
| M1 | `dhan_scripmaster` columns | 29, **all `text`** (incl. `LOT_SIZE`, `SM_EXPIRY_DATE`) |
| M2 | `INSTRUMENT='FUTIDX'`, `UNDERLYING_SYMBOL IN ('NIFTY','SENSEX')`, `SM_EXPIRY_DATE >= '2026-11-28'` | **4 rows: NIFTY 58875 / 2026-12-29 / 65.0; NIFTY 54749 / 2027-01-25 / 65.0; SENSEX 1145756 / 2026-12-31 / 20.0; SENSEX 1172959 / 2027-01-28 / 25.0** — 2 per symbol, not 3 |
| M3 | `INSTRUMENT_TYPE` | **differs by exchange**: `FUT` (NSE) vs `FUTIDX` (BSE). `SEGMENT` is `D` for both; `EXCH_ID` is `NSE`/`BSE`. The marketfeed segment must come from `EXCH_ID`, never from `SEGMENT` |
| M4 | `tape_w` role attributes | `rolsuper f`, `rolbypassrls f`, `rolcanlogin t`, `rolconnlimit 2`, `rolconfig {statement_timeout=15s,idle_in_transaction_session_timeout=10s}` |
| M5 | `tape_live_cycle.relacl` | `{postgres=…,service_role=…,tape_ro=r,merdian_ro=r,tape_w=arw}` — **`arw` = INSERT, SELECT, UPDATE; no `d`, no `D`**; no `anon` |
| M6 | `pg_policies` on `tape_live_cycle` | 5: `tape_w_insert` (INSERT, WITH CHECK `trading_day = ((now() AT TIME ZONE 'Asia/Kolkata'))::date`), `tape_w_update` (USING + WITH CHECK, same), `tape_w_select` (USING, same), `tape_ro_select` (true), `merdian_ro_select` (true) |
| M7 | `pg_indexes` on `tape_live_cycle` | `tape_live_cycle_pk` UNIQUE btree(symbol, trading_day, instrument_token, ts_ist); `ix_tape_live_cycle_trading_day` btree(trading_day) |
| M8 | `pg_default_acl` (`supabase_admin`, `public`, `r`) | includes **`anon=arwdDxtm`** — a table created by `supabase_admin` comes up readable and writable by `anon` |
| M9 | `timezone(text, timestamptz)` volatility | **`i` (IMMUTABLE)**; `date(timestamp)` **`i`**; `date(timestamptz)` `s`. So `(ts AT TIME ZONE 'Asia/Kolkata')::date` is immutable and legal in a `GENERATED … STORED` column; `ts::date` is not |
| M10 | `data_contracts` | table `public.data_contracts`, PK `(product)`, 20 columns; CHECKs: `tier IN (1,2,3)`, `cadence_min > 0`, `freshness_sla_min > 0`, `movement_window_cycles >= 1`, `access_rls IN ('ENABLED_WITH_RO_POLICY','DISABLED_BY_DESIGN','UNVERIFIED')`, `length(change_reason) > 0`. `expected_per_cycle` is jsonb and existing rows use **ranges** (`{"rows":[100,200]}`) |
| M11 | `data_contracts` rows for `tape_live%` | **0** |
| M12 | `futures_oi_1m`, `futoi_w` | do not exist |
| M13 | Box | total 3836 MB, free 2511 MB, **swap 0**, 2 vCPU, Python **3.10.12** |

---

## 3. Process shape: one cron line per minute vs one process per session

**RULED (Q-OP-2): shape (b), one process per session.** The comparison below is kept because the
reasons are load-bearing for §9, §10 and §12, and because the ruling's cost — one ledger row instead
of 377 — turns out not to be covered by an existing watcher (§3.1, §10, §14).

Required comparison. The box figures are M13; the ledger figures are from `core/execution_log.py`.

| | (a) cron every minute | (b) one process per session, cron/timer-started, runs to 15:41 IST |
|---|---|---|
| **Memory** | 377 short-lived interpreters/day, peak ≈ one interpreter + `requests` (~35–50 MB). Nothing accumulates. | One resident process. Working set is 6 rows/min and the day's upsert model (≤ 2,262 rows × ~14 small fields). Bound it as tape does: `MemoryMax`, `MemorySwapMax=0`, `--rss-cap-mb` (`L2_live_runner_2b.service.template:30`, `:38-40`). With swap 0 (M13) an unbounded (b) is an OOM-kill risk; a bounded (b) **fails** instead — the TD-S91-NEW-7 shape. **The two numbers are set by rule, not by guess (Q-OP-1): `MemoryMax = 2 × measured peak RSS`, floor `256M`; `--rss-cap-mb = 1.5 × measured peak RSS`; the peak is the one the replay gate G6 measures. No number is written into the unit template or this plan until G6 has run.** |
| **Restart semantics** | Self-healing by construction: the next minute is a new process. Nothing to restart. **(a)'s one real advantage.** | Needs `Restart=on-failure`, `RestartSec`, `RestartPreventExitStatus`, `StartLimitIntervalSec`/`StartLimitBurst` in `[Unit]` (`L2_live_runner_2b.service.template:13-15`, `:62-64`), plus a model rebuilt from the table at `start()` — the tape guard `live-2b-restart-withheld` (`tests/test_tape_live.py:4761`) exists because rebuilding it from files instead is wrong. |
| **Missed minutes** | **Invisible.** A loaded box skips the firing and nothing records a gap; the only trace is an absent row, indistinguishable from "no contract resolved". | The loop knows it missed a grid point and says so — tape stops on `missed_grid_point` (`services/tape_live/dbwrite.py:460-468`). |
| **`script_execution_log` volume** | **377 rows/day** (one row per invocation, `core/execution_log.py:319-343`, `:353-418`), each 2 HTTP calls → 754 ledger round-trips/day; ≈ 95,000 rows/year for this writer alone. | **1 row/day**, plus at most 2 child rows (`core/execution_log.py:442-463`); ≈ 253–759/year. |
| **Failure visibility** | 377 independent chances to alert; a systematic failure is loud. But a *silent* failure (resolver returns 0 rows) is 377 quiet `contract_met=False` rows nobody reads — the `delivered=False` anti-pattern. | One ledger row + a heartbeat file. A dead process leaves the row at `exit_reason='RUNNING'` with no `finished_at` and no aging timestamp (`core/execution_log.py` has **no heartbeat**). **No scheduled watcher sees that — measured, §3.1.** This is (b)'s real cost and it is not mitigated inside this lane. |
| **"At most one quote call per minute" (req. 3)** | Needs a cross-process lock file. A stale lock silences the whole day; a lock is a new failure mode with no watcher. | An in-memory flag. Trivially provable. |
| **"Contracts resolved once per session" (req. 4)** | Impossible without a disk cache, which is a second source of truth for the contract set. | A local variable. |
| **`CONNECTION LIMIT 1` (F12)** | A minute that overruns while the next starts → the second connection is refused (`FATAL: too many connections for role …`, the text tape recognises at `services/tape_live/dbwrite.py:81`). At 377 invocations/day this is routine, not exceptional. | One connection held for the day. |
| **Dhan second `:30` (F9)** | `cron` has minute granularity; `:30` needs an in-process `sleep 30` in every invocation — 377 processes each sleeping 30 s, i.e. half the wall clock of the day spent in idle interpreters. | One scheduler computes the next `:30` boundary and sleeps to it, as tape's clock does (`services/tape_live/cli.py:529` `--clock {real,sim}`). |

### Why (b) was the right ruling

Four of the requirements — one call per minute, resolve once per session, second `:30`, and
`CONNECTION LIMIT 1` — are each either impossible or a new failure mode under (a). (a)'s single
advantage, free restart, is recoverable in (b) with machinery that already exists and is tested
(`L2_live_runner_2b.service.template`, tape guard `live-2b-restart`).

### 3.1 The hung-run monitor does NOT cover this writer — measured

An earlier draft of this plan claimed the existing orchestrator monitor's hung-run probe would see a
dead futoi process. **That claim was wrong and is withdrawn.** Measured, this session, by reading the
file behind `tests/test_monitor_hung_run.py` (which loads
`monitor_orchestrator_health.py`, `tests/test_monitor_hung_run.py:31`):

- `monitor_orchestrator_health.py:121` — `ORCHESTRATOR_SCRIPT = 'run_merdian_shadow_runner_aws.py'`.
- `monitor_orchestrator_health.py:463` — the probe's query is
  `?script_name=eq.{ORCHESTRATOR_SCRIPT}&finished_at=is.null`, with
  `&started_at=lt.{older}&started_at=gte.{day0}` at `:464` and `HUNG_MIN = 6` at `:157`.

So the probe is **scoped to one `script_name`**. A `capture_futures_oi_1m` row sitting at
`exit_reason='RUNNING'` for 6.5 hours matches **no** row the probe selects, and nothing fires. The
converse is equally true and is why this cannot be fixed by simply widening the filter: `HUNG_MIN = 6`
is derived from the orchestrator's own healthy duration (`:150-156`: longest finished run 184.4 s,
healthy by ~305 s), and under that bound a *healthy* 6.5-hour futoi session would page continuously
all day.

**Engine intake item (this lane does not edit the monitor).** The fix is a per-script hung bound — the
probe takes a set of `(script_name, max_minutes)` pairs instead of one name and one constant — so that
`run_merdian_shadow_runner_aws.py` keeps 6 min while `capture_futures_oi_1m` gets a bound above its
session length (e.g. 400 min) plus a separate "no row started today by 09:20 IST" check, since a writer
that never starts leaves no row at all and is invisible to any unfinished-row probe. Filed with
Q-EN-1…6 in §18.

**What the writer does meanwhile.** Nothing automated watches it. The lane's own mitigations, each
stated as what it is:
1. `heartbeat.json` carries `pid`, `state` and `updated_utc` and is rewritten every grid point (§10);
   the install note names it as the one file to look at, and `write-clear` / `--check` already read it
   (§9.4, §8.1).
2. The parent ledger row completes at session end and its **exit code** carries the verdict (§10), so a
   session that *finishes* badly is visible in `script_execution_log`. A session that *dies* is not.
3. G13 (first live day) is operator-watched by construction.
4. Guard `futoi-monitor-gap` (§12) pins `monitor_orchestrator_health.py:121` and `:463` so that if the
   probe is ever widened, the guard fails and this section is revisited rather than quietly becoming
   stale.

### 3.2 Shape of (b), as ruled

`systemd` unit + timer, both copied from `docs/tape/L2_live_runner_2b.service.template` and
`docs/tape/L2_live_runner.timer.template` (`OnCalendar=Mon..Fri 09:10 Asia/Kolkata`, `Persistent=no`,
**installed but not enabled**; first run manual), with these departures from the tape templates:

- **`User=ssm-user`, `Group=ssm-user` — not a dedicated OS user** (operator, change 1). Reason: the
  writer needs the engine's existing credentials — Dhan (`DHAN_CLIENT_ID`, `DHAN_API_TOKEN`) and the
  Supabase credential that `core.trading_calendar_gate` and `core.execution_log` both load
  (`core/trading_calendar_gate.py:65-75`, `core/execution_log.py:84-87`). Copying those to a new user
  widens exposure for no isolation gain, because the new user would then hold the same secrets.
  **Only `FUTOI_W_DSN` is new**, and it lives in its own file.
- **`ProtectHome=read-only`, not `yes`.** `ProtectHome=yes` makes `/home` inaccessible, which would
  break both credential reads below. The out dir is punched back through with `ReadWritePaths`.
- **`MemoryMax` and `--rss-cap-mb` from the G6 rule** (Q-OP-1, §3 table). Not written until measured.
- **`--out /home/ssm-user/futoi-1m`** (RULED, Q-OP-12), with `ReadWritePaths=/home/ssm-user/futoi-1m`.
  That is the fixed root across days, so the cross-day latch and the per-day counter file (§10.1) are
  found on every later day.
- **`WorkingDirectory` is the exported code directory, NOT the engine tree** (RULED, Q-OP-10), which is
  why §6.6 must populate `os.environ` itself.
- `RestartPreventExitStatus=**2 3 4**` — see §3.3.
- Otherwise unchanged: `Type=simple`, `KillSignal=SIGTERM`, `Nice=10`, `CPUQuota=100%`,
  `MemorySwapMax=0`, `OOMPolicy=stop`, `ProtectSystem=strict`, `NoNewPrivileges`, `PrivateTmp`,
  `CapabilityBoundingSet=`, `UMask=0077`, `Restart=on-failure`, `RestartSec=30`,
  `StartLimitIntervalSec=600`/`StartLimitBurst=3` in `[Unit]`.

### 3.3 Exit codes, and why a failing verdict must not restart the unit (operator, change 1)

`Restart=on-failure` restarts on **any** non-zero exit not listed in `RestartPreventExitStatus`, and
on a signal death. The verdict fails at 15:40–15:41, i.e. at the very end of the session — so without
its own code it would land in the restart set and systemd would start a fresh session for a day whose
grid is already over. That new process would find every grid point passed, compute `M = 377`, fail
again, and repeat up to `StartLimitBurst=3` inside `StartLimitIntervalSec=600`: **three extra ledger
rows, three extra start-up checks and three extra `futoi_w` connections for zero rows of work**, with
the last of them tripping the start limit so the unit ends in `failed` for the wrong reason.

| Code | Meaning | Restarted? | Why |
|---|---|---|---|
| **0** | the session ran to 15:40 and **the verdict passed** | no (clean exit) | nothing to do |
| **1** | **an unhandled exception** — a traceback, or `core.execution_log`'s own `atexit` CRASH path (`core/execution_log.py:420-435`, `exit_code=1`) | **YES** | A genuine crash, and the one case where restarting is right: the grid points ahead are still ahead, and `start()` rebuilds the model from the table (§12 `futoi-restart`). The day is partly recoverable |
| **2** | **refused before any work**: a CLI refusal, any of R1–R10, the §6.6 credential refusal | no | The condition lives in the environment, the role or the credential file. Three restarts in 600 s change none of them, and each one opens a `futoi_w` connection against `CONNECTION LIMIT 1` — so retrying a refusal can manufacture the `53300` that §9.2 treats as stop-tier |
| **3** | **memory or disk cap** (`--rss-cap-mb`, `--disk-floor-mb`) | no | Restarting re-runs the same workload against the same cap |
| **4** | **the session completed and its verdict FAILED** (§10.1) | no | **This is a verdict, not a crash.** The process did exactly what it was asked and then reported that the day's data does not meet contract. Nothing a restart can do |
| signal (**134/137/139**) | SIGABRT / SIGKILL / SIGSEGV | **YES** (except the cgroup OOM case, which `OOMPolicy=stop` ends) | Indistinguishable from exit 1 in kind: the process died mid-session |

So: `RestartPreventExitStatus=2 3 4`, and the restart set is exactly **{1, signal deaths}** — both of
which are "the process died with work left", never "the process finished and said no".

**Exit 4 is carried through `exit_with_reason`, with the reason chosen so the ledger `status` is right.**
Measured: `exit_with_reason` passes a caller's `exit_code` through unchanged for a reason in
`VALID_EXIT_REASONS` (`core/execution_log.py:285-299`; the 12 members are at `:91-104`);
`_compute_contract_met` returns `False` whenever `exit_code != 0` (`:345-351`); and `_ledger_status`
maps `SUCCESS` + `contract_met=False` → **`DEGRADED`** and the error family → **`MISSING`**
(`:122-133`). Therefore:

- **Verdict failed on a data clause** (1, 2, 5, 6, 7): `exit_with_reason("SUCCESS", exit_code=4)` →
  `contract_met=False`, `status='DEGRADED'`. The session ran; the day is partial. That is exactly
  ADR-031's DEGRADED.
- **Verdict failed because the writer stopped** (clauses 3, 4):
  `exit_with_reason("DATA_ERROR", exit_code=4)` → `status='MISSING'`.
- A refusal after `core.*` is imported: `exit_with_reason("DEPENDENCY_MISSING", exit_code=2)` →
  `status='MISSING'`. A refusal *before* the import (§6.6) writes no ledger row at all and prints its
  reason — stated because "no row" and "a row saying refused" are different things to whoever reads
  `script_execution_log` tomorrow.

Guard `futoi-heartbeat` asserts the code is **4** and not 1 on a failing verdict, and statically
asserts that the unit template's `RestartPreventExitStatus` line contains 2, 3 **and** 4. Mutants
`VERDICT-EXIT-RESTARTS` (the template drops the `4`) and `VERDICT-EXIT-IS-ONE` (the code path returns
1). **Two mutants, not one**, because they are different defects with different assertions — the first
is caught only by reading the template, the second only by reading the process exit — and one patch
cannot express both.

**Credentials, three sources, none copied:**

| What | Where | Why that place |
|---|---|---|
| `FUTOI_W_DSN` | `/home/ssm-user/.futoi_w_env`, mode 600, owner `ssm-user`, **outside every git tree**, loaded by `EnvironmentFile=` | Q-OP-8: its own file, separate from every other credential. Same convention as `$HOME/.merdian_ro_env` (`bin/roq.sh:16-17`). `MERDIAN_FUTOI_1M_ENABLED` lives in this file too, so the kill switch flips without editing the unit |
| the resolver's read connection | **`MERDIAN_RO_DSN` from the existing `$HOME/.merdian_ro_env`** — measured this session: `-rw------- ssm-user ssm-user 149 /home/ssm-user/.merdian_ro_env`; path and override from `bin/roq.sh:56` (`${MERDIAN_RO_ENV_FILE:-$HOME/.merdian_ro_env}`), mode gate at `:84-88` | The unit runs as `ssm-user`, which already owns that file at mode 600, so **the secret is reused in place and nothing is copied**. There is therefore **no `FUTOI_RO_DSN`** — that variable is withdrawn from §4. The writer re-implements `roq.sh`'s mode check (`:84-88`) and refuses a file that is not `600`/`400`. One cost, stated: the resolver's single connection counts against `merdian_ro`'s `CONNECTION LIMIT 5` (measured) for the few seconds it runs, once per session, shared with interactive `roq.sh` use |
| `DHAN_CLIENT_ID`, `DHAN_API_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | parsed in-process from `/home/ssm-user/meridian-engine/.env` | §6.5 and §6.6. Never printed, never traced, never `cat`-ed (rule 19). **This plan was written without reading that file**; its variable names come from `capture_index_futures_snapshot_local.py:45-48` and `core/trading_calendar_gate.py:67-72` |

Ledger: one parent row per session; one child row (`log_child_run`) if the verdict fails, so the
failure carries its own reason (§10).

**If the operator chooses (a)** instead, the plan changes in four named places and nowhere else:
requirement 3's guard becomes a lock file with its own stale-lock guard and mutant; requirement 4's
"once per session" becomes "once per day, cached in the out dir, with a guard that the cache is not
re-read across days"; `:30` becomes an in-process sleep with a guard that it sleeps from the minute
boundary, not from process start; and §9's consecutive-skip counters move to a counter file in the out
dir (and gain a mutant for a counter that resets on restart). The four cron lines would be
`45-59 3 * * 1-5`, `* 4-9 * * 1-5`, `0 10 * * 1-5`, `10 10 * * 1-5` (box TZ `Etc/UTC`:
09:15 IST = 03:45 UTC, 15:30 = 10:00, 15:40 = 10:10) — 15 + 360 + 1 + 1 = **377**.

---

## 4. Files to add

New files only. Nothing existing is edited **except** `tests/run_offline.sh` (two steps appended) —
argued in §12.

| Path | Lines (est.) | What |
|---|---|---|
| `services/futoi/__init__.py` | 1 | package marker |
| `services/futoi/cli.py` | ~260 | `live`, `write-clear`, `db-literal-check`; `--check` |
| `services/futoi/runner.py` | ~380 | the session loop, clock, heartbeat, ledger, kill file |
| `services/futoi/quote_source.py` | ~170 | the Dhan call, response parse, error classification |
| `services/futoi/contracts.py` | ~130 | the scripmaster resolver (read-only, as `merdian_ro`) |
| `services/futoi/creds.py` | ~90 | the only module that opens a credential file: parses `KEY=VALUE` from an explicit path, checks mode `600`/`400`, returns values, **never prints and never logs**; no `dotenv` |
| `services/futoi/rows.py` | ~110 | block → row mapping, the minute grid, CSV shape |
| `services/futoi/dbwrite.py` | ~420 | **the only module containing write SQL**; upsert construction, start-up check, latch, stop rules |
| `services/futoi/ddl.py` | ~70 | the table's columns/types/keys as data, so the test can read them without parsing SQL |
| `sql/2026-11-28_futoi_futures_oi_1m.sql` | ~150 | §7, one statement per block, every `GRANT`/`COMMENT`/`REVOKE` live |
| `sql/2026-11-28_futoi_data_contracts.sql` | ~40 | §7.6, the two `data_contracts` rows |
| `docs/futoi/futoi_1m_install.md` | ~200 | operator install note, modelled on `docs/tape/L2_live_runner_install.md` (sections 0–11) |
| `docs/futoi/futoi-1m.service.template` | ~64 | from `L2_live_runner_2b.service.template` |
| `docs/futoi/futoi-1m.timer.template` | ~15 | from `L2_live_runner.timer.template` |
| `tests/test_futoi_1m.py` | ~1,950 | the 17 guards, the fakes, `_futoi_selftest` |
| `tests/futoi_1m_mutants.py` | ~400 | the 138 mutants, `--repeat`, `--only`, `--anchor-check` |
| `tests/futoi/fixtures.json` | ~400 | §11 fixtures (recorded Stage 0a responses + the fault variants) |
| `tests/run_offline.sh` | +2 steps | 42 → **44** |

### Env var and flag names

| Name | Where | Meaning |
|---|---|---|
| `MERDIAN_FUTOI_1M_ENABLED` | `/home/ssm-user/.futoi_w_env` (so the switch flips without editing the unit) | must equal `"1"`; anything else ⇒ exit 0 before any Dhan call. **No tape analogue** — tape has no enable variable at all: its switch is `--db-write` **plus** the DSN, each without the other being a refusal (`services/tape_live/cli.py:277-282`). This variable is requirement 1's addition |
| `FUTOI_W_DSN` | `/home/ssm-user/.futoi_w_env`, mode 600, owner `ssm-user`, loaded by `EnvironmentFile=` | the `futoi_w` DSN. Popped from `os.environ` at start, as tape pops `TAPE_LIVE_W_DSN` (`services/tape_live/cli.py:255`, `:272`) |
| ~~`FUTOI_RO_DSN`~~ | **withdrawn** | The resolver reads `MERDIAN_RO_DSN` from the existing `$HOME/.merdian_ro_env` in place (§3.2). A second variable would mean a second copy of the same secret |
| `MERDIAN_RO_ENV_FILE` | optional override, test only | the same name and default `bin/roq.sh:56` uses, so the guards can point the resolver at a fixture credential file without inventing a new variable |
| `MERDIAN_FUTOI_ENGINE_ENV` | optional override, test only | the path the writer parses Dhan and Supabase values from; default `/home/ssm-user/meridian-engine/.env`. Exists so the guards never touch the real file |
| `DHAN_CLIENT_ID`, `DHAN_API_TOKEN` | **not taken from `os.environ`** — re-read per call from the engine `.env` (§6.5) | as the engine already names them (`capture_index_futures_snapshot_local.py:47-48`) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | set into `os.environ` **before** `core.*` is imported (§6.6) | `core/execution_log.py:86-87` binds them at import; `core/trading_calendar_gate.py:65-75` re-reads them per call |
| `FUTOI_TEST_REDATE` | test only | the re-dated run, as `TAPE_LIVE_TEST_REDATE` (`services/tape_live/dbwrite.py:45`) |

`MERDIAN_FUTOI_1M_ENABLED` semantics: **unset is OFF.** The variable must equal the exact string `"1"`
to enable. Requirement 1 says `=0` exits 0; making unset also exit 0 costs nothing and removes the
"deployed but never configured, silently live" case.

Flags on `futoi live`: `--day`, `--out`, `--clock {real,sim}`, `--start`, `--db-write`,
`--db-batch-rows N`, `--check`, `--kill-file`, `--rss-cap-mb`, `--disk-floor-mb`, `--test-redate-today`.
On `futoi write-clear`: `--out` (required), `--note` (required), `--day`, `--test-redate`.
`futoi db-literal-check`: no arguments. (Shape from `services/tape_live/cli.py:504-547`.)

---

## 5. Off by default (requirement 1)

Two independent switches, neither of which the other can satisfy:

1. **`MERDIAN_FUTOI_1M_ENABLED != "1"` ⇒ exit 0 before any Dhan call.** Checked as the first thing
   after argument parsing, **before** the credential read, **before** the calendar gate, **before** any
   socket. Guard `futoi-off` asserts the Dhan fake recorded **zero** calls.
2. **No `--db-write` ⇒ dry run.** The rows are built, printed and appended to the day's CSV; the sink is
   never constructed. `FUTOI_W_DSN` present without the flag is a **refusal**, not a silent dry run —
   tape's `M-W-DSN-IGNORED` mutant exists precisely because that branch is easy to delete
   (`tests/tape_live_mutants.py:174`).

---

## 6. Session, contracts and row

### 6.1 Session (requirement 3)

Grid: every minute `09:15 … 15:30` inclusive, plus `15:40`, each at second `:30` — 377 points.
The gate is `core.trading_calendar_gate`, **imported, not copied**:
`assert_trading_day_or_exit(log)` (`core/trading_calendar_gate.py:218`) once at start-up, before the
resolver and before any Dhan call. A closed day exits via
`log.exit_with_reason("HOLIDAY_GATE")` → exit **0** (`:227`; `core/execution_log.py:276-282`).
Fail-open is preserved exactly as that module defines it: only a *computed* closure returns False
(`core/trading_calendar_gate.py:136-140`); credentials missing, non-200, exception, and "no row + rule
engine unavailable" all allow the run (`:89-92`, `:112`, `:113-116`, `:142-146`).

One quote call per minute, enforced by a per-grid-point in-memory flag; a second attempt within the same
grid point is a refusal with its own reason, not a second call.

### 6.2 Contracts (requirement 4)

Resolved **once**, at start-up, from `public.dhan_scripmaster` as **`merdian_ro`**, over
`MERDIAN_RO_DSN` read in place from `$HOME/.merdian_ro_env` (§3.2; path and override from
`bin/roq.sh:56`, mode gate re-implemented from `:84-88`). That read path is proven: this plan's M1–M3
were obtained through it. The resolver uses the existing resolver's columns and filter
(`capture_index_futures_snapshot_local.py:153-172`) **plus `LOT_SIZE`** and **minus the
`limit 20`/take-`[0]`** behaviour:

- select: `"SECURITY_ID","DISPLAY_NAME","INSTRUMENT","INSTRUMENT_TYPE","UNDERLYING_SYMBOL","SM_EXPIRY_DATE","SEGMENT","EXCH_ID","LOT_SIZE"`
- where: `"UNDERLYING_SYMBOL" = <symbol>`, `"INSTRUMENT" = 'FUTIDX'`, `"SM_EXPIRY_DATE" >= <today IST>`
- order: `"SM_EXPIRY_DATE"` ascending; take the **first 3** per symbol
- `expiry_rank` = 1, 2, 3 by that order
- `lot_size` = `int(float(LOT_SIZE))` — the column is text and reads `65.0` / `20.0` / `25.0` (M1, M2)
- marketfeed segment from **`EXCH_ID`**: `NSE` → `NSE_FNO`, `BSE` → `BSE_FNO`. **Not** from `SEGMENT`
  (which is `D` for both, M3) and **not** from `INSTRUMENT_TYPE` (which differs by exchange, M3)
- `<today IST>` is `datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()`. The existing resolver's
  naive `datetime.now()` (`capture_index_futures_snapshot_local.py:96-101`) is **not** copied

Fewer than 3: write what resolves, record `contracts_resolved` per symbol, emit a **WARNING**, never
substitute, never pad. Today that path is the live one, not the exceptional one (M2: 2 per symbol).

**Zero resolved for one symbol (RULED, Q-OP-7): write the symbol that resolves; the day's verdict
fails.** The run does not refuse and does not stop — the other index's minute series is worth having —
but clause 5 of the verdict (§10) is false, so the process exits non-zero and the ledger row says which
symbol was empty. Zero for **both**: `exit_with_reason("DATA_ERROR", exit_code=1)` before any Dhan call.

`contracts_resolved` is recorded in the **run** record — heartbeat, `live_metrics.csv`, and the ledger
row's `notes` — not as a table column, because requirement 5's row list does not contain it and a
per-row copy of a per-session fact is a second source of truth.

### 6.3 Row (requirement 5)

| Column | Type | Source | Note |
|---|---|---|---|
| `symbol` | `text` | resolver | `NIFTY` / `SENSEX` |
| `expiry_date` | `date` | `SM_EXPIRY_DATE` | |
| `ts` | `timestamptz` | the grid point | **start of the IST minute, stored as true UTC**. `09:15:00+05:30` → `03:45:00+00:00`. Never the call instant, never IST labelled `+00:00` (rule 16) |
| `trading_day` | `date` GENERATED STORED | `(ts AT TIME ZONE 'Asia/Kolkata')::date` | **departure D-1**, see §13. Legal: M9 |
| `expiry_rank` | `smallint` | resolver order | 1–3, CHECK |
| `security_id` | `bigint` | resolver | |
| `lot_size` | `integer` | `LOT_SIZE` | per row, per F4 |
| `ltp` | `numeric(14,4)` | `last_price` | |
| `oi` | `bigint` | `oi` | **index units** (F3). Never divided here |
| `volume` | `bigint` | `volume` | **index units** (F3) |
| `last_trade_time_raw` | `text` | `last_trade_time` | **verbatim**, `DD/MM/YYYY HH:MM:SS`. No parsed column until Stage 0b establishes the zone (F5) |
| `captured_at` | `timestamptz` | the response-received instant, UTC | |
| `source` | `text` | constant | `dhan:/v2/marketfeed/quote` |

**Absent key ⇒ NULL, never 0** (F6). The mapping is explicit per key: `blk.get(k)` with a sentinel, and
`"" / None` → SQL `NULL`. `oi_day_high`/`oi_day_low` are **not** stored (not in requirement 5), so the
genuine-zero-vs-absent ambiguity at `futoi_stage0a_fields_2026-11-28.md:76` never enters the table.

### 6.4 Files first (requirement 6)

Per day: `<out>/<ISO day>/futoi_rows.csv`, header = the column tuple from `services/futoi/ddl.py`,
appended once per grid point **before** the sink is called, `flush()` + `os.fsync()` before the upsert
is attempted. Also per day: `live_metrics.csv` (one row per grid point), `heartbeat.json`,
`runner.log`, and on a stop `WRITE_STOPPED`.

The guard that makes this a check rather than a comment: for every grid point, **the set of rows the
sink was handed equals the set of rows appended to that minute's section of the CSV, compared by
DB-typed value with NULL = NULL** — not by count. A count-only comparison passes when two rows are
swapped; tape's `W1`/`W3` compare by typed value for that reason
(`tests/tape_live_write_checks.py:9-13`).

### 6.5 Dhan credentials are read at use, not held (operator, change 2)

The Dhan token is re-minted daily at **08:20 IST**, and a 6.5-hour session that read it once at
start-up would be holding a value that may be replaced under it. So:

- **`DHAN_CLIENT_ID` and `DHAN_API_TOKEN` are re-read from `/home/ssm-user/meridian-engine/.env`
  in-process before every call** — 377 reads a day of a small file. Parsed as `KEY=VALUE` by
  `services/futoi/creds.py`: explicit path (never a bare `load_dotenv()`, per
  `.claude/rules/ops-shell.md`), strip an optional surrounding quote pair, take the **last**
  assignment of a key, ignore blanks and `#` comments. **The values never enter `os.environ`**, so
  they cannot reach any child process, and they are **never printed, logged, echoed, interpolated into
  an error message or included in a heartbeat** (rule 19). The path is overridable only by
  `MERDIAN_FUTOI_ENGINE_ENV`, which exists so the guards point at a fixture.
- **This plan was written without opening that file.** The two variable names come from
  `capture_index_futures_snapshot_local.py:47-48`; the file's contents are not known here and are not
  needed.

**Auth failure handling — day-scoped, and NOT the cross-day latch.** On `401`, `403` or a `DH-901`
body:

1. **Re-read the credential once**, immediately, and record `token_rereads += 1`. The call is **not**
   retried inside the same grid point (requirement 3 permits one call per minute); the retry is the
   **next** grid point, with the freshly-read token.
2. If the **next** grid point's call also returns `401`/`403`/`DH-901`, that is a **second consecutive
   auth failure**: Dhan calls stop **for the rest of that day only**. Heartbeat reason
   `dhan_auth_stopped`; a per-day sentinel `<out>/<day>/DHAN_AUTH_STOPPED`; the day's verdict fails.
3. **No cross-day latch is written.** The cross-day latch (`<out>/FUTOI_WRITE_LATCH.json`, §9.1) is for
   **DB stop-tier faults only**. The next trading day calls Dhan again with **no `write-clear`** — a
   token that has since been re-minted is the normal case, and requiring an operator action to resume
   after an expired token would convert every missed rotation into a lost day.

Guards and mutants for all three: `TOKEN-HELD-FROM-START`, `AUTH-NO-REREAD`, `AUTH-STOPS-ON-FIRST`,
`AUTH-LATCHES`, `AUTH-CARRIES-TO-NEXT-DAY` (§13).

### 6.6 The calendar gate's credential, and the import order it forces (operator, change 3)

Two facts, both read from the modules this session:

- `core/trading_calendar_gate.py:65-75` (`_creds()`) reads `SUPABASE_URL` and
  `SUPABASE_SERVICE_ROLE_KEY` and calls a **bare `_load_dotenv()`** if either is empty — a
  cwd-and-parents search. The unit's `WorkingDirectory` is the exported code directory, **not** the
  engine tree, so that search finds nothing and the gate fails open on "no creds"
  (`:89-92`, `return True`). A gate that fails open on every run is not a gate.
- `core/execution_log.py:84-87` binds `_SUPABASE_URL` / `_SUPABASE_KEY` at **module import time**. A
  value set into `os.environ` *after* the import is never seen, and the ledger silently disables itself
  (`:320-323` sets `_finalised = True`).

Therefore, in this exact order, before anything else:

1. Parse `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from the engine `.env` via
   `services/futoi/creds.py`.
2. **If either is absent or empty, refuse: exit 2, no Dhan call, no import of `core.*`.** Printed
   reason: `refused: the calendar gate credential is not available`. The value is never printed — the
   check is a presence test on a non-empty string, the `[ -n "$VAR" ] && echo set` form of rule 19.
3. Set both into `os.environ`.
4. **Then** `import core.trading_calendar_gate` and `import core.execution_log`.
5. Open the `ExecutionLog`, then `assert_trading_day_or_exit(log)`.

The gate's own fail-open on a **genuine** error stays exactly as the module defines it — non-200,
exception, and "no row + rule engine unavailable" all allow the run (`:112`, `:113-116`, `:142-146`);
only a **computed** closure returns False (`:136-140`). What changes is only that "no credential" can
no longer masquerade as that fail-open, because the writer has already refused.

Guards and mutants: `GATE-CRED-MISSING-RUNS` and `IMPORT-BEFORE-ENV` (§13).

---

## 7. DRAFT SQL for the engine

Each statement in its own block, per the brief. `COMMENT`, `GRANT` and `REVOKE` are **live statements,
never commentary** (`§D.81`). **Apply as `postgres`, not `supabase_admin`** (M8). The operator applies;
the engine authors.

Two precedents, and they differ — the choice above is deliberate:

- `sql/2026-11-06_tape_live_tables.sql` wraps **everything in one `BEGIN;`…`COMMIT;`** (`:9`, `:176`),
  because four tables plus policies plus grants are one unit and a half-applied set is the S81 part-run
  defect. It is also rendered, never hand-edited (`services/tape_live/ddl.py:99-126`), with a guard
  asserting the committed file equals `render()`.
- `sql/2026-11-03_s104_marketview_ro_role.sql:1-8` is **statement per block**, no transaction wrapper,
  and is the canonical **role** file: `CREATE ROLE … LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION CONNECTION LIMIT 8;` followed by three `ALTER ROLE … SET …;` and `GRANT USAGE ON SCHEMA
  public …;`. It ships with a named rollback file,
  `sql/2026-11-03_s104_marketview_ro_role_ROLLBACK.sql`.

**`tape_w` is created by no SQL file on the tape ref** — the role exists in the database (M4) with no
committed DDL; the only mentions are the install note, `dbwrite.py` and the tests. `futures_oi_1m` must
not repeat that: `futoi_w`'s `CREATE ROLE`, its two `ALTER ROLE SET`s and its grants ship as files, with
a rollback file beside them.

### 7.0 Preflight (one statement)

```sql
DO $v$ BEGIN
  IF current_setting('server_version_num')::int < 120000 THEN
    RAISE EXCEPTION 'futoi: GENERATED ... STORED needs PostgreSQL >= 12, server is %', current_setting('server_version');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'merdian_ro') THEN
    RAISE EXCEPTION 'futoi: role merdian_ro does not exist; create it before this file';
  END IF;
  IF current_user <> 'postgres' THEN
    RAISE EXCEPTION 'futoi: apply as postgres, not %, or the table comes up with anon privileges (pg_default_acl)', current_user;
  END IF;
END $v$;
```

That third clause is the measured M8 hazard turned into a refusal, not a comment.

### 7.1 Table

```sql
CREATE TABLE public.futures_oi_1m (
    symbol               text        NOT NULL,
    expiry_date          date        NOT NULL,
    ts                   timestamptz NOT NULL,
    trading_day          date        NOT NULL GENERATED ALWAYS AS (((ts AT TIME ZONE 'Asia/Kolkata'))::date) STORED,
    expiry_rank          smallint    NOT NULL,
    security_id          bigint      NOT NULL,
    lot_size             integer     NOT NULL,
    ltp                  numeric(14,4),
    oi                   bigint,
    volume               bigint,
    last_trade_time_raw  text,
    captured_at          timestamptz NOT NULL,
    source               text        NOT NULL,
    CONSTRAINT futures_oi_1m_pk PRIMARY KEY (symbol, expiry_date, ts),
    CONSTRAINT futures_oi_1m_rank_ck CHECK (expiry_rank BETWEEN 1 AND 3),
    CONSTRAINT futures_oi_1m_lot_ck  CHECK (lot_size > 0),
    CONSTRAINT futures_oi_1m_sec_ck  CHECK (ts = date_trunc('minute', ts))
);
```

### 7.2 Index

```sql
CREATE INDEX ix_futures_oi_1m_trading_day ON public.futures_oi_1m USING btree (trading_day);
```

```sql
CREATE INDEX ix_futures_oi_1m_symbol_ts ON public.futures_oi_1m USING btree (symbol, ts);
```

### 7.3 Role

Shape copied from `sql/2026-11-03_s104_marketview_ro_role.sql:4-7`, minus
`default_transaction_read_only` (which `w_env` is careful never to let reach a write path:
`services/tape_live/live_sources.py:127-129`).

```sql
CREATE ROLE futoi_w LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 1;
```

`NOBYPASSRLS` is the default and is not spelled; the start-up check reads `rolbypassrls` directly
(R3b), which is the assertion that matters.

```sql
ALTER ROLE futoi_w SET statement_timeout = '15s';
```

```sql
ALTER ROLE futoi_w SET idle_in_transaction_session_timeout = '10s';
```

> **The password is generated by the operator (RULED, Q-OP-8) and appears in no repo file, no commit,
> no chat message and no log** — `ALTER ROLE futoi_w PASSWORD '<generated>';` run in the editor and
> discarded. The resulting `FUTOI_W_DSN` lives in `/home/ssm-user/.futoi_w_env`, mode 600, owner
> `ssm-user`, **separate from every other credential** (§3.2). This is the one documented exception to
> "every statement ships live in the `sql/` file"; the file carries the statement **shape** in a
> comment and a post-apply check that `rolpassword` is set (§7.8).

### 7.4 Grants and revokes

```sql
GRANT USAGE ON SCHEMA public TO futoi_w;
```

```sql
GRANT SELECT, INSERT, UPDATE ON public.futures_oi_1m TO futoi_w;
```

```sql
GRANT SELECT ON public.futures_oi_1m TO merdian_ro;
```

```sql
REVOKE ALL ON public.futures_oi_1m FROM anon, authenticated;
```

### 7.5 RLS

```sql
ALTER TABLE public.futures_oi_1m ENABLE ROW LEVEL SECURITY;
```

```sql
CREATE POLICY futoi_w_insert ON public.futures_oi_1m FOR INSERT TO futoi_w
    WITH CHECK (trading_day = ((now() AT TIME ZONE 'Asia/Kolkata'))::date);
```

```sql
CREATE POLICY futoi_w_update ON public.futures_oi_1m FOR UPDATE TO futoi_w
    USING      (trading_day = ((now() AT TIME ZONE 'Asia/Kolkata'))::date)
    WITH CHECK (trading_day = ((now() AT TIME ZONE 'Asia/Kolkata'))::date);
```

```sql
CREATE POLICY futoi_w_select ON public.futures_oi_1m FOR SELECT TO futoi_w
    USING (trading_day = ((now() AT TIME ZONE 'Asia/Kolkata'))::date);
```

```sql
CREATE POLICY merdian_ro_select ON public.futures_oi_1m FOR SELECT TO merdian_ro USING (true);
```

`futoi_w` needs `SELECT` as well as `INSERT`/`UPDATE` because the upsert's model is rebuilt from the
table at `start()` and after a restart (M5: `tape_w=arw` is exactly this). It is day-scoped, so the
writer can never read another day.

### 7.6 COMMENTs

```sql
COMMENT ON TABLE public.futures_oi_1m IS
'FOI Stage 1 (docs/research/futoi/stage1/futoi_stage1_writer_plan.md). One row per index-futures contract per minute, 09:15-15:30 IST plus 15:40, captured at second :30 from Dhan POST /v2/marketfeed/quote. Up to 3 monthly contracts per symbol (NIFTY, SENSEX). Writer: services/futoi as role futoi_w (INSERT/UPDATE only, RLS to the IST trading day). Owner: operator. Tier: research. Operator-only: no Marketview or retail surface reads this relation and nothing in it is evidence under any pre-registration.';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.oi IS
'Open interest in INDEX UNITS as the vendor returns it, never contracts. Contracts = oi / lot_size, and lot_size differs between contracts of one index (SENSEX 20 and 25 on 2026-11-28). Verified oi mod lot_size = 0 on 4 of 4 instruments on 3 of 3 samples (docs/research/futoi/stage0/futoi_stage0a_fields_2026-11-28.md sections b-c).';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.volume IS
'Traded volume in INDEX UNITS, never contracts. Contracts = volume / lot_size. Same evidence as oi.';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.lot_size IS
'Units per contract for THIS contract, from dhan_scripmaster."LOT_SIZE" (text in the source, e.g. 65.0). Per row, not per symbol: SENSEX DEC 2026 is 20 and SENSEX JAN 2027 is 25.';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.ts IS
'Start of the IST minute the row belongs to, stored as true UTC. 09:15 IST is 03:45Z. This relation does NOT follow the hist_* convention of an IST clock labelled +00:00 (CLAUDE.md rule 16); the capture instant is captured_at, which is later than ts by about 30 seconds.';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.last_trade_time_raw IS
'Vendor string, stored verbatim: DD/MM/YYYY HH:MM:SS, no timezone marker and no sub-second field. The zone is NOT established (futoi_stage0a_fields_2026-11-28.md NOT VERIFIED 3); IST is not asserted. No parsed column exists until Stage 0b establishes it.';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.captured_at IS
'When the response that produced this row was received, in true UTC. Normally about 30 s after ts, because the call is made at second :30 of the minute ts names. A captured_at far from its ts means the grid slipped; it is provenance, never a time axis — every query groups and joins on ts.';
```

```sql
COMMENT ON COLUMN public.futures_oi_1m.trading_day IS
'The IST calendar day of ts, generated and stored. It exists because the RLS policies compare against it; it is not independent data.';
```

**Comment inventory, so §7.8 can assert a number instead of a guess (operator, change 6):** this
section writes **8** `COMMENT` statements — 1 on the table and 7 on columns (`oi`, `volume`,
`lot_size`, `ts`, `last_trade_time_raw`, `captured_at`, `trading_day`). The `captured_at` comment was
**added here** for that purpose and because `captured_at` vs `ts` is the trap a reader hits first.
§7.8 expects 1 and 7, split by `objsubid`, not a single total.

### 7.7 `data_contracts` rows — ENGINE-AUTHORED DRAFT, not applied

Two rows, one per symbol scope, as `gamma_metrics` does. `expected_per_cycle` is a **range**, never a
floor (rule 0 clause 1). Per minute, per symbol, 1–3 contracts resolve.

**Measured through `bin/roq.sh` as `merdian_ro`, this session (operator, change 7):**

| Query | Result |
|---|---|
| `SELECT calendar, count(*) FROM public.data_contracts GROUP BY calendar` | **`BSE_FO` 12, `NSE_FO` 14** — those two values and no others |
| `SELECT cadence_min, freshness_sla_min, count(*), string_agg(relation_name,…) … GROUP BY 1,2` | `1 / 5` → 2 rows (`market_spot_snapshots` × 2 symbols); `5 / 10` → 10 rows (`gamma_metrics`, `gex_cycle_history`, `gex_strike_snapshots`, `option_chain_snapshots`, `weighted_constituent_breadth_snapshots`); `1440 / 1440` → 13 rows (`equity_intraday_last`, the six `tape_*`); `1440 / 2880` → 1 row (`breadth_indicators_daily`) |

So `calendar` is set from what exists: **`NSE_FO`** for NIFTY, **`BSE_FO`** for SENSEX. No new value is
introduced.

**`freshness_sla_min` is derived, not copied.** The one existing 1-minute product
(`market_spot_snapshots`) uses `5`, and **5 would be wrong here**: this writer's grid has a deliberate
**10-minute gap** between its last two points, 15:30 → 15:40. Worst-case age of the newest `ts` inside
the session is reached just before the 15:40 row lands: at 15:40:29 the newest `ts` is 15:30:00, an age
of **10 min 29 s** (the row is written at second `:30`, while `ts` names the start of its minute, so
the age measured from `ts` exceeds the wall gap by that offset). Rounding up and adding one minute of
margin for the upsert itself gives **`freshness_sla_min = 12`**. The constraint `freshness_sla_min > 0`
(M10) is satisfied; `12 > 11` is the thing that matters, and the derivation is written here so a later
reader can falsify it rather than re-guess it.

`movement_window_cycles` is `1`, the minimum the CHECK allows (M10), because `movement_cols` is empty
and the column is then inert.

**The `INSERT` below is engine-authored draft. The operator applies it; nothing in this lane runs it.**

```sql
INSERT INTO public.data_contracts
 (product, relation_name, scope_symbol, scope_col, time_col, grain, cadence_min, freshness_sla_min,
  expected_per_cycle, movement_cols, movement_window_cycles, calendar, tier, writer, owner, access_rls,
  change_reason, session_end_ist)
VALUES
 ('futures_oi_1m:NIFTY', 'futures_oi_1m', 'NIFTY', 'symbol', 'ts',
  ARRAY['symbol','expiry_date','ts'], 1, 12,
  '{"rows": [1, 3]}'::jsonb, '{}'::text[], 1, 'NSE_FO', 3,
  'services/futoi (capture_futures_oi_1m, role futoi_w)', 'operator', 'ENABLED_WITH_RO_POLICY',
  'FOI Stage 1 seed 2026-11-28: 377 grid points per day (09:15-15:30 inclusive plus 15:40, second :30); rows per cycle 1-3 = contracts resolved from dhan_scripmaster, which held 2 of 3 per symbol on 2026-11-28; freshness 12 min is derived from the deliberate 15:30->15:40 gap (worst-case age 10m29s at 15:40:29) and NOT copied from market_spot_snapshots, which is 1/5; movement_cols is empty BY DECISION, see the note below.',
  '15:40'::time),
 ('futures_oi_1m:SENSEX', 'futures_oi_1m', 'SENSEX', 'symbol', 'ts',
  ARRAY['symbol','expiry_date','ts'], 1, 12,
  '{"rows": [1, 3]}'::jsonb, '{}'::text[], 1, 'BSE_FO', 3,
  'services/futoi (capture_futures_oi_1m, role futoi_w)', 'operator', 'ENABLED_WITH_RO_POLICY',
  'FOI Stage 1 seed 2026-11-28: as NIFTY. SENSEX lot size differs between contracts (20 and 25), so any contracts figure must divide per row.',
  '15:40'::time);
```

**`movement_cols` is empty by decision, and the decision is the interesting part.** A movement check on
`oi` at 1-minute cadence would fire on quiet contracts, not on frozen writers: the far-month SENSEX leg
measured `oi = 25` units — one contract — with a 10:18:01 last trade
(`futoi_stage0a_farmonth_2026-11-28.md:25`), i.e. legitimately flat for five hours. A window short
enough to catch a freeze cannot tell that apart from the contract. The freeze detection therefore lives
in the writer's own end-of-day self-check — **distinct `ltp` count per symbol on `expiry_rank = 1`** —
which is the ADR-030 `distinct_spot` lesson applied: 83 frozen cycles pass a row count and a distinct-`ts`
count and fail only on a distinct *value* count. Threshold and derivation in §9.

### 7.8 Post-apply verification (the operator runs it, in one execution)

```sql
BEGIN;
SET LOCAL ROLE postgres;
SELECT current_user AS role_now,
       (SELECT relacl::text FROM pg_class WHERE oid = 'public.futures_oi_1m'::regclass) AS acl,
       (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.futures_oi_1m'::regclass) AS rls,
       (SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename='futures_oi_1m') AS n_policies,
       (SELECT count(*) FROM pg_description d
         WHERE d.objoid = 'public.futures_oi_1m'::regclass AND d.objsubid = 0) AS n_table_comments,
       (SELECT count(*) FROM pg_description d
         WHERE d.objoid = 'public.futures_oi_1m'::regclass AND d.objsubid > 0) AS n_col_comments,
       (SELECT count(*) FROM public.data_contracts WHERE relation_name='futures_oi_1m') AS n_contracts,
       (SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname='futoi_w') AS pw_set,
       (SELECT rolconnlimit FROM pg_roles WHERE rolname='futoi_w') AS connlimit;
COMMIT;
```

Expected, each stated **before** the run and each falsifiable: `role_now = postgres`;
`acl` contains `futoi_w=arw` and `merdian_ro=r` and **no `anon`** and **no `d`/`D` for futoi_w**;
`rls = t`; `n_policies = 4`; **`n_table_comments = 1` and `n_col_comments = 7`** — counted against the
eight `COMMENT` statements §7.6 actually writes, split by `objsubid` so a missing column comment cannot
be masked by the table comment; `n_contracts = 2`; `pw_set = t`; `connlimit = 1`. The role switch and
the counts are in **one execution** because the Supabase editor opens a new session per run
(`§D.40.1`).

An earlier draft of this block expected `n_comments = 8` against a §7.6 that wrote only 7 — a total
that could not be reached, on a count that would not have said which object was missing. Both halves
are fixed above: the eighth comment is real (`captured_at`) and the count is split.

---

## 8. Write path (requirement 7) and start-up refusals (requirement 8)

### 8.1 Write path

- **All write SQL text lives in `services/futoi/dbwrite.py` and nowhere else.** No `subprocess` import,
  no network-module import in that file; the sink is injected. Tape's `g_2b_confined` checks exactly
  this by `ast` and by scanning every *other* module's string constants for write verbs
  (`tests/test_tape_live.py:4733-4758`).
- **Sink** (`FutoiPsqlWriteSink`, modelled on `PsqlWriteSink`,
  `services/tape_live/live_sources.py:282-303`): `psql` with the script on **stdin**, two argv shapes
  and nothing else —
  `["psql","-X","-q","-t","--csv","-f","-"]` for the start-up and literal checks,
  `["psql","-X","-f","-"]` for a script run. The DSN is decomposed into libpq `PG*` variables so **no
  value is ever in argv** — the same construction `bin/roq.sh:179-191` uses for the read role, and the
  property tape asserts (`tests/test_tape_live.py:4702-4705`).
- **Child environment is a strict allowlist** (`w_env`, `services/tape_live/live_sources.py:126-134`):
  `PATH`, `LANG`, `SystemRoot` carried over from the parent, plus `PGHOST`, `PGPORT`, `PGUSER`,
  `PGPASSWORD`, `PGDATABASE`, `PGSSLMODE`, `PGCONNECT_TIMEOUT = "5"`,
  `PGAPPNAME = "futoi-1m-writer"`. **No `PGOPTIONS` on the write path, deliberately** — the role owns
  its statement/idle/connection limits, and `pg_env`'s `default_transaction_read_only=on` must never
  reach a write (`live_sources.py:116-123`, `:127-129`). The guard asserts set-difference against the
  allowlist and that `default_transaction_read_only` is absent (tape's cell 10d/e,
  `tests/test_tape_live.py:4706-4710`).
- **Stderr is classified and dropped, never returned or stored** (`live_sources.py:283-286`,
  `:90-97`). Anything that does reach a log or heartbeat goes through `scrub()`
  (`live_sources.py:146-158`): every known secret value replaced, plus a `scheme://user:pass@` URI, a
  JWT shape and an AWS access-key shape, truncated to 200 chars. The known-secret list is a plain list
  threaded from the CLI (`cli.py:306`, `:317`, `:348`, `:380`) — **there is no function named
  `redact`**; operator-supplied text is scrubbed too (`cli.py:452`).
- **Script shape**, from `services/tape_live/dbwrite.py:71-73`:
  `\set ON_ERROR_STOP 1` / `\set VERBOSITY sqlstate` / `\timing on` / `BEGIN;` /
  `SET LOCAL standard_conforming_strings = on;` / `SET LOCAL lock_timeout = '5s';` / the INSERTs /
  `COMMIT;`. `\set VERBOSITY sqlstate` is what makes the SQLSTATE readable by the classifier;
  `statement_timeout` is **not** set here because it belongs to the role.
  Timeout on the child process: 60 s, surfaced as rc 124 (`live_sources.py:33`, `:69-70`).
- **One upsert per grid point: one `psql` process, which opens one connection, writes one transaction
  and exits.** Connections are **not** held between grid points — an earlier draft said "one
  connection for the day", which is wrong for a sink that runs `psql` per cycle. Batches of
  `--db-batch-rows` (default 500, `services/tape_live/dbwrite.py:48`) — at ≤6 rows a minute, one
  statement.

  **What `CONNECTION LIMIT 1` therefore buys, restated precisely (operator, change 8).** Three
  connections exist in the design, and all three are serial within the writer:

  | Connection | When | Count at any instant |
  |---|---|---|
  | the model-rebuild `SELECT` | once, inside `start()`, before the first write | 1, then released |
  | the per-grid-point upsert | 377 times, each a fresh `psql` that exits | 1 for well under a second, 377 times |
  | the start-up check | once, inside `start()` (and once per `--check` invocation) | 1, then released |

  So `CONNECTION LIMIT 1` never binds the writer against itself. What it binds is **a second process
  using the role at the same time** — exactly what it is for: it makes "one writer" an enforced
  property rather than an intention, and a `53300` is then positive evidence that something else holds
  the role.

- **`--check` is REFUSED while a heartbeat of today is alive**, by the same liveness test
  `write-clear` uses (`CLEAR_STALE_S = 180`, §9.4). This is a consequence of the two facts above, and
  it is the reason it is written down rather than left to judgement: `--check` is a separate process
  opening its own connection; if it lands in the sub-second window a grid point's upsert holds the
  one permitted connection, the loser gets `FATAL:  too many connections for role "futoi_w"`, which
  `classify` maps to `connection_limit` (§9.2) — a **stop-tier** fault that writes the cross-day latch
  and ends the day's writes. An operator running a read-only sanity check must not be able to stop the
  writer. Refusal message: `refused: a futoi session is running (state <s>, pid <p>, heartbeat <n>s
  old, bound 180s); --check would contend for the one permitted connection`. Guard clause and mutant
  `CHECK-DURING-SESSION` (§12, §13). The alternative — raising the limit to 2 — is rejected because it
  would make a genuine second writer invisible; recorded as **Q-OP-11** for the operator to overturn
  if they prefer that trade.
- **Upsert**: `INSERT INTO public.futures_oi_1m (<cols>) VALUES (…), … ON CONFLICT ON CONSTRAINT
  futures_oi_1m_pk DO UPDATE SET <every non-key column> = EXCLUDED.<col>` — the conflict target is the
  **named constraint**, not a column list (`services/tape_live/dbwrite.py:63-70`, `:41`).
- **Literal rendering** (`lit`, `services/tape_live/dbwrite.py:206-213`): `'<text>'::<DDL type>`, with
  `'` doubled and **no backslash escaping** — which is exactly why
  `standard_conforming_strings = on` is both checked at start-up and `SET LOCAL`-ed. `None` or `""`
  renders bare `NULL` in a nullable column and `''::<ty>` in a `NOT NULL` one; a `0` is never
  conflated, because `"0"` is non-empty and renders `'0'::bigint`. **A NUL byte is a hard refusal**,
  not a literal. (Tape's departure 1 is the lesson: its first full-day run stopped at 10:20 on a
  `23502` because empty-in-a-`NOT NULL`-column was rendered `NULL`,
  `docs/tape/L2_live_runner_plan.md:579-581`. `futures_oi_1m`'s only nullable columns are `ltp`, `oi`,
  `volume`, `last_trade_time_raw`, so futoi cannot hit that — but the branch ships anyway, because the
  next column added might.)
- **Duplicate conflict key inside one write set is refused before sending**, with the keys written to
  `<out>/<day>/db_dupkeys.csv` and reason `dup_conflict_key`
  (`services/tape_live/dbwrite.py:553-564`). This is **not** theoretical for futoi: the PK is
  `(symbol, expiry_date, ts)`, so two scripmaster FUTIDX rows sharing `UNDERLYING_SYMBOL` **and**
  `SM_EXPIRY_DATE` would produce two rows with one key and fail the whole statement. M2 shows distinct
  expiries today; nothing in the table enforces it.
- **No `DELETE` or `TRUNCATE` text anywhere in the write path.** Four layers, copied from tape:
  (i) the privilege names exist **only** in `PRIV_PROBE` and nowhere else in the module
  (`services/tape_live/dbwrite.py:59-61`); (ii) an `ast` walk of every string constant in
  `dbwrite.py` outside `PRIV_PROBE` against a write-verb regex, and every `INSERT` constant must match
  `INSERT INTO public\.futures_oi_1m\b` (tape's `:3620-3645`); (iii) every script actually sent, with
  quoted literals stripped first so data cannot false-trigger it (`:3656-3659`); (iv) every **other**
  `.py` in `services/futoi/` scanned for write verbs (`:4724-4731`).
- `db-literal-check`: `BEGIN READ ONLY; SET LOCAL TIME ZONE 'UTC'; SET LOCAL
  standard_conforming_strings = on; … SELECT '<literal>'::<type>::text …; ROLLBACK;` over the 16-case
  hostile corpus — quote, backslash, comma+semicolon, newline, non-ASCII, `$$x$$ --c /*d*/`,
  `'' ; semi; --`, padded, tab, double quote (`services/tape_live/dbwrite.py:196-203`, `:216-219`).
  Each case's expected server text is written **by hand** before the run; a case whose expectation is
  taken from the run asserts nothing (rule 0 clause 3).

### 8.2 Start-up refusals, before any write

One `psql --csv -t` statement, built as tape builds `CHECK_SQL` (`services/tape_live/dbwrite.py:123-136`):

```sql
SELECT 'role', current_user, NULL, NULL
UNION ALL SELECT 'super', CASE WHEN rolsuper THEN 't' ELSE 'f' END, NULL, NULL FROM pg_roles WHERE rolname = current_user
UNION ALL SELECT 'bypassrls', CASE WHEN rolbypassrls THEN 't' ELSE 'f' END, NULL, NULL FROM pg_roles WHERE rolname = current_user
UNION ALL SELECT 'scs', current_setting('standard_conforming_strings'), NULL, NULL
UNION ALL SELECT 'ist_date', ((now() AT TIME ZONE 'Asia/Kolkata')::date)::text, NULL, NULL
UNION ALL SELECT 'priv', 'futures_oi_1m', 'DELETE',   CASE WHEN has_table_privilege(current_user,'public.futures_oi_1m','DELETE')   THEN 't' ELSE 'f' END
UNION ALL SELECT 'priv', 'futures_oi_1m', 'TRUNCATE', CASE WHEN has_table_privilege(current_user,'public.futures_oi_1m','TRUNCATE') THEN 't' ELSE 'f' END
UNION ALL SELECT 'priv', 'futures_oi_1m', 'INSERT',   CASE WHEN has_table_privilege(current_user,'public.futures_oi_1m','INSERT')   THEN 't' ELSE 'f' END
UNION ALL SELECT 'priv', 'futures_oi_1m', 'UPDATE',   CASE WHEN has_table_privilege(current_user,'public.futures_oi_1m','UPDATE')   THEN 't' ELSE 'f' END
UNION ALL SELECT 'priv', 'futures_oi_1m', 'SELECT',   CASE WHEN has_table_privilege(current_user,'public.futures_oi_1m','SELECT')   THEN 't' ELSE 'f' END;
```

Verdict function, shaped on `services/tape_live/dbwrite.py:152-176`; **the first failing clause is the
reason, and the writer makes no write**:

**Twelve clauses**, each able to fail alone — the split matters: tape splits superuser from BYPASSRLS
and DELETE from TRUNCATE, and splits the server date from the local date so each can fail by itself
(departure 11, `docs/tape/L2_live_runner_plan.md:600-601`). Its guard's own summary line enumerates
exactly eleven (`tests/test_tape_live.py:4416`); futoi adds the SELECT clause, which tape does not need.

| # | Refusal message | Condition |
|---|---|---|
| R1 | the connected role is not the write role | `role != 'futoi_w'` |
| R2 | the write role is the same role as the read connection | `role == <read role>` |
| R3a | the write role is a superuser | `super != 'f'` |
| R3b | the write role bypasses row-level security | `bypassrls != 'f'` |
| R4a | the write role holds DELETE on futures_oi_1m | `priv[DELETE] != 'f'` |
| R4b | the write role holds TRUNCATE on futures_oi_1m | `priv[TRUNCATE] != 'f'` |
| R5 | the write role lacks the write privilege | `priv[INSERT] != 't'` |
| R6 | the write role lacks the change privilege | `priv[UPDATE] != 't'` |
| R7 | the write role cannot read its own table | `priv[SELECT] != 't'` (the model rebuild needs it) |
| R8 | standard_conforming_strings is not on | `scs != 'on'` |
| R9 | the server date is not the date the run is written for | `ist_date != <target>` |
| R10 | the local date is not the date the run is written for | `local_today != <target>` |

`<target> = local_today if redate else run_day` (`services/tape_live/dbwrite.py:171`).

There are also **CLI-level refusals before any connection**, copied from
`services/tape_live/cli.py:269-297`: the write DSN set without `--db-write`; `--db-write` without the
DSN; a malformed DSN; no code sha; a batch size below 1; and the five re-dating conditions
(`dbwrite.py:179-191`). Plus one futoi addition: `MERDIAN_FUTOI_1M_ENABLED != "1"` is an **exit 0**,
not a refusal — requirement 1 says exit 0, and conflating "not enabled" with "misconfigured" would
make a disabled box alert.

`--check` with `--db-write` runs the SQL check and prints `CHECK PASS` only if every clause passes
(`services/tape_live/cli.py:362-368`). A latched day makes **no write-role connection and runs no
check**; `--check` reports the latch (`cli.py:350-361`, `:363-366`).

---

## 9. Errors and thresholds (requirement 9)

### 9.1 Dhan outcomes

| Outcome | Class | Why |
|---|---|---|
| HTTP 200, `status: success`, data block present | ok | |
| HTTP 200, **`data` block missing** | **transient** (`dhan_no_data`) | A missing block is not zero rows. Writing nothing and reporting OK is the TD-S37-03 silent-empty shape |
| HTTP 200, segment present, **one id's block missing** | the row is **omitted**, counted as `blocks_missing` | Per-contract, not per-call. No row with every field NULL. Not a skipped grid point: the other contracts of that minute are written |
| HTTP 200, **non-JSON body** | **transient** (`dhan_nonjson`) | |
| HTTP **429** or a body containing **`DH-904`** | **transient** (`dhan_throttle`) | **RULED (Q-OP-4): `DH-904` is Dhan's throttling code by user reports, so it is classed with 429 under one name.** No in-call retry: the next minute *is* the retry |
| timeout / connection error | **transient** (`dhan_timeout`) | |
| HTTP 5xx | **transient** (`dhan_5xx`) | Matches TD-S81-NEW-11's finding that 5xx is transient |
| HTTP **401 / 403**, or a body containing **`DH-901`** | **auth** (`dhan_auth`) | A credential state. It changes when the token is re-minted or by operator action, not by waiting. Handled by the two-strike, day-scoped rule of §6.5 |

### 9.1a Transient Dhan outcomes never stop the writer and never latch (operator, change 5)

A transient outcome costs **that grid point's rows** and nothing else:

- The grid point is counted in `skips_dhan` (and in its own `dhan_<class>` counter) and the minute
  produces no rows. **The writer does not stop, does not latch, and makes the next call normally.**
- **At 5 consecutive transient grid points: a `WARNING` line and heartbeat reason
  `dhan_transient_run` with the consecutive count. Calls continue.** The threshold is the
  `MAX_CONSECUTIVE_SKIPS_DHAN = 5` of §9.3 — its derivation is unchanged, but **what it triggers is now
  a WARNING, not a stop.** The reason it cannot be a stop: a vendor-side throttle or outage that has
  recovered by minute 7 would otherwise cost the remaining 5 hours of the session, and there is nothing
  to re-run.
- **The day's verdict fails if `skips_dhan > 30` of 377** (RULED, Q-OP-5 — the number stays, its role
  changes from stop to verdict). That is 7.96 % of the session, derived in §9.3 as a judgement about
  the usability of the minute series, not about the health of the process.

Only two things stop this writer, and they are different objects:

| Stop | Scope | Artefact | Cleared by |
|---|---|---|---|
| **DB stop tier** (§9.2) | **carries across days** | `<out>/FUTOI_WRITE_LATCH.json` at the root, written atomically (temp file + `fsync` + `os.replace`) **before** the day's informational `WRITE_STOPPED` sentinel (`services/tape_live/dbwrite.py:429-451`) | `write-clear` only (§9.4) |
| **Dhan auth, two consecutive strikes** (§6.5) | **that day only** | `<out>/<day>/DHAN_AUTH_STOPPED`, heartbeat reason `dhan_auth_stopped` | nothing — the next trading day calls again |

A latch that cannot be parsed stops writes with reason `latch_unreadable` and can still be cleared
(`services/tape_live/dbwrite.py:95-105`). A latch that cannot be **written** does not end the run: the
writer stays stopped in memory, the sentinel is still written, the heartbeat reason becomes
`latch_write_failed` (`:449-451`).

### 9.2 DB outcomes by SQLSTATE

Classifier copied from `classify` (`services/tape_live/dbwrite.py:280-292`): rc 0 → ok; rc 124 → the
60 s process timeout, classed `statement_timeout`; otherwise the SQLSTATE is read out of stderr by
`ERROR:\s+([0-9A-Z]{5})\b` and mapped; if there is no SQLSTATE, the **one exact text**
`FATAL:  too many connections for role "futoi_w"` (two spaces, as the server prints it) is
`connection_limit` and **everything else with no SQLSTATE is `connect`** — including a pooler's own
message. That narrowness is an operator ruling, not a convenience
(`docs/tape/L2_live_runner_plan.md:552-554`; `dbwrite.py:79-81`).

Skip-and-count tier (transient, the condition can clear): `57014` statement_timeout, `55P03` /
`40P01` lock, `connect`.
Stop tier (a statement about the role, the policy or the key — no later minute changes it):
`42501` rls_refused, `53300` connection_limit, `25P03` idle_tx_timeout, `23505` unique violation the
writer did not predict, and **anything unclassified** (`other`). Tape's split: `SKIP_TIER` at
`services/tape_live/dbwrite.py:82`, the dispatch at `:512-524`.

**Nothing is retried inside a cycle.** A skipped write leaves those rows still different from the
model, so the next minute sends them again — there is no retry loop and nothing is computed inside a
transaction (`services/tape_live/dbwrite.py:10-11`). For futoi this means a skipped minute is repaired
by the next one, which is why the skip counters are about *consecutive* minutes.

### 9.3 Thresholds — numbers with derivations, fixed before any measurement

Each is a **belief stated before measuring**, not a number adjusted until a run passed (rule 0
clause 3). None is to be loosened after the fact; the first live week's counters are what test them.

| Constant | Value | What it does | Derivation |
|---|---|---|---|
| `MAX_CONSECUTIVE_SKIPS_DB` | **3** | **STOP + cross-day latch** | Belief: a skip-tier DB condition that has not cleared across three consecutive one-minute attempts is not transient. The role's `statement_timeout` is 15 s (F12; `tape_w` measured at M4), so three attempts give the server ≥45 s across ≥2 min of wall clock. One attempt can lose to a checkpoint; two to one autovacuum of a small table; three spanning two minutes cannot be a single short maintenance event under any mechanism named here. **Nothing measures the distribution of lock waits on this instance**, so this is pre-registered, not measured. Tape's analogue is stricter — the **second** skip stops it (`services/tape_live/dbwrite.py:520`) — because its cadence is 5 min, so two skips there span 10 min |
| `MAX_CONSECUTIVE_SKIPS_DHAN` | **5** | **WARNING + heartbeat reason only; calls continue** (changed from a stop, operator change 5) | Belief: vendor-transient faults (throttle, 5xx, timeout, non-JSON, no-data) clear inside a minute; five consecutive minutes is an outage worth saying out loud. The existing engine's in-call budget is `MAX_RETRIES = 4` at 2 s doubling ≈ ≤30 s (`capture_index_futures_snapshot_local.py:52-53`, `:283-291`); the futoi writer does **no** in-call retry, so five minutes is ~10× that budget. It is **not** a stop because a vendor outage that recovers at minute 7 would otherwise cost the rest of the session and nothing can re-run it |
| `MAX_DHAN_SKIPPED_GRID_POINTS` | **30** of 377 (7.96 %) | **VERDICT fails; the writer keeps running** (RULED, Q-OP-5) | Belief about the **study**, not the system: a gap of *k* minutes hides any OI move that reverses within *k* minutes, and a day missing more than ~8 % of its minutes is not a usable minute series. A research judgement, so it belongs in the verdict and not in a stop rule — a day that fails it is still the best record of that day that exists |
| `MAX_CONSECUTIVE_DHAN_AUTH` | **2** | **Dhan calls stop for that day only; no latch** (operator change 2) | Belief: the first auth failure can be a token re-mint that landed mid-session, which one re-read fixes (§6.5); two **consecutive** failures with a freshly-read credential between them is not a rotation, it is a dead credential. Day-scoped because the credential is re-minted at 08:20 IST daily, so tomorrow's run has a different input |
| `OVERRUN_S` | **45.0** | STOP (grid integrity) | A grid point's budget is 60 s and the call must land at `:30`. Belief: a cycle whose lag + work exceeds 45 s cannot land the next `:30`, so the grid has slipped and the day's `ts` values would stop meaning "start of this minute". Tape's is 300 s at a 5-min cadence, i.e. the same fraction of its budget (`services/tape_live/dbwrite.py:49`) |
| `MIN_DISTINCT_LTP` | **5** per symbol per day on `expiry_rank = 1` | VERDICT | The end-of-day freeze check. Belief: the front month of either index cannot print the same `last_price` for all 377 minutes of a real session. Five is deliberately far below any plausible real value and above the 1 a frozen source would give; it is a floor on a **count of distinct values**, which is the ADR-030 `distinct_spot` lesson, not a floor on a row count. It is **not** applied to ranks 2 and 3 (the far month measured one trade all day: `futoi_stage0a_farmonth_2026-11-28.md:25`) |
| `CLEAR_STALE_S` | **180** (RULED, Q-OP-6; was 600) | the liveness bound for `write-clear` and for the `--check` refusal | The healthy heartbeat gap here is ~60 s, not tape's ~300 s, so tape's 600 s is 10× rather than 2×. 180 s is 3× the healthy gap: it tolerates two missed heartbeats and still lets the operator clear a latch within three minutes of a dead process instead of ten |
| `MAX_MISSED_GRID_POINTS` | **0** | VERDICT clause 7 (change 3) | Not a tolerance, and deliberately not one. A missed grid point is a minute of the day that no process ever attempted, so it is not noise to be budgeted — it is a hole, and the formula already removes it from `rows_expected_final`, which means a non-zero `M` would otherwise be *invisible* in clause 1. Zero is the only value that makes the clause say anything. The number that is a judgement is `MAX_DHAN_SKIPPED_GRID_POINTS` (30), which covers minutes that **were** attempted and came back unusable |

### 9.4 `write-clear`

`futoi write-clear --out DIR --note TEXT [--day D] [--test-redate]` — `--out` and `--note` required,
as tape's (`services/tape_live/cli.py:543-547`). No latch ⇒ `nothing to clear`, rc 0. An unreadable
latch names no day, so **every** day is scanned (`cli.py:439`). Refused while a heartbeat of the latch
day or later is alive — a live POSIX pid, or a state in `starting`/`cycling`/`waiting` with
`updated_utc` younger than **`CLEAR_STALE_S = 180` s (RULED, Q-OP-6; tape's 600 s is 2× its ~300 s
healthy gap, and would be 10× this writer's ~60 s one)**. The refusal
prints the day, state, pid, heartbeat age in seconds, the bound and how long to wait, and exits 2
(`cli.py:442-448`). **The same test, with the same bound, is what refuses `--check` during a session
(§8.1).** On success: the latch is **renamed** to
`FUTOI_WRITE_LATCH.cleared.<YYYYMMDDTHHMMSSZ>.json`, each day's `write_skips` reset, `WRITE_STOPPED`
renamed to `WRITE_STOPPED.cleared.<stamp>`, and the note — **passed through `scrub()` first**, because
it is operator-typed text that lands in two logs (`cli.py:452`) — appended to `<out>/write_clear.log`
and to each scanned day's `runner.log`. `write-clear` is in **no** unit template and in no cron line.

---

## 10. Heartbeat and the ledger (requirement 10)

**Heartbeat file** `<out>/<ISO day>/heartbeat.json`, rewritten every grid point:
`{state, reason, pid, day, grid_point, updated_utc, contracts_resolved: {NIFTY: n, SENSEX: n},
calls_made, blocks_missing, rows_written, skips_db, skips_dhan, consecutive_dhan,
consecutive_dhan_auth, token_rereads, dhan_auth_stopped, instance_id, attempted_n, missed_n,
write: {state, reason, skips, db_written, latch_day, carried}}`. `attempted_n` and `missed_n` are
**this instance's own** figures; the day's `M` is the union computed in §10.1 and lives in
`counters.json`, not here — a per-instance `missed_n` is a progress indicator, never a verdict input.
Runner states, from the tape set
(`services/tape_live/live_runner.py:291`, `:297`, `:495`, `:502`, `:525`, `:641-688`):
`starting | cycling | waiting | stopped | killed | done | no_session | memory_cap | disk_floor |
memory_error | error`; only `starting`/`cycling`/`waiting` count as possibly-running for
`write-clear` (`services/tape_live/cli.py:399`). Writer sub-states: `none | sent | skipped | stopped`
(`dbwrite.py:403-408`). Written atomically, and `last_error` passes through `scrub()`
(`live_runner.py:264-272`).

**The ledger is futoi's own addition, not copied.** The tape live runner uses **no `ExecutionLog` at
all** — its run record is `<out>/<day>/live/run_manifest.json` plus `live_metrics.csv`,
`heartbeat.json` and `runner.log` (`services/tape_live/live_runner.py:628-633`). That is defensible
for a research runner nobody schedules; it is not defensible for a writer the operator will leave on a
timer, because nothing in the engine's monitoring can then see it. So:

**Ledger**, via `core.execution_log.ExecutionLog`, shape (b):

- **One parent row per session.** `script_name='capture_futures_oi_1m'`,
  `product_relation='futures_oi_1m'`, `expected_writes={'futures_oi_1m': G × C}` declared at start-up,
  where `G = 377` and `C = contracts_resolved_NIFTY + contracts_resolved_SENSEX`. Today `C = 4`, so
  **1,508** (M2). That is an **exact count**, not a floor, which is what rule 0 clause 1 requires of
  the field — but it is a *declaration made before the day happened*, so it is not the verdict.
- **`ExecutionLog` cannot produce the verdict, measured.** `_compute_contract_met` tests
  `actual < expected` (`core/execution_log.py:345-351`) — an **at-least** test that passes on an
  over-write; `complete()` passes `exit_code=0` as a literal (`:274`); and `exit_with_reason`
  **defaults to 0** (`:278`). So the writer computes its own verdict and carries it in the process exit
  code (rule 0 clause 2).

**§10.1 The verdict is over the IST DAY, not over one process (operator, changes 2, 3 and 5).**

A restart opens a **second ledger row** (`ExecutionLog` is constructed per process,
`core/execution_log.py:159-196`) and a **new process with fresh in-memory counters**. A verdict
computed from one process's counters would therefore be wrong on exactly the day it matters most. So
the counters are persisted per day and the verdict is computed over their union.

**The counter file.** `<out>/<day>/counters.json`, written atomically (temp file + `fsync` +
`os.replace`) every grid point, beside `heartbeat.json`:

```json
{"day": "2026-11-28", "G": 377, "C": 4, "verdict_written": false,
 "instances": [
   {"instance_id": "<uuid4>", "pid": 12345,
    "started_utc": "...", "ended_utc": null,
    "attempted":   "<377-bit bitmap, 95 hex chars>",
    "no_response": "<377-bit bitmap, 95 hex chars>",
    "b": 0, "l": 0}
 ]}
```

Two deliberate choices in that shape:

- **`attempted` and `no_response` are bitmaps over the 377 grid points, not counts.** Two processes
  each reporting "I attempted 100" cannot distinguish coverage from overlap; a union of bitmaps can.
  377 bits is 95 hex characters — the whole file stays under 1 kB for a day with three restarts.
- **`instance_id` is a `uuid4`, not the pid.** A pid can be reused inside one day, and merging two
  instances because they share a pid would silently halve `M`.

**The quantities, and the formula with `M` (change 3):**

```
G      = 377                       # grid points: 09:15..15:30 inclusive, plus 15:40
C      = contracts_resolved_NIFTY + contracts_resolved_SENSEX    # fixed at start-up, never re-resolved
A      = union over instances of `attempted`
M      = G - popcount(A)           # grid points NEVER ATTEMPTED
S_dhan = popcount(union over instances of `no_response`)
B      = sum over instances of `b` # contract-grid-points absent from an otherwise usable response
L      = sum over instances of `l` # C_last if the FINAL grid point's write was DB-skipped, else 0

rows_expected_final = (G - S_dhan - M) * C - B - L
rows_written        = SELECT count(*) FROM public.futures_oi_1m   -- as futoi_w (see below)
```

**`M` — grid points never attempted.** Three causes, all real: (i) **no process was running** — the
timer never fired, the unit was stopped, or a crash left a gap between a death and the restart;
(ii) **the session started after 09:15** — a late timer, or a manual start mid-session;
(iii) **`overrun`** — the `OVERRUN_S` stop ends the session and leaves every later grid point
unattempted. Without `M` the formula would silently shrink `rows_expected_final` to match whatever a
short day produced, and clause 1 would pass on a day that captured two hours. `M` and `S_dhan` cannot
double-count because `no_response ⊆ attempted` by construction, which is asserted (below).

**`rows_written` comes from the table, not from a tally.** `SELECT count(*) FROM public.futures_oi_1m;`
run as `futoi_w` — **with no `WHERE` clause**, because the SELECT policy
`USING (trading_day = ((now() AT TIME ZONE 'Asia/Kolkata'))::date)` (§7.5) makes the count today's by
construction and makes counting another day impossible. Reading the table rather than a counter is
what makes the figure survive a restart, and also what makes it see a row the database rejected.
(`futoi_w` needs `SELECT` for this and for the model rebuild — §7.5. Mutant
`ROWS-WRITTEN-FROM-COUNTER`.)

`S_db` (DB skip-tier grid points) does **not** appear, and that is a property of the sink, not an
omission: a skipped write leaves those rows still different from the model, so the **next** grid point
re-sends them (`services/tape_live/dbwrite.py:10-11`). The only DB skip that loses rows is one at the
final grid point, because nothing follows it to re-send — that is the `L` term.

**Invariants checked BEFORE the verdict is believed.** Each can fail, and a failure means the counters
are inconsistent, which is worse than having none:

1. the `attempted` bitmaps are **pairwise disjoint** — a grid point is attempted at most once per day,
   because a restart resumes at the next grid point and never back-fills (tape's rule,
   `services/tape_live/live_runner.py:656-659`);
2. `no_response ⊆ attempted`, per instance;
3. `popcount(A) + M == G`;
4. **at most one** instance has `l != 0`, since only the owner of the final grid point can set it.

If any fails: no verdict is computed, `exit_with_reason("DATA_ERROR", exit_code=4)` with reason
`counter_invariant_violated`.

**The verdict PASSES only if all seven hold:**

| # | Clause | Reason name on failure |
|---|---|---|
| 1 | `rows_written == rows_expected_final` | `row_count_mismatch` |
| 2 | `S_dhan <= 30` (`MAX_DHAN_SKIPPED_GRID_POINTS`, Q-OP-5) | `dhan_skips_over_bound` |
| 3 | the writer never stopped (no DB latch, no `overrun`, no Dhan auth stop) | `writer_stopped` |
| 4 | `max consecutive S_db < 3` (`MAX_CONSECUTIVE_SKIPS_DB`) — redundant with 3 by construction, asserted separately so a stop that failed to latch is still caught | `db_skip_run` |
| 5 | `contracts_resolved_NIFTY > 0 and contracts_resolved_SENSEX > 0` (Q-OP-7) | `symbol_unresolved` |
| 6 | `distinct_ltp(expiry_rank = 1) >= MIN_DISTINCT_LTP` for each symbol with `contracts_resolved > 0` | `ltp_frozen` |
| 7 | **`M == 0`** (change 3) | **`missed_grid_points`**, naming the count and the first and last missed grid point, so a short day says *why* it is short instead of reporting a smaller expected count |

Clause 1 is an **equality** on two figures the writer derived independently — one from the database,
one from the persisted counters. Clause 7 is what stops that equality being satisfiable by a day that
simply did less.

**Which process writes the verdict.** The process that **attempts the final grid point (15:40) and
reaches session end**. Exactly one can, because grid points are never re-attempted. It sets
`verdict_written: true` in the counter file and exits 0 or 4 per §3.3.

**What an earlier process's ledger row records.** Not a verdict. Its row carries its own
`exit_reason`/`exit_code` (`CRASH`/1, or 3 for a cap), and its `notes` say
`verdict=deferred; instance=<uuid4>; grid_first=<HH:MM>; grid_last=<HH:MM>; attempted=<n>;
no_response=<n>; b=<n>`. `contract_met` on that row is whatever `ExecutionLog` computes and is **not**
read by anything — stated so that nobody later mistakes a deferred row's `contract_met` for the day's
verdict.

**If no process reaches 15:40, no verdict is written** — and an absent verdict is exactly the silent
hole this plan keeps citing. Closed without a new scheduled job: at start-up, **after** the calendar
gate and **before** the first Dhan call, the writer reads the **previous** trading day's
`counters.json`; if it exists with `verdict_written: false`, it logs a WARNING and writes one
`log_child_run` row (`core/execution_log.py:442-463`) for that prior day, carrying the computed
`rows_expected_final` from the persisted counters, the reason `no_verdict_written`, and the day it
belongs to. It does **not** read the prior day's rows from the table — `futoi_w` is day-scoped and
cannot (§7.5), so `rows_written` for that day is reported as unavailable rather than guessed. Mutant
`PRIOR-DAY-VERDICT-SKIPPED`. **This carry-forward is beyond the operator's ruling and is flagged as
Q-OP-13** so it can be cut.

On any failure the writer uses `exit_with_reason(..., exit_code=4)` — **never `complete()`** — with the
clause's reason name, the reason/`status` pairing of §3.3, and **one child row** carrying
`rows_written`, `rows_expected_final`, `M`, `S_dhan`, `B`, `L` and the clause number in
`error_message`, so the failure is legible without opening the out dir. On success it calls
`exit_with_reason("SUCCESS", exit_code=0)`, so exactly one code path sets the exit code.

Guard `futoi-heartbeat` asserts each clause at its boundary, the exit code of §3.3, and the formula on
planted counter files; guard `futoi-restart` asserts the cross-process union, the four invariants and
the verdict owner. Mutants `VERDICT-NOT-IN-EXIT`, `VERDICT-IGNORES-SDHAN`, `VERDICT-IGNORES-BLOCKS`,
`VERDICT-IGNORES-L`, `VERDICT-IGNORES-M`, `VERDICT-M-CLAUSE-REMOVED`, `VERDICT-SDHAN-AT-31`,
`VERDICT-ONE-SYMBOL-PASSES`, `VERDICT-USES-GE`, `EXPECTED-AS-FLOOR`, `VERDICT-EXIT-RESTARTS`,
`VERDICT-EXIT-IS-ONE`, `ROWS-WRITTEN-FROM-COUNTER`, `PRIOR-DAY-VERDICT-SKIPPED`, `VERDICT-PER-PROCESS`,
`MISSED-NOT-COUNTED`, `COUNTERS-NOT-PERSISTED`, `COUNTERS-OVERLAP-UNCHECKED`, `L-SUMMED-TWICE` (§13).

**Rows per day under the chosen shape: 1 on a clean day, 2 on a failing one, +1 per restart, +1 for a
carried-forward prior day.** Under (a) it would be 377. None of them is watched automatically
today — §3.1.

---

## 11. Fixtures

All in `tests/futoi/fixtures.json`; the two recorded responses are the Stage 0a captures, byte-for-byte.

| # | Fixture | From | Exercises |
|---|---|---|---|
| X1 | the 4-contract quote response | `docs/research/futoi/stage0/sample_response_fields.json` | the happy path, 17 keys, both segments, SENSEX lots 20 and 25 |
| X2 | the 2-contract far-month response | `docs/research/futoi/stage0/farmonth_quote_sample.json` | a 1-per-segment call; `ohlc.close = 0`; a 10:18 last trade |
| X3 | **roll day**: scripmaster holds 3 per symbol, the nearest expires today | hand, from M2's shape | `expiry_rank` reassignment; `SM_EXPIRY_DATE >= today IST` at the boundary |
| X4 | **2 contracts** (today's live state, M2) | M2 | `contracts_resolved = 2`, WARNING, no substitution, 1,508-row expectation |
| X5 | **429** | hand | skip-and-count; the consecutive counter |
| X6 | **a single 401**, followed by ok responses for the rest of the day | hand | **CORRECTED (change 4): one credential re-read, NO stop, NO latch**, `S_dhan` counts exactly that one grid point, and the day's verdict still **PASSES** (1 ≤ 30). The old cell read "day-stop on both DB and Dhan; the latch", which contradicted §6.5's two-strike rule and X17 — it was left over from the pre-change-2 draft. X17 keeps the boundary cases (`401`→`401`, `401`→`200`); X6 is the "a single auth blip does not spoil the day" case neither of those covers |
| X7 | **DH-904 body** | hand | skip-and-count (not a stop) |
| X8 | **timeout** | hand (`requests.Timeout`) | skip-and-count |
| X9 | **non-JSON** body | hand | skip-and-count, no traceback through a grep |
| X10 | **missing `oi` key** in one block | X1 with `oi` deleted | NULL, never 0 |
| X11 | **missing `data` block** | X1 with `data` deleted | skip-and-count, not "0 rows written, OK" |
| X12 | **clock edges** 09:14:30, 09:15:30, 15:30:30, 15:31:30, 15:40:30 | the sim clock | the grid's inclusive ends and the 15:40 extra |
| X13 | **non-trading day** | the gate fake returning a computed closure | exit 0, zero Dhan calls |
| X14 | hostile literals + NUL | the tape corpus (`services/tape_live/dbwrite.py:196-205`) | `db-literal-check`; NUL is a refusal |
| X15 | a SENSEX far-month leg with `oi = 25`, flat all day | X2 | `MIN_DISTINCT_LTP` is rank-1 only |
| X16 | **a fixture engine `.env`** whose `DHAN_API_TOKEN` changes between two reads, plus variants with the key absent, duplicated, quoted and commented out | hand, via `MERDIAN_FUTOI_ENGINE_ENV` | §6.5: re-read per call; last assignment wins; quotes stripped; the real `/home/ssm-user/meridian-engine/.env` is never opened by any test |
| X17 | **401 then 401** and **401 then 200** | hand | §6.5: one re-read, retry at the next grid point, stop only on the second consecutive; the second-day resumption with no `write-clear` |
| X18 | **gate credential absent / empty** in the fixture `.env` | hand | §6.6: exit 2, zero Dhan calls, `core.*` never imported |
| X19 | **a `$HOME/.merdian_ro_env`-shaped file at mode 0644**, and one at 0600 | hand, via `MERDIAN_RO_ENV_FILE` | §6.2: the mode gate re-implemented from `bin/roq.sh:84-88` refuses the first and accepts the second |
| X20 | **a live heartbeat of today** (fresh `updated_utc`, own pid) and a **stale one** (dead pid, 7200 s old) | hand | §8.1 / §9.4: `--check` and `write-clear` refused against the first, accepted against the second, at the 180 s bound |
| X21 | **kill at 11:00, restart at 11:07** — a 7-grid-point gap — plus a variant with a **10:00 first start** (`M = 45`) and a variant with **two** restarts | the sim clock | §10.1: the union of `attempted`, `M` counted over the gap, the four invariants, the verdict written by the process that owns 15:40, the earlier rows reading `verdict=deferred`, and clause 7 failing with `missed_grid_points` naming 11:00 and 11:06 |
| X22 | **a prior day's `counters.json` with `verdict_written: false`** in the out dir | hand | §10.1 carry-forward: one `log_child_run` row for that day with reason `no_verdict_written`, and `rows_written` reported **unavailable** rather than guessed (`futoi_w` cannot read another day) |
| X23 | **planted counter files that violate each invariant** — overlapping `attempted`, a `no_response` bit outside `attempted`, two instances with `l != 0`, and `popcount(A) + M != G` | hand | §10.1: each one refuses with `counter_invariant_violated` and exit 4, and **no verdict is computed** |

---

## 12. Guards (requirement: each with the failure it must show before the code exists)

Written **before** `services/futoi/` exists. Each must FAIL on the tree as it is, for the reason named.
The fakes are written from **this plan and the DDL**, never from the writer, and `_futoi_selftest`
proves each fake assertion can fire with no writer at all — tape's `_w2b_selftest`
(`tests/test_tape_live.py:3432`) is the precedent, and the reason it exists is that a fake that cannot
fail makes every guard over it vacuous.

| Guard | What it proves | **Red-first failure before the code exists** |
|---|---|---|
| `futoi-off` | `MERDIAN_FUTOI_1M_ENABLED != "1"` ⇒ exit 0, **zero** Dhan calls; no `--db-write` ⇒ sink never constructed; DSN without the flag ⇒ refusal | `ImportError: services.futoi.cli does not exist` |
| `futoi-session` | 377 grid points, each at `:30`; none at 09:14:30 or 15:31:30; 15:40:30 present; at most one call per grid point | `ImportError` |
| `futoi-gate` | the gate is `core.trading_calendar_gate` by import (asserted by `ast`: the module is imported and `assert_trading_day_or_exit` called, and no inline weekday literal exists in `services/futoi/`); a computed closure ⇒ exit 0, zero Dhan calls; **a missing or empty gate credential ⇒ exit 2, zero Dhan calls, `core.*` never imported (X18)**; **`SUPABASE_*` is in `os.environ` before `core.execution_log` is imported**, asserted by a stub that records `os.environ` at its own import | `ImportError` |
| `futoi-contracts` | resolver columns/filter/order match `capture_index_futures_snapshot_local.py:153-172` plus `LOT_SIZE`; first 3 by expiry; `expiry_rank` 1..n; lot per row; 2 resolved ⇒ `contracts_resolved=2` + WARNING + **no substitution**; segment from `EXCH_ID`; `today` is IST; **the read credential comes from `$HOME/.merdian_ro_env` (override `MERDIAN_RO_ENV_FILE`) and a mode other than 600/400 is refused (X19)** | `ImportError` |
| `futoi-dhan-creds` | **the credential is re-read before every call** (X16: the token changes between reads and the second call carries the new one); last assignment wins; quotes stripped; absent key ⇒ refusal; **the token never enters `os.environ`** and appears in no file, log or heartbeat; the real engine `.env` path is never opened when the override is set | `ImportError` |
| `futoi-monitor-gap` | `monitor_orchestrator_health.py:121` still reads `ORCHESTRATOR_SCRIPT = 'run_merdian_shadow_runner_aws.py'` and `:463` still scopes the hung probe to `script_name=eq.{ORCHESTRATOR_SCRIPT}` — i.e. **the probe does not cover `capture_futures_oi_1m`**, which is the fact §3.1 and §14 rest on | FAIL: the guard does not exist. Once written it PASSES immediately (the fact is already measured), so its red-first evidence is a scratch-copy edit widening the filter, which must make it FAIL |
| `futoi-row` | `ts` = start of the IST minute as true UTC; `captured_at` later; absent key ⇒ NULL (asserted on X10 by DB-typed value, `NULL is not 0`); `oi`/`volume` stored undivided; `last_trade_time_raw` byte-identical to the fixture; `source` constant | `ImportError` |
| `futoi-files-first` | for every grid point, the rows handed to the sink **equal** the rows appended to that minute's CSV section, compared by DB-typed value with NULL = NULL; the CSV write precedes the sink call; a crash between them leaves the file complete and the DB without the rows | `ImportError` |
| `futoi-upsert-only` | every rendered script: `BEGIN`/`COMMIT`, `ON CONFLICT ON CONSTRAINT futures_oi_1m_pk DO UPDATE`, every non-key column in the SET list, `''` doubled, empty ⇒ bare `NULL`; **no `DELETE`/`TRUNCATE` token** in any script or in any string constant of `services/futoi/` | `ImportError` |
| `futoi-startup` | each of R1–R10 individually, by feeding the check-output parser a crafted CSV; and that the role switch and the counts come back in **one** result set | `ImportError` |
| `futoi-errors-dhan` | the 8 outcome classes of §9.1 each reach their class, with `429` and a `DH-904` body reaching the **same** class `dhan_throttle`; **every transient class leaves the writer running and writes no latch**; 5 consecutive ⇒ WARNING + heartbeat reason and a 6th call still made; **auth: one re-read then a retry at the next grid point, a stop only on the second consecutive, the stop day-scoped with no latch, and the next day calling again with no `write-clear` (X17)**; a non-JSON body does not vanish into a filtered pipe | `ImportError` |
| `futoi-errors-db` | the §9.2 split; `MAX_CONSECUTIVE_SKIPS_DB` at its exact boundary (2 continues, 3 stops and latches); a connect failure with no SQLSTATE is classified by text; a `53300` reaches the **stop** tier | `ImportError` |
| `futoi-latch` | the latch is written atomically before the sentinel; survives a restart on the **same** day and on the **next** day; `latch_unreadable` fails closed and is still clearable; `latch_write_failed` does not end the run; **`write-clear` and `--check` are both refused against a live heartbeat and accepted against a dead pid's stale one, at the 180 s bound (X20)**; **no Dhan outcome of any class ever writes this latch** | `ImportError` |
| `futoi-heartbeat` | the heartbeat's keys and states; `expected_writes` is an **exact** figure, not a floor; **`rows_expected_final` equals `(G − S_dhan − M)·C − B − L` on planted counter files**; each of the **seven** verdict clauses at its boundary, each with its own reason name; **`rows_written` is read from the table and not from a tally**; **a failing verdict exits 4, not 1**; and **the unit template's `RestartPreventExitStatus` line contains 2, 3 and 4** (a static read of `docs/futoi/futoi-1m.service.template`) | `ImportError`; the template assertion fails because the template does not exist |
| `futoi-confined` | the DSN leaves `os.environ` at start and appears in no argv, no file, no log — including on a failing write whose stderr carries it; the child env is the allowlist; `dbwrite.py` imports no `subprocess` and no network module and matches no secret pattern; write SQL exists only in `dbwrite.py` | `ImportError` |
| `futoi-restart` | a restart mid-session rebuilds the upsert model **from the table**, not from the files; skip counters are **not** silently reset; and (change 2) on X21 **the verdict is computed over the union of every instance's persisted counters, not over the last process's own**: `A` is the union, `M` counts the gap, the four §10.1 invariants hold and each can fail (X23), **exactly one** process writes `verdict_written: true` — the owner of the 15:40 grid point — and every earlier process's ledger row reads `verdict=deferred` | `ImportError` |
| `futoi-unchanged` | every tracked file other than the new ones and `tests/run_offline.sh` is **byte-identical to `b24ff39`**, by sha256 over a `git -c core.autocrlf=false archive b24ff39` export, with `capture_index_futures_snapshot_local.py` named explicitly | FAIL: the guard itself does not exist; once written it PASSES immediately and must be shown able to fail by a deliberate one-byte edit in a scratch copy |

**Guard count: 17.** Recomputed from the revised enumeration above, not aimed at: the previous 15 plus
`futoi-dhan-creds` (operator change 2 gave the credential its own lifecycle, which no other guard
covers) and `futoi-monitor-gap` (operator change 4 turned an assumption into a measured fact that must
not rot). **Two** guards are green from the first minute — `futoi-unchanged` and `futoi-monitor-gap` —
and both therefore carry scratch-copy red-first evidence instead of an `ImportError`.

### `tests/run_offline.sh` (the only existing file edited)

Two steps appended **after** step 42, never between an existing step and its `${PIPESTATUS[0]}` test
(the idiom is positional — TD-S93-NEW-1, `tests/run_offline.sh:102-103`), and the `42` labels become
`44`:

```
echo "== 43/44 futoi 1m guards (17) (docs/research/futoi/stage1/futoi_stage1_writer_plan.md)"; python3 tests/test_futoi_1m.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "== 44/44 futoi 1m mutants (137 x5: 138 less 1 skipped on python < 3.11, each must be caught)"; python3 tests/futoi_1m_mutants.py --repeat 5 | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
```

Registering a suite in this file is six things, not one, and all six are house rules with stated
reasons:

1. **Append** at the end, never inside an existing pipeline-and-test pair — `${PIPESTATUS[0]}` is
   positional, so an insertion inside a pair silently disarms it (TD-S93-NEW-1, repeated at
   `tests/run_offline.sh:102-103` and twenty other places).
2. **Renumber** every `N/42` to `N/44` and update the step count and its dated history on
   `tests/run_offline.sh:3`.
3. **A comment block above the step** in house style: the lane/ruling id, what it asserts, **whether it
   loads a golden day** (i.e. whether it moves the rule-23 memory profile — the "steps 8-10" vs
   "steps 11-12" distinction at `:50-52` and `:91-93`), whether it writes any file (`:76-78` is the one
   non-read-only step and says so), the interpreter choice with its measurement if `-I`, the mutant
   count, and the "Appended AFTER step N" sentence. futoi loads **no** golden day and writes only into
   a temp dir, so it is the steps-8-10 class.
4. **A recorded standalone pass before wiring it in**, with timestamp and measured peak RSS under
   `( ulimit -v 700000 )` — `:56-59`: "an unrun test in a single-command suite puts a test nobody has
   seen green in front of the next person who runs it."
5. **Its own rule-23 guard** returning 2 in-window, as every tape step has (`:190-192`, `:198-199`,
   `:205-206`, `:210-211`, `:217-218`), including the Local-only `TAPE_RULE23_OVERRIDE_R1=1` override
   if the suite needs one.
6. **Prove a non-zero exit is a failure, not a skip** — the precedent at `:68-74` replaced the step with
   a stub exiting 2 and confirmed `OFFLINE FAIL`, exit 1.

Plain `python3`, not `python3 -I`: `-I` drops `~/.local/lib/python3.10/site-packages` where `dotenv`
lives (`tests/run_offline.sh:95-100`), and `core.trading_calendar_gate` and `core.execution_log` both
call `load_dotenv` at import (`core/execution_log.py:84`, `core/trading_calendar_gate.py:49-52`).

---

## 13. Mutants (requirement: each with the assertion meant to catch it)

Harness copied from `tests/tape_live_mutants.py`: copy the tree to a temp dir, apply **one exact-string
patch** that must match **exactly once** (`patch()` at `:419`; a non-match prints
`MUTANT NOT APPLIED` and is a **FAIL, never a skip**, `:467-469`), run the named guard against the copy
with `--root`, and require **exit 1** (`run_guard()` at `:430`; `ok = rc == 1` at `:474`). A guard's own
rule-23 refusal is **exit 2 and is NOT a catch** (`tests/tape_live_mutants.py:5-7`) — otherwise every
mutant would "pass" when the suite is run in-window. Every repeat also runs each guard's **control** —
an unpatched copy, which must exit 0 (`:449-459`). Flags `--repeat N`, `--only M-F-…` (`:439-441`).
Verdict line: `FUTOI MUTANTS PASS (138/138 caught xN, 17/17 controls xN)`, or with a skip,
`PASS (137/137 caught xN, 1 skipped (M-F-NUL-PASSES), 17/17 controls xN)` — a skipped mutant is
**never counted as caught**, and its guard still runs as a control (`:12-15`, `:480-486`).

`COPY` (the paths cloned into each temp tree, from `:25-28`): `services/futoi`, `core`,
**`monitor_orchestrator_health.py`**, `sql/2026-11-28_futoi_futures_oi_1m.sql`,
`tests/test_futoi_1m.py`, `tests/futoi`, `tests/futoi_1m_mutants.py`, `tests/run_offline.sh`,
`docs/research/futoi/stage1/futoi_stage1_writer_plan.md`, `docs/futoi/*.template`,
`docs/futoi/futoi_1m_install.md`. `core` is in the list because the calendar-gate and ledger mutants
patch it, and `monitor_orchestrator_health.py` because `MONITOR-SCOPE-UNCHECKED` patches it — **in the
temp copy only; this lane never edits that file on the branch** (§3.1). `futoi-unchanged` then has to
exempt the temp tree, which is why that guard compares against a `git archive` of `b24ff39` rather
than against the working tree.

Added beyond tape's harness: **`--anchor-check`**, which verifies every mutant's `old` string matches
**exactly once** in its target and every named guard exists in `GUARDS`, **without** running any guard.
The tape build did this with an ad-hoc script and recorded "195 / 35 / 0 bad"
(`docs/tape/L2_live_runner_plan.md:487`); committing it makes the check repeatable instead of a figure
in a plan.

| Guard | n | Mutants (abbreviated; each is one exact-string patch) | The assertion that catches them |
|---|---|---|---|
| `futoi-off` | 5 | `OFF-WRITES` (sink built without the flag), `OFF-ENABLED-IGNORED`, `OFF-ENABLED-AFTER-CALL` (env checked after the Dhan call), `OFF-DSN-KEPT` (DSN not popped), `OFF-DRYRUN-SENDS` | zero recorded Dhan calls; sink `None`; `W_ENV` absent from `os.environ`; refusal on DSN-without-flag |
| `futoi-session` | 8 | `START-ONE-EARLY`, `END-ONE-LATE`, `MISS-1540`, `SECOND-00`, `TWICE-PER-MIN`, `GRID-FROM-CALL-TIME`, `GRID-IN-UTC`, `RUNS-PAST-1540` | the exact 377-point set; each call's second == 30; one call per grid point |
| `futoi-gate` | 6 | `GATE-COPIED` (inline `weekday()>=5`), `GATE-AFTER-CALL`, `GATE-IGNORES-CLOSURE`, `GATE-FAILS-CLOSED` (a genuine error blocks), **`GATE-CRED-MISSING-RUNS`** (the presence check removed, so an absent credential rides the gate's fail-open), **`IMPORT-BEFORE-ENV`** (`core.execution_log` imported before `os.environ` is populated) | `ast` finds the import and the call; zero Dhan calls on X13; a non-200 fake still runs; X18 ⇒ exit 2 with no Dhan call; the import-order stub records a populated `os.environ` |
| `futoi-contracts` | 10 | `RESOLVE-EVERY-MINUTE`, `EXPIRY-GT`, `TODAY-NAIVE`, `LIMIT-ONE`, `ORDER-DESC`, `PAD-TO-THREE`, `LOT-PER-SYMBOL`, `LOT-INT-OF-TEXT` (`int('65.0')`), `COUNT-HARDCODED-3`, **`RO-CRED-MODE-UNCHECKED`** | one resolver query per session; the 4 rows of M2 in order; rank 1..2 on X4; SENSEX lots 20 **and** 25; `contracts_resolved == 2`; X19's 0644 file is refused |
| `futoi-dhan-creds` | 7 | **`TOKEN-HELD-FROM-START`** (read once, not per call), **`CRED-FIRST-ASSIGNMENT`** (first assignment wins instead of last), **`CRED-QUOTES-KEPT`**, **`CRED-MISSING-DEFAULTS-EMPTY`** (absent key becomes `""` instead of a refusal), **`CRED-INTO-ENVIRON`**, **`CRED-IN-LOG`** (the token interpolated into an error message), **`CRED-OVERRIDE-IGNORED`** (the real engine path read despite `MERDIAN_FUTOI_ENGINE_ENV`) | on X16 the second call carries the rotated token; the parser's four shapes; `os.environ` never gains the key; the secret needle absent from every file, log line and heartbeat; the real path never opened |
| `futoi-row` | 8 | `ABSENT-AS-ZERO`, `OI-DIVIDED-BY-LOT`, `TS-IST-AS-UTC`, `TS-IS-CAPTURE`, `LTT-PARSED`, `LTT-REFORMATTED`, `SOURCE-BLANK`, `RANK-BY-SECURITY-ID` | typed comparison `NULL is not 0`; `oi` equals the fixture's integer; `ts == 03:45:00+00:00` for 09:15 IST; `last_trade_time_raw` byte-identical |
| `futoi-files-first` | 6 | `DB-BEFORE-FILE`, `NO-FSYNC`, `FILE-PER-RUN`, `COUNT-ONLY-COMPARE`, `HEADER-DRIFT`, `ONE-ROW-DROPPED` | the call-order record; typed set equality (a count-only comparison lets `ONE-ROW-DROPPED` through — that is the point of the mutant) |
| `futoi-upsert-only` | 8 | `D-AS-DELETE`, `TRUNCATE-IN-TEXT`, `CONFLICT-DO-NOTHING`, `CONFLICT-KEY-SYMBOL-TS`, `QUOTE-NOT-DOUBLED`, `NULL-AS-EMPTY-STRING`, `NO-TRANSACTION`, `DUP-KEY-SENT` (the `dup_conflict_key` refusal removed) | token scan over scripts and constants; the fake table raises `23505` on a duplicate key, so removing the refusal is caught by the raise, not by a comment; the hostile-literal row round-trips |
| `futoi-startup` | 13 | one per R1, R2, R3a, R3b, R4a, R4b, R5, R6, R7, R8, R9, R10, plus `CHECK-TWO-RUNS` | each crafted check-CSV yields exactly its reason, and no write is attempted |
| `futoi-errors-dhan` | 15 | `THROTTLE-STOPS`, **`DH904-NOT-THROTTLE`** (DH-904 classed anywhere but with 429), `TIMEOUT-STOPS`, `NONJSON-AS-EMPTY`, `NODATA-AS-ZERO-ROWS`, **`TRANSIENT-LATCHES`**, **`WARN-AT-WRONG-N`** (the 5-consecutive WARNING off by one), **`WARN-IS-A-STOP`**, `401-SKIPS`, `403-SKIPS`, `DH901-SKIPS`, **`AUTH-NO-REREAD`**, **`AUTH-STOPS-ON-FIRST`**, **`AUTH-LATCHES`**, **`AUTH-CARRIES-TO-NEXT-DAY`** | per-outcome class; no latch on disk after any transient; the 5th grid point WARNs and the 6th call is still made; on X17 `401`→`401` stops that day only, `401`→`200` does not stop, and the next day's run calls with no `write-clear` |
| `futoi-errors-db` | 6 | `SKIP-TIER-WIDENED` (42501 skipped), `SKIP-TIER-NARROWED` (57014 stops), `THRESHOLD-OFF-BY-ONE`, `SKIPS-CUMULATIVE-NOT-CONSECUTIVE`, `SQLSTATE-NOT-PARSED`, `CONNECT-NOT-CLASSIFIED` | the boundary pair (2 continues, 3 stops and latches) and the reason string |
| `futoi-latch` | 8 | `LATCH-NOT-WRITTEN`, `LATCH-NOT-ATOMIC`, `LATCH-CORRUPT-OPENS`, `CLEAR-KEEPS-LATCH`, `CLEAR-WHILE-ALIVE`, `LATCH-DAY-SCOPED`, **`CLEAR-STALE-600`** (the bound left at tape's value), **`CHECK-DURING-SESSION`** (the `--check` refusal removed) | next-day run is still stopped; the corrupt latch gives `latch_unreadable`; on X20, `write-clear` and `--check` rc differ between the live and the stale heartbeat, and a 181 s-old heartbeat is clearable while a 179 s-old one is not |
| `futoi-heartbeat` | 18 | `HB-NOT-WRITTEN`, `HB-NOT-UPDATED`, `VERDICT-NOT-IN-EXIT` (uses `complete()`), `EXPECTED-AS-FLOOR`, `LEDGER-ROW-PER-MINUTE`, `CONTRACT-ADJUSTED-TO-OBSERVED`, `VERDICT-IGNORES-SDHAN`, `VERDICT-IGNORES-BLOCKS`, `VERDICT-IGNORES-L`, `VERDICT-SDHAN-AT-31`, `VERDICT-ONE-SYMBOL-PASSES`, `VERDICT-USES-GE` (clause 1 becomes `>=`, i.e. a floor), **`VERDICT-IGNORES-M`** (the `− M` term dropped from the formula), **`VERDICT-M-CLAUSE-REMOVED`** (clause 7 deleted while the formula keeps `M`), **`VERDICT-EXIT-RESTARTS`** (the template's `RestartPreventExitStatus` drops the `4`), **`VERDICT-EXIT-IS-ONE`** (the verdict failure returns 1), **`ROWS-WRITTEN-FROM-COUNTER`** (the tally used instead of the table), **`PRIOR-DAY-VERDICT-SKIPPED`** (the carry-forward removed) | exit **4** on a short day; exactly 1 (or 2) ledger rows; `rows_expected_final` equals the hand-computed figure on planted counter files; each clause flips at its boundary with its own reason name. The two `M` mutants are distinct and each has its own witness: `VERDICT-IGNORES-M` is caught on X21's 10:00-start variant (`M = 45`), where dropping the term makes clause 1 pass on a 332-point day; `VERDICT-M-CLAUSE-REMOVED` is caught on the same fixture, where keeping the term makes clause 1 pass and only clause 7 can still fail. `ROWS-WRITTEN-FROM-COUNTER` is caught on X21: a tally reset by the restart cannot see the first process's rows |
| `futoi-confined` | 6 | `PW-IN-ARGV`, `DSN-LEFT-IN-ENV`, `STDERR-RAW`, `SUBPROCESS-IMPORT`, `WRITE-SQL-OUTSIDE-MODULE`, `ENV-ALLOWLIST-WIDENED` | the secret needle in argv/files/log; `ast` import scan; the per-module constant scan |
| `futoi-restart` | 10 | `MODEL-FROM-FILES`, `MISSED-NOT-RECORDED`, `DOUBLE-COUNT`, `RESUME-REWRITES-DAY`, `SKIPS-RESET`, **`VERDICT-PER-PROCESS`** (the verdict computed from this process's counters only), **`MISSED-NOT-COUNTED`** (the gap's grid points never enter `attempted`, so `M` reads 0), **`COUNTERS-NOT-PERSISTED`** (the counter file written at session end instead of every grid point, so a kill loses the instance), **`COUNTERS-OVERLAP-UNCHECKED`** (the pairwise-disjoint invariant removed), **`L-SUMMED-TWICE`** (the at-most-one-`l` invariant removed) | the model at the second `start()` equals what the fake table holds, exactly; on X21 the union is 377 − 7 and `M == 7`, which `VERDICT-PER-PROCESS` and `MISSED-NOT-COUNTED` each break differently — the first by scoping the sum, the second by scoping the set; `COUNTERS-NOT-PERSISTED` is caught because the killed instance's entry is absent, which trips invariant 3 (`popcount(A) + M != G`) rather than silently shrinking the expectation |
| `futoi-unchanged` | 2 | `TOUCH-EXISTING` (one byte in `capture_index_futures_snapshot_local.py`), `DIGEST-NOT-COMPARED` | the sha256 set difference names the file |
| `futoi-monitor-gap` | 2 | **`MONITOR-SCOPE-UNCHECKED`** (the assertion on `:463` removed), **`MONITOR-ASSUMES-COVERED`** (the guard asserts coverage instead of the gap) | the first leaves the guard unable to notice a widened filter; the second makes it fail on the tree as it is, which is the whole point of pinning a measured fact rather than a hope |

**Mutant count: 5+8+6+10+7+8+6+8+13+15+6+8+18+6+10+2+2 = 138**, over **17** guards. Recomputed from
the revised enumeration, not aimed at. The trail, so the number is auditable rather than asserted:
**102** at the first revision → **127** after the first round of operator changes (+25) → **138** now
(+11), the 11 being 2 for change 1's exit codes (`VERDICT-EXIT-RESTARTS`, `VERDICT-EXIT-IS-ONE`), 5 for
change 2's cross-process verdict (`VERDICT-PER-PROCESS`, `COUNTERS-NOT-PERSISTED`,
`COUNTERS-OVERLAP-UNCHECKED`, `L-SUMMED-TWICE`, `ROWS-WRITTEN-FROM-COUNTER`), 3 for change 3's `M`
(`VERDICT-IGNORES-M`, `VERDICT-M-CLAUSE-REMOVED`, `MISSED-NOT-COUNTED`) and 1 for the carry-forward
(`PRIOR-DAY-VERDICT-SKIPPED`, which Q-OP-13 may cut — if it is cut the count is **137** and this line
is corrected). Change 4 added no mutant: X6 was a wrong fixture description, and the behaviour it now
describes is already asserted by `AUTH-STOPS-ON-FIRST` and `TRANSIENT-LATCHES`. **Guard count stays
17** — both changed guards already existed. If the build finds a mutant that cannot be written as a
single exact-string patch, the count changes and this line is corrected, never the enumeration bent to
keep the total. (Tape's comparable figure is 134 mutants over its 12 stage-2b guards,
`docs/tape/L2_live_runner_plan.md:485-487`.)

`SKIP` set (reported SKIPPED, never counted as caught): Python 3.10.12 is the box interpreter (M13),
and `csv.writer` on < 3.11 raises on a NUL **before** a writer's own refusal is reached — the exact
condition tape recorded as operator ruling 3 (`tests/tape_live_mutants.py:40-42`). So the NUL mutant of
`futoi-upsert-only` is skipped on the box, its branch is **asserted, not proven able to fail** there,
and Local (3.12) is its only real run. This is listed in §16.

---

## 14. What fakes on the box can and cannot prove (box-only list)

The guards run with a fake Dhan transport, a fake `psql` shell and a fake table. On the box, with no
network and no database, they **can** prove:

- the grid, the `:30` second, the one-call-per-minute guard, the 15:40 extra, the clock edges
- the resolver's columns, filter, order and the no-substitution rule, against a fake read connection
- the block→row mapping, NULL-vs-0, units left undivided, the `ts`/`captured_at` distinction
- files-first ordering and typed set equality
- every rendered SQL script's text, including the absence of `DELETE`/`TRUNCATE` and the quoting of
  hostile literals
- the start-up verdict for all 12 refusals, by feeding the parser crafted check output
- every error classification, every threshold boundary, the latch across days, and that
  **`write-clear` and `--check` are both refused against a live heartbeat at the 180 s bound**
- the credential lifecycle against a **fixture** `.env`: re-read per call, the parser's shapes, the
  token never entering `os.environ`, the refusal on an absent gate credential, the import order, and
  the mode gate on the read credential file
- the verdict arithmetic `(G − S_dhan)·C − B − L`, on planted counters, at each clause's boundary
- that no secret reaches argv, the child environment, a file or a log
- that no existing engine file changed
- that `monitor_orchestrator_health.py:121` and `:463` still scope the hung probe to the orchestrator —
  a static read, so the box can prove it

They **cannot** prove, on the box, with fakes:

- that Postgres accepts the DDL — in particular that the `GENERATED … STORED` expression is accepted.
  M9 measures the two functions' volatility, which is the *reason* to expect acceptance; it is not the
  acceptance. Only the apply proves it
- that `futoi_w` can connect, that `CONNECTION LIMIT 1` behaves as assumed, that the RLS policies admit
  today and refuse another day, or that the role lacks DELETE/TRUNCATE in fact rather than in the
  check's own output
- the real server's text form of any literal — that is what `db-literal-check` is for, and it needs a
  database
- any Dhan behaviour: the quote endpoint's rate limit (**established nowhere**, F13), whether `429` or
  `DH-904` is ever returned, whether `DH-904` really is a throttle (Q-OP-4 rules it one **on user
  reports, not on a measurement or a vendor document** — the ruling's consequence is benign either way,
  since a throttle and an unknown code both want skip-and-count), or whether `last_trade_time` is IST
- whether `oi mod lot == 0` holds **intraday** — all three Stage 0a samples carry one frozen post-close
  value per instrument (`futoi_stage0a_fields_2026-11-28.md:75`)
- memory and wall-clock behaviour of a 6.5-hour resident process under the live capture chain. **G6's
  measured peak RSS is what sets `MemoryMax` and `--rss-cap-mb` (Q-OP-1), and G6 is a replay, not a
  live day** — the numbers are derived from the closest thing available, and the first live day (G13)
  is the only test of whether they hold
- that the systemd unit's sandbox directives permit what the writer needs — in particular that
  `ProtectHome=read-only` plus `ReadWritePaths` lets the writer read
  `$HOME/.merdian_ro_env` and the engine `.env` while writing only its out dir
- that the real `/home/ssm-user/meridian-engine/.env` parses as the fixture does. **No test opens it**
  (rule 19), so the parser is proven against X16 and asserted against the real file

---

## 15. Gate order

Each step is named so a partial run is visible as a partial run (the S81 part-run lesson).

| # | Step | Who | Pass criterion |
|---|---|---|---|
| G0 | Stage 0a artefacts committed with `git add -f` **at the lane close, on the operator's word** (RULED, Q-OP-9), so this plan's citations resolve | **operator's word, CC runs it** | the four cited files tracked at the branch head |
| G1 | **Red first**: all 17 guards written, every one FAILS for the reason §12 names. `_futoi_selftest` passes with no writer present | CC | `GUARDS FAIL (0/17)` — except the two guards that are green from the first minute (`futoi-unchanged`, `futoi-monitor-gap`), whose red-first evidence is a scratch-copy edit recorded separately |
| G2 | **Green**: `services/futoi/` written; 17/17 guards PASS | CC | `FUTOI GUARDS PASS (17/17)` |
| G3 | `--anchor-check`: every mutant's anchor matches exactly once, every named guard exists | CC | `138 / 17 / 0 bad` |
| G4 | Mutants **×1**: 138 caught, 17 controls PASS | CC | `MUTANTS PASS (137/137 caught x1, 1 skipped (…-NUL-…), 17/17 controls x1)` on 3.10; 138/138 on 3.12 |
| G5 | **LF export check**: `git -c core.autocrlf=false archive <sha>` into a clean dir; G2 and G4 re-run there; record `CODE_SHA` | CC | identical results; `CODE_SHA` recorded |
| G6 | **Replay**: the recorded Stage 0a responses driven through a whole simulated day (X1 for the morning, X4 for the contract set), 377 grid points, `--db-write` against the fake table; rows in the CSV == rows in the fake table == `rows_expected_final`. **This step also measures peak RSS** — reported with `/usr/bin/time -v` or `resource.getrusage`, under `( ulimit -v 700000 )` | CC | `REPLAY PASS`, the three counts equal and stated, **and the measured peak RSS printed** |
| G6a | **Set the two memory numbers from G6's measurement** (RULED, Q-OP-1): `MemoryMax = 2 × peak`, floor `256M`; `--rss-cap-mb = 1.5 × peak`. Written into `docs/futoi/futoi-1m.service.template` and into §3 of this plan, with the measurement beside them | CC | both numbers present, each shown as the arithmetic on the G6 figure, never as a bare constant |
| G7 | **Mutants ×5**, outside CC, alone | **operator** | `caught x5`, `controls x5` |
| G8 | Commit — **on the operator's word only** | CC | commit message carries the guard/mutant counts, the `CODE_SHA`, and the sha256 of each test file |
| G9 | **Box suite**: `( ulimit -v 700000; bash tests/run_offline.sh )`, outside 08:30–15:40 IST on weekdays (rule 23; `tests/run_offline.sh:18-33`) | **operator** | `OFFLINE PASS`, 44/44 |
| G10 | **Apply the DDL** (§7), as `postgres`, statement by statement; then §7.8 in one execution | **operator** | every expected value of §7.8 matches, including `n_table_comments = 1` and `n_col_comments = 7` |
| G11 | **Install**: unit runs as **`ssm-user`** (not a dedicated user, §3.2); out dir **`/home/ssm-user/futoi-1m`** (Q-OP-12) with `ReadWritePaths` and `ProtectHome=read-only`; `/home/ssm-user/.futoi_w_env` mode 600 holding `FUTOI_W_DSN` and `MERDIAN_FUTOI_1M_ENABLED`; `$HOME/.merdian_ro_env` left exactly as it is; **`RestartPreventExitStatus=2 3 4`** (§3.3); unit + timer installed, **timer not enabled** | **operator** | `systemctl daemon-reload` clean; `systemctl is-enabled futoi-1m.timer` → `disabled`; `stat -c '%a %U'` on the new env file → `600 ssm-user`; `systemctl show -p RestartPreventExitStatus futoi-1m.service` lists 2, 3 and 4 |
| G12 | `--check` with `--db-write`, as `ssm-user`, **outside market hours and with no session running** | **operator** | `CHECK PASS`; a deliberate wrong-role attempt prints R1 and writes nothing; **a `--check` attempted against a live heartbeat is REFUSED, not run** (§8.1) |
| G13 | **First live day**: manual `systemctl start`, operator watching | **operator** | heartbeat advances every minute; **`M == 0`**; the ledger row completes with **exit 0**; `rows_written == rows_expected_final`; `S_dhan ≤ 30`; `distinct_ltp ≥ 5` on rank 1 for both symbols; `counters.json` has one instance with `verdict_written: true`; **no `FUTOI_WRITE_LATCH.json` on disk** |
| G13a | **The restart path, deliberately, on the first live day after 15:41** — `systemctl kill` the unit mid-session is NOT done on a live day; instead re-run the day under `--clock sim` from the real `counters.json` and confirm the union arithmetic against the table | **operator** | the re-run's `rows_expected_final` equals the live day's, computed from the same counter file |
| G14 | **Second live day**, unwatched except for the two files | **operator** | the heartbeat and the ledger row for day 2 exist and the verdict passed, which is the only evidence that nothing from day 1 latched or carried. **Also: no `no_verdict_written` child row for day 1** (§10.1 carry-forward), which is the evidence that day 1's verdict was actually written rather than merely assumed |

CC never applies DDL, never installs, never enables a timer, never runs G7 or G9, never opens
`/home/ssm-user/meridian-engine/.env`, never edits `monitor_orchestrator_health.py` on the branch, and
never commits before G8's word.

---

## 16. Asserted, not proven able to fail

Each of these is in the tests but has not been shown to catch a real defect under the conditions it
runs in. Listing them is the point: a guard that cannot fail is documentation (rule 0).

1. The NUL mutant of `futoi-upsert-only` on Python 3.10.12 — `csv` raises before the writer's refusal
   (tape's ruling 3, `tests/tape_live_mutants.py:40-42`). The 3.10 branch asserts a fail-safe crash;
   only Local 3.12 exercises the refusal itself.
2. `futoi-unchanged` **and `futoi-monitor-gap`** — both green from the first minute; their red-first
   evidence is a deliberate scratch-copy edit, not a real regression. `futoi-monitor-gap` is the
   stranger of the two: it pins a *gap*, so it will fail on the day the engine intake of §3.1 lands,
   and that failure is the intended signal rather than a defect.
3. `latch_write_failed` (disk full / permission) — reached only through an `os` shim, never through a
   real full disk.
4. `write-clear`'s pid-alive branch **inverted relative to tape**: tape's was asserted-not-proven
   because Local is Windows and `os.kill(pid, 0)` never ran there
   (`docs/tape/L2_live_runner_plan.md:603-611`). This box is POSIX (M13), so for futoi the pid branch
   **is** exercised and the **non-POSIX state-and-age-only** branch is the one nothing tests. The
   asserted-not-proven item is the opposite half, and saying so is the point — copying tape's sentence
   unchanged would have recorded the wrong half.
5. `MIN_DISTINCT_LTP = 5` — the threshold is pre-registered, but no frozen live source has ever been
   observed on this relation, so the check has never fired on a real defect.
6. R2 ("the write role is the same role as the read connection") — only reachable by misconfiguration
   the install note forbids; tested by crafted check output alone.
7. The `GENERATED … STORED` expression's **acceptance** — M9 measures volatility, not acceptance (§14).
8. `OVERRUN_S = 45.0` — derived from the 60 s budget, never observed to trigger.
9. The `blocks_missing` per-contract path — no key was ever observed absent (F6); X10 is a hand-made
   deletion.
10. The `futoi-restart` model-rebuild guard against a **withheld** row — futoi has no grain constraint
    distinct from its PK, so tape's guard-34 case has no futoi analogue; the restart guard therefore
    tests less than tape's does.
11. **The Dhan credential parser against the real file.** X16 proves the parser on four hand-made
    shapes; `/home/ssm-user/meridian-engine/.env` is never opened by any test (rule 19), so the claim
    that it parses is an assertion. The first live day is its only run, and a parse failure there is a
    refusal, not a silent empty token — which is the reason
    `CRED-MISSING-DEFAULTS-EMPTY` is a mutant.
12. **The 08:20 IST token rotation itself.** §6.5's whole design exists for it, but no test observes a
    rotation landing mid-session; X16 simulates one by changing the fixture between reads.
13. **`MemoryMax` and `--rss-cap-mb`.** Set by the G6a rule from a replay measurement. A replay's peak
    is asserted to bound a live day's peak; nothing proves it.
14. **`CLEAR_STALE_S = 180`.** Derived as 3× the healthy ~60 s heartbeat gap, but the healthy gap
    itself is a design intention until G13 measures it.
15. **The restart path on a live day.** X21 proves the union arithmetic under the sim clock; a real
    mid-session death is not induced on a live day (G13a re-runs the day in sim from the real counter
    file instead). So "a restart on a live day produces a correct day verdict" is asserted, not
    observed, until one happens by itself.
16. **The exit-4 → no-restart behaviour.** `RestartPreventExitStatus` is asserted statically against
    the template text and `systemctl show` at G11; **systemd is never actually made to see an exit 4**
    in any test, because nothing in this lane starts the unit. The first failing-verdict day is its
    only run, and the tell that it worked is the *absence* of a second ledger row for that day.
17. **The carry-forward's prior-day `rows_written`.** Reported unavailable by construction
    (`futoi_w` is day-scoped), so the carried row names a shortfall it cannot quantify. That is
    deliberate — a guessed figure would be worse — but it means the carried row is a flag, not a
    measurement.

## 17. Not tested

1. The Dhan quote endpoint's rate limit and its interaction with the engine's existing ltp cron
   (F13; `futoi_stage0a_fields_2026-11-28.md:73`, `:77`).
2. Whether the `:30` second avoids the engine's calls in fact — F9 is operator-supplied and the Stage 0a
   doc disclaims the second-level claim.
3. `last_trade_time`'s timezone (F5). The column is text and nothing parses it.
4. Whether `oi mod lot == 0` holds intraday (`futoi_stage0a_fields_2026-11-28.md:75`).
5. `oi_day_high` / `oi_day_low` `0` on BSE_FNO — not stored, so not tested (`:76`).
6. Long-run memory and the 6.5-hour resident process under live load.
7. Behaviour when `dhan_scripmaster` is reloaded **mid-session** (cron fires 07:00 IST on the 1st and
   15th, before the session; but a manual reload during a session would leave the writer on a stale
   contract set, by design — it resolves once).
8. Concurrent runs. The design assumes one process; nothing enforces it beyond `CONNECTION LIMIT 1`,
   which refuses the second one's **database** connection, not its Dhan calls — and because connections
   are opened per grid point and released (§8.1), two writers could interleave for a long time before
   either met a `53300`. The `--check` refusal (§8.1) closes the one case this lane creates; two
   *sessions* is not closed and is not tested.
9. Recovery from a partial upsert: the script is one transaction, so a partial commit cannot occur —
   asserted by the script shape, not by a torn-write experiment.
10. **Whether a dead futoi process is ever noticed.** §3.1: no scheduled watcher covers it, measured.
    This is the largest untested property of the chosen shape and it is not closable inside this lane.
    The §10.1 carry-forward narrows it — a day with no verdict is flagged on the **next** trading day —
    but "next trading day" is up to four days later over a long weekend, and if the writer never runs
    again nothing flags anything.
11. **A day on which the unit never starts at all.** It leaves no `counters.json`, so the carry-forward
    has nothing to read and `M` is never computed. An unfinished-row probe cannot see it either
    (§3.1). The "no row started today by 09:20 IST" half of the Q-EN-7 intake is the only thing that
    would, and it is not in this lane.
12. Anything about retail, Marketview or the Board. This relation is operator-only.

## 18. Open questions

### Answered by the operator, 2026-11-28 — recorded here, applied in the sections named

| # | Ruling | Applied in |
|---|---|---|
| Q-OP-1 | Deploy on this box. `MemoryMax = 2 × measured peak RSS` (floor `256M`), `--rss-cap-mb = 1.5 × measured peak`, the peak from the replay gate; **no number until measured** | §3 table, §3.2, G6/G6a |
| Q-OP-2 | Shape **(b)** | §3 header, §3.2 |
| Q-OP-3 | `trading_day` generated column **accepted** | §6.3, §7.1 |
| Q-OP-4 | `DH-904` is Dhan's throttling code by user reports; classed with `429` as **`dhan_throttle`**, skip-and-count | §9.1, §9.1a, §14 |
| Q-OP-5 | 30 of 377 **stays, as a verdict threshold, not a stop** | §9.1a, §9.3, §10.1 clause 2 |
| Q-OP-6 | `CLEAR_STALE_S = **180**` | §9.3, §9.4, §8.1 |
| Q-OP-7 | Write the symbol that resolves; **the day's verdict fails** | §6.2, §10.1 clause 5 |
| Q-OP-8 | The operator generates the `futoi_w` password; `FUTOI_W_DSN` in **its own file, mode 600**, separate from every other credential | §3.2, §7.3 |
| Q-OP-9 | Stage 0a artefacts committed with `git add -f` **at the lane close, on the operator's word** | G0 |

| Q-OP-10 | Parse `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from the engine `.env` and set them into `os.environ` **before** importing `core.*`; `WorkingDirectory` is **not** the engine tree | §6.6, §3.2 |
| Q-OP-11 | `--check` **refused** during a live session; `CONNECTION LIMIT 1` **stays** | §8.1, §9.4, §12 `futoi-latch` |
| Q-OP-12 | Out dir **`/home/ssm-user/futoi-1m`** | §3.2, §10.1, G11 |

### New, raised by this revision

- **Q-OP-13** The **carry-forward verdict** (§10.1, last paragraph) is beyond the ruling. It closes a
  hole the ruling exposed: if no process reaches 15:40, **no verdict is written at all**, and an absent
  verdict looks exactly like a day nobody has got round to reading. The carry-forward makes the next
  trading day's start-up read the previous day's `counters.json` and, if `verdict_written` is false,
  write one `log_child_run` row with reason `no_verdict_written`. Cost: one extra file read at start-up
  and at most one extra ledger row per gap. **Keep it, or cut it** — if cut, the mutant count drops to
  137 and §17 item 10 becomes the whole of the mitigation.
- **Q-OP-14** §3.3 adds **two** mutants where change 1 asked for one (`VERDICT-EXIT-RESTARTS` on the
  unit template, `VERDICT-EXIT-IS-ONE` on the code path). They are different defects with different
  witnesses and one exact-string patch cannot express both. Flagged only so the extra one is a choice
  on the record rather than a quiet addition.

### For the engine — unchanged, and to the engine intake (operator, 2026-11-28)

**Q-EN-7, added by change 4.** The orchestrator monitor's hung-run probe is scoped to one
`script_name` (`monitor_orchestrator_health.py:121`, `:463`), so no scheduled check sees a
`capture_futures_oi_1m` row stuck at `RUNNING`; and `HUNG_MIN = 6` (`:157`) is derived from the
orchestrator's own ~305 s healthy duration (`:150-156`), so simply widening the filter would page all
day on a *healthy* 6.5-hour session. The fix is a per-script bound — `(script_name, max_minutes)`
pairs — plus a separate "no row started today by 09:20 IST" check, because a writer that never starts
leaves no unfinished row to find. **This lane does not edit that file** (§3.1).

- **Q-EN-1** `tape_live_*` has four live tables, RLS on, and **zero** `data_contracts` rows (M11). Is
  that a known gap, or does the 2b contract seed simply never run? It decides whether futoi's contract
  rows need a different apply step.
- **Q-EN-2** `pg_default_acl` still grants `anon` ALL on new `public` relations owned by
  `supabase_admin` (M8) — the §D.81 remediation (`ALTER DEFAULT PRIVILEGES`) appears unapplied. Is
  there a standing TD for it, and should futoi's DDL carry the `ALTER DEFAULT PRIVILEGES` as well as
  its own `REVOKE`?
- **Q-EN-3** `core.execution_log` has no heartbeat (B6) and `complete()` can only return 0
  (`core/execution_log.py:274`). Should futoi's own-verdict-to-exit-code pattern be lifted into
  `core/` for the next long-running writer, or stay local?
- **Q-EN-4** `tape_w` has `CONNECTION LIMIT 2` (M4); the operator's futoi ruling says 1. With one
  resident process, 1 is right — unless `--check` and the session can overlap. Confirm 1.
- **Q-EN-5** `capture_index_futures_snapshot_local.py`'s naive `today_iso_local()` (`:96-101` → `:165`)
  is the same defect class futoi avoids. Does fixing it belong in this lane or stay filed?
- **Q-EN-6** The `tape_w` role exists in the database (M4) but **no SQL file on `origin/tape/live-l2`
  creates or grants to it** — `sql/2026-11-06_tape_live_tables.sql` only *refuses* if `tape_ro` and
  `merdian_ro` are absent (`:11-21`), and the role's shape survives only in the install note and the
  tests. Is there a committed role file elsewhere, or is this the ADR-025 D2 clause-4 gap again (a file
  that exists but does not reproduce the object)? futoi ships its role SQL and a rollback file either
  way; the question is whether `tape_w` needs the same retrofit.

## 19. Time estimate (an estimate, scaled from tape 2b's measured figures)

Measured, tape 2b: `(195 + 35) × 5 = 1,150` runs at **21.6 to 29.3 s per run** (upper bound 30.2 s),
about **9.6 h** (`docs/tape/L2_live_runner_plan.md:485-490`).

futoi's per-run cost should be far lower: tape's guard runs load whole recorded days from S3 fixtures
and replay a 75-cycle offline day; futoi has 377 grid points of ≤6 tiny rows and no fixture larger than
a few hundred kB. Scaling by the dominant term (fixture I/O and replay, which futoi does not have) and
keeping interpreter start-up and tree copy, the estimate is **3 to 8 s per run**:

- `(138 + 17) × 5 = 775` runs × 3–8 s ≈ **39 to 103 minutes** for G7.
- G4 (×1): 155 runs ≈ **8 to 21 minutes**.
- G9 (whole offline suite): the existing 42 steps measured wall 1:48 with peak RSS 331,740 kB
  (`tests/run_offline.sh:88`); the two futoi steps add the G7 figure, so ≈ **43 to 107 minutes** total.

The run count has moved twice: `585` at the first draft (102 + 15), `720` after the first round of
operator changes (127 + 17), `775` now (138 + 17). The **per-run** estimate of 3–8 s has not changed
and is still the weakest figure here, so the whole movement is run count and the whole uncertainty is
still the per-run number. X21 and X23 are the first fixtures that drive a multi-process run inside one
guard, which is the one thing that could push the per-run figure above the range — the `--only` run in
G2 is what settles it.

Build effort, also an estimate: tape 2b ran 2026-11-14 → 2026-11-23 across several operator gates.
futoi's surface is roughly one third (one table not four, no epochs, no S3, no rebuild scope), so
**three CC sessions** — G1 red-first, G2+G3+G4 green, G5+G6+G6a export, replay and the two memory
numbers — plus two operator-run gates (G7, G9) and the apply/install sequence (G10–G14).

**These are estimates scaled from a different workload, not measurements.** The first `--only` run of
one guard in G2 gives the real per-run figure, and this section is corrected from it before G7 is asked
for.

---

*End of body.*
