# MERDIAN Data Inventory

**Measured:** 2026-09-14  ·  **Regenerate:** `scripts/build_data_inventory.py` (no arguments)

> **Use this register instead of re-deriving.** The extent of MERDIAN's option
> history has been re-derived from scratch at least a dozen times across 70+
> sessions, each time from whichever table that session's brief named, producing
> a different answer each time. If this file looks stale, **re-run the script** —
> do not measure one table and generalise from it.

Measured against the live database. Nothing here is taken from `merdian_reference.json`, from any register, or from a table name.

---

## 1. Method, and the access path

This box has no `psql`, no `psycopg2`/`psycopg`/`asyncpg`/`pg8000`/`sqlalchemy`,
and no Postgres password. The only route is PostgREST as the service role.
The script is READ-ONLY: HTTP GET only, no RPC, no write.

Six rules govern every number below.

1. **`count=exact` always.** `count=planned` on a `not.is.null` filter over an
   all-NULL column returns a planner floor of **1**, which is not a row.
   No planned figure appears anywhere in this register.
2. **A `57014` is never an absence.** Every failing probe is retried, then
   decomposed (day → halves → quarters → eighths). Only an HTTP 200 carrying a
   literal empty JSON array counts as absence. Anything unresolved is listed in
   §10 and the script refuses to write while §10 is non-empty.
3. **Every zero cell is a real empty list** from a day-scoped `limit=1` probe.
   **6,139** such confirmations were counted on this run.
4. **Ranges are probed one month beyond each discovered edge**, so a real edge
   outside the window appears rather than being excluded by construction.
5. **The relation list comes from the live catalog** — the PostgREST OpenAPI
   document, generated from `pg_catalog`.
6. **A relation that cannot produce a real empty list is excluded**, as
   UNMEASURABLE BY THIS METHOD — by measurement, never by name and never by
   catalog category. Each source is probed on a window it certainly holds no
   rows in; one that must scan its whole extent to prove absence times out
   instead of returning `[]`, and so can never satisfy rule 3 on an empty day.
   The exclusions and their timings are in §4b. This does **not** block the
   write — but it does mean the register says **nothing** about those
   relations, neither presence nor absence.

```
GET /rest/v1/                                    -- the relation list
GET /rest/v1/<rel>?select=*&limit=0              Prefer: count=exact
GET /rest/v1/<rel>?select=<col>&<col>=not.is.null&<scope>&limit=1
```

**Calendar-day windows.** Timestamp columns are filtered `[D, D+1)` in UTC. An
IST session (09:15–15:30 IST = 03:45–10:00 UTC) falls strictly inside one UTC
calendar day, and so does a session stored under the legacy IST-clock-as-UTC
convention (Rules 16/20, hours 09–15). Both are contained by the same window,
so no session is split across two cells.

Requests issued this run: **26,172**. Wall time: **0:52:36**.

## 2. Every relation in schema `public` — 224

The catalog does **not** distinguish tables from views; PostgREST's OpenAPI
document exposes both identically and the catalog view that would separate them
is not reachable on this access path. That limit is recorded in §10, not guessed.

```
  _active_universe_choice                       _equity_eod_detected                          _s36_outcomes_pre_truncate
  active_breadth_universe                       active_breadth_universe_members_nse           active_breadth_universe_nse
  aging_policy                                  app_settings                                  basis_context_snapshots
  bom_dhan_bridge                               breadth_coverage_latest                       breadth_equity_indicators
  breadth_indicators_daily                      breadth_ingest_state                          breadth_intraday_history
  breadth_universe_members                      breadth_universe_nse_only                     breadth_universe_sets
  breadth_universe_snapshot                     bse_scripcode_isin_map                        bse_t1_securities
  capital_tracker                               dashboard_last_updated                        data_contamination_ranges
  data_quality_events                           dhan_auth_tokens                              dhan_nse_equity_norm
  dhan_scrip_map                                dhan_scripmaster                              dhan_scripmaster_staging
  dhan_symbol_alias                             dhan_token_probe_log                          eq_corporate_actions
  eq_feature_store                              eq_fundamental_snapshots                      eq_ingestion_log
  eq_instrument_events                          eq_instruments                                eq_macro_data
  eq_market_gate                                eq_paper_trades                               eq_price_daily
  eq_price_daily_backup_20260618                eq_price_daily_v2                             eq_signal_snapshots
  eq_stock_sector_map                           eq_trading_calendar                           eq_watchlist
  equity_eod                                    equity_eod_norm                               equity_eod_shadow_audit
  equity_intraday_last                          exit_alerts                                   expiry_outcomes
  fii_dii_cash_daily                            gamma_metrics                                 gamma_metrics_replay
  gamma_metrics_shadow                          gex_strike_snapshots                          hist_atm_option_bars_15m
  hist_atm_option_bars_5m                       hist_basis_context                            hist_completeness_checks
  hist_future_bars_1m                           hist_gamma_metrics                            hist_greeks_backfill_log
  hist_ict_htf_zones                            hist_ingest_log                               hist_ingest_rejects
  hist_iv_surface_daily                         hist_market_state                             hist_option_bars_1m
  hist_option_greeks_1m                         hist_pattern_signals                          hist_spot_bars_15m
  hist_spot_bars_1m                             hist_spot_bars_5m                             hist_volatility_snapshots
  historical_index_futures_1m                   historical_market_spot_1m                     historical_option_chain_snapshots
  ict_htf_zones                                 ict_primitive_outcomes                        ict_primitive_outcomes_pre_s77
  ict_primitives                                ict_primitives_pre_s77                        ict_zones
  ict_zones_replay                              index_constituent_weights                     index_futures_snapshots
  india_vix_daily                               india_vix_history                             instruments
  intraday_ohlc                                 iv_context_snapshots                          latest_atm_neighborhood
  latest_gamma_metrics                          latest_gamma_metrics_v2                       latest_gamma_walls
  latest_market_breadth                         latest_market_breadth_intraday                latest_market_breadth_nse
  latest_net_gamma_by_strike                    latest_option_chain_run                       latest_option_chain_snapshots
  latest_run_id                                 latest_signal                                 latest_signal_inputs
  latest_signal_inputs_v2                       latest_signal_intraday                        latest_signal_snapshots
  latest_signal_v1                              latest_signal_v1_gated                        latest_signal_v2
  latest_top_gamma_strikes                      market_breadth_daily                          market_breadth_daily_nse
  market_breadth_intraday                       market_environment_snapshots                  market_spot_session_markers
  market_spot_snapshots                         market_spot_snapshots_replay                  market_state_snapshots
  market_state_snapshots_replay                 market_state_snapshots_shadow                 market_ticks
  measurement_health_snapshots                  merdian_parameters                            model_registry
  momentum_snapshots                            momentum_snapshots_replay                     momentum_snapshots_shadow
  momentum_snapshots_v2                         nifty_cycle_base                              nifty_move_anchor
  nse_dhan_bridge                               option_atm_snapshots                          option_chain_snapshots
  option_chain_snapshots_replay                 option_execution_outcomes_v1                  option_execution_path_audit_v1
  option_execution_price_history                option_execution_snapshots                    option_outcome_analytics_v1
  options_flow_snapshots                        options_flow_snapshots_replay                 participant_oi_daily
  po3_session_state                             raw_ingest_log                                script_execution_log
  script_execution_log_replay                   shadow_outcomes_v1                            shadow_outcomes_v2
  shadow_reconstruction_v1                      shadow_reconstruction_v2                      shadow_reconstruction_v3
  shadow_replay_v1                              shadow_signal_outcomes                        shadow_signal_snapshots
  shadow_signal_snapshots_v3                    shadow_signal_validation_v1                   shadow_state_signal_outcomes
  shadow_state_signal_snapshots                 shadow_vs_live_evaluation                     signal_labels
  signal_market_outcome_audit_v1                signal_market_path_audit_v1                   signal_outcome_audit
  signal_outcome_audit_dedup                    signal_outcome_audit_v2                       signal_outcome_audit_v2_intraday_clean
  signal_outcome_research_v1                    signal_outcome_research_v2                    signal_outcomes
  signal_premium_outcomes                       signal_regret_analytics_v1                    signal_regret_analytics_v2
  signal_regret_log                             signal_regret_log_v1                          signal_regret_log_v1_latest
  signal_runs                                   signal_snapshots                              signal_snapshots_replay
  signal_snapshots_shadow                       signal_state_snapshots                        smdm_snapshots
  structural_alerts                             structural_divergence_snapshots               structural_divergence_snapshots_replay
  study_accel_stat                              study_eligible                                study_null_pair
  study_path                                    study_pin_stat                                study_real_pair
  study_recon_accel                             study_recon_pin                               study_runs_m
  study_step_m                                  study_zone_ref                                system_config
  trade_log                                     trading_calendar                              underlyings
  v_dealer_flow_sim                             v_dhan_token_probe_today                      v_expiry_base_rates
  v_gex_strike_accel_zone                       v_gex_strike_pin_zone                         v_max_pain_by_strike
  v_merdian_parameter_audit                     v_oi_prev_close_snapshots                     v_participant_oi_latest
  v_script_execution_health_30m                 v_wcb_active_weights                          v_wcb_weight_totals
  vix_percentile_reference                      vol_analytics                                 vol_analytics_shadow
  volatility_snapshots                          volatility_snapshots_replay                   wcb_signal_validation_v1
  wcb_signal_validation_v2                      weighted_constituent_breadth_snapshots
```

## 3. How a relation became a candidate

Membership was decided by reading each relation's column list out of the live
catalog, never from its name. A relation is a **candidate** if it carries a
strike dimension or a volatility/greek/OI column:

```
strike (any)  (^|_)strikes?($|_)
strike (dim)  ^strike$      <- the row is KEYED by strike
greek         ^(ce_|pe_)?(gamma|delta|theta|vega|rho)(_call|_put)?$
volatility    (^iv$|^iv_|_iv$|implied_vol|^vega$|volatility)
open interest ^(ce_|pe_)?(oi|oi_call|oi_put|open_interest|prev_close_oi)$
gamma         ^(ce_|pe_)?gamma(_call|_put)?$
iv            ^(ce_|pe_)?(iv|atm_iv|atm_call_iv|atm_put_iv|implied_vol_atm)$
spot          ^spot(_close)?$
provenance    ^(source|provenance|origin|written_by|producer|ingest_source|data_source|run_type|source_table)$
```

For the gamma / iv / oi / spot **layers** a name match is not sufficient — the
column must also carry a numeric type in the catalog. That is what keeps
`iv_regime` (a text label) from being counted as an implied volatility.

**A strike dimension is not the same as a strike column.** A relation with
`strike` is keyed by strike and can serve a per-strike layer. A relation with
only `atm_strike` / `ce_strike` / `pe_strike` holds **one distinguished strike**
per row and cannot. Both are listed; only the first can make a day COMPUTABLE.

**73** relations are candidates. **32** of them can
actually serve a layer for a (symbol, day) cell — the rest lack a symbol
identifier, a usable time column, or a numeric layer column.

## 4. Candidate sources and their measured bounds

Bounds are read from the relation's scoping column. Where the first-choice
column could not answer — an ordered scan can exceed the statement timeout on a
column with no usable index at that relation's size — the walk falls through to
the next column, and **the column that actually answered is named below**.

| relation | kind | symbol via | bounds col | layers served | min | max |
|---|---|---|---|---|---|---|
| `gamma_metrics` | single_strike | `symbol` | `ts` | spot | 2026-06-10T10:55:05.214937+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `gex_strike_snapshots` | per_strike | `symbol` | `ts` | gamma, oi, spot | 2026-05-25T09:56:07.707025+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `hist_atm_option_bars_15m` | single_strike | `symbol` | `bar_ts` | gamma, oi, spot | 2025-04-01T09:15:00+00:00 | 2026-03-30T15:15:00+00:00 |
| `hist_atm_option_bars_5m` | single_strike | `symbol` | `bar_ts` | gamma, oi, spot | 2025-04-01T09:15:00+00:00 | 2026-03-30T15:25:00+00:00 |
| `hist_future_bars_1m` | spot_only | `instrument_id` | `bar_ts` | spot | 2025-04-01T09:15:59+00:00 | 2026-03-30T15:30:59+00:00 |
| `hist_market_state` | spot_only | `symbol` | `bar_ts` | spot | 2025-04-01T09:15:59+00:00 | 2026-03-30T15:29:59+00:00 |
| `hist_option_bars_1m` | per_strike | `instrument_id` | `bar_ts` | gamma, iv, oi | 2025-04-01T09:15:59+00:00 | 2026-05-07T15:29:00+00:00 |
| `hist_option_greeks_1m` | per_strike | `instrument_id` | `trade_date` | gamma, iv | 2025-04-01 | 2026-03-30 |
| `hist_volatility_snapshots` | single_strike | `symbol` | `bar_ts` | iv, spot | 2025-04-01T09:15:59+00:00 | 2026-03-30T15:29:59+00:00 |
| `historical_index_futures_1m` | spot_only | `symbol` | `ts` | spot | 2026-03-19T09:58:04.018308+00:00 | 2026-09-11T10:30:05.855133+00:00 |
| `historical_option_chain_snapshots` | per_strike | `symbol` | `ts` | gamma, iv, oi, spot | 2026-03-16T09:51:09.542716+00:00 | 2026-06-03T09:59:00+00:00 |
| `latest_option_chain_run` | per_strike | `symbol` | `created_at` | gamma, iv, oi, spot | 2026-09-11T10:10:05.026862+00:00 | 2026-09-11T10:10:05.085908+00:00 |
| `latest_option_chain_snapshots` | per_strike | `symbol` | `ts` | gamma, iv, oi, spot | 2026-09-11T09:50:06.27105+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `latest_signal_snapshots` | single_strike | `symbol` | `ts` | iv, spot | 2026-09-11T09:50:06.27105+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `market_state_snapshots` | spot_only | `symbol` | `ts` | spot | 2026-03-08T08:07:24.742146+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `market_state_snapshots_replay` | spot_only | `symbol` | `ts` | spot | 2026-05-07T03:45:00+00:00 | 2026-05-07T09:55:00+00:00 |
| `market_state_snapshots_shadow` | spot_only | `symbol` | `ts` | spot | *empty relation* | *empty relation* |
| `market_ticks` | per_strike | `symbol` | `ts` | oi | *empty relation* | *empty relation* |
| `option_atm_snapshots` | single_strike | `symbol` | `created_at` | iv | *empty relation* | *empty relation* |
| `option_chain_snapshots` | per_strike | `symbol` | `ts` | gamma, iv, oi, spot | 2026-08-24T10:00:05.366368+00:00 | 2026-09-11T10:10:04.698857+00:00 |
| `option_chain_snapshots_replay` | per_strike | `symbol` | `ts` | gamma, iv, oi, spot | 2026-05-07T03:45:00+00:00 | 2026-05-07T09:55:00+00:00 |
| `option_execution_path_audit_v1` | single_strike | `symbol` | `created_at` | iv, spot | 2026-03-17T08:27:15.279799+00:00 | 2026-03-17T08:28:50.815701+00:00 |
| `option_execution_price_history` | per_strike | `symbol` | `ts` | iv, spot | 2026-03-18T05:48:52.407896+00:00 | 2026-03-27T09:59:18.417553+00:00 |
| `option_execution_snapshots` | single_strike | `symbol` | `created_at` | iv, spot | 2026-03-17T08:20:27.220215+00:00 | 2026-03-17T08:20:27.220215+00:00 |
| `shadow_signal_snapshots` | spot_only | `symbol` | `ts` | spot | 2026-03-13T09:13:28.265604+00:00 | 2026-03-13T13:19:13.317788+00:00 |
| `shadow_signal_validation_v1` | spot_only | `symbol` | `ts` | spot | 2026-03-13T09:13:28.265604+00:00 | 2026-03-13T13:19:13.317788+00:00 |
| `signal_snapshots` | single_strike | `symbol` | `ts` | iv, spot | 2026-03-08T07:12:13.021899+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `signal_snapshots_replay` | single_strike | `symbol` | `ts` | iv, spot | 2026-05-07T03:45:00+00:00 | 2026-05-07T09:55:00+00:00 |
| `signal_snapshots_shadow` | single_strike | `symbol` | `ts` | iv, spot | *empty relation* | *empty relation* |
| `volatility_snapshots` | single_strike | `symbol` | `ts` | iv, spot | 2025-04-01T03:45:00+00:00 | 2026-09-11T09:50:06.403106+00:00 |
| `volatility_snapshots_replay` | single_strike | `symbol` | `ts` | iv, spot | 2026-05-07T03:45:00+00:00 | 2026-05-07T09:55:00+00:00 |
| `wcb_signal_validation_v2` | spot_only | `symbol` | `ts` | spot | 2026-03-08T07:12:13.021899+00:00 | 2026-09-11T09:50:06.403106+00:00 |

Relations whose bounds did not come from the first-choice column, or which
hold no rows at all:

| relation | note |
|---|---|
| `hist_option_greeks_1m` | fell back to `trade_date` after `bar_ts`.asc: HTTP 500 (unresolved after 3 attempts) |
| `latest_option_chain_run` | fell back to `created_at` after `ts`.asc: HTTP 500 (unresolved after 3 attempts) |
| `market_state_snapshots_shadow` | relation holds no rows; probed `ts`, `created_at` and each returned a real empty list |
| `market_ticks` | relation holds no rows; probed `ts`, `created_at` and each returned a real empty list |
| `option_atm_snapshots` | relation holds no rows; probed `created_at` and each returned a real empty list |
| `signal_snapshots_shadow` | relation holds no rows; probed `ts`, `created_at` and each returned a real empty list |

An **empty relation** above is a measurement, not a failure: every scoping
column probed returned a real empty list. Such relations are excluded from the
day sweep because they can serve no day, and they are not listed in §10.

Query, per relation and direction:
```
GET /<rel>?select=<time_col>&order=<time_col>.asc|desc&limit=1
```

### 4b. Sources that did not reach the day sweep

A source can leave the sweep for three reasons, and they mean different
things. Most consequential first, in this list and in the table:

- **unmeasured** — its bounds never resolved, so its days were never probed.
  Its layers are **absent from every cell in §6**, and that absence is a hole
  in the method, not a property of the data. Any such row is also in §10 and
  therefore blocked this register from being written at all — if you are
  reading one here, read §10 before trusting §6.
- **unmeasurable by this method** — the relation cannot produce a real empty
  list (rule 6), so rule 3 cannot be satisfied for it on any day it holds no
  rows. Excluded by rule, with the measured timings below. This does **not**
  block the write: it is a measured property of the relation, stated, not a
  probe that went missing. What it does mean is that **this register says
  nothing about that relation** — neither presence nor absence. Do not read
  the exclusion as emptiness.
- **empty** — every scoping column returned a real empty list. The relation
  holds no rows, so it can serve no day. A *measurement*; no cell below is
  missing on its account.

| relation | why | layers it would have served | detail |
|---|---|---|---|
| `v_oi_prev_close_snapshots` | **unmeasurable** | oi | cannot produce a real empty list, so method rule 3 cannot be satisfied on any day it holds no rows: `prev_close_ts`: HTTP 500 after 8.4s; `prev_close_ts`: HTTP 500 after 8.4s; `prev_close_ts`: HTTP 500 after 8.4s |
| `market_state_snapshots_shadow` | **empty** | spot | relation holds no rows; it can serve no day, so no cell is missing on its account |
| `market_ticks` | **empty** | oi | relation holds no rows; it can serve no day, so no cell is missing on its account |
| `option_atm_snapshots` | **empty** | iv | relation holds no rows; it can serve no day, so no cell is missing on its account |
| `signal_snapshots_shadow` | **empty** | iv, spot | relation holds no rows; it can serve no day, so no cell is missing on its account |

Every layer an excluded source would have served is also served by at
least one source that was swept, so **no layer in §6 rests solely on an
exclusion**.

## 5. Identifier resolution

Several relations identify the underlying by `instrument_id uuid` rather than by
a symbol string. `public.instruments` resolves it.

| symbol | exchange | strike_step | lot_size |
|---|---|---:|---:|
| NIFTY | NSE | 50 | 65 |
| SENSEX | BSE | 100 | 20 |

```
GET /instruments?select=*
```

The UUID values themselves are deliberately not printed here; re-read them from
`instruments` rather than pasting them into a script.

## 6. What is computable, per symbol per trading day

**Denominator.** A day counts as a trading day for a symbol when
`hist_spot_bars_1m` holds at least one row for that symbol on that date — the
only relation spanning the full window for both symbols. Its limits are in §10.

**The three states.**

- **COMPUTABLE NOW** — per-strike gamma *and* the open interest to pair with it
  are available on that day, and a spot is available.
- **COMPUTABLE AFTER DERIVATION** — no gamma, but per-strike **iv** and OI are
  available, so Black-Scholes can supply the gamma.
- **NOT COMPUTABLE** — neither.

**Two verdicts, because the answer depends on whether a join is allowed.**

| verdict | means |
|---|---|
| `same-relation` | one relation carries gamma **and** OI in the same row |
| `joined` | gamma on one per-strike relation, OI on another, where the row-level key correspondence between that pair was **measured** to hold (§6.1) |

This is load-bearing, not cosmetic, and the reason is measured rather than
assumed. Counting days on which each per-strike relation actually supplied each
layer, across every day where the two verdicts disagree:

- **376** (symbol, day) cells are classified differently by the two
  verdicts, spanning 2025-04-01 … 2026-03-30.
- On those days, per-strike **gamma** was supplied by: `hist_option_greeks_1m` (376d).
- per-strike **OI** by: `hist_option_bars_1m` (376d).
- per-strike **iv** by: `hist_option_greeks_1m` (376d).
- relations supplying **both** gamma and OI on any of those days: **none** — which is exactly why `same-relation` cannot resolve them and a measured join can.

Quoting only `same-relation` would invert the headline wherever that split is
non-empty; quoting only `joined` would hide that those days depend on a join.
Both are below. **`joined` is the operative answer**, and it is only ever granted
on a pair whose correspondence was measured in §6.1.

| month | symbol | trading days | NOW (joined) | AFTER-DERIV (joined) | NOT (joined) | NOW (same-rel) | serving |
|---|---|---:|---:|---:|---:|---:|---|
| 2025-04 | NIFTY | 19 | 14 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (14d) |
| 2025-04 | SENSEX | 18 | 13 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (13d) |
| 2025-05 | NIFTY | 21 | 17 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (17d) |
| 2025-05 | SENSEX | 21 | 17 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (17d) |
| 2025-06 | NIFTY | 21 | 17 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (17d) |
| 2025-06 | SENSEX | 21 | 16 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (16d) |
| 2025-07 | NIFTY | 23 | 18 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (18d) |
| 2025-07 | SENSEX | 23 | 18 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (18d) |
| 2025-08 | NIFTY | 19 | 15 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (15d) |
| 2025-08 | SENSEX | 19 | 15 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (15d) |
| 2025-09 | NIFTY | 22 | 17 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (17d) |
| 2025-09 | SENSEX | 22 | 18 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (18d) |
| 2025-10 | NIFTY | 21 | 17 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (17d) |
| 2025-10 | SENSEX | 21 | 16 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (16d) |
| 2025-11 | NIFTY | 19 | 15 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (15d) |
| 2025-11 | SENSEX | 19 | 15 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (15d) |
| 2025-12 | NIFTY | 22 | 17 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (17d) |
| 2025-12 | SENSEX | 22 | 18 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (18d) |
| 2026-01 | NIFTY | 20 | 16 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (16d) |
| 2026-01 | SENSEX | 20 | 15 | 0 | 5 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (15d) |
| 2026-02 | NIFTY | 20 | 16 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (16d) |
| 2026-02 | SENSEX | 20 | 16 | 0 | 4 | 0 | `hist_option_greeks_1m+hist_option_bars_1m` (16d) |
| 2026-03 | NIFTY | 19 | 15 | 0 | 4 | 5 | `hist_option_greeks_1m+hist_option_bars_1m` (14d), `historical_option_chain_snapshots` (5d) |
| 2026-03 | SENSEX | 19 | 16 | 0 | 3 | 6 | `hist_option_greeks_1m+hist_option_bars_1m` (15d), `historical_option_chain_snapshots` (6d) |
| 2026-04 | NIFTY | 20 | 19 | 0 | 1 | 19 | `historical_option_chain_snapshots` (19d) |
| 2026-04 | SENSEX | 20 | 19 | 0 | 1 | 19 | `historical_option_chain_snapshots` (19d) |
| 2026-05 | NIFTY | 19 | 19 | 0 | 0 | 19 | `historical_option_chain_snapshots` (19d), `gex_strike_snapshots` (4d), `option_chain_snapshots_replay` (1d) |
| 2026-05 | SENSEX | 19 | 19 | 0 | 0 | 19 | `historical_option_chain_snapshots` (19d), `gex_strike_snapshots` (4d), `option_chain_snapshots_replay` (1d) |
| 2026-06 | NIFTY | 21 | 17 | 0 | 4 | 17 | `gex_strike_snapshots` (17d), `historical_option_chain_snapshots` (2d) |
| 2026-06 | SENSEX | 21 | 18 | 0 | 3 | 18 | `gex_strike_snapshots` (18d), `historical_option_chain_snapshots` (2d) |
| 2026-07 | NIFTY | 23 | 23 | 0 | 0 | 23 | `gex_strike_snapshots` (23d) |
| 2026-07 | SENSEX | 23 | 23 | 0 | 0 | 23 | `gex_strike_snapshots` (23d) |
| 2026-08 | NIFTY | 21 | 21 | 0 | 0 | 21 | `gex_strike_snapshots` (21d), `option_chain_snapshots` (6d) |
| 2026-08 | SENSEX | 21 | 21 | 0 | 0 | 21 | `gex_strike_snapshots` (21d), `option_chain_snapshots` (6d) |
| 2026-09 | NIFTY | 9 | 9 | 0 | 0 | 9 | `gex_strike_snapshots` (9d), `option_chain_snapshots` (9d), `latest_option_chain_run` (1d), `latest_option_chain_snapshots` (1d), `latest_option_chain_run+option_chain_snapshots` (1d), `latest_option_chain_snapshots+option_chain_snapshots` (1d) |
| 2026-09 | SENSEX | 9 | 9 | 0 | 0 | 9 | `gex_strike_snapshots` (9d), `option_chain_snapshots` (9d), `latest_option_chain_run` (1d), `latest_option_chain_snapshots` (1d), `latest_option_chain_run+option_chain_snapshots` (1d), `latest_option_chain_snapshots+option_chain_snapshots` (1d) |

A serving entry of the form `A+B` is a joined pair: gamma from `A`, OI from `B`.

### 6.1 The key correspondence that licenses every join

Two relations sharing five column names prove nothing about whether a given
contract-minute in one exists in the other. So each ordered pair was measured:
real key tuples were sampled from the gamma side and each was probed for in the
OI side. **A pair is used only at a perfect hit rate with zero unresolved
probes**; anything less is reported with its rate and not used.

An unresolved probe is counted in the denominator, never subtracted from it.
Subtracting would let 10 hits and 10 timeouts report 100% — a `57014` counted as
corroboration, which is method rule 2 running backwards.

The join's time column is taken from the columns the two relations **share**,
not from either one's scoping column, and a date-only column is refused: joining
on `trade_date` pairs every contract-minute of one side with every
contract-minute of the other across a whole session, which is a cross product.

```
GET /<gamma_rel>?select=<key cols>&<symbol>&<day>&limit=<n>       -- sample
GET /<oi_rel>?select=<k0>&<k0>=eq.<v0>&<k1>=eq.<v1>&...&limit=1   -- probe
```

| gamma side | OI side | symbol | key | sampled | hits | errors | rate | used |
|---|---|---|---|---:|---:|---:|---:|---|
| `gex_strike_snapshots` | `historical_option_chain_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `historical_option_chain_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `latest_option_chain_run` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `latest_option_chain_run` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `latest_option_chain_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `latest_option_chain_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `option_chain_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `gex_strike_snapshots` | `option_chain_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `hist_option_greeks_1m` | `hist_option_bars_1m` | NIFTY | `instrument_id`, `bar_ts`, `expiry_date`, `strike`, `option_type` | 60 | 60 | 0 | 100.0% | **yes** |
| `hist_option_greeks_1m` | `hist_option_bars_1m` | SENSEX | `instrument_id`, `bar_ts`, `expiry_date`, `strike`, `option_type` | 60 | 60 | 0 | 100.0% | **yes** |
| `hist_option_greeks_1m` | `historical_option_chain_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `hist_option_greeks_1m` | `historical_option_chain_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `historical_option_chain_snapshots` | `gex_strike_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `historical_option_chain_snapshots` | `gex_strike_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `historical_option_chain_snapshots` | `hist_option_bars_1m` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `historical_option_chain_snapshots` | `hist_option_bars_1m` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `historical_option_chain_snapshots` | `option_chain_snapshots_replay` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `historical_option_chain_snapshots` | `option_chain_snapshots_replay` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `latest_option_chain_run` | `gex_strike_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `latest_option_chain_run` | `gex_strike_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `latest_option_chain_run` | `latest_option_chain_snapshots` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 1 | 0 | 0 | 0.0% | no |
| `latest_option_chain_run` | `latest_option_chain_snapshots` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 1 | 0 | 0 | 0.0% | no |
| `latest_option_chain_run` | `option_chain_snapshots` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 1 | 1 | 0 | 100.0% | **yes** |
| `latest_option_chain_run` | `option_chain_snapshots` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 1 | 1 | 0 | 100.0% | **yes** |
| `latest_option_chain_snapshots` | `gex_strike_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `latest_option_chain_snapshots` | `gex_strike_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `latest_option_chain_snapshots` | `latest_option_chain_run` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `latest_option_chain_snapshots` | `latest_option_chain_run` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `latest_option_chain_snapshots` | `option_chain_snapshots` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 20 | 0 | 100.0% | **yes** |
| `latest_option_chain_snapshots` | `option_chain_snapshots` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 20 | 0 | 100.0% | **yes** |
| `option_chain_snapshots` | `gex_strike_snapshots` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `option_chain_snapshots` | `gex_strike_snapshots` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `option_chain_snapshots` | `latest_option_chain_run` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 1 | 0 | 5.0% | no |
| `option_chain_snapshots` | `latest_option_chain_run` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 1 | 0 | 5.0% | no |
| `option_chain_snapshots` | `latest_option_chain_snapshots` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `option_chain_snapshots` | `latest_option_chain_snapshots` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `option_chain_snapshots_replay` | `hist_option_bars_1m` | NIFTY | — | — | — | — | — | no — no shared row-level key |
| `option_chain_snapshots_replay` | `hist_option_bars_1m` | SENSEX | — | — | — | — | — | no — no shared row-level key |
| `option_chain_snapshots_replay` | `historical_option_chain_snapshots` | NIFTY | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |
| `option_chain_snapshots_replay` | `historical_option_chain_snapshots` | SENSEX | `symbol`, `ts`, `expiry_date`, `strike`, `option_type` | 20 | 0 | 0 | 0.0% | no |

Query, per source per symbol per day:
```
GET /<rel>?select=<time_col>&<symbol filter>&<day window>&limit=1      -- exists?
GET /<rel>?select=<col>&<col>=not.is.null&<symbol filter>&<day window>&limit=1
     <symbol filter> = symbol=eq.<SYM>   or   instrument_id=eq.<uuid>
     <day window>    = <tcol>=gte.<D>&<tcol>=lt.<D+1>   or   <tcol>=eq.<D>
```

### Totals

| | NIFTY | SENSEX |
|---|---:|---:|
| trading days measured | 359 | 358 |
| COMPUTABLE NOW (joined) | 302 | 302 |
| COMPUTABLE AFTER DERIVATION (joined) | 0 | 0 |
| NOT COMPUTABLE (joined) | 57 | 56 |
| COMPUTABLE NOW (same-relation only) | 113 | 115 |
| NOT COMPUTABLE (same-relation only) | 246 | 243 |

### Cross-check against the S75 sweep

`docs/research/data_inventory_2026-09-08.md` §6 measured this question on
2026-09-08 over 2025-04-01..2026-09-08. Those figures are quoted as prior art
and are **not** an input to anything above. This run's totals are recomputed
over that same window so the two are comparable.

|  | NIFTY S75 | SENSEX S75 | NIFTY now | SENSEX now | delta |
|---|---:|---:|---:|---:|---|
| trading days | 356 | 355 | 356 | 355 | NIFTY +0, SENSEX +0 |
| COMPUTABLE NOW | 299 | 299 | 299 | 299 | NIFTY +0, SENSEX +0 |
| COMPUTABLE AFTER DERIVATION | 0 | 0 | 0 | 0 | NIFTY +0, SENSEX +0 |
| NOT COMPUTABLE | 57 | 56 | 57 | 56 | NIFTY +0, SENSEX +0 |

A non-zero delta is not automatically an error — the database has moved since
that date, and this run's classifier differs in ways §6 and §6.1 state
explicitly. But **a delta with no explanation is not a result.** Read §4 and
§6.1 before quoting any number that disagrees with the row above.

### Layer availability, counted independently of the verdict

A day can have OI without gamma, or spot without either. These columns count
days on which **any** relation supplied that layer, so they do not sum to the
verdict above and are not meant to.

**Per-strike** columns count relations keyed by `strike` — a chain.
**ATM-only** columns count `single_strike` relations, which hold one
distinguished strike (`atm_strike`, `ce_strike`) per row. ATM-only availability
is **measured and reported but never admitted to the verdict**: one strike is
not a chain, and a GEX cannot be computed from it. It is here because "is there
ATM gamma on a day the chain has none" is a real question with a real answer.

| symbol | days | gamma (per-strike) | iv (per-strike) | oi (per-strike) | gamma (ATM-only) | iv (ATM-only) | oi (ATM-only) | spot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NIFTY | 359 | 302 | 249 | 355 | 0 | 355 | 246 | 355 |
| SENSEX | 358 | 302 | 248 | 354 | 0 | 354 | 244 | 354 |

No day carries ATM gamma without also carrying per-strike gamma.

### Days NOT COMPUTABLE, enumerated

Listed under the **joined** verdict. The `same-relation`-only count is given
beside it, and where the two differ the difference is the set of days that exist
solely because a measured join licenses them — those days are enumerated
separately, because a reader who intends to compute without joining needs to
know which days they lose.

**NIFTY — 57 days NOT COMPUTABLE (joined); 246 (same-relation only).**

```
  2025-04-03  2025-04-09  2025-04-17  2025-04-24  2025-04-30  2025-05-08  2025-05-15  2025-05-22
  2025-05-29  2025-06-05  2025-06-12  2025-06-19  2025-06-26  2025-07-03  2025-07-10  2025-07-17
  2025-07-24  2025-07-31  2025-08-07  2025-08-14  2025-08-21  2025-08-28  2025-09-02  2025-09-09
  2025-09-16  2025-09-23  2025-09-30  2025-10-07  2025-10-14  2025-10-20  2025-10-28  2025-11-04
  2025-11-11  2025-11-18  2025-11-25  2025-12-02  2025-12-09  2025-12-16  2025-12-23  2025-12-30
  2026-01-06  2026-01-13  2026-01-20  2026-01-27  2026-02-03  2026-02-10  2026-02-17  2026-02-24
  2026-03-02  2026-03-10  2026-03-17  2026-03-30  2026-04-16  2026-06-03  2026-06-04  2026-06-08
  2026-06-11
```

Of those, **189 days are computable ONLY via a measured
join** — they are NOT COMPUTABLE if you restrict yourself to a single
relation:

```
  2025-04-01  2025-04-02  2025-04-04  2025-04-07  2025-04-08  2025-04-11  2025-04-15  2025-04-16
  2025-04-21  2025-04-22  2025-04-23  2025-04-25  2025-04-28  2025-04-29  2025-05-02  2025-05-05
  2025-05-06  2025-05-07  2025-05-09  2025-05-12  2025-05-13  2025-05-14  2025-05-16  2025-05-19
  2025-05-20  2025-05-21  2025-05-23  2025-05-26  2025-05-27  2025-05-28  2025-05-30  2025-06-02
  2025-06-03  2025-06-04  2025-06-06  2025-06-09  2025-06-10  2025-06-11  2025-06-13  2025-06-16
  2025-06-17  2025-06-18  2025-06-20  2025-06-23  2025-06-24  2025-06-25  2025-06-27  2025-06-30
  2025-07-01  2025-07-02  2025-07-04  2025-07-07  2025-07-08  2025-07-09  2025-07-11  2025-07-14
  2025-07-15  2025-07-16  2025-07-18  2025-07-21  2025-07-22  2025-07-23  2025-07-25  2025-07-28
  2025-07-29  2025-07-30  2025-08-01  2025-08-04  2025-08-05  2025-08-06  2025-08-08  2025-08-11
  2025-08-12  2025-08-13  2025-08-18  2025-08-19  2025-08-20  2025-08-22  2025-08-25  2025-08-26
  2025-08-29  2025-09-01  2025-09-03  2025-09-04  2025-09-05  2025-09-08  2025-09-10  2025-09-11
  2025-09-12  2025-09-15  2025-09-17  2025-09-18  2025-09-19  2025-09-22  2025-09-24  2025-09-25
  2025-09-26  2025-09-29  2025-10-01  2025-10-03  2025-10-06  2025-10-08  2025-10-09  2025-10-10
  2025-10-13  2025-10-15  2025-10-16  2025-10-17  2025-10-21  2025-10-23  2025-10-24  2025-10-27
  2025-10-29  2025-10-30  2025-10-31  2025-11-03  2025-11-06  2025-11-07  2025-11-10  2025-11-12
  2025-11-13  2025-11-14  2025-11-17  2025-11-19  2025-11-20  2025-11-21  2025-11-24  2025-11-26
  2025-11-27  2025-11-28  2025-12-01  2025-12-03  2025-12-04  2025-12-05  2025-12-08  2025-12-10
  2025-12-11  2025-12-12  2025-12-15  2025-12-17  2025-12-18  2025-12-19  2025-12-22  2025-12-24
  2025-12-26  2025-12-29  2025-12-31  2026-01-01  2026-01-02  2026-01-05  2026-01-07  2026-01-08
  2026-01-09  2026-01-12  2026-01-14  2026-01-16  2026-01-19  2026-01-21  2026-01-22  2026-01-23
  2026-01-28  2026-01-29  2026-01-30  2026-02-02  2026-02-04  2026-02-05  2026-02-06  2026-02-09
  2026-02-11  2026-02-12  2026-02-13  2026-02-16  2026-02-18  2026-02-19  2026-02-20  2026-02-23
  2026-02-25  2026-02-26  2026-02-27  2026-03-04  2026-03-05  2026-03-06  2026-03-09  2026-03-11
  2026-03-12  2026-03-13  2026-03-16  2026-03-18  2026-03-19
```

**SENSEX — 56 days NOT COMPUTABLE (joined); 243 (same-relation only).**

```
  2025-04-01  2025-04-08  2025-04-15  2025-04-22  2025-04-29  2025-05-06  2025-05-13  2025-05-20
  2025-05-27  2025-06-03  2025-06-05  2025-06-10  2025-06-17  2025-06-24  2025-07-01  2025-07-08
  2025-07-15  2025-07-22  2025-07-29  2025-08-05  2025-08-12  2025-08-19  2025-08-26  2025-09-04
  2025-09-11  2025-09-18  2025-09-25  2025-10-01  2025-10-09  2025-10-16  2025-10-23  2025-10-30
  2025-11-06  2025-11-13  2025-11-20  2025-11-27  2025-12-04  2025-12-11  2025-12-18  2025-12-24
  2026-01-01  2026-01-08  2026-01-14  2026-01-22  2026-01-29  2026-02-05  2026-02-12  2026-02-19
  2026-02-26  2026-03-05  2026-03-12  2026-03-19  2026-04-16  2026-06-03  2026-06-04  2026-06-08
```

Of those, **187 days are computable ONLY via a measured
join** — they are NOT COMPUTABLE if you restrict yourself to a single
relation:

```
  2025-04-02  2025-04-03  2025-04-04  2025-04-07  2025-04-09  2025-04-11  2025-04-16  2025-04-17
  2025-04-21  2025-04-23  2025-04-24  2025-04-25  2025-04-30  2025-05-02  2025-05-05  2025-05-07
  2025-05-08  2025-05-09  2025-05-12  2025-05-14  2025-05-15  2025-05-16  2025-05-19  2025-05-21
  2025-05-22  2025-05-23  2025-05-26  2025-05-28  2025-05-29  2025-05-30  2025-06-02  2025-06-04
  2025-06-06  2025-06-09  2025-06-11  2025-06-12  2025-06-13  2025-06-16  2025-06-18  2025-06-19
  2025-06-20  2025-06-23  2025-06-25  2025-06-26  2025-06-27  2025-06-30  2025-07-02  2025-07-03
  2025-07-04  2025-07-07  2025-07-09  2025-07-10  2025-07-11  2025-07-14  2025-07-16  2025-07-17
  2025-07-18  2025-07-21  2025-07-23  2025-07-24  2025-07-25  2025-07-28  2025-07-30  2025-07-31
  2025-08-01  2025-08-04  2025-08-06  2025-08-07  2025-08-08  2025-08-11  2025-08-13  2025-08-14
  2025-08-18  2025-08-20  2025-08-21  2025-08-22  2025-08-25  2025-08-28  2025-08-29  2025-09-01
  2025-09-02  2025-09-03  2025-09-05  2025-09-08  2025-09-09  2025-09-10  2025-09-12  2025-09-15
  2025-09-16  2025-09-17  2025-09-19  2025-09-22  2025-09-23  2025-09-24  2025-09-26  2025-09-29
  2025-09-30  2025-10-03  2025-10-06  2025-10-07  2025-10-08  2025-10-10  2025-10-13  2025-10-14
  2025-10-15  2025-10-17  2025-10-20  2025-10-21  2025-10-24  2025-10-27  2025-10-28  2025-10-29
  2025-10-31  2025-11-03  2025-11-04  2025-11-07  2025-11-10  2025-11-11  2025-11-12  2025-11-14
  2025-11-17  2025-11-18  2025-11-19  2025-11-21  2025-11-24  2025-11-25  2025-11-26  2025-11-28
  2025-12-01  2025-12-02  2025-12-03  2025-12-05  2025-12-08  2025-12-09  2025-12-10  2025-12-12
  2025-12-15  2025-12-16  2025-12-17  2025-12-19  2025-12-22  2025-12-23  2025-12-26  2025-12-29
  2025-12-30  2025-12-31  2026-01-02  2026-01-05  2026-01-06  2026-01-07  2026-01-09  2026-01-12
  2026-01-13  2026-01-16  2026-01-19  2026-01-20  2026-01-21  2026-01-23  2026-01-27  2026-01-28
  2026-01-30  2026-02-02  2026-02-03  2026-02-04  2026-02-06  2026-02-09  2026-02-10  2026-02-11
  2026-02-13  2026-02-16  2026-02-17  2026-02-18  2026-02-20  2026-02-23  2026-02-24  2026-02-25
  2026-02-27  2026-03-02  2026-03-04  2026-03-06  2026-03-09  2026-03-10  2026-03-11  2026-03-13
  2026-03-17  2026-03-18  2026-03-30
```

### 6.2 How much — row counts, not just presence

Presence is a yes/no. It does not distinguish a session with a full chain
from one with four rows scraped after a restart, and a register that only
says *yes* invites exactly that mistake. So every cell the sweep found
**present** was then counted with `count=exact` on the same day scope.

Counted per **relation-day**, not per layer-day: gamma, iv and oi on one
relation live in the same rows, so a per-layer count would be the same number
repeated. No new presence probe was issued — this only puts a number on cells
already known to be non-empty.

**5,182** (symbol, day, relation) cells were eligible. **5,182** returned a count; **0** failed; **0** were skipped.

An unproven count is **not** an unresolved presence probe and is not in
§10. The sweep already established that rows exist on that day; a
`count=exact` that times out leaves the *number* missing, not the *fact*.
Recording it as unresolved would block this register over a supplementary
measurement and would also assert something false — that presence is in
doubt. It is not.

```
GET /<rel>?select=*&limit=0&<symbol filter>&<day window>   Prefer: count=exact
```

| symbol | month | relation | days | total rows | median/day | min | max |
|---|---|---|---:|---:|---:|---:|---:|
| NIFTY | 2025-04 | `hist_atm_option_bars_15m` | 19 | 363 | 23 | 2 | 26 |
| NIFTY | 2025-04 | `hist_atm_option_bars_5m` | 19 | 1,001 | 62 | 5 | 76 |
| NIFTY | 2025-04 | `hist_future_bars_1m` | 19 | 20,381 | 1,097 | 939 | 1,124 |
| NIFTY | 2025-04 | `hist_market_state` | 18 | 6,758 | 376 | 374 | 376 |
| NIFTY | 2025-04 | `hist_option_bars_1m` | 19 | 3,198,468 | 165,040 | 154,365 | 209,996 |
| NIFTY | 2025-04 | `hist_option_greeks_1m` | 14 | 707,530 | 51,537 | 45,602 | 55,143 |
| NIFTY | 2025-04 | `hist_volatility_snapshots` | 19 | 6,780 | 376 | 279 | 376 |
| NIFTY | 2025-04 | `volatility_snapshots` | 19 | 991 | 61 | 5 | 75 |
| NIFTY | 2025-05 | `hist_atm_option_bars_15m` | 21 | 449 | 26 | 3 | 26 |
| NIFTY | 2025-05 | `hist_atm_option_bars_5m` | 21 | 1,255 | 72 | 8 | 76 |
| NIFTY | 2025-05 | `hist_future_bars_1m` | 21 | 22,561 | 1,094 | 985 | 1,126 |
| NIFTY | 2025-05 | `hist_market_state` | 21 | 7,888 | 376 | 374 | 376 |
| NIFTY | 2025-05 | `hist_option_bars_1m` | 21 | 3,206,177 | 152,300 | 123,140 | 184,453 |
| NIFTY | 2025-05 | `hist_option_greeks_1m` | 17 | 858,221 | 51,840 | 43,022 | 54,670 |
| NIFTY | 2025-05 | `hist_volatility_snapshots` | 21 | 7,822 | 376 | 345 | 376 |
| NIFTY | 2025-05 | `volatility_snapshots` | 21 | 1,240 | 71 | 8 | 75 |
| NIFTY | 2025-06 | `hist_atm_option_bars_15m` | 21 | 444 | 26 | 6 | 26 |
| NIFTY | 2025-06 | `hist_atm_option_bars_5m` | 21 | 1,271 | 76 | 14 | 76 |
| NIFTY | 2025-06 | `hist_future_bars_1m` | 21 | 22,384 | 1,068 | 976 | 1,125 |
| NIFTY | 2025-06 | `hist_market_state` | 21 | 7,888 | 376 | 374 | 376 |
| NIFTY | 2025-06 | `hist_option_bars_1m` | 21 | 3,059,030 | 141,666 | 122,241 | 191,862 |
| NIFTY | 2025-06 | `hist_option_greeks_1m` | 17 | 783,045 | 42,793 | 39,701 | 60,523 |
| NIFTY | 2025-06 | `hist_volatility_snapshots` | 21 | 7,807 | 376 | 338 | 376 |
| NIFTY | 2025-06 | `volatility_snapshots` | 21 | 1,258 | 75 | 14 | 75 |
| NIFTY | 2025-07 | `hist_atm_option_bars_15m` | 23 | 530 | 26 | 6 | 26 |
| NIFTY | 2025-07 | `hist_atm_option_bars_5m` | 23 | 1,529 | 76 | 15 | 76 |
| NIFTY | 2025-07 | `hist_future_bars_1m` | 23 | 23,651 | 1,030 | 900 | 1,125 |
| NIFTY | 2025-07 | `hist_market_state` | 23 | 8,638 | 376 | 374 | 376 |
| NIFTY | 2025-07 | `hist_option_bars_1m` | 23 | 2,948,985 | 127,430 | 110,211 | 160,258 |
| NIFTY | 2025-07 | `hist_option_greeks_1m` | 18 | 726,674 | 39,623 | 36,745 | 46,304 |
| NIFTY | 2025-07 | `hist_volatility_snapshots` | 23 | 8,571 | 376 | 355 | 376 |
| NIFTY | 2025-07 | `volatility_snapshots` | 23 | 1,511 | 75 | 15 | 75 |
| NIFTY | 2025-08 | `hist_atm_option_bars_15m` | 19 | 454 | 26 | 3 | 26 |
| NIFTY | 2025-08 | `hist_atm_option_bars_5m` | 19 | 1,322 | 76 | 9 | 76 |
| NIFTY | 2025-08 | `hist_future_bars_1m` | 19 | 19,752 | 1,043 | 952 | 1,125 |
| NIFTY | 2025-08 | `hist_market_state` | 19 | 7,136 | 376 | 374 | 376 |
| NIFTY | 2025-08 | `hist_option_bars_1m` | 19 | 2,465,320 | 127,126 | 117,776 | 164,195 |
| NIFTY | 2025-08 | `hist_option_greeks_1m` | 15 | 593,176 | 39,042 | 37,247 | 45,522 |
| NIFTY | 2025-08 | `hist_volatility_snapshots` | 19 | 7,037 | 376 | 329 | 376 |
| NIFTY | 2025-08 | `volatility_snapshots` | 19 | 1,308 | 75 | 9 | 75 |
| NIFTY | 2025-09 | `hist_atm_option_bars_15m` | 22 | 537 | 26 | 12 | 26 |
| NIFTY | 2025-09 | `hist_atm_option_bars_5m` | 22 | 1,555 | 76 | 32 | 76 |
| NIFTY | 2025-09 | `hist_future_bars_1m` | 22 | 22,588 | 1,035 | 893 | 1,114 |
| NIFTY | 2025-09 | `hist_market_state` | 22 | 8,262 | 376 | 374 | 376 |
| NIFTY | 2025-09 | `hist_option_bars_1m` | 22 | 2,804,700 | 126,378 | 107,091 | 151,799 |
| NIFTY | 2025-09 | `hist_option_greeks_1m` | 17 | 686,997 | 39,087 | 36,624 | 49,177 |
| NIFTY | 2025-09 | `hist_volatility_snapshots` | 22 | 8,134 | 376 | 342 | 376 |
| NIFTY | 2025-09 | `volatility_snapshots` | 22 | 1,538 | 75 | 31 | 75 |
| NIFTY | 2025-10 | `hist_atm_option_bars_15m` | 21 | 459 | 26 | 5 | 26 |
| NIFTY | 2025-10 | `hist_atm_option_bars_5m` | 21 | 1,304 | 73 | 13 | 76 |
| NIFTY | 2025-10 | `hist_future_bars_1m` | 21 | 21,306 | 1,057 | 181 | 1,122 |
| NIFTY | 2025-10 | `hist_market_state` | 21 | 7,573 | 376 | 61 | 376 |
| NIFTY | 2025-10 | `hist_option_bars_1m` | 21 | 2,789,600 | 136,228 | 22,662 | 166,912 |
| NIFTY | 2025-10 | `hist_option_greeks_1m` | 17 | 679,539 | 40,049 | 7,853 | 49,074 |
| NIFTY | 2025-10 | `hist_volatility_snapshots` | 21 | 7,445 | 376 | 61 | 376 |
| NIFTY | 2025-10 | `volatility_snapshots` | 21 | 1,291 | 72 | 13 | 75 |
| NIFTY | 2025-11 | `hist_atm_option_bars_15m` | 19 | 438 | 26 | 4 | 26 |
| NIFTY | 2025-11 | `hist_atm_option_bars_5m` | 19 | 1,257 | 74 | 8 | 76 |
| NIFTY | 2025-11 | `hist_future_bars_1m` | 19 | 19,847 | 1,051 | 920 | 1,110 |
| NIFTY | 2025-11 | `hist_market_state` | 19 | 7,136 | 376 | 374 | 376 |
| NIFTY | 2025-11 | `hist_option_bars_1m` | 19 | 2,595,988 | 136,083 | 122,697 | 156,890 |
| NIFTY | 2025-11 | `hist_option_greeks_1m` | 15 | 633,585 | 41,687 | 38,422 | 46,487 |
| NIFTY | 2025-11 | `hist_volatility_snapshots` | 19 | 7,086 | 376 | 359 | 376 |
| NIFTY | 2025-11 | `volatility_snapshots` | 19 | 1,244 | 73 | 8 | 75 |
| NIFTY | 2025-12 | `hist_atm_option_bars_15m` | 22 | 514 | 26 | 14 | 26 |
| NIFTY | 2025-12 | `hist_atm_option_bars_5m` | 22 | 1,473 | 76 | 40 | 76 |
| NIFTY | 2025-12 | `hist_future_bars_1m` | 22 | 22,999 | 1,049 | 987 | 1,119 |
| NIFTY | 2025-12 | `hist_market_state` | 22 | 8,262 | 376 | 374 | 376 |
| NIFTY | 2025-12 | `hist_option_bars_1m` | 22 | 2,883,402 | 128,589 | 113,282 | 156,711 |
| NIFTY | 2025-12 | `hist_option_greeks_1m` | 17 | 663,570 | 38,772 | 35,822 | 44,319 |
| NIFTY | 2025-12 | `hist_volatility_snapshots` | 22 | 8,210 | 376 | 360 | 376 |
| NIFTY | 2025-12 | `volatility_snapshots` | 22 | 1,456 | 75 | 40 | 75 |
| NIFTY | 2026-01 | `hist_atm_option_bars_15m` | 20 | 432 | 25 | 7 | 26 |
| NIFTY | 2026-01 | `hist_atm_option_bars_5m` | 20 | 1,229 | 70 | 20 | 76 |
| NIFTY | 2026-01 | `hist_future_bars_1m` | 20 | 21,291 | 1,076 | 873 | 1,124 |
| NIFTY | 2026-01 | `hist_market_state` | 20 | 7,512 | 376 | 374 | 376 |
| NIFTY | 2026-01 | `hist_option_bars_1m` | 20 | 2,986,009 | 150,526 | 111,237 | 184,312 |
| NIFTY | 2026-01 | `hist_option_greeks_1m` | 16 | 675,373 | 40,458 | 34,526 | 49,036 |
| NIFTY | 2026-01 | `hist_volatility_snapshots` | 20 | 7,469 | 376 | 359 | 376 |
| NIFTY | 2026-01 | `volatility_snapshots` | 20 | 1,216 | 70 | 20 | 75 |
| NIFTY | 2026-02 | `hist_atm_option_bars_15m` | 20 | 452 | 26 | 8 | 26 |
| NIFTY | 2026-02 | `hist_atm_option_bars_5m` | 20 | 1,277 | 74 | 21 | 76 |
| NIFTY | 2026-02 | `hist_future_bars_1m` | 20 | 21,058 | 1,050 | 960 | 1,124 |
| NIFTY | 2026-02 | `hist_market_state` | 20 | 7,512 | 376 | 374 | 376 |
| NIFTY | 2026-02 | `hist_option_bars_1m` | 20 | 3,109,975 | 152,100 | 120,324 | 213,964 |
| NIFTY | 2026-02 | `hist_option_greeks_1m` | 16 | 740,467 | 46,300 | 42,426 | 49,941 |
| NIFTY | 2026-02 | `hist_volatility_snapshots` | 19 | 7,112 | 376 | 362 | 376 |
| NIFTY | 2026-02 | `volatility_snapshots` | 20 | 1,264 | 73 | 21 | 75 |
| NIFTY | 2026-03 | `hist_atm_option_bars_15m` | 19 | 335 | 19 | 3 | 26 |
| NIFTY | 2026-03 | `hist_atm_option_bars_5m` | 19 | 925 | 56 | 7 | 72 |
| NIFTY | 2026-03 | `hist_future_bars_1m` | 19 | 21,219 | 1,122 | 1,055 | 1,127 |
| NIFTY | 2026-03 | `hist_market_state` | 18 | 6,760 | 376 | 374 | 376 |
| NIFTY | 2026-03 | `hist_option_bars_1m` | 19 | 3,610,586 | 182,160 | 158,475 | 217,066 |
| NIFTY | 2026-03 | `hist_option_greeks_1m` | 14 | 798,918 | 57,778 | 47,042 | 68,693 |
| NIFTY | 2026-03 | `hist_volatility_snapshots` | 19 | 7,094 | 376 | 365 | 376 |
| NIFTY | 2026-03 | `historical_index_futures_1m` | 7 | 1,334 | 258 | 1 | 379 |
| NIFTY | 2026-03 | `historical_option_chain_snapshots` | 5 | 108,788 | 22,428 | 614 | 46,050 |
| NIFTY | 2026-03 | `market_state_snapshots` | 13 | 417 | 15 | 1 | 115 |
| NIFTY | 2026-03 | `option_execution_path_audit_v1` | 1 | 3,660 | 3,660 | 3,660 | 3,660 |
| NIFTY | 2026-03 | `option_execution_price_history` | 7 | 6,196 | 1,128 | 4 | 1,512 |
| NIFTY | 2026-03 | `option_execution_snapshots` | 1 | 60 | 60 | 60 | 60 |
| NIFTY | 2026-03 | `shadow_signal_snapshots` | 1 | 5 | 5 | 5 | 5 |
| NIFTY | 2026-03 | `shadow_signal_validation_v1` | 1 | 5 | 5 | 5 | 5 |
| NIFTY | 2026-03 | `signal_snapshots` | 8 | 80 | 9 | 2 | 25 |
| NIFTY | 2026-03 | `volatility_snapshots` | 19 | 1,214 | 63 | 22 | 138 |
| NIFTY | 2026-03 | `wcb_signal_validation_v2` | 8 | 80 | 9 | 2 | 25 |
| NIFTY | 2026-04 | `historical_option_chain_snapshots` | 20 | 720,571 | 35,559 | 19,810 | 61,899 |
| NIFTY | 2026-04 | `market_state_snapshots` | 20 | 1,921 | 81 | 49 | 150 |
| NIFTY | 2026-04 | `signal_snapshots` | 20 | 2,090 | 97 | 53 | 153 |
| NIFTY | 2026-04 | `volatility_snapshots` | 20 | 2,087 | 97 | 53 | 153 |
| NIFTY | 2026-04 | `wcb_signal_validation_v2` | 20 | 2,090 | 97 | 53 | 153 |
| NIFTY | 2026-05 | `gex_strike_snapshots` | 4 | 25,950 | 7,791 | 144 | 10,224 |
| NIFTY | 2026-05 | `hist_option_bars_1m` | 2 | 9,262 | 4,631 | 1,012 | 8,250 |
| NIFTY | 2026-05 | `historical_option_chain_snapshots` | 19 | 727,288 | 34,780 | 17,920 | 129,250 |
| NIFTY | 2026-05 | `market_state_snapshots` | 19 | 1,780 | 74 | 40 | 208 |
| NIFTY | 2026-05 | `market_state_snapshots_replay` | 1 | 74 | 74 | 74 | 74 |
| NIFTY | 2026-05 | `option_chain_snapshots_replay` | 1 | 1,650 | 1,650 | 1,650 | 1,650 |
| NIFTY | 2026-05 | `signal_snapshots` | 19 | 2,546 | 146 | 72 | 349 |
| NIFTY | 2026-05 | `signal_snapshots_replay` | 1 | 76 | 76 | 76 | 76 |
| NIFTY | 2026-05 | `volatility_snapshots` | 19 | 2,545 | 146 | 72 | 350 |
| NIFTY | 2026-05 | `volatility_snapshots_replay` | 1 | 75 | 75 | 75 | 75 |
| NIFTY | 2026-05 | `wcb_signal_validation_v2` | 19 | 2,546 | 146 | 72 | 349 |
| NIFTY | 2026-06 | `gamma_metrics` | 13 | 824 | 83 | 1 | 84 |
| NIFTY | 2026-06 | `gex_strike_snapshots` | 18 | 121,928 | 7,738 | 101 | 12,516 |
| NIFTY | 2026-06 | `historical_index_futures_1m` | 8 | 8 | 1 | 1 | 1 |
| NIFTY | 2026-06 | `historical_option_chain_snapshots` | 2 | 68,620 | 34,310 | 33,840 | 34,780 |
| NIFTY | 2026-06 | `market_state_snapshots` | 18 | 1,011 | 73 | 1 | 84 |
| NIFTY | 2026-06 | `signal_snapshots` | 18 | 1,332 | 83 | 1 | 124 |
| NIFTY | 2026-06 | `volatility_snapshots` | 17 | 979 | 74 | 1 | 84 |
| NIFTY | 2026-06 | `wcb_signal_validation_v2` | 18 | 1,332 | 83 | 1 | 124 |
| NIFTY | 2026-07 | `gamma_metrics` | 23 | 1,893 | 83 | 68 | 84 |
| NIFTY | 2026-07 | `gex_strike_snapshots` | 23 | 186,424 | 8,217 | 6,324 | 8,820 |
| NIFTY | 2026-07 | `historical_index_futures_1m` | 22 | 22 | 1 | 1 | 1 |
| NIFTY | 2026-07 | `market_state_snapshots` | 23 | 1,893 | 83 | 68 | 84 |
| NIFTY | 2026-07 | `signal_snapshots` | 23 | 1,917 | 84 | 68 | 86 |
| NIFTY | 2026-07 | `volatility_snapshots` | 23 | 1,891 | 83 | 68 | 84 |
| NIFTY | 2026-07 | `wcb_signal_validation_v2` | 23 | 1,917 | 84 | 68 | 86 |
| NIFTY | 2026-08 | `gamma_metrics` | 21 | 1,709 | 83 | 64 | 84 |
| NIFTY | 2026-08 | `gex_strike_snapshots` | 21 | 189,037 | 9,126 | 6,720 | 10,164 |
| NIFTY | 2026-08 | `historical_index_futures_1m` | 17 | 17 | 1 | 1 | 1 |
| NIFTY | 2026-08 | `market_state_snapshots` | 21 | 1,707 | 83 | 63 | 84 |
| NIFTY | 2026-08 | `option_chain_snapshots` | 6 | 159,442 | 39,501 | 488 | 39,732 |
| NIFTY | 2026-08 | `signal_snapshots` | 21 | 1,733 | 84 | 65 | 85 |
| NIFTY | 2026-08 | `volatility_snapshots` | 21 | 1,709 | 83 | 64 | 84 |
| NIFTY | 2026-08 | `wcb_signal_validation_v2` | 21 | 1,733 | 84 | 65 | 85 |
| NIFTY | 2026-09 | `gamma_metrics` | 9 | 745 | 83 | 81 | 84 |
| NIFTY | 2026-09 | `gex_strike_snapshots` | 9 | 66,519 | 7,295 | 6,797 | 8,715 |
| NIFTY | 2026-09 | `historical_index_futures_1m` | 9 | 9 | 1 | 1 | 1 |
| NIFTY | 2026-09 | `latest_option_chain_run` | 1 | 1 | 1 | 1 | 1 |
| NIFTY | 2026-09 | `latest_option_chain_snapshots` | 1 | 462 | 462 | 462 | 462 |
| NIFTY | 2026-09 | `latest_signal_snapshots` | 1 | 1 | 1 | 1 | 1 |
| NIFTY | 2026-09 | `market_state_snapshots` | 9 | 745 | 83 | 81 | 84 |
| NIFTY | 2026-09 | `option_chain_snapshots` | 9 | 352,326 | 39,216 | 37,910 | 40,194 |
| NIFTY | 2026-09 | `signal_snapshots` | 9 | 754 | 84 | 82 | 86 |
| NIFTY | 2026-09 | `volatility_snapshots` | 9 | 745 | 83 | 81 | 84 |
| NIFTY | 2026-09 | `wcb_signal_validation_v2` | 9 | 754 | 84 | 82 | 86 |
| SENSEX | 2025-04 | `hist_atm_option_bars_15m` | 18 | 263 | 15 | 2 | 25 |
| SENSEX | 2025-04 | `hist_atm_option_bars_5m` | 18 | 704 | 32 | 5 | 75 |
| SENSEX | 2025-04 | `hist_market_state` | 18 | 6,746 | 375 | 374 | 376 |
| SENSEX | 2025-04 | `hist_option_bars_1m` | 19 | 1,467,760 | 83,495 | 57,945 | 102,483 |
| SENSEX | 2025-04 | `hist_option_greeks_1m` | 13 | 770,238 | 57,655 | 49,705 | 72,873 |
| SENSEX | 2025-04 | `hist_volatility_snapshots` | 18 | 6,650 | 375 | 347 | 375 |
| SENSEX | 2025-04 | `volatility_snapshots` | 18 | 704 | 32 | 5 | 75 |
| SENSEX | 2025-05 | `hist_atm_option_bars_15m` | 21 | 339 | 17 | 1 | 25 |
| SENSEX | 2025-05 | `hist_atm_option_bars_5m` | 21 | 929 | 47 | 1 | 75 |
| SENSEX | 2025-05 | `hist_future_bars_1m` | 21 | 9,520 | 372 | 274 | 895 |
| SENSEX | 2025-05 | `hist_market_state` | 21 | 7,871 | 375 | 373 | 376 |
| SENSEX | 2025-05 | `hist_option_bars_1m` | 21 | 1,645,447 | 78,228 | 58,084 | 111,734 |
| SENSEX | 2025-05 | `hist_option_greeks_1m` | 17 | 1,061,296 | 60,901 | 53,248 | 76,591 |
| SENSEX | 2025-05 | `hist_volatility_snapshots` | 21 | 7,845 | 375 | 363 | 375 |
| SENSEX | 2025-05 | `volatility_snapshots` | 21 | 929 | 47 | 1 | 75 |
| SENSEX | 2025-06 | `hist_atm_option_bars_15m` | 20 | 332 | 17 | 4 | 25 |
| SENSEX | 2025-06 | `hist_atm_option_bars_5m` | 20 | 942 | 47 | 11 | 75 |
| SENSEX | 2025-06 | `hist_future_bars_1m` | 20 | 9,400 | 443 | 241 | 924 |
| SENSEX | 2025-06 | `hist_market_state` | 20 | 7,497 | 375 | 374 | 376 |
| SENSEX | 2025-06 | `hist_option_bars_1m` | 20 | 1,457,470 | 70,984 | 55,914 | 96,411 |
| SENSEX | 2025-06 | `hist_option_greeks_1m` | 16 | 892,394 | 55,581 | 50,309 | 62,929 |
| SENSEX | 2025-06 | `hist_volatility_snapshots` | 20 | 7,448 | 375 | 355 | 375 |
| SENSEX | 2025-06 | `volatility_snapshots` | 20 | 942 | 47 | 11 | 75 |
| SENSEX | 2025-07 | `hist_atm_option_bars_15m` | 23 | 433 | 21 | 5 | 25 |
| SENSEX | 2025-07 | `hist_atm_option_bars_5m` | 23 | 1,238 | 63 | 13 | 75 |
| SENSEX | 2025-07 | `hist_market_state` | 23 | 8,620 | 375 | 374 | 375 |
| SENSEX | 2025-07 | `hist_option_bars_1m` | 23 | 1,555,731 | 66,486 | 52,392 | 92,467 |
| SENSEX | 2025-07 | `hist_option_greeks_1m` | 18 | 896,062 | 49,926 | 44,873 | 54,143 |
| SENSEX | 2025-07 | `hist_volatility_snapshots` | 23 | 8,530 | 375 | 336 | 375 |
| SENSEX | 2025-07 | `volatility_snapshots` | 23 | 1,238 | 63 | 13 | 75 |
| SENSEX | 2025-08 | `hist_atm_option_bars_15m` | 19 | 366 | 22 | 3 | 25 |
| SENSEX | 2025-08 | `hist_atm_option_bars_5m` | 19 | 1,033 | 62 | 7 | 75 |
| SENSEX | 2025-08 | `hist_market_state` | 19 | 7,120 | 375 | 374 | 375 |
| SENSEX | 2025-08 | `hist_option_bars_1m` | 19 | 1,344,065 | 71,909 | 52,074 | 90,739 |
| SENSEX | 2025-08 | `hist_option_greeks_1m` | 15 | 745,399 | 50,790 | 43,890 | 54,495 |
| SENSEX | 2025-08 | `hist_volatility_snapshots` | 19 | 7,092 | 375 | 362 | 375 |
| SENSEX | 2025-08 | `volatility_snapshots` | 19 | 1,033 | 62 | 7 | 75 |
| SENSEX | 2025-09 | `hist_atm_option_bars_15m` | 22 | 467 | 23 | 7 | 25 |
| SENSEX | 2025-09 | `hist_atm_option_bars_5m` | 22 | 1,344 | 68 | 17 | 75 |
| SENSEX | 2025-09 | `hist_market_state` | 22 | 8,240 | 375 | 370 | 375 |
| SENSEX | 2025-09 | `hist_option_bars_1m` | 22 | 1,551,995 | 68,338 | 55,837 | 97,323 |
| SENSEX | 2025-09 | `hist_option_greeks_1m` | 18 | 880,101 | 49,465 | 43,849 | 52,768 |
| SENSEX | 2025-09 | `hist_volatility_snapshots` | 22 | 8,206 | 375 | 358 | 375 |
| SENSEX | 2025-09 | `volatility_snapshots` | 22 | 1,344 | 68 | 17 | 75 |
| SENSEX | 2025-10 | `hist_atm_option_bars_15m` | 21 | 291 | 15 | 4 | 25 |
| SENSEX | 2025-10 | `hist_atm_option_bars_5m` | 21 | 762 | 37 | 7 | 75 |
| SENSEX | 2025-10 | `hist_market_state` | 21 | 7,557 | 375 | 60 | 376 |
| SENSEX | 2025-10 | `hist_option_bars_1m` | 21 | 1,551,569 | 76,998 | 13,828 | 96,393 |
| SENSEX | 2025-10 | `hist_option_greeks_1m` | 16 | 780,514 | 50,607 | 9,265 | 56,910 |
| SENSEX | 2025-10 | `hist_volatility_snapshots` | 21 | 7,507 | 375 | 60 | 375 |
| SENSEX | 2025-10 | `volatility_snapshots` | 21 | 762 | 37 | 7 | 75 |
| SENSEX | 2025-11 | `hist_atm_option_bars_15m` | 19 | 342 | 21 | 3 | 25 |
| SENSEX | 2025-11 | `hist_atm_option_bars_5m` | 19 | 973 | 55 | 8 | 75 |
| SENSEX | 2025-11 | `hist_market_state` | 19 | 7,123 | 375 | 374 | 376 |
| SENSEX | 2025-11 | `hist_option_bars_1m` | 19 | 1,419,356 | 73,813 | 60,177 | 96,241 |
| SENSEX | 2025-11 | `hist_option_greeks_1m` | 15 | 757,688 | 50,593 | 47,354 | 54,851 |
| SENSEX | 2025-11 | `hist_volatility_snapshots` | 19 | 7,075 | 375 | 359 | 375 |
| SENSEX | 2025-11 | `volatility_snapshots` | 19 | 973 | 55 | 8 | 75 |
| SENSEX | 2025-12 | `hist_atm_option_bars_15m` | 22 | 395 | 18 | 7 | 25 |
| SENSEX | 2025-12 | `hist_atm_option_bars_5m` | 22 | 1,142 | 51 | 17 | 75 |
| SENSEX | 2025-12 | `hist_market_state` | 22 | 8,247 | 375 | 374 | 376 |
| SENSEX | 2025-12 | `hist_option_bars_1m` | 22 | 1,565,274 | 68,920 | 54,688 | 94,923 |
| SENSEX | 2025-12 | `hist_option_greeks_1m` | 18 | 866,141 | 48,019 | 43,924 | 54,010 |
| SENSEX | 2025-12 | `hist_volatility_snapshots` | 22 | 8,189 | 375 | 353 | 375 |
| SENSEX | 2025-12 | `volatility_snapshots` | 22 | 1,142 | 51 | 17 | 75 |
| SENSEX | 2026-01 | `hist_atm_option_bars_15m` | 20 | 328 | 16 | 5 | 25 |
| SENSEX | 2026-01 | `hist_atm_option_bars_5m` | 20 | 874 | 45 | 9 | 75 |
| SENSEX | 2026-01 | `hist_future_bars_1m` | 20 | 7,845 | 390 | 223 | 657 |
| SENSEX | 2026-01 | `hist_market_state` | 20 | 7,497 | 375 | 374 | 376 |
| SENSEX | 2026-01 | `hist_option_bars_1m` | 20 | 1,689,038 | 80,702 | 55,726 | 109,228 |
| SENSEX | 2026-01 | `hist_option_greeks_1m` | 15 | 827,980 | 55,696 | 42,942 | 66,061 |
| SENSEX | 2026-01 | `hist_volatility_snapshots` | 20 | 7,440 | 375 | 358 | 375 |
| SENSEX | 2026-01 | `volatility_snapshots` | 20 | 874 | 45 | 9 | 75 |
| SENSEX | 2026-02 | `hist_atm_option_bars_15m` | 20 | 351 | 21 | 4 | 25 |
| SENSEX | 2026-02 | `hist_atm_option_bars_5m` | 20 | 974 | 58 | 11 | 75 |
| SENSEX | 2026-02 | `hist_future_bars_1m` | 20 | 7,543 | 325 | 233 | 651 |
| SENSEX | 2026-02 | `hist_market_state` | 20 | 7,496 | 375 | 374 | 375 |
| SENSEX | 2026-02 | `hist_option_bars_1m` | 20 | 1,791,657 | 87,274 | 75,467 | 111,654 |
| SENSEX | 2026-02 | `hist_option_greeks_1m` | 16 | 1,015,147 | 60,853 | 57,306 | 84,677 |
| SENSEX | 2026-02 | `hist_volatility_snapshots` | 20 | 7,458 | 375 | 358 | 375 |
| SENSEX | 2026-02 | `volatility_snapshots` | 20 | 974 | 58 | 11 | 75 |
| SENSEX | 2026-03 | `hist_atm_option_bars_15m` | 19 | 267 | 15 | 2 | 25 |
| SENSEX | 2026-03 | `hist_atm_option_bars_5m` | 19 | 714 | 39 | 4 | 72 |
| SENSEX | 2026-03 | `hist_future_bars_1m` | 19 | 10,106 | 514 | 376 | 797 |
| SENSEX | 2026-03 | `hist_market_state` | 19 | 7,122 | 375 | 374 | 376 |
| SENSEX | 2026-03 | `hist_option_bars_1m` | 19 | 1,831,880 | 98,808 | 70,933 | 120,134 |
| SENSEX | 2026-03 | `hist_option_greeks_1m` | 15 | 1,084,215 | 73,824 | 61,017 | 77,864 |
| SENSEX | 2026-03 | `hist_volatility_snapshots` | 19 | 7,097 | 375 | 367 | 375 |
| SENSEX | 2026-03 | `historical_index_futures_1m` | 7 | 1,334 | 258 | 1 | 379 |
| SENSEX | 2026-03 | `historical_option_chain_snapshots` | 6 | 114,402 | 15,453 | 564 | 45,450 |
| SENSEX | 2026-03 | `market_state_snapshots` | 13 | 413 | 15 | 1 | 115 |
| SENSEX | 2026-03 | `option_execution_path_audit_v1` | 1 | 3,599 | 3,599 | 3,599 | 3,599 |
| SENSEX | 2026-03 | `option_execution_price_history` | 7 | 6,196 | 1,128 | 4 | 1,512 |
| SENSEX | 2026-03 | `option_execution_snapshots` | 1 | 59 | 59 | 59 | 59 |
| SENSEX | 2026-03 | `shadow_signal_snapshots` | 1 | 5 | 5 | 5 | 5 |
| SENSEX | 2026-03 | `shadow_signal_validation_v1` | 1 | 5 | 5 | 5 | 5 |
| SENSEX | 2026-03 | `signal_snapshots` | 7 | 73 | 11 | 2 | 24 |
| SENSEX | 2026-03 | `volatility_snapshots` | 19 | 1,002 | 47 | 18 | 133 |
| SENSEX | 2026-03 | `wcb_signal_validation_v2` | 7 | 73 | 11 | 2 | 24 |
| SENSEX | 2026-04 | `historical_option_chain_snapshots` | 19 | 688,474 | 37,050 | 22,620 | 45,730 |
| SENSEX | 2026-04 | `market_state_snapshots` | 20 | 2,033 | 97 | 53 | 151 |
| SENSEX | 2026-04 | `signal_snapshots` | 20 | 2,091 | 98 | 54 | 154 |
| SENSEX | 2026-04 | `volatility_snapshots` | 20 | 2,093 | 98 | 54 | 154 |
| SENSEX | 2026-04 | `wcb_signal_validation_v2` | 20 | 2,091 | 98 | 54 | 154 |
| SENSEX | 2026-05 | `gex_strike_snapshots` | 4 | 52,000 | 16,154 | 261 | 19,431 |
| SENSEX | 2026-05 | `hist_option_bars_1m` | 2 | 21,261 | 10,630 | 4,762 | 16,499 |
| SENSEX | 2026-05 | `historical_option_chain_snapshots` | 19 | 660,052 | 31,820 | 15,910 | 119,110 |
| SENSEX | 2026-05 | `market_state_snapshots` | 19 | 1,783 | 73 | 41 | 180 |
| SENSEX | 2026-05 | `market_state_snapshots_replay` | 1 | 70 | 70 | 70 | 70 |
| SENSEX | 2026-05 | `option_chain_snapshots_replay` | 1 | 1,650 | 1,650 | 1,650 | 1,650 |
| SENSEX | 2026-05 | `signal_snapshots` | 19 | 2,561 | 145 | 71 | 350 |
| SENSEX | 2026-05 | `signal_snapshots_replay` | 1 | 76 | 76 | 76 | 76 |
| SENSEX | 2026-05 | `volatility_snapshots` | 19 | 2,561 | 145 | 71 | 352 |
| SENSEX | 2026-05 | `volatility_snapshots_replay` | 1 | 72 | 72 | 72 | 72 |
| SENSEX | 2026-05 | `wcb_signal_validation_v2` | 19 | 2,561 | 145 | 71 | 350 |
| SENSEX | 2026-06 | `gamma_metrics` | 15 | 791 | 82 | 1 | 84 |
| SENSEX | 2026-06 | `gex_strike_snapshots` | 19 | 186,327 | 12,826 | 163 | 18,480 |
| SENSEX | 2026-06 | `historical_index_futures_1m` | 8 | 8 | 1 | 1 | 1 |
| SENSEX | 2026-06 | `historical_option_chain_snapshots` | 3 | 77,055 | 27,824 | 21,345 | 27,886 |
| SENSEX | 2026-06 | `market_state_snapshots` | 19 | 964 | 73 | 1 | 84 |
| SENSEX | 2026-06 | `signal_snapshots` | 19 | 1,333 | 82 | 1 | 147 |
| SENSEX | 2026-06 | `volatility_snapshots` | 17 | 946 | 74 | 1 | 84 |
| SENSEX | 2026-06 | `wcb_signal_validation_v2` | 19 | 1,333 | 82 | 1 | 147 |
| SENSEX | 2026-07 | `gamma_metrics` | 23 | 1,893 | 83 | 68 | 84 |
| SENSEX | 2026-07 | `gex_strike_snapshots` | 23 | 319,869 | 13,778 | 9,887 | 15,687 |
| SENSEX | 2026-07 | `historical_index_futures_1m` | 22 | 22 | 1 | 1 | 1 |
| SENSEX | 2026-07 | `market_state_snapshots` | 23 | 1,893 | 83 | 68 | 84 |
| SENSEX | 2026-07 | `signal_snapshots` | 23 | 1,917 | 84 | 68 | 86 |
| SENSEX | 2026-07 | `volatility_snapshots` | 23 | 1,893 | 83 | 68 | 84 |
| SENSEX | 2026-07 | `wcb_signal_validation_v2` | 23 | 1,917 | 84 | 68 | 86 |
| SENSEX | 2026-08 | `gamma_metrics` | 21 | 1,708 | 83 | 64 | 84 |
| SENSEX | 2026-08 | `gex_strike_snapshots` | 21 | 255,325 | 11,808 | 8,576 | 14,754 |
| SENSEX | 2026-08 | `historical_index_futures_1m` | 19 | 19 | 1 | 1 | 1 |
| SENSEX | 2026-08 | `market_state_snapshots` | 21 | 1,707 | 83 | 63 | 84 |
| SENSEX | 2026-08 | `option_chain_snapshots` | 6 | 126,348 | 29,070 | 392 | 33,712 |
| SENSEX | 2026-08 | `signal_snapshots` | 21 | 1,733 | 84 | 65 | 85 |
| SENSEX | 2026-08 | `volatility_snapshots` | 21 | 1,708 | 83 | 64 | 84 |
| SENSEX | 2026-08 | `wcb_signal_validation_v2` | 21 | 1,733 | 84 | 65 | 85 |
| SENSEX | 2026-09 | `gamma_metrics` | 9 | 741 | 83 | 80 | 84 |
| SENSEX | 2026-09 | `gex_strike_snapshots` | 9 | 100,124 | 11,016 | 10,530 | 12,280 |
| SENSEX | 2026-09 | `historical_index_futures_1m` | 9 | 9 | 1 | 1 | 1 |
| SENSEX | 2026-09 | `latest_option_chain_run` | 1 | 1 | 1 | 1 | 1 |
| SENSEX | 2026-09 | `latest_option_chain_snapshots` | 1 | 366 | 366 | 366 | 366 |
| SENSEX | 2026-09 | `latest_signal_snapshots` | 1 | 1 | 1 | 1 | 1 |
| SENSEX | 2026-09 | `market_state_snapshots` | 9 | 741 | 83 | 80 | 84 |
| SENSEX | 2026-09 | `option_chain_snapshots` | 9 | 267,796 | 29,240 | 28,900 | 31,476 |
| SENSEX | 2026-09 | `signal_snapshots` | 9 | 754 | 84 | 82 | 85 |
| SENSEX | 2026-09 | `volatility_snapshots` | 9 | 741 | 83 | 80 | 84 |
| SENSEX | 2026-09 | `wcb_signal_validation_v2` | 9 | 754 | 84 | 82 | 85 |

**Read the `min` column.** A month whose median is a full chain but whose
minimum is single digits contains a day that is present-but-hollow. Those
days pass every presence test in §6 and will not support a GEX.

## 7–9. Deliberately not measured by this register

Three sweeps that earlier drafts of this script ran are **not** run, and their
absence is a scoping decision, not an omission.

| question | why not here | where it was answered |
|---|---|---|
| **§7** Which rows came from a producer other than the primary ingest? | 36 `(relation, column)` pairs at ~13 min each — **over seven hours**. The three that completed were `eq_macro_data`, `eq_price_daily` and `eq_price_daily_backup_20260618`: equity tables and a dated backup, none of which this register makes a claim about. | Directly, per relation, when a specific producer question arises. |
| **§8** Which declared columns are never written? | Probes every column of every candidate relation; schema hygiene, not data extent. | S62 established `hist_gamma_metrics.gamma_concentration` was the single empty column by direct query. |
| **§9** Does a single-expiry relation silently change expiry class? | Row enumeration under a 200k cap; an instrument-identity question, not an availability one. | S33 measured the NSE/BSE weekday swap directly from `hist_atm_option_bars_5m.expiry_date`. |

Each is a real question with a real answer, and each was answered this session
by a handful of direct queries in minutes. **They are not this question.** If
they are wanted continuously they get their own script, on their own cadence.

The functions remain in the file, unreferenced, so that script can lift them
rather than rewrite them: `sweep_provenance()`, `sweep_never_written()`,
`sweep_expiry_class()`.

> **Why this matters more than the three sweeps did.** A register that
> regenerates in under an hour gets re-run. One that takes eight hours never
> does — and then the extent question gets re-derived from scratch by the next
> session that needs it, which is the exact failure this file was built to
> end. Scope is what keeps it runnable.

## 10. Unresolved probes

**None.** Every probe in this run resolved to a value or to a real empty
list. The script asserts this before writing and refuses to write otherwise.

## 11. What this method could NOT measure

No proxy is substituted for any of these. They are absent, not estimated.

| item | why | what was done instead |
|---|---|---|
| `pg_total_relation_size` per relation | needs SQL against `pg_class`/`pg_namespace`; PostgREST exposes only `public` tables, no RPC wraps it, and there is no psql or DB password | omitted; no size figure appears in this register |
| tables vs views | the OpenAPI document renders both identically and the catalog view that separates them is unreachable | §2 says "relations" throughout and never claims a relation is a table |
| exact row counts on the largest relations | `count=exact` exceeds the statement timeout on multi-million-row relations | presence/absence measured per-day, where exact answers are available; no planned figure is reported |
| distinct strike counts | PostgREST has no `DISTINCT`, and materialising a month of strikes from a 54.8M-row relation is not viable through it | absent rather than estimated |
| whether a weekday with no `hist_spot_bars_1m` row is a market holiday or a data gap | the denominator is defined by the presence of spot bars and cannot distinguish the two | such days are excluded from the denominator entirely, so they inflate neither the numerator nor the total |
| whether a relation's rows are *correct* | this register measures presence and non-nullness only | nothing here should be read as a statement about accuracy |
| implied volatility on the ATM bar relations | `hist_atm_option_bars_5m` and `_15m` carry OHLC-shaped IV (`ce_iv_open/high/low/close`), which `RE_IV`'s terminal anchor does not match — a bar-aggregate IV is not the point-in-time IV the other relations hold | those relations report **no iv layer**. This is a scoping decision, stated here rather than left as an unexplained blank; their gamma, OI and spot are measured normally |
| vendor greeks, 2025-04 → 2026-03 | **RESOLVED 2026-09-14, do not re-derive** — the chain was purchased from **GFDL** (Global Financial Datafeeds); delivery schema is nine columns (`Ticker, Date, Time, Open, High, Low, Close, Volume, Open Interest`) measured uniform across all 175,304 rows of `GFDLNFO_BACKADJUSTED_01042025.csv`. No IV and no greeks were delivered | `hist_option_bars_1m` greek columns are declared and never written (S75, 289 weekdays; S78 re-verified all six plus five Heston params). `hist_option_greeks_1m` iv and gamma are MERDIAN-solved via `backfill_hist_greeks.py` at a chosen `r_used`, not vendor-supplied. `delta`/`theta`/`vega` for that era do not exist and cannot be recovered from this vendor. Closes **TD-S35-NEW-2**; confirms **TD-S58-NEW-1** from the file side |
| the vendor file's location | the CSV is **not** on the AWS box — `find /home/ssm-user -iname 'GFDL*'` returns nothing. It reached S78 via chat upload from the operator's local machine | the schema above is established from the file and cannot be re-verified from AWS. Record where the raw delivery lives before the next session needs it |
| supersession | `docs/research/data_inventory_2026-09-08.md` (S75) and `iv_availability_2026-09-08.md` (S75) are superseded by this register, which regenerates | both remain in git; both come out of the project-knowledge upload set (S78) |

---

*Generated by `scripts/build_data_inventory.py` on 2026-09-14. 26,172 requests, 6,139 empty-list confirmations, 0 unresolved.*
