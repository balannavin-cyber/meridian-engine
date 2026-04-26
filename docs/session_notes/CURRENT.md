# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-26 (Sunday — Session 9) |
| **Concern** | Originally scoped: Candidate B from Session 8's CURRENT.md — TD-019 Step 1 diagnosis (read-only). Operator override mid-session pulled Step 1 + Step 2 (repair) + backfill + scheduling into one session. Justification logged: "overheads are too much to carry to next." |
| **Type** | Diagnostic + repair + automation. Single-session override of "no fix in diagnosis session" rule. |
| **Outcome** | DONE — TD-019 fully CLOSED. Three changes delivered: (1) ENH-71 instrumentation patched into `build_spot_bars_mtf.py`, (2) 7 trading days backfilled (42,324 5m + 14,440 15m rows in 116s), (3) `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task registered and smoke-tested. Diagnosis surprise: original 3 hypothesised causes (Task Scheduler silent fail / aggregator broken / writer error) all refuted. Real cause: producer was never instrumented AND never scheduled — manual on-demand rebuild last run on or around 2026-04-15 EOD. Q-A audit on `script_execution_log` for `actual_writes/expected_writes` referencing `hist_spot_bars_5m` returned zero rows, confirming uninstrumented status. Bonus: filed TD-023 (uninstrumented-producer audit), TD-024 (post-close write anomaly on 04-13 + 04-24), TD-025 (full-rebuild compute waste), TD-026 (PowerShell ASCII-only convention). |
| **Git start → end** | `1de239a` → `<hash>` (Session 9 commit batch) |
| **Local + AWS hash match** | Local advancing; no AWS-side changes (the rollup writer and Task Scheduler binding are local-only). |
| **Files changed (code)** | `build_spot_bars_mtf.py` (patched in place; `+1841` bytes vs pre-Session-9 baseline) |
| **Files added (tracked)** | `run_spot_mtf_rollup_once.bat`, `register_spot_mtf_rollup_task.ps1`, `fix_td019_instrument_build_spot_bars_mtf.py`, `fix_td019_add_sys_import.py` |
| **Files added (untracked)** | `build_spot_bars_mtf.py.pre_td019.bak` (gitignored if `.bak` pattern present) |
| **Files modified (docs)** | `tech_debt.md` (TD-019 closed, TD-023..026 filed), `CURRENT.md` (this rewrite), `merdian_reference.json` (build_spot_bars_mtf entry update + scheduled_tasks block + ENH-73 entry + TD-019 closed + TD-023..026 added), `session_log.md` (one-liner) |
| **Tables changed** | `hist_spot_bars_5m` (+42,324 rows backfilled across 7 trading days; idempotent on `idx_hist_spot_5m_key`). `hist_spot_bars_15m` (+14,440 rows). `script_execution_log` (+2 SUCCESS rows for `build_spot_bars_mtf.py`). |
| **Cron / Tasks added** | `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task — Mon-Fri 16:00 IST — wraps `run_spot_mtf_rollup_once.bat` → `python build_spot_bars_mtf.py`. Smoke-tested same session: `LastTaskResult=0`, `NextRunTime=2026-04-27 16:00:00`. |
| **`docs_updated`** | YES |

### What today did, in 6 bullets

- **TD-019 root cause turned out NOT to be any of the originally-hypothesised candidates.** The Q3 freshness query showed `market_spot_snapshots` and `hist_spot_bars_1m` current to 2026-04-24 19:01 IST while only `hist_spot_bars_5m` was stuck at 2026-04-15 15:25. So capture was healthy and only the rollup was dead. The Q-A audit (`actual_writes::text LIKE '%hist_spot_bars_5m%' OR expected_writes::text LIKE '%hist_spot_bars_5m%'`) returned zero rows in `script_execution_log` — proving no script in the instrumentation layer ever claimed responsibility for that table. Reading `build_spot_bars_mtf.py` source revealed it was a full-history manual rebuild tool, not an automated rollup; nothing else in the repo invoked it; no Task Scheduler task referenced it. The 04-15 EOD silence was simply "operator stopped running it manually."
- **Override of "no fix in diagnosis session" rule.** Operator chose to fix in same session due to overhead concerns. Logged in tech_debt.md TD-019 closure as a deliberate exception. Rule's value is not disputed — it pays rent across multiple sessions — but the override let us close TD-019 + register all four follow-up TDs before context degraded.
- **Three changes delivered to close TD-019.** (1) Patched `build_spot_bars_mtf.py` with ENH-71 `core.execution_log.ExecutionLog`; `expected_writes={"hist_spot_bars_5m": 1, "hist_spot_bars_15m": 1}` minimum-1-row semantics. Try/except wrap routes unhandled exceptions to `exit_with_reason('CRASH')`. (2) Backfill ran in 116s producing 42,324 5m + 14,440 15m rows; idempotent on the unique indexes; verified by SUCCESS row in `script_execution_log` with `contract_met=true, host=local, git_sha=1de239a`. (3) `MERDIAN_Spot_MTF_Rollup_1600` Task Scheduler task registered via `register_spot_mtf_rollup_task.ps1` (idempotent) calling `run_spot_mtf_rollup_once.bat`; smoke-tested via `Start-ScheduledTask` and produced a second SUCCESS row; `NextRunTime=Mon 2026-04-27 16:00:00`.
- **TD-023 filed (S3) — uninstrumented data producers as an anti-pattern.** TD-019's silence survived 7 trading days because the producer wasn't in `script_execution_log`. The Q-A pattern is now the canonical detector: any public data table with zero hits in `script_execution_log.actual_writes/expected_writes` has an uninstrumented producer. Audit-and-patch is a 1-2 session sub-project; defer until convenient.
- **TD-024 filed (S4) — two post-close write events surfaced.** 2026-04-24 `market_spot_snapshots` write at 19:01 IST (3.5h after `MERDIAN_Spot_1M` schedule end), and 2026-04-13 (Mon) `hist_spot_bars_5m` having 152 bars instead of 150 with `last_bar` 16:10 IST. Could be ENH-73 heartbeat (deployed Session 8 — fits 04-24 timing but not 04-13), undocumented EOD job, or manual run. Not a correctness issue; flagged for understanding.
- **TD-025 (S4) and TD-026 (S4) filed.** TD-025: `build_spot_bars_mtf.py` re-aggregates full history every run (~16h/year wasted compute); refactor to incremental + `--full` flag for backfills. TD-026: `.ps1` and `.bat` files in this repo are ASCII-only; em-dash in `register_spot_mtf_rollup_task.ps1` triggered a misleading parse error this session. Add convention to CLAUDE.md alongside TD-010.

---

## This session

> Session 10. Pick ONE primary path from below at session start.

### Candidate A (recommended) — TD-022 ICT detector silence diagnosis

| Field | Value |
|---|---|
| **Goal** | Diagnose why ICT pattern detector produced zero setups on 2026-04-24 despite the chart-visible W BULL_FVG break and -393pt cascade. Three sub-hypotheses to discriminate: (1) lookback/window mismatch — detector requires `status='ACTIVE'` but the zone became `BREACHED` early in the day; (2) detector silently failing on TD-019 stale 5m bar feed (now testable cleanly because 5m is current as of Session 9); (3) pattern-coverage gap — the cascade structure is not a pattern type the detector knows about. Code-reading + targeted replay. |
| **Type** | Code review + data replay. Read-only relative to production tables. |
| **Success criterion** | TD-022 marked diagnosed (one of 1/2/3 supported with evidence); ADR-002 disposition stated based on whether the silence is a bug or expected behaviour; if a code fix is required, scoped to a Session 11 successor ENH. **Hold the no-fix-in-diagnosis-session rule this time** — Session 9's override was justified by repair scope but TD-022 is bigger and the firebreak matters. |
| **Time budget** | ~25-40 exchanges. |

### Candidate B — TD-023 audit pass on uninstrumented producers

| Field | Value |
|---|---|
| **Goal** | Walk every `public.*` data table; for each, run the Q-A pattern against `script_execution_log` to identify uninstrumented producers; locate writers via `Get-ChildItem -Recurse \| Select-String "<table>"`; patch each with the `build_spot_bars_mtf.py` template. Time-boxed — set a stop after N tables audited; don't try to finish the full pass in one session. |
| **Type** | Read-only audit. Patch work optional within session if findings are small. |
| **Success criterion** | Every public data table classified as instrumented / uninstrumented / no-active-producer. Sub-TDs filed for each uninstrumented producer with sufficient detail for a Session 11+ patch pass. |
| **Time budget** | ~20-30 exchanges. Stop early if findings are large. |

### Candidate C — ADR-002 ratification (still BLOCKED)

| Field | Value |
|---|---|
| **Goal** | Originally Session 7's Candidate A. Now BLOCKED on TD-022 (Session 8 reframing). Listed for visibility only. |
| **Time budget** | N/A this session. |

### Candidate D — Kite token propagation automation (C-10) — deferred

| Field | Value |
|---|---|
| **Goal** | Operational automation. Lower priority than TD-022 / TD-023. Deferred to Session 11+. |
| **Time budget** | N/A this session. |

### DO_NOT_REOPEN

- All items from Session 8's CURRENT.md DO_NOT_REOPEN list (capital ceiling, strategy choice, T+30m exit, 5m vs 1m for ICT, OI-* namespace, ENH-72, V19A/B/C as per-session, em-dashes in commits, PS 5.1 Get-Content, `python -c` for multi-line replace in PS, breadth cascade root cause, contamination registry approach, 1H ICT pre-market silence, Kite "AUTH FAILED then AUTH OK", Experiment 17 hypothesis as written, 02-06-2025 events as outliers, ADR-002 unconditional ratification pending TD-022)
- **TD-020 LONG_GAMMA gate question** — closed Session 8. Gate was not the cause of trade absence on 2026-04-24; ICT detector produced zero signals. Do not re-open the gate-blocking framing.
- **TD-019 root cause: uninstrumented + unscheduled, not a code bug.** Manual run was last-touched on 04-15 EOD; that's all that happened. Three originally-hypothesised candidates (Task Scheduler silent fail / aggregator cron broken / writer error) are all REFUTED with evidence. Do not re-litigate.
- **TD-019 closure approach** — instrument + backfill + schedule, in that order, all in one session. The fact that this worked is not license to override "no fix in diagnosis session" routinely. Session 9 override was justified; Session 10 default is back to the rule.
- **`build_spot_bars_mtf.py` is now an automated daily writer.** Manual `python build_spot_bars_mtf.py` invocations are still legal (and idempotent) but no longer required. The "manual on-demand rebuild tool" framing is closed.

### Watch-outs for Candidate A (TD-022 diagnosis)

- The diagnosis is read-only. Resist any urge to fix what gets diagnosed in the same session — split into Session 11. Session 9's override was a one-off.
- Sub-hypothesis (2) "stale 5m fed garbage" is now CLEANLY testable because `hist_spot_bars_5m` is current. If detector reads from current 5m and still produces NONE on a replay of 2026-04-24, hypothesis (2) is refuted; if detector behaviour changes when fed fresh 5m data, hypothesis (2) is supported. This is the strongest diagnostic lever Session 10 has.
- ADR-002 is in-flight; do not draft its content this session — only state which way TD-022 unblocks it.
- Use `signal_snapshots`, `ict_zones`, `ict_htf_zones`, `options_flow_snapshots`, `gamma_metrics` for replay context. `hist_pattern_signals` and `signal_snapshots_shadow` were both empty for 2026-04-24 (Session 8 evidence) so they don't add information.

### Watch-outs for Candidate B (TD-023 audit)

- Time-box hard. There are likely 20+ public data tables; full pass in one session is unrealistic.
- The Q-A pattern returns false negatives if a table name is a substring of another (e.g. `hist_spot_bars_5m` is a substring of `hist_spot_bars_5m_v2` if it existed). Use word boundaries or exact matches in the LIKE clause.
- Any `actual_writes` JSONB referencing a table proves an instrumented producer EXISTS but doesn't prove it covers the FULL set of writers to that table. A table can have one instrumented producer and one uninstrumented producer simultaneously. Cross-reference with `Get-ChildItem | Select-String "<table>"` to confirm complete coverage.

---

## New TDs to file at Session 10 start

None. TD-023, TD-024, TD-025, TD-026 already filed in Session 9 close batch.

---

## Live state snapshot (at Session 10 start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. 2026-04-24 cascade day still the active diagnostic anchor for TD-022. |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) — corrupted breadth caveat. ADR-002 BLOCKED on TD-022. |
| **Breadth pipeline** | FIXED and verified in production 2026-04-24 09:31 IST (Session 7 closure). Independent of any Session 9 work. |
| **Spot bar pipeline (`hist_spot_bars_5m`)** | **HEALTHY.** Current to 2026-04-24 15:25 IST. Daily 16:00 IST Mon-Fri rollup via `MERDIAN_Spot_MTF_Rollup_1600`. ENH-71 instrumented; surfaces in `script_execution_log`. |
| **Local env** | Windows Task Scheduler. PS 5.1 with UTF-8 profile. Git CRLF auto-conversion (cosmetic). PowerShell ASCII-only convention now in force (TD-026). |
| **AWS env** | MERDIAN AWS `i-0878c118835386ec2` (eu-north-1). 11 cron jobs total. Shadow runner FAILED since 2026-04-15 (pre-existing; tracked separately). |
| **MeridianAlpha AWS** | `13.51.242.119`. C-10 OPEN. |
| **Local git HEAD** | `<hash>` (Session 9 commit batch — in sync with origin/main after push) |
| **Last canary tag** | none — no live canary in Session 9 |
| **Open C-N (critical)** | C-10 HIGH OPEN (Kite token propagation manual) |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill), TD-022 (ICT detector silent on cascade days — primary Session 10 candidate) |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007, TD-015, TD-016, TD-017, TD-023 (NEW — uninstrumented-producer audit) |
| **Open TD S4** | TD-009, TD-010, TD-018, TD-021, TD-024 (NEW — post-close write anomaly), TD-025 (NEW — full-rebuild waste), TD-026 (NEW — PS ASCII-only) |
| **Closed in Session 7** | C-09, TD-014 |
| **Closed in Session 8** | TD-020 (LONG_GAMMA gate question diagnosed — gate was not the cause; replaced by TD-022) |
| **Closed in Session 9** | TD-019 (stale 5m pipeline — uninstrumented + unscheduled, both fixed; rollup task bound and smoke-tested) |
| **Open from Session 7** | ADR-002 phase-4a-posture (BLOCKED on TD-022) |
| **Active research backlog** | Exp 17 closed FAIL. Exp 17b proposed (composition-cleaned). Exp 18-23 in Compendium backlog. |
| **Active ENH in flight** | none |
| **Data contamination** | `BREADTH-STALE-REF-2026-03-27` registered. 27-day window 2026-03-27 → 2026-04-23. |
| **ENH-73 status** | DEPLOYED (Session 8). Telegram alerts + 10-min heartbeat. Owner script `merdian_pipeline_alert_daemon` (last SUCCESS 2026-04-26 09:12 IST per `script_execution_log`). |

---

## Mid-session checkpoints

> Per Session Management Rule 1: every ~20 exchanges, write 5 bullets here. Do not wait until session end.

### Checkpoint 1 (~20 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

### Checkpoint 2 (~40 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

---

## Session-end checklist (before commit)

```
[ ] CURRENT.md updated — "Last session" reflects THIS session, "This session" reset for next
[ ] session_log.md appended (one line)
[ ] merdian_reference.json updated for any file/table/item status change
[ ] tech_debt.md updated if any TD added, mitigated, or closed
[ ] Enhancement Register updated if architectural thinking happened
[ ] Local + AWS hash match confirmed if code changed
[ ] All commits prefixed: MERDIAN: [ENV|DATA|SIGNAL|OPS|RESEARCH] <scope> -- <intent>
[ ] Re-upload to project knowledge any of CURRENT.md / session_log.md / merdian_reference.json / tech_debt.md / Enhancement_Register / CLAUDE.md / docs/operational/* that changed (Rule 12)
[ ] Phase boundary check: any Master/Appendix .docx generation triggered? (rare)
[ ] Runbook review: any operation explained for 2nd time? Create runbook from RUNBOOK_TEMPLATE.md
[ ] data_contamination_ranges review: new contamination this session? INSERT row (Rule 13)
```

---

## TD-022 starter approach (Candidate A first step)

```sql
-- 1. Replay context: what did the detector see during 2026-04-24 09:15-15:30 IST?
SELECT
    (created_at AT TIME ZONE 'Asia/Kolkata')::timestamp AS created_ist,
    symbol, ict_pattern, direction_bias, action,
    zone_id, zone_status, source_ts
FROM public.signal_snapshots
WHERE created_at >= '2026-04-24 09:00:00+05:30'
  AND created_at < '2026-04-24 16:00:00+05:30'
ORDER BY created_at;

-- 2. Zone state during the day: ACTIVE vs BREACHED transitions
SELECT
    (status_changed_at AT TIME ZONE 'Asia/Kolkata')::timestamp AS changed_ist,
    symbol, zone_type, status, zone_low, zone_high
FROM public.ict_htf_zones
WHERE timeframe = 'W'
  AND status_changed_at >= '2026-04-24 00:00:00+05:30'
  AND status_changed_at < '2026-04-25 00:00:00+05:30'
ORDER BY symbol, status_changed_at;

-- 3. NEW (Session 10): now that hist_spot_bars_5m is current, check
--    whether 2026-04-24 5m bars are present and whether they could
--    have driven detector output had they been available live.
SELECT
    (bar_ts AT TIME ZONE 'Asia/Kolkata')::timestamp AS bar_ist,
    symbol, open, high, low, close
FROM public.hist_spot_bars_5m
WHERE bar_ts >= '2026-04-24 09:00:00+05:30'
  AND bar_ts < '2026-04-24 16:00:00+05:30'
  AND symbol = 'NIFTY'
ORDER BY bar_ts;
```

If sub-hypothesis (2) — "stale 5m fed garbage" — is supported, the next step is to read `build_trade_signal_local.py` + the ICT detector entry-point and document what input each pattern type requires from `ict_htf_zones` and `hist_spot_bars_5m`.

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-26 (end of Session 9 — TD-019 CLOSED end-to-end, TD-023..026 filed, Session 10 priority is TD-022 ICT detector silence diagnosis).*
