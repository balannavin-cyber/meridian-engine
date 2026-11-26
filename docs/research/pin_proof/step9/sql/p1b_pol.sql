SELECT tablename || ' | ' || policyname || ' | cmd=' || cmd
       || ' | roles=' || array_to_string(roles, ',')
       || ' | permissive=' || permissive
       || ' | qual=' || coalesce(qual, '<none>') AS pol
FROM pg_policies
WHERE schemaname='public'
  AND tablename IN ('gex_run_v2','gex_strike_v2','gex_strike_snapshots','p3b2_invariant_checks')
ORDER BY tablename, policyname;
