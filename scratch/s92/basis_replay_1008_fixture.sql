-- S92 build #2, step 4c fixture. READ-ONLY.
-- For each compute_basis_context_local.py run on 2026-10-08, reconstruct the two
-- index_futures_snapshots rows the real invocation would have seen:
--   row0 = newest row at or before the run start, within the 30-min lookback
--   prev = newest row at least MIN_GAP_MIN (5) older than row0, same window
-- rendered in the EXACT PostgREST wire form, so the replay parses the same bytes
-- the live run did.
--
-- THE WIRE-FORM RECONSTRUCTION is the load-bearing step and it was validated at
-- string level before being trusted: stored 312290 -> '.31229' and 555900 ->
-- '.5559' were read off PostgREST and matched this expression exactly.
\pset format csv
\pset footer off
WITH runs AS (
  SELECT started_at, exit_reason, exit_code
  FROM script_execution_log
  WHERE script_name = 'compute_basis_context_local.py'
    AND started_at >= TIMESTAMPTZ '2026-10-08 03:00:00+00'
    AND started_at <  TIMESTAMPTZ '2026-10-08 10:15:00+00'
),
w AS (
  SELECT r.started_at, r.exit_reason, r.exit_code,
         f.ts, f.spot_price, f.futures_price, f.basis, f.basis_pct,
         row_number() OVER (PARTITION BY r.started_at ORDER BY f.ts DESC) AS rn
  FROM runs r
  LEFT JOIN index_futures_snapshots f
    ON f.symbol = 'NIFTY'
   AND f.ts >= r.started_at - INTERVAL '30 minutes'
   AND f.ts <= r.started_at
),
row0 AS (SELECT * FROM w WHERE rn = 1),
prev AS (
  SELECT r.started_at, f.ts, f.spot_price, f.futures_price, f.basis, f.basis_pct,
         row_number() OVER (PARTITION BY r.started_at ORDER BY f.ts DESC) AS rn
  FROM row0 r
  LEFT JOIN index_futures_snapshots f
    ON f.symbol = 'NIFTY'
   AND f.ts >= r.started_at - INTERVAL '30 minutes'
   AND f.ts <= r.ts - INTERVAL '5 minutes'
),
wire AS (
  SELECT ts,
         to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
         || CASE WHEN to_char(ts,'US') = '000000' THEN ''
                 ELSE '.' || rtrim(to_char(ts,'US'),'0') END
         || '+00:00' AS s
  FROM (SELECT ts FROM row0 WHERE ts IS NOT NULL
        UNION SELECT ts FROM prev WHERE rn = 1 AND ts IS NOT NULL) u
)
SELECT to_char(a.started_at AT TIME ZONE 'Asia/Kolkata','HH24:MI:SS') AS run_ist,
       a.exit_reason                                       AS today_reason,
       a.exit_code                                         AS today_exit,
       coalesce(w0.s, '')                                  AS row0_wire,
       coalesce(a.spot_price::text, '')                    AS row0_spot,
       coalesce(a.futures_price::text, '')                 AS row0_fut,
       coalesce(a.basis::text, '')                         AS row0_basis,
       coalesce(a.basis_pct::text, '')                     AS row0_basis_pct,
       coalesce(wp.s, '')                                  AS prev_wire,
       coalesce(p.spot_price::text, '')                    AS prev_spot,
       coalesce(p.futures_price::text, '')                 AS prev_fut,
       coalesce(p.basis::text, '')                         AS prev_basis,
       coalesce(p.basis_pct::text, '')                     AS prev_basis_pct
FROM row0 a
LEFT JOIN wire w0 ON w0.ts = a.ts
LEFT JOIN prev p  ON p.started_at = a.started_at AND p.rn = 1
LEFT JOIN wire wp ON wp.ts = p.ts
ORDER BY a.started_at;
