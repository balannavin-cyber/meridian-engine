-- Part 0 step 2 (cont): measured facts behind the column mapping.
-- Each row is a measurement, not a claim.
\pset format csv
-- (a) futures expiry_date is unusable: how many NIFTY rows carry one?
SELECT 'fut_expiry_date_nonnull' AS fact,
       count(*)::text AS denom, count(expiry_date)::text AS value
FROM hist_future_bars_1m
WHERE instrument_id = '9992f600-51b3-4009-b487-f878692a0bc5';
-- (b) vendor greeks on hist_option_bars_1m: present at all, on one sampled session?
SELECT 'opt_bars_vendor_cols_2025-10-15' AS fact,
       count(*)::text AS denom,
       ('iv=' || count(iv) || ' delta=' || count(delta) || ' gamma=' || count(gamma)) AS value
FROM hist_option_bars_1m
WHERE instrument_id = '9992f600-51b3-4009-b487-f878692a0bc5'
  AND trade_date = '2025-10-15'
  AND bar_ts = timestamptz '2025-10-15 15:29:59+00';
-- (c) the join the prereg claims measures 100%: bars -> greeks on the 5-col key,
--     one sampled session-minute.
SELECT 'bars_to_greeks_join_2025-10-15_1529' AS fact,
       count(*)::text AS denom,
       count(g.id)::text AS value
FROM hist_option_bars_1m b
LEFT JOIN hist_option_greeks_1m g
  ON  g.instrument_id = b.instrument_id AND g.bar_ts = b.bar_ts
  AND g.expiry_date   = b.expiry_date   AND g.strike = b.strike
  AND g.option_type   = b.option_type
WHERE b.instrument_id = '9992f600-51b3-4009-b487-f878692a0bc5'
  AND b.trade_date = '2025-10-15'
  AND b.bar_ts = timestamptz '2025-10-15 15:29:59+00';
