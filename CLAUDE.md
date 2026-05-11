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
17. **`market_spot_session_markers` column names differ from documentation.** `open_0915` does not exist as a column — the live column is `open_0915_ts`. Do NOT query `market_spot_session_markers` for open price or gap data. Derive `open_0915` from the first tick in `market_spot_snapshots` for the OPEN window (09:15–10:00 IST). Derive `gap_open_pct` from `(open_0915 - prev_close) / prev_close * 100` where `prev_close` is the last bar close from `hist_spot_bars_5m`. Confirmed Session 13 — `detect_po3_session_bias.py` bypasses this table entirely. (Rule added 2026-04-29.)

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
- ❌ Using `astimezone(IST)` on `hist_spot_bars_5m.bar_ts` — bar_ts is stored as IST labeled +00:00. Converting timezone adds 5:30 and shifts all bars out of market hours. Use `replace(tzinfo=None)` instead. (Session 11 bug B3 / Rule 16.) **NOTE: This is era-conditional. Pre-04-07 use `replace(tzinfo=None)`; post-04-07 use `astimezone(IST)`. See Rule 20 (Session 15) for era-aware helper.**
- ❌ Using `ret_30m` from `hist_pattern_signals` as a decimal fraction — it is stored as percentage points. Divide by 100 first. (Session 11 Rule 14.)
- ❌ Reading a Python source file with `Path.read_text(encoding='utf-8')` then calling `ast.parse()` on it when the file has a UTF-8 BOM — `ast.parse` rejects U+FEFF with `invalid non-printable character`. Always use `read_bytes() + decode('utf-8-sig')` in patch scripts. (Session 11 extension — v1 of F3 patch caught this correctly and aborted.)
- ❌ Writing a patched file back with `Path.write_text(text, encoding=...)` on Windows when the original file has LF line endings — `write_text` translates `\n → \r\n` on output, silently converting the file to CRLF and producing a noisy `git diff` showing every line modified. Always use `write_bytes(text.encode(enc))` for symmetric byte handling. v3 of F3 patch is the canonical pattern. (Session 11 extension.)
- ❌ Trusting the dashboard EXIT AT label for trade exit timing — the label slices the UTC timestamp string directly (`exit_ts[11:16]`), not the IST-converted version. On a 09:31 IST signal this shows 04:31, not 10:01. Compute exit time manually: signal IST + 30 minutes. (TD-038, Session 11 extension.)
- ❌ Trusting `direction_bias` when `wcb_regime=NULL` in `signal_snapshots` — `wcb_regime` has been NULL since 2026-03-19 (regression, only 32/2171 rows ever populated). On BULLISH breadth days this caused `direction_bias=BEARISH` producing BUY_PE on BULL_FVG. Do not trade on `direction_bias` until TD-035 is fixed and `wcb_regime` is populated. (Session 11 extension live session.)
- ❌ Querying `market_spot_session_markers` for `open_0915` or `gap_open_pct` — the live column is `open_0915_ts`, not `open_0915`. Derive open price from `market_spot_snapshots` first tick in OPEN window. Derive gap from `hist_spot_bars_5m` prev_close. (Session 13 Rule 17.)
- ❌ Running `merdian_start.py` on AWS — this script uses `creationflags=CREATE_NO_WINDOW` (Windows-only) and hardcoded Windows paths. It will hang or error on Linux. Session 13: caused a frozen SSM terminal requiring EC2 reboot. AWS uses `python3 gamma_engine_supervisor.py` or individual script launches.
- ❌ Appending to a Windows batch file with `Add-Content` when there is an `exit /b` line — the appended line runs after `exit /b` and never executes. Always use string replacement to insert before the exit line. (Session 13 bat file patch.)

---

## Project file layout

```
C:\GammaEnginePython\                 (Windows local, PRIMARY LIVE)
/home/ssm-user/meridian-engine\        (AWS, SHADOW — git pull only)

  CLAUDE.md                           <- THIS FILE — root entry point
  *.py                                <- engine code
  .env                                <- secrets, never commit

  docs/
    operational/
      MERDIAN_Change_Protocol_v1.md
      MERDIAN_Documentation_Protocol_v3.md   <- supersedes v2
      MERDIAN_Session_Management_v1.md
      MERDIAN_Testing_Protocol_v1.md         <- consolidated preflight/canary/replay

    registers/
      merdian_reference.json          <- machine-queryable inventory (authoritative on op state)
      MERDIAN_Enhancement_Register_v<n>.md
      tech_debt.md                    <- persistent middle-tier issues

    runbooks/                         <- step-by-step procedures for recurring ops
      README.md                       <- index of all runbooks
      RUNBOOK_TEMPLATE.md             <- template for new runbooks
      runbook_update_dhan_token.md
      runbook_update_kite_flow.md
      runbook_*.md                    <- grows as recurring ops surface

    session_notes/
      CURRENT.md                      <- live session resume -- updated EVERY session
      session_log.md                  <- append-only one-line per session
      YYYYMMDD_<topic>.md             <- per-session detail when warranted

    decisions/                        <- optional ADRs (one per major decision)
      ADR-001-options-only.md
      ADR-002-5m-for-ict.md
      ...

    research/
      MERDIAN_Experiment_Compendium_v<n>.md
      merdian_all_experiment_results.md

    masters/                          <- .docx PUBLISHED ARTIFACTS (generated on demand)
      MERDIAN_Master_V<n>.docx

    appendices/                       <- .docx PUBLISHED ARTIFACTS (generated on demand)
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
- ✅ **F1 (ICT zone time_zone classification) SHIPPED** (2026-04-27, Session 10) — `fix_ict_time_zone_utc.py` converted UTC→IST before time-bucket assignment. Verified live.
- ✅ **F2 (1H OB threshold tuning) REJECTED** (Exp 29 v2, 2026-04-26, Session 10) — full-year sweep over {0.15, 0.20, 0.25, 0.30, 0.40}% confirmed current 0.40% maximises WR for NIFTY; SENSEX peaks at 0.30%. No threshold cleared the 70%/N≥30 ship bar. Threshold is not the lever for surfacing more MEDIUM-context candidates.
- ✅ **Path A retracted** (Session 10) — the framing "stop pretending ICT is the edge" was wrong. Compendium replicates. Do not re-introduce Path A under different names.
- ✅ **Naked intraday PDH/PDL sweeps have no edge** (Exp 34, Session 11) — WR=11.1% (PDH), 1.8% (PDL) at T+60m. ~0.73 events/session — normal mean reversion, not institutional. Do not retest without structural change.
- ✅ **PDL DTE<3 next-week CE = SKIP** (Exp 35D, Session 11) — T+1D WR=42.9%. EOD bounce is mechanical expiry pinning, not institutional. Fades next day. Confirmed.
- ✅ **BEAR_OB AFTERNOON + PO3_BEARISH = 33.3% WR** (Exp 40, Session 11) — the distribution move is already done by AFTERNOON on bearish-bias sessions. Hard skip. Do not trade.
- ✅ **BULL_OB MIDDAY + PO3_BULLISH = 30.3% WR** (Exp 40, Session 11) — premature. Bullish accumulation doesn't resolve until AFTERNOON London open. Hard skip.
- ✅ **NIFTY BULL_OB AFTERNOON + PO3_BULLISH = 50% WR** (Exp 40, Session 11) — no edge on NIFTY for this signal. SENSEX only (73.7%). Do not route NIFTY here.
- ✅ **Current-week PE beats next-week PE for PDH DTE<3** (Exp 41, Session 11) — NIFTY mean +46% vs +20%, SENSEX mean +125% vs +68%. Current-week captures gamma explosion. Settled.
- ✅ **Entry at T+0 (rejection bar close) always beats waiting** (Exp 41, Session 11) — waiting 1 bar hurts across all edges and both symbols. Never wait.
- ✅ **TD-017 CLOSED** (Session 11 extension, 2026-04-28) — `build_ict_htf_zones.py` now scheduled daily 08:45 IST via `MERDIAN_ICT_HTF_Zones_0845` Task Scheduler. ENH-71 instrumented. Hourly zones (`--timeframe H`) added to bat file Session 13.
- ✅ **TD-030 CLOSED** (Session 11 extension, 2026-04-28) — `recheck_breached_zones()` added; runs AFTER all upserts (ordering bug fixed Session 13). 72 zones now written per run (was 35). Do not reopen.
- ✅ **TD-031 CLOSED** (Session 11 extension, 2026-04-28) — OB/FVG patterns written unconditionally; breach filter retained for PDH/PDL proximity only. D BEAR_OB will appear ACTIVE at 08:45 IST on next down day regardless of overnight recovery. Do not reopen.
- ✅ **TD-032 dashboard opt_type wrong framing SETTLED** — root cause is NOT 'dashboard hardcodes direction off pattern_type'. Root cause IS `build()` read `opt_type` from `ict_zones.opt_type` (ICT zone direction BEFORE ENH-35 gate overrides). Patched Session 11 extension. Pending 10-cycle live verification to formally close. Do not re-introduce the pattern-hardcoding framing.
- ✅ **ENH-75 SHIPPED** (Session 13, 2026-04-29) — PO3 session bias detection live. `detect_po3_session_bias.py` running Mon-Fri 10:05 IST. `po3_session_state` table live. `signal_snapshots.po3_session_bias` column populated. Do not reopen design.
- ✅ **ENH-76 SHIPPED** (Session 13, 2026-04-29) — BEAR_OB MIDDAY 11:30-13:30 IST gated on PO3_BEARISH. 88.2% WR (Exp 40). Wired in `build_trade_signal_local.py`.
- ✅ **ENH-77 SHIPPED** (Session 13, 2026-04-29) — BULL_OB AFTERNOON SENSEX 13:30-15:00 IST gated on PO3_BULLISH. 73.7% WR (Exp 40). NIFTY hard skip (50% WR). Wired.
- ✅ **Exp 42 DONE** (Session 13, 2026-04-29) — BEAR_OB MIDDAY occurs in 72.5% of all sessions. Unfiltered WR=48%, EV negative. PO3_BEARISH is the rare gate (~7% of sessions). Composition rate question answered. Do not re-run.
- ✅ **ENH-85 direction lock REVERTED** (Session 13) — PO3 session lock patch built and reverted. Needs Exp 43 (Signal Direction Stability) before re-implementing. Do NOT re-apply ENH-85 without experiment backing. `build_trade_signal_local.pre_enh85.bak` on disk.
- ✅ **ENH-78 SHIPPED** (Session 14, 2026-04-30) — DTE<3 PDH sweep current-week PE rule live in `build_trade_signal_local.py`. Guarded by `po3_session_bias=PO3_BEARISH AND 1<=dte<=2 AND action=BUY_PE`. Evidence: Exp 35D 90.9% EOD WR (N=11). Stop rule: 40% premium OR PDH reclaim.
- ✅ **ENH-84 SHIPPED** (Session 14, 2026-04-30) — Dashboard 🔄 REFRESH ZONES button + `/refresh_and_download_pine` endpoint. With hotfix for `sys.executable` reference. Live verified.
- ✅ **ENH-86 v1 SHIPPED** (Session 14, 2026-04-30) — WIN RATE legend extended to 7 columns with EV + N. Live rows for E4/E5 added at top. v2 (BLOCKED/ALLOWED visual prominence) deferred — not blocking.
- ✅ **TD-044 CLOSED** (Session 14, 2026-04-30) — ENH-76/77 local var / `out` dict drift fixed. Three-site sync in `build_trade_signal_local.py`. Side effect: file line endings normalised to uniform CRLF. Do NOT reopen — ENH-76/77 gates now correctly persist to DB headline fields.
- ✅ **TD-038 EXIT AT IST PATCH SHIPPED** (Session 14, 2026-04-30) — `merdian_signal_dashboard.py` `card()` now converts UTC→IST for the static EXIT AT label. Mirrors sig_ts conversion. Live verification pending next TRADE_ALLOWED signal.
- ✅ **Breach detection ordering FIXED** (Session 13) — `recheck_breached_zones()` now runs after all `upsert_zones()` calls. Upsert no longer overwrites BREACHED→ACTIVE. Fixed permanently.
- ✅ **ADR-008 Accepted** (Session 24, 2026-05-09) — Replay is a parallel-pipeline sandbox for what-if signal experiments — comparison of two replay runs with one code change, against the same frozen historical data — not a tool to chase bit-identical reproduction of live `signal_snapshots`. Zero touch on live tables; out-of-hours hard guard; boundary-driven orchestrator (scripts in V19 §5.2 order PER BOUNDARY, not script-by-script). Strike-base / spot-granularity / VIX-source divergences from live are documented architectural properties, not bugs. ENH-93 CLOSED via this ADR. The "What 'what-if experiment' means" methodology canonical entry lives in ADR-008.
- ✅ **Phase α Q1 ANSWERED** (Session 25, 2026-05-10) — Zone validity model = (a) pure price-based canonical with timeframe-tiered fallback intraday-only. 1H OB/FVG = price-breach OR 1 week (whichever first); D/W OB/FVG = price-breach only, `valid_to=NULL`; PDH/PDL = date-expire (unchanged). Three implementation actions queued for ADR-005 drafting: `expire_old_zones()` rewrite by `(pattern_type, timeframe)`, `recheck_breached_zones()` as primary D/W transition, backfill pass for D/W zones currently date-EXPIRED unbreached. Independent of ADR-006; can draft anytime. Do not re-litigate; the answer is settled.
- ✅ **Phase α Q2 ANSWERED** (Session 25, 2026-05-10) — AWS migration scope = (a) capture/derived split with four-stage decomposition. Capture stage (`market_spot_snapshots`, `option_chain_snapshots`, `india_vix`, `market_breadth_intraday`, `ict_htf_zones`) → AWS canonical, no Local writers. Derived stage (`gamma_metrics`, `volatility_snapshots`, `momentum_snapshots`, `market_state_snapshots`, `signal_snapshots`) → Local canonical for production; AWS shadow continues writing to `*_shadow` tables. Orchestration stage (runner) → both Local (production) and AWS (shadow) parallel. Operator-facing tooling (dashboard, signal dashboard, exit monitor, trade logger, ICT zone visualizer) → Local only. ADR-006 will codify; do not re-litigate the principle.
- ✅ **Phase α Q3 ANSWERED** (Session 25, 2026-05-10) — Sequencing: token reliability FIRST, then ADR-006 actions. Investigate `refresh_dhan_token.py` failure mode (TD-080) → fix → observe N clean trading days → only then execute ADR-006 disposals. Local writers stay as redundancy until AWS reliability empirically established. **ADR-006 drafting is BLOCKED on TD-080 closure.** Do not re-litigate the order.
- ✅ **Phase α Q4 ANSWERED** (Session 25, 2026-05-10) — Calibration discipline = graduated-strictness holdout (operator deferred to architect recommendation). Phase 1 (now → ~April 2027 / Y2 close): mandatory holdout split scaled by N — N≥60 → 67/33, 10pp tolerance; 30≤N<60 → 75/25, 15pp; N<30 → "low-N calibration-only" tag, no split required. Existing Exp 15-era params get 60-day prospective parity check, flag drift >15pp. Phase 2 (Y2 close): rolling walk-forward — 12-month calibration / 3-month holdout, slide quarterly. Status quo single-cohort silent waiver explicitly REJECTED. ADR-009 will codify; §D.8 of Assumption Register has the working draft.
- ✅ **TD-097 RESOLVED + ENH-96 SHIPPED same-session** (Session 25, 2026-05-10) — Dashboard pre-open status URL-encoding bug producing 0% accuracy widget; root cause: double URL encoding from passing already-encoded query string into `requests.get(..., params={...})`. Fix: collapse into single fully-encoded URL via `urllib.parse.urlencode()`. Patch script `patch_s25_dashboard_preopen_gap.py` (v3 patch canon) deployed 5 substitutions to `merdian_live_dashboard.py`; backups `_PRE_S25.py` + `_PRE_S25b.py` preserved. ENH-96 dashboard "Gap (vs prev close)" card shipped as side-effect — data was already captured in `market_spot_snapshots`, just not surfaced. Do not revert the URL-encoding fix; same bug pattern exists in 5 other scripts (TD-099 sweep pending).
- ✅ **TD-080 REFRAMED** (Session 25, 2026-05-10) — Original framing "Dhan option chain endpoint reliability" narrowed to "AWS Dhan token refresh failure mode" based on cross-script Dhan 401 evidence on 2026-05-07 (PreOpen 03:38 UTC + option chain 09:30-13:30 IST + 14:45-15:25 IST consistent with single token-refresh failure on AWS, not Dhan-side service incident). Investigation surface narrows from "Dhan API" to "`refresh_dhan_token.py` running on AWS at 03:05 UTC". Explicit Blocks: ADR-006 drafting per Phase α Q3. Do not investigate Dhan-vendor-side hypotheses again until AWS-token-refresh hypothesis is fully tested.
- ✅ **TD-078 RESOLVED** (Session 25, 2026-05-10) — TD-070 v2 multi-week BULL_OB lookback verified via SQL. The apparent missing Apr-13 row was a schema-convention misunderstanding (W-timeframe `source_bar_date` is week-start Monday, not arbitrary calendar date). TD-070 v2 fires as designed. **Convention codified:** `ict_htf_zones.source_bar_date` semantics differ by timeframe — W = week-start Monday, D = bar's calendar date, 1H = hour bucket date. Whenever debugging "missing zone row" claims, check the timeframe-aware convention before concluding the row is absent.
- ✅ **`MERDIAN_PreOpen` (Local 09:05 IST) DISABLED** (Session 25, 2026-05-10) — Auction-window writer disposed via PowerShell `Disable-ScheduledTask`, durable across reboots. Operator semantic: "9:05 read meaningless" (call auction prices are not tradeable price discovery). Code dependency check: `ret_session` migrated 09:05 → 09:08 anchor and validated via ADR-008 replay infrastructure (first non-construction use of replay system). AWS sole writer at 09:08. Mon 2026-05-12 verification plan in Topology §9.A. Do not re-enable Local 09:05 task without reverting `ret_session` anchor.
- ✅ **Topology §9 Q1 + Q2 CLOSED** (Session 25, 2026-05-10) — §9 Q1: post-market 16:00 dual-write empirically confirmed across 2026-05-04 → 2026-05-08 (5 trading days); disposition queued for ADR-006 execution gated on TD-080. §9 Q2: original framing inaccurate (no actual dual-write at 09:08 IST; AWS sole writer at that boundary; Local 09:05 was different boundary). §9 Q8 PARTIAL EVIDENCE (Postmarket cron 5-day reliability captured). §9.A NEW documents Local PreOpen disposal + ret_session migration. Do not re-investigate "is there dual-write at 09:08" — answer is no.

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

**Bug B3 → Rule 16:** `hist_spot_bars_5m.bar_ts` stored as IST labeled `+00:00`. Use `replace(tzinfo=None)`, not `astimezone(IST)`. **(Era-conditional — pre-04-07 only. See Rule 20 for the post-04-07 path: `astimezone(IST_TZ)`.)**

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

## Session 13 engineering discoveries (2026-04-29) — codified as Rule 17

**Bug B5 → Rule 17:** `market_spot_session_markers.open_0915` does not exist in production. Live column is `open_0915_ts`. Never query this table for open price. Use `market_spot_snapshots` first tick instead.

**Operational findings (2026-04-29):**
- **ws_feed_zerodha.py not in any startup sequence** — `market_ticks` table empty all session → breadth ingest returns 0 ticks → breadth = 0 / stale all day. Fixed: `MERDIAN_WS_Feed_0900` task registered.
- **merdian_start.py is LOCAL-ONLY** — contains `creationflags=CREATE_NO_WINDOW` (Windows Win32 API) and hardcoded `C:\GammaEnginePython` base path. Running on AWS causes terminal hang. Requires EC2 reboot to recover. Do not run on AWS.
- **bat file `Add-Content` pitfall** — appending lines after `exit /b` with `Add-Content` means they never execute. Always replace the exit line, don't append after it.
- **Pine `bar_index - look_back` goes negative** — on daily charts, zones >252 trading days old produce negative bar indices, silently killing all drawings. Fix: `math.max(0, bar_index - look_back)`.
- **Pine `draw_zone` forward-reference** — `is_nifty`/`is_sensex` must be declared BEFORE `draw_zone` function, not after. Pine evaluates top-to-bottom; forward references fail at runtime.

---

## Session 14 engineering discoveries (2026-04-30) — codified as Rules 18-19

**Bug B6 → Rule 18:** Patch scripts MUST be line-ending agnostic. After three sessions of patches, files accumulate mixed line endings — Session 14 found `build_trade_signal_local.py` with 1039 CRLF + 87 bare-LF lines. Single-EOL `replace()` fails when the anchor crosses a mixed-EOL boundary. Canonical pattern:

```python
src_raw = TARGET.read_bytes().decode("utf-8-sig")
crlf = src_raw.count("\r\n")
bare_lf = src_raw.count("\n") - crlf
write_eol = "\r\n" if crlf >= bare_lf else "\n"

# Match in LF-space (anchors are LF in patch source)
src_lf = src_raw.replace("\r\n", "\n")
patched_lf = src_lf.replace(OLD, NEW)

# Restore predominant EOL on write
patched_out = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
TARGET.write_bytes(patched_out.encode("utf-8"))
```

This pattern also normalises mixed line endings as a side effect — file becomes uniformly EOL-consistent post-patch.

**Bug B7 → Rule 19:** Before writing endpoint code that references module-level attributes (`sys.executable`, `os.path`, etc.), grep imports in target file at module level. Imports inside functions don't expose those names to top-level / endpoint scope. Session 14 ENH-84 endpoint used `sys.executable` but `merdian_signal_dashboard.py` only had `import sys as _sys` deep inside `build()` — endpoint scope had no `sys` reference. Hotfix replaced with literal `"python"`.

```bash
# Quick check before referencing module attributes in patches:
grep -n "^import\|^from " target_file.py
```

**Operational findings (2026-04-30 morning):**
- **AWS SSH IP rotation** — operator's home network has multi-WAN with Airtel/BBNL failover. SG inbound rules with `/32` IPs break whenever ISP fails over. Long-term fix: AWS Systems Manager Session Manager (no SSH, no IP, no SG port 22 rule needed). Documented in tech_debt as operational note (not yet a TD).
- **Dashboard zombie listeners** (recurring) — multi-PowerShell-window habit during testing leaves orphan instances bound to port 8766. Standard pattern: `netstat -ano | findstr :8766 | findstr LISTENING` → `taskkill /F /PID <pid>` for each → restart. Long-term fix: move dashboard to Task Scheduler entry instead of foreground PowerShell.
- **`build_ict_htf_zones.py` contract violation noise** — script declares `expected_writes={'ict_htf_zones': 1}` unconditionally; legitimately writes 0 on idempotent reruns and pre-market windows. Fires false-alarm Telegram alerts. Filed TD-046. Operator must correlate alert against `script_execution_log` to identify the canonical 08:45 scheduled run vs noise reruns.
- **`ict_zones` vs `ict_htf_zones` confusion** — TWO TABLES with different schemas. `ict_zones` (BULL_FVG only, 54 rows total, schema: `symbol, trade_date, pattern_type, zone_low, zone_high, detected_at_ts, status`) is largely orphaned for current pipeline. `ict_htf_zones` (OBs+PDH/PDL+W zones, schema: `id, symbol, timeframe, pattern_type, direction, zone_high, zone_low, zone_mid, valid_from, valid_to, source_bar_date, status, broken_at_date, break_price, created_at, updated_at`) is the canonical table — what dashboard, Pine generator, and signal engine consume. Filed TD-047. Always query `ict_htf_zones` for D/W/H zones with `valid_from <= today <= valid_to AND status='ACTIVE'`. Reserve `ict_zones` queries for explicit BULL_FVG intraday questions.
- **Numbering collision in `tech_debt.md`** — TD-038 and TD-039 each appear twice (Active section + Resolved section, different topics). Pre-existing register hygiene issue. Do NOT renumber — the dual entries are now distinguishable by content (TD-038-A=is_pre_market column; TD-038-B=EXIT AT IST). Fixing collisions retroactively risks breaking external references.

---

## Session 15 engineering discoveries (2026-05-02) — codified as Rule 20

**Bug B8 → Rule 20:** Rule 16 (`hist_spot_bars_5m.bar_ts` use `replace(tzinfo=None)` instead of `astimezone(IST)`) is **era-conditional, not universal**. The era boundary is **2026-04-07**.

| Era | Storage convention | Correct handling |
|---|---|---|
| **Pre-04-07** (legacy ingest) | Bars stored as IST clock-time labelled `+00:00` (TD-029 root cause) | `bar_ts.replace(tzinfo=None)` then filter by `09:15 ≤ time ≤ 15:30` (Rule 16 verbatim) |
| **Post-04-07** (current writer) | Bars stored as true UTC | `bar_ts.astimezone(IST_TZ)` then filter by `09:15 ≤ time ≤ 15:30` |

Applying Rule 16 verbatim to post-04-07 data drops most of the day. Concretely: `replace(tzinfo=None)` on a UTC-stored bar produces a UTC clock-time. Filtering UTC clock-time to 09:15-15:30 IST keeps only bars in the UTC 09:15-10:00 window (= IST 14:45-15:30, the last 45 min of session) → ~9 of ~76 in-session bars per day = **27.5% bar coverage** false alarm.

**Canonical era-aware helper** (use this in any script that needs in-session 5m bars across the era boundary):

```python
from datetime import time, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"  # exclusive: dates < this use Rule 16; >= this use astimezone

def in_session_filter(bar_ts, trade_date_str):
    """Returns True if bar is inside 09:15-15:30 IST, era-aware."""
    if trade_date_str < ERA_BOUNDARY:
        clock = bar_ts.replace(tzinfo=None).time()  # Rule 16 (legacy)
    else:
        clock = bar_ts.astimezone(IST).time()       # Post-04-07 (true UTC)
    return time(9, 15) <= clock <= time(15, 30)
```

**Simpler alternative** — use the `trade_date` column for date filters and `bar_ts` only for ordering. Eliminates the era-awareness need entirely. Used in `diagnostic_bar_coverage_audit_v3.py`:

```python
# Filter on trade_date (string) instead of bar_ts time:
rows = sb.table("hist_spot_bars_5m") \
    .eq("symbol", symbol) \
    .gte("trade_date", str(start_date)) \
    .lte("trade_date", str(end_date)) \
    .order("bar_ts") \
    .range(0, 999) \
    .execute().data
```

**Affected scripts identified Session 15** (verbatim Rule 16 → era-aware fix needed):
- `adr003_phase1_zone_respect_rate.py` v1/v2 (verdict INVALID — Phase 1 v3 will use era-aware)
- `experiment_44_inverted_hammer_cascade.py` (verdict survives caveat re-evaluation; v2 cleaner)

**Bug B9 (non-rule, anti-pattern):** `hist_pattern_signals.ret_60m` is uniformly 0 across all rows. Either the writer never populates it, or `hist_market_state.ret_60m` source is empty. Do not use `ret_60m` as outcome metric until TD-054 closed. Use `ret_30m` (TD-039) or compute from `hist_spot_bars_5m` directly.

**Bug B10 (non-rule, anti-pattern):** `hist_pattern_signals.ret_eod` column does not exist. EOD-outcome experiments must JOIN to `hist_spot_bars_5m` and compute the session-end forward return per row. TD-055 filed for schema migration.

**Operational findings (2026-05-02):**

- **Five-step audit pattern** for "type-X missing across detector" defects. When Session 15 found `hist_pattern_signals.BEAR_FVG=0` over 13 months, the discovery sequence was: (S1) distinct pattern_type counts; (S2) schema + direction columns; (S3) sibling table check; (S4) market-structure sanity (bear-day count last 30d); (S5) **manual canonical 3-bar shape scan in `hist_spot_bars_5m`** — the load-bearing step. Result: 1,129 canonical BEAR_FVG shapes existed in raw price data, 0 in signals → bug must be in detector or signal builder. Pattern preserved at `diagnostic_bear_fvg_audit.py`. Reuse the structure for similar defects (e.g. SWEEP_REVERSAL count audit, missing-timeframe-pattern audit).

- **Patched-copy deploy pattern** is the canonical safe-deploy for production scripts. Steps: (1) produce `<script>_PATCHED.py`; (2) dry-run; (3) live run; (4) full verification; (5) ONLY THEN rename `<script>.py` → `<script>_PRE_<session>.py` and `<script>_PATCHED.py` → `<script>.py`. Allows discrete rollback (one rename) without `.bak` file proliferation. Session 15 used this for `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` — both renames preserved as `_PRE_S15.py`.

- **Verify experiment results against market reality before believing them.** Operator's chart-based challenge to "0 BEAR_FVG over 13 months" was the only signal that surfaced the 13-month silent bug (TD-048). Multiple sessions had run experiments against the broken signal table without anyone noticing. Discoverable by inspection but not by automated test. Going forward: when an experiment produces a result that contradicts visible market structure, treat the data path as suspect before drawing conclusions about the hypothesis.

- **Code review BEFORE patching when fixing a known-incomplete detector.** Session 15's six-bug review (S1.a/S1.b/S15-1H + S2.a/S2.b/S3.a/S3.b) emerged from one review pass. Spreading discovery across multiple sessions would have been more expensive and missed the explicit decision-rule (fix S1, defer S2/S3 with explicit TD filing).

- **Direction-symmetry verification before patching the wrong layer.** Session 15 checked that `build_hist_pattern_signals_5m.py` was direction-symmetric BEFORE patching the zone builders. Confirmed via 5-step audit S5 (canonical shape scan with no signal-table involvement). Avoided the trap of patching the signal builder symptomatically while leaving the zone-builder root cause intact.

---

## Session 16 engineering discoveries (2026-05-03) — codified as Rule 21

**Rule 21 — Always pipe long-running scripts through Tee-Object.** Any PowerShell invocation of an experiment, simulation, or diagnostic that runs longer than ~5 minutes MUST be invoked with `... 2>&1 | Tee-Object -FilePath "<name>_$(Get-Date -Format yyyyMMdd_HHmm).log"`. The first NIFTY full-year run of `experiment_15_pure_ict_compounding.py` was lost mid-session because it was run without Tee-Object, requiring a re-run that cost ~25 minutes of wall time. PowerShell's terminal scrollback is not a reliable archive. The .log file is.

```powershell
# Canonical invocation pattern:
$env:PYTHONIOENCODING = "utf-8"
python <script>.py 2>&1 | Tee-Object -FilePath "<script>_$(Get-Date -Format yyyyMMdd_HHmm).log"
```

The `$env:PYTHONIOENCODING = "utf-8"` prefix is also required whenever the script outputs box-drawing characters (Section headers in analyzers, table separators) — Windows console default encoding is cp1252 which crashes on `─` and `═`.

**Bug B11 (non-rule, anti-pattern) — Wrong-cohort comparison.** Session 16 mid-session had a near-miss where Items 1-6's "ungated coin-flip on `hist_pattern_signals`" results were almost framed as "Exp 15 framework headlines collapse" — when in fact `hist_pattern_signals` is the 5m-batch detector path and Exp 15's actual edge lives on the 1m live-detector path running through `experiment_15_pure_ict_compounding.py`. Operator pushed back ("are we looking at exp code or just compendium results?"), which triggered the source-archaeology phase that surfaced TD-057 and produced the live-cohort replication. **Going forward: before drawing conclusions about whether an experiment's claims replicate, read the experiment's source code and identify the cohort + outcome metric. Two experiments with similar names but different cohorts/metrics are not comparable.** Captured in CLAUDE.md anti-patterns table.

**Bug B12 (non-rule, anti-pattern) — Silent code drift between publication and audit.** April-13 commit `c78b6ea` modified BOTH `experiment_15_pure_ict_compounding.py` AND `detect_ict_patterns.py` together, including silent MTF tier relabeling: pre-Apr-13 vocabulary (HIGH=W, MEDIUM=D, LOW=none) became post-Apr-13 (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none). The Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements. **Always run `git log --follow` on the experiment source file before claiming results are inflated/wrong/correct — silent code drift between publication and audit is a real failure mode.** TD-057 captures the broader provenance gap.

**Operational findings (2026-05-03):**

- **Schema-first rule for queries.** Always check `merdian_reference.json` `tables.<tablename>` schema before writing Supabase queries. Session 16 burned 2 iterations on column-name guessing (`hist_ict_htf_zones.tier` does not exist; correct column is `pattern_type`). Cost was minor but compounds across long sessions. Schema lives in JSON for a reason — use it.

- **Confidence intervals before declaring victory.** Session 16's pooled +193% return looked clean until Wilson 95% CIs and concentration check were applied. Result: BULL_FVG CI [42.5, 58.1] spans 50% (statistical coin flip despite N=155); top 7 sessions = 80% of P&L (event-dependent strategy, not steady-yield). The aggregate number alone would have led to over-confident production assumptions. **Always compute CIs on per-pattern WR and a session-concentration check (cumulative P&L share) before drafting Compendium verdicts.** `analyze_exp15_trades.py` Sections 9-18 codify this pattern; reuse for future research.

- **Trade-list CSV dump pattern is the canonical research artifact.** `experiment_15_with_csv_dump.py` is verbatim methodology of `experiment_15_pure_ict_compounding.py` plus a dataclass→CSV tail. The CSV is durable, version-controllable (gitignored under `*.csv` but persistent on disk), and reusable across diagnostic analyzers. Sessions 9-18 of `analyze_exp15_trades.py` ran in <30 seconds against the CSV after a 30-min compute. Future research should follow this pattern: heavy compute → CSV dump → fast diagnostic analyzer. Avoids re-running the simulation each time a new question is asked.

- **Live-detector replay pattern beats batch-table research.** Session 16 demonstrated that running the live `ICTDetector` over `hist_spot_bars_1m` directly (Exp 15 methodology) produces cleaner research data than relying on the precomputed `hist_pattern_signals` 5m-batch table. The live-replay path has correct outcomes (locally-computed forward return), correct signal-detection logic (the same code that fires production signals), and no schema drift between research and production. ENH-87 proposes formalizing this as the canonical research workflow going forward.

- **Read the script before drawing conclusions about what it measures.** Session 16's wrong-cohort overreach (Bug B11) happened because conclusions were drawn from result aggregates without first reading `experiment_15_pure_ict_compounding.py` source to confirm what cohort and outcome metric were being measured. The script reads `hist_spot_bars_1m`, runs live `ICTDetector`, and computes T+30m option-side P&L from `hist_option_bars_1m` — a fundamentally different measurement than `hist_pattern_signals.ret_30m` spot-side. Twenty minutes spent reading the script would have prevented an hour spent drafting wrong conclusions.

---

## Session 17 engineering discoveries (2026-05-03) — codified as Rule 22 + B13/B14

**Rule 22 — Direction-asymmetric defects in detector pairs.** When a direction-asymmetric bug is found in one component (e.g. zone builder missing BEAR_FVG branch), AUDIT the parallel detector component for the same defect — same author, same era, same blind spot likely applies. Session 15 fixed `build_ict_htf_zones.py` BEAR_FVG zone construction. Session 17 found the EXACT mirror defect in `detect_ict_patterns.py` BEAR_FVG signal emission — both untouched since Apr-13 commit `c78b6ea`. The Session 15 fix was correct but incomplete because the parallel live-detector path was never audited at the same time. Going forward, when fixing a direction-asymmetric defect, the deliverables must include (a) the fix itself, (b) explicit search of any parallel detector/builder/consumer, (c) test data demonstrating both paths now produce symmetric output. TD-058 closure confirms this rule with end-to-end validation (BEAR_FVG signal count 0 → 138).

**Bug B13 (non-rule, anti-pattern) — Self-patching loop.** Session 17 entered a state where each Pine readability fix introduced a new compile error (CE10149 → CE10235 → would have continued). After 3 patch iterations on the same feature, recommendation should be: stop and revert to the last-working version, not keep patching. Pine v6's strict typing rules surface multiple errors per attempt because the compiler bails on the first error, hiding subsequent ones. Codified as: **after 2 hotfix rounds on the same feature, default to revert + re-attempt with full-spec design rather than incremental patching**. Hotfix rounds reset on a verified working build; any new feature attempt resets the counter.

**Bug B14 (non-rule, anti-pattern) — Visible-console pollution.** Operator productivity is materially degraded by Task Scheduler tasks spawning visible Python console windows during pre-market and intraday hours. Each window flash interrupts chart prep, leads to mistypes during signal entry. Session Apr-13 fixed this for `run_option_snapshot_intraday_runner.py` subprocess calls but did not propagate the fix to top-level Task Scheduler entry points. Three years of accumulated tasks (13 currently) all spawn visible windows. Codified as: **every new Task Scheduler task MUST use `pythonw.exe` not `python.exe`, and existing tasks need migration**. Filed as TD-061 with proper-fix sketch.

**Operational findings (2026-05-03):**

- **The check_from filter pattern is a structural anti-pattern.** `detect_ict_patterns.py` had a `check_from = max(0, len(bars) - 10)` filter intended for "only check recently-formed patterns in sub-cycle invocations." The intent was correct (avoid re-detecting old patterns) but the implementation was wrong (caller has no control over what "recent" means; runner passes full session every cycle, defeating the optimization and creating a visibility gap instead). The fix removed the filter entirely and pushed the responsibility to the caller via input bar slicing. Codified as: **shared library functions should not encode caller-specific assumptions about input shape; either expose the assumption as a parameter or push the responsibility to the caller via well-formed input**. ENH-90 candidate finding (BEAR_FVG anti-cluster gate, direction-OPPOSITE to BULL_FVG) is a similar warning — symmetric assumptions in detector logic don't always survive measurement.

- **Smoke tests must simulate caller cadence, not single invocations.** Session 17 first F4 patch alone (`bars=bars[-30:]` runner change without the detector check_from removal) achieved only 74% pattern coverage in single-invocation smoke. The full-day cycle simulator (`diag_td060_full_day_smoke.py`) revealed the cycle-stride/eligibility-window mismatch by walking through 80 5-min cycles end-to-end. Without the cycle simulation, F4 alone would have shipped and failed silently in production. Codified as: **for any patch affecting a periodic detection loop, write a smoke that simulates the loop's cadence; single-invocation tests are insufficient**.

- **Direction-asymmetric findings need N expansion before production deploy.** ENH-90's -16.5pp BEAR_FVG anti-cluster effect (N=22) is statistically suggestive but the Wilson CI [16.4, 52.8] includes 50%. Production deploy at this N risks anti-edge that disappears under more data. Codified as: **before shipping a direction-asymmetric gate, require N≥50 in the smaller arm AND the Wilson 95% CI lower bound to clear the chance threshold by ≥5pp**. ENH-88 (BULL_FVG cluster +12.8pp at N=64) clears this threshold; ENH-90 (BEAR_FVG anti-cluster -16.5pp at N=22) does not.

- **Re-enable Task Scheduler tasks after kill operations.** Operator killed runaway Python processes Saturday May-2; Windows Task Scheduler held all 13 MERDIAN_* tasks `Disabled` until manual re-enable. **Always check `Get-ScheduledTask` state and Enable-ScheduledTask before market open after any kill operation.** Filed as a session-end checklist line below.

- **Holiday-day terminal flashes are correctness, not bugs.** May-1 was Labour Day (NSE holiday); every Mon-Fri-triggered task fires per Windows Task Scheduler (which doesn't know NSE calendar), each task hits `trading_calendar` gate, exits clean — but flashes a console window. The exits are correct (per ENH-66); the noise is a separate problem (TD-061). Codified as: **the calendar gate works; the window is the problem**.

- **Pine v6 has strict block-type unification rules.** `if/else` branches must produce the same value type as their last expression. Session 17's readability rewrite tripped CE10235 because the `if render_as_line` branch ended in `label.new` and the `else` branch ended in `line.new`. Fix: split into two sequential `if` blocks with mutually exclusive conditions. Pine doesn't unify types across separate top-level `if` statements. Codified as: **when writing Pine v6 helpers that branch into different drawing primitives (box/line/label), use sequential ifs not if/else**.

---

## Session 20 engineering discoveries (2026-05-05) — codified as Rule 23 + B15/B16

**Rule 23 — Task Scheduler swap MUST mirror existing action exactly.** When repointing a Windows Scheduled Task to a different script, the new action must replicate the existing action's `Execute` field VERBATIM. Specifically: full path to `pythonw.exe` (not bare `python`), preserved working directory, identical argument shape. Bare `python` relies on PATH resolution which is unreliable in scheduler context — fails silently with `LastTaskResult=2147942402` (ERROR_FILE_NOT_FOUND). `pythonw.exe` (windowless variant) avoids visible console windows; `python.exe` opens a console flicker every minute. Session 20 hit this twice in same session: (a) `MERDIAN_Daily_Audit` was failing because Session 19 created it with bare `python`; fixed via `run_daily_audit.bat` wrapper. (b) `MERDIAN_Spot_1M` swap to v2 initially used bare `python`; caught and re-fixed in same exchange. Codified as: **before swapping a task action, capture the existing action via `Get-ScheduledTask | Select -ExpandProperty Actions | Format-List`; the new action's `Execute` field MUST match character-for-character except for the script name in `Arguments`**.

**Bug B15 (non-rule, anti-pattern) — Diagnostic oscillation without verification.** Session 20 assistant oscillated 4 times on the same diagnostic question ("are live spot bars synthetic O=H=L=C?"), burning ~14 hours of session time. Pattern: concluded YES at 04:00 IST → walked back at 06:30 IST with bad audit query → concluded YES again at 17:00 IST → walked back AGAIN at 18:00 IST after random sample showed real OHLC (forgot those were morning's Kite backfill data alongside flat bars). Locked diagnosis only at 18:30 IST after **triple-verification**: (1) source code reads `O=H=L=C=spot` literally; (2) today's bars sampled directly = 376/376 flat; (3) `script_execution_log` confirms sole writer. Codified as: **before locking ANY diagnosis that contradicts an earlier-in-session conclusion, require three independent confirmations (source code + direct data + audit query). Random sampling is NOT verification when multiple writers may have touched the data.** User explicitly flagged this oscillation as failure mode; assistant acknowledged and filed.

**Bug B16 (non-rule, anti-pattern) — Architecting before reading existing code.** Session 20 assistant proposed multiple wrong architectural directions for live writer fix: Kite WebSocket migration to AWS, building a Dhan WebSocket parallel to Zerodha WS, etc. — all without first reading existing scripts (`ws_feed_zerodha.py`, `ingest_breadth_from_ticks.py`). User had to force this read multiple times ("please read the documentation"). Existing code revealed: (a) Meridian AWS already runs Zerodha WebSocket with own credentials, (b) Zerodha can't do SENSEX BSE F&O, (c) breadth flows through `market_ticks` not direct API. Once read, architecture became obvious. Codified as: **before proposing ANY architectural change touching production scripts, read EVERY currently-running script in the affected pipeline. The existing code is the spec.** This is a stronger version of B11 (wrong-cohort comparison) generalized to architecture.

**Operational findings (2026-05-05):**

- **Dhan REST `/v2/charts/intraday` returns full 1-min OHLC for IDX_I segment indices.** Verified via `web_fetch` of `https://dhanhq.co/docs/v2/historical-data/` plus direct probe. Returns parallel arrays `open[]`, `high[]`, `low[]`, `close[]`, `volume[]`, `timestamp[]`. Same authentication as `/marketfeed/ltp` (access-token + client-id headers). Same instrument identifiers (`securityId`, `exchangeSegment`, `instrument="INDEX"` for IDX_I). 5-year history available at 1/5/15/25/60-min intervals. **This was a knowledge gap in original `capture_spot_1m.py` design** — the LTP endpoint was used because it was familiar; the OHLC endpoint exists and is equally accessible. Codified as: **before designing a vendor integration, fetch the vendor's API documentation index, not just the endpoint we already know about**.

- **Dhan returns "filler" bars for closed-market minute queries.** When querying `/charts/intraday` for a window outside market hours, Dhan returns synthetic bars with O=H=L=C matching last known price and `volume=0`. These must be detected and skipped. Distinguishing: real low-volatility minutes during market hours always have V>0 for IDX_I segment indices. Predicate: `volume == 0 AND open == high == low == close`. Codified in v2.1's `is_filler_bar()` check.

- **Kite returns SENSEX index spot OHLC despite not supporting BSE F&O.** Surprising finding during Session 20 backfill. `kite.historical_data(token=265, ...)` with token 265 (BSE:SENSEX spot) returns full OHLC arrays for both daily and intraday intervals. The "no BSE F&O" restriction (per `ws_feed_zerodha.py` docstring) applies only to options/futures contracts, not the spot index itself. This unblocked single-source NIFTY+SENSEX backfill via Kite. Codified as: **vendor "doesn't support X" claims should be tested against the specific endpoint needed; restrictions in some endpoints may not apply to others**.

- **MALPHA AWS is the Kite gateway, NOT for Meridian code.** User clarified: `ubuntu@13.51.242.119, ~/meridian-alpha` runs `backfill_spot_zerodha.py` and similar utilities tied to Kite credentials, but is NOT a Meridian production environment. Meridian production runs on `ssm-user@ip-172-31-35-90, ~/meridian-engine` ("Meridian AWS"). Tonight's backfill on MALPHA was undesirable but accepted as one-off. Going forward, Meridian code must NOT proliferate to MALPHA. Codified as: **MALPHA AWS = Kite gateway only. Meridian AWS (ssm-user@ip-172-31-35-90) = production. Don't blur these.**

- **NIFTY+SENSEX spot data must come from same source.** User hard constraint reaffirmed: "NIFTY and SENSEX ticks should be recorded. Cant be from different places." Even when Zerodha NIFTY ticks are technically usable for breadth (already streaming live), they cannot be used for spot bars without an equivalent SENSEX source. Single-vendor symmetry trumps "use what's already running." Dhan REST `/charts/intraday` satisfies this — both indices via single API. Codified as settled decision (DO NOT REOPEN).

- **`pythonw.exe` swap in Task Scheduler reduces operator productivity tax.** Even when Holiday Gate (ENH-66) correctly exits clean, visible console window flashes interrupt operator workflow during chart prep. Confirmed Session 17 finding (TD-061). Session 20 reaffirmed: every NEW Task Scheduler entry MUST use `pythonw.exe`. Existing entries should be migrated; tonight v2 swap was opportunity to use `pythonw.exe` (carried forward from v1's pattern). Codified as: **when creating or updating a Task Scheduler action, default to `pythonw.exe` unless console output is operationally required**.

- **Diagnose, then act — never the reverse.** Session 20 assistant tried twice to act before completing diagnosis: proposed v2 design before locking flat-bar root cause; proposed Kite WebSocket migration before reading existing scripts. Both led to wasted exchanges. Codified as: **for any production change, the sequence MUST be (1) read all relevant existing code, (2) lock diagnosis with three confirmations, (3) propose minimal-scope fix, (4) implement. Skipping step 1 or 2 will cost session time and operator trust.**

- **`script_execution_log` writer-attribution audit unblocks confident diagnoses.** A simple SQL query against `script_execution_log` filtered by table-write target uniquely identifies which script writes to which table. Session 20 used: `SELECT script_name, COUNT(*) FROM script_execution_log WHERE actual_writes::text LIKE '%hist_spot_bars_1m%' GROUP BY script_name`. Result: only `capture_spot_1m.py`, 3,897 runs in 30 days. This single query took 5 seconds and would have ended the diagnostic oscillation immediately if used early. Codified as: **for any "what's writing this data?" diagnostic question, run the writer-attribution audit BEFORE attempting to read source code or sample data**.

---

## Session 21 engineering discoveries (2026-05-06) — codified as Rule 24 + operational findings

**Rule 24 — Upsert ON CONFLICT predicate must be verified before relaxing detection filters.** Session 21 closing TD-070 surfaced this hard. The single-bar `prior_move < 0` check was relaxed to an 8-week unbreached-anchor lookback; this widened acceptance and produced multiple zone entries from the same source-bar-date, all colliding on the upsert ON CONFLICT key (symbol, timeframe, pattern_type, source_bar_date, zone_high, zone_low). Postgres 21000 'cannot affect row a second time' error crashed live deploy. Fix required adding `_dedup_zones_by_conflict_key()` helper to collapse zones at the same conflict key keeping earliest valid_from. **Codified as:** when relaxing any filter that affects multiplicity of zone candidates, audit upsert ON CONFLICT keys upstream and add dedup BEFORE the upsert call. Apply this check to any future filter relaxation in detection logic (build_ict_htf_zones, detect_ict_patterns, detect_po3_session_bias).

**Operational findings — Session 21:**

- **Pipeline order matters in idempotent zone management.** The order detect → upsert → recheck → expire is the only correct order: (a) detect produces new candidates; (b) upsert writes ACTIVE for new + leaves existing untouched; (c) recheck flips status based on price action across new + existing; (d) expire flips date-based across all. Reordering any step makes the sequence non-idempotent or produces wrong final state. Session 21 fixed TD-071 by moving expire from BEFORE detect (broken — expires existing zones using last cycle's data) to AFTER recheck. Codified as: **for any pipeline that detects + upserts + recheck-conditions + expires, the only correct order is detect → upsert → recheck → expire. Document this in the script's main() docstring**.

- **Windows Task Scheduler `DisallowStartIfOnBatteries=$true` is silent killer for laptop production systems.** Session 21 traced 22-min cron gap 13:25-13:47 IST to power-source change events. Default Task Scheduler settings disallow battery starts AND stop tasks when going on battery. For laptop-based production system, this drops cycles invisibly. Fix: `DisallowStartIfOnBatteries=$false` AND `StopIfGoingOnBatteries=$false` on every market-hours task. Codified as: **at task creation time, every NEW Task Scheduler task that runs during market hours MUST have battery flags disabled. Audit existing tasks regularly.** This is Rule 23's natural extension (Rule 23 = mirror v1 pattern; this is the explicit battery flag requirement).

- **PowerShell `copy /Y` doesn't work in PS environment.** Session 21 lost ~30 min on TD-070 v2 deploy because `copy /Y file.py file.py` (cmd.exe syntax) returned no error in PowerShell but produced a 0-byte truncated file. The PowerShell-native `Copy-Item -Force` works correctly. Codified as: **NEVER use cmd-style `copy` in PowerShell context. Always `Copy-Item -Force` for file copy in PS.**

- **PowerShell `Add-Content` appends after `exit /b` making lines unreachable.** Session 21 hit this when extending a `.bat` wrapper — `Add-Content` appended new lines AFTER the `exit /b 0` line, making them dead code. Fix: read file content, string-replace to insert before exit line, write back. Codified as: **for `.bat` file edits in PS, use `(Get-Content path) -replace 'exit /b 0', "newcontent`r`nexit /b 0" | Set-Content path`. Never `Add-Content` to a file that has an exit line.**

- **Single-commit-per-session pattern is fragile under cascade.** Session 21 produced 3 patches (TD-070 v1, TD-070 v2, TD-071 + TD-072) but never committed at session end. Session 22 inherited a dirty working tree which compounded with Session 22's own data-recovery dirty state. Codified as: **session_log line and Git commit must happen TOGETHER at session end, no exceptions. If a session ends without commit, the next session's first action is commit-with-S(N-1)-tag-then-start-new-work — never roll forward into new edits with prior session uncommitted.**

---

## Session 22 engineering discoveries (2026-05-07) — codified as B17 + operational findings

**Bug B17 (non-rule, anti-pattern) — Hypothesis exhaustion without controlled test.** Session 22 spent ~6 hours investigating TD-080 Dhan option chain outage by testing and refuting hypotheses (token sync silent failure → battery flag side-effect → AWS competing writer → MALPHA Dhan competition → stale-token daemon → shadow_runner memory cache). Each hypothesis required 20-40 minutes of diagnostic queries. After 6 refutations, root cause still unconfirmed. Codified as: **after 3 refuted hypotheses on the same incident, STOP investigating and design a controlled reproducer test instead.** A reproducer (e.g., "watch tomorrow's 09:15 cron, does it fail or succeed?") can resolve in minutes what 6 hypothesis-refutations failed to resolve. The 7th hypothesis is rarely the right one; the controlled experiment is the only escape.

**Operational findings — Session 22:**

- **Kite returns IST-tagged datetimes for `historical_data` calls — `.replace(tzinfo=ZoneInfo("UTC"))` is the canonical timezone bug pattern, never apply.** TD-084 root cause: `backfill_option_zerodha_OI_FIXED.py` line 184 did `bar["date"].replace(tzinfo=ZoneInfo("UTC")).astimezone(IST)` — Kite already returns IST-tagged, so `.replace(UTC)` shifted timestamps +5h30m, then `is_market_hours()` filter dropped 88% of bars (375 → 46 per strike). Correct pattern: `dt_ist = bar["date"].astimezone(IST) if bar["date"].tzinfo else bar["date"].replace(tzinfo=IST)`. Audit `grep -rn "tzinfo=ZoneInfo.*UTC.*astimezone(IST)"` to find latent instances. Codified as: **NEVER apply `.replace(tzinfo=ZoneInfo("UTC"))` to a Kite `historical_data` row's `date` field. Kite is IST-tagged. The replace is silent data-loss.**

- **Vendor endpoint stability is per-endpoint, not per-vendor.** Session 22 outage: same Dhan token served `/charts/intraday` (capture_spot_1m_v2) at 97% success while `/option-chain` failed 50% of cycles. Endpoints have independent failure modes. Codified as: **when one Dhan/Zerodha/Kite endpoint fails intermittently, do NOT assume the vendor is "down" — test the parallel endpoint. Endpoint-specific failures usually trace to endpoint-specific rate limits, per-endpoint caching, or per-endpoint auth scope.**

- **NIFTY weekly expiry is now Tuesday (NSE 2025+ change), SENSEX stays Thursday (BSE).** Same-day backfill may pull 2 SENSEX expiries (today + next-Thursday) but only 1 NIFTY (next-Tuesday). Session 22 backfill confirmed: NIFTY 22 strikes × 1 expiry (May-12 Tue) = 8,250 bars; SENSEX 44 strikes × 2 expiries (May-7 today + May-14 Thu) = 16,499 bars. Codified as: **NIFTY weekly = Tuesday. SENSEX weekly = Thursday. Don't assume same expiry calendar across symbols.**

- **`find_dotenv()` fails in Python heredoc context — use file approach.** Session 22 hit this twice when running diagnostic Python via `python3 << 'EOF'` heredoc. `find_dotenv()` calls `frame.f_back` which doesn't exist in heredoc execution context, raising AssertionError. Fix: `cat > /tmp/script.py << EOF` then `python3 /tmp/script.py`, with explicit `load_dotenv("/path/.env")` in the script. Codified as: **for any AWS/SSH diagnostic Python that needs env vars, write a file via `cat >` then invoke. Avoid heredoc execution. Always pass explicit path to `load_dotenv()`.**

- **MALPHA AWS Kite gateway is the de-facto recovery path for Dhan outages.** Session 22 validated end-to-end: when Dhan ingest fails, run `backfill_spot_zerodha.py` + `backfill_option_zerodha_OI_FIXED.py` on MALPHA to recover the day's gap. Spot is fully recoverable; option_chain_snapshots full chain is NOT recoverable (Dhan endpoint is real-time only) but per-strike OHLC IS recoverable from Kite. Codified as: **for any Dhan outage of >30 min duration, immediate recovery action = MALPHA Kite backfill of affected day. Document the gap windows; permanent loss is option_chain_snapshots only.**

- **Architecture decisions need ADRs, not session_log notes.** Session 22 architecture conversation Phase α surfaced 4 questions (zone validity model / AWS migration scope / token reliability ordering / today's session shape) that need ADR-grade documentation before implementation. Operator + assistant talked through them but no ADR was drafted. Codified as: **any architectural decision that affects pipeline structure or data model MUST be drafted as `docs/decisions/ADR-NNN-<topic>.md` BEFORE the corresponding code change. ADR is the durable answer to "why did we do it this way?" Tracking it in CURRENT.md or session_log loses the rationale.** Pending ADRs: ADR-005 (zone validity model rewrite per TD-079); ADR-006 (AWS migration scope decision).

---

## Session 25 engineering discoveries (2026-05-10) — codified as B18 + operational findings

**Bug B18 (anti-pattern) — Anti-pattern bugs ship in N silent siblings; fix all when one is found.** Session 25 closed TD-097 (dashboard pre-open URL-encoding bug producing 0% accuracy widget). Root cause was `requests.get(SUPABASE_URL + endpoint, params={...})` double-encoding query strings — Supabase silently returned 200 OK with empty results. The fix took ~30 minutes. The grep for the same anti-pattern took 2 minutes and surfaced **5 more production scripts** with identical defect (filed as TD-099): `build_signal_market_path_audit_v1.py`, `build_signal_outcome_audit_local.py`, `build_signal_regret_log_v1.py`, `build_option_execution_outcomes_v1.py`, `premium_outcome_writer.py`. Each silently under-fetches in production. Codified as: **whenever an anti-pattern bug is fixed in one production code path, immediately `grep -rn` for the same shape across the codebase and treat all matches as the same defect. N silent siblings is the default, not the exception. The grep is the diagnostic; closing only the surfaced site is closure theater.**

**Operational findings — Session 25:**

- **Boundary disposal requires both operator semantic check AND code dependency check.** Session 25 disabled Local `MERDIAN_PreOpen` (09:05 IST) — operator semantic was correct ("9:05 read meaningless" — auction-window prices are not tradeable price discovery), but the task had a real code dependency: `ret_session` computation read from the 09:05 anchor row in `market_spot_snapshots`. Acting on the operator semantic alone would have broken `ret_session`. Investigating the code dependency without the operator semantic would have left orphan auction noise in production. Codified as: **before disabling any Task Scheduler task or AWS cron, run BOTH: (a) operator semantic check — does this writer produce data that's actually used or meaningful? (b) code dependency check — `grep -rn` consumers of the writer's output table for any read paths that target this writer's specific timestamp/anchor. Disposal proceeds only when both checks clear.**

- **Schema-convention semantics deserve formal documentation.** Session 25 closed TD-078 by SQL-verifying TD-070 v2's multi-week BULL_OB lookback. Initial query `WHERE source_bar_date='2026-04-13'` returned empty. Root cause: `ict_htf_zones.source_bar_date` semantics differ by timeframe — for W timeframe it's the **week-start Monday date**, for D it's the bar's calendar date, for 1H it's the hour bucket date. This convention is implicit in `build_ict_htf_zones.py` and not documented elsewhere. Whoever debugs a "missing zone row" claim without this knowledge concludes the row is absent when it's actually present under a different `source_bar_date`. Codified as: **`ict_htf_zones.source_bar_date` is timeframe-aware: W = week-start Monday, D = calendar date, 1H = hour bucket date. When debugging "missing row" claims on this table, check the timeframe-aware convention before concluding the row is absent.** This deserves a System Map §B annotation; filed as follow-up.

- **ADR-008 replay infrastructure is the validation tool for code-dependency migrations; use it before production change, not as a wait-for-Monday substitute.** Session 25 ret_session anchor migration (09:05 → 09:08) was validated via replay over historical days BEFORE the Local 09:05 task was disabled. This is exactly the what-if validation use case ADR-008 was built for. The alternative — disable 09:05 and "see what breaks Monday" — is wait-for-Monday-and-pray, not engineering. Codified as: **for any code change that modifies a data-source anchor, table column, or upstream dependency that production code reads, validate via ADR-008 replay over historical days BEFORE production change. Replay is not just for what-if signal experiments; it is the safety harness for any code-dependency migration whose effects are observable in `*_snapshots` tables.**

- **TD reframing based on cross-script evidence narrows investigation surface materially.** Session 25 reframed TD-080 from "Dhan option chain endpoint reliability" (multi-vendor, multi-endpoint diagnostic) to "AWS Dhan token refresh failure mode" (single-script root-cause: `refresh_dhan_token.py`). The narrowing was earned by cross-script 2026-05-07 evidence — PreOpen 03:38 UTC + option chain 09:30-13:30 IST + 14:45-15:25 IST were all consistent with a single token-refresh failure on AWS, not a Dhan-side service incident. Codified as: **when a TD's investigation surface is broad (multi-component, multi-vendor), re-examine the original incident's cross-script timeline before drafting hypotheses. If the timeline shows correlated failures across components that share a single upstream dependency, narrow the TD to that dependency. The 6-hour hypothesis-refutation marathon Session 22 ran on TD-080 would have completed in 90 minutes had the cross-script narrowing happened first.**

- **Phase α architect-deferral was the right call given low-N — graduated discipline beats uniform discipline at thin data.** Q4 calibration discipline answer: at MERDIAN's Y1 data scale (~250 trading days), strict uniform 67/33 holdout (option a strict) is impractical when half the experiment cohorts have N<60. Status quo single-cohort (option d) leaves overfit risk uncontrolled. Graduated strictness — N≥60 → 67/33 with 10pp tolerance, 30≤N<60 → 75/25 with 15pp, N<30 → "low-N calibration-only" tag — handles data scale honestly without pretending walk-forward is feasible at Y1. Phase 2 cutover at Y2 close commits the discipline forward. Codified as: **methodology decisions at thin data scales require graduated commitment, not uniform commitment. Strict uniform rules either produce unimplementable mandates or get silently waived; both fail. The discipline is to acknowledge the data scale in the rule itself.** ADR-009 will codify; §D.8 of Assumption Register has the working draft.

- **CLAUDE.md update at session close: "settled" bullets are not just for new ADRs; they are also for any answer that future sessions could waste time re-litigating.** Session 25 produced 4 Phase α answers without drafting full ADRs (the ADRs follow in dedicated sessions per Q3 sequencing for ADR-006). The Phase α answers are still durable; if not captured in CLAUDE.md "Things that are settled", a future session could spend hours re-deriving them. Codified as: **at session end, the criterion for adding a "Things that are settled" bullet is not "did we draft an ADR?" — it is "did this session produce an answer that's durable, where re-litigating it would waste future-session time?" If yes, add the bullet, even if the full ADR draft is deferred to a later session. The bullet IS the durable record until the ADR exists.**

## Session 26 engineering discoveries (2026-05-10) — codified as B19 + operational findings

**Bug B19 (anti-pattern) — OI-18 class fix at one site does not close the class; runtime-verify all candidate sites including non-grep-reachable ones.** Session 25 closed TD-097 (dashboard URL-encoding) and immediately filed TD-099 ("same anti-pattern in 5 other production scripts") via `grep -rn "requests.get.*SUPABASE.*params"`. Session 26 proved BOTH legs of TD-099 wrong: (a) the 5 scripts the grep matched were already correct (each emits `requests.get(URL_with_query, params=None)` form, not the broken `requests.get(URL_with_query, params={...})` double-encoding form — TD-099 closed as **filed-in-error**, ~3 hours of unnecessary patching avoided); (b) a real instance of the OI-18 class — unbounded `order_by`+`limit` query that returns oldest rows — existed in `build_momentum_features_local.py::get_session_open_spot()` as a writer-side helper. The grep couldn't find it because the anti-pattern was inside the `supabase_select()` helper call, not a top-level URL construction; the grep rule (`requests.get.*SUPABASE.*params`) was shape-specific to dashboard's request style, not to the bug class. The writer-side instance had been silently NULLing `momentum_snapshots.ret_session` for 3+ trading weeks (2026-04-17 → 2026-05-10, ~5,000 signals), which in turn caused ENH-55 (which gates on `ret_session is not None`) to be a silent no-op for the entire window. Cost of grep-only audit: 24 days of broken gate before the next debugging cycle surfaced it. Codified as: **when an OI-18-class bug ships and is fixed, the closure of the class requires (a) URL-spy or runtime-trace verification of every candidate site, not just grep — the grep is shape-specific and misses helper-buried instances; (b) audit must extend to writer-side helpers downstream of the symptom site, not just request-side construction at the symptom site. Filing rule: a "same anti-pattern in N scripts" claim requires runtime verification before priority assignment. The grep is the trigger to investigate, not the verdict.** TD-097 was fixed; TD-099 was filed-in-error; TD-101 was the real instance the audit missed.

**Operational findings — Session 26:**

- **Production data on a documented period trumps research-cohort hypothesis.** ENH-55 was promoted on Exp 20 evidence (5m-batch `hist_pattern_signals` cohort: opposed 38.3% WR vs aligned 60.9% WR, +22.6pp lift). Once TD-101 fix surfaced 24 days of silent-gate-failure data, retrospective audit on the live signal cohort (action ∈ {BUY_CE, BUY_PE} ∧ `trade_allowed=TRUE`) showed: WOULD_HAVE_BLOCKED bucket 79.5% WR (N=44), WOULD_HAVE_ALIGNED_BONUS bucket 54.3% WR (N=35). Sign of the lift is opposite to Exp 20; magnitude of disagreement clears proxy-WR-noise threshold. ENH-55 was disabled by env flag (default OFF, reversible via `MERDIAN_ENH55_ENABLED=1`). Codified as: **when production data on the cohort that a parameter actually gates contradicts the research-cohort evidence the parameter was promoted on, default to disabling the parameter behind a reversible flag, file the contradiction as an Assumption Register row, and re-validate only with proper outcome metric (option-P&L not spot-direction proxy) on the cohort the parameter actually gates. Calibration discipline first real test (per §D.8.3 prospective parity check) — discipline applied; flag drift criterion fired within 24 days, well inside the 60-day prospective threshold.**

- **Reversible disablement (env flag) > code removal for hypothesis-falsified parameters.** ENH-55's code path stayed in the codebase; only the inner condition was guarded by `if ENH55_ENABLED and ret_session is not None and abs(ret_session) > 0.0005:`. Default `ENH55_ENABLED = os.getenv("MERDIAN_ENH55_ENABLED", "0").strip() == "1"` evaluates to False. Re-enable is a `.env` line addition + restart. The alternative — strip ENH-55 from the codebase — would have made re-validation cost a re-implementation rather than a flag flip. Codified as: **for any production parameter whose hypothesis is falsified by retrospective evidence, the disablement vector is an env flag with default OFF, not code removal. Re-validation cost should be one experiment, not one re-implementation. Code paths that fail empirically are still valuable as documentation of what was tried.**

- **TD-099 lesson — grep-based "same anti-pattern in N other scripts" filings require URL-spy verification before priority assignment.** Session 25 filed TD-099 at S2 HIGH on the strength of a grep match. Session 26 verified each match by intercepting `requests.get` calls and confirmed all 5 scripts emit clean URLs — match was a false positive (the grep regex couldn't distinguish between the broken `URL_with_query + params={...}` double-encoding form and the standard-correct `clean_URL + params={...}` form). 3 hours of patching avoided. Codified as: **before assigning priority to a "same anti-pattern in N scripts" claim, verify with URL-spy or equivalent runtime trace, not grep alone. False-positive grep matches against dashboard-style code patterns are common; the symptom that surfaced the original bug (silent 200-OK with empty results) does not necessarily survive in code-shape grep terms.** Filing pattern going forward: TD-097-style audit-derived TDs require runtime verification of at least one match before filing the rest.

- **TD-101 unbounded query is the OI-18 anti-pattern in writer form.** `supabase_select("market_spot_snapshots", filters={"symbol": symbol}, order_by="ts", desc=False, limit=500)` returns the OLDEST 500 rows in an unbounded table (no date filter), and the inside-loop today-date filter discards all 500. Returns None silently; downstream `compute_return(curr, None)` returns None; stored as NULL. Same shape as TD-097 dashboard query, but inside a helper function rather than at the URL construction site. Fix pattern: bound the query at fetch time (`gte("ts", today_start_utc_iso)` filter, lower limit), keep defense-in-depth date filter inside loop. Threshold preserved at 03:35 UTC per ENH-01 / V18G regression history (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Codified as: **OI-18 (unbounded order_by + limit returning oldest rows) is the canonical Supabase query bug class. Audit shape: any `select()` with `order_by` + `limit` and no time/range filter on the order_by column. Common in helper functions that take a session-scoped time argument but query the full table. Audit broader than just dashboards.**

- **24-day silent-gate-failure window surfaced via writer-bug fix, not via gate-monitoring telemetry.** ENH-55's production telemetry (cautions list, reasons list in `signal_snapshots`) would have shown ENH-55 firing or not firing per signal; since `ret_session` was NULL, the inner condition was False, and the gate produced NO entries — looking telemetrically identical to a gate not firing because ret_session was in the neutral band. There was no signal of the silent failure other than a slow drift in opposed-aligned signal counts that nobody was monitoring. Codified as: **for any gate guarded by a `not None` check on a writer-produced value, ship with a parallel diagnostic that asserts the writer is populating the value at expected cadence (post-cycle: ` SELECT COUNT(*) FILTER (WHERE col IS NULL) / COUNT(*) FROM table_X WHERE date = today` should approach 0). Otherwise a writer regression silently disables the gate. Ship the diagnostic at gate-promotion time, not retrospectively after silent failure surfaces.**

- **Same-session TD close discipline.** TD-101 was filed and closed within Session 26 (NEW S1 → RESOLVED commit `3cb84e2`). Same-session TD lifecycle is acceptable when the diagnostic that surfaces the bug also produces enough evidence for the fix design. Pattern: discovery → SQL diagnostic → bug localization → patch → smoke test → commit, all in one session. The TD entry in `tech_debt.md` records the lifecycle as separate Active and Resolved blocks both stamped Session 26 — the audit trail (NEW + RESOLVED in same session) matters for future sessions reading the register. TD-097 (S25) was the precedent; TD-101 is the second instance.

- **ENH-88 deployment gate satisfied; same-session ship discipline.** ENH-88 (BULL_FVG cluster gate, +12.8pp lift evidence per Session 16 Exp 50b at 90-min lookback N=64) had been BUILT NOT DEPLOYED since Session 17, gated on Mon BULL_OB live data confirmation. Session 26 shipped via `patch_s26_enh88_deploy.py` adding 90-min lookback helper + gate block before `return out, flags` in `build_trade_signal_local.py`. Smoke test PASS (Sunday no data, no errors; ENH88_LOOKBACK_MIN=90 confirmed; both NIFTY+SENSEX False as expected for non-trading day). BEAR-side asymmetry preserved (BEAR_FVG anti-clusters at -16.5pp per ENH-90 — do NOT mirror; BEAR side stays standalone). Codified as: **ENH ship triggers can be data-availability-gated (e.g., "deploy after first cycle confirms data flowing") and that gate can be discharged out-of-band, including on Sunday non-trading days when smoke tests are sufficient. The gate's purpose is to confirm the production data path supports the gate's input, not to wait for a calendar event.**

- **Symmetric ADR-005 zone validity model rewrite — D/W OB/FVG `valid_to=NULL` (price-breach only) + 1H 1-week tactical fallback.** TD-079 fix per Phase α Q1 answer: detection canon-aligned (all four ICT pattern types detected symmetrically), routing data-driven (`assign_tier()` uses empirical edge). 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k revived from EXPIRED → ACTIVE on backfill. Pine 36 → 62 zones (49 HTF + 13 intraday). `expire_old_zones()` filter widened from `["W","D"]` to `["W","D","H"]`. PDH/PDL date-expiry unchanged (those are intraday liquidity targets, not structural levels). Codified as: **architecture-defect TDs whose Phase α answer is in hand can be implemented BEFORE the formal ADR draft, provided (a) the answer is recorded as a settled decision in CLAUDE.md, (b) the implementation is reversible (snapshot original), (c) the ADR draft follows in a dedicated session to capture rationale + alternatives. ADR-005 codification (P2 S27 carry-forward) follows the implementation, not the other way around. Doc Protocol v4 Rule 10 ADR-mandatory-before-code is satisfied because the architectural decision (Phase α Q1) WAS made in S25 and recorded in Decision Index + Assumption Register §D.7; the ADR draft is the writeup of an already-made decision.**

---

---

*CLAUDE.md v1.17 — 2026-05-10 (Session 26 close). Added: B19 (OI-18 class fix at one site does not close the class — runtime-verify all candidate sites including writer-side helpers, not just grep matches; TD-097 → TD-099 grep audit closed nothing real, TD-101 was the real propagation instance the grep couldn't reach because the anti-pattern was buried in a helper); seven Session 26 operational findings (production cohort trumps research cohort when they disagree, env-flag disablement preserves reversibility for hypothesis-falsified parameters, grep-based "N silent siblings" claims require URL-spy verification before priority assignment, OI-18 unbounded query class extends to writer-side helpers, gates guarded on `not None` writer values need parallel writer-cadence diagnostics, same-session TD close acceptable when discovery also designs the fix, ENH ship gates can be data-availability-gated and dischargeable out-of-band, architecture-defect TDs implementable before formal ADR when Phase α answer in hand). Settled decisions added: TD-101 NEW + RESOLVED same-session (S1 — `build_momentum_features_local.py::get_session_open_spot()` unbounded query; bounded with `gte("ts", today_start_utc_iso)` + limit=20; commit `3cb84e2`; 03:35 UTC threshold preserved per ENH-01/V18G regression history); TD-099 RESOLVED filed-in-error (5 scripts grep-matched were standard-correct, ~3 hours of patching avoided; URL-spy verification rule established); TD-079 RESOLVED (ADR-005 zone validity rewrite — D/W OB/FVG `valid_to=NULL` price-breach only + 1H 1-week tactical fallback; 18 SENSEX zones revived; Pine 36 → 62 zones); TD-080 instrumentation deployed (probe-log table `dhan_token_probe_log` + view `v_dhan_token_probe_today` on Supabase; `pull_token_from_supabase.py` extended 50 → 355 lines with atomic .env write + readback verify + post-write Dhan probes + audit logging + asymmetry verdict; root-cause investigation pending Mon 2026-05-12 first probe-log triage); ENH-88 SHIPPED (BULL_FVG cluster gate, 90-min BULL_OB lookback, `MERDIAN_ENH88_ENABLED` runtime sets cleanly; commit `8407169`); ENH-55 DISABLED by env flag (Exp 20 hypothesis falsified by 24-day production cohort N=44 opposed at 79.5% WR vs Exp 20's claim of opposed at 38.3%; opposition block AND alignment +10 bonus both gated; default OFF; reversible via `MERDIAN_ENH55_ENABLED=1`; commit `5b94c78`); §D.9 added to Assumption Register (5 rows D.9.1–D.9.5 + 4 open follow-ups + ADR-009 first-case-study material). v1.16 — 2026-05-10 (Session 25 close). Added: B18 (anti-pattern bugs ship in N silent siblings — fix all when one is found; TD-097 → TD-099 5-script sweep is canonical); six Session 25 operational findings (boundary disposal needs operator semantic + code dependency check; ict_htf_zones.source_bar_date timeframe-aware semantics; ADR-008 replay as validation tool for code-dependency migrations; TD reframing via cross-script evidence narrows investigation surface; methodology decisions at thin data scales require graduated commitment; CLAUDE.md "settled" bullets are for any durable answer not just ADRs). Settled decisions added: Phase α Q1 ANSWERED (zone validity model — pure price-based with intraday 1-week fallback); Phase α Q2 ANSWERED (AWS migration scope — capture/derived split with four-stage decomposition); Phase α Q3 ANSWERED (sequencing — token reliability FIRST, ADR-006 BLOCKED on TD-080); Phase α Q4 ANSWERED (calibration discipline — graduated-strictness holdout, status quo REJECTED); TD-097 RESOLVED + ENH-96 SHIPPED same-session; TD-080 REFRAMED (AWS Dhan token refresh failure mode); TD-078 RESOLVED (TD-070 v2 verified; ict_htf_zones.source_bar_date convention codified); MERDIAN_PreOpen Local 09:05 IST DISABLED (durable; ret_session anchor migrated 09:05 → 09:08 validated via replay); Topology §9 Q1 + Q2 CLOSED + new §9.A boundary disposal section. v1.15 — 2026-05-09 (Session 24 close). Added: ADR-008 settled decision bullet (replay architecture + what-if methodology canonical home; ENH-93 CANDIDATE → CLOSED via ADR-008; 10 new `*_replay` Supabase tables + 11 new files in `C:\GammaEnginePython\replay\`; zero touch on live; boundary-driven orchestrator). v1.14 — 2026-05-07 (Session 22 close). Added: Rule 24 (upsert ON CONFLICT predicate verification before filter relaxation); B17 (hypothesis exhaustion without controlled test, 3-refutation rule); five Session 21 operational findings (pipeline order detect→upsert→recheck→expire idempotency, Task Scheduler battery flags requirement, PowerShell copy /Y fails use Copy-Item -Force, PowerShell Add-Content after exit /b breakage, single-commit-per-session must commit-with-tag-at-end no exceptions); six Session 22 operational findings (Kite IST timezone bug pattern, vendor endpoint per-endpoint stability, NIFTY Tue / SENSEX Thu expiry calendars, find_dotenv heredoc failure use file approach, MALPHA Kite gateway as Dhan outage recovery path, ADR requirement for architectural decisions). Settled decisions added: TD-070/TD-071/TD-072 RESOLVED Session 21; TD-084 RESOLVED same-session Session 22 (Kite IST timezone bug); TD-079 HIGH zone date-expiry architectural defect filed (pending ADR-005); TD-080 HIGH Dhan option chain endpoint intermittent 401s root cause UNCONFIRMED (P0 reproducer test Session 23 09:15 IST cron); TD-081 HIGH no data-freshness guard between primary ingestion and derived layers; TD-082/083 NEW; TD-073/074/075/076/077/078 NEW from Session 21; ENH-93 CANDIDATE filed (replay/simulation harness exact mimic of live runner cycle per V18G § 7.2 6-step pipeline). v1.13 (Session 20 close) Rule 23 + B15/B16 + 7 operational findings. v1.12 (Session 17 close) Rule 22 + B13/B14. v1.11 (Session 16 close) Rule 21 + B11/B12. v1.10 (Session 15 close) Rule 20 + B9/B10. v1.9 (Session 14 close) Rule 18/19. v1.8 (Session 13 close) Rule 17. v1.7 (Session 11 ext). v1.6 Rules 14/15/16. v1.5 compendium-replicates. v1.4 Python path. v1.3 Rule 13. v1.2 Rule 12. v1.1 Rule 11.*
