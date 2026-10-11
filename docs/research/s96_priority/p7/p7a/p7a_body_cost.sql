-- p7a_body_cost.sql -- the v_dex_flow_vs_book body (sql/2026-10-11_s96_v_dex_flow_vs_book.sql
-- Section 1) run as a plain query, for costing through bin/roq.sh BEFORE the view exists.
-- Read-only; creates nothing. Run TWICE (one timing on a shared instance is a sample):
--   { printf 'EXPLAIN (ANALYZE, BUFFERS)\n'; cat p7a_body_cost.sql; } | bin/roq.sh | grep -E 'Execution Time|Planning Time'
-- PASS: Execution Time < 3000 ms on both runs (anon ceiling, MV-6). Note: roq runs as merdian_ro,
-- not anon; the anon timing is Section 4e after apply.
WITH b AS (
        SELECT * FROM public.v_dex_standing_book WHERE leg_n = 1
     ), p AS (
        SELECT symbol, expiry_date, strike, anchor_ts,
               (anchor_ts AT TIME ZONE 'Asia/Kolkata')::date AS p_session_date,
               ce_oi_anchor_qty, pe_oi_anchor_qty
          FROM public.v_oi_since_preopen
     ), agree AS (
        -- one row per symbol whose book session + front expiry equal P5's
        SELECT DISTINCT bb.symbol, pp.anchor_ts
          FROM b bb
          JOIN p pp
            ON pp.symbol = bb.symbol
           AND pp.expiry_date = bb.expiry_date
           AND pp.p_session_date = bb.session_date
     ), j AS (
        SELECT bb.*,
               g.anchor_ts,
               pp.ce_oi_anchor_qty,
               pp.pe_oi_anchor_qty,
               CASE WHEN COALESCE(bb.oi_call, 0) > 0 THEN bb.call_dex_cr IS NULL
                    ELSE (bb.delta_call IS NULL OR bb.delta_call = 0) END AS call_gap,
               CASE WHEN COALESCE(bb.oi_put, 0) > 0 THEN bb.put_dex_cr IS NULL
                    ELSE (bb.delta_put IS NULL OR bb.delta_put = 0) END AS put_gap,
               bb.oi_call - pp.ce_oi_anchor_qty AS d_oi_call,
               bb.oi_put  - pp.pe_oi_anchor_qty AS d_oi_put
          FROM b bb
          JOIN agree g ON g.symbol = bb.symbol
          LEFT JOIN p pp
            ON pp.symbol = bb.symbol
           AND pp.expiry_date = bb.expiry_date
           AND pp.strike = bb.strike
     ), f AS (
        SELECT j.*,
               CASE WHEN d_oi_call IS NULL THEN NULL
                    WHEN d_oi_call = 0     THEN 0
                    WHEN call_gap          THEN NULL
                    ELSE delta_call * d_oi_call * spot / 1e7 END AS call_flow_cr,
               CASE WHEN d_oi_put IS NULL THEN NULL
                    WHEN d_oi_put = 0     THEN 0
                    WHEN put_gap          THEN NULL
                    ELSE delta_put * d_oi_put * spot / 1e7 END   AS put_flow_cr,
               CASE WHEN d_oi_call IS NOT NULL AND d_oi_call <> 0 AND call_gap
                    THEN abs(d_oi_call) ELSE 0 END               AS d_oi_call_no_delta,
               CASE WHEN d_oi_put IS NOT NULL AND d_oi_put <> 0 AND put_gap
                    THEN abs(d_oi_put) ELSE 0 END                AS d_oi_put_no_delta,
               CASE WHEN d_oi_call IS NULL THEN COALESCE(oi_call, 0) ELSE 0 END
             + CASE WHEN d_oi_put  IS NULL THEN COALESCE(oi_put,  0) ELSE 0 END AS no_anchor_oi_qty
          FROM j
     )
SELECT f.symbol,
       f.session_date,
       f.expiry_date,
       f.dte,
       f.anchor_ts,
       f.settled_ts,
       CASE WHEN f.settled_ts < ((f.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
            THEN 'PRE_OPEN' ELSE 'SESSION' END                            AS flow_window,
       f.spot,
       f.strike,
       f.delta_call,
       f.delta_put,
       f.oi_call,
       f.oi_put,
       f.ce_oi_anchor_qty,
       f.pe_oi_anchor_qty,
       f.d_oi_call,
       f.d_oi_put,
       f.call_flow_cr,
       f.put_flow_cr,
       -- NULL when either side is unknown: an unknown cannot be netted (ENH-140).
       CASE WHEN f.call_flow_cr IS NULL OR f.put_flow_cr IS NULL THEN NULL
            ELSE f.call_flow_cr + f.put_flow_cr END                       AS net_flow_cr,
       f.d_oi_call_no_delta,
       f.d_oi_put_no_delta,
       f.call_dex_cr,
       f.put_dex_cr,
       f.net_dex_cr,
       -- Leg totals: each side's MEASURED contribution (COALESCE 0), with what
       -- they do not cover beside them -- the ENH-140 rule. Read together or not at all.
       sum(COALESCE(f.call_flow_cr, 0)) OVER wleg                          AS leg_call_flow_cr,
       sum(COALESCE(f.put_flow_cr , 0)) OVER wleg                          AS leg_put_flow_cr,
       sum(COALESCE(f.call_flow_cr, 0) + COALESCE(f.put_flow_cr, 0)) OVER wleg AS leg_net_flow_cr,
       sum(abs(COALESCE(f.call_flow_cr, 0)) + abs(COALESCE(f.put_flow_cr, 0))) OVER wleg AS leg_gross_flow_cr,
       sum(abs(COALESCE(f.d_oi_call, 0)) + abs(COALESCE(f.d_oi_put, 0))) OVER wleg AS leg_abs_d_oi_qty,
       sum(f.d_oi_call_no_delta + f.d_oi_put_no_delta) OVER wleg           AS leg_gap_d_oi_qty,
       sum(f.no_anchor_oi_qty) OVER wleg                                   AS leg_no_anchor_oi_qty,
       f.leg_call_dex_cr,
       f.leg_put_dex_cr,
       f.leg_net_dex_cr,
       f.leg_oi_qty,
       f.leg_gap_oi_qty
  FROM f
WINDOW wleg AS (PARTITION BY f.symbol, f.expiry_date);
