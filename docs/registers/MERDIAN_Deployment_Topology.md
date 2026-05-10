# MERDIAN Deployment Topology

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Deployment_Topology.md` |
| Location | `docs/registers/` |
| Type | "What runs where" — Local Windows ↔ AWS EC2 boundary spec |
| Established | 2026-05-09 (Session 23 — created per Doc Protocol v4 Rule 9.2; Task Scheduler audit by Navin in same session closed System Map §G.1) |
| Update rule | Inline, same commit as the topology change. Triggers in Doc Protocol v4 Rule 1. |
| Companion | `MERDIAN_System_Map.md` for full file/table inventory; this document for environment placement only. |
| Forward link | This document is the canonical anchor for ADR-006 (reserved — AWS migration scope). When ADR-006 is drafted, it is the architectural decision; this Topology is the operational map. |

---

## Purpose

A single answer to "where does X run? what runs only on Local? what runs only on AWS? what runs on both?" Replaces scattered guidance in V18 §15.4/15.5, V18A §13.5, V18E §7.4/7.5, and CLAUDE.md gotchas.

The two environments are not symmetric. Local Windows is the **primary live execution environment** for signal generation, broker authentication, dashboards, and Phase 4A manual execution. AWS EC2 is the **shadow execution environment** for scheduled redundancy, EOD ingestion, and post-market capture. Treating them as interchangeable produces real failures (see §6 AWS gotchas).

---

## §1 — Side-by-side environment summary

| Aspect | Local Windows (PRIMARY LIVE) | AWS EC2 (SHADOW) |
|---|---|---|
| Path | `C:\GammaEnginePython\` | `/home/ssm-user/meridian-engine/` |
| Instance | Navin's Windows desktop, multi-WAN home network | t3.small, instance `i-0e60e4ed9ce20cefb`, region eu-north-1 |
| OS | Windows 10/11 | Ubuntu Linux |
| Scheduler | Windows Task Scheduler (17 `MERDIAN_*` tasks per Session 23 audit) | crontab (5 entries) |
| Python runtime | `python.exe` (currently CMD-window-spawning; TD-061 candidate for `pythonw.exe` migration) | `python3` |
| Live signal generation | ✅ Primary | ❌ Shadow only (writes shadow rows; not production decisions) |
| Broker auth — Dhan | ✅ TOTP retry | ✅ Token pulled from Local-written Supabase 03:05 UTC |
| Broker auth — Zerodha | ✅ KiteTicker WebSocket (NIFTY full chain) | ❌ Cannot — browser-based auth flow |
| Phase 4A manual execution | ✅ `merdian_trade_logger.py` + dashboard LOG TRADE button | ❌ |
| Dashboards | ✅ Three live dashboards (signal, monitor, live) | ❌ Headless |
| Supervisor | ✅ `gamma_engine_supervisor.py` + `start_supervisor_clean.ps1` | ❌ Cron-driven; no supervisor |
| Pipeline alert daemon | ✅ `merdian_pipeline_alert_daemon.py` | ❌ |
| Telemetry / heartbeat | ✅ `gamma_engine_telemetry_logger.py` writes `runtime/telemetry/*` | ❌ Not currently mirrored |
| EOD ingestion | ✅ Recovery path (when AWS misses) | ✅ Primary 16:10 IST cron |
| Post-market capture | ⚠ Topology question — task exists but JSON says AWS-only (see §6) | ✅ Cron 16:00 IST |
| Code editing | ✅ Sole permitted edit point | ❌ FORBIDDEN except BREAK_GLASS (Change Protocol Step 8) |
| Code distribution | Push to origin via `git push` | Pull via `git pull` from origin |
| Database | Same Supabase Postgres (shared single source of truth) | Same Supabase Postgres |

---

## §2 — Local-only scripts

These scripts only run on Local Windows. Either they require Windows-specific runtime (e.g. `CREATE_NO_WINDOW` subprocess flag), browser-based auth, GUI dashboards, or operational supervision that AWS does not provide.

| Script | Why Local-only |
|---|---|
| `ws_feed_zerodha.py` | Zerodha KiteTicker WebSocket. Auth flow is browser-redirect TOTP. Cannot run headless on AWS. |
| `run_option_snapshot_intraday_runner.py` | Primary live 5-min options runner. AWS has the shadow runner; this is production. |
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
| `merdian_start.py` | **CRITICAL — Local-only script that uses Windows-only `creationflags=CREATE_NO_WINDOW` and hardcoded Windows paths. Running on AWS causes frozen SSM terminal requiring EC2 reboot.** See §6 gotcha #1. |
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
| `run_ict_htf_zones_daily.bat` | `MERDIAN_ICT_HTF_Zones_0845` (08:45 IST) | Bat wrapper around `build_ict_htf_zones.py` |
| `run_po3_session_bias_once.bat` | `MERDIAN_PO3_SessionBias_1005` (10:05 IST) | Bat wrapper around `detect_po3_session_bias.py` |
| `run_market_close_capture_once.bat` | `MERDIAN_Market_Close_Capture` (~15:30 IST) | Local mirror of AWS's `run_market_close_capture_once.py` |
| `run_post_market_capture_once.bat` | `MERDIAN_Post_Market_1600_Capture` (~16:00 IST) | Local equivalent of AWS's `capture_postmarket_1600.py` (different script — see Topology §7.2 Note 2) |
| `run_market_spot_session_markers_once.bat` | `MERDIAN_Session_Markers_1602` (16:02 IST) | Post-close session markers update wrapper |
| `run_market_tape_1m.bat` | `MERDIAN_Market_Tape_1M` (functionally disabled) | Bat wrapper around `run_market_tape_1m.py` (auth-failing) |
| `run_ws_feed_zerodha.bat` | `MERDIAN_WS_Feed_0900` (~09:00 IST) | Bat wrapper around `ws_feed_zerodha.py` |
| `run_spot_mtf_rollup_once.bat` | `MERDIAN_Spot_MTF_Rollup_1600` (16:00 IST) | Wraps `build_spot_bars_mtf.py` |

These additions are pending integration into `merdian_reference.json` `files` (file paths and statuses) — that's a follow-up commit. This Topology is the canonical wiring map; the JSON is the canonical inventory.

---

## §3 — AWS-only scripts

These run only on AWS, primarily for scheduled redundancy or because AWS has reliable always-on cron when Local may be off.

| Script | Why AWS-only |
|---|---|
| `run_merdian_shadow_runner.py` | Shadow 5-min cycle. Breadth ingest disabled (V18E Guard 3 — single-writer rule). Runs in nohup. |
| `capture_postmarket_1600.py` | 16:00 IST close capture. JSON marks AWS-only. **Topology question:** Local also has `MERDIAN_Post_Market_1600_Capture` task — see §6 gotcha #5. |
| `run_market_close_capture_once.py` | AWS parity for close capture. Created V18A. |

---

## §4 — Both-environments scripts

These run on both. The boundary is operational, not architectural — Local is primary, AWS is shadow / fallback / EOD.

| Script | Local role | AWS role |
|---|---|---|
| `capture_market_spot_snapshot_local.py` | 1-min spot capture (Step 1 of intraday runner) | Cron `MERDIAN_PreOpen` 09:08 IST + on-demand by shadow runner |
| `capture_index_futures_snapshot_local.py` | Futures snapshot in cycle | Shadow capture |
| `ingest_option_chain_local.py` | Step 2 of cycle (Dhan REST + writes via Zerodha WS path) | Shadow ingest |
| `ingest_breadth_from_ticks.py` | Live breadth ingest (single-writer) | **DISABLED on AWS** (Guard 3 — single-writer rule) |
| `ingest_equity_eod_local.py` | EOD recovery path | Primary 16:10 IST cron via `run_equity_eod_until_done.py` wrapper |
| `build_market_state_snapshot_local.py` | Step 7 of cycle | Shadow path |
| `compute_gamma_metrics_local.py` | Step 3 | Shadow |
| `compute_iv_context_local.py` | Morning task `MERDIAN_IV_Context_0905` + per-cycle | Shadow |
| `compute_volatility_metrics_local.py` | Step 5 | Shadow |
| `build_momentum_features_local.py` | Step 6 | Shadow |
| `build_wcb_snapshot_local.py` | Per-cycle | Shadow |
| `build_trade_signal_local.py` | Step 9 — production signals | Shadow signals |
| `build_ict_htf_zones.py` | `MERDIAN_ICT_HTF_Zones_0845` task | Shadow build |
| `detect_ict_patterns.py` / `detect_ict_patterns_runner.py` | Step 8 of cycle | Shadow |
| `evaluate_shadow_vs_live.py` | Comparison runner | Comparison runner |
| `run_equity_eod_until_done.py` | Manual recovery | Primary EOD cron |
| `trading_calendar.py` | Hard gate at every cycle entry | Hard gate |
| `stage2_db_contract.py` | Pre-write contract check | Pre-write contract check |
| `refresh_dhan_token.py` | Local Task Scheduler trigger writes new token to .env + Supabase | AWS cron `MERDIAN_Token_Refresh` 09:05 IST + Supabase pull at 03:05 UTC |
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
   │ AWS EC2                                                 │
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

### 5.2 Zerodha token flow

```
   Local Windows ONLY
   ┌─────────────────────────────────────────────────────────┐
   │   Browser-based auth + TOTP                             │
   │     ↓                                                   │
   │   Zerodha access token written to .env / kite_session   │
   │     ↓                                                   │
   │   ws_feed_zerodha.py uses KiteTicker WebSocket          │
   │     ↓                                                   │
   │   option_chain_snapshots (NIFTY full chain rows)        │
   │                                                         │
   │   AWS does NOT participate — auth flow not headless.    │
   └─────────────────────────────────────────────────────────┘
```

### 5.3 Token-related runbook references

- `docs/runbooks/runbook_update_dhan_token.md` — full Dhan rotation procedure
- `docs/runbooks/runbook_update_kite_flow.md` — Zerodha update + verification (Step 3 runs `/home/ssm-user/meridian-engine/check_kite_auth.py`)
- `docs/runbooks/runbook_recover_dhan_401.md` — DhanError 401 recovery

---

## §6 — AWS gotchas (DO NOT)

These are operational rules learned from real failures. Each is honored by current code; documenting them here so they remain honored.

### 6.1 NEVER run `merdian_start.py` on AWS

Uses Windows-only `creationflags=CREATE_NO_WINDOW` and hardcoded Windows paths. Running on AWS:
- **Causes frozen SSM Session Manager terminal**
- **Requires EC2 reboot to recover**

This script is Local-only by design. There is no Linux equivalent. AWS bootstraps via cron + nohup; no equivalent to Local's supervisor.

### 6.2 NEVER use interactive `crontab -e` on AWS

Always use the non-interactive temp-file install pattern:
```bash
cat > /tmp/merdian_cron.txt << 'EOF'
<cron lines>
EOF
crontab /tmp/merdian_cron.txt
crontab -l
crontab -l > logs/aws_crontab_snapshot.txt
```

The reason: a malformed entry in interactive `crontab -e` can replace the entire crontab atomically with whatever was in the buffer. Snapshot every change to `logs/aws_crontab_snapshot.txt`.

### 6.3 NEVER direct-edit code on AWS (CLAUDE.md non-negotiable rule 1)

Edit only in Local. AWS receives code via `git pull`. The only exception is BREAK_GLASS (Change Protocol Step 8) and even that requires a Local commit to backfill within 24h. Direct edits on AWS:
- Get clobbered on next `git pull`
- Create silent Local↔AWS hash mismatch (preflight FAIL)
- Are a known anti-pattern from Sessions 4–6

### 6.4 NEVER enable breadth ingest on AWS

V18E Guard 3 — single-writer rule. `ingest_breadth_from_ticks.py` running on both environments would produce double-writes to `market_breadth_intraday`. AWS shadow runner explicitly disables breadth ingest via flag. Do not "fix" the disabled flag without understanding the rule.

### 6.5 NEVER assume shadow output equals live output

Shadow runner writes to dedicated shadow tables / shadow columns. The output of AWS shadow is **not** a backup of Local live signals. Before `evaluate_shadow_vs_live.py` reports parity, do not act on AWS-emitted signals as if they were live decisions.

### 6.6 Cron entries must use the env-loading pattern

Every cron entry must include:
```bash
/bin/bash -lc 'set -a; . ./.env; set +a; <command>'
```
Without this, `os.environ.get('SUPABASE_URL')` returns `None` and the script fails silently (or writes garbage). The `-lc` ensures login shell behavior.

### 6.7 SSH IP whitelisting fragility

Navin's Local environment runs a multi-WAN home network with load-balancer failover. Static IP whitelisting in the AWS security group breaks when the WAN flips. Permanent fix is **AWS Systems Manager Session Manager** instead of SSH (open ENH/TD candidate). Workaround: update the security group inbound rule when ISP IP changes.

---

## §7 — Cron entries (AWS) and Task Scheduler entries (Local)

### 7.1 AWS crontab (5 entries)

Source: `merdian_reference.json` `aws_cron`. Confirmed via `crontab -l > logs/aws_crontab_snapshot.txt` discipline.

| Label | Time IST | Cron | Action |
|---|---|---|---|
| `MERDIAN_Token_Refresh` | 09:05 | `5 9 * * 1-5` | `refresh_dhan_token.py` |
| `MERDIAN_PreOpen` | 09:08 | `8 9 * * 1-5` | `capture_market_spot_snapshot_local.py` |
| `MERDIAN_Shadow_Runner` | 09:15 | `15 9 * * 1-5` | `run_merdian_shadow_runner.py` (nohup) |
| `MERDIAN_Postmarket` | 16:00 | `30 10 * * 1-5` | `capture_postmarket_1600.py` (NOT YET PROVEN — A-02 open) |
| `MERDIAN_EOD` | 16:10 | `40 10 * * 1-5` | `run_equity_eod_until_done.py` (cursor-gate not ported — A-04 open) |

Times in cron column are UTC; IST = UTC + 5:30. Day-range `1-5` = Mon-Fri.

### 7.2 Windows Task Scheduler (17 entries — Session 23 audit, 2026-05-09)

Source: `Get-ScheduledTask -TaskName "MERDIAN_*"` PowerShell audit by Navin, Session 23. Action mapping captured via second PowerShell pass in same session. **This is the canonical inventory** — supersedes the partial 4-entry list in `merdian_reference.json` `task_scheduler`.

| Task | Trigger | Cadence | Action (canonical) | Notes |
|---|---|---|---|---|
| `MERDIAN_Daily_Audit` | Daily | Daily | `run_daily_audit.bat` | Action confirmed; bat wrapper not yet catalogued |
| `MERDIAN_EOD_Breadth_Refresh` | Daily | Daily | `powershell.exe -File run_eod_breadth_refresh.ps1` (Hidden window) | EOD indicator refresh wrapper |
| `MERDIAN_HB_Watchdog` | Time | Interval | `pythonw.exe merdian_watchdog.py --kill` | **pythonw — TD-061 partial migration**. `--kill` flag = process killer for hung runners |
| `MERDIAN_Watchdog` | Time | Interval | `powershell.exe -File watchdog_check.ps1` (Hidden) | Separate health-check companion to `merdian_watchdog.py` |
| `MERDIAN_ICT_HTF_Zones_0845` | Weekly Mon-Fri | 08:45 IST | `run_ict_htf_zones_daily.bat` → wraps `build_ict_htf_zones.py` (with `--timeframe H` Session 13) | TD-017 closure (Session 11 ext) |
| `MERDIAN_Intraday_Supervisor_Start` | Weekly Mon-Fri + AtLogon | 08:00 IST + logon | `powershell.exe -File merdian_morning_start.ps1` (Hidden) | **Not `start_supervisor_clean.ps1` as JSON had it** — `merdian_morning_start.ps1` is the canonical entry point; may internally invoke supervisor cleanup |
| `MERDIAN_IV_Context_0905` | Weekly Mon-Fri | 09:05 IST | `powershell.exe -File run_iv_context_once.ps1` (Hidden) → wraps `compute_iv_context_local.py` |
| `MERDIAN_Live_Dashboard` | LogonTrigger | At user logon | `pythonw merdian_live_dashboard.py --no-browser` (PYTHONIOENCODING=utf-8) | **pythonw — TD-061 migration done for this task**. `--no-browser` flag prevents auto-launching Streamlit browser |
| `MERDIAN_Market_Close_Capture` | Weekly Mon-Fri | ~15:30 IST | `powershell.exe -Command Start-Process cmd -ArgumentList /c run_market_close_capture_once.bat` (Hidden, Wait) | Local mirror of AWS's `run_market_close_capture_once.py` |
| `MERDIAN_Market_Tape_1M` | Weekly | (functionally disabled) | `run_market_tape_1m.bat` → wraps `run_market_tape_1m.py` | Task is `Ready` but script production-failing on DhanError 401 — see Note 1 |
| `MERDIAN_PO3_SessionBias_1005` | Weekly Mon-Fri | 10:05 IST | `cmd.exe /c run_po3_session_bias_once.bat` → wraps `detect_po3_session_bias.py` | ENH-75 SHIPPED Session 13 |
| `MERDIAN_Post_Market_1600_Capture` | Weekly Mon-Fri | ~16:00 IST | `powershell.exe -Command Start-Process cmd -ArgumentList /c run_post_market_capture_once.bat` (Hidden, Wait) | **Different script from AWS `capture_postmarket_1600.py`** — see Note 2 |
| `MERDIAN_PreOpen` | Weekly Mon-Fri | ~09:08 IST | `pythonw.exe capture_spot_1m.py` | **pythonw — TD-061**. **Different script from AWS PreOpen** (`capture_market_spot_snapshot_local.py`) — see Note 3 |
| `MERDIAN_Session_Markers_1602` | Weekly Mon-Fri | 16:02 IST | `powershell.exe -Command Start-Process cmd -ArgumentList /c run_market_spot_session_markers_once.bat` (Hidden, Wait) | Post-close session markers update — feeds `market_spot_session_markers.open_0915_ts` for next-day reference |
| `MERDIAN_Spot_1M` | Weekly | 1-min cadence | `pythonw.exe capture_spot_1m_v2.py` | **pythonw — TD-061. v2 of the spot capturer** — different from PreOpen's v1. Likely the current production 1-min spot ingester (replacing the disabled `MERDIAN_Market_Tape_1M`) |
| `MERDIAN_Spot_MTF_Rollup_1600` | Weekly Mon-Fri | 16:00 IST | `powershell.exe -Command Start-Process cmd -ArgumentList /c run_spot_mtf_rollup_once.bat` → wraps `build_spot_bars_mtf.py` | Session 9 closure of TD-019/023, ENH-71 instrumented |
| `MERDIAN_WS_Feed_0900` | Weekly Mon-Fri | ~09:00 IST | `cmd.exe /c run_ws_feed_zerodha.bat` → wraps `ws_feed_zerodha.py` | Session 13 task registration |

#### Notes — clarified by canonical action mapping

**Note 1: `MERDIAN_Market_Tape_1M` Ready ≠ functional.** Task state shows `Ready` but `run_market_tape_1m.py` (wrapped by `run_market_tape_1m.bat`) has been failing with `DhanError 401` on every run since 2026-04-07. **`MERDIAN_Spot_1M` running `capture_spot_1m_v2.py` is the active replacement** — confirmed by the v2 naming. Two cleanup paths: (a) disable `MERDIAN_Market_Tape_1M` in Task Scheduler to match script reality, (b) fix the auth issue in `run_market_tape_1m.py`. Recommend (a). Filed as TD candidate.

**Note 2: Post-market capture is two different scripts on two environments.** Local task `MERDIAN_Post_Market_1600_Capture` runs `run_post_market_capture_once.bat`; AWS cron `MERDIAN_Postmarket` runs `capture_postmarket_1600.py`. They're not duplicates of the same script — they're parallel implementations of the same intent on each environment. The remaining question is whether they both write to `market_spot_snapshots` and produce duplicate 16:00-IST rows. Resolution: single SQL query
```sql
SELECT ts, COUNT(*) FROM market_spot_snapshots
WHERE ts BETWEEN '<recent date> 10:30:00 UTC' AND '<recent date> 10:35:00 UTC'
GROUP BY ts HAVING COUNT(*) > 1;
```
(16:00 IST = 10:30 UTC). If duplicates exist, disable one of the two.

**Note 3: PreOpen 09:08 is two different scripts.** Local `MERDIAN_PreOpen` runs `capture_spot_1m.py`; AWS cron `MERDIAN_PreOpen` runs `capture_market_spot_snapshot_local.py`. The script names differ, but both presumably target a 09:08 IST PreOpen capture for `market_spot_session_markers.open_0915_ts`. Same dupe-check applies, at 03:38 UTC. **Open architectural question:** which script is canonical? `capture_spot_1m.py` is on Local (uses pythonw, post-TD-061); `capture_market_spot_snapshot_local.py` is on AWS (older). If they diverge in behavior (column writes, edge handling), one needs to be retired in favor of the other. ADR-006 (AWS migration scope) territory.

#### Architectural insights from the audit

1. **TD-061 (pythonw.exe migration to suppress CMD windows) is partially complete.** Four tasks already use `pythonw.exe`: `HB_Watchdog`, `Live_Dashboard`, `PreOpen`, `Spot_1M`. Eleven other tasks still wrap through `.bat` files via `cmd.exe` or `powershell.exe -Command Start-Process cmd`. The migration pattern is in flight; tasks already running pythonw are the precedent for converting the rest.

2. **Two watchdog architectures coexist intentionally.** `merdian_watchdog.py --kill` (process killer) is the active intervention layer — kills hung Python processes detected by ENH-90 and similar. `watchdog_check.ps1` is the passive observation layer — checks state, writes alerts. They run on different intervals (both `MSFT_TaskTimeTrigger` but different periods presumably). Worth capturing as separate ENH-NN if not already.

3. **Three layers of indirection for most tasks.** Pattern: `Task → powershell.exe -Command Start-Process cmd /c <runner>.bat → cmd → python <script>.py`. The `Start-Process cmd ... -WindowStyle Hidden -Wait` pattern is the alternative to pythonw — it suppresses the cmd window but still spawns one. The pythonw direct-call pattern (used by PreOpen, Spot_1M, Live_Dashboard) is cleaner. TD-061 wants to extend this everywhere.

4. **`merdian_morning_start.ps1` is the supervisor entry point**, not `start_supervisor_clean.ps1` as JSON `task_scheduler` had it. The .ps1 named in JSON may be called *by* `merdian_morning_start.ps1` internally, or may be a stale name. Worth a one-time read of `merdian_morning_start.ps1` to confirm what it dispatches.

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

### 8.2 AWS runtime artifacts

Located under `/home/ssm-user/meridian-engine/`:

| Path | Purpose |
|---|---|
| `logs/aws_shadow_runner.nohup.log` | nohup output of shadow runner |
| `logs/dhan_token_refresh.log` | Daily Dhan token refresh log |
| `logs/premarket.log` | PreOpen capture log |
| `logs/postmarket.log` | Postmarket capture log |
| `logs/eod.log` | EOD ingest log |
| `logs/aws_crontab_snapshot.txt` | Snapshot of crontab — refreshed every install per §6.2 discipline |
| `.env` | Environment file (DHAN_ACCESS_TOKEN refreshed 03:05 UTC daily) |

AWS does **not** currently mirror Local's `runtime/telemetry/` directory. Heartbeat / health-snapshot infrastructure is Local-only.

---

## §9 — Open boundary questions

Items where the Local↔AWS boundary is unresolved or requires verification. Updated post Session 23 action-mapping audit — three questions clarified, several remain.

| # | Question | Status | Resolution path |
|---|---|---|---|
| 1 | Does Local `MERDIAN_Post_Market_1600_Capture` (`run_post_market_capture_once.bat`) and AWS `MERDIAN_Postmarket` (`capture_postmarket_1600.py`) write duplicate rows to `market_spot_snapshots`? | **CLOSED S25 2026-05-10 — confirmed dual-write** | Empirical SQL audit across 2026-05-04 → 2026-05-08 (5 trading days): both writers produced 16:00 IST rows on every day. **Disposition (per Phase α Q2 capture/derived split):** AWS canonical for capture stage; Local writer to be disabled. Action queued for ADR-006 execution phase, gated on TD-080 closure per Phase α Q3 sequencing. |
| 2 | Same question for PreOpen 09:08: Local (`capture_spot_1m.py`, pythonw) vs AWS (`capture_market_spot_snapshot_local.py`) | **CLOSED S25 2026-05-10 — original framing inaccurate** | Empirical audit revealed there was **no actual dual-write at 09:08 IST** — AWS is sole writer at the 09:08 boundary. Local `MERDIAN_PreOpen` was a 09:05 IST task (different boundary, auction window), not 09:08. Local 09:05 task DISABLED same-session S25 (see new section below). Q2 as filed was based on Topology §7.2 Task Scheduler audit naming similarity, not on observed timestamps. |
| 3 | Is `capture_spot_1m_v2.py` the production-active 1-min spot ingester, replacing the disabled `MERDIAN_Market_Tape_1M`? | LIKELY YES, per audit | One-shot evidence: query `market_spot_snapshots` write rate during a recent trading hour. If ~60 rows/hour on Local timestamps, v2 is doing the work. Update JSON `files` inventory. |
| 4 | What does `merdian_morning_start.ps1` actually invoke? Does it call `start_supervisor_clean.ps1` internally, or is the JSON entry stale? | OPEN | One-time read of the .ps1 file. 5 minutes of work. |
| 5 | Confirm the split between `merdian_watchdog.py --kill` (Python process killer) and `watchdog_check.ps1` (PowerShell health check) | LIKELY INTENTIONAL per audit | Worth filing as ENH/operational note documenting the two-watchdog architecture, so future sessions don't try to consolidate them. |
| 6 | Should AWS gain telemetry mirroring (heartbeat / health snapshots) for full operational parity? | OPEN | ENH candidate. Not blocking. |
| 7 | Static IP SSH whitelisting fragility from multi-WAN | OPEN | Move to AWS Systems Manager Session Manager. ENH candidate. |
| 8 | AWS cron `MERDIAN_Postmarket` not yet proven (A-02 open) — needs one full day's evidence of successful run | **PARTIAL EVIDENCE S25 2026-05-10** | 5-day evidence captured 2026-05-04 → 2026-05-08 confirms `MERDIAN_Postmarket` cron writes `market_spot_snapshots` rows at 16:00 IST on every trading day in window (per Q1 dual-write audit). Operational reliability proven for the post-market boundary. A-02 status to be updated formally when ADR-006 disposition executes. |
| 9 | AWS cron `MERDIAN_EOD` cursor-gate logic not ported from V17D1 (A-04 open) | OPEN | Code port required. |
| 10 | Should `MERDIAN_Market_Tape_1M` task be disabled in Task Scheduler to match the script's DhanError 401 production reality? | OPEN — recommend YES | Single Task Scheduler change. File as TD if not already. |
| 11 | Should TD-061 (pythonw migration) be extended to the 11 cmd-spawning tasks, given the precedent of `HB_Watchdog`/`Live_Dashboard`/`PreOpen`/`Spot_1M` already on pythonw? | OPEN | Operational ENH. Each .bat wrapper would need an equivalent direct pythonw call. Worth a session of consolidation work. |

These eleven questions are the proper scope of ADR-006 (reserved — AWS migration scope) when it gets drafted. Items 1–3 in particular are the empirical observations ADR-006 needs as evidence base.

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

## §10 — How to use this map

**At session start:** Read §1 (the side-by-side summary) plus the section relevant to the question being asked.

**Before adding a new script:** Decide §2 / §3 / §4 placement explicitly. Don't default to "both" — Local has 17 already-scheduled tasks; AWS has 5 cron entries. New scheduling on either side is a topology change and per Doc Protocol v4 Rule 10 may require an ADR.

**Before changing cron / task / scheduler:** Update this document in the same commit as the change. Do not let scheduler reality drift from documentation again — Session 17 reactivation was visible only via Task Scheduler audit, not docs.

**Before any AWS operation:** Re-read §6 AWS gotchas. They are short and learned from real failures.

---

## Update log

| Date | Session | Event |
|---|---|---|
| 2026-05-09 | Session 23 (initial) | Created. Sourced from V18 §15.4/15.5, V18A §13.5, V18E §7.4/7.5, CLAUDE.md gotchas, `merdian_reference.json` `environments` + `aws_cron` + `aws_runtime_files` + (partial) `task_scheduler`. **Task Scheduler audit by Navin (PowerShell `Get-ScheduledTask`)** revealed 17 `MERDIAN_*` tasks vs JSON's 4 — full inventory captured in §7.2. Three boundary discrepancies surfaced (post-market dual-environment, pre-open dual-environment, Market_Tape_1M Ready vs DhanError 401). Eight open boundary questions filed in §9. |
| 2026-05-09 | Session 23 (action map pass) | **Canonical action map populated** for all 17 Task Scheduler entries via second PowerShell pass. Surfaced ~15 newly-catalogued scripts (added to §A.2). Three architectural insights: (a) TD-061 pythonw migration is partially complete (4 tasks already pythonw), (b) two-watchdog architecture (`merdian_watchdog.py --kill` + `watchdog_check.ps1`) is intentional, (c) `merdian_morning_start.ps1` (not `start_supervisor_clean.ps1`) is the supervisor entry point. PreOpen and Post-market "duplicates" reframed as different-scripts-same-table writes. §9 expanded from 8 to 11 open questions. |
| 2026-05-10 | Session 25 | **§9 Q1 CLOSED** (post-market 16:00 dual-write empirically confirmed via 5-day audit 2026-05-04 → 2026-05-08; disposition queued for ADR-006 execution gated on TD-080). **§9 Q2 CLOSED and reframed** — original framing inaccurate; no actual dual-write at 09:08 IST; Local 09:05 task was a different (pre-open auction) boundary, not 09:08. **§9 Q8 PARTIAL EVIDENCE** — Postmarket cron 5-day reliability captured. **New §9.A section** documents Local `MERDIAN_PreOpen` (09:05 IST) DISABLED via PowerShell `Disable-ScheduledTask`, durable; `ret_session` anchor migrated 09:05 → 09:08 and validated via ADR-008 replay; Mon 2026-05-12 verification plan filed. **Phase α Q2 (capture/derived split, four-stage decomposition)** answered S25; ADR-006 drafting gated on TD-080 closure per Phase α Q3 sequencing. |

---

*MERDIAN Deployment Topology — established Session 23, 2026-05-09. Updated inline per Doc Protocol v4 Rule 1 + Rule 9.2. Anchor for ADR-006 (AWS migration scope) when drafted.*
