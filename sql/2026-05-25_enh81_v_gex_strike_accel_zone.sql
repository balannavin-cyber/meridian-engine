-- =====================================================================
-- 2026-05-25_enh81_v_gex_strike_accel_zone.sql
-- ENH-81 — Positioning Landscape: accel zone view (sign-flipped)
-- =====================================================================
-- Same algorithm as v_gex_strike_pin_zone, operating on negative side.
-- Verified against NIFTY S37 data: trough=-819791 @ 23950 →
--   accel_lower=23800, accel_upper=24000, n=5.
-- =====================================================================

CREATE OR REPLACE VIEW v_gex_strike_accel_zone AS
WITH RECURSIVE
strike_step AS (
  SELECT run_id, symbol, expiry_date, MIN(diff) AS step
  FROM (
    SELECT run_id, symbol, expiry_date,
           strike - LAG(strike) OVER (PARTITION BY run_id, symbol, expiry_date ORDER BY strike) AS diff
    FROM gex_strike_snapshots
  ) x
  WHERE diff > 0
  GROUP BY run_id, symbol, expiry_date
),
trough AS (
  SELECT DISTINCT ON (run_id, symbol, expiry_date)
    run_id, symbol, expiry_date, ts, spot,
    strike AS trough_strike,
    gex_cr AS trough_gex_cr
  FROM gex_strike_snapshots
  WHERE gex_cr < 0
  ORDER BY run_id, symbol, expiry_date,
           gex_cr ASC,
           ABS(strike - spot) ASC
),
walk AS (
  SELECT t.run_id, t.symbol, t.expiry_date, t.ts,
         t.trough_strike    AS strike,
         t.trough_gex_cr    AS gex_cr,
         t.trough_gex_cr,
         s.step,
         0::int             AS direction
  FROM trough t
  JOIN strike_step s USING (run_id, symbol, expiry_date)

  UNION ALL

  SELECT g.run_id, g.symbol, g.expiry_date, g.ts,
         g.strike, g.gex_cr, w.trough_gex_cr, w.step,
         CASE WHEN g.strike < w.strike THEN -1 ELSE 1 END::int
  FROM walk w
  JOIN gex_strike_snapshots g
    ON (g.run_id, g.symbol, g.expiry_date) = (w.run_id, w.symbol, w.expiry_date)
   AND (
     (w.direction IN (0, -1) AND ABS(g.strike - (w.strike - w.step)) < 0.0001)
     OR
     (w.direction IN (0,  1) AND ABS(g.strike - (w.strike + w.step)) < 0.0001)
   )
  WHERE g.gex_cr < 0
    AND ABS(g.gex_cr) >= 0.3 * ABS(w.trough_gex_cr)    -- TAU_ACCEL — swap for ENH-83 lookup
)
SELECT
  w.run_id, w.symbol, w.expiry_date, MAX(w.ts) AS ts,
  MIN(w.strike)                                              AS accel_lower,
  MAX(w.strike)                                              AS accel_upper,
  COUNT(*)                                                   AS n_strikes,
  SUM(w.gex_cr)                                              AS total_accel_gex_cr,
  MIN(w.trough_gex_cr)                                       AS trough_gex_cr,
  (ARRAY_AGG(w.strike ORDER BY w.gex_cr ASC))[1]             AS trough_strike,
  0.3::numeric                                               AS tau_used
FROM walk w
GROUP BY w.run_id, w.symbol, w.expiry_date;

COMMENT ON VIEW v_gex_strike_accel_zone IS
  'ENH-81 v0 — accel zone via prominence-around-trough walk-by-strike-value. Single recursive term (Postgres-compliant). τ_accel=0.3 hardcoded (ENH-83 swap pending).';
