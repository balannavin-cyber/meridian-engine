# MERDIAN Enhancement Register v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN Enhancement Register v1 |
| Created | 2026-03-31 |
| Sources | MERDIAN Enhancement Plan (original 5-improvement plan) · MERDIAN Master V18 v2 Section 12 · Architectural thinking sessions 2026-03-31 (Heston/Monte Carlo, Bloomberg function mapping, Braket quantum, API commercialisation) · Session 2026-04-01 (historical ingest pipeline, outcome measurement layer, SMDM gap analysis, storage architecture) |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document — updated whenever architectural thinking produces new enhancement candidates. |
| Authority | This register tracks proposals, not decisions. Decisions (with rejected alternatives) live in V18 v2 Section 17 Decision Registry. |
| Update rule | Update this file in the same session that produces new architectural thinking. Commit to Git immediately. |

---

## How to Read This Register

Each entry has:
- **ID** — sequential ENH-nn within tier
- **Title** — what the enhancement is
- **Source** — where the idea originated
- **Description** — what it does and why it matters
- **Dependency** — what must exist before this can be built
- **Priority Tier** — 1 (now) / 2 (after Heston) / 3 (after signal validation) / 4 (long-term)
- **Commercial Relevance** — internal only / customer-facing / standalone data product
- **Status** — PROPOSED / IN PROGRESS / SHADOW LIVE / CLOSED

---

## Tier 1 — Actionable Now (No Heston Required)

These can be built against the current architecture. No new data sources, no model changes, no prerequisites beyond what is already live.

---

### ENH-01: ret_session — Session Return to Momentum Engine

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 1 (original 5-improvement plan, triggered by 16 March NIFTY −300pt miss) |
| Status | IN PROGRESS — compute_momentum_features_v2_local.py built. Shadow Step 5a. Wiring to runner pending. |
| Dependency | None — market_spot_snapshots already contains all required data |
| Priority Tier | 1 |
| Commercial Relevance | Internal — improves signal quality |

**What it does:** Adds a session-horizon return field (`ret_session`) to the momentum engine. Measures price move from session open (09:15 IST) to current time. Distinguishes a sustained intraday trend from a short-term bounce.

**Why it matters:** On 16 March, `ret_5m` was positive (short bounce) while the session was deeply bearish. The positive `ret_5m` created a CONFLICT that vetoed the breadth, gamma, and PCR signals. `ret_session` would have confirmed the bearish trend and prevented the CONFLICT veto from firing incorrectly. This is the single highest-impact improvement from the original enhancement plan.

**Implementation path:** Already built in `compute_momentum_features_v2_local.py`. Must be wired into the options runner as Shadow Step 5a (try/except isolated). Then run shadow for 2 weeks before live promotion.

---

### ENH-02: Put/Call Ratio (PCR) Signal

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 2 (options flow metrics) |
| Status | IN PROGRESS — compute_options_flow_local.py built. Shadow Step 3a. Wiring to runner pending. |
| Dependency | None — OI data already in option_chain_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal — improves signal quality |

**What it does:** Computes Put/Call OI ratio from the full option chain snapshot. On 16 March, PCR was 1.82 (PE OI nearly 2× CE OI) — strong structural bearish signal that the system could not read.

**Why it matters:** PCR is a directional structural signal independent of price momentum. It reflects positioning by institutional participants who write options hedges in advance of expected moves. A PCR above ~1.5 combined with gamma SHORT is a high-conviction bearish structural condition.

**Implementation path:** Built in `compute_options_flow_local.py`. Writes to `options_flow_snapshots`. Wire as Shadow Step 3a.

---

### ENH-03: Volume/OI Ratio Signal

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 2 |
| Status | IN PROGRESS — part of compute_options_flow_local.py |
| Dependency | None — volume and OI already in option_chain_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Computes volume-to-OI ratio per strike. High volume/OI (40-54× observed on 16 March at 23000/23100/23200 PE) signals active institutional buying rather than stale open interest accumulation.

**Why it matters:** Stale OI can persist for days without reflecting current intent. Volume/OI > 20 at a specific strike indicates fresh directional flow in the current session, distinguishing live institutional positioning from historical accumulation.

---

### ENH-04: Chain-Wide IV Skew Signal

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 2 |
| Status | IN PROGRESS — part of compute_options_flow_local.py |
| Dependency | None — IV already in option_chain_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Computes IV skew across the full option chain (put IV − call IV at equidistant strikes from ATM). On 16 March, put IV was 4–6% above call IV at every ATM strike — a strong fear signal the system could not see because it only measured ATM IV.

**Why it matters:** ATM-only IV captures the level of volatility but not its direction. Chain-wide skew reveals whether the market is pricing directional fear (steep put skew) or complacency (flat or inverted skew). This is a stronger signal than a single ATM IV point.

---

### ENH-05: CONFLICT Resolution Logic

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 1 / Phase 4 |
| Status | NOT BUILT — requires ENH-01 (ret_session) first |
| Dependency | ENH-01 (ret_session) must be in shadow and validated first |
| Priority Tier | 1 (but sequenced after ENH-01 shadow validation) |
| Commercial Relevance | Internal |

**What it does:** Replaces the current unconditional CONFLICT → DO_NOTHING veto with weighted signal aggregation. When momentum signals conflict (e.g. ret_5m positive but ret_session negative), the current system vetoes all other signals and produces DO_NOTHING. The fix uses ret_session as the tie-breaker: if session return confirms the direction of breadth + gamma, the signal fires despite the short-horizon conflict.

**Why it matters:** The CONFLICT veto was confirmed as a root cause of the 16 March miss. A system that produces DO_NOTHING on its highest-conviction structural conditions because a single short-horizon momentum reading conflicts is systematically wrong.

---

### ENH-06: Pre-Trade Cost Filter (Almgren-Chriss Bid-Ask Model)

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (TRA equivalent) |
| Status | PROPOSED |
| Dependency | None — bid/ask data already in option_chain_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal quality improvement — directly improves signal actionability |

**What it does:** Before any strategy proposal is emitted, computes net debit/credit at bid-ask (not mid-price), computes round-trip cost including exit spread, and suppresses proposals where model edge does not exceed 2× round-trip cost.

**Why it matters:** Currently MERDIAN signals assume mid-price fills. NSE index options have significant bid-ask spreads, especially away from ATM. A strategy that shows ₹20 edge at mid-price may have −₹5 edge at realistic execution prices. The Almgren-Chriss model provides the framework for this calculation and is open-source / implementable in Python.

**Implementation:** Add as a gate step in the signal layer. Requires bid and ask fields from option_chain_snapshots (currently captured). No new data source needed.

---

### ENH-07: Basis-Implied Risk-Free Rate

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (BTMM equivalent) |
| Status | PROPOSED |
| Dependency | None — futures basis already captured in index_futures_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal precision improvement |

**What it does:** Derives the implied risk-free rate from the futures basis (futures_price − spot_price, annualised over DTE) rather than using a hardcoded rate assumption.

**Why it matters:** For weekly expiry options (≤7 days), rate sensitivity is negligible. For monthly and quarterly contracts, the hardcoded rate assumption introduces pricing error. The futures basis already captures the market's current rate expectation — using it costs nothing and improves Heston calibration precision when that layer is built.

**Implementation:** One-line change in market state assembly. `rate = (futures_price / spot_price - 1) * (365 / dte)`. Already have all inputs in index_futures_snapshots and market_state_snapshots.

---

### ENH-08: Vega Bucketing by Expiry in Position Monitoring

| Field | Detail |
|---|---|
| Source | Bloomberg function mapping session 2026-03-31 (PORT equivalent) |
| Status | PROPOSED |
| Dependency | None — expiry data already in option_chain_snapshots |
| Priority Tier | 1 |
| Commercial Relevance | Internal risk management improvement |

**What it does:** In any position monitoring layer, tracks vega exposure by expiry bucket (near-dated vs far-dated) rather than aggregating total vega. A long near-dated vega and short far-dated vega are not offsetting exposures — they are two different factor bets on the vol term structure.

**Why it matters:** Aggregating vega across expiries is a common but incorrect risk practice. It can make a position look flat-vega when it actually has significant term structure exposure. Relevant as soon as MERDIAN begins tracking positions.

---

### ENH-28: Historical Data Ingest Pipeline (Vendor 1m OHLCV)

| Field | Detail |
|---|---|
| Source | Architectural session 2026-04-01 — vendor data acquisition decision |
| Status | IN PROGRESS — hist_ingest_controller.py built (commit b420d4b), vendor delivery pending EOD 2026-04-01 |
| Dependency | ENH-31 (expiry calendar utility) must be built before production run |
| Priority Tier | 1 |
| Commercial Relevance | Internal — foundational for signal validation and backtest harness |

**What it does:** Ingests vendor-supplied 1-minute OHLCV CSV files (NIFTY + SENSEX options, futures, spot) into the three-tier storage architecture. Validates OHLCV integrity, routes segments (options/futures/spot/LEAPs), deduplicates via SHA-256 checksum, batches Supabase upserts at 1000 rows, writes local Parquet warm tier partitioned by year/month/day. Logs completeness checks per expiry per session.

**Why it matters:** Without historical 1m bar data, the outcome measurement layer (ENH-29) cannot compute path-dependent metrics (MFE, MAE, time_to_mfe, drawdown_before_profit). Without those metrics, the signal validation gate (required before any Tier 2 or Tier 3 work) cannot be passed. This is the critical path item.

**Open items:** HIST-01 (expiry calendar logic — pre/post 1 Sep 2025 rule change and holiday rollback must be implemented before production run). HIST-02 (S3 archiver — LocalParquetArchiver interface ready, swap to S3ParquetArchiver when AWS credentials configured).

---

### ENH-29: Signal Premium Outcome Measurement Layer

| Field | Detail |
|---|---|
| Source | Architectural session 2026-04-01 — Track 1 outcome layer |
| Status | IN PROGRESS — signal_premium_outcomes table live, premium_outcome_writer.py built (commit b420d4b). Signal 615 written (entry=233.4). Path metrics pending hist bar data (ENH-28). |
| Dependency | build_trade_signal_local.py context fields populated (fixed 2026-04-01, commit 3727f64) |
| Priority Tier | 1 |
| Commercial Relevance | Internal — signal validation gate. Required before any commercial path. |

**What it does:** For every BUY_CE/BUY_PE signal, measures: entry premium, premium at T+15m/30m/60m/EOD, premium moves in points, capture thresholds (25/50/75/100pts), IV change during trade (IV crush detection), direction correctness, MFE/MAE/time_to_mfe/drawdown_before_profit (from hist_option_bars_1m when available), outcome label (WIN_LARGE/WIN_MEDIUM/WIN_SMALL/SCRATCH/LOSS_SMALL/LOSS_LARGE), failure mode (NEVER_MOVED/MOVED_THEN_REVERSED/IV_CRUSH/THETA_DECAY/WHIPSAW). Stores full entry context for condition-pattern analysis.

**Quant additions beyond basic outcome tracking:** entry_iv_percentile (vs 30-day history), confidence_decile (bucketed 1-10), session_pct_elapsed (0-100), mins_since_prior_signal and consecutive_same_direction (clustering detection), mfe_to_close_giveback_pct (path quality), first_adverse_move_pts (stop calibration input), iv_crushed flag.

**SMDM slots reserved:** smdm_squeeze_score, smdm_squeeze_alert, smdm_signal_suppressed, smdm_pattern_flags, smdm_otm_bleed_pct, smdm_straddle_velocity, smdm_otm_oi_velocity — all NULL columns, populated when Track 2 (ENH-30) is built.

**Open items:** SPO-01 (DTE null in signal_snapshots — derivable from expiry_date as workaround). SPO-02 (live canary validation for build_trade_signal_local.py fix on 2026-04-02).

---

### ENH-30: SMDM Infrastructure (Track 2)

| Field | Detail |
|---|---|
| Source | SMDM Spec V7 gap analysis session 2026-04-01 |
| Status | PARTIALLY BUILT — all read inputs exist and are richer than spec. structural_alerts table not built. straddle_velocity/otm_oi_velocity absent from gamma_metrics. detect_structural_manipulation.py not built. |
| Dependency | ENH-29 (Track 1) stable and live canary passed — do not build Track 2 while context regression fix is unvalidated |
| Priority Tier | 1 |
| Commercial Relevance | Internal — defensive layer, suppresses signals during manufactured move setups |

**Gap analysis vs SMDM Spec V7 (against V18 live system as of 2026-04-01):**
- `structural_alerts` table: NOT BUILT — needs DDL + creation
- `intraday_ohlc`: EXISTS (spec said ADDING) — has session_high/session_low, missing `basis` column
- `gamma_metrics` straddle_velocity/otm_oi_velocity: NOT IN TABLE, NOT IN raw{} JSONB — needs ALTER TABLE + compute_gamma_metrics_local.py update
- `volatility_snapshots`: FAR RICHER than spec — `atm_iv_vs_vix_spread` is functional equivalent of vix_straddle_ratio
- `signal_snapshots`: cautions JSONB and trade_allowed both exist — SMDM writes directly to them, no schema change needed
- `detect_structural_manipulation.py`: NOT BUILT

**Build sequence when Track 2 opens:**
1. `structural_alerts` DDL
2. `ALTER TABLE intraday_ohlc ADD COLUMN basis NUMERIC`
3. `ALTER TABLE gamma_metrics ADD COLUMN straddle_velocity NUMERIC, ADD COLUMN otm_oi_velocity NUMERIC, ADD COLUMN spot_vs_range NUMERIC, ADD COLUMN run_type TEXT`
4. Update `compute_gamma_metrics_local.py` to populate new columns — touches live code, full change protocol required
5. `detect_structural_manipulation.py`
6. Wire to signal pipeline

---

### ENH-31: Expiry Calendar Utility

| Field | Detail |
|---|---|
| Source | Ingest pipeline design session 2026-04-01 |
| Status | NOT BUILT — flagged as open item HIST-01 |
| Dependency | Must be built before ENH-28 production run |
| Priority Tier | 1 |
| Commercial Relevance | Internal — data integrity |

**What it does:** Provides `is_trading_day(date)` and `get_expiry_date(symbol, year, month, weekly=True)` functions handling NSE/BSE expiry calendar rules:
- Pre-1 Sep 2025: NIFTY weekly = Thursday, SENSEX weekly = Friday. Monthly = last Thursday/Friday of month.
- Post-1 Sep 2025: NIFTY weekly = Tuesday, SENSEX weekly = Thursday. Monthly = last Tuesday/Thursday of month.
- Holiday rollback: if computed expiry falls on a market holiday, expiry moves to previous trading day.
- Example: Thursday 26 March 2026 was a holiday — monthly SENSEX expiry moved forward to Wednesday 25 March.

**Why it matters:** Vendor ticker data has correct expiry dates baked in — the ingest controller parses them directly and is not affected. Risk is in derived logic that computes expiry independently: DTE calculations, completeness checks, LEAP horizon filtering, and the SMDM pattern detection for rollover window (DTE 3-5 of monthly). Without this utility, those computations silently produce wrong results around the 1 Sep 2025 rule change boundary and around holidays.

---

### ENH-32: S3 Warm Tier Archiver

| Field | Detail |
|---|---|
| Source | Storage architecture session 2026-04-01 |
| Status | STUBBED — LocalParquetArchiver interface ready in hist_ingest_controller.py |
| Dependency | AWS credentials configured locally + S3 bucket provisioned |
| Priority Tier | 1 (when AWS credentials ready) |
| Commercial Relevance | Internal infrastructure — cost reduction at scale, enables DuckDB-on-S3 backtest harness |

**What it does:** Replaces `LocalParquetArchiver` with `S3ParquetArchiver` in `hist_ingest_controller.py`. Same `write(table, df, trade_date)` interface — controller code unchanged. Writes Parquet to `s3://meridian-warm-tier/{table}/year={y}/month={m}/day={d}/data.parquet` via boto3. Updates `hist_ingest_log.s3_parquet_key` on completion. Configurable via `.env`: `WARM_TIER_BACKEND=local|s3`.

---

## Tier 2 — After Heston Calibration Layer

These require the Heston vol model to be calibrated and running before they can be built. The calibration layer is itself a new component that needs to be built and validated first.

---

### ENH-09: Heston Volatility Model Calibration Layer

| Field | Detail |
|---|---|
| Source | Architectural session 2026-03-31 |
| Status | PROPOSED — foundation for all Tier 2 enhancements |
| Dependency | Classical signal validation showing positive EV (see ENH-20) |
| Priority Tier | 2 |
| Commercial Relevance | Enables Tier 2 enhancements + standalone vol surface data product |

**What it does:** Calibrates Heston stochastic volatility model parameters (κ kappa — mean reversion speed, θ theta — long-run vol, ξ xi — vol of vol, ρ rho — spot/vol correlation, v0 — initial variance) to the observed option chain smile every 5-minute cycle. Writes to `vol_model_snapshots`.

**Why it matters architecturally:** Heston is the minimum viable model for Indian index options because:
- It captures the volatility smile (which Black-Scholes is blind to)
- It provides a calibrated view on where vol is likely to go (mean reversion)
- The rho parameter explains the put skew structurally rather than treating it as an empirical quirk
- All downstream Tier 2 enhancements depend on having calibrated parameters each cycle

**New table required:** `vol_model_snapshots` — per-symbol, per-cycle: ts, symbol, kappa, theta, xi, rho, v0, calibration_rmse, calibration_time_ms.

**New computation step:** `calibrate_vol_model_local.py` — runs between Step 3 (ingest option chain) and Step 4 (compute gamma). ~2–5 seconds on CPU for standard calibration.

**Calibration quality guard:** If calibration RMSE exceeds threshold, suppress all Tier 2 signals for that cycle. Log: "Calibration quality insufficient — model signals suppressed."

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

---

### ENH-26: Quantum Annealing for Heston Calibration

| Field | Detail |
|---|---|
| Source | Amazon Braket session 2026-03-31 |
| Status | RESEARCH TRACK — not actionable at current stage |
| Dependency | ENH-09 (classical Heston calibration proven + positive EV demonstrated) |
| Priority Tier | 4 |
| Commercial Relevance | Infrastructure acceleration — reduces calibration time |

**What it does:** Uses Amazon Braket quantum annealing (D-Wave) to find Heston parameter combinations that minimise the distance between model prices and market prices across all observed strikes. The calibration step is an optimisation problem — QUBO-amenable. Quantum annealing can theoretically find better solutions than classical gradient descent when the parameter landscape has multiple local minima.

**Current reality:** NISQ-era hardware (2026) is not production-ready for this. Relevant after classical Monte Carlo is proven and calibration speed becomes a bottleneck at higher data rates. Estimated realistic window: 2028–2032 for meaningful quantum advantage on financial calibration problems.

**Correct sequencing:** Build classical Heston calibration → validate positive EV → if calibration speed is a bottleneck → explore Braket annealing as acceleration.

---

### ENH-27: Quantum Amplitude Estimation for Monte Carlo Path Simulation

| Field | Detail |
|---|---|
| Source | Amazon Braket session 2026-03-31 |
| Status | RESEARCH TRACK — not actionable at current stage |
| Dependency | ENH-10 (classical Monte Carlo proven + positive EV demonstrated) |
| Priority Tier | 4 |
| Commercial Relevance | Infrastructure acceleration — reduces path simulation time |

**What it does:** Uses quantum amplitude estimation to speed up Monte Carlo integration quadratically. For a problem requiring 1,000,000 classical samples, achieves equivalent accuracy with ~1,000 quantum samples. For a 5-minute cadence system where option gamma explodes near expiry and every millisecond matters, this acceleration has direct operational value.

**Current reality:** Same NISQ constraints as ENH-26. The mathematical mapping is clean and this is one of the most credible near-term quantum finance applications — but "near-term" in quantum computing means post-2028 for production-grade use.

**Correct sequencing:** Build and validate classical Monte Carlo → if path count requirement becomes a latency bottleneck → explore Braket amplitude estimation.

---

## Summary Table

| ID | Title | Tier | Status | Key Dependency |
|---|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | IN PROGRESS | None |
| ENH-02 | Put/Call Ratio signal | 1 | IN PROGRESS | None |
| ENH-03 | Volume/OI ratio signal | 1 | IN PROGRESS | None |
| ENH-04 | Chain-wide IV skew signal | 1 | IN PROGRESS | None |
| ENH-05 | CONFLICT resolution logic | 1 | NOT BUILT | ENH-01 shadow validation |
| ENH-06 | Pre-trade cost filter (Almgren-Chriss) | 1 | PROPOSED | None |
| ENH-07 | Basis-implied risk-free rate | 1 | PROPOSED | None |
| ENH-08 | Vega bucketing by expiry | 1 | PROPOSED | None |
| ENH-28 | Historical data ingest pipeline | 1 | IN PROGRESS | ENH-31 (expiry calendar) |
| ENH-29 | Signal premium outcome measurement | 1 | IN PROGRESS | build_trade_signal_local fix (done) |
| ENH-30 | SMDM infrastructure (Track 2) | 1 | PARTIAL | ENH-29 stable + live canary |
| ENH-31 | Expiry calendar utility | 1 | NOT BUILT | Must precede ENH-28 production run |
| ENH-32 | S3 warm tier archiver | 1 | STUBBED | AWS credentials |
| ENH-09 | Heston calibration layer | 2 | PROPOSED | Signal validation (ENH-20 gate) |
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
| ENH-26 | Quantum annealing for Heston calibration | 4 | RESEARCH TRACK | ENH-09 classical proven |
| ENH-27 | Quantum amplitude estimation for Monte Carlo | 4 | RESEARCH TRACK | ENH-10 classical proven |

---

## Bloomberg Function Mapping

For reference: how MERDIAN's planned capabilities map to the Bloomberg functions discussed in the 2026-03-31 architectural session.

| Bloomberg Function | MERDIAN Status | Gap / Action |
|---|---|---|
| BVOL (vol surface) | Raw material exists (per-strike IV in option_chain_snapshots) | ENH-09 Heston converts raw IV to coherent surface |
| OVME (options pricing) | Not built | ENH-10 Monte Carlo pricing layer |
| MARS (derivatives risk / Greeks) | Partial (gamma_metrics exist) | ENH-10/16/20 for full Greeks per position |
| TRA (pre-trade cost analysis) | Not built | ENH-06 Almgren-Chriss filter — actionable now |
| PORT (factor risk / vega bucketing) | Not built | ENH-08 vega bucketing — actionable now |
| BTMM (rate environment) | Implicit in futures basis | ENH-07 basis-implied rate — actionable now |
| IB (network) | No equivalent | Not relevant to MERDIAN architecture |
| GMM / TOP (macro news) | Not relevant | MERDIAN is not a news-driven system |

---

## New Tables Required (by Tier)

| Table | Required By | Description |
|---|---|---|
| `hist_option_bars_1m` | ENH-28 | Vendor 1m OHLCV for options — hot tier rolling 90-day window |
| `hist_spot_bars_1m` | ENH-28 | Vendor 1m OHLCV for spot index |
| `hist_future_bars_1m` | ENH-28 | Vendor 1m OHLCV for continuous futures |
| `hist_ingest_log` | ENH-28 | Full audit trail per vendor file — SHA-256 dedup |
| `hist_ingest_rejects` | ENH-28 | Row-level rejection log per ingest batch |
| `hist_completeness_checks` | ENH-28 | Bar count verification per expiry per session |
| `aging_policy` | ENH-28 | Configurable hot tier retention (default 90 days) |
| `hist_iv_surface_daily` | ENH-28 | EOD IV surface summary + Heston parameter slots (Phase 2 reserved) |
| `signal_premium_outcomes` | ENH-29 | Signal outcome measurement — entry context, path metrics, capture thresholds, IV crush, failure taxonomy, SMDM slots reserved |
| `structural_alerts` | ENH-30 | SMDM output store — squeeze scores, pattern flags, cautions (NOT YET BUILT) |
| `vol_model_snapshots` | ENH-09 | Per-cycle Heston parameters (kappa, theta, xi, rho, v0, calibration_rmse) |
| `theoretical_option_prices` | ENH-10 | Per-strike fair value, market LTP, mispricing gap, model Greeks |
| `position_monitor` | ENH-18 | Per open position: entry params, current Greeks, model-state exit conditions |
| `calibration_quality_log` | ENH-21 | Per-cycle calibration quality and suppression events |
| `strategy_proposals` | ENH-11–14 | Structured strategy output: type, legs, edge, sizing, exit conditions |

---

*MERDIAN Enhancement Register v1 — last updated 2026-04-01 — Living document, commit to Git after every update*
