# MERDIAN Decision Index

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Decision_Index.md` |
| Location | `docs/decisions/` |
| Type | Flat lookup of every accepted architectural decision |
| Established | 2026-05-09 (Session 23 — ADR-007 acceptance, Doc Protocol v4 Rule 9.3 introduction) |
| Update rule | Mechanically prepended on every accepted ADR per Doc Protocol v4 Rule 11.1 |

---

## Purpose

A single flat table of every architectural decision MERDIAN has accepted. Two uses:

1. **Pre-flight check at session start.** Before proposing an architectural change, scan this index for "have we decided this already?" Saves session time on re-litigation. Used by future Claude as part of session-start read order (CLAUDE.md Rule 0).
2. **Audit trail across versions.** Each row links back to the full ADR, where the context, evidence, alternatives and consequences live in detail. The index itself is one row per decision; the ADR is the body.

This is not a substitute for the ADRs themselves. It is the lookup that makes the ADR collection navigable.

---

## Conventions

- **Newest first.** New entries prepend at the top of the table. Order = reverse-chronological by Date.
- **One row per accepted ADR.** Rejected ADRs do not enter the index (their status remains in the ADR file itself for audit). Superseded ADRs stay in the index with a `[SUPERSEDED by ADR-NNN]` annotation in the Decision column.
- **Mechanical sourcing.** Each row is sourced from the metadata header + Decision section + Alternatives section + Governance language footer of the ADR. Rule 11.1 specifies the field-to-column mapping.
- **One-liner discipline.** Decision / Rationale / Rejected columns each fit on one line. Long-form lives in the ADR.
- **CASE files separate.** Single-event case studies (`CASE-YYYY-MM-DD-<topic>.md`) are not entered here. They live in `docs/decisions/` alongside ADRs but are diagnostic records, not architectural decisions.

---

## Index

| ID | Date | Topic | Decision | Rationale | Rejected alternative | Source |
|---|---|---|---|---|---|---|
| **ADR-008** | 2026-05-09 | Replay architecture: zero-touch parallel-pipeline sandbox for what-if signal experiments | Build parallel `*_replay` table layer (10 mirrors via CREATE TABLE LIKE INCLUDING ALL) + parallel `replay/*` script layer (7 scripts mirroring live counterparts); CLI `--replay-ts` time injection; out-of-hours hard guard 08:00-16:30 IST weekdays; orchestrator runs scripts in V19 §5.2 order PER BOUNDARY (not script-by-script across boundaries); validation philosophy is replay-vs-replay with one variable changed, NOT replay-vs-live. | ENH-93 CANDIDATE matured into requirement for what-if signal-logic experiments. Live signal_snapshots cannot be replayed under modified code without touching production. Phase 4b 2026-05-07 full-day run: 1056/1064 invocations (99.2%) succeeded; per-script success ≥95% across all 7. NIFTY direction-of-edge match with live: 100% gamma_regime, 68% direction_bias (32% divergence traces to documented spot-granularity property). | Re-run live ingest in sandbox (rejected — wall-clock dependent + side effects); monkey-patch live scripts (rejected — zero-touch violation, diagnostic blast radius); single-script replay (rejected — gates need full upstream chain); live-table re-write with `is_replay` flag column (rejected — coupling + regression risk). | [ADR-008-replay-architecture.md](./ADR-008-replay-architecture.md) |
| **ADR-007** | 2026-04-11/12 (decided) · 2026-05-09 (documented) | V18F ICT signal architecture pivot | ICT pattern detection becomes primary signal trigger; Kelly tier sizing replaces uniform confidence-based sizing; LONG_GAMMA / NO_FLIP gates preserved; CONFLICT terminal rule lifted; VIX>20 gate removed; MIN_CONFIDENCE 60→40; confidence-score becomes adjustment layer; T+30m exit confirmed. | Exp 15: pure ICT 86–94% standalone WR on OB patterns. Exp 17/19: LONG_GAMMA symmetric block correct (47.7% WR — below random). ENH-35 full-year backtest: NIFTY 244 signals, 58.6% T+30m accuracy. Phase 4 promotion gate met (V18G §10.1). | Implement V15.1 spec'd remediation in full (three-zone gamma + multi-horizon voting + regret-log threshold gate within confidence-scoring architecture) — rejected: Exp 17/19 evidence shows LONG_GAMMA is correctly binary; Exp 20 evidence shows momentum is confirmation not vote-member; the V15.1 path leaves discrete ICT-pattern edge on the table. | [ADR-007-v18f-ict-pivot.md](./ADR-007-v18f-ict-pivot.md) |
| **ADR-002** | 2026-04-28 | Market structure philosophy: force over direction, zones over points, scale over time | Six principles (P1–P6) govern the gamma layer and signal engine: P1 markets are zones not points; P2 force over direction; P3 GEX walls are non-stationary; P4 dealer flow drives intraday structure; P5 PINNED gamma regime as new state class; P6 capital scaling demands depth-aware position sizing. Companion to ADR-001. | Practitioner-validated dashboard analysis (Session 12). MERDIAN's V15.1 Appendix D assumption gaps (binary regime, point-based proximity). Capital scaling reality — strategy must evolve as AUM grows. | Maintain V15.1 binary regime + point-based proximity computations as "good enough" — rejected: Appendix D explicitly flagged these as unvalidated, and the practitioner dashboard's success demonstrated the premium of zone- and force-based reasoning. | [ADR-002-market-structure-philosophy.md](./ADR-002-market-structure-philosophy.md) |
| **ADR-001** | 2026-04-23 | Stable lies defeat duration gates: validity requires cross-reference | All MERDIAN gates (shadow gates, promotion gates, validation gates) MUST pair stability testing with validity testing before any component is promoted. Validity layer = cross-reference against external independent source OR internal consistency rule. Validity checks run every cycle, not just at gate boundaries. | Session 7 root-cause: 27-day breadth cascade failure. `equity_intraday_last` reference froze 2026-03-27 when ingest_breadth_intraday_local.py was retired without writer-replacement. Every breadth cycle for 27 days produced fabricated BULLISH 92.x readings. 10-session shadow gate passed during the corruption — duration gate cannot detect a stable lie. | Lengthen duration gate (e.g. 20+ or 30+ sessions) — rejected: more sessions of corrupted data cannot surface corruption. The lever is cross-reference, not duration. | [ADR-001-stable-lies-defeat-duration-gates.md](./ADR-001-stable-lies-defeat-duration-gates.md) |

---

## Pending ADRs — reserved IDs

These IDs are reserved for upcoming architectural decisions. They are not yet drafted; they are placeholders called out in CLAUDE.md to prevent ID collision.

| ID | Topic | Owner | Status |
|---|---|---|---|
| ADR-003 | Phase 1 closure (Operational Core complete declaration) | Navin / Claude | Reserved per CLAUDE.md notes |
| ADR-004 | ICT canon deviations (D-OB definition, D-zone validity, PDH/PDL ±20pt hardcoded — TD-049/050/051) | Navin / Claude | Reserved per CLAUDE.md notes |
| ADR-005 | Zone validity standard (write-once-never-recompute vs continuous re-evaluation — TD-079) | Navin / Claude | Reserved per CLAUDE.md notes |
| ADR-006 | AWS migration scope (what runs on AWS vs Local — durable boundary) | Navin / Claude | Reserved per CLAUDE.md notes |
| ADR-009+ | Next-free | — | Available |

---

## Migration note — pre-ADR settled decisions awaiting promotion

The pre-ADR habit, V19 §8.5 SRB rules and several appendix-§17 decision registries contain **settled architectural decisions that are not yet captured as ADRs**. Two queues:

### V18 master §17 — Consolidated Decision Registry (~12 entries)

V18 master Section 17 records decisions accumulated across V17A–V17E sessions. Examples include the V18 health-monitoring architecture choices, the Dhan→Zerodha WebSocket architecture decision, calendar control rules, and the AWS shadow scope. These predate the ADR habit.

### V18G master §10 — Decision Log (~7 entries)

V18G §10 records decisions from the WebSocket deployment / Phase 4A session. Entries include: Phase 4 promotion gate waiver (10.1), Phase 4 execution path A→B→C (10.2), WebSocket broker choice — Zerodha for NIFTY, Dhan REST for SENSEX (10.3), and four further operational decisions.

### Disposition

These decisions remain authoritative and are cited by current code. They are not orphans — their rationale lives in the cited V18/V18G master sections. But they are not lookup-discoverable from this index, which is the gap.

Two paths forward (pick per ADR-by-ADR judgment, no bulk migration required):

1. **Promote to full ADR.** When a decision is materially load-bearing (e.g. WebSocket broker choice — ADR-006 reserved territory), draft a retroactive ADR using the ADR-007 precedent. The ADR cites the V18 source as the original record; this index gets a new row.
2. **Leave in source.** Operational decisions (e.g. dashboard rewrite specifics, capital floor lowered ₹200K → ₹10K) can stay in their V18 source. They appear in CLAUDE.md "Things that are settled" if directly relevant to future sessions, but do not require an ADR.

This index does not introduce a `DEC-NNN` ID prefix. Per Doc Protocol v4 Rule 5, only ADR-NNN and CASE-YYYY-MM-DD IDs live here.

---

## Index health checks

Suggested cadence — once per phase boundary or quarterly, whichever first:

- Verify every accepted ADR in `docs/decisions/` has a row in this index
- Verify every row in this index has a working `Source` link
- Verify the CLAUDE.md "Things that are settled" footer contains a one-liner for every ADR in this index (Doc Protocol v4 Rule 11.3 reverse check)
- Verify no ADR is in Status: Proposed for more than two sessions without movement (escalate or reject)

---

*MERDIAN Decision Index — established Session 23, 2026-05-09. Prepend-only. Do not edit existing rows except to add `[SUPERSEDED by ADR-NNN]` annotations.*
