-- S103-J / R20 / TD-S97-NEW-13 -- the previous session's close, with a stated fallback. One additive view; nothing is written to any table.
--
-- Why: the board read the previous close as the first dhan_idx_i row in 16:00-16:10 IST (board.ts useOpenGap). On 2026-10-21 the
-- 16:00 capture failed (Dhan 806), so the board said "prev close missing" although the 08:50 reconciler had written the close
-- (dhan_charts_historical, 15:29 IST, NIFTY 22811.35 / SENSEX 73709.69). Measured 2026-10-30 (12-day read): on every day with
-- both, the 16:00 dhan_idx_i spot = the 15:40 chain spot to the paisa (diff 0.00, 7 NIFTY / 7 SENSEX days).
--
-- The view returns the qualifying close prints only -- about two rows per symbol per day -- ranked: 1 = dhan_idx_i 16:00-16:10
-- (what the board reads today), 2 = dhan_charts_historical 15:29-15:31 (the reconciler's close). The reader takes the lowest
-- rank for the date it wants, so the 16:00 print always wins and the fallback is used only when it is absent. No DISTINCT ON
-- inside the view, so the board's ts range is pushed down to the base table's index (anon statement_timeout = 3 s).
-- security_invoker = true, as the _1pct wrappers: grants nothing its reader does not already have.
--
-- Operator action, SQL editor. Run BLOCK 1 as one execution. Then T1-T3, each on its own. No rollback in this file (S103 rule:
-- the rollback is given only inside a refusing block, in a later message).

-- =====================================================================  BLOCK 1
CREATE VIEW public.v_close_print WITH (security_invoker = true) AS
SELECT m.symbol, m.ts, m.spot, m.source_table,
       CASE WHEN m.source_table = 'dhan_idx_i' THEN 1 ELSE 2 END AS close_rank
FROM public.market_spot_snapshots m
WHERE (m.source_table = 'dhan_idx_i'
       AND (m.ts AT TIME ZONE 'Asia/Kolkata')::time >= time '16:00'
       AND (m.ts AT TIME ZONE 'Asia/Kolkata')::time <  time '16:10')
   OR (m.source_table = 'dhan_charts_historical'
       AND (m.ts AT TIME ZONE 'Asia/Kolkata')::time >= time '15:29'
       AND (m.ts AT TIME ZONE 'Asia/Kolkata')::time <  time '15:31');

REVOKE ALL ON public.v_close_print FROM anon, authenticated;
GRANT SELECT ON public.v_close_print TO anon, merdian_ro;

COMMENT ON VIEW public.v_close_print IS
  'S103-J / R20 -- previous-close prints. close_rank 1 = dhan_idx_i 16:00-16:10 IST (the official close, equal to the 15:40 chain spot); '
  'close_rank 2 = dhan_charts_historical 15:29-15:31 IST (the 08:50 reconciler''s close, used only when rank 1 is absent for the date). '
  'Reader: per symbol and session date take the lowest close_rank, then the earliest ts. security_invoker = true.';

-- =====================================================================  T1 -- new rule vs the board's old rule, per symbol per day
-- PASS: 18 rows today (9 dates x 2 symbols, 14-day window). same = true on every row whose source_table = dhan_idx_i;
-- the two 2026-10-21 rows (NIFTY, SENSEX) have source_table = dhan_charts_historical, old_spot NULL, same = false (the fixed case).
WITH new AS (
  SELECT DISTINCT ON (symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date)
         symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d, spot, source_table
  FROM public.v_close_print
  WHERE ts >= now() - interval '14 days'
  ORDER BY symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date, close_rank, ts),
old AS (
  SELECT DISTINCT ON (symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date)
         symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date AS d, spot
  FROM public.market_spot_snapshots
  WHERE source_table = 'dhan_idx_i' AND ts >= now() - interval '14 days'
    AND (ts AT TIME ZONE 'Asia/Kolkata')::time >= time '16:00'
    AND (ts AT TIME ZONE 'Asia/Kolkata')::time <  time '16:10'
  ORDER BY symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date, ts)
SELECT n.symbol, n.d, n.source_table, n.spot AS new_spot, o.spot AS old_spot,
       (n.spot IS NOT DISTINCT FROM o.spot) AS same
FROM new n LEFT JOIN old o USING (symbol, d)
ORDER BY n.symbol, n.d DESC;

-- =====================================================================  T2 -- the board's own role reads it, and quickly
-- T1 runs as postgres and bypasses RLS; a view anon cannot read returns HTTP 200 with zero rows (TD-S81-NEW-5).
-- ONE execution. PASS: role_now = anon; n_rows = 18; ms < 500.
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now, count(*) AS n_rows
FROM public.v_close_print WHERE ts >= now() - interval '14 days';
COMMIT;

-- =====================================================================  T3 -- privileges and invoker setting
-- PASS: one row; anon_sel t, anon_ins f, auth_sel f, ro_sel t, invoker t, has_comment t.
SELECT c.relname,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_sel,
       has_table_privilege('anon', c.oid, 'INSERT') AS anon_ins,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_sel,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_sel,
       coalesce('security_invoker=true' = ANY (c.reloptions), false) AS invoker,
       obj_description(c.oid, 'pg_class') IS NOT NULL AS has_comment
FROM pg_class c JOIN pg_namespace s ON s.oid = c.relnamespace
WHERE s.nspname = 'public' AND c.relname = 'v_close_print' AND c.relkind = 'v';
