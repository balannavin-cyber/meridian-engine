# Parity target evaluation — Day 2 (Wed 14 Oct 2026, NIFTY 3 DTE · SENSEX 1 DTE)

Session S97, day 2 of the 7-day operator trial (13 → 19 Oct). The product is not named in MERIDIAN artefacts.
Evidence: `02_capture_log_2026-10-14.md` (full day, merged; parts `_b` … `_j` kept). Day 1: `parity_target_day1_2026-10-13.md`.
**§7 (added 15 Oct, pre-open): the author's X posts for 13–14 Oct, read against the target and our capture.**

**Close (target header, exchange prints):** NIFTY **22,622.70** (−0.44 %), SENSEX **72,782**. Day shape: no pre-open or 09:15–10:30 reads (operator
offline; session resumed 10:31) → flat range 22,683–22,737 (10:30–12:50) → drop to ~22,573 (13:00–13:25) → bounce to ~22,660 (13:56) → second
leg to ~22,606–22,628 into the close. Closing session (index held) ~15:15 → ~15:30, then a closing print.

---

## 1. Against the plan

| # | ask | done today | status |
|---|---|---|---|
| — | Owed SQL (`07_owed_sql_14Oct`) | Not run. Q1–Q5b and P7 L1/L3/L4 still owed; the per-strike OI for the F7 gap was captured from their OI chain at 11:41 (SENSEX) so the SQL has a target minute. | **owed** |
| — | Replay scrubber (pre-reg #4, 09:20–09:45 split) | Clicking the scrubber crashed the page (11:57, "Something broke on this page"). Not retried. | **not obtained** |
| 2/3 | Depth reads: Flows, Density, IV, OI | All four workspaces read live (§2 D2-9). | **done** |
| 4 | Compare calculations | 42 same- or near-same-spot flip pairs, 10 SENSEX regime splits, pins and walls every checkpoint, both indices, 10:34 → 15:40. | done for Day 2; same-minute strike-level pull still owed |
| — | SENSEX watch into 15 Oct expiry | Both pins at 73,000 from 13:2x to the close; theirs LOCKED ~2 h. | **score at Thursday's settle** |
| 7 | Presentation | Stale / closing-session behaviour of both boards documented; new defects on both (§4). | formal 1440 / 800 / 390 pass still owed (Fri) |

---

## 2. Headline findings (Day 2)

> **Verification, 15 Oct (`08_defect_verification_15Oct.md`):** checked against the target's own pane definitions, D2-1 (verdict rotation), the horizon-gamma mismatch and the signed |γ| share in D2-9, and most of D2-6 (held pin vs live ranking) are **by design**, not defects. What survives as target defects: HHI 0.000 and the null pin printed as "0" (both break their own "never zero" rule), and live tapes not loading / the replay crash. Open: the settlement-line strike, sign vs root, and the ΔOI-base jump. Findings below are kept as written for the record.

**D2-1 — H2 confirmed and sharpened: their since-open direction verdict reverses on premium drift, not on trades.** NIFTY Initiated since 09:15:
−9.1K (99 % bearish, 10:38) → −13.6K (99 %, 11:40) → **+56.8K (100 % bullish, 11:56)** → +58.5K (12:29) → **+2.3K (52 %, 12:46)** → **−48.3K (99 % bearish,
13:07)** → −52.0K (13:41) → −35.8K (15:22) → −28.2K (15:40). The first three regimes happened inside a 0.24 % spot range. The per-strike classes rotated
across the whole chain together: {calls short, puts long} → {calls long, puts short} → {both short} → back. That is the signature of a premium-sign rule
(all call premiums rise together; IV/time decay makes every premium fall together). Classified ΔOI jumped 1.75 → 9.71 Cr shares between 10:38 and 11:56.
Their aggressor tape read −1 … −4 % all day and never changed sign. After 13:00, verdict and tape agreed, because spot actually moved. After the last
trade, the total kept decaying on a held spot (−52.0K → −28.2K): the 15:40 number is a revaluation artefact, not the day's flow. **Keep D-4 declined (S96-I).**

**D2-2 — Flip gap reversed sign from Day 1: ours lower in 42/42 pairs.** NIFTY −48 … −76 (median ≈ −57); SENSEX −104 … −205 (median ≈ −130).
On Day 1 ours was higher on SENSEX 21/21 (+83 … +187). So neither construction carries a fixed bias; the offset depends on the day's book shape.
- **Ten SENSEX regime-sign splits at the same or near-same spot** (11:56, 12:12, 12:28, 13:25, 14:47, 14:56, 15:04, 15:09, 15:22, 15:40): ours long, theirs short,
  spot sitting between two roots 118–205 apart. The gap widened through the afternoon (−106 at 14:31 → −205 at 14:56).
- Against our own per-strike net γ list (strike-axis zero): on NIFTY their root sits ~0–20 above it and ours ~40–76 below; on SENSEX ours sits −57 … +98
  around it and theirs +110 … +180 above. Neither construction tracks the strike-axis crossing consistently.
- **Twice our repriced root sat between two strikes of the same sign** (NIFTY 13:56: 22,450 and 22,500 both negative; SENSEX 14:31: 72,600 and 72,700 both
  negative). The repricing moves the root off the strike-axis bracket. This is the cleanest lead for the ENH-131 investigation.

**D2-3 — Levels converged after the drop; their pins LOCKED ~2 h.** From 13:2x both boards showed NIFTY pin 22,700 and SENSEX pin 73,000, and walls
agreed most of the afternoon (NIFTY 22,700 / 22,500; SENSEX 73,000 / 72,000–72,500). Their SENSEX pin LOCKED from 13:40 to the close (conviction 82–90,
settlement 10–12 %), sitting 127–405 above spot. Ours sat on the same strike with lead rising 1.5 → 6.4. Before 13:00 neither pin meant anything: theirs
wandered with spot (SENSEX 73,200 → 73,500 → 72,800 → 72,900 → 73,500 → 72,900 → 73,200; NIFTY 22,750 → 22,950 → 22,800 → 22,750), ours stayed on the
biggest |γ| strike (23,000 / 73,500). **SENSEX is scored at Thursday's settle.** Close today vs pins: NIFTY −77, SENSEX −218.

**D2-4 — H6 explained: it is the closing session (ADR-022), plus our own 15:15 / 15:20 cut-offs.** Both indices held their last continuous value
from ~15:15 to ~15:30 on both boards (NIFTY 22,625.15 identical at 15:16 and 15:22), then printed a closing value (22,622.70; 72,782). Day 1's "feed pause"
was the same event. On our side three things stack: the 1-minute spot ends at 15:15 by design (TD-S88-NEW-1), the last γ run is 15:20 by schedule (it
reached the board ~15:30), and after 15:30 the spot tile shows the last run's spot while **the basis tile is still computed off the frozen 15:14 tile
value** (SENSEX: +240 shown vs +153 against the displayed spot). Neither board labels the closing session.

**D2-5 — Their explicit stale state.** On a ~30 s feed drop (13:56) they showed header "NO FEED", per-pane "Stale · as of 13:56 IST · not refreshed on
time", and tapes "Couldn't load … (the connection dropped)", while keeping the last levels visible. Ours drops the "LIVE hh:mm" label and says nothing.
This is the best presentation idea seen so far.

**D2-6 — Their pin pane contradicts itself.** Inconsistent in 13+ reads: the settlement line names the runner-up or the #3 candidate (wrong strike in 9 of
14 morning reads); header vs ranking #1 vs settlement name three strikes (12:29); the pin printed as its own runner-up (22,800 / 22,800, 12:45); the session
log renders a null pin as strike "0" and counts "↑ from 0" as a move. Consistent once LOCKED.

**D2-7 — Our board defects seen live.**
- **Degenerate corridor:** both ENH-120 walls on one strike, "22,700–22,700 · 0.00 % wide", with contradictory position words ("below put wall" at 11:40,
  "above call wall" at 11:56 on the same walls). Degenerate on 3 of the 5 NIFTY runs read 11:35–12:40.
- **Wall flicker by run:** NIFTY call wall 22,700 ↔ 23,000; SENSEX put wall 72,000 → 73,000 → 72,000. Close OI on two strikes alternates the argmax.
- **"SPOT ≡ FLIP" label tolerance:** printed with spot and flip 21–55 pts apart (five times), while the FLIP tile showed the gap.
- **Pocket word** follows the local strike, not net Γ ("amplifying" while net long at 13:22 and 14:31): Day-1 item 4, unchanged, still awaiting yes.
- Basis computed off a different spot than the SPOT tile shows (D2-4).

**D2-8 — Our board runs one γ run behind, and that matters on the one move of the day.** At 13:03–13:04 the board showed the 12:55 run, priced 80–233
pts from live spot; read text described a spot that no longer existed. Levels were 8–10 minutes stale through the drop. Their walls moved at 13:02; ours
by 13:15–13:20.

**D2-9 — Depth map (Flows, Density, IV, OI).**
- **Flows:** "Hedging" = their net Γ with the sign flipped (dealer trade per +1 %); the hedge ladder is linear (±2 % = 2 × ±1 %) and adds contracts only;
  per-strike ∂Δ/∂t and ∂Δ/∂σ bars (we have totals only, L7/L8). "Total gamma by horizon" (+4.1K now → +2.2K at expiry) has **no substrate on our side**
  and its "now" value does not match their own net Γ on the same screen (a third NIFTY gamma total).
- **Density:** the "Share of |γ|" pane prints signed values; HHI · by expiry covers 8 expiries, with **0.000 HHI on 9- and 3-strike expiries** (degenerate);
  HHI session series starts 10:03 while tapes start 09:47 and the pin log 09:15. Ours: conc_hhi front expiry only.
- **IV:** ATM 13.44 vs ours 13.1; rolling straddle ₹290.4 vs our "priced ±289" (same object, agree within ₹1.4); their RV is stale ("to 5 Oct"); **we have
  no RV substrate.** Smile / term per expiry render as charts only.
- **OI:** chain with ΔOI vs prev close / since open; a per-minute tick tape from 09:16 with spot − flip (SENSEX short γ every minute 09:16–11:41 by their
  construction); a wall history series per session and per minute today. **We have no wall-history view** (substrate exists per run).

---

## 3. Layer by layer — what changed from Day 1

| layer | Day 1 read | Day 2 read |
|---|---|---|
| flip | SENSEX ours higher 21/21 (+83…+187) | ours lower 42/42 (NIFTY ≈ −57, SENSEX ≈ −130); twice our root not bracketed by a strike-axis sign change |
| regime sign | splits ×4 on NIFTY within ±25 of the flip | 10 SENSEX splits at the same spot, roots 118–205 apart; NIFTY agreed all day |
| walls | theirs follow spot on a trend (H7) | H7 both ways (dip and recovery, 300–500 pts per refresh); ours flicker on near-equal OI and went degenerate on NIFTY; converged after 13:2x |
| pin | neither forecast 0DTE before 15:15 | wandering on both until 13:00; same strikes on both after; theirs LOCKED ~2 h; SENSEX scored Thu |
| direction | verdict Bullish all day; tape disagreed for hours | verdict reversed three times on a 0.24 % range; tape steady −1…−4 % |
| spot / feed | "pause" 15:16–15:25 | closing session (ADR-022) on both boards; our basis off a frozen tile; their explicit stale state |
| IV | not studied | ATM IV and straddle agree; their RV stale; ours has no RV |
| flows / density / OI | not studied | mapped (D2-9); per-strike flows, per-expiry HHI, wall history and gamma-by-horizon exist only on theirs |

---

## 4. Defects

> Reclassified 15 Oct (`08_defect_verification_15Oct.md` §1), target list below: 1 → null pin as "0" **DEFECT**; held pin vs ranking and runner-up are by design; the settlement strike is open · 2 → open (sign vs root, plausibly by design) / refresh skew · 3 → **DEFECT** · 4 → disclosed · 5 → signed share by design, HHI 0.000 **DEFECT** · 6 → by design (ΔOI book) · 7 → disclosed · 8 → **DEFECT** · 9 → by design. MERIDIAN items unchanged.

### Parity target
1. Pin pane self-contradiction (D2-6): settlement strike, header and ranking #1 disagree; pin printed as its own runner-up; null pin rendered as "0".
2. Net Γ sign inconsistent with its own root (14:54: +877 with spot 67 below zero-γ; 15:16; 15:30), and strip vs profile opposite signs.
3. SENSEX Net-delta / Price × delta tapes stuck on "Loading" at 9 checkpoints (12:28 → 15:40); NIFTY tapes "Loading" at 15:40.
4. Three session starts on one board: tapes 09:47, HHI 10:03, OI tick tape and pin log 09:15/09:16.
5. "Share of |γ|" pane prints signed shares; HHI 0.000 on 9- and 3-strike expiries.
6. "Total gamma by horizon — now" ≠ the net Γ on the same screen.
7. RV "to 5 Oct" (nine days stale) shown next to live IV.
8. Replay scrubber crashes the page.
9. Since-open Delta total keeps changing after the last trade (−35.8K → −28.2K, 15:22 → 15:40).

### MERIDIAN (board / pipeline) — candidates, none actioned
1. Degenerate corridor state and contradictory position words (D2-7).
2. Wall flicker between near-equal OI strikes (D2-7).
3. "SPOT ≡ FLIP" label tolerance up to 55 pts.
4. Pocket-word mismatch (Day-1 item 4; still awaiting yes).
5. Basis computed off the frozen tile spot, not the displayed spot (D2-4).
6. No closing-session or stale label; spot tile silently drops "LIVE" (D2-4, D2-5).
7. Board one γ run behind; 8–10 min stale on the 13:00 drop (D2-8).
8. Last γ run 15:20 every day; no levels for the closing session.

---

## 5. Candidates (none proposed — each needs operator yes; anything statistical needs a prereg per ADR-009)
- **Closing-session / stale wording and state:** from 15:15 label spot "closing session · index held"; per-tile "stale · as of hh:mm" on feed loss; suppress
  or flag basis and read text that depend on a held spot. Wording needs explicit yes.
- **Wall and pin hysteresis:** a minimum OI / share margin or N-run persistence before a wall or pin moves; a separate state for coinciding walls. Measure on
  Day 1–2 runs first.
- **Extend the γ schedule to 15:30 every day** (not only expiry).
- **Basis from one spot:** compute basis from the same spot the SPOT tile shows.
- **Pocket-word fix** (Day-1 item 4) — still awaiting yes.
- **Keep D-4 declined.** Day 2 is the strongest evidence yet (D2-1).
- Investigate ENH-131's root leaving the strike-axis bracket (D2-2) with both curves at one minute.

---

## 6. Owed
1. The `07_owed_sql_14Oct` queries (Q1–Q5b, P7 L1/L3/L4), each its own read-only block, run by the operator. Add a SENSEX per-strike OI pull at 11:40 today
   to compare with their chain read (11:41) for F7.
2. A same-minute curve pull for H5 / D2-2: our per-strike net γ plus the repriced curve at a minute where their zero-γ is logged (e.g. SENSEX 15:22: ours
   72,625, theirs 72,819, same spot 72,807).
3. **Thursday 15 Oct (SENSEX expiry):** score both boards' SENSEX pin (73,000 on both at today's close) at the settle; run the Day-1 routine on SENSEX.
4. Replay read for pre-reg #4, only if a route that does not crash the page exists.
5. Carried from Day 1: IndexedDB export; the target's time-amplifier fit; our P7 board state at 09:20 on 12 Oct.
6. **Score the author's SENSEX call at today's settle (15 Oct)** (§7): his trigger 72,500 (break → "ugly"), his expiry profit zone 71,816–73,415, his "It'll fall tomorrow" on NIFTY; against both pins at 73,000 and our long-γ regime.

---

## 7. The author's read, 13–14 Oct, against the target and our capture

Source: @AshwinBadri2, every post and reply 13 Oct 05:30 → 15 Oct 06:20 IST (X search, `since:2026-10-13`), images opened at full size.
Read 15 Oct ~06:15 IST. P&L and positions are self-reported screenshots. Product-promotion posts (trial, pricing) are listed but not analysed.
This extends `04_author_read.md` (29 Sep → 12 Oct).

### 7.1 What he posted

| time (IST) | post (his words, condensed) | image (read at full size) |
|---|---|---|
| **13 Oct 10:56** | NIFTY put OI build-up "looked massive"; net put − call ΔOI peaked 227M, now 170M as spot slips to 22,500; "22,500 is the level to watch" | OI tick tape 10:48: flip **22,525** (spot − flip −14), walls 22,600 / 22,500, PCR ΔOI 6.98, net peaked +237.9M at 10:20; tape starts 09:16 |
| 13 Oct 11:07 | quotes the brand account's 11 AM thread: 22,500 biggest positioning cluster (+35.4M sh); time-decay greek most negative at 22,400 (−13,205 Cr); IV-sensitivity greek peaks at 22,600; "the numbers don't predict the future" | Flows · by strike ×3, 11:02: net positioning +225.3M sh, net ∂Δ/∂t −67.01K Cr, net ∂Δ/∂σ +3.83K Cr |
| 13 Oct 12:51 | "connect the target with Claude and tell Claude to read today's positioning" | an AI-written read: NIFTY 22,539, "stuck in a box 22,500–22,600", **"I expect it to hover near 22,500 until expiry"**, 22,600 the ceiling, gamma break-even 22,528, "if it stays between 22,500 and 22,600, expect a quiet drift toward 22,500 by the close" |
| 13 Oct 13:21 | NIFTY 22,541 at 13:17: new option delta **99 % bullish (+1.9 L Cr)**, mostly put writing (+97.7K Cr); walls 22,500 / 22,600, "both moved up 200 since the open"; thin cushion +1–1.5K, flip 22,536 | Delta · positioning 13:17: Initiated +1,88,384 Cr, 99 %; Strike profile, walls series, Price × gamma, Unusual volume |
| 13 Oct 13:41 | "last hour (12:36–13:35) is churn": net ΔOI flat ~+159M, PCR ΔOI 4.4, spot 22,530–22,555; 22,350–22,450 calls short-covering at 51–65× OI; 22,500 put the busiest strike (written); calls 22,650–22,800 being written ("cap") | tick tape + unusual volume 13:35: flip 22,534 (+7), walls 22,600 / 22,500 |
| **13 Oct 14:06** | **"The stage is set for a massive call explosion!!!"** | tick tape + unusual volume 14:03: spot 22,560, flip 22,551 (+9), walls **22,600 / 22,550**, PCR ΔOI 4.98; **his NIFTY position**: MTM +₹98.3 L at 22,567, margin ₹22.91 Cr, max loss −₹5.79 Cr, POP 91.6 %, Δ +293.65, Γ −13.25 (short γ), Θ +₹34.9 L; breakevens 20,984 / 22,432 / 22,792 / 23,247 |
| 13 Oct (replies) | "I didn't predict. I just read the positioning better with better tools!"; trial links | — |
| 14 Oct | **no NIFTY post during market hours** | — |
| **14 Oct 15:10** | SENSEX: Initiated **−42,204 Cr bearish**, call short build-up doing the lifting; front-expiry γ **−3.47K**, spot below the flip at **72,818**; "the catch: whole-book gamma is still positive at **+2.56K**", IV and straddle bleeding; **"72,500 — if that breaks with bearish positioning still building, things could get ugly; if it holds and the flip is reclaimed, the bearish thesis needs a rethink"** | 7-pane workspace 15:05–15:07 (§7.3) |
| **14 Oct 15:11** | "80 % of my margin is used for a massive profit tomorrow. Will look to exit before 9:30 am due to an obvious margin call!" | **SENSEX position** at spot 72,762: MTM +₹13.58 L, margin ₹21.84 Cr, max loss −₹9.69 Cr (−44 %), POP 74.6 %, Δ +146.83, Γ −0.97, Θ +₹45.2 L; breakevens **71,816 / 73,415** / 76,216; expiry P&L at spot +₹52.0 L; expiry payoff peaks **below** spot (between the −2σ and −1σ marks) and falls to zero at 73,415 |
| 14 Oct ~17:00 | (reply) "Bought next week Put option!" | — |
| 14 Oct 20:17 | (reply) "the data clearly indicated bearish positions created. Any upmove will not sustain … IV crush + [time decay]. Lower opening is also fine due to max profit on lower side" | — |
| 14 Oct ~20:30 | (reply, to "what if it gaps against you before 9:30?") "Book loss!" | — |
| 14 Oct ~23:00 | "WOW" + the pricing page (₹141/day on 6 months, 7-day free trial) | promotion |
| 15 Oct ~01:20 | (reply, on GIFT Nifty holding up) **"It'll fall tomorrow!"** | — |

### 7.2 Day 1 (13 Oct) — his read against what happened (close 22,722, +1.6 %)
- **Morning, 22,500 as the level (10:56, 11:07): right.** 22,500 held as the floor all session. His 10:48 image (flip 22,525, walls 22,600 / 22,500) matches our Day-1 capture of their board.
- **Midday AI read (12:51), "hover near 22,500, quiet drift toward 22,500 by the close": wrong.** NIFTY broke the 22,600 "ceiling" from 13:50 and closed 222 above 22,500. This is the reading their pin pane gave (LOCKED 22,500, 10:14–14:05, Day-1 H1) restated in plain words. It shows what a connected AI repeats: the target's own state words, including a pin that did not hold.
- **Direction (13:21, 99 % bullish): right on the day.** This is the D-4 verdict Day-1 H2 described: Bullish 98–100 % from 09:18 to the close, with their own aggressor tape at −2…−3 % until 15:00 (H3).
- **"Massive call explosion" (14:06): right, but after the move started.** Our log puts the trend start at 13:50; he posted at 22,560, and NIFTY ran another ~160 to 22,722. His own 14:03 image shows the walls already stepping up (22,600 / 22,550). It describes a move under way, not a forecast.
- **His position made money because it was a short-γ premium sale that the close stayed inside** (breakevens 22,432–22,792; close 22,722). Θ +₹34.9 L against Δ +294: the book was mostly time decay with a bullish tilt.

### 7.3 Day 2 (14 Oct) — his SENSEX read against the target's panes and our board
His only Day-2 market read is SENSEX at 15:05–15:10. It stands on three numbers from the target. Each is a place where our Day-2 log disagrees with the target or finds it unreliable:
1. **"Initiated delta bearish −42,204 Cr, call short build-up" (83 % bearish; read 100 % of 4.74 Cr shares).** This is the D-4 verdict (D2-1). We did not capture the SENSEX Delta pane live, so we cannot show it flipping on SENSEX. But it is the same mechanism that flipped the NIFTY verdict three times on a 0.24 % range. On a 1-DTE book where, in his own image, ATM IV fell **−2.57 pts** and the straddle **−₹150.5** since the open, falling premiums on rising OI print as "short build-up" on both sides whoever traded. His screen shows no aggressor tape.
2. **"Front-expiry γ negative, spot below the flip at 72,818."** This is the target's root. At the same minute (our 15:09 capture) our flip was **72,659**, with spot ~100 above it and net Γ **long +0.14**. That was the eighth of the **ten same-spot SENSEX regime splits** we logged on Day 2 (D2-2). **The "short gamma" leg of his thesis is the exact point where the two boards disagreed all afternoon.** His own image has two roots on one screen: 72,818 in Cumulative net gamma and 72,831 in Price × gamma (spot 72,752, net GEX at spot −3K).
3. **"Whole-book gamma still positive at +2.56K." The image does not support this reading.** The right-hand Cumulative net gamma pane is in **"Off open"** mode with "Front expiry" on. Its header reads **"SINCE FIRST TICK +2.56K Cr · NET GAMMA NOW 15:07 −3.47K Cr"**. +2.56K is the change in front-expiry net gamma since the first tick, not a whole-book level. "BOOK: WHOLE BOOK" on both panes names the OI book (standing vs session), not the expiry scope. On his own screen the level is −3.47K. *(Probable misread, made easy by the pane's labels: a presentation lesson for any "since open vs level" toggle, ours included.)*

What his screen also shows (adds to D2-9):
- **Total gamma by horizon, SENSEX:** now **+9.3K** → +6h +8.4K → +12h +7.0K → **+24h −4.2K** → expiry +2.8K. The "now" value has the opposite sign to the net −3.47K on the same screen, and the series flips sign and back. This is the same "third gamma total" defect seen on NIFTY, here with a sign conflict.
- **Flows · net by greek:** SENSEX positioning +43.8M sh, ∂Δ/∂t −51.57K, ∂Δ/∂σ +3.81K, hedging **+3.65K** (= −front-expiry net Γ, as in D2-9).
- **IV:** ATM IV 16.77 vs ours 15.1–15.3 at 15:09–15:16; straddle **₹515.7** vs our "priced ±519–527". The straddle agrees within ₹4–11; the IV level does not. RV20D 11.35 % still "to 5 Oct" (stale).
- **Unusual volume:** 73,100 PE vol ÷ OI **133.9** ("long build-up"). We logged 122 at 14:41.

**What he left out.** The target's own Pin pane had SENSEX **73,000 LOCKED** from 13:40 (conviction 85–90, 127–405 above spot), and our board agreed on the strike. His bearish post does not mention it. **His position is in fact a premium sale** whose expiry profit zone, 71,816–73,415, contains both pins. Most of the "massive profit tomorrow" is Θ (+₹45.2 L/day). The bearish view is the tilt (payoff peak below spot), not the engine. The 72,500 trigger he set was not hit on 14 Oct (low ~72,646 at 13:25, before the post; close 72,782). His "flip reclaimed" condition was also not met: spot ended 46 below their 72,828.

### 7.4 What this means for the evaluation
- **His published signal on Day 2 is the D-4 verdict plus the target's flip sign.** Day 2 found these to be the two least stable objects: the verdict reverses on premium drift (D2-1), and the target's flip sat 104–205 above ours with ten sign splits (D2-2). Today's SENSEX settle scores both at once: his bearish tilt and the target's short-γ regime, against our long regime and both boards' 73,000 pin.
- **Day-1 lesson, repeated in kind:** he states levels the target already shows (walls, flip, pin) and reads direction from the Delta verdict. The AI read he promoted restated the pin state, which was wrong on Day 1.
- **Pre-reg #4 (09:20–09:45 split → day direction):** no post in that window on 13 or 14 Oct; nothing to add to n.
- **Scorecard to fill after today's settle (15 Oct):**

| call | made | test | result |
|---|---|---|---|
| SENSEX bearish; 72,500 break → "ugly" | 14 Oct 15:10 | did SENSEX trade below 72,500 on 15 Oct? | _owed_ |
| SENSEX position profit zone 71,816–73,415 | 14 Oct 15:11 | settle inside? (he said he'd exit before 09:30) | _owed_ |
| "It'll fall tomorrow" (NIFTY) | 15 Oct ~01:20 | NIFTY 15 Oct close vs 14 Oct close 22,622.70 | _owed_ |
| Target SENSEX pin 73,000 LOCKED / ours 73,000 | 14 Oct close | \|settle − 73,000\| | _owed_ |
| Regime: target short (flip 72,828) vs ours long (flip 72,714) | 14 Oct close | direction and range of 15 Oct | _owed_ |
