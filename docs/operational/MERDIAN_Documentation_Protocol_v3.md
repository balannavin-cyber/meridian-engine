# MERDIAN Documentation Protocol v3

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Documentation_Protocol_v3.md` |
| Version | v3 |
| Created | 2026-03-31 (v1) · 2026-04-19 (v2 — Rule 5 numbering) · (this session) (v3 — AI-first markdown layer) |
| Type | Governance — when/what/where to document |
| Companion | `MERDIAN_Change_Protocol_v1.md` · `MERDIAN_Session_Management_v1.md` · `MERDIAN_Testing_Protocol_v1.md` |
| Supersedes | `MERDIAN_Documentation_Protocol_v2.md` |

---

## What changed from v2

v3 keeps every rule in v2 and adds a new top layer:

1. **NEW Rule 0** — `CLAUDE.md` is the single root entry point for all AI sessions
2. **NEW Rule 6** — `.docx` Masters and Appendices are now *published artifacts*, generated from markdown on demand. They are no longer the working canonical record.
3. **NEW Rule 7** — `CURRENT.md` replaces the manually-pasted "session resume block." Claude reads it at session start.
4. **NEW Rule 8** — `tech_debt.md` is the persistent middle-tier register between C-N (critical) and ENH-N (forward-looking).
5. **CHANGED Rule 1** — Session Note vs Appendix: appendices are now triggered only by phase boundaries or external review, not by every code-changing session.
6. **CHANGED Rule 2** — File layout adds `docs/decisions/` (ADRs) as an optional but recommended convention.

Rules 3, 4, 5 from v2 are unchanged.

---

## Why this revision exists

The v1/v2 protocol made `.docx` the canonical rebuild-grade record. That worked while MERDIAN was being built up — `.docx` formatting let the audit-corrected appendices stand as standalone reconstruction documents. But three costs accumulated:

1. **Authoring friction.** Every code session ended with a heavy `.docx` write. Documentation lag became a real risk (the v2 "documentation debt rule" exists because of this).
2. **AI session inefficiency.** Claude can't skim a `.docx` the way it can a markdown file. Every session resume meant either pasting the `.docx` (huge context cost) or extracting from `merdian_reference.json` (correct, but required Navin to know what to extract).
3. **Diff invisibility.** `.docx` files are binary in Git. The history exists, but the *changes* don't.

The fix is not to throw out `.docx` — it's still the right format for stakeholder-facing or audit-grade documents — but to demote it from working format to publication artifact. Markdown becomes the canonical operational truth; `.docx` is generated when a human reader outside the development loop needs it.

---

## Rule 0 — `CLAUDE.md` is the root entry point

**Location:** Repo root (`C:\GammaEnginePython\CLAUDE.md`, mirrored on AWS).

**Purpose:** Orient any new Claude session in 3 minutes. Tells Claude what MERDIAN is, where to look for what, what the non-negotiable rules are, and what NOT to reopen.

**What it contains:**
- Project one-liner
- Read order at session start (CLAUDE.md → CURRENT.md → tech_debt.md → Enhancement Register → JSON for targeted lookups)
- The single-source-of-truth lookup table
- Non-negotiable rules (extracted from Change Protocol)
- Session contract (one concern per session)
- Session-end checklist
- Anti-patterns to refuse
- File layout map
- Settled decisions list (do-not-reopen)

**What it does NOT contain:**
- Detailed protocol mechanics (those live in their respective protocol files)
- File/table inventory (lives in `merdian_reference.json`)
- Architectural narrative (lives in `.docx` masters when generated, or in markdown architecture notes)

**Update cadence:** Whenever a non-negotiable rule, settled decision, or read-order changes. Bump version in the file's footer.

---

## Rule 1 — What triggers what kind of document (REVISED)

### Session log entry — every session

Triggered by **every session, no exceptions**. One line in `session_log.md`:

```
YYYY-MM-DD · <git-hash> · <concern> · <PASS/FAIL/PARTIAL> · docs_updated:yes/no
```

### Session note — when investigation happened but no commit

Triggered by a session that did investigation but produced no code commit, no schema change, no item closure. Lightweight markdown, 10–30 lines, in `docs/session_notes/YYYYMMDD_<topic>.md`.

### `CURRENT.md` overwrite — every session

Triggered by **every session that does anything substantive**. Update "Last session" block to reflect what just happened. Reset "This session" block for next.

### Markdown change record — when code/schema/items change

Triggered by a session that changed any file, table, or item status. Update `merdian_reference.json` and (if applicable) `tech_debt.md` and `Enhancement Register` in the same commit as the code change.

This **replaces** the old "appendix per session" rule for routine sessions. The 13-block appendix structure is no longer the default per-session output.

### Appendix `.docx` — only at phase boundary or external need

Triggered by **one of**:

- A phase boundary crossed (e.g. shadow → live promotion, Phase 4 → Phase 5)
- External review request (audit, investor, regulator)
- Quarterly snapshot (optional, if Navin chooses)
- Accumulated session_log entries since last appendix exceed ~30 substantive sessions

When triggered, the appendix is **assembled from the markdown layer**, not authored from scratch. See Rule 6.

### Master `.docx` — only at major phase boundary or commercial milestone

Triggered by:
- A fundamental architectural change (e.g. Monte Carlo pricing live, strategy proposal engine replacing signal engine)
- A commercial milestone (e.g. API first paying customer)
- Accumulated minor activity since last master makes the markdown layer warrant a re-published narrative
- Quarterly cadence (optional)

Same rule: assembled from the markdown, not authored from scratch.

### Enhancement Register update — when architectural thinking happens

Unchanged from v2. Update in same session as the thinking. ENH-N IDs.

### `tech_debt.md` update — when known broken-ish things change

NEW in v3. Update inline as items are added, mitigated, severity-changed, or closed. Use `TD-N` IDs.

### ADR (Architecture Decision Record) — when a new architectural decision is made

NEW in v3, optional but recommended. Each significant architectural decision gets a small markdown file: `docs/decisions/ADR-NNN-<topic>.md`. Captures: context, decision, alternatives considered, consequences. Once written, the ADR is the durable answer to "why did we do it this way?" — fed into future CLAUDE.md "settled decisions" lists.

### Operational document update — when a protocol changes

Unchanged from v2. Increment version number, never overwrite.

---

## Rule 2 — Where every document lives (REVISED)

```
C:\GammaEnginePython\
(mirrored at /home/ssm-user/meridian-engine/ via git pull)

  CLAUDE.md                                         ← NEW (Rule 0): root AI entry point

  docs/
    operational/
      MERDIAN_Change_Protocol_v1.md
      MERDIAN_Documentation_Protocol_v3.md          ← THIS FILE
      MERDIAN_Session_Management_v1.md
      MERDIAN_Testing_Protocol_v1.md                ← NEW: consolidated testing gates

    registers/
      merdian_reference.json                        ← machine-queryable inventory
      MERDIAN_Enhancement_Register_v<n>.md
      tech_debt.md                                  ← NEW (Rule 8): persistent middle-tier
      MERDIAN_OpenItems_Register_v7.md              ← CLOSED 2026-04-15, retained as audit

    session_notes/
      CURRENT.md                                    ← NEW (Rule 7): live session resume
      session_log.md                                ← append-only one-liner per session
      YYYYMMDD_<topic>.md                           ← per-session detail (rare)

    decisions/                                      ← NEW: optional ADR convention
      ADR-001-options-only.md
      ADR-002-5m-for-ict.md
      ADR-003-capital-ceiling.md
      ...

    research/
      MERDIAN_Experiment_Compendium_v<n>.md
      merdian_all_experiment_results.md

    masters/                                        ← .docx — PUBLISHED ARTIFACTS now
      MERDIAN_Master_V<n>.docx                      ← generated on demand (Rule 6)

    appendices/                                     ← .docx — PUBLISHED ARTIFACTS now
      MERDIAN_Appendix_V<n>.docx                    ← generated on demand (Rule 6)
```

**Format rules:**
- `.md` for everything in operational/, registers/, session_notes/, decisions/, research/
- `.json` for merdian_reference.json (machine-queryable, fastest to update)
- `.docx` only for masters/ and appendices/ — and only when generated for stakeholder use

---

## Rule 3 — When to update (UNCHANGED FROM v2)

### During every development session
```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update tech_debt.md if a TD item changes
```

### At session end (before closing)
```
☐ Overwrite CURRENT.md (Last session reflects this session, This session reset)
☐ Append one line to session_log.md
☐ Update Enhancement Register if architectural thinking happened
☐ Commit all documentation changes to Git
```

### Weekly (or after 3+ development sessions)
```
☐ Review Enhancement Register for stale PROPOSED items
☐ Review tech_debt.md for items that should escalate to ENH or close
```

### At phase boundaries
```
☐ Generate appendix .docx from the markdown layer (Rule 6)
☐ If major phase: generate master .docx
☐ Tag Git: git tag docs-v<version>
```

---

## Rule 4 — Documentation and Git (UNCHANGED FROM v2)

### 4.1 Documentation commits alongside code
Every code commit that changes system behaviour has a corresponding documentation commit in the same push or the immediately following push.

```
MERDIAN: [OPS] tech_debt.md — TD-007 added
MERDIAN: [OPS] merdian_reference.json — file statuses updated
MERDIAN: [OPS] CURRENT.md — session 2026-MM-DD recorded
```

### 4.2 No major master without register update
The Open Items Register (closed) and Enhancement Register and tech_debt.md must be at current state before any major master `.docx` is generated.

### 4.3 Documentation tags
```bash
git tag docs-v<version>
git push --tags
```

---

## Rule 5 — Numbering convention (UNCHANGED FROM v2)

### ENH IDs
Monotonic integers in `MERDIAN_Enhancement_Register_v*.md`. Pick next-free. IDs permanent. REJECTED items keep their ID as a rejection record.

### OI IDs
**No new `OI-*` prefixes.** OpenItems Register closed 2026-04-15. Persistent items go to Enhancement Register or `tech_debt.md`. Historical OI-* entries retained in JSON as audit trail.

### C IDs (critical)
Tracked in `merdian_reference.json` `open_items`. Mid-session production bugs that must close before moving on. Monotonic integers.

### TD IDs (tech debt — NEW in v3)
Tracked in `tech_debt.md`. Monotonic integers (TD-001, TD-002, ...). Use for known broken-ish items with workarounds — neither blocking (C-N) nor forward-looking proposals (ENH-N).

### Session-specific tracking
Record in `CURRENT.md` checkpoints or `session_log.md` only. Do not create persistent IDs.

### Where to put what — quick reference

| Item type | Location |
|---|---|
| Forward-looking enhancement, persistent | Enhancement Register (ENH-N) |
| Critical production bug, must fix soon | `merdian_reference.json` `open_items` (C-N) |
| Known broken-ish, has workaround, persistent | `tech_debt.md` (TD-N) |
| Session-specific task, does not persist | `CURRENT.md` checkpoint or `session_log.md` |
| Architectural decision worth preserving | `docs/decisions/ADR-NNN-<topic>.md` |
| Protocol/process rule | Operational protocol file (increment version) |

---

## Rule 6 — `.docx` as published artifact (NEW)

`.docx` Masters and Appendices are no longer the working canonical record. They are **published renders** of the markdown layer, generated when a stakeholder outside the development loop needs a single rebuild-grade document.

### When to generate

| Trigger | Output |
|---|---|
| Phase boundary (e.g. Phase 4 → Phase 5) | New Master `.docx` |
| Shadow → live promotion confirmed | Appendix `.docx` for the promotion session |
| External audit / investor / regulator request | Master + relevant appendices `.docx` |
| Commercial milestone (first paying customer) | Major Master `.docx` |
| Quarterly snapshot (optional) | Master `.docx` for the quarter |

### How to generate (compile workflow)

The `.docx` is assembled from existing markdown sources. Rough recipe:

1. **Identify the period** (since last `.docx`)
2. **Pull from sources:**
   - Architectural narrative → `CLAUDE.md` settled-decisions + ADRs in `docs/decisions/`
   - File/table inventory → `merdian_reference.json` (rendered to tables)
   - Session history → `session_log.md` lines for the period
   - Enhancement state → current Enhancement Register markdown
   - Tech debt state → current `tech_debt.md`
   - Experiment results → Experiment Compendium markdown
3. **Render to `.docx`** using a script (e.g. `pandoc` or `python-docx` template). The 13-block structure can be a Jinja template if you want to retain that shape.
4. **Commit** the generated `.docx` to `docs/masters/` or `docs/appendices/`.
5. **Tag** `git tag docs-v<version>`.

The point: the markdown is the source. The `.docx` is the publish step. If they drift, the markdown wins and the `.docx` gets regenerated.

### What this stops being

The 13-block appendix structure is no longer required for every code-changing session. It remains the structure of the *published* appendix when one is generated. Routine sessions update markdown registers and `CURRENT.md` instead.

---

## Rule 7 — `CURRENT.md` is the live session resume (NEW)

**Location:** `docs/session_notes/CURRENT.md`

**Purpose:** Replace the practice of pasting a "session resume block" at the start of every chat. Claude reads `CURRENT.md` after `CLAUDE.md` and has full session resume context without any human paste.

**Contents:**
- "Last session" block — what just happened
- "This session" block — goal, type, success criterion, relevant files/tables/items, DO_NOT_REOPEN list
- Live state snapshot — env health, open critical items, active ENH in flight
- Mid-session checkpoint slots (per Session Management Rule 1)
- Session-end checklist

**Update cadence:** Overwrite at the end of every substantive session. Never branch this file. Never archive it (the `session_log.md` is the archive).

**Why it works:** The pain of "pasting the resume block" was load-bearing — it forced Navin to think about what the session was for. With `CURRENT.md`, that thinking still happens, but it's done at session end (when you have the answers) rather than session start (when you're trying to load context). Claude does the load.

---

## Rule 8 — `tech_debt.md` is the persistent middle tier (NEW)

**Location:** `docs/registers/tech_debt.md`

**Purpose:** Track persistent known issues that don't fit the C-N (critical) or ENH-N (forward-looking) buckets. The register the closed OpenItems Register used to fill — but lighter, with explicit lifecycle.

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

**Anti-pattern section:** `tech_debt.md` ends with a list of patterns to avoid (so we don't add new tech debt). Reviewed in CLAUDE.md by reference.

---

## Maintenance principles (UNCHANGED, light revision)

### Keep it lean
Do not add sections that are not used. The 13-block appendix structure exists because all 13 blocks are needed for rebuild-grade. Do not add a Block 14 without a clear reason. Same applies to CLAUDE.md sections, tech_debt.md fields, etc.

### Markdown for working state, .docx for published state, .json for machine queries
- Working operational state: `.md` (frequently updated, readable diffs, AI-readable)
- Published rebuild-grade artifacts: `.docx` (structured, formatted, narrative-heavy)
- Machine-queryable lookup: `.json`

### The documentation debt rule
If `session_log.md` shows three consecutive entries with `docs_updated: no`, there is documentation debt. Address it before any new code work. Documentation debt compounds.

---

### Cross-layer sync (project knowledge vs git working tree)

Local git commits do NOT auto-sync to Claude.ai project knowledge. The two layers drift independently:

- `git commit` updates the local working tree and (after `git push`) origin
- Project knowledge upload is a separate manual step in the Claude.ai UI

A session is not closed until both destinations have the new state. If only git is updated, the next session's Claude reads stale project knowledge and either invents a different goal (bad) or correctly flags the discrepancy and refuses to proceed (acceptable but loses session time). See CLAUDE.md Rule 12 for the mandatory re-upload list.

This was first observed Session 6 -> Session 7 (2026-04-22). Codified as Rule 12 + checklist line + this principle.

---

## What "rebuild-grade" means (UNCHANGED)

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

In v3, "rebuild-grade" is a property of the **markdown layer as a whole** (CLAUDE.md + JSON + tech_debt + Enhancement Register + ADRs + session_log). When a `.docx` is generated, it inherits rebuild-grade from the markdown it was assembled from.

---

*MERDIAN Documentation Protocol v3 — supersedes v2. Commit to Git. Do not modify without updating version number.*
