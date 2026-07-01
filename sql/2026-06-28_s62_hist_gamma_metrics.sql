-- 2026-06-28_s62_hist_gamma_metrics.sql
-- Aggregate historical gamma series derived from hist_option_greeks_1m (the sidecar).
-- Mirrors live gamma_metrics shape so ENH-SDM reads one coherent series across the
-- historical span. NEVER overwrites live gamma_metrics.
--
-- Clock: ts is REAL UTC.
--   - recon rows  (source='hist_greeks_s62'):  sidecar bar_ts is IST-as-UTC -> stored as
--                 (bar_ts - 5h30m) = real UTC, aligning with live gamma_metrics.
--   - expiry rows (source='live_gamma_expiry'): copied verbatim from live gamma_metrics
--                 (already real UTC) for the 18 weekly-expiry days where 0-DTE flat-vol
--                 net_gex is numerically unreconstructible (validated 2025-11-25).
--
-- Grain: 5-min, matching live cadence.
-- pin_risk_score / gamma_concentration: populated for expiry rows (from live); NULL for
--   recon rows pending the live-engine formulas (compute_gamma_metrics_local.py) +
--   their own spot-check gate. net_gex / flip_level / regime are the validated trio.

CREATE TABLE IF NOT EXISTS public.hist_gamma_metrics (
    id                   bigserial   PRIMARY KEY,
    symbol               text        NOT NULL,
    ts                   timestamptz NOT NULL,          -- REAL UTC (see header)
    trade_date           date        NOT NULL,
    net_gex              numeric,                        -- validated (sign 99% / mag 0.96x vs live)
    flip_level           numeric,                        -- recomputed; coverage-sensitive
    regime               text,                           -- sign-based (validated 95% vs live)
    pin_risk_score       numeric,                        -- live-rows: from live; recon-rows: NULL pending formula
    gamma_concentration  numeric,                        -- live-rows: from live; recon-rows: NULL pending formula
    source               text        NOT NULL,           -- 'hist_greeks_s62' | 'live_gamma_expiry'
    created_at           timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_hist_gamma_source CHECK (source IN ('hist_greeks_s62','live_gamma_expiry')),
    CONSTRAINT uniq_hist_gamma_row UNIQUE (symbol, ts, source)
);

CREATE INDEX IF NOT EXISTS idx_hist_gamma_trade_date
    ON public.hist_gamma_metrics (trade_date);
CREATE INDEX IF NOT EXISTS idx_hist_gamma_symbol_ts
    ON public.hist_gamma_metrics (symbol, ts);
