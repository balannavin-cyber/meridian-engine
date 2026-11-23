\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Part A per-(symbol,day) slice. __SYM__ symbol, __D__ IST date, __D1__ next IST date.
-- ONE statement: the shared CTEs are defined once and every result set is a
-- UNION ALL branch of (tag, payload) with payload = row_to_json(...)::text, so
-- the branches may carry different column lists. No temp tables, no writes.
--
-- Front-expiry runs come from gamma_metrics (one row per front-expiry run_id);
-- the S80 extra-expiry legs carry their own run_ids and have no gamma_metrics
-- row, so this join IS the front-expiry filter. Chain joined on run_id AND
-- expiry_date; gex_strike_snapshots joined on run_id AND expiry_date.
WITH r AS (
  SELECT run_id, expiry_date
    FROM gamma_metrics
   WHERE symbol = '__SYM__'
     AND ts >= timestamptz '__D__ 00:00+05:30'
     AND ts <  timestamptz '__D1__ 00:00+05:30'
     AND run_id IS NOT NULL
), c AS (
  SELECT r.run_id, o.strike::float8 AS strike, upper(o.option_type) AS ot,
         o.spot::float8 AS spot, o.oi::float8 AS oi, o.ltp::float8 AS ltp,
         o.bid::float8 AS bid, o.ask::float8 AS ask,
         o.gamma::float8 AS gamma, o.iv::float8 AS iv,
         o.gamma IS NULL AS g_is_null, o.iv IS NULL AS iv_is_null,
         CASE WHEN upper(o.option_type) = 'CE'
              THEN (o.spot::float8 - o.strike::float8) / o.spot::float8
              ELSE (o.strike::float8 - o.spot::float8) / o.spot::float8 END AS m
    FROM r
    JOIN option_chain_snapshots o
      ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
   WHERE o.spot IS NOT NULL AND o.spot > 0 AND o.strike > 0
), ck AS (
  SELECT *, CASE WHEN m < 0 THEN '1_OTM'
                 WHEN m < 0.01 THEN '2_ITM_0_1'
                 WHEN m < 0.02 THEN '3_ITM_1_2'
                 WHEN m < 0.05 THEN '4_ITM_2_5'
                 ELSE '5_ITM_5P' END AS bkt
    FROM c
), g AS (
  SELECT r.run_id, s.strike::float8 AS strike, s.spot::float8 AS spot,
         s.gamma_call::float8 AS gc, s.gamma_put::float8 AS gp,
         s.gex_cr::float8 AS gex_cr, s.oi_call, s.oi_put
    FROM r
    JOIN gex_strike_snapshots s
      ON s.run_id = r.run_id AND s.expiry_date = r.expiry_date
), x AS (  -- A3 strike-level pivot: one gss strike against its two chain legs
  SELECT g.run_id, g.strike, g.gc, g.gp, g.gex_cr, g.spot,
         ce.gamma AS ce_g, ce.oi AS ce_oi, ce.ltp AS ce_ltp,
         ce.run_id IS NULL AS ce_norow, ce.bkt AS ce_bkt,
         pe.gamma AS pe_g, pe.oi AS pe_oi, pe.ltp AS pe_ltp,
         pe.run_id IS NULL AS pe_norow, pe.bkt AS pe_bkt
    FROM g
    LEFT JOIN ck ce ON ce.run_id = g.run_id AND ce.strike = g.strike AND ce.ot = 'CE'
    LEFT JOIN ck pe ON pe.run_id = g.run_id AND pe.strike = g.strike AND pe.ot = 'PE'
)
SELECT tag, payload FROM (
  -- R0: run count and row totals for the day
  SELECT 'R0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d,
           (SELECT count(*) FROM r) AS runs,
           (SELECT count(DISTINCT expiry_date) FROM r) AS expiries,
           (SELECT min(expiry_date)::text FROM r) AS exp_min,
           (SELECT count(*) FROM ck) AS chain_legs,
           (SELECT count(*) FROM g) AS gss_strikes
  ) t
  UNION ALL
  -- R1: A2 per option_type x ITM bucket, over all runs of the day
  SELECT 'R1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, ot, bkt,
           count(*) AS legs_all,
           count(*) FILTER (WHERE oi > 0) AS legs_oi,
           count(*) FILTER (WHERE oi > 0 AND g_is_null) AS g_null,
           count(*) FILTER (WHERE oi > 0 AND NOT g_is_null AND gamma = 0) AS g_zero,
           count(*) FILTER (WHERE oi > 0 AND gamma > 0) AS g_pos,
           count(*) FILTER (WHERE oi > 0 AND iv_is_null) AS iv_null,
           count(*) FILTER (WHERE oi > 0 AND NOT iv_is_null AND iv = 0) AS iv_zero,
           count(*) FILTER (WHERE oi > 0 AND iv > 0) AS iv_pos,
           count(*) FILTER (WHERE oi > 0 AND ltp > 0) AS ltp_pos,
           count(*) FILTER (WHERE oi > 0 AND bid > 0 AND ask > 0) AS quoted,
           coalesce(sum(oi) FILTER (WHERE oi > 0), 0) AS oi_sum
      FROM ck GROUP BY 3,4
  ) t
  UNION ALL
  -- R2: A2 key cell -- oi > 0 AND ltp > 0 AND gamma blank (NULL or 0), with the iv split
  SELECT 'R2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, ot, bkt,
           count(*) AS legs_oi_px,
           count(*) FILTER (WHERE g_is_null OR gamma = 0) AS key_blank_g,
           count(*) FILTER (WHERE g_is_null) AS key_g_null,
           count(*) FILTER (WHERE NOT g_is_null AND gamma = 0) AS key_g_zero,
           count(*) FILTER (WHERE (g_is_null OR gamma = 0) AND (iv_is_null OR iv = 0)) AS key_blank_both,
           count(*) FILTER (WHERE (g_is_null OR gamma = 0) AND iv > 0) AS key_blank_g_iv_pos,
           coalesce(sum(oi), 0) AS oi_sum_oi_px,
           coalesce(sum(oi) FILTER (WHERE g_is_null OR gamma = 0), 0) AS oi_key_blank
      FROM ck WHERE oi > 0 AND ltp > 0 GROUP BY 3,4
  ) t
  UNION ALL
  -- R3/R4: A3 cross-tab, chain gamma state against gex_strike_snapshots state
  SELECT 'R3', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, 'CE' AS leg,
           CASE WHEN ce_norow THEN 'NOROW' WHEN ce_g IS NULL THEN 'NULL'
                WHEN ce_g = 0 THEN 'ZERO' ELSE 'POS' END AS chain_state,
           CASE WHEN gc IS NULL THEN 'NULL' WHEN gc = 0 THEN 'ZERO' ELSE 'POS' END AS gss_state,
           count(*) AS strikes
      FROM x GROUP BY 4,5
  ) t
  UNION ALL
  SELECT 'R4', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, 'PE' AS leg,
           CASE WHEN pe_norow THEN 'NOROW' WHEN pe_g IS NULL THEN 'NULL'
                WHEN pe_g = 0 THEN 'ZERO' ELSE 'POS' END AS chain_state,
           CASE WHEN gp IS NULL THEN 'NULL' WHEN gp = 0 THEN 'ZERO' ELSE 'POS' END AS gss_state,
           count(*) AS strikes
      FROM x GROUP BY 4,5
  ) t
  UNION ALL
  -- R5: A3 chain gamma > 0 but strike table NULL, by ITM bucket
  SELECT 'R5', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, 'CE' AS leg,
           coalesce(ce_bkt,'NA') AS bkt, count(*) AS strikes
      FROM x WHERE ce_g > 0 AND gc IS NULL GROUP BY 4
    UNION ALL
    SELECT '__SYM__', '__D__', 'PE', coalesce(pe_bkt,'NA'), count(*)
      FROM x WHERE pe_g > 0 AND gp IS NULL GROUP BY 4
  ) t
  UNION ALL
  -- R6: A3 strikes where both stored gammas > 0 and gex_cr = 0 (deep-ITM guard signature)
  SELECT 'R6', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d,
           count(*) FILTER (WHERE gc > 0 AND gp > 0) AS strikes_both_pos,
           count(*) FILTER (WHERE gc > 0 AND gp > 0 AND gex_cr = 0) AS both_pos_gex_zero,
           count(*) FILTER (WHERE gc > 0 AND gp > 0 AND gex_cr = 0
                              AND abs(strike - spot) / spot > 0.05) AS both_pos_gex_zero_deep,
           count(*) FILTER (WHERE gex_cr = 0) AS all_gex_zero,
           count(*) FILTER (WHERE gex_cr = 0 AND gc IS NULL AND gp IS NULL) AS gex_zero_both_null,
           count(*) AS gss_strikes
      FROM x
  ) t
) u ORDER BY tag, payload;
