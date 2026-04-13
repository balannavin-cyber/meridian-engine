# MERDIAN Signal Rule Book v1.1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Signal_RuleBook_v1.1.md |
| Supersedes | MERDIAN_Signal_RuleBook_v1.0.docx (2026-04-10, git fcdf620) |
| Updated | 2026-04-13 |
| Sources | Experiments 2, 2b, 2c, 2c v2, 5, 8, 10c, 15, 16 — full year Apr 2025–Mar 2026 |
| Authority | Implementation-ready. All rules are empirically validated. |
| Change summary | 4 NEW rules · 3 CHANGED rules · 5 CONFIRMED rules · 1 CLOSED question |

---

## Change Log from v1.0

| # | Rule | Change type | Source |
|---|---|---|---|
| 1 | BEAR_OB AFTERNOON (13:00–14:30) → HARD SKIP | **NEW** | Exp 2, Exp 8 |
| 2 | BULL_OB AFTERNOON (13:00–15:00) → TIER1 | **NEW** | Exp 2 |
| 3 | BULL_FVG\|HIGH\|DTE=0 → TIER1 | **NEW** | Exp 10c |
| 4 | JUDAS_BULL confirmation window → T+15m | **NEW** | Exp 2c v2 |
| 5 | BEAR_OB DTE=0 and DTE=1 → combined structure | **CHANGED** | Exp 2b |
| 6 | BULL_FVG without regime context → TIER3 min | **CHANGED** | Exp 15 |
| 7 | BEAR_FVG HIGH context → remove zone filter | **CHANGED** | Exp 10c |
| 8 | T+30m exit → CONFIRMED final | **CONFIRMED** | Exp 15, 16 |
| 9 | BEAR_OB MORNING → CONFIRMED TIER1 | **CONFIRMED** | Exp 2 |
| 10 | BULL_OB DTE=0 → CONFIRMED TIER1 | **CONFIRMED** | Exp 2 |
| 11 | 1H zones (MEDIUM) → CONFIRMED in hierarchy | **CONFIRMED** | Exp 10c, 15 |
| 12 | MOM_YES → CONFIRMED strongest single filter | **CONFIRMED** | Exp 8 |
| 13 | Exit timing question | **CLOSED** | Exp 15 |

---

## Section 1 — Pattern Tier Reference

### 1.1 TIER Classification (from Experiments 8, 10c, 15)

| Tier | Win Rate Range | Kelly Fraction (Half) | Kelly Fraction (Full) |
|---|---|---|---|
| TIER1 | 87–100% | 50% of sizing capital | 100% |
| TIER2 | 61–86% | 40% of sizing capital | 80% |
| TIER3 | 49–60% | 20% of sizing capital | 40% |
| SKIP | < 30% | 0% — do not trade | 0% |

---

## Section 2 — BEAR_OB Rules

### 2.1 BEAR_OB by Time Zone

| Time Zone | Window | Rule | WR | Expectancy | Tier | Change from v1.0 |
|---|---|---|---|---|---|---|
| MORNING | 09:15–11:30 | **TRADE — highest priority** | 100% | +70.9% | **TIER1** | CONFIRMED |
| MIDDAY | 11:30–13:00 | Trade with standard filters | ~73% | +34.9% | TIER2 | No change |
| **AFTERNOON** | **13:00–14:30** | **HARD SKIP — no exceptions** | **17%** | **-24.7%** | **SKIP** | **NEW** |
| PRE-CLOSE | 14:30–15:00 | Avoid — thin, noisy | — | — | SKIP | No change |
| POWER HOUR | 15:00–15:30 | No signals (gate active) | — | — | SKIP | Confirmed |

**Rule 2.1.1 — AFTERNOON HARD SKIP:** BEAR_OB detected between 13:00–14:30 IST is a mandatory skip. No filter combination rescues it. WR 17%, expectancy -24.7% on full year. No exceptions.

### 2.2 BEAR_OB by DTE

| DTE | Rule | Rationale | Change from v1.0 |
|---|---|---|---|
| DTE=0 | **Combined structure only** (short futures + long ATM CE as insurance) | PE theta kill rate 22%+ at T+30m. PE expectancy -14.6%. | **CHANGED** |
| DTE=1 | **Combined structure only** | PE expectancy -19.1%. Theta kill rate high. | **CHANGED** |
| DTE=2+ | Pure PE buying continues | Options +25–32% expectancy on these DTE. | No change |

**Rule 2.2.1 — DTE=0/1 COMBINED STRUCTURE:** For BEAR_OB on expiry day (DTE=0) and day before (DTE=1), do not buy PE outright. Use: short futures position + long ATM CE as insurance. For DTE=2+, pure PE buying is the correct approach.

### 2.3 BEAR_OB Quality Filters (from Experiment 8)

| Filter | Effect | Action |
|---|---|---|
| MOM_YES | +21.6pp lift, 83% WR | **TIER1 upgrade if MORNING. TIER2 otherwise.** |
| IMP_WEK (weak impulse) | +103.4% base expectancy | **Prefer** — best BEAR_OB setup |
| IMP_STR (strong impulse) | -7.4% expectancy, 50% WR | **SKIP** — avoid entirely |
| NO_SWEEP | +298% in best combo | Strong supporting filter |
| MOM_NO | +100% WR in right combo | Trade at standard size |

**Rule 2.3.1 — IMP_STR SKIP:** BEAR_OB with a strong impulse (IMP_STR) is structurally unprofitable. Skip regardless of other conditions.

**Rule 2.3.2 — MOM_YES PRIORITY:** MOM_YES is the single strongest discriminating filter across all BEAR_OB subsets. Always check momentum alignment before sizing.

### 2.4 BEAR_OB IV Sizing (from Experiment 5)

| IV Regime | Size multiplier | Rationale |
|---|---|---|
| LOW_IV | 0.5× | Edge exists but muted |
| MED_IV | **1.5× (sweet spot)** | +67.2% expectancy — peak BEAR_OB edge |
| HIGH_IV | 0.5× (GATE) | PE buying = theta kill. High IV on BEAR = dangerous for PE |

**Rule 2.4.1 — HIGH_IV GATE maintained for BEAR_OB only.** BEAR_OB is the single pattern where HIGH_IV reduces edge. All other patterns perform better in HIGH_IV (VIX gate removed).

---

## Section 3 — BULL_OB Rules

### 3.1 BULL_OB by Time Zone

| Time Zone | Window | Rule | WR | Expectancy | Tier | Change from v1.0 |
|---|---|---|---|---|---|---|
| MORNING | 09:15–11:30 | **TRADE — highest priority** | 100% | +70–80% | **TIER1** | CONFIRMED |
| **AFTERNOON** | **13:00–15:00** | **TIER1 — asymmetric to BEAR_OB** | **100%** | **+75.3%** | **TIER1** | **NEW** |
| OPEN | 09:15–10:00 | Caution — noisy | 45% | +3.4% | SKIP or 0.5× | No change |
| MIDDAY | 11:30–13:00 | Trade with filters | ~80%+ | +40–65% | TIER2 | No change |
| POWER HOUR | 15:00+ | Gate active — no signals | — | — | SKIP | No change |

**Rule 3.1.1 — AFTERNOON ASYMMETRY:** Afternoon kills BEAR_OB but supercharges BULL_OB. BULL_OB 13:00–15:00 is a confirmed TIER1 setup at 100% WR. This is the most important asymmetric rule in v1.1.

### 3.2 BULL_OB by DTE

| DTE | Rule | WR | Expectancy | Tier | Change from v1.0 |
|---|---|---|---|---|---|
| DTE=0 | **TIER1 — best DTE bucket** | 100% | +107.4% | **TIER1** | CONFIRMED |
| DTE=1 | Trade | ~85% | +45%+ | TIER2 | No change |
| DTE=2+ | Trade | ~80% | +30%+ | TIER2 | No change |
| DTE=4+ | Trade (HIGH\|DTE=4+: 100% WR) | 100% | +40.2% | TIER1 | No change |

**Rule 3.2.1 — BULL_OB DTE=0 TIER1:** Gamma explosion on expiry day inside bullish structure. Full TIER1 sizing. N=13, 100% WR, +107.4% expectancy confirmed on full year.

### 3.3 BULL_OB Quality Filters

| Filter | Effect | Tier |
|---|---|---|
| MOM_YES + IMP_WEK | Best combination: 100% WR | TIER1 |
| SWEEP + MOM_YES + IMP_WEK | +187% expectancy | TIER1 |
| IMP_WEK (any other) | +50–64% | TIER2 |
| OPEN session | 45% WR | SKIP or 0.5× |

### 3.4 BULL_OB IV Sizing (from Experiment 5)

| IV Regime | Size multiplier | Rationale |
|---|---|---|
| LOW_IV | 1.0× | Uniform |
| MED_IV | 1.0× | Uniform |
| HIGH_IV | 1.0× | Minor edge not worth complexity |

---

## Section 4 — BULL_FVG Rules

### 4.1 BULL_FVG Core Rules

**Rule 4.1.1 — REGIME CONTEXT REQUIRED:** BULL_FVG without MERDIAN regime context is near-random (50.3% WR, Exp 15). It must have SHORT_GAMMA + BULLISH breadth to qualify for TIER1 or TIER2 sizing.

**Rule 4.1.2 — UNCONFLUENCED = TIER3 MINIMUM:** *(CHANGED from v1.0)* BULL_FVG detected by ICT without regime confirmation → TIER3 minimum sizing only (20% Kelly). Do not give full size to unconfluenced FVG.

### 4.2 BULL_FVG Special Setups

| Setup | Rule | WR | Expectancy | Tier | Change from v1.0 |
|---|---|---|---|---|---|
| BULL_FVG\|HIGH ctx\|DTE=0 | **TIER1** | 87.5% | +58.9% | **TIER1** | **NEW** |
| BULL_FVG\|HIGH ctx\|DTE=1 | TIER1 | 100% | +31.7% | TIER1 | No change |
| BULL_FVG\|SHORT_GAMMA\|BULLISH | TIER2 | ~65% | +23%+ | TIER2 | No change |
| BULL_FVG unconfluenced | TIER3 minimum | 50.3% | ~₹296 avg | TIER3 | **CHANGED** |

**Rule 4.2.1 — NEW TIER1 — BULL_FVG|HIGH|DTE=0:** Gamma explosion on expiry day inside weekly zone. N=12, 87.5% WR, +58.9% expectancy. Full TIER1 sizing.

### 4.3 BULL_FVG IV Sizing (from Experiment 5)

| IV Regime | Size multiplier | Rationale |
|---|---|---|
| LOW_IV | 0.5× | FVG edge muted in low vol |
| MED_IV | 1.0× | Standard |
| HIGH_IV | **1.5× (scale UP)** | HIGH_IV = +26.0% expectancy. FVG expands more in high vol. |

---

## Section 5 — JUDAS_BULL Rules

### 5.1 JUDAS_BULL Core Rules

**Rule 5.1.1 — CONFIRMATION WINDOW T+15m:** *(CHANGED from v1.0)* JUDAS_BULL confirmation must be at T+15m (not T+5m). T2 trigger rate: 12% at T+5m → 44% at T+15m. The extended window is required for Judas setups to confirm.

**Rule 5.1.2 — FIXED POSITION OVER PYRAMID:** Even with correct confirmation timing, fixed position (1 lot) at entry beats pyramid entry. T+15m is used for entry timing confirmation only, not for pyramid addition.

**Rule 5.1.3 — OPTIONS ONLY:** Futures pyramid on Judas gives 31% of fixed-entry reward for 12% risk. Options-only for JUDAS_BULL.

### 5.2 JUDAS_BULL IV Sizing

| IV Regime | Size multiplier | Rationale |
|---|---|---|
| LOW_IV | **1.5× (sweet spot)** | Low vol = trending session. Best Judas environment. |
| MED_IV | 1.0× | Standard |
| HIGH_IV | 0.5× | Choppy contra bounce in high vol. Reduce size. |

---

## Section 6 — BEAR_FVG Rules

**Rule 6.1.1 — HIGH CONTEXT DESTROYS EDGE:** *(CHANGED from v1.0)* BEAR_FVG inside HIGH context (daily/weekly zone) produces -40.2% expectancy vs -17.9% without zone. The weekly zone is used as a target by bulls, not resistance. **Remove the HIGH zone filter for BEAR_FVG.** Trade BEAR_FVG without zone filter or avoid entirely.

**Rule 6.1.2 — BEAR_BREAKER NEVER TRADE:** -46% expectancy on full year. No conditions improve it. Permanently skipped.

---

## Section 7 — MTF Context Hierarchy (ENH-37)

| Context | Zone Source | WR | Avg P&L | Rule |
|---|---|---|---|---|
| VERY_HIGH | Weekly zone | 0% (N=2, inconclusive) | -₹976 | N too small — treat as LOW |
| HIGH | Daily zone | 46.7% | +₹4,396 | Below MEDIUM — daily zones stale by session open |
| **MEDIUM** | **1H zone (same session)** | **77.3%** | **+₹13,957** | **KEEP — adds measurable edge** |
| LOW | No zone | 64.3% | +₹3,428 | Volume driver — 74% of trades. Do not skip. |

**Rule 7.1 — 1H ZONES CONFIRMED:** *(CONFIRMED from v1.0)* MEDIUM context (1H zone) outperforms HIGH (daily) for BULL_OB: +73.5% vs +40.7% expectancy. BULL_OB inside 1H zone: avg +₹18,938 vs +₹9,774 without. 1H zones must remain in ENH-37 hierarchy.

**Rule 7.2 — DO NOT SKIP LOW CONTEXT:** 64.3% WR with no zone is still strongly profitable. LOW context = 74% of all ICT trades. Skipping LOW would eliminate the majority of profitable trades.

---

## Section 8 — Exit Rules

**Rule 8.1 — T+30m FIXED EXIT: FINAL.** *(CONFIRMED — question closed)*

| Exit method | WR | Total P&L (Exp 15) | Note |
|---|---|---|---|
| **T+30m fixed** | **63.8%** | **+₹10,43,976** | **Use this** |
| ICT structure break | 36.9% | +₹7,37,341 | Holds too long, WR collapses |

T+30m beats ICT structure break by +₹3,06,635 (+41%) on every MTF context bucket. This question is permanently closed. No further exit experiments.

**Rule 8.2 — POWER HOUR GATE:** No signals after 15:00 IST. SENSEX after 15:00: 20.8% accuracy. Expiry-day gamma noise and thin spreads.

---

## Section 9 — Signal Engine Gate Rules (ENH-35)

| Gate | Rule | Evidence | Status |
|---|---|---|---|
| LONG_GAMMA | → DO_NOTHING | 47.7% accuracy at N=24,579. Below random. | Active |
| NO_FLIP | → DO_NOTHING | 45–48% accuracy. No flip = no reference point. | Active |
| CONFLICT (BULLISH+BEARISH) | → BUY_CE | 58.7% SENSEX, 55.4% NIFTY at N=3,575. Strong edge. | Active (was DO_NOTHING in v1.0) |
| VIX gate (atm_iv > threshold) | REMOVED | HIGH_IV = more edge on all patterns except BEAR_OB | Removed |
| MIN_CONFIDENCE | ≥ 40 (was 60) | Edge exists in conf 40–59 band. | Updated |
| POWER HOUR | After 15:00 → DO_NOTHING | 20.8% SENSEX after 15:00. | Active |

---

## Section 10 — Capital and Sizing Architecture

### 10.1 Capital Ceiling (ENH-38/39, A-02/A-03)

| Threshold | Rule |
|---|---|
| Below ₹10K (floor) | Engine sizes as if ₹10K |
| ₹10K – ₹25L | Full Kelly fraction applied to actual capital |
| ₹25L – ₹50L (freeze) | Lots frozen at ₹25L equivalent. Profits accumulate but lot counts don't grow. |
| Above ₹50L (hard cap) | Engine sizes as if ₹50L. Market impact above this makes larger orders impractical. |

### 10.2 Kelly Strategy

| Strategy | Fractions (T1/T2/T3) | Status |
|---|---|---|
| C — Half Kelly | 50% / 40% / 20% | **LIVE — start here** |
| D — Full Kelly | 100% / 80% / 40% | After 3–6 months live experience |

**Rule 10.2.1 — START WITH STRATEGY C.** Half Kelly provides 1,122x Ret/DD vs Full Kelly's 1,785x, but only 8.2pp additional drawdown. Half Kelly is appropriate during live onboarding when fill quality is uncertain.

### 10.3 Lot Sizing Formula

```
effective_capital = effective_sizing_capital(capital_tracker.capital)
allocated         = effective_capital × kelly_fraction(tier)
lot_cost          = lot_size × ATM_premium (live from option chain)
lots              = floor(allocated / lot_cost)   [minimum: 1]
```

Lot sizes: NIFTY = 65 units (Jan 2026), SENSEX = 20 units (Jan 2026).

---

## Section 11 — Settled Decisions (Do Not Re-Open)

| Decision | Status |
|---|---|
| T+30m exit | FINAL. No further exit experiments. |
| Futures experiments | PERMANENTLY CLOSED. Options only. |
| 1H zones in ENH-37 hierarchy | CONFIRMED. Do not remove. |
| BEAR_OB AFTERNOON hard skip | FINAL. No filter rescues it. |
| Capital ceiling ₹25L/₹50L | FINAL. Validated by Experiment 16. |
| Kelly Strategy C for live start | FINAL. Upgrade to D after experience. |
| BULL_FVG unconfluenced = TIER3 min | FINAL. 50.3% WR without regime context. |
| Session pyramid deferred | Pending ENH-42 WebSocket for real-time prices. |
| Portfolio simulation | COMPLETE. Do not re-run. |

---

## Section 12 — Quick Reference Card

```
SIGNAL FIRES → CHECK IN ORDER:

1. Time zone?
   - 15:00+ → SKIP (power hour gate)
   - 13:00–14:30 + BEAR_OB → HARD SKIP
   - 09:15–11:30 → MORNING (best window)

2. Gamma regime?
   - LONG_GAMMA → DO_NOTHING
   - NO_FLIP → DO_NOTHING
   - SHORT_GAMMA → proceed

3. Pattern?
   - BEAR_OB: check DTE, check MOM_YES, check IMP (skip IMP_STR)
   - BULL_OB: check DTE=0 (TIER1), check afternoon (TIER1)
   - BULL_FVG: need regime context or size as TIER3
   - JUDAS_BULL: confirm at T+15m
   - BEAR_FVG: skip HIGH context, else cautious TIER3

4. Tier assigned → Kelly lots computed from capital_tracker

5. Entry → T+30m exit. No exceptions.
```

---

*MERDIAN Signal Rule Book v1.1 — 2026-04-13*
*Supersedes v1.0 (2026-04-10, git fcdf620)*
*Next update: after Phase 4 live execution data (minimum 30 sessions)*
