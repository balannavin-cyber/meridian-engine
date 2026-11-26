# Lovable prompt — "legacy, unvalidated" and "experimental" labels (S107, operator rulings R4 and R6 of 2026-11-25)

**Engine lane, authored Wed 2026-11-25. Not run.** Written against the Board repo at `cba0695`. Text only. It can ship with the pin switch or after it; it does not depend on any SQL.

**Never click Publish in Lovable.**

## Paste into Lovable

```
Add two kinds of label to existing figures. TEXT ONLY: no calculation, no data source, no colour scale, no threshold, no layout container and no component signature changes. Do not add a dependency. Do not touch src/pages/TapeFlowBook.tsx, src/lib/tapePin.ts, src/lib/tapeClient.ts, anything under src/pages/Tape*, or public/help/. Do not publish.

LABEL A — the exact words "legacy, unvalidated"
Show these words, in the existing small muted caption style of the component (no new colour, no badge component), next to each of the figures below, every place the figure is displayed. Where the figure has a sub-line or caption, append " · legacy, unvalidated" to it. Where it has only a label, append " (legacy, unvalidated)" to the label.

A1. The gamma regime word and any sentence built from it (LONG_GAMMA / SHORT_GAMMA / NO_FLIP, "long-gamma regime", "short-gamma regime", "mixed regime"):
    - src/components/NarrativeModal.tsx: the headline sentence built at lines 22-27, the "Regime" row at line 41, and the paragraph at line 94 onward.
    - src/marketview/ (state.ts carries it as `regime`): every place sections.tsx or ui.tsx prints that value or a sentence chosen by it.
    - src/components/AmbientTrajectory.tsx: the intraday-drift line near line 563 ("the regime flipped to ..."), and the regime lane's title.
    Do NOT label wcb_regime, breadth regime or ambient_regime: those are different quantities.
A2. The pin-risk score, wherever shown:
    - src/marketview/sections.tsx: the "PIN SCORE" stat at lines 39-40, the Pin risk row at lines 205-285 (score, its "weak pin / moderate pin / strong pin" words, and the timeline legend at line 285).
    - src/marketview/ui.tsx: the PinRiskTimeline title or legend (lines 417-436).
    - src/components/NarrativeModal.tsx: the "Pin risk score" row (line 45) and the sentence at line 97.
    - src/components/AmbientTrajectory.tsx line 553 ("pin NN").
    - src/pages/Positioning.tsx: wherever it renders the score.
    - src/pages/Board.tsx p_legacy (line ~412): change the label to "Legacy pin-risk score (unvalidated)". Leave its sub and caption.
A3. The pin probability and the expansion probability (src/marketview/sections.tsx lines 226-240 and anywhere else `pinProbability` or `expansionProb` is printed).
A4. The dealer hedge-flow simulation (data from v_dealer_flow_sim): the "Hedge per 1 %" tile on the Board's Flows tab (src/pages/Board.tsx f_hedge, line ~538), Home card 5 ("What would dealers trade if spot moves?"), and any marketview section that renders useDealerFlow rows.

LABEL B — the exact word "experimental", for the Board Flip only
B1. src/pages/Board.tsx: the Flip strip cell (line ~592) and the Flip item (lines ~210-212): append " · experimental" to the sub-line. When the sub-line is empty, the sub-line is "experimental".
B2. src/pages/Home.tsx card 1: after the flip text add " (experimental)".
B3. src/components/board/LadderPanel.tsx DETAIL.flip: title "Flip (experimental)". Replace the caveat with exactly:
    "Experimental. Two limits: it has no value on expiry day; and it drops every option leg whose vendor gamma is zero, together with that leg's open interest, so it is not independent of gaps in the vendor's gamma. The effect of that on the level has not been measured. Chain clock. Named states: no flip in grid · skipped on expiry day · carry unmeasurable."
B4. src/lib/read.ts: do not change the read sentence.

RULES
- Do not remove or reword anything else. In particular leave "dampening", "amplifying", "long γ", "short γ" and the Net Γ texts exactly as they are.
- Do not label the Pin, the Net peak tiles, the OI walls, max pain, the Pin band, Net Γ, Gross |Γ| or the top-strike share.
- If a figure listed above is not rendered anywhere, say so; do not add it.

REPORT BACK, THEN STOP
- Files changed.
- A table: for each of A1, A2, A3, A4, B1, B2, B3 — every file:line where you added the label, and the final text of that line's label or caption.
- Any place where one of these figures is displayed that you did NOT label, and why.
- Confirm that no file under src/pages/Tape*, src/lib/tapePin.ts, src/lib/tapeClient.ts or public/help/ changed, and that no line containing a number format, a threshold (25, 50, 75) or a data read was edited.
```

## After the build

- Deployed-marker check across all `assets/*.js`: `legacy, unvalidated` and `experimental` present.
- A look on staging: Home, Board (Overview, Flows, Pin), Positioning, the narrative modal. Each listed figure carries its label; nothing else moved.
- The manual does not describe these labels yet. A manual line is owed in the next manual revision.
