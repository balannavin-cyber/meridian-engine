-- ANON FINAL REVOKE (engine stream, 2026-11-03 22:36 IST, operator, Supabase SQL editor, ONE execution).
-- After the same-origin proxy went live (Marketview reads as marketview_ro, 0 requests to supabase.co), anon needs no table grant.
-- Before: 48 SELECT (Phase 1). After: 0. Verified anon_select_remaining = 0; outside check with the old anon key: 401 on
-- gex_strike_snapshots, v_pin_board, capital_tracker. Rollback: sql/2026-11-03_s104_anon_final_revoke_ROLLBACK.sql (separate file).
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

SELECT count(*) AS anon_select_remaining
FROM information_schema.role_table_grants
WHERE grantee = 'anon' AND table_schema = 'public' AND privilege_type = 'SELECT';
