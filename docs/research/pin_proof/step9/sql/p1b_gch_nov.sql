EXPLAIN SELECT count(*) AS n FROM public.gex_cycle_history WHERE symbol='NIFTY' AND ts >= '2026-11-25 00:00:00+05:30'::timestamptz AND ts < '2026-11-26 00:00:00+05:30'::timestamptz;
