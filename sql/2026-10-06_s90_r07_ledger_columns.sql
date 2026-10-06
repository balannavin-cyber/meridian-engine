-- S90 R0.7 (ADR-031 D7.1) — ledger columns on script_execution_log. Additive.
-- SQL editor, postgres, ONE execution, AFTER 16:00 IST and BEFORE the ExecutionLog
-- patch is deployed (the patched code sends these columns; old code ignores them).
BEGIN;
ALTER TABLE public.script_execution_log
  ADD COLUMN IF NOT EXISTS kind    text NOT NULL DEFAULT 'run',
  ADD COLUMN IF NOT EXISTS run_id  uuid,
  ADD COLUMN IF NOT EXISTS product text,
  ADD COLUMN IF NOT EXISTS status  public.merdian_status;
ALTER TABLE public.script_execution_log
  ADD CONSTRAINT script_execution_log_kind_ck
  CHECK (kind IN ('run', 'check', 'gap', 'incident', 'ruling', 'model_call'));
CREATE INDEX IF NOT EXISTS ix_script_execution_log_run_id
  ON public.script_execution_log (run_id) WHERE run_id IS NOT NULL;
COMMENT ON COLUMN public.script_execution_log.kind IS 'ADR-031 D7: run | check | gap | incident | ruling | model_call. Existing rows are runs.';
COMMENT ON COLUMN public.script_execution_log.run_id IS 'ADR-031 D7: the cycle run_id (correlation key with gamma_metrics / option_chain_snapshots / volatility_snapshots / gex_cycle_history).';
COMMENT ON COLUMN public.script_execution_log.product IS 'ADR-031 D1: data_contracts.product written by this run (relation:symbol).';
COMMENT ON COLUMN public.script_execution_log.status IS 'ADR-031 D2: status of the product from the run exit (SUCCESS+contract => OK, else DEGRADED; gates => CLOSED; no output => MISSING; CRASH => UNKNOWN).';
-- R0.7 exit: one query traces a board read (a gamma_metrics row) to every run that produced it.
CREATE OR REPLACE VIEW public.v_run_trace
WITH (security_invoker = true) AS
SELECT gm.symbol,
       gm.ts                                                   AS gamma_ts,
       gm.run_id,
       l.script_name,
       l.product,
       l.status,
       l.exit_reason,
       l.contract_met,
       l.git_sha,
       to_char(l.started_at AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS started_ist,
       l.duration_ms
FROM public.gamma_metrics gm
JOIN public.script_execution_log l ON l.run_id = gm.run_id;
COMMENT ON VIEW public.v_run_trace IS 'S90 R0.7 (ADR-031 D7.5): every ledger run carrying a gamma_metrics row''s run_id (ingest, gamma, volatility). Filter by symbol and gamma_ts. security_invoker.';
REVOKE ALL ON public.v_run_trace FROM anon, authenticated;
GRANT SELECT ON public.v_run_trace TO merdian_ro;
-- R0.3 exit, via run_id (ADR-031 D3 as proposed in S90): share of each day's capture/compute
-- runs that trace to a ledger row carrying git_sha. Last 7 IST days; one row per relation x day.
CREATE OR REPLACE VIEW public.v_provenance_coverage_daily
WITH (security_invoker = true) AS
WITH runs AS (
  SELECT 'option_chain_snapshots' AS relation, (ts AT TIME ZONE 'Asia/Kolkata')::date AS day_ist, run_id
  FROM public.option_chain_snapshots WHERE ts >= now() - interval '7 days' GROUP BY 1, 2, 3
  UNION ALL
  SELECT 'gamma_metrics', (ts AT TIME ZONE 'Asia/Kolkata')::date, run_id
  FROM public.gamma_metrics WHERE ts >= now() - interval '7 days'
  UNION ALL
  SELECT 'volatility_snapshots', (ts AT TIME ZONE 'Asia/Kolkata')::date, source_run_id
  FROM public.volatility_snapshots WHERE ts >= now() - interval '7 days'
  UNION ALL
  SELECT 'gex_cycle_history', (ts AT TIME ZONE 'Asia/Kolkata')::date, run_id
  FROM public.gex_cycle_history WHERE ts >= now() - interval '7 days'
)
SELECT r.relation, r.day_ist,
       count(*)                                                        AS runs,
       count(*) FILTER (WHERE EXISTS (
         SELECT 1 FROM public.script_execution_log l
         WHERE l.run_id = r.run_id AND l.git_sha IS NOT NULL))        AS traced,
       round(100.0 * count(*) FILTER (WHERE EXISTS (
         SELECT 1 FROM public.script_execution_log l
         WHERE l.run_id = r.run_id AND l.git_sha IS NOT NULL)) / count(*), 1) AS traced_pct
FROM runs r
GROUP BY 1, 2;
COMMENT ON VIEW public.v_provenance_coverage_daily IS 'S90 R0.3 exit via run_id: runs per relation per IST day that trace to a script_execution_log row with git_sha. Target 100 % for new rows. security_invoker.';
REVOKE ALL ON public.v_provenance_coverage_daily FROM anon, authenticated;
GRANT SELECT ON public.v_provenance_coverage_daily TO merdian_ro;
COMMIT;

-- Evidence (last result shown).
SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS type, a.attnotnull, pg_get_expr(d.adbin, d.adrelid) AS default
FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE a.attrelid = 'public.script_execution_log'::regclass AND a.attname IN ('kind', 'run_id', 'product', 'status')
ORDER BY a.attnum;
