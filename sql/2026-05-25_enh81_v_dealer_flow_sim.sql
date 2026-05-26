-- =====================================================================
-- 2026-05-25_enh81_v_dealer_flow_sim.sql
-- ENH-81 — Positioning Landscape: dealer flow simulator
-- =====================================================================
--
-- Projects dealer hedging flow at six fixed perturbation scenarios for
-- the LATEST run_id per symbol. Used by the dashboard "DEALER FLOW
-- SIMULATOR — what if spot moves..." panel.
--
-- Math (per ADR-014 §2.3 sign convention):
--   flow_cr ≈ net_gex × Δspot_pct
--
-- Where:
--   * net_gex (Cr) = ∑ strikes (signed_gamma_exposure × spot² / 1e7)
--   * Δspot_pct ∈ {-2%, -1%, -0.5%, +0.5%, +1%, +2%}
--
-- Direction:
--   flow_cr < 0  →  SELL  (dealers must SELL futures to maintain hedge)
--   flow_cr > 0  →  BUY
--
-- Regime change:
--   true iff the perturbed spot crosses the flip_level (sign of net_gex
--   would flip at the new spot).
--
-- This is a first-order approximation. Higher-order (Δspot² term from
-- changing gamma values themselves) is small for ≤2% perturbations and
-- deferred to ADR-002 v2 P8 second-order Greeks.
-- =====================================================================

CREATE OR REPLACE VIEW v_dealer_flow_sim AS
WITH scenarios AS (
  SELECT * FROM (VALUES
    (-0.02::numeric,  '-2.0%'::text),
    (-0.01,           '-1.0%'),
    (-0.005,          '-0.5%'),
    ( 0.005,          '+0.5%'),
    ( 0.01,           '+1.0%'),
    ( 0.02,           '+2.0%')
  ) AS s(pct, label)
),
latest_per_symbol AS (
  SELECT DISTINCT ON (symbol)
    run_id, symbol, expiry_date, ts, spot
  FROM gex_strike_snapshots
  ORDER BY symbol, ts DESC
),
ctx AS (
  SELECT
    l.symbol, l.run_id, l.expiry_date, l.ts, l.spot,
    gm.net_gex, gm.flip_level
  FROM latest_per_symbol l
  JOIN gamma_metrics gm
    ON gm.run_id = l.run_id AND gm.symbol = l.symbol
)
SELECT
  c.run_id, c.symbol, c.expiry_date, c.ts,
  s.label                                         AS scenario,
  s.pct                                           AS spot_pct,
  ROUND((c.spot * (1 + s.pct))::numeric, 2)       AS perturbed_spot,
  c.net_gex,
  ROUND((c.net_gex * s.pct)::numeric, 2)          AS flow_cr,
  CASE WHEN (c.net_gex * s.pct) < 0 THEN 'SELL' ELSE 'BUY' END AS direction,
  CASE
    WHEN c.flip_level IS NULL THEN false
    WHEN s.pct < 0 AND c.spot > c.flip_level
         AND c.spot * (1 + s.pct) <= c.flip_level THEN true
    WHEN s.pct > 0 AND c.spot < c.flip_level
         AND c.spot * (1 + s.pct) >= c.flip_level THEN true
    ELSE false
  END                                             AS crosses_flip
FROM ctx c
CROSS JOIN scenarios s
ORDER BY c.symbol, s.pct;

COMMENT ON VIEW v_dealer_flow_sim IS
  'ENH-81 v0 — dealer flow projection at ±0.5%, ±1%, ±2% scenarios for latest run_id per symbol. First-order approximation per ADR-014 §2.3 sign convention.';
