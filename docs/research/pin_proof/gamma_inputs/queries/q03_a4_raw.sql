\pset format unaligned
\pset fieldsep '|'
-- A4: the stored vendor payload for legs that are BLANK in the chain columns.
-- option_chain_snapshots.raw is the vendor's own per-leg dict (ingest_option_chain_local.py:311
-- stores `option_raw` verbatim, and `greeks` is a nested key of it).
-- One NIFTY run and one SENSEX run, latest run of 2026-11-19, front expiry.
WITH r AS (
  SELECT symbol, run_id, expiry_date, ts,
         row_number() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-19 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
), pick AS (
  SELECT * FROM r WHERE rn = 1
), legs AS (
  SELECT p.symbol, o.strike, o.option_type, o.spot, o.oi, o.ltp,
         o.gamma, o.iv, o.delta, o.vega, o.theta,
         (o.raw ? 'greeks') AS raw_has_greeks,
         (o.raw -> 'greeks')::text AS raw_greeks,
         (o.raw ->> 'implied_volatility') AS raw_iv,
         (o.raw ->> 'last_price') AS raw_ltp,
         (SELECT string_agg(k, ',' ORDER BY k) FROM jsonb_object_keys(o.raw) k) AS raw_keys,
         CASE WHEN o.gamma IS NULL THEN 'G_NULL' WHEN o.gamma = 0 THEN 'G_ZERO' ELSE 'G_POS' END AS gstate,
         row_number() OVER (PARTITION BY p.symbol,
             CASE WHEN o.gamma IS NULL THEN 'G_NULL' WHEN o.gamma = 0 THEN 'G_ZERO' ELSE 'G_POS' END
             ORDER BY o.oi DESC) AS rk
    FROM pick p
    JOIN option_chain_snapshots o
      ON o.run_id = p.run_id AND o.expiry_date = p.expiry_date
   WHERE o.oi > 0 AND o.ltp > 0
)
SELECT symbol, gstate, strike, option_type, spot, oi, ltp, gamma, iv,
       raw_has_greeks, raw_greeks, raw_iv, raw_keys
  FROM legs
 WHERE rk <= 3
 ORDER BY symbol, gstate, rk;
