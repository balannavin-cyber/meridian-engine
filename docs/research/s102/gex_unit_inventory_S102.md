# Γ-size unit — inventory and display-only plan (S102, 2026-10-30, v2)

**v2 (06:5x IST):** re-checked by an independent read of both trees (engine `3abb83f`, board `27c0e17`), not anchored on v1;
every change from v1 was spot-checked in the code before being written. **Corrections to v1** are listed in §6.

**Question (operator, 2026-10-30 06:32 IST):** the board shows Net Γ in "L Cr"; against the parity target it should be in the
thousands. **Answer: the stored unit is 100 × "₹ Cr per 1 % move".**

## 1. The unit

`merdian_compute/gamma.py:54`: `gex_cr = γ · OI · S² / 1e7` per option, PE negated. OI is lot-inclusive quantity (shares)
(`sql/2026-10-09_s93_v_dex_standing_book.sql:418`; S97 F1 recomputed one strike by hand = stored). The conventional figure —
₹ Cr of delta-notional to re-hedge per **1 %** move — is `× 0.01`. So one stored unit = ₹ 1 Cr per **100 %** move.

**The only object that applies the 0.01 is `v_dealer_flow_sim.flow_cr`** (`= −net_gex × pct`, pct ∈ {±0.005, ±0.01, ±0.02}).
Every other "Cr" / "L Cr" gamma figure on the board is 100 × the per-1 % number.

**No decision reads the magnitude.** Regime, flip side and the pin-risk base use the sign; concentration, HHI, shares, net/gross,
runner-up ratio, pin/accel τ × peak use ratios; a constant factor cancels (code read on `3abb83f`, both reads agree).

## 2. Storage (all at the base scale ×1 unless stated)

| Object | Column(s) | Read by the board |
|---|---|---|
| `gex_strike_snapshots` | `gex_cr` (CE + PE per strike) | yes |
| `gamma_metrics` | `net_gex` | yes |
| `gex_cycle_history` | `net_gex`, `gamma_at_pin` | `gamma_at_pin` selected, **never rendered** |
| `gex_pin_maxpain_history` | `peak_pin_gex_cr` | no |
| `market_state_snapshots.gamma_features`, `signal_snapshots`, `structural_divergence_snapshots` | `net_gex` (copied through) | no (`signal_snapshots` is read `select *`, `net_gex` not rendered) |
| `hist_gamma_metrics` | `net_gex` | no — **unit contradictory** (§5) |
| `v_gex_abs_exposure` | `net_gex_cr`, `abs_gex_cr` | yes |
| `v_gex_strike_rank` | `gex_cr`, `abs_gex_cr` (+ shares) | shares only; `gex_cr` for tint sign |
| `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` | `total_pin_gex_cr`, `peak_pin_gex_cr` / `total_accel_gex_cr`, `trough_gex_cr` | strikes, n, τ only |
| `v_gex_net_gamma_river` | `net_gex_cr`, `session_min_net_gex_cr`, `session_max_net_gex_cr` | yes |
| `v_gex_strike_terrain` | `gex_cr` | yes (3D) |
| `v_pin_board` | `gamma_at_pin` | not rendered |
| `v_gex_greeks_l2_strike` / `_net` | `gex_drift_iv_cr_per_volpt`, `gex_drift_time_cr_per_day` (+ `net_*`, `gross_strike_*`) — **S² basis, same missing 0.01** | yes |
| `v_dealer_flow_sim` | `net_gex` ×1; **`flow_cr` already per-1 % at ±1 %** | `flow_cr` |

**Delta-type (scale `oi · S / 1e7`, a true ₹ Cr of delta-notional) — out of scope, must not be rescaled:** `v_dex_standing_book`,
`v_dex_flow_vs_book`, `v_dex_repriced_zero`, `v_delta_drift_flow_vs_book`, and the ∂Δ/∂t, ∂Δ/∂σ columns of `v_gex_greeks_l2_*`.

## 3. Board surfaces

### A. A Γ size shown as a number — rescale ÷ 100 and label "₹ Cr per 1 % move"

| # | Surface | Source | Shown as |
|---|---|---|---|
| A1 | Strip **Net Γ**; Overview "Net Γ" + caption + drawer | `v_gex_abs_exposure.net_gex_cr` | value, "L Cr / Cr · unit definition pending" |
| A2 | Gamma tab **Net Γ**, **Gross \|Γ\|** + drawers | `net_gex_cr`, `abs_gex_cr` | value |
| A3 | Overview / Gamma **ladder** readout column + hover | `gex_strike_snapshots.gex_cr` (`board.ts:288`, direct table read) | per-strike value, hover "… Cr" (bars are relative) |
| A4 | Gamma tab **Net Γ today** caption ("moved from X to Y") | `gamma_metrics.net_gex` (`board.ts:351`, direct table read) | caption value (spark relative) |
| A5 | Gamma tab **gamma river** y-axis labels + hover | `v_gex_net_gamma_river` | axis "…L" (no "Cr"), hover "settled … Cr · range …" |
| A6 | 3D γ terrain **peak label** | `v_gex_strike_terrain.gex_cr` | "peak \|γ\| …L · unit pending" (surface relative) |
| A7 | Flows **∂Γ/∂t, ∂Γ/∂σ** tiles (net / gross) | `v_gex_greeks_l2_net` gamma pair | values |
| A8 | Flows ladder with ∂Γ/∂t or ∂Γ/∂σ selected — readout + hover | `v_gex_greeks_l2_strike` gamma pair | per-strike value, "… Cr" |
| A9 | Legacy pages — SnapshotStrip **NET γ** (Positioning, Context / Breadth, Structure, Max Pain, Expiry Memory) | `gamma_metrics.net_gex` (direct) | "… Cr", full digits |
| A10 | Legacy Positioning — **Net Dealer γ** tile + "Σdmp …k · Σamp …" sub; **Max γ Strike** "pk +X Cr"; HeroChart scalars "net γ in window / Σ dampen / Σ amplify"; **Net Dealer γ · Intraday** big value + y-axis labels | `gamma_metrics.net_gex`, `gex_strike_snapshots.gex_cr` (direct) | values; **"k" suffix on Σdmp is a mislabel** (value is in Cr) |

### B. Already per-1 % — number right, label only

| # | Surface | Source | Change |
|---|---|---|---|
| B1 | Flows **Hedge per 1 %** tile, "Hedge flow vs spot move" chart, Home card 5 | `v_dealer_flow_sim.flow_cr` | drop "unit definition pending"; **do not rescale** |

### C. Unaffected — relative drawing, sign or ratio (no number of Γ size shown)

Ladder bar lengths, silhouette, mini-map; Net Γ today spark; river geometry; 3D surface; legacy HeroChart bars; the SplitBar and
"x of gross"; Pin tab ladder (value = `share_of_abs`, tint = sign of `gex_cr`); Pin / runner-up / lead / HHI / conviction tiles;
the read sentence's pocket word (sign of the nearest strike's `gex_cr`); Home card 3; Rising / Falling; regime words; pin-risk and
expansion scores; pin / accel zone strikes.

### D. Text that quotes a magnitude — restate after the rescale

`public/help/manual.json` (in-app manual v0.4): 12 "L Cr" figures, 3 "unit definition pending", worked examples (e.g. Context
"−13,81,560.7 Cr", Gross "10.5L Cr", ∂Γ/∂t "−4.7L Cr / 40.5L Cr"), the status-word row "unit pending (E-D1)" and the glossary
"Cr / L Cr". Source: `docs/marketview_manual/` (engine) → `build_help_pack.py`. Flow figures (SELL 9,201 / 13,816 Cr) already per-1 %.

### E. Dead code (imported nowhere) — no change; record only

`NarrativeModal.tsx` (would show "Net dealer γ … Cr"), `AmbientTrajectory.tsx`, `mockData.ts`, `pages/Index.tsx` (not routed),
hook `useDealerFlow`.

## 4. Display-only design (ruling "1", 2026-10-30)

- **One conversion, in the database** (S92-G / S92-J). `*_cr_per_1pct` = existing × 0.01, added beside the existing columns (kept
  for other readers and the retail contract §8) on: `v_gex_abs_exposure`, `v_gex_net_gamma_river`, `v_gex_strike_terrain`,
  `v_gex_greeks_l2_net` and `v_gex_greeks_l2_strike` (gamma pair only). The direct table reads (A3, A4, A9, A10) move to thin views
  carrying the per-1 % column, so the board never multiplies.
- **Not rescaled:** `flow_cr` (B1) and every delta-type column (§2).
- **Board:** one Lovable round for A1–A10 (A9–A10 are legacy pages — rescale or retire, operator's call) and the B1 label; the
  "k" mislabel fixed with A10; the manual (D) restated in the same change.
- **Before any test relies on a view, confirm its live definition by md5 (rule 25):** `v_gex_abs_exposure`, `v_gex_strike_rank`,
  `v_gex_concentration`, `v_gex_net_gamma_river`, `v_dealer_flow_sim` have no md5 capture.
- **Tests, before the board sees anything:** (1) per view, `*_cr_per_1pct = 0.01 × existing` on every row of the latest run;
  (2) independent path: per-1 % net Γ = `−flow_cr` at +1 % on the same run; (3) mutants ×1 and ×0.1 fail (1)–(2);
  (4) per surface A1–A10 / B1, a `/staging/` read in Chrome against a SQL value at the same `ts`. Promote only when all pass.
- **Order:** views first (additive, "views any time"), verified; then the Lovable round on `/staging/`; then promote.

## 5. Open for the ADR-032 study (not resolved here)

1. `hist_gamma_metrics.net_gex` unit: `backfill_gamma_metrics.py:83` divides by 1e7, `fill_gamma_concentration.py:72,104` treats the
   table as unscaled; its writer and its s62 DDL also disagree on columns. Not read by the board.
2. `gamma_metrics` rows before 2026-05-11 (TD-NEW-3) were unscaled; whether any remain live depends on retention history.
3. The OI unit of `backfill_gamma_metrics_to_main.py`'s vendor source is not stated.
4. Sign conventions differ between L7/L8 / delta-drift (PE negated) and DEX (not) — a sign matter, not scale; do not mix in a
   rescale.

## 6. Corrections to v1

- **v1 A4 (Pin tab rank values) was wrong** — the Pin ladder shows `share_of_abs`; `gex_cr` sets the tint's sign only → §3C.
- **v1 A5 (local-γ pocket value) was wrong** — no value is shown; the sentence uses the sign only → §3C.
- **v1 A6 (Γ at pin) was wrong** — `gamma_at_pin` is selected and never rendered → §2 only.
- **Added:** A8 (∂Γ strike ladder readout); A5 / A6 axis and label text that shows numbers; A9–A10 broken out by tile with the
  "k" mislabel; §3D the in-app manual; §3E dead code; storage copies and `hist_gamma_metrics` (§2, §5); the md5 precondition (§4).
- v1's B1 (flow per-1 %), the delta-type exclusion and "no decision reads the magnitude" stand.
