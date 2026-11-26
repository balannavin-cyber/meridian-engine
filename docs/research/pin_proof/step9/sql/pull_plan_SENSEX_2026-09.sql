
SELECT row_to_json(t)::text AS j FROM (
  SELECT (ts AT TIME ZONE 'Asia/Kolkata')::date::text AS day,
         'SENSEX' AS symbol, count(*) AS n_runs
  FROM public.gex_run_v2
  WHERE symbol = 'SENSEX'
    AND ts >= '2026-09-01 00:00:00+05:30'::timestamptz AND ts < '2026-10-01 00:00:00+05:30'::timestamptz
    AND rule_version = 'v2-1.2-gss'
  GROUP BY 1 ORDER BY 1
) t;
