# Lovable prompt — S96 DEX flow as bricks on the Flows tab (P7a, `v_dex_flow_vs_book`)

> Paste everything below the line into Lovable. Base: `meridian-connect` `858cb46` (live).
> Guard: `bash ~/mv_lovable_guard.sh 858cb46 v_dex_flow_vs_book` (S92 v2, one named read).
> ACL fingerprint before and after against the S96 baseline (`relations 347 a3cf4ff8…`,
> `anon_public_privs 253 a0b87376…`, `rls_policies 28 d16e21d6…`, `anon_writable_objs 0`).
> Rulings: S96-A (flow numbers only, no badge), S96-C (bricks; remembered value from the DB; Lovable
> owns form, not meaning). Every NEW string in §4 needs the operator's yes before this is pasted.

---

**Show today's DEX flow on the Flows tab as bricks on the three existing DEX tiles and on the ladder.
You own the visual form (shape, shades, spacing, layout within the DEX group). You do NOT own the data,
the words or the rules below — follow them exactly.**

**Change ONLY:** `src/lib/board.ts`, `src/pages/Board.tsx`, files under `src/components/board/`.
Do not touch any other file, dependency, config, env, SQL or Supabase setting. Do not change any
existing item, label or string except where §4 says so. Never use the words "vanna" or "charm". Copy
every quoted string EXACTLY, including `−` (U+2212) and `·`.

## 1. Data — one new hook in `src/lib/board.ts`, directly after `useDexBook`

It must contain `supabase.from("v_dex_flow_vs_book")` exactly once and no other new `supabase.` call.
No date or ts filter: the view decides session and clocks. A NULL stays `null` (a gap), never 0.

```ts
/** P7a: DEX flow since the pre-open beside the book, front leg, settled run (S96-A, S96-C). */
export function useDexFlow(s: Symbol) {
  return useQuery({
    queryKey: ["board", "dexflow", s], ...opts,
    queryFn: async () => {
      const { data, error } = await supabase.from("v_dex_flow_vs_book")
        .select("symbol, expiry_date, anchor_ts, settled_ts, flow_window, strike, call_dex_cr, put_dex_cr, net_dex_cr, call_preopen_dex_cr, put_preopen_dex_cr, net_preopen_dex_cr, call_flow_cr, put_flow_cr, net_flow_cr, leg_call_dex_cr, leg_put_dex_cr, leg_net_dex_cr, leg_call_preopen_dex_cr, leg_put_preopen_dex_cr, leg_net_preopen_dex_cr, leg_call_flow_cr, leg_put_flow_cr, leg_net_flow_cr, leg_gap_d_oi_qty, leg_no_anchor_oi_qty, leg_no_anchor_dex_cr")
        .eq("symbol", s).order("strike", { ascending: true }).limit(1000);
      if (error) throw error;
      const nz = (v: any) => (v == null ? null : Number(v));
      return ((data ?? []) as any[]).map((r) => ({
        strike: Number(r.strike), expiry: r.expiry_date as string, anchorTs: r.anchor_ts as string,
        settledTs: r.settled_ts as string, window: r.flow_window as string,
        now: { call: nz(r.call_dex_cr), put: nz(r.put_dex_cr), net: nz(r.net_dex_cr) },
        pre: { call: nz(r.call_preopen_dex_cr), put: nz(r.put_preopen_dex_cr), net: nz(r.net_preopen_dex_cr) },
        flow: { call: nz(r.call_flow_cr), put: nz(r.put_flow_cr), net: nz(r.net_flow_cr) },
        legNow: { call: nz(r.leg_call_dex_cr), put: nz(r.leg_put_dex_cr), net: nz(r.leg_net_dex_cr) },
        legPre: { call: nz(r.leg_call_preopen_dex_cr), put: nz(r.leg_put_preopen_dex_cr), net: nz(r.leg_net_preopen_dex_cr) },
        legFlow: { call: nz(r.leg_call_flow_cr), put: nz(r.leg_put_flow_cr), net: nz(r.leg_net_flow_cr) },
        legGapDoi: nz(r.leg_gap_d_oi_qty), legNoAnchorOi: nz(r.leg_no_anchor_oi_qty), legNoAnchorDex: nz(r.leg_no_anchor_dex_cr),
      }));
    },
  });
}
```

## 2. When bricks are drawn (fixed)

Draw bricks only when ALL hold; otherwise draw the existing tiles and bars exactly as today and show
the §4 "absent" line:
- the flow hook returned rows for the symbol;
- every row has `window === "SESSION"`;
- its `settledTs` and `expiry` equal those of the existing `useDexBook` front leg (`dex0`). If they
  differ, the two views are on different runs: no bricks.

The tile's big number stays the book value the tile shows today (from `useDexBook`). Do not replace
it with a flow number.

## 3. The brick rule (fixed — the form is yours)

For each of the three tiles (net, call, put) take two numbers from the flow hook's leg totals:
`now = legNow[k]`, `pre = legPre[k]`. For each ladder strike take `now[k]` and `pre[k]` of that strike's
row, k = the selected layer.

- **One scale** for all three tiles (the largest |now| or |pre| among the three); one scale for the
  ladder (the largest |now| or |pre| among the drawn strikes). Never rescale one tile on its own.
- Draw from zero. Three marks, nothing else:
  - **held** = the part that is in both `[0, pre]` and `[0, now]` → **solid**, in the sign colour;
  - **added** = the part of `[0, now]` not in `[0, pre]` → **lighter** shade of the same sign colour;
  - **removed** = the part of `[0, pre]` not in `[0, now]` → **outline only** (dashed or similar), in
    `pre`'s sign colour.
  - When `now` and `pre` have opposite signs, held is empty: added runs 0 → now, removed runs 0 → pre,
    on opposite sides of zero.
- Sign colour = the existing `hue()` convention (positive cool, negative warm).
- This is geometry only. Do not compute or display any other total, sum, ratio or percentage.
- A `null` `now` or `pre` is a gap: draw the existing `·` gap marker, never a zero-length brick.

## 4. Words — exact strings

**4a. Tile sub-line, second line** (keep today's `dexSub` line as the first line), only when bricks are
drawn, for tile k:

`` `from ${fmtCr(legPre[k])} at pre-open OI · ${fmtCr(legFlow[k])} since ${istTime(anchorTs)}` ``

**4b. Absent line** (instead of 4a) when bricks are not drawn:
- before the session's flow exists (no rows, or `window !== "SESSION"`): `no flow before 09:15`
- rows exist but run/expiry differ from the book: `flow · different run — not drawn`

**4c. Gap and outside-split line**, in each DEX tile's caption, appended to today's caption, only when
bricks are drawn:

`` ` ${num(legGapDoi)} qty of ΔOI has no published delta and is not counted; this does not say who bought or wrote.` ``
and, only when `legNoAnchorOi > 0`:
`` ` ${num(legNoAnchorOi)} qty has no pre-open OI and sits outside the split.` ``

**4d. `DETAIL` (in `LadderPanel.tsx`) — append to the existing `how` of `f_dex_net`, `f_dex_call`,
`f_dex_put`** (change nothing else in those entries):

`" Bar: solid = held since the pre-open, light = added, dashed outline = removed, on one scale. \"from x at pre-open OI\" is the pre-open open interest valued at today's delta, so the change is open interest only, not repricing."`

**4e. Append to the existing `scale` of the same three entries:**

`" Flow is itself a partial cancellation: |net|/gross median 0.27 NIFTY, 0.19 SENSEX (31 / 28 sessions). Read the sign."`

**4f. Append to the existing `computed` of the same three entries:**

`" Pre-open and flow: v_dex_flow_vs_book (pre-open = the session's first front-expiry snapshot before 09:15 IST; flow = delta × ΔOI × spot ÷ 1e7 at the settled run)."`

**4g. Ladder note** (`flowsNote`), when a DEX layer is selected and bricks are drawn:

`` `bars · ${dexName[dexLayer]} · held / added / removed since ${istTime(anchorTs)} · settled ${istTime(dex0.settledTs)}` ``

Do NOT change the `PROVISIONAL — flow-vs-book (D-4) not built` badge, the L7/L8 tiles, S*, or any
other tile.

## Reply with

The files changed and what you added in each. Confirm `src/lib/board.ts` contains
`supabase.from("v_dex_flow_vs_book")` exactly once and no other file or existing string changed except
the §4 appends. If any part cannot be applied as written, change nothing and say which part.

---

## Staging read (operator, after the guard PASS) — figures to read against

The views show the 2026-10-09 settled session until the 2026-10-12 pre-open rows land (~08:30 IST), so
the staging read can be done against these SQL figures (4d / 4f, S96):

| tile | now (book) | from … at pre-open OI | since 08:30 / 08:35 |
|---|---|---|---|
| NIFTY net | −8,289 | +79,275 | −87,565 |
| NIFTY call | +87,880 | +119,321 | −31,440 |
| NIFTY put | −96,170 | −40,046 | −56,124 |
| SENSEX net | −3,200 | +5,324 | −8,524 |
| SENSEX call | +19,138 | +12,659 | +6,479 |
| SENSEX put | −22,338 | −7,335 | −15,003 |

NIFTY gap ΔOI 21,710 qty; SENSEX 140 qty; no-anchor 0 on both. NIFTY net and SENSEX net must both
show a **zero crossing** (held empty, added on the negative side, removed outline on the positive side).

---

## Round record (S96, 2026-10-11)

**Wording** approved by the operator 20:01 IST as drafted (§4a–4g). **Base `858cb46` → live `62f5c55`.**

**Fingerprint** (pre-round 20:03, after-round 20:21, final 20:31) identical on all nine rows:
`relations 348 c56612ad…`, `anon_public_privs 254 e93833fd…`, `anon_writable_objs 0`, `public_functions 40
5d8cd7f8…`, `rls_policies 28 d16e21d6…`, `default_privileges 27 9db86164…`, `schemas 10 2a889318…`,
`public_triggers 0`, `anon_role 1 c506ff14…`. (Versus the 17:55 S96 baseline only `relations` / `anon_public_privs`
moved: +1 each, the `v_dex_flow_vs_book` apply.)

**Lovable's first reply** added `useDexFlow` verbatim, bricks on the three tiles and the ladder, a new
`src/components/board/Brick.tsx`, and the §4 appends. It predicted the absent line for a Sunday; wrong — both views
carried the 10-09 SESSION run, and staging drew bricks. Two choices of its own were reported:
- null `leg_gap_d_oi_qty` shown as "—" → **corrected**: omit the sentence;
- a ladder strike with no flow row left blank → **corrected**: draw `·` (follow-up 1, verbatim below).

Follow-up 1 (operator pasted):
> Two fixes, nothing else: 1. In StrikeLadder.tsx (bricks mode): when a ladder strike has no flow row, or its now or
> pre-open value is null, draw the existing "·" gap marker in that row — never an empty row and never a zero-length
> brick. 2. In the 4c caption append: if leg_gap_d_oi_qty is null, omit that sentence entirely (do not show "—").
> Change no other file, string or behaviour. Reply with the files changed.

Lovable then drew `·` also for a strike whose now and pre-open are both 0 — **a measured zero shown as a gap**;
corrected by follow-up 2:
> One correction, nothing else: a strike whose now and pre-open are both exactly 0 is a measured zero (no open
> interest at either time), not a gap. Draw no brick and no "·" for it — just the empty bar track, as the existing
> book bars do for 0. Keep "·" ONLY for: no flow row for that strike, or now or pre-open is null. …

Counts after it, NIFTY Full chain: 83 bricks · 25 `·` · 0 empty; SQL over the view's 239 strikes: 83 brick / 25 gap /
131 measured zero (all 131 outside the ladder's strike range).

**Guard** `mv_lovable_guard.sh 858cb46 v_dex_flow_vs_book`: PASS at `1f3cc63` and again at `62f5c55` — six paths
(`Brick.tsx` A; `LadderPanel.tsx`, `PinFlowsBody.tsx`, `StrikeLadder.tsx`, `board.ts`, `Board.tsx` M), exactly one read
of the view, no other reads, no credentials, no vanna/charm, tsc + build clean.

**Staging read** (Claude, operator's Chrome, `marketview.meridianalpha.in/staging/`) against the table above: all 12
values and both ΔOI gaps equal on NIFTY and SENSEX; every §4 string exact; bricks drawn; zero crossings on both nets
and on the ladder (NIFTY 22,400, SENSEX 72,000); brick proportions measured against value. **One defect found:** the
Net tile's track was twice the Call/Put width, so the three tiles shared a scale as a fraction of width but not in
pixels (NIFTY Net's 79,275 outline drawn longer than Call's 119,321). Follow-up 3:
> One fix, nothing else: the three DEX tile bricks must share ONE scale in pixels, not as a fraction of each bar's own
> width. … Use the same pixel half-width for all three … so equal crore = equal pixels across the three tiles. Ladder
> unchanged. …

Re-read at `62f5c55`: ~1,590 Cr/px NIFTY and ~300 Cr/px SENSEX across all three tiles.

**Promoted** 20:32 IST from the checked commit with no pull: backup `/var/www/marketview.bak-858cb46`; live build
`/tmp/mv-live-build` → `/var/www/marketview/`, `diff -rq` clean, bundle `assets/index-CBde1ur8.js`. Live read in Chrome:
NIFTY tiles and ladder identical to staging.

**Noted, not fixed (follow-up candidate):** while the data queries are still loading, the tiles show the absent line
"no flow before 09:15" — a loading state worded as a data state. Read once on the live board at 20:32 before the
queries returned. Wording for a loading state needs the operator's yes.

**20:33 IST — rollback run by mistake, then re-promoted.** The rollback line printed for reference in the promote
message (`rsync … marketview.bak-858cb46/ → marketview/`) was run, putting live back on `858cb46`; re-promoted 20:34
from the checked build still in `/tmp/mv-live-build` (bundle `assets/index-CBde1ur8.js` asserted before the rsync),
`diff -rq` clean. Live is `62f5c55`. Correction recorded: a rollback command is printed only inside a block that
refuses to run without an explicit argument, never as a bare line beside the steps to run.
