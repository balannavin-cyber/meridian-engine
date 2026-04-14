## 2026-04-13 (late night) — engineering / documentation — WebSocket deployment, Phase 4A completion, V18G audit + v2

**Goal:** Deploy Zerodha WebSocket feed on MERDIAN AWS, complete remaining Phase 4A wiring, build AppendixV18G rebuild-grade documentation, conduct independent audit, produce v2.

**Session type:** engineering / documentation

**Completed:**

ENH-51a — Zerodha WebSocket Feed:
- `ws_feed_zerodha.py` deployed on MERDIAN AWS (i-0878c118835386ec2)
- kiteconnect installed on MERDIAN AWS. ZERODHA_API_KEY + ZERODHA_ACCESS_TOKEN added to MERDIAN AWS .env
- market_ticks DDL applied to MERDIAN Supabase (bigserial PK, 3 indexes, 19 columns)
- Instrument load: 45,712 NFO rows → 998 options + 6 futures + 3 spots = 1,007 total (within 3,000 limit)
- Spot-only dry run: NIFTY 50 23,842.65 | NIFTY BANK 55,605.05 | INDIA VIX 20.50 — all 3 ticks fired
- Live write test: 3 rows in market_ticks confirmed (2026-04-14 02:25:44 UTC)
- AWS cron added: 44 3 * * 1-5 (start 09:14 IST), 02 10 * * 1-5 (stop 15:32 IST)
- --ddl flag bug fixed (was inside __main__ block, hung on WebSocket load). fix_ws_ddl.py applied. Committed a215049.
- Git: beb8709 (ws_feed_zerodha.py) → a215049 (--ddl fix)

Phase 4 architecture design:
- Option A (manual, NOW) → B (semi-auto, after 2-4wk live data) → C (full auto, after 4B stable)
- Option B: merdian_order_placer.py + position monitor via Dhan API
- Option C: merdian_auto_executor.py + merdian_risk_gate.py
- Execution architecture documented in Enhancement Register v7 (ENH-49/50)

WebSocket broker architecture finalised:
- Zerodha KiteTicker: NIFTY full chain (3,000 limit, 100% GEX accuracy, 1,007 instruments)
- Dhan REST: SENSEX only (Zerodha has no BSE F&O) — unchanged
- MeridianAlpha: stays EOD via Zerodha Kite REST. Same Supabase. Integration deferred pending G-01.
- ENH-51 revised architecture documented and committed (355d5cf → 173a63f)

Pre-market and scheduler gap documented:
- Zerodha WebSocket does NOT serve pre-market (09:00–09:08 call auction). MERDIAN_PreOpen (Dhan) covers this.
- HTF zone rebuild (build_ict_htf_zones.py --timeframe D) is MANUAL — unresolved scheduler gap. Needs cron on AWS.
- systemd service documented as the correct supervisor pattern for AWS primary (not Python supervisor)

AppendixV18G:
- V18G v1 written (756 paragraphs, validated)
- Independent audit conducted: 19 findings (6 HIGH, 8 MEDIUM, 5 LOW)
- Key HIGH findings: F-02 fix_dashboard_v2 regex damage missing, F-03 three CAPITAL_FLOOR locations, F-05 options_flow_snapshots absent, F-09 ict_zones/ict_htf_zones/momentum_snapshots absent, F-14 Dhan option chain API missing
- V18G v2 rewritten incorporating all 19 findings (1,017 paragraphs, validated)
- All registers and JSON updated per protocol

**Files changed:** ws_feed_zerodha.py (NEW on MERDIAN AWS), fix_ws_ddl.py, Enhancement Register v7 (ENH-51a/b/c/d/e/f revised), session_log.md (this prepend)

**Schema changes:** market_ticks (NEW in MERDIAN Supabase — DDL applied)

**Open items closed:** ENH-51a (ws_feed_zerodha.py deployed and validated)

**Open items added:** OI-11 (HTF zone cron on AWS), OI-12 (market_ticks retention cron), OI-13 (Telegram credentials)

**Git commit hash:** a215049 (Local + MERDIAN AWS)

**Next session goal:** First live session with all systems (session 10). Pre-market: build_ict_htf_zones.py --timeframe D, python merdian_start.py, python run_preflight.py. Verify: AWS write_cycle_status, ret_session non-null, ICT zones ~09:30, market_ticks populating.

**docs_updated:** yes

---

## 2026-04-13 (late evening) — engineering — Phase 4A + ENH-02/04/06/07 + Signal Engine

**Goal:** Wire options flow into signal engine, build Phase 4A execution layer, close remaining Tier 1 ENH items.

**Session type:** engineering

**Completed:**

ENH-02/04/07 — Options flow wired into confidence scoring:
- `build_trade_signal_local.py`: fetches `options_flow_snapshots` each cycle
- PCR BEARISH+BUY_PE → +5, PCR BULLISH+BUY_CE → +5, contra → -4
- SKEW FEAR+BUY_PE → +4, SKEW GREED+BUY_CE → +4
- FLOW PE_ACTIVE+BUY_PE → +3, FLOW CE_ACTIVE+BUY_CE → +3
- ENH-07: basis_pct note added (futures premium/discount vs spot)
- Max lift on aligned signal: +12 confidence
- All stored in raw JSONB (no DDL needed)

ENH-06 — Pre-trade cost filter:
- `build_trade_signal_local.py`: validates lot sizing against capital at signal time
- Reads capital_tracker, estimates lot cost via estimate_lot_cost()
- If deployed > allocated × 1.10: reduces to 1 lot, adds caution
- Stores enh06_capital_ok, enh06_allocated, enh06_lot_cost in raw JSONB

Phase 4A — Manual execution layer:
- `merdian_trade_logger.py`: CLI trade logger. Reads latest signal, prompts entry price, writes trade_log + exit_alerts rows. Also handles --show (open trades) and --close (exit + PnL)
- `merdian_exit_monitor.py`: polls exit_alerts every 30s, fires console + Telegram alert at T+30m
- `merdian_signal_dashboard.py`: LOG TRADE button (green, appears when action ≠ DO_NOTHING), CLOSE TRADE button (always visible), modal dialogs, POST /log_trade + /close_trade endpoints
- `merdian_pm.py`: exit_monitor added to PROCESSES dict
- `merdian_start.py`: exit_monitor added to startup sequence
- Process manager fix: DETACHED_PROCESS removed (breaks supabase client), single file handle passed to Popen

Phase 4 architecture decisions:
- Option A (manual) now live
- Option B (semi-auto): merdian_order_placer.py + position monitor — after 2-4 weeks 4A data
- Option C (full auto): auto executor + risk gate — after 4B proven stable
- trade_log + exit_alerts tables confirmed existing and empty

**Open after session:**
- Telegram credentials not in .env — exit_monitor alerts console-only until configured
- Phase 4B: merdian_order_placer.py (Dhan API order placement)
- ENH-08: vega bucketing — deferred (weekly options only, low value)
- ENH-30: SMDM — deferred post-Phase 4
- Shadow gate session 10 tomorrow (Tue 2026-04-15) — then Phase 4 full promotion decision

**Files changed:** build_trade_signal_local.py (ENH-02/04/06/07), merdian_signal_dashboard.py (LOG TRADE button + endpoints), merdian_pm.py (exit_monitor + loghandle fix), merdian_start.py (exit_monitor in start order), merdian_trade_logger.py (NEW), merdian_exit_monitor.py (NEW)

**Schema changes:** None (trade_log + exit_alerts already existed)

**Open items closed:** ENH-02 (PCR), ENH-04 (IV skew/flow), ENH-06 (pre-trade cost filter), ENH-07 (basis note)

**Open items added:** None

**Git commit hash:** 54272e1

**Next session goal:** Shadow gate session 10. Pre-market: python merdian_start.py then python run_preflight.py. If session clean → Phase 4 promotion decision.

**docs_updated:** yes

---

## 2026-04-13 (evening) — engineering — Process Manager, ENH-36 Live Spot, ENH-01 ret_session, Bug Fixes

**Goal:** Post-market engineering. Process manager, live 1-min spot capture, ICT backfill, signal timestamp fix, AWS status writer fix, ret_session fix.

**Session type:** engineering

**Completed:**

ENH-46 — Process Manager:
- `merdian_pm.py` — core library: start processes in background (no terminal), PID registry at `runtime/merdian_pids.json`, stop/status/duplicate detection, port conflict check
- `merdian_start.py` — single morning startup command: Step 0 auto-inserts trading_calendar row (permanent V18A-03 fix), Step 1 kills all, Step 2 starts health_monitor + signal_dashboard + supervisor in background
- `merdian_stop.py` — kills all registered + unregistered MERDIAN processes
- `merdian_status.py` — shows all processes with PID, uptime, port, duplicate warnings. `--watch` mode (5s refresh)
- Health monitor: process status panel added (MERDIAN Processes card with PID/status/port per process)
- Zero terminal windows needed — all processes log to `logs/pm_<n>.log`

ENH-36 / ENH-47 — Live 1-min spot capture:
- `capture_spot_1m.py` — calls Dhan IDX_I, writes to `market_spot_snapshots` AND `hist_spot_bars_1m` (synthetic bar O=H=L=C=spot, truncated to minute)
- Task: `MERDIAN_Spot_1M` — every 1 minute, 09:14–15:31 IST Mon–Fri
- Task: `MERDIAN_PreOpen` — fires 09:05 IST Mon–Fri (closes C-07b permanently)
- Dashboard refresh: 60s (was 300s)

C-07b CLOSED — MERDIAN_PreOpen task fires at 09:05 IST Mon–Fri, before supervisor starts at 09:14. Pre-open spot now captured reliably.

ENH-01 — ret_session fix:
- `build_momentum_features_local.py` line ~224: threshold changed from `03:45 UTC` to `03:35 UTC` so MERDIAN_PreOpen capture at 09:05 IST (03:35 UTC) is accepted as session open price
- `ret_session` was computing but returning None because `market_spot_snapshots` had no rows after 03:45 UTC
- From tomorrow: `ret_session` will be non-null, feeding into momentum_regime (2.5x weight)

hist_spot_bars_1m backfill (today's session):
- 750 rows backfilled via Zerodha Kite on MeridianAlpha AWS (375 bars × 2 symbols)
- Confirmed: both instruments at 376 bars (375 + 1 test bar from capture_spot_1m test)

Signal dashboard fixes:
- Spot source changed from `market_spot_snapshots` to `signal_snapshots` (updates every 5-min cycle)
- Signal timestamp UTC→IST conversion fixed (was showing 03:55 IST instead of 09:25 IST)

AWS shadow runner fix:
- `write_cycle_status_to_supabase`: `json=payload` → `json=[payload]`, added `on_conflict=config_key`, removed `"updated_at": "now()"` string, added error logging
- Health monitor STALE 80h display will clear from tomorrow's first cycle
- Git: ab87044 (AWS) + c78b6ea (Local)

Capital floor lowered:
- `merdian_utils.py` + dashboard: CAPITAL_FLOOR 200,000 → 10,000 for trial runs

**Open after session:**
- Shadow gate session 10 tomorrow (Tue 2026-04-15)
- ENH-41 code: BEAR_OB DTE=0/1 combined structure (rule documented, code pending execution layer)
- capital_tracker auto-update after T+30m trade close (needs execution layer)
- ENH-02 PCR signal, ENH-04 IV skew (in progress)

**Files changed:** merdian_pm.py (NEW), merdian_start.py (NEW), merdian_stop.py (NEW), merdian_status.py (NEW), capture_spot_1m.py (NEW), set_capital.py (NEW), backfill_spot_zerodha.py (NEW), merdian_signal_dashboard.py (NEW), merdian_live_dashboard.py (process panel), build_momentum_features_local.py (ret_session threshold), run_merdian_shadow_runner.py (AWS — cycle status writer fix), merdian_utils.py (capital floor)

**Schema changes:** None

**Open items closed:** C-07b (MERDIAN_PreOpen task), ENH-01 (ret_session threshold fix)

**Open items added:** None

**Git commit hash:** c78b6ea (Local) | ab87044 (AWS runner fix)

**Next session goal:** Shadow gate session 10 (tomorrow). Pre-market: `python merdian_start.py` then `python run_preflight.py`.

**docs_updated:** yes

---

## 2026-04-13 — engineering / documentation — ENH-38 Full Build + Dashboard + Registers

**Goal:** Close all open items from research session: Kelly sizing end-to-end, signal dashboard, backfill, Signal Rule Book v1.1, register updates.

**Session type:** engineering / documentation

**Completed:**

OI-09 — capital_tracker table:
- CREATE TABLE public.capital_tracker (symbol PK, capital numeric, updated_at timestamptz)
- Seeded NIFTY + SENSEX at INR 2L each
- Capital floor lowered to INR 10K for trial runs

OI-08 / ENH-38 — Live Kelly tiered sizing (end-to-end):
- merdian_utils.py: LOT_SIZES (NIFTY=65, SENSEX=20), effective_sizing_capital(), estimate_lot_cost() (spot × IV × √DTE × 0.4), compute_kelly_lots(). ACTIVE_KELLY single-line strategy switch.
- detect_ict_patterns_runner.py: reads capital_tracker each cycle, fetches DTE via nearest_expiry_db, computes _lots_t1/t2/t3 with real lot cost, writes to ict_zones. Log: "Kelly lots (lot_size=65, dte=2d, iv=16.3%) T1:x T2:x T3:x"
- build_trade_signal_local.py: reads lots from active ict_zones row, forwards to signal_snapshots.ict_lots_t1/t2/t3
- Supabase: ict_zones +3 cols, signal_snapshots +3 cols
- Lot sizes corrected: NIFTY=65 (Jan 2026), SENSEX=20. Live patchers: patch_kelly_sizing.py → patch_kelly_lot_cost.py → patch_signal_kelly_lots.py

OI-07 — experiment_15b:
- Date type fix: _daily_str = {str(k): v for k, v in daily_ohlcv.items()} passed to detect_daily_zones
- LOT_SIZE corrected: NIFTY=75 (majority of backtest year), SENSEX=20
- Run complete. Results: Strategy C +6,764% combined, Strategy D +16,249% combined. MERDIAN-filtered universe (Exp 16) outperforms pure ICT (Exp 15b) — regime filter confirmed additive.

ENH-43 — Signal dashboard (merdian_signal_dashboard.py, port 8766):
- Action, confidence, ICT pattern/tier/WR/MTF, execution block (strike, expiry, DTE, live premium, lot cost, deployed capital), exit countdown timer (⚡ EXIT NOW at T+30m), active-pattern-only WR legend per card, regime pills, BLOCKED/TRADE ALLOWED badge, hard rules banner. Auto-refresh 5min.

ENH-44 — Capital management:
- set_capital.py: CLI setter supporting NIFTY/SENSEX/BOTH, ceiling notes, show command
- Dashboard: per-symbol number input + SET button, POST /set_capital, instant feedback without page reload

ENH-45 — hist_spot_bars_1m backfill (Apr 7–10):
- Zerodha Kite 1-min historical API via MeridianAlpha AWS instance (same Supabase)
- backfill_spot_zerodha.py: 4 dates × 2 symbols × 375 bars = 3,000 rows
- Upserts on (instrument_id, bar_ts). Verified: all 8 pairs at exactly 375 bars, 09:15–15:29 IST (UTC 03:45–09:59 confirmed)
- Enables correct daily zone pre-building for Apr 7–10 sessions

OI-10 / ENH-40 — Signal Rule Book v1.1:
- docs/research/MERDIAN_Signal_RuleBook_v1.1.md written
- 13 rule changes from v1.0: 4 NEW, 3 CHANGED, 5 CONFIRMED, 1 CLOSED
- Covers all patterns, MTF hierarchy, exit rules, signal engine gates, capital/sizing, quick reference card

**Open after session:**
- Shadow gate sessions 9 and 10 (today Monday, Tuesday)
- C-07b: pre-open capture gap — architectural fix pending
- ENH-41: BEAR_OB DTE combined structure — documented in Rule Book, code pending execution layer
- capital_tracker auto-update after T+30m trade close (requires execution layer)

**Files changed:** merdian_utils.py (Kelly sizing + lot cost), detect_ict_patterns_runner.py (Kelly block), build_trade_signal_local.py (lots passthrough), merdian_signal_dashboard.py (NEW — port 8766), set_capital.py (NEW), backfill_spot_zerodha.py (NEW — MeridianAlpha AWS)

**Schema changes:** capital_tracker (NEW — 3 cols), ict_zones (+ict_lots_t1/t2/t3), signal_snapshots (+ict_lots_t1/t2/t3)

**Open items closed:** OI-07, OI-08, OI-09, OI-10

**Open items added:** None

**Git commit hash:** [pending commit]

**Next session goal:** Shadow gate session 9 today (live market). Pre-market: python build_ict_htf_zones.py --timeframe D. Start merdian_signal_dashboard.py on port 8766.

**docs_updated:** yes

---

## 2026-04-12 — research — Full Experiment Series + Sizing Architecture + Documentation

**Goal:** Complete all 11 overnight experiments, analyse results, establish sizing architecture, document everything.

**Session type:** research / documentation

**Git end:** e24297f (Local + AWS in sync)

**Documents produced this session:**
- MERDIAN_AppendixV18F_v2.docx (rebuild-grade, audit-corrected) — docs/appendices/
- MERDIAN_Enhancement_Register_v5.md — docs/registers/
- MERDIAN_OpenItems_Register_v6.md — docs/registers/
- MERDIAN_Experiment_Compendium_v1.md — docs/registers/
- merdian_reference.json v3 — docs/registers/ (git updated, shadow gate 8/10, 6 new files, 3 new tables, 8 new governance rules, research_findings key added)
- session_log.md — prepended (this entry)

**Completed:**

Overnight runner fixes (encoding + expiry):
- UTF-8 cp1252 encoding fixed via PYTHONIOENCODING=utf-8 in subprocess env
- EXPIRY_WD compute_dte patched in all remaining scripts via fix_remaining_errors.py
- build_ict_htf_zones.py f-string corruption repaired
- 8/11 experiments completed overnight. 3 remaining fixed and run this session.

All 11 experiments now complete (full year Apr 2025–Mar 2026):

Experiment results summary:
- Exp 2: BULL_OB 88.9% WR +41.9% T+30m, BEAR_OB 73.0% +34.9%. BEAR_OB AFTERNOON -24.7% (hard skip). BULL_OB AFTERNOON 100% WR +75.3% (new TIER1).
- Exp 2b: Options beat futures on every pattern/DTE. Only exception: BEAR_OB DTE=0 and DTE=1 (combined structure wins). Futures experiments permanently closed.
- Exp 2c: Fixed-6 beats pyramid 1→2→3 on every pattern. Session pyramid deferred (ENH-42).
- Exp 2c v2: Judas T2 rate 12%→44% with T+15m confirmation window. Still fixed position wins.
- Exp 5: VIX gate removed for BULL_OB and BULL_FVG. Kept for BEAR_OB HIGH_IV. IV-scaled sizing per pattern established.
- Exp 8: MOM_YES = strongest filter (+21.6pp lift on BEAR_OB). IMP_WEK preferred over IMP_STR.
- Exp 10c: MEDIUM context (1H zone) outperforms HIGH (daily) for BULL_OB (+73.5% vs +40.7%). BULL_FVG|HIGH|DTE=0 new TIER1 rule (+58.9%, 87.5% WR). BEAR_FVG HIGH context destroys edge (-40.2%).
- Exp 15: Pure ICT, 1-lot compounding. BEAR_OB 94.4% WR. MEDIUM (1H zone) 77.3% WR. T+30m beats ICT structure break by 41%. Max DD 1.1% NIFTY.
- Exp 16: Kelly tiered sizing with capital ceiling. Strategy C (Half Kelly) +18,585% INR 7.47Cr. Strategy D (Full Kelly) +44,234% INR 17.7Cr. Both realistic and tradeable with INR 25L/50L ceiling.

Key decisions:
1. Futures experiments permanently closed. Options only.
2. INR 50L capital ceiling — liquidity constraint. INR 25L sizing freeze.
3. Strategy D (Full Kelly) selected for live. Start with C, upgrade after 3-6 months.
4. T+30m exit confirmed final. No further exit experiments needed.
5. 1H zones (MEDIUM context) confirmed in ENH-37 hierarchy.
6. BEAR_OB AFTERNOON hard skip rule.
7. BEAR_OB DTE=0/1 combined structure (futures + CE insurance) not pure PE.

Experiment 15b started but incomplete (date type mismatch in detect_daily_zones). Non-blocking.

Documentation produced:
- Enhancement Register v5
- Open Items Register v6
- MERDIAN_Experiment_Compendium_v1.md (new)
- session_log.md prepended (this entry)

Next session goals:
1. Shadow gate sessions 9 and 10 (Monday and Tuesday)
2. Build capital_tracker Supabase table (OI-09)
3. Implement ENH-38 Live Kelly Sizing in runner
4. Update Signal Rule Book v1.1 (OI-10)
5. Fix and run Experiment 15b (OI-07)

**Git commit:** fee7b7c → [pending after doc commit]

---

## 2026-04-11 — research / engineering — ENH-35 Validation + ENH-37 Full Build + Signal Engine Overhaul

**Goal:** Validate signal engine accuracy, apply ENH-35 findings, build ENH-37 ICT detection layer end-to-end.

**Session type:** research / engineering

**Completed:**

Expiry bug found and fixed:
- NIFTY switched Thursday→Tuesday expiry Sep 2025. Hardcoded `EXPIRY_WD = {"NIFTY": 3}` caused all post-Aug 2025 sessions to be skipped as "no option data" in all 11 experiment scripts. DB confirmed full option coverage Apr 2025–Mar 2026 (not a vendor gap — a code bug).
- Fix: `merdian_utils.py` — `build_expiry_index_simple()` + `nearest_expiry_db()`. All 11 scripts patched via `patch_expiry_fix.py`. ENH-31 CLOSED.

Experiments 14 + 14b — session pyramid definitively closed:
- Exp 14 (v1, mid-bounce): Pyramid -₹9,044 (22% WR) vs single T+30m +₹8,329 (100% WR) across 9 sessions.
- Exp 14b (v2, confirmed reversal): v2 improved v1 by ₹3,133 but still -₹12,645 vs single trade.
- Verdict: Single T+30m exit on first OB remains optimal. Session pyramid deferred to post-ENH-42 (WebSocket + bullish sessions needed).

ENH-35 — three validation runs:
- Run 1 (baseline): NIFTY 47.4% below random, 25,762 signals
- Run 2 (+3 changes): SHORT_GAMMA 55.5%, overall still noisy, 8,967 signals
- Run 3 (+6 changes): NIFTY 58.6% STRONG EDGE, 244 signals/year
- Final: trade_allowed=YES pool 268 bars, 55.2% accuracy. Phase 4 target met.
- Key finding: CONFLICT BUY_CE (breadth BULLISH + momentum BEARISH) = 67.9% at N=661 — the old CONFLICT rule was blocking the best trades.

Six signal engine changes applied and validated:
1. CONFLICT BUY_CE now trades (58.7% SENSEX / 55.4% NIFTY)
2. LONG_GAMMA → DO_NOTHING (47.7% — below random)
3. NO_FLIP → DO_NOTHING (45-48% — below random)
4. VIX gate removed (HIGH_IV has more edge — Experiment 5)
5. Confidence threshold 60→40 (edge in conf_20-49 band)
6. Power hour gate — no signals after 15:00 IST (SENSEX 20.8% expiry noise eliminated)

ENH-37 ICT Pattern Detection Layer — all 6 steps complete:
- `ict_zones` (28 cols) + `ict_htf_zones` (16 cols) created in Supabase
- `detect_ict_patterns.py` — ICTDetector class, VERY_HIGH/HIGH/MEDIUM/LOW MTF hierarchy, tier assignment from Experiment 8, breach detection
- `build_ict_htf_zones.py` — W/D/H zone builder. 1H layer added after design discussion (bridges timeframe gap). 39 zones written on first run.
- `detect_ict_patterns_runner.py` — runner integration, every 5-min cycle, non-blocking
- Signal engine enriched: ict_pattern, ict_tier, ict_size_mult, ict_mtf_context (4 new columns in signal_snapshots)
- Dashboard: ICT zones card + signal display updated
- 1H zone rationale: weekly/daily zones are pre-market. Without 1H, a 1M pattern in a bullish 1H structure incorrectly gets LOW context. 1H refreshes hourly during session.

**Open after session:**
- C-07b: Pre-open capture gap still open (supervisor starts 09:14)
- R-04: Dynamic exit v2 — deferred to Phase 4 execution layer
- Shadow gate: 8/10 — sessions 9+10 Monday/Tuesday
- Phase 4 decision: after session 10
- Rerun Exp 5, 8, 10c, portfolio sims on full year data (expiry fix now applied)
- Monday pre-market: `python build_ict_htf_zones.py --timeframe D`

**Files changed:** merdian_utils.py (NEW), patch_expiry_fix.py (NEW), experiment_14_session_pyramid.py (NEW), experiment_14b_session_pyramid_v2.py (NEW), detect_ict_patterns.py (NEW), build_ict_htf_zones.py (NEW), detect_ict_patterns_runner.py (NEW), patch_runner_ict.py (NEW), patch_signal_ict.py (NEW), patch_dashboard_ict.py (NEW), build_trade_signal_local.py (6 changes), run_option_snapshot_intraday_runner.py (ICT step wired), merdian_live_dashboard.py (ICT zones card), run_validation_analysis.py (replay engine updated)

**Schema changes:** ict_zones (NEW — 28 cols), ict_htf_zones (NEW — 16 cols), signal_snapshots (+ict_pattern, +ict_tier, +ict_size_mult, +ict_mtf_context)

**Open items closed:** ENH-31 (expiry calendar), ENH-35 (validation), S-05 (signal accuracy), S-06 (expiry bug), C-09 (power hour noise), R-01 (VIX gate), R-02 (sequence filter), R-03 (gamma gate), R-08 (session pyramid)

**Open items added:** none new

**Git commit hash:** 26c5e72 (Local + AWS)

**Next session goal:** Shadow sessions 9+10 results → Phase 4 promotion decision. If approved: wire ict_size_mult to order quantity (ENH-38), scope ENH-42 WebSocket.

**docs_updated:** yes

---

## 2026-04-10 / 2026-04-11 — research / architecture — ICT Research Series Complete + Signal Rule Book v1.0

**Goal:** Complete the full ICT pattern research series (Experiments 0–13) while monitoring live pipeline. Produce Signal Rule Book v1.0 as implementation-ready document.

**Session type:** research / architecture

**Completed:**

Pipeline (live session 2026-04-10):
- Token refresh Task Scheduler did NOT fire at 08:15 — manually triggered at 08:22 ✅
- Preflight OVERALL PASS (Local) ✅
- AWS token pulled (cron confirmed) ✅
- Supervisor start_supervisor_clean.ps1 failed due to parameter conflict (-NoNewWindow + -WindowStyle) — manually started supervisor at 08:31 ✅
- Runner lock file path mismatch (supervisor looks for runner.lock, runner uses run_option_snapshot_intraday_runner.lock) — cleared manually at 10:28 ✅
- Pipeline ran clean from 10:28 through 15:30 both symbols ✅
- BUY_PE both symbols, confidence 44, trade_allowed=False (VIX gate — but see research below)
- C-07b pre-open NOT CAPTURED (fix was deployed but pre-open runs before supervisor + runner start)
- AWS shadow: cycle OK 09:15, 11:45 — A-05 confirmed working ✅
- Shadow gate: today = session 8/10

Research series — all experiments completed:
- Experiment 0: Symmetric return distribution. Full year base rate 49.7% UP / 50.3% DOWN — essentially random. Market spent 10/12 months NEUTRAL. Only Nov 2025 BULL (55.6%) and Mar 2026 BEAR (55.3%). LOW_VOL Jul-Oct 2025 (0.0-0.2% large moves). HIGH_VOL Apr 2025 + Jan-Mar 2026 (1.5-4.2% large moves).
- Experiment 2: Options P&L — BULL_OB +70%, BEAR_OB +43%, BULL_FVG +34%, JUDAS_BULL +30%. BEAR_FVG -31%, BEAR_BREAKER -46% (never trade).
- Experiment 2b: Futures vs options — options dominate on % (leverage). Futures pyramid on OBs gives 31% of Fixed-6 reward for 12% risk (2.6× better Sharpe).
- Experiment 2c v1+v2: Pyramid entry. OBs confirm in 5 min (T2 80-93%). Judas needs 15-25 min (T2 rose from 12% to 44% with longer window but pyramid expectancy unchanged — Judas = options only).
- Experiment 5: VIX gate stress test. BEAR_OB|HIGH_IV +174.6% vs +84.8% MED_IV. ALL patterns better in HIGH_IV. VIX gate is BACKWARDS — must be removed.
- Experiment 8: Sequence detection. BEAR_OB|MOM_YES +187% (90% WR). BEAR_OB|IMP_STR -7.4% (avoid). Morning 10:00-11:30: BEAR_OB +296.6% 100% WR. BULL_OB|OPEN +3.4% 45% WR (skip).
- Experiment 9: SMDM. NEUTRAL — no structural difference expiry vs normal. Expiry sweep reversal edge lives in DTE=0 gamma, already captured by BOS_BEAR|HIGH|DTE=0.
- Experiment 10/10b/10c: ICT patterns. BULL_OB|MEDIUM +132.8% 100% WR. JUDAS_BULL|HIGH +56.6% 100% WR. MTF lift: JUDAS_BULL +42.4%, BULL_OB +25%.
- Experiment 11+12: Regime intersection. BULL_OB regime-independent (LONG_GAMMA +65.7% ≈ NO_FLIP +62.3%). JUDAS_BULL needs LONG_GAMMA. BEAR_OB|BEARISH momentum +141%.
- Experiment 12b: Repeatability by vol regime. BULL_FVG STRUCTURAL ★★★ (all 3 regimes). Others LIKELY STRUCTURAL ★★.
- Experiment 13: Signal Rule Book v1.0 — built as formatted .docx, 676 paragraphs, 8 sections. Covers pattern tiers, quality filters, execution rules, regime gate changes, portfolio simulation.

Documents produced:
- docs/research/MERDIAN_Signal_RuleBook_v1.docx — Signal Rule Book v1.0 ✅ Committed fcdf620
- docs/research/merdian_all_experiment_results.md — 677-line consolidated results reference ✅

**Open after session:**
- C-07b: Pre-open capture — supervisor/runner start after 09:08, architectural gap remains
- start_supervisor_clean.ps1: fix -NoNewWindow + -WindowStyle parameter conflict
- Runner lock file: supervisor must check run_option_snapshot_intraday_runner.lock (not runner.lock)
- Task Scheduler token refresh: investigate why 08:15 task did not fire
- R-01: Remove VIX gate from build_trade_signal_local.py — replace with IV-scaled sizing (NEW)
- R-02: Add sequence quality filter to signal engine — IMP_STR skip + MOM_YES tier sizing (NEW)
- R-03: Relax gamma regime gate for BULL_OB, BEAR_OB, BULL_FVG — keep for JUDAS_BULL only (NEW)
- R-04: Implement dynamic exit v2 in signal/execution layer (NEW)
- Shadow gate: 8/10 — 2 more clean sessions needed

**Files changed:** docs/research/MERDIAN_Signal_RuleBook_v1.docx (NEW), docs/research/merdian_all_experiment_results.md (NEW), experiment_0-13 scripts (research only, not production)
**Schema changes:** None
**Open items closed:** OI-08 (validation analysis — addressed by research series), E-05 (SMDM — research confirmed neutral, no full implementation needed)
**Open items added:** R-01 (VIX gate removal), R-02 (sequence filter), R-03 (gamma gate relax), R-04 (dynamic exit v2)
**Git commit hash:** fcdf620 (Signal Rule Book committed) | experiment results md pending commit
**Next session goal:** Commit all pending files (experiment scripts, results md, updated registers). Fix start_supervisor_clean.ps1 parameter conflict. Fix runner lock path mismatch. Investigate Task Scheduler token refresh. Continue shadow gate sessions (8/10).
**docs_updated:** yes

---

## 2026-04-09 — live_canary / code_debug — Fourth Live Session + Post-Market Fixes

**Goal:** Run fourth live session and deploy all outstanding post-market fixes.

**Session type:** live_canary / code_debug

**Completed:**

Morning startup:
- Supervisor PID 16248 still alive from April 6 — manually killed and restarted clean PID 1640 at 08:29
- Both preflights passed (Local + AWS) — token auto-refreshed at 07:54 with TOTP retry working
- Runner auto-started by supervisor at 09:15 ✅ — first time fully automatic
- AWS shadow auto-started via cron at 09:15 (PID 95553) ✅

Live session:
- NIFTY: 37,350 rows (09:18–15:27) ✅ Full session
- SENSEX: 42,000 rows (09:19–15:28) ✅ Full session
- NIFTY: BUY_PE all session, confidence 44, trade_allowed=False
- SENSEX: BUY_PE all session, confidence 48, trade_allowed=False
- VIX: 19-20 range — HIGH regime (down from 26+ PANIC on April 6)
- SENSEX: SHORT_GAMMA detected — first time observed in live session
- Breadth: LIVE — Advances 229, Declines 594, BEARISH
- Transient Supabase RemoteProtocolError at 13:17 — one partial cycle, self-healed on next cycle

Post-market fixes deployed (all 5):
1. `start_supervisor_clean.ps1` — kills old supervisor before starting new one. Task Scheduler updated to call PS1 wrapper. Root cause: Task Scheduler started new process without killing old one; old process held lock file preventing fresh starts.
2. AWS Guard 4 (LTP staleness) skipped — `equity_intraday_last` not maintained on AWS shadow. This was preventing `write_cycle_status_to_supabase()` from being called. AWS shadow block now writes status to Supabase after each cycle.
3. `merdian_live_dashboard.py` — `parse_ist_dt` made more robust to handle all Supabase timestamp formats (fixes `?` timestamps on NIFTY pipeline stages).
4. `stage2_db_contract.py` — `check_trading_calendar_week_ahead` now uses Python `trading_calendar` module instead of Supabase table count (fixes false warning — new calendar stores holidays only, not every trading day).
5. Dashboard preflight encoding — already in dashboard fix above (ASCII sanitize + PYTHONIOENCODING).

Task scheduler audit:
- All 8 remaining tasks confirmed needed
- MERDIAN_Market_Tape_1M already disabled yesterday

**Open after session:**
- C-07b: Pre-open capture gap still architectural — supervisor too late for 09:00-09:08 window
- AWS shadow cycle status: not yet verified in dashboard (will confirm tomorrow when shadow runner cycles with Guard 4 fix)
- E-35: run_validation_analysis.py — next engineering priority
- Shadow gate: 7/10 (verify exact count — April 6 was partial, April 7 was delayed)

**Files changed:** start_supervisor_clean.ps1 (new), merdian_live_dashboard.py (timestamp + encoding fix), stage2_db_contract.py (calendar check fix), run_merdian_shadow_runner.py (Guard 4 skip)
**Schema changes:** None
**Open items closed:** S-10 (supervisor lock), A-05 (AWS shadow status write), C-03 (WCB confirmed live), C-07a (AWS premarket confirmed), S-04 (no late stops confirmed), M-02 (premarket recording confirmed)
**Open items added:** E-35 (run_validation_analysis.py)
**Git commit hash:** 858de8f (Local + AWS)
**Next session goal:** Verify AWS shadow status in dashboard, fix C-07b pre-open gap, build E-35 run_validation_analysis.py
**docs_updated:** yes

---

## 2026-04-08 — live_canary / code_debug — Third Live Session

**Goal:** Run third live session. Monitor for supervisor auto-start and AWS shadow.

**Session type:** live_canary / code_debug

**Completed:**

Morning startup:
- Supervisor PID 16248 still alive from April 6 — manually killed, started clean PID 1640 at 08:29
- Both preflights passed. Dhan HTTP 500 on expiry list at first attempt — Dhan server hiccup, cleared on retry
- Token auto-refreshed with TOTP retry (Invalid TOTP on first attempt, waited 30s, succeeded)
- Runner auto-started by supervisor at 09:15 ✅
- AWS shadow auto-started via cron at 09:15 (PID 84986) ✅

Live session:
- NIFTY: 37,350 rows (09:18–15:27) ✅ Full session
- SENSEX: 42,000+ rows (09:19–15:28) ✅ Full session
- VIX dropping from 26+ to 19-20 range — market recovering
- SENSEX: SHORT_GAMMA first observed
- Breadth: LIVE, Advances 405, Declines 965, BEARISH
- Transient Supabase RemoteProtocolError at 13:17 — self-healed on next cycle

Pre-open data confirmed in Supabase:
- NIFTY 23,855 / SENSEX 77,298 at 09:08:02 IST — written by AWS cron capture_premarket_0908.py
- Dashboard showed NOT CAPTURED because it queries wrong table — C-07b root cause partially identified

**Open after session:**
- Supervisor persistent lock root cause confirmed — PID 16248 never dies, new Task Scheduler start exits finding lock occupied
- AWS shadow Guard 4 blocking Supabase status write
- Dashboard ? timestamps on NIFTY — parse_ist_dt bug
- Dashboard preflight button cp1252 — cosmetic but annoying

**Files changed:** None (observations and root cause identification only)
**Schema changes:** None
**Open items closed:** S-04 (confirmed no late stops), C-07a (confirmed AWS premarket capture working)
**Open items added:** S-10 (supervisor persistent lock root cause confirmed)
**Git commit hash:** 17ac20a (no code changes this session)
**Next session goal:** Deploy all 5 post-market fixes — supervisor PS1 wrapper, AWS Guard 4, dashboard timestamp, preflight calendar check, dashboard encoding
**docs_updated:** yes

---

## 2026-04-07 — live_canary / code_debug — Second Live Session + Operational Fixes

**Goal:** Run second live market session and resolve operational failures carried over from day 1.

**Session type:** live_canary / code_debug

**Completed:**

Morning failures (root causes and fixes):
- Supervisor did not auto-start runner — PID 16248 from yesterday had loaded old trading_calendar.py before the rewrite was deployed. Running Python process does not reload imported modules from disk. Fix: added weekly 08:00 Mon-Fri trigger to MERDIAN_Intraday_Supervisor_Start task — supervisor now restarts fresh every morning.
- AWS token 401 at 09:00 — cron at 08:25 IST pulled token before Local's Supabase sync completed. Fixed: AWS cron shifted from 08:25 (03:55 UTC) to 08:35 (03:05 UTC).
- Runner started manually at 09:32, first cycle 09:35. Session ran 09:35–15:28.

Live session:
- NIFTY: 34,452 option chain rows (09:42–15:27) ✅. BUY_PE all session, confidence 48–64, trade_allowed=False (VIX panic gate >25)
- SENSEX: 33,600 rows (09:43–15:28) ✅. BUY_PE / DO_NOTHING, confidence 28–56, trade_allowed=False
- Breadth: LIVE — Advances 387, Declines 934, BEARISH — heavily bearish day
- AWS shadow runner: auto-started via cron at 09:15 (PID 80952), ran full session ✅

Task scheduler audit:
- MERDIAN_Market_Tape_1M DISABLED — was failing every run (DhanError 401), producing no useful output, and making 390 extra Dhan API calls/day contributing to 429 rate limiting on breadth ingest
- All other 8 tasks confirmed correct and needed

**Open after session:**
- C-07b: Pre-open capture still missed — supervisor starts at 09:14, too late for 09:00-09:08 window
- Dashboard preflight button cp1252 encoding error — cosmetic only, preflight works from command line
- Shadow gate count: 6/10 (verify)
- ENH-35: run_validation_analysis.py — next build priority

**Files changed:** None (Task Scheduler and crontab changes only — no code changes)
**Schema changes:** None
**Open items closed:** OI-03 (MERDIAN_Market_Tape_1M disabled — confirmed broken and harmful)
**Open items added:** None
**Git commit hash:** 8a992ee (no code changes today)
**Next session goal:** Fix C-07b pre-open capture gap, fix dashboard preflight encoding, build ENH-35 run_validation_analysis.py
**docs_updated:** yes

---

## 2026-04-06 — live_canary / code_debug / architecture — First Live Session + Architecture Repairs

**Goal:** Run first live market session (NIFTY/SENSEX options pipeline) and repair all root-cause failures discovered during the session.

**Session type:** live_canary / code_debug / architecture

**Completed:**

Live session:
- Runner started manually at 09:26 IST after calendar and syntax fixes (first cycle 09:30)
- NIFTY: BUY_PE action=48 confidence, trade_allowed=False (VIX panic gate >25 correctly blocked)
- SENSEX: DO_NOTHING, confidence=36
- VIX: 26.41 — PANIC regime, 100th percentile, VIX_UPTREND all session
- SMDM: NIFTY squeeze_score=4, SQUEEZE pattern active
- Full pipeline completed: options → gamma → volatility → momentum → market_state → signal → options_flow → momentum_v2 → SMDM → structural_alerts → shadow_v3
- AWS shadow runner manually started 09:46 IST, ran until 15:30 IST market close

Post-market architecture repairs:
- trading_calendar.py full rewrite — rule-based. Old design required manual row per date; missing row = system failure (root cause of today's morning failure). New: weekdays open by default, weekends closed by computation, NSE holidays are the only stored exceptions. No manual date insertion ever required again.
- trading_calendar.json rebuilt — holidays-only format. 23 NSE holiday entries for 2025-2026. Old 371-line manually maintained sessions list replaced.
- merdian_live_dashboard.py full rewrite (v2) — session state computed live from calendar (never stale), token block with expiry countdown, pre-open block (09:00-09:08) with spot capture status, pipeline stages showing actual values (spot, VIX, regime, signal action), breadth block with advances/declines, AWS shadow runner block via Supabase, action buttons with inline result within 5s (no click and pray), cp1252 encoding fixed for Windows.
- refresh_dhan_token.py — added runtime/token_status.json write after every attempt. Added TOTP retry: waits 30s and retries with next TOTP window on Invalid TOTP error.
- run_merdian_shadow_runner.py — breadth ingest disabled on AWS. Both Local and AWS were hitting the same Dhan token simultaneously causing 56/56 chunks returning 429 all day. AWS shadow is read-only for breadth. Also added write_cycle_status_to_supabase() — writes cycle_ok, breadth_coverage, per_symbol status to system_config table after each cycle for dashboard consumption.
- run_option_snapshot_intraday_runner.py — CREATE_NO_WINDOW flag added to subprocess calls. Eliminates 25-30 terminal windows flashing per 5-minute cycle.
- Task Scheduler MERDIAN_Live_Dashboard — updated with PYTHONIOENCODING=utf-8.

**Open after session:**
- C-07b confirmed: pre-open capture gap — supervisor task fires at 09:14, misses 09:00-09:08 window. Architectural fix needed.
- Shadow gate count: verify 5/10 after today
- Supabase disk usage: unverified post-session (was 9.5GB pre-session)
- ENH-35: run_validation_analysis.py — next build priority
- ENH-36: hist_* to live promotion pipeline — after ENH-35

**Files changed:** trading_calendar.py (full rewrite), trading_calendar.json (full rewrite), merdian_live_dashboard.py (full rewrite v2), refresh_dhan_token.py (token_status.json + TOTP retry), run_option_snapshot_intraday_runner.py (CREATE_NO_WINDOW), run_merdian_shadow_runner.py (breadth disabled + Supabase status write)
**Schema changes:** None
**Open items closed:** Calendar root cause resolved (permanent fix)
**Open items added:** C-07b confirmed (pre-open capture gap)
**Git commit hash:** 627a1b5 (Local + AWS)
**Next session goal:** Monitor second live session tomorrow — verify token refresh automatic at 08:15, preflight from dashboard, supervisor auto-start at 09:14, pipeline green by 09:25
**docs_updated:** yes

---

## 2026-04-04 / 2026-04-05 — code_debug / infrastructure / architecture — V18C Session + Historical Backfill Sprint

**Goal:** Close all actionable open items from Groups 1–5, build historical gamma backfill pipeline, ingest vendor correction data, build live monitoring dashboard.

**Session type:** code_debug / infrastructure / architecture (extended — 2 days)

**Completed:**
- V18A-01: Token refresh race condition fixed — Local writes token to Supabase, AWS pulls at 08:25 IST
- OI-03: MERDIAN_Market_Tape_1M re-enabled
- C-04/C-05/C-06: Closed from query evidence
- S-01/S-02: Supervisor task swap — MERDIAN_Intraday_Supervisor_Start enabled, legacy launcher disabled
- S-05: Table freshness checks added to gamma_engine_telemetry_logger.py
- S-07: watchdog_check.ps1 rebuilt with trading_calendar guard and market hours gate
- S-08: MERDIAN_Scheduler_Manifest.md created in docs/
- S-03/S-06/M-01: Confirmed already built — closed
- A-04: Python 3.10 compatibility fix on AWS (datetime.UTC → timezone.utc)
- E-03: India VIX signal rules added to build_shadow_signal_v3_local.py (shadow only)
- D-09/E-06: 13 shadow table DDLs documented in docs/MERDIAN_Shadow_Tables_DDL.md
- Token refresh timing corrected to 08:15 IST per Change Protocol Rule 6
- MERDIAN_Live_Dashboard: live HTTP monitoring dashboard built (localhost:8765)
- Three new Supabase tables: hist_gamma_metrics, hist_volatility_snapshots, hist_market_state
- backfill_gamma_metrics.py: pure-Python BS IV + GEX computation from hist_option_bars_1m
- batch_backfill_gamma.py: batch wrapper — 421/514 dates passed
- batch_reconstruct_signals.py: expiry-aligned batch reconstruction wrapper
- Vendor correction files ingesting: SENSEX F+O contractwise (247 files, 19M rows)
- OpenItems Register converted from docx to markdown — v4 edition

**Open after session:**
- F+O vendor ingest running (MAY/JUN 2025, JAN 2026 SENSEX data)
- SENSEX gamma backfill for May–Jun 2025 and Jan 2026 (after ingest)
- C-03/C-07a/C-07b/S-04/A-05/M-02: require Monday live session
- Shadow gate: 4/10 sessions — needs 6 more clean live sessions
- backfill_volatility_metrics.py and backfill_market_state.py: not yet built
- Appendix V18D: required per documentation protocol

**Files changed:** merdian_live_dashboard.py (NEW), backfill_gamma_metrics.py (NEW), batch_backfill_gamma.py (NEW), batch_reconstruct_signals.py (NEW), gamma_engine_telemetry_logger.py, watchdog_check.ps1, build_shadow_signal_v3_local.py, refresh_dhan_token.py, ingest_equity_eod_local.py (AWS), docs/MERDIAN_Scheduler_Manifest.md, docs/registers/MERDIAN_OpenItems_Register_v4.md, docs/MERDIAN_Shadow_Tables_DDL.md

**Schema changes:** hist_gamma_metrics (NEW), hist_volatility_snapshots (NEW), hist_market_state (NEW), system_config row dhan_api_token (NEW)

**Open items closed:** V18A-01, OI-03, C-01, C-02, C-04, C-05, C-06, C-08, A-03, A-04, E-03, D-09/E-06, S-01–S-08, M-01, Group 3 steps 3.1–3.6, Group 4 items 4.1/4.3/4.6

**Git commit hash:** 0655599

**Next session goal:** Run SENSEX gamma backfill for vendor-corrected months. Build backfill_volatility_metrics.py. Write Appendix V18D.

**docs_updated:** yes

---

## How to Add New Entries

Copy this template and prepend to the top of this file (newest first):

```markdown
## YYYY-MM-DD — [Session type] — [Topic]

**Goal:** [one sentence]
**Session type:** code_debug / architecture / documentation / live_canary / planning

**Completed:**
  - [bullet with evidence]
  - [bullet with evidence]

**Open after session:**
  - [bullet]

**Files changed:** [comma-separated, or "none"]
**Schema changes:** [describe, or "none"]
**Open items closed:** [IDs, or "none"]
**Open items added:** [IDs, or "none"]
**Git commit hash:** [hash]
**Next session goal:** [one sentence, specific]
**docs_updated:** yes / no / na
```

---

*MERDIAN Session Log — started 2026-03-31 — append newest entry at top*
