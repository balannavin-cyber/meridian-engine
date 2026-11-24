-- Pin monitor build: catalog reads only. No data rows of any trading day.
-- CLAUDE.md rule 25 identity read for the pin-zone view is section D.

\echo == A columns ==
SELECT table_name, ordinal_position, column_name, data_type
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name IN ('gex_strike_snapshots', 'gex_cycle_history', 'hist_spot_bars_1m')
 ORDER BY table_name, ordinal_position;

\echo == B indexes ==
SELECT tablename, indexname, indexdef
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND tablename IN ('gex_strike_snapshots', 'gex_cycle_history', 'hist_spot_bars_1m')
 ORDER BY tablename, indexname;

\echo == C privileges merdian_ro ==
SELECT c.relname, c.relkind,
       has_table_privilege(current_user, c.oid, 'SELECT') AS can_select
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
   AND c.relname IN ('gex_strike_snapshots', 'gex_cycle_history', 'hist_spot_bars_1m',
                     'v_gex_strike_pin_zone', 'v_gex_strike_rank_gross')
 ORDER BY c.relname;

\echo == D pin zone view identity and definition ==
SELECT length(d) AS def_length, md5(d) AS def_md5,
       current_setting('server_version') AS pg_version
  FROM (SELECT pg_get_viewdef('public.v_gex_strike_pin_zone'::regclass, true) AS d) v;

SELECT pg_get_viewdef('public.v_gex_strike_pin_zone'::regclass, true) AS pin_zone_def;
