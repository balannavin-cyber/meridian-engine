-- =====================================================================
-- 2026-11-25_s107_stepA_apply_ALL.sql
-- STEP A of the operator decision of 2026-11-25 18:50 IST (ADR-033, rule v1.2).
-- ONE PASTE. Creates, in one transaction: gex_strike_v2, gex_run_v2 (tables, indexes, comments, RLS,
-- merdian_ro read policy and grant), p3b2_invariant_checks (table, RLS, merdian_ro read) and the
-- function p3b2_sweep. It does NOT schedule the p3b2 job and touches no existing object.
-- It is the two files 2026-11-25_s107_gex_v2_tables.sql (sections 1-3) and
-- 2026-11-25_s107_p3b2_invariant_checks.sql (sections 1-2) joined, nothing else.
-- Paste the whole file into the SQL editor as postgres and run it once. If any statement fails,
-- the whole transaction rolls back and nothing is created.
--
-- ROLLBACK (only while nothing reads them; run as one block):
--   BEGIN;
--   DROP FUNCTION public.p3b2_sweep(timestamptz, interval, interval);
--   DROP TABLE public.p3b2_invariant_checks;
--   DROP TABLE public.gex_run_v2;
--   DROP TABLE public.gex_strike_v2;
--   COMMIT;
-- =====================================================================

BEGIN;

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

-- The writer and the backfill use the service key. service_role bypasses RLS but still needs table
-- privileges, and default privileges in public were narrowed in S104, so they are granted here explicitly.
-- No DELETE: rows are removed only by the operator as postgres.
GRANT SELECT, INSERT, UPDATE ON TABLE public.gex_strike_v2 TO service_role;

GRANT SELECT, INSERT, UPDATE ON TABLE public.gex_run_v2 TO service_role;

GRANT USAGE, SELECT ON SEQUENCE public.gex_strike_v2_id_seq TO service_role;

GRANT USAGE, SELECT ON SEQUENCE public.gex_run_v2_id_seq TO service_role;


-- SECTION 1 of 4 -- table and access (run as one block)

CREATE TABLE public.p3b2_invariant_checks (
  id            bigserial PRIMARY KEY,
  kind          text        NOT NULL CHECK (kind IN ('check', 'sweep')),
  symbol        text,
  expiry_date   date,
  run_id        uuid,
  ts            timestamptz,
  check_id      text        CHECK (check_id IN ('V0','V1','V2','V3','V4','V5')),
  status        text        NOT NULL CHECK (status IN ('OK','FAIL','NOT_COMPUTED','INFO','SWEEP_OK','SWEEP_ERROR')),
  n_checked     integer,
  n_fail        integer,
  max_abs_diff  double precision,
  detail        jsonb,
  checked_at    timestamptz NOT NULL DEFAULT now(),
  fn_version    text        NOT NULL,
  CHECK ((kind = 'check') = (check_id IS NOT NULL AND run_id IS NOT NULL))
);
CREATE UNIQUE INDEX p3b2_invariant_checks_run_uq
  ON public.p3b2_invariant_checks (symbol, expiry_date, run_id, check_id) WHERE kind = 'check';
CREATE INDEX p3b2_invariant_checks_ts_ix ON public.p3b2_invariant_checks (ts);
CREATE INDEX p3b2_invariant_checks_checked_at_ix ON public.p3b2_invariant_checks (checked_at);
ALTER TABLE public.p3b2_invariant_checks ENABLE ROW LEVEL SECURITY;
CREATE POLICY p3b2_invariant_checks_ro_select ON public.p3b2_invariant_checks FOR SELECT TO merdian_ro USING (true);
REVOKE ALL ON TABLE public.p3b2_invariant_checks FROM PUBLIC, anon, authenticated;
REVOKE ALL ON SEQUENCE public.p3b2_invariant_checks_id_seq FROM PUBLIC, anon, authenticated;
GRANT SELECT ON TABLE public.p3b2_invariant_checks TO merdian_ro;

-- SECTION 2 of 4 -- the function (run as one block)

CREATE OR REPLACE FUNCTION public.p3b2_sweep(
  p_now      timestamptz DEFAULT now(),
  p_window   interval    DEFAULT interval '60 minutes',
  p_min_age  interval    DEFAULT interval '3 minutes')
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
SET enable_nestloop = off
AS $fn$
DECLARE
  v_ver  constant text := 'p3b2-v1.0 (rule v2-1.2)';
  v_runs integer := 0;
  v_lo   timestamptz;
  v_hi   timestamptz;
BEGIN
  CREATE TEMP TABLE IF NOT EXISTS p3b2_cand (symbol text, expiry_date date, run_id uuid, ts timestamptz) ON COMMIT DROP;
  TRUNCATE p3b2_cand;
  INSERT INTO p3b2_cand
  SELECT g.symbol, g.expiry_date, g.run_id, min(g.ts)
  FROM gex_strike_snapshots g
  WHERE g.ts >= p_now - p_window AND g.ts <= p_now - p_min_age
    AND NOT EXISTS (SELECT 1 FROM p3b2_invariant_checks c
                    WHERE c.kind = 'check' AND c.symbol = g.symbol AND c.expiry_date = g.expiry_date AND c.run_id = g.run_id)
  GROUP BY g.symbol, g.expiry_date, g.run_id;
  GET DIAGNOSTICS v_runs = ROW_COUNT;
  IF v_runs = 0 THEN
    INSERT INTO p3b2_invariant_checks (kind, status, n_checked, fn_version) VALUES ('sweep', 'SWEEP_OK', 0, v_ver);
    RETURN 0;
  END IF;
  SELECT min(ts), max(ts) INTO v_lo, v_hi FROM p3b2_cand;
  ANALYZE p3b2_cand;

  INSERT INTO p3b2_invariant_checks (kind, symbol, expiry_date, run_id, ts, check_id, status, n_checked, n_fail, max_abs_diff, detail, fn_version)
  WITH
  gs AS (            -- V1 stored rows (for V4 only: the gross view's inputs)
    SELECT g.symbol, g.expiry_date, g.run_id, g.strike AS k, g.spot AS s,
           coalesce(g.oi_call, 0)::numeric AS oi_call, coalesce(g.oi_put, 0)::numeric AS oi_put,
           g.gamma_call::float8 AS gamma_call, g.gamma_put::float8 AS gamma_put
    FROM gex_strike_snapshots g JOIN p3b2_cand c USING (symbol, expiry_date, run_id)
    WHERE g.ts BETWEEN v_lo AND v_hi + interval '15 minutes'),
  v2 AS (
    SELECT v.symbol, v.expiry_date, v.run_id, v.strike AS k, v.spot AS s, v.oi_call, v.oi_put,
           v.gamma_strike, v.gamma_legs, v.in_map, v.in_band, v.net_cr, v.gross_cr
    FROM gex_strike_v2 v JOIN p3b2_cand c USING (symbol, expiry_date, run_id)
    WHERE v.ts BETWEEN v_lo - interval '15 minutes' AND v_hi + interval '15 minutes'),
  vr AS (
    SELECT DISTINCT ON (r.symbol, r.expiry_date, r.run_id) r.symbol, r.expiry_date, r.run_id,
           r.net_cr, r.net_top_share, r.gross_band_cr, r.gross_top_share, r.gross_hhi, r.n_map, r.n_zero, r.n_dup_legs
    FROM gex_run_v2 r JOIN p3b2_cand c USING (symbol, expiry_date, run_id)
    WHERE r.ts BETWEEN v_lo - interval '15 minutes' AND v_hi + interval '15 minutes'
    ORDER BY r.symbol, r.expiry_date, r.run_id, r.created_at DESC),
  leg AS (
    SELECT o.symbol, o.expiry_date, o.run_id, o.strike AS k, upper(o.option_type) AS ot,
           o.gamma::float8 AS gamma, o.oi::numeric AS oi, o.spot AS s
    FROM option_chain_snapshots o JOIN p3b2_cand c USING (symbol, expiry_date, run_id)
    WHERE o.ts BETWEEN v_lo - interval '15 minutes' AND v_hi + interval '15 minutes'
      AND o.strike > 0 AND upper(o.option_type) IN ('CE', 'PE')),
  rspot AS (
    SELECT symbol, expiry_date, run_id, count(DISTINCT s) FILTER (WHERE s > 0) AS n_spot, max(s) FILTER (WHERE s > 0) AS s
    FROM leg GROUP BY symbol, expiry_date, run_id),
  lcount AS (
    SELECT symbol, expiry_date, run_id, k, ot, count(*) AS n FROM leg GROUP BY symbol, expiry_date, run_id, k, ot),
  dup AS (
    SELECT symbol, expiry_date, run_id, count(*) FILTER (WHERE n > 1) AS dup_legs FROM lcount GROUP BY symbol, expiry_date, run_id),
  lagg AS (          -- rule steps 1 and 2
    SELECT l.symbol, l.expiry_date, l.run_id, l.k,
           coalesce(sum(l.oi) FILTER (WHERE l.ot = 'CE' AND l.oi > 0), 0) AS oc,
           coalesce(sum(l.oi) FILTER (WHERE l.ot = 'PE' AND l.oi > 0), 0) AS op,
           max(l.gamma) FILTER (WHERE l.ot = 'CE' AND l.gamma > 0) AS gc,
           max(l.gamma) FILTER (WHERE l.ot = 'PE' AND l.gamma > 0) AS gp
    FROM leg l GROUP BY l.symbol, l.expiry_date, l.run_id, l.k),
  r1 AS (            -- steps 3 and 7 distances, exact numeric
    SELECT a.*, sp.s, (abs(a.k - sp.s) > 0.05 * sp.s) AS beyond
    FROM lagg a JOIN rspot sp USING (symbol, expiry_date, run_id)
    WHERE sp.n_spot = 1 AND a.oc + a.op > 0),
  r2 AS (
    SELECT r1.*,
           CASE WHEN beyond AND gc > 5e-5 THEN NULL ELSE gc END AS gc2,
           CASE WHEN beyond AND gp > 5e-5 THEN NULL ELSE gp END AS gp2
    FROM r1),
  rc AS (            -- steps 4 to 7
    SELECT symbol, expiry_date, run_id, k, s, oc, op,
           CASE WHEN gc2 IS NOT NULL AND gp2 IS NOT NULL THEN (gc2 + gp2) / 2.0 ELSE coalesce(gc2, gp2) END AS gstrike,
           CASE WHEN gc2 IS NOT NULL AND gp2 IS NOT NULL THEN 'both' WHEN gc2 IS NOT NULL THEN 'call_only' WHEN gp2 IS NOT NULL THEN 'put_only' END AS legs,
           (gc IS NOT NULL OR gp IS NOT NULL) AS in_map,
           (NOT beyond) AS in_band
    FROM r2),
  rc2 AS (
    SELECT rc.*,
           coalesce(gstrike * (oc - op)::float8 * s::float8 * s::float8 / 1e7, 0) AS net,
           coalesce(gstrike * (oc + op)::float8 * s::float8 * s::float8 / 1e7, 0) AS gross
    FROM rc),
  cmp AS (
    SELECT coalesce(a.symbol, b.symbol) AS symbol, coalesce(a.expiry_date, b.expiry_date) AS expiry_date,
           coalesce(a.run_id, b.run_id) AS run_id, coalesce(a.k, b.k) AS k,
           (a.k IS NULL OR b.k IS NULL
            OR a.in_map IS DISTINCT FROM b.in_map OR a.in_band IS DISTINCT FROM b.in_band OR a.legs IS DISTINCT FROM b.gamma_legs
            OR a.oc <> b.oi_call OR a.op <> b.oi_put
            OR (a.gstrike IS NULL) <> (b.gamma_strike IS NULL)
            OR abs(a.gstrike - b.gamma_strike) > 1e-12 * abs(b.gamma_strike)
            OR abs(a.net - b.net_cr) > 1e-6 + 1e-9 * abs(b.net_cr)
            OR abs(a.gross - b.gross_cr) > 1e-6 + 1e-9 * abs(b.gross_cr)) AS bad,
           greatest(abs(a.net - b.net_cr), abs(a.gross - b.gross_cr)) AS d,
           jsonb_build_object('k', coalesce(a.k, b.k), 'recompute_net', a.net, 'stored_net', b.net_cr,
                              'recompute_gross', a.gross, 'stored_gross', b.gross_cr,
                              'recompute_legs', a.legs, 'stored_legs', b.gamma_legs,
                              'missing', CASE WHEN a.k IS NULL THEN 'recompute' WHEN b.k IS NULL THEN 'stored' END) AS j
    FROM rc2 a FULL JOIN v2 b ON a.symbol = b.symbol AND a.expiry_date = b.expiry_date AND a.run_id = b.run_id AND a.k = b.k),
  cagg AS (
    SELECT symbol, expiry_date, run_id, count(*) AS n, count(*) FILTER (WHERE bad) AS nbad, max(d) AS d,
           to_jsonb((array_agg(j ORDER BY d DESC NULLS FIRST) FILTER (WHERE bad))[1:5]) AS worst
    FROM cmp GROUP BY symbol, expiry_date, run_id),
  v2agg AS (
    SELECT symbol, expiry_date, run_id, count(*) AS n_rows,
           coalesce(sum(net_cr) FILTER (WHERE in_map), 0) AS net,
           count(*) FILTER (WHERE in_map) AS n_map,
           count(*) FILTER (WHERE in_map AND net_cr = 0) AS n_zero,
           max(abs(net_cr)) FILTER (WHERE in_map) / nullif(sum(abs(net_cr)) FILTER (WHERE in_map), 0) AS net_top,
           coalesce(sum(gross_cr) FILTER (WHERE in_band AND gross_cr > 0), 0) AS gband,
           max(gross_cr) FILTER (WHERE in_band AND gross_cr > 0) / nullif(sum(gross_cr) FILTER (WHERE in_band AND gross_cr > 0), 0) AS gtop
    FROM v2 GROUP BY symbol, expiry_date, run_id),
  v2hhi AS (
    SELECT v.symbol, v.expiry_date, v.run_id, sum(power(v.gross_cr / a.gband, 2)) AS hhi
    FROM v2 v JOIN v2agg a USING (symbol, expiry_date, run_id)
    WHERE v.in_band AND v.gross_cr > 0 AND a.gband > 0
    GROUP BY v.symbol, v.expiry_date, v.run_id),
  vw AS (            -- the gross view's formula on stored V1 rows
    SELECT symbol, expiry_date, run_id,
           (CASE WHEN coalesce(gamma_call, 0) > 0 AND coalesce(gamma_put, 0) > 0 THEN (gamma_call + gamma_put) / 2.0
                 WHEN coalesce(gamma_call, 0) > 0 THEN gamma_call
                 WHEN coalesce(gamma_put, 0) > 0 THEN gamma_put ELSE 0 END)
           * (oi_call + oi_put)::float8 * (s::float8 ^ 2) / 1e7 AS gross
    FROM gs WHERE s > 0 AND abs(k / s - 1) <= 0.05),
  vwagg AS (
    SELECT symbol, expiry_date, run_id, max(gross) / nullif(sum(gross), 0) AS top FROM vw WHERE gross > 0
    GROUP BY symbol, expiry_date, run_id),
  run AS (
    SELECT c.symbol, c.expiry_date, c.run_id, c.ts,
           coalesce(a.n_rows, 0) AS n_v2, a.net, a.n_map, a.n_zero, a.net_top, a.gband, a.gtop, h.hhi,
           (r.run_id IS NOT NULL) AS has_run, r.net_cr, r.net_top_share, r.gross_band_cr, r.gross_top_share, r.gross_hhi,
           r.n_map AS r_n_map, r.n_zero AS r_n_zero, r.n_dup_legs,
           sp.n_spot, d.dup_legs, g.n AS n_cmp, g.nbad, g.d AS d1, g.worst, w.top AS view_top,
           (sp.run_id IS NOT NULL) AS has_chain
    FROM p3b2_cand c
    LEFT JOIN v2agg a USING (symbol, expiry_date, run_id)
    LEFT JOIN v2hhi h USING (symbol, expiry_date, run_id)
    LEFT JOIN vr r USING (symbol, expiry_date, run_id)
    LEFT JOIN rspot sp USING (symbol, expiry_date, run_id)
    LEFT JOIN dup d USING (symbol, expiry_date, run_id)
    LEFT JOIN cagg g USING (symbol, expiry_date, run_id)
    LEFT JOIN vwagg w USING (symbol, expiry_date, run_id)),
  out AS (
    SELECT symbol, expiry_date, run_id, ts, 'V0' AS check_id,
           CASE WHEN n_v2 > 0 AND has_run THEN 'OK' ELSE 'FAIL' END AS status,
           1 AS n_checked, CASE WHEN n_v2 > 0 AND has_run THEN 0 ELSE 1 END AS n_fail, NULL::float8 AS max_abs_diff,
           jsonb_build_object('v2_strike_rows', n_v2, 'v2_run_row', has_run, 'distinct_spots', n_spot) AS detail
    FROM run
    UNION ALL
    SELECT symbol, expiry_date, run_id, ts, 'V1',
           CASE WHEN n_v2 = 0 OR NOT has_chain OR n_spot <> 1 THEN 'NOT_COMPUTED' WHEN nbad > 0 THEN 'FAIL' ELSE 'OK' END,
           CASE WHEN n_v2 = 0 OR NOT has_chain OR n_spot <> 1 THEN 0 ELSE n_cmp END,
           CASE WHEN n_v2 = 0 OR NOT has_chain OR n_spot <> 1 THEN 0 ELSE nbad END, d1,
           CASE WHEN n_v2 = 0 THEN jsonb_build_object('reason', 'no V2 rows')
                WHEN NOT has_chain THEN jsonb_build_object('reason', 'no chain rows in window')
                WHEN n_spot <> 1 THEN jsonb_build_object('reason', 'run has ' || n_spot || ' distinct spots')
                ELSE jsonb_build_object('worst', worst) END
    FROM run
    UNION ALL
    SELECT symbol, expiry_date, run_id, ts, 'V2',
           CASE WHEN n_v2 = 0 OR NOT has_run THEN 'NOT_COMPUTED'
                WHEN abs(net - net_cr) > 0.01 OR n_map <> r_n_map OR n_zero <> r_n_zero THEN 'FAIL' ELSE 'OK' END,
           CASE WHEN n_v2 = 0 OR NOT has_run THEN 0 ELSE 1 END,
           CASE WHEN n_v2 > 0 AND has_run AND (abs(net - net_cr) > 0.01 OR n_map <> r_n_map OR n_zero <> r_n_zero) THEN 1 ELSE 0 END,
           abs(net - net_cr),
           jsonb_build_object('sum_net', net, 'run_net_cr', net_cr, 'n_map', n_map, 'run_n_map', r_n_map, 'n_zero', n_zero, 'run_n_zero', r_n_zero)
    FROM run
    UNION ALL
    SELECT symbol, expiry_date, run_id, ts, 'V3',
           CASE WHEN n_v2 = 0 OR NOT has_run THEN 'NOT_COMPUTED'
                WHEN (net_top IS NULL) <> (net_top_share IS NULL) OR abs(net_top - net_top_share) > 1e-9
                  OR abs(gband - gross_band_cr) > 0.01
                  OR (gtop IS NULL) <> (gross_top_share IS NULL) OR abs(gtop - gross_top_share) > 1e-9
                  OR (hhi IS NULL) <> (gross_hhi IS NULL) OR abs(hhi - gross_hhi) > 1e-9 THEN 'FAIL' ELSE 'OK' END,
           CASE WHEN n_v2 = 0 OR NOT has_run THEN 0 ELSE 1 END,
           CASE WHEN n_v2 > 0 AND has_run AND ((net_top IS NULL) <> (net_top_share IS NULL) OR abs(net_top - net_top_share) > 1e-9
                  OR abs(gband - gross_band_cr) > 0.01
                  OR (gtop IS NULL) <> (gross_top_share IS NULL) OR abs(gtop - gross_top_share) > 1e-9
                  OR (hhi IS NULL) <> (gross_hhi IS NULL) OR abs(hhi - gross_hhi) > 1e-9) THEN 1 ELSE 0 END,
           greatest(abs(net_top - net_top_share), abs(gtop - gross_top_share), abs(hhi - gross_hhi)),
           jsonb_build_object('net_top', net_top, 'run_net_top_share', net_top_share, 'gross_band', gband, 'run_gross_band_cr', gross_band_cr,
                              'gross_top', gtop, 'run_gross_top_share', gross_top_share, 'hhi', hhi, 'run_gross_hhi', gross_hhi)
    FROM run
    UNION ALL
    SELECT symbol, expiry_date, run_id, ts, 'V4',
           CASE WHEN NOT has_run THEN 'NOT_COMPUTED'
                WHEN (view_top IS NULL) <> (gross_top_share IS NULL) OR abs(view_top - gross_top_share) > 1e-9 THEN 'FAIL' ELSE 'OK' END,
           CASE WHEN has_run THEN 1 ELSE 0 END,
           CASE WHEN has_run AND ((view_top IS NULL) <> (gross_top_share IS NULL) OR abs(view_top - gross_top_share) > 1e-9) THEN 1 ELSE 0 END,
           abs(view_top - gross_top_share),
           jsonb_build_object('view_formula_rank1_share', view_top, 'run_gross_top_share', gross_top_share)
    FROM run
    UNION ALL
    SELECT symbol, expiry_date, run_id, ts, 'V5', 'INFO', 1, 0, NULL::float8,
           jsonb_build_object('chain_legs_with_more_than_one_row', dup_legs, 'run_n_dup_legs', n_dup_legs, 'distinct_spots', n_spot)
    FROM run)
  SELECT 'check', symbol, expiry_date, run_id, ts, check_id, status, n_checked, n_fail, max_abs_diff, detail, v_ver FROM out;

  INSERT INTO p3b2_invariant_checks (kind, status, n_checked, fn_version) VALUES ('sweep', 'SWEEP_OK', v_runs, v_ver);
  RETURN v_runs;
EXCEPTION WHEN OTHERS THEN
  INSERT INTO p3b2_invariant_checks (kind, status, n_checked, detail, fn_version)
  VALUES ('sweep', 'SWEEP_ERROR', v_runs, jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM), v_ver);
  RETURN -1;
END
$fn$;
REVOKE ALL ON FUNCTION public.p3b2_sweep(timestamptz, interval, interval) FROM PUBLIC, anon, authenticated;


COMMIT;
