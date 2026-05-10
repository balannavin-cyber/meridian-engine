# ADR-005 — Zone validity model: pure price-based canonical with timeframe-tiered fallback intraday-only

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-05-10 (Phase α Q1 answered Session 25; ADR drafted Session 25) |
| **Decision-makers** | Navin (operator), Claude (architect) |
| **Supersedes** | None |
| **Related** | TD-079 (root cause: zone date-expiry architectural defect), TD-049/050/051 (ICT canon deviations — adjacent), ADR-002 (market structure philosophy: zones not points), ADR-001 (validity layer — distinct concept; this ADR is about zone *validity duration*, ADR-001 is about *data validity cross-reference*). |

---

## Context

The `ict_htf_zones` table holds Higher Timeframe (W, D, 1H) zones across four pattern types — BULL_OB, BEAR_OB, BULL_FVG, BEAR_FVG — plus PDH/PDL daily levels. Every zone has a `valid_to` timestamp that determines when the zone transitions from `ACTIVE` to `EXPIRED`.

The pre-S25 production code in `build_ict_htf_zones.py::expire_old_zones()` applied a uniform date-based expiry rule: **all** OB/FVG zones expired at `valid_to = source_bar_date + 4 weeks`, regardless of whether price had ever closed through them. This was the root cause of TD-079.

**Empirical defect surfaced Session 22 (TD-079):** Pine overlay visually missing **all** resistances above current spot 78,000 → 86,000. SQL audit: 18 W BEAR_OB / BEAR_FVG zones above 78k all marked EXPIRED purely on the 4-weeks-after-source-bar boundary, despite none of them having been broken (price never closed through). The system was discarding structurally-relevant unbreached resistances on a stopwatch.

**Per ICT canon:** zones live until price *closes through them*. PDH/PDL are by definition daily levels and legitimately date-expire. OB/FVG do not.

**Phase α Q1 (Session 22 → Session 25):** "What is the canonical zone validity model? (a) pure price-based, (b) write-once-never-recompute, (c) hybrid by timeframe, (d) status quo." Operator answered **(a) with timeframe-tiered fallback for intraday only** in Session 25.

The 1H tactical-window argument: 1H OB/FVG zones from three weeks ago carry no meaningful tactical information; date-bounding them to 1 week prevents unbounded zone-count growth without compromising the zone's role within the session it formed.

---

## Decision

The canonical zone validity model is **pure price-based**, with a **timeframe-tiered date fallback applied only to intraday (1H) zones**.

| Pattern type | Timeframe | `valid_to` rule |
|---|---|---|
| OB / FVG | 1H | Price-breach **OR** `source_bar_date + 7 days`, whichever first |
| OB / FVG | D | Price-breach only — `valid_to = NULL` |
| OB / FVG | W | Price-breach only — `valid_to = NULL` |
| PDH / PDL | D | Date-expire next session — unchanged from pre-S25 |
| (PWH / PWL if defined) | W | Date-expire next week — by analogous logic |

A zone is `EXPIRED` when *either* (a) price has closed through it (per `recheck_breached_zones()`), or (b) for 1H only, `now() >= valid_to` and price has not yet broken it. D/W OB/FVG zones with `valid_to = NULL` can only transition via (a).

---

## Rationale

**Pure price-based for D/W OB/FVG.** Per ICT canon, OB and FVG zones are structural artifacts of past institutional positioning. They retain meaning until price closes through them — an event that materially invalidates the zone's relevance. Date-expiry is orthogonal to that invalidation criterion. Discarding unbreached zones on a stopwatch destroys the structural map (TD-079 evidence: 18 unbreached resistances above 78k silently dropped from Pine, requiring manual annotation by operator).

**1H timeframe-tiered fallback.** 1H OB/FVG zones are tactical-window structures meaningful within the session/week they form. A 1H zone from three weeks ago is statistically and operationally noise. The 1-week fallback bounds the open-zone count for 1H without compromising the within-session validity that's the actual signal. Without the fallback, 1H zone count grows unboundedly — operationally unacceptable for Pine rendering and zone-iteration cost.

**PDH/PDL unchanged.** Daily Previous-Day-High / Previous-Day-Low are by definition single-session levels; the next session's PDH/PDL replaces them. Date-expiry is canonically correct here.

---

## Alternatives considered

**(b) Write-once-never-recompute** (Phase α Q1 option b). Each zone's `valid_to` is set at write time and never modified afterward. **Rejected** — does not match ICT canon. ICT zones are *living* structures; their status legitimately changes as price action evolves. A write-once model fixes the validity at a moment that may not be the canonically correct moment, and precludes the price-breach transition.

**(c) Hybrid by timeframe** (Phase α Q1 option c). Different validity rules per timeframe in a less principled split (e.g., D and 1H both date-bounded, only W price-only). **Rejected** — D timeframe OB/FVG are macro structures with the same canon as W; bounding them by date discards the same structural map TD-079 surfaced for W. The price/date split should not be timeframe-arbitrary; it should be semantically grounded (intraday tactical window vs. macro structural map).

**(d) Status quo** (`valid_to = week_end + 4 weeks` uniform). **Rejected** — TD-079 root cause; produces visible defect on Pine overlay; bleeds signal quality across months of trading by silently discarding structural map.

---

## Consequences

**Positive:**

- Pine overlay shows the full unbreached resistance + support stack, not a truncated date-bounded subset.
- `detect_ict_patterns.py` queries against `ict_htf_zones` will surface the genuine ICT structure for signal generation.
- Operator's manual TradingView annotations for "missing >78k resistances" become unnecessary.
- D/W zone count remains tractable because price-breach is a frequent natural transition (most W zones break within 2-6 weeks; the long-lived ones are exactly the structurally-relevant ones we want to keep).

**Negative:**

- 1H zone count grows to ~1 week of accumulated zones. Acceptable per architect judgment given hourly bar count (~7 bars/day × 5 days × symbols × pattern types). Pine rendering and `recheck_breached_zones()` iteration cost both stay bounded.
- D/W zones with `valid_to = NULL` are forever-active until breach. Edge case: if the zone-detection logic produces a false-positive zone that price never tests but also never breaks (bar pattern was wrong but price went elsewhere), it stays ACTIVE indefinitely. Mitigation: zone-detection logic is the responsibility of `build_ict_htf_zones.py`; this ADR does not change detection, only validity duration. Existing detection precision is the relevant lever, not validity.
- Backfill pass required for historical D/W OB/FVG zones currently date-EXPIRED but unbreached. ~1 SQL transaction; documented in Implementation.

---

## Implementation

Three implementation actions, queued for the dedicated ADR-005 implementation session:

1. **`expire_old_zones()` rewrite.** Split logic by `(pattern_type, timeframe)`:
   - PDH/PDL: keep date-expire as-is.
   - 1H OB/FVG: `valid_to = source_bar_date + INTERVAL '7 days'`.
   - D/W OB/FVG: `valid_to = NULL`; do not call date-expiry path.
2. **`recheck_breached_zones()` becomes primary D/W transition mechanism.** Already exists in code; needs to be the sole pathway for D/W OB/FVG status transitions. Verify it runs every cycle that touches `ict_htf_zones` (current cadence: pre-market 08:45 IST + intraday rebuilds).
3. **Backfill pass.** Scan all historical D/W OB/FVG zones currently `EXPIRED` on date. For each, query `hist_spot_bars_5m` (or appropriate higher-timeframe source) for any bar that closed through the zone between `source_bar_date` and `valid_to`. If no such bar exists: flip status back to `ACTIVE` and set `valid_to = NULL`. Documented before-and-after row count in commit message.

**Verification after deploy:**

- Pine overlay visually shows the full resistance + support stack including unbreached zones older than 4 weeks.
- SQL audit: `SELECT pattern_type, timeframe, status, COUNT(*) FROM ict_htf_zones GROUP BY 1,2,3` shows expected distribution shift (D/W OB/FVG counts increase as legitimately-unbreached zones flip ACTIVE).
- No regression in `detect_ict_patterns.py` signal output (cohort comparison pre/post backfill on a recent week).

**Cost:** ~2 sessions — 1 for code change + smoke test, 1 for backfill execution + verification.

---

## Relationship to other ADRs / TDs / specs

- **TD-079** is the root cause this ADR addresses. Closure of TD-079 is gated on this ADR's implementation session, not on this ADR's drafting.
- **ADR-001** is conceptually adjacent ("validity") but distinct: ADR-001 is about *cross-reference validation* of upstream data (a stable lie defeats duration gates); this ADR is about *temporal validity duration* of detected zones. Both can co-exist; neither supersedes the other.
- **ADR-002** market-structure philosophy "P1 zones not points" supports this ADR — zones are durable, points are not, but the durability still has finite extent governed by canonical price action.
- **TD-049/050/051** are adjacent ICT canon deviations (D-OB definition, D-zone validity, PDH/PDL ±20pt hardcoded). They will be addressed by ADR-004 (reserved). This ADR (ADR-005) deliberately scopes only zone validity duration; canon deviations on detection are a separate decision.
- **ADR-008 replay infrastructure** is the safety harness for the implementation session — `expire_old_zones()` rewrite can be validated via replay over historical days before production deploy.

---

## Governance language one-liner

For propagation to CLAUDE.md "Things that are settled" footer per Doc Protocol v4 Rule 11.3:

> *Zone validity is pure price-based for D/W OB/FVG (`valid_to=NULL`, transition only via `recheck_breached_zones()`); 1H OB/FVG carry a 1-week date fallback for tactical-window bounding; PDH/PDL date-expire unchanged. The pre-S25 uniform `valid_to = week_end + 4 weeks` model (TD-079 root cause) is rejected. Implementation pending dedicated session.*

---

## Open follow-ups

- Implementation session to execute the 3 actions above. Cost ~2 sessions.
- Pine overlay regeneration after backfill to confirm visible structure restoration.
- TD-079 closure block in `tech_debt.md` Resolved section once implementation lands.
- System Map §B.4 `ict_htf_zones` row update to reflect post-implementation state (currently annotated only with `source_bar_date` timeframe-aware semantics from TD-078 closure; add `valid_to` semantics post-implementation).

---

*ADR-005 — Accepted 2026-05-10 (Session 25). Phase α Q1 codification.*
