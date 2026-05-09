# CASE-2026-03-11 — Do-Nothing on a Trend Day

**Permanent architectural reference. Every engineer working on signal quality must read this before modifying thresholds or regime logic.**

---

| Field | Value |
|---|---|
| Document | `CASE-2026-03-11-do-nothing-on-trend-day.md` |
| Location | `docs/decisions/` |
| Type | Single-event case study (Doc Protocol v4 Rule 9 case-file pattern) |
| Event date | 2026-03-11 |
| Documented | March 2026 (V15.1 §3.6, V16 §4) |
| Promoted to standalone markdown | 2026-05-09 (Session 23, per Doc Protocol v4 Rule 1 case-study trigger + ADR-007 follow-up) |
| Status | **Permanent** — the diagnostic insight is preserved indefinitely. The V15.1-spec'd remediation path is superseded by ADR-007 (V18F ICT pivot); see §5 below. |
| Related | ADR-007 (architectural response to this failure) · `MERDIAN_Governance_Framework.md` §1 (the failure motivated the M→V→S→P framework) · `MERDIAN_Assumption_Register.md` (V15.1 Appendix D originated from this case study and the audit it triggered) |

---

## §1 The event

On 11 March 2026, NIFTY fell approximately 450 points (opened ~24,240, closed ~23,800) — a clear, sustained directional session. MERDIAN produced DO_NOTHING for the majority of the session. **The system obeyed its rules. The rules were wrong.**

This is the founding failure event of the March 2026 architectural review. It produced (among other things) the Assumption Register, the Measure→Validate→Shadow→Promote framework, the Four Key Evidence Questions, and Walk-Forward Validation methodology. Every architectural document in MERDIAN traces some lineage to this session.

---

## §2 Observed state

| Variable | Value on 11 March | Effect |
|---|---|---|
| `gamma_regime` | LONG_GAMMA | Hard block on all directional option-buy signals activated |
| `flip_level` | ~23,650 | 539 points (~2.2%) below spot at open |
| `flip_distance` | ~539 points absolute (~2.2%) | Well outside near-flip danger zone — but hard block applied regardless of distance |
| `breadth_regime` | BEARISH | Confirmed broad selling pressure. `breadth_score` ~6.79 — extremely bearish. |
| momentum direction | BULLISH (from `ret_5m`) | 5-minute bounce during downtrend captured — produced CONFLICT with breadth |
| `direction_bias` | NEUTRAL (CONFLICT) | Breadth BEARISH + Momentum BULLISH = CONFLICT → DO_NOTHING |
| `confidence_score` | 38 | Below threshold of 60 → `trade_allowed = false` |
| **Final signal** | **DO_NOTHING, trade_allowed = false** | **No trade authorised. Market moved 450 points.** |

The signal was correctly produced by the rules then in force. Every gate evaluated as designed. The CONFLICT rule produced DO_NOTHING. The LONG_GAMMA gate hard-blocked. The confidence threshold filtered out the residual signal. None of these gates were buggy; all of them were architecturally wrong for this regime.

---

## §3 Three root causes

### Failure 1 — LONG_GAMMA hard block was distance-agnostic

The flip was 2.2% away from spot. At this distance, dealer gamma hedging has negligible directional influence on a 450-point trend move. The hard block was designed for near-flip conditions but applied identically at 2.2%. The assumption that LONG_GAMMA produces uniform behavioural effects regardless of `flip_distance` had never been historically validated.

### Failure 2 — Single-horizon momentum captured a bounce, not the session

`ret_5m` captured a 5-minute bounce during an established downtrend and declared BULLISH momentum. A session anchor (`ret_session = (current_price - open_price) / open_price`) would have read approximately −1.8% by 09:45 IST, correctly overriding the micro bounce as noise-level. `ret_session` did not exist in the momentum schema.

### Failure 3 — CONFLICT rule is terminal with no resolution logic

When breadth and momentum conflict, the logic produced unconditional DO_NOTHING. There was no mechanism to weight session-level evidence (`breadth_score` ~6.79 = strongly BEARISH) against noise-level evidence (a single 5-minute bounce). The rule treated all CONFLICTs as equivalent regardless of strength.

---

## §4 The V15.1-spec'd remediation path

The March 2026 architectural review (V15.1 §15.2 + V16 §18.2) prescribed three specific fixes within the existing confidence-scoring architecture:

| # | Fix | Spec |
|---|---|---|
| 1 | **Three-zone gamma model** (V15.1 §15.2 Item 6, V16 §8.2) | Replace binary LONG_GAMMA hard block with three zones — Zone A (<0.5%) hard block, Zone B (0.5–1.5%) confidence-65 gate, Zone C (>1.5%) gamma gate removed. 11 March was Zone C. |
| 2 | **`ret_session` momentum** (V15.1 §15.2 Item 2) | Add `ret_session = open-to-current` to `momentum_snapshots`. Session anchor would have prevented the micro-bounce misread. |
| 3 | **Multi-horizon momentum voting** (V15.1 §15.2 Item 7) | Replace single-horizon `ret_5m` direction call with a vote across `ret_5m / ret_15m / ret_60m / ret_session / vwap_slope`, ≥2 of 5 must agree. CONFLICT becomes resolvable rather than terminal. |

Plus a discipline gate: **no threshold change without 30+ sessions of `signal_regret_log` data** (V15.1 §15.2 Item 8).

This remediation path was authoritative until April 2026. It motivated the V17 measurement-layer additions, the V18A construction of `signal_regret_log` and `gamma_zone`, and the V18C historical backfill that built the evidence base.

---

## §5 What actually happened — the V18F pivot (ADR-007)

V18F (2026-04-11/12) ran the experiments the remediation framework demanded. The experiments returned a finding the V15.1 spec had not anticipated:

> **The signal-source problem the 11 March failure exposed was not a tuning problem within the existing engine. It was a problem that the engine's *trigger model* was wrong.**

Pure ICT pattern detection (no MERDIAN regime filter) produced 86–94% standalone WR on Order Block patterns (Exp 15). Confidence-score gates that V15.1 spec'd as binary blocks turned out to be either correctly binary (LONG_GAMMA — symmetric across BULL_OB and BEAR_OB at 47.7% WR, below random — meaning the *gate* was right but the *trigger upstream of it* was wrong) or mistakenly binary (CONFLICT, VIX > 20 — both lifted produced higher accuracy).

The remediation V15.1 spec'd became moot:

| V15.1 fix | Disposition under ADR-007 |
|---|---|
| Three-zone gamma model | **Moot** — Exp 17 (1m) + Exp 19 (5m) confirmed binary block correct. Pooled 47.7% WR symmetric across BULL_OB and BEAR_OB. The three-zone refinement addresses a problem that does not exist in the data. The `gamma_zone` field exists in `gamma_metrics` for future research; behavioral role is moot. |
| `ret_session` | **Built and live** — added in V18G as ENH-01. Functions as a confirmation modifier in confidence scoring rather than a vote member. |
| Multi-horizon momentum voting | **Moot** — never built. Made unnecessary because momentum is now a confirmation modifier (Exp 20: +22.6pp lift when ALIGNED), not a primary trigger. |
| 30-session `signal_regret_log` gate | **Satisfied** — `signal_regret_log` was populated to 614 rows V18A; combined with full-year backtest (V18C–F), the evidence requirement was met. ADR-007 SRB-05 lowered MIN_CONFIDENCE 60→40. |

**The diagnostic insight from this case study is permanent. The V15.1 remediation spec is superseded.** Future engineers should read this case study for the diagnosis, and ADR-007 for the resolution.

---

## §6 What this case study still says (permanent implications)

These implications survive the pivot and remain authoritative:

1. **Gates that look like binary truth must be tested as binary truth, not assumed.** LONG_GAMMA's binary block turned out to be correct (Exp 17/19). VIX > 20's binary block turned out to be wrong (Exp 5 + ENH-35). Both were untested assumptions in March 2026. The Four Key Evidence Questions (Governance Framework §3) are the institutional response.
2. **Single-source signals fail on multi-source events.** A 450-point trend day is not a single-source phenomenon — it has session-level direction, breadth confirmation, gamma context, and short-horizon noise simultaneously. A signal engine that lets any one source override the others (single-horizon `ret_5m` declared BULLISH) is structurally fragile. ADR-007's response is to use ICT patterns (which integrate context implicitly through pattern definition) as triggers, with confidence-score modifiers as confirmation rather than gates.
3. **Conservative gates have a quantifiable suppression cost.** The CONFLICT terminal rule, the LONG_GAMMA hard block, and the `confidence < 60` filter all produced DO_NOTHING on 11 March. The Four Evidence Questions exist to quantify this cost for every gate: *"When the gate fired, what did the market do?"* This question, asked of every gate, is what the V18F backtest answered.
4. **"The system obeyed its rules. The rules were wrong."** Operational correctness is necessary but insufficient. Predictive correctness must be empirically demonstrated, not assumed. This sentence is now quoted in the Governance Framework §1 as the core principle.
5. **Documentation of what was tried and why is load-bearing.** Reading V15.1's three-zone gamma spec in 2026-05 without the V18F evidence would mislead a future engineer into thinking it was unimplemented because of priorities. Reading this case study with §5 above tells the truth: it was implemented as a shadow field, tested against data, and made moot by an architectural shift the V15.1 spec did not anticipate. The retroactive ADR-007 is what closes that loop. **Future architectural pivots of comparable scope require an ADR before code, not after** (Doc Protocol v4 Rule 10).

---

## §7 What this case study does NOT mean

To prevent misreading:

- This is **not** a record of a missed trade in the operational sense. MERDIAN was not in live trading on 11 March 2026; the system was running for measurement and shadow validation only. No capital was lost on this date.
- The diagnosis is **not** "ICT patterns would have fired BUY_PE on 11 March 2026". ICT pattern detection didn't exist in MERDIAN until V18F (Apr 2026). What ICT detection on this date would have produced is an empirically open question — `detect_ict_patterns.py` could be run against `hist_spot_bars_5m` for that day to find out. (As of Session 23, this has not been done explicitly. Filed as low-priority enhancement candidate.)
- The remediation supersession in §5 is **not** an indictment of the V15.1 review. The review correctly identified three real failure modes; what the review couldn't have known is that the right fix was upstream of the engine they were tuning. The V15.1 remediation path was the rational response given the architecture in front of them. The pivot was empirical, not retrospective wisdom.

---

## §8 Cross-references

- **`docs/decisions/ADR-007-v18f-ict-pivot.md`** — the architectural response. §5 of this case study summarises; ADR-007 is the full record.
- **`docs/operational/MERDIAN_Governance_Framework.md`** — the framework this failure motivated. §1 (Core Principle) cites this case study.
- **`docs/registers/MERDIAN_Assumption_Register.md`** — ADR-002 cites V15.1 Appendix D as authoritative; that Appendix originated from this case study and the audit it triggered.
- **`docs/decisions/ADR-002-market-structure-philosophy.md`** — Principle P1 ("markets are zones not points") is in part a response to the `flip_distance` unit inconsistency surfaced by this case (V15.1 line 335 NOTE IMPORTANT).
- **`MERDIAN_Master_V15_1.docx`** §3.6 — original case study text, preserved in archive.
- **`MERDIAN_Master_V16_Fixed.docx`** §4 — V16 version of the case study with light editing.

---

## Update log

| Date | Session | Event |
|---|---|---|
| 2026-03 | (V15.1 authoring) | Case study originally documented as V15.1 §3.6, the founding architectural reference event. |
| 2026-03 | (V16 authoring) | Re-stated as V16 §4 with light editing (V16 §4.1/4.2/4.3 sub-section structure). Substance unchanged. |
| 2026-04-11/12 | V18F | V15.1-spec'd remediation evaluated against full-year data. Outcome: signal-source change rather than threshold-tuning. ADR-007 captures the pivot retroactively (Session 23). |
| 2026-05-09 | Session 23 | Promoted from `.docx`-locked archive to standalone markdown at `docs/decisions/CASE-2026-03-11-do-nothing-on-trend-day.md`. Diagnostic content preserved verbatim from V15.1 §3.6 / V16 §4. §4 (V15.1 remediation path) and §5 (V18F supersession) added so the case study is self-contained — readers do not need to chase ADR-007 to know what happened to the original fix list. §6 (permanent implications) and §7 (what this does NOT mean) added to prevent future misreading. |

---

*CASE-2026-03-11 — promoted Session 23, 2026-05-09. Diagnostic content is permanent. Do not modify §1–§3 without architectural review. §4–§5 may be updated if future ADRs further refine the supersession story (e.g. if `gamma_zone` field acquires behavioral role, or if multi-horizon voting is revived under different evidence).*
