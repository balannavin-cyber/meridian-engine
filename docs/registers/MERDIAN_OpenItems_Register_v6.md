# MERDIAN — Master Open Items & Enhancement Status Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v6 — Research-Series-Updated — April 2026 |
| Source documents | Open Items Register v5 · ICT Research Series (Experiments 0–13) · 2026-04-10/11 session |
| Current latest appendix | V18E (2026-04-06 through 2026-04-09) — Appendix for 2026-04-10/11 pending |
| Authority | This document aggregates and does not supersede any master. |

---

### v6 Session Changes (2026-04-10/11)

**Research completed:** ICT research series Experiments 0–13. Signal Rule Book v1.0 produced (docs/research/MERDIAN_Signal_RuleBook_v1.docx, committed fcdf620).

**New open items added:** R-01 (VIX gate removal), R-02 (sequence filter), R-03 (gamma gate relax), R-04 (dynamic exit v2), R-05 (start_supervisor_clean.ps1 fix), R-06 (runner lock path fix), R-07 (Task Scheduler token investigation).

**Closed:** OI-08 (validation analysis — research series addressed this via Experiments 2/10/11/12b), E-05 (SMDM — Experiment 9 confirmed neutral, no full implementation needed).

**Shadow gate:** 8/10 sessions complete (Apr 10 counted).

**Git:** fcdf620 (Signal Rule Book committed). Experiment scripts + register updates pending next commit.

---

## Section 1 — Critical Fixes

### C-01 — market_state_snapshots duplication
**Status:** ✅ CLOSED (V18A)

### C-02 — Re-ingest 2026-03-24 EOD data
**Status:** ✅ CLOSED (V18A)

### C-03 — SENSEX WCB staleness
**Status:** ✅ CLOSED (V18D)

### C-04 — Breadth staleness
**Status:** ✅ CLOSED (V18C)

### C-05 — build_trade_signal_local.py 240-sec timeout
**Status:** ✅ CLOSED (V18A)

### C-06 — EOD coverage gap 13–24 March
**Status:** ✅ CLOSED (V18C)

### C-07a — AWS premarket timestamp/query mismatch
**Status:** ✅ CLOSED (V18D)

### C-07b — Pre-open capture gap (09:00–09:08 window)
**Status:** ⏳ OPEN — architectural gap confirmed (V18D)
Supervisor starts at 09:14 — too late for 09:00-09:08 window. capture_premarket_0908.py fix deployed on AWS (C-07b fix, commit fbf5e87) but not tested in production yet. Dashboard shows NOT CAPTURED every day.
**Fix required:** Dedicated pre-open cron or supervisor pre-session hook before 09:00.

### C-08 — Intermittent SENSEX volatility RuntimeError
**Status:** ✅ CLOSED (V18A)

---

## Section 2 — Local Production Hardening

### S-01 through S-12
**Status:** All ✅ CLOSED — see Register v5 for details.

---

## Section 3 — V18A Open Items

### V18A-01 through V18A-03
**Status:** All ✅ CLOSED — see Register v5 for details.

---

## Section 4 — AWS Readiness

### A-01 through A-06
**Status:** All ✅ CLOSED — see Register v5 for details.

---

## Section 5 — Open Items Register (OI series)

### OI-01 through OI-04, OI-06
**Status:** All ✅ CLOSED — see Register v5 for details.

### OI-05 — ENH-31 expiry calendar utility
**Status:** ⏳ OPEN (medium priority)

### OI-07 — Supabase disk monitoring
**Status:** ⏳ MONITOR — was 9.5GB before vendor correction ingest.

### OI-08 — Historical backfill validation analysis
**Status:** ✅ SUBSTANTIALLY ADDRESSED (2026-04-10/11)
The ICT research series (Experiments 0–13) measured signal quality against hist_spot_bars_1m and hist_option_bars_1m across Apr 2025–Mar 2026. Directional accuracy, option P&L expectancy, and win rates computed for all pattern × regime combinations. Signal Rule Book v1.0 produced as the output. run_validation_analysis.py as originally scoped (regime-based accuracy matrix) is still worth building for automated ongoing measurement — defer as ENH-35 (see Section 6).

### OI-09 — Minor master increment V18.1 or V19
**Status:** ⏳ OPEN — triggered by V18D scope + research series completion. Build after shadow gate confirmed (10/10).

---

## Section 5b — Research-Derived Implementation Items (R series — NEW)

### R-01 — Remove VIX Gate, Replace with IV-Scaled Sizing
**Status:** ⏳ OPEN — HIGH PRIORITY
**Source:** Experiment 5 — VIX gate proven backwards.
**Evidence:** BEAR_OB|HIGH_IV +174.6% vs BEAR_OB|MED_IV +84.8%. ALL patterns better in HIGH_IV.
**Fix:** In `build_trade_signal_local.py`:
1. Remove `trade_allowed=False when VIX>20`
2. Read `atm_iv` from most recent `hist_market_state` row at signal time
3. Apply lot multiplier: atm_iv<12% = 0.5×, 12-18% = 1.0×, >18% = 1.5×
4. JUDAS_BULL exception: always 1.0×
**Blocks:** All live sessions currently misfire (gate blocking HIGH_IV trades)

### R-02 — Add Sequence Quality Filter to Signal Engine
**Status:** ⏳ OPEN — HIGH PRIORITY
**Source:** Experiment 8 — pre-pattern sequence detection.
**Evidence:** BEAR_OB|IMP_STR = -7.4% (skip). BEAR_OB|MOM_YES = +187% vs +59%. BULL_OB|OPEN = +3.4% (skip).
**Fix:** For each detected OB, compute before signal emission:
- IMP_STR = sum(|return|) of 3 preceding 1-min bars ≥ 0.30% → skip trade
- MOM_YES = ≥2 of 3 preceding bars counter-direction → 1.5× Tier 1 sizing
- Time zone check: OPEN session (09:15-10:00) BULL_OB → 0.5× or skip
**Dependency:** ENH-37 (ICT pattern detection) must exist first.

### R-03 — Relax Gamma Regime Gate for OBs and FVG
**Status:** ⏳ OPEN
**Source:** Experiments 11A, 11B.
**Evidence:** BULL_OB works equally in LONG_GAMMA (+65.7%) and NO_FLIP (+62.3%). JUDAS_BULL needs LONG_GAMMA (+24.1% vs -5.2% NO_FLIP).
**Fix:** In signal engine:
- Remove `gamma_regime = LONG_GAMMA` gate for BULL_OB, BEAR_OB, BULL_FVG
- Keep gate for JUDAS_BULL only
- Remove `breadth_regime = BEARISH` gate for OBs (works in all breadth)
- Keep breadth gate for JUDAS_BULL (BEARISH breadth +47.6%, 100% WR)

### R-04 — Implement Dynamic Exit v2
**Status:** ⏳ OPEN
**Source:** Portfolio simulation v2 (2026-04-10/11).
**Evidence:** v1 +49% → v2 +55% NIFTY Fixed. Half-exit adds ~INR 15-20k on trending days.
**Fix:** At T+30m evaluation:
- If P&L < 0: exit all lots
- If P&L ≥ 50% gain: exit half, hold rest to T+60m
- If P&L 0-50%: hold to T+60m
- At T+60m: exit unconditionally
**Note:** This applies to options execution layer, not signal engine itself.

### R-05 — Fix start_supervisor_clean.ps1 Parameter Conflict
**Status:** ⏳ OPEN — OPERATIONAL (causes daily manual intervention)
**Source:** 2026-04-10 morning startup failure.
**Issue:** `-NoNewWindow` and `-WindowStyle` parameters cannot be used simultaneously in `Start-Process`. Script says "Supervisor launched" but fails silently.
**Fix:** Remove `-WindowStyle Hidden` from Start-Process call. Keep `-NoNewWindow` only.

### R-06 — Fix Runner Lock File Path Mismatch
**Status:** ⏳ OPEN — OPERATIONAL
**Source:** 2026-04-10 runner startup failure.
**Issue:** Supervisor checks for `runner.lock` but runner writes `run_option_snapshot_intraday_runner.lock`. Supervisor sees no lock, spawns new runner. New runner finds PID from prior run, exits.
**Fix:** Align lock file name in supervisor health check to match `run_option_snapshot_intraday_runner.lock`.

### R-07 — Investigate Task Scheduler Token Refresh Failure
**Status:** ⏳ OPEN — OPERATIONAL
**Source:** 2026-04-10 — token refresh Task Scheduler did not fire at 08:15.
**Issue:** `MERDIAN_Dhan_Token_Refresh` did not execute at 08:15 on 2026-04-10. Token was from 2026-04-09 08:06. Manual refresh required at 08:22 (token close to 24h expiry).
**Fix:** Check Task Scheduler history for task failure reason. Verify trigger configuration. Consider adding Telegram alert if token age > 23h at 08:20 IST.

---

## Section 6 — Enhancement Plan

### E-01 — Signal regret log
**Status:** ✅ CLOSED (V18A)

### E-02 — Three-zone gamma model
**Status:** ⏳ SHADOW LIVE (V18A)

### E-03 — India VIX signal rules
**Status:** ✅ CLOSED (V18C)

### E-05 — SMDM full live implementation
**Status:** ✅ CLOSED (research) — 2026-04-11
Experiment 9 confirmed SMDM is NEUTRAL — no structural difference between expiry and normal day sweep reversals at spot level. Expiry day edge already captured by BOS_BEAR|HIGH|DTE=0 pattern (+70.2%). No full SMDM implementation required. `structural_alerts` table and squeeze_score logic retained as defensive signals only.

### E-06 — Shadow eval/replay/reconstruction DDLs
**Status:** ✅ CLOSED (V18C)

### E-07 — Multi-session shadow accumulation
**Status:** ⏳ IN PROGRESS — 8/10 sessions complete
Sessions: Apr 1, 2, 6, 7, 8, 9, 10 + pre-V18D sessions. Gate opens after 2 more clean sessions.

### E-08 — Walk-forward validation
**Status:** ✅ SUBSTANTIALLY ADDRESSED (V18D + research series)
Research series (Experiments 0–13) provides comprehensive historical validation across all pattern × regime combinations against full year of hist data.

---

## Section 7 — Shadow Runner Integration

### Step 3e — Shadow gate counting
**Status:** ⏳ IN PROGRESS — 8/10 sessions complete. Gate opens ~2 more sessions.

---

## Section 8 — Signal Quality (Group 5)

### Phase 4 — Promote to live
**Status:** ⏳ BLOCKED — shadow gate 8/10. ~2 more sessions needed.

### ICT Signal Layer — NEW
**Status:** ⏳ DESIGN COMPLETE — implementation pending
Signal Rule Book v1.0 defines all rules. ENH-37 through ENH-41 are the implementation items. Sequence: R-05/R-06/R-07 (operational fixes first) → R-01 (VIX gate) → R-03 (gamma gate) → ENH-37 (ICT patterns) → R-02 (sequence filter) → R-04 (dynamic exit).

---

## Section 9 — Operational Standing Rules (unchanged)

| Principle | Rule |
|---|---|
| DB over Logs | Supabase DB query is canonical truth. |
| Measure → Validate → Shadow → Promote | No live file change until evidence collected. |
| Protected Files | build_momentum_features_local.py, compute_gamma_metrics_local.py, build_market_state_snapshot_local.py, build_trade_signal_local.py — Phase 4 gates only. |
| trading_calendar is execution control plane | Missing row = hard skip. |
| Full file replacement only | When promoting shadow to live. |
| Threshold governance | No confidence threshold changes until 30+ DO_NOTHING sessions in signal_regret_log. |
| run_id not symbol | compute_gamma/volatility scripts receive run_id UUID. |
| Shadow accumulation gate | Manual-only runs do not count. |
| Token refresh cadence | 08:15 IST Local → 08:35 IST AWS pull → 08:45 IST Preflight |
| No AWS direct edits | Rule 1 of Change Protocol. |
| Separate hist tables | hist_* tables are backfill-only. Live tables are Dhan-only. |
| ICT signal gate | ENH-37 shadow validation required before live promotion of ICT patterns. |

---

## Section 10 — What Is Working — Stable Foundation

*(All items from v5 still valid — no regressions)*

- Spot ingestion (1-min): NIFTY + SENSEX, auto-archived ✅
- Options chain ingestion: per-symbol run_id, idempotent archive ✅
- Gamma metrics: NO_FLIP state valid, gamma_zone active ✅
- Volatility snapshots: 34-field VIX enrichment ✅
- WCB (NIFTY + SENSEX): per-symbol loop ✅
- Momentum engine: all 8 fields live including ret_session ✅
- Signal engine: confidence decomposed, flip_distance_pct canonical ✅
- signal_regret_log: 614+ rows, outcome clock running ✅
- TOTP token refresh: Supabase sync architecture confirmed ✅
- Runner supervisor: crash-restart, calendar-aware ✅
- Alert daemon: HEARTBEAT_STALE/MISSING/BASE_WARN operational ✅
- Live dashboard: localhost:8765, auto-refresh 30s, action buttons ✅
- Preflight harness: 4-stage, symmetric Local + AWS ✅
- Historical backfill: hist_gamma_metrics + hist_volatility + hist_market_state ✅
- BS IV solver: pure-Python, validated ✅
- GitHub: repo operational, Local + AWS in sync at fcdf620 ✅
- trading_calendar: rule-based rewrite, no manual entries required ✅
- Shadow gate: 8/10 sessions ✅
- Signal Rule Book v1.0: research complete, implementation backlog defined ✅ **NEW**

---

*MERDIAN Open Items Register v6 — Research-Series-Updated — 2026-04-11*
*Supersedes v5. Next update: after next engineering session (fix R-05/R-06/R-07, commit all pending files).*
