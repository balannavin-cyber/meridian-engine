# MERDIAN Session Management v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Session_Management_v1.md |
| Version | v1 |
| Created | 2026-03-31 |
| Type | Operational — managing AI development sessions efficiently |
| Companion | MERDIAN_Change_Protocol_v1.md · MERDIAN_Documentation_Protocol_v1.md |

---

## Why This Document Exists

AI development sessions degrade. As context accumulates — code pastes, SQL results, error outputs, architectural discussions — the session window fills, response latency increases, and earlier context gets less weight. The typical MERDIAN session degrades noticeably around 60–80 exchanges of heavy code activity and becomes unreliable beyond 100.

The current pattern has been: work until degradation hits, then document under pressure, then struggle to resume in the next session. This is expensive and avoidable.

This protocol inverts that pattern: **documentation is built continuously during the session, not rescued at the end.**

---

## Rule 1 — The 20-Exchange Checkpoint

Every 20 exchanges of significant code or SQL activity, spend 2 minutes updating a running session scratchpad.

**Format — 5 bullet points maximum:**

```
[~20 exchanges]
- Fixed: <what was fixed and how>
- Confirmed: <what was validated with evidence>
- Open: <what is still unresolved>
- Changed: <any file or schema changed>
- Next: <immediate next step>
```

**Why this works:** When the session degrades at exchange 100, you have five checkpoints already written. The final session note or appendix is assembling five checkpoints, not reconstructing from memory.

**The rule:** If you find yourself thinking "I'll write this up at the end," write the checkpoint now instead. The end never arrives with the clarity you expect.

---

## Rule 2 — The Session Resume Block

At the start of every new session, paste a structured resume block before any code exchange. This is the single most important practice for frictionless continuation.

**Format:**

```
MERDIAN SESSION RESUME — [YYYY-MM-DD]

LAST CLEAN STATE:      [Git commit hash or tag, e.g. v20260330-canary-pass]
LOCAL_PREFLIGHT:       [PASS / FAIL / NOT_RUN]
AWS_PREFLIGHT:         [PASS / FAIL / NOT_RUN]

OPEN CRITICAL:         [e.g. C-01, V18A-01, V18A-02, V18A-03]
LAST SESSION DID:
  - [one bullet]
  - [one bullet]
  - [one bullet]

THIS SESSION GOAL:     [one sentence, specific — not "continue working on MERDIAN"]
DO_NOT_REOPEN:         [settled items that must not be re-litigated, e.g. "do not reopen D-06 consumer concerns"]

RELEVANT FILES:        [only files relevant to this session's goal]
RELEVANT TABLES:       [only tables relevant to this session's goal]
RELEVANT OPEN ITEMS:   [only items this session will touch]
```

**Why the DO_NOT_REOPEN field matters:** Without it, every session risks re-proposing what was already decided. The V18A resume prompt explicitly says "Do not re-open D-06 signal-consumer concerns or rebuild the regret log." That constraint prevented wasted work. Make it a standing field.

**Time to prepare:** 5 minutes using session_log.md (last entry) + merdian_reference.json (targeted lookup). Not 30 minutes searching through masters.

---

## Rule 3 — One Concern Per Session

The sessions that degrade fastest mix concerns: debugging a Python import error, then discussing Heston calibration, then debugging a SQL query, then discussing Git protocol. Each topic switch adds context that competes with everything else.

**The rule:** One session = one concern.

| Session type | Goal | What NOT to do |
|---|---|---|
| Code debug | Fix one specific failing component | No architecture discussions |
| Architecture / planning | Design a component or protocol | No code execution |
| Documentation | Produce a specific document | No code execution |
| Live canary | Monitor first live cycle | No new code changes |

**Practical test:** If your session goal requires a comma, it has two concerns. Split it.

**Correct:** "Fix the UPSERT in build_market_state_snapshot_local.py and validate zero duplicate rows."

**Incorrect:** "Fix the UPSERT and also look at the breadth staleness issue and discuss the Heston approach."

---

## Rule 4 — Targeted Context Injection

The single biggest lever on session longevity is what you paste at the start.

**Current pattern (wrong):** Paste the full V18 v2 master at session start. This consumes ~2,000 tokens before a single line of code is written.

**Correct pattern:** Extract only what is relevant to this session's specific goal from `merdian_reference.json`.

### How to extract targeted context

```python
import json
ref = json.load(open('docs/registers/merdian_reference.json'))

# C-01 fix session — paste only these three lookups
print("OPEN ITEM:", json.dumps(ref['open_items']['C-01'], indent=2))
print("FILE:", json.dumps(ref['files']['build_market_state_snapshot_local.py'], indent=2))
print("TABLE:", json.dumps(ref['tables']['market_state_snapshots'], indent=2))
```

**Output size:** ~500 tokens for a targeted lookup vs ~8,000 tokens for a full master paste.

**Result:** Session starts with sharp focus and the context window is preserved for actual work.

### Context by session type

| Session type | Paste from merdian_reference.json |
|---|---|
| Fix a specific open item | `open_items[item_id]` + relevant file entry + relevant table entry |
| Debug a pipeline step | File entry (reads/writes/status) + table entry (constraint/critical_rule) |
| Schema change | Table entry + governance_rules['run_id_vs_symbol_contract'] if relevant |
| AWS sync issue | `environments['aws']` + aws_cron entry + relevant file entry |
| Token refresh issue | `files['refresh_dhan_token.py']` + `open_items['V18A-01']` |

---

## Rule 5 — Session Log Maintenance

The session log is the connective tissue between sessions. It is a single running markdown file — one entry per session, appended continuously, committed to Git at each session end.

**File:** `docs/session_notes/session_log.md`

**Entry format:**

```markdown
## YYYY-MM-DD — [Session type] — [Topic]

**Goal:** [one sentence]
**Session type:** code_debug / architecture / documentation / live_canary / planning
**Completed:**
  - [bullet — what was done with evidence]
  - [bullet]
**Open after session:**
  - [bullet — what remains unresolved]
**Files changed:** [comma-separated list, or "none"]
**Schema changes:** [describe, or "none"]
**Open items closed:** [IDs, or "none"]
**Open items added:** [IDs, or "none"]
**Git commit hash:** [hash at session end]
**Next session goal:** [one sentence — specific]
**docs_updated:** yes / no / na
```

**Why the `docs_updated` field:** Makes documentation debt visible. Three consecutive `no` entries = explicit debt that must be addressed.

**Time to write:** 5 minutes at session end, while context is fresh. The entry becomes the primary input for the next session's resume block.

---

## Rule 6 — Fixture Capture After Clean Sessions

After the first clean live session following any meaningful change, capture and version fixtures immediately. Do not wait — the known-good state will not persist.

**What to capture:**

```
preflight/fixtures/
  idx_i_spot_success_YYYYMMDD.json      — successful IDX_I API response
  optionchain_expirylist_YYYYMMDD.json  — successful expiry list response
  breadth_ltp_sample_YYYYMMDD.json      — sample LTP batch response
  gamma_input_sample_YYYYMMDD.json      — option_chain_snapshots rows used for gamma
  volatility_input_sample_YYYYMMDD.json — option_chain_snapshots rows used for volatility
  momentum_input_sample_YYYYMMDD.json   — source rows for momentum build
```

**Rule:** Fixtures must be from validated successful runs. Never capture from a partially-broken state. Fixtures from a broken state make the replay gate validate against a bad baseline.

**Commit immediately:**

```
MERDIAN: [OPS] Preflight fixtures captured — <date> clean live session
```

---

## Summary — The Complete Cadence

### Before session (5 minutes)

```
1. Read last entry in session_log.md
2. Run: python3 -c "import json; ref=json.load(open('docs/registers/merdian_reference.json')); print(<targeted lookup>)"
3. Write resume block (9 fields, structured)
4. Paste resume block + targeted context only (not full master)
```

### During session

```
Every 20 exchanges: 2-minute checkpoint bullet update
One concern per session — no topic mixing
Code sessions: no architecture. Architecture sessions: no code.
```

### At session end (10 minutes before degradation hits)

```
1. Write/update checkpoint bullets into session_log.md entry
2. Update merdian_reference.json for any changed statuses
3. Update Open Items Register if items closed or added
4. Commit: "MERDIAN: [OPS] Session log + reference JSON updated — YYYY-MM-DD"
5. Note next session goal explicitly in session_log entry
```

### On next session resume

```
Read session_log.md last entry → resume block in 3 minutes
Extract targeted context → paste only what is relevant
Begin without struggle
```

---

## Context Budget Guide

Approximate token costs for common context types. The session window is finite — spend it on work, not on context that is not needed.

| Content | Approx tokens | When to include |
|---|---|---|
| Full V18 v2 master | ~8,000 | Never — use targeted lookup instead |
| Resume block (9 fields) | ~200 | Every session |
| Targeted merdian_reference.json lookup (3 fields) | ~300–500 | Every session |
| Single open item entry | ~150 | When fixing that item |
| Single file entry | ~200 | When touching that file |
| Single table entry | ~150 | When querying/modifying that table |
| Last session_log entry | ~200 | Every session |
| Full Open Items Register | ~3,000 | Only for register update sessions |
| V18A appendix full content | ~4,000 | Only for master compilation sessions |

**Target session start budget:** ~700–1,000 tokens. Leave the rest for actual work.

---

## When to Start a New Session

Start a new session when any of these are true:

```
☐ Response latency exceeds 30 seconds consistently
☐ AI is repeating things already established earlier in the session
☐ AI gives an answer that contradicts a decision made earlier in the session
☐ More than 80 significant exchanges have occurred
☐ The session goal has been achieved (do not continue on a new topic — start fresh)
```

**The wrong time to start a new session:** When you are mid-debug with important state in the context. Write a checkpoint first, then start the new session.

---

*MERDIAN Session Management v1 — 2026-03-31 — Commit to Git. Do not modify without updating version number.*
