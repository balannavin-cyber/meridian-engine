# ENH-110: Consolidated Marketview build

## Status

PROPOSED — 2026-05-26 (Session 38)

## Owner

Navin (operator) + Claude (architect)

## Component

New operator-facing pages replacing three existing surfaces:

- `localhost:8765` MERDIAN Live Dashboard (deprecate)
- `localhost:8766` MERDIAN SIGNAL Dashboard (deprecate)
- Lovable.ai project `e8fde6f9-58d0-4444-860d-508b3635b014` (reseed or replace)

New surfaces: Marketview + Settings (Phase 1); Health, Order Placer, Journal in subsequent phases under their own ENHs.

## Motivation

S38 operator integration check on 2026-05-26 surfaced display-layer consolidation debt — three parallel surfaces with overlapping content, conflicting presentation, and systemic noise that does not drive decisions. Operator framing during integration check:

> *"I want consolidate various dashboards on Meridian."*

Per ADR-017 design principles (filed same session), three become one. ENH-110 is the build spec executing that decision.

The S37 substrate (per-strike GEX, PIN/ACCEL zones, dealer flow scenarios) is doing real work — today's NIFTY PIN at 24,100–24,300 stalled spot below 24,100 within the predicted 60-min window — but the display layer hides that signal under noise. Consolidating to one surface that applies the ADR-017 principles surfaces the substrate's value.

## Scope (in)

- Single Marketview page replacing `:8765` + `:8766` + Lovable
- Settings page absorbing config / calibration / manual-action content
- Left-nav app shell shared across pages (Marketview, Order, Health, Settings, Journal, Logout)
- ENH-83 calibration console graduated and built as Settings → Calibration tab
- Keyboard shortcut layer per ADR-017 Principle 7
- Asymmetric staleness indicator per ADR-017 Principle 3
- Hero spatial chart with confluence detection + ring rendering per ADR-017 Principle 4

## Scope (out)

- Health page — deferred to ADR-018 + ENH-111
- Order Placer page — deferred to ADR-019 + ENH-112 (Phase 1 Marketview includes the affordance only; the execution surface lives separately)
- Journal page + `session_journal` table — deferred to ADR-020 + ENH-113 (Phase 2 of this ENH includes the floating `+` button and capture modal; the journal review surface itself is separate)
- Mobile companion for Square Off — deferred (ENH-114 candidate)
- IV Skew widget — Phase 2 of this ENH, gated on ENH-84 vol_analytics ship
- Adaptive layout based on session phase (different prominence for opening/midday/close) — Phase 3

## Phased build

### Phase 1 — Marketview Phase 1 + Settings (S39+ build candidate; ~2-3 sessions)

**Marketview Phase 1 content:**

- App shell (left nav, top bar with brand only)
- Header strip: symbol toggle + spot + gap chip + DTE chip + regime chip + PO3 chip + session-phase chip + VIX inline + breadth chip + stale chip (conditional)
- Signal row (conditional — hidden when no signal): action + strike + opt_type + conf + status chip + place-order link
- Hero spatial chart: GEX-by-strike bars + PIN/ACCEL bands + ICT zones overlay + spot vertical + max γ marker + confluence dashed amber ring on overlap
- Dealer flow row: 6-scenario grid (±0.5/1/2%)
- Secondary row 3-col: ICT zones near spot (±2%) + today's signals + ATM straddle premium
- IV Skew section: placeholder card greyed at 0.55 opacity ("ships with ENH-84")
- Floating `+` action button bottom-right (modal Phase 2)
- Drill-downs per the interaction table in Appendix A

**Settings Phase 1 content:**

- App shell with Settings highlighted in left nav
- Top bar: page title + pending-changes badge (conditional) + discard + save-changes button (both conditional)
- Sub-nav tabs: Calibration / Capital & sizing / Display / Connections / Manual actions / About
- Calibration tab: ENH-83 parameter table with grouped sections (PIN/ACCEL thresholds, signal gating, capital floors, ICT zone params) + edit modal enforcing mandatory `change_reason` per ADR-016
- Capital & sizing tab: per-symbol caps + sizing rules + risk limits
- Display tab: theme/refresh/density/sparkline/confluence-highlight/stale-threshold toggles + keyboard shortcut reference
- Connections tab: Dhan / Kite / AWS shadow runner / Supabase / Telegram rows with status badge (silent when healthy per ADR-017 Principle 3) + last-refresh inline + refresh-now button per row
- Manual actions tab: three confirmation-gated buttons (refresh signal, regenerate Pine overlay, rebuild ICT zones)
- About tab: MERDIAN version, last deployment, git commit hash, active ADRs link, session count
- Drill-downs per the interaction table in Appendix B

**Backend Phase 1:**

- `merdian_parameters` table per ADR-016 (DDL + bootstrap seeds for `pin.tau.NIFTY`, `pin.tau.SENSEX`, `accel.tau.NIFTY`, `accel.tau.SENSEX`, `sl.buffer_pct`, `retest.tolerance_pct`, `capital.default_inr`, plus session-window flags)
- `core/parameters.py` TTL-cached read API
- Parameter audit log view (`v_merdian_parameter_audit`)
- ENH-81 SQL view DDLs updated to call `get_parameter('pin.tau.<symbol>')` instead of literal `0.3`; `// TAU_PIN` markers removed → closes TD-S37-01

### Phase 2 — Marketview enrichment (~1-2 sessions; gated on ENH-84 ship + ENH-108 ship)

- IV Skew smile widget (gamma_call/gamma_put ratio across strike grid) — populates the placeholder from Phase 1
- `session_journal` table + annotation capture modal + floating `+` button activation
- Confluence detection primitive: writer that compares ENH-81 PIN/ACCEL strikes to active ICT zones per cycle, writes overlap rows to `signal_confluence` table, consumed by hero chart renderer for the dashed amber ring
- Today's signals column enriched with outcome trajectory (open / SL hit / EOD / exited + realized PnL per ADR-011 chain-table held-strike doctrine)
- Operator annotations end-to-end: capture → store → review via Journal page (ENH-113 if filed separately, or absorbed into this ENH Phase 2)

### Phase 3 — Salience + intelligence (~1-2 sessions; gated on Phase 1 live cohort of ~10 trading days)

- Distance × time salience function applied to hero chart rendering per ADR-017 Principle 6
- Historical confluence hit-rate lookup on confluence-ring click (drill: "this confluence pattern has fired N times historically with X% follow-through")
- Adaptive layout based on session phase: opening 09:15–09:30 emphasizes gap + pre-open prints; midday 11:30–13:30 compresses signal row; afternoon 13:30–15:30 re-prioritizes exit-window content; closing 15:00–15:30 surfaces position-flat checklist
- Keyboard shortcut hint overlay (press `?` to show)

## Acceptance criteria

Phase 1:

- Operator runs a full trading day (09:00–15:30 IST) without opening `:8765` or `:8766` or the current Lovable build URL.
- All TRADE_ALLOWED signals fire to and are actionable from Marketview signal row.
- Every parameter change goes through Settings → Calibration with mandatory `change_reason` written to `merdian_parameters`; `change_reason` enforced at DB layer (CHECK constraint non-empty) per ADR-016.
- Stale indicator absent on a healthy session; visible (red strip) within 60s of any source going stale. Verified by manual stale-injection test on a non-trading day.
- Anon-key probe smoke-test passes for all Supabase tables/views consumed by Marketview before ship — addresses TD-S37-03 brittleness.
- All ADR-017 six principles + corollary pass review at ship time — checklist enforced in PR template.

Phase 2:

- Confluence ring fires on the hero chart when ENH-81 PIN/ACCEL overlaps any ICT zone at the same strike range — visually verifiable on a day with overlap (e.g., 2026-05-26 NIFTY had this overlap at PIN 24,100–24,300 ∩ W BEAR_FVG 24,150–24,280).
- Operator captures at least 5 journal annotations across 3 different sessions and reviews them end-of-day via Journal surface.

Phase 3:

- Distance × time salience visually differentiates NIFTY (0h DTE, max γ near spot) from SENSEX (24h DTE, max γ farther) on the same dashboard render — operator can tell at-a-glance which symbol's positioning landscape is operationally live today.

## Implementation notes

- Phase 1 visual implementation lives on Lovable.ai. Existing project `e8fde6f9-58d0-4444-860d-508b3635b014` becomes the seed for the Marketview hero chart (GEX-by-strike already implemented); rest of Marketview + entire Settings page reimplemented per Appendix A + B prompts below.
- Data sources unchanged from S37 substrate:
  - `gex_strike_snapshots` (ADR-015 schema v2)
  - `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`, `v_dealer_flow_sim`, `v_oi_prev_close_snapshots`
  - `gamma_metrics`, `market_breadth_intraday`, `signal_snapshots`, `ict_zones`, `po3_session_state`
- RLS pattern: per-table anon-read access via the three-line canonical pattern from S37 closure (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + `CREATE POLICY ... FOR SELECT TO anon USING (true)` + `GRANT SELECT ... TO anon`).
- TD-S37-01 closure path codified: Phase 1 backend work ships ENH-83, which graduates ADR-016 from PROPOSED to ACCEPTED. The two are bundled in the same Phase 1 deliverable.
- Auto-refresh interval moves from "hardcoded 30s in dashboard" to "configurable in Settings → Display"; default 30s; "manual" option for annotation-mode-like workflow.
- Theme: dark mode primary (operator preference per integration-check screenshots); light mode functional but not default.

## Cross-references

- ADR-017 Operator Console Design Principles (parent decision)
- ADR-002 v2 §Layer 2.5 display layer
- ADR-015 per-strike GEX schema v2 (data source for hero chart)
- ADR-016 parameter calibration pattern (Settings → Calibration tab implementation; graduates from PROPOSED to ACCEPTED via this ENH Phase 1)
- ENH-80 per-strike GEX writer (data source)
- ENH-81 Positioning Landscape (PIN/ACCEL data source for hero chart)
- ENH-83 calibration console (graduates from build-deferred to required by this ENH Phase 1)
- ENH-84 vol_analytics + RR ratio (Phase 2 dependency for IV skew widget)
- ENH-108 N-touch retest detection (Phase 2 dependency for today's signals enrichment)
- TD-S37-01 hardcoded τ in ENH-81 views (closed when this ENH Phase 1 ships ENH-83)
- TD-S37-02 §F1 dealer-vs-positioning split (independent track; not blocking)
- TD-S37-03 Lovable anon-key brittleness (addressed in Phase 1 smoke test)

---

## Appendix A — Lovable brief: Marketview Phase 1

The prompt below is the operator-curated specification for Lovable.ai to execute the Marketview Phase 1 build. Use verbatim or with minimal contextual edits at S39+ build time. Preserved here for durability — the build artifact lives with its spec.

```
PROJECT CONTEXT

MERDIAN is a Market Structure Intelligence engine for intraday NIFTY and SENSEX
options trading on Indian markets (NSE/BSE). The operator is a discretionary
trader sitting at a desk during market hours 09:15-15:30 IST, sole user of the
system. The current dashboard at lovable.dev/projects/e8fde6f9-58d0-4444-860d-
508b3635b014 implements GEX-by-strike and a Regime card with PIN/ACCEL bands.
We are consolidating two other dashboards plus this one into a single
Marketview page per ADR-017 (Operator Console Design Principles).

DESIGN PRINCIPLES (non-negotiable, from ADR-017)

1. Three-filter rule. Cut content that is (a) IMPLICIT (derivable from context
   like date, time-of-day, market-state), (b) REDUNDANT (same fact twice),
   or (c) SYSTEMIC (about the system, not the decision — pipeline state,
   shadow runner, token refresh status — those belong on Health page).

2. Silence = healthy. Default state of status/warning indicators is INVISIBLE.
   Surface only on abnormality. Stale chip is hidden when fresh; "OK" / "VALID"
   indicators do not render in default-healthy state.

3. Confluence is the headline. When PIN/ACCEL overlaps an ICT zone, render the
   overlap as a dashed amber ring — not as a footnote on the individual
   components. This is MERDIAN's primary value proposition.

4. Motion not timestamps. Updating numbers get inline 3-5 tick sparklines
   instead of "last updated at HH:MM:SS" labels.

5. Distance × time salience. Structural elements render with intensity
   proportional to proximity-to-spot × DTE-urgency × magnitude. Render fade-out
   for elements beyond actionable range.

6. Keyboard-first. Implement keyboard shortcuts: N/S toggle symbol, Space
   freeze refresh, E focus order, J/K step signals, A annotate, / strike
   search.

LAYOUT — APP SHELL

Left nav (76px wide, vertical strip, secondary background):
- Brand text "MERDIAN" vertical (rotated) at top, monospace, tertiary color
- 5 icon-label stacks (icon 18px Tabler outline + 9px label below):
  - Market (icon: layout-dashboard) — HIGHLIGHTED on this page with info
    background + info text + rounded
  - Order (icon: cash-register)
  - Health (icon: heart-rate-monitor)
  - Settings (icon: settings)
  - Journal (icon: notebook)
- Logout icon (Tabler: logout) at bottom, tertiary color

Main content: vertical scroll, no nested scroll regions, full-bleed (no inner
padding wrappers).

LAYOUT — MARKETVIEW SECTIONS (top to bottom)

(1) HEADER STRIP — always rendered, single row, flex-wrap on narrow viewports,
border-bottom 0.5px tertiary:

- Symbol toggle pill (inline-flex, secondary bg, rounded, 2px padding):
   * [NIFTY] — primary bg + tertiary border + rounded + 500 weight + 11px when
     selected
   * [SENSEX] — text-only, secondary color, 11px when unselected
- Spot price: monospace 18px, weight 500
- Change %: 11px weight 500, color by sign (success green / danger red)
- 5-tick sparkline next to spot, 42x14, stroke matches change% color
- Gap chip (inline, no background): "gap -0.26%", color by sign
- DTE chip: rounded 11px font-weight 500 with bg+text:
   * 0h → danger bg + danger text (today is expiry)
   * 1h-23h → warning bg + warning text (tomorrow)
   * 24h+ → secondary bg + secondary text
- Regime chip: warning (no_flip) / danger (short_gamma) / success (long_gamma)
- PO3 chip: success (po3 ↑) / danger (po3 ↓) / secondary (po3 —)
- Session-phase chip: info bg ("morning" / "midday" / "afternoon")
- VIX inline text: "vix 15.7" — label tertiary, value primary
- Spacer (flex: 1)
- Breadth inline text: "breadth +49" — color by sign
- Stale chip (CONDITIONAL — hidden when fresh): "stale 90s" danger bg+text

(2) SIGNAL ROW — CONDITIONAL (hidden entirely when no active signal):

- Background: secondary surface (light tint)
- Padding: 10px 16px
- Border-bottom: 0.5px tertiary
- Layout (flex row, align center, gap 10px):
   * Tabler icon: target (14px secondary color)
   * Action text: "BUY 24,100 PE" — 13px weight 500
   * Confidence: "conf 20" — 11px secondary
   * Status chip: "blocked · morning" — danger bg+text, rounded, 10px
   * Spacer
   * Hint text: "click → expand" — 11px tertiary
   * Primary link: "place order →" — info color, 11px weight 500

(3) HERO SPATIAL CHART — always rendered:

- SVG, viewBox "0 0 660 320"
- Width 100%, height auto, display block
- aria-label and title/desc for accessibility

Layers back-to-front:

(a) PIN band: rect spanning strike-X range of PIN zone (e.g. 24,100-24,300),
    full chart height. Fill green hex #639922, opacity 0.08.
    Label "PIN 24,100-24,300" centered at top of band, 10px weight 500,
    green-text color.

(b) ACCEL band: same pattern, strike range of ACCEL (e.g. 23,800-24,000).
    Fill red hex #E24B4A, opacity 0.08. Label "ACCEL 23,800-24,000" same
    pattern, red-text color.

(c) GEX zero baseline: horizontal line at y=160, stroke border-secondary,
    0.5px.

(d) GEX bars per strike, 10px wide, distributed across X axis (one bar per
    available strike from gex_strike_snapshots):
     - Positive GEX (gamma_call dominant or net positive at strike):
       extend UP from y=160, fill green #3B6D11 to #639922 with opacity
       scaled to magnitude
     - Negative GEX: extend DOWN from y=160, fill red #A32D2D to #E24B4A
       opacity scaled

(e) ICT zone overlays — semi-transparent rectangles at strike-X-range of
    each active zone within chart view. Stack vertically in upper region
    (resistance zones) or lower region (support zones). Each box:
     - Fill colored by direction: BEAR_* uses dark-red opacity 0.55,
       BULL_* uses dark-green opacity 0.55
     - Stroke matching fill at 0.5px
     - Inside label: "W BEAR_FVG" 9px, light-color text
    Render at most 4 zone boxes; if more, render top 4 by recency.

(f) Confluence ring — CONDITIONAL (only when PIN/ACCEL strike range overlaps
    any ICT zone strike range):
     - Dashed rectangle (stroke-dasharray="3,2") around the overlap region
     - Stroke amber hex #EF9F27, 1.5px
     - Label above the ring: "★ confluence: PIN ∩ BEAR_FVG" 9px amber
       weight 500

(g) PDH / PDL / pre-market level markers — small vertical tick marks (4px
    long) at the respective strike X-position straddling the y=160 baseline,
    stroke amber #BA7517. Optional label "PDH" / "PDL" below.

(h) Max γ vertical line: dotted purple stroke #7F77DD, 1px,
    stroke-dasharray="3,2", spans chart vertical. Inline label "max γ N"
    9px purple weight 500.

(i) Spot vertical line: solid stroke blue #185FA5, 1.5px, spans chart
    vertical. Spot price label box at bottom: filled rect #185FA5, rx 2,
    white text 10px monospace weight 500 centered in box.

(j) X-axis labels at 5 evenly-spaced strikes (e.g. 23,500 / 23,800 / 24,000
    / 24,300 / 24,500), 9px tertiary text-anchor middle.

(k) Y-axis labels: "long γ" at upper edge (y=42), "short γ" at lower edge
    (y=290), 9px tertiary text-anchor end at x=36.

All text inside SVG: use style="fill: var(--color-text-*)" for theme-aware
coloring where possible. Semantic colors (success/danger/info/warning) use
their respective hex values from the ramp.

(4) DEALER FLOW ROW — 6-cell grid:

- Padding: 12px 16px
- Border-bottom: 0.5px tertiary
- Section heading: 10px tertiary uppercase letter-spacing 1px:
  "dealer flow · 6 scenarios"
- Grid: 6 equal columns, gap 4px
- Each cell:
   * Secondary background, rounded 4px, padding 6px 4px, text-align center
   * Top: percentage label "−2%" / "−1%" etc, 9px tertiary
   * Bottom: dealer Cr value, monospace 11px weight 500
     - Large magnitude (>1L): danger color
     - Smaller magnitude: warning color

(5) SECONDARY ROW — 3-column grid:

- Padding: 12px 16px
- Border-bottom: 0.5px tertiary
- Section heading: 10px tertiary uppercase "secondary · context panels"
- Grid: 3 equal columns, gap 8px
- Each column is a card:
   * Primary background
   * 0.5px tertiary border
   * Rounded medium
   * Padding 10px

Column 1 — "ICT zones ±2%" (CONDITIONAL — hidden when zero zones within ±2%):
- Header row: Tabler icon target-arrow 13px + "ICT zones ±2%" 11px weight 500
- List rows: 10px secondary text, line-height 1.5
   Format per row: "{tf} {type} · {range_low}-{range_high}"
   Example: "W BEAR_FVG · 24,160-24,280"
- Footer hint: 9px tertiary "click row → TradingView"
- Click handler: open TradingView with that zone marker focused

Column 2 — "today's signals":
- Header row: Tabler icon history 13px + "today's signals" 11px weight 500
- List rows: 10px secondary, line-height 1.5
   Format: "{HH:MM} {action} {strike} · {status}"
   Example: "10:57 BUY_PE 24,100 · blocked"
- If all blocked, append tertiary placeholder line:
   "— no actionables yet —"
- Footer hint: 9px tertiary "j/k → step"

Column 3 — "atm straddle":
- Header row: Tabler icon chart-line 13px + "atm straddle" 11px weight 500
- Inline SVG sparkline (180x42 viewBox) of intraday straddle premium
   Polyline 1.5px stroke info color
   Dashed horizontal line at avg, tertiary 0.5px dasharray="2,2"
- Below sparkline: 10px secondary text
   "₹{current} · avg ₹{avg}" with avg styled tertiary

(6) IV SKEW SECTION — Phase 2 placeholder (always rendered, opacity 0.55):

- Padding: 12px 16px
- Section heading: 10px tertiary uppercase "iv skew · phase 2 (enh-84)"
- Placeholder card: secondary bg + dashed-border secondary + rounded medium
  + padding 14px 12px + text-align center
  Text: "smile from gamma_call/gamma_put across strike grid · ships with
  enh-84" 10px tertiary

(7) FLOATING ACTION BUTTON — bottom-right of main, position absolute:

- 36x36 circle
- Background: info bg
- Border: 0.5px info border
- Center: Tabler icon plus, 18px info color
- Click: opens journal capture modal (Phase 2 — placeholder for now)

INTERACTIONS

- Symbol toggle: click or keyboard N/S
- Header chip click: tooltip with full breakdown
   * gap chip → tooltip with prelim/final/prev-close/last-update
   * breadth chip → tooltip with adv/dec/cov/IBR/score
   * DTE chip → tooltip with exact expiry timestamp + hours
   * morning chip → tooltip explaining session phase + gated patterns
- Stale chip click: nav to Health page
- Signal row click (except place order): expand inline to full execution
   block (strike/expiry/DTE/IV/premium/lot cost/WR table)
- Place order link: nav to Order Placer page (route /order) with
   strike/expiry/qty pre-filled in query params
- Hero chart strike bar click: side panel slides in from right with
   per-strike detail (gamma_call, gamma_put, OI, distance to spot,
   nearby zones)
- Hero chart band label click: modal with τ used + peak/trough strike +
   historical sessions with similar prominence pattern
- Confluence ring click: modal with overlap detail + historical hit rate
   for this confluence pattern
- Max γ marker click: drill into per-strike GEX detail at that strike
- Dealer flow cell click: modal with hedging detail (call/put split, what
   dealers must hedge, comparison vs prior session)
- ICT zones row click: opens TradingView with zone focused (window.open)
- Today's signals row click: expand inline to full signal context +
   outcome trajectory if exited
- Straddle premium chart click: full-panel modal with intraday + N-day
   avg overlays + IV decomposition
- Floating + button click OR keyboard A: journal capture modal
   (one-line text input, auto-tagged with cycle + spot + active signal)

KEYBOARD SHORTCUTS (global on Marketview page only):
- N / S — symbol toggle
- Space — freeze refresh (annotation mode); toggle to resume
- E — focus order placer (nav)
- J / K — step through today's signals (highlight active one)
- A — open annotation modal
- / — focus quick-search field (jump hero chart to that strike)

Implementation note: intercept Space only when Marketview surface is
focused, not when an input is active.

CONDITIONAL RENDERING RULES

- Signal row: hidden when no active signal (collapses entirely, not shown
  with empty fields)
- ICT zones column: hidden when zero zones within ±2% of spot
- Today's signals column: hidden when zero signals today (or shows just
  the placeholder "— no actionables yet —" with no header)
- Stale chip: hidden when all sources fresh (latency < 60s)
- Confluence ring: hidden when no overlap detected by detection primitive
- IV skew section: rendered always but greyed (Phase 2 placeholder)
- "X pending" badge (in Settings, not here): hidden at zero — referenced
  for consistency
- Empty-state messages "No active X" / "No data" / "Nothing here":
  CUT ENTIRELY. Sections collapse rather than show empty-state text.

THEME

- Dark mode primary (operator preference per S37 screenshots and current
  Lovable build). Light mode functional but not the default.
- CSS variables for all colors. Theme-aware: --color-background-primary,
  --color-text-primary, --color-text-secondary, etc.
- Test in both modes before shipping.

DATA SOURCES (Supabase)

Tables / views consumed:
- gex_strike_snapshots — per-strike GEX rows (ADR-015 schema v2):
   run_id, strike, expiry_date, symbol, ts, spot, gamma_call, gamma_put,
   oi_total_calls, oi_total_puts, gex_cr, source_table
- v_gex_strike_pin_zone — PIN zone bounds with peak strike and total Cr
- v_gex_strike_accel_zone — ACCEL zone bounds with trough strike and Cr
- v_dealer_flow_sim — 6-scenario grid (±0.5/1/2%) with Cr per scenario
- gamma_metrics — net_gex, regime, flip_level, max gamma, dte
- market_breadth_intraday — adv/dec/cov/IBR/regime
- signal_snapshots — today's signals with action, strike, conf, status
- ict_zones — active zones with timeframe, type, range, status
- po3_session_state — po3_session_bias (PO3_BULLISH / PO3_BEARISH / NEUTRAL)
- market_spot_session_markers — pre-open prints, session anchors for gap

Anon-read access via Supabase JS client. Auto-refresh every 30s
(configurable in Settings → Display). All numeric values from these
tables; do not invent values for "looks better" — fidelity is the value.

SMOKE TEST (acceptance gate per TD-S37-03 mitigation)

Before shipping, run direct anon-key probe for each table/view above.
If any returns empty data unexpectedly, halt ship and surface RLS config
issue. Silent empty datasets are the failure mode being mitigated.

DELIVERABLE

A single React page implementing the above as one consolidated surface.
Maintain existing Lovable project conventions (Tailwind, shadcn/ui).
Replaces /marketview-equivalent in the project. Old GEX dashboard becomes
the hero chart seed; rest reimplemented per this spec.

The page must pass all six ADR-017 principles + the keyboard-first
corollary at PR time. The principles checklist:

[ ] Three-filter rule applied — no implicit / redundant / systemic content
[ ] Silence = healthy — no unconditional status indicators
[ ] Confluence ring renders on overlap (verify with mock confluence data)
[ ] Numbers have sparklines, not timestamps
[ ] Distance × time salience applied to hero chart elements
[ ] Keyboard shortcuts all wired and tested
[ ] Stale indicator absent on healthy session, visible within 60s on
    forced stale

End of Marketview prompt.
```

---

## Appendix B — Lovable brief: Settings Phase 1

```
PROJECT CONTEXT

MERDIAN Settings page. Configuration surface for parameter calibration +
display preferences + system connections. Companion to Marketview
consolidation per ADR-017 + ENH-110. Implements ENH-83 calibration console
graduated from PROPOSED build-deferred to required.

LAYOUT — APP SHELL

Same left-nav as Marketview (76px wide, vertical strip), but Settings icon
HIGHLIGHTED with info bg + info text + rounded — instead of Market.

LAYOUT — SETTINGS PAGE

Top bar (border-bottom 0.5px tertiary, padding 10px 16px, flex row align
center gap 12px):
- Title: "Settings" 14px weight 500
- Subtitle inline: "parameter changes & system config" 11px tertiary
- Spacer (flex 1)
- "X pending" badge (CONDITIONAL — hidden at zero): warning bg + warning
   text, rounded, 2px 7px padding, 10px weight 500
- "discard" text link (CONDITIONAL — hidden at zero pending): 11px
   secondary, cursor pointer
- "save changes" primary button (CONDITIONAL — hidden at zero pending):
   info bg + info text, rounded, 4px 10px padding, 11px weight 500

Body: flex row split into left sub-nav (130px) + main tab content (flex 1)
Both share min-height 480px.

SUB-NAV — vertical tabs:

Each tab: 7px 14px padding, 12px font-size
Selected tab: info bg + info text + 2px info border-left
Unselected: secondary text, no background

Tabs (top to bottom):
- Calibration (DEFAULT SELECTED)
- Capital & sizing
- Display
- Connections
- Manual actions
- About

MAIN CONTENT — Calibration tab (primary; most complex):

Padding: 14px 16px

Header block:
- Line 1: 11px tertiary "ENH-83 parameter console · ADR-016 audit pattern"
- Line 2: 11px secondary "every change requires `change_reason` ·
   temporal-immutable history"
- `change_reason` styled as inline code: secondary bg, 1px 4px padding,
  rounded 3px, 10px font-size

Parameter sections (collapsible, first 3 expanded by default):

Each section has:
- Section title row: 10px tertiary uppercase letter-spacing 1px, margin
  8px 0 6px
- Table card: primary bg, 0.5px tertiary border, rounded medium, overflow
  hidden

Table structure: grid with columns (2fr 0.8fr 1.2fr 1.2fr 0.4fr):
- KEY (monospace 11px info color)
- VALUE (monospace 11px weight 500)
- LAST CHANGED (11px secondary)
- REASON (11px secondary)
- (edit icon — Tabler edit 13px tertiary, justify-self end)

Header row: 7px 12px padding, 10px tertiary uppercase letter-spacing 0.5px,
border-bottom 0.5px tertiary

Data row: 8px 12px padding, border-bottom 0.5px tertiary (except last)

Pending row override: warning-tinted background (rgba(186, 117, 23, 0.06)),
value styled with warning color + asterisk suffix

Sections to build:

(a) PIN / ACCEL THRESHOLDS:
- pin.tau.NIFTY (default 0.30)
- pin.tau.SENSEX (default 0.30)
- accel.tau.NIFTY (default 0.30)
- accel.tau.SENSEX (default 0.30)

(b) SIGNAL GATING:
- sl.buffer_pct (default 0.005, ref: ADR-012)
- retest.tolerance_pct (default 0.001, ref: ADR-004 §11)
- signal.morning_window_block (boolean, default false)
- signal.afternoon_window_block (boolean, default false)

(c) CAPITAL FLOORS:
- capital.default_inr (default 25000)
- capital.kelly_multiplier (default 1.0)
- capital.max_position_inr (default 50000)

(d) ICT ZONE PARAMS:
- ict.zone.h_valid_days (default 7)
- ict.zone.dwm_breach_only (default true)

Footer link below all sections (11px tertiary):
- Tabler icon history 13px + "view full audit log →"
- Click: opens full audit log view (separate route /settings/audit or modal)

EDIT MODAL (opens on edit-icon click):

Trigger: click on edit icon in any parameter row.

Modal layout:
- Title: "Edit parameter: {key}" — monospace info color
- Current value (readonly, monospace, secondary bg, padded)
- New value input (monospace, validated against min/max bounds for that
   parameter — bounds defined in merdian_parameters DDL)
- Effective from radio:
   * "now" (writes immediately, next read picks up)
   * "next cycle" (writes with valid_from = next cycle start)
- Change reason: multiline text input, REQUIRED, save button disabled
   until non-empty
- Related ADR/ENH link (if parameter has one): "see ADR-016" as text link
- Cancel button + Save button

Save behavior:
- Row in table marked pending (amber tint + asterisk after value)
- Top-bar "X pending" badge increments
- Save not yet committed to DB until top-bar "save changes" clicked

Top-bar save behavior:
- Confirmation modal listing all pending changes
- On confirm: writes all pending to merdian_parameters with their
   respective change_reason values
- Clears pending state
- Shows brief success toast

Top-bar discard behavior:
- Confirmation modal "Discard 2 pending changes?"
- On confirm: resets all pending; restores original values

OTHER TABS (Phase 1 minimum content):

Capital & sizing tab:
- Per-symbol capital inputs (NIFTY input, SENSEX input)
- Sizing rules (Kelly multiplier, max position)
- Risk limits (per-trade max, daily max)
- Same edit-modal pattern as Calibration tab (mandatory change_reason)

Display tab:
- Theme radio (auto / light / dark, default auto)
- Refresh interval radio (30s / 60s / manual, default 30s)
- Density radio (compact / normal / spacious, default normal)
- Sparklines toggle (on / off, default on)
- Confluence highlight toggle (on / off, default on)
- Stale threshold radio (60s / 120s / 300s, default 60s)
- Keyboard shortcuts (readonly list):
   * N/S — toggle symbol
   * Space — freeze refresh
   * E — focus order placer
   * J/K — step signals
   * A — annotate
   * / — strike search

Display preferences NOT routed through merdian_parameters (these are
local-user prefs not system params); stored in localStorage with auto-save
on change (no pending state).

Connections tab:
- One row per service: Dhan, Kite, AWS shadow runner, Supabase, Telegram
- Each row layout: name + status badge + last-refresh inline + refresh
   button
- Status badge — APPLY SILENCE-IS-HEALTHY:
   * HIDDEN when status is healthy / token valid / cycle succeeded
   * VISIBLE amber when stale (refresh > N min ago, configurable)
   * VISIBLE red when failed / expired / down
- Last-refresh inline: 11px secondary "refreshed Xm ago"
- "refresh now" button — confirmation modal before running

Manual actions tab:
- Three buttons, each in own row with description:
   * "refresh signal" — triggers re-run of signal compute
   * "regenerate Pine overlay" — runs generate_pine_overlay.py
   * "rebuild ICT zones" — runs build_ict_htf_zones.py
- Each button click: confirmation modal showing what will run + expected
   wall-time + impact (e.g., "will overwrite current .pine file")
- On confirm: triggers backend action, shows progress, success toast on
   completion

About tab:
- MERDIAN version (from CLAUDE.md current footer)
- Last deployment timestamp
- Git commit hash (current head)
- Active ADRs (link to Decision Index)
- Session count (from session_log)
- "Built by Navin" credit

INTERACTIONS

- Tab click: instant switch, no save needed for navigation
- Edit icon click: opens edit modal
- Modal save: marks row pending, increments badge
- Top-bar save changes: confirmation, writes all pending, clears state
- Top-bar discard: confirmation, resets pending
- Refresh button (Connections): confirmation, triggers backend action
- Manual action button: confirmation showing impact, triggers backend
- Audit log link: full audit log view (separate route)

CONDITIONAL RENDERING (per ADR-017 Principle 3)

- X pending badge: hidden at zero
- Save + discard buttons in top bar: hidden when zero pending
- Connection status badge: hidden when healthy
- Empty parameter sections: cut entirely if no params in that group
- Manual action progress: hidden until action triggered

DATA SOURCES (Supabase)

- merdian_parameters table (ADR-016 DDL):
   id, key, value (jsonb), value_type, category, description,
   min_value, max_value, valid_from, valid_to, changed_by, change_reason
- merdian_parameter_audit view (or v_merdian_parameter_audit) for audit log
- script_execution_log + various status views for Connections tab
- Telegram alert config table (TBD)

THEME

Same as Marketview: dark mode primary, light mode functional. CSS variables
throughout.

DELIVERABLE

A single React page with the tab structure above. Calibration tab
completeness is the primary deliverable — this is the ENH-83 + ADR-016
contract. Other tabs minimum viable for Phase 1; full content in
Phase 2+.

The edit modal MUST enforce change_reason as required + write to
merdian_parameters with full audit trail. This is the ADR-016 architectural
contract — non-negotiable.

End of Settings prompt.
```

---

*Filed Session 38, 2026-05-26. Parent decision: ADR-017. Build candidate for S39+.*
