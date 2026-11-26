EXPLAIN SELECT count(*) AS n, count(DISTINCT run_id) AS n_run
FROM public.gamma_metrics
WHERE symbol='NIFTY' AND ts >= '2026-08-27 00:00:00+05:30'::timestamptz
  AND ts < '2026-08-28 00:00:00+05:30'::timestamptz;
