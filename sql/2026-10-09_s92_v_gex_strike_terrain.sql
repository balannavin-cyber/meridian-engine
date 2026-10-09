-- =====================================================================
-- 2026-10-09_s92_v_gex_strike_terrain.sql
-- S92 / ruling S92-J -- read surface for the OPTIONAL Marketview 3D view
-- (/board/3d: "γ terrain" and "Pain bowl"; the IV fence reads v_iv_surface
-- through the board's existing hook and needs nothing here).
--   public.v_gex_strike_terrain   grain (symbol, session_date, strike)
-- =====================================================================
--
-- AUTHORED 2026-10-09 (S92). Read-only view; deploys any time. Nothing in
-- this file has been run against the database.
--
-- WHY THIS VIEW EXISTS
--   The operator's 3D experiment (meridian-connect branch lab-3d, 78fb26e,
--   TD-S92-NEW-2) built its surfaces in the browser: ~29 raw reads per load
--   (trading_calendar + two gex_strike_snapshots queries per session), the
--   "settled run" chosen client-side (last run <= 15:30 IST), and max pain
--   recomputed client-side. Ruling S92-G removed exactly that shape from L13:
--   one rule, one implementation, in the database. This view is that
--   implementation for the 3D surfaces; the client reads it and draws.
--
-- NOT A PARITY LAYER and adds no layer to ADR-025. Display-only (S37).
--
-- WHAT IT RETURNS
--   For each symbol, the 14 most recent sessions that hold a GEX run and are
--   not marked closed, newest = session_rank 1. Per session, the SETTLED run.
--   Per run, the front-expiry strikes within +/- 6 % of session 1's settled
--   spot (one common strike axis for the whole surface).
--
-- RULES TAKEN FROM SIBLING VIEWS, NOT INVENTED HERE
--   * Settled run = the last run at or before 15:15 IST of that session
--     (v_gex_net_gamma_river / ENH-126: after 15:15 the index is frozen
--     through the closing auction, ADR-022). Effectively the 15:10 cycle.
--     The lab used 15:30, which would have threaded the auction-frozen
--     spot into every slice. session_complete = a run at or after 15:10 IST,
--     the river's own test.
--   * Closed days: a date is dropped ONLY if trading_calendar holds an
--     explicit is_open = false row for it. A missing row is not a verdict
--     (ADR-020; the river measured the calendar missing a closure), and
--     the writer has run on closed days (2026-06-26, 2026-10-02 -- frozen
--     cycles), which is why an explicit closed row must win.
--   * gex_cr is NULL when the run carries no gamma for that strike
--     (gamma_call and gamma_put both NULL). SENSEX has no gamma on ~30 % of
--     strikes (ADR-024 §A3) and the writer stores 0 there; drawing that as
--     a flat zero would assert a measurement that was never made.
--     NULL is a gap, never a zero.
--   * writer_pain is ENH-123's formula verbatim (v_gex_max_pain):
--     sum(max(K - k, 0) * oi_call) + sum(max(k - K, 0) * oi_put) over ALL of
--     the run's strikes k (OI NULL -> 0), for candidate K. is_max_pain marks
--     the argmin over ALL candidates of the run (ties -> lower strike, as
--     ENH-123), so the marked strike can fall outside the window; then no
--     row in the window carries it and max_pain_strike says where it is.
--
-- ROW COUNT. NIFTY ~ 58 strikes x 14 = ~810 rows; SENSEX ~ 96 x 14 = ~1,350,
--   which exceeds PostgREST's 1,000-row cap (CLAUDE.md rule 15). The client
--   pages with .range(0, 999) / .range(1000, 1999), ORDER BY session_date,
--   strike. Stated here so it is not discovered as a silent truncation.
--
-- APPLY ORDER: Section 1 -> 2 -> 3, verify with Section 4 (each 4x alone).
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS (TD-S81-NEW-5).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_terrain AS
WITH RECURSIVE syms AS (
        SELECT s.symbol FROM (VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol)
     ), back AS (
        -- Step back one IST date at a time from the newest run: one backward
        -- index seek per step on (symbol, ts DESC). 20 steps leave room for
        -- closed days to be dropped and still yield 14 sessions.
        SELECT s.symbol, 1 AS step_n,
               (SELECT (max(g.ts) AT TIME ZONE 'Asia/Kolkata')::date
                  FROM gex_strike_snapshots g WHERE g.symbol = s.symbol) AS d
          FROM syms s
        UNION ALL
        SELECT b.symbol, b.step_n + 1,
               (SELECT (max(g.ts) AT TIME ZONE 'Asia/Kolkata')::date
                  FROM gex_strike_snapshots g
                 WHERE g.symbol = b.symbol
                   AND g.ts < (b.d::timestamp AT TIME ZONE 'Asia/Kolkata'))
          FROM back b
         WHERE b.step_n < 20 AND b.d IS NOT NULL
     ), sessions AS (
        SELECT b.symbol, b.d AS session_date,
               row_number() OVER (PARTITION BY b.symbol ORDER BY b.d DESC) AS session_rank
          FROM back b
         WHERE b.d IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM trading_calendar tc
                            WHERE tc.trade_date = b.d AND tc.is_open = false)
     ), settled AS (
        SELECT s.symbol, s.session_date, s.session_rank, r.run_id, r.ts,
               EXISTS (SELECT 1 FROM gex_strike_snapshots g2
                        WHERE g2.symbol = s.symbol
                          AND g2.ts >= (s.session_date + TIME '15:10') AT TIME ZONE 'Asia/Kolkata'
                          AND g2.ts <  (s.session_date + 1)::timestamp AT TIME ZONE 'Asia/Kolkata')
                 AS session_complete
          FROM sessions s
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts
                 FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol
                  AND g.ts >= s.session_date::timestamp AT TIME ZONE 'Asia/Kolkata'
                  AND g.ts <= (s.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata'
                ORDER BY g.ts DESC
                LIMIT 1) r
         WHERE s.session_rank <= 14
     ), runrows AS (
        SELECT st.symbol, st.session_date, st.session_rank, st.run_id, st.ts, st.session_complete,
               g.expiry_date, g.dte, g.strike, g.spot,
               CASE WHEN g.gamma_call IS NULL AND g.gamma_put IS NULL THEN NULL ELSE g.gex_cr END AS gex_cr,
               g.oi_call, g.oi_put
          FROM settled st
          JOIN gex_strike_snapshots g
            ON g.symbol = st.symbol AND g.run_id = st.run_id
           AND g.ts >= st.ts AND g.ts < st.ts + interval '5 minutes'
     ), fexp AS (                -- front expiry per session: nearest expiry_date >= session date
        SELECT symbol, session_date, min(expiry_date) AS front_expiry
          FROM runrows WHERE expiry_date >= session_date GROUP BY symbol, session_date
     ), front AS (
        SELECT r.*
          FROM runrows r
          JOIN fexp e ON e.symbol = r.symbol AND e.session_date = r.session_date
         WHERE r.expiry_date = e.front_expiry
     ), pain AS (
        -- ENH-123's formula, every candidate K of the run, in O(n) by running sums
        -- instead of ENH-123's O(n^2) self-join (measured 3.5 s on a 14-session
        -- fixture as a self-join). Algebraically identical, exact in numeric:
        --   sum_k max(K-k,0)*oc_k = K*sum_{k<K} oc_k - sum_{k<K} k*oc_k
        --   sum_k max(k-K,0)*op_k = sum_{k>K} k*op_k - K*sum_{k>K} op_k
        -- (the k = K term is zero in both). Section 4c tests the result against
        -- gex_pin_maxpain_history, an independent store.
        SELECT q.*,
               q.strike * COALESCE(sum(q.oc) OVER wlt, 0) - COALESCE(sum(q.strike * q.oc) OVER wlt, 0)
             + COALESCE(sum(q.strike * q.op) OVER wgt, 0) - q.strike * COALESCE(sum(q.op) OVER wgt, 0)
                 AS writer_pain
          FROM (SELECT f.*, COALESCE(f.oi_call, 0)::numeric AS oc, COALESCE(f.oi_put, 0)::numeric AS op
                  FROM front f) q
        WINDOW wlt AS (PARTITION BY q.symbol, q.session_date ORDER BY q.strike
                       ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
               wgt AS (PARTITION BY q.symbol, q.session_date ORDER BY q.strike
                       ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING)
     ), marked AS (
        SELECT p.*,
               -- argmin over ALL candidates of the run; ties -> lower strike (ENH-123)
               first_value(p.strike) OVER (PARTITION BY p.symbol, p.session_date
                                           ORDER BY p.writer_pain, p.strike) AS max_pain_strike,
               -- one strike axis for the whole surface: session 1's settled spot
               max(p.spot) FILTER (WHERE p.session_rank = 1) OVER (PARTITION BY p.symbol) AS axis_spot
          FROM pain p
     )
SELECT m.symbol,
       m.session_date,
       m.session_rank::int                    AS session_rank,
       m.session_complete,
       m.run_id,
       m.ts,
       m.spot,
       m.expiry_date,
       m.dte,
       m.strike,
       m.gex_cr,
       m.oi_call,
       m.oi_put,
       m.writer_pain,
       m.max_pain_strike,
       (m.strike = m.max_pain_strike)          AS is_max_pain
  FROM marked m
 WHERE abs(m.strike - m.axis_spot) <= 0.06 * m.axis_spot;


-- =====================================================================
-- SECTION 2 of 4 -- COMMENT (live statement)
-- =====================================================================

COMMENT ON VIEW public.v_gex_strike_terrain IS
  'S92 / ruling S92-J -- read surface for the OPTIONAL Marketview 3D view (/board/3d: gamma terrain, pain bowl). NOT a parity layer; display-only. Grain (symbol, session_date, strike). The 14 most recent sessions per symbol that hold a GEX run and are not explicitly closed (trading_calendar is_open = false drops a date; a missing row does not). Per session the SETTLED run = last run at or before 15:15 IST (the ENH-126 river rule; after 15:15 the index is auction-frozen, ADR-022); session_complete = a run at or after 15:10 IST. Front expiry. Strikes within +/- 6 pct of session 1 settled spot, one common axis. gex_cr is NULL where the run has no gamma for the strike (gamma_call and gamma_put both NULL) -- a gap, never a zero (SENSEX lacks gamma on ~30 pct of strikes, ADR-024 A3). writer_pain is the ENH-123 formula verbatim over all of the run strikes; is_max_pain marks the argmin over all candidates (ties to the lower strike), so the max-pain strike can lie outside the window -- max_pain_strike says where. Consumers MUST order by session_date, strike. SENSEX can exceed 1,000 rows: page with range. Height carries magnitude, hue carries sign; gex_cr has no defined unit yet (E-D1). Never label second-order terms vanna or charm (L78-1).';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (live statements)
-- =====================================================================
-- REVOKE FIRST, then GRANT. Supabase DEFAULT PRIVILEGES hand new objects ALL
-- (CASE-2026-09-22). authenticated is revoked too -- the S92 views left it
-- with ALL (TD-S92-NEW-4); this one does not repeat that.

REVOKE ALL ON public.v_gex_strike_terrain FROM anon, authenticated;
GRANT SELECT ON public.v_gex_strike_terrain TO anon;
GRANT SELECT ON public.v_gex_strike_terrain TO merdian_ro;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run each block ALONE; read-only)
-- =====================================================================

-- 4a. As anon, in ONE execution, with the acting role in the same result set.
--     Expect role_now = anon; 14 sessions per symbol (fewer only if the table
--     holds fewer); rows ~800 NIFTY / ~1,350 SENSEX; complete_sessions = 13 or 14.
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now, symbol,
       count(DISTINCT session_date) AS sessions,
       count(*) AS n_rows,
       count(*) FILTER (WHERE gex_cr IS NULL) AS gex_null_rows,
       count(DISTINCT session_date) FILTER (WHERE session_complete) AS complete_sessions,
       min(session_date) AS oldest, max(session_date) AS newest
  FROM public.v_gex_strike_terrain
 GROUP BY symbol ORDER BY symbol;
COMMIT;

-- 4b. Cost, as anon. Expect well under 1 s; record Execution Time.
BEGIN;
SET LOCAL ROLE anon;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_terrain;
COMMIT;

-- 4c. Max pain against an INDEPENDENT store (Rule 0: a parity claim is a test).
--     gex_pin_maxpain_history holds max_pain_strike per run, written by a
--     separate path (S80). Expect mismatched = 0; report missing.
WITH t AS (SELECT DISTINCT symbol, session_date, run_id, expiry_date, max_pain_strike
             FROM public.v_gex_strike_terrain)
SELECT t.symbol,
       count(*)                                                                AS sessions,
       count(h.run_id)                                                         AS with_history_row,
       count(*) FILTER (WHERE h.run_id IS NOT NULL
                          AND h.max_pain_strike IS DISTINCT FROM t.max_pain_strike) AS mismatched,
       string_agg(t.session_date || ' view=' || t.max_pain_strike || ' hist=' || h.max_pain_strike, ', ')
         FILTER (WHERE h.run_id IS NOT NULL AND h.max_pain_strike IS DISTINCT FROM t.max_pain_strike) AS detail
  FROM t
  LEFT JOIN gex_pin_maxpain_history h
    ON h.symbol = t.symbol AND h.run_id = t.run_id AND h.expiry_date = t.expiry_date
 GROUP BY t.symbol ORDER BY t.symbol;

-- 4d. ACL. Expect anon=r and merdian_ro=r only; no authenticated entry.
SELECT relname, relacl FROM pg_class WHERE relname = 'v_gex_strike_terrain';
