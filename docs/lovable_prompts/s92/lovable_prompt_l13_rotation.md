# Lovable prompt — L13 OI rotation: bind `v_oi_rotation_since_open` (S92)

Paste everything below the line into Lovable as ONE message.

---

## Task

The OI tab shows a "ΔOI net" item and ΔOI ticks on the strike ladder. Today these are **computed in the browser**:
`useLadderStrikes` in `src/lib/board.ts` fetches the day's first γ run from `gex_strike_snapshots` and subtracts it.
That is a second implementation of a rule the database already owns.

Replace it with a read of the existing, live database view **`v_oi_rotation_since_open`**, and show what that view
says — including its absent and stale states. The view already exists, anon can already read it, it returns in
~20 ms. **You do not create, change or grant anything in the database.**

## Hard limits — breaking any of these means the change is rejected and reverted

1. **Do not touch the database or Supabase in any way.** No SQL, migrations, tables, views, functions, policies,
   grants, RLS, edge functions, storage. No `supabase/` folder, no `*.sql` file. Do not change the Supabase client.
2. **You may edit only:** `src/lib/board.ts`, `src/pages/Board.tsx`, and files in `src/components/board/`.
   Do not edit any other file: not `src/lib/supabase.ts` / `queries.ts` / `read.ts` / `utils.ts`, not `.env*`,
   `package.json`, any lockfile, `vite.config.ts`, `index.html`, `tsconfig*`, tailwind/eslint config,
   `components.json`, `src/App.tsx`, `roadmap.md`. No new dependencies. No new environment variables.
3. **Exactly one new data read is allowed**, and it must be exactly this shape, in `src/lib/board.ts`:
   ```ts
   supabase.from("v_oi_rotation_since_open")
     .select("symbol, expiry_date, dte, anchor_ts, latest_ts, strike, ce_oi_anchor_qty, ce_oi_latest_qty, ce_oi_delta_qty, ce_presence, pe_oi_anchor_qty, pe_oi_latest_qty, pe_oi_delta_qty, pe_presence, snapshot_age_min, stale_floor_min_used, is_fresh")
     .eq("symbol", s).order("strike", { ascending: true }).limit(1000)
   ```
   in a new hook `useOiRotation(s: Symbol)` with `queryKey: ["board", "rotation", s]`, the file's existing `...opts`,
   and `enabled: s !== "SENSEX"` (SENSEX is not fetched at all).
   **No other `supabase.from(...)`, `.rpc(...)`, `fetch(...)` or `createClient` may be added anywhere.**
4. **Remove the browser recompute.** In `useLadderStrikes`, delete the first-run lookup (the `runsQ` query, the
   `firstRunId` query, `firstRows`, `firstByStrike`, `runCount`) and the `deltaCall` / `deltaPut` fields. Keep the
   hook's first two queries (latest run id, and that run's strikes) exactly as they are.
5. **Do not change any other tab** (Overview, Pin, Gamma, Flows, IV), the summary strip, the read sentence, Home,
   Context, Structure, Health, Settings. On the OI tab, change only the ΔOI item, the ΔOI ticks and their detail text.
6. Keyboard (keys 1–6, ↑/↓), click-to-select and `?tab=oi&sel=oi_delta` URLs keep working.

## What the view is (do not restate it as anything else)

One row per front-expiry strike: OI at the **anchor** (first chain snapshot at or after **09:15 IST** of the
session), OI at the **latest** chain snapshot, and the delta, for CE and PE side by side. The **session follows the
data, not the clock**: overnight and at weekends it shows the last completed session; between ~08:35 and 09:15 on a
trading day it returns **no rows** (no 09:15 anchor yet). It is on the **chain** clock, not the γ clock.

## What to render

**SENSEX: keep it "n/a".** The hook is disabled for SENSEX, no ticks are drawn, and the ΔOI note reads
`ΔOI · n/a (SENSEX · TD-S84-NEW-4)`. (Reason, for the detail text only: SENSEX's 09:15 anchor can come from a stale
vendor row.)

**NIFTY, the "ΔOI net" item** (id `oi_delta`, keep the id):
- **Value:** two signed numbers, calls then puts: `C +x · P +y`, each the sum of that side's `*_oi_delta_qty` over
  rows where that side's presence is `BOTH`, formatted with the existing `oiFmt`, each in its sign hue (`hue()`).
  Do not add them into one total.
- **Sub-line:** `since 09:15 · chain hh:mm` using `latest_ts` in IST. If the IST date of `latest_ts` is not today,
  append ` · session YYYY-MM-DD`. If `is_fresh` is false, append ` · not fresh (age n min)` using `snapshot_age_min`
  rounded to whole minutes. **Never hide the item because it is not fresh.**
- **No rows returned:** value `—` in the dashed `Absent` chip, sub-line `ΔOI · no 09:15 anchor yet`.
- **Caption:** `Open interest added (+) or unwound (−) since the 09:15 anchor, per side, in quantity.`
- **Expiry check:** if the view's `expiry_date` differs from the ladder's `expiry_date`, show the `Absent` chip with
  sub-line `ΔOI · expiry differs (chain dd MMM vs γ dd MMM)` and draw no ticks.

**NIFTY, the ΔOI ticks on the OI ladder:** join view rows to ladder strikes by `strike`. Put tick from
`pe_oi_delta_qty`, call tick from `ce_oi_delta_qty`, on the same sides the ticks use today. A side whose presence is
`ANCHOR_ONLY` or `LATEST_ONLY`, or whose delta is null, gets **no tick** and a small grey `n/c` mark on that side —
**never 0**. A ladder strike with no view row gets no tick.

**Units and words:**
- The unit is **quantity** (shares-equivalent at the current lot size). Never write "contracts" or "lots", and never
  divide by a lot size.
- Never add the words added/unwound as a state label, or "writing", "buying", "long", "short", "build-up",
  "unwinding" as a reading of the number. The sign carries it. No traffic lights, no thresholds, no band words.
- Colour means sign only (`--cool` positive, `--warm` negative), exactly as today.

**Detail panel text for `oi_delta`** — replace the existing `DETAIL.oi_delta` entry with exactly:
- title: `ΔOI since 09:15`
- unit: `quantity since the 09:15 anchor, per side`
- what: `Open interest at the latest chain snapshot minus open interest at the first chain snapshot at or after 09:15 IST, front expiry, per strike, calls and puts separately.`
- how: `Cool ticks rose; warm ticks fell. The value sums each side over strikes present at both times. n/c marks a strike present at only one of the two times — not comparable, never zero.`
- computed: `v_oi_rotation_since_open (ENH-127): ce/pe_oi_latest_qty − ce/pe_oi_anchor_qty. Vendor oi_change is not used.`
- scale: `raw quantity · no band`
- caveat: `An OI change cannot tell writing from buying. Chain clock, not γ clock. SENSEX withheld: its 09:15 anchor can come from a stale vendor row (TD-S84-NEW-4).`
- withIds: keep the existing ones
- src: `v_oi_rotation_since_open · COMMENT live`

## One commit

Message starting `MERIDIAN Marketview: L13 OI rotation reads v_oi_rotation_since_open`. (If your tool names the
commit itself, that is fine — say so.)

## Acceptance checklist (checked against live data before anything goes past staging)

- [ ] Only `src/lib/board.ts`, `src/pages/Board.tsx` and files under `src/components/board/` changed.
- [ ] Exactly one added `supabase.from(...)`, and it is `v_oi_rotation_since_open` with the 17 columns above.
- [ ] The `gex_strike_snapshots` first-run query is gone.
- [ ] Before 09:15 IST on 2026-10-09, NIFTY OI tab "ΔOI net" reads the 2026-10-08 session:
      calls Σ = **+90,945,465**, puts Σ = **+28,841,280** (shown through `oiFmt`), sub-line contains
      `since 09:15 · chain 15:40 · session 2026-10-08 · not fresh`.
- [ ] Largest ticks: **22,500 CE +10,118,875**, **22,400 CE +9,900,800**, **21,000 PE +6,363,890**,
      **22,600 PE −3,433,755** (through `oiFmt`).
- [ ] SENSEX OI tab: ΔOI still `n/a`, note `ΔOI · n/a (SENSEX · TD-S84-NEW-4)`.
- [ ] No "contracts", no "vanna"/"charm", no added/unwound labels; other tabs unchanged; keys and ↑/↓ work; no sideways
      scroll at 375 px.
