-- S100-K (2026-10-24, operator, Supabase SQL editor): TD-S94-NEW-1 audit residual. A merdian_ro_select policy on every
-- public RLS table with no SELECT/ALL policy reaching merdian_ro (as S94's 2026-10-10 DO block). Refuses unless the
-- set is exactly the 51 measured at ~10:01 IST, and rolls back unless the audit count is 0 afterwards.
-- Applied ~10:04 IST: committed (audit 0); merdian_ro_select policies 56 = 51 new + 5 earlier (data_contamination_ranges,
-- participant_oi_daily [S94], dhan_token_probe_log, gamma_metrics, gex_strike_snapshots). roq.sh 10:05 IST:
-- market_breadth_intraday / hist_option_greeks_1m / basis_context_snapshots 0 -> 1000 (LIMIT 1000), control equity_eod 1000.
BEGIN;
DO $$
DECLARE t text; n_before int; n_after int; done int := 0;
BEGIN
  CREATE TEMP TABLE s100k_set ON COMMIT DROP AS
  SELECT c.relname::text AS relname
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public' AND c.relkind IN ('r','p') AND c.relrowsecurity
     AND NOT EXISTS (
           SELECT 1 FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname
              AND p.cmd IN ('SELECT','ALL')
              AND EXISTS (SELECT 1 FROM unnest(p.roles) r
                           WHERE r = 'public' OR (r IN (SELECT rolname FROM pg_roles) AND pg_has_role('merdian_ro', r, 'MEMBER'))));
  SELECT count(*) INTO n_before FROM s100k_set;
  IF n_before <> 51 THEN RAISE EXCEPTION 'S100-K REFUSED: set is % tables, expected 51 -- nothing applied', n_before; END IF;
  FOR t IN SELECT relname FROM s100k_set ORDER BY 1 LOOP
    EXECUTE format('CREATE POLICY merdian_ro_select ON public.%I FOR SELECT TO merdian_ro USING (true)', t);
    done := done + 1;
  END LOOP;
  SELECT count(*) INTO n_after
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public' AND c.relkind IN ('r','p') AND c.relrowsecurity
     AND NOT EXISTS (
           SELECT 1 FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname
              AND p.cmd IN ('SELECT','ALL')
              AND EXISTS (SELECT 1 FROM unnest(p.roles) r
                           WHERE r = 'public' OR (r IN (SELECT rolname FROM pg_roles) AND pg_has_role('merdian_ro', r, 'MEMBER'))));
  IF n_after <> 0 THEN RAISE EXCEPTION 'S100-K FAIL: % tables still unreadable after % policies -- rolled back', n_after, done; END IF;
  RAISE NOTICE 'S100-K: % policies created, audit count now 0', done;
END $$;
COMMIT;
SELECT count(*) AS merdian_ro_select_policies,
       count(*) FILTER (WHERE tablename IN ('market_breadth_intraday','hist_option_greeks_1m','basis_context_snapshots')) AS probe_tables
  FROM pg_policies WHERE schemaname = 'public' AND policyname = 'merdian_ro_select';
