# Defect verification — defect, or how the parity target is defined? (15 Oct, pre-open; **updated 15 Oct post-close and 16 Oct post-close with the live checks**)

Operator question (15 Oct 06:31): are the target "defects" from Day 1–2 real, or are they the target's definitions working as designed?
The target is a **positioning platform, not a predictive one**. Reads that "played out" on a tiny sample are not the test, and neither are reads that "failed to predict".

**Method.** Every finding in `parity_target_day1_2026-10-13.md` §4, `parity_target_day2_2026-10-14.md` §2/§4 and §7 was checked against the target's **own stated
definitions**, read 15 Oct 06:35–06:50 IST, read-only, from the pane footers of every default workspace (Terminal, Flows, Density, Pin, Delta, IV) and the
What's-new entries already logged in `00_inventory`. Verbatim footer phrases are quoted where they decide the case.
**Post-close update (15 Oct 15:45 IST):** rows #4, #5, #8, #16, #23 updated from that day's live checks (`02_capture_log_2026-10-15.md`); new rows #25–#27; tally and §5 added.
**Post-close update (16 Oct 15:50 IST):** rows #4, #8, #9, #16, #19, #22, #23, #25, #26, #27 updated from Day 4 (`02_capture_log_2026-10-16.md`, sent in chat;
report `parity_target_day4_2026-10-16.md`); new rows #28–#29; tally, §4 and §5 updated. #13 and #17 were not re-checked on 16 Oct.

Verdicts:
- **BY DESIGN**: the behaviour follows from a stated definition. Not a defect; at most a labelling note.
- **DISCLOSED**: a real data limit, but the screen says so.
- **DEFECT**: inconsistent on screen whatever the definition, or breaks the target's own stated rule.
- **OPEN**: no stated definition found; needs a live check.

---

## 1. Verdict table (target)

| # | finding (where logged) | target's own definition (footer, quoted) | verdict |
|---|---|---|---|
| 1 | Since-open direction verdict reverses three times on a 0.24 % range; per-strike classes rotate together (D2-1, Day-1 H2) | Delta · positioning: "INITIATED: ΔOI × delta signed by the class each leg was read as, **from ΔOI and the premium move** … A read from ΔOI and price, **not from trades**" · "A read of OI and premium changes, not advice" | **BY DESIGN.** A premium-sign classifier *must* re-class every leg when premiums move together (spot, IV or decay). The rotation is the definition working. *16 Oct: Bearish 98–100 % 09:20–09:45 on both indices, Bullish from ~10:00 to the close (89–100 %).* |
| 2 | Verdict contradicts their own aggressor tape for hours (Day-1 H3; Day 2 morning) | Aggressor: "counted as bought when the later tick's last trade is above its bid/ask midpoint … Δ balance weights each leg's volume by its delta" | **BY DESIGN.** Two different objects. *15 Oct: SENSEX disagree 33 / flat 8 / agree 6; NIFTY agree 25/25. 16 Oct: NIFTY agree 3 / disagree 15 / flat 2; SENSEX agree 3 / disagree 2 / flat 13 / n/a 1.* |
| 3 | Since-open total keeps changing after the last trade (Day 1; 15 Oct +1,92,390 → +84,051) | Initiated = "ΔOI × delta"; "Cr of delta-notional (Δ × OI in shares × spot)" | **BY DESIGN.** A mark, not a flow count. *16 Oct NIFTY +90,900 (15:14) → +57,668 (15:40).* |
| 4 | Classified ΔOI base jumps 1.75 → 9.71 Cr shares (D2-1) | READ = "share of \|ΔOI\| the engine could classify" | **BY DESIGN** (closed 16 Oct). 15 Oct: the one jump coincided with READ 63 % → 99 %. 16 Oct: READ 94–100 % all day; base grew 2.4–2.5× 09:20 → 09:30 with READ flat at the open (accumulation), then smooth; no > 2× jump later. |
| 5 | Delta totals print partial refreshes; "·" rows while READ 100 % (Day-1 H4) | "·" = no class read; READ is a share of \|ΔOI\| | **PARTLY BY DESIGN.** Unchanged. |
| 6 | Walls jump 300–500 pts per refresh, follow spot (Day-1 H7, Day 2) | Price × delta: "walls are the **gamma** call and put walls" | **BY DESIGN.** *16 Oct: NIFTY call wall moved 12 times between 23,000 and 23,200, put wall 6 times.* |
| 7 | Flip 104–205 pts from ours; regime splits (D2-2, Day-1 H5) | Price × gamma: "the engine's zero-gamma scan … zero gamma = its root nearest spot" | **BY DESIGN on their side** (construction). *NIFTY pairs 104/104 ours lower (cumulative); 16 Oct splits SENSEX 4, NIFTY 19, almost all with spot between the roots.* Which root is closer to the dealer book stays **OPEN** (curve pull, owed). |
| 8 | Net Γ sign inconsistent with its own root (Day-1 defect 8; D2) | "zero gamma = its root **nearest spot**" | **OPEN, plausibly by design.** 16 Oct: eight same-screen profile-vs-strip sign splits (09:17 +2.3K / −1.99K outside ±1K; 13:47 +1.4K / −1.87K; 14:55 +760 / −1.93K; 15:40 SENSEX +273 / −73.48 …), all with spot within ~22 pts of the root; zero-γ vs profile FLIP 1–13 pts apart on the same screen. No multi-root case captured (Peak/Trough not opened). |
| 9 | Header strip net Γ vs Strike-profile / Price × gamma net, opposite signs (Day-1 defect 2) | strip "NET Γ front expiry · Cr"; profile "front expiry, standing OI" | **Refresh skew, low severity**, but 16 Oct shows splits up to ~2K (09:17) and the "SINCE YOUR LAST VISIT" status word ("Turned negative" / "Stayed positive") follows the strip, flipping ≥ 17 times on noise. Presentation note. |
| 10 | "Total gamma by horizon — now" ≠ net Γ on the same screen (D2-9) | Flows: "… **over classified ΔOI**" | **BY DESIGN.** **Withdrawn.** |
| 11 | "Hedging" = −net Γ; hedge ladder linear (D2-9) | "potential hedging flow … at current gamma, linear" | **BY DESIGN** (stated). |
| 12 | "Share of \|γ\|" prints signed values (D2-9) | Density: "Share of \|γ\| by strike, **signed** …" | **BY DESIGN** (stated). **Withdrawn.** |
| 13 | HHI 0.000 on 9-, 25- and 3-strike expiries (D2-9) | Flows: "**n/a is no reading, never zero**" | **DEFECT by their own rule.** (Not re-checked 15 or 16 Oct.) |
| 14 | Pin header strike ≠ ranking #1 (Day-1 defect 1; D2-6) | "#n = the strike's rank among the engine's top five **now**"; pin = held state | **BY DESIGN.** Withdrawn. *16 Oct 09:55: the held pin 22,950 was outside its own top-5 (pressure 19 %) — the extreme of the same rule; logged under #26.* |
| 15 | Pin printed as its own runner-up (12:45) | runner-up = "margin over the runner-up" | **Presentation flaw, explained by #14.** *16 Oct: on exact ties the RUNNER-UP field is simply omitted (10:06).* |
| 16 | Settlement line names a strike that is neither pin nor runner-up | no definition on the pane | **BY DESIGN (undisclosed; presentation note).** Computed on the strike with the **largest Γ ΔOI**. Held at every read: **SENSEX 91/91, NIFTY 84/84** (15 + 16 Oct). Decoupled reads 16 Oct: NIFTY 09:36, 09:55, 10:25; SENSEX 10:16 and **15:40 (final): PIN 74,500 / "SETTLEMENT 6 % within ±100 of 74,000"**. |
| 17 | Null pin rendered as strike "0" (D2-6) | "n/a is no reading, never zero" | **DEFECT by their own rule.** (Not re-seen 15 or 16 Oct.) |
| 18 | LOCKED pin did not hold (Day 1) | SETTLEMENT is the only forward number | **BY DESIGN (descriptive).** Score the settlement % (15 Oct SENSEX: 2/49 inside, both after the print). 16 Oct NIFTY: 49 readings logged, final 23,100 at 17 % (±50); scored 19 Oct. |
| 19 | SENSEX tape panes stuck on "Loading" (D2); replay scrubber crashed the page | — | **DEFECT** (availability). 16 Oct: **six** "Loading SENSEX session tape…" (13:06, 13:28, 14:06, 14:47, 15:31, 15:40) + 09:20 aggressor "Loading SENSEX order flow…"; at 14:47 a Strike-profile pane **without a clock** showed the 14:26 NET GEX −189 beside "FLIP n/a · C WALL n/a · P WALL n/a". |
| 20 | RV "to 5 Oct" (D2-9) | "dotted when stale or thin" | **DISCLOSED.** |
| 21 | Three session starts (D2) | "since 09:47 IST" printed | **DISCLOSED.** |
| 22 | Stale / NO FEED state (Day 1 "no stale flag") | per-pane "Stale · as of hh:mm"; header "NO FEED" | **Day-1 item withdrawn.** 15 Oct: "CLOSED" from 15:30. **16 Oct: "LIVE FEED" at 15:31 and 15:36; "● CLOSED" first at 15:40**, with the "Market closed … Add Review workspace" banner; Delta wording turns date-specific ("16 Oct since open"). Hidden-tab staleness still shows no badge (10:36). See #29. |
| 23 | Two unlabelled "C WALL" numbers (Day-1 defect 3) | both panes: gamma walls of "the current book" | **Consistent 15 + 16 Oct → presentation / refresh, low.** Agreed at every readable minute on both days. |
| 24 | Author's "whole-book gamma +2.56K" (§7.3) | "Net gamma change since the session's first tick" | **Not a target defect.** |
| **25** | **Session log rewrites closed rows** (15 Oct ~20 instances incl. values; 16 Oct **108 rank-tag rewrites, 0 value rewrites**) | Pin · session log: "**One row per 15-minute pin reading** … each held until the next"; "#n = rank … **now**" | **DEFECT by their own rule (high).** 16 Oct narrows it: no closed row changed pin, state, margin, conviction, spot or held all day; the "#n" tag is the row-pin's rank in the **current** table and is recomputed on every refresh (24 NIFTY and 25 SENSEX rows re-tagged in one step after the post-close pin moves). The Day-3 value changes still stand. A tag tells nothing about the reading's own time. |
| **26** | **Back-dated / post-close pin changes; withdrawn moves; copy-forward** | same footer | **DEFECT (same family).** 16 Oct: back-dated 3 (NIFTY ↓22,900 stamped 09:30; **NIFTY ↑23,100 and SENSEX ↑74,500 both made after the close (~15:33, ~15:39) and stamped 15:30**); withdrawn 3; copy-forward 1 (NIFTY 09:45 ← 10:00); held pin outside its own top-5 (09:55). Two days of two: the final pin is decided after the close on OI alone. Live rows also carry the **last** reading in their window, spot included (NIFTY "15:15 · 23,146"). |
| **27** | Path markers missing for some moves | path: "↑↓ = the pin moved" | **Presentation inconsistency, low.** 16 Oct: missing for 09:31, 09:55, 10:15 (both indices); the post-close markers were drawn (with the 15:30 stamp). |
| **28** | **"held" has three meanings and resets without a state change** (16 Oct) | header "held"; row "Held"; per-strike "Held" column | **DEFECT (wording), low.** Header = time in state; row = time on strike; per-strike column showed "23,000 held 1h 00m" while the pin was 22,900. Header reset with no change at 10:10, 10:16, ~13:37; the post-close 15:30 row read "held 10m" at 15:36. |
| **29** | **No cue for the closing session; "LIVE FEED" past the close** (16 Oct) | header "LIVE FEED" / "CLOSED" | **Presentation, medium.** NIFTY held 23,119.00 from ~15:14 to 15:30 (ADR-022) with "LIVE FEED" and no held-value cue; the close (23,146.15) printed by 15:31 but "CLOSED" came only at 15:40. |

### Correction to F3
Density footer: "HHI, CALL HHI and PUT HHI: concentration over the **21 strikes nearest spot** only". The HHI window is 21 strikes, not 72.

---

## 2. Tally (post-close 16 Oct)

| verdict | count | items |
|---|---|---|
| BY DESIGN | 13 | 1, 2, 3, **4 (closed)**, 6, 7 (their side), 10, 11, 12, 14, 16, 18, + 24 (author) |
| DISCLOSED | 2 | 20, 21 |
| Presentation / refresh, low–medium | 5 | 9, 15, 23, 27, **29** |
| **DEFECT** | **6** | **13** (HHI 0.000), **17** (null pin as 0), **19** (tapes not loading; stale clock-less pane), **25** (log tags recomputed; Day-3 values), **26** (back-dated / post-close / withdrawn / copy-forward), **28** (held wording) |
| OPEN | 2 | 5 (Day-1 swings), 8 |
| withdrawn | 1 | 22 |

**The operator's instinct still holds for the reads:** verdict, aggressor disagreement, post-close drift, walls, held pin and the settlement strike follow from
definitions. **The real defects are in the record and the availability:** the log does not keep the rank or (Day 3) the values it showed; the final pin is set
after the close and stamped 15:30; SENSEX tapes fail to load several times a day.

---

## 3. What this changes in the evaluation

1. Reframe D2-1 / Day-1 H2–H3 from "defect" to "property". Unchanged.
2. **"The reads played out" needs one caution.** Pre-reg #4 is the non-circular test: 13 Oct right (informal), 15 Oct 2/2 right, **16 Oct 0/2 (both 09:45 Bearish,
   both indices rose)**. 3 right / 2 wrong; n too small.
3. **Score the target's forward numbers, not its states.** Settlement % = argmax-Γ ΔOI strike (91/91, 84/84). NIFTY 19 Oct: 49 readings ready to score.
4. The flip / regime split stays a construction difference (NIFTY 104/104 ours lower).
5. **Our board's close handling is confirmed on a non-expiry day:** "LIVE" on a held value, γ run stops 15:20, no stale strip, the close never shown (16 Oct: 27 pts NIFTY).
6. **Do not use the target's session log as ground truth** for any back-test, and do not read its "#n" tags as historical ranks.

---

## 4. Live checks — done
- **15 Oct:** #16 resolved; #8 one crossing; #4/#5 evidence; #23 consistent; SENSEX Delta live.
- **16 Oct:** #25 diffed every round (108 tag rewrites, 0 value rewrites); #26 three back-dated moves incl. two post-close; #16 held 58/58 + 66/66; #8 eight
  same-screen splits at the root (still OPEN); #4 closed; #23 consistent; #19 six recurrences.

## 5. Checks for 19 Oct (NIFTY expiry)
- Settlement %: score the 16 Oct NIFTY log (49 readings) and log every 19 Oct reading against the settle.
- #25/#26: capture the full log at 15:30, 15:35 and 15:40 (post-close moves on expiry).
- #8: open Price × gamma Peak / Trough / 0-cross at one same-screen split.
- #13 / #17: re-check HHI on short far expiries and any null pin.
- #29: note when "CLOSED" appears and whether the close prints before it.
