# Parity target evaluation — Day 1 (Tue 13 Oct 2026, NIFTY 0DTE · SENSEX 2DTE)

Session S97. 7-day operator trial of the parity target (linked to the operator's broker account), 13 → 19 Oct.
The product is not named in MERIDIAN artefacts. Evidence files sit in `claude/parity_eval/` (same folder as this doc):
`00_inventory` · `01_cockpit_schema` · `02_capture_log` (every checkpoint, both boards) · `03_findings` (F1–F7, pre-open) ·
`04_author_read` · `05_delta_positioning_NIFTY_1246` (per-strike class table + method footnote) · `06_nifty_pin_scorecard`.

**Close:** NIFTY 22,722 (+1.60 %; "Nifty ends at 22,722", Business Standard). SENSEX +1,109 pts on the day (same source). Day shape:
open ~22,36x → morning high ~22,566 (10:28) → range 22,490–22,560 (10:30–13:50) → trend up 13:50–15:30 to 22,722.

---

## 1. Against the plan (the seven asks)

| # | ask | done today | status |
|---|---|---|---|
| 1 | Access via Chrome | Operator's signed-in Chrome, two tabs (target workspace + Marketview). Network payloads read once via an in-page hook at 07:46. After that, JS was blocked by auto mode for the rest of the session. All live reads are rendered (screenshot zoom + page text). | done; the export of the IndexedDB capture is still owed (needs default permission mode) |
| 2 | Read every tab / pane / drill-down | All 7 default workspaces and the 26-pane catalogue mapped (`00_inventory`). Settings and What's-new read (no changes made). Cockpit payload schema captured (`01_cockpit_schema`). | map done; **replay scrubber, pane customisation, History, Flows / Density / IV / OI drill-downs still owed** |
| 3 | How it works | GEX unit (F1, exact), flip construction (F2), HHI window (F3), pin construction (F4), D-4 classifier (F5 + today's per-strike table and footnote), aggressor method (today). | substantially done for gamma / pin / delta; Flows (charm/vanna-type panes), IV smile/term and OI tick tape not yet studied live |
| 4 | Compare calculations | 40 checkpoints × 2 indices, both boards (`02_capture_log`). Pin scorecard (`06`). SENSEX flip gap tracked 21 times. Regime sign compared at the same minute. | live comparison done for Day 1; **same-minute strike-level comparison not done** (needs the export or SQL) |
| 5 | How each treats each layer | §3 below | done for walls / flip / regime / pin / delta; IV, OI and flows owed |
| 6 | Make MERIDIAN better | §5 candidates (none proposed; each needs operator yes / prereg where ADR-009 applies) | list started |
| 7 | Presentation & rendering | Defect lists §4. Partial-load, label/ranking and freeze behaviour observed on both boards. | **formal 1440 / 800 / 390 pass still owed (Fri)** |

P7 provisional live read was done at 09:24 through the board (marked PROVISIONAL): our flow "against book" (net −26,087 since 08:30;
put flow −24,523) vs their since-open Bullish on the same put writing → **opposite sign on the same leg; this is the D-4 sign convention in one reading.**
Anchors differ (our 08:30 vs their 09:15). Still owed: L1/L3/L4 SQL from `live_read_pack_2026-10-12`.

---

## 2. Headline findings (Day 1)

**H1 — Pins: neither board forecast the 0DTE close before 15:15** (`06`). 31 paired checkpoints: same strike 12, ours closer 14, theirs
closer 5. Within ±50 of the close: 4 each, all from 15:15. Mean |pin − close|: ours 141, theirs 182. Ours looked better only because it
sat on the 22,600 call OI wall above spot through midday and the trend ended near there. That is luck of direction, not skill. n = 1 day.
- Their pin is spot-following by construction (ΔOI pressure × distance decay × time amplifier). LOCKED at 22,500 with conviction 81–93 from
  10:14 to 14:05 while spot ranged 22,490–22,566, then it stepped up behind price: 22,550 → 22,600 → 22,650 → 22,700. "LOCKED" describes
  where price is sitting. It is not a forecast.
- Ours (|γ| share, no distance term, D-5a) flipped on leads of 0.1–3 share points: 22,600 ↔ 22,500 ↔ 22,400. Leads swung 8.6 → 11.4 → 1.5
  and 17.3 → 3.1 in single runs. No hysteresis, no state on the tile.
- Their **settlement probability** (21 % → 99 %) rises whenever spot sits near the pin as τ shrinks. It hit 96 % on a frozen spot (H6).

**H2 — Their headline direction read is D-4 and it is built on the premium-change sign** (`05`). 12:46 per-strike table: calls 22,500–22,650
"long buildup", ITM calls "short cover", every put ≤22,750 "short buildup" → 99 % bullish. On an up-drifting 0DTE the call premium rises
with spot, so "long buildup" there is partly mechanical. By 15:01 the class mix had rotated: calls ≤22,600 became short cover, calls
22,650–22,750 long buildup, and the biggest move changed from put short buildup to call short cover. The verdict word never changed
(Bullish 98–100 % from 09:18 to the close). It was right on direction today, but direction was mostly decided after 13:50.

**H3 — Their own trade tape contradicted their verdict for hours.** Delta · aggressor (trade side vs mid, Δ-weighted) read **−2 % to −3 %
"sold Δ"** with **puts +7 % bought** from 12:56 to 13:06, while the classifier called every put strike written and the day 99 % bullish.
It turned to +0 / +1 % only after 15:00. Nothing on screen reconciles the two. This is the strongest live evidence today for keeping the S96-I
decline: ΔOI + premium classification ≠ who traded.

**H4 — Their Delta totals print partial refreshes.** At 15:16 the ITM call short-cover rows (22,300–22,500) printed "·" (no Δ) while
READ said 100 %. The same mechanism explains Initiated +1.93 L → +1.79 L (14:06) → +1.96 L (14:16), +1.58 L (14:51) → +1.97 L (15:01), and
the 15:40 final **+56,809** vs +1,96,825 at 15:01. **Rule: a target Delta total counts only if repeated across ≥2 reads.**

**H5 — SENSEX flip: ours higher every reading, +83 to +187 (21 readings).** At 13:28 our per-strike net γ changes sign between 72,500
(−76K) and 72,600 (+42K), a strike-axis zero of ~72,565 vs their 72,540, yet our printed repriced flip was 72,658. Hypothesis: the
gap is construction inside ENH-131's repricing (γ re-evaluated over the spot grid shifts the root up when puts dominate below). It is
not OI or units. The same bias showed on NIFTY as **same-spot regime-sign disagreements** (ours short / theirs long within 10–25 pts of their
zero-γ) at 12:50, 13:00, 13:50 and 14:16.

**H6 — Index feed pause 15:16–15:25 hit both boards; ours kept showing the stale price.** Both showed NIFTY 22,702.05 for ≥9 min while
futures moved (basis +103 → +128). Theirs resumed by 15:30 (22,721.95). **Ours showed 22,702.1 through 15:40**, with basis computed off it
(+146.7 → +158.0) and the IV tile "—". Our spot tile dropped its "LIVE hh:mm" label: an implicit stale marker, unexplained. Neither board
flagged staleness explicitly.
*Operator query, 19:10:* γ runs on 13 Oct end at **15:20 IST for both symbols** (09:45Z, 09:50Z; no 15:25 / 15:30 runs). 12 Oct's last run was also
15:20 (F7), so **the 15:20 cut-off is the schedule, not a failure.** Both last runs were priced at 22,702.1, inside the upstream pause. The
likely mechanism: after 15:20 the board falls back to the last run's spot and the live LTP never reached the tile. Still to settle with the
spot-tick table: did our live ticks resume after 15:25 (board fault) or not (ingest fault)? Separately, a 15:20 last run means **our board
has no γ read for the final 10 minutes of an expiry**. Theirs runs to 15:40.

**H7 — Walls mean different things and behave differently on a trend.** Theirs = argmax call GEX / argmin put GEX (γ-weighted, the
construction S79 rejected). They re-anchor near spot within one refresh: 22,600 / 22,500 → 22,700 / 22,600 → 22,750 / 22,700 as NIFTY ran.
Ours = ENH-120 written-OI edges. They stayed at 22,550 / 22,600 one run past the break and the board said "above call wall", which is
the correct edge read. They then moved to 22,600 / 22,700, then 22,600 / 22,800. SENSEX walls matched exactly twice (11:26, 13:46) by
different methods.

**H8 — Regime sign is noise within ±25 pts of the flip on 0DTE, on both boards.** Their net Γ flickered sign between reloads and between
panes (strip vs Strike-profile pane opposite signs ×6). Ours swung −0.15 → +0.14 of gross in one 10-min run on a 40-pt move and later
−0.24 → +0.04. A three-state read (short / at flip / long) would be honest on both.

**H9 — Units (F1, measured exact, confirmed live).** Theirs = γ·OI(shares)·S²·0.01/1e7·√(τ/5 d), τ in calendar hours to 15:40 on expiry day.
Ours = γ·OI·S²/1e7. Overnight our NIFTY net Γ rose ×2.6 on an unchanged spot (dte 1 → 0 roll); theirs +9 %. Sign and net/gross are comparable;
magnitudes are not, and the ratio changes every minute into expiry.

---

## 3. Layer by layer (Day 1 read)

| layer | parity target | MERIDIAN | live behaviour today |
|---|---|---|---|
| GEX unit | Cr per 1 % move, √(τ/5 d) normalised (F1) | γ·OI·S²/1e7, unit "definition pending" on the tile | overnight ×2.6 (ours) vs +9 % (theirs) |
| flip | zero of the net-GEX curve vs spot, every expiry incl. 0DTE (F2) | ENH-131 repriced zero; **skipped on expiry day** | SENSEX gap +83…+187, ours always higher (H5) |
| regime sign | standing book, per refresh; strip and pane can disagree | standing book per 5-min run, board one run behind | both flicker at the flip (H8); same-spot splits ×4 |
| walls | γ-weighted extremes, follow spot | written-OI edges (ENH-120) | H7 |
| pin | ΔOI pressure × distance × time; LOCKED/STABLE/SHIFTING; conviction band; settlement % | |γ| share; lead in share points; state only on the Pin tab (ENH-133), not the tile | H1 |
| concentration | HHI over fixed 72 strikes, ΔOI book | conc_hhi over every strike in the run, standing book | not compared live today |
| direction | D-4 Initiated (ΔOI × Δ signed by class from ΔOI + premium), State, Flow, aggressor tape | P7 DEX flow vs book (SAME/OPPOSITE badge); D-4 declined (S96-I) | H2, H3, H4 |
| spot / feed | resumed after the 15:16 pause | froze at 22,702.1 to ≥15:40 | H6 |
| IV | ATM IV, RV, straddle panes (not studied live) | ATM IV tile, priced move | ours 18.2 (10:37) → 5.6 (15:25) → "—" |

---

## 4. Defects

### Parity target (presentation / correctness)
1. Pin pane: header strike, ranking #1 and settlement line refresh separately. Seen SENSEX 10:2x, NIFTY 11:38 (header lags), 11:45–12:05
   (settlement lags ~25 min), SENSEX 13:15 (header leads), NIFTY 14:06. Six instances.
2. Net Γ sign: header strip vs Strike-profile pane opposite at the same minute ×6.
3. Two unlabelled "C WALL" numbers on one screen (Strike profile 22,600 vs Price × delta 22,800, 14:30).
4. Delta totals print partial refreshes; blank cells counted as read (H4).
5. Positioning verdict vs aggressor tape contradiction, unreconciled (H3).
6. No stale-spot flag; settlement % computed on a frozen spot (96 %).
7. Partial-load "n/a" walls/flip; renderer freezes (CDP screenshot timeouts) from ~12:30 on a long-lived tab.
8. SENSEX net Γ printed +185 with spot 39 below zero-γ (14:36): sign inconsistent with its own root.

### MERIDIAN (board / pipeline) — candidates, none actioned
1. **Spot tile stayed on 22,702.1 after the 15:16 pause** (H6). γ runs end at 15:20 by schedule (confirmed by query), so after 15:20 the board shows
   the last run's spot; whether live ticks resumed is still to check. **Also: no γ coverage 15:20–15:30 on expiry day** (theirs runs to 15:40).
   Candidate: extend the expiry-day schedule to 15:30.
2. Symbol switch slows to minutes as the tab ages; page unresponsive meanwhile. NIFTY unreadable 13:10–13:50. γ runs were all present
   (operator query 13:49: 15 + 15 runs, every 5 min, 108 / 171 strikes). Fault is client-side.
3. Board shows the run before last (≈5–10 min lag).
4. **Wording:** the "pocket" word follows the nearest strike's γ sign, not net Γ. "Dampening" while net short ×6, "amplifying" while net
   long ×2. **Needs operator yes before any wording change.**
5. Partial loads render "no run" / "prev close missing" instead of "loading".
6. Pin lead not a conviction measure on 0DTE; no state word on the tile (ENH-133 has it in history).
7. Basis tile uses a stale spot without saying so.

---

## 5. What MERIDIAN could take (candidates only — each needs operator yes; tests need prereg per ADR-009)
- **Stale-spot badge** on the spot tile (LTP unchanged N ticks while futures moves), and suppress basis/read-text that depend on it.
- **"At the flip" regime state** when |net| / gross < threshold, for both boards' honesty on 0DTE.
- **Pin hysteresis + state word on the tile** (minimum lead or N-run persistence before the pin moves). Measure against today's 31 pairs first.
- **Carry both GEX units** (raw and √τ-normalised) with the unit labelled; never mix (F1).
- A labelled **"γ ceiling / floor"** slot for γ-weighted walls next to our OI walls (board-design E-3). Never rename ours.
- **Do NOT adopt** a premium-sign D-4 verdict (H2–H4). If anything, the aggressor-vs-classifier divergence is the interesting object.
- Investigate the **ENH-131 repricing root offset** (H5) with both curves at one minute.

---

## 6. Owed (carry to the next sessions)
1. Operator SQL (each its own block, read-only):
   - spot ticks 15:10–15:45 NIFTY: did our feed freeze, and where (ingest vs board)?
   - ~~γ runs 15:20–15:40~~ **answered 19:10: last runs 15:15 and 15:20 IST, both symbols; none after (schedule).**
   - P7 L1 / L3 / L4 from `live_read_pack_2026-10-12`.
   - NIFTY strike OI vs theirs at one minute (the 16–34 % NIFTY OI discrepancy from F7).
   - Our SENSEX per-strike net γ + repriced curve at a minute we also have their zero-γ (H5).
2. IndexedDB export (`hwcap` on the target origin, `mvcap` on Marketview). Both persist per origin. The target hook stopped at its first
   reload (~09:1x), so it holds pre-open + the first minutes only. Needs default permission mode for one JS call.
3. Their `time_amplifier_tod` / `_expiry` intraday fit (needs the export).
4. Pre-reg candidate: their 09:20–09:45 since-open split sign vs the 09:45 → 15:15 direction (n accrues daily; today: Bullish 99–100 % → up +1.6 %).
5. Our P7 board state at 09:20 on 12 Oct (`v_dex_flow_vs_book` / cycle history).

## 7. The author (two weeks of posts, `04`)
Since 6 Oct his market posts are Delta · positioning screenshots: one word + split % + biggest move. On 12 Oct 9:20 "screaming
bearish" (−87,494 Cr, 100 %) preceded a ~210-pt fall. On 8 Oct 100 % bearish was right. On 9 Oct the two windows disagreed. Today it read
Bullish 99–100 % all day; the close was +1.6 %. Three right, one ambiguous, all n-of-one days. H3 says the tape disagreed with the word for hours.
