# ADR-001 — Stable lies defeat duration gates: validity requires cross-reference

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-04-23 |
| **Session** | Session 7 — breadth cascade root cause |
| **Supersedes** | None — first ADR in the `docs/decisions/` register |
| **Related commits** | `2c130bb` · `1630726` · `befe721` · `04d91a0` · `48d1b6e` |
| **Related open items** | C-09 (CLOSED) · C-10 (OPEN) · TD-014 (CLOSED) |
| **Related registry** | `data_contamination_ranges.BREADTH-STALE-REF-2026-03-27` |

---

## Context

On 2026-04-23, Session 7 diagnosed a breadth cascade failure that had been producing systematically wrong live-trading data for 27 consecutive trading days. The root cause was a writer-retirement gap: when `ingest_breadth_intraday_local.py` was retired on 2026-04-16 (C-08 closure), only one of its two responsibilities was replaced. The new writer `ingest_breadth_from_ticks.py` computed breadth but did not maintain the `equity_intraday_last` reference-price table. The reference froze at 2026-03-27 15:30 IST. Every subsequent breadth compute compared todays live LTPs against a month-old baseline, producing fabricated "BULLISH 92.x" readings on bearish days — directionally inverted from the NSE authoritative 32/68 adv/dec ratio.

During those 27 days, MERDIAN passed its 10-session shadow gate (closed 2026-04-15). Every one of those gate sessions ran on corrupted breadth. The gate did not catch the corruption because **it couldnt**.

The shadow gate as designed measures *stability* — does the signal engine produce consistent output across N sessions without crashing, without drifting outside expected ranges, without edge-case failures? Breadth was perfectly stable across all 10 gate sessions. It stably reported BULLISH 92 every cycle. A stable lie is indistinguishable from a stable truth when your only instrument is a stability meter.

The duration knob was the wrong lever. A 20-session gate would have seen the same stable lie. A 30-session gate would have seen the same stable lie. Doubling the sample size of corrupted data does not surface the corruption — it just gives you more of it.

What the gate needed — and did not have — was a cross-reference check: at each cycle, compare MERDIANs computed breadth against an independent source (NSE API, VRD Nation, sample broker calls) and flag disagreement. That check would have fired on 2026-03-28 — the first trading day the reference went stale. Instead we learned about it on 2026-04-23, 27 days later, via Navins manual observation that MERDIAN breadth was directionally opposite to VRD Nation.

## Decision

**All future MERDIAN gates — shadow gates, promotion gates, validation gates — MUST pair stability testing with validity testing before a component can be promoted.**

Specifically:

1. **Stability layer (existing):** N-session duration test confirming the component runs consistently, produces values within expected ranges, survives edge cases, and does not crash. Unchanged from current practice.

2. **Validity layer (new, required):** A cross-reference check that runs **every cycle**, not just at gate transition, comparing the components output against at least one of:
   - An **external independent source** (different vendor, different API, different computation method), or
   - An **internal consistency rule** (e.g., sum of parts equals aggregate, inputs within bounds implied by other system state)

3. **Sanity check cadence:** Validity checks are cheap. They run at the same frequency as the component being tested, not just at gate boundaries.

4. **Failure handling:** A validity check failure on a single cycle is a warning. Failure on two consecutive cycles raises a S1 alert and flags the component for human review before next-cycle trust.

5. **No promotion without both layers.** A component that passes stability but has no validity check defined is explicitly not gate-eligible. Adding "no validity source available" is an acceptable deferral reason only if the component is non-critical; for trading-path components, a validity source must be found before promotion.

This rule is retroactive for MERDIANs existing promoted components — each must be audited against the standard, and any without a validity layer must have one added (or be explicitly flagged as "promoted on stability alone, validity check pending").

## Consequences

**Positive:**
- The class of bug that produced the breadth cascade cannot pass future gates. Fabricated stability is surfaced by definition when compared against an independent source.
- Governance is honest about what gates actually test. Duration gates measure "the component is steady." Validity gates measure "the component is correct." Both are required; neither is sufficient alone.
- The cost of catching contamination shifts from 27 days (lived experience) to ~2 cycles (validity check latency).
- Future researchers inheriting this codebase have a durable explanation of why every component has a validity sibling — not institutional memory, but a settled protocol in the ADR register.

**Negative:**
- Each gate now has two orthogonal requirements, increasing gate-build cost.
- Every feature block (breadth, gamma, volatility, momentum, WCB, futures) must have a validity source identified — some are straightforward (breadth vs NSE API, basis vs spot), others harder (gamma sum-of-parts is checkable but costly; volatility cross-check against VIX feed is straightforward; momentum is trickier).
- False-positive rate on gates increases slightly. Legitimate drift (e.g., NSE universe expansion) will flag as a validity mismatch and require reconciliation.
- Development friction: any new signal component takes longer to promote.

**Neutral:**
- Existing promoted components now carry explicit debt against this ADR. See follow-up work in Session 8+.

## Alternatives considered

### Alternative 1 — Longer duration gates (20 / 30 / 100 sessions)

Rejected. Doubling the sample size of corrupted data doubles the sample, not the error coverage. The 27-day window we just fixed included ten gate-qualifying sessions; any N <= 27 would have passed on the exact same lie. The premise is wrong — duration measures persistence, not truth.

### Alternative 2 — Manual spot-checks by human

Rejected. This is effectively the status quo that failed. Navin spotted the breadth inversion by noticing it didnt match VRD Nation. That worked once, out of 27 failed opportunities. Vigilance at that frequency is not a scalable governance mechanism, and expecting a human to eyeball live data continuously is a setup for accumulation of silent failures.

### Alternative 3 — Trust `contract_met` telemetry alone

Rejected. `contract_met` captures execution correctness ("did the writer write a row with coverage >= threshold?"), not data correctness ("was the data it wrote correct?"). The breadth writer was perfectly `contract_met=true` on every single one of the 27 contaminated days — it was writing rows, at the expected frequency, with >=50% coverage. The coverage field measured row count, not freshness. Execution-level telemetry is necessary but not sufficient.

### Alternative 4 — Do nothing; accept the risk

Rejected. Phase 4A is live trading. For 27 days, the only reason corrupted breadth did not reach P&L was the ENH-35 LONG_GAMMA hard gate — breadth-derived signals with fabricated BULLISH regime were blocked by an orthogonal gate that happened to be on. That is luck, not architecture. A regime shift to non-LONG_GAMMA on any of those 27 days would have fired real trades on fabricated data. "Protected by an unrelated gate" is not an acceptable posture for a live-trading system.

### Alternative 5 — Validity check at gate transition only (not every cycle)

Rejected in favor of every-cycle. Transition-only validity reduces to "the sample at the gate boundary happened to agree with an external source on that day," which is the same class of weakness as the duration gate itself — a single stable snapshot of stable agreement. Every-cycle validity gives continuous attestation, at negligible additional cost (validity checks are almost always a single extra query or HTTP call per cycle).

## External source candidates by feature block

To operationalize this ADR, each of MERDIANs six JSONB feature blocks needs a validity source identified. Candidates (to be validated in Session 8+ work on TD-NNN-B):

| Feature block | Validity source candidate | Notes |
|---|---|---|
| Breadth | NSE NIFTY 500 adv/dec API - scrape of authoritative breadth widget - broker `ohlc()` sample of N symbols | NSE breadth API is rate-limited; sample approach may be more sustainable. Todays fix uses `ohlc()` for reference, similar pattern. |
| Gamma | Sum of strike-level exposures = total net_gex (internal consistency) | No external source with same computation available; internal sum-check is the only option. Computationally cheap. |
| Volatility | NSE VIX tick vs internal computed VIX - option chain IV fit residuals | VIX feed is authoritative; disagreement > N% flags. |
| Momentum | Spot-price consistency across tick sources - cross-exchange spot comparison (NSE vs BSE) | Cheap; relies on two independent spot feeds agreeing. |
| WCB | Weighted constituent output vs unweighted reference - sanity-bounded by underlying index direction | Harder — WCB is a MERDIAN-specific construction. Consistency rule: WCB regime must not disagree with unweighted breadth by more than N pp without a regime-transition event. |
| Futures | Basis vs theoretical basis = (index * (1 + r*T) - index) | Internal formula check. Disagreement > 0.5% flags. |

These are candidates — the actual validity checks per block will be designed in Session 8+ as part of TD-NNN-B work.

## Relationship to other rules

- **CLAUDE.md Rule 13 (data contamination registry):** provides the forensic layer — once contamination is diagnosed, record it so future researchers avoid tainted data. This ADR provides the preventive layer — catch contamination at source before it becomes historical poison.
- **CLAUDE.md "Things that are settled":** this ADR is eligible for future addition to the settled list once applied across all six JSONB blocks. Not eligible yet — its a standard without current enforcement coverage.
- **Documentation Protocol v3 Rule 1:** ADRs are the durable record of architectural decisions. This is the first entry in `docs/decisions/` and establishes the precedent that significant governance decisions land here, not in scattered CLAUDE.md footers or session_log one-liners.
- **Testing Protocol v1 (if amended):** validity checks belong in the testing protocol as a mandatory layer of the canary/replay/preflight framework. Testing Protocol v1 does not currently require validity checks; that amendment is a candidate for Session 9+.

## Governance language

> **"N days of shadow does not catch a stable lie. Duration gates test stability, not truth. Truth requires external reference or internal consistency — applied every cycle, not just at gate boundaries."**

This is the one-line compressed form for future CLAUDE.md "settled decisions" addition once the standard is fully enforced.

## Open follow-up

- **Session 8+**: Design the validity check library (helper function per feature block), integrate into the gate framework, apply retroactively to all six JSONB blocks.
- **Testing Protocol v1 amendment**: formalize the two-layer gate requirement in the protocol file.
- **ADR-002+ candidate**: Consumer-owned freshness contracts. If a consumer reads an upstream feature block, the freshness gate is the consumers responsibility, not the producers. Session 7 surfaced this pattern but it is a separable architectural decision that warrants its own ADR.

---

*ADR-001 — 2026-04-23 — Session 7 close. First entry in `docs/decisions/`. Establishes the two-layer gate standard (stability + validity) for all future MERDIAN component promotion.*