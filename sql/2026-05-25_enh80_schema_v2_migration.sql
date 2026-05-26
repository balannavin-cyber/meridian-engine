-- =====================================================================
-- 2026-05-25_enh80_schema_v2_migration.sql
-- ADR-015 — Per-Strike GEX Schema v2 migration
-- =====================================================================
--
-- Drops derived booleans (is_local_max, is_flip_zone, is_pin_candidate_bool)
-- and the single gamma column. Adds gamma_call + gamma_put split to preserve
-- IV skew at strike resolution.
--
-- Migration is destructive (TRUNCATE) but safe — no downstream code reads
-- gex_strike_snapshots yet. The 405 rows from S37 first-fire are throwaway.
--
-- Sequencing (operator):
--   1. Disable any scheduler task that calls compute_gamma_metrics_local.py
--      (or time deploy to land before next 5-min tick)
--   2. Run this SQL
--   3. Restore writer backup, apply patch v2:
--        copy compute_gamma_metrics_local_PRE_S37.py compute_gamma_metrics_local.py
--        python patch_s37_enh80_writer_v2.py --dry-run
--        python patch_s37_enh80_writer_v2.py --apply
--   4. Smoke-fire NIFTY + SENSEX, run §2.5 falsification.
-- =====================================================================

BEGIN;

-- Step 1: TRUNCATE — drop the 405 throwaway rows from S37 first-fire.
TRUNCATE TABLE gex_strike_snapshots;

-- Step 2: Drop derived/folded columns.
ALTER TABLE gex_strike_snapshots
  DROP COLUMN gamma,
  DROP COLUMN is_local_max,
  DROP COLUMN is_flip_zone,
  DROP COLUMN is_pin_candidate_bool;

-- Step 3: Add IV-skew-preserving gamma split.
ALTER TABLE gex_strike_snapshots
  ADD COLUMN gamma_call double precision,
  ADD COLUMN gamma_put  double precision;

-- Step 4: Column comments.
COMMENT ON COLUMN gex_strike_snapshots.gamma_call IS
  'Black-Scholes gamma of the CE leg at this strike. NULL if no CE row present in chain. Source: option_chain_snapshots via chain cache.';

COMMENT ON COLUMN gex_strike_snapshots.gamma_put IS
  'Black-Scholes gamma of the PE leg at this strike. NULL if no PE row present in chain. Source: option_chain_snapshots via chain cache.';

-- Step 5: Verify post-migration shape.
-- Expected columns: id, run_id, symbol, ts, expiry_date, dte, strike, spot,
--                   gamma_call, gamma_put, oi_call, oi_put, gex_cr, created_at
-- (14 columns; was 16; net -4 + 2 = -2)

COMMIT;

-- Post-commit verification queries (run separately, not inside the transaction):
--
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'gex_strike_snapshots'
-- ORDER BY ordinal_position;
--
-- SELECT count(*) FROM gex_strike_snapshots;  -- expect 0
