-- S100-H (2026-10-24, applied by the operator in the Supabase SQL editor ~09:26 IST): deactivate the 12 active
-- pg_cron jobs that called the retired Edge Functions (TD-S90-NEW-14: job 37 was the off-box equity_eod cursor
-- writer). Reversible: same call with active := true. Nothing deleted; the functions and their x-cron-secret
-- remain until a later ruling.
--   ingest_option_chain      30 31 33 34 35 36
--   ingest_equity_eod        37   (*/2 10-11 UTC = 15:30-17:28 IST)
--   ingest_breadth_intraday  40 41 42 43 44
-- Result: 12 rows. Verification: deactivated_12 12, active_function_jobs_left 0, active_jobs_total 3 (39, 46, 47).

SELECT j AS jobid, cron.alter_job(job_id := j, active := false) AS altered FROM unnest(ARRAY[30,31,33,34,35,36,37,40,41,42,43,44]) AS j;

-- Verification (run on its own):
SELECT count(*) FILTER (WHERE jobid = ANY(ARRAY[30,31,33,34,35,36,37,40,41,42,43,44]) AND NOT active) AS deactivated_12, count(*) FILTER (WHERE active AND command LIKE '%/functions/v1/%') AS active_function_jobs_left, count(*) FILTER (WHERE active) AS active_jobs_total FROM cron.job;
