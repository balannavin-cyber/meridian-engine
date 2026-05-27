-- ============================================================================
-- ENH-110 §Phase 1 — RLS + GRANT triplet for all Marketview / Settings surfaces
-- Session 39 / 2026-05-26
--
-- TD-S37-03 mitigation pattern: per-table RLS triplet documented inline.
-- Idempotent: safe to re-run; uses DROP POLICY IF EXISTS + CREATE POLICY.
--
-- Surfaces (from ENH-110 §Implementation Notes + Appendix A DATA SOURCES):
--   gex_strike_snapshots             — ADR-015 schema v2 (already RLS'd S37)
--   v_gex_strike_pin_zone            — ENH-81 (already deployed S37)
--   v_gex_strike_accel_zone          — ENH-81 (already deployed S37)
--   v_dealer_flow_sim                — ENH-81 (already deployed S37)
--   v_oi_prev_close_snapshots        — ENH-81 scaffold S37
--   gamma_metrics
--   market_breadth_intraday
--   signal_snapshots
--   ict_zones
--   po3_session_state
--   market_spot_session_markers
--   merdian_parameters               — ADR-016 (anon SELECT only; writes via update_parameter RPC)
--   v_merdian_parameter_audit        — Settings audit log surface
--
-- Anon role gets SELECT on every surface above. Writes use service-role
-- only (Settings save action goes through update_parameter SECURITY DEFINER
-- function — operator does not have direct INSERT/UPDATE on any table from
-- the Lovable client).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- TABLES — full triplet (RLS enable + policy + grant)
-- ---------------------------------------------------------------------------

-- gex_strike_snapshots (re-applied for idempotency / drift recovery)
ALTER TABLE public.gex_strike_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS gex_strike_snapshots_anon_read ON public.gex_strike_snapshots;
CREATE POLICY gex_strike_snapshots_anon_read
    ON public.gex_strike_snapshots FOR SELECT TO anon USING (true);
GRANT SELECT ON public.gex_strike_snapshots TO anon;

-- gamma_metrics
ALTER TABLE public.gamma_metrics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS gamma_metrics_anon_read ON public.gamma_metrics;
CREATE POLICY gamma_metrics_anon_read
    ON public.gamma_metrics FOR SELECT TO anon USING (true);
GRANT SELECT ON public.gamma_metrics TO anon;

-- market_breadth_intraday
ALTER TABLE public.market_breadth_intraday ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS market_breadth_intraday_anon_read ON public.market_breadth_intraday;
CREATE POLICY market_breadth_intraday_anon_read
    ON public.market_breadth_intraday FOR SELECT TO anon USING (true);
GRANT SELECT ON public.market_breadth_intraday TO anon;

-- signal_snapshots
ALTER TABLE public.signal_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS signal_snapshots_anon_read ON public.signal_snapshots;
CREATE POLICY signal_snapshots_anon_read
    ON public.signal_snapshots FOR SELECT TO anon USING (true);
GRANT SELECT ON public.signal_snapshots TO anon;

-- ict_zones
ALTER TABLE public.ict_zones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS ict_zones_anon_read ON public.ict_zones;
CREATE POLICY ict_zones_anon_read
    ON public.ict_zones FOR SELECT TO anon USING (true);
GRANT SELECT ON public.ict_zones TO anon;

-- po3_session_state
ALTER TABLE public.po3_session_state ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS po3_session_state_anon_read ON public.po3_session_state;
CREATE POLICY po3_session_state_anon_read
    ON public.po3_session_state FOR SELECT TO anon USING (true);
GRANT SELECT ON public.po3_session_state TO anon;

-- market_spot_session_markers
ALTER TABLE public.market_spot_session_markers ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS market_spot_session_markers_anon_read ON public.market_spot_session_markers;
CREATE POLICY market_spot_session_markers_anon_read
    ON public.market_spot_session_markers FOR SELECT TO anon USING (true);
GRANT SELECT ON public.market_spot_session_markers TO anon;

-- merdian_parameters (already applied in the ENH-83 DDL; re-applied for
-- drift recovery / single-source-of-truth in one migration)
ALTER TABLE public.merdian_parameters ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS merdian_parameters_anon_read ON public.merdian_parameters;
CREATE POLICY merdian_parameters_anon_read
    ON public.merdian_parameters FOR SELECT TO anon USING (true);
GRANT SELECT ON public.merdian_parameters TO anon;


-- ---------------------------------------------------------------------------
-- VIEWS — GRANT SELECT only (RLS applies via the underlying base tables;
-- views inherit the policy chain). Postgres requires explicit SELECT grant
-- on view objects for the anon role to invoke them via PostgREST.
-- ---------------------------------------------------------------------------

GRANT SELECT ON public.v_gex_strike_pin_zone        TO anon;
GRANT SELECT ON public.v_gex_strike_accel_zone      TO anon;
GRANT SELECT ON public.v_dealer_flow_sim            TO anon;
GRANT SELECT ON public.v_oi_prev_close_snapshots    TO anon;
GRANT SELECT ON public.v_merdian_parameter_audit    TO anon;


-- ---------------------------------------------------------------------------
-- Audit query — confirm every surface has SELECT grant for anon
-- (run after applying the migration to validate; non-zero row count where
-- expected confirms the triplet stuck)
-- ---------------------------------------------------------------------------

-- Tables with RLS enabled
SELECT
    schemaname,
    tablename,
    rowsecurity,
    (SELECT count(*) FROM pg_policies p
     WHERE p.schemaname = t.schemaname AND p.tablename = t.tablename) AS policy_count
FROM pg_tables t
WHERE schemaname = 'public'
  AND tablename IN (
    'gex_strike_snapshots',
    'gamma_metrics',
    'market_breadth_intraday',
    'signal_snapshots',
    'ict_zones',
    'po3_session_state',
    'market_spot_session_markers',
    'merdian_parameters'
  )
ORDER BY tablename;

-- Anon grants on tables and views
SELECT
    table_schema, table_name, privilege_type, grantee
FROM information_schema.role_table_grants
WHERE grantee = 'anon'
  AND table_schema = 'public'
  AND table_name IN (
    'gex_strike_snapshots', 'gamma_metrics', 'market_breadth_intraday',
    'signal_snapshots', 'ict_zones', 'po3_session_state',
    'market_spot_session_markers', 'merdian_parameters',
    'v_gex_strike_pin_zone', 'v_gex_strike_accel_zone',
    'v_dealer_flow_sim', 'v_oi_prev_close_snapshots',
    'v_merdian_parameter_audit'
  )
ORDER BY table_name, privilege_type;

-- Anon-callable RPC functions
SELECT
    routine_schema, routine_name, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('get_parameter_num', 'get_parameter_text',
                       'get_parameter_bool', 'update_parameter')
ORDER BY routine_name;

-- ============================================================================
-- END
-- ============================================================================
