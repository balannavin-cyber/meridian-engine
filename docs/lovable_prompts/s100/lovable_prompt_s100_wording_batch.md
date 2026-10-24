# Wording batch — Spot tile label, dealer-claim wording (ruling S100-R) — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** Text and one label rule only, in five files. Every string below is
operator-approved (S100-R); use each exactly. No data read, query, layout, colour or style change. Do **not** change any
upper-case Γ anywhere (ruled names stay as they are).

## 1 — `src/pages/Board.tsx`

**1a.** Add this one module-level helper directly above the line that declares the Board page component (the
`function Board…` / `export default function Board…` declaration):

```ts
const istMinutes = (iso: string) => { const d = new Date(new Date(iso).getTime() + 5.5 * 3600_000); return d.getUTCHours() * 60 + d.getUTCMinutes(); };  // S100-R
```

**1b.** Replace exactly:

```tsx
        <Cell id="spot" label={liveSpot ? `Spot · live ${istTime(liveSpot.ts)}` : "Spot"} {...C}
```

with exactly:

```tsx
        <Cell id="spot" label={liveSpot ? (istMinutes(liveSpot.ts) >= 915 ? "Spot · held since 15:15" : `Spot · live ${istTime(liveSpot.ts)}`) : (g?.ts && istMinutes(g.ts) >= 940 ? "Spot · close" : "Spot")} {...C}
```

(915 = 15:15 IST and 940 = 15:40 IST, in minutes after midnight.)

**1c.** In the Flows caption, replace exactly `` `For a +1% move dealers would `` with `` `Under the house sign, for a +1% move dealers would ``
(only that opening; the rest of the template is unchanged).

## 2 — `src/components/board/LadderPanel.tsx`

**2a.** In the `net:` entry, replace exactly

`how: "Positive (cool) means dealers are net long gamma and hedge against moves; negative (warm) means they hedge with moves.",`

with exactly

`how: "Positive (cool) means dealers are net long gamma and hedge against moves; negative (warm) means they hedge with moves. This reading assumes dealers are net long calls and short puts; NSE aggregate participant OI shows that only in some regimes (P2, S94).",`

**2b.** In the `f_hedge:` entry, replace exactly

`what: "What dealers must trade to stay hedged if spot moves, from net Γ at the latest run.",`

with exactly

`what: "What dealers would trade to stay hedged if spot moves, if they hold the house sign (net long calls, short puts — regime-dependent, P2); from net Γ at the latest run.",`

## 3 — `src/pages/Home.tsx`

Replace exactly `q: "What is actually written?",` with `q: "What does open interest show?",`
and exactly `q: "What must dealers trade if spot moves?",` with `q: "What would dealers trade if spot moves?",`.

## 4 — `src/components/NarrativeModal.tsx`

Replace exactly `"Long-γ dealers buy dips and sell rips, compressing realized vol."` with
`"If dealers are long γ, they buy dips and sell rips, compressing realized vol."`
and exactly `"Short-γ dealers chase price, amplifying directional moves."` with
`"If dealers are short γ, they chase price, amplifying directional moves."`.

## 5 — `src/components/AmbientTrajectory.tsx`

Replace exactly `⚠ INTRADAY DRIFT — dealers flipped to {liveN} since the open;` with
`⚠ INTRADAY DRIFT — the regime flipped to {liveN} since the open;` (the rest of the line unchanged).

## Reply with

Each file and each replacement (old → new). If any quoted text does not exist exactly as quoted, change nothing in that
file and say which.

---

## Checks (Claude / operator)

1. Guard: round copy of the s92 guard with line 34's allowlist → `src/pages/Board.tsx|src/components/board/*|src/pages/Home.tsx|src/components/NarrativeModal.tsx|src/components/AmbientTrajectory.tsx`;
   five paths M; no new data reads; no credentials; no vanna/charm; tsc + build clean; net 10 insertions, 9 deletions
   (Board +3 / −2, LadderPanel +2 / −2, Home +2 / −2, NarrativeModal +2 / −2, AmbientTrajectory +1 / −1).
2. Staging read: Board Spot tile `Spot` on a non-trading day (γ run 15:20 Friday — so `Spot · close` cannot show until a
   15:40 γ run exists: a Monday Part C read); every D-string as approved on Board, its drawers and Home.
3. Promote, backup `.bak-3366bf1`, S100-L retention (delete `.bak-1072593`).

---

## Round record

**Wording** approved 2026-10-24 ~17:25 IST (S100-R: A both labels, B D1–D7, C Γ kept). **Lovable** `497a507` "Changes" →
`1aeb000` "Updated board & narrative text"; reply: every quoted string matched and was replaced; no Γ touched.

**Guard** (`~/s100m/mv_lovable_guard_s100r.sh`: s92 guard, line 34 allowlist + Home, NarrativeModal, AmbientTrajectory;
`diff` one line): five paths M; no new data reads, no credentials, no vanna/charm; build clean; staging `1aeb000`;
**5 files, 10 insertions, 9 deletions** = computed.

**Staging read** (18:14–18:17 IST, NIFTY): Home card 4 "What does open interest show?", card 5 "What would dealers trade if
spot moves?"; Net Γ drawer *how* ends with the S94-F sentence; Hedge per 1 % *what* "What dealers would trade … if they
hold the house sign (net long calls, short puts — regime-dependent, P2); from net Γ at the latest run."; Flows caption
"Under the house sign, for a +1% move dealers would sell about ₹2,912 Cr; for −1%, buy about ₹2,912 Cr."; Spot tile
`SPOT` (γ run Friday 15:20 — `Spot · close` needs a 15:40 run: Part C Monday).

**Promoted** 18:19 IST (log `~/s100m/promote_1aeb000.log`): built-bundle counts — `Spot · held since 15:15` 1, `Spot · close` 1,
D6/D7 strings 0; backup `.bak-3366bf1`; `LIVE = BUILD`; bundle `assets/index-BdbC9K5_.js`; S100-L: `.bak-1072593` deleted;
left `.bak-3366bf1`, `.bak-2ee83e1`, `.bak-142c3e6` + 3 `PRE_*`.

**D6 / D7 are dead code:** the old strings were absent from the previous live build too (0) and no file under `src/` imports
`NarrativeModal` or `AmbientTrajectory` — both components are tree-shaken out. The wording is corrected in source;
nothing renders it. TD candidate: remove the two unused components (or wire them, by ruling).
