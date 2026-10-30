-- S102 / ADR-032 D1 -- Γ sizes in ₹ Cr per 1 % move, for display. Seven thin wrapper views, additive.
-- Inventory: claude/gex_unit_inventory_S102.md v2 (§3A surfaces A1-A8; A9-A10 legacy use v_gamma_metrics_1pct and
-- v_gex_strike_snapshots_1pct if the operator rules "rescale").
--
-- Rule: every wrapper is  SELECT src.*, src.<col> * 0.01 AS <col>_1pct  -- nothing else. Stored columns, writers and the
-- source views are untouched. security_invoker = true: a wrapper grants nothing its reader did not already have (anon reads
-- every source today -- the board queries them directly).
-- NOT wrapped / NOT rescaled: v_dealer_flow_sim.flow_cr (already per-1 %) and every delta-type column (oi*S/1e7).
--
-- Operator action, SQL editor. Run BLOCK 1 as one execution. Then T1-T4, each on its own. Rollback: BLOCK R.

-- =====================================================================  BLOCK 1
CREATE VIEW public.v_gex_abs_exposure_1pct WITH (security_invoker = true) AS
SELECT v.*, v.net_gex_cr * 0.01 AS net_gex_cr_1pct, v.abs_gex_cr * 0.01 AS abs_gex_cr_1pct
FROM public.v_gex_abs_exposure v;

CREATE VIEW public.v_gex_net_gamma_river_1pct WITH (security_invoker = true) AS
SELECT v.*, v.net_gex_cr * 0.01 AS net_gex_cr_1pct,
       v.session_min_net_gex_cr * 0.01 AS session_min_net_gex_cr_1pct,
       v.session_max_net_gex_cr * 0.01 AS session_max_net_gex_cr_1pct
FROM public.v_gex_net_gamma_river v;

CREATE VIEW public.v_gex_strike_terrain_1pct WITH (security_invoker = true) AS
SELECT v.*, v.gex_cr * 0.01 AS gex_cr_1pct
FROM public.v_gex_strike_terrain v;

CREATE VIEW public.v_gex_greeks_l2_net_1pct WITH (security_invoker = true) AS
SELECT v.*, v.net_gex_drift_time_cr_per_day * 0.01 AS net_gex_drift_time_cr_per_day_1pct,
       v.net_gex_drift_iv_cr_per_volpt * 0.01 AS net_gex_drift_iv_cr_per_volpt_1pct,
       v.gross_strike_gex_drift_time * 0.01 AS gross_strike_gex_drift_time_1pct,
       v.gross_strike_gex_drift_iv * 0.01 AS gross_strike_gex_drift_iv_1pct
FROM public.v_gex_greeks_l2_net v;

CREATE VIEW public.v_gex_greeks_l2_strike_1pct WITH (security_invoker = true) AS
SELECT v.*, v.gex_drift_time_cr_per_day * 0.01 AS gex_drift_time_cr_per_day_1pct,
       v.gex_drift_iv_cr_per_volpt * 0.01 AS gex_drift_iv_cr_per_volpt_1pct
FROM public.v_gex_greeks_l2_strike v;

CREATE VIEW public.v_gex_strike_snapshots_1pct WITH (security_invoker = true) AS
SELECT t.*, t.gex_cr * 0.01 AS gex_cr_1pct
FROM public.gex_strike_snapshots t;

CREATE VIEW public.v_gamma_metrics_1pct WITH (security_invoker = true) AS
SELECT t.*, t.net_gex * 0.01 AS net_gex_1pct
FROM public.gamma_metrics t;

DO $$ DECLARE v text; BEGIN
  FOREACH v IN ARRAY ARRAY['v_gex_abs_exposure_1pct','v_gex_net_gamma_river_1pct','v_gex_strike_terrain_1pct',
                           'v_gex_greeks_l2_net_1pct','v_gex_greeks_l2_strike_1pct','v_gex_strike_snapshots_1pct',
                           'v_gamma_metrics_1pct'] LOOP
    EXECUTE format('REVOKE ALL ON public.%I FROM anon, authenticated', v);
    EXECUTE format('GRANT SELECT ON public.%I TO anon, merdian_ro', v);
    EXECUTE format($c$COMMENT ON VIEW public.%I IS %L$c$, v,
      'S102 / ADR-032 D1 -- display wrapper: every source column, plus <col>_1pct = <col> x 0.01 = Rs Cr of delta-notional '
      'per 1 % move (stored gamma exposure is gamma*OI*S^2/1e7, i.e. per 100 % move). security_invoker = true; grants '
      'nothing the reader lacks. Retired by ADR-032 D2 if ruled.');
  END LOOP;
END $$;

-- =====================================================================  T1 -- the scale, on every wrapper
-- PASS: every n_rows > 0 (the check has rows to fail on), every bad = 0, every same_as_x1 = 0 (a x1 wrapper would be caught),
-- every same_as_x01 = 0 (a x0.1 wrapper would be caught). One row per wrapper.
WITH a AS (SELECT net_gex_cr x, net_gex_cr_1pct y FROM v_gex_abs_exposure_1pct
           UNION ALL SELECT abs_gex_cr, abs_gex_cr_1pct FROM v_gex_abs_exposure_1pct),
     r AS (SELECT net_gex_cr x, net_gex_cr_1pct y FROM v_gex_net_gamma_river_1pct
           UNION ALL SELECT session_min_net_gex_cr, session_min_net_gex_cr_1pct FROM v_gex_net_gamma_river_1pct
           UNION ALL SELECT session_max_net_gex_cr, session_max_net_gex_cr_1pct FROM v_gex_net_gamma_river_1pct),
     t AS (SELECT gex_cr x, gex_cr_1pct y FROM v_gex_strike_terrain_1pct),
     n AS (SELECT net_gex_drift_time_cr_per_day x, net_gex_drift_time_cr_per_day_1pct y FROM v_gex_greeks_l2_net_1pct
           UNION ALL SELECT net_gex_drift_iv_cr_per_volpt, net_gex_drift_iv_cr_per_volpt_1pct FROM v_gex_greeks_l2_net_1pct
           UNION ALL SELECT gross_strike_gex_drift_time, gross_strike_gex_drift_time_1pct FROM v_gex_greeks_l2_net_1pct
           UNION ALL SELECT gross_strike_gex_drift_iv, gross_strike_gex_drift_iv_1pct FROM v_gex_greeks_l2_net_1pct),
     s AS (SELECT gex_drift_time_cr_per_day x, gex_drift_time_cr_per_day_1pct y FROM v_gex_greeks_l2_strike_1pct
           UNION ALL SELECT gex_drift_iv_cr_per_volpt, gex_drift_iv_cr_per_volpt_1pct FROM v_gex_greeks_l2_strike_1pct),
     g AS (SELECT gex_cr x, gex_cr_1pct y FROM v_gex_strike_snapshots_1pct
           WHERE ts >= (SELECT max(ts) FROM gex_strike_snapshots) - interval '10 minutes'),
     m AS (SELECT net_gex x, net_gex_1pct y FROM v_gamma_metrics_1pct WHERE ts >= now() - interval '7 days'),
     u AS (SELECT 'abs_exposure' w, * FROM a UNION ALL SELECT 'river', * FROM r UNION ALL SELECT 'terrain', * FROM t
           UNION ALL SELECT 'l2_net', * FROM n UNION ALL SELECT 'l2_strike', * FROM s
           UNION ALL SELECT 'strike_snapshots', * FROM g UNION ALL SELECT 'gamma_metrics', * FROM m)
SELECT w, count(*) FILTER (WHERE x IS NOT NULL AND x <> 0) AS n_rows,
       count(*) FILTER (WHERE x IS NOT NULL AND abs(y - 0.01 * x) > 1e-9 * abs(x)) AS bad,
       count(*) FILTER (WHERE x IS NOT NULL AND x <> 0 AND abs(y - x) <= 1e-9 * abs(x)) AS same_as_x1,
       count(*) FILTER (WHERE x IS NOT NULL AND x <> 0 AND abs(y - 0.1 * x) <= 1e-9 * abs(x)) AS same_as_x01,
       count(*) FILTER (WHERE (x IS NULL) <> (y IS NULL)) AS null_mismatch
FROM u GROUP BY w ORDER BY w;

-- =====================================================================  T2 -- an independent path: the board's Net Γ per 1 %
-- equals the dealer-flow view's own +1 % hedge, sign-flipped (flow_cr = -net_gex x pct, rounded to 2 dp). This checks the
-- rescale (wrapper arithmetic vs the flow view's pct arithmetic), NOT the gamma formula -- both read gamma_metrics.net_gex.
-- gamma_metrics may carry more than one row per (symbol, run_id) (the board dedupes by ts), so the newest row per
-- (symbol, run_id) is taken; n_gm_rows reports how many there were.
-- PASS: exactly one row per symbol, abs_diff <= 0.01 (flow_cr is rounded to 2 dp).
WITH f AS (SELECT symbol, run_id, flow_cr FROM v_dealer_flow_sim WHERE abs(spot_pct - 0.01) < 1e-9),
     m AS (SELECT DISTINCT ON (g.symbol, g.run_id) g.symbol, g.run_id, g.net_gex_1pct,
                  count(*) OVER (PARTITION BY g.symbol, g.run_id) AS n_gm_rows
             FROM v_gamma_metrics_1pct g JOIN f USING (symbol, run_id)
            ORDER BY g.symbol, g.run_id, g.ts DESC)
SELECT f.symbol, m.n_gm_rows, m.net_gex_1pct, -f.flow_cr AS minus_flow_cr_at_plus_1pct,
       round(abs(m.net_gex_1pct + f.flow_cr)::numeric, 4) AS abs_diff
FROM f JOIN m USING (symbol, run_id)
ORDER BY f.symbol;

-- =====================================================================  T3 -- WIRING ONLY: the Board's two Net Γ sources agree
-- per 1 % (strip / Overview read v_gex_abs_exposure; Net Γ today reads gamma_metrics). NOT an independent check -- both are sums
-- of signed_gamma_exposure() on the same run, so this passes by construction (S79 COMMENT on v_gex_abs_exposure); it fails only
-- if a wrapper is wired to the wrong column or run. Absolute tolerance as well as relative, so a net near zero does not trip it.
-- PASS: exactly one row per symbol, ok = true.
WITH m AS (SELECT DISTINCT ON (symbol, run_id) symbol, run_id, net_gex_1pct
             FROM v_gamma_metrics_1pct
            WHERE run_id IN (SELECT run_id FROM v_gex_abs_exposure_1pct)
            ORDER BY symbol, run_id, ts DESC)
SELECT a.symbol, a.run_id, a.net_gex_cr_1pct, m.net_gex_1pct,
       abs(a.net_gex_cr_1pct - m.net_gex_1pct) <= greatest(0.01, 1e-6 * abs(m.net_gex_1pct)) AS ok
FROM v_gex_abs_exposure_1pct a JOIN m USING (symbol, run_id)
ORDER BY a.symbol;

-- =====================================================================  T4 -- privileges and invoker setting
-- PASS: 7 rows; anon_sel t, anon_ins f, auth_sel f, ro_sel t, invoker t, has_comment t.
SELECT c.relname,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_sel,
       has_table_privilege('anon', c.oid, 'INSERT') AS anon_ins,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS auth_sel,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_sel,
       coalesce('security_invoker=true' = ANY (c.reloptions), false) AS invoker,
       obj_description(c.oid, 'pg_class') IS NOT NULL AS has_comment
FROM pg_class c JOIN pg_namespace s ON s.oid = c.relnamespace
WHERE s.nspname = 'public' AND c.relname LIKE '%\_1pct' ESCAPE '\' AND c.relkind = 'v'
ORDER BY c.relname;

-- =====================================================================  T5 -- the board's own role reads every wrapper
-- T1-T4 run as postgres and bypass RLS; a view anon cannot read returns HTTP 200 with zero rows (TD-S81-NEW-5, TD-S37-03).
-- ONE execution (the editor opens a new session per run, S84 §D.40.1), role selected beside the result.
-- PASS: role_now = anon; all seven true. Control: the same SELECT without the SET LOCAL line returns role_now = postgres.
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now,
       EXISTS (SELECT 1 FROM v_gex_abs_exposure_1pct)      AS abs_exposure,
       EXISTS (SELECT 1 FROM v_gex_net_gamma_river_1pct)   AS river,
       EXISTS (SELECT 1 FROM v_gex_strike_terrain_1pct)    AS terrain,
       EXISTS (SELECT 1 FROM v_gex_greeks_l2_net_1pct)     AS l2_net,
       EXISTS (SELECT 1 FROM v_gex_greeks_l2_strike_1pct)  AS l2_strike,
       EXISTS (SELECT 1 FROM v_gex_strike_snapshots_1pct)  AS strike_snapshots,
       EXISTS (SELECT 1 FROM v_gamma_metrics_1pct)         AS gamma_metrics;
COMMIT;

-- Dependency: these wrappers depend on their sources. DROP VIEW of a source now errors (use CREATE OR REPLACE, which may only
-- append columns, or drop the wrapper first and re-create it after). Recorded in ADR-032 D1.

-- =====================================================================  BLOCK R -- rollback (nothing reads these until the board round)
-- DROP VIEW public.v_gex_abs_exposure_1pct, public.v_gex_net_gamma_river_1pct, public.v_gex_strike_terrain_1pct,
--           public.v_gex_greeks_l2_net_1pct, public.v_gex_greeks_l2_strike_1pct, public.v_gex_strike_snapshots_1pct,
--           public.v_gamma_metrics_1pct;
