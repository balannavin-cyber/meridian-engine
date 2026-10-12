# Marketview user manual

**MERIDIAN · Marketview** (https://marketview.meridianalpha.in)

| | |
|---|---|
| Manual version | v0.3.1 (draft) |
| Board | meridian-connect `804d684` per CURRENT.md; served bundle `index-CadQe4qO.js` |
| Status | All parts drafted from pass 1 (09:00–09:12), pass 2 (09:40–09:41) and the capture pass (09:52–10:21), 2026-10-12. Pass 3 (after the close) and an expiry-day read are owed. |

> **Read this first.** Marketview is a measuring board, not a signal service. No tile here tells you to buy or sell. Several tiles carry the board's own warnings: "band not measured", "unit definition pending", "not built", "declined on evidence". This manual repeats those warnings wherever they apply. Where the board says something is unmeasured, the manual says so too, and does not fill the gap with a guess.

---

## How to use this manual

Each tile, chart and mark is described with the same eight headings:

| Heading | What it gives you |
|---|---|
| **What it is** | One plain sentence. |
| **How to read it** | What higher, lower, cool or warm means. |
| **Worked example** | A real screen: date, time (IST), symbol and the values shown. |
| **What it is NOT telling you** | The tempting misreading. |
| **Caveats** | Calibration gaps and known defects, stated plainly. |
| **Read it with** | The tiles that give it context. These match the drawer's READ IT WITH chips. |
| **Source** | The database view and column it reads, plus the ruling that fixed its wording. |
| **Last verified** | Date and board build. A tile whose stamp is older than the current build is marked **UNVERIFIED**. |

Every tile also has an in-app **drawer** (§1.5). The manual expands the drawer for a newcomer. It never contradicts the drawer. Where this manual and the drawer seem to disagree, the drawer describes what the board does, and the disagreement is listed in §7.2 as a finding.

---

## Part 0 — Just enough options

This part assumes you know what a call, a put, a strike, an expiry and a premium are. Everything else is introduced here, and only because some tile needs it.

### 0.1 Open interest (OI)

**Open interest** is the number of option contracts open at a strike at a given moment. On this board OI is a **quantity at the current lot size**, not a count of contracts. Two things matter for reading the board:

- **OI says nothing about who holds the position.** One buyer and one writer make each open contract. A rise in OI means new positions were opened, but it cannot tell you whether buyers or writers started them. The board repeats this in several places: *"An OI change cannot tell writing from buying"* (ΔOI drawer); *"this does not say who bought or wrote"* (Flows captions).
- **OI is only as good as the vendor's feed.** On some sessions the vendor carried large OI on legs that had not traded at all. For SENSEX on 2026-09-25, 09-28 and 09-29, untraded legs held 33–94 % of front OI (TD-S95-NEW-1). Tiles built from OI levels are not protected against this. The only guarded surface is the Flows badge (§3, Flows; §5.4).

**ΔOI** is the change in OI between two moments. The board uses two reference moments:

- **"since 09:15"** on the OI tab: the first chain snapshot at or after 09:15 IST.
- **"since the pre-open"** on the Flows tab: the session's first front-expiry snapshot before 09:15 IST, usually about 08:30 for NIFTY and 08:35 for SENSEX.

### 0.2 Delta (Δ)

**Delta** is how much an option's premium moves for a one-point move in the index. A call's delta is between 0 and +1. A put's delta is between −1 and 0. Multiplying delta by OI and by spot gives an amount in rupees: roughly, how much index exposure those open options behave like. The board writes this in **₹ crore (Cr)**.

On this board the deltas come from the **vendor**, and the vendor's deltas fail a basic consistency check (put–call parity). For that reason the DEX tiles say *"Magnitude indicative, not measured … Read the sign."*

### 0.3 Gamma (γ)

**Gamma** is how fast delta itself changes as the index moves. It is largest for strikes near spot and close to expiry. The board weights each strike's gamma by its OI and writes the result as **γ exposure**, in "₹ Cr", with the warning **"unit definition pending"**. What one unit of this number means is still an open question (E-1 / E-D1). Compare its **sign** and its **share of the total**. Do not compare its size from one day to the next.

### 0.4 Why "dealer" is only a model

Many option boards assume a **dealer**, a market-maker who takes the other side of customers' trades and hedges. A typical assumption is that dealers are *long calls and short puts*. If that were true, positive γ would mean dealers buy dips and sell rallies ("dampening"). Negative γ would mean they sell dips and buy rallies ("amplifying").

MERIDIAN tested that assumption against NSE's published participant positions (P2, 2026-10-10, 340 sessions). The result was **regime-dependent**: the assumed side held in some periods and was inverted in others. P2 used NSE data only, so **SENSEX was not tested at all**. The board therefore labels its sign *"open-interest arithmetic, not a dealer claim"* and carries the phrase *"dealer side regime-dependent (P2)"* on the DEX tiles.

Read every "dealer", "dampening" and "amplifying" on the board as a name for the **sign of an OI-weighted sum**, not as a statement of who holds what. Some captions still say "dealer" outright (§7.2, findings F-1, F-7). Their wording is **under review** (TD-S96-NEW-1).

### 0.5 Implied volatility (IV) and the priced move

**IV** is the volatility the option prices imply, quoted in percent per year. The **ATM straddle** (the at-the-money call plus put) gives a rough size for the move the market is pricing **to expiry**. The board calls this the **priced move**. It is not a one-day range and not a σ (sigma) band: the board has no single agreed σ yet (E-2).

### 0.6 DTE, sessions and expiry legs

- **DTE** means days to expiry. The board mostly counts **sessions** (trading days) to expiry. One Flows sub-line counts **calendar days** ("6 cal d").
- An **expiry leg** is one expiry date. **W1 / front** is the nearest expiry; **W2 / back** is the next. MERIDIAN captures two legs, so the IV tab compares two points and does not draw a curve.
- **dte 0** is expiry day. Several tiles deliberately do not compute on dte 0 and say so: *"skipped on expiry day"*, `SKIPPED_EXPIRY`, *"no flow on expiry day"*.

### 0.7 Second-order sensitivities: ∂Δ/∂σ and ∂Δ/∂t

The Flows tab shows how the OI-weighted delta would change for two reasons other than a price move:

- **∂Δ/∂σ** is how much delta changes for a +1 point rise in implied volatility, with spot and time held fixed.
- **∂Δ/∂t** is how much delta changes as one calendar day passes, with spot and IV held fixed.

The board also shows the matching pair for gamma, **∂Γ/∂σ** and **∂Γ/∂t** (its labels use a capital Γ; see finding F-2). Their net is a small leftover of large opposing terms. That is why the board always shows them beside their gross.

---

## Part 1 — Getting around

### 1.1 Pages

The top bar has six pages. Health and Settings sit slightly apart and are quieter:

| Page | What it answers |
|---|---|
| **Home** | The day at a glance: spot, one sentence, six question cards. |
| **Board** | The main instrument: header strip, read sentence, six sub-tabs, strike ladder, drawer. |
| **Context** | Breadth and volatility. |
| **Structure** | Price-structure zones and the engine's signal stream. |
| **Health** | Whether the data writers are running. |
| **Settings** | The parameter store, read-only. |

The **NIFTY / SENSEX** toggle sits at the top right. Keys **N** and **S** also switch it. Switching keeps your sub-tab and resets the zoom to *Near spot*.

### 1.2 Board sub-tabs

**Overview · Pin · Gamma · OI · Flows · IV**, switched with keys **1–6**. Each sub-tab answers one question. Home repeats these questions as its card titles:

1. Overview: *What kind of day, and where are the edges?*
2. Pin: *How settled is the centre?*
3. Gamma: *Can I trust single strikes?*
4. OI: *What is actually written?* (see finding F-7 on the word "written")
5. Flows: *What must dealers trade if spot moves?* (see §0.4)
6. IV: *What do time and cover cost?*

### 1.3 The strike ladder and zoom

Every sub-tab except IV draws a vertical **strike ladder**. Strikes run top to bottom, high to low, and spot is marked across it. Three zoom modes sit above the ladder:

| Mode | Key | Window |
|---|---|---|
| **Near spot** (default) | `0` | spot ± the larger of 2.5 × straddle and 1.2 %, widened to whole strikes |
| **All levels** | `L` | the sub-tab's levels ± 2 strikes |
| **Full chain** | `F` | every stored strike |

**+ / −** zoom in and out, making a *Custom* window. When strikes get crowded the ladder becomes **dense**: it labels every fourth strike plus the level strikes, and shows readouts on level rows only. That is why the SENSEX ladder can show fewer numbers than the NIFTY ladder at the same zoom.

### 1.4 The header strip and the read

Above the sub-tabs sit the **header strip** (Part 2) and the **read**, one sentence summarising the strip, for example:

> *"Spot 73,181.3 sits in a dampening pocket, 1.1% under the call OI wall at 74,000. Flip carry is unmeasurable. Net gamma is -0.42 of gross."* (SENSEX, 2026-10-12, γ run 09:00 IST)

The read states what is there. It never predicts or recommends.

### 1.5 Drawers

Selecting a tile or list row opens its **drawer** on the right. Every drawer has the same slots:

| Slot | Content |
|---|---|
| Header | sub-tab · title · unit |
| Source line | where the text came from: `‹view› · COMMENT live` (the database view's own comment), `sql/ file · COMMENT not live` (written in the repo but not applied to the database comment), or `derived` |
| **WHAT IT IS** | |
| **HOW TO READ IT** | |
| **COMPUTED** | the view and column |
| **SCALE** | whether a measured band exists; usually *"band not measured — calibration gap"* |
| **CAVEAT** | |
| **READ IT WITH** | two or three chips that jump to related tiles |

The live build has **39** drawer entries. The IV sub-tab has **none** (finding F-9).

### 1.6 Two clocks

The board reads from two separate data runs, about 5 minutes apart:

- the **γ clock**, the gamma run (`gex_strike_snapshots` / `gamma_metrics`), which feeds spot, net γ, walls, pin and the ladder;
- the **chain clock**, the option-chain snapshot, which feeds flip, IV, ΔOI, the ∂Δ/∂σ and ∂Δ/∂t tiles and S\*.

The DEX tiles use a third time: the **settled run**, the last run at or before 15:15 IST.

A tile never mixes clocks without showing both times. When the two clocks drift more than one cycle apart, a clock chip appears in the strip: *"γ hh:mm · chain hh:mm"*. After 15:15 the DEX tiles (settled run) and the ∂Δ tiles (latest run) are **not one snapshot** (TD-S96-NEW-4). Check their times before comparing them.

### 1.7 Keys

| Key | Action |
|---|---|
| `N` / `S` | symbol |
| `1`–`6` | sub-tab |
| `0` / `L` / `F` | zoom mode |
| `+` / `−` | zoom in / out |
| `/` | strike search |
| `Space` | freeze / resume |
| `J` / `K` | step through signals on Context |

Keys act only when the board has focus: click a sub-tab first. *(Verified 2026-10-12 on staging: `3` and `S`. `?` is listed in the design note but has no handler on the live or staging build, so it is left out here. `/`, `Space` and `J`/`K` are not yet verified.)*

### 1.8 The 3D view

`/board/3d`, reached from the **3D ›** links on Gamma, OI and IV, is an optional drill-down with three modes:

1. **γ terrain**
2. **IV fence**
3. **Pain bowl**

It covers the last 14 sessions, with today marked *"partial"*. Height is |net γ| per strike at each session's settled run. Colour is sign. Holes are missing strikes, never zero. It is outside the parity work and is display-only. **R** resets the view; **Esc** returns to the 2D board.

---

## Part 2 — The header strip

The strip has ten cells in two rows. It appears on every Board sub-tab and summarises the symbol at a glance. Examples come from **pass 2** (2026-10-12, NIFTY 09:41 IST and SENSEX 09:40 IST) unless another time is given. Every cell in this part was last verified on 2026-10-12 against bundle `index-CadQe4qO.js`.

### 2.1 SYMBOL · EXPIRY

- **What it is.** The front expiry date and how many trading sessions remain until it.
- **How to read it.** "13 OCT / NIFTY · 1 DTE" means NIFTY's nearest expiry is 13 October, one session away.
- **Worked example.** NIFTY 09:41 showed `13 OCT · NIFTY · 1 DTE`; SENSEX showed `15 OCT · SENSEX · 3 DTE`.
- **Not telling you.** Nothing about the back expiry. For the back expiry, see IV → W2.
- **Caveats.** On the day this reads 0 DTE, several tiles deliberately stop computing (§5).
- **Source.** `gamma_metrics.expiry_date`; `v_iv_term_structure.dte_sessions`, leg 1.

### 2.2 SPOT

- **What it is.** The index level, shown two ways.
- **How to read it.** The big number is the **live tick**; the cell title says when, as in "SPOT · LIVE 09:41". The sub-line gives the change from the previous close, then **"board hh:mm @ x"**, which is the spot the γ run used. The ladder, the read sentence and the levels all use the *board* spot, not the live tick.
- **Worked example.** NIFTY 09:41 showed `22,524.3 · ▲+3.8 · +0.02 % · board 09:35 @ 22,538.4`. The live tick and the board spot differed by 14 points.
- **Not telling you.** The live tick and the board spot are not the same number, and the levels are measured from the board spot. In the Overview list, the "Spot · board hh:mm" row shows the change **at the board spot** (SENSEX 09:40: +130.3), while the strip shows the change **at the live tick** (−101.5). Both are correct for their own moment.
- **Caveats.** Before the first live tick the cell reads plain "SPOT" with the board value only, as seen at 09:00. While data is loading the change line can be blank for a moment.
- **Read it with.** CLOCKS (§2.10).
- **Source.** Live tick, plus `gamma_metrics.spot/ts` for the board spot.

### 2.3 NET Γ

- **What it is.** The sum of signed γ exposure across every strike of the latest γ run, in ₹ Cr. The unit is still open.
- **How to read it.** Look at the **sign** and at **net ÷ gross**, not the size.
  - The sub-line says "long γ" (positive) or "short γ" (negative), then the net-to-gross ratio, for example "0.10 of gross". A ratio near 0 means the book nearly cancels out. A ratio near ±1 means it is one-sided.
  - The bar under the number splits gross into its warm (negative) and cool (positive) parts.
- **Worked example.** NIFTY 09:41 showed `+9.2L Cr · long γ · 0.10 of gross`. At 09:00 the same symbol showed `−13.9L Cr · short γ · −0.23 of gross`, so the sign flipped across the open. SENSEX 09:40 showed `+5,444 Cr · long γ · 0.00 of gross`: positive, but so small against gross that the ratio rounds to 0.00. Treat that as balanced.
- **Not telling you.**
  - Who holds the gamma. "Long γ" is the sign of an OI-weighted sum (§0.4).
  - How big a move to expect. A positive sign does **not** mean a calmer day: the P1c test was inconclusive, and P1c, P1 and P2 have produced no pre-registered YES between them.
- **Caveats.**
  - The size has no agreed unit (E-D1), so do not compare magnitudes across days.
  - The strip/Overview drawer for this cell states the dealer reading as fact. The P2 caveat appears only on the Gamma-tab drawer (finding F-1).
  - The label uses a capital Γ (finding F-2).
- **Read it with.** Pin (γ-conc), Flip, and on the Gamma tab, Gross |Γ|.
- **Source.** `v_gex_abs_exposure.net_gex_cr`; net/gross = `net_gex_cr ÷ abs_gex_cr`. Rulings S94-F, ADR-015 Amendment A.

### 2.4 FLIP

- **What it is.** The spot level at which net γ, repriced as if spot were there, would cross zero. This is the "L3 repriced flip".
- **How to read it.** The value and its % distance from spot tell you how far price would have to travel before the sign of the OI-weighted γ changes. On the ladder it is the **dashed** FLIP line.
- **Worked example.**
  - NIFTY 09:52: `22,497 · −0.08 % from spot`, drawn as a dashed FLIP rule just below spot.
  - NIFTY 10:15: `22,453 · −0.15 %`. The ladder showed **"SPOT ≡ FLIP"** because both fell on the same strike row.
  - Before about 09:50, both symbols read **"carry unmeasurable"** and drew no value and no line.
- **Not telling you.** That price is drawn to or repelled by the flip. Nothing tests that.
- **Caveats.**
  - The flip needs a carry rate **r** derived from futures. When r cannot be measured, the cell names that state and does not guess. Status `UNMEASURABLE_R`.
  - Other named states are "no flip in grid" and "skipped on expiry day".
  - Flip is on the **chain clock**; spot is on the **γ clock**.
  - This flip is not the engine's older `flip_level`, which the board does not display.
  - At 09:41 the futures cell already showed a price (22,570), yet carry was still unmeasurable. See finding F-16.
- **Read it with.** Corridor, Priced move.
- **Source.** `v_gex_repriced_flip.flip`, `status` (ENH-131).

### 2.5 CORRIDOR

- **What it is.** The range from the put OI wall to the call OI wall, both chosen within an eligible σ band around spot.
- **How to read it.** The value is the two walls. The sub-line gives the state and the width as % of spot:
  - **inside**: spot is between the walls;
  - **above call wall**: spot is above the upper wall;
  - **below put wall**: spot is below the lower wall;
  - **undefined**.

  The small track shows where spot sits.
- **Worked example.** NIFTY 09:41 showed `22,500–22,600 · inside · 0.44 % wide`. At 09:00 the same symbol showed `22,500–22,500 · above call wall · 0.00 % wide`: both walls on one strike, a collapsed corridor. That is a property of the view, not a fault (MV-8). At 10:15 it showed `22,500–22,600 · below put wall`, with spot just under the lower wall.
- **Not telling you.** That the walls hold price. The P1 test found the day's high and low **did not land closer to the walls than to random strikes at the same distance** (n = 85, NIFTY).
- **Caveats.** The walls are raw OI, positional only. When the IV feed is stale, the eligible band is less certain.
- **Read it with.** Pin, Spot.
- **Source.** `v_gex_strike_walls.put_wall, call_wall, corridor_state` (ENH-120). P1 wording per S94-D.

### 2.6 PIN (γ-conc)

- **What it is.** The single strike holding the largest share of gross |γ|.
- **How to read it.** The value is the strike. The sub-line gives its share of gross and the **lead** over the runner-up in share points. "≡ put OI wall" appears when the pin sits on the same strike as a wall.
- **Worked example.**
  - NIFTY 09:41: `22,700 · 10.8 % of gross · lead 1.7 pts`.
  - SENSEX 09:40: `72,000 · 6.6 % of gross · lead 0.7 pts · ≡ put OI wall`. A lead of 0.7 points means #1 and #2 are almost tied.
- **Not telling you.**
  - Where price will settle. *"Concentration is not a forecast of the close"*; the pin renders, it does not predict (S74).
  - The same P1 null result applies as for the walls.
- **Caveats.** A small lead means "top strike" is close to arbitrary. Always read the lead, not just the strike. While loading, the cell can briefly read "no run" (finding F-8).
- **Read it with.** Corridor, Net Γ, and the Pin tab.
- **Source.** `v_gex_strike_rank`, ranks 1–2 (ENH-125).

### 2.7 IV · VIX

- **What it is.** Front-leg ATM implied volatility, India VIX, and the priced move.
- **How to read it.** "17.0 · 15.09" means front ATM IV is 17.0 % and VIX is 15.09. The sub-line gives VIX's change today, then the priced move in points and %.
- **Worked example.** NIFTY 09:41 showed `17.0 · 15.09 · ▲VIX +0.65 · ±196 · ±0.87 %`. *(SENSEX showed ▲VIX +0.65 at 09:40; NIFTY showed +0.71 at 09:41.)*
- **Not telling you.** The priced move is **to expiry**, not one day, and it is not a σ band.
- **Caveats.** Before the open the sub-line read "◆VIX 0.00". The ◆ glyph is not defined anywhere (finding F-10). Read it as "no change yet".
- **Source.** `v_iv_term_structure` leg 1; `gamma_metrics.vix`, `.straddle_atm`.

### 2.8 FUT · BASIS

- **What it is.** The front-month index future and its premium over spot.
- **How to read it.** "22,570 · +56.3" is the futures price and its basis over spot. The sub-line gives the futures' change and its expiry ("27 OCT").
- **Worked example.**
  - Before 09:30 both symbols read **"futures from 09:30"**.
  - At 09:41, NIFTY showed `22,570 · +56.3 · ▼−18.3 · 27 OCT`.
- **Caveats.** The futures are the monthly contract, not the weekly option expiry.
- **Source.** `index_futures_snapshots`.

### 2.9 OPEN · GAP

- **What it is.** The day's opening gap from the previous close.
- **How to read it.** The value is the gap in %. The sub-line gives the pre-open print, the final open, the previous close and whether the gap has been filled.
- **Worked example.**
  - 09:41, NIFTY: `▲+0.50 % · pre-open 22,593 · final 22,633 · prev 22,520 · gap filled`.
  - Before 09:11: `no pre-open print · prev 22,520`.
- **Caveats.** "prev close missing" appears for a few seconds while loading (finding F-8).
- **Source.** `market_spot_snapshots` (pre-open 09:11; final from the 09:16 bar).

### 2.10 CLOCKS

- **What it is.** The times of the two data runs behind the board (§1.6).
- **How to read it.** "γ 09:35 · chain 09:40 · 5 min apart" means the ladder, net γ and levels are from 09:35, while flip, IV and ΔOI are from 09:40. The cell appears only when the clocks are more than one cycle apart.
- **Worked example.**
  - NIFTY 09:41: `γ 09:35 · chain 09:40 · 5 min apart`.
  - SENSEX 09:40: `γ 09:30 · chain 09:40 · 10 min apart`.
  - Not shown in pass 1 (09:00), when the two runs were close.
- **Not telling you.** That the board is broken. Two clocks are by design. The cell exists so you never compare a γ-clock number with a chain-clock number without knowing they are minutes apart.
- **Source.** `v_gex_strike_walls.ts` against `v_gex_repriced_flip.ts`.

### 2.11 The read

One sentence under the strip, for example *"Spot 22,538.4 sits in an amplifying pocket, 0.2% above the put OI wall at 22,500. Flip carry is unmeasurable. Net gamma is 0.10 of gross."* (NIFTY 09:41).

- **"Pocket"** is the sign of the γ terrain at spot's own strike row. It can differ from the overall Net Γ sign: here the overall book was long γ while spot's row was amplifying.
- The read uses the **board** spot, not the live tick.
- It describes and never predicts.

## Part 3 — Each sub-tab

Each sub-tab has the same layout: a **list** of values on the left, the **strike ladder** in the middle, and the **drawer** on the right for whichever row is selected. A tile covered in Part 2 is not repeated here; only what the sub-tab adds is described.

### 3.1 Overview: *What kind of day, and where are the edges?*

**List rows.** Net Γ · Flip · Corridor · Pin (γ-conc) · Priced move · Spot · board hh:mm · Time to expiry. The first five repeat the strip (Part 2). The other two:

- **Priced move.** The ATM straddle as ± points and "± % to expiry". It lights the **left gutter** on the ladder.
  - *Example (SENSEX 09:40):* ±933, ±1.28 % to expiry.
  - *Not telling you:* a one-day range. It *"Includes time value to expiry"*.
  - *Source:* `gamma_metrics.straddle_atm`.
- **Time to expiry.** Trading sessions left, e.g. "3 sess · front 15 OCT". Drawer: *"Fewer sessions concentrate gamma near spot."*
  - *Source:* `v_iv_term_structure.dte_sessions`, leg 1.

**The ladder: signed γ by strike.**

- Bars run from a centre axis, **warm to the left (amplifying)** and **cool to the right (dampening)**. The right-hand column reads each bar's value.
- Spot is the bright solid rule. The walls are thin solid rules with pills, the pin is a dotted γ-CONC rule, and the flip is a dashed rule when it exists.
- The faint fill behind the bars is the **terrain**.
- **Example:** SENSEX 09:40, call OI wall 73,000 with +78,596 on its row, put OI wall ≡ γ-conc at 72,000 with −88,006.
- **Not telling you:** each bar is OI × γ arithmetic. It is not a measure of which way hedgers will trade.

**The "γ CEILING / FLOOR · pending measurement" toggle** sits above every ladder and is permanently disabled. The level has no column in the database (E-3). It is not a wall and is never drawn.

### 3.2 Pin: *How settled is the centre?*

The header line says which session the tiles describe: **"pin state · this session · front leg"** in market hours, or **"pin state · previous session yyyy-mm-dd"** before the first cycle of the day.

| Tile | What it is | Worked example (NIFTY 09:41) | Not telling you / caveats |
|---|---|---|---|
| **PIN (γ-conc)** | the strike with the largest share of gross \|γ\| | 22,700 · 10.8 % · dampening | Not a forecast of the close (S74). P1: high/low no closer to it than to random strikes (n = 85). |
| **PIN STATE** | whether the leader has held through today's open 5-minute cycles: NO PIN · SHIFTING · STABLE · LOCKED | SHIFTING · held 3 cycles · 15 min · live · unreconciled | Thresholds are seeded parameters, *"not yet re-measured against outcomes (D-6)"* (Settings → PIN_STATE). Rows can be revised until reconciled after the close. |
| **CONVICTION** | lead clarity scaled by time to expiry | 0.40 · stage 1 · no band (D-6) | A number only, never a word. Compare within one symbol. Stage 2 needs about six weeks of history. The formula deviates from the parity target's undisclosed one. |
| **RUNNER-UP** | the #2 strike and #2 ÷ #1 | 22,650 · #2/#1 = 0.84 | Near 1 means two strikes share the centre. Ranking is by \|γ\| only; the "ranked pressure" variant was declined on evidence (D-5a). |
| **LEAD** | #1 share − #2 share, in points | 1.7 pts | *"A number, not a state."* No LOCKED/CONTESTED wording (D-6). |
| **LEADER TODAY** | each stretch with the same leader | 1 change: 22,500 → 22,700 · 4 cycles · 09:20–09:35 | Front leg only. Before the open it shows the previous session under this "today" label (finding F-3). |
| **CONCENTRATION (HHI)** | the true Herfindahl index, Σ share², plus top-5 share | 0.060 · top-5 share 44.8 % | The only true HHI on the board. Its natural level moves with time of day and DTE; no percentile yet. |
| **PIN BAND** | the τ-weighted pin zone | 22,600–22,800 | A different measure from the pin point; the two can disagree. Before the open, the NIFTY pin (22,400) sat outside its band (22,600–22,900), and SENSEX's band was the single strike 74,000 (finding F-13). *"Renders, does not predict"* (S74). |
| **PIN DISTANCE** | signed % from spot to the pin | +0.72 % above spot | No σ distance until a canonical σ exists (E-2). |
| **LEGACY PIN-RISK SCORE** | the older 0–100 score | 24/100 · number only · no band (E-D4) | Its old weak/moderate/strong words were never measured and were removed. Kept for continuity only; not part of the pin layer. |

**The ladder: share of gross |γ|.**

- Each strike's bar runs from the left edge with a "#rank · share" readout. The top 10 are full strength; rank > 10 is faint. Colour is the strike's γ sign.
- **"γ-CONC #1"** and **"#2"** are outlined.
- *Example (NIFTY 09:41):* #3 22,600 and #4 22,400 both read 8.6 %. A tie shown as two ranks is a tie.

### 3.3 Gamma: *Can I trust single strikes?*

| Tile | What it is | Worked example | Not telling you / caveats |
|---|---|---|---|
| **Top-strike share** | the largest strike's share of gross \|γ\| (max ÷ sum), with a DTE bucket (0 · 1-2 · 3+) and a call/put split in the drawer | NIFTY 09:41: 10.8 % · 1-2 DTE bucket · at 22,700. SENSEX 09:00: 10.9 %, calls 9.7 %, puts 12.9 %. | *"This is max/sum, not a Σshare² index — never call it HHI."* 0-DTE concentrates naturally. The call/put split matters: one side can be concentrated while the other is spread. |
| **Gross \|Γ\|** | the sum of absolute γ exposure | SENSEX 09:00: 10.5L Cr | Unit pending (E-D1); compare within a day. |
| **Net Γ** | the same value as the strip, plus "Σ crosses zero n×" | SENSEX 09:00: −4.5L Cr · amplifying · Σ crosses zero 3× | This drawer carries the P2 sentence: *"This reading assumes dealers are net long calls and short puts; NSE aggregate participant OI shows that only in some regimes (P2, S94)."* Where the white dots cross zero, the running sum changes sign; *"that is not the repriced flip."* |
| **Contributing strikes** | strikes with non-zero γ out of all stored | SENSEX 09:00: 161 / 170 · 95 % | Unquoted strikes count as non-contributing. |
| **Net-long γ strike** | the strike with the largest positive net γ (dotted NET-LONG γ rule) | SENSEX 09:00: 74,000 · +1.12 % from spot · not "near spot" | It can sit far from price (ADR-024 Amendment A). |
| **Net Γ today** | sparkline of net γ at each run today | SENSEX 09:00: 6 runs · 08:30–09:00 | Drawn only with ≥ 3 runs. The pre-open runs count as "today". γ clock. |

**The ladder** is the Overview ladder plus **white dots**: the cumulative Σγ from the top strike down.

**GAMMA RIVER.** *"settled net γ per session · history, not today's read"*, covering 30 sessions. Its marks:

| Mark | Meaning |
|---|---|
| ● | settled net γ |
| ○ | an incomplete session |
| grey bar | the session's min–max |
| line | spot, right scale |
| "0" under a day | 0-DTE |
| dashed break | no data |

- **Read the grey bar, not only the dot.** The daily value is one sample: a day can close positive inside a range that went far negative.
- *Source:* `v_gex_net_gamma_river` (ENH-126).

### 3.4 OI: *What is actually written?*

The question on the Home card says "written", but OI cannot tell writing from buying (finding F-7). This tab shows **how much is open, where**, not who opened it.

| Tile | What it is | Worked example (NIFTY 09:41) | Not telling you / caveats |
|---|---|---|---|
| **Max pain** | the strike where option holders' total payout would be lowest, at the γ run | 22,550 | *"A positional concentration, not a forecast or pressure sign."* MERIDIAN computes max pain two ways (γ run and raw chain); which is canonical is undecided (P5 / E-D2). This tile uses the γ run. |
| **Distance to max pain** | signed % from spot | +0.05 % · above spot | Uses the γ-clock spot. |
| **Call OI wall** / **Put OI wall** | the eligible strike with the most call / put OI | 22,600 / 22,500 | *"OI is positional; grey does not encode pressure sign."* P1 null result as in §2.5. |
| **Total OI** | calls + puts, at the current lot size | 4,771.9L · calls +2,362.7L · puts +2,409.2L | A quantity, not contracts. Do not compare across products without context. |
| **ΔOI net** | OI change since the first chain snapshot at or after 09:15, per side | C +798.9L · P +361.9L · since 09:15 · chain 09:40 | Cannot tell writing from buying. Chain clock. Before 09:15 it reads **"ΔOI · no 09:15 anchor yet"**. A strike present at only one of the two times shows **n/c**, never zero. |

- **SENSEX** shows **"ΔOI · n/a (SENSEX · TD-S84-NEW-4)"** permanently. Its 09:15 baseline can come from a stale vendor row, so it is withheld (S92-H).
- **The ladder ("butterfly").** Put OI extends left in mid grey and call OI right in light grey, with a total-OI readout. The max-pain ink rule and the faint **pain valley** curve sit behind. Small **ticks** under the bars show ΔOI: cool = rose, warm = fell (NIFTY only).

### 3.5 Flows: *What must dealers trade if spot moves?*

Read §0.4 first. Everything here is OI arithmetic, and the dealer wording on this tab is under review.

**The bordered badge** at the top always reads *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not built"*.

- ΔOI is never split into "new writing", "covering" and so on.
- That classification was **declined on evidence** (S96-I): option premium moves with spot, so the split would partly restate the price move.
- This is a permanent, recorded deviation.

**Hedge flow vs spot move.** A chart of ₹ Cr at −2, −1, −0.5, +0.5, +1 and +2 %, plus the **HEDGE PER 1 %** tile.

- *Worked example (NIFTY 09:41):* HEDGE PER 1 % = **SELL 9,201**; −1 %: BUY 9,201 · +1 %: SELL 9,201.
  - The book was long γ (+9.2L Cr), so the model buys on falls and sells on rises.
  - At 09:00, when NIFTY was short γ, the same tile read BUY 13,886 for +1 %.
- *How to read it:* the six points lie **on one straight line by construction** (flow = −net γ × move), so they say no more than the one-percent figure.
- *Not telling you:* what anyone will actually trade. It is a first-order model, and it ignores the second-order terms in the tiles below.
- *Caveats:* the unit is pending (E-D1). "L3 flip not available." appears when the flip has no value; otherwise the flip is a dashed line on this chart. The read sentence and the drawer say "dealers would buy/sell", which is dealer wording beyond P2 (finding F-7).
- *Source:* `v_dealer_flow_sim`.

**∂Δ/∂t · PER DAY** and **∂Δ/∂σ · PER VOL PT** (§0.7).

- **What they are.** How the OI-weighted delta, in ₹ Cr of delta-notional, would change over one calendar day, or for a +1 IV point.
- **How to read them.** The big number is the book. When the session's flow can be shown, a sub-line reads *"from x at pre-open OI · ±y since hh:mm"*, and **bricks** appear under the number (§4.4). Each tile has its own scale.
- **Worked example (NIFTY, chain 09:50, read 09:52).**
  - ∂Δ/∂t: **−39,393 Cr / 39,393 Cr · net/gross −1.00** = **−25,475** at pre-open OI **−13,918** since 08:30.
  - ∂Δ/∂σ: **+5,210 Cr / 5,210 Cr · net/gross 1.00** = +3,232 + 1,978.
  - Both sums check exactly.
  - Earlier the same morning these tiles showed *"unmeasurable r"*, with *"no flow before 09:15"* at 09:00 and *"flow · different run — not drawn"* at 09:40–09:41. They became measurable between 09:41 and 09:52 (finding F-16).
- **Not telling you.** Who holds the position, or what happens next.
- **Caveats.**
  - *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not built"*.
  - dte 0 is skipped, never floored.
  - The ∂Δ/∂σ drawer notes that the underlying column is "per +0.01 of σ, not per 1.00".
  - **Wording in transition (S97-A).** On the live build the caption reads *"Dealer delta-notional drifts −39,393 Cr per calendar day (gross 39,393 Cr); bars per strike. 21,580 qty of ΔOI has no priced greek and is not counted; this does not say who bought or wrote."* (NIFTY 09:52). A wording round approved 2026-10-12 (staging `c0aad8d`, promotion owed) changes it to *"Delta-notional drifts {net} per calendar day (gross {gross}); dealer side regime-dependent (P2); bars per strike."* It also removes "dealer" from both drawers' WHAT IT IS lines and rewrites the COMPUTED sign note. This manual follows the new wording once promoted. Until then, read "dealer" here as the sign of an OI-weighted sum (§0.4).
- **Source.** `v_gex_greeks_l2_net`; flow from `v_delta_drift_flow_vs_book` (ENH-144); rulings S96-F, S96-G.

**∂Γ/∂t · PER DAY** and **∂Γ/∂σ · PER VOL PT**.

- The same idea applied to gamma. The net is *"a small residue of large opposing terms"*, so the tile always shows **net beside gross**; the small bar is |net| ÷ gross.
- **Never read the net alone.** No flow is shown for this pair.
- *Worked example (NIFTY, chain 09:50):* ∂Γ/∂t **−4.7L Cr / 40.5L Cr · ratio −0.12**; ∂Γ/∂σ **+60,256 Cr / 5.3L Cr · ratio 0.11**. Each net is about a tenth of its gross, which is why it must be read with the gross.

**EXPIRY LEG.** Which expiry the second-order tiles and bars describe (e.g. "15 OCT · chain 09:40").

- On the front leg's expiry day, the front leg is skipped and the next leg is shown.
- Status values: OK · SKIPPED_EXPIRY · UNMEASURABLE_R · NO_LEGS.

**NET DEX · CALL DEX · PUT DEX (OI proxy).**

- **What they are.** How many ₹ crore of the index the open options *behave like*, from OI × each option's own delta (calls +, puts −).
- **How to read them.**
  - **Line 1:** the book and its **gap**, e.g. "−13,290 Cr · gap 8,16,465 of 48,73,94,050 qty". The gap is OI with no published delta, left out of the total.
  - **Line 2:** "calls +, puts − · front leg 13 OCT · 1 cal d · settled 09:40". *Settled* is the last run at or before 15:15. After 15:15 it stays at that run, so the morning shows the previous session's book.
  - **Line 3 (market hours):** *"from x at pre-open OI · ±y since hh:mm"*. The book = pre-open value + flow.
  - **Bricks** under the number share **one scale** across the three tiles: solid = held, light = added, dashed outline = removed.
- **Worked example (NIFTY 09:41).**
  - Net DEX −13,290 Cr = **−15,119** at pre-open OI **+1,829** since 08:30.
  - Call DEX +98,702 = +58,224 + 40,477.
  - Put DEX −1.1L = −73,344 − 38,648.
  - The three lines add up as stated (±1 Cr rounding).
  - SENSEX 09:40: Net −5,577 = −7,740 + 2,163.
- **The flow chip** under Net DEX compares the **sign** of the flow since the pre-open with the sign of the book.
  - *Worked example:* both symbols read **"flow since 08:30 · against book"** (NIFTY 09:41, SENSEX 09:40). On both, net flow since the pre-open was positive while the net book was negative.
  - When it cannot say, it shows a reason line instead: *"no badge · untraded OI on this snapshot"*, *"no badge · a net is zero"* or *"no badge · sign depends on the delta used"*. Before 09:15 it draws nothing.
- **Not telling you.**
  - *"This number does not say who holds the position."*
  - The chip *"shows only whether flow and book agree in sign. Says nothing about what happens next — M-P7 tested that it can speak, not that it predicts."*
  - The chip is a neutral colour on purpose. "Against book" is not a warning.
- **Caveats.**
  - *"Magnitude indicative, not measured"*. Vendor delta fails put–call parity. **Read the sign.**
  - Flow is itself a partial cancellation: median |net| ÷ gross is 0.27 on NIFTY and 0.19 on SENSEX.
  - On dte 0, greek gaps can flip the total's sign.
  - The untraded-leg guard protects **the chip only**. The DEX numbers themselves can be inflated on sessions where the vendor reports OI on legs that never traded (TD-S95-NEW-1; SENSEX 09-25, 09-28 and 09-29).
- **Source.** Book: `v_dex_standing_book` (ENH-140). Flow and chip: `v_dex_flow_vs_book` (ENH-143). Rulings S94-G/H/I, S96-C/D/E.

**ZERO-Δ LEVEL · S\*.**

- **What it is.** The spot level at which the open options, each repriced there at its own IV, would carry zero net delta. It is drawn as a **dotted** line on the ladder.
- **How to read it.** Below S\*, the repriced book is net short the index; above it, net long.
- **Worked example (NIFTY, chain 09:50).** *"22,533 · +12 pts · +0.06σ above chain spot 22,520.8 · chain 09:50 (book settled 09:50)"*. S\* is measured from the **chain** spot, which is a different spot from the strip's board spot. Before about 09:50 it read *"r unmeasurable"*.
- **Not telling you.** *"A level from today's book, not a forecast: nothing tests whether price moves toward it."*
- **Caveats.**
  - It can disagree in sign with Net DEX, which uses vendor delta (2 of 7 gate days).
  - Chain clock, not the DEX settled run.
  - Not computed on expiry day.
- **Source.** `v_dex_repriced_zero` (ENH-141).

**The Flows ladder** draws whichever layer is selected: a DEX tile or a ∂ tile.

- The note above it names the layer and time, e.g. *"bars · Net DEX · held / added / removed since 08:30 · settled 09:40"*.
- The caption under it restates the total and the gaps.
  - *Example (NIFTY 09:41):* *"Net DEX · OI proxy −13,290 Cr over strikes with a published delta; 8,16,465 qty of OI has no published delta and is not counted. Bars per strike. 28,080 qty of ΔOI has no published delta and is not counted; this does not say who bought or wrote."*
- **`·`** marks a strike with OI but no delta: a gap, never zero.

### 3.6 IV: *What do time and cover cost?*

This tab is on the **chain clock** only (e.g. "chain clock · 12 Oct 09:05 IST"). It has no zoom modes and **no drawers** (finding F-9).

- **Term structure** (*"front vs back · 2 legs captured"*). Two cards, **W1 · FRONT** and **W2 · BACK**, each with:
  - ATM IV and the ATM strike;
  - CE and PE IV;
  - **SPREAD VS FRONT** (W1 is always +0.00);
  - **FWD VOL FROM PREV**: the volatility implied for the period between the two expiries, so W2 only;
  - **"data quality · CE−PE parity gap"**: how far apart the call and put IVs at ATM are. Large gaps mean noisier quotes.

  The headline says **BACKWARDATION** (front IV above back) with the slope in vol points.
  - *Example (NIFTY 09:05):* W1 13 Oct 16.82 %, CE 19.78 % / PE 13.87 %, parity gap +5.91; W2 19 Oct 14.13 %; backwardation, slope −2.69; fwd vol 13.63 %.
  - *Not telling you:* a term-structure curve. Two points are not a curve. PBD B.7 rules out regime words, yet "BACKWARDATION" is shown (finding F-9).
- **IV smile.** Implied volatility across strikes for W1 or W2.
  - ● PE side (grey) · ● CE side (light): each strike uses its out-of-the-money side.
  - ◯ ATM.
  - **┆ K98:** the strike about 2 % below the forward, which the server uses for skew.
  - ▏ OTM absent: no out-of-the-money quote.
  - "zero-OI (quoted) excluded · n strikes".
  - **Skew line:** "skew 98 +4.31 vol pts @ 22,150" (NIFTY 09:05) is the IV at K98 minus ATM IV. It is labelled *"skew from view · not recomputed"*.
  - *Caveats:* skew is not comparable across legs. On expiry day it reads skipped. The Context page shows a *different* skew figure computed in the browser (finding F-5).
- **Source.** `v_iv_term_structure` (ENH-130); `v_iv_surface` (ENH-132).

## Part 3b — Home, Context, Structure, Health, Settings

All examples on this page come from pass 1, 2026-10-12, roughly 09:05–09:12 IST.

### 3b.1 Home

**Masthead.** Shows the symbol, the front expiry, the sessions left, spot at the γ run, and the change since the previous close.

- Example (NIFTY, 09:11): *"NIFTY · 13 OCT · 1 SESSION LEFT · 22,623.9 · γ run 09:05 · +103.5 · +0.46 %"*.
- The read sentence comes next. It is the same sentence that appears on the Board.

**Six question cards.** Each card opens the Board sub-tab with the same number (keys 1–6). Each carries a one-line summary and a small picture.

| Card | Example line (NIFTY, 09:11) | Note |
|---|---|---|
| 1 OVERVIEW | "corridor 22,500–22,900 · carry unmeasurable" | |
| 2 PIN | "22,400 holds 10.0 % of gross · lead 1.4 pts" | |
| 3 GAMMA | "net/gross -0.23 · top strike 10.0 %" | |
| 4 OI | "max pain 22,500 · pin 22,400 · +100" | The "+100" is the gap in points between max pain and pin. |
| 5 FLOWS | "−1 %: SELL 13,816 Cr · +1 %: BUY 13,816 Cr" | Read with §0.4: the "dealers" premise is a model. |
| 6 IV | "front 16.8 · back 14.1 · straddle ±203" | |

Two of the card titles use wording the drawers do not support: card 4 asks "What is actually written?" and card 5 asks "What must dealers trade…?" (finding F-7).

**Context line.** Example: *"CONTEXT · DAILY · trend up · aligned · as of 09 Oct ›"*. This is the daily ambient summary, and it opens Context. It is dated to the last settled session, not to today.

### 3b.2 Context — "Breadth & Volatility"

This page still uses the **older header strip**:

- a LIVE pill;
- SPOT with a change figure;
- NET Γ in full digits, e.g. "-13,81,560.7 Cr";
- MAX Γ (the net-long γ strike);
- MAX PAIN;
- PIN SCORE (the legacy score);
- VIX;
- EXPIRY with a countdown.

Its spot-change figure does not match the Board or Home. At 09:11 NIFTY showed **+392.1 (+1.76 %)** here, against +103.5 on Home and −10.7 on the Board (finding F-4). Use the Board's figure.

| Card | What it shows | Example | Caveat |
|---|---|---|---|
| **WCB** | weighted constituent breadth, /100, with coverage | "— /100 · coverage 0.0 % · as of 09/10 15:40" | A constituent with no tick in the last 10 minutes drops out and is never filled with a stale value (S90-G). Before the open, coverage is 0 % and the value shows as a gap. |
| **MARKET BREADTH** | advancing vs declining share, and the A/D ratio | "61 % adv · A/D 1.56 · ↑772 / 494↓" | Not documented in the project docs (register K7). |
| **INDIA VIX** | the VIX level | 14.38 | |
| **IV SKEW** | ATM put IV ÷ ATM call IV − 1, computed in the browser | "−29.9 % CE · ATM 22,600 · CE 19.8 / PE 13.9"; it showed "iv not populated" while loading | Not the same measure as the IV tab's skew 98 (finding F-5). |

This page is not yet the Context page described in the board design. It has no Ambient, Expiry memory or Signals sections (finding F-6).

### 3b.3 Structure — "Structure & Signals"

The page uses the same older header strip as Context. It then has two panels.

**ICT ZONES — NEAREST TO SPOT** shows "10 of 40 · sorted by distance to spot". Each row carries:

- a tier chip (SKIP or TIER2);
- a pattern (BULL_FVG, BEAR_FVG, BEAR_OB);
- the source date;
- the price range;
- the distance from spot to the zone's **midpoint** in %. A zone that contains spot can therefore still read "+0.02 % above".

These zones come from a writer that last succeeded **26 days ago** (Health, `build_ict_htf_zones.py`, as of 09:11). The list is a record of older structure, not today's.

**TODAY'S SIGNALS — STREAM** lists the engine's signal rows: time, strike, grade, action. Example (NIFTY): rows from 08:30 to 09:00, each "22,500 · D · BUY_PE".

- These rows were written before the market opened.
- The meaning of the grade "D" is not established (S90).
- **This manual does not present these rows as trading signals, and neither should you.** They are a log of what the engine wrote (finding F-12).

### 3b.4 Health

| Tile | Meaning |
|---|---|
| **OVERALL** | System status. It read **CRITICAL** at 09:11. Health is not calendar-aware yet (MV-4), so it can read CRITICAL for reasons that are expected at that hour. |
| **WRITER FLEET** | Healthy writers out of tracked writers, e.g. "9/15 · 6 stale". |
| **TOKEN STATUS** | When the broker token last refreshed, and the last HTTP status. |
| **WRITER FRESHNESS** | One row per script: last success, age, expected cadence, host, status. Check this table first when a Board tile looks stale. The note "outside trading hours — staleness expected" appears outside market hours. |
| **ERROR RATE / TOP ERRORS** | Non-success exits in the last 24 hours. |

### 3b.5 Settings

Settings lists the parameter store, grouped by section:

- Calibration
- Capital & sizing
- Display
- Connections
- Manual actions
- About

Each parameter row shows key · value · last changed · **reason**.

The page is **read-only** (S90-E). Parameters change only through the database's own audited path, and every change carries a reason.

Rows of note:

- **PIN_STATE** thresholds read "ENH-133 provisional, owes D-6 calibration". This is the source of the Pin state words in §3.2.
- **WALLS** band 1.5 carries the sweep that chose it.

The capital keys show values whose units are not stated on the page. The manual does not interpret them (finding F-14).

### 3b.6 The 3D view

See §1.8.

---

## Part 4 — Visual grammar

### 4.1 Colour carries sign, and nothing else

| Colour | Meaning |
|---|---|
| **Cool (blue)** | positive sign: dampening, long γ, OI added, positive DEX |
| **Warm (orange)** | negative sign: amplifying, short γ, OI removed, negative DEX |
| **Light grey / mid grey** | calls / puts on the OI butterfly and IV smile; grey carries side, never pressure |
| **Pale gold** | your selection and the active zoom mode only |
| **Dark red strip** | stale data, at the top of the page only, never inside a chart |

Size is shown by **length**, never by colour strength. Signs are always written out (`+` and `−`), so colour is never the only carrier.

Neither the green/red nor the "good/bad" reading of cool/warm applies. Cool is not "safe" and warm is not "danger". They are the two signs of an OI-weighted sum (§0.4).

### 4.2 Lines on the ladder

| Line | Style | Pill |
|---|---|---|
| Spot | solid, bright, glowing | **SPOT** |
| Flip (the L3 repriced flip) | **dashed** | **FLIP** |
| Call / put OI walls | solid, thin | **CALL OI WALL / PUT OI WALL** |
| γ-conc (pin), Net-long γ, K98, **S\*** | **dotted** | γ-CONC, NET-LONG γ |
| Max pain | ink rule, with a faint "pain valley" curve | MAX PAIN |
| γ ceiling / floor | not drawn | toggle reads *"pending measurement"* |

When two levels fall on one strike, the rule is drawn once and the pill joins them with **≡**, for example *"PUT OI WALL ≡ γ-CONC"*. On NIFTY at 09:00 on 2026-10-12 it read *"CALL OI WALL ≡ PUT OI WALL"*, both walls on 22,500. No ring or highlight marks a coincidence. A coincidence is only two levels on one strike, not added confirmation.

### 4.3 Gutters and bands

- **Left gutter: priced move.** It lights strikes within ± the ATM straddle of spot.
- **Right gutter: pin band.** It fills strikes inside the τ-weighted pin zone. The pin band and the pin point are different measures; see Part 3, Pin.
- **Terrain.** A faint fill behind the γ bars, slightly stronger inside the corridor.

### 4.4 Bricks: solid, light, dashed outline

On the Flows tiles and the Flows ladder, a value that can change through the day is drawn as **bricks**, measured from the session's pre-open:

| Mark | Meaning |
|---|---|
| **Solid** | held since the pre-open |
| **Light** (same colour, paler) | added since the pre-open |
| **Dashed outline** | removed since the pre-open |

If a value changes sign during the day, the held part is empty: the added part runs from 0 to *now* on one side, and the removed part runs from 0 to the *pre-open value* on the other. The sub-line spells out the numbers: *"now · from x at pre-open OI · ±y since hh:mm"*. "At pre-open OI" means the pre-open open interest valued at **today's** delta, so the change reflects OI only, not repricing.

The three DEX tiles share **one scale**. The two ∂Δ tiles each have **their own scale**, because their units differ.

### 4.5 Chips and badges

| Mark | Meaning |
|---|---|
| **Bordered badge** on Flows | the fixed notice *"flow-vs-book shown on unclassified ΔOI; classification (D-4) not built"* |
| **Flow chip** on Net DEX | *"flow since hh:mm · same sign as book"* or *"… · against book"*; neutral colour, never green or red, never a number |
| **Dashed-outline chip** | a named absence: something the board knows it does not have, in plain words |
| **≡ pill** | two levels on one strike |
| **READ IT WITH chips** | in the drawer; jump to the related tile |

### 4.6 Gaps are drawn as gaps, never as zero

This is the board's most important rule. When a value was **not measured**, the board shows a gap:

- `·` on a ladder row;
- **n/c** (not comparable) for ΔOI;
- a **dashed break** in a time series;
- a hollow **○** for an incomplete session;
- a named state in words.

It never shows **0**. A zero would state a fact that was never measured, for example "perfectly balanced". When the board does show **0**, or an empty bar track, the value was measured and really is zero.

---

## Part 5 — Status words

| Word on the board | Where | What it means |
|---|---|---|
| **unit definition pending** / **unit pending (E-D1)** | Net Γ, Gross \|Γ\|, Hedge per 1 % | The size of this number has no agreed real-world unit yet. Compare signs and shares, not magnitudes across days. |
| **band not measured — calibration gap** | most SCALE slots | Nobody has measured what a "normal" or "large" value is, so the board gives no high/low words. |
| **pending measurement** | γ CEILING / FLOOR toggle | This level has no column in the database; it is not drawn. |
| **carry unmeasurable** / **unmeasurable r** / **r unmeasurable** | Flip, ∂ tiles, S\* | These tiles need a carry rate taken from futures prices. Futures start at 09:30 (strip: *"futures from 09:30"*), so before then the rate cannot be measured and the tile does not guess. Status code `UNMEASURABLE_R`. |
| **no flip in grid** | Flip | Repriced γ never crosses zero in the tested range. Status `NO_CROSSING`. |
| **skipped on expiry day** / `SKIPPED_EXPIRY` / **no flow on expiry day** | Flip, ∂ tiles, S\*, IV skew | On dte 0 the board deliberately does not compute these. |
| **no flow before 09:15** | Flows tiles | Flow is measured only once the session is open (`flow_window = SESSION`). Before that, this is the correct reading, not a fault. |
| **flow · loading** | Flows tiles | The data is still loading. |
| **flow · different run — not drawn** | Flows tiles | The flow rows and the book come from different runs, so the board will not draw bricks across them. |
| **PRE_OPEN** | badge code | Flow-vs-book before 09:15; the chip draws nothing. |
| **ABSTAIN** + reason | Net DEX chip | The chip declines to say SAME or OPPOSITE. Reasons: **UNTRADED**, *"no badge · untraded OI on this snapshot"*, more than 2 % of the DEX book sits on legs that have not traded; **ZERO_NET**, *"no badge · a net is zero"*; **DELTA_SET**, *"no badge · sign depends on the delta used"*, the vendor's delta and a parity-corrected delta give opposite signs. |
| **gap … qty** / **has no published delta** / **has no priced greek** | DEX and ∂Δ captions | OI (or ΔOI) on legs with no usable greek. It is left out of the total, never counted as zero. |
| **has no pre-open OI and sits outside the split** | DEX caption | OI on strikes that did not exist at the pre-open. |
| **n/c** | ΔOI | The strike exists at only one of the two times, so it is not comparable. |
| **no 09:15 anchor yet** | OI tab, before 09:15 | The ΔOI baseline does not exist yet. |
| **ΔOI · n/a (SENSEX · TD-S84-NEW-4)** | OI tab, SENSEX | Withheld permanently, because SENSEX's 09:15 baseline can come from a stale vendor row. A standing deviation (S92-H). |
| **settled hh:mm** | DEX sub-line | The DEX book is taken from the last run at or before 15:15. |
| **live · unreconciled** | Pin state | The row can still be revised; rows are reconciled after the close. |
| **stage 1 · no band (D-6)** | Conviction | A number only. The planned second stage needs about six weeks of history. |
| **number only · no band (E-D4)** | Legacy pin-risk score | Its old "weak/moderate/strong" words were never measured and were removed. |
| **DECLINED-ON-EVIDENCE** | drawers (D-4, D-5a) | Considered, tested, and deliberately not built. |
| **not built** | Flows badge (D-4) | The classification of ΔOI into writing, covering and so on does not exist and will not be shown. |
| **no pre-open print** / **prev close missing** / **futures from 09:30** | strip | The input does not exist yet at this time of day. "prev close missing" also appears for a few seconds while loading (finding F-8). |
| **partial** | 3D, river (○) | The session is not finished. |
| **OVERALL CRITICAL** / **outside trading hours — staleness expected** | Health | See Part 3b. Health is not yet calendar-aware (MV-4). |

---

## Part 6 — Glossary

| Term | Meaning |
|---|---|
| **ATM** | at the money; the strike nearest spot on the board's grid. The IV tab uses the chain-clock spot, so its ATM can differ from the strip's spot. |
| **Book** | the standing OI-weighted total, e.g. the DEX book. |
| **Corridor** | the range from the put OI wall to the call OI wall within an eligible σ band. States: inside, above call wall, below put wall, undefined. |
| **Cr / L Cr** | ₹ crore; "L Cr" = lakh crore (1L Cr = 1,00,000 Cr). |
| **DEX** | delta exposure: delta × OI × spot ÷ 10⁷, in ₹ Cr. Calls carry +, puts −. |
| **DTE / sessions** | days, or trading sessions, to expiry. |
| **Flip** | the spot level at which repriced net γ would change sign (the "L3 repriced flip"). |
| **Flow** | the change in a book since the pre-open, from ΔOI only. |
| **Flow-vs-book** | whether flow and book have the same sign; see the Net DEX chip. |
| **γ-conc / Pin** | the strike holding the largest share of gross \|γ\|. |
| **Gross \|γ\|** | the sum of absolute γ exposure across strikes. |
| **HHI** | the Herfindahl concentration index, Σ share². Only the Pin tab's "Concentration (HHI)" is a true HHI. The Gamma tab's "Top-strike share" is not, and is never called HHI. |
| **Max pain** | the strike at which option holders' total payout would be lowest. A positional figure, not a forecast. |
| **Net-long γ strike** | the strike with the largest positive net γ; not "near spot". |
| **OI wall** | the eligible strike with the largest call (or put) OI. |
| **Pin band** | the τ-weighted pin zone (ENH-81); a different measure from the pin point. |
| **Pre-open anchor** | the session's first front-expiry snapshot before 09:15 IST. |
| **Priced move** | the ATM straddle, as ± points and % to expiry. |
| **S\*** | the spot level at which the open options, repriced at their own IVs, would carry zero net delta. |
| **Settled run** | the last run at or before 15:15 IST. |
| **Untraded leg** | a strike-side with volume 0 so far and OI > 0. |
| **W1 / W2** | the front and back expiry legs. |

---

## Part 7 — Changelog and findings

### 7.1 Changelog

| Date | Board | Manual | Change |
|---|---|---|---|
| 2026-10-12 | `804d684` (bundle `index-CadQe4qO.js`) | v0.1 | Coverage register (140 rows) and pass 1 (pre-open). Parts 0, 1, 4, 5, 6 and 7 drafted. |
| 2026-10-12 | same | v0.2 | Pass 2 (09:40–09:41). Parts 2, 3 and 3b written. F-16 added; F-3 and F-13 refined. Owed: worked examples for ∂Δ/∂σ, ∂Δ/∂t, ∂Γ and S\* once carry is measurable; pass 3 after the close; an expiry-day read (NIFTY 13 Oct is dte 0). |
| 2026-10-12 | same | v0.3 | Capture pass (09:52–10:21): 23 real screenshots; worked examples for Flip, ∂Δ, ∂Γ and S\*; F-17 to F-20 added; F-16 partly resolved; S97-A wording transition noted. |
| 2026-10-12 | same | v0.3.1 | §1.7: `?` removed (no handler on live or staging); key verification noted. Help pack: section titles rendered without Markdown marks; route moves to `/manual`. |

### 7.2 Findings where the board and the docs disagree

**For the operator. The board has not been changed.**

| # | Finding | Evidence |
|---|---|---|
| F-1 | The strip/Overview **Net Γ** drawer (`net`) states *"dealers are net long gamma and hedge against moves"* as fact. The S94-F P2 sentence appears only in the Gamma-tab Net Γ drawer (`g_net`). | bundle registry; S94-F |
| F-2 | **Upper-case Γ** is still live as literal text: "NET Γ", "Gross \|Γ\|", "∂Γ/∂t", "∂Γ/∂σ". The S92 consequence records γ as restored. | bundle; strip text |
| F-3 | Pin tab **"LEADER TODAY"** shows the 2026-10-09 session under the header "previous session". The 10-09 rows still read **"unreconciled"** on 10-12, while the `p_state` drawer says rows are reconciled at end of day. | Pin tab, 09:0x, both symbols |
| F-4 | **Three different spot-change figures** for NIFTY at about 09:11: strip −10.7 (prev 22,520, γ 09:00); Home +103.5 / +0.46 % (γ 09:05); Context and Structure **+392.1 / +1.76 %**. Context and Structure still run the legacy strip: LIVE pill, PIN SCORE, full-digit NET Γ, MAX Γ. | pass 1 |
| F-5 | **Two skews disagree**: the IV tab shows *"skew 98 +4.31 vol pts … skew from view · not recomputed"*; Context shows *"IV SKEW −29.9 % CE"*, a client-side recompute. | pass 1, NIFTY |
| F-6 | **Context** is "Breadth & Volatility", not the PBD A.7 page (no Ambient, Expiry memory or Signals). | pass 1 |
| F-7 | **Dealer and writing wording** beyond what P2 and the drawers allow: Home card 4 *"What is actually written?"*; Home card 5 and the Flows read sentence *"dealers would buy about ₹…"*; the `f_hedge` drawer *"What dealers must trade"*; the L7/L8 captions (TD-S96-NEW-1). | pass 1; bundle |
| F-8 | **Loading states read as data states** for a few seconds after a symbol switch: PIN *"no run"*, OPEN · GAP *"prev close missing"*. Same class as the DEX loading fix in `c81b700`. | pass 1, NIFTY |
| F-9 | The **IV tab has no drawers** (0 of 39 keys). Its *"BACKWARDATION"* label is a regime word; PBD B.7 rules regime words out. | bundle; IV tab |
| F-10 | **"◆VIX 0.00"** in the strip is not defined anywhere. | strip, both symbols |
| F-11 | **`/board/overview` returns 404**; PBD documents `/board/:tab`. | pass 1 |
| F-12 | **Structure** shows a BUY_PE stream graded "D" from 08:30 to 09:00, before the open. The grade's meaning is not established (S90). | pass 1 |
| F-13 | The **pin point sits outside the pin band**: NIFTY pin 22,400, band 22,600–22,900. The SENSEX band is a single strike (74,000), while the pin is 72,000. These are two definitions, not an error, but undocumented on the board. | pass 1 |
| F-14 | The **Settings capital units** are unclear: `capital.default_inr 25000`, `max_position_inr 50000`, against CLAUDE.md rule 8 (₹25L / ₹50L). The manual does not interpret them. | Settings |
| F-15 | The **build stamp** is the served bundle hash; its mapping to `804d684` is not confirmed from the board. | — |
| F-16 | **Carry stayed unmeasurable after futures went live.** At NIFTY 09:41 and SENSEX 09:40, Flip read "carry unmeasurable", every ∂ tile read "unmeasurable r" and S\* read "r unmeasurable", yet FUT · BASIS already showed a price (NIFTY 22,570). The ∂Δ tiles read *"flow · different run — not drawn"*. The live-read pack expects L4 (`v_delta_drift_flow_vs_book`) to show values in market hours. I have not diagnosed this. It matters to the main session's P7 read. | pass 2 |

| F-17 | **Settings shows edit (pencil) icons** on every parameter row, while S90-E rules Settings read-only. I did not click them, so I don't know whether they open a write path. | Settings 10:20 |
| F-18 | **Stale strip on a freshly loaded page.** At 10:05 SENSEX Home, after a reload, read *"chain data 14 min old · gamma run 19 min old · Health ›"*. At 10:20, Health showed the chain and γ writers succeeding within the last minute. Earlier (09:52) the strip also appeared on a tab left open for ten minutes. Two possibilities: the page does not refetch in a background tab, and/or the writers lagged around 10:00. Not diagnosed; this is for the main session. | Home 10:05; Health 10:20 |
| F-19 | IV tab **"BACKWARDATION"** is drawn in the **warm (orange) sign colour**. It is not a sign, so this breaks the rule that colour carries sign and nothing else (PBD C.2). Adds to F-9. | IV 10:20 |
| F-20 | **SENSEX "no run"** in the PIN strip cell, Max pain and Distance to max pain at 09:55, while NIFTY's same cells had values. The page then stopped responding for about a minute. It may be a loading state (F-8) or a genuine missing run; I could not tell. | SENSEX OI 09:55 |

**Refinements from pass 2.**
- **F-16 resolved in part.** Flip, the ∂ tiles and S\* all had values by 09:52 (NIFTY, chain 09:50). They had read "unmeasurable" at 09:40–09:41. What remains is a gap of roughly 20–35 minutes after the open with no carry. Whether that is expected (the session-median futures carry needs some futures prints) is a question for the main session.
- **F-3** applies **before the first cycle only.** At 09:41 the header read "pin state · this session".
- **F-13**: at 09:41 the NIFTY pin (22,700) sat **inside** its band (22,600–22,800). The pre-open mismatch came from the previous session's data.
