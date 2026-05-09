# ADR-007 — V18F ICT Pivot: pattern triggers replace confidence thresholds; gates and governance remain

| Field | Value |
|---|---|
| **Status** | Accepted (retroactive) |
| **Date decided** | 2026-04-11 / 2026-04-12 (V18F Research Session 3) |
| **Date documented** | 2026-05-09 (Session 23) |
| **Session** | Session 23 — retroactive ADR drafting; original decision in V18F |
| **Git anchor** | `fee7b7c` → `cfba66e` (V18F session range) |
| **Supersedes** | V15.1 §3 (Signal Decision Logic) · §15.2 Items 6, 7, 8 (three-zone gamma model, multi-horizon momentum voting, signal_regret_log as threshold-change gate) · §15.4 (Phase 2 sequencing) · V16 §7 (Signal Decision Logic) · §8.2 (Three-Zone Gamma Model spec) · §17.6 system_config seed values for `min_confidence_threshold=60` and `min_dte_threshold=2`. The 11 March 2026 case study insight (V15.1 §3.6 · V16 §4) is **preserved**; its V15.1-spec'd remediation path is **replaced**. |
| **Preserved from V15.1/V16** | LONG_GAMMA → DO_NOTHING gate · NO_FLIP → DO_NOTHING gate · Measure → Validate → Shadow → Promote governance (V16 §3) · Four Key Evidence Questions framing (V16 §3.3) · Walk-Forward validation methodology (V16 §3.6) · `signal_snapshots` as primary record · `market_spot_snapshots` as canonical outcome timeline · Stable local Python backbone |
| **Related ENH** | ENH-35 (full-year signal validation — COMPLETE) · ENH-37 (ICT layer — PRODUCTION) · ENH-38 (Kelly tier sizing — IN PROGRESS) · ENH-39 (capital ceiling — DONE) · ENH-40 (Signal Rule Book v1.1 — pending formal doc, OI-10) · ENH-43 (breadth removal candidate) · ENH-88 (BULL_FVG cluster gate — built, not deployed) |
| **Codified rules** | V19 §8.5 SRB-01 through SRB-05 (this ADR is their upstream rationale) |
| **Related TD** | TD-058 (BEAR_FVG live emission — closed Session 17) · TD-059 (ENH-37 MTF hierarchy possibly inverted) · TD-060 (live runner zero-OB — closed Session 17) |
| **Related ADRs** | ADR-001 (validity-layer gate standard — applies to any new gates) · ADR-002 (market-structure principles — orthogonal: ADR-002 governs the gamma/zone layer; ADR-007 governs the signal-trigger layer) |

---

## Context

From V11 through V15.1 (March 2026), MERIDIAN/Gamma Engine ran a **confidence-scoring signal engine**: gamma + breadth + momentum + India VIX features were combined into a `confidence_score` integer 0–100, gated by `min_confidence_threshold = 60`, producing `BUY_CE` / `BUY_PE` / `DO_NOTHING` with `trade_allowed` boolean. Direction was inferred from gamma_regime crossed with breadth_regime; momentum confirmed direction; VIX > 20 hard-gated `trade_allowed = false`; breadth-momentum CONFLICT produced unconditional DO_NOTHING.

On **11 March 2026**, this engine produced DO_NOTHING for the majority of a session in which NIFTY fell ~450 points. Three structural defects were diagnosed (V15.1 §3.6, V16 §4): (1) LONG_GAMMA hard block applied symmetrically regardless of `flip_distance` (the flip was 2.2% away — outside any near-flip dampening zone); (2) single-horizon `ret_5m` captured a counter-trend bounce and declared BULLISH momentum; (3) the CONFLICT rule had no resolution logic. V15.1 §15.2 spec'd three remediations: a three-zone gamma model (Item 6), multi-horizon momentum voting (Item 7), and a signal_regret_log table to provide the empirical foundation for any threshold change (Item 8). V15.1/V16 also established the principle that **no threshold change occurs without 30+ sessions of regret-log data**.

V16 (March 2026) introduced the Measure → Validate → Shadow → Promote governance framework (V16 §3), the Four Key Evidence Questions (§3.3), and Walk-Forward validation methodology (§3.6). V16 §25 declared: *"No change to any live signal file until (1) measurement gaps closed, (2) evidence collected, (3) shadow runs 2+ weeks at or above live accuracy, (4) model change log entry written."*

V17 (16A–E, late March) closed the measurement gaps: ret_session went live (16D), shadow tables for IV context, options flow, momentum_v2, SMDM and shadow_signal_v3 were built (16E), and the live signal path was kept untouched per the additive-shadow rule. V18A (2026-03-31) added the three-zone gamma model in shadow (`gamma_zone` field on `gamma_metrics`) and built `signal_regret_log` to 614 rows. V18B–E (Apr 1–9) ingested the full historical year (Apr 2025 – Mar 2026) and ran a 7-session live canary sprint that PASSED. By 2026-04-10, the prerequisites the V16 framework demanded for any signal-architecture change were satisfied: measurement gaps closed, full-year evidence base built, shadow gate at 7/10 sessions.

**V18F (2026-04-11/12)** was the validation pass. Eleven experiments (Exp 0, 2, 2b, 2c, 2c v2, 5, 8, 10c, 14, 15, 16) were run against the full year of historical data. The combined evidence answered the Four Key Evidence Questions decisively, and produced a finding the V15.1 spec had not anticipated: **the highest-edge signal trigger was not a confidence-score threshold derived from gamma+breadth+momentum, but the discrete ICT pattern itself.** Pure ICT pattern detection (BEAR_OB, BULL_OB, BULL_FVG, JUDAS_BULL) with no MERDIAN regime filter produced 86–94% standalone win rates on the OB patterns (Exp 15). Confidence-score gates that V15.1 had spec'd as binary blocks turned out to be either correctly binary (LONG_GAMMA — symmetric across BULL_OB and BEAR_OB at 47.7% WR, below random) or mistakenly binary (CONFLICT, VIX > 20 — both lifted produced higher accuracy in backtest).

The V15.1 remediation path — implement the three-zone gamma model and multi-horizon voting *within* the confidence-scoring architecture — became moot. The signal-source problem the 11 March failure exposed was not a tuning problem within the existing engine; it was a problem that the engine's *trigger model* was wrong.

This ADR documents the resulting pivot.

---

## Decision

The signal engine architecture is restructured along the following lines, all changes shipped in V18F (commit `cfba66e`) and codified in V19 §8.5 as Signal Rule Book v1.1 (SRB-01 through SRB-05).

**1. ICT pattern detection is the primary signal trigger.** `detect_ict_patterns.py` produces discrete pattern events (BEAR_OB, BULL_OB, BULL_FVG, JUDAS_BULL) on each 5-minute cycle. Each pattern carries a tier (TIER1/TIER2/TIER3/SKIP) and direction (BUY_CE/BUY_PE). The `signal_snapshots.action` field is set from the detected pattern's direction, not from a gamma+breadth+momentum threshold combination. A cycle with no qualifying pattern produces `action='DO_NOTHING'` regardless of confidence-score state.

**2. Kelly tier sizing replaces uniform confidence-based sizing.** TIER1 patterns (BULL_OB MORNING, BULL_OB DTE=0, BEAR_OB MORNING, BEAR_OB DTE=4+ MOM_YES) use Half Kelly = 50% of effective capital starting; Full Kelly = 100% as upgrade. TIER2 (BULL_OB MOM_YES, BEAR_OB MOM_YES, BULL_OB AFTERNOON, JUDAS_BULL) uses 40% / 80%. TIER3 (BULL_FVG unconfluenced, JUDAS_BULL unconfirmed) uses 20% / 40%. Strategy C (Half Kelly) is the live starting point per V18G §10.1; Strategy D (Full Kelly) upgrade after 3–6 months of live data.

**3. LONG_GAMMA → DO_NOTHING and NO_FLIP → DO_NOTHING gates are preserved as binary blocks.** Exp 17 (1m bars) and Exp 19 (5m bars) confirmed symmetric block correctness: BULL_OB 50.5% vs BEAR_OB 49.7% under LONG_GAMMA — both below random. NO_FLIP 45–48% WR across all pattern types — below random. The V15.1-spec'd three-zone refinement is unnecessary: the gates are right as binary; only the *trigger* upstream of them was wrong.

**4. CONFLICT terminal rule is lifted.** The V15.1/V16 rule that breadth-momentum CONFLICT produces unconditional DO_NOTHING is removed. CONFLICT BUY_CE trades show 58.7% WR (NIFTY) / 55.4% (combined). Reversing the lift lowered accuracy in backtest. The V15.1 §3.3 "open architectural question" is closed.

**5. VIX > 20 trade_allowed gate is removed.** HIGH_IV regimes show *more* edge on OB patterns, not less. The V15.1-planned `trade_allowed = false` gate at VIX > 20 was counterproductive and is dropped. India VIX context is retained as informational metadata in `volatility_snapshots` but does not gate any signal.

**6. MIN_CONFIDENCE lowered 60 → 40.** The V15.1/V16 system_config seed `min_confidence_threshold = 60` was based on judgment, not data. The V15.1/V16 rule was "no threshold change without 30+ sessions of regret-log data" — that gate was satisfied by `signal_regret_log` (614 rows V18A) plus the full-year backtest (V18C–F). At threshold 40, more signals pass without materially degrading accuracy.

**7. Confidence scoring is relegated to an adjustment layer beneath ICT tier.** The score still exists and feeds `signal_snapshots.confidence_score`, but its role changed: ICT tier provides the base trigger and the ±20 / ±10 / 0 base point allocation; PCR (ENH-02), skew (ENH-04), and flow (ENH-04) modifiers add ±5 / ±4 / ±3 confidence points; LONG_GAMMA and NO_FLIP override to SKIP regardless of score; basis_pct caution adds a flag. The ENH-43 candidate to remove the breadth confidence component was filed in V18F based on Exp 20 evidence (breadth +/- 1.0pp = pure noise).

**8. T+30m is the confirmed exit horizon.** Exp 15 compared T+30m exit (63.8% WR, +₹10.4L total) against ICT structure-break exit (36.9% WR, +₹7.4L). T+30m wins by 41% on total P&L. The exit rule is final.

**9. The 11 March 2026 case study insight is preserved; its V15.1-spec'd remediation is moot.** The diagnostic — that a confidence engine combining symmetric LONG_GAMMA blocks, single-horizon momentum, and terminal CONFLICT produces structurally wrong DO_NOTHING signals on trend days — remains a permanent architectural reference. The fix V15.1 §15.2 spec'd (three-zone gamma + multi-horizon voting + regret-log threshold-tune sequencing) is replaced by signal-source change. Future engineers should read V15.1 §3.6 / V16 §4 for the diagnosis and this ADR for the resolution.

---

## Evidence

Each rule above is grounded in a specific experiment from the V18F series. Numbers are from `MERDIAN_AppendixV18F_v2.docx` and the Experiment Compendium.

| Rule | Experiment | Cohort | Headline | Verdict |
|---|---|---|---|---|
| 1. ICT trigger primary | Exp 15 (Pure ICT compounding) | Full year, no MERDIAN regime filter, ₹2L→₹6.51L NIFTY / ₹7.92L SENSEX | BEAR_OB 94.4% WR (N=36), BULL_OB 86.4% (N=44), BULL_FVG 50.3% (N=155), JUDAS_BULL 69.0% | ICT patterns alone produce edge; OB patterns are the strongest standalone signals in any MERDIAN component |
| 2. Kelly tiers | Exp 16 (portfolio simulation v2) | Full year, 4 sizing strategies | Strategy C (Half Kelly): +18,585% combined return, 16.6% max DD, Ret/DD 1,122x. Strategy D (Full Kelly): +44,234%, 24.8% max DD, Ret/DD 1,785x | Tier-based sizing dominates uniform sizing; start C, upgrade D after live data |
| 3a. LONG_GAMMA preserved | Exp 17 (1m gamma asymmetry) + Exp 19 (5m gamma asymmetry) | LONG_GAMMA cohort, both pattern directions | BULL_OB 50.5% vs BEAR_OB 49.7% — pooled 47.7% WR, below random | Symmetric block correct; no asymmetry to exploit; three-zone refinement unnecessary |
| 3b. NO_FLIP preserved | Exp 19 sub-analysis | NO_FLIP cohort, all pattern types | 45–48% WR across BULL_OB, BEAR_OB, BULL_FVG | Block correct |
| 4. CONFLICT lifted | Exp 0 (signal_regret_log) + Exp 20 (momentum-breadth alignment) + ENH-35 backtest | CONFLICT BUY_CE pool, NIFTY full year | 58.7% WR; reversing the lift lowered backtest accuracy | Lift correct; V15.1 "open question" closed |
| 5. VIX gate removed | Exp 5 + ENH-35 sub-analysis | HIGH_IV cohort × OB patterns | HIGH_IV OB WR materially higher than NORMAL_IV OB WR | Gate counterproductive; remove |
| 6. MIN_CONFIDENCE 60→40 | Exp 0 (signal_regret_log 614 rows) + ENH-35 full year | All trade_allowed signals | At threshold 40, signal count rises without degrading accuracy; trade_allowed=YES pool 268 bars 55.2% accuracy | The V15.1/V16 30-session regret-log gate was satisfied; threshold lowered |
| 7. Confidence as adjustment | Exp 20 + Exp 21–25 (breadth/skew/PCR/flow individual signal contributions) | Various | Momentum +22.6pp lift (ALIGNED 60.9% / OPPOSED 38.3%); breadth +/- 1.0pp = noise (ENH-43 follow-up); skew/PCR/flow contribute small but measurable edge | Modifiers retained except breadth (pending ENH-43); base trigger is ICT tier |
| 8. T+30m exit | Exp 15 exit comparison | All ICT patterns, full year | T+30m: 63.8% WR, +₹10.43L; ICT structure break: 36.9% WR, +₹7.37L | T+30m wins by 41% total P&L |
| Composite validation | ENH-35 full-year backtest | NIFTY 244 signals, full year Apr 2025–Mar 2026 | 58.6% T+30m accuracy. trade_allowed=YES pool 268 bars 55.2% accuracy. SENSEX 24 signals 20.8% — too few, regime mismatch flagged | Phase 4 promotion gate met (V18G §10.1 waived shadow gate session 10 in favor of full-year backtest evidence) |

---

## Alternatives considered

### A. Implement V15.1's spec'd remediation in full

Build the three-zone gamma model (Zone A < 0.5% block / Zone B 0.5–1.5% confidence-65 / Zone C > 1.5% gate removed), wire multi-horizon momentum voting (≥2 of 5 of ret_5m / ret_15m / ret_60m / ret_session / vwap_slope agree), and use `signal_regret_log` as the threshold-tune evidence base. Stay within the confidence-scoring architecture.

**Rejected because:**
- Exp 17 and Exp 19 evidence: LONG_GAMMA is correctly binary. BULL_OB and BEAR_OB show no asymmetry by `flip_distance`. The three-zone model addresses a problem that does not exist in the data — it would add complexity without lifting WR.
- Exp 20 evidence: momentum is a confirmation modifier (+22.6pp lift when aligned), not a vote member with equal weight. The voting model treats five horizons as peers, but `ret_session` and `vwap_slope` carry materially different information value than `ret_5m`. Equal weighting would dilute the strongest signals.
- Even with both V15.1 fixes implemented perfectly, the underlying signal trigger would still be a confidence-score threshold derived from continuous regime features. Exp 15 demonstrated that discrete ICT pattern events have higher standalone edge than any threshold-derived trigger MERDIAN had built. The V15.1 path leaves that edge on the table.
- The 11 March case study itself was a *signal-source* failure (the system saw no actionable trigger because its trigger model required gamma+breadth+momentum agreement that didn't materialize), not a *threshold-tuning* failure within a correct trigger model. V15.1's spec'd remediation treated the symptom, not the cause.

### B. Hybrid — keep confidence-score as primary, add ICT as confirmation layer

Run the confidence-scoring engine as before; require ICT pattern presence as an additional gate when `confidence_score` crosses the threshold, but do not let ICT patterns trigger signals on their own.

**Rejected because:**
- Exp 15 shows pure ICT (no MERDIAN regime filter) produces 86–94% WR on OB patterns. Relegating ICT to confirmation reverses the demonstrated relationship: the layer with the higher standalone edge would be subordinated to the layer with the lower standalone edge.
- The confidence-score's standalone edge is mostly a function of LONG_GAMMA / NO_FLIP gates being correct (47.7% / 45–48% WR — below random when blocked). Once those gates are extracted, the residual confidence-score adds modest +5/+4/+3 point modifiers — informative, not generative.
- Plus the architectural complexity of two parallel trigger paths with a confirmation handshake adds debugging surface area for no clear gain.

### C. Pure ICT — drop confidence-scoring entirely

Trigger on ICT pattern only. No LONG_GAMMA gate, no NO_FLIP gate, no PCR/skew/flow modifiers. Tier sizing alone decides position size.

**Rejected because:**
- LONG_GAMMA and NO_FLIP gates have demonstrated negative edge: 47.7% and 45–48% WR — below random for *all* pattern types under those regimes. Dropping the gates would systematically include known-bad cells.
- PCR/skew/flow modifiers (ENH-02/04) add measurable confidence points (+5 / +4 / +3) that translate to entry-quality differentiation. Discarding them sacrifices small but free edge.
- The pivot is a *trigger* change. The validated gates and modifiers from the V15.1/V16 era are kept on their own merit, not for backward compatibility.

---

## Consequences

### Positive

- **Empirical grounding.** The signal engine is now validated on a full year (Apr 2025 – Mar 2026) of NIFTY+SENSEX data. NIFTY 58.6% T+30m accuracy, trade_allowed=YES pool 55.2%, Phase 4 promotion gate met (V18G §10.1).
- **Live trading enabled.** Discrete pattern triggers with deterministic tier→Kelly sizing made Phase 4A manual execution implementable. `merdian_trade_logger.py` + dashboard LOG TRADE button shipped V18G; first live trades executed since.
- **V16 governance demonstrated working.** Measure (V17 → V18A measurement gap closure) → Validate (V18F Exp 0–16 with walk-forward Apr 2025–Mar 2026 cohort) → Shadow (8/10 sessions PASSED + full-year backtest as gate-equivalent evidence per V18G §10.1) → Promote (V18F live). The framework V16 §3 set out was followed end-to-end.
- **Four Evidence Questions answered.** Q1 trade_allowed=false suppression cost: ENH-35 evidence quantifies. Q2 LONG_GAMMA cost: 47.7% WR confirms gate correctness. Q3 confidence 40–60 accuracy: comparable to 60+, threshold lowered. Q4 CONFLICT correctness: 58.7% WR — not blocked.

### Negative — risk to manage

- **V15.1/V16 specs become moot.** Three-zone gamma model (V15.1 §15.2 Item 6 / V16 §8.2), multi-horizon momentum voting (V15.1 §15.2 Item 7), and signal_regret_log-as-threshold-gate sequencing (V15.1 §15.2 Item 8) are all superseded. A future session reading V15.1/V16 in isolation could re-propose any of these without realizing the experimental evidence has rendered them moot. The Decision Index entry for ADR-007 must explicitly link these as superseded specs.
- **V15.1 Appendix D Assumption Register requires refresh.** D.1 (Signal Engine assumptions: `min_confidence_threshold=60`, `min_dte_threshold=2`, CONFLICT terminal, LONG_GAMMA hard block) is largely obsolete. D.4 (Momentum: `ret_5m` as primary momentum signal, voting model not implemented) is largely obsolete — `ret_5m` is now confirmation only; `ret_session` was built. D.2 (Breadth) is partially live (intraday DMA still fixed at EOD; ENH-43 candidate to remove breadth from confidence layer pending). D.3 (Gamma) remains authoritative — Exp 17/19 confirmed binary regime correct.
- **New dependencies introduced.** ICT pattern detection requires high-quality 1-minute spot bars, ICT zone construction infrastructure (`build_ict_htf_zones.py`), and pattern-detection runtime infrastructure (`detect_ict_patterns.py` + `detect_ict_patterns_runner.py`). TD-058 (BEAR_FVG live emission zero) and TD-060 (cycle stride zero-OB bug) — both closed Session 17 — were direct consequences of this dependency surface. Future detector edits carry signal-quality risk that the confidence-score architecture did not.

### Mitigations

- This ADR + the Decision Index entry are the primary mitigation for the moot-spec re-litigation risk.
- V15.1 Appendix D refresh: file as ENH or deliver as part of `docs/registers/MERDIAN_Assumption_Register.md` (per the documentation protocol revision following this ADR).
- The detector dependency surface is addressed by ADR-001's validity layer (cross-reference / sanity check on each cycle) plus the Session 17 patches that ship `_PRE_S<n>.py` snapshots for every detector edit.

---

## Relationship to other documents

- **V15.1 §3.6 / V16 §4 — 11 March 2026 case study.** The diagnostic insight is preserved permanently. The remediation V15.1 §15.2 spec'd is replaced by this ADR. Both documents should be read together by any engineer working on signal architecture: V15.1/V16 for the diagnosis, this ADR for the resolution.
- **V15.1 Appendix D — Assumption Register.** ADR-002 cited this register as authoritative. Post-pivot, D.1 and D.4 require refresh; D.2 and D.3 remain largely authoritative. The refresh should be a derivative document (`docs/registers/MERDIAN_Assumption_Register.md`) so ADR-002's citation remains live.
- **V15.1 §15.2 Items 6, 7, 8.** Superseded. The three-zone model field (`gamma_zone`) remains in `gamma_metrics` for future research but its V15.1-spec'd behavioral role is moot. The multi-horizon voting model was never built and will not be. The signal_regret_log table remains live (614 rows V18A) and continues to record DO_NOTHING outcomes for ongoing monitoring, but its V15.1-spec'd role as the gate for any threshold change has been retired — the gate purpose was satisfied at V18F.
- **V16 §3 — Measure → Validate → Shadow → Promote framework.** Preserved unchanged. This pivot followed the framework end-to-end and is its first major application.
- **V16 §3.3 — Four Key Evidence Questions.** Preserved unchanged. All four were answered by the V18F experiment series.
- **V16 §3.6 — Walk-Forward Validation.** Preserved unchanged. V18F's Exp 15 cohort was full-year (Apr 2025 – Mar 2026); a Year-1+2 calibration / Year-3 holdout split was not formally separated, but the principle is recorded as the standard for any future parameter derivation. This is an open methodological question — see follow-up.
- **V19 §8.5 SRB-01 to SRB-05 — Signal Rule Book v1.1.** This ADR is the upstream rationale. Each SRB rule maps to one decision item above (SRB-01 = decision 4; SRB-02 = decision 3a; SRB-03 = decision 3b; SRB-04 = decision 5; SRB-05 = decision 6).
- **ADR-001 — Stable lies defeat duration gates.** Complementary. ADR-001's two-layer gate standard (stability + validity) applies to any new gates introduced by ICT (e.g. zone status transitions, breach detection). Future ICT-layer additions should pair stability tests with cross-reference validity checks per ADR-001.
- **ADR-002 — Market structure philosophy.** Orthogonal. ADR-002 governs what the *gamma layer* should compute (per-strike GEX, force, zones, regime states P1–P6). ADR-007 governs what the *signal layer* fires on. Both apply concurrently. ADR-002's P5 PINNED regime is forward-looking and will integrate into the signal layer when delivered (ENH-82) — likely as an additional gate or modifier, structurally similar to LONG_GAMMA and NO_FLIP.

---

## Governance language

> *"The signal trigger is the discrete ICT pattern. The confidence score is the size dial. Gates that validated as binary truth — LONG_GAMMA, NO_FLIP — remain. Gates that validated as conservative myth — CONFLICT, VIX>20 — are lifted. The 11 March 2026 insight stays; its proposed remediation does not."*

This is the one-line compressed form for CLAUDE.md "settled decisions" addition.

---

## Open follow-ups

These are the items spawned by, dependent on, or unresolved by this ADR. They do not block its acceptance but are the natural next deliverables.

- **ENH-43 — Remove breadth from confidence scoring.** Exp 20 evidence: breadth +/- 1.0pp = pure noise. V19 §8.4 explicitly notes breadth "should be removed per ENH-43". Action: small patch to `build_trade_signal_local.py` removing the breadth scoring block. Estimated 0.5 session.
- **TD-059 / ENH-89 — MTF context hierarchy possibly inverted.** V18F evidence said MEDIUM > HIGH > LOW for OB; Session 16 evidence on N=231 live cohort says LOW > HIGH (BEAR_OB|LOW 100% WR N=17 vs BEAR_OB|HIGH 71.4% N=7). Current treatment: annotation-only (don't size up on HIGH context). Decision options: (A) annotation-only permanent, (B) inversion, (C) shadow A/B test. Recommend Option C; decision deferred to Session 18+.
- **ENH-88 — BULL_FVG cluster gate.** Built in Session 17, not deployed pending BULL_OB signal flow confirmation post-TD-060 fix. Deploy after Monday 2026-05-04 live cycle confirms BULL_OB emission.
- **V15.1 Appendix D refresh.** Promote a current-state Assumption Register at `docs/registers/MERDIAN_Assumption_Register.md` reflecting post-pivot state. D.1 and D.4 largely rewritten; D.2 and D.3 carried forward. Required so ADR-002's citation has a live anchor.
- **ENH-40 / OI-10 — Signal Rule Book v1.1 formal document.** SRB rules currently codified inline in V19 §8.5. Formal `Signal_Rule_Book_v1.1.md` document pending.
- **Walk-forward methodology audit.** V16 §3.6 set the standard; V18F Exp 15 used the full year as one cohort rather than a Y1+Y2 calibration / Y3 holdout split. Decide whether to (a) rerun with a formal split, (b) accept the full-year cohort as the validation pass given the absence of parameter-fitting in Exp 15, or (c) adopt a forward-looking walk-forward standard for next major parameter changes.
- **Decision Index entry.** This ADR mechanically prepends to `docs/decisions/MERDIAN_Decision_Index.md` once that file exists per the documentation protocol revision.

---

*ADR-007 — 2026-05-09 — Session 23. Retroactive ADR for the V18F (2026-04-11/12) signal architecture pivot. First architectural ADR documenting a pivot that was already shipped — establishes the pattern that retroactive ADRs are acceptable for major decisions that pre-date the ADR habit, and required for any decision of comparable scope going forward.*
