# MERDIAN data inventory — historical GEX feasibility

**Date measured:** 2026-09-08  ·  **Scope:** every relation exposed in Supabase schema `public`
**Question:** for which calendar months can a per-strike GEX be computed for NIFTY and for SENSEX,
and from which tables.

Every number below is followed by the query that produced it. Nothing here is taken from
`merdian_reference.json`, from any register, or from a table name.

---

## 0. Measurement method, and what it could not measure

### The access path

This box has no `psql` binary, no `psycopg2`/`psycopg`/`asyncpg`/`pg8000`/`sqlalchemy`, and
no Postgres password. `.env` holds exactly two connection keys — `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` — so the only route to the database is PostgREST as the
service role.

```
$ command -v psql            -> absent
$ python3 -c 'import psycopg2'  -> ModuleNotFoundError  (same for psycopg, asyncpg,
                                    pg8000, sqlalchemy)
dotenv key scan of .env, names only:  SUPABASE_URL (len 40), SUPABASE_SERVICE_ROLE_KEY (len 219)
```

PostgREST exposes no arbitrary-SQL RPC. The 38 RPCs it does publish were enumerated from
the OpenAPI document (`GET /rest/v1/`) and none of them executes caller-supplied SQL:

```
get_active_nse_universe_batch, get_active_nse_universe_json, get_hocs_distinct_expiries,
get_parameter_bool/num/text, get_vix_context_regime, get_vix_level_bucket,
get_vix_percentile, get_vix_regime, hist_bars_eligible_for_aging, cleanup_gamma_engine_data,
insert_option_chain_batch, insert_option_chain_run, compute_atm_straddle_for_run,
compute_breadth_regime, compute_expansion_probability, compute_flip_level_v2/v3,
compute_gamma_flip_for_run, compute_gamma_metrics_for_run, compute_options_regime,
compute_signal_v1/v2, compute_straddle_slope_for_run, update_parameter, trigger_ingest,
trigger_ingest_nifty, trigger_ingest_sensex, is_breadth_contaminated,
build_breadth_indicators_daily, build_market_breadth_daily/intraday/intraday_backup/latest,
swap_dhan_scripmaster, get_distinct_symbols, get_symbol_population
```

### What this blocks

Two things the task asked for cannot be measured on this access path, and I did not
substitute a guess for either:

| Asked for | Status |
|---|---|
| `pg_total_relation_size` per table | **Not measurable.** Needs SQL against `pg_class`/`pg_namespace`; PostgREST exposes only the `public` schema's tables, not the catalog. No RPC wraps it. Step 1 is therefore ordered by row estimate, not by size. |
| `pg_class.reltuples` read directly | **Not measurable directly.** Substituted with PostgREST `Prefer: count=planned`, which returns the planner's row estimate for the query — for an unfiltered `select=*` that estimate is derived from `pg_class.reltuples`. Labelled `planned` everywhere below. |

Neither substitution is silent: every count in this document carries its method.

### exact vs planned

`count=exact` runs a real `COUNT(*)` and is the trustworthy number. It survives on most
tables and dies on the largest one:

```
GET /hist_option_bars_1m?select=*&limit=0   Prefer: count=planned  -> 206  */54815936   0.44s
GET /hist_option_bars_1m?select=*&limit=0   Prefer: count=exact    -> 500 (timeout)     8.44s
GET /gex_strike_snapshots?select=*&limit=0  Prefer: count=planned  -> 206  */1398101    0.45s
GET /gex_strike_snapshots?select=*&limit=0  Prefer: count=exact    -> 206  */1427348    0.56s
```

So the per-month measurement in Step 3 attempts `count=exact` first and falls back to
`count=planned` only when exact exceeds the statement timeout. **Each cell states which
one produced it.** A `planned` figure is a planner estimate and can be wrong by a wide
margin on a filtered range; an `exact` figure is a real count.

---

## 1. Every relation in schema `public`

**222 relations** (tables and views — PostgREST does not distinguish them in its
OpenAPI document, and the catalog view that would is not reachable).

Row figures are `Prefer: count=planned` on `GET /rest/v1/<relation>?select=*&limit=0`,
one request per relation, run 2026-09-08. Ordered by estimate descending, **not** by
`pg_total_relation_size`, which is not measurable here.

| # | relation | planned rows | cols |
|---:|---|---:|---:|
| 1 | `hist_option_bars_1m` | 54,815,936 | 26 |
| 2 | `hist_option_greeks_1m` | 19,251,048 | 12 |
| 3 | `eq_price_daily` | 3,774,314 | 14 |
| 4 | `eq_price_daily_backup_20260618` | 3,723,551 | 14 |
| 5 | `eq_feature_store` | 3,685,146 | 24 |
| 6 | `eq_price_daily_v2` | 3,248,277 | 14 |
| 7 | `historical_option_chain_snapshots` | 3,200,434 | 23 |
| 8 | `eq_signal_snapshots` | 1,526,610 | 32 |
| 9 | `gex_strike_snapshots` | 1,398,101 | 14 |
| 10 | `latest_signal` | 1,013,000 | 16 |
| 11 | `latest_signal_intraday` | 1,013,000 | 16 |
| 12 | `latest_signal_v2` | 1,013,000 | 15 |
| 13 | `option_chain_snapshots` | 699,265 | 21 |
| 14 | `equity_eod` | 366,168 | 8 |
| 15 | `hist_future_bars_1m` | 304,937 | 15 |
| 16 | `hist_spot_bars_1m` | 269,501 | 10 |
| 17 | `script_execution_log` | 227,591 | 18 |
| 18 | `dhan_scripmaster` | 195,933 | 29 |
| 19 | `dhan_scripmaster_staging` | 195,933 | 29 |
| 20 | `hist_gamma_metrics` | 183,872 | 16 |
| 21 | `hist_market_state` | 181,848 | 21 |
| 22 | `hist_volatility_snapshots` | 181,115 | 28 |
| 23 | `hist_basis_context` | 122,012 | 15 |
| 24 | `breadth_indicators_daily` | 77,781 | 20 |
| 25 | `market_spot_snapshots` | 77,156 | 8 |
| 26 | `hist_ingest_rejects` | 50,336 | 8 |
| 27 | `volatility_snapshots` | 49,773 | 36 |
| 28 | `study_path` | 47,787 | 4 |
| 29 | `hist_spot_bars_5m` | 46,067 | 11 |
| 30 | `latest_signal_v1` | 45,000 | 13 |
| 31 | `latest_signal_v1_gated` | 45,000 | 17 |
| 32 | `hist_ict_htf_zones` | 40,664 | 13 |
| 33 | `breadth_intraday_history` | 32,312 | 10 |
| 34 | `hist_atm_option_bars_5m` | 27,016 | 53 |
| 35 | `vol_analytics` | 24,765 | 10 |
| 36 | `market_breadth_intraday` | 22,722 | 14 |
| 37 | `signal_snapshots` | 20,867 | 53 |
| 38 | `wcb_signal_validation_v1` | 20,867 | 40 |
| 39 | `wcb_signal_validation_v2` | 20,867 | 43 |
| 40 | `index_futures_snapshots` | 20,737 | 13 |
| 41 | `momentum_snapshots` | 20,714 | 17 |
| 42 | `ict_primitive_outcomes` | 19,662 | 38 |
| 43 | `ict_primitives` | 19,432 | 16 |
| 44 | `_s36_outcomes_pre_truncate` | 19,410 | 38 |
| 45 | `market_state_snapshots` | 18,500 | 18 |
| 46 | `options_flow_snapshots` | 16,477 | 15 |
| 47 | `hist_spot_bars_15m` | 15,971 | 11 |
| 48 | `eq_watchlist` | 14,684 | 16 |
| 49 | `dhan_nse_equity_norm` | 14,386 | 14 |
| 50 | `weighted_constituent_breadth_snapshots` | 12,663 | 20 |
| 51 | `option_execution_price_history` | 12,392 | 11 |
| 52 | `shadow_signal_snapshots_v3` | 12,038 | 29 |
| 53 | `v_oi_prev_close_snapshots` | 10,560 | 6 |
| 54 | `hist_atm_option_bars_15m` | 9,601 | 53 |
| 55 | `gamma_metrics` | 9,050 | 27 |
| 56 | `structural_divergence_snapshots` | 8,444 | 24 |
| 57 | `smdm_snapshots` | 7,781 | 14 |
| 58 | `hist_pattern_signals` | 7,583 | 27 |
| 59 | `option_execution_path_audit_v1` | 7,259 | 21 |
| 60 | `momentum_snapshots_v2` | 6,433 | 12 |
| 61 | `basis_context_snapshots` | 6,315 | 12 |
| 62 | `structural_alerts` | 5,668 | 28 |
| 63 | `signal_market_path_audit_v1` | 5,551 | 26 |
| 64 | `bse_t1_securities` | 5,218 | 3 |
| 65 | `breadth_equity_indicators` | 4,500 | 22 |
| 66 | `latest_option_chain_run` | 3,496 | 21 |
| 67 | `latest_option_chain_snapshots` | 3,477 | 21 |
| 68 | `option_chain_snapshots_replay` | 3,300 | 21 |
| 69 | `intraday_ohlc` | 2,854 | 13 |
| 70 | `eq_fundamental_snapshots` | 2,833 | 35 |
| 71 | `eq_stock_sector_map` | 2,833 | 4 |
| 72 | `historical_index_futures_1m` | 2,748 | 13 |
| 73 | `historical_market_spot_1m` | 2,748 | 8 |
| 74 | `eq_instruments` | 2,132 | 20 |
| 75 | `gamma_metrics_shadow` | 1,952 | 25 |
| 76 | `study_null_pair` | 1,896 | 3 |
| 77 | `india_vix_history` | 1,782 | 4 |
| 78 | `raw_ingest_log` | 1,520 | 7 |
| 79 | `participant_oi_daily` | 1,515 | 20 |
| 80 | `breadth_universe_members` | 1,495 | 14 |
| 81 | `dhan_scrip_map` | 1,495 | 8 |
| 82 | `hist_completeness_checks` | 1,480 | 10 |
| 83 | `nse_dhan_bridge` | 1,385 | 9 |
| 84 | `equity_intraday_last` | 1,385 | 4 |
| 85 | `ict_htf_zones` | 1,279 | 16 |
| 86 | `script_execution_log_replay` | 1,120 | 18 |
| 87 | `latest_signal_inputs_v2` | 1,013 | 21 |
| 88 | `signal_state_snapshots` | 856 | 22 |
| 89 | `shadow_state_signal_snapshots` | 844 | 19 |
| 90 | `shadow_state_signal_outcomes` | 844 | 31 |
| 91 | `hist_ingest_log` | 742 | 18 |
| 92 | `signal_regret_log` | 614 | 20 |
| 93 | `hist_greeks_backfill_log` | 492 | 9 |
| 94 | `ict_zones` | 486 | 31 |
| 95 | `latest_atm_neighborhood` | 407 | 10 |
| 96 | `latest_net_gamma_by_strike` | 407 | 9 |
| 97 | `study_accel_stat` | 390 | 8 |
| 98 | `dhan_token_probe_log` | 375 | 13 |
| 99 | `equity_eod_norm` | 245 | 7 |
| 100 | `market_spot_session_markers` | 236 | 18 |
| 101 | `trading_calendar` | 218 | 10 |
| 102 | `market_environment_snapshots` | 158 | 26 |
| 103 | `signal_snapshots_replay` | 152 | 50 |
| 104 | `equity_eod_shadow_audit` | 150 | 20 |
| 105 | `market_spot_snapshots_replay` | 150 | 8 |
| 106 | `options_flow_snapshots_replay` | 150 | 15 |
| 107 | `market_breadth_daily_nse` | 150 | 17 |
| 108 | `volatility_snapshots_replay` | 147 | 36 |
| 109 | `gamma_metrics_replay` | 144 | 25 |
| 110 | `market_state_snapshots_replay` | 144 | 18 |
| 111 | `study_recon_accel` | 141 | 8 |
| 112 | `study_recon_pin` | 141 | 8 |
| 113 | `study_runs_m` | 141 | 4 |
| 114 | `study_step_m` | 141 | 4 |
| 115 | `shadow_reconstruction_v3` | 138 | 40 |
| 116 | `eq_ingestion_log` | 137 | 11 |
| 117 | `momentum_snapshots_replay` | 135 | 17 |
| 118 | `study_eligible` | 134 | 4 |
| 119 | `study_zone_ref` | 134 | 9 |
| 120 | `study_real_pair` | 132 | 3 |
| 121 | `eq_trading_calendar` | 121 | 5 |
| 122 | `signal_outcome_audit_v2` | 121 | 33 |
| 123 | `study_pin_stat` | 121 | 8 |
| 124 | `option_execution_snapshots` | 119 | 13 |
| 125 | `signal_regret_log_v1` | 119 | 57 |
| 126 | `iv_context_snapshots` | 106 | 15 |
| 127 | `eq_market_gate` | 97 | 10 |
| 128 | `shadow_reconstruction_v1` | 87 | 33 |
| 129 | `bse_scripcode_isin_map` | 80 | 4 |
| 130 | `index_constituent_weights` | 80 | 11 |
| 131 | `v_wcb_active_weights` | 80 | 8 |
| 132 | `expiry_outcomes` | 77 | 20 |
| 133 | `signal_outcomes` | 73 | 51 |
| 134 | `shadow_reconstruction_v2` | 69 | 37 |
| 135 | `market_breadth_daily` | 61 | 19 |
| 136 | `bom_dhan_bridge` | 59 | 8 |
| 137 | `po3_session_state` | 56 | 15 |
| 138 | `nifty_cycle_base` | 55 | 8 |
| 139 | `nifty_move_anchor` | 55 | 8 |
| 140 | `signal_outcome_audit` | 48 | 26 |
| 141 | `latest_gamma_metrics` | 45 | 17 |
| 142 | `latest_gamma_metrics_v2` | 45 | 18 |
| 143 | `latest_signal_inputs` | 45 | 20 |
| 144 | `fii_dii_cash_daily` | 33 | 11 |
| 145 | `signal_labels` | 24 | 16 |
| 146 | `data_quality_events` | 23 | 12 |
| 147 | `signal_market_outcome_audit_v1` | 17 | 44 |
| 148 | `v_script_execution_health_30m` | 16 | 8 |
| 149 | `latest_top_gamma_strikes` | 15 | 9 |
| 150 | `eq_macro_data` | 13 | 6 |
| 151 | `merdian_parameters` | 13 | 16 |
| 152 | `system_config` | 13 | 9 |
| 153 | `v_merdian_parameter_audit` | 13 | 11 |
| 154 | `ict_zones_replay` | 12 | 31 |
| 155 | `v_gex_strike_accel_zone` | 11 | 11 |
| 156 | `v_gex_strike_pin_zone` | 11 | 11 |
| 157 | `shadow_signal_outcomes` | 10 | 65 |
| 158 | `shadow_signal_snapshots` | 10 | 35 |
| 159 | `shadow_signal_validation_v1` | 10 | 37 |
| 160 | `eq_paper_trades` | 10 | 13 |
| 161 | `latest_gamma_walls` | 6 | 10 |
| 162 | `v_dealer_flow_sim` | 6 | 11 |
| 163 | `v_expiry_base_rates` | 6 | 10 |
| 164 | `shadow_outcomes_v1` | 4 | 21 |
| 165 | `shadow_outcomes_v2` | 4 | 27 |
| 166 | `shadow_replay_v1` | 4 | 28 |
| 167 | `dhan_auth_tokens` | 4 | 4 |
| 168 | `signal_regret_analytics_v1` | 4 | 29 |
| 169 | `signal_regret_analytics_v2` | 4 | 32 |
| 170 | `signal_runs` | 3 | 12 |
| 171 | `aging_policy` | 3 | 7 |
| 172 | `latest_signal_snapshots` | 2 | 38 |
| 173 | `instruments` | 2 | 12 |
| 174 | `capital_tracker` | 2 | 3 |
| 175 | `underlyings` | 2 | 3 |
| 176 | `v_wcb_weight_totals` | 2 | 3 |
| 177 | `option_atm_snapshots` | 1 | 10 |
| 178 | `signal_premium_outcomes` | 1 | 80 |
| 179 | `signal_snapshots_shadow` | 1 | 42 |
| 180 | `exit_alerts` | 1 | 10 |
| 181 | `market_ticks` | 1 | 19 |
| 182 | `option_execution_outcomes_v1` | 1 | 27 |
| 183 | `signal_regret_log_v1_latest` | 1 | 58 |
| 184 | `trade_log` | 1 | 18 |
| 185 | `v_max_pain_by_strike` | 1 | 5 |
| 186 | `active_breadth_universe_members_nse` | 1 | 4 |
| 187 | `active_breadth_universe_nse` | 1 | 6 |
| 188 | `breadth_universe_nse_only` | 1 | 12 |
| 189 | `dhan_symbol_alias` | 1 | 4 |
| 190 | `hist_iv_surface_daily` | 1 | 18 |
| 191 | `market_state_snapshots_shadow` | 1 | 18 |
| 192 | `measurement_health_snapshots` | 1 | 13 |
| 193 | `shadow_vs_live_evaluation` | 1 | 15 |
| 194 | `signal_outcome_audit_dedup` | 1 | 27 |
| 195 | `signal_outcome_research_v1` | 1 | 29 |
| 196 | `signal_outcome_research_v2` | 1 | 32 |
| 197 | `structural_divergence_snapshots_replay` | 1 | 24 |
| 198 | `vol_analytics_shadow` | 1 | 10 |
| 199 | `_active_universe_choice` | 1 | 2 |
| 200 | `_equity_eod_detected` | 1 | 10 |
| 201 | `active_breadth_universe` | 1 | 1 |
| 202 | `app_settings` | 1 | 3 |
| 203 | `breadth_coverage_latest` | 1 | 4 |
| 204 | `breadth_ingest_state` | 1 | 7 |
| 205 | `breadth_universe_sets` | 1 | 5 |
| 206 | `breadth_universe_snapshot` | 1 | 3 |
| 207 | `dashboard_last_updated` | 1 | 1 |
| 208 | `data_contamination_ranges` | 1 | 11 |
| 209 | `eq_corporate_actions` | 1 | 13 |
| 210 | `eq_instrument_events` | 1 | 9 |
| 211 | `india_vix_daily` | 1 | 2 |
| 212 | `latest_market_breadth` | 1 | 19 |
| 213 | `latest_market_breadth_intraday` | 1 | 14 |
| 214 | `latest_market_breadth_nse` | 1 | 17 |
| 215 | `latest_run_id` | 1 | 1 |
| 216 | `model_registry` | 1 | 11 |
| 217 | `momentum_snapshots_shadow` | 1 | 17 |
| 218 | `option_outcome_analytics_v1` | 1 | 19 |
| 219 | `signal_outcome_audit_v2_intraday_clean` | 1 | 38 |
| 220 | `v_dhan_token_probe_today` | 1 | 12 |
| 221 | `v_participant_oi_latest` | 1 | 3 |
| 222 | `vix_percentile_reference` | 1 | 3 |

---

## 2. Candidates — which relations hold a GEX input

A per-strike GEX needs, per strike per timestamp: **gamma**, **open interest**, **strike**,
**option_type**, **spot**, and a **symbol** identifier. Membership below was decided by
reading each relation's column list out of the PostgREST OpenAPI definitions (generated from
the live catalog), never from the relation's name.

`iv` is tracked as a seventh column because gamma is recoverable from it by Black-Scholes,
which Step 6 needs in order to separate COMPUTABLE NOW from COMPUTABLE AFTER DERIVATION.

Tiers:

- **A — per-strike + greek**: carries a strike/option_type dimension *and* gamma or iv.
- **B — per-strike chain**: carries strike/option_type/OI but no greek.
- **C — spot or scalar**: carries spot, or an aggregate gamma with no strike dimension.
- **D — no GEX input**: none of the seven columns. Listed as a count only.

A relation qualifying on `symbol` alone is **not** a candidate: a symbol identifies a row
but supplies no GEX quantity. That exclusion is stated rather than applied silently.

### Tier A — per-strike, with gamma or iv  (28 relations)

| relation | planned rows | GEX columns present | time columns |
|---|---:|---|---|
| `hist_option_bars_1m` | 54,815,936 | **expiry**=`expiry_date`; **gamma**=`gamma`; **instrument_id**=`instrument_id`; **iv**=`iv`; **oi**=`oi`; **option_type**=`option_type`; **premium**=`close`; **strike**=`strike` | `bar_ts`, `expiry_date`, `trade_date` |
| `hist_option_greeks_1m` | 19,251,048 | **expiry**=`expiry_date`; **gamma**=`gamma`; **instrument_id**=`instrument_id`; **iv**=`iv`; **option_type**=`option_type`; **strike**=`strike` | `bar_ts`, `created_at`, `expiry_date`, `trade_date` |
| `historical_option_chain_snapshots` | 3,200,434 | **expiry**=`expiry_date`; **gamma**=`gamma`; **iv**=`iv`; **oi**=`oi,oi_change`; **option_type**=`option_type`; **premium**=`ask,bid,ltp`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `gex_strike_snapshots` | 1,398,101 | **expiry**=`expiry_date`; **gamma**=`gamma_call,gamma_put`; **oi**=`oi_call,oi_put`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `option_chain_snapshots` | 699,265 | **expiry**=`expiry_date`; **gamma**=`gamma`; **iv**=`iv`; **oi**=`oi,oi_change`; **option_type**=`option_type`; **premium**=`ask,bid,ltp`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `hist_volatility_snapshots` | 181,115 | **expiry**=`expiry_date,expiry_type`; **instrument_id**=`instrument_id`; **iv**=`atm_call_iv,atm_iv,atm_put_iv,iv_regime,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `bar_ts`, `created_at`, `expiry_date`, `trade_date` |
| `volatility_snapshots` | 49,773 | **expiry**=`expiry_date,expiry_type`; **iv**=`atm_call_iv,atm_put_iv,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `hist_atm_option_bars_5m` | 27,016 | **expiry**=`expiry_date`; **gamma**=`ce_gamma,pe_gamma`; **instrument_id**=`instrument_id`; **oi**=`ce_oi,pe_oi`; **spot**=`spot_close,spot_high,spot_low,spot_open`; **strike**=`atm_strike`; **symbol**=`symbol` | `bar_ts`, `created_at`, `expiry_date`, `trade_date` |
| `signal_snapshots` | 20,867 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_concentration,gamma_regime`; **iv**=`atm_call_iv,atm_put_iv,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `option_execution_price_history` | 12,392 | **expiry**=`expiry_date`; **iv**=`iv`; **option_type**=`option_type`; **premium**=`ltp`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `hist_atm_option_bars_15m` | 9,601 | **expiry**=`expiry_date`; **gamma**=`ce_gamma,pe_gamma`; **instrument_id**=`instrument_id`; **oi**=`ce_oi,pe_oi`; **spot**=`spot_close,spot_high,spot_low,spot_open`; **strike**=`atm_strike`; **symbol**=`symbol` | `bar_ts`, `created_at`, `expiry_date`, `trade_date` |
| `gamma_metrics` | 9,050 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_zone`; **spot**=`spot,spot_vs_range`; **strike**=`max_gamma_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `option_execution_path_audit_v1` | 7,259 | **iv**=`ce_iv,pe_iv`; **spot**=`spot`; **strike**=`ce_strike,pe_strike`; **symbol**=`symbol` | `chain_ts`, `created_at`, `path_ts`, `signal_ts` |
| `structural_alerts` | 5,668 | **gamma**=`cond_short_gamma,gamma_pinning`; **strike**=`gap_target_strike`; **symbol**=`symbol` | `created_at`, `ts` |
| `latest_option_chain_run` | 3,496 | **expiry**=`expiry_date`; **gamma**=`gamma`; **iv**=`iv`; **oi**=`oi,oi_change`; **option_type**=`option_type`; **premium**=`ask,bid,ltp`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `latest_option_chain_snapshots` | 3,477 | **expiry**=`expiry_date`; **gamma**=`gamma`; **iv**=`iv`; **oi**=`oi,oi_change`; **option_type**=`option_type`; **premium**=`ask,bid,ltp`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `option_chain_snapshots_replay` | 3,300 | **expiry**=`expiry_date`; **gamma**=`gamma`; **iv**=`iv`; **oi**=`oi,oi_change`; **option_type**=`option_type`; **premium**=`ask,bid,ltp`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `latest_atm_neighborhood` | 407 | **expiry**=`expiry_date`; **gamma**=`abs_net_gamma,gamma_call,gamma_put,net_gamma`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `expiry_date` |
| `latest_net_gamma_by_strike` | 407 | **expiry**=`expiry_date`; **gamma**=`abs_net_gamma,gamma_call,gamma_put,net_gamma`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `expiry_date` |
| `signal_snapshots_replay` | 152 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_concentration,gamma_regime`; **iv**=`atm_call_iv,atm_put_iv,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `volatility_snapshots_replay` | 147 | **expiry**=`expiry_date,expiry_type`; **iv**=`atm_call_iv,atm_put_iv,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `option_execution_snapshots` | 119 | **iv**=`ce_iv,pe_iv`; **spot**=`spot`; **strike**=`ce_strike,pe_strike`; **symbol**=`symbol` | `chain_ts`, `created_at`, `signal_ts` |
| `latest_top_gamma_strikes` | 15 | **expiry**=`expiry_date`; **gamma**=`abs_net_gamma,gamma_call,gamma_put,net_gamma`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `expiry_date` |
| `latest_gamma_walls` | 6 | **expiry**=`expiry_date`; **gamma**=`abs_net_gamma,gamma_call,gamma_put,net_gamma`; **spot**=`spot`; **strike**=`strike`; **symbol**=`symbol` | `expiry_date` |
| `latest_signal_snapshots` | 2 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_concentration,gamma_regime`; **iv**=`atm_call_iv,atm_put_iv,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `option_atm_snapshots` | 1 | **iv**=`ce_iv,pe_iv`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `signal_ts` |
| `signal_premium_outcomes` | 1 | **expiry**=`expiry_date,premium_expiry`; **gamma**=`gamma_regime`; **iv**=`entry_iv,iv_at_exit,iv_change_during_trade,iv_crushed`; **option_type**=`option_type`; **spot**=`spot_move_15m_pts,spot_move_60m_pts`; **strike**=`entry_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `signal_ts`, `updated_at` |
| `signal_snapshots_shadow` | 1 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_concentration,gamma_regime`; **iv**=`atm_call_iv,atm_put_iv,iv_skew`; **spot**=`spot`; **strike**=`atm_strike`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |

### Tier B — per-strike, no greek  (20 relations)

| relation | planned rows | GEX columns present | time columns |
|---|---:|---|---|
| `hist_future_bars_1m` | 304,937 | **expiry**=`expiry_date`; **instrument_id**=`instrument_id`; **oi**=`oi`; **premium**=`close` | `bar_ts`, `expiry_date`, `trade_date` |
| `v_oi_prev_close_snapshots` | 10,560 | **expiry**=`expiry_date`; **oi**=`prev_close_oi`; **option_type**=`option_type`; **strike**=`strike`; **symbol**=`symbol` | `expiry_date`, `prev_close_ts` |
| `historical_index_futures_1m` | 2,748 | **expiry**=`expiry_date`; **instrument_id**=`security_id`; **oi**=`open_interest`; **premium**=`ltp`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `ict_zones` | 486 | **option_type**=`opt_type`; **spot**=`spot_at_detection`; **symbol**=`symbol` | `broken_at_ts`, `created_at`, `detected_at_ts`, `last_tested_at`, `session_bar_ts`, `trade_date` |
| `market_environment_snapshots` | 158 | **expiry**=`front_expiry`; **strike**=`max_gamma_strike_drift_5d`; **symbol**=`symbol` | `as_of_date`, `created_at`, `for_session_date` |
| `study_recon_accel` | 141 | **expiry**=`expiry_date`; **strike**=`n_strikes`; **symbol**=`symbol` | `expiry_date`, `ts` |
| `study_recon_pin` | 141 | **expiry**=`expiry_date`; **strike**=`n_strikes`; **symbol**=`symbol` | `expiry_date`, `ts` |
| `signal_regret_log_v1` | 119 | **expiry**=`ce_expiry_date,pe_expiry_date`; **spot**=`spot_15m,spot_30m,spot_60m,spot_move_15m,spot_move_15m_pct,spot_move_30m,spot_move_30m_pct,spot_move_60m,spot_move_60m_pct`; **strike**=`ce_strike,pe_strike`; **symbol**=`symbol` | `ce_expiry_date`, `created_at`, `pe_expiry_date`, `signal_ts` |
| `expiry_outcomes` | 77 | **expiry**=`expiry_date,expiry_type`; **strike**=`open_pin_strike`; **symbol**=`symbol` | `created_at`, `expiry_date` |
| `nifty_cycle_base` | 55 | **strike**=`atm_strike` | — |
| `ict_zones_replay` | 12 | **option_type**=`opt_type`; **spot**=`spot_at_detection`; **symbol**=`symbol` | `broken_at_ts`, `created_at`, `detected_at_ts`, `last_tested_at`, `session_bar_ts`, `trade_date` |
| `v_gex_strike_accel_zone` | 11 | **expiry**=`expiry_date`; **strike**=`n_strikes,trough_strike`; **symbol**=`symbol` | `expiry_date`, `ts` |
| `v_gex_strike_pin_zone` | 11 | **expiry**=`expiry_date`; **strike**=`n_strikes,peak_pin_strike`; **symbol**=`symbol` | `expiry_date`, `ts` |
| `instruments` | 2 | **expiry**=`weekly_expiry_dow`; **strike**=`strike_step`; **symbol**=`symbol` | `updated_at` |
| `exit_alerts` | 1 | **option_type**=`option_type`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `exit_ts`, `fired_at` |
| `market_ticks` | 1 | **expiry**=`expiry_date`; **instrument_id**=`instrument_token`; **oi**=`oi_day_high,oi_day_low,open_interest`; **premium**=`last_price`; **strike**=`strike`; **symbol**=`symbol,tradingsymbol` | `created_at`, `expiry_date`, `ts` |
| `option_execution_outcomes_v1` | 1 | **expiry**=`entry_expiry_date`; **strike**=`entry_strike`; **symbol**=`symbol` | `created_at`, `entry_expiry_date`, `signal_ts` |
| `signal_regret_log_v1_latest` | 1 | **expiry**=`ce_expiry_date,pe_expiry_date`; **spot**=`spot_15m,spot_30m,spot_60m,spot_move_15m,spot_move_15m_pct,spot_move_30m,spot_move_30m_pct,spot_move_60m,spot_move_60m_pct`; **strike**=`ce_strike,pe_strike`; **symbol**=`symbol` | `ce_expiry_date`, `created_at`, `pe_expiry_date`, `signal_ts` |
| `trade_log` | 1 | **expiry**=`expiry_date`; **option_type**=`option_type`; **strike**=`strike`; **symbol**=`symbol` | `created_at`, `entry_ts`, `exit_ts`, `expiry_date`, `signal_ts` |
| `v_max_pain_by_strike` | 1 | **strike**=`candidate_strike,max_pain_strike`; **symbol**=`symbol` | — |

### Tier C — spot, or gamma without a strike dimension  (76 relations)

| relation | planned rows | GEX columns present | time columns |
|---|---:|---|---|
| `latest_signal` | 1,013,000 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `breadth_ts`, `expiry_date`, `metrics_ts` |
| `latest_signal_intraday` | 1,013,000 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `breadth_ts`, `expiry_date`, `metrics_ts` |
| `latest_signal_v2` | 1,013,000 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `expiry_date`, `metrics_ts` |
| `hist_spot_bars_1m` | 269,501 | **instrument_id**=`instrument_id`; **premium**=`close` | `bar_ts`, `trade_date` |
| `hist_gamma_metrics` | 183,872 | **gamma**=`gamma_concentration,gamma_zone`; **instrument_id**=`instrument_id`; **spot**=`spot`; **symbol**=`symbol` | `bar_ts`, `created_at`, `trade_date` |
| `hist_market_state` | 181,848 | **gamma**=`gamma_regime,gamma_zone`; **iv**=`atm_iv,iv_regime,iv_skew`; **spot**=`spot`; **symbol**=`symbol` | `bar_ts`, `created_at`, `trade_date` |
| `hist_basis_context` | 122,012 | **expiry**=`expiry_date`; **spot**=`spot_delta,spot_now`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `market_spot_snapshots` | 77,156 | **spot**=`spot`; **symbol**=`symbol` | `created_at`, `ts` |
| `study_path` | 47,787 | **spot**=`spot`; **symbol**=`symbol` | `session_date` |
| `hist_spot_bars_5m` | 46,067 | **instrument_id**=`instrument_id`; **premium**=`close`; **symbol**=`symbol` | `bar_ts`, `created_at`, `trade_date` |
| `latest_signal_v1` | 45,000 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `expiry_date`, `metrics_ts` |
| `latest_signal_v1_gated` | 45,000 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `expiry_date`, `metrics_ts` |
| `vol_analytics` | 24,765 | **iv**=`implied_vol_atm`; **symbol**=`symbol` | `created_at`, `ts` |
| `wcb_signal_validation_v1` | 20,867 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_concentration,gamma_regime`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `wcb_signal_validation_v2` | 20,867 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `index_futures_snapshots` | 20,737 | **expiry**=`expiry_date,expiry_type`; **spot**=`spot_price`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `market_state_snapshots` | 18,500 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_features,gamma_run_id`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `options_flow_snapshots` | 16,477 | **spot**=`spot`; **symbol**=`symbol` | `created_at`, `ts` |
| `hist_spot_bars_15m` | 15,971 | **instrument_id**=`instrument_id`; **premium**=`close`; **symbol**=`symbol` | `bar_ts`, `created_at`, `trade_date` |
| `dhan_nse_equity_norm` | 14,386 | **instrument_id**=`dhan_security_id`; **symbol**=`instrument` | — |
| `shadow_signal_snapshots_v3` | 12,038 | **gamma**=`gamma_regime`; **iv**=`iv_context_low_conf,iv_rank,iv_regime`; **symbol**=`symbol` | `created_at`, `ts` |
| `structural_divergence_snapshots` | 8,444 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_concentration_delta`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `hist_pattern_signals` | 7,583 | **gamma**=`gamma_regime`; **iv**=`iv_regime`; **spot**=`spot_at_signal`; **symbol**=`symbol` | `bar_ts`, `created_at`, `trade_date` |
| `basis_context_snapshots` | 6,315 | **spot**=`spot_delta,spot_now`; **symbol**=`symbol` | `created_at`, `ts` |
| `signal_market_path_audit_v1` | 5,551 | **spot**=`spot,spot_move_pct,spot_move_points,spot_source_ts`; **symbol**=`symbol` | `created_at`, `futures_source_ts`, `path_ts`, `signal_ts`, `spot_source_ts` |
| `breadth_equity_indicators` | 4,500 | **instrument_id**=`dhan_security_id`; **premium**=`close`; **symbol**=`ticker` | `trade_date`, `updated_at` |
| `historical_market_spot_1m` | 2,748 | **instrument_id**=`security_id`; **premium**=`ltp`; **symbol**=`symbol` | `created_at`, `ts` |
| `gamma_metrics_shadow` | 1,952 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_zone`; **spot**=`spot,spot_vs_range`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `breadth_universe_members` | 1,495 | **instrument_id**=`dhan_security_id`; **symbol**=`symbol,ticker` | `added_at` |
| `dhan_scrip_map` | 1,495 | **instrument_id**=`dhan_security_id`; **symbol**=`ticker,trading_symbol` | `updated_at` |
| `hist_completeness_checks` | 1,480 | **expiry**=`expiry_date`; **instrument_id**=`instrument_id` | `checked_at`, `expiry_date`, `trade_date` |
| `nse_dhan_bridge` | 1,385 | **instrument_id**=`dhan_security_id`; **symbol**=`instrument` | `updated_at` |
| `latest_signal_inputs_v2` | 1,013 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration`; **spot**=`spot`; **symbol**=`symbol` | `breadth_date`, `created_at`, `expiry_date`, `ts` |
| `signal_state_snapshots` | 856 | **gamma**=`gamma_bias,gamma_zone`; **symbol**=`symbol` | `created_at`, `ts` |
| `shadow_state_signal_snapshots` | 844 | **gamma**=`gamma_bias,gamma_zone`; **symbol**=`symbol` | `created_at`, `ts` |
| `signal_regret_log` | 614 | **gamma**=`gamma_regime`; **spot**=`spot_at_15m,spot_at_30m,spot_at_60m,spot_at_signal`; **symbol**=`symbol` | `created_at`, `signal_ts` |
| `hist_greeks_backfill_log` | 492 | **iv**=`rows_null_iv`; **symbol**=`symbol` | `finished_at`, `started_at`, `trade_date` |
| `equity_eod_norm` | 245 | **instrument_id**=`dhan_security_id`; **premium**=`close` | `trade_date` |
| `equity_eod_shadow_audit` | 150 | **instrument_id**=`security_id`; **symbol**=`ticker` | `created_at`, `request_finished_at`, `request_started_at` |
| `market_spot_snapshots_replay` | 150 | **spot**=`spot`; **symbol**=`symbol` | `created_at`, `ts` |
| `options_flow_snapshots_replay` | 150 | **spot**=`spot`; **symbol**=`symbol` | `created_at`, `ts` |
| `gamma_metrics_replay` | 144 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_zone`; **spot**=`spot,spot_vs_range`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `market_state_snapshots_replay` | 144 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_features,gamma_run_id`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `shadow_reconstruction_v3` | 138 | **gamma**=`gamma_regime`; **iv**=`iv_context_low_conf,iv_rank,iv_regime`; **symbol**=`symbol` | `created_at`, `reconstruction_date`, `source_iv_context_ts`, `source_market_state_ts`, `source_momentum_ts`, `source_options_flow_ts` |
| `iv_context_snapshots` | 106 | **iv**=`current_atm_iv,iv_52w_high,iv_52w_low,iv_percentile,iv_rank,iv_regime`; **symbol**=`symbol` | `created_at`, `ts` |
| `shadow_reconstruction_v1` | 87 | **gamma**=`gamma_regime`; **iv**=`iv_context_low_conf,iv_rank,iv_regime`; **symbol**=`symbol` | `created_at`, `reconstruction_date`, `source_iv_context_ts`, `source_market_state_ts`, `source_momentum_ts`, `source_options_flow_ts` |
| `signal_outcomes` | 73 | **spot**=`spot_15m,spot_30m,spot_60m,spot_at_signal,spot_eod`; **symbol**=`symbol` | `created_at`, `entry_spot_ts`, `horizon_15m_ts`, `horizon_30m_ts`, `horizon_60m_ts`, `horizon_eod_ts` |
| `shadow_reconstruction_v2` | 69 | **gamma**=`gamma_regime`; **iv**=`iv_context_low_conf,iv_rank,iv_regime`; **symbol**=`symbol` | `created_at`, `reconstruction_date`, `source_iv_context_ts`, `source_market_state_ts`, `source_momentum_ts`, `source_options_flow_ts` |
| `bom_dhan_bridge` | 59 | **instrument_id**=`dhan_security_id` | `updated_at` |
| `signal_outcome_audit` | 48 | **gamma**=`gamma_regime`; **symbol**=`symbol` | `created_at`, `signal_ts` |
| `latest_gamma_metrics` | 45 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `latest_gamma_metrics_v2` | 45 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `latest_signal_inputs` | 45 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration`; **spot**=`spot`; **symbol**=`symbol` | `breadth_date`, `created_at`, `expiry_date`, `ts` |
| `signal_labels` | 24 | **expiry**=`expiry_date`; **spot**=`spot_return_pct`; **symbol**=`symbol` | `created_at`, `entry_ts`, `exit_ts`, `expiry_date` |
| `signal_market_outcome_audit_v1` | 17 | **spot**=`spot_15m,spot_30m,spot_60m,spot_mae_60m_points,spot_mfe_60m_points,spot_move_15m_pct,spot_move_15m_points,spot_move_30m_pct,spot_move_30m_points,spot_move_60m_pct,spot_move_60m_points`; **symbol**=`symbol` | `created_at`, `signal_ts` |
| `shadow_signal_outcomes` | 10 | **spot**=`spot_15m,spot_30m,spot_60m,spot_at_signal,spot_eod`; **symbol**=`symbol` | `created_at`, `entry_spot_ts`, `horizon_15m_ts`, `horizon_30m_ts`, `horizon_60m_ts`, `horizon_eod_ts` |
| `shadow_signal_snapshots` | 10 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `shadow_signal_validation_v1` | 10 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `market_state_ts`, `ts` |
| `v_dealer_flow_sim` | 6 | **expiry**=`expiry_date`; **spot**=`spot_pct`; **symbol**=`symbol` | `expiry_date`, `ts` |
| `shadow_outcomes_v1` | 4 | **spot**=`spot_15m,spot_30m,spot_5m,spot_60m`; **symbol**=`symbol` | `created_at`, `ts` |
| `shadow_outcomes_v2` | 4 | **spot**=`spot_15m,spot_30m,spot_5m,spot_60m`; **symbol**=`symbol` | `created_at`, `shadow_created_at`, `ts` |
| `shadow_replay_v1` | 4 | **spot**=`spot_15m,spot_30m,spot_5m,spot_60m`; **symbol**=`symbol` | `created_at`, `replay_date`, `source_shadow_created_at`, `ts` |
| `signal_runs` | 3 | **gamma**=`gamma_run_ids` | `breadth_ts`, `created_at`, `run_ts` |
| `active_breadth_universe_members_nse` | 1 | **instrument_id**=`dhan_security_id`; **symbol**=`ticker` | — |
| `active_breadth_universe_nse` | 1 | **instrument_id**=`dhan_security_id`; **symbol**=`ticker` | `updated_at` |
| `breadth_universe_nse_only` | 1 | **instrument_id**=`dhan_security_id`; **symbol**=`symbol,ticker` | `added_at` |
| `dhan_symbol_alias` | 1 | **instrument_id**=`dhan_security_id` | — |
| `hist_iv_surface_daily` | 1 | **expiry**=`expiry_date`; **instrument_id**=`instrument_id`; **iv**=`atm_iv` | `expiry_date`, `heston_calibrated_at`, `snap_ts`, `trade_date` |
| `market_state_snapshots_shadow` | 1 | **expiry**=`expiry_date,expiry_type`; **gamma**=`gamma_features,gamma_run_id`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `measurement_health_snapshots` | 1 | **gamma**=`gamma_status` | `created_at`, `ts` |
| `shadow_vs_live_evaluation` | 1 | **spot**=`spot_after_30m,spot_after_60m,spot_at_signal`; **symbol**=`symbol` | `created_at`, `ts` |
| `signal_outcome_audit_dedup` | 1 | **gamma**=`gamma_regime`; **symbol**=`symbol` | `created_at`, `signal_ts` |
| `signal_outcome_research_v1` | 1 | **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `signal_ts` |
| `signal_outcome_research_v2` | 1 | **gamma**=`gamma_concentration,gamma_regime`; **spot**=`spot`; **symbol**=`symbol` | `signal_ts` |
| `structural_divergence_snapshots_replay` | 1 | **expiry**=`expiry_date`; **gamma**=`gamma_concentration,gamma_concentration_delta`; **spot**=`spot`; **symbol**=`symbol` | `created_at`, `expiry_date`, `ts` |
| `vol_analytics_shadow` | 1 | **iv**=`implied_vol_atm`; **symbol**=`symbol` | `created_at`, `ts` |

### Tier D — no GEX input  (98 relations)

Carry none of gamma / iv / oi / strike / option_type / spot / instrument_id. Named for
completeness of the enumeration; not measured further.

`_active_universe_choice`, `_equity_eod_detected`, `_s36_outcomes_pre_truncate`, `active_breadth_universe`, `aging_policy`, `app_settings`, `breadth_coverage_latest`, `breadth_indicators_daily`, `breadth_ingest_state`, `breadth_intraday_history`, `breadth_universe_sets`, `breadth_universe_snapshot`, `bse_scripcode_isin_map`, `bse_t1_securities`, `capital_tracker`, `dashboard_last_updated`, `data_contamination_ranges`, `data_quality_events`, `dhan_auth_tokens`, `dhan_scripmaster`, `dhan_scripmaster_staging`, `dhan_token_probe_log`, `eq_corporate_actions`, `eq_feature_store`, `eq_fundamental_snapshots`, `eq_ingestion_log`, `eq_instrument_events`, `eq_instruments`, `eq_macro_data`, `eq_market_gate`, `eq_paper_trades`, `eq_price_daily`, `eq_price_daily_backup_20260618`, `eq_price_daily_v2`, `eq_signal_snapshots`, `eq_stock_sector_map`, `eq_trading_calendar`, `eq_watchlist`, `equity_eod`, `equity_intraday_last`, `fii_dii_cash_daily`, `hist_ict_htf_zones`, `hist_ingest_log`, `hist_ingest_rejects`, `ict_htf_zones`, `ict_primitive_outcomes`, `ict_primitives`, `index_constituent_weights`, `india_vix_daily`, `india_vix_history`, `intraday_ohlc`, `latest_market_breadth`, `latest_market_breadth_intraday`, `latest_market_breadth_nse`, `latest_run_id`, `market_breadth_daily`, `market_breadth_daily_nse`, `market_breadth_intraday`, `market_spot_session_markers`, `merdian_parameters`, `model_registry`, `momentum_snapshots`, `momentum_snapshots_replay`, `momentum_snapshots_shadow`, `momentum_snapshots_v2`, `nifty_move_anchor`, `option_outcome_analytics_v1`, `participant_oi_daily`, `po3_session_state`, `raw_ingest_log`, `script_execution_log`, `script_execution_log_replay`, `shadow_state_signal_outcomes`, `signal_outcome_audit_v2`, `signal_outcome_audit_v2_intraday_clean`, `signal_regret_analytics_v1`, `signal_regret_analytics_v2`, `smdm_snapshots`, `study_accel_stat`, `study_eligible`, `study_null_pair`, `study_pin_stat`, `study_real_pair`, `study_runs_m`, `study_step_m`, `study_zone_ref`, `system_config`, `trading_calendar`, `underlyings`, `v_dhan_token_probe_today`, `v_expiry_base_rates`, `v_merdian_parameter_audit`, `v_participant_oi_latest`, `v_script_execution_health_30m`, `v_wcb_active_weights`, `v_wcb_weight_totals`, `vix_percentile_reference`, `weighted_constituent_breadth_snapshots`

---

## 3. Coverage, month by month, across each candidate's full history

No start date was assumed. For every table the true `min`/`max` of its date column was
read first (`?select=<col>&order=<col>.asc|desc&limit=1`), then months were probed from one
month **before** that minimum to one month **after** that maximum, so a real edge outside
the discovered bound would appear rather than be excluded by construction.

### 3.0 The discovered bounds

| table | date column | min | max |
|---|---|---|---|
| `hist_option_bars_1m` | `trade_date` | *not readable — see note* | *not readable — see note* |
| `hist_option_bars_1m` | `bar_ts` | 2025-04-01T09:15:59+00:00 | 2026-05-07T15:29:00+00:00 |
| `hist_option_greeks_1m` | `trade_date` | 2025-04-01 | 2026-03-30 |
| `hist_option_greeks_1m` | `bar_ts` | *not readable — see note* | *not readable — see note* |
| `historical_option_chain_snapshots` | `ts` | 2026-03-16T09:51:09.542716+00:00 | 2026-06-03T09:59:00+00:00 |
| `option_chain_snapshots` | `ts` | 2026-08-24T10:00:05.366368+00:00 | 2026-09-08T03:05:06.352824+00:00 |
| `gex_strike_snapshots` | `ts` | 2026-05-25T09:56:07.707025+00:00 | 2026-09-07T10:10:05.075295+00:00 |
| `hist_atm_option_bars_5m` | `trade_date` | 2025-04-01 | 2026-03-30 |
| `hist_atm_option_bars_15m` | `trade_date` | 2025-04-01 | 2026-03-30 |
| `hist_volatility_snapshots` | `trade_date` | 2025-04-01 | 2026-03-30 |
| `volatility_snapshots` | `ts` | 2025-04-01T03:45:00+00:00 | 2026-09-07T10:10:05.075295+00:00 |
| `option_execution_price_history` | `ts` | 2026-03-18T05:48:52.407896+00:00 | 2026-03-27T09:59:18.417553+00:00 |
| `v_oi_prev_close_snapshots` | `prev_close_ts` | 2026-08-25T10:10:04.673098+00:00 | 2026-09-07T10:10:05.075295+00:00 |
| `gamma_metrics` | `ts` | 2026-06-09T10:55:05.326819+00:00 | 2026-09-07T10:10:05.075295+00:00 |
| `hist_gamma_metrics` | `trade_date` | 2025-04-01 | 2026-03-30 |
| `gamma_metrics_shadow` | `ts` | 2026-05-12T09:56:07.278052+00:00 | 2026-06-01T09:55:16.5334+00:00 |
| `hist_spot_bars_1m` | `trade_date` | 2025-04-01 | 2026-09-07 |
| `hist_spot_bars_5m` | `trade_date` | 2025-04-01 | 2026-06-04 |
| `hist_spot_bars_15m` | `trade_date` | 2025-04-01 | 2026-06-04 |
| `market_spot_snapshots` | `ts` | 2026-02-15T03:51:40.822+00:00 | 2026-09-07T10:30:02.978183+00:00 |
| `historical_market_spot_1m` | `bar_ts` | *not readable — see note* | *not readable — see note* |
| `index_futures_snapshots` | `ts` | 2026-03-16T04:35:39.824576+00:00 | 2026-09-07T10:30:04.849389+00:00 |
| `hist_future_bars_1m` | `trade_date` | 2025-04-01 | 2026-03-30 |

Three entries need their failure stated rather than glossed:

- `hist_option_bars_1m.trade_date` — `order=trade_date.asc&limit=1` returns `57014`
  statement timeout in both directions. The column is present but has no usable index for
  an ordered scan at this table size, so `bar_ts` was used for every range filter on this
  table instead.
- `hist_option_greeks_1m.bar_ts` — same `57014` in both directions; `trade_date` was used.
- `historical_market_spot_1m.bar_ts` — `42703 column does not exist`. The column is `ts`.
  Corrected and re-measured in Step 5.

### 3.1 `hist_option_bars_1m` — 54.8M rows, the vendor chain

Month-scoped `not.is.null` probes on this table exceed the statement timeout, and
`count=planned` on a `not.is.null` filter over an **all-NULL** column returns a planner
floor of `1`, which is not a row. Reporting that `1` would have been a false positive.
So gamma/iv/oi presence here was measured **per trading day** with `limit=1`, which returns
either real rows or a real empty list:

```
GET /hist_option_bars_1m?select=gamma&bar_ts=gte.<day>&bar_ts=lt.<day+1>
    &instrument_id=eq.<uuid>&gamma=not.is.null&limit=1
```

**289 weekdays probed, 2025-04-01 through 2026-05-08, each for both symbols.**

| month | symbol | weekdays with rows | days with non-null gamma | days with non-null iv | days with non-null oi | month rows |
|---|---|---:|---:|---:|---:|---:|
| 2025-04 | NIFTY | 19 | 0 | 0 | 19 | — |
| 2025-04 | SENSEX | 19 | 0 | 0 | 19 | 1,467,760 (exact) |
| 2025-05 | NIFTY | 21 | 0 | 0 | 21 | — |
| 2025-05 | SENSEX | 21 | 0 | 0 | 21 | 1,720,360 (planned) |
| 2025-06 | NIFTY | 21 | 0 | 0 | 21 | — |
| 2025-06 | SENSEX | 20 | 0 | 0 | 20 | 1,667,768 (planned) |
| 2025-07 | NIFTY | 23 | 0 | 0 | 23 | 2,703,655 (planned) |
| 2025-07 | SENSEX | 23 | 0 | 0 | 23 | 1,490,226 (planned) |
| 2025-08 | NIFTY | 19 | 0 | 0 | 19 | 2,288,305 (planned) |
| 2025-08 | SENSEX | 19 | 0 | 0 | 19 | 1,344,065 (exact) |
| 2025-09 | NIFTY | 22 | 0 | 0 | 22 | 2,450,839 (planned) |
| 2025-09 | SENSEX | 22 | 0 | 0 | 22 | 1,350,876 (planned) |
| 2025-10 | NIFTY | 21 | 0 | 0 | 21 | 2,576,625 (planned) |
| 2025-10 | SENSEX | 21 | 0 | 0 | 21 | 1,551,569 (exact) |
| 2025-11 | NIFTY | 19 | 0 | 0 | 19 | 2,573,360 (planned) |
| 2025-11 | SENSEX | 19 | 0 | 0 | 19 | 1,419,356 (exact) |
| 2025-12 | NIFTY | 22 | 0 | 0 | 22 | 2,971,964 (planned) |
| 2025-12 | SENSEX | 22 | 0 | 0 | 22 | 1,565,274 (exact) |
| 2026-01 | NIFTY | 20 | 0 | 0 | 20 | 3,852,029 (planned) |
| 2026-01 | SENSEX | 20 | 0 | 0 | 20 | 2,123,197 (planned) |
| 2026-02 | NIFTY | 20 | 0 | 0 | 20 | — |
| 2026-02 | SENSEX | 20 | 0 | 0 | 20 | 1,759,257 (planned) |
| 2026-03 | NIFTY | 19 | 0 | 0 | 19 | 1,737,580 (planned) |
| 2026-03 | SENSEX | 19 | 0 | 0 | 19 | 957,736 (planned) |
| 2026-04 | NIFTY | 0 | 0 | 0 | 0 | — |
| 2026-04 | SENSEX | 0 | 0 | 0 | 0 | — |
| 2026-05 | NIFTY | 2 | 0 | 0 | 2 | 9,262 (exact) |
| 2026-05 | SENSEX | 2 | 0 | 0 | 2 | 21,261 (exact) |

**gamma: zero. iv: zero.** Not on any of the 289 probed days, for either symbol, anywhere in
the table's 13-month span. Two day-cells (`2025-05-28` and `2025-06-26`, NIFTY, gamma)
initially returned `57014`; both were re-probed at half-day scope and returned `HTTP 200 []`
on both halves, so **no cell in this sweep is unresolved**.

`oi` is non-null on every one of those days. A sampled row confirms the shape:

```
GET /hist_option_bars_1m?select=instrument_id,bar_ts,expiry_date,strike,option_type,oi,iv,gamma
    &bar_ts=gte.2025-06-02T09:20:00&bar_ts=lt.2025-06-02T09:21:00&limit=4
-> {"expiry_date":"2025-06-26","strike":14000.0,"option_type":"PE","oi":64925,
    "iv":null,"gamma":null}   (4 of 4 rows, iv and gamma null)
```

Two further measured facts about this table's extent:

- **2026-04: zero.** All 22 weekdays probed, both symbols, `HTTP 200 []`. No rows.
- **2026-05: two days.** `2026-05-04` and `2026-05-07`, both symbols, both with non-null
  `oi` and null gamma/iv. The table's max `bar_ts` of `2026-05-07T15:29:00+00:00` is those
  two days, not a continuous run.

### 3.2 `hist_option_greeks_1m` — 19.3M rows, the greeks sidecar

Same day-level method, 261 weekdays probed, 2025-04-01 through 2026-03-31, both symbols.

| month | symbol | weekdays with rows | days with non-null gamma | days with non-null iv | days present in `hist_option_bars_1m` |
|---|---|---:|---:|---:|---:|
| 2025-04 | NIFTY | 14 | 14 | 14 | 19 |
| 2025-04 | SENSEX | 13 | 13 | 13 | 19 |
| 2025-05 | NIFTY | 17 | 17 | 17 | 21 |
| 2025-05 | SENSEX | 17 | 17 | 17 | 21 |
| 2025-06 | NIFTY | 17 | 17 | 17 | 21 |
| 2025-06 | SENSEX | 16 | 16 | 16 | 20 |
| 2025-07 | NIFTY | 18 | 18 | 18 | 23 |
| 2025-07 | SENSEX | 18 | 18 | 18 | 23 |
| 2025-08 | NIFTY | 15 | 15 | 15 | 19 |
| 2025-08 | SENSEX | 15 | 15 | 15 | 19 |
| 2025-09 | NIFTY | 17 | 17 | 17 | 22 |
| 2025-09 | SENSEX | 18 | 18 | 18 | 22 |
| 2025-10 | NIFTY | 17 | 17 | 17 | 21 |
| 2025-10 | SENSEX | 16 | 16 | 16 | 21 |
| 2025-11 | NIFTY | 15 | 15 | 15 | 19 |
| 2025-11 | SENSEX | 15 | 15 | 15 | 19 |
| 2025-12 | NIFTY | 17 | 17 | 17 | 22 |
| 2025-12 | SENSEX | 18 | 18 | 18 | 22 |
| 2026-01 | NIFTY | 16 | 16 | 16 | 20 |
| 2026-01 | SENSEX | 15 | 15 | 15 | 20 |
| 2026-02 | NIFTY | 16 | 16 | 16 | 20 |
| 2026-02 | SENSEX | 16 | 16 | 16 | 20 |
| 2026-03 | NIFTY | 14 | 14 | 14 | 19 |
| 2026-03 | SENSEX | 15 | 15 | 15 | 19 |

gamma and iv are non-null on **every day that has any row at all** — the sidecar has no
partially-populated day. What it has instead is fewer days than the chain it sits beside:

| | NIFTY | SENSEX |
|---|---:|---:|
| days with gamma in `hist_option_greeks_1m` | 193 | 192 |
| days with rows in `hist_option_bars_1m`, same window (to 2026-03-31) | 246 | 245 |
| days in the sidecar that are **not** in the chain | 0 | 0 |
| days in the chain with no sidecar row | **53** | **53** |

The sidecar is a strict subset. Its coverage stops at 2026-03-30.

### 3.3 `historical_option_chain_snapshots` — 3.2M rows

| month | symbol | rows | non-null gamma | non-null iv | non-null oi | days with rows | strike min–max |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-03 | NIFTY | 109,322 (exact) | 109,322 (exact) | 109,322 (exact) | 109,322 (exact) | 5 | 9000–41000 |
| 2026-03 | SENSEX | 114,402 (exact) | 114,402 (exact) | 114,402 (exact) | 114,402 (exact) | 6 | 65100–95300 |
| 2026-04 | NIFTY | 720,571 (exact) | 675,143 (planned) | 675,143 (planned) | 688,399 (planned) | 20 | *timeout — see below* |
| 2026-04 | SENSEX | 734,205 (exact) | 662,657 (planned) | 662,657 (planned) | 675,668 (planned) | 20 | *timeout — see below* |
| 2026-05 | NIFTY | 727,288 (exact) | 698,608 (planned) | 698,608 (planned) | 712,325 (planned) | 19 | *timeout — see below* |
| 2026-06 | NIFTY | 68,620 (exact) | 68,620 (exact) | 68,620 (exact) | 68,620 (exact) | 2 | 18150–29850 |
| 2026-06 | SENSEX | 77,055 (exact) | 55,710 (exact) | 55,710 (exact) | 77,055 (exact) | 3 | 67300–86300 |

Three cells above timed out at month scope and were re-measured at day scope. Day-scope
results are exact:

| cell | month-scope result | day-scope result |
|---|---|---|
| 2026-05 SENSEX, does the month exist | `57014` timeout | **19 of 21 weekdays have rows** |
| 2026-04 strike min/max | `57014` timeout | NIFTY 17100–30100, SENSEX 64900–93200 (on 2026-04-01) |
| 2026-05 strike min/max | `57014` timeout | NIFTY 17100–29850, SENSEX 64900–86300 (on 2026-05-04) |

On every day sampled for non-null density, gamma, iv, oi and spot are non-null on **100%**
of that day's rows:

| day | symbol | rows | non-null gamma | non-null iv | non-null oi | non-null spot |
|---|---|---:|---:|---:|---:|---:|
| 2026-03-20 | NIFTY | 22,428 | 22,428 | 22,428 | 22,428 | 22,428 |
| 2026-03-16 | SENSEX | 1,728 | 1,728 | 1,728 | 1,728 | 1,728 |
| 2026-04-01 | NIFTY | 27,666 | 27,666 | 27,666 | 27,666 | 27,666 |
| 2026-04-01 | SENSEX | 30,672 | 30,672 | 30,672 | 30,672 | 30,672 |
| 2026-05-04 | NIFTY | 17,920 | 17,920 | 17,920 | 17,920 | 17,920 |
| 2026-05-04 | SENSEX | 15,910 | 15,910 | 15,910 | 15,910 | 15,910 |
| 2026-06-01 | NIFTY | 33,840 | 33,840 | 33,840 | 33,840 | 33,840 |
| 2026-06-01 | SENSEX | 27,824 | 27,824 | 27,824 | 27,824 | 27,824 |

The two month-scope figures that read below 100% (2026-04 and 2026-05 gamma) are
`planned` estimates, not counts. The day-scope exact counts above contradict them.

### 3.4 `option_chain_snapshots` — 699K rows, the live capture

| month | symbol | rows | non-null gamma | non-null iv | non-null oi | days with rows | strike min–max |
|---|---|---:|---:|---:|---:|---:|---|
| 2026-08 | NIFTY | 200,922 (exact) | 200,922 (exact) | 200,922 (exact) | 200,922 (exact) | 6 | 17850–30000 |
| 2026-08 | SENSEX | 159,668 (exact) | 159,668 (exact) | 159,668 (exact) | 159,668 (exact) | 6 | 66500–86000 |
| 2026-09 | NIFTY | 196,426 (exact) | 196,426 (exact) | 196,426 (exact) | 196,426 (exact) | 6 | 18500–30000 |
| 2026-09 | SENSEX | 146,880 (exact) | 146,880 (exact) | 146,880 (exact) | 146,880 (exact) | 6 | 69100–86000 |

Every count here is `exact`. gamma, iv and oi are non-null on 100% of rows in both months.
The table's earliest row is `2026-08-24T10:00:05+00:00`; 2026-07 was probed and returned
zero rows for both symbols.

### 3.5 `gex_strike_snapshots` — 1.4M rows, per-strike GEX already computed

| month | symbol | rows | non-null gamma_call | non-null gamma_put | non-null oi_call | non-null oi_put | non-null gex_cr | days | strike min–max |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-05 | NIFTY | 25,950 | 16,712 | 15,660 | 25,950 | 25,950 | 25,950 | 4 | 20100.0–27250.0 |
| 2026-05 | SENSEX | 52,000 | 19,833 | 16,940 | 52,000 | 52,000 | 52,000 | 4 | 64900.0–91700.0 |
| 2026-06 | NIFTY | 121,928 | 66,866 | 83,895 | 121,928 | 121,928 | 121,928 | 18 | 12000.0–34500.0 |
| 2026-06 | SENSEX | 186,327 | 98,435 | 106,171 | 186,327 | 186,327 | 186,327 | 19 | 64900.0–91000.0 |
| 2026-07 | NIFTY | 186,424 | 108,228 | 163,595 | 186,424 | 186,424 | 186,424 | 23 | 21100.0–26300.0 |
| 2026-07 | SENSEX | 319,869 | 142,070 | 200,133 | 319,869 | 319,869 | 319,869 | 23 | 66500.0–85300.0 |
| 2026-08 | NIFTY | 189,037 | 143,258 | 124,611 | 189,037 | 189,037 | 189,037 | 21 | 21200.0–27200.0 |
| 2026-08 | SENSEX | 255,325 | 155,888 | 138,482 | 255,325 | 255,325 | 255,325 | 21 | 66800.0–85300.0 |
| 2026-09 | NIFTY | 37,316 | 32,154 | 20,565 | 37,316 | 37,316 | 37,316 | 6 | 22000.0–27200.0 |
| 2026-09 | SENSEX | 54,064 | 41,036 | 28,957 | 54,064 | 54,064 | 54,064 | 6 | 71100.0–84700.0 |

Every count in this table is `exact`. `oi_call`, `oi_put` and `gex_cr` are non-null on 100%
of rows in every month. `gamma_call` and `gamma_put` are non-null on a fraction — between
54% and 88% depending on month and side — while `gex_cr` for the same rows is 100%
non-null. This document records that pattern; it does not interpret it.

### 3.6 `hist_atm_option_bars_5m` — 27K rows

| month | symbol | rows | non-null ce_gamma | non-null pe_gamma | non-null ce_oi | non-null pe_oi | days |
|---|---|---:|---:|---:|---:|---:|---:|
| 2025-04 | NIFTY | 1,001 | 0 | 0 | 1,001 | 1,001 | 19 |
| 2025-04 | SENSEX | 704 | 0 | 0 | 702 | 700 | 18 |
| 2025-05 | NIFTY | 1,255 | 0 | 0 | 1,254 | 1,255 | 21 |
| 2025-05 | SENSEX | 929 | 0 | 0 | 925 | 926 | 21 |
| 2025-06 | NIFTY | 1,271 | 0 | 0 | 1,270 | 1,271 | 21 |
| 2025-06 | SENSEX | 942 | 0 | 0 | 940 | 941 | 20 |
| 2025-07 | NIFTY | 1,529 | 0 | 0 | 1,529 | 1,529 | 23 |
| 2025-07 | SENSEX | 1,238 | 0 | 0 | 1,236 | 1,238 | 23 |
| 2025-08 | NIFTY | 1,322 | 0 | 0 | 1,322 | 1,322 | 19 |
| 2025-08 | SENSEX | 1,033 | 0 | 0 | 1,032 | 1,033 | 19 |
| 2025-09 | NIFTY | 1,555 | 0 | 0 | 1,554 | 1,555 | 22 |
| 2025-09 | SENSEX | 1,344 | 0 | 0 | 1,341 | 1,343 | 22 |
| 2025-10 | NIFTY | 1,304 | 0 | 0 | 1,303 | 1,303 | 21 |
| 2025-10 | SENSEX | 762 | 0 | 0 | 762 | 761 | 21 |
| 2025-11 | NIFTY | 1,257 | 0 | 0 | 1,257 | 1,257 | 19 |
| 2025-11 | SENSEX | 973 | 0 | 0 | 971 | 973 | 19 |
| 2025-12 | NIFTY | 1,473 | 0 | 0 | 1,473 | 1,473 | 22 |
| 2025-12 | SENSEX | 1,142 | 0 | 0 | 1,141 | 1,142 | 22 |
| 2026-01 | NIFTY | 1,229 | 0 | 0 | 1,228 | 1,229 | 20 |
| 2026-01 | SENSEX | 874 | 0 | 0 | 873 | 874 | 20 |
| 2026-02 | NIFTY | 1,313 | 0 | 0 | 1,313 | 1,313 | 20 |
| 2026-02 | SENSEX | 993 | 0 | 0 | 993 | 993 | 20 |
| 2026-03 | NIFTY | 925 | 0 | 0 | 925 | 925 | 19 |
| 2026-03 | SENSEX | 714 | 0 | 0 | 710 | 712 | 19 |

`ce_gamma` and `pe_gamma` are non-null on **zero** rows in every month, both symbols, all
counts `exact`. `ce_oi`/`pe_oi` are near-fully populated. This table also carries one ATM
strike per bar (`atm_strike`), not a strike dimension, so it could not support a per-strike
GEX even with gamma present.

### 3.7 `hist_volatility_snapshots` — 181K rows

| month | symbol | rows | non-null atm_iv | non-null atm_call_iv | non-null atm_put_iv | days |
|---|---|---:|---:|---:|---:|---:|
| 2025-04 | NIFTY | 6,780 | 0 | 6,780 | 6,780 | 19 |
| 2025-04 | SENSEX | 6,650 | 0 | 6,650 | 6,650 | 18 |
| 2025-05 | NIFTY | 7,822 | 0 | 7,822 | 7,822 | 21 |
| 2025-05 | SENSEX | 7,845 | 0 | 7,845 | 7,845 | 21 |
| 2025-06 | NIFTY | 7,807 | 0 | 7,807 | 7,807 | 21 |
| 2025-06 | SENSEX | 7,448 | 0 | 7,448 | 7,448 | 20 |
| 2025-07 | NIFTY | 8,571 | 0 | 8,571 | 8,571 | 23 |
| 2025-07 | SENSEX | 8,530 | 0 | 8,530 | 8,530 | 23 |
| 2025-08 | NIFTY | 7,037 | 0 | 7,037 | 7,037 | 19 |
| 2025-08 | SENSEX | 7,092 | 0 | 7,092 | 7,092 | 19 |
| 2025-09 | NIFTY | 8,134 | 0 | 8,134 | 8,134 | 22 |
| 2025-09 | SENSEX | 8,206 | 0 | 8,206 | 8,206 | 22 |
| 2025-10 | NIFTY | 7,445 | 0 | 7,445 | 7,445 | 21 |
| 2025-10 | SENSEX | 7,507 | 0 | 7,507 | 7,507 | 21 |
| 2025-11 | NIFTY | 7,086 | 0 | 7,086 | 7,086 | 19 |
| 2025-11 | SENSEX | 7,075 | 0 | 7,075 | 7,075 | 19 |
| 2025-12 | NIFTY | 8,210 | 0 | 8,210 | 8,210 | 22 |
| 2025-12 | SENSEX | 8,189 | 0 | 8,189 | 8,189 | 22 |
| 2026-01 | NIFTY | 7,469 | 0 | 7,469 | 7,469 | 20 |
| 2026-01 | SENSEX | 7,440 | 0 | 7,440 | 7,440 | 20 |
| 2026-02 | NIFTY | 7,112 | 0 | 7,112 | 7,112 | 19 |
| 2026-02 | SENSEX | 7,458 | 0 | 7,458 | 7,458 | 20 |
| 2026-03 | NIFTY | 7,094 | 0 | 7,094 | 7,094 | 19 |
| 2026-03 | SENSEX | 7,097 | 0 | 7,097 | 7,097 | 19 |

`atm_iv` is non-null on **zero** rows in every month (all `exact`); `atm_call_iv` and
`atm_put_iv` are non-null on 100%. One ATM strike per row, so no strike dimension.

### 3.8 `gamma_metrics` and `hist_gamma_metrics` — aggregate, not per-strike

Both hold `net_gex` as a single scalar per (symbol, timestamp). `gamma_metrics.max_gamma_strike`
is one strike per row, not a strike dimension. Neither can produce a per-strike GEX; they are
measured here because `net_gex` is a GEX quantity and Step 2 admitted them as candidates.

**`gamma_metrics`**

| month | symbol | rows | non-null net_gex | non-null gamma_concentration | non-null max_gamma_strike | days |
|---|---|---:|---:|---:|---:|---:|
| 2026-06 | NIFTY | 837 | 837 | 837 | 837 | 15 |
| 2026-06 | SENSEX | 799 | 799 | 799 | 799 | 15 |
| 2026-07 | NIFTY | 1,893 | 1,893 | 1,893 | 1,893 | 23 |
| 2026-07 | SENSEX | 1,893 | 1,893 | 1,893 | 1,893 | 23 |
| 2026-08 | NIFTY | 1,709 | 1,709 | 1,709 | 1,709 | 21 |
| 2026-08 | SENSEX | 1,708 | 1,708 | 1,708 | 1,708 | 21 |
| 2026-09 | NIFTY | 422 | 422 | 422 | 422 | 6 |
| 2026-09 | SENSEX | 419 | 419 | 419 | 419 | 6 |

**`hist_gamma_metrics`**

| month | symbol | rows | non-null net_gex | non-null gamma_concentration | days |
|---|---|---:|---:|---:|---:|
| 2025-04 | NIFTY | 6,758 | 6,758 | 4,888 | 18 |
| 2025-04 | SENSEX | 6,746 | 6,746 | 4,875 | 18 |
| 2025-05 | NIFTY | 7,888 | 7,888 | 6,392 | 21 |
| 2025-05 | SENSEX | 7,871 | 7,871 | 6,373 | 21 |
| 2025-06 | NIFTY | 7,888 | 7,888 | 6,392 | 21 |
| 2025-06 | SENSEX | 7,497 | 7,497 | 6,000 | 20 |
| 2025-07 | NIFTY | 8,638 | 8,638 | 6,768 | 23 |
| 2025-07 | SENSEX | 8,620 | 8,620 | 6,750 | 23 |
| 2025-08 | NIFTY | 7,136 | 7,136 | 5,640 | 19 |
| 2025-08 | SENSEX | 7,120 | 7,120 | 5,623 | 19 |
| 2025-09 | NIFTY | 8,262 | 8,262 | 6,392 | 22 |
| 2025-09 | SENSEX | 8,240 | 8,240 | 6,743 | 22 |
| 2025-10 | NIFTY | 7,573 | 7,573 | 6,077 | 21 |
| 2025-10 | SENSEX | 7,557 | 7,557 | 5,685 | 21 |
| 2025-11 | NIFTY | 7,136 | 7,136 | 5,640 | 19 |
| 2025-11 | SENSEX | 7,123 | 7,123 | 5,625 | 19 |
| 2025-12 | NIFTY | 8,262 | 8,262 | 6,392 | 22 |
| 2025-12 | SENSEX | 8,247 | 8,247 | 6,750 | 22 |
| 2026-01 | NIFTY | 7,512 | 7,512 | 6,016 | 20 |
| 2026-01 | SENSEX | 7,497 | 7,497 | 5,625 | 20 |
| 2026-02 | NIFTY | 7,512 | 7,512 | 6,016 | 20 |
| 2026-02 | SENSEX | 7,496 | 7,496 | 6,000 | 20 |
| 2026-03 | NIFTY | 6,760 | 6,760 | 5,264 | 18 |
| 2026-03 | SENSEX | 7,122 | 7,122 | 5,625 | 19 |

---

## 4. Identifier resolution

`hist_option_bars_1m`, `hist_option_greeks_1m`, `hist_spot_bars_*`, `hist_future_bars_1m`,
`hist_volatility_snapshots`, `hist_atm_option_bars_5m` and `hist_gamma_metrics` identify their
instrument by `instrument_id uuid` rather than by a symbol string.

### What resolves it

`public.instruments`, which holds **exactly two rows** (`count=exact` -> `0-1/2`):

| id | symbol | exchange | strike_step | lot_size | weekly_expiry_dow |
|---|---|---|---:|---:|---:|
| `9992f600-51b3-4009-b487-f878692a0bc5` | NIFTY | NSE | 50 | 65 | 2 (Tue) |
| `73a1390a-30c9-46d6-9d3f-5f03c3f5ad71` | SENSEX | BSE | 100 | 20 | 4 (Thu) |

### How many distinct ids the data tables hold

**Two, on every table where the question could be answered.** The probe was
`?select=instrument_id&instrument_id=not.in.(<nifty>,<sensex>)&limit=3`:

| table | NIFTY id present | SENSEX id present | any third id |
|---|---|---|---|
| `hist_option_bars_1m` | present | *`57014` timeout* | *`57014` timeout — unresolved* |
| `hist_option_greeks_1m` | present | present | *`57014` timeout — unresolved* |
| `hist_spot_bars_1m` | present | present | **zero rows returned** |
| `hist_spot_bars_5m` | present | present | **zero rows returned** |
| `hist_future_bars_1m` | present | present | **zero rows returned** |
| `hist_volatility_snapshots` | present | present | **zero rows returned** |
| `hist_atm_option_bars_5m` | present | present | **zero rows returned** |
| `hist_gamma_metrics` | present | present | **zero rows returned** |

On `hist_option_bars_1m` and `hist_option_greeks_1m` the unfiltered `not.in.` scan exceeds
the statement timeout, so a third id cannot be excluded on those two by this method. On the
other six the scan completes and returns zero rows. `hist_option_bars_1m` SENSEX presence was
confirmed separately by the day-scoped sweep in §3.1, which found SENSEX rows on 265 days.

### Is strike / expiry / option_type encoded in the id

**No — the id identifies the underlying index only, and strike, expiry and option type are
separate columns.** A single sampled minute makes this unambiguous: four rows sharing one
`instrument_id`, differing in expiry, strike and type.

```
GET /hist_option_bars_1m?select=instrument_id,bar_ts,expiry_date,strike,option_type,oi,iv,gamma
    &bar_ts=gte.2025-06-02T09:20:00&bar_ts=lt.2025-06-02T09:21:00&limit=4

instrument_id                         bar_ts                expiry_date  strike  type   oi
9992f600-51b3-4009-b487-f878692a0bc5  2025-06-02T09:20:59Z  2025-06-26   14000   PE   64925
9992f600-51b3-4009-b487-f878692a0bc5  2025-06-02T09:20:59Z  2025-12-24   16000   PE    3775
9992f600-51b3-4009-b487-f878692a0bc5  2025-06-02T09:20:59Z  2025-12-24   19000   PE  170325
9992f600-51b3-4009-b487-f878692a0bc5  2025-06-02T09:20:59Z  2025-09-25   19000   PE  121875
```

So `hist_option_bars_1m` and `hist_option_greeks_1m` share the join key
`(instrument_id, bar_ts, expiry_date, strike, option_type)`. Both carry all five columns.

---

## 5. Spot

Every relation holding an index spot price against a timestamp, with its measured extent
per symbol. `min`/`max` from `?select=<col>&order=<col>.asc|desc&limit=1&<symbol filter>`.

| relation | time column | price column | symbol | min | max |
|---|---|---|---|---|---|
| `hist_spot_bars_1m` | `trade_date` | `close` | NIFTY | 2025-04-01 | 2026-09-07 |
| `hist_spot_bars_1m` | `trade_date` | `close` | SENSEX | 2025-04-01 | 2026-09-07 |
| `hist_spot_bars_5m` | `trade_date` | `close` | NIFTY | 2025-04-01 | 2026-06-04 |
| `hist_spot_bars_5m` | `trade_date` | `close` | SENSEX | 2025-04-01 | 2026-06-04 |
| `hist_spot_bars_15m` | `trade_date` | `close` | NIFTY | 2025-04-01 | 2026-06-04 |
| `hist_spot_bars_15m` | `trade_date` | `close` | SENSEX | 2025-04-01 | 2026-06-04 |
| `market_spot_snapshots` | `ts` | `spot` | NIFTY | 2026-02-15T03:51:40.822+00:00 | 2026-09-07T10:30:02.978183+00:00 |
| `market_spot_snapshots` | `ts` | `spot` | SENSEX | 2026-02-15T04:33:02.791+00:00 | 2026-09-07T10:30:02.978183+00:00 |
| `historical_market_spot_1m` | `ts` | `ltp` | NIFTY | 2026-03-19T09:58:01.772979+00:00 | 2026-09-07T10:30:02.978183+00:00 |
| `historical_market_spot_1m` | `ts` | `ltp` | SENSEX | 2026-03-19T09:58:01.772979+00:00 | 2026-09-07T10:30:02.978183+00:00 |
| `hist_gamma_metrics` | `trade_date` | `spot` | NIFTY | 2025-04-01 | 2026-03-30 |
| `hist_gamma_metrics` | `trade_date` | `spot` | SENSEX | 2025-04-01 | 2026-03-30 |
| `gamma_metrics` | `ts` | `spot` | NIFTY | 2026-06-09T10:55:05.326819+00:00 | 2026-09-08T03:20:06.544479+00:00 |
| `gamma_metrics` | `ts` | `spot` | SENSEX | 2026-06-10T07:30:06.642078+00:00 | 2026-09-08T03:20:06.421695+00:00 |
| `historical_option_chain_snapshots` | `ts` | `spot` | NIFTY | 2026-03-20T03:51:37.363417+00:00 | 2026-06-02T09:55:11.888617+00:00 |
| `historical_option_chain_snapshots` | `ts` | `spot` | SENSEX | 2026-03-16T09:51:09.542716+00:00 | 2026-06-03T09:59:00+00:00 |
| `option_chain_snapshots` | `ts` | `spot` | NIFTY | 2026-08-24T10:00:05.366368+00:00 | 2026-09-08T03:25:04.695125+00:00 |
| `option_chain_snapshots` | `ts` | `spot` | SENSEX | 2026-08-24T10:00:05.477058+00:00 | 2026-09-08T03:25:04.727326+00:00 |
| `gex_strike_snapshots` | `ts` | `spot` | NIFTY | 2026-05-25T09:56:07.707025+00:00 | 2026-09-08T03:20:06.544479+00:00 |
| `gex_strike_snapshots` | `ts` | `spot` | SENSEX | 2026-05-25T09:56:50.356398+00:00 | 2026-09-08T03:20:06.421695+00:00 |
| `hist_volatility_snapshots` | `trade_date` | `spot` | NIFTY | 2025-04-01 | 2026-03-30 |
| `hist_volatility_snapshots` | `trade_date` | `spot` | SENSEX | 2025-04-01 | 2026-03-30 |
| `volatility_snapshots` | `ts` | `spot` | NIFTY | 2025-04-01T03:45:00+00:00 | 2026-09-08T03:20:06.544479+00:00 |
| `volatility_snapshots` | `ts` | `spot` | SENSEX | 2025-04-01T03:45:00+00:00 | 2026-09-08T03:20:06.421695+00:00 |
| `index_futures_snapshots` | `ts` | `spot` | NIFTY | 2026-03-16T04:35:39.824576+00:00 | 2026-09-07T10:30:04.849389+00:00 |
| `index_futures_snapshots` | `ts` | `spot` | SENSEX | 2026-03-16T04:35:39.824576+00:00 | 2026-09-07T10:30:04.849389+00:00 |

### Granularity

Consecutive timestamps read from the most recent populated day of each relation:

| relation | consecutive timestamps sampled | implied granularity |
|---|---|---|
| `market_spot_snapshots` | 03:41:03, 03:46:03, 03:47:02, 03:48:03, 03:49:03, 03:50:04 | 1 minute |
| `gamma_metrics` | 03:05:06, 03:10:06, 03:15:04, 03:20:06 | 5 minutes |
| `volatility_snapshots` | 03:05:06, 03:10:06, 03:15:04, 03:20:06 | 5 minutes |
| `historical_option_chain_snapshots` | six rows sharing 03:45:48.867904 | one snapshot per chain sweep |
| `option_chain_snapshots` | six rows sharing 03:05:06.146085 | one snapshot per chain sweep |
| `gex_strike_snapshots` | six rows sharing 03:05:06.146085 | one snapshot per chain sweep |
| `hist_spot_bars_1m` | *see note* | 1 minute (`bar_ts`; the sample was taken on `trade_date`, which is date-only) |
| `hist_spot_bars_5m` / `_15m` | *see note* | 5 / 15 minutes by construction of the same writer family |

Two entries could not be sampled and that is recorded rather than filled in:
`historical_market_spot_1m` and `index_futures_snapshots` returned fewer than two rows on the
day-scoped granularity probe, so no interval was observed. `historical_market_spot_1m` also
returned an identical min and max for NIFTY and SENSEX, which the probe design cannot
distinguish from a genuine coincidence; it is reported as measured, uninterpreted.

### Which spot source can serve which candidate, and at what tolerance

| candidate needing spot | spot already in the same row? | otherwise nearest source | matching tolerance |
|---|---|---|---|
| `historical_option_chain_snapshots` | **yes** — `spot`, non-null on 100% of rows on every sampled day | — | exact, same row |
| `option_chain_snapshots` | **yes** — `spot` | — | exact, same row |
| `gex_strike_snapshots` | **yes** — `spot` | — | exact, same row |
| `hist_option_bars_1m` | no | `hist_spot_bars_1m` (2025-04-01 to 2026-09-07, both symbols) | join on `(instrument_id, bar_ts)`; both are 1-minute series, so exact-minute matching is available for the whole overlap |
| `hist_option_greeks_1m` | no | `hist_spot_bars_1m` | same, `(instrument_id, bar_ts)`, exact minute |

`hist_spot_bars_1m` is the only spot relation covering the full 2025-04-01 to 2026-09-07 span
for both symbols. `hist_spot_bars_5m` and `_15m` both stop at 2026-06-04.

---

## 6. The answer

One row per calendar month from the earliest data anywhere (2025-04) to today (2026-09-08),
stated separately for NIFTY and SENSEX.

### How each day was classified

The verdict is a **count of measured trading days**, not an interpolation between sampled
months. Every trading day in the range was probed individually in each source.

- **Trading-day denominator** — a day counts as a trading day for a symbol if
  `hist_spot_bars_1m` holds at least one row for that symbol on that date. This is the only
  relation spanning 2025-04-01 to 2026-09-07 for both symbols. 376 weekdays were probed.
- **COMPUTABLE NOW** — some per-strike source has non-null gamma *and* the open interest to
  pair it with, on that day, for that symbol.
- **COMPUTABLE AFTER DERIVATION** — no gamma, but a per-strike source has non-null iv and OI,
  so Black-Scholes can supply gamma.
- **NOT COMPUTABLE** — neither.

Four day-cells initially returned `57014` instead of a true/false answer
(`historical_option_chain_snapshots` gamma on 2026-04-16 for both symbols;
`hist_option_bars_1m` gamma on 2025-05-28 and 2025-06-26 for NIFTY). Counting an errored
probe as an absence would have manufactured a verdict, so each was re-probed at half-day and
then quarter-day scope until it resolved. All four resolved to **false**. The classifier now
asserts that no cell is unresolved before it counts anything, and that assertion passes.

Source combinations, each verified to carry every column it is credited with:

| label | tables | supplies |
|---|---|---|
| `greeks+bars` | `hist_option_greeks_1m` ⋈ `hist_option_bars_1m` on `(instrument_id, bar_ts, expiry_date, strike, option_type)` | gamma + iv from the sidecar, oi from the chain, spot from `hist_spot_bars_1m` on `(instrument_id, bar_ts)` |
| `hocs` | `historical_option_chain_snapshots` | gamma, iv, oi, strike, option_type, spot, symbol — all in one row |
| `ocs` | `option_chain_snapshots` | same, all in one row |
| `gex_strike` | `gex_strike_snapshots` | gamma_call/gamma_put, oi_call/oi_put, strike, spot, symbol — all in one row |

### The table

| month | symbol | trading days | COMPUTABLE NOW | COMPUTABLE AFTER DERIVATION | NOT COMPUTABLE | source combination |
|---|---|---:|---:|---:|---:|---|
| 2025-04 | NIFTY | 19 | 14 | 0 | 5 | `greeks+bars` (14d) |
| 2025-04 | SENSEX | 18 | 13 | 0 | 5 | `greeks+bars` (13d) |
| 2025-05 | NIFTY | 21 | 17 | 0 | 4 | `greeks+bars` (17d) |
| 2025-05 | SENSEX | 21 | 17 | 0 | 4 | `greeks+bars` (17d) |
| 2025-06 | NIFTY | 21 | 17 | 0 | 4 | `greeks+bars` (17d) |
| 2025-06 | SENSEX | 21 | 16 | 0 | 5 | `greeks+bars` (16d) |
| 2025-07 | NIFTY | 23 | 18 | 0 | 5 | `greeks+bars` (18d) |
| 2025-07 | SENSEX | 23 | 18 | 0 | 5 | `greeks+bars` (18d) |
| 2025-08 | NIFTY | 19 | 15 | 0 | 4 | `greeks+bars` (15d) |
| 2025-08 | SENSEX | 19 | 15 | 0 | 4 | `greeks+bars` (15d) |
| 2025-09 | NIFTY | 22 | 17 | 0 | 5 | `greeks+bars` (17d) |
| 2025-09 | SENSEX | 22 | 18 | 0 | 4 | `greeks+bars` (18d) |
| 2025-10 | NIFTY | 21 | 17 | 0 | 4 | `greeks+bars` (17d) |
| 2025-10 | SENSEX | 21 | 16 | 0 | 5 | `greeks+bars` (16d) |
| 2025-11 | NIFTY | 19 | 15 | 0 | 4 | `greeks+bars` (15d) |
| 2025-11 | SENSEX | 19 | 15 | 0 | 4 | `greeks+bars` (15d) |
| 2025-12 | NIFTY | 22 | 17 | 0 | 5 | `greeks+bars` (17d) |
| 2025-12 | SENSEX | 22 | 18 | 0 | 4 | `greeks+bars` (18d) |
| 2026-01 | NIFTY | 20 | 16 | 0 | 4 | `greeks+bars` (16d) |
| 2026-01 | SENSEX | 20 | 15 | 0 | 5 | `greeks+bars` (15d) |
| 2026-02 | NIFTY | 20 | 16 | 0 | 4 | `greeks+bars` (16d) |
| 2026-02 | SENSEX | 20 | 16 | 0 | 4 | `greeks+bars` (16d) |
| 2026-03 | NIFTY | 19 | 15 | 0 | 4 | `greeks+bars` (14d), `hocs` (5d) |
| 2026-03 | SENSEX | 19 | 16 | 0 | 3 | `greeks+bars` (15d), `hocs` (6d) |
| 2026-04 | NIFTY | 20 | 19 | 0 | 1 | `hocs` (19d) |
| 2026-04 | SENSEX | 20 | 19 | 0 | 1 | `hocs` (19d) |
| 2026-05 | NIFTY | 19 | 19 | 0 | 0 | `hocs` (19d), `gex_strike` (4d) |
| 2026-05 | SENSEX | 19 | 19 | 0 | 0 | `hocs` (19d), `gex_strike` (4d) |
| 2026-06 | NIFTY | 21 | 17 | 0 | 4 | `gex_strike` (17d), `hocs` (2d) |
| 2026-06 | SENSEX | 21 | 18 | 0 | 3 | `gex_strike` (18d), `hocs` (2d) |
| 2026-07 | NIFTY | 23 | 23 | 0 | 0 | `gex_strike` (23d) |
| 2026-07 | SENSEX | 23 | 23 | 0 | 0 | `gex_strike` (23d) |
| 2026-08 | NIFTY | 21 | 21 | 0 | 0 | `gex_strike` (21d), `ocs` (6d) |
| 2026-08 | SENSEX | 21 | 21 | 0 | 0 | `gex_strike` (21d), `ocs` (6d) |
| 2026-09 | NIFTY | 6 | 6 | 0 | 0 | `ocs` (6d), `gex_strike` (6d) |
| 2026-09 | SENSEX | 6 | 6 | 0 | 0 | `ocs` (6d), `gex_strike` (6d) |

### Totals, 2025-04-01 to 2026-09-08

| | NIFTY | SENSEX |
|---|---:|---:|
| trading days measured | 356 | 355 |
| COMPUTABLE NOW | 299 | 299 |
| COMPUTABLE AFTER DERIVATION | 0 | 0 |
| NOT COMPUTABLE | 57 | 56 |

### The days counted NOT COMPUTABLE

**NIFTY — 57 days.**

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

**SENSEX — 56 days.**

```
  2025-04-01  2025-04-08  2025-04-15  2025-04-22  2025-04-29  2025-05-06  2025-05-13  2025-05-20
  2025-05-27  2025-06-03  2025-06-05  2025-06-10  2025-06-17  2025-06-24  2025-07-01  2025-07-08
  2025-07-15  2025-07-22  2025-07-29  2025-08-05  2025-08-12  2025-08-19  2025-08-26  2025-09-04
  2025-09-11  2025-09-18  2025-09-25  2025-10-01  2025-10-09  2025-10-16  2025-10-23  2025-10-30
  2025-11-06  2025-11-13  2025-11-20  2025-11-27  2025-12-04  2025-12-11  2025-12-18  2025-12-24
  2026-01-01  2026-01-08  2026-01-14  2026-01-22  2026-01-29  2026-02-05  2026-02-12  2026-02-19
  2026-02-26  2026-03-05  2026-03-12  2026-03-19  2026-04-16  2026-06-03  2026-06-04  2026-06-08
```

### Two things the table says that are worth reading off it directly

**COMPUTABLE AFTER DERIVATION is zero in every month, for both symbols.** That column is empty
not because iv is scarce but because the two are never separated: in every relation measured,
wherever iv is non-null gamma is non-null on the same rows, and wherever gamma is absent iv is
absent too. `historical_option_chain_snapshots`, `option_chain_snapshots` and
`hist_option_greeks_1m` each carry both. `hist_option_bars_1m` and `hist_atm_option_bars_5m`
carry neither. There is no measured day in this database whose only obstacle to a per-strike
GEX is a missing gamma that a stored iv could supply.

**The 57 / 56 NOT COMPUTABLE days are not one gap.** They fall in three separate shapes, each
measured:

| shape | days | what was measured |
|---|---:|---|
| 2025-04-01 to 2026-03-31, trading days with no `hist_option_greeks_1m` row | **52** NIFTY, **52** SENSEX | `hist_option_bars_1m` has rows with non-null `oi`; gamma and iv non-null on zero rows; no sidecar row for that date |
| 2026-04-16 | 1 NIFTY, 1 SENSEX | `historical_option_chain_snapshots` holds rows with non-null `oi`; `gamma`, `iv` and `spot` non-null on zero rows. This was one of the four cells that first returned `57014`; resolved to false at quarter-day scope |
| 2026-06-03, 06-04, 06-08 (+ 06-11 for NIFTY only) | 4 NIFTY, 3 SENSEX | `gex_strike_snapshots` has zero rows on 06-03, 06-04 and 06-08 for both symbols, and zero for NIFTY on 06-11 while SENSEX has full gamma that day. `historical_option_chain_snapshots` has zero rows for NIFTY on 06-03 and rows with null gamma/iv/spot for SENSEX; its maximum `ts` is `2026-06-03T09:59:00+00:00`, so it holds nothing on 06-04 or later |

The 52 above and the **53** in §3.2 are different quantities and both are as measured: §3.2
counts days present in `hist_option_bars_1m` but absent from the sidecar (denominator = chain
days, 246/245), while this row counts trading days by the `hist_spot_bars_1m` reference
(denominator = 356/355). They are not the same denominator and should not be read as one figure
disagreeing with itself.

### The weekday distribution of the 52 + 52 early NOT COMPUTABLE days

Measured, both symbols, 2025-04-01 to 2026-03-31. Denominator is all trading days in that
window by weekday, from the `hist_spot_bars_1m` reference.

| weekday | NIFTY NOT days | NIFTY trading days | SENSEX NOT days | SENSEX trading days |
|---|---:|---:|---:|---:|
| Mon | 3 | 50 | 0 | 49 |
| Tue | 27 | 51 | 22 | 51 |
| Wed | 2 | 49 | 3 | 49 |
| Thu | 20 | 46 | 27 | 46 |
| Fri | 0 | 50 | 0 | 50 |
| **total** | **52** | 246 | **52** | 245 |

Zero Fridays for either symbol. The two heavy weekdays are Tuesday and Thursday for both
symbols, in opposite order.

For reference, the actual expiry weekday was measured rather than inferred from the
`weekly_expiry_dow` integer, whose base convention the table does not record:

```
GET /historical_option_chain_snapshots?select=expiry_date&symbol=eq.NIFTY
    &ts=gte.2026-04-01&ts=lt.2026-04-08&limit=1000
-> one distinct expiry_date: 2026-04-07  (Tuesday)

same for SENSEX
-> one distinct expiry_date: 2026-04-09  (Thursday)
```

So NIFTY expires Tuesday and SENSEX Thursday in the sampled week, and `instruments` holds
`weekly_expiry_dow = 2` and `4` respectively. The correspondence between the expiry weekdays and
the two heavy columns above is recorded as measured; no claim is made here about why the
distribution has that shape.

### One measured fact that sits outside the three-state rule

The rule given for COMPUTABLE AFTER DERIVATION is *iv present, gamma absent*. On that rule,
every day whose only per-strike source is `hist_option_bars_1m` is NOT COMPUTABLE, because §3.1
measured iv as non-null on zero of 289 probed days.

That table does, however, carry `open`, `high`, `low` and `close` per strike per minute, and
`oi` non-null on every one of those days. A premium-to-iv-to-gamma solve is therefore a
two-step derivation from columns that are present, rather than a one-step derivation from a
stored iv. It is recorded here as a measured column-presence fact and is deliberately **not**
counted as a fourth state, because the task specified three.


---

## 7. Where measurement differs from what the repository records

Recorded here because the numbers came out of the queries above, not to propose anything.

**`hist_option_bars_1m` holds rows after 2026-03-30.** `CLAUDE.md` records TD-S34-NEW-4 with the
workaround *"restrict backtests to `trade_date <= '2026-03-30'`"*, on the evidence of nine probed
post-April dates returning zero. All nine of those dates are confirmed zero by this sweep. The
table nevertheless has rows on **2026-05-04 and 2026-05-07**, both symbols, with non-null `oi` —
and its maximum `bar_ts` is `2026-05-07T15:29:00+00:00`, not a date in March. Neither of those two
dates is among the nine that were probed. April 2026 is zero across all 22 weekdays.

**The 0%-Greeks characterisation of the purchased chain is confirmed and can now be stated as a
count.** gamma and iv are non-null on **zero of 289 probed trading days**, both symbols, across
2025-04-01 to 2026-05-08, with no unresolved cells.

**`historical_option_chain_snapshots` begins before the 2026-04-01 boundary.** Its earliest row is
`2026-03-16T09:51:09+00:00`, and it has rows on 5 (NIFTY) / 6 (SENSEX) March trading days. The
S35 dual-source reader boundary of 2026-04-01 sits inside a period where both tiers hold data,
rather than at the first row of the later tier.

**`hist_option_greeks_1m` covers a strict subset of the chain's days.** 193 (NIFTY) / 192 (SENSEX)
days carry gamma, against 246 / 245 days where the chain has rows in the same window. Zero days
exist in the sidecar that are absent from the chain.

---

## 8. Everything that could not be measured

| item | why | what was done instead |
|---|---|---|
| `pg_total_relation_size` per table | needs SQL against the catalog; PostgREST exposes only `public` tables, no RPC wraps it, no psql, no DB password | Step 1 ordered by row estimate; the omission is stated in the header rather than filled with a proxy |
| `pg_class.reltuples` read directly | same | `Prefer: count=planned`, which is the planner estimate derived from it; labelled `planned` at every use |
| exact row counts on `hist_option_bars_1m` | `count=exact` on that table returns `57014` at 8.44s | month figures marked `(planned)`; all presence/absence facts measured per-day where exact answers are available |
| a third `instrument_id` on `hist_option_bars_1m` and `hist_option_greeks_1m` | the unfiltered `not.in.` scan exceeds the statement timeout on both | ruled out on the other six instrument_id tables, where the scan completes and returns zero rows; not ruled out on these two, and said so in §4 |
| distinct strike counts per month | PostgREST has no `DISTINCT`, and materialising a month of strikes from a 54.8M-row table is not viable through it | strike `min`–`max` per month per symbol reported instead, which is measured; distinct counts are absent rather than estimated |
| granularity of `historical_market_spot_1m` and `index_futures_snapshots` | the day-scoped probe returned fewer than two rows, so no interval was observed | left blank in §5 |
