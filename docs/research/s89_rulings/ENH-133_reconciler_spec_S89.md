# ENH-133 session-gate reconciler — design spec (S89, 2026-10-03)

> **DESIGN ONLY. No script was written, no DB write was made, no cron line was added, no
> engine file was touched.** Authored in `~/meridian-cc`; the reconciler is production
> engine code and deploys via the engine path (push + `git pull --ff-only` after 16:00 IST,
> from the operator's own terminal).
>
> Created by the **§6 ruling of 2026-10-03 — Option A**: a three-state session gate whose
> write-time value is provisional, finalised once a date is complete.
>
> Companions: **`ENH-133_schema_spec_S89.md`** (columns), **`ENH-133_writer_spec_S89.md`**
> (the per-cycle writer), `sql/2026-10-03_s89_gex_cycle_history.sql` (authored-not-applied
> DDL), `sql/2026-10-03_s89_seed_pin_state_params.sql` (authored-not-applied param seed).

---

## 1. WHY THIS COMPONENT EXISTS

The writer runs **inside** a cycle and can only see the tape as it stands at that instant.
Measured: the γ clock starts **08:30–08:40 IST** while the first `market_spot_snapshots`
tick lands **~09:11:03** every day, so **6–8 of each day's 74–83 cycles** are written with
zero ticks and are stamped **`PRE_TICK`**.

`PRE_TICK` is an honest statement of what the writer saw. It is not an answer to "did this
date trade?" — **that question can only be answered once the date is complete**, and that
is this component's entire job.

Two things therefore become final here, not at write time:

1. **`session_gate_state`** — every `PRE_TICK` row resolves to `OPEN` or `FROZEN`.
2. **`held_for_cycles` and `pin_state`** — recomputed over the *finalised* `OPEN` set,
   because a streak that began before 09:11 cannot be counted correctly at write time.

New script: **`reconcile_gex_cycle_history_session_local.py`**, with its own
`ExecutionLog` row and its own exit code. **It is a separate engine deliverable from the
writer** — the two have different schedules, different failure modes and different write
contracts.

---

## 2. SCOPE AND SAFETY

### 2.1 Which dates it touches

For each `symbol`, each **COMPLETED IST trading date** that is not yet finalised.

**It never touches today's in-progress date.** The definition of "completed" is explicit,
because getting it wrong would freeze a live day:

```
eligible_date  <  current IST date
```

A date equal to the current IST date is skipped unconditionally — **not** "skipped unless
it looks finished". There is no heuristic here: a partial tape is indistinguishable from
a frozen one, which is the whole defect this component exists to resolve.

### 2.2 Which dates are "not yet finalised"

A date is **unfinalised** if any of its rows carries `session_gate_state = 'PRE_TICK'`.
Once no `PRE_TICK` row remains for `(symbol, date)`, the date is final.

**This makes re-running a finalised date a no-op by construction**, rather than by a
separate guard that could disagree with the work (§5).

### 2.3 What it does NOT rewrite

- **`session_gate_ticks`** — it records what the *writer* saw. Overwriting it with an
  end-of-day count would destroy the only evidence that a `PRE_TICK` row was a genuine
  tick-absence rather than a failed read.
- **Every layer scalar** — `pin_leader_strike`, `gamma_at_pin`, `runnerup_share_ratio`,
  `top5_share`, `conc_*`, `max_pain_strike`, the walls, `is_fresh`, `snapshot_age_min`,
  `chain_ts`, `atm_iv`, `repriced_flip_*`. These were measured on their own clock and are
  not re-derivable later. **The reconciler changes verdicts, never measurements.**
- **`writer` / `writer_version`** — provenance of the original write. The reconciler
  stamps its own identity separately (§6).

---

## 3. THE TWO PASSES

### 3.1 Pass 1 — finalise `session_gate_state`

Per `(symbol, date)`:

```
day_distinct_spot = count of distinct market_spot_snapshots.spot
                    for that symbol over the FULL IST date

if day_distinct_spot > 1:   # the day TRADED
    every row of that (symbol, date)  ->  session_gate_state = 'OPEN'
else:                       # holiday / frozen book
    every row of that (symbol, date)  ->  session_gate_state = 'FROZEN'
```

**It is a whole-date verdict, applied uniformly.** A traded date has no frozen cycles and
a frozen date has no open ones; the mid-day distinction the writer had to make disappears
once the date is known. 2026-10-02 (`distinct_spot = 1` for both symbols, NIFTY pinned at
22421.95, SENSEX at 71909.7 — **TD-S89-NEW-1**) becomes uniformly `FROZEN`. 2026-09-30
(`distinct_spot > 1`) becomes uniformly `OPEN`, which is what promotes its **08:50–09:11**
cycles and makes acceptance A(d) satisfiable.

**`trading_calendar` is deliberately NOT consulted.** 2026-10-02 is **absent** from it —
the Rule 18 fail-open shape — so a calendar-assisted verdict would read that date as open.
The tape is the evidence; the calendar is not. (`trading_calendar` *is* still used for the
`conviction` trading-day conversion, where it is the only available source — writer spec
§5.1.)

### 3.2 Pass 2 — recompute `held_for_cycles`, then `pin_state`

Over the finalised `OPEN` set for `(symbol, expiry_date)`, ordered by `ts`:

```
carry = held_for_cycles of the LAST OPEN row of the PRIOR trading date
        for this (symbol, expiry_date), and that row's pin_leader_strike
for each OPEN row of this date, in ts order:
    if pin_leader_strike == previous OPEN row's pin_leader_strike:  held_for = prev + 1
    else:                                                          held_for = 1
```

**THE CARRY-FORWARD RULE, stated explicitly because it is a recorded choice and is
overridable:**

> **A leader that persists across an overnight or holiday gap CONTINUES its streak.** The
> streak is carried from the last `OPEN` row of the prior trading date, not reset at the
> date boundary. A **leader change resets to 1**. A **`FROZEN` (holiday) date contributes
> nothing to the count and does not itself reset the streak** — the streak bridges it.

The alternative — reset at each date boundary — is defensible and was **not** chosen: a
pin that holds the same strike through a weekend is the phenomenon `held_for_cycles` is
meant to detect, and resetting would make a multi-day pin indistinguishable from a
first-cycle one. **Nothing in the data settles this; it is a design decision**, which is
why it is written as a rule rather than buried in the code.

Then `pin_state` is re-derived from the **final** `held_for_cycles`, the row's own
`runnerup_share_ratio` and `conc_top1_share`, and the `merdian_parameters` thresholds —
**the same state machine and the same missing-key behaviour as the writer** (writer spec
§7):

```
if   conc_top1_share < pin_state.nopin_conc_floor.<sym>      -> 'NO PIN'
elif held_for_cycles < pin_state.stable_held_for.<sym>       -> 'SHIFTING'
elif held_for_cycles >= pin_state.locked_held_for.<sym>
     and runnerup_share_ratio <= pin_state.locked_ratio_max.<sym>  -> 'LOCKED'
else                                                         -> 'STABLE'
```

Thresholds read via `core.parameters.get_parameter_num(key)` with **no default**. A
missing key leaves `pin_state = NULL` and `pin_state_reason = "missing parameter key:
<key>"` — **never a substituted default** (ADR-020: absence is not a verdict). Note
`merdian_parameters` currently measures **0 rows** and the ADR-016 write path does not
exist — **TD-S89-NEW-2**.

**The state machine lives in ONE place — RULED 2026-10-03: `core/pin_state.py`.** The
writer and the reconciler both **import** it; **neither carries its own copy.** Two
implementations of one rule is the shape ADR-020 was written for, and a parity claim
between two copies is asserted only by a test that compares them, never by a comment
(Rule 0 clause 4). With one home the comparison question does not arise. The missing-key
behaviour above belongs to that helper, not to either caller. Mirrored at writer spec §7.0.

### 3.3 `FROZEN` rows

`held_for_cycles` and `pin_state` on a `FROZEN` row are **set to NULL** with
`pin_state_reason = "frozen date"`. They are not computed and not carried: a pin state
derived from a book that never moved would be a measurement of the previous session's last
print, which is exactly what TD-S89-NEW-1 records.

---

## 4. SCHEDULE — proposed, not added

**Proposed: 16:25 IST, Mon–Fri — `55 10 * * 1-5` (host TZ `Etc/UTC`).**

Derivation, so the number is not a round guess:

| Constraint | Measured |
|---|---|
| Last in-session spot tick | **15:29 IST** (the `*/1 03..09` feed ends 09:59 UTC) |
| Last `market_spot_snapshots` row of the day | **16:00:04 IST** — the post-close print |
| `build_market_spot_session_markers.py` | **16:10 IST** (`40 10 * * 1-5`) |
| Last γ cycle | **15:20–15:40 IST** |

The tape is complete at **16:00:04**, so anything after that is sufficient; 16:25 sits
**15 minutes clear** of the 16:00 print and **after** the 16:10 markers job, so the two
EOD writers do not contend. It is also the same side of midnight as the date it
reconciles, which keeps "yesterday" unambiguous.

**No cron line is added in this pass.** Scheduling is an engine-path change and belongs
with the deploy.

**A note on what the schedule does NOT need to guarantee.** Because §2.1 refuses any date
equal to the current IST date, a late or missed run is harmless — the date is simply
reconciled on the next run. **The reconciler is catch-up by design, not
schedule-critical**: it iterates every unfinalised completed date, so a week of missed runs
resolves in one pass. That is deliberate, and it is why the schedule can be proposed rather
than defended.

---

## 5. IDEMPOTENCY

Re-running a finalised date is a **no-op by construction**, not by a flag: §2.2 defines
"unfinalised" as *carries at least one `PRE_TICK` row*, and pass 1 removes every
`PRE_TICK` for that date. So a second run finds no eligible dates and writes nothing.

**One consequence worth stating, since it is the obvious objection.** This means the
reconciler will **not** re-derive `held_for_cycles` for an already-finalised date, even if
the carry-forward rule later changes or a threshold is recalibrated. That is correct for
routine operation and wrong for a rule change, so a **`--recompute <date>` escape hatch**
is specified: it re-runs pass 2 only, over dates given explicitly, and **never** re-runs
pass 1 (a finalised `OPEN`/`FROZEN` verdict is evidence about the tape and must not be
recomputed from a tape that has since been archived). Default behaviour without the flag
is untouched.

---

## 6. GUARDS AND WRITE CONTRACT

| # | Guard | Pass condition | What makes it fail |
|---|---|---|---|
| **R1** | Write contract | `expected_writes` = **exact** count of rows the reconciler will update, computed **before** the first update from the eligible-date row count | Rule 0 clause 1 — a floor of 1 passes on 1 row and on 6,000 |
| **R2** | No `PRE_TICK` survives | after a run, **zero** rows with `session_gate_state = 'PRE_TICK'` on any date `< current IST date` | a date skipped silently; the count is the check |
| **R3** | Today untouched | **zero** rows modified whose IST date = current IST date | an off-by-one in the date comparison, which would freeze a live day |
| **R4** | Measurements unchanged | for every reconciled row, the layer scalars (§2.3) are **byte-identical** before and after | a reconciler that recomputes a measurement instead of a verdict |
| **R5** | Coverage | per `(symbol, date)` reconciled, the count of rows stamped equals the count of rows that date held before the run | a partial stamp leaving a date half-`OPEN` |
| **R6** | Streak continuity | within a reconciled date, `held_for_cycles` over the `OPEN` set is **strictly +1 per cycle while `pin_leader_strike` is unchanged**, and exactly `1` on each change | an off-by-one; a reset where the leader did not change |

**R4 is the one that distinguishes this component from a rewriter.** The reconciler's
licence is narrow — three columns (`session_gate_state`, `held_for_cycles`, `pin_state`,
plus `pin_state_reason`) — and R4 is what makes "narrow" testable rather than asserted.

### 6.1 Provenance

The reconciler stamps its own identity without destroying the writer's. **RULED
2026-10-03: `reconciled_at timestamptz` and `reconciler_version text` are in the
still-unapplied DDL**, and the reconciler **never** overwrites `writer` /
`writer_version` — the two provenances are separate facts about the same row.

**`reconciled_at IS NULL` is the canonical unreconciled signal.** The absence of a
`PRE_TICK` row is **not**: a date whose cycles all began after 09:11 is written with no
`PRE_TICK` at all and would be indistinguishable from a finalised date. R2 (§6) tests that
no `PRE_TICK` survives; `reconciled_at` is what tells a reader whether pass 2 ran.

---

## 7. ACCEPTANCE

**A(c) — frozen date.** After reconciliation, every row of **2026-10-02** carries
`session_gate_state = 'FROZEN'`, is excluded by the default read, and **no row of a traded
date is left `PRE_TICK`**.

**A(d) — the streak, rebound to this component.** After reconciliation,
`held_for_cycles` runs **1 → 73** across **2026-09-30, leader 23000, 08:50 → 14:50 IST**,
and **resets to 1** on the first post-14:50 leader change.

**A(d) is a reconciler test and cannot pass at write time** — the streak begins at
**08:50**, before 09-30's first tick at **09:11:04**, so at write time its opening cycles
are `PRE_TICK`. 09-30 traded, so pass 1 promotes them and pass 2 makes the run continuous.
The assertion moved to the component that can satisfy it; **A(d) was not loosened.**

**A(e) — carry-forward, NEW with this component.** Construct or identify a leg whose
`pin_leader_strike` is unchanged between the last `OPEN` cycle of one date and the first
`OPEN` cycle of the next; assert `held_for_cycles` **continues** rather than resetting to
1. Without this, §3.2's carry-forward rule is a comment and not a behaviour — and the
longest measured streaks (09-30 / 23000 / 73, 09-25 / 23000 / 64) are **same-leader on
adjacent dates**, so the rule is live on real data and not hypothetical.

**The expected value for A(e) is computed from the data at test time, never carried from
this document** — an expected value obtained by running the thing is not an assertion
(Rule 0 clause 3).

---

## 8. OUT OF SCOPE

- **No script written, no cron line added, no DDL applied** in this pass.
- **No engine file touched.** Three engine-path changes now stand queued for the deploy:
  `write_gex_cycle_history_local.py`, the orchestrator step, and
  `reconcile_gex_cycle_history_session_local.py`.
- **`merdian_calibrate.py`** — ENH-83 scope, **TD-S89-NEW-2**.
- **No phase-2 consumer.** Nothing reads this table yet.

**The two open items in this spec were RULED 2026-10-03 and are now folded in:** the
`reconciled_at` / `reconciler_version` columns are in the unapplied DDL (§6.1), and the
pin-state machine has one home at `core/pin_state.py`, imported by both callers (§3.2).
Both were taken while they were still cheap — the DDL was unapplied and no code existed;
each would have become expensive the moment there were two copies of the state machine or
a table of rows whose reconciliation status could not be read.

---

*Reconciler design spec, Session 89, 2026-10-03. Created by the §6 Option-A ruling. The
carry-forward rule in §3.2 is a recorded, overridable design choice, not a measurement.*
