# MERDIAN Technical Debt Register

**Purpose:** A single living markdown file for *known broken-ish things* that aren't blocking but shouldn't be forgotten. This file fills the gap between:

- **C-N (critical)** in `merdian_reference.json` → must fix before next live session
- **ENH-N (enhancement)** in `Enhancement_Register.md` → forward-looking proposal, may never be built
- **Session-local tasks** in `session_log.md` → don't persist past today
- **Tech debt (this file)** → persistent, known, has a workaround, will be paid down when convenient

If an item doesn't fit those four buckets, it doesn't get tracked.

---

## How to use this file

1. **Add an item** when you discover a real issue mid-session that has a workaround and isn't blocking. Use the template below.
2. **Update an item** when the workaround changes, severity changes, or you learn more about root cause.
3. **Close an item** when fixed — move it to the `# Resolved (audit trail)` section at the bottom with the closing commit hash. Never delete.
4. **Promote** to C-N if it becomes blocking, or to ENH-N if it grows into a real enhancement.

---

## Severity scale

| Sev | Meaning | Response time |
|---|---|---|
| **S1** | Production-impacting workaround in place. Fix this sprint. | Within 5 sessions |
| **S2** | Non-blocking but degrades a real user-facing or research workflow. | Within 15 sessions |
| **S3** | Cosmetic, performance-tolerable, or affects only edge cases. | When convenient |
| **S4** | Anti-pattern flagged for future refactor. No active impact. | Aspirational |

---

## Item template

```markdown
### TD-<NNN> — <one-line title>

| | |
|---|---|
| **Severity** | S1 / S2 / S3 / S4 |
| **Discovered** | YYYY-MM-DD (session/appendix ref) |
| **Component** | <file path or table or system area> |
| **Symptom** | What you observe when this hits |
| **Root cause** | What we believe causes it (or "unknown") |
| **Workaround** | What is currently being done to live with it |
| **Proper fix** | What the real fix looks like |
| **Cost to fix** | <est sessions or hours> |
| **Blocked by** | <ENH-N, TD-N, or "nothing"> |
| **Owner check-in** | <date when last reviewed> |
```

---

## Active debt

> Items below are illustrative seeds based on the project state I've read.
> Audit and adjust before committing — replace with the real current state.

---

### TD-001 — `pull_token_from_supabase.py` deployed but not in `merdian_reference.json` Block 3 inventory until v18D audit

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-04 (Appendix V18D_v2 audit fix M-01) |
| **Component** | `merdian_reference.json` files inventory |
| **Symptom** | File exists in production, listed in Block 9 failure modes, missing from Block 3 inventory |
| **Root cause** | Inventory update lag — file added in production before being added to JSON |
| **Workaround** | Audit caught it; corrected in V18D v2 |
| **Proper fix** | Pre-commit hook that diffs deployed `*.py` files against `merdian_reference.json` files keys |
| **Cost to fix** | 2 sessions |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-19 |

---

### TD-002 — `breadth_regime` NULL before 2025-07-16 in `hist_market_state`

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | Appendix V18F v2 Block 4 |
| **Component** | `public.hist_market_state` |
| **Symptom** | Any signal validation that filters by `breadth_regime` silently drops Apr–Jul 2025 sessions |
| **Root cause** | Breadth indicator backfill started 2025-07-16; earlier rows have NULL |
| **Workaround** | Validation queries explicitly mark coverage as `2025-07-16 onwards` and exclude earlier sessions |
| **Proper fix** | Backfill `breadth_regime` for Apr–Jul 2025 from raw `equity_eod` |
| **Cost to fix** | 1 session (similar to other backfill scripts) |
| **Blocked by** | nothing — can be done any time |
| **Owner check-in** | — |

---

### TD-003 — `experiment_15b` `detect_daily_zones` date type mismatch (now CLOSED — kept here as template example)

| | |
|---|---|
| **Severity** | ~~S2~~ → moved to Resolved |

*See "Resolved" section below for the closing entry. Keeping the template visible here so future tech debt items have an example to follow.*

---

### TD-004 — `BFO_CONTRACT_05062025.csv` permanent ingestion failure (malformed Date column header)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | Appendix V18D v2 (SENSEX F+O corrected ingest) |
| **Component** | SENSEX F+O daily ingestion pipeline |
| **Symptom** | One file fails ingestion every time it's encountered; logs flag it, pipeline continues |
| **Root cause** | Source CSV from exchange has a malformed header for that single date |
| **Workaround** | Skip-list the file in the ingestion runner; rebuild that date's gamma from adjacent days if needed |
| **Proper fix** | Manually clean and re-ingest the one file; update the source-file checksum |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | — |

---

### TD-005 — `option_execution_price_history` table marked DEPRECATED but not yet DROPPED

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | merdian_reference.json (E-06) |
| **Component** | `public.option_execution_price_history` |
| **Symptom** | Table exists in DB, takes up space, no writers, one stale reader pending migration |
| **Root cause** | `build_option_execution_outcomes_v1.py` migration pending |
| **Workaround** | Mark DEPRECATED in JSON, no new writes |
| **Proper fix** | Complete the outcome engine migration (E-06), then `DROP TABLE` |
| **Cost to fix** | 2 sessions |
| **Blocked by** | E-06 migration |
| **Owner check-in** | 2026-04-19 |

---

### TD-006 — `run_market_tape_1m.py` disabled due to DhanError 401 / Windows ACCESS_VIOLATION

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-07 (merdian_reference.json files entry) |
| **Component** | `run_market_tape_1m.py`, `MERDIAN_Market_Tape_1M` Task Scheduler task |
| **Symptom** | DhanError 401 every run, returncode=3221225786 (Windows ACCESS_VIOLATION), 390 extra Dhan calls/day |
| **Root cause** | Unknown — auth path through this runner differs from main runners |
| **Workaround** | Task disabled. Tape data not currently captured at 1m granularity. |
| **Proper fix** | Either rebuild against shared auth helper (preferred) or formally deprecate and remove |
| **Cost to fix** | 2–3 sessions |
| **Blocked by** | Decision: do we still want 1m market tape? If no → close as WONTFIX |
| **Owner check-in** | — |

---

### TD-007 — `is_pre_market` column in `hist_spot_bars_1m` is vestigial

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-22 (OI-18 investigation during Session 5 — see `session_log.md` 2026-04-22 entry) |
| **Component** | `public.hist_spot_bars_1m` column + all producers and consumers (20+ files) |
| **Symptom** | Column is always written `false` by every producer (`capture_spot_1m.py`, `backfill_spot_zerodha.py`, all backfill and MTF builders). Every consumer filters `.eq("is_pre_market", False)` — the filter drops zero rows because no producer ever writes `True`. Dead code path masquerading as a semantic filter. |
| **Root cause** | Column was added with intent to mark pre-open (09:00–09:14 IST) bars so they could be excluded from analytics. Writer-side implementation was never completed; consumers were written defensively with the filter assumption. Nobody noticed because the filter is functionally a no-op. |
| **Workaround** | None needed — column works, just adds no value. Pre-open bars ARE being captured and used in analytics today; the filter is decorative. |
| **Proper fix** | Two mutually exclusive paths:<br>  (a) Make the column honest — writer computes `is_pre_market = (IST time of bar_ts between 09:00:00 and 09:14:59)`. All consumers accept the new filter semantics. Requires one-time backfill to retag historical pre-open rows from `False` to `True`. Multi-file, ~20 consumer files to review.<br>  (b) Drop the column + drop all `.eq("is_pre_market", False)` filters from consumers. Schema-breaking but simpler. ~1 session. |
| **Cost to fix** | 2–3 sessions for (a), 1 session for (b) |
| **Blocked by** | Decision: is the pre-open exclusion semantics actually wanted, or is it a bug-shaped assumption that no one actually depends on? If wanted → (a). If not → (b). |
| **Owner check-in** | 2026-04-22 |

---

### TD-009 — `.bak` file debris in `docs/registers/`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (V19A Block 11.4) |
| **Component** | `docs/registers/` directory |
| **Symptom** | Six intermediate `.bak` files left over from the 2026-04-19/20 register unification work: `MERDIAN_Enhancement_Register_v7.md.bak` (35 KB), `_v7.md.bak_v8_20260419_112002` (29 KB), `_v7.md.pre_enh5954.bak` (40 KB), `_v7.md.pre_enh6364.bak` (41 KB), `_v7.md.pre_enh64_close.bak` (45 KB), `_v7.md.pre_enh65.bak` (45 KB). Total ~235 KB. Also present: 5 `merdian_reference.json.bak_*` files totaling ~415 KB. No operational value post-unification. |
| **Root cause** | Safety-backup pattern during `fix_enh*.py` patch runs created these incidentally. Never cleaned up after the patches landed. `.gitignore` now prevents new `.bak` files being tracked (commit `bca369d`), but existing files on disk remain. |
| **Workaround** | Ignore. Not tracked in git anymore. Disk cost trivial. |
| **Proper fix** | Move to `docs/registers/archive/` for audit trail, or delete outright. Archive is the safer default — disk is cheap, audit trail is valuable. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

---

### TD-010 — PowerShell 5.1 `Get-Content` defaults to cp1252 when reading UTF-8 files

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-22 (verifying `session_log.md` post-prepend; sibling of OI-20 write-path BOM issue but different path — this one is read-side) |
| **Component** | PS 5.1 default decoder in `Get-Content`, `Select-String`, `Import-Csv`, and most PS file-reading cmdlets |
| **Symptom** | UTF-8 multi-byte characters in files (em-dash `—` = `E2 80 94`, middle dot `·` = `C2 B7`, curly quotes, etc.) display as multi-character cp1252 mojibake — e.g. `—` renders as `â€”`, `·` renders as `Â·`. **File bytes on disk are correct**; only the PS display is wrong. Verified by re-reading the same file with `-Encoding UTF8` flag which renders correctly. |
| **Root cause** | PS 5.1 reads bytes then decodes them with cp1252 by default. The `$PROFILE` fix from OI-20 (which set `$OutputEncoding`, `[Console]::OutputEncoding`, `[Console]::InputEncoding` to UTF-8 without BOM) addresses the OUTPUT / stdout / argv-to-git-commit paths. It does NOT control `Get-Content`'s INPUT decoder — that is governed by the cmdlet's internal default which remains cp1252 on PS 5.1. Two orthogonal PS 5.1 defaults; OI-20 fix covered one, TD-010 is the other. |
| **Workaround** | Pass `-Encoding UTF8` explicitly to every `Get-Content`, `Select-String`, `Import-Csv` call when the target file contains non-ASCII. Irritating but correct. |
| **Proper fix** | Extend `$PROFILE` with `$PSDefaultParameterValues['*:Encoding']='utf8'` — sets UTF-8 as the default for every cmdlet that accepts an `-Encoding` parameter. Verified safe: does not affect cmdlets without an `-Encoding` param; explicit `-Encoding` passes still override. Long-term answer is PS 7 but that's a multi-session migration with Task Scheduler retest burden. |
| **Cost to fix** | <1 session for the `$PROFILE` addition. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-22 |

### TD-015 — `run_preflight.py` 4-stage preflight system is undocumented; reinvented as one-off

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (Session 7 close + Friday post-market work, morning preflight) |
| **Component** | `run_preflight.py`, runbook coverage, CLAUDE.md "Common operations" table |
| **Symptom** | A canonical 4-stage preflight (env / auth / db / runner_drystart) exists at `run_preflight.py` but is referenced by no runbook, not in CLAUDE.md's operations table, and not surfaced in `merdian_reference.json` operations index. On 2026-04-24 morning the chat re-invented it as `preflight_20260424.py` (now an untracked file in working tree, gitignored as `preflight_*.py` scratch). Future sessions will re-invent it again unless the canonical path is surfaced. |
| **Root cause** | Documentation gap. `run_preflight.py` predates the runbook layer (Rule 11, 2026-04-22); never retroactively given a runbook entry. Tribal knowledge that didn't survive the Session 6 -> 7 chat boundary. |
| **Workaround** | Operator memory. One-off `preflight_20260424.py` written for today, never run again; not committed. |
| **Proper fix** | (a) Create `docs/runbooks/runbook_run_preflight.md` from `RUNBOOK_TEMPLATE.md` documenting the four stages, expected exit codes, when to run each, and the standard "all-PASS = green to start day" criterion. (b) Add row to CLAUDE.md "Common operations" table. (c) Delete `preflight_20260424.py` from working tree. (d) Confirm `merdian_reference.json` has a `files.run_preflight.py` entry; add if missing. |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-016 — Dhan TOTP scheduled task fails with `Invalid TOTP`; manual run with same seed succeeds

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 08:15 IST scheduled task |
| **Component** | `refresh_dhan_token.py`, `MERDIAN_Refresh_Dhan_Token` Task Scheduler task, Dhan TOTP auth path |
| **Symptom** | 08:15 IST scheduled invocation of `refresh_dhan_token.py` returned `Invalid TOTP`. Manual run of the same script at 09:03 IST, same seed, same host, succeeded on first attempt. Both inside Dhan's accepted TOTP window. No diagnostic context captured at the failing run beyond the error string. |
| **Root cause** | Unknown. Three plausible causes, none yet confirmed: (a) Windows clock drift not surfaced by `w32tm /query /status`; (b) TOTP seed cache mismatch between Task Scheduler service context and interactive PowerShell; (c) Dhan-side rate-limit silently rejecting first call when a stale failed-login is still cached upstream. |
| **Workaround** | Manual `python refresh_dhan_token.py` at session start when the scheduled task fails. AWS picks up the new token via `pull_token_from_supabase.py` after the manual run completes. Token refresh is operator-supervised at session start anyway, so the failure mode is non-blocking — but it costs ~5 minutes per occurrence. |
| **Proper fix** | When the failure recurs, run a 30-minute diagnostic capture: (1) `w32tm /stripchart /computer:time.windows.com` against +/-10s of the 08:15 fire moment, (2) capture exact request/response (envvars, CWD, egress IP, computed TOTP value at the same wall-clock) for scheduled-context vs interactive-context, (3) diff. One of the three suspected causes should fall out. Until reproduction, document the manual-fallback procedure in `runbook_update_dhan_token.md`'s failure-modes section. |
| **Cost to fix** | 1 session diagnosis when it recurs (cannot reproduce on demand). Possibly +1 session for the actual fix once root cause is identified. |
| **Blocked by** | Recurrence — cannot reproduce on demand. Next 08:15 IST `Invalid TOTP` is the trigger. |
| **Owner check-in** | 2026-04-24 |

---

### TD-017 — `build_ict_htf_zones.py --timeframe H` has no scheduled invocation

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-24 (pre-market `--timeframe H` returned 0 zones; investigation confirmed this is structurally correct but the post-market scheduled run is missing) |
| **Component** | `build_ict_htf_zones.py`, Windows Task Scheduler + AWS cron coverage for `--timeframe H` |
| **Symptom** | The 09:00 IST cron runs `--timeframe D` only. `--timeframe H` requires >= 2 completed 1H candles of the current session and is therefore a no-op pre-market — confirmed not a bug (added to CURRENT.md DO_NOT_REOPEN). But there is no post-market scheduled invocation, so 1H HTF zones in `ict_htf_zones` lag behind D zones whenever the operator forgets the manual run. |
| **Root cause** | Original cron deployment included `--timeframe D` only. Post-market H requirement was identified during today's investigation but never converted into a scheduled task. Behaviour of the builder is correct; scheduling coverage is incomplete. |
| **Workaround** | Manual post-market run by operator. Inconsistently performed — 1H zone freshness is therefore best-effort. |
| **Proper fix** | Add Windows Task Scheduler task **and** AWS cron entry at 16:15 IST (15 min after EOD ingest) running `python build_ict_htf_zones.py --timeframe H`. Mirror logging, exit-code capture, and Telegram alert pattern of the existing 09:00 IST D-timeframe task. Update `merdian_reference.json` cron inventory. Verify whether OI-11 maps cleanly to this concern; if so, mark OI-11 as superseded by TD-017 in the historical OI register (register itself stays closed per Rule 9). |
| **Cost to fix** | 1 session (Task Scheduler + AWS cron + JSON inventory + runbook touch in `runbook_*` if appropriate) |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

### TD-018 — `build_ict_htf_zones.py:468` uses deprecated `datetime.utcnow()`

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-24 (DeprecationWarning surfaced during D-timeframe build run) |
| **Component** | `build_ict_htf_zones.py` line 468 (and likely other callsites repo-wide) |
| **Symptom** | `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).` emitted on every D build. No functional impact today; will hard-break when the cpython release that removes `utcnow()` reaches the deployed Python. |
| **Root cause** | Code written against pre-3.12 Python. `datetime.utcnow()` was deprecated in Python 3.12. |
| **Workaround** | Ignore the warning. Builder produces correct zones. |
| **Proper fix** | Replace `datetime.utcnow()` at `build_ict_htf_zones.py:468` with `datetime.now(timezone.utc)` (and add `from datetime import timezone` import). Verify call-site treats the resulting tz-aware datetime correctly — tz-aware vs naive comparison is the typical breakage on this migration. While in there, `grep -rn "utcnow()" *.py` for other callsites and fix in the same patch — there are likely several. |
| **Cost to fix** | <1 session for `build_ict_htf_zones.py:468` alone; ~1 session for codebase-wide migration. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-24 |

---

---

## Anti-patterns to avoid (the "don't add new tech debt" list)

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| Hand-patching files on AWS to fix something fast | Creates Local↔AWS drift, no audit trail | Use BREAK_GLASS protocol; doc in Change Protocol Step 8 |
| `print()` left in production code | Pollutes logs; hides real signals | Pre-commit Step 1.5 catches this |
| Hardcoded Windows paths in files destined for AWS | Breaks AWS run silently | Pre-commit Step 1.5 catches this |
| Patch script (`fix_*.py`) without `ast.parse()` validation | Invalid syntax shipped, found at market open | Standing rule (CLAUDE.md #5) — ast.parse every patch |
| Creating a new `OI-N` ID | Register is closed | Use this file (TD-N), ENH-N, or C-N |
| Pasting full master into session | Burns context window, dilutes focus | Targeted JSON lookup per Session Mgmt Rule 4 |
| Mixing concerns in one session | Accelerates context degradation | Split sessions per Session Mgmt Rule 3 |

---

## Resolved (audit trail)

> Closed items live here forever. Never delete — they are evidence of work done and decisions made.

### TD-003 (closed) — `experiment_15b` `detect_daily_zones` date type mismatch

| | |
|---|---|
| **Closed** | 2026-04-13 (Appendix V18F follow-on session) |
| **Closing commit** | `<hash>` |
| **Fix applied** | `_daily_str = {str(k): v for k, v in daily_ohlcv.items()}` passed to `detect_daily_zones`. LOT_SIZE corrected: NIFTY=75, SENSEX=20. |
| **Lesson** | `date.fromisoformat()` inside `detect_daily_zones` requires string keys; tracking it as TD vs OI made the lifecycle visible. |

---

### TD-008 (closed) — Enhancement Register ENH-72 status drift

| | |
|---|---|
| **Closed** | 2026-04-22 (same session as discovery) |
| **Closing commit** | Session 2026-04-22 batched [OPS] commit (hash TBD at commit time) |
| **Fix applied** | `fix_td008_enh72_register_flip.py` — performed 5 exact string-match replacements in `MERDIAN_Enhancement_Register.md` (lines at ~114, 152, 1892, 1999, 2064), flipping `PROPOSED` → `CLOSED 2026-04-21`. Appended 1,916-byte closure block after the ENH-72 detail section with commit chain `3a22735..f121fca` and per-script live-validation numbers. File size 114,396 → 116,392 bytes. Backup preserved at `.pre_td008.bak`. |
| **Validation** | `Select-String` for `ENH-72.*PROPOSED` returns zero results post-patch. `Select-String` for `ENH-72.*CLOSED` returns 5+ matches (original 5 flipped locations + new matches in the closure block). |
| **Lesson** | Documentation-drift between the JSON authoritative-state layer and the markdown human-readable register is a real class of bug. The `enhancement_register_delta_<date>.md` delta-file pattern used on 2026-04-21 was an anti-pattern — it deferred the real register update indefinitely. **Going forward:** when an ENH closes, update the unified register in the same commit as the JSON and the session_log. No delta files. |

---

### TD-014 (closed) — `ingest_breadth_from_ticks.py` write-contract instrumentation

| | |
|---|---|
| **Closed** | 2026-04-23 (Session 7) |
| **Closing commit** | `1630726` |
| **Fix applied** | Added `_write_exec_log()` helper and instrumentation at all exit paths of `main()`. Writes one row to `script_execution_log` per invocation with `host='local'`, `exit_code`, `exit_reason` from `chk_exit_reason_valid` enum (SUCCESS / SKIPPED_NO_INPUT / DATA_ERROR), `contract_met` flag, `actual_writes` JSONB. `contract_met` is True iff `coverage_pct >= 50%` AND `market_breadth_intraday` write succeeded. Telemetry write wrapped in try/except so failure cannot crash the pipeline (preserves write-path correctness regardless of telemetry state). |
| **Validation** | Tested 2026-04-23 19:09 IST — `SKIPPED_NO_INPUT` path exercised (market closed, no ticks in 10-min window). Row written to `script_execution_log` with `host='local'`, `exit_code=1`, `contract_met=false`, `actual_writes={market_breadth_intraday:0, breadth_intraday_history:1}`. Production run 2026-04-24 first cycle 09:31 IST exercised SUCCESS path with realistic 291/983 BEARISH breadth, `contract_met=true`. |
| **Lesson** | Write-contract instrumentation on every persistence-side script is non-optional. Without `script_execution_log` rows, the 27-day breadth cascade silent failure had no detection signal. The `coverage_pct >= 50% + write_succeeded` rule is what makes the contract enforceable rather than aspirational. ENH-71 (foundation) + ENH-72 (propagation to 9 critical scripts) + this TD-014 (10th, breadth-specific) form the full instrumentation layer. |

---

*MERDIAN tech_debt.md v1 — created concurrent with CLAUDE.md and Documentation Protocol v3. Update inline as items are added/closed; commit with `MERDIAN: [OPS] tech_debt — <action>`.*
