# 40_db_findings — live database, read through `bin/roq.sh` as `merdian_ro` (prompt §3 item 5)

`current_user = merdian_ro`, `current_database = postgres`, PostgreSQL 17.6 on aarch64.
All SELECT, `default_transaction_read_only=on`, `statement_timeout=30s`. No statement timed out.

## 0. WHAT THIS ROLE IS NOT ALLOWED TO READ — stated first, because it bounds everything below

| Target | Result | Consequence for this sweep |
|---|---|---|
| `pg_stat_statements` | `ERROR: relation "pg_stat_statements" does not exist` — **the extension IS installed** (`pg_extension` lists it) but the relation is not granted to `merdian_ro` | **Prompt §3 item 5(f) CANNOT BE ANSWERED.** This sweep cannot enumerate readers that exist only as query traffic — a PostgREST caller, a Lovable preview, a Retool/n8n job, a hand-run editor query. Every reader named in this report came from a repo or the catalog. |
| `cron.job` | `ERROR: permission denied for schema cron` | Cannot list `pg_cron` jobs. CLAUDE.md records jobid 19 `cleanup_gamma_engine_daily()` at `30 12 * * *`, `active=false`; that is **not** re-verified here and belongs to the editor under postgres (CLAUDE.md data-access rule). |

Both are the TD-S81-NEW-16 shape: a zero from this role would be the **reader**, not the state.
Neither was worked around.

## 1. The Γ-size column inventory — 94 columns, 8 carry a unit COMMENT

Query: every `pg_attribute` in `public` on a relkind in `(r,v,m,p)` whose name matches
`(^|_)(net_)?gex(_|$) | gex_cr | gamma_at_pin | net_gamma | gex_drift | total_gex | gamma_load | abs_mass | signed_mass | netgex | gamma_exposure`,
joined to `pg_description`. **94 rows.** Full output: §1 of `41_db_raw.txt`.

**Base tables (`relkind='r'`) — 19 Γ-ish columns, 8 commented, 11 not:**

| table.column | unit COMMENT? |
|---|---|
| `gamma_metrics.net_gex` | **ADR-032** |
| `gex_cycle_history.gamma_at_pin` | **ADR-032** |
| `gex_cycle_history.net_gex` | **ADR-032** |
| `gex_pin_maxpain_history.peak_pin_gex_cr` | **ADR-032** |
| `gex_strike_snapshots.gex_cr` | **ADR-032** |
| `hist_gamma_metrics.net_gex` | **ADR-032** (and it records a **THIRD scale** — see §5) |
| `signal_snapshots.net_gex` | **ADR-032** |
| `structural_divergence_snapshots.net_gex` | **ADR-032** |
| `gamma_metrics_replay.net_gex` | NO COMMENT |
| `gamma_metrics_shadow.net_gex` | NO COMMENT |
| `hist_market_state.net_gex` | NO COMMENT |
| `signal_snapshots_replay.net_gex` | NO COMMENT |
| `signal_snapshots_shadow.net_gex` | NO COMMENT |
| `structural_divergence_snapshots_replay.net_gex` | NO COMMENT |
| `study_recon_accel.total_accel_gex_cr` | NO COMMENT |
| `study_recon_pin.total_pin_gex_cr` | NO COMMENT |
| `expiry_outcomes.gex_regime_persistence` | NO COMMENT — a persistence ratio, not a size |
| `market_environment_snapshots.gex_regime_persistence_20d` | NO COMMENT — ratio, not a size |
| `market_environment_snapshots.net_gex_regime` | NO COMMENT — `text`, a regime WORD |

So the eight commented columns are the **live** and **historical** carriers; the six `_shadow` /
`_replay` siblings and the two `study_recon_*` tables hold the same quantity at the same stored
scale with nothing written on them. **75 view columns: 0 have a column COMMENT.**

## 2. Views and functions that mention a Γ token, with identity (prompt §3 item 5a/5b)

**53 views** mention `gex|gamma|dealer_gamma|zone_signed_mass|total_abs_mass`.
**0 materialized views exist anywhere in the cluster** (`relkind='m'` → 0; `relkind='v'` in
`public` → 82, so the catalog is readable and the zero is real).
Each view's `length(pg_get_viewdef(oid,true))` and `md5(...)` are in §2 of `41_db_raw.txt`
— per CLAUDE.md rule 25, that md5 is the only identity for "which `sql/` file is live", and
**this sweep did not attempt to match any file to any view**; it records the md5 so the operator can.

The 20 Γ views that matter, by what they deliver:

| view | deflen | defmd5 | `gex_cr` | `net_gex` | scale literal |
|---|---|---|---|---|---|
| `v_gex_abs_exposure` | 1378 | `2787513ebf09dd0106ad723a8d5a47da` | yes | yes | — |
| `v_gex_abs_exposure_1pct` | 251 | `a587187e89ac4a35b12415d0e9f636ca` | yes | yes | `0.01` |
| `v_gamma_metrics_1pct` | 501 | `8e9908e26bbf496702a10811708bf413` | — | yes | `0.01` |
| `v_gex_strike_snapshots_1pct` | 240 | `670e13d9d601a602940bdfaaddb39104` | yes | — | `0.01` |
| `v_gex_strike_terrain` | 6463 | `c3beee55f60488da6dc20430f6b33981` | yes | — | — |
| `v_gex_strike_terrain_1pct` | 298 | `df14f1c1b991434b7c452e981deab526` | yes | — | `0.01` |
| `v_gex_net_gamma_river` | 2403 | `cea9d5c8e405c8bd30c2f99290b98cd9` | yes | yes | — |
| `v_gex_net_gamma_river_1pct` | 423 | `7192428ee50f412e58368e83e9a7f308` | yes | yes | `0.01` |
| `v_gex_greeks_l2_net` | 1546 | `8962836c9839711b299aac4000cecbf9` | — | yes | — |
| `v_gex_greeks_l2_net_1pct` | 986 | `34e5c9b7b289486c89b5735244e42cf2` | — | yes | `0.01` |
| `v_gex_greeks_l2_strike` | 4028 | `66cfb53bd8fb63a445977d236b9d62d6` | — | — | **`10000000`** |
| `v_gex_greeks_l2_strike_1pct` | 602 | `42e8ff77afbf959f8491eb18a63879f1` | — | — | `0.01` |
| `v_gex_greeks_l2_leg` | 9656 | `838ad0a62dd638068e80a43b716597ba` | — | — | — |
| **`v_gex_concentration`** | 2140 | `c4cf15aa43fdb932b56db77cefee7188` | **yes** | — | — |
| **`v_gex_strike_pin_zone`** | 3523 | `89c9ac6aef9eb332ddd28f9062d0e21e` | **yes** | — | — |
| **`v_gex_strike_accel_zone`** | 3547 | `87a0691ef33ef5e08cbf315fd6511064` | **yes** | — | — |
| **`v_gex_strike_rank`** | 4002 | `0ab189a40cd648e8cc0e8f77b55cc5f6` | **yes** | — | — |
| **`v_gex_repriced_flip`** | 10260 | `58ad6ba8f366c52a8e71b4ac1ea66864` | — | — | **`10000000`** |
| `v_dealer_flow_sim` | 1784 | `781e40e126944f2736b93f22e1558c6f` | — | yes | `0.01` (**a MOVE, not a unit** — §4) |
| `v_pin_board` | 2922 | `9a827e8155e188db9ab9cd9b4fc429e0` | — | yes | — |

**Bold rows carry a Γ size and have NO `_1pct` sibling.** There are exactly **7** `_1pct` wrappers:
`v_gamma_metrics_1pct`, `v_gex_abs_exposure_1pct`, `v_gex_greeks_l2_net_1pct`,
`v_gex_greeks_l2_strike_1pct`, `v_gex_net_gamma_river_1pct`, `v_gex_strike_snapshots_1pct`,
`v_gex_strike_terrain_1pct`. Unwrapped Γ-size views: `v_gex_abs_exposure` (has a wrapper, but the
base is readable), `v_gex_concentration`, `v_gex_strike_pin_zone`, `v_gex_strike_accel_zone`,
`v_gex_strike_rank`, `v_gex_strike_walls`, `v_gex_max_pain`, `v_gex_pin_maxpain`,
`v_gex_repriced_flip`, `v_gex_greeks_l2_leg`, `v_gex_greeks_l2_strike`, `v_pin_board`,
`latest_gamma_metrics`, `latest_gamma_metrics_v2`, `latest_signal_inputs`,
`latest_signal_inputs_v2`, `latest_signal_snapshots`, `signal_outcome_research_v1`,
`signal_outcome_research_v2`, `wcb_signal_validation_v1`, `wcb_signal_validation_v2`,
`v_dealer_flow_sim`, `latest_signal_intraday`, `shadow_signal_validation_v1`,
`signal_outcome_audit_dedup`, `latest_net_gamma_by_strike`, `latest_gamma_walls`,
`latest_top_gamma_strikes`, `latest_atm_neighborhood`, `v_run_trace`.

**Functions: 15 whose `prosrc` mentions `gex|gamma`** (13 in `public`, 2 in `realtime` and
unrelated). `proname`, identity args, `length(prosrc)` and `md5(prosrc)` in §3 of `41_db_raw.txt`.

## 3. Every scale literal in a Γ view, with its context (measured, not inferred)

Query form: `regexp_matches(pg_get_viewdef(oid,true), '(.{0,100}(?:10000000|1e7|0\.01).{0,70})', 'g')`
over all 53 Γ views → 33 fragments. Grouped by what the literal is DOING:

**(a) `/1e7` — an independent re-implementation of the Γ formula, IN SQL, at scale A**
- `v_gex_greeks_l2_strike`: `b.sgn * b.u_gex_drift_iv * b.oi * power(b.spot, 2) / 10000000 AS leg_gex_drift_iv`
  and the same for `leg_gex_drift_time`. **Γ-type (S²).** The same SELECT also builds
  `leg_delta_drift_time` / `leg_delta_drift_iv` as `… * b.oi * b.spot / 10000000` — **Δ-type (S¹)**.
  → **this view MIXES a Γ size and a Δ size in one SELECT list**, which prompt §2 asks for explicitly.
- `v_gex_repriced_flip`: `exp(…)/(gr.s_grid * l.sigma * sqrt(e.t_years)) * l.oi * power(gr.s_grid, 2) / 10000000 AS total_gex`
  — a **full Black–Scholes γ recomputed from scratch** on an ENH-131 spot grid, then scaled to
  scale A, published as **`total_gex`**. Not `gex_cr`, not `net_gex`. A Γ size under a name the
  §2 token list does not contain.

**(b) `/1e7` — Δ-type only, NOT a Γ size (listed because prompt §2 asks for the mixing sites)**
`v_delta_drift_flow_vs_book` (12 fragments, all `… * j.spot / 10000000` → `*_iv_flow_cr`,
`*_t_flow_cr`, `*_iv_preopen_cr`, `*_t_preopen_cr`); `v_dex_repriced_zero`
(`… * l.oi * gr.s_grid / 10000000` → `gross_dex`, `total_dex`). One power of spot. Correct as is.

**(c) `× 0.01` — the ADR-032 D1 conversion. Exactly 14 columns across 7 wrappers:**

| wrapper | converted columns |
|---|---|
| `v_gamma_metrics_1pct` | `net_gex * 0.01 AS net_gex_1pct` |
| `v_gex_abs_exposure_1pct` | `net_gex_cr * 0.01`, `abs_gex_cr * 0.01` |
| `v_gex_strike_snapshots_1pct` | `gex_cr * 0.01 AS gex_cr_1pct` |
| `v_gex_strike_terrain_1pct` | `gex_cr * 0.01 AS gex_cr_1pct` |
| `v_gex_net_gamma_river_1pct` | `net_gex_cr * 0.01`, `session_min_net_gex_cr * 0.01`, `session_max_net_gex_cr * 0.01` |
| `v_gex_greeks_l2_net_1pct` | `net_gex_drift_time_cr_per_day * 0.01`, `net_gex_drift_iv_cr_per_volpt * 0.01`, `gross_strike_gex_drift_time * 0.01`, `gross_strike_gex_drift_iv * 0.01` |
| `v_gex_greeks_l2_strike_1pct` | `gex_drift_time_cr_per_day * 0.01`, `gex_drift_iv_cr_per_volpt * 0.01` |

**Every wrapper is purely additive: it re-selects every source column unchanged and appends the
`_1pct` ones.** Measured directly in the bodies — e.g. `v_gex_strike_snapshots_1pct` reads
`… oi_call, oi_put, gex_cr, created_at, gamma_call, gamma_put, gex_cr * 0.01 AS gex_cr_1pct FROM gex_strike_snapshots t`.
Consequence: a `SELECT *` on a wrapper returns **both scales**, under names differing by one suffix.
Two board call sites do exactly that (`30_ts_findings.md` §1).

`v_gex_greeks_l2_strike_1pct` converts the two `*_cr_per_*` columns but **passes
`gross_gex_drift_iv` / `gross_gex_drift_time` through unconverted** (they appear in its select
list with no `* 0.01`). Stated as measured; whether those two are Γ sizes in the same unit is a
question for the operator, not a finding.

## 4. `v_dealer_flow_sim` — the one place the `0.01` is NOT a unit conversion

Full body read. It is:
```
scenarios(pct) = VALUES (-0.02, -0.01, -0.005, 0.005, 0.01, 0.02)
ctx            = latest gex_strike_snapshots run per symbol  JOIN gamma_metrics gm ON run_id,symbol
                 → carries gm.net_gex  (RAW, scale A)
SELECT …  c.net_gex,
          round((- c.net_gex) * s.pct, 2) AS flow_cr,
          CASE WHEN ((- c.net_gex) * s.pct) < 0 THEN 'SELL' ELSE 'BUY' END AS direction,
          … crosses_flip from c.flip_level …
```
So `flow_cr = −(Γ per 100 % move) × (fractional move)`. **The `× s.pct` IS the per-move
conversion** — at `pct = 0.01` it is numerically identical to the ADR-032 `× 0.01`. That is why
CLAUDE.md says `flow_cr` is already true ₹ Cr and is not rescaled, and it is correct.

Two things follow, and both are measured, not inferred:
1. **This view is the tightest coupling to the STORED unit in the whole system.** It consumes
   `gamma_metrics.net_gex` directly. If the stored unit moved from scale A to scale B
   (ADR-032 D2), `flow_cr` becomes 100× too small with no error and no NULL — the arithmetic
   still succeeds and the sign is unchanged.
2. **It also publishes `c.net_gex` as its own column, at scale A**, and `queries.ts:289` reads
   this view with `select("*")`. So the board receives a scale-A `net_gex` beside a correctly-
   scaled `flow_cr` in one row — the mixing case, live.

The view has **no `_1pct` wrapper** and a live relation COMMENT.

## 5. `hist_gamma_metrics.net_gex` — a THIRD scale, and its own COMMENT says so

Live COMMENT, verbatim:
> `ADR-032: RAW scale, about 1e7 x the live gamma_metrics unit (gamma*OI*S^2, no /1e7). INR crore per 1% = value/1e9. Measured 2026-10-31: 182,430 of 182,461 non-null rows >= 1e9, one scale throughout (2025-04..2026-03).`

So the system holds **three** stored Γ scales simultaneously: raw `γ·OI·S²` (historical),
`γ·OI·S²/1e7` (live, per 100 %), and `× 0.01` (per 1 %, view-only). Any reader that joins
`hist_gamma_metrics` to `gamma_metrics` on a magnitude is wrong by 1e7. Measured readers of
`hist_gamma_metrics.net_gex`: `fill_gamma_concentration.py`, `validate_hist_greeks_flat_r.py`,
`backfill_hist_greeks.py`, `s31_weekly_attribution_diagnostic.py` (which carries
`GAMMA_UNIT_BOUNDARY = 2026-04-01` at `:94` precisely to straddle an era change), and the
untracked `research/srs/m3_dispersion.py` (sign-only, states the convention is immaterial).

## 6. `latest_net_gamma_by_strike.net_gamma` — a NAME THAT LOOKS LIKE A Γ SIZE AND IS NOT

Full body read. It is:
```
base = sum(gamma) per (run_id, symbol, expiry_date, strike) split CE/PE  FROM option_chain_snapshots
SELECT … gamma_call - gamma_put AS net_gamma,  abs(gamma_call - gamma_put) AS abs_net_gamma
```
**No OI. No S². No /1e7.** It is bare per-option γ differenced across the two sides — a
dimensionless Greek, not an exposure in ₹. The name `net_gamma` is in the prompt's §2 token list
as a Γ-size carrier; here it is not one. It propagates to **three** dependent views
(`latest_atm_neighborhood`, `latest_gamma_walls`, `latest_top_gamma_strikes`, all carrying
`net_gamma` + `abs_net_gamma`), none of which has a COMMENT. Anything that rescales these by
`× 0.01` would be introducing an error, not fixing one. Per CLAUDE.md's S100-R C naming ruling
this is **γ**, not **Γ**.

## 7. Function bodies: one magnitude threshold on a Γ size, live, in the database

`public.compute_options_regime(net_gex numeric)`:
```
when net_gex >  0.0005 then 'LONG_GAMMA'
when net_gex < -0.0005 then 'SHORT_GAMMA'
```
A **±0.0005 dead-band**, not a sign test. At scale A (|net_gex| ~1e5–1e6 per CLAUDE.md S28) and at
scale B (~1e3–1e4) the band is far below the data either way, so the behaviour does not change —
but the band's **width in real terms moves by 100×** with the unit, and nothing records that.

Scale-invariant, checked and clear:
- `compute_expansion_probability(net_gex, gamma_concentration, straddle_slope)`: `if net_gex < 0`
  (sign) and `(0.10 - gamma_concentration)/0.10` (ratio).
- `compute_signal_v2(…)`: `pin_penalty := least(greatest((gamma_concentration - 0.04) * 500, 0), 15)`
  — `gamma_concentration` is `max|gex|/sum|gex|`, dimensionless.
- `compute_flip_level_v2`, `compute_flip_level_v3`, `compute_gamma_flip_for_run`,
  `compute_gamma_metrics_for_run`, `backfill_pin_maxpain_runs`, `insert_option_chain_batch`,
  `insert_option_chain_run`, `cleanup_gamma_engine_data`: no scale literal in `prosrc`.
- `p3b_sweep(…)` is the only `public` function whose `prosrc` holds a scale literal; it is the
  P3b invariant harness (`abs(top1 - conc) > 1e-6`, a ratio tolerance).

## 8. Dependents of the Γ columns (prompt §3 item 5c)

`pg_depend` → `pg_rewrite` → `pg_class`, for every column whose name matches `gex|gamma` or ends
`_cr`. Full list in §4 of `41_db_raw.txt`. The chains that matter:

```
gex_strike_snapshots.gex_cr
  ├─ v_gex_abs_exposure ──→ v_gex_abs_exposure_1pct          [wrapped]
  ├─ v_gex_strike_snapshots_1pct                              [wrapped]
  ├─ v_gex_strike_terrain ─→ v_gex_strike_terrain_1pct        [wrapped]
  ├─ v_gex_concentration                                      [UNWRAPPED]
  ├─ v_gex_strike_pin_zone                                    [UNWRAPPED]  → generate_pine_overlay.py, queries.ts:223
  ├─ v_gex_strike_accel_zone                                  [UNWRAPPED]  → generate_pine_overlay.py, queries.ts:243
  └─ v_gex_strike_rank                                        [UNWRAPPED]  → board.ts:99,452 (ratio cols only)

gamma_metrics.net_gex
  ├─ v_gamma_metrics_1pct                                     [wrapped]
  ├─ v_gex_net_gamma_river ─→ v_gex_net_gamma_river_1pct      [wrapped]
  ├─ v_dealer_flow_sim                                        [UNWRAPPED]  → §4
  ├─ latest_gamma_metrics ─→ latest_gamma_metrics_v2
  │                        └─ latest_signal_inputs ─→ latest_signal_inputs_v2
  │                                                  ├─ latest_signal_intraday ─→ latest_signal
  │                                                  ├─ latest_signal_v1 ─→ latest_signal_v1_gated
  │                                                  └─ latest_signal_v2
  └─ signal_outcome_research_v1 ─→ signal_outcome_research_v2

gex_cycle_history.{net_gex, gamma_at_pin} ──→ v_pin_board     [UNWRAPPED]  → board.ts:435
signal_snapshots.net_gex ─→ latest_signal_snapshots, wcb_signal_validation_v1, wcb_signal_validation_v2
v_gex_greeks_l2_leg.{u_gex_drift_iv, u_gex_drift_time} ─→ v_gex_greeks_l2_strike, v_delta_drift_flow_vs_book
```
The `latest_signal_*` chain is **eight views deep** off `gamma_metrics.net_gex` and no member
of it has a wrapper or a COMMENT.

## 9. Triggers, constraints, generated columns, indexes, policies (prompt §3 item 5d)

Every zero below is paired with a non-zero from the **identical query shape**, so the zero is a
measurement and not a pattern that could not fire (CLAUDE.md rule 0):

| check | Γ result | control from the same query | verdict |
|---|---|---|---|
| user triggers on a Γ relation | **0** | 9 user triggers exist cluster-wide | real zero |
| CHECK constraint mentioning `gex\|gamma` | **0** | 41 constraints match `symbol` via the same `pg_get_constraintdef(oid) ~*` form | real zero |
| generated column that is a Γ size | **0** | 5 generated columns exist in `public` (`coverage_pct`, 3× `zone_mid`, `weight_fraction`) | real zero |
| index keyed on a Γ **value** | **0** | 28 `pg_indexes` rows on Γ relations are visible | real zero — every Γ index is on `(symbol, ts, run_id, strike, expiry_date)` keys |
| materialized views | **0** | 82 views in `public` | real zero |
| RLS policies on Γ relations | **9** | 78 policies in `public` | see below |

The 9 policies: `gamma_metrics` and `gex_strike_snapshots` each carry **two duplicate
`anon`-SELECT policies** (`"anon read"` / `"anon read gamma_metrics"` and
`"anon read gex_strike_snapshots"` / `"gex_strike_snapshots_anon_read"`), all `qual = true`, plus
`merdian_ro_select` on `gamma_metrics`, `gex_strike_snapshots`, `gamma_metrics_replay`,
`gex_pin_maxpain_history`. The duplication is pre-existing and not a unit matter; noted because
the two base tables holding the stored Γ sizes are **anon-readable with `qual = true`**, so any
change to them is immediately public (the `security_invoker = true` note on the wrappers says
they grant nothing extra — consistent).

**Nothing in the database enforces, checks or constrains the unit of a Γ size.** The only
machine-readable statement of the unit anywhere in the cluster is the eight COMMENTs in §1.
