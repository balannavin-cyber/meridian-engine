\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Part B per-day slice. __IID__ instrument_id, __SYM__ symbol, __D__ trade_date.
-- bar_ts is IST clock labelled +00:00 (TD-029 family): literals are written +00
-- and never converted. Targets 10:00 / 12:30 / 15:00 at second :59.
--
-- ONE statement: shared CTEs once, result sets UNION ALL'd as (tag, payload)
-- with payload = row_to_json(...)::text. No temp tables, no writes.
--
-- Bar lookup reads ONLY the +/-120 s neighbourhood of each target minute, via a
-- LATERAL probe on (instrument_id, trade_date, bar_ts) -- never a DISTINCT over
-- the whole day.
WITH tgt(tname, tts) AS (
  VALUES ('10:00', timestamptz '__D__ 10:00:59+00'),
         ('12:30', timestamptz '__D__ 12:30:59+00'),
         ('15:00', timestamptz '__D__ 15:00:59+00')
), sel AS (
  SELECT t.tname, p.bar_ts,
         extract(epoch FROM (p.bar_ts - t.tts)) AS off_sec
    FROM tgt t
    CROSS JOIN LATERAL (
      SELECT ob.bar_ts
        FROM hist_option_bars_1m ob
       WHERE ob.instrument_id = '__IID__'
         AND ob.trade_date = date '__D__'
         AND ob.bar_ts >= t.tts - interval '120 seconds'
         AND ob.bar_ts <= t.tts + interval '120 seconds'
       ORDER BY abs(extract(epoch FROM (ob.bar_ts - t.tts))), ob.bar_ts
       LIMIT 1
    ) p
), fexp AS (
  SELECT s.tname, min(g.expiry_date) AS expiry
    FROM sel s
    JOIN hist_option_greeks_1m g
      ON g.instrument_id = '__IID__' AND g.bar_ts = s.bar_ts
     AND g.expiry_date >= date '__D__'
   GROUP BY 1
), spt AS (
  SELECT s.tname, hs.close::float8 AS spot
    FROM sel s
    JOIN hist_spot_bars_1m hs
      ON hs.instrument_id = '__IID__' AND hs.bar_ts = s.bar_ts
), leg AS (
  SELECT s.tname, s.bar_ts, s.off_sec, sp.spot, fe.expiry,
         ob.strike::float8 AS strike,
         (upper(ob.option_type) LIKE 'C%') AS is_call,
         ob.oi::float8 AS oi, ob.close::float8 AS px,
         g.id IS NOT NULL AS has_g,
         g.gamma::float8 AS gamma, g.iv::float8 AS iv
    FROM sel s
    JOIN spt sp ON sp.tname = s.tname
    JOIN fexp fe ON fe.tname = s.tname
    JOIN hist_option_bars_1m ob
      ON ob.instrument_id = '__IID__' AND ob.trade_date = date '__D__'
     AND ob.bar_ts = s.bar_ts AND ob.expiry_date = fe.expiry
    LEFT JOIN hist_option_greeks_1m g
      ON g.instrument_id = '__IID__' AND g.bar_ts = s.bar_ts
     AND g.strike = ob.strike AND g.option_type = ob.option_type
     AND g.expiry_date = ob.expiry_date
), lbk AS (
  SELECT *,
         CASE WHEN m < 0 THEN '1_OTM'
              WHEN m < 0.01 THEN '2_ITM_0_1'
              WHEN m < 0.02 THEN '3_ITM_1_2'
              WHEN m < 0.05 THEN '4_ITM_2_5'
              ELSE '5_ITM_5P' END AS bkt
    FROM (
      SELECT *, CASE WHEN is_call THEN (spot - strike) / spot
                     ELSE (strike - spot) / spot END AS m
        FROM leg
    ) q
)
SELECT tag, payload FROM (
  -- R0: how each sampled minute resolved
  SELECT 'R0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, s.tname,
           to_char(s.bar_ts AT TIME ZONE 'UTC', 'HH24:MI:SS') AS bar_clock,
           s.off_sec, sp.spot, fe.expiry::text AS expiry,
           (fe.expiry - date '__D__') AS dte
      FROM sel s LEFT JOIN spt sp ON sp.tname = s.tname
                 LEFT JOIN fexp fe ON fe.tname = s.tname
  ) t
  UNION ALL
  -- R1: B2 coverage by option_type x ITM bucket, legs with oi > 0, counts and OI
  SELECT 'R1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, tname,
           CASE WHEN is_call THEN 'CE' ELSE 'PE' END AS ot, bkt,
           count(*) AS legs_oi, sum(oi) AS oi_sum,
           count(*) FILTER (WHERE has_g AND gamma > 0) AS g_pos,
           count(*) FILTER (WHERE has_g AND gamma IS NULL) AS g_null,
           count(*) FILTER (WHERE has_g AND gamma = 0) AS g_zero,
           count(*) FILTER (WHERE NOT has_g) AS g_norow,
           coalesce(sum(oi) FILTER (WHERE has_g AND gamma > 0), 0) AS oi_g_pos,
           coalesce(sum(oi) FILTER (WHERE has_g AND gamma IS NULL), 0) AS oi_g_null,
           coalesce(sum(oi) FILTER (WHERE has_g AND gamma = 0), 0) AS oi_g_zero,
           coalesce(sum(oi) FILTER (WHERE NOT has_g), 0) AS oi_g_norow,
           count(*) FILTER (WHERE px > 0) AS px_pos
      FROM lbk WHERE oi > 0 GROUP BY 3,4,5
  ) t
  UNION ALL
  -- R2: B3 call-vs-put at one strike, raw per-strike ratios (pooled in python)
  SELECT 'R2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, c.tname, c.strike,
           CASE WHEN abs(c.strike - c.spot) / c.spot <= 0.01 THEN 'W1'
                WHEN abs(c.strike - c.spot) / c.spot <= 0.03 THEN 'W1_3'
                ELSE 'WOUT' END AS band,
           c.gamma / p.gamma AS g_ratio,
           CASE WHEN p.iv > 0 THEN c.iv / p.iv END AS iv_ratio
      FROM lbk c JOIN lbk p
        ON p.tname = c.tname AND p.strike = c.strike AND NOT p.is_call
     WHERE c.is_call AND c.gamma > 0 AND p.gamma > 0
  ) t
  UNION ALL
  -- R3: B4 fillable share of open interest (a strike is fillable if >= 1 leg has gamma > 0)
  SELECT 'R3', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, k.tname,
           sum(k.oi_tot) AS oi_tot,
           coalesce(sum(k.oi_tot) FILTER (WHERE k.n_pos >= 1), 0) AS oi_fillable,
           coalesce(sum(k.oi_tot) FILTER (WHERE k.n_pos = 2), 0) AS oi_both,
           coalesce(sum(k.oi_tot) FILTER (WHERE k.n_pos = 0), 0) AS oi_neither,
           count(*) AS strikes,
           count(*) FILTER (WHERE k.n_pos >= 1) AS strikes_fillable,
           count(*) FILTER (WHERE k.n_pos = 2) AS strikes_both
      FROM (
        SELECT tname, strike, sum(oi) AS oi_tot,
               count(*) FILTER (WHERE has_g AND gamma > 0) AS n_pos
          FROM lbk GROUP BY 1,2
      ) k GROUP BY 3
  ) t
) u ORDER BY tag, payload;
