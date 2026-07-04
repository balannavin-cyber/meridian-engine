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
| `capture_market_spot_snapshot_local.py` | ✅ | ✅ | Dhan REST `/marketfeed/quote/index` | `market_spot_snapshots` | ACTIVE |
| `capture_index_futures_snapshot_local.py` | ✅ | ✅ | Dhan REST + dynamic contract resolution | `index_futures_snapshots` | ACTIVE — V17E dynamic contract |
| `ws_feed_zerodha.py` | ✅ | ❌ | Zerodha KiteTicker WebSocket (NIFTY full chain) | `option_chain_snapshots` (Zerodha rows) | ACTIVE — Session 13 task registered |
| `ingest_option_chain_local.py` | ✅ | ✅ | Dhan REST option chain | `option_chain_snapshots` (live cadence), `historical_option_chain_snapshots` (HOCS — point-in-time 5m historical archive; S35 cataloguing) | ACTIVE — currently failing 401 on Local (V18A) — name is misleading: writes both live AND historical archive |
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
| `compute_volatility_metrics_local.py` | ✅ | ✅ | `option_chain_snapshots`, India VIX | `volatility_snapshots` | ACTIVE — IV=0 filter, ATM fallback | — compute_volatility_metrics_local.py — S48 FIX: TARGET_TABLE corrected from hardcoded "compute_volatility_metrics" (non-existent, 404 graceful handler) to canonical "volatility_snapshots" per ADR-006. Reads from volatility_snapshots for prior-cycle history. Writes to volatility_snapshots (production, no shadow post-S48). Both AWS + LOCAL fixed. Silent failure for 2+ months due to 404 handler exiting exit_code=0.
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
| `run_ict_htf_zones_daily.py` | ✅ | ❌ | **NEW S29 (TD-061 closure).** Python orchestrator for `MERDIAN_ICT_HTF_Zones_0845` task — replaces `.bat` chain. Runs `build_ict_htf_zones.py --timeframe both` → `--timeframe H` → `generate_pine_overlay.py` in sequence; rc-fold via `max()`; preserves bit-identical banner log format. `sys.executable` ensures pythonw propagation to child subprocesses. | ACTIVE — first scheduled fire 2026-05-15 08:45 IST |
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
| `run_ict_htf_zones_daily.bat` | Pre-S29 bat wrapper for ICT_HTF_Zones_0845 task | **ORPHANED 2026-05-14 (S29 TD-061 closure)** — task now points to `run_ict_htf_zones_daily.py`. Delete in cleanup pass after a week of stability. |
| `run_eod_breadth_refresh.ps1` | Pre-S29 PowerShell wrapper for EOD_Breadth_Refresh task | **ORPHANED 2026-05-14 (S29 TD-061 closure)** — task now points direct to `pythonw.exe run_equity_eod_until_done.py`. Delete in cleanup pass after a week. |
| `run_iv_context_once.ps1` | Pre-S29 PowerShell wrapper for IV_Context_0905 task | **ORPHANED 2026-05-14 (S29 TD-061 closure)** — task now points direct to `pythonw.exe compute_iv_context_local.py`. Delete in cleanup pass after a week. |
| `run_po3_session_bias_once.bat` | Pre-S29 bat wrapper for PO3_SessionBias_1005 task | **ORPHANED 2026-05-14 (S29 TD-061 closure)** — task now points direct to `pythonw.exe detect_po3_session_bias.py`. Delete in cleanup pass after a week. |
| `migrate_to_pythonw.ps1` | One-off S29 migration script — bulk re-register of 18 Task Scheduler tasks to `pythonw.exe` + Hidden + IgnoreNew settings. v2 (after v1 regex bug captured shell redirection metacharacters into `pythonw` arguments). | **ONE-OFF S29 (2026-05-14)** — archive after S29 close commit. Not for ongoing use. v1 abandoned due to regex undercatch. |
| `patch_s29_td_new_i_j.py` | v1 patch script for TD-NEW-I + TD-NEW-J | **ABANDONED S29** — regex undercaught threshold sites + risked docstring breakage. Delete after S29 close commit. Replaced by v2. |
| `patch_s29_td_new_i_j_v2.py` | v2 patch script — applied 2026-05-14 evening | **APPLIED S29** — single-use; keep on disk for evidence trail with backups (`merdian_daily_audit_PRE_S29_TD_NEW_I_J_V2.py`, `capture_spot_1m_v2_PRE_S29_TD_NEW_I_J_V2.py`). |

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
| `market_ticks` | `ws_feed_zerodha.py` (Kite WebSocket; AWS) | `ingest_breadth_from_ticks.py` (last 10 min only) | LIVE — high-rate ephemeral. **CRITICAL RULE (S29 codified):** retention via pg_cron `prune-market-ticks` (jobid 46) every 30 min, 1-hour horizon. Originally jobid 45 (`30 14 * * 1-5`, 2-day horizon, RETIRED 2026-05-14) which failed for 14+ consecutive weekdays causing 62 GB bloat — see `CASE-2026-05-14-breadth-cascade-token-and-bloat.md`. Worst-case DELETE workload now ~1 GB (30 min of accumulation), well inside Postgres statement_timeout. Table was previously absent from System Map B-section despite being a live tape table — the catalog gap obscured the retention-stability dependency. |
| `historical_option_chain_snapshots` (HOCS) | `ingest_option_chain_local.py` (writer; despite name, this is a **point-in-time historical archive**, not the live `option_chain_snapshots` writer); `fill_2026_04_16_breeze_v3.py` (S35 surgical fill, `source='breeze_backfill_s35'`) | `build_ict_primitives.py` (ENH-106 v8 dual-source chain reader — `_prefetch_hocs_for_tuple` reads on post-2026-04-01 retests per `CHAIN_TIER_BOUNDARY_UTC`); ad-hoc cohort analysis | ACTIVE — post-2026-04-01 chain-history canonical (~2.67 GB / 2.67M rows / 41 trading days as of S35); keyed on `symbol` text not `instrument_id` uuid; `ltp` not `close`; 5-min cadence; `run_id` NOT NULL (backfill scripts must set; v3 generates UUID per invocation); `source` text column annotates writer provenance (`ingest_option_chain_local` for ingest cycles; `'breeze_backfill_s35'` for S35 Breeze surgical fill). **Strike-coverage structural limit (TD-S35-NEW-1):** `ingest_option_chain_local` captures ATM±N strikes per cycle; retests with large spot drift can miss held-strike. **Pre-2026-04-01 chain history is in `hist_option_bars_1m` (vendor-sourced) — that table is 54.8M rows of vendor-purchased 1m OHLC data covering pre-Apr-2026 window; ENH-106 v8 routes per-tuple to whichever table covers the anchor.** Cross-refs: ADR-013 PROPOSED (Breeze canonical adoption), ENH-109 PROPOSED (Breeze graduation), TD-S35-NEW-1/2/3, Deployment Topology §1.6. |

### B.2 Computed metrics (5-min cycle outputs)

| Table | Written by | Read by | Status |
|---|---|---|---|
| `gamma_metrics` | `compute_gamma_metrics_local.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE — V18A `gamma_zone` field, raw columns. ENH-80 will add zone-bound columns. |
| `iv_context_snapshots` | `compute_iv_context_local.py` | `build_market_state_snapshot_local.py`, signal builder | ACTIVE — morning via `MERDIAN_IV_Context_0905` |
| `volatility_snapshots` | `compute_volatility_metrics_local.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE |
| `momentum_snapshots` | `build_momentum_features_local.py` | `build_market_state_snapshot_local.py`, signal builder | LIVE — includes `ret_session` (ENH-01). **TD-101 RESOLVED Session 26 (commit `3cb84e2`):** `get_session_open_spot()` was returning oldest 500 rows of unbounded `market_spot_snapshots` query (OI-18 class anti-pattern); inside-loop today-date filter discarded all 500; `ret_session` was NULL on every row 2026-04-17 → 2026-05-10 (3+ weeks ~5,000 signals). Fix: bounded query with `gte("ts", today_start_utc_iso)` + limit=20; threshold 03:35 UTC preserved per ENH-01/V18G regression history. **Live impact:** ENH-55 momentum opposition gate was silent no-op for 24 days; surfaced retrospective evidence falsifying Exp 20 hypothesis (see Assumption Register §D.9). |
| `momentum_snapshots_v2` | `compute_momentum_features_v2_local.py` (manual) | shadow comparison | ACTIVE — manual / shadow only |
| `weighted_constituent_breadth_snapshots` | `build_wcb_snapshot_local.py` | analytics, breadth diagnostic | LIVE |
| `market_state_snapshots` | `build_market_state_snapshot_local.py` | `build_trade_signal_local.py`, analytics | LIVE WITH DEFECT — C-01 open (duplicate rows) |

### B.3 Signals (live decision layer)

| Table | Written by | Read by | Status |
|---|---|---|---|
| `signal_snapshots` | `build_trade_signal_local.py` | outcome engine, analytics, shadow comparison, regret log builder, `merdian_signal_dashboard.py` | LIVE — primary decision record. ICT columns added 2026-04-11 (`patch_signal_ict.py`). `po3_session_bias` added Session 13. **Session 26 changes:** ENH-88 BULL_FVG cluster gate SHIPPED (commit `8407169`) — `raw.enh88_decision` field set to `"ALLOW"` or `"BLOCK"` for every BULL_FVG BUY_CE signal based on 90-min BULL_OB lookback in same table. ENH-55 momentum opposition + alignment bonus DISABLED by env flag (commit `5b94c78`) — default OFF; `cautions` and `reasons` lists no longer carry `ENH-55: Momentum opposition` or `ENH-55: Momentum aligned` entries unless `MERDIAN_ENH55_ENABLED=1`. ENH-53 breadth modifier remains active (different evidence base). |
| `signal_regret_log` | `build_signal_regret_log_v1.py` | analytics, ADR-007 evidence base | ACTIVE — 614 rows V18A baseline. Per ADR-007, the V15.1-spec'd role as threshold-change gate is retired; ongoing diagnostic role continues. |
| `shadow_signal_snapshots_v3` | `build_shadow_signal_v3_local.py` (manual) | shadow comparison | ACTIVE — manual only |

### B.4 ICT layer

| Table | Written by | Read by | Status |
|---|---|---|---|
| `ict_htf_zones` | `build_ict_htf_zones.py`, `build_ict_htf_zones_historical.py` | `detect_ict_patterns.py`, dashboard, Pine overlay | LIVE — ENH-37. **`source_bar_date` semantics differ by timeframe (codified Session 25 from TD-078 closure):** W = week-start Monday date; D = bar's calendar date; 1H = hour bucket date. When debugging "missing zone row" claims on this table, check the timeframe-aware convention before concluding the row is absent. **ADR-005 zone validity model applied Session 26 (TD-079 fix, commit `0731e67`):** D/W OB/FVG `valid_to=NULL` (price-breach only canonical); 1H OB/FVG `valid_to=trade_date+7days` tactical fallback; PDH/PDL date-expire unchanged. `expire_old_zones()` filter widened from `["W","D"]` → `["W","D","H"]`. Backfill revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. Pine 36 → 62 zones (49 HTF + 13 intraday). |
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

### B.10 Operational instrumentation (Session 26)

| Table | Written by | Read by | Status |
|---|---|---|---|
| `dhan_token_probe_log` | `pull_token_from_supabase.py` (post-write probes); ad-hoc operator scripts | `v_dhan_token_probe_today` view; Mon morning verification triplet (P0b S27) | LIVE — Session 26 (TD-080 instrumentation, commit `718ef39`). 12 columns: id, ts_utc, ts_ist, host, script, phase ('pre_write'/'post_write_ltp'/'post_write_optionchain'/'asymmetry_verdict'), endpoint, http_status, latency_ms, token_len, token_prefix, verdict ('OK'/'PARTIAL'/'FAIL'), error_excerpt, notes. Sunday 2026-05-10 smoke test PASS at 20:28 IST: token len=280, both Dhan probes 200 OK, verdict=OK. Mon 2026-05-12 first cron-driven probe is the diagnostic input for TD-080 root-cause investigation. |
| `v_dhan_token_probe_today` | (view, auto-reflects newest rows) | Mon morning verification triplet (P0b S27); operator console for triage | LIVE — Session 26 view. Filter: today's UTC date. ORDER BY ts_utc DESC. Used directly as `SELECT * FROM v_dhan_token_probe_today ORDER BY ts_ist DESC LIMIT 10` for triage. |

---

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

## §A.S26 — Production scripts touched in Session 26

> Lightweight callout per Doc Protocol v4 §1 (System Map update trigger: production scripts changed). Rows in §A.1–§A.5 above are the canonical source for path, reads, writes, called-by, status. This section captures S26-specific change descriptions in one place for the session-history view.

| Script | S26 change | Commit |
|---|---|---|
| `pull_token_from_supabase.py` (AWS) | Extended 50 → 355 lines: atomic .env write with readback verify, post-write probes of Dhan `/v2/marketfeed/ltp` + `/v2/optionchain/expirylist`, audit logging to new `dhan_token_probe_log` table, asymmetry verdict logic. **Note:** AWS does NOT call Dhan `generateAccessToken` — Local does the refresh at 08:15 IST and PATCHes Supabase; AWS pulls from Supabase at 08:35 IST. The S26 instrumentation lives in the AWS-side puller. Backup `_PRE_S26.py` preserved. | `718ef39` |
| `build_ict_htf_zones.py` (Local) | TD-079 ADR-005 zone validity rewrite via `patch_s26_td079_zone_validity.py` 13 surgical replacements AST-validated: D/W OB/FVG `valid_to=None` (price-breach only canonical), 1H OB/FVG `valid_to=str(trade_date+timedelta(days=7))` (tactical fallback), `expire_old_zones()` filter widened `["W","D"]` → `["W","D","H"]`, PDH/PDL date-expiry unchanged. Live rebuild produced 80 zones; backfill SQL revived 18 SENSEX W BEAR_OB/BEAR_FVG zones above 78k from EXPIRED → ACTIVE valid_to=NULL. Pine output 36 → 62 zones (49 HTF + 13 intraday). | `0731e67` |
| `build_trade_signal_local.py` (Local) | Two patches in same file this session. **ENH-88 deploy** (`patch_s26_enh88_deploy.py`): adds `ENH88_LOOKBACK_MIN: int = 90` + `_has_recent_bull_ob(sb, symbol, current_ts_iso, lookback_min=90)` helper after ENH-75 helper anchor; new ENH-88 gate block before `return out, flags` queries `signal_snapshots` for BULL_OB in last 90min with `trade_allowed=True`; ALLOW or BLOCK with three-site sync (action, trade_allowed, out{}); sets `out["raw"]["enh88_decision"]`. BEAR-side anti-clusters not mirrored (per ENH-90 -16.5pp anti-edge). **ENH-55 disable** (`patch_s26_enh55_disable.py`): adds `ENH55_ENABLED: bool = os.getenv("MERDIAN_ENH55_ENABLED", "0").strip() == "1"` after `SIGNAL_V4_ENABLED`; modifies inner condition `if ret_session is not None and abs(ret_session) > 0.0005:` → `if ENH55_ENABLED and ret_session is not None and abs(ret_session) > 0.0005:`. Disables BOTH opposition block AND alignment bonus (same evidence base, symmetric claims falsified together). ENH-53 breadth modifier untouched. Default OFF; reversible via `.env` `MERDIAN_ENH55_ENABLED=1`. | `8407169` + `5b94c78` |
| `build_momentum_features_local.py` (Local) | TD-101 RESOLVED — `get_session_open_spot()` bounded query fix via `patch_s26_td101_ret_session.py`. Old: `supabase_select("market_spot_snapshots", filters={"symbol": symbol}, order_by="ts", desc=False, limit=500)` returns oldest 500 rows of unbounded table; inside-loop today-date filter discards all 500; returns None silently. New: `today_start_utc_iso` derived from `current_ts.astimezone(timezone.utc)` date; `gte("ts", today_start_utc_iso)` filter; limit=20; defense-in-depth date filter inside loop preserved; threshold 03:35 UTC preserved per ENH-01/V18G regression history (catches both 09:05 IST Local PreOpen now-disabled and 09:08 IST AWS PreOpen current anchor). Backup `_PRE_S26_TD101.py` preserved. Same OI-18 class as S25 TD-097 dashboard fix; the audit Session 25 ran (TD-099) didn't reach this writer-side helper because grep was shape-specific to dashboard URL construction. | `3cb84e2` |

**Tables touched Session 26:**
- New: `dhan_token_probe_log` (TD-080 instrumentation; see §B.10 above), `v_dhan_token_probe_today` (view).
- Data update: `ict_htf_zones` — 18 SENSEX W BEAR_OB/BEAR_FVG zones revived from EXPIRED → ACTIVE valid_to=NULL via TD-079 backfill SQL.
- No DDL changes to existing tables.

**Note on `merdian_start.py`:** Unchanged Session 26. Per CLAUDE.md memory, this file remains LOCAL-ONLY (Windows `creationflags=CREATE_NO_WINDOW` + hardcoded Windows paths). Running on AWS still freezes SSM terminal. No S26 work attempts to modify this constraint.

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

The JSON tracks 4; Session 17 reactivation evidence indicates 13 `MERDIAN_*` tasks exist in production. The reference is partial. Known:

| Task | Cadence | Action | Status |
|---|---|---|---|
| `MERDIAN_Market_Tape_1M` | 1-min | run_market_tape_1m.py | DISABLED 2026-04-07 |
| `MERDIAN_Intraday_Supervisor_Start` | Mon-Fri 08:00 + AtLogon | start_supervisor_clean.ps1 | ACTIVE |
| `MERDIAN_Live_Dashboard` | AtLogon | merdian_live_dashboard.py | ACTIVE — PYTHONIOENCODING=utf-8 |
| `MERDIAN_Spot_MTF_Rollup_1600` | Mon-Fri 16:00 IST | run_spot_mtf_rollup_once.bat → build_spot_bars_mtf.py | ACTIVE — Session 9 closure of TD-019/023, ENH-71 instrumented |
| `MERDIAN_ICT_HTF_Zones_0845` | Mon-Fri 08:45 IST | build_ict_htf_zones.py (with `--timeframe H` added Session 13) | ACTIVE — Session 11 extension closure of TD-017 |
| `MERDIAN_IV_Context_0905` | Mon-Fri 09:05 IST | compute_iv_context_local.py | ACTIVE |
| (~7 more) | (TBD) | — | **Gap — see §G.1** |

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

### G.1 Task Scheduler completeness (HIGH priority gap)

`merdian_reference.json` lists 4 Task Scheduler entries; Session 17 reactivation evidence (13 `MERDIAN_*` tasks were disabled and re-enabled) indicates the production reality is ~13 tasks. The other ~9 are not in the JSON. A one-session audit:
```powershell
Get-ScheduledTask -TaskName "MERDIAN_*" | Select TaskName, State, Triggers
```
will produce the canonical list. Update §D.2 with the result.

### G.2 Kite client function signatures (MEDIUM priority gap)

§F.3 captures Dhan client signatures from V15.1. The newer `core/kite_client.py` (added V18G for Zerodha NIFTY full-chain WebSocket) is not captured. Worth a quick read of the file to populate F.3 sub-section.

### G.3 13-block appendix block schemas (LOW priority gap)

V18 master appendices (V18A–H) use a 13-block structure. The schema of each block (B1 file changes, B2 table changes, etc.) is well-known to current Claude but undocumented in markdown form. If the Master `.docx` archive becomes hard to read, this Map could absorb a B1–B13 schema reference table in a §H section.

### G.4 Signal_snapshots column-by-column reference

`signal_snapshots` is the primary decision record. Its column inventory (especially after ICT additions and `po3_session_bias`) is split across V18F appendix + V18G appendix + V19 §8. A consolidated column reference would belong here as B.3 sub-table.

---

## Update log

| Date | Session | Event |
|---|---|---|
| 2026-05-09 | Session 23 | Created. Sourced from `merdian_reference.json` (72 files, 36 tables, 4 cron, 4 task entries) + V18/V19 master appendices for cycle pipelines + V15.1 §9.1/9.2 for core abstractions and monitoring schemas. Four known gaps flagged in §G for follow-up sessions. |
| 2026-05-09 | Session 24 | Added §A.X (Replay layer scripts) and §B.X (Replay tables) per ADR-008. 11 new replay scripts in `C:\GammaEnginePython\replay\` + 10 new `*_replay` Supabase tables. Zero-touch constraint preserved (live scripts physically untouched). |
| 2026-05-10 | Session 26 | **§B.4 ict_htf_zones + signal_snapshots + momentum_snapshots rows annotated** with S26 changes (TD-079 zone validity rewrite, ENH-88 + ENH-55 disable, TD-101 ret_session writer fix). **New §B.10 Operational instrumentation section** for `dhan_token_probe_log` table + `v_dhan_token_probe_today` view (TD-080 instrumentation, S26 commit `718ef39`). **New §A.S26 callout block** lists 4 production scripts touched Session 26 (`pull_token_from_supabase.py` AWS, `build_ict_htf_zones.py` Local, `build_trade_signal_local.py` Local two patches, `build_momentum_features_local.py` Local) with commit hashes + change descriptions. No §A row removals (all underlying scripts remain canonical at same paths). Pipeline diagrams §C unchanged (no orchestration / schedule changes Session 26). |
| 2026-05-10 | Session 25 | §B.4 ict_htf_zones row annotated with timeframe-aware `source_bar_date` semantics (codified from TD-078 closure): W = week-start Monday, D = bar's calendar date, 1H = hour bucket date. Implicit convention in `build_ict_htf_zones.py` made explicit so future debugging of "missing row" claims doesn't waste time. No script index or pipeline diagram changes (S25 was code-light per non-AWS-touch constraint of Phase α Q3 sequencing). MERDIAN_PreOpen Local 09:05 IST task DISABLED via PowerShell (durable); no §A row removal because the underlying script `capture_spot_1m.py` retains capability — only the scheduled invocation was removed. Note for future: Topology §7.2 task inventory next pass should mark `MERDIAN_PreOpen` State=Disabled. |
| 2026-05-24 | Session 35 | **HOCS canonical cataloguing + ENH-106 v8 dual-source reader + ADR-012 v9 SL writer.** **§B.1 expanded** — new row for `historical_option_chain_snapshots` (HOCS) catalogues it as post-2026-04-01 chain-history canonical (~2.67 GB / 2.67M rows / 41 trading days as of S35); writer identified as `ingest_option_chain_local.py` (despite name misleading — also writes the live `option_chain_snapshots`); reader identified as `build_ict_primitives.py` ENH-106 v8 `_prefetch_hocs_for_tuple` on post-Apr-2026 retests per `CHAIN_TIER_BOUNDARY_UTC = 2026-04-01`; strike-coverage structural limit codified (TD-S35-NEW-1 S2); cross-refs to ADR-013/ENH-109/TD-S35-NEW-1/2/3 + Deployment Topology §1.6. **§A.1 `ingest_option_chain_local.py` row updated** — Writes column expanded to clarify dual-write to both `option_chain_snapshots` (live cadence) AND `historical_option_chain_snapshots` (HOCS — point-in-time 5m historical archive); name described as misleading. **New §A.S35 section** — 3 production scripts touched: `build_ict_primitives.py` (4 patches applied via `patch_s35_*.py` — v8 dual-source / v8.1 calendar union / v8.2 RPC / v9 SL writer, 4 backups preserved, AST validated, smoke + single-cell n=5 validation PASS), `ingest_option_chain_local.py` (cataloguing only — no patch; name misleading codification), `fill_2026_04_16_breeze_v3.py` (NEW on MERDIAN AWS — one-shot Breeze surgical fill of 2026-04-16 HOCS gap writing 107,630 rows in 4-5min; v3 hardening UUID `run_id` + real-rows-only success log + SENSEX `stock_code='BSESEN'` per TD-S35-NEW-3; md5 `5eae3849776ec2a6061ed2100ecb0e13`; nano multi-line paste file transfer codified). S35 stale-doc updates table: TD-S34-NEW-4 CLOSED-MECHANICAL (81% post-Apr-2026 retest recovery), ADR-012 IMPLEMENTED (via writer v9). **New §B.S35 section** — 7 schema / data / RPC / index changes: `ict_primitive_outcomes` ADD COLUMN `option_pnl_source TEXT` (chain data tier audit tag) + 5 ADR-012 SL columns (`sl_level`/`sl_buffer_pct`/`sl_triggered_ts`/`sl_exit_prem`/`pnl_with_sl_pct`); writer INSERT-only behavior codified (TD-S35-NEW-4 S3); TRUNCATE + full re-backfill 19,571 outcomes in 2,107s; HOCS Breeze surgical fill 107,630 rows; new RPC `public.get_hocs_distinct_expiries(text)` STABLE function (EXPLAIN ANALYZE 325ms Index Only Scan); new covering index `idx_hocs_symbol_expiry ON (symbol, expiry_date)` ~40 MB (built via direct DB connection with `SET statement_timeout=0` bypassing PostgREST 8s limit). S35 architectural notes section codifies: HOCS as post-2026-04-01 canonical, key columns (`symbol` text not `instrument_id` uuid; `ltp` not `close`; true-UTC `bar_ts` not vendor's IST-mislabeled), `run_id` NOT NULL backfill discipline (silent-lie failure mode without explicit UUID generation), pre-Apr-2026 vendor uncatalogued (TD-S35-NEW-2 S1 — bus-factor-of-one institutional knowledge at risk; catalogue at S36). No pipeline diagram changes §C (no orchestration / schedule changes Session 35 — Breeze invocation was one-shot manual; ENH-109 graduation would add a new MERDIAN AWS cron and trigger §C/§D updates at that time). |
| 2026-05-25 | Session 36 | **TD-S30-CANDIDATE-1 closed-misdiagnosis + ENH-99 SHIPPED (capture-layer resilience).** **New §A.S36 section** — 4 production scripts touched: `gamma_engine_retry_utils.py` (PATCHED via `patch_s36_enh99_v3.py` regex-anchor — new `retry_predicate` kwarg + `[RETRY_BURN_DOWN]` telemetry, backwards-compatible), `ingest_option_chain_local.py` (PATCHED via `patch_s36_enh99_v2.py` — 2 Dhan retry sites bumped to attempts=6/delay=15.0 with `retry_predicate=is_dhan_429`; ~96s budget vs ~60s Dhan quota window), `orphan_run_janitor.py` (NEW Local — env-aware raw HTTP per house convention, int4 duration clamp at `2^31-1`, per-row error tolerant; smoke-fire 22/24 + 2 REPL stragglers = 24 orphans closed), `backfill_gamma_metrics_to_main.py` (CALLED — March-epoch overwrite-recompute 2850 cycles, no patch). **S36 stale-doc updates table:** TD-S30-CANDIDATE-1 CLOSED-MISDIAGNOSIS (writer never regressed, residual was historical raw-rupees window from pre-S27); TD-080 CLOSED via ENH-99 SHIPPED (Components 1+2+3, Mode B DROPPED as upstream-resolved S29). **New §B.S36 section** — 2 tables touched: `gamma_metrics` (2850 cycles overwrite recompute + ~4300 row DELETE on Apr-early-May raw-rupees window + 1 outlier DELETE; post-cleanup single-unit Cr globally) + `script_execution_log` (24 orphan RUNNING rows PATCHed to DATA_ERROR with ORPHAN_RECOVERED notes prefix). **S36 architectural notes section** codifies: int4 `duration_ms` clamp pattern (TD-S36-NEW-4); `chk_exit_reason_valid` closed-set constraint excludes ORPHANED literal; `MERDIAN_Dhan_Token_Refresh` not instrumented to `script_execution_log` (TD-S36-NEW-2); `dhan_token_probe_log` forward-only from 2026-05-10 (TD-S36-NEW-3). New Task Scheduler task `MERDIAN_Orphan_Janitor` (weekly Mon-Fri 09:14 IST, Hidden + IgnoreNew + 5min limit) catalogued separately in Deployment Topology §7.2; task count 19 → 20. No pipeline diagram changes §C (no orchestration / schedule changes affecting the 5-min runner). |
| 2026-05-29 | Session 40 | **TD-S37-01 CLOSED via view-tau patch + Marketview v4 atomic-card redesign + AWS deploy pipeline established + v_max_pain_by_strike view created + update_parameter RPC bug DISCOVERED+FIXED same-session.** **New §B.4 view: `v_max_pain_by_strike`** — long-format-aware DDL deployed to Supabase via `https://supabase.com/dashboard/project/kilmcowcikwdhvdxwofi/sql/new` SQL editor; pivots `option_chain_snapshots` long-format (one row per strike+option_type with single `oi` column) to wide format via `MAX(CASE WHEN option_type='CE' THEN oi END)` aggregation; computes per-candidate-strike total writer pain via `Σ GREATEST(strike-K, 0) × ce_oi + Σ GREATEST(K-strike, 0) × pe_oi`; identifies max-pain strike per symbol via `ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY total_pain ASC)`; classifies sides as `'PE_SIDE'` / `'CE_SIDE'` / `'MAX_PAIN'`; granted SELECT to anon (consumed by Marketview Max Pain card). Verified post-deploy: NIFTY max_pain=23,900 (235 candidate strikes), SENSEX max_pain=76,000 (188 candidate strikes) — both align with spot levels (NIFTY 23,906 / SENSEX 75,933 at S40 close) per typical near-expiry max-pain magnetization. **`merdian_parameters` schema fix:** `ALTER TABLE public.merdian_parameters ALTER COLUMN valid_to DROP DEFAULT;` applied via Supabase SQL editor — removes `DEFAULT now()` clause that Lovable auto-scaffold added; under PostgreSQL transaction-time semantics `now()` returns identical timestamps across all calls within one transaction, causing `update_parameter()` RPC to violate strict `chk_valid_from_to (valid_to > valid_from)` CHECK constraint on every INSERT; remediated and verified via 0.30→0.25→0.30 round-trip with clean temporal chain (3 active rows with proper temporal sequence post-fix). Codified as TD-S40-NEW-2 DISCOVERED-CLOSED-SAME-SESSION + D.22.1 (Lovable temporal-immutable column DEFAULT audit pattern). **New §A.S40 section** — 1 production script + 4 new artifacts: `build_ict_htf_zones.py` ENH-81 views (`v_gex_strike_pin_zone` + `v_gex_strike_accel_zone`) PATCHED via `patch_s40_enh83_view_tau_rewrite.py` — replaces hardcoded `tau_used = 0.30` with runtime `get_parameter_num('pin.tau.'||symbol)` lookup per ADR-016 contract; both DDLs re-applied via Supabase SQL editor; smoke-fire verified `tau_used = 0.30` post-rewrite for NIFTY + SENSEX (closes TD-S37-01 hardcoded τ in ENH-81 views from S37 P0 carry-forward). Cosmetic fix S40: initial patch script had cp1252-unsafe Unicode chars (`→`/`—`) in print() statements crashing under PowerShell `Tee-Object`; replaced with ASCII; 0 cp1252-unsafe print() statements remain (TD-S40-NEW-1 S4 RESOLVED same-session). **New AWS clone path `/home/ssm-user/meridian-connect`** established as Marketview build source — fresh `git clone https://github.com/balannavin-cyber1/meridian-connect.git` on AWS EC2 `i-0878c118835386ec2`; future deploys 3-line: `cd ~/meridian-connect && git pull && npm install && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx`; uses `npm install` not `npm ci` because Lovable doesn't commit `package-lock.json`. Verified deploy at S40: HTTP 200 at `http://13.63.27.85/marketview`; v4 atomic-card layout rendering live Supabase data with degraded-empty-state handling for writer-side gaps (`gamma_metrics.vix` NULL → "VIX not exposed"; `market_breadth_intraday.wcb` column absent → "data unavailable"; `gamma_metrics.pin_risk_score` absent → "no pin-risk data"). **Marketview v4 atomic-card layout codified as design pattern** (D.22.2) — replaces single Hero rollup with single-metric cards; Narrative modal triggered from header link carries the prose summary. **Stacked by-strike charts** (D.22.3) — Positioning + Max Pain stacked full-width (not side-by-side) for shared-strike-axis cross-read (max γ 24,050 vs max pain 23,900 at 100pt gap visible as vertical alignment). New artifacts staged: `marketview_v4_mockup.html` + `marketview_v4_render.png` (4-iteration mockup arc v1→v4), `lovable_build_prompt_marketview_v4.md` (515-line comprehensive build spec with embedded SQL DDLs for v_max_pain_by_strike + per-card Supabase wiring + 7-phase incremental pasting option), `lovable_correction_prompt.md` (column-mapping correction prompt — Lovable column-name guesses corrected post-build: `net_dealer_gamma_cr` → `net_gex`, regime value-normalization `LONG_GAMMA → POSITIVE_γ`, `atm_straddle_premium` → `straddle_atm`, derive max-γ from `gex_strike_snapshots` aggregation, `pin_probability` derived as `100 - expansion_probability`, IV skew uses `option_chain_snapshots.iv` with long-format pivot). **No pipeline diagram changes §C** (S40 was view-tau patch + frontend redesign + AWS deploy pipeline + Supabase view creation; no orchestration / schedule changes affecting the 5-min runner). **TD-S40-NEW-3 filed S2:** TradingView Pine overlay extension for PIN + Accel zones — `generate_pine_overlay.py` (505 lines, currently ICT-only); ~30-40 min to extend with `box.new()` blocks reading from `v_gex_strike_pin_zone` + `v_gex_strike_accel_zone`; deferred S42+. |

---

| 2026-06-12 / 2026-06-16 | Session 53–54 | **Crontab / orchestration recovery + ingest cadence change + first-full-day audit.** S53: dropped `SHELL=/bin/bash` directive root-caused the total capture/compute blackout (cron defaulted to dash; every `source .env` chain died silently) — SHELL line restored; 4 run_ingest.sh lines reconstructed (unquoted `bash run_ingest.sh NIFTY/SENSEX FULL` form); 2 futures cron lines commented (SyntaxError 246/253 — futures DARK); volatility writer insert→upsert(on_conflict=symbol,ts) commit cd98a87. S54: ingest 04–09 UTC minute field `30,35,40,45,50,55`→`*/5` (NEW-4 — closes :00–:29 hole; doubles Dhan calls 6→12/hr 04–09). Audit of first full post-fix day (2026-06-15): capture CLEAN (spot 370/370; option_chain 68 distinct-min/symbol dense `*/5`); 84 PIPELINE COMPLETE / 0 FAILED; upsert held. **One new bug isolated:** SENSEX compute (volatility_snapshots + gamma_metrics + market_state_snapshots, identical counts) silently under-writes ~½ of cycles — NIFTY 44 / SENSEX 23 distinct-ts/day despite 68 chain-ts/hr captured each; mechanism is in the compute write path / orchestrator per-symbol loop, not data; surviving SENSEX rows carry correct ts (rules out ts-merge collapse). TD-S54-NEW-1 (S1), code trace pending. Cross-refs: tech_debt.md TD-S53/S54-NEW-*; merdian_reference.json v34; MERDIAN_Deployment_Topology.md S53–54 row. |

| 2026-07-04 | Session 64 | **ENH-116 Ambient Environment Intelligence BUILT + DEPLOYED end-to-end + Marketview v5 six-page terminal + public TLS/Google-auth domain.** New Supabase surfaces: `market_environment_snapshots` (nightly four-lens verdict store — L1 gamma-persistence / L2 price-vs-breadth / L3 participant tilt [ADR-018 D2 recency-guarded] / L4 macro NULL; reconcile v2 verdict; `regime_conditional_note` Phase-B receipt; `session_prior` relate-line), `expiry_outcomes` (65-row retroactive seed 29 NIFTY / 36 SENSEX, forward-accruing, seed all `ambient_regime=RANGE`), view `v_expiry_base_rates` (grouped (ambient_regime, lens_alignment, expiry_type) → pinned/broke rates + N + dominant break, N-floored). New engine writers: `compile_market_environment_local.py` (post-market compiler), `relate_ambient_to_open_local.py` (pre-market reconciler, idempotent), `backfill_expiry_outcomes.py` (seed), `accrue_expiry_outcomes.py` (forward labeler) — all three loop scripts `ExecutionLog`-instrumented to `script_execution_log` / `v_script_execution_health_30m`. ENH-116 crons on MERDIAN AWS: compile `0 16`, accrue `15 16`, relate `55 3` (Mon–Fri). Carry-in commits: ENH-07A rate-floor `21b08d9`; ICT HTF zones regen `62cd2de` (81 zones). Marketview v5 (meridian-connect) restructured into a left-rail six-page terminal (Home / Positioning / Max Pain / Breadth / Structure / Expiry Memory) + ops sections, global NIFTY/SENSEX toggle, 60s ticker, max-pain ±20, Net Dealer γ intraday. TD-S62-NEW-2 RESOLVED (SENSEX 2026-01-19 concentration 375/375, 0 null). Engine HEAD `61ab702` AWS-synced. No new ADR; no new TD. Cross-refs: Deployment Topology §S64 (crons + domain/TLS/oauth2-proxy). |

*MERDIAN System Map — established Session 23, 2026-05-09. Last updated Session 64, 2026-07-04 (§S64 — ENH-116 Ambient Environment Intelligence built + deployed end-to-end [tables `market_environment_snapshots` + `expiry_outcomes` + view `v_expiry_base_rates`; four writers; three AWS crons] + Marketview v5 six-page terminal + public TLS/Google-auth domain marketview.meridianalpha.in). Previous Session 63, 2026-07-02 (§S63 — SENSEX `compute_flip_level` fix deployed `dc63bb3` + ENH-115 P1 FII/DII participant-positioning writer/backfill/cash/cron LIVE + ENH-07 A Phase-2 commits documented). Previous Session 54, 2026-06-16 (S53–S54 crontab/orchestration recovery + ingest `*/5` + first-full-day audit isolating SENSEX compute under-write TD-S54-NEW-1); previous Session 40, 2026-05-29 (TD-S37-01 closed via view-tau patch + Marketview v4 atomic-card redesign + AWS deploy pipeline established + `v_max_pain_by_strike` view created + `update_parameter` RPC `chk_valid_from_to` bug DISCOVERED+FIXED same-session via `valid_to DROP DEFAULT`). Previous: Session 36, 2026-05-25 (TD-S30-CANDIDATE-1 closed-misdiagnosis + ENH-99 SHIPPED capture-layer resilience). Updated inline per Doc Protocol v4 Rule 1 + Rule 9.1. Source authority: `merdian_reference.json` for canonical file paths and statuses; this Map for human-readable architectural narrative and pipeline ordering.*

---

## §A.X — Replay layer (`C:\GammaEnginePython\replay\`) — added Session 24, 2026-05-09

Built per ADR-008 zero-touch constraint. This is a sibling tree to the live scripts; NOT a fork or set of monkey-patches. Live scripts physically untouched. All replay scripts at `C:\GammaEnginePython\replay\`. Operator-invoked only — no Task Scheduler entries.

| Script | Purpose | Reads | Writes | Called by |
|---|---|---|---|---|
| `replay_clock.py` | UTC/IST constants, `parse_replay_ts()`, `replay_today_ist()`, `to_iso_utc()`, `assert_outside_market_hours()` (08:00-16:30 IST weekday block); 12/12 self-tests | — | — | All replay scripts (import only) |
| `replay_execution_log.py` | Mirror of `core/execution_log.py` with table → `script_execution_log_replay`, host=`replay`, atexit hook preserved | `script_execution_log_replay` (PATCH for set_symbol) | `script_execution_log_replay` (INSERT/PATCH) | All replay scripts |
| `replay_chain_reconstructor.py` | Reconstruct `option_chain_snapshots_replay` + `market_spot_snapshots_replay` for a date from hist_*; computes IV via inverse Black-Scholes Newton-Raphson; with TD-087 5h30m subtract on read for option bars + TD-094 OI lift from live `option_chain_snapshots` per ±150s match window | `hist_spot_bars_1m`, `hist_option_bars_1m`, `instruments`, live `option_chain_snapshots` (OI lift only) | `option_chain_snapshots_replay`, `market_spot_snapshots_replay` | `replay_runner_for_date.py` (Phase 4 orchestrator); manual CLI invocation |
| `replay_compute_gamma_metrics.py` | Mirror of `compute_gamma_metrics_local.py` | `option_chain_snapshots_replay` (filter by run_id) | `gamma_metrics_replay` | Orchestrator; manual `--replay-ts --run-id --symbol` |
| `replay_compute_volatility_metrics.py` | Mirror of `compute_volatility_metrics_local.py`; replaces `fetch_india_vix()` with `india_vix_daily` historical close | `option_chain_snapshots_replay`, live `india_vix_daily` (history), `volatility_snapshots_replay` (prior cycles) | `volatility_snapshots_replay` | Orchestrator; manual `--replay-ts --run-id --symbol` |
| `replay_build_momentum_features.py` | Mirror of `build_momentum_features_local.py`; cycle_ts from `--replay-ts` | `market_spot_snapshots_replay`, `gamma_metrics_replay`, `momentum_snapshots_replay` (prior session_vwap), live `market_breadth_intraday` (filtered by replay_date) | `momentum_snapshots_replay` | Orchestrator; manual `--replay-ts --symbol` |
| `replay_build_market_state_snapshot.py` | Mirror of `build_market_state_snapshot_local.py`; consolidator | `gamma_metrics_replay`, `volatility_snapshots_replay`, `momentum_snapshots_replay` (`ts <= replay_ts` semantics), live `market_breadth_intraday`, live `weighted_constituent_breadth_snapshots` | `market_state_snapshots_replay` | Orchestrator; manual `--replay-ts --symbol` |
| `replay_detect_ict_patterns_runner.py` | Mirror of `detect_ict_patterns_runner.py`; `bar_ts < replay_ts` strict; skips hourly 1H zone rebuild (already in live ict_htf_zones for replay_date) | `hist_spot_bars_1m` (filtered `bar_ts < replay_ts`), live `ict_htf_zones` (filtered by replay_date), `ict_zones_replay`, `market_state_snapshots_replay` (atm_iv lookup), `option_chain_snapshots_replay` (expiry lookup), live `capital_tracker` (current state, accepted) | `ict_zones_replay` (new patterns + breach updates + Kelly lots) | Orchestrator; manual `--replay-ts --symbol` |
| `replay_compute_options_flow.py` | Mirror of `compute_options_flow_local.py`; CLI changed to `--replay-ts --symbol --run-id` per orchestrator pattern | `option_chain_snapshots_replay` (filter by run_id) | `options_flow_snapshots_replay` | Orchestrator; manual `--replay-ts --run-id --symbol` |
| `replay_build_trade_signal.py` | Mirror of `build_trade_signal_local.py`; ALL gates preserved exactly (ENH-53/55/76/77/78, DTE, VIX-elevated, power-hour using `replay_ts.astimezone(IST).hour`, LONG_GAMMA, NO_FLIP, signal_v4); ICT enrichment from `ict_zones_replay`; PO3 from live `po3_session_state`; ENH-06 capital from live `capital_tracker` | `market_state_snapshots_replay`, `options_flow_snapshots_replay`, `ict_zones_replay`, live `po3_session_state` (filtered by replay_date), live `capital_tracker` | `signal_snapshots_replay` | Orchestrator; manual `--replay-ts --symbol` |
| `replay_runner_for_date.py` | Phase 4 orchestrator. File lock at `replay/runtime/replay.lock`; OOH guard at entry; TRUNCATE 9 `_replay` tables (preserves `script_execution_log_replay` audit); reconstruct chain + spot via `replay_chain_reconstructor.reconstruct()`; for each of 76 boundaries iterate scripts in V19 §5.2 order PER BOUNDARY (gamma → volatility → momentum → market_state → ICT → options_flow → signal); subprocess.run per script; per-script success-rate matrix at end. CLI: `replay_date YYYY-MM-DD [--first-n-boundaries N] [--skip-truncate] [--skip-reconstruct]` | All `_replay` tables (TRUNCATE), reads via subprocess'd replay scripts | All `_replay` tables (writes via subprocess'd replay scripts) | Operator manual; never on cron/scheduler |

**Status as of S24 close:** Phase 4b validated full-day on 2026-05-07 — 1056/1064 invocations (99.2%) succeeded in 5009s. ENH-95 candidate filed for in-process orchestrator optimization (~85 min → 10-15 min estimated, deferred until first what-if experiment campaign demonstrates need). Replay is operator-invoked only; no scheduled runs.

**Migration file:** `C:\GammaEnginePython\replay\migrations\001_create_replay_tables.sql` — applied 2026-05-09.

---

## §B.X — Replay tables (`*_replay` mirrors) — added Session 24, 2026-05-09

Created Session 24, 2026-05-09 via SQL migration `replay/migrations/001_create_replay_tables.sql`. All 10 tables created with `CREATE TABLE LIKE <live_table> INCLUDING ALL` — schema parity with live, separate row spaces. No views, no triggers. TRUNCATEd at start of every full-day replay orchestrator run except `script_execution_log_replay` which accumulates as audit.

| Table | Mirrors | Purpose |
|---|---|---|
| `option_chain_snapshots_replay` | `option_chain_snapshots` | Reconstructed chain rows (OHLC + IV via Black-Scholes + OI lifted from live per TD-094) |
| `market_spot_snapshots_replay` | `market_spot_snapshots` | Reconstructed spot rows from `hist_spot_bars_1m` at 5-min boundaries |
| `gamma_metrics_replay` | `gamma_metrics` | Replay gamma compute output (regime, gamma_zone, flip_level, net_gex, straddle_atm) |
| `volatility_snapshots_replay` | `volatility_snapshots` | Replay volatility compute output; VIX sourced from `india_vix_daily` historical close (replaces live `fetch_india_vix()` network call) |
| `momentum_snapshots_replay` | `momentum_snapshots` | Replay momentum features (ret_5m/15m/30m/60m/session, vwap_slope, atm_straddle_change, momentum_regime). 5-min vs 1-min spot granularity vs live is a documented divergence per ADR-008. |
| `market_state_snapshots_replay` | `market_state_snapshots` | Replay 6-component JSONB state (gamma_features + breadth_features + volatility_features + momentum_features + wcb_features + spot/expiry context) |
| `ict_zones_replay` | `ict_zones` | Replay ICT pattern detection output (intraday zones with breach status + Kelly tier lots). Requires orchestrator boundary sequence to reproduce live behavior — single-boundary ad-hoc invocations under-detect because patterns whose anchor bar is outside 30-bar lookback are missed. |
| `signal_snapshots_replay` | `signal_snapshots` | Replay signal-builder output — apex of pipeline; this is the what-if comparison target. Per ADR-008 §"What 'what-if experiment' means", baseline replay snapshot is preserved (CTAS or CSV) before modified-code re-run, then SQL-diffed. |
| `options_flow_snapshots_replay` | `options_flow_snapshots` | Replay options flow — PCR, skew_regime, flow_regime, ce/pe vol_oi ratios per ATM±5 window |
| `script_execution_log_replay` | `script_execution_log` | Replay audit trail; host='replay' on every row; preserved across runs (NOT truncated by orchestrator) so audit history of every experiment is retained automatically. Same ENH-72 write-contract semantics as live ExecutionLog. |

**Permitted live reads from replay code (immutable historical reference per ADR-008):** `instruments`, `hist_spot_bars_1m`, `hist_option_bars_1m`, `india_vix_daily`, `option_chain_snapshots` (for OI lift only), `market_breadth_intraday`, `weighted_constituent_breadth_snapshots`, `ict_htf_zones`, `po3_session_state`, `capital_tracker`. **Live writes from replay code: PROHIBITED architecturally** (replay scripts only address `*_replay` table names; constraint is structural, not a runtime check).

---

## §A.S29 — Production scripts touched in Session 29

> Per Doc Protocol v4 §1 (System Map update trigger). S29 had two halves: (1) firefighting on 2026-05-14 (operational + 2 production code patches + 1 new orchestrator + multiple Task Scheduler config updates), (2) backfill/dashboard build work 2026-05-14→2026-05-16 (vol_analytics backfill, Phase 0b tests, gamma_metrics backfill, market view dashboard).

### S29 firefighting changes (2026-05-14)

| Change | File | Detail |
|---|---|---|
| **NEW orchestrator** | `run_ict_htf_zones_daily.py` | Python orchestrator replacing pre-S29 `.bat` for `MERDIAN_ICT_HTF_Zones_0845`. Calls `build_ict_htf_zones.py --timeframe both`, `--timeframe H`, `generate_pine_overlay.py` via subprocess; rc-fold via `max(rc_wd, rc_h, rc_pine)`; banner format preserved bit-identical. `sys.executable` ensures pythonw propagation. Registered in §A.4. |
| **Code patch (TD-NEW-I)** | `merdian_daily_audit.py` | Threshold reductions: `spot_bars_per_symbol_min: 370 → 365`, `market_spot_snapshots_per_symbol: 370 → 365`. Resolves spurious FAIL on 98% coverage days. Patch via `patch_s29_td_new_i_j_v2.py`; backup `merdian_daily_audit_PRE_S29_TD_NEW_I_J_V2.py`. |
| **Code patch (TD-NEW-J = TD-083)** | `capture_spot_1m_v2.py` | Docstring L36 + call-site L346: `'OUTSIDE_MARKET_HOURS'` → `'OFF_HOURS'` (matches `chk_exit_reason_valid` closed-set constraint). Eliminates daily false-alarm CRASH rows from pre/post-market firings. Backup `capture_spot_1m_v2_PRE_S29_TD_NEW_I_J_V2.py`. |
| **Task Scheduler config** | 9 tasks re-registered to pythonw + 18 tasks settings-hardened | See Topology §7.2 for the full 19-task state table. TD-061 + TD-063 RESOLVED. Backups under `backups\scheduler\20260514_184211\` + `\20260514_190443\`. |
| **Migration tooling (one-off)** | `migrate_to_pythonw.ps1` | 272-line PowerShell to bulk re-register tasks. v2 (after v1 regex captured shell redirection metacharacters). Filed in §A.9 as one-off; archive after S29 close commit. |

### S29 build changes (2026-05-14 → 2026-05-16)

| Change | File | Detail |
|---|---|---|
| **NEW backfill** | `backfill_volatility_snapshots.py` | Full-year `volatility_snapshots` backfill from `hist_atm_option_bars_5m` + `hist_spot_bars_5m` with inverse-BS IV solve. Stage 1 of Phase 0b prep. 19,520 rows written. |
| **NEW backfill** | `backfill_vol_analytics.py` | Stage 2: `vol_analytics` regime classification from backfilled `volatility_snapshots`. 24,758 rows written. Regime mix: LOW 38.1%, COMPRESSED 32.7%, FAIR 15.1%, HIGH 14.1%. |
| **NEW analysis** | `phase0b_rr_conditional_wr.py` | Phase 0b P7 test — joins `hist_pattern_signals` × `vol_analytics` × `hist_atm_option_bars_5m`. Verdict: **FAIL** on ADR-002 v2 P7 4-way regime gate. χ²=1.56, p≈0.30 across regimes. |
| **NEW analysis** | `phase0b_compressed_veto.py` | Salvage test — COMPRESSED-veto binary. Verdict: **FAIL on power** (right direction, variance dominates). Bootstrap CI [-3.36, +17.69]pp includes zero. |
| **NEW analysis** | `phase0b_p5_pinned_proxy.py` | Proxy P5 PINNED test. Initial run constrained by gamma_metrics sparsity (N=3 attributed); pending re-run on backfilled gamma_metrics cohort. |
| **NEW backfill** | `backfill_gamma_metrics_to_main.py` | Full-year `gamma_metrics` backfill from `hist_option_bars_1m` + `hist_spot_bars_1m`. Reimplements live writer math (TD-NEW-2 Parts A+B + TD-NEW-3 explicit citations to commit `241f943`). Unblocked by new DB index `ix_hist_option_bars_1m_bar_ts_strike` (created S29). |
| **NEW dashboard** | `market_view.html` | VRDNation-replica IV view — Plus Jakarta Sans + JetBrains Mono, Chart.js, DTE pill selector 0-6, IV badge, trading insights. |
| **NEW data builder** | `build_straddle_premium_data.py` | Generates `market_view_data.json` for the dashboard. |

### S29 stale-doc updates

| Item | Before | After |
|---|---|---|
| TD-094 ("`hist_option_bars_1m.oi` is 0 — S22 backfill broken via Kite limitation") | Active stale | **REOPENED FOR RESTATEMENT** — vendor data replaced S22's broken Kite backfill; OI populated 99.9% (verified S29 query: avg ~1M, max 66M across 12 months). TD-094 reclassified at S29 close as "stale documentation, vendor data healthy". Unblocks all gamma-context Phase 0b dimensions (P1 LONG_GAMMA, P3 flip_distance, P5 PINNED, ENH-80 per-strike GEX). |

---

## §B.S29 — Tables touched in Session 29

| Change | Table | Detail |
|---|---|---|
| **CRITICAL_RULE update** | `market_ticks` | Retention cron migrated jobid 45 → jobid 46 (`*/30 * * * 1-5`, 1-hour horizon). See §B.1 entry. |
| **Backfill writes** | `volatility_snapshots` | +19,520 rows S29 backfill (Apr 2025 → Mar 2026) |
| **Backfill writes** | `vol_analytics` | +24,758 rows S29 backfill |
| **Backfill writes** | `gamma_metrics` | Full-year backfill in progress at S29 close; ~29,437 pre-existing + new from full-year run |
| **New DB index** | `hist_option_bars_1m` | `CREATE INDEX ix_hist_option_bars_1m_bar_ts_strike ON hist_option_bars_1m (bar_ts, strike, option_type)` — created via direct DB connection with `SET statement_timeout=0` (PostgREST 8s timeout doesn't apply). Unblocks per-cycle indexed lookups for gamma backfill. |

---

## §A.S35 — Production scripts touched in Session 35

| Change | Script | Detail |
|---|---|---|
| **PATCHED** | `build_ict_primitives.py` (Local) | Four S35 patches applied via `patch_s35_*.py`: (1) `patch_s35_enh106_v8_dual_source.py` — adds `CHAIN_TIER_BOUNDARY_UTC = 2026-04-01`, `_source_tier()` + `_prefetch_hocs_for_tuple()` helpers, rewrites `_prefetch_chain_for_primitives` to route per-tuple by anchor timestamp; (2) `patch_s35_enh106_v8p1_expiry_calendar_union.py` — `_load_expiry_calendar` UNIONs vendor `hist_option_bars_1m.expiry_date` + HOCS expiries via new RPC; (3) `patch_s35_enh106_v8p2_hocs_expiries_rpc.py` — swaps PostgREST DISTINCT pagination for direct RPC call `get_hocs_distinct_expiries(text)`; (4) `patch_s35_adr012_v9_sl_writer.py` — adds `SL_BUFFER_PCT_DEFAULT = 0.005` constant, 5 `OutcomeRow` SL fields (`sl_level`, `sl_buffer_pct`, `sl_triggered_ts`, `sl_exit_prem`, `pnl_with_sl_pct`), SL evaluation block in `compute_retest_atm_pnl` walking aggregated 5m bars from `first_retest_ts + 5min` through 15:25 IST EOD, upsert plumbing for 5 new columns. 4 backups preserved: `build_ict_primitives_PRE_S35.py`, `_PRE_S35_v8p1.py`, `_PRE_S35_v8p2.py`, `_PRE_S35_v9.py`. AST validated pre+post each patch. Smoke test PASS after v9. Single-cell n=5 validation on 2026-05-14 NIFTY M5 cohort confirms BEAR SL exits 13-14pp better than held-to-EOD. |
| **CALLED** | `ingest_option_chain_local.py` (Local + AWS) | Existing script — no patch; S35 cataloguing only. Name is misleading: writes both `option_chain_snapshots` (live cadence — ATM±N strikes per cycle) AND `historical_option_chain_snapshots` (HOCS — point-in-time 5m historical archive that is the post-2026-04-01 chain-history canonical). Strike-coverage structural limit (TD-S35-NEW-1 S2): retests with large spot drift can miss held-strike at retest moment. Recovery requires writer widening or ADR-013 Breeze canonical adoption. |
| **NEW backfill** | `fill_2026_04_16_breeze_v3.py` (MERDIAN AWS) | One-shot surgical backfill of 2026-04-16 chain coverage gap in HOCS using ICICI Direct Breeze API from MERDIAN AWS (SEBI static-IP whitelist required Elastic IP `13.63.27.85`). 107,630 rows written (NIFTY 61,899 + SENSEX 45,731) `source='breeze_backfill_s35'` in 4-5min wallclock. v3 hardening: UUID `run_id` per invocation (HOCS NOT NULL); real-rows-only success log (v1/v2 silently lied via accumulator state); symbol-scoped pre-flight; SENSEX `stock_code='BSESEN'` empirically discovered via 6-variant probe per TD-S35-NEW-3. md5 `5eae3849776ec2a6061ed2100ecb0e13`. File transfer to MERDIAN AWS used nano multi-line paste (base64 single-line exceeded SSM terminal buffer ~4KB). |

### S35 stale-doc updates

| Item | Before | After |
|---|---|---|
| TD-S34-NEW-4 (post-2026-04-01 chain coverage gap in `hist_option_bars_1m`) | Filed S34 OPEN — vendor stopped delivering | **CLOSED-MECHANICAL S35** — diagnosed as two-tier architecture: pre-Apr-2026 vendor `hist_option_bars_1m` + post-Apr-2026 MERDIAN-ingest `historical_option_chain_snapshots` (HOCS). ENH-106 v8 dual-source reader routes per-tuple by 2026-04-01 UTC boundary; 81% post-Apr-2026 retest recovery on zone-primitive denominator after v8 + Breeze 2026-04-16 surgical fill. Structural residual 75 attributed to TD-S35-NEW-1 HOCS strike-coverage limit. |
| ADR-012 (spot-anchored SL doctrine) | ACCEPTED S34 (n=7 foundation) — writer-extension pending | **IMPLEMENTED S35** via writer v9 patch (`patch_s35_adr012_v9_sl_writer.py`); 5 schema columns added; SL evaluation in `compute_retest_atm_pnl`; full validation cohort gated on S36 TRUNCATE + full recompute. |

---

## §B.S35 — Tables, RPCs, and indexes touched in Session 35

| Change | Object | Detail |
|---|---|---|
| **Schema add** | `ict_primitive_outcomes` | `ADD COLUMN option_pnl_source TEXT` — chain data tier audit tag for ENH-106 v8 dual-source reader. Values: `'merdian_hist_5m'` (HOCS-sourced post-Apr-2026), `'hist_option_bars_1m'` (vendor-sourced pre-Apr-2026), or NULL (no option PnL computed). DDL: `20260524_enh106_v8_option_pnl_source.sql`. |
| **Schema add** | `ict_primitive_outcomes` | 5 ADR-012 SL columns: `sl_level NUMERIC`, `sl_buffer_pct NUMERIC`, `sl_triggered_ts TIMESTAMPTZ`, `sl_exit_prem NUMERIC`, `pnl_with_sl_pct NUMERIC`. BULL: trigger close < zone_low × (1 − X); BEAR: trigger close > zone_high × (1 + X); X = `SL_BUFFER_PCT_DEFAULT = 0.005` per ADR-012 §3. Level primitives (PDH/PDL/PWH/etc.) skip SL by design (no zone bounds — NULL); `pnl_with_sl_pct` falls back to `option_pnl_eod` on no-trigger. DDL: `20260524_adr012_v9_sl_columns.sql`. |
| **Writer behavior** | `ict_primitive_outcomes` | TD-S35-NEW-4 S3 codification: `build_ict_primitives.py upsert_outcomes` is INSERT-only — schema column adds do NOT backfill existing rows. New columns populate only on freshly-inserted rows; existing rows show NULL until explicitly DELETE'd or full-table TRUNCATE'd before recompute. |
| **Data writes** | `ict_primitive_outcomes` | TRUNCATE + full re-backfill 19,571 rows (NIFTY 8,925 + SENSEX 10,646) in 2,107s wallclock. All `option_pnl_source` populated (no NULLs on chain-tier-eligible retests); ADR-012 SL columns populated on zone-primitive retests, NULL on level primitives by design. |
| **Data writes** | `historical_option_chain_snapshots` (HOCS) | 107,630 INSERT rows from S35 Breeze 2026-04-16 surgical fill (NIFTY 61,899 + SENSEX 45,731) with `source='breeze_backfill_s35'`. Pre-existing rows untouched. Coverage post-fill: 41 trading days (2026-03-16 → 2026-05-22) including 2026-04-16 single-day outage previously empty. |
| **New RPC function** | `public.get_hocs_distinct_expiries(_symbol text)` | `STABLE` function returning `TABLE(expiry_date date)`. Created to replace ENH-106 v8.1's PostgREST DISTINCT pagination over 2.67M HOCS rows (wrong query shape — pagination finding 10 distinct values across 2.67M is O(N) when DB-side DISTINCT can be O(log N) via covering index). EXPLAIN ANALYZE 325ms / Index Only Scan after v8.2 index build. DDL: `20260524_enh106_v8p2_hocs_distinct_expiries_rpc.sql`. |
| **New DB index** | `historical_option_chain_snapshots` | `CREATE INDEX idx_hocs_symbol_expiry ON historical_option_chain_snapshots (symbol, expiry_date)` covering index, ~40 MB. Built via direct DB connection with `SET statement_timeout=0` (PostgREST 8s timeout doesn't apply on 2.67M-row table). Enables Index Only Scan for `get_hocs_distinct_expiries` RPC. DDL: `20260524_enh106_v8p2_hocs_expiry_index.sql`. |

### S35 architectural notes

- **HOCS is the post-2026-04-01 chain-history canonical**, not `hist_option_bars_1m` (which stopped at 2026-03-31). ENH-106 v8 dual-source reader routes per-tuple by `CHAIN_TIER_BOUNDARY_UTC = 2026-04-01 UTC` — choice was made because (a) vendor delivery to `hist_option_bars_1m` stopped exactly at that boundary, and (b) MERDIAN-ingest started building HOCS in earnest from 2026-03-16, providing 2-week overlap window for any future cross-source audit.
- **HOCS key columns:** `symbol` (TEXT, not `instrument_id` uuid), `bar_ts` (TIMESTAMPTZ, true UTC not the IST-mislabeled-as-UTC vendor convention from `hist_option_bars_1m` Bug B3), `expiry_date` (DATE), `strike` (NUMERIC), `option_type` (TEXT `'CALL'`/`'PUT'`), `ltp` (NUMERIC — not `close`), `run_id` (UUID NOT NULL).
- **`run_id` NOT NULL backfill discipline:** backfill scripts that don't set `run_id` lie silently because supabase-py wraps INSERT failures in try/except but doesn't roll back local accumulator state — codified in `fill_2026_04_16_breeze_v3.py` v3 hardening (generates UUID per invocation; real-rows-only success log).
- **Pre-Apr-2026 vendor `hist_option_bars_1m` is uncatalogued in this Map's writer column (TD-S35-NEW-2 S1):** the vendor identity + contract terms + refresh cadence + `stock_code` mappings are not documented anywhere; bus-factor-of-one institutional knowledge at risk. Catalogue at S36.

---



---

---

## §A.S36 — Production scripts touched in Session 36

> Per Doc Protocol v4 §1. S36 was capture-layer resilience: 1 misdiagnosis closure (TD-S30-CANDIDATE-1 — historical data unit-mix repair on `gamma_metrics`, no live writer regression) + 1 TD closure via ENH-99 SHIPPED (Dhan 429 retry predicate + orphan janitor + telemetry). No orchestration / schedule changes; one new Task Scheduler task (`MERDIAN_Orphan_Janitor`) — see Deployment Topology §7.2.

| Change type | Script | Description |
|---|---|---|
| **PATCHED** | `gamma_engine_retry_utils.py` (Local) | `patch_s36_enh99_v3.py` — regex-anchor replacement of entire `retry_call` function (947 matched chars; v1+v2 had failed on first-400-char literal anchor due to deeper-body mismatch). New kwarg `retry_predicate: Callable[[Exception], bool] | None = None` added to signature + per-attempt predicate evaluation (when predicate present, only retry on predicate True; non-predicate exceptions raise immediately, do not consume retry budget) + `[RETRY_BURN_DOWN]` stderr telemetry tag on final failure (carries script identity + last exception class + attempt count). Backup `gamma_engine_retry_utils_PRE_S36.py`; AST validated pre+post; +996 bytes net. Backwards-compatible — all existing call sites without `retry_predicate` kwarg continue exception-blind behavior unchanged. |
| **PATCHED** | `ingest_option_chain_local.py` (Local) | `patch_s36_enh99_v2.py` — INGEST block applied live. 2 Dhan retry sites at lines 316 + 346 bumped from `attempts=3, delay_seconds=5.0, backoff_multiplier=1.5` to `attempts=6, delay_seconds=15.0, backoff_multiplier=1.5, retry_predicate=is_dhan_429`. ~24s → ~96s retry budget; window of safety vs ~60s Dhan quota window. Local `is_dhan_429(exc)` predicate defined in module (checks `getattr(exc, 'status', None) == 429` OR string-match on `'too many requests'` / `'805'` in exception repr — error_code 805 is Dhan's "Too many requests"). Supabase INSERT retry site at line 417 intentionally NOT touched (different exception class, no quota semantics, no benefit from 429-gated retry). Backup `ingest_option_chain_local_PRE_S36.py`; +504 bytes net; AST validated. |
| **NEW** | `orphan_run_janitor.py` (Local) | Standalone reaper of orphan RUNNING rows in `script_execution_log`. v3 deployed to `C:\GammaEnginePython\` after v1/v2 iteration: v1 used `supabase-py create_client` + `SUPABASE_URL`/`SUPABASE_KEY` env names → KeyError (house convention is `SUPABASE_SERVICE_ROLE_KEY` + raw HTTP via `requests`, see `ingest_option_chain_local.py`); v2 switched to raw HTTP but included `Prefer: return=representation` header → PostgREST 400 on PATCH (D.18.3 — header interacts with RLS on PATCH path); v3 dropped Prefer header + added per-row error tolerance + body printing + int4 duration clamp (D.18.4 — `age_ms = min(int((now - started_at).total_seconds() * 1000), 2_147_483_647)` because `script_execution_log.duration_ms` is int4 and orphan ages > ~24 days overflow `2^31 - 1`). Closes any RUNNING row aged > 5 min by PATCHing `exit_reason='DATA_ERROR'` + `notes='ORPHAN_RECOVERED: age_min=N'` prefix + `finished_at=now()` + `duration_ms=<clamped>`. Daily audit greps `notes LIKE 'ORPHAN_RECOVERED%'` for visibility. CHECK constraint `chk_exit_reason_valid` excludes 'ORPHANED' literal — `DATA_ERROR` with prefixed notes is the operational pattern. Smoke-fire test 2026-05-25 17:26:26 closed 22/24 orphans + 2 stragglers via REPL after int4 clamp fix. |
| **CALLED** | `backfill_gamma_metrics_to_main.py` (Local) | TD-S30-CANDIDATE-1 March epoch recovery invocation: `python backfill_gamma_metrics_to_main.py --start 2026-03-02 --end 2026-05-04 --mode overwrite --symbol both` — 2,850 cycles written; March epoch fully recovered to Cr units (overwrote pre-S27 raw-rupees rows from the live writer's pre-/1e7-patch window). April-early-May ~4,300 rows could not recompute (chain coverage residual under TD-S35-NEW-1 sparse `hist_option_bars_1m`) — these were DELETEd via `DELETE FROM gamma_metrics WHERE ts >= '2026-03-02' AND ts < '2026-05-12' AND ABS(net_gex) > 1e8`. No patch to the script itself; existing S29-era logic at HEAD commit (confirmed via `findstr /N /C:"1e7" backfill_gamma_metrics_to_main.py`). Cataloguing-only entry for S36 traceability. |

### S36 stale-doc updates

| Document item | Prior state | New state |
|---|---|---|
| TD-S30-CANDIDATE-1 ("live `gamma_metrics.net_gex` Cr unit regression" — carried 7 sessions S29 → S35) | OPEN — assumed live writer regression | **CLOSED-MISDIAGNOSIS S36** — direct read of writer function body in first turn confirmed `/1e7` Cr conversion intact at S27 commit `241f943`. Residual was historical data unit-mix from pre-S27 raw-rupees window, not live regression. Three-epoch SQL confirmed (pre-2026-03 Cr / 2026-03-02→2026-05-04 raw-rupees / post-2026-05-11 Cr). March recovered via overwrite-recompute; Apr-early-May ~4,300 rows DELETE'd as confirmed gaps. Foundational diagnosis-ordering lesson codified §D.18.1. |
| TD-080 ("Dhan 429 retry layer + circuit breaker" — ENH-99 reserved S29, carried 5 sessions S29 → S35) | PROPOSED — spec carried as ENH-99 reservation | **CLOSED via ENH-99 SHIPPED S36** — three failure modes diagnosed against `script_execution_log` (Mode A 429 quota / Mode B 401 token / Mode C orphan RUNNING). Mode B DROPPED as solved upstream S29 (zero post-S29 401s in 11 instrumented days). Components 1+2+3 shipped: retry predicate `is_dhan_429` + orphan janitor + telemetry. Component 4 audit thresholds deferred. |

## §B.S36 — Tables touched in Session 36

| Change type | Table | Description |
|---|---|---|
| **Data writes (overwrite + delete)** | `gamma_metrics` | TD-S30-CANDIDATE-1 cleanup: 2,850 cycles overwritten on March epoch (via `backfill_gamma_metrics_to_main.py --mode overwrite`); ~4,300 rows DELETEd via `DELETE FROM gamma_metrics WHERE ts >= '2026-03-02' AND ts < '2026-05-12' AND ABS(net_gex) > 1e8` (April-early-May raw-rupees window with no chain data available for recompute under TD-S35-NEW-1); 1 outlier 2026-05-19 09:55:14 NIFTY -4.7B from a single cycle DELETEd. Post-cleanup: every remaining row magnitude is consistent with Cr units (no raw-rupee outliers above `1e8` threshold survive). Residual Apr-early-May row gap filed as TD-S36-NEW-1 S3 (architecturally bounded by ADR-013 Breeze fallback when n≥3 backfills accumulated). |
| **Data updates** | `script_execution_log` | 24 orphan RUNNING rows aged 0.7-25 days closed via `orphan_run_janitor.py` v3 smoke-fire + 2 REPL stragglers (after int4 duration clamp fix). PATCH set `exit_reason='DATA_ERROR'` + `notes='ORPHAN_RECOVERED: age_min=N'` prefix + `finished_at=now()` + `duration_ms=<min(actual_age_ms, 2147483647)>`. Affected scripts: `compute_gamma_metrics_local` (largest cluster), `capture_spot_1m_v2`, `detect_ict_patterns_runner`, `build_trade_signal_local`, `ingest_option_chain_local`, `backfill_gamma_metrics_to_main`, `build_market_state_snapshot_local`, `compute_options_flow_local`. Final state: 0 RUNNING > 5 min. CHECK constraint `chk_exit_reason_valid` excludes 'ORPHANED' literal — operational pattern uses `DATA_ERROR` with notes prefix instead. |

### S36 architectural notes

- **`script_execution_log.duration_ms` is int4** — orphan-recovery durations exceeding `2^31 - 1 = 2,147,483,647 ms` (~24.85 days) overflow on PG INSERT/UPDATE. Operational pattern: clamp at write time via `min(int(age_ms), 2_147_483_647)`. Schema-level fix (migrate to int8) filed as TD-S36-NEW-4 S3 — non-urgent given clamp pattern works.
- **`script_execution_log.exit_reason` CHECK constraint `chk_exit_reason_valid`** allows only `SUCCESS, HOLIDAY_GATE, OFF_HOURS, TOKEN_EXPIRED, DATA_ERROR, SKIPPED_NO_INPUT, DEPENDENCY_MISSING, CRASH, TIMEOUT, RUNNING, DRY_RUN`. The 'ORPHANED' literal is NOT in the closed set. Janitor uses `exit_reason='DATA_ERROR'` + `notes='ORPHAN_RECOVERED: age_min=N'` prefix; daily audit greps `notes LIKE 'ORPHAN_RECOVERED%'` for visibility. Avoid proposing 'ORPHANED' constraint extension — the existing closed set is treated as architectural at S36.
- **`MERDIAN_Dhan_Token_Refresh` Task Scheduler task is not instrumented to `script_execution_log` (TD-S36-NEW-2 S3):** the script runs daily and writes to `dhan_token_probe_log` (S29-era instrumentation per TD-080 Mode B fix), but does not emit `script_execution_log` rows on start/exit. Means token-refresh failures are invisible to the daily audit pipeline that scans `script_execution_log`. Filed S3 — quick-win when next touching the token path.
- **`dhan_token_probe_log` first probe row is 2026-05-10 20:28 (TD-S36-NEW-3 S4):** pre-2026-05-10 token incidents (including the 2026-05-07 Mode B storm referenced in D.18.2) are invisible to the probe log. Documentation-only gap; the S29 instrumentation is forward-only by design — pre-S29 history is reconstructable only via `script_execution_log.exit_reason='TOKEN_EXPIRED'` rows.


---


## S55 update log (2026-06-17 — carry-forward execution sweep)

- **Orchestrator run_merdian_shadow_runner_aws.py — per-symbol run_id (commit 1889604).** `fetch_latest_run_id` (one run_id/cycle) → `fetch_latest_run_ids` ({NIFTY,SENSEX}); gamma + volatility now run ONCE PER SYMBOL with that symbol's run_id (labels carry the symbol). Closes the SENSEX compute under-write (TD-S54-NEW-1) at the code layer — each cycle previously computed only whichever symbol's ingest landed last in created_at order. gamma read path verified clean.
- **compute_volatility_metrics_local.py read-path repointed (commit e6fba1b).** Two reads (L351 fetch_recent_volatility_rows, L454 fetch_last_valid_vix_snapshot) + provenance label (L671) were querying the dead table `compute_volatility_metrics` (S48 fixed the write/TARGET_TABLE, left the reads); repointed to production `volatility_snapshots` (reads stay on prod per TD-NEW-12). Closes TD-S55-NEW-1. Pre-fix rows carry blank intraday-change context (forward-only correctness).
- **seed_trading_calendar.py — NEW script.** Rule-engine-driven (get_session_config_for_date), next-N-days, full-schema idempotent upsert on trade_date into `trading_calendar`; cron 02:30 UTC daily. Reads from trading_calendar.py (the rule engine) + trading_calendar.json (holidays). Retires the daily manual calendar insert (TD-S54-NEW-4 seeder half).
- **stage2_db_contract.py V18A-03 tightened (commit c2910e8).** check_trading_calendar_today now selects open_time and gates PASS on open_time present (FAIL points at the seeder) — aligns preflight with the capture gate's open_time IS NOT NULL (TD-S54-NEW-4 preflight half).
- **capture_postmarket_1600.py — non-blank exit reason (commit 5b92433).** Wrapper now emits exit code + stderr + stdout tail (TD-S54-NEW-3). Real failure was the futures SyntaxError cascading the prerequisite gate.
- **capture_index_futures_snapshot_local.py — Windows-path fix (commit 66f8252).** Three sites: L50 DEBUG_DIR repointed to script-dir + mkdir; L246/L253 relative_to f-strings dropped. Parses + runs on AWS now; futures still DARK because dhan_scripmaster is stale (no June index futures) and reload_dhan_scripmaster_from_csv.py is not yet AWS-ported. Cron stays commented (TD-S53-NEW-6).
- **Schema: `script_execution_log.duration_ms` migrated int4 → bigint (TD-S36-NEW-4 CLOSED).** SUPERSEDES the int4-overflow clamp note in the gotchas list above — the `min(int(age_ms), 2_147_483_647)` write-time clamp is no longer required (clamp is harmless if left in place).
- **Reference baseline correction:** option_chain FULL rows/fire are NIFTY 460 (230 strikes × 2) and SENSEX 372 (186 strikes × 2), stable all session — retire the stale 534/606 figures.
- **Breadth chain (TD-S48-NEW-1) re-diagnosed (OPEN):** ws_feed_zerodha.py (MALPHA) → market_ticks → ingest_breadth_from_ticks.py (AWS) → breadth_intraday_history → market_breadth_intraday. ws_feed_zerodha.py ABSENT from MALPHA; feed dark since 06-11; one closing read next session (what ingest_breadth_from_ticks SELECTs as its tick source) + restore under systemd.

---


## S56 + S57 update log (2026-06-18 / 2026-06-19)

### S56 (2026-06-18 — reconstructed at S57)
- **Futures resolver exact-match fix.** `capture_index_futures_snapshot_local.py` NIFTY → NIFTYNXT50 `DISPLAY_NAME ilike.*NIFTY*` substring bug fixed to exact `UNDERLYING_SYMBOL = eq.{symbol}` + `INSTRUMENT = eq.FUTIDX` (commit `8eae351`); 3 garbage `index_futures_snapshots` rows deleted (NIFTYNXT50, BANKNIFTY, SENSEX50, 2026-03-27 era).
- **Scripmaster reloader ported to AWS.** NEW `reload_dhan_scripmaster.py` (commit `132eddc`) — staging table `dhan_scripmaster_staging` + transactional swap RPC `swap_dhan_scripmaster()` (TRUNCATE-in-plpgsql to bypass the safe-update guard); 234,882 rows; FUTIDX resolves through Aug 2026. Replaces the non-atomic Local Windows-CSV `reload_dhan_scripmaster_from_csv.py`. Closes the S55 NEW-6 contract-resolution tail; futures cron `*/5 04-09 UTC` re-enabled both symbols.
- **New table:** `dhan_scripmaster_staging` (written by reload_dhan_scripmaster.py; swapped into dhan_scripmaster via the RPC).
- **Breadth-feed supervision built (surfaced post-S57 from git log).** S56 also authored + git-tracked the supervision scaffolding for rebuild-safety: wsfeed preflight (commit `afe8112` — tolerate `.env` special chars, drop `set -u` around `source`) + wsfeed alert script + **5 `systemd` units under `deploy/systemd/`** (commits `30cca59` + `b627914`). BUILT + committed but NOT enabled on MALPHA — S57 found the feed still unsupervised in an AWS `screen`; cutover/enable = ADR-018 D1 (TD-S57-NEW-1).

### S57 (2026-06-19)
- **Data audit 06-19 CLEAN:** chain 83/83 distinct ts both symbols from 03:00; all six derived tables exact 82/82 1:1 NIFTY:SENSEX (TD-S54-NEW-1 closed on DATA); futures 144 fires/symbol, basis 0.017–0.299%.
- **Breadth chain host correction (SUPERSEDES the S55 note above):** `ws_feed_zerodha.py` was NOT absent from MALPHA — it was running on **AWS** (not MALPHA) since 06-11 in a detached `screen`, holding an expired Zerodha token, 403-looping, writing zero-coverage rows. That hollow-write is why market_ticks read empty yet breadth "worked" through 06-11. Remediated live (token refresh MALPHA + PID 259620 kill -9 + clean restart, 2213 instruments). **Canonical home is MALPHA under `systemd`** per ADR-018 D1.
- **ADR-018 ACCEPTED** — breadth-feed supervision (D1 systemd-on-MALPHA + WCB cron fix; D2 mandatory recency-floor reader guard) + signal-subsystem disposition (D3 SMDM retired evidence-based vs ENH-30; D4 ENH-SDM AWS orchestrator-integrated per ADR-006).
- **SMDM RETIRED** — `compute_smdm_local.py` + `smdm_snapshots` retired (ADR-018 D3); STOP_HUNT/SQUEEZE flags + gamma-squeeze scalar dropped; manipulation-footprint + flow-velocity carried into ENH-SDM.
- **New table (PLANNED):** `structural_divergence_snapshots` (written by `compute_structural_divergence_local.py`, ENH-SDM, AWS orchestrator-integrated; consumers must apply ADR-018 D2 recency-floor guard).
- **Signal-subsystem orphans (S49 Local-disable):** options_flow_snapshots / iv_context_snapshots / shadow-v3 NOT migrated; disposition (port-to-AWS vs deprecate) open.

---

## §S58 (2026-06-22) — breadth supervision verified + ENH-SDM P1 schema

**New table — `structural_divergence_snapshots`** (+ `_replay` mirror, ADR-008): ENH-SDM observability monitor. Written by `compute_structural_divergence_local.py` (PLANNED P2); reads `gamma_metrics` (latest+prior) + spot. Gamma-centric primitives per CASE-2026-06-02: pin-risk rate, straddle-collapse velocity, gamma-concentration, net_gex/regime-flip + three-wick trigger. Display-not-gate. UNIQUE(symbol,ts), true-UTC. Migration `sql/2026-06-22_enh_sdm_structural_divergence_snapshots.sql`. Created S58 (empty); P2 writer carried to S59.

**Breadth feed — host correction MALPHA→AWS.** `ws_feed_zerodha.py` is supervised on **MERDIAN AWS** under `systemd` (units `merdian-wsfeed.service` + start/stop timers, `User=ssm-user`, `/home/ssm-user/meridian-engine`), NOT MALPHA (ADR-018 D1 corrected). MALPHA = Zerodha token gateway only. Cutover + Monday-open verification done S58 (single PID, 2213 instruments, zero 403s).

**Recency-floor guard** live in `build_market_state_snapshot_local.py` (the only live latest-row breadth/WCB consumer) — stale breadth/WCB nulled → existing degraded path; `*_stale_floored` raw flags. Verified zero STALE on the Monday open. Closes TD-081.

**Signal orphans (ADR-019):** `shadow_signal_snapshots_v3` / `iv_context_snapshots` RETAINED-PENDING-REHOME; `options_flow_snapshots` RETAINED-DORMANT. None retired.

---

## §S59 (2026-06-24) — breadth-correctness guard + ICT daily-PDL write fix

**`scripts/eod_health_check.py` — REFERENCE FRESHNESS section added** (commit `6b58587`, via `patch_s59_eod_reference_freshness.py` canon-v3, +55 lines, backup `eod_health_check_PRE_S59.py`). New section checks `equity_intraday_last` was refreshed **for the audited `--date`** (anchored to `--date`, not wall-clock) and measures the **`ts`** column, FAIL on a stale baseline. Proven live: `--date 2026-06-22` → FAIL STALE BASELINE (newest ts 2026-05-20); `--date 2026-06-23/24` → OK. This is the reference-table analogue of the ADR-018 D2 recency-floor (which guarded the feed/`market_breadth_intraday`, not the prev-close reference).

**`equity_intraday_last` freshness semantics (codified §D.25).** The table has BOTH `ts` (upsert-updated by `refresh_equity_intraday_last.py` — the real freshness column) and `created_at` (row-birth `DEFAULT now()`, never moves on upsert). All freshness checks read **`ts`**. Columns: `['ticker','ts','last_price','created_at']`, `ticker` is `NSE:`-prefixed (normalize via `norm_sym()` to match bare-`symbol` keys). The breadth prev-close baseline was FROZEN 2026-05-20→2026-06-24 because the `refresh_equity_intraday_last.py` cron was never carried onto the AWS-only host — see Deployment Topology §S59 + tech_debt TD-S59-NEW-1.

**`build_ict_htf_zones.py` — daily PDH/PDL now written unconditionally** (commit `2b40a4b`, `patch_s59_daily_pdl_unconditional.py` canon-v3, backup `build_ict_htf_zones_PRE_S59.py`, **Local** Task-Scheduler job — not AWS). The daily call site no longer passes the freshly-built daily PDH/PDL through `filter_breached_zones()`; `detect_daily_zones` emits exactly one PDH + one PDL per run (single prior day, no loop), so the proximity prune was unnecessary and dropped fresh PDLs on down-close days (the prior-day CLOSE used as `current_spot` sits inside the new PDL band built from the prior-day LOW). **Weekly block left filtered** (`detect_weekly_zones` loops the lookback and emits many PDH/PDL → still needs the nearest-2 prune). Verified `D PDL 23776-23796 => ACTIVE` for 06-24. See tech_debt TD-S59-NEW-3.

**Clarification — `build_ict_htf_zones.py` + `generate_pine_overlay.py` run on LOCAL** (Windows Task Scheduler), not on the AWS orchestrator. Diagnostics read Supabase (shared backend), so host-of-execution is irrelevant for reads; "AWS-only" governs writers/compute.

---

## §S60 (2026-06-26, Muharram holiday) — ENH-SDM P2 writer LIVE + shared holiday gate + trading_calendar fix

**NEW writer `compute_structural_divergence_local.py` (ENH-SDM P2) — LIVE + WRITING.** Display-not-gate observability monitor. Reads `gamma_metrics` (latest + prior + session-open); writes `structural_divergence_snapshots` (UPSERT on `symbol,ts`). Wired into `run_merdian_shadow_runner_aws.py execute_pipeline` after the SENSEX `build_market_state_snapshot` step, before the NIFTY `build_trade_signal` step (commit `8cec587`) — **non-fatal** (`run_compute_step` catches non-zero/timeout/exception → False; `execute_pipeline` tallies `failed_steps`, never aborts on first failure). Nothing downstream routes on it. AS-BUILT primitives/enums ratified in `docs/decisions/ENH-SDM_structural_divergence_monitor_spec.md` (S60). Forward cohort accrues from the next open; signal/modes gated on N (S58) + the TD-S58-NEW-1 Greeks solve. Writer commit `4bd3bf5`.

**NEW `core/trading_calendar_gate.py` (shared holiday gate, TD-S60-NEW-3).** Single source of holiday gating; reads `trading_calendar`; fail-open at every branch; self-sufficient (`load_dotenv` + raw `requests`, bypasses `core.config`). Exposes `is_trading_day_today()` / `is_trading_day(iso)` / `assert_trading_day_or_exit(log=None)`. The orchestrator (`run_merdian_shadow_runner_aws.py`) is cut over to it (commit `38a82ff`, −36/+2 lines); ~28 other entrypoints carry their own inline gates and migrate incrementally. Commit `3b3b8ee` (v2, self-sufficient).

**`trading_calendar.json` corrected at source (TD-S60-NEW-2, commit `bafddc2`).** The V18E rule engine `trading_calendar.py` reads holidays from `trading_calendar.json`; it had only 2 of 15 NSE-2026 equity holidays (one misdated), so the `trading_calendar` table mismarked every holiday `is_open=true` since ~April and the pipeline ran the full compute chain on Muharram. Regenerated to the 15 official NSE-2026 equity holidays (+ Nov-8 Muhurat special session); reseeded via `seed_trading_calendar.py --days 220`; stale `is_open=true` holiday rows flipped to false by explicit UPDATE (the seeder only writes open days). 06-26 reads closed, 06-29 (Mon) reads open. This is the holiday trust-anchor for the whole system — see CLAUDE.md Rule 18.

**`market_spot_session_markers` writer rescheduled (TD-S60-NEW-1).** `build_market_spot_session_markers.py` (Local/AWS marker writer; feeds the Marketview header's `prev_close_spot`) had stalled after 2026-06-04; cron `40 10 * * 1-5` (16:10 IST) added on AWS, markers backfilled 06-05→06-25, None-guard on postmarket-ts deref (`4f676e1`), `get_open_0915` window widened + `get_prev_close_spot` walk-back-7-days (`c9c2ab3`), and a freshness guard added to `scripts/eod_health_check.py` (`5066d81`).

**`structural_divergence_snapshots` — now LIVE + writing** (was P1-schema-deployed-only at S58). Cohort starts clean Monday (the 06-26 holiday-test rows were purged, TD-S60-NEW-4). Cross-refs: tech_debt TD-S60-NEW-1..5; merdian_reference.json v39 S60 change_log; Deployment Topology §S60.

## §S61 (2026-06-27, Saturday market closed) — ENH-02 wired + ENH-07 B basis-velocity context LIVE + historical basis cohort

**ENH-02 options-flow WIRED + reader floored (TD-S61-NEW-1).** `compute_options_flow_local.py` (orphaned at the S49 migration) re-homed into `run_merdian_shadow_runner_aws.py execute_pipeline` at the canonical options_flow slot. `build_trade_signal_local.py::_fetch_options_flow()` had no recency floor and had been applying the ENH-02/04 confidence modifiers (±3/4/5 on `pcr_regime`/`skew_regime`/`flow_regime`) off a ~24-day-stale `options_flow_snapshots` row since S49; ADR-018 D2 floor added (`MERDIAN_FLOW_RECENCY_FLOOR_MIN`, default 15 min). Commits `8ddbc78` + `d16986c`.

**NEW writer `compute_basis_context_local.py` (ENH-07 B) — LIVE + WRITING.** Display-not-gate. Reads ONLY `index_futures_snapshots` (spot+basis atomic per row, no join skew); computes basis velocity over a configurable window and labels `LONG_BUILD/WEAK_LONG/SHORT_BUILD/WEAK_SHORT/NEUTRAL` via spot/velocity deadbands; writes `basis_context_snapshots` (UPSERT `symbol,ts`; DDL `2026-06-26_enh07b_basis_context_snapshots.sql`). Wired into the orchestrator (L244-245, after market_state, before trade_signal). `_fetch_basis_context()` reader (`build_trade_signal_local.py` L516, ADR-018 D2 floor `MERDIAN_BASIS_RECENCY_FLOOR_MIN`) surfaces **display-only** `basis_context_label`/`basis_velocity_pp`/`basis_context_stale` into `signal_snapshots.raw` — NO confidence modifier (context-not-gate per S37). Env `MERDIAN_BASIS_VELOCITY_WINDOW_MIN`=15 / `_SPOT_DEADBAND_PCT`=0.0002 / `_VEL_DEADBAND_PP`=0.005 / `_RECENCY_FLOOR_MIN`=15. Writer commit `141386d` (+336).

**NEW table `basis_context_snapshots` (LIVE).** Columns: `symbol`, `ts`, `context_label`, `basis_velocity_pp`, `spot_delta`, `window_min`. UNIQUE(symbol,ts) + label CHECK + index.

**NEW historical cohort `hist_basis_context` (research/one-shot).** `backfill_basis_context.py` (DDL `2026-06-26_enh07b_hist_basis_context.sql`: `id/ts/symbol/contract_series/expiry_date/basis/basis_pct_now/basis_pct_prev/basis_velocity_pp/window_min/spot_now/spot_delta/context_label/source='hist_backfill'/created_at`; UNIQUE(symbol,ts) + label CHECK + index). Pairs `hist_future_bars_1m`×`hist_spot_bars_1m` per exact minute (zero shift — TD-S61-NEW-2), per-symbol front-month selector (NIFTY `contract_series`=1 expiry-NULL with liquidity preflight; SENSEX `contract_series`=0 expiry-populated). Wrote NIFTY 92,515 (96.0% labelled, avg basis_pct 0.283%) / SENSEX 29,689 (77.1% labelled; `abs(basis_pct_now)<1.0` MANDATORY → SENSEX secondary, NIFTY reference). Coverage NIFTY 2025-04-01→2026-03-30 / SENSEX 2025-05-02→2026-03-30; ~3-month Apr–Jun 2026 hole (no hist futures). Committed `3f1fe4e`.

**`hist_future_bars_1m` + `hist_spot_bars_1m` confirmed IST-clock-as-UTC → zero pairing shift (TD-S61-NEW-2).** The assumed −5h30m futures shift was wrong (14% pairing yield); both tables are mutually-consistent IST-as-UTC → zero shift (~99%). Refines the TD-087 note for the bar-pairing case.

**ENH-07 A reframed; `core/bs_engine.py` built+validated.** The live gamma engine reads vendor (Dhan) Greeks — no live BS solver, no live rate parameter; the risk-free rate is a parameter inside the TD-S58-NEW-1 historical Greeks backfill only. `core/bs_engine.py` validated (S=25218, K=24000, P=18, T=8/365, r=6.5% → IV=21.45%, γ=0.000134). Cross-refs: tech_debt TD-S59-NEW-2 + TD-S61-NEW-1/2/3; merdian_reference.json v40 S61 change_log; Deployment Topology §S61; CLAUDE.md v1.38.

## §S62 (2026-07-01) — historical per-strike Greeks + `gamma_concentration` backfill run to completion + `hist_gamma_metrics` discovery + ENH-116 spec + flip-bug diagnosis

**ENH-07 A CLOSED (no-op, flat r).** Superseded the S61 REFRAMED/open status: (1) empirical — flat r=6.5% BS reconstruction validated vs live `gamma_metrics` (sign 99% / magnitude 0.96× / sign-regime 95%); (2) architectural — the live engine reads vendor Greeks with no rate injection, so there is no live rate parameter. The historical backfill solves at flat r=6.5% (`core/bs_engine.py` substrate).

**NEW sidecar `hist_option_greeks_1m`** — per-strike lean `iv`+`gamma`, solved from vendor `hist_option_bars_1m` (NOT mutated) by `backfill_hist_greeks.py` (vectorized numpy IV bisection; reproduces `signed_gex_vec` verbatim; deep-ITM reject + PE flip + `γ·oi·S²/1e7`). **iv is the master key** — every Greek recomputes from iv+S+K+T+r; concentration is scale-invariant and needs only gamma, so the lean schema costs nothing for the concentration use.

**KEY DISCOVERY — `hist_gamma_metrics` already existed.** A pre-existing full-window (Apr 2025–Mar 2026) both-symbol **1-minute** series (~91,325 NIFTY / 91,136 SENSEX rows; schema: `bar_ts`, `spot`, `net_gex`, `gamma_concentration`, `flip_level`, `flip_distance[_pct]`, `straddle_slope`, `regime`, `gamma_zone`, `expansion_probability`). Validated vs live: **net_gex stored UNSCALED** (×1e7 vs live's /1e7 Cr convention; median ratio ~1.007e7), ~93% sign agreement, **expiry days handled CLEANLY** (real vendor Greeks — does NOT have the 0-DTE flat-vol disease). Clock: hist `bar_ts` is IST-clock-as-UTC at `:59`; live `ts` is real UTC at `:00`; shift = **−5h30m + truncate-to-minute**. **The ONE gap: `gamma_concentration` was 100% empty.** This table IS the historical source of truth; the new-table sidecar recompute was redundant. Concentration was recoverable ONLY by re-deriving per-strike gamma from raw bars (the historical per-strike source `gex_strike_snapshots` starts 2026-05-25, zero overlap with the hist window).

**`gamma_concentration` FILLED full-window both symbols.** `fill_gamma_concentration.py` computes `gamma_concentration = max|gex|/sum|gex|` (verbatim from `compute_gamma_concentration`; Herfindahl dominance ratio, scale-invariant → the 1e7 unit convention is moot for the fill) and idempotently PATCHes ONLY that column, matched on (symbol, bar_ts). `run_fullwindow.py` orchestrated per-month solve+fill (heartbeat, loud-abort+resume, per-day granularity, token-independent). **NIFTY COMPLETE** (12 mo; expiry-day nulls exactly on the expiry Tuesdays; loud-abort on empty 2026-04; Diwali 61-bar 2025-10-21 filled). **SENSEX COMPLETE** — `ALL DONE symbol=SENSEX total 1145.4 min` (~19h) — **bar 2026-01-19** (SSLError mid-solve → TD-S62-NEW-2, one-line resume). Expiry days are LIVE-SOURCED (`SKIPPED_EXPIRY`; 0-DTE flat-vol net_gex is numerically unreconstructible — `diag_1125.py`), not reconstructed. A proven-DIVERGENT `--fast` path was ABANDONED (not loosened).

**`hist_gamma_metrics` is now the canonical historical gamma series** for both symbols, full-window, with net_gex + `gamma_concentration` + flip/regime populated — the substrate for the ENH-116 expiry-memory seed and any future ENH-SDM backward study.

**ENH-116 Ambient Environment Intelligence — SPECCED (PROPOSED, P2).** Four regime lenses (gamma-positioning / breadth-trajectory / cycle-OI-participant / macro) + post-market compiler / pre-market reconciler + three-phase expiry-memory + three-tier View/Console; two proposed schemas `market_environment_snapshots` + `expiry_outcomes`; display-not-gate first year. Spec `docs/decisions/ENH-116-ambient-environment-intelligence.md`.

**TD-S62-NEW — SENSEX `compute_flip_level` bug (StockMojo parity).** In NEGATIVE_γ the near-spot region is a uniform short-γ pit with no near-spot zero-crossing, so the ATM-outward walk falls through to a spurious deep-tail crossing (~71,500) instead of the pit→wall boundary at 77,000 (above spot). Every other reading matches StockMojo exactly; flip is the sole outlier. Fix (near-spot sign-change walk + short-γ display guard) carried to S63.

Cross-refs: tech_debt TD-S58-NEW-1 (RESOLVED) + TD-S62-NEW + TD-S62-NEW-2; Enhancement Register ENH-07 A CLOSED + ENH-116 PROPOSED; merdian_reference.json v41 S62 change_log; Deployment Topology §S62; CLAUDE.md v1.39.

## §S63 (2026-07-02) — SENSEX flip fix DEPLOYED + ENH-115 P1 FII/DII participant positioning LIVE + ENH-07 A Phase-2 commits documented

**TD-S62-NEW flip fix — DEPLOYED (`dc63bb3`).** `compute_gamma_metrics_local.py::compute_flip_level` is now regime-conditional: a near-spot sign-change walk (first cumulative-GEX sign change on each side, nearest spot) plus a short-γ display guard (label the flip ill-defined under NEGATIVE_γ when no clean near-spot crossing exists, rather than emitting a spurious deep-tail level). SENSEX flip resolves near-spot; StockMojo parity confirms.

**ENH-115 P1 FII/DII participant positioning — BUILT + LIVE + BACKFILLED.** New Local+AWS scripts `parse_participant_oi.py` (NSE archive `fao_participant_oi_<DDMMYYYY>.csv` parser), `ingest_participant_positioning.py` (EOD writer — trading-day gate, participant leg upsert under the `core.execution_log.ExecutionLog` contract, non-fatal consolidated FII/DII cash leg), `backfill_participant_oi.py` (≥1yr resumable weekday-filtered backfill). New tables `participant_oi_daily` + `fii_dii_cash_daily` + freshness view `v_participant_oi_latest` (`sql/2026-07-02_enh115_participant_positioning.sql`). Scope: participant-wise OI is **NSE(NSCCL)-only** (no BSE participant equivalent — stub dropped in-code); FII/DII cash is **ONE consolidated NSE+BSE+MSEI** `fiidiiTradeReact` report. Writer live-proven (5 rows 2026-07-01, TOTAL long==short==18,953,033); backfill 270 trading days 2025-05-28→2026-07-01 (0 failures, 17 weekday-holiday MISSes cross-checked vs NSE calendar) — seeds the ENH-116 expiry-memory cohort. Display-not-gate positioning source; feeds ENH-116 Lens 3.

**Backfill calendar-gate discipline (Rule 18 corollary).** The historical backfill does NOT use the DB `trading_calendar` gate — that gate fail-opens on historical dates the (days-220-reseeded) table doesn't cover, inflating the plan to 382 days and running 400 slow sequential lookups. Replaced with a local Mon–Fri weekday filter + NSE archive 404 as holiday ground truth (MISS ≠ FAIL). PostgREST params use list-of-tuples (Python silently drops duplicate dict keys).

**ENH-07 A Phase-2 commits documented.** `894332a → cd7078d → 0f997c7` (all `measure_rate_sensitivity.py`, a read-only rate-sensitivity probe) — the "rate immaterial" finding underpins the S62 ENH-07 A no-op close; Enhancement Register Part-4 + Part-1 reconciled (A CLOSED no-op / B SHIPPED-Measure), reference.json artifact added.

Cross-refs: tech_debt TD-S62-NEW (RESOLVED) + TD-S62-NEW-2 (carried); Enhancement Register ENH-115 P1 BUILT + ENH-07 A/B reconciled; merdian_reference.json v42 S63 change_log; Deployment Topology §S63; CLAUDE.md v1.40.
