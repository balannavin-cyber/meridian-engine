# MERDIAN Enhancement Register v6

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Enhancement_Register_v6.md |
| Supersedes | MERDIAN_Enhancement_Register_v5.md (2026-04-12) |
| Updated | 2026-04-18 |
| Sources | Enhancement Register v5 · Research Sessions 4 and 5 (2026-04-17 through 2026-04-18) |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document. |
| Authority | Tracks proposals, not decisions. Decisions live in master Decision Registry. |
| Update rule | Update in the same session that produces new architectural thinking. Commit immediately. |

---

## v6 Changes from v5

| Change | Detail |
|---|---|
| ENH-43 NEW | Remove breadth as hard gate — Exp 25 confirmed 1.0pp spread (noise) |
| ENH-44 NEW | Momentum opposition hard block — Exp 20 confirmed +22.6pp lift |
| ENH-45 NEW | Premium sweep detector — Exp 27b confirmed 64.5% WR for <1% PE sweeps |
| ENH-46 NEW | MTF OHLCV infrastructure — hist_spot_bars_5m/15m + hist_atm_option_bars_5m/15m built |
| ENH-47 NEW | hist_pattern_signals table — pattern signal store built, backfilled 6,318 rows |
| Exp 17 | LONG_GAMMA gate confirmed correct (Exp 17 + Exp 19 on 5m — symmetric block) |
| Exp 18 | OI wall + ICT confluence — INDEPENDENT. ENH (OI wall synthesis) REJECTED |
| Exp 19 | LONG_GAMMA asymmetry — NO ASYMMETRY on 5m. Current symmetric gate correct |
| Exp 20 | Momentum alignment — +22.6pp lift on 5m. Confirmed gate-level signal |
| Exp 23 series | Sweep reversal — NO MECHANICAL EDGE on 1m or 5m. Discretionary only |
| Exp 25 | Breadth independence — 1.0pp spread on 5m. Gate is noise |
| Exp 26 | Option wick reversal — No edge overall. SHORT_GAMMA PE wick 76.9% (N=13) — monitor |
| Exp 27 | ICT in premium space — No broad edge. 37K signals = detection too loose |
| Exp 27b | Small PE premium sweep — 64.5% WR (N=107) for <1% sweeps. PROPOSED ENH |
| 1m → 5m | All ICT pattern detection moved to 5m bars. 1m = execution only |

---

## Tier 1 — Actionable Now

---

### ENH-35: Historical Signal Validation
*(Carried from v5 — COMPLETE)*

---

### ENH-37: ICT Pattern Detection Layer
*(Carried from v5 — COMPLETE)*

---

### ENH-38: Live Kelly Tiered Sizing
*(Carried from v5 — PROPOSED — next live build)*

---

### ENH-39: Capital Ceiling Enforcement
*(Carried from v5 — PROPOSED — with ENH-38)*

---

### ENH-40: Signal Rule Book v1.1
*(Carried from v5 — PROPOSED — document update required)*

---

### ENH-41: BEAR_OB DTE Gate — Combined Structure
*(Carried from v5 — PROPOSED)*

---

### ENH-42: Session Pyramid — Deferred
*(Carried from v5 — DEFERRED)*

---

### ENH-43: Remove Breadth Hard Gate

| Field | Detail |
|---|---|
| Source | Experiment 25 (5m bars, 2026-04-17) |
| Status | **PROPOSED — signal engine build required** |
| Priority Tier | 1 |
| Commercial Relevance | Internal — removes blocking gate, restores valid trades |

**What it does:** Removes `breadth_regime` as a hard gate in the signal engine. Currently BULLISH breadth blocks BUY_PE signals. Experiment 25 shows breadth is completely independent of ICT edge.

**Evidence:**

| Breadth | WR | N |
|---|---|---|
| BULLISH | 49.3% | 533 |
| BEARISH | 48.9% | 1,492 |
| NEUTRAL | 49.9% | 1,052 |

WR spread = 1.0pp across regimes — pure noise. BEAR_OB actually performs BETTER on BULLISH breadth days (51.0% vs 45.0% on BEARISH). Breadth is directionally backwards as a gate.

**Today's impact:** MERDIAN blocked a valid BULL_OB signal on 2026-04-17 due to BULLISH breadth reading stale data. The trade was taken manually — +25%. The block was not justified by evidence.

**Implementation:**
- Remove `breadth_regime` from hard gate logic in `build_signal_v3.py`
- Keep breadth as confidence modifier only: BULLISH_BREADTH + BUY_CE = +5 pts, BEARISH_BREADTH + BUY_PE = +5 pts
- Remove from `DO_NOTHING` reasons list

---

### ENH-44: Momentum Opposition Hard Block

| Field | Detail |
|---|---|
| Source | Experiment 20 (5m bars, 2026-04-17) |
| Status | **PROPOSED — signal engine build required** |
| Priority Tier | 1 |
| Commercial Relevance | Internal — strongest single filter found in experiment series |

**What it does:** Adds momentum direction as a hard gate. When `ret_session` opposes the ICT pattern direction, block the signal. This is the largest single edge improvement found in the entire experiment series.

**Evidence:**

| Momentum | WR | N |
|---|---|---|
| ALIGNED | 60.9% | 2,138 |
| OPPOSED | 38.3% | 2,275 |
| NEUTRAL | 47.6% | 311 |

Lift = +22.6pp aligned vs opposed. Consistent across all patterns:

| Pattern | Aligned | Opposed |
|---|---|---|
| BEAR_OB | 63.1% | 40.4% |
| BULL_OB | 59.3% | 35.9% |
| BULL_FVG | 58.6% | 36.9% |

**Alignment definition:**
- BUY_PE (BEAR_OB) signal + `ret_session < -0.05%` = ALIGNED
- BUY_CE (BULL_OB) signal + `ret_session > +0.05%` = ALIGNED
- |ret_session| < 0.05% = NEUTRAL (allow, 47.6% WR)
- Direction mismatch = OPPOSED → BLOCK

**Implementation:**
- Add to `build_signal_v3.py` before pattern tier evaluation
- Block = DO_NOTHING with reason "Momentum opposes signal direction"
- Neutral = allow (do not penalise)
- This supersedes current `momentum_regime` confidence modifier

---

### ENH-45: Premium Sweep Detector

| Field | Detail |
|---|---|
| Source | Experiments 27 and 27b (2026-04-17/18) |
| Status | **PROPOSED — needs more live data before build** |
| Priority Tier | 2 |
| Commercial Relevance | Internal — new signal class |

**What it does:** Detects small ATM PE/CE premium sweeps in morning session as a reversal signal — independent of spot structure.

**Evidence from Exp 27b:**

| PE Sweep Size | WR | N |
|---|---|---|
| 0.2-1.0% | **64.5%** | 107 |
| 1.0-1.5% | 56.1% | 41 |
| 1.5-2.0% | 37.5% | 40 |

Small sweeps (< 1%) have genuine edge. Large sweeps are noise or contrary signal.

**Key insight:** Premium sweep is MOMENTUM-INDEPENDENT (unlike spot ICT which needs momentum alignment). Option premium microstructure has its own edge regardless of spot momentum direction.

**Signal definition:**
```
ATM PE premium sweeps above prior morning high by 0.2-1.0%
AND closes back below prior high within 2 bars (quick rejection)
AND morning session only (09:15-10:30 IST)
→ BUY_CE signal (spot expected to rise)
Expected WR: ~64.5% on premium
```

**Why not build immediately:**
- N=107 is meaningful but needs more sessions
- Need to validate on live data (5m ATM bars now captured in pipeline)
- CE small sweep (bear version) less clear — CE + NO_FLIP = 68.4% (N=57) promising but small

**Monitoring plan:** Log every morning PE/CE premium sweep < 1% in live data. Review after 50 live occurrences.

---

### ENH-46: MTF OHLCV Infrastructure

| Field | Detail |
|---|---|
| Source | Session 4 (2026-04-17) |
| Status | **COMPLETE** |
| Updated | 2026-04-17 |

**Built:**

| Table | Rows | Description |
|---|---|---|
| `hist_spot_bars_5m` | 41,248 | 5m spot bars, NIFTY + SENSEX, full year |
| `hist_spot_bars_15m` | 14,072 | 15m spot bars |
| `hist_atm_option_bars_5m` | 27,082 | ATM PE+CE OHLC, greeks, IV OHLC, wick metrics |
| `hist_atm_option_bars_15m` | 9,601 | 15m ATM option bars |

**Key design decisions:**
- ATM ± 2 strikes only (not all strikes — keeps table small)
- PE/CE wick metrics pre-computed: `pe_upper_wick_ratio`, `pe_reversal_wick` etc.
- IV OHLC stored where available (NULL in backfill — greeks not in vendor data)
- 1m bars = execution only going forward. All pattern detection on 5m/15m.

**Build scripts:** `build_spot_bars_mtf.py`, `build_atm_option_bars_mtf.py`

---

### ENH-47: hist_pattern_signals Table

| Field | Detail |
|---|---|
| Source | Session 4 (2026-04-17) |
| Status | **COMPLETE** |
| Updated | 2026-04-17 |

**What it does:** Stores all historical ICT pattern signal events with regime context and outcomes. Eliminates need to re-derive patterns from raw data in every experiment.

**Schema key columns:**
- `pattern_type` — BEAR_OB, BULL_OB, BULL_FVG, SWEEP_REVERSAL
- `gamma_regime`, `breadth_regime`, `iv_regime`, `ret_session` — at signal time
- `win_30m` — spot direction proxy (retain for backward compat)
- `win_option_30m` — actual premium P&L outcome (new — joined from ATM bars)
- `source` — backfill_5m (current) | live (future writes)

**Current state:** 6,318 rows backfilled on 5m bars. 52 sweep reversals detected (vs 0 on 1m). All experiments now run in < 60 seconds against this table.

**Next:** Live signal detector writes to this table on every signal fire. Dataset grows automatically.

---

## Experiment Results Summary (Sessions 4-5, 2026-04-17/18)

| Exp | Question | Result | Decision |
|---|---|---|---|
| 17 | BEAR_OB MORNING × Gamma | LONG_GAMMA = 54.6% WR — coin flip | Gate confirmed |
| 18 | OI wall + ICT confluence | +4.5pp lift — noise | OI synthesis REJECTED |
| 19 (5m) | LONG_GAMMA asymmetry BULL vs BEAR OB | 50.5% vs 49.7% — no asymmetry | Symmetric gate confirmed |
| 20 (5m) | Momentum alignment | +22.6pp lift | **ENH-44: Add as hard gate** |
| 23 | Naked sweep reversal | 17.8% WR — no edge | ENH-54 sweep mode REJECTED |
| 23b | Sweep + W zone confluence | 19.5% WR — still no edge | Confluence doesn't rescue |
| 23c | Sweep + quality filters | 33.3% WR (N=3) — insufficient data | Discretionary only |
| 25 (5m) | Breadth independence | 1.0pp spread — noise | **ENH-43: Remove hard gate** |
| 26 | Option wick reversal | 1.7pp lift — noise | No signal |
| 26 (partial) | PE wick under SHORT_GAMMA | 76.9% (N=13) — promising | Monitor with more data |
| 27 | ICT concepts in premium space | 37K signals — too loose | No broad edge |
| 27b | Small PE premium sweep | 64.5% (N=107) for <1% sweep | **ENH-45: PROPOSED** |

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
| ENH-31 | Expiry calendar utility | 1 | COMPLETE |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED |
| ENH-33 | Pure-Python BS IV engine | 1 | PRODUCTION |
| ENH-34 | Live monitoring dashboard | 1 | PRODUCTION |
| ENH-35 | Historical signal validation | 1 | **COMPLETE** |
| ENH-36 | hist_* to live promotion pipeline | 1 | NOT BUILT |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | PROPOSED — next build |
| ENH-39 | Capital ceiling enforcement | 1 | PROPOSED — with ENH-38 |
| ENH-40 | Signal Rule Book v1.1 | 1 | PROPOSED — document update |
| ENH-41 | BEAR_OB DTE gate | 1 | PROPOSED |
| ENH-42 | Session pyramid | 2 | DEFERRED |
| ENH-43 | Remove breadth hard gate | 1 | **PROPOSED** |
| ENH-44 | Momentum opposition hard block | 1 | **PROPOSED** |
| ENH-45 | Premium sweep detector | 2 | **PROPOSED — monitor first** |
| ENH-46 | MTF OHLCV infrastructure | 1 | **COMPLETE** |
| ENH-47 | hist_pattern_signals table | 1 | **COMPLETE** |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

---

*MERDIAN Enhancement Register v6 — 2026-04-18 — Living document, commit to Git after every update*
*Supersedes v5 (2026-04-12). Commit alongside session log and open items update.*
