-- Tape T1-db post-apply access check (docs/tape/T1_db_plan.md section 1.2).
-- Rendered by services/tape_offline/sidecar_sql.py. Supabase SQL editor, postgres, ONE execution:
-- the role switch and the reads must share one execution (the editor opens a new session per run, S84).
-- Fails LOUDLY (permission denied) if merdian_ro cannot read a table. A 0 row count is not a failure
-- before the first load: the read proves privilege, not data. role_now must read merdian_ro or every
-- PASS below is void. One line per table, ending ACCESS PASS / ACCESS FAIL (<reasons>).
BEGIN;
SET LOCAL ROLE merdian_ro;
SELECT relation || ' ' || CASE WHEN role_now = 'merdian_ro' AND rls AND policies = 1 AND ro_select_policies = 1
         AND ro_has_select AND NOT anon_any AND NOT authenticated_any THEN 'ACCESS PASS'
       ELSE 'ACCESS FAIL (' || concat_ws(', ',
         CASE WHEN role_now <> 'merdian_ro' THEN 'role_now=' || role_now END,
         CASE WHEN NOT rls THEN 'rls off' END,
         CASE WHEN policies <> 1 THEN 'policies=' || policies END,
         CASE WHEN ro_select_policies <> 1 THEN 'no single merdian_ro SELECT USING (true) policy' END,
         CASE WHEN NOT ro_has_select THEN 'merdian_ro lacks SELECT' END,
         CASE WHEN anon_any THEN 'anon has a privilege' END,
         CASE WHEN authenticated_any THEN 'authenticated has a privilege' END) || ')' END AS verdict,
       role_now, rows_readable_by_ro, rls, policies, ro_select_policies, ro_has_select, anon_any, authenticated_any
FROM (
SELECT 'tape_minute' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.tape_minute) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_minute') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_minute'
           AND p.cmd = 'SELECT' AND p.roles = '{merdian_ro}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_any,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.tape_minute'::regclass
UNION ALL
SELECT 'tape_strike_cycle' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.tape_strike_cycle) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_strike_cycle') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_strike_cycle'
           AND p.cmd = 'SELECT' AND p.roles = '{merdian_ro}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_any,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.tape_strike_cycle'::regclass
UNION ALL
SELECT 'tape_events' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.tape_events) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_events') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_events'
           AND p.cmd = 'SELECT' AND p.roles = '{merdian_ro}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_any,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.tape_events'::regclass
UNION ALL
SELECT 'tape_chain_runs' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.tape_chain_runs) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_chain_runs') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_chain_runs'
           AND p.cmd = 'SELECT' AND p.roles = '{merdian_ro}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_any,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.tape_chain_runs'::regclass
UNION ALL
SELECT 'tape_chain_events' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.tape_chain_events) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_chain_events') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_chain_events'
           AND p.cmd = 'SELECT' AND p.roles = '{merdian_ro}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_any,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.tape_chain_events'::regclass
UNION ALL
SELECT 'tape_daily_report' AS relation,
       current_user::text AS role_now,
       (SELECT count(*) FROM public.tape_daily_report) AS rows_readable_by_ro,
       c.relrowsecurity AS rls,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_daily_report') AS policies,
       (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = 'tape_daily_report'
           AND p.cmd = 'SELECT' AND p.roles = '{merdian_ro}'::name[] AND p.qual = 'true') AS ro_select_policies,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_has_select,
       has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS anon_any,
       has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS authenticated_any
FROM pg_class c WHERE c.oid = 'public.tape_daily_report'::regclass
) x
ORDER BY relation;
COMMIT;
