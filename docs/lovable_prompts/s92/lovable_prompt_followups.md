# Lovable follow-up messages — S92 (sent in the same Lovable chat, after the design pass)

Each was sent as one message. Recorded verbatim so the history of what Lovable was told is complete.

## 1. Minus signs and phone hedge labels (after `03e44cc`)

> Two follow-ups, same hard limits as before (only `src/pages/Board.tsx` and `src/components/board/**`; no data, Supabase, env, package or config changes):
> 1. In the Flows tab, the four ratio sub-lines (`net/gross …` under ∂Δ/∂t and ∂Δ/∂σ, `ratio …` under ∂Γ/∂t and ∂Γ/∂σ) print negative values with a plain hyphen. Render the minus as `−` (U+2212), like every other value on the board. Change only the sign character: same digits, same two decimals, positives unchanged.
> 2. On phone width (375 px), make the hedge-chart labels (the BUY/SELL point labels, the % ticks, the zero-line and flip-line captions) legible: at least 10 px rendered. Thin the tick labels if they collide, but keep all six points labelled. No sideways scroll.
> Do not change anything else.

## 2. Ruled names rendered through CSS `uppercase` (after `5a66e1e`)

> One fix, same hard limits as before (only `src/pages/Board.tsx` and `src/components/board/**`; nothing else).
> In the Flows 2 × 2 grid, the cell headings (`∂Δ/∂t · per day`, `∂Δ/∂σ · per vol pt`, `∂Γ/∂t · per day`, `∂Γ/∂σ · per vol pt`) use the `uppercase` class, so the browser renders them as `∂Δ/∂T`, `∂Δ/∂Σ`, `∂Γ/∂T`, `∂Γ/∂Σ`. These are ruled names and must render exactly as written. Remove `uppercase` from those four headings, or wrap the `∂…/∂…` symbol part in a `normal-case` span so only the `· per day` / `· per vol pt` part is capitalised. Check that no other Greek or math symbol on the Pin or Flows tabs sits inside an `uppercase` element. Do not change anything else.

(The operator separately asked Lovable to remove the tab numbers in the same round.)

## 3. Remove the 3D experiment from `main` (after the guard failed on `78fb26e`; work first saved as branch `lab-3d`)

> Remove the 3D view work from this branch. It is saved separately and will come back later. Delete `src/pages/Lab3D.tsx` and `src/lib/terrain.ts`. Remove the Lab3D route and import from `src/App.tsx`, and any link or "3D view" panel or button added for it in `src/pages/Board.tsx` or `src/components/board/**`. Remove `three`, `@react-three/fiber`, `@react-three/drei` and any other packages added for it from `package.json`, and let the lockfile update to match. Keep everything else exactly as it is now: the Pin/Flows layout, the ∂-heading and γ fixes, the minus signs, the tab-number removal. Change nothing else.
