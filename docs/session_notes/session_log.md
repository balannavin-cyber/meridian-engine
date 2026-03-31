# MERDIAN Session Log

**Running history of all development sessions. One entry per session. Newest first.**

Maintained per MERDIAN_Session_Management_v1.md Rule 5.
Committed to Git at end of every session.

---

## 2026-03-31 — Documentation / Planning — Documentation Baseline Sprint + Governance Framework

**Goal:** Establish complete documentation baseline: format V18A, update registers, build JSON reference layer, produce all operational protocol documents, and establish governance framework for future sessions.

**Session type:** documentation / planning

**Completed:**
- MERDIAN_Appendix_V18A_v4.docx — formatted from raw content. 986 paragraphs, 13 blocks, rebuild-grade. Supersedes v1/v2/v3. Covers: E-02 three-zone gamma shadow, signal regret log (614 rows), TOTP token automation, partial-pipeline failure diagnosis, 6 functional narrations.
- MERDIAN_OpenItems_Register_v3.docx — updated from v2. D-06 SUBSTANTIALLY CLOSED. E-01 CLOSED (614 rows). E-02 SHADOW LIVE. A-03 PARTIALLY CLOSED. Three new items added: V18A-01 (Windows token unattended proof), V18A-02 (runner circuit-breaker), V18A-03 (trading_calendar maintenance). Priority sequence updated.
- merdian_reference.json — built from scratch. 35 files, 25 tables, 6 security IDs, 8 AWS runtime files, 5 cron entries, 16 open items, 16 governance rules, session resume template. Machine-queryable operational layer.
- MERDIAN_Enhancement_Register_v1.md — 27 enhancements across 4 tiers. Tier 1 (actionable now, 8 items including ENH-06 pre-trade cost filter, ENH-07 basis-implied rate, ENH-08 vega bucketing). Tier 2 (after Heston, 13 items including full strategy proposal engine, model-state stops, EV-based sizing). Tier 3 (after signal validation, 4 items including API stages 1-3 and vol surface data product). Tier 4 (quantum research track, 2 items). Bloomberg function mapping table included.
- MERDIAN_Change_Protocol_v1.md — two-part: execution checklist (10 steps, usable at 08:45 IST under pressure) + reference standard (architectural rationale). Includes: 3-rule colour header, 4-track classification, pre-commit sanity check, rollback procedure, DEGRADED failure mode, 08:15 token refresh cadence, LOCAL_ONLY/NO_SESSION/DEGRADED failure paths.
- MERDIAN_Documentation_Protocol_v1.md — 4 rules: what triggers what kind of document, where everything lives (full directory tree), when to update, how it connects to Git. Rebuild-grade checklist included.
- MERDIAN_Session_Management_v1.md — 6 rules: 20-exchange checkpoint, 9-field resume block, one-concern-per-session, targeted context injection (Python extraction examples), session_log format, fixture capture. Context budget guide included.

**Architectural decisions made this session:**
- Dev protocol and documentation protocol are SEPARATE documents (different audiences, different cadences)
- merdian_reference.json is the operational lookup layer — docx masters remain authoritative for architecture and decisions
- Documentation governance: session note (no code) / appendix (code/schema/discovery) / minor master (3+ appendices or breaking change) / major master (phase boundary)
- Baseline reconciliation required before new protocol is operational — code and documentation both need one-time inventory and sync
- Session degradation addressed by: 20-exchange checkpoints, targeted context injection, one-concern-per-session, session_log for frictionless resume

**Strategic insights captured:**
- Heston calibration enables complete strategy proposal engine (not just BUY_PE/BUY_CE) — vertical spreads, calendars, straddles/strangles, skew trades, model-state stops, EV-based sizing
- Bloomberg function mapping: MERDIAN's calibrated vol surface = BVOL equivalent (standalone data product). Monte Carlo pricing = OVME equivalent.
- API commercial path: Stage 1 (signal polling REST), Stage 2 (WebSocket + historical), Stage 3 (strategy proposal API). Stage 1 gated on signal validation.
- Amazon Braket: relevant AFTER classical Monte Carlo proven. Insertion points: Heston calibration (annealing) + path simulation (amplitude estimation). Not actionable at current scope.
- Pre-trade cost filter (Almgren-Chriss) is Tier 1 — actionable now, uses bid/ask already in option_chain_snapshots.
- Preflight harness architecture established: 5 stages, symmetric on Local and AWS, automated at 08:30 IST with Telegram alerting.

**Files changed:** All new — no existing code modified
**Schema changes:** None
**Open items closed:** None (documentation sprint)
**Open items added:** None (V18A-01/02/03 were added in Register v3 update, not new discoveries today)
**Git commit hash:** PENDING — see Phase 7 instructions below
**Next session goal:** Code baseline reconciliation — Phase 8 (inventory Local vs Git vs AWS, classify files, resolve drifts, tag v0-baseline). Run on Local and AWS with terminal access.
**docs_updated:** yes

---

## 2026-03-31 — Documentation — V18A Appendix (Previous Session — Pre-Baseline Sprint)

**Goal:** Format APPENDIX_V18A_raw.docx into proper MERDIAN-style appendix

**Session type:** documentation

**Completed:**
- MERDIAN_Appendix_V18A_v4.docx built and validated (986 paragraphs, all validations passed)
- MERDIAN_Master_V18_v2.docx built and validated (2,530 paragraphs) — Audit-Corrected v2 with Sections 15/16/17

**Open after session:**
- Open Items Register v3 not yet built
- merdian_reference.json not yet built
- Enhancement Register not yet built
- Operational protocol documents not yet built

**Git commit hash:** PENDING
**Next session goal:** Complete documentation baseline sprint (all phases)
**docs_updated:** yes

---

## How to Add New Entries

Copy this template and prepend to the top of this file (newest first):

```markdown
## YYYY-MM-DD — [Session type] — [Topic]

**Goal:** [one sentence]
**Session type:** code_debug / architecture / documentation / live_canary / planning

**Completed:**
  - [bullet with evidence]
  - [bullet with evidence]

**Open after session:**
  - [bullet]

**Files changed:** [comma-separated, or "none"]
**Schema changes:** [describe, or "none"]
**Open items closed:** [IDs, or "none"]
**Open items added:** [IDs, or "none"]
**Git commit hash:** [hash]
**Next session goal:** [one sentence, specific]
**docs_updated:** yes / no / na
```

---

*MERDIAN Session Log — started 2026-03-31 — append newest entry at top*
