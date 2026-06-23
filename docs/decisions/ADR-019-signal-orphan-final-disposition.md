# ADR-019: Signal-Subsystem Orphan Final Disposition (Port-Not-Retire)

## Status

ACCEPTED — 2026-06-22 (Session 58)

Executes the governance rule established in **ADR-018** ("orphaned signal subsystems are dispositioned explicitly — retire-with-evidence or port-to-AWS — never left silently dead") for the three subsystems left open after ADR-018 dispositioned SMDM. Cross-references ADR-018 (D3 SMDM retire / D4 ENH-SDM), ADR-007 (V18F ICT pivot → signal_v4), ADR-006 (AWS migration scope), ADR-001 (stable-lies → shadow/cross-reference is permanent governance).

## Context

The S49 Local-disable migrated capture + core compute to AWS but **did not include the signal layer**. Five V17 (16E) shadow-batch subsystems died with Local: SMDM, momentum_v2, and the chain `options_flow` + `iv_context` → `shadow_signal_v3`. SMDM was dispositioned in ADR-018 (retired as built, primitives rebuilt as ENH-SDM). This ADR dispositions the remaining three.

The three are **one dependency chain**, not independent subsystems:

```
compute_options_flow_local.py → options_flow_snapshots ─┐
                                                        ├→ build_shadow_signal_v3_local.py
compute_iv_context_local.py   → iv_context_snapshots ───┘        → shadow_signal_snapshots_v3
                                                                 → evaluate_shadow_vs_live.py
```

`options_flow_snapshots` and `iv_context_snapshots` are read by nothing but shadow-v3.

### Why the first-pass "deprecate" verdict was wrong

The initial analysis recommended **deprecating** all three, reasoning that the V16 Measure→Validate→Shadow→Promote cycle they served "concluded" at V18F (the candidate was promoted, the live path became signal_v4), making shadow-v3 a spent experiment.

That reasoning was reversed on operator challenge, and the reversal is the substantive content of this ADR: **a subsystem must not be retired on the strength of an experiment-state or experiment-verdict claim, because MERDIAN's own record shows those verdicts do not reliably hold.** This very session rebuilt SMDM's primitives as ENH-SDM *despite* its Exp 9 NEUTRAL verdict (ADR-018 D4) — i.e. ADR-018 itself did not retire on a verdict; it retired a stale *build* while keeping the *idea*. "Retire-with-evidence" therefore means evidence that the **capability has no value**, not a verdict on one historical instance of it. None of these three failed that bar. They went dark from a **migration-scope wiring gap (S49)**, not from a test that holds.

## Decision

**Port, do not retire, all three — deferred and sequenced.** Each is a retained capability pending re-home to AWS, with the dependency chain kept intact so they port as a unit.

### D1 — `shadow_signal_v3`: RETAIN the shadow-comparison mechanism; only the v3 instance is dated

`build_shadow_signal_v3_local.py` + `shadow_signal_snapshots_v3` + `evaluate_shadow_vs_live.py` implement the **Shadow** stage of Measure→Validate→Shadow→Promote — the capability whose founding lesson is ADR-001 (a duration gate cannot catch a stable lie; you need the shadow/cross-reference). That is permanent governance tooling, not a spent experiment. What is genuinely dated is the v3 signal logic's coupling to a pre-v4 architecture. Disposition: **preserve the shadow-comparison harness; rebuild it against `signal_v4` at the next signal-architecture change that needs a Shadow stage.** Discarding it would mean rebuilding the validation harness from scratch at that point. Whether any of the v3 signal *logic* is worth carrying forward is deferred to that rebuild and is an operator call.

### D2 — `iv_context`: RETAIN / port (distinct capability, not superseded)

`compute_iv_context_local.py` (a 09:05 setup task) + `iv_context_snapshots` is **IV regime/context** — for an options-*buying* system, a first-order input (am I buying cheap or expensive premium). The first-pass claim that it was "superseded by `gamma_call`/`gamma_put`" (ADR-015) was wrong: that split gives per-strike *gamma* skew, one slice, not IV regime. Distinct capability, orphaned by S49, not refuted. Disposition: **port to AWS when wired to a live consumer** (signal path and/or Marketview IV-regime surface).

### D3 — `options_flow`: RETAIN-DORMANT (do not delete; tied to ENH-02)

`compute_options_flow_local.py` + `options_flow_snapshots` is **ENH-02's substrate** (the PCR/flow work extended this session — ΔPCR + ATM±3 strike-PCR). Disposition: **dormant, not deleted.** If ENH-02's PCR graduates to a live context scalar, this re-homes to AWS with a *live* consumer (signal/dashboard), not shadow-v3.

## Consequences

- The S49 signal-orphan question is **closed by disposition, not by deletion**: SMDM (ADR-018 D3, build retired / idea rebuilt as ENH-SDM), and now shadow-v3 + iv_context + options_flow all RETAINED pending re-home. Nothing is left silently dead (ADR-018 governance satisfied), and nothing valuable is discarded on verdict grounds.
- The three port **as a unit** (the chain is intact) when the shadow harness is rebuilt against v4 — likely alongside or after ENH-SDM (which also needs the AWS/orchestrator signal-layer path per ADR-018 D4).
- No code runs today for any of the three (all dormant since S49); this ADR changes their *status and intent*, not their runtime. No deployment action is taken now.
- `momentum_v2` (the fifth V17 shadow-batch member) is not dispositioned here; flag it for a future pass so the batch is fully accounted for.

## Governance

**Refines ADR-018's disposition rule:** "retire-with-evidence" requires evidence that a capability has **no value** — an experiment verdict or experiment-state claim on a single instance is *not* sufficient grounds to retire, because MERDIAN's validation history shows such verdicts do not reliably transfer (cohort-translation discipline; SMDM-NEUTRAL-then-rebuilt). A subsystem orphaned by a migration-scope gap defaults to **port**, sequenced behind a live consumer, not to deprecation. Deletion of a retained-dormant subsystem requires a separate explicit decision once its owning ENH is itself closed.
