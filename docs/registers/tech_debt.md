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

### TD-019 — `hist_spot_bars_5m` pipeline stale since 2026-04-15; blocks forward research validation

| | |
|---|---|
| **Severity** | ~~S2~~ → CLOSED 2026-04-26 (Session 9) |
| **Discovered** | 2026-04-25 (Session 8 — Exp 17 backtest discovered last bar 2026-04-15 09:55) |
| **Component** | `hist_spot_bars_5m`, `hist_spot_bars_1m`, `build_spot_bars_mtf.py`, `capture_spot_1m.py`, `MERDIAN_Spot_1M` Task Scheduler task |
| **Symptom** | `hist_spot_bars_5m` last bar 2026-04-15 15:25 IST for both NIFTY and SENSEX. 10 calendar-day / 7 trading-day gap as of 2026-04-26. The 2026-04-24 NIFTY -393 / SENSEX -1,100 cascade event — the motivating event for Experiment 17 — was missing from the dataset, blocking forward overlay validation of any current research. |
| **Root cause** | (FINAL) `build_spot_bars_mtf.py` was uninstrumented (no `script_execution_log` writes ever) AND was never bound to Task Scheduler. It was a manual on-demand full-history rebuild. Last manual run was on or around 2026-04-15 EOD; nobody ran it again until Session 9. Capture pipeline (`capture_spot_1m.py`, `market_spot_snapshots`, `hist_spot_bars_1m`) was healthy throughout — the gap was purely downstream. The originally-hypothesised candidate causes ((a) Task Scheduler silent fail, (b) aggregator cron broken, (c) capture writer error) were all refuted by Q-A audit (no script in `script_execution_log` ever claimed `hist_spot_bars_5m` as a write target) and Q-B trading-day pattern (clean 150-row days through 04-15 with no irregular bulk-load shape). |
| **Workaround** | None needed post-fix. |
| **Proper fix** | Applied 2026-04-26 in three changes (all delivered same session, override of "no fix in diagnosis session" rule logged): (1) **Instrument** — patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog`. `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` (minimum-1 row semantics catches "ran cleanly but wrote nothing"). Wraps `_run()` in try/except → `exit_with_reason('CRASH', ...)` for unhandled exceptions. Patch scripts: `fix_td019_instrument_build_spot_bars_mtf.py` (+1830 bytes) + `fix_td019_add_sys_import.py` (+11 bytes) — second was a follow-up because original file never imported `sys`. Both ast.parse() validated; backup at `build_spot_bars_mtf.py.pre_td019.bak`. (2) **Backfill** — manual `python build_spot_bars_mtf.py` run wrote 42,324 5m rows + 14,440 15m rows in 116s. Idempotent on `idx_hist_spot_5m_key` / `idx_hist_spot_15m_key` unique indexes. Verified via `script_execution_log`: `exit_reason=SUCCESS, contract_met=true, host=local, git_sha=1de239a`. (3) **Schedule** — registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task. Daily 16:00 IST Mon-Fri. Wrapper `run_spot_mtf_rollup_once.bat` matches existing MERDIAN task pattern (logs to `logs\task_output.log`). Smoke-tested same session: second SUCCESS row in `script_execution_log` 11:37 IST, `LastTaskResult=0`, `NextRunTime=2026-04-27 16:00`. |
| **Cost to fix** | Delivered in 1 session (Session 9, 2026-04-26). |
| **Blocked by** | — closed. |
| **Owner check-in** | CLOSED 2026-04-26 |

---

### TD-020 — LONG_GAMMA gate on 2026-04-24 strongly directional day — diagnosis required before ADR-002 ratification

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-25 (Session 8 — chart review of 2026-04-24 NIFTY -393 / SENSEX -1,100 intraday cascade) |
| **Component** | `build_market_state_snapshot_local.py` (gamma regime classification), gating logic in `build_trade_signal_local.py`, `options_flow_snapshots`, ADR-002 (in-flight) |
| **Symptom** | 2026-04-24 was the strongest directionally-bearish intraday day of the recent month: NIFTY -393 pts H-L (-1.6%), SENSEX -1,100 pts H-L (-1.4%). CURRENT.md "Live trading" block records BULL_FVG TIER2 signals on both indices BLOCKED by LONG_GAMMA gate. LONG_GAMMA classification implies dealer-driven mean reversion expected; the actual price action was strongly trending. Concern: if BEAR setups were also generated and also blocked, the gate left a high-conviction directional opportunity on the table; if BEAR setups were NOT generated despite the bearish breadth context, that is a separate signal-generation question. ADR-002 is currently being drafted around the assumption that the gate "did its job" by blocking trades — that framing is not yet evidence-supported for the strongest test case in recent history. |
| **Root cause** | Unknown. Three sub-hypotheses to discriminate: (a) **Regime classification was correct** but local positioning differed from net (Exp 23 territory — net GEX positive but local-near-spot GEX negative); gate fired correctly given the data it had, but the data was the wrong granularity for the regime question. (b) **Regime classification was wrong** — net GEX was actually negative all day but classifier returned LONG_GAMMA due to bug, stale source_ts, or threshold miscalibration. (c) **Regime classification was correct AND positioning was correct** — gamma did try to hedge, but other forces (breadth-driven momentum, news flow, FII positioning) dominated; gate is doing what it's designed to do, ADR-002 framing stands. |
| **Workaround** | None operationally — Phase 4A live trading continues. ADR-002 drafting paused until diagnosis completes. |
| **Proper fix** | Session 9 diagnosis (sub-hypotheses to discriminate): (1) Pull `options_flow_snapshots` for 2026-04-24 09:15-15:30 IST, both indices, every snapshot. Plot net GEX time series. Confirm regime classification matches the reported LONG_GAMMA state at each cycle. (2) Pull all signals generated 2026-04-24 from signal pipeline output — every direction (bull AND bear), every tier. Confirm whether BEAR signals were generated and what gate dispositioned them. (3) Compute local-vs-net gamma divergence (Exp 23 framework — strikes within ±0.5% of spot vs full chain). If they diverge significantly, this is the smoking gun for sub-hypothesis (a). (4) Check `source_ts` freshness on the gamma JSONB block during 2026-04-24 — Candidate D's concern. If the gamma block was reading stale data, that's sub-hypothesis (b). |
| **Cost to fix** | 1 session for diagnosis (read-only DB queries, no code change). Outcome determines whether Session 10 needs a code fix or ADR-002 can ratify as-is. |
| **Blocked by** | TD-019 partially — the spot bar gap on 2026-04-24 means we have GEX/options data for that day but not 5m spot bars. GEX time-series + tick data should be sufficient for the diagnosis without 5m spot bars. |
| **Owner check-in** | 2026-04-25 |


**Disposition (2026-04-25, Session 8 extended diagnosis):** All three originally-hypothesised sub-causes refuted or moot. Replaced by sub-hypothesis (d), undocumented at filing.

**Evidence:**
- `gamma_metrics` 2026-04-24 09:15-14:25 IST: 100 NIFTY rows + 123 SENSEX rows. `regime='LONG_GAMMA'` on every row. NIFTY `net_gex` range +5.3T to +18.6T. SENSEX `net_gex` range +185B to +2.2T (avg +1.5T). No regime flip, no sign change in net_gex. Classification was numerically correct.
- `signal_snapshots` 2026-04-24 full day: 245 rows (122 NIFTY, 123 SENSEX). `ict_pattern='NONE'` on all 245. `direction_bias='NEUTRAL'` on all 245. `action='DO_NOTHING'` on all 245. **Zero ICT setups generated all day, either direction, either index.**
- `hist_pattern_signals`, `signal_snapshots_shadow`, `signal_state_snapshots` 2026-04-24: zero rows in each. The 245 signal_snapshots rows are the complete 2026-04-24 signal record.

**Sub-hypothesis evaluation:**
- (a) Local-vs-net divergence: MOOT -- gate had no signals to filter, so its granularity is irrelevant for 2026-04-24.
- (b) Regime classification was wrong: REFUTED -- net_gex strongly positive throughout, LONG_GAMMA correctly assigned.
- (c) Regime correct AND gate worked as designed: PARTIALLY SUPPORTED but misleading -- regime call was correct, but the gate did not protect anything because it received no inputs to gate.
- **(d) NEW: ICT pattern detector silent on the strongest directional day of the recent month.** Cannot be diagnosed under TD-020 scope (which assumed gate-behaviour question). Filed as TD-022.

**Reconciliation with Session 7 CURRENT.md statement:** Session 7's CURRENT.md described "BULL_FVG TIER2 signals on both indices BLOCKED by LONG_GAMMA gate" on 2026-04-24. The signal_snapshots data does not support this -- no BULL_FVG signals existed. Either Session 7's CURRENT.md was incorrect (the more likely explanation; possibly described expected behaviour rather than observed), or BULL_FVG signals were generated and rejected upstream of signal_snapshots in a layer not yet identified. This warrants a brief check in Session 9 of any pre-`signal_snapshots` log/queue that might hold rejected setups; if no such layer exists, treat the Session 7 statement as erroneous and update DO_NOT_REOPEN.

**Impact on ADR-002:** Cannot ratify the "gate-protected posture" framing. The protection on 2026-04-24 was not the gate; it was the absence of signals. ADR-002 remains BLOCKED, now blocked on TD-022 (the real causal question), not TD-020 (which is closed).

**Status:** CLOSED -- diagnosed.
**Closed:** 2026-04-25
**Closed_by:** Session 8 extended diagnosis
**Successor:** TD-022 (ICT detector silent on cascade days)

---

### TD-021 -- Two undocumented operational conventions surfaced during Session 8

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-25 (Session 8) |
| **Component** | `.gitignore`, `merdian_pm.py`, `merdian_start.py` |
| **Symptom** | Two small things that bit operations during this session and will bite again unless documented. (a) `.gitignore` line 78 `/experiment_*.py` blocks default-add of new experiment scripts at repo root; convention is to force-add experiments worth keeping reproducible (precedent: `experiment_15.py`, `experiment_15b.py`, `experiment_17_bull_zone_break_cascade.py`). The convention is undocumented anywhere. Cost when missed: one extra commit and a confused user. (b) Adding a new managed process requires two parallel edits -- `merdian_pm.py` PROCESSES dict AND `merdian_start.py` hardcoded list at line 150. ENH-73 deployment hit this exactly: pm_stop killed the process correctly (saw it in PROCESSES) but pm_start didn't launch it (start.py's loop didn't include it). |
| **Root cause** | Both are missing-documentation issues, not bugs. (a) gitignore convention only became apparent when a new experiment was force-added; no comment in `.gitignore` flags it. (b) Schema duplication between `merdian_pm.PROCESSES` and `merdian_start.py`'s hardcoded loop. Originally fine when there were 3 processes; now there are 5 and the redundancy has cost. |
| **Workaround** | Operator memory + this register entry. |
| **Proper fix** | (a) Add a one-line comment above `.gitignore:78` reading something like `# experiment_*.py is default-ignored to keep scratch out of git. Force-add (git add -f) for experiments worth retaining. Precedent: experiment_15.py, experiment_15b.py, experiment_17_bull_zone_break_cascade.py.` (b) Refactor `merdian_start.py` line 150 to iterate over `pm.PROCESSES.keys()` directly, eliminating the second list. ~5 line change. After this, adding a process anywhere requires only one edit. |
| **Cost to fix** | <1 session -- bundle into a future OPS commit. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-25 |

---

### TD-022 -- ICT pattern detector generated zero setups on 2026-04-24 directional cascade day; live signal generation may be silently skipping cascade conditions

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-25 (Session 8 extended TD-020 diagnosis) |
| **Component** | ICT pattern detector (`build_ict_zones.py` / `build_ict_htf_zones.py` upstream; `build_trade_signal_local.py` integration), `signal_snapshots`, `hist_pattern_signals` |
| **Symptom** | 2026-04-24 was the strongest bearish intraday day of the recent month (NIFTY -1.6%, SENSEX -1.4%, NIFTY broke W BULL_FVG 24,074-24,241 by 09:30 IST and cascaded -393 pts intraday; SENSEX similar at 77,636 cascading -1,100 pts). The chart-visible W BULL_FVG zones existed in `ict_htf_zones` (confirmed by 2026-04-25 morning chart screenshots labelled "W BULL_FVG 24,074 PRICE INSIDE [Apr 17]"). Despite this, `signal_snapshots` for 2026-04-24 contains 245 rows, ALL with `ict_pattern='NONE'`, `direction_bias='NEUTRAL'`, `action='DO_NOTHING'`. The live ICT detector did not register the zone interaction or the break. Phase 4A's apparent risk-aversion on this day was not produced by the gate (LONG_GAMMA gate on 2026-04-24 received zero signals to filter -- see TD-020 disposition); it was produced by detector silence. |
| **Root cause** | Unknown. Three plausible classes, requires investigation: (1) **Lookback/window mismatch** -- detector may require zone status that `ict_htf_zones` doesn't yet have; e.g. detector reads `status='ACTIVE'` but the W BULL_FVG was already `BREACHED` by mid-morning, removing it from candidates. (2) **Detector input gap** -- TD-019 stale `hist_spot_bars_5m` may already have been affecting live detection on 2026-04-24 (last bar 2026-04-15 means detector reading from a 9-day-stale price feed by 2026-04-24, possibly outputting NONE because no fresh candles to anchor patterns to). (3) **Pattern type filter** -- detector may be configured to detect only certain ICT patterns (e.g. `BREAK_OF_STRUCTURE`, `LIQUIDITY_SWEEP`) and the cascade pattern of "open inside zone, break below, close below" doesn't map to any registered pattern. |
| **Workaround** | None. Phase 4A is currently relying on detector silence as if it were intentional risk control. Any apparent system success on directional days is unverified -- could be skill, could be silence. |
| **Proper fix** | Session 9 (NEW Candidate A, replacing TD-020 LONG_GAMMA diagnosis): (1) Read `build_trade_signal_local.py` and the ICT detector entry-point. Document what input each pattern type requires from `ict_htf_zones` and `hist_spot_bars_5m`. (2) Replay 2026-04-24 against the detector with current data: pull a single 2026-04-24 bar from Kite REST (one-off, doesn't fix TD-019), feed it to the detector against the ict_htf_zones at that moment in time (`created_at <= 2026-04-24 09:30:00 IST`), see what the detector outputs. (3) If detector outputs NONE for a clear cascade input, that's a pattern-coverage bug -- file ENH. (4) If detector outputs a setup but signal_snapshots shows NONE, that's an integration bug between detector and writer -- file ENH. (5) If detector errors or silently fails on missing 5m bars, that's TD-019's fault -- closure of TD-019 closes this. |
| **Cost to fix** | 1-2 sessions for diagnosis. Fix scope unknown until diagnosis completes. |
| **Blocked by** | Partially TD-019 -- if root cause is TD-019, then TD-019's repair is also TD-022's repair. Diagnosis itself can proceed before TD-019 fix. |
| **Owner check-in** | 2026-04-26 |
| **Blocks** | (was: ADR-002 ratification) -- now superseded by TD-020 reframing |

**Disposition (2026-04-26, Session 9 deep-dive):** TD-022's filed framing
("ICT pattern detector silent on cascade day") was structurally wrong. The
detector ran 404 cycles on 2026-04-24 (per script_execution_log), wrote 3
ict_zones rows for the day (1 NIFTY + 2 SENSEX BULL_FVG TIER2), and produced
output as designed. The "silence" observed in signal_snapshots is downstream
of `enrich_signal_with_ict()` in build_trade_signal_local.py, which filters
zones by direction matching `action`: `direction = +1 if action=="BUY_CE" else -1`.
With `action='DO_NOTHING'` (set upstream by the LONG_GAMMA gate firing on
every cycle), the directional filter matches nothing, returns empty,
ict_pattern is set to NONE. ICT is an innocent passenger; the gate is the
driver.

**Real cause (re-attributed to TD-020 reframing):** LONG_GAMMA gate fired
correctly as designed on every cycle, setting `direction_bias='NEUTRAL'`,
`action='DO_NOTHING'`, `trade_allowed=False`. Session 8 disposition concluded
"gate had no signals to filter; ICT detector silent" — that was reading the
gate's OUTPUT (NEUTRAL/DO_NOTHING) as if it were the gate's INPUT. See TD-020
(reopened/closed-correctly).

**Status:** CLOSED -- duplicate of TD-020 (correctly reframed).
**Closed:** 2026-04-26 (Session 9)
**Closed by:** TD-020 reframing + ENH-37 source read

---

### TD-023 — Uninstrumented data producers (anti-pattern, audit pending)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — surfaced during TD-019 closure) |
| **Component** | All scripts that write to data tables; `script_execution_log` audit coverage |
| **Symptom** | The TD-019 silence was hidden for 7 trading days because `build_spot_bars_mtf.py` never wrote a row to `script_execution_log`. Any producer not wired into ENH-71 contract logging can fail invisibly until a downstream consumer notices. A Q-A audit during TD-019 (searching `script_execution_log` for `actual_writes` / `expected_writes` referencing the stale table) returned zero rows — proving the table had no instrumented producer. By extension, every other public data table needs the same audit; producers that fail the same query are the same kind of trap waiting to spring. |
| **Root cause** | ENH-71 propagation was scoped to a known set of scripts (ENH-72 closed 9, TD-014 added the 10th). Producers outside that explicit set were never required to instrument. `build_spot_bars_mtf.py` was outside the set because it was treated as a "manual rebuild tool" rather than a production writer. Same risk applies to any other manual / occasional / one-off writer that targets a production table. |
| **Workaround** | None active. Operator memory + this register entry. |
| **Proper fix** | Audit pass: (1) `select tablename from pg_tables where schemaname='public'` to list all public data tables. (2) For each, run the Q-A pattern: `WHERE actual_writes::text LIKE '%<table>%' OR expected_writes::text LIKE '%<table>%'` against `script_execution_log`. Tables with zero hits = uninstrumented producer somewhere. (3) `Get-ChildItem -Recurse -Include *.py \| Select-String -Pattern "<table>" -List` to locate the writer(s). (4) Patch each using the `build_spot_bars_mtf.py` template (~10 lines per script). File one sub-TD per uninstrumented producer found; close as patched. |
| **Cost to fix** | 1-2 sessions for the audit. Patching pace depends on producer count. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-024 — 19:01 IST writes to `market_spot_snapshots` (post-close anomaly, two cases)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Q3 freshness query during TD-019 diagnosis) |
| **Component** | `market_spot_snapshots`, `hist_spot_bars_5m`, possibly `capture_spot_1m.py`, possibly ENH-73 heartbeat |
| **Symptom** | (a) 2026-04-24 `market_spot_snapshots` and `hist_spot_bars_1m` show writes at 19:01:02 IST for both NIFTY and SENSEX. `capture_spot_1m.py` is documented as 09:14-15:31 IST per `MERDIAN_Spot_1M` Task Scheduler task. A 19:01 write is ~3.5 hours after schedule end. `script_execution_log` shows `capture_spot_1m.py` last_run 2026-04-24 19:01:01 IST — the script ran, it just ran outside its window. (b) 2026-04-13 (Mon) `hist_spot_bars_5m` shows 152 bars (vs typical 150) with `last_bar` at 16:10 IST. Two extra post-close 5m bars. Different table, different mechanism, but same family (post-close write). |
| **Root cause** | Unknown. Candidate causes: (1) ENH-73 Telegram alerts + 10-min heartbeat deployed Session 8 — fits 04-24 timing but not 04-13 (12 days earlier, before ENH-73). (2) Undocumented EOD job not in Task Scheduler inventory. (3) Manual run not recorded in operator memory. (4) Clock or tz handling issue at the wrapping shell layer. |
| **Workaround** | Not a data-correctness issue; bars and snapshots are well-formed. No active mitigation needed. |
| **Proper fix** | Query `script_execution_log` for `capture_spot_1m.py` rows where `started_at` falls outside the 09:14-15:31 IST window. Identify host/git_sha pattern. If ENH-73 heartbeat: document as expected behaviour, update `merdian_reference.json` cadence string. If different invoker: trace via Task Scheduler history or `.bat` log files for the same date. |
| **Cost to fix** | <1 session for diagnosis. Resolution scope depends on cause. |
| **Blocked by** | nothing — investigation can run any time. Bundle with TD-023 audit if convenient. |
| **Owner check-in** | 2026-04-26 |

---

### TD-025 — `build_spot_bars_mtf.py` re-aggregates full history every run (compute waste)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — observed during TD-019 patch design) |
| **Component** | `build_spot_bars_mtf.py` |
| **Symptom** | Each invocation reloads ALL 1m bars (~210k rows across NIFTY+SENSEX = ~282 trading days × 75 bars × 2 instruments) and re-aggregates the entire history into 5m + 15m, even when only the last day's worth of new data needs producing. At 116s/run × 252 trading days/year × 2 outputs = ~16 hours/year of wasted compute. Idempotent upserts on the unique index mean it's not incorrect, just wasteful. |
| **Root cause** | Original design as a manual on-demand full-history rebuild tool (TD-019 closure context). Was never re-architected after being scheduled as a daily task. |
| **Workaround** | None needed — daily 116s runtime is comfortably within Task Scheduler's 30-min `ExecutionTimeLimit`. |
| **Proper fix** | Parameterise on a date window. Default to "since `MAX(bar_ts)` in `hist_spot_bars_5m`" or "today's `trade_date` only". Full rebuild remains available via `--full` flag for backfills (so the TD-019 backfill recipe is preserved). Reduces typical run from ~116s to <10s. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing. Defer until other priorities clear. |
| **Owner check-in** | 2026-04-26 |

---

### TD-026 — PowerShell scripts must be ASCII-only (encoding pitfall)

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — `register_spot_mtf_rollup_task.ps1` failed parse due to em-dashes) |
| **Component** | All `.ps1` and `.bat` files in repo |
| **Symptom** | Windows PowerShell 5.x defaults to ANSI/Windows-1252 when reading a `.ps1` without a BOM. Non-ASCII characters (em-dashes `—`, box-drawing `─`, smart quotes, etc.) get mangled and produce misleading parser errors that point at lines BEFORE the actual offending byte. Exact failure mode encountered Session 9: em-dash on line 52 → parser reported "Missing closing '}' in statement block" at line 51. Wasted one round trip. |
| **Root cause** | Windows PowerShell 5.x text-handling default, not a script bug. Same family as TD-010 (`Get-Content -Encoding UTF8` requirement). PowerShell 7+ defaults to UTF-8 and would not have hit this. |
| **Workaround** | Re-emit script as pure ASCII: replace `—` with `--`, `─` with `-`, smart quotes with straight quotes, box-drawing with `\|`/`+`/`-`. |
| **Proper fix** | Convention, not a code change: all `.ps1` and `.bat` in this repo are ASCII-only. No em-dashes in comments, no box-drawing in banners. Add a one-line note to CLAUDE.md alongside TD-010 / `Get-Content -Encoding UTF8` so the rule is visible at session start. |
| **Cost to fix** | Convention-only; no fix to apply. Closes when documented in CLAUDE.md. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-027 — `merdian_pipeline_alert_daemon` scope drifted from name

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-26 (Session 9 — Item 4 of TD-022 follow-up parking lot) |
| **Component** | `merdian_pipeline_alert_daemon.py`, ENH-73 + ENH-46-A |
| **Symptom** | The daemon's name and ENH-73 description suggest broad "pipeline alerting." Initial implementation alerted only on infrastructure failures from `script_execution_log`. ENH-46-A extended it to also alert on tradable signals (signal_snapshots). The file now does two distinct jobs but is named for one. |
| **Root cause** | ENH-73 was scoped narrowly during Session 8 deployment (infrastructure visibility); name and description used the broader "pipeline" term that implied wider scope. Documentation drift between intent and implementation, not a bug. ENH-46-A absorbed the gap rather than splitting into a new daemon. |
| **Workaround** | None needed; the daemon does what it does correctly post-ENH-46-A. This TD is about clarity going forward. |
| **Proper fix** | Two paths, mutually exclusive: (a) **Rename narrowly**: rename to `merdian_infra_alert_daemon.py`, keep ENH-73 narrow, treat ENH-46-A as a separate daemon `merdian_signal_alert_daemon.py`. Cleaner separation of concerns, requires file rename + Task Scheduler / pm.PROCESSES + state.json migration. (b) **Embrace the broad name**: keep the file name; document the multi-mode behaviour in the daemon docstring and ENH-73 description; accept a kitchen-sink. Recommendation: (b) for now, revisit if scope balloons further (e.g. third alerting domain added later). |
| **Cost to fix** | <1 session. Not urgent. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-028 — `merdian_pm.py` silently fails on unknown process name

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-26 (Session 9 — ENH-46-A daemon restart) |
| **Component** | `merdian_pm.py`, `start()` and `status()` functions |
| **Symptom** | Calling `python merdian_pm.py stop merdian_pipeline_alert_daemon` (full script filename instead of registry key `pipeline_alert`) returned no output and took no action. Calling `python merdian_pm.py status` also returned no output (whether the registry was empty or the function silently no-op'd is unclear). Net effect: operator believed the daemon had been stopped/restarted when in fact it had not, leading to ~10 minutes of confusion (PID 24968 still running with old code while operator thought new code was loaded). The pm tool's `start()` returns `False, f"Unknown: {name}"` on miss — but only the print path was checked; the actual return path was not surfaced, so the user saw nothing. |
| **Root cause** | Two issues entangled: (1) `start()` and `stop()` print the result tuple via wrappers in some code paths but not others — when called via `python merdian_pm.py <cmd> <name>` from CLI, the bool/msg tuple is returned but not echoed. (2) `status` likely outputs only when there are processes to report, suppressing the "no processes registered" case entirely. Either should fail loudly. |
| **Workaround** | Use the actual registry keys (`pipeline_alert`, `health_monitor`, `signal_dashboard`, `supervisor`, `exit_monitor`) not the script filenames. For start/restart, fall back to direct `Start-Process` PowerShell launch (used in Session 9 to relaunch the alert daemon after `merdian_pm.py start pipeline_alert` produced no output). |
| **Proper fix** | Three changes: (a) print the `(ok, msg)` tuple unconditionally at the top of every CLI handler. (b) emit `[OK] No matching processes` (or similar) from `status` when registry is empty. (c) consider raising on unknown process name (rather than `return False, "Unknown: ..."`) so silent-fail can't happen. <1 session. Bundle with TD-021 fix on the `merdian_start.py` dual-list issue (same file family, related cleanup). |
| **Cost to fix** | <1 session |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-26 |

---

### TD-029 — `hist_spot_bars_1m` and `hist_spot_bars_5m` pre-04-07 era TZ-stamping bug

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-26 (Session 10 mid-experiment, hist_spot_bars_5m TZ diagnostic) |
| **Component** | `hist_spot_bars_1m`, `hist_spot_bars_5m` (rows with `trade_date < 2026-04-07`) |
| **Symptom** | Pre-04-07 rows have IST clock-time stored under UTC tzinfo marker. Approximately 2,820 rows in 5m table affected. 1m table also affected (Q-1M-TZ-DIAGNOSTIC confirmed identical era boundary). |
| **Root cause** | One-off ingest event 2026-04-18 04:43 UTC misclassified the timezone metadata for previously-ingested historical bars. Post-04-07 rows are correctly UTC-stamped (current writer behaviour is correct). |
| **Workaround** | Era-aware CASE on `trade_date` in queries: pre-04-07 → strip-tzinfo-and-reattach-IST; post-04-07 → standard UTC→IST conversion. Used successfully in Exp 29 v2, Exp 31, Exp 32, Exp 15 re-run. Code pattern documented at `experiment_29_1h_threshold_sweep_v2.py:canonicalize_ts_to_ist()`. |
| **Proper fix** | Two options: (a) **Repair**: `UPDATE hist_spot_bars_1m / 5m SET bar_ts = bar_ts - INTERVAL '5 hours 30 minutes' WHERE trade_date < '2026-04-07' AND created_at BETWEEN '2026-04-18 04:43' AND '2026-04-18 04:45';`. Cleaner long-term, but irreversible if scope is wrong. (b) **Document**: write era boundary into `merdian_reference.json`, add CASE-on-trade_date helper to query helpers. Safer. Recommendation: Path A (repair) once scope confirmed via full row-count audit. |
| **Cost to fix** | <1 session if Path A; ~2 sessions if Path B (helper + audit + propagation). |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-030 — `build_ict_htf_zones.py` doesn't re-evaluate breach on existing active zones

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 pre-open ops) |
| **Component** | `build_ict_htf_zones.py` (all timeframes; affects `ict_htf_zones` table integrity) |
| **Symptom** | Two W BULL_FVG zones (NIFTY 24,074-24,241, SENSEX 77,636-78,203) formed 2026-04-20 remained `status='ACTIVE'` after Friday 04-24's selloff broke through them. Zones with `valid_to >= today` AND `status='ACTIVE'` AND price already below `zone_low` (BULL) or above `zone_high` (BEAR) constitute zombie zones that mislead MTF context lookups. |
| **Root cause** | Script applies breach filter at *write time* during detection of new candidate zones — eliminates already-violated candidates before INSERT. Does NOT re-evaluate existing active zones for breach when subsequent price action breaks them. The "Expired old zones before <date>" log line is date-based expiry only, not breach-based invalidation. |
| **Workaround** | Manual SQL UPDATE per session when zones are visibly stale. Zombie-zone detection query: compute current spot vs zone boundaries with directional CASE, mark BULL_BREACHED if spot < zone_low / BEAR_BREACHED if spot > zone_high. Then UPDATE matching IDs to `status='BREACHED', valid_to=CURRENT_DATE`. Used 2026-04-27 pre-open with success (cleared 2 zombie BULL_FVG zones). |
| **Proper fix** | Add a re-evaluation pass at the start of every `build_ict_htf_zones.py` run: for each existing `status='ACTIVE'` zone, compute its current breach status against the most recent bar's close. If breached, UPDATE to BREACHED before detecting new candidates. Incremental cost minimal — one extra SELECT + conditional UPDATE per active zone, runs once per script invocation. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-031 — D BEAR_OB / D BEAR_FVG detection underactive in `build_ict_htf_zones.py`

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 pre-open ops, post-rebuild zone audit) |
| **Component** | `build_ict_htf_zones.py` daily zone detection (D BEAR_OB and D BEAR_FVG specifically) |
| **Symptom** | Q-D-BEAR-COVERAGE returned: D BEAR_OB total ever written = 2 (last 2026-04-11). D BEAR_FVG total ever written = 0. D BULL_OB = 4 lifetime, D BULL_FVG = 0. Despite multiple visibly bearish daily candles in the past two weeks (NIFTY -1.87% week ending 04-24, SENSEX -1.29%, both with strong red 1D bars 04-23/04-24), the script wrote zero new D BEAR structures. |
| **Root cause** | Two candidate hypotheses, not yet confirmed: (a) detector logic for D BEAR_OB is asymmetric — fires only under conditions rarely met (e.g., requires opposing-direction prior bar like the 1H detector, but daily timeframe rarely produces clean 0.40% moves followed by clean reversal candles); (b) breach filter is over-conservative on bearish daily candles (e.g., subsequent intraday spot prints filter the candidate out before INSERT). Neither hypothesis tested. |
| **Workaround** | None. The system operates with a one-sided D-context view — bearish detections cannot get HIGH MTF context from D BEAR zones. Practical impact: BUY_PE candidates can only get HIGH context via PDH proximity (which works as `direction=-1` and is correctly populated), but cannot get D BEAR_OB / D BEAR_FVG confluence. |
| **Proper fix** | Diagnostic session: trace through `detect_daily_zones()` against a known bearish day (e.g., 2026-04-24) and identify why no D BEAR_OB fires. If logic bug, patch + verify. If breach filter is the cause, decide whether to relax filter for D timeframe. |
| **Cost to fix** | ~1 session diagnostic, +1 session for fix if logic bug. |
| **Blocked by** | nothing — investigation can run any time |
| **Owner check-in** | 2026-04-27 |

---

### TD-032 — Dashboard execution panel ignores `direction_bias` / `action`, displays trades inconsistent with DB ground truth

| | |
|---|---|
| **Severity** | S2 (becomes S1 the moment ENH-46-C ships and trade_allowed=true rows appear) |
| **Discovered** | 2026-04-27 (Session 10 live, post-F0 unmasking) |
| **Component** | `merdian_signal_dashboard.py` execution panel rendering pipeline |
| **Symptom** | Multiple observed inconsistencies between dashboard execution panel and `signal_snapshots` ground truth, observed live during 2026-04-27 trading session: (a) At 11:21 IST, NIFTY signal_snapshots row had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050, spot=24068.8`. Dashboard rendered: "Strike 24,100 CE / premium ₹85" — wrong instrument (CE not PE), wrong strike (24,100 not 24,050). (b) At 11:38 IST, dashboard rendered "▲ BUY CE / Strike 24,000 CE" while DB had `direction_bias=BEARISH, action=BUY_PE, atm_strike=24050` — dashboard showed BULLISH instrument while DB was BEARISH. (c) At 12:10 IST, dashboard correctly showed ▼ SELL/BUY PE / Strike 24,050 CE — strike-number now matched but instrument label still CE despite BUY_PE action. Pattern is non-deterministic across cycles. |
| **Root cause (provisional)** | Pattern-driven hardcoding ruled out (dashboard CAN render PE on BULL_FVG patterns at other times). Most likely candidates: (a) race condition between cycle's signal_snapshots write and dashboard's multi-field render, (b) dashboard reads some fields from a different/stale source while reading other fields fresh, (c) in-memory cached state in dashboard process clobbering periodic reads. The DB is consistently correct; the dashboard is the unreliable layer. Pre-F0 the inconsistency was masked because direction_bias was clobbered to NEUTRAL on every LONG_GAMMA cycle (the F0 regression). F0's unclobber unmasked the dashboard rendering bug that has presumably existed for weeks. |
| **Workaround** | Always validate against `signal_snapshots` directly before placing any trade. Dashboard is unreliable for direction/strike/instrument-type rendering. `SELECT direction_bias, action, atm_strike, spot FROM signal_snapshots WHERE symbol=$1 ORDER BY ts DESC LIMIT 1`. |
| **Proper fix** | Source code audit of `merdian_signal_dashboard.py` rendering pipeline. Identify which fields come from where, ensure single-source-of-truth (DB row at render time) for the action/strike/instrument triple. Add a "DB-vs-display consistency check" log line at every render: if dashboard-computed strike/instrument differs from DB row, log warning. |
| **Cost to fix** | 1-2 sessions for diagnosis + fix. |
| **Blocked by** | nothing — investigation can run any time |
| **BLOCKER FOR** | **ENH-46-C ship.** Conditional gate lift cannot promote any signal to live `trade_allowed=true` while operator cannot trust dashboard to show correct trade direction. Without TD-032 fixed, an operator looking at the dashboard could place a CE trade when the system intended PE (or vice-versa), causing a 100%-direction-wrong loss. |
| **Owner check-in** | 2026-04-27 |

---

### TD-033 — Dashboard "SELL / BUY PE" label conflation

| | |
|---|---|
| **Severity** | S3 (cosmetic/confusing but does not change actual order routing) |
| **Discovered** | 2026-04-27 (Session 10 live) |
| **Component** | `merdian_signal_dashboard.py` direction label rendering |
| **Symptom** | Dashboard direction label concatenates direction-bias short-form ("SELL" or "BUY") with action ("BUY_CE" or "BUY_PE"), producing strings like "▼ SELL / BUY PE" or "▲ BUY / BUY CE". Two different concepts (short-form bias label vs concrete trade action) shown as one combined label. No real OMS does this. Confusing for operators, especially under stress. |
| **Root cause** | Dashboard rendering layer building label string from two fields without disambiguating them. Likely an early-stage UI prototype that never got cleaned up. |
| **Workaround** | None needed; just confusing. Read the dashboard label as: short-form before the slash = bias, after slash = trade action. The action is what would be placed. |
| **Proper fix** | Display action (BUY_CE / BUY_PE) prominently as the trade. Display direction_bias separately as a regime tag if at all. Or remove the bias label entirely — `gamma_regime` and `wcb_regime` already render in the gate footer. |
| **Cost to fix** | <1 session. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-034 — `hist_atm_option_bars_5m` severely undersampled on expiry days (dte=0)

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-27 (Session 10 extension, while running Experiment 33) |
| **Component** | `hist_atm_option_bars_5m` ingestion pipeline + the resulting backtest data quality |
| **Symptom** | Only 11 NIFTY expiry days (dte=0) and 22 SENSEX expiry days observed in 2025-04-01 to 2026-03-30 window. Expected ~50 per symbol (one per weekly expiry day, including monthlies). NIFTY coverage rate: 22%. SENSEX coverage rate: 44%. The `hist_atm_option_bars_5m` table has reasonable coverage on non-expiry days (247 distinct dates) but loses most expiry-day rows. |
| **Impact** | Any backtest research on expiry-day behaviour has 22-44% sample coverage. Affects retrospective analysis of: Exp 31 (expiry-day options replay), Exp 33 (inside-bar before expiry), future ENH-46-C shadow analysis on expiry days, any expiry-day-conditional ICT filter design. The Experiment 33 result of "71% next-day continuation" is based on N=14 instead of the ~50 inside-bar-before-expiry candidates a full coverage would have surfaced. |
| **Root cause (hypotheses)** | (a) Ingestion script has an expiry-day exclusion filter (intentional or accidental), (b) ATM-strike-only filter drops rows when ATM changes intraday on volatile expiries (intraday strike migration), (c) ingestion failures on expiry days due to API rate limits or option chain volatility, (d) a `dte > 0` filter somewhere upstream. None confirmed. |
| **Workaround** | Use spot data (`hist_spot_bars_1m`) for expiry-day characterisation where possible — full coverage. Use option_chain_snapshots' 14-day window for fill-in. For backtests requiring multi-month expiry-day option data, accept the smaller sample. |
| **Proper fix** | Trace ingestion logic. Identify why dte=0 rows are missing. If filter bug → patch + backfill. If API/timing issue → add retry logic + flag missing days. Backfill historical expiry days from upstream (Dhan/Zerodha) where API allows. |
| **Cost to fix** | ~2 sessions diagnostic, ~1-2 sessions backfill if data sources available. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-035 — `signal_snapshots.wcb_regime` is NULL on all rows but dashboard shows "BULLISH"

| | |
|---|---|
| **Severity** | S3 (cosmetic on dashboard, may indicate routing inconsistency) |
| **Discovered** | 2026-04-27 (Session 10 live, during DB-vs-dashboard verification) |
| **Component** | `signal_snapshots` table + dashboard wcb_regime rendering |
| **Symptom** | `SELECT wcb_regime FROM signal_snapshots WHERE ts >= CURRENT_DATE LIMIT 10` returns null on every row. Dashboard footer shows "LONG_GAMMA  BULLISH" — the BULLISH portion is wcb_regime per the rendering logic, but DB has NULL. Dashboard must be reading wcb_regime from a different source (likely `wcb_alignment` field or a separate `market_state_snapshots` table) but the contract is undocumented. |
| **Impact** | Two layers may be making decisions on different wcb_regime sources without explicit acknowledgment. ENH-35 gate logic that depends on wcb_regime classification could be operating on `wcb_alignment` (related but not identical) or on `market_state_snapshots.wcb_regime` (separate table) — unverified which. Architecturally suspect. |
| **Workaround** | Treat dashboard's wcb display as informational only, not as the gate's wcb input. For verification, query `market_state_snapshots` directly, or read `signal_snapshots.wcb_alignment`. |
| **Proper fix** | Source-trace `build_trade_signal_local.py` and `merdian_signal_dashboard.py` to find where wcb_regime is read for each. Either: (a) populate `signal_snapshots.wcb_regime` correctly on every cycle (if it should always be set), or (b) drop the column from signal_snapshots if it's redundant with wcb_alignment / market_state_snapshots, or (c) document explicitly that the column is intentionally null and the canonical source is elsewhere. |
| **Cost to fix** | <1 session — diagnostic + decide which path. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-036 — `signal_snapshots.confidence_score` flat-lines for hours

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-27 (Session 10 live, during signal_snapshots monitoring) |
| **Component** | `build_trade_signal_local.py` confidence scoring logic |
| **Symptom** | `confidence_score` for NIFTY = 20.0 across 10 cycles spanning 11:18 to 12:10 IST. SENSEX = 32.0 across same window. Earlier 09:31-09:41 IST window also NIFTY=20, SENSEX=32. Score has not moved for at least 1 hour, possibly the entire session. |
| **Impact** | Confidence score should respond to changing market state. Either: (a) score is computed only at coarser granularity (e.g., once per session) and held constant — design choice but not documented, (b) score is computed per cycle but inputs aren't moving enough to change it — possible but unlikely over 90+ minutes of price action, (c) bug pinning score to a constant. Without diagnostic, hard to know which. |
| **Workaround** | Don't use confidence_score for any trade decision. Treat it as deprecated until validated. |
| **Proper fix** | Source-trace confidence scoring logic. Decide whether it should be dynamic or static. If dynamic → fix update cadence. If static → rename to something like `static_confidence_baseline` to clarify. |
| **Cost to fix** | <1 session diagnostic. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-27 |

---

### TD-037 — Schema column-name inconsistency across timestamp-bearing tables

| | |
|---|---|
| **Severity** | S4 |
| **Discovered** | 2026-04-27 (Session 10 extension, surfaced by repeated SQL errors during Exp 33 development) |
| **Component** | Database schema across multiple tables |
| **Symptom** | Three different timestamp column conventions across canonical tables: `signal_snapshots` uses `ts`, `hist_spot_bars_1m` uses `bar_ts`, `ict_zones` uses both `detected_at_ts` and `session_bar_ts`, `option_chain_snapshots` uses `ts`, `market_spot_snapshots` uses `ts`, `hist_atm_option_bars_5m` uses `bar_ts`, `script_execution_log` uses `started_at` and `finished_at`. Ad-hoc queries error out frequently with "column ts does not exist" or similar; consumes time iterating through column-discovery queries. |
| **Impact** | Friction on ad-hoc queries during live diagnostics. Real cost: during Session 10 extension, 4 query iterations were needed before getting to working SQL for `hist_spot_bars_1m` — adds up to ~10 minutes of iteration time when troubleshooting under market hours. Also makes Claude/AI sessions less efficient because column names can't be predicted from one table to another. |
| **Workaround** | Always run column-discovery query first when querying a new table: `SELECT column_name FROM information_schema.columns WHERE table_name='X'`. Document common patterns in a Session 11+ schema reference card. |
| **Proper fix** | Aspirational schema-hygiene refactor — standardise on `bar_ts` for time-series bar data, `ts` for snapshot/event data, `created_at`/`updated_at` as sidecars. Would require migrations and code refactors across all readers. Not worth scheduling unless an unrelated migration is happening. |
| **Cost to fix** | ~3-5 sessions for schema migration + reader updates. Cost-benefit not favourable for now. |
| **Blocked by** | nothing — but not a priority |
| **Owner check-in** | 2026-04-27 |

---

### TD-038 — `hist_spot_bars_5m` has no `is_pre_market` column (schema assumption mismatch)

| | |
|---|---|
| **Severity** | S3 |
| **Discovered** | 2026-04-28 (Session 11 Exp 34 bug B1) |
| **Component** | `hist_spot_bars_5m`, any research script querying it |
| **Symptom** | Scripts that filter `.eq("is_pre_market", False)` raise `APIError 42703: column does not exist`. First hit: Exp 34 initial run returned 0 events because the Supabase query failed silently. |
| **Root cause** | The column `is_pre_market` does not exist in `hist_spot_bars_5m`. Pre-market exclusion must be done by filtering `bar_ts` to session hours (09:15–15:30 IST). |
| **Workaround** | Filter by time: `WHERE EXTRACT(HOUR FROM bar_ts AT TIME ZONE 'Asia/Kolkata') * 60 + EXTRACT(MINUTE ...) BETWEEN 555 AND 930`. In Python (with TD-029 workaround applied): filter post-fetch using `9*60+15 <= bar_minutes(dt) <= 15*60+30`. |
| **Proper fix** | Either (a) add `is_pre_market` column as a computed boolean on insert, or (b) document the absence in `merdian_reference.json` tables entry and ensure all scripts use time-based filtering. Option b is lighter. |
| **Cost to fix** | <0.5 sessions for option b. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-28 |

---

### TD-039 — `hist_pattern_signals.ret_30m` stored as percentage points, not decimal fraction

| | |
|---|---|
| **Severity** | S2 |
| **Discovered** | 2026-04-28 (Session 11 Exp 41 — ret_30m inflated by 100x, corrected in Exp 41B) |
| **Component** | `hist_pattern_signals` table, `ret_30m` and `ret_60m` columns |
| **Symptom** | Any script that uses `ret_30m` as a decimal fraction (multiplying directly by spot price) gets numbers 100x too large. Exp 41 showed SENSEX E4 EV = −11,649 pts per trade, clearly impossible. |
| **Root cause** | `ret_30m` is populated as a percentage (e.g., 0.1351 = 0.1351% move, not 13.51%). The schema comment or docs do not make this explicit. |
| **Workaround** | Divide `ret_30m` by 100 before using as a decimal fraction. Sign convention: BEAR_OB wins when `ret_30m < 0` (spot fell). BULL_OB wins when `ret_30m > 0`. Codified in CLAUDE.md Rule 14. |
| **Proper fix** | Either (a) update all writers to store as decimal fraction (breaking change to any existing consumers), or (b) rename column to `ret_30m_pct` to make the unit explicit in the schema. Option b is safer. Also add column comment in Supabase: `COMMENT ON COLUMN hist_pattern_signals.ret_30m IS 'Spot return in percentage points (divide by 100 for fraction)'`. |
| **Cost to fix** | <0.5 sessions for option b + comment. |
| **Blocked by** | nothing |
| **Owner check-in** | 2026-04-28 |

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

### TD-019 (closed) — `hist_spot_bars_5m` pipeline stale since 2026-04-15

| | |
|---|---|
| **Closed** | 2026-04-26 (Session 9) |
| **Closing commit** | `<hash>` (Session 9 commit batch) |
| **Fix applied** | Three changes in one session (override of no-fix-in-diagnosis-session rule logged): (1) Patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog` instrumentation. `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` (minimum-1 row semantics); try/except wrap → `CRASH` exit reason on unhandled exceptions. (2) Backfilled 42,324 5m rows + 14,440 15m rows via `python build_spot_bars_mtf.py`, 116s, idempotent on `idx_hist_spot_5m_key` / `idx_hist_spot_15m_key`. (3) Registered `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task. Daily 16:00 IST Mon-Fri via `run_spot_mtf_rollup_once.bat` wrapper (mirrors existing MERDIAN task pattern; logs to `logs\task_output.log`). |
| **Validation** | `script_execution_log` shows two SUCCESS rows for `build_spot_bars_mtf.py` on 2026-04-26 (manual run 11:22 IST, smoke-test invocation via Task Scheduler 11:37 IST). Both `contract_met=true`, both `actual_writes={"hist_spot_bars_5m": 42324, "hist_spot_bars_15m": 14440}`, durations 116s and 118s. `Get-ScheduledTaskInfo MERDIAN_Spot_MTF_Rollup_1600` returns `LastTaskResult=0, NextRunTime=2026-04-27 16:00:00`. |
| **Files changed** | `build_spot_bars_mtf.py` (patched in place; `+1841` bytes; backup `build_spot_bars_mtf.py.pre_td019.bak`). New: `run_spot_mtf_rollup_once.bat`, `register_spot_mtf_rollup_task.ps1`, `fix_td019_instrument_build_spot_bars_mtf.py`, `fix_td019_add_sys_import.py`. Updated: `merdian_reference.json` (build_spot_bars_mtf entry status + cadence + scheduled_tasks block + ENH-73 + TD entries), `tech_debt.md` (this entry + TD-023..026), `CURRENT.md` (full rewrite for Session 10), `session_log.md` (one-liner). |
| **Lesson** | (a) "Manual on-demand rebuild" is a data-pipeline anti-pattern — it survives one operator's memory gap by exactly zero days. Every writer to a production table must be both instrumented (ENH-71) and scheduled. (b) Q-A pattern (`script_execution_log.actual_writes::text LIKE '%<table>%'`) is the canonical detector for uninstrumented producers — the absence of a hit IS the smoking gun. Filed as TD-023 to audit-and-patch the rest of the producers. (c) Override of "no fix in diagnosis session" rule was justified by the user this session ("overheads are too much to carry to next") but burned the firebreak that the rule was protecting. The rule pays its rent across multiple sessions; future overrides should be rare and explicit. |

---

### TD-020 (closed) — LONG_GAMMA gate on 2026-04-24 strongly directional day -- diagnosis required before ADR-002 ratification

| | |
|---|---|
| **Closed** | 2026-04-26 (Session 9 reframing; Session 8's prior close was incorrect) |
| **Closing commit** | `<hash>` (Session 9 second-batch commit) |
| **Original Session 8 disposition (NOW SUPERSEDED):** Concluded "gate had no signals to filter; ICT detector silent" and pointed at TD-022 as the real cause. That conclusion was wrong. |
| **Corrected disposition (2026-04-26, Session 9):** The LONG_GAMMA gate DID fire on every 2026-04-24 cycle, exactly as designed. Source path in `build_trade_signal_local.py`: when `gamma_regime == "LONG_GAMMA"`, three things happen in sequence: `cautions.append(...)`, `action = "DO_NOTHING"`, `trade_allowed = False`, **`direction_bias = "NEUTRAL"`**. The gate setting `direction_bias=NEUTRAL` is part of firing, not evidence the gate received nothing. Session 8 saw the gate's OUTPUT (NEUTRAL/DO_NOTHING) and read it as the gate's INPUT (no signals). |
| **Evidence (Session 9 verification):** Q-022-A: 245 signal_snapshots rows on 04-24, all `direction_bias='NEUTRAL'`, all `action='DO_NOTHING'`, `gamma_regime='LONG_GAMMA'` on every row, `net_gex` strongly positive throughout. Q-022-10: gamma_regime breakdown 04-20 to 04-24 confirmed 100% LONG_GAMMA / NO_FLIP coverage on 04-22 / 04-23 (NIFTY) / 04-24 — and on those exact dates, zero PE rows. PE rows fired only in the brief SHORT_GAMMA windows on 04-21 (3 PEs) and 04-23 (35 PEs). |
| **Why this matters:** The gate is mechanically correct. The question of whether it should have fired on a -1.6%/-1.4% directional cascade day is a CALIBRATION question, not a BEHAVIOUR question. ENH-35's 47.7% historical accuracy on LONG_GAMMA cycles validates the gate against a population average; whether the directional sub-population within LONG_GAMMA is mis-served is the question Exp 28/28b investigated (see Compendium). |
| **Files referenced (no code changed for this TD):** `build_trade_signal_local.py` (read-only confirmation of gate logic in the LONG_GAMMA branch). |
| **Validation:** None coded. The disposition is documentary — a corrected reading of existing live data. |
| **Lesson** | When a gate's design includes mutating the inputs it conditions on (here: gate sets `direction_bias=NEUTRAL` AS PART of firing), reading the resulting state to ask "did the gate fire?" is circular. Always trace the gate from its trigger, not from its visible aftermath. Session 8 made the inverse error and chained TD-022 onto a flawed premise; Session 9's deep-dive into source restored the ordering. Going forward, any TD that hypothesises "gate did/didn't fire" must verify by reading source flow, not output state. |

---

*MERDIAN tech_debt.md v1 — created concurrent with CLAUDE.md and Documentation Protocol v3. Update inline as items are added/closed; commit with `MERDIAN: [OPS] tech_debt — <action>`.*
