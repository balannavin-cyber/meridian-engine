# MERDIAN Enhancement Register v3

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Enhancement_Register_v3.md |
| Supersedes | MERDIAN_Enhancement_Register_v2.md (2026-04-06) |
| Updated | 2026-04-09 |
| Sources | Enhancement Register v1 · V18D session (2026-04-04/05) · V18E live canary sprint (2026-04-06 through 2026-04-09) |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document. |
| Authority | Tracks proposals, not decisions. Decisions live in master Decision Registry. |
| Update rule | Update in the same session that produces new architectural thinking. Commit immediately. |

---

## V2 Changes from V1

| Change | Detail |
|---|---|
| ENH-28 status | IN PROGRESS → SUBSTANTIALLY COMPLETE |
| ENH-29 status | IN PROGRESS → PIVOTED — architecture changed this session |
| ENH-07 status | PROPOSED → IN PROGRESS (infrastructure now exists) |
| ENH-33 NEW | Pure-Python Black-Scholes IV engine (built this session) |
| ENH-34 NEW | Live monitoring dashboard (built and deployed this session) |
| ENH-35 NEW | Historical signal validation and accuracy measurement (next build) |
| ENH-36 NEW | hist_* to live table promotion pipeline |
| Summary table | Updated to reflect all changes |

---


## V3 Changes from V2

| Change | Detail |
|---|---|
| ENH-34 status | PRODUCTION — confirmed stable across 4 live sessions (Apr 6-9). Dashboard v2 deployed. |
| ENH-35 status | NOT BUILT — next engineering priority after shadow gate confirmed |
| Shadow gate | Updated: 7/10 sessions complete (Apr 6, 7, 8, 9 counted) |
| Operational notes | MERDIAN_Market_Tape_1M disabled permanently (Apr 7). breadth Local-only confirmed. |

## How to Read This Register

Each entry has:
- **ID** — sequential ENH-nn
- **Title** — what the enhancement is
- **Source** — where the idea originated
- **Description** — what it does and why it matters
- **Dependency** — what must exist before this can be built
- **Priority Tier** — 1 (now) / 2 (after Heston) / 3 (after signal validation) / 4 (long-term)
- **Commercial Relevance** — internal only / customer-facing / standalone data product
- **Status** — PROPOSED / IN PROGRESS / SUBSTANTIALLY COMPLETE / SHADOW LIVE / CLOSED

---

## Tier 1 — Actionable Now (No Heston Required)

---

### ENH-01: ret_session — Session Return to Momentum Engine

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 1 (original 5-improvement plan) |
| Status | IN PROGRESS — compute_momentum_features_v2_local.py built. Shadow Step 5a. Wiring pending. |
| Dependency | None |
| Priority Tier | 1 |
| Commercial Relevance | Internal — improves signal quality |

**What it does:** Adds `ret_session` to the momentum engine. Measures price move from session open (09:15 IST) to current time. Distinguishes a sustained intraday trend from a short-term bounce.

**Why it matters:** On 16 March, `ret_5m` was positive (short bounce) while the session was deeply bearish. `ret_session` would have confirmed the bearish trend and prevented the CONFLICT veto from firing incorrectly. Highest-impact improvement from the original enhancement plan.

**Implementation path:** Already built in `compute_momentum_features_v2_local.py`. Wire into options runner as Shadow Step 5a (try/except isolated). Run shadow for 2 weeks before live promotion.

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

---

### ENH-05: CONFLICT Resolution Logic

| Field | Detail |
|---|---|
| Source | MERDIAN Enhancement Plan Phase 1 / Phase 4 |
| Status | NOT BUILT — requires ENH-01 first. Now also benefits from ENH-35 accuracy data. |
| Dependency | ENH-01 (ret_session) shadow validation + ENH-35 accuracy measurement |
| Priority Tier | 1 (sequenced after ENH-01 + ENH-35) |
| Commercial Relevance | Internal |

**What it does:** Replaces unconditional CONFLICT → DO_NOTHING veto with weighted signal aggregation. Uses ret_session as tie-breaker when short-horizon momentum conflicts with breadth + gamma.

**Update V2:** ENH-35 (historical accuracy measurement) now provides empirical data on which CONFLICT configurations were actually profitable vs not. This should inform the resolution logic rather than using arbitrary weights.

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

---

### ENH-28: Historical Data Ingest Pipeline

| Field | Detail |
|---|---|
| Source | V18B/V18C session — historical dataset procurement |
| Status | **SUBSTANTIALLY COMPLETE** (was IN PROGRESS) |
| Dependency | ENH-31 (expiry calendar) — still open for production accuracy |
| Priority Tier | 1 |
| Commercial Relevance | Internal foundation |

**What it does:** Vendor 1-minute OHLCV option bars ingested into `hist_option_bars_1m`. Spot bars in `hist_spot_bars_1m`. Full ingest log and completeness checking.

**Update V2 (V18D session):**
- NIFTY: 247 days (April 2025 – March 2026) ✅
- SENSEX: 247 days after vendor correction (previously 185 days due to BSE_INDICES packaging error) ✅
- Vendor correction received and ingested 2026-04-05: 4,818,720 new rows
- Three derived hist tables now built: `hist_gamma_metrics` (244 dates each), `hist_volatility_snapshots` (488 pairs), `hist_market_state` (487 pairs)
- Remaining gap: ENH-31 (expiry calendar) still needed for DTE accuracy near expiry changes

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

---

### ENH-31: Expiry Calendar Utility

| Field | Detail |
|---|---|
| Source | V18B session |
| Status | NOT BUILT |
| Dependency | None — must precede ENH-28 production run for accurate DTE |
| Priority Tier | 1 |
| Commercial Relevance | Internal |

**What it does:** Handles pre/post 1 Sep 2025 expiry rule change (NIFTY Thursday→Tuesday, SENSEX Tuesday→Thursday). Required for accurate DTE calculations near expiry transitions. The V18D backfill batch worked around this with expiry-aligned window generation but the core utility is still needed.

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

---

### ENH-35: Historical Signal Validation and Accuracy Measurement (NEW)

| Field | Detail |
|---|---|
| Source | V18D session — identified as next build after hist_market_state completion |
| Status | NOT BUILT — next priority |
| Dependency | hist_market_state (built) + hist_spot_bars_1m (built) |
| Priority Tier | 1 |
| Commercial Relevance | Internal — gates Phase 4 promotion |

**What it does:** Measures directional accuracy of the MERDIAN signal engine against historical data.

**Algorithm:**
1. For each bar_ts in `hist_market_state` where a BUY_PE or BUY_CE signal would be generated (using signal logic against gamma_regime, breadth_regime, iv_regime, momentum_regime), record the signal
2. Look up `hist_spot_bars_1m` at T+15m, T+30m, T+60m
3. Compute: direction correct (BUY_PE = spot fell, BUY_CE = spot rose)?
4. Aggregate by: gamma_regime × breadth_regime combination, DTE bucket, VIX regime, time of day
5. Output: accuracy matrix by regime combination, confidence calibration curve

**Why this matters:**
- Without empirical accuracy data, Phase 4 promotion is entirely gate-count based (shadow sessions) with no signal quality measurement
- The accuracy matrix tells us which regime combinations are actually predictive and which are noise
- Directly informs ENH-05 (CONFLICT resolution) — weight regimes by their empirical accuracy not by intuition
- 487 date/symbol pairs × ~376 bars/day = ~183K potential signal evaluations — statistically meaningful

**Output tables needed:**
- `hist_signal_evaluations` — per bar_ts: signal generated, direction, spot at T+15/30/60, correct/incorrect
- `hist_accuracy_summary` — aggregated: accuracy by regime combination, by hour, by DTE bucket

**Script to build:** `run_validation_analysis.py`

---

### ENH-36: hist_* to Live Table Promotion Pipeline (NEW)

| Field | Detail |
|---|---|
| Source | V18D session — documented in DEC-V18D-01 as deferred build |
| Status | NOT BUILT |
| Dependency | ENH-35 (validation must confirm data quality before promotion) |
| Priority Tier | 1 |
| Commercial Relevance | Internal governance |

**What it does:** Promotes validated rows from `hist_gamma_metrics`, `hist_volatility_snapshots`, and `hist_market_state` into the live tables (`gamma_metrics`, `volatility_snapshots`, `market_state_snapshots`). Enables the live system to use historical data for backtesting, walk-forward validation, and training.

**Requirements:**
- Provenance tagging: add `data_source='historical_backfill'` column to live tables before insert
- Conflict handling: historical bar_ts values should not collide with live (different timestamp precision) but must be verified
- Audit: INSERT SELECT in a single transaction with row count verification
- Gate: ENH-35 accuracy measurement must pass a minimum accuracy threshold before promotion is allowed

**Script:** `promote_hist_to_live.py` — dry-run mode first, then live run with explicit confirmation flag

---

## Tier 2 — After Signal Validation (Heston Required)

---

### ENH-09: Heston Calibration Layer

| Field | Detail |
|---|---|
| Source | Architecture session 2026-03-31 |
| Status | PROPOSED |
| Dependency | ENH-33 (BS IV engine provides market IVs to calibrate against) + Signal validation (ENH-20 gate) |
| Priority Tier | 2 |
| Commercial Relevance | Foundation for all Tier 2 enhancements |

**Update V2:** ENH-33 (BS IV engine) is now built and validated. The market IVs it computes across all strikes are the calibration targets for Heston. This removes one prerequisite — the IV surface data now exists historically. The remaining gate is signal validation passing Phase 4 threshold.

**What it does:** Fits Heston stochastic volatility model parameters (kappa, theta, xi, rho, v0) to the observed IV surface at each cycle. Provides a coherent vol surface rather than isolated per-strike IVs.

---

### ENH-10 through ENH-21

*(Unchanged from v1 — all depend on ENH-09. See v1 for full entries.)*

---

## Tier 3 — After Classical Validation

### ENH-22 through ENH-25

*(Unchanged from v1.)*

---

## Tier 4 — Long-Term (Post-Classical Validation)

### ENH-26: Quantum Annealing for Heston Calibration
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
