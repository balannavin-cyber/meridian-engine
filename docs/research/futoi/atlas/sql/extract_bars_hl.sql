-- Atlas extraction: 1-minute bars WITH high and low.
--
-- The closed M1/M2 run's data/futures_bars.csv and data/spot_bars.csv carry
-- close only. Studies A and C need ranges, so high and low are pulled here
-- rather than approximated from closes.
--
-- NIFTY only. Window 2025-04-01 .. 2026-03-30 enforced in the predicate, so
-- nothing after the window end is read (the Stage 1 holdout stays sealed) --
-- hist_spot_bars_1m in particular runs to 2026-11-17.
--
-- Session clock 09:15:59 .. 15:29:59 on the vendor clock, no conversion.
-- The 15:30 bar is never used.
--
-- :which is 'fut' (series 1 only) or 'spot'.
\pset format csv
SELECT trade_date::text AS trade_date,
       to_char(bar_ts, 'HH24:MI:SS') AS hhmmss,
       high, low, close,
       CASE WHEN :'which' = 'fut' THEN oi     ELSE NULL END AS oi,
       CASE WHEN :'which' = 'fut' THEN volume ELSE NULL END AS volume
FROM (
  SELECT trade_date, bar_ts, high, low, close, oi, volume
  FROM hist_future_bars_1m
  WHERE :'which' = 'fut'
    AND instrument_id = :'nifty' AND contract_series = 1
    AND trade_date BETWEEN :'lo' AND :'hi'
    AND bar_ts::time BETWEEN '09:15:59' AND '15:29:59'
  UNION ALL
  SELECT trade_date, bar_ts, high, low, close, NULL::bigint, NULL::bigint
  FROM hist_spot_bars_1m
  WHERE :'which' = 'spot'
    AND instrument_id = :'nifty'
    AND trade_date BETWEEN :'lo' AND :'hi'
    AND bar_ts::time BETWEEN '09:15:59' AND '15:29:59'
) q
ORDER BY trade_date, bar_ts;
