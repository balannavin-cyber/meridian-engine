\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Futures coverage probe for the Part B sampled minutes. __IID__ instrument_id,
-- __SYM__ symbol, __D__ trade_date. ONE statement, (tag, payload) UNION ALL.
--
-- Discovery only: does a futures bar exist at each sampled minute, and what is its
-- contract_series / expiry_date / close. NOTHING is re-solved here.
--
-- Two probes per target minute, both exact-key index lookups:
--   EXACT   -- a bar at the identical bar_ts (same IST-clock-labelled-+00:00 convention
--              as hist_option_bars_1m). This is what a sensitivity run would join on.
--   NEAREST -- the closest bar within +/-120 s, returned even when EXACT hits.
-- The NEAREST leg exists so that an EXACT miss can be told apart from a clock-convention
-- mismatch: zero rows on both means no data, zero on EXACT with a hit on NEAREST at a
-- non-zero offset means the two stores do not share a bar_ts convention. A zero from the
-- EXACT leg alone is NOT evidence of absence.
WITH tgt(tname, tts) AS (
  VALUES ('10:00', timestamptz '__D__ 10:00:59+00'),
         ('12:30', timestamptz '__D__ 12:30:59+00'),
         ('15:00', timestamptz '__D__ 15:00:59+00')
)
SELECT tag, payload FROM (
  -- F1: every futures contract present at the EXACT sampled bar_ts
  SELECT 'F1' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, g.tname,
           f.contract_series, f.expiry_date::text AS expiry_date,
           f.close::float8 AS fut_close, f.oi, f.volume,
           (f.expiry_date - date '__D__') AS fut_dte
      FROM tgt g
      JOIN hist_future_bars_1m f
        ON f.instrument_id = '__IID__' AND f.bar_ts = g.tts
  ) t
  UNION ALL
  -- F2: per target minute, whether EXACT hit at all, and the NEAREST bar within 120 s
  SELECT 'F2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, g.tname,
           (ex.n IS NOT NULL AND ex.n > 0) AS exact_hit,
           coalesce(ex.n, 0) AS exact_contracts,
           nr.off_sec AS nearest_off_sec,
           nr.contract_series AS nearest_series,
           nr.close::float8 AS nearest_close
      FROM tgt g
      LEFT JOIN LATERAL (
        SELECT count(*) AS n
          FROM hist_future_bars_1m f
         WHERE f.instrument_id = '__IID__' AND f.bar_ts = g.tts
      ) ex ON true
      LEFT JOIN LATERAL (
        SELECT extract(epoch FROM (f.bar_ts - g.tts)) AS off_sec,
               f.contract_series, f.close
          FROM hist_future_bars_1m f
         WHERE f.instrument_id = '__IID__'
           AND f.bar_ts >= g.tts - interval '120 seconds'
           AND f.bar_ts <= g.tts + interval '120 seconds'
         ORDER BY abs(extract(epoch FROM (f.bar_ts - g.tts))), f.contract_series
         LIMIT 1
      ) nr ON true
  ) t
) u;
