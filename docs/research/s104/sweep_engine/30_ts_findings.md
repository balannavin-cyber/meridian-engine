# 30_ts_findings — board tree `~/meridian-connect` @ 6f14a92 (prompt §3 item 4)

129 tracked files: 81 `.tsx`, 9 `.ts`, 1 `.js`, 1 `.css`, 1 `.html`, 6 `.json`, 21 `.jpg`, 3 `.md`,
1 `.lock`, 1 `.toml`, 4 extensionless. All text files swept; the 21 `.jpg` are the only files not read.

## 1. Every `supabase.from("…")` target that carries a Γ size, and its `.select(…)`

Scale column: **A** = stored `γ·OI·S²/1e7` (per 100 % move) · **B** = `× 0.01` (per 1 % move).

| file:line | relation | select | scale delivered |
|---|---|---|---|
| `src/lib/board.ts:95,99` | `v_gex_strike_rank` | `run_id` / `strike, strike_rank, share_of_abs, ts` | **ratio only** — no Γ size crosses the wire |
| `src/lib/board.ts:132,137` | `gex_strike_snapshots` **(RAW TABLE)** | `run_id, spot, ts` / **`strike, gex_cr`** | **A** |
| `src/lib/board.ts:153,162` | `gamma_metrics` **(RAW TABLE)** | `ts, spot` / `vix, ts` | no Γ size selected |
| `src/lib/board.ts:223` | `v_gex_max_pain` | `max_pain_strike, ts, is_fresh` | none |
| `src/lib/board.ts:236,240` | `v_dealer_flow_sim` | `run_id` / `spot_pct, flow_cr, direction` | `flow_cr` = true ₹ Cr (`−net_gex × pct`) |
| `src/lib/board.ts:285,289` | `v_gex_strike_snapshots_1pct` | `run_id, ts, spot` / (see §2) | **B** |
| `src/lib/board.ts:328` | `v_gex_max_pain` | `candidate_strike, total_pain, max_pain_strike, max_pain_value, …` | pain, not Γ |
| `src/lib/board.ts:353` | `v_gamma_metrics_1pct` | `ts, net_gex_1pct` | **B** |
| `src/lib/board.ts:371` | `v_gex_net_gamma_river_1pct` | `session_date, net_gex_cr_1pct, session_min_…_1pct, session_max_…_1pct, …` | **B** |
| `src/lib/board.ts:435` | `v_pin_board` | `… , **gamma_at_pin**, …` | **A** — and never consumed (§4) |
| `src/lib/board.ts:448,452` | `v_gex_strike_rank` | `run_id` / (strike-rank fields) | ratio only |
| `src/lib/board.ts:471,475` | `v_gex_greeks_l2_net_1pct` | `ts` / **`*`** | **A and B in the same row** (§3) |
| `src/lib/board.ts:488` | `v_gex_greeks_l2_strike_1pct` | explicit column list | **B** (+ raw A columns the wrapper keeps) |
| `src/lib/board.ts:509` | `v_dex_standing_book` | explicit | Δ-type, **not** a Γ size |
| `src/lib/board.ts:529` | `v_dex_flow_vs_book` | 25 explicit `*_dex_cr` / `*_flow_cr` | Δ-type, **not** Γ |
| `src/lib/board.ts:555` | `v_delta_drift_flow_vs_book` | explicit `leg_iv_*_cr`, `leg_t_*_cr` | Δ-type, **not** Γ |
| `src/lib/board.ts:577` | `v_dex_repriced_zero` | — | Δ-type |
| `src/lib/queries.ts:35,36` | `v_gamma_metrics_1pct` | **`*`** | **A and B in the same row** |
| `src/lib/queries.ts:54,75` | `gamma_metrics` **(RAW TABLE)** | `ts, spot, straddle_atm` / `ts, straddle_atm` | no Γ size |
| `src/lib/queries.ts:183,194,204` | `v_gex_strike_snapshots_1pct` | `run_id, ts` / `strike, gex_cr_1pct, oi_call, oi_put, spot` | **B** |
| `src/lib/queries.ts:222,223` | `v_gex_strike_pin_zone` **(NO WRAPPER)** | **`*`** | **A** — `peak_pin_gex_cr`, `total_pin_gex_cr` |
| `src/lib/queries.ts:242,243` | `v_gex_strike_accel_zone` **(NO WRAPPER)** | **`*`** | **A** — `trough_gex_cr`, `total_accel_gex_cr` |
| `src/lib/queries.ts:279,288,289` | `v_dealer_flow_sim` | `run_id, ts` / **`*`** | **A (`net_gex`) beside derived-B (`flow_cr`)** |
| `src/lib/queries.ts:385,386` | `v_gamma_metrics_1pct` | `ts, spot, pin_risk_score, straddle_atm, expansion_probability, net_gex_1pct` | **B** |
| `src/lib/queries.ts:463` | `v_max_pain_by_strike` | — | pain, not Γ |
| `src/lib/terrain.ts:23` | `v_gex_strike_terrain_1pct` | `… gex_cr_1pct …` | **B** |

Every `select("*")` over a Γ-carrying relation: `board.ts:475`, `queries.ts:36`, `queries.ts:223`,
`queries.ts:243`, `queries.ts:289`. **Four of the five were missed by the line-scoped token sweep**
because the relation name sits on the previous line — see `90_report.md` §5.

## 2. The alias layer — the single most consequential thing in this tree

`src/lib/queries.ts` fetches the per-1 % column and **renames it back to the scale-A name**:

```
queries.ts:43    return data ? { ...(data as any), net_gex: (data as any).net_gex_1pct } : data;
queries.ts:210   return (data ?? []).map((r: any) => ({ ...r, gex_cr: r.gex_cr_1pct }));
queries.ts:392   return (data ?? []).map((r: any) => ({ ...r, net_gex: r.net_gex_1pct }));
```

Consequence, measured: in `src/marketview/*` the field names `net_gex` and `gex_cr` carry
**scale B**, while in `src/lib/board.ts:137` the field name `gex_cr` carries **scale A**, read
straight from the `gex_strike_snapshots` table. One app, one field name, two scales 100× apart.

Who consumes the aliased (scale-B) values:
- `marketview/state.ts:47` `netDealerGamma = g.net_gex` → rendered `sections.tsx:33,75,110,142`
- `marketview/state.ts:60-68` `peakGammaCr`, `dampenTotal`, `amplifyTotal` from `s.gex_cr`
  → rendered `sections.tsx:87,111,112,150,151`
- `marketview/ui.tsx:251,327,328` bar heights from `b.gex_cr`; `ui.tsx:500-518` `NetGammaIntraday` from `r.net_gex`
Who consumes the scale-A `gex_cr`: `src/lib/read.ts:14,29` (`useSpotPocket`) — **sign only**
(`pocket.gex_cr >= 0 ? "a dampening" : "an amplifying"` pocket), so it is correct either way.

## 3. The wrappers keep the raw column

Every `_1pct` view is additive: it returns **every source column unchanged** and appends the
`_1pct` ones (measured from the live definitions — `40_db_findings.md` §3). So a `select("*")`
on a wrapper hands the client both scales under names that differ only by a suffix.
`board.ts:475` and `queries.ts:36` both do exactly that.

## 4. Fields fetched and never rendered
- `board.ts:435` selects `gamma_at_pin` from `v_pin_board`; `git grep gamma_at_pin -- src/**`
  returns that one line. Fetched, scale A, dropped.
- `queries.ts:223` / `:243` `select("*")` on the pin/accel views: `marketview/state.ts:25,26`
  holds them as `pin`/`accel` and `sections.tsx:89,90,92,93,117` renders only **strike levels**
  (`pin_lower`, `pin_upper`, `peak_pin_strike`, `accel_lower`, `accel_upper`). The four Γ
  magnitudes in those rows reach the client and are never displayed.

## 5. Formatters applied to a Γ value — all three branch on the same magnitude

| file:line | formatter | branch |
|---|---|---|
| `src/pages/Board.tsx:27` | `crLakh(v)` | `\|v\| >= 1e5 ? "<v/1e5>L Cr" : "<v> Cr"` — **the unit WORD changes** |
| `src/pages/Board.tsx:197` | `lad(v)` | `\|v\| >= 1e5 ? "<v/1e5>L" : "<v>"` — per ladder strike |
| `src/components/board/GammaRiver.tsx:7` | `lak(v)` | `\|v\| >= 1e5 ? "<v/1e5>L" : "<v>"` — on `net_gex_cr_1pct` |

`crLakh` users: `Board.tsx:208,209,265,266,268,269,277,444(fmtCr),587`. `lad`: `Board.tsx:198`.
`lak`: inside `GammaRiver`, fed by `useGammaRiver` → `v_gex_net_gamma_river_1pct` (**scale B**).
No test covers any of the three. Scale-free formatters, applied to Γ sizes with no unit suffix of
their own: `fmtNum`, `fmtSigned`, `fmtPct`, `num`, `sgn` (`marketview/ui.tsx:32-41`, `Board.tsx:23-25`).
`fmtBillion` (`ui.tsx:44`) has `1e9/1e6/1e3` branches and **is** used, at `ui.tsx:388` — but on
`total_pain` (the max-pain y-axis in `MaxPainChart`), which is writer pain, not a Γ size. Stated
this way because my first pass asserted "its definition only" and the grep returned two lines;
the conclusion survived, the evidence for it did not.

## 6. UI strings stating a unit (26 string literals; the Γ-relevant ones)

Saying **"₹ Cr per 1 % move"**: `Board.tsx:265,587`, `marketview/sections.tsx:33,79,108,138`,
`LadderPanel.tsx:19,26,27,30`, `Lab3D.tsx:147,251`.
Saying **"per 100 % move"**: `LadderPanel.tsx:19` only — inside the `computed:` prose, as the
explanation of the stored unit.
Saying only **"₹ Cr"** / **" Cr"** with no per-move qualifier, on a Γ size:
- `Board.tsx:518` `"Hedge flow vs spot move (₹ Cr)"` — correct, `flow_cr` IS plain ₹ Cr.
- `Board.tsx:27` the `crLakh` fallback branch emits bare `" Cr"`.
- **`src/components/NarrativeModal.tsx:42`** `["Net dealer γ", fmt(state.netDealerGamma, " Cr")]`
- **`src/components/NarrativeModal.tsx:91`** `Net dealer γ of {fmt(state.netDealerGamma, " Cr")} …`
`LadderPanel.tsx:19,26,27,30` carry `src: "sql/ file · COMMENT not live"` — a claim about the
database, so I measured it. Of 16 Γ views checked for a relation COMMENT, **15 have one and
exactly one does not: `v_gex_abs_exposure`**. The four badged entries name
`v_gex_abs_exposure_1pct` and `v_gamma_metrics_1pct` in their `computed:` text, and **both of
those DO carry a live relation COMMENT**. So the badge is true of the underlying
`v_gex_abs_exposure` and false of the wrapper the row actually reads. Reported, not judged;
`f_gdt`/`f_gdiv` at `:52,53` carry `src: "v_gex_greeks_l2_net · COMMENT live"`, which is correct.

## 7. Mocks and dead code (listed, not judged — prompt §3 item 4)
- `src/lib/mockData.ts:31` `gex_cr: number; // signed`, `:101` `out.push({ strike, gex_cr: +(pinComp + accelComp + noise).toFixed(1) })`
  — invented Γ values, no stated scale. `git grep mockData -- src/**` → imported by nothing.
- `src/components/NarrativeModal.tsx` — `export function NarrativeModal` at `:30`; the only
  other mention of the name in the tree is that line. Not imported, not routed. It holds the
  two incomplete unit labels above.
- `src/marketview/state.ts:59` returns a zeroed shape when `rows` is empty — `peakGammaCr: null`,
  not `0` (correct per CLAUDE.md "NULL is a gap, never a zero").
