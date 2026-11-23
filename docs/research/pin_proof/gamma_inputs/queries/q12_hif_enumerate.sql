\pset format aligned
-- historical_index_futures_1m is ~2,748 rows / 856 kB (q11), so a full enumeration is
-- safe and settles whether the zeros in _partG_raw.txt were real absence or a wrong
-- symbol key. Nothing is concluded from a zero until this runs.
SELECT symbol,
       count(*) AS rows,
       count(DISTINCT expiry_date) AS distinct_expiries,
       count(*) FILTER (WHERE expiry_date IS NULL) AS null_expiry,
       count(*) FILTER (WHERE ltp IS NULL) AS null_ltp,
       min(ts AT TIME ZONE 'UTC')::date AS first_day,
       max(ts AT TIME ZONE 'UTC')::date AS last_day,
       count(DISTINCT (ts AT TIME ZONE 'UTC')::date) AS distinct_days,
       string_agg(DISTINCT source, ',') AS sources
  FROM historical_index_futures_1m
 GROUP BY symbol
 ORDER BY rows DESC;
