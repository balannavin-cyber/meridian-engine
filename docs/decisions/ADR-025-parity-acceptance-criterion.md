# ADR-025 — Parity acceptance criterion: a layer is achieved when it renders, and the programme is complete when every layer has a disposition

| Field | Value |
|---|---|
| Status | **Accepted** |
| Date decided | 2026-09-21 |
| Date documented | 2026-09-21 (Session 80) |
| Session | Session 80 |
| Supersedes | Nothing. First acceptance ruling for the Hedgewall parity programme. |
| Related | **TD-S79-NEW-22 (D0)** — the entry that filed this decision · `MERDIAN_Hedgewall_Parity_Spec.md` (S78) · ENH-120 / ENH-121 / ENH-122 (S79) · ENH-123 / ENH-124 (S80, off-spec) · TD-S79-NEW-15…-21 (L3 measured and declined) · ADR-021 (latest-run scoping) · ADR-017 (console design) · ADR-009 (pre-registration) · ADR-016 (parameter calibration) · TD-S79-NEW-3 (`sql/` as a superseded rebuild source) · TD-080 (Dhan 429, S1-recurring) |
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
- **Stage it**: ship at W1+W2, watch ENH-99 retry telemetry for one week, then extend NIFTY to 4. TD-080 is S1-recurring across S22 / S28 / S29.
- **Calls and rows are separable risks.** Far expiries need only ATM ± N strikes for an IV reading; full depth is required for W1 alone.
- Cadence may be tiered — W1/W2 every cycle, monthlies less often.

**The SENSEX asymmetry is a finding about the instrument, not a defect.** At 97.25 % front-weekly, any SENSEX term-structure panel is close to a single point, and L9 must render that rather than imply a curve that is not there.

---

## Consequences

**The board reorders immediately.** Under D2, the next work is **rendering ENH-120 / ENH-121 / ENH-122**, not building L9 or L12. Five views compute; two layers are BUILT; the gap between those numbers is entirely clauses 3 and 4.

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
