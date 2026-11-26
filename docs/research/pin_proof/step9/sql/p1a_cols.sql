SELECT c.relname || ' | ' || c.relkind::text || ' | ' || a.attnum::text || ' | ' || a.attname
       || ' | ' || format_type(a.atttypid, a.atttypmod)
       || ' | nn=' || a.attnotnull::text AS col
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid
WHERE n.nspname = 'public'
  AND c.relname IN ('gex_run_v2','gex_strike_v2','gex_cycle_history',
                    'gex_strike_snapshots','p3b2_invariant_checks')
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY c.relname, a.attnum;
