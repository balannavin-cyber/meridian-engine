SELECT count(*) AS n_rows, count(run_id) AS n_nonnull_run, count(DISTINCT run_id) AS n_distinct_run,
       count(DISTINCT expiry_date) AS n_expiry, count(net_gex) AS n_net_gex_nonnull
FROM public.gamma_metrics
WHERE symbol='NIFTY' AND ts >= '2026-08-27 00:00:00+05:30'::timestamptz
  AND ts < '2026-08-28 00:00:00+05:30'::timestamptz;
