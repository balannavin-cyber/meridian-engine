# Parity target evaluation, Day 3 — Thu 15 Oct 2026 (SENSEX 0DTE expiry; NIFTY front 19 Oct)

Source: `02_capture_log_2026-10-15.md` (merged parts A–F; 09:23 → 15:40 IST, ~50 checkpoints; SENSEX in every round, NIFTY in every FULL round).
Verdict labels as in `08_defect_verification_15Oct.md`: **BY DESIGN / DISCLOSED / DEFECT / OPEN**, plus **usefulness** where a read is scored against an outcome.
Units: target GEX in K Cr (γ·OI·S²·0.01/1e7·√(τ/5d)), ours in L Cr (γ·OI·S²/1e7) — signs and net/gross only, never magnitudes.

**Day in one line:** a one-way rally (SENSEX 72,782 → **74,316 close, +2.11 %**; NIFTY 22,622.70 → **22,997.35, +1.66 %**). Both boards' pins stepped up
behind spot all day; the target's settlement % turned out to be computed on the **argmax-Γ ΔOI strike** (#16 solved); the target's session log was seen
rewriting closed rows ~20 times; our board never showed the 15:30 closing print.

---

## §1 Against the plan (starter §5)

| plan item | done? | note |
|---|---|---|
| Pre-open: docs, author's X, tabs, plan | partly | Author read at 06:50 (nothing new since 01:20). **Capture started 09:23, not 09:15** (target URL hunt); the 09:20 pre-reg read is lost, 09:23–09:24 substituted. |
| Pre-reg #4 window (09:20 / 09:30 / 09:45) | yes (09:23 / 09:30 / 09:45) | Table in part A; 09:45 → 15:15 column filled at 15:16. |
| SENSEX expiry routine (H1–H9 shape) | yes | Pin path, settlement %, flips (ours skipped), walls, verdict vs aggressor, closing hold, 15:30 print, post-close. |
| NIFTY in every FULL round | yes | Missed only at 15:16 / 15:25 (target NIFTY Terminal not read). |
| Live checks #16, #8, #4/#5, #23 | yes | #16 solved; #23 consistent; #4/#5 evidence; #8 still open (see §2). |
| SENSEX Delta · positioning live | yes | Every round. |
| Post-close 15:40 + §7 + §8 | yes | Project full → files sent in chat (see §6). |

Operating issues: Marketview went to a 0×0 viewport twice (10:55, 15:05; fresh tabs 863736757 → 863736767); one index-picker misfire (BANKNIFTY, 09:56, discarded);
the project has refused writes since 11:18 (full) — parts C–F were held locally.

---

## §2 Headline findings

**D3-1 · #16 settled: the settlement % is computed on the strike with the largest Γ ΔOI, not on the displayed pin. — BY DESIGN (undisclosed; presentation note).**
- Held at **every** read: **33/33 SENSEX, 18/18 NIFTY** (from ~11:55, when the rule was formulated, through 15:40; it also explains every earlier mismatch on review).
- Six clean **decoupled** reads where the pressure #1 / header pin ≠ settlement strike, and the settlement strike = argmax Γ ΔOI:
  SENSEX 13:46 (pin 74,500 / settlement 74,000), 15:10 (74,000 / 73,900), 15:16 (73,900 / 73,800), 15:25 (74,100 / 74,200), 15:32 (74,300 / 74,400); NIFTY 13:56 (23,000 / 22,900).
- So the "pin" (pressure = Γ ΔOI × distance decay × time amplifier) and the settlement probability are about **different strikes by construction**. The pane
  never says so; a reader takes "SETTLEMENT 37 % within ±100 of 73,900" as a statement about the PIN 74,000 above it. "Longest-held" (the earlier hypothesis) is refuted.

**D3-2 · The session log ("one row per 15-minute reading … each held until the next") rewrites closed rows. — DEFECT (breaks its own stated rule).**
- Closed-row changes logged: SENSEX 11:15, 11:30, 11:45, **12:00 (LOCKED 22 % 80 → STABLE 23 % 72: a live LOCKED state erased)**, 12:15, 13:45 (three versions), 14:00
  (overwritten with the 14:15 values), 14:30, 14:45, **15:00 (pin back-dated: 74,000 → "73,900 ↓ from 74,000", stamped 15:00, appeared after 15:10)**,
  **15:15 (three pins: 73,900 → 74,100 → 74,300; spot replaced with the 15:30 closing print)**; NIFTY 09:45 / 10:30 contradictions, 13:45, 14:00, 14:15, 14:30, 14:45,
  15:00 (STABLE → LOCKED), 15:15 (spot replaced with the close).
- **Rank tags** ("#n") are repainted onto rows closed hours earlier every time the live ranking reshuffles (SENSEX 73,800 rows: untagged → #5 → #4 → #3 → #2 → #3 → untagged
  in 90 minutes; 74,000 rows: #1 → · → #5 → #3 → ·).
- **Post-close change of the final reading:** the SENSEX 15:30 row read "74,300 STABLE 20 % 71" at 15:32 and "**74,400** ↑ from 74,300 SHIFTING 31 % 50" at 15:40,
  after the index had stopped trading (OI kept updating).
- Same family, not counted (newest row, inside "held until the next"): a 13:45 SENSEX move to 74,500 shown at 13:46 was withdrawn and its path marker erased.
- Consequence: the target's own history cannot reproduce what it showed live. Any back-count of LOCKED time, pin moves or "pin vs settle" from its log differs
  from the live screen (the 15:15 pin is unrecoverable). This matters for the scorecard (§7) and for anyone (incl. the author) citing its pin history.

**D3-3 · Settlement % calibration, first expiry scored. — usefulness.**
- 49 SENSEX readings; the settle (74,316) was inside the stated ±100 band on **2** (both "66 % within ±100 of 74,400", 15:32 and 15:40 — after the closing print was known).
- Every reading before 15:30 named a strike 116–1,316 pts from the settle (all "no"). Mean stated probability 21 %. The stated %s were individually modest (8–47 %),
  so most of the "no"s are not miscalibration per se, but the band chased spot upward all day and never got ahead of it. Running table in §7.2; n = 1 expiry.

**D3-4 · Both pins stepped up behind spot; neither forecast the settle. — usefulness (descriptive).**
- Their pin path: 73,000 → 73,300 → 73,500 → 73,700 → 73,800 → 74,000 (12:30–14:45) → 73,900 → 74,300 → 74,400 (post-close). Ours: 73,000 / 73,500 / 74,000 flicker in the morning,
  74,200 → 74,500 midday, 74,000 (14:15–15:00), 73,900 → 74,100 at the close.
- Scorecard (§7.1): 47 pairs — **same 13, ours closer 25, theirs closer 9**; within ±100 of the settle **theirs 2/49, ours 0/47**; mean |pin − settle| theirs 564, ours 404.
  As on 13 Oct, ours being "closer" is the trend's luck (our pin has no distance term and sat above spot on the call OI wall through midday), not skill.

**D3-5 · Flips: ours skipped on SENSEX all day (expiry, ENH-131); NIFTY pairs 22 more today, all ours lower → 64/64 (cumulative since 13 Oct). — BY DESIGN (construction).**
- NIFTY gap −30 … −82; our flip sits +22…+63 above our own strike-axis zero, theirs +56…+133.
- SENSEX strike-axis zero vs their zero-γ: +347 (09:25) → +24 (13:16) → **−1…−7 (13:46–14:35, roots coincide)** → +95 (15:16, their root fell 100 in 10 min) → +137 (15:25, spot frozen).
  The roots agree when the book is stable and diverge when OI moves fast (their root uses the live classified book; ours lags one run).

**D3-6 · Regime splits: SENSEX 8, NIFTY 9 (same-minute sign disagreements). — BY DESIGN (construction) + H8.**
- Almost all inside ±60 pts of a root. Our SENSEX net sign alternated on every run 14:00 → 14:25 (+20.1L / −22.6L / +28.7L / −26.8L) with spot within ±40 of the zero:
  at-the-root regime noise (H8). Both boards turned SENSEX long in the closing hold (theirs +2.6K at 15:20, ours +11.6L on the 15:15 run) as spot sat above both roots.

**D3-7 · Verdict vs aggressor. — BY DESIGN (two objects).**
- SENSEX: verdict Bullish 95–100 % all day; aggressor Δ disagreed **33 times**, flat 8, agreed 6. NIFTY: aggressor agreed **25/25**.
- SENSEX State turned negative several times ("puts outweigh calls", −15K … −44K, 14:29–15:10) while Initiated stayed 99–100 % bullish; positive again from 15:16.

**D3-8 · Walls. — BY DESIGN (theirs) / #23 consistent.**
- Their γ-weighted call wall followed spot down from 74,500 (13:55) → 74,300 → 74,200 → 74,100 → **74,000 = their pin (15:05)** → 74,400 at the close; both C WALL panels agreed at
  every readable minute (#23). Ours are OI walls (74,500 → 74,300 → 74,200 call; 73,800 → 74,000 put).

**D3-9 · Closing session (ADR-022). — BY DESIGN (both); our labelling DEFECT (D2-4 family).**
- Both boards froze spot at ~15:14–15:15. **SENSEX froze 48 pts apart** (theirs 73,970, ours 73,922.2 "LIVE 15:14"); NIFTY on the same 22,940. Our tile kept the word "LIVE"
  on a stale value for ~10 min, then (by 15:26) showed plain "SPOT" with the run spot.
- **Their pin and settlement kept moving on OI alone during the hold** (73,900 → 74,100 → 74,300; 47 % → 17 % → 66 %; zero-γ 73,937 → 73,806 → 74,192).
- At 15:30 the target printed the closing prices (74,316 / 22,997.35). **Our board never did**: SPOT 73,969.7 / 22,940.0 through 15:40; the 15:20 γ run landed (clock "γ 15:20")
  on the frozen spot and reproduced the 15:15 board; FUT·BASIS +227.8 / +55.5 computed off the frozen tile.

**D3-10 · Our front-future basis jumped between runs on the expiry day. — OPEN (candidate DEFECT).**
- SENSEX basis +46 → +53 → **+114** → +61 → +91 → +98 → +110 → **+175** → +181 → +168 → +228 (14:36 → 15:40) with the FUT print parked near 74,100–74,200 while spot fell ~110.
  Looks like a stale or thin quote on the expiring contract. Needs the futures tick table (owed SQL).

---

## §3 Layer table — what changed from Day 2

| layer | target | ours | change today |
|---|---|---|---|
| Pin | pressure (Γ ΔOI × distance × time); held state; **settlement % on argmax Γ ΔOI** | γ-concentration share; no hysteresis | Settlement-strike rule established (D3-1). |
| Pin history | session log, rewrites closed rows | none kept on the board | New DEFECT (D3-2). |
| Zero-γ / flip | root nearest spot, served on 0DTE | flip skipped on expiry (ENH-131); NIFTY served | Roots coincided on SENSEX 13:46–14:35. |
| Walls | γ-weighted, follow spot | OI walls | Unchanged. |
| Positioning verdict | ΔOI × Δ, premium-classed | (declined, S96-I) | READ % explains the 09:23→09:26 jump (#4/#5). |
| Close handling | prints 15:30 close; "CLOSED" header; review banner | stale "LIVE" tile ~10 min; no close print | Confirmed on expiry (D3-9). |

---

## §4 Defects

**Theirs (by their own rules or inconsistent on screen):**
1. **Session-log history rewrite** (D3-2) — new, high severity for any use of their history.
2. Back-dated pin move (15:00 SENSEX) and post-close change of the final reading (15:30 SENSEX) — same family.
3. Path markers missing for several moves (10:00, 11:30, 15:15, 15:30 SENSEX; 14:00 NIFTY) while the log shows "↑/↓ from".
4. Header state vs live log row disagree at the same minute (15:10: header SHIFTING, live row STABLE).
5. Carried from 08: HHI 0.000 (#13), null pin "0" (#17), tapes stuck on "Loading" (#19) — not re-seen today on the panes read.
- **Presentation note:** the settlement line's strike is the argmax-Γ ΔOI strike, not the pin; undisclosed (D3-1).

**Ours (inconsistent on our own screen or vs our own definitions; all candidates):**
1. **No closing print; "LIVE" on a stale tile** (D2-4, confirmed on expiry): SENSEX shown 346 below the settle; basis off the frozen tile.
2. **Pocket word vs net Γ**: "dampening" on short nets (NIFTY repeatedly; SENSEX 14:51) and "amplifying" on long (14:26); the word flipped run to run at an unchanged sign.
3. **"short γ · −0.00 of gross"** — a regime word on a zero net (morning).
4. **Pin flicker on near-ties** (leads 0.0–0.5): SENSEX 73,000 ↔ 73,500 ↔ 74,000 (morning), 74,500 ↔ 74,000 (14:00–14:25, coupled to the net-sign flips), 74,000 → 73,900 → 74,100;
   NIFTY 23,200 → 22,700 (lead 0.0) → 23,100.
5. **Read text vs PIN tile**: read text anchors on the put OI wall 74,000 while PIN = 74,500 "≡ call OI wall" (14:26) or 73,900 (15:05–15:10).
6. **One-run lag** on sign and pin (14:20 run long on run spot 74,245.6 while live spot sat below both roots).
7. **Phantom overnight change** on the SPOT tile (+25.1 SENSEX / +2.5 NIFTY pre-open).
8. **Sign vs root**: net long with spot below our own strike-axis zero (NIFTY ×6 in the morning; SENSEX 14:08).
9. **Front-future basis jumps** on the expiring contract (D3-10, open).
10. Marketview tab drops to a 0×0 viewport (10:55, 15:05).

---

## §5 Candidates (none proposed; operator's yes needed for anything)
- Closing-session state on our SPOT tile ("closing session · last trade hh:mm", then "close" at 15:30) and pick up the official close.
- Pocket word from net Γ (or drop it near the root); three-state regime near the flip (H8).
- Pin hysteresis / a tie state ("74,000 ≈ 73,900") instead of flicker.
- If we ever show a pin history: write-once rows (the target's rewrite problem is the counter-example).

---

## §6 Owed
1. **SQL (operator runs; `07_owed_sql_14Oct.md` Q1–Q5b, still unrun)**, plus today: (a) SENSEX front-future ticks 14:30–15:30 vs spot (basis jumps, D3-10); (b) do γ runs exist at 15:25/15:30,
   and what spot did the 15:20 run use; (c) same-minute curve pull for the SENSEX root coincidence 13:46–14:35 vs the 15:16–15:25 divergence.
2. **BSE confirmation of the 74,316 settle** (shell cannot reach exchange sites; the figure is the target's 15:30 print).
3. IndexedDB export (one JS call each; ask once).
4. NSE participant-OI description test (candidate).
5. **Project space:** the project refuses writes since 11:18; today's merged log, this report and the 08 update are sent in chat instead. The Day-2 part files
   `02_capture_log_2026-10-14_b … _j` duplicate the merged Day-2 log and could be removed — operator's decision.

---

## §7 Scorecards

### 7.1 SENSEX pin scorecard (06 format) — settle 74,316
Close used: **74,316**, the target's 15:30 print (header strip, Pin, Terminal; "CLOSED" at 15:40). Our board never displayed it (73,969.7).
Pins as rendered at each checkpoint: target = Pin · pressure header; ours = Marketview PIN (γ-conc) tile (one run behind). Rows extracted from the merged log.

| IST | their pin | Δ to settle | our pin | Δ to settle | same? |
|---|---|---|---|---|---|
| 09:24 | 73,000 | 1316 | 73,000 | 1316 | yes |
| 09:31 | 73,000 | 1316 | — | — |  |
| 09:35 | 73,000 | 1316 | 73,500 | 816 | no (ours closer) |
| 09:40 | 73,000 | 1316 | 73,500 | 816 | no (ours closer) |
| 09:45 | 73,000 | 1316 | — | — |  |
| 09:50 | 73,200 | 1116 | 73,000 | 1316 | no (theirs closer) |
| 09:55 | 73,200 | 1116 | 73,000 | 1316 | no (theirs closer) |
| 10:00 | 73,300 | 1016 | 74,000 | 316 | no (ours closer) |
| 10:05 | 73,500 | 816 | 73,000 | 1316 | no (theirs closer) |
| 10:10 | 73,500 | 816 | 73,000 | 1316 | no (theirs closer) |
| 10:15 | 73,500 | 816 | 74,000 | 316 | no (ours closer) |
| 10:26 | 73,500 | 816 | 74,000 | 316 | no (ours closer) |
| 10:35 | 73,500 | 816 | 74,000 | 316 | no (ours closer) |
| 10:45 | 73,500 | 816 | 74,000 | 316 | no (ours closer) |
| 10:56 | 73,700 | 616 | 74,000 | 316 | no (ours closer) |
| 11:06 | 73,700 | 616 | 74,000 | 316 | no (ours closer) |
| 11:15 | 73,700 | 616 | 74,000 | 316 | no (ours closer) |
| 11:26 | 73,700 | 616 | 73,500 | 816 | no (theirs closer) |
| 11:36 | 73,800 | 516 | 74,000 | 316 | no (ours closer) |
| 11:46 | 73,800 | 516 | 74,200 | 116 | no (ours closer) |
| 11:55 | 73,800 | 516 | 74,200 | 116 | no (ours closer) |
| 12:05 | 73,800 | 516 | 74,200 | 116 | no (ours closer) |
| 12:16 | 73,800 | 516 | 74,200 | 116 | no (ours closer) |
| 12:25 | 73,800 | 516 | 74,200 | 116 | no (ours closer) |
| 12:44 | 74,000 | 316 | 74,200 | 116 | no (ours closer) |
| 12:56 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 13:04 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 13:16 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 13:26 | 74,000 | 316 | 74,000 | 316 | yes |
| 13:35 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 13:46 | 74,500 | 184 | 74,500 | 184 | yes |
| 13:55 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 14:06 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 14:15 | 74,000 | 316 | 74,000 | 316 | yes |
| 14:25 | 74,000 | 316 | 74,500 | 184 | no (ours closer) |
| 14:29 | 74,000 | 316 | 74,000 | 316 | yes |
| 14:35 | 74,000 | 316 | 74,000 | 316 | yes |
| 14:40 | 74,000 | 316 | 74,000 | 316 | yes |
| 14:45 | 74,000 | 316 | 74,000 | 316 | yes |
| 14:49 | 74,000 | 316 | 74,000 | 316 | yes |
| 14:55 | 74,000 | 316 | 74,000 | 316 | yes |
| 15:00 | 74,000 | 316 | 74,000 | 316 | yes |
| 15:05 | 74,000 | 316 | 73,900 | 416 | no (theirs closer) |
| 15:10 | 74,000 | 316 | 73,900 | 416 | no (theirs closer) |
| 15:16 | 73,900 | 416 | 73,900 | 416 | yes |
| 15:20 | 73,900 | 416 | 74,100 | 216 | no (ours closer) |
| 15:25 | 74,100 | 216 | 74,100 | 216 | yes |
| 15:32 | 74,300 | 16 | 74,100 | 216 | no (theirs closer) |
| 15:40 | 74,400 | 84 | 74,100 | 216 | no (theirs closer) |

**Totals (n = 1 expiry; descriptive):** reads theirs 49, ours 47; pairs 47: same 13, ours closer 25, theirs closer 9
- within ±100 of the settle: theirs 2/49, ours 0/47
- mean |pin − settle|: theirs 564, ours 404

Notes: theirs at 15:40 is the post-close rewritten final (74,400); at 15:32 it was 74,300. Ours at 15:32/15:40 is the 15:15/15:20 run on a frozen spot.

### 7.2 Settlement-% calibration (the target's one forward number)

**SENSEX 15 Oct (settle 74,316; band ±100):**

| IST | strike | % (±100) | settle 74,316 inside? |
|---|---|---|---|
| 09:24 | 73,000 | 14 % | no (+1316) |
| 09:31 | 73,000 | 13 % | no (+1316) |
| 09:35 | 73,000 | 13 % | no (+1316) |
| 09:40 | 73,000 | 12 % | no (+1316) |
| 09:45 | 73,000 | 14 % | no (+1316) |
| 09:50 | 73,000 | 11 % | no (+1316) |
| 09:55 | 73,000 | 9 % | no (+1316) |
| 10:00 | 73,000 | 8 % | no (+1316) |
| 10:05 | 73,000 | 8 % | no (+1316) |
| 10:10 | 73,500 | 15 % | no (+816) |
| 10:15 | 73,500 | 14 % | no (+816) |
| 10:26 | 73,500 | 14 % | no (+816) |
| 10:35 | 73,500 | 14 % | no (+816) |
| 10:45 | 73,500 | 13 % | no (+816) |
| 10:56 | 73,500 | 13 % | no (+816) |
| 11:06 | 73,700 | 16 % | no (+616) |
| 11:15 | 73,500 | 13 % | no (+816) |
| 11:26 | 73,500 | 13 % | no (+816) |
| 11:36 | 73,800 | 17 % | no (+516) |
| 11:46 | 73,800 | 16 % | no (+516) |
| 11:55 | 73,800 | 16 % | no (+516) |
| 12:05 | 73,800 | 17 % | no (+516) |
| 12:16 | 73,800 | 17 % | no (+516) |
| 12:25 | 73,800 | 17 % | no (+516) |
| 12:44 | 74,000 | 18 % | no (+316) |
| 12:56 | 74,000 | 18 % | no (+316) |
| 13:04 | 74,000 | 19 % | no (+316) |
| 13:16 | 74,000 | 19 % | no (+316) |
| 13:26 | 74,000 | 20 % | no (+316) |
| 13:35 | 74,000 | 18 % | no (+316) |
| 13:46 | 74,000 | 16 % | no (+316) |
| 13:55 | 74,000 | 17 % | no (+316) |
| 14:06 | 74,000 | 19 % | no (+316) |
| 14:15 | 74,000 | 20 % | no (+316) |
| 14:25 | 74,000 | 23 % | no (+316) |
| 14:29 | 74,000 | 24 % | no (+316) |
| 14:35 | 74,000 | 26 % | no (+316) |
| 14:40 | 74,000 | 28 % | no (+316) |
| 14:45 | 74,000 | 30 % | no (+316) |
| 14:49 | 74,000 | 32 % | no (+316) |
| 14:55 | 74,000 | 34 % | no (+316) |
| 15:00 | 74,000 | 35 % | no (+316) |
| 15:05 | 74,000 | 39 % | no (+316) |
| 15:10 | 73,900 | 37 % | no (+416) |
| 15:16 | 73,800 | 28 % | no (+516) |
| 15:20 | 73,900 | 47 % | no (+416) |
| 15:25 | 74,200 | 17 % | no (+116) |
| 15:32 | 74,400 | 66 % | **yes** (−84) |
| 15:40 | 74,400 | 66 % | **yes** (−84) |

- readings 49; inside 2; mean stated probability 21.3 %; Brier 0.048 (climatology-free; descriptive)

**Running table across expiries:**

| expiry | index | readings | inside band | stated % range | readings on the eventual "inside" strike | note |
|---|---|---|---|---|---|---|
| 13 Oct | NIFTY (close 22,721.95, band ±50) | ~38 (strikes not logged per read) | 15:15–15:30 reads at 22,700 (96–99 %) inside | 21 → 99 % | only from 15:15 | 96 % printed on a frozen spot (06) |
| 15 Oct | SENSEX (settle 74,316, band ±100) | 49 | **2** (15:32, 15:40; 66 %) | 8 → 66 % | only after the 15:30 print | band strike chased spot all day |
| 19 Oct | NIFTY | pending | | | | |

### 7.3 The author's scorecard (@AshwinBadri2)
| his call (14 Oct) | outcome 15 Oct |
|---|---|
| Bearish SENSEX: "72,500 breaks → ugly" | **Not triggered.** SENSEX opened 73,049 and never traded near 72,500 on either board; low of the reads 73,250 (09:15 row). |
| SENSEX position profits at expiry 71,816–73,415 | **Outside.** Settle 74,316, **901 above** the upper breakeven. |
| NIFTY "It'll fall tomorrow!" (01:20) | **No.** NIFTY closed 22,997.35, **+374.65 (+1.66 %)** above 22,622.70. |
| Target short-γ vs ours long (pre-open) | Mixed: 8 same-minute SENSEX splits; both long from the closing hold. A short-γ (amplifying) read fits a one-way +2 % day; ours did not flag it. Descriptive only. |
| His pins vs settle | His own pins not stated; target pins vs settle in §7.1. |

**His posts today (X, `from:AshwinBadri2 since:2026-10-15`, read 15:45):**
- **~09:45 (≈6 h before the read):** he says he was carrying a bearish overnight position; SENSEX "jumped off the put wall on unusual volumes", with delta positioning backing a bullish
  shift; he converted the trade into a call ratio spread with put shorts. **Board at the time:** target SENSEX verdict Bullish 99–100 % (09:30–09:45), aggressor −11…−7 % (disagree);
  their pin 73,000 → 73,200 SHIFTING; ours 73,500 → 73,000; spot ~73,300–73,600. He changed his own thesis intraday on the target's positioning read — the use pre-reg #4 tests.
- **~13:45:** product post (replay a session to see how positioning evolved).
- **~14:40:** replies — "Positioning changed today morning!", a SENSEX Delta · positioning chart (Bullish, +2,31,007 Cr, 100 %, put short buildup +1,01,512 — matches our 14:07 read exactly),
  "this divergence isn't healthy!" (context not visible).

### 7.4 Pre-reg #4 (09:20–09:45 split vs 09:45 → 15:15 direction)
| index | early-window verdict (09:23 / 09:30 / 09:45) | aggressor | 09:45 spot | 15:15 spot | direction | verdict |
|---|---|---|---|---|---|---|
| NIFTY | Bullish 91 % (READ 63 %) / 99 % / 99 % | agree | 22,777 | 22,940 | +163 | **right** |
| SENSEX | Bullish 99 % / 99 % / 100 % | disagree | 73,333 | 73,970 | +637 | **right** |

n (pre-reg #4, cumulative): 13 Oct NIFTY right (Day 1, informal); 14 Oct not logged; 15 Oct 2/2 right. No inference until the pre-reg's n.

---
**Addendum (16 Oct 05:07 IST):** operator's charting screen shows the BSE SENSEX close for 15 Oct as **74,315.61 (+2.11 %)**, which confirms the target's 74,316 print (rounded). §7 distances change by < 1 pt; no table changes. The same chart's last 75-min bar ends at **73,959.44**, the last continuous-session value. That is 356 below the official close and consistent with the closing-session freeze both boards showed (target 73,970; our run spot 73,969.7; our tile 73,922.2).
