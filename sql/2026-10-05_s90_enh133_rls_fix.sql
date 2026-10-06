-- S90 R0.4 — bring gex_cycle_history to the committed DDL's access intent.
-- SQL editor, postgres, ONE execution.
--
-- WHY. P2 (2026-10-05 17:12 IST) measured rls_on = t, 0 policies, and
-- relacl authenticated=rm. The DDL enables no RLS and says why
-- (sql/2026-10-03_s89_gex_cycle_history.sql:172-173: RLS with zero policies
-- makes the table unreadable by every non-bypass role, TD-S81-NEW-16 family).
-- So something outside the file turned RLS on at CREATE time; the first
-- SELECT below names it if it is an event trigger. With RLS on, merdian_ro
-- reads 0 rows forever and every row-level acceptance item (G1-G3, R1-R6)
-- would pass or fail on an empty read.
-- authenticated=rm comes from default privileges (R01-F8 family); the DDL
-- revokes anon only. Nothing in MERDIAN reads this table as authenticated.

-- 1. What enabled RLS? (read-only)
SELECT evtname, evtevent, evtfoid::regproc AS fn, evtenabled, evttags
FROM pg_event_trigger ORDER BY evtname;

BEGIN;
ALTER TABLE public.gex_cycle_history DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.gex_cycle_history FROM authenticated;
REVOKE ALL ON TABLE public.gex_cycle_history FROM anon;
GRANT SELECT ON TABLE public.gex_cycle_history TO merdian_ro;
COMMIT;

-- 2. Evidence (last result shown): expect rls_on=false and an ACL with only
--    postgres, service_role and merdian_ro=r.
SELECT current_user AS role_now, c.relrowsecurity AS rls_on, c.relacl::text AS acl,
       (SELECT string_agg(evtname || ':' || evtfoid::regproc::text, ', ') FROM pg_event_trigger) AS event_triggers
FROM pg_class c WHERE c.oid = 'public.gex_cycle_history'::regclass;
