# MERDIAN Change Protocol v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Change_Protocol_v1.md |
| Version | v1 |
| Created | 2026-03-31 |
| Type | Operational — execution document |
| Companion | MERDIAN_Documentation_Protocol_v1.md · MERDIAN_Session_Management_v1.md |

---

## Part 1 — Operational Checklist

> **This is the execution document. Must be usable at 08:45 IST under pressure. No interpretation required.**

---

### 🔴 Three Rules — Read First

```
🔴  FAIL ANYWHERE → STOP
🟡  BREAK_GLASS → document same session
🟢  ALL GREEN → proceed to canary
```

---

### NON-NEGOTIABLE RULES

```
Edit ONLY in Local
GitHub = source of truth
AWS = deploy target (never edit directly)
No run without preflight PASS
Local & AWS commit hash MUST match before any live session
```

---

### STEP 0 — Identify Change Track

Every change is exactly one of:

| Track | What it covers |
|---|---|
| **A — Code** | Any Python file (.py) |
| **B — Config / Schema** | Calendar rows, DB constraints, .env, AWS cron, Windows tasks |
| **C — Docs only** | .md, .docx, .json registers |

---

### STEP 1 — Execute Change

#### 🟢 Track A — Code Change
```
1. Edit in Local
2. Run Local Preflight → MUST PASS
3. Commit → Push to Git
4. AWS → git pull
5. Verify commit hash matches Local (see Step 4)
6. Run AWS Preflight → MUST PASS
7. IF signal path changed → run Live Canary (Step 7)
8. Done
```

#### 🟡 Track B — Config / Schema Change
```
1. Apply change in Local / DB / cron / scheduler
2. Run contract checks (DB gate or env gate as applicable)
3. Commit → Push to Git
4. AWS → git pull
5. Run AWS contract checks
6. Done
```

#### 🔵 Track C — Docs Only
```
1. Edit
2. Commit → Push
3. Done
```

---

### STEP 1.5 — Pre-Commit Sanity (Track A only)

Before committing, confirm all four:

```
☐ No hardcoded Windows paths in files destined for AWS
☐ No print/debug statements left in production code
☐ No .env values hardcoded in any file
☐ File is complete (full replacement, not a fragment)
```

---

### STEP 1.6 — Patch Script Syntax Gate (ENH-59) — Track A only

Any `fix_*.py` / `patch_*.py` / `update_*.py` script that rewrites another
.py file on disk MUST validate the result's AST before writing. This is
non-optional.

```
☐ Script reads target file
☐ Script applies edits in memory
☐ Script calls ast.parse(patched_text) BEFORE writing
☐ If SyntaxError: print error to stderr and sys.exit(non-zero) — do NOT write
☐ Script also validates its OWN AST on startup (ast.parse(__file__))
```

**Why:** force_wire_breadth.py (2026-04-16) inserted code at wrong indent
depth. Script exited cleanly; IndentationError surfaced only at next
restart, would have disabled the entire pipeline.

**Reference implementations:** fix_enh6061.py, update_registers_enh5355.py,
fix_runner_indent.py, fix_atm_option_build.py, fix_expiry_lookup.py.

---

### STEP 2 — Commit Format (MANDATORY)

```
MERDIAN: [TAG] <scope> — <intent>
```

| Tag | Meaning |
|---|---|
| `ENV` | runtime, infra, scheduler, auth, AWS/local paths |
| `DATA` | schema, ingestion, DB constraints, table changes |
| `SIGNAL` | anything touching signal output or computation |
| `OPS` | preflight, monitoring, alerting, documentation |

**Commit body must include:**
```
Why this change was needed
What file(s) changed
Environment(s) affected: Local / AWS / Both
Validation performed
Live session required for final confirmation? yes/no
```

**Examples:**
```
MERDIAN: [ENV] Windows token task path — fix SYSTEM account python path
MERDIAN: [DATA] gamma_metrics — add gamma_zone column and unique index
MERDIAN: [SIGNAL] E-02 shadow — gamma_zone classification in compute_gamma_metrics
MERDIAN: [OPS] preflight Stage 0 — environment contract checks
```

---

### STEP 3 — Breaking Change Check

A change is **BREAKING** if it touches any of:

```
☐ DB schema used by downstream scripts
☐ stdout contract (Run ID: prefix — ingest_option_chain_local.py)
☐ function signature called by a runner
☐ trading_calendar schema or field names
```

**If BREAKING:**
```
→ MUST update both Local and AWS in the SAME session
→ MUST validate compatibility / migration script
→ MUST run replay or equivalent validation
→ Document as BREAKING in commit body
```

---

### STEP 4 — Sync Verification (MANDATORY before any run)

Run on BOTH environments:

```bash
git log --oneline -1
```

**Rule:** Local commit hash == AWS commit hash

```
If NOT equal:
  ❌ STOP — DO NOT PROCEED
  Resolve sync before continuing
  This is the DEGRADED failure mode — both preflights may pass but environments are running different code
```

---

### STEP 5 — Preflight Gate

```
Preflight PASS → OK to proceed
Preflight FAIL → DO NOT RUN — investigate first
```

Preflight stages:
- Stage 0: Environment contract (imports, files, signatures)
- Stage 1: Auth/API smoke (token, IDX_I, expiry-list, LTP)
- Stage 2: DB contract (tables, columns, indexes, calendar row, freshness)
- Stage 3: Runner dry-start (start and clean-exit outside session)
- Stage 4: Replay/fixture (analytics on known-good stored payloads)
- Stage 5: Live canary (market hours only — final gate)

---

### STEP 6 — Daily Operating Mode

```
08:15 IST — Token refresh (Local + AWS)
08:30 IST — Preflight auto-run (Local + AWS) → Telegram PASS/FAIL
```

| Preflight result | Action |
|---|---|
| Both PASS | Proceed to 09:15 live canary |
| FAIL → fixed by 09:10 | Re-run preflight → if PASS, proceed |
| Local PASS, AWS FAIL | LOCAL_ONLY session — AWS sits out |
| Both FAIL | NO_SESSION — log reason, investigate |
| Hash mismatch (DEGRADED) | Resolve sync → re-run preflight |

---

### STEP 7 — Live Canary Rule

Live session allowed ONLY IF:
```
☐ Preflight PASS (both or LOCAL_ONLY mode confirmed)
☐ Hash match confirmed (Step 4)
☐ Trading calendar row exists for today (DB gate check)
```

Live canary purpose: validate behaviour on live changing data.
Live canary is NOT for: discovering import errors, schema mismatches, path failures, auth failures.

---

### STEP 8 — Emergency (BREAK_GLASS)

If AWS must be edited directly (emergency only):

```
1. Fix on AWS
2. Immediately copy exact file to Local
3. Commit with message: MERDIAN: [ENV] BREAK_GLASS — <reason>
4. Push → AWS git pull
5. Verify hash match
6. Document in Open Items Register same session
```

---

### STEP 8B — Rollback

If live canary fails after promotion:

```
1. git log --oneline -5    (identify last known-good commit)
2. git checkout <prior_hash> -- <affected_files>
3. Commit: MERDIAN: [TAG] ROLLBACK to <hash> — <reason>
4. Push → AWS git pull → verify hash match
5. Run preflight → confirm PASS
6. Document rollback reason in register
```

---

### STEP 9 — Post-Market

```
☐ Capture fixtures (if first clean session after meaningful change)
☐ Update Open Items Register (close what closed, add what was found)
☐ Update merdian_reference.json (file/table/item status changes)
☐ Write session note or appendix (see Documentation Protocol)
☐ Commit all documentation changes
```

---

### STEP 10 — Release Marker

After successful live canary:

```bash
git tag vYYYYMMDD-canary-pass
git push --tags
```

---

### ✅ Done Criteria

A change is complete only when ALL of these are true:

```
☐ In Git (committed and pushed)
☐ Synced to AWS (hash match confirmed)
☐ Preflight PASS on target environment(s)
☐ Live canary PASS (if signal path changed)
☐ Documentation updated (register + reference JSON)
☐ docs_updated field noted in preflight report
```

---

## Part 2 — Reference Standard

> **This is the architectural document. Explains WHY and HOW. Not for execution under pressure.**

---

### Objective

Ensure:
- Zero environment drift between Local, Git, and AWS
- Deterministic deployments — same code, same behaviour, every time
- No live-session debugging of failures that preflight should catch
- Full traceability of every change
- Safe evolution of the signal system

---

### System Model

```
GitHub        — canonical source of truth
Local         — primary engineering workspace (edit here only)
AWS           — deployment target (receive code via git pull only)

Flow:   Local → Git → AWS → Preflight → Live Canary
```

---

### Core Problems This Protocol Solves

MERDIAN has experienced repeated session losses from:
- Local ≠ AWS file drift (direct AWS edits left uncommitted)
- Missing contract validation (import errors, signature drift discovered at live session)
- Live sessions used as debuggers for basic environment failures
- No pre-execution readiness check
- Scheduler ownership confusion between environments

Every rule in this protocol traces to one of these failure modes.

---

### Design Principles

1. **No interpretation at runtime** — checklist must be executable under stress without ambiguity
2. **Preflight over live debugging** — live market is a canary, not a test environment
3. **DB is truth, logs are secondary** — consistent with MERDIAN's established V17D principle
4. **One codebase, two environments** — no forks, no divergence, no environment-specific code branches
5. **Full-file promotion only** — no hand-patched partials. Every file in Git is a complete, reviewable file
6. **No state outside Git** — release states, environment sync, and canary outcomes live in Git (commits + tags). No external spreadsheet, no memory. If it is not in Git, it did not happen.

---

### Change Classification

| Class | Examples | Key gate |
|---|---|---|
| ENV | scheduler, token refresh, runner contract, AWS calendar, cron | Stage 0 + Stage 1 + Stage 3 |
| DATA | schema, constraints, table columns, view changes | Stage 2 + replay if analytics affected |
| SIGNAL | E-02 shadow, confidence penalties, signal logic | Stage 4 replay + shadow validation before live promotion |
| OPS | monitoring, preflight, alerting, documentation | No operational gates — commit directly after review |

---

### Breaking Change Definition

A change is breaking if it alters:
- DB schema used by downstream code (table columns, constraint names, index names)
- The `Run ID:` stdout format emitted by `ingest_option_chain_local.py` (both runners parse this)
- Function signatures called by any runner script
- trading_calendar schema or field names

Breaking changes require:
1. Both environments updated in the same session
2. Migration script or compatibility check documented
3. Replay validation on stored fixtures before live promotion
4. `BREAKING` noted in commit body

---

### Branching Model

```
main        — production only. Merged from dev or hotfix.
dev         — integration. Day-to-day development work.
hotfix/*    — emergency only. Must merge to main AND dev simultaneously.
              Commit must include BREAK_GLASS.
              Must be documented in Open Items Register same session.
```

**Why hotfix/* matters:** Without a defined emergency path, engineers make undocumented AWS edits under pressure. The hotfix branch gives pressure a legitimate channel that still maintains traceability.

---

### State Model (Git-driven, no external tracker)

| State | Meaning |
|---|---|
| Commit exists | Code is in Git |
| AWS pulled, hash match | Code is deployed |
| `vYYYYMMDD-canary-pass` tag | Live session validated on that date |

No external state tracker. No spreadsheet. No memory. Git is the record.

---

### Failure Modes

| Mode | Condition | Response |
|---|---|---|
| FULL | Local + AWS preflight PASS, hash match | Proceed to live canary |
| LOCAL_ONLY | AWS preflight FAIL, Local PASS | Local runs, AWS sits out |
| NO_SESSION | Local preflight FAIL | No live session, investigate |
| DEGRADED | Hash mismatch (both may preflight PASS) | Resolve sync before proceeding — different code on two environments |

---

### MERDIAN-Specific Standing Rules

| Rule | Statement |
|---|---|
| Rule 1 | No code edits on AWS unless BREAK_GLASS emergency |
| Rule 2 | No live session reliance for failures preflight should catch |
| Rule 3 | No AWS run of new code that is not in Git |
| Rule 4 | No documentation lag after meaningful promotion |
| Rule 5 | DB is truth — logs are supporting evidence |
| Rule 6 | Token refresh at 08:15 IST — before preflight, not after |
| Rule 7 | trading_calendar row must exist for today — checked in preflight Stage 2 |

---

### Daily Cadence Summary

```
08:15 IST   Token refresh (Local + AWS)
08:30 IST   Preflight auto-run (Local + AWS) → Telegram PASS/FAIL
08:30–09:10 Investigation window if FAIL
09:15 IST   Live canary (PASS only)
Post-market Fixtures + docs + commit
```

---

*MERDIAN Change Protocol v1 — 2026-03-31 — Commit to Git. Do not modify without updating version number.*
