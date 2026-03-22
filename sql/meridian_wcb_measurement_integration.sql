/* ============================================================
MERDIAN
WCB Measurement Integration
Phase: Measure

Purpose
-------
Add storage fields so Weighted Constituent Breadth (WCB)
can be recorded in MERDIAN without changing signal logic.

This migration:
1. Adds wcb_features to market_state_snapshots
2. Adds observational WCB columns to signal_snapshots

This is measurement-only.
No signal rule changes are introduced here.
============================================================ */


/* ------------------------------------------------------------
1) market_state_snapshots
------------------------------------------------------------ */
ALTER TABLE market_state_snapshots
ADD COLUMN IF NOT EXISTS wcb_features JSONB;


/* ------------------------------------------------------------
2) signal_snapshots
------------------------------------------------------------ */
ALTER TABLE signal_snapshots
ADD COLUMN IF NOT EXISTS wcb_regime TEXT;

ALTER TABLE signal_snapshots
ADD COLUMN IF NOT EXISTS wcb_score NUMERIC;

ALTER TABLE signal_snapshots
ADD COLUMN IF NOT EXISTS wcb_alignment TEXT;

ALTER TABLE signal_snapshots
ADD COLUMN IF NOT EXISTS wcb_weight_coverage_pct NUMERIC;


/* ------------------------------------------------------------
3) helpful indexes
------------------------------------------------------------ */
CREATE INDEX IF NOT EXISTS idx_market_state_snapshots_wcb_features
ON market_state_snapshots
USING GIN (wcb_features);

CREATE INDEX IF NOT EXISTS idx_signal_snapshots_wcb_regime
ON signal_snapshots (wcb_regime);


/* ------------------------------------------------------------
4) column comments
------------------------------------------------------------ */
COMMENT ON COLUMN market_state_snapshots.wcb_features IS
'Measurement-only WCB feature block attached to market state during Phase 1 measurement expansion.';

COMMENT ON COLUMN signal_snapshots.wcb_regime IS
'Observed WCB regime at signal time. Measurement only.';

COMMENT ON COLUMN signal_snapshots.wcb_score IS
'Observed WCB score at signal time. Measurement only.';

COMMENT ON COLUMN signal_snapshots.wcb_alignment IS
'Observed relationship between signal direction and WCB regime. Measurement only.';

COMMENT ON COLUMN signal_snapshots.wcb_weight_coverage_pct IS
'Observed matched WCB weight coverage percentage at signal time.';