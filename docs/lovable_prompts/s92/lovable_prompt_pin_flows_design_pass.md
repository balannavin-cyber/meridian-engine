# Lovable prompt — Pin + Flows design pass (S92)

Paste everything below the line into Lovable as ONE message.

---

## Task

Redesign the **presentation** of two existing Board tabs — **Pin** and **Flows** — so they read as clearly as the
Overview, Gamma, OI and IV tabs. Both tabs already work and show correct live numbers. This is a **layout and visual
hierarchy pass only**. The data, the numbers and every word of explanatory text stay exactly as they are.

Code to read first:
- `src/pages/Board.tsx` — the sections marked `// ---------- Pin tab (S92 ...` and `// ---------- Flows tab (S92 ...`
  compute `pinItems`, `pinRows`, `pinLevels`, `stretches`, `flowItems`, `flowRows`, `flowLevels`, `flowChart`,
  `flowsBadge`, `flowsNote`, `pinNote`.
- `src/components/board/LadderPanel.tsx` — renders the tab row, the value list, the shared strike ladder and the
  detail panel. Its `DETAIL` record holds the explanation text for every item id.
- `src/components/board/StrikeLadder.tsx` — the shared ladder (`oneSided` and `faint` are used by Pin).

## Hard limits — breaking any of these means the change is rejected and reverted

1. **Do not touch the database or Supabase in any way.** No SQL, no migrations, no new tables, views, functions,
   policies, grants, RLS changes, edge functions or storage. Do not open, change or "fix" the Supabase connection. Do
   not create or edit any `supabase/` folder or `*.sql` file.
2. **Do not edit these files at all:** `src/lib/` (every file: `board.ts`, `queries.ts`, `read.ts`, `supabase.ts`,
   `utils.ts`, `mockData.ts`), `.env` and any `.env*` file, `package.json`, `bun.lock`, any lockfile, `vite.config.ts`,
   `index.html`, `tsconfig*.json`, `tailwind.config.*`, `eslint.config.js`, `components.json`.
   Do not add dependencies. Do not add environment variables.
3. **You may edit only:** `src/pages/Board.tsx`, files in `src/components/board/`, and you may **add** new files in
   `src/components/board/`. Nothing else.
4. **No new data reads.** Do not add any `supabase.from(...)`, `fetch(...)` or new hook. Use only the values already
   computed in `Board.tsx`. Do not change how any value is computed, rounded, signed or formatted.
5. **Every value and subtitle string that renders today must render identically** — same digits, same sign
   characters (`−` is U+2212, not `-`), same units, same words. You may move them, regroup them and restyle them.
6. **Every explanatory string stays** — the `DETAIL` entries for `p_*` and `f_*` ids, captions, `pinNote`,
   `flowsNote`, and the absent-state words (`no run`, `no #2`, `no history`, `no band`, `n/a`, `no chain`, the
   `market closed · next …` word). Keep the `Absent` dashed-chip treatment for them.
7. **Do not change any other tab** (Overview, Gamma, OI, IV), the summary strip, the read sentence, Home, Context,
   Structure, Health or Settings.
8. **Keyboard and selection keep working:** keys `1`–`6` switch tabs, `↑`/`↓` move through a tab's items, clicking an
   item selects it and lights its ladder levels, `?tab=pin&sel=p_conv` style URLs still open the right item.
9. One commit, message starting `MERIDIAN Marketview: Pin/Flows design pass`.

## Rules the content itself must keep (these are parity rulings, not style preferences)

- **Never label anything "vanna" or "charm".** The four Flows measures keep their names: `∂Δ/∂t`, `∂Δ/∂σ`, `∂Γ/∂t`,
  `∂Γ/∂σ`, with their existing descriptions.
- **A ∂Γ net value is never shown without its gross beside it, at the same visual weight or close to it.** The ∂Γ pair's
  net is a small residue of large opposing terms. The ∂Δ pair shows net with gross beside it too.
- **The badge `PROVISIONAL — flow-vs-book (D-4) not built` stays visible at the top of the Flows tab** whenever the
  tab is open. It may be restyled, never hidden, collapsed or moved below the fold.
- **No state word without a measured band.** Conviction, lead, HHI and share are numbers only: do not add words such as
  strong/weak/high/low, traffic-light colours, gauges with zones, or thresholds. `NO PIN / SHIFTING / STABLE / LOCKED`
  is the only state vocabulary and it already exists.
- **Colour means sign and nothing else.** `--cool` = positive / dampening / dealers buy; `--warm` = negative /
  amplifying / dealers sell. Calls/puts are greys (`--call`, `--put`). `--sel` (pale gold) is for the current
  selection only. Do not introduce new hues. Every sign is also written (`+` / `−`); colour is never the only carrier.
- **Two clocks.** The Flows second-order figures are on the **chain** clock, the hedge line on the **γ** clock. Keep
  `chain hh:mm` visible on the expiry-leg item, and do not merge the two into one unlabelled time.
- Fonts: IBM Plex Sans / Plex Sans Condensed with `tabular-nums`, as the other tabs.
- Phone (375 px wide): no sideways scroll; groups stack in one column.

## What to improve

**Pin tab**
- Make the **pin-state block** the first thing the eye lands on: one card holding the pin strike, the state word, held
  for (cycles and minutes), and conviction (number, with its `stage 1 · no band (D-6)` note visible, not hidden in a
  tooltip). Runner-up and lead sit with it, because they are what the state is judged on.
- Turn **Leader today** into a compact horizontal timeline strip of the existing `stretches` (each segment = one leader
  stretch, width proportional to its cycle count, labelled with its strike; neutral greys, the current stretch outlined
  in `--sel` only when that item is selected). Keep the existing list in the detail panel.
- Group the remaining items: concentration (HHI + top-5 share), pin band + pin distance, legacy score last and visually
  quieter.
- Keep the share-of-gross ladder exactly as it renders now (bars from the left edge, top 10 full strength, rank > 10
  faint).

**Flows tab**
- Show the **hedge line** larger and earlier: a proper small chart with a labelled zero line, x-axis ticks at −2 %, −1 %,
  −0.5 %, +0.5 %, +1 %, +2 %, the six points labelled `BUY n` / `SELL n` exactly as now, and the dashed L3 flip line with
  its existing caption. It may stay in the detail panel or move into the tab body.
- Present the four measures as a **2 × 2 grid**: ∂Δ/∂t and ∂Δ/∂σ on the first row, ∂Γ/∂t and ∂Γ/∂σ on the second. Each
  cell shows net and gross together and a thin bar of |net| ÷ gross drawn from the existing net/gross ratio (neutral
  grey track, fill in the sign hue). Clicking a cell selects it and switches the ladder bars, as today.
- Keep the expiry-leg item and its "All captured legs" table; keep `front skipped · expiry day` when it appears.

## Acceptance checklist (I will check every line against live data before this goes past staging)

- [ ] Only `src/pages/Board.tsx` and files under `src/components/board/` changed or added.
- [ ] No Supabase/SQL/env/package/config change of any kind.
- [ ] Pin, NIFTY, before 09:15 IST on 2026-10-09 still shows exactly: `22,500`, `9.2 % of gross · dampening · ≡ call OI wall`,
      `SHIFTING`, `held 2 cycles · 10 min · live · unreconciled`, `0.00`, `stage 1 · no band (D-6)`, `22,000`,
      `#2/#1 = 1.00`, `0.0 pts`, `0.046`, `top-5 share 37.4 %`, `22,400–22,700`, `+1.28 %`, `4 changes`,
      `73 cycles · 09:20–15:20`, `37/100`.
- [ ] Flows, NIFTY shows exactly: `SELL 9,211`, `−1 %: BUY 9,211 · +1 %: SELL 9,211`, `−7,933 Cr / 7,933 Cr`,
      `+5,405 Cr / 5,405 Cr`, `−1.7L Cr / 4.8L Cr`, `+63,845 Cr / 3.2L Cr`, `13 OCT`, `chain 15:40`, and the badge.
- [ ] Flows, SENSEX shows `front skipped · expiry day · chain 15:40` and `15 OCT`.
- [ ] The words "vanna" and "charm" appear nowhere in the code or UI.
- [ ] Other tabs unchanged; keys 1–6 and ↑/↓ work; no sideways scroll at 375 px.
