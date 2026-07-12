# Lovable Prompt — Marketview v8: Ambient Trajectory polish

**Target repo:** `balannavin-cyber1/meridian-connect`
**Builds on:** v7 (`AmbientTrajectory.tsx` — stacked lanes + MONTH/CYCLE/WEEK, already shipped)
**Scope:** three fixes. Nothing structural — v7's architecture is correct and stays.
**Session:** S68.

v7 is working: the verdict reads the newest settled row, the lanes autoscale, the clocks are legible,
and MONTH/CYCLE/WEEK each promote the right clock. These are the three things still wrong.

---

## FIX 1 — WEEK is degenerate immediately after a cycle rollover

**Observed:** with SENSEX selected, WEEK renders only *"trajectory building — 1 settled session in week
window"*. SENSEX's expiry cycle rolled over on 2026-07-09, so the current cycle contains exactly one
settled session (07-10). NIFTY, mid-cycle, shows three. Every Monday — and every Thursday for SENSEX —
WEEK will be near-empty for one or both symbols.

This is a flaw in the v7 spec, not in the implementation: scoping WEEK to *strictly* the current cycle
guarantees an unusable view right after every rollover, which is precisely when an operator most wants
to see what the last cycle did.

**Fix — floor the window:**

- If the current expiry cycle has **≥ 4 settled sessions**, show only the current cycle (v7 behaviour,
  unchanged).
- If it has **< 4**, extend the window backwards into the **previous cycle** until at least 6 settled
  sessions are in view.
- Sessions belonging to the **previous** cycle render **dimmed / desaturated** (roughly 40% opacity) so
  the current cycle still reads as the subject. The cycle divider between them stays fully visible — it
  is the boundary that gives the dimming its meaning.
- The lane subtitle should say which case applies, e.g.
  `this cycle (1 session) · prior cycle shown for context` — or, when the cycle is full, just
  `this cycle · 5 sessions`.

The point: WEEK must never render an empty or one-point chart. It always shows a readable stretch, with
the current cycle visually foregrounded.

---

## FIX 2 — axis-label collisions

Three specific overlaps, all caused by lane labels and axis ticks being drawn in the same space:

1. **MONTH:** the Clock-1 y-axis tick (`45%`) collides with the price y-axis tick (`24,489`) where the
   two lanes meet.
2. **MONTH / CYCLE:** the `90%` and `63%` Clock-1 ticks sit hard against the lane boundary.
3. **WEEK:** the `PRICE` lane label and its subtitle are drawn *on top of* the `flip 24,49x` dashed
   reference line and its label.

**Fix:**

- **Lane titles go inside the lane, top-left, with padding** — not floating over the plot area, and
  never in the same band as an axis tick. Give each lane a small header strip (~18px) that the plot
  area does not draw into.
- **Y-axis ticks: 2 per lane, maximum** (min and max of the autoscaled range). More than that is noise
  at these lane heights, and it is what is causing the collisions.
- **Reference-line labels** (`flip`, `max γ`) right-align at the plot edge and must not overlap the
  lane header strip. If a reference line falls within the header band, drop its label to just below the
  line.
- Add ~8px vertical padding between lanes so nothing from one lane bleeds into the next.

---

## FIX 3 — MONTH: the Clock-2 lane is clipped at the bottom

In MONTH view the Clock-2 fill runs off the bottom of its lane and collides with the x-axis date
labels (`19 Jun`, `24 Jun`, ...).

**Fix:** reserve the x-axis label band (~24px) below the last lane and exclude it from the Clock-2
plot area. The Clock-2 lane's autoscaled range must fit entirely within its own lane box. No lane may
draw into the x-axis band.

---

## ACCEPTANCE

1. WEEK with SENSEX selected (cycle rolled 07-09) shows **≥ 6 settled sessions**, with the prior
   cycle dimmed and the divider visible. It must never say "1 settled session".
2. WEEK with NIFTY (mid-cycle, ≥4 sessions) is unchanged from v7.
3. No overlapping text anywhere, in any of the three views, for either symbol. Check specifically:
   the Clock-1/price axis boundary in MONTH, and the PRICE lane label vs the flip line in WEEK.
4. In MONTH the Clock-2 fill sits entirely inside its lane; x-axis date labels are clear of it.
5. Max 2 y-ticks per lane.
6. Everything else from v7 — autoscaling, lane order per timeframe, divergence markers on price only,
   NULL-as-gap, settled-solid/live-dashed — unchanged.

---

## NOTE

The settled series is being backfilled deeper (target ~45 sessions) in the same session as this build,
so MONTH will thicken. Early sessions may carry **NULL `cycle_oi_call_put_asym`** (the participant-OI
feed started later than the gamma feed) — those must continue to render as **gaps** in the Clock-2
lane, never as zero. A long gap on the left of MONTH's Clock-2 lane is correct and expected.
