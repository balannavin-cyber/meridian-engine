# Lovable prompt — S96 flow-vs-book badge on the DEX Net tile (S96-E B3, `v_dex_flow_vs_book`)

> Paste everything below the line into Lovable. Base: `meridian-connect` `62f5c55` (live).
> Guard: `bash ~/mv_lovable_guard.sh 62f5c55 v_dex_flow_vs_book` (S92 v2, one named read).
> The guard counts ADDED lines containing `supabase.from("v_dex_flow_vs_book")` and requires exactly one, so §1
> rewrites the existing read as ONE line (`.from(...)` and `.select(...)` together); the old two-line form is
> removed. That is the same single read, extended — not a second one.
> ACL fingerprint before and after against the S96 round baseline (`relations 348 c56612ad…`,
> `anon_public_privs 254 e93833fd…`, `rls_policies 28 d16e21d6…`, `anon_writable_objs 0`).
> Rulings: S96-E (badge columns, B1/B2), B3 wording approved by the operator 2026-10-12 03:59 IST (strings 1–8,
> PRE_OPEN string dropped), S96-A D3 (L7/L8 badge amended, not retired), S96-C (Lovable owns form, not meaning).

---

**Add the flow-vs-book badge to the DEX Net tile on the Flows tab, change one existing badge string, and fix the
loading-state line. You own the visual form (chip shape, placement within the Net tile, colour). You do NOT own the
data, the words or the rules below — follow them exactly.**

**Change ONLY:** `src/lib/board.ts`, `src/pages/Board.tsx`, files under `src/components/board/`. Do not touch any
other file, dependency, config, env, SQL or Supabase setting. Do not change any existing item, label or string
except where §4 says so. Never use the words "vanna" or "charm". Copy every quoted string EXACTLY, including `·`,
`—` and `Δ`.

## 1. Data — extend the existing `useDexFlow` hook in `src/lib/board.ts`

Do NOT add a new hook or a new query. In `useDexFlow`, replace the two lines

```ts
      const { data, error } = await supabase.from("v_dex_flow_vs_book")
        .select("…the existing column list…")
```

with ONE line: the same `supabase.from("v_dex_flow_vs_book")` immediately followed by `.select(` on the same line,
whose column list is the existing list with `, flow_book_badge, flow_book_abstain_code` appended at the end. Keep
`.eq("symbol", s).order("strike", { ascending: true }).limit(1000)` as it is. After the change the file must contain
`supabase.from("v_dex_flow_vs_book")` exactly once.

In the row mapping add two fields (keep every existing field):

```ts
        badge: (r.flow_book_badge ?? null) as "SAME" | "OPPOSITE" | "ABSTAIN" | null,
        abstainCode: (r.flow_book_abstain_code ?? null) as "PRE_OPEN" | "UNTRADED" | "ZERO_NET" | "DELTA_SET" | null,
```

Both values are the same on every row of a symbol (the database computes them per symbol). Read them from the first
row. Do not compute, infer or default a badge anywhere in the client: if `badge` is `null`, draw nothing.

## 2. When the badge area is drawn (fixed)

Only on the **DEX Net tile**, and only when the bricks are drawn (the existing §2 condition of the bricks round: flow
rows present, every row `window === "SESSION"`, `settledTs` and `expiry` equal to the `useDexBook` front leg). When
the bricks are not drawn, draw no badge and no reason line. Not on the Call or Put tiles, not on the ladder.

## 3. The badge (fixed — the form is yours)

- `badge === "SAME"` → a chip with string 4.1.
- `badge === "OPPOSITE"` → a chip with string 4.2.
- `badge === "ABSTAIN"` → **no chip** (the slot is empty), and one small reason line from 4.3 chosen by
  `abstainCode`. If `abstainCode` is `PRE_OPEN` or anything not listed in 4.3, draw nothing.
- The chip is neutral in colour (it is not a signal, buy, sell or warning). Do not use green/red for SAME/OPPOSITE.
- Do not compute or show any number in or beside the chip.

## 4. Words — exact strings

**4.1** SAME chip: `` `flow since ${istTime(anchorTs)} · same sign as book` ``

**4.2** OPPOSITE chip: `` `flow since ${istTime(anchorTs)} · against book` ``

`anchorTs` is the same value the existing tile sub-line (`from … at pre-open OI · … since hh:mm`) uses.

**4.3** Reason line when `badge === "ABSTAIN"`:
- `UNTRADED` → `no badge · untraded OI on this snapshot`
- `ZERO_NET` → `no badge · a net is zero`
- `DELTA_SET` → `no badge · sign depends on the delta used`

**4.4** `DETAIL` in `LadderPanel.tsx` — append to the existing `how` of `f_dex_net` only (change nothing else):

`" Badge: shows only whether flow and book agree in sign. Says nothing about what happens next — M-P7 tested that it can speak, not that it predicts."`

**4.5** Replace the existing badge text `PROVISIONAL — flow-vs-book (D-4) not built` (wherever it appears, same
element, same styling) with:

`flow-vs-book shown on unclassified ΔOI; classification (D-4) not built`

**4.6** Loading state. While `useDexFlow` (or `useDexBook`) for the symbol is still loading, show
`flow · loading` in place of the absent line on the DEX tiles. `no flow before 09:15` and
`flow · different run — not drawn` keep their existing meanings and are shown only once the queries have returned.

Do NOT change the bricks, their captions, S*, the L7/L8 tiles' numbers, or any other tile.

## Reply with

The files changed and what you changed in each. Confirm `src/lib/board.ts` contains
`supabase.from("v_dex_flow_vs_book")` exactly once, on one line together with `.select(`, and that no other file or
existing string changed except §4. If any part cannot be applied as written, change nothing and say which part.

---

## Staging read (operator, after the guard PASS) — figures to read against

Until the 2026-10-12 pre-open rows land (~08:30 IST) the view carries the 2026-10-09 settled session (15:10:07);
S96-E 4h / 4i on it (computed in the database, matched by the M-P7 scorer):

| symbol | `flow_book_badge` | code | flow net v / p | book net v / p |
|---|---|---|---|---|
| NIFTY | SAME | — | −87,565 / −93,544 | −8,289 / −26,436 |
| SENSEX | SAME | — | −8,524 / −10,568 | −3,200 / −5,896 |

So both Net tiles must show the 4.1 chip, with the same `hh:mm` as that tile's existing sub-line, and no reason line.
The L7/L8 badge must read 4.5 exactly. On a hard reload the DEX tiles may show `flow · loading` briefly and must
never show `no flow before 09:15` while the queries are pending. After ~08:30 and until the tape moves after 09:15
the join guard returns no rows: then `no flow before 09:15` and no badge is the correct board.

---

## Round record

**Wording** approved by the operator 2026-10-12 03:59 IST (strings 1–8; PRE_OPEN string dropped before approval —
bricks are never drawn before 09:15, so the code cannot reach a visible slot). **Base `62f5c55` → live `c81b700`.**

**Fingerprint** pre-round 04:07 and after-round 04:46 IST identical on all nine rows, and identical to the S96 round
baseline: `relations 348 c56612ad…`, `anon_public_privs 254 e93833fd…`, `anon_writable_objs 0`, `public_functions 40
5d8cd7f8…`, `rls_policies 28 d16e21d6…`, `default_privileges 27 9db86164…`, `schemas 10 2a889318…`, `public_triggers 0`,
`anon_role 1 c506ff14…` (S96-D / S96-E replaced a view body only; no ACL or relation change).

**Lovable's first reply** applied §1–§4: the one read rewritten as one line with the two columns appended, `badge` /
`abstainCode` in the mapping, the chip / reason line on the Net tile only and only with the bricks, 4.4 appended to
`f_dex_net` `how`, 4.6 loading line. It again predicted no bricks "on Sunday night" — wrong: the views carried the 10-09
SESSION run. It asked whether the four sensitivity-tile explanations (∂Δ/∂t, ∂Δ/∂σ, ∂Γ/∂t, ∂Γ/∂σ), which begin with the
same `PROVISIONAL — flow-vs-book (D-4) not built`, should change too, and left them alone.

**§4.5 was a drafting error and was reverted in the round.** That badge is the L7/L8 flow-vs-book deviation (D-4). What
P7a puts on the board is DEX flow; flow-vs-book for ∂Δ/∂σ and ∂Δ/∂t is **P7b, not built**, so the amended text would have
claimed it. Operator agreed; follow-up (pasted verbatim):
> One revert, nothing else: put the bordered badge on the Flows tab back to its exact previous text `PROVISIONAL —
> flow-vs-book (D-4) not built` (same element, same styling). Leave the four sensitivity-tile explanations unchanged,
> as you did. Change no other file, string or behaviour. Reply with the file changed.

The S96-A D3 amended badge text is **owed to the P7b round**, with the four explanation boxes.

**Guard** `mv_lovable_guard.sh 62f5c55 v_dex_flow_vs_book`: PASS at `c81b700` — four paths, all M (`LadderPanel.tsx`,
`PinFlowsBody.tsx`, `board.ts`, `Board.tsx`), exactly one added read of the view (the one-line rewrite), no other reads,
no credentials, no vanna/charm, tsc + build clean; 4 files, 24 insertions, 9 deletions.

**Staging read** (Claude, operator's Chrome, `/staging/` at `c81b700`): NIFTY Net chip `flow since 08:30 · same sign as
book`, SENSEX `flow since 08:35 · same sign as book` — each with its own tile sub-line's time; no reason line; no chip on
Call / Put / ladder; L7/L8 badge unchanged; 4.4 sentence in the Net `how` after the bricks sentence; bricks values
unchanged from the S96-C read (NIFTY −8,289 / +79,275 / −87,565; SENSEX −3,200 / +5,324 / −8,524; ΔOI gaps 21,710 / 140).
**Loading state:** a fresh load in a hidden frame sampled every 25 ms until the chip appeared (2.6 s) never showed
`no flow before 09:15` (the defect) and also never showed `flow · loading` (the data arrived before the tab rendered), so
the screen could not prove the new branch; the code does — `Board.tsx:450` tests `dflQ.isLoading || dexQ.isLoading`
before the `!dfSession` branch.

**Promoted** 04:49 IST from the checked commit, no pull, in a refusing subshell (HEAD = `c81b700`, no tracked changes,
backup path absent, tsc, build rooted at `/assets/`): backup `/var/www/marketview.bak-62f5c55`; `/tmp/mv-live-build` →
`/var/www/marketview/`, `diff -rq` clean, bundle `assets/index-BgpGiutv.js`. **Live read** in Chrome: bundle
`index-BgpGiutv.js`; both symbols show the SAME chip with 08:30 / 08:35, the three sub-lines equal to staging, L7/L8 badge
unchanged, no `no flow before 09:15`, no reason line.
