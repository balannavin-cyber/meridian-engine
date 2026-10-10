-- S94 (2026-10-10) — read policies for merdian_ro on two RLS tables that had RLS ON and ZERO policies.
-- APPLIED 2026-10-10 ~08:32 IST by the operator in the Supabase SQL editor (one execution).
--
-- Measured before: merdian_ro read 0 rows from participant_oi_daily (control gamma_metrics: 1000);
--   pg_class.relrowsecurity = t and pg_policies empty on both tables below.
-- Measured after (bin/roq.sh): participant_oi_daily 1700, data_contamination_ranges 1.
-- Basis: ADR-031 D6 (RLS on + a merdian_ro SELECT policy); same pattern as S90 on script_execution_log.
-- Consequence recorded as TD-S94-NEW-1: before this, every Rule 13 check run through bin/roq.sh
--   read an empty contamination registry regardless of its contents.
-- Idempotent; additive; grants no write and nothing to anon/authenticated.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                 AND tablename='participant_oi_daily' AND policyname='merdian_ro_select') THEN
    EXECUTE 'CREATE POLICY merdian_ro_select ON public.participant_oi_daily FOR SELECT TO merdian_ro USING (true)';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public'
                 AND tablename='data_contamination_ranges' AND policyname='merdian_ro_select') THEN
    EXECUTE 'CREATE POLICY merdian_ro_select ON public.data_contamination_ranges FOR SELECT TO merdian_ro USING (true)';
  END IF;
END $$;

-- Read-back (expect 2 rows: merdian_ro_select, {merdian_ro}, SELECT)
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname='public' AND tablename IN ('participant_oi_daily','data_contamination_ranges')
ORDER BY 1;
