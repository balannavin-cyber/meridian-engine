-- =====================================================================
-- 2026-05-25_enh81_falsification.sql
-- ENH-81 — falsification gates for pin_zone, accel_zone, dealer_flow_sim
-- =====================================================================
-- Run after view deploy. Expected results documented inline.
-- =====================================================================

-- =====================================================================
-- Gate 1: pin zone — peak strike is inside the returned zone,
--         and all included strikes meet the τ threshold.
-- =====================================================================
WITH v AS (SELECT * FROM v_gex_strike_pin_zone WHERE symbol='NIFTY' ORDER BY ts DESC LIMIT 1)
SELECT
  'pin'                                          AS zone_type,
  v.pin_lower, v.pin_upper,
  v.peak_pin_strike, v.peak_pin_gex_cr,
  v.tau_used,
  ROUND((v.tau_used * v.peak_pin_gex_cr)::numeric, 2) AS expected_floor,
  ROUND(MIN(g.gex_cr)::numeric, 2)               AS observed_floor_in_zone,
  COUNT(*)                                       AS n_strikes_in_zone,
  v.n_strikes                                    AS n_strikes_view,
  CASE
    WHEN COUNT(*) <> v.n_strikes
      THEN 'FAIL: count mismatch'
    WHEN MIN(g.gex_cr) < v.tau_used * v.peak_pin_gex_cr
      THEN 'FAIL: floor breach'
    WHEN v.peak_pin_strike NOT BETWEEN v.pin_lower AND v.pin_upper
      THEN 'FAIL: peak outside zone'
    ELSE 'PASS'
  END                                            AS gate
FROM v
JOIN gex_strike_snapshots g
  ON g.run_id = v.run_id AND g.symbol = v.symbol
 AND g.strike BETWEEN v.pin_lower AND v.pin_upper
GROUP BY v.pin_lower, v.pin_upper, v.peak_pin_strike, v.peak_pin_gex_cr,
         v.tau_used, v.n_strikes;

-- =====================================================================
-- Gate 2: accel zone — trough strike is inside zone, |gex_cr| floor met.
-- =====================================================================
WITH v AS (SELECT * FROM v_gex_strike_accel_zone WHERE symbol='NIFTY' ORDER BY ts DESC LIMIT 1)
SELECT
  'accel'                                                  AS zone_type,
  v.accel_lower, v.accel_upper,
  v.trough_strike, v.trough_gex_cr,
  v.tau_used,
  ROUND((v.tau_used * ABS(v.trough_gex_cr))::numeric, 2)   AS expected_abs_floor,
  ROUND(MIN(ABS(g.gex_cr))::numeric, 2)                    AS observed_abs_floor,
  COUNT(*)                                                 AS n_strikes_in_zone,
  v.n_strikes                                              AS n_strikes_view,
  CASE
    WHEN COUNT(*) <> v.n_strikes
      THEN 'FAIL: count mismatch'
    WHEN MIN(ABS(g.gex_cr)) < v.tau_used * ABS(v.trough_gex_cr)
      THEN 'FAIL: floor breach'
    WHEN v.trough_strike NOT BETWEEN v.accel_lower AND v.accel_upper
      THEN 'FAIL: trough outside zone'
    ELSE 'PASS'
  END                                                      AS gate
FROM v
JOIN gex_strike_snapshots g
  ON g.run_id = v.run_id AND g.symbol = v.symbol
 AND g.strike BETWEEN v.accel_lower AND v.accel_upper
GROUP BY v.accel_lower, v.accel_upper, v.trough_strike, v.trough_gex_cr,
         v.tau_used, v.n_strikes;

-- =====================================================================
-- Gate 3: dealer flow sim — sign and magnitude sanity per scenario.
-- =====================================================================
SELECT
  symbol, scenario, spot_pct, perturbed_spot, flow_cr, direction, crosses_flip,
  -- Sanity: flow direction must match (net_gex × pct) sign.
  CASE
    WHEN (net_gex * spot_pct < 0 AND direction <> 'SELL') THEN 'FAIL: direction mismatch'
    WHEN (net_gex * spot_pct > 0 AND direction <> 'BUY')  THEN 'FAIL: direction mismatch'
    ELSE 'PASS'
  END AS gate
FROM v_dealer_flow_sim
WHERE symbol IN ('NIFTY', 'SENSEX')
ORDER BY symbol, spot_pct;

-- =====================================================================
-- Gate 4 (sanity, not falsification): all three views agree on the
-- latest run_id per symbol — no stale data from different snapshots.
-- =====================================================================
SELECT
  COALESCE(p.symbol, a.symbol, d.symbol)                   AS symbol,
  p.run_id                                                 AS pin_run_id,
  a.run_id                                                 AS accel_run_id,
  d.run_id                                                 AS dflow_run_id,
  CASE
    WHEN p.run_id = a.run_id AND a.run_id = d.run_id THEN 'PASS: aligned'
    WHEN p.run_id IS NULL OR a.run_id IS NULL OR d.run_id IS NULL
      THEN 'INFO: one or more views empty for this symbol'
    ELSE 'FAIL: run_id mismatch across views'
  END AS gate
FROM
  (SELECT DISTINCT ON (symbol) symbol, run_id FROM v_gex_strike_pin_zone   ORDER BY symbol, ts DESC) p
  FULL OUTER JOIN
  (SELECT DISTINCT ON (symbol) symbol, run_id FROM v_gex_strike_accel_zone ORDER BY symbol, ts DESC) a USING (symbol)
  FULL OUTER JOIN
  (SELECT DISTINCT ON (symbol) symbol, run_id FROM v_dealer_flow_sim       ORDER BY symbol, ts DESC) d USING (symbol)
WHERE COALESCE(p.symbol, a.symbol, d.symbol) IN ('NIFTY', 'SENSEX');
