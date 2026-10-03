# ENH-133 writer — design spec (S89, 2026-10-03)

> **DESIGN ONLY. No writer was written, no DB write was made, no engine file was
> touched.** This spec is authored in `~/meridian-cc`; the writer is production engine
> code and deploys via the engine path (push + `git pull --ff-only` after 16:00 IST, from
> the operator's own terminal).
>
> Companion documents: **`ENH-133_schema_spec_S89.md`** (the bound column spec),
> `sql/2026-10-03_s89_gex_cycle_history.sql` (authored-not-applied DDL),
> `sql/2026-10-03_s89_seed_pin_state_params.sql` (authored-not-applied param seed).
>
> **§6's measured session-gate defect was RULED 2026-10-03 — Option A, the three-state gate
> plus an EOD reconciler.** §6 now records the resolution; the reconciler is a separate
> deliverable specified in **`ENH-133_reconciler_spec_S89.md`**. Everything in this file is
> settled.

---

## 1. PURPOSE

At each γ cycle, once the run's scalars exist, **upsert one `gex_cycle_history` row per
`(symbol, expiry_date)` for that `run_id`**. Idempotent on the PK
`(symbol, expiry_date, ts)`.

New script: **`write_gex_cycle_history_local.py`**, with its own `ExecutionLog` row and
its own exit code.

---

## 2. HOOK POINT — measured, not chosen for convenience

**`run_option_snapshot_and_gamma.py`, a new step after the `vol_rc` guard (`:105`) and
before `run_market_state` (`:106`)**, invoked like its siblings:

```python
cmd = ["python", "write_gex_cycle_history_local.py", run_id]
```

**Why not at the end of `compute_gamma_metrics_local.py`.** Measured 2026-10-03:
`v_gex_strike_rank` and `v_gex_strike_walls` **read `volatility_snapshots`**
(`pg_get_viewdef` probe returned `t` for both; `f` for `v_gex_concentration`,
`v_gex_max_pain`, `v_gex_pin_maxpain`, `v_gex_repriced_flip`). The orchestrator runs:

```
:97   gamma_rc = run_gamma(run_id)          <- gamma_metrics + gex_strike_snapshots land
:102  vol_rc   = run_volatility(run_id)     <- volatility_snapshots lands
:106  ms_rc    = run_market_state(symbol)
```

So at `compute_gamma_metrics_local.py:1398` there is **no `volatility_snapshots` row for
this `run_id` yet**. A writer hooked there would read `atm_iv_used` as NULL or as the
**previous cycle's** value, and with it `sigma`, `dist_sigma`, `band_used`, `put_wall`
and `call_wall` — storing σ-derived scalars from one cycle against another cycle's
gamma. That is precisely the cross-clock defect this table exists to make visible.

The chosen point is the **first instant at which every bound source sits on one clock**.

**Cost, stated:** this makes the writer **two** engine-path changes — the new script and
one new step in the orchestrator.

---

## 3. WRITE MECHANICS — mirrored from the gamma writer

| Concern | Binding |
|---|---|
| Client | `create_client(supabase_url, service_role_key)` — the `compute_gamma_metrics_local.py:69` pattern, module-level `SUPABASE` |
| Upsert | `SUPABASE.table("gex_cycle_history").upsert(rows, on_conflict="symbol,expiry_date,ts")` — mirrors `:1113` / `:1215` |
| Provenance | `writer = "write_gex_cycle_history_local.py"`, `writer_version = "<tag>"` — mirrors the `builder` / `builder_version` precedent at `:1101-1102` |
| Write contract | `ExecutionLog(script_name=…, expected_writes={"gex_cycle_history": N}, …)`, then `log.record_write("gex_cycle_history", N)`, closing `log.complete()` |
| Shadow | **NONE.** No `--shadow`, no shadow table — §4 |

### 3.1 `expected_writes` is an EXACT count, never a floor

**Rule 0 clause 1.** `_compute_contract_met` tests `actual < expected`
(`core/execution_log.py:297-303`), so `{"gex_cycle_history": 1}` passes on 1 row and on
163 — indistinguishable. The writer **knows** its leg count before it writes: it is the
number of distinct `(symbol, expiry_date)` pairs for the `run_id` in `gamma_metrics`.

```
N = count of distinct (symbol, expiry_date) in gamma_metrics for this run_id
expected_writes = {"gex_cycle_history": N}      # exact, computed, not literal
```

A run that writes N−1 rows must fail the contract. If `N` is computed **after** the
upsert from the rows actually sent, the check asserts nothing — so `N` is derived from
`gamma_metrics` **before** the first row is built.

---

## 4. NO SHADOW TABLE — ruled

The writer writes **`gex_cycle_history` directly**. No `--shadow` flag, no
`gex_cycle_history_shadow`.

**Reason this is safe here and was not for gamma:** there is **no live consumer until
phase-2**, so a wrong row misleads nobody; and `held_for_cycles` is a **carry-forward
chain** — a shadow table would accumulate its own independent streak, so the two copies
would diverge in a way neither could be checked against. **On a bug: truncate and
restart.** The chain rebuilds from the next cycle forward.

This is a deliberate departure from the TD-NEW-12 (S28) shadow-vs-live split; it is
recorded here so the absence is visibly a decision rather than an omission.

---

## 5. DERIVED FIELDS

Per `ENH-133_schema_spec_S89.md` §3. Restated in writer terms, with the measured values
from the **NIFTY 2026-10-01 09:50:07+00** run as a worked example.

| Field | Rule | 10-01 value |
|---|---|---|
| `pin_leader_strike` | `v_gex_strike_rank.strike` @ `strike_rank = 1` | 22700 |
| `gamma_at_pin` | that row's `gex_cr` | 407101.3857451711 |
| `runnerup_share_ratio` | `share_of_abs(r2) / share_of_abs(r1)` | 0.074746 / 0.094194 = **0.7935** |
| `top5_share` | `cum_share_of_abs` @ `strike_rank = 5` | **0.360276** |
| `top5_share_n_ranks` | ranks actually available (`n_ranked`) | 110 ranked of 116 strikes → 5 |
| `conc_top1_share` | `v_gex_concentration.hhi_net` as-is, honest name | 0.09419433182919231685 |
| `conc_hhi` | **Σ over ALL ranked rows of `share_of_abs`²** — writer-derived | **0.04635883019194746740** |
| `max_pain_strike` | `v_gex_max_pain.max_pain_strike` | 22500 |
| `call_wall_strike` / `put_wall_strike` | `v_gex_strike_walls.call_wall` / `.put_wall` | 23000 / 22000 |
| `is_fresh` / `snapshot_age_min` | persisted from the pin/maxpain views | `f` / 2670.7 (Saturday read) |
| `chain_ts` | `option_chain_snapshots.ts` where `run_id = gamma_metrics.run_id` | 2026-10-01 09:50:07.41145+00 |
| `atm_iv` | `volatility_snapshots.atm_iv_avg` where **`source_run_id`** = `run_id` | 11.70527899673892 |

**Two join keys that are not named `run_id`.** `option_chain_snapshots` **does** have
`run_id` (480 rows carried the gamma `run_id` on that cycle, `ts` exactly equal) — bind on
it, **never on nearest-ts**: the maximum chain `ts` inside a ±5-minute window is
**09:55:07**, which belongs to the *next* cycle. `volatility_snapshots` has **no
`run_id`**; its key is **`source_run_id`**, whose value equalled `a8d9647a…` exactly.
Joining it on `run_id` would not compile.

### 5.1 `conviction`

```
T    = TRADING days to expiry        (NOT gamma_metrics.dte)
T    = max(T, 0.47)                  # floor
boost = min(2.53 * T ** -0.5, 3.70)  # cap
conviction = (1 - runnerup_share_ratio) * boost
```

**`gamma_metrics.dte` is CALENDAR days — measured, not assumed:**

| run date | expiry | stored `dte` | calendar | **trading days ahead** |
|---|---|---|---|---|
| 2026-09-23 | 2026-09-29 | 6 | 6 | **4** |
| 2026-09-30 | 2026-10-06 | 6 | 6 | **3** |
| 2026-10-01 | 2026-10-06 | 5 | 5 | **2** |

`dte` equalled the calendar difference on all 8 runs checked. **The writer converts via
`trading_calendar` (`is_open`, dates `> run_date` and `<= expiry_date`) and must never
feed `dte` to `boost()`.** Feeding calendar days to 10-01 would give
`2.53 · 5^−0.5 = 1.13` where the correct `2.53 · 2^−0.5 = 1.79` — a 58 % understatement,
in the direction that makes conviction look lower than designed.

**`trading_calendar` is a trust-anchor (Rule 18) and every gate over it fail-opens.** The
writer uses `core/trading_calendar_gate.py`, not a new inline copy (TD-S60-NEW-3). If the
calendar cannot answer, `conviction` is **NULL with a reason**, not computed off calendar
days.

### 5.2 `held_for_cycles`

Read the prior row for `(symbol, expiry_date)` ordered by `ts DESC`, **restricted to
`session_gate_state = 'OPEN'`**; if its `pin_leader_strike` equals this row's,
`held_for_cycles = prior + 1`, else `1`. First-ever row for a leg: `1`.

**Write-time values are PROVISIONAL.** A streak that begins before the day's first spot
tick starts on `PRE_TICK` rows, which the write-time rule cannot count. The EOD reconciler
recomputes `held_for_cycles` and `pin_state` over the finalised OPEN set and carries the
streak across date boundaries — reconciler spec §3.2.

### 5.3 `repriced_flip` — clock-matched or NULL

`v_gex_repriced_flip` has **no `run_id`, no `dte`**, names its expiry **`front_expiry`**,
carries `t_days`. It **cannot** be joined on `(run_id, symbol, expiry_date)`.

**Measured hazard:** its latest row on 2026-10-03 was `2026-10-02 10:10:04+00` at the
frozen spot **22421.95**, while the γ clock was `2026-10-01 09:50:07+00` — a
**~1,460-minute** gap onto a frozen book.

```
match on (symbol, same IST trading date as the run, front_expiry = expiry_date)
  matched   -> repriced_flip_level = flip
               repriced_flip_ts    = the ts the view RETURNED
               repriced_flip_source = 'CLOCK_MATCHED'
  no match  -> repriced_flip_level = NULL
               repriced_flip_ts    = the ts the view RETURNED (recorded anyway)
               repriced_flip_source = 'UNMATCHED_NULL'
```

**Never take the view's stale latest.** The DDL `CHECK` makes `UNMATCHED_NULL` + a
non-NULL level impossible, so a writer bug fails loudly instead of storing an off-clock
number.

---

## 6. SESSION GATE — three states (RULED 2026-10-03, Option A)

### 6.1 Independence: confirmed

**`market_spot_snapshots` is written by independent cron lines, not by
`run_market_state`:**

```
41 3  * * 1-5            capture_market_spot_snapshot_local.py   (09:11 IST)
*/1 03,04,…,09 * * 1-5   capture_spot_1m_v2.py                   (08:30–15:29 IST, per minute)
```

`build_market_state_snapshot_local.py` — the `run_market_state` step that runs **after**
the hook — contains **no reference to `market_spot_snapshots`**. The gate does not depend
on a step that has not run.

### 6.2 But the ticks are NOT present at the first cycles of the day — measured

| date | first γ run | first spot tick | γ cycles | **cycles before the first tick** |
|---|---|---|---|---|
| 2026-09-22 | 08:40:06 | 09:11:03 | 74 | **7** |
| 2026-09-23 | 08:35:06 | 09:11:04 | 82 | **7** |
| 2026-09-24 | 08:35:05 | 09:11:04 | 83 | **8** |
| 2026-09-25 | 08:35:05 | 09:11:04 | 83 | **8** |
| 2026-09-28 | 08:40:06 | 09:11:04 | 82 | **7** |
| 2026-09-29 | 08:30:07 | 09:11:03 | 83 | **8** |
| 2026-09-30 | 08:35:06 | 09:11:04 | 83 | **8** |
| 2026-10-01 | 08:40:06 | 09:11:03 | 80 | **6** |

At the first γ run of 2026-10-01 the gate's inputs are **0 ticks, 0 distinct spot**, on a
day that traded normally. The first tick lands at **09:11:03** every day — the `41 3`
cron, **not** the per-minute feed, whose 08:30 start is not reaching this table.

**A boolean gate therefore fires for a reason other than the one it names** (Rule 0
inverted): it reports "frozen" for *pre-open tick absence*. It would exclude ~**9 %** of
each day's rows from the default read and shorten every streak beginning before 09:11.
**A whole-trading-date evaluation does not fix it** — at 08:40 the later ticks do not yet
exist for the writer to read.

### 6.3 Resolution — three states, write-time provisional

```
ticks         = count of market_spot_snapshots for (symbol, this IST date, ts' <= ts)
distinct_spot = count of distinct spot over that same window
session_gate_ticks = ticks

ticks == 0                            -> session_gate_state = 'PRE_TICK'
distinct_spot > 1                     -> session_gate_state = 'OPEN'
else (ticks >= 1, distinct_spot == 1) -> session_gate_state = 'FROZEN'
```

`session_gate_state` is `NOT NULL`; `session_gate_ticks` is nullable so that "the writer
could not count" (NULL) stays distinguishable from "the tape had not started" (0).

**`held_for_cycles` and `pin_state` at write time are PROVISIONAL**, carried forward over
`OPEN` rows only. **Both are finalised by the EOD reconciler**, which is the only component
that can see a completed date — `ENH-133_reconciler_spec_S89.md`.

**Option B was rejected and the reason is worth keeping.** Calendar-assisting the gate
(`trading_calendar.is_open` AND (`ticks = 0` OR `distinct_spot > 1`)) needs no reconciler,
but **2026-10-02 is ABSENT from `trading_calendar`** — the Rule 18 fail-open shape — so the
frozen day's pre-tick cycles would read `OPEN`. The option that removes the reconciler is
the one that hands the frozen day a true window.

## 7. PIN-STATE MACHINE

Evaluated in this order; **first match wins**:

```
if   conc_top1_share < pin_state.nopin_conc_floor.<sym>      -> 'NO PIN'
elif held_for_cycles < pin_state.stable_held_for.<sym>       -> 'SHIFTING'
elif held_for_cycles >= pin_state.locked_held_for.<sym>
     and runnerup_share_ratio <= pin_state.locked_ratio_max.<sym>  -> 'LOCKED'
else                                                         -> 'STABLE'
```

### 7.0 ONE home for the state machine — RULED 2026-10-03

**The ladder above lives in `core/pin_state.py` and nowhere else.** The writer and the EOD reconciler both
import it; **neither carries its own copy.** Two implementations of one rule is the shape ADR-020 was written
for — the gate said *no row → allow* while the seeder said *no row → closed* — and a parity claim between two
copies is asserted only by a test that compares them, never by a comment (Rule 0 clause 4). With one home the
comparison question does not arise. The missing-key behaviour in §7.1 is part of that shared helper, not of
either caller.

### 7.1 Thresholds are read, never hardcoded

Via **`core.parameters.get_parameter_num(key)`** with **no default argument**. The module
raises `ParameterNotFoundError`; the writer catches it and writes:

```
pin_state        = NULL
pin_state_reason = "missing parameter key: <key>"
```

**Never a substituted default.** Absence is not a verdict (ADR-020): the gate said
"no row → allow" while the seeder said "no row → closed", and every unseeded weekend read
as a trading day for ~6 consumers since S60. A default here would be the same shape.

Every other column on the row is still written — a missing threshold costs `pin_state`,
not the cycle.

### 7.2 The eight provisional values

`sql/2026-10-03_s89_seed_pin_state_params.sql`, authored-not-applied,
`ON CONFLICT DO NOTHING`, `change_reason = "ENH-133 provisional, owes D-6 calibration"`:

| key suffix | NIFTY | SENSEX |
|---|---|---|
| `stable_held_for` | 6 | 6 |
| `locked_held_for` | 12 | 12 |
| `locked_ratio_max` | 0.50 | 0.50 |
| `nopin_conc_floor` | 0.04 | 0.04 |

**These are a starting point so the machine runs, not a measured result.** Two scale
notes, because the S83 family is exactly this failure: `locked_ratio_max = 0.50` sits
against a measured `runnerup_share_ratio` of **0.7935** on 10-01, so that cycle would
**not** lock — plausible but untested; and `nopin_conc_floor = 0.04` sits against a
measured `conc_top1_share` of **0.0942**, i.e. a factor of ~2.4 of headroom, so NO PIN
would be rare. **Neither threshold was derived from a distribution.** D-6 calibration is
owed before any of these drive a displayed word.

**`merdian_calibrate.py` is NOT built here** — ENH-83 scope (see §9).

---

## 8. GUARDS AND ACCEPTANCE

| # | Guard | Pass condition | What makes it fail |
|---|---|---|---|
| **G1** | Write contract | `expected_writes` = exact leg count `N`, computed from `gamma_metrics` **before** the upsert | N−1 rows written; a floor of 1 could not see it |
| **G2** | Coverage (**TD-S54-NEW-1**) | after a dry run, **per-symbol distinct-`ts` coverage = 100 %** of the window's γ cycles | upsert merging a lost per-symbol write into silence — the exact S54 shape, where `insert → upsert` turned SENSEX's ~½-cycle under-write into a silent merge |
| **G3** | Provenance | `writer` and `writer_version` non-NULL on every row | a row whose origin cannot be traced after a version change |
| **A(a)** | Source columns exist | an `information_schema` query returns **all** bound `(table, column)` pairs **by name** | a renamed or dropped source column |
| **A(b)** | = G2 | | |
| **A(c)** | Frozen handling | **after reconciliation**, every row of a frozen date carries `session_gate_state = 'FROZEN'` and is excluded by the default read, and **no row of a traded date is left `PRE_TICK`** | a gate keyed on row count or distinct `ts`, both of which 10-02 passes; or a reconciler that promotes a frozen date |
| **A(d)** | `held_for_cycles` | **after reconciliation**, increments **1 → 73** across **2026-09-30, leader 23000, 08:50 → 14:50 IST**, and **resets to 1** on the first post-14:50 leader change | an off-by-one; a reconciler that fails to promote the pre-09:11 cycles; or a streak that resets across the overnight boundary when the leader did not change |

**A(d) is bound to 09-30, not to 28–29 Sep.** Measured: 2026-09-28 has **four**
interleaving rank-1 leaders (22800 ×49 spanning 09:20–14:15 *while* 23000 ×31 spans
08:40–15:40), so there is no stable run there to increment across. Longest consecutive
streaks in the window: **09-30 / 23000 / 73 cycles**, then 09-25 / 23000 / 64, 09-29 /
22600 / 48, 10-01 / 22700 / 25. The reset cycle's new leader is read from the data at
test time, never carried from this document.

**A(d) is a RECONCILER test, not a writer test, and that follows from the measurement.**
The 09-30 streak begins **08:50**, before that day's first tick at **09:11:04**, so at
write time its opening cycles are `PRE_TICK` and the run reads short. 09-30 traded, so the
reconciler promotes them to `OPEN` and the 1 → 73 run becomes continuous. **A(d) is
asserted after reconciliation and is not expected to pass at write time.** A(d) was not
loosened to accommodate the writer; the assertion moved to the component that can satisfy
it.

---

## 9. OUT OF SCOPE, EXPLICITLY

- **`merdian_calibrate.py`** — ADR-016 names it as the write API; it is absent from the
  tree; `ENH-83` reads **SHIPPED (S39)**; `merdian_parameters` measures **0 rows**. A
  three-way disagreement, filed as its own tech-debt item. **Building it is ENH-83 scope.**
- **No DDL applied, no seed applied, no writer written** in this pass.
- **No engine file touched.** Both engine-path changes (the new script, the orchestrator
  step) deploy via push + `git pull --ff-only` after 16:00 IST from the operator's own
  terminal.
- **No phase-2 consumer.** Nothing reads this table yet; the board work is separate.

---

*Writer design spec, Session 89, 2026-10-03. Read-only introspection via `bin/roq.sh` and
greps of `~/meridian-cc`. **§6.3 needs a ruling before the writer is built**; §§1–5, 7, 8
are bound and settled.*
