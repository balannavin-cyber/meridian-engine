# Read sentence — name the pocket word as local, state the net side (ruling S100-Q / S100-Q.1) — Lovable prompt

**Paste into the `meridian-connect` Lovable project.** One file, `src/lib/read.ts`. Wording is operator-approved (S100-Q.1,
option A); use it exactly. No data, query, layout or style change.

## Context

The read sentence (Board and Home) says "sits in a dampening / an amplifying pocket" from the γ sign of the strike nearest
spot, while the NET Γ tile shows the total; the two can disagree (e.g. "dampening" at −0.01 of gross). Keep the word, name
it as local, and say the net side in words.

## Change — `src/lib/read.ts`

1. Replace exactly:

```ts
    ? `Spot ${num(spot, 1)} sits in ${pocket.gex_cr >= 0 ? "a dampening" : "an amplifying"} pocket`
```

with exactly:

```ts
    ? `Spot ${num(spot, 1)} sits in ${pocket.gex_cr >= 0 ? "a dampening" : "an amplifying"} pocket (local γ)`  // S100-Q.1
```

2. Replace exactly:

```ts
  if (ratio != null) out += `. Net gamma is ${ratio.toFixed(2)} of gross`;
```

with exactly:

```ts
  if (ratio != null) out += `. Net gamma is ${ratio >= 0 ? "long" : "short"}, ${ratio.toFixed(2)} of gross`;  // S100-Q.1
```

Nothing else changes. The γ in "(local γ)" is a lower-case Greek gamma (U+03B3).

## Reply with

The file and both replacements (old → new). If either quoted line does not exist exactly as quoted, change nothing and
say which.

---

## Checks (Claude / operator)

1. Guard: round copy of `docs/lovable_prompts/s92/mv_lovable_guard.sh` with line 34's allowlist → `src/lib/read.ts` and one
   inserted case arm `src/lib/read.ts) ;;` ahead of the `src/lib/*` rule; one path M; no new data reads; no credentials;
   no vanna/charm; tsc + build clean; net 2 insertions, 2 deletions.
2. Staging read, both symbols, Board and Home: the sentence reads "… pocket (local γ), …" and ends "Net gamma is
   long|short, x.xx of gross." with the sign word matching the NET Γ tile.
3. Promote, backup `.bak-2ee83e1`, S100-L retention (delete `.bak-04fcd05`).

---

## Round record

**Wording** approved 2026-10-24 ~17:13 IST (S100-Q.1, option A). **Lovable** `23dec64` "Changes" → `3366bf1` "Updated spot gamma
descriptions"; reply: both lines replaced as quoted, γ U+03B3, nothing else.

**Guard** (`~/s100m/mv_lovable_guard_s100q.sh`: s92 guard with line 34 → `src/lib/read.ts` and an inserted arm
`src/lib/read.ts) ;;` at :40 — `diff` showed exactly those two): `M src/lib/read.ts`; no new data reads, no credentials, no
vanna/charm; build clean; staging `3366bf1`; **1 file, 2 insertions, 2 deletions**.

**Staging read** (17:15–17:16 IST): SENSEX Board and Home "… sits in an amplifying pocket (local γ), … Net gamma is long,
0.02 of gross." with NET Γ `long γ · 0.02 of gross`; NIFTY Home "… amplifying pocket (local γ) … Net gamma is long, 0.05 of
gross." with NET Γ `long γ · 0.05` — both symbols currently show the local-amplifying / net-long split the eval flagged.

**Promoted** 17:17 IST from `3366bf1` (log `~/s100m/promote_3366bf1.log`): backup `.bak-2ee83e1`; `LIVE = BUILD`; bundle
`assets/index-Bu6mi2fq.js`; S100-L: `.bak-04fcd05` deleted; left `.bak-2ee83e1`, `.bak-142c3e6`, `.bak-1072593` + 3 `PRE_*`.
**Live read** 17:18 IST NIFTY Board: "Spot 22,516.4 sits in an amplifying pocket (local γ), …".
