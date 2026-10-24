-- R10: per-strike net gamma exposure (gex_strike_snapshots.gex_cr, vendor gamma, at the observed spot) at the same chain ts
-- the repriced-curve queries use; the strikes D2-2 named (NIFTY 22,450 / 22,500; SENSEX 72,600 / 72,700) with neighbours.
WITH t AS (
  SELECT 'NIFTY'::text AS symbol, (SELECT max(ts) FROM option_chain_snapshots WHERE symbol='NIFTY' AND ts >= TIMESTAMPTZ '2026-10-14 08:15:00+00' AND ts <= TIMESTAMPTZ '2026-10-14 08:26:59+00') AS ts, 22300 AS lo, 22650 AS hi
  UNION ALL
  SELECT 'SENSEX', (SELECT max(ts) FROM option_chain_snapshots WHERE symbol='SENSEX' AND ts >= TIMESTAMPTZ '2026-10-14 08:50:00+00' AND ts <= TIMESTAMPTZ '2026-10-14 09:01:59+00'), 72300, 72900)
SELECT g.symbol, to_char(g.ts AT TIME ZONE 'Asia/Kolkata','HH24:MI:SS') AS ts_ist, g.expiry_date, round(g.spot::numeric,2) AS spot,
       g.strike, round(g.gex_cr::numeric,0) AS gex_cr, CASE WHEN g.gex_cr < 0 THEN '-' ELSE '+' END AS sgn
  FROM gex_strike_snapshots g JOIN t ON g.symbol = t.symbol AND g.ts = t.ts
 WHERE g.strike BETWEEN t.lo AND t.hi
 ORDER BY g.symbol, g.strike;
