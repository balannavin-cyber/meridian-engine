-- Phase 2 step 1 (design: claude/anon_phase2_design_S104.md). Dedicated read role for the PostgREST proxy: SELECT on the same 48
-- relations anon can read after Phase 1, nothing else. No password here: set it in the dashboard (Database > Roles) or with ALTER ROLE.
-- Operator action, SQL editor, ONE execution. Rollback: sql/2026-11-03_s104_marketview_ro_role_ROLLBACK.sql.
CREATE ROLE marketview_ro LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 8;
ALTER ROLE marketview_ro SET statement_timeout = '8s';
ALTER ROLE marketview_ro SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE marketview_ro SET default_transaction_read_only = on;
GRANT USAGE ON SCHEMA public TO marketview_ro;
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
  public.v_gex_abs_exposure_1pct,
  public.v_gex_concentration,
  public.v_gex_greeks_l2_net_1pct,
  public.v_gex_greeks_l2_strike_1pct,
  public.v_gex_max_pain,
  public.v_gex_net_gamma_river_1pct,
  public.v_gex_repriced_flip,
  public.v_gex_strike_accel_zone,
  public.v_gex_strike_pin_zone,
  public.v_gex_strike_rank,
  public.v_gex_strike_snapshots_1pct,
  public.v_gex_strike_terrain_1pct,
  public.v_gex_strike_walls,
  public.v_iv_surface,
  public.v_iv_term_structure,
  public.v_max_pain_by_strike,
  public.v_merdian_parameter_audit,
  public.v_oi_rotation_since_open,
  public.v_pin_board,
  public.weighted_constituent_breadth_snapshots,
  public.v_gex_abs_exposure,
  public.v_gex_greeks_l2_net,
  public.v_gex_greeks_l2_strike,
  public.v_gex_net_gamma_river,
  public.v_gex_strike_terrain
TO marketview_ro;
-- RLS-on tables among the 48 carry anon-only policies (qual = true); mirror them for the new role so reads are not silently empty.
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT c.relname FROM pg_class c
            WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r' AND c.relrowsecurity
              AND has_table_privilege('marketview_ro', c.oid, 'SELECT')
  LOOP
    EXECUTE format('CREATE POLICY marketview_ro_select ON public.%I FOR SELECT TO marketview_ro USING (true)', r.relname);
  END LOOP;
END $$;
