# ADR-017: Operator Console Design Principles

## Status

PROPOSED — 2026-05-26 (Session 38)

## Context

The MERDIAN engine produces decision-grade signals through a four-layer architecture (per ADR-002 v2): capture → compute → display → execution. The compute layer shipped Layer 2 substrate at S37 (ENH-80 per-strike GEX writer, ENH-81 Positioning Landscape views, Pine overlay v1+v2, Lovable.ai dashboard live).

S38 operator integration check on a live trading day (2026-05-26, 09:00–11:30 IST) surfaced that the display layer has **consolidation debt, not feature debt**. Three operator-facing surfaces exist in parallel:

- `localhost:8765` (MERDIAN Live Dashboard) — light theme, systemic-state heavy (pipeline stages, AWS shadow runner, pre-open capture rows, Dhan token, session/state cards)
- `localhost:8766` (MERDIAN SIGNAL) — dark theme, signal-execution heavy (BUY/SELL action, execution block, capital input, place-order surface, breadth strip)
- Lovable.ai dashboard at `lovable.dev/projects/e8fde6f9-58d0-4444-860d-508b3635b014` — dark theme, GEX + Regime layer + PIN/ACCEL bands + GEX-by-strike histogram

Operator switched between all three surfaces plus an external max-pain dashboard (VRDNation) during the integration check. Existing surfaces overlap in fields, conflict in presentation, and surface implicit / redundant / systemic content that does not drive decisions ("Auto-refresh 30s", "REGULAR_SESSION · 09:15–15:30", "Next: Market close 15:30 in 4h 30m", date stamps, "STALE · 1024h 44m ago" persisting when nothing is actually stale today, ICT empty-state messages, "Signal: 10:56 IST" timestamps when fresh data is implicit, prelim+final gap split, VIX on multiple cards).

Operator framing during the integration check:

> *"Pre-lim, final? Just give gap + % then date and time for what? Market close 15:30 so? like no one knows? Regular Session, normal day — what does it mean — market open, time to close in so many places, not required. In order placement everything is a clutter."*

The substrate is doing real work — today NIFTY PIN 24,100–24,300 stalled spot below 24,100 within the predicted 60-minute window; max-γ-inside-W/D BEAR_FVG confluence at 24,150–24,280 was the strongest cross-system signal MERDIAN produced today — but the display layer **hides that signal under noise**. The Pine overlay combined-view rendering also surfaced a visual occlusion bug where PIN/ACCEL boxes are hidden behind ICT zone fills at overlapping strike ranges.

This ADR codifies the design principles for resolving the consolidation debt and protecting against future drift back into noise-heavy surfaces.

## Decision

Adopt six design principles + one ergonomic corollary for all MERDIAN operator-facing surfaces. New surfaces conform; existing surfaces refactor per ENH-110.

### Principle 1 — Three-filter content rule

Every item must pass three filters before rendering on an operator-facing surface:

- **Implicit content** — derivable from context — does not render. Date when clock is up. "Market open" when data is updating. Session phase when the chip already exists in header. "Auto-refresh 30s" entirely. "Next: Market close 15:30 in 4h 30m" entirely.
- **Redundant content** — same fact in multiple cells — collapses to one. Gap as prelim+final → one number. VIX on every card → one chip in header. "Eff. sizing ₹25,000" alongside "Capital ₹25,000" when they match → one. Timestamps on every cell when one cycle timestamp covers the whole section.
- **Systemic content** — what the system is doing, not what the operator decides on — moves to Health. Pipeline stages, AWS shadow runner status, token-refresh logs, capture audit rows, last-cycle timestamps, "X rows written" success logs, "captured N rows" — all off Marketview.

### Principle 2 — Role contract: three pages, no overlap

- **Marketview** = decisions (current state, signals, structural landscape, what to do now)
- **Health** = diagnostics (what the system is doing, capture/pipeline status, token state, error log, shadow runner state)
- **Settings** = configuration (parameter calibration, capital, display preferences, manual actions, connections)

Items that don't fit cleanly into one of these get cut, not split across pages. Execution and journaling get their own subsequent surfaces (Order Placer, Journal) per ADR-019 + ADR-020 when filed.

### Principle 3 — Asymmetric surfacing: silence is healthy

Default state = invisible. Only abnormality surfaces.

- Stale indicator hidden when fresh; red strip when stale.
- "X pending" badge hidden at zero; amber when populated.
- Empty-state messages cut entirely; section header collapses when zero rows.
- "Success" / "VALID" / "OK" / "HEALTHY" status indicators do not render in the default-healthy state.
- The operator should be able to tell at a glance whether anything needs attention by the **absence or presence** of color/markers, not by reading status labels.

This inverts the default assumption that "showing status is informative." Showing positive status is noise; showing negative status is signal.

### Principle 4 — Confluence is the headline

When two or more structural systems agree at the same strike range — max γ inside an ICT BEAR_FVG cluster, PIN overlapping PDH/PDL, PO3 alignment with active ICT zone, dealer flip-level coinciding with retest-tolerance band — the overlap renders as a **first-class visual element**, not as a side-note in the individual components.

Canonical visual: dashed amber ring around the overlap region in the hero spatial chart, labeled with the confluence content (e.g., "★ confluence: PIN ∩ BEAR_FVG"). Subordinate to this, the underlying elements (max γ marker, ICT zone fill, PIN band) render at reduced visual weight inside the confluence region so the ring reads as the dominant signal.

Confluence detection is the substrate's primary value proposition — it is what MERDIAN sees that an unaided operator does not. It must be the visual headline, not a derivable inference.

### Principle 5 — Motion replaces timestamps

Numbers that update get an inline sparkline (3–5 ticks) instead of a "last updated" timestamp. Movement is the freshness signal. Timestamps stay in journal entries and audit logs only.

Empty sparkline = data has not moved (which is itself information). Stale sparkline = problem (handled by Principle 3 stale indicator).

This removes a class of visual noise (timestamps everywhere) and replaces it with a higher-bandwidth signal (micro-trends visible at-a-glance).

### Principle 6 — Distance × time salience

Structural elements (PIN, ACCEL, max γ, ICT zones, dealer flow scenarios) render with intensity proportional to a salience function:

```
salience(element) = f(proximity_to_spot, time_to_decision, magnitude)
```

Elements beyond actionable range render with reduced opacity or compressed footprint. Concrete example from S38 integration check: NIFTY's max γ at +0.15% from spot with 0h DTE is operationally live; SENSEX's max γ at +0.6% from spot with 24h DTE on the same day is decorative — the dashboard must visually differentiate. All-equal rendering is the current bug.

Implementation: applied at hero chart render time; configurable thresholds live in `merdian_parameters` per ADR-016.

### Principle 7 (corollary) — Keyboard-first ergonomics

Operator-facing surfaces define reserved keyboard shortcuts. Canonical set for Marketview:

| Key | Action |
|---|---|
| `N` / `S` | toggle symbol (NIFTY / SENSEX) |
| `Space` | freeze refresh (annotation mode); toggle to resume |
| `E` | focus Order Placer surface |
| `J` / `K` | step through today's signals |
| `A` | add journal annotation |
| `/` | quick-search a strike, jumps hero chart |

Shortcuts documented in Settings → Display tab; visible on focused-element hover tooltip. Operator workflow during market hours is keyboard-dominant; the current click-only dashboards are an ergonomic tax.

## Consequences

### Operational

- Three existing dashboards (`:8765`, `:8766`, current Lovable build) deprecate to one Marketview surface per ENH-110.
- Operator workflow consolidates: pre-open and intraday no longer require tab-switching across MERDIAN surfaces. External tabs (TradingView, max-pain reference) remain peer surfaces — MERDIAN does not attempt to replicate the chart, and operator continues to use TradingView for price action.
- New "Journal" surface emerges as a first-class operator artifact for session-tagged annotations + automatic outcome-loop review (deferred to ADR-020).
- ENH-83 calibration console graduates from PROPOSED build-deferred to required — Settings → Calibration tab needs it.

### Architectural

- Display layer (per ADR-002 v2 Layer 2.5) gains a codified design contract.
- Future widgets must pass the three-filter check at PR/spec time. Empty-state messages are an explicit anti-pattern.
- Confluence detection becomes a substrate primitive — a cross-system overlap detector running once per cycle and writing to a `signal_confluence` table or equivalent view — not just a visual rendering rule.
- Subsequent pages (Health, Order Placer, Journal) need their own design contracts derived from these principles in ADR-018, ADR-019, ADR-020 — filed PROPOSED on demand.

### Costs

- ENH-110 build (~2-3 sessions Phase 1 + ~1-2 sessions Phase 2 + ~1-2 sessions Phase 3) before Marketview reaches feature-parity with the cut content.
- During the transition, both old surfaces (`:8765`, `:8766`) and new Marketview coexist. Operator must commit to using the new surface for the acceptance criterion in ENH-110 to fire (a full trading day without opening the old surfaces).
- Settings tab structure adds a surface area to maintain; offset by removing scattered config from existing dashboards.

### Risks

- **Lovable anon-key brittleness** (TD-S37-03): RLS misconfiguration produces silent empty datasets, not auth errors. ENH-110 Phase 1 acceptance includes direct anon-key probe smoke-test per table.
- **Confluence detection underdelivers**: if Principle 4 fires on too few sessions to be useful, it's decoration. Mitigated by the falsification criterion below — 20-session check after ship.
- **Keyboard shortcuts conflict with browser defaults**: e.g., `Space` typically scrolls. Implementation must intercept only when Marketview surface is focused.

## Cross-references

- ADR-002 v2 Layer 2.5 (display layer in MERDIAN architecture)
- ADR-016 parameter calibration pattern (referenced in Settings → Calibration tab; ENH-83 graduation)
- ENH-83 calibration console (graduates from PROPOSED build-deferred to required by ENH-110 Phase 1)
- ENH-110 Consolidated Marketview build (implementation spec — companion to this ADR)
- ENH-80 per-strike GEX writer (data source for hero chart)
- ENH-81 Positioning Landscape (PIN/ACCEL data source for hero chart)
- ENH-84 vol_analytics + RR ratio (Phase 2 dependency for IV skew widget)
- ENH-108 N-touch retest detection (Phase 2 dependency for today's signals enrichment)
- TD-S37-01 hardcoded τ in ENH-81 views (closed when ENH-83 ships per Phase 1)
- TD-S37-03 Lovable anon-key brittleness (addressed in Phase 1 smoke test)

## Falsification criteria

- If a new operator-facing widget is added between S38 and Y2-close and it does NOT pass the three-filter check at ship time, ADR-017 was not enforced and needs amendment or stronger gating.
- If operator returns to manual tab-switching between MERDIAN surfaces post-ENH-110 Phase 1 ship, the role contract (Principle 2) was wrong — revisit page boundaries.
- If confluence highlighting (Principle 4) does not surface a single actionable signal in the first 20 sessions post-ship, the principle was decoration not substance — revisit the detection criteria or retire the visual.
- If the silence-is-healthy rule (Principle 3) causes operator to miss an actual stale condition (because they didn't realize absence-of-indicator was the signal), the asymmetry was too aggressive — revisit threshold and add subtle ambient indicator.

---

*Filed Session 38, 2026-05-26. Companion build spec: ENH-110.*
