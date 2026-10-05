-- =====================================================================
-- ENH-133 — provisional pin_state thresholds into merdian_parameters (ADR-016)
-- Authored Session 89, 2026-10-03.
--
--   *** AUTHORED, NOT APPLIED. ***
--   This file has NOT been run against the database.
--
-- WHY A SEED MIGRATION AND NOT THE CLI: ADR-016 §"Write API — CLI only in v0"
-- names `merdian_calibrate.py` (ENH-83) as the write path. That file is NOT in
-- the tree (repo-wide find, 2026-10-03), while the register reads ENH-83
-- SHIPPED (S39) and `merdian_parameters` measures 0 rows. Filed separately as a
-- tech-debt item; building the CLI is ENH-83 scope, not ENH-133's. This seed is
-- the minimum that unblocks ENH-133 without taking that scope.
--
-- ALL EIGHT VALUES ARE PROVISIONAL AND OWE D-6 CALIBRATION. They are a starting
-- point chosen so the state machine runs, NOT a measured result. Nothing may
-- cite them as calibrated.
-- =====================================================================

BEGIN;

INSERT INTO public.merdian_parameters
    (key, value_num, value_type, category, description,
     min_value, max_value, valid_from, changed_by, change_reason)
VALUES
  ('pin_state.stable_held_for.NIFTY',   6,    'numeric', 'pin_state',
   'Consecutive same-leader cycles at or above which pin_state leaves SHIFTING.',
   1,   200,  now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.locked_held_for.NIFTY',   12,   'numeric', 'pin_state',
   'Consecutive same-leader cycles at or above which pin_state may reach LOCKED.',
   1,   400,  now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.locked_ratio_max.NIFTY',  0.50, 'numeric', 'pin_state',
   'Maximum runnerup_share_ratio (r2 share / r1 share) permitted for LOCKED. Near 1 = not locked.',
   0,   1,    now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.nopin_conc_floor.NIFTY',  0.04, 'numeric', 'pin_state',
   'conc_top1_share below this reads NO PIN. NOTE: this is a TOP-1 SHARE floor, not a Herfindahl.',
   0,   1,    now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.stable_held_for.SENSEX',  6,    'numeric', 'pin_state',
   'Consecutive same-leader cycles at or above which pin_state leaves SHIFTING.',
   1,   200,  now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.locked_held_for.SENSEX',  12,   'numeric', 'pin_state',
   'Consecutive same-leader cycles at or above which pin_state may reach LOCKED.',
   1,   400,  now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.locked_ratio_max.SENSEX', 0.50, 'numeric', 'pin_state',
   'Maximum runnerup_share_ratio (r2 share / r1 share) permitted for LOCKED. Near 1 = not locked.',
   0,   1,    now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration'),
  ('pin_state.nopin_conc_floor.SENSEX', 0.04, 'numeric', 'pin_state',
   'conc_top1_share below this reads NO PIN. NOTE: this is a TOP-1 SHARE floor, not a Herfindahl.',
   0,   1,    now(), 'ENH-133 seed (S89)', 'ENH-133 provisional, owes D-6 calibration')
ON CONFLICT DO NOTHING;

COMMIT;

-- ---------------------------------------------------------------------
-- VERIFY AFTER APPLY — run this, do not assume the insert landed.
-- Expect exactly 8 rows. ON CONFLICT DO NOTHING means a partial apply is
-- SILENT, so the count is the check, not the absence of an error.
-- ---------------------------------------------------------------------
-- SELECT count(*) AS seeded, count(*) FILTER (WHERE valid_to IS NULL) AS live
-- FROM public.merdian_parameters WHERE key LIKE 'pin_state.%';
--
-- And confirm the READ path resolves each one, which is what the writer does:
-- SELECT key, value_num, value_type FROM public.merdian_parameters
-- WHERE key LIKE 'pin_state.%' AND valid_to IS NULL ORDER BY key;

-- =====================================================================
-- NOT INCLUDED, DELIBERATELY
--   * No UPDATE / upsert. ON CONFLICT DO NOTHING means a re-run cannot
--     overwrite a calibrated value with a provisional one. Re-calibration
--     goes through the ADR-016 valid_from / valid_to lifecycle, not this file.
--   * No merdian_calibrate.py. ENH-83 scope.
--   * No defaults in code. The writer reads each key with
--     core.parameters.get_parameter_num(key) and NO fallback; a missing key
--     leaves pin_state NULL with the reason recorded (ADR-020 — absence is
--     not a verdict).
-- =====================================================================
