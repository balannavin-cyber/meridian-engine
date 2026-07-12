# Lovable Prompt — Marketview v6: Ambient Trajectory as the Home Hero

**Target repo:** `balannavin-cyber1/meridian-connect` (Lovable → GitHub → AWS rsync)
**Scope:** ENH-116 Objective 1 — the three-clock-over-price panel becomes the **first and primary view**
on Home. Everything currently on Home demotes to drill-down.
**Governing docs:** ENH-116 (three clocks, four lenses), ADR-017 (operator console design principles).
**Session:** S68.

---

## 0. CONTEXT — read before building

MERDIAN is an intraday options-structure engine for NIFTY / SENSEX. Marketview is its operator
console. Today's Home page shows the ambient verdict headline, a four-lens strip, expiry-memory base
rates, and an open-shift callout — all of them **point-in-time**: they say what the room is *right now*
and nothing about how it *got here*.

The missing thing — and the point of this build — is **trajectory**. A PM cannot read a regime from a
single snapshot. The engine now stores a settled nightly series with three independent "clocks"
running at different speeds:

- **Clock 1 — Positioning Regime** (multi-week): how persistently dealers have been long/short gamma.
  Slow. Turns over weeks.
- **Clock 2 — Cycle-So-Far** (expiry cycle, Mon→expiry): how call/put OI has accumulated through the
  *current* expiry cycle, and where in that cycle we are. Resets every expiry.
- **Clock 3 — Session** (intraday): the live pin / flip / accel read. This already exists and is
  unchanged — it now gets *interpreted against* Clocks 1 and 2 instead of in isolation.

**The product is the three clocks plotted over price, together, so divergence is visible.**
When the clocks agree, the pin is fortress-grade. When they disagree, the room is changing — that is
the single most valuable thing on the screen.

### The restructure (this is the core instruction)

The Ambient Trajectory panel is **the first thing on the screen**. It is not a card among cards. It is
the view. Everything presently on Home — four-lens strip, expiry-memory base rates, open-shift
callout — becomes **drill-down**: reachable, one interaction away, not competing for the first glance.

ADR-017 governs: *Marketview = decisions, silence = healthy, signal = loud.* The trajectory panel
answers "what is the room doing, and is it changing?" before anything else is allowed to speak.

---

## 1. HARD CONSTRAINTS — do not violate

1. **Do not guess column names.** Every column you need is listed verbatim in §3. Past builds broke
   because column names were inferred; this prompt exists partly to prevent that. If you need a field
   that is not in §3, it does not exist — surface an empty state, do not invent it.
2. **Do not create tables, views, or migrations.** Backend is fixed. Read only.
3. **Do not add write paths.** The console is read-only. No inserts, no updates.
4. **Do not change the existing left-rail page structure** (Home / Positioning / Max Pain / Breadth /
   Structure / Expiry Memory + ops sections). Only Home's *content hierarchy* changes.
5. **Do not remove any existing Home content.** It relocates to drill-down. Nothing is deleted.
6. **Keep the existing global NIFTY/SENSEX toggle and the 60s auto-refresh + "updated Ns ago" ticker.**
   The trajectory panel respects the symbol toggle.
7. **Settled vs live must never be visually conflated.** Clock 1 and Clock 2 are *settled nightly*
   data. Clock 3 is *live intraday*. They must be styled so an operator can never mistake one for the
   other (see §5).
8. Use the existing Supabase client (`src/lib/supabase.ts`) and the existing query layer
   (`src/lib/queries.ts`) conventions.

---

## 2. LAYOUT — Home, top to bottom

    ┌────────────────────────────────────────────────────────────────┐
    │  TIER 0 — AMBIENT VERDICT (one line, existing, stays at top)    │
    │  "ACCUMULATION · lenses ALIGNED · gamma POSITIVE_γ ..."         │
    ├────────────────────────────────────────────────────────────────┤
    │                                                                │
    │  TIER 1 — AMBIENT TRAJECTORY  ◀── THE HERO. THE FIRST VIEW.    │
    │  Three clocks over price. Full width. Tall (min 420px).        │
    │  This is the largest object on the page by a wide margin.      │
    │                                                                │
    ├────────────────────────────────────────────────────────────────┤
    │  TIER 2 — DRILL-DOWN (collapsed / tabbed / below the fold)     │
    │  · Four-lens strip          (existing — demoted)               │
    │  · Expiry memory base rates (existing — demoted)               │
    │  · Open-shift callout       (existing — demoted)               │
    │  · Intraday-drift banner    (existing — demoted)               │
    └────────────────────────────────────────────────────────────────┘

**Tier 0** — the verdict headline stays exactly where it is and looks exactly as it does. It is one
line. It reframes everything below it. Do not restyle it.

**Tier 1** — the new hero. Occupies the viewport immediately below the verdict. An operator opening
Marketview should see the verdict line and then, without scrolling, the trajectory.

**Tier 2** — everything else. Put it in a compact tab strip or an accordion directly below Tier 1,
default-collapsed *except* keep the four-lens strip visible if space allows (it is the receipts for
the verdict). The rule: nothing in Tier 2 may be visually louder than Tier 1.

---

## 3. DATA — exact schema, verified live

### 3a. Settled ambient series (Clocks 1 + 2 + price) — `market_environment_snapshots`

One row per symbol per settled session, written nightly at 21:30 IST.

Columns you will use (all verified to exist):

| column | type | meaning |
|---|---|---|
| `symbol` | text | `NIFTY` / `SENSEX` |
| `as_of_date` | date | the settled session this row describes — **this is the x-axis** |
| `for_session_date` | date | the next session this row is a prior for |
| `eod_spot` | numeric | **settled close — this is the price line** |
| `front_expiry` | date | **front expiry as of that session — Clock-2 cycle anchor** |
| `cycle_oi_call_put_asym` | numeric | **Clock-2 magnitude.** `(call_oi − put_oi)/(call_oi + put_oi)` on the total index board. Range ≈ [−1, +1]. **Positive = call-side building = ceiling. Negative = put-side building = floor.** NULL when the participant board was stale (abstains — render as a gap, not as zero). |
| `gex_regime_persistence_20d` | numeric | **Clock-1 magnitude.** Fraction of last 20 sessions net-long-gamma. Range [0, 1]. High = persistently long-gamma = caged/mean-reverting regime. |
| `max_gamma_strike_drift_5d` | numeric | Clock-1 direction. OLS slope of max-γ strike over 5 sessions, in index points/session. Positive = the magnet is drifting up. |
| `concentration_trend_5d` | numeric | Clock-1 texture. Slope of gamma concentration. Rising = the cage is tightening. |
| `net_gex_regime` | text | `POSITIVE_γ` / `NEGATIVE_γ` / `MIXED` |
| `wcb_slope_5d` | numeric | Breadth-lens trajectory (weighted constituent breadth, 5d slope) |
| `pct_above_20dma_slope_5d` | numeric | Breadth-lens trajectory (% above 20DMA, 5d slope) |
| `price_vs_breadth_div` | text | `CONFIRM` / `BEARISH_DIV` / `BULLISH_DIV` / `NEUTRAL` |
| `ambient_regime` | text | `ACCUMULATION` / `DISTRIBUTION` / `TREND_UP` / `TREND_DOWN` / `RANGE` / `UNSTABLE` |
| `lens_alignment` | text | `ALIGNED` / `DIVERGENT` — **the divergence flag; this is the loud one** |
| `session_prior` | text | plain-language one-liner |
| `regime_conditional_note` | text | base-rate receipt (may read "insufficient N") |

Derive in the client, do not expect a column:

- **`dte` = `front_expiry` − `as_of_date`** (days). This is **where in the cycle** that session sat.
- **cycle rollover** = any session where `front_expiry` differs from the previous session's
  `front_expiry`. These are the Clock-2 reset boundaries.

**Query (settled series, ~40 sessions):**

    const { data } = await supabase
      .from('market_environment_snapshots')
      .select('as_of_date, eod_spot, front_expiry, cycle_oi_call_put_asym, gex_regime_persistence_20d, max_gamma_strike_drift_5d, concentration_trend_5d, net_gex_regime, wcb_slope_5d, pct_above_20dma_slope_5d, price_vs_breadth_div, ambient_regime, lens_alignment, session_prior, regime_conditional_note')
      .eq('symbol', symbol)
      .order('as_of_date', { ascending: true })
      .limit(40);

Note: the series currently has ~15 settled sessions and grows nightly. Handle a short series
gracefully — do not assume 40 points exist.

### 3b. Live session read (Clock 3) — `gamma_metrics`

Already consumed elsewhere in the app. Take the **latest row for the symbol**. Columns you will use:

`ts`, `spot`, `regime`, `flip_level`, `max_gamma_strike`, `gamma_concentration`, `net_gex`,
`expiry_date`, `dte`, `pin_risk_score`, `expansion_probability`, `gamma_zone`

Value mapping (already used elsewhere — keep consistent): `regime` is stored as `LONG_GAMMA` /
`SHORT_GAMMA` / `NO_FLIP` and is displayed as `POSITIVE_γ` / `NEGATIVE_γ` / `MIXED`.

---

## 4. THE HERO PANEL — construction

A single composed chart. Shared x-axis = `as_of_date` (settled sessions, oldest → newest), with the
**live session appended at the right edge** as a visually distinct "today" marker.

### Layer 1 — Price (the spine)

- Line of `eod_spot` across the settled series. This is the reference everything else is read against.
- Right-most point: today's **live** `gamma_metrics.spot`, drawn as a distinct marker (see §5 —
  live styling). Connect it to the settled line with a dashed segment to signal "this is not settled
  yet."

### Layer 2 — Clock 2 (the cycle) — the x-axis is *segmented*, not continuous

This is the visual idea that makes the panel work:

- Draw a **vertical divider at every cycle rollover** (where `front_expiry` changes). The chart is now
  visibly cut into expiry cycles.
- Label each cycle segment with its expiry date and, on the current (right-most) segment, the live
  **`dte` countdown**.
- Within each segment, render `cycle_oi_call_put_asym` as a **filled area** on a secondary axis
  centered at zero:
  - **positive (call-heavy → ceiling building)** fills **upward**, in the "resistance" hue;
  - **negative (put-heavy → floor building)** fills **downward**, in the "support" hue.
  - NULL → **gap in the fill** (the participant board was stale and abstained). Do not plot zero.
    A stale abstention and a genuine zero are different statements.
- The reader's takeaway per cycle: *"through this cycle, the room has been building a floor / a
  ceiling, and we are N days from expiry."*

### Layer 3 — Clock 1 (the slow regime)

- `gex_regime_persistence_20d` as a **smooth line on its own [0,1] axis**, drawn *under* the price
  spine as a low-contrast ribbon or subdued line — it is context, not the headline.
- Because it is slow, it should look slow: no markers, no emphasis, just a drifting band.
- Annotate the current value with a plain-language chip:
  - ≥ 0.70 → `PERSISTENT LONG-γ` (caged / mean-reverting)
  - ≤ 0.30 → `PERSISTENT SHORT-γ` (trending / amplifying)
  - otherwise → `MIXED-γ`
- Add a small directional arrow from `max_gamma_strike_drift_5d`: ↑ if > 0, ↓ if < 0, → if ≈ 0.
  Label: "magnet drifting up/down".

### Layer 4 — Divergence markers (the loud thing)

- On any settled session where `lens_alignment = 'DIVERGENT'`, place a **marker on the price line**
  in the alert hue.
- Hovering it shows `session_prior`.
- **A run of consecutive DIVERGENT sessions is the single most important pattern this panel can
  show** — the room has been disagreeing with itself for N days. If ≥ 2 consecutive DIVERGENT
  sessions end at the most recent settled session, surface a persistent inline callout above the
  chart:

      "LENSES DIVERGENT — N consecutive sessions. Conviction reduced; the room is changing."

  If there is no such run, show nothing. **Silence is healthy** (ADR-017).

### Layer 5 — Clock 3 (live), at the right edge

A compact vertical "now" rail at the right of the chart, clearly separated from the settled series:

- live `spot` marker on the price axis
- `flip_level` as a horizontal reference line extending left across the chart (dashed) — it is the
  level the live session is trading around
- `max_gamma_strike` as a second horizontal reference (the magnet)
- a chip: live `regime` (mapped to `POSITIVE_γ`/`NEGATIVE_γ`/`MIXED`) + `dte` + `pin_risk_score`

**Intraday-drift check (keep the existing logic, relocate the surfacing):** if the live
`gamma_metrics.regime` (mapped) disagrees with the most recent settled `net_gex_regime`, show the
existing amber `INTRADAY DRIFT` banner — but now **inside the hero panel**, directly under the
Clock-3 rail, because that is where the contradiction is visible. The settled verdict is once-nightly;
when the live tape has already flipped, the operator must see it in the same glance.

### Interaction

- Hover any settled session → tooltip with: date, `eod_spot`, `dte`, `ambient_regime`,
  `lens_alignment`, `price_vs_breadth_div`, `cycle_oi_call_put_asym`, `gex_regime_persistence_20d`,
  and `session_prior`.
- Click a session → expand the Tier-2 drill-down **scoped to that session** (four-lens strip showing
  that day's values, and its `regime_conditional_note`).
- Default view: last ~2 expiry cycles. Allow zoom-out to the full series.

---

## 5. STYLING — settled vs live, and the honesty rule

Reuse the existing v5 design tokens (font scale, neutral palette, existing zone hues). Do not invent
a new palette. Two rules that are not negotiable:

1. **Settled data is solid. Live data is dashed / outlined.** Any pixel derived from
   `market_environment_snapshots` is settled fact. Any pixel derived from live `gamma_metrics` is
   provisional. The operator must be able to tell them apart without a legend.
2. **NULL is a gap, never a zero.** `cycle_oi_call_put_asym` is NULL when the participant board went
   stale and the lens *abstained*. Plotting that as 0 would render an abstention as "perfectly
   balanced OI", which is a lie. Break the fill.

Colour semantics, consistent with the rest of the app:
- support / floor / put-heavy → the existing bullish hue
- resistance / ceiling / call-heavy → the existing bearish hue
- divergence / drift → amber (the existing alert hue)
- Clock-1 ribbon → low-contrast neutral. It must not compete with price.

---

## 6. EMPTY / DEGRADED STATES

- Fewer than 3 settled sessions → render the price line only, with "trajectory building — N sessions".
  Do not render half a chart.
- `cycle_oi_call_put_asym` all-NULL across the window → hide the Clock-2 fill entirely and note
  "participant board unavailable". Do not render an empty axis.
- `regime_conditional_note` containing "insufficient N" → render it verbatim, muted. It is *correct*
  for the engine to say it does not know yet. Do not hide it and do not dress it up as a statistic.
- No live `gamma_metrics` row (pre-open / post-close) → omit the Clock-3 rail, keep the settled
  series, and label the panel "settled through <date>".

---

## 7. ACCEPTANCE CRITERIA

1. Home opens to: verdict line, then the trajectory panel. Nothing else competes above the fold.
2. The price line, the cycle dividers, and the Clock-2 fill share one x-axis and are read together.
3. Cycle dividers land exactly on `front_expiry` changes; the current cycle shows a live `dte`.
4. `cycle_oi_call_put_asym` fills up for positive, down for negative, and **gaps** on NULL.
5. Clock-1 persistence renders as a slow, low-contrast band with a plain-language chip.
6. DIVERGENT sessions are marked on the price line; a ≥2-session run produces the callout; no run
   produces silence.
7. Settled and live are visually unmistakable.
8. The symbol toggle switches the whole panel (NIFTY ↔ SENSEX) — note the two symbols have
   *different* front expiries, so the cycle dividers move.
9. Four-lens strip, expiry memory, and open-shift callout are all still reachable, below the hero.
10. No new tables, views, or write paths.

---

## 8. DEPLOY

Standard meridian-connect pipeline. After Lovable pushes to GitHub, on the AWS box:
`cd ~/meridian-connect && git pull && npm run build && sudo rsync -av --delete dist/ /var/www/marketview/`

---

## 9. WHY THIS PANEL IS THE PRODUCT

Every GEX dashboard shows a snapshot. What separates MERDIAN is knowing **how the room got here**:
that dealers have been persistently long gamma for three weeks (Clock 1), that this cycle the room has
been quietly building a put floor since Monday (Clock 2), and that this morning the tape flipped short
gamma anyway (Clock 3). Any one of those is a fact. Together they are a *decision*: the cage held for
weeks, the floor is real, and the flip is either a fakeout inside a fortress or the first crack.

That is the read this panel exists to make possible in one glance. Build it so the divergence is the
thing the eye lands on.
