-- =====================================================================
-- ENH-133 — per-cycle layer-history table  (gex_cycle_history)
-- Authored Session 89, 2026-10-03.  Scope ruled 2026-10-03 (rulings_s89.md).
--
--   *** AUTHORED, NOT APPLIED. ***
--   This file has NOT been run against the database. It is committed as the
--   bound migration source so the DDL is reviewable before it exists.
--   Spec: docs/research/s89_rulings/ENH-133_schema_spec_S89.md
--
-- Every column below is bound to a column proven to exist by introspection on
-- 2026-10-03; the type follows the SOURCE type, not a convenience choice.
-- Per the S81 rule, COMMENT and GRANT ship here as LIVE statements, never as
-- commentary — a sql/ file that carries only the table body is not a rebuild
-- source, and a rebuild from it fails silently at the access boundary.
-- =====================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.gex_cycle_history (
    -- ---- identity / clock / gate  (the only NOT NULL columns) ----------
    symbol                  text          NOT NULL,
    expiry_date             date          NOT NULL,
    ts                      timestamptz   NOT NULL,   -- the gamma run ts
    run_id                  uuid          NOT NULL,   -- gamma_metrics.run_id
    is_trading_session      boolean       NOT NULL,   -- distinct_spot > 1 (see spec)

    -- ---- clock corroboration -------------------------------------------
    chain_ts                timestamptz,              -- option_chain_snapshots.ts for THIS run_id
    dte                     integer,                  -- gamma_metrics.dte — CALENDAR days (measured)
    spot                    numeric,                  -- gamma_metrics.spot
    atm_iv                  numeric,                  -- volatility_snapshots.atm_iv_avg

    -- ---- regime / flip  (L6, L3) ---------------------------------------
    net_gex                 numeric,                  -- gamma_metrics.net_gex
    gamma_regime            text,                     -- gamma_metrics.regime
    flip_level              numeric,                  -- gamma_metrics.flip_level
    repriced_flip_level     double precision,         -- v_gex_repriced_flip.flip
    repriced_flip_ts        timestamptz,              -- v_gex_repriced_flip.ts AS RETURNED
    repriced_flip_source    text,                     -- 'CLOCK_MATCHED' | 'UNMATCHED_NULL'

    -- ---- pin / concentration  (L1/L2/L12, E-D2) -------------------------
    pin_leader_strike       numeric,                  -- v_gex_strike_rank.strike @ strike_rank = 1
    gamma_at_pin            numeric,                  -- v_gex_strike_rank.gex_cr @ strike_rank = 1
    runnerup_share_ratio    numeric,                  -- share_of_abs(r2) / share_of_abs(r1)
    top5_share              numeric,                  -- cum_share_of_abs @ strike_rank = 5
    top5_share_n_ranks      smallint,                 -- ranks actually available (edge: < 5)
    conc_top1_share         numeric,                  -- v_gex_concentration.hhi_net — TOP-1 SHARE, NOT a Herfindahl
    conc_top1_share_call    double precision,         -- hhi_call  — semantics UNVERIFIED
    conc_top1_share_put     double precision,         -- hhi_put   — semantics UNVERIFIED
    conc_hhi                numeric,                  -- true Herfindahl Σ(share_of_abs)^2 over ALL ranked strikes — distinct from conc_top1_share (top-1 share)
    max_pain_strike         numeric,                  -- v_gex_max_pain.max_pain_strike (gamma clock, E-D2)
    pin_state               text,                     -- NO PIN | SHIFTING | STABLE | LOCKED
    pin_state_reason        text,                     -- why NULL, when it is (missing param key etc.)
    held_for_cycles         integer,                  -- consecutive same-leader cycles, session-gated
    conviction              numeric,                  -- (1 - runnerup_share_ratio) * boost(T)

    -- ---- walls  (L4/L5) -------------------------------------------------
    call_wall_strike        numeric,                  -- v_gex_strike_walls.call_wall
    put_wall_strike         numeric,                  -- v_gex_strike_walls.put_wall

    -- ---- freshness, persisted and never dropped -------------------------
    is_fresh                boolean,                  -- v_gex_pin_maxpain / v_gex_max_pain
    snapshot_age_min        numeric,                  -- idem

    -- ---- provenance ------------------------------------------------------
    writer                  text,
    writer_version          text,
    created_at              timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT gex_cycle_history_pk
        PRIMARY KEY (symbol, expiry_date, ts),
    CONSTRAINT gex_cycle_history_pin_state_ck
        CHECK (pin_state IS NULL OR pin_state IN ('NO PIN','SHIFTING','STABLE','LOCKED')),
    CONSTRAINT gex_cycle_history_repriced_src_ck
        CHECK (repriced_flip_source IS NULL
               OR repriced_flip_source IN ('CLOCK_MATCHED','UNMATCHED_NULL')),
    -- an UNMATCHED L3 read must not carry a level: that is the whole point of the field
    CONSTRAINT gex_cycle_history_repriced_null_ck
        CHECK (repriced_flip_source IS DISTINCT FROM 'UNMATCHED_NULL'
               OR repriced_flip_level IS NULL),
    CONSTRAINT gex_cycle_history_held_for_ck
        CHECK (held_for_cycles IS NULL OR held_for_cycles >= 1)
);

-- Default history read is session-gated; this index serves it directly.
CREATE INDEX IF NOT EXISTS ix_gex_cycle_history_sym_ts_session
    ON public.gex_cycle_history (symbol, ts DESC)
    WHERE is_trading_session;

CREATE INDEX IF NOT EXISTS ix_gex_cycle_history_run
    ON public.gex_cycle_history (run_id);

-- ---------------------------------------------------------------------
-- COMMENTS — live statements, not commentary (S81 rule)
-- ---------------------------------------------------------------------
COMMENT ON TABLE public.gex_cycle_history IS
'ENH-133 per-cycle layer history. One row per (symbol, expiry_date, ts) at the 5-minute gamma cadence, both expiry legs, written by the existing compute chain. Grain accommodates a future 1-minute pass (Candidate A) unchanged.
RETENTION: KEEP INDEFINITELY. This table is explicitly NOT a target of pg_cron jobid 19 (cleanup_gamma_engine_daily, currently active=false). Any future retention job must name this table explicitly to touch it; a blanket gamma-chain cleanup must not.
Rows are written even when is_trading_session = false; the DEFAULT history read filters is_trading_session = true. A frozen-market cycle (see TD-S89-NEW-1, 2026-10-02) is recorded and flagged, never silently dropped.
Scope ruled 2026-10-03 — docs/research/s89_rulings/rulings_s89.md; bound spec — docs/research/s89_rulings/ENH-133_schema_spec_S89.md. Complement to ENH-134 (as-of functions cover the already-stored window; this table accumulates forward).';

COMMENT ON COLUMN public.gex_cycle_history.dte IS
'gamma_metrics.dte, which is CALENDAR days to expiry — measured 2026-10-03 across 8 runs (dte == expiry_date - run_date on all; trading days ahead differed, e.g. 10-01 dte 5 = 2 trading days). boost(T) takes TRADING days, so the writer converts via trading_calendar; do NOT feed this column to boost() directly.';

COMMENT ON COLUMN public.gex_cycle_history.conc_top1_share IS
'v_gex_concentration.hhi_net, stored under an honest name: it is the TOP-1 STRIKE SHARE of total abs(gex_cr), NOT a Herfindahl. Measured 2026-10-03 on NIFTY 10-01: published value 0.09419433182919231685 is byte-identical to v_gex_strike_rank.share_of_abs at strike_rank 1 and to gamma_metrics.gamma_concentration, while the true Herfindahl (sum of squared shares) is 0.04635883019194746740 — a factor of ~2. Never name this column hhi_*.';

COMMENT ON COLUMN public.gex_cycle_history.conc_top1_share_call IS
'v_gex_concentration.hhi_call, carried verbatim. SEMANTICS UNVERIFIED: the net leg was proven to be a top-1 share rather than a Herfindahl, and the call/put legs have NOT been checked either way. Do not publish as a Herfindahl, and do not compare with conc_top1_share, until verified.';

COMMENT ON COLUMN public.gex_cycle_history.conc_top1_share_put IS
'v_gex_concentration.hhi_put, carried verbatim. SEMANTICS UNVERIFIED — see conc_top1_share_call.';

COMMENT ON COLUMN public.gex_cycle_history.conc_hhi IS
'True Herfindahl concentration = sum of squared per-strike shares (share_of_abs^2) over all ranked strikes for the run. Distinct from conc_top1_share, which is the single top strike''s share. Measured 2026-10-03 NIFTY 10-01: conc_hhi = 0.04635883019194746740 vs conc_top1_share 0.09419433182919231685 (factor ~2). This is the real HHI; conc_top1_share is dominance, not dispersion.';

COMMENT ON COLUMN public.gex_cycle_history.repriced_flip_level IS
'v_gex_repriced_flip.flip (L3), CLOCK-MATCHED to this row''s gamma run. That view carries NO run_id and NO dte, names its expiry front_expiry, and its latest row can sit on a different trading date than the gamma run (measured 2026-10-03: its latest was 2026-10-02 10:10:04+00 at the frozen spot 22421.95 while the gamma clock was 2026-10-01 09:50:07+00 — a ~1,460-minute gap on a frozen book). If the writer cannot match the clock it stores NULL here and UNMATCHED_NULL in repriced_flip_source. Kept SEPARATE from flip_level per ADR-025 B7: the two are different definitions and measured 22368.20 vs 22692.00 on those runs.';

COMMENT ON COLUMN public.gex_cycle_history.repriced_flip_ts IS
'The ts the L3 view actually RETURNED, stored so a reader can test the clock match rather than trust it. Compared by column name, never by position.';

COMMENT ON COLUMN public.gex_cycle_history.is_trading_session IS
'(count(distinct spot) in market_spot_snapshots for this symbol on this IST trading date up to ts) > 1. Row-count and distinct-ts checks CANNOT distinguish a traded day from a frozen one: 2026-10-02 had ~143k chain rows across 83 distinct ts and distinct_spot = 1 for both symbols (TD-S89-NEW-1). This column is the discriminator.';

COMMENT ON COLUMN public.gex_cycle_history.held_for_cycles IS
'Consecutive cycles for which pin_leader_strike has been unchanged, counting only is_trading_session = true rows, so a holiday or frozen gap does not increment it. Starts at 1 on a leader change.';

COMMENT ON COLUMN public.gex_cycle_history.pin_state IS
'NO PIN | SHIFTING | STABLE | LOCKED, derived from held_for_cycles, runnerup_share_ratio and conc_top1_share using thresholds read from merdian_parameters (ADR-016 dot-keys). Thresholds are PROVISIONAL and owe D-6 calibration. A missing parameter key leaves this NULL with the reason in pin_state_reason — absence is not a verdict (ADR-020) and the writer must never substitute a default.';

COMMENT ON COLUMN public.gex_cycle_history.conviction IS
'(1 - runnerup_share_ratio) * boost(T), boost(T) = 2.53 * T^(-0.5), T in TRADING days to expiry, cap 3.70, floor T = 0.47 (D-5b / D-5c). Stage 1 only; Stage 2 multiplies by the 30-session conc_top1_share percentile once this table has history. The runner-up margin exists in NO relation and is computed by the writer — see the spec.';

COMMENT ON COLUMN public.gex_cycle_history.is_fresh IS
'Persisted from v_gex_pin_maxpain / v_gex_max_pain, never dropped: without it a stale-book cycle is indistinguishable from a fresh one in history. Measured example 2026-10-03: is_fresh = f at snapshot_age_min = 2670.7 reading Saturday.';

-- ---------------------------------------------------------------------
-- GRANTS — live statements (S81 rule).
-- anon is deliberately NOT granted. Supabase DEFAULT PRIVILEGES have been
-- observed to hand ALL on newly created objects to anon (S39 -> S81,
-- CASE-2026-09-22-anon-privilege-exposure), so the REVOKE below is not
-- belt-and-braces: it is the statement that prevents the default. If a later
-- script fails on an empty service-role key, supply the key — never restore
-- the grant.
-- ---------------------------------------------------------------------
REVOKE ALL ON TABLE public.gex_cycle_history FROM anon;
GRANT SELECT ON TABLE public.gex_cycle_history TO merdian_ro;

COMMIT;

-- =====================================================================
-- NOT INCLUDED, DELIBERATELY
--   * No RLS enable. Enabling RLS with zero policies makes the table
--     unreadable by every non-bypass role (TD-S81-NEW-16 family); if RLS is
--     wanted, the policy ships in the same statement as the enable.
--   * No backfill. The window before the first write is unrecoverable except
--     through ENH-134; this table accumulates forward only.
--   * No writer. The writer is a separate deliverable; its logic is specified
--     in ENH-133_schema_spec_S89.md and is not implied by this DDL.
-- =====================================================================
