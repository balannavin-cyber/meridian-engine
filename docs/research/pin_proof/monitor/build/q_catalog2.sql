-- Pin monitor build, catalog read 2: how a symbol resolves to
-- hist_spot_bars_1m.instrument_id, and the tau parameter function.
-- Catalog only. No data rows.

\echo == E tables holding both a symbol-like and an instrument-like column ==
SELECT c.table_name,
       string_agg(c.column_name || ':' || c.data_type, ', ' ORDER BY c.ordinal_position) AS cols
  FROM information_schema.columns c
 WHERE c.table_schema = 'public'
   AND c.table_name IN (
        SELECT table_name FROM information_schema.columns
         WHERE table_schema = 'public' AND column_name = 'instrument_id'
       )
   AND c.table_name LIKE '%instrument%'
 GROUP BY c.table_name
 ORDER BY c.table_name;

\echo == F candidate instrument dimension tables ==
SELECT t.table_name, t.table_type
  FROM information_schema.tables t
 WHERE t.table_schema = 'public'
   AND (t.table_name LIKE '%instrument%' OR t.table_name LIKE '%scrip%')
 ORDER BY t.table_name;

\echo == G columns of public.instruments ==
SELECT ordinal_position, column_name, data_type
  FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'instruments'
 ORDER BY ordinal_position;

\echo == H indexes on instruments ==
SELECT indexname, indexdef FROM pg_indexes
 WHERE schemaname = 'public' AND tablename = 'instruments' ORDER BY indexname;

\echo == I get_parameter_num signature ==
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args,
       pg_get_function_result(p.oid) AS result,
       has_function_privilege(current_user, p.oid, 'EXECUTE') AS can_execute
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'public' AND p.proname = 'get_parameter_num';
