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
| Verify Kite auth before market open | `docs/runbooks/runbook_update_kite_flow.md` Step 3 — runs `/home/ssm-user/meridian-engine/check_kite_auth.py` (persisted Session 10) |
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
13. **Data contamination registry.** Before running ANY research query or experiment that reads hist_* tables, check `public.data_contamination_ranges`. See Rule 13 section below.
14. **`ret_30m` in `hist_pattern_signals` is stored as PERCENTAGE POINTS, not decimal fraction.** e.g., 0.1351 means 0.1351% of spot, NOT 13.51%. Divide by 100 before multiplying by spot price. Sign convention: BEAR_OB wins when `ret_30m < 0` (spot fell). BULL_OB wins when `ret_30m > 0`. Confirmed Session 11 via diagnostic query. Any script that uses this field must apply the division. (Lesson from Exp 41 which inflated E4/E5 P&L by 100x — corrected in Exp 41B.)
15. **Supabase hard-caps at 1000 rows per request.** `range(0, 4999)` still returns only 1000. Always set `page_size = 1000` in pagination loops, and terminate when `len(batch) < 1000`. Confirmed Session 11 — Exp 34 initially fetched only 130 of 18,895 bars because page_size was 5000. (Rule added 2026-04-28.)
16. **TD-029 timezone workaround for hist_spot_bars_5m.** `bar_ts` is stored as IST labeled as `+00:00`. Do NOT use `astimezone(IST)` — this adds 5:30 and shifts all bars. Use `dt.replace(tzinfo=None)` to treat the stored value as naive IST directly. Confirmed Session 11 — Exp 34 initial run had 3,450 bars instead of 18,895 due to this bug. (Rule added 2026-04-28.)

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
- ❌ Designing an alternative experiment to research code without first running the research code AS-IS to establish baseline replication — Session 10 Exp 31/32 burned a half-day on a false-negative loop and produced a wrong "Path A" recommendation (later retracted) because Exp 15 wasn't run as-written first. If research code replicates, alternatives may add insight; if research code doesn't replicate, that is the question to answer first, before any alternative is designed.
- ❌ Heredoc-pasting Python scripts via SSM (`cat > file.py <<EOF ... EOF`) — invisible non-printing characters can survive nano/cat visual checks but break the Python parser silently (Session 10 morning Kite auth debug). Always nano-type Step 3 verification scripts. SSM TTY can hang silently; `echo hello` is the canary before running anything substantive.
- ❌ Using `is_pre_market` as a column name in `hist_spot_bars_5m` — this column does not exist. Filter by time: `09:15 ≤ bar_ts_IST ≤ 15:30`. Apply TD-029 workaround (Rule 16). (Session 11 bug B1.)
- ❌ Setting `page_size > 1000` in Supabase pagination — Supabase hard-caps at 1000 rows per request regardless. Use `page_size = 1000` and loop. (Session 11 bug B2 / Rule 15.)
- ❌ Using `astimezone(IST)` on `hist_spot_bars_5m.bar_ts` — bar_ts is stored as IST labeled +00:00. Converting timezone adds 5:30 and shifts all bars out of market hours. Use `replace(tzinfo=None)` instead. (Session 11 bug B3 / Rule 16.)
- ❌ Using `ret_30m` from `hist_pattern_signals` as a decimal fraction — it is stored as percentage points. Divide by 100 first. (Session 11 Rule 14.)
- ❌ Reading a Python source file with `Path.read_text(encoding='utf-8')` then calling `ast.parse()` on it when the file has a UTF-8 BOM — `ast.parse` rejects U+FEFF with `invalid non-printable character`. Always use `read_bytes() + decode('utf-8-sig')` in patch scripts. (Session 11 extension — v1 of F3 patch caught this correctly and aborted.)
- ❌ Writing a patched file back with `Path.write_text(text, encoding=...)` on Windows when the original file has LF line endings — `write_text` translates `\n → \r\n` on output, silently converting the file to CRLF and producing a noisy `git diff` showing every line modified. Always use `write_bytes(text.encode(enc))` for symmetric byte handling. v3 of F3 patch is the canonical pattern. (Session 11 extension.)
- ❌ Trusting the dashboard EXIT AT label for trade exit timing — the label slices the UTC timestamp string directly (`exit_ts[11:16]`), not the IST-converted version. On a 09:31 IST signal this shows 04:31, not 10:01. Compute exit time manually: signal IST + 30 minutes. (TD-038, Session 11 extension.)
- ❌ Trusting `direction_bias` when `wcb_regime=NULL` in `signal_snapshots` — `wcb_regime` has been NULL since 2026-03-19 (regression, only 32/2171 rows ever populated). On BULLISH breadth days this caused `direction_bias=BEARISH` producing BUY_PE on BULL_FVG. Do not trade on `direction_bias` until TD-035 is fixed and `wcb_regime` is populated. (Session 11 extension live session.)

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
- ✅ **Compendium replicates** (Exp 15 re-run 2026-04-27, Session 10) — BEAR_OB ~92% WR, BULL_OB ~84%, MEDIUM context ~77%, combined +193.4% return. The system has real, durable, year-validated edge. Earlier Session 10 wave-1 conclusion that "compendium does not replicate" was **measurement error in Exp 31/32**, explicitly retracted. Do not re-run Exp 31/Exp 32 as evidence of edge absence.
- ✅ **F2 (1H OB threshold tuning) REJECTED** (Exp 29 v2, 2026-04-26, Session 10) — full-year sweep over {0.15, 0.20, 0.25, 0.30, 0.40}% confirmed current 0.40% maximises WR for NIFTY; SENSEX peaks at 0.30%. No threshold cleared the 70%/N≥30 ship bar. Threshold is not the lever for surfacing more MEDIUM-context candidates.
- ✅ **Path A retracted** (Session 10) — the framing "stop pretending ICT is the edge" was wrong. Compendium replicates. Do not re-introduce Path A under different names.
- ✅ **Naked intraday PDH/PDL sweeps have no edge** (Exp 34, Session 11) — WR=11.1% (PDH), 1.8% (PDL) at T+60m. ~0.73 events/session — normal mean reversion, not institutional. Do not retest without structural change.
- ✅ **PDL DTE<3 next-week CE = SKIP** (Exp 35D, Session 11) — T+1D WR=42.9%. EOD bounce is mechanical expiry pinning, not institutional. Fades next day. Confirmed.
- ✅ **BEAR_OB AFTERNOON + PO3_BEARISH = 33.3% WR** (Exp 40, Session 11) — the distribution move is already done by AFTERNOON on bearish-bias sessions. Hard skip. Do not trade.
- ✅ **BULL_OB MIDDAY + PO3_BULLISH = 30.3% WR** (Exp 40, Session 11) — premature. Bullish accumulation doesn't resolve until AFTERNOON London open. Hard skip.
- ✅ **NIFTY BULL_OB AFTERNOON + PO3_BULLISH = 50% WR** (Exp 40, Session 11) — no edge on NIFTY for this signal. SENSEX only (73.7%). Do not route NIFTY here.
- ✅ **Current-week PE beats next-week PE for PDH DTE<3** (Exp 41, Session 11) — NIFTY mean +46% vs +20%, SENSEX mean +125% vs +68%. Current-week captures gamma explosion. Settled.
- ✅ **Entry at T+0 (rejection bar close) always beats waiting** (Exp 41, Session 11) — waiting 1 bar hurts across all edges and both symbols. Never wait.
- ✅ **TD-017 CLOSED** (Session 11 extension, 2026-04-28) — `build_ict_htf_zones.py` now scheduled daily 08:45 IST via `MERDIAN_ICT_HTF_Zones_0845` Task Scheduler. ENH-71 instrumented. Do not reopen.
- ✅ **TD-030 CLOSED** (Session 11 extension, 2026-04-28) — `recheck_breached_zones()` added; runs after OHLCV load each day, marks mitigated ACTIVE zones BREACHED. 72 zones now written per run (was 35). Do not reopen.
- ✅ **TD-031 CLOSED** (Session 11 extension, 2026-04-28) — OB/FVG patterns written unconditionally; breach filter retained for PDH/PDL proximity only. D BEAR_OB will appear ACTIVE at 08:45 IST on next down day regardless of overnight recovery. Do not reopen.
- ✅ **TD-032 dashboard opt_type wrong framing SETTLED** — root cause is NOT 'dashboard hardcodes direction off pattern_type'. Root cause IS `build()` read `opt_type` from `ict_zones.opt_type` (ICT zone direction BEFORE ENH-35 gate overrides). Patched Session 11 extension. Pending 10-cycle live verification to formally close. Do not re-introduce the pattern-hardcoding framing.

If any of these need to change, that is itself an architectural session — write a new ADR.

---

## Rule 13 — Data contamination registry (added Session 7, 2026-04-23)

MERDIAN tracks known data-integrity incidents in the Supabase table `public.data_contamination_ranges`. Before running ANY research query, experiment analysis, or model training that reads fields listed in `field_scope` from tables listed in `affected_tables`, check whether the query time window overlaps with a registered contamination range.

**Standard check — SQL helper:**

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

## Session 11 engineering discoveries (2026-04-28) — now codified as Rules 14-16

Three bugs were found and fixed across all Session 11 experiment scripts. They are now rules so future sessions don't repeat the debugging cycle:

**Bug B1 → Rule 14:** `hist_pattern_signals.ret_30m` is percentage points, not decimal. Divide by 100.

**Bug B2 → Rule 15:** Supabase pagination max is 1000 rows/request. Use `page_size = 1000`.

**Bug B3 → Rule 16:** `hist_spot_bars_5m.bar_ts` stored as IST labeled `+00:00`. Use `replace(tzinfo=None)`, not `astimezone(IST)`.

**Bug B4 (non-rule, one-time):** `hist_spot_bars_5m` has no `is_pre_market` column. Filter by `09:15 ≤ bar_ts_IST ≤ 15:30` instead.

---

## Session 11 extension engineering discoveries (2026-04-28) — operational safety

Three operational findings from the Session 11 extension (engineering + live session). These are anti-patterns codified above (Rules not needed — these are one-time discoveries, not recurring schema bugs):

**Patch script encoding hazards (now anti-patterns):**
- BOM: `ast.parse` rejects U+FEFF in string. Use `read_bytes() + decode('utf-8-sig')` in all patch scripts. v1 of F3 patch caught this correctly via abort.
- CRLF: `write_text()` on Windows translates `\n → \r\n`. Use `write_bytes(text.encode(enc))`. v3 of F3 patch is canonical template.

**Live session findings (2026-04-28, 09:15-15:30 IST):**
- **FIRST GATE OPEN**: SENSEX `trade_allowed=true` fired at 09:16 IST (BULL_FVG TIER2 VERY_HIGH MTF). ENH-46-A Telegram delivered simultaneously. First-ever production gate open.
- **wcb_regime regression**: `direction_bias=BEARISH` while `breadth_regime=BULLISH` all session. `wcb_regime=NULL` since 2026-03-19 (32/2171 rows ever populated). Without WCB, direction computation is unreliable on breadth-driven days. **TD-035 elevated to S2. Do not trade direction_bias signals until fixed.**
- **EXIT AT timer shows UTC**: dashboard EXIT AT label slices UTC timestamp directly. Compute exit time manually: signal IST + 30 min. TD-038 filed. **Live trading risk until fixed.**
- **SENSEX DTE=2 on expiry day**: expected DTE=0 on 2026-04-28 monthly expiry. TD-039 filed.

---

*CLAUDE.md v1.7 — 2026-04-28 (Session 11 extension close). Added: (a) four new anti-patterns — BOM in patch scripts, CRLF write_text hazard, EXIT AT UTC display bug, wcb_regime NULL direction_bias warning; (b) five new settled-decisions — TD-017/030/031 CLOSED, TD-032 framing settled; (c) Session 11 extension engineering discoveries section documenting live session findings (first gate open, wcb regression, exit timer bug, DTE bug). v1.6 (Session 11 research close) added Rules 14/15/16 and B1-B4 engineering discoveries. v1.5 added compendium-replicates + F2-rejected + anti-patterns. v1.4 corrected Local Python path. v1.3 Rule 13. v1.2 Rule 12. v1.1 Rule 11.* Added: (a) Rules 14/15/16 — ret_30m scale (÷100), Supabase 1000-row hard cap, TD-029 timezone workaround; (b) four new anti-patterns matching B1/B2/B3/B4 bugs; (c) eight new settled-decisions entries covering Session 11 experiment conclusions; (d) Session 11 engineering discoveries section documenting B1-B4 for future sessions. v1.5 (2026-04-27) added compendium-replicates, F2-rejected, Path-A-retracted decisions + two anti-patterns + Kite-auth common-ops row. v1.4 corrected Local Python path. v1.3 Rule 13 contamination registry. v1.2 Rule 12 doc-sync. v1.1 Rule 11 runbooks.*
