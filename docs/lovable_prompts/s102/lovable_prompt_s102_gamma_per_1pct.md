# Γ sizes in ₹ Cr per 1 % move (ADR-032 D1) — Lovable prompt

**Paste into the `meridian-connect` Lovable project — only after the seven `_1pct` views are applied and T1–T4 PASS**
(`sql/2026-10-30_s102_gex_per_1pct_views.sql`). Data-source and label changes only, in seven files. No layout, colour, style,
component or formatter change; **do not edit `crLakh`, `lad`, `fmtCr` or any formatter** (they are shared with the delta-type
figures, which must not change). Do not touch any `delta_*`, `dex`, `flow_cr` or `spot_pct` name. Every string is operator-approved
(table W below). Make exactly the replacements listed; where a replacement says "every occurrence (n)", there are exactly n.

**Why:** every Γ size was shown at the stored scale γ·OI·S²/1e7, which is the hedge for a 100 % move. The `_1pct` views carry
`<column>_1pct = <column> × 0.01`, ₹ Cr of delta-notional per 1 % move — the same unit as the Flows "Hedge per 1 %" figure.

## src/lib/board.ts

**1.** Replace exactly

```tsx
latestBySymbol("v_gex_abs_exposure", s)
```

with exactly

```tsx
latestBySymbol("v_gex_abs_exposure_1pct", s)
```

**2.** Replace exactly

```tsx
applyGate(supabase.from("gex_strike_snapshots").select("run_id, ts, spot")
```

with exactly

```tsx
applyGate(supabase.from("v_gex_strike_snapshots_1pct").select("run_id, ts, spot")
```

**3.** Replace exactly

```tsx
const { data, error } = await supabase.from("gex_strike_snapshots")
        .select("strike, expiry_date, gex_cr, gamma_call, gamma_put, oi_call, oi_put")
```

with exactly

```tsx
const { data, error } = await supabase.from("v_gex_strike_snapshots_1pct")
        .select("strike, expiry_date, gex_cr_1pct, gamma_call, gamma_put, oi_call, oi_put")
```

**4.** Replace exactly

```tsx
gex: has && r.gex_cr != null ? Number(r.gex_cr) : null,
```

with exactly

```tsx
gex: has && r.gex_cr_1pct != null ? Number(r.gex_cr_1pct) : null,
```

**5.** Replace exactly

```tsx
supabase.from("gamma_metrics").select("ts, net_gex")
```

with exactly

```tsx
supabase.from("v_gamma_metrics_1pct").select("ts, net_gex_1pct")
```

**6.** Replace exactly

```tsx
.filter((r) => r.net_gex != null && !seen.has(r.ts) && seen.add(r.ts))
        .map((r) => ({ ts: r.ts as string, v: Number(r.net_gex) }));
```

with exactly

```tsx
.filter((r) => r.net_gex_1pct != null && !seen.has(r.ts) && seen.add(r.ts))
        .map((r) => ({ ts: r.ts as string, v: Number(r.net_gex_1pct) }));
```

**7.** Replace exactly

```tsx
supabase.from("v_gex_net_gamma_river")
        .select("session_date, net_gex_cr, session_min_net_gex_cr, session_max_net_gex_cr, session_complete, spot, dte")
```

with exactly

```tsx
supabase.from("v_gex_net_gamma_river_1pct")
        .select("session_date, net_gex_cr_1pct, session_min_net_gex_cr_1pct, session_max_net_gex_cr_1pct, session_complete, spot, dte")
```

**8.** Replace exactly

```tsx
net: Number(r.net_gex_cr), lo: Number(r.session_min_net_gex_cr), hi: Number(r.session_max_net_gex_cr),
```

with exactly

```tsx
net: Number(r.net_gex_cr_1pct), lo: Number(r.session_min_net_gex_cr_1pct), hi: Number(r.session_max_net_gex_cr_1pct),
```

**9.** Replace every occurrence (3) of

```tsx
"v_gex_greeks_l2_net"
```

with exactly

```tsx
"v_gex_greeks_l2_net_1pct"
```

**10.** Replace exactly

```tsx
supabase.from("v_gex_greeks_l2_strike")
        .select("strike, n_legs, delta_drift_iv_cr_per_volpt, delta_drift_time_cr_per_day, gex_drift_iv_cr_per_volpt, gex_drift_time_cr_per_day, status")
```

with exactly

```tsx
supabase.from("v_gex_greeks_l2_strike_1pct")
        .select("strike, n_legs, delta_drift_iv_cr_per_volpt, delta_drift_time_cr_per_day, gex_drift_iv_cr_per_volpt_1pct, gex_drift_time_cr_per_day_1pct, status")
```

**11.** Replace exactly

```tsx
g_div: r.gex_drift_iv_cr_per_volpt != null ? Number(r.gex_drift_iv_cr_per_volpt) : null,
```

with exactly

```tsx
g_div: r.gex_drift_iv_cr_per_volpt_1pct != null ? Number(r.gex_drift_iv_cr_per_volpt_1pct) : null,
```

**12.** Replace exactly

```tsx
g_dt: r.gex_drift_time_cr_per_day != null ? Number(r.gex_drift_time_cr_per_day) : null,
```

with exactly

```tsx
g_dt: r.gex_drift_time_cr_per_day_1pct != null ? Number(r.gex_drift_time_cr_per_day_1pct) : null,
```

## src/lib/terrain.ts

**13.** Replace exactly

```tsx
supabase.from("v_gex_strike_terrain")
```

with exactly

```tsx
supabase.from("v_gex_strike_terrain_1pct")
```

**14.** Replace exactly

```tsx
dte, strike, gex_cr, oi_call,
```

with exactly

```tsx
dte, strike, gex_cr_1pct, oi_call,
```

**15.** Replace exactly

```tsx
gex: nn(r.gex_cr),
```

with exactly

```tsx
gex: nn(r.gex_cr_1pct),
```

## src/pages/Board.tsx

**16.** Replace exactly

```tsx
const net = n(abs?.net_gex_cr), gross = n(abs?.abs_gex_cr);
```

with exactly

```tsx
const net = n(abs?.net_gex_cr_1pct), gross = n(abs?.abs_gex_cr_1pct);
```

**17.** Replace every occurrence (3) of

```tsx
fl("net_gex_drift_time_cr_per_day")
```

with exactly

```tsx
fl("net_gex_drift_time_cr_per_day_1pct")
```

**18.** Replace every occurrence (2) of

```tsx
fl("gross_strike_gex_drift_time")
```

with exactly

```tsx
fl("gross_strike_gex_drift_time_1pct")
```

**19.** Replace every occurrence (3) of

```tsx
fl("net_gex_drift_iv_cr_per_volpt")
```

with exactly

```tsx
fl("net_gex_drift_iv_cr_per_volpt_1pct")
```

**20.** Replace every occurrence (2) of

```tsx
fl("gross_strike_gex_drift_iv")
```

with exactly

```tsx
fl("gross_strike_gex_drift_iv_1pct")
```

**21.** Replace exactly

```tsx
${ratio != null ? ` · ${ratio.toFixed(2)} of gross` : ""} · unit definition pending`
```

with exactly

```tsx
${ratio != null ? ` · ${ratio.toFixed(2)} of gross` : ""} · ₹ Cr per 1 % move`
```

**22.** Replace exactly

```tsx
sub: "₹ Cr · unit pending (E-D1)"
```

with exactly

```tsx
sub: "₹ Cr per 1 % move"
```

## src/pages/Home.tsx

**23.** Replace exactly

```tsx
const net = n(abs?.net_gex_cr), gross = n(abs?.abs_gex_cr);
```

with exactly

```tsx
const net = n(abs?.net_gex_cr_1pct), gross = n(abs?.abs_gex_cr_1pct);
```

## src/lib/read.ts

**24.** Replace exactly

```tsx
const net = n(abs?.net_gex_cr), gross = n(abs?.abs_gex_cr);
```

with exactly

```tsx
const net = n(abs?.net_gex_cr_1pct), gross = n(abs?.abs_gex_cr_1pct);
```

## src/components/board/LadderPanel.tsx

**25.** Replace exactly

```tsx
unit: "Cr (unit definition pending)", what: "Sum of signed dealer gamma exposure
```

with exactly

```tsx
unit: "₹ Cr per 1 % move", what: "Sum of signed dealer gamma exposure
```

**26.** Replace exactly

```tsx
computed: "v_gex_abs_exposure.net_gex_cr; net/gross = net_gex_cr ÷ abs_gex_cr."
```

with exactly

```tsx
computed: "v_gex_abs_exposure_1pct.net_gex_cr_1pct (= net_gex_cr × 0.01; stored γ·OI·S²/1e7 is per 100 % move, ADR-032); net/gross = net ÷ gross."
```

**27.** Replace exactly

```tsx
caveat: "Unit definition still open; compare sign and net/gross, not magnitude across days."
```

with exactly

```tsx
caveat: "Not normalised for time to expiry (the parity target scales by √(τ/5 d)); compare sign and net/gross across days, not magnitude."
```

**28.** Replace exactly

```tsx
g_gross: { title: "Gross |Γ|", unit: "₹ Cr (unit definition pending)"
```

with exactly

```tsx
g_gross: { title: "Gross |Γ|", unit: "₹ Cr per 1 % move"
```

**29.** Replace exactly

```tsx
computed: "v_gex_abs_exposure.abs_gex_cr."
```

with exactly

```tsx
computed: "v_gex_abs_exposure_1pct.abs_gex_cr_1pct (= abs_gex_cr × 0.01, ADR-032)."
```

**30.** Replace exactly

```tsx
caveat: "Unit still open; compare within a day, not magnitudes across days."
```

with exactly

```tsx
caveat: "Not normalised for time to expiry; compare within a day, not magnitudes across days."
```

**31.** Replace exactly

```tsx
g_net: { title: "Net Γ", unit: "₹ Cr (unit definition pending)"
```

with exactly

```tsx
g_net: { title: "Net Γ", unit: "₹ Cr per 1 % move"
```

**32.** Replace exactly

```tsx
computed: "v_gex_abs_exposure.net_gex_cr."
```

with exactly

```tsx
computed: "v_gex_abs_exposure_1pct.net_gex_cr_1pct (= net_gex_cr × 0.01, ADR-032)."
```

**33.** Replace exactly

```tsx
g_spark: { title: "Net Γ today", unit: "₹ Cr"
```

with exactly

```tsx
g_spark: { title: "Net Γ today", unit: "₹ Cr per 1 % move"
```

**34.** Replace exactly

```tsx
computed: "gamma_metrics.ts, net_gex for today, deduped by ts; drawn only with ≥3 runs."
```

with exactly

```tsx
computed: "v_gamma_metrics_1pct.ts, net_gex_1pct for today, deduped by ts; drawn only with ≥3 runs."
```

**35.** Replace exactly

```tsx
f_hedge: { title: "Hedge per 1 %", unit: "₹ Cr (unit definition pending)"
```

with exactly

```tsx
f_hedge: { title: "Hedge per 1 %", unit: "₹ Cr"
```

**36.** Replace exactly

```tsx
unit: "₹ Cr GEX per calendar day"
```

with exactly

```tsx
unit: "₹ Cr per 1 % move, per calendar day"
```

**37.** Replace exactly

```tsx
computed: "v_gex_greeks_l2_net.net_gex_drift_time_cr_per_day with gross_strike_gex_drift_time."
```

with exactly

```tsx
computed: "v_gex_greeks_l2_net_1pct.net_gex_drift_time_cr_per_day_1pct with gross_strike_gex_drift_time_1pct (× 0.01, ADR-032)."
```

**38.** Replace exactly

```tsx
unit: "₹ Cr GEX per +1 IV point"
```

with exactly

```tsx
unit: "₹ Cr per 1 % move, per +1 IV point"
```

**39.** Replace exactly

```tsx
computed: "v_gex_greeks_l2_net.net_gex_drift_iv_cr_per_volpt with gross_strike_gex_drift_iv."
```

with exactly

```tsx
computed: "v_gex_greeks_l2_net_1pct.net_gex_drift_iv_cr_per_volpt_1pct with gross_strike_gex_drift_iv_1pct (× 0.01, ADR-032)."
```

## src/pages/Lab3D.tsx

**40.** Replace exactly

```tsx
peak |γ| {num(max / 1e5, 1)}L · unit pending
```

with exactly

```tsx
peak |γ| ₹ {num(max)} Cr per 1 % move
```

**41.** Replace exactly

```tsx
Height = |net γ| per strike at each session's settled run (≤ 15:15 IST, v_gex_strike_terrain);
```

with exactly

```tsx
Height = |net γ| per strike (₹ Cr per 1 % move) at each session's settled run (≤ 15:15 IST, v_gex_strike_terrain_1pct);
```

## Reply with

Each file and each replacement number (old → new). If any quoted text does not occur exactly the stated number of times, change
nothing in that file and say which number.

---

## W — wording (APPROVED by the operator 2026-10-30 08:43 IST, caveats as revised)

| Where | Was | Becomes |
|---|---|---|
| Strip Net Γ sub-line | `· unit definition pending` | `· ₹ Cr per 1 % move` |
| Gamma tab Gross \|Γ\| sub | `₹ Cr · unit pending (E-D1)` | `₹ Cr per 1 % move` |
| Drawers Net Γ (both), Gross \|Γ\|, Net Γ today | `(₹) Cr (unit definition pending)` / `₹ Cr` | `₹ Cr per 1 % move` |
| Drawer Net Γ caveat | `Unit definition still open; compare sign and net/gross, not magnitude across days.` | `Not normalised for time to expiry (the parity target scales by √(τ/5 d)); compare sign and net/gross across days, not magnitude.` |
| Drawer Gross \|Γ\| caveat | `Unit still open; compare within a day, not magnitudes across days.` | `Not normalised for time to expiry; compare within a day, not magnitudes across days.` |
| Drawer Hedge per 1 % unit | `₹ Cr (unit definition pending)` | `₹ Cr` (the title already says "per 1 %") |
| Drawers ∂Γ/∂t, ∂Γ/∂σ units | `₹ Cr GEX per calendar day` / `per +1 IV point` | `₹ Cr per 1 % move, per calendar day` / `per +1 IV point` |
| Drawers "computed" lines | source column names | the `_1pct` view and column, "× 0.01, ADR-032" |
| 3D γ terrain peak label | `peak |γ| …L · unit pending` | `peak |γ| ₹ … Cr per 1 % move` |
| 3D γ note | `Height = |net γ| per strike at …` | `Height = |net γ| per strike (₹ Cr per 1 % move) at …` |

**Small values.** The formatters are unchanged, so a value below 0.5 now prints as `+0` (ladder readout, ∂Γ strike readouts on
far strikes). Read the smallest strikes on `/staging/` before promote; if `+0` appears where the old board showed a non-zero
number, that is a formatter decision for the operator, not part of this round.

Not in this round: the legacy pages (Positioning / Context / Structure / Max Pain / Expiry Memory — inventory A9–A10; rescale or
retire, operator's call), the in-app manual text (inventory §3D, engine `docs/marketview_manual/` → `build_help_pack.py`, restated
in the same change as this round's promote), and dead code (inventory §3E).

## Checks (Claude / operator) — every one before promote

1. **Guard** (s92 guard, round copy with line 34's allowlist →
   `src/lib/board.ts|src/lib/terrain.ts|src/lib/read.ts|src/pages/Board.tsx|src/pages/Home.tsx|src/pages/Lab3D.tsx|src/components/board/LadderPanel.tsx`):
   exactly these seven paths M; no new table / view names other than the seven `_1pct` views; no credentials; tsc + build clean.
   Diff fingerprint: the replacement count per file in the reply equals this prompt's (board.ts 14 sites, terrain.ts 3, read.ts 1,
   Home.tsx 1, Board.tsx 13, LadderPanel.tsx 15, Lab3D.tsx 2 — occurrences, not lines).
2. **Network** (staging, Chrome): the board requests `v_gex_abs_exposure_1pct`, `v_gex_strike_snapshots_1pct` (ladder),
   `v_gamma_metrics_1pct` (Net Γ today), `v_gex_net_gamma_river_1pct`, `v_gex_greeks_l2_net_1pct`, `v_gex_greeks_l2_strike_1pct`,
   `v_gex_strike_terrain_1pct`, and **no longer** their unsuffixed sources from these hooks (`v_gex_abs_exposure`,
   `v_gex_net_gamma_river`, `v_gex_greeks_l2_net`, `v_gex_greeks_l2_strike`, `v_gex_strike_terrain`; `gamma_metrics` and
   `gex_strike_snapshots` stay requested by other hooks).
3. **Values** (staging vs SQL at the same `ts`, both symbols): strip Net Γ = `v_gex_abs_exposure_1pct.net_gex_cr_1pct`; Gross =
   `abs_gex_cr_1pct`; "x of gross" unchanged from live; one ladder strike readout = `gex_cr_1pct`; Net Γ today caption first/last =
   `v_gamma_metrics_1pct.net_gex_1pct`; river hover one day = `net_gex_cr_1pct`; ∂Γ/∂t and ∂Γ/∂σ net/gross = the `_1pct` columns;
   3D peak = max |`gex_cr_1pct`|; **and the strip Net Γ equals −(Hedge per 1 % at +1 %)** within rounding (T2's identity, on the board).
4. **Unchanged** (staging = live): every delta-type tile (Net/Call/Put DEX, ∂Δ/∂t, ∂Δ/∂σ, S*), Hedge per 1 % values, pin shares,
   HHI, net/gross, the read sentence, ladder bar shapes and silhouette zero crossings.
5. **Mutant** (Claude, before the round is pasted): T1's `same_as_x1` / `same_as_x01` columns are the view-level mutants; on the board,
   check 3's −(Hedge per 1 %) identity fails by 100× if any hook still reads an unsuffixed column.
