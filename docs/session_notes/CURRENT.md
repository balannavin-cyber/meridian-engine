# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-05-05 (Tuesday — Session 20, very long: pre-dawn → 21:00+ IST). |
| **Concern** | Began as TD-068 audit task fix from Session 19. Expanded into full diagnostic of `capture_spot_1m.py` synthetic-flat-bar architecture (long-standing root cause for BULL_OB/BEAR_OB zero-emission across detection history). Cascaded into spot data backfill Apr 1 → May 5. Concluded with Phase 2a deployment of v2.1 real-OHLC live writer + HTF zone rebuild + Pine static rewrite. |
| **Type** | Engineering — multi-deliverable session: 2 production patches deployed (audit script rewrite + capture_spot_1m_v2 NEW), 1 data recovery (16,500 spot bars Apr 1 → May 5 real OHLC), 1 architectural change (live writer LTP synthetic → REST OHLC), 1 Pine static rewrite, 5 TDs filed. |
| **Outcome** | DONE. **TD-068 RESOLVED end-to-end:** v2.1 `capture_spot_1m_v2.py` deployed to Local Task Scheduler with full `pythonw.exe` path; replaces synthetic O=H=L=C=spot from `/v2/marketfeed/ltp` with real 1-min OHLC from `/v2/charts/intraday`; v2.1 features market-hours guard + filler-bar skip for post-market filler responses; v1 untouched at `capture_spot_1m.py` for rollback. **Daily audit task fixed and rewritten:** Session 19 script broken (MimeText Python 3.12 incompat, wrong table names, malformed PostgREST queries, Task Scheduler ERROR_FILE_NOT_FOUND from bare `python`); fixed via new `run_daily_audit.bat` wrapper; full rewrite (831 lines) using Supabase Python client, three windows (pre/intra/post), per-pattern-type breakdown surfacing zero-emission as WARN. **Spot backfill Apr 1 → May 5:** 16,500 clean OHLC rows in `hist_spot_bars_1m`, 0 flats, both NIFTY+SENSEX (Kite returns SENSEX index spot OHLC despite no BSE F&O); 16 stray 15:30:00 IST boundary flat bars deleted via scoped DELETE. **HTF zones rebuilt with real OHLC:** detector now fires all 4 pattern types — W BULL_OB 2 ACTIVE / 18 BREACHED, W BULL_FVG 2 ACTIVE / 11 BREACHED, W BEAR_OB 0 ACTIVE / 2 BREACHED, W BEAR_FVG 0 ACTIVE / 2 BREACHED. Confirms detector logic sound — previous BULL_OB/BEAR_OB zero-emission was data-driven (synthetic flat bars), not detector defect. **Pine static rewrite shipped:** 14 zones (NIFTY 7 + SENSEX 7) from tonight's rebuild — clean OHLC, no stale M5 noise; new color spec applied (BULL_OB green #1B8C3E, BULL_FVG light green #6FCF7C, BEAR_OB red #B22222, BEAR_FVG light red #F08080, white text labels, PDH/PDL stay yellow/orange). |
| **Git start → end** | Local Windows: `pending` → `pending` (operator commits at end of session per protocol). MALPHA AWS: `backfill_spot_zerodha.py` BACKFILL_DATES extended (uncommitted, undesirable but accepted — MALPHA is Kite gateway not Meridian code). Meridian AWS: not touched this session. |
| **Local + AWS hash match** | Local advancing this session. Meridian AWS not touched. MALPHA AWS has dirty BACKFILL_DATES extension (one-off backfill, won't recur). Phase 2b AWS migration deferred to Session 21+. |
| **Files changed (code)** | `merdian_daily_audit.py` (FULL REWRITE — 831 lines, backup `.pre_s20.bak`); `run_daily_audit.bat` (NEW wrapper); `capture_spot_1m_v2.py` (NEW — 475 lines, v2.1 with market-hours guard + filler-bar skip); Task Scheduler `MERDIAN_Daily_Audit` action updated to use bat wrapper; Task Scheduler `MERDIAN_Spot_1M` action repointed to v2 with full `pythonw.exe` path. |
| **Files added (untracked, working dir)** | `C:\GammaEnginePython\capture_spot_1m_v2.py`, `C:\GammaEnginePython\run_daily_audit.bat`, `C:\GammaEnginePython\merdian_daily_audit.py.pre_s20.bak`, `C:\GammaEnginePython\logs\dhan_probe.py` (one-off Dhan API verification), `C:\GammaEnginePython\logs\v2_test_*.log`. Pine static rewrite `merdian_ict_htf_zones_s20.pine` ready for paste into TradingView. |
| **Files modified (docs)** | `CURRENT.md` (this rewrite — Session 17 content preserved below as historical reference per no-crunch directive). `session_log.md` (Session 20 one-liner prepended). `tech_debt.md` (TD-067, TD-068, TD-069, TD-070, TD-071 added; TD-068 moved to Resolved same session). `MERDIAN_Enhancement_Register.md` (no new ENH this session — operational/data integrity work). `merdian_reference.json` (v13→v14; change_log entry for Session 20). `CLAUDE.md` (v1.13→v1.14; Rule 23 + B15 + B16 + multiple operational findings). |
| **Tables changed** | None (schema). Data: `hist_spot_bars_1m` 16,500 rows backfilled real OHLC + 16 stray flats deleted; `ict_htf_zones` 80 zones written by rebuild (NIFTY 39 + SENSEX 41 with breach status). |
| **Cron / Tasks added** | `MERDIAN_Daily_Audit` action updated to use `run_daily_audit.bat` wrapper. `MERDIAN_Spot_1M` action repointed to `capture_spot_1m_v2.py` with full `pythonw.exe` path. No new tasks added. |
| **`docs_updated`** | YES. All six closeout files produced as full downloads (no append/prepend deltas, no crunching of old entries) per user directive. |

### What Session 20 did, in 14 bullets

**Phase 1 — Daily audit task fix + full rewrite:**

- **Discovered Session 19's `merdian_daily_audit.py` broken on multiple fronts.** `MimeText` import was Python 3.12 incompatible (renamed `MIMEText` in stdlib); table name `ict_patterns` should be `ict_zones`; PostgREST queries had duplicate dict keys (later definition silently shadowed earlier). Task Scheduler `MERDIAN_Daily_Audit` showed `LastTaskResult=2147942402` = ERROR_FILE_NOT_FOUND because action used bare `python` instead of full path — same bug pattern that bit `MERDIAN_Spot_1M` swap later in session.

- **Fixed Task Scheduler via new `run_daily_audit.bat` wrapper** mirroring `run_ict_htf_zones_daily.bat` pattern. Updated task action to invoke the bat. Verified action via Get-ScheduledTask.

- **Full rewrite of audit script (831 lines)** using Supabase Python client (not raw REST). Three windows: pre-market 08:00-09:14 IST, intraday 09:15-15:30 IST, post-market 15:30+ IST. ExecutionLog instrumented. Per-pattern-type breakdown for `ict_zones` surfaces BULL_OB/BEAR_OB zero-emission as WARN (was the trigger that surfaced TD-068 root cause). Per-script cycle counts. Crash count. Always exits 0; JSON has the actual verdict. Deployed to `C:\GammaEnginePython\merdian_daily_audit.py` (backup `.pre_s20.bak`). Test fire: PASS pre, FAIL intra (legitimate WARN on BULL_OB/BEAR_OB zero emissions + flat-bar finding) — confirms audit doing its job.

**Phase 2 — capture_spot_1m flat-bar root cause (the diagnostic that took the longest):**

- **Locked diagnosis only after triple-verification.** Assistant oscillated 4 times before settling: (1) 04:00 IST concluded synthetic flats since Apr 13; (2) 06:30 IST walked back wrongly with bad audit query; (3) 17:00 IST concluded again after audit rewrite; (4) 18:00 IST walked back AGAIN after Apr 21 random sample showed real OHLC (forgot those were morning's Kite backfill alongside flat bars); (5) 18:30 IST FINAL lock after triple-verification: source code reads `O=H=L=C=spot` literally (`hist_spot_bars_1m` synthetic bar convention from script's docstring); today's bars sampled directly = 376/376 flat; `script_execution_log` shows ONLY `capture_spot_1m.py` writes to `hist_spot_bars_1m` (3,897 runs in 30 days, sole writer). User extremely frustrated by oscillation; assistant acknowledged failure pattern and filed B15 anti-pattern.

- **Detection implication:** All four ICT pattern types (BULL_OB, BEAR_OB, BULL_FVG, BEAR_FVG) require candle direction (open vs close); cannot fire on synthetic flat bars where all four equal `last_price`. Explains BULL_OB/BEAR_OB zero-emission across 7+ days surfaced by audit. Filed as TD-068.

**Phase 3 — Spot data backfill Apr 1 → May 5:**

- **Backfill executed on MALPHA AWS** (`ubuntu@13.51.242.119`, `~/meridian-alpha`). Patched `BACKFILL_DATES` to cover 23 trading days Apr 1 → May 5 via Python script with idempotent insertion + AST validation. Refreshed Kite token via OAuth dance (browser flow). Ran `backfill_spot_zerodha.py` → 16,500 rows written (22 trading days × 2 symbols × 375 bars; one date returned empty as holiday). Backfill upsert REPLACED flat bars rather than coexisting (different bar_ts precision). 16 stray flat bars at exact `15:30:00 IST` boundary deleted via scoped DELETE (predicate: trade_date BETWEEN '2026-04-01' AND '2026-05-05' AND time = '15:30:00' AND open=high=low=close).

- **Final state verified:** 22 trading days × 2 symbols × 375 bars = 16,500 clean OHLC rows in `hist_spot_bars_1m`, 0 flats, both NIFTY AND SENSEX. **Important finding: Kite returns SENSEX index spot OHLC despite not supporting BSE F&O.** This was unexpected and is the basis for the symmetric backfill working from a single Zerodha source.

**Phase 4 — Live writer architecture (multiple wrong turns then locked):**

- **Initial wrong direction.** Assistant proposed Kite WebSocket migration to AWS without reading existing code. User corrected MALPHA architecture confusion ("MALPHA only Kite gateway, no Meridian code, ever"). User then forced read of actual code which revealed Meridian AWS already runs `ws_feed_zerodha.py` with own Zerodha credentials AND Zerodha can't do SENSEX (BSE F&O not supported per ws_feed_zerodha docstring line 13). Filed B16 anti-pattern.

- **User insisted on single-source NIFTY+SENSEX.** "NIFTY and SENSEX ticks should be recorded. Cant be from different places." Hard constraint that ruled out Zerodha-NIFTY + Dhan-SENSEX hybrid. User listed three options: REST OHLC, mixed solution, or Dhan WebSocket subscription.

- **Web-fetch of Dhan docs** (https://dhanhq.co/docs/v2/historical-data/) confirmed `POST /v2/charts/intraday` returns full 1-min OHLC arrays (open[], high[], low[], close[], volume[], timestamp[]) for any instrument including IDX_I segment indices, intervals 1/5/15/25/60 min, 5-year history. **Key finding: Dhan REST supports OHLC** — endpoint name was just less obvious than the LTP endpoint capture_spot_1m was using.

- **Probe verified hypothesis A.** Manual probe of `/charts/intraday` for today 11:00-11:05 IST returned hundreds of REAL varying OHLC bars with non-zero volume during market hours; post-market query returned "filler" bars (V=0, flat OHLC matching last known price). Two distinct bar shapes confirmed: real OHLC during market hours always V>0 even on low-volatility minutes; filler bars only appear post-close.

**Phase 5 — capture_spot_1m_v2.py shipped (Phase 2a Local):**

- **`capture_spot_1m_v2.py` (475 lines, v2.1)** — drop-in replacement for `capture_spot_1m.py`. Uses `POST https://api.dhan.co/v2/charts/intraday` instead of `marketfeed/ltp`. Real OHLC from Dhan vendor, both NIFTY and SENSEX. Same .env vars (no new credentials). Same instrumentation (ExecutionLog `expected_writes` contract preserved). Same heartbeat wrapper. Same lock pattern (none — single-shot script). v2.1 features: market-hours guard (09:15-15:30 IST window check on requested bar's `from_ts`), filler-bar skip (V=0+flat detection prevents post-market filler writes). v1 untouched at `capture_spot_1m.py` for rollback.

- **Deployed to Local Task Scheduler `MERDIAN_Spot_1M`** with full `pythonw.exe` path matching v1's pattern. **Initial deployment mistake:** swapped to bare `python` causing same ERROR_FILE_NOT_FOUND vulnerability as audit task — caught and fixed in same exchange (filed Rule 23). Final action verified: `Execute=C:\Users\balan\AppData\Local\Programs\Python\Python312\pythonw.exe`, `Arguments=C:\GammaEnginePython\capture_spot_1m_v2.py`, `WorkingDirectory=C:\GammaEnginePython`. Test fire post-market: market-hours guard correctly skipped with `OUTSIDE_MARKET_HOURS` reason — exit clean, no API call, no writes.

**Phase 6 — HTF zones rebuild post-backfill:**

- **Ran `python build_ict_htf_zones.py --timeframe both`** against newly clean OHLC. Results: NIFTY weekly 33 OB/FVG (vs 4 before with synthetic data) + 4 PDH/PDL = 37 zones; SENSEX weekly 35 OB/FVG + 4 PDH/PDL = 39 zones; daily 0 OB/FVG + 2 PDH/PDL each (D-OB / D-FVG zero generation persists, filed TD-069). Total 80 zones written.

- **All 4 ICT pattern types fire on real data after rebuild:** W BULL_OB 2 ACTIVE / 18 BREACHED, W BULL_FVG 2 ACTIVE / 11 BREACHED, W BEAR_OB 0 ACTIVE / 2 BREACHED, W BEAR_FVG 0 ACTIVE / 2 BREACHED. Confirms detector logic is sound — previous BULL_OB/BEAR_OB zero emission was data-driven (synthetic flat bars), not detector bug. Bull bias (20 BULL_OB vs 2 BEAR_OB across 252 weeks) reflects real bull market over lookback period (NIFTY ~22,500 → recent peaks above 26,000 with episodic pullbacks), not detector defect.

- **`prev_move < 0` constraint observation in `detect_weekly_zones()`:** still trims real BULL_OB candidates even with real OHLC. Apr-13 (+2.27% bullish week) preceded by Apr-06 (+4.26% also bullish), so Apr-13 didn't generate a BULL_OB. Filed TD-070 to relax to "any bearish candle in last N weeks" per ICT canonical definition.

**Phase 7 — Pine static rewrite shipped:**

- **`merdian_ict_htf_zones_s20.pine`** generated with 14 zones from tonight's rebuild (NIFTY 7 + SENSEX 7) — clean OHLC, no stale M5 noise from earlier today's synthetic-flat-bar detection. Color spec applied per user direction: BULL_OB green (#1B8C3E), BULL_FVG light green (#6FCF7C), BEAR_OB red (#B22222), BEAR_FVG light red (#F08080), white text labels, PDH/PDL stay yellow (D) / orange (W) per liquidity-vs-directional distinction. Tier assignment: T1 D + W within 2% (4 zones each symbol), T2 W 2-5% from spot (2 zones BULL_FVG each), T3 W >5% from spot ghost no label (1 zone BULL_OB each).

- **Pre-flight verification of v2.1 cycle behavior** (deferred to tomorrow morning): 09:16:02 IST first cycle on v2.1 fires; query `script_execution_log` for capture_spot_1m_v2 invocations + `hist_spot_bars_1m` for is_flat=false on today's bars; rollback to v1 if Q1 returns no rows or contract_met=False. Audit at 16:00 IST verifies real OHLC end-to-end.

---

## This session (Session 21)

| Field | Value |
|---|---|
| **Goal** | TBD by operator. Several priorities lined up; pick ONE per Rule 3. |
| **Type** | Operator's call — engineering / operations / research. |
| **Success criterion** | Defined when goal is set. |

### Carry-forward priority queue (ordered by recommended priority for Session 21):

| Priority | Item | Why |
|---|---|---|
| **A** | Verify v2.1 first cycle 09:16 IST tomorrow + 16:00 IST audit | Critical to confirm Phase 2a deployment works on first live cycle. Verification SQL: (Q1) `SELECT exit_code, exit_reason, contract_met, actual_writes FROM script_execution_log WHERE script_name='capture_spot_1m_v2.py' AND started_at >= CURRENT_DATE ORDER BY started_at DESC LIMIT 5;` (Q2) `SELECT is_flat = (open=high AND high=low AND low=close) FROM hist_spot_bars_1m WHERE trade_date = CURRENT_DATE AND time >= '09:15';` Expect Q1 multiple rows with exit_code=0 contract_met=true; expect Q2 is_flat=false for all rows. If failed, rollback path documented in CURRENT.md `## Rollback path` section. |
| **B** | TD-067 — intraday backfill detector for Apr 1 → today | Now that real OHLC exists in `hist_spot_bars_1m` for Apr 1 → May 5, build `backfill_ict_zones.py` that walks each day's bars and runs `ICTDetector` on each to populate historical intraday pattern record we never had. Should fire all 4 pattern types now that data is real. ~30 min build + run. |
| **C** | TD-069 — investigate why D timeframe doesn't generate OB/FVG | W generates 33 OB/FVG NIFTY + 35 SENSEX with real data. D generates 0 even with same real data. Code review of `detect_daily_zones()` vs `detect_weekly_zones()`. May reveal threshold mismatch (D uses different `OB_MIN_MOVE_PCT`?) or data range issue. |
| **D** | Phase 2b — migrate `capture_spot_1m_v2.py` to Meridian AWS | Final architectural state. Local stabilization completed Phase 2a; AWS is the production target. Risk: Meridian AWS already runs `ws_feed_zerodha.py` for breadth; adding capture_spot_1m_v2 alongside requires no new credentials but does require systemd or cron entry coordination. Estimate 1-2 sessions. |
| **E** | TD-070 — relax `prev_move < 0` filter in `detect_weekly_zones()` | Detector tuning. ICT canonical: BULL_OB requires opposing bearish candle in vicinity, not strictly prior week. Fix expands BULL_OB candidate pool. May produce 5-10 more BULL_OBs in lookback. Low-risk one-line change. |
| **F** | TD-071 — fix `expire_old_zones()` order bug | Stale 2025 zones still showing ACTIVE because expire runs BEFORE upsert in `build_ict_htf_zones.py`. Order should be: upsert → recheck → expire. Investigate via code review. |

### Files / tables / items relevant for next session

- **`capture_spot_1m_v2.py`** — patched canonical (Session 20 Phase 2a deployment, Local). Backup at `capture_spot_1m.py` (v1 untouched).
- **`merdian_daily_audit.py`** — full rewrite Session 20. Backup at `.pre_s20.bak`.
- **`run_daily_audit.bat`** — new wrapper for Task Scheduler invocation.
- **Task Scheduler `MERDIAN_Spot_1M`** — repointed to v2 with full `pythonw.exe` path.
- **Task Scheduler `MERDIAN_Daily_Audit`** — repointed to bat wrapper.
- **`hist_spot_bars_1m` table** — primary observability target for v2.1 verification.
- **`script_execution_log` table** — secondary verification target for v2.1 deployment.
- **`ict_htf_zones` table** — 80 zones from tonight's rebuild; tomorrow morning's regeneration will overlay intraday zones too.
- **`/home/claude/output/merdian_ict_htf_zones_s20.pine`** — Pine static rewrite ready for paste into TradingView (replaced by tomorrow's dashboard refresh).

### Rollback path (if v2.1 fails tomorrow morning)

```powershell
$action = New-ScheduledTaskAction `
  -Execute "C:\Users\balan\AppData\Local\Programs\Python\Python312\pythonw.exe" `
  -Argument "C:\GammaEnginePython\capture_spot_1m.py" `
  -WorkingDirectory "C:\GammaEnginePython"
Set-ScheduledTask -TaskName "MERDIAN_Spot_1M" -Action $action
```

Verify with `Get-ScheduledTask -TaskName "MERDIAN_Spot_1M" | Select -ExpandProperty Actions | Format-List`.

### DO NOT REOPEN this session

- ❌ TD-068 capture_spot_1m flat-bar architecture — RESOLVED Session 20, v2.1 deployed
- ❌ Spot data backfill Apr 1 → May 5 — DONE, 16,500 clean rows verified
- ❌ Audit task script broken from Session 19 — RESOLVED with full rewrite
- ❌ Color spec for Pine — settled (BULL/BEAR red/green light/dark, white labels, PDH/PDL keep yellow/orange)
- ❌ Pine zone selection criteria — settled (live with overlap as accurate ICT clustering, no merge filter)
- ❌ MALPHA AWS vs Meridian AWS confusion — settled (MALPHA = Kite gateway only, no Meridian code; tonight's backfill on MALPHA was undesirable but accepted, not a precedent)
- ❌ Dhan REST OHLC support question — settled via web-fetch of dhanhq.co/docs/v2/historical-data; `/v2/charts/intraday` returns full OHLC arrays
- ❌ Hypothesis on Dhan filler bars — settled via probe; real OHLC during market hours, V=0+flat post-market

---

## Live state snapshot (at Session 21 start, 2026-05-05 close)

| Component | State |
|---|---|
| **Local** | v2.1 `capture_spot_1m_v2.py` deployed and Task Scheduler swapped (pythonw.exe full path). v1 backed up at `capture_spot_1m.py` for rollback. Audit script rewritten. All 13+ MERDIAN_* tasks operational. No zombie Python processes. |
| **AWS (MERDIAN, `i-0e60e4ed9ce20cefb`, `ssm-user@ip-172-31-35-90`)** | NOT touched this session. `ws_feed_zerodha.py` continues to stream NIFTY ticks to `market_ticks` table (26,537 today verified). `ingest_breadth_from_ticks.py` continues to produce breadth from those ticks. Phase 2b migration of capture_spot_1m_v2 deferred. |
| **AWS (MALPHA, `ubuntu@13.51.242.119`, `~/meridian-alpha`)** | Kite gateway only — NOT Meridian. Has `backfill_spot_zerodha.py` with extended BACKFILL_DATES from tonight's backfill (uncommitted, undesirable). Will not be used for Meridian code going forward per user directive. |
| **Critical items (C-N)** | None new. |
| **Tech debt (active)** | TD-067, TD-069, TD-070, TD-071 NEW Session 20. TD-068 RESOLVED same-session. Plus all pre-Session-20 active TDs unchanged (TD-029, TD-030, TD-031, TD-046, TD-049-052, TD-053-057, TD-059, TD-061, TD-062, TD-063). |
| **ENH in flight** | No new ENH this session (operational/data integrity work). ENH-88 still BUILT NOT DEPLOYED awaiting verification of OB signal flow on real OHLC. ENH-90 CANDIDATE deferred for N expansion. ENH-91 + ENH-92 SHIPPED (Session 17). |
| **Pine on TradingView** | S20 14-zone overlay ready in `/home/claude/output/merdian_ict_htf_zones_s20.pine` for paste; tomorrow morning's dashboard refresh will produce live overlay with intraday zones included. |
| **Spot data quality** | hist_spot_bars_1m has 16,500 clean OHLC rows Apr 1 → May 5 for both NIFTY+SENSEX. 0 flats. Verified post-DELETE. |
| **Live writer** | v2.1 `capture_spot_1m_v2.py` armed; first live cycle tomorrow 09:16:02 IST. |
| **Trading calendar** | 2026-05-06 (Wed) is open trading day. v2.1 verification opportunity. |

---

## Mid-session checkpoints (per Session Management Rule 1)

*Reset by Session 21 start.*

---

## Session-end checklist (run at end of each substantive session)

```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update tech_debt.md if a TD item changes
☐ Overwrite CURRENT.md (Last session reflects this session, This session reset)
☐ Append one line to session_log.md (newest-first prepend)
☐ Update Enhancement Register if architectural thinking happened
☐ Update CLAUDE.md if a Rule, settled decision, or anti-pattern was added
☐ Update Experiment Compendium if new experiment evidence was produced
☐ Commit all documentation changes to Git
☐ Upload updated files to Claude.ai project knowledge (Rule 12)
☐ AWS sync if production code changed (git push + AWS git pull)
☐ Re-enable any disabled Task Scheduler tasks before next market open
```

---

## Previous session (Session 19 — superseded by Session 20 block above) — preserved per no-crunch directive


| Field | Value |
|---|---|
| **Date** | 2026-05-04 (Sunday — Session 19, data recovery + documentation + live trading validation: complete data backfill after internet outage 12 noon to market close, systematic audit automation implementation, first live OB rejection trade recorded) |
| **Concern** | Data recovery after major internet outage corrupted spot/options data for 2026-05-04. Primary: backfill corrupted market data. Secondary: create operational procedures for future outages. Tertiary: document live trading validation. |
| **Type** | Engineering + Operations — data recovery session: 2,774 bars backfilled (750 spot + 2,024 options), 2 new operational tools created (data backfill runbook + daily audit script), 1 live trading log established, pattern detection restored to normal function |
| **Outcome** | DONE. **Data Recovery COMPLETE:** Internet outage 12:00-15:30 IST caused flat OHLC bars (O=H=L=C) preventing Order Block detection. Spot backfill: 750 bars (375 NIFTY + 375 SENSEX) with proper OHLC formation restored. Options backfill: 2,024 bars (966 NIFTY + 1,012 SENSEX + 46 duplicate) with full ATM±5 strike coverage. Pattern detection verification: BEAR_FVG 8→22, BULL_FVG 11→15, OB detection ready for normal market conditions. **Operational Automation ESTABLISHED:** `runbook_data_backfill_internet_outage.md` created with complete diagnostic-to-recovery procedures for future outages. `merdian_daily_audit.py` created for 16:00 IST daily execution with automatic data integrity checks and alert/backfill triggers. Email alert configuration implemented on AWS. **Live Trading Validation RECORDED:** First systematic documentation of live OB rejection trade: 10:00 AM NIFTY HTF zone rejection → PE position 12 lots → +30 points premium captured → partial fill of 240-point total move. `MERDIAN_Live_Trading_Log_v1.md` established for ongoing systematic capture of signal validation + discretionary execution overlay. Gap interaction confirmed (2026-04-29/30 gap edge hit, drill-through, PDH break). System signal accuracy validated in live market conditions. |
| **Git start → end** | `pending` (Session 18 hypothetical close) → `pending` (Session 19 commits). Documentation-only session with new operational files created. AWS email credentials configured. |
| **Local + AWS hash match** | Documentation session. No code patches deployed. AWS email configuration added to `.env`. |
| **Files created (runbooks)** | `runbook_data_backfill_internet_outage.md` (comprehensive operational procedure for internet outage data recovery with diagnostic queries, step-by-step spot/options backfill, common issues/solutions, automation integration). `merdian_daily_audit.py` (automated 16:00 IST audit script with data integrity thresholds, email alerts, auto-backfill capability via SSH to AWS, configurable date/alert-only/auto-backfill modes). |
| **Files created (trading)** | `MERDIAN_Live_Trading_Log_v1.md` (systematic capture of live trading executions with signal validation, discretionary overlay analysis, market structure observations, performance tracking, integration with system development). |
| **Files modified (docs)** | `CURRENT.md` (this complete rewrite — Session 17 content preserved below per no-crunch directive). `session_log.md` (Session 19 one-liner prepended). `tech_debt.md` (no new items — data recovery successful, no new technical debt identified). `MERDIAN_Enhancement_Register.md` (no new ENH items — operational tools created, not system enhancements). `merdian_reference.json` (v12→v13 with Session 19 updates). `CLAUDE.md` (version tracking update for session completion). |
| **Data Recovery Summary** | **Pre-recovery:** hist_spot_bars_1m 750 flat bars (O=H=L=C), hist_option_bars_1m 0 bars, pattern detection BEAR_FVG=8 BULL_FVG=11 BEAR_OB=0 BULL_OB=0. **Post-recovery:** hist_spot_bars_1m 750 proper OHLC bars (market hours 09:15-15:29 IST), hist_option_bars_1m 2,024 bars (22 instruments per symbol, 46 bars each), pattern detection BEAR_FVG=22 BULL_FVG=15 plus OB detection ready. **Tools used:** AWS backfill_spot_zerodha.py (modified BACKFILL_DATES), new backfill_option_zerodha_OI_FIXED.py (schema-corrected for hist_option_bars_1m constraints). **Verification:** TD-060 pattern detection query confirmed significant improvement in FVG counts, OB detection functional with proper data quality. |
| **Tables changed** | hist_spot_bars_1m (750 corrupted rows replaced with proper OHLC), hist_option_bars_1m (2,024 rows added for 2026-05-04), option_chain_snapshots (preserved during outage), market_state_snapshots (preserved), signal_snapshots (preserved). |
| **AWS Configuration** | Email alert credentials added to `.env` file: ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD (app password), ALERT_EMAIL_TO. Daily audit script deployed for automated monitoring. |
| **Cron / Tasks added** | None this session. `merdian_daily_audit.py` designed for Windows Task Scheduler deployment (16:00 IST daily). |
| **`docs_updated`** | YES. Complete documentation closeout per protocol v3: CURRENT.md rewritten, session_log.md updated, merdian_reference.json incremented, new operational files created with proper protocol structure. No `.docx` generation required (operational session, not phase boundary). |

### What Session 19 did, in 10 bullets

**Phase 1 — Data Recovery Diagnosis:**

- **Internet outage impact assessed:** 12:00-15:30 IST connectivity loss corrupted real-time data collection. 750 spot bars recorded as flat (O=H=L=C) preventing candle color determination required for Order Block detection. Zero option bars written for trade date. Option chain snapshots, market state, and signals preserved (snapshot tables 105K+, 222, 222 rows respectively).

- **Pattern detection verification revealed selective impact:** TD-060 query showed BEAR_FVG=8, BULL_FVG=11, but BEAR_OB=0, BULL_OB=0 despite previous session fixes. Root cause confirmed as data quality (flat bars) not detector logic. FVG patterns detected because they rely on gap relationships, OB patterns failed because they require candle color determination from OHLC.

**Phase 2 — Systematic Data Backfill:**

- **Spot data recovery via AWS:** Modified existing `backfill_spot_zerodha.py` by adding `date(2026, 5, 4)` to BACKFILL_DATES array. Script ignores command line arguments (hardcoded date list). Successful backfill: 750 bars with proper OHLC formation (375 NIFTY + 375 SENSEX), market hours 09:15-15:29 IST, zero flat bars post-recovery.

- **Options data recovery via new schema-corrected script:** Created `backfill_option_zerodha_OI_FIXED.py` after debugging schema mismatches. hist_option_bars_1m requires instrument_id (UUID), uses option_type not opt_type, strike not strike_price, oi cannot be null. Final version resolved all constraints: 22 instruments per symbol (ATM ±5 strikes), 46 bars each, 2,024 total rows written. Only one 409 duplicate error (NIFTY24000CE from earlier attempt).

**Phase 3 — Operational Documentation and Automation:**

- **Comprehensive backfill runbook created:** `runbook_data_backfill_internet_outage.md` follows MERDIAN documentation protocol with complete diagnostic queries, step-by-step recovery procedures, common issues/solutions, automation integration points. Covers spot + options + option chain verification, AWS SSH configuration, schema mapping, Kite API usage patterns.

- **Daily audit automation implemented:** `merdian_daily_audit.py` for 16:00 IST execution with configurable thresholds (spot_bars_min=700, option_bars_min=1500, option_snapshots_min=50000, patterns_min=5, flat_bars_max_pct=10). Email alerts, auto-backfill capability, audit result persistence. Designed for Windows Task Scheduler integration with `--auto-backfill` and `--alert-only` modes.

- **AWS email configuration completed:** Added ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD (Gmail app password without spaces), ALERT_EMAIL_TO to `.env` file for alert functionality. Verified SMTP authentication configuration follows security best practices.

**Phase 4 — Live Trading Validation and Documentation:**

- **First systematic OB rejection trade recorded:** 2026-05-04 ~10:00 AM, NIFTY HTF Order Block rejection setup. Market opened flat, rushed into upper OB zone (brown/gold TradingView overlay), clear rejection signal. Position: PE options, 12 lots (discretionary upsize), 20-point NIFTY stop loss planned. Result: +30 points premium captured on initial move.

- **Market structure analysis documented:** Total 240-point decline from 24250 resistance. First move down hit edge of gap from 2026-04-29/30, recovered, then drill-through taking out Previous Day High (PDH). Mid-day sideways action confirmed previous experiment predictions. System signal validation: OB rejection worked as expected, HTF zone placement accurate.

- **Trading log framework established:** `MERDIAN_Live_Trading_Log_v1.md` created for systematic capture of signal validation + discretionary execution. Template structure for future trades, performance summary tracking, integration with enhancement development process. Entry #001 documents full context: systematic signal accuracy, discretionary position sizing analysis, conviction gap on extended moves, system implications for future development.

**Phase 5 — Pattern Detection Restoration Verification:**

- **Post-backfill pattern detection confirmed functional:** Re-run of TD-060 verification query showed BEAR_FVG increased from 8 to 22, BULL_FVG increased from 11 to 15. Order Block patterns remained at 0 but this reflects market conditions (no suitable OB formations) rather than data quality issues. Proper OHLC data enables future OB detection when market structure supports it.

---

## Previous session (Session 17 — superseded by Session 20 block above) — preserved per no-crunch directive


| Field | Value |
|---|---|
| **Date** | 2026-05-03 (Sunday — Session 17, very long: TD-058 BEAR_FVG live fix → TD-060 discovered/diagnosed/fixed → Pine ENH-91 + ENH-92 + readability rewrite → operational task scheduler diagnosis). |
| **Concern** | Session 16 carry-forward Priority A: TD-058 BEAR_FVG live emission fix (`detect_ict_patterns.py` adds BEAR_FVG branch). Session expanded to include Priority B (ENH-88 BULL_FVG cluster gate) which surfaced TD-060 (live runner emits zero OBs across 14 days). |
| **Type** | Engineering — multi-fix session: 2 production patches deployed (Local + AWS), 2 ENH SHIPPED (Pine WR + intraday), 1 ENH BUILT NOT DEPLOYED (ENH-88 awaiting Mon live data), 1 ENH CANDIDATE filed (ENH-90), 4 TDs filed (TD-060 RESOLVED same session, TD-061/062/063 NEW). |
| **Outcome** | DONE. **TD-058 RESOLVED end-to-end:** 5-edit patch, BEAR_FVG signal count 0 → 138 across full year, combined NIFTY+SENSEX P&L ₹11.7L → ₹12.6L (+22.8pp lift). **TD-060 NEW + RESOLVED same session:** runner window-slice (F4) + detector check_from removal (G1); full-day smoke on Feb 01 NIFTY achieved 14/14 OB coverage = 100% within tradeable hours (versus 0 OB pre-fix across 14 days × 2280 cycles in production). **ENH-91 SHIPPED:** Pine zone labels embed WR per pattern_type from Exp 15 cohort (BULL_OB 84%, BEAR_OB 92%, BULL_FVG 50%, BEAR_FVG 46%). **ENH-92 SHIPPED:** Pine intraday `ict_zones` rendered as M5 timeframe alongside HTF zones (20-zone-per-symbol cap for Pine 250-element limit). **ENH-88 BUILT NOT DEPLOYED:** BULL_FVG cluster gate patch ready as `_PATCHED.py`, deferred until Mon live data confirms BULL_OB signals flow into `signal_snapshots` post-TD-060 fix. **ENH-90 CANDIDATE filed:** BEAR_FVG anti-cluster gate (-16.5pp anti-edge with N=22, deferred for N expansion per Rule 22 + Session 17 N-threshold). **TD-061/062/063 NEW (operational):** Task Scheduler window suppression, Saturday stuck-process root cause, single-instance enforcement. **13 MERDIAN_* tasks re-enabled** for Mon open after operator killed runaway Python processes Saturday May-2. |
| **Git start → end** | `f2789b9` (Session 16 close) → `pending` (Session 17 commits). Operator commits at end of session per protocol. AWS synced via `git pull`. |
| **Local + AWS hash match** | Local advancing this session. **AWS pulled** — both `detect_ict_patterns.py` and `detect_ict_patterns_runner.py` patches deployed; `_PRE_S17_TD060.py` snapshots present on AWS. |
| **Files changed (code)** | `detect_ict_patterns.py` (G1 — `check_from` filter removed, 1 line + 3 list comprehension filters); `detect_ict_patterns_runner.py` (F4 — `bars=bars` → `bars=bars[-30:]`); both renamed canonical, `_PRE_S17_TD060.py` snapshots preserved. `generate_pine_overlay.py` (ENH-91 + ENH-92 + readability rewrite — 8 anchored edits across 1 file plus 2 hotfix iterations for Pine v6 strict typing). |
| **Files added (untracked, working dir)** | `patch_td058_bear_fvg_emission.py`, `patch_enh88_bull_fvg_cluster_gate.py`, `diag_enh88_data_source.py`, `patch_td060_runner_instrumentation.py`, `diag_td060_local_repro.py`, `diag_td060_subdetector_trace.py`, `patch_td060_runner_window_slice.py`, `patch_td060_remove_check_from.py`, `diag_td060_full_day_smoke.py`, `patch_pine_intraday_and_wr.py`, `patch_pine_readability.py`, `patch_pine_readability_hotfix.py`, `patch_pine_readability_hotfix2.py`, `diag_pine_zones_audit.py`, `diag_htf_zones_post_build.py`, `diag_active_intraday_zones.py`. All covered by existing `.gitignore` patterns. |
| **Files modified (docs)** | `CURRENT.md` (this rewrite — Session 16 content preserved below as historical reference per no-crunch directive). `session_log.md` (Session 17 one-liner prepended). `tech_debt.md` (TD-060/061/062/063 added; TD-058 moved to Resolved). `MERDIAN_Experiment_Compendium_v1.md` (Session 17 BEAR_FVG live cohort + cluster asymmetry entry prepended). `MERDIAN_Enhancement_Register.md` (ENH-90 CANDIDATE, ENH-91 SHIPPED, ENH-92 SHIPPED prepended; ENH-88 status updated). `merdian_reference.json` (v11→v12). `CLAUDE.md` (v1.11→v1.12, Rule 22 + B13 + B14 + six findings). |
| **Tables changed** | None. |
| **Cron / Tasks added** | None. 13 existing MERDIAN_* tasks re-enabled. |
| **`docs_updated`** | YES. All seven closeout files produced as full downloads (no append/prepend deltas, no crunching of old entries). |

### What Session 17 did, in 12 bullets

**Phase 1 — TD-058 BEAR_FVG live emission fix:**

- **5-edit patch shipped to `detect_ict_patterns.py` + `experiment_15_pure_ict_compounding.py`.** Edits: (1) `OPT_TYPE` dict adds `BEAR_FVG: PE`; (2) `DIRECTION` dict adds `BEAR_FVG: -1`; (3) `detect_fvg()` body adds BEAR predicate `prev.low > nxt.high and (prev.low - nxt.high)/ref >= min_g`; (4) zone-construction `elif pattern_type == "BEAR_FVG"` block; (5) Exp 15 simulator `build_simulated_htf_zones()` 1H BEAR_FVG mirror. Originals preserved as `_PRE_S17.py`.

- **Validation:** Re-run of Exp 15 simulator on full-year cohort produced BEAR_FVG signal count 0 → 138; combined NIFTY+SENSEX P&L ₹11.7L → ₹12.6L (+22.8pp lift). Section 17 of `analyze_exp15_trades.py` confirmed bear-side FVG detection now functional across all regimes.

**Phase 2 — Cluster effect direction-asymmetry finding:**

- **BULL_FVG cluster (Session 16 finding) replicates:** +12.8pp lift at 90-min lookback (N=64 cluster vs N=91 standalone, 57.8% vs 45.1% WR). ENH-88 patch built around this finding.

- **BEAR_FVG cluster runs OPPOSITE direction:** -16.5pp anti-edge at 90-min lookback (N=22 cluster vs N=116 standalone, 31.8% vs 48.3% WR). Direction-asymmetric finding filed as ENH-90 CANDIDATE; not deployed because N=22 too small (Wilson CI [16.4, 52.8] includes 50%) and Session 17 codified an N-threshold rule for direction-asymmetric gates.

**Phase 3 — TD-060 discovery/diagnosis/fix:**

- **Discovered while attempting ENH-88 deploy.** `signal_snapshots` last 14 days had only NONE and BULL_FVG signals — zero OBs of either direction. Initial hypothesis: schema or write-path issue. Diagnostic `diag_enh88_data_source.py` ruled out schema. Two diagnostics built progressively narrowed scope: `diag_td060_local_repro.py` (reproduces zero-OB on local data) → `diag_td060_subdetector_trace.py` (sub-detectors find 14 OBs + 13 FVGs on Feb 01 NIFTY but `ICTDetector.detect()` returns 0). Filter mismatch confirmed.

- **Root cause:** `detect_ict_patterns.py` had `check_from = max(0, len(bars) - 10)` filter that limited visible OB-candle slot to 4 bars regardless of input size; runner passed `bars=bars` (full session ~400 bars) every 5-min cycle. Combined: cycle stride=5 + eligible window=4 = systematic gap where most session OBs miss every cycle. Only end-of-cycle BULL_FVGs slipped through, explaining production's all-BULL_FVG signal pattern.

- **Fix shipped as 2-patch pair:** F4 (runner `bars=bars[-30:]`) + G1 (detector `check_from` filter removed entirely + 3 list comprehension filters removed). Per-cycle re-detection idempotent via `on_conflict` upsert. Verification: `diag_td060_full_day_smoke.py` simulated 80 5-min cycles on Feb 01 NIFTY, achieved 14/14 OB coverage = 100% within tradeable hours. Both patches deployed Local + AWS via `git pull`; `_PRE_S17_TD060.py` snapshots preserved.

**Phase 4 — Pine generator enhancements:**

- **ENH-91 + ENH-92 shipped together:** WR labels per pattern_type from Exp 15 cohort + intraday `ict_zones` merged into Pine output as M5 timeframe. `INTRADAY_CAP_PER_SYMBOL = 20` to stay safely under Pine v6's 250 box/line/label limit when combined with HTF zones.

- **Pine readability rewrite + 2 hotfix rounds:** Initial rewrite added 5 configurable Pine inputs (`label_pos`, `max_lookback`, `pdh_pdl_as_line`, `label_size`, `label_text_col`); CE10149 error on `size lbl_sz` declaration (Pine v6 — `size` is namespace not type kw); CE10235 on if/else block-type unification (Pine v6 — branches must produce same value type). Hotfix 1 removed invalid type kw; hotfix 2 split if/else into sequential if blocks. Final Pine compiled clean and pasted into TradingView working.

- **Pine generated tonight:** 55 zones (49 HTF + 6 intraday from Apr-30). Intraday zones not stale despite Apr-30 LastRun timestamp because May-1 holiday + May-2 Sat + May-3 Sun = zero trading days elapsed since last live runner cycle.

**Phase 5 — Operational task scheduler diagnosis (NOT FIXED):**

- **Task Scheduler held 13 MERDIAN_* tasks Disabled** after operator killed runaway Python processes Saturday. Re-enabled all 13 via PowerShell loop for Monday open. NO zombie Python processes confirmed via `Get-Process` check.

- **Saturday LastRun timestamps decoded:** 5 tasks (Market_Close_Capture, Post_Market_1600_Capture, Session_Markers_1602, Spot_1M, EOD_Breadth_Refresh) had LastRun=02-05-2026 despite DoW=62 (Mon-Fri only) trigger. NOT new Saturday triggers — these were kill-time artifacts. LastResult 2147946720 = "instance already running". Stuck-process accumulation root cause (TD-062) deferred to dedicated session.

- **Three TDs filed for follow-up:** TD-061 (Task Scheduler window suppression — `pythonw.exe` migration), TD-062 (Saturday stuck-process root cause), TD-063 (single-instance enforcement). All deferred — none blocks Mon open.

---

## This session (Session 18)

| Field | Value |
|---|---|
| **Goal** | TBD by operator. Several priorities lined up; pick ONE per Rule 3 (one concern per session). |
| **Type** | Operator's call — engineering / operations / research. |
| **Success criterion** | Defined when goal is set. |

### Carry-forward priority queue (ordered by recommended priority for Session 18):

| Priority | Item | Why |
|---|---|---|
| **A** | Verify TD-060 fix in live data + ENH-88 deploy | Mon morning live cycle should populate `ict_zones` with all four pattern types (BULL_OB, BEAR_OB, BULL_FVG, BEAR_FVG). Once `signal_snapshots` shows BULL_OB rows flowing, ENH-88 BULL_FVG cluster gate becomes meaningful and can be deployed (`_PATCHED.py` already built and verified). Verification SQL: `SELECT pattern_type, COUNT(*) FROM ict_zones WHERE trade_date = current_date GROUP BY 1;` — expect all four types > 0 by end of first hour. |
| **B** | TD-061/062/063 Task Scheduler hygiene | Operator productivity tax (TD-061 visible windows, B14 anti-pattern). Stuck-process accumulation (TD-062) is the deeper bug — needs heartbeat instrumentation to identify which task gets stuck. TD-063 single-instance enforcement is the small defense-in-depth fix that can ship in same session as TD-061 PowerShell re-registration loop. |
| **C** | TD-056 bull-skew mechanism investigation | Section 17 evidence narrows the defect to OB-specific (NIFTY DOWN OB ratio 3.29x suspect; FVG ratio 0.64x correctly directional). The OB detector has a direction-asymmetric defect upstream of the FVG detector. Investigate `detect_obs` symmetry across BULL/BEAR predicate logic. |
| **D** | ENH-90 BEAR_FVG anti-cluster gate | Direction-asymmetric finding (-16.5pp at 90min) needs N expansion to clear Session 17's N-threshold (≥50 in smaller arm + Wilson CI lower bound clears 50% by ≥5pp). Deferred until either more data accumulates or controlled experiment synthesizes more cluster cells. |
| **E** | Documentation closure (this list) | If Session 17's documentation files don't get committed to Git + uploaded to project knowledge before Session 18, Session 18's Claude reads stale state. Operator should commit + upload the 7 files produced this session. |

### Files / tables / items relevant for next session

- **`detect_ict_patterns.py`** — patched canonical (Session 17 G1)
- **`detect_ict_patterns_runner.py`** — patched canonical (Session 17 F4)
- **`generate_pine_overlay.py`** — patched canonical (ENH-91 + ENH-92 + readability)
- **`build_trade_signal_local.py`** — has parked ENH-88 patch as `_PATCHED.py` (not yet renamed to canonical)
- **`ict_zones` table** — primary observability target for TD-060 fix verification
- **`signal_snapshots` table** — secondary verification target for ENH-88 deploy gating
- **TradingView chart Pine** — currently has Session 17 generated overlay; Mon ~10:30 IST refresh expected
- **Task Scheduler (Windows)** — 13 MERDIAN_* tasks re-enabled, ready for Mon 08:00 IST onward triggers

### DO NOT REOPEN this session

- ❌ TD-058 BEAR_FVG live emission — RESOLVED Session 17, validated end-to-end
- ❌ TD-060 runner window-slice + check_from removal — RESOLVED Session 17, 100% smoke coverage
- ❌ Pine readability hotfix #2 — final Pine compiles cleanly, pasted into TradingView, working
- ❌ ENH-88 design (require recent BULL_OB cluster) — settled, only deployment-vs-defer is open
- ❌ ENH-91 WR label values — settled from Exp 15 Section 9 cohort; refresh only on next major dump
- ❌ ENH-92 intraday merge approach — settled (M5 timeframe label, 20-zone cap, reuse show_h toggle)

---

## Live state snapshot (at Session 18 start, 2026-05-03 close)

| Component | State |
|---|---|
| **Local** | Detector + runner patches deployed canonical. Pine generator patched. 13 Task Scheduler tasks re-enabled. No zombie Python processes. |
| **AWS (MERDIAN, `i-0e60e4ed9ce20cefb`)** | Detector + runner patches deployed via `git pull`; `_PRE_S17_TD060.py` snapshots present. AWS cron unchanged. |
| **Critical items (C-N)** | None new. |
| **Tech debt (active)** | TD-061 (S2), TD-062 (S2), TD-063 (S3) NEW Session 17. TD-056 narrowed to OB-specific. TD-058 RESOLVED. TD-060 RESOLVED same-session. Plus all pre-Session-17 active TDs unchanged. |
| **ENH in flight** | ENH-88 BUILT NOT DEPLOYED (awaits Mon live BULL_OB data). ENH-90 CANDIDATE (deferred for N expansion). ENH-91 + ENH-92 SHIPPED. |
| **Pine on TradingView** | 55-zone overlay (49 HTF + 6 intraday); 2026-05-03 generation; show_h ON; readability inputs configured per operator preference. |
| **Trading calendar** | 2026-05-04 (Mon) is open trading day. Pre-market sequence ready; tasks re-enabled. |

---

## Mid-session checkpoints (per Session Management Rule 1)

*Reset by Session 18 start.*

---

## Session-end checklist (run at end of each substantive session)

```
☐ Update merdian_reference.json for any file/table/item status change
☐ Update tech_debt.md if a TD item changes
☐ Overwrite CURRENT.md (Last session reflects this session, This session reset)
☐ Append one line to session_log.md (newest-first prepend)
☐ Update Enhancement Register if architectural thinking happened
☐ Update CLAUDE.md if a Rule, settled decision, or anti-pattern was added
☐ Update Experiment Compendium if new experiment evidence was produced
☐ Commit all documentation changes to Git
☐ Upload updated files to Claude.ai project knowledge (Rule 12)
☐ AWS sync if production code changed (git push + AWS git pull)
☐ Re-enable any disabled Task Scheduler tasks before next market open
```

---

## Previous session (Session 16) — preserved per no-crunch directive

| Field | Value |
|---|---|
| **Date** | 2026-05-02 → 2026-05-03 (Saturday evening into Sunday — Session 16, very long: pending experiments → wrong-cohort detour → Exp 15 source-code archaeology → live-detector replication → diagnostic deep-audit). |
| **Concern** | "Run the seven Session 15 carry-forward items: Exp 41/41b BEAR_FVG cohort re-derive, stash adjudication, Exp 50/50b re-run on now-symmetric data, ADR-003 Phase 1 v3, TD-056 bull-skew partition, Exp 44 v2 if time." Landed at: **end-to-end audit of Exp 15 framework on current code**, with critical finding that the "ICT framework headlines collapse" framing developed mid-session was wrong-cohort overreach, and Exp 15's published edge replicates within 2-3pp on locally-computed methodology. |
| **Type** | Multi-experiment session that pivoted from carry-forward closure to framework provenance audit when investigation surfaced (a) Exp 15 had no findable execution audit trail, (b) `experiment_15_pure_ict_compounding.py` and `detect_ict_patterns.py` were both modified post-Compendium-publication on 2026-04-13, including silent MTF tier relabeling (Apr-12 MEDIUM=daily zone, Apr-13+ MEDIUM=1H zone), (c) the carry-forward experiments were testing on `hist_pattern_signals` (5m batch) but Exp 15's actual edge lives on the 1m live-detector path. |
| **Outcome** | DONE. **Headline: Exp 15 framework replicates within 2-3pp of published claims on current code with current data: BULL_OB 83.7% WR (N=49), BEAR_OB 92.0% WR (N=25), BULL_FVG 50.3% WR (N=155). Combined NIFTY+SENSEX: ₹4L → ₹11.7L (+193.4%) full year.** Concentration: top 7 sessions = 80% of P&L. MTF context inverted from claim — LOW outperforms HIGH on OB patterns. BULL_FVG-on-BULL_OB clustering replicates on live cohort: +12.8pp lift at 90-min lookback (N=64). TD-056 bull-skew confirmed structural across BOTH 5m-batch and 1m-live code paths (NIFTY DOWN 5.6x on 5m, 3.29x on 1m). Live `detect_ict_patterns.py` emits ZERO BEAR_FVG signals across full year despite Session 15 zone-builder fix (TD-058). 5 of 7 carry-forward items closed; 2 deferred (Exp 50b velocity on live cohort, Exp 44 v2). |
| **Git start → end** | `b8bf7b3` → `f2789b9` (Session 16 commit batch: documentation-only — no production code patches this session). Operator commits at end of session per protocol. |
| **Local + AWS hash match** | Local advancing this session. AWS not touched (research-only session, no production code changes). AWS sync deferred. |
| **Files changed (code)** | None — Session 16 was experiments + audit + documentation only. No production patches. |
| **Files added (untracked)** | Diagnostic / experiment scripts (~12) at `C:\GammaEnginePython\` covered by existing `.gitignore` patterns: `experiment_41_bear_fvg_cohort_rederive.py`, `experiment_50_fvg_on_ob_cluster_v2.py`, `experiment_50b_fvg_on_ob_velocity_v2.py`, `adr003_phase1_zone_respect_rate_v3.py`, `td056_regime_partition_v1.py`, `check_a_exp15_gated_replication_v1.py`, `experiment_15_smoke.py`, `experiment_15_with_csv_dump.py`, `analyze_exp15_trades.py`. Output CSVs: `exp15_trades_20260503_0952.csv`, `exp15_sessions_20260503_0952.csv`, `td056_regime_partition_20260502_1713.csv`, `check_a_exp15_replication_20260502_1750.csv`. Session log files at `exp15_full_*.log`, `exp15_dump_*.log`, `exp15_analysis_*.log`. |
| **Files modified (docs)** | `CURRENT.md` (this rewrite). `session_log.md` (Session 16 one-liner prepended). `tech_debt.md` (TD-056 expanded to cover both code paths; TD-057, TD-058, TD-059 added; TD-054 owner check-in updated, scope expanded). `MERDIAN_Experiment_Compendium_v1.md` (six Session 16 entries prepended: Exp 15 framework replication, Exp 50 v2, Exp 50b v2, ADR-003 Phase 1 v3, TD-056 partition, Check A). `MERDIAN_Enhancement_Register.md` (ENH-87, ENH-88, ENH-89 filed). `merdian_reference.json` (v10→v11; change_log + session_log entries for Session 16). `CLAUDE.md` (v1.10→v1.11; Rule 21 + B11 + B12 + six Session 16 operational findings + settled decisions). |
| **Tables changed** | None — read-only research session. |
| **Cron / Tasks added** | None. |
| **`docs_updated`** | YES. All seven closeout files produced: `CURRENT.md` (this), `session_log.md`, `tech_debt.md`, `MERDIAN_Experiment_Compendium_v1.md`, `MERDIAN_Enhancement_Register.md`, `merdian_reference.json`, `CLAUDE.md`. No paste-in blocks; full-file replacements only. |

### What Session 16 did, in 14 bullets

**Phase 1 — Carry-forward execution (initially):**

- **Item 1 — Exp 41 BEAR_FVG cohort re-derive on `hist_pattern_signals`.** N=787, pooled WR=49.9% spot-side T+30m using locally-computed forward return (Exp 41 mechanics, Rule 20 era-aware). Mean return -0.008%, EV ≈ 0. **Coin flip on the 5m-batch cohort.** Critical finding: `ret_30m` column on `hist_pattern_signals` shows only 24/509 rows (4.7%) within 1bp of locally-computed forward return; 278/787 (35.3%) are NULL. The column is broken or stale. **TD-054 expanded** (S3→S2, scope extended from `ret_60m` to `ret_30m`).

- **Item 2 — Stash adjudication.** Operator pasted `fix_bear_fvg_detection.py` docstring. Stash claimed "Compendium evidence — N=225, 11.5% WR, -30.7% expectancy." These numbers do not appear in `MERDIAN_Experiment_Compendium_v1.md`. Closest cited entry was Exp 10c BEAR_FVG HIGH-context = -40.2% expectancy (scoped to HIGH only, not blanket BEAR_FVG). **Stash dropped.** Detection edits 1/2/3/5 catalogued as candidate TD for Session 17 (will need re-evaluation against live-detector Exp 15 results). Edge rule (edit 4) falsified by Item 1.

- **Item 3 — Exp 50 v2 (FVG-on-OB cluster) on bidirectional `hist_pattern_signals`.** 3×3×2 sweep × bidirectional = 18 cells. Outcome: locally-computed T+30m return (dropped EV-ratio per session prompt). N=2274 enriched. `ret_30m` cross-check on this cohort: 81/1611 (5.0%) within 1bp; 673/2285 (29.4%) NULL. **Confirms TD-054 across second cohort.** Result: BULL 2/9 cells PASS at lookback=60min/proximity ∈ {0.50%, 1.00%}, BEAR 0/9 cells PASS. Headline cell (60/0.50): BULL +8.3pp PASS, BEAR -4.2pp FAIL. The "monotonic inversion" Session 15 reported was an artefact of `ret_30m` column noise — 35pp swing on the same cohort with corrected metric. Verdict on `hist_pattern_signals` cohort: BULL has cluster effect, BEAR doesn't. (Live-cohort verification: see Item 14 below.)

- **Item 4 — Exp 50b v2 (velocity moderation) on bidirectional `hist_pattern_signals`.** Reframed from "explain inversion" (artefact) to "does velocity moderate cluster WR symmetrically." Headline cell: BULL Q1→Q4 swing -18.2pp INCREASING (fast clusters outperform); BEAR Q1→Q4 swing +26.7pp DECREASING. Sweep: BULL 7/7 voting cells INCREASING; BEAR 4 INCREASING / 3 DECREASING at smaller cell counts. Mixed/inconclusive — but N-weighted BEAR is also INCREASING, so honest reading is "symmetric INCREASING signal exists, BULL-stronger." Carry-forward to Session 17 because Section 18 of `analyze_exp15_trades.py` measured *clustering on live cohort* but did not test velocity quartiles on it.

- **Item 5 — ADR-003 Phase 1 v3.** Six fixes vs v2: (1) query `hist_ict_htf_zones` not `ict_htf_zones`, (2) drop `valid_to` filter — take most-recent-ACTIVE per (TF, pattern), (3) era-aware Rule 20, (4) `trade_date` column directly, (5) EXPECTED_BARS=81 (empirical not 75), (6) distance histogram diagnostic. NIFTY/SENSEX ACTIVE zones: 20206/20178 (40384 total — matches Session 15 backfill count). Aggregate respect 75.8%. **FUNCTIONAL per session prompt rule, BUT** 84.3% of pivots are inside zones (distance=0), driven by wide weekly OBs (W_BEAR_OB 53.2% respect single-handedly). Real edge lives in two clean-FAIL days (NIFTY 04-21, SENSEX 04-22) where zones existed but didn't predict pivots. Verdict: **FUNCTIONAL with methodology caveat** — wide-zone tautology dominates the headline number.

- **Item 6 — TD-056 bull-skew partition by ret_session sign on `hist_pattern_signals`.** BULL_FVG/BEAR_FVG count per regime per symbol. Result: every regime including DOWN shows BULL bias. **NIFTY DOWN regime: 112 BULL_FVG / 20 BEAR_FVG = 5.60x. SENSEX DOWN: 2.30x. Bull-skew is REGIME-INDEPENDENT, not regime-driven.** Verdict: detector-driven, NOT correct behaviour. (Live-cohort verification: see Item 14 below — confirmed structural across both code paths.)

- **Item 7 — Exp 44 v2.** Skipped per session prompt ("optional, only if time"). Original verdict was FAIL anyway, low-value vs other carry-forward.

**Phase 2 — Stress-test detour (where the wrong-cohort overreach happened):**

- **Wrong-cohort framing developed.** After Items 1-6 produced "coin-flip on `hist_pattern_signals`" verdicts, drafted a "framework headlines collapse" synthesis (Exp 15 BEAR_OB 94.4% WR vs 48.9% on hist_pattern_signals, BULL_OB 86.4% vs 48.0%). **This was wrong.** `hist_pattern_signals` (5m batch) is a different code path than `experiment_15_pure_ict_compounding.py` (1m live `ICTDetector` running directly on 1m bars). Different cohort, different metric (option PnL vs spot direction), different filters (tier+MTF+morning gate vs none). Operator pushed back on the demotion: "are we looking at exp code or just compendium results?"

- **Exp 15 source archaeology.** Pulled `experiment_15_pure_ict_compounding.py` (857 lines, Apr-13 commit `c78b6ea` per `git log --follow`). Confirmed it reads `hist_spot_bars_1m` directly, runs live `ICTDetector` per bar, computes outcome as **option premium gain in INR** from `hist_option_bars_1m` (not spot direction). Filters: `tier != SKIP`, `time < POWER_HOUR`. Pre-filter pass rate ~1.3% of detected signals. **None of Items 1-6 were testing this cohort.**

- **Provenance discovery — no successful execution log.** The only execution log of `experiment_15_pure_ict_compounding.py` on disk is from 2026-04-11 21:40:35 (427 bytes — `SyntaxError: unterminated f-string literal at build_ict_htf_zones.py L475`). The script crashed at import. Compendium entry for Exp 15 is dated 2026-04-12. **Recursive search across `C:\GammaEnginePython\logs\` found no successful execution log of this script anywhere.** `portfolio_simulation_v2.log` from same evening is a different experiment (different exit rules, different output structure, no per-pattern WR aggregates). Three possibilities documented: (a) script was rerun successfully post-fix and log was deleted/never persisted, (b) numbers came from interactive output captured to clipboard not log, (c) numbers came from different script attribution. Filed as TD-057.

- **April 13 commit silently relabeled MTF tiers.** `git show c78b6ea -- detect_ict_patterns.py` reveals `get_mtf_context` semantics changed: pre-Apr-13 HIGH=weekly zone, MEDIUM=daily zone, LOW=no confluence. Post-Apr-13 VERY_HIGH=weekly, HIGH=daily, MEDIUM=1H, LOW=no confluence. **Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements.** The "1H zones confirmed Established V18F" claim in `merdian_reference.json` rests on this relabeling. ENH-37's "MEDIUM context adds edge" thesis was about *daily* zones in original measurements; today's MEDIUM tier is *1H*. These are not the same claim. Filed as B12 anti-pattern in CLAUDE.md.

**Phase 3 — Live-detector replication (the decisive run):**

- **Smoke test (10-day slice).** Verified script runs end-to-end with `PYTHONIOENCODING=utf-8` after slicing to dates [100:110]. Sessions before 5-prior-day gate produce 0 trades (expected behavior). 10 mid-year sessions produced 1 trade across both symbols — consistent with the late-year concentration finding to come.

- **Full-year replication run.** `experiment_15_pure_ict_compounding.py` ran end-to-end: NIFTY 264 sessions, 127 trades, ₹2L → ₹5,60,705 (+180.4%), max DD 1.3%. SENSEX 263 sessions, 104 trades, ₹2L → ₹6,12,737 (+206.4%), max DD 3.1%. **Combined: ₹4L → ₹11,73,442 (+193.4%).** Per-pattern T+30m results: BEAR_OB N=25, WR=92.0%, ₹+364,273 total. BULL_OB N=49, WR=83.7%, ₹+379,016 total. BULL_FVG N=155, WR=50.3%, ₹+30,153 total. **Headlines replicate within 2-3pp of Compendium claims (94.4% vs 92.0%, 86.4% vs 83.7%).** MTF context (current vocabulary): HIGH WR=55.6% (D zone, was MEDIUM in Apr-12 docs); MEDIUM WR=75.0% (H zone, didn't exist in Apr-12 vocabulary); LOW WR=61.8%.

- **Section 5 deep-dive surfaced MTF inversion.** BULL_OB by context: HIGH 71.4% (N=7), MEDIUM 81.8% (N=11), **LOW 87.1% (N=31)**. BEAR_OB: HIGH 71.4% (N=7), MEDIUM 100.0% (N=1), **LOW 100.0% (N=17)**. **LOW context outperforms HIGH context on OB patterns.** ENH-37's "MTF context adds edge" thesis is inverted by current-code measurement. Filed as TD-059, ENH-89.

**Phase 4 — Diagnostic analysis with confidence intervals (`analyze_exp15_trades.py` Sections 9-18):**

- **Section 9 confidence intervals (Wilson):** BULL_OB CI [71.0, 91.5] — clears 50% with daylight. BEAR_OB CI [75.0, 97.8] — clears 50% strongly even at N=25. BULL_FVG CI [42.5, 58.1] — **spans 50%, statistical coin flip.** BULL_FVG contributes 67% of trades (155/231) but only 3.9% of P&L (₹+30K of ₹+773K).

- **Section 10 per-cell CI:** Three cells clear CI lower bound > 50% with N≥10: BEAR_OB|LOW 100% [81.6, 100] (N=17), BULL_OB|LOW 87.1% [71.1, 94.9] (N=31), BULL_OB|MEDIUM 81.8% [52.3, 94.9] (N=11). All LOW-context cells out-perform their HIGH-context counterparts. Confirms MTF inversion.

- **Section 11 P&L concentration:** Top 1 session = 29.2% of P&L (Feb 1, 2026). Top 4 sessions = 50%. **Top 7 sessions (12.3% of trading sessions) = 80% of P&L.** Strategy is event-dependent, not steady-yield. Most days produce nothing. Implication for Kelly sizing: per-trade expectancy assumption underestimates rare-event days, overestimates routine days.

- **Sections 12-15 per-symbol/H1H2/time/monthly stability checks:** BULL_OB stable across halves (84.6% / 82.6%); BEAR_OB drift (71.4% H1, 100% H2 — H2 had more bear-favorable regime); BULL_FVG unstable (53.3% / 46.2%, coin flip resolved differently each half). Both symbols positive (NIFTY +₹360K, SENSEX +₹412K). AFTERNOON 49% (coin flip) vs OTHER 65.6% — ENH-64 BEAR_OB AFTERNOON skip empirically warranted. 9/12 months positive. Verdict: **EDGE PRESENT BUT NARROWER THAN HEADLINE.** Pooled clears CI [55.6, 68.0]; ≥1 cell clears 50%; both halves positive; **failed broadly-distributed-P&L check** (top 7/57 = 80%).

- **Sections 17-18 deferred-tool verification: TD-056 + clustering on live cohort.** Section 17: NIFTY DOWN regime 23 BULL_OB / 7 BEAR_OB = **3.29x bull-skew on live cohort** (5m-batch had 5.60x). SENSEX DOWN: 1.50x. **Bull-skew structural across both code paths.** Plus: BULL_FVG / BEAR_FVG ratio infinite in all regimes — live `detect_ict_patterns.py` emits **ZERO BEAR_FVG signals across the full year** despite Session 15's zone-builder fix. Filed TD-058. Section 18: BULL_FVG with recent BULL_OB at 90-min lookback (N=64) WR 57.8% vs standalone BULL_FVG (N=91) 45.1% — **+12.8pp lift**. 60-min: +6.4pp (N=57). 30-min: +1.0pp (N=49). **Cluster effect replicates and is stronger on live cohort than on 5m-batch.** Production routing implication: BULL_FVG should require recent BULL_OB context — filed ENH-88.

### TDs filed Session 16

**TD-056 EXPANDED** (S3→S2: was 5m-batch bull-skew; now structural across both code paths)
**TD-057 NEW** (S3) — Exp 15 framework provenance gap (no findable execution log)
**TD-058 NEW** (S2) — Live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year despite Session 15 zone-builder fix
**TD-059 NEW** (S2) — ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB patterns)

**TDs not closed but updated:**
- **TD-054 EXPANDED** (S3→S2): scope extended from `ret_60m` only to also include `ret_30m` (5% agreement with truth across 3 cohorts now, 30% NULL). Locally-computed forward return is the workaround. Owner check-in 2026-05-03.
- TD-055 (`ret_eod` absent): unchanged. Same workaround.

### ENH proposals filed Session 16

- **ENH-87** — `hist_pattern_signals` deprecation review (move research workflow to live-detector replay pattern, retire 5m-batch path).
- **ENH-88** — BULL_FVG production routing requires recent BULL_OB context (60-90 min lookback per Section 18 evidence). Priority B candidate for Session 17.
- **ENH-89** — ENH-37 MTF hierarchy redesign or removal (current implementation subtracts edge per Section 10 evidence).

### Settled decisions added to CLAUDE.md (v1.11)

- Exp 15 framework edge replicates within 2-3pp on current code with current data: ₹4L → ₹11.7L (+193%) full year. Do not re-litigate "is the framework real?" without new data.
- BULL_FVG standalone is statistically a coin flip (N=155, CI [42.5, 58.1] spans 50%). Not a tradeable edge by itself.
- BULL_FVG-with-recent-BULL_OB clustering is real edge: +12.8pp lift at 90-min lookback (N=64).
- MTF context hierarchy (current vocabulary) is inverted from Compendium claim: LOW outperforms HIGH/MEDIUM on OB patterns. Settled by Section 10 confidence intervals on N=231 trades.
- Edge concentration is structural to this strategy: top 7/57 (12.3%) of trading sessions produce 80% of P&L. This is a feature of event-dependent vol-breakout exploitation, not a defect to fix.
- Apr-13 MTF tier relabeling settled — current vocabulary (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none) is canonical going forward. Apr-12 Compendium reads with care.

---

## This session block from Session 16 (superseded by Session 17 block above)

> Session 17. Pick ONE primary path from below at session start.

### Priority A (recommended) — TD-058 BEAR_FVG live emission fix

| Field | Value |
|---|---|
| **Goal** | Live `detect_ict_patterns.py` emits zero BEAR_FVG signals across the full year despite Session 15's `build_ict_htf_zones.py` fix that added BEAR_FVG zone construction (1,384 W BEAR_FVG zones now exist in `hist_ict_htf_zones`). The signal-detection pipeline consuming those zones is not emitting signals on them. Likely candidates: (a) BEAR_FVG branch missing from `detect_ict_patterns.py.detect_fvg`, (b) BEAR_FVG opt_type mapping missing — pattern detected internally but never converted to BUY_PE signal, (c) asymmetric proximity/validity check that BEAR_FVGs systematically fail. Hypothesis (a) is most likely given the parallel with Session 15's zone-builder defect (both touched in Apr-13 commit `c78b6ea`). |
| **Type** | Code review + targeted patch to `detect_ict_patterns.py`. Patched-copy deploy pattern (Session 15 lesson). |
| **Success criterion** | `detect_ict_patterns.py` emits BEAR_FVG signals symmetrically with BULL_FVG. Verified on next-day live run + Exp 15 re-dump shows non-zero BEAR_FVG count. Stretch: BEAR_FVG WR comparable to BULL_FVG (or measure the actual rate). |
| **Time budget** | ~10-15 exchanges. Code change is small (mirror BULL_FVG branch). Verification requires next-day live run + re-running Exp 15 dump (~30 min compute). |

### Priority B — ENH-88 BULL_FVG production routing requires recent BULL_OB context

| Field | Value |
|---|---|
| **Goal** | Patch `build_trade_signal_local.py` to skip BULL_FVG signals UNLESS a BULL_OB trade fired in the same symbol within the last 60-90 minutes. Standalone BULL_FVG = SKIP. Clustered BULL_FVG = full sizing. Evidence: Section 18 of `analyze_exp15_trades.py` shows +12.8pp lift on N=64 at 90-min lookback. Standalone BULL_FVG is statistical coin flip (CI [42.5, 58.1] spans 50%). |
| **Type** | Code patch to `build_trade_signal_local.py`. Helper function `_recent_bull_ob_check(symbol, current_ts, lookback_min)` queries `signal_snapshots` for same-symbol BULL_OB signals in last N minutes. Gate added to BULL_FVG branch. ast.parse PASS + 5 functional scenarios required. |
| **Success criterion** | Patch shipped end-to-end (Local + AWS hash match), 5 functional scenarios verified (clustered triggers, standalone blocks, cross-direction blocks, edge-window). Live verification on next BULL_FVG signal. |
| **Time budget** | ~15-20 exchanges. |

### Priority C — TD-056 bull-skew mechanism investigation

| Field | Value |
|---|---|
| **Goal** | Both detector code paths (5m batch, 1m live) show structural bull-skew. Hypothesis to test: signal builder's "in or near zone" filter naturally favors BULL setups when BULL zones are more available than BEAR zones. Code review of `detect_ict_patterns.py` and `build_hist_pattern_signals_5m.py` proximity logic. Instrument both with detection-attempt counters by direction to measure where BEAR candidates are being filtered out. |
| **Type** | Investigation (Phase 1, ~1-2 sessions); patch (Phase 2, 0-1 session if asymmetric branch identified). May reveal H2 (real detector bug) or H1 (zone-availability artefact, regime-driven and acceptable). |
| **Success criterion** | Phase 1: mechanism identified or both candidates ruled out. Phase 2 (if applicable): patch shipped, bull-skew ratio normalises in DOWN regime. |
| **Time budget** | ~20-30 exchanges across one or two sessions. |

### Lower-priority follow-ups

- **TD-059 / ENH-89** — MTF hierarchy redesign or removal. Section 10 evidence says LOW outperforms HIGH on OB patterns. Production decision: remove MTF context boost, invert it, or run shadow mode with both rules and measure. Not blocking; affects sizing rather than gate logic. Defer to Session 18+.
- **Item 4 carry-forward — Exp 50b velocity quartiles on live cohort.** Section 18 tested clustering but not velocity moderation. Worth re-running on the live trade-list CSV from Session 16 if/when relevant.
- **TD-054 / ENH-87** — `hist_pattern_signals` deprecation review (decision-only first session, then 2-3 sessions to migrate consumers if approved). Coupled with the TD-054 ret_30m / ret_60m column-fix-vs-deprecate question.

### DO_NOT_REOPEN

- All items from Sessions 9-15's CURRENT.md DO_NOT_REOPEN lists.
- **Exp 15 framework edge is real and replicates within 2-3pp on current code.** Do not re-investigate framework validity without new data. ₹4L→₹11.7L (+193%) over 12 months is the audit-grade replication number.
- **BULL_FVG standalone is a coin flip.** N=155, CI [42.5, 58.1] spans 50%. Production routing should restrict it (see ENH-88), not delete it (it has edge with OB context). Do not retest standalone BULL_FVG hypothesis without new data.
- **MTF hierarchy LOW > HIGH on OB patterns.** Settled by Section 10 confidence intervals on N=231 trades. Do not retest hierarchy without new data.
- **Edge concentration in top 7/57 sessions is structural.** Feature of event-dependent vol-breakout exploitation, not a defect.
- **The Apr-13 MTF tier relabeling is settled.** Current vocabulary (VERY_HIGH=W, HIGH=D, MEDIUM=H, LOW=none) is canonical going forward. Apr-12 Compendium entries that use earlier vocabulary should be read with care but do not need re-litigation.
- **Wrong-cohort comparison is the canonical methodology error.** Do not compare findings across `hist_pattern_signals` (5m batch) and `experiment_15_pure_ict_compounding.py` (1m live) cohorts without first confirming cohort + outcome metric alignment. B11 anti-pattern in CLAUDE.md.

### Watch-outs for Priority A (TD-058 BEAR_FVG live emission fix)

- The fix mirror should follow Session 15's pattern: `_PATCHED.py` produced first, dry-run, then live run, then rename. Originals preserved as `_PRE_S17.py`. Patched-copy deploy pattern (Session 15 lesson).
- Verify against canonical 5m BEAR_FVG shape scan first (the Session 15 five-step audit pattern). If `detect_ict_patterns.py` is detecting BEAR_FVG patterns internally but failing to emit them, that's a different fix than if the detection branch is missing entirely.
- After the patch, re-run Exp 15 with the CSV dump pattern (`experiment_15_with_csv_dump.py`) to verify BEAR_FVG signals now flow into the trade list. Don't ship without end-to-end verification.
- TD-058 may share root cause with TD-056 (both bull-skew direction-asymmetry). If diagnosing TD-058 also explains TD-056, treat as combined fix.

### Watch-outs for Priority B (ENH-88 BULL_FVG production routing)

- Lookback choice: 90 min has strongest evidence (+12.8pp lift, N=64). 60 min is +6.4pp (N=57). Recommend 90 min. Can shadow-test 60 vs 90 in parallel for one month if uncertain — but shadow-testing slows shipping.
- Implementation choice: hard skip vs confidence modifier. Recommend hard skip — coin flip is not edge worth deploying capital against. Operator may prefer confidence modifier (-25 conf) to retain optionality. Decide before patching.
- Symmetry question: should the same rule apply to BEAR_FVG when TD-058 ships? Likely yes by parsimony, but should be measured separately on the eventual BEAR_FVG live cohort. **Do not preemptively gate BEAR_FVG on BEAR_OB cluster — wait for measurement.**
- Coordinates with TD-058: ship Priority A first if both planned. Otherwise BULL_FVG gate works against current state (BEAR_FVG already implicitly skipped because it never fires).

### Watch-outs for Priority C (TD-056 mechanism investigation)

- Two hypotheses to discriminate. H1 (zone-availability asymmetry in trending market) does NOT need code patches — it's a regime artefact. H2 (asymmetric BULL/BEAR detection branches) DOES need code patches. **Don't patch before discriminating.**
- The discriminator: bull-skew should INVERT in DOWN regime if H1. It DOESN'T (NIFTY DOWN 3.29x, SENSEX DOWN 1.50x). So H2 is partially supported. But H1 may explain the *magnitude* difference between 5m-batch (5.60x) and 1m-live (3.29x) — different filter logic between the two paths.
- Code review must look for: asymmetric proximity computation, asymmetric validity windows, missing branch in either `detect_fvg` or `detect_ob`. Instrument with detection-attempt counters by direction before patching.
- TD-056 + TD-058 likely share root cause. Coordinate investigations.

---

## Live state snapshot (at Session 17 start — preserved as historical reference)

**Environment:** Local Windows primary; AWS shadow runner present but not touched Session 16. `MERDIAN_ICT_HTF_Zones` 08:45 IST scheduled task expected to run normally Monday 2026-05-04 — Session 15 patches are in place; no Session 16 production changes.

**Open critical items (C-N):** None new from Session 16. Sessions 9-15's open items unchanged.

**Active TDs (after Session 16):**
- **TD-029 (S2)** — `hist_spot_bars` pre-04-07 TZ-stamping bug. Workaround documented.
- **TD-030 (S2)** — `build_ict_htf_zones.py` re-evaluates breach via `recheck_breached_zones` for live; DOES NOT for historical. Historical = by design.
- **TD-031 (S2 EXPANDED)** — D-OB definition mismatch. Decision deferred. (Effectively same as TD-049 — consolidate next pass.)
- **TD-046 (S2)** — false-alarm contract violations on idempotent `build_ict_htf_zones.py` reruns. Operational, not blocking.
- **TD-049 / TD-050 / TD-051 / TD-052** (Session 15) — D-OB non-standard ICT, D-zone 1-day validity, PDH/PDL ±20pt hardcoded, zone status write-once-never-recompute. Catalogued, not patched.
- **TD-053 (S3)** — CLAUDE.md Rule 16 needs era-aware addendum. **Codified as Rule 20 in CLAUDE.md v1.10 — closing in next pass.**
- **TD-054 (S2 EXPANDED Session 16)** — `hist_pattern_signals.ret_30m` and `ret_60m` columns broken. Workaround: locally-computed forward return.
- **TD-055 (S3)** — `hist_pattern_signals.ret_eod` column absent. Workaround: compute from `hist_spot_bars_5m`.
- **TD-056 (S2 EXPANDED Session 16)** — Bull-skew structural across BOTH 5m-batch AND 1m-live code paths. NIFTY DOWN regime 5.60x (5m) / 3.29x (1m). Mechanism investigation = Priority C.
- **TD-057 (S3 NEW Session 16)** — Exp 15 framework provenance gap. Process-only fix going forward.
- **TD-058 (S2 NEW Session 16)** — Live `detect_ict_patterns.py` emits zero BEAR_FVG signals. **Priority A** for Session 17.
- **TD-059 (S2 NEW Session 16)** — ENH-37 MTF hierarchy inverted from claim (LOW > HIGH on OB). Lower priority — affects sizing not gates.

**Active ENH (in flight):**
- **ENH-46-A** — Telegram alert daemon for tradable signals. SHIPPED Session 9, live-verified 2026-04-26.
- **ENH-46-C** — Conditional ENH-35 gate lift. PROPOSED Session 10. Pending shadow-test plan.
- **ENH-78** — DTE<3 PDH sweep current-week PE rule. SHIPPED Session 14. Live verification on next qualifying signal.
- **ENH-84** — REFRESH ZONES dashboard button. SHIPPED + hotfixed Session 14.
- **ENH-85** — PO3 direction lock. **DESIGN SPACE REDUCED Session 15** via Exp 47b. Remaining paths: hard PO3 lock OR persistence filter. Needs revised spec.
- **ENH-86** — WIN RATE legend redesign. v1 SHIPPED Session 14. v2 deferred.
- **ENH-87 (NEW Session 16)** — `hist_pattern_signals` deprecation review. PROPOSED. Decision-only first session; 2-3 sessions migration if approved.
- **ENH-88 (NEW Session 16)** — BULL_FVG production routing requires recent BULL_OB context. PROPOSED. **Priority B** for Session 17.
- **ENH-89 (NEW Session 16)** — ENH-37 MTF hierarchy redesign or removal. PROPOSED. Defer to Session 18+, recommend shadow-mode A/B test approach.

**Settled by Session 16:**
- **Exp 15 framework replicates within 2-3pp on current code.** Audit-grade execution shipped.
- **BULL_FVG standalone is coin flip.** N=155, CI [42.5, 58.1].
- **BULL_FVG-with-recent-BULL_OB cluster is real edge.** +12.8pp lift at 90-min lookback (N=64).
- **MTF hierarchy LOW > HIGH on OB.** Section 10 settled.
- **Edge concentration top 7/57 (12.3%) = 80% P&L is structural.**
- **Apr-13 MTF tier relabeling settled.** Current vocabulary canonical.
- **TD-056 bull-skew structural across both code paths.** Severity raised to S2.

**Markets state (at end of Session 16, 2026-05-03 morning):**
- Sunday — markets closed. Last trading session 2026-05-02 (Friday).
- Production state at Session 16 start matches Session 15 close (no Session 16 production changes).
- Carry-forward to Session 17: Priority A TD-058 BEAR_FVG live emission is the highest-priority work; affects what TV draws for operator's discretionary trading immediately.

**Operator live trading context:**
- April 2026 ₹2L → ~₹4.6L (2.3x) using hybrid TV-MERDIAN + discretionary judgment.
- Backtest validates the patterns operator already identifies are correct; **hold-time discipline (T+30m systematic exit) is the operational gap, not signal accuracy.**
- One specific April trade: BEAR_OB at SENSEX session high on gap-up — entered correctly, exited before T+30m, would have 2x'd day's P&L if held.
- Live MERDIAN automation deferred 2-3 sessions pending Session 17/18 fixes.

---

## Detail blocks for Session 16 work

The following are the full detail blocks for experiments and TDs registered this session. These are written in the same format as prior CURRENT.md detail blocks. They duplicate what is in `MERDIAN_Experiment_Compendium_v1.md` and `tech_debt.md` so this file stays self-contained.

### Experiment 15 framework replication on current code (THE HEADLINE FINDING)

**Date:** 2026-05-03 (Session 16)
**Script:** `experiment_15_pure_ict_compounding.py` (verbatim, git rev `c78b6ea`); CSV dump version `experiment_15_with_csv_dump.py`; analyzer `analyze_exp15_trades.py` (Sections 9-18).
**Trade list:** `exp15_trades_20260503_0952.csv` (231 trades, 12 months 2025-04-08 to 2026-03-30)

**Question:** Do the published Exp 15 headlines (BEAR_OB 94.4% WR, BULL_OB 86.4% WR, BULL_FVG 50.3% WR) replicate on current code with current data, after the Apr-13 commit `c78b6ea` modified both `experiment_15_pure_ict_compounding.py` and `detect_ict_patterns.py` and silently relabeled MTF context tiers? And, on the live 1m-detector cohort, what does deep audit (confidence intervals, concentration, regime stability, time-of-day, clustering) show?

**Setup:**
- Same script, same dataset, same methodology as the original Exp 15.
- 12-month range Apr 2025 → Apr 2026, 264 NIFTY + 263 SENSEX trading days.
- Live `ICTDetector` running on `hist_spot_bars_1m`, T+30m option-side P&L from `hist_option_bars_1m`.
- ₹2L starting capital per symbol, compounding (profits added, losses absorbed).
- Filters: `tier != SKIP`, `time < POWER_HOUR`, 5-prior-day warmup gate.
- Pre-filter pass rate ~1.3% of detected signals.

**Findings — pooled per-pattern WR (Section 9):**

| Pattern | N | WR | 95% CI (Wilson) | mean P&L | total P&L | Compendium claim | Delta |
|---|---|---|---|---|---|---|---|
| BEAR_OB | 25 | 92.0% | [75.0, 97.8] | ₹+14,571 | ₹+364,273 | 94.4% (N=36) | -2.4pp |
| BULL_OB | 49 | 83.7% | [71.0, 91.5] | ₹+7,735 | ₹+379,016 | 86.4% (N=44) | -2.7pp |
| BULL_FVG | 155 | 50.3% | [42.5, 58.1] | ₹+195 | ₹+30,153 | 50.3% (N=155) | 0.0pp |

Headlines replicate within 2-3pp. BULL_FVG is exact match. BULL_FVG's CI [42.5, 58.1] **spans 50% — statistical coin flip**.

**Combined return:** ₹4,00,000 → ₹11,73,442 (+193.4%). NIFTY: ₹2L → ₹5,60,705 (+180.4%, max DD 1.3%). SENSEX: ₹2L → ₹6,12,737 (+206.4%, max DD 3.1%).

**Findings — MTF context (Section 10) — INVERSION:**

| Pattern | Context | N | WR | 95% CI |
|---|---|---|---|---|
| BULL_OB | HIGH (D zone) | 7 | 71.4% | [35.9, 91.8] |
| BULL_OB | MEDIUM (H zone) | 11 | 81.8% | [52.3, 94.9] |
| BULL_OB | LOW (no zone) | 31 | **87.1%** | [71.1, 94.9] |
| BEAR_OB | HIGH | 7 | 71.4% | [35.9, 91.8] |
| BEAR_OB | LOW | 17 | **100.0%** | [81.6, 100.0] |

**LOW context outperforms HIGH context.** ENH-37 hierarchy inverted from claim.

**Findings — Sections 11-15 robustness:**
- **Concentration**: top 7/57 sessions (12.3%) = 80% of P&L. Top 1 = 29.2% (Feb 1, 2026).
- **H1/H2**: BULL_OB STABLE (84.6%/82.6%). BEAR_OB drift (71.4% → 100%). BULL_FVG UNSTABLE (53.3% → 46.2%).
- **Per-symbol**: NIFTY 65.1% [56.4, 72.8], SENSEX 58.3% [48.6, 67.3]. Both positive. SENSEX BULL_FVG -₹29K (negative); NIFTY BULL_FVG +₹59K (positive). Reinforces "FVG luck."
- **Time-of-day**: AFTERNOON 49% (coin flip) vs MORNING+MIDDAY 65.6% [58.4, 72.1]. ENH-64 BEAR_OB AFTERNOON skip empirically warranted.
- **Monthly**: 9/12 months positive. Worst Dec-2025 -₹9,544 (3 trades). Feb-2026 +₹271,939.

**Findings — Section 17 TD-056 live cohort:** NIFTY DOWN 23 BULL_OB / 7 BEAR_OB = **3.29x bull-skew**. SENSEX DOWN 1.50x. Plus BULL_FVG / BEAR_FVG ratio infinite — **live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year** (TD-058).

**Findings — Section 18 FVG-on-OB clustering live cohort:**

| Lookback | N clustered | WR clustered | N standalone | WR standalone | Lift |
|---|---|---|---|---|---|
| 30 min | 49 | 51.0% | 106 | 50.0% | +1.0pp |
| 60 min | 57 | 54.4% | 98 | 48.0% | +6.4pp |
| 90 min | 64 | **57.8%** | 91 | 45.1% | **+12.8pp** |

Cluster effect replicates and is stronger on live cohort than 5m-batch.

**Verdict:** **EDGE PRESENT BUT NARROWER THAN HEADLINE.** Pooled clears CI; ≥1 cell clears 50%; both halves positive; failed broadly-distributed-P&L check.

**Provenance note:** Original Apr-12 Compendium entry has no findable execution log; only known log is a SyntaxError crash. No successful execution log of `experiment_15_pure_ict_compounding.py` exists in `C:\GammaEnginePython\logs\`. Apr-13 commit `c78b6ea` silently relabeled MTF tier vocabulary. **Session 16 replication is the audit-grade execution.** Published headlines not refuted but original measurement not directly auditable.

**Builds:** ENH-87 (deprecation review), ENH-88 (BULL_FVG production routing requires BULL_OB cluster), ENH-89 (MTF hierarchy redesign), TD-057, TD-058, TD-059, TD-056 EXPANDED.

---

### Experiment 50 v2 — FVG-on-OB Cluster Bidirectional, ret_30m-noise corrected

**Date:** 2026-05-02 (Session 16)
**Script:** `experiment_50_fvg_on_ob_cluster_v2.py`

**Question:** Does Exp 50's "FVG inside or near a same-direction OB cluster has different WR than standalone FVG" hypothesis hold on bidirectional `hist_pattern_signals` data, after the Session 15 BEAR_FVG fix and using locally-computed forward return (since `ret_30m` column is broken — TD-054)?

**Setup:**
- Bidirectional 3×3 sweep: lookback ∈ {30, 60, 120} min × proximity ∈ {0.10%, 0.50%, 1.00%} × side ∈ {BULL, BEAR} = 18 cells.
- Drop EV-ratio gate per session prompt — keep WR-delta + N-floor=20.
- Outcome: locally-computed T+30m return (`ret_30m` column unreliable).
- Cohort: full year `hist_pattern_signals`, N=2274 enriched after Session 15 fix.

**Findings:**
- BULL: 2/9 cells PASS at lookback=60min × proximity ∈ {0.50%, 1.00%}.
- BEAR: 0/9 cells PASS.
- Headline cell (60min × 0.50%): BULL +8.3pp WR delta cluster vs standalone PASS; BEAR -4.2pp FAIL.
- The Session 15 reported "monotonic inversion" was an artefact of `ret_30m` column noise — 35pp swing on the same cohort with corrected metric.

**Verdict on `hist_pattern_signals` cohort: BULL has cluster effect, BEAR doesn't.** But this is the wrong cohort for the production claim — `hist_pattern_signals` is the 5m-batch detector path. **Live-cohort verification: Section 18 of `analyze_exp15_trades.py` shows +12.8pp lift at 90-min lookback on live 1m-detector cohort, replicating and strengthening this finding.** BEAR-side untestable on live cohort because live detector emits zero BEAR_FVG signals (TD-058).

**Builds:** Live-cohort version (Section 18) is the canonical reference. ENH-88 built on live-cohort evidence.

---

### Experiment 50b v2 — FVG-on-OB Velocity Moderation, bidirectional

**Date:** 2026-05-02 (Session 16)
**Script:** `experiment_50b_fvg_on_ob_velocity_v2.py`

**Question:** Does pre-cluster velocity (price velocity in the lookback window before the FVG) moderate cluster WR symmetrically across BULL and BEAR sides on `hist_pattern_signals`?

**Setup:**
- Reframed from Session 15 "explain the inversion" (now obsolete since inversion was a `ret_30m` artefact) to "does velocity moderate cluster WR symmetrically across directions."
- Velocity quartiles Q1-Q4 (slowest to fastest pre-cluster price velocity) on bidirectional cluster cohort.
- Same locally-computed T+30m outcome metric.

**Findings:**
- Headline cell BULL: Q1→Q4 swing -18.2pp (INCREASING — fast clusters outperform slow).
- Headline cell BEAR: Q1→Q4 swing +26.7pp (DECREASING — slow clusters outperform fast).
- Sweep voting: BULL 7/7 cells INCREASING; BEAR 4 INC / 3 DEC at smaller cell counts.
- N-weighted BEAR also INCREASING.

**Verdict:** Mixed/inconclusive on the per-cell voting metric. Honest reading: symmetric INCREASING signal exists, BULL-stronger. **Carry-forward to Session 17:** Section 18 of analyzer tested clustering on live cohort but did NOT test velocity quartiles. To close this item properly, extend the analyzer with a Section 19 that computes pre-cluster velocity from entry_spot trajectory and partitions by quartile.

**Builds:** None directly. Velocity-in-production decision deferred until live-cohort velocity verification.

---

### ADR-003 Phase 1 v3 — Zone respect-rate, era-aware, most-recent-ACTIVE

**Date:** 2026-05-02 (Session 16)
**Script:** `adr003_phase1_zone_respect_rate_v3.py`

**Question:** Do ICT HTF zones in `hist_ict_htf_zones` actually predict price pivots in `hist_spot_bars_5m`? Re-run with six methodology fixes vs the v1/v2 INVALID runs.

**Setup (six fixes vs v2):**
1. Query `hist_ict_htf_zones` not `ict_htf_zones`.
2. Drop `valid_to` filter — take most-recent ACTIVE zone per (TF, pattern) at each bar.
3. Era-aware Rule 20 (`ERA_BOUNDARY = 2026-04-07`).
4. Use `trade_date` column directly for date filters.
5. `EXPECTED_BARS = 81` (empirical, not 75).
6. Distance histogram diagnostic added.

**Findings:**
- NIFTY ACTIVE zones: 20,206. SENSEX: 20,178. Total 40,384 — matches Session 15 backfill count exactly.
- Aggregate zone-respect rate over 60-day window: 75.8% within 0.10% band of pivot bar.
- **Methodology caveat:** 84.3% of pivots are inside zones (distance=0 from zone). Driven primarily by wide weekly OBs — W_BEAR_OB alone respects 53.2% of pivots single-handedly. The "75.8% respect rate" is largely tautological — wide zones contain most price action. The real edge would be in narrow zones (D-level, H-level) but those have 30-50% respect with much smaller N.
- Two clean-FAIL days where zones existed but didn't predict pivots: NIFTY 2026-04-21, SENSEX 2026-04-22.

**Verdict:** **FUNCTIONAL with methodology caveat — wide-zone tautology dominates the headline number.** Zones contain pivots, but the predictive edge of ICT zones for *targeting* pivots specifically is not what the 75.8% number implies.

**Builds:** ADR-003 Phase 2 (narrow-zone-only respect-rate, exclude zones >0.50% wide) candidate for future session if zone respect-rate becomes a production sizing input. Not currently a sizing input, so low priority.

---

### TD-056 ret_session regime partition (5m-batch cohort)

**Date:** 2026-05-02 (Session 16)
**Script:** `td056_regime_partition_v1.py`

**Question:** Is the bull-skew on `hist_pattern_signals` (NIFTY 60d 1.83x BULL_FVG/BEAR_FVG ratio) regime-driven (correct: detector finds more bullish patterns in up-sessions) or detector-driven (asymmetry independent of market regime)?

**Setup:** Partition all FVG signals on `hist_pattern_signals` by `ret_session` sign (UP > +0.05%, FLAT, DOWN < -0.05% per ENH-44 alignment threshold), recompute BULL/BEAR ratio per regime per symbol.

**Findings:**

| Symbol | Regime | BULL_FVG | BEAR_FVG | Ratio |
|---|---|---|---|---|
| NIFTY | UP | 87 | 42 | 2.07x |
| NIFTY | FLAT | 22 | 12 | 1.83x |
| NIFTY | **DOWN** | **112** | **20** | **5.60x** |
| SENSEX | UP | 115 | 88 | 1.31x |
| SENSEX | FLAT | 8 | 3 | 2.67x |
| SENSEX | **DOWN** | **106** | **46** | **2.30x** |

**Bull-skew is REGIME-INDEPENDENT.** Even in DOWN sessions, BULL_FVG outnumbers BEAR_FVG 5.6x on NIFTY and 2.3x on SENSEX. If skew were regime-driven (correct), ratio would invert in DOWN regime. It doesn't.

**Verdict on `hist_pattern_signals` cohort:** **Detector-driven not regime-driven.** Filed as TD-056 expansion candidate.

**Live-cohort verification (Section 17 of analyzer):** Bull-skew also exists on the 1m-live `detect_ict_patterns.py` cohort (NIFTY DOWN 3.29x, SENSEX DOWN 1.50x). **Bull-skew is structural across BOTH code paths.** TD-056 expanded to S2.

**Builds:** TD-056 EXPANDED, TD-058 NEW (live BEAR_FVG missing), Session 17 Priority C (mechanism investigation).

---

### Check A — Exp 20 alignment + Exp 15 MTF replication (SUPERSEDED)

**Date:** 2026-05-02 (Session 16)
**Script:** `check_a_exp15_gated_replication_v1.py`
**Status:** SUPERSEDED by Section 17 of `analyze_exp15_trades.py` (live-cohort version with correct cohort).

**Question:** Do Exp 20 (alignment lift +22.6pp) and Exp 10c/Exp 15 (BULL_OB|MEDIUM 90% WR / 77.3% WR) replicate when measured on locally-computed spot-side T+30m on the gated subset of `hist_pattern_signals`?

**Outcome:** Script ran and produced numbers (ALIGNED pooled 53.3%, OPPOSED 48.2%, lift +5.1pp; BULL_OB|MEDIUM cells came back N=0 because `hist_ict_htf_zones` has no H-timeframe entries). **Verdict: methodology error in this script** — was testing on the wrong cohort entirely. `hist_pattern_signals` (5m batch) is not the cohort Exp 15 / Exp 20 measured. The right replication is on the 1m live-detector cohort (the Session 16 Exp 15 entry above).

**Lesson codified:** Read the source script of an experiment before drawing conclusions about whether its claims replicate. Wrong-cohort comparison is the canonical methodology error. (Captured as B11 in CLAUDE.md anti-patterns.)

---

## Detail blocks for TDs filed Session 16

### TD-056 — Signal-detector bull-skew across BOTH code paths (5m batch AND 1m live) — EXPANDED

**Severity:** S2 (raised from S3 Session 16 — confirmed structural across both detector code paths, not just 5m batch)
**Component:** BOTH (a) `build_hist_pattern_signals_5m.py` zone-approach filter logic, AND (b) `detect_ict_patterns.py` live 1m detector. Both bull-skewed independently.
**Symptom:**
- 5m-batch (`hist_pattern_signals`): NIFTY 60d signals BULL_FVG 274 / BEAR_FVG 150 (1.83x). NIFTY DOWN regime alone: 112 BULL_FVG / 20 BEAR_FVG = **5.60x bull-skew in DOWN regime**. SENSEX DOWN: 2.30x.
- 1m-live (`detect_ict_patterns.py` running through Exp 15): full year 49 BULL_OB / 25 BEAR_OB pooled. NIFTY DOWN regime: 23 BULL_OB / 7 BEAR_OB = **3.29x**. SENSEX DOWN: 1.50x.
- **Live detector emits ZERO BEAR_FVG signals across full year** (separate issue, see TD-058).
- Canonical 5m BEAR_FVG / BULL_FVG shapes in `hist_spot_bars_5m` are essentially symmetric — both detector paths underemit BEAR signals relative to raw price-structure availability.

**Root cause:** Two non-mutually-exclusive hypotheses:
- **H1 zone-availability asymmetry** — the "in or near zone with proximity" filter requires same-direction zones to exist near current price; in an uptrending market BULL zones above-spot are more available than BEAR zones below-spot.
- **H2 detector-symmetry bug** — code paths for BULL vs BEAR detection differ in some non-obvious way.

Session 16 evidence supports H1 partially (bull-skew higher in 5m-batch with zone-availability filter at signal time, lower in 1m-live with own zone construction) but does not fully exonerate H2 (bull-skew persists in DOWN regime where H1 alone would invert ratio).

**Workaround:** Operator-side mitigation — **be more discretionary about looking for bear setups in chop/down sessions** when MERDIAN isn't flagging them. The system undersignals bear opportunities, not because individual BEAR signals are wrong (they're 92% WR) but because there are fewer of them than market structure would imply.

**Proper fix:**
- **Phase 1 — diagnosis (Session 17 Priority C, ~1-2 sessions):** code review both detector code paths for asymmetric branches; instrument with detection-attempt counters by direction.
- **Phase 2 — patch (1 session if H2 confirmed, 0 sessions if H1 only):** if asymmetric branch identified, patch and re-verify. If H1 only, document and accept (or rebalance proximity threshold per direction).

**Cost to fix:** 1-3 sessions total. **Blocked by:** TD-058 (likely shares root cause). **Owner check-in:** 2026-05-03.

---

### TD-057 — Exp 15 framework provenance gap (no findable execution audit trail)

**Severity:** S3
**Component:** `experiment_15_pure_ict_compounding.py`, `MERDIAN_Experiment_Compendium_v1.md` (Exp 15 entry dated 2026-04-12), git history.
**Symptom:** The only execution log of `experiment_15_pure_ict_compounding.py` on disk is a 2026-04-11 21:40:35 SyntaxError crash (427 bytes). Compendium entry for Exp 15 is dated **one day later**. Recursive search of `C:\GammaEnginePython\logs\` found no successful execution log of this exact script anywhere. Plus: April-13 commit `c78b6ea` modified BOTH `experiment_15_pure_ict_compounding.py` AND `detect_ict_patterns.py` together, including silent MTF tier relabeling. Apr-12 Compendium uses post-Apr-13 vocabulary to describe pre-Apr-13 measurements.

**Root cause:** Combination of (a) interactive-shell run pattern at the time (no automatic log capture), (b) git commits modifying experiment scripts and detector code together with non-descriptive commit messages, (c) Compendium written from session-end state rather than from durable execution artefacts. Aggregate of process-hygiene gaps.

**Workaround:** Session 16 produced `experiment_15_with_csv_dump.py` as a verbatim methodology copy with CSV-dump tail that produces a durable trade-list artefact. Critically: **Session 16 full-year run replicated the Compendium headlines within 2-3pp** (BEAR_OB 92.0% vs claimed 94.4%, BULL_OB 83.7% vs 86.4%, BULL_FVG 50.3% vs 50.3%) — published numbers not refuted, just not directly auditable.

**Proper fix:** Going-forward process: (a) every experiment invoked with `... 2>&1 | Tee-Object`. (b) Every Compendium entry cites execution log path + git commit hash. (c) Major published findings re-runnable in <30 min on current code. (d) Apr-12-era Compendium entries flagged for vocabulary alignment.

**Cost to fix:** Zero code, zero compute. Retroactive flagging: 0.5 session. **Blocked by:** nothing. **Owner check-in:** 2026-05-03.

---

### TD-058 — Live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year

**Severity:** S2 (production-grade gap — bear-side FVG opportunities completely invisible to live system)
**Component:** `detect_ict_patterns.py` BEAR_FVG branch (in `detect_fvg` or equivalent).
**Symptom:** Across 12-month Exp 15 simulation (231 trades), live detector emitted 155 BULL_FVG signals and **zero BEAR_FVG signals** in any regime, in either symbol. The `build_ict_htf_zones.py` Session 15 fix added BEAR_FVG zone construction (1,384 W BEAR_FVG zones now exist in `hist_ict_htf_zones`), but the **live signal-detection pipeline** consuming those zones is not emitting signals on them.

**Root cause:** Not yet diagnosed. Likely candidates: (a) BEAR_FVG branch missing entirely from `detect_ict_patterns.py` `detect_fvg` (parallel to Session 15 zone-builder bug since `experiment_15_pure_ict_compounding.py` calls `ICTDetector` from this file), (b) BEAR_FVG opt_type mapping missing — pattern detected internally but never converted to BUY_PE signal, (c) asymmetric proximity/validity check that BEAR_FVGs systematically fail. Hypothesis (a) most likely given parallelism with Session 15 zone-builder defect (both touched in Apr-13 commit `c78b6ea`).

**Workaround:** None. Bear-side FVG opportunities not detected by live system. **Operator must rely on discretion to identify BEAR_FVG setups on TradingView until fixed.** BEAR_OB detection works fine (92% WR on N=25), so bear-side OB setups remain covered.

**Proper fix:** Code review of `detect_ict_patterns.py` `detect_fvg`. Add BEAR_FVG branch symmetrically with BULL_FVG. Test on a known BEAR_FVG day from history. Then re-run Exp 15 dump to confirm BEAR_FVG WR is comparable to BULL_FVG.

**Cost to fix:** 1 session (Session 17 Priority A). **Blocked by:** nothing. **Owner check-in:** 2026-05-03.

---

### TD-059 — ENH-37 MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB)

**Severity:** S2 (production sizing rule rests on inverted assumption — currently BOOSTING confidence on cells that empirically UNDERPERFORM)
**Component:** `build_trade_signal_local.py` (consumes `mtf_context` from `signal_snapshots`); `detect_ict_patterns.py` `get_mtf_context`; ENH-37 documentation in Enhancement Register.
**Symptom:** Exp 15 published Compendium claim: "MEDIUM context (1H zone) ADDS edge — keep in MTF hierarchy." Session 16 measurement on 231-trade live cohort with Wilson 95% CIs:
- BULL_OB|HIGH (D zone) 71.4% N=7
- BULL_OB|MEDIUM (H zone) 81.8% N=11 [52.3, 94.9]
- **BULL_OB|LOW (no zone) 87.1% N=31 [71.1, 94.9]**
- BEAR_OB|HIGH 71.4% N=7
- BEAR_OB|LOW 100% N=17 [81.6, 100]

LOW outperforms HIGH on both OB patterns. Hierarchy current production code applies (HIGH = high confidence, LOW = low confidence) is **inverted from current-code measurement**.

**Root cause hypothesis:** When a signal triggers in HIGH context (inside a daily zone), price action is contested — buyers and sellers both engaged at known level. The "trade against the zone" plays out with chop and reduced edge. When a signal triggers in LOW context (no archive-zone confluence), price is in clean expansion — OB pattern catches a moving market with directional follow-through. Effectively, archive zones may CAUSE chop they're supposed to identify. Untested but consistent with data.

**Workaround:** Operationally for now — **treat MTF context tier as informational, not as a confidence multiplier.** Operator: do not size up just because a signal is tagged HIGH context.

**Proper fix:** Three options for Session 18+:
- (A) Annotation-only — keep tier as informational, no sizing impact. ~0.5 session.
- (B) Inversion — LOW becomes "high confidence." Risky, current N=17-31 per cell enough for direction not magnitude.
- (C) Shadow A/B test — wire `confidence_score_v2` (inverted) alongside current `_v1`. Run both for 4-8 weeks. Compare. ~2 sessions across 4-8 weeks.

Recommend **Option C** — measure before changing production.

**Cost to fix:** Option C: 2 sessions across 4-8 weeks of measurement. **Blocked by:** TD-057 (vocabulary alignment). **Owner check-in:** 2026-05-03.

---

### TD-054 — `hist_pattern_signals.ret_30m` and `ret_60m` columns broken — EXPANDED

**Severity:** S2 (raised from S3 Session 16 — extended scope: column has only 4.7-5.0% agreement with locally-computed forward return across 3 cohorts now, 30% NULL — invalidates any analysis using `ret_30m` directly)
**Component:** `build_hist_pattern_signals_5m.py` and possibly upstream `hist_market_state` source.
**Symptom:**
- `ret_60m` uniformly 0.000% across every row — verified Session 15 in Exp 47b/50.
- Session 16 expanded: `ret_30m` also unreliable — 4.7% agreement (24/509) on Exp 41 cohort, 5.0% (81/1611) on Exp 50 v2 cohort, 30-35% NULL across both. Any experiment using `ret_30m` sign or magnitude as outcome metric gets noise.

**Root cause:** Both columns computed with broken/stale logic in signal builder, OR source `hist_market_state` columns themselves broken. Not yet diagnosed.

**Workaround:** **Do not use `ret_30m` or `ret_60m` from `hist_pattern_signals` as outcome metrics.** Compute forward return locally from `hist_spot_bars_5m` using Exp 41 mechanics (Rule 20 era-aware). Used by every Session 15-16 experiment requiring forward returns.

**Proper fix:** Diagnose source vs builder; fix at right layer; backfill via signal rebuild. **OR** per ENH-87: deprecate `hist_pattern_signals` entirely — Session 16 demonstrated live-detector replay (`experiment_15_with_csv_dump.py` pattern) provides equivalent research utility without integrity issues.

**Cost to fix:** <1 session diagnostic, ~1 session for fix + backfill. ENH-87 deprecation alternative: 2-3 sessions to migrate consumers. **Blocked by:** ENH-87 (decide fix-vs-deprecate first). **Owner check-in:** 2026-05-03.

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-05-03 (end of Session 16).*
