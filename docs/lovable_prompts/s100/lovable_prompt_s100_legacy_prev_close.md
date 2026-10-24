# Legacy pages — previous close and SPOT tile from the same sources as Board (ruling S100-N) — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** Data wiring only, two files in `src/marketview/`. No new database
query (it reuses three hooks Board already uses), no wording, label, style or layout change.

## Context

The SPOT tile in the legacy `SnapshotStrip` (Context / Structure pages) measures its change against
`market_spot_session_markers.prev_close_spot` of the newest marker row. That row is the *previous* session's until about
16:10 IST, so its `prev_close_spot` is the close **two sessions back** for the whole trading day (10-12 09:11 IST:
+392.1 shown, the real move +103.5). Board and Home already take the previous close from `useOpenGap(...).prevClose`
(the prior session's 16:00 settled close) and the headline spot from `useLiveSpot` (the 1-min spot, γ-run spot as the
fallback). Make the legacy strip do the same.

## Change 1 — `src/marketview/state.ts`

1. Add one import line after the existing `import { spotFromMarker, formatDTE } from "./ui";`, importing
   `useSessions`, `useOpenGap` and `useLiveSpot` **from the same module `src/pages/Board.tsx` imports them from**
   (`@/lib/board` if that is where they are declared):

```ts
import { useSessions, useOpenGap, useLiveSpot } from "@/lib/board";  // S100-N
```

2. Replace exactly these four lines:

```ts
  const spot = (g.spot ?? spotFromMarker(marker.data) ?? 0) as number;
  const prevClose = (marker.data?.prev_close_spot ?? null) as number | null;
  const changeAbs = prevClose && spot ? spot - prevClose : 0;
  const changePct = prevClose && spot ? ((spot - prevClose) / prevClose) * 100 : 0;
```

with exactly these:

```ts
  const spot = (g.spot ?? spotFromMarker(marker.data) ?? 0) as number;  // γ-run spot: levels stay measured against it
  // S100-N: previous close and SPOT tile from the same sources as Board / Home (prior session's 16:00 close; live 1-min spot)
  const sess = useSessions();
  const og = useOpenGap(symbol, sess.data?.session ?? null, sess.data?.prev ?? null).data;
  const live = useLiveSpot(symbol).data ?? null;
  const headSpot = (live?.spot ?? spot) as number;
  const prevClose = (og?.prevClose ?? null) as number | null;
  const changeAbs = prevClose && headSpot ? headSpot - prevClose : 0;
  const changePct = prevClose && headSpot ? ((headSpot - prevClose) / prevClose) * 100 : 0;
```

3. In the returned object (the line that begins `symbol, strikeStep, expiry, dte, spot, prevClose, changeAbs, changePct,`)
   add `headSpot,` immediately after `spot,`. Change nothing else in that line.

## Change 2 — `src/marketview/sections.tsx`

In `SnapshotStrip`, in the `"SPOT"` cell only, replace exactly:

```tsx
    { label: "SPOT", value: s.spot ? fmtNum(s.spot) : "—",
```

with:

```tsx
    { label: "SPOT", value: s.headSpot ? fmtNum(s.headSpot) : "—",  // S100-N
```

Leave the `"MAX γ"` cell and every other use of `s.spot` unchanged (those are levels measured against the γ-run spot).

## Constraints

No `supabase.` line added, edited or removed; no other file; no label, wording, colour or layout change; do not touch
`market_spot_session_markers` use anywhere else (`useSpotMarker` stays — `spot` still falls back to it).

## Reply with

The two files changed and each replacement (old → new). Confirm the import path you used and that it is the one
`Board.tsx` uses. If any quoted line does not exist exactly as quoted, change nothing and say which.

---

## Checks (Claude / operator)

1. Guard (round copy, allowlist `src/marketview/state.ts` and `src/marketview/sections.tsx`): two paths M; no new data
   reads; no credentials; no vanna/charm; tsc + build clean.
2. Staging read, same moment, both symbols: the Context page SPOT tile value and change equal Board's Spot cell value and
   change (both = live 1-min spot or, when it is > 10 min old, the γ-run spot, minus the prior session's 16:00 close);
   the expected figures computed from the database at the read.
3. Promote as S100-M (a), backup `.bak-1072593`, S100-L retention (delete the oldest `.bak-`).

---

## Round record

**Lovable** ~12:55 IST: `ced1acc` "Changes", `142c3e6` "Fixed spot field in SPOT cell"; reply: the four replacements as
quoted, import from `@/lib/board` (the module `Board.tsx` uses), no `supabase.` line touched.

**Guard** (`~/s100m/mv_lovable_guard_s100n.sh`: s92 guard, line 34 allowlist → the two `src/marketview` files; `diff`
one line): `M src/marketview/sections.tsx`, `M src/marketview/state.ts`; no new data reads, no credentials, no
vanna/charm; tsc + build clean; staging `142c3e6`; **2 files, 12 insertions, 6 deletions** = the prompt's edits computed
(state.ts +11 / −5, sections.tsx +1 / −1).

**Staging read** (operator's Chrome, Sat 12:57–13:00 IST): SENSEX Context SPOT 72,894.95 −354.44 (−0.48 %) = Board Spot
72,895.0 ▼−354.4 · −0.48 % (prev 73,249); NIFTY 22,516.4 −171.25 (−0.75 %) = 22,516.4 ▼−171.3 · −0.75 % (prev 22,688).
**Rule 0 caveat:** on a non-trading day the newest marker row's `prev_close_spot` equals the 16:00 close and no live
1-min spot exists, so old and new code agree — this read cannot fail for the reason of the change. The discriminating
read is a trading day before ~16:10 IST (Part C, Monday 10-26).

**Promoted** ~12:59 IST from `142c3e6` (operator's run; its output not pasted — reconstructed from the box at 16:29 IST:
`.bak-1072593` present with live's 12:31 IST mtime, `.bak-c81b700` deleted, 8 entries, live and `/tmp/mv-live-build`
both 07:29 UTC); a second run at 16:28 IST refused at "backup path exists" before any write. Live bundle
`assets/index-BeRqvGjW.js`. **Live read** 16:30 IST NIFTY Context: 22,516.4 −171.25 (−0.75 %), equal to the staging read.
