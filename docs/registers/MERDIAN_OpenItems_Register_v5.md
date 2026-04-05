# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v5 — V18D-Updated — April 2026 |
| Source documents | V18C · V18D · Open Items Register v4 |
| Current latest appendix | V18D (Historical Backfill · Live Dashboard · Vendor Data · 2026-04-04/05) |
| Authority | This document aggregates and does not supersede any master. V18D wins on post-V18C facts. |

---

### V18D Session Changes (2026-04-04/05)

**Closed this session:** OI-02, OI-06 (easy cleanup), validation architecture (Option B now viable via hist_market_state).

**Key additions:** hist_gamma_metrics (244 dates x2), hist_volatility_snapshots (488 pairs), hist_market_state (487 pairs), merdian_live_dashboard.py, BS IV solver validated, SENSEX F+O correction ingested (4.8M new rows), watchdog popup fixed.

**Git range:** d374e4b → bea5224

---

## Section 1 — Critical Fixes

### C-01 — market_state_snapshots duplication
**Status:** ✅ CLOSED (V18A)

### C-02 — Re-ingest 2026-03-24 EOD data
**Status:** ✅ CLOSED (V18A)

### C-03 — SENSEX WCB staleness
**Status:** ⏳ PENDING — confirm on 2026-04-07 live session
```sql
SELECT index_symbol, MAX(ts) AS latest_ts, NOW() - MAX(ts) AS lag
FROM weighted_constituent_breadth_snapshots GROUP BY index_symbol;
```
Expected: lag < 10 minutes during live hours.

### C-04 — Breadth staleness
**Status:** ✅ CLOSED (V18C)

### C-05 — build_trade_signal_local.py 240-sec timeout
**Status:** ✅ CLOSED (V18A)

### C-06 — EOD coverage gap 13–24 March
**Status:** ✅ CLOSED (V18C)

### C-07a — AWS premarket timestamp/query mismatch
**Status:** ⏳ PENDING — confirm on next live session

### C-07b — Local PREMARKET pipeline recording validation
**Status:** ⏳ PENDING — confirm on next live session

### C-08 — Intermittent SENSEX volatility RuntimeError
**Status:** ✅ CLOSED (V18A)

---

## Section 2 — Local Production Hardening

### S-01/S-02 — Scheduler ownership fix
**Status:** ✅ CLOSED (V18C)

### S-03 — MERDIAN_State_Stack_5M
**Status:** ✅ CLOSED (V18C)

### S-04 — 15:10/15:11 late-session stop
**Status:** ⏳ PENDING — monitor from 2026-04-07

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
**Status:** ✅ CLOSED (V18D)
Root cause: repetition trigger with no Duration limit fired 24/7. Fix: watchdog_task_fixed.xml reimported with Duration=PT9H, StartBoundary=2026-04-07T07:30:00. Fires only 07:30–16:30 IST daily.

### M-01 — POSTMARKET session state
**Status:** ✅ CLOSED (V18C)

### M-02 — PREMARKET recording validation
**Status:** ⏳ PENDING — requires live session between 09:00–09:14 IST

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
**Status:** ✅ CLOSED (V18A)

### A-02 — AWS 4:00 PM weighted-average close
**Status:** ✅ CLOSED (V18C)

### A-03 — Dhan auth stability
**Status:** ✅ CLOSED (V18C)

### A-04 — AWS EOD ingestion end-to-end
**Status:** ✅ CLOSED (V18C)

### A-05 — Local vs AWS parity comparison
**Status:** ⏳ PENDING — requires live session

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
**Status:** ✅ CLOSED (V18C)

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
**Status:** ⏳ IN PROGRESS — 4/10 sessions. Gate opens after ~6 more from 2026-04-07.

### E-08 — Walk-forward validation (historical dataset)
**Status:** ✅ SUBSTANTIALLY ADDRESSED (V18D)
hist_market_state table now has 487 date/symbol pairs from April 2025 – March 2026. Full year of varied market conditions (bull, correction, sideways) available. Validation analysis script (OI-08) is the next step.

---

## Section 7 — Shadow Runner Integration (Group 3)

### All steps 3a–3d
**Status:** ✅ CLOSED (V18C)

### Step 3e — Shadow gate counting
**Status:** ⏳ IN PROGRESS — 4/10 sessions. Next session will be 5/10.

---

## Section 8 — Signal Quality (Group 5)

### D-06 — flip_distance unit inconsistency
**Status:** ✅ CLOSED (V18A)

### Phase 4 — Promote to live
**Status:** ⏳ BLOCKED — shadow gate 4/10

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
| Token refresh cadence | 08:15 IST Local → 08:25 IST AWS → 08:30 IST Preflight |
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
- GitHub: repo operational, Local + AWS in sync at bea5224 ✅

---

*MERDIAN Open Items Register v5 — V18D-Updated — 2026-04-06*
*Supersedes v4. Next update: after 2026-04-07 live session.*
