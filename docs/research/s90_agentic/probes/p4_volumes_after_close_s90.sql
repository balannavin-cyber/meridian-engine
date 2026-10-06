-- S90 R0.1 / R1.9 — volumes and continuity. RUN AFTER 15:45 IST (heavier reads).
-- Window: the last 5 sessions, 2026-09-28 .. 2026-10-05 (IST), bounded by ts.
-- Run:  bin/roq.sh scratch/s90/p4_volumes_after_close_s90.sql > scratch/s90/p4_volumes_after_close_s90.out 2>&1
\pset pager off
\pset null '(null)'
SELECT current_user AS role_now, now() AS probed_at;

-- Rows, distinct ts, distinct spot per IST day per symbol. distinct_spot is
-- the TD-S89-NEW-1 tell: a frozen day passes rows and ts, fails spot.
SELECT 'option_chain_snapshots' AS rel, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist, symbol,
       count(*) AS n_rows, count(DISTINCT ts) AS n_ts, count(DISTINCT expiry_date) AS n_expiries,
       count(DISTINCT run_id) AS n_runs, count(DISTINCT spot) AS distinct_spot
FROM public.option_chain_snapshots
WHERE ts >= '2026-09-27 18:30+00' AND ts < '2026-10-05 18:30+00'
GROUP BY 2,3 ORDER BY 2,3;

SELECT 'market_spot_snapshots' AS rel, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist, symbol,
       source_table, count(*) AS n_rows, count(DISTINCT spot) AS distinct_spot,
       min(ts AT TIME ZONE 'Asia/Kolkata')::time AS first_ist, max(ts AT TIME ZONE 'Asia/Kolkata')::time AS last_ist
FROM public.market_spot_snapshots
WHERE ts >= '2026-09-27 18:30+00' AND ts < '2026-10-05 18:30+00'
GROUP BY 2,3,4 ORDER BY 2,3,4;

SELECT 'gamma_metrics' AS rel, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist, symbol,
       count(*) AS n_rows, count(DISTINCT ts) AS n_ts, count(DISTINCT expiry_date) AS n_expiries,
       count(DISTINCT raw->>'builder_version') AS n_builder_versions,
       max(raw->>'builder_version') AS builder_version
FROM public.gamma_metrics
WHERE ts >= '2026-09-27 18:30+00' AND ts < '2026-10-05 18:30+00'
GROUP BY 2,3 ORDER BY 2,3;

SELECT 'gex_strike_snapshots' AS rel, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist, symbol,
       count(*) AS n_rows, count(DISTINCT ts) AS n_ts, count(DISTINCT run_id) AS n_runs,
       count(DISTINCT expiry_date) AS n_expiries
FROM public.gex_strike_snapshots
WHERE ts >= '2026-09-27 18:30+00' AND ts < '2026-10-05 18:30+00'
GROUP BY 2,3 ORDER BY 2,3;

SELECT 'volatility_snapshots' AS rel, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist, symbol,
       count(*) AS n_rows, count(DISTINCT ts) AS n_ts, count(DISTINCT source_run_id) AS n_src_runs
FROM public.volatility_snapshots
WHERE ts >= '2026-09-27 18:30+00' AND ts < '2026-10-05 18:30+00'
GROUP BY 2,3 ORDER BY 2,3;

-- market_ticks: by day and instrument_type only (largest table; ts-indexed).
SELECT 'market_ticks' AS rel, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist,
       instrument_type, count(*) AS n_rows
FROM public.market_ticks
WHERE ts >= '2026-09-27 18:30+00' AND ts < '2026-10-05 18:30+00'
GROUP BY 2,3 ORDER BY 2,3;

-- Oldest row per core table: is retention acting? (jobid 19 measured inactive.)
SELECT 'option_chain_snapshots' AS rel, min(ts) AS oldest FROM public.option_chain_snapshots
UNION ALL SELECT 'gamma_metrics', min(ts) FROM public.gamma_metrics
UNION ALL SELECT 'gex_strike_snapshots', min(ts) FROM public.gex_strike_snapshots
UNION ALL SELECT 'volatility_snapshots', min(ts) FROM public.volatility_snapshots
UNION ALL SELECT 'market_spot_snapshots', min(ts) FROM public.market_spot_snapshots;

-- trading_calendar, next 30 days. Absent weekdays matter: the ingest's
-- inline gate (ingest_option_chain_local.py:293-327) reads NO ROW as OPEN.
SELECT d::date AS day, to_char(d,'Dy') AS dow, tc.is_open, tc.open_time, tc.notes
FROM generate_series('2026-10-05'::date, '2026-11-04'::date, '1 day') d
LEFT JOIN public.trading_calendar tc ON tc.trade_date = d::date
ORDER BY 1;
