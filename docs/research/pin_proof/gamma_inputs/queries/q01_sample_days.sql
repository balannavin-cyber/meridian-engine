\pset format unaligned
\pset fieldsep '|'
-- instruments
SELECT 'IID' AS k, symbol, id FROM instruments WHERE symbol IN ('NIFTY','SENSEX') ORDER BY symbol;
-- backfill log: status spread inside the B window
SELECT 'LOGSTAT' AS k, symbol, status, count(*) AS days,
       min(trade_date) AS d0, max(trade_date) AS d1,
       sum(rows_written) AS rows_written, sum(rows_null_iv) AS rows_null_iv
  FROM hist_greeks_backfill_log
 WHERE trade_date >= '2025-04-01' AND trade_date <= '2026-03-30'
 GROUP BY 1,2,3 ORDER BY 2,3;
-- candidate sample days: first DONE trade_date of each month
SELECT 'FIRSTDAY' AS k, symbol, to_char(trade_date,'YYYY-MM') AS ym,
       min(trade_date) AS first_done_day, count(*) AS done_days_in_month
  FROM hist_greeks_backfill_log
 WHERE trade_date >= '2025-04-01' AND trade_date <= '2026-03-30'
   AND status = 'DONE' AND rows_written > 0
 GROUP BY 1,2,3 ORDER BY 2,3;
