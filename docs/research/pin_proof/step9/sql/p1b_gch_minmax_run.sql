SELECT symbol, count(*) AS n, min(ts) AT TIME ZONE 'Asia/Kolkata' AS mn_ist,
       max(ts) AT TIME ZONE 'Asia/Kolkata' AS mx_ist, count(DISTINCT (ts AT TIME ZONE 'Asia/Kolkata')::date) AS days
FROM public.gex_cycle_history WHERE symbol IN ('NIFTY','SENSEX') GROUP BY symbol ORDER BY symbol;
