-- =====================================================================
-- 2026-08-13_s69_gex_pin_accel_latest_run_scope.sql
-- S69 — pin/accel view performance fix (ADR-grade: core-table read path)
-- =====================================================================
-- PROBLEM: v_gex_strike_pin_zone / v_gex_strike_accel_zone process the
-- ENTIRE gex_strike_snapshots table (1.06M rows, 250+ sessions) on every
-- call — strike_step, peak, and the recursive walk all run unscoped across
-- all run_ids. The generator then takes ORDER BY ts DESC LIMIT 1, discarding
-- everything but the newest. Cost grew with the table until it crossed the
-- PostgREST 8s ceiling (57014 statement timeout) — pin/accel silently
-- dropped from the overlay.
--
-- FIX: introduce a `latest_run` CTE (one row per symbol: the newest run_id),
-- and INNER JOIN every heavy CTE to it, so the recursion only ever touches
-- the current snapshot. Algorithm output is byte-identical for the latest
-- snapshot — we only stop computing pin zones for ancient history nobody reads.
--
-- Supporting index makes the latest-run lookup an index seek, not a scan.
-- =====================================================================

-- 1) Index: make "latest run_id per symbol" instant.
CREATE INDEX IF NOT EXISTS ix_gex_strike_snap_sym_ts
  ON gex_strike_snapshots (symbol, ts DESC);

-- 2) PIN view — scoped to latest run per symbol.
CREATE OR REPLACE VIEW v_gex_strike_pin_zone AS
WITH RECURSIVE
latest_run AS (
  SELECT DISTINCT ON (symbol) symbol, run_id, ts
  FROM gex_strike_snapshots
  ORDER BY symbol, ts DESC
),
scoped AS (
  SELECT g.*
  FROM gex_strike_snapshots g
  JOIN latest_run lr
    ON g.symbol = lr.symbol AND g.run_id = lr.run_id
),
strike_step AS (
  SELECT run_id, symbol, expiry_date, MIN(diff) AS step
  FROM (
    SELECT run_id, symbol, expiry_date,
           strike - LAG(strike) OVER (PARTITION BY run_id, symbol, expiry_date ORDER BY strike) AS diff
    FROM scoped
  ) x
  WHERE diff > 0
  GROUP BY run_id, symbol, expiry_date
),
peak AS (
  SELECT DISTINCT ON (run_id, symbol, expiry_date)
    run_id, symbol, expiry_date, ts, spot,
    strike AS peak_strike,
    gex_cr AS peak_gex_cr
  FROM scoped
  WHERE gex_cr > 0
  ORDER BY run_id, symbol, expiry_date,
           gex_cr DESC,
           ABS(strike - spot) ASC
),
walk AS (
  SELECT p.run_id, p.symbol, p.expiry_date, p.ts,
         p.peak_strike AS strike, p.peak_gex_cr AS gex_cr, p.peak_gex_cr,
         s.step, 0::int AS direction
  FROM peak p
  JOIN strike_step s USING (run_id, symbol, expiry_date)
  UNION ALL
  SELECT g.run_id, g.symbol, g.expiry_date, g.ts,
         g.strike, g.gex_cr, w.peak_gex_cr, w.step,
         CASE WHEN g.strike < w.strike THEN -1 ELSE 1 END::int AS direction
  FROM walk w
  JOIN scoped g
    ON (g.run_id, g.symbol, g.expiry_date) = (w.run_id, w.symbol, w.expiry_date)
   AND (
     (w.direction IN (0, -1) AND ABS(g.strike - (w.strike - w.step)) < 0.0001)
     OR
     (w.direction IN (0,  1) AND ABS(g.strike - (w.strike + w.step)) < 0.0001)
   )
  WHERE g.gex_cr > 0
    AND g.gex_cr >= 0.3 * w.peak_gex_cr
)
SELECT
  w.run_id, w.symbol, w.expiry_date, MAX(w.ts) AS ts,
  MIN(w.strike) AS pin_lower,
  MAX(w.strike) AS pin_upper,
  COUNT(*) AS n_strikes,
  SUM(w.gex_cr) AS total_pin_gex_cr,
  MAX(w.peak_gex_cr) AS peak_pin_gex_cr,
  (ARRAY_AGG(w.strike ORDER BY w.gex_cr DESC))[1] AS peak_pin_strike,
  get_parameter_num('pin.tau.' || symbol)::numeric AS tau_used
FROM walk w
GROUP BY w.run_id, w.symbol, w.expiry_date;

COMMENT ON VIEW v_gex_strike_pin_zone IS
  'ENH-81 v0 + S69 perf — pin zone via prominence walk, SCOPED to latest run_id per symbol (latest_run CTE). Identical output for the current snapshot; no longer scans all history. τ_pin via get_parameter_num.';

-- 3) ACCEL view — scoped to latest run per symbol (sign-flipped twin of pin).
CREATE OR REPLACE VIEW v_gex_strike_accel_zone AS
WITH RECURSIVE
latest_run AS (
  SELECT DISTINCT ON (symbol) symbol, run_id, ts
  FROM gex_strike_snapshots
  ORDER BY symbol, ts DESC
),
scoped AS (
  SELECT g.*
  FROM gex_strike_snapshots g
  JOIN latest_run lr
    ON g.symbol = lr.symbol AND g.run_id = lr.run_id
),
strike_step AS (
  SELECT run_id, symbol, expiry_date, MIN(diff) AS step
  FROM (
    SELECT run_id, symbol, expiry_date,
           strike - LAG(strike) OVER (PARTITION BY run_id, symbol, expiry_date ORDER BY strike) AS diff
    FROM scoped
  ) x
  WHERE diff > 0
  GROUP BY run_id, symbol, expiry_date
),
trough AS (
  SELECT DISTINCT ON (run_id, symbol, expiry_date)
    run_id, symbol, expiry_date, ts, spot,
    strike AS trough_strike,
    gex_cr AS trough_gex_cr
  FROM scoped
  WHERE gex_cr < 0
  ORDER BY run_id, symbol, expiry_date,
           gex_cr ASC,
           ABS(strike - spot) ASC
),
walk AS (
  SELECT t.run_id, t.symbol, t.expiry_date, t.ts,
         t.trough_strike AS strike, t.trough_gex_cr AS gex_cr, t.trough_gex_cr,
         s.step, 0::int AS direction
  FROM trough t
  JOIN strike_step s USING (run_id, symbol, expiry_date)
  UNION ALL
  SELECT g.run_id, g.symbol, g.expiry_date, g.ts,
         g.strike, g.gex_cr, w.trough_gex_cr, w.step,
         CASE WHEN g.strike < w.strike THEN -1 ELSE 1 END::int
  FROM walk w
  JOIN scoped g
    ON (g.run_id, g.symbol, g.expiry_date) = (w.run_id, w.symbol, w.expiry_date)
   AND (
     (w.direction IN (0, -1) AND ABS(g.strike - (w.strike - w.step)) < 0.0001)
     OR
     (w.direction IN (0,  1) AND ABS(g.strike - (w.strike + w.step)) < 0.0001)
   )
  WHERE g.gex_cr < 0
    AND ABS(g.gex_cr) >= 0.3 * ABS(w.trough_gex_cr)
)
SELECT
  w.run_id, w.symbol, w.expiry_date, MAX(w.ts) AS ts,
  MIN(w.strike) AS accel_lower,
  MAX(w.strike) AS accel_upper,
  COUNT(*) AS n_strikes,
  SUM(w.gex_cr) AS total_accel_gex_cr,
  MIN(w.trough_gex_cr) AS trough_gex_cr,
  (ARRAY_AGG(w.strike ORDER BY w.gex_cr ASC))[1] AS trough_strike,
  get_parameter_num('accel.tau.' || symbol)::numeric AS tau_used
FROM walk w
GROUP BY w.run_id, w.symbol, w.expiry_date;

COMMENT ON VIEW v_gex_strike_accel_zone IS
  'ENH-81 v0 + S69 perf — accel zone via prominence walk, SCOPED to latest run_id per symbol (latest_run CTE). Identical output for the current snapshot; no longer scans all history. τ_accel via get_parameter_num.';

-- =====================================================================
-- VERIFY (run after applying):
--   \timing on
--   SELECT symbol, ts, pin_lower, pin_upper, n_strikes FROM v_gex_strike_pin_zone;
--   SELECT symbol, ts, accel_lower, accel_upper, n_strikes FROM v_gex_strike_accel_zone;
-- Both should return in <100ms and show TODAY's ts, matching the values the
-- old (slow) view produced for the same snapshot.
-- =====================================================================
