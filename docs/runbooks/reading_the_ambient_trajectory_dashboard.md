# Reading the MERDIAN Home Dashboard — Ambient Trajectory

**A card-by-card guide for someone seeing this screen for the first time.**

| Field | Value |
|---|---|
| Document | `docs/runbooks/reading_the_ambient_trajectory_dashboard.md` |
| Covers | Marketview **Home** page (v9), `https://marketview.meridianalpha.in` |
| Type | Reader's guide — what each element means, how to read it, what to do with it |
| Written | Session 68 (2026-07-12), on the ENH-116 Objective 1 ship |
| Governing | ENH-116 (four lenses, three clocks, expiry memory) · ADR-017 (console design) · ADR-002 v2 (market-structure philosophy) · ADR-015 (GEX-as-context-not-gate) |

---

## 0. Before anything else: what this screen is *for*

Every options dashboard on the internet shows you a **snapshot**: net gamma right now, max pain right now, pin risk right now. Those are facts, and MERDIAN has them too (they're in the top bar and the drill-down).

But a snapshot cannot answer the question an options trader actually has at 9:15 in the morning, which is:

> **"Is what I'm looking at *stable*, or is it *changing*?"**

A pin at 24,300 means something completely different if dealers have been persistently long gamma for three weeks (the pin is a fortress) versus if the gamma regime flipped last Tuesday and the room has been quietly buying puts ever since (the pin is about to fail).

**Same number. Opposite trade.** The difference is not in the snapshot — it is in the *trajectory*.

That is what this screen exists to show, and it is the one thing that separates MERDIAN from a GEX dashboard.

### One critical framing before you read a single number

**This screen does not tell you what to do.** It is *display-not-gate* (ADR-015, ADR-002 v2 §D.19.3). It does not emit signals, it does not size positions, it does not gate entries. It describes the environment; **the operator is the integration layer.** Anyone who reads a colour on this page and puts on a trade because of it has misunderstood the product.

---

## 1. The three clocks (read this section or nothing else will make sense)

MERDIAN models the market environment as **three clocks running at three different speeds.** Everything on the hero panel is one of these three, or price, or the divergence between them.

| Clock | Speed | Question it answers | Where it comes from |
|---|---|---|---|
| **Clock 1 — Positioning Regime** | **Weeks.** Turns slowly. | *"What kind of market is this, structurally?"* Have dealers been persistently long gamma (a caged, mean-reverting market) or short gamma (a trending, amplifying one)? | `gex_regime_persistence_20d` — the fraction of the last 20 sessions that closed net-long-gamma. Range 0–1. |
| **Clock 2 — Cycle-So-Far** | **Days.** Resets every expiry. | *"What has the room been building **this cycle**?"* Since Monday, has open interest been accumulating on the call side (a ceiling) or the put side (a floor)? And how far into the cycle are we? | `cycle_oi_call_put_asym` (magnitude) + `front_expiry` (position). |
| **Clock 3 — Session** | **Minutes.** Live. | *"What is the tape doing **right now**?"* Where is spot relative to the flip level and the gamma magnet? Is it pinning? | Live `gamma_metrics` — flip level, max-γ strike, pin score. |

**The product is the three clocks read *together*, over price.**

- **When the clocks agree** → the structure is coherent. A pin is a real pin. A trend is a real trend.
- **When the clocks disagree** → *the room is changing.* This is the single most valuable thing on the screen, and the panel is built to make it the thing your eye lands on.

A worked example, which is exactly what the panel is designed to let you say in one glance:

> *"Dealers have been persistently long gamma for three weeks (Clock 1 — the cage is tight). This cycle the room has been quietly building a put floor since Monday (Clock 2). But this morning the tape flipped short gamma anyway (Clock 3)."*

Any one of those is a fact. Together they are a **decision**: the cage held for weeks, the floor is real, so the flip is either a fakeout inside a fortress — or the first crack in it. That read is what this screen exists to make possible.

---

## 2. Card by card, top to bottom

### 2.1 — The Live Stat Bar

```
● LIVE   SPOT 24,203.5   NET Γ +8,53,161.79 Cr   MAX Γ 24,300   MAX PAIN 24,200
         +240.7 (+1.00%)                          +0.4%          +0.0%
         PIN SCORE 47/100   VIX 12.24   EXPIRY 14 Jul (4d 0h)
```

**What it is:** live reference. Not analysis — *reference*. It is dense on purpose and it earns its single line.

| Field | How to read it |
|---|---|
| **SPOT** | Live index level + change from previous close. |
| **NET Γ** | Net dealer gamma exposure, in ₹ crore. **Positive = dealers are long gamma = they dampen moves** (they sell into strength, buy into weakness → mean reversion). **Negative = dealers are short gamma = they amplify moves** (they chase → trends and cascades). This sign is the single most important number in the bar. |
| **MAX Γ** | The strike with the largest gamma concentration — **the magnet.** Price is structurally attracted to it while dealers are long gamma. |
| **MAX PAIN** | The strike at which the most options expire worthless. A weaker, older concept than MAX Γ; kept for reference and cross-checking. |
| **PIN SCORE** | 0–100. How strongly the structure is pinning price to the max-γ strike. High = caged. |
| **VIX** | India VIX. Context for whether options are cheap or expensive. |
| **EXPIRY** | Front expiry + a live countdown. **NIFTY and SENSEX have different expiries** — this changes when you flip the symbol toggle. |

> **New-reader trap:** `NET Γ` positive is *not* "bullish." It is "dampening." Gamma sign tells you the market's **behaviour** (mean-reverting vs trending), never its **direction**. Direction comes from the lenses below.

---

### 2.2 — The Ambient Verdict (one line)

```
ACCUMULATION  ·  ALIGNED  ·  as-of 10 Jul → for 13 Jul
WEEKLY ACCUMULATION/ALIGNED: insufficient N (N=1)
```

**What it is:** the engine's one-line read of the *settled* environment. Computed once nightly at 21:30 IST from the completed session, and keyed to the **next** session — hence `as-of <settled day> → for <next session>`.

**First value — the regime.** One of six:

| Regime | Meaning |
|---|---|
| **ACCUMULATION** | Buyers are quietly building, in a dampening (long-γ) environment. |
| **DISTRIBUTION** | Sellers are quietly building, in a dampening environment. |
| **TREND_UP** | Bullish *and* the gamma environment amplifies (short-γ). Moves extend. |
| **TREND_DOWN** | Bearish *and* amplifying. Cascades are possible. |
| **RANGE** | No directional conviction, long-γ cage. Fade the edges. |
| **UNSTABLE** | The lenses disagree. **Reduce conviction.** |

**Second value — the alignment.** `ALIGNED` or `DIVERGENT`. This is the divergence flag: do the directional lenses (breadth and participant positioning) *agree* with each other?

> **How the verdict is actually built** (worth knowing, because it is not obvious): the **directional** lenses are **breadth** and **participant positioning**. Their agreement is the conviction; their opposition is the divergence. **Gamma is not a direction** — it is the *amplification modifier* (short-γ turns a lean into a trend; long-γ turns it into accumulation/distribution). If the participant board is stale, Lens 3 **abstains** rather than tilting on old data (ADR-018 D2), and the verdict degrades gracefully to breadth + gamma.

**Third line — the base-rate receipt.** *"Historically, when the environment looked like this going into a weekly expiry, what happened?"*

Right now it reads **`insufficient N (N=1)`**, and **that is correct behaviour, not a bug.** The honest answer is that we do not have enough labelled expiries yet to quote a rate. The engine is designed to say "I don't know" rather than to dress up one observation as a statistic. It will start quoting real base rates when N clears the floor (8), and that happens only through forward accrual — one expiry at a time.

---

### 2.3 — THE HERO: Ambient Trajectory (three clocks over price)

This is the screen. Everything else is supporting cast.

#### The timeframe switcher — `MONTH · CYCLE · WEEK`

Three clocks run at three speeds, so they cannot share one zoom. **Each timeframe promotes one clock to protagonist and lets the other two recede.** The timeframe selector is really a *clock* selector:

| View | Window | Which clock leads | Use it to ask |
|---|---|---|---|
| **MONTH** | Full settled history (~44 sessions today) | **Clock 1** — becomes the top and tallest lane | *"What kind of market has this been, structurally, over weeks?"* |
| **CYCLE** *(default)* | Last ~2 expiry cycles | **Clock 2** — the cycle build | *"What has the room been building this cycle, and how long do I have?"* |
| **WEEK** | Current expiry cycle (floored to ≥6 sessions) | **Clock 3** — live session furniture | *"Where is the tape sitting inside the structure this cycle built?"* |

#### Lane 1 — PRICE

The settled daily close (`eod_spot`) as a solid line — this is the spine everything else is read against.

- **The `NOW` marker at the right edge** (hollow circle, **dashed** connector) is **live**, not settled. The dashing is deliberate and it is a hard rule of this panel: **settled data is solid, live data is dashed.** They must never be visually conflated, because one is fact and the other is provisional.
- **Orange dots on the price line = `DIVERGENT` sessions.** Days when the lenses disagreed. Hover one to see that day's plain-language read.
- **In WEEK view**, two horizontal reference lines appear: `flip` (the gamma flip level — the boundary between the dampening and amplifying regimes) and `max γ` (the magnet). Where price sits relative to these two lines *is* the session's structural position.

#### Lane 2 — CLOCK 2 · CYCLE

`cycle_oi_call_put_asym`, plotted as a filled area centred on zero.

- **Fills UP (red) = call-side building = a CEILING forming.**
- **Fills DOWN (green) = put-side building = a FLOOR forming.**
- Formula: `(call OI − put OI) / (call OI + put OI)` across the **total NSE index-option participant board.** Range roughly ±0.15 in practice.
- **A gap in the fill is NOT zero.** It means the participant board was **stale** that day and the lens **abstained** (ADR-018 D2). Drawing it as `0.0` would assert "perfectly balanced OI" — a measurement that never happened. **NULL is a gap, never a zero.** This is a lie the panel deliberately refuses to tell.

#### The vertical cycle dividers

**This is the design idea that makes Clock 2 legible.** Dashed vertical lines cut the chart at every **expiry rollover** (wherever `front_expiry` changes). The chart is therefore not a continuous timeline — it is **segmented into expiry cycles**, because that is how OI actually behaves: it accumulates through a cycle and **resets at expiry**.

Without the cuts, the OI asymmetry is a meaningless squiggle. With them, each segment reads as a sentence: *"through this cycle, the room built a floor, and we are 4 days out."*

The current (right-most) segment shows a live **`dte` countdown**.

#### Lane 3 — CLOCK 1 · REGIME

`gex_regime_persistence_20d` — a slow, low-contrast band. It is context, not headline, and it is styled to look slow because it *is* slow.

Below the chart, the plain-language chip:

```
Clock 1 · PERSISTENT LONG-γ (caged) · 85%    ↓ magnet down (-60.0 pts/session)
```

| Reading | Meaning |
|---|---|
| **≥ 70% — `PERSISTENT LONG-γ`** | Dealers have been long gamma most of the last 20 sessions. **A caged, mean-reverting market.** Pins hold. Breakouts fail. Fade the edges. |
| **≤ 30% — `PERSISTENT SHORT-γ`** | Dealers have been short gamma. **A trending, amplifying market.** Moves extend. Cascades happen. Do not fade. |
| **31–69% — `MIXED-γ`** | No stable regime. Lower conviction. |

The **magnet arrow** (`max_gamma_strike_drift_5d`, in index points per session) says whether the gamma magnet is drifting up or down — a slow, structural directional tell independent of price.

#### The `LIVE · CLOCK 3` chip (right edge)

```
LIVE · CLOCK 3
POSITIVE_γ
4d · pin 47
```

The live session's regime, days to expiry, and pin score. Visually separated from the settled series because it is a *different kind of thing*.

**If the live regime disagrees with the latest settled regime**, an amber **`INTRADAY DRIFT`** banner appears here. That matters because the settled verdict is computed **once, nightly** — so if the tape flipped this morning, the headline above is *already stale* and you must know that in the same glance.

---

### 2.4 — The Drill-Down (collapsed by default)

Four tabs, one click away. They were the old Home page; they are now supporting evidence.

| Tab | What it holds | When you want it |
|---|---|---|
| **Four Lenses** | The four raw lens values behind the verdict: `NET GEX REGIME`, `PRICE VS BREADTH` (CONFIRM / BULLISH_DIV / BEARISH_DIV), `OI CYCLE ASYMMETRY`, `FII 5D Δ FUT L/S`, `PRO OPTIONS IMBALANCE`. | When you don't trust the verdict and want to see its receipts. **`PRICE VS BREADTH` is the top-tier tell** — price up while breadth deteriorates (`BEARISH_DIV`) is distribution. |
| **Expiry Memory** | Base rates: historically, at this regime + alignment + expiry type, how often did price PIN vs BREAK? | When sizing an expiry-day view. **Currently N-starved — it will say so honestly.** |
| **Key Parameters** | The live structural levels: `FLIP LEVEL`, `MAX Γ STRIKE`, `PIN ZONE`, `ACCEL ZONE`, `SPOT CONTEXT` (σ range), net dealer γ with its dampening/amplifying split. | **This is where you get actual levels to trade around.** The `ACCEL ZONE` is where short-gamma hedging accelerates moves — the danger/opportunity band. |
| **Net γ Intraday** | Net dealer gamma through the session, Rising / Falling / Flat, with the Σ-dampening vs Σ-amplifying split. | When you want to know if the structure is *strengthening or decaying* intraday. |

---

## 3. How to actually read the screen (three recipes)

### Recipe 1 — The morning read (60 seconds)

1. **Verdict line.** Regime + ALIGNED/DIVERGENT. This frames everything.
2. **Clock 1 chip.** Caged or trending? This tells you *what kind of trade is even available today.*
3. **CYCLE view, Clock-2 lane.** Floor or ceiling building this cycle? How many days left?
4. **Clock-3 chip + INTRADAY DRIFT.** Has the tape already contradicted the settled read?
5. **Key Parameters tab.** Grab the flip level, max-γ strike, and accel zone. Those are your levels.

### Recipe 2 — "Is this pin real?"

- Clock 1 says `PERSISTENT LONG-γ` (≥70%) → **the cage is structurally sound.**
- Clock 2 shows OI building **against** the direction of any breakout attempt → **the pin has support.**
- Clock 3 shows spot **inside** the pin zone with a high pin score → **it is holding right now.**
- **All three agree → the pin is fortress-grade.** Fade the edges.
- **Any one disagrees → reduce size.** The most dangerous configuration is a high pin score (Clock 3 says "pinning!") sitting on top of a *collapsing* Clock 1 — a cage that is quietly rusting.

### Recipe 3 — The divergence read (the one that pays)

Look for **orange dots clustering** on the price line, and for the persistent callout:

```
LENSES DIVERGENT — N consecutive sessions. Conviction reduced; the room is changing.
```

**A run of ≥2 consecutive DIVERGENT sessions is the highest-value pattern this panel can show.** It means the directional lenses have been contradicting each other for days — breadth saying one thing, the participant board saying another. Structurally, the room is repositioning and the current regime label is losing its grip.

If there is **no run, the panel says nothing.** That is deliberate: **silence is healthy** (ADR-017). An empty callout area means the structure is coherent. Do not go looking for a signal that isn't there.

---

## 4. What you should NOT conclude from this screen

- ❌ **It is not a signal.** No entry, no exit, no size. Display-not-gate, by design and by ADR.
- ❌ **Gamma sign is not direction.** `POSITIVE_γ` means *dampening*, not *bullish*.
- ❌ **A gap in Clock 2 is not "balanced OI."** It is "we didn't have the data, so we didn't guess."
- ❌ **`insufficient N (N=1)` is not a broken panel.** It is the engine refusing to quote a statistic it hasn't earned.
- ❌ **The settled verdict is not live.** It is computed once nightly. The `INTRADAY DRIFT` banner exists precisely because it can go stale within hours.

---

## 5. Honest limitations (as of S68)

A new reader should know exactly where the edges are:

| Limitation | Detail |
|---|---|
| **Lens 4 (macro) is NULL** | USDINR / crude / gold are specced but no feed is wired. `macro_tilt` is empty. The verdict is a **three-lens** verdict today, not four. |
| **Base rates are N-starved** | Real N ≈ 1 per regime cell. The historical seed (pre-S64) is **degenerate by construction** — every seeded row is `RANGE/ALIGNED` with NULL lenses, because the backfiller had no breadth or participant data. Genuine base rates accrue **forward only**, one expiry at a time. Expect `insufficient N` for a while yet. |
| **History is 44 sessions** | 2026-05-08 → 2026-07-10. Enough for ~9 expiry cycles and a real Clock-1 arc, but this is a young series. |
| **Clock 2 is once-nightly** | It reflects the *settled* participant board. It does not move intraday. |
| **The divergence-run callout has never fired live** | The DIVERGENT sessions in the current history are scattered, not consecutive. The first live ≥2-session run is an event worth studying. |

---

## 6. Why this matters (the one-paragraph version)

Every GEX dashboard shows a snapshot: here is net gamma, here is max pain, here is the pin. What none of them can tell you is **how the room got here** — whether the pin you're looking at is the product of three weeks of persistent dealer length (a fortress) or the last gasp of a regime that broke a fortnight ago and has been bleeding ever since (a trap). The three clocks, plotted over price with their disagreements marked, are the answer to that question. When they agree, trade the structure with confidence. When they disagree, the room is changing — and the divergence is the trade.

---

*Written Session 68, 2026-07-12, on the ENH-116 Objective 1 ship. Update this guide whenever the Home page changes shape or a new lens goes live (Lens 4 macro, ENH-118 vol-regime).*
