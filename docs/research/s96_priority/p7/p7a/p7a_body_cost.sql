-- p7a_body_cost.sql -- the v_dex_flow_vs_book body (sql/2026-10-11_s96_v_dex_flow_vs_book.sql
-- Section 1) run as a plain query, for costing through bin/roq.sh BEFORE an apply. S96-E: body
-- regenerated with the M-P7 badge (parity set, CTE o, four appended columns).
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
     ), u AS (
        -- S96-D: the untraded-leg signature S2 per strike side AT THE SETTLED RUN, read from the
        -- chain by the same exact seek the book uses (ts, symbol, expiry_date). S2 = oi > 0, volume
        -- 0 so far (or NULL), and oi_change = oi: all of today's OI is new yet nothing traded.
        SELECT c.symbol, c.expiry_date, c.strike,
               bool_or(c.option_type = 'CE' AND COALESCE(c.oi, 0) > 0
                       AND COALESCE(c.volume, 0) = 0 AND c.oi_change = c.oi) AS call_s2,
               bool_or(c.option_type = 'PE' AND COALESCE(c.oi, 0) > 0
                       AND COALESCE(c.volume, 0) = 0 AND c.oi_change = c.oi) AS put_s2,
               -- S96-E: the CE delta gap by the ENH-140 iv form, for the parity delta set (M-P7 4).
               bool_or(c.option_type = 'CE'
                       AND (c.delta IS NULL OR (c.delta = 0 AND COALESCE(c.iv, 0) = 0))) AS call_gap_iv
          FROM (SELECT DISTINCT bb.symbol, bb.expiry_date, bb.settled_ts
                  FROM b bb JOIN agree g ON g.symbol = bb.symbol) st
          JOIN public.option_chain_snapshots c
            ON c.symbol = st.symbol
           AND c.expiry_date = st.expiry_date
           AND c.ts = st.settled_ts
         GROUP BY c.symbol, c.expiry_date, c.strike
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
               bb.oi_put  - pp.pe_oi_anchor_qty AS d_oi_put,
               COALESCE(uu.call_s2, false) AS call_s2,
               COALESCE(uu.put_s2,  false) AS put_s2,
               -- S96-E: a CE delta usable for the parity set -- present and not a gap; a strike the
               -- chain row is missing for counts as unusable.
               (bb.delta_call IS NOT NULL AND uu.call_gap_iv IS NOT NULL AND NOT uu.call_gap_iv) AS call_ok
          FROM b bb
          JOIN agree g ON g.symbol = bb.symbol
          LEFT JOIN p pp
            ON pp.symbol = bb.symbol
           AND pp.expiry_date = bb.expiry_date
           AND pp.strike = bb.strike
          LEFT JOIN u uu
            ON uu.symbol = bb.symbol
           AND uu.expiry_date = bb.expiry_date
           AND uu.strike = bb.strike
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
             + CASE WHEN d_oi_put  IS NULL THEN COALESCE(oi_put,  0) ELSE 0 END AS no_anchor_oi_qty,
               -- S96-C: the pre-open OI valued at the SETTLED delta (not the 08:30 book).
               CASE WHEN ce_oi_anchor_qty IS NULL THEN NULL
                    WHEN ce_oi_anchor_qty = 0     THEN 0
                    WHEN call_gap                 THEN NULL
                    ELSE delta_call * ce_oi_anchor_qty * spot / 1e7 END AS call_preopen_dex_cr,
               CASE WHEN pe_oi_anchor_qty IS NULL THEN NULL
                    WHEN pe_oi_anchor_qty = 0     THEN 0
                    WHEN put_gap                  THEN NULL
                    ELSE delta_put * pe_oi_anchor_qty * spot / 1e7 END  AS put_preopen_dex_cr,
               -- book OI on a side with NO anchor OI, valued as the book values it: the one
               -- term outside preopen + flow, so the leg identity can be stated exactly.
               CASE WHEN ce_oi_anchor_qty IS NULL AND COALESCE(oi_call, 0) > 0 AND NOT call_gap
                    THEN delta_call * oi_call * spot / 1e7 ELSE 0 END
             + CASE WHEN pe_oi_anchor_qty IS NULL AND COALESCE(oi_put, 0) > 0 AND NOT put_gap
                    THEN delta_put * oi_put * spot / 1e7 ELSE 0 END    AS no_anchor_dex_cr,
               -- S96-D: |book DEX| on S2 sides, and |book DEX| on all sides. A gap side has a NULL
               -- book and counts 0 in both, as in the guard survey (guard_cycles.sql).
               CASE WHEN call_s2 THEN abs(COALESCE(call_dex_cr, 0)) ELSE 0 END
             + CASE WHEN put_s2  THEN abs(COALESCE(put_dex_cr,  0)) ELSE 0 END AS s2_gross_cr,
               abs(COALESCE(call_dex_cr, 0)) + abs(COALESCE(put_dex_cr, 0))   AS book_gross_cr,
               -- S96-E: the parity delta set (M-P7 pre-registration 4, mp7_cycles.sql b_put_p /
               -- f_put_p verbatim): PE delta replaced by delta_call - 1, CE unchanged; a PE value is a
               -- gap under it when its strike's CE delta is a gap or absent.
               CASE WHEN COALESCE(oi_put, 0) = 0 THEN 0
                    WHEN NOT call_ok THEN NULL
                    ELSE (delta_call - 1) * oi_put * spot / 1e7 END            AS put_dex_p_cr,
               CASE WHEN d_oi_put IS NULL THEN NULL
                    WHEN d_oi_put = 0     THEN 0
                    WHEN NOT call_ok      THEN NULL
                    ELSE (delta_call - 1) * d_oi_put * spot / 1e7 END          AS put_flow_p_cr
          FROM j
     ), o AS (
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
       f.leg_gap_oi_qty,
       -- S96-C (appended, so CREATE OR REPLACE keeps the existing columns in place)
       f.call_preopen_dex_cr,
       f.put_preopen_dex_cr,
       CASE WHEN f.call_preopen_dex_cr IS NULL OR f.put_preopen_dex_cr IS NULL THEN NULL
            ELSE f.call_preopen_dex_cr + f.put_preopen_dex_cr END             AS net_preopen_dex_cr,
       sum(COALESCE(f.call_preopen_dex_cr, 0)) OVER wleg                       AS leg_call_preopen_dex_cr,
       sum(COALESCE(f.put_preopen_dex_cr , 0)) OVER wleg                       AS leg_put_preopen_dex_cr,
       sum(COALESCE(f.call_preopen_dex_cr, 0) + COALESCE(f.put_preopen_dex_cr, 0)) OVER wleg AS leg_net_preopen_dex_cr,
       sum(f.no_anchor_dex_cr) OVER wleg                                       AS leg_no_anchor_dex_cr,
       -- S96-D (appended): the untraded-leg guard at the settled run. Share NULL when the leg has
       -- no measured book; untraded_guard is then NULL (unknown, never false).
       sum(f.s2_gross_cr) OVER wleg                                            AS leg_s2_gross_cr,
       sum(f.s2_gross_cr) OVER wleg / NULLIF(sum(f.book_gross_cr) OVER wleg, 0) AS leg_s2_gross_share,
       sum(f.s2_gross_cr) OVER wleg / NULLIF(sum(f.book_gross_cr) OVER wleg, 0) >= 0.02 AS untraded_guard,
       -- S96-E (appended): the parity-set nets, measured part (COALESCE 0), as M-P7 summed them.
       sum(COALESCE(f.call_dex_cr, 0) + COALESCE(f.put_dex_p_cr, 0)) OVER wleg   AS leg_book_net_p_cr,
       sum(COALESCE(f.call_flow_cr, 0) + COALESCE(f.put_flow_p_cr, 0)) OVER wleg AS leg_flow_net_p_cr
  FROM f
WINDOW wleg AS (PARTITION BY f.symbol, f.expiry_date)
     )
-- S96-E: the M-P7 badge (pre-registration 4) with the two ruled conditions in front of it. One
-- abstain code per row, first match wins: PRE_OPEN (S96-A D7), UNTRADED (S96-D: guard not false,
-- NULL included), ZERO_NET (any of the four nets exactly 0; a NULL net cannot occur -- leg totals
-- are COALESCE sums -- and is folded in so it can never speak), DELTA_SET (vendor and parity
-- signs differ on flow or on book).
SELECT o.*,
       CASE WHEN z.code IS NOT NULL THEN 'ABSTAIN'
            WHEN sign(o.leg_net_flow_cr) = sign(o.leg_net_dex_cr) THEN 'SAME'
            ELSE 'OPPOSITE' END                                               AS flow_book_badge,
       z.code                                                                 AS flow_book_abstain_code
  FROM o
  CROSS JOIN LATERAL (
       SELECT CASE WHEN o.flow_window <> 'SESSION' THEN 'PRE_OPEN'
                   WHEN o.untraded_guard IS DISTINCT FROM false THEN 'UNTRADED'
                   WHEN o.leg_net_flow_cr IS NULL OR o.leg_flow_net_p_cr IS NULL
                     OR o.leg_net_dex_cr  IS NULL OR o.leg_book_net_p_cr IS NULL
                     OR o.leg_net_flow_cr = 0 OR o.leg_flow_net_p_cr = 0
                     OR o.leg_net_dex_cr  = 0 OR o.leg_book_net_p_cr = 0 THEN 'ZERO_NET'
                   WHEN sign(o.leg_net_flow_cr) <> sign(o.leg_flow_net_p_cr)
                     OR sign(o.leg_net_dex_cr)  <> sign(o.leg_book_net_p_cr) THEN 'DELTA_SET'
                   END AS code
  ) z;
