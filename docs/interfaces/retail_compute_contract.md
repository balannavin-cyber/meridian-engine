# Retail compute contract — `merdian_compute` (S101, retail scope §1.3)

Status: **v2.1, S101 (2026-10-26)**. Owner: `meridian-engine`. Consumer: `retail-meridian` (scope §1.2,
per-user compute). The engine keeps only this contract (ruling R-11); retail keeps its own docs.
History: v1 (`11f2cbe`) the extracted parts · **v2: the composed gamma cycle (C2), the walls' ATM-IV
input (C3), the pin path's pure cores (C4), the full view closure (§8) and the live-definition check.**
v2.1 (C6): every §8 view's live definition recorded by md5; `v_gex_strike_pin_zone`'s live definition differs
from every older file and is now registered (TD at the S101 close).

## 1. How retail takes it

- Install pinned by commit SHA, never a branch:
  `pip install "git+https://github.com/balannavin-cyber/meridian-engine@<sha>#egg=merdian_compute"`.
- Import only `merdian_compute.gamma`, `.volatility`, `.pin`, `.cycle`. Stdlib only — no runtime
  dependency. Python **3.10 or 3.11** for bit-for-bit parity with production (§10).
- **Never import:** any writer (`compute_gamma_metrics_local`, `compute_volatility_metrics_local`,
  `write_gex_cycle_history_local`, `ingest_*`, `run_*`), any `core.*` (`supabase_client`, `dhan_client`,
  `config`, `parameters`, `trading_calendar_gate`, **`pin_state`**), `fetch_india_vix`,
  `gamma_engine_retry_utils`. Each reads the environment, opens a client, or rewrites `sys.argv` at
  import (`compute_volatility_metrics_local`).
- Offline step **24** proves `import merdian_compute` (all four modules) reads no environment, imports no
  supabase / requests / dotenv / core and opens no socket. Offline step **25** pins this contract.

## 2. What the package is

Every definition is either **moved byte-identical** from a live writer, or **cut** from a writer's
function body with its statements kept and only counted substitutions made; the writers import every
name back, so production runs the same code retail runs. Proofs per commit are in the commit messages
(AST equality, golden replays before vs after, error-path replays, mutants).

| Module | From | Public surface |
|---|---|---|
| `gamma` | `compute_gamma_metrics_local.py` | `prepare_gamma_inputs`, **`compute_gamma_core`** (the composed cycle, C2); the parts: `signed_gamma_exposure`, `filter_usable_option_rows`, `infer_*`, `compute_net_gex`, `build_strike_exposure_map`, `compute_gamma_concentration`, `compute_flip_level`, `find_atm_strike`, `compute_straddle_atm`, `compute_straddle_slope`, `compute_expansion_probability`, `determine_regime`, `determine_gamma_zone`, `compute_straddle_velocity`, `compute_otm_oi_velocity`, `compute_otm_oi_snapshot`, `compute_max_gamma_strike`, `compute_pin_risk_score`, `build_gss_rows`, `GammaMetricsResult` |
| `volatility` | `compute_volatility_metrics_local.py` | **`derive_atm_iv`** (C3), `ATM_IV_KEYS`; `parse_iso_date`, `parse_iso_dt`, `safe_float`, `get_expiry_type`, `get_strike_step`, `find_atm_strike`, `find_row` |
| `pin` | `core/pin_state.py` | **`derive_core`** (C4), `NO_PIN`, `SHIFTING`, `LOCKED`, `STABLE`, `VALID_STATES`, `key_for` |
| `cycle` | `write_gex_cycle_history_local.py` | **`trading_days_between`**, **`held_for_cycles_next`** (C4), `derive_rank_fields`, `boost`, `conviction_for`, `IST`, `BOOST_COEFF`, `BOOST_CAP`, `T_FLOOR` |

Underscore names are importable but not part of the surface. Step 25 pins 39 public signatures and the
`GammaMetricsResult` field order.

## 3. Inputs — one option row

A `dict` shaped like an `option_chain_snapshots` row as PostgREST serves it, **one symbol, one expiry,
one cycle** (a multi-expiry batch raises, TD-S79-NEW-12). Keys read, computed from the package's AST:

| Key | Read by | Notes |
|---|---|---|
| `gamma`, `oi` | exposure, filter, GSS rows, OTM OI | per-option γ as delivered; OI in contracts |
| `option_type` | everywhere | `"CE"` / `"PE"` |
| `strike` | exposure map, ATM, step, straddle, ATM IV | |
| `spot` | `infer_spot`, `derive_atm_iv` | the cycle's spot |
| `ltp` | straddle ATM / slope | |
| `iv` | `derive_atm_iv` | **percent** as delivered (e.g. `12.5`); not rescaled |
| `symbol`, `expiry_date` | infer / ATM IV | ATM IV supports NIFTY (step 50) and SENSEX (step 100) only |
| `ts`, `created_at` | `infer_ts`, `build_gss_rows`, `derive_atm_iv` | **ISO-8601 with `T` and a `±HH:MM` offset** (`2026-10-23T09:00:00.123456+00:00`). The psql form `2026-10-23 09:00:00.12+00` raises in `build_gss_rows` on Python 3.10 (measured S101). With no `ts` at all, `infer_ts` falls back to `datetime.now()` — the package's only clock read; always supply `ts`. |

`derive_atm_iv` takes the **first row** for symbol / expiry / ts / spot and searches the rows for the ATM
CE and PE: pass the batch **in ascending strike order**, as the writer selects it.

## 4. Units and signs (CLAUDE.md settled decision, S100-R C)

- **Γ = aggregate dealer exposure**; **γ = per-option gamma**. Never relabel one as the other.
- Per row `gex = gamma × oi × spot² / 1e7` (**₹ crore**), **CE positive, PE negative**; `net_gex`, the
  exposure map and `gex_cr` use that unit and sign. Positive = dealers long γ (dampening).
- `max_gamma_strike` = strike with the largest **positive** exposure (tie: lower strike), `None` if none.
- `gamma_concentration` = max |strike Γ| / Σ |strike Γ|.
- `regime`: `NO_FLIP` without a flip; else `LONG_GAMMA` if `net_gex >= 0`, `SHORT_GAMMA` otherwise.
  `flip_distance_pct = |spot − flip| / spot × 100`; `gamma_zone` `< 0.5` HIGH, `< 1.5` MID, else LOW.
- `pin_risk_score` 0–100: 0.30 concentration, 0.30 spot proximity, 0.20 sustained time,
  0.20 (1 − expansion/100), renormalised when a factor is unavailable.
- ATM IV: `atm_strike = round(spot / step) × step`; `atm_iv_avg = (call iv + put iv) / 2`;
  `iv_skew = put iv − call iv` (percent points).

## 5. The calls retail makes, per symbol per cycle

```python
from merdian_compute import gamma, volatility, pin, cycle

inputs = gamma.prepare_gamma_inputs(rows, run_id, expected_symbol="NIFTY")   # raises like the writer
res = gamma.compute_gamma_core(**inputs, run_type="FULL",
                               prior_row=<§6>, spot_vs_range=None, vix=None,
                               recent_max_strikes=<§6>)                     # -> GammaMetricsResult
atm = volatility.derive_atm_iv(sorted(rows, key=lambda r: float(r["strike"])))
if atm["error"] is None:
    atm_iv_avg = atm["atm_iv_avg"]                                         # the walls' sigma input
state, reason = pin.derive_core(held, runnerup_share_ratio, conc_top1_share,
                                nopin_conc_floor=..., stable_held_for=...,
                                locked_held_for=..., locked_ratio_max=...)  # §7
```

`compute_gamma_core` is exactly what the live writer runs: the writer's `compute_gamma_metrics` is now
"fetch chain → `prepare_gamma_inputs` → the four history reads → `compute_gamma_core`". Step 25 runs the
two calls above on every golden chain and matches production: 313 rows × 11 Board fields,
`pin_risk_score` on 291 rows, `straddle_velocity` on 307, ATM IV 313 rows × 5 fields.
`res.gss_rows` are the per-strike rows (`gex_strike_snapshots` shape) the views in §8 read.

## 6. History inputs — retail supplies them from its own per-user tables

| Input | Production source | Retail rule |
|---|---|---|
| `recent_max_strikes` | `gex_strike_snapshots` before `ts`, `gex_cr > 0`, argmax per cycle, last 5 — **no date bound: it crosses sessions** | last 5 prior cycles' `max_gamma_strike`, across session boundaries |
| `prior_row` | latest `gamma_metrics` row before `ts` (also crosses sessions) | `{"straddle_atm": <prior value>}` |
| `otm_oi_velocity` | the same `prior_row`, which never carries `otm_oi_snapshot` / `raw` | **NULL in every production row** (0 / 313 golden rows) — a live defect, filed S101; retail matches production by passing the same shape |
| `vix`, `spot_vs_range` | Dhan VIX / `intraday_ohlc` | stored only, not computed on |

## 7. The pin path (C4)

`gex_cycle_history` rows carry the pin state the board's Pin pane reads (`v_pin_board`). Per row:

1. **Rank fields** — `cycle.derive_rank_fields(rank_rows)` over the cycle's `v_gex_strike_rank` rows (§8).
2. **Carry-forward** — `cycle.held_for_cycles_next(state, leader, prior_rows)`: `prior_rows` = the latest
   EARLIER row of the same (symbol, expiry) with `session_gate_state = 'OPEN'`, as a list of ≤ 1 dict
   (`pin_leader_strike`, `held_for_cycles`). `None` unless `state == "OPEN"` and a leader exists.
3. **Ladder** — `pin.derive_core(held, ratio, conc, <four thresholds>)`. Production reads the thresholds
   from `merdian_parameters` under `pin_state.<suffix>.<SYMBOL>` (`pin.key_for`); retail passes its own.
   A NULL conc or held → `(None, reason)`; a NULL ratio can never be LOCKED.
4. **Trading days / conviction** — `cycle.trading_days_between(run_date, expiry, is_open)` with the
   caller's calendar predicate; production's `is_trading_day` **fails open** (a date with no calendar row
   counts as open). Then `cycle.conviction_for(ratio, t_days, calendar_healthy)`.

Not packaged, and retail must build its own: the **session gate** (`session_gate` reads
`market_spot_snapshots` ticks to classify a cycle OPEN / FROZEN / PRE_TICK) and the **reconciler**
(`reconcile_gex_cycle_history_session_local.py`). No golden day holds `gex_cycle_history`, so C4 is proven
before-vs-after (1,577 input combinations, mutants) and against the ruled S89 ladder, not against
production rows.

## 8. Views retail re-creates in its own schema

Walls, pin, max pain, rank and the repriced flip are SQL, not Python. Retail re-creates them over its
per-user tables (adding `user_id` and RLS, scope §1.2). The closure below was extracted from `sql/` by
script (S101); files are the newest defining file at the S101 HEAD.

| View | File | Reads |
|---|---|---|
| `v_gex_strike_walls` | `sql/2026-09-15_s79_v_gex_strike_walls.sql` | `gex_strike_snapshots`, `volatility_snapshots` (`atm_iv_avg` ← `derive_atm_iv`) |
| `v_gex_concentration` | `sql/2026-09-15_s79_v_gex_concentration.sql` | `gex_strike_snapshots` |
| `v_gex_strike_rank` | `sql/2026-09-22_s81_v_gex_strike_rank.sql` | `gex_strike_snapshots`, `volatility_snapshots` |
| `v_gex_max_pain` | `sql/2026-09-22_s80_v_gex_max_pain.sql` | `gex_strike_snapshots`; `now()`; DB function `get_parameter_num('maxpain.stale_floor_min')` |
| `v_gex_strike_pin_zone` | **`sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql`** (live; the 3 older files are not) | `gex_strike_snapshots`; `get_parameter_num('pin.tau.<SYMBOL>')` **with default 0.3**, which drives the walk |
| `v_gex_pin_maxpain` | `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` | `gex_strike_snapshots`, `v_gex_max_pain`, `v_gex_strike_pin_zone`, `v_gex_strike_walls` |
| `v_max_pain_by_strike` | `sql/2026-09-22_s81_v_max_pain_by_strike_latest_ts_retrofit.sql` (3 files) | `option_chain_snapshots` |
| `v_gex_repriced_flip` | `sql/2026-09-25_s83_v_gex_repriced_flip.sql` | `option_chain_snapshots`, **`index_futures_snapshots`** — retail needs a futures quote per symbol |
| `v_pin_board` | `sql/2026-10-08_s92_v_pin_board.sql` | `gex_cycle_history` (§7); `security_invoker = false` |

Create order: `v_gex_strike_walls`, `v_gex_concentration`, `v_gex_strike_rank`, `v_gex_max_pain`,
`v_gex_strike_pin_zone`, `v_gex_pin_maxpain`, `v_max_pain_by_strike`, `v_gex_repriced_flip`, then
`v_pin_board` once `gex_cycle_history` exists.

**Live definitions (recorded S101, 2026-10-26, operator `pg_get_viewdef(…, true)` on production).** Retail copies
the LIVE definition, never "the newest file", and checks it by md5 — a marker check passed a file whose tau the
live view uses differently (S101 §D.55).

| View | Live = file | def_length | def_md5 |
|---|---|---|---|
| `v_gex_strike_walls` | `sql/2026-09-15_s79_v_gex_strike_walls.sql` | 4664 | `8135c42b4fe3613a676ec7e05af7ee9d` |
| `v_gex_concentration` | `sql/2026-09-15_s79_v_gex_concentration.sql` | 2140 | `c4cf15aa43fdb932b56db77cefee7188` |
| `v_gex_strike_rank` | `sql/2026-09-22_s81_v_gex_strike_rank.sql` | 4002 | `0ab189a40cd648e8cc0e8f77b55cc5f6` |
| `v_gex_max_pain` | `sql/2026-09-22_s80_v_gex_max_pain.sql` | 3088 | `3d067c67ef36f9841af9eea81a4c0575` |
| `v_gex_strike_pin_zone` | `sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql` (byte-exact; length and md5 reproduced from the file) | 3523 | `89c9ac6aef9eb332ddd28f9062d0e21e` |
| `v_gex_pin_maxpain` | `sql/2026-09-22_s80_v_gex_pin_maxpain.sql` | 2577 | `0d7d5258d6a1169ffe97a94aa82474e5` |
| `v_max_pain_by_strike` | `sql/2026-09-22_s81_v_max_pain_by_strike_latest_ts_retrofit.sql` | 4028 | `3d0ed5cb979ab7ed6dbfcfa5e8f09f30` |
| `v_gex_repriced_flip` | `sql/2026-09-25_s83_v_gex_repriced_flip.sql` | 10260 | `58ad6ba8f366c52a8e71b4ac1ea66864` |
| `v_pin_board` | `sql/2026-10-08_s92_v_pin_board.sql` | 2922 | `9a827e8155e188db9ab9cd9b4fc429e0` |

Only `v_gex_strike_pin_zone` and `v_max_pain_by_strike` were confirmed by full md5 against a file; the other
seven rows match their file on structural markers (MR-S1 O1), and their md5 is the live value to compare against.

`v_gex_strike_pin_zone`, live vs the older s69 file: the walk threshold is `tau × peak` with
`tau = COALESCE(get_parameter_num('pin.tau.'||symbol), 0.3)` (the s69 file hard-codes `0.3` and only reports the
parameter); `tau_used` is never NULL; `latest_run` is a LATERAL skip-scan over `VALUES ('NIFTY'), ('SENSEX')` —
retail replaces that list with its own symbols. Same output as the s69 file only while `pin.tau` = 0.30.

Re-check before each retail copy (read-only):

```sql
SELECT length(d) AS def_length, md5(d) AS def_md5
  FROM (SELECT pg_get_viewdef('public.v_gex_strike_pin_zone'::regclass, true) AS d) v;
```

(one view per run; substitute the view name). A row whose md5 differs from the table means the live view changed
again and its DDL is not registered.

## 9. Not covered (stated, so retail does not assume it)

1. Session gate and reconciler (§7).
2. The VIX fields of `volatility_snapshots` (regime, percentile, velocities): history-dependent, still
   in the writer; only ATM IV is packaged. The writer's `dte` uses the wall clock (`datetime.now()`),
   not the row's `ts` — the TD-NEW-4 class fixed in the gamma writer but not here; filed S101.
3. `index_futures_snapshots` for the repriced flip; `merdian_parameters` rows and a `get_parameter_num`
   SQL function; a `trading_calendar` for the calendar predicate.
4. Drift outside the package: the gamma math is re-implemented in `backfill_gamma_metrics_to_main.py`,
   `measure_rate_sensitivity.py` and `replay/replay_compute_gamma_metrics.py`; volatility in
   `replay/replay_compute_volatility_metrics.py`. Recorded, not changed.

## 10. Interpreter

Production runs Python 3.10. From 3.12, `sum()` over floats is compensated, so `net_gex` and
`gamma_concentration` differ from production in the last one or two bits (~1e-15 relative; 474 of 486
golden runs). Step 25 compares at 1e-9 and passes on both. Retail wanting bit-for-bit parity pins 3.10 or
3.11.

## 11. Change control

- A change to anything in `merdian_compute/` ships only with a before-vs-after replay of the writer it
  came from, offline suite green incl. steps 24–25, and a new retail pin.
- A signature or `GammaMetricsResult` field change fails step 25 by design: update `SIGNATURES` there and
  this document in the same commit, and tell retail before it re-pins.
