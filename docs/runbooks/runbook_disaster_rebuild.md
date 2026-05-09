# RUNBOOK: Disaster rebuild (cold rebuild from zero)

> **Purpose.** If chat history, Supabase context, and local machine state are all partially or fully lost — this runbook enables MERDIAN to be rebuilt with minimal trial and error. Promotes V15.1/V16 Appendix A to current ICT-era state per Doc Protocol v4 Rule 9.6.

---

| Field | Value |
|---|---|
| **Operation** | Cold rebuild of MERDIAN from zero — local Windows + AWS shadow + Supabase backend + Dhan/Zerodha brokers |
| **Frequency** | As-needed (catastrophic failure / audit reproduction / fresh dev environment) |
| **Environment** | Both Local primary + AWS shadow |
| **Prerequisites** | Dhan account + TOTP authenticator · Zerodha account + TOTP · Supabase project credentials · AWS account with EC2 SSM access · GitHub access · Windows 10/11 machine · Python 3.12 · Git |
| **Expected duration** | 4–8 hours of focused work, plus 1 trading day of historical backfill running |
| **Who can do this** | Navin only (broker auth flows are not delegable) |
| **Last verified end-to-end** | **Never as a single procedure post-V18F.** V15.1/V16 Appendix A was validated March 2026 against the pre-ICT architecture. Each individual phase below has been operationally exercised since (most recently in normal live operation as of Session 22, 2026-05-07), but the full cold-rebuild flow has not been executed against the current architecture. **Treat this runbook as the most accurate available specification, but expect to encounter at least one undocumented gap; update this runbook in the same session as any gap discovery.** |

---

## When to use this runbook

Three triggers:

1. **Catastrophic loss** — Local machine destroyed, Supabase project lost, or both. The runbook is the institutional knowledge of how MERDIAN goes back together.
2. **Audit reproduction** — A reviewer needs to verify that MERDIAN can be rebuilt from `git` + Supabase + broker credentials alone. The runbook is the audit response.
3. **Fresh dev environment** — A new contributor or a clean Windows installation needs to come up from zero. The runbook is the onboarding path.

This is **not** the runbook for routine operational restarts (use `runbook_restart_runner_local.md` / `_aws.md` instead) or for token rotation (use `runbook_update_dhan_token.md` / `runbook_update_kite_flow.md`). Those are scoped to a single component.

---

## Phase overview

The rebuild is sequential. Each phase has a single completion gate that must be satisfied before the next phase begins.

| # | Phase | Output | Completion gate |
|---|---|---|---|
| 1 | Foundation | Local machine has code, env, deps, broker access | `python test_core_layer.py` returns Supabase OK + Dhan OK |
| 2 | Schema | Supabase has all production tables | `SELECT count(*)` succeeds on all 36 tables |
| 3 | Historical data | Historical OHLCV + breadth + ICT zones backfilled | `hist_spot_bars_5m` ≥ 40k rows, `hist_pattern_signals` ≥ 6k rows |
| 4 | Live runner | 5-min cycle producing live signals | `signal_snapshots` writing every 5 min during market hours |
| 5 | ICT layer | ICT pattern detection live in cycle | `signal_snapshots.ict_pattern` populated when patterns fire |
| 6 | Phase 4A execution | Manual trade-logger + Zerodha WebSocket live | LOG TRADE button works in dashboard; Zerodha NIFTY full chain ticking |
| 7 | AWS shadow | AWS shadow runner operational | AWS cron runs Mon-Fri without errors; shadow rows populate |
| 8 | Task Scheduler | 17 Local tasks registered | `Get-ScheduledTask -TaskName "MERDIAN_*"` returns 17 entries |
| 9 | Validation | Full system health check passes | All B.1–B.6 verification queries return expected output |

Rollback points are between phases. Within a phase, partial completion is recoverable; across phases, partial state is not.

---

## Phase 1 — Foundation

### 1.1 Clone repository

```bash
cd C:\
git clone <repo-url> GammaEnginePython
cd GammaEnginePython
git log --oneline -5    # confirm latest commits
```

*What to expect:* Folder tree matches `MERDIAN_System_Map.md` §A. `CLAUDE.md` exists at root. `docs/` populated.

### 1.2 Install Python 3.12 (if needed) and dependencies

```powershell
# Check Python
python --version    # expect 3.12.x (use C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe path if needed)

pip install -r requirements.txt
```

*What to expect:* All packages install cleanly. Common dependencies: `supabase`, `dhanhq`, `kiteconnect`, `pyotp`, `python-dotenv`, `pandas`, `numpy`, `streamlit` (for dashboards).

### 1.3 Recreate `.env` from secure secrets store

Create `C:\GammaEnginePython\.env` with the following keys (values from your secrets store — never commit):

```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<service-role-key>
SUPABASE_ANON_KEY=<anon-key>

DHAN_CLIENT_ID=<dhan-client-id>
DHAN_ACCESS_TOKEN=<placeholder — refreshed in step 1.5>
DHAN_TOTP_SECRET=<base32-totp-secret>

KITE_API_KEY=<zerodha-api-key>
KITE_API_SECRET=<zerodha-api-secret>
KITE_ACCESS_TOKEN=<placeholder — refreshed in Phase 6>
KITE_TOTP_SECRET=<base32-totp-secret>

TELEGRAM_BOT_TOKEN=<optional, for alert routing>
TELEGRAM_CHAT_ID=<optional>
```

⚠ **`.env` must never enter Git.** Confirm `.gitignore` excludes it.

### 1.4 Generate fresh Dhan token via TOTP

```bash
python refresh_dhan_token.py
```

*What to expect:* Browser-based OAuth flow OR direct TOTP if scripted. Token written to `.env` `DHAN_ACCESS_TOKEN` and to Supabase `system_config` (or equivalent). V18E added auto-retry on `InvalidTOTP` (waits 30s).

⚠ **Token is valid for one trading day.** Re-run daily 08:35-ish IST (handled by Task Scheduler in Phase 8).

### 1.5 Verify core connectivity

```bash
python test_core_layer.py
```

*Expected output:*
```
Supabase connection: OK
Dhan API connection: OK
```

**Completion gate for Phase 1:** Both lines OK. Do not proceed to Phase 2 with either failing.

---

## Phase 2 — Schema

### 2.1 Enable pgcrypto extension on Supabase

In Supabase SQL editor:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### 2.2 Recreate operational tables — deploy in dependency order

DDLs are not inlined here (they total several thousand lines). Source: V18 master Section 17 + V18 appendix Block 5 (schema changes) + post-V18 ALTER TABLEs from `merdian_reference.json` `tables.<name>.alter_table`.

**Deploy order matters** — tables that read from others must come after them:

1. **Calendar / config:** `trading_calendar`, `breadth_universe_members`, `dhan_scrip_map`
2. **Breadth foundation:** `equity_eod`, `equity_intraday_last`, `breadth_indicators_daily`, `breadth_ingest_state`
3. **Breadth live:** `market_breadth_intraday`, `breadth_intraday_history`, `latest_market_breadth_intraday` (view)
4. **Spot tape:** `market_spot_snapshots`, `market_spot_session_markers`
5. **Options:** `option_chain_snapshots`, `index_futures_snapshots`
6. **Computed metrics:** `gamma_metrics`, `volatility_snapshots`, `iv_context_snapshots`, `momentum_snapshots`, `momentum_snapshots_v2`, `weighted_constituent_breadth_snapshots`
7. **Market state:** `market_state_snapshots`
8. **Signals:** `signal_snapshots` (with ICT columns), `signal_regret_log`, `shadow_signal_snapshots_v3`
9. **ICT layer:** `ict_htf_zones`, `ict_zones`, `hist_pattern_signals`, `hist_spot_bars_5m`, `hist_spot_bars_15m`, `hist_atm_option_bars_5m`, `hist_atm_option_bars_15m`
10. **PO3 (V18G+):** `po3_session_state`
11. **Manual / shadow:** `smdm_snapshots`, `options_flow_snapshots`

⚠ **`signal_snapshots` requires the post-V18A ALTER TABLE** for ICT columns:
```sql
ALTER TABLE public.signal_snapshots
  ADD COLUMN IF NOT EXISTS ict_pattern text,
  ADD COLUMN IF NOT EXISTS ict_tier text,
  ADD COLUMN IF NOT EXISTS ict_size_mult numeric,
  ADD COLUMN IF NOT EXISTS ict_mtf_context text,
  ADD COLUMN IF NOT EXISTS po3_session_bias text;
```

Plus the V18A `gamma_zone` column on `gamma_metrics`. See `merdian_reference.json` `tables.<name>.ict_columns.alter_table` for each.

### 2.3 Create runtime directories (Local)

```powershell
mkdir C:\GammaEnginePython\runtime
mkdir C:\GammaEnginePython\runtime\heartbeats
mkdir C:\GammaEnginePython\runtime\telemetry
mkdir C:\GammaEnginePython\runtime\logs
mkdir C:\GammaEnginePython\runtime\lock
```

### 2.4 Verify schema

```sql
SELECT table_name, COUNT(*) OVER() AS total_tables
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Completion gate for Phase 2:** All ~36 tables present per `MERDIAN_System_Map.md` §B inventory. View `latest_market_breadth_intraday` exists. No errors on `SELECT count(*)` on any table.

---

## Phase 3 — Historical data backfill

This phase ingests the year of historical data that ICT detection and signal validation depend on. Expect a half-day to a full day of running scripts.

### 3.1 Populate trading calendar

```sql
-- Insert calendar rows for the period of interest
-- Source: NSE trading holiday calendar
INSERT INTO trading_calendar (trade_date, is_trading_day, holiday_reason, ...)
VALUES (...);
```

⚠ `trading_calendar` is the hard gate at every cycle entry. Missing rows = system treats day as non-trading. See `runbook_add_calendar_row.md`.

### 3.2 Backfill breadth universe

```bash
# breadth_universe_members - manual seed from current Nifty 500 + index drivers
# breadth_indicators_daily - run for last 365 days
python ingest_equity_eod_local.py --backfill --from 2025-04-01 --to 2026-04-30
```

*What to expect:* `equity_eod` populates one trading day at a time. Cursor advances per day in `breadth_ingest_state`.

### 3.3 Backfill historical OHLCV

```bash
# Spot bars 5m and 15m
python build_spot_bars_mtf.py --backfill --from 2025-04-01 --to 2026-04-30

# ATM option bars (5m and 15m)
python build_atm_option_bars_mtf.py --backfill --from 2025-04-01 --to 2026-04-30
```

*Expected row counts post-backfill (per session 23 reference):*
- `hist_spot_bars_5m`: ~41,000–42,000 rows (NIFTY + SENSEX, full year)
- `hist_spot_bars_15m`: ~14,000 rows
- `hist_atm_option_bars_5m`: ~27,000 rows
- `hist_atm_option_bars_15m`: ~9,600 rows

### 3.4 Backfill ICT historical zones and patterns

```bash
# Historical HTF zones (D, H, 4H)
python build_ict_htf_zones_historical.py --from 2025-04-01 --to 2026-04-30

# Historical pattern signals (5m source)
python build_hist_pattern_signals_5m.py --backfill
```

*Expected row counts:*
- `ict_htf_zones`: dependent on the period; ~50–100 zones per day visible × full year
- `hist_pattern_signals`: ~6,300+ rows (source=backfill_5m)

### 3.5 Backfill signal regret log (optional, for analytics)

```bash
python build_signal_regret_log_v1.py --backfill
```

Original V18A baseline was 614 rows. Re-running against current data will produce a different count.

**Completion gate for Phase 3:** Row counts above achieved (within ±5%). Spot-check: `SELECT MIN(ts), MAX(ts) FROM hist_spot_bars_5m` returns the full backfill range.

---

## Phase 4 — Live runner

### 4.1 Verify trading calendar has today's row

```sql
SELECT * FROM trading_calendar WHERE trade_date = CURRENT_DATE;
```

If missing, add it (per 3.1) or use `runbook_add_calendar_row.md`.

### 4.2 Test single-cycle dry-run (outside market hours, optional)

```bash
python run_option_snapshot_intraday_runner.py --dry-run
```

*What to expect:* All 9 steps execute. No DB writes if `--dry-run` is honored. Logs go to `runtime/logs/`.

### 4.3 Start supervisor

```powershell
powershell -ExecutionPolicy Bypass -File merdian_morning_start.ps1
# OR (older path)
python gamma_engine_supervisor.py
```

*What to expect:* Supervisor heartbeat starts. `runtime/heartbeats/` populates.

### 4.4 Start alert daemons

```bash
python gamma_engine_alert_daemon.py
python merdian_pipeline_alert_daemon.py
```

### 4.5 Live cycle will start at 09:15 IST

If during market hours: the supervisor + scheduler should auto-start `run_option_snapshot_intraday_runner.py` at the next 5-min tick. Verify:

```sql
SELECT ts, symbol, action, confidence_score, trade_allowed, ict_pattern, po3_session_bias
FROM signal_snapshots
WHERE ts >= NOW() - INTERVAL '15 minutes'
ORDER BY ts DESC
LIMIT 10;
```

*Expected:* Rows for both NIFTY and SENSEX, every 5 min.

**Completion gate for Phase 4:** `signal_snapshots` has new rows every 5 min during market hours. `market_state_snapshots` has the corresponding row. No `C-N` critical bugs in `merdian_reference.json` `open_items`.

---

## Phase 5 — ICT layer (already wired into Phase 4 cycle, but verify separately)

ICT pattern detection is a step in `run_option_snapshot_intraday_runner.py` (Step 8). This phase validates that the ICT layer is producing expected outputs.

### 5.1 Build today's HTF zones (08:45 IST)

Manual trigger if Task Scheduler not yet up (Phase 8):

```bash
python build_ict_htf_zones.py --timeframe D --timeframe H
```

*What to expect:* New rows in `ict_htf_zones` for today's session. Status `LIVE`. Daily and Hourly zones written.

### 5.2 Verify intraday zones populating

```sql
SELECT zone_id, symbol, zone_type, status, created_at
FROM ict_zones
WHERE created_at >= CURRENT_DATE
ORDER BY created_at DESC
LIMIT 20;
```

### 5.3 Verify PO3 session bias detection

```bash
# Mon-Fri 10:05 IST in production via MERDIAN_PO3_SessionBias_1005
python detect_po3_session_bias.py
```

```sql
SELECT trade_date, symbol, po3_state, sweep_direction, sweep_ts
FROM po3_session_state
WHERE trade_date = CURRENT_DATE;
```

### 5.4 Verify signal_snapshots ICT columns populated

```sql
SELECT ts, symbol, action, ict_pattern, ict_tier, ict_size_mult, ict_mtf_context, po3_session_bias
FROM signal_snapshots
WHERE ts >= CURRENT_DATE
  AND ict_pattern IS NOT NULL
ORDER BY ts DESC
LIMIT 10;
```

**Completion gate for Phase 5:** When ICT patterns fire, `signal_snapshots` rows carry the four ICT columns plus `po3_session_bias`. Empty when no pattern (expected — most cycles produce DO_NOTHING per the architecture).

---

## Phase 6 — Phase 4A execution layer

### 6.1 Generate Zerodha access token

```bash
python check_kite_auth.py
```

⚠ **Browser-based.** Opens login flow; you complete it manually. TOTP-required. Writes `KITE_ACCESS_TOKEN` to `.env`.

See `runbook_update_kite_flow.md` for details.

### 6.2 Start Zerodha WebSocket feed

```bash
python ws_feed_zerodha.py
```

*What to expect:* `option_chain_snapshots` starts receiving rows from Zerodha (alongside Dhan REST writes — note the dual writers).

### 6.3 Start dashboards

```bash
python merdian_signal_dashboard.py
python merdian_live_dashboard.py
python gamma_engine_monitor_dashboard.py
```

Each opens in a browser. Dashboards run via `pythonw.exe` post-TD-061.

### 6.4 Verify trade logger

The LOG TRADE button on `merdian_signal_dashboard.py` should:
1. Capture the user's selection (which signal row to log)
2. Call `merdian_trade_logger.py` with the row identifiers
3. Write to the trade log table (or signal_snapshots augmentation)

Test by manually clicking after a signal fires; verify the trade entry persists.

**Completion gate for Phase 6:** Zerodha WS ticking, dashboards live, LOG TRADE captures at least one test entry.

---

## Phase 7 — AWS shadow setup

### 7.1 Provision EC2 instance

If rebuilding from zero — t3.small, eu-north-1, Ubuntu 24, with SSM Session Manager enabled (preferred over SSH per `MERDIAN_Deployment_Topology.md` §6.7).

### 7.2 Clone repo on AWS

```bash
sudo -u ssm-user bash
cd /home/ssm-user
git clone <repo-url> meridian-engine
cd meridian-engine
```

### 7.3 Install Python deps and recreate AWS .env

```bash
sudo apt update && sudo apt install python3-pip -y
pip3 install -r requirements.txt

# .env on AWS — same SUPABASE_* and DHAN_* keys as Local. NO Kite keys (AWS does not run WS feed).
nano .env    # or scp from a secure source
chmod 600 .env
```

### 7.4 Install AWS crontab (5 entries)

```bash
cat > /tmp/merdian_cron.txt << 'EOF'
5  9 * * 1-5  cd /home/ssm-user/meridian-engine && /bin/bash -lc 'set -a; . ./.env; set +a; python3 refresh_dhan_token.py >> logs/dhan_token_refresh.log 2>&1'
8  9 * * 1-5  cd /home/ssm-user/meridian-engine && /bin/bash -lc 'set -a; . ./.env; set +a; python3 capture_market_spot_snapshot_local.py >> logs/premarket.log 2>&1'
15 9 * * 1-5  cd /home/ssm-user/meridian-engine && /bin/bash -lc 'set -a; . ./.env; set +a; nohup python3 run_merdian_shadow_runner.py >> logs/aws_shadow_runner.nohup.log 2>&1 &'
30 10 * * 1-5  cd /home/ssm-user/meridian-engine && /bin/bash -lc 'set -a; . ./.env; set +a; python3 capture_postmarket_1600.py >> logs/postmarket.log 2>&1'
40 10 * * 1-5  cd /home/ssm-user/meridian-engine && /bin/bash -lc 'set -a; . ./.env; set +a; python3 run_equity_eod_until_done.py >> logs/eod.log 2>&1'
EOF
crontab /tmp/merdian_cron.txt
crontab -l > logs/aws_crontab_snapshot.txt
```

⚠ **NEVER use interactive `crontab -e`** — see `MERDIAN_Deployment_Topology.md` §6.2.

### 7.5 Test shadow runner manually

```bash
cd /home/ssm-user/meridian-engine
/bin/bash -lc 'set -a; . ./.env; set +a; python3 run_merdian_shadow_runner.py'
```

*What to expect:* Runs once. Writes shadow rows. No `breadth_intraday` writes (single-writer rule per V18E Guard 3).

⚠ **Never run `merdian_start.py` on AWS** — it uses Windows-only `creationflags=CREATE_NO_WINDOW` and freezes the SSM terminal requiring EC2 reboot. See Topology §6.1.

**Completion gate for Phase 7:** AWS cron registered (5 entries via `crontab -l`). One manual shadow runner run completes without errors. Token pulled from Supabase per the Local-writes-AWS-pulls flow.

---

## Phase 8 — Local Task Scheduler bootstrap

Register all 17 `MERDIAN_*` tasks. Use `schtasks /create` or PowerShell. Source actions from `MERDIAN_Deployment_Topology.md` §7.2 canonical action map.

**Action mapping summary** (full detail in Topology §7.2):

| Task | Trigger | Action |
|---|---|---|
| `MERDIAN_Daily_Audit` | Daily | `run_daily_audit.bat` |
| `MERDIAN_EOD_Breadth_Refresh` | Daily | `powershell.exe -File run_eod_breadth_refresh.ps1` |
| `MERDIAN_HB_Watchdog` | Time interval | `pythonw.exe merdian_watchdog.py --kill` |
| `MERDIAN_Watchdog` | Time interval | `powershell.exe -File watchdog_check.ps1` |
| `MERDIAN_ICT_HTF_Zones_0845` | Mon-Fri 08:45 IST | `run_ict_htf_zones_daily.bat` |
| `MERDIAN_Intraday_Supervisor_Start` | Mon-Fri 08:00 + AtLogon | `powershell.exe -File merdian_morning_start.ps1` |
| `MERDIAN_IV_Context_0905` | Mon-Fri 09:05 IST | `powershell.exe -File run_iv_context_once.ps1` |
| `MERDIAN_Live_Dashboard` | AtLogon | `pythonw merdian_live_dashboard.py --no-browser` |
| `MERDIAN_Market_Close_Capture` | Mon-Fri ~15:30 IST | `run_market_close_capture_once.bat` |
| `MERDIAN_Market_Tape_1M` | Weekly | `run_market_tape_1m.bat` (currently DhanError 401) |
| `MERDIAN_PO3_SessionBias_1005` | Mon-Fri 10:05 IST | `run_po3_session_bias_once.bat` |
| `MERDIAN_Post_Market_1600_Capture` | Mon-Fri ~16:00 IST | `run_post_market_capture_once.bat` |
| `MERDIAN_PreOpen` | Mon-Fri ~09:08 IST | `pythonw.exe capture_spot_1m.py` |
| `MERDIAN_Session_Markers_1602` | Mon-Fri 16:02 IST | `run_market_spot_session_markers_once.bat` |
| `MERDIAN_Spot_1M` | Weekly (1-min cadence loop) | `pythonw.exe capture_spot_1m_v2.py` |
| `MERDIAN_Spot_MTF_Rollup_1600` | Mon-Fri 16:00 IST | `run_spot_mtf_rollup_once.bat` |
| `MERDIAN_WS_Feed_0900` | Mon-Fri ~09:00 IST | `run_ws_feed_zerodha.bat` |

### 8.1 Verify all 17 are registered

```powershell
Get-ScheduledTask -TaskName "MERDIAN_*" | Select TaskName, State
```

**Completion gate for Phase 8:** All 17 tasks present and `Ready`.

---

## Phase 9 — Validation

### B.1 Core connectivity

```bash
python test_core_layer.py
```

Expected: `Supabase connection: OK | Dhan API connection: OK`

### B.2 Breadth pipeline

```sql
-- Latest breadth snapshot has all 15 columns
SELECT ts, universe_count, advances, declines, breadth_score, breadth_regime
FROM market_breadth_intraday
ORDER BY ts DESC LIMIT 1;

-- Coverage check (>=1375 GREEN, >=1100 AMBER)
SELECT COUNT(*) FROM equity_intraday_last
WHERE ts > NOW() - INTERVAL '20 minutes';
```

### B.3 Options and gamma

```sql
SELECT symbol, ts, regime, net_gex, flip_level, flip_distance_pct, dte, straddle_atm, gamma_zone
FROM gamma_metrics
ORDER BY ts DESC LIMIT 4;

-- VIX in volatility snapshots
SELECT symbol, ts, atm_iv_avg, india_vix, vix_change, vix_regime, vix_percentile_regime
FROM volatility_snapshots
ORDER BY ts DESC LIMIT 4;
```

### B.4 Market state and signals

```sql
SELECT symbol, ts,
  gamma_features      IS NOT NULL AS has_gamma,
  breadth_features    IS NOT NULL AS has_breadth,
  volatility_features IS NOT NULL AS has_volatility,
  momentum_features   IS NOT NULL AS has_momentum
FROM market_state_snapshots
ORDER BY ts DESC LIMIT 4;

SELECT ts, market_state_ts, symbol, action, confidence_score, trade_allowed,
       ict_pattern, ict_tier, po3_session_bias
FROM signal_snapshots
ORDER BY created_at DESC LIMIT 10;
```

### B.5 ICT layer

```sql
SELECT zone_id, symbol, zone_type, status, COUNT(*) OVER() AS total
FROM ict_htf_zones
WHERE created_at >= CURRENT_DATE
LIMIT 10;

SELECT trade_date, symbol, po3_state, sweep_direction
FROM po3_session_state
WHERE trade_date = CURRENT_DATE;
```

### B.6 Component heartbeat

```bash
python gamma_engine_health_check.py
```

Expected during live session: `ENGINE: HEALTHY | PIPELINE: HEALTHY | SYMBOL_SYNC: OK`
Post-session: `ENGINE: CLOSED_OK | PIPELINE: HEALTHY | SESSION: POSTMARKET`

### B.7 Dupe-check the dual-writer surfaces (post Session 23 audit)

```sql
-- Post-market 16:00 dupe check (16:00 IST = 10:30 UTC)
SELECT ts, COUNT(*)
FROM market_spot_snapshots
WHERE ts BETWEEN CURRENT_DATE + interval '10:29' AND CURRENT_DATE + interval '10:31'
GROUP BY ts HAVING COUNT(*) > 1;

-- PreOpen 09:08 dupe check (09:08 IST = 03:38 UTC)
SELECT ts, COUNT(*)
FROM market_spot_snapshots
WHERE ts BETWEEN CURRENT_DATE + interval '03:37' AND CURRENT_DATE + interval '03:39'
GROUP BY ts HAVING COUNT(*) > 1;
```

If duplicates found: see `MERDIAN_Deployment_Topology.md` §9 questions #1 and #2.

**Completion gate for Phase 9:** All B.1–B.7 queries return expected output. No critical (`C-N`) bugs in `merdian_reference.json` `open_items`. Live cycle running for 1 hour without supervisor intervention.

---

## Rollback points

If a phase fails irrecoverably, the system can be rolled back to the previous phase's completion gate. The state at each gate is well-defined:

| After phase | Recoverable from | Cost of redo |
|---|---|---|
| 1 | Just clone again, redo .env | Minutes |
| 2 | Drop tables, redo DDLs | Minutes |
| 3 | Truncate hist_* and ict_* tables, rerun backfills | Hours (long backfills) |
| 4 | Stop runner, fix, restart | Minutes |
| 5 | Detector misbehavior — revert detector code via Git (see Session 17 `_PRE_S17_TD060.py` precedent), rerun cycle | Minutes |
| 6 | Phase 4A is additive — disable trade-logger button, system continues to produce signals | Trivial |
| 7 | Disable AWS cron entries, fix, redeploy | Minutes |
| 8 | Disable problem tasks one at a time | Minutes per task |

---

## Failure modes

| If you see… | It probably means… | Do this |
|---|---|---|
| `test_core_layer.py` Supabase fails | Wrong URL/key in `.env`, or VPN issue | Verify `.env` matches secrets store; try Supabase UI to confirm project alive |
| `test_core_layer.py` Dhan fails | Token expired or wrong client ID | `python refresh_dhan_token.py` (TOTP) — see `runbook_recover_dhan_401.md` |
| Phase 2 DDL errors "relation X already exists" | Tables partially exist from prior attempt | Either DROP CASCADE and redo, or skip-and-verify per `IF NOT EXISTS` |
| Phase 3 backfill very slow | Dhan rate-limit or one-row-at-a-time pattern | Verify pagination v2 in `merdian_utils.py`; for EOD use cursor-gated `run_equity_eod_until_done.py` |
| Live cycle: `signal_snapshots` not populating | Calendar gate, supervisor not running, or runner crashed | Check `trading_calendar` for today's row; check supervisor heartbeat in `runtime/heartbeats/`; check `runtime/logs/` for runner crash |
| ICT patterns never firing | `ict_htf_zones` not built today, or `hist_spot_bars_5m` not populating | Run `build_ict_htf_zones.py` manually; verify `MERDIAN_ICT_HTF_Zones_0845` task ran |
| Zerodha WS auth fails | TOTP expired or token expired | `runbook_update_kite_flow.md` — full reauth flow |
| Frozen SSM terminal on AWS | Someone ran `merdian_start.py` on AWS | EC2 reboot. **Do not** repeat. Topology §6.1. |
| Local↔AWS commit hash mismatch | Direct edit on AWS, or push not propagated | `runbook_resolve_hash_mismatch.md` |
| Task Scheduler shows tasks `Disabled` | Runaway-process kill (Session 17 precedent) | Re-enable with PowerShell loop. See Session 17 memory notes for command. |

---

## Related

- **Source documents:**
  - `MERDIAN_Master_V15_1.docx` Appendix A — original V15.1 procedure (March 2026, pre-ICT)
  - `MERDIAN_Master_V16_Fixed.docx` Appendix A — V16 18-step procedure (March 2026, pre-ICT)
- **Architectural context required to interpret this runbook:**
  - `MERDIAN_System_Map.md` — file/table inventory, pipeline diagrams
  - `MERDIAN_Deployment_Topology.md` — Local↔AWS boundaries, full action map for §8 task list
  - `MERDIAN_Governance_Framework.md` §8 — Do-NOT-Revive list (rebuild must not reintroduce these)
  - `ADR-007-v18f-ict-pivot.md` — current signal architecture
- **Component-specific runbooks** (use these when only a part is failing, not the whole system):
  - `runbook_update_dhan_token.md`
  - `runbook_update_kite_flow.md`
  - `runbook_restart_runner_local.md` / `runbook_restart_runner_aws.md`
  - `runbook_backfill_missing_day.md`
  - `runbook_resolve_hash_mismatch.md`
  - `runbook_recover_dhan_401.md`
  - `runbook_add_calendar_row.md`
  - `runbook_emergency_stop.md`

---

## Change history

| Date | Change | Commit |
|---|---|---|
| 2026-03 | Original V15.1 Appendix A authored (18 steps, pre-ICT architecture) | (V15.1 era) |
| 2026-03 | V16 Appendix A — same procedure, light editing | (V16 era) |
| 2026-05-09 | Promoted to standalone runbook at `docs/runbooks/runbook_disaster_rebuild.md`. Refreshed for current ICT-era architecture. Phased structure replaces flat 18-step list. New phases: ICT layer (§5), Phase 4A execution including Zerodha WebSocket (§6), AWS shadow setup (§7), 17-task Scheduler bootstrap (§8 — sourced from Session 23 audit), validation expanded with B.5 (ICT) and B.7 (dupe-check). Rollback points and failure modes added. Session 23. | `<commit-hash>` |

---

## Honest limitations of this runbook

This runbook has not been executed end-to-end against the current architecture as a single procedure. Each phase derives from current operational knowledge captured in the registers, but the seams between phases (especially Phase 3 → 4 → 5 ordering, and Phase 7 timing of AWS bring-up relative to Local) have not been re-validated post-V18F.

**Update obligation.** The first time this runbook is executed end-to-end, every gap or correction encountered must be back-filled into the document in the same session. The first execution is also a documentation event.

**Known unknowns:**
- Several wrappers (`run_daily_audit.bat`, `run_eod_breadth_refresh.ps1`, etc.) are listed by task association but their internal contents have not been read in this consolidation. A first execution will surface what they invoke and any bootstrap dependencies.
- The exact `signal_snapshots` schema after all post-V18A ALTER TABLEs have been applied is not consolidated in one place — it is reassembled from multiple appendix Block 5 sources. Worth a one-session schema-snapshot enhancement (suggested in System Map §G.4).
- The internal contents of `merdian_morning_start.ps1` are not captured here (Topology §9 question #4 — pending audit).

---

*Runbook — commit with `MERDIAN: [OPS] runbook_disaster_rebuild — created/updated`. The runbook is an artifact of institutional knowledge; treat it as a living specification subject to update on every execution.*
