\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Second futures source probe: historical_index_futures_1m, which unlike
-- hist_future_bars_1m carries BOTH expiry_date and a price (ltp), plus a stored basis.
-- __SYM__ symbol, __D__ trade_date. Keyed by (symbol, ts), index idx on (symbol, ts).
--
-- Probed at the same 3 sampled minutes. ts convention is NOT assumed to match
-- hist_option_bars_1m: an EXACT probe at the IST-clock-labelled-+00:00 timestamp runs
-- alongside a +/-120 s NEAREST probe and a whole-day count, so three outcomes are
-- distinguishable -- no data for the day, data on a different clock convention, or data
-- at the exact minute.
WITH tgt(tname, tts) AS (
  VALUES ('10:00', timestamptz '__D__ 10:00:59+00'),
         ('12:30', timestamptz '__D__ 12:30:59+00'),
         ('15:00', timestamptz '__D__ 15:00:59+00')
)
SELECT tag, payload FROM (
  SELECT 'G1' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, g.tname,
           (ex.n IS NOT NULL AND ex.n > 0) AS exact_hit,
           coalesce(ex.n, 0) AS exact_rows,
           nr.off_sec AS nearest_off_sec,
           nr.expiry_date::text AS nearest_expiry,
           nr.ltp::float8 AS nearest_ltp,
           nr.basis::float8 AS nearest_stored_basis,
           nr.source AS nearest_source
      FROM tgt g
      LEFT JOIN LATERAL (
        SELECT count(*) AS n
          FROM historical_index_futures_1m h
         WHERE h.symbol = '__SYM__' AND h.ts = g.tts
      ) ex ON true
      LEFT JOIN LATERAL (
        SELECT extract(epoch FROM (h.ts - g.tts)) AS off_sec,
               h.expiry_date, h.ltp, h.basis, h.source
          FROM historical_index_futures_1m h
         WHERE h.symbol = '__SYM__'
           AND h.ts >= g.tts - interval '120 seconds'
           AND h.ts <= g.tts + interval '120 seconds'
         ORDER BY abs(extract(epoch FROM (h.ts - g.tts)))
         LIMIT 1
      ) nr ON true
  ) t
  UNION ALL
  -- G2: whole-day presence, so "no rows at the minute" can be told from "no rows at all".
  -- Bounded to one day on the (symbol, ts) index.
  SELECT 'G2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d,
           count(*) AS rows_in_day,
           count(DISTINCT expiry_date) AS distinct_expiries,
           min(expiry_date)::text AS min_expiry,
           count(*) FILTER (WHERE expiry_date IS NULL) AS rows_null_expiry,
           count(*) FILTER (WHERE ltp IS NULL) AS rows_null_ltp,
           min(to_char(ts AT TIME ZONE 'UTC', 'HH24:MI:SS')) AS first_clock,
           max(to_char(ts AT TIME ZONE 'UTC', 'HH24:MI:SS')) AS last_clock
      FROM historical_index_futures_1m
     WHERE symbol = '__SYM__'
       AND ts >= timestamptz '__D__ 00:00:00+00'
       AND ts <  timestamptz '__D__ 00:00:00+00' + interval '1 day'
  ) t
) u;
