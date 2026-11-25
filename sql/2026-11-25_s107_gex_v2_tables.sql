-- =====================================================================
-- 2026-11-25_s107_gex_v2_tables.sql
-- ADR-033 (scope D), rule v1.2 -- storage for V2 exposure. Two NEW tables. No V1 object is touched.
--
-- AUTHORED, NOT APPLIED. NOT APPROVED FOR APPLY (operator decision pending the second check).
-- When approved: SQL editor, as postgres, one section at a time, outside 08:30-15:40 IST.
-- If the editor offers to enable RLS: this file enables it itself; answer ENABLE.
--
-- ROLLBACK (two statements, only while nothing reads them):
--   DROP TABLE public.gex_run_v2;
--   DROP TABLE public.gex_strike_v2;
-- =====================================================================

-- SECTION 1 of 4 -- per-strike table (one statement)

CREATE TABLE public.gex_strike_v2 (
  id            bigserial PRIMARY KEY,
  run_id        uuid             NOT NULL,
  symbol        text             NOT NULL,
  ts            timestamptz      NOT NULL,
  expiry_date   date             NOT NULL,
  dte           integer,
  strike        numeric          NOT NULL CHECK (strike > 0),
  spot          numeric          NOT NULL CHECK (spot > 0),
  oi_call       numeric          NOT NULL CHECK (oi_call >= 0),
  oi_put        numeric          NOT NULL CHECK (oi_put >= 0),
  gamma_strike  double precision          CHECK (gamma_strike > 0),
  gamma_legs    text                      CHECK (gamma_legs IN ('both', 'call_only', 'put_only')),
  in_map        boolean          NOT NULL,
  in_band       boolean          NOT NULL,
  net_cr        double precision NOT NULL,
  gross_cr      double precision NOT NULL CHECK (gross_cr >= 0),
  rule_version  text             NOT NULL CHECK (rule_version IN ('v2-1.2', 'v2-1.2-gss')),
  created_at    timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT gex_strike_v2_run_strike_uq UNIQUE (run_id, strike, expiry_date),
  CONSTRAINT gex_strike_v2_oi_ck CHECK (oi_call + oi_put > 0),
  CONSTRAINT gex_strike_v2_none_ck CHECK ((gamma_strike IS NULL) = (gamma_legs IS NULL)),
  CONSTRAINT gex_strike_v2_zero_ck CHECK (gamma_strike IS NOT NULL OR (net_cr = 0 AND gross_cr = 0))
);

-- SECTION 2 of 4 -- per-run table (one statement)

CREATE TABLE public.gex_run_v2 (
  id               bigserial PRIMARY KEY,
  run_id           uuid             NOT NULL,
  symbol           text             NOT NULL,
  ts               timestamptz      NOT NULL,
  expiry_date      date             NOT NULL,
  dte              integer,
  spot             numeric          NOT NULL CHECK (spot > 0),
  net_cr           double precision NOT NULL,
  net_top_share    double precision          CHECK (net_top_share > 0 AND net_top_share <= 1),
  gross_band_cr    double precision NOT NULL CHECK (gross_band_cr >= 0),
  gross_top_share  double precision          CHECK (gross_top_share > 0 AND gross_top_share <= 1),
  gross_hhi        double precision          CHECK (gross_hhi > 0 AND gross_hhi <= 1),
  n_map            integer          NOT NULL CHECK (n_map >= 0),
  n_zero           integer          NOT NULL CHECK (n_zero >= 0 AND n_zero <= n_map),
  n_dup_legs       integer                   CHECK (n_dup_legs >= 0),
  rule_version     text             NOT NULL CHECK (rule_version IN ('v2-1.2', 'v2-1.2-gss')),
  created_at       timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT gex_run_v2_run_uq UNIQUE (run_id, symbol, expiry_date),
  CONSTRAINT gex_run_v2_band_ck CHECK ((gross_top_share IS NULL) = (gross_hhi IS NULL))
);

-- SECTION 3 of 4 -- indexes, comments, access (run one statement at a time)

CREATE INDEX gex_strike_v2_symbol_ts_ix ON public.gex_strike_v2 (symbol, ts DESC);

CREATE INDEX gex_run_v2_symbol_ts_ix ON public.gex_run_v2 (symbol, ts DESC);

COMMENT ON TABLE public.gex_strike_v2 IS
'ADR-033 V2 per-strike exposure, rule v1.2. One row per strike with OI on either leg. gamma_strike = one gamma per strike after the per-leg guard (NULL = none). net_cr = gamma_strike*(oi_call-oi_put)*spot^2/1e7 and gross_cr = gamma_strike*(oi_call+oi_put)*spot^2/1e7, in Crore (multiply by 0.01 for per 1 % move, ADR-032). in_map = a leg has vendor gamma > 0 before the guard. in_band = |strike-spot| <= 0.05*spot. rule_version v2-1.2 = live from the chain; v2-1.2-gss = backfilled from stored gex_strike_snapshots rows (duplicate leg rows not visible). Never written to or from a V1 column. No flip, regime or pin-risk figure exists on V2.';

COMMENT ON TABLE public.gex_run_v2 IS
'ADR-033 V2 run figures, rule v1.2. net_cr = sum of net over the map (whole run). net_top_share = max|net|/sum|net| over the map. gross_band_cr, gross_top_share, gross_hhi are over strikes with in_band and gross_cr > 0 ONLY (the gross pin view''s set), so gross_band_cr is not a whole-run total. n_map = strikes in the map; n_zero = of those, net exactly 0. n_dup_legs = chain legs with more than one row (NULL for backfilled rows).';

ALTER TABLE public.gex_strike_v2 ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.gex_run_v2 ENABLE ROW LEVEL SECURITY;

CREATE POLICY gex_strike_v2_ro_select ON public.gex_strike_v2 FOR SELECT TO merdian_ro USING (true);

CREATE POLICY gex_run_v2_ro_select ON public.gex_run_v2 FOR SELECT TO merdian_ro USING (true);

REVOKE ALL ON TABLE public.gex_strike_v2 FROM PUBLIC, anon, authenticated;

REVOKE ALL ON TABLE public.gex_run_v2 FROM PUBLIC, anon, authenticated;

REVOKE ALL ON SEQUENCE public.gex_strike_v2_id_seq FROM PUBLIC, anon, authenticated;

REVOKE ALL ON SEQUENCE public.gex_run_v2_id_seq FROM PUBLIC, anon, authenticated;

GRANT SELECT ON TABLE public.gex_strike_v2 TO merdian_ro;

GRANT SELECT ON TABLE public.gex_run_v2 TO merdian_ro;

-- SECTION 4 of 4 -- verification. Read-only. Commented so pasting the file runs nothing extra.

-- 4a -- expect two rows: rls t, policies 1, ro_select t, anon_select f, auth_select f, rows 0.
-- SELECT c.relname, c.relrowsecurity AS rls,
--        (SELECT count(*) FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname) AS policies,
--        has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_select,
--        has_table_privilege('anon', c.oid, 'SELECT') AS anon_select,
--        has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_select
--   FROM pg_class c WHERE c.oid IN ('public.gex_strike_v2'::regclass, 'public.gex_run_v2'::regclass) ORDER BY 1;

-- 4b -- the API can see the new tables (PostgREST schema cache). Run from the box AFTER apply, before the writer hook is enabled:
--   expect HTTP 200 and [] from:  GET /rest/v1/gex_run_v2?select=run_id&limit=1   (service key; never print it)

-- 4c -- V-2d, dependency listing: expect 0 rows (no view or function outside the V2 set depends on a V2 table).
-- SELECT DISTINCT dep.relname AS dependent, src.relname AS depends_on
--   FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid JOIN pg_class dep ON dep.oid = r.ev_class
--   JOIN pg_class src ON src.oid = d.refobjid
--  WHERE d.refclassid = 'pg_class'::regclass AND src.relname IN ('gex_strike_v2', 'gex_run_v2')
--    AND dep.oid <> src.oid AND dep.relname NOT LIKE 'v\_gex2\_%' ESCAPE '\';
