EXPLAIN SELECT symbol, count(*) AS n, min(ts) AS min_ts, max(ts) AS max_ts FROM gex_pin_maxpain_history GROUP BY symbol;
