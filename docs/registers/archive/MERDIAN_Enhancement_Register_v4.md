# MERDIAN Enhancement Register v4

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Enhancement_Register_v4.md |
| Supersedes | MERDIAN_Enhancement_Register_v3.md (2026-04-09) |
| Updated | 2026-04-11 |
| Sources | Enhancement Register v3 · Session 2026-04-11 |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document. |
| Authority | Tracks proposals, not decisions. Decisions live in master Decision Registry. |

---

## V4 Changes from V3

| Change | Detail |
|---|---|
| ENH-31 status | CLOSED — data-driven expiry fix built (merdian_utils.py) |
| ENH-35 status | COMPLETE — three validation runs; final signal universe 268 bars at 55.2% accuracy |
| ENH-37 status | COMPLETE — full 6-step build this session |
| Signal engine | Six Phase 4 prerequisite changes applied and validated |
| Shadow gate | 8/10 (sessions 9+10 Monday/Tuesday) |
| Phase 4 status | NOT YET — pending shadow sessions 9+10 |
| ENH-42 NEW | WebSocket ATM option feed (proposed — after Phase 4) |
| Experiment scripts | All 11 patched with DB-driven expiry lookup — unlocks Sep 2025–Mar 2026 |

---

## Tier 1 — Signal Validation Gate

---

### ENH-05: CONFLICT Resolution Logic

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-11 |
| Dependency | ENH-35 (done) |

ENH-35 confirmed CONFLICT is asymmetric. breadth BULLISH + momentum BEARISH → BUY_CE now trades: 58.7% SENSEX, 55.4% NIFTY at N=3,575. breadth BEARISH + momentum BULLISH → DO_NOTHING retained (47-49%, protects capital). `infer_direction_bias()` updated in `build_trade_signal_local.py`.

---

### ENH-28: Historical Data Ingest Pipeline

| Field | Detail |
|---|---|
| Status | **PRODUCTION** |

NIFTY + SENSEX 247 days Apr 2025–Mar 2026 confirmed. The apparent Aug 2025 coverage gap was a false alarm — caused by hardcoded EXPIRY_WD in experiment scripts, fixed by ENH-31.

---

### ENH-31: Expiry Calendar Utility

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-11 |

`merdian_utils.py` built: `build_expiry_index_simple()` + `nearest_expiry_db()`. Replaces hardcoded `EXPIRY_WD = {"NIFTY": 3}` which broke when NIFTY switched Thursday→Tuesday expiry in September 2025. All 11 experiment scripts patched via `patch_expiry_fix.py`. Unlocks Sep 2025–Mar 2026 option data across all experiments.

---

### ENH-35: Historical Signal Validation and Accuracy Measurement

| Field | Detail |
|---|---|
| Status | **COMPLETE** — three validation runs 2026-04-11 |

**Final signal universe after all six changes:**

| Metric | Value |
|---|---|
| NIFTY signals/year | 244 |
| NIFTY accuracy T+30m | 58.6% STRONG EDGE |
| trade_allowed=YES pool | 268 bars, 55.2% |
| SHORT_GAMMA\|BEARISH | 54.8%, N=104 |
| SHORT_GAMMA\|BULLISH | 55.5%, N=164 |
| BUY_CE\|MOM_BEARISH | 67.9%, N=661 STRONG EDGE |
| BUY_CE\|HIGH_IV | 57.5%, N=1,584 EDGE |

**Six changes applied to signal engine:**
1. CONFLICT BUY_CE now trades (SENSEX 58.7%, NIFTY 55.4% accuracy)
2. LONG_GAMMA gated to DO_NOTHING (47.7% accuracy — below random)
3. NO_FLIP gated to DO_NOTHING (45-48% accuracy — below random)
4. VIX gate removed (HIGH_IV has MORE edge — Experiment 5 confirmed)
5. Confidence threshold 60→40 (edge lives in conf_20-49 band)
6. Power hour gate — no signals after 15:00 IST (SENSEX expiry noise)

SENSEX note: 24 signals at 20.8% accuracy — all firing 15:04-15:28 (expiry unwinding). Power hour gate eliminates this noise source.

---

### ENH-36: hist_* to Live Table Promotion Pipeline

| Field | Detail |
|---|---|
| Status | NOT BUILT |
| Dependency | ENH-35 (done) |

Deferred — ENH-35 confirmed signal engine changes more impactful than data promotion for Phase 4.

---

### ENH-37: ICT Pattern Detection Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-11 |
| Git commit | 26c5e72 |

**Three-level zone hierarchy:**

| Timeframe | Context | Significance |
|---|---|---|
| Weekly (W) | VERY_HIGH | Multi-session, institutionally proven |
| Daily (D) | HIGH | Session-proven, pre-market |
| 1-Hourly (H) | MEDIUM | Nascent, same-session |
| None | LOW | No confluence |

**Files built:**

| File | Purpose |
|---|---|
| `ict_zones_ddl.sql` | DDL — ict_zones (28 cols) + ict_htf_zones (16 cols) |
| `detect_ict_patterns.py` | ICTDetector class, tier/MTF/breach detection |
| `build_ict_htf_zones.py` | W/D/H zone builder — 39 zones on first run |
| `detect_ict_patterns_runner.py` | Runner integration — every 5-min cycle |
| `patch_runner_ict.py` | Wired ICT step into runner |
| `patch_signal_ict.py` | Wired ICT enrichment into signal engine |
| `patch_dashboard_ict.py` + `patch_dashboard_ict_step4.py` | ICT zones card in dashboard |

**4 new signal fields:** `ict_pattern`, `ict_tier`, `ict_size_mult`, `ict_mtf_context`

**Runner pipeline (post-wiring):**
```
ingest → archive → gamma → volatility → momentum → market_state →
detect_ict_patterns_runner [NEW, non-blocking] →
build_trade_signal → options_flow → momentum_v2 → smdm → shadow_signal
```

**Zone schedule:**
- Weekly: Sunday night
- Daily: pre-market 08:45 IST
- 1H: top of each hour during session (from runner)
- Intraday detection: every 5-min cycle

---

### ENH-38: IV-Scaled Position Sizing

| Field | Detail |
|---|---|
| Status | PARTIAL — multiplier logic in ENH-37 ICT tier assignment |

LOW_IV (<12%) = 0.5x, MED_IV = 1.0x, HIGH_IV (>18%) = 1.5x. Needs wiring to execution layer (Phase 4).

---

### ENH-42: WebSocket ATM Option Feed

| Field | Detail |
|---|---|
| Status | PROPOSED |
| Dependency | Phase 4 live |

Replaces failed MERDIAN_Market_Tape_1M with Dhan WebSocket. Tick-by-tick ATM ± 5 strikes. Enables real-time zone breach detection and session pyramid entries (Experiment 14b concept — deferred pending live infrastructure). Build after Phase 4 stable.

---

## Tier 2 — After Phase 4

### ENH-09: Heston Calibration Layer

| Status | PROPOSED |
|---|---|
| Dependency | ENH-33 (done) + Phase 4 gate |

*(Unchanged from v3)*

### ENH-10 through ENH-21 — all depend on ENH-09

*(Unchanged from v3)*

---

## Tier 3 and 4

*(Unchanged from v3)*

---

## Summary Table

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-05 | CONFLICT resolution logic | 1 | **COMPLETE** |
| ENH-07 | Basis-implied risk-free rate | 1 | IN PROGRESS |
| ENH-28 | Historical data ingest | 1 | **PRODUCTION** |
| ENH-29 | Signal premium outcome measurement | 1 | PIVOTED |
| ENH-30 | SMDM infrastructure | 1 | PARTIAL |
| ENH-31 | Expiry calendar utility | 1 | **COMPLETE** |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED |
| ENH-33 | Pure-Python BS IV engine | 1 | **PRODUCTION** |
| ENH-34 | Live monitoring dashboard | 1 | **PRODUCTION** |
| ENH-35 | Historical signal validation | 1 | **COMPLETE** |
| ENH-36 | hist_* to live promotion | 1 | NOT BUILT |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | IV-scaled position sizing | 1 | PARTIAL |
| ENH-42 | WebSocket ATM option feed | 1 | PROPOSED |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10–21 | (depend on ENH-09) | 2 | PROPOSED |
| ENH-22–25 | (Tier 3) | 3 | PROPOSED |
| ENH-26–27 | (Quantum — Tier 4) | 4 | PROPOSED |
