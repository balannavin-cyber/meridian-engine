## 2026-04-21 — engineering / operations — Session 3+4: ENH-72 propagation (9 of 9) + backfill + ICT rebuild + Task Scheduler repair + ICT pipeline cleanup

**Goal:** Complete ENH-72 (ExecutionLog write-contract) propagation to all 9 critical pipeline scripts. In parallel: backfill missing spot bars (04-16/17/20), rebuild ICT HTF zones, regenerate Pine Script, fix MERDIAN_Dhan_Token_Refresh task config, diagnose dashboard "NOT CAPTURED" false negative. Late-session pivot: close three high-value bug fixes surfaced by working ExecutionLog instrumentation (OI-24 ICT schema mismatch, OI-26 broken expiry lookup, OI-27 1H zones never triggering).

**Session type:** engineering / operations

**Completed:**

ENH-72 ExecutionLog propagation (9 of 9 targets — programme COMPLETE):
- Target 1: ingest_option_chain_local.py — commit 3a22735 (Session 2 carry-over)
- Target 2: compute_gamma_metrics_local.py — commit d676a73 + set_symbol() helper
- Target 3: compute_volatility_metrics_local.py — commit 2173002
- Target 4: build_momentum_features_local.py — commit 74e15a0
- Target 5: build_market_state_snapshot_local.py — commit 70df409
- Target 6: build_trade_signal_local.py — commit b3d88fa (signal engine, ict_failed/enh06_failed flags, action in notes)
- Target 7: compute_options_flow_local.py — commit 1e75a74 (no-arg batch, floor=1 for partial success)
- Target 8: ingest_breadth_intraday_local.py — commit dd66076 (4-layer guard preserved, CalendarSkip→HOLIDAY_GATE)
- Target 9: detect_ict_patterns_runner.py — commit f121fca (floor=0, non-blocking exit 0 preserved, schema bugfix)
- Live production validation across targets 1-5 during 2026-04-21 trading day: 1,871 invocations, 5 failures, ~99.7% clean rate

Phase 1 — hist_spot_bars_1m backfill (2026-04-21 ~17:28 IST):
- Identified: 04-20 had 260 garbage rows with shifted timestamps (11:09-20:38 IST); 04-16/17 missing entirely
- Deleted 520 bad rows for 04-20
- Recovered backfill_spot_zerodha.py from Local via scp to MeridianAlpha (file wiped by failed nano edit, recovered via sed)
- Ran Kite backfill: 2,250 rows written (3 dates × 2 symbols × 375 bars), all 09:15-15:29 IST

Phase 2 — ICT HTF zone rebuild + Pine Script regeneration (~17:34 IST):
- build_ict_htf_zones.py processed 249 daily bars per symbol (full year)
- 35 zones written, 10 active per symbol after expiry filter
- NIFTY: D PDH 24,470, D PDL 24,311+24,231, fresh W BULL_FVG 24,074-24,241 (Apr 17)
- SENSEX: D PDH 78,944, D PDL 78,364+78,193, fresh W BULL_FVG 77,636-78,203 (Apr 17)
- Pine Script regenerated with updated zones and flip-to-support annotations

Phase 3 — Task Scheduler repair + dashboard diagnosis (~18:00 IST):
- MERDIAN_Dhan_Token_Refresh task config fix: Set-ScheduledTask with absolute Python path + WorkingDirectory
- Manual trigger verified 18:03:58 LastTaskResult=0; interactive refresh at 18:10 confirmed new token
- MERDIAN_PreOpen task config verified correct; task fires at 09:05 with exit 0
- Dashboard "NOT CAPTURED" diagnosed as false negative: capture_spot_1m.py writes data correctly but does NOT set is_pre_market=true flag; dashboard filters on that flag

Late-session fixes (ENH-72 instrumentation surfaced these hidden bugs):
- OI-24 CLOSED: detect_ict_patterns_runner.py load_atm_iv() was reading non-existent market_state_snapshots.market_state column. Original sys.exit(0) tail block had been silently masking this in production. Fixed to read volatility_features.atm_iv_avg directly. Commit f121fca (in the Target 9 ENH-72 commit).
- OI-26 CLOSED: merdian_utils.build_expiry_index_simple had hardcoded sample_dates [2025-04..2026-03]. On 2026-04-21 it returned stale historical expiries; nearest_expiry_db fell through to expiry_index[-1] producing SENSEX dte=-54d and NIFTY dte=252d. Replaced with get_nearest_expiry(sb, symbol) reading option_chain_snapshots.expiry_date (authoritative Dhan-sourced value, includes NSE holiday-driven shifts). Old functions kept DEPRECATED for audit trail. ENH-63 expiry index cache retired. Commit 49c5e3c.
- OI-27 CLOSED: ict_htf_zones had ZERO rows with timeframe='H' in its entire history. Two independent bugs: (a) is_hour_boundary() gated on minute<3, production runner cycles never landed in that window, (b) `if __name__ == "__main__": main()` positioned mid-file in build_ict_htf_zones.py before detect_1h_zones was defined, crashing CLI --timeframe H. Fix (a): replaced with data-driven should_rebuild_1h_zones(sb, symbol) — checks ict_htf_zones directly, rebuilds once per hour per symbol regardless of cycle schedule. Fix (b): moved __main__ block to end of file. Smoke confirmed 4 1H zones now visible in ict_htf_zones (first time ever). Commit d15c494.

Diagnosed but not fixed:
- OI-25: NIFTY atm_iv=2.5% observed. Investigation traced to BS-solver IV degeneracy on expiry day (NIFTY expired today 2026-04-21 at Tuesday close, last 10 min pricing near-zero extrinsic value → tiny computed IV). NOT a unit mismatch. Pipeline propagates the Dhan-returned raw IV correctly through every stage. V19 §15:00 IST session-time gate in build_trade_signal already prevents any trade decision based on these degenerate values. Cosmetic issue in Kelly lot display on expiry-day afternoons, no production impact.

**Open after session:**
  - Tomorrow: live validation of instrumented scripts (targets 6-9) + 1H zone writing (should fire at 10:00+ IST) + nearest_expiry_db replacement
  - Session 5 (ENH-74): live config rebuild — NOT STARTED
  - Session 6 (ENH-67/69/73): dashboard + alerts — requires C-08 already resolved
  - Documentation debt:
    - V18I appendix (Session 2 ENH-66/68/71)
    - V18J appendix (Session 3 ENH-72 targets 1-5)
    - V18K appendix (Session 4 targets 6-9 + OI-24/26/27 fixes + Phase 1/2/3 ops)
    - Enhancement Register v8 overhaul (v7 on disk stops at ENH-59; missing ENH-60 through ENH-74+)

**Files changed (core/):**
  - compute_gamma_metrics_local.py, compute_volatility_metrics_local.py (Session 3 targets 2-3)
  - build_momentum_features_local.py, build_market_state_snapshot_local.py (targets 4-5)
  - build_trade_signal_local.py, compute_options_flow_local.py (Session 4 targets 6-7)
  - ingest_breadth_intraday_local.py (target 8)
  - detect_ict_patterns_runner.py (target 9 ENH-72 + OI-24 schema fix + OI-26 expiry swap + OI-27 hour trigger)
  - build_ict_htf_zones.py (OI-27 CLI __main__ position fix)
  - merdian_utils.py (OI-26 new get_nearest_expiry function, deprecation markers on old expiry index functions)
  - core/execution_log.py (set_symbol helper added, Session 3)
  - backfill_spot_zerodha.py on MeridianAlpha (BACKFILL_DATES updated)

**Schema changes:** none

**Open items closed (6):**
  - OI-16 CLOSED — MERDIAN_Dhan_Token_Refresh task config fixed via Set-ScheduledTask with absolute paths
  - OI-17 CLOSED — hist_spot_bars_1m 04-16/17/20 backfilled (2,250 rows)
  - OI-24 CLOSED — detect_ict_patterns_runner load_atm_iv schema bug (fixed in commit f121fca)
  - OI-26 CLOSED — nearest_expiry_db broken DTE, replaced by get_nearest_expiry reading option_chain_snapshots (commit 49c5e3c)
  - OI-27 CLOSED — 1H zone detection never triggered, data-driven rebuild + CLI __main__ fix (commit d15c494)

**Open items added / diagnosed (5 remain):**
  - OI-18 — capture_spot_1m.py does not set is_pre_market=true flag for pre-open bars
  - OI-19 DEFERRED — MeridianAlpha pending kernel reboot, non-urgent
  - OI-20 COSMETIC — UTF-8 BOM prefix in Session 3+4 commits
  - OI-21 — refresh_dhan_token.py silent fail when invoked via Task Scheduler
  - OI-22 — Telegram alert wording misleading for transient Dhan timeouts
  - OI-23 — MERDIAN_SIGNAL_V4 docstring/code drift
  - OI-25 DIAGNOSED (not a bug) — NIFTY atm_iv=2.5% is expiry-day BS-solver IV degeneracy, gated downstream by V19 §15:00 session cutoff

**Git commit hashes (Session 3+4 full chain):** 3a22735 → d676a73 → 2173002 → 74e15a0 → 70df409 → b3d88fa → 1e75a74 → dd66076 → f121fca → 49c5e3c → d15c494

**Next session goal:** Tomorrow morning validation window 09:15-11:00 IST. Verify: (a) all 9 instrumented scripts produce SUCCESS rows in first live cycle, (b) 1H zones fire at ~10:00 IST boundary (first hourly rebuild), (c) Kelly lots sizing shows realistic counts for SENSEX (NIFTY will cycle back to real IV once new weekly is current). Then either begin Session 5 (ENH-74 live config) or start documentation debt closeout (V18J/V18K appendices + Enhancement Register v8).

**docs_updated:** yes (this entry + enhancement_register_delta_20260421.md)

---
