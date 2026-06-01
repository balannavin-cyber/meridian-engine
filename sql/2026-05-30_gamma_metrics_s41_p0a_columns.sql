-- =====================================================================
-- MERDIAN S41 P0.a — gamma_metrics column adds for VIX + Pin Risk Score
-- =====================================================================
-- Date            : 2026-05-30
-- Session         : S41
-- Mandate         : P0.a Marketview writer-side gap closure (India VIX +
--                   Pin Risk Score + Pin Risk Timeline cards)
-- Architecture    : B — extend gamma_metrics (vs separate india_vix_snapshots
--                   table) — chosen because Marketview is already wired to
--                   gamma_metrics.vix per Lovable S40 schema-correction prompt.
--                   Redundancy of writing VIX to both (NIFTY, ts) and
--                   (SENSEX, ts) rows per cycle is ~16 bytes/cycle —
--                   architecturally negligible vs the cost of either
--                   re-wiring Marketview or maintaining a JOIN view.
--
-- Operator-confirmed S41:
--   1. Pin Risk Score formula: additive-weighted (NOT multiplicative)
--   2. max_gamma_strike: materialize to gamma_metrics (was previously
--      derived client-side via gex_strike_snapshots aggregation per S40
--      correction prompt — moving to per-cycle pre-computed column is
--      cleaner and eliminates one Marketview-side aggregation)
--
-- Rollback        : Each ADD COLUMN is reversible via DROP COLUMN. Safe
--                   to apply in production — backwards-compatible.
-- Writer-side     : compute_gamma_metrics_local.py extended in same
--                   session via patch_s41_p0a_india_vix_pin_risk.py.
--                   Apply this DDL BEFORE running the patched writer.
-- =====================================================================

BEGIN;

-- 1. India VIX (live value from Dhan marketfeed/ltp security_id=21 IDX_I).
--    NUMERIC unbounded — VIX typically 10-30, historical range 2-90.
--    NULL when Dhan VIX fetch fails (token expired, 429, network).
--    VIX is index-wide (same value for NIFTY and SENSEX rows in same cycle)
--    — D.22.1-class redundancy, accepted per Architecture B decision.
ALTER TABLE public.gamma_metrics
    ADD COLUMN IF NOT EXISTS vix NUMERIC;

COMMENT ON COLUMN public.gamma_metrics.vix IS
    'S41 P0.a — India VIX live (Dhan marketfeed/ltp IDX_I/21). '
    'NULL on Dhan fetch failure (token/429/network). '
    'Index-wide value, replicated across NIFTY+SENSEX rows per cycle.';


-- 2. max_gamma_strike (argmax(|gex_cr|) over the strike map for the cycle).
--    NUMERIC for cross-symbol compatibility (NIFTY 50-pt steps, SENSEX 100-pt).
--    NULL on degenerate cycles (empty strike map).
ALTER TABLE public.gamma_metrics
    ADD COLUMN IF NOT EXISTS max_gamma_strike NUMERIC;

COMMENT ON COLUMN public.gamma_metrics.max_gamma_strike IS
    'S41 P0.a — strike with max |gex_cr| in this cycle. '
    'Replaces client-side aggregation against gex_strike_snapshots '
    '(Marketview S40 correction prompt mapping). '
    'NULL on degenerate strike map.';


-- 3. pin_risk_score (additive-weighted 0-100 per S41 operator-confirmed formula).
--    Formula:
--      0.30 * gamma_concentration              (0-1)
--    + 0.30 * spot_proximity_factor            (0-1)
--    + 0.20 * sustained_time_factor            (0-1; dropped + renorm if N<3)
--    + 0.20 * (1 - expansion_probability/100)  (0-1)
--    Clamped to [0, 100]. NULL if gamma_concentration or expansion_probability
--    is None. Renormalized when sustained_time_factor or spot_proximity_factor
--    is unavailable. See compute_pin_risk_score() in
--    compute_gamma_metrics_local.py for implementation details.
ALTER TABLE public.gamma_metrics
    ADD COLUMN IF NOT EXISTS pin_risk_score NUMERIC;

COMMENT ON COLUMN public.gamma_metrics.pin_risk_score IS
    'S41 P0.a — additive-weighted pin risk score 0-100. '
    'Components: gamma_concentration*0.30 + spot_proximity*0.30 + '
    'sustained_time*0.20 + (1-expansion_prob)*0.20. '
    'Renormalized when factors unavailable. See ADR-002 v2 PINNED state '
    'and compute_pin_risk_score() docstring.';


COMMIT;


-- =====================================================================
-- Verification queries (run after COMMIT — expect schema-add success)
-- =====================================================================

-- 1. Columns exist with correct type:
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema='public' AND table_name='gamma_metrics'
--   AND column_name IN ('vix','max_gamma_strike','pin_risk_score')
-- ORDER BY column_name;
-- Expected: 3 rows, data_type='numeric', is_nullable='YES' for all three.

-- 2. Comments registered:
-- SELECT col.column_name, pd.description
-- FROM pg_catalog.pg_statio_all_tables AS st
-- JOIN information_schema.columns AS col
--   ON col.table_schema=st.schemaname AND col.table_name=st.relname
-- JOIN pg_catalog.pg_description AS pd
--   ON pd.objoid=st.relid AND pd.objsubid=col.ordinal_position
-- WHERE st.schemaname='public' AND st.relname='gamma_metrics'
--   AND col.column_name IN ('vix','max_gamma_strike','pin_risk_score')
-- ORDER BY col.column_name;
-- Expected: 3 rows, descriptions matching COMMENT ON statements above.

-- 3. Existing rows have NULLs in new columns (no DEFAULT, ADD COLUMN
--    is zero-downtime; backfill is writer-side, not schema-side):
-- SELECT COUNT(*) AS total_rows,
--        COUNT(vix) AS vix_filled,
--        COUNT(max_gamma_strike) AS mgs_filled,
--        COUNT(pin_risk_score) AS prs_filled
-- FROM public.gamma_metrics;
-- Expected pre-writer-deploy: vix_filled=0, mgs_filled=0, prs_filled=0.

-- =====================================================================
-- Rollback (if needed BEFORE writer deploy — after deploy, must coordinate
-- with patch_s41_p0a_india_vix_pin_risk.py revert):
-- =====================================================================
-- BEGIN;
-- ALTER TABLE public.gamma_metrics DROP COLUMN IF EXISTS pin_risk_score;
-- ALTER TABLE public.gamma_metrics DROP COLUMN IF EXISTS max_gamma_strike;
-- ALTER TABLE public.gamma_metrics DROP COLUMN IF EXISTS vix;
-- COMMIT;
