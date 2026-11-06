-- =====================================================================
-- Tape live flow-vs-book: the four tape_live_* tables (docs/tape/L0_plan.md section 5; spec s3).
-- AUTHORED, NOT APPLIED (L0). Rendered by services/tape_live/ddl.py from services/tape_db/tape_schema.py.
-- Supabase SQL editor, postgres, ONE execution, in L2 only. Idempotent: IF NOT EXISTS everywhere, policies
-- created only if absent, REVOKE / COMMENT re-runnable. Additive only. Display only, never scored.
-- Readers: tape_ro (the /tape page path) and merdian_ro, SELECT only. No anon, no authenticated.
-- =====================================================================

BEGIN;

DO $v$ BEGIN
  IF current_setting('server_version_num')::int < 150000 THEN
    RAISE EXCEPTION 'tape live: UNIQUE NULLS NOT DISTINCT needs PostgreSQL >= 15, server is %', current_setting('server_version');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tape_ro') THEN
    RAISE EXCEPTION 'tape live: role tape_ro does not exist; create it before this file';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'merdian_ro') THEN
    RAISE EXCEPTION 'tape live: role merdian_ro does not exist; create it before this file';
  END IF;
END $v$;

-- ---------------------------------------------------------------- tape_live_cycle
CREATE TABLE IF NOT EXISTS public.tape_live_cycle (
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
    as_of                    timestamptz NOT NULL,
    live_run_id              uuid NOT NULL,
    code_sha                 text NOT NULL,
    CONSTRAINT tape_live_cycle_pk PRIMARY KEY (symbol, trading_day, instrument_token, ts_ist),
    CONSTRAINT tape_live_cycle_grain_uq UNIQUE NULLS NOT DISTINCT (symbol, trading_day, expiry, strike, leg, ts_ist)
);
CREATE INDEX IF NOT EXISTS ix_tape_live_cycle_trading_day ON public.tape_live_cycle (trading_day);
COMMENT ON TABLE public.tape_live_cycle IS 'Tape live flow-vs-book (docs/tape/tape_live_flow_vs_book_spec_v0.1.md). Provisional 5-minute strike-leg cycle rows, upserted every cycle; data columns, key and grain are those of the offline cycle table, generated from services/tape_db/tape_schema.py. Writer: services/tape_live (W). Owner: operator. Tier: research. Rows are display only, never scored: no scoring SQL reads this relation and nothing in it is evidence under pre-registration v0.4. Provenance per row: as_of (writer clock, UTC), live_run_id, code_sha.';

ALTER TABLE public.tape_live_cycle ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_cycle' AND policyname = 'tape_ro_select') THEN
    CREATE POLICY tape_ro_select ON public.tape_live_cycle FOR SELECT TO tape_ro USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_cycle' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_live_cycle FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_live_cycle FROM anon, authenticated;
GRANT SELECT ON public.tape_live_cycle TO tape_ro, merdian_ro;

-- ---------------------------------------------------------------- tape_live_events
CREATE TABLE IF NOT EXISTS public.tape_live_events (
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
    as_of                    timestamptz NOT NULL,
    live_run_id              uuid NOT NULL,
    code_sha                 text NOT NULL,
    CONSTRAINT tape_live_events_grain_uq UNIQUE NULLS NOT DISTINCT (symbol, trading_day, expiry, strike, leg, kind, ts_ist, side)
);
CREATE INDEX IF NOT EXISTS ix_tape_live_events_trading_day ON public.tape_live_events (trading_day);
COMMENT ON TABLE public.tape_live_events IS 'Tape live flow-vs-book (docs/tape/tape_live_flow_vs_book_spec_v0.1.md). Provisional CONC / THIN event candidates up to the cycle; upserted, and deleted when a later cycle no longer produces them; columns from services/tape_db/tape_schema.py. Writer: services/tape_live (W). Owner: operator. Tier: research. Rows are display only, never scored: no scoring SQL reads this relation and nothing in it is evidence under pre-registration v0.4. Provenance per row: as_of (writer clock, UTC), live_run_id, code_sha.';

ALTER TABLE public.tape_live_events ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_events' AND policyname = 'tape_ro_select') THEN
    CREATE POLICY tape_ro_select ON public.tape_live_events FOR SELECT TO tape_ro USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_events' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_live_events FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_live_events FROM anon, authenticated;
GRANT SELECT ON public.tape_live_events TO tape_ro, merdian_ro;

-- ---------------------------------------------------------------- tape_live_wall
CREATE TABLE IF NOT EXISTS public.tape_live_wall (
    symbol                   text NOT NULL,
    trading_day              date NOT NULL,
    expiry                   date NOT NULL,
    ts_ist                   timestamptz NOT NULL,
    chain_run_id             text NOT NULL,
    chain_run_ts             timestamptz NOT NULL,
    call_wall                numeric,
    put_wall                 numeric,
    call_wall_oi_call        bigint,
    put_wall_oi_put          bigint,
    as_of                    timestamptz NOT NULL,
    live_run_id              uuid NOT NULL,
    code_sha                 text NOT NULL,
    CONSTRAINT tape_live_wall_pk PRIMARY KEY (symbol, trading_day, expiry, ts_ist)
);
CREATE INDEX IF NOT EXISTS ix_tape_live_wall_trading_day ON public.tape_live_wall (trading_day);
COMMENT ON TABLE public.tape_live_wall IS 'Tape live flow-vs-book (docs/tape/tape_live_flow_vs_book_spec_v0.1.md). The chain run used for each 5-minute grid point T (the latest run whose timestamp floored to the grid is <= T), its front expiry, call wall (largest oi on the CE side) and put wall (largest on the PE side) and those two OI values. Writer: services/tape_live (W). Owner: operator. Tier: research. Rows are display only, never scored: no scoring SQL reads this relation and nothing in it is evidence under pre-registration v0.4. Provenance per row: as_of (writer clock, UTC), live_run_id, code_sha.';

ALTER TABLE public.tape_live_wall ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_wall' AND policyname = 'tape_ro_select') THEN
    CREATE POLICY tape_ro_select ON public.tape_live_wall FOR SELECT TO tape_ro USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_wall' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_live_wall FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_live_wall FROM anon, authenticated;
GRANT SELECT ON public.tape_live_wall TO tape_ro, merdian_ro;

-- ---------------------------------------------------------------- tape_live_label
CREATE TABLE IF NOT EXISTS public.tape_live_label (
    symbol                   text NOT NULL,
    trading_day              date NOT NULL,
    ts_ist                   timestamptz NOT NULL,
    wall                     text NOT NULL,
    rule_version             text NOT NULL,
    strike                   numeric,
    leg                      text NOT NULL,
    label                    text NOT NULL,
    partial                  boolean NOT NULL,
    reason                   text NOT NULL,
    flags                    jsonb NOT NULL,
    as_of                    timestamptz NOT NULL,
    live_run_id              uuid NOT NULL,
    code_sha                 text NOT NULL,
    CONSTRAINT tape_live_label_pk PRIMARY KEY (symbol, trading_day, ts_ist, wall, rule_version),
    CONSTRAINT tape_live_label_wall_ck CHECK (wall IN ('call', 'put')),
    CONSTRAINT tape_live_label_label_ck CHECK (label IN ('HIT', 'ABSORBED', 'THINNING', 'QUIET', 'NO_READ')),
    CONSTRAINT tape_live_label_leg_ck CHECK (leg IN ('CE', 'PE'))
);
CREATE INDEX IF NOT EXISTS ix_tape_live_label_trading_day ON public.tape_live_label (trading_day);
COMMENT ON TABLE public.tape_live_label IS 'Tape live flow-vs-book (docs/tape/tape_live_flow_vs_book_spec_v0.1.md). As-seen label record per wall and grid point: insert-only, first label wins (ON CONFLICT DO NOTHING), never recomputed; services/tape_live/verify_day.py compares it with the final rows after load. Writer: services/tape_live (W). Owner: operator. Tier: research. Rows are display only, never scored: no scoring SQL reads this relation and nothing in it is evidence under pre-registration v0.4. Provenance per row: as_of (writer clock, UTC), live_run_id, code_sha.';

ALTER TABLE public.tape_live_label ENABLE ROW LEVEL SECURITY;
DO $p$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_label' AND policyname = 'tape_ro_select') THEN
    CREATE POLICY tape_ro_select ON public.tape_live_label FOR SELECT TO tape_ro USING (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tape_live_label' AND policyname = 'merdian_ro_select') THEN
    CREATE POLICY merdian_ro_select ON public.tape_live_label FOR SELECT TO merdian_ro USING (true);
  END IF;
END $p$;
REVOKE ALL ON public.tape_live_label FROM anon, authenticated;
GRANT SELECT ON public.tape_live_label TO tape_ro, merdian_ro;

COMMIT;
