-- ANON SHRINK, Phase 1 (engine stream, 2026-11-03). Marketview's bundle names 43 relations; 5 source views are added because the
-- security_invoker _1pct wrappers read them as anon. Everything else in public stops being readable by anon. ONE execution.
-- Before: 251 public relations anon can SELECT, MAINTAIN on ~190. After: 48 SELECT, nothing else.
-- Rollback: sql/2026-11-03_s104_anon_shrink_ROLLBACK.sql (re-grants the original 251 SELECTs).
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
GRANT SELECT ON
  public.dhan_token_probe_log,
  public.expiry_outcomes,
  public.gamma_metrics,
  public.gex_strike_snapshots,
  public.ict_zones,
  public.index_futures_snapshots,
  public.market_breadth_intraday,
  public.market_environment_snapshots,
  public.market_spot_session_markers,
  public.market_spot_snapshots,
  public.merdian_parameters,
  public.option_chain_snapshots,
  public.script_execution_log,
  public.signal_snapshots,
  public.trading_calendar,
  public.v_close_print,
  public.v_dealer_flow_sim,
  public.v_delta_drift_flow_vs_book,
  public.v_dex_flow_vs_book,
  public.v_dex_repriced_zero,
  public.v_dex_standing_book,
  public.v_expiry_base_rates,
  public.v_gamma_metrics_1pct,
  public.v_gex_abs_exposure,
  public.v_gex_abs_exposure_1pct,
  public.v_gex_concentration,
  public.v_gex_greeks_l2_net,
  public.v_gex_greeks_l2_net_1pct,
  public.v_gex_greeks_l2_strike,
  public.v_gex_greeks_l2_strike_1pct,
  public.v_gex_max_pain,
  public.v_gex_net_gamma_river,
  public.v_gex_net_gamma_river_1pct,
  public.v_gex_repriced_flip,
  public.v_gex_strike_accel_zone,
  public.v_gex_strike_pin_zone,
  public.v_gex_strike_rank,
  public.v_gex_strike_snapshots_1pct,
  public.v_gex_strike_terrain,
  public.v_gex_strike_terrain_1pct,
  public.v_gex_strike_walls,
  public.v_iv_surface,
  public.v_iv_term_structure,
  public.v_max_pain_by_strike,
  public.v_merdian_parameter_audit,
  public.v_oi_rotation_since_open,
  public.v_pin_board,
  public.weighted_constituent_breadth_snapshots
TO anon;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon;
-- the five SECURITY DEFINER write/trigger functions: no caller needs them as anon
REVOKE EXECUTE ON FUNCTION public.insert_option_chain_batch(text, date, numeric, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.insert_option_chain_run(text, date, numeric, jsonb, jsonb) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.trigger_ingest(text) FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.trigger_ingest_nifty() FROM PUBLIC, anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.trigger_ingest_sensex() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.insert_option_chain_batch(text, date, numeric, jsonb, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.insert_option_chain_run(text, date, numeric, jsonb, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.trigger_ingest(text) TO service_role;
GRANT EXECUTE ON FUNCTION public.trigger_ingest_nifty() TO service_role;
GRANT EXECUTE ON FUNCTION public.trigger_ingest_sensex() TO service_role;
