SELECT c.relname
       || ' | select=' || has_table_privilege('merdian_ro', ('public.'||c.relname)::regclass, 'SELECT')::text
       || ' | rls=' || c.relrowsecurity::text
       || ' | rls_forced=' || c.relforcerowsecurity::text
       || ' | policies=' || (SELECT count(*) FROM pg_policies p
                             WHERE p.schemaname='public' AND p.tablename=c.relname)::text
       || ' | pol_for_ro=' || (SELECT count(*) FROM pg_policies p
                             WHERE p.schemaname='public' AND p.tablename=c.relname
                               AND ('merdian_ro' = ANY(p.roles) OR 'public' = ANY(p.roles)))::text
       AS priv
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public'
  AND c.relname IN ('gex_run_v2','gex_strike_v2','gex_cycle_history',
                    'gex_strike_snapshots','p3b2_invariant_checks')
ORDER BY c.relname;
