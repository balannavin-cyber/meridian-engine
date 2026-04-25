# CLAUDE.md — MERDIAN Engine Orientation

> **Read this first, every session, before doing anything else.**
> This file is the contract between Navin and any Claude session working on MERDIAN.
> If something here conflicts with a `.docx` master, this file wins on operational state.
> The `.docx` masters win on architecture, governance, and historical decisions.

---

## What this project is

MERDIAN — Market Structure Intelligence & Options Decision Engine. A live options decision engine for NIFTY and SENSEX weekly options, with shadow-mode validation, ICT pattern detection, Kelly tiered sizing, and a hist_pattern_signals research store. Two environments: **Local Windows (PRIMARY LIVE)** and **AWS t3.small (SHADOW)**, both pulling from a single Git repo.

---

## Read order at session start

1. **This file** (`CLAUDE.md`) — orientation, rules, pointers
2. **`docs/session_notes/CURRENT.md`** — what the last session did, what this session is for, what NOT to reopen
3. **`docs/registers/tech_debt.md`** — known broken-ish things, workarounds, severity
4. **`docs/registers/MERDIAN_Enhancement_Register_v<latest>.md`** — forward-looking proposals (only if this session touches them)
5. **`docs/registers/merdian_reference.json`** — *targeted lookup only*, not full read. Use for file/table inventory.

That's it. Do **not** auto-load any `.docx` master at session start. They are generated artifacts, not working documents.

---

## Common operations — consult before asking

For any recurring operation (token rotation, runner restart, backfill, credential rotation, broker flow update, etc.), consult `docs/runbooks/README.md` to find the right runbook. Follow the runbook step by step.

| I need to… | Runbook |
|---|---|
| Rotate the Dhan access token | `docs/runbooks/runbook_update_dhan_token.md` |
| Update the Kite broker flow | `docs/runbooks/runbook_update_kite_flow.md` |
| Restart a stuck runner (Local) | `docs/runbooks/runbook_restart_runner_local.md` |
| Restart a stuck runner (AWS) | `docs/runbooks/runbook_restart_runner_aws.md` |
| Backfill a missing trading day | `docs/runbooks/runbook_backfill_missing_day.md` |
| Resolve Local↔AWS hash mismatch | `docs/runbooks/runbook_resolve_hash_mismatch.md` |
| Recover from DhanError 401 | `docs/runbooks/runbook_recover_dhan_401.md` |
| Add a row to trading_calendar | `docs/runbooks/runbook_add_calendar_row.md` |
| Emergency stop live trading | `docs/runbooks/runbook_emergency_stop.md` |

**Rule:** If the runbook exists but has `⚠ NAVIN: FILL` markers and you need that specific detail now, ask Navin for ONLY that detail, then update the runbook in the same session. If a runbook does not exist yet, ask Navin **once**, then immediately create it from `docs/runbooks/RUNBOOK_TEMPLATE.md` before proceeding with the task.

---

## The single source of truth map

| Question | Where to look |
|---|---|
| "What does this file do? Where is it? What does it write to?" | `merdian_reference.json` → `files.<filename>` |
| "What's the schema / row count / status of this table?" | `merdian_reference.json` → `tables.<tablename>` |
| "How do I do <recurring operation>?" | `docs/runbooks/` — check `README.md` first |
| "Is this issue known? What's the workaround?" | `tech_debt.md` |
| "Is this a critical bug or a forward proposal?" | `merdian_reference.json` → `open_items` (C-N) for critical · Enhancement Register for ENH-N |
| "What did we decide last time about X?" | `docs/decisions/ADR-<N>-<topic>.md` if it exists, else `session_log.md` grep |
| "How do I run preflight / canary / replay?" | `docs/operational/MERDIAN_Testing_Protocol_v1.md` |
| "What's the commit/branch/deploy rule?" | `docs/operational/MERDIAN_Change_Protocol_v1.md` |
| "When do I write an appendix vs a session note?" | `docs/operational/MERDIAN_Documentation_Protocol_v3.md` |
| "How do I keep a session from degrading?" | `docs/operational/MERDIAN_Session_Management_v1.md` |
| "What were the experiment findings?" | `docs/research/MERDIAN_Experiment_Compendium_v<latest>.md` |

---

## Non-negotiable rules

These are hard rules. Do not propose violations. Do not ask "what if we…".

1. **Edit only in Local.** AWS receives code via `git pull` — never direct edits except BREAK_GLASS (see Change Protocol Step 8).
2. **No run without preflight PASS.** Local commit hash must equal AWS commit hash before any live session.
3. **DB is truth.** Logs are supporting evidence. If a query disagrees with a log line, the query wins.
4. **Full-file promotion only.** No hand-patched partials. Every file in Git is a complete, reviewable file.
5. **Patch scripts must end with `ast.parse()` validation** before writing the target. (Lesson from `force_wire_breadth.py` 2026-04-16 — IndentationError discovered at market open.)
6. **5m bars for ICT pattern detection**, never 1m. 1m is for precise entry timing only after HTF confirms.
7. **Options-only.** Futures experiments are permanently closed (Experiment 2b, 2026-04-12).
8. **Capital ceiling is final:** ₹50L hard cap, ₹25L sizing freeze, ₹2L floor. Do not re-litigate.
9. **OpenItems Register is permanently closed (2026-04-15).** Do not create new `OI-*`, `RESEARCH-OI-*`, or `SPO-*` IDs. Persistent items go to Enhancement Register (ENH-N) or tech_debt.md. Critical production bugs use C-N in `merdian_reference.json`.
10. **No new ID prefix without updating the numbering convention** in `MERDIAN_Documentation_Protocol_v3.md` Rule 5.
11. **Do not ask Navin for file paths or routine operational procedures.** File locations live in `merdian_reference.json` → `files` (keyed by filename). Recurring procedures live in `docs/runbooks/`. If the answer isn't in either, say so explicitly and ask ONCE — then capture the answer as a new runbook using `docs/runbooks/RUNBOOK_TEMPLATE.md` before the end of the session. Next session, it will be there.
12. **Project knowledge is not the git working tree.** Local commits to git do NOT auto-sync to Claude.ai project knowledge. Any session that modifies `CURRENT.md`, `session_log.md`, `merdian_reference.json`, `tech_debt.md`, `MERDIAN_Enhancement_Register.md`, this file (`CLAUDE.md`), or any `docs/operational/*` file MUST re-upload those files to project knowledge before the session is considered closed. Failure to do so causes the next session's Claude to read stale state and either invent a different goal or refuse to proceed (failure mode observed Session 6 → Session 7, 2026-04-22). Treat git commit and project knowledge upload as two separate destinations both required for session close.

---

## Session contract

Every session has exactly ONE concern. If the goal sentence needs a comma, it has two concerns — split it.

| Session type | Goal | Output expected |
|---|---|---|
| Code debug | Fix one specific failing component | Patched file + tech_debt.md update or close + session_log entry |
| Architecture / planning | Design a component or protocol | New ADR markdown OR Enhancement Register entry |
| Documentation | Produce/update a specific document | The document, committed |
| Live canary | Monitor first live cycle | Canary outcome appended to session_log + git tag if PASS |
| Research / experiment | Answer one quantitative question | Result line in Experiment Compendium + commit |

---

## What Claude must do at session end (every session)

Before saying "done":

```
☐ Update CURRENT.md to reflect what THIS session did and what next session should pick up
☐ Update merdian_reference.json if any file/table/item status changed
☐ Update tech_debt.md if any item was added, mitigated, or closed
☐ Update Enhancement Register if any architectural thinking happened
☐ Update or create runbooks for any operational procedure Navin had to explain this session
☐ Append a one-line entry to session_log.md (date · git hash · concern · outcome)
☐ Commit all documentation changes with prefix MERDIAN: [OPS] ...
☐ Confirm Local + AWS hash match if any code changed
☐ Re-upload to project knowledge any of the files modified above (per Rule 12). Without this, next session's Claude reads stale state.
```

If three consecutive `session_log.md` entries show `docs_updated: no`, **stop and address documentation debt** before any new code work.

---

## When to generate a `.docx` (rare)

`.docx` Masters and Appendices are no longer the working format. Generate them only at:

- **Phase boundary** (e.g. shadow → live promotion, Phase 4 → Phase 5)
- **Commercial milestone** (e.g. first paying API customer)
- **External review** (audit, investor, regulator request)
- **Quarterly snapshot** (optional, if Navin wants a periodic reference)

When generating: assemble from the markdown layer. The markdown is the source. The `.docx` is the published render. See `MERDIAN_Documentation_Protocol_v3.md` Rule 6 for the compile workflow.

---

## Anti-patterns Claude should refuse

- ❌ "Let me re-read the V18 master to get oriented" — read CLAUDE.md and CURRENT.md instead
- ❌ "I'll write up the appendix at the end" — write the session_log entry now, the appendix only if a phase boundary triggers it
- ❌ "Let me discuss Heston while we fix this UPSERT bug" — split the session
- ❌ "I'll edit directly on AWS to save time" — BREAK_GLASS protocol exists for emergencies; everything else goes through Local → Git → AWS
- ❌ "Let me create OI-18 for this" — register is closed; use tech_debt.md or ENH-N
- ❌ "Let me run a 1m ICT detection just to check" — 5m is the architectural rule, 1m on ICT is wrong by design
- ❌ Pasting the full master into the session as context — use targeted JSON lookups instead
- ❌ "Where is file X?" without first checking `merdian_reference.json` files keys
- ❌ Asking Navin how to do a recurring operation without first checking `docs/runbooks/`
- ❌ Asking the same operational question twice across sessions — if asked once, it becomes a runbook
- ❌ "I committed CURRENT.md, that's enough" — git commit and project knowledge upload are two separate destinations, both required for session close per Rule 12
- ❌ Inventing a session goal because the one in CURRENT.md feels stale — flag the discrepancy and ask, do NOT silently swap goals (the file is the contract; if it's stale, fix the file, don't fabricate intent)

---

## Project file layout

```
C:\GammaEnginePython\                 (Windows local, PRIMARY LIVE)
/home/ssm-user/meridian-engine\        (AWS, SHADOW — git pull only)

  CLAUDE.md                           ← THIS FILE — root entry point
  *.py                                ← engine code
  .env                                ← secrets, never commit

  docs/
    operational/
      MERDIAN_Change_Protocol_v1.md
      MERDIAN_Documentation_Protocol_v3.md   ← supersedes v2
      MERDIAN_Session_Management_v1.md
      MERDIAN_Testing_Protocol_v1.md         ← consolidated preflight/canary/replay

    registers/
      merdian_reference.json          ← machine-queryable inventory (authoritative on op state)
      MERDIAN_Enhancement_Register_v<n>.md
      tech_debt.md                    ← persistent middle-tier issues

    runbooks/                         ← step-by-step procedures for recurring ops
      README.md                       ← index of all runbooks
      RUNBOOK_TEMPLATE.md             ← template for new runbooks
      runbook_update_dhan_token.md
      runbook_update_kite_flow.md
      runbook_*.md                    ← grows as recurring ops surface

    session_notes/
      CURRENT.md                      ← live session resume — updated EVERY session
      session_log.md                  ← append-only one-line per session
      YYYYMMDD_<topic>.md             ← per-session detail when warranted

    decisions/                        ← optional ADRs (one per major decision)
      ADR-001-options-only.md
      ADR-002-5m-for-ict.md
      ...

    research/
      MERDIAN_Experiment_Compendium_v<n>.md
      merdian_all_experiment_results.md

    masters/                          ← .docx PUBLISHED ARTIFACTS (generated on demand)
      MERDIAN_Master_V<n>.docx

    appendices/                       ← .docx PUBLISHED ARTIFACTS (generated on demand)
      MERDIAN_Appendix_V<n>.docx
```

---

## Quick environment reference

| Field | Local | AWS |
|---|---|---|
| Base path | `C:\GammaEnginePython` | `/home/ssm-user/meridian-engine` |
| Python | `python` (on PATH; use `py` as fallback) | `python3` |
| Scheduler | Windows Task Scheduler | Linux cron |
| Role | PRIMARY LIVE | SHADOW |
| Instance | — | `i-0878c118835386ec2` (eu-north-1) |
| Access | direct | AWS SSM Session Manager |

For env contracts, runner names, and full file paths, use `merdian_reference.json` → `environments`.

---

## Things that are settled — DO NOT REOPEN

These are decisions made and validated. Re-litigating them wastes session time.

- ✅ Options-only framework (Experiment 2b, 2026-04-12)
- ✅ Capital ceiling ₹50L / ₹25L / ₹2L (Appendix V18F v2)
- ✅ T+30m exit timing (Experiment 8/14b/15, multiple confirmations)
- ✅ 1H zones in MEDIUM context (ENH-37, validated)
- ✅ BEAR_OB AFTERNOON → HARD SKIP (Signal Rule Book v1.1, 17% WR)
- ✅ ICT pattern detection on 5m bars (Research Sessions 4-5, 2026-04-17)
- ✅ ENH-42 WebSocket — DEFERRED post-Phase 4, do not build now
- ✅ OpenItems Register closed (2026-04-15)
- ✅ D-06 signal-consumer concerns (resolved earlier; do not rebuild regret log)

If any of these need to change, that is itself an architectural session — write a new ADR.

---

*CLAUDE.md v1.2 — 2026-04-22 (PM). Added Rule 12 (project knowledge != git working tree; mandatory re-upload at session end) plus matching session-end checklist line and two anti-patterns. Trigger: Session 6 -> Session 7 stale-cache failure mode where new chat read pre-Session-6 CURRENT.md from project knowledge and refused to proceed (correct behaviour given the file it had access to). v1.1 (2026-04-22 AM) added runbook layer (rule 11). Update version any time read order, non-negotiable rules, session contract, or common operations list changes.*


## Rule 13 - Data contamination registry (added Session 7, 2026-04-23)

MERDIAN tracks known data-integrity incidents in the Supabase table `public.data_contamination_ranges`. Before running ANY research query, experiment analysis, or model training that reads fields listed in `field_scope` from tables listed in `affected_tables`, check whether the query time window overlaps with a registered contamination range.

**Standard check - SQL helper:**

```sql
SELECT public.is_breadth_contaminated(ts) FROM your_query;
-- Or filter:
WHERE NOT public.is_breadth_contaminated(ts)
```

**For non-breadth fields:**

```sql
SELECT * FROM public.data_contamination_ranges 
WHERE field_scope ILIKE '%your_field%';
```

**When to add a new entry:**

Whenever a new data-integrity incident is diagnosed, INSERT a row into `data_contamination_ranges` with:
- Unique `contamination_id` (pattern: `SCOPE-DESCRIPTION-YYYY-MM-DD`)
- `field_scope` (comma-separated list of affected column/field names)
- `contamination_start` and `contamination_end` (timestamptz, IST)
- `affected_tables` (array of table names, including views' underlying tables)
- `root_cause` (what broke)
- `remediation` (how it was fixed)
- `created_session`

**Current registered contamination ranges (2026-04-23):**
- `BREADTH-STALE-REF-2026-03-27`: 27-day breadth cascade (Session 7). See `merdian_reference.json` TD-NNN for context.

**Anti-pattern:** Running experiments on historical data without first checking `data_contamination_ranges`. Research conclusions drawn on tainted data are worse than no conclusions.


---

*CLAUDE.md v1.3 - 2026-04-23. Added Rule 13 (data contamination registry). Trigger: Session 7 discovered 27-day breadth contamination spanning 29 tables; without a registry, future researchers would train/analyze against tainted rows. v1.2 added Rule 12 (doc-sync). v1.1 added Rule 11 (runbooks).*


*CLAUDE.md v1.4 — 2026-04-25 (corrected Local Python path in env table; the previously listed `Python312\python.exe` path doesn't exist on Navin's box; surfaced when running experiment_17). v1.3 added Rule 13 (data contamination registry). v1.2 added Rule 12 (doc-sync). v1.1 added Rule 11 (runbooks).*

