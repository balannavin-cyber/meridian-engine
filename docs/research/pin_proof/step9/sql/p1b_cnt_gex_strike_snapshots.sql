EXPLAIN SELECT count(*) AS n FROM public.gex_strike_snapshots WHERE symbol='NIFTY' AND ts >= '2026-08-27 00:00:00+05:30'::timestamptz AND ts < '2026-08-28 00:00:00+05:30'::timestamptz;
