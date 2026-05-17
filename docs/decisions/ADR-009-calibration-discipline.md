# ADR-009 — Calibration discipline: graduated-strictness holdout (Phase 1) → rolling walk-forward (Phase 2 at Y2 close)

| Field | Value |
|---|---|
| **Status** | Accepted (principle Session 25; S29 case-study addition + Phase 0b FAIL sub-rule; S30 case-study addition + cohort-prior gate hazard sub-rule); Phase 2 cutover deferred to Y2 close (~April 2027) |
| **Date** | 2026-05-10 (Phase α Q4 answered Session 25; ADR drafted Session 25). **Updated 2026-05-16 (Session 29 — S29 first case study added: ENH-97 RR-regime gate FAIL on Phase 0b; new sub-rule "Phase 0b FAIL = abandon dimension as gate, not retry with parameter tweaks"; cross-link Assumption Register §D.12.1 + §D.12.2 + §D.12.3).** **Updated 2026-05-17 (Session 30 — S30 second case study added: cohort-translation D.9.3 caught itself; live-cohort pure-ICT WR 58.3% mean +6.96% median +3.38% N=211 8wk pooled +1469pp unverdicted by S29 Phase 0b on hist_pattern_signals cohort; new sub-rule "cohort-prior gate hazard" codified into §Phase 1; cross-link Assumption Register §D.13.1 + §D.13.3).** |
| **Decision-makers** | Navin (operator, deferred to architect), Claude (architect) |
| **Supersedes** | None — codifies what was previously implicit (Exp 15 era single-cohort derivation) |
| **Related** | MERDIAN_Assumption_Register.md §D.7 (Validation queue) and §D.8 (Methodology assumptions — working draft of this ADR) **+ §D.12 (S29 Phase 0b falsification realization + first case study cross-link)**, Exp 15 framework (foundational PO3 + ICT calibration), ADR-007 (V18F ICT pivot — parameters that may be subject to this discipline retroactively), ADR-002 v2 §P7 (ENH-97 RR-regime gate falsification commitment — realized S29 as first case study under this ADR), CLAUDE.md operational finding (Session 22 architecture-decisions-need-ADRs codification). |

---

## Context

MERDIAN's foundational signal parameters were derived via **Exp 15 era single-cohort calibration** — the full available year of data (~Apr 2025 → Apr 2026) was used to derive parameter thresholds (gap-size bands, sweep depth bands, MTF context multipliers, tier WR thresholds, BEAR_OB AFTERNOON skip cutoff, ENH-77 BULL_OB AFTERNOON SENSEX gate, and others). The thresholds were chosen by examining the entire dataset to find the cuts that maximized in-sample win rate.

**The canonical methodological hazard in quantitative trading research is parameter overfitting from in-sample-only calibration.** When parameters are derived by looking at the full dataset, they memorize that dataset's noise alongside its signal. Out-of-sample performance is structurally lower than in-sample because the noise component doesn't generalize. The size of that degradation is unknowable without a holdout split.

MERDIAN currently has roughly Apr-2025 → Apr-2026 of usable data with consistent capture quality. Most experiment results on file derive from this single-cohort analysis. Assumption Register §D.7 has long flagged this as an open methodological commitment.

**Phase α Q4 (Session 22 → Session 25):** "Should future parameter derivation enforce a calibration / holdout split? (a) strict mandatory holdout, (b) suggested-not-enforced, (c) immediate rolling walk-forward, (d) status quo single-cohort." Operator deferred to architect recommendation in Session 25.

**Architect-recommended answer:** **graduated-strictness holdout** spanning Phase 1 (now → Y2 close) and Phase 2 (Y2 close onward). The graduation acknowledges the **N reality** at MERDIAN's current data scale: with ~250 trading days in Y1, half the experiment cohorts have N<60 even at the full cohort, and a uniform 67/33 split sometimes leaves the holdout below the threshold for a reliable WR estimate. Strict (a) ships fewer parameters; (d) ships parameters that don't generalize; (c) is academic-correct but operationally too heavy until ~2 more years of data accumulate.

The graduation handles all three trade-offs explicitly: discipline scales with cohort size, parameters that can't support formal split get an explicit "low-N tag" rather than silent waiver, and Phase 2 commits to walk-forward when the data scale supports it.

§D.8 of the Assumption Register has the working draft of this rule (5 rows: D.8.1 single-cohort REJECTED, D.8.2 graduated holdout LIVE, D.8.3 prospective parity check on existing params LIVE, D.8.4 Phase 2 walk-forward DEFERRED to Y2, D.8.5 silent waiver explicitly REJECTED). This ADR codifies and links.

---

## Decision

Calibration discipline operates in **two phases**, with a graduated-strictness holdout rule in Phase 1 and a migration to rolling walk-forward in Phase 2.

### Phase 1 — Graduated-strictness holdout (now → ~April 2027 / Y2 close)

For any **new parameter change**, the cohort size N (in the largest viable derivation cohort) determines the split discipline:

| Cohort size N | Split | Tolerance | Disposition if holdout WR outside tolerance |
|---|---|---|---|
| **N ≥ 60** | 67% calibration / 33% holdout | Holdout WR within **10pp** of calibration WR | Parameter filed but **not shipped** to production; document the gap; investigate before retry |
| **30 ≤ N < 60** | 75% calibration / 25% holdout | Holdout WR within **15pp** of calibration WR | Parameter filed but **not shipped**; document the gap |
| **N < 30** | **No formal split required** | "low-N calibration-only" tag in `merdian_reference.json` | Parameter ships with explicit tag; re-validate formally when N reaches 30 via prospective accumulation |

For **existing Exp 15-era parameters**, no retroactive split is required (cohort size cannot be increased after the fact). Instead, each gets a **prospective parity check**: track live WR for the next 60 trading days (ending ~July 2026) against the calibration WR. **Flag drift > 15pp** as evidence the parameter is degrading; review for de-prioritization.

### Phase 2 — Rolling walk-forward (Y2 close, ~April 2027 onward)

Migrate Phase 1's static-split discipline to **rolling walk-forward**:

- **Calibration window:** trailing 12 months.
- **Holdout window:** following 3 months.
- **Slide cadence:** quarterly. Each quarter, the calibration window rolls forward by 3 months and the holdout window rolls forward by 3 months.
- **Parameter versioning:** each parameter set generated by a walk-forward iteration is tagged in git AND captured in `merdian_reference.json` with version, calibration window dates, holdout window dates, calibration WR, holdout WR, drift delta. Old parameters preserved for replay-based comparison per ADR-008.
- **Tolerance:** TBD at Phase 2 cutover; expected 10pp per quarterly iteration (consistent with N≥60 Phase 1 rule, since 12-month calibration windows comfortably exceed N=60).

### Status-quo single-cohort silent waiver — explicitly rejected

Option (d) in Phase α Q4 framing is **not acceptable** even under the constraint that some experiments have insufficient N for formal split. Discipline at low-N is the **explicit "low-N tag"** in Phase 1 D.8.2, **not** a silent waiver.

### Phase 0b FAIL = abandon the dimension as a gate, not retry with parameter tweaks (NEW Session 29)

Added Session 29 as the third governance sub-rule following the first realized falsification.

When a Phase 0b conditional-effect test (or equivalent overlay-calibration study) returns a verdict of FAIL — defined here as either (a) confidence interval for the conditional-WR delta INCLUDES ZERO with adequate N, OR (b) the cohort's median P&L is non-positive across the proposed gate's buckets — the dimension is dead as a signal-time gate. The correct response is to **abandon the dimension** (or ship as logging-only if the data has future-analysis value), **not** to retry with different parameter cutoffs / thresholds / window definitions.

The hazard prevented by this rule is the calibration-time parameter sweep that re-derives an in-sample optimum from the same dataset that produced the FAIL verdict — the exact methodological failure ADR-009 was created to prevent (parameter overfitting from in-sample-only calibration). Retrying with different parameters on a cohort that has already returned a FAIL verdict is structurally equivalent to single-cohort calibration: every parameter tweak is an additional in-sample optimization step against noise that doesn't generalize.

Operational discipline:
- If the FAIL is on confidence-interval-includes-zero with adequate N: the dimension genuinely has no effect; parameter sweeps cannot create an effect.
- If the FAIL is on median-negative cohort: the cohort itself is unfavorable; a conditional gate within an unfavorable cohort cannot survive overhead/slippage even when it improves WR locally.
- If the FAIL is on inadequate N (CI wide but doesn't include zero, AND median positive): the verdict is INCONCLUSIVE, not FAIL — defer to data accumulation, then retest on the larger cohort. Distinguish "inconclusive" from "FAIL" explicitly in verdict reporting.

Logging-only graduation: if the dimension has future-analysis value (e.g., the underlying state variable might compound with another gate in Phase 1+ work), ship the data-capture writer + backfill but do not consume the data in any signal-time gate. The dimension becomes research-available without a production-decision dependency.

---

## Case studies

### S29 first case study — ENH-97 RR-regime gate FAIL

ENH-97 was proposed in ADR-002 v2 §P7 (Session 27 acceptance) as a 4-way RR-regime conditional-WR gate (HIGH/FAIR/LOW/COMPRESSED based on realized-vol/implied-vol ratio). Filed in Assumption Register §D.10.1 as "LIVE pending Phase 0b validation" with explicit falsification commitment.

Phase 0b conditional-WR test was run Session 29 on a 1,968-signal regime-tagged cohort (joining `hist_pattern_signals × vol_analytics × hist_atm_option_bars_5m`).

**Result.** Overall WR 46.2%; χ²=1.56 p≈0.30 across the 4 regime buckets. Per-bucket WR deltas all within sampling noise. No regime configuration produces statistically distinguishable WR.

**Salvage test.** COMPRESSED-as-veto-binary tested (collapse HIGH+FAIR+LOW into one bucket, compare against COMPRESSED). Bootstrap CI [-3.36, +17.69]pp **INCLUDES ZERO**; median P&L negative in both COMPRESSED and non-COMPRESSED buckets.

**Verdict.** Definitive FAIL on both stipulated criteria simultaneously (CI includes zero, median negative).

**Disposition.** Per ADR-002 v2 falsification commitment + the new sub-rule above, ENH-97 PIVOTED `PROPOSED` → `SHIPPED-AS-LOGGING`:
- `vol_analytics.rr_regime` column written by forward-cycle writer + backfilled full year (24,758 rows in `vol_analytics` from `backfill_vol_analytics.py`).
- No signal-time gate consumes the column.
- Data preserved as research-available for potential Phase 1+ second-order use (e.g., conditional on a second dimension that also passes Phase 0b).
- No parameter-sweep retry undertaken or scheduled.

**Cross-validation finding.** The cohort itself was found to be median-negative across all regimes — buyer-edge concentrates in the tails (asymmetric winners on regime-aligned setups per ADR-002 v2 §P1 buyer-writer inversion model), not at the median. This finding is independently captured in Assumption Register §D.12.2 as a structural property of the ICT cohort. It strengthens the FAIL verdict: even if a regime split had produced a marginally significant WR uplift, the median-negative cohort property would have prevented deployment under the new sub-rule.

**Methodology lesson.** Future Phase 0b dimensions must report **median P&L alongside WR delta** in verdict output. WR-only reporting can mask cohort median-negativity and produce a misleading marginal-pass. Filed as enhancement to Phase 0b reporting template (S30 carry-forward).

**References.** `phase0b_rr_conditional_wr.py` (462 lines, Session 29), `phase0b_compressed_veto.py` (309 lines, salvage test), Assumption Register §D.12.1 + §D.12.2 + §D.12.3 (codified governance), Enhancement Register ENH-97 §History (Session 29 status-update block with falsification narrative), ADR-002 v2 §P7 (original gate proposal with falsification commitment).


### S30 second case study — Cohort-translation discipline (D.9.3) caught itself: live-cohort pure-ICT edge unverdicted by S29 Phase 0b

D.9.3 (Session 26) recorded a hypothesis-falsification finding: ENH-55 momentum opposition gate was promoted on 5m-batch `hist_pattern_signals` cohort evidence (Exp 20: opposed 38.3% WR vs aligned 60.9%, +22.6pp lift) but production data on the live signal cohort showed the opposite sign (opposed 79.5% WR vs aligned 54.3% WR, N=44). The codified lesson was: research-cohort verdicts do not transfer to live-cohort behavior without re-validation.

S29 Phase 0b RR-regime gate test (the first case study above) was run on the same 5m-batch `hist_pattern_signals` cohort — 1,968 signals joined `hist_pattern_signals × vol_analytics × hist_atm_option_bars_5m`. The FAIL verdict (χ²=1.56 p≈0.30, COMPRESSED salvage CI [-3.36, +17.69]pp includes zero, median P&L negative both buckets) was clean on that cohort. ENH-97 PIVOTED PROPOSED → SHIPPED-AS-LOGGING per the falsification commitment.

**S30 finding.** A separate question — "what would MERDIAN's gate stack produce on the live cohort if all post-action overrides were disabled?" — was run via `s30_path1_live_cohort_pnl_v5.py` on the live `signal_snapshots` ICT-tagged cohort (8 weeks, 2026-03-23 → 2026-05-15, action ∈ {BUY_CE, BUY_PE} derived from direction_bias before LONG_GAMMA / ENH-77 / ENH-88 / DTE / confidence overrides). Result: **N=211 setups, WR 58.3%, mean +6.96%, median +3.38%, pooled +1,469.13pp**. BULL_FVG sub-cohort: N=99 WR 58.6% (beats Compendium settled 50%). BEAR_FVG: N=107 WR 58.9% (beats Compendium settled 46%). BULL_OB: N=5 (does not replicate Compendium 84% at this N). BEAR_OB: **N=0** (detector tags zero across 8 weeks — orthogonal OB attachment defect; filed as TD-S30-NEW-3).

**Cohort-translation re-applied.** S29 Phase 0b verdict was correct on its 5m-batch cohort. The verdict does NOT transfer to the live cohort, where the same underlying ICT pattern detections — without the gate stack — show median-positive P&L distribution (median +3.38%, contradicting S29's median-negative finding) and statistically meaningful WR uplift over Compendium settled (≥8.6pp on both FVG sub-cohorts, two-sided z-test p<0.05 at this N).

**Disposition.** Per D.9.3 cohort-translation discipline + the methodology lesson of this case study, S29's ENH-97 SHIPPED-AS-LOGGING disposition is preserved (the 5m-batch cohort verdict stands); ENH-97 is added to a new RE-EVALUATE queue gated on live `vol_analytics` accumulation (~3 months → N≈600 ICT-tagged signals with regime tags). The gate stack itself was identified as cohort-prior-biased — ENH-76 / ENH-77 / ENH-88 were all promoted on `hist_pattern_signals` cohort evidence and not re-validated on the live ICT-tagged cohort before shipping. Per the methodology lesson, all four were env-flag disabled in S30 (`MERDIAN_ENH76_ENABLED=0`, `MERDIAN_ENH77_ENABLED=0`, `MERDIAN_ENH88_ENABLED=0`, `MERDIAN_TIER_MULT_DISABLE=1`) pending re-validation on the live cohort at N≥30 per pattern type. Commit `2604fc2`.

**Methodology lesson.** D.9.3 was filed S26 but its scope was implicitly narrowed to "ENH-55 specifically." S30 demonstrates the principle is general: **any signal-time gate whose empirical justification was derived from a non-production cohort (`hist_pattern_signals` 5m-batch, Phase 0b research dataset, replay-derived counts, etc.) requires explicit re-validation on the live signal-snapshots cohort before production deployment.** The cohort-translation check belongs BEFORE the deployment, not after. Single-cohort-derivation (option d of Phase α Q4, rejected as foundational methodology) reappears under a different guise when gates are shipped on a research cohort without checking transfer — same hazard, different surface. Codified into ADR-009 §Phase 1 as new sub-rule (next paragraph).

**Sub-rule added Session 30 (cohort-prior gate hazard).** Any gate whose go/no-go decision derives from a cohort other than the cohort the gate operates on at runtime is in scope for the cohort-translation discipline of D.9.3, regardless of the original derivation's statistical quality. The discipline: env-flag the gate with default OFF until the gate's effect has been measured on N≥30 events on the live runtime cohort. The flag enables reversibility (cheaper than code removal); the default OFF eliminates silent-deployment hazard; the N≥30 floor matches the §Phase 1 graduated-strictness "no formal split required" threshold below which conditional-WR claims are statistically meaningless. Cross-link D.8.2 graduated split (low-N tag) + D.9.3 (cohort-translation) — same principle three failure modes.

**References.** `s30_path1_live_cohort_pnl_v5.py` (live cohort pure-ICT edge measurement), `s30_gate_audit_and_ob_attachment.py` (gate-by-gate rejection-rate audit + OB attachment defect surfacing), `s30_target_days_audit.py` (per-setup blocked/allowed decomposition on May 5/6/13/14 cohort), `apply_s30_patches.py` (four env-flag patches to `build_trade_signal_local.py`), commit `2604fc2`. Assumption Register §D.13.1-D.13.5 (codified findings). Live cohort WR 58.3% / mean +6.96% / median +3.38% / N=211 / 8wk.

---


## Rationale

**Graduated-strictness handles N reality at thin data scales.** With Y1 data scale (~250 trading days), uniform 67/33 holdout is impractical when half the experiment cohorts have N<60. Strict (a) produces unimplementable mandates that get silently waived; status quo (d) leaves overfit risk uncontrolled. The graduation matches discipline to statistical power: 10pp tolerance at N≥60 (where holdout has ~20 events, enough for a meaningful WR estimate), 15pp at 30≤N<60 (smaller holdout, wider tolerance), explicit tag at N<30 (statistically meaningless to split, so don't pretend).

**The "low-N tag" is the discipline at low-N.** It's not a waiver. It's a published commitment: "we know this parameter wasn't formally validated, here's the cohort size at calibration, here's the calibration WR, here's the N-target at which we'll formally split-validate." Future sessions cannot silently inherit a low-N parameter as if it were formally validated; the tag travels with it in `merdian_reference.json`.

**Prospective parity check on existing Exp 15-era parameters is the only retroactive lever available.** Cohort size cannot be increased after the fact; retroactively splitting destroys both halves' statistical power. The only honest move is to let live trading provide the holdout naturally over the next 60 trading days. This is already happening implicitly; this ADR formalizes the threshold (>15pp drift = flag) and the review cadence (~July 2026 owner check-in).

**Phase 2 cutover at Y2 close commits walk-forward forward.** Walk-forward is the academically correct discipline. It's operationally too heavy at Y1 data scale (cohort sizes don't always support 12+3 month windows). Committing to Phase 2 cutover at ~April 2027 means walk-forward is locked in once data supports it, without pretending it's feasible now. The cutover date is not flexible; it's the discipline.

**Phase α architect-deferral was the right shape.** Operator's "I'll go with you since I don't have a better position" reflects the genuine epistemic state: at thin data scales, the methodological choice is not a domain-expert call but a statistical-discipline call. Architect taking responsibility for the recommendation is appropriate. ADR-009 inherits that responsibility in writing.

---

## Alternatives considered

**(a) Strict walk-forward holdout — mandatory before any production parameter change with uniform 67/33 + fixed tolerance.** **Rejected** — at Y1 data scale, half of MERDIAN's experiment cohorts can't support 67/33 with a meaningful holdout. Strict (a) produces either unimplementable mandates or silent waivers; both fail. The failure mode of strict (a) is documentation theater, not discipline.

**(b) Walk-forward holdout strongly recommended, not enforced.** **Rejected** — discipline drifts under "strongly recommended." "Robust enough" judgments creep in. The line between "ship without holdout" and "skip holdout because robust enough" becomes operator-mood-dependent. The point of methodology discipline is to remove judgment from the validation step itself; graduated-strictness preserves that.

**(c) Immediate rolling walk-forward — N-month calibration / M-month holdout slide forward starting now.** **Rejected** — operationally too heavy at Y1 data scale. 12-month calibration window doesn't exist for parameters tied to features that didn't exist 12 months ago (PO3 session bias from Session 13, ENH-37 ICT pattern detection from Apr 2026, etc.). Walk-forward needs stable feature coverage spanning the calibration window; many MERDIAN features don't have it yet. Phase 2 cutover at Y2 close commits to (c) when data supports it.

**(d) Status quo — single-cohort derivation, accept overfitting risk.** **Rejected** — single-cohort derivation has produced parameters that are traded against. Degradation discipline matters even at low-N. The silent waiver this implies is precisely the failure mode the "low-N tag" replaces with explicit commitment.

---

## Consequences

**Positive:**

- Future parameter changes ship with explicit validation discipline matched to cohort size.
- Existing Exp 15-era parameters get prospective parity tracking; degradation surfaces empirically.
- The "low-N tag" makes silent waivers impossible; every parameter carries its validation provenance.
- Phase 2 cutover commits walk-forward forward without pretending it's feasible now.
- ADR-008 replay infrastructure can validate Phase 1 holdout splits via baseline-vs-holdout comparison on historical data.

**Negative:**

- Phase 1 Y1 will ship fewer parameters than status quo would. The first parameter change submitted under D.8.2 graduated discipline may discover that the holdout fails — a parameter that "felt right" doesn't hold up. This is the discipline working as designed, but it adds friction to research velocity.
- Parameter versioning infrastructure must be designed before Phase 2 cutover. ~1 dedicated session for `merdian_reference.json` schema extension + git-tag conventions. Not blocking; just tracked as Phase 2 prerequisite.
- The 60-day prospective parity check on existing parameters requires either dashboard surfacing or scheduled audit script. Filed as open follow-up.

---

## Implementation

**Immediate (Phase 1 starts now):**

1. **Apply D.8.2 graduated split discipline to next parameter-change experiment.** First test case: any new parameter proposal post-S25. Document the cohort size, the chosen split, the calibration WR, the holdout WR, and the disposition (ship / file-not-ship / low-N tag).
2. **Inventory Exp 15-era parameter values currently in production code paths.** Most are in `detect_ict_patterns.py` thresholds and `assign_tier()` routing logic. Each gets an entry in a tracking artifact (TBD: file in `docs/registers/` or `merdian_reference.json` extension) with calibration WR + N-target for upgrade.
3. **Define `merdian_reference.json` schema extension for "low-N calibration-only" tag.** Fields: parameter name, cohort size at calibration, calibration WR, derivation date, N-target for upgrade to formal split.
4. **Operationalize the 60-day prospective parity check for existing parameters.** Either via dashboard widget (surfacing live WR vs calibration WR per parameter) or via scheduled audit script (running weekly, alerting if drift > 15pp). File as ENH if not already.

**Phase 2 cutover (~April 2027):**

1. Verify data scale supports rolling walk-forward (12-month windows have stable feature coverage).
2. Build walk-forward driver script: takes calibration window dates + holdout window dates, runs derivation on calibration cohort, evaluates on holdout cohort, emits parameter set with tagged version metadata.
3. Migrate parameter versioning to git-tag convention; each walk-forward iteration produces a tagged parameter snapshot.
4. Retire D.8.2 graduated split rules; replace with walk-forward rules in this ADR's Phase 2 section.
5. Update CLAUDE.md governance language; update Decision Index ADR-009 row to reflect Phase 2 active status.

**Verification:**

- Phase 1 immediate: first parameter-change experiment under D.8.2 produces a documented split + holdout result + ship/no-ship disposition. The disposition is the verification that the rule is operational.
- Phase 1 60-day mark (~July 2026): owner check-in on existing Exp 15-era parameters' prospective parity. Document drift per parameter. Flag any > 15pp.
- Phase 2 cutover: walk-forward driver script produces first valid quarterly iteration with all metadata captured. Old parameters preserved for replay-based comparison per ADR-008.

**Cost:** ~2 sessions Phase 1 (inventory + tracking artifact + initial application). ~2 sessions for Phase 2 cutover at Y2 close.

---

## Relationship to other ADRs / TDs / specs

- **MERDIAN_Assumption_Register.md §D.8** is the working draft of this rule; this ADR codifies and the §D.8 rows reference back.
- **MERDIAN_Assumption_Register.md §D.12** (NEW Session 29) codifies the first realized falsification under this ADR: ENH-97 RR-regime gate FAIL on Phase 0b. §D.12.3 records the new sub-rule "Phase 0b FAIL = abandon dimension as gate, not retry with parameter tweaks" as it was added to this ADR §Decision section.
- **ADR-002 v2 §P7** filed ENH-97 with explicit falsification commitment ("If Phase 0b finds RR regime has no statistically significant differential effect on signal WR, ENH-97 may PIVOT to logging-only"). Session 29 Phase 0b run realized that commitment. This ADR's S29 case study is the realization record.
- **MERDIAN_Enhancement_Register.md ENH-97** is the production-side artifact of the S29 case study (status PROPOSED → SHIPPED-AS-LOGGING per the case study disposition).
- **ADR-008 replay infrastructure** is the validation tool for D.8.2 graduated splits — replay over a calibration-window date range and a holdout-window date range, with the parameter modification, can produce the holdout WR before production deploy.
- **ADR-007 V18F ICT pivot** is the source of many Exp 15-era parameters. Those parameters fall under D.8.3 prospective parity check (60-day ending ~July 2026).
- **CLAUDE.md operational finding (Session 22):** "Architecture decisions need ADRs, not session_log notes." This ADR is the answer to that finding for Phase α Q4. Drafting now satisfies the rule.
- **Future ENH-NN** (TBD): operationalize the 60-day prospective parity check. To be filed when the implementation pattern is chosen (dashboard widget vs scheduled audit script).
- **Future ENH-NN** (TBD, S30 carry-forward from this session): enhance Phase 0b reporting template to include median P&L alongside WR delta per verdict bucket. Methodology lesson from S29 case study — WR-only reporting can mask cohort median-negativity.

---

## Governance language one-liner

For propagation to CLAUDE.md "Things that are settled" footer per Doc Protocol v4 Rule 11.3:

> *Calibration discipline is graduated-strictness holdout. Phase 1 (now → ~April 2027 / Y2 close): N≥60 → 67/33 split with 10pp tolerance; 30≤N<60 → 75/25 with 15pp; N<30 → "low-N calibration-only" tag in `merdian_reference.json`, no split required. Existing Exp 15-era parameters get a 60-day prospective parity check, flag drift >15pp. Phase 2 (Y2 close): rolling walk-forward 12-month calibration / 3-month holdout, slide quarterly, parameter versioning via git tag + `merdian_reference.json`. Status-quo single-cohort silent waiver explicitly rejected.*

---

## Open follow-ups

- Operationalize D.8.3 prospective parity check (dashboard widget vs scheduled audit script). File as ENH.
- Inventory all Exp 15-era parameter values currently in production code paths. ~1 session.
- Define `merdian_reference.json` schema extension for "low-N calibration-only" tag. ~0.5 session.
- Design Phase 2 walk-forward driver script (deferred to Y2 cutover).
- Owner check-in ~July 2026 (60 trading days post-S25) on existing parameters' prospective parity.
- **NEW Session 29 — Phase 0b reporting template enhancement.** Methodology lesson from S29 first case study (ENH-97 RR-regime gate FAIL): future Phase 0b dimensions must report median P&L alongside WR delta per verdict bucket. WR-only reporting can mask cohort median-negativity and produce a misleading marginal-pass. File as ENH-NN when the reporting template artifact is chosen (likely `phase0b_*` script harness extension). S30 carry-forward.

---

*ADR-009 — Accepted 2026-05-10 (Session 25). Phase α Q4 codification. Operator deferred to architect recommendation; architect responsibility codified.*
