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
| "What did we decide last time about X?" | `docs/decisions/ADR-<N>-<topic>.md` if it exists, else grep **both** `docs/session_notes/session_log.md` (newest 10 entries) **and** `docs/registers/session_log_history.md` (everything older — git-only, not in project knowledge) |
| "How do I run preflight / canary / replay?" | `docs/operational/MERDIAN_Testing_Protocol_v1.md` |
| "What's the commit/branch/deploy rule?" | `docs/operational/MERDIAN_Change_Protocol_v1.md` |
| "When do I write an appendix vs a session note?" | `docs/operational/MERDIAN_Documentation_Protocol_v3.md` |
| "How do I keep a session from degrading?" | `docs/operational/MERDIAN_Session_Management_v1.md` |
| "What were the experiment findings?" | `docs/research/MERDIAN_Experiment_Compendium_v<latest>.md` |

---

## Non-negotiable rules

These are hard rules. Do not propose violations. Do not ask "what if we…".

0. **A check that cannot fail for the reason it names is not a check.** Before writing any verification, state in one sentence what would make it fail, and confirm that a real defect produces exactly that. If the answer is "it wouldn't", you have documentation, not verification. Four clauses, each testable at write time:
   - **`expected_writes` states an exact count or a range, never a floor.** `_compute_contract_met` tests `actual < expected` (`core/execution_log.py:297-303`), so `{"ict_htf_zones": 1}` passes on 163 writes and on 1 — indistinguishable.
   - **A computed verdict must reach the exit code** — unless a named consumer reads it from its persisted form, *and that consumer exists and is scheduled*. `merdian_daily_audit.py:827` hardcodes exit 0 via `ExecutionLog.complete` (`core/execution_log.py:225-229`), deferring (`:825-826`) to a wrapper that is absent from `crontab -l` and has no systemd unit: the FAIL exits 0 and reaches nothing.
   - **An expected value obtained by running the thing is not an assertion.** State the belief, then measure. Adjusting the number until it passes replaces the belief with the observation, and the check then asserts nothing.
   - **A parity claim between two implementations is asserted only by a test that compares them, never by a comment.**

   Instances: F-25, F-81, F-82, coupling-audit rows 7–8, and two of this session's own assertions — detail in `docs/research/ict_structure_audit_2026-09-09.md`.
0a. **A detector must be provable to read only bars at or before its entry bar, and that proof must be an assertion in a test, not a claim in a comment.** S77 established that every favourable ICT number MERDIAN has ever published came from detectors that conditioned on bars later than the bar they entered on. Two independent instances, six weeks apart, in code written by different passes:
   - `experiment_2_options_pnl.py:257-264` fires at bar `i` if `bars[i+5].close` is ≥0.40 % away, then emits bar `j ≤ i` and enters there (`:486`). Every trade begins immediately before a move the selection rule required to have happened. 96 points ÷ the ATM premium at each DTE reproduces the published +41.9 % to within two points — the headline was arithmetic, not behaviour.
   - **F-68**: `valid_from` set to the confirming bar's open rather than its close, across all 19,571 outcome rows.

   Neither was found by review. Both were found when a later session tried to use the number. The controls that would have caught them are cheap and specific:

   1. **Assert the anchor.** A test that constructs bars and asserts every emitted `valid_from` equals its confirming bar's close — not merely that the code parses. S77's smoke test caught nothing until this assertion was added; with it, it exercised 22 real emissions.
   2. **State the entry timestamp expression in the docstring, and check the code against it.** `detect_order_blocks`'s docstring already said *"OB is confirmed at displacement close"* while the code used the open. One sentence asserted both readings, so reading either half confirmed whatever the reader already believed.
   3. **A win rate above ~70 %, or any 100 % cell, is a defect report.** `BEAR_BREAKER` won 0 of 46 (P = 1.4 × 10⁻¹⁴); H displacement reads 41/41. No market process produces those. Compute the binomial tail before believing the cell.
   4. **Win rate tracking lookahead depth is the signature.** Exp 15 backdates entry by 1 bar and reads BULL_FVG at 50.3 %; Exp 10c's unconstrained detector reads the same pattern, same period, at 83.8 %.
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
17. **`market_spot_session_markers` — CORRECTED S88 (2026-10-01).** `open_0915` does not exist (that half stands), but **`open_0915_spot` does, and it is the 09:16 bar's CLOSE, not the 09:15 open** — so `gap_open_pct` is computed off that close. `merdian_ro` also cannot read this table at all (RLS, policy `TO anon`), so a zero from it is the **reader**, not the data. Detail: `merdian_reference.json` → `rule_17_market_spot_session_markers_column_mismatch`; §D.44.5; `capture_s88.md` §3.3. (Added 2026-04-29; corrected Session 88.)
19. **NEVER run `bash -x`, `set -x`, `cat`, `grep`, or any other content-revealing command against `.env` — or against any script that sources it.** `bin/wsfeed_preflight.sh`, `run_ingest.sh`, and every `source .env &&` cron line all load the environment; tracing any of them prints every secret to the transcript. This happened in Session 71 and exposed `DHAN_TOTP_SEED`, `DHAN_PIN`, `SUPABASE_SERVICE_ROLE_KEY`, both Breeze keys, `ZERODHA_API_KEY`, and `TELEGRAM_BOT_TOKEN` — several of which never expire. **Scope every diagnostic to the specific check, never to the environment load.** To test whether a variable is set: `[ -n "$VAR" ] && echo set`. To trace a script that sources `.env`: bracket the sourcing block with `set +x` / `set -x`, or run the inner check alone with the environment already loaded. To compare a secret across hosts: `grep '^KEY=' .env | cut -d= -f2 | tr -d '\r\n' | sha256sum` — compare hashes, never values.
18. **`trading_calendar` is a trust-anchor — validate it against the official NSE source before trusting ANY holiday gate.** Every holiday gate in MERDIAN fail-opens on this table (a wrong/empty calendar silently defeats all of them). The source of truth is `trading_calendar.json` (read by the V18E rule engine `trading_calendar.py`; the table is seeded from it by `seed_trading_calendar.py`). S60 found the JSON held only 2 (one misdated) of the 15 NSE-2026 equity holidays, so the table mismarked every holiday `is_open=true` since ~April and the pipeline ran the full compute chain on Muharram. When adding or trusting a gate, verify the calendar against the official NSE/BSE holiday list first; a gate over a wrong calendar is worse than no gate (it can suppress a real trading day). The canonical gate is `core/trading_calendar_gate.py` (`is_trading_day_today()` / `assert_trading_day_or_exit(log)`) — import it, do not roll a new inline copy. (Rule added 2026-06-26, TD-S60-NEW-2/3.)

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
☐ Re-upload modified docs (CURRENT.md, session_log.md, merdian_reference.json, tech_debt.md, Enhancement Register, this file, operational protocols) to Claude.ai project knowledge — Rule 12 above
```

---

## Anti-patterns Claude should never repeat

These are mistakes that Sessions 1-N have made. Each one cost real time.

- ❌ Running `bash -x` / `set -x` on any script that sources `.env`, or `cat`/`grep`-ing `.env` itself. Prints every secret to the transcript. Session 71 — exposed the TOTP seed, PIN, service-role key, and both Breeze keys, none of which expire. See Rule 19 for the correct forms.
- ❌ Running a verification test on the box before `git push` + `git pull` have completed. The box runs the *old* code and the test passes for the wrong reason. Session 71 did this twice. **Sequence is: Local patch → apply → confirm the file changed → commit → push → pull → test.**
- ❌ Committing after `git add <file>` without first confirming the file is actually modified. `git add` on an unmodified file is a silent no-op and the commit succeeds carrying nothing. Session 71 `28b7920` shipped a patch script whose target was never patched. **Gate the commit on `M  <file>` appearing in `git status --porcelain`.**
- ❌ Piping a diagnostic through `2>&1 | grep <pattern>` when the command might fail. The traceback goes through the grep and is filtered out, leaving silence that is indistinguishable from a clean run producing no matches. Run it ungated first.
- ❌ Inventing an explanation to make data points fit a pattern. Session 71 asserted a non-existent trading holiday to make three preflight failures fit a "first trading day of the week" story; `trading_calendar` shows every weekday 07-27→08-24 `is_open = true`. **n=3 with no mechanism is n=3 with no mechanism.** State the gap.
- ❌ Reading `MERDIAN_Master_V18.docx` etc. at session start. Generated artifacts. Working state lives in this file + CURRENT.md + tech_debt + JSON.
- ❌ Creating a new ID prefix on the fly. Use the existing IDs in `merdian_reference.json` `open_items` or Enhancement Register. New prefix → ADR.
- ❌ Asking "are you sure?" 8 times before doing the obvious thing. Honor preflight + Change Protocol; once those pass, proceed.
- ❌ Asking Navin for the working directory or file path of a known script. Look it up in `merdian_reference.json` `files.<filename>` first. The JSON is authoritative.

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

- ✅ **A verification method can only find what it enumerates.** The S70 ADR-006 audit counted *scheduled tasks* and concluded migration was complete; a manually-invoked production script was invisible to it. The S70 migration was verified by counting tasks disabled rather than checking that every call site the retired `.bat` contained had a new home — and the Pine generator silently lost its schedule. **State what the method cannot see, in the same breath as the verdict.**
- ✅ **The accepted set and the storage key are different decisions.** Widening `capture_cas_close.py`'s bar-slot assertion to `{15:29, 15:34}` was right; letting the accepted slot become the `bar_ts` was not. It would have written a second closing bar into sessions already backfilled at 15:29 and hidden the row from a reconciler that reads one slot. **Tolerance belongs at the boundary; canonicalisation belongs at the write.** Provenance goes in `raw`.
- ✅ **Fail-soft must be visible in the artefact it degrades.** A `57014` timeout on `v_gex_strike_pin_zone` made `generate_pine_overlay.py` emit a Pine file with NIFTY ACCEL, no PIN, and an `// ENH-81 positioning as-of <ts>` stamp taken from the surviving side — asserting complete, current positioning while half was missing. "No pin zone today" is a legitimate reading of that file. **A consumer-facing artefact carries its own defects, or the defect becomes a finding.**
- ✅ **One upstream cause can present as N independent failures.** The 08-25 health check reported 3 FAIL + 1 WARN across `market_ticks`, `market_breadth_intraday`, and `weighted_constituent_breadth_snapshots`. All three are one chain, and the single cause was a preflight rejection at 03:40. **A health check that asserts per-table without modelling the chain multiplies one incident into a triage problem.**
- ✅ **Absence is not a verdict** — a shared gate must resolve a missing `trading_calendar` row through the V18E rule engine (`trading_calendar.get_session_config_for_date`), never default to allow and never hardcode day-of-week. Fail-open is preserved for *genuine errors* only (missing/malformed json, unparseable date, import failure); only a **computed** closure returns False. Two modules may not each author their own contract for what “no row” means — the gate said *no row → allow*, the seeder said *no row → closed*, and every unseeded weekend + NSE holiday read as a trading day for ~6 consumers since S60. A `weekday>=5 ⇒ closed` short-circuit is REJECTED: it would block **Muhurat**, a real weekend session. (ADR-020, S68, `f8e287b`)
- ✅ **NULL is a gap, never a zero.** When a recency guard makes a lens *abstain* (ADR-018 D2), rendering the NULL as 0 states a fact that was never measured — a stale participant board drawn as `0.0` asserts “perfectly balanced OI”. Break the series. (ENH-116 / Marketview v6–v9, S68)
- ✅ **TD-032 dashboard opt_type wrong framing SETTLED** — root cause is NOT 'dashboard hardcodes direction off pattern_type'. Root cause IS `build()` read `opt_type` from `ict_zones.opt_type` (ICT zone direction BEFORE ENH-35 gate overrides). Patched Session 11 extension. Pending 10-cycle live verification to formally close. Do not re-introduce the pattern-hardcoding framing.
- ✅ **TD-038 EXIT AT IST PATCH SHIPPED** (Session 14, 2026-04-30) — `merdian_signal_dashboard.py` `card()` now converts UTC→IST for the static EXIT AT label. Mirrors sig_ts conversion. Live verification pending next TRADE_ALLOWED signal.
- ✅ **`MERDIAN_PreOpen` (Local 09:05 IST) DISABLED** (Session 25, 2026-05-10) — Auction-window writer disposed via PowerShell `Disable-ScheduledTask`, durable across reboots. Operator semantic: "9:05 read meaningless" (call auction prices are not tradeable price discovery). Code dependency check: `ret_session` migrated 09:05 → 09:08 anchor and validated via ADR-008 replay infrastructure (first non-construction use of replay system). AWS sole writer at 09:08. Mon 2026-05-12 verification plan in Topology §9.A. Do not re-enable Local 09:05 task without reverting `ret_session` anchor.
- ✅ **TD-NEW-2 + TD-NEW-3 P0 verification PASS — live cycle** (Session 28, 2026-05-12 09:25 IST) — S28 P0 mandate closed in ~10 minutes after market open. 09:15 IST cycle on Local + AWS confirmed both patches working on live data: `flip_level` dynamic (not stuck), `net_gex` in Crore range (78K–924K Cr per cycle, not trillions of raw rupees). Pre-patch corruption signal absent from `gamma_metrics` rows tagged 2026-05-12 onwards. P0 closure recorded in CURRENT.md. Drift period of ~22h followed P0 closure; surfaced TD-NEW-12 + TD-NEW-4 + TD-NEW-13 (see below). Do not re-verify; the live cycle evidence is the verification.

- ✅ **IMDSv2 attached-SG check mandatory before AWS SG edits — REFUTED operator-console-name memory** (Session 39, 2026-05-27) — D.21.3 REFUTED. AWS networking debug arc lost hours because operator was editing orphan `launch-wizard-2` SG (unattached, residue from earlier instance) while attached SG was `launch-wizard-1`. Browser connectivity to `13.63.27.85:80` failed despite VPC route table + NACL + iptables all clean; root cause was SG edits applied to wrong SG. Resolution: IMDSv2 token query — `TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600") && curl -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/security-groups` returned `launch-wizard-1`. Adding TCP 80 from `0.0.0.0/0` to `launch-wizard-1` produced instant connectivity. Codified: **Before editing any AWS SG, run the IMDSv2 attached-SG query from the running instance; do not rely on AWS Console naming or operator memory.** TD-S39-NEW-4 S4 filed to delete orphan `launch-wizard-2` after audit. Do not edit SGs by name without IMDSv2 verification.

- ✅ **A relation that cannot produce a REAL EMPTY LIST is excluded from a measurement as UNMEASURABLE BY THIS METHOD — by measurement, never by name and never by catalog category (S78, `MERDIAN_Data_Inventory.md` method rule 6).** Probe each source on a window it certainly holds no rows in; one that must scan its whole extent to prove absence times out instead of returning `[]`, and so can never satisfy the rule that every zero cell is a real empty list. Such a relation does not fail once, it fails **once per empty day**. The exclusion does **not** block the write — but the register then says **nothing** about that relation, neither presence nor absence, and must say so. One relation excluded on the S78 run (`v_oi_prev_close_snapshots`, HTTP 500 at ~8.3 s on every scope including an unfiltered day window); the shape recurs at finer scope, where a single 107k-row day of `historical_option_chain_snapshots` also times out. **A protocol amendment recorded in the register that implements it — not an ADR**, in the same shape as the S74 Doc Protocol v4 Rule 7 amendment.

- ✅ **A `sql/` file that carries only the view body is not a rebuild source, and a rebuild from it fails SILENTLY.** Measured S81 across all three S79 GEX views: bodies match the database 3/3, **`COMMENT ON VIEW` present in `sql/` and ABSENT live 3/3**, and **`GRANT SELECT` to anon COMMENTED OUT in `sql/` while PRESENT live 3/3**. So a rebuild yields views correct in body, better documented than live, and **anon-inaccessible — three panels at HTTP 200 with zero rows**, the TD-S37-03 silent-empty shape arriving from the artefact that exists to make rebuilds safe. The root cause was not a missing sentence but a **part-run apply**: the S79 pass ran Section 1 per view and never ran the COMMENT statements. **Rule: `COMMENT` and `GRANT` ship as LIVE statements in the `sql/` file, never as commentary**, and this is **observed, not theorised** — ENH-126 shipped live and anon-unreadable until its skipped `GRANT` was re-run, and only a verification that tests the **anon path** rather than the object's existence could tell the two apart. ADR-025 D2 clause 4 tests that a file exists, **not that it reproduces the object** (TD-S81-NEW-5).
- ✅ **Fixing every instance does not fix the mechanism, and a fix with no watcher has a half-life.** S39 revoked `anon` privileges on thirteen surfaces and left Supabase's DEFAULT PRIVILEGES untouched, so **every object created afterwards came up with ALL again** — `v_max_pain_by_strike` (S40) measured at all seven privileges at S81 is the proof, and D.21.1 read "remediated" for 42 sessions while regressing. The remediation that holds is **`ALTER DEFAULT PRIVILEGES`**; `REVOKE` alone reproduces S39. **And a trust model is only as good as its precondition** — D.21.2's *"the boundary is the RLS policy + GRANT pair"* was **false for ~100 tables with RLS off**, where there is no policy to filter and the GRANT alone is the boundary. Corollary, stated because it is the tempting wrong fix: when a script later fails on an empty service-role key, **supply the key — never restore the grant** (`CASE-2026-09-22-anon-privilege-exposure`, TD-S81-NEW-1/-2/-3).
- ✅ **On a latest-run-scoped view, a count taken at one moment cannot be compared with a count taken at another.** The S81 anon/editor pairing read NIFTY 56 vs 60 and looked like a privilege defect; it was a **new GEX run landing between the two reads** at the ~5-minute writer cadence, confirmed by reading `v_gex_concentration` on the same run and matching 60 / 0.2017 / 23450 exactly. SENSEX paired only because its count happened to be stable across the boundary. **This is a FALSE ALARM where Rule 0 usually warns about the opposite** — a check firing for a reason other than the one it names. **Stable form: fetch `ts` alongside the count and compare counts ONLY when `ts` matches.** Applies to every future pairing on the GEX view family.
- ✅ **An expected value handed to a verifier must be COMPUTED, and computed from the artefact — never recalled.** S81 published an expected `comment_len` of 4637 against a file literal of **5632**; the artefact was correct the whole time and the number came from nowhere, because the run that would have printed it aborted on a wrong assertion before reaching that line and a figure was stated anyway. **Distinct from an assertion misfiring on prose: that is a wrong CHECK, this is a wrong CLAIM with no measurement behind it.** Applied for the rest of that session — the max-pain retrofit's `comment_len 5062` and `comment_md5` were both computed from the file literal before being handed over, and matched. The same discipline killed a second error the same day: a "0 remaining contradictions" claim written into a commit message **before** the check ran, which the check then contradicted.

- ✅ **Derive a gate's threshold from the quantity's scale BEFORE measuring, and write the derivation beside the number.** Four S83 gates failed on this one shape, and each had been set as a round level: a **1 %** net-vs-net comparison where net/gross runs **0.0095–0.341**, so a 2–4 % *gross* error reads as **19 %** and the gate scores the cancellation rather than the model; a **±5 %** window that could not see a full-grid crossing count change from 2 to 1; a **±0.01** r band against a measured dispersion of **0.0203–0.2087**, **~19× wider**, so passing it measured the band and not the quantity; and one **4.0** skew threshold applied across tenors when a fixed 2 %-below-ATM strike sits at a different point on the smile at every tenor. **A mis-specified gate is recorded as mis-specified and NEVER loosened** — all four stand failed, and the builds they gated shipped on separately pre-registered replacements. This is Rule 0's sibling: Rule 0 asks whether a check *can* fail for the reason it names; this asks whether the number it fails at *means* anything.
- ✅ **A role-scoped check runs in ONE execution, and selects `current_user` beside the counts.** The Supabase SQL editor opens a **new session per run**, so a `SET ROLE` issued in one run does not survive into the next — a two-run check (switch role, then count) reports the editor's own role's counts while appearing to test `anon`. Canonical form: `BEGIN; SET LOCAL ROLE anon; SELECT current_user AS role_now, <counts>; COMMIT;` in a single execution, so the acting role is carried by **the same result set** as the numbers. Verified S84 both ways — the single-run form returned `role_now = anon` with 4 / 2 / 868, and the identical query without the switch returned `role_now = postgres` **with the same counts**; that control is what makes it a test rather than three numbers. **`merdian_ro` cannot run it at all** (`permission denied to set role "anon"`), so this check belongs to the editor under the postgres role, and `bin/roq.sh` is not a substitute. (S84, §D.40.1.)
- ✅ **A line citation is stable only into a file that will NOT be edited above the cited line — so newest-first registers are cited by entry ID plus row name, never by line.** The test is not whether the citation crosses files; it is whether anything is inserted **above** the target. `tech_debt.md` files new entries at the **top**, so every line number in it decays on the next filing: filing TD-S84-NEW-1 shifted three citations **inside its own entry** by **+16**, and a fourth — `tech_debt.md:490` — came to resolve to **`TD-S81-NEW-11`'s heading**, a different entry that reads perfectly plausibly, while the real row moved to 580. **A stale citation that lands on other valid content is worse than one that lands on nothing**, because nothing signals the error. `sql/`, ADR and `scratch/` files keep their line numbers — they are appended to, corrected in place, or frozen. **And a dry run cannot catch this class:** the numbers are correct at compose time and wrong only after the write, so the check must run **after** the edit, against the written file. (S84, §D.40.6.)
- ✅ Cross-document section refs carry their owning document (`capture_s74.md` §7.2, not bare §7.2); a bare §N resolves to whichever file the reader is in. TD-S85-NEW-2, §D.41.6. Sibling of §D.40.6.
- ✅ A guardrail must be conditioned on a value the host can read, proven with a control; and a CPU quota bounds rate, not draw — the budget is CPUQuota × timeout. ADR-026 §8.1, §D.41.1–2.

If any of these need to change, that is itself an architectural session — write a new ADR.

---

## Rule 13 — Data contamination registry (added Session 7, 2026-04-23)

MERDIAN tracks known data-integrity incidents in the Supabase table `public.data_contamination_ranges`. Before running ANY research query, experiment analysis, or model training that reads fields listed in `field_scope` from tables listed in `affected_tables`, check whether the query time window overlaps with a registered contamination range.
---

**Rule 21 — Always pipe long-running scripts through Tee-Object.** Any PowerShell invocation of an experiment, simulation, or diagnostic that runs longer than ~5 minutes MUST be invoked with `... 2>&1 | Tee-Object -FilePath "<name>_$(Get-Date -Format yyyyMMdd_HHmm).log"`. The first NIFTY full-year run of `experiment_15_pure_ict_compounding.py` was lost mid-session because it was run without Tee-Object, requiring a re-run that cost ~25 minutes of wall time. PowerShell's terminal scrollback is not a reliable archive. The .log file is.

```powershell
# Canonical invocation pattern:
$env:PYTHONIOENCODING = "utf-8"
python <script>.py 2>&1 | Tee-Object -FilePath "<script>_$(Get-Date -Format yyyyMMdd_HHmm).log"
```

The `$env:PYTHONIOENCODING = "utf-8"` prefix is also required whenever the script outputs box-drawing characters (Section headers in analyzers, table separators) — Windows console default encoding is cp1252 which crashes on `─` and `═`.
**Rule 22 — Direction-asymmetric defects in detector pairs.** When a direction-asymmetric bug is found in one component (e.g. zone builder missing BEAR_FVG branch), AUDIT the parallel detector component for the same defect — same author, same era, same blind spot likely applies. Session 15 fixed `build_ict_htf_zones.py` BEAR_FVG zone construction. Session 17 found the EXACT mirror defect in `detect_ict_patterns.py` BEAR_FVG signal emission — both untouched since Apr-13 commit `c78b6ea`. The Session 15 fix was correct but incomplete because the parallel live-detector path was never audited at the same time. Going forward, when fixing a direction-asymmetric defect, the deliverables must include (a) the fix itself, (b) explicit search of any parallel detector/builder/consumer, (c) test data demonstrating both paths now produce symmetric output. TD-058 closure confirms this rule with end-to-end validation (BEAR_FVG signal count 0 → 138).

<!-- S58 (2026-06-22): +3 settled decisions (ADR-019 port-not-retire; ws_feed host=AWS not MALPHA; ENH-SDM observability-first). -->

<!-- S59 (2026-06-24): +3 settled decisions (equity_intraday_last freshness=ts; breadth prev-close cron on MERDIAN AWS = re-run of C-09; daily ICT PDH/PDL unconditional, weekly filtered). -->

<!-- S60 (2026-06-26): +2 settled decisions (trading_calendar trust-anchor / fixed-at-source; canonical core/trading_calendar_gate.py — import not inline). Rule 18 added (calendar trust-anchor). No ADR (bug-fix + helper-consolidation; Rule 10 bar not met). -->

<!-- S61 (2026-06-27): +3 settled decisions (ENH-07 A no-live-solver reframe; hist bar tables IST-clock-as-UTC zero-shift; ADR-018 D2 floor re-audited — options_flow + basis readers). No ADR (Rule 10 bar not met). -->

<!-- S63 (2026-07-02): +3 settled decisions (ENH-115 P1 participant/cash EOD source live — display-not-gate, feeds ENH-116 Lens 3; historical-backfill calendar-gate corollary to Rule 18 — local weekday filter + API 404; SENSEX compute_flip_level regime-conditional fix). No ADR (bug-fix + ENH build + doc task; Rule 10 bar not met). -->
<!-- S64 (2026-07-04): +5 settled decisions (ENH-116 built/deployed end-to-end; ast.parse-alone-insufficient live case; Marketview public+TLS+Google-auth at marketview.meridianalpha.in; Marketview v5 six-page terminal). No ADR (ENH build/deploy + frontend + infra + carry-in bug-fix; Rule 10 bar not met). -->
<!-- S65 (2026-07-07): +3 settled decisions (Dhan EOD publish-lag is expected not a stall / compute_date_window T-1/220 correct; EOD coverage guard denominator = active-universe ~1,159 not nominal 1,385 + staleness off last trading day w/ ~3-day Dhan-lag tolerance [TD-S65-NEW-1]; OAuth new-client rotation changes id+secret, exposure closes on old-client delete [ENH-117 security fold]). No ADR (OAuth rotation + banner prompt + breadth diagnosis + guard-tune; Rule 10 bar not met). -->
<!-- S66 (2026-07-09): +5 settled decisions (equity_eod<->breadth_indicators_daily DECOUPLED, re-fetching candles != DMA rebuild; DH-901 from one writer while others 200 = token-timing not expiry, read-token-at-use; freshness guards measure per-ticker coverage% not table-max; v_expiry_base_rates live-cohort-only, seed degenerate by construction [M4], re-label dead end; diagnose by running the failing call + verify schema before SQL). No ADR (guard tune + view segregation + breadth diagnosis; Rule 10 bar not met). -->
<!-- S67 (2026-07-10): +4 settled decisions (frozen-table-with-unidentified-writer is a scheduler gap after migration not a mystery writer — Local retired ~Jun 7 per ADR-006, canonical 40 10 AWS cron self-aborting on builder rc=1; coverage-gated builder in a cursored-ingest loop must treat gate-miss as non-fatal not loop-stop; active universe = 1,385 / true ceiling 97.83% / guard denominator = active-count not window-peak; Dhan EOD publish-lag frontier fill is expected not a bug). Also CORRECTED 3 S66 bullets in place (DECOUPLED/unidentified-writer framing was wrong; NEW-1/2/3 marked FIXED). No ADR — all four S67 changes are bug-fixes/hardening (Rule 10 explicitly excludes bug fixes); breadth root-cause is operational. TD-S66-NEW-1/2/3/4 CLOSED, NEW-5 reframed. Commit `f5b9afd`. -->

---

## Where the rest of this file went

This file was split at Session 86 (ADR-028). Nothing was rewritten; content was relocated.

- **Path-scoped rules** — `.claude/rules/*.md`. Each declares `paths:` frontmatter and loads
  only when a matching file is read: `python-writers.md`, `sql-views.md`, `registers.md`,
  `schedulers.md`, `data-access.md`, `research.md`, `pine.md`, `ops-shell.md`.
- **Skills** — `.claude/skills/doc-close/` and `.claude/skills/merdian-runbooks/`.

**Session history is not loaded.** The 23 `Session NN engineering discoveries` blocks and all
version footers live in `docs/registers/CLAUDE_history.md`. Open it when you need one of
these, and cite by session number, never by line:

| If you need… | Session block |
|---|---|
| patch-script encoding / EOL / BOM history | S11 ext, S14 |
| timezone and bar-era handling | S11, S15, S22 |
| Supabase / PostgREST limits and schema drift | S28, S29, S35 |
| cohort, holdout and gate-transfer reasoning | S26, S31-B (carries S30), S33 |
| chain-data tier transition and held-strike PnL | S33, S34, S35 |
| Pine v6 ergonomics | S31-B, S41 |
| read-path scoping, recency floors, CAS timing | S69, S70 |
| fail-open corollary and cross-tier identity | S71, S72 |

*CLAUDE.md v1.60 — 2026-10-02 (Session 88 close). **L9 stage-1 SENSEX arm PASS ×3**; TD-S80-NEW-1 **NOT closed**, NIFTY arm owed **2026-10-06** (measured). **NEGATIVE RESULT:** on the built layers 2026-10-01 was **not distinguishable** from five other SENSEX expiry days before 12:15; 08-27 scored highest on a **rank-5-of-17** range. **11 of 12 parity views carry no history**; L3/L10 refuse at dte 0 (System Map §1963-1976). **TD-S88-NEW-1**; **§D.44 — 10 rows all REFUTED, seven my own**; **ENH-133..138 PROPOSED**; reference **v66**. No new ADR, no production code. Predecessor footers: `docs/registers/CLAUDE_history.md`.*
