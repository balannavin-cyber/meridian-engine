# MERDIAN Documentation Protocol v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Documentation_Protocol_v2.md |
| Version | v2 |
| Created | 2026-03-31 (v1) |
| Updated | 2026-04-19 (v2 -- Rule 5 numbering convention added) |
| Type | Governance — when/what/where to document |
| Companion | MERDIAN_Change_Protocol_v1.md · MERDIAN_Session_Management_v1.md |

---

## Purpose

This document answers four questions:

1. What triggers which kind of document?
2. Where does every document live?
3. When must it be updated?
4. How does documentation connect to the Git protocol?

Without these answers, documentation happens by feel — which is why MERDIAN has had gaps between what the register says and what the system actually is.

---

## Rule 1 — What Triggers What Kind of Document

### Session Note

**Triggered by:** A development session where investigation occurred but no code was committed, no schema was changed, and no open item was closed.

**What it is:** A lightweight record — not a full block structure. Date, what was investigated, what was not resolved, what the next step is.

**Format:** Free-form markdown, 10–30 lines.

**Location:** `docs/session_notes/YYYYMMDD_<topic>.md`

**Example triggers:**
- A session spent diagnosing a failure that could not be fixed that day
- An architecture planning session with no code output
- A holiday session (like 2026-03-31) that produces decisions but no code

---

### Appendix

**Triggered by:** A development session that produces ANY of:

```
☐ A new file created or materially modified
☐ A schema change (new table, new column, new constraint, new index)
☐ A bug fixed with a confirmed root cause
☐ A new validated component added to the system
☐ An open item closed with evidence
☐ A new architectural discovery with operational consequences
```

**One session = one appendix.** If a session produces multiple items from the list, they all go into one appendix for that session.

**What it must contain (13-block structure):**

| Block | Content |
|---|---|
| 1 | Session identity — objective, secondary items, parent docs, versioning |
| 2 | Before/after boundary — what existed, what was discovered, what changed |
| 3 | File inventory — every file touched with full path, reads, writes, status |
| 4 | Table inventory — every table created/modified/confirmed with state |
| 5 | Exact schemas — DDL or confirmed column lists for new/modified tables |
| 6 | API and capture contracts — observed values, failures, meanings |
| 7 | Execution chain / pipeline diagram |
| 8 | Validation results — evidence, not just "worked" |
| 9 | Known failure modes and fixes — symptom → root cause → fix |
| 10 | Decision log — what was decided and why alternatives were rejected |
| 11 | Stable vs incomplete state — do not re-investigate vs known gaps |
| 12 | Resume checkpoint — settled facts, next task, paste-ready resume prompt |
| 13 | Functional narration — why the system works the way it does |

**What "rebuild-grade" means:** A developer with no prior context can reconstruct the system state from the appendix alone, without asking any questions.

**Location:** `docs/appendices/MERDIAN_Appendix_<version>.docx`

**Format:** MERDIAN-style docx (Node.js + docx library, colored callout boxes, data tables, pipeline diagrams in monospaced font, section-level governance markers). Follow existing appendix style from V17A v2 through V18A v4.

---

### Minor Master Increment

**Triggered by ANY of:**

```
☐ 3 or more appendices accumulated since last master
☐ One appendix that changes a core architectural component
☐ A breaking change (as defined in Change Protocol)
☐ A major open item category closed
```

**What it is:** A compilation and synthesis of accumulated appendices into the master. Not just concatenation — adds:
- Master Reference Matrices (Section 15 pattern) updated to current state
- Functional Narration (Section 16 pattern) updated with new Block 13 content
- Decision Registry (Section 17 pattern) updated with new decisions
- All status tables and inventories updated

**Naming:** V18 → V18.1 → V18.2, or V18 → V19 depending on scope (see Major Master below).

**Location:** `docs/masters/MERDIAN_Master_V<version>.docx`

---

### Major Master Increment

**Triggered by ANY of:**

```
☐ A phase boundary crossed (e.g. shadow runner wired and validated, Heston calibration layer live)
☐ A commercial milestone (e.g. API first paying customer)
☐ A fundamental architectural change (e.g. Monte Carlo pricing live, strategy proposal engine replacing signal engine)
☐ Accumulated minor increments make the document unwieldy (>30 appendices since last major)
```

**What it adds over minor:** In addition to all minor increment content, a major master adds:
- A new architectural narrative section explaining the system's current capabilities end-to-end
- An updated Phase Roadmap section
- A revised commercial context section if applicable
- Full re-audit of all reference matrices, governance rules, and decision registry

---

### Enhancement Register Update

**Triggered by:** Any chat or session that produces architectural thinking about MERDIAN's future direction. This includes architecture planning sessions, commercial viability discussions, and research explorations (Heston, Monte Carlo, quantum, API design).

**What it is:** The forward-looking register of proposed improvements. Not a session record — a living list of enhancements with their status, dependencies, and commercial relevance.

**When to update:** In the same session that produces the thinking. If you wait until "later," the nuance is lost.

**Location:** `docs/registers/MERDIAN_Enhancement_Register_v1.md`

---

### Operational Document Update

**Triggered by:** Any change to the protocols themselves — when the Change Protocol, Documentation Protocol, or Session Management document needs to be updated because a rule has changed or a new rule has been established.

**Naming:** Increment version number: `MERDIAN_Change_Protocol_v2.md`. Never overwrite — keep prior versions in Git history.

**Location:** `docs/operational/`

---

## Rule 2 — Where Every Document Lives

All documentation lives in Git under `/docs/`. Nothing lives only on your local system. Nothing lives only in your head.

```
C:\GammaEnginePython\docs\
(mirrored at /home/ssm-user/meridian-engine/docs/ via git pull)

docs/
  masters/
    GammaEngine_Master_V15_1.docx
    MERDIAN_Master_V16_Fixed.docx
    MERDIAN_Master_V17.docx
    MERDIAN_Master_V18_v2.docx
    MERDIAN_Master_V<next>.docx       ← add when triggered

  appendices/
    MERDIAN_Appendix_V16A_v2.docx
    MERDIAN_Appendix_V16B.docx
    MERDIAN_Appendix_V16C_v2.docx
    MERDIAN_Appendix_V16D.docx
    MERDIAN_Appendix_V16E_v2.docx
    MERDIAN_Appendix_V17A_v2.docx
    MERDIAN_Appendix_V17B_v2.docx
    MERDIAN_Appendix_V17C.docx
    MERDIAN_Appendix_V17D.docx
    MERDIAN_Appendix_V17D1_v2.docx
    MERDIAN_Appendix_V17E_v2.docx
    MERDIAN_Appendix_V18A_v4.docx
    MERDIAN_Appendix_V<next>.docx     ← add when triggered

  registers/
    MERDIAN_OpenItems_Register_v3.docx
    MERDIAN_Enhancement_Register_v1.md
    merdian_reference.json

  operational/
    MERDIAN_Change_Protocol_v1.md     ← this companion doc
    MERDIAN_Documentation_Protocol_v1.md  ← this document
    MERDIAN_Session_Management_v1.md  ← the third companion doc

  session_notes/
    session_log.md                    ← running log of all sessions
    YYYYMMDD_<topic>.md               ← individual session notes
```

**Key rules:**
- `.docx` files are binary in Git — diffs are not readable, but version history and existence are tracked
- `.md` and `.json` files have readable diffs — use these for frequently updated documents
- Operational protocol documents are `.md` not `.docx` — they change more often and need readable diffs
- The Enhancement Register is `.md` for the same reason

---

## Rule 3 — When to Update

### During every development session:

```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update Open Items Register: close what closed, add what was found
```

### At session end (before closing):

```
☐ Write session note OR appendix (see triggers above)
☐ Update Enhancement Register if architectural thinking occurred
☐ Append to session_log.md
☐ Commit all documentation changes to Git
```

### Weekly (or after 3+ development sessions):

```
☐ Review whether minor master increment is triggered (3+ appendices)
☐ Review Enhancement Register for stale PROPOSED items
```

### At phase boundaries:

```
☐ Write major master increment
☐ Archive prior appendices as compiled
☐ Tag Git with documentation version: git tag docs-v<version>
```

---

## Rule 4 — Documentation and Git

Three connections between documentation and the Git protocol:

### 4.1 Documentation Commits Alongside Code

Every code commit that changes system behaviour should have a corresponding documentation commit in the same push or the immediately following push. This is not a separate workflow — it is the same push, or if there is insufficient time, the next push within the same session.

```
MERDIAN: [OPS] Open Items Register v3 — C-01 status updated
MERDIAN: [OPS] merdian_reference.json — V18A file statuses updated
MERDIAN: [OPS] Appendix V18A v4 — session record committed
```

### 4.2 No Major Master Without Register Update

Before any major master version is committed, the Open Items Register must be updated to current state. The two documents must be temporally consistent.

### 4.3 Documentation Tags

When a new master is committed:

```bash
git tag docs-v18-v2
git push --tags
```

This links code state and documentation state at a specific point in time.

---

## Rule 5 -- Numbering Convention for ENH and C Items

Adopted 2026-04-19 after V18H_v2 (2026-04-17/18) created ENH IDs
colliding with `Enhancement_Register_v7` and OI IDs violating the
`OpenItems_Register` permanent closure from 2026-04-15.

### Background

`MERDIAN_OpenItems_Register_v7.md` was permanently closed 2026-04-15 with
the directive: "New operational issues will be tracked in the Enhancement
Register or session appendices." This rule operationalises that closure.

### ENH IDs

- Monotonic integers in `MERDIAN_Enhancement_Register_v*.md` (ENH-01,
  ENH-02, ...).
- When adding: use the next free integer. Before adding, verify against
  the latest register version AND
  `docs/registers/merdian_reference.json` `open_items` keys.
- IDs are permanent. REJECTED items keep their ID as a rejection
  record -- never reuse a rejected ID for a different proposal.

### OI IDs

- **No new OI-* prefixes may be created.** OpenItems Register is closed.
  This includes plain `OI-N`, `RESEARCH-OI-N`, `SPO-N`, and any similar
  new operational prefixes.
- Where V18H_v2 or similar appendices have already introduced OI-*
  items, those items migrate into the Enhancement Register (folded into
  an existing or new ENH) with a note in the appendix errata file.
- Historical OI-* entries in `merdian_reference.json` `open_items` (from
  the pre-closure era) are retained as audit trail and not deleted.

### C IDs (critical)

- `C-N` critical fixes remain tracked in `merdian_reference.json`
  `open_items`. C IDs serve a different role from ENH: mid-session
  production bugs that must close before moving on, not forward-looking
  proposals.
- Monotonic integers. Pick next-free. IDs permanent.

### Session-specific tracking

If an item is only relevant to one session and does not persist (e.g.
"verify shadow gate sessions 9+10"), record it in the session note or
`session_log.md` entry only. Do not create a persistent ID.

### Where to put what -- quick reference

| Item type | Location |
|---|---|
| Forward-looking enhancement, persistent | Enhancement Register (ENH-N) |
| Critical production bug, must fix soon | `merdian_reference.json` open_items (C-N) |
| Session-specific task, does not persist | session_log.md entry |
| Architectural finding worth preserving | Session appendix "Incomplete" table (Block 11) |
| Protocol/process rule | Change Protocol or Documentation Protocol (increment version) |

### Enforcement at session end

When closing a session, verify:

```
[ ] No new RESEARCH-OI-*, OI-*, SPO-* IDs introduced this session
[ ] All new persistent tracking is an ENH-N or C-N
[ ] Session-local tasks are in session_log.md, not a new ID
```

### Historical note

V18H_v2 (2026-04-17/18) proposed ENH-43..47 and OI-11..15. Reconciled
2026-04-19: ENH renumbered to ENH-53/55/56/57/58; OI content folded into
matching ENH entries with one new ENH (ENH-59) for the standalone
patch-syntax rule. See `docs/appendices/V18H_v2_RENUMBERING_NOTE.md` for
the full mapping.

---

## Maintenance Principles

### Keep it lean

Do not add sections to documents that are not used. The 13-block appendix structure exists because all 13 blocks are needed for rebuild-grade status. Do not add a Block 14 without a clear reason.

### docx for rebuild-grade records, markdown for living documents

- Masters and appendices: `.docx` (structured, formatted, narrative-heavy)
- Registers, protocols, session notes: `.md` (frequently updated, need readable diffs)
- Operational reference: `.json` (machine-queryable, fastest to update)

### The documentation debt rule

If `session_log.md` shows three consecutive entries with `docs_updated: no`, there is a documentation debt. Address it before the next phase boundary. Documentation debt compounds — it is much harder to reconstruct three sessions than to write up one session immediately.

---

## What "Rebuild-Grade" Means

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

If any of these is missing, the document is not rebuild-grade.

---

*MERDIAN Documentation Protocol v2 -- 2026-04-19 -- Commit to Git. Do not modify without updating version number.*
