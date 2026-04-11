# MERDIAN — All Experiment Results
# Consolidated reference file — all key numbers in one place
# Generated: 2026-04-10
# Sessions: Apr 2025 – Mar 2026 | NIFTY + SENSEX | 247 + 246 sessions

---

## EXPERIMENT 0 — Symmetric Return Distribution
**Period:** Apr 2025 – Mar 2026 | **Bars scored:** 169,823 (T+30m)

### Full Year Base Rate
| Direction | T+15m | T+30m | T+60m |
|---|---|---|---|
| UP | 49.9% | 49.7% | 49.7% |
| DOWN | 50.1% | 50.3% | 50.3% |

**Large moves >0.5% at T+30m: 1.3% of all bars**

### Monthly Base Rate (T+30m)
| Month | UP% | DN% | Large>0.5% | Phase | Character |
|---|---|---|---|---|---|
| Apr 2025 | 52.2% | 47.8% | 4.2% | NEUTRAL | TRENDING |
| May 2025 | 47.0% | 53.0% | 2.2% | NEUTRAL | TRENDING |
| Jun 2025 | 54.2% | 45.8% | 1.2% | NEUTRAL | REVERTING |
| Jul 2025 | 47.8% | 52.2% | 0.2% | NEUTRAL | TRENDING |
| Aug 2025 | 48.1% | 51.9% | 0.0% | NEUTRAL | CHOPPY |
| Sep 2025 | 48.3% | 51.7% | 0.2% | NEUTRAL | TRENDING |
| Oct 2025 | 53.9% | 46.1% | 0.1% | NEUTRAL | REVERTING |
| Nov 2025 | 55.6% | 44.4% | 0.3% | **BULL** | REVERTING |
| Dec 2025 | 49.9% | 50.1% | 0.0% | NEUTRAL | STABLE |
| Jan 2026 | 45.4% | 54.6% | 1.5% | NEUTRAL | TRENDING |
| Feb 2026 | 49.1% | 50.9% | 2.0% | NEUTRAL | STABLE |
| Mar 2026 | 44.7% | 55.3% | 4.2% | **BEAR** | CHOPPY |

### Empirical Phase Boundaries
- NEUTRAL: Apr 2025 → Oct 2025 (7 months)
- BULL: Nov 2025 only (1 month — insufficient for phase analysis)
- NEUTRAL: Dec 2025 → Feb 2026
- BEAR: Mar 2026 only (1 month)

### Key Finding
Market spent 10/12 months NEUTRAL at 1-min bar level. Assumed BULL/BEAR phases were wrong. Vol-regime grouping is the correct analysis framework.

### Time of Day Large Moves (>0.5% at T+30m)
| Zone | N | Large% |
|---|---|---|
| OPEN 09:15-10:00 | 22,140 | 2.0% |
| MORNING 10:00-11:30 | 44,280 | 1.2% |
| MIDDAY 11:30-13:00 | 44,280 | 1.0% |
| AFTERNOON 13:00-14:30 | 44,333 | 1.0% |
| POWER HOUR 14:30-15:30 | 14,790 | 2.3% |

### Magnitude Distribution (T+30m)
| Bucket | UP | DOWN | Total |
|---|---|---|---|
| <0.1% | 52,223 | 50,783 | 103,006 |
| 0.1-0.3% | 27,038 | 29,602 | 56,640 |
| 0.3-0.5% | 3,816 | 4,150 | 7,966 |
| 0.5-1.0% | 1,197 | 891 | 2,088 |
| >1.0% | 66 | 57 | 123 |

---

## EXPERIMENT 2 — Options P&L Simulation (Fixed T+30m exit)
**Patterns scored at T+30m | Options only | ATM CE/PE**

### Core Pattern Results (all DTE, both symbols)
| Pattern | N | WR | T+30m Exp | T+60m Exp |
|---|---|---|---|---|
| BEAR_OB | 68 | 75.9% | +43.2% | +60.5% |
| BULL_OB | 101 | 93.5% | +70.0% | +59.9% |
| BULL_FVG | 269 | 83.8% | +34.1% | +30.4% |
| JUDAS_BULL | 32 | 84.2% | +29.8% | +29.8% |
| JUDAS_BEAR | 21 | 37.5% | -6.0% | -4.8% |
| BEAR_FVG | 225 | 11.5% | -30.7% | -36.0% |
| BEAR_OTE | 53 | 4.8% | -29.7% | -36.4% |
| BEAR_BREAKER | 46 | 0.0% | -45.6% | -44.0% |
| BOS_BULL | 1717 | 93.5% | +33.3% | +33.3% |
| BOS_BEAR | 1667 | 19.7% | -5.9% | -9.6% |

### DTE Breakdown — Key Rows
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BULL_OB\|DTE=0 | 20 | +121.4% | 100% |
| BEAR_OB\|DTE=0 | 16 | +72.5% | 66.7% |
| BULL_OB\|DTE=2-3 | 38 | +50.9% | 100% |
| BULL_OB\|DTE=4+ | 25 | +49.3% | 100% |
| BOS_BEAR\|DTE=0 | 373 | +27.5% | 32.1% |
| BEAR_FVG\|DTE=0 | 68 | -39.8% | 16.3% |

---

## EXPERIMENT 2b — Futures vs Options vs Combined
**Stop: 0.2% | T+30m exit | All structures normalised to 6-unit base**

### Key Finding
Options win everywhere over futures on % basis due to premium leverage.
Futures expectancy 0.1-0.6% per trade vs options 10-70%.
Scale comparison is apples/oranges — capital deployed differs.

### Stop Rate Problem
| Pattern | Stops% at 0.2% stop |
|---|---|
| BEAR_FVG | 69% |
| BULL_FVG | 65% |
| BEAR_OB (SENSEX) | 91% |
| BULL_OB | 28% |

**0.2% stop too tight — within normal 1-minute candle noise.**

### Insurance Option Effectiveness (when futures stop hit)
| Pattern | Recovery Rate |
|---|---|
| JUDAS_BULL | 50% |
| BOS_BULL | 27% |
| BULL_OB | 25% |
| BEAR_FVG | 2% |
| BOS_BEAR | 3% |

**Key finding:** Bullish insurance (PE when long) recovers 25-50% of stops due to vega expansion. Bearish insurance (CE when short) rarely helps — IV compresses when market rises.

---

## EXPERIMENT 2c — Pyramid Entry (v1: T+5m/T+10m, Stop 0.5%)

### Tier Trigger Rates
| Pattern | T2% (T+5m, 0.20%) | T3% (T+10m, 0.40%) |
|---|---|---|
| BEAR_OB | 93% | 62% |
| BULL_OB | 80% | 53% |
| BEAR_FVG | 16% | 8% |
| BULL_FVG | 12% | 3% |
| JUDAS patterns | 12% | 4% |
| BOS/MSS | 1-8% | 0-4% |

### Structure Comparison (T+30m, normalised to 6-unit base)
| Pattern | Fixed-1 | Fixed-6 | Pyramid |
|---|---|---|---|
| BEAR_OB | +0.10% | +0.61% | +0.19% |
| BULL_OB | +0.09% | +0.56% | +0.18% |
| JUDAS_BULL | +0.03% | +0.20% | +0.03% |

**Risk-adjusted: Pyramid gives 31% of Fixed-6 reward for 12% of the risk = 2.6× better Sharpe**

### Key Finding
OBs: pyramid natural fit — T2 fires 80-93% of the time (market confirms immediately)
BOS/MSS: pyramid never fires — 1-6% T2 rate. Always Fixed-1 effectively.
Judas: timing mismatch — needs 15-25 minute window, not 5-10.

---

## EXPERIMENT 2c v2 — Judas Pyramid (T+15m/T+25m confirmation)

### Judas T2/T3 Rate Improvement
| Pattern | v1 T2% | v2 T2% | v1 T3% | v2 T3% |
|---|---|---|---|---|
| JUDAS_BULL | 12% | 44% | 4% | 24% |
| JUDAS_BEAR | 12% | 25% | 0% | 6% |

**Pyramid expectancy unchanged despite higher trigger rate — adds too late, exits too soon.**
**Conclusion: Judas = options only, no pyramid regardless of timing window.**

---

## EXPERIMENT 5 — ATM IV / VIX Stress Test
**Proxy: atm_iv from hist_market_state | VIX not stored historically**
**IV thresholds: LOW<12%, MED 12-18%, HIGH 18-40%**

### Section 1 — IV Baseline (all patterns combined)
| IV Regime | N | AvgIV | T+30m Exp | WR |
|---|---|---|---|---|
| HIGH_IV (18-40%) | 199 | 30.1% | +66.2% | 72% |
| MED_IV (12-18%) | 100 | 14.5% | +26.1% | 71% |
| LOW_IV (<12%) | 37 | 10.2% | +11.6% | 62% |

### Section 2 — Pattern × IV
| Label | N | AvgIV | T+30m Exp | WR |
|---|---|---|---|---|
| BEAR_OB\|HIGH | 22 | 30.4% | +174.6% | 86% |
| BEAR_OB\|MED | 11 | 14.4% | +84.8% | 100% |
| BULL_OB\|HIGH | 51 | 32.4% | +67.3% | 70% |
| BULL_OB\|MED | 10 | 14.7% | +49.3% | 100% |
| BULL_FVG\|HIGH | 111 | 29.1% | +25.7% | 73% |
| BULL_FVG\|MED | 69 | 14.6% | +12.6% | 59% |
| BULL_FVG\|LOW | 23 | 9.9% | -14.3% | 0% |
| JUDAS_BULL\|LOW | 6 | 10.9% | +27.2% | 100% |
| JUDAS_BULL\|MED | 10 | 13.8% | +18.5% | 75% |
| JUDAS_BULL\|HIGH | 15 | 29.2% | +14.2% | 33% |

### Section 3 — VIX Gate Verdict
| Pattern | MED Exp | HIGH Exp | Verdict |
|---|---|---|---|
| BEAR_OB | +84.8% | +174.6% | **REMOVE GATE** |
| BULL_OB | +49.3% | +67.3% | **REMOVE GATE** |
| BULL_FVG | +12.6% | +25.7% | **REMOVE GATE** |
| JUDAS_BULL | +18.5% | +14.2% | REVIEW (neutral) |

### VIX Gate Decision
**REMOVE binary VIX>20 gate for BEAR_OB, BULL_OB, BULL_FVG.**
**Replace with IV-scaled position sizing:**
- atm_iv < 12%: 0.5× lots
- atm_iv 12-18%: 1.0× lots
- atm_iv > 18%: 1.5× lots
- JUDAS_BULL: no scaling (HIGH_IV degrades Judas edge)

**Important caveat:** NIFTY IV range 15.6-31.1%, SENSEX 26.3-31.1% — dataset had no true low-vol periods for SENSEX. LOW_IV findings from NIFTY only.

---

## EXPERIMENT 10 — ICT Pattern Detection
**6,713 pattern occurrences across 493 sessions**

### Baseline PIA (Percentage In Agreement) at T+30m
| Pattern | N | T+30m WR | T+30m Exp |
|---|---|---|---|
| BEAR_OB | 68 | 92.6% | — |
| BULL_OB | 101 | 84.5% | — |
| JUDAS_BEAR | 21 | 95.2% | — |
| JUDAS_BULL | 32 | 81.2% | — |
| BULL_FVG (HIGH context) | — | 64.7% | — |
| Breaker blocks | — | 7-27% | — |
| BOS/MSS (1-min) | — | noise | — |

---

## EXPERIMENT 10b — MTF + CE + DTE
**CE (Consequential Encroachment) does NOT improve OB accuracy on Indian indices.**

### MTF Context Lift
| Pattern | LOW Exp | HIGH Exp | Lift |
|---|---|---|---|
| JUDAS_BULL | +14% | +56.6% | +42.4% |
| BULL_OB | — | — | +25% |
| BEAR_FVG | positive | negative | -20.2% (no benefit) |

**DTE=0:** Most explosive P&L on all patterns. Only take with full MTF confirmation.

---

## EXPERIMENT 10c — MTF × Options P&L
**Full results — pattern × MTF context × DTE**

### Section 1 — Baseline
| Pattern | N | NoD | T+30m Exp | WR |
|---|---|---|---|---|
| BULL_OB | 101 | 66 | +70.0% | 93.5% |
| BEAR_OB | 68 | 39 | +43.2% | 75.9% |
| BULL_FVG | 269 | 149 | +34.1% | 83.8% |
| BOS_BULL | 1717 | 1063 | +33.3% | 93.5% |
| JUDAS_BULL | 32 | 13 | +29.8% | 84.2% |
| MSS_BULL | 1225 | 734 | +27.1% | 92.4% |
| BULL_OTE | 60 | 30 | +25.0% | 89.7% |
| BOS_BEAR | 1667 | 1013 | -5.9% | 19.7% |
| JUDAS_BEAR | 21 | 13 | -6.0% | 37.5% |
| MSS_BEAR | 1182 | 771 | -12.5% | 15.0% |
| BEAR_OTE | 53 | 31 | -29.7% | 4.8% |
| BEAR_FVG | 225 | 125 | -30.7% | 11.5% |
| BEAR_BREAKER | 46 | 29 | -45.6% | 0.0% |

### Section 2 — Pattern × MTF Context (key rows)
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BULL_OB\|MEDIUM | 45 | +132.8% | 100% |
| BEAR_OB\|LOW | 34 | +61.1% | 81% |
| JUDAS_BULL\|HIGH | 9 | +56.6% | 100% |
| BULL_OB\|HIGH | 18 | +44.8% | 100% |
| BEAR_OB\|HIGH | 7 | +5.3% | 67% |
| BEAR_OB\|MEDIUM | 27 | -9.3% | 60% |
| BEAR_FVG\|HIGH | 42 | -44.3% | 5% |
| BEAR_BREAKER\|MEDIUM | 14 | -95.7% | 0% |

### Section 3 — Pattern × DTE (key rows)
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BULL_OB\|DTE=0 | 20 | +121.4% | 100% |
| BEAR_OB\|DTE=0 | 16 | +72.5% | 67% |
| BULL_OB\|DTE=2-3 | 38 | +50.9% | 100% |
| BULL_OB\|DTE=4+ | 25 | +49.3% | 100% |
| BOS_BEAR\|DTE=0 | 373 | +27.5% | 32% |
| BEAR_FVG\|DTE=0 | 68 | -39.8% | 16% |
| BEAR_BREAKER\|DTE=0 | 6 | -65.5% | 0% |

### Section 4 — HIGH MTF Context Only
| Pattern | N | T+30m Exp | WR |
|---|---|---|---|
| JUDAS_BULL\|HIGH | 9 | +56.6% | 100% |
| BULL_OB\|HIGH | 18 | +44.8% | 100% |
| BULL_FVG\|HIGH | 56 | +38.4% | 95% |
| BOS_BULL\|HIGH | 571 | +28.1% | 90% |
| BEAR_OB\|HIGH | 7 | +5.3% | 67% |
| BEAR_FVG\|HIGH | 42 | -44.3% | 5% |
| BEAR_BREAKER\|HIGH | 11 | -51.9% | 0% |

### Section 5 — HIGH MTF × DTE (highest conviction)
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BOS_BEAR\|HIGH\|DTE=0 | 147 | +70.2% | 32% |
| JUDAS_BULL\|HIGH\|DTE=0 | 3 | +62.6% | 100% |
| MSS_BULL\|HIGH\|DTE=0 | 86 | +57.7% | 95% |
| BULL_FVG\|HIGH\|DTE=0 | 14 | +56.9% | 86% |
| BOS_BULL\|HIGH\|DTE=0 | 85 | +49.2% | 94% |
| BULL_OB\|HIGH\|DTE=4+ | 13 | +48.4% | 100% |
| MSS_BEAR\|HIGH\|DTE=0 | 93 | +31.7% | 38% |

### Section 6 — MTF Lift Table
| Pattern | LOW Exp | MED Exp | HIGH Exp | H-L Lift |
|---|---|---|---|---|
| JUDAS_BULL | +14.1% | +14.2% | +56.6% | +42.4% |
| BULL_OB | +19.7% | +132.8% | +44.8% | +25.0% |
| BULL_FVG | +27.6% | +35.9% | +38.4% | +10.8% |
| BEAR_OB | +61.1% | -9.3% | +5.3% | -55.7% |
| BEAR_FVG | -24.0% | -28.0% | -44.3% | -20.2% |
| BOS_BULL | +37.9% | +33.3% | +28.1% | -9.7% |
| MSS_BULL | +26.3% | +26.8% | +27.9% | +1.6% |

---

## EXPERIMENT 11 — ICT × MERDIAN Regime Intersection

### 11A — Pattern × Gamma Regime
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|NO_FLIP | 13 | +124.4% | 100% |
| BULL_OB\|LONG_GAMMA | 45 | +65.7% | 95% |
| BULL_OB\|NO_FLIP | 45 | +62.3% | 75% |
| BULL_FVG\|LONG_GAMMA | 206 | +28.4% | 75% |
| JUDAS_BULL\|LONG_GAMMA | 23 | +24.1% | 75% |
| BEAR_OB\|LONG_GAMMA | 37 | +19.7% | 77% |
| JUDAS_BULL\|NO_FLIP | 9 | -5.2% | 33% |

**Key finding:** BULL_OB works in BOTH LONG_GAMMA (+65.7%) and NO_FLIP (+62.3%) — regime-independent. JUDAS_BULL only works in LONG_GAMMA.

### 11B — Pattern × Breadth Regime
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| JUDAS_BULL\|BEARISH | 9 | +47.6% | 100% |
| BULL_FVG\|NEUTRAL | 42 | +40.9% | 50% |
| BULL_OB\|NO_BREADTH | 76 | +64.4% | 87% |

### 11C — Pattern × Momentum Regime
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|BEARISH | 17 | +141.0% | 83% |
| BULL_OB\|BEARISH | 29 | +68.3% | 86% |
| BULL_OB\|NEUTRAL | 37 | +64.7% | 85% |
| BULL_OB\|BULLISH | 24 | +49.8% | 100% |
| BEAR_FVG\|BULLISH | 50 | -21.4% | 13% |
| BEAR_FVG\|NEUTRAL | 69 | -21.6% | 15% |
| BEAR_FVG\|BEARISH | 83 | -27.2% | 16% |

**Key finding:** BEAR_OB\|BEARISH momentum = +141% — momentum alignment is the most powerful filter for BEAR_OB. BULL_OB works across all momentum regimes.

### 11D — Full Regime Combo (min N=10)
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BULL_OB\|LONG_GAMMA\|NO_BREADTH\|NEUTRAL | 19 | +65.2% | 100% |
| BULL_OB\|NO_FLIP\|NO_BREADTH\|BEARISH | 10 | +61.1% | 86% |
| BULL_FVG\|LONG_GAMMA\|NO_BREADTH\|BULLISH | 63 | +44.3% | 82% |
| BEAR_OB\|LONG_GAMMA\|NO_BREADTH\|NEUTRAL | 10 | +37.0% | 78% |

---

## EXPERIMENT 12b — Repeatability by Volatility Regime
**Revised from Exp 12 — vol regime replaces assumed phase boundaries**
**HIGH_VOL: Apr 2025, Jan-Mar 2026 | MID_VOL: May, Jun, Nov, Dec 2025 | LOW_VOL: Jul-Oct 2025**

### Coverage
| Vol Regime | Days | Days w/data | Coverage% | Scored% |
|---|---|---|---|---|
| HIGH_VOL | 83 | 22 | 26.5% | 22.0% |
| MID_VOL | 58 | 48 | 82.8% | 87.7% |
| LOW_VOL | 22 | 14 | 63.6% | 60.9% |

### Section 2 — Pattern × Vol Regime
| Label | N det | Scored | T+30m Exp | WR | Verdict |
|---|---|---|---|---|---|
| BEAR_OB\|HIGH_VOL | 56 | 17 | +147.4% | 88% | STRONG EDGE |
| BEAR_OB\|MID_VOL | 12 | 12 | +41.2% | 83% | STRONG EDGE |
| BULL_OB\|MID_VOL | 32 | 26 | +63.0% | 86% | STRONG EDGE |
| BULL_OB\|HIGH_VOL | 69 | 9 | +46.5% | 67% | EDGE |
| JUDAS_BULL\|HIGH_VOL | 18 | 5 | +22.1% | 80% | STRONG EDGE |
| JUDAS_BULL\|LOW_VOL | 7 | 7 | +39.3% | 100% | STRONG EDGE |
| JUDAS_BULL\|MID_VOL | 7 | 7 | -2.4% | 29% | noise |
| BULL_FVG\|MID_VOL | 87 | 76 | +27.8% | 70% | STRONG EDGE |
| BULL_FVG\|HIGH_VOL | 166 | 37 | +18.4% | 65% | EDGE |
| BULL_FVG\|LOW_VOL | 16 | 7 | +7.3% | 43% | EDGE |

### Repeatability Verdict
| Pattern | HIGH Exp | MID Exp | LOW Exp | Verdict |
|---|---|---|---|---|
| BULL_FVG | +18.4% | +27.8% | +7.3% | **STRUCTURAL ★★★** |
| BEAR_OB | +147.4% | +41.2% | n/a | LIKELY STRUCTURAL ★★ |
| BULL_OB | +46.5% | +63.0% | n/a | LIKELY STRUCTURAL ★★ |
| JUDAS_BULL | +22.1% | -2.4% | +39.3% | LIKELY STRUCTURAL ★★ |

---

## PORTFOLIO SIMULATION v1 — Fixed T+30m Exit, 3-min Gap
**Starting: ₹2,00,000 per symbol (₹4,00,000 total)**
**Patterns: BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL**
**Period scored: Apr 2025 – Aug 2025 (option coverage gap Sep+ for most dates)**

### NIFTY (66 trades, 76.9% WR)
| Structure | Final Capital | Return | Max DD |
|---|---|---|---|
| Fixed 1 lot | ₹2,97,955 | +49% | 0.7% |
| Pyramid 1→3→6 | ₹4,59,528 | +130% | 0.7% |

Best trade (Fixed): ₹+9,172 — BULL_FVG 2025-05-15
Worst trade: ₹-1,060 — BULL_FVG 2025-05-16

### SENSEX (117 trades, 70.1% WR)
| Structure | Final Capital | Return | Max DD |
|---|---|---|---|
| Fixed 1 lot | ₹4,70,574 | +135% | 2.1% |
| Pyramid 1→3→6 | ₹8,12,424 | +306% | 6.0% |

Best trade (Pyramid): ₹+67,545 — BULL_OB 2025-05-15
Worst trade (Pyramid): ₹-11,286 — BEAR_OB 2025-04-08

### Combined ₹4L
| Structure | Final |
|---|---|
| Fixed | ₹7,68,529 |
| Pyramid | ₹12,71,952 |

### May 15 2025 — Exceptional Day
Contributed ~50% of NIFTY total return and ~40% of SENSEX return.
Strong trending afternoon session — multiple consecutive BULL_OB + BULL_FVG signals.

---

## PORTFOLIO SIMULATION v2 — Dynamic Exit + 5-min Gap Tolerance
**Changes:** Cut losers at T+30m | Ride winners to T+60m | Half-exit if gain >50% | MAX_GAP=5

### NIFTY (64 trades)
| Structure | Final Capital | Return | Max DD | WR |
|---|---|---|---|---|
| Fixed (dynamic) | ₹3,10,199 | +55% | 1.1% | 65.6% |
| Pyramid (dynamic+half) | ₹4,70,956 | +136% | 1.1% | 65.6% |

Best trade (Pyramid): ₹+61,121 — BULL_OB 2025-05-15 (half@30m+rest@60m at 208% gain)
Worst trade: ₹-2,228 — BULL_FVG 2025-05-09

### SENSEX (114 trades)
| Structure | Final Capital | Return | Max DD | WR |
|---|---|---|---|---|
| Fixed (dynamic) | ₹4,49,166 | +125% | 4.4% | 56.1% |
| Pyramid (dynamic+half) | ₹7,96,077 | +298% | 6.1% | 57.0% |

Best trade (Pyramid): ₹+80,546 — BULL_OB 2025-05-15 (half@30m+rest@60m at 94% gain)
Worst trade (Pyramid): ₹-11,286 — BEAR_OB 2025-04-08

### v1 vs v2 Comparison
| | NIFTY Fixed | NIFTY Pyr | SENSEX Fixed | SENSEX Pyr |
|---|---|---|---|---|
| v1 return | +49% | +130% | +135% | +306% |
| v2 return | +55% | +136% | +125% | +298% |
| v1 max DD | 0.7% | 0.7% | 2.1% | 6.0% |
| v2 max DD | 1.1% | 1.1% | 4.4% | 6.1% |

**v2 improves NIFTY (+6% fixed, +6% pyramid). SENSEX slightly lower due to some winners reversing between T+30 and T+60. Win rate lower in v2 (65% vs 77%) because dynamic exit cuts recovering losers — but overall P&L higher.**

**Half-exit mechanism adds ~₹15-20k on major trending days (May 15 BULL_OB trades).**

---

## CONSOLIDATED SIGNAL RULES (research-derived)

### Trade These Patterns → Options
| Pattern | Instrument | Best When | Hold |
|---|---|---|---|
| BULL_OB | ATM CE | Any gamma regime, any DTE. MEDIUM MTF context best (+132.8%) | T+30-60m dynamic |
| BEAR_OB | ATM PE | Morning session, DTE=0 highest P&L, BEARISH momentum +141% | T+30-60m dynamic |
| BULL_FVG | ATM CE | HIGH MTF context (+38.4%). Avoid LOW_IV (<12%) | T+30-60m dynamic |
| JUDAS_BULL | ATM CE | LONG_GAMMA regime only. HIGH MTF context (+56.6%) | Minimum 30min |

### Never Trade These as Options
| Pattern | Reason |
|---|---|
| BEAR_FVG | -30.7% expectancy, negative in ALL regimes |
| BEAR_OTE | -29.7% expectancy |
| BEAR_BREAKER | -45.6% expectancy |
| BULL_BREAKER | Inverse edge |
| JUDAS_BEAR | -6.0% expectancy in options |

### Execution Structure
| Pattern | Futures Pyramid | Options |
|---|---|---|
| BULL_OB / BEAR_OB | Yes — T2@T+5m (0.20%), T3@T+10m (0.40%) | Yes — both |
| JUDAS_BULL | No — pyramid timing mismatch | Yes only |
| BULL_FVG | No — T2 only 12% | Yes only |

### Exit Rules (v2)
- Losers: exit at T+30m (cut premium decay)
- Winners: ride to T+60m
- Large winners (>50% gain at T+30m): exit half at T+30m, hold rest to T+60m

### Position Sizing (IV-scaled — from Experiment 5)
| atm_iv | Size multiplier |
|---|---|
| <12% | 0.5× (less edge in low vol) |
| 12-18% | 1.0× (normal) |
| >18% | 1.5× (elevated vol = more edge) |
| JUDAS_BULL | Fixed — no IV scaling |

### Gates — Current vs Recommended
| Gate | Current | Recommended |
|---|---|---|
| VIX>20 gate | trade_allowed=False | **REMOVE — replace with IV scaling** |
| Gamma regime | Required LONG_GAMMA | **Remove for OBs. Keep for JUDAS** |
| Breadth | BEARISH required for PE | **Keep for JUDAS. Relax for OBs** |

---

## EXPERIMENT 9 — SMDM: Expiry Day Liquidity Sweeps
**Spot-only | NIFTY 100,029 bars / SENSEX 99,778 bars**
**Sweep: price >0.10% beyond prior session H/L in first 45 min | Reversal: >0.15% counter-move**

### Sweep and Reversal Rates
| Category | Sessions | Sweep% | Reversal% | Avg Extent |
|---|---|---|---|---|
| NIFTY Expiry — Sweep UP | 46 | 28.3% | 69.2% | 0.3% |
| NIFTY Expiry — Sweep DN | 46 | 26.1% | 66.7% | 0.4% |
| NIFTY Normal — Sweep UP | 200 | 26.5% | 62.3% | 0.5% |
| NIFTY Normal — Sweep DN | 200 | 27.5% | 67.3% | 0.5% |
| SENSEX Expiry — Sweep UP | 50 | 30.0% | 86.7% | 0.8% |
| SENSEX Expiry — Sweep DN | 50 | 28.0% | 71.4% | 0.2% |
| SENSEX Normal — Sweep UP | 195 | 24.1% | 63.8% | 0.3% |
| SENSEX Normal — Sweep DN | 195 | 27.7% | 68.5% | 0.6% |

### P&L After Reversal Entry (spot % return)
| Category | N | T+30m Exp | WR T+30 |
|---|---|---|---|
| NIFTY Expiry — Sweep UP → Short | 9 | +0.05% | 78% |
| NIFTY Expiry — Sweep DN → Long | 8 | +0.13% | 62% |
| NIFTY Normal — Sweep UP → Short | 33 | +0.02% | 45% |
| NIFTY Normal — Sweep DN → Long | 37 | -0.00% | 43% |
| SENSEX Expiry — Sweep UP → Short | 13 | +0.14% | 77% |
| SENSEX Expiry — Sweep DN → Long | 10 | -0.05% | 40% |
| SENSEX Normal — Sweep UP → Short | 30 | -0.05% | 40% |
| SENSEX Normal — Sweep DN → Long | 37 | +0.03% | 47% |

### Combined Expectancy
| Symbol | Expiry | Normal |
|---|---|---|
| NIFTY | +0.09% | +0.01% |
| SENSEX | +0.06% | -0.01% |

### Verdict: NEUTRAL
No structural difference between expiry and normal day sweep reversals at spot level.
Sweep frequency (~27%) and reversal rates (~65-70%) are identical on expiry vs normal days.

**Notable exception:** SENSEX Expiry Sweep UP → Short has 77% WR vs 40% normal.
But P&L tiny in spot % terms — edge lives in DTE=0 gamma, not measured here.

**Action:** DO NOT add SMDM as separate pattern class.
Expiry day edge already captured by BOS_BEAR|HIGH|DTE=0 (+70.2% from Exp 10c).
Existing ICT suite handles expiry day reversals sufficiently.

---

## EXPERIMENT 8 — Pre-Pattern Sequence Detection
**Options P&L | NIFTY 207 patterns + SENSEX 231 patterns**
**Lookback: 3 bars | Sweep lookback: 5 bars | Impulse threshold: 0.3% cumulative**

### Section 1 — Baseline
| Pattern | N | NoD | T+30m Exp | WR |
|---|---|---|---|---|
| BEAR_OB | 68 | 39 | +103.4% | 86% |
| BULL_OB | 101 | 66 | +58.2% | 81% |
| BULL_FVG | 269 | 149 | +23.2% | 67% |

### Section 2 — Prior Sweep Filter
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|NO_SWEEP | 21 | +134.2% | 90% |
| BEAR_OB\|SWEEP | 8 | +22.7% | 75% |
| BULL_OB\|SWEEP | 12 | +67.8% | 67% |
| BULL_OB\|NO_SWEEP | 23 | +54.3% | 86% |
| BULL_FVG\|NO_SWEEP | 82 | +28.4% | 73% |
| BULL_FVG\|SWEEP | 38 | +10.2% | 50% |

**Key finding:** BEAR_OB WITHOUT prior sweep is much stronger (+134% vs +23%). A sweep before a BEAR_OB means institutions already took the liquidity — less fuel left for the next move.

### Section 3 — Momentum Alignment Filter
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|MOM_YES | 10 | +187.0% | 90% |
| BEAR_OB\|MOM_NO | 19 | +59.5% | 84% |
| BULL_OB\|MOM_YES | 25 | +64.9% | 86% |
| BULL_OB\|MOM_NO | 10 | +44.2% | 70% |
| BULL_FVG\|MOM_NO | 75 | +30.0% | 75% |
| BULL_FVG\|MOM_YES | 45 | +9.0% | 50% |

**Key finding:** MOM_YES = 2+ counter-direction bars before OB. BEAR_OB with prior bullish bars = +187% vs +59% without. Momentum alignment is the strongest single filter for BEAR_OB (lift: +83.6%).

**BULL_FVG inverted:** MOM_NO better for FVG (+30% vs +9%). FVGs form in trending environments — counter-trend bars before FVG = bad sign.

### Section 4 — Impulse Strength Filter
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|IMP_WEK | 23 | +132.4% | 96% |
| BEAR_OB\|IMP_STR | 6 | -7.4% | 50% |
| BULL_OB\|IMP_WEK | 28 | +67.3% | 83% |
| BULL_OB\|IMP_STR | 7 | +27.1% | 71% |
| BULL_FVG\|IMP_WEK | 118 | +23.9% | 67% |

**Key finding:** Strong preceding impulse (>0.3% cumulative) DESTROYS BEAR_OB edge (-7.4%). OB formed mid-trend not at exhaustion. IMP_WEK = quiet drift before OB = genuine institutional setup.

### Section 5 — Time Zone Filter
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|MORNING 10:00-11:30 | 8 | +296.6% | 100% |
| BEAR_OB\|OPEN 09:15-10:00 | 17 | +40.0% | 88% |
| BULL_OB\|AFTNOON 13:30-15:30 | 5 | +155.8% | 100% |
| BULL_OB\|MORNING 10:00-11:30 | 16 | +72.0% | 100% |
| BULL_OB\|OPEN 09:15-10:00 | 11 | +3.4% | 45% |
| BULL_FVG\|MIDDAY 11:30-13:30 | 20 | +43.4% | 85% |
| BULL_FVG\|AFTNOON 13:30-15:30 | 26 | +32.6% | 80% |
| BULL_FVG\|OPEN 09:15-10:00 | 31 | +9.6% | 48% |

**Key finding:** BULL_OB|OPEN is nearly random (+3.4%, 45% WR). Open session is noise — institutions still positioning. By 10:00 direction is established. BEAR_OB|MORNING is the kill zone — +296.6%, 100% WR.

### Section 6 — Combined Filter (best combos)
| Label | N | T+30m Exp | WR |
|---|---|---|---|
| BEAR_OB\|NO_SWEEP\|MOM_YES\|IMP_WEK | 6 | +298.0% | 100% |
| BULL_OB\|SWEEP\|MOM_YES\|IMP_WEK | 6 | +187.1% | 100% |
| BEAR_OB\|NO_SWEEP\|MOM_NO\|IMP_WEK | 10 | +100.0% | 100% |
| BULL_OB\|NO_SWEEP\|MOM_NO\|IMP_WEK | 7 | +64.0% | 100% |
| BULL_OB\|NO_SWEEP\|MOM_YES\|IMP_WEK | 13 | +50.8% | 83% |
| BULL_FVG\|NO_SWEEP\|MOM_NO\|IMP_WEK | 53 | +34.6% | 82% |

### Section 7 — Filter Lift Summary
| Pattern | Baseline | +Momentum | +Sweep | +Impulse | Best filter |
|---|---|---|---|---|---|
| BEAR_OB | +103.4% | +187.0% | +22.7% | -7.4% | Momentum (+83.6% lift) |
| BULL_OB | +58.2% | +64.9% | +67.8% | +27.1% | Sweep (+9.6% lift) |
| BULL_FVG | +23.2% | +9.0% | +10.2% | -9.5% | No filter adds value |

### Signal Quality Tiers (Experiment 8 derived)

**BEAR_OB Tiers:**
| Tier | Conditions | T+30m Exp | WR | Size |
|---|---|---|---|---|
| TIER 1 | Morning + MOM_YES + IMP_WEK | ~298% | 100% | 1.5× |
| TIER 2 | IMP_WEK + any other | +100-132% | 90-96% | 1.0× |
| TIER 3 | IMP_STR | -7.4% | 50% | SKIP |

**BULL_OB Tiers:**
| Tier | Conditions | T+30m Exp | WR | Size |
|---|---|---|---|---|
| TIER 1 | Morning OR Afternoon + IMP_WEK | +72-155% | 100% | 1.5× |
| TIER 2 | Any + NO_SWEEP + IMP_WEK | +50-64% | 83-86% | 1.0× |
| TIER 3 | OPEN session | +3.4% | 45% | SKIP or 0.5× |

**BULL_FVG:** No sequence filter adds meaningful value. Trade all with normal size. Time zone: MIDDAY and AFTERNOON best, OPEN weakest.

---

## PENDING EXPERIMENTS
- Experiment 13 — Synthesis + Signal Rule Book v1.0
- Option A — Experiment 12 rerun with correct phase boundaries (deferred)

---

## DATA NOTES
- hist_option_bars_1m: 54.8M rows, Apr 2025–Mar 2026. Coverage sparse after Aug 2025
- hist_spot_bars_1m: NIFTY 247 sessions, SENSEX 246 sessions
- hist_market_state: 91,325 NIFTY + 91,136 SENSEX rows
- hist_future_bars_1m: NIFTY contract_series=1 (continuous), SENSEX contract_series=0
- market_spot_snapshots: id, created_at, ts, symbol, spot, source_table, source_id, raw
- system_config columns: id, config_key, config_value, value_type, description, active, updated_at, updated_by, created_at
- VIX not stored historically in any table. atm_iv used as proxy.
- breadth_regime NULL before 2025-07-16 (breadth proxy not available)

