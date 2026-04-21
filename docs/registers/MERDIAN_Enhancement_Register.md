# MERDIAN Enhancement Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `docs/registers/MERDIAN_Enhancement_Register.md` |
| Scope | Living register of all proposed and delivered MERDIAN enhancements, ENH-01 through ENH-74 |
| Lineage | Unified from v1 (2026-03-31) through v7 (2026-04-19 v8-appended). Prior versioned files archived at `docs/registers/archive/`. |
| Last updated | 2026-04-20 |
| Purpose | Forward-looking and historical register of all enhancement proposals, their status, evidence, and delivery. |
| Authority | Current operational state of each ENH. Session appendices win on session-specific rationale; this register wins on current status. |
| Update rule | Update in-place (append or edit). Do NOT create a new versioned file. |
| Numbering | Per Documentation Protocol v2 Rule 5 (2026-04-19): monotonic integers, REJECTED IDs keep their slot as rejection record. |

---

## Conventions

- **Status values:** COMPLETE, PROPOSED, IN PROGRESS, DOCUMENTED, PARTIAL, DEFERRED, STUBBED, PRODUCTION, RESEARCH TRACK, SUPERSEDED, REJECTED, PIVOTED.
- **History field** in each entry shows status progression across register versions.
- **Rejected IDs** retain their number as a rejection record. Do NOT reuse.
- **Sub-items** (e.g. ENH-51a through ENH-51f) belong to their parent ID's block.
- Today's session commits are cross-referenced where relevant.

---

## Part 1 -- Status Summary

Sortable table of all 72 IDs. For full detail see Part 4.

| ID | Title | Priority Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session — Session Return to Momentum Engine | 1 | **COMPLETE** |
| ENH-02 | Put/Call Ratio (PCR) Signal | 1 | **COMPLETE** |
| ENH-03 | Volume/OI Ratio Signal | 1 | **COMPLETE** |
| ENH-04 | Chain-Wide IV Skew Signal | 1 | **COMPLETE** |
| ENH-05 | CONFLICT Resolution Logic | 1 | **SUPERSEDED by ENH-35** |
| ENH-06 | Pre-Trade Cost Filter (Almgren-Chriss Bid-Ask Model) | 1 | **COMPLETE** |
| ENH-07 | Basis-Implied Risk-Free Rate | 1 | **COMPLETE** |
| ENH-08 | Vega Bucketing by Expiry | 1 | **DEFERRED** |
| ENH-09 | Heston Calibration Layer | 2 | **PROPOSED** |
| ENH-10 | Theoretical Option Pricing (Monte Carlo) | 2 | **PROPOSED** |
| ENH-11 | Calibrated Strike Selection for Vertical Spreads | 2 | **PROPOSED** |
| ENH-12 | Calendar Spreads (Vol Term Structure Expression) | 2 | **PROPOSED** |
| ENH-13 | Straddles and Strangles (Pure Vol Direction) | 2 | **PROPOSED** |
| ENH-14 | Skew Trades / Risk Reversals | 2 | **PROPOSED** |
| ENH-15 | Expected Value Computation for Position Sizing | 2 | **PROPOSED** |
| ENH-16 | Greeks-Aware Position Sizing | 2 | **PROPOSED** |
| ENH-17 | Vol-Uncertainty Scaling (xi-Based Position Sizing) | 2 | **PROPOSED** |
| ENH-18 | Model-State Stops (Exit on Thesis Break, Not Price) | 2 | **PROPOSED** |
| ENH-19 | Profit-Taking on Mispricing Convergence | 2 | **PROPOSED** |
| ENH-20 | Delta Hedging Cadence (Gamma/Vanna Driven) | 2 | **PROPOSED** |
| ENH-21 | Calibration Quality Guard | 2 | **PROPOSED** |
| ENH-22 | Calibrated Vol Surface as Standalone Data Product | 3 | **PROPOSED** |
| ENH-23 | REST API — Stage 1 (Signal Polling) | 3 | **PROPOSED** |
| ENH-24 | REST API — Stage 2 (Real-Time WebSocket + Historical) | 3 | **PROPOSED** |
| ENH-25 | Strategy Proposal API — Stage 3 | 3 | **PROPOSED** |
| ENH-26 | Quantum Annealing for Heston Calibration | 4 | **RESEARCH TRACK** |
| ENH-27 | Quantum Amplitude Estimation for Monte Carlo | 4 | **RESEARCH TRACK** |
| ENH-28 | Historical Data Ingest Pipeline | 1 | **COMPLETE** |
| ENH-29 | Signal Premium Outcome Measurement | 1 | **PIVOTED** |
| ENH-30 | SMDM Infrastructure (Track 2) | 1 | **PARTIAL** |
| ENH-31 | Expiry Calendar Utility | 1 | **COMPLETE** |
| ENH-32 | S3 Warm Tier Archiver | 1 | **STUBBED (see ENH-52b)** |
| ENH-33 | Pure-Python Black-Scholes IV Engine (NEW) | 1 | **PRODUCTION** |
| ENH-34 | Live Monitoring Dashboard (NEW) | 1 | **PRODUCTION** |
| ENH-35 | Historical Signal Validation | 1 | **COMPLETE** |
| ENH-36 | hist_* to live 1-min spot promotion | 1 | **COMPLETE** |
| ENH-37 | ICT Pattern Detection Layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly Tiered Sizing | 1 | **COMPLETE** |
| ENH-39 | Capital Ceiling Enforcement | 1 | **COMPLETE** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **COMPLETE** |
| ENH-41 | BEAR_OB DTE Gate — Combined Structure | 1 | **DOCUMENTED -- code pending execution layer** |
| ENH-42 | Session Pyramid — Deferred | 2 | **DEFERRED** |
| ENH-43 | Signal Dashboard | 1 | **COMPLETE** |
| ENH-44 | Capital Management | 1 | **COMPLETE** |
| ENH-45 | hist_spot_bars_1m Zerodha Backfill | 1 | **COMPLETE** |
| ENH-46 | Process Manager | 1 | **COMPLETE** |
| ENH-47 | MERDIAN_PreOpen Task (C-07b permanent fix) | 1 | **COMPLETE** |
| ENH-48 | Phase 4A Execution Layer | 1 | **COMPLETE** |
| ENH-49 | Phase 4B — Semi-Auto Order Placement | 1 | **COMPLETE** |
| ENH-50 | Phase 4C — Full Auto | 1 | **PROPOSED** |
| ENH-51 | WebSocket Feed + AWS Cloud Migration | 1 | **IN PROGRESS (51a COMPLETE)** |
| ENH-51a | (no title -- see None) | 1 | **COMPLETE** |
| ENH-51b | (no title -- see None) | 1 | **PROPOSED** |
| ENH-51c | (no title -- see None) | 1 | **PROPOSED** |
| ENH-51d | (no title -- see None) | 1 | **PROPOSED** |
| ENH-51e | (no title -- see None) | 1 | **DEFERRED** |
| ENH-51f | (no title -- see None) | 1 | **DEFERRED** |
| ENH-52 | Dhan Expired Options 5-Year Backfill | 1 | **PROPOSED** |
| ENH-52b | S3 Warm Tier Archiver (was HIST-02) | 1 | **DEFERRED (Phase 5)** |
| ENH-53 | Remove breadth regime as hard gate | 1 | **COMPLETE (PROMOTED)** |
| ENH-54 | HTF Sweep Reversal Trade Mode | 1 | **REJECTED** |
| ENH-55 | Momentum opposition hard block | 1 | **COMPLETE (PROMOTED)** |
| ENH-56 | Premium sweep detector (monitor phase) | 1 | **PROPOSED (MONITOR ONLY)** |
| ENH-57 | MTF OHLCV infrastructure | 1 | **COMPLETE** |
| ENH-58 | hist_pattern_signals table | 1 | **COMPLETE** |
| ENH-59 | Patch script syntax validation rule | 1 | **COMPLETE** |
| ENH-60 | UnboundLocalError in build_trade_signal_local flow-modifier block | 1 | **COMPLETE** |
| ENH-61 | V3 trade_allowed=True unconditional reset at DTE block | 1 | **COMPLETE** |
| ENH-62 | Shadow runner dead since 2026-04-15 | 1 | **COMPLETE** |
| ENH-63 | IV-scaled lot sizing multiplier | 1 | **REJECTED** |
| ENH-64 | Pre-pattern sequence features + afternoon skip + FVG low-IV downgrade | 1 | **COMPLETE** |
| ENH-65 | Remove duplicate Kelly-write block + cache expiry index | 1 | **COMPLETE** |
| ENH-66 | Trading calendar auto-insert must populate open_time/close_time | 1 | **COMPLETE** |
| ENH-67 | latest_market_breadth_intraday is a VIEW — dashboard shows stale counter (was C-08) | 1 | **PROPOSED** |
| ENH-68 | Runner re-reads .env per cycle (tactical stopgap for stale-memory bug class) | 1 | **COMPLETE (tactical, replaced by ENH-74)** |
| ENH-69 | Supervisor staleness threshold shorter than cycle duration (false-restart loop) | 1 | **PROPOSED** |
| ENH-70 | Preflight rewrite — dry-run write-contract enforcement, not probe theater | 1 | **PROPOSED** |
| ENH-71 | Write-contract layer — script_execution_log + ExecutionLog helper (foundation) | 1 | **COMPLETE** |
| ENH-72 | Propagate ExecutionLog to 9 remaining critical scripts (Session 3) | 1 | **PROPOSED** |
| ENH-73 | Dashboard truth + alert daemon contract-violation rules (Session 6) | 1 | **PROPOSED** |
| ENH-74 | Live config layer — core/live_config.py (Session 5, strategic replacement of ENH-68) | 1 | **PROPOSED** |

---

## Part 2 -- Active Work (not yet delivered or under monitoring)

| ID | Title | Status |
|---|---|---|
| ENH-09 | Heston Calibration Layer | **PROPOSED** |
| ENH-10 | Theoretical Option Pricing (Monte Carlo) | **PROPOSED** |
| ENH-11 | Calibrated Strike Selection for Vertical Spreads | **PROPOSED** |
| ENH-12 | Calendar Spreads (Vol Term Structure Expression) | **PROPOSED** |
| ENH-13 | Straddles and Strangles (Pure Vol Direction) | **PROPOSED** |
| ENH-14 | Skew Trades / Risk Reversals | **PROPOSED** |
| ENH-15 | Expected Value Computation for Position Sizing | **PROPOSED** |
| ENH-16 | Greeks-Aware Position Sizing | **PROPOSED** |
| ENH-17 | Vol-Uncertainty Scaling (xi-Based Position Sizing) | **PROPOSED** |
| ENH-18 | Model-State Stops (Exit on Thesis Break, Not Price) | **PROPOSED** |
| ENH-19 | Profit-Taking on Mispricing Convergence | **PROPOSED** |
| ENH-20 | Delta Hedging Cadence (Gamma/Vanna Driven) | **PROPOSED** |
| ENH-21 | Calibration Quality Guard | **PROPOSED** |
| ENH-22 | Calibrated Vol Surface as Standalone Data Product | **PROPOSED** |
| ENH-23 | REST API — Stage 1 (Signal Polling) | **PROPOSED** |
| ENH-24 | REST API — Stage 2 (Real-Time WebSocket + Historical) | **PROPOSED** |
| ENH-25 | Strategy Proposal API — Stage 3 | **PROPOSED** |
| ENH-30 | SMDM Infrastructure (Track 2) | **PARTIAL** |
| ENH-41 | BEAR_OB DTE Gate — Combined Structure | **DOCUMENTED -- code pending execution layer** |
| ENH-50 | Phase 4C — Full Auto | **PROPOSED** |
| ENH-51b |  | **PROPOSED** |
| ENH-51c |  | **PROPOSED** |
| ENH-51d |  | **PROPOSED** |
| ENH-52 | Dhan Expired Options 5-Year Backfill | **PROPOSED** |
| ENH-56 | Premium sweep detector (monitor phase) | **PROPOSED (MONITOR ONLY)** |
| ENH-67 | latest_market_breadth_intraday is a VIEW — dashboard shows stale counter | **PROPOSED** |
| ENH-69 | Supervisor staleness threshold — false restart loop | **PROPOSED** |
| ENH-70 | Preflight rewrite — dry-run contract enforcement | **PROPOSED** |
| ENH-72 | Propagate ExecutionLog to 9 critical scripts | **PROPOSED** |
| ENH-73 | Dashboard truth + alert daemon | **PROPOSED** |
| ENH-74 | Live config layer (core/live_config.py) | **PROPOSED** |


---

## Part 3 -- Rejected & Redefined

Per Documentation Protocol v2 Rule 5: rejected IDs keep their slot as rejection records and are never reused.

### ENH-05 -- SUPERSEDED by ENH-35

- Original proposal (v1-v3): standalone CONFLICT resolution logic in signal engine.
- v4 (2026-04-11): ENH-35 empirically confirmed CONFLICT is asymmetric. CONFLICT BUY_CE now trades (58.7%/55.4% WR). ENH-05's logic was subsumed into ENH-35's Six Signal Engine Changes.
- No separate ENH-05 implementation needed.

### ENH-42 -- REDEFINED (v4 -> v5)

- **Original ENH-42 (v4, 2026-04-11):** WebSocket ATM Option Feed. Proposed as replacement for failed `MERDIAN_Market_Tape_1M`.
- **Redefined ENH-42 (v5, 2026-04-12):** Session Pyramid. Deferred based on Experiments 14/14b.
- **Original WebSocket concept re-filed as ENH-51** (2026-04-13), now split into sub-items ENH-51a through ENH-51f.
- The ENH-42 ID was reused because the WebSocket concept migrated to a larger scope (ENH-51). No data loss; traceable through this note.

### ENH-54 -- REJECTED (2026-04-19)

- Proposed: HTF Sweep Reversal Trade Mode (Experiment series 17).
- Evidence: Experiment 23/23b/23c showed 17-19% WR on sweep reversals. Edge requires discretionary judgment on wick quality and zone mitigation -- cannot mechanise.
- Rejection rationale: pursuing this signal class as an automated MERDIAN mode creates systematic capital loss.

### ENH-63 -- REJECTED (2026-04-19)

- Proposed: IV-scaled lot sizing multiplier helper in merdian_utils.py.
- Rejection rationale: `compute_kelly_lots()` in merdian_utils.py (ENH-38v2, commit c78b6ea 2026-04-13) already applies IV scaling via `estimate_lot_cost(spot, atm_iv_pct, dte_days)`. Higher IV -> higher per-lot premium estimate -> fewer lots. ENH-63's proposed layered multiplier would double-count IV.
- Today's commit b2e8078 was a silent-bug repair (duplicate V1 Kelly block clobbering V2 output for 6 days) -- filed as ENH-65. Not ENH-63.


---

## Part 4 -- Individual Entry Blocks

Chronological by ID. Each entry shows current status, evidence, and history.

### ENH-01: ret_session — Session Return to Momentum Engine

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

**Fix:** `build_momentum_features_local.py` session open threshold changed from 03:45 UTC (09:15 IST) to 03:35 UTC (09:05 IST). `MERDIAN_PreOpen` task captures spot at 09:05 IST — this row is now accepted as the session open price. `ret_session` will be non-null from tomorrow's first cycle. Feeds into `momentum_regime` with 2.5× weight.


**History:** v1=IN PROGRESS — compute_momentum_features_v2_local.py built. Shadow Step 5a. Wiring to runner pending. | v2=IN PROGRESS — compute_momentum_features_v2_local.py built. Shadow Step 5a. Wiring pending. | v3=IN PROGRESS — compute_momentum_features_v2_local.py built. Shadow Step 5a. Wiring pending. | v5=IN PROGRESS | v6=IN PROGRESS | v7=COMPLETE

---

### ENH-02: Put/Call Ratio (PCR) Signal

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 2 |
| Status | IN PROGRESS — compute_options_flow_local.py built. Shadow Step 3a. Wiring pending. |
| Dependency | None |
| Priority Tier | 1 |
| Commercial Relevance | Internal — improves signal quality |

**What it does:** Computes Put/Call OI ratio from the full option chain snapshot. PCR > 1.5 combined with SHORT gamma = high-conviction bearish structural condition.


**History:** v1=IN PROGRESS — compute_options_flow_local.py built. Shadow Step 3a. Wiring to runner pending. | v2=IN PROGRESS — compute_options_flow_local.py built. Shadow Step 3a. Wiring pending. | v3=IN PROGRESS — compute_options_flow_local.py built. Shadow Step 3a. Wiring pending. | v5=IN PROGRESS | v6=IN PROGRESS | v7=COMPLETE

---

### ENH-03: Volume/OI Ratio Signal

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 2 |
| Status | IN PROGRESS — part of compute_options_flow_local.py |
| Dependency | None |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Computes volume-to-OI ratio per strike. High volume/OI signals active institutional buying rather than stale OI accumulation. Volume/OI > 20 at a specific strike = fresh directional flow in current session.


**History:** v1=IN PROGRESS — part of compute_options_flow_local.py | v2=IN PROGRESS — part of compute_options_flow_local.py | v3=IN PROGRESS — part of compute_options_flow_local.py | v5=IN PROGRESS | v6=IN PROGRESS | v7=COMPLETE

---

### ENH-04: Chain-Wide IV Skew Signal

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 2 |
| Status | IN PROGRESS — part of compute_options_flow_local.py |
| Dependency | None |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Computes IV skew across the full option chain (put IV − call IV at equidistant strikes from ATM). Chain-wide skew reveals directional fear vs complacency — stronger signal than single ATM IV point.


**History:** v1=IN PROGRESS — part of compute_options_flow_local.py | v2=IN PROGRESS — part of compute_options_flow_local.py | v3=IN PROGRESS — part of compute_options_flow_local.py | v5=IN PROGRESS | v6=IN PROGRESS | v7=COMPLETE

---

### ENH-05: CONFLICT Resolution Logic

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-11 |
| Dependency | ENH-35 (done) |

ENH-35 confirmed CONFLICT is asymmetric. breadth BULLISH + momentum BEARISH → BUY_CE now trades: 58.7% SENSEX, 55.4% NIFTY at N=3,575. breadth BEARISH + momentum BULLISH → DO_NOTHING retained (47-49%, protects capital). `infer_direction_bias()` updated in `build_trade_signal_local.py`.


**History:** v1=NOT BUILT — requires ENH-01 (ret_session) first | v2=NOT BUILT — requires ENH-01 first. Now also benefits from ENH-35 accuracy data. | v3=NOT BUILT — requires ENH-01 first. Now also benefits from ENH-35 accuracy data. | v4=COMPLETE — 2026-04-11 | v5=NOT BUILT | v6=NOT BUILT | v7=SUPERSEDED by SE-01 (ENH-35) | 2026-04-19=SUPERSEDED by ENH-35

---

### ENH-06: Pre-Trade Cost Filter (Almgren-Chriss Bid-Ask Model)

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (TRA equivalent) |
| Status | PROPOSED |
| Dependency | None — bid/ask data already in option_chain_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal quality improvement |

**What it does:** Before any strategy proposal is emitted, computes net debit/credit at bid-ask (not mid-price), computes round-trip cost including exit spread, and suppresses proposals where model edge does not exceed 2× round-trip cost.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED | v5=PROPOSED | v6=PROPOSED | v7=COMPLETE

---

### ENH-07: Basis-Implied Risk-Free Rate

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (BTMM equivalent) |
| Status | **IN PROGRESS** (was PROPOSED — infrastructure now exists) |
| Dependency | hist_future_bars_1m confirmed populated with 247 days of data |
| Priority Tier | 1 |
| Commercial Relevance | Internal — improves BS pricing accuracy |

**What it does:** Derives the implied risk-free rate from the futures basis (futures price − spot price) rather than using the constant 6.5% assumption. The current BS IV solver uses a hardcoded 6.5% — the basis-implied rate is more accurate and will vary by DTE and market conditions.

**Update V2:** `hist_future_bars_1m` was confirmed as populated during the V18D backfill work. The basis can be computed at every bar_ts from `hist_future_bars_1m.close − hist_spot_bars_1m.close`. This is now buildable immediately — no new data required. The BS IV solver in `backfill_gamma_metrics.py` and `backfill_volatility_metrics.py` both use hardcoded 6.5% — these would benefit from dynamic rate computation.


**History:** v1=PROPOSED | v2=IN PROGRESS (was PROPOSED — infrastructure now exists) | v3=IN PROGRESS (was PROPOSED — infrastructure now exists) | v4=IN PROGRESS | v5=IN PROGRESS | v6=IN PROGRESS | v7=COMPLETE

---

### ENH-08: Vega Bucketing by Expiry

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (PORT equivalent) |
| Status | PROPOSED |
| Dependency | None |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Groups total vega exposure by expiry bucket (weekly vs monthly). Reveals whether the system's implied volatility sensitivity is concentrated in near-term or far-term expiries — useful for calendar spread strategy generation.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED | v5=PROPOSED | v6=PROPOSED | v7=DEFERRED

---

### ENH-09: Heston Calibration Layer

| Status | PROPOSED |
|---|---|
| Dependency | ENH-33 (done) + Phase 4 gate |

*(Unchanged from v3)*


**History:** v1=PROPOSED — foundation for all Tier 2 enhancements | v2=PROPOSED | v3=PROPOSED | v4=PROPOSED | v5=PROPOSED | v6=PROPOSED | v7=PROPOSED

---

### ENH-10: Theoretical Option Pricing (Monte Carlo)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 (Heston calibration layer) |
| Priority Tier | 2 |
| Commercial Relevance | Core of mispricing signal — enables strategy proposals |

**What it does:** Uses calibrated Heston parameters to compute theoretical fair value for every strike in the option chain via Monte Carlo path simulation (or semi-analytical Heston for European options, which is faster). Computes mispricing gap: theoretical_price − market_ltp. Writes to `theoretical_option_prices`.

**Why it matters:** This converts MERDIAN from a market-structure reader to a mispricing detector. The system no longer just asks "given the market structure, which direction?" It asks "is this option mispriced relative to what the calibrated model says it should be worth?"

**New table required:** `theoretical_option_prices` — per-strike per-cycle: ts, symbol, strike, option_type, expiry, model_price, market_ltp, mispricing_gap, model_delta, model_gamma, model_vega, model_vanna.


**History:** v1=PROPOSED | v2=`position_monitor` | v3=`position_monitor` | 2026-04-19=PROPOSED

---

### ENH-11: Calibrated Strike Selection for Vertical Spreads

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-10 (theoretical option prices) |
| Priority Tier | 2 |
| Commercial Relevance | Customer-facing in Stage 3 API |

**What it does:** When a directional signal fires, selects the specific strikes for a vertical spread by identifying: (a) the overpriced strike to sell, (b) the underpriced strike to buy, using the mispricing gaps from ENH-10. Produces a structured proposal: strategy_type=PUT_SPREAD, long_leg=<strike>, short_leg=<strike>, net_debit_mid, net_debit_market, model_edge.

**Why it matters:** Replaces "BUY_PE" (naked direction) with a spread structure that captures mispricing on both legs. Directional view is expressed at the cheapest possible price given the current vol surface shape.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-12: Calendar Spreads (Vol Term Structure Expression)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 (Heston calibration — kappa and theta parameters) |
| Priority Tier | 2 |
| Commercial Relevance | Customer-facing in Stage 3 API |

**What it does:** Uses Heston kappa (mean reversion speed) and theta (long-run vol) to identify when near-term vol is expensive relative to medium-term vol. Proposes calendar spreads: sell near-dated option (rich premium), buy further-dated option (cheap vol). Pure vol term structure bet, not directional.

**Why it matters:** If calibrated vol is significantly above theta with high kappa (fast mean reversion), the model says near-term vol will compress before expiry. This is tradeable without any directional view on spot.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-13: Straddles and Strangles (Pure Vol Direction)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 (xi and theta parameters) |
| Priority Tier | 2 |
| Commercial Relevance | Customer-facing in Stage 3 API |

**What it does:** Uses xi (vol of vol) and current vol vs theta to generate vol direction signals independent of spot direction. Current vol >> theta, low xi → short straddle (vol expected to compress, mean revert). Current vol << theta, high xi → long straddle (vol expected to expand, large move in either direction).

**Why it matters:** These are market-neutral trades. They do not require a view on spot direction. They require only a calibrated view on vol dynamics — which Heston provides directly.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-14: Skew Trades / Risk Reversals

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 (rho parameter) |
| Priority Tier | 2 |
| Commercial Relevance | Customer-facing in Stage 3 API |

**What it does:** Uses Heston rho (spot-vol correlation) to identify when market skew pricing is anomalous relative to the structural spot-vol relationship. Proposes risk reversals: sell overpriced puts, buy underpriced calls (or vice versa) in same notional. Near-zero directional delta, expressing a view that current skew is anomalous.

**Why it matters:** Skew tends to overshoot in both directions around events then normalise. Heston provides a model-consistent anchor for what "normal" skew is — something the current system has no concept of.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-15: Expected Value Computation for Position Sizing

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-10 (Monte Carlo paths) |
| Priority Tier | 2 |
| Commercial Relevance | Internal — improves position sizing quality |

**What it does:** For any proposed strategy, runs the simulated Monte Carlo paths through the payoff function and averages the discounted results. Computes: model_fair_value, market_price, edge = model_fair_value − market_price. Sizes position proportional to edge / variance_of_outcomes. Kelly-adjacent sizing grounded in actual model output.

**Why it matters:** Current MERDIAN confidence scores are not connected to a probability distribution. This provides explicit EV-based sizing — if edge is ₹20 and variance is ₹100, size accordingly. If edge is ₹5, size minimally.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-16: Greeks-Aware Position Sizing

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-10 (model Greeks from Monte Carlo) |
| Priority Tier | 2 |
| Commercial Relevance | Internal |

**What it does:** Sizes positions to a target risk metric rather than a target notional. Target delta exposure → size the spread. Target vega per vol point → size the straddle. Target gamma limit → cap spread size. All driven by model Greeks from ENH-10.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-17: Vol-Uncertainty Scaling (xi-Based Position Sizing)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 (xi parameter from Heston calibration) |
| Priority Tier | 2 |
| Commercial Relevance | Internal |

**What it does:** Scales position size inversely with xi (vol of vol). High xi = the vol model's prediction is less reliable = wider distribution of outcomes = smaller position. This is a second-order risk control that Black-Scholes cannot provide.

**Why it matters:** Current MERDIAN has no mechanism to shrink position size when the vol environment itself is uncertain. xi provides exactly this signal.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-18: Model-State Stops (Exit on Thesis Break, Not Price)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 (calibrated parameters updated each cycle) |
| Priority Tier | 2 |
| Commercial Relevance | Internal — fundamental improvement to position management |

**What it does:** Exits positions not when price hits a level but when the calibrated parameters cross a threshold that invalidates the original thesis. Example: entered short straddle because vol was above theta with low xi. If subsequent calibration shows xi has spiked, the mean reversion that was relied upon is now unpredictable → exit on model state.

**New table required:** `position_monitor` — per open position: entry_ts, strategy_type, legs, entry_params (kappa/theta/xi/rho at entry), current_params, delta, gamma, vega, model_state_exit_condition, days_to_expiry.


**History:** v1=PROPOSED | v2=`calibration_quality_log` | v3=`calibration_quality_log` | 2026-04-19=PROPOSED

---

### ENH-19: Profit-Taking on Mispricing Convergence

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-10 (theoretical prices updated each cycle) |
| Priority Tier | 2 |
| Commercial Relevance | Internal |

**What it does:** Closes positions when market price converges to model fair value — the mispricing that justified entry has been captured. Does not require holding to expiry. Each 5-minute cycle re-evaluates mispricing gap. When gap falls below exit threshold → close.

**Why it matters:** Current MERDIAN has no mid-trade guidance. This provides a model-driven exit that is independent of price level or P&L — based purely on whether the original edge still exists.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-20: Delta Hedging Cadence (Gamma/Vanna Driven)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-10 (gamma and vanna from Monte Carlo) |
| Priority Tier | 2 |
| Commercial Relevance | Internal |

**What it does:** For vol-long positions where direction-neutrality is required, determines when to delta-hedge based on gamma and vanna levels. High gamma + high vanna → hedge every 5-minute cycle. Low gamma + low vanna → hedge less frequently. MERDIAN's existing 5-minute cycle is the natural hedging cadence.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-21: Calibration Quality Guard

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-09 |
| Priority Tier | 2 |
| Commercial Relevance | Internal — system integrity |

**What it does:** Before any Tier 2 signal is emitted, checks calibration RMSE against a quality threshold. If calibration could not fit the current smile within tolerance, suppresses all model-dependent signals for that cycle. Logs: "CALIBRATION_QUALITY_INSUFFICIENT — model signals suppressed for this cycle."

**New table required:** `calibration_quality_log` — per-cycle: ts, symbol, rmse, n_strikes_used, calibration_passed, suppression_reason.

---

## Tier 3 — After Signal Validation

These require MERDIAN's signals to have demonstrated genuine positive expected value over a statistically meaningful sample. Signal validation is the gate — not a technical gate but a commercial one.


**History:** v1=PROPOSED | v2=`strategy_proposals` | v3=`strategy_proposals` | 2026-04-19=PROPOSED

---

### ENH-22: Calibrated Vol Surface as Standalone Data Product

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (BVOL equivalent) |
| Status | PROPOSED |
| Dependency | ENH-09 (Heston calibration layer live and proven) |
| Priority Tier | 3 |
| Commercial Relevance | STANDALONE DATA PRODUCT — separate from signal service |

**What it does:** Packages the calibrated Heston surface (kappa, theta, xi, rho, v0 + theoretical price at every strike) as a queryable data product updated every 5 minutes. This is the Indian-market equivalent of Bloomberg BVOL.

**Why it matters commercially:** Bloomberg charges for BVOL as a standalone service. MERDIAN would produce an equivalent NSE/BSE index options vol surface as a byproduct of its own calibration pipeline. Target customers: options market makers, risk managers at brokers, academic researchers, prop desks — many of whom need the surface but cannot or will not build the calibration pipeline themselves.

**Commercial note:** This is a data product, not a signal service. Different customer, different pricing model, different sales motion. It is separable from the signal API.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-23: REST API — Stage 1 (Signal Polling)

| Field | Detail |
|---|---|
| Source | Commercial viability session 2026-03-31 |
| Status | PROPOSED |
| Dependency | Signal validation (30+ sessions, positive EV demonstrated) + multi-tenancy design |
| Priority Tier | 3 |
| Commercial Relevance | PRIMARY COMMERCIAL PATH — Stage 1 |

**What it does:** Read-only REST API over signal_snapshots and market_state_snapshots. Customers poll for the latest signal. Authentication via Supabase API key scoped to specific tables. Rate-limited. Per-customer keys.

**What customers receive:** action (BUY_PE / BUY_CE / DO_NOTHING), confidence_score, trade_allowed, gamma_regime, breadth_regime, momentum_alignment, reasons array.

**Infrastructure required:** Supabase Row Level Security (RLS) policies per customer. Per-customer API keys. Rate limiting on Supabase connection pool. Audit logging.

**Target customer:** Systematic retail traders, small prop desks wanting a signal feed to plug into their own execution logic.

**Pricing model:** Per-symbol subscription (NIFTY only / SENSEX only / both). Monthly recurring.


**History:** v1=PROPOSED | v2=Strategy Proposal API Stage 3 | v3=Strategy Proposal API Stage 3 | 2026-04-19=PROPOSED

---

### ENH-24: REST API — Stage 2 (Real-Time WebSocket + Historical)

| Field | Detail |
|---|---|
| Source | Commercial viability session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-23 (Stage 1) validated with paying customers |
| Priority Tier | 3 |
| Commercial Relevance | Commercial — improves retention |

**What it does:** Adds Supabase real-time subscription (WebSocket) so customers receive signals the moment they are written, not on next poll. Also adds historical signal endpoint: query by date range with performance statistics (win rate by regime, average confidence at signal time).

**Why it matters:** A signal that fires at 11:35 IST and is only seen by a polling customer at 11:35:28 may be 28 seconds behind a fast-moving option. WebSocket delivery eliminates that gap. Infrastructure change is one Supabase configuration flag + client reconnection design.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-25: Strategy Proposal API — Stage 3

| Field | Detail |
|---|---|
| Source | Commercial viability session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-10 (Monte Carlo pricing live) + ENH-23 + ENH-24 |
| Priority Tier | 3 |
| Commercial Relevance | HIGH-VALUE commercial path — qualitatively different product |

**What it does:** Replaces directional signal with a complete structured trade brief: strategy_type, specific strikes, legs, theoretical edge, suggested sizing, Greeks of full position, entry conditions, exit conditions, market structure gate status.

**Target customer:** Sophisticated retail traders, family offices, small institutional desks. Price point significantly higher than Stage 1/2. This is a trade brief, not a signal.

---

## Tier 4 — Long-Term (Post-Classical Validation)

These require the classical Monte Carlo system to be built and proven before quantum acceleration makes sense.


**History:** v1=PROPOSED | v2=PROPOSED | v3=PROPOSED

---

### ENH-26: Quantum Annealing for Heston Calibration


**History:** v1=RESEARCH TRACK — not actionable at current stage | v2=RESEARCH TRACK | v3=RESEARCH TRACK

---

### ENH-27: Quantum Amplitude Estimation for Monte Carlo

*(Unchanged from v1. Realistic window: 2028–2032.)*

---

## Summary Table

| ID | Title | Tier | Status | Key Dependency |
|---|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | IN PROGRESS | None |
| ENH-02 | Put/Call Ratio signal | 1 | IN PROGRESS | None |
| ENH-03 | Volume/OI ratio signal | 1 | IN PROGRESS | None |
| ENH-04 | Chain-wide IV skew signal | 1 | IN PROGRESS | None |
| ENH-05 | CONFLICT resolution logic | 1 | NOT BUILT | ENH-01 + ENH-35 |
| ENH-06 | Pre-trade cost filter (Almgren-Chriss) | 1 | PROPOSED | None |
| ENH-07 | Basis-implied risk-free rate | 1 | **IN PROGRESS** | hist_future_bars_1m confirmed |
| ENH-08 | Vega bucketing by expiry | 1 | PROPOSED | None |
| ENH-28 | Historical data ingest pipeline | 1 | **SUBSTANTIALLY COMPLETE** | ENH-31 (expiry calendar) |
| ENH-29 | Signal premium outcome measurement | 1 | **PIVOTED** | hist_market_state + ENH-35 |
| ENH-30 | SMDM infrastructure (Track 2) | 1 | PARTIAL | ENH-29 stable |
| ENH-31 | Expiry calendar utility | 1 | NOT BUILT | Must precede ENH-28 production |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED | AWS credentials |
| ENH-33 | Pure-Python BS IV engine | 1 | **PRODUCTION** | None |
| ENH-34 | Live monitoring dashboard | 1 | **PRODUCTION — v2 deployed, 4 sessions validated** | None |
| ENH-35 | Historical signal validation | 1 | NOT BUILT — next priority | hist_market_state + hist_spot_bars_1m |
| ENH-36 | hist_* to live promotion pipeline | 1 | NOT BUILT | ENH-35 validation pass |
| ENH-09 | Heston calibration layer | 2 | PROPOSED | ENH-33 (done) + Phase 4 gate |
| ENH-10 | Monte Carlo theoretical pricing | 2 | PROPOSED | ENH-09 |
| ENH-11 | Calibrated strike selection (vertical spreads) | 2 | PROPOSED | ENH-10 |
| ENH-12 | Calendar spreads (vol term structure) | 2 | PROPOSED | ENH-09 |
| ENH-13 | Straddles/strangles (pure vol direction) | 2 | PROPOSED | ENH-09 |
| ENH-14 | Skew trades / risk reversals | 2 | PROPOSED | ENH-09 |
| ENH-15 | EV computation for position sizing | 2 | PROPOSED | ENH-10 |
| ENH-16 | Greeks-aware position sizing | 2 | PROPOSED | ENH-10 |
| ENH-17 | Vol-uncertainty scaling (xi-based sizing) | 2 | PROPOSED | ENH-09 |
| ENH-18 | Model-state stops | 2 | PROPOSED | ENH-09 |
| ENH-19 | Profit-taking on mispricing convergence | 2 | PROPOSED | ENH-10 |
| ENH-20 | Delta hedging cadence (gamma/vanna driven) | 2 | PROPOSED | ENH-10 |
| ENH-21 | Calibration quality guard | 2 | PROPOSED | ENH-09 |
| ENH-22 | Calibrated vol surface — standalone data product | 3 | PROPOSED | ENH-09 proven |
| ENH-23 | REST API Stage 1 (signal polling) | 3 | PROPOSED | Signal validation |
| ENH-24 | REST API Stage 2 (WebSocket + historical) | 3 | PROPOSED | ENH-23 |
| ENH-25 | Strategy Proposal API Stage 3 | 3 | PROPOSED | ENH-10 + ENH-23/24 |
| ENH-26 | Quantum annealing for Heston calibration | 4 | RESEARCH TRACK | ENH-09 proven |
| ENH-27 | Quantum amplitude estimation for Monte Carlo | 4 | RESEARCH TRACK | ENH-10 proven |

---

## Bloomberg Function Mapping (unchanged from v1)

| Bloomberg Function | MERDIAN Status | Gap / Action |
|---|---|---|
| BVOL (vol surface) | Raw material exists — per-strike IV in option_chain_snapshots + BS engine (ENH-33) | ENH-09 Heston converts raw IV to coherent surface |
| OVME (options pricing) | Not built | ENH-10 Monte Carlo pricing layer |
| MARS (derivatives risk / Greeks) | Partial — gamma_metrics exist, BS gamma available (ENH-33) | ENH-10/16/20 for full Greeks per position |
| TRA (pre-trade cost analysis) | Not built | ENH-06 Almgren-Chriss filter — actionable now |
| PORT (factor risk / vega bucketing) | Not built | ENH-08 vega bucketing — actionable now |
| BTMM (rate environment) | Partial — hist_future_bars_1m populated, basis computable | ENH-07 basis-implied rate — now IN PROGRESS |

---

## New Tables Required (updated)

| Table | Required By | Status |
|---|---|---|
| `hist_option_bars_1m` | ENH-28 | ✅ BUILT — 247d NIFTY, 247d SENSEX |
| `hist_spot_bars_1m` | ENH-28 | ✅ BUILT — 247d both |
| `hist_future_bars_1m` | ENH-28 / ENH-07 | ✅ BUILT |
| `hist_ingest_log` | ENH-28 | ✅ BUILT |
| `hist_ingest_rejects` | ENH-28 | ✅ BUILT |
| `hist_completeness_checks` | ENH-28 | ✅ BUILT |
| `hist_gamma_metrics` | ENH-28 / ENH-33 | ✅ BUILT — 244 dates x 2 symbols |
| `hist_volatility_snapshots` | ENH-28 / ENH-33 | ✅ BUILT — 488 pairs |
| `hist_market_state` | ENH-28 / ENH-29 | ✅ BUILT — 487 pairs |
| `hist_signal_evaluations` | ENH-35 | NOT BUILT — next session |
| `hist_accuracy_summary` | ENH-35 | NOT BUILT — next session |
| `aging_policy` | ENH-28 | Not built |
| `hist_iv_surface_daily` | ENH-09 | Not built |
| `signal_premium_outcomes` | ENH-29 (post-Phase 4) | Deferred |
| `structural_alerts` | ENH-30 | Not built |
| `vol_model_snapshots` | ENH-09 | Not built |
| `theoretical_option_prices` | ENH-10 | Not built |
| `position_monitor` | ENH-18 | Not built |
| `calibration_quality_log` | ENH-21 | Not built |
| `strategy_proposals` | ENH-11–14 | Not built |

---

## Critical Path to Phase 4 Promotion

```
ENH-33 BS IV engine ✅ DONE
        │
        ▼
ENH-28 Historical ingest ✅ SUBSTANTIALLY COMPLETE
        │
        ▼
ENH-35 Historical validation (run_validation_analysis.py) ← NEXT BUILD (shadow gate 7/10)
        │
        ▼
ENH-05 CONFLICT resolution (informed by accuracy matrix)
        │
        ▼
Phase 4 Gate: shadow sessions + accuracy threshold both met
        │
        ▼
ENH-36 hist_* promotion + Phase 4 live promotion
        │
        ▼
ENH-09 Heston calibration (Tier 2 begins)
```

---

*MERDIAN Enhancement Register v3 — 2026-04-09 — Living document, commit to Git after every update*
*Supersedes v2 (2026-04-06). Commit alongside V18E appendix.*


**History:** v1=RESEARCH TRACK — not actionable at current stage | v2=Key Dependency | v3=Key Dependency | 2026-04-19=RESEARCH TRACK

---

### ENH-28: Historical Data Ingest Pipeline

| Field | Detail |
|---|---|
| Status | **PRODUCTION** |

NIFTY + SENSEX 247 days Apr 2025–Mar 2026 confirmed. The apparent Aug 2025 coverage gap was a false alarm — caused by hardcoded EXPIRY_WD in experiment scripts, fixed by ENH-31.


**History:** v1=IN PROGRESS — hist_ingest_controller.py built (commit b420d4b), vendor delivery pending EOD 2026-04-01 | v2=SUBSTANTIALLY COMPLETE (was IN PROGRESS) | v3=SUBSTANTIALLY COMPLETE (was IN PROGRESS) | v4=PRODUCTION | v5=SUBSTANTIALLY COMPLETE | v6=SUBSTANTIALLY COMPLETE | v7=COMPLETE

---

### ENH-29: Signal Premium Outcome Measurement

| Field | Detail |
|---|---|
| Source | V18B session — outcome measurement layer |
| Status | **PIVOTED** (was IN PROGRESS) |
| Dependency | hist_market_state (now built) + run_validation_analysis.py (ENH-35) |
| Priority Tier | 1 |
| Commercial Relevance | Internal — gates Phase 4 promotion |

**What it does:** Measures whether signals were directionally correct in historical data. Originally planned as live premium tracking in `signal_premium_outcomes` table.

**Update V2 (V18D session):** Architecture pivoted. Original approach (measure live signal premiums from 17 days of market_state_snapshots data) was blocked by data limitations — all 17 days were one-directional bearish. New approach: measure directional accuracy from `hist_market_state` (487 date/symbol pairs, full year of varied conditions) against `hist_spot_bars_1m` (T+15m/T+30m/T+60m spot moves). The `run_validation_analysis.py` script (ENH-35) implements this. The `signal_premium_outcomes` table architecture may still be relevant for real-time premium tracking once Phase 4 is live — defer to post-validation.


**History:** v1=IN PROGRESS — signal_premium_outcomes table live, premium_outcome_writer.py built (commit b420d4b). Signal 615 written (entry=233.4). Path metrics pending hist bar data (ENH-28). | v2=PIVOTED (was IN PROGRESS) | v3=PIVOTED (was IN PROGRESS) | v4=PIVOTED | v5=PIVOTED | v6=PIVOTED | v7=PIVOTED

---

### ENH-30: SMDM Infrastructure (Track 2)

| Field | Detail |
|---|---|
| Source | V18B session |
| Status | PARTIAL |
| Dependency | ENH-29 stable + live canary |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Structural Market Distortion Monitor. Squeeze score computation, pattern flags, cautions output to `structural_alerts` table. Already has defensive logic in signal engine (squeeze_score ≥ 4/5 → DO_NOTHING, trade_allowed=FALSE on expiry day). Full early-warning buy signal conversion is an architectural change requiring validation.


**History:** v1=PARTIALLY BUILT — all read inputs exist and are richer than spec. structural_alerts table not built. straddle_velocity/otm_oi_velocity absent from gamma_metrics. detect_structural_manipulation.py not built. | v2=PARTIAL | v3=PARTIAL | v4=PARTIAL | v5=PARTIAL | v6=PARTIAL | v7=PARTIAL — non-blocking shadow steps running | 2026-04-19=PARTIAL

---

### ENH-31: Expiry Calendar Utility

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-11 |

`merdian_utils.py` built: `build_expiry_index_simple()` + `nearest_expiry_db()`. Replaces hardcoded `EXPIRY_WD = {"NIFTY": 3}` which broke when NIFTY switched Thursday→Tuesday expiry in September 2025. All 11 experiment scripts patched via `patch_expiry_fix.py`. Unlocks Sep 2025–Mar 2026 option data across all experiments.


**History:** v1=NOT BUILT — flagged as open item HIST-01 | v2=NOT BUILT | v3=NOT BUILT | v4=COMPLETE — 2026-04-11 | v5=COMPLETE (merdian_utils.py) | v6=COMPLETE (merdian_utils.py) | v7=COMPLETE — merdian_utils.py | 2026-04-19=COMPLETE

---

### ENH-32: S3 Warm Tier Archiver

| Field | Detail |
|---|---|
| Source | V18B session |
| Status | STUBBED |
| Dependency | AWS credentials |
| Priority Tier | 1 |
| Commercial Relevance | Internal infrastructure |

**What it does:** Archives hist_option_bars_1m and hist_spot_bars_1m to S3 Parquet warm tier. `LocalParquetArchiver` already in hist_ingest_controller.py — swap for `S3ParquetArchiver` when AWS credentials configured. Interface is identical.


**History:** v1=STUBBED — LocalParquetArchiver interface ready in hist_ingest_controller.py | v2=STUBBED | v3=STUBBED | v4=STUBBED | v5=STUBBED | v6=STUBBED | v7=STUBBED — see ENH-52b | 2026-04-19=STUBBED (see ENH-52b)

---

### ENH-33: Pure-Python Black-Scholes IV Engine (NEW)

| Field | Detail |
|---|---|
| Source | V18D session — built as part of backfill pipeline |
| Status | **PRODUCTION** — built, validated, deployed |
| Dependency | None — uses only Python standard library (math module) |
| Priority Tier | 1 |
| Commercial Relevance | Internal foundation — enables ENH-09 Heston calibration |

**What it does:** Computes Black-Scholes implied volatility (bisection solver), BS gamma, and signed GEX from option price, strike, spot, expiry, and risk-free rate. No external dependencies — uses only `math.erfc`, `math.log`, `math.sqrt`, `math.exp`.

**Validated values (2025-10-15 NIFTY 24000 PE):**
- Input: S=25218, K=24000, P=18, T=8d, r=6.5%
- Output: IV=21.46%, gamma=0.000134, GEX contribution=6.94bn
- Convergence: |price diff| < Rs 0.001 in ≤100 bisection iterations

**Architecture significance:**
1. Foundation for the Heston calibration layer (ENH-09) — Heston fits to market IVs, which this engine provides
2. Real-time IV cross-validation against Dhan-provided IV values
3. Fallback IV computation if Dhan IV feed is unavailable
4. Enables IV computation on any option bar wherever open/high/low/close data exists

**Location:** `backfill_gamma_metrics.py` (functions: `implied_vol`, `bs_gamma_greek`, `bs_price`, `norm_cdf`, `norm_pdf`). Should be extracted to a shared `core/bs_engine.py` module in a future session to enable reuse across scripts.

**Known limitation:** Uses constant 6.5% risk-free rate. ENH-07 (basis-implied rate) would improve accuracy.


**History:** v2=PRODUCTION — built, validated, deployed | v3=PRODUCTION — built, validated, deployed | v4=PRODUCTION | v5=PRODUCTION | v6=PRODUCTION | v7=PRODUCTION

---

### ENH-34: Live Monitoring Dashboard (NEW)

| Field | Detail |
|---|---|
| Source | V18D session — built in response to operational blindness during market hours |
| Status | **PRODUCTION** — built and deployed |
| Dependency | None |
| Priority Tier | 1 |
| Commercial Relevance | Internal operational infrastructure · Pattern reusable for customer-facing status page |

**What it does:** Python HTTP server at `localhost:8765`. Auto-refreshes every 30 seconds. Shows:
- Pipeline stages per symbol (NIFTY/SENSEX): options → gamma → volatility → momentum → market_state → signal — each with status, last timestamp, age
- Component heartbeats: supervisor, runner, telemetry, alert daemon — alive/dead + last beat age
- Supabase table freshness: 5 core tables with last row timestamp and lag
- Latest signals: action, confidence, trade_allowed per symbol
- Action buttons: start supervisor, run preflight, refresh token, run health check, start tape — all triggerable without terminal access

**Architectural significance:**
- Eliminates operational blindness during 6-hour market window
- Action buttons enable intervention without terminal — critical for distracted-operator scenarios
- Architecture (HTTP server + collect_data + build_html) is reusable pattern for a customer-facing signal status page (ENH-23/24)
- No JavaScript required — uses HTML meta refresh for reliability in all browser environments

**Task Scheduler:** `MERDIAN_Live_Dashboard` — AtLogOn trigger, `--no-browser` flag. Opens at `http://localhost:8765`.

**Enhancement path:** Future improvements could include WebSocket push updates (eliminate 30s polling lag), mobile-responsive layout, Telegram alert integration for off-screen alerts, and a password-protected version for remote access.


**History:** v2=PRODUCTION — built and deployed | v3=PRODUCTION — built and deployed | v4=PRODUCTION | v5=PRODUCTION | v6=PRODUCTION | v7=PRODUCTION

---

### ENH-35: Historical Signal Validation

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

Full year results: NIFTY 244 signals, 58.6% T+30m accuracy. 6 signal engine changes applied. Do not re-run.


**History:** v2=NOT BUILT — next priority | v3=NOT BUILT — next priority | v4=COMPLETE — three validation runs 2026-04-11 | v5=COMPLETE | v6=COMPLETE | v7=COMPLETE

---

### ENH-36: hist_* to live 1-min spot promotion

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | capture_spot_1m.py, MERDIAN_Spot_1M Task Scheduler task |

**What was built:** `capture_spot_1m.py` calls Dhan IDX_I every minute, writes to `market_spot_snapshots` (live spot for dashboard) and `hist_spot_bars_1m` (synthetic 1-min bar O=H=L=C=spot for ICT detector). `MERDIAN_Spot_1M` Task Scheduler task fires every minute 09:14–15:31 IST Mon–Fri. Dashboard refresh lowered to 60s. ICT detector will have live bars from 09:14 onwards — first zones expected ~09:30.


**History:** v2=NOT BUILT | v3=NOT BUILT | v4=NOT BUILT | v5=NOT BUILT | v6=NOT BUILT | v7=COMPLETE

---

### ENH-37: ICT Pattern Detection Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

All components live. MTF hierarchy confirmed. 1H zones (MEDIUM) confirmed adds edge.


**History:** v4=COMPLETE — 2026-04-11 | v5=COMPLETE | v6=COMPLETE | v7=COMPLETE

---

### ENH-38: Live Kelly Tiered Sizing

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

End-to-end: runner → ict_zones → signal_snapshots. Strategy C (Half Kelly). See v6 for full detail.


**History:** v4=PARTIAL — multiplier logic in ENH-37 ICT tier assignment | v5=PROPOSED — next live build | v6=COMPLETE | v7=COMPLETE

---

### ENH-39: Capital Ceiling Enforcement

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

Floor ₹10K (lowered for trial). Freeze ₹25L. Hard cap ₹50L.


**History:** v5=PROPOSED — implement with ENH-38 | v6=COMPLETE | v7=COMPLETE

---

### ENH-40: Signal Rule Book v1.1

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | docs/research/MERDIAN_Signal_RuleBook_v1.1.md |

13 rule changes. See v6 for full detail.


**History:** v5=PROPOSED — document update required | v6=COMPLETE | v7=COMPLETE

---

### ENH-41: BEAR_OB DTE Gate — Combined Structure

| Field | Detail |
|---|---|
| Status | **DOCUMENTED — code pending execution layer** |
| Updated | 2026-04-13 |

Rule in Signal Rule Book v1.1 Section 2.2. Code pending Phase 4 execution layer.


**History:** v5=PROPOSED | v6=DOCUMENTED — code pending execution layer | v7=DOCUMENTED — code pending execution layer | 2026-04-19=DOCUMENTED -- code pending execution layer

---

### ENH-42: Session Pyramid — Deferred

| Field | Detail |
|---|---|
| Status | **DEFERRED** |
| Priority Tier | 2 |

Post-Phase 4 with WebSocket real-time prices.


**History:** v4=PROPOSED | v5=DEFERRED — post ENH-38 stable | v6=DEFERRED — post ENH-42 WebSocket | v7=DEFERRED

---

### ENH-43: Signal Dashboard

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| File | C:\GammaEnginePython\merdian_signal_dashboard.py (port 8766) |

Signal timestamp UTC→IST fixed. Spot reads from signal_snapshots. 60s auto-refresh.


**History:** v6=COMPLETE | v7=COMPLETE

---

### ENH-44: Capital Management

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

set_capital.py + dashboard SET input. Floor ₹10K.


**History:** v6=COMPLETE | v7=COMPLETE

---

### ENH-45: hist_spot_bars_1m Zerodha Backfill

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |

Apr 7–10 + Apr 13: 3,750 rows total. ICT detector has full backtest coverage.


**History:** v6=COMPLETE | v7=COMPLETE

---

### ENH-46: Process Manager

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | merdian_pm.py, merdian_start.py, merdian_stop.py, merdian_status.py |

**What was built:**
- `merdian_pm.py` — core: start background (no terminal), PID registry `runtime/merdian_pids.json`, stop, status, duplicate detection, port conflict check
- `merdian_start.py` — morning startup: Step 0 auto-inserts trading_calendar row (permanent V18A-03 fix), Step 1 kills all, Step 2 starts all 3 processes in background
- `merdian_stop.py` — kills all registered + unregistered instances of all MERDIAN scripts
- `merdian_status.py` — shows PIDs, uptime, port, alive/stopped, duplicate warnings. `--watch` mode.
- Health monitor: MERDIAN Processes panel added (PID/status/port per process, duplicate warning)

**Zero terminal windows needed.** All logs in `logs/pm_<name>.log`. Morning startup is one command: `python merdian_start.py`.


**History:** v7=COMPLETE

---

### ENH-47: MERDIAN_PreOpen Task (C-07b permanent fix)

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Closes | C-07b (pre-open capture gap — open since 2026-04-06) |

`MERDIAN_PreOpen` Task Scheduler task fires at 09:05 IST Mon–Fri, runs `capture_spot_1m.py` once. Captures NIFTY + SENSEX spot before supervisor starts at 09:14. This row becomes the session open price for `ret_session` computation. C-07b permanently closed.

---

## Summary Table — Full Register

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | **COMPLETE** |
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
| ENH-36 | hist_* to live 1-min spot | 1 | **COMPLETE** |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | **COMPLETE** |
| ENH-39 | Capital ceiling enforcement | 1 | **COMPLETE** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **COMPLETE** |
| ENH-41 | BEAR_OB DTE gate — combined structure | 1 | DOCUMENTED — code pending |
| ENH-42 | Session pyramid | 2 | DEFERRED |
| ENH-43 | Signal dashboard | 1 | **COMPLETE** |
| ENH-44 | Capital management | 1 | **COMPLETE** |
| ENH-45 | hist_spot_bars_1m Zerodha backfill | 1 | **COMPLETE** |
| ENH-46 | Process Manager | 1 | **COMPLETE** |
| ENH-47 | MERDIAN_PreOpen task | 1 | **COMPLETE** |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

---

*MERDIAN Enhancement Register v7 — 2026-04-13 (evening) — Living document, commit to Git after every update*
*Supersedes v6 (2026-04-13 morning). Commit alongside Open Items Register v8 and session log update.*


**History:** v7=COMPLETE

---

### ENH-48: Phase 4A Execution Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-13 |
| Files | merdian_trade_logger.py · merdian_exit_monitor.py |

Manual execution layer. Signal fires → operator clicks LOG TRADE on dashboard → enters premium → trade_log + exit_alerts written. Exit monitor polls every 30s, fires Telegram at T+30m. CLOSE TRADE updates PnL and capital_tracker.


**History:** v7=COMPLETE

---

### ENH-49: Phase 4B — Semi-Auto Order Placement

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-15 |
| Files | merdian_order_placer.py (AWS port 8767) |
| Dhan IP | 13.63.27.85 (Elastic IP, permanent, whitelisted in Dhan) |

merdian_order_placer.py on MERDIAN AWS. Endpoints: POST /place_order, POST /square_off, GET /margin, GET /health. Downloads Dhan scrip master (streaming, no OOM). Finds security_id by streaming CSV match on exchange=NSE/BSE, segment=D, OPTIDX, trading_symbol prefix, expiry_date, strike, option_type. Places MARKET INTRADAY order. Polls fill. Writes trade_log + exit_alerts. Updates capital_tracker on square off. Dashboard PLACE ORDER button (yellow) routes to AWS order placer via AWS_ORDER_PLACER_URL. Dashboard SQUARE OFF button routes to /square_off. Scrip master refreshed daily (delete runtime/dhan_scrip_master.csv before market open).


**History:** v7=COMPLETE

---

### ENH-50: Phase 4C — Full Auto

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Gate | Phase 4B stable + 2–4 weeks real fill data + slippage analysis |

Full automated execution without operator confirmation. Signal fires → order placed → exit at T+30m automatically.


**History:** v7=PROPOSED

---

### ENH-51: WebSocket Feed + AWS Cloud Migration
**Status: PROPOSED**
**Added: 2026-04-13**

#### Architecture Decision

Dhan WebSocket (`wss://api-feed.dhan.co`) replaces 5-min REST option chain polling.
AWS becomes primary compute. Local becomes dashboard-only.
Zerodha evaluated and rejected — no SENSEX F&O coverage.

#### Why Dhan WebSocket over Zerodha KiteTicker

| Dimension | Dhan | Zerodha |
|---|---|---|
| Subscription limit | 100 instruments | 3,000 instruments |
| NIFTY options | ✅ | ✅ |
| SENSEX options | ✅ | ❌ Not available |
| Authentication | Existing token (no change) | Separate API subscription INR 2K/month |
| Integration effort | Low (already integrated) | High (new broker API) |

SENSEX is non-negotiable for MERDIAN. Dhan is the only option.

#### Instrument Subscription Strategy

Subscribe at session open via one REST call to get security_ids, then maintain WebSocket connection:

| Instrument | Count |
|---|---|
| NIFTY spot (security_id 13) | 1 |
| SENSEX spot (security_id 51) | 1 |
| NIFTY ATM ±15 strikes CE+PE | 30 |
| SENSEX ATM ±15 strikes CE+PE | 30 |
| Buffer | 38 |
| **Total** | **62 of 100 limit** |

±15 strikes covers ~750 NIFTY points intraday — handles 99% of sessions without resubscription.
GEX accuracy: ~75-80% vs 100% with full chain. Acceptable for directional signals.
Flip_level computation: slightly less precise but directionally correct.

#### Migration Phases

**ENH-51a — ws_feed.py on AWS (1 session)**
- `ws_feed.py`: connects to Dhan WebSocket at 09:14 IST
- Startup: one REST call to get current expiry security_ids for ATM ±15 strikes
- Subscribes 62 instruments
- Writes ticks to `atm_option_ticks` Supabase table (new)
- Reconnects automatically on drop (exponential backoff)
- Replaces `capture_spot_1m.py` for spot (writes hist_spot_bars_1m from ticks)

**ENH-51b — Promote AWS runner to full pipeline (1 session)**
- Modify `run_merdian_shadow_runner.py` to read from `atm_option_ticks` instead of REST option chain
- AWS runs full pipeline: ingest → gamma → vol → momentum → signal
- Local still runs in parallel (validation phase)
- Gate: 5 sessions where AWS signal matches local within 2 confidence points

**ENH-51c — AWS as primary, local as shadow (2 weeks validation)**
- Flip: AWS writes to live tables, local writes to shadow tables
- Monitor divergence daily
- Gate: 10 clean sessions as primary

**ENH-51d — Local cutover (1 session)**
- Turn off local runner, local breadth ingest, local capture tasks
- Local machine: dashboards only (reads Supabase — already works)
- AWS: full pipeline + WebSocket feed

#### New Table Required

```sql
CREATE TABLE atm_option_ticks (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ts           timestamptz NOT NULL DEFAULT now(),
  symbol       text NOT NULL,
  security_id  int NOT NULL,
  instrument   text NOT NULL,   -- SPOT / CE / PE
  strike       int,
  expiry_date  date,
  ltp          numeric NOT NULL,
  volume       bigint,
  oi           bigint,
  bid          numeric,
  ask          numeric
);
CREATE INDEX idx_atm_ticks_symbol_ts ON atm_option_ticks (symbol, ts DESC);
```

#### TOTP / Token Impact

No change. WebSocket authenticates with the same daily Dhan token.
Token refresh: existing cron at 08:15 IST (Local) + 08:35 IST (AWS pull) unchanged.
One WebSocket connection per session — no per-call token overhead.

#### Benefits vs Current Architecture

| Metric | Current (REST) | With WebSocket |
|---|---|---|
| Data freshness | 5-min snapshots | Real-time ticks |
| Spot update | 5-min (capture_spot_1m) | Every tick |
| Premium at signal time | Estimated or 5-min stale | Live |
| ICT detector input | 1-min synthetic bars | Real 1-min bars from ticks |
| 429 rate limit risk | Yes | No |
| AWS dependency on Local | Full (all data comes from Local) | None |
| Local machine required | Yes (runner + data) | Dashboards only |

#### Dependencies

- ENH-48 Phase 4A stable (live trade data to validate signal quality)
- Phase 4B (ENH-49) ideally live before cutover (need live fills to validate)
- Estimated start: after 2-4 weeks of Phase 4A data

---

*ENH-51 added 2026-04-13 — WebSocket + AWS migration*


**History:** v7=PROPOSED | 2026-04-19=IN PROGRESS (51a COMPLETE)

---

### ENH-51a -- ws_feed_zerodha.py on AWS — NIFTY full chain

Sub-item of ENH-51 (WebSocket Feed + AWS Cloud Migration). See ENH-51 block for context.

### ENH-51b -- Dhan REST stays for SENSEX — no change

Sub-item of ENH-51 (WebSocket Feed + AWS Cloud Migration). See ENH-51 block for context.

### ENH-51c -- AWS runner reads from Zerodha ticks (NIFTY)

Sub-item of ENH-51 (WebSocket Feed + AWS Cloud Migration). See ENH-51 block for context.

### ENH-51d -- AWS primary, local dashboards-only

Sub-item of ENH-51 (WebSocket Feed + AWS Cloud Migration). See ENH-51 block for context.

### ENH-51e -- MeridianAlpha intraday WebSocket

Sub-item of ENH-51 (WebSocket Feed + AWS Cloud Migration). See ENH-51 block for context.

### ENH-51f -- Unified portfolio management layer

Sub-item of ENH-51 (WebSocket Feed + AWS Cloud Migration). See ENH-51 block for context.

### ENH-52: Dhan Expired Options 5-Year Backfill

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-14 |
| Gate | Phase 4B stable |

Use Dhan Data API expired options endpoint to extend hist_option_bars_1m back to 2021. Provides 1-min OHLCV + IV + OI for NIFTY/SENSEX expired contracts. Constraint: ATM-relative strikes (ATM±10 for indices). Requires mapping ATM-relative → absolute strike using hist_spot_bars_1m spot prices. 30-day chunks. Current dataset is 1 year (Apr 2025–Mar 2026). 5-year extension adds COVID recovery, rate cycle, and multiple volatility regime data.


**History:** v7=PROPOSED

---

### ENH-52b: S3 Warm Tier Archiver (was HIST-02)

| Field | Detail |
|---|---|
| Status | **DEFERRED — Phase 5** |
| Added | 2026-04-15 (moved from OI register HIST-02) |

LocalParquetArchiver stubbed at C:\GammaEnginePython\data\warm_tier\. S3ParquetArchiver pending AWS credentials and bucket setup. Not blocking any current pipeline. DuckDB backtest harness on S3 Parquet also deferred. Build after Phase 4C stable.


**History:** v7=DEFERRED — Phase 5 | 2026-04-19=DEFERRED (Phase 5)

---

### ENH-53: Remove breadth regime as hard gate

| Field | Detail |
|---|---|
| Status | **COMPLETE (PROMOTED)** — 2026-04-19 |
| Promoted | 2026-04-19 |
| Commits | 8f70822 (build, flag default off), e986cbb (flag default on) |
| Evidence | Experiment 25 (5m): WR spread = 1.0pp across BULLISH/BEARISH/NEUTRAL regimes. Pure noise. BEAR_OB on BULLISH days: 51.0% (better than BEARISH 45.0%). Gate directionally backwards. |
| Validation | 2026-04-19 historical replay on 2026-03-16/20/24/25: SENSEX 25/169 (14.8%) V4_OPENED rows, all BEARISH breadth + BULLISH momentum + SHORT_GAMMA. NIFTY 1/171 V4_OPENED (LONG_GAMMA-dominated window). 0 errors, 0 OTHER, trade_allowed-flip check empty. |
| Build | `build_trade_signal_local.py`: (1) new helper `infer_direction_bias_v4(momentum_direction)` replaces `infer_direction_bias(breadth, momentum)` under V4; (2) old +20 implicit alignment bonus skipped under V4; (3) post-action V4-only block adds +5 confidence when breadth aligns with action, 0 otherwise. |
| Flag | MERDIAN_SIGNAL_V4 — kept as hot-rollback escape hatch. Default "1". Override to "0" for V3 legacy. |
| Depends on | ENH-55 (implemented in same session) |


**History:** v7=COMPLETE (PROMOTED) — 2026-04-19 | 2026-04-19=COMPLETE (PROMOTED)

---

### ENH-54: HTF Sweep Reversal Trade Mode

| Field | Detail |
|---|---|
| Status | **REJECTED** — 2026-04-19 |
| Rejected | 2026-04-19 (closing this session; decided 2026-04-17/18 per V18H_v2) |
| Added | 2026-04-15 |
| Priority | Tier 2 — was post Phase 4B stable |
| Original gate | Experiment 17 (backtest) must validate edge before any build |
| Reason for rejection | Experiments 23 / 23b / 23c (2026-04-17/18 V18H_v2 session) tested sweep reversal across the full year. Baseline 17-19% WR. 23b HTF confluence filter: no lift. 23c quality filter: no lift. Hypothesis rejected. Discretionary trades remain possible (the 2026-04-17 live NIFTY BUY_CE sweep reversal was a manual call), but the pattern does not generalize into an automated signal. |
| Do not revisit without | New evidence and a distinct experimental setup; simple variants already tested. |
| Depends on | ENH-49 (Phase 4B live), hist_ict_htf_zones (breach-filtered, live) |

**Observation:**
The Apr 7-8 2026 tariff shock produced a textbook weekly JUDAS_BEAR — price swept below W BULL_OB at 71,948 (SENSEX) to ~71,500, grabbed sell-side liquidity, reversed sharply and rallied 6,600 points to 78,111 over 5 sessions. MERDIAN's T+30m exit would have captured only the first 30 minutes of a multi-session expansion. Current-week options at DTE≤2 are inappropriate for multi-session holds due to theta acceleration.

**What changes:**

1. **Weekly sweep detection** — new logic in detect_ict_patterns_runner.py:
   - If today's session low < W BULL_OB zone_low AND session close > zone midpoint → flag WEEKLY_SWEEP_REVERSAL (bullish)
   - If today's session high > W BEAR_OB zone_high AND session close < zone midpoint → flag WEEKLY_SWEEP_REVERSAL (bearish)
   - Requires hist_ict_htf_zones (already live) for zone lookup

2. **DTE-aware option selection** — modify option selection in order placer:
   - DTE ≥ 4: current week expiry (current behaviour)
   - DTE < 4 OR WEEKLY_SWEEP_REVERSAL: next week expiry (DTE ~8-10)
   - Scrip master streaming already supports next-week lookup

3. **Zone-based exit** — replace T+30m for sweep reversal entries:
   - Primary exit: first opposing HTF zone (BEAR_OB/PDH above for longs)
   - Secondary exit: T+2 sessions if no zone reached
   - Hard stop: if price re-enters the sweep zone (reversal failed)

4. **Sizing** — TIER1 (highest conviction) for confirmed weekly sweeps

**Confirmation hierarchy (all preferred, minimum 2 of 4):**
1. Price closes back inside W BULL_OB/BEAR_OB (primary — required)
2. JUDAS_BEAR/BULL confirmed at T+15m intraday (secondary)
3. WCB transitioning BEARISH→TRANSITION or NEUTRAL→BULLISH (tertiary)
4. VIX declining intraday after sweep (context)

**Experiment 17 required before build:**
- Dataset: full year hist_spot_bars_1m + hist_ict_htf_zones
- Identify all sessions where price swept a W BULL_OB or BEAR_OB and closed back inside
- Score with next-week ATM CE/PE using hist_option_bars_1m
- Exit rules: first opposing HTF zone OR T+2 sessions
- Compare vs current T+30m same-week option
- Hypothesis: HTF sweep reversals with zone-based exit significantly outperform T+30m

**What we are NOT doing until Experiment 17 validates:**
- No code changes to detect_ict_patterns_runner.py
- No changes to option selection logic
- No changes to exit monitor
- No execution layer changes

**Expected edge (hypothesis only — unvalidated):**
The Apr 7-8 move suggests sweep reversals from W zones are high-conviction multi-session trades. If Experiment 17 confirms this across the full year, the edge could be substantially larger than standard ICT pattern trades (+58-107% validated in Experiments 2-16).

---

## v8 Appended 2026-04-19 -- V18H_v2 ENH + OI migration

V18H_v2 (2026-04-17/18) proposed ENH-43..47 and OI-11..15. These collided
with existing COMPLETE items in v7 and with the permanently-closed
OpenItems Register (closed 2026-04-15). Per new numbering convention
(Documentation Protocol v2): ENH IDs are monotonic in this register; no
new OI-* series may be created. V18H_v2 items are renumbered and OI
content is folded into the matching ENH entries below.

| V18H_v2 label | Canonical | Disposition |
|---|---|---|
| ENH-43 + OI-11 | **ENH-53** | folded; OI-11 content is ENH-53 Build field |
| ENH-44 + OI-12 | **ENH-55** | folded; OI-12 content is ENH-55 Build field |
| ENH-45 + OI-15 | **ENH-56** | folded; OI-15 content is ENH-56 Monitoring field |
| ENH-46 | **ENH-57** | COMPLETE record only |
| ENH-47 | **ENH-58** | COMPLETE record only |
| OI-13 | **ENH-59** | promoted to full ENH (patch script syntax rule) |
| OI-14 | (none) | session task, tracked in session_log only |

Errata: `docs/appendices/V18H_v2_RENUMBERING_NOTE.md`. V18H_v2.docx is
NOT modified.


**History:** v7=REJECTED — 2026-04-19 | 2026-04-19=REJECTED

---

### ENH-55: Momentum opposition hard block

| Field | Detail |
|---|---|
| Status | **COMPLETE (PROMOTED)** — 2026-04-19 |
| Promoted | 2026-04-19 |
| Commits | 8f70822 (build, flag default off), e986cbb (flag default on) |
| Evidence | Experiment 20 (5m): ALIGNED 60.9% WR (N=2,138) vs OPPOSED 38.3% WR (N=2,275). Lift +22.6pp. Consistent across BEAR_OB (63.1/40.4), BULL_OB (59.3/35.9), BULL_FVG (58.6/36.9). |
| Definition | BUY_PE + ret_session < -0.05% = ALIGNED. BUY_CE + ret_session > +0.05% = ALIGNED. \|ret_session\| < 0.05% = NEUTRAL (allow). Mismatch = OPPOSED → block. |
| Validation | 2026-04-19 historical replay on 2026-03-16/20/24/25: V4_BLOCKED = 0 on both symbols. SQL audit of 60-day history: 0 rows where momentum_regime field explicitly opposes ret_session. Opposition block in place as safety rail with no practical fire cases in historical data. Aligned +10 bonus fires on V4_OPENED and aligned-SAME paths. |
| Build | `build_trade_signal_local.py`: (1) if `abs(ret_session) > 0.0005` and action opposes sign of ret_session → action=DO_NOTHING, trade_allowed=False, direction_bias=NEUTRAL; (2) else if aligned → +10 confidence; (3) re-clamp confidence to [0, 100]. |
| Flag | MERDIAN_SIGNAL_V4 — shared with ENH-53. Default "1". |
| Depends on | None — bundled with ENH-53 |


**History:** v7=COMPLETE (PROMOTED) — 2026-04-19 | 2026-04-19=COMPLETE (PROMOTED)

---

### ENH-56: Premium sweep detector (monitor phase)

| Field | Detail |
|---|---|
| Status | **PROPOSED -- MONITOR ONLY, DO NOT BUILD** (was V18H_v2 ENH-45) |
| Added | 2026-04-18 |
| Priority | MEDIUM |
| Evidence | Experiment 27b: PE sweep 0.2-1.0% = 64.5% WR (N=107). Size boundary is critical: large sweeps (>3%) = 49.1% (coin flip); small (<1%) = 64.5%. Momentum-independent (aligned vs opposed: 56.4% vs 57.5% -- no difference). |
| Key insight | Premium sweeps behave differently from spot ICT patterns -- momentum-independent. A separate signal class. |
| Monitoring (was OI-15) | Log live morning PE/CE sweeps <1% from hist_atm_option_bars_5m. Target: 50 live occurrences. Review threshold: build if 60%+ WR sustained. |
| Build gate | 50 live occurrences + 60%+ WR. Not before. |


**History:** v7=PROPOSED -- MONITOR ONLY, DO NOT BUILD (was V18H_v2 ENH-45) | 2026-04-19=PROPOSED (MONITOR ONLY)

---

### ENH-57: MTF OHLCV infrastructure

| Field | Detail |
|---|---|
| Status | **COMPLETE** (was V18H_v2 ENH-46) |
| Completed | 2026-04-17 |
| Tables | hist_spot_bars_5m (41,248 rows), hist_spot_bars_15m (14,072), hist_atm_option_bars_5m (27,082 with pre-computed wick metrics), hist_atm_option_bars_15m (9,601) |
| Scripts | build_spot_bars_mtf.py, build_atm_option_bars_mtf.py, fix_atm_option_build.py, fix_expiry_lookup.py |
| Runtime | ~50 minutes total for full year backfill |
| Key decision | 1m bars are execution-granularity only. All ICT pattern detection uses 5m bars going forward. Evidence: Experiment 23 sweep detection found 0 events on 1m vs 52 on 5m. |


**History:** v7=COMPLETE (was V18H_v2 ENH-46) | 2026-04-19=COMPLETE

---

### ENH-58: hist_pattern_signals table

| Field | Detail |
|---|---|
| Status | **COMPLETE** (was V18H_v2 ENH-47) |
| Completed | 2026-04-17 |
| Table | hist_pattern_signals (6,318 rows, source=backfill_5m) |
| Script | build_hist_pattern_signals_5m.py |
| Key outcome | 52 sweep reversals detected on 5m vs 0 on 1m -- validates timeframe architectural decision. |
| Downstream impact | All future experiments run in <2 minutes vs hours. Experiment 20 ran in 90s vs prior 3.5h baseline (Exp 18 OI wall rebuild). |


**History:** v7=COMPLETE (was V18H_v2 ENH-47) | 2026-04-19=COMPLETE

---

### ENH-59: Patch script syntax validation rule

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-19 |
| Completed | 2026-04-19 |
| Added | 2026-04-17 |
| Priority | MEDIUM |
| Trigger | force_wire_breadth.py (2026-04-16 session) inserted a code block at wrong indent depth in run_option_snapshot_intraday_runner.py. Script exited cleanly at market close; IndentationError only surfaced at next session restart, would have disabled the entire pipeline. |
| Rule | Every `fix_*.py` / `patch_*.py` / `update_*.py` script MUST call `ast.parse(patched_text)` on the in-memory result before writing the target file. If SyntaxError: print error to stderr and `sys.exit(non-zero)`. Script must also validate its own AST on startup. |
| Resolution | Added to MERDIAN_Change_Protocol_v1.md as STEP 1.6 (Patch Script Syntax Gate). Enforced for all patch scripts from 2026-04-19 forward. |
| Reference implementations | fix_enh6061.py, update_registers_enh5355.py, fix_runner_indent.py, fix_atm_option_build.py, fix_expiry_lookup.py. |


**History:** v7=COMPLETE — 2026-04-19 | 2026-04-19=COMPLETE

---

### ENH-60: UnboundLocalError in build_trade_signal_local flow-modifier block

| Field | Detail |
|---|---|
| Status | **OPEN** |
| Opened | 2026-04-19 |
| Priority | MEDIUM |
| Origin | Pre-existing latent bug in `build_trade_signal_local.py`. Exposed during ENH-53/55 backtest — fired on ~0.3% of rows (1/313 NIFTY, varies on SENSEX). Not introduced by V4. |
| Symptom | `UnboundLocalError: cannot access local variable 'action' where it is not associated with a value` — raised in the options-flow confidence-modifier block when pcr_regime/skew_regime/flow_regime is populated AND gamma_regime is not LONG_GAMMA/NO_FLIP. `action` is referenced there before it is assigned in the action-decision block below. |
| Fix | Pre-initialise `action = "DO_NOTHING"` at the top of `build_signal()`, before the gamma-treatment block. Single-line change. Safe default. Track A, not BREAKING. |
| Impact if deferred | Rare signal build failures during live cycles. At ~0.3% error rate: ~1-3 signal drops per trading day. Affected rows never write to signal_snapshots. |
| Build when | Next session — trivial fix |


**History:** v7=OPEN | 2026-04-19=COMPLETE

---

### ENH-61: V3 trade_allowed=True unconditional reset at DTE block

| Field | Detail |
|---|---|
| Status | **OPEN** |
| Opened | 2026-04-19 |
| Priority | LOW |
| Origin | V3 legacy behaviour preserved bit-identical through ENH-53/55 promotion. In `build_signal()`, DTE block sets `trade_allowed = True` unconditionally, overriding the `False` set by LONG_GAMMA/NO_FLIP gamma gate. |
| Symptom | On LONG_GAMMA / NO_FLIP gated rows, `signal_snapshots.trade_allowed` is written as `True` even though `action = DO_NOTHING`. Cosmetically wrong; no trading impact since `action` gates downstream execution. |
| Fix | Initialise `trade_allowed = True` once at function top, then only ever transition it to `False` downward. Remove the unconditional `trade_allowed = True` inside the DTE block. |
| Impact if deferred | None on execution (action is the effective gate). Pollutes signal_snapshots analytics — any filter on `trade_allowed=True` will include gate-blocked DO_NOTHING rows. |
| Build when | Bundle with ENH-60 or next time touching build_trade_signal_local.py |


**History:** v7=OPEN | 2026-04-19=COMPLETE

---

### ENH-62: Shadow runner dead since 2026-04-15

| Field | Detail |
|---|---|
| Status | **OPEN** |
| Opened | 2026-04-19 |
| Priority | MEDIUM |
| Origin | AWS shadow runner last heartbeat 2026-04-15 (per session resume header). Unrelated to ENH-53/55 but blocks the "5 shadow sessions" validation pattern. Historical replay substituted for this session. |
| Symptom | AWS preflight FAILED state; no shadow signal_snapshots rows emitted since 2026-04-15. |
| Fix | Diagnose shadow runner process status on AWS (systemd / supervisor logs), restart if crashed, investigate crash cause if recurring. |
| Impact if deferred | Next build that wants shadow validation must fall back to historical replay (acceptable, proven this session) or live canary (riskier). No immediate blocker. |
| Build when | Before next shadow-required validation, or opportunistically. |

---


**History:** v7=OPEN | 2026-04-19=COMPLETE

---

### ENH-63: IV-scaled lot sizing multiplier

| Field | Detail |
|---|---|
| Status | **REJECTED** -- 2026-04-19 |
| Rejection rationale | `compute_kelly_lots()` in `merdian_utils.py` (ENH-38v2, 2026-04-13) already applies IV scaling via `estimate_lot_cost(spot, atm_iv_pct, dte_days)`. Higher IV -> higher per-lot premium estimate -> fewer lots. Proposed layered multiplier would double-count IV. Today's commit `b2e8078` was a silent-bug repair (duplicate V1 block clobbering V2 output for 6 days) -- filed separately as ENH-65. |
| Added | 2026-04-19 |
| Priority | HIGH — direct execution-layer edge |
| Evidence | Experiment 5 (full year options P&L): BEAR_OB\|HIGH_IV +174.6% exp 86% WR (N=22) vs BEAR_OB\|MED_IV +84.8% exp 100% WR (N=11). BULL_FVG\|LOW_IV -14.3% exp 0% WR (N=23). BULL_OB\|HIGH +67.3% vs BULL_OB\|MED +49.3%. HIGH_IV environments carry MORE edge, not less. |
| Prior context | VIX>20 binary gate was removed (build_trade_signal_local.py line annotation "ENH-35 + Experiment 5"). Intended replacement — IV-scaled lot sizing — is documented in Signal Rule Book v1.1 and session_log R-01 but never built. |
| Build | New helper in `merdian_utils.py`: `iv_size_multiplier(atm_iv: float, pattern: str) -> float`. Returns: atm_iv < 12 → 0.5; 12 ≤ atm_iv < 18 → 1.0; atm_iv ≥ 18 → 1.5. Exception: pattern == 'JUDAS_BULL' → always 1.0 (HIGH_IV degrades Judas edge per Exp 5). Apply in `detect_ict_patterns_runner.py` where `ict_lots_t1/t2/t3` are computed: multiply Kelly lot output by `iv_size_multiplier` then floor to int, min 1. |
| Schema change | None. atm_iv already in market_state_snapshots.volatility_features and signal_snapshots. |
| Flag gate | New env var `MERDIAN_IV_SIZING_V1` (default "0"). Flip to "1" after historical replay validates no regression in ict_zones.ict_lots_* distribution. |
| Validation | Historical replay against ict_zones rows written in last 4 weeks. Compare pre-/post-multiplier lot counts. Expected: 40-50% rows get 1.5× boost (HIGH_IV weeks), 10-15% get 0.5× reduction (LOW_IV periods — rare in current dataset). |
| Risk | If atm_iv is null or zero-ish, multiplier must default to 1.0 (no change). Guard in helper. |
| Depends on | ENH-38 (Kelly tiered sizing — live). |
| Blocks | Live promotion of Candidate A in session 2026-04-19 research handoff. |


**History:** v7=REJECTED -- 2026-04-19 | 2026-04-19=REJECTED

---

### ENH-64: Pre-pattern sequence features + afternoon skip + FVG low-IV downgrade

| Field | Detail |
|---|---|
| Status | **COMPLETE** — 2026-04-19 |
| Completed | 2026-04-19 (commit 3362b8f, code); sub-rule 1 pre-existing |
| Sub-rule 1 | COMPLETE — compute_sequence_features + assign_tier already live in detect_ict_patterns.py before this session. |
| Sub-rule 2 | COMPLETE — BEAR_OB AFTNOON -> SKIP (commit 3362b8f). |
| Sub-rule 3 | COMPLETE — BULL_FVG + atm_iv < LOW_IV_THRESHOLD -> SKIP (commit 3362b8f). Register said TIER3 downgrade; adjusted to SKIP at build time (tier vocabulary is TIER1/TIER2/SKIP; 0% WR N=23 warrants hard skip). |
| Added | 2026-04-19 |
| Priority | MEDIUM-HIGH — tier classifier becomes evidence-driven |
| Scope | Three composable refinements to the ICT tier-classification pipeline. Bundled because all feed `ict_zones.ict_tier` / `ict_size_mult` in `detect_ict_patterns_runner.py`. |
| Sub-rule 1 — Sequence features | Add 3-bar lookback computation in detector. New fields in ict_zones: `seq_mom_yes` (2+ counter-direction bars before OB), `seq_imp_wek` (cumulative preceding impulse < 0.3%), `seq_no_sweep` (no liquidity grab in prior 5 bars). |
| Sub-rule 1 — Evidence | Exp 8: BEAR_OB\|NO_SWEEP\|MOM_YES\|IMP_WEK = +298% exp 100% WR (N=6). BEAR_OB\|MOM_YES alone +187% (N=10) vs MOM_NO +59% (N=19). BEAR_OB\|IMP_WEK +132% (N=23) vs IMP_STR -7.4% (N=6). Momentum alignment is the single strongest filter for BEAR_OB (+83.6pp lift). |
| Sub-rule 1 — Tier promotion | If pattern ∈ {BEAR_OB, BULL_OB} AND seq_mom_yes AND seq_imp_wek AND seq_no_sweep → promote to TIER1 regardless of MTF context. If any single sub-feature missing → default MTF tier logic. |
| Sub-rule 1 — Inversion | BULL_FVG: MOM_NO better than MOM_YES (+30% vs +9%). For FVG patterns, INVERT momentum filter. Flag `seq_mom_inverted = True` for FVG. |
| Sub-rule 2 — BEAR_OB afternoon skip | If pattern == BEAR_OB AND detect_ts IST hour ∈ [13, 14] → `ict_tier = SKIP`, `ict_size_mult = 0`. Evidence: BEAR_OB\|AFTERNOON (13:00-14:30) -24.7% exp 17% WR. Signal Rule Book v1.1 Rule 1 (NEW). |
| Sub-rule 3 — BULL_FVG low-IV downgrade | If pattern == BULL_FVG AND atm_iv < 12 → force `ict_tier = TIER3` (min sizing). Evidence: BULL_FVG\|LOW 0% WR N=23, -14.3% exp. Compose with ENH-63 multiplier (0.5× TIER3 → effectively minimum viable lot). |
| Schema change | ict_zones +3 nullable columns: seq_mom_yes BOOLEAN, seq_imp_wek BOOLEAN, seq_no_sweep BOOLEAN. Backfill NULL for historical rows — only forward-applied. |
| Flag gate | New env var `MERDIAN_SEQ_TIER_V1` (default "0"). |
| Validation | Historical replay against hist_pattern_signals.signal_v4 = true rows. Compare tier distribution pre-/post-change. Expected: 5-10% of BEAR_OB/BULL_OB rows promote to TIER1 (+300% sizing). 100% of afternoon BEAR_OB rows get SKIP (was TIER3 min). BULL_FVG LOW_IV rows — sparse in live data, cosmetic for now. |
| Depends on | ENH-37 (ICT detector — live), ENH-38 (Kelly sizing — live). |
| Could unblock | Refined Signal Rule Book v2.0 once this and ENH-63 ship. |


**History:** v7=COMPLETE — 2026-04-19 | 2026-04-19=COMPLETE

---

### ENH-65: Remove duplicate Kelly-write block + cache expiry index

| Field | Detail |
|---|---|
| Status | **COMPLETE** -- 2026-04-19 |
| Completed | 2026-04-19 (commit `b2e8078`) |
| Priority | HIGH -- silent bug in production signal path |
| Discovery | Session 2026-04-19 investigation of ENH-63 scope. `detect_ict_patterns_runner.py` (436 lines) contained two Kelly-write blocks back-to-back. V2 block (ENH-38v2, commit `c78b6ea` 2026-04-13): IV-aware, calls `compute_kelly_lots(capital, tier, symbol, spot, atm_iv_pct, dte_days)`. V1 block (ENH-38, commit `26c5e72` 2026-04-11): IV-blind, calls `compute_kelly_lots(capital, tier)` positional -- triggers `CAPITAL_PER_LOT=100000` fallback. Both executed each cycle; V1 ran second and overwrote V2's lot counts. IV-scaled sizing had been dead code for 6 days. |
| Root cause | Commit `c78b6ea` (2026-04-13 session) added the V2 block by prepending without deleting V1. Dual-block layout went unnoticed because both executed without error -- result always round-number lots from V1's `CAPITAL_PER_LOT` fallback. |
| Secondary finding | V2 block called `build_expiry_index_simple(sb, inst_id)` every 5-min cycle. That helper issues 12 paginated Supabase queries per call. Runtime impact: ~1,728 queries/day/symbol for a near-static dataset (expiry calendar changes weekly, not every 5 minutes). |
| Build | Single patch `fix_enh63.py` applied to `detect_ict_patterns_runner.py`: (1) delete 85-line duplicate region (2nd Session-start block through V1 end marker); (2) add `_EXPIRY_INDEX_CACHE: dict = {}` at module scope; (3) wrap `build_expiry_index_simple` call with cache lookup keyed by `inst_id`. |
| File delta | 436 -> 370 lines (-75), 18,361 -> 15,262 bytes (-3,099). |
| Schema change | None. |
| Flag gate | None -- straight bug fix, not a toggleable feature. |
| Validation | Pre-commit: `ast.parse()` on patched file passes. Post-commit structural: 1 Session-start block (was 2), 1 V2 end marker, 0 V1 Kelly header, 3 `_EXPIRY_INDEX_CACHE` references (decl + get + set). Runtime verification: Monday 2026-04-21 09:15+ IST -- confirm `ict_zones.ict_lots_t1/t2/t3` values vary with `atm_iv_at_detection` across cycles (was constant under V1 fallback). |
| Environment | Local only. AWS shadow runner has been FAILED since 2026-04-15 -- not DEGRADED gate because AWS never ran this file in the affected window. AWS `git pull` needed before AWS shadow recovery. |
| Depends on | None. |
| Supersedes | ENH-63 (REJECTED -- the IV-scaled multiplier it proposed would have double-counted IV given ENH-38v2's existing IV-aware cost model). |

---

*End of v8 section.*


**History:** v7=COMPLETE -- 2026-04-19 | 2026-04-19=COMPLETE

---


### ENH-66: Trading calendar auto-insert must populate open_time/close_time

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Completed | 2026-04-20 |
| Commit | `8f83859` |
| Priority | HIGHEST — root cause of 2026-04-20 3-hour outage |
| Area | ENV / Operations |
| Session | 1 of re-engineering programme |

**Context.** 2026-04-20 09:15 IST — seven production scripts silently exited "Market holiday" despite it being a trading day. Root cause: V18G holiday-gate logic treats `open_time IS NULL` as "market closed." The `trading_calendar` row auto-inserted by `merdian_start.py` only carried `{trade_date, is_open=True}` — leaving `open_time` and `close_time` NULL. Scripts interpreted the missing times as a holiday signal and exited cleanly with code 0. Windows Task Scheduler, supervisor, and dashboard all showed green. Pipeline bled out from 09:15 until 11:39 IST when the row was patched live via direct Supabase PATCH.

**Fix.** `ensure_calendar_row()` in `merdian_start.py` patched at two points: (1) INSERT path for new weekday rows — include `open_time='09:15:00'` and `close_time='15:30:00'` in the payload when `is_open=True`; (2) Existing-row branch — if `open_time` or `close_time` is NULL on an `is_open=True` row, PATCH the missing columns before returning success (covers any pre-existing bad rows on subsequent runs). Single authoritative source. Seven downstream gate-reading scripts (`capture_spot_1m.py`, `capture_market_spot_snapshot_local.py`, `compute_iv_context_local.py`, `build_market_spot_session_markers.py`, `ingest_breadth_intraday_local.py`, `run_equity_eod_until_done.py`, `merdian_start.py` itself) left unchanged — their gate logic is correct; they were receiving incomplete data. Also strips a pre-existing UTF-8 BOM from `merdian_start.py` that had been silently blocking `ast.parse()`.

**Validation (live against Supabase).**
- DELETE today's calendar row → `ensure_calendar_row()` re-creates it with both times populated.
- `capture_spot_1m.py` writes NIFTY + SENSEX rows instead of "Market holiday exiting".
- Regression check: `is_open=False` → script correctly exits as holiday (gate logic intact).
- Backfill branch fired on stack restart at 19:44 IST (msg `open_time/close_time backfilled (ENH-66)`).

**History:** 2026-04-20=COMPLETE

---


### ENH-67: latest_market_breadth_intraday is a VIEW — dashboard shows stale counter

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-20 |
| Priority | MEDIUM (cosmetic — signal engine uses `wcb_regime` which is correct) |
| Area | DASHBOARD |
| Was tracked as | C-08 in permanently-closed OpenItems Register |
| Targets | Session 6 of programme |

**Context.** Dashboard card "Market Breadth — NSE Universe" shows `▲ 1,265 ADV ▼ 54 DEC BULLISH` for multiple hours on 2026-04-20 despite VRD Nation advance-decline chart and WCB weighted aggregate both showing BEARISH. Diagnosis: `latest_market_breadth_intraday` is a PostgreSQL VIEW, not a TABLE. `ingest_breadth_intraday_local.py` upserts appear to fail silently. The view returns whatever was last successfully written elsewhere (stale pre-market seeded row).

**Proposed fix options.**
- A. Convert view → table; migrate ingest writes to match.
- B. Repoint `ingest_breadth_intraday_local.py` to write to a new proper table; leave view for legacy consumers.
- C. Dashboard reads `wcb_regime` rollup instead of `latest_market_breadth_intraday` universe counter.

Recommend B + C. Not fixing immediately because signal engine already uses `wcb_regime` for gating decisions (per ENH-53 breadth removal from hard gate), so the inversion is display-only and did not contribute to today's outage.

**History:** 2026-04-20=PROPOSED

---


### ENH-68: Runner re-reads .env per cycle (tactical stopgap)

| Field | Detail |
|---|---|
| Status | **COMPLETE (tactical)** — strategic replacement at ENH-74 |
| Completed | 2026-04-20 |
| Commit | `b195499` |
| Priority | HIGH — root cause of 2026-04-20 60-minute outage from 11:26 to 12:26 IST |
| Area | SIGNAL / Runner |
| Session | 1 of re-engineering programme |

**Context.** Runner process started at 09:15:34 loads `.env` once at startup via `load_dotenv()`. When `refresh_dhan_token.py` rewrote `.env` at 11:00 IST, the runner continued using its stale in-memory `DHAN_API_TOKEN`. Every subsequent cycle's option-chain ingest failed Dhan 401, which the V18A-02 circuit-breaker correctly halted. Only `merdian_stop.py` + `merdian_start.py` picked up the new token. 60 minutes of cycles lost.

**Fix (tactical, Option B of four considered).** Add guarded `load_dotenv(override=True, dotenv_path=BASE_DIR / ".env")` call at top of `run_full_cycle()` in `run_option_snapshot_intraday_runner.py`. One reload per 5-minute cycle. Log line `ENH-68: .env reloaded for this cycle (override=True)` written every cycle for audit trail. Graceful degradation with `_load_dotenv = None` if python-dotenv unavailable.

**Options considered and rejected.**
- A (flag file): adds coordination surface between two scripts; Windows file-race risk; rejected.
- C (per-use helper `get_dhan_token_live()`): fixes token instance, not class of bug; rejected.
- D (proper fix — `core/live_config.py`): 1-day refactor touching 50-80 call sites. Worth doing properly; separated as ENH-74 (Session 5).

**Validation.**
- 6 ENH-68 markers at expected line numbers (import at line 16, reload block lines 495-509).
- `ast.parse()` OK, module import OK, python-dotenv available.
- Stack restarted at 19:44 IST — runner picks up patched code.
- Live validation awaits Tuesday 09:15 IST: expect `ENH-68: .env reloaded` log line on every cycle. Any .env rotation (token, flags, caps, credentials) picked up within ≤5 minutes with no runner restart.

**Strategic replacement.** ENH-74 (Session 5) introduces `core/live_config.py` with 30s TTL-cached accessors. When that lands, this patch is removed.

**History:** 2026-04-20=COMPLETE (tactical)

---


### ENH-69: Supervisor staleness threshold shorter than cycle duration

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-20 |
| Priority | LOW — cosmetic, runner survives, children exit cleanly |
| Area | OPS / Supervisor |
| Targets | Session 6 of programme |

**Context.** Supervisor health check runs every 60s; observed cycle duration 146.6s (logged `CYCLE END — duration=146.6s`). When the runner's work extends past supervisor's heartbeat-age threshold, supervisor considers runner dead and spawns a replacement. The new process detects the real runner holds the lock and exits cleanly with `Another runner appears active (pid=..., stale=False, heartbeat_age=...). Exiting.` Pattern fills `pm_supervisor.log` with "Runner not healthy: Runner lock missing pid" every minute despite runner being perfectly alive.

**Proposed fix options.**
1. Widen supervisor heartbeat threshold to `max(180s, 2 × longest_observed_cycle_duration)`.
2. Richer liveness signal (process running AND lock file present AND lock mtime within N seconds), not heartbeat_age alone.
3. Runner writes more frequent heartbeats during long steps (every 15s during ingest, per-child-process finish).

Recommend option 3 — aligns with per-step visibility that `script_execution_log` (ENH-71) already provides.

**Depends on:** ENH-71.

**History:** 2026-04-20=PROPOSED

---


### ENH-70: Preflight is theater — rewrite as dry-run contract enforcement

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-20 |
| Priority | HIGH — allowed today's bugs to ship undetected |
| Area | OPS / Preflight |
| Targets | Session 4 of programme |

**Context.** Preflight PASSED at 08:53 IST on 2026-04-20 while the holiday-gate bug was already latent in `trading_calendar` and about to break 7 production scripts. Preflight checks: Python imports succeed, Supabase REST responds, Dhan IDX_I returns one probe, file presence on disk. None of these caught a script that silently exits 0 on a trading day.

**Proposed fix (Session 4).** Add `--dry-run` flag to each critical script. Invoked with dry-run, script writes to a shadow schema (`_preflight_market_spot_snapshots`, etc.) with 1-hour TTL, but still exercises all gate logic, all API calls, all decision paths. `ExecutionLog` (ENH-71) records the invocation with `exit_reason='DRY_RUN'` and computes `contract_met` against actual writes to shadow tables. Preflight stage:

1. Generates one `invocation_id` per script.
2. Spawns `python <script> --dry-run --invocation-id <uuid>` per script.
3. Polls `script_execution_log` for the matching `invocation_id`.
4. FAILs preflight if `contract_met=FALSE` for any critical script.

Today's bug replayed under new preflight: `capture_spot_1m.py --dry-run` would hit the holiday gate, return `exit_reason='HOLIDAY_GATE'` with `contract_met=False` (expected writes declared but not delivered), and fail preflight with the explicit reason. 08:53 IST crash, not 09:15 IST silent outage.

**Depends on:** ENH-71 + ENH-72.

**History:** 2026-04-20=PROPOSED

---


### ENH-71: Write-contract layer (foundation)

| Field | Detail |
|---|---|
| Status | **COMPLETE** (layer + reference implementation); propagation at ENH-72 |
| Completed | 2026-04-20 |
| Commit | `260c7d0` |
| Priority | FOUNDATIONAL — unblocks ENH-70, ENH-72, ENH-73 |
| Area | OPS / Observability |
| Session | 2 of re-engineering programme |

**Context.** Today's 3-hour silent outage was possible because MERDIAN has no write-contract enforcement. Scripts declare success by exit code 0; nothing verifies they wrote the rows they were supposed to. "Script succeeded" and "script did nothing and claimed success" are indistinguishable to every observer — dashboard, supervisor, Task Scheduler, alert daemon.

**What shipped.**

1. **Table** `public.script_execution_log` with closed-set `exit_reason` CHECK constraint. Columns: `id`, `script_name`, `invocation_id` (unique), `host`, `symbol`, `trade_date`, `started_at`, `finished_at`, `duration_ms`, `exit_code`, `exit_reason`, `contract_met`, `expected_writes jsonb`, `actual_writes jsonb`, `notes`, `error_message`, `git_sha`. Valid `exit_reason` values: `SUCCESS`, `HOLIDAY_GATE`, `OFF_HOURS`, `TOKEN_EXPIRED`, `DATA_ERROR`, `SKIPPED_NO_INPUT`, `DEPENDENCY_MISSING`, `CRASH`, `TIMEOUT`, `RUNNING`, `DRY_RUN`. Adding a new value requires explicit migration. Partial indexes on `contract_met=false` and `exit_reason <> 'SUCCESS'` keep them tiny at scale.

2. **View** `public.v_script_execution_health_30m` for dashboard/alert consumption. Per-script rollup: `invocations`, `successful`, `failed`, `in_flight`, `success_pct`, `last_run`, `last_exit_reason` over last 30 min.

3. **Helper class** `core.execution_log.ExecutionLog`. API: `record_write(table, n)`, `exit_with_reason(reason, exit_code, notes, error_message)`, `complete(notes)`. Opening row INSERTed at construction (`exit_reason='RUNNING'`, `contract_met=NULL`). `complete()` / `exit_with_reason()` PATCH with final fields and compute `contract_met`. `atexit` hook catches unhandled crashes and writes `exit_reason='CRASH'` with captured traceback. Invalid exit_reasons coerced to CRASH with error_message — developer bugs become visible, not suppressed. Best-effort Supabase writes (warn to stderr on failure); ExecutionLog must never break the calling script.

4. **Reference implementation:** `capture_spot_1m.py` converted. Declares `expected_writes={market_spot_snapshots: 2, hist_spot_bars_1m: 2}`. Env-var check → `DEPENDENCY_MISSING`. Holiday gate → `HOLIDAY_GATE` (today's silent exit now loud; `contract_met=False` because writes expected but not delivered). Dhan fetch exception classified as `TOKEN_EXPIRED` (401/auth hints) or `DATA_ERROR`. `record_write()` after each successful INSERT/UPSERT. Final return via `log.complete()`.

**Validation (live against Supabase, 2026-04-20 session).**
- Empty table, accessible view, CHECK constraint rejected `INVALID_REASON` (status 400, error code 23514).
- Smoke test: SUCCESS row with `contract_met=True`.
- Contract violation test: expected 3 writes, wrote 1 → `met=False`, `exit_reason=SUCCESS`.
- Crash test: no finalise call → atexit hook → `exit_reason=CRASH`.
- `HOLIDAY_GATE` test: expected writes + zero actual → `met=False`.
- Live run of converted `capture_spot_1m.py`: `SUCCESS met=True`, 2+2 writes, 1114ms, `git_sha='b195499'`.
- Replay of today's exact outage: flipped `is_open=False`, ran script. Row recorded: `reason=HOLIDAY_GATE met=False expected={market_spot_snapshots: 2, hist_spot_bars_1m: 2} actual={} notes='trading_calendar says closed for 2026-04-20'`. **Today's silent exit is now a dashboard-visible, alertable row.**

**Blocks:** ENH-70, ENH-72, ENH-73.

**History:** 2026-04-20=COMPLETE (foundation)

---


### ENH-72: Propagate ExecutionLog to 9 remaining critical scripts

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-20 |
| Priority | HIGH |
| Area | OPS / Observability |
| Depends on | ENH-71 |
| Targets | Session 3 of programme |

**Scope (priority order).**
1. `ingest_option_chain_local.py` — highest write volume; today's Dhan 401 failures become `TOKEN_EXPIRED`-classified rows instead of just log spam and V18A-02 alerts.
2. `ingest_breadth_intraday_local.py` — breadth inversion / stale writes; enables ENH-67 investigation.
3. `capture_market_spot_snapshot_local.py`.
4. `compute_iv_context_local.py`.
5. `build_market_spot_session_markers.py`.
6. `run_equity_eod_until_done.py`.
7. `refresh_dhan_token.py` — records token rotation events (enables ENH-74 validation).
8. `build_ict_htf_zones.py`.
9. `detect_ict_patterns_runner.py` — the "Insufficient bars (0)" silent degrade from this morning becomes `SKIPPED_NO_INPUT`.
10. `build_trade_signal_local.py` — signal producer.

Estimated 20 min per conversion once the ENH-71 pattern is established. Total ~3–4 hours.

**History:** 2026-04-20=PROPOSED

---


### ENH-73: Dashboard truth + alert daemon contract-violation rules

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-20 |
| Priority | MEDIUM |
| Area | DASHBOARD / Alerting |
| Depends on | ENH-71 + ENH-72 |
| Targets | Session 6 of programme |

**Scope.**

Dashboard: new card "Pipeline Data Integrity (last 30 min)" driven by `v_script_execution_health_30m`. Per-stage RED/AMBER/GREEN traffic light based on `success_pct`. Click-through reveals last failure row with `exit_reason`, `expected_writes`, `actual_writes`, `error_message`. Closes the gap where dashboard said "LIVE · 3m 53s ago" today while pipeline was silently broken.

Alert daemon rules (each is a 60s polling query against `script_execution_log`):
- `contract_met=FALSE` during market hours (immediate alert).
- `HOLIDAY_GATE` during market hours rolling count >1 in last N cycles (catches today's exact bug class).
- Cascade detection: script A fails → scripts B, C, D consecutively emit `DEPENDENCY_MISSING`. Alert names the root cause, not the symptoms.
- Freshness: specific table X hasn't received a row in >15 min during market hours.

Also folds in ENH-67 (breadth counter fix) and ENH-69 (supervisor heartbeat richness) as related dashboard-truth improvements.

**History:** 2026-04-20=PROPOSED

---


### ENH-74: Live config layer — core/live_config.py (strategic replacement of ENH-68)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Added | 2026-04-20 |
| Priority | HIGH — eliminates stale-in-memory bug class |
| Area | CORE |
| Depends on | — |
| Replaces | ENH-68 (tactical) |
| Targets | Session 5 of programme |

**Context.** ENH-68 fixes the Dhan token instance of the stale-in-memory bug. But the bug class is broader: any `os.environ[...]` / `os.getenv(...)` read at module import becomes a frozen snapshot. Tokens, feature flags, capital caps, Supabase keys, Telegram credentials — all vulnerable. The runner has ~40 env reads; the repo has 50–80 in total.

**Proposed fix.** Build `core/live_config.py` with function-based accessors backed by 30s TTL-cached `load_dotenv(override=True)`:

```python
def dhan_token() -> str: ...
def dhan_client_id() -> str: ...
def supabase_url() -> str: ...
def supabase_service_key() -> str: ...
def feature_flag(name: str, default: bool = False) -> bool: ...
def capital_per_lot() -> int: ...
```

All config reads go through these functions. 30s TTL — token rotations picked up within one cycle, no perf concern. Thread-safe via `Lock`.

**Migration.** Repo-wide audit of `os.environ[...]` and `os.getenv(...)`. Estimated 50–80 call sites. Replace each with the corresponding `live_config.XXX()` call. Remove ENH-68's per-cycle `load_dotenv` in runner (superseded).

**Validation.**
- Replay 2026-04-20 scenario: runner up, edit `.env` to rotate token, wait 30s, next cycle uses new token.
- Flag-flip test: change `MERDIAN_SIGNAL_V4` in `.env`, flag takes effect within 30s with no restart.
- ExecutionLog records of `refresh_dhan_token.py` events serve as audit trail for token rotations.

Estimated effort: 4–6 hours, repo-wide.

**History:** 2026-04-20=PROPOSED

---


## MERDIAN Re-engineering Programme — triggered 2026-04-20

2026-04-20 outage post-mortem exposed architectural gaps: preflight theater, no write-contract enforcement, stale-in-memory bug class. Six sessions across ~3 weeks. Total ~20–25 hours focused engineering.

| Session | ENH | Status | Duration |
|---|---|---|---|
| 1 — Stop the bleeding | ENH-66, ENH-68 (tactical) | COMPLETE 2026-04-20 | 2h |
| 2 — Write-contract layer | ENH-71 + capture_spot_1m reference | COMPLETE 2026-04-20 | 3h |
| 3 — Propagate to 9 scripts | ENH-72 | PROPOSED | 4–5h |
| 4 — Preflight rewrite | ENH-70 | PROPOSED | 3h |
| 5 — Live config layer | ENH-74 | PROPOSED | 4–6h |
| 6 — Dashboard truth + alerts | ENH-67, ENH-69, ENH-73 | PROPOSED | 3h |

**Governance.** Every session produces its own commit chain, its own register entry, and live replay-validation against Supabase. No merges without validation paste in chat transcript and register update.

**Governing principle.** MERDIAN stops being a system where "looked green but was broken" is possible. Silent failures → visible failures → alertable failures.

---


## Part 5 -- Change Log

Append-only. Record every meaningful register edit.

| Date | Version | Action | Commit | Summary |
|---|---|---|---|---|
| 2026-03-31 | v1 | Initial register | (pre-git) | ENH-01 through ENH-32 established |
| 2026-04-03 | v2 | +ENH-33..36 | -- | Pure-Python BS, Live dashboard, Signal validation, hist->live promotion |
| 2026-04-09 | v3 | Refinements | -- | Status updates |
| 2026-04-11 | v4 | ENH-37 COMPLETE, ENH-35 COMPLETE | 26c5e72 | ICT layer live; full-year signal validation |
| 2026-04-12 | v5 | +ENH-38..42 | -- | Kelly sizing proposal; ENH-42 redefined (WebSocket -> Session pyramid) |
| 2026-04-13 | v6 | ENH-38..40 COMPLETE; +ENH-43..45 | -- | Kelly sizing live; dashboard; capital; spot backfill |
| 2026-04-13 | v7 | +ENH-46..51 | -- | Process manager, pre-open, Phase 4A/4B, WebSocket |
| 2026-04-14/15 | v7 (v8 section) | +ENH-52, ENH-52b | -- | 5-year backfill; S3 warm tier deferred |
| 2026-04-17/18 | v7 (v8 section) | +ENH-53..58 (V18H_v2 renumbered) | -- | Breadth gate removal, momentum block, sweep monitor, MTF OHLCV, hist_pattern_signals |
| 2026-04-19 | v7 | ENH-53, 55, 59 COMPLETE; +ENH-60..65 | 8f70822..b2dcc4e | V4 signal engine live; ENH-54/63 rejected; duplicate Kelly block removed (ENH-65) |
| 2026-04-19 | **unified** | Merged v1-v7 into single file | (this commit) | Canonical register going forward |
| 2026-04-20 | **unified** | 2026-04-20 outage + re-engineering programme Sessions 1+2 | 8f83859, b195499, 260c7d0 | ENH-66 COMPLETE (holiday-gate root cause); ENH-67..70 PROPOSED (view/supervisor/preflight/dashboard); ENH-68 COMPLETE tactical (runner .env reload); ENH-71 COMPLETE (write-contract layer + capture_spot_1m reference); ENH-72..74 PROPOSED (propagation, alerts, live config). Six-session re-engineering programme approved post-outage. |

---

## Part 6 -- Archive References

Historical registers are preserved under `docs/registers/archive/`:

- `MERDIAN_Enhancement_Register_v1.md` (2026-03-31)
- `MERDIAN_Enhancement_Register_v2.md` (2026-04-03)
- `MERDIAN_Enhancement_Register_v3.md` (2026-04-09)
- `MERDIAN_Enhancement_Register_v4.md` (2026-04-11)
- `MERDIAN_Enhancement_Register_v5.md` (2026-04-12)
- `MERDIAN_Enhancement_Register_v6.md` (2026-04-13)
- `MERDIAN_Enhancement_Register_v7.md` (2026-04-13, v8-appended 2026-04-19)
- `MERDIAN_Enhancement_Register_v6_V18H_v2.md` (V18H_v2 session artifact, pre-Rule-5 renumbering)

Each archive file is the committed state at its version. This unified file is the living register going forward.

---

*MERDIAN Enhancement Register -- unified 2026-04-19, updated 2026-04-20 -- do not version the filename.*


---

# Deltas pending merge into v8

# MERDIAN Enhancement Register — Delta 2026-04-21

**Purpose:** Addendum to Enhancement Register v7 covering Session 3+4 of 2026-04-21. To be merged into v8 during next documentation debt closeout.

**Context:** Enhancement Register v7 on disk stops at ENH-59 (2026-04-13). Sessions between 2026-04-13 and 2026-04-21 added ENH-60 through ENH-74+ which are referenced in code comments and commits but not yet in the register. This delta captures tonight's additions only. Full v8 overhaul to cover the ENH-60..71 gap deferred to a future session.

---

## ENH-72 — ExecutionLog Write-Contract Propagation (9 of 9 critical scripts)

| Field | Detail |
|---|---|
| Status | **COMPLETE** — all 9 targets |
| Sessions | 2 (base layer), 3 (targets 1-5), 4 (targets 6-9) |
| Updated | 2026-04-21 |
| Authority | V19 §15 governance rule `script_execution_log_contract` |

**What this programme delivered:**

Every production script in the 5-minute pipeline now records each invocation to `script_execution_log` with:
- `exit_reason` classification (SUCCESS, DATA_ERROR, DEPENDENCY_MISSING, TOKEN_EXPIRED, HOLIDAY_GATE, SKIPPED_NO_INPUT)
- `contract_met` boolean (actual writes ≥ expected floor)
- `duration_ms` timing
- Structured `notes` for operator triage (symbol coverage, feature flags, subsystem degradation)
- `error_message` for failure triage

**Scripts instrumented:**

| # | Script | Contract | Commit |
|---|---|---|---|
| 1 | ingest_option_chain_local.py | {option_chain_snapshots: 50 or 8 by mode} | 3a22735 |
| 2 | compute_gamma_metrics_local.py | {gamma_snapshots: 1} via set_symbol helper | d676a73 |
| 3 | compute_volatility_metrics_local.py | {volatility_snapshots: 1} via set_symbol | 2173002 |
| 4 | build_momentum_features_local.py | {momentum_snapshots: 1} | 74e15a0 |
| 5 | build_market_state_snapshot_local.py | {market_state_snapshots: 1} | 70df409 |
| 6 | build_trade_signal_local.py | {signal_snapshots: 1}, ict_failed/enh06_failed flags, action in notes | b3d88fa |
| 7 | compute_options_flow_local.py | {options_flow_snapshots: 1} floor, partial-success tolerant | 1e75a74 |
| 8 | ingest_breadth_intraday_local.py | {equity_intraday_last: 100}, 4-layer guard → HOLIDAY_GATE | dd66076 |
| 9 | detect_ict_patterns_runner.py | {ict_zones: 0} floor, non-blocking exit 0 preserved | f121fca |

**Production validation (2026-04-21 trading day, live):**
- 1,871 total invocations logged across targets 1-5 during full session
- 5 failures (~99.7% clean rate)
- Failures classified correctly: 3 DATA_ERROR (Dhan timeouts), 2 incidental
- Final cycle 15:27 IST clean shutdown

**Critical behaviour decisions baked in:**
- `action=DO_NOTHING` is NOT a failure — it's a reasoned decision. contract_met=true for all successful decisions including DO_NOTHING.
- `trade_allowed=False` is NOT a failure — it's a gate firing. contract_met=true.
- Detector "no patterns found" (ict_zones floor=0) is NOT a failure — patterns are rare events.
- HOLIDAY_GATE exits (CalendarSkip) record cleanly instead of crashing.

**Remaining known contract hazards (out of ENH-72 scope):**
- signal_snapshots, volatility_snapshots use INSERT not UPSERT — duplicate (symbol, ts) would 23505. Latent; no production repro.
- ENH-72 instrumented everything but did NOT refactor the underlying write operations. Contracts audit data flow, not trade logic.

---

## ENH-37 ADDENDUM — 1H zone trigger made data-driven (supersedes is_hour_boundary time-window check)

| Field | Detail |
|---|---|
| Parent | ENH-37 (ICT Pattern Detection Layer) |
| Updated | 2026-04-21 |
| Trigger | OI-27 (1H zones never triggered in production) |
| Commit | d15c494 |

**Problem:** Original `is_hour_boundary()` in `detect_ict_patterns_runner.py` returned True only when `minute < 3`. Production runner cycle schedule (5-min offset from 09:14 start) never lands in minutes 0-2. Result: `detect_1h_zones` never called, `ict_htf_zones` had ZERO rows with timeframe='H' across the entire life of the pipeline.

**Fix:** Replaced time-window check with `should_rebuild_1h_zones(sb, symbol)`. Queries `ict_htf_zones` directly for existing H-timeframe rows in current hour. Rebuilds if none found. Works for any cycle schedule (whether :00/:05/:10 or :14/:19/:24). Idempotent upsert means re-firing would be harmless, but the check prevents wasted work. Fails open on query error.

**Verification:** 4 1H zones now visible in ict_htf_zones (first time ever in production). PDH/PDL for both NIFTY and SENSEX from today's session. No BULL_OB/BEAR_OB/BULL_FVG detected today because hourly moves didn't cross the 0.40% OB_MIN_MOVE_PCT threshold — that threshold is calibration, separate from this fix.

**Secondary fix (same commit):** `build_ict_htf_zones.py` had `if __name__ == "__main__": main()` positioned mid-file at line 559, before `detect_1h_zones` was defined at line 600+. CLI `python build_ict_htf_zones.py --timeframe H` crashed with NameError. Runner path via `from build_ict_htf_zones import detect_1h_zones` was unaffected. Moved `__main__` block to end of file.

---

## ENH-38 ADDENDUM — expiry lookup source changed to option_chain_snapshots

| Field | Detail |
|---|---|
| Parent | ENH-38 (Live Kelly Tiered Sizing) |
| Updated | 2026-04-21 |
| Trigger | OI-26 (SENSEX dte=-54d, NIFTY dte=252d observed) |
| Commit | 49c5e3c |

**Problem:** Kelly sizing input `dte_days` was computed via `build_expiry_index_simple(sb, inst_id) → nearest_expiry_db(trade_date, index)` in `merdian_utils.py`. The index was built by sampling `hist_option_bars_1m.expiry_date` at hardcoded monthly dates spanning 2025-04-01 through 2026-03-03. On 2026-04-21 the entire hardcoded window was in the past, producing a stale index with no future expiries. `nearest_expiry_db` fell through to `expiry_index[-1]` returning historical expiries, producing impossible DTEs (SENSEX -54d, NIFTY 252d).

**Fix:** New function `get_nearest_expiry(sb, symbol)` reads the latest `option_chain_snapshots.expiry_date` directly. This field is written every 5-minute cycle by `ingest_option_chain_local.py` from Dhan's live option chain response. Dhan itself handles NSE holiday-driven expiry shifts (Thursday holiday → Wednesday expiry, etc.) natively in its API, so the value is always correct without a local calendar.

**Architectural principle:** Don't re-implement calendar logic that the upstream broker API already handles correctly. Use the authoritative source.

**Retired (no current callers, kept for audit trail):**
- `build_expiry_index_simple()` — DEPRECATED
- `nearest_expiry_db()` — DEPRECATED
- ENH-63 `_EXPIRY_INDEX_CACHE` dict — REMOVED

**Smoke validation:**
- NIFTY dte=0d (correct — NIFTY weekly expires Tuesday 2026-04-21, today)
- SENSEX dte=2d (correct — SENSEX weekly expires Thursday 2026-04-23)

---

## ENH-63 — Expiry Index Cache

| Field | Detail |
|---|---|
| Status | **RETIRED 2026-04-21** (superseded by ENH-38 addendum) |

Original purpose: cache `build_expiry_index_simple()` output across cycles to avoid 12 paginated queries per call. Removed with OI-26 fix — the whole expiry index approach is obsolete, replaced by single-query `get_nearest_expiry()` reading the authoritative `option_chain_snapshots.expiry_date`.

---

## Non-Enhancement Fix: OI-24 (ICT schema mismatch)

| Field | Detail |
|---|---|
| Type | Bug fix (documented here because OI Register v7 is permanently closed) |
| Updated | 2026-04-21 |
| Commit | f121fca (folded into ENH-72 target 9) |

**Problem:** `detect_ict_patterns_runner.py` `load_atm_iv()` queried `market_state_snapshots.market_state` — a column that doesn't exist. The table stores features as separate JSONB columns (`volatility_features`, `gamma_features`, etc.). Original script's tail `sys.exit(0)` on any exception had silently masked this error in production for an unknown duration.

**Fix:** `load_atm_iv()` now reads `volatility_features.atm_iv_avg` directly — matches how `build_trade_signal_local.py` consumes the same field. Entire function body wrapped in try/except returning None (atm_iv is an optional input for the detector; downstream uses fallback thresholds).

**Why this matters beyond the immediate fix:** This is exactly the kind of silent degradation ENH-72 was designed to surface. Pre-instrumentation, the pipeline logged "all green" while a critical enrichment was failing. Post-instrumentation, the failure surfaced in `script_execution_log` as `exit_reason=DATA_ERROR` with the specific error message — we could see and fix it within one session.

---

*Delta document 2026-04-21 — to merge into Enhancement Register v8 at next full documentation update.*
