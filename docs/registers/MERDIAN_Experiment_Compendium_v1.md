# MERDIAN Experiment Compendium v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Experiment_Compendium_v1.md |
| Created | 2026-04-12 |
| Period covered | Apr 2025 – Mar 2026 (full backtest year) |
| Dataset | 247 NIFTY sessions, 246 SENSEX sessions, 100K+ spot bars, full options chain 1-min bars |
| Purpose | Single authoritative reference: all experiments run, findings, and live system builds that arise |
| Update rule | Prepend new experiments. Never delete prior findings. |

---

## How to Read This Document

Each experiment entry has:
- **Question** — what the experiment was trying to answer
- **Setup** — key parameters
- **Findings** — the data results
- **Verdict** — what the finding means operationally
- **Builds** — what was built or changed in the live system as a result

Experiments are ordered by number. Most recent changes prepended to the top of the findings section for each entry.

---

## Proposed Experiments — Backlog

> **PROPOSED** = experiment designed but not yet run. Setup, universe, and pass criteria are specified to the level needed for execution. Once run, the entry is moved out of this section into the main numbered list with Findings and Verdict added.

### Experiment 17 (RUN 2026-04-25, FAIL) — BULL Zone Break-Below as Rejection Cascade

**Date proposed:** 2026-04-24
**Origin:** 2026-04-24 NIFTY price action (open inside W BULL_FVG 24,074-24,241, broke below, cascaded -275 pts to 23,898). Navin observation: "breaking below a green zone considered a rejection?"

**Question:** When NIFTY/SENSEX 5m close prints below the lower edge of an active W BULL_FVG or W BULL_OB by ≥ 0.1%, is the subsequent return statistically more bearish than baseline?

**Setup:**
- **Universe:** all instances 2024-01 → 2026-04 in `hist_spot_bars_5m` where active W BULL_FVG / W BULL_OB existed in `ict_htf_zones` AND a 5m bar's `close` < `zone_low * 0.999` (0.1% below)
- **Active zone filter:** zone `status = 'ACTIVE'` at the bar timestamp; not yet broken/expired
- **Direction filter:** require price came from inside or above the zone, not from already-below
- **Outcome metrics:** spot return at T+30m, T+60m, T+EOD relative to break bar close
- **Baseline:** distribution of same metrics over all 5m bars in same time-of-day buckets (no break)
- **Sample target:** ≥ 30 events across NIFTY + SENSEX

**Pass criteria (any of):**
- T+30min mean return ≤ -0.3% (vs ~0% baseline)
- T+60min mean return ≤ -0.5%
- T+EOD mean return ≤ -0.6%
- T+EOD return < 0 in ≥ 65% of cases

**Estimated effort:** Medium. Backfillable from existing data — no new instrumentation. Script likely 200-300 lines.

---


**Verdict (run 2026-04-25 09:54 IST):** FAIL on all four pass criteria. Filed as negative result. Hypothesis as written, not supported.

**Sample:** 13 events (target ≥ 30). Underpowered.

| Metric | Events (N=13) | Baseline | Delta | Pass criterion | Result |
|---|---|---|---|---|---|
| Mean ret T+30m | +0.034% | +0.003% | +0.031% | ≤ -0.300% | FAIL |
| Mean ret T+60m | +0.042% | +0.004% | +0.038% | ≤ -0.500% | FAIL |
| Mean ret T+EOD | +0.158% | -0.014% | +0.171% | ≤ -0.600% | FAIL |
| % EOD < 0      | 30.8%   | —        | —     | ≥ 65%      | FAIL |

The hypothesised direction (bearish cascade after break-below) is not present in the sample. The mean drift is mildly POSITIVE — opposite of the spec's prediction — but the sample composition makes any directional claim weak.

**Composition diagnostic (all 13 events inspected manually):**

| Issue | Events | Effect |
|---|---|---|
| 09:15 IST gap-down opens | 7 (54%) | `prev_close` is prior day's 15:25 close. Tests overnight gap behaviour, not intraday rejection. Distinct hypothesis (Exp 21 territory). |
| 14:00 IST or later breaks | 4 (31%) | T+EOD horizon collapses to 1-6 bars. Degenerate horizon. |
| `valid_from == bar_date` | 4 (31%) | Zone created same trading day it broke. Live-tradability concern (see look-ahead note below). |
| `prev_close == zone_low` exactly | 2 | BULL_OB structural artifact — zone is anchored to that candle's range, direction filter is trivially satisfied. |
| **Truly clean intraday rejection events** | **2** | NIFTY 2025-09-05 10:10 (+0.250% EOD) and SENSEX 2026-02-25 12:30 (-0.262% EOD). N=2 says nothing. |

**On the 02-06-2025 events (NIFTY +0.60% EOD, SENSEX +0.72% EOD):** These are NOT outliers to discount. Both indices gapped down on Monday 02-06-2025 against fresh W BULL_OB zones (`valid_from = 2025-06-02`), broke decisively below by ~0.7%, then closed strongly positive. Textbook "Monday open stop-hunt below fresh weekly support, then V-shape". They are the cleanest tests in the sample and they reject the hypothesis with conviction. Remove them and you remove the strongest evidence against the spec, not anomalies.

**Look-ahead audit (run 2026-04-25 against `created_at`):** All 13 zones in the sample were created retrospectively. 11 of 13 created in one batch at 2026-04-15 10:04 IST; the other 2 at 2026-04-11 19:19 IST (54-day creation lag from `valid_from`). Implication:
- Exp 17 is a **structural** backtest — the zones are geometrically deterministic from completed weekly candles, so the data validly tests the structural break-below pattern hypothesis. The look-ahead does not invalidate the FAIL.
- However, none of the 13 events was **live-detectable** in MERDIAN's operational history. Live ICT zone tracking effectively did not exist before 2026-04-15 10:04 IST. The retrospective backfill on that timestamp was the system's first comprehensive zone population.
- The 2026-04-24 NIFTY cascade event (W BULL_FVG 24,074-24,241 anchored to Apr 17 weekly candle, broke 09:30+, cascaded to 23,840 lows) is the system's first credible "live zone, live break-below" instance. It is currently missing from `hist_spot_bars_5m` (TD-019, 10-day pipeline staleness) and cannot be scored yet.

**Distributional finding worth recording (independent of FAIL/PASS):** 54% of detected break-below events are 09:15 IST gap-downs. **W BULL zones in this dataset are violated by overnight gap, not by intraday selling.** This has implications for Phase 4A:
- Live "intraday break of zone" alerts will fire much less often than a naive view assumes.
- The dominant risk to a long position protected by a W BULL zone is overnight, not intraday.
- Stop placement should account for this asymmetry — overnight stops more critical than intraday.

**Universe shrinkage from spec:**
- Spec assumed 2024-01..2026-04 (28 months); actual `hist_spot_bars_5m` coverage is 2025-04-01..2026-04-15 (12.5 months). Pipeline staleness extends the gap further (TD-019).
- Only 37 W BULL_FVG/BULL_OB zones existed in this window (15 BULL_FVG + 22 BULL_OB).

**Disposition:** Hypothesis as written, not supported by structural data. Closed as FAIL. No ENH proposed.

**Follow-ups (queued, not promoted):**

| Follow-up | Type | Trigger |
|---|---|---|
| **Exp 17b** — same script, intraday-only filter (drop gap-down opens, drop late-day breaks, drop same-day-zone events) plus add D-timeframe zones for sample boost. Target N ≥ 30 cleanly. | New experiment | After TD-019 pipeline repair. |
| **2026-04-24 forward overlay** — single-event overlay of the live cascade against this run's rules. The motivating anecdote becomes a single forward data point. | One-off scoring | After TD-019 backfill of 2026-04-16..present. |
| **Exp 19** (already in backlog) — Liquidity Sweep + Rejection. The mild positive-drift finding here is mechanically what Exp 19 is designed to test with proper framing. | Existing backlog | When prioritised. |

**Run artifacts:**
- `experiment_17_bull_zone_break_cascade.py` (script, committed Session 8)
- `experiment_17_events.csv` (13 rows; gitignored)
- `experiment_17_baseline_buckets.csv` (41,248 rows; gitignored)
- Run: 2026-04-25 09:54 IST against `hist_spot_bars_5m` 2025-04-01..2026-04-15

---

### Experiment 18 (PROPOSED) — BEAR Zone Break-Above as Confirmation

**Date proposed:** 2026-04-24
**Origin:** Mirror hypothesis to Experiment 17.

**Question:** When 5m close prints above the upper edge of an active W BEAR_OB or W BEAR_FVG by ≥ 0.1%, is the subsequent return statistically more bullish than baseline?

**Setup:** Mirror of Experiment 17 with reversed conditions.
- Filter: 5m `close` > `zone_high * 1.001` while zone `status = 'ACTIVE'`
- Outcome: T+30m, T+60m, T+EOD spot return
- Sample target: ≥ 30 events

**Pass criteria:** T+30m mean ≥ +0.3%, T+EOD mean ≥ +0.5%, T+EOD return > 0 in ≥ 65% of cases.

**Note:** Currently no active BEAR_OB / BEAR_FVG zones in MERDIAN system as of 2026-04-24 (all expired post-2025 rally). Backfill must run on historical zone state from `ict_htf_zones` history including EXPIRED entries — capturing each zone during its ACTIVE lifetime.

**Estimated effort:** Medium (same scope as Exp 17, joined script).

---

### Experiment 19 (PROPOSED) — Liquidity Sweep + Rejection (PDH/PDL Stop Run)

**Date proposed:** 2026-04-24
**Origin:** Classic ICT mechanic. Worth quantifying for Indian indices.

**Question:** When price breaks above PDH or below PDL by ≥ 0.05% but reverses within N bars (defined below), does the reversal then move materially in the opposite direction within 60 min?

**Setup:**
- Universe: all sessions 2024-01 → 2026-04 with `ict_htf_zones` D PDH and D PDL records
- **PDH-then-rejection event:** 5m bar high ≥ PDH × 1.0005 AND within next 6 bars (30 min) close drops back below PDH × 0.999
- **PDL-then-rejection event:** symmetric with PDL
- Outcome: spot move from rejection bar low (PDH case) or high (PDL case) over next 60 min
- Test sub-buckets: by time-of-day (morning/midday/afternoon), by VIX regime (HIGH/LOW)

**Pass criteria:**
- PDH-rejection: ≥ 60% of events show 60-min move ≥ -0.4% (down move from rejection)
- PDL-rejection: ≥ 60% show 60-min move ≥ +0.4% (up move from rejection)
- Sample size ≥ 40 per side

**Builds (if pass):** ENH candidate — add `LIQUIDITY_SWEEP_DETECTED` boolean to market state; allow it to override BLOCKED status when combined with BULL_OB or BEAR_OB pattern.

**Estimated effort:** Medium-large. Requires more careful 5m bar windowing logic than Exp 17/18.

---

### Experiment 20 (PROPOSED) — Open Range Break-and-Go

**Date proposed:** 2026-04-24
**Origin:** Indian market often chops in mornings. Worth knowing if first-15-min HOD/LOD breaks have edge.

**Question:** Does breaking the first 15-min HOD/LOD after 09:30 IST, without recapturing within 30 min, lead to continuation in the break direction?

**Setup:**
- Universe: all sessions 2024-01 → 2026-04
- **Open range:** spot bars 09:15-09:30 IST (first 3 × 5m bars). `OR_high` = max high. `OR_low` = min low.
- **Break event (up):** any 5m close > OR_high after 09:30; "no recapture" = no 5m close < OR_high in next 6 bars (30 min)
- **Break event (down):** symmetric below OR_low
- Outcome: spot move from break confirmation bar to EOD
- Sub-bucket: by VIX regime, by gamma regime, by breadth regime

**Pass criteria:**
- Up-break + no recapture: ≥ 65% positive EOD return, mean ≥ +0.5%
- Down-break + no recapture: ≥ 65% negative EOD return, mean ≤ -0.5%
- Asymmetry note: India morning bias may produce different up vs down statistics

**Builds (if pass):** New TIER candidate — `OR_BREAK_CONFIRMED` as additive context multiplier on existing patterns.

**Estimated effort:** Small-medium.

---

### Experiment 21 (PROPOSED) — Gap-and-Go vs Gap-Fill

**Date proposed:** 2026-04-24
**Origin:** Common observation — gap behavior varies. Quantify.

**Question:** When NIFTY/SENSEX opens with a gap > 0.3% from prior close, does the same-day fill probability differ materially from continuation probability?

**Setup:**
- Universe: all sessions 2024-01 → 2026-04 with `abs(today_open - prev_close) / prev_close > 0.003`
- **Gap up:** today_open > prev_close × 1.003
- **Gap down:** today_open < prev_close × 0.997
- **Filled:** any 5m bar in regular session traded through prev_close
- **Time-to-fill:** minutes from open to fill
- Outcome variables: fill rate, time-to-fill distribution, EOD return conditional on fill vs not-fill
- Sub-bucket: by gap size (0.3-0.5%, 0.5-1.0%, >1.0%), by VIX regime, by direction

**Pass criteria:** No fixed pass/fail — this is descriptive. Useful even as null result. Output: a 2D table (gap size × direction) showing fill rate and EOD return distributions.

**Builds (if interesting result):** Gap context block in market state — `GAP_REGIME = {NONE, FILL_LIKELY, CONTINUATION_LIKELY}` as additive signal modifier.

**Estimated effort:** Small. Mostly aggregation queries.

---

### Experiment 22 (PROPOSED) — Zone Confluence vs Single Zone

**Date proposed:** 2026-04-24
**Origin:** Hypothesis that overlapping HTF zones (e.g., D PDL + W BULL_OB at same level) create stronger reactions than isolated zones.

**Question:** When ≥ 2 active HTF zones overlap (zone ranges intersect), does price behavior at that level differ from single-zone behavior?

**Setup:**
- Universe: all `ict_htf_zones` records 2024-01 → 2026-04 where zone ranges overlap with another active zone of same direction (BULL/BULL or BEAR/BEAR)
- **Overlap definition:** `zone_low_A ≤ zone_high_B AND zone_high_A ≥ zone_low_B`
- **Single-zone control:** zones with no overlap during their active lifetime
- **Test event:** 5m bar low touches zone (within 0.1% of `zone_low`)
- Outcome: probability of holding (no break of `zone_low - 0.2%` in next 60 min) and bounce magnitude
- Compare: confluence holds vs single-zone holds

**Pass criteria:**
- Confluence hold rate ≥ 1.2× single-zone hold rate
- Bounce magnitude (from low to next 60-min high) ≥ 1.3× single-zone bounce
- Sample size ≥ 25 confluence events

**Builds (if pass):** New scoring rule — confluence multiplier in tier classification. BULL_FVG inside zone confluence → upgrade tier.

**Estimated effort:** Medium. Requires careful zone-overlap windowing.

---

### Experiment 23 (PROPOSED) — Local vs Net Gamma Divergence

**Date proposed:** 2026-04-24
**Origin:** 2026-04-24 NIFTY -275 pts move while regime classified as LONG_GAMMA. Hypothesis: local gamma profile (at spot ±0.5%) diverged from net GEX, making the LONG_GAMMA label misleading.

**Question:** When net GEX and local-spot GEX disagree directionally or in magnitude, does subsequent realized vol exceed what LONG_GAMMA regime predicts?

**Setup:**
- Universe: all `gamma_metrics` snapshots 2024-01 → 2026-04 (1m or 5m frequency)
- **Net GEX:** sum of GEX across all strikes (existing field)
- **Local GEX:** sum of GEX for strikes within `spot ± 0.5%` (NEW computation — derive from `historical_option_chain_snapshots`)
- **Divergence regime:** `sign(net_GEX) != sign(local_GEX)` OR `abs(local_GEX) < 0.2 × abs(net_GEX)`
- Outcome: realized 30-min spot range vs implied vol-based expected range
- Compare: divergence regime vs aligned regime

**Pass criteria:**
- Divergence regime shows realized 30-min range ≥ 1.5× aligned regime
- Sample size ≥ 50 divergence events
- Effect persists after controlling for VIX level

**Builds (if pass):**
- New regime label: `REGIME_UNCERTAIN` when divergence detected
- ENH-35 LONG_GAMMA hard block does not apply during `REGIME_UNCERTAIN` — pattern signals can fire
- Validity check (per ADR-001): GEX label is cross-checked against local-vs-net every cycle

**Estimated effort:** Large. Requires re-deriving local GEX from option chain snapshots — new helper function.

**Architectural note:** This experiment directly tests ADR-001's premise. The LONG_GAMMA label may have been a "stable lie" — internally consistent but not capturing the true risk profile. If this experiment passes, it justifies adding regime validity checks to the architecture, not just freshness checks.

---

### Backlog summary

| # | Title | Effort | Backfillable | Dependency |
|---|---|---|---|---|
| 17 | BULL zone break-below cascade | Medium | Yes | None |
| 18 | BEAR zone break-above confirmation | Medium | Yes | None |
| 19 | Liquidity sweep + rejection | Med-large | Yes | None |
| 20 | Open range break-and-go | Small-med | Yes | None |
| 21 | Gap-and-go vs gap-fill | Small | Yes | None |
| 22 | Zone confluence vs single | Medium | Yes | None |
| 23 | Local vs net gamma divergence | Large | Partially | Local-GEX helper function |

**Recommended order:** 17 → 21 → 20 → 19 → 22 → 18 → 23. Reasoning: 17 is the freshest hypothesis with direct trigger evidence (yesterday's NIFTY action). 21 is small/cheap and gives broad context. 20 and 19 build the intraday-pattern library. 22 deepens existing zone work. 18 mirrors 17. 23 is largest and tests architecture itself — last because it depends on confidence in the simpler patterns first.

---

## Experiment 16 — Kelly Tiered Sizing with Compounding Capital

**Date:** 2026-04-12
**Script:** `experiment_16_kelly_tiered_sizing.py`

**Question:** What is the optimal position sizing strategy across four approaches — flat pyramid, user fixed tiering, Half Kelly, and Full Kelly — when capital compounds after every trade and a ₹50L liquidity ceiling is applied?

**Setup:**
- Same trade universe as portfolio simulation (BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL)
- Tier classification: TIER1 (100% WR setups), TIER2 (80%+), TIER3 (standard)
- T2/T3 pyramid confirmation: spot +0.2% at T+5m, +0.4% at T+10m
- Capital ceiling: sizing frozen at ₹25L, hard cap ₹50L
- Starting: ₹2L per index

**Findings:**

| Strategy | Combined Final | Return | Max DD | Ret/DD |
|---|---|---|---|---|
| A — Original 1→2→3 | ₹23.7L | +494% | 12.7% | 38.9x |
| B — User 7→14→21 (T1+2) | ₹38.2L | +855% | 13.4% | 63.6x |
| C — Half Kelly tiered | ₹7.47Cr | +18,585% | 16.6% | 1,122x |
| D — Full Kelly tiered | ₹17.7Cr | +44,234% | 24.8% | 1,785x |

Tier 1 contribution (NIFTY, 31 trades, 93.5% WR): Strategy C generates ₹1.59Cr from 31 trades alone.
Best session (Feb 1, 2026): Strategy D +₹3.73Cr, Strategy C +₹1.86Cr from one session.
Worst trade: BULL_OB MIDDAY DTE=2-3 on Feb 1 — Strategy C loss -₹5.38L (same session recovered in subsequent trades).

Strategy B underperforms because fixed lots (7/14/21) don't scale with compounding capital. C and D outperform because lots recalculate from current capital each trade.

**Verdict:**
- Strategy D (Full Kelly) wins on both absolute return AND risk-adjusted return (Ret/DD 1,785x)
- Start live with Strategy C (Half Kelly) — safer DD profile, still extraordinary Ret/DD (1,122x)
- Strategy B (user fixed) is outclassed by Kelly but captures the tier logic correctly
- Strategy A (original) is the confirmed baseline — every other strategy beats it

**Builds arising:**
- ENH-38: Live Kelly sizing implementation (OI-08)
- ENH-39: Capital ceiling enforcement (OI-09)
- Capital tracker Supabase table (OI-09)

---

## Experiment 15b — Pure ICT Universe x Kelly Sizing

**Date:** 2026-04-12 (incomplete — date type fix pending)
**Script:** `experiment_15b_kelly_sizing.py`

**Question:** What do the four sizing strategies return when applied to the pure ICT trade universe (Experiment 15) rather than the MERDIAN-filtered universe (Experiment 16)?

**Status:** Script built, minor date type fix in `detect_daily_zones` needed. Run after shadow gate sessions 9-10. Non-blocking — Experiment 15 already answers the core 1H zone question.

---

## Experiment 15 — Pure ICT Compounding Simulation

**Date:** 2026-04-12
**Script:** `experiment_15_pure_ict_compounding.py`

**Question:** Can ICT patterns alone (no MERDIAN regime signals, gates, or filters) generate profitable returns with compounding capital? And does the 1H zone layer (MEDIUM context, ENH-37) add measurable edge?

**Setup:**
- ICTDetector with W/D/H zone simulation from hist_spot_bars_1m
- BEAR_OB, BULL_OB, BULL_FVG, JUDAS_BULL — no regime filter
- Starting: ₹2L per index, compounding with 1 lot per ₹1L capital
- Losses absorbed (no floor reset)
- T+30m exit vs ICT structure break exit compared

**Findings:**

| | NIFTY | SENSEX |
|---|---|---|
| Final capital | ₹6,51,308 | ₹7,92,669 |
| Return | +225.7% | +296.3% |
| Max drawdown | 1.1% | 3.6% |
| Sessions traded | 47/247 | 41/246 |
| Profitable sessions | 27/47 | 23/41 |

**Pattern performance:**

| Pattern | N | WR | Avg P&L |
|---|---|---|---|
| BEAR_OB | 36 | 94.4% | +₹13,192 |
| BULL_OB | 44 | 86.4% | +₹11,891 |
| BULL_FVG | 155 | 50.3% | +₹296 |

**MTF context (the 1H zone question):**

| Context | N | WR | Total P&L |
|---|---|---|---|
| VERY_HIGH (weekly) | 2 | 0.0% | -₹976 |
| HIGH (daily) | 15 | 46.7% | +₹65,944 |
| MEDIUM (1H zone) | 22 | 77.3% | +₹3,07,060 |
| LOW (no zone) | 196 | 64.3% | +₹6,71,948 |

MEDIUM outperforms HIGH. 1H zone is same-session institutional order flow — more current than prior-session daily zones.

BULL_OB inside 1H zone: 83.3% WR, avg +₹18,938 vs +₹9,774 without zone. 1H zone nearly doubles average trade P&L on BULL_OB.

**Exit comparison:**

| Exit | WR | Total P&L |
|---|---|---|
| T+30m | 63.8% | +₹10,43,976 |
| ICT structure break | 36.9% | +₹7,37,341 |

T+30m wins by ₹3,06,635 (+41%). ICT exit WR collapses to 36.9% because price often consolidates or partially reverses between T+30m and structure break.

**Tier performance:**

| Tier | N | WR | Total |
|---|---|---|---|
| TIER1 | 33 | 90.9% | +₹5,19,348 |
| TIER2 | 202 | 59.4% | +₹5,24,628 |

**Verdict:**
- 1H zones ADD EDGE — MEDIUM context is the most profitable context tier by WR. Keep in ENH-37.
- BEAR_OB is self-contained — 94.4% WR with no MERDIAN gates. Strongest standalone ICT pattern.
- BULL_FVG needs MERDIAN context — 50.3% WR alone is near-random. Must have SHORT_GAMMA + BULLISH breadth.
- T+30m exit confirmed once more. Final answer on exit question.
- 1.1% max drawdown demonstrates the framework's robustness — trading 1 in 5 sessions, losses are shallow and recoveries fast.

**Builds arising:**
- MEDIUM context confirmed in ENH-37 hierarchy (no change required — already live)
- BULL_FVG TIER3 minimum sizing rule (OI-10, Signal Rule Book v1.1)
- T+30m exit rule confirmed (OI-10, document as tested)

---

## Experiment 10c — ICT Patterns: MTF Context x Options P&L

**Date:** 2026-04-12
**Script:** `experiment_10c_mtf_pnl.py`

**Question:** Does MTF context (HIGH/MEDIUM/LOW) systematically improve option P&L? Which context tier adds most edge? Does 1H zone (MEDIUM) add anything beyond daily zone (HIGH)?

**Setup:** All ICT patterns, full year, prior-session W/D H zone simulation, options P&L at T+15m/T+30m/T+60m.

**Key findings:**

BULL_OB by context:
- MEDIUM (1H zone): +73.5% T+30m expectancy, 90% WR (N=45)
- HIGH (daily zone): +40.7%, 100% WR (N=18)
- LOW (no zone): +30.5%, 88% WR (N=38)

MEDIUM outperforms HIGH. Confirmed again — 1H zone is more current than daily zone.

**MTF lift table (HIGH vs LOW):**

| Pattern | Lift | Verdict |
|---|---|---|
| JUDAS_BULL | +24.3pp | Major edge from HIGH context |
| BULL_FVG | +11.7pp | Adds edge |
| BULL_OB | +10.2pp | Adds edge |
| BOS_BULL | -5.0pp | No MTF benefit |
| BEAR_FVG | -22.3pp | HIGH context DESTROYS edge |
| BEAR_BREAKER | -22.0pp | HIGH context DESTROYS edge |

BEAR_FVG inside weekly zone: -40.2% expectancy vs -17.9% without zone. Zone is used as a target by bulls, not resistance by bears.

**Highest conviction setups (HIGH + DTE=0/1):**

| Setup | N | WR | Exp |
|---|---|---|---|
| BULL_OB\|HIGH\|DTE=4+ | 15 | 100% | +40.2% |
| JUDAS_BULL\|HIGH\|DTE=4+ | 5 | 100% | +37.8% |
| BULL_FVG\|HIGH\|DTE=0 | 12 | 87.5% | +58.9% |
| BULL_FVG\|HIGH\|DTE=1 | 8 | 100% | +31.7% |

BULL_FVG inside weekly zone on expiry day — new Tier 1 rule.

**Verdict:**
- Keep MEDIUM in ENH-37 hierarchy — confirmed again
- BEAR_FVG and BEAR_BREAKER — remove HIGH zone filter
- BULL_FVG|HIGH|DTE=0 → new TIER1 signal rule
- JUDAS_BULL inside weekly zone gets largest MTF lift — prioritise

**Builds arising:**
- BULL_FVG|HIGH|DTE=0 added to TIER1 in Signal Rule Book (OI-10)
- BEAR_FVG HIGH context removal (OI-10)

---

## Experiment 8 — Pre-Pattern Sequence Detection

**Date:** 2026-04-12
**Script:** `experiment_8_sequence.py`

**Question:** Do the 3 bars before an OB pattern predict its quality? Specifically: prior sweep, momentum alignment (MOM_YES), and impulse strength (IMP_STR).

**Key findings:**

| Filter | BEAR_OB lift | BULL_OB lift | Verdict |
|---|---|---|---|
| MOM_YES | +21.6pp | +3.2pp | Dominant filter |
| Sweep | -0.5pp | +1.1pp | No benefit |
| IMP_STR | -7.2pp | +2.0pp | Weaker impulse is better |

BEAR_OB|MOM_YES: N=23, 83% WR, +56.1% T+30m — single strongest filter.
BEAR_OB|MORNING: N=9, 100% WR, +81.2% — best time zone filter.
BEAR_OB|AFTERNOON: -2.5% expectancy, 55% WR — confirmed negative.

Best combined: BULL_OB|SWEEP|MOM_YES|IMP_WEK: N=20, 100% WR, +54.4%.

**Verdict:** MOM_YES is the tier classification criterion for TIER1/TIER2. IMP_STR (strong impulse before OB) is slightly negative — calm approach to zone = more reliable reversal.

**Builds arising:**
- MOM_YES included in TIER1/TIER2 classification (already implemented in ENH-37)
- IMP_WEK preferred over IMP_STR (already in tier logic)

---

## Experiment 5 — IV/VIX Stress Test

**Date:** 2026-04-12
**Script:** `experiment_5_vix_stress.py`

**Question:** Does the VIX gate (blocking trades when IV is high) help or hurt? What is the correct IV-based sizing rule per pattern?

**Key findings:**

| Pattern | LOW_IV | MED_IV | HIGH_IV | Gate verdict |
|---|---|---|---|---|
| BULL_FVG | +0.2% | +10.5% | +26.0% | REMOVE gate |
| BULL_OB | +40.0% | +39.9% | +42.9% | REMOVE gate |
| JUDAS_BULL | +28.9% | +9.3% | +16.1% | Keep for LOW |
| BEAR_OB | +14.7% | +67.2% | +16.5% | KEEP gate for HIGH_IV |

**IV sizing rules:**
- BULL_FVG: LOW=0.5x, MED=1.0x, HIGH=1.5x (scale up in high IV)
- BULL_OB: uniform (minor HIGH_IV edge, not worth complexity)
- JUDAS_BULL: LOW=1.5x, MED=1.0x, HIGH=0.5x (reverse — low IV is sweet spot)
- BEAR_OB: LOW=0.5x, MED=1.5x, HIGH=0.5x (gate back HIGH_IV — MED is the sweet spot at +67.2%)

**Verdict:** Remove VIX gate for BULL_FVG and BULL_OB. Reinstate specifically for BEAR_OB in HIGH_IV (PE buying in high vol = theta kill). Replace binary gate with IV-scaled sizing per pattern.

**Builds arising:**
- IV sizing rules in Signal Rule Book v1.1 (OI-10)
- ENH-35 confirmed removing VIX gate from signal engine

---

## Experiment 2c v2 — Judas Bull Pyramid (Extended Confirmation Window)

**Date:** 2026-04-12
**Script:** `experiment_2c_v2_judas.py`

**Question:** Does extending the Judas confirmation window from T+5m to T+15m improve pyramid performance?

**Finding:** Judas T2 trigger rate jumped from 12% (T+5m) to 44% (T+15m). Judas patterns take 15-25 minutes to confirm — the market does move in the predicted direction, just slower than OBs.

However Fixed-6 still outperforms even the improved pyramid. Reason: even at T+15m confirmation, the additional units are at worse premium prices.

**Verdict:** Use T+15m confirmation window for Judas entry timing, but do not pyramid — stay fixed position.

**Builds arising:**
- JUDAS_BULL confirmation window → T+15m in Signal Rule Book (OI-10)

---

## Experiment 2c — Pyramid Entry vs Fixed Position

**Date:** 2026-04-12
**Script:** `experiment_2c_pyramid_entry.py`

**Question:** Does the 1→2→3 pyramid entry structure (adding on confirmation) outperform a fixed 6-lot position?

**Key findings:**

| Pattern | T2 Rate | T3 Rate | Winner |
|---|---|---|---|
| BEAR_OB | 93% | 62% | Fixed-6 |
| BULL_OB | 80% | 53% | Fixed-6 |
| JUDAS_BULL | 12% | 4% | Fixed-6 |

Fixed-6 wins on every pattern. High T2/T3 rates on OBs mean the market confirms quickly — but adding units at T+5m and T+10m means buying expensive premium after the move has already started.

**Verdict:** Session pyramid deferred (ENH-42). Single T+30m exit on first OB entry remains optimal for options. Pyramid applies when sizing with Kelly (adding units from capital, not from confirmation).

---

## Experiment 2b — Futures vs Options vs Combined

**Date:** 2026-04-12
**Script:** `experiment_2b_futures_vs_options.py`

**Question:** Do futures outperform options for any pattern/DTE combination? Is the combined structure (futures + insurance option) ever better than pure options?

**Key findings:** Options win on every pattern and every DTE. No exception except BEAR_OB DTE=0 and DTE=1.

| Setup | Options Exp | Futures Exp | Winner |
|---|---|---|---|
| BULL_OB (all DTE) | +47.9% | +0.5% | Options |
| BEAR_OB DTE=0 | -14.6% | +0.0% | Combined |
| BEAR_OB DTE=1 | -19.1% | +0.1% | Combined |
| BEAR_OB DTE=2-3 | +25.2% | +0.5% | Options |
| BEAR_OB DTE=4+ | +31.7% | +0.1% | Options |

BEAR_OB DTE=0 and DTE=1: PE premium collapses from theta even when spot moves correctly — 22% theta kill rate. The combined structure (futures short + CE insurance) works here.

Insurance option (CE bought at BULL_OB entry) recovers 79% of stops — nearly always helps. Skip insurance for FVG and BOS patterns — market moves too directionally.

**Verdict:** Options only for all patterns except BEAR_OB DTE=0/1. Futures experiments permanently closed.

**Builds arising:**
- Futures experiments closed permanently (decision logged)
- ENH-41: BEAR_OB DTE gate — combined structure for DTE=0 and DTE=1 (OI-10)

---

## Experiment 2 — Options P&L by Pattern (Full Year)

**Date:** 2026-04-12
**Script:** `experiment_2_options_pnl.py`

**Question:** What are the actual options P&L statistics for each ICT pattern across the full year, and how do they vary by DTE and time of day?

**Pattern performance:**

| Pattern | N | WR | T+30m Exp |
|---|---|---|---|
| BULL_OB | 81 | 88.9% | +41.9% |
| BEAR_OB | 63 | 73.0% | +34.9% |
| JUDAS_BULL | 29 | 69.0% | +15.2% |
| JUDAS_BEAR | 18 | 83.3% | +11.6% |

**DTE highlights:**
- BULL_OB|DTE=0: 100% WR, +107.4% (N=13) — gamma explosion on expiry day
- BEAR_OB|DTE=2-3: 70% WR, +44.2% — best sustained BEAR_OB expectancy
- BEAR_OB|DTE=0: 66.7% WR, +7.3% — drops sharply vs DTE=2+

**Time of day highlights:**
- BEAR_OB|MORNING: 100% WR, +70.9% — zero losses
- BEAR_OB|AFTERNOON (13:00-14:30): 17% WR, -24.7% — hard skip
- BULL_OB|AFTERNOON (13:00-15:00): 100% WR, +75.3% — asymmetric: afternoon kills bear, supercharges bull
- BEAR_OB|MIDDAY: 65% WR, +64.6% — strong

**Theta kill rate (spot correct but option lost):**
- BEAR_OB T+30m: 22% — highest, confirms theta risk on PE buying
- BULL_OB T+30m: 5.7% — much cleaner

**Verdict:** All four patterns are tradeable at T+30m. BULL_OB|DTE=0 and BEAR_OB|MORNING are the two standout high-conviction rules.

**Builds arising:**
- BEAR_OB AFTERNOON hard skip (OI-10)
- BULL_OB AFTERNOON TIER1 (OI-10)
- BULL_OB DTE=0 TIER1 confirmed (already in ENH-37)
- T+30m exit confirmed (OI-10 — document)

---

## Experiment 16 Tier Classification Reference

From all experiments combined, the validated tier structure:

### TIER1 (100% WR setups — deploy Full Kelly 100% of sizing capital)
- BULL_OB | MORNING (10:00-11:30)
- BULL_OB | DTE=0
- BULL_OB | AFTERNOON (13:00-15:00)
- BULL_OB | SWEEP + MOM_YES + IMP_WEK
- BEAR_OB | MORNING (10:00-11:30)
- BULL_FVG | HIGH context | DTE=0 (NEW — Exp 10c)

### TIER2 (80-91% WR setups — deploy Full Kelly 80% of sizing capital)
- BULL_OB | MOM_YES
- BULL_OB | IMP_STR
- BULL_OB | DTE=4+
- BEAR_OB | MOM_YES
- BEAR_OB | DTE=4+
- JUDAS_BULL | DTE=2-3

### TIER3 (standard setups — deploy Full Kelly 40% of sizing capital)
- All other BULL_OB
- All other BEAR_OB (except AFTERNOON — skip)
- JUDAS_BULL (unqualified)
- BULL_FVG with SHORT_GAMMA + BULLISH breadth context

### SKIP (do not trade)
- BEAR_OB | AFTERNOON (13:00-14:30) — -24.7% expectancy
- BEAR_OB | DTE=0 or DTE=1 — use combined structure instead
- BULL_FVG without MERDIAN regime context — 50.3% WR (near-random)
- BEAR_FVG | HIGH context — -40.2% expectancy
- LONG_GAMMA signals — validated below random

---

## Capital and Sizing Reference

From Experiment 16:

| Rule | Value | Rationale |
|---|---|---|
| Starting capital | INR 2,00,000 per index | Minimum viable lot deployment |
| Capital floor | INR 2,00,000 | Never size below this — prevents recovery collapse |
| Sizing freeze | INR 25,00,000 | Lots stop growing — liquidity degrades above this |
| Hard cap | INR 50,00,000 | No lot calculation uses more than this |
| Strategy (start) | Half Kelly | C — 1,122x Ret/DD, 16.6% max DD |
| Strategy (mature) | Full Kelly | D — 1,785x Ret/DD, 24.8% max DD |
| Pyramid confirmation | T+5m +0.2%, T+10m +0.4% | OBs; Judas T+15m |
| Exit | T+30m | Confirmed over ICT structure break |
| Compounding | Per trade | Capital updates after every closed trade |

---

*MERDIAN Experiment Compendium v1 — 2026-04-12*
*Living document. Prepend new experiments. Never delete prior findings.*
*Commit alongside Enhancement Register v5 and Open Items Register v6.*
