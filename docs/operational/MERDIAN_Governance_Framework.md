# MERDIAN Governance Framework

**Market Structure Intelligence & Options Decision Engine**

---

| Field | Value |
|---|---|
| Document | `MERDIAN_Governance_Framework.md` |
| Location | `docs/operational/` |
| Type | Governance — how decisions about MERDIAN are validated, shadowed, and promoted |
| Established | 2026-05-09 (Session 23 — created per Doc Protocol v4 Rule 9.4) |
| Source | V16 §3 (Measure→Validate→Shadow→Promote framework) + V16 §3.3 (Four Evidence Questions) + V16 §3.6 (Walk-Forward Validation) + V15.1 §18.1 / V16 §25.1 (Do-NOT-Revive list) — promoted to canonical markdown form |
| Update rule | Rare. Any change to a governance rule requires a new version with exhaustive changelog (Doc Protocol v4 Rule 1). |
| Authority | V19 explicitly states *"V19 does not supersede V16 on architecture"* — the V16 governance is preserved unchanged. ADR-007 demonstrated the framework end-to-end during the V18F pivot. |

---

## Purpose

This document is the consolidated record of MERDIAN's development governance. The four-stage Measure→Validate→Shadow→Promote framework, the Four Key Evidence Questions, the Walk-Forward Validation methodology, the Shadow Mode discipline, and the Do-NOT-Revive list — all of these were established in V16 §3 and §25 in March 2026 and have been preserved through every subsequent architectural change. ADR-002 and ADR-007 explicitly invoke this framework as the standard their decisions were measured against.

Two uses:

1. **Pre-change discipline.** Before proposing a parameter change, threshold modification, or new component, the framework's gates apply. Skipping them is what produced the 11 March 2026 failure that motivated the framework in the first place.
2. **Anchor for ADR rationale.** ADR-001 (validity layer), ADR-002 (architectural principles), and ADR-007 (V18F ICT pivot) all cite "the V16 governance" as the standard their decisions met. This document is that standard.

---

## §1 Core principle

> *Operational correctness is necessary but insufficient. Predictive correctness must be empirically demonstrated, not assumed.*
> — V16 §3.1, March 2026

The principle is not that empirical evidence is *useful*. It is that evidence is *required*. A signal engine that runs without crashes (operational correctness) but produces wrong decisions (predictive incorrectness) is worse than a signal engine that does not run at all — because it consumes capital, attention, and confidence while producing no edge.

The four-stage framework below operationalises this principle.

---

## §2 The four stages — Measure → Validate → Shadow → Promote

Adopted in V16 Appendix E following an external quantitative critique. Mandatory for all signal-engine changes from the point of adoption forward.

| Stage | What it means | Gate to next stage |
|---|---|---|
| **1. Measure** | Fix measurement gaps first. Bad inputs produce bad signals regardless of decision logic. | All measurement gaps for the relevant module are closed. |
| **2. Validate** | Build the evidence base. Query historical signal outcomes. Answer the four key questions before touching any parameter. | Phase 0 evidence base complete for the relevant component. |
| **3. Shadow** | Run new logic in parallel without affecting live signals. Both signals persisted to Supabase. Compare outcomes. | Shadow accuracy ≥ live accuracy for minimum 2 weeks. |
| **4. Promote** | Promote shadow logic to live only after validation passes. Remove old logic — do not leave dead code. | Shadow gate passed; model change log entry written. |

The framework is *sequential* — you cannot validate before measurement gaps are closed (you'd be validating noise), cannot shadow before validation evidence is in (you'd be running a guess), and cannot promote before shadow gates pass (you'd be deploying unproven logic).

---

## §3 The Four Key Evidence Questions (Phase 0)

Before modifying any parameter or threshold, answer these four questions from `signal_snapshots` data. The questions and their architectural status post ADR-007 are recorded below.

| # | Question | What it measures | Why it matters | Post ADR-007 status |
|---|---|---|---|---|
| Q1 | When BUY_PE/BUY_CE was blocked (`trade_allowed=false`), what did the market do? | Cost of conservative gates | Quantifies suppression cost — was the gate correct? | **ANSWERED** by ENH-35 full-year backtest (V18F). Quantified for trade_allowed=YES (268 bars, 55.2% accuracy). Lower threshold (60→40) passes more signals without materially degrading accuracy. |
| Q2 | When DO_NOTHING fired due to LONG_GAMMA, what did the market do? | Cost of binary LONG_GAMMA block | Quantifies the 11 March failure mode | **ANSWERED** by Exp 17 (1m) + Exp 19 (5m): 47.7% pooled WR — below random. Symmetric block correct. ADR-007 SRB-02 preserved the gate. The V15.1-spec'd three-zone refinement is moot (per ADR-007). |
| Q3 | When confidence was 40–60 (below threshold), what was accuracy? | Whether threshold 60 is correct | May reveal good signals being discarded | **ANSWERED** by Exp 0 (signal_regret_log 614 rows) + ENH-35 backtest. Accuracy at 40–60 is comparable to ≥60. ADR-007 SRB-05 lowered threshold to 40. The V15.1/V16 rule "no threshold change without 30+ sessions of regret data" was satisfied. |
| Q4 | When breadth and momentum conflicted, which was right more often? | Whether CONFLICT should be terminal | Informs multi-horizon voting design | **ANSWERED** by ENH-35 backtest + Exp 20: CONFLICT BUY_CE 58.7% NIFTY / 55.4% combined. Reversing the lift lowered accuracy. ADR-007 SRB-01 lifted the rule. The V15.1 multi-horizon voting design was made moot — momentum is now a confirmation modifier, not a vote member. |

**All four were answered by the V18F experiment series** (Exp 0, 2–16), making V18F the first complete application of the framework to the live signal engine. The questions are not retired by being answered — future architectural changes that reopen any of these areas (e.g. proposing a new VIX gate, a new conservative threshold, a new CONFLICT-style terminal rule) require fresh Phase 0 evidence.

---

## §4 Model Change Log — mandatory

Every threshold change, every logic modification, every new field addition requires a dated entry containing:

- **Date / version** — when, what session
- **Parameter changed** — before / after values
- **Hypothesis being tested** — what the change is trying to achieve
- **Validation criterion** — how success will be measured
- **Outcome** — filled after observation period

Today, the model change log is distributed across `tech_debt.md` (TD entries), `MERDIAN_Enhancement_Register.md` (ENH entries with status transitions), `session_log.md` (per-session record), and ADRs (architectural changes). The framework does not require these be a single file — only that the five fields above are captured for every behavioral change. ADR-007's metadata header is the canonical example.

---

## §5 Shadow Mode — mandatory for all signal logic changes

- Every logic change runs in shadow for **minimum 2 weeks** before promotion
- Shadow and live signals both persisted to Supabase (separate tables / columns; never overlapping write paths)
- Shadow accuracy must meet or exceed live accuracy before promotion
- When a shadow policy is promoted, **old logic is removed — not kept as dead code or alternative path**

Shadow Mode operationalises the Promote stage's gate. It is the safety net that prevents the rationalist failure mode "I've thought about this carefully, it must work" from reaching live capital.

---

## §6 Walk-Forward Validation Methodology (3-Year Dataset)

Mandatory for any parameter derived from historical data.

- **Calibration window:** Year 1 and Year 2 — derive parameters from this data only
- **Validation window:** Year 3 — evaluate on data the system never saw
- **If Year 3 materially underperforms, parameters are overfit — simplify**

> *"Any system calibrated on the full 3-year dataset and evaluated on the same 3 years is lying to you."*

Specific components derivable from 3-year data: LONG_GAMMA block validity by `flip_distance` zone; confidence threshold calibration curve; optimal momentum horizons for NSE; breadth regime thresholds; VIX regime thresholds; CONFLICT resolution logic.

### Open methodological question (post ADR-007)

ADR-007's Exp 15 cohort was full-year (Apr 2025 – Mar 2026) treated as one block, not formally split into Y1+Y2 calibration / Y3 holdout. Three options remain:

1. **Re-run with formal split.** Highest rigor; most work.
2. **Accept full-year cohort.** Defensible because Exp 15 did not fit parameters — it tested an architecture (ICT triggers) whose specification predates the data. Calibration-validation distinction less load-bearing when no fitting occurs.
3. **Adopt Walk-Forward as forward-looking standard.** Apply to next major parameter change; treat ADR-007 as a one-time exception for an architecture-pivot decision rather than a parameter-fit decision.

This question is filed in ADR-007's open follow-ups. The Framework records it here so the answer, when it comes, lands in the correct document.

---

## §7 Worked example — the V18F pivot followed this framework end-to-end

ADR-007 documents the V18F ICT signal architecture pivot. The pivot is the single most consequential decision since V11. It also happens to be the first complete application of this framework to the live signal engine. Tracing it stage-by-stage:

| Stage | When | What happened |
|---|---|---|
| **Measure** | V17 (16A–E, late March 2026) | Closed measurement gaps in shadow. `ret_session` went live (16D). Shadow tables built for IV context, options flow, momentum_v2, SMDM, shadow_signal_v3 (16E). Live signal path untouched per the additive-shadow rule. |
| **Validate** | V18A → V18E (Mar 31 – Apr 9, 2026) | Built the evidence base. Three-zone gamma model added in shadow as `gamma_zone` field (V18A). `signal_regret_log` populated to 614 rows (V18A). Full historical year ingested (V18C). 7-session live canary sprint passed (V18E). All measurement and evidence prerequisites for a signal-architecture change satisfied. |
| **Validate (formal Phase 0)** | V18F (Apr 11–12, 2026) | Eleven experiments (Exp 0, 2, 2b, 2c, 2c v2, 5, 8, 10c, 14, 15, 16) ran against the full year. The Four Key Evidence Questions were answered (per §3 above). The architectural finding — that ICT pattern triggers had higher standalone edge than confidence-score thresholds — emerged from Exp 15. |
| **Shadow** | V18E shadow gate sessions | 8 of 10 shadow sessions PASSED. Per V18G §10.1, the framework's standard 2-week shadow gate was waived in favor of the 1-year backtest (ENH-35 NIFTY 244 signals, 58.6% T+30m accuracy) — substituting evidence depth for evidence duration. **This waiver is itself a precedent worth flagging:** future shadow-gate waivers require equivalent strength of alternative evidence. |
| **Promote** | V18F (Apr 12, 2026) | Shipped. Six rules codified as V19 §8.5 SRB-01 to SRB-05. Old logic (CONFLICT terminal, VIX > 20 gate, MIN_CONFIDENCE = 60) removed — not kept as dead code. ADR-007 documents the decision retroactively (Session 23). |

The framework works. The V18F pivot's empirical grounding is what makes ADR-007 acceptable as a *retroactive* ADR — the decision was already made under the framework, the ADR just makes the rationale audit-discoverable.

---

## §8 Do NOT Revive — anti-pattern list

The architectural patterns below are forbidden. Each was tried, failed, and replaced. Reviving them would re-introduce the failure mode without the original learning.

### §8.1 Original list (V15.1 §18.1 / V16 §25.1)

- **Buildship-based large-loop orchestration** — replaced by `run_option_snapshot_intraday_runner.py` and Windows Task Scheduler / AWS cron
- **`pg_net` / `pg_cron` based options pipeline** — replaced by Local Python backbone; Postgres-side scheduling does not have the observability, retry semantics, or supervisor model the local pipeline requires
- **Supabase Edge Functions for analytics** — replaced by Local Python; Edge Functions cannot meet the cadence + observability + reproducibility requirements
- **BOM/BSE breadth v1** — replaced by NSE-only WCB (V16); BOM/BSE feeds had reliability and coverage gaps
- **`vix_snapshots` table** — `india_vix` lives in `volatility_snapshots`; the legacy table was a data-locality mistake
- **Per-module ad hoc execution** — replaced by `run_option_snapshot_intraday_runner.py`; ad hoc per-module triggering produced inconsistent state and missing rows
- **`nse_dhan_bridge` table** — function served by `dhan_scrip_map`; the bridge was a redundant indirection

### §8.2 Post-ADR-007 additions (Session 23)

These were tried under the V11→V15.1/V16 confidence-scoring architecture, validated as wrong by V18F evidence, and superseded by ADR-007. Re-introducing any of them under a different name re-litigates a settled decision without the V18F evidence base.

- **Confidence-threshold gating without ICT pattern triggers** — the pre-V18F architecture. ICT pattern detection has demonstrably higher standalone edge than confidence-score thresholds (Exp 15: 86–94% WR on OBs). Confidence-score is now an adjustment layer, not a primary trigger.
- **Single-horizon `ret_5m` as primary direction signal** — the 11 March 2026 failure mode (V15.1 §3.6 / V16 §4). Replaced by ICT-derived direction with ret_session as session anchor and momentum confirmation modifier (ENH-01).
- **CONFLICT terminal rule** (breadth-momentum disagreement → unconditional DO_NOTHING) — V18F SRB-01 lifted. Reversing lowered backtest accuracy. The V15.1 §3.3 "open architectural question" is closed.
- **VIX > 20 hard gate on `trade_allowed`** — V18F SRB-04 removed. HIGH_IV regimes show MORE edge on OBs, not less. Counterproductive gate.
- **Three-zone gamma model as live behavioral spec** — `gamma_zone` field exists in `gamma_metrics` for research; behavioral role is moot per ADR-007. Reviving the V15.1 §15.2 Item 6 spec re-introduces complexity that Exp 17/19 evidence already showed was unnecessary (binary block correct).
- **Multi-horizon momentum voting model** (≥2 of 5 of ret_5m / ret_15m / ret_60m / ret_session / vwap_slope agree) — V15.1 §15.2 Item 7. Never built. Made moot by signal-source change: momentum is now a confirmation modifier, not a vote member.

### §8.3 Operational anti-patterns (forming a third group)

These are not architectural reversals but operational mistakes the project has paid for. Codified across CLAUDE.md non-negotiable rules and Deployment Topology §6:

- **Direct-editing code on AWS** — CLAUDE.md non-negotiable rule 1. AWS receives code via `git pull`. Direct edits get clobbered or produce silent Local↔AWS hash mismatches.
- **Running code without preflight PASS** — CLAUDE.md rule 2. Local commit hash must equal AWS commit hash before any live session.
- **Interactive `crontab -e` on AWS** — Deployment Topology §6.2. Always non-interactive temp-file install, snapshot to `logs/aws_crontab_snapshot.txt`.
- **Running `merdian_start.py` on AWS** — Deployment Topology §6.1. Causes frozen SSM terminal requiring EC2 reboot.
- **Patch scripts without `ast.parse()` validation** — CLAUDE.md non-negotiable rule 5. The `force_wire_breadth.py` 2026-04-16 IndentationError at market open is the founding event.
- **Reopening the OpenItems Register** — CLAUDE.md non-negotiable rule 9. Closed 2026-04-15. Persistent items go to ENH-N or TD-N.

---

## §9 Cross-references to architectural ADRs

This Framework records the *governance*. ADRs record the *architectural decisions* that the governance produced. The two operate together:

| ADR | What it adds | Relationship to this Framework |
|---|---|---|
| **ADR-001** — Stable lies defeat duration gates | Validity layer must accompany every stability gate (cross-reference / sanity check on each cycle) | The Shadow stage gate (§2) tests stability over time. ADR-001 says that's not sufficient — the gate also needs validity testing. **Both layers required for promotion.** Filed because Session 7's 27-day breadth cascade passed every shadow gate while writing fabricated rows. |
| **ADR-002** — Market structure philosophy (P1–P6) | Architectural principles for the gamma layer: zones over points, force over direction, dealer flow drives intraday structure, PINNED regime as new state class, capital scaling demands depth-aware sizing | Orthogonal to the signal trigger layer. Where ADR-007 governs *what fires a signal*, ADR-002 governs *what the gamma layer computes underneath*. Both apply concurrently. |
| **ADR-007** — V18F ICT pivot | ICT pattern detection is the primary signal trigger; Kelly tier sizing replaces uniform confidence-based sizing; LONG_GAMMA / NO_FLIP gates preserved; CONFLICT / VIX>20 gates lifted; MIN_CONFIDENCE 60→40 | First complete application of this Framework to the live signal engine. §7 above traces the stages. |

Future ADRs are required for any change of comparable scope (Doc Protocol v4 Rule 10). The Framework is what they're measured against.

---

## §10 What this Framework does NOT cover

For clarity on scope:

- **Per-domain non-negotiable rules** — these live in CLAUDE.md (currently 24 rules as of Session 22). Examples: 5m bars for ICT detection, options-only framework, capital ceiling, OpenItems Register closed. The Framework provides the *meta*-rules; CLAUDE.md provides the *specific* rules.
- **File / table / runner inventory** — lives in `MERDIAN_System_Map.md` and `merdian_reference.json`.
- **Local↔AWS topology** — lives in `MERDIAN_Deployment_Topology.md`.
- **Unvalidated assumptions** — live in `MERDIAN_Assumption_Register.md`. The Framework's Phase 0 / Validate stage is what moves an assumption from LIVE to VALIDATED / REFUTED / SUPERSEDED.
- **Decision history** — lives in ADRs and `MERDIAN_Decision_Index.md`. The Framework is the standard ADRs cite; the ADRs are the decisions themselves.

---

## Update log

| Date | Session | Event |
|---|---|---|
| 2026-05-09 | Session 23 | Created. V16 §3 (Measure→Validate→Shadow→Promote) preserved verbatim. V16 §3.3 (Four Evidence Questions) preserved verbatim, with post-ADR-007 status added per question. V16 §3.6 (Walk-Forward Validation) preserved verbatim, with open methodological question filed. V15.1 §18.1 / V16 §25.1 (Do-NOT-Revive) preserved verbatim as §8.1; six post-ADR-007 antipatterns added as §8.2; six operational antipatterns referenced from CLAUDE.md / Deployment Topology as §8.3. ADR-001/002/007 cross-references added. Worked example (§7) traces V18F pivot stage-by-stage. |

---

*MERDIAN Governance Framework — established Session 23, 2026-05-09. The V16 §3 framework is preserved unchanged; this document promotes it from `.docx`-locked archive to canonical markdown form. V19's "V19 does not supersede V16 on architecture" makes this Framework permanently authoritative on governance.*
