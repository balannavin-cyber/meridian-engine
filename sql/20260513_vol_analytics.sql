-- ============================================================================
-- MERDIAN Session 29 — vol_analytics + vol_analytics_shadow
-- Created: 2026-05-13
-- Purpose: Per-cycle realized vs implied vol pricing layer (RR ratio).
--          A buyer entering at zone touch is unconditionally betting on
--          realized > implied vol for the holding period. RR (realized/implied)
--          classifies each cycle into a regime gating whether option-buying
--          is structurally cheap (HIGH), fair (FAIR), structurally adverse
--          (LOW), or compression-locked (COMPRESSED). Without this layer
--          the pipeline has no vol-pricing filter; structural edge (zones,
--          force) carries the trade alone even when premium is mispriced.
-- Refs:    ENH-97 (vol_analytics + RR ratio writer, S28 P2 PROPOSED filing).
--          ADR-002 v2 §P7 (vol-pricing principle) + §Schema (this DDL).
--          Assumption Register §D.10.1 (RR independent edge LIVE pending
--          Phase 0b validation = pending this build).
--          Assumption Register §D.11.1 (shadow architecture invariant —
--          physical separation via target-table routing, NOT host column;
--          codified post-TD-NEW-12 silent architecture violation).
-- ============================================================================

-- Canonical table — Local writes target.
CREATE TABLE IF NOT EXISTS public.vol_analytics (
    id                uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at        timestamptz  NOT NULL DEFAULT now(),

    -- Identity
    ts                timestamptz  NOT NULL,                                -- cycle timestamp (matches gamma_metrics.ts)
    symbol            text         NOT NULL,                                -- 'NIFTY' | 'SENSEX'

    -- Realized vol — annualised; computed from 5-min spot bars
    --   realized_vol_10 = 10-bar window (50 min)  — fast diagnostic horizon
    --   realized_vol_30 = 30-bar window (150 min) — regime-stable RR numerator
    realized_vol_10   numeric,
    realized_vol_30   numeric,

    -- Implied vol — annualised; sourced from volatility_snapshots.atm_iv_avg
    -- for the matching (symbol, ts) cycle. Falls back to direct compute from
    -- option_chain_snapshots ATM rows when upstream value is NULL.
    implied_vol_atm   numeric,

    -- RR pricing — rr_ratio = realized_vol_30 / implied_vol_atm
    rr_ratio          numeric,
    rr_regime         text         CHECK (rr_regime IN ('HIGH','FAIR','LOW','COMPRESSED')),

    -- Diagnostic reproducibility — should at minimum capture:
    --   {"realized_source":"hist_spot_bars_5m", "iv_source":"volatility_snapshots.atm_iv_avg",
    --    "iv_fallback_used": bool, "bars_used_10": int, "bars_used_30": int,
    --    "regime_thresholds": {"HIGH":1.2,"FAIR_LOW":0.85,"COMPRESSED":0.4}}
    raw               jsonb        NOT NULL DEFAULT '{}'::jsonb,

    -- Idempotency — one row per (symbol, ts); UPSERT on conflict
    CONSTRAINT vol_analytics_symbol_ts_key UNIQUE (symbol, ts)
);

CREATE INDEX IF NOT EXISTS ix_vol_analytics_symbol_ts_desc
    ON public.vol_analytics (symbol, ts DESC);

-- Shadow companion — AWS writes target when invoked with --shadow flag.
-- Per Assumption Register §D.11.1, physical-separation routing replaces
-- narrative-only host-column enforcement. Applied at table birth here vs.
-- retrofitted post-violation as in S28 gamma_metrics_shadow remediation.
CREATE TABLE IF NOT EXISTS public.vol_analytics_shadow
    (LIKE public.vol_analytics INCLUDING ALL);

-- Schema cache reload — per S28 TD-NEW-12 lesson (PGRST204 cache rejection
-- without explicit reload after DDL); codified as CLAUDE.md B22 / D.11.1.
NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- Regime classification (writer-side logic — documented here for review;
-- enforced in compute_vol_analytics_local.py, NOT in this DDL):
--
--   rr_ratio > 1.2          → 'HIGH'        (realized exceeds implied; buyer favorable)
--   0.85 ≤ rr_ratio ≤ 1.2   → 'FAIR'        (balanced; structural edge carries alone)
--   0.4 ≤ rr_ratio < 0.85   → 'LOW'         (implied prices vol that isn't materializing)
--   rr_ratio < 0.4          → 'COMPRESSED'  (mean-reversion regime; buyer mostly stands aside)
--   rr_ratio IS NULL        → NULL          (insufficient bar history; <30 bars on 5m)
--
-- Boundary inclusivity per ADR-002 v2 §P7: HIGH strict >, COMPRESSED strict <;
-- 0.85 endpoint belongs to FAIR, 0.4 endpoint belongs to LOW.
-- ============================================================================
