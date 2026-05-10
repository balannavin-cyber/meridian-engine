# ADR-006 — AWS migration scope: capture/derived split with four-stage decomposition

| Field | Value |
|---|---|
| **Status** | Accepted (principle); execution gated on TD-080 closure (sequencing) |
| **Date** | 2026-05-10 (Phase α Q2 + Q3 answered Session 25; ADR drafted Session 25) |
| **Decision-makers** | Navin (operator), Claude (architect) |
| **Supersedes** | None |
| **Related** | TD-080 (sequencing dependency: AWS Dhan token refresh failure mode must close before disposals execute), Topology §9 (evidence base — 11 open boundary questions; §9 Q1+Q2 closed Session 25; §9.A boundary disposal documented), ADR-008 (shadow-table pattern reuse), CLAUDE.md operational findings (Session 22 architecture-decisions-need-ADRs codification). |

---

## Context

MERDIAN runs in two environments simultaneously: Local Windows (`C:\GammaEnginePython\`, primary live pipeline, 17 Task Scheduler tasks per Topology §7.2) and AWS Meridian (`/home/ssm-user/meridian-engine/`, shadow pipeline, 5 cron entries per Topology §7.1). Several boundaries had unresolved Local↔AWS scope ambiguity surfaced by the Topology §9 audit Session 23 — 11 open boundary questions including:

- Q1: post-market 16:00 IST dual-write (Local `MERDIAN_Post_Market_1600_Capture` vs. AWS `MERDIAN_Postmarket`) — **closed Session 25, dual-write empirically confirmed across 2026-05-04 → 2026-05-08**.
- Q2: PreOpen 09:08 IST dual-write — **closed Session 25, original framing inaccurate; AWS sole writer at 09:08; Local 09:05 was different boundary, disposed (§9.A)**.
- Other open: data-freshness guards (TD-081), runner orchestration scope, telemetry mirroring, etc.

Without a canonical principle for "what runs on AWS vs Local", every new task or boundary decision required ad-hoc adjudication. Session 22 Phase α framing established four operator priorities: (P1) primary data ingestion stable on AWS; (P2) derived layer stays Local; (P3) ICT structures correct; (P4) related TDs pulled in; (P5) open to architectural re-look.

**Phase α Q2 (Session 22 → Session 25):** "What's the canonical principle for what runs on AWS vs Local? (a) capture/derived split, (b) everything to AWS except UI, (c) hybrid by criticality, (d) status quo ad-hoc." Operator answered **(a) capture/derived split** in Session 25.

**Phase α Q3 (Session 22 → Session 25):** "When should TD-080 (AWS Dhan token refresh failure mode) be investigated relative to ADR-006 actions? (a) token reliability FIRST, (b) ADR-006 actions FIRST in parallel, (c) treat as single workstream." Operator answered **(a) token reliability FIRST, ADR-006 actions second** in Session 25 — Local writers stay as redundancy until AWS reliability empirically established across N clean trading days.

The architect-recommended sharpening of (a) was a **four-stage decomposition** that disambiguates the runner — which spans both capture orchestration and derived computation under the (a) principle as originally framed. Without the decomposition, "should X go on AWS?" remains case-by-case; with it, the decomposition gives a deterministic answer per stage.

---

## Decision

The canonical principle for "what runs on AWS vs Local" is a **capture/derived split with four-stage decomposition**:

| Stage | Scope | Local | AWS | Rationale |
|---|---|---|---|---|
| **Capture** | Source-of-truth ingest writers: `market_spot_snapshots`, `option_chain_snapshots`, `india_vix`, `market_breadth_intraday`, `ict_htf_zones` (rebuild from source bars) | **NO writers** (post-disposal state) | **Canonical** | Capture needs always-on cron infrastructure (laptop-independent). Pre-market, post-market, overnight. |
| **Derived** | Computed-state writers: `gamma_metrics`, `volatility_snapshots`, `momentum_snapshots`, `market_state_snapshots`, `signal_snapshots` | **Canonical for production** | **Shadow only** (writes to `*_shadow` tables, not live tables) | Derived computation is where operator iteration speed matters — interactive debugging, ad-hoc SQL, replay what-ifs, experiment scripts. SSH-tunneled debugging is slower; signal-layer iteration is where MERDIAN improves. |
| **Orchestration** | Runner that dispatches the derived stage per cycle (`gamma_engine_supervisor.py` Local; `run_merdian_shadow_runner.py` AWS) | **Production** | **Shadow** (parallel; writes via Derived stage to `*_shadow` tables) | Both run in parallel; comparison between them feeds replay parity validation per ADR-008. Shadow-table pattern from ADR-008 generalizes. |
| **Operator-facing tooling** | Dashboard, signal dashboard, exit monitor, trade logger, ICT zone visualizer | **Local only** | **None** | Operator-facing UI needs local responsiveness, file-system access, and discretionary-execution context. AWS adds round-trip latency without benefit. |

**Sequencing constraint (Phase α Q3):** Disposal of redundant Local writers (e.g., Local post-market 16:00 dual-write per §9 Q1) is **gated on TD-080 closure** — AWS Dhan-token-dependent ingest reliability must be empirically established across N clean trading days before Local writers are removed. The principle in this ADR is settled NOW; the execution awaits that gate.

---

## Rationale

**Capture on AWS = laptop-independent guarantee.** Pre-market, post-market, and overnight cron writers cannot depend on whether the operator's laptop is on, plugged in, awake, or surviving Windows update reboots. Topology §9 Q1 evidence (5 days of post-market dual-write across 2026-05-04 → 2026-05-08) and §9 Q2 evidence (09:08 AWS sole writer with token failure exposing reliability gap on 2026-05-07) both point the same way: capture has to live where always-on infrastructure does. AWS canonical for capture is the single durable answer.

**Derived on Local = operator iteration speed.** Signal-layer computation is where MERDIAN improves over time. The operator reads tracebacks, dumps intermediate variables, runs ad-hoc SQL against snapshot tables, runs replay what-ifs, builds experiment scripts. SSH-tunneled debugging through AWS is not impossible but is *slower*. The capture/derived split is not infrastructure dogma — it's matching infrastructure to the workflow that produces system improvement.

**Runner straddles both — explicit decomposition disambiguates.** The runner does both *orchestration* (cron-equivalent dispatching subprocess calls per V19 §5.2 cycle) and *derived computation* (computing `gamma_metrics`, `volatility_snapshots`, etc.). Treating the runner as a single unit forces it to one environment. The decomposition splits orchestration (parallel both environments) from derived (Local canonical, AWS shadow), which is the architecturally correct move because it lets shadow-table replay parity work without giving up Local iteration speed.

**Shadow-table pattern reuse.** The shadow-table pattern is already in production for ADR-008 replay (`*_replay`) and partially for AWS shadow runner. ADR-006 generalizes: AWS shadow continues writing derived-stage outputs to `*_shadow` tables; comparison between Local production and AWS shadow feeds parity validation. This is real architectural reuse, not boilerplate duplication.

**Operator-facing tooling Local-only.** Dashboards, signal dashboards, exit monitors, trade loggers, ICT zone visualizers all need (a) local file-system access for screenshots/logs, (b) low-latency interaction during live trading, (c) integration with operator's discretionary-execution workflow. None of these benefit from AWS placement; all of them lose from it.

**Q3 sequencing (token reliability first).** TD-080 cross-script evidence on 2026-05-07 narrowed the failure mode from "Dhan API reliability" (multi-vendor diagnostic) to "AWS `refresh_dhan_token.py` failure mode" (single-script root-cause). Until that single-script defect is fixed and N clean trading days pass, Local writers stay as redundancy. This is empirical risk management, not over-caution: the 2026-05-07 incident *did* lose ~70% of trading day's option chain ingest (64 missing 5-min windows; permanent loss of full-chain greeks/IV smile/OI per strike for outage windows).

---

## Alternatives considered

**(b) Everything to AWS except dashboard + interactive tooling.** Capture + derived both on AWS; only operator-facing UI Local. **Rejected** — over-commits to cloud and degrades the iteration loop. Eliminates Local-vs-AWS dual-state confusion at the cost of harder local debugging, requires SSH access for any signal-layer investigation, and treats signal-layer iteration as a second-class concern. The iteration loop is where MERDIAN improves; this alternative penalizes the wrong thing.

**(c) Hybrid by criticality, not layer.** Mission-critical writers (capture, signal generation, alerts) on AWS; supporting/exploratory tooling Local. **Rejected** — criticality classification is subjective and drifts over time. "Signal generation" appearing in the mission-critical list pulls signal-layer to AWS, contradicting (P2) operator priority. The semantic shape of (c) collapses into either (a) or (b) depending on how criticality is drawn; explicit (a) decomposition is cleaner.

**(d) Status quo + ad-hoc decisions.** Each new task migrated based on case-specific judgment. **Rejected** — pragmatic but produces drift. Topology §9-style audits keep surfacing more unaddressed boundaries (5 days of dual-writes, orphan auction-state task before Session 25). ADR-006 becomes a thin document; future audits become the actual decision mechanism. The decomposition prevents future audit-driven decisions from drifting from a stated principle.

**(a) without four-stage decomposition.** Capture vs. derived as a binary split, without explicit treatment of the runner. **Rejected** — the runner straddles both; without explicit decomposition, "should the runner be on AWS?" remains case-by-case. The S22 leaning put the runner in AWS alongside capture; today's (P2) priority pushes back. Four-stage decomposition is the architect-recommended sharpening that makes the principle deterministic.

---

## Consequences

**Positive:**

- Future "should X go on AWS?" questions have a deterministic answer via stage-classification.
- Topology §9 Q1 disposal (Local post-market 16:00 dual-write) executes cleanly under this principle once TD-080 closes.
- Topology §9 Q2 + §9.A (Local 09:05 disposal already shipped Session 25) fits cleanly under Capture stage.
- Shadow-table pattern reuse from ADR-008 generalizes; replay parity validation gains AWS-shadow comparison as a parallel signal.
- Operator iteration speed on signal layer preserved.
- Capture stage gains laptop-independence guarantee.

**Negative:**

- TD-080 must close before disposals can execute — this can take weeks if the failure mode requires statistical sampling. Local writers stay running as redundancy in the interim, doubling infrastructure for capture stage during the gate.
- Shadow-table writes from AWS continue; storage cost grows. Acceptable per architect judgment (Supabase storage is cheap relative to operational risk of removing AWS shadow path).
- Operator-facing tooling on Local means AWS-only operator workflows (e.g., during travel) require either VPN-back-to-Local or temporary tooling-on-AWS deployment. Edge case; not a blocker.

---

## Implementation

**Phase 0 — TD-080 closure (gating dependency):**

1. Dedicated TD-080 investigation session to root-cause `refresh_dhan_token.py` AWS failure mode.
2. Hardening fix to refresh script.
3. Observation: N clean trading days (recommended N=5) of AWS Dhan-token-dependent ingest with no 401s or token-scope failures.
4. TD-080 marked RESOLVED; Phase 1 can proceed.

**Phase 1 — Local writer disposal (post-TD-080):**

1. Local `MERDIAN_Post_Market_1600_Capture` task disabled via PowerShell `Disable-ScheduledTask` (durable). AWS `MERDIAN_Postmarket` is already proven via Topology §9 Q8 partial evidence (5-day reliability captured Session 25).
2. Audit any other Local capture-stage writers identified in Topology §9 questions Q3-Q11 and dispose accordingly.
3. Update Topology §7.2 task inventory to reflect disabled state.

**Phase 2 — AWS shadow derived-stage validation (parallel with Phase 1):**

1. Verify AWS shadow runner writes complete derived-stage outputs to `*_shadow` tables: `gamma_metrics_shadow`, `volatility_snapshots_shadow`, `momentum_snapshots_shadow`, `market_state_snapshots_shadow`, `signal_snapshots_shadow`.
2. SQL parity check: compare `*_shadow` rows vs Local `*` rows for the same boundaries on a 5-day window. Document divergence rate per stage.
3. File any divergences as TDs (similar to ADR-008 documented divergences for replay).

**Phase 3 — Operator-facing tooling Local-only confirmation:**

1. Inventory current operator-facing scripts (dashboards, signal dashboards, exit monitor, trade logger, ICT zone visualizer per Topology §A).
2. Confirm none have AWS-side scheduled invocations.
3. Document Local-only constraint in CLAUDE.md operational findings if not already.

**Verification after each phase:**

- After Phase 0: AWS Dhan-token-dependent ingest produces no 401s for N consecutive trading days.
- After Phase 1: SQL audit shows single-writer at each disposed boundary; no row gaps in `market_spot_snapshots` or `option_chain_snapshots` post-disposal.
- After Phase 2: shadow-vs-live parity rate documented; outliers filed as TDs.
- After Phase 3: Topology §A inventory matches stated principle (operator tooling Local only).

**Cost:** Phase 0 ~1-2 sessions for investigation + 5-day observation. Phase 1 ~0.5 session. Phase 2 ~1 session for parity audit. Phase 3 ~0.5 session for inventory confirmation. Total ~3-4 sessions plus 5-trading-day observation gate.

---

## Relationship to other ADRs / TDs / specs

- **TD-080** is the gating dependency. Drafting this ADR now (Session 25) does not violate Q3 sequencing — Q3 sequences the *execution actions*, not the *principle*. Locking the principle in writing while it's fresh is better than waiting until TD-080 closes and re-deriving it then.
- **ADR-008 replay architecture** uses the shadow-table pattern (`*_replay`); ADR-006 generalizes to `*_shadow` for AWS-Local parity. Same architectural primitive, different use cases.
- **Topology §9** is the evidence base. §9 Q1 + Q2 closures Session 25 pre-validated the principle empirically. §9.A documents the first concrete disposition (Local 09:05 PreOpen disable). Future Topology §9 questions Q3-Q11 each get a deterministic answer via this ADR's stage-classification.
- **CLAUDE.md operational finding (Session 22):** "Architecture decisions need ADRs, not session_log notes." This ADR is the answer to that finding for Phase α Q2+Q3. Drafting now satisfies the rule.
- **TD-081 (no data-freshness guard between primary ingestion and derived layers).** Adjacent — the capture/derived split makes data-freshness guard semantics clearer (it's a guard between stages, not an ad-hoc check). TD-081 implementation will reference this ADR.

---

## Governance language one-liner

For propagation to CLAUDE.md "Things that are settled" footer per Doc Protocol v4 Rule 11.3:

> *AWS vs Local placement is governed by stage: Capture (`market_spot_snapshots`, `option_chain_snapshots`, `india_vix`, `market_breadth_intraday`, `ict_htf_zones`) → AWS canonical no Local writers; Derived (`gamma_metrics`, `volatility_snapshots`, `momentum_snapshots`, `market_state_snapshots`, `signal_snapshots`) → Local canonical with AWS shadow to `*_shadow` tables; Orchestration (runner) → both Local production AND AWS shadow parallel; Operator-facing tooling (dashboards, monitors, visualizers) → Local only. Disposal of redundant Local capture writers gated on TD-080 closure (Phase α Q3 sequencing). Status-quo ad-hoc placement and "everything to AWS except UI" both rejected.*

---

## Open follow-ups

- TD-080 dedicated investigation session (gating Phase 0).
- Phase 1-3 execution sessions post-TD-080.
- Topology §9 Q3-Q11 walk-through under this ADR's principle to surface remaining disposals.
- ADR-006 update if Phase 2 shadow-vs-live parity audit reveals architectural surprises (currently expected: documented divergences similar to ADR-008's strike-base / spot-granularity / VIX-source patterns).

---

*ADR-006 — Accepted (principle) 2026-05-10 (Session 25). Phase α Q2 + Q3 codification. Execution gated on TD-080 closure.*
