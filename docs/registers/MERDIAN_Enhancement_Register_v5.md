# MERDIAN Enhancement Register v5

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | MERDIAN_Enhancement_Register_v5.md |
| Supersedes | MERDIAN_Enhancement_Register_v4.md (2026-04-11) |
| Updated | 2026-04-12 |
| Sources | Enhancement Register v4 · Research Sessions 2 and 3 (2026-04-11 through 2026-04-12) |
| Purpose | Forward-looking register of all proposed MERDIAN improvements. Living document. |
| Authority | Tracks proposals, not decisions. Decisions live in master Decision Registry. |
| Update rule | Update in the same session that produces new architectural thinking. Commit immediately. |

---

## v5 Changes from v4

| Change | Detail |
|---|---|
| ENH-35 status | COMPLETE — full year validation run. NIFTY 58.6% T+30m accuracy. Shadow gate at 8/10. |
| ENH-37 status | COMPLETE — ICT layer fully built and wired into runner and dashboard |
| ENH-38 NEW | Live Kelly tiered sizing implementation |
| ENH-39 NEW | Capital ceiling enforcement (₹25L freeze, ₹50L hard cap) |
| ENH-40 NEW | Signal Rule Book v1.1 incorporating all experiment findings |
| ENH-41 NEW | BEAR_OB DTE gate — combined structure for DTE=0 and DTE=1 |
| ENH-42 NEW | Session pyramid — deferred post-experiment |
| Futures experiments | PERMANENTLY CLOSED — options-only going forward |
| Experiment 15b | IN PROGRESS — date type fix needed, run pending |

---

## Tier 1 — Actionable Now

---

### ENH-35: Historical Signal Validation

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

**Full year results (Apr 2025–Mar 2026):**
- NIFTY: 244 signals, 58.6% T+30m accuracy — STRONG EDGE
- SENSEX: 24 signals, 20.8% T+30m — BELOW RANDOM (too few signals; regime mismatch)
- trade_allowed=YES pool: 268 bars, 55.2% accuracy

**Six signal engine changes applied (all validated):**
1. CONFLICT BUY_CE now trades (58.7%/55.4% accuracy confirmed)
2. LONG_GAMMA → DO_NOTHING (47.7% — below random)
3. NO_FLIP → DO_NOTHING (45-48% — below random)
4. VIX gate removed (HIGH_IV has more edge on OBs)
5. Confidence threshold 60→40
6. Power hour gate — no signals after 15:00 IST

---

### ENH-37: ICT Pattern Detection Layer

| Field | Detail |
|---|---|
| Status | **COMPLETE** |
| Updated | 2026-04-11 |

**Components built:**
- `ict_zones_ddl.sql` — ict_zones (28 cols) + ict_htf_zones (16 cols) — LIVE in Supabase
- `detect_ict_patterns.py` — ICTDetector, VERY_HIGH/HIGH/MEDIUM/LOW MTF hierarchy
- `build_ict_htf_zones.py` — W/D/H zone builder, 39 zones on first run
- `detect_ict_patterns_runner.py` — runner integration, every 5-min cycle
- `patch_runner_ict.py` — wired ICT step between market_state and signal
- `patch_signal_ict.py` — 4 new signal fields: ict_pattern, ict_tier, ict_size_mult, ict_mtf_context
- Dashboard ICT zones card — live

**MTF hierarchy validated by experiments:**
- W = VERY_HIGH (weekly zone)
- D = HIGH (daily zone)
- H = MEDIUM (1H zone — same session, confirmed adds edge)
- NONE = LOW (no zone — still profitable, 64.3% WR on pure ICT)

**Key finding from Exp 10c and Exp 15:**
MEDIUM context (1H zone) outperforms HIGH (daily) for BULL_OB: +73.5% vs +40.7% expectancy. Keep MEDIUM in hierarchy.

---

### ENH-38: Live Kelly Tiered Sizing

| Field | Detail |
|---|---|
| Source | Experiment 16 — Kelly Tiered Sizing with Compounding Capital |
| Status | **PROPOSED — next live build** |
| Dependency | ENH-37 (tier classification already wired) |
| Priority Tier | 1 |
| Commercial Relevance | Internal — directly affects P&L |

**What it does:** Replaces fixed lot sizing with Kelly-fraction-based sizing computed per trade from current capital. Four tiers based on empirical WR from full-year research.

**Kelly fractions (validated):**

| Tier | Criteria | WR | Half Kelly | Full Kelly |
|---|---|---|---|---|
| TIER1 | BULL_OB MORNING, BULL_OB DTE=0, BEAR_OB MORNING, BULL_OB SWEEP+MOM_YES | 93-100% | 50% | 100% |
| TIER2 | BULL_OB MOM_YES, BEAR_OB MOM_YES, BULL_OB IMP_STR, BULL_OB AFTERNOON, BEAR_OB DTE=4+ | 80-91% | 40% | 80% |
| TIER3 | JUDAS_BULL, BULL_FVG, BEAR_OB (unqualified), BULL_OB (unqualified) | 49-73% | 20% | 40% |

**Experiment 16 results (with ₹25L/₹50L ceiling):**

| Strategy | Combined Return | Max DD | Ret/DD |
|---|---|---|---|
| A — Original 1→2→3 | +494% | 12.7% | 38.9x |
| B — User 7→14→21 (T1+2) | +855% | 13.4% | 63.6x |
| C — Half Kelly | +18,585% | 16.6% | 1,122x |
| D — Full Kelly | +44,234% | 24.8% | 1,785x |

**Recommendation:** Start with Strategy C (Half Kelly) live. After 3-6 months confidence in fill quality, upgrade to D. Strategy D wins on risk-adjusted return (Ret/DD 1,785x vs 1,122x) with only 8.2pp additional drawdown.

**Compounding rule:** After every trade, capital += P&L. Next trade's lot count recalculated from updated capital. No floor reset — losses reduce capital permanently.

---

### ENH-39: Capital Ceiling Enforcement

| Field | Detail |
|---|---|
| Source | Decision in research session 3 |
| Status | **PROPOSED — implement with ENH-38** |
| Dependency | ENH-38 |
| Priority Tier | 1 |
| Commercial Relevance | Internal — risk management |

**What it does:** Enforces two capital limits driven by NIFTY/SENSEX options liquidity constraints:
- **₹25L freeze:** Sizing capital frozen at ₹25L. Lots do not increase beyond this level even as account grows. Profits above ₹25L accumulate but don't translate to more lots.
- **₹50L hard cap:** Absolute ceiling. No lot calculation ever uses more than ₹50L equivalent. Large orders above ₹50L create market impact, widen spreads, and make precise entry questionable even with algorithmic placement.
- **₹2L floor:** If capital falls below ₹2L, size as if capital = ₹2L. Prevents sizing collapse after drawdown making recovery impossible.

**Implementation:** `effective_sizing_capital(capital)` function — already built in experiment_16_kelly_tiered_sizing.py and experiment_15b_kelly_sizing.py.

---

### ENH-40: Signal Rule Book v1.1

| Field | Detail |
|---|---|
| Source | Synthesis of Experiments 2, 2b, 5, 8, 10c, 15, 16 |
| Status | **PROPOSED — document update required** |
| Dependency | None — all evidence gathered |
| Priority Tier | 1 |
| Commercial Relevance | Internal — trading rules |

**What it does:** Updates the live trading signal rules based on full-year empirical research. Key changes from current rules:

**NEW rules (add):**
- BEAR_OB AFTERNOON (13:00-14:30) → SKIP. WR drops to 17%, expectancy -24.7%. Hard skip.
- BULL_OB AFTERNOON (13:00-15:00) → TIER1. 100% WR, +75.3% expectancy. Best afternoon window.
- BULL_FVG|HIGH|DTE=0 → TIER1. N=12, 87.5% WR, +58.9% expectancy. New rule.
- JUDAS_BULL confirmation window → T+15m (not T+5m). T2 rate jumps from 12% to 44%.
- MOM_YES filter → single strongest filter across all patterns (+21.6pp lift on BEAR_OB).

**CHANGED rules (update):**
- BEAR_OB DTE=0 and DTE=1 → combined structure (futures + CE insurance), NOT pure PE buying. Options lose money on these DTE due to theta kill rate (22%+ at T+30m). Futures +0.1-0.4% expectancy vs options -14.6% to -19.1%.
- BULL_FVG without MERDIAN regime context → TIER3 minimum sizing only. 50.3% WR on pure ICT. Needs SHORT_GAMMA + BULLISH breadth to qualify for TIER1/TIER2.
- BEAR_FVG in HIGH context → remove HIGH filter. HIGH context destroys BEAR_FVG edge (-40.2% vs -17.9% in LOW). Use BEAR_FVG without zone filter.

**CONFIRMED rules (keep as-is):**
- T+30m exit. Confirmed over ICT structure break exit across all experiments (+41% more P&L, WR 63.8% vs 36.9%).
- BEAR_OB MORNING → TIER1. 100% WR, +70.9% expectancy on full year.
- BULL_OB DTE=0 → TIER1. 100% WR, +107.4% expectancy.
- 1H zones (MEDIUM context) → keep in ENH-37 hierarchy. BULL_OB inside 1H zone: 83.3% WR, avg +₹18,938 vs +₹9,774 without.

---

### ENH-41: BEAR_OB DTE Gate — Combined Structure

| Field | Detail |
|---|---|
| Source | Experiment 2b (Futures vs Options) |
| Status | **PROPOSED** |
| Dependency | Futures execution capability (minor) |
| Priority Tier | 1 |
| Commercial Relevance | Internal — prevents systematic option loss on expiry-day BEAR trades |

**What it does:** For BEAR_OB trades on DTE=0 and DTE=1 specifically, uses a combined execution structure: short futures position + long ATM CE as insurance. This avoids the PE theta kill problem (22% theta kill rate at T+30m on BEAR_OB DTE=0, -14.6% option expectancy vs +0.1% futures expectancy).

For BEAR_OB DTE=2+: pure PE buying continues (options +25-32% expectancy on these DTE).

---

### ENH-42: Session Pyramid — Deferred

| Field | Detail |
|---|---|
| Source | Experiments 14 and 14b |
| Status | **DEFERRED — post ENH-38 stable** |
| Dependency | ENH-38 (Kelly sizing must be live and stable first) |
| Priority Tier | 2 |

**Context:** Experiments 14 and 14b tested pyramid entries within a session (add on T2 confirmed reversal). Verdict: single T+30m exit on first OB remains optimal. Session pyramid -₹12,645 vs single trade over the full year. Deferred until Kelly tiered sizing is live and producing data.

---

## Summary Table — Full Register

| ID | Title | Tier | Status |
|---|---|---|---|
| ENH-01 | ret_session momentum | 1 | IN PROGRESS |
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
| ENH-36 | hist_* to live promotion pipeline | 1 | NOT BUILT |
| ENH-37 | ICT pattern detection layer | 1 | **COMPLETE** |
| ENH-38 | Live Kelly tiered sizing | 1 | **PROPOSED — next build** |
| ENH-39 | Capital ceiling enforcement | 1 | **PROPOSED — with ENH-38** |
| ENH-40 | Signal Rule Book v1.1 | 1 | **PROPOSED — document update** |
| ENH-41 | BEAR_OB DTE gate | 1 | **PROPOSED** |
| ENH-42 | Session pyramid | 2 | DEFERRED |
| ENH-09 | Heston calibration layer | 2 | PROPOSED |
| ENH-10 to ENH-27 | Downstream of Heston | 2-4 | PROPOSED |

---

*MERDIAN Enhancement Register v5 — 2026-04-12 — Living document, commit to Git after every update*
*Supersedes v4 (2026-04-11). Commit alongside session log and open items update.*
