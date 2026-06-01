# MERDIAN Strategy Reference v1 — "151 Trading Strategies" Integration Framework

**Source:** Kakushadze, Z. & Serur, J.A. (2018). "151 Trading Strategies." SSRN Electronic Journal. https://ssrn.com/abstract=3247865

**Document version:** v1 (2026-06-01, S42)  
**Authority:** ENH-114 (candidate, pending filing)  
**Status:** Reference library — catalog + decision tree for strategy integration

---

## I. Overview

MERDIAN currently operates a **directional options buying system** (Phase 4A manual execution, Phase 4B systematic). This reference document catalogs 151+ strategies from Kakushadze & Serur and identifies which are:
1. **Directly implementable** within NIFTY/SENSEX infrastructure
2. **Timing-ready** via existing MERDIAN signals (ICT zones, gamma metrics, IV context)
3. **Backtestable** against historical NIFTY/SENSEX data
4. **Risk-manageable** within current margin/liquidity constraints

The paper provides 550+ mathematical formulas for Greeks, premium decay, hedge ratios, and optimal sizing — all applicable to MERDIAN's signal layer.

---

## II. MERDIAN Current State (S42)

**Current trading posture:** Directional naked options
- **Instrument:** NIFTY/SENSEX call/put
- **Entry signal:** ICT zone structure (PDH/PDL, OB, FVG), market structure (regime, breadth)
- **Position management:** Gamma-based (gamma_metrics, GEX heatmap), IV context, pin risk
- **Risk control:** Stop-loss anchored to spot (ADR-012), max loss per trade
- **Greeks awareness:** gamma_metrics table (max_gamma_strike, pin_risk_score, vega context)

**Signal layer capabilities:**
- ICT primitives (D/H/M5 zones per ADR-004 canonical)
- Gamma exposure (per-strike, per-regime)
- Volatility (India VIX capture, IV skew via option chain)
- Market breadth (WCB score, constituent momentum)
- Orderflow proxy (market_breadth_intraday, bid-ask ticks via Dhan)

---

## III. Strategy Catalog — Options (per Kakushadze & Serur Chapter 2)

### A. Single-Leg Strategies (Current MERDIAN core)

| Strategy | Paper ref | Greeks | MERDIAN ready? | Notes |
|---|---|---|---|---|
| **Long Call** | §2.1 | Δ+, Γ+, Θ-, Ν+ | ✅ YES | Directional up. Current production trade. |
| **Long Put** | §2.1 | Δ-, Γ+, Θ-, Ν+ | ✅ YES | Directional down. Current production trade. |
| **Covered Call** | §2.2 | Δ+, Γ-, Θ+ | ⏳ CANDIDATE S43 | Sell upside cap, collect theta. Requires stock ownership (not NIFTY/SENSEX cash). Could use synthetic long (buy call + sell put). |
| **Covered Put** | §2.3 | Δ-, Γ-, Θ+ | ⏳ CANDIDATE S43 | Sell downside put on existing short. Same synthetic mechanics. |
| **Protective Put** | §2.4 | Δ+, Γ+, Θ- | ⏳ CANDIDATE S43 | Long call + buy put (insurance). Maps to **Collar** (below). |
| **Protective Call** | §2.5 | Δ-, Γ+, Θ- | ⏳ CANDIDATE S43 | Long put + buy call (upside protection on short). Tail-risk hedge. |

**Decision rule:** Single-leg strategies ✅ READY. Multi-leg requires: (a) simultaneous execution, (b) margin headroom, (c) Greeks aggregation in position tracker.

---

### B. Two-Leg Directional Spreads (Gamma/Theta trade-off)

| Strategy | Paper ref | Max profit | Max loss | Θ decay | MERDIAN ready? | Priority | Notes |
|---|---|---|---|---|---|---|---|
| **Bull Call Spread** | §2.6 | Width - debit | Debit paid | Θ+ (short leg) | ⏳ S43 | P1 | Buy ATM call + Sell OTM call. Directional up, capped loss. |
| **Bear Call Spread** | §2.8 | Width - debit | Debit paid | Θ+ (short leg) | ⏳ S43 | P1 | Sell ATM call + Buy OTM call. Directional down, capped loss. |
| **Bull Put Spread** | §2.7 | Width - credit | Credit width | Θ+ (both legs) | ⏳ S43 | P2 | Sell ATM put + Buy OTM put. Sells volatility. |
| **Bear Put Spread** | §2.9 | Width - credit | Credit width | Θ+ (both legs) | ⏳ S43 | P2 | Sell OTM put + Buy further OTM put. Neutral/down bias. |
| **Calendar Spread** | §2.18-19 | Premium decay | Directional move | Θ+ (short-term leg) | ⏳ S44 | P3 | Buy far-term + Sell near-term (same strike). Theta harvesting. |
| **Diagonal Spread** | §2.20-21 | Varies | Varies | Θ+ mixed | ⏳ S44 | P3 | Buy far call + Sell near OTM call (different strikes). Time + direction. |

**Decision rule:** Spreads require **margin headroom** (credit spreads need naked short margin). Priority: Bull Call (simple, directional), Bull Put (theta income, fits gamma-neutral regimes). Defer calendar/diagonal to Phase 1.5+ (complexity in rolling mechanics).

---

### C. Volatility-Directional Hybrids (Multi-leg, gamma+vega play)

| Strategy | Paper ref | Best for | Δ sens | Γ sens | Ν sens | MERDIAN ready? | Priority | Notes |
|---|---|---|---|---|---|---|---|
| **Collar** | §2.53 | Cap/protect | Medium | Low | Low | ⏳ S43 | **P0** | Long call + short call (cap) + long put (protection). Maps to pin-risk-aware positioning. |
| **Iron Condor** | §2.50 | Range-bound | ~0 | Low | Short | ⏳ S44 | P2 | Sell ATM call spread + Sell ATM put spread. Premium collection in low-vol regimes. |
| **Iron Butterfly** | §2.44-45 | Tight range | ~0 | Medium | Short | ⏳ S44 | P2 | Sell ATM call/put spreads at center. Tighter capital requirement than condor. |
| **Long Straddle** | §2.22 | Volatility expansion | ~0 | High | Long | ⏳ S43 | P1 | Buy ATM call + put. Profits on any direction if Δ realized > Δ implied. |
| **Short Straddle** | §2.25 | Volatility contraction | ~0 | High (short) | Short | ⚠️ S44+ | P3 | Sell ATM call + put. Naked gamma short. High margin risk. |
| **Long Strangle** | §2.23 | Vol expansion, cheaper | ~0 | Med-High | Long | ⏳ S43 | P1 | Buy OTM call + put (wider wings). Similar to straddle, lower cost. |
| **Short Strangle** | §2.26 | Vol contraction, cheaper | ~0 | Med-High (short) | Short | ⚠️ S44+ | P3 | Sell OTM call + put. Premium collection with wings. |

**Decision rule:** Collar is **P0 for S43** (directional + protection, aligns with ADR-012 pin-risk logic). Straddle/strangle **P1 candidate** if India VIX > 18 AND market structure shows "equilibrium" (PDH/PDL narrow, regime flat). Iron Condor/Butterfly **P2+** (requires margin buffer, deferrable to Phase 1.5).

---

### D. Ratio & Exotic Spreads (High leverage, tail risk)

| Strategy | Paper ref | Use case | Risk profile | MERDIAN ready? | Notes |
|---|---|---|---|---|---|
| **Call Ratio Backspread** | §2.36 | High-conviction short | Unlimited long risk | ❌ NOT S43 | Buy 1× OTM call + Sell 2× ATM call. Max loss if spot rallies hard. Deferrable. |
| **Put Ratio Backspread** | §2.37 | High-conviction long | Unlimited short risk | ❌ NOT S43 | Buy 1× OTM put + Sell 2× ATM put. Max loss if spot drops hard. Deferrable. |
| **Ratio Call Spread** | §2.38 | Short-biased premium | Undefined short risk | ❌ NOT S43 | Sell 2× OTM calls + Buy 1× ATM call. Asymmetric payoff. Avoid Phase 4A/4B. |
| **Ratio Put Spread** | §2.39 | Long-biased premium | Undefined long risk | ❌ NOT S43 | Sell 2× OTM puts + Buy 1× ATM put. Asymmetric payoff. Avoid Phase 4A/4B. |

**Decision rule:** ❌ **Avoid all ratio spreads in Phase 4A/4B.** Tail risk (undefined loss) incompatible with managed-account operations. File as **candidate ADR-005 amendment** (execution-anchor doctrine refined): "Ratio spreads require pre-trade drawdown reserve + automatic liquidation on breach; not recommended for discretionary Phase 4A."

---

### E. Spread Variants (Butterflies, Condors, etc.)

| Strategy | Paper ref | Δ | Max profit | Max loss | MERDIAN ready? | Notes |
|---|---|---|---|---|---|
| **Long Call Butterfly** | §2.40 | ~0 | Wing width | Debit paid | ⏳ S44 | Buy 1 call, sell 2 middle calls, buy 1 OTM call. Profits near middle strike. Capital-efficient. |
| **Short Call Butterfly** | §2.42 | ~0 | Debit paid | Wing width | ⏳ S44 | Inverse. Profits if move away from middle. |
| **Long Put Butterfly** | §2.41 | ~0 | Wing width | Debit paid | ⏳ S44 | Put equivalent. |
| **Long Call Condor** | §2.46 | ~0 | Wider profit zone | Debit paid | ⏳ S44 | 4-leg (buy ATM, sell 2× OTM, buy far OTM). Wider range than butterfly. |
| **Long Iron Condor** | §2.50 | ~0 | Both spreads profit | Max of both debits | ⏳ S44 | Call spread + put spread (synthetic condor). Common vol-neutral strategy. |

**Decision rule:** ⏳ **S44+ only.** Complexity: 3–4 simultaneous legs, precise strike selection, tight monitoring. Defer until margin tracking + position aggregation proven over ≥20 days.

---

## IV. Timing Signals — MERDIAN Integration Points

### Which MERDIAN signals trigger which strategies?

**Signal 1: Market structure (ICT zones)**

```
IF (market_state == PDH/PDL_established AND spot_near_level):
    → Collar (protect upside, profit from level hold)
    → Iron Butterfly (sell at level, profit on range hold)

IF (market_state == FVG_breakout AND momentum_confirmed):
    → Bull Call Spread (directional with capped loss)
    → Long Call (naked, high Γ advantage)

IF (market_state == zone_consolidation AND range_narrow):
    → Iron Condor (sell premium, profit on range)
    → Short Straddle (gamma short, theta positive)
```

**Signal 2: Volatility (India VIX + IV context)**

```
IF (india_vix > 18 AND iv_skew > 2%):
    → Long Straddle / Strangle (vol expansion play)
    → Gamma concentration at max_gamma_strike

IF (india_vix < 15 AND iv_skew < 1%):
    → Iron Condor / Iron Butterfly (premium collection)
    → Short straddle (vol contraction play, theta+)

IF (iv_implied > iv_realized):
    → Sell volatility via spread (call spread, put spread)
    → Avoid long gamma strategies
```

**Signal 3: Gamma exposure (gamma_metrics)**

```
IF (spot_near_max_gamma_strike AND gamma_concentration_high):
    → Collar (protect gamma short risk)
    → Straddle (gamma long, profit if realized_vol > implied_vol)

IF (pin_risk_score > 70 AND dom_strike == ATM):
    → Reduce naked short gamma
    → Switch to spreads (defined-loss, managed gamma)

IF (sustained_time_factor < 5 days_to_expiry):
    → Short theta strategies (short straddle, iron condor)
    → Calendar spreads (harvest near-term decay)
```

**Signal 4: Market breadth (WCB + constituent momentum)**

```
IF (wcb_score < 40 AND regime == bear):
    → Bear Put Spread / Bear Call Spread (directional down, capped loss)
    → Protective Put (hedge long positions)

IF (wcb_score > 60 AND regime == bull):
    → Bull Call Spread / Bull Put Spread (directional up)
    → Covered Call (income on upside move)
```

---

## V. Backtesting & Validation Framework

### How to test each strategy against NIFTY/SENSEX history

Per MERDIAN_Testing_Protocol_v1.md, each strategy candidate requires:

1. **Cohort definition:** Historical windows matching signal criteria
   - Example: "Collar tested on 50 windows where (PDH established AND India VIX > 16)"
   - Min N=30 cohorts for statistical validity

2. **Greeks validation:** Confirm paper's formulas match Dhan API Greeks
   - Kakushadze Table (§2.53, p. 37): Collar Delta, Gamma, Theta vs. observed
   - Tolerance: ±2% on Greeks (bid-ask slippage)

3. **Walk-forward backtest:** Per ENH-72 contract pattern
   - Initial window: 10 trading days
   - Roll window: 5-day increments
   - Metrics: Win rate, Profit factor, Max drawdown, Sharpe

4. **Cross-vendor validation:** Spot-check results vs. QuantLib or StockMojo
   - Example: Condor premium = Kakushadze formula?
   - Example: Butterfly Greeks match TradingView overlay?

### Candidate backtesting schedule

| Strategy | Estimated effort | Timeline | Window | Expected outcome |
|---|---|---|---|---|
| **Collar** | 4 hrs (well-defined Greeks) | S43 Week 1 | 50 windows, 10d each | Win rate 55–60% on defined-loss trades |
| **Bull Call Spread** | 3 hrs (simple 2-leg) | S43 Week 2 | 50 windows, 5d each | Win rate 50–55%, Θ+ edge visible |
| **Long Straddle** | 6 hrs (vega-heavy) | S43 Week 3 | 30 windows (high-vol only) | Win rate 48–52%, profitable only if realized_vol > implied_vol by >1% |
| **Iron Condor** | 8 hrs (4-leg precision) | S43 Week 4 | 30 windows (range-bound) | Win rate 55–60%, theta decay profitable in consolidation |

---

## VI. Implementation Roadmap

### Phase 1 (S43 — next 2 weeks)

**Deliverables:**
- ENH-114 filed: "Options strategies library — Collar + Bull Call Spread pilot"
- Backtest framework: Greeks validation (Dhan vs. Kakushadze formulas)
- Collar strategy: 50-window backtest (PDH/PDL + protection logic)
- Bull Call Spread: 50-window backtest (directional spreads)

**Code changes:**
- `strategy_router.py` (new): Route trades based on market_state → strategy selection
- `collar_Greeks.py` (new): Collar Greeks calculation + P&L aggregation
- `strategy_validation.py` (new): Compare observed vs. formula Greeks

**Risks:**
- Margin requirements (spreads need 2× buffer vs. naked)
- Dhan API Greeks lag (Kakushadze assumes Black-Scholes; Dhan uses model-specific)
- Simultaneous execution (legs must fill near-simultaneously to avoid slippage)

**Go/no-go decision:** After 2 weeks, review backtest results. If Collar + Bull Call Spread show win rate >53% + Sharpe >0.5 → approve for Phase 4A discretionary testing. Otherwise, pivot to different strategies or defer.

### Phase 1.5 (S44 — weeks 3–4)

**Conditional on Phase 1 PASS:**
- Long Straddle / Strangle: Trigger on India VIX > 18 + equilibrium structure
- Iron Condor / Iron Butterfly: Range-bound consolidation only
- Calendar Spreads: Theta harvesting in flat regimes

### Phase 2 (S45+)

**Systematic automation:**
- `execute_multi_leg.py` (new): Simultaneous order execution for spreads
- `position_aggregator.py` (enhanced): Greeks roll-up across multi-leg positions
- `strategy_profit_attribution.py` (new): Decompose P&L by Greeks (Δ, Γ, Θ, Ν)

---

## VII. Risk Management & Guardrails

### Margin guardrails (hard constraints)

```python
# Spreads require defined risk = margin requirement
margin_requirement = max_loss_per_spread

# Hard limit: spreads cannot exceed 30% of available margin
total_spread_margin_used = SUM(margin_requirement for all open spreads)
if total_spread_margin_used > 0.30 * available_margin:
    REJECT_new_spread_order()
    ALERT("Spread margin limit breached")
```

### Greeks guardrails (soft constraints)

```python
# Portfolio-level Greeks must stay within bounds
net_delta = SUM(δ for all positions)
net_gamma = SUM(γ for all positions)
net_vega = SUM(ν for all positions)
net_theta = SUM(θ for all positions)

# Monitoring ranges (per ADR-002 "force not direction")
if ABS(net_delta) > 500:  # ~500 points directional exposure
    ALERT("High directional delta — consider hedging")
    
if net_gamma < -0.005:  # Significant gamma short
    ALERT("Gamma short — market move >2% causes loss")
    REDUCE_gamma_short_positions()

if net_vega > 50:  # Long volatility exposure
    ALERT("High long vega — vulnerable to vol collapse")
```

### Execution guardrails

```python
# Spreads must execute within max slippage
spread_max_slippage_pct = 0.5  # 0.5% total slippage tolerance

# Limit 1-leg distance (e.g., call spread must have legs within 100 points)
max_strike_distance = 100  # points

# Simultaneous fill requirement: all legs must fill within 30 seconds
timeout_multi_leg_order = 30  # seconds
```

---

## VIII. Glossary & Formula Reference

### Key papers formulas (condensed)

**Collar (§2.53, Kakushadze p. 37):**
```
P&L = C_long(K₁) - C_short(K₂) - P_long(K₃)
Max Profit = K₂ - K₁ - Net Premium
Max Loss = K₁ - K₃ - Net Premium
Δ = δ_long_call - δ_short_call - δ_long_put
Θ = θ_long_call - θ_short_call - θ_long_put
```

**Bull Call Spread (§2.6, Kakushadze p. 20):**
```
P&L = C_long(K₁) - C_short(K₂), K₁ < K₂
Max Profit = K₂ - K₁ - (C(K₁) - C(K₂))
Max Loss = C(K₁) - C(K₂)
Δ = δ_long - δ_short ∈ [0, 1]
Θ = θ_long - θ_short (positive near expiry)
```

**Long Straddle (§2.22, Kakushadze p. 25):**
```
P&L = C(K) + P(K) - 2×Premium
Max Profit = Unlimited
Max Loss = 2×Premium (if spot stays at K)
Δ ≈ 0 (delta-neutral)
Γ = γ_call + γ_put (high, positive)
Θ = θ_call + θ_put (negative, theta decay)
Ν = ν_call + ν_put (long vega)
Break-even = K ± 2×Premium
```

---

## IX. Decision Tree — Which Strategy to Use?

```
START: New trading opportunity identified (signal from ICT zones, gamma, IV)

Q1: What is the directional bias?
  ├─ BULLISH → Q2a
  ├─ BEARISH → Q2b
  └─ NEUTRAL → Q3

Q2a: Bullish signal. How strong + confident?
  ├─ Strong + high-conviction (momentum confirmed)
  │  └─ Use: Long Call or Bull Call Spread
  ├─ Moderate (directional but with protection needed)
  │  └─ Use: Collar or Protective Call
  └─ Weak (cautious, cap upside wanted)
     └─ Use: Bull Call Spread (capped profit)

Q2b: Bearish signal. How strong?
  ├─ Strong + high-conviction
  │  └─ Use: Long Put or Bear Call Spread
  ├─ Moderate (want to sell premium on downside)
  │  └─ Use: Bear Put Spread
  └─ Weak + short-biased
     └─ Use: Protective Put (hedge long)

Q3: Neutral signal. What is the regime?
  ├─ Consolidation (tight range, low volatility)
  │  └─ Use: Iron Condor or Iron Butterfly (sell premium)
  ├─ Equilibrium (PDH/PDL established, spot in range)
  │  └─ Use: Short Straddle or Short Strangle (if margin>40%)
  ├─ High volatility (India VIX > 18, spreads wide)
  │  └─ Use: Long Straddle or Long Strangle (buy vol)
  └─ Earnings / event risk
     └─ Use: Straddle (profit on surprise move size)

Q4: Risk management check
  ├─ Do we have margin for spreads? (30% rule)
  │  └─ YES → Proceed with multi-leg
  │  └─ NO → Revert to single-leg (Long Call / Long Put)
  ├─ Is Greece aggregation working?
  │  └─ YES → Proceed
  │  └─ NO → Single-leg only
  └─ Is slippage < 0.5% expected?
     └─ YES → Proceed
     └─ NO → Wait for better liquidity

EXECUTE: Select final strategy, route to order execution layer
MONITOR: Track Greeks, monitor exit signals per ADR-012
```

---

## X. Reference Links & Sources

**In-repo:**
- `MERDIAN_Testing_Protocol_v1.md` — backtest framework
- `ADR-002-market-structure-philosophy.md` — force-based Greeks interpretation
- `ADR-012-spot-anchored-sl-doctrine.md` — stop-loss methodology
- `MERDIAN_Experiment_Compendium_v1.md` — historical experiment patterns

**External:**
- Kakushadze & Serur (2018). "151 Trading Strategies." [PDF](https://ssrn.com/abstract=3247865)
- Chapter 2 (Options): pp. 17–39 (best for NIFTY/SENSEX implementation)
- Chapter 3 (Stocks): pp. 41–57 (useful for WCB weighting logic)
- Appendix (Backtesting code): pp. 300+ (walk-forward framework reference)

---

**MERDIAN Strategy Reference v1 — 2026-06-01 (S42). Pending ENH-114 filing for S43 action.**
