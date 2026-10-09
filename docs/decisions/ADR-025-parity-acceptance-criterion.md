# ADR-025 — Parity acceptance criterion: a layer is achieved when it renders, and the programme is complete when every layer has a disposition

| Field | Value |
|---|---|
| Status | **Accepted** · **parity CLOSED 2026-10-09** (Amendment D) |
| Date decided | 2026-09-21 |
| Date documented | 2026-09-21 (Session 80) |
| Session | Session 80 |
| Supersedes | Nothing. First acceptance ruling for the Hedgewall parity programme. |
| Related | **TD-S79-NEW-22 (D0)** — the entry that filed this decision · `MERDIAN_Hedgewall_Parity_Spec.md` (S78) · ENH-120 / ENH-121 / ENH-122 (S79) · ENH-123 / ENH-124 (S80, off-spec) · TD-S79-NEW-15…-21 (L3 measured and declined) · ADR-021 (latest-run scoping) · ADR-017 (console design) · ADR-009 (pre-registration) · ADR-016 (parameter calibration) · TD-S79-NEW-3 (`sql/` as a superseded rebuild source) · TD-080 (Dhan 429, S1-recurring) |
| Amended | **Amendment A**, 2026-09-22 (Session 80) — what shipped against what was ruled; session self-corrections; D2 clause 4 registration status. Body text above is unchanged. · **Amendment B**, 2026-09-23 (Session 81) — **REVERSES part of Consequences**: rendering is deferred until every layer carries a disposition, so D2 clause 3 is suspended and BUILT stays 2 of 14 **by decision**. Also rules the deferral's scope (it does not block repairs to shipped surfaces), corrects the effort figure to **days, not weeks**, records the S81 dispositions, and corrects two A1 statements. D1–D5 are otherwise unchanged. · **Amendment C**, 2026-10-08 (Session 92) — **parity closes on D1 plus the P6 render pass** (ruling S92-A, amending S90-D); B1's suspension **spent** on its own trigger; clause-3 evidence measured from the live board (`meridian-connect` `255cca0`); **BUILT 9 of 14**, PENDING L7/L8/L12/L13, L11 DECLINED. **C6** (same session) records rulings S92-C…F. **C7–C8**, 2026-10-09 (Session 92, continued) — clause-3 evidence for L7/L8/L12/L13 read from the live board (`5563bb7`, `1deeb87`); L13 binds ENH-127 (S92-G), SENSEX L13 withheld as a D3 deviation (S92-H); **BUILT 13 of 14, PENDING 0, L11 DECLINED — D1 met**; only R2.4 and the P6 closing amendment remain. · **Amendment D**, 2026-10-09 (Session 92) — **closing amendment (P6): parity CLOSED**; R2.4 REPORTED (`e85cf7a`); D3 deviations at close (L7/L8 D-4, L12 pressure leg, SENSEX L13); the S92-A pause on harness work ends. |
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
| L11 | Five-axis radar | **PENDING** | Composition of five layers, three unbuilt. Last by construction. **[SUPERSEDED 2026-10-03 — **DECLINED-ON-EVIDENCE**. Absent from the terminal sample; composition-only; 0–10 scaling undisclosed. Ruling: `docs/research/s89_rulings/rulings_s89.md` → "L11 (five-axis radar)". Feeds the P6 closing amendment.]** |
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
| L3 | Flip level | **PENDING** | **was BLOCKED-ON-DECISION. All three open decisions are RULED at S81 — see B7.** What remains is build work, not a decision |
| L4 | Call wall | **PENDING** | clause 3 now suspended by B1 |
| L5 | Put wall | **PENDING** | as L4 |
| L6 | Net-vs-absolute GEX | **PENDING** | as L4 |
| L7 | Vanna | **PENDING** | **was BLOCKED-ON-DECISION.** ENH-98 deferral **LIFTED** — its own condition (a Phase-1 consumer) is met by L7/L8. Build not started; the go/no-go is INCONCLUSIVE and must be re-run |
| L8 | Charm | **PENDING** | as L7; ships with it |
| L9 | IV term structure | **PENDING** | **unblocked at the source.** Capture depth **stage 1 (W1+W2) deployed and verified** — see B5. Depth 4 still gated, and see B3 on why that gate cannot currently be read |
| L10 | IV surface | **PENDING** | — |
| L11 | Five-axis radar | **PENDING** | **[SUPERSEDED 2026-10-03 — **DECLINED-ON-EVIDENCE**. Absent from the terminal sample; composition-only; 0–10 scaling undisclosed. Ruling: `docs/research/s89_rulings/rulings_s89.md` → "L11 (five-axis radar)". Feeds the P6 closing amendment.]** |
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

### B7 — L3's three open decisions are RULED (operator, S81)

**Provenance, stated rather than smoothed over.** These rulings were made **in session at S81** and
**did not reach the S81 doc-close notes** during the session; they were recorded at the doc-close on
operator confirmation. The doc-close pass found **zero textual support** in the notes and **declined
to write them** until that confirmation — so what is recorded here is *ruled late*, not
*reconstructed*. The distinction is worth preserving: an ADR clause whose source is a session rather
than a contemporaneous artefact should say so.

These close the three decisions **B4 previously listed as outstanding**, which is why **L3 moves
BLOCKED-ON-DECISION → PENDING**.

**TD-S79-NEW-17 — ADD A DISCRIMINATOR.** `gamma_metrics.flip_level` **values are unchanged**; add a
column recording **which construction produced each row** (LONG cumulative-crossing-nearest-spot vs
SHORT per-strike sign-flip). **No regime or signal behaviour changes.** This is the minimal of the
three options NEW-17 named: it does not pick a winner between constructions, it makes the blend
**readable** — which is exactly what made every S79 flip statistic uninterpretable, since *a blend is
a property of neither construction*. With the column present, past statistics can be re-cut by
construction instead of re-derived.

**TD-S79-NEW-20 — RE-SYNC replay to production.** Replay is pinned to production's legacy fallback
branch and its signature cannot accept the argument that selects the other two. **Pass spot, so
replay takes production's branches**, and **record one historical day's before/after replay flip.**
That one measured day is the witness; without it the re-sync is a code change nothing observed.

**TD-S79-NEW-21 — MEASURE, THEN PARAMETERISE.** **Sweep the SHORT-branch relative floor, report flip
sensitivity, and only then** move it to `merdian_parameters` **at the measured value**. **The
ordering is the ruling.** Parameterising an unmeasured constant **relocates it rather than
calibrating it**, and a parameter implies its value was chosen — which, unswept, it was not.

**What L3 actually builds.** A **NEW display-only view of the REPRICED zero-gamma level**, which
**does not read and does not change `gamma_metrics.flip_level`.** So the unsound shipped construct
is neither displayed nor depended on, and the three rulings above concern making the **existing**
column honest rather than feeding it to the new layer — **two tracks that share a name and nothing
else.**

**Sequencing.** None of -17, -20 or -21 ships before the **stage-1 verification has passed**. **It
passed 2026-09-23 at 09:14 IST** (B5), so **all three are unblocked as of this doc-close.**

---

## Amendment C — 2026-10-08 (Session 92)

*Appended without editing anything above. It records where parity now closes, that Amendment B1's
trigger fired and rendering began without a record saying so, the clause-3 evidence the live board
supplies, and the dispositions that follow. B4 is left standing as the S81 record; C4 is the current
state.*

### C1 — Where parity closes (ruling **S92-A**, amending S90-D)

**Parity closes on D1 plus the P6 render pass**: every one of the fourteen layers carries a final
disposition, the board renders every BUILT layer, and this ADR receives its closing amendment.
S90-D had tied the close to the agentic roadmap's Stage 2 exit (golden days green on every deploy,
parity fixture scores reported, one past day replays exactly). S92-A keeps **R2.4 — screenshot
parity fixtures scored per field — inside parity as the D3 reference check**, and moves **R2.2,
R2.3, R2.5 and R2.6 post-parity**. Single source: `docs/research/s92_parity/rulings_s92.md`.

**R2.4 does not change D2.** Agreement with the reference is still **not** a BUILT condition; R2.4
**reports** per-field scores. Turning any score into a gate needs its own ruling.

### C2 — B1's trigger fired, and rendering began without a record

B1 deferred parity presentation until every layer carried a disposition. **That condition has held
since S81** (B4: no layer blank), and `parity_board_design.md` said so at S84–S85. The board was then
built in the Marketview repository (`balannavin-cyber1/meridian-connect`) between **2026-10-03 and
2026-10-06** — OI tab `cd945f2`, IV tab `d8c379f`, the S90 corrections `98b8930`, live headline and
board stamps `c53dbea` / `255cca0` — and **no register, ADR or CURRENT.md entry recorded that the
rendering pass had begun.** The Enhancement Register still read *"clause 3 PENDING BY DECISION"* on
every view the board was already reading.

**From this amendment B1's suspension is spent**: clause 3 is assessed on evidence, layer by layer,
as D2 always intended. B2 (repairs to shipped surfaces are never blocked) is unaffected.

### C3 — Clause-3 evidence, measured from the consumer side

Read at **`meridian-connect` `255cca0`**, which was **live = staging** when measured on 2026-10-07
(CURRENT.md, AM-1 post-close). Each binding is a query in deployed code, not a design intent. Where
the S90 live check (`docs/research/s90_agentic/marketview_live_check_S90.md`, 2026-10-05) read the
rendered values against the rows the page fetched, that is noted.

| Layer | Object | Binding (`src/`) | Rendered as | Values read live |
|---|---|---|---|---|
| L1 | `gex_strike_snapshots` | `lib/board.ts:137` | the strike ladder | yes (S90) |
| L2 | `v_gex_strike_pin_zone` | `lib/board.ts:349`, `pages/Board.tsx:94,378` | pin-band gutter | not separately |
| L3 | `v_gex_repriced_flip` | `lib/board.ts:83` | strip FLIP, ladder rule, Home | yes (S90, MV-2 fixed) |
| L4 / L5 | `v_gex_strike_walls` | `lib/board.ts:85` | corridor, OI-tab walls | yes (S90; MV-8 noted) |
| L6 | `v_gex_abs_exposure` | `lib/board.ts:81` | net, gross, net/gross | yes (S90, MV-5 fixed) |
| L9 | `v_iv_term_structure` | `lib/board.ts:87,254,421` | IV tab, both legs | yes (S90) |
| L10 | `v_iv_surface` | `lib/board.ts:423` via `useIvTab` (`pages/Board.tsx:276`) | IV-tab smile | parity gaps only (S90) |
| L12 | `v_gex_concentration`, `v_gex_strike_rank` | `lib/board.ts:354`, `:95-99` | top-strike share; pin and lead | rank yes (S90) |
| L13 | **none** — ΔOI recomputed client-side from `gex_strike_snapshots` first vs latest run | `lib/board.ts:283-307`, `pages/Board.tsx:296-303` | OI-tab ΔOI; SENSEX "n/a" | — |
| L14 | `v_gex_net_gamma_river` | `lib/board.ts:379`, `pages/Board.tsx:186` | Gamma-tab river | per-day values not checked |
| L7 / L8 | views do not exist | — | Flows tab: *"layer not built yet"* | — |

The Pin tab also renders *"layer not built yet"* (`components/board/LadderPanel.tsx:212`).

**Clauses 1, 2 and 4 are already on record** for every layer moved below: ENH-120/121/122 EXPLAIN in
TD-S79-NEW-14 (walls 2.507 ms, abs 1.077 ms, concentration 1.943 ms, `Index Only Scan`);
ENH-125/126/127/130/131/132 *"D2 clauses 1/2/4 MET"* in their register rows; DDL for every object
under `sql/`. Several detail panels say *"COMMENT not live"* (TD-S84-NEW-3): clause 4 asks for the
DDL in `sql/`, which is met, so this is a documentation defect and not a clause failure.

### C4 — Dispositions as at S92

| # | layer | disposition | change since S81 (B4) |
|---|---|---|---|
| L1 | Gamma density per strike | **BUILT** | — (re-confirmed on the new board, C3) |
| L2 | Pin zone | **BUILT** | — (re-confirmed: the pin-band gutter binds ENH-81) |
| L3 | Flip level | **BUILT** | PENDING → BUILT. ENH-131; clause 3 met (C3) |
| L4 | Call wall | **BUILT** | PENDING → BUILT. ENH-120 |
| L5 | Put wall | **BUILT** | PENDING → BUILT. ENH-120 |
| L6 | Net-vs-absolute GEX | **BUILT** | PENDING → BUILT. ENH-121 |
| L7 | Vanna | **PENDING** | T1 **PASSED** 2026-10-07 (A5 arm). Views authored (`sql/2026-10-03_s89_v_gex_greeks_l2.sql`), **never applied**; the S89 DROP is moot. D-4 (flow-vs-book) unmet: its previous-close ΔOI input is PPC-1, parked post-parity |
| L8 | Charm | **PENDING** | as L7 |
| L9 | IV term structure | **BUILT** | PENDING → BUILT. ENH-130. TD-S80-NEW-1 (NIFTY stage-1 arm) stays open; it is a max-pain mixture check, not an L9 clause |
| L10 | IV surface | **BUILT** | PENDING → BUILT. ENH-132 |
| L11 | Five-axis radar | **DECLINED-ON-EVIDENCE** | S89, `d9a804a` |
| L12 | Pin conviction | **PENDING** | HHI and rank legs render (C3). Ranked-**pressure** key DECLINED-ON-EVIDENCE (D-5a). Conviction (D-5c) not built; Pin tab empty |
| L13 | OI rotation | **PENDING** | The board shows ΔOI but **does not read ENH-127**: it recomputes since-first-run client-side — a second implementation of a gated rule. SENSEX suppressed (TD-S84-NEW-4) |
| L14 | 30-session gamma river | **BUILT** | PENDING → BUILT. ENH-126 |

**BUILT: 9 of 14 · DECLINED-ON-EVIDENCE: 1 · PENDING: 4 (L7, L8, L12, L13).**

D2 does not require a layer's values to be right, and C4 does not claim they are. Known open items
on BUILT layers stay on their own registers: E-D1 (the unit of `gex_cr`, shown on the board as
*"unit definition pending"*), MV-8 (degenerate corridor), TD-S84-NEW-3 (COMMENTs not live).

### C5 — What remains before P6

1. **L7 / L8.** Restamp the authored DDL's PROVISIONAL text from *"T1 pending"* to the A5 PASS, apply
   it, render on the Flows tab, and rule on D-4 against PPC-1 (un-park it, or record a D3 deviation).
2. **L12.** Build conviction stage 1 (D-5c) and pin state from `gex_cycle_history` on the Pin tab, and
   rule how a layer with one leg DECLINED and the rest BUILT is disposed. Pin state depends on
   ENH-133 acceptance (roadmap R0.4).
3. **L13.** Bind `v_oi_rotation_since_open` or rule the client recompute acceptable — not both — and
   decide whether the SENSEX guard gates the layer.
4. **R2.4** fixture scores reported (C1).
5. **P6** closing amendment.

### C6 — Rulings S92-C…F (same session, 17:06 IST)

Recorded in `docs/research/s92_parity/rulings_s92.md`, not restated here. Their effect on C4 and C5:

- **L7 / L8 (S92-C, S92-E).** D-4 is an **ADR-025 D3 deviation**, deferred to PPC-1 post-parity, so
  it no longer blocks BUILT. The views carry the badge *"PROVISIONAL -- flow-vs-book (D-4) not built"*.
  L7 and L8 become BUILT when the Flows tab reads `v_gex_greeks_l2_strike` / `_net` on the live board.
  C5 item 1's "rule on D-4" is done.
- **L12 (S92-D, S92-F).** The Pin tab reads `v_pin_board` (one session of `gex_cycle_history`, front
  leg, anon through the view only). L12 becomes BUILT when it does, with the ranked-pressure leg
  DECLINED-ON-EVIDENCE as a D3 deviation and conviction stage 2 not required. C5 item 2's
  disposition question is done.
- **C4 is not changed by C6.** BUILT stays 9 of 14 until the two tabs ship and are read as C3 was.

### C7 — Clause-3 evidence for L7, L8, L12 and L13, read from the live board (2026-10-09)

**L7, L8, L12 and L13 are BUILT.** Every one of them now meets all four D2 clauses; the evidence for
clause 3 was read the way C3 was — from the served bundle on the live board, not from the code.

| layer | surface | live commit (`meridian-connect`) | clause 2 (EXPLAIN, as `anon`) | what the live board read |
|---|---|---|---|---|
| **L7** ∂Δ/∂σ · ∂Γ/∂σ | Flows tab, 2 × 2 grid + ladder bars | `e3fc3d3` (10-08), presentation pass `5563bb7` (10-09 07:03 IST) | `v_gex_greeks_l2_strike` / `_net` **192 ms** | NIFTY ∂Δ/∂σ **+5,405 Cr / 5,405 Cr**, ∂Γ/∂σ **+63,845 Cr / 3.2L Cr**; badge *"PROVISIONAL — flow-vs-book (D-4) not built"* at the top of the tab |
| **L8** ∂Δ/∂t · ∂Γ/∂t | as L7 | as L7 | as L7 | NIFTY ∂Δ/∂t **−7,933 Cr / 7,933 Cr**, ∂Γ/∂t **−1.7L Cr / 4.8L Cr**; SENSEX expiry leg *"front skipped · expiry day · chain 15:40"* |
| **L12** pin conviction | Pin tab, pin-state card + leader strip + share-of-gross ladder | as L7 | `v_pin_board` **1.1 ms**; anon reads the view and is **denied on `gex_cycle_history`** | NIFTY pin **22,500 · SHIFTING · conviction 0.00 · stage 1 · no band (D-6)**; SENSEX **71,600 · SHIFTING · 0.25** |
| **L13** OI rotation | OI tab, ΔOI item + ladder ticks | **`1deeb87`** (10-09 07:47 IST) | `v_oi_rotation_since_open` **19.1 ms**, index scans only | NIFTY **C +909.5L · P +288.4L** (= +90,945,465 / +28,841,280 qty), *"since 09:15 · chain 15:40 · session 2026-10-08 · not fresh"*; SENSEX *"ΔOI · n/a (SENSEX · TD-S84-NEW-4)"* |

**Clause 4** holds for each: ENH-98 (`sql/2026-10-03_s89_v_gex_greeks_l2.sql`, restamped by S92-C),
ENH-133 + `sql/2026-10-08_s92_v_pin_board.sql` (S92-D), ENH-127
(`sql/2026-09-22_s81_v_oi_rotation_since_open.sql`).

**L13 closes on the database view, not the client recompute** (ruling **S92-G**): the board's
since-first-γ-run recompute in `useLadderStrikes` was deleted in the same commit, so there is one
implementation of the rule, not two. **SENSEX L13 is withheld** (ruling **S92-H**) because its 09:15
anchor can come from a stale vendor row (TD-S84-NEW-4); this is the layer's **D3 deviation**, recorded
in ENH-127. One clean SENSEX session (10-08: top |Δ| 5.4M on 71,600 CE, nothing near the 48.7M
artefact) is noted and **does not** close the TD.

**How the presentation was built.** The Pin/Flows presentation pass and the L13 bind went through
Lovable (the 2026-09-29 standing ruling), under a safeguard kit recorded in
`docs/lovable_prompts/s92/`: a box-side guard that refuses to build `/staging/` if Lovable's net diff
touches any path outside an allowlist, adds any data read other than the one named view, adds a
credential pattern, or adds the words *vanna* / *charm*; and a read-only ACL fingerprint (relation
ACLs, anon privileges, functions, policies, default privileges, schemas, triggers, anon role) taken
before and after. **The fingerprint was identical across all three Lovable rounds** (05:07, 06:53 and
07:25 IST; `anon_writable_objs = 0` throughout). The guard **stopped one build**: an operator 3D
experiment had added `three` / `@react-three/*`, a route and direct anon reads of
`gex_strike_snapshots` and `trading_calendar`; it was preserved on branch `lab-3d`, removed from
`main`, and filed as TD-S92-NEW-2. Every promotion was gated on a browser read of `/staging/`
against figures measured from SQL.

### C8 — Dispositions as at S92 close of the render pass

| # | layer | disposition | change since C4 |
|---|---|---|---|
| L1 | Gamma density per strike | **BUILT** | — |
| L2 | Pin zone | **BUILT** | — |
| L3 | Flip level | **BUILT** | — |
| L4 | Call wall | **BUILT** | — |
| L5 | Put wall | **BUILT** | — |
| L6 | Net-vs-absolute GEX | **BUILT** | — |
| L7 | Vanna (∂Δ/∂σ, ∂Γ/∂σ — never labelled "vanna", L78-1) | **BUILT** | PENDING → BUILT (C7). D3 deviation: D-4 flow-vs-book, PPC-1 post-parity (S92-E) |
| L8 | Charm (∂Δ/∂t, ∂Γ/∂t — never labelled "charm", L78-1) | **BUILT** | as L7 |
| L9 | IV term structure | **BUILT** | — |
| L10 | IV surface | **BUILT** | — |
| L11 | Five-axis radar | **DECLINED-ON-EVIDENCE** | — |
| L12 | Pin conviction | **BUILT** | PENDING → BUILT (C7). D3 deviation: ranked-pressure leg DECLINED-ON-EVIDENCE (D-5a, S92-F); conviction stage 2 not required |
| L13 | OI rotation | **BUILT** | PENDING → BUILT (C7). D3 deviation: SENSEX withheld (S92-H, TD-S84-NEW-4). Historical leg remains capped by jobid 19 (TD-S76-NEW-2) and is not a BUILT condition |
| L14 | 30-session gamma river | **BUILT** | — |

**BUILT: 13 of 14 · DECLINED-ON-EVIDENCE: 1 · PENDING: 0.** C8 supersedes C4 as the current state
and leaves C4 standing as the 2026-10-08 record. **D1 is met**: every layer carries a final
disposition and the board renders every BUILT layer.

**What remains before the P6 closing amendment:** **R2.4** fixture scores reported (C1; reported,
not gating). Nothing else in C5 is open. Follow-ups that are not parity conditions: TD-S92-NEW-1
(*"contracts"* in the OI explanations), TD-S92-NEW-2 (`lab-3d` review), TD-S92-NEW-3 (a cited probe
missing from git), TD-S92-NEW-4 (`authenticated` privileges on the S92 views).


## Amendment D — 2026-10-09 (Session 92) — closing amendment (P6)

*Appended without editing anything above. It records that parity is closed under the criterion C1
set, the R2.4 report that C1 kept inside parity, and the D3 deviations standing at close. It rules
nothing new. C8 remains the current disposition table.*

### D1 — Parity is closed

Ruling **S92-A** (C1) set three conditions. All three now hold:

| condition (C1) | evidence |
|---|---|
| every one of the fourteen layers carries a final disposition | **C8**: BUILT 13 of 14, L11 DECLINED-ON-EVIDENCE, PENDING 0 |
| the board renders every BUILT layer | **C3** (L1–L6, L9, L10, L14 at `255cca0`) and **C7** (L7, L8, L12, L13 at `5563bb7` / `1deeb87`), each read from the served bundle on the live board; live = `meridian-connect` **`1deeb87`** at close |
| this ADR receives its closing amendment | this amendment |

R2.4, which C1 kept inside parity as the D3 reference check, is **REPORTED** (D2 below).

**Hedgewall parity is closed as at 2026-10-09.**

### D2 — R2.4, reported (not gating)

`docs/research/s92_parity/r24/README.md` (`meridian-engine` `e85cf7a`). **40 fixtures** from the
reference dashboard's own screenshots (NIFTY 36, SENSEX 4), **199 field scores**, reference values
read twice blind (186 of 199 identical, the rest formatting or column choice), MERIDIAN's side
replayed by its own rules as of each anchor.

| field | result |
|---|---|
| DTE | 19 of 19 |
| Spot | 23 of 26 within 0.1 % |
| Pin vs MERIDIAN leader | 11 exact, 9 more inside MERIDIAN's top 5 (20 of 26), 6 outside |
| Net GEX sign | 17 of 21 (the four misses sit near the flip) |
| Walls | 8 of 17 exact |
| HHI | reference / MERIDIAN median **2.09** — the reference divides by a stated strike window, MERIDIAN by every strike in the run |
| Flip | comparable only to the legacy `flip_level` (reference always lower, median 407 pts); the board's L3 flip has no fixture yet |
| ± gamma peaks | unresolved, n = 8 |

**No score is a BUILT condition and none reopens a disposition** (C1; D2 of this ADR). Turning any
score into a gate still needs its own ruling.

### D3 — D3 deviations standing at close

Each is a place where MERIDIAN does not do what the reference does, with the stated reason ADR-025 D3
requires:

| layer | deviation | reason on record |
|---|---|---|
| L7, L8 | flow-vs-book split (D-4) not built; views badged *"PROVISIONAL — flow-vs-book (D-4) not built"* | its previous-close ΔOI input is PPC-1, parked post-parity (**S92-C, S92-E**) |
| L12 | pin ranked on \|gamma\|, not on the reference's pressure key | ranked-pressure leg DECLINED-ON-EVIDENCE (D-5a, **S92-F**); R2.4 finding 1 shows it in the scores (the 6 pin misses) |
| L13 | SENSEX withheld (*"n/a"*) | its 09:15 anchor can come from a stale vendor row, TD-S84-NEW-4 (**S92-H**) |

L11 is DECLINED-ON-EVIDENCE (S89, `d9a804a`), not a deviation on a BUILT layer.

### D4 — What closing changes, and what it does not

- **The S92-A pause ends.** Harness / agentic work paused "until parity closes" may resume: R2.2,
  R2.3, R2.5, R2.6 and Stages 3+ of `agentic_layer_roadmap_S90.md`, all post-parity.
- **Nothing is authorised in production.** Every layer stays display-only; the closing paragraph of
  *Governance language* is unchanged.
- **Open items stay on their own registers** and are not parity conditions: E-D1 (unit of `gex_cr`),
  MV-8, TD-S84-NEW-3, TD-S84-NEW-4, TD-S80-NEW-1, PPC-1, ENH-134 (as-of functions),
  TD-S92-NEW-1…4, and R2.4's open findings (± peaks; L3 flip awaiting post-2026-10-05 screenshots).

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

**As amended at S92:** B1's suspension is **spent** — its trigger had held since S81 and rendering
began 2026-10-03 — so clause 3 is assessed on evidence again (**Amendment C2**). Parity closes on D1
plus the P6 render pass, with R2.4 fixture scores reported but not gating (**Amendment C1**, ruling
**S92-A**).

**As at 2026-10-09 (Amendment C8):** BUILT **13 of 14**, L11 DECLINED-ON-EVIDENCE, PENDING **0** — D1 is
met and the board renders every BUILT layer.

**As closed, 2026-10-09 (Amendment D):** R2.4 scores are reported and this ADR carries its closing
amendment — **Hedgewall parity is closed.** Scores remain reported, not gating.

**This ADR authorises nothing in production.** Every layer it governs is display-only. Any gate
built on one would additionally require N ≥ 30 live-runtime-cohort validation per ADR-009 and
**D.13.1**.

*Amendment B — Session 81 doc-close, 2026-09-23. **B1 reverses the Consequences section's "the board
reorders immediately" and narrows nothing else.** B2 clarifies scope without changing D1–D5. B4
supersedes the S80 disposition table as the current state and leaves it standing as the S80 record.
B5 and B6 correct Amendment A without reversing its ruling.*

*Amendment C — Session 92, 2026-10-08. **C1 records ruling S92-A** (where parity closes). **C2 ends
B1's suspension on its own stated trigger** and narrows nothing else in B. C4 supersedes B4 as the
current state and leaves it standing as the S81 record. D1–D5 are unchanged. C7–C8, 2026-10-09: L7/L8/L12/L13 BUILT on live-board evidence; C8 supersedes C4 as the current state and leaves C4 standing as the 2026-10-08 record.*

*Amendment D — Session 92, 2026-10-09. **Closing amendment (P6).** Records that the three C1 conditions hold and parity is closed, R2.4 reported, and the D3 deviations at close. Rules nothing new; C8 stays the current disposition table. D1–D5 are unchanged.*
