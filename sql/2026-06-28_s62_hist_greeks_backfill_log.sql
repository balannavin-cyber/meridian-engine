-- 2026-06-28_s62_hist_greeks_backfill_log.sql
-- Resume marker for the Greeks backfill. One row per completed (trade_date, symbol) chunk.
-- Resume = "skip dates already DONE" — survives SSM timeout / restart without re-solving.

CREATE TABLE IF NOT EXISTS public.hist_greeks_backfill_log (
    id            bigserial   PRIMARY KEY,
    trade_date    date        NOT NULL,
    symbol        text        NOT NULL,                  -- 'NIFTY' | 'SENSEX'
    rows_written  integer     NOT NULL DEFAULT 0,
    rows_null_iv  integer     NOT NULL DEFAULT 0,        -- strikes that didn't invert (expected, tracked)
    status        text        NOT NULL,                  -- 'DONE' | 'PARTIAL' | 'ERROR'
    detail        text,                                  -- free-text (error class, notes)
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    CONSTRAINT chk_backfill_status_valid CHECK (status IN ('DONE','PARTIAL','ERROR')),
    CONSTRAINT uniq_backfill_chunk UNIQUE (trade_date, symbol)
);

CREATE INDEX IF NOT EXISTS idx_hist_greeks_log_status
    ON public.hist_greeks_backfill_log (status, symbol);

-- Resume query the backfill runs at start:
--   SELECT trade_date FROM hist_greeks_backfill_log
--   WHERE symbol = :sym AND status = 'DONE';
-- ...and skips those dates. PARTIAL/ERROR dates are re-attempted (UPSERT on the greeks UNIQUE key
-- makes re-solving a completed-but-logged-PARTIAL date safe).
