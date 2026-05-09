# MERDIAN Documentation Protocol v4

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Documentation_Protocol_v4.md` |
| Version | v4 |
| Created | 2026-03-31 (v1) · 2026-04-19 (v2 — Rule 5 numbering) · 2026-04-22 (v3 — AI-first markdown layer) · 2026-05-09 (v4 — Session 23, six reference indexes + mandatory ADR + retroactive ADR pattern) |
| Type | Governance — when/what/where to document |
| Companion | `MERDIAN_Change_Protocol_v1.md` · `MERDIAN_Session_Management_v1.md` · `MERDIAN_Testing_Protocol_v1.md` |
| Supersedes | `MERDIAN_Documentation_Protocol_v3.md` |
| Triggered by | Session 23 source-of-truth consolidation. ADR-007 (V18F ICT pivot) was the first retroactive ADR; the act of writing it surfaced gaps v3 did not address. |

---

## What changed from v3 — exhaustive changelog

> **Rule of this revision:** every change from v3 is recorded explicitly below. v3 rules that are unchanged are listed as such; rules that are modified show v3 form → v4 form; new rules and removals are flagged. No silent edits.

### Added

| Item | Detail |
|---|---|
| **Rule 9 (NEW)** — Reference indexes are first-class | Six lookup-optimized markdown indexes introduced as canonical reference layer: System Map, Deployment Topology, Decision Index, Governance Framework, Assumption Register, Disaster Rebuild Runbook. Each has location, purpose, source-of-truth status, update trigger. Replaces the v3 implicit assumption that `merdian_reference.json` + master `.docx` cover all reference needs. |
| **Rule 10 (NEW)** — ADRs are mandatory before code for specific change classes | v3 rule: "optional but recommended." v4 rule: **mandatory** before code for signal-architecture changes, deployment-topology changes, schema-affecting changes, and any reversal of a settled decision. Retroactive ADRs are accepted for pre-habit decisions (ADR-007 precedent) but not for new ones. |
| **Rule 11 (NEW)** — ADR linkage rules | Every accepted ADR mechanically (a) prepends to `MERDIAN_Decision_Index.md`, (b) cites `MERDIAN_Assumption_Register.md` if it touches an assumption, (c) contributes its one-line "Governance language" footer to `CLAUDE.md` settled-decisions list. Closes the loop between ADRs and the documents that consume them. |
| **Retroactive ADR pattern documented** | Established by ADR-007. Retroactive ADRs are acceptable for major decisions made before the ADR habit was strong. Not acceptable for new decisions of comparable scope. Recorded in Rule 10. |
| **Protocol versioning rule** | This protocol's own change log (this section) must be exhaustive. v3→v4 is the first revision held to that standard. Going forward, every protocol revision lists every change. |

### Modified

| Rule | v3 form | v4 form | Why |
|---|---|---|---|
| **Rule 1** — trigger events | Listed: session_log, session note, CURRENT.md, markdown change record, appendix.docx, master.docx, ENH register, tech_debt, ADR (optional), operational doc | Added trigger entries for: System Map, Deployment Topology, Decision Index, Assumption Register, Governance Framework, Disaster Rebuild Runbook. ADR trigger upgraded from "optional but recommended" to "mandatory for X classes." | Six new reference docs introduced in Session 23 need clear update triggers. ADR upgrade reflects ADR-007 lesson — the V18F pivot shipped without an ADR for 28 days because the protocol said ADRs were optional. |
| **Rule 2** — file layout | Listed paths under `docs/{operational, registers, session_notes, decisions, research, masters, appendices}/`. `masters/` and `appendices/` described as "PUBLISHED ARTIFACTS now — generated on demand." | Added paths for six new reference docs. Marked `masters/` and `appendices/` as **archive-only post-V19**. Added explicit note: V19 is the last Master expected under normal cadence; new Masters only on commercial milestone, not phase boundary. | Six new files need a home. Master generation cadence changed because markdown layer is now genuinely canonical (was aspirational in v3). |
| **Rule 3** — when to update | Listed: per-session, weekly, phase boundary checklists | Session-end checklist extended with: "update System Map / Deployment Topology / Decision Index / Assumption Register if any of those changed; if a new ADR was written, prepend Decision Index entry and update CLAUDE.md settled-decisions footer." | Six new files need session-end discipline equivalent to existing files. |
| **Rule 6** — `.docx` generation cadence | Triggered by phase boundary, shadow→live promotion, external review, commercial milestone, quarterly snapshot | Phase boundary trigger **demoted to optional**. Primary triggers now: external review, commercial milestone. Shadow→live promotion triggers an Appendix `.docx` only when the promotion is communicated to a stakeholder outside the development loop. | V19 is the last Master generated under v3 rules. Going forward markdown layer is canonical; Master `.docx` exists for stakeholder communication, not for development discipline. |

### Removed

Nothing was removed structurally. One trigger weakened (phase boundary as Master `.docx` trigger — see Rule 6 modification above) but the trigger remains optional. No rules deleted, no clauses dropped.

### Preserved unchanged from v3

| Rule | Status |
|---|---|
| **Rule 0** — `CLAUDE.md` is the root entry point | UNCHANGED |
| **Rule 4** — Documentation and Git (commits alongside code) | UNCHANGED |
| **Rule 5** — Numbering convention (ENH / OI / C / TD IDs) | UNCHANGED |
| **Rule 7** — `CURRENT.md` is the live session resume | UNCHANGED |
| **Rule 8** — `tech_debt.md` is persistent middle tier | UNCHANGED |
| Maintenance principles ("keep it lean", format mapping, documentation debt rule) | UNCHANGED |
| Cross-layer sync (project knowledge vs git working tree) | UNCHANGED |
| "Rebuild-grade" definition | UNCHANGED |

---

## Why this revision exists

v3 was written to demote `.docx` from working format to publication artifact and elevate markdown to canonical. That goal was met. But v3 left two gaps that Session 23 surfaced:

1. **No reference-index layer.** v3 assumed `merdian_reference.json` + master `.docx` covered all "where is X?" lookups. They don't. JSON is hard to scan; master `.docx` is locked at the version it was generated. Sessions repeatedly burnt time digging through V17/V18/V19 masters and appendices to answer questions that should have one canonical markdown source. Six new reference indexes (System Map, Deployment Topology, Decision Index, Governance Framework, Assumption Register, Disaster Rebuild Runbook) close that gap.
2. **ADRs were optional.** The V18F ICT pivot — the most significant architectural decision since V11 — shipped without an ADR. Twenty-eight days later, drafting ADR-007 retroactively required reconciling V15.1 → V19 because nine apparently-isolated reversals all stemmed from one undocumented pivot. v3's "ADR optional but recommended" wording let that happen. v4 makes ADRs mandatory for the change classes that produce that kind of damage when undocumented.

v4 is the first revision held to an exhaustive changelog standard. Going forward every protocol revision shows the full diff.

---

## Rule 0 — `CLAUDE.md` is the root entry point (UNCHANGED FROM v3)

**Location:** Repo root (`C:\GammaEnginePython\CLAUDE.md`, mirrored on AWS).

**Purpose:** Orient any new Claude session in 3 minutes. Tells Claude what MERDIAN is, where to look for what, what the non-negotiable rules are, and what NOT to reopen.

**What it contains:**
- Project one-liner
- Read order at session start (CLAUDE.md → CURRENT.md → System Map → Decision Index → tech_debt.md → Enhancement Register → JSON for targeted lookups)
- The single-source-of-truth lookup table
- Non-negotiable rules (extracted from Change Protocol)
- Session contract (one concern per session)
- Session-end checklist
- Anti-patterns to refuse
- File layout map
- Settled decisions list — auto-derived from accepted ADRs (per Rule 11)

**What it does NOT contain:**
- Detailed protocol mechanics (those live in their respective protocol files)
- File/table inventory (lives in `merdian_reference.json` and rendered in System Map)
- Architectural narrative (lives in ADRs and `.docx` masters when generated)

**Update cadence:** Whenever a non-negotiable rule, settled decision, or read-order changes. Bump version in the file's footer.

> **v3→v4 note:** Read order extended to include System Map and Decision Index. Settled decisions now sourced from ADR governance-language footers per Rule 11.

---

## Rule 1 — What triggers what kind of document (REVISED in v4)

### Session log entry — every session (UNCHANGED FROM v3)

Triggered by **every session, no exceptions**. One line in `session_log.md`:

```
YYYY-MM-DD · <git-hash> · <concern> · <PASS/FAIL/PARTIAL> · docs_updated:yes/no
```

### Session note — when investigation happened but no commit (UNCHANGED FROM v3)

Triggered by a session that did investigation but produced no code commit, no schema change, no item closure. Lightweight markdown, 10–30 lines, in `docs/session_notes/YYYYMMDD_<topic>.md`.

### `CURRENT.md` overwrite — every session (UNCHANGED FROM v3)

Triggered by **every session that does anything substantive**. Update "Last session" block to reflect what just happened. Reset "This session" block for next.

### Markdown change record — when code/schema/items change (UNCHANGED FROM v3)

Triggered by a session that changed any file, table, or item status. Update `merdian_reference.json` and (if applicable) `tech_debt.md` and `Enhancement Register` in the same commit as the code change.

### System Map update — when files/tables/runners/orchestration change (NEW IN v4)

Triggered by any change to: production scripts (location, reads-from, writes-to, called-by, status), live operational tables (DDL, write-path, read-path), 5-min cycle / 1-min cycle / pre-market / post-market pipeline ordering, Task Scheduler / cron orchestration. Update inline in same commit as the code change.

### Deployment Topology update — when AWS↔Local boundaries shift (NEW IN v4)

Triggered by any change to: what runs on Local-only, what runs on AWS-only, what runs on both, cron entries (AWS), Task Scheduler entries (Local), token flow, runtime artifacts, AWS gotchas list.

### Decision Index entry — every accepted ADR (NEW IN v4)

Triggered by every accepted ADR. Mechanically prepended to `MERDIAN_Decision_Index.md` per Rule 11. Single row: ID, date, topic, decision one-liner, rationale one-liner, rejected alternative, source link.

### Assumption Register update — when an assumption is validated, refuted, or refreshed (NEW IN v4)

Triggered by experimental evidence that confirms, refutes, or supersedes an assumption recorded in the register. Update the assumption row inline; do not delete superseded assumptions — annotate them with the experiment that resolved them. Replaces the V15.1 Appendix D pattern of static assumption capture.

### Governance Framework — when a governance rule changes (NEW IN v4)

Triggered by any change to: Measure→Validate→Shadow→Promote framework, Four Key Evidence Questions, Walk-Forward methodology, Do-NOT-Revive list. Frequency: rare. Increment version in the file's footer.

### Disaster Rebuild Runbook — when rebuild dependencies change (NEW IN v4)

Triggered by: new infrastructure (broker API, scheduler, secrets store), DDL of a load-bearing table, supervisor / runner / dashboard substitution, environment variable additions. Update inline. Annual review at minimum.

### Case-study file — when a session-defining failure event is diagnosed (NEW IN v4)

Triggered by a single-event diagnosis worth permanent record (precedent: 11 March 2026 case study). Single file at `docs/decisions/CASE-YYYY-MM-DD-<topic>.md`. Captures: observed state, root-cause analysis, implications, link to remediation ADR.

### Appendix `.docx` — only at external need (REVISED IN v4)

> **v3 form:** Triggered by phase boundary, external review, quarterly snapshot, or 30+ session_log accumulation.
> **v4 form:** Phase-boundary trigger demoted to optional. Primary triggers now: external review request, shadow→live promotion communicated outside the development loop, commercial milestone.

### Master `.docx` — only at commercial milestone (REVISED IN v4)

> **v3 form:** Triggered by fundamental architectural change, commercial milestone, accumulated minor activity, or quarterly cadence.
> **v4 form:** Primary trigger is commercial milestone. Architectural changes are documented via ADRs and the markdown reference layer; a new Master is not required.

V19 is the last Master expected under normal cadence. Future Masters are stakeholder communication artifacts.

### Enhancement Register update — when architectural thinking happens (UNCHANGED FROM v3)

Update in same session as the thinking. ENH-N IDs.

### `tech_debt.md` update — when known broken-ish things change (UNCHANGED FROM v3)

Update inline as items are added, mitigated, severity-changed, or closed. Use `TD-N` IDs.

### ADR — when an architectural decision is made (REVISED IN v4)

> **v3 form:** Optional but recommended. "Each significant architectural decision gets a small markdown file."
> **v4 form:** **Mandatory before code** for the change classes listed in Rule 10. See Rule 10 and Rule 11 for full mechanics.

### Operational document update — when a protocol changes (UNCHANGED FROM v3, except changelog requirement)

Increment version number, never overwrite. **NEW in v4:** Every revision must include an exhaustive changelog showing all additions, modifications, removals, and items preserved unchanged. v3→v4 is the first revision held to this standard.

---

## Rule 2 — Where every document lives (REVISED IN v4)

```
C:\GammaEnginePython\
(mirrored at /home/ssm-user/meridian-engine/ via git pull)

  CLAUDE.md                                         ← Rule 0: root AI entry point

  docs/
    operational/
      MERDIAN_Change_Protocol_v1.md
      MERDIAN_Documentation_Protocol_v4.md          ← THIS FILE
      MERDIAN_Session_Management_v1.md
      MERDIAN_Testing_Protocol_v1.md
      MERDIAN_Governance_Framework.md               ← NEW v4: M→V→S→P + 4 evidence Qs + walk-forward + Do-NOT-Revive

    registers/
      merdian_reference.json                        ← machine-queryable inventory
      MERDIAN_Enhancement_Register_v<n>.md
      tech_debt.md                                  ← persistent middle-tier
      MERDIAN_OpenItems_Register_v7.md              ← CLOSED 2026-04-15, retained as audit
      MERDIAN_System_Map.md                         ← NEW v4: file/table/runner/orchestration index
      MERDIAN_Deployment_Topology.md                ← NEW v4: AWS↔Local boundaries
      MERDIAN_Assumption_Register.md                ← NEW v4: derived from V15.1 Appendix D, refreshed for ICT-era

    runbooks/                                       ← step-by-step procedures
      README.md                                     ← index of all runbooks
      RUNBOOK_TEMPLATE.md                           ← template for new runbooks
      runbook_disaster_rebuild.md                   ← NEW v4: cold-rebuild blueprint, current architecture
      runbook_*.md

    session_notes/
      CURRENT.md                                    ← live session resume
      session_log.md                                ← append-only one-liner per session
      YYYYMMDD_<topic>.md                           ← per-session detail (rare)

    decisions/                                      ← ADRs (mandatory per Rule 10)
      MERDIAN_Decision_Index.md                     ← NEW v4: flat lookup index, prepended on each accepted ADR
      ADR-001-stable-lies-defeat-duration-gates.md
      ADR-002-market-structure-philosophy.md
      ADR-007-v18f-ict-pivot.md                     ← retroactive ADR (Session 23)
      CASE-YYYY-MM-DD-<topic>.md                    ← NEW v4: case-study file pattern (e.g. CASE-2026-03-11)
      ...

    research/
      MERDIAN_Experiment_Compendium_v<n>.md
      merdian_all_experiment_results.md

    masters/                                        ← .docx — ARCHIVE-ONLY post-V19
      MERDIAN_Master_V<n>.docx                      ← V19 is the last under normal cadence

    appendices/                                     ← .docx — ARCHIVE-ONLY post-V19
      MERDIAN_Appendix_V<n>.docx
```

**Format rules:**
- `.md` for everything in operational/, registers/, runbooks/, session_notes/, decisions/, research/
- `.json` for `merdian_reference.json` (machine-queryable, fastest to update)
- `.docx` only for masters/ and appendices/, and only when a stakeholder outside the development loop requires one — V19 is the current and likely final Master under normal development cadence

> **v3→v4 note:** Six new files added to the layout. `masters/` and `appendices/` marked archive-only post-V19. No paths removed.

---

## Rule 3 — When to update (REVISED IN v4 — additions only)

### During every development session (UNCHANGED FROM v3)
```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update tech_debt.md if a TD item changes
```

### At session end before closing (REVISED IN v4)
```
☐ Overwrite CURRENT.md (Last session reflects this session, This session reset)
☐ Append one line to session_log.md
☐ Update Enhancement Register if architectural thinking happened
☐ Update System Map if file/table/runner/orchestration changed                    ← NEW v4
☐ Update Deployment Topology if AWS↔Local boundary changed                        ← NEW v4
☐ If a new ADR was written:                                                       ← NEW v4
    ☐ prepend entry to MERDIAN_Decision_Index.md
    ☐ append governance-language one-liner to CLAUDE.md settled-decisions
    ☐ if it touches an assumption: update MERDIAN_Assumption_Register.md
☐ Commit all documentation changes to Git
☐ Re-upload modified files to Claude.ai project knowledge (per CLAUDE.md Rule 12)
```

### Weekly (or after 3+ development sessions) (UNCHANGED FROM v3)
```
☐ Review Enhancement Register for stale PROPOSED items
☐ Review tech_debt.md for items that should escalate to ENH or close
```

### At phase boundaries (REVISED IN v4)
```
☐ Generate appendix .docx from the markdown layer ONLY if external communication required
☐ If commercial milestone: generate Master .docx (otherwise the markdown layer is sufficient)
☐ Tag Git: git tag docs-v<version>
```

> **v3→v4 note:** Phase boundary no longer auto-triggers `.docx` generation. Tag is still produced.

---

## Rule 4 — Documentation and Git (UNCHANGED FROM v3)

### 4.1 Documentation commits alongside code
Every code commit that changes system behaviour has a corresponding documentation commit in the same push or the immediately following push.

```
MERDIAN: [OPS] tech_debt.md — TD-007 added
MERDIAN: [OPS] merdian_reference.json — file statuses updated
MERDIAN: [OPS] CURRENT.md — session 2026-MM-DD recorded
MERDIAN: [OPS] System Map — runner orchestration updated
MERDIAN: [OPS] Decision Index — ADR-007 entry prepended
```

### 4.2 No major Master without register update
The Open Items Register (closed) and Enhancement Register and `tech_debt.md` and (NEW v4) System Map and Decision Index must be at current state before any Master `.docx` is generated.

### 4.3 Documentation tags
```bash
git tag docs-v<version>
git push --tags
```

> **v3→v4 note:** Section 4.2 extended to include System Map and Decision Index in the pre-Master checklist. Two example commit prefixes added in Section 4.1. Substance of all three subsections unchanged.

---

## Rule 5 — Numbering convention (UNCHANGED FROM v3)

### ENH IDs
Monotonic integers in `MERDIAN_Enhancement_Register_v*.md`. Pick next-free. IDs permanent. REJECTED items keep their ID as a rejection record.

### OI IDs
**No new `OI-*` prefixes.** OpenItems Register closed 2026-04-15. Persistent items go to Enhancement Register or `tech_debt.md`. Historical OI-* entries retained in JSON as audit trail.

### C IDs (critical)
Tracked in `merdian_reference.json` `open_items`. Mid-session production bugs that must close before moving on. Monotonic integers.

### TD IDs (tech debt)
Tracked in `tech_debt.md`. Monotonic integers (TD-001, TD-002, ...). Use for known broken-ish items with workarounds — neither blocking (C-N) nor forward-looking proposals (ENH-N).

### ADR IDs (NEW emphasis in v4)
Monotonic integers in `docs/decisions/ADR-NNN-<short-kebab-topic>.md`. Pick next-free. IDs permanent. Reserved ranges may exist (e.g. ADR-003/004/005/006 reserved for pending decisions per CLAUDE.md). Retroactive ADRs use the next-free non-reserved ID; ADR-007 is the precedent.

### CASE IDs (NEW IN v4)
Date-stamped: `CASE-YYYY-MM-DD-<topic>.md` in `docs/decisions/`. No monotonic numbering — the date is the identifier. Used for single-event case studies.

### Session-specific tracking
Record in `CURRENT.md` checkpoints or `session_log.md` only. Do not create persistent IDs.

### Where to put what — quick reference (REVISED IN v4)

| Item type | Location |
|---|---|
| Forward-looking enhancement, persistent | Enhancement Register (ENH-N) |
| Critical production bug, must fix soon | `merdian_reference.json` `open_items` (C-N) |
| Known broken-ish, has workaround, persistent | `tech_debt.md` (TD-N) |
| Session-specific task, does not persist | `CURRENT.md` checkpoint or `session_log.md` |
| Architectural decision (mandatory for change classes in Rule 10) | `docs/decisions/ADR-NNN-<topic>.md` |
| Single-event failure case study | `docs/decisions/CASE-YYYY-MM-DD-<topic>.md` |
| File/table/runner inventory lookup | `MERDIAN_System_Map.md` |
| AWS↔Local boundary lookup | `MERDIAN_Deployment_Topology.md` |
| Decision history quick lookup | `MERDIAN_Decision_Index.md` |
| Unvalidated assumption | `MERDIAN_Assumption_Register.md` |
| Governance rule | `MERDIAN_Governance_Framework.md` (rare changes) |
| Cold-rebuild procedure | `docs/runbooks/runbook_disaster_rebuild.md` |
| Protocol/process rule | Operational protocol file (increment version, exhaustive changelog) |

> **v3→v4 note:** Six new rows added to the lookup table. CASE ID convention added. Existing rows unchanged.

---

## Rule 6 — `.docx` is archive-only post-V19 (REVISED IN v4)

> **v3 form:** `.docx` Masters and Appendices are published artifacts, generated on demand at phase boundaries, external reviews, or commercial milestones.
> **v4 form:** V19 is the last Master expected under normal development cadence. The markdown layer (CLAUDE.md + System Map + Decision Index + Governance Framework + Assumption Register + tech_debt + Enhancement Register + ADRs + session_log + experiment compendium) is fully canonical and rebuild-grade on its own. Future `.docx` generation is reserved for stakeholder communication outside the development loop — external audit, investor, regulator, commercial milestone — not for internal development discipline.

### When to generate (REVISED v4)

| Trigger | Output |
|---|---|
| External audit / investor / regulator request | Master + relevant appendices `.docx` |
| Commercial milestone (first paying customer) | Master `.docx` |
| Shadow → live promotion communicated to outside stakeholder | Appendix `.docx` for the promotion |
| Phase boundary | **Optional, no longer required** — markdown layer captures phase transitions via ADRs and System Map updates |
| Quarterly snapshot | **Optional** |

### How to generate (UNCHANGED FROM v3)

1. **Identify the period** (since last `.docx`)
2. **Pull from sources:**
   - Architectural narrative → `CLAUDE.md` settled-decisions + ADRs in `docs/decisions/`
   - File/table inventory → `MERDIAN_System_Map.md` (NEW v4 source) + `merdian_reference.json`
   - AWS↔Local topology → `MERDIAN_Deployment_Topology.md` (NEW v4 source)
   - Decision history → `MERDIAN_Decision_Index.md` (NEW v4 source)
   - Session history → `session_log.md` lines for the period
   - Enhancement state → current Enhancement Register markdown
   - Tech debt state → current `tech_debt.md`
   - Experiment results → Experiment Compendium markdown
3. **Render to `.docx`** using a script (e.g. `pandoc` or `python-docx` template).
4. **Commit** the generated `.docx` to `docs/masters/` or `docs/appendices/`.
5. **Tag** `git tag docs-v<version>`.

The point: the markdown is the source. The `.docx` is the publish step. If they drift, the markdown wins and the `.docx` gets regenerated.

> **v3→v4 note:** Three new sources added to the pull list (System Map, Deployment Topology, Decision Index). Generation mechanics unchanged. Trigger list pared down — phase boundary and quarterly snapshot are now optional.

---

## Rule 7 — `CURRENT.md` is the live session resume (UNCHANGED FROM v3)

**Location:** `docs/session_notes/CURRENT.md`

**Purpose:** Replace the practice of pasting a "session resume block" at the start of every chat. Claude reads `CURRENT.md` after `CLAUDE.md` and has full session resume context without any human paste.

**Contents:**
- "Last session" block — what just happened
- "This session" block — goal, type, success criterion, relevant files/tables/items, DO_NOT_REOPEN list
- Live state snapshot — env health, open critical items, active ENH in flight
- Mid-session checkpoint slots (per Session Management Rule 1)
- Session-end checklist

**Update cadence:** Overwrite at the end of every substantive session. Never branch this file. Never archive it (the `session_log.md` is the archive).

---

## Rule 8 — `tech_debt.md` is the persistent middle tier (UNCHANGED FROM v3)

**Location:** `docs/registers/tech_debt.md`

**Purpose:** Track persistent known issues that don't fit the C-N (critical) or ENH-N (forward-looking) buckets.

**Lifecycle:**
1. Discover an issue mid-session that isn't blocking but shouldn't be forgotten
2. Add as `TD-NNN` with severity (S1–S4), workaround, proper-fix sketch, blocked-by, owner-check-in date
3. Update inline as workaround changes or root cause is learned
4. Close by moving to "Resolved (audit trail)" section with closing commit hash
5. Promote to C-N if it becomes blocking, or to ENH-N if it grows into a real proposal

**Severity:**
- **S1** Production-impacting workaround in place. Within 5 sessions.
- **S2** Non-blocking but degrades real workflow. Within 15 sessions.
- **S3** Cosmetic / performance-tolerable / edge cases. When convenient.
- **S4** Anti-pattern flagged for future refactor. Aspirational.

**Anti-pattern section:** `tech_debt.md` ends with a list of patterns to avoid. Reviewed in CLAUDE.md by reference.

---

## Rule 9 — Reference indexes are first-class (NEW IN v4)

The markdown layer has six lookup-optimized reference files. Each is canonical for its concern, kept current as part of the session-end discipline (Rule 3), and stable enough that Claude reads them at session start to ground every decision.

### 9.1 `MERDIAN_System_Map.md` (`docs/registers/`)

**Purpose:** Single answer to "what lies where, what writes to what, what calls what." Replaces digging through V17/V18/V19 master appendices.

**Contents (sections):**
- §A Script Index — every active production script with local_path, aws_path, reads_from, writes_to, called_by, cadence, status
- §B Table Index — every live operational table with written_by, read_by, unique_key, DDL link, contamination notes
- §C Cycle Pipeline Diagrams — 1-min tape, 5-min options, AWS shadow, pre-market, post-market
- §D Orchestration Index — Task Scheduler tasks, AWS cron entries, supervisor responsibilities
- §E Monitoring & Runtime — health-check thresholds, telemetry files, heartbeat schema
- §F Core abstractions — `core/config.py`, `core/supabase_client.py`, `core/dhan_client.py` function signatures

**Update trigger:** Any change to scripts, tables, pipeline ordering, or orchestration (Rule 1).

### 9.2 `MERDIAN_Deployment_Topology.md` (`docs/registers/`)

**Purpose:** Single answer to "what runs on Local vs AWS." Replaces scattered V18 §15.4/15.5 + V18A §13.5 + V18E §7.4/7.5 + CLAUDE.md gotchas.

**Contents:**
- §1 Side-by-side Local vs AWS table
- §2 Local-only scripts list
- §3 AWS-only scripts list
- §4 Both-environments scripts list
- §5 Token flow diagram
- §6 AWS gotchas (DO NOT)
- §7 Cron specification + Task Scheduler XML inventory
- §8 Runtime artifacts per environment

**Update trigger:** Any AWS↔Local boundary change (Rule 1).

### 9.3 `MERDIAN_Decision_Index.md` (`docs/decisions/`)

**Purpose:** Flat lookup table of every architectural decision. Each ADR mechanically prepends here. Used for "have we decided this already?" checks at session start.

**Contents:** One row per decision: ID, date, topic, decision one-liner, rationale one-liner, rejected alternative, source link.

**Update trigger:** Every accepted ADR. Mechanical — not authored, generated from the ADR's metadata header (Rule 11).

### 9.4 `MERDIAN_Governance_Framework.md` (`docs/operational/`)

**Purpose:** Consolidate the governance rules V19 says are non-superseded but which were locked inside `.docx` masters: Measure→Validate→Shadow→Promote, Four Key Evidence Questions, Walk-Forward Validation, Do-NOT-Revive list.

**Contents:**
- Pulled verbatim from V16 §3 (M→V→S→P), V16 §3.3 (Four Questions), V16 §3.6 (Walk-Forward)
- Do-NOT-Revive list pulled from V15.1 §18.1 + V16 §25.1
- ADR-001 cross-reference (validity layer is part of the governance)

**Update trigger:** Rare. Any change to a governance rule. Increment version in the file's footer with exhaustive changelog (per Rule 1).

### 9.5 `MERDIAN_Assumption_Register.md` (`docs/registers/`)

**Purpose:** Living version of V15.1 Appendix D. Records every unvalidated design decision, links to the experiment that validated/refuted/superseded it.

**Contents:**
- Signal Engine assumptions (refreshed for ICT-era post ADR-007)
- Breadth Engine assumptions
- Gamma Regime assumptions (largely intact post ADR-007)
- Momentum assumptions (largely refreshed post ADR-007)
- Volatility assumptions
- Each row: assumption, how set, status (LIVE / VALIDATED / SUPERSEDED / REFUTED), evidence link

**Update trigger:** Experimental evidence that confirms/refutes/supersedes an assumption (Rule 1). Superseded assumptions are annotated, not deleted — preserves audit trail.

### 9.6 `runbook_disaster_rebuild.md` (`docs/runbooks/`)

**Purpose:** Cold-rebuild blueprint for the current architecture. Promotes V15.1/V16 Appendix A to current-state.

**Contents:**
- Prerequisites (AWS, Supabase, Dhan, Zerodha credentials; local Windows; Git)
- Sequence: clone → env → core test → schema → data backfill → runner start → ICT layer → execution layer → validation
- Per-step expected output
- Rollback points

**Update trigger:** Any change to rebuild dependencies (new infrastructure, schema changes, supervisor/runner changes) (Rule 1).

---

## Rule 10 — ADRs are mandatory before code (NEW IN v4)

> **v3 form:** "Optional but recommended."
> **v4 form:** Mandatory before code for the change classes below. v3's permissive wording allowed the V18F ICT pivot — the most consequential architectural decision since V11 — to ship without an ADR. ADR-007 was written 28 days later under reconstruction conditions. v4 prevents recurrence.

### Mandatory ADR triggers

An ADR must be drafted (Status: Proposed) before code lands for any of:

- **Signal architecture changes** — anything affecting how signals are triggered, scored, gated, or sized. Includes new pattern types, new gates, threshold changes that move beyond the "tune within range" interpretation, sizing-model changes.
- **Deployment topology changes** — anything moving a script between Local and AWS, changing the broker API used for a data class, changing the scheduler ownership, or introducing a new infrastructure dependency.
- **Schema-affecting changes** — anything adding/removing/restructuring a load-bearing table or its primary write contract. (Ad-hoc columns, indexes, and audit tables exempt.)
- **Reversal of a settled decision** — anything that lifts or inverts a rule recorded in CLAUDE.md "settled decisions" or in the Decision Index. The ADR documents the new evidence.

### Not required (use ENH-N or TD-N instead)

- Tuning a parameter within an already-validated range
- Bug fixes
- Refactoring without behavioral change
- Operational tooling additions (dashboards, runbooks, audit scripts)
- Experimental work (lives in Experiment Compendium until findings produce an architectural change, at which point the ADR captures the change)

### Retroactive ADRs

Acceptable for major decisions made before the ADR habit was strong. ADR-007 (V18F ICT pivot, decided 2026-04-11/12, documented 2026-05-09) is the precedent. Retroactive ADRs:
- Use Status: `Accepted (retroactive)`
- Carry both `Date decided` and `Date documented` in the metadata header
- Are NOT acceptable for new decisions of comparable scope going forward

### ADR template

Match ADR-001 / ADR-002 / ADR-007 format:

```
# ADR-NNN — <short title>: <one-line decision essence>

| Field | Value |
|---|---|
| Status | Proposed | Accepted | Accepted (retroactive) | Rejected | Superseded |
| Date | YYYY-MM-DD |
| Session | Session N |
| Supersedes | <prior decisions if any>
| Related ENH / TD / commits | ...

## Context
## Decision
## Evidence (or Rationale for non-data-driven decisions)
## Alternatives considered
## Consequences (positive / negative / mitigations)
## Relationship to other documents
## Governance language (one-line compressed form for CLAUDE.md settled-decisions)
## Open follow-ups

*ADR-NNN — YYYY-MM-DD — Session N — closing note.*
```

---

## Rule 11 — ADR linkage rules (NEW IN v4)

Every accepted ADR closes the loop with three downstream documents. The closure is mechanical — done in the same commit as the ADR acceptance.

### 11.1 Decision Index entry — mandatory

A new row prepends to `docs/decisions/MERDIAN_Decision_Index.md`. Sourced from the ADR's metadata header and "Governance language" footer:

| Column | Source in ADR |
|---|---|
| ID | `# ADR-NNN —` line |
| Date | metadata Date row |
| Topic | title second half |
| Decision | one-line summary of the Decision section |
| Rationale | one-line summary of Evidence/Rationale |
| Rejected | one-line summary of strongest rejected alternative |
| Source link | filename of the ADR |

### 11.2 Assumption Register update — conditional

If the ADR validates, refutes, or supersedes an assumption recorded in `MERDIAN_Assumption_Register.md`, update that assumption row inline. Mark superseded assumptions with a `SUPERSEDED by ADR-NNN` annotation; do not delete.

### 11.3 CLAUDE.md settled-decisions footer — mandatory

The ADR's "Governance language" one-line compressed form appends to CLAUDE.md's settled-decisions list. This is the form that future sessions will encounter at the top of every session. ADRs without a clean one-line governance footer are not ready for acceptance.

### 11.4 Order of operations at ADR acceptance

```
1. ADR moves Status: Proposed → Accepted (or Accepted retroactive)
2. Decision Index row prepended
3. Assumption Register updated (if applicable)
4. CLAUDE.md settled-decisions appended
5. Single commit with all four files: MERDIAN: [OPS] ADR-NNN accepted, downstream updates
```

---

## Maintenance principles (UNCHANGED FROM v3)

### Keep it lean
Do not add sections that are not used. The 13-block appendix structure exists because all 13 blocks are needed for rebuild-grade. Same applies to CLAUDE.md sections, tech_debt.md fields, etc.

### Markdown for working state, .docx for published state, .json for machine queries
- Working operational state: `.md` (frequently updated, readable diffs, AI-readable)
- Published rebuild-grade artifacts: `.docx` (structured, formatted, narrative-heavy)
- Machine-queryable lookup: `.json`

### The documentation debt rule
If `session_log.md` shows three consecutive entries with `docs_updated: no`, there is documentation debt. Address it before any new code work. Documentation debt compounds.

---

## Cross-layer sync (UNCHANGED FROM v3)

Local git commits do NOT auto-sync to Claude.ai project knowledge. The two layers drift independently:

- `git commit` updates the local working tree and (after `git push`) origin
- Project knowledge upload is a separate manual step in the Claude.ai UI

A session is not closed until both destinations have the new state. If only git is updated, the next session's Claude reads stale project knowledge and either invents a different goal (bad) or correctly flags the discrepancy and refuses to proceed (acceptable but loses session time). See CLAUDE.md Rule 12 for the mandatory re-upload list.

This was first observed Session 6 → Session 7 (2026-04-22).

---

## What "rebuild-grade" means (UNCHANGED FROM v3)

A document is rebuild-grade when:
```
☐ A developer with no prior context can reconstruct the system state from it alone
☐ Every file touched is accounted for with full path, reads, writes, status
☐ Every table created or modified is accounted for with row count or state
☐ Every API contract is documented with actual observed values, not descriptions
☐ Every known wrong thing is explicitly flagged
☐ Rejected alternatives are documented (not just what was decided, but why)
☐ The resume prompt allows continuation without re-reading the whole document
```

In v4, "rebuild-grade" is a property of the **markdown layer as a whole** (CLAUDE.md + System Map + Deployment Topology + Decision Index + Governance Framework + Assumption Register + tech_debt + Enhancement Register + ADRs + session_log + experiment compendium + JSON). When a `.docx` is generated, it inherits rebuild-grade from the markdown it was assembled from.

---

*MERDIAN Documentation Protocol v4 — supersedes v3. Commit to Git. Do not modify without updating version number AND providing exhaustive changelog of changes from prior version. v3→v4 is the first revision held to the exhaustive-changelog standard; v4→v5 and beyond inherit it.*
