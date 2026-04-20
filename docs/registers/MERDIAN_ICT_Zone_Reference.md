# MERDIAN ICT HTF Zone Behaviour Reference

**Purpose:** Field guide for reading and trading each zone type on the MERDIAN chart.
**Applies to:** NIFTY and SENSEX weekly/daily zones from `build_ict_htf_zones.py`
**Last updated:** 2026-04-15

---

## Zone Types at a Glance

| Zone | Color | Timeframe | Nature | Position |
|---|---|---|---|---|
| BEAR_OB | Red | Weekly | Supply / Resistance | Above price |
| PDH | Orange | Weekly/Daily | Liquidity / Resistance | Above price |
| BULL_OB | Green | Weekly/Daily | Demand / Support | Below price |
| BULL_FVG | Green | Weekly | Imbalance / Gap | Below price |
| PDL | Teal | Weekly/Daily | Liquidity / Support | Below price |

---

## 1. BEAR_OB — Bearish Order Block (Supply Zone)

**What it is:**
The last bullish candle(s) before a significant bearish move. Institutions sold heavily from this level. Their unfilled sell orders remain here, creating supply.

**Expected behaviour when price enters:**
- First touch: expect rejection. Price often wicks into the zone and reverses.
- Volume spike likely as resting sell orders are triggered.
- If SHORT_GAMMA regime: signal engine may fire BUY_PE here.

**If price trades THROUGH (closes above zone_high):**
- Zone is mitigated — institutional supply absorbed.
- Bullish signal: buyers overpowered sellers at this level.
- Expect acceleration upward toward next supply zone.
- Old BEAR_OB often flips to support on pullback.

**Trading context:**
- Wide BEAR_OB (zone_high - zone_low > 500pts): distribution zone, multiple weeks of selling. Expect multiple rejection attempts before break.
- Narrow BEAR_OB (<100pts): single candle supply. May be absorbed quickly on strong momentum.
- Overlapping BEAR_OBs (cluster): highest resistance area. Multiple institutions selling. Requires very strong momentum to break.

**NIFTY example:** W BEAR_OB 24,401–25,020 — formed May 2025 during decline from ATH. Five months of memory. Expect strong selling pressure on first test.

---

## 2. PDH — Prior Day/Week High (Liquidity Level)

**What it is:**
The high of the prior trading session (D) or prior week (W). Buy-stop orders and stop-losses from short sellers cluster just above this level — this is "buy-side liquidity."

**Expected behaviour when price approaches:**
- Price often gravitates toward PDH to collect liquidity before reversing.
- A brief spike above PDH followed by reversal = **liquidity sweep** (bearish trap).
- Clean break and hold above = genuine breakout, momentum continuation.

**If price trades THROUGH and holds above:**
- Bullish: buy-stops triggered, price finds new support at old PDH.
- Old PDH flips to support — look for pullback-to-PDH entries.

**If price sweeps above and reverses (wick):**
- Bearish: liquidity grab. Smart money sold into buy stops.
- Expect move back down. Stronger the wick, stronger the reversal signal.

**Key distinction:** PDH is not structural support/resistance like an OB — it's a **liquidity magnet**. Price visits it to grab orders, then makes its real move.

**NIFTY example:** W PDH 24,284–24,324 — nearest resistance above current price. Only 54 points away. High probability of test tomorrow.

---

## 3. BULL_OB — Bullish Order Block (Demand Zone)

**What it is:**
The last bearish candle(s) before a significant bullish move. Institutions bought heavily from this level. Their unfilled buy orders remain here, creating demand.

**Expected behaviour when price returns:**
- Strong buying interest expected on retest.
- Price often bounces sharply from BULL_OB.
- If LONG_GAMMA regime: flip level may adjust — BULL_OB provides context for signal engine.

**If price trades THROUGH (closes below zone_low):**
- Zone is mitigated — institutional demand absorbed.
- Bearish signal: sellers overpowered buyers at this level.
- Expect acceleration downward toward next demand zone.
- May flip to resistance on bounce.

**Daily BULL_OB vs Weekly BULL_OB:**
- D BULL_OB: intraday significance. Tested and potentially mitigated within 1-2 sessions.
- W BULL_OB: multi-week significance. Takes sustained selling to break. Much stronger.

**SENSEX example:** D BULL_OB 75,937–76,848 — tested Apr 13-15 and held perfectly. This is now the key reference support for the current rally. Break below with close = bearish reversal signal.

---

## 4. BULL_FVG — Bullish Fair Value Gap (Imbalance)

**What it is:**
A gap in price where a candle's low is higher than the candle two bars prior's high. Price moved so fast that no trading occurred in this range — creating an imbalance that markets tend to fill.

**Expected behaviour:**
- Price typically returns to fill the gap at some point.
- On the return visit, FVG acts as support (for bullish FVG).
- The **midpoint** of the FVG is the most important level — 50% retracement of the gap.

**If price enters the FVG:**
- Normal rebalancing — not immediately bearish.
- Watch for bounce at midpoint or zone_low.
- Full fill (price trades through entire gap) = imbalance resolved. Next support below.

**If price closes below FVG zone_low:**
- Gap fully filled — bearish. Original move may be fully retraced.
- Look for next demand zone below.

**SENSEX example:** W BULL_FVG 73,164–75,868 — massive gap created by tariff panic recovery. The Apr 13-15 pullback filled the upper portion. Gap is now partially filled. If price drops back to 73,164, expect strong institutional buying as the gap is fully tested.

---

## 5. PDL — Prior Day/Week Low (Liquidity Level)

**What it is:**
The low of the prior session or week. Sell-stop orders and stop-losses from long holders cluster just below — this is "sell-side liquidity."

**Expected behaviour:**
- Price often sweeps below PDL to grab sell-stops before reversing up.
- Clean break and hold below = genuine breakdown, bearish continuation.
- Wick below PDL + strong close above = classic **liquidity sweep** (bullish trap reversal).

**If price sweeps below and reverses:**
- Bullish: sell-side liquidity grabbed. Smart money bought the dip.
- This is the JUDAS_BEAR pattern at the intraday level.
- Stronger the wick and recovery, stronger the bullish signal.

**If price closes below PDL:**
- Bearish: genuine breakdown. Next PDL below becomes the target.
- Old PDL may flip to resistance on bounce.

**NIFTY example:** D PDL 23,546–23,566 — today's low. If NIFTY dips to 23,546 tomorrow and recovers, that's a sell-side sweep and bullish reversal signal. If it closes below 23,546, bearish continuation toward W BULL_FVG at 22,714.

---

## Zone Interaction Playbook

### Scenario 1: Price approaches a BEAR_OB (supply)
1. Watch for first candle reaction in the zone
2. If rejection + bearish close → short signal possible (BUY_PE)
3. If price stalls but holds → wait for next candle confirmation
4. If clean close above zone_high → zone breached, next BEAR_OB is target

### Scenario 2: Price approaches a BULL_OB (demand)
1. Watch for bounce on first touch
2. If bounce + bullish close → long signal possible (BUY_CE)
3. If price stalls but holds → wait for confirmation
4. If close below zone_low → zone broken, next BULL_OB below is target

### Scenario 3: Price sweeps a PDH (liquidity grab — bearish)
1. Price spikes above PDH, creates wick
2. Closes back below PDH high
3. This is a sell-side setup — institutions sold into buy stops
4. Target: PDL below or nearest BULL_OB

### Scenario 4: Price sweeps a PDL (liquidity grab — bullish)
1. Price dips below PDL, creates wick
2. Closes back above PDL low
3. This is a buy-side setup — institutions bought the dip
4. Target: PDH above or nearest BEAR_OB
5. If this occurs at a W BULL_OB: **HTF sweep reversal** (ENH-54 pattern)

### Scenario 5: Overlapping zones (confluence)
Multiple zones at the same price level = highest conviction area.
Example: W PDH + W BEAR_OB at same level → double resistance. Harder to break, stronger rejection expected.

---

## MERDIAN Signal Engine Integration

| Zone | Signal engine impact |
|---|---|
| W BEAR_OB above price | MTF context = HIGH (bearish overhead) |
| W BULL_OB below price | MTF context = HIGH (bullish support) |
| D BULL_OB | Intraday support reference for signal confidence |
| PDH/PDL nearby | TIER adjustment — proximity to liquidity adds caution |
| Zone breach | `ict_zones` updated next morning via `build_ict_htf_zones.py` |

---

## Morning Routine with Zones

Before market open each day:

1. Note current price vs nearest zones above and below
2. Identify nearest BEAR_OB (first resistance) and nearest BULL_OB (first support)
3. Note if any PDH/PDL within 100-200 points — likely to be swept intraday
4. When MERDIAN fires a signal, cross-reference: is price near a zone? Does the zone direction match the signal?
5. Zone confluence with signal = higher conviction trade

---

## Weekly Update Protocol

Every Sunday night or Monday pre-market:

```powershell
python build_ict_htf_zones.py
python check_htf_zones.py
```

Then regenerate the TradingView Pine Script with updated zone levels.
Zones change as new weekly bars form — PDH/PDL update every week, OBs persist until mitigated.

---

*MERDIAN ICT Zone Behaviour Reference — 2026-04-15*
*Cross-reference: MERDIAN_Enhancement_Register_v7.md (ENH-37, ENH-54)*
