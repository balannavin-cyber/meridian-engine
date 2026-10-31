# parity_target_render_study.md — how the parity target treats, renders and presents each layer

**Session:** S84 (parallel research) · **Captured:** 2026-09-25, 10:55–11:15 IST · **Status:** COMPLETE (A–F)
**Scope:** research only — no code, no SQL, no database, nothing in production.
**Source:** the parity target's public site. The base URL is recorded in the S84 brief only; every path below is relative to it. The product is never named in this document.
**Governs:** the render/UI half of ADR-025 parity, feeding the whole-board design pass held by Amendment B1.
**Instruments:** text fetch of every page; the built-in browser at three widths (375 px phone emulation, ~800 px narrow, 1440 px desktop emulation); DOM and computed-style inspection for chart element types, colours, type and spacing tokens; scripted click-through of every tab, every one of the 49 guide values, and the landing sliders; manual hover on three panels. No sign-up, no login, no form submitted, no checkout.

**Dating rule.** Every finding in this document was observed on **2026-09-25** unless it says otherwise. The target is new and changing (its disclaimer is dated 21 Sep 2026). Nothing here should be read as a claim about the target on any other date.

**Evidence codes.**
- **A1·*panel*** — landing page, named panel.
- **A2·*Tab*/*VALUE*** — guide page, tab and value; the per-value detail panel.
- **A3·§n** — read-the-terminal section.
- **A4·§n** — disclaimer section.

"Described" means a rendered observation, not text. "Inferred" is always labelled, with its reason.

**Benchmark rule.** Every number on A1, A2 and A3 is illustrative or a sample snapshot. **No figure in this document is a benchmark**, and none should be compared against a MERDIAN value.

---

## A. Page inventory

All visits 2026-09-25. "Illustrative" means the page itself labels the figures as not live.

| # | path | gated | illustrative | fetched as | purpose (one line) |
|---|---|---|---|---|---|
| A1 | `/` | no | **yes** — every data panel carries "ILLUSTRATIVE · NOT LIVE DATA" | text + browser (375 / 800 / 1440) + DOM | Marketing landing: 13 panels demonstrating the layers, plus pricing and the feature list |
| A1a | `/#method` | no | n/a (copy only) | as A1 | Three claims: gamma density weighted by OI; pin/flip/walls recomputed each tick; real-time regime sign |
| A1b | `/#explorer` | no | yes | as A1 | Gamma explorer: net gamma by strike, a regime card, and level cards with one-line definitions |
| A1c | `/#layers` | no | yes | as A1 | Six-layer tab panel (GAMMA/VANNA/CHARM/DELTA/FLOWS/IV) with a DTE slider; all six tabs cycled |
| A1d | `/#pricing` | no | n/a | as A1 | Plans, and the list of what the terminal contains (incl. intraday replay, historical snapshots, 0DTE and weekly chains kept separate) |
| A2 | `/guide` | no | **yes** — "PRODUCTION SAMPLE SET · NOT LIVE", one BANKNIFTY monthly-expiry snapshot | text + browser + DOM; **all 7 tabs and all 49 values clicked and their detail panels extracted** | The closest public view of the terminal itself: status strip, tabs, value list + chart, and a detail panel per value |
| A3 | `/read-the-terminal/` | no | **yes** — its closing note says every pictured figure is an example | text + browser | Plain-language primer, §01–§12 (S83 recorded 01–11; **§12 is a glossary**) |
| A4 | `/disclaimer/` | no | n/a | text | Data sources, "models are estimates", availability, invite-only manual onboarding, refund rule tied to broker authentication. Dated 21 Sep 2026 |
| A5 | `/contact/` | no | n/a | text | Contact channels and hours; a form (**not submitted**) |
| A6 | `/terminal/` | **yes** — renders only "Checking session…" | — | text only; **not probed further** | The live product. Everything known about it comes from A1, A2, A3, A4 |
| A7 | `/sitemap.xml`, `/robots.txt` | — | — | text | Both **404**. No hidden public pages are discoverable this way |
| — | the target's X account, phone, email | — | — | **not visited** | Listed on A5 as the channel for daily gamma notes and expiry maps. Not the target's site; out of scope |

**What the public pages say about the gated terminal** (A1d, A2, A4):
- Every plan is the whole terminal; nothing is tiered.
- Access is invite-only and opened by hand; payment is by UPI.
- The refund window closes on **broker authentication**, which A4 §07 describes as the point where the terminal starts running against the user's own account. *Inferred, not stated:* the live terminal may source its data through the subscriber's broker connection.
- A2's IV tab says that tab "is live in the terminal".
- No alerts or notifications are mentioned anywhere on the public pages.

---

## B. Board-level findings

### B1. Information architecture — what the terminal is made of

From A2, the public view closest to the terminal:

1. **Status strip** — always on top, one row on desktop, a 2×4 grid on a phone. Eight cells, each a small grey label over a bold value:
   - **SYMBOL**
   - **EXPIRY**, with its class ("31 JUL · MONTHLY")
   - **SPOT**, with day % change
   - **REGIME** (a word, coloured)
   - **NET Γ** (₹ Cr, signed and coloured)
   - **HHI**, with its band word ("0.412 COMPRESSED")
   - **CORRIDOR** ("floor to ceiling")
   - **DTE · IV** ("5 · 13.2%")

   This strip **is the first-screen answer**: regime, its size, whether the levels can be trusted, where the edges are, and the yardstick inputs.
2. **Tab row** — seven tabs: **Overview · Pin · Gamma · Delta · OI · Flows · IV**. Each tab is one question.
3. **Tab body** — a card holding:
   - a title line ("OVERVIEW · BANKNIFTY · 31 JUL EXPIRY");
   - a sample/live badge;
   - a one-sentence purpose ("the four strikes that matter today");
   - a **value list** of 4–10 rows (label, a one-line subtitle, value right-aligned);
   - **one chart**;
   - **a one-line chart caption** that changes with the selected value.
4. **Detail panel** — below the tab card, full width. It explains the selected value in fixed slots: title, unit line, definition, COMPUTED, HOW TO READ, READ IT WITH, THE SCALE (three bands, one marked "YOU ARE HERE"), CAVEAT.
5. **Board index** — all 49 values filed "By question" (six questions) or "By reading" (well / mid / badly), with a text filter. Clicking any value jumps the readout to it.

The landing page (A1) is not the terminal. It is **one panel per concept**, each with its own interaction toy. It is the best evidence of which **forms** the target chose for each layer. The six-layer tab panel on A1 is placeholder art (see C).

### B2. Layout and proportion (described, measured from the DOM)

| width | status strip | tabs | body | detail panel |
|---|---|---|---|---|
| **1440 px** | one row, 8 cells | one row | **two columns:** value list ≈ 220 px, chart ≈ 980 × 426 px (chart ≈ **4.5×** the list width) | full width below |
| **~800 px** | wraps | wraps to 2 rows | stacked: list, then chart | below |
| **375 px** | **2 × 4 grid** | wraps to 2 rows (4 + 3) | stacked: list, then chart | below |

- **Hierarchy by size:** the chart is the largest element. The strip holds the densest information per pixel. The value list is the primary *control* (it drives the chart and the panel).
- **The landing hero** at 1440 px is two columns, copy left and chart right. On a phone it stacks.
- **No left nav and no sticky header** on the public pages (the header is `position: static`). Navigation is the top link bar plus the tabs. *(Whether the gated terminal has a shell is not observable.)*

### B3. Visual language — the presentation tokens

These are the target's **styling** choices. They are recorded so the design session can decide, not so we copy them. Every item in B3 is styling unless marked **substantive**.

- **Theme:** dark only; no light mode was seen. Page background ≈ `#09090B`, card background ≈ `#14161A`, hairline borders ≈ `#2C313A`.
- **Type:**
  - A **serif display face** (Newsreader, weight 300) for page headlines and for **big hero numbers** on the landing cards ("24,000", "Dampening", "+30 fut").
  - A **sans face** (Inter) for everything in the terminal view.
  - Numbers are **not** tabular or monospace (`font-variant-numeric: normal`).
- **Type scale in the terminal view (A2):**

  | element | size | weight / treatment | colour |
  |---|---|---|---|
  | strip labels | 9.5 px | tracked | grey `#6E7684` |
  | strip values | 15 px | 600 | — |
  | tab labels | 13.5 px | 600 | — |
  | value labels | 10.5 px | 600, tracked | — |
  | values | 15 px | 600 | coloured by meaning |
  | value subtitles | 10.5 px | 400 | grey |
  | detail title | 24 px | 800 | — |
  | detail slot headers ("COMPUTED") | 10.5 px | 700, tracked | — |
  | chart caption | 12.5 px | — | grey |

  **Labels are always small, tracked and grey. Values are bold and coloured. Explanations are grey sentences.**
- **Card anatomy:** radius 14 px, padding 16 px, no border, fill one step lighter than the page.
- **Selected and "you are here" states:**
  - **Selected tab:** teal text, teal hairline border, and a filled chip. Unselected tabs have a grey text and a grey border.
  - **Selected value row:** teal tint at 10 % plus a teal left rule.
  - **"YOU ARE HERE" band:** teal tint at 16 %, a teal border, and a teal label. The other two bands are dark cards, each with a thin **coloured top rule** (muted teal for the middle band, rose for the bad band).
  - **Caveat block:** a rose-tinted box with a rose "CAVEAT" tag.
- **Number formatting** — mixed scale suffixes. **This is substantive for us:**
  - Indian **L** (lakh): "4.18L Cr", "−1.42L".
  - Western **K** and **M**: "+70.7K Cr", "24.1M contracts", "+₹8k".
  - Every value is **signed where a sign exists** ("+", and the true minus "−").
  - Units always sit beside the number: Cr, pts, %, x, "th".
  - Distance to spot is printed as a **subtitle** under a level: "+1.32% from spot", "0.58% below spot", "call wall · +1.85%".
- **Two palettes.** The target is inconsistent with itself:

  | where | positive / calls | negative / puts | spot | pin |
  |---|---|---|---|---|
  | landing (A1) | teal `#38B8A6` | rose `#E8546B` | white | teal |
  | terminal sample (A2) | **amber** (`#D99B2E`) for call legs | **violet** (`#59497F`/`#A78BFA`) for put legs | white rule | red bar (Pin tab) |

  In the terminal sample, signed gamma is teal/red. The OI call wall is drawn amber and the OI put wall violet (A2·OI/CALL WALL, PUT WALL detail text). The **substantive** rule under both palettes: **sign/side is encoded by hue, and magnitude by length or size — never by hue intensity alone.**
- **Copy/render drift:** A1·30-session river says gold means dampening and rust means amplifying, but it renders teal on both sides of zero. This is styling drift, not substance.

### B4. Interaction model

| pattern | where | what it does |
|---|---|---|
| **Click a value → chart cross-link** | A2, every tab | Selecting a value (1) highlights its row, (2) highlights its element in the chart, (3) **replaces the chart caption with a sentence naming that element** (e.g. selecting flip gives "the dashed white rule… left of it amplifies, right of it dampens"), and (4) loads the detail panel. **This is the main learning mechanism: the chart teaches its own legend one element at a time.** |
| **Read-it-with links** | A2 detail panel | Each value lists 2–3 other values (tab-tagged chips). Clicking one jumps to it. **The comparisons are explicit and navigable.** |
| **By question / By reading + filter** | A2 board index | Re-groups all 49 values. The filter box searches name or meaning. |
| **Hover → focus-and-dim + fixed readout slot** | A1·gamma orbit | Hovering a strike dims the other bodies. A fixed slot at the panel foot (normally "HOVER A BODY") shows "strike · CALL x · PUT y Cr". **This is not a floating tooltip.** |
| **Hover → floating card** | A1·OI rotation | Row highlight plus a card: strike, net ("LEFT −1.13M" in rose serif), CALL and PUT legs, and distance ("300 pts above spot"). |
| **Hover a strike** | A1·explorer | Axis label slot shows "HOVER A STRIKE". |
| **Spot slider re-derives everything** | A1·explorer, A1·hedge simulator (±50 buttons) | Moving spot re-derives flip, walls and the regime card. **The regime sentence is regenerated with live numbers** ("Spot is below the flip at 24,000, so…"). |
| **DTE slider** | A1·six layers, A1·radar | Changes the profile or radar shape by time to expiry. |
| **Timeline playback** | A1·pin funnel | Play/pause plus a scrubber from 09:15 to 15:30. A narrative sentence changes per step. |
| **Drag to rotate** | A1·IV surface | 3-D mesh; a skew slider deforms it. |
| **Symbol pills** | A1·hero | NIFTY / SENSEX / BANKNIFTY. On A2 the symbol is shown in the strip; a switcher is not visible on the sample. |
| **Expiry scoping** | A2 strip + A2·Overview/DTE caveat | The readout is scoped to **one expiry at a time** ("31 JUL · MONTHLY"). The caveat says weekly and monthly overlap, so check which one is selected. A1d says **0DTE and weekly chains are kept separate**. |

**No keyboard shortcuts** were observed. Clicking one *layer* does not highlight another *layer's* chart: cross-linking is **value → own chart**, plus navigable read-it-with links.

### B5. Reading order the target prescribes

- **A2 (four steps):**
  1. Regime, then size.
  2. Concentration (HHI).
  3. Levels **in sigma**.
  4. Direction of travel (1-day delta, day ΔOI, wall held or rolled).
- **A3 §09 (seven questions, with a gate):**
  1. Kind of day.
  2. Room to flip.
  3. **Can I trust the levels (HHI, and is it normal for this index)?** A smeared board → **stop, use zones not lines**.
  4. Edges (floor, ceiling, pin) against a normal day.
  5. Do the two views agree (**pin against max pain**)?
  6. Fresh or left over (change since open, how busy)?
  7. What would break it (time passing, options repricing)?
- **The value list order on A2·Overview follows the same logic:** spot → net GEX → regime → pin → flip → ceiling → floor → PCR → DTE.

### B6. Sign and colour semantics across the board

- **Positive gamma, dampening, calm** = teal (landing) / teal-green (terminal). **Negative, amplifying, fast** = rose/red.
- Levels take their **side's** colour:
  - Put wall / floor is red or rose.
  - Call wall / ceiling is neutral white on A1·hero and A2·Overview (A2 prints CEILING white and FLOOR red), but teal on A1·explorer. **This is inconsistent — styling.**
  - Pin and flip are teal.
- **Added vs removed:** teal = added OI, rose/red = unwound/closed (A1·OI rotation; A2·OI/DAY ΔOI "teal added, red closed").
- **Buy vs sell futures:** teal = buy, rose = sell (A1·hedge simulator legend).
- **Quality:** green dot = reading well, grey = mid, red = badly (A2 By reading).
- **Spot** is always white: a white rule, or a white dot on the zero line.
- **Illustrative badges** are grey outline chips, bottom-right of each panel.

### B7. Units

| quantity | unit (target) | evidence |
|---|---|---|
| Net GEX, net Γ, GEX at pin | ₹ crore, K/L-scaled, signed | A2·Overview/NET GEX; A2·Pin/GEX AT PIN |
| Hedging per 1 %, vanna per +1 pt IV, charm per session | "thousands of crore" of notional or of gamma exposure | A2·Flows |
| DEX standing and flow | ₹ crore of delta-notional; also contracts | A2·Delta |
| OI, ΔOI, positioning | contracts (M), **never converted to Cr** | A2·Flows/POSITIONING |
| Levels | strike; distance as % of spot (subtitle); **distance in σ** in the reading guidance | A2·Overview; A2·Pin/SIGMA |
| Sigma | index points (1 σ session range) | A2·Pin/SIGMA |
| IV | % annualised; slope and skew in **vol points** | A2·IV |
| Concentration | HHI 0–1; delta concentration %; peak share % of book | A2·Gamma, A2·Delta |
| Conviction | 0–100 | A2·Pin/CONVICTION |
| Margin | score points (unitless) | A2·Pin/MARGIN |
| Boost | multiplier (x) | A2·Pin/BOOST |
| DTE | **trading sessions** per the exchange calendar | A2·Overview/DTE |
| Term slope on A1 surface panel | pts **per 30 d** (normalised) | A1·IV surface |
| Term slope on A1 term panel and A2 | pts, back − front, **not normalised** | A1·IV term; A2·IV/TERM SLOPE |

**S83 said the surface slope is scaled and the term slope unscaled. That is VERIFIED, and A2 adopts the unscaled one.**

### B8. Freshness, out-of-hours and expiry-day behaviour

- **No timestamp is shown on any value**, and there is **no stale chip** on the public views.
  - Freshness is carried by the word "live" in SPOT's unit line and by the badge ("PRODUCTION SAMPLE SET · NOT LIVE").
  - SPOT's caveat says figures are snapshots and strikes are stale between refreshes relative to a fast tape.
  - *Inferred (reason: none rendered on a sample; the live state is gated):* the terminal's live badge may be the freshness cue.
- **Blank, never fake.** A3 §11: anything built on today's trading is empty outside market hours; where a number cannot be produced honestly, nothing is shown. Specific rules:
  - Δ1D HHI shows a **dash rather than zero** after a holiday or data gap (A2·Gamma/Δ1D HHI).
  - CONVERGENCE reads **FLAT** if either input is exactly zero, and stays **blank** if either basis is missing (A2·Delta/CONVERGENCE).
  - ZERO-Δ LEVEL returns **null when the running sum never crosses**, "a different answer from crossing at the first row" (A2·Delta/ZERO-Δ).
  - Dealer-side classification leaves a strike **blank** when neither OI nor price moved enough.
  - A **quiet-day detector** flags when time decay, not trading, is driving the price leg (A3 §07).
- **Expiry proximity is a scaling, not a mode.** DTE "scales almost everything". Bands: 0–1 DTE levels sharpest; 2–5 meaningful; above 5 walls indicative (A2·Overview/DTE). BOOST is an explicit expiry-day multiplier (A2·Pin/BOOST). Charm "accelerates into expiry" (A1·six layers/CHARM).
  - **No special expiry-day screen and no expiry-day blanking were observed.** MERDIAN's SKIPPED_EXPIRY is stricter.
- **Short-history honesty:** PERCENTILE and "rank vs history" carry the caveat that a short series makes every day look extreme (A2·Gamma/PERCENTILE; A3 §05, §11).

### B9. Onboarding, glossary, mistakes

- **Three layers of explanation:**
  1. A3 — no maths, 25 minutes, 16 pictures.
  2. A2 — every number, with its method.
  3. Per the A3 closing note, **the method lives in the product next to each number**.
- **Every value states its own caveat.** Each caveat is a limit on what the value can tell you, not a legal line.
- **Common mistakes** (A3 §10, eight items) are written as **"instead of… do this"** pairs, each pointing to a comparison: distance from spot, is the wall still at the same strike, PCR direction not level, room to flip, rank vs own history, is total OI rising, re-read every session, ask what the number is measured against.
- **Glossary** (A3 §12): one line per term; 18 terms.
- **Named states are always words, never only colours:**
  - Dampening / Amplifying; Positive Γ / Neutral / Negative Γ
  - COMPRESSED / BALANCED / DISPERSED
  - LOCKED / CONTESTED / DRIFTING
  - holding / thinning / rolled
  - rising / flat / falling
  - SAME SIGN / OPPOSITE SIGN / FLAT
  - normal / flat / inverted
  - Reading well / mid / badly

### B10. Motion

- Landing panels **fade in on scroll**.
- A **marquee ticker** carries spot, flip, net gamma, walls, pin and the other symbols' spot.
- The **pin funnel autoplays**, and the **wall probe animates by itself** until the user takes over ("move to take control").
- The terminal sample (A2) has **no motion** beyond state changes on click.

**All of the landing motion is marketing styling, not substance.**

### B11. Free vs gated

- **Free:** the concepts, all methods on A2, and illustrative panels.
- **Gated:** the live terminal. A1d lists what it adds that the public pages do not show at all:
  - **intraday replay from the open**
  - **historical snapshots across past sessions**
  - **separate 0DTE and weekly chains**
  - BANKNIFTY alongside NIFTY and SENSEX
- **Empty-state wording** was not observable. The only prompt-states seen are "HOVER A STRIKE", "HOVER A BODY", "DRAG PRICE TO GENERATE FLOW" and "CLICK A VALUE". **ADR-017 P3 treats these as noise**; the target uses them as affordance hints.

---

## C. Per-layer table

**Our spec layers L1–L19**, with MERDIAN objects from `CURRENT.md` / `capture_s83.md` / ADR-025 B4. "Gap" is typed as **data**, **computation** or **UI only**. Every row was observed 2026-09-25.

| layer | target treatment | render form | compared against | states and edge cases | evidence | our view(s) / ENH | gap to close | notes |
|---|---|---|---|---|---|---|---|---|
| **L1** gamma density per strike | Per strike: γ × OI × contract multiplier × spot², **signed by an assumed side (short calls, long puts)**, summed **over the selected expiry**. ₹ Cr. | A2·Gamma: **horizontal diverging bars with strike on the vertical axis** (positive right teal, negative left red), plus a **dashed cumulative silhouette** from the top of the chain down; spot as a white horizontal rule. A2·Overview/Flows: call bars amber up and put bars violet down with a dashed net line. A1·explorer: vertical diverging bars with strike on x. A1·wall: stacked-block columns. | spot; its own cumulative; the two peaks | Side assumption stated as unobservable (caveat) | A2·Overview/NET GEX "COMPUTED" (described); A2·Gamma chart (described) | ENH-80 `gex_strike_snapshots.gex_cr`; Marketview GEX histogram (strike on x) | **UI only** — orientation (strike on y), cumulative overlay, call/put split view. Our PE negation matches their side assumption | Our deep-ITM guard (\|K−S\|/S > 5 %) is not mentioned by the target |
| **L2** pin zone | **No band.** The target uses a **corridor** (floor put wall → ceiling call wall, gamma-based) and a **pin point** with runner-up. Pin = strike maximising **total call + put gamma exposure**. | A2·Overview: **shaded corridor rectangle** between floor and ceiling on the chain chart; strip cell "CORRIDOR x to y". A1·pin funnel: inverted cone narrowing to the pin over the session. | spot inside or outside the corridor; pin distance vs spot | Spot: inside walls / at a wall / outside walls | A2·Overview/SPOT scale; A2·Overview/PIN (described) | ENH-81 `v_gex_strike_pin_zone` (τ-weighted band) | **UI + computation** — our band is a different object from their corridor. The corridor is derivable from L4/L5 gamma walls | Decide whether PIN band survives, is renamed, or sits beside the corridor |
| **L3** flip level | **Interpolated strike where the cumulative net gamma profile across strikes changes sign.** | Dashed white vertical rule labelled "Γ FLIP" on the chain chart; a strip-adjacent value with subtitle "x% below spot"; A1·explorer card ("where hedging changes sign") | **spot (headroom)**, regime, net GEX | Spot well above / **within 0.25 % of flip** / below. "A switch, not a target." | A2·Overview/FLIP "COMPUTED" + scale (described); A3 §03 | ENH-131 `v_gex_repriced_flip` (**Black-Scholes repriced zero-gamma over a spot grid**); legacy `gamma_metrics.flip_level` (not displayed) | **Computation (D3 deviation)** — the target's is a strike-axis cumulative crossing at *current* spot; ours reprices gamma as spot moves. Also UI | ENH-131's gate record already publishes `n_cross_full_grid`; the target shows one crossing only. Record as a D3 deviation or build their construction beside ours |
| **L4** call wall | **Two objects.** (a) **CEILING** = strike with **maximum call-side gamma exposure** in the expiry. (b) **CALL WALL (OI tab)** = strike with **maximum call OI**; the text says these often differ. | (a) Chain-chart label and corridor top edge; value subtitle "call wall · +1.85 %". (b) OI butterfly, **amber bar with its size printed at the tip**. | spot distance; OI wall vs gamma wall; itself across snapshots | **Wall holding / thinning / rolled** (tracked across snapshots). Caveat: a single strike, not a cluster — a shelf of three medium strikes can matter more | A2·Overview/CEILING; A2·OI/CALL WALL (described) | ENH-120 (OI argmax); S79 **rejected** the gamma-weighted argmax (collapses to ATM at −0.09σ/+0.19σ) | **Computation (open question)** — it is unconfirmed whether the target's gamma wall (max call-side GEX) is the same construct S79 measured and rejected. Needs a re-read of S79 against this definition. **Holding/thinning/rolled needs cross-snapshot state** | See E-Q3 |
| **L5** put wall | Mirror of L4: FLOOR = max put-side gamma exposure; PUT WALL (OI) = max put OI, violet. | As L4, mirrored | as L4 | As L4. Caveat: put walls **rebuild faster than call walls near expiry** as protection rolls down | A2·Overview/FLOOR; A2·OI/PUT WALL | ENH-120 | as L4 | — |
| **L6** net vs absolute GEX | **NET GEX** (Cr, signed) → **REGIME** word. Bands: **> +1,000 Cr** strong dampening; **±100 Cr** neutral/flat ("gamma is not today's story"); **< −1,000 Cr** strong amplifying. The absolute leg appears as the **denominator of HHI and of peak share**, not as its own tile. A1·six layers lists "net and absolute GEX per strike". | Strip cells REGIME + NET Γ; A2·Overview value; A1·explorer **regime card with a regenerated sentence**; A1·ticker | net vs regime vs flip vs HHI | Positive Γ / **Neutral** / Negative Γ. The landing card is binary (no neutral) — illustrative simplification | A2·Overview/NET GEX, REGIME scales (described) | Marketview REGIME card (net); ENH-121 absolute leg (computed, unrendered) | **UI + a calibration question** — the target's ±100 / ±1,000 Cr bands are **absolute Cr**, symbol-agnostic. Ours needs a measured band per ADR-016, not copied numbers | **Neutral band is substantive**: our regime has no neutral state |
| **L7** vanna | **Per +1 pt IV: gamma added or removed**, in thousands of Cr. Computed on an **IV-shift grid −15..+15 pts**, the +1 rung minus the 0 rung. **It reprices only TODAY's classified OI change, not the standing book** (stated). | A2·Flows value; A1·six-layer tab (placeholder curve); A3 §07 "fear view" line chart ("below the line is the fast day") | IV front, net GEX | Vol adds gamma / little sensitivity / vol removes gamma | A2·Flows/VANNA (described) | ENH-98 (PENDING, not started) | **Computation + data** — scope choice (today's flow vs standing book) must be decided by us; the target's choice is stated | **Load-bearing for L7/L8 design before build** |
| **L8** charm | **Gamma the clock removes over the next 24 h**, today's classified OI only, repriced at 0/6/12/24/48 h and expiry; the +24 h rung minus 0 h. A1 also lists **expiry-day acceleration** and an **overnight hedge estimate**. | A2·Flows value; A3 §07 "time view" (curve piling up toward expiry) | DTE, Δ1D HHI | Gamma building / little change / gamma draining | A2·Flows/CHARM (described) | ENH-98 | as L7 | Testimonial (A1) calls charm on expiry day a 1 pm check — **not evidence**, only usage colour |
| **L9** IV term structure | **FRONT ATM IV** = IV at the strike closest to spot, front expiry, annualised. **BACK ATM IV = furthest listed expiry.** **TERM SLOPE = back − front, vol pts, not normalised.** Bands: **> +2 normal · −1..+2 flat · < −1 inverted.** | A2·IV: line + area with the front point highlighted, **x = DTE (2/5/14/30/60/84), not dates**. A1·term: line + area with point labels, x = 7/14/21/28/56/84 d, **evenly spaced (categorical)**. | front vs back; front IV → sigma | Normal / flat / inverted; "two points only" caveat; back month thinly traded, **may be stale** | A2·IV/FRONT, BACK, TERM SLOPE (described); A1·IV term | ENH-130 `v_iv_term_structure` (W1+W2) | **Data (known D3 deviation)** — capture depth; UI (x as DTE) | **Our `parity_gap` quality column has no target equivalent** |
| **L10** IV surface | Strike × expiry mesh, **no method stated**. Scalars: ATM IV; **SKEW = IV 2 % below — "ATM" on A1, "spot" on A2 — minus ATM IV, same expiry, vol pts**; term slope per 30 d. Skew bands **> +4 steep · +1..+4 normal · < +1 flat/inverted**; **the change matters more than the level**. | A1: wireframe mesh, teal lines, **rose lines on the put wing**, drag to rotate, skew slider deforms it; axes STRIKE → / ← EXPIRY. A2: **no surface on the sample** — the IV tab shows term only; skew is a value | skew vs put wall, HHI put; its own change | Steep / normal / flat; caveat: two points only, one thin strike can move it | A1·IV surface; A2·IV/SKEW (described) | ENH-132 `v_iv_surface`, `leg_skew_98` (**0.98 × ATM strike**, OTM put) | **Computation (D3 check)** — the anchor is spot (A2) or ATM (A1); ours is the ATM strike, no search. UI: a surface is marketing-only on the public pages | Our "iv = 0 means absent" rule has no target statement |
| **L11** five-axis radar | Five readings (gamma, vanna, charm, IV term, pin) on **0–10**; scaling **not stated**. | A1: **five horizontal 0–10 bars above a filled pentagon** on concentric rings; the vertices are **not labelled on the shape**; DTE slider. **Absent from A2** (not one of the 49 values) | DTE | none stated | A1·radar (described) | none | **Computation + UI** — composition only; weakest-evidenced layer | **The target's terminal sample does not carry it.** Candidate for DECLINED-ON-EVIDENCE or deferral — operator question |
| **L12** pin conviction | Pin candidates by a **gamma-weighted score** (method not stated). **CONVICTION 0–100** = normalised lead of the top over the distribution (**≥ 70 LOCKED · 30–69 CONTESTED · < 30 DRIFTING**). **MARGIN** = top − second score. **RUNNER-UP.** **GEX AT PIN** (Cr; bands 1L / 0.3L). Concentration is separate: **HHI = Σ (per-strike share of \|γ\|)²**, bands **0.10 / 0.25**, plus HHI CALL, HHI PUT, PERCENTILE vs history, **Δ1D**, **Δ vs rolling mean**. | A2·Pin: **horizontal bars of candidate strikes on one scale**, the pin bar red, runner-up marked. A1·orbit: conviction **gauge bar DRIFTING→LOCKED** + a sentence + **TOP CANDIDATES ranked #1–#5 as % of the leader** | leader vs runner-up (margin); conviction vs HHI; HHI vs its own history | Adjacent close runner-up → **read as a zone**; distant close → two centres | A2·Pin, A2·Gamma (described); A3 §04–05 | ENH-122 (HHI leg, **max/sum**), ENH-125 (ranked) | **Computation** — our "HHI" is max/sum, **not the Herfindahl sum of squares**; call/put split, percentile, Δ1D and Δmean are missing. Conviction/margin not built | Rename ours or add a true HHI — E-Q5 |
| **L13** OI rotation since open | **DAY ΔOI** = OI now − **09:15** per strike, summed. **POSITIONING ΔOI** (Flows) = OI now − **last snapshot of the previous session** — **two different baselines, both shown**. A1 headline "X ROTATED from strike → strike". | A1: **centred diverging horizontal bars per strike**, unwound left rose, added right teal; header "X rotated A → B"; footer **UNWOUND total · window ±10 strikes of spot · ADDED total**; hover card with the call and put legs and the distance from spot. A2·OI: a thin ΔOI rule under each OI bar | open vs now; previous close vs now; total OI trend | Strongly positive / rotation / emptying | A1·OI rotation (described); A2·OI/DAY ΔOI; A2·Flows/POSITIONING | ENH-127 (live leg) | **Computation** (the previous-close baseline) + **UI** | Our historical leg is capped at 14 days by jobid 19 |
| **L14** 30-session river | Daily net gamma, **price threaded on its own scale**. Colour rule stated (gold/rust) but not rendered. | A1: thin line + fill against zero, pale price line, date-range label; **no axes values** | zero line; price | dampening / amplifying | A1·30 sessions (described) | ENH-126 | **UI only** | We hold 299 d vs their 30; the history is ours to show |
| **L15** SpotGamma key-level set (ext.) | Partly present under other names: **+Γ PEAK / −Γ PEAK with share of book** (bands 8 % / 20 %); the gap between them is "the zone where hedging changes character". **No hedge wall, no vol trigger.** | Chain-chart labels "+γ PEAK", "−γ PEAK" with "% OF BOOK" | peak vs flip; share | as bands | A2·Gamma/+Γ, −Γ PEAK | none (folds into L12/L3 per spec) | **Computation** (small) | "Share of book, not the strike" is a presentation rule worth keeping |
| **L16** implied 1-day move (ext.) | **SIGMA** = ATM IV scaled to the **time remaining in the expiry**, in points; **the yardstick for every distance** (< 0.5σ routine · 0.5–1σ genuine · > 1σ unusual). A3 calls it the "normal day". | A2·Pin value; A3 corridor diagram "a normal day moves about this far" | **every level's distance from spot** | caveat: IV is a price, not a measurement | A2·Pin/SIGMA; A3 §04 | none (spec: `volatility_snapshots.atm_iv_avg`, 18 months) | **Computation + UI — promote.** For the target it is **not an extension, it is the board's unit of distance** | **Load-bearing (E)** |
| **L17** view architecture (ext.) | Greek × dimension switching is **present as tabs** (Gamma / Delta / Flows / IV), not as a switcher matrix. **No by-expiry gamma view.** "Permissive strike" colouring: **not present.** Dealer vega: **not present.** Expiry-week charm: BOOST + charm acceleration. | Tabs | — | — | A2 tabs; A1·six layers | none | — | The tab = question model is simpler than a switcher matrix |
| **L18** FII/DII participant positioning (ext.) | **Not present.** | — | — | — | absent on A1–A5 | ENH-115 (built, ambient only) | — | **MERDIAN-only** |
| **L19** max pain / pin–max-pain (ext.) | **MAX PAIN** = strike minimising total intrinsic payout; **ATM PIN** is the gamma pin overlaid on the OI ladder. **"Max pain near the pin" = the strongest configuration** on the board; far apart → prefer the gamma reading. | A2·OI: **dashed red horizontal rule** (max pain) and **dotted teal rule** (ATM pin) across the OI butterfly | **pin vs max pain** (reading-order step 5) | near / within a few strikes / far | A2·OI/MAX PAIN, ATM PIN; A3 §06 | ENH-123, ENH-124 (parked) | **UI only** | **Target treats it as core, not an extension** — D5 parking is worth revisiting (E-Q4) |

### C-bis. Unmapped target panels and values (no L-number in our spec)

| target item | treatment (stated) | render | compared against | evidence | nearest MERDIAN object | gap |
|---|---|---|---|---|---|---|
| **Delta exposure suite** — STANDING DEX, ΔOI FLOW DEX, CONVERGENCE, ZERO-Δ LEVEL, CONCENTRATION, IN CONTRACTS | Per strike δ × OI × lot × spot / 1e7, netted by adding (put δ negative). Flow = the same on OI change vs previous close. Convergence = a sign test only. Zero-Δ = running net delta in ascending strike order, first sign change, null if none. Concentration = max \|net\| / gross. | A2·Delta values; the chart reuses the gamma chain "for strike layout only" | **standing vs today** (convergence); zero-Δ vs flip | A2·Delta (described) | none (delta exists in OCS 61/62 d) | **data (horizon) + computation + UI** |
| **Hedging per 1 % move / ladder** | +1 % rung notional; **LINEAR by design** (±2 % is exactly 4× ±0.5 %); at current gamma | A1·hedge simulator (strike ladder + futures trace); A3 §07 ladder bar chart ("look for the jump") | regime (fuel vs brake) | A2·Flows/HEDGING; A1·hedge simulator | **`v_dealer_flow_sim` (6 scenarios ±0.5/1/2 %) — already built and on Marketview** | UI only |
| **OI tab** — TOTAL OI, CALL/PUT OI share (45/55 %), PCR (0.80/1.30), VOL/OI (0.20/0.60) | Stated | A2·OI butterfly (calls right amber, puts left violet), dashed volume profile, sizes at bar tips | trend through the session, not level | A2·OI | OCS `oi`; ENH-127 | computation (small) + UI |
| **Boost** | Pin concentration ÷ **time-normalised baseline** (baseline not stated); 1.05 / 1.30 | value | DTE, conviction | A2·Pin/BOOST | none | computation |
| **Pin funnel** — pin probability, magnet pull, distance to pin, gamma at spot (word) | **Not stated** | A1: session cone, top-to-bottom time, playback | pin vs spot over time | A1·pin funnel | none | computation (undisclosed) |
| **Gamma orbit** | Size = gamma, distance = points from spot | A1: radial bodies, call/put rim colour, hover readout | — | A1·orbit | none | UI (alternative L1 view; marketing) |
| **Dealer-side classification** | Four cases (OI up/down × option price up/down); blank when neither moved; **quiet-day detection** when time decay drives price | A3 §07 grid | — | A3 §07 | none — we assume the side (PE negated) | **computation (big)** — E-Q7 |
| **By reading triage** | Every value graded well/mid/bad by its current band | A2 board index with coloured dots | all values at once | A2 | none | UI |
| **Intraday replay / historical snapshots** | Listed as terminal features | not visible | open vs now; past sessions | A1d | ADR-008 replay architecture; 299 d history | UI (+ data retention, jobid 19) |

---

## D. Coverage differences

### D1. What the target does that our spec does not cover yet (candidate additions)

1. **Sigma as the board's unit of distance** — every level read in σ from spot. L16 promoted from extension to core.
2. **A true HHI** (Σ share²) with **call and put HHI**, **percentile vs own history**, **Δ1D**, **Δ vs rolling mean**. Our L12 "HHI" is max/sum.
3. **Pin candidate set** — runner-up, margin, conviction (LOCKED/CONTESTED/DRIFTING), GEX at pin, boost.
4. **Two wall families** — gamma walls (ceiling/floor, defining the **corridor**) and OI walls. Plus **wall state across snapshots** (holding / thinning / rolled).
5. **±Γ peaks with share of book.**
6. **Delta exposure suite** (six values), including the **standing-vs-today convergence** sign test.
7. **Two ΔOI baselines** — since 09:15, and since the previous close.
8. **OI tab** — total OI, call/put share, PCR (direction only), vol/OI.
9. **Regime neutral band.**
10. **Vanna and charm scoped to today's written positions**, with stated rung grids.
11. **Dealer-side inference** from the OI × price four-case grid, with blank and quiet-day handling.
12. **Expiry scoping per readout**, with 0DTE and weekly kept separate; BANKNIFTY.
13. **Per-value explanation contract:** unit line, COMPUTED, HOW TO READ, READ IT WITH, 3-band SCALE with you-are-here, CAVEAT.
14. **By-reading triage** of all values.
15. **Intraday replay** and **historical snapshots**.

### D2. What our spec has that the target does not show (candidate MERDIAN-only layers)

1. **Gate records published with the value** — ENH-131's G1–G5 in the view COMMENT; `n_cross_full_grid`, which exposes more than one crossing. The target shows one flip and no fidelity record.
2. **`parity_gap`** (CE − PE at ATM) on L9 — a **quote-quality column**; "a slope smaller than it is noise". The target has no data-quality column at all; its caveats are prose.
3. **Explicit absence states** — `SKIPPED_EXPIRY` (dte 0), `UNMEASURABLE_R`, one-expiry cycles → NULL slope with no fallback, **iv = 0 = absent**, and the **2026-06-04 → 08-23 hole rendered as absence**. The target has the same *doctrine* ("blank, never fake") but fewer *named* states.
4. **Quote state (per the S84 brief)** — to be confirmed against the live object before it is designed in. Named here only because the brief names it.
5. **Repriced flip** (ENH-131) — a different, falsifiable construction.
6. **History depth** — 299 d of per-strike gamma; 18 months of ATM IV (L16); the river at 299 d vs 30.
7. **L18 FII/DII participant positioning** — India-native; absent on the target.
8. **ICT zones, PO3, confluence ring, breadth, signal row** — ENH-110 / ADR-017 P4. The target has no price-structure overlay. Its only "confluence" statements are **pin ≈ max pain** and **zero-Δ ≈ flip**, both as reading advice.
9. **Pin zone band** (L2, τ-weighted) — the target has a point pin plus a corridor instead.

---

## E. Implications for the whole-board design session (Amendment B1)

### E1. How the target groups layers

| target tab (question) | our layers inside it |
|---|---|
| **Overview** (which kind of day and where are the edges) | L6 regime + net, L3 flip, L4/L5 gamma walls → corridor, L2/L12 pin, PCR, DTE |
| **Pin** (how settled is the centre) | L12 candidates, conviction, margin, GEX at pin, **L16 sigma**, boost |
| **Gamma** (can I trust the levels) | L1 signed + cumulative, L12 HHI family, L15 ±Γ peaks |
| **Delta** (which way does the book lean) | unmapped suite |
| **OI** (what is actually written) | L4/L5 OI walls, **L19 max pain + pin overlay**, L13 day ΔOI, totals |
| **Flows** (what must be traded next) | L7 vanna, L8 charm, the hedging ladder (`v_dealer_flow_sim`), positioning ΔOI |
| **IV** (price of time and cover) | L9, L10 skew |
| **Landing only, not in the terminal sample** | L10 surface mesh, **L11 radar**, L14 river, orbit, funnel |

**Implication:** the target designs **by question, not by layer**. Several of our layers split across two tabs:
- L4/L5 appear on both Overview and OI.
- L12's concentration half sits on Gamma and its candidate half on Pin.

### E2. Load-bearing comparisons (the ones every reading rests on)

1. **Level vs spot, in σ** — every level's distance divided by the 1σ range. Without L16 the board has no yardstick.
2. **Net GEX sign → size → regime**, with a **neutral band** that tells the reader to ignore gamma today.
3. **Concentration as a gate** — HHI (and its percentile) decides whether individual strikes are read at all ("smeared → stop, use zones").
4. **Spot vs flip** — headroom, with a named "within 0.25 %" boundary state.
5. **Pin vs runner-up** (margin, conviction) and **pin vs max pain** (agreement = strongest).
6. **Now vs a baseline** — open vs now (day ΔOI), previous close vs now (positioning, ΔOI flow, Δ1D HHI), today vs history (percentile, Δ vs mean), standing vs today (convergence).
7. **Front vs back IV**, and **skew change vs level**.
8. **Same wall across snapshots** — holding / thinning / rolled.

### E3. What the first screen must answer (target's answer, as a benchmark for ours)

Eight cells: **symbol · expiry (with class) · spot (± %) · regime word · net Γ · HHI + band word · corridor · DTE · IV**. Together these answer:
- what kind of day it is and how strongly;
- whether the levels can be trusted;
- where the edges are;
- how to scale distance.

Against ADR-017 / ENH-110, our header strip has regime, DTE, gap, PO3, VIX, breadth and stale. It **lacks concentration, corridor and a σ yardstick**, and **has** items the target does not show (PO3, breadth, gap).

### E4. Tensions with the house UI rules

- **ADR-017 P3 (silence is healthy) vs the target's "By reading" triage.** The target shows every value graded well/mid/bad. Ours hides the healthy state. *Possible reconciliation:* apply P3 to **system health** (stale, pipeline) and grade **market readings** explicitly. The target's "mid = the least informative reading" is itself a P3-style idea.
- **ADR-017 P5 (sparklines, not timestamps).** The target has **neither** on values. It carries freshness in a live/sample badge and in caveats. Direction of travel is a **separate value** (Δ1D, day ΔOI), not a sparkline.
- **ADR-017 P4 (confluence ring).** The target has no visual confluence element. Its two stated agreements (pin ≈ max pain, zero-Δ ≈ flip) are reading steps. *Candidate:* these are confluences our ring could detect **without ICT**.
- **ENH-110 hero chart** draws strike on **x**. **Every chain chart in the target's terminal sample draws strike on y** (a ladder), which lets a cumulative silhouette and horizontal rules for spot, flip, pin and max pain read like a price ladder. *Styling or substance?* — **substance** for a board that must overlay many horizontal levels; styling for a single histogram.
- **ADR-017 P6 (distance × time salience).** The target does this **in text and bands**: pin "almost on spot / short way / far", DTE bands, boost. It does not fade graphics. Our P6 is more ambitious and unmatched.
- **ADR-017 P7 (keyboard).** The target has none. Ours is operator-grade; keep it.

### E5. Open questions for the operator

1. **Axis orientation.** Adopt strike-on-y (ladder) for the hero chain chart, reversing the ENH-110 Appendix A geometry?
2. **Tab = question grouping** vs one consolidated Marketview. Does the parity board become a set of tabs inside Marketview, or a second page?
3. **Wall definition.** The target's gamma wall is *max call-side / put-side GEX*. Does S79's rejection of the "gamma-weighted argmax" apply to this exact definition, or was a different product measured? This needs a re-read of the S79 measurement before L4/L5 are rendered.
4. **L19 parking (D5).** The target puts max pain and the pin–max-pain comparison in its reading order. Keep it parked, or promote it into the fourteen by amendment?
5. **L11 radar.** It is absent from the target's terminal sample and exists only as a landing illustration with an undisclosed 0–10 scaling. Candidate **DECLINED-ON-EVIDENCE**?
6. **L12 naming.** Our `gamma_concentration` is max/sum. Build a true Herfindahl, rename ours, or both?
7. **Dealer side.** We assume the side as the target's *stated* default does (short calls, long puts). Its A3 §07 describes an OI × price classification on top. Is that in scope for parity, or recorded as a known deviation?
8. **Vanna/charm scope (before L7/L8 build).** Standing book, or today's written positions as the target states?
9. **Regime neutral band** — add one, calibrated per ADR-016 per symbol, rather than copying ±100 Cr?
10. **Skew anchor** — spot (target A2) vs ATM strike (ours, and the target's A1 wording). Record as a D3 deviation, or re-anchor?
11. **BANKNIFTY and expiry selection** (0DTE vs weekly kept separate) — in scope?
12. **Per-value explanation contract** (unit / computed / read / read-with / scale / caveat) — adopt as the house pattern for every parity value? Our view COMMENTs already hold most of it.
13. **Number formatting** — standardise on Cr with lakh/crore scaling, or mixed K/L/M as the target does? (Recommend one scale family; the target's mix is a styling weakness.)

---

## F. Where the target is silent (methods not disclosed) — these become our own decisions

Everything else in C is stated on A2. These are not:

1. **Pin candidate score** — "gamma weighted score per strike", with no weights or form.
2. **Conviction normalisation** — "normalised lead of the top candidate over the candidate distribution", with no formula.
3. **Boost baseline** — "time normalised baseline", undefined.
4. **Radar 0–10 scaling** for all five axes, and which quantities feed each.
5. **Pin probability, magnet pull, "gamma at spot" word bands** on the funnel.
6. **Dealer-side classification thresholds** — what counts as OI or price "moving enough", and the quiet-day detector's rule.
7. **IV source and solver** — whether IV is the vendor's or their own; rate, dividend and day-count conventions; how a one-sided or zero quote is handled. The disclaimer only says exchange chain plus third-party feeds.
8. **Surface construction** — interpolation or fitting, wing treatment, OTM vs average convention. The surface is illustrative only.
9. **Time basis for sigma** — "time remaining in the expiry": calendar vs trading, session fraction or not. DTE itself is in trading sessions.
10. **Flip interpolation details** — which cumulative direction (top-down vs bottom-up), and what happens with multiple crossings or none.
11. **Snapshot cadence** — "each tick" (A1·method) vs "each snapshot" (A2); no interval is stated.
12. **History length** behind the percentile, the rolling-mean window, and the 30-session river's source.
13. **Contract multiplier / lot size source** — "from the payload", with no provenance.
14. **Which expiry is "front"** on expiry day itself (0DTE), and whether the readout rolls at settlement.
15. **Pin tie-break** between adjacent equal scores.

**Standing note.** Several A2 detail panels expose internal identifiers from the target's own code. These are **not recorded here** beyond this sentence, and are not to be used. Where a method is stated in plain language above, we match the **concept and the market convention**, and every constant is re-derived from our own measurement per ADR-016 and the S83 CLAUDE.md bullet on deriving a gate's scale first.

---

*Captured 2026-09-25, 10:55–11:15 IST. Observations are of illustrative and sample content only; no live target figure was seen. Working notes: session scratchpad `s84_render_study_notes.md` (not uploaded).*
