# ADR-023 — A read path that was made fast must be made fresh in the same pass: recency floors are part of the latency fix, not a follow-up to it

| Field | Value |
|---|---|
| Status | **Accepted** |
| Date decided | 2026-08-22 |
| Date documented | 2026-08-22 |
| Session | Session 70 |
| Supersedes | Nothing. **Generalises ADR-018 D2** from a specific guard on a specific consumer into a construction rule that binds every derived read path. |
| Related ENH / TD / ADR | ADR-018 D2 (recency floors, the narrow form) · ADR-021 (latest-run view scoping — the fix that created this exposure) · ADR-001 (stable lies) · TD-S69-NEW-3 (`fetch_positioning_landscape` has no floor — the instance) · TD-S61-NEW-1 (`options_flow_snapshots` floor — the precedent that was done correctly) · ENH-81 (Positioning Landscape views) |
| Rule 10 class | **Signal architecture change** — it governs what reaches the operator-facing overlay and under what freshness contract. Mandatory ADR, and written **before** the code per Rule 10. |

---

## Context

ADR-021 rewrote `v_gex_strike_pin_zone` and `v_gex_strike_accel_zone` to scope on `latest_run`, cutting the working set from 1.06M rows to ~80 strikes per symbol. The views went from returning `57014` statement timeouts to returning instantly.

That fix was correct and is not in question. What it also did — silently — was change the *shape of the next failure*.

**Before ADR-021**, a stalled GEX writer produced a timeout. `fetch_positioning_landscape()` raised, the Pine generator emitted an overlay with no PIN and no ACCEL boxes, and the absence was visible on the chart. Loud, unmissable, and in fact exactly how the S69 incident was found: the operator noticed the zones were gone.

**After ADR-021**, the same stall produces stale pin/accel zones returned in milliseconds. The overlay renders. The boxes are there. The numbers are plausible. They are simply from whenever the writer last ran — which could be an hour ago or a week ago, and nothing on the chart says which.

The speed fix converted a loud failure into a quiet one. That is the precise transformation ADR-001 exists to refuse, and it was introduced by a change that was in every other respect an improvement.

S69 noticed this at the time and added a recency floor to the *sibling* consumer, `fetch_intraday_zones` — which is what made the Local generator's honest 106–110 zone count honest, versus the box's 139 with stale M5 merged in. The GEX-side floor was filed as TD-S69-NEW-3 and left for later. It is still not written. The asymmetry has been live since 2026-08-13.

The pattern is not new. TD-S61-NEW-1 added exactly this floor to `_fetch_options_flow()` in `build_trade_signal_local.py`, with a `MERDIAN_FLOW_RECENCY_FLOOR_MIN` env knob and a `_flow_stale` flag recorded into `raw`. That was done right. The problem is that it was done as a *reaction to an incident* rather than as a *construction rule*, so the next read path built or optimised did not inherit it.

## Decision

**Every derived read path carries an explicit recency floor, and the floor ships in the same commit as any change that alters that path's latency or scope.**

Concretely:

**D1 — `fetch_positioning_landscape()` gains a floor.** Follow the `_fetch_options_flow()` shape exactly rather than inventing a second idiom:
- read the row's `ts`, compute age in minutes against `datetime.now(timezone.utc)`
- floor from `MERDIAN_GEX_RECENCY_FLOOR_MIN`, default **15** minutes (the GEX writer's cadence is 5 minutes; 15 permits two missed cycles before the guard fires)
- if the row is older than the floor, **drop the pin/accel data entirely** so the renderer no-ops, and record `pin_accel_stale=True` plus the observed age into the overlay's `raw`/header line
- fail-safe to *absent*, never to *stale*. An overlay with no positioning boxes is a true statement about MERDIAN's knowledge; an overlay with week-old boxes is a false one.

**D2 — the floor is a construction obligation, not a follow-up TD.** Any change that makes a derived read path faster, or narrows its scope, or adds a new consumer of a derived view, must land its recency floor in the same commit. A latency fix without a freshness floor is an incomplete change, and reviewing it as complete is the defect. Filing the floor as a TD "to do next" — which is what S69 did — is explicitly **not** sufficient: TD-S69-NEW-3 has now been open across two sessions while the exposure was live.

**D3 — staleness must be visible in the artefact, not only in a log.** The consumer records the staleness flag and the observed age where the operator will encounter it. A guard that silently suppresses data is better than one that serves stale data, but it is still a silent state change; the operator must be able to tell "no zones because the writer stalled" from "no zones because there are none."

## Rationale

This is not a data-driven decision — there is no cohort to measure. It rests on three observations, each with a concrete instance in MERDIAN's own history:

**A fast wrong answer is worse than a slow one.** ADR-001's founding case was a stability gate that produced confident output from insufficient evidence. The post-ADR-021 pin/accel path has the same signature: well-formed, immediate, and potentially describing a market state that no longer exists.

**Freshness and correctness are independent properties, and speed work only addresses the latter.** ADR-021 guarantees the views compute the right zones for the run they are scoped to. It says nothing about whether that run is current. The `latest_run` CTE resolves `DISTINCT ON (symbol) … ORDER BY symbol, ts DESC` — which faithfully returns the newest row *that exists*, including when the newest row is stale. The scoping fix cannot detect writer failure by construction.

**MERDIAN has already paid for this lesson twice and not generalised it.** ADR-018 D2 established recency floors after the breadth subsystem served stale data. TD-S61-NEW-1 applied one to options flow. Neither was promoted into a rule that binds new code, so ADR-021 — written by someone who knew both — still shipped without one. A principle that must be remembered separately at each site will eventually be forgotten at one of them.

## Alternatives considered

| Alternative | Verdict |
|---|---|
| **Leave it: the GEX writer is reliable, and a stall would be noticed** | **Rejected.** The writer's reliability is not the question — the question is what happens when it fails. S69 is the counter-example: the GEX writer *was* healthy and `gex_strike_snapshots` *was* fresh while the read path was completely broken for weeks. Writer-state and read-path-state are independent (Assumption Register D.27.5), and "someone will notice" is what did not happen for the weeks pin/accel was missing. |
| **Put the floor inside the view rather than the consumer** | **Rejected.** A view that returns zero rows when the data is stale is indistinguishable, at the consumer, from a view that returns zero rows because there are no zones. The consumer needs to know *why* it got nothing in order to render the right thing and record the right flag. Freshness is a consumer-side contract; scope is a view-side contract (ADR-021). Keep them separate. |
| **A global freshness checker that audits all tables on a cron** | **Rejected as a substitute; retained as a complement.** This is TD-S69-NEW-2 (health-check coverage) and it is worth doing — but a check that runs every 15 minutes cannot prevent a specific consumer from rendering a stale artefact in between. The floor belongs at the point of consumption. |
| **Raise the floor high (e.g. 24h) so it almost never fires** | **Rejected.** A floor that never fires is decoration. The floor must be tight enough to catch the failure it exists for: a GEX writer stall during a session. 15 minutes against a 5-minute cadence is the tightest value that tolerates ordinary jitter. |
| **Make the floor mandatory only for operator-facing paths** | **Rejected.** The Pine overlay is operator-facing; `signal_snapshots` is machine-facing and feeds research cohorts. Stale data poisoning a cohort is worse than stale data on a chart, because nobody looks at a cohort until months later (see the `vix_percentile` case, S70: a reference distribution frozen since 2026-03-11, invisible because the fallback logged nothing). |

## Consequences

**Positive**
- The pin/accel path fails to *absent* rather than to *stale*, restoring the loud-failure property ADR-021 removed.
- The rule binds future work, so the next derived view or new consumer inherits the obligation rather than depending on someone remembering ADR-018 D2.
- The staleness flag gives the operator a positive signal distinguishing "writer stalled" from "no zones today" — currently indistinguishable.

**Negative**
- The overlay will occasionally render without positioning boxes where it previously rendered stale ones. That is the intended behaviour and will look like a regression the first time it happens; the `pin_accel_stale` flag exists so it reads as a diagnosis rather than a fault.
- Every new derived read path now carries a small fixed cost. Accepted: the cost is a dozen lines and the alternative is an unbounded silent-staleness surface.
- The floor is a wall-clock heuristic, not a correctness proof. A writer that runs on time but writes wrong data passes the floor. Freshness is necessary, not sufficient.

**Mitigations**
- Default floor lives in an env var (`MERDIAN_GEX_RECENCY_FLOOR_MIN`), so it is tunable without a code change if the writer cadence changes.
- The same `_flow_stale` idiom is reused verbatim, so there is one pattern to learn and one to audit.

## Relationship to other documents

- **ADR-018 D2** — the narrow form. This ADR does not supersede it; it promotes it from a subsystem guard to a construction rule.
- **ADR-021** — the change that created this exposure. ADR-021's open follow-up 1 is precisely D1 here, and this ADR is its escalation from "follow-up" to "obligation."
- **ADR-001** — a fast, plausible, wrong answer is the canonical stable lie. This is that shape arriving through a performance improvement rather than through a gate.
- **Assumption Register D.27.8** — "making a slow read path fast is a strictly safe change" was rejected at S69. This ADR is the standing rule that follows from that rejection.
- **TD-S69-NEW-2** — health-check coverage. Complementary: the health check catches the writer stalling; the floor prevents the consumer from acting on it in the meantime.

## AMENDMENT 1 (Session 71, 2026-08-29) — the Context was overstated and D1's default was derived from the wrong cadence

This ADR is **not reversed**. D2 and D3 stand unchanged, as does the fail-to-absent principle. Three corrections, all discovered while attempting to implement D1.

### A1.1 — The GEX floor already exists. It is warn-only.

The Context of this ADR, TD-S69-NEW-3, and the Decision Index row all state that the positioning-view floor is "still not written." It **was** written, in S69, at `generate_pine_overlay.py:244–266`. It computes the age, prints `STALE: {symbol} positioning views newest ts is …` to stderr, and then executes `return out` **unconditionally**, against a hardcoded `POSITIONING_MAX_AGE_MIN = 1440`.

So the gap is not absence. It is that the floor **warns and returns the stale data anyway** — precisely the failure mode this ADR's D2 ("fail to absent, never to stale") was written to forbid. D1 is therefore a **correction to an existing block**, not new code, and it must not introduce a second idiom alongside it.

D3 is separately and honestly already satisfied for the healthy path: `_pine_positioning_render` emits `// ENH-81 positioning as-of {ts}` into the generated Pine.

### A1.2 — A recency floor is calibrated against the CONSUMER's cadence, never the writer's

D1 specifies a 15-minute default and justifies it as "the tightest value that tolerates ordinary jitter" given the GEX writer's 5-minute cycle. **That is the writer's cadence. The floor binds the consumer.**

`generate_pine_overlay.py` is the consumer. Measured gaps between the newest `gex_strike_snapshots` row and a generation run:

| Generation timing | Newest GEX | Age at generation |
|---|---|---|
| Post-close, after `capture_cas_close.py` (`50 10` UTC) | ~15:25 IST | **~57 min** |
| Pre-market Monday (observed 2026-08-24) | Friday 15:25 IST | **~17 h** |

A 15-minute floor rejects **every** run under both schedules, making PIN/ACCEL permanently absent. The existing 1440 constant's own comment — *"views are EOD-ish, not intraday"* — is correct about the consumer and was written by someone reasoning about the right quantity.

**Amended D1 default: `MERDIAN_GEX_RECENCY_FLOOR_MIN`, default `120`.** Two writer-hours of headroom against the ~57-minute post-close gap; tight enough to catch a mid-session GEX stall; env-tunable so it moves without a commit.

This default is **coupled to a scheduling decision** that does not yet exist. `generate_pine_overlay.py` has had **no scheduled invoker** since the S70 migration dropped the third line of `merdian_eod_ict.bat` (TD-S71-NEW-7). The recommended invoker is `52 10 * * 1-5` (16:22 IST), after the detectors and after the CAS close write. **The floor value and the schedule must be decided together or the floor is uncalibrated again.**

This is the third instance of one error shape in three sessions: Guard 3 generalised from N=2; `OB_MIN_MOVE_PCT` measured a single-bar body against a 5-bar definition; D1 took the writer's cadence for the consumer's. **The easy-to-reason-about quantity substituted for the one that actually binds.**

### A1.3 — D1 is widened: fail-soft must be visible in the artefact, not only stale-soft

Observed 2026-08-28. A `57014` statement timeout on `v_gex_strike_pin_zone` was caught by `fetch_positioning_landscape`'s per-side `except`, which printed a warning to stderr and continued with `out["pin"] = None`. The accel side succeeded. The generated Pine therefore contained:

- a NIFTY **ACCEL** box and **no PIN** box, and
- `// ENH-81 positioning as-of 2026-08-27T09:50:05` — a stamp taken from the *surviving* side.

The artefact asserts complete, current positioning while half of it is missing, and **"no pin zone today" is a legitimate reading of that file**. Staleness and absence are different defects with the same consequence: a consumer that cannot tell.

**D1 therefore also requires:** when either side is unavailable — whether by recency floor or by fetch failure — the generated Pine carries an explicit marker (`// ENH-81 PIN UNAVAILABLE — <reason>`), and the as-of stamp is **per-side or suppressed**, never inherited from the surviving half.

### A1.4 — Status

D1 remains **NOT IMPLEMENTED**, deliberately, pending the `52 10` + 120-minute decision. Implementing it against the original 15-minute default would have removed PIN/ACCEL from every overlay. Recording a non-delivery on evidence is the correct outcome here, not a missed carry.

---

## Governance language

> **A read path made fast must be made fresh in the same pass (ADR-023, S70).** Every derived read path carries an explicit recency floor, and the floor ships in the same commit as any change to that path's latency or scope — filing it as a follow-up TD is not sufficient (TD-S69-NEW-3 stayed open across two sessions with the exposure live). `fetch_positioning_landscape()` takes a `MERDIAN_GEX_RECENCY_FLOOR_MIN` floor, default 15 minutes, and **fails to absent, never to stale**: an overlay with no positioning boxes is a true statement about what MERDIAN knows; an overlay with week-old boxes is a false one. Staleness is recorded in the artefact, not only in a log, so the operator can tell "writer stalled" from "no zones today."

## Open follow-ups

1. **D1 implementation** — add the floor to `fetch_positioning_landscape()` in `generate_pine_overlay.py`, mirroring `_fetch_options_flow()`. Closes TD-S69-NEW-3. Ship with the `capture_cas_close.py` Guard 3 correction in the same pass.
2. **Audit existing consumers** for derived reads without a floor. Known-good: `_fetch_options_flow` (TD-S61-NEW-1), `fetch_intraday_zones` (S69). Unaudited: everything reading `market_state_snapshots`, `signal_snapshots`, and the Marketview frontend queries.
3. **TD-S69-NEW-2** — health-check coverage on the derived surfaces, as the complement to the per-consumer floors.
4. **Consider a shared helper** (`assert_fresh(row, floor_min, label)`) once there are three or more sites, so the idiom cannot drift between them. Not before — two sites is not yet a pattern worth abstracting.

---

*ADR-023 — 2026-08-22 — Session 70 — written before the code, which is the whole point. The exposure was created by a fix, filed as a TD, and left open across two sessions while live. The rule that follows is not "remember the floor" but "the floor is part of the fix" — a principle that has to be remembered at each site will eventually be forgotten at one of them.*
