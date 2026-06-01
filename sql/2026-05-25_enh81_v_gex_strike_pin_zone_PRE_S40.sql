-- =====================================================================
-- 2026-05-25_enh81_v_gex_strike_pin_zone.sql
-- ENH-81 — Positioning Landscape: pin zone view (prominence-around-peak)
-- =====================================================================
--
-- Algorithm: walk outward from peak strike by exact strike-value steps.
-- Single recursive term (Postgres requires <anchor> UNION ALL <one_rec>).
-- Direction tracked via CASE in the recursive SELECT.
--
-- Threshold: τ_pin = 0.3 hardcoded. ENH-83 swap target:
--   COALESCE((SELECT (value)::numeric FROM merdian_parameters
--             WHERE key = 'pin_zone.tau.' || symbol AND valid_to IS NULL), 0.3)
--
-- Verified algorithm against operator's NIFTY snapshot (S37 2026-05-25):
--   spot=24057, expected pin=[24100, 24200], n=3, peak=580341 at 24200.
-- =====================================================================

CREATE OR REPLACE VIEW v_gex_strike_pin_zone AS
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
peak AS (
  SELECT DISTINCT ON (run_id, symbol, expiry_date)
    run_id, symbol, expiry_date, ts, spot,
    strike AS peak_strike,
    gex_cr AS peak_gex_cr
  FROM gex_strike_snapshots
  WHERE gex_cr > 0
  ORDER BY run_id, symbol, expiry_date,
           gex_cr DESC,
           ABS(strike - spot) ASC
),
walk AS (
  -- Anchor: peak strike (direction = 0, can branch both ways)
  SELECT p.run_id, p.symbol, p.expiry_date, p.ts,
         p.peak_strike     AS strike,
         p.peak_gex_cr     AS gex_cr,
         p.peak_gex_cr,
         s.step,
         0::int            AS direction
  FROM peak p
  JOIN strike_step s USING (run_id, symbol, expiry_date)

  UNION ALL

  -- Single recursive term: both walk directions combined via OR.
  -- Direction inferred from strike comparison; further walks in opposite
  -- direction blocked by the (0,-1)/(0,+1) gating on w.direction.
  SELECT g.run_id, g.symbol, g.expiry_date, g.ts,
         g.strike,
         g.gex_cr,
         w.peak_gex_cr,
         w.step,
         CASE WHEN g.strike < w.strike THEN -1 ELSE 1 END::int AS direction
  FROM walk w
  JOIN gex_strike_snapshots g
    ON (g.run_id, g.symbol, g.expiry_date) = (w.run_id, w.symbol, w.expiry_date)
   AND (
     (w.direction IN (0, -1) AND ABS(g.strike - (w.strike - w.step)) < 0.0001)
     OR
     (w.direction IN (0,  1) AND ABS(g.strike - (w.strike + w.step)) < 0.0001)
   )
  WHERE g.gex_cr > 0
    AND g.gex_cr >= 0.3 * w.peak_gex_cr     -- TAU_PIN — swap for ENH-83 lookup
)
SELECT
  w.run_id, w.symbol, w.expiry_date, MAX(w.ts) AS ts,
  MIN(w.strike)                                              AS pin_lower,
  MAX(w.strike)                                              AS pin_upper,
  COUNT(*)                                                   AS n_strikes,
  SUM(w.gex_cr)                                              AS total_pin_gex_cr,
  MAX(w.peak_gex_cr)                                         AS peak_pin_gex_cr,
  (ARRAY_AGG(w.strike ORDER BY w.gex_cr DESC))[1]            AS peak_pin_strike,
  0.3::numeric                                               AS tau_used
FROM walk w
GROUP BY w.run_id, w.symbol, w.expiry_date;

COMMENT ON VIEW v_gex_strike_pin_zone IS
  'ENH-81 v0 — pin zone via prominence-around-peak walk-by-strike-value. Single recursive term (Postgres-compliant). τ_pin=0.3 hardcoded (ENH-83 swap pending).';
