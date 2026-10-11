The edits pass every guard check on a copy of `392256a`: 4 allowed paths, +30/−2 lines, exactly 1 read of `v_dex_repriced_zero`, no other reads, no credentials, no vanna/charm, `tsc` clean and the build green. This time the tile is placed in `FlowsBody`, not just declared.

## Step 26 — paste into Lovable (Marketview, `main` at `392256a`)

````text
Add the S* zero-delta level to the DEX group on the Flows tab. Change ONLY these four files:
`src/lib/board.ts`, `src/pages/Board.tsx`, `src/components/board/LadderPanel.tsx`, `src/components/board/PinFlowsBody.tsx`.
Do not touch any other file. Do not change any existing item, label, string, colour, CSS variable, component, query or hook
except the three one-line edits named below. Do not add dependencies. Do not compute any level or total on the client.
Never use the words "vanna" or "charm". Copy every quoted string EXACTLY, including `−` (U+2212), `·`, `Δ`, `σ`, `—`.

## 1. `src/lib/board.ts` — one new hook, placed directly after the existing `useDexBook` function

It must contain `supabase.from("v_dex_repriced_zero")` exactly once and no other new `supabase.` call. No gate, no date filter.

```ts
/** P6 / S95: S*, the re-priced zero-delta level (ruling S94-H). Latest chain cycle, one row per symbol. */
export function useDexZero(s: Symbol) {
  return useQuery({
    queryKey: ["board", "dexzero", s], ...opts,
    queryFn: async () => {
      const { data, error } = await supabase.from("v_dex_repriced_zero")
        .select("symbol, ts, spot, status, zero_delta, zero_minus_spot, zero_sigma")
        .eq("symbol", s).limit(1);
      if (error) throw error;
      const r = ((data ?? []) as any[])[0];
      if (!r) return null;
      const nz = (v: any) => (v == null ? null : Number(v));
      return { ts: r.ts as string, spot: nz(r.spot), status: String(r.status), zero: nz(r.zero_delta), minus: nz(r.zero_minus_spot), sigma: nz(r.zero_sigma) };
    },
  });
}
```

## 2. `src/components/board/LadderPanel.tsx` — one new `DETAIL` entry, directly after the `f_dex_put` entry

```ts
  f_dex_zero: { title: "Zero-Δ level · S*", unit: "index points", what: "The spot level at which the open options, each re-priced at that spot with Black–Scholes at its own implied volatility, would carry zero net delta. There is at most one such level.", how: "Open-interest delta; dealer side regime-dependent (P2). With spot below S* the re-priced book is net short the index; above S*, net long. The dotted line on the ladder marks it.", computed: "v_dex_repriced_zero.zero_delta — L3's repricing (v_gex_repriced_flip) with delta in place of gamma; r = session-median futures carry; latest chain cycle.", scale: "S* − spot in 1-day σ. In its gates the level moved at most 0.17σ across rate and time conventions, except on 1-dte SENSEX, where it moved 0.24σ.", caveat: "A level from today's book, not a forecast: nothing tests whether price moves toward it. It can disagree in sign with the Net DEX tile, which uses the vendor's delta (2 of 7 gate days). Chain clock (latest), not the book's settled run. Not computed on expiry day.", withIds: ["f_dex_net", "f_dex_call"], src: "v_dex_repriced_zero · COMMENT live" },
```

## 3. `src/pages/Board.tsx`

**3a.** In the existing import from `"@/lib/board"`, change `useDexBook, useFlowSim,` to `useDexBook, useDexZero, useFlowSim,`. No other import changes.

**3b.** Change the `dexKey` line's object from
`{ f_dex_net: "net", f_dex_call: "call", f_dex_put: "put" }` to
`{ f_dex_net: "net", f_dex_call: "call", f_dex_put: "put", f_dex_zero: "net" }`.

**3c.** Directly after the line that begins `  const dexCap = `, add:

```ts
  // ---- S95: S*, the re-priced zero-delta level (ruling S94-H) ----
  const zr = (useDexZero(symbol).data ?? null) as { ts: string; spot: number | null; status: string; zero: number | null; minus: number | null; sigma: number | null } | null;
  const zOk = !!zr && zr.status === "OK" && zr.zero != null;
  const zeroWord: Record<string, string> = { NO_CROSSING: "no crossing within ±10 %", SKIPPED_EXPIRY: "expiry day — not computed", UNMEASURABLE_R: "r unmeasurable" };
  const zeroSub = zOk && zr!.minus != null && zr!.sigma != null
    ? `${sgn(zr!.minus, 0)} pts · ${sgn(zr!.sigma, 2)}σ ${zr!.minus >= 0 ? "above" : "below"} spot · chain ${istTime(zr!.ts)} (book settled ${dex0 ? istTime(dex0.settledTs) : "—"})`
    : zr ? `chain ${istTime(zr.ts)}` : "";
```

`sgn`, `num`, `istTime`, `Absent`, `dex0`, `dexLayer` already exist in this file; define no new helpers.

**3d.** In the `flowLevels` array, directly after the existing `FLIP (L3)` entry line, add this one line:

```ts
    ...(dexLayer && zOk ? [{ id: "sstar", name: "S* (ZERO-Δ)", at: zr!.zero as number, style: "dotted" as const }] : []),
```

**3e.** In the `flowItems` array, directly after the `f_dex_put` item, add:

```ts
    { id: "f_dex_zero", label: "Zero-Δ level · S*", sub: zeroSub, value: zOk ? num(zr!.zero as number) : <Absent word={zr ? (zeroWord[zr.status] ?? zr.status.toLowerCase()) : "no level"} />, levelIds: zOk ? ["sstar"] : [], caption: zOk ? `S* ${num(zr!.zero as number)}, ${sgn(zr!.minus ?? 0, 0)} pts from spot ${num(zr!.spot ?? 0, 1)} at chain ${istTime(zr!.ts)}.` : "No zero-Δ level." },
```

## 4. `src/components/board/PinFlowsBody.tsx` — place the tile (without this it never renders)

In `FlowsBody`, inside the bordered DEX group, directly after the line that holds the `f_dex_call` / `f_dex_put` grid and before that group's closing `</div>`, add:

```tsx
        <Tile it={by("f_dex_zero")} sel={sel} setSel={setSel} className="w-full" />
```

## Reply with

The four files changed and the number of lines added in each (expected: board.ts 17, LadderPanel.tsx 1, Board.tsx 11 added + 2 changed, PinFlowsBody.tsx 1). Confirm `supabase.from("v_dex_repriced_zero")` appears exactly once. If any part cannot be applied exactly as written, change nothing and say which.
````

**After it pushes**, in this order:
1. The fingerprint SQL again. All nine rows must equal the 13:18 snapshot (`relations 346 06c07d80…`, `anon_public_privs 252 7f41638b…`, and the rest unchanged).
2. On the box: `bash ~/mv_lovable_guard.sh 392256a v_dex_repriced_zero 2>&1 | tee ~/guard_s95c.log; echo "guard_exit=${PIPESTATUS[0]}"`. PASS ends with `STAGING DEPLOYED <sha>`, `4 files changed, 30 insertions(+), 2 deletions(-)`, `guard_exit=0`.

Then I'll diff Lovable's push against my tested copy and read `/staging/` myself before you promote.