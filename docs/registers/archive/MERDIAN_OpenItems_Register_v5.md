# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v5 — V18D-Updated — April 2026 |
| Source documents | V18C · V18D (Historical Backfill + Live Canary Sessions) · Open Items Register v4 |
| Current latest appendix | V18D (Historical Backfill · Live Canary Sessions · 2026-04-04 through 2026-04-09) |
| Authority | This document aggregates and does not supersede any master. V18D wins on post-V18C facts. |

---

### V18D Session Changes (2026-04-04/05 + 2026-04-06 through 2026-04-09)

**Closed 2026-04-04/05:** OI-02, OI-06 (easy cleanup), validation architecture (Option B now viable via hist_market_state). hist_gamma_metrics (244 dates x2), hist_volatility_snapshots (488 pairs), hist_market_state (487 pairs), merdian_live_dashboard.py, BS IV solver validated, SENSEX F+O correction ingested (4.8M new rows), watchdog popup fixed.

**Closed 2026-04-06 through 2026-04-09 (Live Canary Sprint):** OI-03 (Market_Tape_1M disabled permanently), C-03 (WCB confirmed live), C-07a (AWS premarket confirmed), S-04 (no late stops confirmed), M-02 (premarket confirmed), S-10 (supervisor persistent lock), S-11 (Market_Tape_1M task), A-05 (AWS shadow status write).

**Key live canary fixes:** trading_calendar.py full rewrite (rule-based, no manual entries), dashboard v2 (live session state, token countdown, pipeline values), TOTP retry, AWS breadth disabled (rate limit fix), AWS Guard 4 skipped, supervisor clean-start PS1 wrapper, stage2 preflight calendar check fixed.

**Shadow gate status:** 7/10 sessions complete.

**Git range:** d374e4b → 858de8f

---

## Section 1 — Critical Fixes

### C-01 — market_state_snapshots duplication
**Status:** ✅ CLOSED (V18A)

### C-02 — Re-ingest 2026-03-24 EOD data
**Status:** ✅ CLOSED (V18A)

### C-03 — SENSEX WCB staleness
**Status:** ✅ CLOSED (V18D — confirmed live 2026-04-06 through 2026-04-09)
WCB running correctly for both symbols on all 4 live sessions. Per-symbol loop fix confirmed operational.

### C-04 — Breadth staleness
**Status:** ✅ CLOSED (V18C)

### C-05 — build_trade_signal_local.py 240-sec timeout
**Status:** ✅ CLOSED (V18A)

### C-06 — EOD coverage gap 13–24 March
**Status:** ✅ CLOSED (V18C)

### C-07a — AWS premarket timestamp/query mismatch
**Status:** ✅ CLOSED (V18D — confirmed live 2026-04-08)
AWS cron `capture_premarket_0908.py` fires at 09:08 IST and correctly captures NIFTY + SENSEX spot. Confirmed: NIFTY 23,855 / SENSEX 77,298 at 09:08:02 IST on 2026-04-08.

### C-07b — Pre-open capture gap (09:00–09:08 window)
**Status:** ⏳ OPEN — architectural gap confirmed (V18D)
Supervisor starts at 09:14 — too late for 09:00-09:08 window. AWS cron at 09:08 captures one snapshot but `ingest_market_spot_local.py` doesn't exist on AWS so the pre-open script calls a non-existent file. Dashboard shows NOT CAPTURED every day.
**Fix required:** Dedicated pre-open cron or supervisor pre-session hook before 09:00.

### C-08 — Intermittent SENSEX volatility RuntimeError
**Status:** ✅ CLOSED (V18A)

---

## Section 2 — Local Production Hardening

### S-01/S-02 — Scheduler ownership fix
**Status:** ✅ CLOSED (V18C)

### S-03 — MERDIAN_State_Stack_5M
**Status:** ✅ CLOSED (V18C)

### S-04 — 15:10/15:11 late-session stop
**Status:** ✅ CLOSED (V18D — confirmed resolved 2026-04-06 through 2026-04-09)
No late stops observed on any of the 4 live sessions. S-01/S-02 fix confirmed effective.

### S-05 — Supervisor data-freshness awareness
**Status:** ✅ CLOSED (V18C)

### S-06 — Lock-file cleanup on abnormal exit
**Status:** ✅ CLOSED (V18C)

### S-07 — Watchdog implementation
**Status:** ✅ CLOSED (V18C)

### S-08 — Scheduler ownership manifest
**Status:** ✅ CLOSED (V18C). Updated V18D: MERDIAN_Live_Dashboard added as 12th task.

### S-09 — Token refresh timing
**Status:** ✅ CLOSED (V18C)

### S-10 — Watchdog terminal popup
**Status:** ✅ CLOSED (V18D — 2026-04-04/05)
Root cause: repetition trigger with no Duration limit fired 24/7. Fix: watchdog_task_fixed.xml reimported with Duration=PT9H, StartBoundary=2026-04-07T07:30:00. Fires only 07:30–16:30 IST daily.

### S-11 — Supervisor persistent lock (NEW V18D live canary)
**Status:** ✅ CLOSED (V18D — 2026-04-09)
Root cause: Task Scheduler started new supervisor process without killing old one. Old process from April 6 ran until April 9 holding the lock file — new processes exited immediately finding lock occupied. Fix: `start_supervisor_clean.ps1` uses WMI to find and kill existing supervisor processes before starting fresh. MERDIAN_Intraday_Supervisor_Start now calls this PS1. Weekly 08:00 Mon-Fri trigger also added.

### S-12 — MERDIAN_Market_Tape_1M permanently disabled (NEW V18D live canary)
**Status:** ✅ CLOSED (V18D — 2026-04-07)
Confirmed broken: DhanError 401 every run, returncode=3221225786. Confirmed harmful: 390 extra Dhan calls/day from 09:00-15:30 contributing to 429 rate limiting during breadth ingest. Disabled via Disable-ScheduledTask. No downstream pipeline dependency confirmed.

### M-01 — POSTMARKET session state
**Status:** ✅ CLOSED (V18C)

### M-02 — PREMARKET recording validation
**Status:** ✅ CLOSED (V18D — confirmed live)
market_spot_snapshots receiving rows during pre-open. AWS cron confirmed writing at 09:08 IST. See C-07b for remaining gap (09:00-09:07 window).

---

## Section 3 — V18A Open Items

### V18A-01 — Windows token task unattended proof
**Status:** ✅ CLOSED (V18C)

### V18A-02 — Runner circuit-breaker
**Status:** ✅ CLOSED (V18A)

### V18A-03 — trading_calendar row maintenance
**Status:** ✅ CLOSED (V18A)

---

## Section 4 — AWS Readiness

### A-01 — AWS 4-guard system
**Status:** ✅ UPDATED (V18D live canary)
Guard 3 (breadth coverage) bypassed on AWS — breadth disabled to prevent rate limit saturation. Guard 4 (LTP staleness) skipped on AWS — `equity_intraday_last` not maintained on AWS shadow. Guards 1 (calendar) and 2 (session state) remain active.

### A-02 — AWS 4:00 PM weighted-average close
**Status:** ✅ CLOSED (V18C)

### A-03 — Dhan auth stability
**Status:** ✅ CLOSED (V18C)

### A-04 — AWS EOD ingestion end-to-end
**Status:** ✅ CLOSED (V18C)

### A-05 — AWS shadow Supabase status write
**Status:** ✅ CLOSED (V18D — 2026-04-09)
`write_cycle_status_to_supabase()` added to shadow runner. Writes `cycle_ok`, `breadth_coverage`, `per_symbol`, `last_error`, `cycle_time_ist` to `system_config` table under key `aws_shadow_cycle_status`. Guard 4 skip was preventing the write — fixed by removing Guard 4 on AWS.

### A-06 — Telegram crash-alert on AWS runner
**Status:** ✅ CLOSED (V18C)

---

## Section 5 — Open Items Register (OI series)

### OI-01 — Vendor data futures parse fix
**Status:** ✅ CLOSED (V18C)

### OI-02 — Vendor correction MAY/JUN 2025, JAN 2026
**Status:** ✅ CLOSED (V18D)
Vendor correction files received 2026-04-05. SENSEX F+O contractwise files (BFO_CONTRACT format confirmed). 247 files processed, 4,818,720 new rows accepted, 1 failed (BFO_CONTRACT_05062025.csv — permanent malformed Date column). SENSEX gamma backfill for corrected months: 41/43 (May/Jun) + 20/22 (Jan) — all failures are confirmed holidays.

### OI-03 — MERDIAN_Market_Tape_1M task disabled
**Status:** ✅ CLOSED (V18D — DISABLED permanently 2026-04-07)
Confirmed broken: DhanError 401 every run. Confirmed harmful: 390 extra Dhan calls/day contributing to 429 rate limiting. Disabled. No downstream pipeline dependency confirmed. See S-12.

### OI-04 — AWS shadow runner architecture review
**Status:** ✅ CLOSED (V18C)

### OI-05 — ENH-31 expiry calendar utility
**Status:** ⏳ OPEN (medium priority)

### OI-06 — Stale IN_PROGRESS hist_ingest_log entries
**Status:** ✅ CLOSED (V18D)
`DELETE FROM hist_ingest_log WHERE status = 'IN_PROGRESS';` — run as part of cleanup.

### OI-07 — Supabase disk monitoring
**Status:** ⏳ MONITOR
Was 9.5GB before vendor correction ingest. Re-check after ingestion of 19M+ rows.

### OI-08 — Historical backfill validation analysis
**Status:** ⏳ OPEN (next session)
hist_market_state (487 date/symbol pairs) now available. Need to build run_validation_analysis.py to measure signal accuracy: for each historical signal in signal_snapshots direction, did spot move accordingly at T+15m/T+30m/T+60m using hist_spot_bars_1m?

### OI-09 — Minor master increment V18.1 or V19
**Status:** ⏳ DEFERRED
Triggered by V18D scope (new files, schema changes, components added). Defer until after 2026-04-07 live session confirms system health.

---

## Section 6 — Enhancement Plan

### E-01 — Signal regret log
**Status:** ✅ CLOSED (V18A)

### E-02 — Three-zone gamma model
**Status:** ⏳ SHADOW LIVE (V18A)

### E-03 — India VIX signal rules
**Status:** ✅ CLOSED (V18C)

### E-05 — SMDM full live implementation
**Status:** ⏳ SHADOW ONLY

### E-06 — Shadow eval/replay/reconstruction DDLs
**Status:** ✅ CLOSED (V18C)

### E-07 — Multi-session shadow accumulation
**Status:** ⏳ IN PROGRESS — 7/10 sessions complete
Sessions: Apr 2, Apr 1, Mar 25, Mar 23 (pre-V18D) + Apr 6, Apr 7, Apr 8, Apr 9 (V18D live canary). Gate opens after ~3 more clean sessions.

### E-08 — Walk-forward validation (historical dataset)
**Status:** ✅ SUBSTANTIALLY ADDRESSED (V18D)
hist_market_state table now has 487 date/symbol pairs from April 2025 – March 2026. Full year of varied market conditions (bull, correction, sideways) available. Validation analysis script (OI-08) is the next step.

---

## Section 7 — Shadow Runner Integration (Group 3)

### All steps 3a–3d
**Status:** ✅ CLOSED (V18C)

### Step 3e — Shadow gate counting
**Status:** ⏳ IN PROGRESS — 7/10 sessions complete. Gate opens ~3 more clean sessions.

---

## Section 8 — Signal Quality (Group 5)

### D-06 — flip_distance unit inconsistency
**Status:** ✅ CLOSED (V18A)

### Phase 4 — Promote to live
**Status:** ⏳ BLOCKED — shadow gate 7/10. ~3 more sessions needed.

---

## Section 9 — Pending 2026-04-07 Checklist

| Time | Action |
|---|---|
| 08:15 IST | Token refresh fires automatically |
| 08:25 IST | AWS pulls token |
| 08:30 IST | Run python run_preflight.py — must show OVERALL PASS |
| 08:30 IST | Open http://localhost:8765 — dashboard auto-started at login |
| During session | Watch dashboard — all stages green by 09:25 |
| After close | Run C-03 WCB query |
| After close | Check shadow gate = 5/10 |
| After close | Check Supabase disk usage |

---

## Section 10 — Operational Principles (Standing Rules)

| Principle | Rule |
|---|---|
| DB over Logs | Supabase DB query is canonical truth. |
| Measure → Validate → Shadow → Promote | No live file change until evidence collected. |
| Protected Files | build_momentum_features_local.py, compute_gamma_metrics_local.py, build_market_state_snapshot_local.py, build_trade_signal_local.py — Phase 4 gates only. |
| trading_calendar is execution control plane | Missing row = hard skip. |
| Full file replacement only | When promoting shadow to live. |
| Threshold governance | No confidence threshold changes until 30+ DO_NOTHING sessions in signal_regret_log. |
| run_id not symbol | compute_gamma/volatility scripts receive run_id UUID. |
| Shadow accumulation gate | Manual-only runs do not count. |
| Token refresh cadence | 08:15 IST Local → 08:35 IST AWS pull → 08:45 IST Preflight |
| No AWS direct edits | Rule 1 of Change Protocol. |
| Separate hist tables | hist_* tables are backfill-only. Live tables are Dhan-only. Promote via INSERT SELECT when validated. |

---

## Section 11 — What Is Working — Stable Foundation

- Spot ingestion (1-min): NIFTY + SENSEX, auto-archived ✅
- Futures ingestion (1-min): dynamic contract resolution live ✅
- Option chain ingestion: per-symbol run_id, idempotent archive ✅
- Gamma metrics: NO_FLIP state valid, gamma_zone active ✅
- Volatility snapshots: 34-field VIX enrichment ✅
- WCB (NIFTY + SENSEX): per-symbol loop ✅
- Momentum engine: all 8 fields live including ret_session ✅
- Signal engine: confidence decomposed, flip_distance_pct canonical ✅
- signal_regret_log: 614 rows, outcome clock running ✅
- TOTP token refresh: Supabase sync architecture confirmed ✅
- Runner supervisor: crash-restart, calendar-aware ✅
- Alert daemon: HEARTBEAT_STALE/MISSING/BASE_WARN operational ✅
- Health monitoring: file-based heartbeats, table freshness checks ✅
- Live dashboard: localhost:8765, auto-refresh 30s, action buttons ✅ **NEW V18D**
- Preflight harness: 4-stage, symmetric Local + AWS, Telegram ✅
- Historical backfill: hist_gamma_metrics + hist_volatility + hist_market_state ✅ **NEW V18D**
- BS IV solver: pure-Python, validated against known option ✅ **NEW V18D**
- Vendor data: SENSEX F+O correction ingested ✅ **NEW V18D**
- Watchdog: market-hours only (07:30–16:30 IST), no weekend popup ✅ **FIXED V18D**
- GitHub: repo operational, Local + AWS in sync at 858de8f ✅
- trading_calendar: rule-based rewrite, no manual entries required ✅ **UPDATED V18D live canary**
- Dashboard v2: live session state, token countdown, pipeline values, inline feedback ✅ **UPDATED V18D live canary**
- Supervisor clean-start: PS1 wrapper kills old process before starting new ✅ **NEW V18D live canary**
- TOTP retry: automatic 30s wait on Invalid TOTP ✅ **NEW V18D live canary**
- Breadth: Local-only ingest, AWS reads from Supabase ✅ **NEW V18D live canary**

---

*MERDIAN Open Items Register v5 — V18D-Updated — 2026-04-09*
*Supersedes v4. Next update: after next engineering session.*
