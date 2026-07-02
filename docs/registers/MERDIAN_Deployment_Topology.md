# MERDIAN Deployment Topology

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Deployment_Topology.md` |
| Location | `docs/registers/` |
| Type | "What runs where" — Local Windows ↔ MERDIAN AWS EC2 ↔ MALPHA AWS EC2 boundary spec |
| Established | 2026-05-09 (Session 23 — created per Doc Protocol v4 Rule 9.2; Task Scheduler audit by Navin in same session closed System Map §G.1) |
| Update rule | Inline, same commit as the topology change. Triggers in Doc Protocol v4 Rule 1. |
| Companion | `MERDIAN_System_Map.md` for full file/table inventory; this document for environment placement only. |
| Forward link | This document is the canonical anchor for ADR-006 (reserved — AWS migration scope). When ADR-006 is drafted, it is the architectural decision; this Topology is the operational map. |


**S48 Fix (2026-06-10):** Corrected orchestrator crontab syntax. Prior entry had `flock` scope error: `flock -n /lock cd /path &&` command executed `cd` under lock but subsequent command outside lock, breaking relative paths and .env sourcing. Fixed: moved `cd` before `flock` and added explicit `source .env`. Cron daemon restarted 2026-06-10 07:21 UTC. Orchestrator now firing every 5-min boundary as intended.

---

## Purpose

A single answer to "where does X run? what runs only on Local? what runs only on MERDIAN AWS? what runs only on MALPHA AWS? what runs on multiple?" Replaces scattered guidance in V18 §15.4/15.5, V18A §13.5, V18E §7.4/7.5, and CLAUDE.md gotchas.

The three environments are not symmetric. Local Windows is the **primary live execution environment** for signal generation, broker authentication, dashboards, and Phase 4A manual execution. MERDIAN AWS EC2 is the **shadow execution environment** for scheduled redundancy, EOD ingestion, post-market capture, and Phase 4B order placement (Dhan IP-whitelisted endpoint). MALPHA AWS EC2 is the **Zerodha token gateway environment** — runs the Kite token refresh service that other environments consume; not a Meridian-pipeline host. Treating them as interchangeable produces real failures (see §6 AWS gotchas).

---

## §1 — Side-by-side environment summary

| Aspect | Local Windows (PRIMARY LIVE) | MERDIAN AWS (SHADOW + AWS-only services) | MALPHA AWS (Kite gateway) |
|---|---|---|---|
| Path | `C:\GammaEnginePython\` | `/home/ssm-user/meridian-engine/` | `/home/ubuntu/meridian-alpha/` |
| Instance | Navin's Windows desktop, multi-WAN home network | t3.small, instance `i-0e60e4ed9ce20cefb` per pre-S35 documentation (**S35 instance-ID drift surfaced — current console shows `i-0878c118835386ec2`; instance was rebuilt at unknown earlier session; Elastic IP `13.63.27.85` unchanged; reconcile at S36**), region eu-north-1, host `ip-172-31-35-90`, user `ssm-user` | EC2 at `13.51.242.119`, user `ubuntu` |
| OS | Windows 10/11 | Ubuntu Linux | Ubuntu Linux |
| Python runtime | `python.exe` (3.12 — currently CMD-window-spawning; TD-061 candidate for `pythonw.exe` migration) | `python3` (3.10 — strict `fromisoformat()` microsecond handling, see §6.9 / TD-NEW-13) | `python3` |
| Scheduler | Windows Task Scheduler (20 `MERDIAN_*` tasks per Session 36; was 19 at S29 audit; was 17 at S23) | crontab (6 entries — see §7.1) | crontab (Kite token refresh schedule) |
| Live signal generation | ✅ Primary | ❌ Shadow only (writes shadow rows; not production decisions) | ❌ Not a Meridian pipeline host |
| Broker auth — Dhan | ✅ TOTP retry | ✅ Token pulled from Local-written Supabase 03:05 UTC | ❌ |
| Broker auth — Zerodha (Kite) | ✅ KiteTicker WebSocket (NIFTY full chain) | ❌ Cannot — depends on MALPHA token | ✅ **Sole Kite token writer**; MERDIAN AWS reads from MALPHA (manual sed step today — TD-NEW-7) |
| Phase 4A manual execution | ✅ `merdian_trade_logger.py` + dashboard LOG TRADE button | ❌ | ❌ |
| Phase 4B order placer (Dhan REST) | ❌ Not whitelisted; multi-WAN home IP unstable | ✅ `merdian_order_placer.py` HTTP server port 8767, AWS Elastic IP 13.63.27.85 Dhan-whitelisted, @reboot cron (S28 surfacing) | ❌ |
| Dashboards | ✅ Three live dashboards (signal, monitor, live) | ❌ Headless | ❌ |
| Supervisor | ✅ `gamma_engine_supervisor.py` + `start_supervisor_clean.ps1` | ❌ Cron-driven; no supervisor | ❌ |
| Pipeline alert daemon | ✅ `merdian_pipeline_alert_daemon.py` | ❌ | ❌ |
| Telemetry / heartbeat | ✅ `gamma_engine_telemetry_logger.py` writes `runtime/telemetry/*` | ❌ Not currently mirrored | ❌ |
| EOD ingestion | ✅ Recovery path (when MERDIAN AWS misses) | ✅ Primary 16:10 IST cron | ❌ |
| Post-market capture | ⚠ Topology question — task exists but JSON says AWS-only (see §6) | ✅ Cron 16:00 IST | ❌ |
| `gamma_metrics_shadow` write target | ❌ Production `gamma_metrics` is Local's write target | ✅ **As of S28** AWS `compute_gamma_metrics_local.py --shadow` writes here (TD-NEW-12 RESOLVED). Pre-S28 wrote to production `gamma_metrics` (silent architectural invariant violation Apr 29 → May 13). | ❌ |
| Code editing | ✅ Sole permitted edit point | ❌ FORBIDDEN except BREAK_GLASS (Change Protocol Step 8) | ❌ (separate repo, separate auth; not Meridian code surface) |
| Code distribution | Push to origin via `git push` | Pull via `git pull` from origin | Independent repo |
| Database | Same Supabase Postgres (shared single source of truth) | Same Supabase Postgres | Writes Kite token to Supabase `system_config` (planned per TD-NEW-7); currently writes only locally + propagated manually |

---

## §1.5 — MALPHA: third environment, Zerodha token gateway

MALPHA is a separate EC2 instance running the Kite (Zerodha) token refresh gateway. Until Session 28, MALPHA was treated inline in narrative as "Kite gateway, not Meridian" and was not given a row in this side-by-side. Two operational outages from manual MALPHA→MERDIAN AWS token propagation (2026-04-22 and 2026-05-12) surfaced that MALPHA is an unmissable third environment that the Meridian production pipeline depends on, even though it doesn't host any Meridian code.

**Why MALPHA exists as a separate environment:**

- Zerodha Kite Connect's API auth flow is **browser-redirect TOTP** — the same flow that prevents `ws_feed_zerodha.py` from running on MERDIAN AWS. MALPHA hosts the auth-browser-capable service in headless-but-interactive form.
- Multi-WAN home network on Local makes Local's Kite auth fragile (IP changes), but Kite Connect tolerates this for the *token refresh* leg. MALPHA gives stable IP for the *token writer* leg.
- Architectural separation: Meridian's pipeline never touches Kite directly on AWS — it consumes Zerodha tokens from MALPHA via Supabase, same pattern as Dhan tokens.

**MALPHA → MERDIAN AWS token propagation (current S28 state — fragile, TD-NEW-7):**

- MALPHA writes refreshed Zerodha access token to its own `.env` and local file.
- A **manual `sed` step** on MERDIAN AWS pulls the new token into `/home/ssm-user/meridian-engine/.env`. No automation.
- This is the proximate cause of the 2026-04-22 and 2026-05-12 morning outages where MERDIAN AWS `ws_feed_zerodha.py` (also runs on MERDIAN AWS for shadow path? No — Local-only per §2; the dependency is for `ingest_option_chain_local.py` which uses Kite SDK on AWS for some calls) rejected the stale token.

**TD-NEW-7 (S1) fix design (queued for S29+):**

- MALPHA writes Zerodha access token to Supabase `system_config` table (same pattern as Dhan).
- MERDIAN AWS `pull_token_from_supabase.py` extended to handle Zerodha key alongside Dhan.
- Eliminates the manual step; same automation pattern eliminates the same failure class as Dhan token sync solved.

**MALPHA as Meridian dependency:**

| Meridian operation | Depends on MALPHA? | How |
|---|---|---|
| Kite WebSocket on Local (`ws_feed_zerodha.py`) | No | Local has its own browser-auth flow |
| Kite REST calls on MERDIAN AWS (`ingest_option_chain_local.py` etc.) | YES | MERDIAN AWS reads Kite access token from `.env` written via manual sed from MALPHA |
| Any AWS-side script that imports `kiteconnect` and requires auth | YES | Same |

**Until TD-NEW-7 closes**, the Topology has three environments and a manual operational step between two of them. After TD-NEW-7 closes, the manual step becomes a Supabase replication that mirrors the Dhan token flow exactly.

---

## §1.6 — Breeze (ICICI Direct) — historical options backfill source (NEW S35)

ICICI Direct's Breeze retail API was used for the first time in MERDIAN at Session 35 to surgically fill a one-day chain coverage gap in `historical_option_chain_snapshots` (HOCS) for 2026-04-16. It is not an environment in the same sense as Local / MERDIAN AWS / MALPHA — it is an **external API consumed from MERDIAN AWS** — but it warrants topology codification because (a) its SEBI static-IP whitelist requirement makes the consumption boundary fixed to MERDIAN AWS, not arbitrary, and (b) ADR-013 PROPOSED 2026-05-24 may graduate Breeze to a canonical historical backfill source (ENH-109), at which point it becomes a regularly-scheduled service.

**Why Breeze consumed only from MERDIAN AWS:**

- ICICI Direct's Breeze API requires a SEBI-compliant static-IP whitelist after 2026-04-01. Operator already registered MERDIAN AWS Elastic IP `13.63.27.85` with ICICI Direct (the same IP that serves Dhan order placement per §3's `merdian_order_placer.py` entry). Local's multi-WAN home network has unstable IP and cannot satisfy the whitelist.
- Auth uses a cookie-based session (API key + API secret + session-token request) rather than OAuth-redirect — no headless-but-interactive constraint that affects Zerodha. Consumption is straightforward Python `requests` calls.
- Rate limit: 5000 calls/day budget + 100 calls/min throttle. Comfortably within budget for full-chain backfill of a single day (≈800-1000 calls per symbol per day across strikes × expiries × OHLC granularity); marginal for full-year backfill (would need cadence planning per ENH-109).

**S35 demonstrated capability:**

- `fill_2026_04_16_breeze_v3.py` (md5 `5eae3849776ec2a6061ed2100ecb0e13`) deployed to MERDIAN AWS at `/home/ssm-user/meridian-engine/`. Wrote 107,630 HOCS rows (NIFTY 61,899 + SENSEX 45,731) `source='breeze_backfill_s35'` in 4-5min wallclock from a single SSM session.
- File transfer to MERDIAN AWS used nano multi-line paste after base64-single-line paste exceeded SSM terminal buffer (~4KB) — codified as operational finding in CLAUDE.md v1.25.
- SENSEX symbology on Breeze: `stock_code='BSESEN'` not `'SENSEX'`, empirically discovered via 6-variant probe (TD-S35-NEW-3 S4). NIFTY uses `stock_code='NIFTY'`. F&O: `product_type='options'` + `right` ∈ {`'call'`, `'put'`}. Exchange: `exchange_code='NFO'` (NIFTY) / `'BFO'` (SENSEX).
- Two relevant Breeze functions:
  - `rollingoption` — ATM±N strikes per call across DTE range; 3-year lookback; high call efficiency. Best fit for ATM-anchored research (mirrors current vendor `hist_option_bars_1m` shape; ATM-only cap acceptable). Operator confirmed proven capable on S35.
  - `get_historical_data_v2` — per-strike per-expiry full granular control; 3-year lookback; lower call efficiency (one call per strike-expiry-day cell). Best fit for full-chain backfill (no strike-cap restriction; matches HOCS shape; supports Phase 3 GEX time-series prerequisite per ADR-002 v2 P7/P8).

**Current status (S35):** Architectural fallback for one-shot chain coverage gaps (proven on 2026-04-16). PROPOSED graduation to canonical historical backfill source pending ADR-013 decision. Not on S36 critical path.

**Cross-references:**

- ADR-013 PROPOSED 2026-05-24 — Breeze as canonical historical backfill source.
- ENH-109 PROPOSED 2026-05-24 — graduate `rollingoption` + `get_historical_data_v2` (Phase 3 GEX prerequisite per ADR-002 v2 P7/P8).
- TD-S35-NEW-3 — SENSEX `stock_code='BSESEN'` codification.
- `historical_option_chain_snapshots` (HOCS) — post-Apr-2026 chain-history canonical Supabase table; source values include `'breeze_backfill_s35'` (S35 surgical fill) alongside the default `ingest_option_chain_local`-produced rows.
- ENH-106 v8 dual-source chain reader — downstream consumer; `option_pnl_source` audit column will need a new value `'breeze_canonical'` once ENH-109 ships.

---

## §2 — Local-only scripts

These scripts only run on Local Windows. Either they require Windows-specific runtime (e.g. `CREATE_NO_WINDOW` subprocess flag), browser-based auth, GUI dashboards, or operational supervision that AWS does not provide.

| Script | Why Local-only |
|---|---|
| `ws_feed_zerodha.py` | Zerodha KiteTicker WebSocket. Auth flow is browser-redirect TOTP. Cannot run headless on MERDIAN AWS. |
| `run_option_snapshot_intraday_runner.py` | Primary live 5-min options runner. MERDIAN AWS has the shadow runner; this is production. |
| `gamma_engine_supervisor.py` | Process supervision tied to Windows Task Scheduler. Restart-only model (V15.1: NEVER reload code on the fly). |
| `start_supervisor_clean.ps1` | PowerShell — Windows native. Wired to `MERDIAN_Intraday_Supervisor_Start` task. |
| `gamma_engine_monitor_dashboard.py` | GUI dashboard (Tkinter / Streamlit). |
| `gamma_engine_alert_daemon.py` | Companion alert process to monitor dashboard. |
| `merdian_pipeline_alert_daemon.py` | Pipeline-stage alerting. Currently running PID 19636. |
| `merdian_signal_dashboard.py` | Live signal table + Pine refresh + LOG TRADE button (V19, Phase 4A). |
| `merdian_live_dashboard.py` | Live session state + token countdown (V18E v2). |
| `merdian_trade_logger.py` | Phase 4A manual trade entry. Couples human button-press to signal_snapshots row. |
| `detect_po3_session_bias.py` | Runs Mon-Fri 10:05 IST via `MERDIAN_PO3_SessionBias_1005` (ENH-75). |
| `build_atm_option_bars_mtf.py` | MTF option bar rollup. |
| `build_hist_pattern_signals_5m.py` | Pattern backfill. |
| `build_ict_htf_zones_historical.py` | Historical ICT zone backfill. |
| `build_signal_regret_log_v1.py` | Regret log builder. |
| `build_spot_bars_mtf.py` | Spot MTF rollup at 16:00 via `MERDIAN_Spot_MTF_Rollup_1600`. |
| `merdian_start.py` | **CRITICAL — Local-only script that uses Windows-only `creationflags=CREATE_NO_WINDOW` and hardcoded Windows paths. Running on MERDIAN AWS causes frozen SSM terminal requiring EC2 reboot.** See §6 gotcha #1. |
| `run_market_tape_1m.py` | Was scheduled via `MERDIAN_Market_Tape_1M` (now Ready). DhanError 401 — functionally disabled even though task is Ready. Replaced by `capture_spot_1m_v2.py`. |

### A.2 Newly catalogued (Session 23 Task Scheduler audit)

These scripts and wrappers were discovered via the canonical action mapping. Each is wired to a Task Scheduler entry; the JSON's `files` inventory does not yet contain all of them.

| Script | Wired to | Purpose |
|---|---|---|
| `merdian_watchdog.py` | `MERDIAN_HB_Watchdog` (TimeTrigger interval) | Process killer — `--kill` flag terminates hung Python processes. Runs as `pythonw.exe` (no CMD window). |
| `watchdog_check.ps1` | `MERDIAN_Watchdog` (TimeTrigger interval) | Companion to `merdian_watchdog.py` — passive state-check / alert layer. PowerShell. |
| `merdian_morning_start.ps1` | `MERDIAN_Intraday_Supervisor_Start` | Morning supervisor entry point. Likely invokes `start_supervisor_clean.ps1` internally; canonical morning launch. |
| `capture_spot_1m.py` | `MERDIAN_PreOpen` (~09:08 IST) | PreOpen 1-min spot capture. Runs as `pythonw.exe`. |
| `capture_spot_1m_v2.py` | `MERDIAN_Spot_1M` (1-min cadence) | **Active 1-min spot ingester** — replaces disabled `run_market_tape_1m.py`. Runs as `pythonw.exe`. |
| `run_daily_audit.bat` | `MERDIAN_Daily_Audit` (daily) | Daily DB / system audit wrapper |
| `run_eod_breadth_refresh.ps1` | `MERDIAN_EOD_Breadth_Refresh` (daily) | EOD breadth indicator refresh |
| `run_iv_context_once.ps1` | `MERDIAN_IV_Context_0905` (09:05 IST) | PowerShell wrapper around `compute_iv_context_local.py` |
| `run_ict_htf_zones_daily.bat` | `MERDIAN_ICT_HTF_Zones_0845` (08:45 IST) | Bat wrapper around `build_ict_htf_zones.py`. **S28 update (TD-NEW-5):** chained Pine overlay generation appended as Call 3; `generate_pine_overlay.py` now invoked automatically after zone build. |
| `run_po3_session_bias_once.bat` | `MERDIAN_PO3_SessionBias_1005` (10:05 IST) | Bat wrapper around `detect_po3_session_bias.py` |
| `run_market_close_capture_once.bat` | `MERDIAN_Market_Close_Capture` (~15:30 IST) | Local mirror of MERDIAN AWS's `run_market_close_capture_once.py` |
| `run_post_market_capture_once.bat` | `MERDIAN_Post_Market_1600_Capture` (~16:00 IST) | Local equivalent of MERDIAN AWS's `capture_postmarket_1600.py` (different script — see Topology §7.2 Note 2) |
| `run_market_spot_session_markers_once.bat` | `MERDIAN_Session_Markers_1602` (16:02 IST) | Post-close session markers update wrapper |
| `run_market_tape_1m.bat` | `MERDIAN_Market_Tape_1M` (functionally disabled) | Bat wrapper around `run_market_tape_1m.py` (auth-failing) |
| `run_ws_feed_zerodha.bat` | `MERDIAN_WS_Feed_0900` (functionally disabled S28 TD-NEW-6) | Bat wrapper around `ws_feed_zerodha.py`. **S28 update (TD-NEW-6):** Local task DISABLED via `Disable-ScheduledTask`; was a dead-stub firing daily and polluting logs. The actual production WS feed runs on MERDIAN AWS only. |
| `run_spot_mtf_rollup_once.bat` | `MERDIAN_Spot_MTF_Rollup_1600` (16:00 IST) | Wraps `build_spot_bars_mtf.py` |

These additions are pending integration into `merdian_reference.json` `files` (file paths and statuses) — that's a follow-up commit. This Topology is the canonical wiring map; the JSON is the canonical inventory.

---

## §3 — MERDIAN AWS-only scripts

These run only on MERDIAN AWS, primarily for scheduled redundancy or because AWS has reliable always-on cron when Local may be off, or for Dhan-IP-whitelisting reasons (Phase 4B order placer).

| Script | Why MERDIAN AWS-only |
|---|---|
| `run_merdian_shadow_runner.py` | Shadow 5-min cycle. Breadth ingest disabled (V18E Guard 3 — single-writer rule). Runs in nohup. **S28 update (TD-NEW-12):** line 479 now passes `--shadow` flag to `compute_gamma_metrics_local.py` invocation. Routes AWS compute writes to `gamma_metrics_shadow` table (the architectural intent restored). |
| `capture_postmarket_1600.py` | 16:00 IST close capture. JSON marks AWS-only. **Topology question:** Local also has `MERDIAN_Post_Market_1600_Capture` task — see §6 gotcha #5. |
| `run_market_close_capture_once.py` | AWS parity for close capture. Created V18A. |
| `merdian_order_placer.py` | **Phase 4B Order Placer (S28 surfacing)** — HTTP server on port 8767. Exposes `/place_order`, `/square_off`, `/order_status`, `/margin` endpoints called by Local dashboard's PLACE ORDER button. AWS-only because Dhan Trading API whitelists IP `13.63.27.85` (MERDIAN AWS Elastic IP); Local's multi-WAN home network has unstable IP. Launched via `@reboot` cron entry (deliberately persistent). Has been running deployed-but-low-traffic since 2026-04-29 (HTTP server idle most of the day, occasionally polled for margin / health). Was not catalogued in the original Topology — TD-NEW-11 (S3, documentation gap) filed Session 28 + closed here by the catalog. |

---

## §4 — Both-environments scripts (Local + MERDIAN AWS)

These run on both Local and MERDIAN AWS. The boundary is operational, not architectural — Local is primary, MERDIAN AWS is shadow / fallback / EOD.

| Script | Local role | MERDIAN AWS role |
|---|---|---|
| `capture_market_spot_snapshot_local.py` | 1-min spot capture (Step 1 of intraday runner) | Cron `MERDIAN_PreOpen` 09:08 IST + on-demand by shadow runner |
| `capture_index_futures_snapshot_local.py` | Futures snapshot in cycle | Shadow capture |
| `ingest_option_chain_local.py` | Step 2 of cycle (Dhan REST + writes via Zerodha WS path) | Shadow ingest. Note: depends on Zerodha access token propagated from MALPHA (§1.5 / TD-NEW-7). |
| `ingest_breadth_from_ticks.py` | Live breadth ingest (single-writer) | **DISABLED on MERDIAN AWS** (Guard 3 — single-writer rule) |
| `ingest_equity_eod_local.py` | EOD recovery path | Primary 16:10 IST cron via `run_equity_eod_until_done.py` wrapper |
| `build_market_state_snapshot_local.py` | Step 7 of cycle | Shadow path |
| `compute_gamma_metrics_local.py` | Step 3 — writes to **`gamma_metrics`** (no flag) | Shadow — writes to **`gamma_metrics_shadow`** (`--shadow` flag, S28 TD-NEW-12) |
| `compute_iv_context_local.py` | Morning task `MERDIAN_IV_Context_0905` + per-cycle | Shadow |
| `compute_volatility_metrics_local.py` | Step 5 | Shadow |
| `build_momentum_features_local.py` | Step 6 | Shadow |
| `build_wcb_snapshot_local.py` | Per-cycle | Shadow |
| `build_trade_signal_local.py` | Step 9 — production signals | Shadow signals |
| `build_ict_htf_zones.py` | `MERDIAN_ICT_HTF_Zones_0845` task | Shadow build |
| `detect_ict_patterns.py` / `detect_ict_patterns_runner.py` | Step 8 of cycle | Shadow |
| `evaluate_shadow_vs_live.py` | Comparison runner. **Becomes meaningful S29+** once `gamma_metrics_shadow` has rows from S28 TD-NEW-12 onwards. | Comparison runner |
| `run_equity_eod_until_done.py` | Manual recovery | Primary EOD cron |
| `trading_calendar.py` | Hard gate at every cycle entry | Hard gate |
| `stage2_db_contract.py` | Pre-write contract check | Pre-write contract check |
| `refresh_dhan_token.py` | Local Task Scheduler trigger writes new token to .env + Supabase | MERDIAN AWS cron `MERDIAN_Token_Refresh` 09:05 IST + Supabase pull at 03:05 UTC |
| `merdian_utils.py` | Utility imports | Utility imports |

---

## §5 — Token flow

### 5.1 Dhan token flow

```
   Daily 08:35-ish IST
   ┌─────────────────────────────────────────────────────────┐
   │ Local Windows                                           │
   │   Task Scheduler triggers refresh_dhan_token.py         │
   │   ↓ (browser TOTP if needed, V18E auto-retry on InvalidTOTP)
   │   Writes new DHAN_ACCESS_TOKEN to:                      │
   │     - .env file (local)                                 │
   │     - Supabase row (system_config or equivalent)        │
   └─────────────────────────────────────────────────────────┘
                          │
                          │ Supabase replication
                          ▼
   ┌─────────────────────────────────────────────────────────┐
   │ MERDIAN AWS EC2                                         │
   │   Cron 03:05 UTC = 08:35 IST (shifted from 03:55 UTC)   │
   │     ↓                                                   │
   │   Pulls latest token from Supabase                      │
   │   Writes to /home/ssm-user/meridian-engine/.env         │
   │                                                         │
   │   Cron MERDIAN_Token_Refresh 09:05 IST                  │
   │     ↓                                                   │
   │   refresh_dhan_token.py — verification + retry on AWS   │
   └─────────────────────────────────────────────────────────┘
```

**Critical timing:** AWS pull at 03:05 UTC was shifted from 03:55 UTC specifically to allow Local Supabase sync to complete before AWS pulls. Reverting the shift breaks the chain.

### 5.2 Zerodha token flow (S28 state — TD-NEW-7 pending)

```
   MALPHA AWS (Kite gateway)
   ┌─────────────────────────────────────────────────────────┐
   │   Browser-based auth + TOTP (headless-interactive)      │
   │     ↓                                                   │
   │   Zerodha access token written to MALPHA .env           │
   └─────────────────────────────────────────────────────────┘
                          │
                          │ MANUAL sed step (TD-NEW-7 S1 fragility)
                          ▼
   ┌─────────────────────────────────────────────────────────┐
   │ MERDIAN AWS EC2                                         │
   │   /home/ssm-user/meridian-engine/.env updated by hand   │
   │   ↓                                                     │
   │   Kite REST calls work; ingest_option_chain_local.py    │
   │   subprocesses use this token for Zerodha-side reads    │
   └─────────────────────────────────────────────────────────┘

   Local Windows (PARALLEL, independent)
   ┌─────────────────────────────────────────────────────────┐
   │   Browser-based auth + TOTP                             │
   │     ↓                                                   │
   │   Zerodha access token written to Local .env / kite_session
   │     ↓                                                   │
   │   ws_feed_zerodha.py uses KiteTicker WebSocket          │
   │     ↓                                                   │
   │   option_chain_snapshots (NIFTY full chain rows)        │
   │                                                         │
   │   MERDIAN AWS does NOT participate in WebSocket path.   │
   └─────────────────────────────────────────────────────────┘
```

**Outages traced to manual step:** 2026-04-22 and 2026-05-12 both presented as `ingest_option_chain_local.py` failing AWS-side because Local had a stale Zerodha token. Fix design under TD-NEW-7: replace manual `sed` with Supabase `system_config` write on MALPHA + extend MERDIAN AWS `pull_token_from_supabase.py` to handle Zerodha key. Mirrors Dhan flow exactly.

### 5.3 Token-related runbook references

- `docs/runbooks/runbook_update_dhan_token.md` — full Dhan rotation procedure
- `docs/runbooks/runbook_update_kite_flow.md` — Zerodha update + verification (Step 3 runs `/home/ssm-user/meridian-engine/check_kite_auth.py`). **Update S28:** runbook gap surfaced — runbook does not currently document the manual `sed` step on MERDIAN AWS. Update queued alongside TD-NEW-7 fix.
- `docs/runbooks/runbook_recover_dhan_401.md` — DhanError 401 recovery

---

## §6 — AWS gotchas (DO NOT)

These are operational rules learned from real failures. Each is honored by current code; documenting them here so they remain honored. **All §6 rules apply to MERDIAN AWS unless otherwise noted; MALPHA is a separate environment and operates under separate rules.**

### 6.1 NEVER run `merdian_start.py` on MERDIAN AWS

Uses Windows-only `creationflags=CREATE_NO_WINDOW` and hardcoded Windows paths. Running on AWS:
- **Causes frozen SSM Session Manager terminal**
- **Requires EC2 reboot to recover**

This script is Local-only by design. There is no Linux equivalent. AWS bootstraps via cron + nohup; no equivalent to Local's supervisor.

### 6.2 NEVER use interactive `crontab -e` on MERDIAN AWS

Always use the non-interactive temp-file install pattern:
```bash
crontab -l > /home/ssm-user/meridian-engine/logs/aws_crontab_snapshot_$(date +%Y%m%d_%H%M%S).txt
# build new crontab to /tmp/merdian_cron_new.txt (sed edit or full rewrite)
diff <(crontab -l) /tmp/merdian_cron_new.txt   # always diff first
crontab /tmp/merdian_cron_new.txt
crontab -l | head -30
```

The reason: a malformed entry in interactive `crontab -e` can replace the entire crontab atomically with whatever was in the buffer. Snapshot every change to a timestamped file under `logs/`.

### 6.3 NEVER direct-edit code on MERDIAN AWS (CLAUDE.md non-negotiable rule 1)

Edit only in Local. MERDIAN AWS receives code via `git pull`. The only exception is BREAK_GLASS (Change Protocol Step 8) and even that requires a Local commit to backfill within 24h. Direct edits on AWS:
- Get clobbered on next `git pull`
- Create silent Local↔AWS hash mismatch (preflight FAIL)
- Are a known anti-pattern from Sessions 4–6

### 6.4 NEVER enable breadth ingest on MERDIAN AWS

V18E Guard 3 — single-writer rule. `ingest_breadth_from_ticks.py` running on both environments would produce double-writes to `market_breadth_intraday`. AWS shadow runner explicitly disables breadth ingest via flag. Do not "fix" the disabled flag without understanding the rule.

### 6.5 NEVER assume shadow output equals live output

Shadow runner writes to dedicated shadow tables / shadow columns. The output of AWS shadow is **not** a backup of Local live signals. Before `evaluate_shadow_vs_live.py` reports parity, do not act on AWS-emitted signals as if they were live decisions.

**S28 update (TD-NEW-12 RESOLVED):** Until Session 28, this rule was honored in narrative but silently violated in code — `gamma_metrics_shadow` table existed but was empty, because `compute_gamma_metrics_local.py` on MERDIAN AWS wrote to production `gamma_metrics`, race-condition double-writing rows that Local wrote. Resolution: `--shadow` flag (TARGET_TABLE pattern) routes all reads + writes + telemetry to `gamma_metrics_shadow` when MERDIAN AWS invokes the script via `run_merdian_shadow_runner.py` line 479. Rule is now enforced architecturally, not just narratively. See D.11.1 in Assumption Register for the codified invariant.

### 6.6 Cron entries must use the env-loading pattern

Every cron entry must include:
```bash
/bin/bash -lc 'set -a; . ./.env; set +a; <command>'
```
Without this, `os.environ.get('SUPABASE_URL')` returns `None` and the script fails silently (or writes garbage). The `-lc` ensures login shell behavior.

### 6.7 SSH IP whitelisting fragility

Navin's Local environment runs a multi-WAN home network with load-balancer failover. Static IP whitelisting in the AWS security group breaks when the WAN flips. Permanent fix is **AWS Systems Manager Session Manager** instead of SSH (open ENH/TD candidate). Workaround: update the security group inbound rule when ISP IP changes.

### 6.8 Shadow tables must match production schema (TD-NEW-12 S28)

If a `<table>_shadow` exists for write-comparison purposes (e.g. `gamma_metrics_shadow`), it must match the production `<table>` schema column-for-column AND constraint-for-constraint. Symptoms of drift surface only when AWS-side writes actually fire (which itself was only true post-S28 for `gamma_metrics_shadow` — pre-S28 it was empty):

- Missing columns → `PGRST204 schema cache` errors on `payload` upsert.
- Missing UNIQUE constraint matching the upsert `on_conflict` clause → `42P10 no unique or exclusion constraint matching the ON CONFLICT specification`.

**Cause:** Shadow tables were typically created via `CREATE TABLE ... LIKE <production> INCLUDING ...` without `INCLUDING ALL` — copies columns but drops constraints + indexes. New columns added to production over time (via `ALTER TABLE`) are not propagated automatically to shadow.

**Discipline going forward:**

1. When adding columns to a production table, simultaneously `ALTER TABLE <name>_shadow ADD COLUMN IF NOT EXISTS ...` if a shadow table exists.
2. Periodic schema-diff sweep (suggested as ENH candidate) compares `information_schema.columns` between production and `<name>_shadow` for all known shadow-paired tables.
3. NOTIFY pgrst, 'reload schema' after ALTER if PostgREST is caching old schema.

### 6.9 Python version parity between Local and MERDIAN AWS (TD-NEW-13 S28)

Local runs Python 3.12; MERDIAN AWS runs Python 3.10. The two stdlibs differ in `datetime.fromisoformat()` permissiveness — Python 3.10 rejects microsecond fractions that are not exactly 3 or 6 digits; Python 3.12 accepts arbitrary precision. Supabase serializes PostgreSQL timestamps with variable precision (2-7 digits common).

**Symptom:** Code that parses ISO timestamps via `fromisoformat()` runs fine on Local, fails on MERDIAN AWS, on a fraction of timestamps (those whose microsecond field length happens to be non-3/6). Failures are silent on Local-only smoke tests.

**Required discipline for any ISO-timestamp-parsing code path:**

1. Normalize the microsecond field to exactly 6 digits before `fromisoformat()` via regex pad/truncate (see `_dte_from_ts` in `compute_gamma_metrics_local.py` for the canonical pattern).
2. Smoke test on MERDIAN AWS — not just Local — when any new compute path consumes Supabase timestamps.
3. Long-term: align Python versions (upgrade MERDIAN AWS to 3.12), but until then, normalize defensively.

See D.11.3 in Assumption Register for the codified invariant. See CLAUDE.md B22 (filed S28) for the operational rule.

### 6.10 Token edits to `.env` do not restart consumer processes (S29 firefighting, TD-NEW-A 2026-05-14)

Editing `ZERODHA_ACCESS_TOKEN` in `/home/ssm-user/meridian-engine/.env` does **not** affect a long-running `ws_feed_zerodha.py` instance. The feeder loaded the token at process start and holds it in memory until killed. Symptom of skipping the consumer restart is identical to skipping the sed: empty `market_ticks` all day. On 2026-05-14 the operator correctly propagated the new token to `.env` twice and verified via `kite.profile()` AUTH OK, but the running feeder process continued to hold the prior day's token loaded from yesterday's 09:14 IST cron start. Six hours of breadth cascade resulted.

**Diagnostic discipline:** When `market_ticks` is empty but `kite.profile()` returns AUTH OK, the failure mode is consumer-process-state, not token-propagation. Check `pgrep -f ws_feed_zerodha.py` — if the PID has been running since before the most recent `.env` edit, it must be killed and restarted. See `runbook_update_kite_flow.md` Step 2d (added S29).

**Operational rule:** Any `.env` edit on MERDIAN AWS requires explicit consumer-process restart of every script that reads the affected variable. There is no exception "if the value didn't really change" — the operator cannot verify in-memory state without restarting.

### 6.11 `pg_cron` failures are invisible by default (S29 firefighting, TD-NEW-B 2026-05-14)

The `cron.job_run_details` table records every cron run with `status` and `return_message`, but no MERDIAN telemetry polls it. A job can fail every weekday for weeks without any operator-visible signal until a downstream consumer notices.

**2026-05-14 incident:** `delete-old-market-ticks` (jobid 45) had been failing every weekday since at least 2026-04-30 (14+ consecutive runs) with `ERROR: canceling statement due to statement timeout`. Failed deletes left `market_ticks` accumulating without bound to 62 GB, which caused INSERTs from `ws_feed_zerodha.py` to also exceed statement_timeout, cascading into the §6.10 incident.

**Operator session-start checklist (manual workaround until TD-NEW-B health-check daemon lands):**

```sql
SELECT jobname, status, return_message, start_time
FROM cron.job_run_details d JOIN cron.job j USING (jobid)
WHERE start_time > now() - interval '7 days' AND status != 'succeeded'
ORDER BY start_time DESC;
```

Empty result = healthy. Any rows = investigate. Add to morning session-start ritual.

**Long-term:** TD-NEW-B (S1) is the polling daemon implementation. Either (a) extension of `merdian_pipeline_alert_daemon.py` to query `cron.job_run_details` every N minutes and Telegram-alert on failure, or (b) dashboard widget surfacing recent failures. Either approach closes the failure class.

**Design rule:** Any pg_cron job added to production must be accompanied by either (a) a polling check that surfaces failures within 24 hours, or (b) an explicit entry in the operator session-start checklist. See CLAUDE.md B26 (filed S29) for the codified rule.

---

## §7 — Cron entries (MERDIAN AWS) and Task Scheduler entries (Local)

### 7.1 MERDIAN AWS crontab (6 entries — S28 update)

Source: `merdian_reference.json` `aws_cron`. Confirmed via `crontab -l > logs/aws_crontab_snapshot_*.txt` discipline.

| Label | Time IST | Cron | Action |
|---|---|---|---|
| `MERDIAN_Token_Refresh` | 09:05 | `5 9 * * 1-5` | `refresh_dhan_token.py` |
| `MERDIAN_PreOpen` | 09:08 | `8 9 * * 1-5` | `capture_market_spot_snapshot_local.py` |
| `MERDIAN_Shadow_Runner` | 09:15 | `45 3 * * 1-5` (UTC) | `run_merdian_shadow_runner.py` (nohup) — **passes `--shadow` to compute_gamma_metrics_local from S28 TD-NEW-12 commit `de23467`** |
| `MERDIAN_WS_Stop` | 15:32 | `02 10 * * 1-5` (UTC) | `pkill -9 -f ws_feed_zerodha.py`. **S28 update (TD-NEW-8):** SIGTERM → SIGKILL upgrade. WS process was ignoring SIGTERM; accumulated 9 zombies over Apr 30 → May 11 (1.4GB RAM impact). |
| `MERDIAN_Postmarket` | 16:00 | `30 10 * * 1-5` | `capture_postmarket_1600.py` (NOT YET PROVEN — A-02 open) |
| `MERDIAN_EOD` | 16:10 | `40 10 * * 1-5` | `run_equity_eod_until_done.py` (cursor-gate not ported — A-04 open) |

Plus `@reboot` entries:

| Trigger | Action |
|---|---|
| `@reboot` | `merdian_signal_dashboard.py` (port nohup) |
| `@reboot` | `merdian_order_placer.py` (port 8767 HTTP server — see §3) |

Times in cron column are mostly UTC; IST = UTC + 5:30. Day-range `1-5` = Mon-Fri. The Token_Refresh + PreOpen + Postmarket + EOD entries display IST in this table for legibility; UTC is the actual cron specifier.

### 7.2 Windows Task Scheduler (20 entries — Session 36 update, 2026-05-25; was 19 at S29 audit, 2026-05-14)

Source: `Get-ScheduledTask -TaskName "MERDIAN_*"` PowerShell audit during S29 firefighting (`migrate_to_pythonw.ps1` dry-run reported `[INFO] Found 19 MERDIAN_* tasks`). Action mapping captured via two PowerShell passes (§2.5 + §2.6 of S29 firefighting handoff). **This is the canonical inventory** — supersedes the 17-entry S23 list. **TD-061 RESOLVED 2026-05-14** — 13/19 tasks now on `pythonw.exe`, 18/19 with `Hidden=$true + MultipleInstances=IgnoreNew`. **TD-NEW-E CLOSED** — 2 newly-discovered tasks (`MERDIAN_Dhan_Token_Refresh`, `MERDIAN_Intraday_Session_Start`) included; purpose-of-task investigation pending operator confirmation.

| Task | State | Action.Execute | Action.Arguments | Hidden | MultipleInstances | Notes |
|---|---|---|---|---|---|---|
| `MERDIAN_Daily_Audit` | Ready | `pythonw.exe` | `merdian_daily_audit.py` | TRUE | IgnoreNew | S29 migrated from .bat wrapper to direct pythonw. Backup `backups\scheduler\20260514_184211\`. |
| `MERDIAN_Dhan_Token_Refresh` | Ready | (unchanged — UNHANDLED) | (unchanged) | TRUE | IgnoreNew | **NEW TASK discovered S29.** Purpose unverified — operator confirmation pending. Settings hardened S29; action untouched. |
| `MERDIAN_EOD_Breadth_Refresh` | Ready | `pythonw.exe` | `run_equity_eod_until_done.py` | TRUE | IgnoreNew | S29 migrated — wrapper `run_eod_breadth_refresh.ps1` dropped; task now direct pythonw. Wrapper kept on disk unreferenced; delete after 1 week stability. |
| `MERDIAN_HB_Watchdog` | Ready | `pythonw.exe` | `merdian_watchdog.py --kill` | TRUE | IgnoreNew | Already pythonw pre-S29. `--kill` flag = process killer for hung runners. |
| `MERDIAN_ICT_HTF_Zones_0845` | Ready | `pythonw.exe` | `run_ict_htf_zones_daily.py` | TRUE | IgnoreNew | S29 — **new Python orchestrator** replaces `.bat` (which couldn't collapse to single pythonw call because it chains 3 scripts + rc-fold). See §2.7 of S29 handoff for orchestrator behavior. |
| `MERDIAN_Intraday_Session_Start` | Ready | (unchanged — UNHANDLED) | (unchanged) | TRUE | IgnoreNew | **NEW TASK discovered S29.** Purpose unverified — operator confirmation pending. Settings hardened S29; action untouched. |
| `MERDIAN_Intraday_Supervisor_Start` | Ready | (unchanged — settings-only-fail) | (unchanged) | unchanged | unchanged | **Only task where Settings update failed S29** — multi-trigger XML (Weekly Mon-Fri 08:00 + AtLogon) caused `Set-ScheduledTask -Settings <obj>` to fail. Workaround: build full Register-ScheduledTask XML + Force overwrite. Filed as TD candidate for next Task Scheduler touch. Action canonically `powershell.exe -File merdian_morning_start.ps1`. |
| `MERDIAN_IV_Context_0905` | Ready | `pythonw.exe` | `compute_iv_context_local.py` | TRUE | IgnoreNew | S29 — wrapper `run_iv_context_once.ps1` dropped. Task points direct at pythonw. |
| `MERDIAN_Live_Dashboard` | Ready | `pythonw.exe` | `merdian_live_dashboard.py --no-browser` | TRUE | IgnoreNew | Already pythonw pre-S29. `--no-browser` prevents auto-launching Streamlit browser. |
| `MERDIAN_Market_Close_Capture` | Ready | `pythonw.exe` | `C:\GammaEnginePython\capture_market_spot_snapshot_local.py` | TRUE | IgnoreNew | S29 migrated — was `cmd /c run_market_close_capture_once.bat`. Now direct pythonw. |
| `MERDIAN_Market_Tape_1M` | Ready (broken since 2026-04-07) | (unchanged) | (unchanged) | TRUE | IgnoreNew | **Still broken** — `run_market_tape_1m.py` fails DhanError 401 daily. `MERDIAN_Spot_1M` running `capture_spot_1m_v2.py` is the active replacement. Recommend Disabled; not closed S29. |
| `MERDIAN_Orphan_Janitor` | Ready | `pythonw.exe` | `orphan_run_janitor.py` | TRUE | IgnoreNew | **NEW S36 (ENH-99 Component 2).** Weekly Mon-Fri 09:14 IST. Closes any `script_execution_log` row in state RUNNING aged > 5 min by PATCHing `exit_reason='DATA_ERROR'` + `notes='ORPHAN_RECOVERED: age_min=N'` prefix + `finished_at=now()` + `duration_ms=<min(actual_age_ms, 2147483647)>` (int4 clamp at `2^31-1` per D.18.4). 5min execution limit + battery flags + Interactive Limited principal. Smoke-fire test 2026-05-25 17:26:26 closed 22/24 orphans + 2 REPL stragglers; final state 0 RUNNING > 5min. |
| `MERDIAN_PO3_SessionBias_1005` | Ready | `pythonw.exe` | `detect_po3_session_bias.py` | TRUE | IgnoreNew | S29 — wrapper `run_po3_session_bias_once.bat` dropped. ENH-75 SHIPPED S13. |
| `MERDIAN_Post_Market_1600_Capture` | Ready | `pythonw.exe` | `C:\GammaEnginePython\capture_market_spot_snapshot_local.py` | TRUE | IgnoreNew | S29 migrated. **Same script as Market_Close_Capture but different boundary timing.** Different from MERDIAN AWS `capture_postmarket_1600.py` — see Note 2. |
| `MERDIAN_PreOpen` | Disabled (S25) | `pythonw.exe` | `capture_spot_1m.py` | TRUE | IgnoreNew | **State=Disabled S25 — durable.** Settings hardened S29 even though disabled (defensive — in case ever re-enabled). Different script from MERDIAN AWS PreOpen — see Note 3 + §9.A. |
| `MERDIAN_Session_Markers_1602` | Ready | `pythonw.exe` | `C:\GammaEnginePython\build_market_spot_session_markers.py` | TRUE | IgnoreNew | S29 migrated. Post-close session markers update — feeds `market_spot_session_markers.open_0915_ts` for next-day reference. |
| `MERDIAN_Spot_1M` | Ready | `pythonw.exe` | `capture_spot_1m_v2.py` | TRUE | IgnoreNew | Already pythonw pre-S29. **Active 1-min spot ingester** replacing disabled `MERDIAN_Market_Tape_1M`. |
| `MERDIAN_Spot_MTF_Rollup_1600` | Ready | `pythonw.exe` | `build_spot_bars_mtf.py` | TRUE | IgnoreNew | S29 migrated — was `Start-Process cmd /c run_spot_mtf_rollup_once.bat`. Now direct. S9 closure of TD-019/023, ENH-71 instrumented. |
| `MERDIAN_Watchdog` | Ready | (unchanged — settings-only) | (unchanged) | TRUE | IgnoreNew | `.ps1` passive observer (state check, not process killer). Cannot migrate to pythonw — it's PowerShell, not Python. Settings hardened S29. |
| `MERDIAN_WS_Feed_0900` | Disabled (S28) | (unchanged) | (unchanged) | TRUE | IgnoreNew | **State=Disabled S28 (TD-NEW-6) — durable.** Was dead-stub firing daily polluting logs; actual WS feed runs on MERDIAN AWS only. Settings hardened S29 defensively. |

**Counts (S29 final state):**
- **13 actions on pythonw** (was 4 at S29-start; 9 migrated during S29 firefighting).
- **18 of 19 settings tightened** with `Hidden=$true + MultipleInstances=IgnoreNew + ExecutionTimeLimit=30min + battery flags`. Only `Intraday_Supervisor_Start` retains loose settings due to multi-trigger XML quirk.
- **5 residual window-flash sources:** Intraday_Supervisor_Start (08:00 + logon), Watchdog (interval-based, can't migrate — PowerShell), Intraday_Session_Start (unknown cadence pending verification), Dhan_Token_Refresh (once-per-morning), Market_Tape_1M (broken-but-firing daily). All five are low-frequency; daily flash count expected to drop dramatically from "gazillion" (operator term) to single digits.

**Counts (S36 update — additive to S29 baseline):**
- **14 actions on pythonw** (was 13 at S29; `MERDIAN_Orphan_Janitor` added S36 — direct pythonw).
- **19 of 20 settings tightened** with `Hidden=$true + MultipleInstances=IgnoreNew`. `MERDIAN_Intraday_Supervisor_Start` retains loose settings (S29 multi-trigger XML quirk — unchanged S36).
- **Residual window-flash sources unchanged S36** (5 sources from S29 baseline).


**Backups (S29):**
- `backups\scheduler\20260514_184211\*.xml` — all 18 task XMLs from v1 `migrate_to_pythonw.ps1 -Apply` run.
- `backups\scheduler\20260514_190443\*.xml` — 4 task XMLs from phase-2 wrapper-drop run (ICT_HTF, EOD_Breadth, IV_Context, PO3_SessionBias).

#### Notes — clarified by canonical action mapping

**Note 1: `MERDIAN_Market_Tape_1M` Ready ≠ functional.** Task state shows `Ready` but `run_market_tape_1m.py` has been failing with `DhanError 401` on every run since 2026-04-07. `MERDIAN_Spot_1M` running `capture_spot_1m_v2.py` is the active replacement. Two cleanup paths: (a) disable `MERDIAN_Market_Tape_1M` in Task Scheduler to match script reality, (b) fix the auth issue. Recommend (a). Filed as TD candidate; not closed S29.

**Note 2: Post-market capture is two different scripts on two environments.** Local task `MERDIAN_Post_Market_1600_Capture` runs `capture_market_spot_snapshot_local.py` (S29 — was `.bat` wrapper); MERDIAN AWS cron `MERDIAN_Postmarket` runs `capture_postmarket_1600.py`. Different scripts, parallel implementations of the same intent. Dual-write status confirmed S25 — disposition queued for ADR-006 execution gated on TD-080. After S29 migration to direct pythonw, the Local writer is `capture_market_spot_snapshot_local.py` not the prior `.bat` chain.

**Note 3: PreOpen 09:08 is two different scripts.** Local `MERDIAN_PreOpen` runs `capture_spot_1m.py`; MERDIAN AWS cron `MERDIAN_PreOpen` runs `capture_market_spot_snapshot_local.py`. Local task DISABLED S25 (durable); AWS is sole writer. Boundary closed at AWS. See §9.A.

**Note 4 (NEW S29): `MERDIAN_Dhan_Token_Refresh` and `MERDIAN_Intraday_Session_Start` — purpose pending verification.** Both tasks discovered during S29 audit but their actions were not modified (UNHANDLED in the migration script's whitelist). Settings hardened to `Hidden + IgnoreNew`. Operator should verify (a) what scripts they invoke, (b) what cadence, (c) whether they're production-active. Once verified, file a §A.2 catalog entry and update this table's Notes column. Filed as follow-up to TD-NEW-E (CLOSED in this rewrite, with the verification step as a follow-up).

**Note 5 (NEW S29): `MERDIAN_ICT_HTF_Zones_0845` action changed from `.bat` to Python orchestrator.** The 3-step chain (`build_ict_htf_zones.py --timeframe both` → `--timeframe H` → `generate_pine_overlay.py`) with rc-fold and per-call banner logging could not collapse to a single pythonw call. Solution: wrote `run_ict_htf_zones_daily.py` Python orchestrator that does the same 3 subprocess calls, preserves rc-fold via `max(rc_wd, rc_h, rc_pine)`, and preserves banner format bit-identical to the `.bat` output. `sys.executable` (= pythonw when launched by pythonw) ensures child subprocesses also use pythonw — no cmd windows at any level. Old `.bat` kept on disk unreferenced; delete after 1 week of stability.

#### Architectural insights from the audit

1. **TD-061 RESOLVED 2026-05-14** (was: partially complete since S17/S18). 13/19 tasks now run `pythonw.exe` directly (no cmd intermediary). 18/19 tasks have `MultipleInstances=IgnoreNew` (= TD-063 RESOLVED). 5 residual window flashes are low-frequency sources documented above. **Lesson:** S18 footer claimed TD-061 RESOLVED but body remained Active; S23 audit confirmed only 4/15 migrated; S29 audit found 19 tasks (vs S23's 17) and only 4/19 on pythonw. Codified as Doc Protocol v4 candidate Rule N — **TD body-state must match footer-claim**.

2. **Two watchdog architectures coexist intentionally.** `merdian_watchdog.py --kill` (process killer) runs as pythonw; `watchdog_check.ps1` is the passive observation layer (PowerShell, cannot migrate to pythonw). They run on different intervals. Architecturally complementary, not redundant.

3. **Three-environment isolation discipline survived stress.** S29 firefighting touched 19 Local tasks + 0 AWS cron entries + 0 MALPHA code — environment boundaries held even under unplanned firefighting pressure. TD-061's earlier "partial closure" failure mode would have leaked into AWS if the migration discipline was sloppier.

4. **`merdian_morning_start.ps1` content remains undocumented.** S23 noted this; S29 did not investigate. Open question §9 Q4 still applies. Low priority since the task is `Ready` and firing as expected; investigation when convenient.



---

## §8 — Runtime artifacts per environment

### 8.1 Local Windows runtime artifacts

Located under `C:\GammaEnginePython\runtime\`:

| Path | Purpose |
|---|---|
| `runtime/telemetry/latest_health_snapshot.json` | Most recent health snapshot, single object (overwritten each cycle) |
| `runtime/telemetry/health_snapshots.jsonl` | Append-only per-cycle health log |
| `runtime/telemetry/health_events.jsonl` | DEGRADED ↔ RECOVERED transitions |
| `runtime/telemetry/alerts.jsonl` | Alert fire log (deduped) |
| `runtime/telemetry/alert_state.json` | Active alerts and last-fired timestamps |
| `runtime/logs/<runner>.log` | Per-runner log files |
| `runtime/lock/*.lock` | Single-instance enforcement (TD-063 candidate) |

### 8.2 MERDIAN AWS runtime artifacts

Located under `/home/ssm-user/meridian-engine/`:

| Path | Purpose |
|---|---|
| `logs/aws_shadow_runner.nohup.log` | nohup output of shadow runner |
| `logs/dhan_token_refresh.log` | Daily Dhan token refresh log |
| `logs/premarket.log` | PreOpen capture log |
| `logs/postmarket.log` | Postmarket capture log |
| `logs/eod.log` | EOD ingest log |
| `logs/aws_crontab_snapshot_*.txt` | Timestamped snapshots of crontab — refreshed every install per §6.2 discipline |
| `logs/order_placer.log` | `merdian_order_placer.py` HTTP server log (S28 catalogued) |
| `logs/ws_feed.log` | Zerodha WebSocket feed log (Note: WS feed silent on success — TD-NEW-9 S2 filed for heartbeat instrumentation) |
| `logs/signal_dashboard.log` | `merdian_signal_dashboard.py` nohup log |
| `logs/backfill_logs/*` | Manual backfill operation logs (S28 broken-window P1 backfill artifacts) |
| `.env` | Environment file (DHAN_ACCESS_TOKEN refreshed 03:05 UTC daily; ZERODHA_ACCESS_TOKEN refreshed manually from MALPHA — TD-NEW-7) |

**Marketview frontend (NEW S40 — 2026-05-29):** A second codebase tree exists under `/home/ssm-user/meridian-connect/` (separate from `meridian-engine`):

| Path | Purpose |
|---|---|
| `/home/ssm-user/meridian-connect/` | Git clone of `balannavin-cyber1/meridian-connect` (Lovable-authored Vite + React frontend, public repo). Source-of-truth for the Marketview UI rendered at `http://13.63.27.85/marketview`. Cloned S40 to replace prior scp-built-html deploy pattern with an on-AWS `npm install && npm run build` pipeline. No `package-lock.json` is committed (Lovable doesn't emit one) — use `npm install` not `npm ci`. |
| `/home/ssm-user/meridian-connect/dist/` | Vite build output. Bundle filename hashes each build (S40 close: `index-vDqPX1iO.js`, ~537 KB — chunk-size warning is cosmetic, driven by Recharts + d3 inclusion). |
| `/var/www/marketview/` | nginx-served document root. Populated via `sudo rsync -av --delete dist/ /var/www/marketview/` after every build. Nginx config grep at S40 confirmed nginx serves static files from this directory at the `/marketview` location block. |
| `logs/` (no centralized log dir for Marketview) | The frontend has no server-side logs — it is a static SPA. All observability is browser-console + Supabase access logs. |

**Canonical Marketview deploy command (3-line, S40 codified):**
```
cd ~/meridian-connect && git pull && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx
```

The Marketview frontend reads Supabase directly using a `service_role` key sourced from `/home/ssm-user/meridian-engine/.env` (the Python writer env — Marketview shares the .env, does not have its own). The key is embedded in the built JS bundle, which is fine since the build is served only on the SEBI-whitelisted Elastic IP `13.63.27.85` and the broader public-internet exposure of the key is governed by `.env` removal from the public Git repo (TD-S39-NEW-3, carry-forward to S41 — operator local `git rm --cached .env` + push still pending at S40 close; S40 curl verified key still present on `balannavin-cyber1/meridian-connect` main branch).

MERDIAN AWS does **not** currently mirror Local's `runtime/telemetry/` directory. Heartbeat / health-snapshot infrastructure is Local-only.

### 8.3 MALPHA AWS runtime artifacts (S28 catalogued)

Located under `/home/ubuntu/meridian-alpha/`:

- Kite (Zerodha) token refresh service files (separate codebase, not in `meridian-engine` repo).
- Local `.env` containing the refreshed Zerodha access token.
- Service-specific logs (not mirrored to Meridian's audit trail).

MALPHA does not write to Meridian's Supabase tables today; that capability is queued for TD-NEW-7 (Zerodha token to `system_config`).

---

## §9 — Open boundary questions

Items where the Local↔AWS boundary is unresolved or requires verification. Updated post Session 23 action-mapping audit — three questions clarified, several remain. **S28 added Q12-Q14 covering MALPHA + order placer + shadow-table architecture.**

| # | Question | Status | Resolution path |
|---|---|---|---|
| 1 | Does Local `MERDIAN_Post_Market_1600_Capture` (`run_post_market_capture_once.bat`) and AWS `MERDIAN_Postmarket` (`capture_postmarket_1600.py`) write duplicate rows to `market_spot_snapshots`? | **CLOSED S25 2026-05-10 — confirmed dual-write** | Empirical SQL audit across 2026-05-04 → 2026-05-08 (5 trading days): both writers produced 16:00 IST rows on every day. **Disposition (per Phase α Q2 capture/derived split):** AWS canonical for capture stage; Local writer to be disabled. Action queued for ADR-006 execution phase, gated on TD-080 closure per Phase α Q3 sequencing. |
| 2 | Same question for PreOpen 09:08: Local (`capture_spot_1m.py`, pythonw) vs AWS (`capture_market_spot_snapshot_local.py`) | **CLOSED S25 2026-05-10 — original framing inaccurate** | Empirical audit revealed there was **no actual dual-write at 09:08 IST** — AWS is sole writer at the 09:08 boundary. Local `MERDIAN_PreOpen` was a 09:05 IST task (different boundary, auction window), not 09:08. Local 09:05 task DISABLED same-session S25 (see new section below). Q2 as filed was based on Topology §7.2 Task Scheduler audit naming similarity, not on observed timestamps. |
| 3 | Is `capture_spot_1m_v2.py` the production-active 1-min spot ingester, replacing the disabled `MERDIAN_Market_Tape_1M`? | LIKELY YES, per audit | One-shot evidence: query `market_spot_snapshots` write rate during a recent trading hour. If ~60 rows/hour on Local timestamps, v2 is doing the work. Update JSON `files` inventory. |
| 4 | What does `merdian_morning_start.ps1` actually invoke? Does it call `start_supervisor_clean.ps1` internally, or is the JSON entry stale? | OPEN | One-time read of the .ps1 file. 5 minutes of work. |
| 5 | Confirm the split between `merdian_watchdog.py --kill` (Python process killer) and `watchdog_check.ps1` (PowerShell health check) | LIKELY INTENTIONAL per audit | Worth filing as ENH/operational note documenting the two-watchdog architecture, so future sessions don't try to consolidate them. |
| 6 | Should AWS gain telemetry mirroring (heartbeat / health snapshots) for full operational parity? | OPEN | ENH candidate. Not blocking. |
| 7 | Static IP SSH whitelisting fragility from multi-WAN | OPEN | Move to AWS Systems Manager Session Manager. ENH candidate. |
| 8 | MERDIAN AWS cron `MERDIAN_Postmarket` not yet proven (A-02 open) — needs one full day's evidence of successful run | **PARTIAL EVIDENCE S25 2026-05-10** | 5-day evidence captured 2026-05-04 → 2026-05-08 confirms `MERDIAN_Postmarket` cron writes `market_spot_snapshots` rows at 16:00 IST on every trading day in window (per Q1 dual-write audit). Operational reliability proven for the post-market boundary. A-02 status to be updated formally when ADR-006 disposition executes. |
| 9 | MERDIAN AWS cron `MERDIAN_EOD` cursor-gate logic not ported from V17D1 (A-04 open) | OPEN | Code port required. |
| 10 | Should `MERDIAN_Market_Tape_1M` task be disabled in Task Scheduler to match the script's DhanError 401 production reality? | OPEN — recommend YES | Single Task Scheduler change. File as TD if not already. |
| 11 | Should TD-061 (pythonw migration) be extended to the 11 cmd-spawning tasks, given the precedent of `HB_Watchdog`/`Live_Dashboard`/`PreOpen`/`Spot_1M` already on pythonw? | OPEN | Operational ENH. Each .bat wrapper would need an equivalent direct pythonw call. Worth a session of consolidation work. |
| **12** | **MALPHA → MERDIAN AWS Zerodha token propagation is manual `sed`. Should it move to Supabase `system_config` (Dhan-pattern)?** | **OPEN S28 — TD-NEW-7 S1 filed** | Two outages (2026-04-22, 2026-05-12) traced to this manual step. Fix: MALPHA writes token to Supabase; MERDIAN AWS `pull_token_from_supabase.py` extended to handle Zerodha key. Closes the failure class. ~60-90 min spans MALPHA + MERDIAN AWS + Supabase. S29+ work. |
| **13** | **Did `merdian_order_placer.py` running on MERDIAN AWS since 2026-04-29 get catalogued in the Topology before S28?** | **CLOSED S28 — filed-as-error, now catalogued** | TD-NEW-10 filed during S28 as "process running un-audited" — investigated and confirmed intentional Phase 4B Order Placer (HTTP server port 8767, Dhan-IP-whitelisted Elastic IP 13.63.27.85, @reboot cron). Closed as filed-in-error. Topology gap → TD-NEW-11 (S3 documentation) filed and closed simultaneously here by adding the row to §3 and the cron entry to §7.1. |
| **14** | **Should `gamma_metrics_shadow` history be backfilled?** | **OPEN S28** | TD-NEW-12 RESOLVED S28 wires AWS to write to `gamma_metrics_shadow` from S29 09:15 IST cron forward. Pre-S29, the table is empty (apart from a handful of S28 smoke-test rows). Optional backfill: re-run patched compute with `--shadow` on the 587 broken-window run_ids (and optionally Apr 29 → May 11 production-deployment-window cycles). Cost ~30-45 min. Operator decision. Forward-only is acceptable for `evaluate_shadow_vs_live.py` purposes. |

These fourteen questions are the proper scope of ADR-006 (reserved — AWS migration scope) when it gets drafted. Items 1–3 and 12–14 in particular are the empirical observations ADR-006 needs as evidence base.

---

### §9.A — S25 boundary disposal — `MERDIAN_PreOpen` (09:05 IST) DISABLED

**Date:** 2026-05-10 (Session 25)

**Context:** §9 Q2 audit revealed Local 09:05 task wrote `market_spot_snapshots` rows during the pre-open auction window (09:00–09:08 IST). AWS sole-writer status at 09:08 IST is empirically confirmed; the Local 09:05 task was a different-boundary write, not a duplicate of AWS 09:08.

**Reasoning chain for disposal:**

1. **Operator semantic:** Quote — "9:05 read meaningless" — auction-window prices are not tradeable price discovery; pre-open call auction does not produce continuous-market prints comparable to 09:08+ snapshots.
2. **Code dependency check:** `ret_session` computation reads from `market_spot_snapshots` for the session anchor. Original anchor was 09:05 row. Migration to 09:08 anchor was validated via ADR-008 replay infrastructure (replay over historical days with 09:08 anchor produced equivalent `ret_session` values within tolerance for downstream momentum/signal cycles).
3. **Disposal action:** `MERDIAN_PreOpen` task State changed `Ready` → `Disabled` via PowerShell `Disable-ScheduledTask` on 2026-05-10. Durable across reboots. No code change to disable script writers (Local `capture_spot_1m.py` retains capability; only the scheduled invocation was removed).
4. **`ret_session` anchor migration:** 09:05 → 09:08, validated via replay; production code path now reads first 09:08 IST tick from AWS-written `market_spot_snapshots` row.

**Mon 2026-05-12 verification plan:**

- Confirm `MERDIAN_PreOpen` does not appear in 09:00–09:10 IST execution log (`script_execution_log` should show no entries from this task).
- Confirm AWS `capture_market_spot_snapshot_local.py` 09:08 IST write succeeds and produces canonical `market_spot_snapshots` row.
- Confirm `ret_session` computation in `build_momentum_features_local.py` cycle ≥1 reads correctly from 09:08 anchor.
- If any of the three fail: re-enable Local `MERDIAN_PreOpen` as fallback while investigating; do not block production.

**Cross-references:**

- §7.2 Task Scheduler entry for `MERDIAN_PreOpen` to be marked `State=Disabled` on next inventory pass.
- Phase α Q2 (capture stage → AWS canonical) endorses this disposal as architecturally aligned.
- Phase α Q3 (token reliability first) does NOT block this specific disposition because the 09:08 AWS writer is `capture_market_spot_snapshot_local.py` (Kite-WebSocket-derived path, not Dhan-token-dependent). The Q3-gated dispositions are those where AWS reliability still depends on Dhan token refresh (e.g. option-chain captures, post-market 16:00 disposal).

---

## §9.B — Boundary disposals and discoveries (Session 26)

> Fourth working block (after §9, §9.A) for the boundary work shipped in Session 26. Single block: TD-080 instrumentation deployed (probe-log table + view + extended `pull_token_from_supabase.py`).

**TD-080 instrumentation (Session 26, commit `718ef39`):**

- New Supabase table `dhan_token_probe_log` created (DDL applied via `001_create_dhan_token_probe_log.sql` migration).

  | Column | Type | Purpose |
  |---|---|---|
  | `id` | bigserial PK | Auto-increment row ID. |
  | `ts_utc` | timestamptz | UTC timestamp of probe execution. |
  | `ts_ist` | timestamp | IST display timestamp (derived). |
  | `host` | text | `'aws'` or `'local'` — execution environment. |
  | `script` | text | Caller script name (e.g. `'pull_token_from_supabase.py'`). |
  | `phase` | text | One of: `'pre_write'`, `'post_write_ltp'`, `'post_write_optionchain'`, `'asymmetry_verdict'`. |
  | `endpoint` | text | Dhan endpoint probed (e.g. `'/v2/marketfeed/ltp'`, `'/v2/optionchain/expirylist'`). |
  | `http_status` | int | HTTP response code from Dhan. |
  | `latency_ms` | int | Round-trip latency. |
  | `token_len` | int | Length of token used (sanity check; expected 280). |
  | `token_prefix` | text | First 12 chars of token (audit, no PII risk). |
  | `verdict` | text | `'OK'` / `'PARTIAL'` / `'FAIL'` per phase logic. |
  | `error_excerpt` | text | First 500 chars of response body if non-200. |
  | `notes` | text | Free-form annotation. |

- New convenience view `v_dhan_token_probe_today` (DDL in same migration): filters today's UTC date, orders DESC by `ts_utc`. Used by Mon 2026-05-12 verification triplet check #1.

- `pull_token_from_supabase.py` extended 50 → 355 lines:
  - **Atomic .env write** with readback verify (read-back-and-compare-prefix sanity check before considering write committed).
  - **Post-write probes** of `/v2/marketfeed/ltp` (lightweight, low-rate-limit) + `/v2/optionchain/expirylist` (option-chain-relevant) immediately after .env write.
  - **Audit logging** to `dhan_token_probe_log` for each probe phase.
  - **Asymmetry verdict** logic: if both endpoints succeed → `OK`; if only one succeeds → `PARTIAL` (logged with which endpoint, prepares for Mon triage); if both fail → `FAIL` (token-side problem, distinct from per-endpoint problem).
  - Backup `pull_token_from_supabase_PRE_S26.py` preserved.

- **Sunday 2026-05-10 smoke test PASS** at 20:28 IST: token len=280, both probes 200 OK, verdict=`OK`. MERDIAN AWS cron `5 3 * * 1-5 /usr/bin/python3 /home/ssm-user/meridian-engine/pull_token_from_supabase.py` continues to fire weekday 03:05 UTC = 08:35 IST as before; no scheduler change.

**Mon 2026-05-12 verification triplet (P0b S27):**

```sql
-- Check #1 (08:36 IST onwards) — token probe-log triage
SELECT * FROM v_dhan_token_probe_today ORDER BY ts_ist DESC LIMIT 10;
-- Decision tree:
--   both 200 → token side healthy; if option-chain still fails 09:15 IST → endpoint-side investigation
--   partial (LTP 200 + option-chain 401) → JWT scope / endpoint-specific auth issue
--   both fail → upstream problem (TOTP / login flow on Local 08:15)
```

```sql
-- Check #2 (09:08 IST) — Topology §9.A 3-check
-- (a) MERDIAN_PreOpen task absent from 09:00-09:10 IST script_execution_log (verifies S25 disable durable)
SELECT script_name, ts, exit_code, contract_met
FROM script_execution_log
WHERE ts >= (CURRENT_DATE + INTERVAL '3 hours 30 minutes')::timestamptz
  AND ts < (CURRENT_DATE + INTERVAL '3 hours 40 minutes')::timestamptz
  AND script_name LIKE '%PreOpen%' OR script_name LIKE '%capture_spot_1m%'
ORDER BY ts;

-- (b) MERDIAN AWS 09:08 IST capture_market_spot_snapshot_local.py write succeeded
SELECT id, ts, symbol, spot, source_table FROM market_spot_snapshots
WHERE ts >= (CURRENT_DATE + INTERVAL '3 hours 38 minutes')::timestamptz
  AND ts < (CURRENT_DATE + INTERVAL '3 hours 40 minutes')::timestamptz
  AND symbol IN ('NIFTY','SENSEX')
ORDER BY ts;

-- (c) ret_session reads from 09:08 anchor — TD-101 fix verification
SELECT cycle_ts, symbol, raw->>'ret_session' AS ret_session_value
FROM signal_snapshots
WHERE ts >= (CURRENT_DATE + INTERVAL '3 hours 45 minutes')::timestamptz
  AND symbol IN ('NIFTY','SENSEX')
ORDER BY ts
LIMIT 10;
-- Expect: ret_session populated (not NULL) starting from second cycle onwards (first cycle may legitimately be neutral if open == 09:08 spot)
```

```sql
-- Check #3 (first cycle onwards) — ENH-88 + ENH-55 absence verification
-- ENH-88 BULL_FVG cluster gate firing
SELECT
    COUNT(*) FILTER (WHERE cautions::text LIKE '%ENH-88%' OR reasons::text LIKE '%ENH-88%') AS enh88_decisions,
    COUNT(*) FILTER (WHERE raw->>'enh88_decision' = 'ALLOW')                                  AS enh88_allow,
    COUNT(*) FILTER (WHERE raw->>'enh88_decision' = 'BLOCK')                                  AS enh88_block,
    COUNT(*) FILTER (WHERE ict_pattern = 'BULL_FVG' AND action = 'BUY_CE')                    AS bull_fvg_signals
FROM signal_snapshots
WHERE ts >= CURRENT_DATE;
-- Expect: enh88_decisions ≥ bull_fvg_signals (every BULL_FVG BUY_CE signal records an enh88_decision)

-- ENH-55 disabled — no opposition blocks, no alignment bonuses
SELECT
    COUNT(*) FILTER (WHERE cautions::text LIKE '%ENH-55: Momentum opposition%') AS opposition_blocks,
    COUNT(*) FILTER (WHERE reasons::text  LIKE '%ENH-55: Momentum aligned%')      AS alignment_bonuses,
    COUNT(*)                                                                       AS total_signals
FROM signal_snapshots
WHERE ts >= CURRENT_DATE;
-- Expect: opposition_blocks=0, alignment_bonuses=0, total_signals > 0

-- TD-101 ret_session writer fix verification (ground truth)
SELECT
    COUNT(*) AS total_momentum_rows,
    COUNT(*) FILTER (WHERE ret_session IS NOT NULL) AS rs_populated,
    100.0 * COUNT(*) FILTER (WHERE ret_session IS NOT NULL) / NULLIF(COUNT(*), 0) AS pct_populated
FROM momentum_snapshots
WHERE ts >= CURRENT_DATE + INTERVAL '4 hours';
-- Expect: pct_populated approaches 100% from second cycle onwards
```

**Cross-references:**

- TD-080 root-cause investigation (P1 S27) — gates ADR-006 drafting per Phase α Q3 sequencing. Probe-log triage on Mon morning is the diagnostic input; ADR-006 evidence base for AWS migration scope decisions.
- §9.A `MERDIAN_PreOpen` disable validation continues — Mon's Check #2 is the first live trading day after disable.
- TD-101 ret_session writer fix is orthogonal to topology but verification is bundled here because Check #2 (c) depends on it.
- ENH-88 + ENH-55 verification queries are not topology-scope but bundled because Mon morning is the verification gate for all S26 changes that depend on live data flowing.

---

## §9.C — Boundary disposals and discoveries (Session 28)

> Fifth working block for the boundary work shipped in Session 28. Three discoveries: (1) shadow architecture was silently violated since deployment, now restored via TD-NEW-12 wiring; (2) MALPHA exists as a third environment not previously catalogued in §1; (3) `merdian_order_placer.py` exists as a fourth MERDIAN-AWS-only service not previously catalogued in §3. Plus the partial S28-shaped closure of §9 Q2/Q8/Q12-Q14 disposition.

**Discovery 1 — shadow architecture (TD-NEW-12 RESOLVED S28):**

The architectural invariant in §6.5 ("AWS shadow output ≠ live output") was honored in narrative but silently violated in code from MERDIAN AWS shadow runner deployment (~2026-04-29) through 2026-05-13. `compute_gamma_metrics_local.py` on MERDIAN AWS wrote to production `gamma_metrics` table because the script hardcoded the target table name and the AWS shadow runner passed no flag to redirect. Result: race-condition double-writes against the same `(symbol, ts)` row that Local was upserting, UPSERT semantics determining which value persisted per cycle. `gamma_metrics_shadow` table existed in Supabase but had **0 rows** for 13 days.

Diagnosis path during S28: investigating TD-080 (Dhan token probe-log triage) revealed that AWS option-chain ingest was succeeding 20/20 cycles per day but `gamma_metrics_shadow` had no rows today. Cross-check on `script_execution_log` showed AWS `compute_gamma_metrics_local.py` invocations had `actual_writes: {"gamma_metrics": 1}` — literally writing to the production table, telemetry-honest. Diagnostic SQL on `gamma_metrics` confirmed 2 writes per `(symbol, minute)` bucket for all of today's cycles before the patch landed.

Resolution shipped:

1. **Compute patch** (commit `72622a9`) — `compute_gamma_metrics_local.py` now respects `--shadow` flag:
   - Module-level `USE_SHADOW = "--shadow" in sys.argv` sniff (strips flag before custom argv parser runs).
   - `TARGET_TABLE = "gamma_metrics_shadow" if USE_SHADOW else "gamma_metrics"` constant.
   - `fetch_prior_gamma_metrics()` SELECT routed via TARGET_TABLE (shadow path reads its own history).
   - `upsert_gamma_metrics()` UPSERT routed via TARGET_TABLE.
   - `ExecutionLog` `expected_writes` dict + `record_write()` instrumentation keyed by TARGET_TABLE (telemetry honest about which table actually received the write).
2. **AWS wrapper patch** (commit `de23467`) — `run_merdian_shadow_runner.py` line 479 appends `"--shadow"` to the subprocess args list.
3. **Schema reconciliation** — `ALTER TABLE gamma_metrics_shadow ADD COLUMN IF NOT EXISTS` for 7 missing columns (dte, gamma_zone, otm_oi_velocity, raw, run_type, spot_vs_range, straddle_velocity). Plus `ADD CONSTRAINT gamma_metrics_shadow_symbol_ts_key UNIQUE (symbol, ts)` to enable the upsert's `on_conflict="symbol,ts"` clause. Schema cache refresh via `NOTIFY pgrst, 'reload schema'`. (Schema drift was orthogonal to the write-target bug; surfaced because the bug masked it for 13 days.)
4. **Smoke tests** — Local Path 1 (no flag) writes to `gamma_metrics`; Path 2 (`--shadow`) writes to `gamma_metrics_shadow`. AWS smoke at 07:07 IST 2026-05-13 confirmed same. Telemetry rows honest with `actual_writes` reflecting actual target table.

Architectural codification: D.11.1 in Assumption Register, §6.5 update + new §6.8 gotcha in this Topology, CLAUDE.md settled-decision footer entry for TD-NEW-12 RESOLVED.

**Discovery 2 — MALPHA as third environment (Topology gap closed in this rewrite):**

MALPHA AWS (Kite gateway, EC2 at `13.51.242.119`, `ubuntu` user, `~/meridian-alpha`) was treated inline as "Kite gateway, not Meridian" in previous Topology revisions. It is a third environment that the Meridian production pipeline depends on for the Zerodha access token. Two outages (2026-04-22 and 2026-05-12) were traced to the manual `sed` step that propagates the token from MALPHA to MERDIAN AWS `.env`. The dependency is unmissable; the catalog gap obscured it.

Resolution: new §1.5 added documenting MALPHA, new column in §1 side-by-side, TD-NEW-7 (S1) filed for the Supabase-based propagation fix (mirroring Dhan flow).

**Discovery 3 — `merdian_order_placer.py` as MERDIAN-AWS-only service (Topology gap closed in this rewrite):**

The Phase 4B Order Placer (HTTP server on port 8767) has been running on MERDIAN AWS via `@reboot` cron since 2026-04-29 (PID 579 confirmed S28). The architectural reason it's on AWS-not-Local is that Dhan Trading API whitelists the AWS Elastic IP `13.63.27.85`; Local's multi-WAN home network has unstable IP. The order placer responds to dashboard PLACE ORDER button clicks via HTTP. Previous Topology revisions did not catalog it (was a TD-NEW-11 documentation gap filed and closed in S28).

Resolution: added to §3 AWS-only scripts, added to §7.1 @reboot cron entries, added to §8.2 runtime artifacts log path.

**§9 Q12-Q14 dispositions:**

- Q12 (MALPHA → MERDIAN AWS Zerodha token propagation): OPEN, TD-NEW-7 (S1) filed.
- Q13 (order placer catalog gap): CLOSED in this rewrite.
- Q14 (`gamma_metrics_shadow` history backfill): OPEN; operator decision; forward-only acceptable.

**Cross-references:**

- TD-NEW-12 RESOLVED Session 28 — commits `72622a9` + `de23467` + schema SQL.
- TD-NEW-4 RESOLVED Session 28 — bundled with TD-NEW-12 (commit `72622a9`) — `dte` computed from `result.ts.date()` not `date.today()`.
- TD-NEW-13 RESOLVED Session 28 — commit `447634c` — Python 3.10 microsecond normalization in `_dte_from_ts` helper.
- TD-NEW-7 S1 OPEN — Zerodha token MALPHA → Supabase → MERDIAN AWS automation.
- TD-NEW-11 (S3 documentation gap, order placer not catalogued) — CLOSED in this rewrite.
- §6.5 (existing gotcha updated S28), §6.8 (new gotcha S28), §6.9 (new gotcha S28).
- Assumption Register §D.11 — codified invariants from S28 production resolutions.
- CLAUDE.md B22 + B23 (S28) — operational rules from this session.

---

## §9.D — Boundary disposals and discoveries (Session 29 firefighting, 2026-05-14)

> Sixth working block. The 2026-05-14 firefighting session did not change environment boundaries (no scripts moved between Local/AWS/MALPHA) but it surfaced two new operational invariants now codified as §6.10 + §6.11, resolved TD-061 + TD-063 + TD-083 in-flight, and confirmed the Task Scheduler inventory had drifted from S23's 17-entry list to 19 entries.

**Discovery 1 — Task Scheduler inventory drift (TD-NEW-E CLOSED in this rewrite):**

The S23 canonical 17-task inventory was 2 entries stale. `migrate_to_pythonw.ps1` dry-run reported 19 `MERDIAN_*` tasks. Two new tasks discovered: `MERDIAN_Dhan_Token_Refresh` and `MERDIAN_Intraday_Session_Start`. Both had their settings hardened (Hidden + IgnoreNew) but actions were left unchanged because the migration script's whitelist did not include them and operator confirmation was needed first.

**Lesson:** Any session that touches Task Scheduler must include `Get-ScheduledTask -TaskName 'MERDIAN_*' | Measure-Object` as the first check and reconcile against the Topology §7.2 table count. Codified as Doc Protocol v4 candidate Rule N (Task Scheduler audit cadence).

**Resolution:** §7.2 rewritten with 19-task table; Notes 4 + 5 added for new tasks + ICT_HTF orchestrator. TD-NEW-E filed and closed in same commit.

**Discovery 2 — `.env` token edits don't restart consumers (codified as §6.10):**

The morning incident (six-hour breadth cascade despite correct `.env` token state) surfaced the operational invariant that token files are read at process startup, not at every use. Long-running consumers (websocket feeders, daemons, cron'd scripts that don't auto-exit) hold whatever value was loaded at startup until killed. The diagnostic ambiguity is severe — `kite.profile()` returns AUTH OK from a script that loads `.env` fresh (correctly reports new token healthy), while the consumer process holds the prior token and continues failing in a silent reconnect loop.

**Resolution:** New §6.10 gotcha added (this rewrite). `runbook_update_kite_flow.md` Step 2d added (separate commit, same S29 close). CLAUDE.md B24 anti-pattern line added (same S29 close).

**Discovery 3 — `pg_cron` failures are silent (codified as §6.11):**

The deeper root cause of the breadth cascade — `delete-old-market-ticks` failing every weekday for 14+ days unnoticed — exposed a structural blind spot: `cron.job_run_details` records every cron run including failures, but no MERDIAN telemetry polls it. The failure mode is invisible until a downstream consumer notices.

**Resolution:** New §6.11 gotcha added (this rewrite). Operator session-start checklist SQL provided. TD-NEW-B (S1) filed for the polling daemon implementation. CLAUDE.md B26 anti-pattern line added.

**TD lifecycle this session:**

| TD | Status entering S29 | Status at S29 close | Notes |
|---|---|---|---|
| **TD-061** | Active body / footer-claimed-RESOLVED-S18 (inconsistent) | **RESOLVED** | 13/19 on pythonw + 18/19 settings tightened. Body block moved to Resolved in `tech_debt.md` with §7.2 final state table as evidence. |
| **TD-063** | Active (footer-RESOLVED-S18 inconsistent) | **RESOLVED** | 18/19 on `MultipleInstances=IgnoreNew`. 1 failure on Intraday_Supervisor_Start documented as known limitation. |
| **TD-080** | Reframed S25; cause unconfirmed | **PROMOTED to S1 RECURRING** | 3rd documented occurrence (S22, S28, S29). Per-token Dhan rate-limit instability hypothesis corroborated. ENH spec for retry layer is P0 carry-forward to S30. |
| **TD-083** | Active | **RESOLVED via TD-NEW-J** | `capture_spot_1m_v2.py` recording `OUTSIDE_MARKET_HOURS` as CRASH (invalid `chk_exit_reason_valid` value). Patched call-site L346 + docstring L36 to `OFF_HOURS`. |
| **OI-12** | Closed 2026-04-14 (proved unstable) | **RE-RESOLVED** | New cron `prune-market-ticks` jobid 46, `*/30 * * * 1-5`, 1-hour horizon. Old jobid 45 retired. See `MERDIAN_OpenItems_Register_v7.md` RE-RESOLVED block. |
| **TD-NEW-A** | — | NEW + **RESOLVED in-flight** | `market_ticks` retention runaway → 62 GB → INSERT timeouts. Same fix as OI-12 re-resolution. |
| **TD-NEW-B** | — | NEW (open) | `pg_cron` failures invisible. S1. Polling daemon implementation queued. |
| **TD-NEW-C** | — | NEW (open) | `ws_feed_zerodha.py` silent on Supabase 500/token errors. Extends TD-NEW-9. |
| **TD-NEW-D** | — | NEW (cosmetic) | `ws_feed_zerodha.py` log prefixes `[HH:MM:SS IST]` are actually UTC. |
| **TD-NEW-E** | — | NEW + **CLOSED in this rewrite** | Topology §7.2 staleness (17→19). |
| **TD-NEW-F** | — | NEW + **RESOLVED via runbook edits** | `runbook_update_kite_flow.md` missing Step 2d. 5 edits applied at S29 close. |
| **TD-NEW-H** | — | NEW (open) | `backfill_volatility_snapshots.py` NULL `expiry_date` schema violation; 7 pre-market CRASHes. |
| **TD-NEW-I** | — | NEW + **RESOLVED** | Daily audit thresholds 370 → 365. |
| **TD-NEW-J** | — | NEW + **RESOLVED** (= TD-083) | `capture_spot_1m_v2.py` exit_reason fix. |

**Cross-references:**

- `CASE-2026-05-14-breadth-cascade-token-and-bloat.md` — full incident chronology + codification of §6.10 + §6.11.
- `CASE-2026-05-14-spot-gap-backfill.md` — separate concurrent incident (Dhan 429 storm + spot-bar gap backfill).
- CLAUDE.md v1.20 — B24/B25/B26/B27/B28 anti-pattern lines + 5 settled-decision footer entries.
- `tech_debt.md` — TD-061, TD-063, TD-083 moved to Resolved; new TDs filed.



**At session start:** Read §1 + §1.5 (the side-by-side summary plus MALPHA) plus the section relevant to the question being asked.

**Before adding a new script:** Decide §2 / §3 / §4 placement explicitly. Don't default to "both" — Local has 17 already-scheduled tasks; MERDIAN AWS has 6 cron entries + 2 @reboot. New scheduling on either side is a topology change and per Doc Protocol v4 Rule 10 may require an ADR.

**Before changing cron / task / scheduler:** Update this document in the same commit as the change. Do not let scheduler reality drift from documentation again — Session 17 reactivation was visible only via Task Scheduler audit, not docs. Session 28 surfaced that the `@reboot` cron entries for `merdian_order_placer.py` and `merdian_signal_dashboard.py` had been live for two weeks without Topology mention; do not repeat.

**Before any MERDIAN AWS operation:** Re-read §6 AWS gotchas. They are short and learned from real failures. §6.8 (shadow schema parity) and §6.9 (Python version parity) added S28. **§6.10 (token edits don't restart consumers) and §6.11 (pg_cron failures silent) added S29.**

**Before any MALPHA operation:** §1.5. MALPHA is not Meridian code; do not edit there. Coordinate token refresh boundary changes with TD-NEW-7 design.

---

## Update log

| Date | Session | Event |
|---|---|---|
| 2026-05-09 | Session 23 (initial) | Created. Sourced from V18 §15.4/15.5, V18A §13.5, V18E §7.4/7.5, CLAUDE.md gotchas, `merdian_reference.json` `environments` + `aws_cron` + `aws_runtime_files` + (partial) `task_scheduler`. **Task Scheduler audit by Navin (PowerShell `Get-ScheduledTask`)** revealed 17 `MERDIAN_*` tasks vs JSON's 4 — full inventory captured in §7.2. Three boundary discrepancies surfaced (post-market dual-environment, pre-open dual-environment, Market_Tape_1M Ready vs DhanError 401). Eight open boundary questions filed in §9. |
| 2026-05-09 | Session 23 (action map pass) | **Canonical action map populated** for all 17 Task Scheduler entries via second PowerShell pass. Surfaced ~15 newly-catalogued scripts (added to §A.2). Three architectural insights: (a) TD-061 pythonw migration is partially complete (4 tasks already pythonw), (b) two-watchdog architecture (`merdian_watchdog.py --kill` + `watchdog_check.ps1`) is intentional, (c) `merdian_morning_start.ps1` (not `start_supervisor_clean.ps1`) is the supervisor entry point. PreOpen and Post-market "duplicates" reframed as different-scripts-same-table writes. §9 expanded from 8 to 11 open questions. |
| 2026-05-10 | Session 25 | **§9 Q1 CLOSED** (post-market 16:00 dual-write empirically confirmed via 5-day audit 2026-05-04 → 2026-05-08; disposition queued for ADR-006 execution gated on TD-080). **§9 Q2 CLOSED and reframed** — original framing inaccurate; no actual dual-write at 09:08 IST; Local 09:05 task was a different (pre-open auction) boundary, not 09:08. **§9 Q8 PARTIAL EVIDENCE** — Postmarket cron 5-day reliability captured. **New §9.A section** documents Local `MERDIAN_PreOpen` (09:05 IST) DISABLED via PowerShell `Disable-ScheduledTask`, durable; `ret_session` anchor migrated 09:05 → 09:08 and validated via ADR-008 replay; Mon 2026-05-12 verification plan filed. **Phase α Q2 (capture/derived split, four-stage decomposition)** answered S25; ADR-006 drafting gated on TD-080 closure per Phase α Q3 sequencing. |
| 2026-05-10 | Session 26 | **New §9.B section** documents TD-080 instrumentation deployment (commit `718ef39`): new Supabase table `dhan_token_probe_log` (12 columns) + view `v_dhan_token_probe_today`; `pull_token_from_supabase.py` extended 50 → 355 lines with atomic .env write + readback verify + post-write Dhan endpoint probes (`/v2/marketfeed/ltp` + `/v2/optionchain/expirylist`) + audit logging + asymmetry verdict logic; backup `_PRE_S26.py` preserved. Sunday 2026-05-10 smoke test PASS (token len=280, both probes 200 OK, verdict=OK). Mon 2026-05-12 verification triplet filed (3 SQL check blocks: 08:36 IST probe-log triage, 09:08 IST §9.A 3-check + TD-101 ret_session verification, first-cycle ENH-88 + ENH-55 absence verification + TD-101 writer-cadence verification). TD-080 root-cause investigation (P1 S27) gates ADR-006 drafting. **Note:** S26 also shipped 4 production code patches but only TD-080 is topology-scope (Local↔AWS boundary or new infrastructure); TD-079 zone validity, ENH-88 deploy, TD-101 writer fix, ENH-55 disable are recorded in `MERDIAN_Enhancement_Register.md`, `tech_debt.md`, `MERDIAN_System_Map.md` not here. |
| 2026-05-13 | Session 28 | **Major Topology rewrite.** **§1 expanded** — three-environment side-by-side replaces two-environment (Local + MERDIAN AWS + MALPHA). **New §1.5 — MALPHA: third environment, Zerodha token gateway.** Explains why MALPHA exists separately, current manual `sed` propagation step (TD-NEW-7 S1), and Meridian dependency map. **§3 catalog gap closed** — added `merdian_order_placer.py` (Phase 4B Order Placer HTTP server on port 8767, Dhan-IP-whitelisted Elastic IP, @reboot cron, deployed 2026-04-29). **§4 updated** — `compute_gamma_metrics_local.py` row distinguishes Local target (`gamma_metrics`) from AWS target (`gamma_metrics_shadow` via `--shadow` flag, S28 TD-NEW-12). **§5.2 updated** — Zerodha token flow now shows MALPHA → manual sed → MERDIAN AWS dependency. **§6.5 updated** — shadow output gotcha now architecturally enforced not just narratively (TD-NEW-12). **Two new gotchas §6.8 (shadow schema parity) + §6.9 (Python 3.10 vs 3.12 fromisoformat).** **§7.1 expanded** — 5 entries → 6 entries (added `MERDIAN_WS_Stop` SIGKILL upgrade per TD-NEW-8) + 2 @reboot entries (signal dashboard + order placer). **§7.2 task updates** — `MERDIAN_PreOpen` State=Disabled per S25; `MERDIAN_WS_Feed_0900` State=Disabled per TD-NEW-6; `MERDIAN_ICT_HTF_Zones_0845` note about Pine overlay chaining per TD-NEW-5. **§8.2 expanded** — added MERDIAN AWS log paths (`order_placer.log`, `ws_feed.log`, `signal_dashboard.log`, `backfill_logs/`). **New §8.3 — MALPHA runtime artifacts.** **§9 questions Q12-Q14 added** covering MALPHA Zerodha propagation (TD-NEW-7 OPEN S1), order placer catalog (CLOSED), `gamma_metrics_shadow` history backfill (OPEN operator decision). **New §9.C section** — three S28 discoveries documented: shadow architecture restoration (TD-NEW-12), MALPHA third-environment (catalog gap), order placer fourth-AWS-service (catalog gap). Plus dispositions of Q12-Q14. **§10 updated** to point to §1.5 + the two new gotchas at session start reading list. Cross-refs to Assumption Register §D.11, CLAUDE.md B22 + B23, MERDIAN_Enhancement_Register.md (no ENH changes from S28; ENH-84 + ENH-85 formal filing is in the Enhancement Register itself), `tech_debt.md` (TD-NEW-4/5/6/7/8/9/10/11/12/13 lifecycle blocks). |
| 2026-05-14 | Session 29 (firefighting) | **Operational Topology updates from unplanned firefighting session.** **§1 task count updated** 17 → 19. **Two new §6 gotchas added** — §6.10 (`.env` edits don't restart consumer processes, TD-NEW-A) + §6.11 (`pg_cron` failures invisible by default, TD-NEW-B). **§7.2 fully rewritten** — 17-task table → 19-task table reflecting S29 final state (13/19 pythonw migrations, 18/19 Hidden+IgnoreNew settings). Two new tasks documented (`MERDIAN_Dhan_Token_Refresh`, `MERDIAN_Intraday_Session_Start`) with action-untouched/settings-hardened state; pending operator verification of purpose. New Note 4 (NEW S29 tasks pending verification) + Note 5 (ICT_HTF Python orchestrator). Architectural insights section revised — TD-061 RESOLVED (was: partial since S17/S18). **New §9.D section** — S29 firefighting discoveries: Task Scheduler inventory drift (TD-NEW-E CLOSED), `.env` consumer-restart invariant (§6.10), `pg_cron` silent-failures invariant (§6.11). Full TD-lifecycle table for the session (TD-061/063/083 RESOLVED; TD-080 PROMOTED to S1 RECURRING; TD-NEW-A through J lifecycle). **§10 updated** to point to §6.10 + §6.11. Cross-refs to `CASE-2026-05-14-breadth-cascade-token-and-bloat.md`, `CASE-2026-05-14-spot-gap-backfill.md`, `MERDIAN_OpenItems_Register_v7.md` (OI-12 RE-RESOLVED block), CLAUDE.md v1.20 (B24-B28 + footer entries), `runbook_update_kite_flow.md` (5 edits applied + change-history row). **Zero new code shipped this session** — firefighting only; code patches deferred to single S29 close commit. |
| 2026-05-24 | Session 35 | **Breeze cataloguing + MERDIAN AWS instance-ID drift surfacing.** **§1 Instance row updated** — annotation added that pre-S35 documented instance `i-0e60e4ed9ce20cefb` no longer matches current AWS console (current shows `i-0878c118835386ec2`); Elastic IP `13.63.27.85` unchanged; instance was rebuilt at unknown earlier session; reconcile at S36 P0_TERTIARY. **New §1.6 — Breeze (ICICI Direct) — historical options backfill source.** Catalogues Breeze as an external API consumed only from MERDIAN AWS due to SEBI static-IP whitelist on Elastic IP `13.63.27.85` (same whitelist that serves `merdian_order_placer.py` Dhan endpoint per §3); explains S35 demonstrated capability via `fill_2026_04_16_breeze_v3.py` writing 107,630 HOCS rows in 4-5min wallclock; SENSEX symbology `stock_code='BSESEN'` codified (not `'SENSEX'`, empirically discovered via 6-variant probe per TD-S35-NEW-3); rate limit (5000/day + 100/min throttle) sufficient for single-day fills, marginal for full-year (cadence planning per ENH-109); two Breeze functions documented (`rollingoption` for ATM-anchored research, `get_historical_data_v2` for full-chain Phase 3 GEX prerequisite). PROPOSED graduation to canonical historical backfill source pending ADR-013 decision; not on S36 critical path. Cross-refs to ADR-013 PROPOSED + ENH-109 PROPOSED + TD-S35-NEW-3 + HOCS table + ENH-106 v8 `option_pnl_source` audit column. **Zero new gotchas added this session** (Breeze consumption from MERDIAN AWS straightforward; SSM file transfer via nano multi-line paste codified as operational finding in CLAUDE.md v1.25 not as a §6 gotcha since not a "DO NOT" rule). **Zero scheduler changes this session** — Breeze consumption was one-shot manual invocation; if ENH-109 ships, a new MERDIAN AWS cron entry or systemd unit would be added at that time and Topology updated in the same commit per Update rule. **Zero MALPHA changes this session.** Cross-refs to ADR-013 PROPOSED, ENH-109 PROPOSED, `MERDIAN_System_Map.md` (HOCS table + `ingest_option_chain_local.py` writer + `get_hocs_distinct_expiries(text)` RPC + `idx_hocs_symbol_expiry` covering index all catalogued S35), CLAUDE.md v1.25 (Breeze operational findings), `tech_debt.md` (TD-S35-NEW-1/2/3/4 NEW filings + TD-S34-NEW-4 CLOSED-MECHANICAL resolution row). |
| 2026-05-25 | Session 36 | **TD-S30-CANDIDATE-1 closed-misdiagnosis + ENH-99 SHIPPED capture-layer resilience + Task Scheduler 19 → 20.** **§1 task count updated** 19 → 20 (`MERDIAN_Orphan_Janitor` added). **§7.2 heading updated** to 20-entry inventory; new row inserted alphabetically between `MERDIAN_Market_Tape_1M` and `MERDIAN_PO3_SessionBias_1005`. New task `MERDIAN_Orphan_Janitor` weekly Mon-Fri 09:14 IST, direct `pythonw.exe`, Hidden+IgnoreNew, 5min execution limit; ENH-99 Component 2 deliverable reaping orphan RUNNING rows in `script_execution_log` (int4 duration clamp at `2^31-1` per D.18.4). **S36 counts addendum added** to §7.2 (14/20 pythonw, 19/20 hardened). **Zero §1.x environment changes this session** — no instance ID reconcile yet (S35 P0_TERTIARY carry-forward to S37+; AWS console drift `i-0e60e4ed9ce20cefb` → `i-0878c118835386ec2` unchanged from S35 surfacing). **Zero MALPHA changes this session.** **Zero §6 gotchas added this session** (PostgREST `Prefer: return=representation` interaction with RLS codified in Assumption Register §D.18.3 not as a §6 "DO NOT" gotcha since the operational pattern is per-write-path not per-environment; int4 `duration_ms` clamp codified as D.18.4 not §6 for same reason — environment-agnostic engineering rules belong in Assumption Register, environment-specific DO-NOT rules belong here). **Zero §7.1 cron changes this session** — no AWS scheduler changes. Cross-refs to ENH-99 SHIPPED block in Enhancement Register, TD-S30-CANDIDATE-1 CLOSED-MISDIAGNOSIS in `tech_debt.md`, TD-080 CLOSED-via-ENH-99 in `tech_debt.md`, §D.18 in Assumption Register (4 rows), `MERDIAN_System_Map.md` §A.S36 + §B.S36 sections, CLAUDE.md v1.26. |
| 2026-05-29 | Session 40 | **Marketview frontend graduates to a topology-relevant AWS resource.** **§8.2 expanded** — new sub-block "Marketview frontend (NEW S40)" catalogs `/home/ssm-user/meridian-connect/` (git clone of `balannavin-cyber1/meridian-connect`, Lovable-authored Vite + React SPA, public repo), `/home/ssm-user/meridian-connect/dist/` (Vite build output, S40 bundle `index-vDqPX1iO.js` ~537 KB), and `/var/www/marketview/` (nginx-served document root rendered at `http://13.63.27.85/marketview`). Canonical 3-line deploy command codified (`cd ~/meridian-connect && git pull && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/ && sudo systemctl reload nginx`). Use `npm install` not `npm ci` (Lovable doesn't emit `package-lock.json`). The Marketview frontend reads Supabase directly via a `service_role` key sourced from `/home/ssm-user/meridian-engine/.env` (shared with the Python writer env) embedded in the built JS bundle — exposure is governed by carry-forward TD-S39-NEW-3 (`.env` removal from public repo still pending at S40 close; S40 curl verified key still present). **Zero §1 environment changes this session** — instance ID still `i-0878c118835386ec2`, Elastic IP unchanged. **Zero §3 catalog changes this session** — Marketview lives in §8.2 (runtime artifact) not §3 (script) because it is a static SPA, not a scheduled Python runner; §3's existing pattern restricted to scheduled compute paths. **Zero §6 gotchas added this session** — the `npm install` vs `npm ci` distinction is captured inline in §8.2 not as a DO-NOT rule because it is informational, not a footgun. **Zero §7 scheduler changes this session** — the Marketview deploy is on-demand (git pull when Lovable iterates), not scheduled. **Zero MALPHA changes this session.** Cross-refs to D.22 in Assumption Register (D.22.1 Lovable temporal-immutable column DEFAULT audit, D.22.2 atomic-card layout VALIDATED, D.22.3 stacked-by-strike charts VALIDATED), TD-S40-NEW-1/2/3 in `tech_debt.md`, TD-S37-01 CLOSED via patch_s40_enh83_view_tau_rewrite.py in `tech_debt.md`, `MERDIAN_System_Map.md` S40 update log (`v_max_pain_by_strike` view + `merdian_parameters.valid_to DROP DEFAULT` schema change), CLAUDE.md v1.30 (S40 settled-decisions footer). |

---

| 2026-06-12 / 2026-06-16 | Session 53–54 | **Crontab recovery + ingest cadence change.** S53 root-caused a TOTAL capture/compute blackout to a dropped `SHELL=/bin/bash` directive: a crontab reinstall at 00:47 UTC 2026-06-12 left cron defaulting to /bin/sh (dash), and `source` is a bash builtin dash lacks, so every `cd … && source .env && python3 …` chain died with `/bin/sh: source: not found` into discarded cron mail — silently, since ~2026-06-11 05:03 UTC; capture + all four S52 monitors share that chain and died together. **Fix:** `SHELL=/bin/bash` re-added as crontab line 1 (canonical: always verify it as line 1 on AWS). Four run_ingest.sh lines reconstructed to the working UNQUOTED form `cd /home/ssm-user/meridian-engine && bash run_ingest.sh NIFTY/SENSEX FULL >> cron.log 2>&1` (run_ingest.sh self-sources .env; the S49 single-quoted 'NIFTY FULL' form is NOT live — the unquoted form is). Two `capture_index_futures_snapshot_local.py` cron lines COMMENTED (hard SyntaxError lines 246/253: Windows-path backslash inside an f-string expr; never ran on AWS) — futures DARK, tracked TD-S53-NEW-6. Volatility writer `compute_volatility_metrics_local.py` insert→upsert(on_conflict=symbol,ts), commit cd98a87 (EC2 `git checkout origin/main -- <file>`, not full pull — dirty CRLF tree). **S54:** the two 04–09 UTC ingest lines' minute field changed `30,35,40,45,50,55` → `*/5` (NEW-4 — closes the :00–:29 hourly hole; **doubles Dhan option-chain calls 6→12/hr in 04–09 — watch cron.log for 429/401**). Monday calendar gate note: capture_market_spot_snapshot_local.py:263 requires both `is_open=true` AND `open_time IS NOT NULL` (a calendar row with NULL open_time passes preflight but the capture gate rejects it — TD-S54-NEW-4). Zero §1 environment changes (instance i-0878c118835386ec2, EIP 13.63.27.85 unchanged). Cross-refs: tech_debt.md TD-S53-NEW-1..6 + TD-S54-NEW-1..4; merdian_reference.json v34; MERDIAN_System_Map.md S53–54 update-log row. |
| 2026-06-16 / 2026-06-17 | Session 55 | **Carry-forward execution sweep — orchestrator + compute fixes, calendar seeder cron, token cron cleanup; futures still dark.** **§7.1 cron changes (AWS):** added `30 02 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 seed_trading_calendar.py` (NEW daily calendar seeder, fires before the 03:45 UTC open — retires the daily manual trading_calendar insert, TD-S54-NEW-4). Removed the redundant `source .env` from the Dhan token-refresh line `5 3 * * 1-5 ... refresh_dhan_token.py` (script self-loads via load_dotenv; drops the dash-killable blackout pattern from a token-critical job; the cron target refresh_dhan_token.py is CORRECT — it is the .env writer all consumers read, vs refresh_dhan_token_aws.py which writes only Supabase). Two `capture_index_futures_snapshot_local.py` lines REMAIN COMMENTED — futures parse-fixed (commit 66f8252) but contract resolution fails on a STALE dhan_scripmaster (no June index futures); reload_dhan_scripmaster_from_csv.py needs an AWS port (Windows CSV path `C:\gammaenginepython\api-scrip-master-detailed.csv`, interactive prompt, non-atomic delete-then-reload) before the futures cron can be uncommented. **Production code (via git, EC2 git pull):** run_merdian_shadow_runner_aws.py per-symbol run_id resolution (1889604); compute_volatility_metrics_local.py read-path repointed to volatility_snapshots (e6fba1b); capture_postmarket_1600.py non-blank exit reason (5b92433); capture_index_futures_snapshot_local.py Windows-path fix (66f8252); seed_trading_calendar.py NEW (eb052d0); stage2_db_contract.py V18A-03 open_time gate (c2910e8). **Schema:** `ALTER TABLE script_execution_log ALTER COLUMN duration_ms TYPE bigint` (int4→int8, TD-S36-NEW-4 closed — supersedes the System Map int4-clamp note). **MALPHA finding (no change made):** breadth chain dark since 06-11 — ws_feed_zerodha.py ABSENT from MALPHA filesystem; market_ticks empty; ingest_breadth_from_ticks.py SKIPPED_NO_INPUT every cycle. Feed restore under systemd is S56 work (TD-S48-NEW-1 re-diagnosed). Zero §1 environment changes (instance i-0878c118835386ec2, EIP 13.63.27.85 unchanged). Cross-refs: tech_debt.md (TD-S54-NEW-1/3/4, TD-S55-NEW-1, TD-S53-NEW-6, TD-S48-NEW-1, TD-S36-NEW-4, TD-S41-NEW-2); merdian_reference.json v35; MERDIAN_System_Map.md S55 update-log row. |

| 2026-06-18 | Session 56 (reconstructed at S57) | **Futures resolver fix + scripmaster reloader ported to AWS + futures cron re-enabled.** `capture_index_futures_snapshot_local.py` resolver corrected from a `DISPLAY_NAME ilike.*NIFTY*` substring match (which resolved NIFTY → NIFTYNXT50) to exact `UNDERLYING_SYMBOL = eq.{symbol}` + `INSTRUMENT = eq.FUTIDX` (commit `8eae351`); 3 garbage `index_futures_snapshots` rows deleted (NIFTYNXT50/BANKNIFTY/SENSEX50, 2026-03-27 era). NEW `reload_dhan_scripmaster.py` (commit `132eddc`) ports the scripmaster reload to AWS with a staging table `dhan_scripmaster_staging` + transactional swap RPC `swap_dhan_scripmaster()` (TRUNCATE-in-plpgsql) — 234,882 rows, FUTIDX resolves through Aug 2026 — replacing the non-atomic Local Windows-CSV loader. **§7.1 cron:** the two `capture_index_futures_snapshot_local.py` lines UNCOMMENTED — futures cron `*/5 04-09 UTC` re-enabled both symbols (the S53→S55 dark state is over). `run_ingest.sh` (`c893af9`) git-tracked, firing both symbols. **Breadth-feed supervision built (surfaced post-S57 from the git log, not in this row's original reconstruction):** S56 also authored + git-tracked the breadth-feed supervision scaffolding for rebuild-safety — wsfeed **preflight** (commit `afe8112`: tolerate `.env` special chars, drop `set -u` around `source`) + wsfeed **alert** script + **5 `systemd` units under `deploy/systemd/`** (commits `30cca59` + `b627914`). These were BUILT + committed but **NOT enabled on MALPHA** — which is why S57 still found the feed running unsupervised in an AWS `screen`. The cutover/enable onto MALPHA is ADR-018 D1 remaining work (TD-S57-NEW-1), not a build. Zero §1 environment changes (instance i-0878c118835386ec2, EIP 13.63.27.85). Cross-refs: ADR-018 (D1); tech_debt.md (TD-S53-NEW-6 tail, TD-S57-NEW-1); merdian_reference.json v36 S56 change_log. |
| 2026-06-19 | Session 57 | **Breadth feed re-homed under supervision (ADR-018) + SMDM retired + ENH-SDM placed on AWS.** Root cause of the 23-day breadth outage: `ws_feed_zerodha.py` was running on **AWS** (not MALPHA as the topology documented) since 06-11 in a detached `screen`, holding an expired Zerodha token, 403-looping, writing zero-coverage rows — wrong host + no process supervision + no reader staleness detection. Remediated live (token refresh on MALPHA → `kite.profile()`=`OK: Navin Balan OV0782` → stale AWS PID 259620 `kill -9` → clean restart, 2213 instruments, Feed live, no 403s). **ADR-018 ACCEPTED** sets the durable topology: (D1) `ws_feed_zerodha.py` runs under a **`systemd` unit on MALPHA** (Restart=on-failure + single-instance enforcement + journald) — one host owns the Zerodha session end-to-end; unsupervised `screen`/`nohup` deployment of a long-running broker feed is prohibited going forward; WCB cron arg fixed same pass. (D2) every breadth/divergence reader applies a recency-floor guard on `fetch_latest_row`. (D3) SMDM retired (evidence-based vs ENH-30); (D4) ENH-SDM `compute_structural_divergence_local.py` → `structural_divergence_snapshots` placed **AWS orchestrator-integrated per ADR-006** (kept subsystem, not a Local orphan). Signal-subsystem orphans (options_flow / iv_context / shadow-v3, dropped by the S49 Local-disable) remain open dispositions. systemd unit build itself carries to S58 (TD-S57-NEW-1/2). Zero §1 environment changes (instance i-0878c118835386ec2, EIP 13.63.27.85). Cross-refs: ADR-018; tech_debt.md TD-S48-NEW-1 (CLOSED-DECISION) + TD-S57-NEW-1/2; merdian_reference.json v36; MERDIAN_System_Map.md S57 update-log. Anchor for ADR-018 (breadth-feed supervision). |

*MERDIAN Deployment Topology — established Session 23, 2026-05-09. Last updated Session 63, 2026-07-02 (§S63 — ENH-115 FII/DII participant-positioning EOD writer scheduled on MERDIAN AWS: two Mon–Fri crontab lines 14:00 + 15:30 UTC; new tables `participant_oi_daily` + `fii_dii_cash_daily` + view `v_participant_oi_latest`; participant OI NSE-only, cash consolidated NSE+BSE+MSEI). Previous Session 57, 2026-06-19 (ADR-018 breadth-feed supervision model: ws_feed_zerodha.py re-homed to MALPHA under systemd — found running unsupervised on AWS with an expired token, 403-looping for 23 days; SMDM retired; ENH-SDM structural-divergence monitor placed AWS orchestrator-integrated per ADR-006); previous Session 56, 2026-06-18 (futures resolver exact-match fix + scripmaster reloader ported to AWS with staging+swap RPC + futures cron */5 04-09 UTC re-enabled); previous Session 55, 2026-06-17 (calendar seeder cron added 02:30 UTC + token cron `source .env` removed + futures parse-fixed but cron still commented pending scripmaster reload + duration_ms→bigint); previous Session 54, 2026-06-16 (S53–S54 crontab recovery: SHELL=/bin/bash restored as line 1 + 4 ingest lines reconstructed + 2 futures lines commented + ingest 04–09 UTC `*/5`); previous Session 40, 2026-05-29 (Marketview frontend graduates to topology-relevant AWS resource — §8.2 expanded with `/home/ssm-user/meridian-connect/`, `/home/ssm-user/meridian-connect/dist/`, `/var/www/marketview/` cataloging + 3-line canonical deploy command codified). Updated inline per Doc Protocol v4 Rule 1 + Rule 9.2. Anchor for ADR-006 (AWS migration scope) when drafted. Also anchor for ADR-013 (Breeze canonical historical backfill source) when drafted.*

## §S58 (2026-06-22) — ws_feed supervision host CORRECTION + verified live

**CORRECTION to the AWS↔MALPHA boundary:** the Zerodha `ws_feed_zerodha.py` is supervised on **MERDIAN AWS** (`i-0878c118835386ec2`, `ssm-user@`, `/home/ssm-user/meridian-engine`) under `systemd`, NOT MALPHA. Prior topology rows implying the feed runs on MALPHA / Local-only are superseded by the S56 unit files (`User=ssm-user`, `WorkingDirectory=/home/ssm-user/meridian-engine`, `ExecStart=.../ws_feed_zerodha.py`, `EnvironmentFile=.../.env`). MALPHA's role is unchanged: **Zerodha token gateway only** — it refreshes the token and propagates it to the AWS `.env` (TD-NEW-7); it hosts no Meridian pipeline code.

**systemd units (on MERDIAN AWS):** `merdian-wsfeed.service` (ExecStartPre `bin/wsfeed_preflight.sh` validates `kite.profile()`; `OnFailure` Telegram alert; `Restart=always`; StartLimitBurst=3), `merdian-wsfeed-alert.service`, `merdian-wsfeed-stop.service`, `merdian-wsfeed-start.timer` (Mon-Fri 03:40 UTC), `merdian-wsfeed-stop.timer` (Mon-Fri 10:05 UTC). Installed to `/etc/systemd/system/`, both timers `enable --now`. **Verified live 2026-06-22:** start.timer fired 03:40:01 UTC, preflight OK OV0782, single PID 452985, 2213 instruments, zero 403s.

**Recency-floor guard** (`build_market_state_snapshot_local.py`, both Local + AWS) verified live: zero STALE on the open, breadth ts seconds-old.

---

## §S59 (2026-06-24) — AWS crontab: `refresh_equity_intraday_last.py` re-added (was missing)

**AWS↔Local boundary change — missing cron restored on MERDIAN AWS.** The breadth prev-close reference table `equity_intraday_last` is refreshed pre-open by `refresh_equity_intraday_last.py` (Kite `ohlc()`, writes `last_price` + `ts`). That cron line was **never carried onto the AWS-only host** — `crontab -l | grep refresh_equity_intraday_last` returned empty — so the baseline froze 2026-05-20→2026-06-24 and breadth read BULLISH on down days (TD-S59-NEW-1, a verbatim re-run of C-09 / ADR-001). Re-added this session:

```
35 3 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 refresh_equity_intraday_last.py >> logs/refresh_equity_intraday_last.log 2>&1
```

UTC slot `35 3` = **09:05 IST**, deliberately AFTER the 03:00 UTC MALPHA→AWS token sync (a 05:10 IST manual attempt 401'd on an off-hours expired token; the 03:35 UTC slot lands after the sync). **Verified self-firing:** the cron fired autonomously at 03:35 UTC on the 06-24 open (maiden timed run) and wrote 1,316 rows — confirmed via `eod_health_check --date 2026-06-24` REFERENCE FRESHNESS = OK. Durability now double-guarded: the cron writes the baseline, and `eod_health_check`'s new REFERENCE FRESHNESS section (§S59 System Map) FAILs if it ever goes stale again.

**Host clarification (no change, recorded for topology completeness):** `build_ict_htf_zones.py` + `generate_pine_overlay.py` run on **LOCAL** (Windows Task Scheduler), not the AWS orchestrator. The S59 ICT daily-PDL fix (commit `2b40a4b`) is therefore a Local-only deploy (Local → git → no EC2 pull required for that file). Zero §1 environment changes (instance `i-0878c118835386ec2`, EIP `13.63.27.85`). Cross-refs: tech_debt TD-S59-NEW-1/2/3; merdian_reference.json v38 S59 change_log; MERDIAN_System_Map.md §S59.

---

## §S60 (2026-06-26, Muharram holiday) — marker-writer cron added + orchestrator holiday gate + shared core gate helper

**1. `market_spot_session_markers` writer cron ADDED (AWS).** `build_market_spot_session_markers.py` had stalled after 2026-06-04 (unscheduled post-AWS-migration), freezing the frontend's `prev_close_spot` baseline 21 days and showing a phantom SENSEX +4.34% header (TD-S60-NEW-1). Cron added on MERDIAN AWS:

```
40 10 * * 1-5 cd /home/ssm-user/meridian-engine && /usr/bin/python3 build_market_spot_session_markers.py >> logs/market_spot_session_markers.log 2>&1
```

UTC slot `40 10` = **16:10 IST** (post-close, house-style no-flock). Backfilled markers 06-05→06-25. Durability guarded by a new freshness check in `scripts/eod_health_check.py` (commit `5066d81`). Same C-09/ADR-001 family as the S59 breadth baseline freeze — a stalled writer + a stale reference.

**2. Orchestrator holiday gate ADDED, then cut over to a shared `core/` helper.** `run_merdian_shadow_runner_aws.py` had **no holiday gate** and ran the full 5-min compute chain on Muharram (`PIPELINE COMPLETE` 03:51 UTC on a closed market). Root cause was upstream in `trading_calendar.json` (2-of-15 NSE-2026 holidays, one misdated — TD-S60-NEW-2); fixed at source (commit `bafddc2`, 15 official holidays, reseed + stale-row UPDATE; 06-26 closed / 06-29 open verified). Gate belt added (`af74d0c`), proven firing live on Muharram, then **cut over** (`38a82ff`) to the new shared helper.

**3. NEW shared gate helper `core/trading_calendar_gate.py` (TD-S60-NEW-3).** Single source of holiday-gating, replacing ~30 bespoke inline `is_open` checks incrementally. **Self-sufficient by design:** own `load_dotenv()` + raw `requests` + `os.getenv`, deliberately bypassing `core.config.get_settings()`/`SupabaseClient` — because `core/config.py` hardcodes a Windows `BASE_DIR` and finds no `.env` on AWS (TD-S60-NEW-5), so a SupabaseClient-routed gate would silently fail-open every day (a no-op gate; caught by smoke-test). Fail-open at every branch. Exposes `is_trading_day_today()` / `is_trading_day(iso)` / `assert_trading_day_or_exit(log=None)` (ExecutionLog → HOLIDAY_GATE). Smoke-tested F/T/F on AWS (06-26 closed, 06-29 open, 06-26 closed). Orchestrator cut over; marker writer left on its own working inline gate; ~28 other entrypoints migrate incrementally.

**Holiday-noise repair (TD-S60-NEW-4):** the pre-gate + SDM-test compute rows on 2026-06-26 were DELETE'd (scoped single date; gamma 30 / market_state 30 / volatility 30 / momentum 29 / signal 34 / structural_divergence 16; 0 remaining). `market_spot_snapshots` (0, holiday feed correctly didn't capture) + `market_spot_session_markers` (2) preserved.

Zero §1 environment changes (instance `i-0878c118835386ec2`, EIP `13.63.27.85`). Cross-refs: tech_debt TD-S60-NEW-1..5; merdian_reference.json v39 S60 change_log; MERDIAN_System_Map.md §S60; CLAUDE.md Rule 18.

## §S61 (2026-06-27, Saturday market closed) — ENH-02 options-flow re-homed to AWS orchestrator + ENH-07 B basis-velocity writer wired

**Orchestrator pipeline additions (MERDIAN AWS).** Two writers added to `run_merdian_shadow_runner_aws.py execute_pipeline` via the canonical Local→git→AWS `git pull` vector (no AWS-CLI/SCP):
- `compute_options_flow_local.py` re-homed at the options_flow slot (was orphaned at the S49 migration) — ENH-02 substrate now advancing each cycle (TD-S61-NEW-1). Commits `8ddbc78` + `d16986c`.
- `compute_basis_context_local.py` (ENH-07 B) tupled at L244-245 (after market_state, before trade_signal) — reads `index_futures_snapshots`, writes `basis_context_snapshots`. Commit `141386d`.

Both readers in `build_trade_signal_local.py` carry the ADR-018 D2 recency floor (`MERDIAN_FLOW_RECENCY_FLOOR_MIN`, `MERDIAN_BASIS_RECENCY_FLOOR_MIN`, both 15-min default). Basis context is display-only into `signal_snapshots.raw` (context-not-gate).

**New SQL migrations (Supabase SQL editor).** `2026-06-26_enh07b_basis_context_snapshots.sql` (live table) + `2026-06-26_enh07b_hist_basis_context.sql` (historical cohort).

**Historical backfill (one-shot).** `backfill_basis_context.py` wrote `hist_basis_context` (NIFTY 92,515 / SENSEX 29,689) from `hist_future_bars_1m`×`hist_spot_bars_1m` (zero-shift pairing — TD-S61-NEW-2). Committed `3f1fe4e`.

Zero §1 environment changes (instance `i-0878c118835386ec2`, EIP `13.63.27.85`). No cron/systemd changes this session (both writers run inside the existing 5-min orchestrator cycle). Cross-refs: tech_debt TD-S59-NEW-2 + TD-S61-NEW-1/2/3; merdian_reference.json v40 S61 change_log; MERDIAN_System_Map.md §S61.

## §S62 (2026-07-01) — historical per-strike Greeks + `gamma_concentration` backfill run to completion (both symbols); ENH-116 spec; flip-bug diagnosis

**No production-runtime topology change.** S62 was a historical/research backfill run, an ENH spec, and a parity diagnosis — no live writer, cron, systemd, orchestrator, or environment change. Instance `i-0878c118835386ec2` / EIP `13.63.27.85` unchanged. All backfill work ran **Local** (`C:\GammaEnginePython`, Python 3.12) against Supabase over raw HTTP; it is **token-independent** (Supabase-only, no Kite/Dhan token) and safe across the 6 AM Kite-expiry and midnight boundaries.

**New Local backfill scripts (staged, not yet git-committed — carry to S63):**
- `backfill_hist_greeks.py` — vectorized numpy IV bisection over vendor `hist_option_bars_1m` (NOT mutated); reproduces `signed_gex_vec` verbatim (deep-ITM reject `|K−S|/S>0.05 AND |γ|>5e-5→0`; PE flip; `γ·oi·S²/1e7`); writes lean `iv`+`gamma` sidecar `hist_option_greeks_1m`. `--validate` gate sign≥98/sreg≥94/mag 0.9–1.1; `SKIP_EXPIRY` sentinel + `status=SKIPPED_EXPIRY` for same-day expiry (0-DTE flat-vol net_gex unreconstructible; live-sourced instead).
- `fill_gamma_concentration.py` — computes `gamma_concentration = max|gex|/sum|gex|` (verbatim `compute_gamma_concentration`; Herfindahl, scale-invariant) and idempotently PATCHes ONLY that column on the pre-existing `hist_gamma_metrics` rows, matched on (symbol, bar_ts). `--validate` reproduces existing-table net_gex.
- `run_fullwindow.py` — per-month solve+fill orchestration wrapper: timestamped heartbeat, tee to `fullwindow_backfill.log`, loud non-zero-exit abort + resume instruction, per-day resume granularity, token-independent.
- Diagnostics/patches (Local): `diag_1125.py` (0-DTE reconstructibility probe), `patch_expiry_skip.py` (canon-v3, `_PRE_EXPIRYSKIP`).

**New / filled tables:**
- `hist_option_greeks_1m` — **NEW** per-strike sidecar (lean `iv`+`gamma`; iv is the master key, every Greek recomputes from it). Vendor `hist_option_bars_1m` left unmutated.
- `hist_gamma_metrics` — **PRE-EXISTING** full-window (Apr 2025–Mar 2026) both-symbol 1-minute series (~91,325 NIFTY / 91,136 SENSEX rows; net_gex stored UNSCALED ×1e7 vs live /1e7 Cr). **This session's discovery:** it already carried net_gex/flip_level/regime etc.; its **one** empty column `gamma_concentration` was filled full-window for both symbols. NIFTY COMPLETE; SENSEX COMPLETE (`ALL DONE symbol=SENSEX total 1145.4 min`) **bar 2026-01-19** (SSLError mid-solve — TD-S62-NEW-2, one-line resume filed).

**New SQL (Supabase SQL editor):** `hist_option_greeks_1m` DDL; `chk_backfill_status_valid` CHECK widened to include `SKIPPED_EXPIRY`.

**New spec doc:** `docs/decisions/ENH-116-ambient-environment-intelligence.md` (301 ln / 18,762 B) — ENH-116 PROPOSED (P2).

**Diagnosis (no code change):** TD-S62-NEW — SENSEX `compute_flip_level` resolves to a spurious deep-tail flip (~−6.75%/−7.11%) under NEGATIVE_γ; isolated by StockMojo cross-engine parity as the sole divergent field. Fix (walk rewrite + short-γ display guard) carried to S63.

Cross-refs: tech_debt TD-S58-NEW-1 (RESOLVED) + TD-S62-NEW + TD-S62-NEW-2; Enhancement Register ENH-07 A CLOSED + ENH-116 PROPOSED; merdian_reference.json v41 S62 change_log; MERDIAN_System_Map.md §S62; CLAUDE.md v1.39.



## §S63 (2026-07-02) — ENH-115 FII/DII participant-positioning EOD cron + tables (AWS)

**ENH-115 P1 participant/cash EOD writer scheduled on MERDIAN AWS.** `ingest_participant_positioning.py` runs post-NSE-publish; two Mon–Fri crontab lines (snapshot-first install, `SHELL=/bin/bash` verified as crontab line 1; idempotent so a double-fire is safe):

```
0 14 * * 1-5  cd /home/ssm-user/meridian-engine && source .env && python3 ingest_participant_positioning.py >> logs/participant_positioning.log 2>&1
30 15 * * 1-5 cd /home/ssm-user/meridian-engine && source .env && python3 ingest_participant_positioning.py >> logs/participant_positioning.log 2>&1
```

- `0 14 * * 1-5` = 14:00 UTC / 19:30 IST — primary, after the ~19:00 IST NSE participant-OI + `fiidiiTradeReact` publish.
- `30 15 * * 1-5` = 15:30 UTC / 21:00 IST — expiry-day re-fire (late republish); idempotent upsert makes the double-run safe.

**New Supabase tables (writer targets):** `participant_oi_daily` (NSE/NSCCL participant-wise long/short OI; UPSERT on `(trade_date, participant)`; 5 rows/day: CLIENT/DII/FII/PRO/TOTAL), `fii_dii_cash_daily` (consolidated NSE+BSE+MSEI FII/FPI + DII buy/sell/net cash, from `fiidiiTradeReact`), `v_participant_oi_latest` (freshness view). Scope: participant-wise OI is **NSE-only** (no BSE equivalent — BSE participant stub dropped); FII/DII cash is **ONE consolidated report** (no separate BSE fetch). Deploy vector: Local → git → EC2 `git pull --ff-only`. Display-not-gate source; feeds ENH-116 Lens 3.

**Backfill (one-shot, not scheduled):** `backfill_participant_oi.py` ran 270 trading days 2025-05-28→2026-07-01 (0 failures). It deliberately does **not** use the DB `trading_calendar` gate (fail-opens on historical dates the reseeded table doesn't cover) — local Mon–Fri weekday filter + NSE archive 404 as holiday ground truth (Rule 18 corollary).
