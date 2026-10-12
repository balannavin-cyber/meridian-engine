-- flow_body_cost.sql -- the v_delta_drift_flow_vs_book body (sql/2026-10-12_s96_v_delta_drift_flow_vs_book.sql
-- Section 1) as a plain query, for costing through bin/roq.sh BEFORE the apply. Read-only. Run TWICE:
--   { printf 'EXPLAIN (ANALYZE, BUFFERS)\n'; cat flow_body_cost.sql; } | bin/roq.sh | grep -E 'Execution Time|CTE Scan on (gate|hx)|Seq Scan on option_chain'
-- PASS: Execution Time < 3000 ms both runs; gate and hx at loops=1; no Seq Scan on option_chain_snapshots.
WITH l AS MATERIALIZED (
        -- one read of the S96-F base: the L7/L8 latest ts, both legs, per chain row
        SELECT * FROM public.v_gex_greeks_l2_leg
     ), fr AS (
        -- the front leg at that ts
        SELECT symbol, ts, min(expiry_date) AS expiry_date
          FROM l
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), p AS (
        SELECT symbol, expiry_date, strike, anchor_ts,
               (anchor_ts AT TIME ZONE 'Asia/Kolkata')::date AS p_session_date,
               ce_oi_anchor_qty, pe_oi_anchor_qty
          FROM public.v_oi_since_preopen
     ), agree AS (
        -- JOIN GUARD: the base's session date and front expiry must equal P5's, else no rows
        SELECT DISTINCT f.symbol, f.ts, f.expiry_date, pp.anchor_ts
          FROM fr f
          JOIN p pp
            ON pp.symbol = f.symbol
           AND pp.expiry_date = f.expiry_date
           AND pp.p_session_date = (f.ts AT TIME ZONE 'Asia/Kolkata')::date
     ), k AS (
        -- pivot the front leg's chain rows to one row per strike (one CE and one PE row per strike)
        SELECT l.symbol, l.ts, l.expiry_date, g.anchor_ts, l.strike,
               max(l.spot) AS spot, max(l.dte) AS dte, max(l.n_r_rows) AS n_r_rows,
               max(l.oi_qty) FILTER (WHERE l.option_type = 'CE')               AS oi_call,
               max(l.oi_qty) FILTER (WHERE l.option_type = 'PE')               AS oi_put,
               max(l.oi)     FILTER (WHERE l.option_type = 'CE')               AS oi_call_d,
               max(l.oi)     FILTER (WHERE l.option_type = 'PE')               AS oi_put_d,
               bool_or(l.option_type = 'CE' AND l.in_leg_set AND l.evaluable)  AS call_in_book,
               bool_or(l.option_type = 'PE' AND l.in_leg_set AND l.evaluable)  AS put_in_book,
               max(l.u_delta_drift_iv)   FILTER (WHERE l.option_type = 'CE')   AS u_iv_call,
               max(l.u_delta_drift_iv)   FILTER (WHERE l.option_type = 'PE')   AS u_iv_put,
               max(l.u_delta_drift_time) FILTER (WHERE l.option_type = 'CE')   AS u_t_call,
               max(l.u_delta_drift_time) FILTER (WHERE l.option_type = 'PE')   AS u_t_put
          FROM l
          JOIN agree g ON g.symbol = l.symbol AND g.ts = l.ts AND g.expiry_date = l.expiry_date
         GROUP BY l.symbol, l.ts, l.expiry_date, g.anchor_ts, l.strike
     ), j AS (
        SELECT k.*, pp.ce_oi_anchor_qty, pp.pe_oi_anchor_qty,
               k.oi_call - pp.ce_oi_anchor_qty AS d_oi_call,
               k.oi_put  - pp.pe_oi_anchor_qty AS d_oi_put
          FROM k
          LEFT JOIN p pp
            ON pp.symbol = k.symbol AND pp.expiry_date = k.expiry_date AND pp.strike = k.strike
     ), f AS (
        -- sgn x unit x quantity x spot / 1e7, the L7/L8 expression (CE +1.0, PE -1.0). BOOK sums the
        -- leg set exactly as v_gex_greeks_l2_strike does; a side with OI that the leg set excludes is
        -- a gap (NULL), a side with no OI a true 0. FLOW and PRE-OPEN price on `priceable` (S96-F E2),
        -- i.e. wherever the unit column is not NULL; a non-zero dOI with no unit is a gap.
        SELECT j.*,
               CASE WHEN j.call_in_book THEN 1.0 * j.u_iv_call * j.oi_call_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_call, 0) = 0 THEN 0 END                     AS call_iv_book_cr,
               CASE WHEN j.put_in_book  THEN -1.0 * j.u_iv_put * j.oi_put_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_put, 0) = 0 THEN 0 END                      AS put_iv_book_cr,
               CASE WHEN j.call_in_book THEN 1.0 * j.u_t_call * j.oi_call_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_call, 0) = 0 THEN 0 END                     AS call_t_book_cr,
               CASE WHEN j.put_in_book  THEN -1.0 * j.u_t_put * j.oi_put_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_put, 0) = 0 THEN 0 END                      AS put_t_book_cr,
               CASE WHEN j.d_oi_call IS NULL THEN NULL WHEN j.d_oi_call = 0 THEN 0
                    WHEN j.u_iv_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_iv_call * j.d_oi_call::double precision * j.spot / 1e7 END  AS call_iv_flow_cr,
               CASE WHEN j.d_oi_put IS NULL THEN NULL WHEN j.d_oi_put = 0 THEN 0
                    WHEN j.u_iv_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_iv_put * j.d_oi_put::double precision * j.spot / 1e7 END   AS put_iv_flow_cr,
               CASE WHEN j.d_oi_call IS NULL THEN NULL WHEN j.d_oi_call = 0 THEN 0
                    WHEN j.u_t_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_t_call * j.d_oi_call::double precision * j.spot / 1e7 END   AS call_t_flow_cr,
               CASE WHEN j.d_oi_put IS NULL THEN NULL WHEN j.d_oi_put = 0 THEN 0
                    WHEN j.u_t_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_t_put * j.d_oi_put::double precision * j.spot / 1e7 END    AS put_t_flow_cr,
               CASE WHEN j.ce_oi_anchor_qty IS NULL THEN NULL WHEN j.ce_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_iv_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_iv_call * j.ce_oi_anchor_qty::double precision * j.spot / 1e7 END AS call_iv_preopen_cr,
               CASE WHEN j.pe_oi_anchor_qty IS NULL THEN NULL WHEN j.pe_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_iv_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_iv_put * j.pe_oi_anchor_qty::double precision * j.spot / 1e7 END AS put_iv_preopen_cr,
               CASE WHEN j.ce_oi_anchor_qty IS NULL THEN NULL WHEN j.ce_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_t_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_t_call * j.ce_oi_anchor_qty::double precision * j.spot / 1e7 END  AS call_t_preopen_cr,
               CASE WHEN j.pe_oi_anchor_qty IS NULL THEN NULL WHEN j.pe_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_t_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_t_put * j.pe_oi_anchor_qty::double precision * j.spot / 1e7 END  AS put_t_preopen_cr,
               CASE WHEN j.d_oi_call IS NOT NULL AND j.d_oi_call <> 0 AND j.u_iv_call IS NULL
                    THEN abs(j.d_oi_call) ELSE 0 END
             + CASE WHEN j.d_oi_put IS NOT NULL AND j.d_oi_put <> 0 AND j.u_iv_put IS NULL
                    THEN abs(j.d_oi_put) ELSE 0 END                                            AS gap_d_oi_qty,
               CASE WHEN j.d_oi_call IS NULL THEN COALESCE(j.oi_call, 0) ELSE 0 END
             + CASE WHEN j.d_oi_put  IS NULL THEN COALESCE(j.oi_put,  0) ELSE 0 END            AS no_anchor_oi_qty
          FROM j
     ), g2 AS (
        SELECT f.*,
               -- the book on sides with NO anchor OI: the one term outside pre-open + flow
               CASE WHEN f.ce_oi_anchor_qty IS NULL THEN COALESCE(f.call_iv_book_cr, 0) ELSE 0 END
             + CASE WHEN f.pe_oi_anchor_qty IS NULL THEN COALESCE(f.put_iv_book_cr,  0) ELSE 0 END AS iv_no_anchor_cr,
               CASE WHEN f.ce_oi_anchor_qty IS NULL THEN COALESCE(f.call_t_book_cr, 0) ELSE 0 END
             + CASE WHEN f.pe_oi_anchor_qty IS NULL THEN COALESCE(f.put_t_book_cr,  0) ELSE 0 END  AS t_no_anchor_cr
          FROM f
     )
SELECT g2.symbol,
       g2.expiry_date,
       g2.dte,
       g2.ts,
       g2.anchor_ts,
       CASE WHEN g2.ts < (((g2.ts AT TIME ZONE 'Asia/Kolkata')::date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
            THEN 'PRE_OPEN' ELSE 'SESSION' END                                      AS flow_window,
       CASE WHEN g2.dte = 0 THEN 'SKIPPED_EXPIRY'
            WHEN g2.n_r_rows < 6 THEN 'UNMEASURABLE_R'
            ELSE 'OK' END                                                          AS status,
       g2.spot,
       g2.strike,
       g2.oi_call, g2.oi_put, g2.ce_oi_anchor_qty, g2.pe_oi_anchor_qty, g2.d_oi_call, g2.d_oi_put,
       -- d(delta)/d(sigma), Rs crore of delta-notional per +1 IV point
       g2.call_iv_flow_cr, g2.put_iv_flow_cr,
       CASE WHEN g2.call_iv_flow_cr IS NULL OR g2.put_iv_flow_cr IS NULL THEN NULL
            ELSE g2.call_iv_flow_cr + g2.put_iv_flow_cr END                         AS net_iv_flow_cr,
       g2.call_iv_book_cr, g2.put_iv_book_cr,
       CASE WHEN g2.call_iv_book_cr IS NULL OR g2.put_iv_book_cr IS NULL THEN NULL
            ELSE g2.call_iv_book_cr + g2.put_iv_book_cr END                         AS net_iv_book_cr,
       g2.call_iv_preopen_cr, g2.put_iv_preopen_cr,
       CASE WHEN g2.call_iv_preopen_cr IS NULL OR g2.put_iv_preopen_cr IS NULL THEN NULL
            ELSE g2.call_iv_preopen_cr + g2.put_iv_preopen_cr END                   AS net_iv_preopen_cr,
       -- d(delta)/dt, Rs crore of delta-notional per calendar day
       g2.call_t_flow_cr, g2.put_t_flow_cr,
       CASE WHEN g2.call_t_flow_cr IS NULL OR g2.put_t_flow_cr IS NULL THEN NULL
            ELSE g2.call_t_flow_cr + g2.put_t_flow_cr END                           AS net_t_flow_cr,
       g2.call_t_book_cr, g2.put_t_book_cr,
       CASE WHEN g2.call_t_book_cr IS NULL OR g2.put_t_book_cr IS NULL THEN NULL
            ELSE g2.call_t_book_cr + g2.put_t_book_cr END                           AS net_t_book_cr,
       g2.call_t_preopen_cr, g2.put_t_preopen_cr,
       CASE WHEN g2.call_t_preopen_cr IS NULL OR g2.put_t_preopen_cr IS NULL THEN NULL
            ELSE g2.call_t_preopen_cr + g2.put_t_preopen_cr END                     AS net_t_preopen_cr,
       g2.gap_d_oi_qty,
       g2.no_anchor_oi_qty,
       -- LEG TOTALS: each side's MEASURED contribution (COALESCE 0), read with the gap and no-anchor
       -- quantities beside them or not at all (the ENH-140 rule).
       sum(COALESCE(g2.call_iv_flow_cr, 0) + COALESCE(g2.put_iv_flow_cr, 0)) OVER w        AS leg_iv_flow_cr,
       sum(abs(COALESCE(g2.call_iv_flow_cr, 0)) + abs(COALESCE(g2.put_iv_flow_cr, 0))) OVER w AS leg_iv_gross_flow_cr,
       sum(COALESCE(g2.call_iv_book_cr, 0) + COALESCE(g2.put_iv_book_cr, 0)) OVER w        AS leg_iv_book_cr,
       sum(COALESCE(g2.call_iv_preopen_cr, 0) + COALESCE(g2.put_iv_preopen_cr, 0)) OVER w  AS leg_iv_preopen_cr,
       sum(g2.iv_no_anchor_cr) OVER w                                                     AS leg_iv_no_anchor_cr,
       sum(COALESCE(g2.call_t_flow_cr, 0) + COALESCE(g2.put_t_flow_cr, 0)) OVER w          AS leg_t_flow_cr,
       sum(abs(COALESCE(g2.call_t_flow_cr, 0)) + abs(COALESCE(g2.put_t_flow_cr, 0))) OVER w AS leg_t_gross_flow_cr,
       sum(COALESCE(g2.call_t_book_cr, 0) + COALESCE(g2.put_t_book_cr, 0)) OVER w          AS leg_t_book_cr,
       sum(COALESCE(g2.call_t_preopen_cr, 0) + COALESCE(g2.put_t_preopen_cr, 0)) OVER w    AS leg_t_preopen_cr,
       sum(g2.t_no_anchor_cr) OVER w                                                      AS leg_t_no_anchor_cr,
       sum(abs(COALESCE(g2.d_oi_call, 0)) + abs(COALESCE(g2.d_oi_put, 0))) OVER w          AS leg_abs_d_oi_qty,
       sum(g2.gap_d_oi_qty) OVER w                                                        AS leg_gap_d_oi_qty,
       sum(g2.no_anchor_oi_qty) OVER w                                                    AS leg_no_anchor_oi_qty
  FROM g2
WINDOW w AS (PARTITION BY g2.symbol, g2.expiry_date);
