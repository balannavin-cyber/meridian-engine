-- All NIFTY spot 1-minute bars in the window, same session clock.
\pset format csv
SELECT trade_date::text AS trade_date,
       to_char(bar_ts, 'HH24:MI:SS') AS hhmmss,
       close
FROM hist_spot_bars_1m
WHERE instrument_id = :'nifty'
  AND trade_date BETWEEN :'lo' AND :'hi'
  AND bar_ts::time BETWEEN '09:15:59' AND '15:29:59'
ORDER BY trade_date, bar_ts;
