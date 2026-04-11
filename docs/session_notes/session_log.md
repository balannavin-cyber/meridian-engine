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
