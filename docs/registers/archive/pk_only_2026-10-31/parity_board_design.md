# parity_board_design.md — the Marketview board, designed as a whole

**Sessions 84–85 · first drafted 2026-09-28 · revised 2026-09-29 · design only — no code, no SQL, nothing in production**
**Status:** §0, §B unchanged in substance from the S84 draft. **§A and §C rewritten to match the prototype canvas "Marketview Board"** (accepted in direction by the operator, 2026-09-29 06:42 IST). **§D–G new.** **A–G APPROVED by the operator 2026-10-01 13:04 IST, with four additions (R1–R4 below), folded in at A.3a, A.3b, B.1a, C.8 and E-16..E-20.** §H (phased Lovable prompts) follows once the E-16..E-19 column measurement has run.
**Scope (operator, 2026-09-28):** the whole Marketview, not only Positioning. `/home` becomes the strip, one factual sentence and an entry to the question tabs; the Positioning tabs follow the brief; the other pages are folded in or retired.
**Inputs:** the brief (`parity_board_design_prompt.md`), `claude/parity_target_render_study.md`, `parity_render_contract.md` (the data contract, incl. Appendix A `queries.ts` and Appendix B `state.ts` / `sections.tsx`), ADR-017, ENH-110, ADR-025 (incl. Amendments A and B), the S84 post-close addendum, the prototype canvas, and a read-only capture of the live site (§0).

**Is the B1 trigger met?** ADR-025 Amendment B1 defers presentation until every one of the fourteen layers carries a disposition. They now all do: L1, L2 BUILT; L3–L6, L9, L10, L12–L14 PENDING; L7, L8 PENDING (B4); L11 PENDING (B4). D1 counts PENDING as a disposition and the BLOCKED-ON-DECISION class has been empty since S81. **Correction, S88:** earlier drafts of this paragraph read "L11 DECLINED". No ADR amendment records that; ADR-025 B4 reads PENDING. Whether L11 is declined (the parity target's terminal sample does not carry it — study C, L11) is an **operator ruling owed**, not a fact this document can assert. The trigger is met either way. So the design pass can run. Clause 3 stays suspended until the build ships.

### Operator rulings on the design (2026-09-29 06:42 IST — source: `claude/s84_post_close_addendum.md` §2.2)

1. The direction of A–C is **accepted**.
2. **ICT is low priority.** It gets its own page (**Structure**), **not on Home**.
3. The current dashboard is "anodyne and not intuitive". The redesign must **render the data intuitively**, not re-lay it out.
4. **Every multi-strike view needs zoom**, and the **default view must be sensible** (never strike 21,000 when spot is 26k).
5. **The build is in Lovable.** The handover is a prompt.
6. Design at the level of a top UI architect and visual designer.

### Operator additions at approval (2026-10-01 13:04 IST)

- **R1 — Change marks.** Wherever a level such as spot or VIX is shown, it carries a small up/down arrow and its change. Applied meaningfully to other values as well (C.8).
- **R2 — Futures with basis.** Show the front-month future, its basis to spot, and the change in basis against the previous session (A.3a, B.1a).
- **R3 — Pre-market open.** Show the pre-open print (A.3b, B.1a).
- **R4 — Gap up / gap down.** Show the opening gap against the previous close, pre-open and final (A.3b, B.1a).

### What changed in this revision

| section | change |
|---|---|
| A.1 | Four market pages, not three: **Structure** added for ICT (ruling 2). |
| A.2 | **Top bar**, not a left rail. |
| A.3 | Strip cells carry **micro-visuals**; S7 subtitle is now the priced move; strip cells are selectable. |
| A.4 | Home: large spot, **the read**, six question cards each with a small picture. |
| A.5 | **One ladder for every tab**; zoom controls, edge chips, chain minimap, two gutters (priced move, pin band). |
| A.6 | Per-tab drawing updated to the prototype: gamma terrain, max-pain valley, smile on the ladder. |
| A.7 / A.8 | Context keeps the daily clock; **Structure** holds ICT. |
| B | New rows only: strip micro-visuals, the read, gutters, terrain, valley, minimap, Structure. Existing bindings unchanged. |
| C | Rewritten: dark **instrument** theme, **temperature hues** for sign, neutral greys for side, pale gold for selection only, IBM Plex. |
| D–G | New. |

---

## 0. What the live site shows today (captured 2026-09-28, 11:15–11:25 IST)

Read-only. Built-in browser at 1440 × 900 and at 375 × 812 (phone emulation). Every page opened; no form submitted, no parameter touched. Symbol toggled with the `S` key to read SENSEX.

### 0.1 Page inventory

| route | nav label | what it shows | reads (from contract §2.2) |
|---|---|---|---|
| `/home` | Home | Title "Home — Ambient Trajectory". Snapshot strip (7 cells). A regime line "TREND_DOWN · ALIGNED · as-of 25 Sept → for 28 Sept". A three-clock chart (price, cycle OI asymmetry, 20-day γ persistence) with MONTH/CYCLE/WEEK switch. A collapsed "Drill-down" (lenses, expiry memory, parameters, intraday Γ) that did not open on click. | `market_environment_snapshots` (`useAmbient`, `useAmbientSeries`), `gamma_metrics`, `market_spot_session_markers` |
| `/positioning` | Positioning | Strip; Key Parameters (Regime, Net Dealer γ, Spot Context, Flip Level, Max γ Strike, Pin Zone, Accel Zone); GEX-by-strike histogram (strike on x); net dealer γ intraday; Pin Risk score, Pin Probability, ATM straddle; Pin Risk timeline. | `gamma_metrics`, `gex_strike_snapshots`, `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone` |
| `/max-pain` | Max Pain & OI | Strip; max pain by strike (±20 strikes), a "PIN BIAS: CONVERGENT" word and one generated sentence. | `v_max_pain_by_strike` |
| `/breadth` | Breadth & Vol | Strip; WCB score 26.9 "BEARISH", advances and DMA breadth, coverage 23.9 %; A/D 189 / 1,110; India VIX; IV skew "−36.1 % CE" (ATM CE 20.3 / PE 13.0). | `weighted_constituent_breadth_snapshots`, `market_breadth_intraday`, `option_chain_snapshots` (`useIvSmile`) |
| `/structure` | Structure & ICT | Strip; 10 ICT zones "nearest to spot"; today's signal stream (15 rows, every one `BUY_PE`, 10:05–11:15). | `ict_zones`, `signal_snapshots` |
| `/expiry-memory` | Expiry Memory | Base rates for the current (ambient × alignment) pair; 20 recent expiries. | `v_expiry_base_rates`, `expiry_outcomes` |
| `/health` | Health (Ops) | Overall CRITICAL; writer fleet 10/16, 6 stale; token 502 three days ago; per-script freshness; 24 h error buckets. | Health views (outside the contract) |
| `/order` | Order | Stub: "Deferred to ADR-019 + ENH-112". | none |
| `/journal` | Journal | Stub: "Deferred to ADR-020 + ENH-113". | none |
| `/settings` | Calibration (nav) / Settings (title) | ENH-83 parameter console; tabs Calibration · Capital & sizing · Display · Connections · Manual actions · About. | `merdian_parameters`, `v_merdian_parameter_audit` |

### 0.2 Defects seen on the live site

These are **repairs to shipped surfaces**. ADR-025 B2 says the B1 deferral does not block them. They are listed here because the new design must not carry them forward; filing them is a doc-close item (addendum §4).

| # | where | what the page shows | why it is wrong | source |
|---|---|---|---|---|
| L-1 | Strip, every page | NIFTY `MAX PAIN 22,950 −0.6 %` with spot 22,821.5; SENSEX `MAX PAIN 68,700 +6.1 %` with spot 72,867. | **Sign is inverted.** Both max pains sit on the other side of spot from what the sign says. `MAX γ` on the same strip is signed correctly. `state.ts` computes `(spot − maxPain) / maxPain`; every other distance is `(level − spot) / spot`. | Appendix B.1, `painSpotDistPct` |
| L-2 | Positioning · Spot Context; hero subtitle; "Σ to expiry" | `±2.09 %`, `σ 22,344–23,299`, while Flip Level reads `23,299.21 · +2.09 % from spot`. SENSEX: `±6.66 %` and flip `−6.66 %`. | **Flip distance is printed as a volatility σ** — the upper "σ" bound is the flip level itself. Already filed as TD-S84-NEW-7; confirmed live on both symbols. | contract Part 3 §1 |
| L-3 | Home · trajectory | "NIFTY · settled through 04 Aug", x-axis 22 Jul – 04 Aug, while the regime line is as-of 25 Sept. | `useAmbientSeries` orders `as_of_date` **ascending** with `limit 40`, so it returns the **oldest** 40 sessions, not the latest. The chart is eight weeks stale by construction. | Appendix A, `useAmbientSeries` |
| L-4 | Positioning · Net Dealer γ | `Σdmp 63,10,275.29k · Σamp −53,08,578.61`. | Unit suffix `k` on a Crore figure, and no unit on the second. The same figures read `Cr` two cards below. | Appendix B.2, `KeyParametersSection` |
| L-5 | Positioning · Regime | `POSITIVE_γ · long dealer γ · mean-reverting · LOW_GAMMA` beside net Γ of +10 lakh Cr. | The words describe a behaviour (mean-reverting) nobody has measured, and `LOW_GAMMA` sits beside the largest positive figure on the page. Two states from two sources, no band behind either. | brief ruling 6 |
| L-6 | Positioning · Pin Probability | `73.0 % · complement of expansion (27.0 %)`. | A "probability" label on a pin that S74 measured as **not predictive** (19 of 21 sessions negative). Contract §3 says any label implying attraction contradicts the measurement. | contract §3 |
| L-7 | Pin Risk score | `38/100 · weak pin`, same 38 on both symbols. | The 25 / 50 / 75 words are unmeasured thresholds (ruling 6). The identical 38 on NIFTY and SENSEX should be checked before it is trusted. | Appendix B.3 |
| L-8 | Breadth · IV skew | `−36.1 % CE · ATM 22,800 · CE 20.3 / PE 13.0`. | Client-side skew from one ATM CE and one ATM PE quote; the server already publishes `v_iv_surface.leg_skew_98`. A CE IV 56 % above the PE IV at the same strike is more likely a quote problem than a skew (compare the stale-`ltp` finding, contract §9). | contract Part 2 §2.5 |
| L-9 | Structure · ICT zones | All 10 "nearest" zones sit **above** spot; three are dated 2026-06-02. | The list is the latest 40 by `detected_at_ts`, sorted by midpoint distance, with no validity filter (`ict.zone.h_valid_days` = 7 is not applied) and no below-spot side. | Appendix A, `useIctZones`; Settings capture |
| L-10 | Structure · signals | 15 rows of `BUY_PE` at 22,800–22,850, one every 5 min. | Redundant content (ADR-017 P1). A run of identical signals is one fact. | ADR-017 P1 |
| L-11 | Expiry Memory | `OUTCOME` and `MOVE %` are `—` on all 20 rows; base rates rest on N = 1 and N = 4. | The outcome columns never fill. The base-rate table prints percentages from one or four cases. | live capture |
| L-12 | Order, Journal | Stub pages in the nav. Journal cites **ADR-020**, which in the register is "calendar absence is not a verdict". | Empty-state pages (ADR-017 P3) and a wrong ADR reference. | Decision Index |
| L-13 | Nav | Nav says "Calibration"; the page title says "Settings". | Two names for one page. | live capture |
| L-14 | Phone (375 px) | The 220 px left nav never collapses. Content gets ~130 px; values wrap mid-number (`+10,01,696.67 / Cr`); the "Narrative →" button is cut off; the page scrolls sideways. | The shell has no phone layout. | screenshots |
| L-15 | Net Γ magnitude | NIFTY `+10,01,696.67 Cr` (≈ 10 lakh crore); SENSEX `+44,98,578.03 Cr`. | These are `gex_cr` sums in the S27 `/1e7` convention. **What one unit means** (₹ of hedge per 1 % move? per point?) is not stated anywhere the board can cite. The format in C.7 will print "10.0L Cr", which invites a reader to take it as rupees. Gap **E-1**. | contract §1 (units) |

### 0.3 Health page, seen in passing (not a design item)

- `detect_ict_patterns_runner.py` last succeeded **Fri 15:52 IST** — three days, on a 5-minute cadence, during market hours today. This is a live stall, not a weekend artifact. **Re-check owed at S85** (addendum §2.5).
- `merdian_pipeline_alert_daemon` last success **109 days** ago; `local_token_refresh` last status **502**, three days ago.
- Four daily jobs (`compile_market_environment_local.py`, `accrue_expiry_outcomes.py`, `local_token_refresh`, and the ICT one above) read "3d" because the page ages them in calendar days across the weekend. That makes OVERALL read CRITICAL on an ordinary Monday — the ADR-020 "calendar absence is not a verdict" shape on the Health page itself. Candidate TD.

---

## A. Board map

### A.1 Information architecture — before and after

The current site has **seven market pages**, and most readings live on the page named for the table they come from. The new site has **four market pages**, organised by the clock a reading moves on — plus Structure, which is its own subject (ruling 2).

| today | after | why |
|---|---|---|
| Home (ambient trajectory) | **Home** = strip + the read + six question cards + context line | The first screen answers "what kind of day", not "what did the daily job say" |
| Positioning | **Board** (`/board/:tab`) = strip + the read + six question tabs | Everything that moves intraday with the option book |
| Max Pain & OI | folded into **Board · OI** | Max pain sits on the OI tab, compared with the pin |
| Breadth & Vol | breadth → **Context**; VIX → strip; IV skew → **Board · IV** | Skew is an option-book reading; breadth is a slow clock |
| Structure & ICT | ICT zones → **Structure** (own page, off Home, off the Board); signals → **Context**, run-collapsed, conditional (decision **E-D6**) | Ruling 2. Price structure is MERDIAN-only (study D2.8) and low priority |
| Expiry Memory | → **Context** | Daily/weekly clock |
| Health, Settings | unchanged routes; label "Settings" everywhere (fixes L-13) | ADR-017 P2 role contract |
| Order, Journal | **removed from nav** until their ENHs ship | Stub pages are empty states (P3). Routes may stay |

Four places, three clocks:

- **Board** — the option book, every 5-minute cycle. Two sub-clocks: the GEX run and the chain snapshot (contract §0).
- **Context** — daily and weekly: ambient regime, expiry memory, breadth, signals.
- **Structure** — ICT zones, on the same ladder component as the Board, with its own clock (zone detection).
- **Home** — no clock of its own. The strip, one sentence, and one card per question, each a link into the Board.

### A.2 App shell — a top bar

| width | shell |
|---|---|
| ≥ 1024 px | **56 px top bar**: `MERDIAN` wordmark · nav `Home · Board · Context · Structure` · a divider · `Health · Settings` (in a quieter grey) · spacer · symbol toggle `NIFTY | SENSEX`. The selected nav item sits on a filled chip. The strip is the first row of the content, not part of the bar. |
| 768–1023 px | Same bar. The strip wraps to two rows. |
| < 768 px | **52 px top bar**: `MERDIAN` · symbol toggle · a 44 × 44 menu button. The menu opens a sheet with the six destinations. Nothing may cause sideways scroll (fixes L-14). |

**Why a top bar and not a rail.** The ladder is tall and narrow by nature; it wants every horizontal pixel for bars and labels, and every vertical pixel for strikes. A top bar spends 56 px of height once. A rail spends 64–220 px of width on every row of the ladder. The operator also has only six destinations; a rail's advantage (many destinations, icons) does not apply.

The shell carries **no status text** in the healthy state. The only shell-level signal is the stale strip (P3), full width, directly under the bar.

### A.3 The summary strip — on every Board tab and on Home

Seven cells, one row at 1440 px, a 2 × 4 grid on a phone (the eighth slot holds the clock chip when shown). Each cell is a small grey label, a large value in the condensed face, a one-line grey subtitle, and — new in this revision — **a micro-visual** that shows the reading's shape before its number is read. Every cell is a button: it selects that value (D.1). Bindings are in B.1.

| # | label | value | subtitle | micro-visual | question it answers |
|---|---|---|---|---|---|
| S1 | NIFTY · EXPIRY | `29 SEP` | `1 session left · weekly` | none | Which contract am I reading? |
| S2 | SPOT | `22,821.5` | `−241.6 · −1.05 %` | **intraday sparkline** of spot (≥ 3 distinct runs) | Where is price, and how did it get here? |
| S3 | NET Γ | `+10.0L Cr` (hue by sign) | `long γ · net/gross 0.18` | **split bar**: amplifying (warm) left, dampening (cool) right, a centre tick | Which way do dealers lean, and how one-sided is it? |
| S4 | FLIP | `23,299` | `+2.09 % · σ —` (or a named state) | **distance marker**: a ±3 % track, spot dot at centre, a dashed tick at the flip | How much room before hedging changes sign? |
| S5 | CORRIDOR | `22,500 – 23,000` | `inside · width 2.2 %` | **track**: the corridor as a span, put and call ticks at its ends, spot dot | Where are the written edges, and where is price inside them? |
| S6 | PIN (γ-CONC) | `23,000` | `14.4 % of book · lead 2.9 pts` | **two bars**: #1 full width, #2 as a fraction of #1 | Where is the centre, and how decisive is it? |
| S7 | IV · VIX | `9.84 · 13.96` | `priced move ±189 · ±0.83 %` | none | What is the market charging for time, in points? |
| S8 | FUT · BASIS | `22,874 · +52.5` | `basis ▲ +6.1 vs prev · 23 OCT` | none | Where is the future, and is the premium widening or narrowing? (R2) |
| S9 | OPEN · GAP | `▼ −0.42 %` | `pre-open 22,980 · final 22,966 · prev 23,063` | none | Did the day open away from yesterday's close, and by how much? (R3, R4) |
| S10 | (conditional) | clock chip | `γ 11:20 · chain 11:40` | — | Shown only when the two clocks differ by more than one cycle (C.6) |

Below the strip, on Home and on the Board, sits **the read** — one factual sentence composed from the values (D.4). Example (illustrative): *"Spot 22,821 sits in an amplifying pocket, 0.8 % under the call OI wall at 23,000, which is also the largest gamma strike. Flip is +2.09 % away, outside the ±189 the straddle is pricing by expiry. Net gamma is small against gross (0.18)."*

**Count and layout.** Nine standing cells plus the conditional clock chip. At 1440 px the strip is one row of ~150 px cells in the condensed face; at 1024–1439 it wraps to two rows (5 + 4); on a phone it is a 2 × 5 grid. **S2 and S7 now carry change marks (R1, C.8).**

### A.3a Futures and basis (R2)

- **Value:** the front-month index future's last price, then its **basis** = future − spot, in index points, signed.
- **Subtitle:** the basis change against the **previous session's last basis**, with a change mark (C.8), and the contract's expiry (`23 OCT`).
- **Why basis rather than the future alone:** the future moves with spot; the information is in the premium. A widening premium on a rising spot reads differently from a narrowing one, and that is what the change mark shows at a glance.
- **Absence:** futures capture runs from **09:30 IST** (cron hours 04–09 UTC, s81 notes TD (b)). Before the first row of the day the cell shows the named state **"futures from 09:30"**, never yesterday's value. A gap in capture mid-session past the recency floor shows **"futures stale"**.
- **Basis context label** (`LONG_BUILD` / `SHORT_BUILD` …, ENH-07 B) is **not shown**: its deadbands are env constants, not a measured band (ADR-016), and it is display-only in the signal row today. Gap E-18.

### A.3b Pre-market open and gap (R3, R4)

- **Value:** the **gap** = (open − previous close) / previous close × 100, with an up or down mark. Before 09:15 the open is the **pre-open print (09:08)**; from 09:15 it is the **final open**. The value never mixes the two: the subtitle names which one it is.
- **Subtitle:** `pre-open 22,980 · final 22,966 · prev 23,063`. Before 09:15 the final slot reads `final at 09:15`.
- **After the open** the cell stays for the whole session — the gap is the day's frame (gap-and-go vs gap-and-fill, ENH-96's stated reason) — and gains one more fact once spot has moved: **`gap filled`** when spot has traded back through the previous close, as a word, no colour.
- **Absence:** no pre-open row for the day → **"no pre-open print"**; no previous close → the gap is not computed and the cell reads **"prev close missing"**. **Never** compute a gap against a stale previous close — the TD-S60-NEW-1 failure (a 21-day-stale baseline printed +4.34 % on a +0.76 % day) is the reason this cell must check that the previous close belongs to the previous trading session.
- **Home:** the masthead change line gains the gap as a second fact: `−241.6 · −1.05 % · opened ▼ 0.42 %`.

The strip replaces today's seven-cell strip. What it drops and why:

- **MAX γ** → becomes **NET-LONG γ STRIKE** on the Gamma tab only. It is not the pin, and ADR-024 Amendment A forbids reading it as "near spot" (contract §2.5).
- **MAX PAIN** → OI tab. Not a strip value; its sign was wrong (L-1).
- **PIN SCORE** → Pin tab, as a legacy number with no band words (L-7; decision **E-D4**).
- **VIX** stays, merged into S7 (ADR-017 P1: one VIX, once).

### A.4 Home

Home answers "what kind of day" in one screen, then offers six doors.

1. **Masthead** — `NIFTY · 29 SEP · 1 SESSION LEFT` in small tracked grey; spot at 56 px in the condensed face; the day's change beside it in the sign hue.
2. **The read** — the same sentence as the Board, at 17 px, to the right of spot.
3. **Six question cards**, a 2 × 3 grid. Each card: a large muted number (1–6, also the keyboard key), the tab name, the tab's question, a one-line answer in words and numbers, and **a 220 × 56 px picture** of that answer. Clicking a card (or pressing its number) opens that tab with its first value selected.
4. **Context line** — `CONTEXT · DAILY · Trend down · aligned · as of 25 Sep · WCB 26.9 bearish · 189 up / 1,110 down ›`, linking to Context.

Structure (ICT) is **not** on Home (ruling 2).

| card | question | one-line answer (illustrative) | picture |
|---|---|---|---|
| 1 Overview | What kind of day, and where are the edges? | Spot is inside the written corridor 22,500–23,000. Flip is +2.09 % away. | ±2.5 % track: corridor span, put and call ticks, dashed flip tick, glowing spot dot |
| 2 Pin | How settled is the centre? | 23,000 holds 14.4 % of all gamma, 2.9 pts ahead of 23,100. | #1 bar full width, #2 bar as a fraction of it, both labelled |
| 3 Gamma | Can I trust single strikes? | Net is 18 % of gross — the two sides almost cancel. Top strike holds 14.4 % of the book. | the S3 split bar, larger, with both sums labelled |
| 4 OI | What is actually written? | Max pain 22,950 sits 1 strike below the gamma pin. | ±2.5 % track with corridor, max-pain tick and pin tick |
| 5 Flows | What must dealers trade if spot moves? | About ₹13,782 Cr per 1 % — buying falls and selling rises. | the hedge line through zero, with the −1 % and +1 % points marked BUY / SELL |
| 6 IV | What do time and cover cost? | Front 9.84, second weekly 10.34. The straddle prices ±189 by expiry. | two points, front and back, joined; no curve |

Phone: the masthead and the read stack; the cards become one column, each with its answer line and no picture.

### A.5 Board — the tab template

Every tab has the same anatomy. **The strike ladder is one component, shared by every tab except Flows. Its strikes, window and zoom do not move when the tab changes — only the data layer drawn on it does.** The operator keeps their place on the price axis while changing the question.

1. **Strip** (A.3) and **the read** (D.4).
2. **Tab row** — `Overview · Pin · Gamma · OI · Flows · IV`, keyed 1–6. The selected tab is a filled chip with a 2 px pale-gold top rule.
3. **Tab card**, two columns at 1440 px:
   - **Value list** (≈ 300 px): the tab's question as a one-line header, then 2–7 rows. Each row: label, one-line subtitle, value right-aligned. The list is the control (D.1).
   - **Ladder panel** (the rest of the width):
     - **Header row:** chart title in small tracked caps (e.g. `SIGNED DEALER GAMMA BY STRIKE`), then zoom controls — `Near spot · All levels · Full chain` and `− / +` (D.2).
     - **Edge chips above** — levels above the window (D.2).
     - **Ladder rows**, top = highest strike. Each row is a five-column grid: **strike label (60 px) · left gutter (10 px) · chart cell · right gutter (10 px) · readout (64 px)**.
       - *Left gutter* = **priced-move bracket**: filled on strikes within ± the ATM straddle of spot.
       - *Right gutter* = **pin band**: filled on strikes inside `pin_lower … pin_upper`.
       - *Chart cell* = the tab's data layer, over a hairline zero axis where the layer is signed.
       - *Readout* = the row's value in words-and-numbers form (e.g. `+14.4L`, `#1 · 14.4%`, `1.52 C`, `no quote`).
     - **Level rules** run across the chart cell. A level that lands on a strike is drawn inside that row, with a label pill at the right end; a level between strikes (spot, flip) gets its own zero-height row between the two strikes it falls between, with a value tag at the left axis.
     - **Edge chips below.**
     - **Chain minimap** — a 30 px column to the right of the ladder: the whole chain in miniature, 5 px per strike, a pale-gold box around the current window, a white tick at spot (D.2).
     - **Legend** — one line of swatches under the ladder, tab-specific.
     - **Axis note** — `← amplifying · dampening →`, or the tab's equivalent, and the readout column's header.
   - **Caption** — one sentence naming the selected element, under the chart. It changes with the selection.
4. **Detail panel** — full width below the card. Fixed slots: tab · title · unit · WHAT IT IS · HOW TO READ IT · COMPUTED · SCALE · CAVEAT · READ IT WITH (2–3 chips that select other values, possibly on other tabs). Where no band is measured, the SCALE slot says so and names the gap.

**Ladder geometry.** Row height = 560 px ÷ strikes in the window, clamped to **8–26 px**. Below 14 px the ladder is *dense*: strike labels thin to every fourth strike plus any strike carrying a level; readouts show only on level rows. Bar height = row height − 8, minimum 6 px. Bars scale to the **largest magnitude inside the visible window**, so zooming in re-scales rather than shrinking the picture.

**Desktop, 1440 px — template (illustrative)**

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ MERDIAN  Home [Board] Context Structure │ Health Settings                        [NIFTY|SENSEX] │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│ EXPIRY 29 SEP │ SPOT 22,821.5 ∿ │ NET Γ +10.0L ▮▮▮|▮▮ │ FLIP 23,299 ·──┆ │ CORRIDOR ▕━●━▏ │ PIN ▬▬/▬ │ IV·VIX │
│ Spot 22,821 sits in an amplifying pocket, 0.8 % under the call OI wall at 23,000 … (the read)    │
│ [Overview] Pin  Gamma  OI  Flows  IV                                                              │
│ ┌ What kind of day…  ┐ ┌ SIGNED DEALER GAMMA BY STRIKE     [Near spot] All levels Full chain − + ┐│
│ │▌Net Γ     +10.0L Cr│ │ ▲ FLIP 23,299 · +2.09 %                                             ┌─┐││
│ │  long γ · n/g 0.18 │ │ 23,100 │ │           ██████                    │▐│  +6.2L          │▪│││
│ │ Flip        23,299 │ │ 23,050 │ │        ████                         │▐│  +4.1L          │▪│││
│ │  +2.09 % · σ —     │ │ 23,000 │▐│ ─────────█████████████── γ-CONC ≡ CALL OI WALL │▐│ +14.4L│▪│││
│ │ Corridor      2.2 %│ │ 22,950 │▐│              ███                    │▐│  +2.0L          │▣│││
│ │ Pin (γ-conc) 23,000│ │ 22,900 │▐│  ░░ amplifying pocket tint ░░       │ │  −0.4L          │▣│││
│ │ Priced move   ±189 │ │ 22,821 ┼━━━━━━━━━━━━━━━━━━━ SPOT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│▣│││
│ │ Spot        22,821 │ │ 22,800 │▐│  █████████████│                     │ │  −9.6L          │▣│││
│ │ Time to expiry 1 s │ │ 22,700 │▐│     ██████████│                     │ │  −6.4L          │▣│││
│ └────────────────────┘ │ 22,650 │ │        ███████│                     │ │  −3.3L          │▪│││
│                        │ ▼ PUT OI WALL 22,500 · −1.41 %                                      └─┘││
│                        │ ■ dampening  ■ amplifying  ▐ priced move  ▐ pin band                    ││
│                        └──────────────────────────────────────────────────────────────────────────┘│
│ caption: Bars to the right cushion moves (dampening). Bars to the left push them along.         │
│ ┌ DETAIL · NET Γ ─ unit · what · how to read · computed · scale · caveat · read with [Flip][Gross]┐│
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Phone, 390 px — template**

```
┌─────────────────────────────────┐
│ MERDIAN     [NIFTY|SENSEX]   ☰  │
├────────────────┬────────────────┤
│ strip 2 × 4 (values, subtitles; │
│ micro-visuals omitted)          │
├─────────────────────────────────┤
│ the read (13.5 px)              │
├─────────────────────────────────┤
│ Overview Pin Gamma OI Flows IV› │ ← scrolls inside itself only
├─────────────────────────────────┤
│ SIGNED GAMMA  [Near spot][All]  │
│ ladder, 22 px rows, near-spot   │
│ window, both gutters, pills     │
│ ▲ flip 23,299 off-screen · tap  │
├─────────────────────────────────┤
│ value list (48 px rows)         │
├─────────────────────────────────┤
│ detail: title + how to read;    │
│ "More ›" opens the other slots  │
└─────────────────────────────────┘
```

On a phone the ladder comes **before** the value list: the picture is the answer, the list is the control, and the thumb reaches the list after seeing the picture. No pinch, no drag: zoom is the two mode buttons and the edge chips (D.7).

### A.6 The six tabs — what sits in each

The value list is given in order; the first row is selected when the tab opens. "Levels" are the rules drawn on the ladder for that tab. Bindings are in B.

**1 · Overview — "What kind of day, and where are the edges?"**
- List: Net Γ · Flip · Corridor · Pin (γ-conc) · Priced move · Spot · Time to expiry.
- Layer: **signed net γ per strike**, horizontal diverging bars — dampening (cool) right of the zero axis, amplifying (warm) left. **Gamma terrain**: every row's background is tinted by the sign of its own `gex_cr` at a fixed 7 % alpha (11 % inside the corridor), so the pocket spot sits in is visible without reading a number.
- Levels: spot, flip, call OI wall, put OI wall, γ-conc.
- Gutters: priced move (left), pin band (right).
- Reserved, off by default: **γ CEILING / γ FLOOR** (decision on gap **E-3**). A toggle in the header, disabled and labelled "pending measurement". When on: dotted 2-2 rules, labelled "γ CEILING" / "γ FLOOR", never "wall".

**2 · Pin — "How settled is the centre?"**
- List: Pin (γ-conc) · Runner-up · Lead · Share of book · Pin band · Pin distance · Legacy pin-risk score (number only; decision **E-D4**).
- Layer: **share of the |γ| book per strike**, bars from the left edge on one scale, hue by the strike's side (cool dampening / warm amplifying). The top 10 at full opacity with `#n · x.x%` in the readout; the rest at 25 %.
- Selecting Lead outlines bars #1 and #2 in pale gold and dims the others.
- Levels: spot, γ-conc.

**3 · Gamma — "Can I trust single strikes?"**
- List: Top-strike share · Gross |Γ| · Net Γ · Contributing strikes · Net-long γ strike · Net Γ today (sparkline).
- Layer: signed γ as on Overview, plus the **cumulative silhouette** — a white dot per row at the running total of `gex_cr` from the top strike down. Where the dots cross the zero axis the book changes sign. Same gamma terrain.
- Levels: spot, flip, net-long γ.
- **Gamma river** — below the tab card, a second, smaller chart: daily net Γ over the stored sessions (30 by default, "all" up to the stored depth), as the day's min–max band with the settled point on it, price on its own scale. The one tab with two charts; the river is history, not a second reading of today. **Not yet in the prototype.**

**4 · OI — "What is actually written?"**
- List: Call OI wall · Put OI wall · Corridor · Max pain · Pin vs max pain · OI since open.
- Layer: **OI butterfly** — call OI right (light grey), put OI left (mid grey), each bar's size at the readout (`1.52 C`). A 2 px **ΔOI-since-open tick** under each bar, cool = added, warm = removed. **Max-pain valley**: one small dot per row at that candidate strike's total payout, scaled across the window — the dots trace a valley and **max pain is its floor**.
- The two booleans (max pain in pin band? in corridor?) stay separate words in the Pin-vs-max-pain subtitle. They disagree in opposite directions on the two symbols (contract §14) and must not collapse into one "aligned" word.
- Levels: spot, call OI wall, put OI wall, γ-conc, max pain.
- **SENSEX: the ΔOI ticks and the OI-since-open row are absent** until the outlier guard exists (TD-S84-NEW-4).

**5 · Flows — "What must dealers trade if spot moves?"**
- List: Hedge per 1 % · Reaches flip? · Vanna and Charm **absent** until the views exist (no placeholder).
- Chart: **not the ladder.** One line: hedge flow (₹ Cr, signed) against spot move −2.5 % … +2.5 %, through zero, with the six stored scenarios as dots labelled `BUY 13,782` / `SELL 13,782`, and the flip as a dashed vertical at its % distance. The six scenarios are exactly linear (contract §16), so the honest form is a slope.
- Participant positioning (L18) does **not** appear (contract §17). Gap.

**6 · IV — "What do time and cover cost?"**
- List: Front ATM IV · Back ATM IV · Short-end slope · Parity gap · Skew₉₈ · ATM straddle.
- Layer: the **smile of the selected leg on the same ladder** — strike on the vertical axis, IV on the horizontal, one dot per strike joined to the left edge by a hairline. Dot tone by `side_used` (light grey = CE quote, mid grey = PE quote). `OTM_ABSENT` or `iv = 0` → the row reads `no quote` and has no dot, never zero.
- A leg switch above the chart: `Front · Back`.
- Levels: spot, k₉₈.
- No term-structure curve: two points are not a curve (contract §11).

### A.7 Context

One scrolling page. Each section collapses when it has nothing to say (P3).

1. **Ambient** — regime · alignment · session prior · note, from the latest snapshot; the three-clock trajectory below it, **latest 40 sessions** (fixes L-3).
2. **Expiry memory** — base rates for the current pair, each rate with its N beside it; **counts, not %, when N < 5** ("1 of 1 pinned"); recent expiries without the empty outcome columns until they fill (L-11).
3. **Breadth** — WCB score and regime, advances, DMA breadth, coverage; A/D.
4. **Signals** — conditional. Identical consecutive rows collapse into one (`BUY_PE 22,850 · ×15 · 10:05–11:15`) (fixes L-10). Whether this section stays at all is decision **E-D6** (ADR-019).

### A.8 Structure (ICT) — own page, low priority

- **Zone list** — zones within ±2 % of spot, **both sides**, **valid ones only** (`ict.zone.h_valid_days`), grouped `Above spot` / `Below spot`, nearest first (fixes L-9). Each row: timeframe · type · range · distance %.
- **Ladder** — the same ladder component, window and zoom as the Board, with zones drawn as spans on the chart cell (bearish warm outline, bullish cool outline, no fill heavier than 12 %), and spot, call OI wall, put OI wall as thin reference rules. This is where the ADR-017 P4 **confluence ring** belongs once its detection primitive exists (F, ADR-017 P4); until then no ring is drawn.
- Not linked from Home. Reached from the top bar.

---

## B. Per-tile table

Conventions for this section:

- **Bindings** are `view.column`, exactly as in the contract (Part 1 and Appendix A). A value marked **derived** is arithmetic on bound columns, done in the read layer; the formula is given. Nothing else is invented. Fields that do not exist are marked **GAP** and are listed in E.
- **Clock** is `γ` (latest `gex_strike_snapshots` run) or `chain` (latest `option_chain_snapshots` ts). A tile never mixes clocks without showing both times (contract §0).
- **Distance** is `(level − spot) / spot × 100`, in % of spot, signed, for every level on the board. σ is shown as `σ —` until the canonical σ exists (gap E-2).
- **Explanation slots** (unit · computed · how to read · read with · caveat) are drawn from the view COMMENT cited. Where the COMMENT did not run live (contract P2: `v_gex_abs_exposure`, `v_gex_max_pain`, `v_gex_pin_maxpain`), the text comes from the `sql/` file and the tile is flagged until the COMMENT is applied.
- **States** lists every value the column can emit, observed or not (contract §4 constraint 2). Named absence states render as a grey word in a dashed chip, in the value slot.

### B.1 Summary strip

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| S1 Symbol · Expiry | Which contract? | — | `gamma_metrics.expiry_date`; `v_iv_term_structure.dte_sessions` where `leg = 1` (chain). Class weekly/monthly: **GAP** (E-9) | text | — | expiry day: subtitle reads `expiry today` | select → Overview, Time to expiry | contract §1, §11 |
| S2 Spot | Where is price? | — | `gamma_metrics.spot` (γ); prior close `market_spot_session_markers.prev_close_spot` | value + signed change and % | prior close | no prior close → change omitted, not zero | select → Overview, Spot | — |
| S2 sparkline | How did it get here? | — | `gamma_metrics.ts`, `.spot` today (γ), deduped by `ts` (`useGammaToday`) | 100 × 12 px polyline, ink | — | < 3 distinct runs → no sparkline, no text | — | S81 ruling (≥ 3 runs) |
| S3 Net Γ | Which way, how one-sided? | L6 · ENH-121 | `v_gex_abs_exposure.net_gex_cr`, `.abs_gex_cr` (γ). **derived** net/gross = `net_gex_cr / abs_gex_cr`. Sign word (`long γ` / `short γ`) from the sign of `net_gex_cr` | value, hue by sign; subtitle word + ratio | its own gross | `net_gex_cr` null → `—` with "no run". **No "neutral" word** (no band — E-4) | select → Overview, Net Γ | `sql/2026-09-15_s79_v_gex_abs_exposure.sql:145` (COMMENT not live — P2) |
| S3 split bar | How one-sided? | L6 | **derived** from the same row: dampening = `(abs_gex_cr + net_gex_cr) / 2`; amplifying = `(abs_gex_cr − net_gex_cr) / 2`; each ÷ `abs_gex_cr` for width | two segments, warm left, cool right, centre tick | each other | as S3 | — | contract §6 (no client re-sum of `gex_cr`) |
| S4 Flip | Room before hedging flips? | L3 · ENH-131 | `v_gex_repriced_flip.flip`, `.flip_minus_spot`, `.status` (chain). **derived** % = `flip_minus_spot / spot × 100` | value + distance | spot | `status`: OK → value · `NO_CROSSING` → "no flip in grid" · `SKIPPED_EXPIRY` → "skipped · expiry day" · `UNMEASURABLE_R` → "carry unmeasurable". `flip` null on any non-OK status | select → Overview, Flip | `v_gex_repriced_flip` COMMENT (6,997 chars, live) |
| S4 marker | — | L3 | same; track spans spot ± 3 % | spot dot centre, dashed tick at flip, span between | spot | non-OK status → no tick, track only | — | — |
| S5 Corridor | Where are the written edges? | L4/L5 · ENH-120 | `v_gex_strike_walls.put_wall`, `.call_wall`, `.corridor_state` (γ). **derived** width % = `(call_wall − put_wall) / spot × 100` | two strikes + state word | spot | `INSIDE` → "inside" · `ABOVE_CEILING` → "above call wall" · `BELOW_FLOOR` → "below put wall" · `UNDEFINED` → "corridor undefined". The words avoid "ceiling/floor" (reserved for the γ pair). `iv_fresh = false` → subtitle adds "IV stale" | select → Overview, Corridor | `v_gex_strike_walls` COMMENT (live) |
| S5 track | — | L4/L5 | same + `gamma_metrics.spot`; track spans put wall − pad … call wall + pad, pad = max(3 strikes, 25 % of width) | span, put tick (mid grey), call tick (light grey), spot dot | — | `UNDEFINED` → no span | — | — |
| S6 Pin | Where is the centre, how decisive? | L2 + L12 · ENH-81, ENH-125 | point: `v_gex_strike_rank.strike` where `strike_rank = 1` (γ). share: `.share_of_abs` rank 1. **derived** lead = `(share_of_abs[1] − share_of_abs[2]) × 100`, in share points. Coincidence suffix `≡ call OI wall` / `≡ put OI wall` when `strike[1]` equals a wall | strike + share + lead | runner-up | fewer than 2 ranked rows → lead and #2 bar omitted | select → Pin, Pin | `v_gex_strike_rank` COMMENT (live); S74 note in caveat |
| S6 bars | — | L12 | **derived** #2 width = `share_of_abs[2] / share_of_abs[1]` | #1 light bar full width, #2 grey bar | — | as S6 | — | — |
| S7 IV · VIX | Price of time? | L9 · ENH-130 | `v_iv_term_structure.atm_iv` where `leg = 1` (chain); `gamma_metrics.vix` (γ) | two values | back leg (IV tab) | `front_is_0dte = true` → IV subtitle "front is 0 DTE" | select → Overview, Priced move | `v_iv_term_structure` COMMENT (live) |
| S7 subtitle | What move is priced? | — | `gamma_metrics.straddle_atm` (γ). **derived** % = `straddle_atm / spot × 100` | `priced move ±189 · ±0.83 %` | — | null → subtitle omitted | — | — |
| S10 Clock chip (conditional) | Are γ and chain readings from the same moment? | — | `v_gex_strike_walls.ts` vs `v_gex_repriced_flip.ts` | chip | — | hidden when the two `ts` are within 5 min | — | contract §0 |

### B.1a Bindings for R1–R4 — measured S88 (2026-10-01 13:08–13:22 IST)

Source: `scratch/s88_design/cols.out` (sha256 `41fbc556…`) via `cols_digest.out`; read as `merdian_ro`. **Anon readability is derived from `has_table_privilege` + RLS/policy state, not from a read performed as anon** — the authoritative single-run `SET LOCAL ROLE anon` check is owed in the SQL editor (E-16a).

| tile | quantity | binding | previous-session baseline | states |
|---|---|---|---|---|
| S8 future | front-month future last price | `index_futures_snapshots.futures_price`, `.contract_symbol`, `.expiry_date`, `.ts` (RLS off, anon SELECT yes) | — | before today's first row → "futures from 09:30"; age past floor → "futures stale" |
| S8 basis | future − spot | `index_futures_snapshots.basis` (and `.basis_pct`); spot and basis are one row, `spot_price` | the **last in-session row (≤ 15:30 IST)** of the previous trading session — **not** the last row of the day: the table carries a **16:00:06** post-close row (NIFTY basis 79.55, SENSEX 519.71 on 09-30), and a post-close basis is not the session's basis | — |
| S8 contract | which future | `.contract_symbol`, `.expiry_date` — **the October monthly** (NIFTY 10-27, SENSEX 10-29), not the weekly option front | — | subtitle names the contract; never implies it is the options front |
| S9 pre-open | pre-open print | `market_spot_snapshots.spot`, `.ts` where `source_table = 'dhan_idx_i'` and IST time in [09:00, 09:15) — the **last** such row | — | no row → "no pre-open print"; shown **with its time** (C.8) |
| S9 final open | session open | `market_spot_snapshots.raw ->> 'ohlc_open'` on the **first `dhan_charts_intraday` row at or after 09:15** (09:16 bar). **Never `spot` at 09:16** — that is the bar's close | — | before the first bar → "final at 09:16" |
| S9 previous close | prior session close | **NOT `market_spot_session_markers`.** Measured S88 (`markers_check.out`): its writer runs at **16:10 IST**, so today's row does not exist during the session, and the front end's newest-row read (`queries.ts:11-27`, no date filter) returns the previous session's row, whose `prev_close_spot` is the close **two sessions back**. Bind instead to the previous trading session's settled close in `market_spot_snapshots` — the ADR-022 settled-close bar, measured S88 (`capture_s88.md` §3.6): the settled close is the **16:00:04 IST `dhan_idx_i` row** of the previous trading session (post closing-auction, ADR-022); the 15:15 bar is pre-auction and is **not** the close. On 2026-10-01 the stale read overstated NIFTY's fall by **0.4178 pp** (−1.2953 % vs −0.8775 %) | previous **trading** session from `trading_calendar`, never "yesterday" | no row → "prev close missing"; never fall back to a markers row |
| S9 alt. source | gap already computed | the same table carries `premarket_ref_ts`, `premarket_ref_spot`, `open_0915_ts`, `open_0915_spot`, `gap_open_pct`, `premarket_move_pct`, `capture_quality` | — | **not bound.** Measured S88: populated for 09-30 (operator editor read); `open_0915_spot` **is the 09:16 bar's close** (writer window 09:15–09:18, `c9c2ab3`), so `gap_open_pct` is computed off a close, not the open; and the day's row did not exist intraday. The board computes the gap in the read layer from `ohlc_open` instead |
| S2 change | spot vs previous close | as S9 previous close | as above | as above |
| S7 VIX change | VIX vs previous session | `gamma_metrics.vix`, last row of the previous trading session (09-30: 15:40:05, 13.49) | `trading_calendar`-derived (E-19) | no prior row → change omitted |

**Findings from the measurement that the design now carries:**

1. **The pre-open print lands at 09:11:03–04 IST**, both symbols, both days, and no row exists between 09:00 and 09:11. **This is by design**: the capture cron was moved 09:08 → 09:11 at S74 (`7bb1779`), after the exchange's ~09:08 price fix, so the 09:11 row carries the settled pre-open price. The tile shows the print with its own timestamp (E-21, resolved).
2. **There is no 09:15 open row.** The open is inside `raw` on the 09:16 bar.
3. **`market_spot_session_markers.open_0915_spot` exists** — `merdian_reference.json` rule 17 (S13) says `open_0915` does not; the schema has moved since. Rule 17 is stale on this point.
4. **VIX is one series**: both symbols carry 13.49 at the same ts. Expected (India VIX); recorded.
5. **anon holds `MAINTAIN` + `SELECT` on two of the three tables but not the third** — grant hygiene (P4 shape), not an open door.

### B.2 Overview

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| Net Γ | as S3 | L6 | as S3 | list row | flip, corridor | as S3 | select → bars at full opacity, caption | as S3 |
| Flip | as S4 | L3 | as S4; quality note `n_cross_full_grid` when > 1 ("2 crossings in grid") | list row + dashed rule | spot, net Γ | as S4 | select → rule turns pale gold | as S4 |
| Corridor | as S5 | L4/L5 | as S5; `corridor_width_sigma` **not shown** until canonical σ (contract Part 3 §1) | list row; selected → corridor rows tinted pale gold at 7 % | spot | as S5 | select → both wall rules and the span highlight | as S5 |
| Pin (γ-conc) | as S6 | L2/L12 | as S6 | list row + dotted rule | spot | — | select → rule highlights | as S6 |
| Priced move | What move is the market paying for? | — | `gamma_metrics.straddle_atm` (γ) | list row `±189`; left gutter on strikes with `|strike − spot| ≤ straddle_atm` | flip, corridor | null → gutter empty, row omitted | select → gutter turns pale gold | — ; caveat: "not σ" (E-2) |
| Spot | — | — | as S2 | list row + solid rule | — | — | — | — |
| Time to expiry | How near is expiry? | — | `v_iv_term_structure.dte_sessions` leg 1 (chain) | list row | — | 0 → "expiry day" | — | contract §11 |
| Ladder — signed γ per strike | Where does dealer gamma sit? | L1 · ENH-80 | `gex_strike_snapshots.strike`, `.gex_cr` for the latest `run_id` per symbol (γ) | horizontal diverging bars; length = `gex_cr`, scaled to the window; hue by sign | spot, flip, walls, pin | strikes with `gamma_call` and `gamma_put` null contribute 0 and are drawn as an empty row with readout `·`, not a zero bar | hover → D.3 | ENH-80 COMMENT (97 chars) — thin; see E |
| Gamma terrain | Which pocket is spot in? | L1 | sign of `gex_strike_snapshots.gex_cr` per row (γ) | row background, cool or warm at 7 % (11 % inside the corridor) | — | contributes-0 rows → no tint | — | — |
| Pin band gutter | Where is the τ-weighted zone? | L2 · ENH-81 | `v_gex_strike_pin_zone.pin_lower`, `.pin_upper` (γ) | right gutter filled cool at 55 % | pin point | no row → gutter empty | selected (Pin band) → pale gold | `v_gex_strike_pin_zone` COMMENT |
| γ CEILING / FLOOR slot | Most call-side / put-side gamma? | L4/L5 γ pair | **GAP** — no column (contract Part 3 §2; E-3) | two dotted rules, off by default | OI walls | toggle disabled | toggle | — |

### B.3 Pin

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| Pin (γ-conc) | Which strike holds the most gamma? | L12 · ENH-125 | `v_gex_strike_rank.strike`, `.gex_cr`, `.side` where `strike_rank = 1` (γ) | list row; rank-1 bar | runner-up, max pain (OI tab) | — | select → bar #1 outlined | `v_gex_strike_rank` COMMENT |
| Runner-up | What is second? | L12 | same, `strike_rank = 2` | list row; bar #2 | pin point | absent when `n_ranked < 2` | select → bar #2 outlined | same |
| Lead | How decisive is the pin? | L12 | **derived** `share_of_abs[1] − share_of_abs[2]` | number in share points; **no LOCKED/CONTESTED word** (no band — E-4) | — | — | select → #1 and #2 outlined, the rest dimmed to 35 % | contract Part 3 §5 |
| Share of book | How big is the top strike? | L12 | `v_gex_strike_rank.share_of_abs` rank 1 | % | cumulative share | — | select | same |
| Pin band | Where is the τ-weighted pin zone? | L2 · ENH-81 | `v_gex_strike_pin_zone.pin_lower`, `.pin_upper`, `.n_strikes`, `.tau_used` | range; right gutter | pin point | no row → omitted | select → gutter pale gold | `v_gex_strike_pin_zone` COMMENT; S74 "renders, does not predict" in caveat |
| Pin distance | How far is the pin from spot? | L2 | **derived** `(strike[1] − spot) / spot × 100` | % · σ — | spot | — | — | — |
| Legacy pin-risk score | (legacy reading) | pre-parity | `gamma_metrics.pin_risk_score` (γ) | number /100, **no band words** | — | null → omitted | select → detail only | none — decision E-D4 |
| Ladder — share by strike | Is the centre one strike or a shelf? | L12 | `v_gex_strike_rank.strike`, `.share_of_abs`, `.side`, all ranked rows; top 10 emphasised | bars from the left edge, one scale; hue by `side` | each other | unranked strikes → empty row | hover → D.3 | same |

### B.4 Gamma

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| Top-strike share | How dominant is the largest strike? | L12 · ENH-122 | `v_gex_concentration.hhi_net` (γ). **Label is "top-strike share", never "HHI"** — the column is max/sum (contract Part 3 §4) | % | call and put legs | — | select | `v_gex_concentration` COMMENT ("max/sum") |
| Top call-strike share | same, calls | L12 | `v_gex_concentration.hhi_call` | % (detail panel) | put leg | — | — | same; COMMENT: split is load-bearing |
| Top put-strike share | same, puts | L12 | `v_gex_concentration.hhi_put` | % (detail panel) | call leg | — | — | same |
| DTE bucket | Which regime of concentration applies? | L12 | `v_gex_concentration.dte_bucket` | word `0` / `1-2` / `3+` in the Top-strike-share subtitle | — | all three reachable; only `3+` observed | — | same |
| Gross |Γ| | How big is the whole book? | L6 | `v_gex_abs_exposure.abs_gex_cr` | ₹ Cr (unit caveat, E-1) | net | — | select | abs-exposure `sql/` COMMENT |
| Net Γ | as S3 | L6 | as S3 | list row | gross | as S3 | select | as S3 |
| Contributing strikes | How many strikes carry any gamma? | L6 | `v_gex_abs_exposure.n_contributing`, `.n_strikes` | "113 / 138" | — | — | select | contract §6 |
| Net-long γ strike | Where is the largest positive strike? | L1 | **derived** argmax of positive `gex_strike_snapshots.gex_cr`, or `gamma_metrics.max_gamma_strike` — decision E-D5 | list row + dotted rule | pin point (≡ when the same strike) | no positive strike → omitted | select | ADR-024 Amendment A caveat: not "near spot" |
| Net Γ today | Is net gamma moving? | L6 | `gamma_metrics.ts`, `.net_gex` today (γ), deduped by `ts` | sparkline, only with ≥ 3 distinct runs | — | < 3 runs → no sparkline, no text | — | S81 ruling |
| Ladder — signed γ + silhouette | Where does the book change sign? | L1 | `gex_strike_snapshots.strike`, `.gex_cr` (latest run); **derived** cumulative = running sum from the highest strike down | diverging bars + one white dot per row at the cumulative total | spot, flip | as Overview | hover → D.3 | ENH-80 |
| River | How has settled net Γ moved? | L14 · ENH-126 | `v_gex_net_gamma_river.session_date`, `.net_gex_cr`, `.session_min_net_gex_cr`, `.session_max_net_gex_cr`, `.session_complete`, `.spot`, `.dte` | band (min–max) + point per day; price on its own scale; zero line; 0-DTE sessions marked | zero; price | `session_complete = false` → hollow point; data hole 2026-06-04 → 08-23 drawn as a break (ADR-020) | hover → day readout | `v_gex_net_gamma_river` COMMENT ("single sample, not an aggregate") |

### B.5 OI

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| Call OI wall | Where is the largest call OI in the band? | L4 · ENH-120 | `v_gex_strike_walls.call_wall`, `.call_wall_oi` (γ) | strike + OI in lakh/crore contracts | spot, pin | `iv_fresh = false` → "IV stale" | select → rule and bar highlight | `v_gex_strike_walls` COMMENT |
| Put OI wall | same, puts | L5 | `.put_wall`, `.put_wall_oi` | as above | spot, pin | as above | select | same |
| Corridor | as S5 | L4/L5 | as S5 + `n_eligible_strikes` in the detail panel | row | spot | as S5 | select | same |
| Max pain | Where is total payout smallest? | L19 · ENH-123 (extension) | **P5 decision pending (E-D2).** Proposed: `v_gex_max_pain.max_pain_strike` (γ clock — same run as walls and pin). Alternative: `v_max_pain_by_strike.max_pain_strike` (chain) | row + dash-dot rule | pin point | `is_fresh = false` → "stale" chip | select | file COMMENT `v_gex_max_pain.sql:125` (not live — P2) |
| Max-pain valley | How sharp is the minimum? | L19 | the same view, all candidate rows: `v_gex_max_pain.candidate_strike`, `.total_pain` (γ) — or `v_max_pain_by_strike.candidate_strike`, `.total_pain` under the alternative | one dot per row at total payout, min–max of the window mapped to 4–96 % | max pain | a strike with no candidate row → no dot | — | same |
| Pin vs max pain | Do the two centres agree? | L19 · ENH-124 | `v_gex_pin_maxpain.gap_points`, `.gap_strikes`, `.max_pain_in_pin_band`, `.max_pain_in_corridor` (γ). `gap_sigma` **not shown** until canonical σ | `−150 pts` + subtitle `−3 strikes · in band: no · in corridor: yes` | — | `sigma_overstated_expiry_day = true` → caveat line | select → both rules highlight | file COMMENT `:137` (not live); "unanswered by design" in caveat |
| OI since open | What was written or closed today? | L13 · ENH-127 | `v_oi_rotation_since_open.strike`, `.ce_oi_delta_qty`, `.pe_oi_delta_qty`, `.ce_presence`, `.pe_presence`, `.is_fresh` (chain) | row: largest add and largest cut; 2 px tick under each ladder bar | since open | `ANCHOR_ONLY` / `LATEST_ONLY` → tick hollow, named in hover. **SENSEX: row and ticks absent** until the outlier guard exists (contract §9) | hover | `v_oi_rotation_since_open` COMMENT |
| Ladder — OI butterfly | What is written at each strike? | L4/L5 | `gex_strike_snapshots.strike`, `.oi_call`, `.oi_put` for the latest run (γ) — the live columns, **not** `oi_total_calls` (contract §2) | calls right, puts left; neutral greys; size at the readout | walls, max pain, pin | null OI → empty row | hover → strike · call OI · put OI · ΔOI | contract §2 |

**Clock note for this tab.** The butterfly and the walls are on the γ clock; the ΔOI ticks are on the chain clock. The S8 clock chip is therefore shown on the OI tab whenever the two differ by more than one cycle (D.5).

### B.6 Flows

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| Hedge per 1 % | What must dealers trade per 1 % move? | — · ENH-81 | `v_dealer_flow_sim.flow_cr`, `.direction` where `spot_pct = ±1` (γ), filtered by `symbol` | ₹ Cr + BUY/SELL (the view's own words) | net Γ | — | select → line highlights | `v_dealer_flow_sim` COMMENT (153 chars) + contract §16 |
| Reaches flip? | Does a 2 % move reach the flip? | — | `v_dealer_flow_sim.crosses_flip`, `.scenario` | first scenario where true, else "no" | flip | flip non-OK → "flip not available" | select → flip rule on the chart | same |
| Flow line | Hedge flow against spot move | — | all six rows: `.spot_pct`, `.flow_cr`, `.direction` | one line through zero, six labelled dots; flip at `flip_minus_spot / spot × 100` | zero | — | hover → dot readout | same |
| Vanna (L7) | — | L7 · ENH-98 | **absent** (no view) | not rendered | — | — | — | ruling 9 |
| Charm (L8) | — | L8 · ENH-98 | **absent** (no view) | not rendered | — | — | — | ruling 9 |

### B.7 IV

| tile | question | layer / ENH | binding (clock) | form | compared against | states incl. absence | interaction | explanation source |
|---|---|---|---|---|---|---|---|---|
| Front ATM IV | What is the front expiry charging? | L9 · ENH-130 | `v_iv_term_structure.atm_iv`, `.expiry_date`, `.atm_strike` where `leg = 1` (chain) | vol pts | back | `front_is_0dte` → caption note | select | `v_iv_term_structure` COMMENT |
| Back ATM IV | Second weekly | L9 | same, `leg = 2` | vol pts | front | no leg 2 → "one expiry captured" | select | same |
| Short-end slope | Is the short end rising or falling? | L9 | `v_iv_term_structure.term_slope` | signed vol pts; **no Normal/Flat/Inverted word** (no band) | parity gap | NULL → "one expiry captured" | select | same |
| Parity gap | Can the ATM quote be trusted? | L9 | `v_iv_term_structure.parity_gap` per leg | vol pts, `front · back` | slope | — | select | same (quality column) |
| Forward vol | Implied vol between the two expiries | L9 | `v_iv_term_structure.fwd_vol_from_prev`, leg 2 only | vol pts (detail panel of Back ATM IV) | front | leg 1 → not shown | — | same |
| Skew₉₈ | How much dearer is 2 % OTM cover? | L10 · ENH-132 | `v_iv_surface.leg_skew_98`, `.leg_k98`, `.leg_atm_iv`, `.leg_status` (chain), per leg | signed vol pts, per leg; **not comparable across legs** | its own change | `leg_status = SKIPPED_EXPIRY` → "skipped · expiry day" | select → k₉₈ rule | `v_iv_surface` COMMENT |
| ATM straddle | What does today's move cost? | — | `gamma_metrics.straddle_atm` today; 5-day bucket average from `useStraddleIntraday` | ₹ + % vs 5-day | 5-day average | < 1 prior day → average omitted | select → Priced move gutter | — |
| Ladder — smile | Where is IV along the strikes? | L10 | `v_iv_surface.strike`, `.iv`, `.side_used`, `.quote_state`, `.leg_atm_strike`, `.leg_k98`, selected `leg` | dot per strike, IV on x, hairline to the left edge; tone by `side_used` | ATM | `quote_state = OTM_ABSENT` or `iv = 0` → `no quote`, no dot | hover → strike · iv · side · parity gap | same |

### B.8 Home, Context, Structure, and the ladder chrome

| tile | binding | notes |
|---|---|---|
| Home masthead | as S1, S2 | — |
| Home question cards | the headline values of each tab, from the bindings above | no new reads; each card's picture reuses its strip micro-visual or tab chart at small scale |
| Context line | `market_environment_snapshots.ambient_regime`, `.lens_alignment`, `.as_of_date` (latest by `as_of_date`); WCB and A/D from the Breadth bindings | `useAmbient` already reads the latest row correctly |
| Ambient trajectory | `useAmbientSeries` columns (Appendix A) — **order descending, limit 40, then reverse** | fixes L-3 |
| Expiry memory | `v_expiry_base_rates.*`, `expiry_outcomes.*` | N beside every rate; counts, not %, when N < 5 |
| Breadth | `weighted_constituent_breadth_snapshots` (`useWcbLatest` columns), `market_breadth_intraday.*` | — |
| Signals | `signal_snapshots` (`useTodaysSignals` columns) | collapse identical consecutive rows; decision E-D6 |
| Structure — zones | `ict_zones.*` — filter to valid zones and ±2 % of spot, both sides | the validity column name is **not** in the contract (`ict_zones` is outside the eighteen). **GAP until confirmed** (E-11) |
| Chain minimap | `gex_strike_snapshots.strike`, `.gex_cr` for the whole latest run (γ) — the same rows as the ladder, unwindowed | one 3 px bar per strike, scaled to the whole chain's max |
| Edge chips | the tab's level bindings, compared against the window | no new reads |

---

## C. Visual system

### C.1 Theme — dark "instrument"

The board is read for hours at a desk, next to charting software, often in a dim room. It is dark, low-glare and quiet, so that the few bright things on it — spot, the selected element, a sign — are the things that matter. **Proposed default: dark.** ENH-110 already names dark as primary. Whether the live site's light theme was deliberate is decision **E-D3**; if it was, a light token set is owed before §H.

### C.2 Colour — one meaning per hue

**The rule:** hue carries **sign** and nothing else. Side (call/put) is carried by **tone** (light vs mid grey). Levels are told apart by **line style and a word**. Magnitude is carried by **length**, never by opacity or hue intensity. Selection is the only warm-pale colour on the board.

**Temperature for sign.** Cool = the book leans against moves; warm = it leans with them. The metaphor is physical (a cool book is damped, a warm one is running) and it survives colour-vision deficiency better than green/red: blue and orange differ in both hue and lightness.

| token | hex | meaning |
|---|---|---|
| `--bg` | `#0D0F12` | page |
| `--strip` | `#12151A` | strip cells |
| `--s1` | `#15191E` | card, tab-card, detail panel |
| `--s2` | `#1C2127` | selected strip cell, selected nav chip |
| `--s-sel-row` | `#20262E` | selected list row |
| `--line` | `#22272E` | hairlines between regions |
| `--line-2` | `#2A3038` | control borders |
| `--axis` | `#2F363F` | ladder zero axis |
| `--ink-1` | `#ECEEF1` | values, spot rule and tag |
| `--ink-2` | `#A0A8B3` | labels, subtitles, captions |
| `--ink-3` | `#7F8893` | tertiary labels, strike labels without a level |
| `--rule` | `#B8BEC6` | level rules that are not spot and not selected |
| `--cool` | `#5DB4F5` | positive sign: dampening, long γ, OI added, dealers buy |
| `--warm` | `#FF8A4C` | negative sign: amplifying, short γ, OI removed, dealers sell |
| `--call` | `#D5DAE0` | call side (OI butterfly, call wall tick, CE-quoted smile dots) |
| `--put` | `#7F8A97` | put side (OI butterfly, put wall tick, PE-quoted smile dots) |
| `--sel` | `#F3E7B3` | **interaction only**: selected tab rule, selected row rule, selected level, minimap window, active zoom mode |
| `--alert-bg` / `--alert-fg` | `#5A1D1D` / `#FFD7D2` | the stale strip only (P3). Never inside a chart |

Derived fills: gamma terrain `rgba(93,180,245,.07)` / `rgba(255,138,76,.07)` (0.11 inside the corridor on Overview); pin-band gutter `rgba(93,180,245,.55)`; priced-move gutter `rgba(236,238,241,.30)`; selected-corridor rows `rgba(243,231,179,.07)`.

**Two corrections to the prototype, proposed for review:**

1. **Max-pain valley and max-pain tick** use `#C9B77A` (a gold) in the prototype. Gold sits next to the selection colour and carries no sign or side, so it breaks the one-meaning rule. **Proposed: `--ink-2` dots, and the max-pain rule in `--rule` dash-dot like every other level.** The valley shape and the dash-dot style carry it; colour is not needed.
2. **The "ILLUSTRATIVE DATA" badge** also uses `#C9B77A`. It disappears on real data, so it does not matter for the build; noted so it is not copied into the Lovable prompt.

**Contrast, computed from the hexes (WCAG relative luminance).** `--ink-2` on `--s1` 7.35:1; `--ink-3` on `--s1` 4.91:1, on `--strip` 5.09:1, on `--bg` 5.34:1; `--cool` on `--bg` 8.51:1; `--warm` on `--bg` 8.22:1; `--put` on `--bg` 5.47:1; alert text on alert fill 9.77:1. **One failure:** `--ink-3` on the selected-row fill `--s-sel-row` is **4.24:1**, under 4.5. The prototype draws list labels in ink-3 on that row. **Fix: on the selected row, the label switches to `--ink-2`.** The muted question numbers on Home (`#4A525D`) are decorative and carry no information.

**Why calls and puts are grey, not coloured.** On the OI butterfly a call bar is not "positive" and a put bar is not "negative". If side took a hue, a reader would carry the sign meaning into the butterfly, which is the target's own inconsistency (study B3, B6). Two tones of grey say "two sides" and nothing more; the ΔOI ticks under them carry the sign.

Every sign is also written: `+` and the true minus `−` (U+2212). Colour is never the only carrier (ADR-017 P3, study B9).

### C.3 Type

**IBM Plex Sans** for text; **IBM Plex Sans Condensed** for large values and the wordmark. `font-variant-numeric: tabular-nums` on every number, so digits do not jitter as values update. Plex is a technical face with open apertures and distinct 1/l/I and 0/O; the condensed cut lets a 7-cell strip fit 1440 px without shrinking numbers.

| role | size / line | weight | colour | treatment |
|---|---|---|---|---|
| Wordmark | 15 | 700 condensed | ink-1 | tracking 0.18 em |
| Nav item | 13 | 500 | ink-2; selected ink-1 on `--s2` | Health/Settings ink-3 |
| Home spot | 56 / 60 | 600 condensed | ink-1 | — |
| The read | 17 / 26 (Home) · 14 / 21 (Board) · 13.5 / 20 (phone) | 400 | `#D8DCE1` | max ~95 characters per line |
| Strip label | 10 / 14 | 600 | ink-3 | uppercase, tracking 0.10 em |
| Strip value | 20 / 24 | 600 condensed | ink-1, or sign hue | tabular |
| Strip subtitle | 11 / 15 | 400 | ink-2 | tabular, single line, ellipsis |
| Tab label | 14 / 20 | 600 | ink-2; selected ink-1 | selected: filled chip + 2 px `--sel` top rule |
| List label | 10 / 14 | 600 | ink-3; **ink-2 on the selected row** (contrast, C.2) | uppercase, tracking 0.10 em |
| List subtitle | 11 / 15 | 400 | ink-2 | — |
| List value | 16 / 20 | 600 | ink-1, or sign hue | tabular, right-aligned |
| Chart title | 10 / 14 | 700 | ink-2 | uppercase, tracking 0.10 em |
| Strike label | 11.5 (10 when rows < 18 px) | 400; 600 on level rows | ink-3; ink-1 on level rows | right-aligned |
| Level pill | 10 | 700 | ink-1 on `--bg`, 1 px `#3A414B` border; selected: `--bg` on `--sel` | uppercase, tracking 0.08 em |
| Readout | 11 (10 dense) | 400 | sign hue or ink-2 | right-aligned |
| Caption | 12 / 18 | 400 | ink-2 | sentence case |
| Detail title | 22 / 28 | 700 | ink-1 | — |
| Detail slot header | 10 / 14 | 700 | ink-3 | uppercase, tracking 0.12 em |
| Detail body | 13 / 20 | 400 | ink-1 | max 72 characters per line |

Phone: strip value 18, list value 15, strip label 9.5; everything else unchanged.

### C.4 Levels on the ladder

All levels are horizontal rules across the chart cell. One weight for every strike mark (S81 ruling; P6 salience deferred). Selected: the rule turns `--sel` at 2 px and its pill fills `--sel`.

| level | rule | label |
|---|---|---|
| Spot | ink-1, solid, 2 px, soft glow `0 0 10px rgba(236,238,241,.45)` | filled ink tag with the value at the left axis; pill `SPOT` at the right |
| Flip | `--rule`, dashed, 1 px | tag `+2.09 %` at the left axis; pill `FLIP 23,299` |
| Call OI wall | `--rule`, solid, 1 px; `--call` tick in the strip | pill `CALL OI WALL` |
| Put OI wall | `--rule`, solid, 1 px; `--put` tick in the strip | pill `PUT OI WALL` |
| Corridor | (no fill on the ladder; the two wall rules and the terrain carry it; selected → pale-gold row tint) | — |
| Pin band | right gutter, `--cool` at 55 % | legend "pin band" |
| Priced move | left gutter, ink at 30 % | legend "priced move (straddle)" |
| γ-conc | `--rule`, dotted, 1 px | pill `γ-CONC` |
| Net-long γ (Gamma tab) | `--rule`, dotted | pill `NET-LONG γ` |
| Max pain | `--rule`, dash-dot (proposed; C.2) | pill `MAX PAIN` |
| γ CEILING / FLOOR (when on) | `--rule`, dotted 2-2 | `γ CEILING`, `γ FLOOR` — never "wall" |
| k₉₈ (IV tab) | `--rule`, dotted | pill `k₉₈` |

**Coincidence.** When two named strikes land on the same strike, the rule is drawn once (solid wins over dotted) and the pill reads both names joined by `≡` — for example `γ-CONC ≡ CALL OI WALL`. No ring, no highlight, no colour (S81 ruling: both bases are OI-weighted, so the coincidence is partly arithmetic). This is separate from the ADR-017 P4 confluence ring, which belongs to the Structure page (A.8, F).

### C.5 Spacing and shape

- 4 px base: 4 · 8 · 12 · 16 · 24 · 32 · 48.
- Page gutters: 24 px desktop (48 px on Home), 12–16 px phone. Content max width 1440 px.
- Cards: radius 10–12, no border, `--s1` on `--bg`. The tab card joins its selected tab (square top-left corner).
- Strip: 1 px `--line` gaps between cells (the grid shows through), cell padding 12 × 16, min height 66 px on phone.
- Value-list row: min 52 px desktop, 48 px phone; selected row `--s-sel-row` with a 3 px inset `--sel` left rule.
- Touch targets ≥ 44 px on phone (menu button, symbol toggle, list rows, zoom buttons).
- Ladder: row height 8–26 px by window (A.5); 22 px fixed on phone.

### C.6 State treatments

| state | where it appears | treatment |
|---|---|---|
| **Healthy, fresh** | everywhere | nothing. No "LIVE" pill, no "updated 5s ago", no "auto every 60s" (all three are on today's shell — ADR-017 P1, P3) |
| **Stale source** | shell | `--alert` strip across the top under the bar: "chain data 14 min old · Health ›". Hidden when fresh |
| **Clocks differ** | strip S8 | ink-2 chip `γ 11:20 · chain 11:40`; hidden within one cycle |
| **Named absence** (`SKIPPED_EXPIRY`, `UNMEASURABLE_R`, `NO_CROSSING`, `OTM_ABSENT`, NULL slope, `UNDEFINED` corridor) | value slot, strip, list | dashed-outline chip, ink-2, with the plain words from B (e.g. "skipped · expiry day"). Never 0, never the previous value. The level's rule and edge chip are not drawn |
| **Data hole** (e.g. 2026-06-04 → 08-23) | river, any series | the line breaks; the gap is labelled once, "no data", on hover |
| **Not built** (L7, L8, L18) | Flows | the tile does not exist. No placeholder, no greyed card |
| **No band measured** | any value that would take a state word | the number alone. The detail panel's SCALE slot reads "band not measured — calibration gap" and names the gap |
| **Stale value inside a fresh view** (`is_fresh = false`, `iv_fresh = false`) | the value's subtitle | ink-2 word "stale" or "IV stale", no colour |
| **Suppressed pending a guard** (L13 on SENSEX) | OI tab | ΔOI row and ticks absent for that symbol; the detail panel says why |
| **Selected** | strip cell, tab, list row, level, gutter, bars | `--sel` rule/fill on the control; the level or gutter turns `--sel`; for Pin/Lead/Runner-up, non-selected bars drop to 35 % |
| **Contributes nothing** (strike stored, `gamma_call`/`gamma_put` null) | ladder row | empty row, readout `·` |

### C.7 Numbers

One scale family:

- **Exposure** (`gex_cr`, `net_gex_cr`, `abs_gex_cr`, `flow_cr`): ₹ Cr with lakh scaling. At or above 1 lakh Cr the value prints as `L Cr` with one decimal (`+10.0L Cr`); below that, full Indian grouping (`−13,782 Cr`). Never a doubled unit ("Cr Cr"), never `k`. The unit is always beside the number. **Held until E-1 is answered** (what one unit of `gex_cr` means).
- **Contracts** (OI, ΔOI): lakh / crore contracts — `1.52 Cr`, `−4.3 L`. Never converted to ₹ (study B7). In the readout column, `1.52 C` / `1.68 P` (the letter names the larger side).
- **Distances:** `+2.09 %` of spot; `σ —` beside it until the canonical σ exists.
- **Priced move:** `±189` points, and `±0.83 %` of spot in the strip.
- **IV, slope, skew, parity gap:** vol points, two decimals, signed where a sign exists.
- **Shares:** % with one decimal; leads in share points (`2.9 pts`).
- **Strikes:** no decimals, Indian grouping (`23,299`, never `23,299.21`).
- **Time:** IST, `HH:MM`, only where a timestamp is itself the information (clock chip, detail panel).


### C.8 Change marks (R1)

A **change mark** is a small triangle and a signed change beside or under a value: `▲ +0.42` / `▼ −1.05 %`.

- **Glyph:** `▲` up, `▼` down, `◆` unchanged within display precision. 9 px, baseline-aligned with the change text.
- **Colour: ink, not the sign hues.** `--cool` and `--warm` mean *dampening* and *amplifying* (C.2). Spot going up is not "dampening", so a cool up-arrow would carry a false meaning. The triangle's direction carries the direction; ink-2 for the mark and its text. **This corrects the prototype**, which draws spot's change in warm orange.
- **Baseline is stated once per class, never per cell:**

| value | change against | where shown |
|---|---|---|
| Spot | previous session close | S2 subtitle, Home masthead |
| VIX | previous session's last value | S7 subtitle |
| Futures basis | previous session's last basis | S8 subtitle |
| Gap | previous close (it *is* the change) | S9 value |
| Net Γ | previous session's settled value (`v_gex_net_gamma_river`, `session_rank = 2`) | S3 subtitle, Overview list |
| Front ATM IV | previous session's last value (**source GAP-M — E-20**; `v_iv_term_structure` is latest-only) | S7, IV tab |
| ATM straddle | the 5-day average at the same time of day (already in `useStraddleIntraday`) | IV tab |
| Walls, pin, flip, max pain | **no change mark.** A level's move is a strike jump, not a quantity; it is shown as text when it happens (`call wall rolled 23,000 → 23,100 since open`) — and only once the cross-snapshot wall state (study D1 item 4) is built. Until then, nothing. |

- **Absence:** no baseline → **no mark and no number** — never `▲ +0.00` and never a change against a stale baseline.
- **Phone:** marks stay; they are the cheapest carrier of direction on a small screen.

---

## D. Interactions

### D.1 The selection model

The board has **one selected value at a time**, per symbol. Its state is `{symbol, tab, selected, window, mode}`.

**What can select a value:**

| control | selects |
|---|---|
| a strip cell | that cell's value (its tab opens if not open) |
| a Home question card, or keys `1`–`6` | that tab's first value |
| a tab | that tab's first value (Overview → Net Γ · Pin → Pin · Gamma → Top-strike share · OI → Call OI wall · Flows → Hedge per 1 % · IV → Front ATM IV) |
| a list row, or `↑` / `↓` in the list | that value |
| a level pill on the ladder | that level's value |
| a READ IT WITH chip | that value, switching tab if it lives elsewhere |

**What a selection changes, together and at once** — this is the board's main teaching mechanism (study B4): the list row gets its `--sel` rule; the chart element turns `--sel` (rule, gutter, outline or row tint — C.6); the caption becomes the one sentence that names that element; the detail panel loads that value's slots.

**What a selection does not change:** the ladder window. Selecting a level that is off-screen does not pan to it; its edge chip carries the distance, and a click on the chip includes it (D.2). The operator's place on the axis is theirs.

### D.2 Zoom and the default view (answers ruling 4)

**The window is a range of strikes** `[lo, hi]`, always snapped to the strike step and clamped to the stored chain. It is shared by every ladder tab and by Structure.

| mode | window | when |
|---|---|---|
| **Near spot** (default) | spot ± max(2.5 × straddle, 1.2 % of spot), snapped outward to strikes | on load, on symbol switch, on `0` |
| **All levels** | from the lowest to the highest level on the current tab, + 2 strikes of margin each side | on `L`; recomputed when the tab changes while in this mode |
| **Full chain** | every stored strike | on `F` |
| **Custom** | whatever `+` / `−`, a chip, the minimap or `/` produced | after any of those |

**Why that default.** The straddle term scales with what the market is pricing, so the window grows on volatile days and near expiry shrinks with the move. The 1.2 % floor guarantees a readable ladder when the straddle is small (expiry afternoon). Worked on the prototype's figures: NIFTY spot 22,821.5, straddle 189 → half-width max(472.5, 273.9) = 472.5 → 22,300 … 23,300, 21 strikes, 26 px rows. SENSEX at ~73,000 with an *assumed* straddle of 600 → half-width 1,500 → ~31 strikes at step 100, 18 px rows. Real SENSEX figures come with the snapshot. **Spot is always inside the default window, by construction** — the "strike 21,000 at spot 26k" failure cannot occur.

**`+` / `−`.** Scale the half-width by 0.7 / 1.4 about the window's centre; minimum half-width 4 strikes; clamp to the chain.

**Edge chips.** Every level on the current tab that lies outside the window becomes a chip above or below the ladder: `▲ FLIP 23,299 · +2.09 %`. The arrow gives the side, the distance is % of spot. **A click includes the level**: the window extends just far enough to hold it plus one strike, and the mode becomes Custom. Levels in a named-absence state produce no chip.

**Chain minimap.** A 30 px column right of the ladder: every stored strike, 5 px each, a 3 px sign-hued bar per strike (scaled to the whole chain), a white tick at spot and a `--sel` box around the window. **A click re-centres the window** on that strike, keeping its size. It answers "where am I in the chain" and "is there anything big I cannot see" at once.

**Refresh.** A new cycle keeps the window in Custom and Full chain; in Near spot and All levels it recomputes from the new spot, straddle and levels, so the default view never drifts away from price.

**Density.** Row height and label thinning follow A.5. The readout column blanks on dense rows except level rows, so the ladder never becomes a wall of numbers.

**Phone.** Two mode buttons (`Near spot`, `All levels`) and the chips as a single text line ("▲ flip 23,299 is off-screen above · tap to include"). No `+` / `−`, no minimap, no pinch, no drag. Row height is fixed at 22 px; the window is Near spot unless a chip was tapped.

### D.3 Hover and the readout

- Every ladder row shows its readout in the fixed right-hand column; there are **no floating tooltips** over the chart (study B4's fixed-slot pattern, which does not cover the data).
- **Hover a row** (desktop): the row gets a faint `--s2` band and the caption line temporarily reads the row in full — strike · the tab's value · distance from spot, e.g. `23,000 · +14.4L Cr · +0.78 % · γ-CONC ≡ CALL OI WALL`. On OI: `23,000 · call 1.52 Cr · put 0.41 Cr · ΔOI +0.22 Cr call`. On IV: `22,600 · IV 13.20 · PE quote`. Leaving the ladder restores the selection's caption.
- Hover never changes the selection.

### D.4 The read — how the sentence is composed

One sentence of 2–4 clauses, built from bound values only. **It states; it never predicts, recommends or grades.** No word that needs a measured band (ADR-016) may appear in it.

| clause | shown when | template | source |
|---|---|---|---|
| Pocket | always, if the run has a contributing strike nearest spot | `Spot {spot} sits in {a dampening | an amplifying} pocket` | sign of `gex_cr` at the strike nearest spot |
| Nearest wall | corridor ≠ `UNDEFINED` | `, {x.x}% {under | above} the {call | put} OI wall at {wall}` | `v_gex_strike_walls` |
| Coincidence | the pin equals that wall | `, which is also the largest gamma strike` | `v_gex_strike_rank` rank 1 |
| Flip | `status = OK` | `. Flip is {±x.xx}% away, {inside | outside} the ±{straddle} the straddle is pricing by expiry` | `v_gex_repriced_flip`, `gamma_metrics.straddle_atm` |
| Flip absent | `status ≠ OK` | `. {No flip in the ±10 % grid | Flip skipped on expiry day | Carry unmeasurable, flip not computed}` | same |
| Balance | always | `. Net gamma is {x.xx} of gross` | `v_gex_abs_exposure` |

Recomposed every cycle. Selecting a value does not change it. The same sentence appears on Home and on every Board tab (the phone shows it under the strip).

### D.5 Symbol, clocks and refresh

- **Symbol:** the top-bar toggle, or `N` / `S`. Switching keeps the tab and the selected value, and resets the window to Near spot (the other symbol's price axis is unrelated).
- **Two clocks:** the clock chip (S8) appears whenever γ and chain differ by more than one cycle, on every page that shows both — which includes the strip on every page and the OI and IV tabs in particular.
- **Refresh:** each cycle updates in place. Selection, tab and window survive. `Space` freezes refresh (ADR-017 P7) and shows a small `frozen` chip in the bar; `Space` again resumes.

### D.6 Keyboard (ADR-017 P7, extended)

| key | action | source |
|---|---|---|
| `N` / `S` | symbol | ADR-017 |
| `1`–`6` | tab | new |
| `↑` / `↓` | previous / next value in the list | new |
| `+` / `−` | zoom in / out | new |
| `0` · `L` · `F` | Near spot · All levels · Full chain | new |
| `/` | strike search: type a strike, `Enter` centres the window on it | ADR-017 (was "jumps hero chart") |
| `Space` | freeze / resume refresh | ADR-017 |
| `J` / `K` | step signals (Context) | ADR-017 |
| `E`, `A` | reserved for Order and Journal; inert until those ship | ADR-017 |
| `?` | show the key list | ENH-110 Phase 3 |

Keys act only when the board has focus and no input is active.

### D.7 Phone

- Order: bar · strip (2 × 4, no micro-visuals) · the read · tabs · ladder · value list · detail.
- Tabs scroll inside their row; the page never scrolls sideways.
- The detail panel shows title and HOW TO READ; `More ›` expands COMPUTED, SCALE, CAVEAT and READ IT WITH in place.
- Home: masthead, the read, six cards in one column (answer lines, no pictures), context line.
- Structure and Context stack their sections; the Structure ladder follows D.2's phone rules.

### D.8 Absence inside interaction

- Selecting a value in a named-absence state still loads its detail panel, and the panel says **why** it is absent (e.g. `SKIPPED_EXPIRY`: "the repriced flip is not computed on expiry day, by design").
- Its level has no rule, no pill and no edge chip; the list row shows the dashed chip.
- READ IT WITH chips pointing at an absent value are still shown, so the reader can learn why.

---

## E. Gaps — named, not guessed

### E.1 Data and computation gaps (the board shows the gap, never a stand-in)

| # | gap | where it bites | what the board does meanwhile | owner / source |
|---|---|---|---|---|
| E-1 | **What one unit of `gex_cr` means** (₹ of hedge per 1 % move? per point?) | every exposure value; C.7 formatting | prints the value with `Cr`, formatting held; detail panel says "unit definition pending" | operator decision (L-15) |
| E-2 | **Canonical σ-to-expiry** — four definitions, two conventions, none in `gamma_metrics` | every distance's `σ —`; `flip_sigma`, `gap_sigma`, `corridor_width_sigma`, `dist_sigma` all held | % of spot + the **priced-move bracket**, labelled "not σ" | contract Part 3 §1; TD-S84-NEW-7 |
| E-3 | **γ ceiling / floor levels** — states emit, levels are unnamed | Overview toggle | toggle disabled | contract Part 3 §2 |
| E-4 | **Bands for every state word** — regime neutral, lead (LOCKED…), top-strike share (COMPRESSED…), term slope (normal/flat/inverted), skew (steep…), pin-risk 25/50/75 | every place a word would go | number alone; SCALE slot names the calibration gap | ADR-016; contract Part 3 §3 |
| E-5 | **True HHI** (Σ share²) — the column is max/sum | Gamma tab | label "top-strike share"; true HHI derivable from `v_gex_strike_rank.share_of_abs` if wanted | contract Part 3 §4 |
| E-6 | **Previous-close ΔOI** — scaffold only | OI tab | since-open only, labelled as such | contract Part 3 §6 |
| E-7 | **L7 vanna / L8 charm** | Flows | absent; gated on T1 (A3, A4) | capture_s84 §2.6 |
| E-8 | **L13 on SENSEX** — stale anchor | OI tab | suppressed | TD-S84-NEW-4 |
| E-9 | **Expiry class** (weekly / monthly) | S1 subtitle | omitted | — |
| E-10 | **Participant tilt (L18)** — the view carries a date and no OI | — | absent | contract §17 |
| E-11 | **`ict_zones` validity column** — outside the contract | Structure | filter by `detected_at_ts` against `ict.zone.h_valid_days` only once the column is confirmed; until then the list is labelled "validity unconfirmed" | measure the table before §H |
| E-12 | **View COMMENTs not live** on `v_gex_abs_exposure`, `v_gex_max_pain`, `v_gex_pin_maxpain` | detail panels | text from the `sql/` file, flagged | TD-S84-NEW-3 |
| E-13 | **`gamma_metrics` has no `CREATE TABLE` in `sql/`** | strip S1, S2, S7, priced move, sparklines | reads as today; recorded so the most-read table is not mistaken for governed | TD-S84-NEW-2 |
| E-14 | **Snapshot export omits** flows, ΔOI, river and the max-pain candidate rows | the prototype's Flows tab, OI ticks, OI valley, river | those stay illustrative in the canvas until a second export | S85 export prompt |
| E-15 | **ACCEL zone** (`v_gex_strike_accel_zone`, ENH-81) is on today's Positioning page and **has no place in this design** | — | not drawn; the gamma terrain shows amplifying pockets directly | operator decision (E-D7) |
| E-16 | **`index_futures_snapshots` — column names and anon readability** | S8 (R2) | cell reads "futures pending" in the prototype | measure before §H (`information_schema` + single-run role-scoped anon check) |
| E-17 | **`market_spot_snapshots` — how the 09:08 pre-open row and the first OPEN-window tick are identified; anon readability** | S9 (R3, R4) | — | measure before §H |
| E-18 | **Basis context label bands** — env deadbands, not measured (ADR-016) | S8 | label not shown | calibration gap |
| E-19 | **Previous-session reads** (VIX, basis) — the front end has no "last row of the previous trading session" query today; it must use `trading_calendar`, not "yesterday" (ADR-020) | S7, S8, C.8 | marks omitted | build in §H phase 1 |
| E-16a | **Anon path for `index_futures_snapshots` and `market_spot_session_markers`** — derived yes, not exercised | S8, S9 | — | one single-run `SET LOCAL ROLE anon` check in the SQL editor |
| E-17a | **Are the markers' `prev_close_spot`, `premarket_ref_spot`, `open_0915_spot`, `gap_open_pct` populated today and 09-30, and what does `open_0915_spot` hold?** | S9, S2 | prev close from markers; gap computed in the read layer | same editor run |
| E-22 | ~~Previous session's settled close~~ **RESOLVED S88** — the 16:00:04 `dhan_idx_i` row; see B.1a. | S2, S9, C.8 | — | — |
| E-21 | ~~Pre-open written at 09:11, not 09:08~~ **RESOLVED S88** — deliberate: the capture cron moved 09:08 → 09:11 on 2026-08-24 (`merdian_reference.json` change_log S74, `7bb1779`), i.e. after the exchange's 09:08 price fix. The 09:11 print **is** the pre-open price | S9 | print shown with its own time, labelled `pre-open` | — |
| E-20 | **Previous-session front ATM IV** — `v_iv_term_structure` is latest-run scoped, so it cannot return yesterday's value | C.8 IV mark | mark omitted | decide: a small history read on `option_chain_snapshots`, or no mark |

### E.2 Decisions owed by the operator (design)

| # | decision | proposed |
|---|---|---|
| E-D1 | Unit of `gex_cr` (E-1) | — |
| E-D2 | P5: canonical max pain | `v_gex_max_pain` (γ clock — same run as walls and pin), which also gives the valley its candidate rows on the same clock |
| E-D3 | Theme | dark (C.1); light only if the live site's light was deliberate |
| E-D4 | Legacy pin readings | keep the pin-risk score as a bare number on the Pin tab; drop "Pin Probability" (S74) |
| E-D5 | NET-LONG γ STRIKE source | `gamma_metrics.max_gamma_strike` if it matches the argmax of positive `gex_cr` on a measured sample; otherwise the client argmax. Measure first |
| E-D6 | Signal row on Marketview (ADR-019) | Context only, run-collapsed |
| E-D7 | ACCEL zone | retire from Marketview; the terrain replaces it |
| E-D8 | The corrections to the prototype in C.2: max pain in ink, not gold; selected-row label in ink-2 (contrast) | accept |

---

## F. Amendments owed to ENH-110 and ADR-017

Proposed for the S85 doc-close. None of these changes a decision about data; all change presentation contracts written in S38, before the parity layers existed.

### F.1 ENH-110

| # | ENH-110 says | amend to | why |
|---|---|---|---|
| F1 | Hero spatial chart, strike on **x** (App. A (3)) | **Ladder, strike on y**, shared by every tab | many horizontal levels read like a price ladder; study E4 |
| F2 | Left nav 76 px (App. A shell); Order, Journal in nav | **Top bar**; Order, Journal out of nav until built | A.2; L-12 |
| F3 | Bar **opacity scaled by magnitude** (App. A (3)(d)) | **length only**; opacity reserved for de-emphasis on selection | magnitude by length is readable; opacity is not |
| F4 | Green/red sign, blue spot, purple max γ, green PIN band, red ACCEL band | cool/warm temperature for sign; grey tones for side; ink spot; levels by line style; pale gold = selection only | C.2 |
| F5 | IV skew **placeholder card greyed at 0.55** | **absent until built** | ruling 9; P3 |
| F6 | Dealer flow **6-cell grid** | **one slope line** | contract §16 |
| F7 | Header: regime chip, PO3 chip, session-phase chip, gap chip, VIX, breadth, stale | strip S1–S8 (A.3); PO3 and breadth → Context; session phase cut (implicit, P1); gap → spot subtitle; regime → the sign word under Net Γ | A.3 |
| F8 | ICT zones overlay on the hero chart; confluence ring on PIN/ACCEL ∩ ICT | ICT on **Structure** only; ring there, once the detection primitive exists; options-board coincidences drawn as `≡` | ruling 2; S81 |
| F9 | Signal row always at the top when a signal exists | Context, run-collapsed (pending E-D6) | ADR-019 |
| F10 | Phase 2 IV skew widget from `gamma_call`/`gamma_put` ratio | superseded by L10 `v_iv_surface.leg_skew_98` | ENH-132 |
| F11 | Data sources list `oi_total_calls`, `oi_total_puts` | `oi_call`, `oi_put` | TD-S83-NEW-7 |
| F12 | Floating `+` journal button | out until ENH-113 | P3 |
| F13 | Anon smoke test "per table" | per view, in the **single-run role-scoped form** (`BEGIN; SET LOCAL ROLE anon; SELECT current_user, …; COMMIT;`) | capture_s84 §3(a) |
| F14 | "Old GEX dashboard becomes the hero seed" | rebuilt; nothing of the S37 hero survives | F1–F4 |

### F.2 ADR-017

| principle | amendment |
|---|---|
| **P1** three-filter | Unchanged. Applied: LIVE pill, "auto every 60s", session-phase chip removed. |
| **P2** role contract | "Three pages" → **three roles**. The Marketview role now spans four pages (Home, Board, Context, Structure); Health and Settings unchanged. |
| **P3** silence is healthy | Clarified: P3 governs **system status**. **Named data states** (`SKIPPED_EXPIRY`, `NO_CROSSING`, …) are data, not status, and always render — silently omitting them would read as a value. Market readings are **not graded** (well/mid/bad) until their bands are measured (ADR-016). |
| **P4** confluence is the headline | Scoped: the ring applies to ICT ∩ options-level overlaps on the **Structure** page, once the detection primitive exists. On the options board, same-strike coincidence is drawn as `≡` with **no** emphasis, because both bases are OI-weighted and the coincidence is partly arithmetic (S81). |
| **P5** motion replaces timestamps | Narrowed: sparklines only where ≥ 3 distinct runs exist (S81), and only where motion is itself the question (spot, net Γ today). One timestamp exception: the **clock chip**, when two clocks differ — there the time *is* the information (contract §0). |
| **P6** distance × time salience | **Still deferred** (S81: uniform weight). Partly served by the zoom model: distance becomes position, and off-window levels become chips carrying their distance. |
| **P7** keyboard | Extended per D.6. `/` now centres the ladder on a strike. |

---

## G. ADR-017 and render-contract checklist for this design

To be copied into the §H prompts as the per-phase acceptance list.

| check | how this design meets it | where |
|---|---|---|
| P1 — no implicit, redundant or systemic content | no LIVE pill, no refresh text, no session chip; one VIX; health off Marketview | A.3, C.6 |
| P2 — decisions / diagnostics / configuration separated | Home, Board, Context, Structure = decisions; Health; Settings | A.1 |
| P3 — silence is healthy | stale strip only when stale; no OK badges; empty sections collapse | C.6 |
| P4 — confluence | options board: `≡`, no emphasis; ring on Structure only when detected | C.4, A.8, F.2 |
| P5 — motion, not timestamps | spot and net-Γ-today sparklines (≥ 3 runs); clock chip only when clocks differ | A.3, B.4 |
| P6 — salience | deferred by decision; zoom and chips serve distance | D.2, F.2 |
| P7 — keyboard | D.6 keys, focus-scoped | D.6 |
| Contract §0 — two clocks | clock chip whenever γ and chain differ by > 1 cycle; OI tab named as mixed | B.5, D.5 |
| Contract §4.2 — every state vocabulary handled | `status` 4 of 4 · `corridor_state` 4 of 4 · `leg_status` 2 of 2 · `presence` 3 of 3 · `dte_bucket` 3 of 3 · `front_is_0dte` · `is_fresh` · `iv_fresh` · `session_complete` · `sigma_overstated_expiry_day` — each has a treatment in B and C.6 | B, C.6 |
| Every tile binds a real column | B; gaps named in E | B, E |
| No state word without a measured band | every band word listed as gap E-4 | E-4 |
| No placeholder for an unbuilt layer | L7, L8, L18 absent | A.6, C.6 |
| Default view sensible | Near spot formula; spot always in window | D.2 |
| Every multi-strike view zooms | one ladder component everywhere (Board, Structure) | A.5, D.2 |
| Phone: no sideways scroll | top bar, 2 × 4 strip, tabs scroll in-row, fixed ladder | A.2, D.7 |
| L-1 … L-15 not carried forward | distance sign rule (B conventions), latest-40 trajectory, units beside numbers, no unbanded words, no "probability", server skew, ICT validity, run-collapse, counts under N < 5, nav cleanup, one name for Settings, phone shell, unit held | §0.2 ↔ A, B, C |
| Anon path per view | single-run role-scoped check per view, per phase | F13; §H |

---

## H. Phased Lovable prompts

**Not written yet.** A–G are approved; §H waits only on the E-16/E-17 measurement, so that every R2–R4 binding names a real column. Planned phases (addendum §3.2): phase 1 — shell, strip, the read, Overview, Gamma, OI; phase 2 — Pin, IV; phase 3 — Flows (+ L7/L8 once built), Context, Structure. Each prompt names the files to change, the exact column bindings, the absence rules and the zoom rules, and ends with a per-view anon smoke test.

---

*parity_board_design.md — S84 draft (§0, A–C) revised S85, 2026-09-29: §A and §C rewritten to the prototype canvas; §D–G added. Nothing in this document is filed or built. The prototype runs on illustrative data until the S85 snapshot is swapped in.*
