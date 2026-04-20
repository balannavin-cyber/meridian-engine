# MERDIAN Enhancement Register v6

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Enhancement_Register_v6.md |
| Supersedes | MERDIAN_Enhancement_Register_v5.md (2026-04-12) |
| Updated | 2026-04-13 |
| Sources | Enhancement Register v5 · Session 2026-04-13 |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document. |
| Authority | Tracks proposals, not decisions. Decisions live in master Decision Registry. |
| Update rule | Update in the same session that produces new architectural thinking. Commit immediately. |

---

## v6 Changes from v5

| Change | Detail |
|---|---|
| ENH-38 status | **COMPLETE** — Kelly sizing live end-to-end: runner → ict_zones → signal_snapshots |
| ENH-39 status | **COMPLETE** — Capital ceiling enforced in merdian_utils.effective_sizing_capital() |
| ENH-40 status | **COMPLETE** — Signal Rule Book v1.1 written (docs/research/MERDIAN_Signal_RuleBook_v1.1.md) |
| ENH-41 status | **DOCUMENTED** — Rule in Signal Rule Book v1.1 Section 2.2. Code pending execution layer. |
| ENH-43 NEW | Signal dashboard — merdian_signal_dashboard.py, port 8766 |
| ENH-44 NEW | Capital management — set_capital.py + dashboard SET input |
| ENH-45 NEW | hist_spot_bars_1m Zerodha backfill — Apr 7–10 via backfill_spot_zerodha.py |
| Experiment 15b | COMPLETE — date fix + lot size correction. Results documented. |
| Capital floor | LOWERED to ₹10K (was ₹2L) for trial run support |
| LOT_SIZES | NIFTY=65 units (Jan 2026), SENSEX=20 units (Jan 2026). Backtest uses NIFTY=75/SENSEX=20. |

---

## Tier 1 — Actionable Now

---

### ENH-35: Historical Signal Validation

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

Full year results: NIFTY 244 signals, 58.6% T+30m accuracy. 6 signal engine changes applied. Phase 4 gate passed. Do not re-run.

---

### ENH-37: ICT Pattern Detection Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

All 6 components live: DDL, ICTDetector, HTF zone builder, runner, signal enrichment, dashboard. MTF hierarchy W/D/H confirmed. 1H zones (MEDIUM) confirmed adds edge.

---

### ENH-38: Live Kelly Tiered Sizing

| Field | Detail |
|---|---|
| Source | Experiment 16 — Kelly Tiered Sizing with Compounding Capital |
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

**What was built:**
- `merdian_utils.py` — `LOT_SIZES`, `CAPITAL_FLOOR=10_000`, `effective_sizing_capital()`, `estimate_lot_cost()` (spot × IV × √DTE × 0.4), `compute_kelly_lots()`. Strategy switch: `ACTIVE_KELLY = KELLY_FRACTIONS_C` → change to D when ready.
- `detect_ict_patterns_runner.py` — reads `capital_tracker` each cycle, fetches DTE via `nearest_expiry_db`, computes and writes `ict_lots_t1/t2/t3` to `ict_zones`. Log: `Kelly lots (lot_size=65, dte=2d, iv=15.0%) T1:x T2:x T3:x`
- `build_trade_signal_local.py` — reads lots from active `ict_zones`, forwards to `signal_snapshots.ict_lots_t1/t2/t3`
- Schema: `ict_zones` +3 integer cols, `signal_snapshots` +3 integer cols

**Kelly fractions (validated):**

| Tier | Criteria | WR | Half Kelly | Full Kelly |
|---|---|---|---|---|
| TIER1 | BULL_OB MORNING, BULL_OB DTE=0, BEAR_OB MORNING, BULL_OB SWEEP+MOM_YES | 93-100% | 50% | 100% |
| TIER2 | BULL_OB MOM_YES, BEAR_OB MOM_YES, BULL_OB AFTERNOON, BEAR_OB DTE=4+ | 80-91% | 40% | 80% |
| TIER3 | JUDAS_BULL, BULL_FVG, BEAR_OB (unqualified), BULL_OB (unqualified) | 49-73% | 20% | 40% |

**Experiment 16 results (with ₹25L/₹50L ceiling):**

| Strategy | Combined Return | Max DD | Ret/DD |
|---|---|---|---|
| A — Original 1→2→3 | +494% | 12.7% | 38.9x |
| B — User 7→14→21 (T1+2) | +855% | 13.4% | 63.6x |
| C — Half Kelly | +18,585% | 16.6% | 1,122x |
| D — Full Kelly | +44,234% | 24.8% | 1,785x |

Start with Strategy C. Upgrade to D after 3–6 months live experience.

---

### ENH-39: Capital Ceiling Enforcement

| Field | Detail |
|---|---|
| Source | Decision in research session 3 |
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

`effective_sizing_capital(capital)` in `merdian_utils.py`:
- Below ₹10K → floor at ₹10K (lowered from ₹2L for trial runs)
- ₹10K–₹25L → full Kelly on actual capital
- ₹25L–₹50L → freeze at ₹25L
- Above ₹50L → hard cap at ₹50L

---

### ENH-40: Signal Rule Book v1.1

| Field | Detail |
|---|---|
| Source | Synthesis of Experiments 2, 2b, 5, 8, 10c, 15, 16 |
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | docs/research/MERDIAN_Signal_RuleBook_v1.1.md |

13 rule changes: 4 NEW, 3 CHANGED, 5 CONFIRMED, 1 CLOSED. Full detail in document.

---

### ENH-41: BEAR_OB DTE Gate — Combined Structure

| Field | Detail |
|---|---|
| Source | Experiment 2b (Futures vs Options) |
| Status | **DOCUMENTED — code pending execution layer** |
| Updated | 2026-04-13 |

Rule documented in Signal Rule Book v1.1 Section 2.2. For manual trading: BEAR_OB DTE=0 and DTE=1 → short futures + long ATM CE as insurance. Not pure PE. For DTE=2+: pure PE continues. Code implementation requires execution layer build (post-Phase 4).

---

### ENH-42: Session Pyramid — Deferred

| Field | Detail |
|---|---|
| Source | Experiments 14 and 14b |
| Status | **DEFERRED — post ENH-42 WebSocket** |
| Priority Tier | 2 |

Single T+30m exit on first OB remains optimal. Session pyramid -₹12,645 vs single trade. Deferred until WebSocket provides real-time option prices for contra bounce timing.

---

### ENH-43: Signal Dashboard

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | C:\GammaEnginePython\merdian_signal_dashboard.py |
| Port | 8766 |

Trader-facing dashboard (separate from health monitor on 8765). Per-symbol cards: action, confidence, ICT pattern/tier/WR/MTF, execution block (strike, expiry, DTE, live premium, lot cost, capital deployed), exit countdown (⚡ EXIT NOW at T+30m), active-pattern-only WR legend, regime pills, BLOCKED/TRADE ALLOWED badge. Hard rules banner. Auto-refresh 5min. Live clock ticks every second.

---

### ENH-44: Capital Management

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | set_capital.py, merdian_signal_dashboard.py (SET input) |

`set_capital.py` — CLI setter: `NIFTY 500000`, `SENSEX 300000`, `BOTH 500000`, `--show`. Dashboard: per-symbol number input + SET button, POST /set_capital, instant visual feedback (✓ Saved / Error), no page reload.

---

### ENH-45: hist_spot_bars_1m Zerodha Backfill

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | backfill_spot_zerodha.py (runs on MeridianAlpha AWS instance) |

4 missing live canary sessions (Apr 7, 8, 9, 10) backfilled via Zerodha Kite 1-min historical API. 3,000 rows (375 bars × 2 symbols × 4 dates). Upserts on (instrument_id, bar_ts). Enables correct daily zone pre-building via `build_ict_htf_zones.py --timeframe D`.

---

## Summary Table — Full Register

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | IN PROGRESS |
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
| ENH-36 | hist_* to live promotion pipeline | 1 | NOT BUILT |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | **COMPLETE** |
| ENH-39 | Capital ceiling enforcement | 1 | **COMPLETE** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **COMPLETE** |
| ENH-41 | BEAR_OB DTE gate — combined structure | 1 | DOCUMENTED — code pending |
| ENH-42 | Session pyramid | 2 | DEFERRED |
| ENH-43 | Signal dashboard | 1 | **COMPLETE** |
| ENH-44 | Capital management (set_capital + dashboard) | 1 | **COMPLETE** |
| ENH-45 | hist_spot_bars_1m Zerodha backfill | 1 | **COMPLETE** |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

---

*MERDIAN Enhancement Register v6 — 2026-04-13 — Living document, commit to Git after every update*
*Supersedes v5 (2026-04-12). Commit alongside Open Items Register v7 and session log update.*
