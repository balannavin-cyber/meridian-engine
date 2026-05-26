-- ============================================================================
-- ENH-80 / ADR-014 — per-strike GEX schema
-- File: sql/2026-05-25_enh80_gex_strike_snapshots.sql
-- Session: 37
-- Date: 2026-05-25
-- Operator: Navin
-- Apply via: Supabase SQL editor or psql against the production DB
-- ============================================================================
--
-- This file is idempotent. Re-running on an already-applied DB will be a no-op
-- on the table and indexes (IF NOT EXISTS guards). The UNIQUE constraint is
-- added inside the CREATE TABLE so a re-run does not attempt to add it twice.
--
-- Sign convention (codified in ADR-014 §2.3 and Assumption Register §D.18.5):
--   gex_cr > 0  →  dampening (dealer long gamma at this strike)
--   gex_cr < 0  →  amplifying (dealer short gamma at this strike)
--
-- Falsification rule (ADR-014 §2.5):
--   SUM(gex_cr) over all rows for a given run_id must equal
--   gamma_metrics.net_gex for the same run_id within ±0.01 Cr.
--
-- Schema cross-reference:
--   - run_id joins to public.gamma_metrics.run_id (uuid)
--   - (symbol, ts) join shape matches gamma_metrics (symbol, ts) for ad-hoc
--     temporal joins where run_id is not in hand.
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.gex_strike_snapshots (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                   uuid        NOT NULL,
    symbol                   text        NOT NULL,
    ts                       timestamptz NOT NULL,
    expiry_date              date        NOT NULL,
    dte                      integer     NOT NULL,
    strike                   numeric     NOT NULL,
    spot                     numeric     NOT NULL,
    gamma                    numeric,
    oi_call                  bigint,
    oi_put                   bigint,
    gex_cr                   numeric     NOT NULL,
    is_local_max             boolean     NOT NULL DEFAULT false,
    is_flip_zone             boolean     NOT NULL DEFAULT false,
    is_pin_candidate_bool    boolean,
    created_at               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_gss_run_strike_expiry UNIQUE (run_id, strike, expiry_date)
);

-- Primary access pattern: latest snapshot per symbol, descending ts.
CREATE INDEX IF NOT EXISTS idx_gss_symbol_ts
    ON public.gex_strike_snapshots (symbol, ts DESC);

-- Expiry-pinned queries: e.g. "current-week NIFTY GEX strip from 09:15 to 15:30".
CREATE INDEX IF NOT EXISTS idx_gss_symbol_exp_ts
    ON public.gex_strike_snapshots (symbol, expiry_date, ts DESC);

-- Falsification join: SUM(gex_cr) GROUP BY run_id vs gamma_metrics.net_gex.
CREATE INDEX IF NOT EXISTS idx_gss_run_id
    ON public.gex_strike_snapshots (run_id);

-- Strike-range queries within a fixed (symbol, ts): Positioning Landscape
-- window aggregation (e.g. ±100Δ from spot for NET Γ IN WINDOW scalar).
CREATE INDEX IF NOT EXISTS idx_gss_symbol_ts_strike
    ON public.gex_strike_snapshots (symbol, ts DESC, strike);

-- Convenience COMMENT block so DB introspection surfaces the convention.
COMMENT ON TABLE  public.gex_strike_snapshots                       IS 'Per-strike GEX time-series. ENH-80 / ADR-014. See ADR for sign convention and falsification rule.';
COMMENT ON COLUMN public.gex_strike_snapshots.run_id                IS 'Joins to gamma_metrics.run_id. SUM(gex_cr) per run_id == gamma_metrics.net_gex ±0.01 Cr.';
COMMENT ON COLUMN public.gex_strike_snapshots.gex_cr                IS 'Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).';
COMMENT ON COLUMN public.gex_strike_snapshots.oi_call               IS 'Call OI at this strike at snapshot time. Source: chain cache.';
COMMENT ON COLUMN public.gex_strike_snapshots.oi_put                IS 'Put OI at this strike at snapshot time. Source: chain cache.';
COMMENT ON COLUMN public.gex_strike_snapshots.is_local_max          IS 'True iff |gex_cr[i]| > |gex_cr[i-1]| AND |gex_cr[i]| > |gex_cr[i+1]| within the (run_id, expiry_date) row group. Endpoints always false.';
COMMENT ON COLUMN public.gex_strike_snapshots.is_flip_zone          IS 'True iff sign(gex_cr[i]) != sign(gex_cr[i-1]) within the (run_id, expiry_date) row group, sorted by strike ascending.';
COMMENT ON COLUMN public.gex_strike_snapshots.is_pin_candidate_bool IS 'NULL until ENH-82 calibrates threshold tau. ENH-82 populates as: is_local_max AND |gex_cr| > tau.';

COMMIT;

-- ============================================================================
-- Post-apply verification (run as a separate transaction).
-- Expected output:
--   - relname = 'gex_strike_snapshots' with reltuples = 0 immediately after DDL
--   - 4 indexes present
--   - 1 unique constraint present
-- ============================================================================

-- 1. Table exists, row count zero.
SELECT relname, reltuples::bigint AS approx_rows
FROM   pg_class
WHERE  relname = 'gex_strike_snapshots';

-- 2. Indexes present.
SELECT indexname
FROM   pg_indexes
WHERE  schemaname = 'public'
  AND  tablename  = 'gex_strike_snapshots'
ORDER  BY indexname;

-- 3. Unique constraint present.
SELECT conname, pg_get_constraintdef(oid) AS definition
FROM   pg_constraint
WHERE  conrelid = 'public.gex_strike_snapshots'::regclass
  AND  contype  = 'u';

-- 4. Column comments present.
SELECT a.attname, pg_catalog.col_description(a.attrelid, a.attnum) AS comment
FROM   pg_attribute a
WHERE  a.attrelid = 'public.gex_strike_snapshots'::regclass
  AND  a.attnum > 0
  AND  NOT a.attisdropped
ORDER  BY a.attnum;
