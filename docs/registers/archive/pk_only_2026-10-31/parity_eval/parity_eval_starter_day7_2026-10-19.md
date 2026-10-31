# Starter prompt — parity target evaluation, Day 7: Mon 19 Oct 2026 (NIFTY front expiry; final day and final report)

Paste everything below the line as the first message of the session. It **supersedes** `parity_eval_starter_day4_2026-10-16.md` and
`parity_eval_starter_day3_2026-10-15.md`; where they differ, this one wins. Written at the Day-4 close (16 Oct 15:55 IST).

---

## 0. Today
**Mon 19 Oct 2026, Day 7 of 7** (13 → 19 Oct; Sat/Sun no market). **NIFTY front expiry (0DTE)**; SENSEX front = **22 Oct** (check SYMBOL·EXPIRY).
**Check first that 19 Oct is a trading day** (a search on 16 Oct surfaced an "October 20" exchange-holiday headline; confirm the NSE calendar before
scheduling anything). If the market is shut, run only §8 (final report) and say so.

**Main jobs today, in order of importance:**
1. **NIFTY expiry routine, both boards** (§5; Day-1 H1–H9 shape, Day-3 §5 for the SENSEX expiry): pin path, settlement %, walls, flips (ours skipped on 0DTE,
   ENH-131), verdict vs aggressor, closing hold 15:15–15:30, the 15:30 print, post-close 15:40.
2. **Scoring** (§7): NIFTY pin scorecard (`06` format), **settlement-% calibration** (16 Oct 49 readings + today's), pre-reg #4 (today = n 6–7), the author's scorecard.
3. **Final report** (§8): synthesis across Days 1–7 — adopt / don't adopt / test, with evidence links — published as a project doc.
4. Running counters (§4.3) and the closing behaviour of both boards.

You are finishing the evaluation of **the parity target**, a live options-analytics terminal on a 7-day trial on the operator's broker account. Goal: understand
exactly how it works, compare it layer by layer with MERIDIAN's board (Marketview), and find what makes MERIDIAN better. This is S97's evaluation thread.
Days 1–4 are done and documented. **One session per evaluation day. This session ends when the operator says so.**

**Framing (operator, 15 Oct): the target is a positioning platform, not a predictive one.** Judge each number against the target's own definition first
(pane footers). A read that "didn't predict" is not a defect. Separate in every finding: **definition** (BY DESIGN) / **defect** (inconsistent on screen or
breaks its own stated rule) / **usefulness** (does the description match an independent record; do its few forward numbers calibrate). Labels in the log:
**BY DESIGN / DISCLOSED / DEFECT / OPEN**, plus **presentation**.

## 1. Read first, in this order (do not ask the operator for anything these answer)
1. `claude/parity_eval/08_defect_verification_15Oct.md` — **updated post-close 16 Oct**: verdict table #1–#29, tally (6 DEFECT), §5 checks for 19 Oct. **Start here.**
2. `claude/parity_eval/parity_target_day4_2026-10-16.md` — D4-1 … D4-15, §6 owed, §7 scores, **§8 presentation pass**.
3. `claude/parity_eval/parity_target_day3_2026-10-15.md` — D3-1 … D3-10, §7 scorecards (SENSEX pin scorecard, settlement-% table, author, pre-reg #4).
4. `parity_target_day2_2026-10-14.md`, `parity_target_day1_2026-10-13.md` (H1–H9 = the NIFTY expiry routine from 13 Oct).
5. `03_findings.md`, `00_inventory.md`, `01_cockpit_schema.md`, `06_nifty_pin_scorecard_13Oct.md` (format), `07_owed_sql_14Oct.md`, `04_author_read.md`.
6. Day-4 merged log `02_capture_log_2026-10-16.md` — **sent in chat on 16 Oct; in the project only if the operator uploaded it** (check `project_info`);
   it holds the **NIFTY settlement-% table (Appendix 1, 49 rows)**. If it is not in the project, the table summary is in Day-4 §2 D4-6 and §7; ask the
   operator once for the file.
7. Then as usual: `CLAUDE.md`, `claude/S97_session_prompt.md`, `claude/rulings_s96.md`, `claude/live_read_pack_2026-10-12.md`.

## 2. Standing rules (non-negotiable)
- **Never name the product** in any MERIDIAN artefact: write "the parity target" / "the target". The author's X handle (@AshwinBadri2) is fine.
  Never paste the target's URL or brand into project docs. **`grep -i` every file for the brand before every `project_write`.**
- **Session close is when the operator says so. Do not remind him. Never mention sleep, rest, pausing or "pick this up later".**
- **Read the docs before asking him to check anything.**
- SQL: each query in its own code block. Read-only only (`bin/roq.sh`). DDL and writes are operator actions. **No `.env` reads.**
- **Board wording:** any change needs his explicit yes. **Never write the trade names of ∂Δ/∂σ and ∂Δ/∂t** on our board or in project docs (use the symbols;
  quote the author only when attributing).
- **On the target: read only.** Never touch broker auth, billing / subscription, the Claude-connection settings, or anything that places orders.
  **Do not click the replay scrubber** (crashed the page 14 Oct). Do not trigger dialogs. Do not dismiss banners you don't need to (the "Since your last
  visit" strip and "Add … workspace" banners were left alone on Day 3).
- **Browser: Claude in Chrome** (his signed-in Chrome), not the built-in browser.
- **Candidates are candidates.** Nothing is proposed or built without his yes. Anything statistical needs a prereg first (ADR-009).
- **Permissions given on earlier days do not carry over** (the window resize, JS for the IndexedDB export, anon SELECTs). Ask once each.
- **Project files: never delete anything in the project.** Only the operator deletes, and only files he names. He cannot see full file names in the
  project's context tab, so when you recommend deletions give **exact full paths** and say which merged file holds their content (Day 3 lesson: a
  prefix-based delete took out the merged logs with the parts).

## 3. How to operate (learned on Days 1–4)

### 3.1 Start-up (before 09:10)
1. `ToolSearch` once: `select:ReadNotifications,SendUserMessage,mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__resize_window`
   (+ `mcp__claude-code-remote__send_later` / `list_triggers` if deferred).
2. `tabs_context_mcp`. On 16 Oct the operator kept one Chrome window with **the target** (tab title starts
   "Workspace | …", path `/workspace/?ws=Pin`) and **Marketview** (`https://marketview.meridianalpha.in/board`) and X in one tab group (create a Claude tab group with his yes if none exists). **Use those tabs.** If the target tab is
   missing, ask him once for it ("please open the target's workspace tab"); do not hunt for the URL (Day 3 lost 09:15–09:23 doing that).
3. Confirm both render: zoom the target header `[1000,0,1343,50]` and the Marketview strip `[0,0,1343,360]`. Log tab ids in part A.
4. `project_info`: note `knowledge_size` vs `max_knowledge_size` (2,000,000). **Day 3 ran out at 11:18 and every write after failed.** If < 120 KB headroom,
   tell the operator once, with exact paths of safe deletions (§2), and keep logs locally meanwhile.
5. SendUserMessage a 3-line plan. Ask once for the permissions you will need (JS for the IndexedDB export; anon SELECT).

### 3.2 Tabs and rendering
- **Only the front tab of a Chrome window renders.** Two windows side by side keep both alive. A background or occluded tab goes stale; a **0×0 viewport**
  means screenshots fail and clicks are ignored (Marketview: 10:55 and 15:05 on Day 3; 12:35 on Day 4 after a Chrome reconnect changed every tab id). Fix: `tabs_create_mcp` → navigate to the board →
  close the old tab → log the new id → update the round instructions file (§3.6).
- `navigate` Marketview at **every** round (it freezes in the background: "LIVE 10:38 · board 10:30").
- If tab ids change (Chrome reconnect), call `tabs_context_mcp` again.

### 3.3 Reading the target (Day-4 coordinates for a 1343×766 viewport; re-measure if the window size differs)
- **Workspace tabs** on the bottom bar, **y ≈ 744** (766-high viewport; 686 at 710): **Terminal x≈60, Flows 132, Density 202, Pin 262, Delta 315, IV 364, OI 404**. Click, wait 2–3 s.
- **Activate the target tab first** (a zoom on it) and check every pane's "HH:MM IST" clock = now: a background target tab stops updating with no badge (16 Oct 10:36).
- **Index picker:** `find` "Next index button (chevron right of index name in header)" / "Previous index button …", **re-find before every click** (a stale ref
  landed on the target's Settings page on 16 Oct 09:21 — Back only), click by ref, **2 s between clicks**,
  order **NIFTY → BANKNIFTY → SENSEX → FINNIFTY → MIDCPNIFTY**, confirm with zoom `[1000,0,1343,50]` scale 0.5 after every switch (a misfire landed on
  BANKNIFTY on Day 3; discard such reads). The selection persists across workspaces.
- **Pin:** `get_page_text` on the Pin workspace returns everything: header (PIN, STATE, held, CONVICTION, RUNNER-UP, margin, **SETTLEMENT % and its
  strike**), the top-5, the per-strike table (P %, **Γ ΔOI**, Net Γ OI, held), the pin-path markers ("↑ 73,300 · 09:45 …") and the **full session log**
  (one row per 15-min reading). Read the whole log every time (§4.2).
- **Terminal:** zoom `[0,90,1343,480]`, or `[0,400,1343,640]` when the "SINCE YOUR LAST VISIT" strip pushes the panes down (it appeared 15:00 on Day 3).
  Read: spot, NET GEX (Strike profile) + strip net Γ, zero gamma / FLIP, **C WALL / P WALL on both the Strike profile and the Price × delta rail** (#23),
  net Δ off open, zero Δ.
- **Delta:** zoom `[0,220,600,520]` (scale 0.6) for the headline, then `find` "text containing 'of ΔOI could be read', and the Delta aggressor Δ percentage at top right of the aggressor pane"
  (the five-item find failed once on 16 Oct; the zoom gives verdict, % and since-open).
- End each round on the **Pin** workspace.
- Footers are definitions; `get_page_text` reads them. Quote them verbatim when a verdict depends on wording.

### 3.4 Reading Marketview
- `navigate` the board, `find` "SENSEX and NIFTY symbol buttons in banner", click by ref, wait 2 s, zoom `[0,0,1343,360]`: SYMBOL·EXPIRY, SPOT (LIVE clock,
  "board HH:MM @ run spot"), NET Γ (+ share of gross, regime word), FLIP (or "skipped · expiry day"), CORRIDOR (+ position word), PIN (γ-conc, % of gross,
  lead, wall tag), IV·VIX (priced move), FUT·BASIS, OPEN·GAP, CLOCKS ("γ hh:mm · chain hh:mm"), and the read text.
- **The read text quotes the γ run's spot, not the live tile** (BY DESIGN; withdrawn as a defect on Day 3).
- **Per-strike net γ** around spot: `find` "strike labels A, B, C and D each with the signed net gamma number on the same row" (name 4 strikes around spot).
  This phrasing works; looser phrasings return strikes without values. **Strike-axis zero** = linear interpolation between the two strikes where the
  sign changes.
- Record **"γ hh:mm @ run spot"**, not the read time. The board shows the run before last (≈5–10 min lag), by design.

### 3.5 Units and comparisons
- Target Delta totals in Cr (the log writes "+2,31,007 Cr"); target GEX in K Cr = γ·OI·S²·0.01/1e7·√(τ/5d); ours in L Cr = γ·OI·S²/1e7 (F1).
  **Compare signs, shares of gross, levels — never magnitudes.**
- **Flip pair** only when the two spots are ≤ ~45 pts apart. Our flip is skipped on 0DTE (not today).
- **Regime split** = ours vs theirs net sign at the same minute.

### 3.6 Scheduling the rounds
- Each round is a `send_later` message; firing arrives as a notification → call `ReadNotifications` first, then act.
- Write the shared instructions once to a local file (e.g. `/home/claude/pe/round_common.txt`: tab ids, coordinates, find strings, log file, counters
  source, rules) and make each scheduled message short: "COMMON instructions in /home/claude/pe/round_common.txt — read and follow; this round = FULL/LIGHT
  …", plus a compact fallback summary in case the file is gone.
- **Rate limit:** about 8 triggers can be created in a burst, then "rate limit reached, try again in ~30 s". Schedule in batches; sleep 30 s between.
- Fire times are UTC (IST − 5:30). Check `list_triggers` before scheduling to avoid duplicates. A late-firing round that overlaps the next one: skip the
  duplicate and say so in the log.

### 3.7 Logging and writing
- Logs are built **locally** (bash heredoc `cat >> file <<'EOF'`, in the working directory, e.g. `/home/claude/pe/`). `project_write` with `local_path`
  must point **inside the working directory** (a scratchpad path is rejected).
- **Naming:** local parts `/home/claude/pe/capture_part_2026-10-19_a.md`, `_b`, … (~1 h each); merged at the close into
  `02_capture_log_2026-10-19.md`. **Hourly backup = `SendUserFile` the finished part (proactive, attach)** — Drive uploads of 30 KB parts were too slow on
  Day 4. Do not `project_write` during the day (space).
- If a write is refused (project full): keep the part locally, **tell the operator once**, don't retry every round, never delete anything.
- Local files are lost if the session's machine is reclaimed; anything important must reach the project or be sent with `SendUserFile`.

### 3.8 Messaging
- `SendUserMessage` only for things he should see now: a new finding, a counter milestone, a problem needing him. 1–5 short lines. No narration.

## 4. What to look for

### 4.1 Settled — keep checking, cheaply
- **#16 BY DESIGN:** settlement % on the **argmax-Γ ΔOI strike**, not the pin. Cumulative **SENSEX 91/91, NIFTY 84/84**. At every Pin read note pin, settlement strike,
  argmax Γ ΔOI; flag any exception at once. On 16 Oct the final post-close state named two strikes (SENSEX PIN 74,500 / settlement 74,000).
- **#4 BY DESIGN (closed 16 Oct); #23 consistent (15 + 16 Oct).** Log READ % and C WALL pairs anyway.
- **Live-row rule:** the newest row shows the **last** reading in its window, spot included ("15:15 · 23,146" was the ~15:29 reading). Use Terminal spot
  for any "at hh:mm" value.

### 4.2 #25/#26 on expiry day
- Capture the whole session log each Pin read; log only closed-row changes. 16 Oct: **108 rank-tag rewrites, 0 value rewrites**; tags are the row-pin's rank
  in the **current** table. Watch whether values change on closed rows on an expiry (Day 3 SENSEX expiry: yes).
- **Post-close:** on 15 and 16 Oct the target's final pin changed **after** the close and was stamped 15:30 (16 Oct NIFTY ↑23,100 ~15:33, SENSEX ↑74,500 ~15:39).
  Read the Pin at **15:31, 15:35, 15:40 and ~15:45**. Score the live 15:31 pin and the post-close pin separately.

### 4.3 Running counters (carry, update every round, print in each Read line)
| counter | at Day-4 close |
|---|---|
| NIFTY flip pairs, ours lower (cumulative since 13 Oct) | **104/104** (ours skipped on 0DTE today → no NIFTY pairs; SENSEX pairs continue) |
| Same-minute regime splits (per day) | Day 3: SENSEX 8, NIFTY 9 · Day 4: SENSEX 4, NIFTY 19 |
| Settlement strike = argmax Γ ΔOI | SENSEX 91/91, NIFTY 84/84 |
| Verdict vs aggressor (Day 4) | NIFTY agree 3 / disagree 15 / flat 2; SENSEX agree 3 / disagree 2 / flat 13 / n/a 1 (|Δ| ≤ 1 % = flat) |
| Pre-reg #4 (09:20–09:45 verdict vs 09:45 → 15:15 direction) | 13 Oct NIFTY right (informal) · 15 Oct 2/2 right · **16 Oct 0/2 (both Bearish, both up)** → 3 right / 2 wrong |
| Closed-row rewrites | Day 3 ~20 (incl. values) · Day 4 108 (tags only); back-dated 3, withdrawn 3, copy-forward 1 |

### 4.4 Settlement-% calibration (the target's one forward number) — scored today
- **16 Oct NIFTY log:** 49 readings, 09:16 → 15:40; strikes 23,100 (09:16, 09:31), 22,900 (10:06–10:25), 23,000 (to 15:31), **23,100 at 17 % post-close**; 10–17 % (±50).
  Today add every reading (time, strike, %, band ±50, = pin?). After the settle: inside / outside per reading, mean stated %, Brier (descriptive); add the row
  to the running table (Day-3 §7.2: 13 Oct NIFTY, 15 Oct SENSEX 2/49 inside, both after the print).

### 4.5 Our board — re-observe (all candidates; none proposed)
- **Close handling (D2-4, D3-9, D4-7):** 15:14–15:30 both boards hold the last continuous value (ADR-022). Ours: "LIVE hh:mm" on the held value ~10 min, then plain
  "SPOT"; γ run stopped at 15:20 (CLOCKS "20 min apart" by 15:40); **no stale strip**; close never shown (16 Oct −27 NIFTY). Today: does SPOT ever show the settle?
- **FUT·BASIS jumps** on non-expiring contracts (D4-8: SENSEX 29 OCT −7.9 → +47.3 in 3 min). Today NIFTY 27 OCT / SENSEX 29 OCT.
- CLOCKS card intermittently absent; corridor word vs read text; pocket word at unchanged sign; read text vs PIN tile; PIN near-ties; 0×0 tab after reconnect.
- Our flip is **skipped on NIFTY today** (expiry, ENH-131): do not count pairs on NIFTY.

### 4.6 Theirs — re-observe
- #19 SENSEX tapes "Loading" (six times on 16 Oct; once with a clock-less stale profile pane). #13 HHI, #17 null pin (not re-checked since Day 2). #27 path markers.
- **Closing states:** 16 Oct "LIVE FEED" through 15:36, "● CLOSED" + "Market closed …" banner first at 15:40 (15 Oct: 15:30). Note the minute today.

## 5. Today's plan (Mon 19 Oct)
1. **Pre-open (before 09:10):** §3.1; read §1; the author's X posts since 16 Oct 15:40 (`from:AshwinBadri2 since:2026-10-16`, Latest; `find` "all tweet text
   bodies in the timeline with their relative times"); pre-open read of both boards (note our SPOT tile: did it pick up the 16 Oct close, 23,146.15?).
2. **09:15–09:45 pre-reg #4 window:** NIFTY and SENSEX Delta verdict, %, READ, aggressor at **09:20, 09:30, 09:45** (exact minutes; schedule first). Note 09:45 spots.
3. **Cadence:** 5 min to ~10:15 → 10 min to 14:30 → **5 min 14:30–15:30** (expiry afternoon) → 15:31, 15:35, 15:40, ~15:45. NIFTY in every round (both boards, Pin +
   Terminal + Delta); SENSEX in alternate rounds.
4. **15:15:** fill pre-reg #4 (Terminal spot at 15:15). **15:30:** the print on both boards; NIFTY settle = official close (confirm from a closing report /
   bhavcopy via WebSearch; the shell cannot reach exchange sites).
5. **Post-close:** full Pin logs both indices; diff vs live captures; CLOSED state; then §7 and §8.

## 6. Expiry routine reminders (NIFTY 0DTE)
- Pin path with times, state, conviction, margin; settlement % and strike each read; walls on both panes; zero-γ; their pin vs ours vs spot.
- Ours: FLIP shows "skipped · expiry day"; record PIN (γ-conc, lead), CORRIDOR, NET Γ share, SPOT label and CLOCKS through the close.
- Pin scorecard rows (06 format): IST · their pin · Δ to settle · our pin · Δ to settle · same? — built from live captures only, never from their log.

## 7. Scoring
- **NIFTY pin scorecard** (06 format) against the official settle; totals (same / ours closer / theirs closer; within ±50; mean |pin − settle|). Score their
  15:31 live pin and the post-close pin separately (§4.2).
- **Settlement-% calibration:** 16 Oct + 19 Oct NIFTY readings vs the settle; update the running table.
- **Pre-reg #4** today; cumulative table 13–19 Oct.
- **Author's scorecard:** his calls since 16 Oct vs outcomes (Day-3 §7.3 format).

## 8. End of day = final report
- Merge parts → `02_capture_log_2026-10-19.md` (send in chat; project only if space allows).
- Write `claude/parity_eval/parity_target_day7_2026-10-19.md` (Day-4 structure §1–§7) **and** the **final report**
  `claude/parity_eval/parity_target_final_report_2026-10-19.md`: what the target is (layers, definitions), what is BY DESIGN vs DEFECT (from `08`), what its
  forward numbers scored (settlement %, pins, pre-reg #4, author), the presentation comparison (Day-4 §8), and **adopt / don't adopt / test** for MERIDIAN, each
  with evidence links (day report § and log time). Candidates only; nothing proposed without his yes.
- Update `08` for anything settled today. Check `project_info` before writes; `grep -i` for the brand; if refused, send the files in chat.
- Short chat summary: outcome, counters, owed.

## 9. Context: state at the Fri 16 Oct close
- **NIFTY 23,146.15 (+0.65 %)** and **SENSEX ~74,729** — the target's 15:31 print; **official close not yet confirmed** (owed). A quiet up day: 22,966 (09:45) → 23,119 held 15:14–15:30.
- Target NIFTY: pin **23,000 from 10:15 to 15:31** (LOCKED 12:00–15:25, conviction 80–88), SHIFTING at 15:31, **23,100 STABLE after the close** (stamped 15:30), settlement
  **17 % within ±50 of 23,100**; zero-γ 23,155; net GEX −345 / strip −1.78K (short at the root); walls C 23,200 / P 23,000. SENSEX: 74,000 all day → 74,500 SHIFTING post-close,
  settlement 6 % within ±100 of 74,000; zero-γ 74,736.
- Ours NIFTY (held 23,119.0): flip 23,089, PIN 23,200 (12.7 %, lead 3.7), net Γ +20.7L long (0.22), corridor 23,000–23,100; SENSEX PIN 75,000, flip 74,389, call wall 76,000.
- Day-4 headlines: pre-reg #4 0/2; #25 narrowed to tag recompute (108, 0 values); two post-close back-dated pin moves; #19 ×6; our close handling confirmed on a
  non-expiry day; basis jumps not expiry-specific.

## 10. Owed / carried (ask the operator only for what needs him)
1. **Official 16 Oct close** (NIFTY, SENSEX) — WebSearch a closing report; if none, ask him once.
2. **SQL (he runs; one block each; names from `merdian_reference.json`):** `07` Q1–Q5b; Day-3 (a)–(d); Day-4 (e) NIFTY 27 OCT / SENSEX 29 OCT futures ticks 09:30–15:40
   on 16 Oct vs spot; (f) γ runs after 15:20 on 16 Oct and the spot each used; (g) our SPOT source 15:14–15:40 on 16 Oct.
3. **IndexedDB export** (`hwcap` / `mvcap`): one JS call each; ask once (approved 16 Oct, not pulled).
4. **Target narrow-width test** (presentation pass): his choice — un-maximise the window, or allow the target in an iframe.
5. NSE participant-wise OI description test (candidate; check WebFetch reach first).
6. Wording candidates awaiting his yes: pocket word; closing-session / stale labels; corridor degenerate state; pin tie state.
7. **Project space:** ~40 KB free on 16 Oct before the close writes; safe deletions are listed in the 16 Oct chat summary.
