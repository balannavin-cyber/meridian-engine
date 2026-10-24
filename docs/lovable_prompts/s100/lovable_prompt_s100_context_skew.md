# Context — IV skew tile shows the view's skew (ruling S100-P) — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** Two files in `src/marketview/`. No new database query (it reuses
`useIvTab`, the IV tab's existing hook). Wording below is operator-approved (S100-P); use it exactly.

## Context

The Context page's "IV Skew" tile computes `(ATM PE IV ÷ ATM CE IV − 1) × 100` in the browser — a put/call IV gap at one
strike, not a skew — while the IV tab shows the real skew, `leg_skew_98` (vol points at the K98 strike) from
`v_iv_surface`. Make the Context tile show the view's skew for the front leg, and drop the client computation.

## Change 1 — `src/marketview/state.ts`

1. In the existing line `import { useSessions, useOpenGap, useLiveSpot } from "@/lib/board";  // S100-N`, add `useIvTab`
   to the imported names (same module; `useIvTab` is exported from `@/lib/board`).

2. Replace exactly these two lines:

```ts
  const ivSkewPct = ivSmile.data && ivSmile.data.atmCe && ivSmile.data.atmPe
    ? (ivSmile.data.atmPe / ivSmile.data.atmCe - 1) * 100 : null;
```

with exactly:

```ts
  // S100-P: skew from the view (front leg = lowest leg), as the IV tab shows it; no client recompute
  const ivSurf = (((useIvTab(symbol).data as any)?.surface) ?? []) as any[];
  const frontLeg = ivSurf.length ? Math.min(...ivSurf.map((r) => Number(r.leg))) : null;
  const skewRow = frontLeg != null ? (ivSurf.find((r) => Number(r.leg) === frontLeg) ?? null) : null;
  const ivSkew98 = skewRow?.leg_skew_98 != null ? Number(skewRow.leg_skew_98) : null;
  const ivK98 = skewRow?.leg_k98 != null ? Number(skewRow.leg_k98) : null;
```

3. In the returned object, replace `ivSmile, ivSkewPct, zonesNearSpot,` with `ivSmile, ivSkew98, ivK98, zonesNearSpot,`.
   Leave the `const ivSmile = useIvSmile(...)` line as it is (the smile chart still uses it).

## Change 2 — `src/marketview/sections.tsx` (the "IV Skew" Card only)

Replace exactly this block:

```tsx
          {s.ivSmile.data && s.ivSkewPct != null ? (<>
            <div className="mt-1 text-[26px] font-bold leading-none" style={{ fontFamily: MV.mono, color: Math.abs(s.ivSkewPct) < 1 ? MV.mid : s.ivSkewPct > 0 ? MV.red : MV.green }}>
              {Math.abs(s.ivSkewPct) < 1 ? "flat" : `${s.ivSkewPct > 0 ? "+" : ""}${s.ivSkewPct.toFixed(1)}% ${s.ivSkewPct > 0 ? "PE" : "CE"}`}
            </div>
            <div className="mt-1 text-[11px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
              ATM {fmtNum(s.ivSmile.data.atm, { maximumFractionDigits: 0 })} · CE {s.ivSmile.data.atmCe?.toFixed(1)} / PE {s.ivSmile.data.atmPe?.toFixed(1)}
            </div>
            <div className="mt-2"><IVSmile points={s.ivSmile.data.points} atm={s.ivSmile.data.atm} /></div>
          </>) : <Unavailable label="iv not populated" />}
```

with exactly:

```tsx
          {s.ivSkew98 != null || s.ivSmile.data ? (<>
            <div className="mt-1 text-[26px] font-bold leading-none" style={{ fontFamily: MV.mono, color: s.ivSkew98 == null || s.ivSkew98 === 0 ? MV.mid : s.ivSkew98 > 0 ? MV.red : MV.green }}>
              {s.ivSkew98 == null ? "—" : `${s.ivSkew98 > 0 ? "+" : ""}${s.ivSkew98.toFixed(1)} vol pts`}
            </div>
            <div className="mt-1 text-[11px]" style={{ color: MV.weak, fontFamily: MV.mono }}>
              {s.ivSkew98 == null ? "—" : `@ K98 ${s.ivK98 != null ? fmtNum(s.ivK98, { maximumFractionDigits: 0 }) : "—"} · front leg · from view`}
            </div>
            {s.ivSmile.data ? <div className="mt-2"><IVSmile points={s.ivSmile.data.points} atm={s.ivSmile.data.atm} /></div> : null}
          </>) : <Unavailable label="iv not populated" />}
```

The header line (`IV Skew`) stays. No other Card, file, label, colour token or layout changes.

## Constraints

No `supabase.` line added, edited or removed; `useIvSmile` and `IVSmile` untouched; no other use of `ivSkewPct` may remain
(if one exists elsewhere, change nothing and say where).

## Reply with

The two files and each replacement (old → new). If any quoted block does not exist exactly as quoted, change nothing
and say which.

---

## Checks (Claude / operator)

1. Guard (round copy, allowlist the two `src/marketview` files): two paths M; no new data reads; no credentials; no
   vanna/charm; tsc + build clean.
2. Staging read, both symbols: Context tile value = the IV tab's "skew 98" for its front leg (same ts), and the K98
   strike equal; expected figures from `v_iv_surface` through roq at the read.
3. Promote, backup `.bak-142c3e6`, S100-L retention (delete `.bak-804d684`).

---

## Round record

**Wording** approved 2026-10-24 ~16:40 IST (S100-P: "Yes, as shown"). **Lovable** `6c11173` "Changes" → `2ee83e1`; reply: the
three state.ts edits and the sections.tsx block as quoted, `ivSkewPct` no longer referenced, no `supabase.` line touched.

**Guard** (`~/s100m/mv_lovable_guard_s100n.sh 142c3e6`): `M src/marketview/sections.tsx`, `M src/marketview/state.ts`; no new
data reads, no credentials, no vanna/charm; build clean; staging `2ee83e1`; **2 files, 13 insertions, 9 deletions** = the
prompt's edits computed (state.ts +8 / −4, sections.tsx +5 / −5; Claude's pre-estimate "+16 / −10" was wrong).

**Staging read** (16:41–16:43 IST): NIFTY IV tab W1 front `skew 98 +2.54 vol pts @ 22,150` = Context `+2.5 vol pts · @ K98
22,150 · front leg · from view`; SENSEX `+1.61 @ 71,600` = `+1.6 · @ K98 71,600`. Discriminating: the old tile read
"+28.7% PE" / "+9.2% PE".

**Promoted** 16:47 IST from `2ee83e1` (log `~/s100m/promote_2ee83e1.log`): backup `.bak-142c3e6`; `LIVE = BUILD`; bundle
`assets/index-CoRd4ixq.js`; S100-L: `.bak-804d684` deleted; left `.bak-142c3e6`, `.bak-1072593`, `.bak-04fcd05` + 3 `PRE_*`.
**Live read** 16:48 IST SENSEX Context: `+1.6 vol pts · @ K98 71,600 · front leg · from view`.

**Noted:** on first load (before queries return) the legacy strip shows SPOT change `0 (0.00%)`, MAX Γ `—` and the skew
tile `iv not populated` — loading states rendered as values (the `: 0` fallback in `state.ts` when `prevClose` is null);
same class as the Health panels' "no errors" while loading.
