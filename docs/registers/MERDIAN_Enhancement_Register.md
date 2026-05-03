# MERDIAN Enhancement Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `docs/registers/MERDIAN_Enhancement_Register.md` |
| Scope | Living register of all proposed and delivered MERDIAN enhancements, ENH-01 through ENH-86 |
| Lineage | Unified from v1 (2026-03-31) through v7 (2026-04-19 v8-appended). Prior versioned files archived at `docs/registers/archive/`. |
| Last updated | 2026-05-02 (Session 15 — Exp 44/47/47b/50/50b run with verdicts; ENH-85 design space reduced via Exp 47b; production patches shipped to two zone builders closing TD-S1-BEAR-FVG-DETECTOR; ADR-003 Phase 1 v1/v2 INVALID — see ADR file for v3 plan; no new ENH IDs filed) |
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

Sortable table of all 86 IDs. For full detail see Part 4.

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
| ENH-72 | Propagate ExecutionLog to 9 remaining critical scripts | 1 | **CLOSED 2026-04-21** |
| ENH-73 | Dashboard truth + alert daemon contract-violation rules (Session 6) | 1 | **PROPOSED** |
| ENH-74 | Live config layer — core/live_config.py (Session 5, strategic replacement of ENH-68) | 1 | **PROPOSED** |
| ENH-73a | Tradable signal alerts via existing pipeline alert daemon (Session 9 wave 2) | 1 | **SHIPPED 2026-04-26** |
| ENH-73b | Dashboard latched-signal panel (Session 9 wave 2, deferred) | 1 | **PROPOSED-DEFERRED** |

| ENH-84 | Dashboard "Refresh Zones + Pine" Button (intraday) | 1 | **SHIPPED 2026-04-30** |
| ENH-85 | PO3 Session Direction Lock (anti-flip-flop) | 1 | **PROPOSED-DEFERRED — design space reduced Session 15 via Exp 47b (slower-anchor falsified); remaining paths: hard PO3 lock OR persistence filter** |
| ENH-86 | Dashboard WIN RATE Section Redesign | 1 | **SHIPPED v1 2026-04-30 (v2 BLOCKED/ALLOWED prominence DEFERRED)** |
| ENH-78 | DTE<3 PDH sweep → current-week PE rule | 1 | **SHIPPED 2026-04-30** |
| ENH-79 | PWL weekly sweep detection + signal entry rules | 1 | **PROPOSED** |
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
| ENH-72 | Propagate ExecutionLog to 9 critical scripts | **CLOSED 2026-04-21** |
| ENH-73 | Dashboard truth + alert daemon | **PROPOSED** |
| ENH-74 | Live config layer (core/live_config.py) | **PROPOSED** |
| ENH-73a | Tradable signal alerts (extends ENH-73) | **SHIPPED 2026-04-26** |
| ENH-73b | Dashboard latched-signal panel | **PROPOSED-DEFERRED** |


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


### ENH-72: Propagate ExecutionLog to 9 remaining critical scripts — CLOSED 2026-04-21

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



**Closure note (appended 2026-04-22):**

| Field | Value |
|---|---|
| Status | CLOSED 2026-04-21 |
| Closed commit chain | `3a22735` → `d676a73` → `2173002` → `74e15a0` → `70df409` → `b3d88fa` → `1e75a74` → `dd66076` → `f121fca` |
| Scripts instrumented (9 of 9) | `ingest_option_chain_local.py`, `compute_gamma_metrics_local.py`, `compute_volatility_metrics_local.py`, `build_momentum_features_local.py`, `build_market_state_snapshot_local.py`, `build_trade_signal_local.py`, `compute_options_flow_local.py`, `ingest_breadth_intraday_local.py`, `detect_ict_patterns_runner.py` |
| Live production validation (2026-04-21 trading day) | 1,891 invocations recorded in `script_execution_log`. 12 non-success events; distribution non-uniform. Per-script contract-met rates: `ingest_option_chain_local.py` 100% (303/303); `compute_gamma_metrics_local.py` 99.3% (301/303, both failures on null-symbol batch); `compute_volatility_metrics_local.py` 99.7% (299/300); `build_momentum_features_local.py` 100% (299/299); `build_market_state_snapshot_local.py` 100% (287/287); `build_trade_signal_local.py` 100% (2/2, low invocation count expected — signal engine gates heavily); `compute_options_flow_local.py` 100% (2/2); `ingest_breadth_intraday_local.py` 0% (0/2, both invocations failed contract — tracked separately, likely related to C-08 underlying write-path already resolved); `detect_ict_patterns_runner.py` 67% (12/12 contract-met, 4/12 exit_reason!=SUCCESS — ICT detection has `non_blocking exit 0` semantics for missing zones). |
| Pattern established | `capture_spot_1m.py` (ENH-71 reference impl) → 9 scripts above. All follow `ExecutionLog` context manager with `expected_writes` declared at construction and `record_write(table, count)` after each insert. |
| Follow-on | ENH-73 (dashboard alert daemon) depends on this propagation being complete. No further ENH-72 scope — this ID is permanently closed. |


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
| 3 — Propagate to 9 scripts | ENH-72 | CLOSED 2026-04-21 | commit chain 3a22735..f121fca |
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

## ENH-72 — ExecutionLog Write-Contract Propagation (9 of 9 critical scripts) — CLOSED 2026-04-21

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

---

### ENH-73a: Tradable signal alerts via existing pipeline alert daemon (extends ENH-73)

| Field | Detail |
|---|---|
| Status | **SHIPPED 2026-04-26 (Session 9 wave 2)** |
| Type | Operational extension of ENH-73 |
| Parent | ENH-73 (Dashboard truth + alert daemon contract-violation rules) |
| Area | OPS / Observability |
| Session | 9 wave 2 |
| Commit | `<hash>` (Session 9 wave 2 commit batch) |

**Context.** ENH-73 deployed Session 8 with name "pipeline alert daemon" but implementation alerted only on infrastructure failures from script_execution_log (TOKEN_EXPIRED, DATA_ERROR, DEPENDENCY_MISSING, RUNNING, contract-violated SUCCESS). It did not poll signal_snapshots. Empirical evidence Session 9: 1,017 BUY_PE rows + 1 BUY_CE row produced over 21 trade days; only 3 PE rows had trade_allowed=true; operator reported never having seen any of them surface in real time. Combined with merdian_live_dashboard.py overwriting any displayed signal every ~3 minutes (limit=1, latest-cycle query), zero operator-facing surface existed for "actionable signal just occurred."

**Implementation.** Two-step patch on `merdian_pipeline_alert_daemon.py`:

1. `fix_enh46a_signal_alerts.py` — added SIGNAL_ALERT_ACTIONS constant, fetch_new_tradable_signals(), format_signal_alert(), run_signal_cycle() with own watermark (`last_alerted_signal_ts`). Hooked into both cmd_daemon main loop and cmd_once for testability.
2. `fix_enh46a_init_bug.py` — discovered post-deploy that the original patch placed signal-watermark init INSIDE init_watermark_if_missing() AFTER the early-return-on-existing-state guard. Result: warm restarts silently skipped signal-watermark init. Refactored into separate `init_signal_watermark_if_missing()` called independently from cmd_daemon, cmd_once.

**Note on naming.** Filed in working notes as "ENH-46-A" because the working filename `fix_enh46a_signal_alerts.py` predated the ID resolution. Live register ID is **ENH-73a** because semantically this extends ENH-73's scope. Patch script filenames retained for git history continuity.

**Verified live.** Synthetic INSERT into signal_snapshots with action='BUY_PE', trade_allowed=true → Telegram delivered within poll cycle. Watermark advanced. signal_alerts_sent_total counter incremented. Daemon PID 19636 (relaunched after patch).

**Files changed.**

- `merdian_pipeline_alert_daemon.py`: +5,566 bytes (across both patches).
- `runtime/pipeline_alert_state.json`: schema extended with `last_alerted_signal_ts`, `signal_alerts_sent_total`, `last_signal_alert_at`.
- Backups preserved at `.pre_enh46a.bak` and `.pre_enh46a_initbug.bak`.

**Caveats.**

- Surfaces every trade_allowed=true cycle, not just transitions. In a SHORT_GAMMA window producing 38 PE cycles in 2 hours, operator receives 38 alerts. Rate-limiting / dedup not yet implemented; may add if alert fatigue becomes an issue.
- BUY_PE trade_allowed=false rows (1,014 of 1,017 historical) NOT alerted. By design — those are gated downstream and not actionable.

**Related TDs filed Session 9 wave 2:**

- TD-027 (S4): Alert daemon scope drift — file is named for one job, now does two.
- TD-028 (S3): `merdian_pm.py` silent fail on unknown name — discovered during ENH-73a daemon restart.

**History:** 2026-04-26=SHIPPED end-to-end with synthetic verification.

---

### ENH-73b: Dashboard latched-signal panel (DEFERRED)

| Field | Detail |
|---|---|
| Status | **PROPOSED 2026-04-26 (Session 9 wave 2). Deferred pending ENH-73a live evaluation.** |
| Type | Operational; alternative surface to ENH-73a |
| Parent | ENH-73 (Dashboard truth + alert daemon contract-violation rules) |
| Area | OPS / Dashboard |
| Session | 9 wave 2 (filed) |

**Context.** merdian_live_dashboard.py displays only the latest signal_snapshots row per symbol (limit=1 query, no trade_allowed filter). Tradable signals overwrite within ~3 minutes per cycle. Operator looking at dashboard during a SHORT_GAMMA window may still miss the alert.

**Why deferred.** ENH-73a's Telegram path push-notifies the operator's phone. If A meets operational need in practice, B may be unnecessary entirely. Re-evaluate after first live SHORT_GAMMA window with ENH-73a in production.

**If proceeded later.** Add a second panel ("Latest Tradable Signal") that latches the most recent action != DO_NOTHING AND trade_allowed=true row per symbol with T+30m retention (matches documented exit horizon). ~50-100 lines HTML/JS in merdian_live_dashboard.py.

**History:** 2026-04-26=PROPOSED, deferred.


---

## Session 13 New ENH Entries (2026-04-29)

### ENH-84 — Dashboard "Refresh Zones + Pine" Button (intraday)

| Field | Detail |
|---|---|
| Status | **SHIPPED 2026-04-30 (Session 14, with hotfix)** |
| Priority | 1 |
| Session filed | Session 13 (2026-04-29) |
| Goal | Add a button to the MERDIAN signal dashboard that: (1) calls `build_ict_htf_zones.py --timeframe H` to rebuild hourly zones, (2) calls `generate_pine_overlay.py` to regenerate the Pine file, (3) serves the updated `.pine` file for one-click copy-paste into TradingView. Enables intraday zone refresh without manual CLI. |
| Type | Code — small. Dashboard endpoint + button. |
| Blocker | None. |
| Note | TradingView Pine cannot receive live data pushes (sandboxed). This is the practical near-term solution. Full intraday charting in MERDIAN dashboard (TradingView Lightweight Charts) is ENH-87 candidate. |
| Patch | `fix_enh84_refresh_zones_pine_button.py` — added 🔄 REFRESH ZONES button to topbar after PINE OVERLAY + GET endpoint `/refresh_and_download_pine` that subprocess-runs `build_ict_htf_zones.py --timeframe H` (60s timeout) then calls `_gen_pine(sb)` and serves `merdian_ict_htf_zones_refreshed.pine`. Two anchors. ast.parse PASS. |
| Hotfix | `fix_enh84_hotfix_sys_executable.py` — initial deploy used `sys.executable` for the subprocess call. Dashboard had no `import sys` at module level (only `import sys as _sys` deep inside `build()`), so `sys` was undefined at endpoint scope. Hotfix replaces `sys.executable` with bare `"python"`. Lesson: grep imports in target file at module level before writing endpoint code that references module attributes. |
| Live verification | Post-hotfix: button visible in topbar, endpoint returns Pine file, operator pasted into TradingView showing 21 zones (`MERDIAN HTF | SENSEX | 21 zones | entry-band | 2026-04-30`). Dashboard zombie-listener pattern surfaced during deploy (PIDs 32052, 24764 both bound to port 8766 simultaneously); operator pattern: `netstat -ano | findstr :8766 | findstr LISTENING` → `taskkill /F /PID <pid>` for each, restart. |

---

### ENH-85 — PO3 Session Direction Lock (anti-flip-flop)

| Field | Detail |
|---|---|
| Status | **PROPOSED-DEFERRED (pending Exp 43)** |
| Priority | 1 |
| Session filed | Session 13 (2026-04-29) |
| Goal | Prevent ENH-55 `ret_session` momentum opposition from flipping `direction_bias` intraday on confirmed PO3 session days. On PO3_BEARISH days, lock direction BEARISH for the session; on PO3_BULLISH days, lock BULLISH. Eliminates random BUY_CE signals appearing between BUY_PE signals when spot briefly crosses the session open price. |
| Evidence | Observed 2026-04-29: 12:01 IST BUY_PE → 13:10 IST BUY_CE (spot briefly above open) → 13:51 IST BUY_PE. Mechanically caused by `ret_session` sign change, not genuine reversal. |
| Blocker | **Exp 43 (Signal Direction Stability) must be run first.** Markets do genuinely reverse intraday. A hard lock prevents adapting to those reversals. Need backtested stability criterion (persistence filter, hysteresis, or slower momentum anchor) before implementing. |
| Build built and reverted | `build_trade_signal_local.pre_enh85.bak` on disk. Do NOT re-apply without Exp 43 backing. |

---

### ENH-86 — Dashboard WIN RATE Section Redesign

| Field | Detail |
|---|---|
| Status | **SHIPPED v1 2026-04-30 (Session 14). v2 (BLOCKED/ALLOWED visual prominence) DEFERRED.** |
| Priority | 1 |
| Session filed | Session 13 (2026-04-29) |
| Goal (original combined) | Current WIN RATE table mixes signal quality, execution tiers, and historical WR into one opaque block. Redesign into two separate visual sections: (A) Signal quality — pattern, condition, historical WR, EV, N. (B) Execution — tier, lots, BLOCKED/ALLOWED shown prominently. Remove tier from signal quality display entirely. BLOCKED/ALLOWED should be the most prominent element in execution, not buried in a table row. |
| Type | Code — medium. Dashboard HTML/JS changes. |
| Blocker | None. |
| **v1 scope (SHIPPED)** | WIN RATE legend extended from 5-column to 7-column: added EV (per-trade) and N (sample size) columns. New LIVE rows added at top of legend for E4 (BEAR_OB MIDDAY+PO3_BEARISH 88.2% N=17 +116.5pts SENSEX) and E5 (BULL_OB AFT+PO3_BULLISH SENSEX 73.7% N=19 +35.5pts). Existing pattern rows (BEAR_OB MORNING 100% N=9 +81.2%; BULL_OB DTE=0 100% N=20 +121.4%; BULL_FVG HIGH+DTE=0 87.5% N=12 +58.9%; BEAR_OB MOM_YES 83% N=23 +56.1%) backfilled from MERDIAN_Experiment_Compendium_v1; remaining rows display `—` honestly where data wasn't available. |
| **v1 patch** | `fix_enh86_winrate_redesign_v1.py` — three anchor replacements: (1) `WIN_RATES` list extended from 5-tuple to 7-tuple; (2) `legend_rows()` 7-col unpack emitting EV+N td cells (colspan 5→7); (3) `<thead>` updated 5→7 columns. Live verified after hard refresh + zombie-listener kill. |
| **v2 scope (DEFERRED)** | Signal quality vs Execution visual separation. BLOCKED/ALLOWED moved out of table-row context into a prominent execution panel element (banner, large badge, or border-highlighted card). Tier removed from signal quality display. Removes the original conflation issue but is structurally a bigger UI change. Not blocking; legend now carries EV+N which was the highest-value information gap. |
| **v2 trigger** | Operator decides v2 priority based on usage — if BLOCKED/ALLOWED conflation continues to cause misreads, escalate; otherwise the v1 EV/N visibility may be sufficient. |

---

### Exp 43 — Signal Direction Stability (filed Session 13)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Session filed | Session 13 (2026-04-29) |
| Question | What is the minimum stability criterion for `direction_bias` before a MERDIAN signal should be trusted? How often does `direction_bias` flip intraday, and when it flips, is it associated with genuine reversals or noise? |
| Motivation | ENH-55 `ret_session` crosses zero whenever spot oscillates around session open, producing spurious direction flips (BUY_CE between two BUY_PEs on 2026-04-29). Need empirical backing before implementing ENH-85. |
| Approach options | (1) Persistence filter: require N consecutive cycles same direction (query: how often does direction stay stable ≥3 cycles before a signal fires?). (2) Slower anchor: use ret_30m or ret_60m instead of ret_session for V4 direction. (3) Hysteresis: require stronger threshold to flip back (e.g. 0.15% not 0.05%). (4) PO3 as soft prior: weight confidence ±N when PO3 agrees/disagrees rather than hard lock. |
| Data source | `hist_pattern_signals` + `hist_market_state` (ret_session per bar). Cross-reference direction flips with T+30m outcomes. |
| Output | Empirical answer to: "does holding direction stable improve WR vs allowing ENH-55 full rein?" If yes, implement ENH-85 with the winning criterion. |


---

### ENH-78 — DTE<3 PDH sweep → current-week PE rule

| Field | Detail |
|---|---|
| Status | **SHIPPED 2026-04-30 (Session 14)** |
| Priority | 1 |
| Session filed | Session 11 (2026-04-28, Exp 35D PASS) — formally added to register Session 14. |
| Session shipped | Session 14 (2026-04-30) |
| Goal | When PO3_BEARISH session bias confirmed AND DTE is 1 or 2 AND signal action is BUY_PE: lift the standard DTE<=1 confidence penalty (was -12 conf points + "DTE gate" caution) and treat as a high-conviction current-week PE setup. Tag with explicit stop rule. |
| Evidence | Exp 35D — PDH DTE<3 current-week PE: 90.9% EOD WR (N=11), +125% mean SENSEX option return. Current-week beats next-week on this rule. |
| Type | Code — small. Single guarded block in `build_trade_signal_local.py` before `return out, flags`. |
| Logic | If `po3_session_bias=PO3_BEARISH AND 1<=dte<=2 AND action=BUY_PE`: DTE=1 — reverse -12 confidence penalty, remove "DTE gate" cautions, add stop rule "40% premium OR PDH reclaim", set `out["raw"]["enh78_triggered"]=True/dte/stop_note`. DTE=2 — same but tagged "confirmed" (no original gate to reverse since 2 was already allowed by base logic). |
| Stop rule rationale | Premium-based stop (40%) protects against opening-print decay on DTE=1; PDH reclaim is the structural invalidation (sweep failed, no continuation). Either trigger exits. |
| Patch | `fix_enh78_dte_lt3_pe_rule.py` — single ENH-78 block insertion before `return out, flags`. CRLF auto-detect. |
| Validation | ast.parse PASS + 5 functional scenarios verified: (1) DTE=1 BEAR PO3_BEARISH BUY_PE → triggered, conf reversed; (2) DTE=2 same → triggered as confirmed; (3) DTE=3 → not triggered; (4) PO3_NONE → not triggered; (5) action=BUY_CE → not triggered. |
| Live verification | Smoke test post-apply ran clean. Live ENH-78 trigger pending — requires PO3_BEARISH session day with DTE<=2 — natural verification within 1–2 weeks. |
| Carries | TD-044 fix (Session 14) ensures ENH-76/77 dict-sync — relevant because ENH-78 reads `action` after ENH-76/77 may have set `out["action"]`. Without TD-044, ENH-78 would have triggered against stale `action=BUY_PE` even when ENH-76 supposedly blocked. With TD-044, the gate ordering is sound. |

---

### ENH-79 — PWL weekly sweep detection + signal entry rules

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Priority | 1 |
| Session filed | Session 11 (2026-04-28, Exp 39B PASS) — formally added to register Session 14. |
| Session target | Session 15 (primary build target) |
| Goal | Detect PWL (Previous Week's Low) weekly sweep at start of new trading week, persist daily session bias, gate appropriate ATM CE entry signals on the sweep day or next 1–2 days. Mirrors PO3 daily session bias detection (ENH-75) but at weekly cadence. |
| Evidence | Exp 39B — PWL refined weekly: 76.9% EOW WR (N=13), T+2D mean +534pts SENSEX (E6). Subset E7 — PWL weekly + daily PDL confluence: 100% conf-day WR (N=5), highest conviction signal in research set but smallest N. |
| Sub-decisions pending operator confirmation | (1) Storage shape — Option A: column on `market_state_snapshots` (per-cycle, redundant). Option B (recommended): new table `weekly_sweep_state(symbol, trade_date, weekly_sweep_bias, daily_pdl_confluence, swept_pwl_value, prev_week_range, detected_at, raw)` keyed `(symbol, trade_date)`. (2) Detection time — Option A: 08:50 IST pre-market (analyses yesterday's close, reflects sweep that completed in last session). Option B: 15:35 IST EOD (detects today's sweep for tomorrow's trade). Compendium implies pre-market 08:50 detection. (3) E6 vs E7 — Option A: ship E6 detection, E7 emerges as a confluence flag. Option B: ship E7 only (highest WR, smallest N). Option C (recommended): ship E6 with `daily_pdl_confluence` boolean flag — signal engine handles both, tags confluence case for higher-conviction sizing. |
| Default plan | New table `weekly_sweep_state` per Option B; new script `detect_weekly_sweep_bias.py` modeled on `detect_po3_session_bias.py` runs 08:50 IST daily; new Task Scheduler entry `MERDIAN_WeeklySweep_0850`; helper `_get_weekly_sweep_bias()` in `build_trade_signal_local.py` (mirroring `_get_po3_bias()`); entry gating logic for E6 + E7 confluence flag — when `weekly_sweep_bias=BULLISH` AND it's the sweep day's EOD or T+1/T+2, allow next-week ATM CE; if `daily_pdl_confluence=True`, tag for higher-conviction sizing. |
| Caveat | Entry trigger "sweep day EOD" differs from MERDIAN's existing intraday cycle entry triggers. May require a separate alert path (e.g. a daily 15:35 IST evaluation gate that fires Telegram if conditions met) rather than firing through the regular intraday signal cycle. Worth flagging in design phase. |
| Forbidden ground | Do NOT replicate ENH-85 mistake (build before research). Operator approval of sub-decisions before code. |



---

### ENH-87 — `hist_pattern_signals` deprecation review (move research to live-detector replay pattern)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Priority | 2 |
| Session filed | Session 16 (2026-05-03) |
| Session target | Session 17 / 18 — decision-only first session, then 2-3 sessions to migrate consumers if approved |
| Goal | Deprecate `hist_pattern_signals` (the 5m-batch detector path) as a research scaffold, in favour of the live-detector replay pattern demonstrated by Session 16's `experiment_15_with_csv_dump.py` + `analyze_exp15_trades.py` workflow. |
| Motivation | Three accumulated integrity issues with `hist_pattern_signals`: (1) `ret_30m` column has 4.7-5.0% agreement with locally-computed forward return across 3 cohorts (TD-054 expanded), 30% NULL — every research finding using `ret_30m` directly is suspect. (2) `ret_60m` uniformly 0 across all rows (TD-054). (3) Bull-skew is structural to this code path (TD-056) — produces 5.6x BULL/BEAR_FVG ratio in NIFTY DOWN regime. Plus: the live trading pipeline does NOT consume `hist_pattern_signals` — it reads `signal_snapshots` from `build_trade_signal_local.py` which uses the live 1m detector path. So `hist_pattern_signals` is research scaffolding, not production state. The Session 16 finding that `experiment_15_pure_ict_compounding.py` (live-detector replay, 1m bars, ICTDetector running per bar) replicates Compendium headlines within 2-3pp on 231 trades demonstrates that the same research questions are answerable on the live-detector cohort with better integrity. |
| Approach options | **(A) Hard deprecate.** Stop running `build_hist_pattern_signals_5m.py`. Migrate any active research that depends on it to the live-detector replay pattern. Mark table read-only "research-archive only, do not trust column values, do not extend." TD-054 / TD-055 / TD-056 close as wontfix-by-deprecation. **(B) Fix and keep.** Diagnose `ret_30m`/`ret_60m` column population, fix at source (signal builder or upstream `hist_market_state`), backfill via signal rebuild. Investigate bull-skew (TD-056 Phase 1). 2-3 sessions of work. **(C) Coexist.** Keep table for historical research (Sessions 1-13 experiments still in Compendium reference it), explicitly tag any new research as "live-detector replay required" — don't allow new findings on `hist_pattern_signals` cohort without parallel live-cohort verification. |
| Recommendation | **Option C in the short term, Option A long-term.** Don't drop the table now (existing Compendium entries reference it; auditing those would take a session). But require new research to use live-detector replay pattern. Migrate downstream consumers (research dashboards, `merdian_signal_dashboard.py` if it reads from this table — needs check) gradually. Re-evaluate hard deprecation in 3-6 months when no live consumers depend on it. |
| Cost | Option C: ~0.5 session to add migration guidance to CLAUDE.md and tag new-research workflow. Option A (eventual): 2-3 sessions to migrate all consumers + drop table. |
| Forbidden ground | Do NOT delete the table or stop the builder until downstream consumers verified migrated. Hard deprecation in middle of production migrations creates orphan-data audit trail issues. |

---

### ENH-88 — BULL_FVG production routing requires recent BULL_OB context (60-90 min lookback)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Priority | 1 |
| Session filed | Session 16 (2026-05-03) |
| Session target | Session 17 (Priority B) |
| Goal | Patch `build_trade_signal_local.py` to skip BULL_FVG signals UNLESS a BULL_OB trade fired in the same symbol within the last 60-90 minutes. Standalone BULL_FVG = SKIP (or sized down to floor). Clustered BULL_FVG = full sizing. |
| Evidence | Section 18 of `analyze_exp15_trades.py` on Session 16 live-cohort 231-trade CSV: BULL_FVG with recent BULL_OB at 90-min lookback (N=64) WR 57.8% [44.4, 70.5], vs standalone BULL_FVG (N=91) WR 45.1% [35.2, 55.5] — **+12.8pp lift**. At 60-min lookback: clustered N=57 WR 54.4%, standalone N=98 WR 48.0% — +6.4pp lift. At 30-min lookback: +1.0pp lift only. Standalone BULL_FVG pooled across full year is statistically a coin flip (Section 9: N=155, WR 50.3%, CI [42.5, 58.1] spans 50%). The cluster effect transforms a coin flip into a real edge. |
| Type | Code — small. Helper function `_recent_bull_ob_check(symbol, current_ts, lookback_min)` queries `signal_snapshots` for same-symbol BULL_OB signals in last N minutes. Gate added to BULL_FVG branch in `build_trade_signal_local.py`. |
| Logic (proposed) | If `pattern_type=BULL_FVG`: query `signal_snapshots` for `symbol=current.symbol AND pattern_type='BULL_OB' AND signal_ts >= current_ts - 90min AND signal_ts < current_ts AND trade_allowed=True`. If COUNT >= 1: proceed with normal sizing. Else: set `action=DO_NOTHING`, `trade_allowed=False`, add caution `"BULL_FVG without recent BULL_OB context — coin flip pooled, +12.8pp lift only when clustered (Session 16 Exp 15 Section 18)"`. |
| Lookback choice | 90 min is the strongest evidenced — +12.8pp lift on N=64. 60 min is +6.4pp on N=57. **Recommend 90 min as initial production lookback.** Can shadow-test 60 vs 90 in parallel for one month if uncertain. |
| Validation | Patch script must end with `ast.parse()` PASS. Functional scenarios: (1) BULL_FVG with BULL_OB at T-30min → trigger; (2) BULL_FVG with BULL_OB at T-60min → trigger; (3) BULL_FVG with BULL_OB at T-100min → block; (4) BULL_FVG with no BULL_OB in 90min → block; (5) BULL_FVG with BEAR_OB at T-30min → block (wrong direction). |
| Open questions | (a) Should the lookback distinguish between MTF context tiers? Section 18 didn't partition by tier — pooled across all. (b) Should the same rule apply to BEAR_FVG when TD-058 is fixed (live detector starts emitting BEAR_FVG)? Likely yes by symmetry, but should be measured separately on the eventual BEAR_FVG live cohort. (c) Should we ship as confidence-modifier (BULL_FVG without OB context: -25 conf, with: 0 modifier) or hard skip (block trade)? Recommend hard skip — coin flip is not edge worth deploying capital against. |
| Estimated cost | 1 session (Session 17 Priority B). Includes patch + verification scenarios + Compendium entry update. |
| Carries | Coordinates with TD-058 (BEAR_FVG live emission fix) — once TD-058 closes, ENH-88 should be extended symmetrically to BEAR_FVG. |

---

### ENH-89 — ENH-37 MTF context hierarchy redesign or removal (LOW outperforms HIGH)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Priority | 2 |
| Session filed | Session 16 (2026-05-03) |
| Session target | Session 18+ (lower priority than ENH-88 / TD-058 fixes, since this is a sizing input not a gate) |
| Goal | Redesign or remove MTF context hierarchy in production scoring. Current implementation (HIGH=W zone confluence, MEDIUM=H zone, LOW=no zone) treats higher confluence as higher confidence. Session 16 evidence: this is inverted on OB patterns. |
| Evidence | Section 10 of `analyze_exp15_trades.py` on Session 16 live-cohort 231 trades, Wilson 95% CIs: **BULL_OB|HIGH (D zone) 71.4% N=7, BULL_OB|MEDIUM (H zone) 81.8% N=11 [52.3, 94.9], BULL_OB|LOW (no zone) 87.1% N=31 [71.1, 94.9]**. **BEAR_OB|HIGH 71.4% N=7, BEAR_OB|MEDIUM 100% N=1, BEAR_OB|LOW 100% N=17 [81.6, 100]**. LOW context outperforms HIGH on BOTH OB patterns. The hierarchy as currently built may be filtering away the cleanest signal cohort or boosting confidence on contested-price-action cells. |
| Hypothesis | When a signal triggers in HIGH context (inside a daily zone), the price action is contested — buyers and sellers are both engaged at a known level. The "trade against the zone" logic plays out, but with chop and reduced edge. When a signal triggers in LOW context (no archive-zone confluence), price is in clean expansion — the OB pattern catches a moving market with directional follow-through. Effectively, archive zones may CAUSE the chop they're supposed to identify. Untested but consistent with the data. |
| Approach options | **(A) Annotation-only.** Keep MTF context as informational tag in `signal_snapshots` but do NOT use it as a confidence multiplier or sizing input. Production scoring becomes context-agnostic. Lowest-risk change. ~0.5 session. **(B) Inversion.** LOW becomes "high confidence" tier. Risky — current N=17-31 per cell is enough for direction signal but not enough for magnitude calibration. Could overfit to Session 16 cohort. **(C) Shadow A/B test.** Wire `confidence_score_v2` (inverted hierarchy) into `signal_snapshots` alongside current `confidence_score_v1`. Run both for 4-8 weeks live. Compare per-trade outcomes. Decide based on accumulated live data. ~1 session to wire shadow + 4-8 weeks measurement + 1 session to decide and ship. |
| Recommendation | **Option C — measure before changing production.** Current sizing rule is "wrong" on backtest but live regime may differ. Shadow-mode lets us decide on real data without disrupting current operations. While shadow runs, reduce sizing-multiplier-from-MTF-context magnitudes by half as a hedge against inverted-rule cost. |
| Caveat | Vocabulary alignment must be settled first (TD-057). Current production code uses post-Apr-13 vocabulary (HIGH=D, MEDIUM=H). The "ENH-37 thesis" was filed against pre-Apr-13 vocabulary (HIGH=W, MEDIUM=D). Before redesigning, document which vocabulary is canonical going forward. (Recommend: post-Apr-13, since that's what `detect_ict_patterns.py` produces today.) |
| Cost | Option C: 2 sessions across 4-8 weeks of live measurement. |
| Forbidden ground | Do NOT ship Option B without parallel measurement. N per cell is too small for confidence in the inverted magnitude. |



---

### Exp 44 — Intraday Inverted Hammer Reversal After Cascade (filed Session 14)

| Field | Detail |
|---|---|
| Status | **PROPOSED** |
| Session filed | Session 14 (2026-04-30) |
| Seed observation | NIFTY 15m on 2026-04-30, ~09:30-10:00 IST: opening cliff drop -300pts, terminal candle was an inverted hammer at the bottom of the move (~23,800 area), next candle tested but did not break below the hammer's range, third candle began the V-recovery to ~24,080 by 12:00 IST. Pattern observed real-time as a structurally clean capitulation reversal. |
| Question | Does an inverted hammer after a sustained intraday cascade, followed by a non-violating range test, predict a reversal large enough to be tradeable at T+30m / T+60m / EOD? Run both the bearish-cascade (long-side reversal) AND bullish-cascade mirror (short-side reversal) sides separately. |
| Hypothesis (bearish side / long entry) | (1) spot drops >=X% from session open within last N bars; (2) candle K is inverted hammer — high-wick >= 2x body, body in lower 1/3, close near low; (3) candle K+1 retests range of K (touches near K's low) but does NOT close below K's low; (4) entry at K+2 open; (5) measure T+30m, T+60m, EOD return. |
| Hypothesis (bullish side / short entry — MIRROR) | (1) spot rises >=X% from session open within last N bars; (2) candle K is hammer/shooting star — low-wick >= 2x body, body in upper 1/3, close near high; (3) candle K+1 retests range of K (touches near K's high) but does NOT close above K's high; (4) entry at K+2 open; (5) measure T+30m, T+60m, EOD return. |
| Specification gaps | (a) X = cascade magnitude threshold? Try {0.3%, 0.5%, 0.7%, 1.0%}. (b) N = look-back window for cascade? Try {10, 15, 20} 5m bars. (c) "near low/high" tolerance — 0.05%? 0.10%? (d) "body in lower/upper" — fixed 1/3 vs ratio. (e) Wick ratio threshold — 2x body vs 3x body. |
| Data source | `hist_spot_bars_5m` 12 months NIFTY + SENSEX, IST window 09:15-15:30 only. Apply TD-029 timezone workaround: `replace(tzinfo=None)`. Apply Bug B4 workaround: filter by time, no `is_pre_market` column. Apply Rule 15: page_size=1000. |
| Outcome metric | T+30m / T+60m / EOD spot return from K+2 entry. Win rate at each horizon. EV per trade in points. Sample size per side (bearish, bullish). |
| Comparison hurdles | If WR < ~70% for either side, edge is not actionable. Need N >= 30 events per side per symbol for statistical power. Compare against existing edges: BEAR_OB MIDDAY+PO3 (88.2% N=17), E1 PDH first-sweep (93.3% N=15) — must beat baseline. |
| Risk of overlap | Pattern may overlap with: (a) E1 PDH first-sweep (similar capitulation+reversal but daily TF); (b) BEAR_OB MORNING (5m TF, 100% N=9 — small N); (c) Wyckoff spring/upthrust (well-documented in TA literature). If found-edge is just a 5m re-expression of E1, the additive value is questionable. |
| Estimated cost | 3-5 hours research time. Single research session. Could fit Session 15 if ENH-79 deferred to Session 16. |
| Today's data point | 2026-04-30 NIFTY 15m candle K ~09:45 IST. Verify candle attributes via `hist_spot_bars_5m` after EOD rollup tomorrow. Treat as live N=1 prior. |
| Forbidden ground | Do NOT cherry-pick threshold values. Use canonical sweep methodology from Exp 29 v2 (full-year sweep, multiple thresholds, report best/worst). Do NOT mix Bearish + Bullish samples — they are independent hypotheses. |
| Output | Compendium entry with N, WR, EV per side per symbol per horizon. Decision: PASS (file as ENH-N), MARGINAL (revisit later), FAIL (rule out). |


---

## Session 15 New ENH Entries (2026-05-02)

No new ENH IDs filed Session 15. Six experiments registered (Exp 44 result, Exp 47, Exp 47b, Exp 50, Exp 50b, ADR-003 Phase 1 result). Two production patches shipped to zone builders, closing TD-S1-BEAR-FVG-DETECTOR (see `tech_debt.md`). ENH-85's design space was reduced by Exp 47b — see status update in Part 1 Status Summary table.

### Exp 44 — Intraday Inverted Hammer Reversal After Cascade (RESULT — FAIL, with TZ-bug caveat)

| Field | Detail |
|---|---|
| Status | **FAIL (with caveat — re-run as Exp 44 v2 with era-aware Rule 16 if revisiting). Resolves PROPOSED state from Session 14 EOD addendum entry above.** |
| Session run | Session 15 (2026-05-01) |
| Script | `experiment_44_inverted_hammer_cascade.py` |
| Sweep grid | 6 cascade thresholds × 4 lookback bars × 2 sides (bull/bear) × 3 horizons (6/12/30 bars) × 2 symbols = 288 cells |
| Decision rule (set Session 14) | PASS = (sym, cas, lb, side, horizon) cell with WR ≥ 70 AND N ≥ 30 |
| Result | **No cell met both thresholds simultaneously.** Highest-WR cells were N=4-12 (underpowered). Highest-N cells (>50) had WR in 48-58% range. |
| Verdict | FAIL. The seed observation (NIFTY 09:30-10:00 IST V-recovery on 2026-04-30) appears to be a single memorable instance, not a generalisable rule. |
| Caveat (filed Session 15 post-result) | Script applied CLAUDE.md Rule 16 verbatim to the entire 263-day sample. The post-04-07 era (~22 sessions) requires era-aware TZ handling per TD-NEW-RULE16-ERA-AWARE — those sessions had ~9 in-session bars analysed instead of ~76. Verdict survives a back-of-envelope re-evaluation (the affected sessions are too few to flip the cell counts) but a v2 re-run with era-aware TZ would close the verdict cleanly. Filed as Session 16 Candidate C contingent. |
| Forbidden ground | (Already-honored.) Did NOT cherry-pick threshold; canonical sweep methodology preserved per the Session 14 entry above. |
| Builds | None. |

---

### Exp 47 — Direction Stability Anchor (INVALID — superseded by Exp 47b)

| Field | Detail |
|---|---|
| Status | **INVALID (tautological by construction). Superseded by Exp 47b.** |
| Session run | Session 15 (2026-05-01) |
| Script | `experiment_47_direction_stability_anchors.py` |
| Question | Does using `ret_30m`, `ret_60m`, or `ret_session` as a slower anchor instead of ENH-55 V4's current anchor reduce same-session direction flips? |
| Method | For each `hist_pattern_signals` row, compute candidate-anchor-direction; per-pattern WR using the anchor as policy and `ret_30m` sign as outcome; same-session flip count per anchor. |
| Result | Per-pattern WR 99-100% across all anchors. Suspicious — no real-world classifier achieves this. |
| Diagnosis | `ret_30m` was used as BOTH the policy (direction sign) and the outcome (forward T+30m return per Rule 14). Tautological — predicting the sign of `ret_30m` from the sign of `ret_30m`. |
| Verdict | INVALID by construction. Filed Exp 47b with backwards-looking anchors only. |
| Builds | None. |

---

### Exp 47b — Backwards-Looking Anchors (HYPOTHESIS FALSIFIED — closes ENH-85 "slower anchor" path)

| Field | Detail |
|---|---|
| Status | **HYPOTHESIS FALSIFIED. ENH-85 design space reduced — "use a slower anchor" path closed; remaining options: hard PO3 lock OR persistence filter.** |
| Session run | Session 15 (2026-05-01) |
| Script | `experiment_47b_backwards_anchor.py` |
| Question | Are `ret_30m_back` (close[B] - close[B-6]) or `ret_60m_back` (close[B] - close[B-12]) more stable than `ret_session` (anchored to session open, the ENH-55 V4 baseline) as direction policy? |
| Method | Pulled `hist_pattern_signals` rows + matching `hist_spot_bars_5m` for backwards lookups. Computed both backwards anchors per signal. Counted same-session flips per anchor. Per-pattern WR Rule-14-compliant (forward `ret_30m` as outcome, backwards anchor as policy). |
| Result | ret_session baseline: 0.27 flips/session. ret_30m_back: 0.85 flips/session = **3.13x baseline** (213% MORE flips). ret_60m_back: 0.77 flips/session = **2.87x baseline** (187% MORE flips). Per-pattern WR using backwards anchors: 53-58% (within noise). |
| Verdict | FALSIFIED. Backwards-looking rolling anchors flip MORE than `ret_session`, not less. `ret_session` (anchored to session open, zero rolling) is structurally the slowest available anchor — there is no "slower anchor" path remaining for ENH-85. |
| Implication for ENH-85 | Remaining design paths reduced to: (a) **hard PO3 lock** (anchor flips disallowed regardless of underlying signal — risks fighting genuine reversals; needs Exp 43-style stability backing per Session 13 entry), or (b) **persistence filter** (require N consecutive same-direction signals before flipping — adds latency but preserves adaptation). Decision deferred to Session 16+. |
| Note on Exp 43 relationship | Exp 47b answers a subset of Exp 43's question (option 2 of 4: "slower anchor"). Options 1 (persistence filter), 3 (hysteresis), and 4 (PO3 as soft prior weight) remain testable. Exp 43 itself remains PROPOSED at register-level — Session 16+ work. |
| Builds | None. ENH-85 design space recorded. |

---

### Exp 50 — FVG-on-OB Cluster vs Standalone (FAIL with anomaly; bug-discovery vehicle)

| Field | Detail |
|---|---|
| Status | **FAIL with monotonic INVERSION anomaly, BULL-only — invalid until re-run on now-symmetric data. CRITICAL: the bug-discovery vehicle for the BEAR_FVG defect closed this session.** |
| Session run | Session 15 (2026-05-01) |
| Script | `experiment_50_fvg_on_ob_cluster.py` |
| Question | Per ICT's PD Array Matrix theory: does an FVG forming after price leaves an OB (same direction) have higher WR than a standalone FVG? Theory: cluster = institutional sponsorship + structural foundation = higher probability. |
| Method | 3×3 sweep (lookback_min ∈ {30, 60, 120} × proximity_pct ∈ {0.20, 0.50, 1.00}). For each cell: cluster = BULL_FVG within `lookback_min` after a BULL_OB and within `proximity_pct` of OB zone; standalone = BULL_FVG with no preceding BULL_OB in window. Outcome: ret_30m sign. |
| Decision rule | PASS = cluster WR ≥ standalone + 5pp AND cluster EV_30m ≥ standalone × 1.3 AND cluster N ≥ 30. |
| Result (BULL-only) | **1/9 cells PASS** (only 120min/0.50% loose threshold). Pattern shows monotonic INVERSION of ICT prediction at tight thresholds: cluster WR is WORSE than standalone WR. Effect grows as thresholds tighten (largest at 30min/0.20% = -36.2pp WR delta). Headline cell (60min/0.50%, N=75): cluster WR 24.0% vs standalone 36.7%, delta -12.7pp. |
| Verdict | FAIL with anomaly. Inversion plausibly explained by either (a) exhaustion (tight cluster = price moved fast = FVG forms over-extended, fails more), or (b) survivorship bias (cluster definition expands → standalone bucket loses higher-quality FVGs that had a "background" OB → standalone WR drops disproportionately at loose thresholds, making cluster look better). Tested via Exp 50b. |
| **CRITICAL ancillary finding** | During Exp 50 setup, discovered `hist_pattern_signals` contains 1,261 BULL_FVG and **0 BEAR_FVG** signals over 13 months. Per market structure (sustained bear periods clearly visible on weekly chart Apr 2024-2026, NIFTY -17% Aug 2024 → Mar 2025), this is impossible. Operator challenged. Triggered five-step `diagnostic_bear_fvg_audit.py`, six-bug code review of `build_ict_htf_zones_historical.py`, two production patches (S1.a + S1.b), full historical backfill (40,384 rows), live builder patch (S1.a + S1.b + 1H BEAR_FVG mirror), and signal table rebuild (6,318 → 7,484 rows; **BEAR_FVG 0 → 795**). Closes TD-S1-BEAR-FVG-DETECTOR. |
| Carry-forward | Re-run on now-symmetric data in Session 16 (Candidate A). 18 cells (vs 9) with bear-side data added. Drop EV-ratio criterion when re-running (when both standalone and cluster EVs are tiny negatives, the ratio is meaningless); keep WR-delta + N-floor only. |
| Builds | None directly from Exp 50. The bug discovery led to S1 production patches — that's the actual deliverable from this experiment. |

---

### Exp 50b — Velocity Test on Cluster Inversion (MARGINAL, BULL-only)

| Field | Detail |
|---|---|
| Status | **MARGINAL — direction supports exhaustion at headline cell but sweep robustness fails. BULL-only — invalid until re-run on now-symmetric data.** |
| Session run | Session 15 (2026-05-01) |
| Script | `experiment_50b_fvg_on_ob_velocity.py` |
| Question | Is Exp 50's cluster-FVG inversion driven by exhaustion? Hypothesis: tight clusters imply fast pre-FVG velocity, FVG forms over-extended, fails more often. Test: partition cluster-FVGs by velocity quartile and check if WR drops as velocity rises. |
| Method | Reused Exp 50 cluster definition. For each cluster pair: velocity = abs(fvg_price - ob_price) / delta_min. Partitioned cluster pairs into velocity quartiles per cell. Measured WR per quartile. |
| Decision rule | PASS = headline cell shows DECREASING WR Q1→Q4 AND ≥60% of voting cells (N≥20) show same direction. |
| Result (BULL-only) | Headline cell (60min/0.50%, N=75): Q1 WR 36.8% → Q4 WR 13.3% — DECREASING (consistent with exhaustion). Sweep across 7 voting cells (N≥20): 3 of 7 = 43% DECREASING (below the 60% bar). 1 anomaly cell (120min/1.00%, N=242): Q1 55.7% → Q4 47.5% INCREASING. |
| Verdict | MARGINAL. Direction supports exhaustion hypothesis at the headline cell, but sweep robustness fails. Could be (a) real exhaustion, (b) survivorship in standalone bucket (Exp 50 alternative explanation), or (c) noise. Cannot ship as a filter without bidirectional validation. |
| Carry-forward | Re-run on bidirectional data in Session 16 (Candidate A). The bigger N from bear-side data should make quartile partitioning more robust. |
| Builds | None. |

---

### ADR-003 Phase 1 — Zone Respect-Rate (RESULT — INVALID, methodology bug)

| Field | Detail |
|---|---|
| Status | **INVALID — script-side TZ-handling methodology bug. v3 with era-aware Rule 16 needed. Filed Session 16 Candidate C.** Resolves PROPOSED state from Session 14 EOD addendum. |
| Session run | Session 15 (2026-05-01) |
| Script | `adr003_phase1_zone_respect_rate_v2.py` |
| ADR file | See `ADR-003-ict-zone-architecture-review.md` for full Phase 1 results section + carry-forward Phase 1 v3 plan. |
| Question | Per Session 14 ADR-003 proposal: do `ict_htf_zones` and `hist_ict_htf_zones` zones reflect price-pivot behaviour? Compute respect-rate over last 10 trading days per timeframe. |
| Result (raw, before discovery) | 0% respect across all timeframes for both symbols. Apparent post-04-07 `hist_spot_bars_5m` coverage 27.5%. 0 D zones in 10-day lookback. |
| Diagnosis (mid-investigation) | The 27.5% coverage was a script-side bug, not a pipeline failure. Script applied CLAUDE.md Rule 16 (`replace(tzinfo=None)` then filter to 09:15-15:30) verbatim to post-04-07 era. Post-04-07 bars are stored as true UTC; the verbatim filter dropped to ~9 bars/day. Real coverage post-04-07 is ~100% per `diagnostic_bar_coverage_audit_v3.py` (which uses `trade_date` column instead). The 0 D zones in lookback was a separate finding — D-zone non-FVG validity in the historical builder is exactly 1 day (TD-S2.b), so D zones expire by next session. |
| Verdict | INVALID. Methodology compromised by script-side TZ-handling bug AND latent D-zone validity bug. Phase 1 v3 with era-aware Rule 16 needed before any architecture verdict can be drawn. |
| Builds | Two TDs filed — TD-NEW-RULE16-ERA-AWARE (CLAUDE.md Rule 16 needs era-aware addendum, addressed Session 16 Candidate C) and reinforcement of TD-S2.b (D-zone single-day validity for non-FVG). |

---

### Status update — TD-S1-BEAR-FVG-DETECTOR (CLOSED Session 15)

This is a TD entry, not an ENH. Cross-referenced here because closure is the headline outcome of Session 15 and affects how downstream ENH evidence is interpreted (any Compendium entry's "WR on BEAR_FVG" derived from `hist_pattern_signals` pre-Session-15 was based on 0 rows and is invalid). See `tech_debt.md` for full TD detail; summary:

| Field | Detail |
|---|---|
| Discovered | Session 15 (during Exp 50 setup) |
| Symptom | 0 BEAR_FVG signals in `hist_pattern_signals` over 13 months despite 1,129 canonical 3-bar BEAR_FVG shapes existing in `hist_spot_bars_5m` (60d) and 46-50% of recent sessions being bear days. |
| Root cause | `build_ict_htf_zones_historical.py` and `build_ict_htf_zones.py` had no W BEAR_FVG branch in `detect_weekly_zones()` (only BULL_FVG implemented). `detect_daily_zones()` had no FVG of either direction. `detect_1h_zones()` (live builder only) had only BULL_FVG. Three locations affected, two scripts. Signal builder `build_hist_pattern_signals_5m.py` was direction-symmetric and innocent. |
| Fix shipped | S1.a (W BEAR_FVG branch in both builders) + S1.b (D BULL_FVG + D BEAR_FVG in both builders, with new constants `FVG_D_MIN_PCT=0.10%` and `D_FVG_VALID_DAYS=5`) + 1H BEAR_FVG mirror in live `detect_1h_zones()`. Full historical backfill ran (40,384 rows; W BEAR_FVG=1,384). Live builder ran (85 rows). Signal rebuild via existing `build_hist_pattern_signals_5m.py` (no code change — direction-symmetric verified): hist_pattern_signals 6,318 → 7,484 rows. **BEAR_FVG 0 → 795.** |
| Files renamed | `build_ict_htf_zones.py` and `build_ict_htf_zones_historical.py` are now the patched versions; originals preserved as `_PRE_S15.py`. |
| Status | **CLOSED 2026-05-02.** |
| Bugs intentionally NOT fixed (catalogued as separate TDs) | TD-S2.a (D-OB definition non-standard ICT — uses move bar K+1 as OB instead of opposing prior K), TD-S2.b (D-zone non-FVG validity = 1 day), TD-S3.a (PDH/PDL `+/-20pt` hardcoded, 3.2x narrower in % on SENSEX vs NIFTY), TD-S3.b (zone status workflow write-once-never-recompute on historical builder). All four candidates for Session 16 Candidate D. |

---

*End Session 15 closeout block. Next session entries land below this line.*
