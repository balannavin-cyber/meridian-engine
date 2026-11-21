-- Part 0 step 3: per-month chain coverage. Scoped to ONE month per run because
-- hist_option_bars_1m is 54.8M rows and roq.sh pins statement_timeout=30s.
-- "solved iv" is reported three ways; the operative one for M1 is close_iv.
\pset format csv
SELECT :'ym' AS ym,
       (SELECT count(DISTINCT trade_date) FROM hist_option_bars_1m
         WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi') AS optbar_sessions,
       (SELECT count(DISTINCT trade_date) FROM hist_option_greeks_1m
         WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi') AS greeks_sessions,
       (SELECT count(DISTINCT trade_date) FROM hist_option_greeks_1m
         WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi'
           AND iv IS NOT NULL) AS greeks_sessions_any_iv,
       (SELECT count(DISTINCT trade_date) FROM hist_option_greeks_1m
         WHERE instrument_id = :'nifty' AND trade_date BETWEEN :'lo' AND :'hi'
           AND iv IS NOT NULL AND bar_ts::time = '15:29:59') AS greeks_sessions_close_iv;
