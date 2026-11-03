-- =====================================================================
-- Tape T1-db: sidecar tables (docs/tape/T1_db_plan.md sections 1.1-1.2).
-- AUTHORED, NOT APPLIED. Rendered by services/tape_db/sidecar_sql.py from tape_schema.py.
-- Supabase SQL editor, postgres, ONE execution. Idempotent: IF NOT EXISTS everywhere, policies
-- created only if absent, REVOKE/GRANT/COMMENT re-runnable. Additive only.
-- When the editor offers to enable RLS: the DDL already enables it WITH a merdian_ro policy
-- (ADR-031 D6) - either answer leaves the same end state (S90 precedent).
-- Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800.
-- Post-apply check: services/tape_db/check_tape_access.sql.
-- =====================================================================

BEGIN;

DO $v$ BEGIN
  IF current_setting('server_version_num')::int < 150000 THEN
    RAISE EXCEPTION 'tape T1-db: UNIQUE NULLS NOT DISTINCT needs PostgreSQL >= 15, server is %', current_setting('server_version');
  END IF;
END $v$;

-- ---------------------------------------------------------------- tape_minute
CREATE TABLE IF NOT EXISTS public.tape_minute (
    trading_day              date NOT NULL,
    symbol                   text NOT NULL,
    role                     text NOT NULL,
    opt_type                 text,
    strike                   numeric,
    expiry                   date,
    instrument_token         bigint NOT NULL,
    tradingsymbol            text,
    minute_ist               timestamptz NOT NULL,
    buy_qty                  bigint,
    sell_qty                 bigint,
    uncl_qty                 bigint,
    gap_qty                  bigint,
    trades                   bigint,
    vwap                     double precision,
    bid_qty_5                bigint,
    ask_qty_5                bigint,
    oi                       bigint,
    oi_delta                 bigint,
    exch_ts_max              timestamptz,
    run_id                   uuid NOT NULL,
    code_sha                 text NOT NULL,
    source                   text NOT NULL,
    config_version           text,
    loaded_at                timestamptz NOT NULL,
    CONSTRAINT tape_minute_pk PRIMARY KEY (symbol, trading_day, instrument_token, minute_ist)
);
CREATE INDEX IF NOT EXISTS ix_tape_minute_trading_day ON public.tape_minute (trading_day);
COMMENT ON TABLE public.tape_minute IS 'Tape T1-db sidecar, tape side. Source: tape T1a/T1b offline output tape_minute.csv. Writer: services/tape_db/load_day.py (offline, one load per trading day; --replace deletes the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800: this relation is never combined with the chain-side (tape_chain_*) relations by any view, function, trigger or loader step; the later, hashed scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). Plan: docs/tape/T1_db_plan.md.';
COMMENT ON COLUMN public.tape_minute.config_version IS 'OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.';
COMMENT ON COLUMN public.tape_minute.minute_ist IS 'tape_minute.csv minute (HH:MM, IST) on trading_day, stored as <day>T<HH:MM>:00+05:30.';

ALTER TABLE public.tape_minute ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_minute' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_minute FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_minute FROM anon, authenticated;
GRANT SELECT ON public.tape_minute TO merdian_ro;

-- ---------------------------------------------------------------- tape_strike_cycle
CREATE TABLE IF NOT EXISTS public.tape_strike_cycle (
    trading_day              date NOT NULL,
    symbol                   text NOT NULL,
    expiry                   date,
    strike                   numeric,
    leg                      text NOT NULL,
    instrument_token         bigint NOT NULL,
    tradingsymbol            text,
    ts_ist                   timestamptz NOT NULL,
    buy_5                    bigint,
    sell_5                   bigint,
    uncl_5                   bigint,
    gap_5                    bigint,
    trades_5                 bigint,
    buy_15                   bigint,
    sell_15                  bigint,
    buy_30                   bigint,
    sell_30                  bigint,
    balance_5                double precision,
    balance_15               double precision,
    balance_30               double precision,
    resting_imb              double precision,
    classified_share_5       double precision,
    buy_cum                  bigint,
    sell_cum                 bigint,
    uncl_cum                 bigint,
    gap_cum                  bigint,
    oi_last                  bigint,
    oi_delta_5               bigint,
    minutes_present_5        integer,
    first_seen_ts_ist        timestamptz,
    run_id                   uuid NOT NULL,
    code_sha                 text NOT NULL,
    source                   text NOT NULL,
    config_version           text,
    loaded_at                timestamptz NOT NULL,
    CONSTRAINT tape_strike_cycle_pk PRIMARY KEY (symbol, trading_day, instrument_token, ts_ist),
    CONSTRAINT tape_strike_cycle_grain_uq UNIQUE NULLS NOT DISTINCT (symbol, trading_day, expiry, strike, leg, ts_ist)
);
CREATE INDEX IF NOT EXISTS ix_tape_strike_cycle_trading_day ON public.tape_strike_cycle (trading_day);
COMMENT ON TABLE public.tape_strike_cycle IS 'Tape T1-db sidecar, tape side. Source: tape T1a/T1b offline output tape_strike_cycle.csv. Writer: services/tape_db/load_day.py (offline, one load per trading day; --replace deletes the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800: this relation is never combined with the chain-side (tape_chain_*) relations by any view, function, trigger or loader step; the later, hashed scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). Plan: docs/tape/T1_db_plan.md.';
COMMENT ON COLUMN public.tape_strike_cycle.config_version IS 'OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.';
COMMENT ON CONSTRAINT tape_strike_cycle_grain_uq ON public.tape_strike_cycle IS 'Plan grain kept as a constraint (FUT rows have NULL strike / expiry, so it cannot be the PK). Also asserts no two instrument tokens map to one strike-leg on a day.';

ALTER TABLE public.tape_strike_cycle ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_strike_cycle' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_strike_cycle FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_strike_cycle FROM anon, authenticated;
GRANT SELECT ON public.tape_strike_cycle TO merdian_ro;

-- ---------------------------------------------------------------- tape_events
CREATE TABLE IF NOT EXISTS public.tape_events (
    trading_day              date NOT NULL,
    symbol                   text NOT NULL,
    expiry                   date,
    strike                   numeric,
    leg                      text NOT NULL,
    kind                     text NOT NULL,
    ts_ist                   timestamptz NOT NULL,
    side                     text NOT NULL,
    magnitude                double precision,
    detail                   jsonb,
    run_id                   uuid NOT NULL,
    code_sha                 text NOT NULL,
    source                   text NOT NULL,
    config_version           text,
    loaded_at                timestamptz NOT NULL,
    CONSTRAINT tape_events_grain_uq UNIQUE NULLS NOT DISTINCT (symbol, trading_day, expiry, strike, leg, kind, ts_ist, side)
);
CREATE INDEX IF NOT EXISTS ix_tape_events_trading_day ON public.tape_events (trading_day);
COMMENT ON TABLE public.tape_events IS 'Tape T1-db sidecar, tape side. Source: tape T1a/T1b offline output tape_events.csv. Writer: services/tape_db/load_day.py (offline, one load per trading day; --replace deletes the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800: this relation is never combined with the chain-side (tape_chain_*) relations by any view, function, trigger or loader step; the later, hashed scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). Plan: docs/tape/T1_db_plan.md.';
COMMENT ON COLUMN public.tape_events.config_version IS 'OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.';
COMMENT ON CONSTRAINT tape_events_grain_uq ON public.tape_events IS 'Grain. No PRIMARY KEY: FUT rows carry NULL strike and expiry, so no NOT NULL natural key exists. NULLS NOT DISTINCT makes two FUT rows at one grain a violation.';

ALTER TABLE public.tape_events ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_events' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_events FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_events FROM anon, authenticated;
GRANT SELECT ON public.tape_events TO merdian_ro;

-- ---------------------------------------------------------------- tape_chain_runs
CREATE TABLE IF NOT EXISTS public.tape_chain_runs (
    trading_day              date NOT NULL,
    symbol                   text NOT NULL,
    expiry                   date NOT NULL,
    ts_ist                   timestamptz NOT NULL,
    chain_run_id             text,
    n_strikes                integer,
    leader_strike            numeric,
    call_wall                numeric,
    put_wall                 numeric,
    net_sign                 smallint,
    in_window                boolean,
    run_id                   uuid NOT NULL,
    code_sha                 text NOT NULL,
    source                   text NOT NULL,
    config_version           text,
    loaded_at                timestamptz NOT NULL,
    CONSTRAINT tape_chain_runs_pk PRIMARY KEY (symbol, trading_day, expiry, ts_ist)
);
CREATE INDEX IF NOT EXISTS ix_tape_chain_runs_trading_day ON public.tape_chain_runs (trading_day);
COMMENT ON TABLE public.tape_chain_runs IS 'Tape T1-db sidecar, chain side. Source: tape T1a/T1b offline output chain_runs.csv. Writer: services/tape_db/load_day.py (offline, one load per trading day; --replace deletes the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800: this relation is never combined with the tape-side (tape_minute, tape_strike_cycle, tape_events, tape_daily_report) relations by any view, function, trigger or loader step; the later, hashed scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). Plan: docs/tape/T1_db_plan.md.';
COMMENT ON COLUMN public.tape_chain_runs.config_version IS 'OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.';
COMMENT ON COLUMN public.tape_chain_runs.chain_run_id IS 'chain_runs.csv run_id (the chain / gamma run), renamed so it cannot be read as the load''s provenance run_id.';

ALTER TABLE public.tape_chain_runs ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_chain_runs' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_chain_runs FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_chain_runs FROM anon, authenticated;
GRANT SELECT ON public.tape_chain_runs TO merdian_ro;

-- ---------------------------------------------------------------- tape_chain_events
CREATE TABLE IF NOT EXISTS public.tape_chain_events (
    trading_day              date NOT NULL,
    symbol                   text NOT NULL,
    expiry                   date NOT NULL,
    kind                     text NOT NULL,
    ts_ist                   timestamptz NOT NULL,
    strike                   numeric NOT NULL,
    prev_strike              numeric,
    prev_value               double precision,
    new_value                double precision,
    merged_n                 integer,
    run_id                   uuid NOT NULL,
    code_sha                 text NOT NULL,
    source                   text NOT NULL,
    config_version           text,
    loaded_at                timestamptz NOT NULL,
    CONSTRAINT tape_chain_events_pk PRIMARY KEY (symbol, trading_day, expiry, kind, ts_ist, strike)
);
CREATE INDEX IF NOT EXISTS ix_tape_chain_events_trading_day ON public.tape_chain_events (trading_day);
COMMENT ON TABLE public.tape_chain_events IS 'Tape T1-db sidecar, chain side. Source: tape T1a/T1b offline output chain_events.csv. Writer: services/tape_db/load_day.py (offline, one load per trading day; --replace deletes the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800: this relation is never combined with the tape-side (tape_minute, tape_strike_cycle, tape_events, tape_daily_report) relations by any view, function, trigger or loader step; the later, hashed scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). Plan: docs/tape/T1_db_plan.md.';
COMMENT ON COLUMN public.tape_chain_events.config_version IS 'OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.';

ALTER TABLE public.tape_chain_events ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_chain_events' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_chain_events FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_chain_events FROM anon, authenticated;
GRANT SELECT ON public.tape_chain_events TO merdian_ro;

-- ---------------------------------------------------------------- tape_daily_report
CREATE TABLE IF NOT EXISTS public.tape_daily_report (
    symbol                   text NOT NULL,
    trading_day              date NOT NULL,
    completeness_pct         double precision,
    gaps_gt_10s              integer,
    gaps_gt_60s              integer,
    packets                  bigint,
    segments                 integer,
    uploads_ok               integer,
    uploads_retried          integer,
    uploads_failed           integer,
    skew_median_s            double precision,
    connects                 integer,
    reconnects               integer,
    disconnects              integer,
    watchdog_trips           integer,
    frame_errors             integer,
    g3_verdict               text,
    classified_share_early   double precision,
    classified_share_late    double precision,
    report                   jsonb,
    g3                       jsonb,
    run_id                   uuid NOT NULL,
    code_sha                 text NOT NULL,
    source                   text NOT NULL,
    config_version           text,
    loaded_at                timestamptz NOT NULL,
    CONSTRAINT tape_daily_report_pk PRIMARY KEY (symbol, trading_day)
);
CREATE INDEX IF NOT EXISTS ix_tape_daily_report_trading_day ON public.tape_daily_report (trading_day);
COMMENT ON TABLE public.tape_daily_report IS 'Tape T1-db sidecar, tape side. Source: runner daily_report_<day>.json + T1a g3_report.json. Writer: services/tape_db/load_day.py (offline, one load per trading day; --replace deletes the day first). Owner: operator. Tier: research (3). Pre-registration v0.2 sha256 71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800: this relation is never combined with the chain-side (tape_chain_*) relations by any view, function, trigger or loader step; the later, hashed scoring SQL is the only place the two sides meet. Provenance per row: run_id (= script_execution_log.run_id of the load), code_sha (git rev-parse HEAD at load), source, config_version (OWED, NULL), loaded_at (UTC). Plan: docs/tape/T1_db_plan.md.';
COMMENT ON COLUMN public.tape_daily_report.config_version IS 'OWED: no tape config version exists yet; NULL until one is defined. Never a placeholder.';
COMMENT ON COLUMN public.tape_daily_report.completeness_pct IS 'OWED: pre-registration rule 4 defines completeness; that definition is not in the repo, so T1-db stores NULL rather than invent one.';
COMMENT ON COLUMN public.tape_daily_report.connects IS 'OWED: the T0 runner daily report does not write a connect count (T0.1). NULL, never 0.';
COMMENT ON COLUMN public.tape_daily_report.watchdog_trips IS 'OWED until T0.1: not in the T0 runner daily report. NULL, never 0.';
COMMENT ON COLUMN public.tape_daily_report.frame_errors IS 'OWED until T0.1: not in the T0 runner daily report. NULL, never 0.';

ALTER TABLE public.tape_daily_report ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_daily_report' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_daily_report FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_daily_report FROM anon, authenticated;
GRANT SELECT ON public.tape_daily_report TO merdian_ro;

COMMIT;
