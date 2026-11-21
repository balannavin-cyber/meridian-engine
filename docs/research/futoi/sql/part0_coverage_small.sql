-- Part 0 step 3: coverage per month, the three small tables (whole window, one pass).
-- spot / futures / gamma_metrics are ~100MB or less and index-scan fine at year scope.
\pset format csv
SELECT 'spot' AS src, to_char(trade_date,'YYYY-MM') AS ym,
       count(DISTINCT trade_date) AS sessions, count(*) AS bars
FROM hist_spot_bars_1m
WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi'
GROUP BY 1,2
UNION ALL
SELECT 'fut_s1', to_char(trade_date,'YYYY-MM'), count(DISTINCT trade_date), count(*)
FROM hist_future_bars_1m
WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi' AND contract_series = 1
GROUP BY 1,2
UNION ALL
SELECT 'fut_s2', to_char(trade_date,'YYYY-MM'), count(DISTINCT trade_date), count(*)
FROM hist_future_bars_1m
WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi' AND contract_series = 2
GROUP BY 1,2
UNION ALL
SELECT 'fut_s3', to_char(trade_date,'YYYY-MM'), count(DISTINCT trade_date), count(*)
FROM hist_future_bars_1m
WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi' AND contract_series = 3
GROUP BY 1,2
UNION ALL
SELECT 'gamma_metrics', to_char(trade_date,'YYYY-MM'), count(DISTINCT trade_date), count(*)
FROM hist_gamma_metrics
WHERE symbol = 'NIFTY' AND trade_date BETWEEN :'lo' AND :'hi'
GROUP BY 1,2
ORDER BY 1,2;
