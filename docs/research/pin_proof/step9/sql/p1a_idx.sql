SELECT tablename || ' :: ' || indexname || ' :: ' ||
       regexp_replace(indexdef, '^CREATE (UNIQUE )?INDEX [^ ]+ ON [^ ]+ USING ', '') AS idx
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('gex_run_v2','gex_strike_v2','gex_cycle_history',
                    'gex_strike_snapshots','p3b2_invariant_checks')
ORDER BY tablename, indexname;
