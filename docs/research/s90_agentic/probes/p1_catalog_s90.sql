-- S90 R0.1 / R0.4 probe P1 — CATALOG ONLY. Safe in market hours: touches no
-- data table rows, only pg_catalog / information_schema / stats views.
-- Run:  bin/roq.sh scratch/s90/p1_catalog_s90.sql > scratch/s90/p1_catalog_s90.out 2>&1
\pset pager off
\pset null '(null)'
SELECT current_user AS role_now, now() AS probed_at;

-- ===== 1. 16:00 BLOCKER — merdian_parameters value_type contract =========
-- S89 seed writes value_type 'num'; repo DDL CHECK allows only 'numeric'
-- and get_parameter_num() filters value_type = 'numeric'.
SELECT conname, pg_get_constraintdef(c.oid) AS def
FROM pg_constraint c
WHERE conrelid = 'public.merdian_parameters'::regclass
ORDER BY conname;

SELECT p.proname, p.prosecdef AS security_definer,
       pg_get_function_identity_arguments(p.oid) AS args,
       p.proacl::text AS acl,
       has_function_privilege('anon', p.oid, 'EXECUTE') AS anon_can_execute,
       position('numeric' in pg_get_functiondef(p.oid)) > 0 AS body_mentions_numeric
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public'
  AND p.proname IN ('get_parameter_num','get_parameter_text','get_parameter_bool','update_parameter')
ORDER BY p.proname;

-- Row counts that RLS cannot blind (stats + planner estimate), beside the
-- RLS-filtered count merdian_ro actually sees. A gap = reader artefact.
SELECT s.relname, s.n_live_tup, c.reltuples::bigint AS reltuples_est,
       c.relrowsecurity AS rls_on,
       (SELECT count(*) FROM pg_policy pl WHERE pl.polrelid = c.oid) AS n_policies,
       (SELECT string_agg(pl.polname || ' TO ' ||
               array_to_string(ARRAY(SELECT rolname FROM pg_roles WHERE oid = ANY(pl.polroles)), ','), '; ')
        FROM pg_policy pl WHERE pl.polrelid = c.oid) AS policies
FROM pg_stat_user_tables s JOIN pg_class c ON c.oid = s.relid
WHERE s.relname = 'merdian_parameters';
SELECT count(*) AS rows_visible_to_merdian_ro FROM public.merdian_parameters;

-- ===== 2. gex_cycle_history — must be ABSENT before the apply ============
SELECT to_regclass('public.gex_cycle_history') AS gex_cycle_history_regclass;

-- ===== 3. Core products: keys, provenance columns, RLS, grants, size ======
WITH t(rel) AS (VALUES ('option_chain_snapshots'),('market_spot_snapshots'),
  ('market_ticks'),('gex_strike_snapshots'),('gamma_metrics'),
  ('volatility_snapshots'),('script_execution_log'),('merdian_parameters'),
  ('trading_calendar'),('gex_cycle_history'))
SELECT t.rel,
       c.oid IS NOT NULL AS exists,
       c.relrowsecurity AS rls_on,
       (SELECT count(*) FROM pg_policy pl WHERE pl.polrelid = c.oid) AS n_policies,
       (SELECT string_agg(DISTINCT r.rolname, ',') FROM pg_policy pl
          JOIN pg_roles r ON r.oid = ANY(pl.polroles) WHERE pl.polrelid = c.oid) AS policy_roles,
       CASE WHEN c.oid IS NULL THEN NULL ELSE has_table_privilege('anon', c.oid, 'SELECT') END AS anon_select,
       CASE WHEN c.oid IS NULL THEN NULL ELSE has_table_privilege('anon', c.oid, 'INSERT') END AS anon_insert,
       CASE WHEN c.oid IS NULL THEN NULL ELSE has_table_privilege('merdian_ro', c.oid, 'SELECT') END AS ro_select,
       c.relacl::text AS relacl,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       pg_total_relation_size(c.oid) AS total_bytes,
       s.n_live_tup
FROM t LEFT JOIN pg_class c ON c.oid = to_regclass('public.' || t.rel)
       LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
ORDER BY t.rel;

-- provenance-shaped columns per core product
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('option_chain_snapshots','market_spot_snapshots','market_ticks',
       'gex_strike_snapshots','gamma_metrics','volatility_snapshots','script_execution_log')
  AND (column_name ~ '(run_id|source|builder|version|sha|writer|host|raw|created_at)')
ORDER BY table_name, column_name;

-- unique keys (grain) per core product
SELECT c.relname AS table_name, i.relname AS index_name,
       pg_get_indexdef(ix.indexrelid) AS def
FROM pg_index ix
JOIN pg_class c ON c.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
WHERE ix.indisunique
  AND c.relname IN ('option_chain_snapshots','market_spot_snapshots','market_ticks',
       'gex_strike_snapshots','gamma_metrics','volatility_snapshots','script_execution_log',
       'merdian_parameters','trading_calendar')
ORDER BY 1, 2;

-- ===== 4. Database size: top 25 relations ===============================
SELECT c.relname, c.relkind, pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       pg_total_relation_size(c.oid) AS bytes, s.n_live_tup
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE n.nspname = 'public' AND c.relkind IN ('r','m')
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 25;
SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;
