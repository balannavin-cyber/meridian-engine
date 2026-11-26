# Lovable prompt — Pin tab wording, round 2 (S107, pin lane order of 25 Nov 18:45)

**Engine lane, authored Wed 2026-11-25 evening. Not run.** Written against the Board repo at `d7642c2` (the live Board). Text only; no SQL needed. Order of the two items is the pin lane's: the untrue statement first.

**Never click Publish in Lovable.** After it is built it needs its own guard round and promote; the s107 guard's fingerprint does not cover it.

## Paste into Lovable

```
Two wording corrections on the Board's Pin tab. TEXT ONLY: no calculation, no data source, no layout, no colour. Change only src/components/board/LadderPanel.tsx and src/pages/Board.tsx. Do not touch public/help/, src/pages/Tape*, src/lib/tapePin.ts, src/lib/tapeClient.ts or src/lib/queries.ts. Do not publish.

1. The Pin's detail panel states a test result as if it were about this Pin. It is not.
   src/components/board/LadderPanel.tsx, DETAIL.p_pin, the caveat. It now reads:
   "Concentration is not a forecast of the close (S74: the pin renders, it does not predict). Levels: P1 — the day's high/low did not land closer to the pin than to random strikes at the same σ (n = 85). Not the net-gamma top strike; see Net peak. Shares here are not comparable with net shares."
   Replace the whole caveat with exactly:
   "Not a forecast of the close. The gross pin has not been tested against outcomes. The earlier tests (S74; P1, n = 85: the day's high/low landed no closer to the pin than to random strikes) were run on the net-gamma top strike, which is now the Net peak, and say nothing about this Pin. Not the net-gamma top strike; see Net peak. Shares here are not comparable with net shares."
   Then, in the same file, DETAIL.p_netpeak: append to its caveat exactly:
   " Tested and found not predictive of the close: S74; P1, n = 85 (the day's high/low landed no closer to it than to random strikes)."
   DETAIL.pin (the strip's Pin entry): replace its caveat with exactly:
   "Not a forecast of the close; the gross pin has not been tested against outcomes. Not the net-gamma top strike; see Net peak. Shares here are not comparable with net shares."

2. On the Pin tab's bars, the gross runner-up's rule is named "#2", and it sits beside that strike's NET rank readout (for example "#15 · 2.3%"), so one row shows two different rank numbers.
   src/pages/Board.tsx, the Pin tab levels (the array that holds id "gconc" named "PIN #1" and id "runner" named "#2", near line 372-375):
   - rename "PIN #1" to "PIN"
   - rename "#2" to "PIN #2"
   Keep the ids. Then in the bars' row readout (pinRows, near lines 366-370) change the visible readout from `#${rk.rank} · ${share}%` to `net #${rk.rank} · ${share}%`, and the full tooltip from `#${rk.rank} · ...% of |net γ| · ...` to `net #${rk.rank} · ...% of |net γ| · ...`.
   In src/components/board/LadderPanel.tsx, the Pin tab ladder legend that reads "PIN / #2 / NET PEAK": change it to "PIN / PIN #2 / NET PEAK".
   In src/pages/Board.tsx, the p_lead caption "#1 leads #2 by ... share points (both outlined)." becomes "The Pin leads its runner-up by ... band-gross share points (both outlined)."

REPORT BACK, THEN STOP
- Files changed (must be exactly those two).
- The three caveats as they now read.
- The level names and the readout template as they now read.
- Every remaining place in src/ where the text "P1" or "n = 85" appears, with file and line.
```

## After the build

- A guard round and a promote with the two proxy build settings (see `mv_lovable_guard_s107_pin.sh` revision 2 for the build lines and the bundle audit). The fingerprint lines must be rewritten for this round.
- The manual: the Pin tab table row for PIN (gross γ) already says the P1 result was measured on the earlier net pin. A manual line for the two labels ("legacy, unvalidated", "experimental") is still owed; it goes into manual v0.7 with this round.
