-- S90 R1.5 — daily health report over the S90 spine (ADR-031 D2/D7). Read-only views.
-- SQL editor, postgres, ONE execution. Additive: two views, no table touched.
-- security_invoker: the view runs with the CALLER's rights, so RLS on cycle_health /
-- script_execution_log still applies (a definer view would bypass it). anon/authenticated
-- revoked explicitly: Supabase default privileges would otherwise grant them (R01-F8).
BEGIN;

-- Per IST day x product: status mix and SLO (CLOSED excluded from the denominator).
CREATE OR REPLACE VIEW public.v_cycle_health_daily
WITH (security_invoker = true) AS
SELECT
  (h.cycle_ts AT TIME ZONE 'Asia/Kolkata')::date                      AS day_ist,
  h.product,
  count(*)                                                            AS cycles,
  count(*) FILTER (WHERE h.status = 'OK')                             AS ok,
  count(*) FILTER (WHERE h.status = 'DEGRADED')                       AS degraded,
  count(*) FILTER (WHERE h.status = 'STALE')                          AS stale,
  count(*) FILTER (WHERE h.status = 'MISSING')                        AS missing,
  count(*) FILTER (WHERE h.status = 'NOT_COMPUTED')                   AS not_computed,
  count(*) FILTER (WHERE h.status = 'UNKNOWN')                        AS unknown,
  count(*) FILTER (WHERE h.status = 'CLOSED')                         AS closed,
  round(100.0 * count(*) FILTER (WHERE h.status = 'OK')
        / NULLIF(count(*) FILTER (WHERE h.status <> 'CLOSED'), 0), 1) AS slo_ok_pct,
  5 * count(*) FILTER (WHERE h.status NOT IN ('OK', 'CLOSED'))        AS minutes_not_ok,
  to_char(min(h.cycle_ts) FILTER (WHERE h.status NOT IN ('OK', 'CLOSED'))
          AT TIME ZONE 'Asia/Kolkata', 'HH24:MI')                     AS first_not_ok_ist,
  to_char(max(h.cycle_ts) FILTER (WHERE h.status NOT IN ('OK', 'CLOSED'))
          AT TIME ZONE 'Asia/Kolkata', 'HH24:MI')                     AS last_not_ok_ist,
  (array_agg(h.reason ORDER BY h.cycle_ts DESC)
     FILTER (WHERE h.status NOT IN ('OK', 'CLOSED')))[1]              AS latest_reason,
  count(DISTINCT h.checker_version)                                   AS checker_versions
FROM public.cycle_health h
GROUP BY 1, 2;

COMMENT ON VIEW public.v_cycle_health_daily IS
  'S90 R1.5 (ADR-031 D2). Per IST day and product: status counts, slo_ok_pct = OK / non-CLOSED cycles, minutes_not_ok at the 5-minute cadence, first/last non-OK time and the latest reason. Source: cycle_health (R1.2 runner, shadow). security_invoker.';

-- Per IST day x script: the run ledger (ADR-031 D7), every scheduled writer that logs.
CREATE OR REPLACE VIEW public.v_run_ledger_daily
WITH (security_invoker = true) AS
SELECT
  l.trade_date                                                        AS day_ist,
  l.script_name,
  count(*)                                                            AS runs,
  count(*) FILTER (WHERE l.exit_reason = 'SUCCESS')                   AS success,
  count(*) FILTER (WHERE l.exit_code <> 0)                            AS failed,
  count(*) FILTER (WHERE l.contract_met IS FALSE)                     AS contract_missed,
  string_agg(DISTINCT l.exit_reason, ',')                             AS exit_reasons,
  to_char(min(l.started_at) AT TIME ZONE 'Asia/Kolkata', 'HH24:MI')   AS first_ist,
  to_char(max(l.started_at) AT TIME ZONE 'Asia/Kolkata', 'HH24:MI')   AS last_ist,
  (array_agg(left(l.error_message, 200) ORDER BY l.started_at DESC)
     FILTER (WHERE l.exit_code <> 0))[1]                              AS latest_error
FROM public.script_execution_log l
GROUP BY 1, 2;

COMMENT ON VIEW public.v_run_ledger_daily IS
  'S90 R1.5 / R0.7 (ADR-031 D7). Per IST trade_date and script: runs, successes, failures, contract misses, exit reasons, latest error. Source: script_execution_log. security_invoker.';

REVOKE ALL ON public.v_cycle_health_daily, public.v_run_ledger_daily FROM anon, authenticated;
GRANT SELECT ON public.v_cycle_health_daily, public.v_run_ledger_daily TO merdian_ro;
COMMIT;

-- Evidence (last result shown): access state of both views.
SELECT c.relname,
       (SELECT option_value FROM pg_options_to_table(c.reloptions) WHERE option_name = 'security_invoker') AS security_invoker,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_select
FROM pg_class c
WHERE c.oid IN ('public.v_cycle_health_daily'::regclass, 'public.v_run_ledger_daily'::regclass);
