-- ============================================================================
-- ENH-116 — Ambient Environment Intelligence  ·  Phase 1 (Measure) schemas
-- ----------------------------------------------------------------------------
-- Session   : S64 (2026-07-02)
-- Spec       : docs/decisions/ENH-116-ambient-environment-intelligence.md (build seq step 1)
-- Governance : display-not-gate (ADR-002 v2 §D.19.3); M→V→S→P; ADR-018 supervision.
-- Idempotent : CREATE ... IF NOT EXISTS — safe to re-run in the Supabase SQL editor.
--
-- Resolved design calls (S64):
--   * Expiry pooling  : pooled, expiry_type carried as a feature (no separate table).
--   * 5th lens         : NOT reserved — later ALTER if/when rates/global lens is built.
--   * Lens 3 (particip): columns populatable NOW (ENH-115 P1 source live S63), not NULL.
--   * Lens 4 (macro)   : columns present, written NULL until a feed is chosen.
--   * source tags      : '*_s62' retained verbatim from the spec constants; bump to
--                        '*_s64' only if you want provenance to track the build session.
-- ============================================================================


-- ── market_environment_snapshots ──────────────────────────────────────────
-- Post-market compiler output; one row per symbol per (next) session date.
CREATE TABLE IF NOT EXISTS public.market_environment_snapshots (
    id                         bigserial PRIMARY KEY,
    symbol                     text NOT NULL,
    as_of_date                 date NOT NULL,        -- the settled session this summarizes
    for_session_date           date NOT NULL,        -- the NEXT session this contexts

    -- Lens 1: gamma-positioning
    gex_regime_persistence_20d numeric,              -- frac of last 20 sessions net-long-gamma [0..1]
    max_gamma_strike_drift_5d  numeric,              -- signed pts/session drift of max-γ strike
    concentration_trend_5d     numeric,              -- signed slope of daily gamma_concentration
    net_gex_regime             text,                 -- POSITIVE_γ | NEGATIVE_γ | MIXED

    -- Lens 2: breadth trajectory
    wcb_slope_5d               numeric,
    pct_above_20dma_slope_5d   numeric,
    price_vs_breadth_div       text,                 -- CONFIRM | BEARISH_DIV | BULLISH_DIV | NEUTRAL

    -- Lens 3: cycle-OI / participant (ENH-115 inputs; live S63)
    cycle_oi_call_put_asym     numeric,              -- +ve = call-side (ceiling) building
    fii_index_fut_ls_delta_5d  numeric,
    pro_options_imbalance      numeric,

    -- Lens 4: macro context (extensible; NULL until sources wired)
    usdinr_trend_5d            numeric,
    crude_trend_5d             numeric,
    gold_trend_5d              numeric,
    macro_tilt                 text,                 -- RISK_ON | RISK_OFF | NEUTRAL

    -- Reconciliation
    ambient_regime             text,                 -- TREND_UP|TREND_DOWN|RANGE|DISTRIBUTION|ACCUMULATION|UNSTABLE
    lens_alignment             text,                 -- ALIGNED | DIVERGENT
    session_prior              text,                 -- structured prose (pre-market reconciler fills relate-part)
    regime_conditional_note    text,                 -- Phase-B base-rate string when available

    source                     text NOT NULL DEFAULT 'ambient_compiler_s62',
    created_at                 timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uniq_env_row UNIQUE (symbol, for_session_date, source)
);
CREATE INDEX IF NOT EXISTS idx_env_for_session
    ON public.market_environment_snapshots (for_session_date);


-- ── expiry_outcomes ───────────────────────────────────────────────────────
-- Phase-A labeled event-store; one row per expiry. Stores, does not predict.
CREATE TABLE IF NOT EXISTS public.expiry_outcomes (
    id                       bigserial PRIMARY KEY,
    symbol                   text NOT NULL,
    expiry_date              date NOT NULL,
    expiry_type              text NOT NULL,          -- WEEKLY | MONTHLY

    -- ambient state going IN (snapshot of the four lenses as of expiry morning)
    ambient_regime           text,
    lens_alignment           text,
    gex_regime_persistence   numeric,
    concentration_at_open    numeric,
    breadth_div_at_open      text,
    participant_tilt         text,
    macro_tilt               text,
    open_pin_strike          numeric,
    open_flip_level          numeric,
    open_pin_risk_score      numeric,

    -- OUTCOME (labeled at settlement)
    resolved                 text,                   -- PINNED | BROKE_UP | BROKE_DOWN
    settlement_vs_open_pin_pct numeric,
    intraday_range_pct       numeric,
    accel_zone_triggered     boolean,

    source                   text NOT NULL DEFAULT 'expiry_memory_s62',
    created_at               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_expiry_type CHECK (expiry_type IN ('WEEKLY','MONTHLY')),
    CONSTRAINT chk_resolved    CHECK (resolved IN ('PINNED','BROKE_UP','BROKE_DOWN')),
    CONSTRAINT uniq_expiry_event UNIQUE (symbol, expiry_date, source)
);
CREATE INDEX IF NOT EXISTS idx_expiry_regime
    ON public.expiry_outcomes (symbol, ambient_regime, resolved);
