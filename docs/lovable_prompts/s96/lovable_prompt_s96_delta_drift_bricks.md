# Lovable prompt — S96 ∂Δ/∂σ and ∂Δ/∂t flow as bricks on the two Δ sensitivity tiles (P7b, `v_delta_drift_flow_vs_book`)

> Paste everything below the line into Lovable. Base: `meridian-connect` `c81b700` (live).
> Guard: `bash ~/mv_lovable_guard.sh c81b700 v_delta_drift_flow_vs_book` (S92 v2, one named read).
> ACL fingerprint before and after. Expected pre-round vs the S96 round baseline (`relations 348 c56612ad…`,
> `anon_public_privs 254 e93833fd…`): `relations` 350 and `anon_public_privs` 256 (+2 each: `v_gex_greeks_l2_leg`
> S96-F and `v_delta_drift_flow_vs_book` S96-G); every other row unchanged.
> Rulings: S96-F, S96-G (P7b), S96-A D3 (L7/L8 badge amended), S96-C (bricks; Lovable owns form, not meaning).
> Wording approved by the operator 2026-10-12 06:13 IST: W1 option 1 (bricks, each tile its own scale), strings 1–9.

---

**Show today's ∂Δ/∂σ and ∂Δ/∂t flow on the Flows tab as bricks on the two existing Δ sensitivity tiles
("∂Δ/∂σ · PER VOL PT" and "∂Δ/∂t · PER DAY"), and amend one badge and four explanation boxes. You own the visual
form. You do NOT own the data, the words or the rules below — follow them exactly.**

**Change ONLY:** `src/lib/board.ts`, `src/pages/Board.tsx`, files under `src/components/board/`. Do not touch any other
file, dependency, config, env, SQL or Supabase setting. Do not change any existing item, label or string except where
§4 says so. Never use the words "vanna" or "charm". Copy every quoted string EXACTLY, including `·`, `—`, `Δ`, `Γ`, `γ`
and `÷`. Do not change any existing data read (no other `supabase.` call may be added or edited).

## 1. Data — one new hook in `src/lib/board.ts`, directly after `useDexFlow`

It must contain `supabase.from("v_delta_drift_flow_vs_book")` exactly once, on one line together with `.select(`, and
no other new `supabase.` call. No date or ts filter: the view decides session and clocks. A NULL stays `null`.

```ts
/** P7b: ∂Δ/∂σ and ∂Δ/∂t flow since the pre-open beside the L7/L8 book, front leg (S96-F, S96-G). */
export function useDeltaDriftFlow(s: Symbol) {
  return useQuery({
    queryKey: ["board", "ddflow", s], ...opts,
    queryFn: async () => {
      const { data, error } = await supabase.from("v_delta_drift_flow_vs_book").select("symbol, expiry_date, ts, anchor_ts, flow_window, status, leg_iv_book_cr, leg_iv_preopen_cr, leg_iv_flow_cr, leg_iv_no_anchor_cr, leg_t_book_cr, leg_t_preopen_cr, leg_t_flow_cr, leg_t_no_anchor_cr, leg_gap_d_oi_qty, leg_no_anchor_oi_qty")
        .eq("symbol", s).order("strike", { ascending: true }).limit(1);
      if (error) throw error;
      const nz = (v: any) => (v == null ? null : Number(v));
      const r = ((data ?? []) as any[])[0];
      if (!r) return null;
      return {
        expiry: r.expiry_date as string, ts: r.ts as string, anchorTs: r.anchor_ts as string,
        window: r.flow_window as string, status: r.status as string,
        iv: { book: nz(r.leg_iv_book_cr), pre: nz(r.leg_iv_preopen_cr), flow: nz(r.leg_iv_flow_cr), noAnchor: nz(r.leg_iv_no_anchor_cr) },
        t:  { book: nz(r.leg_t_book_cr),  pre: nz(r.leg_t_preopen_cr),  flow: nz(r.leg_t_flow_cr),  noAnchor: nz(r.leg_t_no_anchor_cr) },
        gapDoi: nz(r.leg_gap_d_oi_qty), noAnchorOi: nz(r.leg_no_anchor_oi_qty),
      };
    },
  });
}
```

(The leg totals are the same on every row of a symbol, so one row is enough.)

## 2. When bricks are drawn (fixed)

Only on the two Δ tiles. Draw bricks on a tile only when ALL hold; otherwise draw the tile exactly as today and show
the §4 absent line under it:
- the hook returned a row, `window === "SESSION"` and `status === "OK"`;
- **same run as the tile:** the tile's own displayed net (the L7/L8 value it shows today, before any rounding) and
  the hook's `book` for that construct differ by less than 0.01 (Rs crore). `iv.book` pairs with the ∂Δ/∂σ tile,
  `t.book` with the ∂Δ/∂t tile. They are the same quantity from the same run (checked in the database to 1e-12), so
  a larger difference means the two reads are on different runs: no bricks.

Do NOT change the tile's big number or its existing net/gross line. The ∂Γ/∂t and ∂Γ/∂σ tiles get no bricks.

## 3. The brick rule (fixed — the form is yours; reuse the existing `Brick` component)

For each Δ tile take `now = book` and `pre = pre` of its construct. Exactly the S96-C rule: draw from zero;
**held** = the part in both `[0, pre]` and `[0, now]` → solid in the sign colour; **added** = the part of `[0, now]`
not in `[0, pre]` → lighter shade of the same sign colour; **removed** = the part of `[0, pre]` not in `[0, now]` →
outline only, in `pre`'s sign colour; opposite signs → held empty, added 0 → now, removed 0 → pre.

- **EACH TILE HAS ITS OWN SCALE** (the larger of |now| and |pre| on that tile). The two tiles are in different units
  (per IV point vs per calendar day), so they must NOT share a scale. This is the opposite of the DEX tiles.
- Sign colour = the existing `hue()` convention. Geometry only; compute or show no other total, ratio or percentage.
- A `null` `now` or `pre` is a gap: draw the existing `·` marker, never a zero-length brick.

## 4. Words — exact strings

**4.1** Δ tile sub-line (a new line under the tile's existing lines), only when bricks are drawn, for construct k:

`` `from ${fmtCr(pre)} at pre-open OI · ${fmtCr(flow)} since ${istTime(anchorTs)}` ``

**4.2** Absent line (instead of 4.1) when bricks are not drawn, first match:
- while `useDeltaDriftFlow` for the symbol is loading → `flow · loading`
- `status === "SKIPPED_EXPIRY"` → `no flow on expiry day`
- no row, or `window !== "SESSION"` → `no flow before 09:15`
- otherwise (status not OK, or the same-run test fails) → `flow · different run — not drawn`

**4.3** Gap caption, appended to each Δ tile's existing caption, only when bricks are drawn and `gapDoi` is not null:

`` ` ${num(gapDoi)} qty of ΔOI has no priced greek and is not counted; this does not say who bought or wrote.` ``

**4.4** Replace the Flows-tab bordered badge text `PROVISIONAL — flow-vs-book (D-4) not built` (same element, same
styling) with:

`flow-vs-book shown on unclassified ΔOI; classification (D-4) not built`

**4.5** In `DETAIL` (in `LadderPanel.tsx`), the explanation entries of the four sensitivity tiles begin with the text
`PROVISIONAL — flow-vs-book (D-4) not built`. Replace ONLY that leading text, nothing else in the entry:
- in the ∂Δ/∂t and ∂Δ/∂σ entries → `flow-vs-book shown on unclassified ΔOI; classification (D-4) not built`
- in the ∂Γ/∂t and ∂Γ/∂σ entries → `flow not shown for the γ pair (net is a cancellation residue); classification (D-4) not built`

**4.6** Append to the existing `how` of the ∂Δ/∂t and ∂Δ/∂σ entries only:

`" Bar: solid = held since the pre-open, light = added, dashed outline = removed. \"from x at pre-open OI\" is the pre-open open interest valued at today's greeks, so the change is open interest only, not repricing."`

**4.7** Append to the existing `computed` of the ∂Δ/∂t and ∂Δ/∂σ entries only:

`" Pre-open and flow: v_delta_drift_flow_vs_book (pre-open = the session's first front-expiry snapshot before 09:15 IST; flow = greek × ΔOI × spot ÷ 1e7 at the L7/L8 run)."`

Do NOT change the DEX tiles, their bricks or badge, S*, the ladder, or any other tile or string.

## Reply with

The files changed and what you changed in each. Confirm `src/lib/board.ts` contains
`supabase.from("v_delta_drift_flow_vs_book")` exactly once, on one line with `.select(`, that no other data read was
added or edited, and that no other file or existing string changed except §4. If any part cannot be applied as
written, change nothing and say which part.

---

## Staging read (operator / Claude, after the guard PASS)

Read the tiles against SQL taken at the same moment (one statement, through `bin/roq.sh` or the editor):

```sql
SELECT DISTINCT symbol, ts, anchor_ts, flow_window, status,
       round(leg_iv_book_cr::numeric, 2) AS iv_book, round(leg_iv_preopen_cr::numeric, 2) AS iv_pre,
       round(leg_iv_flow_cr::numeric, 2) AS iv_flow, round(leg_t_book_cr::numeric, 2) AS t_book,
       round(leg_t_preopen_cr::numeric, 2) AS t_pre, round(leg_t_flow_cr::numeric, 2) AS t_flow,
       leg_gap_d_oi_qty, leg_no_anchor_oi_qty
  FROM public.v_delta_drift_flow_vs_book ORDER BY symbol;
```

Until the 2026-10-12 pre-open rows land (~08:30 IST) the views carry the 2026-10-09 15:40 run: NIFTY book ∂Δ/∂σ
+6,089.82 / ∂Δ/∂t −9,796.95, flow +1,761.07 / −1,919.44; SENSEX +1,086.93 / −1,259.07, flow +729.56 / −795.65
(S96-G K1 / K2). After ~08:30 and until the tape moves after 09:15 the absent line `no flow before 09:15` is correct.

---

## Round record

**Wording** approved by the operator 2026-10-12 06:13 IST (W1 option 1; strings 1–9). Prompt committed `74baad5`.
**Base `c81b700` → live `804d684`.**

**Fingerprint** pre-round 06:15 and after-round 06:30 IST identical on all nine rows: `relations 350 ccc3895d…`,
`anon_public_privs 256 f19b614e…`, `anon_writable_objs 0`, `public_functions 40 5d8cd7f8…`, `rls_policies 28 d16e21d6…`,
`default_privileges 27 9db86164…`, `schemas 10 2a889318…`, `public_triggers 0`, `anon_role 1 c506ff14…`. Versus the 04:07
round baseline only `relations` and `anon_public_privs` moved, +2 each: `v_gex_greeks_l2_leg` (S96-F) and
`v_delta_drift_flow_vs_book` (S96-G), both created this morning. This is the new baseline.

**Lovable's first reply** applied §1–§4: `useDeltaDriftFlow` verbatim (one read, one line with `.select(`, no other read
touched), bricks on the two Δ tiles under the three conditions with each tile on its own scale, 4.1–4.3, the badge,
the four explanation replacements and the Δ-only appends. It predicted "no flow before 09:15" for a Monday before the
open — wrong for the third round running: the views carried the 10-09 15:40 SESSION run. It noted that the D-4 text
starts each entry's CAVEAT line, not the entry, and replaced only that phrase — as 4.5 intends.

**Guard** `mv_lovable_guard.sh c81b700 v_delta_drift_flow_vs_book`: PASS at `d1e8f4b` and at `804d684` — four paths, all M
(`LadderPanel.tsx`, `PinFlowsBody.tsx`, `board.ts`, `Board.tsx`), exactly one added read of the view, no other reads, no
credentials, no vanna/charm, tsc + build clean; 4 files, 39 insertions, 8 deletions.

**Staging read** (Claude, operator's Chrome) at `d1e8f4b`: sub-lines NIFTY ∂Δ/∂σ "from +4,329 Cr at pre-open OI · +1,761 Cr
since 08:30", ∂Δ/∂t "from −7,878 … · −1,919 …"; SENSEX "+357 … · +730 … since 08:35", "−463 … · −796 …"; pre-open + flow =
the tile's big number on all four (6,090; −9,797; 1,087; −1,259); flow equal to S96-G K1. Bricks on each tile's own scale,
measured on SENSEX: ∂Δ/∂t held:added 29:47 px against 463:796 Cr (0.38 / 0.37), ∂Δ/∂σ 25:50 against 357:730 (0.33 / 0.33).
γ tiles no bricks; badge amended; Δ explanation caveats amended and `how` / `computed` appended once each; γ caveats
carry the γ string; DEX chip unchanged. **One defect: the 4.3 gap sentence rendered nowhere** — Lovable had joined it only
to a "No ∂Δ/∂t for this leg." fallback. Follow-up (pasted verbatim):
> One fix, nothing else: the §4.3 gap sentence (…) does not render anywhere. Append it to the caption paragraph shown
> under the ladder when the ∂Δ/∂t or ∂Δ/∂σ layer is selected (the line that currently reads "Dealer delta-notional drifts
> … ; bars per strike."), the same place the DEX tiles' gap sentence is appended, only when that tile's bricks are drawn
> and `gapDoi` is not null. Change no other file, string or behaviour. Reply with the file changed.

Re-read at `804d684`: the caption under the ladder for both Δ layers ends "13,33,670 qty of ΔOI has no priced greek and is
not counted; this does not say who bought or wrote." (NIFTY) / "6,59,900 qty …" (SENSEX); not on the γ layers. Read
against SQL in one statement through roq: `leg_gap_d_oi_qty` 1,333,670 / 659,900 exactly; pre-open / flow 4,328.75 /
1,761.07 / −7,877.51 / −1,919.44 and 357.37 / 729.56 / −463.42 / −795.65; no-anchor 0; ts the 15:40 IST run. Against
`leg_abs_d_oi_qty` 145,107,950 / 13,126,700 the unpriced share is 0.92 % NIFTY and 5.03 % SENSEX (computed).

**Promoted** 06:39 IST from the checked commit, no pull, in a refusing subshell (HEAD = `804d684`, no tracked changes,
backup path absent, tsc, build rooted at `/assets/`): backup `/var/www/marketview.bak-c81b700`; `/tmp/mv-live-build` →
`/var/www/marketview/`, `diff -rq` clean, bundle `assets/index-CadQe4qO.js`. **Live read** in Chrome: bundle
`index-CadQe4qO.js`; both symbols' Δ sub-lines, DEX sub-lines and SAME chips equal to staging; badge amended; gap caption
present; no absent line.

**Noted, not changed (pre-existing):** the L7/L8 tile captions read "Dealer delta-notional drifts …" and "A +1 IV point
moves dealer delta-notional …". "Dealer" there is the S89 PE-negation assumption (ADR-014 sign), which P2 found
regime-dependent; the wording predates this round and was not touched. Candidate for a wording review.
