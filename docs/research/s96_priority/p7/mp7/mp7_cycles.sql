-- mp7_cycles.sql -- M-P7, per-cycle DEX book and flow totals for the date :'d'.
-- Pre-registered with docs/research/s96_priority/p7/MP7_flow_badge_prereg_2026-10-11.md (sections 3-4).
-- One row per (symbol, cycle ts) of the front expiry in [09:15, 15:15] IST, ANCHORED sessions only
-- (the same session / front / anchor rules as mp7_status.sql, repeated here so each file runs alone).
-- Leg arithmetic = v_dex_standing_book (ENH-140) verbatim: delta x oi x spot / 1e7, no PE flip,
-- no OI -> 0 tested before the gap, gap = delta IS NULL OR (delta = 0 AND COALESCE(iv,0) = 0),
-- totals are the MEASURED part (COALESCE 0) with the uncovered quantity beside them.
-- Two delta sets: vendor (_v), and parity-implied put delta delta_call - 1 (_p; CE unchanged;
-- a PE value is a gap under _p when its strike's CE delta is a gap or absent).
-- Flow: same arithmetic on dOI = oi(cycle) - oi(anchor), NULL unless both sides carry an oi.
-- Run (mp7_run.sh): { printf "\\set d '%s'\n" 2026-09-01; cat mp7_cycles.sql; } | bin/roq.sh
\set QUIET on
\pset format csv
WITH RECURSIVE syms AS (
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c) AS symbol
        UNION ALL
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c WHERE c.symbol > s.symbol)
          FROM syms s WHERE s.symbol IS NOT NULL
     ), sess AS MATERIALIZED (
        SELECT s.symbol, (:'d')::date AS session_date
          FROM syms s
         WHERE s.symbol IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM public.trading_calendar tc
                            WHERE tc.trade_date = (:'d')::date AND tc.is_open = false)
           AND (SELECT count(DISTINCT m.spot)
                  FROM public.market_spot_snapshots m
                 WHERE m.symbol = s.symbol
                   AND m.ts >= ((:'d')::date::timestamp AT TIME ZONE 'Asia/Kolkata')
                   AND m.ts <= (((:'d')::date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')) > 1
     ), fr AS MATERIALIZED (
        SELECT x.symbol, x.session_date,
               -- A1 (2026-10-11): min over a DISTINCT of the SAME predicates. The bare min()
               -- let the planner walk idx_ocs_symbol_expiry_strike_type with ts as a filter
               -- (EXPLAIN 2026-08-24: cost 294,617, 30 s timeout). DISTINCT needs every matching
               -- row, so the ts range on idx_ocs_ts_symbol_expiry is the cheap path -- the
               -- v_dex_standing_book legs CTE shape (measured 61 ms). Same value by definition.
               (SELECT min(e.expiry_date)
                  FROM (SELECT DISTINCT c.expiry_date FROM public.option_chain_snapshots c
                         WHERE c.symbol = x.symbol
                           AND c.ts >= (x.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                           AND c.ts <= ((x.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
                           AND c.expiry_date >= x.session_date) e) AS expiry_date
          FROM sess x
     ), anchored AS MATERIALIZED (
        SELECT f.symbol, f.session_date, f.expiry_date, a.anchor_ts
          FROM fr f
          CROSS JOIN LATERAL (
               SELECT min(c.ts) AS anchor_ts FROM public.option_chain_snapshots c
                WHERE c.symbol = f.symbol AND c.expiry_date = f.expiry_date
                  AND c.ts >= (f.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                  AND c.ts <  ((f.session_date + 1)::timestamp AT TIME ZONE 'Asia/Kolkata')
          ) a
         WHERE f.expiry_date IS NOT NULL
           AND a.anchor_ts < ((f.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
     ), ak AS MATERIALIZED (
        SELECT k.symbol, c.strike,
               max(c.oi) FILTER (WHERE c.option_type = 'CE') AS a_oi_call,
               max(c.oi) FILTER (WHERE c.option_type = 'PE') AS a_oi_put,
               count(*)                                      AS a_rows
          FROM anchored k
          JOIN public.option_chain_snapshots c
            ON c.symbol = k.symbol AND c.ts = k.anchor_ts AND c.expiry_date = k.expiry_date
         GROUP BY k.symbol, c.strike
     ), ak_tot AS (
        SELECT symbol, sum(COALESCE(a_oi_call, 0) + COALESCE(a_oi_put, 0)) AS anchor_oi_qty,
               count(*) FILTER (WHERE a_oi_call IS NOT NULL OR a_oi_put IS NOT NULL) AS anchor_n_strikes
          FROM ak GROUP BY symbol
     ), cycles AS MATERIALIZED (
        SELECT k.symbol, k.session_date, k.expiry_date, k.anchor_ts, t.ts
          FROM anchored k
          CROSS JOIN LATERAL (
               SELECT DISTINCT c.ts FROM public.option_chain_snapshots c
                WHERE c.symbol = k.symbol AND c.expiry_date = k.expiry_date
                  AND c.ts >= ((k.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
                  AND c.ts <= ((k.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
          ) t
     ), px AS (
        SELECT y.symbol, y.session_date, y.expiry_date, y.anchor_ts, y.ts,
               c.strike, c.option_type, c.oi, c.delta, c.iv, c.spot
          FROM cycles y
          JOIN public.option_chain_snapshots c
            ON c.symbol = y.symbol AND c.expiry_date = y.expiry_date AND c.ts = y.ts
     ), k AS (
        SELECT p.symbol, p.session_date, p.expiry_date, p.anchor_ts, p.ts, p.strike,
               max(p.spot)                                     AS spot,
               min(p.spot)                                     AS spot_min,
               count(*)                                        AS n_rows,
               count(DISTINCT p.option_type)                   AS n_types,
               max(p.oi)    FILTER (WHERE p.option_type = 'CE') AS oi_call,
               max(p.oi)    FILTER (WHERE p.option_type = 'PE') AS oi_put,
               max(p.delta) FILTER (WHERE p.option_type = 'CE') AS delta_call,
               min(p.delta) FILTER (WHERE p.option_type = 'PE') AS delta_put,
               bool_or(p.option_type = 'CE'
                       AND (p.delta IS NULL OR (p.delta = 0 AND COALESCE(p.iv, 0) = 0))) AS call_gap,
               bool_or(p.option_type = 'PE'
                       AND (p.delta IS NULL OR (p.delta = 0 AND COALESCE(p.iv, 0) = 0))) AS put_gap
          FROM px p
         GROUP BY p.symbol, p.session_date, p.expiry_date, p.anchor_ts, p.ts, p.strike
     ), kk AS (
        SELECT k.*, a.a_oi_call, a.a_oi_put, (a.symbol IS NULL) AS cycle_only,
               -- a CE delta usable for the parity set: present and not a gap
               (k.delta_call IS NOT NULL AND NOT COALESCE(k.call_gap, false)) AS call_ok,
               k.oi_call - a.a_oi_call AS d_call,
               k.oi_put  - a.a_oi_put  AS d_put
          FROM k
          LEFT JOIN ak a ON a.symbol = k.symbol AND a.strike = k.strike
     ), v AS (
        SELECT kk.*,
               CASE WHEN COALESCE(oi_call, 0) = 0 THEN 0
                    WHEN call_gap THEN NULL
                    ELSE delta_call * oi_call * spot / 1e7 END                AS b_call,
               CASE WHEN COALESCE(oi_put, 0) = 0 THEN 0
                    WHEN put_gap THEN NULL
                    ELSE delta_put * oi_put * spot / 1e7 END                  AS b_put_v,
               CASE WHEN COALESCE(oi_put, 0) = 0 THEN 0
                    WHEN NOT call_ok THEN NULL
                    ELSE (delta_call - 1) * oi_put * spot / 1e7 END           AS b_put_p,
               CASE WHEN d_call IS NULL THEN NULL
                    WHEN d_call = 0 THEN 0
                    WHEN call_gap THEN NULL
                    ELSE delta_call * d_call * spot / 1e7 END                 AS f_call,
               CASE WHEN d_put IS NULL THEN NULL
                    WHEN d_put = 0 THEN 0
                    WHEN put_gap THEN NULL
                    ELSE delta_put * d_put * spot / 1e7 END                   AS f_put_v,
               CASE WHEN d_put IS NULL THEN NULL
                    WHEN d_put = 0 THEN 0
                    WHEN NOT call_ok THEN NULL
                    ELSE (delta_call - 1) * d_put * spot / 1e7 END            AS f_put_p
          FROM kk
     )
SELECT v.symbol,
       v.session_date,
       v.expiry_date,
       (v.expiry_date - v.session_date)                                       AS dte,
       to_char(v.anchor_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS')         AS anchor_ist,
       to_char(v.ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS')                AS cycle_ist,
       count(*)                                                               AS n_strikes,
       count(*) FILTER (WHERE v.n_rows <> v.n_types)                          AS n_dupe_strikes,
       count(*) FILTER (WHERE v.cycle_only)                                   AS n_cycle_only_strikes,
       max(t.anchor_n_strikes)                                                AS anchor_n_strikes,
       max(t.anchor_oi_qty)                                                   AS anchor_oi_qty,
       max(v.spot) - min(v.spot_min)                                          AS spot_spread,
       max(v.spot)                                                            AS spot,
       sum(COALESCE(v.oi_call, 0) + COALESCE(v.oi_put, 0))                    AS oi_qty,
       sum(COALESCE(v.b_call, 0))                                             AS book_call,
       sum(COALESCE(v.b_put_v, 0))                                            AS book_put_v,
       sum(COALESCE(v.b_put_p, 0))                                            AS book_put_p,
       sum(abs(COALESCE(v.b_call, 0)) + abs(COALESCE(v.b_put_v, 0)))          AS book_gross_v,
       sum(CASE WHEN v.b_call  IS NULL THEN COALESCE(v.oi_call, 0) ELSE 0 END
         + CASE WHEN v.b_put_v IS NULL THEN COALESCE(v.oi_put,  0) ELSE 0 END) AS book_gap_oi_v,
       sum(CASE WHEN v.b_call  IS NULL THEN COALESCE(v.oi_call, 0) ELSE 0 END
         + CASE WHEN v.b_put_p IS NULL THEN COALESCE(v.oi_put,  0) ELSE 0 END) AS book_gap_oi_p,
       sum(COALESCE(v.f_call, 0))                                             AS flow_call,
       sum(COALESCE(v.f_put_v, 0))                                            AS flow_put_v,
       sum(COALESCE(v.f_put_p, 0))                                            AS flow_put_p,
       sum(abs(COALESCE(v.f_call, 0)) + abs(COALESCE(v.f_put_v, 0)))          AS flow_gross_v,
       sum(abs(COALESCE(v.d_call, 0)) + abs(COALESCE(v.d_put, 0)))            AS abs_doi_qty,
       sum(CASE WHEN v.d_call IS NOT NULL AND v.f_call  IS NULL THEN abs(v.d_call) ELSE 0 END
         + CASE WHEN v.d_put  IS NOT NULL AND v.f_put_v IS NULL THEN abs(v.d_put)  ELSE 0 END) AS flow_gap_doi_v,
       sum(CASE WHEN v.d_call IS NOT NULL AND v.f_call  IS NULL THEN abs(v.d_call) ELSE 0 END
         + CASE WHEN v.d_put  IS NOT NULL AND v.f_put_p IS NULL THEN abs(v.d_put)  ELSE 0 END) AS flow_gap_doi_p,
       sum(CASE WHEN v.d_call IS NULL THEN COALESCE(v.oi_call, 0) ELSE 0 END
         + CASE WHEN v.d_put  IS NULL THEN COALESCE(v.oi_put,  0) ELSE 0 END) AS no_anchor_oi_qty
  FROM v
  JOIN ak_tot t ON t.symbol = v.symbol
 GROUP BY v.symbol, v.session_date, v.expiry_date, v.anchor_ts, v.ts
 ORDER BY v.symbol, v.ts;
