-- hist_gamma_metrics.net_gex for control C3 (section 5).
-- C3 compares sign(g), computed here from the chain, with sign(net_gex) as the
-- board computes it. Only the SIGN is compared, so the scale conventions
-- TD-S103-NEW-4 records (seven copies of the Gamma formula at four scales) do
-- not by themselves move this number -- but a convention that differs in SIGN
-- would, which is why C3 is a control and not a formality.
--
-- hist_gamma_metrics is 183,872 rows / 46 MB, so the whole window at the 69
-- window boundaries is one query, not a per-session loop.
\pset format csv
SELECT trade_date::text AS trade_date,
       to_char(bar_ts, 'HH24:MI:SS') AS hhmmss,
       net_gex,
       spot
FROM hist_gamma_metrics
WHERE symbol = 'NIFTY'
  AND trade_date BETWEEN :'lo' AND :'hi'
  AND to_char(bar_ts, 'MI')::int % 5 = 0
  AND bar_ts::time BETWEEN '09:20:59' AND '15:00:59'
ORDER BY trade_date, bar_ts;
