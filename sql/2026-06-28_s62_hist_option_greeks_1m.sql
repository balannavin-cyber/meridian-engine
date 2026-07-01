-- 2026-06-28_s62_hist_option_greeks_1m.sql
-- TD-S58-NEW-1 Greeks backfill — sidecar table (vendor hist_option_bars_1m is NOT mutated).
-- Lean schema: iv + gamma only. iv is the recoverable substrate (any further Greek —
-- delta/theta/vega/charm/vanna — is a cheap closed-form recompute off iv+S+K+T+r, no re-solve).
-- gamma is the validated ENH-SDM input (pin_risk / gamma_concentration / net_gex).
-- Stage 1 scope: NIFTY, Sep–Dec 2025. SENSEX + remaining window follow after aggregate spot-check.

CREATE TABLE IF NOT EXISTS public.hist_option_greeks_1m (
    id             bigserial   PRIMARY KEY,
    instrument_id  uuid        NOT NULL,                 -- matches instruments.id (NIFTY/SENSEX)
    bar_ts         timestamptz NOT NULL,                 -- raw IST-as-UTC, copied verbatim (ZERO shift)
    trade_date     date        NOT NULL,                 -- copied verbatim; chunk key + index
    strike         numeric     NOT NULL,
    option_type    text        NOT NULL,                 -- 'CE' | 'PE'
    expiry_date    date        NOT NULL,
    iv             numeric,                              -- solved at flat r; NULL if no inversion
    gamma          numeric,                              -- BS gamma on solved iv; NULL if iv NULL
    r_used         numeric     NOT NULL DEFAULT 0.065,   -- flat r — ENH-07 A closed, no basis rate
    source         text        NOT NULL DEFAULT 'hist_greeks_s62',
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chk_option_type_valid CHECK (option_type IN ('CE','PE')),
    CONSTRAINT uniq_hist_greeks_row UNIQUE (instrument_id, bar_ts, strike, expiry_date, option_type)
);

-- chunk-scan (resume / per-day aggregate recompute)
CREATE INDEX IF NOT EXISTS idx_hist_greeks_trade_date
    ON public.hist_option_greeks_1m (trade_date);

-- per-bar chain assembly (aggregate recompute reads a whole chain at one bar_ts)
CREATE INDEX IF NOT EXISTS idx_hist_greeks_instr_barts
    ON public.hist_option_greeks_1m (instrument_id, bar_ts);

-- NOTE: UNIQUE key = row-level idempotency. Backfill UPSERTs ON CONFLICT, so re-running a
-- trade_date overwrites cleanly (no duplicate rows, no manual cleanup on resume).
