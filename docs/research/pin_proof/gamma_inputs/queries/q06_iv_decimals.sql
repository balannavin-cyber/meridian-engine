\pset format unaligned
\pset fieldsep '|'
-- Decimal places carried by the vendor's own implied_volatility, read from the
-- stored raw payload (NOT from the typed iv column), on ONE run per symbol:
-- the last front-expiry run of 2026-11-19. Answers whether the Q2 control is
-- a comparison against a full-precision field or against a 2-dp field.
WITH r AS (
  SELECT symbol, run_id, expiry_date, ts,
         row_number() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-19 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
), pick AS (SELECT * FROM r WHERE rn = 1), dp AS (
  SELECT p.symbol,
         length(split_part(o.raw ->> 'implied_volatility', '.', 2)) AS iv_dp,
         length(split_part((o.raw -> 'greeks') ->> 'gamma', '.', 2)) AS g_dp
    FROM pick p
    JOIN option_chain_snapshots o
      ON o.run_id = p.run_id AND o.expiry_date = p.expiry_date
   WHERE (o.raw ->> 'implied_volatility') IS NOT NULL
)
SELECT symbol, 'iv' AS field, iv_dp AS decimal_places, count(*) AS legs
  FROM dp GROUP BY 1,2,3
UNION ALL
SELECT symbol, 'gamma', g_dp, count(*) FROM dp GROUP BY 1,2,3
ORDER BY 1,2,3;
