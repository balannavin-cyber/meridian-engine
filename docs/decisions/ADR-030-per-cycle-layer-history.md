# ADR-030 — Per-cycle layer history: `gex_cycle_history`

| Field | Value |
|---|---|
| Status | **PROPOSED** (Session 89, 2026-10-03/04) — operator accepts at this doc-close |
| Date | 2026-10-04 |
| Session | S89 |
| Supersedes | nothing |
| Superseded by | nothing |
| Parent | **ADR-025** — D-3 (2026-10-03) pulled ENH-133 into parity scope ahead of §H phase 2 |
| Register entry | **ENH-133** |
| Bound schema spec | [`../research/s89_rulings/ENH-133_schema_spec_S89.md`](../research/s89_rulings/ENH-133_schema_spec_S89.md) |
| DDL | [`../../sql/2026-10-03_s89_gex_cycle_history.sql`](../../sql/2026-10-03_s89_gex_cycle_history.sql) — committed, applies Mon 2026-10-05 ≥ 16:00 IST |

---

## Why this ADR is short

**The schema is not in this file, and that is deliberate.** Columns, types, derived-field
logic, the three-state session gate, `pin_state` carry-forward, the honest naming of
`conc_top1_share`, the acceptance test and the measured `run_id` semantics are all bound in
`ENH-133_schema_spec_S89.md` (374 lines) and in the DDL's own `COMMENT ON TABLE`. **A schema
restated in a second place is a schema that can drift out of agreement with itself** — the
same argument ADR-029 D15 makes about its mapping file, and the same reason `rulings_s89.md`
is never restated into an ADR.

This ADR spends its words on the two decisions the spec *assumes* rather than argues.

---

## D1 — Adopt a per-cycle layer-history PERSISTENCE pattern

**Decision.** MERIDIAN adopts a persisted per-cycle history for parity layer scalars: **one row
per `(symbol, expiry_date, ts)`** at the γ cadence, both expiry legs, `run_id` stored and not
keyed. `gex_cycle_history` is the first instance.

**Why it is an architectural decision and not a table.** **Eleven of the twelve parity views
carry no history** (S88, `MERDIAN_System_Map.md` §1963-1976): each is scoped to the latest run
or the latest chain `ts` by ADR-021, which is correct for a board and leaves the layers unable
to answer any question with a *time* in it. That is not a defect in any one view — it is a
property of the whole read layer, and closing it changes what the layer family *is*. The
substrate this unlocks is named rather than implied: **`pin_state` "held for"**, **HHI
history and its percentile** (the D-5c conviction stage 2), **intraday net-GEX**, and **flip
crossings over a session**. None of those is computable from a latest-only view at any cost.

**The key is a timestamp, not a cycle ordinal.** A future 1-minute pass writes into the same
table unchanged. An ordinal would have had to be renumbered, and a renumbered key is a silent
rewrite of history.

**ENH-133 and ENH-134 are COMPLEMENTS, not alternatives** (D-3): 133 accumulates forward, 134's
as-of functions address the already-stored window. Adopting one does not retire the other.

**Write-and-flag, never write-nothing.** A row is written even when the session gate is false,
and readers filter on it. **2026-10-02 is why**: the ingest ran 83 cycles on Gandhi Jayanti and
recorded the previous session's last spot every time, producing rows that **pass a row count
and a distinct-`ts` count** and fail only on `distinct_spot` (TD-S89-NEW-1). A gate that
suppressed the write would have left a hole indistinguishable from an outage.

**Rejected — recompute history on read from `gamma_metrics` + `gex_strike_snapshots`.** Five of
the scalars the spec names (runner-up strike, runner-up margin, gamma at pin, top-5 share,
per-rank shares) **exist in no relation** and are writer-derived; a read-time recomputation
would have to re-implement the writer and would drift from it. Worse, `pin_state` and
`held_for_cycles` are **carry-forward** quantities — recomputing them on read makes their value
depend on the read's window rather than on what happened.

**Rejected — store only the front leg.** The grain carries both W1 and W2 because L78-3
requires W2 to compute as normal on expiry day. Front-only would have made expiry days, the
cohort most of this history is for, the one case it cannot describe.

## D2 — Retention: outside `pg_cron` jobid 19, keep indefinitely

**Decision.** `gex_cycle_history` is **explicitly NOT a target of `pg_cron` jobid 19**
(`cleanup_gamma_engine_daily`, measured `active = false`, last run 2026-09-08 12:30 UTC), and
its retention window is **keep indefinitely**. Taken from the bound spec §4 — **this ADR does
not set a new value, it ratifies the spec's**. A future retention job must **name this table
explicitly** to touch it; a blanket gamma-chain cleanup must not reach it.

**Why indefinite is the right default here and not laziness.** The spec §6 records that **the
window before the first write is unrecoverable except through backfill**, and there is no
backfill. Every row is therefore the only copy of a moment that cannot be reconstructed. A
thinning job trades away exactly the thing the table exists to accumulate, and `jobid 19`
already demonstrated the failure mode it would have: it thins OCS to one 10:00 UTC row per day
after 14 days, which is why L13's historical leg is capped at 14 days by construction.

**This is stated in three places by design** — the DDL `COMMENT ON TABLE`, the spec, and the
registers — because a retention rule held in one place is a retention rule a future job will
not see.

**Standing tripwire, carried from the spec:** assert `jobid 19 active = false` at each
SQL-editor doc-close. `merdian_ro` **cannot read `cron.job`**, so that assertion belongs to the
editor under `postgres` and **cannot be delegated to `bin/roq.sh`** — stated so the check is
not later written against a role that cannot run it.

**Rejected — a bounded window (e.g. 365 days) set now.** No consumer has yet asked a question
with a horizon, so any number chosen today would be a guess with a deletion attached. Indefinite
is reversible; deleted rows are not.

---

## Consequences

- **The DDL applies Monday 2026-10-05 ≥ 16:00 IST against this ADR**, together with the ENH-98
  L7/L8 views. It is committed under `sql/` and was authored before this ADR existed.
- **TD-S80-NEW-7's risk is already discharged for this object.** That TD exists because
  `gex_pin_maxpain_history` shipped as a new table with no schema ADR and no committed DDL —
  *"one `DROP` from unrecoverable"*. Here the DDL is committed and the spec is bound **before**
  the apply, so the precedent is satisfied in the order it intends. **TD-S80-NEW-7 itself stays
  open** — it is about `gex_pin_maxpain_history`, which this ADR does not touch.
- **ENH-133's Priority Tier remains OPERATOR-TO-ASSIGN.** Accepting this ADR settles the
  pattern and the retention; it does not assign a tier, and nothing here should be read as
  doing so.
- **No parity disposition changes.** ENH-133 is in parity scope by D-3; it is not one of the
  fourteen layers and does not move the BUILT count.

## Governance language

> **Per-cycle layer history is persisted, not recomputed, and it is not retention-managed by
> the gamma-chain cleanup.** One row per `(symbol, expiry_date, ts)`, both expiry legs,
> `run_id` stored not keyed, written **even when the session gate is false** and filtered on
> read. The key is a timestamp so a finer cadence needs no renumbering. `gex_cycle_history`
> sits **outside `pg_cron` jobid 19** and keeps rows **indefinitely**; a future retention job
> must name it explicitly. The schema itself lives in `ENH-133_schema_spec_S89.md` and is
> never restated. (ADR-030, S89.)

## Cross-references

ADR-025 (D-3 — ENH-133 into parity scope) · ADR-021 (latest-run scoping, which is what makes
the existing views latest-only) · ADR-020 (absence is not a verdict — why a missing
`pin_state` key is NULL with a reason, never a default) · TD-S80-NEW-7 · TD-S89-NEW-1 ·
TD-S89-NEW-2 (the ADR-016 write path absent, which is why the `pin_state.*` keys are seeded by
a dated migration rather than a CLI) · ENH-133 · ENH-134 · `rulings_s89.md` (D-3, ENH-133 scope).

---

**S90 annotation (2026-10-05, ruling S90-B, `docs/research/s90_agentic/rulings_s90.md`).** D1's "both expiry legs" is not achievable on the current source: `gamma_metrics` is `UNIQUE (symbol, ts)` and `UNIQUE (run_id)`, so it holds one expiry per symbol per cycle, and `gex_cycle_history` reads its legs from it. **Front leg (W1) only, by ruling, until a W2 compute path is separately ruled.** The PK `(symbol, expiry_date, ts)` is unchanged and admits W2 later without a migration. D2 is unaffected. **Applied 2026-10-05 ~17:05 IST; writer wired into `run_merdian_shadow_runner_aws.py` after gamma + volatility (`5ac0ed0`, off switch `ENH133_WRITER_ENABLED`, ruling S90-F); EOD reconciler `55 10 * * 1-5` (`be36d48`). First live cycle 2026-10-06 09:15 IST.**
