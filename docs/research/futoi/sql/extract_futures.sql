-- All NIFTY futures 1-minute bars in the window, series 1/2/3, inside the
-- session 09:15:59..15:29:59 (vendor clock, IST written as UTC, :59 seconds).
-- The 15:30 bar is never used (prereg section 2).
\pset format csv
SELECT trade_date::text AS trade_date,
       to_char(bar_ts, 'HH24:MI:SS') AS hhmmss,
       contract_series, close, oi, volume
FROM hist_future_bars_1m
WHERE instrument_id = :'nifty'
  AND trade_date BETWEEN :'lo' AND :'hi'
  AND bar_ts::time BETWEEN '09:15:59' AND '15:29:59'
ORDER BY trade_date, contract_series, bar_ts;
