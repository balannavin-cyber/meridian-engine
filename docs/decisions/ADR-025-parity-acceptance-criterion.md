# ADR-025 — Parity acceptance criterion: a layer is achieved when it renders, and the programme is complete when every layer has a disposition

| Field | Value |
|---|---|
| Status | **Accepted** |
| Date decided | 2026-09-21 |
| Date documented | 2026-09-21 (Session 80) |
| Session | Session 80 |
| Supersedes | Nothing. First acceptance ruling for the Hedgewall parity programme. |
| Related | **TD-S79-NEW-22 (D0)** — the entry that filed this decision · `MERDIAN_Hedgewall_Parity_Spec.md` (S78) · ENH-120 / ENH-121 / ENH-122 (S79) · ENH-123 / ENH-124 (S80, off-spec) · TD-S79-NEW-15…-21 (L3 measured and declined) · ADR-021 (latest-run scoping) · ADR-017 (console design) · ADR-009 (pre-registration) · ADR-016 (parameter calibration) · TD-S79-NEW-3 (`sql/` as a superseded rebuild source) · TD-080 (Dhan 429, S1-recurring) |
| Amended | **Amendment A**, 2026-09-22 (Session 80) — what shipped against what was ruled; session self-corrections; D2 clause 4 registration status. Body text above is unchanged. · **Amendment B**, 2026-09-23 (Session 81) — **REVERSES part of Consequences**: rendering is deferred until every layer carries a disposition, so D2 clause 3 is suspended and BUILT stays 2 of 14 **by decision**. Also rules the deferral's scope (it does not block repairs to shipped surfaces), corrects the effort figure to **days, not weeks**, records the S81 dispositions, and corrects two A1 statements. D1–D5 are otherwise unchanged. |
| Rule 10 class | **Programme scope and acceptance.** Governs a multi-session build. Mandatory ADR per Doc Protocol v4 Rule 10 and per TD-S79-NEW-22's own *Proper fix* clause. |

---

## Context

`MERDIAN_Hedgewall_Parity_Spec.md` resolves **fourteen layers** to sources, computations and horizons, and orders them by value-per-hour. It is a source-resolution document. It never states what "parity achieved" means.

S79 built three layers and measured a fourth (L3) and declined it. That was the first time a layer was rejected rather than deferred, and it exposed the gap: declining a layer reads as incompleteness when no criterion exists, so the programme terminates only when the spec is exhausted. TD-S79-NEW-22 filed this as **D0** and ruled that the fix is an ADR, drafted **before the next layer is built**.

S80 made the gap concrete in three ways:

1. **Two more layers were built that are not among the fourteen** — ENH-123 (`v_gex_max_pain`) and ENH-124 (`v_gex_pin_maxpain`). Max pain appears nowhere in the spec's fourteen layers or its ten-row build order. Without a criterion, adding a layer and reporting progress is unfalsifiable.
2. **Three spec claims were refuted by measurement** (§ *Spec corrections* below), so the build order can no longer be trusted as written.
3. **Five views now compute and none renders.** S79 deliberately deferred presentation "until the full board is understood." That deferral has run to five layers and no operator surface has changed since ENH-81 in S37.

## Decision

### D1 — Scope

**Parity is achieved when every one of the fourteen layers carries a recorded disposition, not when all fourteen are built.**

Dispositions are: **BUILT · PENDING · BLOCKED-ON-DECISION · BLOCKED-ON-DATA · DECLINED-ON-EVIDENCE**.

This makes stopping early a *result*. Building eight layers, measuring the rest and declining them is a complete programme, which is the outcome L3 already demonstrated is reachable.

### D2 — Evidence bar

**A layer is BUILT only when all four of the following hold:**

1. **It computes** against the live database and its output has been read.
2. **It is run-scoped and EXPLAIN-verified** per ADR-021.
3. **It is visible on at least one operator surface** — Marketview or the Pine overlay.
4. **It has an ENH register entry and its DDL is committed under `sql/`.**

Each clause is earned from a specific failure in this system, not chosen for symmetry:

- Clause 2 exists because an unscoped view crossed the PostgREST 8 s ceiling at 1.06M rows and silently emptied the Pine overlay for weeks — the failure ADR-021 was written for.
- Clause 3 exists because the spec's own §3 excludes "Marketview iteration cycles" from its effort numbers, which is precisely how five computed-but-invisible views accumulated. A layer that nobody can see has delivered nothing.
- Clause 4 exists because TD-S79-NEW-3 records `sql/` as a superseded rebuild source: a view living only in the live database is one `DROP` from unrecoverable, and cannot be rebuilt from the repo.

**Agreement with the reference is not required for BUILT.** It is a separate, optional validation, applied per layer only where the reference publishes a comparable number.

### D3 — Reference

**Hedgewall (hedgewall.in) binds.** Deviation requires a stated reason recorded in the layer's ENH entry. optionsflow.in is a second observation, used where the two disagree, and never as the binding target without such a note.

### D4 — Declining

**DECLINED-ON-EVIDENCE is a completed disposition, not a hole.** L3 carries seven register entries (TD-S79-NEW-15…-21) — more work than most built layers — and counts toward completion.

It stays **distinct** from BLOCKED-ON-DATA and BLOCKED-ON-DECISION. A judgement that a layer should not be displayed is not the same as a missing input or an unmade decision, and collapsing them would hide which ones are fixable.

**BLOCKED-ON-DATA is retained with zero members among the fourteen.** §2.5 names genuine walls — HIRO-class order flow ("no layer in this document closes it") and DIX-class dark-pool positioning, for which India has no equivalent feed — and the category must exist for them.

### D5 — Off-spec layers

**A layer outside the fourteen does not count toward parity.** It files to §2.5 as an extension and is tracked separately.

ENH-123 (`v_gex_max_pain`) and ENH-124 (`v_gex_pin_maxpain`) file as **L19** and are **parked** — applied, unrendered, not counted.

Parking is not the same as leaving them unregistered. Clause 4 of D2 applies to every production object regardless of parity status (§ *Consequences*).

---

## Dispositions as at S80

| # | layer | disposition | note |
|---|---|---|---|
| L1 | Gamma density per strike | **BUILT** | ENH-80 S37; renders as the Marketview GEX-by-strike histogram |
| L2 | Pin zone | **BUILT** | ENH-81 S37; renders in Marketview and the Pine overlay |
| L3 | Flip level | **BLOCKED-ON-DECISION** | Current construct unsound and must not be displayed. Rebuild is specced but gated on three open decisions — TD-S79-NEW-17 (three constructions sharing a column), -20 (replay pinned to the legacy branch), -21 (unswept hardcoded floor). TD-S79-NEW-18 is UNRESOLVED. |
| L4 | Call wall | **PENDING** | Computes (ENH-120). Fails D2 clauses 3 and 4. |
| L5 | Put wall | **PENDING** | Same view as L4. |
| L6 | Net-vs-absolute GEX | **PENDING** | Net leg renders on the Marketview REGIME card; the **absolute** leg (ENH-121) computes and does not render. |
| L7 | Vanna | **BLOCKED-ON-DECISION** | ENH-98 deferral, "Phase 2 deployment plan commitment". Operator decision, not a data limit. Horizon 61/62 days. |
| L8 | Charm | **BLOCKED-ON-DECISION** | As L7; ships with it. |
| L9 | IV term structure | **PENDING** | Requires an ingest change (§ below). Spec's live source claim refuted. |
| L10 | IV surface | **PENDING** | 61/62 days in two blocks; must render the 2026-06-04 → 08-23 hole as absence. |
| L11 | Five-axis radar | **PENDING** | Composition of five layers, three unbuilt. Last by construction. |
| L12 | Pin conviction | **PENDING** | HHI leg computes (ENH-122); ranked-candidates leg not built. Fails clauses 3 and 4. |
| L13 | OI rotation | **PENDING** | Live straightforward; historical capped at 14 days by jobid 19. |
| L14 | 30-session gamma river | **PENDING** | 299 days available. Watch the Cr-vs-unscaled unit convention — TD-S30-CANDIDATE-1 cost seven sessions to that class. |

**BUILT: 2 of 14.** Not three, and not five.

---

## Spec corrections measured in S80

Recorded here because the build order can no longer be read as written. All three are the same reflex — reasoning from a register or a row count when the source was available (ADR-024 §A9).

1. **L9's live source is false.** `option_chain_snapshots` holds **one expiry per cycle** across all 2,923 cycles ever written (`min = avg = max = 1`, `cycles_multi_expiry = 0`). The spec's *"full expiry ladder per cycle"* was never true. `ingest_option_chain_local.py:365` selects `future_expiries[0]` from the full list the vendor returns at line 327 and discards the rest, with no comment stating why.
2. **L4's gamma-weighted argmax was rejected**, not deferred. S79 measured it collapsing to ATM at −0.09σ / +0.19σ — it finds the money, not the wall. The spec still says both variants are "worth rendering."
3. **L4 / L5 / L13 name columns that do not exist.** The spec uses `oi_total_calls` / `oi_total_puts`; `gex_strike_snapshots` carries `oi_call` / `oi_put` per ADR-015.

Also corrected: `historical_option_chain_snapshots` carries up to 3 expiries per cycle, but **every** such cycle is 2026-04-16 — the `breeze_backfill_s35` day, which §1.1 records as carrying no spot, no greeks and no bid/ask. The ladder was never captured by the live ingest, in either relation. **No regression occurred; the capability never existed.**

## L9 ingest depth — measured, not assumed

Measured on `hist_option_bars_1m` (the 14-expiry vendor tier), full day 2025-06-02, every contract at its peak OI. Day level holds **21** expiries; the S78 per-minute figure of 14 is a subsample.

**NIFTY** (504.5M OI): W1 67.8 % · current monthly 18.8 % · W2 5.2 % · Dec quarterly 3.4 % · next monthly 2.6 % · Sep quarterly 1.4 % · **W3 0.47 %**.

**SENSEX** (62.4M OI): W1 **97.25 %** · W2 2.65 % · current monthly **0.089 %** · remainder ~0.

**Ruling: capture depth is per-symbol and selected, not sliced.**

- **NIFTY — 4 expiries:** W1, W2, current monthly, next monthly → **94.45 %** of OI at 0 / 7 / 21 / 56 DTE.
- **SENSEX — 2 expiries:** W1, W2 → **99.90 %**. Its monthlies are dead and cost two calls per cycle for nothing.

Chronological `future_expiries[0:4]` yields 92.28 % on NIFTY and no curve — four points inside three weeks. The discriminator is that **W3 carries 0.47 % while the December quarterly carries 3.4 %**, so slicing takes the worthless expiry and misses the valuable one. The monthly is identifiable as the last weekly of its calendar month.

Implementation constraints, all to be measured before shipping:

- The count is `ingest.n_expiries.{symbol}` in `merdian_parameters` per ADR-016. This is a **capture-depth config**, not an output threshold, so TD-S79-NEW-21's measure-before-parameterise rule does not bind it the same way.
  - **Amendment A1 (2026-09-22): what shipped is a module-level constant, not this parameter.** The deviation is deliberate and conditioned; see below.
- **Stage it**: ship at W1+W2, watch ENH-99 retry telemetry for one week, then extend NIFTY to 4. TD-080 is S1-recurring across S22 / S28 / S29.
  - **Amendment A1: the staging shipped finer than this.** A stage 0 at depth 1 — provably inert — precedes W1+W2.
- **Calls and rows are separable risks.** Far expiries need only ATM ± N strikes for an IV reading; full depth is required for W1 alone.
- Cadence may be tiered — W1/W2 every cycle, monthlies less often.

**The SENSEX asymmetry is a finding about the instrument, not a defect.** At 97.25 % front-weekly, any SENSEX term-structure panel is close to a single point, and L9 must render that rather than imply a curve that is not there.

---

## Consequences

**The board reorders immediately.** Under D2, the next work is **rendering ENH-120 / ENH-121 / ENH-122**, not building L9 or L12. **[SUPERSEDED S81 — see Amendment B1. This sentence no longer governs: rendering is deferred until every layer carries a disposition. Left in place so the reversal is visible rather than retrofitted.]** Five views compute; two layers are BUILT; the gap between those numbers is entirely clauses 3 and 4.

**Effort estimates in spec §3 are not binding.** They were derived from source resolution, never from building anything, and two are now measured wrong — L9 is not "3 h, one view + one chart, cheapest real read on the list", and L4/L5 shipped at ENH-120 without the second variant the spec calls for. Ordering is re-derived from measured cost.

**Six S80 production objects require registration under D2 clause 4**, independent of D5's parking:

- `v_gex_max_pain`, `v_gex_pin_maxpain` — views
- `gex_pin_maxpain_history` — table, Rule 10 schema-affecting, requires its own ADR
- `backfill_pin_maxpain_runs(text, timestamptz, timestamptz, integer)` — live
- `backfill_pin_maxpain(text, date)` — **superseded; drop it.** A second callable path into the same table is a hazard, not a spare.
- `scripts/backfill_pin_maxpain.py` — on EC2, untracked
- plus 11,795 rows of derived data in `gex_pin_maxpain_history`

## What this ADR does not decide

- **Whether any layer is correct.** D2 clause 1 requires that a layer computes and has been read, not that its values are right.
- **The L3 rebuild's form.** TD-S79-NEW-17 / -20 / -21 remain open decisions.
- **The ENH-98 deferral.** L7/L8 stay BLOCKED-ON-DECISION until it is lifted.
- **Whether the pin/max-pain coincidence predicts anything.** That is a conjunction question and is governed by spec §5 and ADR-009 — pre-registration, target and success criterion written before the first query. ENH-97 stands as the warning: chi-sq 1.56, p ≈ 0.30 on 1,968 signals.
- **jobid 19.** Re-enabling it caps L13's history at 14 days and deletes what L14 needs. Unresolved, TD-S76-NEW-2.

---

## Amendment A — 2026-09-22 (Session 80)

*Appended at S80 doc-close. The body above is the decision as accepted on 2026-09-21 and is
not edited. This amendment records where the implementation departed from it, what the session
got wrong, and which of D2 clause 4's obligations are now discharged.*

### A1 — Capture depth shipped as a constant, not a parameter

The L9 ruling places the count in `merdian_parameters` as `ingest.n_expiries.{symbol}`, per
ADR-016. What shipped in `ingest_option_chain_local.py` (commit `b094fa2`) is a module-level
constant:

```python
EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}
```

with the extra-expiry pass **appended** before the completion print and guarded by `if _depth > 1:`.

**Why, stated rather than assumed.** A database-read parameter introduces a read path, and a read
path can fail. ADR-023's obligation is that a read fails to *absent*, never to stale — but a
capture-depth read that failed **open** would raise depth silently on a cycle whose downstream
consumers assume one expiry, which is precisely the corruption TD-S79-NEW-12's guard now crashes
on. At depth 1 the constant makes stage 0 inert **by inspection**: the extra pass is unreachable,
W1's path is untouched, and the stdout `Run ID:` contract and ENH-71's `record_write` stay bound
to W1 alone. A constant is the right instrument for a safety interlock; a parameter is the right
instrument for a tuning knob. This is one of the former until the guard has proven itself.

**Actual staging**, finer than the bullet above describes:

| stage | depth | gate |
|---|---|---|
| **0 — shipped S80** | NIFTY 1 · SENSEX 1 | Inert by construction. Verification owed: `grep -c "S80 extra expiries"` on `cron.log` must be **0**, and the day's runs must show `max_exp = 1` at 2–3 runs per symbol. |
| 1 | NIFTY 2 · SENSEX 2 | A non-expiry day, **after** TD-S80-NEW-10's missing expiry filter is fixed. Not before: a second expiry entering `option_chain_snapshots` arms the per-strike `max()` mixture in the S40 `v_max_pain_by_strike`. |
| 2 | NIFTY 4 by the **selection** rule · SENSEX 2 | One week of clean ENH-99 retry telemetry. TD-080 is S1-recurring across S22 / S28 / S29. |

**The parameter is not abandoned; it is conditioned.** It becomes the correct instrument at stage 2,
when depth is a tuning decision rather than an interlock. Recorded as a condition and not a plan:
move the depth to `ingest.n_expiries.{symbol}` once TD-S79-NEW-12's guard has run in production
across a full expiry cycle without firing.

### A2 — Self-corrections, Session 80

In the form of ADR-024 §A9, and for the same reason: an error corrected inside a session leaves no
trace unless it is written down, and the pattern across them is worth more than any one of them.

1. **`[0]` on an unordered set — TD-S79-NEW-12's own shape, hours after patching the guard for it.**
   Claimed the day's first `option_chain_snapshots` row was 09:00 IST; it is **08:30–08:40 IST**.
   The claim came from `ORDER BY ts ASC LIMIT 5` over an arbitrary `LIMIT 20` backfill subset —
   the minimum of a sample read as the minimum of the set. The guard shipped that same morning
   exists to crash on exactly this class of reasoning.

2. **Two measurements three days apart, called an anomaly.** Reported 3,093 against 2,923 `run_id`s
   as unexplained. Monday 2026-09-21 wrote 85 × 2 = 170 runs; 2,923 + 170 = 3,093 exactly. It had
   already been drafted as TD-S80-NEW-6 before the arithmetic was done, and was withdrawn before
   filing — later than it should have been caught, earlier than the register.

3. **Called a stale sentence a phantom commit.** Asserted that `CURRENT.md` referenced a follow-on
   commit that did not exist. On EC2, `grep -c "TD-S79-NEW-23"` = 1 and `change_log[0]` = S79: the
   commit is present and one sentence describing it is stale. Downgraded to **TD-S80-NEW-13**.

4. **Used `sha256` across tiers, which C-15 names an invalid instrument.** Compared file hashes
   Local against EC2 to test identity. `core.autocrlf=true` makes every text file differ across
   those tiers by exactly its line count; the cross-tier instrument is **`git hash-object`**.
   C-15 states this in `MERDIAN_ClaudeCode_Guardrails.md`, which had already been read.

5. **Had §S73.A backwards, and patched production because of it.** Argued against `~/meridian-cc`
   on the grounds that *"CC lives on EC2, so using it re-inverts the deploy direction."* §S73.A
   establishes the agent tree for precisely the opposite reason — so agent work happens on EC2
   **without touching production**. The consequence was not theoretical: both S80 patch scripts
   ran against `~/meridian-engine`, the production tree. Corrected on the operator's instruction
   to read PK first.

**The pattern.** 1 through 4 are one reflex, and it is the reflex ADR-024 §A9 already named:
*reasoning from the archive when the source was available* — a sample for a set, a stale figure
for a current one, a memory of a file for the file. 5 is a different and worse failure: asserting
a topology claim without reading the topology document, then acting on it. Reading PK before
asserting is the remedy for all five, and it is cheap in every one of these cases.

### A3 — D2 clause 4 registration, status at doc-close

Of the six objects the *Consequences* section lists:

- `v_gex_max_pain`, `v_gex_pin_maxpain`, `gex_pin_maxpain_history`,
  `backfill_pin_maxpain_runs(text, timestamptz, timestamptz, integer)` — **DDL committed under
  `sql/` at `85dfad2`.** Register entries land in this doc-close, Enhancement Register Part 4.
- `backfill_pin_maxpain(text, date)` — **dropped**, as ruled. It computed before `ON CONFLICT`
  could discard, and timed out; a second callable path into one table is a hazard, not a spare.
- `scripts/backfill_pin_maxpain.py` — **committed at `85dfad2`**, byte-identical to the run that
  produced the 11,795 rows (`sha256 453f1be8…`). It hardcodes the window 2026-05-25 → 2026-09-18,
  so re-running it extends nothing; extending the history means editing the window.

**Clause 4 is discharged for all six. Rule 10 is not.** `gex_pin_maxpain_history` is a new table
and still owes its own schema ADR — **TD-S80-NEW-7**. Committing DDL and ratifying a schema are
different obligations, and only the first has been met.

*Amendment A — Session 80 doc-close, 2026-09-22. No decision in the body above is reversed,
narrowed or extended by this amendment.*

---

## Amendment B — 2026-09-23 (Session 81)

**This amendment REVERSES part of the Consequences section above. It is recorded as a reversal, not
as a gloss.**

### B1 — Presentation of the parity layers is DEFERRED until every layer carries a disposition

**Decision (operator, S81).** The trigger for rendering is **full dispositional coverage of all
fourteen layers** — not "a layer has become BUILT".

**Rationale (operator).** On the reference board most layers only make sense **in comparison with
each other**. A board assembled one layer at a time is a different artefact from a board designed as
a whole, and the second cannot be reached by iterating toward it from the first. So the design pass
happens once, against a complete set of dispositions.

**What this reverses.** The Consequences section states *"**The board reorders immediately.** Under
D2, the next work is rendering ENH-120 / ENH-121 / ENH-122, not building L9 or L12."* **That
sentence no longer governs.** The board does not reorder to rendering on a layer becoming BUILT; it
reorders when the dispositional set is complete. The original sentence is left in place above and
annotated, so the reversal is visible rather than retrofitted.

**Consequence for D2 clause 3, and it must not be misread.** Clause 3 — *"visible on at least one
operator surface"* — is now **unmeetable by design until the rendering pass runs**. Therefore:

- **BUILT stays at 2 of 14, BY DECISION.**
- **ENH-120 / ENH-121 / ENH-122 / ENH-125 / ENH-126 / ENH-127 remain PENDING on clause 3 only.**
- **This is a deliberate hold, not a lapse.** A later reader finding six computed-and-unrendered
  views must not conclude that clause 3 was forgotten — it was **suspended, with a stated trigger**.
  The distinction matters because D2 clause 3 exists precisely because five invisible views once
  accumulated unnoticed; suspending it deliberately is the opposite of that failure, and only the
  written trigger makes the two distinguishable.

### B2 — Scope of the deferral: it does NOT block repairs to surfaces already shipped

**Decision (operator, S81).** Amendment B defers **presentation of the parity layers**. It does not
block **correctness fixes to cards already live.**

**The instance that forced the ruling.** `useIvSmile` (`queries.ts:395`) neither selected nor
filtered `expiry_date`, filtered to `maxTs`, then wrote `entry.ce = r.iv` into a Map keyed by
strike — **last write wins**. At capture depth 1 that was inert. At depth 2 two expiries share one
`ts` and one silently overwrites the other, on the **Breadth** page's IV-skew number and smile chart
(`sections.tsx:372-379`). **Fixed and deployed 2026-09-22, before the 08:30 IST ingest of 09-23** —
so the collided smile never rendered.

**Why the ruling is recorded rather than assumed.** Amendment B's scope will be read again, by
someone deciding whether a bug fix is allowed. Without this clause a reader could treat the freeze
as blocking repairs, **which it does not**. A deferral of new presentation that silently also froze
defect repair would make the freeze more expensive than the thing it defers.

### B3 — Effort correction: the remaining parity build is DAYS, not weeks

The spec's §3 estimate is **≈ 5 working days**, and that figure is a **FLOOR**, not a midpoint. **Do
not restate it as weeks.** The distinction changes what the deferral costs: a design-as-a-whole pass
gated on a few days of build is a sequencing choice, whereas the same pass gated on weeks would be a
deferral of the programme.

**The only genuine clock in the programme is L9 at NIFTY depth 4**, which needs one week of ENH-99
retry telemetry. **A FIRST L9 build does not need it** — depth 2 is live and verified (see B5).
Nothing else in the fourteen is waiting on elapsed time.

**And that clock currently cannot be read.** **TD-S81-NEW-14** measures that the ENH-99 retry
counters **cannot record the failures actually occurring**: the predicate retries only `429`, `429`
has **never occurred** in any retained log, and the classes that do occur — `502` ×12, `401` ×9,
`500` ×2 — all fail fast without touching the budget. **A week of that telemetry reads clean
regardless of what happens.** The stage-2 gate therefore needs re-definition — count fail-fasts by
class and dropped captures, not retries — **before it can be used to authorise depth 4.**

### B4 — Dispositions as at S81

The **S80 table above is left untouched as the S80 record.** This is the S81 state.

| # | layer | disposition | change since S80 |
|---|---|---|---|
| L1 | Gamma density per strike | **BUILT** | — |
| L2 | Pin zone | **BUILT** | — |
| L3 | Flip level | **BLOCKED-ON-DECISION** | **unchanged — the three open decisions are NOT ruled on in this amendment** |
| L4 | Call wall | **PENDING** | clause 3 now suspended by B1 |
| L5 | Put wall | **PENDING** | as L4 |
| L6 | Net-vs-absolute GEX | **PENDING** | as L4 |
| L7 | Vanna | **PENDING** | **was BLOCKED-ON-DECISION.** ENH-98 deferral **LIFTED** — its own condition (a Phase-1 consumer) is met by L7/L8. Build not started; the go/no-go is INCONCLUSIVE and must be re-run |
| L8 | Charm | **PENDING** | as L7; ships with it |
| L9 | IV term structure | **PENDING** | **unblocked at the source.** Capture depth **stage 1 (W1+W2) deployed and verified** — see B5. Depth 4 still gated, and see B3 on why that gate cannot currently be read |
| L10 | IV surface | **PENDING** | — |
| L11 | Five-axis radar | **PENDING** | — |
| L12 | Pin conviction | **PENDING** | **both legs now compute**: HHI (ENH-122) + ranked (ENH-125). Fails clause 3 only |
| L13 | OI rotation | **PENDING** | **live leg BUILT** (ENH-127). Historical leg still capped by jobid 19. Fails clause 3 only |
| L14 | 30-session gamma river | **PENDING** | **BUILT** (ENH-126) on the gamma_metrics-only decision. Fails clause 3 only |

**BUILT: 2 of 14 — unchanged, and unchanged BY DECISION rather than for want of work.** Four views
shipped this session; none of them can reach clause 3 while B1 holds.

### B5 — A1's stdout precondition is TRUE and guards nothing

Amendment A1 records, as a safety property of shipping capture depth behind `if _depth > 1`, that
*"the stdout `Run ID:` contract and ENH-71's `record_write` stay bound to W1 alone."* **That
statement is true and it protected nothing.**

**The AWS runner never reads that stdout line. It re-queries the table** — `fetch_latest_run_ids()`
ordered by `created_at.desc`. W1 and the extra-expiry pass share one `ts` but **not** `created_at`,
which is a DB-side default and therefore later for the extra pass. So from its **first cycle** at
depth 2 the runner would have handed gamma and volatility **W2's** `run_id`, and
`compute_options_flow_local.py` would independently have picked W2 too — **silently**, because each
`run_id` is still single-expiry and TD-S79-NEW-12's guard sees one expiry and returns W2's date
without raising. `gex_strike_snapshots`, `gamma_metrics`, ENH-120/121/122/125/126, the Pine overlay
and the Positioning page would all have followed, with `gamma_metrics.dte` jumping from 0/2 to 7/9.

**A precondition that holds and protects nothing is the shape this project has a rule about.** It
was fixed before the flip (`89ad2bb`): both selectors now order `ts.desc,expiry_date.asc` — latest
snapshot, then its front expiry — with **no `">= today"` guard**, deliberately and unlike the views,
because the ingest never writes past expiries and a no-fallback guard in the orchestrator converts
an edge case into a **compute outage** rather than a display gap.

**Verified live 2026-09-23 at 09:14 IST, all four checks PASS on both symbols**, through the
read-only path: A depth landed (2 expiries / 2 run_ids), **B gamma on FRONT expiry** (NIFTY
`2026-09-29` dte 6, SENSEX `2026-09-24` dte 1), C one gamma row per cycle, D options flow on front
expiry. **B could have failed**: W2 (`2026-10-06` dte 13 / `2026-10-01` dte 8) was live in the table
at the same `ts`, so the check had a real wrong answer available and did not return it.

### B6 — Stage numbering, corrected

A1's own wording is *"a stage 0 at depth 1 — provably inert — precedes W1+W2"*. Two artefacts
carried an off-by-one against it and both were corrected: `ingest_option_chain_local.py:57-59` (at
`8d51cce`) and TD-S80-NEW-1's Status row (at this doc-close). **Canonical: stage 0 = depth 1 inert ·
stage 1 = W1+W2 · stage 2 = NIFTY 4.** The **code comment mattered more than the register row** — it
is what an implementer reads when choosing a value.

---

## Governance language

**Doc Protocol v4 Rule 11.3.** The sentence that governs, quotable without the surrounding argument:

> **"Hedgewall parity is achieved when every one of the fourteen layers carries a recorded
> disposition — BUILT · PENDING · BLOCKED-ON-DECISION · BLOCKED-ON-DATA · DECLINED-ON-EVIDENCE — not
> when all fourteen are built. A layer counts as BUILT only when all four D2 clauses hold: it
> computes against the live database and its output has been read; it is run-scoped and
> EXPLAIN-verified per ADR-021; it is visible on at least one operator surface; and it has an ENH
> entry with its DDL committed under `sql/`. Agreement with the reference is not required for BUILT.
> A layer outside the fourteen does not count toward parity at all."**

**As amended at S81:** clause 3 is **suspended by decision** until the dispositional set is complete
(**Amendment B1**), so a computed-but-unrendered layer is **PENDING by design, not by neglect** —
and the deferral covers **new parity presentation only**, never repairs to surfaces already shipped
(**Amendment B2**).

**This ADR authorises nothing in production.** Every layer it governs is display-only. Any gate
built on one would additionally require N ≥ 30 live-runtime-cohort validation per ADR-009 and
**D.13.1**.

*Amendment B — Session 81 doc-close, 2026-09-23. **B1 reverses the Consequences section's "the board
reorders immediately" and narrows nothing else.** B2 clarifies scope without changing D1–D5. B4
supersedes the S80 disposition table as the current state and leaves it standing as the S80 record.
B5 and B6 correct Amendment A without reversing its ruling.*
