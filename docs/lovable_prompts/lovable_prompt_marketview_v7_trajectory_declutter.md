# Lovable Prompt — Marketview v7: Ambient Trajectory, Decluttered + Multi-Timeframe

**Target repo:** `balannavin-cyber1/meridian-connect`
**Builds on:** v6 (`AmbientTrajectory.tsx`, `Home.tsx`, `queries.ts` — already shipped)
**Scope:** fix one data bug, then restructure the hero panel from a single overloaded canvas into
three stacked lanes with a timeframe switcher.
**Session:** S68.

---

## 0. FIX THIS FIRST — the verdict card is rendering a stale row

The settled-series query returns rows **ascending by `as_of_date`** (oldest → newest). The
AMBIENT VERDICT card and the FOUR LENS STRIP are currently reading **`data[0]`** — the *oldest* row
in the window — while the Clock-1 chip correctly reads the *last*.

Observed live: the verdict reads `AS-OF 2026-06-19 close → FOR 2026-06-22 session` and the lens strip
shows `OI CYCLE ASYMMETRY 0.0362` (a 06-19 value), while the newest settled session is **2026-07-10**
(`cycle_oi_call_put_asym = -0.0972`). The whole top of the page is three weeks stale.

**Fix:** every "current ambient state" reader — verdict regime, lens alignment,
`regime_conditional_note`, the four-lens strip, the as-of/for-session line — must read the row with
the **maximum `as_of_date`** (i.e. the LAST element of the ascending array, not the first).

Define it once and reuse it:

    const settled = rows;                          // ascending by as_of_date
    const latest  = settled[settled.length - 1];   // ← the current ambient state
    const prev    = settled[settled.length - 2];

Do not sprinkle `[0]` / `.at(-1)` decisions across components. One `latest` at the top of Home,
passed down.

---

## 1. THE PROBLEM WITH v6

v6 is correct but unreadable. Three specific causes:

1. **Fixed axes on data that doesn't use them.** `cycle_oi_call_put_asym` is plotted on a hard
   `[-1, +1]` axis, but the real data lives in roughly `[-0.15, +0.11]`. It renders as a flat smear
   hugging zero. Same for `gex_regime_persistence_20d`: real range across the window is ~`0.50–0.85`,
   plotted on `[0, 1]` — a dead grey line.
2. **Four different scales on one canvas.** Price (~24,000), asymmetry (±0.15), persistence (0–1), and
   live reference lines all share one plot area. Price wins by magnitude; everything else becomes
   background texture.
3. **No timeframe.** The three clocks run at three different speeds, but the panel shows exactly one
   window. A multi-week positioning arc and an intra-week cycle build cannot be read at the same zoom.

Also: the `+1 ceiling` / `-1 floor` axis labels are colliding with the price axis labels, and the
legend is a four-item run-on sentence.

---

## 2. THE RESTRUCTURE — stacked lanes, one shared x-axis

Replace the single composed chart with **three vertically stacked lanes** sharing one x-axis and one
set of cycle dividers. Each lane owns its own y-scale and **autoscales to its observed data range**
(with a small pad), never to a theoretical range.

    ┌──────────────────────────────────────────────────────────────┐
    │  PRICE           eod_spot · settled solid · live NOW dashed   │   ~180px
    │  · divergence markers sit ON this line                        │
    ├──────────────────────────────────────────────────────────────┤
    │  CLOCK 2 · CYCLE   cycle_oi_call_put_asym, zero-centred       │   ~90px
    │  · fills up = ceiling (call-heavy) · down = floor (put-heavy) │
    │  · NULL = gap                                                 │
    ├──────────────────────────────────────────────────────────────┤
    │  CLOCK 1 · REGIME  gex_regime_persistence_20d                 │   ~70px
    │  · slow band, autoscaled to observed range                    │
    └──────────────────────────────────────────────────────────────┘
      ↑ vertical cycle dividers (front_expiry changes) run through ALL three lanes

**Rules:**

- **Autoscale every lane.** Clock-2's axis is `[-max(|asym|)·1.2, +max(|asym|)·1.2]` over the visible
  window, not `[-1, 1]`. Clock-1's axis is `[min−0.05, max+0.05]` over the visible window, not `[0, 1]`.
  Keep a zero reference line on Clock-2 (it is the floor/ceiling divide and is meaningful); Clock-1
  needs no zero line.
- **One x-axis, at the bottom only.** Lanes 1 and 2 have no x labels.
- **Cycle dividers span all three lanes** as a single vertical rule, labelled once, at the top.
- **Divergence markers live only on the price lane.** Nowhere else.
- Drop the inline legend paragraph. Each lane gets a small left-hand label instead
  (`PRICE`, `CLOCK 2 · CYCLE`, `CLOCK 1 · REGIME`) plus a one-line hint in muted type.
- Remove the `+1 ceiling` / `-1 floor` axis text. Label the Clock-2 lane's positive/negative halves
  with a single small `ceiling ▲` / `floor ▼` at the axis extremes instead — no collision with price.

Total panel height should be **smaller** than v6's single chart, not larger. The gain is legibility,
not real estate.

---

## 3. THE TIMEFRAME SWITCHER — each view promotes one clock

This is the core new idea. The three clocks run at three speeds, so give each one a view where it is
the protagonist. A segmented control at the panel's top-right:

    [ MONTH ]  [ CYCLE ]  [ WEEK ]

### MONTH — Clock 1 leads (positioning regime)

- Window: the full available settled series (target ~60 sessions; will be shorter until backfilled).
- **Lane order flips: CLOCK 1 becomes the TOP and TALLEST lane (~160px), price drops to ~120px,
  Clock 2 shrinks to ~60px.**
- Clock-1 rendered as the hero: the persistence band, prominent, with the plain-language chip
  (`PERSISTENT LONG-γ` ≥0.70 / `PERSISTENT SHORT-γ` ≤0.30 / `MIXED-γ`) and the magnet-drift arrow.
- Cycle dividers still drawn, but muted — at this zoom they are texture, not the point.
- The read: *"dealers have been persistently long gamma and getting more so — the cage is tightening
  over weeks."*

### CYCLE — Clock 2 leads (cycle-so-far) — **this is the DEFAULT**

- Window: last ~2 expiry cycles.
- Lane order as in §2 (price top, Clock 2 middle, Clock 1 bottom), but **Clock 2 gets the emphasis**:
  full-saturation fill, bold divider labels, live `dte` countdown on the current segment.
- The read: *"through this cycle the room has been building a floor, and we are 4 days out."*

### WEEK — Clock 3 leads (the live session against its cycle)

- Window: **current expiry cycle only** (from the last cycle rollover to today), daily granularity,
  plus the live session.
- Price lane expands (~220px) and the live Clock-3 furniture becomes prominent: `flip_level` and
  `max_gamma_strike` as horizontal reference lines **across the whole lane**, live spot marker, and the
  pin-zone band shaded.
- Clock 2 stays (it is *this* cycle's build — highly relevant at this zoom).
- Clock 1 collapses to a **single chip**, not a lane — at one week's zoom it does not move.
- Show the intraday-drift banner here if live regime ≠ latest settled `net_gex_regime`.
- The read: *"the floor built this cycle sits at X; the tape is trading above the flip and pinning."*

**State:** remember the selected timeframe (component state is fine; no persistence needed).
**Default: CYCLE.**

---

## 4. DECLUTTER THE REST OF HOME

- **Verdict card:** keep, but tighten. One line: `ACCUMULATION · ALIGNED · as-of 10 Jul → for 13 Jul`,
  with `regime_conditional_note` beneath in muted type. Drop the oversized `REGIME` / `LENS ALIGNMENT`
  column headers — the values are self-describing.
- **Live stat bar** (SPOT / NET Γ / MAX Γ / MAX PAIN / PIN SCORE / VIX / EXPIRY): keep exactly as is.
  It is dense but it is *reference*, not analysis, and it earns its line.
- **Drill-down:** keep the tab strip (Four Lenses / Expiry Memory / Key Parameters / Net γ Intraday).
  Default **collapsed**. It is already correct — just make sure the Four Lenses strip now reads
  `latest`, not `data[0]` (§0).

---

## 5. STYLING — unchanged rules, restated

- Settled = solid. Live = dashed/outlined. Never conflated.
- NULL `cycle_oi_call_put_asym` = **gap in the fill**, never zero. A stale participant board *abstained*;
  rendering it as 0 would state "perfectly balanced OI", which is false.
- Support/floor/put-heavy → bullish hue. Resistance/ceiling/call-heavy → bearish hue.
  Divergence/drift → amber. Clock-1 → low-contrast neutral.
- Reuse existing v5/v6 tokens. No new palette.

---

## 6. ACCEPTANCE CRITERIA

1. Verdict card, as-of/for line, and four-lens strip all read the **newest** settled row
   (`as_of_date` max). Verify: with data through 2026-07-10 the card must say `as-of 10 Jul`, not
   `19 Jun`, and OI cycle asymmetry must read `-0.0972`, not `0.0362`.
2. Three stacked lanes, one shared bottom x-axis, cycle dividers spanning all lanes.
3. Every lane autoscales to observed range. The Clock-2 fill must visibly move (it ranges ~±0.15) and
   the Clock-1 band must visibly rise across the window (~0.50 → 0.85). Neither may render flat.
4. Timeframe switcher `MONTH / CYCLE / WEEK` works; each reorders/resizes lanes as specified;
   default is CYCLE.
5. WEEK view shows only the current expiry cycle and promotes the live Clock-3 furniture.
6. MONTH view promotes Clock 1 to the top and tallest lane.
7. No axis-label collisions. No inline legend paragraph.
8. Total hero height ≤ v6's chart height.
9. NULL asym still renders as a gap.
10. Symbol toggle still switches everything (NIFTY/SENSEX have different expiries → dividers move).

---

## 7. NOTE ON DATA DEPTH

The settled series is currently ~15 sessions (~3 expiry cycles). **CYCLE** and **WEEK** are fully
usable today. **MONTH** will look thin until the series is backfilled deeper — handle a short series
gracefully (render what exists, label `N sessions`), do not assume 60 points.
