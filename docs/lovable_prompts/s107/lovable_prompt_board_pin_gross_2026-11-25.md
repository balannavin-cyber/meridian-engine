# Lovable prompt — Board Pin = gross pin, with a "Net peak" line (S107, operator rulings R2/R3 of 2026-11-25)

**Engine lane, authored Wed 2026-11-25. Not run.** Written against the Board repo at `90cb618` (the live Board's source per the pin lane's check of 25 Nov).

## Before the operator runs this prompt

1. `sql/2026-11-25_s107_v_gex_pin_gross.sql` is applied and its checks 4a, 4b, 4c pass. If the view is absent the tiles show "no run"; they never fall back to the old source.
2. The order-flow lane has the note (STREAMS X1). `/tape` is not touched by this prompt.
3. **Never click Publish in Lovable.** Deployment is by the existing box route.

## Paste into Lovable

```
Change what the Board calls "Pin" from the net-gamma top strike to the gross pin, and move pin state and conviction under a second line named "Net peak". Text and data-source changes only. Do not change any calculation that is not named below. Do not add a dependency. Do not touch src/pages/TapeFlowBook.tsx, src/lib/tapePin.ts, src/lib/tapeClient.ts, src/lib/queries.ts or anything under src/pages/Tape*. Do not publish.

BACKGROUND (so the labels are right)
- Today the Pin is rank 1 of the view v_gex_strike_rank. That ranking is on NET gamma per strike, and the Board's text wrongly calls its share "of gross".
- The new Pin is the gross pin, read from a new view v_gex_pin_gross. One row per symbol. Columns: symbol, run_id, ts, expiry_date, dte, spot, pin_strike, pin_share (fraction 0..1), pin_gamma_legs, runnerup_strike, runnerup_share (fraction 0..1), lead_share_pts (already multiplied by 100; null when there is no runner-up), n_ranked, n_in_set, n_oi_no_gamma.
- pin_share is the strike's share of gross gamma over strikes within 5 % of spot. It is NOT comparable with the old net share. Never show the two as the same kind of number.
- The old net top strike keeps existing. It is gex_cycle_history.pin_leader_strike (already read through v_pin_board) and is now called "Net peak".

1. DATA HOOK (src/lib/board.ts)
Add, next to useRepricedFlip:
  export const useGrossPin = (s: Symbol) =>
    useQuery({ queryKey: ["board", "grosspin", s], ...opts, queryFn: latestBySymbol("v_gex_pin_gross", s) });
Keep useStrikeRank, useStrikeRankAll and usePinBoard exactly as they are. Do not change the views they read.

2. BOARD PAGE (src/pages/Board.tsx)
a. Read const gp = useGrossPin(symbol).data as any. Define:
   pin = n(gp?.pin_strike); sh1 = n(gp?.pin_share); sh2 = n(gp?.runnerup_share); lead = n(gp?.lead_share_pts); pinRunner = n(gp?.runnerup_strike); pinTs = gp?.ts.
   These replace the values now derived from rank r1/r2 at lines 152-154 and pinRunner at line 343. Do not compute lead as (sh1 - sh2) * 100 any more; use lead_share_pts.
   Keep the old net values under new names for the Net peak line and the bars: netRank1 = rank.find(strike_rank === 1), netTopShare = n(netRank1?.share_of_abs).
b. Everything that today uses pin for a position keeps using pin (now the gross pin): pinWall (line 155), pinDist (line 345), the ladder level at line 204, the Pin tab levels at lines 365-366.
c. Rename the ladder level names: "γ-CONC" -> "PIN" (line 204) and "γ-CONC #1" -> "PIN #1" (line 365). Keep the ids ("gconc", "runner") unchanged.
d. Strip cell (line 606-608) and its summary item (lines 216-218): label "Pin (gross γ)". Sub: `${(sh1*100).toFixed(1)} % of band gross · lead ${lead.toFixed(1)} pts` plus pinWall when present, plus ` · ${istTime(pinTs)}`. Caption: `${num(pin)} carries the largest gross gamma within 5 % of spot, ${(sh1*100).toFixed(1)}% of that band (dotted rule).` When gp is missing: <Absent word="no run" />, caption "No gross pin for this run.".
e. Pin tab cells (lines 371-397):
   - p_pin: label "Pin (gross γ)", value pin, sub `${(sh1*100).toFixed(1)} % of band gross`, then pin_gamma_legs when it is not "both" (show "call γ only" or "put γ only"), then pinWall, then istTime(pinTs). Remove the side word (dampening/amplifying) from this cell. Caption: `${num(pin)} holds the largest share of gross γ within 5 % of spot, ${(sh1*100).toFixed(1)}%.`
   - p_runner: value pinRunner. Sub: `${(sh2*100).toFixed(1)} % of band gross`. Do NOT show #2/#1 here any more. Caption: `${num(pinRunner)} is second with ${(sh2*100).toFixed(1)}% of band gross.`
   - p_lead: value from lead (lead_share_pts). Sub "#1 − #2, band-gross share points".
   - p_dist: unchanged code, now measured from the gross pin. Caption unchanged.
   - Insert a visible group heading "Net peak" before the cells below, with the note: "The strike with the largest net gamma. Pin state and conviction are computed on it, not on the Pin above."
   - NEW cell p_netpeak (first in the Net peak group): label "Net peak", value num(n(pinLatest?.pin_leader_strike)), sub: `${(netTopShare*100).toFixed(1)} % of |net γ|` when netTopShare is known, then istTime(pinLatest?.ts), then "= Pin" when it equals pin or "≠ Pin" when it differs. Caption: `The net-gamma top strike is ${...}.` Absent word "no history" when pinLatest is missing. levelIds ["netpeak"].
   - p_state: label "Net peak state". Keep value, sub and logic. In the caption replace "Pin stable at" style wording with `Net peak ${word} at ${strike}...`.
   - p_conv: label "Net peak conviction". Keep value and caption; the caption already shows #2/#1, which is the NET ratio; add the word "net" before "#2/#1".
   - p_hhi: label "Net concentration (HHI)". Keep value and logic.
   - "Leader today" / leader stretches block and the p_today cell: retitle "Net peak today" and "Net peak stretches". Keep logic.
   - p_band: leave exactly as it is.
   - p_legacy: leave exactly as it is.
f. Pin tab levels (lines 363-367): add { id: "netpeak", name: "NET PEAK", at: <pin_leader_strike>, style: "dotted" } only when pin_leader_strike is not null and differs from pin.
g. Pin tab bars (pinRows, lines 357-362): they stay on the NET ranking (rankAll). Change only the words: wherever the readout or tooltip says "% of gross", say "% of |net γ|". Give the bar panel the heading "Net γ share by strike". Do not recolour.
h. pinNote (line 415): "net peak state · ..." in place of "pin state · ...".

3. HOME PAGE (src/pages/Home.tsx)
a. Read useGrossPin(symbol). Card 2 ("How settled is the centre?", line 143-146): use pin_strike, pin_share, lead_share_pts. Text: `${num(pin)} holds ${(pin_share*100).toFixed(1)} % of band gross · lead ${lead.toFixed(1)} pts`. BarsPic a = pin_share, b = runnerup_share.
b. Card 4 ("What does open interest show?", line 151-154): pin is the gross pin. Text: `max pain ${num(mps)} · pin ${num(pin)} (gross) · ${sgn(mps - pin, 0)}`.
c. Card 3 ("Can I trust single strikes?", line 147-150): keep it on the NET rank share from useStrikeRank, and change the words to `top strike ${...} % of |net γ|`.

4. THE READ SENTENCE (src/lib/read.ts)
Line 13 and line 19: take pin from useGrossPin(symbol).data?.pin_strike instead of the rank. Line 38: say ", which is also the gross-gamma pin" in place of ", which is also the largest gamma strike". Change nothing else in this file.

5. EXPLAINER COPY (src/components/board/LadderPanel.tsx, DETAIL entries)
- pin and p_pin: title "Pin (gross γ)"; unit "strike · share of band gross"; what: "The strike carrying the largest gross gamma among strikes within 5 % of spot. Gross gamma uses one gamma per strike (the mean of the two vendor gammas, or the one that exists) times call plus put open interest."; computed: "v_gex_pin_gross.pin_strike, pin_share; lead = lead_share_pts."; caveat: add "Not the net-gamma top strike; see Net peak. Shares here are not comparable with net shares."
- p_runner: computed "v_gex_pin_gross.runnerup_strike, runnerup_share."; unit "strike · share of band gross".
- p_lead: computed "v_gex_pin_gross.lead_share_pts = (pin_share − runnerup_share) × 100."
- p_state, p_conv, p_hhi, p_today: prefix the title with "Net peak" as in step 2e and add to each caveat: "Computed on the net-gamma top strike (gex_cycle_history.pin_leader_strike), not on the Pin."
- Add an entry p_netpeak: title "Net peak"; unit "strike"; what "The strike with the largest absolute net gamma at the latest cycle row."; how "When it differs from the Pin, the two constructions disagree about the centre."; computed "v_pin_board.pin_leader_strike (gex_cycle_history)."; scale "—"; caveat "Net gamma depends on both vendor leg gammas agreeing; legacy construction."; withIds ["p_pin", "p_state"]; src "v_pin_board".
- p_dist: add to computed "pin = v_gex_pin_gross.pin_strike".
- Anywhere else in this file that says the Pin is "share of gross |γ|" from v_gex_strike_rank: correct it to the wording above.

6. RULES
- If v_gex_pin_gross returns no row or an error, show the Absent state. Never fall back to v_gex_strike_rank for the Pin.
- The Pin line and the Net peak line each print their own time, because they come from different reads and can be one cycle apart.
- No change to any number's rounding other than as written above.

7. REPORT BACK, THEN STOP
- The list of files changed. It must be exactly: src/lib/board.ts, src/pages/Board.tsx, src/pages/Home.tsx, src/lib/read.ts, src/components/board/LadderPanel.tsx.
- Confirm in one line that TapeFlowBook.tsx and tapePin.ts are unchanged.
- Every place where the text "of gross" still appears, with file and line, and which quantity it describes.
- Anything in this prompt you could not do as written, and what you did instead.
```

## After the build (pin lane or operator)

- Deployed-marker check across **all** `assets/*.js` (Tape, Help and Lab3D are lazy chunks): the strings `of band gross` and `Net peak` are present; `v_gex_pin_gross` is present.
- On the live Board, for each symbol: Pin strike equals `pin_strike` from `select symbol, pin_strike, pin_share, lead_share_pts, ts from public.v_gex_pin_gross;` read at the same time; Net peak equals the latest `pin_leader_strike` in `v_pin_board`.
- Record the switch date in STREAMS (Board pin row) and in the pin monitor's DECISIONS.md.

## Decisions in this prompt that were mine, for the operator and the pin lane to confirm or change

1. The Pin tab **bars stay on net shares**, relabelled. The Board roles have no per-strike gross source; a second wrapper view would be needed for gross bars.
2. **Pin band is untouched** (open item: whether it should follow the gross pin).
3. **Runner-up, lead and distance** move to the gross pin; the **#2/#1 ratio** stays with Net peak conviction.
4. **Home card 3** stays on the net top-strike share, relabelled.
5. The side word (dampening/amplifying) is removed from the Pin cell only, because the gross pin has no sign. No other dealer wording changes (R5).
