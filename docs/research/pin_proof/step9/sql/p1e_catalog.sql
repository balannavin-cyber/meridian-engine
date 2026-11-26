SELECT c.relname || ' | ' || c.relkind::text || ' | ' || a.attnum::text || ' | ' || a.attname
       || ' | ' || format_type(a.atttypid, a.atttypmod) || ' | nn=' || a.attnotnull::text AS col
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_attribute a ON a.attrelid=c.oid
WHERE n.nspname='public' AND c.relname='gamma_metrics'
  AND a.attnum>0 AND NOT a.attisdropped
ORDER BY a.attnum;

SELECT indexname || ' :: ' || regexp_replace(indexdef, '^.* USING ', '') AS idx
FROM pg_indexes WHERE schemaname='public' AND tablename='gamma_metrics' ORDER BY indexname;

SELECT c.relname
       || ' | select=' || has_table_privilege('merdian_ro', ('public.'||c.relname)::regclass, 'SELECT')::text
       || ' | rls=' || c.relrowsecurity::text
       || ' | policies=' || (SELECT count(*) FROM pg_policies p WHERE p.schemaname='public' AND p.tablename=c.relname)::text
       AS priv
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relname='gamma_metrics';

SELECT tablename || ' | ' || policyname || ' | cmd=' || cmd || ' | roles=' || array_to_string(roles,',')
       || ' | qual=' || coalesce(qual,'<none>') AS pol
FROM pg_policies WHERE schemaname='public' AND tablename='gamma_metrics' ORDER BY policyname;
