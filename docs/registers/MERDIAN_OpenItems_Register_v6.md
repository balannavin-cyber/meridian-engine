# MERDIAN — Master Open Items & Enhancement Status Register v6

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Edition | v6 — 2026-04-11 |
| Supersedes | v5 (2026-04-09) |
| Source documents | v5 · Session 2026-04-11 |
| Git range | 858de8f → 26c5e72 |

---

## Session 2026-04-11 Changes

**Completed this session:** ENH-31 (expiry fix), ENH-35 (three validation runs, 55.2% accuracy confirmed), ENH-37 (full ICT layer — 6 steps), six signal engine changes applied and validated, Experiments 14+14b closed (session pyramid deferred), expiry bug fixed across all experiment scripts.

**Shadow gate:** 8/10. Sessions 9+10 Monday/Tuesday.

**Git:** 858de8f → 26c5e72

---

## Section 1 — Critical Fixes

### C-01 through C-07a — ALL CLOSED (see v5)

### C-07b — Pre-open capture gap
**Status:** OPEN. Supervisor starts 09:14, pre-open window is 09:00-09:08. Dashboard shows NOT CAPTURED daily. Fix: dedicated pre-open cron before 09:00.

### C-08 — Intermittent SENSEX volatility RuntimeError
**Status:** OPEN — occasional, non-blocking.

### C-09 — SENSEX SHORT_GAMMA power hour noise
**Status:** CLOSED 2026-04-11. All 24 SENSEX signals fired 15:04-15:28 at 20.8% accuracy. Power hour gate added: no signals after 15:00 IST for both symbols.

---

## Section 2 — Signal Engine

### S-01 through S-04 — ALL CLOSED (see v5)

### S-05 — Signal engine below-random accuracy
**Status:** CLOSED 2026-04-11. ENH-35 identified root causes. Six changes applied and validated. NIFTY 58.6% accuracy, 244 signals/year, trade_allowed=YES pool 55.2% at N=268.

Changes:
1. CONFLICT BUY_CE now trades (58.7%/55.4% accuracy)
2. LONG_GAMMA gated to DO_NOTHING (47.7% — below random)
3. NO_FLIP gated to DO_NOTHING (45-48% — below random)
4. VIX gate removed (HIGH_IV has more edge — Experiment 5)
5. Confidence threshold 60→40 (edge lives in conf_20-49)
6. Power hour gate — no signals after 15:00 IST

### S-06 — Expiry bug in experiment scripts
**Status:** CLOSED 2026-04-11. NIFTY switched Thu→Tue expiry Sep 2025. Hardcoded EXPIRY_WD caused all post-Aug sessions to be skipped. Fixed via merdian_utils.py + patch_expiry_fix.py across 11 scripts.

---

## Section 3 — Research Items

### R-01 — VIX gate — CLOSED (removed, HIGH_IV has more edge)
### R-02 — Sequence quality filter — CLOSED (ENH-37 ICT tier assignment)
### R-03 — Gamma gate — CLOSED (LONG_GAMMA + NO_FLIP both gated)
### R-05, R-06, R-07 — ALL CLOSED (V18E)

### R-04 — Dynamic exit v2
**Status:** OPEN — deferred to Phase 4. Portfolio simulation v2 confirmed +6% improvement on NIFTY. Needs execution layer.

### R-08 — Session pyramid (Experiments 14 + 14b)
**Status:** CLOSED 2026-04-11 — concept deferred.

All 9 qualifying sessions were BEARISH. Results: Pyramid -₹4,558 (22% WR) vs single T+30m exit +₹8,329 (100% WR). v2 confirmed reversal entry improved v1 by ₹3,133 but still -₹12,645 vs single trade. Deferred pending WebSocket (ENH-42) + bullish session data + Jan-Mar 2026 HIGH_VOL rerun.

---

## Section 4 — ENH-37 Operational Notes

### Zone Schedule
| Job | When | Command |
|---|---|---|
| Weekly zones | Sunday night | `python build_ict_htf_zones.py --timeframe W` |
| Daily zones | Pre-market 08:45 | `python build_ict_htf_zones.py --timeframe D` |
| 1H zones | Hourly in session | Automatic from runner |
| Intraday detection | Every 5-min cycle | Automatic from runner |

### Monday/Tuesday — What to Watch
- ICT zones card in dashboard populating during session
- Signal stage showing `ICT:BEAR_OB(TIER1)[HIGH]x1.5` when pattern fires
- ict_pattern, ict_tier, ict_mtf_context fields in signal_snapshots
- Zone breach transitions (ACTIVE → BROKEN)
- ICT step is non-blocking — runner continues if it fails

---

## Section 5 — Phase 4 Checklist

| Gate | Status |
|---|---|
| Shadow 8/10 | DONE |
| ENH-35 accuracy validated | DONE — 55.2% at N=268 |
| CONFLICT fix | DONE |
| LONG_GAMMA gate | DONE |
| NO_FLIP gate | DONE |
| Power hour gate | DONE |
| ENH-37 ICT layer | DONE |
| Session 9 shadow (Monday) | PENDING |
| Session 10 shadow (Tuesday) | PENDING |
| Phase 4 decision | AFTER session 10 |

---

## Open Items Summary

| ID | Description | Priority | Status |
|---|---|---|---|
| C-07b | Pre-open capture gap | HIGH | OPEN |
| C-08 | SENSEX volatility RuntimeError | MED | OPEN |
| R-04 | Dynamic exit v2 | HIGH | Phase 4 |
| R-08 | Session pyramid | LOW | Post-ENH-42 |
| Phase 4 | Shadow sessions 9+10 | CRITICAL | Mon/Tue |
