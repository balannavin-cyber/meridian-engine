# MERDIAN Enhancement Register v7

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Enhancement_Register_v7.md |
| Supersedes | MERDIAN_Enhancement_Register_v6.md (2026-04-13 morning) |
| Updated | 2026-04-13 (evening) |
| Sources | Enhancement Register v6 · Evening session 2026-04-13 |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document. |
| Authority | Tracks proposals, not decisions. Decisions live in master Decision Registry. |
| Update rule | Update in the same session that produces new architectural thinking. Commit immediately. |

---

## v7 Changes from v6

| Change | Detail |
|---|---|
| ENH-01 status | **COMPLETE** — ret_session threshold fixed (03:45→03:35 UTC). Will populate from tomorrow. |
| ENH-36 status | **COMPLETE** — capture_spot_1m.py + MERDIAN_Spot_1M task. Live 1-min bars writing to hist_spot_bars_1m. |
| ENH-46 NEW | **COMPLETE** — Process Manager (merdian_pm/start/stop/status). Zero terminal windows. |
| ENH-47 NEW | **COMPLETE** — MERDIAN_PreOpen Task Scheduler task. Closes C-07b. |
| C-07b | **CLOSED** — MERDIAN_PreOpen fires at 09:05 IST Mon–Fri via Task Scheduler |
| Signal dashboard | Signal timestamp UTC→IST fixed. Spot reads from signal_snapshots (5-min updates). |
| AWS status writer | write_cycle_status_to_supabase fixed: list payload + on_conflict + error logging |
| Dashboard refresh | 60s (was 300s) |
| Capital floor | Lowered to ₹10K for trial runs |

---

## Tier 1 — Actionable Now

---

### ENH-01: ret_session — Session Return to Momentum Engine

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

**Fix:** `build_momentum_features_local.py` session open threshold changed from 03:45 UTC (09:15 IST) to 03:35 UTC (09:05 IST). `MERDIAN_PreOpen` task captures spot at 09:05 IST — this row is now accepted as the session open price. `ret_session` will be non-null from tomorrow's first cycle. Feeds into `momentum_regime` with 2.5× weight.

---

### ENH-35: Historical Signal Validation

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

Full year results: NIFTY 244 signals, 58.6% T+30m accuracy. 6 signal engine changes applied. Do not re-run.

---

### ENH-36: hist_* to live 1-min spot promotion

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | capture_spot_1m.py, MERDIAN_Spot_1M Task Scheduler task |

**What was built:** `capture_spot_1m.py` calls Dhan IDX_I every minute, writes to `market_spot_snapshots` (live spot for dashboard) and `hist_spot_bars_1m` (synthetic 1-min bar O=H=L=C=spot for ICT detector). `MERDIAN_Spot_1M` Task Scheduler task fires every minute 09:14–15:31 IST Mon–Fri. Dashboard refresh lowered to 60s. ICT detector will have live bars from 09:14 onwards — first zones expected ~09:30.

---

### ENH-37: ICT Pattern Detection Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

All components live. MTF hierarchy confirmed. 1H zones (MEDIUM) confirmed adds edge.

---

### ENH-38: Live Kelly Tiered Sizing

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

End-to-end: runner → ict_zones → signal_snapshots. Strategy C (Half Kelly). See v6 for full detail.

---

### ENH-39: Capital Ceiling Enforcement

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

Floor ₹10K (lowered for trial). Freeze ₹25L. Hard cap ₹50L.

---

### ENH-40: Signal Rule Book v1.1

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | docs/research/MERDIAN_Signal_RuleBook_v1.1.md |

13 rule changes. See v6 for full detail.

---

### ENH-41: BEAR_OB DTE Gate — Combined Structure

| Field | Detail |
|---|---|
| Status | **DOCUMENTED — code pending execution layer** |
| Updated | 2026-04-13 |

Rule in Signal Rule Book v1.1 Section 2.2. Code pending Phase 4 execution layer.

---

### ENH-42: Session Pyramid — Deferred

| Field | Detail |
|---|---|
| Status | **DEFERRED** |
| Priority Tier | 2 |

Post-Phase 4 with WebSocket real-time prices.

---

### ENH-43: Signal Dashboard

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | C:\GammaEnginePython\merdian_signal_dashboard.py (port 8766) |

Signal timestamp UTC→IST fixed. Spot reads from signal_snapshots. 60s auto-refresh.

---

### ENH-44: Capital Management

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

set_capital.py + dashboard SET input. Floor ₹10K.

---

### ENH-45: hist_spot_bars_1m Zerodha Backfill

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

Apr 7–10 + Apr 13: 3,750 rows total. ICT detector has full backtest coverage.

---

### ENH-46: Process Manager

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | merdian_pm.py, merdian_start.py, merdian_stop.py, merdian_status.py |

**What was built:**
- `merdian_pm.py` — core: start background (no terminal), PID registry `runtime/merdian_pids.json`, stop, status, duplicate detection, port conflict check
- `merdian_start.py` — morning startup: Step 0 auto-inserts trading_calendar row (permanent V18A-03 fix), Step 1 kills all, Step 2 starts all 3 processes in background
- `merdian_stop.py` — kills all registered + unregistered instances of all MERDIAN scripts
- `merdian_status.py` — shows PIDs, uptime, port, alive/stopped, duplicate warnings. `--watch` mode.
- Health monitor: MERDIAN Processes panel added (PID/status/port per process, duplicate warning)

**Zero terminal windows needed.** All logs in `logs/pm_<name>.log`. Morning startup is one command: `python merdian_start.py`.

---

### ENH-47: MERDIAN_PreOpen Task (C-07b permanent fix)

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Closes | C-07b (pre-open capture gap — open since 2026-04-06) |

`MERDIAN_PreOpen` Task Scheduler task fires at 09:05 IST Mon–Fri, runs `capture_spot_1m.py` once. Captures NIFTY + SENSEX spot before supervisor starts at 09:14. This row becomes the session open price for `ret_session` computation. C-07b permanently closed.

---

## Summary Table — Full Register

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | **COMPLETE** |
| ENH-02 | Put/Call Ratio signal | 1 | IN PROGRESS |
| ENH-03 | Volume/OI ratio signal | 1 | IN PROGRESS |
| ENH-04 | Chain-wide IV skew signal | 1 | IN PROGRESS |
| ENH-05 | CONFLICT resolution logic | 1 | NOT BUILT |
| ENH-06 | Pre-trade cost filter | 1 | PROPOSED |
| ENH-07 | Basis-implied risk-free rate | 1 | IN PROGRESS |
| ENH-08 | Vega bucketing by expiry | 1 | PROPOSED |
| ENH-28 | Historical data ingest pipeline | 1 | SUBSTANTIALLY COMPLETE |
| ENH-29 | Signal premium outcome measurement | 1 | PIVOTED |
| ENH-30 | SMDM infrastructure | 1 | PARTIAL |
| ENH-31 | Expiry calendar utility | 1 | COMPLETE (merdian_utils.py) |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED |
| ENH-33 | Pure-Python BS IV engine | 1 | PRODUCTION |
| ENH-34 | Live monitoring dashboard | 1 | PRODUCTION |
| ENH-35 | Historical signal validation | 1 | **COMPLETE** |
| ENH-36 | hist_* to live 1-min spot | 1 | **COMPLETE** |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | **COMPLETE** |
| ENH-39 | Capital ceiling enforcement | 1 | **COMPLETE** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **COMPLETE** |
| ENH-41 | BEAR_OB DTE gate — combined structure | 1 | DOCUMENTED — code pending |
| ENH-42 | Session pyramid | 2 | DEFERRED |
| ENH-43 | Signal dashboard | 1 | **COMPLETE** |
| ENH-44 | Capital management | 1 | **COMPLETE** |
| ENH-45 | hist_spot_bars_1m Zerodha backfill | 1 | **COMPLETE** |
| ENH-46 | Process Manager | 1 | **COMPLETE** |
| ENH-47 | MERDIAN_PreOpen task | 1 | **COMPLETE** |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

---

*MERDIAN Enhancement Register v7 — 2026-04-13 (evening) — Living document, commit to Git after every update*
*Supersedes v6 (2026-04-13 morning). Commit alongside Open Items Register v8 and session log update.*

---

### ENH-51: WebSocket Feed + AWS Cloud Migration
**Status: PROPOSED**
**Added: 2026-04-13**

#### Architecture Decision

Dhan WebSocket (`wss://api-feed.dhan.co`) replaces 5-min REST option chain polling.
AWS becomes primary compute. Local becomes dashboard-only.
Zerodha evaluated and rejected — no SENSEX F&O coverage.

#### Why Dhan WebSocket over Zerodha KiteTicker

| Dimension | Dhan | Zerodha |
|---|---|---|
| Subscription limit | 100 instruments | 3,000 instruments |
| NIFTY options | ✅ | ✅ |
| SENSEX options | ✅ | ❌ Not available |
| Authentication | Existing token (no change) | Separate API subscription INR 2K/month |
| Integration effort | Low (already integrated) | High (new broker API) |

SENSEX is non-negotiable for MERDIAN. Dhan is the only option.

#### Instrument Subscription Strategy

Subscribe at session open via one REST call to get security_ids, then maintain WebSocket connection:

| Instrument | Count |
|---|---|
| NIFTY spot (security_id 13) | 1 |
| SENSEX spot (security_id 51) | 1 |
| NIFTY ATM ±15 strikes CE+PE | 30 |
| SENSEX ATM ±15 strikes CE+PE | 30 |
| Buffer | 38 |
| **Total** | **62 of 100 limit** |

±15 strikes covers ~750 NIFTY points intraday — handles 99% of sessions without resubscription.
GEX accuracy: ~75-80% vs 100% with full chain. Acceptable for directional signals.
Flip_level computation: slightly less precise but directionally correct.

#### Migration Phases

**ENH-51a — ws_feed.py on AWS (1 session)**
- `ws_feed.py`: connects to Dhan WebSocket at 09:14 IST
- Startup: one REST call to get current expiry security_ids for ATM ±15 strikes
- Subscribes 62 instruments
- Writes ticks to `atm_option_ticks` Supabase table (new)
- Reconnects automatically on drop (exponential backoff)
- Replaces `capture_spot_1m.py` for spot (writes hist_spot_bars_1m from ticks)

**ENH-51b — Promote AWS runner to full pipeline (1 session)**
- Modify `run_merdian_shadow_runner.py` to read from `atm_option_ticks` instead of REST option chain
- AWS runs full pipeline: ingest → gamma → vol → momentum → signal
- Local still runs in parallel (validation phase)
- Gate: 5 sessions where AWS signal matches local within 2 confidence points

**ENH-51c — AWS as primary, local as shadow (2 weeks validation)**
- Flip: AWS writes to live tables, local writes to shadow tables
- Monitor divergence daily
- Gate: 10 clean sessions as primary

**ENH-51d — Local cutover (1 session)**
- Turn off local runner, local breadth ingest, local capture tasks
- Local machine: dashboards only (reads Supabase — already works)
- AWS: full pipeline + WebSocket feed

#### New Table Required

```sql
CREATE TABLE atm_option_ticks (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ts           timestamptz NOT NULL DEFAULT now(),
  symbol       text NOT NULL,
  security_id  int NOT NULL,
  instrument   text NOT NULL,   -- SPOT / CE / PE
  strike       int,
  expiry_date  date,
  ltp          numeric NOT NULL,
  volume       bigint,
  oi           bigint,
  bid          numeric,
  ask          numeric
);
CREATE INDEX idx_atm_ticks_symbol_ts ON atm_option_ticks (symbol, ts DESC);
```

#### TOTP / Token Impact

No change. WebSocket authenticates with the same daily Dhan token.
Token refresh: existing cron at 08:15 IST (Local) + 08:35 IST (AWS pull) unchanged.
One WebSocket connection per session — no per-call token overhead.

#### Benefits vs Current Architecture

| Metric | Current (REST) | With WebSocket |
|---|---|---|
| Data freshness | 5-min snapshots | Real-time ticks |
| Spot update | 5-min (capture_spot_1m) | Every tick |
| Premium at signal time | Estimated or 5-min stale | Live |
| ICT detector input | 1-min synthetic bars | Real 1-min bars from ticks |
| 429 rate limit risk | Yes | No |
| AWS dependency on Local | Full (all data comes from Local) | None |
| Local machine required | Yes (runner + data) | Dashboards only |

#### Dependencies

- ENH-48 Phase 4A stable (live trade data to validate signal quality)
- Phase 4B (ENH-49) ideally live before cutover (need live fills to validate)
- Estimated start: after 2-4 weeks of Phase 4A data

---

*ENH-51 added 2026-04-13 — WebSocket + AWS migration*


---

### ENH-51 Revision — 2026-04-13 (post-MeridianAlpha review)

**Architecture updated after reviewing MeridianAlpha state.**

#### Revised Scope

| Component | Decision | Rationale |
|---|---|---|
| Zerodha KiteTicker | NIFTY full chain only | 3,000 instrument limit, 100% GEX accuracy |
| Dhan REST | SENSEX only (unchanged) | Zerodha has no SENSEX F&O |
| MeridianAlpha WebSocket | NOT NOW | EOD pipeline working, G-01 corporate actions blocks signal accuracy first |
| Shared Supabase | YES | Both systems already share DB. G-01 (market gate) already reads MERDIAN breadth. |

#### Why Not Zerodha for SENSEX

Zerodha does not list BSE F&O (SENSEX options). Dhan is the only broker covering both
NIFTY and SENSEX F&O. Architecture: Zerodha = data feed for NIFTY, Dhan = execution
broker + SENSEX data. Clean separation by symbol.

#### MeridianAlpha Integration Timeline

MeridianAlpha current state (as of 2026-04-13):
- EOD pipeline live: 2,132 stocks, 3.6M price rows, RS rank, trend template, watchlist ✅
- G-01 corporate action adjustment: CRITICAL — blocks signal accuracy. Must fix first.
- Delivery data: Windows-only (jugaad-data). AWS blocked by NSE bot detection.
- No intraday data yet.

**MeridianAlpha does NOT need WebSocket until:**
1. G-01 corporate actions fixed (signal accuracy restored)
2. Intraday strategy defined (currently EOD-only)
3. Stock F&O signals designed (180 stocks, Phase 3+)

**Shared infrastructure convergence point:**
Both systems already share Supabase. G-01 (market gate) reads MERDIAN breadth.
Portfolio management layer (future) will allocate capital across both systems.
No premature integration until MeridianAlpha signal layer is clean.

#### Revised ENH-51 Sub-items

| Sub-item | What | Dependency |
|---|---|---|
| ENH-51a | ws_feed_zerodha.py on AWS — NIFTY full chain | Phase 4B stable |
| ENH-51b | Dhan REST stays for SENSEX — no change | Already done |
| ENH-51c | AWS runner reads from Zerodha ticks (NIFTY) | ENH-51a |
| ENH-51d | AWS primary, local dashboards-only | ENH-51c + 10 sessions validated |
| ENH-51e | MeridianAlpha intraday WebSocket | After G-01 fixed + intraday strategy defined |
| ENH-51f | Unified portfolio management layer | Both systems stable, Phase 5 |

---

*ENH-51 revised 2026-04-13*


---

### ENH-51 Update — Late Night 2026-04-13/14

**ENH-51a: ws_feed_zerodha.py — STATUS: COMPLETE**
**Updated: 2026-04-14 02:30 IST**

Deployed on MERDIAN AWS (i-0878c118835386ec2, eu-north-1).

| Validation | Result |
|---|---|
| Instrument load | 45,712 NFO rows → 998 options + 6 futures + 3 spots = 1,007 total |
| Spot dry run | NIFTY 50: 23,842.65 &#124; NIFTY BANK: 55,605.05 &#124; INDIA VIX: 20.50 |
| Live write | 3 rows in market_ticks at 2026-04-14 02:25:44 UTC ✅ |
| market_ticks DDL | Applied to MERDIAN Supabase ✅ |
| AWS cron | 44 3 * * 1-5 (start) &#124; 02 10 * * 1-5 (stop) ✅ |
| Git | beb8709 → a215049 (--ddl fix) |

**Instrument subscriptions (1,007 total, within 3,000 limit):**
- 3 spots: NIFTY 50 (token 256265), NIFTY BANK (260105), INDIA VIX (264969)
- 998 NFO options: NIFTY + BANKNIFTY, current + next weekly expiry, CE+PE
- 6 futures: NIFTY + BANKNIFTY front month

**Token refresh:** ZERODHA_ACCESS_TOKEN in MERDIAN AWS .env. Refreshed daily via MeridianAlpha AWS browser login (core/refresh_kite_token.py — semi-manual, token expires 06:00 IST).

**Pre-market note:** Zerodha WebSocket does NOT serve pre-market (09:00–09:08 call auction). Connection closes outside 09:15–15:30 IST. MERDIAN_PreOpen (Dhan IDX_I) covers pre-open capture.

**Known issue — instrument_token INT overflow risk:** instrument_token column is INT (signed 32-bit, max ~2.1B). Zerodha tokens are 32-bit unsigned (max ~4.2B). Monitor — convert to BIGINT if any token exceeds 2.1B.

---

**ENH-51 Sub-item Status (revised after MeridianAlpha architecture review):**

| Sub-item | What | Status |
|---|---|---|
| ENH-51a | ws_feed_zerodha.py on MERDIAN AWS — NIFTY full chain | **COMPLETE** |
| ENH-51b | Promote AWS runner to read from market_ticks (not Dhan REST option chain) | PROPOSED — after Phase 4B stable |
| ENH-51c | AWS as primary compute, local dashboards-only | PROPOSED — after ENH-51b + 10 sessions validated |
| ENH-51d | Local runner cutover — turn off local runner | PROPOSED — after ENH-51c gate |
| ENH-51e | MeridianAlpha intraday WebSocket | DEFERRED — after MeridianAlpha G-01 fixed + intraday strategy defined |
| ENH-51f | Unified portfolio management layer | DEFERRED — both systems stable, Phase 5 |

**Conflicts between WebSocket and current REST pipeline (documented for ENH-51b planning):**

1. Duplicate spot writes: capture_spot_1m.py → market_spot_snapshots (local). ws_feed_zerodha.py → market_ticks (AWS). No conflict today — separate tables. Resolution: runner switches to market_ticks in ENH-51b.
2. Option chain REST vs WebSocket ticks: option_chain_snapshots (local REST) vs market_ticks (AWS WS). Pipeline reads option_chain_snapshots. No conflict today. Resolution: ENH-51b migrates gamma/vol scripts to market_ticks.
3. Token synchronisation: Zerodha token in MERDIAN AWS .env + Dhan token in local .env + system_config. No conflict — separate flows. Pre-market checklist: both tokens must refresh before 09:14.
4. Breadth ingest: stays local (Dhan LTP for 1,385 tickers, 429 risk on AWS). Path to AWS: subscribe breadth stocks to Zerodha WebSocket (1,007 + 1,385 = 2,392 — within 3,000 limit). Deferred to ENH-51c.

---

*ENH-51 late-night update 2026-04-13/14 — ENH-51a COMPLETE*


---

## v8 Changes — Session 2026-04-14/15

| Change | Detail |
|---|---|
| ENH-48 | **COMPLETE** — Phase 4A execution layer: merdian_trade_logger.py + merdian_exit_monitor.py + dashboard LOG TRADE/CLOSE buttons |
| ENH-49 | **COMPLETE** — Phase 4B: merdian_order_placer.py on AWS (port 8767). Dhan order API confirmed. Elastic IP 13.63.27.85 whitelisted. Scrip master streaming. |
| ENH-50 | **PROPOSED** — Phase 4C full auto. Gate: Phase 4B stable + real slippage data. |
| ENH-51a | **COMPLETE** (confirmed) — ws_feed_zerodha.py on MERDIAN AWS. 1,007 instruments. Cron 03:44 UTC. |
| ENH-51b | **PROPOSED** — Pipeline reads market_ticks instead of REST. Gate: tomorrow's live session confirms market_ticks options data quality. |
| ENH-51c/d | **PROPOSED** — AWS primary, local dashboards-only. Gate: ENH-51b + 10 sessions validated. |
| ENH-52 NEW | **PROPOSED** — Dhan expired options 5-year backfill. ATM-relative strikes. Batch 30-day chunks. Gate: Phase 4B stable. |
| ENH-52b NEW | **DEFERRED (Phase 5)** — S3 warm tier archiver. Was HIST-02 in open items. LocalParquetArchiver stubbed. S3ParquetArchiver pending. Not blocking anything. |
| Shadow gate | **CLOSED** — Phase 4 promoted. Gate waived (full year backtest evidence sufficient). Session 9 passed 2026-04-13. |
| OI register | **PERMANENTLY CLOSED** — all items resolved 2026-04-15. |

---

### ENH-48: Phase 4A Execution Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | merdian_trade_logger.py · merdian_exit_monitor.py |

Manual execution layer. Signal fires → operator clicks LOG TRADE on dashboard → enters premium → trade_log + exit_alerts written. Exit monitor polls every 30s, fires Telegram at T+30m. CLOSE TRADE updates PnL and capital_tracker.

---

### ENH-49: Phase 4B — Semi-Auto Order Placement

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-15 |
| Files | merdian_order_placer.py (AWS port 8767) |
| Dhan IP | 13.63.27.85 (Elastic IP, permanent, whitelisted in Dhan) |

merdian_order_placer.py on MERDIAN AWS. Endpoints: POST /place_order, POST /square_off, GET /margin, GET /health. Downloads Dhan scrip master (streaming, no OOM). Finds security_id by streaming CSV match on exchange=NSE/BSE, segment=D, OPTIDX, trading_symbol prefix, expiry_date, strike, option_type. Places MARKET INTRADAY order. Polls fill. Writes trade_log + exit_alerts. Updates capital_tracker on square off. Dashboard PLACE ORDER button (yellow) routes to AWS order placer via AWS_ORDER_PLACER_URL. Dashboard SQUARE OFF button routes to /square_off. Scrip master refreshed daily (delete runtime/dhan_scrip_master.csv before market open).

---

### ENH-50: Phase 4C — Full Auto

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Gate | Phase 4B stable + 2–4 weeks real fill data + slippage analysis |

Full automated execution without operator confirmation. Signal fires → order placed → exit at T+30m automatically.

---

### ENH-52: Dhan Expired Options 5-Year Backfill

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-14 |
| Gate | Phase 4B stable |

Use Dhan Data API expired options endpoint to extend hist_option_bars_1m back to 2021. Provides 1-min OHLCV + IV + OI for NIFTY/SENSEX expired contracts. Constraint: ATM-relative strikes (ATM±10 for indices). Requires mapping ATM-relative → absolute strike using hist_spot_bars_1m spot prices. 30-day chunks. Current dataset is 1 year (Apr 2025–Mar 2026). 5-year extension adds COVID recovery, rate cycle, and multiple volatility regime data.

---

### ENH-52b: S3 Warm Tier Archiver (was HIST-02)

| Field | Detail |
|---|---|
| Status | **DEFERRED — Phase 5** |
| Added | 2026-04-15 (moved from OI register HIST-02) |

LocalParquetArchiver stubbed at C:\GammaEnginePython\data\warm_tier\. S3ParquetArchiver pending AWS credentials and bucket setup. Not blocking any current pipeline. DuckDB backtest harness on S3 Parquet also deferred. Build after Phase 4C stable.

---

### Infrastructure Changes (2026-04-14/15)

| Item | Detail |
|---|---|
| t3.micro → t3.small | AWS instance upgraded. 2GB RAM. Required for scrip master parsing (32MB CSV). |
| Elastic IP | 13.63.27.85 allocated + associated to i-0878c118835386ec2. Permanent. |
| Dhan IP whitelist | 13.63.27.85 added to Dhan Static IP Setting (IP Address 1). |
| AWS signal dashboard | merdian_signal_dashboard.py running on AWS port 8766. Bound to 0.0.0.0. IP-restricted to 103.39.127.162 + 103.30.127.162. |
| AWS @reboot crons | signal_dashboard + order_placer auto-start on reboot via crontab @reboot. |
| Task Scheduler fix | MERDIAN_Intraday_Supervisor_Start → merdian_morning_start.ps1 → merdian_start.py. Single control plane. StartWhenAvailable=false on Spot_1M + PreOpen. |
| Holiday gates | 4 scripts patched: build_market_spot_session_markers.py, capture_market_spot_snapshot_local.py, compute_iv_context_local.py, run_equity_eod_until_done.py. Calendar check before any API call. |
| merdian_start.py | ensure_calendar_row() read-before-write. Holidays never overwritten. |
| SPO-01 fix | compute_gamma_metrics_local.py derives DTE from expiry_date. gamma_metrics.dte column added. Flows to market_state_snapshots → signal_snapshots. |
| ict_zones fix | Dashboard order column detected_at → detected_at_ts. Eliminates 391 daily 400 errors. |
| Supabase disk | Auto-expanded to 50GB. 22.26GB used. Autoscaling enabled. |
| market_ticks retention | pg_cron job 45: DELETE WHERE ts < now() - interval '2 days'. Daily 20:00 IST weekdays. |
| HTF zone cron AWS | 30 3 * * 1-5 build_ict_htf_zones.py --timeframe D on MERDIAN AWS. |
| Telegram | TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env. Exit monitor alerts confirmed working. |

---

## Updated Summary Table

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | **COMPLETE** |
| ENH-02 | Put/Call Ratio signal | 1 | **COMPLETE** |
| ENH-03 | Volume/OI ratio signal | 1 | **COMPLETE** |
| ENH-04 | Chain-wide IV skew signal | 1 | **COMPLETE** |
| ENH-05 | CONFLICT resolution logic | 1 | SUPERSEDED by SE-01 (ENH-35) |
| ENH-06 | Pre-trade cost filter | 1 | **COMPLETE** |
| ENH-07 | Basis-implied risk-free rate | 1 | **COMPLETE** |
| ENH-08 | Vega bucketing by expiry | 1 | DEFERRED |
| ENH-28 | Historical data ingest pipeline | 1 | **COMPLETE** |
| ENH-29 | Signal premium outcome measurement | 1 | PIVOTED |
| ENH-30 | SMDM infrastructure | 1 | PARTIAL — non-blocking shadow steps running |
| ENH-31 | Expiry calendar utility | 1 | **COMPLETE** — merdian_utils.py |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED — see ENH-52b |
| ENH-33 | Pure-Python BS IV engine | 1 | **PRODUCTION** |
| ENH-34 | Live monitoring dashboard | 1 | **PRODUCTION** |
| ENH-35 | Historical signal validation | 1 | **COMPLETE** |
| ENH-36 | hist_* to live 1-min spot | 1 | **COMPLETE** |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | **COMPLETE** |
| ENH-39 | Capital ceiling enforcement | 1 | **COMPLETE** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **COMPLETE** |
| ENH-41 | BEAR_OB DTE gate — combined structure | 1 | DOCUMENTED — code pending execution layer |
| ENH-42 | Session pyramid | 2 | DEFERRED — post Phase 4B |
| ENH-43 | Signal dashboard | 1 | **COMPLETE** |
| ENH-44 | Capital management | 1 | **COMPLETE** |
| ENH-45 | hist_spot_bars_1m Zerodha backfill | 1 | **COMPLETE** |
| ENH-46 | Process Manager | 1 | **COMPLETE** |
| ENH-47 | MERDIAN_PreOpen task | 1 | **COMPLETE** |
| ENH-48 | Phase 4A execution layer | 1 | **COMPLETE** |
| ENH-49 | Phase 4B semi-auto order placement | 1 | **COMPLETE** |
| ENH-50 | Phase 4C full auto | 2 | PROPOSED |
| ENH-51a | ws_feed_zerodha.py on AWS | 1 | **COMPLETE** |
| ENH-51b | Pipeline reads market_ticks | 1 | PROPOSED — gate: live tick data confirmed |
| ENH-51c | AWS primary, local dashboards-only | 1 | PROPOSED — gate: ENH-51b + 10 sessions |
| ENH-51d | Local runner cutover | 1 | PROPOSED |
| ENH-51e | MeridianAlpha intraday WebSocket | 3 | DEFERRED — G-01 must fix first |
| ENH-51f | Unified portfolio management | 4 | DEFERRED — Phase 5 |
| ENH-52 | Dhan expired options 5-year backfill | 2 | PROPOSED |
| ENH-52b | S3 warm tier archiver | 3 | DEFERRED — Phase 5 |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

*MERDIAN Enhancement Register — v8 appended 2026-04-15*
*Base document: Enhancement Register v7 (2026-04-13 evening)*


---

### ENH-54: HTF Sweep Reversal Trade Mode

| Field | Detail |
|---|---|
| Status | **PROPOSED — experiment required before build** |
| Added | 2026-04-15 |
| Priority | Tier 2 — post Phase 4B stable |
| Gate | Experiment 17 (backtest) must validate edge before any build |
| Depends on | ENH-49 (Phase 4B live), hist_ict_htf_zones (breach-filtered, live) |

**Observation:**
The Apr 7-8 2026 tariff shock produced a textbook weekly JUDAS_BEAR — price swept below W BULL_OB at 71,948 (SENSEX) to ~71,500, grabbed sell-side liquidity, reversed sharply and rallied 6,600 points to 78,111 over 5 sessions. MERDIAN's T+30m exit would have captured only the first 30 minutes of a multi-session expansion. Current-week options at DTE≤2 are inappropriate for multi-session holds due to theta acceleration.

**What changes:**

1. **Weekly sweep detection** — new logic in detect_ict_patterns_runner.py:
   - If today's session low < W BULL_OB zone_low AND session close > zone midpoint → flag WEEKLY_SWEEP_REVERSAL (bullish)
   - If today's session high > W BEAR_OB zone_high AND session close < zone midpoint → flag WEEKLY_SWEEP_REVERSAL (bearish)
   - Requires hist_ict_htf_zones (already live) for zone lookup

2. **DTE-aware option selection** — modify option selection in order placer:
   - DTE ≥ 4: current week expiry (current behaviour)
   - DTE < 4 OR WEEKLY_SWEEP_REVERSAL: next week expiry (DTE ~8-10)
   - Scrip master streaming already supports next-week lookup

3. **Zone-based exit** — replace T+30m for sweep reversal entries:
   - Primary exit: first opposing HTF zone (BEAR_OB/PDH above for longs)
   - Secondary exit: T+2 sessions if no zone reached
   - Hard stop: if price re-enters the sweep zone (reversal failed)

4. **Sizing** — TIER1 (highest conviction) for confirmed weekly sweeps

**Confirmation hierarchy (all preferred, minimum 2 of 4):**
1. Price closes back inside W BULL_OB/BEAR_OB (primary — required)
2. JUDAS_BEAR/BULL confirmed at T+15m intraday (secondary)
3. WCB transitioning BEARISH→TRANSITION or NEUTRAL→BULLISH (tertiary)
4. VIX declining intraday after sweep (context)

**Experiment 17 required before build:**
- Dataset: full year hist_spot_bars_1m + hist_ict_htf_zones
- Identify all sessions where price swept a W BULL_OB or BEAR_OB and closed back inside
- Score with next-week ATM CE/PE using hist_option_bars_1m
- Exit rules: first opposing HTF zone OR T+2 sessions
- Compare vs current T+30m same-week option
- Hypothesis: HTF sweep reversals with zone-based exit significantly outperform T+30m

**What we are NOT doing until Experiment 17 validates:**
- No code changes to detect_ict_patterns_runner.py
- No changes to option selection logic
- No changes to exit monitor
- No execution layer changes

**Expected edge (hypothesis only — unvalidated):**
The Apr 7-8 move suggests sweep reversals from W zones are high-conviction multi-session trades. If Experiment 17 confirms this across the full year, the edge could be substantially larger than standard ICT pattern trades (+58-107% validated in Experiments 2-16).

---

## v8 Appended 2026-04-19 -- V18H_v2 ENH + OI migration

V18H_v2 (2026-04-17/18) proposed ENH-43..47 and OI-11..15. These collided
with existing COMPLETE items in v7 and with the permanently-closed
OpenItems Register (closed 2026-04-15). Per new numbering convention
(Documentation Protocol v2): ENH IDs are monotonic in this register; no
new OI-* series may be created. V18H_v2 items are renumbered and OI
content is folded into the matching ENH entries below.

| V18H_v2 label | Canonical | Disposition |
|---|---|---|
| ENH-43 + OI-11 | **ENH-53** | folded; OI-11 content is ENH-53 Build field |
| ENH-44 + OI-12 | **ENH-55** | folded; OI-12 content is ENH-55 Build field |
| ENH-45 + OI-15 | **ENH-56** | folded; OI-15 content is ENH-56 Monitoring field |
| ENH-46 | **ENH-57** | COMPLETE record only |
| ENH-47 | **ENH-58** | COMPLETE record only |
| OI-13 | **ENH-59** | promoted to full ENH (patch script syntax rule) |
| OI-14 | (none) | session task, tracked in session_log only |

Errata: `docs/appendices/V18H_v2_RENUMBERING_NOTE.md`. V18H_v2.docx is
NOT modified.

---

### ENH-53: Remove breadth regime as hard gate

| Field | Detail |
|---|---|
| Status | **PROPOSED** (was V18H_v2 ENH-43) |
| Added | 2026-04-17 |
| Priority | HIGH |
| Evidence | Experiment 25 (5m): WR spread = 1.0pp across BULLISH/BEARISH/NEUTRAL regimes. Pure noise. BEAR_OB on BULLISH days: 51.0% (better than BEARISH 45.0%). Gate directionally backwards. |
| Gate | C-08 closed 2026-04-19 -- breadth now reads fresh from market_breadth_intraday via the view |
| Build (was OI-11) | `build_trade_signal_local.py`: (1) remove breadth_regime from hard-gate / DO_NOTHING logic; (2) demote to confidence modifier: BULLISH+BUY_CE = +5 pts, BEARISH+BUY_PE = +5 pts, opposing = 0 pts; (3) remove from DO_NOTHING reasons. |
| Gate for live promotion | Shadow test 5 sessions before promoting live. |
| Depends on | ENH-55 (implement in same session -- both are build_trade_signal_local.py edits) |

---

### ENH-55: Momentum opposition hard block

| Field | Detail |
|---|---|
| Status | **PROPOSED** (was V18H_v2 ENH-44) |
| Added | 2026-04-17 |
| Priority | HIGH |
| Evidence | Experiment 20 (5m): ALIGNED 60.9% WR (N=2,138) vs OPPOSED 38.3% WR (N=2,275). Lift +22.6pp. Consistent across BEAR_OB (63.1/40.4), BULL_OB (59.3/35.9), BULL_FVG (58.6/36.9). |
| Definition | BUY_PE + ret_session < -0.05% = ALIGNED. BUY_CE + ret_session > +0.05% = ALIGNED. \|ret_session\| < 0.05% = NEUTRAL (allow). Mismatch = OPPOSED -> block. |
| Build (was OI-12) | `build_trade_signal_local.py`: (1) if `abs(ret_session) > 0.0005` and direction opposes ret_session -> DO_NOTHING; (2) remove current momentum_regime confidence modifier (superseded); (3) add +10 confidence points when aligned. |
| Gate for live promotion | Shadow test 5 sessions alongside ENH-53. |
| Depends on | None -- can build standalone, but bundled with ENH-53 in single session |

---

### ENH-56: Premium sweep detector (monitor phase)

| Field | Detail |
|---|---|
| Status | **PROPOSED -- MONITOR ONLY, DO NOT BUILD** (was V18H_v2 ENH-45) |
| Added | 2026-04-18 |
| Priority | MEDIUM |
| Evidence | Experiment 27b: PE sweep 0.2-1.0% = 64.5% WR (N=107). Size boundary is critical: large sweeps (>3%) = 49.1% (coin flip); small (<1%) = 64.5%. Momentum-independent (aligned vs opposed: 56.4% vs 57.5% -- no difference). |
| Key insight | Premium sweeps behave differently from spot ICT patterns -- momentum-independent. A separate signal class. |
| Monitoring (was OI-15) | Log live morning PE/CE sweeps <1% from hist_atm_option_bars_5m. Target: 50 live occurrences. Review threshold: build if 60%+ WR sustained. |
| Build gate | 50 live occurrences + 60%+ WR. Not before. |

---

### ENH-57: MTF OHLCV infrastructure

| Field | Detail |
|---|---|
| Status | **COMPLETE** (was V18H_v2 ENH-46) |
| Completed | 2026-04-17 |
| Tables | hist_spot_bars_5m (41,248 rows), hist_spot_bars_15m (14,072), hist_atm_option_bars_5m (27,082 with pre-computed wick metrics), hist_atm_option_bars_15m (9,601) |
| Scripts | build_spot_bars_mtf.py, build_atm_option_bars_mtf.py, fix_atm_option_build.py, fix_expiry_lookup.py |
| Runtime | ~50 minutes total for full year backfill |
| Key decision | 1m bars are execution-granularity only. All ICT pattern detection uses 5m bars going forward. Evidence: Experiment 23 sweep detection found 0 events on 1m vs 52 on 5m. |

---

### ENH-58: hist_pattern_signals table

| Field | Detail |
|---|---|
| Status | **COMPLETE** (was V18H_v2 ENH-47) |
| Completed | 2026-04-17 |
| Table | hist_pattern_signals (6,318 rows, source=backfill_5m) |
| Script | build_hist_pattern_signals_5m.py |
| Key outcome | 52 sweep reversals detected on 5m vs 0 on 1m -- validates timeframe architectural decision. |
| Downstream impact | All future experiments run in <2 minutes vs hours. Experiment 20 ran in 90s vs prior 3.5h baseline (Exp 18 OI wall rebuild). |

---

### ENH-59: Patch script syntax validation rule

| Field | Detail |
|---|---|
| Status | **PROPOSED -- process rule** (was V18H_v2 OI-13) |
| Added | 2026-04-17 |
| Priority | MEDIUM |
| Trigger | force_wire_breadth.py (2026-04-16 session) inserted a code block at wrong indent depth in run_option_snapshot_intraday_runner.py. Script exited cleanly at market close; IndentationError only surfaced at next session restart, would have disabled the entire pipeline. |
| Rule | Every `fix_*.py` patch script MUST call `ast.parse(target_file.read_text())` before writing the target file. If SyntaxError: print error and `sys.exit(1)`. |
| Build | Add to MERDIAN_Change_Protocol.md as new STEP 1.6 (Patch script syntax gate) at next protocol increment. |
| Applied informally | fix_runner_indent.py (2026-04-17), fix_atm_option_build.py, fix_expiry_lookup.py all already include `ast.parse()` validation. Rule is enforced in practice; formal protocol inclusion pending. |

---

*End of v8 section.*
