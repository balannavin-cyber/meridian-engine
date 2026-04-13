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
