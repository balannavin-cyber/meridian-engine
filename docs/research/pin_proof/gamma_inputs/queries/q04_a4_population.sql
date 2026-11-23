\pset format unaligned
\pset fieldsep '|'
-- A4 population split. For every leg with oi > 0, ltp > 0 and chain gamma = 0,
-- read the stored vendor payload and ask whether the vendor sent NOTHING for the
-- leg (delta, vega, theta all 0 as well) or sent the other greeks and only gamma
-- came through as 0 -- which at the vendor's observed 5-decimal quantisation means
-- |gamma| < 5e-6 rather than "absent".
-- Scope: the last 10 runs of 2026-11-19 per symbol, front expiry.
WITH r AS (
  SELECT symbol, run_id, expiry_date, ts,
         row_number() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-19 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
), pick AS (
  SELECT * FROM r WHERE rn <= 10
), legs AS (
  SELECT p.symbol, o.oi::float8 AS oi, o.gamma::float8 AS gamma, o.iv::float8 AS iv,
         CASE WHEN upper(o.option_type) = 'CE'
              THEN (o.spot::float8 - o.strike::float8) / o.spot::float8
              ELSE (o.strike::float8 - o.spot::float8) / o.spot::float8 END AS m,
         ((o.raw -> 'greeks') ->> 'delta')::float8 AS rd,
         ((o.raw -> 'greeks') ->> 'vega')::float8  AS rv,
         ((o.raw -> 'greeks') ->> 'theta')::float8 AS rt,
         ((o.raw -> 'greeks') ->> 'gamma')::float8 AS rg,
         (o.raw -> 'greeks') IS NULL AS no_greeks_key,
         ((o.raw -> 'greeks') ->> 'gamma') IS NULL AS no_gamma_key
    FROM pick p
    JOIN option_chain_snapshots o
      ON o.run_id = p.run_id AND o.expiry_date = p.expiry_date
   WHERE o.oi > 0 AND o.ltp > 0 AND o.gamma = 0
     AND o.spot IS NOT NULL AND o.spot > 0 AND o.strike > 0
)
SELECT symbol,
       CASE WHEN m < 0 THEN '1_OTM'
            WHEN m < 0.01 THEN '2_ITM_0_1'
            WHEN m < 0.02 THEN '3_ITM_1_2'
            WHEN m < 0.05 THEN '4_ITM_2_5'
            ELSE '5_ITM_5P' END AS bkt,
       count(*) AS blank_legs,
       count(*) FILTER (WHERE no_greeks_key) AS raw_no_greeks_key,
       count(*) FILTER (WHERE no_gamma_key) AS raw_no_gamma_key,
       count(*) FILTER (WHERE rg = 0) AS raw_gamma_literal_zero,
       count(*) FILTER (WHERE rd = 0 AND rv = 0 AND rt = 0) AS vendor_sent_nothing,
       count(*) FILTER (WHERE NOT (rd = 0 AND rv = 0 AND rt = 0)) AS gamma_only_zero,
       count(*) FILTER (WHERE NOT (rd = 0 AND rv = 0 AND rt = 0) AND iv > 0) AS gamma_only_zero_iv_pos,
       sum(oi) AS oi_sum,
       coalesce(sum(oi) FILTER (WHERE rd = 0 AND rv = 0 AND rt = 0), 0) AS oi_vendor_sent_nothing
  FROM legs
 GROUP BY 1,2 ORDER BY 1,2;
-- Quantisation control: every DISTINCT non-zero vendor gamma on one run must be an
-- exact multiple of 1e-5 if the vendor rounds to 5 decimals. A single counter-example
-- refutes the quantisation reading.
WITH r AS (
  SELECT symbol, run_id, expiry_date, ts,
         row_number() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-19 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
), pick AS (SELECT * FROM r WHERE rn = 1)
SELECT p.symbol, count(*) AS legs_gamma_pos,
       count(DISTINCT o.gamma) AS distinct_gamma,
       count(*) FILTER (WHERE (o.gamma * 100000) <> round(o.gamma * 100000)) AS not_mult_of_1e5,
       min(o.gamma) AS min_pos_gamma, max(o.gamma) AS max_gamma
  FROM pick p
  JOIN option_chain_snapshots o
    ON o.run_id = p.run_id AND o.expiry_date = p.expiry_date
 WHERE o.gamma > 0
 GROUP BY 1 ORDER BY 1;
