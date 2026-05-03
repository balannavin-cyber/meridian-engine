# MERDIAN Experiment Compendium v1

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Experiment_Compendium_v1.md |
| Created | 2026-04-12 |
| Last updated | 2026-04-28 (Session 11 — Exp 34 through 41B added) |
| Period covered | Apr 2025 – Apr 2026 (full backtest year) |
| Dataset | 262 NIFTY sessions, 261 SENSEX sessions, 18,895 / 18,870 regular-session 5m bars |
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

Experiments are ordered by number. Most recent experiments at top.

Update note 2026-05-02 (Session 15): registered metadata also at top — period covered now extends Apr 2025 → Apr 2026 (full backfill on patched zone builders, 264 NIFTY + 263 SENSEX trading days, 40,384 zone rows in `hist_ict_htf_zones`, 7,484 signal rows in `hist_pattern_signals` after the BEAR_FVG fix shipped this session). All Session 15 experiments below were run on this dataset. Note: Exp 50 / Exp 50b results recorded here are BULL-only (the bug-discovery vehicle for the BEAR_FVG defect closed this session) — expected to be re-run on now-symmetric data in Session 16.

Update note 2026-05-03 (Session 16): six Session 16 entries added at top below this note. Headline finding: **Exp 15 framework (1m live-detector path) replicates within 2-3pp of original Compendium claims on current code with current data — combined NIFTY+SENSEX ₹4L → ₹11.7L (+193.4%) full year, BEAR_OB 92.0% (vs 94.4%), BULL_OB 83.7% (vs 86.4%), BULL_FVG 50.3% (vs 50.3%).** Per-cell deep audit (Wilson 95% CIs on N=231 trades) revealed BULL_FVG is statistical coin flip standalone but +12.8pp lift with recent BULL_OB cluster (90-min lookback, N=64); MTF context hierarchy is INVERTED from claim (LOW outperforms HIGH on OB patterns); edge concentrates in top 7/57 sessions = 80% P&L (event-dependent). Session 15 Exp 50 / Exp 50b BULL-only verdicts re-tested on bidirectional `hist_pattern_signals` (Items 3-4 of carry-forward) — included as separate v2 entries below. Live-cohort verification of clustering done in Section 18 of `analyze_exp15_trades.py` and reported in the Exp 15 framework replication entry. **Provenance note for Apr-12 Compendium entry on Exp 15:** the original execution log of `experiment_15_pure_ict_compounding.py` is a 427-byte SyntaxError crash; no successful execution log of that exact script exists anywhere in `C:\GammaEnginePython\logs\`. Apr-13 commit `c78b6ea` modified both the experiment script and `detect_ict_patterns.py.get_mtf_context`, silently relabeling MTF tier vocabulary (pre-Apr-13: HIGH=W, MEDIUM=D; post-Apr-13: VERY_HIGH=W, HIGH=D, MEDIUM=H). Apr-12 entry uses post-Apr-13 vocabulary. Session 16 replication is therefore the audit-grade execution; published headlines are not refuted but the original measurement is not directly auditable. TD-057 captures the broader provenance gap.

---

## Session 16 — Exp 15 framework replication on current code (the headline finding)

**Date:** 2026-05-03
**Script:** `experiment_15_pure_ict_compounding.py` (verbatim, git rev `c78b6ea`); CSV dump version `experiment_15_with_csv_dump.py`; analyzer `analyze_exp15_trades.py` (Sections 9-18).
**Trade list:** `exp15_trades_20260503_0952.csv` (231 trades, 12 months 2025-04-08 to 2026-03-30)

**Question:** Do the published Exp 15 headlines (BEAR_OB 94.4% WR, BULL_OB 86.4% WR, BULL_FVG 50.3% WR) replicate on current code with current data, after the Apr-13 `c78b6ea` commit modified both `experiment_15_pure_ict_compounding.py` and `detect_ict_patterns.py` and silently relabeled MTF context tiers? And, on the live 1m-detector cohort, what does deep audit (confidence intervals, concentration, regime stability, time-of-day, clustering) show?

**Setup:**
- Same script, same dataset, same methodology as the original Exp 15
- 12-month range Apr 2025 → Apr 2026, 264 NIFTY + 263 SENSEX trading days
- Live `ICTDetector` running on `hist_spot_bars_1m`, T+30m option-side P&L from `hist_option_bars_1m`
- ₹2L starting capital per symbol, compounding (profits added, losses absorbed)
- Filters: `tier != SKIP`, `time < POWER_HOUR`, 5-prior-day warmup gate
- Pre-filter pass rate ~1.3% of detected signals

**Findings — pooled per-pattern WR:**

| Pattern | N | WR | 95% CI (Wilson) | mean P&L | total P&L | Compendium claim | Delta |
|---|---|---|---|---|---|---|---|
| BEAR_OB | 25 | 92.0% | [75.0, 97.8] | ₹+14,571 | ₹+364,273 | 94.4% (N=36) | -2.4pp |
| BULL_OB | 49 | 83.7% | [71.0, 91.5] | ₹+7,735 | ₹+379,016 | 86.4% (N=44) | -2.7pp |
| BULL_FVG | 155 | 50.3% | [42.5, 58.1] | ₹+195 | ₹+30,153 | 50.3% (N=155) | 0.0pp |

**Headlines replicate within 2-3pp of original claims.** BULL_FVG is exact match (N=155 to N=155). BULL_FVG's CI [42.5, 58.1] **spans 50% — statistical coin flip**; contributes 67% of trades (155/231) but only 3.9% of P&L (₹+30K of ₹+773K total).

**Combined return:** ₹4,00,000 → ₹11,73,442 (+193.4%) over 12 months. NIFTY: ₹2L → ₹5,60,705 (+180.4%, max DD 1.3%, 127 trades). SENSEX: ₹2L → ₹6,12,737 (+206.4%, max DD 3.1%, 104 trades).

**Findings — MTF context (current vocabulary, current data):**

| Pattern | Context | N | WR | 95% CI | mean P&L |
|---|---|---|---|---|---|
| BULL_OB | HIGH (D zone) | 7 | 71.4% | [35.9, 91.8] | ₹+13,140 |
| BULL_OB | MEDIUM (H zone) | 11 | 81.8% | [52.3, 94.9] | ₹+9,616 |
| BULL_OB | LOW (no zone) | 31 | 87.1% | [71.1, 94.9] | ₹+5,847 |
| BEAR_OB | HIGH | 7 | 71.4% | [35.9, 91.8] | ₹+11,417 |
| BEAR_OB | MEDIUM | 1 | 100.0% | [—] | ₹+54,876 |
| BEAR_OB | LOW | 17 | 100.0% | [81.6, 100.0] | ₹+13,499 |

**LOW context outperforms HIGH context on both BULL_OB and BEAR_OB.** ENH-37 hierarchy is inverted from claim. (Note: current vocabulary = post-Apr-13. The Apr-12 Compendium entry's "MEDIUM context adds edge" was about *daily* zones; today's MEDIUM is *1H* — TD-057 captures this vocabulary boundary.)

**Findings — concentration (Section 11):**
- Top 1 session = 29.2% of P&L (Feb 1, 2026 — vol-breakout day)
- Top 4 sessions = 50% of P&L
- **Top 7 sessions (12.3% of trading sessions with trades) = 80% of P&L**
- 33/57 sessions with trades profitable; 24/57 negative

**Findings — H1/H2 stability (Section 12):**
- BULL_OB: 84.6% H1 → 82.6% H2 — STABLE across halves
- BEAR_OB: 71.4% H1 → 100.0% H2 — drift (H2 had more bear-favorable regime)
- BULL_FVG: 53.3% H1 → 46.2% H2 — UNSTABLE, pure coin flip

**Findings — per-symbol (Section 13):**
- NIFTY pooled WR 65.1% [56.4, 72.8], total ₹+360,705
- SENSEX pooled WR 58.3% [48.6, 67.3], total ₹+412,737
- SENSEX BULL_FVG: -₹29,056 (negative)
- NIFTY BULL_FVG: +₹59,209
- Reinforces "BULL_FVG is luck, both sides"
- SENSEX BEAR_OB N=13 WR 92.3% drives ₹+271,921 — largest single contributor

**Findings — time-of-day (Section 14):**
- AFTERNOON: 49% WR (coin flip)
- MORNING + MIDDAY pooled: 65.6% WR [58.4, 72.1]
- ENH-64 BEAR_OB AFTERNOON skip is empirically warranted

**Findings — monthly (Section 15):**
- 9 of 12 months positive
- Worst month December 2025 at -₹9,544 (only 3 trades)
- Months with N≥10 are mostly winners
- February 2026 alone produced ₹+271,939 (driven by Feb 1 vol breakout)

**Findings — TD-056 bull-skew on live cohort (Section 17):**
- NIFTY DOWN regime: 23 BULL_OB / 7 BEAR_OB = **3.29x bull-skew** (5m-batch had 5.60x)
- SENSEX DOWN regime: 15 BULL_OB / 10 BEAR_OB = 1.50x
- BULL_FVG / BEAR_FVG ratio is **infinite in all regimes** — live `detect_ict_patterns.py` emits **zero BEAR_FVG signals across full year** despite Session 15's `build_ict_htf_zones.py` BEAR_FVG fix (TD-058 filed)
- Bull-skew confirmed structural across BOTH 5m-batch AND 1m-live code paths

**Findings — FVG-on-OB clustering on live cohort (Section 18):**

| Lookback | N clustered | WR clustered | N standalone | WR standalone | Lift |
|---|---|---|---|---|---|
| 30 min | 49 | 51.0% | 106 | 50.0% | +1.0pp |
| 60 min | 57 | 54.4% | 98 | 48.0% | +6.4pp |
| 90 min | 64 | **57.8%** | 91 | 45.1% | **+12.8pp** |

**Cluster effect replicates and is stronger on live cohort than 5m-batch.** Standalone BULL_FVG is coin flip; BULL_FVG-with-recent-BULL_OB at 90-min lookback transforms into real edge. BEAR-side untestable (zero BEAR_FVG emissions per TD-058).

**Verdict:** **EDGE PRESENT BUT NARROWER THAN HEADLINE.**
- Pooled WR clears CI [55.6, 68.0] — real edge above coin flip
- ≥1 cell clears CI > 50% with confidence (BULL_OB|LOW, BEAR_OB|LOW with very tight intervals)
- Both halves of year positive (₹+287,967 H1, ₹+485,475 H2)
- **Failed broadly-distributed-P&L check** (top 7/57 = 80%)

Edge is real but concentrated. The +193% number alone overstates steady-yield expectation — the strategy is event-dependent vol-breakout exploitation, not daily accumulation.

**Builds arising:**
- ENH-87 (filed): `hist_pattern_signals` deprecation review — live-detector replay pattern (this script's CSV dump methodology) provides equivalent research utility without the integrity issues of the 5m batch table
- ENH-88 (filed): BULL_FVG production routing requires recent BULL_OB context (60-90 min lookback, +12.8pp lift evidence) — replace 50% coin flip with 58% lifted cohort
- ENH-89 (filed): ENH-37 MTF hierarchy redesign or removal — current implementation subtracts edge per Section 10 evidence
- TD-057 (filed): Exp 15 framework provenance gap (no findable execution audit trail)
- TD-058 (filed): live `detect_ict_patterns.py` emits zero BEAR_FVG signals across full year despite Session 15 zone-builder fix
- TD-059 (filed): MTF context hierarchy inverted from claim (LOW outperforms HIGH on OB patterns)
- TD-056 EXPANDED (S3→S2): bull-skew confirmed structural across BOTH 5m-batch AND 1m-live code paths

---

## Session 16 — Exp 50 v2 (FVG-on-OB cluster, bidirectional, ret_30m-noise corrected)

**Date:** 2026-05-02 (Session 16)
**Script:** `experiment_50_fvg_on_ob_cluster_v2.py`

**Question:** Does Exp 50's "FVG inside or near a same-direction OB cluster has different WR than standalone FVG" hypothesis hold on bidirectional `hist_pattern_signals` data, after the Session 15 BEAR_FVG fix and using locally-computed forward return (since `ret_30m` column is broken — TD-054)?

**Setup:**
- Bidirectional 3×3 sweep: lookback ∈ {30, 60, 120} min × proximity ∈ {0.10%, 0.50%, 1.00%} × side ∈ {BULL, BEAR} = 18 cells
- Drop EV-ratio gate per session prompt — keep WR-delta + N-floor=20
- Outcome: locally-computed T+30m return (`ret_30m` column unreliable — `hist_pattern_signals` cohort 5% agreement, 30% NULL)
- Cohort: full year `hist_pattern_signals`, N=2274 enriched after Session 15 fix

**Findings:**
- BULL: 2/9 cells PASS at lookback=60min × proximity ∈ {0.50%, 1.00%}
- BEAR: 0/9 cells PASS
- Headline cell (60min × 0.50%): BULL +8.3pp WR delta cluster vs standalone PASS; BEAR -4.2pp FAIL
- The Session 15 reported "monotonic inversion" was an artefact of `ret_30m` column noise — 35pp swing on the same cohort with corrected (locally-computed) metric

**Verdict on `hist_pattern_signals` cohort: BULL has cluster effect, BEAR doesn't.** But this is the wrong cohort — `hist_pattern_signals` is the 5m-batch detector path, not the 1m live detector that Exp 15 uses. **Live-cohort verification: see Session 16 Exp 15 entry above, Section 18: BULL_FVG-on-BULL_OB clustering on the live 231-trade cohort shows +12.8pp lift at 90-min lookback (N=64), replicating and strengthening this finding.** BEAR-side untestable on live cohort because live detector emits zero BEAR_FVG signals (TD-058).

**Builds arising:** Live-cohort replication via Section 18 of `analyze_exp15_trades.py` is the canonical version. ENH-88 (BULL_FVG production routing requires recent BULL_OB) is built on the live-cohort evidence.

---

## Session 16 — Exp 50b v2 (FVG-on-OB velocity moderation)

**Date:** 2026-05-02 (Session 16)
**Script:** `experiment_50b_fvg_on_ob_velocity_v2.py`

**Question:** Does pre-cluster velocity (price velocity in the lookback window before the FVG) moderate cluster WR symmetrically across BULL and BEAR sides on `hist_pattern_signals`?

**Setup:**
- Reframed from Session 15 "explain the inversion" (now obsolete since inversion was a `ret_30m` artefact) to "does velocity moderate cluster WR symmetrically across directions"
- Velocity quartiles Q1-Q4 (slowest to fastest pre-cluster price velocity) on bidirectional cluster cohort
- Same locally-computed T+30m outcome metric

**Findings:**
- Headline cell BULL: Q1→Q4 swing -18.2pp (INCREASING — fast clusters outperform slow)
- Headline cell BEAR: Q1→Q4 swing +26.7pp (DECREASING — slow clusters outperform fast)
- Sweep voting: BULL 7/7 cells INCREASING; BEAR 4 INC / 3 DEC at smaller cell counts
- N-weighted BEAR also INCREASING

**Verdict:** Mixed/inconclusive on the per-cell voting metric. Honest reading: symmetric INCREASING signal exists, BULL-stronger. **Carry-forward to Session 17:** Section 18 of `analyze_exp15_trades.py` tested clustering on live cohort but did NOT test velocity quartiles. To close this item properly, extend the analyzer with a Section 19 that computes pre-cluster velocity from entry_spot trajectory and partitions by quartile.

**Builds arising:** None directly. Decision (whether to prefer fast or slow clusters in production sizing) deferred until live-cohort velocity verification.

---

## Session 16 — ADR-003 Phase 1 v3 (zone respect-rate, era-aware, most-recent-ACTIVE)

**Date:** 2026-05-02 (Session 16)
**Script:** `adr003_phase1_zone_respect_rate_v3.py`

**Question:** Do ICT HTF zones in `hist_ict_htf_zones` actually predict price pivots in `hist_spot_bars_5m`? Re-run with six methodology fixes vs the v1/v2 INVALID runs.

**Setup (six fixes vs v2):**
1. Query `hist_ict_htf_zones` not `ict_htf_zones` (Session 15's fix table)
2. Drop `valid_to` filter — take most-recent ACTIVE zone per (TF, pattern) at each bar
3. Era-aware Rule 20 (`ERA_BOUNDARY = 2026-04-07`)
4. Use `trade_date` column directly for date filters
5. `EXPECTED_BARS = 81` (empirical, not 75)
6. Distance histogram diagnostic added

**Findings:**
- NIFTY ACTIVE zones: 20,206. SENSEX: 20,178. Total 40,384 — matches Session 15 backfill count exactly.
- Aggregate zone-respect rate over 60-day window: 75.8% within 0.10% band of pivot bar
- **Methodology caveat:** 84.3% of pivots are inside zones (distance=0 from zone). Driven primarily by wide weekly OBs — W_BEAR_OB alone respects 53.2% of pivots single-handedly. The "75.8% respect rate" is largely tautological — wide zones contain most price action. The real edge would be in narrow zones (D-level, H-level) but those have 30-50% respect with much smaller N.
- Two clean-FAIL days where zones existed but didn't predict pivots: NIFTY 2026-04-21, SENSEX 2026-04-22

**Verdict:** **FUNCTIONAL with methodology caveat — wide-zone tautology dominates the headline number.** The system "works" in the sense that zones contain pivots, but the predictive edge of ICT zones for *targeting* pivots specifically is not what the 75.8% number implies.

**Builds arising:** ADR-003 Phase 2 (narrow-zone-only respect-rate, exclude zones >0.50% wide) candidate for future session if zone respect-rate becomes a production sizing input. Not currently a sizing input, so low priority.

---

## Session 16 — TD-056 ret_session regime partition (5m-batch cohort)

**Date:** 2026-05-02 (Session 16)
**Script:** `td056_regime_partition_v1.py`

**Question:** Is the bull-skew on `hist_pattern_signals` (NIFTY 60d 1.83x BULL_FVG/BEAR_FVG ratio) regime-driven (correct behaviour: detector finds more bullish patterns in up-sessions) or detector-driven (asymmetry independent of market regime)?

**Setup:** Partition all FVG signals on `hist_pattern_signals` by `ret_session` sign (UP > +0.05%, FLAT, DOWN < -0.05% per ENH-44 alignment threshold), recompute BULL/BEAR ratio per regime per symbol.

**Findings:**

| Symbol | Regime | BULL_FVG | BEAR_FVG | Ratio |
|---|---|---|---|---|
| NIFTY | UP | 87 | 42 | 2.07x |
| NIFTY | FLAT | 22 | 12 | 1.83x |
| NIFTY | **DOWN** | **112** | **20** | **5.60x** |
| SENSEX | UP | 115 | 88 | 1.31x |
| SENSEX | FLAT | 8 | 3 | 2.67x |
| SENSEX | **DOWN** | **106** | **46** | **2.30x** |

**Bull-skew is REGIME-INDEPENDENT.** Even in DOWN sessions, BULL_FVG outnumbers BEAR_FVG 5.6x on NIFTY and 2.3x on SENSEX. If the skew were regime-driven (correct behaviour), we'd expect ratio to invert in DOWN regime (more BEAR_FVGs when price is falling). It doesn't. The detector is structurally biased toward BULL detection on this code path.

**Verdict on `hist_pattern_signals` cohort:** **Detector-driven not regime-driven.** Filed as TD-056 expansion candidate.

**Live-cohort verification:** See Session 16 Exp 15 entry above, Section 17 — bull-skew also exists on the 1m-live `detect_ict_patterns.py` cohort (NIFTY DOWN 3.29x, SENSEX DOWN 1.50x). **Bull-skew is structural across BOTH code paths**, not just 5m-batch. Plus: live detector emits zero BEAR_FVG signals (TD-058 — separate but related). TD-056 expanded to Severity S2.

**Builds arising:**
- TD-056 EXPANDED to cover both code paths
- TD-058 NEW (live detector emits zero BEAR_FVG)
- Session 17 Priority C: mechanism investigation

---

## Session 16 — Check A (Exp 20 alignment + Exp 15 MTF replication on `hist_pattern_signals`)

**Date:** 2026-05-02 (Session 16)
**Script:** `check_a_exp15_gated_replication_v1.py`
**Status:** SUPERSEDED by Section 17 of `analyze_exp15_trades.py` (live-cohort version with correct cohort)

**Question:** Do Exp 20 (alignment lift +22.6pp) and Exp 10c/Exp 15 (BULL_OB|MEDIUM 90% WR / 77.3% WR) replicate when measured on locally-computed spot-side T+30m on the gated subset of `hist_pattern_signals`?

**Outcome:** Script ran and produced numbers (ALIGNED pooled 53.3%, OPPOSED 48.2%, lift +5.1pp; BULL_OB|MEDIUM cells came back N=0 because `hist_ict_htf_zones` has no H-timeframe entries). **Verdict: methodology error in this script** — was testing on the wrong cohort entirely. `hist_pattern_signals` (5m batch) is not the cohort Exp 15 / Exp 20 measured. The right replication is on the 1m live-detector cohort, which the Session 16 Exp 15 entry above documents.

**Lesson codified:** Read the source script of an experiment before drawing conclusions about whether its claims replicate. Wrong-cohort comparison is the canonical methodology error. (Captured in CLAUDE.md anti-patterns.)

---

## Experiment 50b — Velocity Test on Cluster-FVG Inversion (BULL-only, MARGINAL)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_50b_fvg_on_ob_velocity.py`

**Question:** If Exp 50's cluster-FVG inversion is real, is it driven by exhaustion? Hypothesis: tight clusters (small lookback × small proximity) imply fast pre-FVG velocity, FVG forms over-extended, fails more often. Test: partition cluster-FVGs by velocity quartile and check whether WR drops monotonically Q1 → Q4.

**Setup:**
- Reused Exp 50 cluster definition (BULL_FVG within `lookback_min` after BULL_OB and within `proximity_pct` of OB zone). Same 3×3 sweep grid.
- Velocity = `abs(fvg_price - ob_price) / delta_min` (price-distance per unit time between OB and the subsequent FVG).
- Quartile partition per (lookback_min, proximity_pct) cell.
- Outcome: ret_30m sign per cluster pair.
- BULL-only — `hist_pattern_signals` had 0 BEAR_FVG rows at experiment-run time (subsequently fixed in same session — re-run on bidirectional data is Session 16 carry-forward).

**Decision rule:** PASS = headline cell shows DECREASING WR from Q1 to Q4 AND ≥60% of voting cells (N≥20) show same direction.

**Findings:**

| Lookback | Prox% | N | WR_Q1 | WR_Q4 | Direction |
|---|---|---|---|---|---|
| 30 | 0.50 | 47 | 28.6% | 16.7% | DECREASING |
| 30 | 1.00 | 63 | 31.3% | 25.0% | DECREASING |
| 60 | 0.50 | 75 | 36.8% | 13.3% | **DECREASING (headline cell)** |
| 60 | 1.00 | 110 | 39.3% | 35.7% | DECREASING (slight) |
| 120 | 0.50 | 187 | 51.1% | 38.3% | DECREASING |
| 120 | 1.00 | 242 | 55.7% | 47.5% | INCREASING (anomaly) |

- Headline cell (60min/0.50%, N=75) PASSes — Q1 36.8% → Q4 13.3%, monotonically decreasing.
- Across 7 voting cells (N≥20), 3 of 7 show DECREASING = **43% sweep PASS rate**, below the 60% bar.

**Verdict — MARGINAL.** Direction supports exhaustion at the headline cell, but sweep robustness fails. The inversion could be (a) real exhaustion, (b) survivorship bias in standalone bucket (Exp 50 alternative explanation: as cluster definition expands, the standalone bucket loses higher-quality FVGs that had a "background" OB, dragging standalone WR down disproportionately at loose thresholds), or (c) noise. Cannot ship as a filter without bidirectional validation.

**Builds:** None. Carry-forward to Session 16: re-run on bidirectional data.

---

## Experiment 50 — FVG-on-OB Cluster vs Standalone (BULL-only, FAIL with anomaly; bug-discovery vehicle)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_50_fvg_on_ob_cluster.py`

**Question:** Per ICT's PD Array Matrix theory: does an FVG forming after price leaves an OB (same direction) have higher WR than a standalone FVG? Theory: cluster = institutional sponsorship + structural foundation = higher probability.

**Setup:**
- 3×3 sweep: `lookback_min` ∈ {30, 60, 120} × `proximity_pct` ∈ {0.20%, 0.50%, 1.00%}.
- Cluster = BULL_FVG within `lookback_min` after a BULL_OB AND within `proximity_pct` of OB zone.
- Standalone = BULL_FVG with no preceding BULL_OB in window.
- Outcome: ret_30m sign.
- BULL-only — `hist_pattern_signals` had 0 BEAR_FVG rows (cause was the bug this experiment surfaced).

**Decision rule:** PASS = cluster WR ≥ standalone + 5pp AND cluster EV_30m ≥ standalone × 1.3 AND cluster N ≥ 30.

**Findings (BULL-only):**

| Lookback | Prox% | N_cluster | WR_cluster | WR_standalone | WR_delta | Verdict |
|---|---|---|---|---|---|---|
| 30 | 0.20 | 8 | 0.0% | 36.2% | -36.2pp | FAIL (N too low) |
| 30 | 0.50 | 47 | 21.3% | 36.5% | -15.2pp | FAIL |
| 30 | 1.00 | 63 | 30.2% | 36.2% | -6.1pp | FAIL |
| 60 | 0.20 | 13 | 15.4% | 36.1% | -20.8pp | FAIL |
| 60 | 0.50 | 75 | 24.0% | 36.7% | -12.7pp | FAIL (headline) |
| 60 | 1.00 | 110 | 37.3% | 35.8% | +1.5pp | FAIL |
| 120 | 0.20 | 36 | 36.1% | 35.9% | +0.2pp | FAIL |
| **120** | **0.50** | **187** | **41.2%** | **35.0%** | **+6.2pp** | **PASS (1/9 cells)** |
| 120 | 1.00 | 242 | 49.2% | 32.8% | +16.4pp | FAIL on EV-ratio (mis-calibrated criterion) |

- 1/9 cells PASS at the 120min/0.50% loose threshold only.
- **Monotonic INVERSION of ICT's prediction at tight thresholds**: cluster WR is WORSE than standalone WR. Effect grows as thresholds tighten (largest at 30min/0.20% = -36.2pp WR delta).
- The trend is monotonic and consistent across the sweep grid.
- Two competing explanations (per Exp 50b which tested one): exhaustion vs survivorship in standalone bucket.

**Critical ancillary finding (the actual headline of this experiment).** During Exp 50 setup, discovered `hist_pattern_signals` contained 1,261 BULL_FVG and **0 BEAR_FVG** signals over 13 months. Per market structure (sustained bear periods clearly visible on weekly chart Apr 2024-2026, NIFTY -17% Aug 2024 → Mar 2025), this is impossible. Operator challenged. Triggered five-step `diagnostic_bear_fvg_audit.py`, six-bug code review of `build_ict_htf_zones_historical.py`, two production patches (S1.a + S1.b), full historical backfill (40,384 rows), live builder patch (S1.a + S1.b + 1H BEAR_FVG mirror), signal table rebuild (6,318 → 7,484 rows; **BEAR_FVG 0 → 795**). Closes TD-S1-BEAR-FVG-DETECTOR.

**Verdict — FAIL with anomaly (and a major bug discovered).** ICT's PD Array Matrix prediction is INVERTED on BULL-only data at all but one cell. The actual deliverable from this experiment is the BEAR_FVG production fix.

**Caveats and carry-forward:**
- The EV-ratio criterion (cluster EV_30m ≥ standalone × 1.3) is mis-calibrated when both EVs are tiny negatives — the ratio becomes a meaningless multiple of two near-zeros. Drop this criterion when re-running; keep WR-delta + N-floor only.
- The 1/9-cell PASS at 120min/0.50% may be a survivorship artifact (loose thresholds drain the standalone bucket of background-OB-adjacent FVGs).
- Carry-forward to Session 16: re-run on now-symmetric data — 18 cells (vs 9), proper bear-side test of the inversion claim. Either bear-side replicates the inversion (real signal) or it doesn't (BULL-only artifact).

**Builds:** None directly from Exp 50. The bug discovery led to S1 production patches in `build_ict_htf_zones_historical.py` and `build_ict_htf_zones.py` — that is the deliverable.

---

## Experiment 47b — Backwards-Looking Anchors (HYPOTHESIS FALSIFIED — closes ENH-85 "slower anchor" path)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_47b_backwards_anchor.py`

**Question:** Are `ret_30m_back` (close[B] − close[B−6]) or `ret_60m_back` (close[B] − close[B−12]) more stable than `ret_session` (anchored to session open, the ENH-55 V4 baseline) as direction policy? If so, swapping anchors is a low-cost candidate fix for the ENH-55 flip-flop problem.

**Setup:**
- Pulled `hist_pattern_signals` rows + matching `hist_spot_bars_5m` for backwards lookups.
- Computed `ret_30m_back` and `ret_60m_back` per signal bar.
- Counted same-session direction flips per anchor (number of sign changes per (symbol, trade_date)).
- Per-pattern WR Rule-14-compliant: forward `ret_30m` as outcome; backwards anchor sign as policy.

**Findings:**

| Policy | Same-session flips/session | Multiplier vs ret_session |
|---|---|---|
| ret_session (baseline) | 0.27 | 1.00x |
| ret_30m_back | 0.85 | **3.13x baseline (213% MORE flips)** |
| ret_60m_back | 0.77 | **2.87x baseline (187% MORE flips)** |

- Per-pattern WR using backwards anchors: 53–58% (within noise; not predictive).
- Both backwards-rolling anchors flip MORE than `ret_session`, not less.

**Verdict — FALSIFIED.** `ret_session` (anchored to session open, zero rolling) is structurally the slowest available anchor — there is no "slower anchor" path remaining for ENH-85.

**Implication for ENH-85.** Remaining design paths reduced to: (a) **hard PO3 lock** (anchor flips disallowed when PO3 session bias confirmed — risks fighting genuine reversals; needs Exp 43-style stability backing first), or (b) **persistence filter** (require N consecutive same-direction signals before flipping — adds latency but preserves adaptation). Decision deferred to Session 16+. Status update for ENH-85 reflected in Enhancement Register Status Summary table.

**Note on Exp 43 relationship.** Exp 47b answers a subset of Exp 43's question (option 2 of 4: "slower anchor"). Options 1 (persistence filter), 3 (hysteresis), and 4 (PO3 as soft prior weight) remain testable. Exp 43 itself remains PROPOSED at the register level.

**Builds:** None directly. ENH-85 design space recorded as reduced.

---

## Experiment 47 — Direction Stability Anchor (INVALID — superseded by Exp 47b)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_47_direction_stability_anchors.py`

**Question:** Does using `ret_30m`, `ret_60m`, or `ret_session` as a slower anchor than ENH-55 V4's current anchor reduce same-session direction flips?

**Setup:**
- For each `hist_pattern_signals` row, compute candidate-anchor-direction (sign of metric).
- Count same-session flips per anchor per symbol.
- Compute per-pattern WR using the anchor as the policy.

**Findings:**
- Per-pattern WR 99–100% across all anchors. No real-world classifier achieves this.

**Diagnosis.** `ret_30m` was used as BOTH the policy (sign-as-direction) and the outcome (forward T+30m return per Rule 14). Tautological — predicting the sign of `ret_30m` from the sign of `ret_30m`. The classifier's "win rate" was just measuring agreement of a quantity with itself.

**Verdict — INVALID by construction.** Filed Exp 47b with backwards-looking anchors only (ret_30m_back / ret_60m_back computed from `hist_spot_bars_5m`).

**Builds:** None.

---

## Experiment 44 — Intraday Inverted Hammer Reversal After Cascade (FAIL, with TZ-bug caveat)

**Date:** 2026-05-01 (Session 15)
**Script:** `experiment_44_inverted_hammer_cascade.py`

**Question:** From Session 14 EOD seed observation (NIFTY 09:30–10:00 IST V-recovery from −300pt opening cliff): does an inverted hammer after a sustained intraday cascade, followed by a non-violating range test, predict a reversal large enough to trade at T+30m / T+60m / EOD? Run both bearish-cascade (long-side reversal) AND bullish-cascade mirror (short-side reversal) sides separately.

**Setup:**
- Source: `hist_spot_bars_5m` Apr 2025 → Apr 2026, both symbols, in-session 09:15–15:30 IST per CLAUDE.md Rule 16.
  - **Caveat noted post-result:** Rule 16 was applied verbatim to the entire 263-day sample. The post-04-07 era (~22 sessions) requires era-aware TZ handling per TD-NEW-RULE16-ERA-AWARE — those sessions had ~9 in-session bars analysed instead of ~76. Verdict survives a back-of-envelope re-evaluation (affected sessions are too few to flip cell counts) but a v2 re-run with era-aware TZ would close cleanly.
- Sweep grid: 6 cascade thresholds (`cascade_pct` ∈ {0.20, 0.25, 0.30, 0.35, 0.40, 0.45}%) × 4 lookback bars (`lookback_bars` ∈ {3, 5, 7, 9}) × 2 sides (bull/bear) × 3 horizons (6, 12, 30 bars = 30m, 60m, 2.5h) × 2 symbols = 288 cells.
- Cascade definition: spot drops `cascade_pct` within `lookback_bars` of session open.
- Win: forward return aligned with side at horizon.

**Decision rule:** PASS = (sym, cas, lb, side, horizon) cell with WR ≥ 70 AND N ≥ 30.

**Findings:**
- **No cell met both thresholds simultaneously.**
- Highest-WR cells were N=4–12 (underpowered).
- Highest-N cells (>50) had WR in the 48–58% range.
- The seed pattern (NIFTY V-recovery 2026-04-30) appears to be a single-instance memorable observation, not a generalisable rule.

**Verdict — FAIL.** No tradeable rule. Closed.

**Caveat (re-run option).** Re-run as Exp 44 v2 with era-aware Rule 16 if revisiting; filed as Session 16 Candidate C contingent.

**Builds:** None.

---

## ADR-003 Phase 1 — ICT Zone Respect-Rate Diagnostic (RESULT — INVALID, methodology bug)

**Date:** 2026-05-01 (Session 15)
**Script:** `adr003_phase1_zone_respect_rate_v2.py` (and v1 prior)
**ADR:** See `ADR-003-ict-zone-architecture-review.md` for full Phase 1 results section + Phase 1 v3 plan.

**Question:** Per Session 14 ADR-003 proposal: do `ict_htf_zones` and `hist_ict_htf_zones` zones reflect price-pivot behaviour? Compute respect-rate (% of zone touches where spot reverses within zone) over last 10 trading days for each timeframe. No redesign without numeric evidence.

**Setup:**
- Pulled active zones from both tables for last 10 sessions, both symbols.
- For each zone, found 5m bars where spot entered the zone (high ≥ zone_low AND low ≤ zone_high).
- For each entry, classified as RESPECTED (spot reversed within zone) or BROKEN (spot exited the other side).
- Computed respect-rate per (symbol, timeframe, pattern_type).

**Initial findings (v1, v2 — both INVALID):**
- Raw respect-rate: 0% across all timeframes for both symbols.
- Apparent post-04-07 `hist_spot_bars_5m` coverage: 27.5% (vs ~100% pre-04-07).
- D zone count in lookback: 0.

**Diagnosis (mid-investigation, two independent bugs surfaced):**
1. The 27.5% coverage was a script-side bug. CLAUDE.md Rule 16 says: apply `replace(tzinfo=None)` to bar_ts then filter to in-session 09:15–15:30. This is correct for pre-04-07 era only. Post-04-07 bars are stored as true UTC; Rule 16 verbatim drops most of the day. Real coverage post-04-07 is ~100% per `diagnostic_bar_coverage_audit_v3.py` (which avoids the issue by filtering on `trade_date` column).
2. The 0 D zones in lookback was a separate finding. The historical builder writes D-zone non-FVG with `valid_to = valid_from = target_date` — exactly 1 day validity. By definition, D zones expire by the next session and don't appear in 10-day lookback queries that filter on `valid_from <= lookback_start AND valid_to >= today`.

**Verdict — INVALID.** Methodology compromised by script-side TZ-handling bug AND latent D-zone validity bug. Phase 1 v3 with era-aware Rule 16 needed before any architecture verdict can be drawn.

**Builds:** Two TDs filed — TD-NEW-RULE16-ERA-AWARE (CLAUDE.md Rule 16 needs era-aware addendum, addressed Session 16 Candidate C) and reinforcement of TD-S2.b (D-zone single-day validity for non-FVG). No architecture decision made yet — pending Phase 1 v3.

---

## Experiment 41B — Corrected EV for E4/E5 (ret_30m scale fix)

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_41b_ev_corrected.py`

**Question:** Exp 41 inflated E4/E5 P&L by 100x because `ret_30m` in `hist_pattern_signals` is stored as PERCENTAGE POINTS (0.1351 = 0.1351%), not as a decimal fraction. What are the correct EV numbers?

**Fix:** Divide `ret_30m` by 100 before multiplying by spot. Sign convention: BEAR_OB wins when `ret_30m < 0` (spot fell). BULL_OB wins when `ret_30m > 0`.

**Baseline (all BEAR_OB / BULL_OB, no filter):**
- BEAR_OB NIFTY: WR=49.4%, mean|win=27.1pts, mean|loss=27.8pts, EV=−0.7pts (no edge — correct baseline)
- BEAR_OB SENSEX: WR=51.1%, mean|win=91.9pts, mean|loss=93.7pts, EV=+1.2pts
- BULL_OB NIFTY: WR=48.1%, mean|win=31.4pts, mean|loss=28.7pts, EV=+0.2pts
- BULL_OB SENSEX: WR=48.4%, mean|win=109.3pts, mean|loss=95.9pts, EV=+3.5pts

**E4 — BEAR_OB MIDDAY + PO3_BEARISH (corrected):**

| Symbol | N | WR | Mean win | Mean loss | Win/Loss | EV/trade | Full Kelly | Half Kelly |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 6 | 83.3% | 20.6 pts | 2.2 pts | 9.33x | 16.8 pts | 82% | 41% |
| SENSEX | 11 | 90.9% | 133.7 pts | 55.3 pts | 2.42x | 116.5 pts | 87% | 44% |

PO3 filter multiplies NIFTY EV by 9x and SENSEX EV by 18x over baseline. Real and substantial edge.

**E5 — BULL_OB AFTERNOON + PO3_BULLISH (corrected):**

| Symbol | N | WR | Mean win | Mean loss | Win/Loss | EV/trade | Full Kelly | Half Kelly |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 12 | 50.0% | 27.1 pts | 18.5 pts | 1.46x | 4.3 pts | 16% | 8% |
| SENSEX | 19 | 73.7% | 81.4 pts | 93.1 pts | 0.87x | 35.5 pts | 44% | 22% |

NIFTY E5: EV=4.3pts → discard. SENSEX E5: positive EV=35.5pts but unfavourable win/loss ratio (0.87x). Tail loss risk — size conservatively.

**Verdict:** Kelly fractions are mathematically valid but based on N=6–19. Cap all at 5–8% of risk capital until N=30 live events. Do not apply full Kelly to any edge at current sample sizes.

**Builds arising:** Feeds ENH-76 and ENH-77 sizing rules.

---

## Experiment 41 — P&L and Max Adverse Excursion: All Session 11 Edges

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_41_pnl_mae_all_edges.py`

**Question:** For each of the 7 Session 11 edges, what is the full return distribution in points, the Max Adverse Excursion (MAE), optimal entry timing, and current-week vs next-week option P&L?

**Note:** E4/E5 ret_30m results from this script are incorrect (100x scale error — see Exp 41B). MAE results are correctly computed. Edge 3 option comparison is correctly computed.

**MAE Analysis (E1/E2 — NIFTY and SENSEX sweep entries):**

| Edge | Symbol | MAE P75 | MAE P90 | Minimum viable stop |
|---|---|---|---|---|
| E1 PDH sweep | NIFTY | 83 pts | 94 pts | 100 pts above PDH |
| E1 PDH sweep | SENSEX | 206 pts | 373 pts | 400 pts above PDH |
| E2 PDL sweep | NIFTY | 114 pts | 116 pts | 120 pts below PDL |
| E2 PDL sweep | SENSEX | 314 pts | 379 pts | 400 pts below PDL |

**SENSEX MAE implication:** 400pt stop on SENSEX ATM PE/CE (premium ~₹180–250) means option is down 50–70% before recovery. SENSEX E1/E2 entry at sweep is NOT viable with short-DTE options. Route SENSEX E1 to session bias only; trade via E4 (SENSEX) or E5 (SENSEX). NIFTY E1 is viable: 94pt stop, ATM PE ~₹80–120, option down ~30% worst-case before recovery.

**Entry timing (E1/E2):**

Waiting 1 bar after rejection consistently hurts across all symbols and edges:
- PDH NIFTY: T+0=+3pts WR=50%, T+1=−19pts WR=17%. Waiting costs 22pts.
- PDH SENSEX: T+0=+48pts WR=89%, T+1=−7pts WR=56%. Waiting costs 55pts.
- PDL NIFTY: T+0=−19pts WR=33%, T+1=−22pts WR=33%. Small difference.
- PDL SENSEX: T+0=−75pts WR=38%, T+1=−100pts WR=15%. Waiting costs 25pts.

**Rule: Always enter at rejection bar close (T+0). Never wait.**

**Edge 3 option comparison (correct):**

| | NIFTY | SENSEX |
|---|---|---|
| Current-week PE mean | +46% | +125% |
| Next-week PE mean | +20% | +68% |
| Verdict | Current-week wins | Current-week wins |

Current-week captures gamma explosion on large moves (SENSEX 2026-02-19: +468% CW vs +112% NW). On small moves current-week underperforms, but large moves dominate the mean. **Current-week PE is the correct instrument for E3.**

**E6/E7 P&L reference (from Exp 35C/39B — correctly computed at spot-return level):**
- E6 T+2D mean: +0.667% = +160 pts NIFTY / +534 pts SENSEX
- Next-week CE (DTE~8): ~80–120% option return on mean T+2D move

**Verdict:** MAE defines the stop framework. Entry timing is resolved (T+0 always). Option instrument is resolved (current-week intraday, next-week multi-day). See Exp 41B for corrected E4/E5 EV.

---

## Experiment 40 — PO3 × OB Time Asymmetry Deep Drill

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_40_po3_ob_time_asymmetry.py`
**Verdict:** ✅ FULL PASS (both signals)

**Question:** Are BEAR_OB MIDDAY + PO3_BEARISH and BULL_OB AFTERNOON + PO3_BULLISH valid independent signals with sufficient lift over baseline?

**Origin:** Exp 38 found that mixing MIDDAY and AFTERNOON diluted both signals. This experiment tests each independently with proper pass criteria.

**The 2×2 structural matrix:**

| Signal | N | T+30m WR | Lift vs baseline | Verdict |
|---|---|---|---|---|
| BEAR_OB MIDDAY + PO3_BEARISH | 17 | **88.2%** | **+39.1pp** | ✅ PASS |
| BEAR_OB AFTERNOON + PO3_BEARISH | 18 | 33.3% | — | Hard skip |
| BULL_OB MIDDAY + PO3_BULLISH | 33 | 30.3% | — | Hard skip |
| BULL_OB AFTERNOON + PO3_BULLISH | 31 | **64.5%** | **+16.8pp** | ✅ PASS |

**Sub-buckets Signal 1 (BEAR_OB MIDDAY + PO3_BEARISH):**
- NIFTY: N=6, WR=83.3%
- SENSEX: N=11, WR=90.9%
- TIER1: N=17, WR=88.2% (all signals are TIER1)
- LONG_GAMMA: N=14, WR=85.7%
- Counter (PO3_BULLISH session): N=56, WR=50% — baseline noise

**Sub-buckets Signal 2 (BULL_OB AFTERNOON + PO3_BULLISH):**
- NIFTY: N=12, WR=50% → DISCARD (use SENSEX only)
- SENSEX: N=19, WR=73.7%
- LONG_GAMMA: N=23, WR=60.9%
- Counter anomaly: BULL_OB AFT + PO3_BEARISH = 68.4% — suggests BULL_OB AFTERNOON has intrinsic London-window edge regardless of morning bias

**Structural explanation:**
- Bearish institutions distribute into the midday lull (11:30–13:30 IST) after the morning manipulation. BEAR_OB in MIDDAY = distribution entry.
- Bullish accumulation resolves at London open (13:30+ IST). BULL_OB in AFTERNOON = accumulation completion.
- Mixing windows destroys both signals.

**Verdict:** FULL PASS. Both signals are ENH candidates.

**Builds arising:**
- ENH-76: Gate BEAR_OB MIDDAY signals on `po3_session_bias = PO3_BEARISH`
- ENH-77: Gate BULL_OB AFTERNOON signals (SENSEX only) on `po3_session_bias = PO3_BULLISH`
- Expected firing rate: E4 ~6–9 per symbol per quarter, E5 ~8–10 per symbol per quarter

---

## Experiment 39B — Weekly Sweep Refined

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_39b_weekly_sweep_refined.py`
**Verdict:** ✅ PASS (3 of 5 criteria)

**Origin:** Exp 39 FAIL (PWL EOW WR=35.3% worse than random). Three root cause issues identified: (1) reversal definition too loose — trending markets pass trivially, (2) no gap context required, (3) no Monday filter.

**Refinements applied:**
- Close must retreat ≥15% of prior week's range below PWH (or above PWL) — genuine reversal, not a bounce
- Gap context required: gap-up for PWH sweeps, gap-down for PWL sweeps
- Monday-only subset tested separately

**Results:**

| Test | N | WR | Verdict |
|---|---|---|---|
| PWH refined standalone EOW | 9 | 66.7% | ✅ PASS |
| PWL refined standalone EOW | 13 | **76.9%** | ✅ PASS |
| PWH Monday-only | 3 | 100% | N too small |
| PWL Monday-only | 5 | **80%** | ✅ PASS |
| PWL + daily confluence conf-day EOD | 5 | **100%** | ✅ PASS |

**PWL multi-day continuation:**
- T+1D: WR=84.6%, mean=+0.312% (+250pts SENSEX)
- T+2D: WR=76.9%, mean=+0.667% (+534pts SENSEX)

**PWL + daily PDL confluence (Edge 7 — highest conviction):**
- When PWL sweep week also has a daily PDL swept in OPEN window → 100% conf-day EOD WR (N=5)
- All 5 events were genuine wins. Maximum size entry justified.
- T+2D continuation confirmed → next-week CE instrument

**Note:** `conf_day_win` mean showing 100.000% is a display bug (boolean averaged instead of return value). WR of 100% is correct.

**Filter impact:** Exp 39 (loose) had 27 PWH + 34 PWL events. Exp 39B (refined) has 9 PWH + 13 PWL. Filtering removed ~65% of events that were trending markets, not genuine reversals.

**Verdict:** Weekly sweep edge is REAL once reversal quality is verified. PWL is the stronger side.

**Builds arising:**
- ENH-79: Pre-market PWL sweep detection. Write `weekly_sweep_bias = BULLISH / NONE` to market state by 08:50 IST on sweep detection days.
- Instrument: next-week ATM CE. Entry: sweep day EOD. Stop: session close below PWL. Scale-out: 50% EOD, 50% T+2D.

---

## Experiment 39 — Weekly Sweep HTF Context (Failed — see 39B)

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_39_weekly_sweep_htf_context.py`
**Verdict:** ❌ FAIL

**Finding:** PWL EOW WR=35.3% — worse than random. PWH EOW WR=51.9% — near-random. Root cause: reversal definition too loose. Trending markets hit PWL and close back "inside" on the sweep day while continuing lower the following week. The metric measured a bounce, not a genuine reversal.

Weekly zones in `hist_ict_htf_zones` (timeframe='W') contain BULL_OB/BEAR_OB/FVG/PDH/PDL — no PWH/PWL directly. Weekly levels computed from prior-week high/low via 5m bar aggregation (correct approach).

**Leads to:** Exp 39B with tighter reversal definition.

---

## Experiment 38 — OB in Distribution Leg on PO3 Sessions

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_38_po3_distribution_ob.py`
**Verdict:** ❌ FAIL (combined) — buried signal → Exp 40

**Finding:** When MIDDAY and AFTERNOON are combined:
- BEAR_OB MIDDAY+AFT + PO3_BEARISH: N=35, WR=60% (below 65% threshold)
- BULL_OB MIDDAY+AFT + PO3_BULLISH: N=64, WR=46.9%

But when separated:
- BEAR_OB MIDDAY + PO3_BEARISH: N=17, WR=**88.2%** ← genuine signal
- BULL_OB AFTERNOON + PO3_BULLISH: N=31, WR=**64.5%** ← genuine signal
- BEAR_OB AFTERNOON + PO3_BEARISH: N=18, WR=**33.3%** ← the reversal move is already done
- BULL_OB MIDDAY + PO3_BULLISH: N=33, WR=**30.3%** ← premature, not ready

Mixing MIDDAY and AFTERNOON destroys both valid signals by averaging with the invalid ones.

**Leads to:** Exp 40 testing each independently.

---

## Experiment 37 — London Kill Zone Isolation

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_37_london_kill_zone.py`
**Verdict:** ⚠️ PARTIAL — BEAR_OB concentrated in early LKZ, BULL_OB not

**Key finding:** 607 of 628 AFTERNOON signals sit in 14:30–15:00 IST — the AFTERNOON session label masks that almost all signals are post-London-open, not within it.

| Window | BEAR_OB WR | BULL_OB WR | N (BEAR) |
|---|---|---|---|
| 13:30–14:00 (LKZ EARLY) | **77.8%** | 41.7% | 18 |
| 14:00–14:30 (LKZ CORE) | 44.4% | 30.0% | 18 |
| 14:30–15:00 (bulk) | 49.6% | 51.1% | 607 |
| 15:00–15:30 | 47.6% | 25.8% | 21 |

BEAR_OB 13:30–14:00 at 77.8% (N=18) is the genuine signal. Too small to pass (N<20), but directionally real. Re-test in 3 months as data accumulates. BEAR_OB LKZ/non-LKZ concentration ratio: 1.23x.

BULL_OB is structurally weak in the LKZ — London open creates net bearish pressure on NIFTY/SENSEX. BULL_OB AFTERNOON edge is a London fade, not a London entry.

---

## Experiment 36 — PO3 Session Bias × OB Composition

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_36_po3_ob_composition.py`
**Verdict:** ❌ FAIL

**Finding:** Baseline `hist_pattern_signals` WR = 50.3% (unfiltered). PO3 alignment adds ~0pp to aligned OBs, but counter-bias shows −12pp degradation. PO3 is more useful as a BLOCKER than amplifier for OBs in aggregate.

Key: BEAR_OB on PO3_BULLISH session: WR=38.3% (−12pp vs baseline). Use to block counter-direction signals.

Too sparse: only 5–6% of sessions labelled as PO3_BEARISH or PO3_BULLISH. Works better as a gate on specific sub-windows (see Exp 40) than as a blanket OB filter.

---

## Experiment 35D — PO3 Sweep: DTE Context + Option Selection

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_35d_po3_dte_option_selection.py`
**Verdict:** ✅ PASS (PDH DTE<3 → current-week PE viable; PDL DTE<3 → SKIP)

**Decision table:**

| Scenario | EOD WR | T+1D WR | Mean|wins | Recommendation |
|---|---|---|---|---|
| PDH DTE<3 | 90.9% | 72.7% | 0.329% | ✅ CURRENT-WEEK PE |
| PDH DTE3+ | 100.0% | 50.0% | 0.214% | Current-week PE only |
| PDL DTE<3 | 78.6% | 42.9% | 0.546% | ❌ SKIP/WAIT |
| PDL DTE3+ | 63.6% | 72.7% | 0.385% | Current-week CE only |

**PDH DTE=1 (expiry day itself):** 75% T+1D WR, mean|wins=0.556%. Best single sub-case. Buy next-week PE when NIFTY/SENSEX gaps up on Thursday and sweeps/rejects PDH.

**PDL DTE<3 failure explained:** EOD bounce is mechanical expiry pinning, not institutional. Fades T+1D (42.9% WR). Do not buy CE.

**DTE=1 all events (for manual review):** Five events cross-referenced with TradingView examples in pull_edge_examples.py output and MERDIAN_Edge_Examples_Session11.docx.

**Verdict:** Current-week PE confirmed for PDH DTE<3. PDL DTE<3 is explicitly a SKIP.

**Builds arising:** ENH-78: DTE<3 PDH sweep instrument rule — detect `dte <= 2` at signal time and route to current-week PE with 40% option stop.

---

## Experiment 35C — PO3 Filtered Config + Multi-Day Extension

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_35c_po3_filtered_multiday.py`
**Verdict:** ✅ PASS (both sides EOD; PDH T+1D confirmed; PDL T+1D borderline)

**Filters applied (from Exp 35B failure mode analysis):**
- PDH: block gap >0.5% (real breakout risk, not manufactured stop run)
- PDH: block sweep depth 0.10–0.20% (ambiguous zone, 50% WR)
- PDL: block depth <0.10% (noise ticks, 37.5% WR)

**Filter lift:**
- PDH: 75.9% → **93.3%** (N=15) ← +17pp from filters
- PDL: 63.6% → **72.0%** (N=25) ← +8pp from filters

**Multi-day continuation (filtered events):**

| Horizon | PDH WR | PDL WR | PDH mean|wins | PDL mean|wins |
|---|---|---|---|---|
| EOD | 93.3% | 72.0% | −0.550% (−132 pts NIFTY) | +0.484% |
| T+1D | 66.7% | 56.0% | +0.306% | +0.454% |
| T+2D | 46.7% | 44.0% | +0.552% | +0.672% |
| T+3D | 60.0% | 52.0% | +0.702% | +0.775% |

**Winning multi-day move magnitudes:**
- PDH T+2D wins: mean=+0.552%, median=+0.515%, max=1.166%
- PDL T+2D wins: mean=+0.672%, median=+0.706%, max=2.090%

**SENSEX PDL filtered is exceptional:** 84.6% EOD WR, T+1D 61.5% — near-standalone tradeable on SENSEX.

**Option instrument:** Current-week only (T+1D WR insufficient for next-week theta exposure on PDH). Exception: see Exp 35D for DTE<3 specific case.

**Verdict:** Filters from 35B significantly lift both edges. EOD signal quality STRONG. Multi-day continuation PARTIAL (confirmed for PDH T+1D, borderline for PDL).

---

## Experiment 35B — PO3 First Sweep Deep Drill

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_35b_po3_first_sweep_deep_drill.py`
**Verdict:** ✅ INFORMATIVE DIAGNOSTIC (not pass/fail — drove Exp 35C)

**Q1 — Return trajectory:** Edge is ENTIRELY BACK-LOADED.

| Horizon | PDH WR | PDL WR |
|---|---|---|
| T+30m | 27.6% | 15.2% |
| T+60m | 10.3% | 0.0% |
| T+120m | 20.7% | 3.0% |
| EOD | **75.9%** | **63.6%** |

**Critical implication:** This is a SESSION BIAS SETTER, not an intraday entry signal. Entering at rejection bar → stopped out before the move most of the time. Use it to set session direction, wait for OB in distribution leg.

**Q2 — Reversal speed:** T+2 bar (10 min) reversal = 40% WR danger zone. T+1 (instant snap) and T+3+ (slow grind) are both strong. Exclude T+2 bar reversals from the signal.

**Q3 — Failure modes:**
- PDH large gap >0.5%: 42.9% WR (real breakout, not manufactured stop run — block this)
- PDH depth 0.10–0.20%: 50% WR (ambiguous — block this)
- PDL shallow <0.10%: 37.5% WR (noise tick — block this)
- PDH losers: 2026-03-24 (gap=1.625%), 2026-03-05 (gap=0.553%) — both large-gap events

**Sweep depth × EOD WR:**
- PDH 0.05–0.10%: 100% WR (N=8) — shallow fake, clean
- PDH 0.10–0.20%: 50% WR (N=10) — danger zone, real breakout attempts
- PDH >0.20%: 81.8% WR (N=11) — engineered deep sweep

**Gap size × EOD WR:**
- PDH small gap (<0.2%): 81.8% WR
- PDH medium gap (0.2–0.5%): 90.9% WR ← best
- PDH large gap (>0.5%): 42.9% WR ← block

**Builds arising:** Filter definitions for Exp 35C production config.

---

## Experiment 35 — First PDH/PDL Sweep as PO3 Session Bias

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_35_po3_first_sweep_session_bias.py`
**Verdict:** ⚠️ PARTIAL PASS (PDH passes, PDL borderline)

**Question:** When the FIRST touch-and-rejection of PDH occurs in the OPEN window (09:15–10:00), does the session close bearish (EOD WR ≥ 60%)? Mirror for PDL.

**Setup:** OPEN window only (09:15–10:00 IST), gap context required, sweep ≥0.05%, reversal within 6 bars (30 min). NIFTY + SENSEX.

**Results:**

| Scenario | N | EOD WR | Mean ret |
|---|---|---|---|
| PDH first-sweep + gap-up OPEN | 35 | **74.3%** | −0.307% |
| PDL first-sweep + gap-down OPEN | 37 | **67.6%** | +0.232% |
| PDH sweep + gap-down/flat | 22 | 50.0% | −0.012% |
| PDL sweep + gap-up/flat | 31 | 48.4% | −0.060% |

Gap context is the key discriminator. Non-aligned gaps → coin flip.

Sweep depth:
- PDH 0.05–0.10%: 81.8% WR
- PDH 0.10–0.20%: 33.3% WR (danger zone)
- PDH >0.20%: 76.5% WR
- PDL >0.10%: 63–76% WR

**Verdict:** PARTIAL PASS. Leads directly to Exp 35B (deep drill) and 35C (filtered production config).

---

## Experiment 34 — PDH/PDL Liquidity Sweep + Rejection (All Intraday)

**Date:** 2026-04-28 (Session 11)
**Script:** `experiment_34_pdh_pdl_liquidity_sweep.py`
**Verdict:** ❌ FAIL

**Question:** When a 5m bar's wick sweeps PDH by ≥0.05% and price closes back inside within 6 bars, does the move continue bearishly at T+60m with WR ≥ 60%?

**Setup:** All intraday PDH/PDL sweeps (not just first), both NIFTY and SENSEX. OPEN through AFTERNOON sessions.

**Findings:**
- PDH sweeps (N=373): T+60m WR=11.1%, mean=−0.038%
- PDL sweeps (N=447): T+60m WR=1.8%, mean=−0.024%
- Events per session: ~0.73 PDH, ~0.88 PDL — these are routine intraday mean reversions, not institutional stop runs

**Verdict:** FAIL comprehensively. Naked intraday PDH/PDL sweeps have no edge. They are normal mean reversion noise. The ICT BSL/SSL thesis requires first-sweep + gap context + session timing constraint.

**Engineering bugs fixed during this experiment (now baked into all subsequent scripts):**
- B1: `hist_spot_bars_5m` has no `is_pre_market` column → time-based filter (09:15–15:30 IST)
- B2: Supabase pagination hard-caps at 1000 rows/request (not 5000) → `page_size = 1000`
- B3: TD-029 timezone: `bar_ts` stored as IST labeled +00:00. `astimezone(IST)` adds 5:30 wrongly → fix: `replace(tzinfo=None)` to treat stored value as naive IST

**One genuine sub-signal:** PDH MORNING WR=20.4%, mean=−0.192% — directionally correct but below threshold. Points to Exp 35 (first-sweep + morning context).

**Builds arising:** None (FAIL). B1/B2/B3 bug fixes propagated to all subsequent experiment scripts.

---

## Experiment 33 — Inside Bar Before Expiry (Breakout thesis)

**Date:** 2026-04-27 (Session 10 extension)
**Script:** `experiment_33_inside_bar_before_expiry.py`

*(Previously logged — see Session 10 entry. Included here for compendium completeness.)*

**Verdict:** Breakout thesis SUPPORTED (93% break rate, 71% next-day continuation, 93% mid-of-range close). Pin thesis REJECTED (only 7% pin rate). N=14 — small. ENH-47 filed. Discretionary use first.

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
- **BEAR_OB MIDDAY + PO3_BEARISH: 88.2% WR — near-TIER1 (NEW — Exp 40)**

### TIER2 (80-91% WR setups — deploy Full Kelly 80% of sizing capital)
- BULL_OB | MOM_YES
- BULL_OB | IMP_STR
- BULL_OB | DTE=4+
- BEAR_OB | MOM_YES
- BEAR_OB | DTE=4+
- JUDAS_BULL | DTE=2-3
- **PDH first-sweep filtered (EOD): 93.3% WR — TIER2 as session bias (NEW — Exp 35C)**

### TIER3 (standard setups — deploy Full Kelly 40% of sizing capital)
- All other BULL_OB
- All other BEAR_OB (except AFTERNOON — skip)
- JUDAS_BULL (unqualified)
- BULL_FVG with SHORT_GAMMA + BULLISH breadth context
- **BULL_OB AFTERNOON + PO3_BULLISH (SENSEX only): 64.5% WR (NEW — Exp 40)**
- **PWL refined weekly sweep: 76.9% EOW (NEW — Exp 39B)**

### SKIP (do not trade)
- BEAR_OB | AFTERNOON (13:00-14:30) — -24.7% expectancy
- **BEAR_OB | AFTERNOON + PO3_BEARISH: 33.3% WR — hard skip (move already done)**
- BEAR_OB | DTE=0 or DTE=1 — use combined structure instead
- BULL_FVG without MERDIAN regime context — 50.3% WR (near-random)
- BEAR_FVG | HIGH context — -40.2% expectancy
- LONG_GAMMA signals — validated below random
- **BULL_OB MIDDAY + PO3_BULLISH: 30.3% WR — hard skip (premature)**
- **NIFTY BULL_OB AFTERNOON + PO3_BULLISH: 50.0% WR — skip, SENSEX only**
- **PDL DTE<3 next-week CE: 42.9% T+1D WR — expiry pinning bounce, not institutional**

---

## Capital and Sizing Reference

From Experiment 16 (confirmed; Session 11 additions noted):

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
| **Session 11 addition** | **5–8% cap per new edge** | **Cap all Session 11 Kelly fractions until N=30 live events** |
| **Session 11 addition** | **Max 2% capital at risk per concurrent trade** | **Multiple edges can fire same session; cap total exposure** |

---

*MERDIAN Experiment Compendium v1 — 2026-04-12*
*Living document. Prepend new experiments. Never delete prior findings.*
*Last updated 2026-04-28 (Session 11 — Exp 34 through 41B)*
