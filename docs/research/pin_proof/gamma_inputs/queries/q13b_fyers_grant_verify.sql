\pset format aligned
-- Verify the operator's 2026-11-20 grant + policy on public.fyers_futures_bars_1m.
-- CATALOG ONLY -- no row of the table is read by this query.
-- Expectation fixed before running: SELECT true, INSERT/UPDATE/DELETE all false.
SELECT current_user AS role_now,
       has_table_privilege('merdian_ro', 'public.fyers_futures_bars_1m', 'SELECT') AS sel,
       has_table_privilege('merdian_ro', 'public.fyers_futures_bars_1m', 'INSERT') AS ins,
       has_table_privilege('merdian_ro', 'public.fyers_futures_bars_1m', 'UPDATE') AS upd,
       has_table_privilege('merdian_ro', 'public.fyers_futures_bars_1m', 'DELETE') AS del;
-- Row-security state and every policy on the table, as stored.
SELECT c.relname, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname = 'fyers_futures_bars_1m';
SELECT policyname, permissive, roles, cmd, qual, with_check
  FROM pg_policies
 WHERE schemaname = 'public' AND tablename = 'fyers_futures_bars_1m'
 ORDER BY policyname;
