# ENH-133 — per-cycle layer-history table: bound pre-DDL spec (S89, 2026-10-03)

> **Scope RULED 2026-10-03** (`rulings_s89.md`). This is the **bound** spec: every source
> column named below was confirmed to exist by `information_schema` introspection on
> 2026-10-03, and each target type follows its **source** type rather than a convenience
> choice.
>
> **No DDL was applied in this pass.** The migration is authored at
> `sql/2026-10-03_s89_gex_cycle_history.sql` and has **not** been run against the
> database. Proposed table name **`gex_cycle_history`** — the ruling did not name it.
>
> **TD-S80-NEW-7 precedent:** a new table owes its own schema ADR before any DDL. This
> file is the artefact that ADR is written from; it is not itself the ADR.

---

## 1. GRAIN / KEY

| Decision | Value |
|---|---|
| Grain | **one row per `(symbol, expiry_date, ts)`** at the 5-minute γ cadence |
| Primary key | `(symbol, expiry_date, ts)` |
| `run_id` | **stored, not keyed** — `gamma_metrics.run_id` |
| Expiry coverage | **per-expiry, both legs** (W1 and W2), not front-only |
| Forward compatibility | the grain is a timestamp, not a cycle ordinal, so a future **1-minute pass (Candidate A)** writes into the same table **unchanged** |

**Why `ts` and not `run_id` in the key.** `run_id` is one value per cycle across both
legs, so it cannot distinguish the two expiry rows of the same cycle. Keying on
`(symbol, expiry_date, ts)` admits both legs and still rejects a duplicate write of the
same leg at the same instant.

---

## 2. COLUMNS — bound

`NOT NULL` on **`symbol`, `expiry_date`, `ts`, `run_id`, `is_trading_session`** only.
Every optional scalar is **NULLABLE** — measured reason: on the 10-01 run
`gamma_metrics.breadth_regime` is an **empty string** and `otm_oi_velocity` /
`spot_vs_range` are **NULL**, so a `NOT NULL` on a layer scalar would reject real
production rows.

### 2.1 Identity, clock, gate

| Target column | Type | Source | Note |
|---|---|---|---|
| `symbol` | `text` | `gamma_metrics.symbol` | NOT NULL |
| `expiry_date` | `date` | `gamma_metrics.expiry_date` | NOT NULL |
| `ts` | `timestamptz` | `gamma_metrics.ts` | NOT NULL — the γ run |
| `run_id` | `uuid` | `gamma_metrics.run_id` | NOT NULL |
| `is_trading_session` | `boolean` | **derived** (§3.6) | NOT NULL |
| `chain_ts` | `timestamptz` | `option_chain_snapshots.ts` **for this `run_id`** | §2.1a |
| `dte` | `integer` | `gamma_metrics.dte` | **CALENDAR days** — §3.5 |
| `spot` | `numeric` | `gamma_metrics.spot` | |
| `atm_iv` | `numeric` | `volatility_snapshots.atm_iv_avg` | join on **`source_run_id`** — §2.1b |

**§2.1a — `chain_ts` binds by `run_id`, not by nearest ts.** `option_chain_snapshots` has
a `run_id uuid`, and on the 10-01 γ run **480 chain rows carry the same `run_id`** with
`ts` exactly equal to the γ run's `ts` (`2026-10-01 09:50:07.41145+00`). A nearest-ts rule
would have been wrong: the maximum chain `ts` inside a ±5-minute window is **09:55:07**,
which belongs to the *next* cycle. Bind on `run_id`.

**§2.1b — `volatility_snapshots` has no `run_id`.** Its key column is **`source_run_id`**,
whose value on that cycle equals `gamma_metrics.run_id` (`a8d9647a…`) exactly. Joining on
a column named `run_id` would fail to compile against this relation.

### 2.2 Regime and flip (L6, L3)

| Target column | Type | Source |
|---|---|---|
| `net_gex` | `numeric` | `gamma_metrics.net_gex` |
| `gamma_regime` | `text` | `gamma_metrics.regime` |
| `flip_level` | `numeric` | `gamma_metrics.flip_level` |
| `repriced_flip_level` | `double precision` | `v_gex_repriced_flip.flip` |
| `repriced_flip_ts` | `timestamptz` | `v_gex_repriced_flip.ts` **as returned** |
| `repriced_flip_source` | `text` | `CLOCK_MATCHED` \| `UNMATCHED_NULL` |

`gamma_metrics.regime` reads `LONG_GAMMA`; **`gamma_zone`** (`MID_GAMMA`) is a *separate*
field and is not bound here. The two flips stay **separate columns per ADR-025 B7** —
measured on these runs they read **22692.00** (stored) and **22368.20** (L3 repriced),
different definitions on different clocks.

### 2.3 Pin and concentration (L1/L2/L12, E-D2)

| Target column | Type | Source |
|---|---|---|
| `pin_leader_strike` | `numeric` | `v_gex_strike_rank.strike` @ `strike_rank = 1` |
| `gamma_at_pin` | `numeric` | `v_gex_strike_rank.gex_cr` @ `strike_rank = 1` |
| `runnerup_share_ratio` | `numeric` | **derived** — §3.2 |
| `top5_share` | `numeric` | `v_gex_strike_rank.cum_share_of_abs` @ `strike_rank = 5` |
| `top5_share_n_ranks` | `smallint` | **derived** — the edge in §3.3 |
| `conc_top1_share` | `numeric` | `v_gex_concentration.hhi_net`, **renamed honestly** — §3.4 |
| `conc_top1_share_call` | `double precision` | `v_gex_concentration.hhi_call` — **semantics unverified** |
| `conc_top1_share_put` | `double precision` | `v_gex_concentration.hhi_put` — **semantics unverified** |
| `conc_hhi` | `numeric` | **derived** (§3.4) — true Herfindahl Σ(`share_of_abs`)² over all ranked strikes |
| `max_pain_strike` | `numeric` | `v_gex_max_pain.max_pain_strike` (γ clock, **E-D2**) — separate column |
| `pin_state` | `text` | **derived** — §3.7 |
| `pin_state_reason` | `text` | **derived** — why `pin_state` is NULL when it is |
| `held_for_cycles` | `integer` | **derived** — §3.8 |
| `conviction` | `numeric` | **derived** — §3.5 |

**Five scalars the ruling named do not exist in any relation** and are therefore writer-
derived, not selected: **runner-up strike, runner-up margin, gamma at pin, top-5 share,
per-rank shares**. `v_gex_pin_maxpain` has 30 columns and **nothing second-place and
nothing gamma-valued**; `v_gex_concentration` has `top_strike_net` — which is a *strike*
(22700), not a share.

### 2.4 Walls, freshness, provenance

| Target column | Type | Source |
|---|---|---|
| `call_wall_strike` | `numeric` | `v_gex_strike_walls.call_wall` |
| `put_wall_strike` | `numeric` | `v_gex_strike_walls.put_wall` |
| `is_fresh` | `boolean` | `v_gex_pin_maxpain.is_fresh` / `v_gex_max_pain.is_fresh` |
| `snapshot_age_min` | `numeric` | same pair |
| `writer`, `writer_version` | `text` | the writer's own identity |
| `created_at` | `timestamptz NOT NULL DEFAULT now()` | DB clock |

**Freshness is persisted, never dropped.** Both views carry their own staleness verdict —
measured `is_fresh = f` at `snapshot_age_min = 2670.7` reading on Saturday. Without these
two columns a stale-book cycle is indistinguishable from a fresh one once it is history.

---

## 3. WRITER LOGIC — the derived fields

### 3.1 Pin leader binding
`pin_leader_strike` = `v_gex_strike_rank.strike` at `strike_rank = 1`;
`gamma_at_pin` = that row's `gex_cr`. On 10-01: **22700**, `gex_cr = 407101.3857451711`.

### 3.2 Runner-up ratio
`runnerup_share_ratio = share_of_abs(rank 2) / share_of_abs(rank 1)`.
On 10-01: `0.074746 / 0.094194 = 0.7935`. **Near 1 = not locked.**

**This is a choice between two live definitions and must not be left to the writer.** The
runner-up margin is also derivable from `v_gex_max_pain`, which exposes one row per
`candidate_strike` with `total_pain`: ranks 1/2/3 are **22500 / 22550 / 22600** at
**+0.000 % / +0.609 % / +3.748 %** above the minimum, giving a margin of **0.609 %** on the
same run. The gamma-share definition above is the ruled one; the pain-based figure is
recorded so the two are never conflated.

### 3.3 Top-5 share, and its edge
`top5_share` = `cum_share_of_abs` at `strike_rank = 5` → **0.360276** on 10-01.
**If fewer than 5 ranks exist, take the maximum available rank's `cum_share_of_abs` and
store that rank in `top5_share_n_ranks`.** The edge is real: `v_gex_strike_rank` ranks only
**contributing** strikes (`n_ranked = 110` against `n_strikes = 116` on 10-01), so a thin
ladder can rank fewer than five. A NULL would be indistinguishable from "not computed";
the count makes the degradation inspectable.

### 3.4 Honest naming of the concentration scalar
`conc_top1_share` = `v_gex_concentration.hhi_net` **as-is**, under a corrected name.
**Measured 2026-10-03, NIFTY 10-01, from `gex_strike_snapshots`:**

```
top-1 share computed   0.09419433182919231685
true Herfindahl Σs²    0.04635883019194746740
hhi_net as published   0.09419433182919231685   <- equals top-1 share
rank-1 share_of_abs    0.09419433182919231685   <- identical
gamma_concentration    0.09419433182919230000   <- identical to 16 s.f.
```

So the published `hhi_net` **is the top-1 share, not a Herfindahl**, and differs from the
true HHI by a factor of ~2. **Never name this column `hhi_*` here.** `hhi_call` / `hhi_put`
are carried verbatim and flagged **semantics-unverified** — the net leg was proven, the
legs were not checked either way. Filed as a register note (tech_debt, 2026-10-03).

**And the real Herfindahl is stored alongside it, as its own column.**
`conc_hhi` = Σ over **all** `v_gex_strike_rank` rows for `(symbol, expiry_date, ts)` of
`share_of_abs`² — **writer-derived**, since no relation publishes it. **0.0464** on 10-01,
against `conc_top1_share` **0.0942**. The two answer different questions and both are kept:
`conc_top1_share` is **dominance** (how much the lead strike carries), `conc_hhi` is
**dispersion** (how concentrated the whole ladder is). **Per-side true HHI (call / put) is
DEFERRED** — `hhi_call` / `hhi_put` remain carried as unverified top-1-share-per-side and are
**not** Herfindahls; nothing may publish them as such until checked.

### 3.5 Conviction, and the dte conversion
`conviction = (1 − runnerup_share_ratio) · boost(T)`, with
`boost(T) = 2.53 · T^(−0.5)`, **cap 3.70, floor T = 0.47** (D-5b / D-5c).

**`T` is TRADING days, and `gamma_metrics.dte` is CALENDAR days — measured, not assumed:**

| run date | expiry | stored `dte` | calendar days | trading days ahead |
|---|---|---|---|---|
| 2026-09-23 | 2026-09-29 | 6 | 6 | **4** |
| 2026-09-30 | 2026-10-06 | 6 | 6 | **3** |
| 2026-10-01 | 2026-10-06 | 5 | 5 | **2** |

`dte` equals the calendar difference on all 8 runs checked, while trading days differ.
**The writer converts via `trading_calendar` (`is_open`) and must not feed `dte` to
`boost()` directly.** The DDL carries this as a column COMMENT so the trap travels with
the schema.

### 3.6 `is_trading_session` — the frozen-day discriminator
`is_trading_session = (count(distinct spot) in market_spot_snapshots for that symbol, on
that IST trading date, up to ts) > 1`.

Columns bound: `market_spot_snapshots.spot`, `.ts`, `.symbol` — all present.

**Why a count of rows or of distinct `ts` cannot substitute:** 2026-10-02 carried ~143k
chain rows across **83 distinct ts** spanning 08:50–15:40 and passes every density check,
with `distinct_spot = 1` for both symbols (NIFTY 22421.95, SENSEX 71909.7, `spot_range
0.00`). Control 2026-10-01: **78** distinct spot values. See **TD-S89-NEW-1**.

**The row is still WRITTEN when false.** The default history read filters
`is_trading_session = true`. Writing-and-flagging keeps the frozen cycle inspectable;
dropping it would make the gap indistinguishable from a writer outage.

### 3.7 `pin_state`
`pin_state ∈ {NO PIN, SHIFTING, STABLE, LOCKED}`, derived from `held_for_cycles`,
`runnerup_share_ratio` and `conc_top1_share`, with thresholds **read from
`merdian_parameters`** (ADR-016) by dot-key:

```
pin_state.stable_held_for.NIFTY
pin_state.locked_held_for.NIFTY
pin_state.locked_ratio_max.NIFTY
pin_state.nopin_conc_floor.NIFTY      (and the SENSEX quartet)
```

**`merdian_parameters` is currently EMPTY — measured: 0 total rows, 0 live rows, 0
categories.** The table exists and is readable by `merdian_ro`; it has never been seeded.
Two consequences, both load-bearing:

1. **Seeding the eight keys is part of the writer deliverable**, not a precondition
   someone else has met. Values are **PROVISIONAL and owe D-6 calibration**.
2. **A missing key leaves `pin_state` NULL with the reason in `pin_state_reason`.** The
   writer must **never** substitute a default and must never hardcode a threshold in the
   view or the writer. Absence is not a verdict (ADR-020); a silent default here would be
   exactly the two-modules-two-contracts failure that ADR-020 was written for.

### 3.8 `held_for_cycles`
Read the prior row for `(symbol, expiry_date)`; if its `pin_leader_strike` equals this
row's, `held_for_cycles = prior + 1`, else `1`. **Count only `is_trading_session = true`
rows**, so a holiday or frozen gap does not increment it.

### 3.9 `repriced_flip` (L3) — clock-matched or NULL
`v_gex_repriced_flip` **has no `run_id` and no `dte`**, names its expiry **`front_expiry`**,
and carries `t_days` instead. So it **cannot be joined on the standard
`(run_id, symbol, expiry_date)` key**.

**Measured hazard:** its latest row on 2026-10-03 was
`ts = 2026-10-02 10:10:04+00`, `spot = 22421.95` — the **frozen 10-02 book** — while every
other relation sat on the **2026-10-01 09:50:07+00** γ run: a **~1,460-minute** cross-clock
gap onto a frozen book.

**Rule: the writer CLOCK-MATCHES L3 to the γ run (same trading date / ts). If it cannot
match, it stores `repriced_flip_level = NULL`, `repriced_flip_source = 'UNMATCHED_NULL'`,
and the `ts` the view actually returned in `repriced_flip_ts`. It NEVER takes the view's
stale latest.** A `CHECK` in the DDL enforces that `UNMATCHED_NULL` cannot carry a level,
so a writer bug fails loudly rather than storing an off-clock number.

---

## 4. RETENTION

**Keep indefinitely.** The table is **explicitly NOT a target of `pg_cron` jobid 19**
(`cleanup_gamma_engine_daily`, confirmed `active = false`, last run 2026-09-08 12:30 UTC).
This is stated in **three** places by design: the DDL `COMMENT ON TABLE`, this spec, and
the registers. A future retention job must name this table explicitly to touch it; a
blanket gamma-chain cleanup must not.

**Standing tripwire (S89):** assert `jobid 19 active = false` at each SQL-editor doc-close.
`merdian_ro` cannot read `cron.job`, so that assertion belongs to the editor under
postgres and cannot be delegated to `roq.sh`.

---

## 5. ACCEPTANCE TEST

| # | Test | Pass condition | What makes it fail |
|---|---|---|---|
| **(a)** | Every bound source column exists in the live schema | an `information_schema` query returns **all** bound `(table, column)` pairs | a renamed or dropped source column; the test names pairs, so a missing one is identified, not merely counted |
| **(b)** | Dry-run writer coverage | per-symbol **distinct-`ts` coverage = 100 %** of γ cycles in the window (**TD-S54-NEW-1** guard) | a writer that skips cycles; coverage is a ratio against the γ clock's own distinct `ts`, not a row count |
| **(c)** | Frozen cycle handling | a frozen cycle (or the stored **2026-10-02** rows) lands `is_trading_session = false` **and** is excluded by the default read | a session gate keyed on row count or distinct `ts`, both of which 10-02 passes |
| **(d)** | `held_for_cycles` increments and resets | increments across a real stable-leader run and resets on the leader change | an off-by-one, or incrementing across a session gap |

**Test (d) is rebound, because the run it was specified against does not exist.**
The ruling named "the 28–29 Sep NIFTY stable-leader run". Measured: **2026-09-28 has four
distinct rank-1 leaders** (22800 ×49, 23000 ×31, 22900 ×1, 23100 ×1) and they *interleave*
— 22800 spans 09:20–14:15 while 23000 spans 08:40–15:40 — so there is no stable run there
to increment across. Longest **consecutive** same-leader streaks in the window:

| date | leader | consecutive cycles | window (IST) |
|---|---|---|---|
| **2026-09-30** | **23000** | **73** | 08:50 → 14:50 |
| 2026-09-25 | 23000 | 64 | 10:10 → 15:40 |
| 2026-09-29 | 22600 | 48 | 11:15 → 15:10 |
| 2026-10-01 | 22700 | 25 | 11:15 → 13:15 |

**Bind test (d) to 2026-09-30, leader 23000, 73 consecutive cycles**, asserting
`held_for_cycles` runs 1 → 73 over 08:50 → 14:50 and **resets to 1** on the first cycle
after 14:50. The reset cycle's new leader must be read from the data at test time, not
carried from this document.

---

## 6. What this spec deliberately does not do

- **No RLS enable.** Enabling RLS with zero policies makes a table unreadable by every
  non-bypass role including `anon` (TD-S81-NEW-16 family). If RLS is wanted, the policy
  ships in the same statement as the enable.
- **No backfill.** The window before the first write is unrecoverable except through
  **ENH-134**; this table accumulates forward only. That is the whole reason the two are
  complements rather than alternatives (**D-3**).
- **No writer.** The writer is a separate deliverable. Nothing in the DDL implies it
  exists.
- **No `anon` grant.** The migration carries a live `REVOKE ALL … FROM anon` because
  Supabase DEFAULT PRIVILEGES were observed to hand `ALL` on newly created objects to
  `anon` (S39 → S81, `CASE-2026-09-22-anon-privilege-exposure`). The REVOKE is the
  statement that prevents the default, not a precaution on top of it.

---

*Bound pre-DDL spec, Session 89, 2026-10-03. Read-only introspection via `bin/roq.sh`;
no DDL applied, no writer written, no engine change. The schema ADR is the next artefact
(TD-S80-NEW-7 precedent) and this file is its input.*
