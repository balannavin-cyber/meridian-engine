-- ============================================================================
-- gex_pin_maxpain_history  --  derived pin/max-pain history, one row per run
-- Session 80 (2026-09-22) · ADR-025
-- ============================================================================
--
-- WHAT
--   One row per (symbol, run_id, expiry_date) carrying the pin band, the peak
--   pin strike and the max-pain strike, reproduced from gex_strike_snapshots.
--   Populated by backfill_pin_maxpain_runs() -- see
--   sql/2026-09-22_s80_backfill_pin_maxpain_runs.sql.
--
-- WHY IT EXISTS
--   v_gex_strike_pin_zone is latest-run scoped by ADR-021 (its recursive tau
--   walk crossed the PostgREST 8 s ceiling at 1.06M rows). The pin band and
--   peak_pin_strike therefore cannot be read historically from the view at all.
--   This table materialises the same computation per run so the pin/max-pain
--   relationship can be measured across history without re-running the walk.
--
--   S80 populated it for all 11,795 runs (2026-05-25 -> 2026-09-18) and
--   measured the gap at a stable -0.4 sigma across both symbols, every DTE and
--   every session hour.
--
-- PARITY STATUS
--   NOT a parity layer. ADR-025 D5 files this and its consumers as L19, an
--   extension under Hedgewall_Parity_Spec section 2.5. Parked: applied,
--   unrendered, not counted toward parity.
--
-- RULE 10
--   Schema-affecting. A dedicated ADR for the table itself is OWED -- ADR-025
--   rules on the parity programme, not on this table's design.
--
-- IDEMPOTENT: CREATE TABLE IF NOT EXISTS. Safe to re-run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.gex_pin_maxpain_history (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol          text NOT NULL,
  run_id          uuid NOT NULL,
  ts              timestamptz NOT NULL,
  expiry_date     date NOT NULL,
  dte             integer,
  spot            numeric,
  peak_pin_strike numeric,
  pin_lower       numeric,
  pin_upper       numeric,
  pin_n_strikes   integer,
  peak_pin_gex_cr numeric,
  tau_used        numeric,
  max_pain_strike numeric,
  chain_n_strikes integer,
  computed_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (symbol, run_id, expiry_date)
);

-- The UNIQUE constraint is load-bearing, not hygiene: backfill_pin_maxpain_runs
-- relies on ON CONFLICT DO NOTHING for resumability. Verified S80 -- a re-run
-- over a completed day returns 0 and inserts nothing.

COMMENT ON TABLE public.gex_pin_maxpain_history IS
  'S80/ADR-025 L19. Per-run pin band + max-pain strike reproduced from '
  'gex_strike_snapshots, because v_gex_strike_pin_zone is latest-run scoped '
  '(ADR-021) and cannot be read historically. Populated by '
  'backfill_pin_maxpain_runs(). Extension, not a parity layer.';
