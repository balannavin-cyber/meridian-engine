# Lovable prompt — S95 DEX standing book on the Flows tab (P6, ENH-140)

> Paste everything below the line into Lovable. Base: `meridian-connect` `13b1410`.
> Guard: `bash ~/mv_lovable_guard.sh 13b1410 v_dex_standing_book` (S92 v2, one named read).
> Wording approved by the operator 2026-10-10 11:25 IST (S95), incl. the two §D.48.1 lines.
> Rulings: S94-G (P2 phrase), S94-H (no zero-Δ level), S94-I (gap beside every leg total; dte 0 note).

---

**Add the DEX standing book to the Flows tab of the Board. Change ONLY these three files:**
`src/lib/board.ts`, `src/pages/Board.tsx`, `src/components/board/LadderPanel.tsx`.
Do not touch any other file. Do not change any existing item, label, string, colour, CSS variable,
component, query or hook. Do not add dependencies. Do not touch Supabase settings, SQL, env, package
or config files. Do not compute any total, sum, ratio or percentage on the client: every number shown
comes straight from a column of the view. Never use the words "vanna" or "charm". Copy every quoted
string below EXACTLY, including the characters `−` (U+2212) and `·`.

## 1. `src/lib/board.ts` — one new hook, placed directly after `useGreeksStrike`

Add exactly this (it must contain the literal `supabase.from("v_dex_standing_book")` exactly once,
and no other new `supabase.` call). Do not apply `applyGate` or any date/ts filter: the view decides
the session itself.

```ts
/** P6 / ENH-140: DEX standing book, front leg, settled run. Session decided by the view. */
export function useDexBook(s: Symbol) {
  return useQuery({
    queryKey: ["board", "dex", s], ...opts,
    queryFn: async () => {
      const { data, error } = await supabase.from("v_dex_standing_book")
        .select("symbol, session_date, leg_n, expiry_date, dte, settled_ts, strike, call_dex_cr, put_dex_cr, net_dex_cr, leg_call_dex_cr, leg_put_dex_cr, leg_net_dex_cr, leg_oi_qty, leg_gap_oi_qty, leg_n_gap_strikes")
        .eq("symbol", s).eq("leg_n", 1).order("strike", { ascending: true }).limit(1000);
      if (error) throw error;
      const nz = (v: any) => (v == null ? null : Number(v));
      return ((data ?? []) as any[]).map((r) => ({
        strike: Number(r.strike), expiry: r.expiry_date as string, dte: Number(r.dte), settledTs: r.settled_ts as string,
        call: nz(r.call_dex_cr), put: nz(r.put_dex_cr), net: nz(r.net_dex_cr),
        legCall: nz(r.leg_call_dex_cr), legPut: nz(r.leg_put_dex_cr), legNet: nz(r.leg_net_dex_cr),
        legOi: nz(r.leg_oi_qty), legGap: nz(r.leg_gap_oi_qty),
      }));
    },
  });
}
```

A NULL must stay `null` (it is a gap); never turn it into 0.

## 2. `src/components/board/LadderPanel.tsx` — three new `DETAIL` entries

In the `DETAIL` object, directly after the `f_leg` entry, add exactly:

```ts
  // ---- S95 Flows tab: DEX standing book (P6, ENH-140; rulings S94-G, S94-H, S94-I) ----
  f_dex_net: { title: "Net DEX · OI proxy", unit: "₹ Cr of index — measured part of the leg", what: "How many ₹ crore of the index the open options behave like, built from open interest with each side at its own delta sign (calls +, puts −).", how: "Open-interest delta; dealer side regime-dependent (P2). Positive (cool): the open options, taken together, behave like a long index position; negative (warm): like a short one. Bars show each strike. · marks a strike where a side has OI but no published delta — a gap, never 0.", computed: "v_dex_standing_book.leg_net_dex_cr, front leg, settled run (last run at or before 15:15 IST). Per strike: net_dex_cr (delta × OI × spot ÷ 1e7).", scale: "Magnitude indicative, not measured: vendor delta fails put–call parity and |net|/gross is 9–24 %. Read the sign.", caveat: "Always read beside its gap: leg_gap_oi_qty is OI with no published delta and is not in the total. On expiry day (dte 0) greek gaps can flip the total's sign. This number does not say who holds the position.", withIds: ["f_dex_call", "f_dex_put"], src: "v_dex_standing_book · COMMENT live" },
  f_dex_call: { title: "Call DEX · OI proxy", unit: "₹ Cr of index — measured part of the leg", what: "How many ₹ crore of the index the open calls behave like, built from call open interest at each strike's call delta (calls +).", how: "Open-interest delta; dealer side regime-dependent (P2). Bars show each strike. · marks a strike where calls have OI but no published delta — a gap, never 0.", computed: "v_dex_standing_book.leg_call_dex_cr, front leg, settled run (last run at or before 15:15 IST). Per strike: call_dex_cr (delta × OI × spot ÷ 1e7).", scale: "Magnitude indicative, not measured: vendor delta fails put–call parity and |net|/gross is 9–24 %. Read the sign.", caveat: "Always read beside its gap: leg_gap_oi_qty is OI with no published delta and is not in the total. On expiry day (dte 0) greek gaps can flip the total's sign. This number does not say who holds the position.", withIds: ["f_dex_net", "f_dex_put"], src: "v_dex_standing_book · COMMENT live" },
  f_dex_put: { title: "Put DEX · OI proxy", unit: "₹ Cr of index — measured part of the leg", what: "How many ₹ crore of the index the open puts behave like, built from put open interest at each strike's put delta (puts −).", how: "Open-interest delta; dealer side regime-dependent (P2). Bars show each strike. · marks a strike where puts have OI but no published delta — a gap, never 0.", computed: "v_dex_standing_book.leg_put_dex_cr, front leg, settled run (last run at or before 15:15 IST). Per strike: put_dex_cr (delta × OI × spot ÷ 1e7).", scale: "Magnitude indicative, not measured: vendor delta fails put–call parity and |net|/gross is 9–24 %. Read the sign.", caveat: "Always read beside its gap: leg_gap_oi_qty is OI with no published delta and is not in the total. On expiry day (dte 0) greek gaps can flip the total's sign. This number does not say who holds the position.", withIds: ["f_dex_net", "f_dex_call"], src: "v_dex_standing_book · COMMENT live" },
```

## 3. `src/pages/Board.tsx`

**3a.** Add `useDexBook` to the existing import list from `"@/lib/board"`. Change no other import.

**3b.** In the Flows tab block, directly after the line that defines `l78Strikes`, add:

```ts
  // ---- S95: DEX standing book (P6, ENH-140) ----
  const dex = (useDexBook(symbol).data ?? []) as { strike: number; expiry: string; dte: number; settledTs: string; call: number | null; put: number | null; net: number | null; legCall: number | null; legPut: number | null; legNet: number | null; legOi: number | null; legGap: number | null }[];
  const dex0 = dex[0] ?? null;
  const dexKey: Record<string, "net" | "call" | "put"> = { f_dex_net: "net", f_dex_call: "call", f_dex_put: "put" };
  const dexLayer = sel ? dexKey[sel] ?? null : null;
  const dexSub = dex0 ? `calls +, puts − · front leg ${expShort(dex0.expiry)} · dte ${dex0.dte} · settled ${istTime(dex0.settledTs)}${dex0.dte === 0 ? " · dte 0 — greek gaps can flip the total's sign" : ""}` : "";
  const dexGap = (withOi: boolean) => dex0?.legGap == null ? "" : ` · gap ${num(dex0.legGap)}${withOi && dex0.legOi != null ? ` of ${num(dex0.legOi)}` : ""} qty`;
  const dexVal = (v: number | null, withOi: boolean) => !dex0 ? <Absent word="no book" /> : v == null ? <Absent word="no value" /> :
    <span><span style={{ color: hue(v) }}>{fmtCr(v)}</span><span style={{ color: "var(--ink-2)" }}>{dexGap(withOi)}</span></span>;
  const dexCap = (name: string, v: number | null) => dex0 && v != null ? `${name} ${fmtCr(v)} over strikes with a published delta;${dex0.legGap != null ? ` ${num(dex0.legGap)} qty of OI has no published delta and is not counted.` : ""} Bars per strike.` : "No DEX book.";
```

`fmtCr`, `num`, `hue`, `expShort`, `istTime`, `Absent` already exist in this file; use them, define no new helpers.

**3c.** Replace the existing `const flowRows = …` statement with this version (the non-DEX branch is
the existing code, unchanged):

```ts
  const flowRows = dexLayer ? (dex.length ? (ladder?.rows ?? []).map((lr) => {
    const r = dex.find((x) => x.strike === lr.strike);
    const v = r ? r[dexLayer] : null;
    return { strike: lr.strike, value: v, tint: null, readout: v == null ? "·" : lad(v), full: v == null ? "gap — OI with no published delta" : `${lad(v)} Cr` };
  }) : []) : l78Strikes.length ? (ladder?.rows ?? []).map((lr) => {
    const r = l78Strikes.find((x) => x.strike === lr.strike);
    const v = r ? r[flowLayer] : null;
    return { strike: lr.strike, value: v, tint: null, readout: v == null ? "·" : lad(v), full: v == null ? "no legs" : `${lad(v)} Cr` };
  }) : [];
```

**3d.** In the `flowItems` array, after the `f_leg` item (keep `f_leg` and every other item exactly as
it is), append these three items:

```ts
    { id: "f_dex_net", label: "Net DEX · OI proxy", sub: dexSub, value: dexVal(dex0?.legNet ?? null, true), levelIds: [], caption: dexCap("Net DEX · OI proxy", dex0?.legNet ?? null) },
    { id: "f_dex_call", label: "Call DEX · OI proxy", sub: dexSub, value: dexVal(dex0?.legCall ?? null, false), levelIds: [], caption: dexCap("Call DEX · OI proxy", dex0?.legCall ?? null) },
    { id: "f_dex_put", label: "Put DEX · OI proxy", sub: dexSub, value: dexVal(dex0?.legPut ?? null, false), levelIds: [], caption: dexCap("Put DEX · OI proxy", dex0?.legPut ?? null) },
```

**3e.** Replace the existing `const flowsNote = …` line with:

```ts
  const dexName: Record<string, string> = { net: "Net DEX", call: "Call DEX", put: "Put DEX" };
  const flowsNote = dexLayer ? (dex0 ? `bars · ${dexName[dexLayer]} · OI proxy · ${expShort(dex0.expiry)} leg · settled ${istTime(dex0.settledTs)}` : "bars · no DEX book")
    : l78Leg ? `bars · ${layerName[flowLayer]} · ${expShort(l78Leg.expiry_date)} leg · chain ${istTime(l78Leg.ts)}` : "bars · no L7/L8 rows";
```

## Reply with

The three files changed and, for each, what you added. Confirm that `src/lib/board.ts` contains
`supabase.from("v_dex_standing_book")` exactly once and that no other file or existing string changed.
If anything above cannot be applied exactly as written, change nothing and say which part.

---

## Round 2 (fix) — base `d1912d2` → `392256a`

Round 1 (`d1912d2`) added the items but never placed them: `FlowsBody` (`PinFlowsBody.tsx`) renders tiles
by id, so the three DEX cards were unreachable except via `?sel=`. Found on the `/staging/` browser read,
not by `tsc` (an unplaced item is not a type error). Round 2 also changed the sub-line `dte N` → `N cal d`
(operator yes, 11:50 IST): the view's `dte` is calendar days, the header's DTE is sessions.
Guard: `bash ~/mv_lovable_guard.sh d1912d2` (layout-only) PASS; ACL fingerprint identical to 11:19 IST.

1. `src/components/board/PinFlowsBody.tsx`, `FlowsBody`, after the `f_leg` Tile:
   a bordered group: `f_dex_net` full width, then `f_dex_call` / `f_dex_put` in a 2-column grid.
2. `src/pages/Board.tsx`, `dexSub`: `· dte ${dex0.dte} ·` → `· ${dex0.dte} cal d ·`.

## Round 4 (S* sub-line fix), base 1c5a047
Staging review found the tile's "above spot" measured from the chain spot (22,520.5) while the header
showed 22,535.7 — S* read as above on the tile, below on the header (NIFTY). Fix names the chain spot.
One line in src/pages/Board.tsx (zeroSub). Expected diff 1 file, +1/−1. No new data read.
Round 3 (S* tile) Lovable 103f663+1c5a047 = tested copy; fingerprint = 13:18; guard_s95c PASS.
Round 4 Lovable 719e85c+858cb46 = tested copy; fingerprint = 13:18 (13:45); guard_s95d PASS (1 file +1/-1).
Promoted 858cb46 at 13:47 IST; backup /var/www/marketview.bak-392256a (4 files, DEX yes, S* no).
Live read 13:48: NIFTY 22,529 +8 +0.07σ above chain spot 22,520.5; SENSEX 72,688 +215 +0.45σ above chain spot 72,472.3; dotted rule present both; bundle index-xwAr9HtW.js.
Lesson: a level tile must name the spot it is measured from when the header spot comes from a different clock.
