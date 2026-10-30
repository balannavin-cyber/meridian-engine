-- S102 / tracker 2.2 B1 R40 -- v_market_ticks_eq_latest: the newest non-NULL EQ last_price per stock in the
-- last 10 minutes, read by ingest_breadth_from_ticks.py (S102_R40_LATEST_VIEW) in place of paging every EQ tick.
--
-- Why: the writer paged ~161,000 EQ ticks per run by offset (~162 calls) to keep one tick per stock in
-- Python; runs took 140-176 s on a 1-minute cron, so ~3 copies ran at once all session (379 of 431 runs
-- > 60 s on 2026-10-26 and 10-27). This query, EXPLAIN ANALYZE 2026-10-28 11:17 IST: 1,313 rows from
-- 161,806 in 406.6 ms (bitmap scan on idx_market_ticks_ts, external sort 5.8 MB).
--
-- Key and rule are the writer's own: sym = COALESCE(NULLIF(tradingsymbol,''), symbol) (Python's
-- `tradingsymbol or symbol`); the first tick in ts-desc order that has a last_price (Python skipped a
-- NULL last_price and kept looking). Window 10 minutes = TICK_WINDOW_MINUTES in the writer; change both
-- together. Ties on equal ts within one stock are unordered here, as they were in Python.
--
-- Operator action, SQL editor. Run the DDL block, then the verification SELECT on its own.

CREATE OR REPLACE VIEW public.v_market_ticks_eq_latest
WITH (security_invoker = false) AS
SELECT DISTINCT ON (COALESCE(NULLIF(t.tradingsymbol, ''), t.symbol))
       COALESCE(NULLIF(t.tradingsymbol, ''), t.symbol) AS sym,
       t.last_price,
       t.ts
FROM public.market_ticks t
WHERE t.instrument_type = 'EQ'
  AND t.ts >= now() - interval '10 minutes'
  AND t.last_price IS NOT NULL
  AND COALESCE(NULLIF(t.tradingsymbol, ''), t.symbol) <> ''
ORDER BY COALESCE(NULLIF(t.tradingsymbol, ''), t.symbol), t.ts DESC;

COMMENT ON VIEW public.v_market_ticks_eq_latest IS
  'S102 R40 -- newest non-NULL last_price per EQ stock (sym = COALESCE(NULLIF(tradingsymbol,''''), symbol)) over the last 10 minutes of market_ticks. Read by ingest_breadth_from_ticks.py (keyset on sym) in place of paging every EQ tick. Window must equal the writer''s TICK_WINDOW_MINUTES. Owner privileges (security_invoker = false); not readable by anon or authenticated.';

REVOKE ALL ON public.v_market_ticks_eq_latest FROM anon, authenticated;
GRANT SELECT ON public.v_market_ticks_eq_latest TO service_role, merdian_ro;

-- Verification (run on its own after the block above). PASS: rows_now 1,000-1,400 in session (0 outside it),
-- one row per sym, anon/authenticated false, service_role/merdian_ro true, comment present.
-- SELECT (SELECT count(*) FROM public.v_market_ticks_eq_latest)                    AS rows_now,
--        (SELECT count(DISTINCT sym) FROM public.v_market_ticks_eq_latest)        AS distinct_sym,
--        has_table_privilege('anon',          'public.v_market_ticks_eq_latest', 'SELECT') AS anon_sel,
--        has_table_privilege('authenticated', 'public.v_market_ticks_eq_latest', 'SELECT') AS auth_sel,
--        has_table_privilege('service_role',  'public.v_market_ticks_eq_latest', 'SELECT') AS svc_sel,
--        has_table_privilege('merdian_ro',    'public.v_market_ticks_eq_latest', 'SELECT') AS ro_sel,
--        obj_description('public.v_market_ticks_eq_latest'::regclass, 'pg_class') IS NOT NULL AS has_comment;
