-- =====================================================================
-- v_gex_strike_rank_gross -- the textbook (gross) pin, construction VS.
-- SHADOW VIEW. Engine session S107, intake I-002 row 1 (ENH-149).
-- Authored 2026-11-23 by the engine lane from the Board-pin lane's
-- revision 2 draft (docs/research/pin_proof/
-- 2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql). REVISION 3.
--
-- The operator applies this in the SQL editor, ONE STATEMENT AT A TIME,
-- in the order of the sections. Claude does not run SQL on production.
--
-- WHAT CHANGED FROM REVISION 2 (ranking rule, band, tie-break: unchanged)
--   + gamma_legs     which legs supplied gamma_strike: 'both', 'call_only',
--                    'put_only'.
--   + n_in_set       strikes of the run and expiry inside the 5 % band
--                    (the denominator for the next column).
--   + n_oi_no_gamma  of those, strikes that hold open interest and have no
--                    vendor gamma on either leg. They cannot be ranked;
--                    this count is how a reader sees that they exist.
--   The three columns are appended at the END of the column list, so the
--   statement also applies over a revision 2 view if one was ever created.
--   COMMENT and GRANT are live statements (TD-S81-NEW-5 rule).
--
-- WHAT IT IS
--   Strikes of the latest run per symbol, within 5 % of spot, ranked on
--     gross_cr = gamma_strike * (oi_call + oi_put) * spot^2 / 1e7
--   gamma_strike = mean of gamma_call and gamma_put when both are > 0; the
--   one that is > 0 when the other is 0 or NULL; no gamma when neither.
--   strike_rank = 1 is the pin ruled 2026-11-21
--   (docs/research/pin_proof/ruling_pin_definition_2026-11-21.md).
--   Unit: gross_cr is the stored unit (gamma * OI * S^2 / 1e7), NOT per 1 %.
--   No _1pct wrapper is made because nothing shows this view (ADR-032 D1
--   applies only if it reaches the Board).
--
-- WHAT IT IS NOT
--   It does not replace v_gex_strike_rank (netted, ENH-125). Nothing reads
--   it. The Board, /tape, gex_cycle_history, gamma.py and every signal gate
--   are unchanged. A Board switch is a separate decision and needs an
--   order-flow lane note first (STREAMS X1).
--   Rollback: DROP VIEW public.v_gex_strike_rank_gross;
--
-- KNOWN LIMITS
--   - Latest run only, no history. The ten-day shadow is scored by the
--     pin lane's evening replay from gex_strike_snapshots, not by this view.
--   - side and gex_cr are the STORED net (two vendor gammas). The frozen
--     audit of 2026-11-22 found that net wrong in sign on 8.6-9.9 % of runs
--     with a clearly non-zero total. They are carried for comparison with
--     v_gex_strike_rank only and say nothing about the gross pin.
--   - A run and expiry with no rankable strike returns no row, so its
--     n_oi_no_gamma is not visible here.
--   - A frozen-OI run is ranked like any other. Weaker on pre-open runs.
--   - Pin lane dry run of the revision 2 SELECT, 2026-11-22: no Seq Scan,
--     2.93 s, 135 rows. The sibling view measured 11.8 ms at S81. The gap
--     is not explained; read the plan (4a) before anything polls this view.
--
-- REGISTRATION (CLAUDE.md rule 25; TD-PIN1-NEW-4)
--   After apply, run 4d and record length, md5 and the server version in
--   docs/interfaces/retail_compute_contract.md section 8 and in I-002.
--   The md5 of pg_get_viewdef is not stable across server versions, so the
--   version travels with it.
-- =====================================================================

-- SECTION 1 of 4 -- the view (one statement)

CREATE OR REPLACE VIEW public.v_gex_strike_rank_gross AS
WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol)
                  FROM gex_strike_snapshots g
                 WHERE g.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.run_id, lr.ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts
                 FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol
                ORDER BY g.ts DESC
                LIMIT 1
          ) lr
         WHERE s.symbol IS NOT NULL
     ), base AS (
        SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte,
               g.strike, g.spot, g.oi_call, g.oi_put,
               g.gamma_call, g.gamma_put, g.gex_cr,
               CASE WHEN COALESCE(g.gamma_call, 0) > 0 AND COALESCE(g.gamma_put, 0) > 0
                         THEN (g.gamma_call + g.gamma_put) / 2.0
                    WHEN COALESCE(g.gamma_call, 0) > 0 THEN g.gamma_call
                    WHEN COALESCE(g.gamma_put,  0) > 0 THEN g.gamma_put
                    ELSE 0
               END AS gamma_strike,
               CASE WHEN COALESCE(g.gamma_call, 0) > 0 AND COALESCE(g.gamma_put, 0) > 0
                         THEN 'both'
                    WHEN COALESCE(g.gamma_call, 0) > 0 THEN 'call_only'
                    WHEN COALESCE(g.gamma_put,  0) > 0 THEN 'put_only'
                    ELSE 'none'
               END AS gamma_legs
          FROM gex_strike_snapshots g
          JOIN latest_run lr
            ON g.symbol = lr.symbol AND g.run_id = lr.run_id
         WHERE g.spot > 0
           AND abs(g.strike / g.spot - 1) <= 0.05
     ), scoped AS (
        SELECT b.*,
               b.gamma_strike * (COALESCE(b.oi_call, 0) + COALESCE(b.oi_put, 0))
               * (b.spot::double precision ^ 2) / 1e7 AS gross_cr
          FROM base b
     ), setstats AS (
        SELECT sc.run_id, sc.symbol, sc.expiry_date,
               count(*) AS n_in_set,
               count(*) FILTER (WHERE sc.gamma_legs = 'none'
                                  AND COALESCE(sc.oi_call, 0) + COALESCE(sc.oi_put, 0) > 0)
                 AS n_oi_no_gamma
          FROM scoped sc
         GROUP BY sc.run_id, sc.symbol, sc.expiry_date
     ), ranked AS (
        SELECT sc.run_id, sc.symbol, sc.ts, sc.expiry_date, sc.dte,
               sc.strike, sc.spot, sc.oi_call, sc.oi_put,
               sc.gamma_call, sc.gamma_put, sc.gamma_strike, sc.gamma_legs,
               sc.gex_cr, sc.gross_cr,
               row_number() OVER w AS strike_rank,
               sc.gross_cr / NULLIF(sum(sc.gross_cr) OVER p, 0) AS share_of_gross,
               count(*) OVER p AS n_ranked
          FROM scoped sc
         WHERE sc.gross_cr > 0
        WINDOW p AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date),
               w AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date
                     ORDER BY sc.gross_cr DESC, abs(sc.strike - sc.spot), sc.strike)
     ), hdr AS (
        SELECT run_id, symbol, expiry_date,
               max(gross_cr) FILTER (WHERE strike_rank = 1) AS top_cr,
               max(gross_cr) FILTER (WHERE strike_rank = 2) AS second_cr
          FROM ranked
         GROUP BY run_id, symbol, expiry_date
     )
SELECT r.run_id,
       r.symbol,
       r.expiry_date,
       r.ts,
       r.dte,
       r.spot,
       r.strike_rank,
       r.strike,
       r.oi_call,
       r.oi_put,
       r.gamma_call,
       r.gamma_put,
       r.gamma_strike,
       r.gross_cr,
       r.share_of_gross,
       r.gex_cr,
       CASE WHEN r.gex_cr > 0 THEN 'DAMPENING'
            WHEN r.gex_cr < 0 THEN 'AMPLIFYING'
       END AS side,
       (h.top_cr - h.second_cr) / NULLIF(h.top_cr, 0) AS lead_rel,
       r.n_ranked,
       r.gamma_legs,
       st.n_in_set,
       st.n_oi_no_gamma
  FROM ranked r
  JOIN hdr h
    ON h.run_id = r.run_id AND h.symbol = r.symbol AND h.expiry_date = r.expiry_date
  JOIN setstats st
    ON st.run_id = r.run_id AND st.symbol = r.symbol AND st.expiry_date = r.expiry_date;


-- SECTION 2 of 4 -- comment (one statement)

COMMENT ON VIEW public.v_gex_strike_rank_gross IS
'S107 2026-11-23, I-002 row 1, ENH-149 -- textbook (gross) pin, SHADOW, revision 3. Strikes of the latest run per symbol within 5 % of spot, ranked on gross_cr = gamma_strike*(oi_call+oi_put)*spot^2/1e7 (stored unit, not per 1 %). gamma_strike = mean of gamma_call and gamma_put when both > 0, else the one that is > 0 (construction VS); gamma_legs says which: both / call_only / put_only. Tie-break nearer to spot then lower strike. strike_rank = 1 is the pin ruled 2026-11-21. n_in_set = in-band strikes of the run and expiry; n_oi_no_gamma = of those, strikes with open interest and no gamma on either leg (not rankable). lead_rel = (top - second)/top, NOT the Board lead in share points. side and gex_cr are the STORED net from two vendor gammas, carried for comparison with v_gex_strike_rank only. Does not replace v_gex_strike_rank; nothing reads it; no Board use without an order-flow lane note (STREAMS X1). Consumers must ORDER BY strike_rank.';


-- SECTION 3 of 4 -- privileges. THREE statements, run separately, in order.
-- New objects in public can inherit default grants; remove them first.
-- Shadow stage: the read-only research role only. marketview_ro is NOT
-- granted until a Board switch is approved.

REVOKE ALL ON public.v_gex_strike_rank_gross FROM anon;

REVOKE ALL ON public.v_gex_strike_rank_gross FROM authenticated;

GRANT SELECT ON public.v_gex_strike_rank_gross TO merdian_ro;


-- SECTION 4 of 4 -- verification. Read-only. Run separately, after 1-3.
-- They are commented so that pasting the whole file runs nothing extra.

-- 4a -- plan: expect index probes, no Seq Scan on gex_strike_snapshots.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_rank_gross;

-- 4b -- top 3 per symbol, the new columns, and the netted leader beside it.
-- SELECT g.symbol, g.strike_rank, g.strike, g.gamma_legs,
--        round(g.share_of_gross::numeric, 4) AS share_of_gross,
--        round(g.lead_rel::numeric, 4)       AS lead_rel,
--        g.n_ranked, g.n_in_set, g.n_oi_no_gamma,
--        (SELECT n.strike FROM public.v_gex_strike_rank n
--          WHERE n.symbol = g.symbol AND n.strike_rank = 1) AS netted_leader
--   FROM public.v_gex_strike_rank_gross g
--  WHERE g.strike_rank <= 3
--  ORDER BY g.symbol, g.strike_rank;

-- 4c -- privileges, comment and options. PASS: merdian_ro true; anon,
--       authenticated, marketview_ro false; has_comment true.
-- SELECT r.rolname,
--        has_table_privilege(r.rolname, 'public.v_gex_strike_rank_gross', 'SELECT') AS can_select,
--        obj_description('public.v_gex_strike_rank_gross'::regclass, 'pg_class') IS NOT NULL AS has_comment
--   FROM pg_roles r
--  WHERE r.rolname IN ('anon', 'authenticated', 'marketview_ro', 'merdian_ro')
--  ORDER BY 1;

-- 4d -- registration read (rule 25): record all three values.
-- SELECT length(d) AS def_length, md5(d) AS def_md5, current_setting('server_version') AS pg_version
--   FROM (SELECT pg_get_viewdef('public.v_gex_strike_rank_gross'::regclass, true) AS d) v;

-- ROLLBACK
-- DROP VIEW public.v_gex_strike_rank_gross;
