-- =============================================================================
-- MERDIAN — signal_premium_outcomes table
-- Track 1: Outcome measurement layer
-- Created: 2026-04-01
-- Run against: Supabase hot tier
-- DO NOT RUN AGAIN — already executed 2026-04-01
-- =============================================================================

CREATE TABLE signal_premium_outcomes (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_snapshot_id          BIGINT NOT NULL,
    symbol                      TEXT NOT NULL,
    signal_ts                   TIMESTAMPTZ NOT NULL,
    action                      TEXT NOT NULL,
    trade_allowed               BOOLEAN,
    entry_spot                  NUMERIC,
    entry_strike                NUMERIC,
    option_type                 TEXT,
    expiry_date                 DATE,
    dte_at_entry                INTEGER,
    dte_bucket                  TEXT,
    entry_premium               NUMERIC,
    entry_iv                    NUMERIC,
    entry_iv_percentile         NUMERIC,
    entry_quality               TEXT,
    premium_as_pct_spot         NUMERIC,
    gamma_regime                TEXT,
    breadth_regime              TEXT,
    breadth_score               NUMERIC,
    confidence_score            NUMERIC,
    confidence_decile           SMALLINT,
    flip_distance               NUMERIC,
    flip_distance_pct           NUMERIC,
    volatility_regime           TEXT,
    india_vix                   NUMERIC,
    vix_regime                  TEXT,
    straddle_atm                NUMERIC,
    straddle_slope              TEXT,
    wcb_regime                  TEXT,
    wcb_score                   NUMERIC,
    time_of_day                 TIME,
    intraday_bucket             TEXT,
    day_of_week                 SMALLINT,
    session_pct_elapsed         NUMERIC,
    mins_since_prior_signal     NUMERIC,
    consecutive_same_direction  SMALLINT,
    premium_15m                 NUMERIC,
    premium_30m                 NUMERIC,
    premium_60m                 NUMERIC,
    premium_eod                 NUMERIC,
    premium_expiry              NUMERIC,
    move_15m_pts                NUMERIC,
    move_30m_pts                NUMERIC,
    move_60m_pts                NUMERIC,
    move_eod_pts                NUMERIC,
    mfe_session_pts             NUMERIC,
    mae_session_pts             NUMERIC,
    time_to_mfe_mins            NUMERIC,
    mfe_to_close_giveback_pct   NUMERIC,
    drawdown_before_profit_pts  NUMERIC,
    first_adverse_move_pts      NUMERIC,
    captured_25pts              BOOLEAN,
    captured_50pts              BOOLEAN,
    captured_75pts              BOOLEAN,
    captured_100pts             BOOLEAN,
    iv_at_exit                  NUMERIC,
    iv_change_during_trade      NUMERIC,
    iv_crushed                  BOOLEAN,
    spot_move_15m_pts           NUMERIC,
    spot_move_60m_pts           NUMERIC,
    direction_correct           BOOLEAN,
    outcome_label               TEXT,
    failure_mode                TEXT,
    smdm_squeeze_score          NUMERIC,
    smdm_squeeze_alert          BOOLEAN,
    smdm_signal_suppressed      BOOLEAN,
    smdm_pattern_flags          TEXT[],
    smdm_otm_bleed_pct          NUMERIC,
    smdm_straddle_velocity      NUMERIC,
    smdm_otm_oi_velocity        NUMERIC,
    was_squeeze_day             BOOLEAN,
    otm_premium_pre_squeeze     NUMERIC,
    otm_premium_at_squeeze      NUMERIC,
    squeeze_magnitude_pts       NUMERIC,
    data_source                 TEXT NOT NULL DEFAULT 'LIVE',
    evaluation_version          TEXT NOT NULL DEFAULT 'v1',
    path_data_available         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT spo_unique_signal UNIQUE (signal_snapshot_id, symbol)
);

CREATE INDEX idx_spo_ts
    ON signal_premium_outcomes (symbol, signal_ts DESC);
CREATE INDEX idx_spo_conditions
    ON signal_premium_outcomes (gamma_regime, breadth_regime, confidence_decile, action);
CREATE INDEX idx_spo_captures
    ON signal_premium_outcomes (action, captured_25pts, captured_50pts, captured_75pts, captured_100pts);
CREATE INDEX idx_spo_iv_crush
    ON signal_premium_outcomes (iv_crushed, action, gamma_regime)
    WHERE iv_crushed = TRUE;
CREATE INDEX idx_spo_failure
    ON signal_premium_outcomes (failure_mode, action)
    WHERE failure_mode IS NOT NULL;
CREATE INDEX idx_spo_smdm
    ON signal_premium_outcomes (smdm_squeeze_alert, action, symbol)
    WHERE smdm_squeeze_alert = TRUE;
