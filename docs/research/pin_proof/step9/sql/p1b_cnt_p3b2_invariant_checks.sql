EXPLAIN SELECT count(*) AS n FROM public.p3b2_invariant_checks WHERE symbol='NIFTY' AND ts >= '2026-08-27 00:00:00+05:30'::timestamptz AND ts < '2026-08-28 00:00:00+05:30'::timestamptz;
