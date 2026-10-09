# Lovable prompt — optional 3D view at /board/3d, reading one database view (S92-J)

**Before pasting:** (1) `v_gex_strike_terrain` is applied and Section 4 of
`sql/2026-10-09_s92_v_gex_strike_terrain.sql` passed; (2) run `acl_fingerprint.sql` and keep the result;
(3) note the current `origin/main` SHA as BASE. **After Lovable pushes:** run
`bash ~/mv_lovable_guard_lab3d.sh <BASE>` (this folder's `mv_lovable_guard_lab3d.sh`, installed beside v2),
then `acl_fingerprint.sql` again — both must be clean before `/staging/` is even looked at.

Paste everything below the line into Lovable as ONE message.

---

## Task

Bring back the operator's 3D drill-down page from his earlier experiment (branch `lab-3d`, commit
`78fb26e` in this repository's history: `src/pages/Lab3D.tsx`, `src/lib/terrain.ts`, the `/board/3d`
route and the small "3D" entry links) as an **optional** view. The 2D board stays exactly as it is and
stays the default. The 3D page is reached only from its entry links and loads its 3D code only when opened.

The one big change from the experiment: **the 3D page draws what the database computes; it computes
nothing itself.** The data for the γ terrain and the pain bowl now comes from ONE existing, live database
view, `v_gex_strike_terrain`. The IV fence keeps using the board's existing `useIvTab` hook (no new read).

## Hard limits — breaking any of these means the change is rejected and reverted

1. **Do not touch the database or Supabase in any way.** No SQL, migrations, tables, views, functions,
   policies, grants, RLS, edge functions, storage. No `supabase/` folder, no `*.sql` file. Do not change
   the Supabase client, `.env*`, or any environment variable.
2. **You may edit only:** `src/pages/Lab3D.tsx` (new), `src/lib/terrain.ts` (new), `src/App.tsx` (the route
   only), `package.json` and the lockfile (dependency additions only), `src/pages/Board.tsx` and files in
   `src/components/board/` (the "3D" entry links only). Nothing else — not `src/lib/board.ts`, not any other
   `src/lib/**`, not `vite.config.ts`, `index.html`, `tsconfig*`, tailwind/eslint config, `roadmap.md`.
3. **Dependencies:** add only `three`, `@react-three/fiber`, `@react-three/drei` and `@types/three`. Remove
   or change nothing else in `package.json`.
4. **Lazy loading is mandatory.** In `src/App.tsx` add exactly:
   `const Lab3D = lazy(() => import("./pages/Lab3D"));` (with `lazy`/`Suspense` imported from `"react"`)
   and one route `<Route path="/board/3d" element={<Suspense fallback={null}><Lab3D /></Suspense>} />`.
   **Never `import Lab3D from …` statically** — three.js must not load on the 2D board.
5. **Exactly one new data read, in `src/lib/terrain.ts`, of exactly this shape** (paged, because SENSEX can
   exceed 1,000 rows):
   ```ts
   supabase.from("v_gex_strike_terrain")
     .select("symbol, session_date, session_rank, session_complete, run_id, ts, spot, expiry_date, dte, strike, gex_cr, oi_call, oi_put, writer_pain, max_pain_strike, is_max_pain")
     .eq("symbol", s).order("session_date", { ascending: true }).order("strike", { ascending: true })
     .range(from, from + 999)
   ```
   called in a loop for `from = 0, 1000, …` until a page returns fewer than 1,000 rows, inside
   `useStrikeHistory(s)` with `queryKey: ["terrain", "view", s]` and `staleTime: 5 * 60_000`.
   **No other `supabase.from(...)`, `.rpc(...)`, `fetch(...)` or `createClient` anywhere.** In particular
   the experiment's reads of `trading_calendar` and `gex_strike_snapshots` are **deleted**, and so is
   `getGate()` use in `terrain.ts`.
6. Do not change any 2D tab, the summary strip, Home, Context, Structure, Health or Settings, apart from the
   small "3D" entry links that existed in the experiment (Gamma river, IV smile, OI legend).

## What the view gives you, and what to do with it

`v_gex_strike_terrain`: one row per (symbol, session, strike) for the 14 most recent sessions; per session
the settled run (≤ 15:15 IST); strikes within ±6 % of the newest session's spot — **the strike axis is
already chosen; do not re-window it.** `session_rank` 1 = newest.

- **γ terrain:** height = |`gex_cr`| (scaled to the max in view), hue = sign of `gex_cr` (`--cool` ≥ 0,
  `--warm` < 0). **`gex_cr` NULL means no gamma was measured for that strike: leave a hole, never draw 0.**
  The peak label reads `peak |γ| <value> · unit pending` — the unit of `gex_cr` is not yet defined (E-D1).
- **Pain bowl:** height = `writer_pain`, normalised **per session** (min→max of that session), as in the
  experiment. The max-pain marker per session is the row with `is_max_pain = true`; if no row in the window
  has it, show `max pain <max_pain_strike> · outside window` as text for that session. **Delete the
  client-side pain sum** — the view's `writer_pain` replaces it.
- **Spot path:** `spot` per session. **Session labels:** `session_date` (and `· 0` when `dte` = 0). If
  `session_complete` is false for a session, append `· partial` to its label.
- **IV fence:** unchanged from the experiment, via `useIvTab`.

## Words and symbols

- Write **γ** in lower case everywhere, including the tab label (`γ terrain`, not `Γ terrain`). Do **not**
  apply CSS `uppercase` / `text-transform` to any label containing Greek letters or ∂ — it turns γ into Γ and
  ∂Δ/∂t into ∂Δ/∂T.
- Never write the words vanna or charm. No band words, no traffic lights. Colour means sign only.

## One commit

Message starting `MERIDIAN Marketview: optional 3D view reads v_gex_strike_terrain (S92-J)`. If your tool
names the commit itself, say so.

## Acceptance checklist (checked on /staging/ against SQL before anything goes live)

- [ ] `/board` loads with no three.js in its JavaScript (the guard checks the entry chunk).
- [ ] `/board/3d` opens from the "3D" links; Esc returns to the 2D board.
- [ ] NIFTY and SENSEX: 14 session slices each; the newest slice's strikes match
      `SELECT strike, gex_cr FROM v_gex_strike_terrain WHERE symbol = … AND session_rank = 1`.
- [ ] SENSEX shows holes (not flat zero) where `gex_cr` is NULL.
- [ ] Max-pain markers match `max_pain_strike` per session.
- [ ] No "contracts", no vanna/charm, γ in lower case; no sideways scroll at 375 px.
