# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v4 — V18C-Updated — April 2026 |
| Source documents | GammaEngine V15.1 · V16 · V17 · V17A–V17E · V18 v2 · V18A v4 · V18A-2 · V18B · V18C · Enhancement Plan |
| Current latest appendix | V18C (Infrastructure Upgrade · Historical Data Ingest · 2026-04-03/04) |
| Authority | This document aggregates and does not supersede any master. V16 wins on architecture. V17 wins on post-V16 development facts. V18 wins on post-V17 facts. |

### V18C Session Changes (2026-04-04)

**Closed this session:** V18A-01, OI-03, C-01, C-02, C-04, C-05, C-06, C-08, A-03, A-04, E-03, D-09/E-06, S-01/S-02, S-03, S-05, S-06, S-07, S-08, M-01, Group 3 steps 3.1–3.4 and 3.6, Group 4 items 4.1/4.3/4.6.

**Key fixes:** Token refresh race condition fixed via Supabase sync. AWS Python 3.10 EOD compatibility fix. India VIX signal rules added to shadow engine. Watchdog rebuilt. Supervisor task swap (legacy launcher disabled). Table freshness checks added to telemetry logger. 13 shadow table DDLs documented. Scheduler ownership manifest created. Token refresh timing corrected to 08:15 IST per Change Protocol.

**Shadow gate status:** 4/10 sessions complete. Gate opens after ~6 more clean sessions (~2 weeks from 2026-04-07).

---

## Section 1 — Critical Fixes

### C-01 — market_state_snapshots duplication
**Status:** ✅ CLOSED (V18A)
ALTER TABLE ADD CONSTRAINT uq_market_state_symbol_ts UNIQUE (symbol, ts). UPSERT logic confirmed. Zero duplicate rows.

### C-02 — Re-ingest 2026-03-24 EOD data
**Status:** ✅ CLOSED (V18A)
99.35% coverage confirmed (1376/1385 rows). Remaining 9 are systematic DH-905 failures on every date — not a re-ingest gap.

### C-03 — SENSEX WCB staleness
**Status:** ⏳ PENDING — confirm on next live session (2026-04-07)
Per-symbol loop fix in Git at d6cb60e. Run diagnostic query on first live session:
```sql
SELECT index_symbol, MAX(ts) AS latest_ts, NOW() - MAX(ts) AS lag
FROM weighted_constituent_breadth_snapshots
GROUP BY index_symbol;
```
Expected: lag < 10 minutes during live hours.

### C-04 — Breadth staleness
**Status:** ✅ CLOSED (V18C session)
`universe_count = 1385` confirmed. Guard 4 (20-min staleness stop) active.

### C-05 — build_trade_signal_local.py 240-sec timeout
**Status:** ✅ CLOSED (V18A)
Root cause was momentum duplicate key crash during crash loop race condition, not signal timeout. CalendarSkip fix eliminates crash loop. Confirmed no errors in last live session log (2026-04-02).

### C-06 — EOD coverage gap 13–24 March
**Status:** ✅ CLOSED (V18C session)
All dates 2026-03-15 through 2026-03-24 confirmed at 99.85–100.07%. Nothing needs re-ingestion.

### C-07a — AWS premarket timestamp/query mismatch
**Status:** ⏳ PENDING — confirm on next live session
Run in Supabase SQL editor during 09:00–09:20 IST window:
```sql
SELECT symbol, ts AT TIME ZONE 'Asia/Kolkata' AS ts_ist, spot
FROM market_spot_snapshots
WHERE ts AT TIME ZONE 'Asia/Kolkata' BETWEEN 'YYYY-MM-DD 09:00:00' AND 'YYYY-MM-DD 09:20:00'
ORDER BY ts;
```

### C-07b — Local PREMARKET pipeline recording validation
**Status:** ⏳ PENDING — confirm on next live session
Validate rows written to market_spot_session_markers during 09:00–09:14 window.

### C-08 — Intermittent SENSEX volatility RuntimeError
**Status:** ✅ CLOSED (V18A)
compute_volatility_metrics_local.py line 474 fixed: `first.get("ts") or first.get("created_at")`.

---

## Section 2 — Local Production Hardening

### S-01/S-02 — Scheduler ownership fix
**Status:** ✅ CLOSED (V18C session)
`MERDIAN_Intraday_Session_Start` disabled permanently. `MERDIAN_Intraday_Supervisor_Start` enabled. Supervisor is sole owner of runner startup.

### S-03 — MERDIAN_State_Stack_5M
**Status:** ✅ CLOSED (V18C session)
Task does not exist — already fully removed at some prior point. Retired.

### S-04 — 15:10/15:11 late-session stop
**Status:** ⏳ PENDING — monitor next 3 live sessions
Root hypothesis: duplicate launcher causing race condition. S-01/S-02 fix should resolve. Monitor from 2026-04-07.

### S-05 — Supervisor data-freshness awareness
**Status:** ✅ CLOSED (V18C session)
`check_table_freshness()` added to `gamma_engine_telemetry_logger.py`. Queries 4 core tables (signal_snapshots, market_state_snapshots, gamma_metrics, volatility_snapshots). Stale threshold: 10 minutes. Any stale table elevates event_level to WARN. Committed at 333d725.

### S-06 — Lock-file cleanup on abnormal exit
**Status:** ✅ CLOSED (V18C session)
Already fully built in run_option_snapshot_intraday_runner.py. `atexit.register(release_lock)` + SIGINT/SIGTERM handlers + stale lock reclaim in `acquire_lock()`. LOCK_STALE_SECONDS=900, LOCK_HEARTBEAT_UPDATE_SECONDS=15.

### S-07 — Watchdog implementation
**Status:** ✅ CLOSED (V18C session)
`watchdog_check.ps1` rebuilt. Checks if `gamma_engine_supervisor` process is alive. Only acts during market hours (09:00–15:35 IST) on confirmed trading days (trading_calendar guard). Fires Telegram alert before restarting. MERDIAN_Watchdog task enabled with -WindowStyle Hidden. Committed at 3ec6212.

### S-08 — Scheduler ownership manifest
**Status:** ✅ CLOSED (V18C session)
`docs/MERDIAN_Scheduler_Manifest.md` created. Documents all 10 tasks with owner, trigger, script, purpose. Committed at 915c85a. Updated to 08:15 IST token refresh timing.

### S-09 — Token refresh timing
**Status:** ✅ CLOSED (V18C session)
Local task moved from 09:05 to 08:15 IST per Change Protocol Rule 6. AWS pull moved from 03:40 to 03:55 UTC (08:25 IST). Correct cadence: Local refresh 08:15 → AWS pull 08:25 → Preflight 08:30.

### M-01 — POSTMARKET session state
**Status:** ✅ CLOSED (V18C session)
Already fully built in `trading_calendar.py`. States: CLOSE_REF_DUE, POST_CLOSE_WAIT, POSTMARKET_REF_DUE, POSTMARKET_COMPLETE. Helper functions `is_close_ref_due()`, `is_postmarket_ref_due()` present.

### M-02 — PREMARKET recording validation
**Status:** ⏳ PENDING — requires live session between 09:00–09:14 IST
Validate rows written to market_spot_session_markers during PREMARKET window.

---

## Section 3 — V18A Open Items

### V18A-01 — Windows token task unattended proof
**Status:** ✅ CLOSED (V18C session)
Root cause found: both Local and AWS were calling Dhan API simultaneously causing "Token can be generated once every 2 minutes" error. Fix: AWS cron token refresh removed. Local writes token to `system_config.dhan_api_token` in Supabase after refresh. AWS pulls via `pull_token_from_supabase.py`. Token timing corrected to 08:15 IST (Local) / 08:25 IST (AWS). Committed at 23f1cf4.

### V18A-02 — Runner circuit-breaker
**Status:** ✅ CLOSED (V18A)
`_is_auth_failure()` and `_send_circuit_breaker_alert()` in run_option_snapshot_intraday_runner.py. 401 detection halts gamma/state/signal, fires Telegram OPTION_AUTH_BREAK alert.

### V18A-03 — trading_calendar row maintenance
**Status:** ✅ CLOSED (V18A)
CalendarSkip exits code 0 on holiday. Preflight Stage 2 checks week-ahead calendar rows. Rows confirmed for 2026-04-07 through 2026-04-10 (is_open=true).

---

## Section 4 — AWS Readiness

### A-01 — AWS 4-guard system
**Status:** ✅ CLOSED (V18A)
All 4 guards confirmed in run_merdian_shadow_runner.py at lines 388, 403, 415, 431.

### A-02 — AWS 4:00 PM weighted-average close
**Status:** ✅ CLOSED (V18C session)
`capture_postmarket_1600.py` exists and is wired into AWS cron at 10:30 UTC (16:00 IST). Calls `run_market_close_capture_once.py`.

### A-03 — Dhan auth stability
**Status:** ✅ CLOSED (V18C session)
See V18A-01. Race condition resolved via Supabase token sync. AWS no longer calls Dhan API for token refresh.

### A-04 — AWS EOD ingestion end-to-end
**Status:** ✅ CLOSED (V18C session)
Python 3.10 compatibility fix applied to `ingest_equity_eod_local.py`. `datetime.UTC` replaced with `timezone.utc` alias. EOD ingestion confirmed working (149 candles per ticker). Committed at 61a6613.

### A-05 — Local vs AWS parity comparison
**Status:** ⏳ PENDING — requires live session
Run both pipelines simultaneously and compare signal outputs for same timestamp.

### A-06 — Telegram crash-alert on AWS runner
**Status:** ✅ CLOSED (V18C session)
Already built. `send_fatal_telegram()` at line 144, called at line 743 on fatal crash. TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID loaded from .env.

### A-07 — AWS git credential caching
**Status:** ✅ CLOSED (V18C session)
`git config --global credential.helper store` configured. Git identity set (balannavin-cyber).

---

## Section 5 — Historical Ingest (from V18C)

### OI-01 — SENSEX 2025 individual futures replay
**Status:** ⏳ OPEN (medium priority)
49,635 rows rejected pre-fix. Replay by deleting BFO_CONTRACT_*2025 log entries and re-running `--year 2025`. Individual futures now parse correctly with INDIVIDUAL_FUTURES_PATTERN.

### OI-02 — Vendor correction MAY/JUN 2025, JAN 2026
**Status:** ⏳ WAITING on vendor
Email sent. Await resend of correct SENSEX F+O contractwise files. No code changes needed on receipt.

### OI-03 — MERDIAN_Market_Tape_1M task disabled
**Status:** ✅ CLOSED (V18C session)
Re-enabled. Token conflict concern confirmed unfounded — both runners read same .env token value.

### OI-04 — AWS shadow runner architecture review
**Status:** ✅ CLOSED (V18C session)
Shadow runner scope confirmed valid. All 4 guards present. AWS completing full shadow signal cycles (NIFTY + SENSEX). Retained as-is.

### OI-05 — ENH-31 expiry calendar utility
**Status:** ⏳ OPEN (medium priority)
Pre/post 1 Sep 2025 expiry rule change not handled. Required for accurate DTE calculations.

### OI-06 — Stale IN_PROGRESS hist_ingest_log entries
**Status:** 🟡 LOW — easy
`DELETE FROM hist_ingest_log WHERE status = 'IN_PROGRESS';`

### OI-07 — Supabase disk monitoring
**Status:** ⏳ MONITOR
At 9.5GB of 18GB provisioned as of V18C. Monitor as vendor corrections and live data accumulate.

---

## Section 6 — Enhancement Plan

### E-01 — Signal regret log
**Status:** ✅ CLOSED (V18A)
614 rows in `signal_regret_log`. Outcome clock running. Must reach 30+ sessions of DO_NOTHING outcome data before any confidence threshold changes.

### E-02 — Three-zone gamma model
**Status:** ⏳ SHADOW LIVE (V18A)
gamma_zone field active. HIGH_GAMMA (<0.5%), MID_GAMMA (0.5–1.5%), LOW_GAMMA (>1.5%). Observe 2 weeks then Phase 4 gate.

### E-03 — India VIX signal rules
**Status:** ✅ CLOSED (V18C session)
Added to `build_shadow_signal_v3_local.py`: confidence penalty -8 if india_vix > 20, trade_allowed = False if india_vix > 25. Shadow-only — live signal engine untouched. Committed at e753a15.

### E-05 — SMDM full live implementation
**Status:** ⏳ SHADOW ONLY
Shadow layer built and validated in V16E. Full live promotion requires 2-week shadow accuracy gate (same as Phase 4).

### E-06 — Shadow eval/replay/reconstruction DDLs
**Status:** ✅ CLOSED (V18C session)
All 13 shadow tables documented in `docs/MERDIAN_Shadow_Tables_DDL.md`. Committed at e430ad5.

### E-07 — Multi-session shadow accumulation
**Status:** ⏳ IN PROGRESS
Shadow gate: 4/10 sessions complete (Apr 2, Apr 1, Mar 25, Mar 23). Gate opens after ~6 more clean sessions from 2026-04-07. Shadow steps already wired in runner.

### E-08 — Walk-forward validation (3-year dataset)
**Status:** ⏳ PLANNED
Phase 2 Learning Foundation. Historical dataset procurement required.

---

## Section 7 — Shadow Runner Integration (Group 3)

### Step 3a — compute_options_flow after Step 3
**Status:** ✅ CLOSED (V18C session — confirmed already wired)

### Step 3b — compute_momentum_features_v2 after Step 5
**Status:** ✅ CLOSED (V18C session — confirmed already wired)

### Step 3c — build_shadow_signal_v3 after Step 7
**Status:** ✅ CLOSED (V18C session — confirmed already wired)

### Step 3d — IV context 09:05 once-per-morning
**Status:** ✅ CLOSED (V18C session — MERDIAN_IV_Context_0905 task exists and configured)

### Step 3e — Shadow gate counting (2 weeks/10 sessions)
**Status:** ⏳ IN PROGRESS — 4/10 sessions. See E-07.

### D-09/E-06 — Shadow table DDLs
**Status:** ✅ CLOSED (V18C session)
13 tables documented. See `docs/MERDIAN_Shadow_Tables_DDL.md`.

---

## Section 8 — Signal Quality (Group 5)

### D-06 — flip_distance unit inconsistency
**Status:** ✅ SUBSTANTIALLY CLOSED (V18A)
flip_distance_pct canonical in market-state builder. Downstream consumers verified.

### Phase 4 — Promote to live
**Status:** ⏳ BLOCKED — shadow gate must pass first (4/10 sessions)
After gate: promote momentum v2, options flow, CONFLICT resolution to live. Full file replacement only. Requires model change log entry.

---

## Section 9 — Pending Monday 2026-04-07 Checklist

| Time | Action |
|---|---|
| 08:15 IST | Token refresh fires automatically — check `logs\dhan_token_refresh.log` |
| 08:25 IST | AWS pulls token — check `logs/dhan_token_refresh.log` on AWS |
| 08:30 IST | Run `python run_preflight.py` — must show OVERALL PASS |
| During session | Watch for no duplicate launch, no 15:10 stop |
| After close | Run C-03 WCB query, C-07a AWS premarket query |
| After close | Check shadow gate count — should be 5/10 |

---

## Section 10 — Operational Principles (Standing Rules)

| Principle | Rule |
|---|---|
| DB over Logs | Supabase DB query is canonical truth. Logs are secondary. |
| Measure → Validate → Shadow → Promote | No live file change until measurement gaps closed, evidence collected, shadow runs 2+ weeks, model change log written. |
| Protected Files | build_momentum_features_local.py, compute_gamma_metrics_local.py, build_market_state_snapshot_local.py, build_trade_signal_local.py — not touched until Phase 4 gates pass. |
| trading_calendar is execution control plane | All runners must check is_open before executing. Missing row = hard skip. |
| Full file replacement only | When promoting shadow to live, replace entire file. No partial edits. |
| Threshold governance | No confidence threshold changes until signal_regret_log has 30+ sessions of DO_NOTHING outcome data. |
| run_id not symbol | compute_gamma_metrics_local.py and compute_volatility_metrics_local.py must receive run_id (UUID), not symbol. |
| Shadow accumulation gate | Gate counting begins only after runner integration deployed. Manual-only runs do not count. |
| Token refresh cadence | 08:15 IST Local → 08:25 IST AWS pull → 08:30 IST Preflight |
| No AWS direct edits | Rule 1 of Change Protocol: no code edits on AWS unless BREAK_GLASS emergency. |

---

## Section 11 — What Is Working — Stable Foundation

The following are validated, stable, and should not be reinvestigated.

- Spot ingestion (1-min): NIFTY + SENSEX, auto-archived
- Futures ingestion (1-min): dynamic contract resolution live (V17E)
- Option chain ingestion: per-symbol run_id, idempotent archive
- Gamma metrics: NO_FLIP state valid, gamma_zone active (V18A)
- Volatility snapshots: 34-field VIX enrichment, UNIQUE(symbol,ts)
- WCB (NIFTY + SENSEX): per-symbol loop, 98.86%/98.27% coverage
- Momentum engine: all 8 fields live including ret_session
- Signal engine: confidence decomposed, flip_distance_pct canonical
- signal_regret_log: 614 rows, outcome clock running
- E-02 three-zone gamma shadow: LOW_GAMMA validated
- TOTP token refresh: Supabase sync architecture confirmed
- Outcome engine + analytics: schema valid, V2 rows accumulating
- Runner supervisor: crash-restart, calendar-aware, no duplicate launch (V18C fix)
- Alert daemon: HEARTBEAT_STALE/MISSING/BASE_WARN operational
- Health monitoring: file-based heartbeats, table freshness checks (V18C), 7-section HTML dashboard
- Preflight harness: 4-stage, symmetric Local + AWS, Telegram alerting
- Six shadow tables: all created, UPSERT-safe
- Shadow evaluation/replay/reconstruction tooling: all three tools operational
- Intraday 4-layer guard system: calendar, session-state, coverage, staleness
- trading_calendar: authoritative control plane, missing row = hard skip
- GitHub: repo operational, Local + AWS in sync at e753a15
- AWS EOD ingestion: Python 3.10 compatibility confirmed (V18C fix)
- AWS shadow cycles: NIFTY + SENSEX full signal generation operational
- Historical data: ~15M+ option bars, 247 days NIFTY, 185 days SENSEX (vendor gap confirmed)
- Watchdog: rebuilt with calendar guard, enabled (V18C)

---

*MERDIAN Open Items Register v4 — V18C-Updated — 2026-04-04*
*Supersedes v3. Next update: after 2026-04-07 live session.*
