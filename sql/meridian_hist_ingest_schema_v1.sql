-- =============================================================================
-- MERDIAN — Migration V1: Historical Vendor Data + Ingest Infrastructure
-- Safe to run against live database — creates NEW tables only.
-- Does NOT modify: instruments, option_chain_snapshots,
--   historical_option_chain_snapshots, signal_labels, raw_ingest_log,
--   or any other existing table.
-- =============================================================================


-- =============================================================================
-- SECTION 1: HISTORICAL OHLCV TABLES
-- These are net-new — vendor 1m bar data is a different structure from
-- the existing snapshot-based option_chain_snapshots.
-- instruments.id (uuid) used as FK — references existing instruments table.
-- =============================================================================

-- 1m OHLCV bars for options — vendor historical data
-- At ~123K rows/day for NIFTY, expect ~31M rows/year at steady state.
-- Rolling 90-day window in hot tier; aged to S3 warm Parquet by aging job.
CREATE TABLE IF NOT EXISTS hist_option_bars_1m (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID            NOT NULL
                        REFERENCES instruments(id) ON DELETE RESTRICT,
    trade_date          DATE            NOT NULL,
    bar_ts              TIMESTAMPTZ     NOT NULL,
    expiry_date         DATE            NOT NULL,
    strike              NUMERIC(10,2)   NOT NULL,
    option_type         TEXT            NOT NULL CHECK (option_type IN ('CE','PE')),
    open                NUMERIC(10,2)   NOT NULL,
    high                NUMERIC(10,2)   NOT NULL,
    low                 NUMERIC(10,2)   NOT NULL,
    close               NUMERIC(10,2)   NOT NULL,
    volume              BIGINT          NOT NULL CHECK (volume >= 0),
    oi                  BIGINT          NOT NULL CHECK (oi >= 0),
    -- Computed Greeks — NULL on raw ingest, populated by post_ingest_compute
    iv                  NUMERIC(10,6),
    delta               NUMERIC(10,6),
    gamma               NUMERIC(12,8),
    theta               NUMERIC(10,4),
    vega                NUMERIC(10,4),
    -- Heston params — NULL until Phase 2, schema forward-compatible
    heston_v0           NUMERIC(12,8),
    heston_kappa        NUMERIC(10,6),
    heston_theta        NUMERIC(12,8),
    heston_xi           NUMERIC(12,8),
    heston_rho          NUMERIC(8,6),
    -- Provenance
    is_pre_market       BOOLEAN         NOT NULL DEFAULT FALSE,
    is_leap             BOOLEAN         NOT NULL DEFAULT FALSE,
    ingest_batch_id     UUID,           -- FK to hist_ingest_log.id
    CONSTRAINT hist_ohlc_integrity CHECK (
        high >= low
        AND close <= high AND close >= low
        AND open <= high AND open >= low
    ),
    CONSTRAINT hist_option_bars_unique
        UNIQUE (instrument_id, bar_ts, expiry_date, strike, option_type)
);

COMMENT ON TABLE hist_option_bars_1m IS
    'Vendor-supplied 1m OHLCV for NIFTY/SENSEX options. '
    'Distinct from option_chain_snapshots (live point-in-time pulls). '
    'Rolling 90-day hot window — aged to S3 warm Parquet, never purged. '
    'Greeks populated async. Heston columns reserved for Phase 2.';

COMMENT ON COLUMN hist_option_bars_1m.is_leap IS
    'TRUE for expiries >90 days at ingest time. Stored but excluded from '
    'live signal computation. Included in warm tier backtests.';


-- 1m OHLCV bars for spot index (NIFTY 50, SENSEX)
-- Volume and OI are structurally zero for cash indices — omitted.
CREATE TABLE IF NOT EXISTS hist_spot_bars_1m (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID            NOT NULL
                        REFERENCES instruments(id) ON DELETE RESTRICT,
    trade_date          DATE            NOT NULL,
    bar_ts              TIMESTAMPTZ     NOT NULL,
    open                NUMERIC(10,2)   NOT NULL,
    high                NUMERIC(10,2)   NOT NULL,
    low                 NUMERIC(10,2)   NOT NULL,
    close               NUMERIC(10,2)   NOT NULL,
    is_pre_market       BOOLEAN         NOT NULL DEFAULT FALSE,
    ingest_batch_id     UUID,
    CONSTRAINT hist_spot_ohlc_integrity CHECK (
        high >= low
        AND close <= high AND close >= low
        AND open <= high AND open >= low
    ),
    CONSTRAINT hist_spot_bars_unique
        UNIQUE (instrument_id, bar_ts)
);

COMMENT ON TABLE hist_spot_bars_1m IS
    'Cash index 1m bars. Volume/OI excluded — always zero for NSE_IDX/BSE_IDX. '
    'Pre-market rows flagged, excluded from signal computation by convention.';


-- 1m OHLCV bars for continuous futures (NIFTY-I, II, III)
CREATE TABLE IF NOT EXISTS hist_future_bars_1m (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID            NOT NULL
                        REFERENCES instruments(id) ON DELETE RESTRICT,
    trade_date          DATE            NOT NULL,
    bar_ts              TIMESTAMPTZ     NOT NULL,
    expiry_date         DATE            NOT NULL,
    contract_series     SMALLINT        NOT NULL CHECK (contract_series IN (1,2,3)),
    open                NUMERIC(10,2)   NOT NULL,
    high                NUMERIC(10,2)   NOT NULL,
    low                 NUMERIC(10,2)   NOT NULL,
    close               NUMERIC(10,2)   NOT NULL,
    volume              BIGINT          NOT NULL,
    oi                  BIGINT          NOT NULL,
    ingest_batch_id     UUID,
    CONSTRAINT hist_future_ohlc_integrity CHECK (
        high >= low
        AND close <= high AND close >= low
        AND open <= high AND open >= low
    ),
    CONSTRAINT hist_future_bars_unique
        UNIQUE (instrument_id, bar_ts, contract_series)
);

COMMENT ON TABLE hist_future_bars_1m IS
    'Continuous futures series (1=front, 2=second, 3=third month). '
    'Preserved for basis and roll analysis. Not consumed by current signal engine.';


-- =============================================================================
-- SECTION 2: INGEST AUDIT INFRASTRUCTURE
-- raw_ingest_log exists but is lightweight (7 cols, operational only).
-- hist_ingest_log is the full audit trail for vendor file loads.
-- Both coexist — hist_ingest_log does not replace raw_ingest_log.
-- =============================================================================

CREATE TABLE IF NOT EXISTS hist_ingest_log (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filename     TEXT            NOT NULL,
    source_checksum     CHAR(64)        NOT NULL,   -- SHA-256 hex
    vendor_date         DATE            NOT NULL,   -- trading date in the file
    segment             TEXT            NOT NULL
                        CHECK (segment IN ('OPTIONS','FUTURES','SPOT','MIXED')),
    rows_received       INTEGER         NOT NULL,
    rows_accepted       INTEGER         NOT NULL,
    rows_rejected       INTEGER         NOT NULL    DEFAULT 0,
    rows_pre_market     INTEGER         NOT NULL    DEFAULT 0,
    rows_leap_flagged   INTEGER         NOT NULL    DEFAULT 0,
    s3_raw_key          TEXT,                       -- cold tier path after archive
    s3_parquet_key      TEXT,                       -- warm tier Parquet path
    started_at          TIMESTAMPTZ     NOT NULL    DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    compute_completed_at TIMESTAMPTZ,               -- post_ingest_compute done?
    status              TEXT            NOT NULL    DEFAULT 'IN_PROGRESS'
                        CHECK (status IN (
                            'IN_PROGRESS',
                            'BARS_LOADED',
                            'COMPUTE_DONE',
                            'ARCHIVED',
                            'FAILED',
                            'PARTIAL'
                        )),
    error_detail        TEXT,
    CONSTRAINT hist_ingest_checksum_unique UNIQUE (source_checksum)
);

COMMENT ON TABLE hist_ingest_log IS
    'Full audit trail for vendor file ingestion. Distinct from raw_ingest_log '
    '(live engine operational log). source_checksum UNIQUE is the primary '
    'deduplication guardrail — same file rejected regardless of filename. '
    'Status progression: IN_PROGRESS → BARS_LOADED → COMPUTE_DONE → ARCHIVED.';


-- Row-level rejection detail
CREATE TABLE IF NOT EXISTS hist_ingest_rejects (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id            UUID            NOT NULL
                        REFERENCES hist_ingest_log(id) ON DELETE CASCADE,
    source_row_number   INTEGER,
    raw_ticker          TEXT,
    raw_date            TEXT,
    raw_time            TEXT,
    reject_reason       TEXT            NOT NULL,
    raw_row             TEXT            -- original CSV row preserved verbatim
);

COMMENT ON TABLE hist_ingest_rejects IS
    'Row-level rejection log per ingest batch. '
    'High reject counts on a batch_id signal vendor data issues. '
    'raw_row preserved for manual inspection and potential reprocessing.';


-- Post-ingest completeness verification
CREATE TABLE IF NOT EXISTS hist_completeness_checks (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id            UUID            NOT NULL
                        REFERENCES hist_ingest_log(id) ON DELETE CASCADE,
    instrument_id       UUID            NOT NULL
                        REFERENCES instruments(id),
    trade_date          DATE            NOT NULL,
    expiry_date         DATE,           -- NULL for spot checks
    expected_bars       INTEGER         NOT NULL,   -- 375 for full session
    actual_bars         INTEGER         NOT NULL,
    coverage_pct        NUMERIC(5,2)    NOT NULL    -- actual/expected * 100
                        GENERATED ALWAYS AS
                            (ROUND((actual_bars::NUMERIC / NULLIF(expected_bars,0)) * 100, 2))
                        STORED,
    flag_incomplete     BOOLEAN         NOT NULL    DEFAULT FALSE,
    checked_at          TIMESTAMPTZ     NOT NULL    DEFAULT now()
);

COMMENT ON TABLE hist_completeness_checks IS
    'Post-ingest bar count verification. coverage_pct is computed automatically. '
    'flag_incomplete=TRUE triggers manual review. '
    'coverage_pct < 80 on an active weekly expiry indicates a material data gap.';


-- =============================================================================
-- SECTION 3: AGING POLICY
-- Configurable retention — read by aging_job.py at runtime.
-- Changing hot_retention_days here changes behaviour everywhere.
-- =============================================================================

CREATE TABLE IF NOT EXISTS aging_policy (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name          TEXT            NOT NULL UNIQUE,
    hot_retention_days  INTEGER         NOT NULL DEFAULT 90,
    enabled             BOOLEAN         NOT NULL DEFAULT TRUE,
    last_run_at         TIMESTAMPTZ,
    last_rows_migrated  INTEGER,
    notes               TEXT
);

COMMENT ON TABLE aging_policy IS
    'Configurable per-table hot tier retention. aging_job.py reads hot_retention_days '
    'at runtime — never hardcode 90 in application code. '
    'Aged rows are written to S3 warm Parquet before deletion from hot tier.';

INSERT INTO aging_policy (table_name, hot_retention_days, notes) VALUES
    ('hist_option_bars_1m',  90,  'Aged to S3 warm Parquet before hot deletion'),
    ('hist_spot_bars_1m',    90,  'Aged to S3 warm Parquet before hot deletion'),
    ('hist_future_bars_1m',  90,  'Aged to S3 warm Parquet before hot deletion')
ON CONFLICT (table_name) DO NOTHING;


-- =============================================================================
-- SECTION 4: IV SURFACE DAILY SUMMARY
-- iv_context_snapshots exists (15 cols) — this is additive, not a replacement.
-- Stores daily EOD surface summary keyed to expiry, with Heston slots reserved.
-- =============================================================================

CREATE TABLE IF NOT EXISTS hist_iv_surface_daily (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id       UUID            NOT NULL
                        REFERENCES instruments(id),
    trade_date          DATE            NOT NULL,
    expiry_date         DATE            NOT NULL,
    snap_ts             TIMESTAMPTZ     NOT NULL,   -- typically 15:29 close bar
    dte                 INTEGER         NOT NULL,
    atm_iv              NUMERIC(10,6),
    skew_25d            NUMERIC(10,6),              -- 25-delta risk reversal
    skew_10d            NUMERIC(10,6),              -- 10-delta risk reversal
    term_slope          NUMERIC(10,6),              -- slope vs next expiry
    -- Heston calibration output — NULL in Phase 1, populated in Phase 2
    heston_v0           NUMERIC(12,8),
    heston_kappa        NUMERIC(10,6),
    heston_theta        NUMERIC(12,8),
    heston_xi           NUMERIC(12,8),
    heston_rho          NUMERIC(8,6),
    heston_calibrated_at TIMESTAMPTZ,
    heston_rmse         NUMERIC(12,8),              -- calibration fit quality
    ingest_batch_id     UUID,
    CONSTRAINT hist_iv_surface_unique
        UNIQUE (instrument_id, trade_date, expiry_date)
);

COMMENT ON TABLE hist_iv_surface_daily IS
    'EOD IV surface summary per expiry per day. Additive alongside iv_context_snapshots. '
    'Full strike-level smile stored in S3 warm derived/ to avoid row explosion here. '
    'Heston columns reserved for Phase 2 — NULL safe throughout Phase 1. '
    'heston_rmse tracks calibration quality for parameter rejection logic.';


-- =============================================================================
-- SECTION 5: INDEXES
-- =============================================================================

-- hist_option_bars_1m
-- Primary signal engine access: latest bars for a specific contract
CREATE INDEX IF NOT EXISTS idx_hist_option_signal
    ON hist_option_bars_1m (instrument_id, expiry_date, strike, option_type, bar_ts DESC);

-- Chain snapshot: full chain at a point in time
CREATE INDEX IF NOT EXISTS idx_hist_option_chain_snap
    ON hist_option_bars_1m (instrument_id, trade_date, bar_ts);

-- Aging job: find rows past retention threshold
CREATE INDEX IF NOT EXISTS idx_hist_option_aging
    ON hist_option_bars_1m (trade_date);

-- Greeks population: find bars with null IV efficiently
CREATE INDEX IF NOT EXISTS idx_hist_option_null_iv
    ON hist_option_bars_1m (instrument_id, trade_date)
    WHERE iv IS NULL;

-- hist_spot_bars_1m
CREATE INDEX IF NOT EXISTS idx_hist_spot_ts
    ON hist_spot_bars_1m (instrument_id, bar_ts DESC);

CREATE INDEX IF NOT EXISTS idx_hist_spot_aging
    ON hist_spot_bars_1m (trade_date);

-- hist_future_bars_1m
CREATE INDEX IF NOT EXISTS idx_hist_future_ts
    ON hist_future_bars_1m (instrument_id, contract_series, bar_ts DESC);

-- hist_ingest_log
CREATE INDEX IF NOT EXISTS idx_hist_ingest_date
    ON hist_ingest_log (vendor_date DESC);

CREATE INDEX IF NOT EXISTS idx_hist_ingest_status
    ON hist_ingest_log (status)
    WHERE status IN ('IN_PROGRESS','BARS_LOADED','FAILED','PARTIAL');

-- hist_iv_surface_daily
CREATE INDEX IF NOT EXISTS idx_hist_iv_surface_lookup
    ON hist_iv_surface_daily (instrument_id, expiry_date, trade_date DESC);


-- =============================================================================
-- SECTION 6: AGING HELPER FUNCTION
-- Returns row counts eligible for migration — does NOT modify data.
-- aging_job.py calls this, writes S3 Parquet, confirms write,
-- then issues DELETE WHERE trade_date < cutoff.
-- =============================================================================

CREATE OR REPLACE FUNCTION hist_bars_eligible_for_aging()
RETURNS TABLE (
    table_name      TEXT,
    eligible_rows   BIGINT,
    cutoff_date     DATE
) AS $$
DECLARE
    v_option_cutoff  DATE;
    v_spot_cutoff    DATE;
    v_future_cutoff  DATE;
BEGIN
    SELECT CURRENT_DATE - hot_retention_days INTO v_option_cutoff
    FROM aging_policy WHERE table_name = 'hist_option_bars_1m' AND enabled = TRUE;

    SELECT CURRENT_DATE - hot_retention_days INTO v_spot_cutoff
    FROM aging_policy WHERE table_name = 'hist_spot_bars_1m' AND enabled = TRUE;

    SELECT CURRENT_DATE - hot_retention_days INTO v_future_cutoff
    FROM aging_policy WHERE table_name = 'hist_future_bars_1m' AND enabled = TRUE;

    RETURN QUERY
    SELECT 'hist_option_bars_1m'::TEXT, COUNT(*)::BIGINT, v_option_cutoff
    FROM hist_option_bars_1m WHERE trade_date < v_option_cutoff;

    RETURN QUERY
    SELECT 'hist_spot_bars_1m'::TEXT, COUNT(*)::BIGINT, v_spot_cutoff
    FROM hist_spot_bars_1m WHERE trade_date < v_spot_cutoff;

    RETURN QUERY
    SELECT 'hist_future_bars_1m'::TEXT, COUNT(*)::BIGINT, v_future_cutoff
    FROM hist_future_bars_1m WHERE trade_date < v_future_cutoff;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION hist_bars_eligible_for_aging() IS
    'Read-only — returns counts only, modifies nothing. '
    'aging_job.py uses this to determine batch size before writing S3. '
    'Deletion only after S3 write is confirmed via s3_parquet_key in hist_ingest_log.';


-- =============================================================================
-- END OF MIGRATION
-- Version: 1.0
-- Tables created: 7 (hist_option_bars_1m, hist_spot_bars_1m,
--   hist_future_bars_1m, hist_ingest_log, hist_ingest_rejects,
--   hist_completeness_checks, aging_policy, hist_iv_surface_daily)
-- Tables untouched: all existing MERDIAN tables
-- Portability: standard PostgreSQL — no Supabase-specific syntax
-- =============================================================================
