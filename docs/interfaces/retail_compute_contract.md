# Retail compute contract — `merdian_compute` (S101, retail scope §1.3)

Status: **v1, S101 (2026-10-25)**. Owner: `meridian-engine`. Consumer: `retail-meridian` (scope §1.2,
per-user compute). The engine keeps only this contract (ruling R-11); retail keeps its own docs.

## 1. How retail takes it

- Install pinned by commit SHA, never a branch:
  `pip install "git+https://github.com/balannavin-cyber/meridian-engine@<sha>#egg=merdian_compute"`.
- Import only `merdian_compute.gamma` and `merdian_compute.cycle`. Stdlib only — no runtime dependency.
- **Never import:** any writer (`compute_gamma_metrics_local`, `write_gex_cycle_history_local`,
  `compute_volatility_metrics_local`, `ingest_*`, `run_*`), `core.*` (`core.supabase_client`,
  `core.dhan_client`, `core.config`, `core.parameters`, `core.trading_calendar_gate`, `core.pin_state`),
  `fetch_india_vix`, `gamma_engine_retry_utils`. Each of these reads the environment or opens a client.
- Offline step **24** proves `import merdian_compute` reads no environment, imports no
  supabase / requests / dotenv / core and opens no socket. Offline step **25** pins this contract
  (signatures + outputs against production rows). Both run on every engine suite run.

## 2. What the package is

Every definition was moved **byte-identical** from the live writers at `7b91d1a`; the writers re-import
each name, so production runs the same objects retail runs (S101 A3: `ast.dump` equal for all 39 moved
definitions; golden replay of the gamma writer 486/486 runs identical before vs after on the same
interpreter). Any edit to `merdian_compute/` is an edit to the live writer.

**Interpreter.** Production runs Python 3.10. From 3.12, `sum()` over floats uses compensated
summation, so `net_gex` and `gamma_concentration` differ from production in the last one or two bits
(~1e-15 relative; measured S101 on 474 of 486 golden runs). Step 25 compares at 1e-9 and passes on
both. Retail wanting bit-for-bit parity with production pins Python 3.10 or 3.11.

| Module | From | Names |
|---|---|---|
| `gamma` | `compute_gamma_metrics_local.py` | `to_float`, `as_iso_ts`, `signed_gamma_exposure`, `GammaMetricsResult`, `filter_usable_option_rows`, `infer_symbol`, `infer_spot`, `infer_expiry_date`, `infer_ts`, `infer_strike_step`, `compute_net_gex`, `build_strike_exposure_map`, `compute_gamma_concentration`, `_FLIP_DOMINANCE_EPS_FRAC`, `_flip_short_gamma_perstrike`, `compute_flip_level`, `find_atm_strike`, `compute_straddle_atm`, `compute_straddle_slope`, `compute_expansion_probability`, `determine_regime`, `determine_gamma_zone`, `compute_straddle_velocity`, `compute_otm_oi_velocity`, `compute_otm_oi_snapshot`, `compute_max_gamma_strike`, `compute_pin_risk_score`, `_dte_from_ts`, `build_gss_rows` |
| `cycle` | `write_gex_cycle_history_local.py` | `IST`, `BOOST_COEFF`, `BOOST_CAP`, `T_FLOOR`, `_FRAC`, `_norm_frac`, `_ist_date`, `derive_rank_fields`, `boost`, `conviction_for` |

Underscore names are importable but not part of the retail surface; step 25 pins the signatures of the
26 public functions listed there.

## 3. Inputs — one option row

A row is a `dict` shaped like an `option_chain_snapshots` row, **one symbol, one expiry, one cycle**
(`infer_expiry_date` raises on a multi-expiry batch, TD-S79-NEW-12). Keys read (computed from the
package's AST, S101):

| Key | Read by | Notes |
|---|---|---|
| `gamma` | exposure, filter, GSS rows | per-option γ, the broker greek as delivered |
| `oi` | exposure, filter, OTM OI | contracts |
| `option_type` | exposure, straddle, OTM OI | `"CE"` / `"PE"` (upper-cased on read) |
| `strike` | exposure map, ATM, step, straddle | |
| `spot` | `infer_spot` | the cycle's spot, same on every row |
| `ltp` | straddle ATM / slope | |
| `symbol`, `expiry_date` | infer | |
| `ts` (or `created_at`) | `infer_ts`, `build_gss_rows` | **always supply `ts`**: with none, `infer_ts` and `as_iso_ts` fall back to `datetime.now()` (the only clock read in the package; never reached at import) |

`filter_usable_option_rows` drops `gamma == 0` or `oi <= 0`. `signed_gamma_exposure` also returns 0 for a
strike more than 5 % from spot carrying `|gamma| > 5e-5` (TD-NEW-2 Part A).

## 4. Units and signs (CLAUDE.md settled decision, S100-R C)

- **Γ = aggregate dealer exposure**; **γ = per-option gamma**. Never relabel one as the other.
- Per row: `gex = gamma × oi × spot² / 1e7` (**₹ crore**), **CE positive, PE negative**. `net_gex` and
  every strike value in the exposure map and `gex_cr` are in that unit and sign.
- Positive strike exposure = dealers long γ (dampening). `compute_max_gamma_strike` = the strike with the
  largest **positive** exposure (tie: lower strike); `None` when no strike is positive.
- `gamma_concentration` = max |strike Γ| / Σ |strike Γ|, in [0, 1].
- `regime`: `NO_FLIP` when no flip; else `LONG_GAMMA` if `net_gex >= 0`, `SHORT_GAMMA` otherwise.
- `flip_distance_pct = |spot − flip| / spot × 100`; `gamma_zone`: `< 0.5` HIGH, `< 1.5` MID, else LOW,
  `None` without a flip.
- `pin_risk_score` 0–100, weights 0.30 concentration / 0.30 spot proximity / 0.20 sustained time /
  0.20 (1 − expansion/100), renormalised when a factor is unavailable.

## 5. The Board-core sequence

Retail runs, per symbol per cycle, the same sequence the writer's `compute_gamma_metrics` runs between
its fetches (step 25 runs exactly this and matches production on 313 rows × 11 fields):

```
spot   = infer_spot(rows);           use = filter_usable_option_rows(rows)
smap   = build_strike_exposure_map(use, spot)
net    = compute_net_gex(use, spot); conc = compute_gamma_concentration(smap)
flip   = compute_flip_level(smap, spot)
fdp    = None if flip is None else (abs(spot - flip) / spot * 100.0 if spot > 0 else None)
zone   = determine_gamma_zone(fdp);  regime = determine_regime(net, flip)
strad  = compute_straddle_atm(use, spot); slope = compute_straddle_slope(use, spot)
expand = compute_expansion_probability(conc, fdp, net)
maxg   = compute_max_gamma_strike(smap)
pin    = compute_pin_risk_score(gamma_concentration=conc, expansion_probability=expand, spot=spot,
                                max_gamma_strike=maxg, strike_step=infer_strike_step(use),
                                recent_max_strikes=<§6>)
gss    = build_gss_rows(rows, spot, symbol, ts, expiry_date, run_id)   # per-strike rows for the views
```

**Open (ruling owed, S101):** this sequence lives in the writer's `compute_gamma_metrics`, interleaved
with its fetches, so retail must re-state it. The recommended follow-up moves it into one pure
`merdian_compute.gamma.compute_gamma_core(...)` the writer then calls, proven by the same golden replay.
Until then, step 25 is what keeps retail's copy of the sequence honest.

## 6. History inputs — retail supplies them from its own per-user tables

| Input | Production source | Retail rule |
|---|---|---|
| `recent_max_strikes` | `fetch_recent_max_gamma_strikes`: `gex_strike_snapshots` before `ts`, `gex_cr > 0`, argmax per cycle, last 5 — **no date bound, it crosses sessions** | the last 5 prior cycles' `max_gamma_strike` for the symbol, across session boundaries (step 25: 291/291 equal on full in-day windows) |
| `prior_row` for `compute_straddle_velocity` | `gamma_metrics` latest row before `ts` | `{"straddle_atm": <prior>}` |
| `prior_row` for `compute_otm_oi_velocity` | the same query, which selects only `straddle_atm,ts` | **production writes NULL in every row** (0 non-null across the six golden days) because the function reads `otm_oi_snapshot` / `raw`, which that query never returns. Retail matches production by passing the same shape. Filed S101; not fixed in a behaviour-neutral session. |
| `vix`, `spot_vs_range` | live Dhan fetch / `intraday_ohlc` | not compute; stored only |

## 7. Views retail re-creates in its own schema

Walls, pin and max pain are SQL, not Python. Retail re-creates them over its per-user tables (adding
`user_id` and RLS, scope §1.2). Definition files below are the newest in `sql/` at `7b91d1a`; **the live
definition must be confirmed with `pg_get_viewdef` before retail copies it** (three files define
`v_max_pain_by_strike`). Dependencies were extracted from the files by script (S101).

| View | File | Reads | Notes |
|---|---|---|---|
| `v_gex_strike_walls` | `sql/2026-09-15_s79_v_gex_strike_walls.sql` | `gex_strike_snapshots`, `volatility_snapshots` | σ band from `volatility_snapshots.atm_iv_avg` — **not packaged** (§8) |
| `v_gex_max_pain` | `sql/2026-09-22_s80_v_gex_max_pain.sql` | `gex_strike_snapshots` | `now()` freshness and DB function `get_parameter_num('maxpain.stale_floor_min')` |
| `v_gex_strike_pin_zone` | `sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql` | `gex_strike_snapshots` | dependency of `v_gex_pin_maxpain` (three defining files) |
| `v_gex_pin_maxpain` | `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` | `v_gex_max_pain`, `v_gex_strike_pin_zone` | |
| `v_max_pain_by_strike` | `sql/2026-09-22_s81_v_max_pain_by_strike_latest_ts_retrofit.sql` | `option_chain_snapshots` | header supersedes the other two files |
| `v_pin_board` | `sql/2026-10-08_s92_v_pin_board.sql` | `gex_cycle_history` | `security_invoker = false`; reads the ENH-133 table — **not packaged** (§8) |

Create order: `v_gex_strike_walls`, `v_gex_max_pain`, `v_gex_strike_pin_zone`, `v_gex_pin_maxpain`,
`v_max_pain_by_strike`, then `v_pin_board` once `gex_cycle_history` exists.

## 8. Not covered by v1 (stated, so retail does not assume it)

1. **ATM IV / volatility** (`compute_volatility_metrics_local.py`, 909 lines, imports
   `core.supabase_client` at module top) — needed for the walls' σ band. Not purity-mapped yet.
2. **Pin state** (`gex_cycle_history`) — `write_gex_cycle_history_local.py` needs
   `core.pin_state.derive` (thresholds from `merdian_parameters` over HTTP), the trading calendar
   (`trading_days_to_expiry`) and a carry-forward `held_for_cycles` chain. Only its pure helpers
   (`cycle.*`) are packaged.
3. **Parameters and calendar** — retail needs its own `merdian_parameters` rows (`pin_state.*`,
   `maxpain.stale_floor_min`) and `trading_calendar`, plus a `get_parameter_num` SQL function.
4. **Drift risk outside this package:** the gamma math is re-implemented in
   `backfill_gamma_metrics_to_main.py` and `measure_rate_sensitivity.py` (and `replay/`) instead of
   importing it. Out of S101 scope; recorded.

## 9. Change control

- A change to anything in `merdian_compute/` ships only with: S101 golden replay (before vs after), offline
  suite green incl. steps 24–25, and a new retail pin.
- A signature or `GammaMetricsResult` field change fails step 25 by design: update `SIGNATURES` there and
  this document in the same commit, and tell retail before it re-pins.
