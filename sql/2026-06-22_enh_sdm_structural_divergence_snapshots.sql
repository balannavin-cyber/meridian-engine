-- ============================================================================
-- ENH-SDM  P1 — structural_divergence_snapshots  (forward observability monitor)
-- ============================================================================
-- Session 58 (2026-06-22).
--
-- Authorized under ADR-018 D4. NOTE: ADR-018 D4's primitive list
-- (breadth / OI-displacement / straddle / settlement-VWAP) is being CORRECTED to
-- the gamma-centric set below, sourced to the validated CASE-2026-06-02 short-
-- covering trade. That correction (+ the observability-first reframe) batches with
-- the S58 doc tail. The breadth/OI/VWAP ideas are deferred as candidate secondary
-- primitives, not core.
--
-- POSTURE: this is an OBSERVABILITY monitor, display-not-gate (S37). It computes
-- and surfaces the four gamma-state primitives every cycle. It does NOT fire or
-- gate a trade. The single +71% case (2026-06-02) justifies MEASURING these
-- conditions; it does NOT justify acting on them. A signal/modes build is gated on
-- a real cohort (P0a verdict S58: only ~8 expiry days have all 4 primitives
-- co-present; backward study blocked behind a Greeks backfill — see TD-S58-NEW-1).
-- The monitor accrues a clean forward cohort while that question stays open.
--
-- PRIMITIVES (all read from gamma_metrics + spot; no new capture):
--   1. pin-risk rate            — Δ pin_risk_score / time   (rehedge cascade)
--   2. straddle-collapse vel.   — % decline of straddle_atm (vol crush → covering)
--   3. gamma concentration      — gamma_concentration + Δ   (supply localization)
--   4. net_gex / regime-flip    — net_gex sign + regime transition (covering done)
--   trigger: three-red-wick spot reversal (microstructure)
--
-- Conventions match gamma_metrics / market_state_snapshots: uuid id,
-- timestamptz true-UTC ts, UNIQUE(symbol, ts), raw jsonb, _replay mirror (ADR-008).
-- Idempotent (IF NOT EXISTS) — safe to re-run.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.structural_divergence_snapshots (
    id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ts                          timestamptz NOT NULL,        -- cycle ts, true-UTC (mirrors gamma_metrics.ts)
    symbol                      text        NOT NULL,
    run_id                      uuid,
    created_at                  timestamptz NOT NULL DEFAULT now(),

    expiry_date                 date,
    dte                         integer,
    spot                        numeric,

    -- Primitive 1 — pin-risk rate (rehedge cascade; case: >10 pts / 30min)
    pin_risk_score              numeric,    -- source snapshot (gamma_metrics.pin_risk_score)
    pin_risk_rate               numeric,    -- Δ pin_risk_score per hour over the cycle

    -- Primitive 2 — straddle-collapse velocity (case: >30% by 10:30 IST = acute)
    straddle_atm                numeric,    -- source snapshot (gamma_metrics.straddle_atm)
    straddle_collapse_pct       numeric,    -- % decline vs session / T-1 reference

    -- Primitive 3 — gamma concentration (case: >0.5 = localized supply)
    gamma_concentration         numeric,    -- source snapshot
    gamma_concentration_delta   numeric,    -- Δ over the cycle

    -- Primitive 4 — net_gex / regime flip (case: NO_FLIP -> LONG_GAMMA = covered)
    net_gex                     numeric,    -- source snapshot
    regime                      text,       -- source snapshot
    regime_flip                 text,       -- e.g. 'NO_FLIP->LONG_GAMMA'; NULL if none

    -- Microstructure trigger
    three_wick_reversal         boolean,    -- spot three-red-wick reversal detected

    -- Context classifiers — DISPLAY ONLY, NOT a gate (S37)
    phase                       text,       -- PRE_EXPIRY / EXPIRY_AM / COVERING_WINDOW / POST / NONE
    direction                   text,       -- divergence direction: UP / DOWN / NONE
    divergence_mode             text,       -- OFFENSIVE_CONTEXT / DEFENSIVE_CONTEXT / NONE (label, no action)
    sdm_score                   integer,    -- count of primitives in tail (0-4); context only, never a trigger

    -- Recency-floor observability (ADR-018 D2): flag if a stale source row was floored
    source_stale_floored        boolean DEFAULT false,

    raw                         jsonb,

    CONSTRAINT uq_sdm_symbol_ts UNIQUE (symbol, ts)
);

CREATE INDEX IF NOT EXISTS ix_sdm_symbol_ts
    ON public.structural_divergence_snapshots (symbol, ts DESC);

-- ADR-008 replay parity: mirror table, identical structure.
CREATE TABLE IF NOT EXISTS public.structural_divergence_snapshots_replay
    (LIKE public.structural_divergence_snapshots INCLUDING ALL);

-- ============================================================================
-- POST-DEPLOY VERIFY (run after applying):
--   select count(*) from structural_divergence_snapshots;          -- expect 0
--   select count(*) from structural_divergence_snapshots_replay;   -- expect 0
--   \d+ public.structural_divergence_snapshots                     -- confirm columns + uq + index
-- ============================================================================
