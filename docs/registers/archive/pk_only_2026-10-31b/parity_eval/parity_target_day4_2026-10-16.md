# Parity target evaluation, Day 4 — Fri 16 Oct 2026 (no expiry; NIFTY front 19 Oct, SENSEX front 22 Oct)

Source: `02_capture_log_2026-10-16.md` (merged parts A–H; 08:38 → 15:43 IST, 47 rounds; NIFTY every round, SENSEX in FULL rounds). The merged log is 141 KB and was sent in
chat (project space); this report quotes it. Verdict labels as in `08_defect_verification_15Oct.md`: **BY DESIGN / DISCLOSED / DEFECT / OPEN**, plus **usefulness**
and **presentation**. Units: target GEX K Cr, ours L Cr — signs and net/gross only.

**Day in one line:** a quiet up day (NIFTY 22,997.35 → **23,146.15**, +0.65 %; SENSEX → **~74,729**, target's print, official close owed). Both 09:45 Bearish verdicts
pointed the wrong way (pre-reg #4: 0/2); the target's NIFTY pin sat on 23,000 for 5 h 15 m (LOCKED from 12:00) and then **moved after the close, stamped 15:30**,
on both indices; the session log re-tagged 108 closed rows (0 value changes); our board again never showed the close.

---

## §1 Against the plan (starter §5)

| plan item | done? | note |
|---|---|---|
| Pre-open: docs, author's X, both boards | yes | 08:38. Author: one product reply (~16:50 15 Oct), no market call. Our SPOT showed the 15 Oct close 22,997.4 pre-open (never shown live on Day 3). |
| Pre-reg #4 (09:20 / 09:30 / 09:45) | yes, exact minutes | 09:20 SENSEX aggressor unreadable ("Loading SENSEX order flow…"). 15:15 column filled. |
| Cadence 5 → 10 → 5 min, FULL/LIGHT alternating | yes | 47 rounds. **12:45 skipped** (Marketview tab went 0×0 after a Chrome reconnect; replaced 12:57). One late fire (11:50 counted as 11:45). |
| Presentation pass | **partly** | Pass A 12:25 (Marketview at 800/390 px via iframes; `resize_window` is a silent no-op on the maximised window), Pass B 12:55 (explain-a-number, states). **Target at narrow widths not tested** (operator's call). Closed state seen 15:40. See §8. |
| #25 diff, #8, #13/#17, settlement-% log | #25, #8, settlement yes; **#13/#17 not re-checked** | See §2. |
| Closing 15:00–15:40, both boards | yes | 15:00, 15:05, 15:10 F, 15:15 F, 15:20, 15:25, 15:31 print, 15:36, 15:40 F. |
| Post-close full Pin logs + diff | yes | Every closed row diffed round by round all day; final logs read at 15:40. |

---

## §2 Findings

**D4-1 · Pre-reg #4: both 09:45 Bearish verdicts were the wrong direction. — usefulness.**
- Early window: NIFTY Bearish 100 % / 100 % / 100 %; SENSEX Bearish 98 % / 99 % / 100 % (09:20 / 09:30 / 09:45). Aggressor: NIFTY disagree; SENSEX n/a at 09:20.
- 09:45 → 15:15: NIFTY 22,966.25 → 23,119.00 (+152.75); SENSEX 74,192 → 74,674 (+482). **0/2.** Both verdicts flipped to Bullish ~10:00 and stayed Bullish
  89–100 % to the close (restating the day, as on Day 3).
- Cumulative pre-reg #4: 13 Oct NIFTY right (informal), 15 Oct 2/2 right, 16 Oct 0/2 → **3 right / 2 wrong**. No inference at this n.

**D4-2 · The session log re-tags closed rows on every ranking change; 108 rank-tag rewrites, 0 value rewrites. — DEFECT (#25, narrowed).**
- Two clean diffs ≥ 30 min apart were taken many times over: **no closed row changed pin, state, margin, conviction, spot or held today.** Every change was the
  "#n" tag. The SENSEX 09:15/09:30/09:45 tags flipped nine times (none→#4→none→#5→#4→none→#4→none→#4→#1).
- Post-close the pin moves (D4-3) re-tagged 24 NIFTY rows (#1→#2) and 25 SENSEX rows in one refresh each. So the tag is the row-pin's rank in the **current**
  pressure table, not the rank at the reading — a reader of "12:00 23,000 #2" learns nothing about 12:00.
- Narrows Day 3's #25: Day 3 also saw value changes on closed rows (12:00 LOCKED→STABLE, 15:15 three pins); today none. Keep #25 as DEFECT (tags + Day-3 values).

**D4-3 · Back-dated moves, three today, two of them after the close. — DEFECT (#26).**
- NIFTY ↓22,900 stamped 09:30 (live 09:31 still showed 23,100). Withdrawn by 09:40.
- **NIFTY ↑23,100 stamped 15:30**: live 15:31 = 23,000 SHIFTING 3 % 45; at 15:36 the header read 23,100 STABLE "held 3m" (move ~15:33); the 15:30 row was rewritten
  to "23,100 ↑ from 23,000 STABLE 35 %", path marker "↑ 23,100 · 15:30". Final 15:40: STABLE 72, margin 43 %, settlement 17 %.
- **SENSEX ↑74,500 stamped 15:30**: live 15:31 = 74,000 LOCKED 22 % 81; 15:40 header 74,500 SHIFTING "held 1m" (move ~15:39); 15:30 row rewritten likewise.
- Inside the newest row's window, so "held until the next" allows the change; the 15:30 stamp on a post-close move does not. Same as Day 3 (SENSEX 15:30 row
  changed 15:32 → 15:40). **Two days of two: the target's final pin is decided after the close, on OI alone.**
- Also: withdrawn moves 3 (NIFTY 22,900; NIFTY 22,950 at 09:55, shown outside its own top-5; SENSEX 75,000 10:12–10:19); copy-forward 1 (NIFTY 09:45 ← 10:00).

**D4-4 · Live-row semantics: a row shows the last reading in its window, including its spot. — BY DESIGN (presentation note).**
- NIFTY 15:15 row: LOCKED 38 % / 35 % / 20 % at spot 23,119 (15:17–15:25 reads) → final **SHIFTING 6 % 42 at 23,146** (the ~15:29 reading after the close print).
  SENSEX 15:15: 48 %/87/74,674 → 28 %/82/74,729. Big drifts inside windows (SENSEX 14:45 margin +18 pts).
- So "15:15 · 23,146" is not the 15:15 spot. Pre-reg #4 used the Terminal spot at 15:14 (23,119.00) and the row spot only where they agree.

**D4-5 · Settlement = argmax Γ ΔOI held all day; one post-close decoupling with the pin. — BY DESIGN (#16).**
- **SENSEX 58/58, NIFTY 66/66** (cumulative with Day 3: 91/91 and 84/84). Decoupled reads today: NIFTY 09:36, 09:55, 10:25; SENSEX 10:16 and **15:40: PIN 74,500
  but "SETTLEMENT 6 % within ±100 of 74,000"** (Γ ΔOI 564 vs 521). The final post-close state of the pane is about two different strikes.

**D4-6 · NIFTY settlement-% log for Monday's calibration (49 readings). — usefulness (pending 19 Oct).**
- 10–17 %; 23,100 (09:16, 09:31), 22,900 (10:06–10:25), 23,000 (all else to 15:31), **23,100 at 17 % post-close** (final). = pin except 09:36, 09:55, 10:25.
  Table: counters appendix of the merged log; to be scored against the 19 Oct settle.

**D4-7 · Closing session (ADR-022): both boards held 23,119.00 from ~15:14; the target printed the close, ours did not. — BY DESIGN (both) / our DEFECT (D2-4, D3-9) confirmed on a non-expiry day.**
- Target: 23,119.00 at 15:14, 15:16, 15:20, 15:25; **23,146.15 at 15:31**; header still "LIVE FEED" at 15:31 and 15:36; **"● CLOSED" first at 15:40** (Day 3: CLOSED
  at 15:30) with the banner "Market closed. The session laid out: …" + "Add Review workspace / Not today" (untouched). Delta wording turns date-specific
  ("16 Oct since open"). No pane says the 15:15–15:30 value is held.
- Ours: SPOT "LIVE 15:15" still at 15:20 (stale "LIVE" label ~10 min), plain "SPOT" from 15:25, **23,119.0 / 74,674.3 through 15:40** (−27.15 / ~−55 vs the
  target's print); the γ run stopped at 15:20 (CLOCKS 5 → 10 → 15 → **20 min apart** by 15:40) while chain snapshots continued and FLIP moved (23,070 → 23,089)
  without a run; **no stale strip at any point 15:15–15:40** (it did fire on the 0×0 tab at 12:38). FUT·BASIS computed off the frozen tile (NIFTY 23,123 · +4.0
  identical 15:20 and 15:25; 23,113 · −6.0 at 15:40).
- *Correction:* chat messages at 15:20–15:31 called this "a shared upstream stall"; it is the closing session. Withdrawn.

**D4-8 · Our front-future basis jumps on a non-expiring contract. — DEFECT (candidate, D3-10 not expiry-specific).**
- SENSEX 29 OCT: +10.0 (09:32) … +62.2 (11:37) → **−6.1 (11:57)** → +48.4 (13:06) → +71.1 (13:47) → +40.3 → +56.4 → +33.9 → **−7.9 (15:11)** → **+47.3 (15:14)** →
  +60.7 → +3.6. Swings of 40–68 pts within 3–20 min. NIFTY 27 OCT −10.3 … +19.9. Needs the futures tick SQL (owed).

**D4-9 · Regime and flips. — BY DESIGN (construction).**
- Flip pairs: **NIFTY 104/104 cumulative (40 today), SENSEX 19/19 today, ours always lower**; NIFTY gap 33–114 (narrowest mid-afternoon), SENSEX 134–347.
- Splits: **SENSEX 4, NIFTY 19**; after 10:00 every NIFTY split had spot between the two roots. The target's NIFTY net crossed zero ≥ 8 times 13:15–15:40
  (−11.3K/−13.9K at 14:25); SENSEX short twice (14:26, 15:00). Ours long all day (share 0.04–0.26).

**D4-10 · Same-screen sign splits at the root, eight today. — OPEN (#8/#9 family).**
- Strike-profile NET GEX vs header strip opposite signs: 09:17 (+2.3K / −1.99K, outside ±1K), 09:55, 11:06, 11:16, 12:15, 13:47 (+1.4K / −1.87K "Turned negative"),
  14:55 (+760 / −1.93K), 15:40 SENSEX (+273 / −73.48). Zero-γ vs profile FLIP gaps 1–13 pts (09:47 NIFTY 13; 10:37 SENSEX 9). No multi-root case captured
  (Price×gamma Peak/Trough not opened). Keep OPEN.

**D4-11 · #19 SENSEX tape stuck on "Loading": six times, one with a stale number beside n/a fields. — DEFECT (availability).**
- 13:06, 13:28, 14:06, 14:47, 15:31, 15:40 (Net delta · session, Price × delta, Replay bar) + 09:20 aggressor. **14:47: Strike profile pane without a clock showing
  "NET GEX −189 · FLIP n/a · C WALL n/a · P WALL n/a"** — −189 was the 14:26 value — beside a live Price×gamma pane (74,517).

**D4-12 · "Held" has three meanings and resets without a state change. — DEFECT (wording) / #26 family.**
- Header "held" = time in state (09:46 1m vs row 45m); row "held" = time on strike; per-strike column "23,000 held 1h 00m" while the pin was 22,900. Header reset with
  no change at 10:10, 10:16 and ~13:37 (SENSEX STABLE rows 13:15–13:45). Post-close 15:30 row "held 10m" at 15:36 matches neither 15:30 nor 15:33.

**D4-13 · Verdict vs aggressor. — BY DESIGN (two objects).** NIFTY agree 3 / disagree 15 / flat 2 (Bullish verdict, aggressor −1…−5 %); SENSEX agree 3 / disagree 2 /
flat 13 / n/a 1. READ 94–100 %; no > 2× base jump with READ flat (#4 stays BY DESIGN).

**D4-14 · Walls. — #23 consistent; usefulness note.** Both C WALL values agreed at every read. Their NIFTY call wall moved 12 times (23,000–23,200), the put wall 6;
zero-Δ drawn off-scale (23,900 at 15:00; 22,400 at 15:20–15:36). **Our SENSEX call wall moved to 76,000 at the 15:10 run** (corridor 74,000–76,000; read text
re-anchored on the put wall 74,000) while theirs stayed 75,000.

**D4-15 · Our FLIP "carry unmeasurable" 08:43 → ~09:40. — BY DESIGN** (manual §2.4, UNMEASURABLE_R until futures print). Closed.

---

## §3 Layer table — what changed from Day 3

| layer | target | ours | change today |
|---|---|---|---|
| Pin | held pressure pin; settlement on argmax Γ ΔOI | γ-conc share | Post-close pin moves on both indices, stamped 15:30 (D4-3). |
| Pin history | log; closed-row **tags** recomputed live | none | 0 value rewrites today; 108 tag rewrites (D4-2). |
| Zero-γ / flip | root nearest spot | flip from futures carry r | Ours lower 104/104; NIFTY roots 33–114 apart. |
| Close handling | holds 15:15–15:30, prints close 15:31, CLOSED at 15:40 (15:30 on Day 3) | holds, never prints close; "LIVE" ~10 min on held value; γ run stops 15:20; no stale strip | Confirmed on a non-expiry day (D4-7). |
| Futures | — | basis jumps on a non-expiring contract | D3-10 not expiry-specific (D4-8). |

---

## §4 Defects

**Theirs:** (1) session-log rank tags recomputed on closed rows (#25; 108 today); (2) post-close pin changes stamped 15:30, both indices (#26); back-dated 09:30
move; withdrawn moves ×3; copy-forward ×1; pin shown outside its own top-5 (09:55); (3) #19 tapes "Loading" ×6 + a clock-less stale profile pane; (4) "held"
wording/resets; (5) header "LIVE FEED" through the closing session and 6–10 min after it; no held-value cue 15:15–15:30; (6) carried, not re-checked: #13, #17.
- Presentation: settlement strike ≠ pin unannounced (15:40 SENSEX); RUNNER-UP omitted on ties; "SINCE YOUR LAST VISIT" word flips with the live sign
  against a fixed 09:56 baseline (≥ 17 flips); no stale badge on a hidden tab (10:36); Γ ΔOI scale changed at the 09:20 version reload (887 → 5,068).

**Ours (candidates):** (1) **no close print; "LIVE" on a held value; γ run stops at 15:20; no stale strip with a 20-min-old run** (D4-7); (2) FUT·BASIS jumps
(D4-8); (3) CLOCKS card intermittently absent (15:05, 15:15, 15:25; absent at 800 px); (4) corridor tile word vs read text ("above call wall" vs "at the call OI
wall", 14:16–15:10); (5) pocket word flip at unchanged sign (09:26 → 09:32); (6) read text anchoring on a different wall than the PIN tile (7 times in the morning);
(7) PIN on near-ties (lead 0.0 SENSEX 10:17; 0.1 NIFTY 09:16) and PIN 23,200 kept after the target dropped 23,200 from walls and top-5; (8) Marketview tab 0×0
after a Chrome reconnect (12:35); (9) `/help` → nginx 403 (link goes to /manual); (10) opening spot 40 pts off the target at 09:16–09:17 (open; re-check).

---

## §5 Candidates (none proposed; operator's yes needed)
- Closing-session state on SPOT ("closing session · held since 15:14", then the official close at 15:30) and a stale strip when the γ run is > 10 min old.
- Write-once pin history if we ever show one; if a rank is shown, show the rank **at the reading** (the target's tag recompute is the counter-example).
- Date the post-close wording (the target's "16 Oct since open" is good practice).
- Hover-to-explain on tile labels (Pass B); keep the qualifiers when tiles truncate at narrow widths.

---

## §6 Owed
1. **Official close 16 Oct** (NSE NIFTY / BSE SENSEX): provisional = the target's print 23,146.15 / ~74,729; web search at 15:42 found no report yet.
2. **SQL (operator runs):** `07` Q1–Q5b; Day-3 (a)–(d); **today:** (e) SENSEX 29 OCT and NIFTY 27 OCT futures ticks 09:30–15:40 vs spot (D4-8); (f) γ runs after 15:20 on
   16 Oct and the spot each used; (g) our SPOT source 15:14–15:40 — did any row carry 23,146.15?
3. IndexedDB export (`hwcap` / `mvcap`), one JS call each — approved 08:40, not yet pulled.
4. **Target narrow-width test** — operator's choice: un-maximise the window, or allow loading the target in an iframe.
5. #13 HHI and #17 null pin — not re-checked today.
6. Project space ≈ 40 KB free at the start of the day; see the chat summary for what was written and which files are safe to delete.

---

## §7 Scores (no expiry today)
- **Pre-reg #4:** NIFTY wrong (Bearish 100 % at 09:45; +152.75 to 15:15); SENSEX wrong (Bearish 100 %; +482). Cumulative 3 right / 2 wrong.
- **Settlement-% log (NIFTY 19 Oct):** 49 readings, final 23,100 at 17 % (±50). Scored on Monday.
- **Pin vs close (descriptive, non-scored):** NIFTY close 23,146.15 (provisional). Their pin 23,000 from 10:15 to 15:31 (−146), 23,100 post-close (−46). Ours
  23,200 through the afternoon and at the close (+54). SENSEX close ~74,729: theirs 74,000 (−729) → 74,500 post-close (−229); ours 75,000 (+271).

---

## §8 Presentation pass

**Method and limits.** `resize_window` returns success but the maximised window stays 1343 wide (also at 08:43 — corrected). Marketview was rendered at
800 and 390 px in same-origin iframes (removed afterwards). The target was read at its native 1343×766 only; loading a second instance in an iframe could open a
second session on the operator's account, so it waits for his call.

| width | board | what shows / what is lost |
|---|---|---|
| 1343 | target | Header + strip + "SINCE YOUR LAST VISIT" take ~45 % of the height; Pin pane shows 6 strike rows; per-pane "HH:MM IST" clocks; hover tooltips on labels. |
| 1343 | ours | 9–10 tiles in one band; CLOCKS card shown on some runs only; read text under the tiles; drawer + /manual for definitions. |
| 800 | ours | Nav collapses to ☰; tiles 3 per row; **CLOCKS absent**; sub-lines truncate ("board 12:20 @ 23,1…", "unit definition pend…"); all key numbers visible. |
| 390 | ours | Tiles 2 per row; all 9 key numbers after one short scroll; no overlap, no horizontal scroll; qualifiers truncated further. |
| 800 / 390 | target | not tested |

**States.**
| state | target | ours |
|---|---|---|
| Loading | pane text "Loading … session tape" (sometimes for 20+ min, #19) | full board in ~3 s |
| Stale | per-pane clock only; hidden tab showed 10-min-old panes with no badge (10:36) | page-top strip "chain data N min old · gamma run N min old · Health ›" (fired 12:38) — but **not** 15:15–15:40 |
| Held (closing session) | no cue; "LIVE FEED" | "LIVE hh:mm" kept ~10 min, then plain "SPOT" |
| Closed | "● CLOSED" + "Market closed. The session laid out…" + review offer; date-specific Delta wording (15:40) | none; held value stays; no close |
| n/a | "n/a · Expiry rolled 15 Oct to 22 Oct, not compared"; RUNNER-UP field simply absent on ties | named non-states: "carry unmeasurable", "unit definition pending", "pending measurement" |

**How each explains a number.** Target: one hover per label (e.g. NET Γ strip: "Net gamma exposure of each index's front (immediate) expiry, in Cr, signed · as of
the last tick") and a long footer per pane. Ours: tile sub-line, a click drawer (WHAT IT IS / HOW TO READ IT / COMPUTED / SCALE / CAVEAT / READ IT WITH) and
/manual with "What it is NOT telling you" and build stamps; no hover.

**Better / worse (candidates only).**
- Target better: hover-to-explain; plain one-line since-visit diff; pane timestamps; explicit closed state with a review path; date-specific post-close wording;
  "not a forecast" line on summaries.
- Ours better: page-level stale strip with ages (when it fires); documented named non-states; gaps never drawn as zero; responsive layout; deeper, limit-stating
  explanations.
- Both weak: neither says "closing session, value held" 15:15–15:30. Target: since-visit word flips with noise; no stale badge on hidden tabs; held "LIVE FEED"
  6–10 min past the close. Ours: qualifiers truncate first on small screens; CLOCKS visibility erratic; stale strip silent while the run is 20 min old.
