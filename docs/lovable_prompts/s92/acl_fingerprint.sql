-- acl_fingerprint.sql — S92 Lovable safeguard. READ-ONLY. Run in the Supabase SQL editor
-- once BEFORE pasting the Lovable prompt and once AFTER Lovable has pushed. Paste both outputs to Claude.
-- Any change in a count or md5 between the two runs means something touched the database
-- (S39: Lovable's Supabase connection granted anon ALL). Nothing here writes.

WITH
rels AS (   -- every table / view / matview / sequence outside system schemas: ACL + RLS flags
  SELECT n.nspname || '.' || c.relname || ':' || c.relkind::text || ':' || coalesce(c.relacl::text, '-')
         || ':' || c.relrowsecurity || ':' || c.relforcerowsecurity AS k
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE c.relkind IN ('r','v','m','p','S','f')
    AND n.nspname NOT IN ('pg_catalog','information_schema','pg_toast')
    AND n.nspname NOT LIKE 'pg_temp%' AND n.nspname NOT LIKE 'pg_toast_temp%'
),
anon_rels AS ( -- what anon can actually do, per object in public
  SELECT c.relname || ':' ||
         concat_ws(',',
           CASE WHEN has_table_privilege('anon', c.oid, 'SELECT') THEN 'r' END,
           CASE WHEN has_table_privilege('anon', c.oid, 'INSERT') THEN 'a' END,
           CASE WHEN has_table_privilege('anon', c.oid, 'UPDATE') THEN 'w' END,
           CASE WHEN has_table_privilege('anon', c.oid, 'DELETE') THEN 'd' END,
           CASE WHEN has_table_privilege('anon', c.oid, 'TRUNCATE') THEN 'D' END) AS k
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relkind IN ('r','v','m','p')
),
funcs AS (  -- functions in public: signature + ACL + security definer flag
  SELECT p.oid::regprocedure::text || ':' || coalesce(p.proacl::text, '-') || ':' || p.prosecdef AS k
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public'
),
pols AS (   -- RLS policies
  SELECT schemaname || '.' || tablename || ':' || policyname || ':' || cmd || ':'
         || array_to_string(roles, ',') || ':' || coalesce(qual, '') || ':' || coalesce(with_check, '') AS k
  FROM pg_policies
),
defacl AS ( -- DEFAULT PRIVILEGES (CASE-2026-09-22 hazard)
  SELECT pg_get_userbyid(d.defaclrole) || ':' || coalesce(n.nspname, '*') || ':' || d.defaclobjtype::text
         || ':' || d.defaclacl::text AS k
  FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid = d.defaclnamespace
),
schemas AS (
  SELECT nspname || ':' || coalesce(nspacl::text, '-') AS k
  FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema'
),
trig AS (   -- non-internal triggers in public
  SELECT c.relname || ':' || t.tgname || ':' || t.tgenabled::text AS k
  FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE NOT t.tgisinternal AND n.nspname = 'public'
),
anon_role AS (
  SELECT 'anon:' || coalesce(array_to_string(r.rolconfig, ','), '-') || ':' || r.rolbypassrls AS k
  FROM pg_roles r WHERE r.rolname = 'anon'
)
SELECT 'relations'      AS what, count(*) AS n, md5(string_agg(k, '|' ORDER BY k)) AS fp FROM rels
UNION ALL SELECT 'anon_public_privs', count(*), md5(string_agg(k, '|' ORDER BY k)) FROM anon_rels
UNION ALL SELECT 'anon_writable_objs', count(*) FILTER (WHERE k ~ ':.*[awdD]'), NULL FROM anon_rels
UNION ALL SELECT 'public_functions',   count(*), md5(string_agg(k, '|' ORDER BY k)) FROM funcs
UNION ALL SELECT 'rls_policies',       count(*), md5(string_agg(k, '|' ORDER BY k)) FROM pols
UNION ALL SELECT 'default_privileges', count(*), md5(string_agg(k, '|' ORDER BY k)) FROM defacl
UNION ALL SELECT 'schemas',            count(*), md5(string_agg(k, '|' ORDER BY k)) FROM schemas
UNION ALL SELECT 'public_triggers',    count(*), md5(string_agg(k, '|' ORDER BY k)) FROM trig
UNION ALL SELECT 'anon_role',          count(*), md5(string_agg(k, '|' ORDER BY k)) FROM anon_role
ORDER BY 1;
