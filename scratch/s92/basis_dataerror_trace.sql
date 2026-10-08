-- S92: END-TO-END TRACE. For each compute_basis_context_local.py run today,
-- find the row that WOULD have been rows[0] (newest index_futures_snapshots in
-- its 30-min lookback, at or before the run start) and report that row's
-- rendered fraction width. READ-ONLY.
--
-- WHAT WOULD MAKE THIS FAIL: a DATA_ERROR run whose rows[0] width is 0/3/6
-- (parses fine) would mean the fraction is NOT its cause. A SUCCESS run whose
-- rows[0] width is in {1,2,4,5} would mean a failing width does not produce the
-- failure. Either one refutes the mechanism. Both columns are printed for every
-- run, so the table can show either.
WITH runs AS (
  SELECT started_at, exit_reason, exit_code
  FROM script_execution_log
  WHERE script_name = 'compute_basis_context_local.py'
    AND started_at >= TIMESTAMPTZ '2026-10-08 03:00:00+00'
    AND started_at <  TIMESTAMPTZ '2026-10-08 10:15:00+00'
),
pick AS (
  SELECT r.started_at, r.exit_reason, r.exit_code,
         (SELECT f.ts FROM index_futures_snapshots f
           WHERE f.symbol = 'NIFTY'
             AND f.ts >= r.started_at - INTERVAL '30 minutes'
             AND f.ts <= r.started_at
           ORDER BY f.ts DESC LIMIT 1) AS row0_ts
  FROM runs r
)
SELECT to_char(started_at AT TIME ZONE 'Asia/Kolkata','HH24:MI:SS') AS run_ist,
       exit_reason,
       exit_code,
       CASE WHEN row0_ts IS NULL THEN '(no row in window)'
            ELSE to_char(row0_ts AT TIME ZONE 'Asia/Kolkata','HH24:MI:SS') END AS row0_ist,
       CASE WHEN row0_ts IS NULL THEN NULL ELSE to_char(row0_ts,'US') END       AS stored_us,
       CASE WHEN row0_ts IS NULL THEN NULL
            WHEN to_char(row0_ts,'US')='000000' THEN 0
            ELSE length(rtrim(to_char(row0_ts,'US'),'0')) END                   AS width,
       CASE WHEN row0_ts IS NULL THEN 'n/a -- no input'
            WHEN (CASE WHEN to_char(row0_ts,'US')='000000' THEN 0
                       ELSE length(rtrim(to_char(row0_ts,'US'),'0')) END) IN (1,2,4,5)
                 THEN 'WOULD RAISE'
            ELSE 'parses' END                                                   AS py310
FROM pick
WHERE exit_reason <> 'SUCCESS'
ORDER BY started_at;

-- And the complement: SUCCESS runs whose rows[0] width is in {1,2,4,5}.
-- A non-zero count here REFUTES the mechanism. Expected: 0.
WITH runs AS (
  SELECT started_at, exit_reason
  FROM script_execution_log
  WHERE script_name = 'compute_basis_context_local.py'
    AND started_at >= TIMESTAMPTZ '2026-10-08 03:00:00+00'
    AND started_at <  TIMESTAMPTZ '2026-10-08 10:15:00+00'
    AND exit_reason = 'SUCCESS'
),
pick AS (
  SELECT r.started_at,
         (SELECT f.ts FROM index_futures_snapshots f
           WHERE f.symbol = 'NIFTY'
             AND f.ts >= r.started_at - INTERVAL '30 minutes'
             AND f.ts <= r.started_at
           ORDER BY f.ts DESC LIMIT 1) AS row0_ts
  FROM runs r
)
SELECT count(*) AS success_runs,
       count(*) FILTER (WHERE row0_ts IS NOT NULL
         AND (CASE WHEN to_char(row0_ts,'US')='000000' THEN 0
                   ELSE length(rtrim(to_char(row0_ts,'US'),'0')) END) IN (1,2,4,5))
         AS success_with_failing_width_REFUTES
FROM pick;
