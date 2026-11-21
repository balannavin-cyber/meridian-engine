-- Part 0 step 2 (cont): the prereg §2 claims the bars->greeks join measures 100%.
-- Chain-wide it measured 117/433 on 2025-10-15 15:29:59. Resolve per expiry.
\pset format csv
SELECT b.expiry_date::text AS expiry,
       count(*)            AS bars,
       count(g.id)         AS matched,
       round(100.0 * count(g.id) / count(*), 1) AS pct
FROM hist_option_bars_1m b
LEFT JOIN hist_option_greeks_1m g
  ON  g.instrument_id = b.instrument_id AND g.bar_ts = b.bar_ts
  AND g.expiry_date   = b.expiry_date   AND g.strike = b.strike
  AND g.option_type   = b.option_type
WHERE b.instrument_id = '9992f600-51b3-4009-b487-f878692a0bc5'
  AND b.trade_date = '2025-10-15'
  AND b.bar_ts = timestamptz '2025-10-15 15:29:59+00'
GROUP BY 1 ORDER BY 1;
