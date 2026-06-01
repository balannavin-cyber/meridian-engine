# MERDIAN Strategy Quick Card v1

**Print this. Laminate. Keep at terminal.**

---

## SIGNAL → STRATEGY ROUTER (30-second decision)

### Market Structure Signal

```
SIGNAL: FVG Breakout (ICT zone breach + momentum)
├─ BULLISH FVG → Bull Call Spread (or Long Call)
├─ BEARISH FVG → Bear Put Spread (or Long Put)
└─ Max loss: Spread width or full premium

SIGNAL: PDH/PDL Established (spot near level, range narrow)
├─ Near PDH + upside capped → Collar (buy call, sell call, buy put)
├─ Near PDL + downside capped → Protective Put
└─ Profit from level hold, limited upside

SIGNAL: Consolidation (tight range, no direction)
├─ India VIX < 15 → Iron Condor (sell premium both sides)
├─ India VIX > 18 → Long Straddle (buy volatility)
└─ Max loss (condor) = spread widths; Max loss (straddle) = premium paid
```

### Volatility Signal

```
SIGNAL: India VIX > 18
├─ Implied vol high → SELL vol (spreads)
├─ Buy Straddle if realized_vol expected > implied_vol
└─ Key: Iron Condor if BULLISH, Straddle if NEUTRAL

SIGNAL: India VIX < 15
├─ Implied vol low → BUY vol (naked calls/puts)
├─ Sell vol via Iron Condor (theta harvest)
└─ Key: Iron Butterfly if capital-constrained
```

### Gamma/Pin Risk Signal

```
SIGNAL: Spot NEAR max_gamma_strike (±50 points)
├─ Gamma concentration high → PROTECT (Collar, not naked short)
├─ If long gamma → Straddle/Strangle (sell premium on moves)
└─ If short gamma → Reduce size or switch to spreads

SIGNAL: pin_risk_score > 70 (high pinning risk at ATM strike)
├─ Reduce naked calls/puts at ATM
├─ Switch to Collar (cap upside, protect downside)
└─ Monitor until expiry < 2 days
```

### Breadth Signal (WCB)

```
SIGNAL: WCB_score > 60 (bullish breadth)
├─ Bull Call Spread or Bull Put Spread (directional up)
└─ Avoid Bear strategies

SIGNAL: WCB_score < 40 (bearish breadth)
├─ Bear Put Spread or Long Put (directional down)
└─ Avoid Bull strategies

SIGNAL: WCB_score = 50 ± 5 (neutral)
├─ Straddle/Strangle or Iron Condor (vol play, not direction)
└─ Avoid directional spreads
```

---

## STRATEGY CHECKLIST (before executing)

```
☐ Margin available? (spreads use 2–3× more margin)
  └─ If <30% margin headroom → CANCEL, use naked only
  
☐ Greeks aggregation working? (position tracker enabled)
  └─ If NOT → Single-leg only (no spreads)
  
☐ Slippage expected < 0.5%? (check bid-ask width × legs)
  └─ If NOT → WAIT for better liquidity
  
☐ Expiry sufficient? (≥3 days for spreads, ≥5 days for theta plays)
  └─ If <3 days → Avoid multi-leg (theta decay accelerates)
  
☐ Size manageable? (max loss ≤ 2% of account)
  └─ If NOT → REDUCE size by 50%
```

---

## QUICK REFERENCE: Greeks By Strategy

| Strategy | Δ | Γ | Θ | Ν | Best when | Max loss |
|---|---|---|---|---|---|---|
| **Long Call** | + | + | - | + | Bullish directional | Premium paid |
| **Long Put** | - | + | - | + | Bearish directional | Premium paid |
| **Bull Call Spread** | + | ~0 | + | ~0 | Bullish, cap profit | Debit paid |
| **Bear Put Spread** | - | ~0 | + | ~0 | Bearish, sell premium | Spread width |
| **Collar** | ~0 | Low | ~0 | Low | Directional + protect | Defined (K₁ - K₃) |
| **Straddle (long)** | 0 | ++ | -- | ++ | Vol expansion | Premium paid |
| **Straddle (short)** | 0 | -- | ++ | -- | Vol contraction | Unlimited ⚠️ |
| **Iron Condor** | 0 | Low | ++ | Short | Range-bound, low vol | Spread width |
| **Calendar Spread** | ~0 | ~0 | ++ | + | Theta harvest | Debit paid |

---

## QUICK MATH: Profit/Loss Zones

**Bull Call Spread (Buy K₁ Call @ $A, Sell K₂ Call @ $B, K₁ < K₂):**
```
Max Profit = (K₂ - K₁) - (A - B)
Max Loss = A - B
Breakeven = K₁ + (A - B)
Profit if spot > K₂ - (A - B)
Loss if spot < K₁ + (A - B)
```

**Collar (Long K₁ Call @ $A, Short K₂ Call @ $B, Long K₃ Put @ $C):**
```
Max Profit = (K₂ - K₁) - A - C + B ≈ (K₂ - K₁) - Net Premium
Max Loss = (K₁ - K₃) - A - C + B ≈ (K₁ - K₃) - Net Premium
Breakeven = K₁ + Net Premium (upside)
Breakeven = K₃ - Net Premium (downside)
```

**Long Straddle (Buy K Call @ $A, Buy K Put @ $B):**
```
Max Profit = Unlimited
Max Loss = A + B (if spot stays at K at expiry)
Breakeven = K ± (A + B)
Profit if |Spot - K| > A + B
```

---

## EXECUTION CHECKLIST (LIVE ORDER)

```
STEP 1: Confirm strategy from decision tree above
STEP 2: Check margin + Greeks aggregation
STEP 3: Calculate max loss & confirm ≤ 2% of account
STEP 4: Set ORDER:
  └─ Single-leg: Market order OK
  └─ Spreads: Limit order (specify legs + max slippage)
STEP 5: EXECUTE legs (simultaneous if multi-leg)
STEP 6: Confirm fills, track Greeks in position tracker
STEP 7: Set EXIT RULES per ADR-012:
  ├─ Profit target (50% of max profit)
  ├─ Stop loss (spot anchor + 2% move)
  ├─ Time stop (close 2 days before expiry)
  └─ Greeks stop (if γ flips sign, close)
```

---

## RISK LIMITS (DO NOT EXCEED)

```
❌ DO NOT:
   • Use spreads if margin < 40% available
   • Trade more than 3 multi-leg positions at once
   • Use ratio spreads (undefined loss)
   • Use short straddle (gamma short unlimited loss)
   • Trade overnight if gamma_concentration > 80%

✅ DO:
   • Use Collar for downside protection (ADR-012)
   • Use Bull Call Spread for capped-loss directional
   • Use Long Straddle if India VIX > 18 AND realized_vol expected > implied
   • Monitor Greeks continuously (refresh every 5 min)
   • Close spreads 2 days before expiry (theta accelerates)
```

---

**MERDIAN Strategy Quick Card v1 — Print, laminate, keep at terminal. Update frequency: Monthly (or per ENH-114 phase approval).**

*Source: MERDIAN_Strategy_Reference_v1.md + Kakushadze & Serur (2018) "151 Trading Strategies"*
