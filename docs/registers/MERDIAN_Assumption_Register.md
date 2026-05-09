# MERDIAN Assumption Register

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Assumption_Register.md` |
| Location | `docs/registers/` |
| Type | Living register of every unvalidated design decision and its current state |
| Lineage | Promoted from `GammaEngine_Master_V15.1.docx` Appendix D (March 2026) → refreshed post-ADR-007 V18F ICT pivot (May 2026) |
| Established | 2026-05-09 (Session 23 — created as direct follow-up to ADR-007, since ADR-002 cites Appendix D as authoritative and ADR-007's open-follow-up #4 mandates the refresh) |
| Update rule | Inline updates whenever experimental evidence validates / refutes / supersedes an assumption. Superseded rows are annotated, never deleted. Doc Protocol v4 Rule 9.5 + Rule 11.2. |

---

## Purpose

Every threshold, every gate, every regime classifier, every formula in MERDIAN was set by *something* — judgment, NSE convention, theoretical reasoning, prior validation. This register records what that something was, and whether subsequent evidence has confirmed, refuted, or superseded it.

Two uses:

1. **Pre-change discipline.** Before modifying a threshold or gate, look up its row here. If the assumption is still LIVE (unvalidated), the change requires data per Doc Protocol's Measure → Validate → Shadow → Promote framework. If the assumption is VALIDATED, you're proposing to overturn validated work and need an ADR with stronger evidence than the validation cohort. If it's SUPERSEDED or REFUTED, the change may already be moot.
2. **ADR anchor.** ADR-002 cites V15.1 Appendix D as authoritative for the assumption gaps it addresses. Now ADR-002's citation lives here.

---

## Status taxonomy

| Status | Meaning | Required to change |
|---|---|---|
| **LIVE** | Assumption still in effect, unvalidated. May or may not still apply post-pivot. | Per Measure→Validate→Shadow→Promote |
| **VALIDATED** | Empirical evidence confirms the assumption. | ADR with cohort that overturns the validation |
| **REFUTED** | Empirical evidence contradicts the assumption. | Action required: drop the assumption from live code |
| **SUPERSEDED** | Replaced by a different mechanism (typically post-architectural-shift). Annotation links the superseding ADR. | Already handled |
| **RESOLVED** | Was a known bug or gap, now fixed. | Already handled |

---

## D.1 Signal Engine assumptions

V15.1 Appendix D §D.5 originally. Largely SUPERSEDED post-ADR-007 (V18F ICT pivot). The architecture changed from confidence-threshold-gated decision to ICT-pattern-triggered decision; most of the V15.1 signal-engine assumptions belonged to the prior architecture.

| Assumption (V15.1) | How set | Status | Evidence / annotation |
|---|---|---|---|
| `min_confidence_threshold = 60` — signals below 60 are not executed | Seeded in `system_config`; never empirically tested at the time | **SUPERSEDED by ADR-007** | V18F SRB-05: lowered to 40. The V15.1 rule "no threshold change without 30+ sessions of regret-log data" was satisfied by `signal_regret_log` (614 rows, V18A) plus full-year backtest (V18C–F). Lower threshold passes more signals without materially degrading accuracy. |
| `min_dte_threshold = 2` — options with DTE < 2 are not traded | Risk conservatism around expiry-day gamma explosion | **SUPERSEDED by ADR-007** | Replaced by DTE-aware tier rules (V19 §8.3): BULL_OB DTE=0 = TIER1; BEAR_OB DTE=0/1 = SKIP under specific gates; BEAR_OB DTE=4+ MOM_YES = TIER1. Theta-kill rate and tier interact rather than a single global DTE threshold. |
| `reasons` field is dynamically generated from the actual decision path, not templated text | Confirmed in V15 architecture review | **VALIDATED — LIVE** | Carried forward into ICT-era. `signal_snapshots.reasons` reflects the actual conditional branch taken in `build_trade_signal_local.py`. |
| Confidence-score 0–100 is the primary signal trigger | V11→V15.1 architecture | **SUPERSEDED by ADR-007** | Confidence-score is now an adjustment layer beneath ICT tier (V19 §8.4). ICT pattern detection is the trigger. |
| LONG_GAMMA hard block applied regardless of `flip_distance` | Binary regime simplicity; never validated against distance | **VALIDATED post-Exp 17/19** | Counterintuitively, Exp 17 (1m) and Exp 19 (5m) confirmed: BULL_OB 50.5% vs BEAR_OB 49.7% under LONG_GAMMA — pooled 47.7% WR, below random. Binary block is correct. The V15.1-spec'd three-zone refinement is unnecessary. The 11 March 2026 case study insight (binary block was wrong on a 2.2%-from-flip session) is preserved as diagnostic; the pivot to ICT triggers means the block now operates on a different signal-source upstream. |
| Breadth-momentum CONFLICT → unconditional DO_NOTHING | Architectural conservatism; never validated | **SUPERSEDED by ADR-007 SRB-01** | V18F evidence: CONFLICT BUY_CE produces 58.7% WR (NIFTY) / 55.4% (combined). Reversing the lift lowered backtest accuracy. Rule lifted. V15.1 §3.3 "open architectural question" is closed. |

### New post-pivot signal-engine assumptions (LIVE — pending validation as live data accumulates)

| Assumption (post ADR-007) | How set | Status | Evidence / annotation |
|---|---|---|---|
| ICT TIER1/TIER2/TIER3 boundaries (per V19 §10.3) reflect true edge differentials | V18F Exp 15/16 cohort | **LIVE — partial** | Exp 15 backed the gross hierarchy (TIER1 ≈ 90%+ WR, TIER2 ≈ 60–80%, TIER3 ≈ 50%). Live data accumulating since V18G (Phase 4A). Re-validate after 30+ live trades per tier. |
| ENH-37 MTF context boost (HIGH > MEDIUM > LOW) is the right hierarchy | V18F Exp 10c/15 cohort | **LIVE — questioned by TD-059** | Session 16 evidence on N=231 live cohort shows LOW outperforms HIGH on OB patterns. Filed as TD-059 / ENH-89. Current production treatment: annotation-only (do not size up on HIGH). Decision deferred (Option A annotation, B inversion, or C shadow A/B test). |
| Power hour gate: no signals after 15:00 IST | V18F (ENH-35) | **LIVE — convention** | Reasonable practitioner convention; not separately tested for ICT-era. Re-validate when sample size permits. |
| Confidence modifiers (PCR ±5, skew ±4, flow ±3) reflect proportional edge contribution | V18F Exp 21–25 small-but-measurable evidence | **LIVE** | Each ENH-02/04 backed by an experiment showing measurable but small edge. The exact point allocations are heuristic; could be re-fitted with more data. |
| Breadth modifier (BEARISH+BUY_PE = +5, BULLISH+BUY_CE = +5) adds edge | V15.1 carry-over (assumed); V18F Exp 20 contradicts | **REFUTED — ENH-43 candidate** | Exp 20 shows breadth contributes +/- 1.0pp = pure noise. ENH-43 is the candidate to remove. Action required: remove breadth scoring block from `build_trade_signal_local.py`. Estimated 0.5 session of work. |

---

## D.2 Gamma Regime assumptions

V15.1 Appendix D §D.2 originally. Largely INTACT post-ADR-007. The gamma layer was not the locus of the V18F pivot; the pivot was upstream (signal trigger). V15.1's gamma-regime assumptions were either confirmed by Exp 17/19 evidence or remain unvalidated.

| Assumption (V15.1) | How set | Status | Evidence / annotation |
|---|---|---|---|
| Binary LONG/SHORT regime based on `net_gex` sign only. No consideration of distance from flip | Design simplicity; distance was known but not used in regime gate | **VALIDATED — Exp 17/19** | Exp 17 (1m) + Exp 19 (5m) confirmed: pooled 47.7% WR under LONG_GAMMA across both BULL_OB and BEAR_OB. Binary correct. Three-zone model superseded as unnecessary refinement (the `gamma_zone` field still exists in `gamma_metrics` for future research, but its V15.1-spec'd behavioral role is moot). |
| LONG_GAMMA means dealers dampen moves and directional trades have lower expected value | Theoretical — based on dealer hedging mechanics | **VALIDATED indirectly** | Exp 17/19 binary block evidence is the direct empirical confirmation: directional trades under LONG_GAMMA are systematically below random WR. Mechanism (dealer dampening) is consistent. |
| Single expiry dominates GEX calculation. No multi-expiry weighting | Near-term expiry selected | **LIVE** | Not specifically tested in V18F. Multi-expiry GEX would require additional ingestion + computation. Worth experiment on expiry week specifically. Not blocking. |
| `flip_distance_pct` in schema; absolute points in live JSON — unit inconsistency | Documented bug in V15.1 §5.3 | **RESOLVED in V18A** | `flip_distance_pct` is now the canonical field; `flip_distance_points` retained as diagnostic. ADR-002 P1 (zones over points) cites the resolution as the canonical-percent precedent. |
| CE gamma positive, PE gamma negative — sign convention used in net_gex | Standard Black-Scholes gamma sign convention | **VALIDATED — LIVE** | No challenge raised. Industry standard. |
| Near-flip regime (within 0.5%) has different outcome distribution than far-flip (> 1.5%) | V15.1 spec'd as reason for three-zone model | **REFUTED post-Exp 17/19** | Three-zone model would have been the test; ADR-007 establishes that the empirical answer is "the binary regime is correct as a gate but the signal trigger upstream was wrong." `gamma_zone` field still computed, but no behavioral effect in current rules. Could re-emerge as a research artifact; not a live assumption. |
| ADR-002 P5 PINNED gamma regime is a distinct state class beyond LONG/SHORT/NO_FLIP | ADR-002 architectural commitment | **LIVE — pending build** | ENH-82 will deliver. When built, will integrate as additional gate or modifier (structurally similar to LONG_GAMMA / NO_FLIP). |

---

## D.3 Breadth Engine assumptions

V15.1 Appendix D §D.1 originally. Mostly LIVE but the broader role of breadth in MERDIAN is pending deprecation per ENH-43.

| Assumption (V15.1) | How set | Status | Evidence / annotation |
|---|---|---|---|
| Equal-weighting of ~1,385 stocks. Larger index components have no more influence than small caps | Architectural simplicity; never tested | **LIVE — partial mitigation via WCB** | V16 introduced WCB (Weighted Constituent Breadth) which addresses this for the index-driver subset. Equal-weighted breadth survives in `market_breadth_intraday`. Pending ENH-43 decision on whether to deprecate the breadth confidence modifier entirely. |
| BULLISH threshold: `breadth_score >= 62.5` | Judgmental — set in `system_config` | **LIVE** | Not validated for ICT-era. Pending ENH-43 outcome. If ENH-43 removes breadth from confidence scoring, threshold becomes irrelevant for the signal layer (still meaningful for analytical/diagnostic purposes). |
| BEARISH threshold: `breadth_score <= 37.5` | Judgmental — set in `system_config` | **LIVE** | Same. |
| DMAs computed from EOD closes. Intraday DMA values are fixed at yesterday's close during session | Intraday DMA computation not implemented | **LIVE** | Status unchanged. Computation cost is the blocker. Open question: does intraday DMA refresh produce materially different breadth scores? Untested. |
| `breadth_score_change` is a valid short-term momentum proxy | Derived feature; never independently validated | **SUPERSEDED post-ADR-007** | Momentum signals are now ICT-derived (pattern bars, MOM_YES gate, ret_session) plus PO3 session bias. `breadth_score_change` is no longer used as a momentum input in the live signal engine. Field still computed; consumer relationship dropped. |
| Breadth contributes +5 confidence when aligned (BEARISH+BUY_PE, BULLISH+BUY_CE) | V15.1 carry-over | **REFUTED — ENH-43 candidate** | Cross-referenced from D.1. Exp 20 shows breadth +/- 1.0pp = pure noise. ENH-43 to remove from `build_trade_signal_local.py`. |

---

## D.4 Momentum assumptions

V15.1 Appendix D §D.4 originally. Heavily refreshed post-ADR-007. The role of momentum changed from "primary direction signal" to "confirmation modifier" (ret_5m demoted; ret_session built).

| Assumption (V15.1) | How set | Status | Evidence / annotation |
|---|---|---|---|
| `ret_5m` is a valid momentum signal — a single 5-minute return captures direction | Standard short-term momentum measure; not validated in NSE context | **SUPERSEDED by ADR-007** | The 11 March 2026 case study (V15.1 §3.6 / V16 §4) was the founding evidence that single-horizon `ret_5m` produces wrong direction calls on trend days with micro-bounces. Post-ADR-007 `ret_5m` is no longer a primary direction signal. It survives as one of several momentum-confirmation inputs (ENH-01 in V18G adds `ret_session` as the session anchor). |
| VWAP slope is computed over an unspecified window | Implementation detail not captured | **LIVE — TD candidate** | Window still not formally specified in `build_momentum_features_local.py`. Worth a 0.5-session audit to either document the actual window or formally fix it. Not blocking. |
| Breadth-momentum CONFLICT → unconditional DO_NOTHING. No resolution logic | Architectural conservatism; never validated | **SUPERSEDED by ADR-007 SRB-01** | Cross-referenced from D.1. CONFLICT BUY_CE 58.7% WR. Rule lifted. V15.1 §3.3 "open architectural question" is closed. |
| `ret_session` does not exist. Session direction anchor is absent | Measurement gap; never built | **RESOLVED V18G (ENH-01)** | `ret_session` is now live in `momentum_snapshots`. Session-open threshold 03:35 UTC accepts 09:05 IST PreOpen capture. Used as confirmation modifier in confidence scoring, not as a primary trigger. |
| Multi-horizon momentum voting model (ret_5m / ret_15m / ret_60m / ret_session / vwap_slope, ≥2 of 5 agree) | V15.1 §15.2 Item 7 spec | **SUPERSEDED by ADR-007** | Never built. Rendered moot by signal-source change: momentum is now a confirmation modifier, not a vote member with equal weight. Equal weighting would dilute the strongest signals. |

### New post-pivot momentum assumptions (LIVE)

| Assumption (post ADR-007) | How set | Status | Evidence / annotation |
|---|---|---|---|
| MOM_YES gate (momentum aligned with pattern direction) lifts WR materially | V18F Exp 20 evidence | **VALIDATED** | Exp 20: ALIGNED 60.9%, OPPOSED 38.3%, lift +22.6pp. Wired into TIER1/TIER2 criteria (V19 §8.3). |
| PO3 session bias (BSL/SSL liquidity sweep on 1H window) classifies session as PO3_BULLISH / PO3_BEARISH / NEUTRAL | Research Session 11 (ENH-75) | **VALIDATED — LIVE** | `detect_po3_session_bias.py` runs Mon-Fri 10:05 IST. `po3_session_state` table populated. Used in BEAR_OB MIDDAY (ENH-76) and BULL_OB AFTERNOON SENSEX (ENH-77) gates. |

---

## D.5 Volatility assumptions

V15.1 Appendix D §D.3 originally. VIX gate is SUPERSEDED; most other volatility assumptions are intact.

| Assumption (V15.1) | How set | Status | Evidence / annotation |
|---|---|---|---|
| VIX HIGH threshold: `> 20`. Used to gate `trade_allowed = false` at HIGH VIX | NSE convention; not validated for MERDIAN signal quality | **SUPERSEDED by ADR-007 SRB-04** | V18F evidence: HIGH_IV regimes show MORE edge on OBs, not less. Gate counterproductive. Removed. India VIX context retained as informational metadata in `volatility_snapshots`; does not gate any signal. |
| ATM IV = (atm_call_iv + atm_put_iv) / 2. Simple average | Simplicity | **LIVE** | Not specifically challenged. Could investigate whether put_IV or call_IV individually has higher predictive power for the direction being traded. Not blocking. |
| VIX fallback: last known value with `STALE_VIX` caution. Provisional — not confirmed in live code | Provisional spec V15.1 §8.4 | **LIVE — UNRESOLVED** | Status not confirmed against live `fetch_india_vix.py`. Could be a silent regime misclassification risk. Worth a 0.5-session audit + harden as a named feature. File as TD if not already. |
| VIX percentile context model: 5 bands (VERY_LOW / LOW / NORMAL / ELEVATED / EXTREME at 0–20 / 20–40 / 40–60 / 60–80 / 80–100 percentile) | V16 §10.2 | **LIVE — partially used** | `vix_percentile_regime` field populated in `volatility_snapshots` per V18D. Behavioral interpretation of each band is not currently wired into signal logic; it's diagnostic context only. |

### New post-pivot volatility assumptions (LIVE)

| Assumption (post ADR-007) | How set | Status | Evidence / annotation |
|---|---|---|---|
| `basis_pct` > 0.5% adds caution flag (not a block) | V18G ENH-07 | **LIVE** | Wired in `build_trade_signal_local.py`. Does not affect `trade_allowed`. Diagnostic only. |
| HIGH_IV regimes have MORE edge on ICT OB patterns | V18F Exp 5 + ENH-35 sub-analysis | **VALIDATED** | Direct empirical reversal of the V15.1 VIX > 20 gate. Foundation for SRB-04. |

---

## D.6 ICT-era new assumptions (no V15.1 antecedent)

These assumptions did not exist in V15.1 because ICT pattern detection was not yet the trigger. Recorded here so they have a home for future validation / refutation.

| Assumption | How set | Status | Evidence / annotation |
|---|---|---|---|
| ICT pattern detection is meaningful only on 5m bars; 1m bars are too noisy for structural patterns | V18H lesson (sweep detection 0 events on 1m vs 52 on 5m) | **VALIDATED** | Codified as CLAUDE.md Rule 6: "5m bars for ICT pattern detection, never 1m. 1m is for precise entry timing only after HTF confirms." |
| T+30m exit beats both ICT structure-break exit and longer holds | V18F Exp 8/14b/15 multiple confirmations | **VALIDATED** | Exp 15: T+30m 63.8% WR +₹10.43L vs ICT structure break 36.9% WR +₹7.37L. T+30m wins by 41% on total P&L. CLAUDE.md settled-decision. |
| Kelly Half (Strategy C) is the safe live starting point; Kelly Full (Strategy D) is the upgrade after 3–6 months of live data | V18G §10.1 + V18F Exp 16 | **LIVE — proposed** | Current Phase 4A operates with Strategy C. Live data accumulating to validate before upgrading. |
| Capital ceiling: ₹50L hard cap, ₹25L sizing freeze, ₹10K floor | V18F + V18G §10.1 (floor lowered from ₹2L → ₹10K) | **VALIDATED — LIVE** | CLAUDE.md non-negotiable rule 8. Liquidity-driven for NIFTY/SENSEX options. Do not re-litigate. |
| 1H zones (MEDIUM context) add edge over LOW context on ICT patterns | V18F Exp 10c/15 cohort | **CONTESTED — TD-059** | Original Exp 10c/15 evidence supported. Session 16 evidence on N=231 contradicts (LOW > HIGH on OB). Resolution: ENH-89 (annotation only / inversion / shadow A/B test). |
| BEAR_OB AFTERNOON (13:00–14:30 IST) is a hard SKIP | V18F Signal Rule Book v1.1 evidence | **VALIDATED** | 17% WR, -24.7% expectancy. Hard skip. CLAUDE.md settled-decision. |
| `signal_regret_log` should remain populated as ongoing monitoring (not as threshold-change gate, since that role retired with ADR-007) | V18A precedent + ADR-007 evidence | **LIVE — ongoing** | Keeps the audit trail. The V15.1-spec'd role as threshold-change gate is retired (the gate purpose was satisfied at V18F). The diagnostic role continues. |
| Phase 4 promotion gate waiver (10-session shadow → 9-session + 1-year backtest) is acceptable when stronger evidence exists | V18G §10.1 decision | **LIVE — precedent** | One-time waiver. Future shadow-gate waivers require equivalent strength of alternative evidence. Worth ADR if pattern recurs. |

---

## D.7 Validation queue (next experiments to fund)

Open assumptions that would benefit from formal validation, prioritised:

| Priority | Assumption | Suggested experiment |
|---|---|---|
| HIGH | ENH-37 MTF hierarchy correctness (TD-059) | Shadow A/B test with `confidence_score_v1` (current hierarchy) and `_v2` (inverted). Run 4–8 weeks. Compare WR. |
| HIGH | Breadth contribution to confidence (ENH-43 disposition) | Already have Exp 20 evidence (1.0pp = noise). Action: remove breadth scoring block. 0.5 session of work. |
| MEDIUM | VIX fallback STALE_VIX behavior | Audit live `fetch_india_vix.py` against V15.1 §8.4 spec. Harden as named feature. 0.5 session. |
| MEDIUM | VWAP slope window | Read window from `build_momentum_features_local.py`; document; assess fixed vs adaptive. 0.5 session. |
| MEDIUM | Multi-expiry GEX on expiry week | Compare single-expiry vs multi-expiry GEX-driven signals on expiry-week cohort. 1–2 sessions. |
| LOW | Equal-weighted breadth vs cap-weighted | Already addressed by WCB; full revalidation low priority unless ENH-43 keeps breadth in confidence layer. |
| LOW | Intraday DMA refresh impact | Compute intraday DMA for 30 sessions, compare breadth_score deltas. Expected small-impact result. |

---

## Update log

This register itself follows Doc Protocol v4 Rule 9.5: superseded rows are annotated, never deleted. Significant register events are recorded here.

| Date | Session | Event |
|---|---|---|
| 2026-05-09 | Session 23 | Created. V15.1 Appendix D content promoted. Refreshed for ICT-era post ADR-007. Status assignments grounded in V18F evidence + V19 SRB rules + Session 16/17 findings. |

---

*MERDIAN Assumption Register — established Session 23, 2026-05-09. Living document. Update inline as experimental evidence resolves rows; superseded rows are annotated with the superseding ADR/Exp, never deleted.*
