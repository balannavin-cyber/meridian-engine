# MERDIAN System Map

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_System_Map.md` |
| Location | `docs/registers/` |
| Type | File / table / runner / orchestration index — "what lies where" lookup |
| Established | 2026-05-09 (Session 23 — created per Doc Protocol v4 Rule 9.1) |
| Update rule | Inline, same commit as the code change. Update triggers in Doc Protocol v4 Rule 1. |
| Source authority | `merdian_reference.json` is the machine-queryable inventory; this Map is the human-readable, lookup-optimised layer above it. When the two disagree, the JSON wins on file paths and exact statuses; this Map wins on architectural narrative and pipeline ordering. |

---

## Purpose

A single answer to "where does X live? what writes to what? what calls what?" Replaces digging through V17/V18/V19 master appendices for routine inventory questions. Used at session start (CLAUDE.md Rule 0 read order #3) to ground decisions in current architecture.

This is the **production** map. Research scripts (`experiment_*.py`, etc.) are not catalogued here — they live in `docs/research/` and `merdian_reference.json`. Patches, hotfix scripts, and one-off migrations are not catalogued unless they introduce permanent infrastructure.

## How to read this map

- **Status column** uses the JSON's status taxonomy (ACTIVE / LIVE / STABLE / PRODUCTION / DISABLED / RETIRED). Where the JSON's status is verbose, this Map summarises and links the JSON entry for full text.
- **Per-row links to JSON** are by file or table name. Look up `merdian_reference.json` → `files.<name>` or `tables.<name>` for the canonical entry.
- **Sections are domain-scoped, not alphabetical.** Within a section, ordering is by execution order or architectural prominence.

---

## §A — Script index (production scripts)

### A.1 Capture & ingest layer (data acquisition)

| Script | Local | AWS | Reads | Writes | Status |
|---|---|---|---|---|---|
| `capture_market_spot_snapshot_local.py` | ✅ | ✅ | Dhan REST `/marketfeed/quote/index` | `market_spot_snapshots` | ACTIVE — used by AWS PreOpen cron 09:08 IST |
| `capture_spot_1m.py` | ✅ | ❌ | Dhan REST | `market_spot_snapshots` | ACTIVE — used by Local `MERDIAN_PreOpen` task (pythonw.exe). Different code path from `capture_market_spot_snapshot_local.py` despite same purpose — see Deployment Topology §9 question #2 |
| `capture_spot_1m_v2.py` | ✅ | ❌ | Dhan REST | `market_spot_snapshots` | ACTIVE — used by Local `MERDIAN_Spot_1M` task (pythonw.exe). Production-active 1-min spot ingester replacing disabled `run_market_tape_1m.py` |
| `capture_index_futures_snapshot_local.py` | ✅ | ✅ | Dhan REST + dynamic contract resolution | `index_futures_snapshots` | ACTIVE — V17E dynamic contract |
| `ws_feed_zerodha.py` | ✅ | ❌ | Zerodha KiteTicker WebSocket (NIFTY full chain) | `option_chain_snapshots` (Zerodha rows) | ACTIVE — Session 13 task registered |
| `ingest_option_chain_local.py` | ✅ | ✅ | Dhan REST option chain | `option_chain_snapshots` | ACTIVE — currently failing 401 on Local (V18A) |
| `ingest_breadth_from_ticks.py` | ✅ | ✅ | Dhan tick feed | `market_breadth_intraday`, `equity_intraday_last` | ACTIVE — C-08 fix 2026-04-19 |
| `ingest_equity_eod_local.py` | ✅ | ✅ | Dhan REST EOD | `equity_eod` | ACTIVE — cursor-gated full coverage |
| `capture_postmarket_1600.py` | ❌ | ✅ | Dhan REST | `market_spot_snapshots` (16:00 close) | ACTIVE (AWS only) |
| `run_market_close_capture_once.py` | ❌ | ✅ | Dhan REST | end-of-day snapshots | ACTIVE (AWS only) — V18A AWS parity |

### A.2 Compute layer (5-min cycle, runs in Step order within `run_option_snapshot_intraday_runner.py`)

| Script | Local | AWS | Reads | Writes | Status |
|---|---|---|---|---|---|
| `build_market_state_snapshot_local.py` | ✅ | ✅ | `option_chain_snapshots`, `gamma_metrics`, `market_breadth_intraday`, `momentum_snapshots`, `volatility_snapshots`, `iv_context_snapshots` | `market_state_snapshots` | ACTIVE — V18A `flip_distance_pct` canonical |
| `compute_gamma_metrics_local.py` | ✅ | ✅ | `option_chain_snapshots` | `gamma_metrics` (with V18A `gamma_zone` field) | ACTIVE |
| `compute_iv_context_local.py` | ✅ | ✅ | `option_chain_snapshots` | `iv_context_snapshots` | ACTIVE — runs morning via `MERDIAN_IV_Context_0905` |
| `compute_volatility_metrics_local.py` | ✅ | ✅ | `option_chain_snapshots`, India VIX | `volatility_snapshots` | ACTIVE — IV=0 filter, ATM fallback |
| `build_momentum_features_local.py` | ✅ | ✅ | `market_spot_snapshots`, `market_spot_session_markers` | `momentum_snapshots` | ACTIVE — `ret_session` live (ENH-01) |
| `build_wcb_snapshot_local.py` | ✅ | ✅ | constituent ticks | `weighted_constituent_breadth_snapshots` | ACTIVE — continues even when Dhan options auth broken |
| `build_trade_signal_local.py` | ✅ | ✅ | `market_state_snapshots`, ICT pattern context | `signal_snapshots` | ACTIVE — 6 ENH-35 changes applied (ADR-007 codification) + 4 ICT columns |
| `build_signal_regret_log_v1.py` | ✅ | ❌ | `signal_snapshots`, `market_spot_snapshots` | `signal_regret_log` | ACTIVE — 614 rows (V18A baseline) |

### A.3 ICT layer (Inner Circle Trader pattern detection)

| Script | Local | AWS | Reads | Writes | Status |
|---|---|---|---|---|---|
| `build_ict_htf_zones.py` | ✅ | ✅ | `hist_spot_bars_5m`, `hist_spot_bars_15m`, etc. | `ict_htf_zones` | PRODUCTION — ENH-37, patched Session 15 |
| `build_ict_htf_zones_historical.py` | ✅ | ❌ | historical OHLCV | `ict_htf_zones` (backfill) | PRODUCTION — historical builder, patched Session 15 |
| `detect_ict_patterns.py` | ✅ | ✅ | `hist_spot_bars_5m`, `ict_htf_zones` | `hist_pattern_signals` | PRODUCTION — ENH-37 |
| `detect_ict_patterns_runner.py` | ✅ | ✅ | runner harness | calls `detect_ict_patterns` | PRODUCTION — ENH-37, wired by `patch_runner_ict.py` |
| `detect_po3_session_bias.py` | ✅ | ❌ | `hist_spot_bars_5m`, sweep events | `po3_session_state` | ACTIVE — ENH-75 SHIPPED 2026-04-29 |
| `build_atm_option_bars_mtf.py` | ✅ | ❌ | `option_chain_snapshots` | `hist_atm_option_bars_5m`, `hist_atm_option_bars_15m` | STABLE — 27,082 + 9,601 rows |
| `build_hist_pattern_signals_5m.py` | ✅ | ❌ | `hist_spot_bars_5m`, `ict_htf_zones` | `hist_pattern_signals` (backfill) | STABLE — 6,318 rows |
| `build_spot_bars_mtf.py` | ✅ | ❌ | `market_spot_snapshots` | `hist_spot_bars_5m`, `hist_spot_bars_15m` | STABLE — ENH-71 instrumented, 42,324 rows |

### A.4 Runners & orchestration

| Script | Local | AWS | Purpose | Status |
|---|---|---|---|---|
| `run_option_snapshot_intraday_runner.py` | ✅ | ❌ | Live 5-minute options runner — Steps 1–8 including signal build | ACTIVE — V18E CREATE_NO_WINDOW |
| `run_merdian_shadow_runner.py` | ❌ | ✅ | AWS shadow 5-minute cycle | ACTIVE — V18E breadth ingest disabled (Guard 3) |
| `run_market_tape_1m.py` | ✅ | ❌ | 1-minute tape (DhanError 401 every run) | DISABLED — see TD register |
| `gamma_engine_supervisor.py` | ✅ | ❌ | Restarts crashed runners; emits heartbeat | ACTIVE — V17E clean exit |
| `start_supervisor_clean.ps1` | ✅ | ❌ | Kills existing supervisor, starts fresh | ACTIVE — V18E |
| `run_equity_eod_until_done.py` | ✅ | ✅ | EOD recovery + AWS EOD ingest | ACTIVE |
| `trading_calendar.py` | ✅ | ✅ | Calendar gate; weekday + non-holiday lookup | ACTIVE — V18E rule-based rewrite |
| `stage2_db_contract.py` | ✅ | ✅ | Contract validation before DB writes | ACTIVE — V18E calendar week-ahead check |

### A.5 Token, auth, dashboards, monitoring

| Script | Local | AWS | Purpose | Status |
|---|---|---|---|---|
| `refresh_dhan_token.py` | ✅ | ✅ | Daily Dhan token refresh + TOTP retry | ACTIVE — V18E TOTP retry on InvalidTOTP |
| `merdian_signal_dashboard.py` | ✅ | ❌ | Live signal table, Pine refresh, trade-log button | ACTIVE — V19, ENH-84 refresh button |
| `merdian_live_dashboard.py` | ✅ | ❌ | Live session state + token countdown | ACTIVE — V18E v2 |
| `gamma_engine_monitor_dashboard.py` | ✅ | ❌ | Operational monitoring dashboard | ACTIVE |
| `gamma_engine_alert_daemon.py` | ✅ | ❌ | Alert emission on operational thresholds | ACTIVE |
| `merdian_pipeline_alert_daemon.py` | ✅ | ❌ | Pipeline-stage alerting | RUNNING (PID 19636 as of 2026-04-26 14:17 IST) |
| `gamma_engine_telemetry_logger.py` | ✅ | ❌ | Heartbeat / telemetry capture | ACTIVE — supervisor write failure tracked (M-07) |
| `merdian_watchdog.py` | ✅ | ❌ | Process killer for hung Python runners (`--kill` flag) | ACTIVE — wired to `MERDIAN_HB_Watchdog` (TimeTrigger interval), runs as `pythonw.exe`. **Production-critical; currently untracked in git — see follow-up flag** |
| `watchdog_check.ps1` | ✅ | ❌ | Passive state-check / alert layer (companion to `merdian_watchdog.py`) | ACTIVE — wired to `MERDIAN_Watchdog` (TimeTrigger interval). PowerShell |
| `merdian_morning_start.ps1` | ✅ | ❌ | Morning supervisor entry point (Mon-Fri 08:00 + AtLogon) | ACTIVE — wired to `MERDIAN_Intraday_Supervisor_Start`. **Replaces `start_supervisor_clean.ps1` that JSON had as the action** — `merdian_morning_start.ps1` may invoke `start_supervisor_clean.ps1` internally; not yet audited |
| `evaluate_shadow_vs_live.py` | ✅ | ✅ | Shadow vs live comparison (returns 0 rows below threshold) | FUNCTIONAL |

### A.6 Phase 4A execution (manual signal capture + trade logging)

| Script | Local | AWS | Purpose | Status |
|---|---|---|---|---|
| `merdian_trade_logger.py` | ✅ | ❌ | Manual trade entry coupled with signal_snapshots row | ACTIVE — V18G Phase 4A |
| `build_option_execution_outcomes_v1.py` | ✅ | ❌ | Compute outcomes from logged trades | NEEDS MIGRATION — must read from new schema |

### A.7 Manual / shadow scripts (not in live pipeline)

These exist but are not wired into any scheduler. Used for shadow A/B tests or manual research runs.

| Script | Purpose | Status |
|---|---|---|
| `compute_smdm_local.py` | SMDM (Simple Market Direction Model) shadow layer | MANUAL |
| `compute_options_flow_local.py` | Options flow shadow features | MANUAL |
| `compute_momentum_features_v2_local.py` | Shadow momentum v2 | MANUAL |
| `build_shadow_signal_v3_local.py` | Shadow signal architecture | MANUAL |

### A.8 Utility / core abstractions

| Script | Purpose | Status |
|---|---|---|
| `merdian_utils.py` | Shared utilities — paginated reads, NIFTY Thursday→Wed weekly handling | STABLE — v2 paginated |
| `archive_market_tape_history.py` | Periodic compression of market tape history | ACTIVE |
| `archive_option_chain_history.py` | Periodic compression of option chain history | ACTIVE |

### A.9 Backups, retired, deprecated — DO NOT USE

These exist on disk but are not authoritative. Listed for completeness so future sessions don't accidentally use them.

| File | Original | Disposition |
|---|---|---|
| `build_ict_htf_zones_PRE_S15.py` | Pre-Session-15 build_ict_htf_zones | BACKUP — keep for rollback |
| `build_ict_htf_zones_historical_PRE_S15.py` | Pre-Session-15 historical builder | BACKUP — keep for rollback |
| `ingest_breadth_intraday_local.py` | Daily breadth ingester | RETIRED 2026-04-16 (commit 4599bb8) — superseded by `ingest_breadth_from_ticks.py` |
| `ingest_option_execution_price_history_v2.DEAD` | Old execution price ingester | RETIRED — DO NOT USE |
| `run_market_tape_1m.pre_premarket_fix.DEAD` | Old market tape runner | RETIRED — DO NOT USE |
| `run_all_experiments_overnight.py` | Overnight research batch | STABLE but research-only, not production |
| Session-17 `_PRE_S17_TD060.py` snapshots | Pre-TD-060 detector versions | BACKUP — see CLAUDE.md Rule 22 |

---

## §B — Table index

All 36 currently-tracked tables in `merdian_reference.json`. Grouped by domain.

### B.1 Spot, options, futures (live tape)

| Table | Written by | Read by | Status |
|---|---|---|---|
| `market_spot_snapshots` | `capture_market_spot_snapshot_local.py`, `capture_postmarket_1600.py` | `build_momentum_features_local.py`, signal regret log, outcome engine, all spot-derived computations | LIVE — 1-min cadence; canonical timeline (V16 architectural principle) |
| `market_spot_session_markers` | `capture_market_spot_snapshot_local.py` (PreOpen capture) | `build_momentum_features_local.py` for `ret_session` | ACTIVE — V18A `open_0915_ts` (NOT `open_0915` — that column does not exist) |
| `option_chain_snapshots` | `ingest_option_chain_local.py` (Dhan REST), `ws_feed_zerodha.py` (Kite WS) | `compute_gamma_metrics_local.py`, `compute_iv_context_local.py`, `compute_volatility_metrics_local.py`, ATM bar builder | LIVE — dual cadence; Dhan currently failing 401 on Local (V18A) |
| `index_futures_snapshots` | `capture_index_futures_snapshot_local.py` | basis computation | LIVE — V17E dynamic contract resolution |

### B.2 Computed metrics (5-min cycle outputs)

| Table | Written by | Read by | Status |
|---|---|---|---|
| `gamma_metrics` | `compute_gamma_metrics_local.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE — V18A `gamma_zone` field, raw columns. ENH-80 will add zone-bound columns. |
| `iv_context_snapshots` | `compute_iv_context_local.py` | `build_market_state_snapshot_local.py`, signal builder | ACTIVE — morning via `MERDIAN_IV_Context_0905` |
| `volatility_snapshots` | `compute_volatility_metrics_local.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE |
| `momentum_snapshots` | `build_momentum_features_local.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE — includes `ret_session` (ENH-01) |
| `momentum_snapshots_v2` | `compute_momentum_features_v2_local.py` (manual) | shadow comparison | ACTIVE — manual / shadow only |
| `weighted_constituent_breadth_snapshots` | `build_wcb_snapshot_local.py` | analytics, breadth diagnostic | LIVE |
| `market_state_snapshots` | `build_market_state_snapshot_local.py` | `build_trade_signal_local.py`, analytics | LIVE WITH DEFECT — C-01 open (duplicate rows) |

### B.3 Signals (live decision layer)

| Table | Written by | Read by | Status |
|---|---|---|---|
| `signal_snapshots` | `build_trade_signal_local.py` | outcome engine, analytics, shadow comparison, regret log builder, `merdian_signal_dashboard.py` | LIVE — primary decision record. ICT columns added 2026-04-11 (`patch_signal_ict.py`). `po3_session_bias` added Session 13. |
| `signal_regret_log` | `build_signal_regret_log_v1.py` | analytics, ADR-007 evidence base | ACTIVE — 614 rows V18A baseline. Per ADR-007, the V15.1-spec'd role as threshold-change gate is retired; ongoing diagnostic role continues. |
| `shadow_signal_snapshots_v3` | `build_shadow_signal_v3_local.py` (manual) | shadow comparison | ACTIVE — manual only |

### B.4 ICT layer

| Table | Written by | Read by | Status |
|---|---|---|---|
| `ict_htf_zones` | `build_ict_htf_zones.py`, `build_ict_htf_zones_historical.py` | `detect_ict_patterns.py`, dashboard, Pine overlay | LIVE — ENH-37 |
| `ict_zones` | `detect_ict_patterns.py` (intraday zone build) | dashboard, signal builder | LIVE — ENH-37. Note: separate schema from `ict_htf_zones` (TD-047). |
| `hist_pattern_signals` | `detect_ict_patterns.py`, `build_hist_pattern_signals_5m.py` (backfill) | analytics, dashboards, win-rate computations | ACTIVE — 6,318 rows |
| `hist_spot_bars_5m` | `build_spot_bars_mtf.py` | ICT detector, HTF zone builder, experiment scripts | ACTIVE — 41,248 rows full year |
| `hist_spot_bars_15m` | `build_spot_bars_mtf.py` | HTF zone builder | ACTIVE — 14,072 rows full year |
| `hist_atm_option_bars_5m` | `build_atm_option_bars_mtf.py` | analytics, premium-outcome computation | ACTIVE — 27,082 rows full year |
| `hist_atm_option_bars_15m` | `build_atm_option_bars_mtf.py` | analytics | ACTIVE — 9,601 rows |
| `po3_session_state` | `detect_po3_session_bias.py` | signal builder (ENH-76, ENH-77 gates) | ACTIVE — Session 13 (ENH-75) |

### B.5 Breadth

| Table | Written by | Read by | Status |
|---|---|---|---|
| `market_breadth_intraday` | `ingest_breadth_from_ticks.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE — writes resumed 2026-04-19 (C-08 closure) |
| `breadth_intraday_history` | `ingest_breadth_from_ticks.py` | analytics, validity layer (ADR-001) | LIVE — every cycle including zero-coverage |
| `latest_market_breadth_intraday` | view (auto-reflects newest row) | analytics, dashboard | LIVE — view |
| `breadth_indicators_daily` | `ingest_equity_eod_local.py` | DMA10/DMA20/DMA40 RPC calls | ACTIVE |
| `breadth_ingest_state` | `ingest_equity_eod_local.py` | cursor-advance logic | ACTIVE — tracks EOD cursor per trade_date |
| `breadth_universe_members` | manual / config | breadth ingester filter | ACTIVE — `is_active=true` is universe filter |

### B.6 Equity / EOD

| Table | Written by | Read by | Status |
|---|---|---|---|
| `equity_eod` | `ingest_equity_eod_local.py` | breadth indicators daily, analytics | MOSTLY CURRENT — 2026-03-24 coverage 39.71% (C-02 open) |
| `equity_intraday_last` | `ingest_breadth_from_ticks.py` | breadth dashboards, validity layer (ADR-001 reference) | LIVE with 4 guards |

### B.7 Calendar / config

| Table | Written by | Read by | Status |
|---|---|---|---|
| `trading_calendar` | manual / config | every cycle as hard gate; `trading_calendar.py` lookup | AUTHORITATIVE — missing row = system treats day as non-trading |

### B.8 Manual / shadow only

| Table | Written by | Read by | Status |
|---|---|---|---|
| `smdm_snapshots` | `compute_smdm_local.py` (manual) | shadow analytics | ACTIVE — manual. `pattern` field: SQUEEZE / STOP_HUNT |
| `options_flow_snapshots` | `compute_options_flow_local.py` (manual) | shadow analytics | ACTIVE — manual only |

### B.9 Not built / deprecated

| Table | Status | Note |
|---|---|---|
| `capital_tracker` | NOT BUILT | OI-09 / required before ENH-38 (Kelly capital scaling) |
| `gex_strike_snapshots` | NOT BUILT | ENH-80 PROPOSED — build after ENH-75 |
| `option_execution_price_history` | DEPRECATED | No new rows. Formal DROP pending after outcome engine migration. |

---

## §C — Pipeline diagrams

### C.1 5-minute options runner (LOCAL, primary)

```
                    08:30 IST start, runs every 5 min until 15:30 IST
                                      │
                                      ▼
              ┌───────────────────────────────────────────────┐
              │  trading_calendar gate (HARD)                 │
              │  ↓ open ↓ closed → exit                       │
              └───────────────────────────────────────────────┘
                                      │
       Step 1  capture_market_spot_snapshot_local.py
                  → market_spot_snapshots (1m cadence)
                  → market_spot_session_markers (PreOpen capture)
                                      │
       Step 2  ingest_option_chain_local.py
                  → option_chain_snapshots (5m rows)
                                      │
       Step 3  compute_gamma_metrics_local.py
                  → gamma_metrics (with gamma_zone)
                                      │
       Step 4  compute_iv_context_local.py    (or morning task pre-cycle)
                  → iv_context_snapshots
                                      │
       Step 5  compute_volatility_metrics_local.py
                  → volatility_snapshots
                                      │
       Step 6  build_momentum_features_local.py
                  → momentum_snapshots
                                      │
       Step 7  build_market_state_snapshot_local.py
                  → market_state_snapshots
                                      │
       Step 8  detect_ict_patterns_runner.py
                  → hist_pattern_signals
                  → ict_zones
                                      │
       Step 9  build_trade_signal_local.py
                  → signal_snapshots (with ICT columns + po3_session_bias)
                                      │
                                      ▼
                  merdian_signal_dashboard.py reads + renders
```

### C.2 1-minute tape (LOCAL — currently DISABLED)

```
   capture_market_spot_snapshot_local.py
            ↓
   market_spot_snapshots (1m cadence)
            ↓
   build_wcb_snapshot_local.py
            ↓
   weighted_constituent_breadth_snapshots
            ↓
   ingest_breadth_from_ticks.py
            ↓
   market_breadth_intraday + breadth_intraday_history + equity_intraday_last

   Note: run_market_tape_1m.py is DISABLED (DhanError 401 every run).
```

### C.3 AWS shadow runner

```
   09:15 IST cron MERDIAN_Shadow_Runner
            ↓
   run_merdian_shadow_runner.py (V18E)
   - Breadth ingest DISABLED on AWS (Guard 3 — single-writer rule)
   - Reads option_chain via Dhan REST
   - Writes shadow rows to dedicated shadow tables (or shadow columns)
   - Runs in nohup; logs to logs/aws_shadow_runner.nohup.log
            ↓
   evaluate_shadow_vs_live.py compares (FUNCTIONAL — returns 0 rows below threshold)
```

### C.4 Pre-market

```
   08:35 IST    Token pull  (refresh_dhan_token.py — AWS cron + Local Task Scheduler)
                → .env writes new DHAN_ACCESS_TOKEN
                → Local Supabase sync
   08:45 IST    build_ict_htf_zones.py (MERDIAN_ICT_HTF_Zones_0845)
                → ict_htf_zones (D, H, 4H zones for the day)
   09:05 IST    compute_iv_context_local.py (MERDIAN_IV_Context_0905)
                → iv_context_snapshots (AM band)
   09:08 IST    capture_market_spot_snapshot_local.py PreOpen capture
                → market_spot_session_markers.open_0915_ts
   09:15 IST    Market open. 5-min cycle begins.
```

### C.5 Post-market

```
   15:30 IST    Last 5-min cycle of the trading day
   15:35 IST    Final dashboard snapshot
   16:00 IST    capture_postmarket_1600.py (AWS only)
                → market_spot_snapshots (16:00 close row)
   16:00 IST    MERDIAN_Spot_MTF_Rollup_1600 (Local Task Scheduler)
                → run_spot_mtf_rollup_once.bat → build_spot_bars_mtf.py
                → hist_spot_bars_5m, hist_spot_bars_15m
   16:10 IST    AWS cron MERDIAN_EOD
                → run_equity_eod_until_done.py
                → equity_eod
                → breadth_indicators_daily (downstream)
```

---

## §D — Orchestration index

### D.1 AWS cron entries (4 confirmed)

Source: `merdian_reference.json` `aws_cron`. Install rule: NEVER use interactive `crontab -e`; always non-interactive temp-file install (snapshot to `logs/aws_crontab_snapshot.txt`).

| Label | Time IST | Script | Notes |
|---|---|---|---|
| `MERDIAN_Token_Refresh` | 09:05 | `refresh_dhan_token.py` | Daily token refresh; AWS pulls at 03:05 UTC = 08:35 IST |
| `MERDIAN_PreOpen` | 09:08 | `capture_market_spot_snapshot_local.py` | PreOpen spot capture |
| `MERDIAN_Shadow_Runner` | 09:15 | `run_merdian_shadow_runner.py` | nohup, logs to `aws_shadow_runner.nohup.log` |
| `MERDIAN_Postmarket` | 16:00 | `capture_postmarket_1600.py` | NOT YET PROVEN (A-02 open) |
| `MERDIAN_EOD` | 16:10 | `run_equity_eod_until_done.py` | Cursor-gate logic not ported (A-04 open) |

### D.2 Local Task Scheduler entries

**Canonical inventory: `MERDIAN_Deployment_Topology.md` §7.2.** 17 `MERDIAN_*` tasks confirmed via Session 23 audit (`Get-ScheduledTask` + action mapping pass). The full inventory with trigger types, cadences, canonical actions (script paths + arguments), and architectural notes lives in Topology §7.2 — single source of truth.

Summary view:

| Tasks running | Count |
|---|---|
| Active production tasks | 16 |
| Disabled / functionally non-functional | 1 (`MERDIAN_Market_Tape_1M` — task `Ready` but script DhanError 401) |
| **Total** | **17** |

The split by trigger type: 13 Weekly (Mon-Fri-bound), 2 TimeTrigger (recurring intervals — watchdogs), 1 LogonTrigger (`Live_Dashboard`), 1 Daily.

Architectural insights from the action-mapping audit (full detail in Topology §7.2 Notes + Architectural Insights subsection):
- **TD-061 pythonw migration partially complete** — 4 tasks already use `pythonw.exe` (`HB_Watchdog`, `Live_Dashboard`, `PreOpen`, `Spot_1M`); 11 still wrap through cmd via .bat
- **Two-watchdog architecture is intentional** — `merdian_watchdog.py --kill` (kill layer) + `watchdog_check.ps1` (observe layer)
- **Local `MERDIAN_PreOpen` and AWS cron `MERDIAN_PreOpen` run different scripts** — `capture_spot_1m.py` (Local, pythonw) vs `capture_market_spot_snapshot_local.py` (AWS); dupe-check pending

### D.3 Supervisor responsibilities

`gamma_engine_supervisor.py` (V17E clean exit):
- Restarts crashed runners (`run_option_snapshot_intraday_runner.py`, etc.)
- Emits heartbeat to telemetry
- Does NOT reload code on the fly — restart-only (V15.1 architectural principle)
- Single-instance enforcement: TD-063 candidate per Session 17

`start_supervisor_clean.ps1` (V18E):
- Kills any existing `gamma_engine_supervisor.py` process
- Starts a fresh one
- Wired to `MERDIAN_Intraday_Supervisor_Start` task (08:00 + AtLogon)

---

## §E — Monitoring & runtime artifacts

### E.1 Health-check thresholds

Source: V15.1 §9.2.4. These thresholds are still load-bearing in `gamma_engine_health_check.py` (status not separately re-confirmed in current sessions — worth a one-line code grep to verify).

| Constant | Value | Meaning |
|---|---|---|
| `MAX_CYCLE_AGE_SECONDS` | 420 | Latest cycle older than 7 minutes triggers DEGRADED |
| `MAX_STAGE_LAG_SECONDS` | 180 | Stage-to-stage gap older than 3 minutes triggers DEGRADED |
| `MAX_SYMBOL_TS_GAP` | 180 | Per-symbol timestamp gap older than 3 minutes triggers DEGRADED |

### E.2 Telemetry files

Located under `runtime/telemetry/` per V15.1 §9.2.5. The five canonical files:

| File | Cadence | Purpose |
|---|---|---|
| `latest_health_snapshot.json` | Every cycle | Most recent health snapshot, single object overwritten |
| `health_snapshots.jsonl` | Every cycle, append | Per-cycle health snapshot log |
| `health_events.jsonl` | On state change, append | DEGRADED/RECOVERED transitions |
| `alerts.jsonl` | On alert fire, append | Per-alert record (deduped via `alert_state.json`) |
| `alert_state.json` | On alert state change | Active alerts and last-fired timestamps |

### E.3 Heartbeat field schema

Per V15.1 §9.2.3 — emitted by supervisor and runners:

```json
{
  "component": "<runner | supervisor | dashboard>",
  "timestamp": "<UTC ISO 8601>",
  "pid": <int>,
  "base_status": "<OK | DEGRADED | DOWN>",
  "notes": "<freeform>"
}
```

`gamma_engine_telemetry_logger.py` writes these. M-07 tracked: supervisor write failure observed; not yet fully resolved.

---

## §F — Core abstractions

The `core/` module is the abstraction layer every other script depends on. Function signatures captured here so future sessions don't have to grep.

### F.1 `core/config.py` (per V15.1 §9.1)

```python
def get_env(key: str, default: str = None) -> str:
    """Read environment variable; raise if required and missing."""

def load_dotenv(path: str = ".env") -> None:
    """Load .env into os.environ. Idempotent."""

def get_supabase_url() -> str: ...
def get_supabase_key() -> str: ...
def get_dhan_client_id() -> str: ...
def get_dhan_access_token() -> str: ...
def get_kite_api_key() -> str: ...
def get_kite_access_token() -> str: ...
```

### F.2 `core/supabase_client.py` (per V15.1 §9.1)

```python
def select(table: str, where: dict = None, limit: int = None,
           order_by: str = None, columns: list = None) -> list[dict]:
    """Read from a Supabase table with where-filter, ordering, projection."""

def select_all(table: str, where: dict = None, batch_size: int = 1000) -> list[dict]:
    """Paginated read until exhaustion. Use for full-table scans."""

def insert(table: str, rows: list[dict] | dict) -> dict:
    """Insert one or many rows."""

def upsert(table: str, rows: list[dict] | dict, on_conflict: str = None) -> dict:
    """Upsert with conflict resolution."""

def rpc(function: str, params: dict = None) -> any:
    """Call a Postgres function via RPC."""
```

### F.3 `core/dhan_client.py` (per V15.1 §9.1)

```python
def get_option_chain(security_id: str, segment: str, expiry: str) -> dict:
    """Full option chain for security_id, segment, expiry."""

def get_ltp(security_ids: list[str], segment: str) -> dict:
    """Last traded prices for a list of security IDs."""

def get_historical_candles(security_id: str, segment: str,
                            from_date: str, to_date: str,
                            interval: str = "1m") -> list[dict]:
    """OHLCV candles between dates."""

def get_expiry_list(security_id: str, segment: str) -> list[str]:
    """All available expiries for an underlying."""
```

`core/kite_client.py` (newer, V18G addition for Zerodha — function signatures pending capture in a follow-up session).

### F.4 `merdian_utils.py` (utility layer)

Stable abstractions used by multiple builders:
- Paginated reads (v2 — handles Supabase pagination correctly)
- NIFTY Thursday → Wednesday weekly expiry handling
- Market session detection (PRE_MARKET / MARKET_OPEN / MARKET_CLOSED)
- IST↔UTC conversions

---

## §G — Known gaps in this map

Things this Map does not yet cover comprehensively. Fill in subsequent sessions.

### G.1 Task Scheduler completeness — ✅ RESOLVED (Session 23 audit)

`merdian_reference.json` originally listed 4 Task Scheduler entries; Session 17 reactivation evidence suggested ~13. Session 23 PowerShell audit (Navin) revealed **17 tasks** plus a second-pass action-mapping audit that captured the canonical `Execute + Arguments` for each. Full inventory now lives in `MERDIAN_Deployment_Topology.md` §7.2; this Map's §D.2 points to it as single source of truth.

Three discoveries from the audit became their own follow-ups (filed in Topology §9 questions list):
- Local↔AWS PreOpen run different scripts (dupe-check pending)
- Local↔AWS Post-market run different scripts (dupe-check pending)
- TD-061 pythonw migration partially complete (4/15 candidate tasks already migrated)

### G.2 Kite client function signatures (MEDIUM priority gap)

§F.3 captures Dhan client signatures from V15.1. The newer `core/kite_client.py` (added V18G for Zerodha NIFTY full-chain WebSocket) is not captured. Worth a quick read of the file to populate F.3 sub-section.

### G.3 13-block appendix block schemas (LOW priority gap)

V18 master appendices (V18A–H) use a 13-block structure. The schema of each block (B1 file changes, B2 table changes, etc.) is well-known to current Claude but undocumented in markdown form. If the Master `.docx` archive becomes hard to read, this Map could absorb a B1–B13 schema reference table in a §H section.

### G.4 Signal_snapshots column-by-column reference (MEDIUM priority gap)

`signal_snapshots` is the primary decision record. Its column inventory (especially after ICT additions and `po3_session_bias`) is split across V18F appendix + V18G appendix + V19 §8. A consolidated column reference would belong here as B.3 sub-table.

### G.5 Wrapper script layer — `.bat` and `.ps1` files (NEWLY DISCOVERED, Session 23)

The Task Scheduler audit revealed ~13 `.bat` and `.ps1` wrappers that orchestrate when production Python scripts run on Local. They are not "writes-to-table" production architecture (System Map's primary scope) but they are the operational glue that schedules production architecture. Inventory lives in **Deployment Topology §A.2** (Newly catalogued scripts) — this Map points to it. Consider whether the wrapper layer warrants its own §A.10 here in a future session, or whether keeping it in Topology is the right division.

---

## Update log

| Date | Session | Event |
|---|---|---|
| 2026-05-09 | Session 23 (initial) | Created. Sourced from `merdian_reference.json` (72 files, 36 tables, 4 cron, 4 task entries) + V18/V19 master appendices for cycle pipelines + V15.1 §9.1/9.2 for core abstractions and monitoring schemas. Four known gaps flagged in §G for follow-up sessions. |
| 2026-05-09 | Session 23 (Topology audit follow-up) | Updates after the Deployment Topology Task Scheduler audit (canonical 17-task inventory): §A.1 gained `capture_spot_1m.py` and `capture_spot_1m_v2.py` (production data-capture scripts revealed by audit); §A.5 gained `merdian_watchdog.py`, `watchdog_check.ps1`, `merdian_morning_start.ps1` (operational/supervisor layer); §D.2 reduced to pointer to Topology §7.2 (canonical scheduler inventory); §G.1 marked RESOLVED; §G.5 added documenting the .bat/.ps1 wrapper layer that lives in Topology §A.2. |

---

*MERDIAN System Map — established Session 23, 2026-05-09. Updated inline per Doc Protocol v4 Rule 1 + Rule 9.1. Source authority: `merdian_reference.json` for canonical file paths and statuses; this Map for human-readable architectural narrative and pipeline ordering.*
