-- TD-S103-NEW-9 (ADR-032 D1 dependency rule: append-only). v_gex_greeks_l2_strike_1pct converted only 2 of its 4 Γ columns;
-- append gross_gex_drift_iv_1pct and gross_gex_drift_time_1pct (x 0.01). Columns 1-22 are unchanged, same names, same order.
-- Live viewdef read 2026-11-01 11:45 IST (22 columns; 20 source columns + the two _1pct). Source: public.v_gex_greeks_l2_strike.
-- Operator action, SQL editor. STEP A (alone), STEP B (one execution), STEP C = T1 (alone), STEP D (alone).
-- Rollback (only if needed; the extra columns are harmless): DROP VIEW public.v_gex_greeks_l2_strike_1pct; then re-create the
-- 22-column original from sql/2026-10-30_s102_gex_per_1pct_views.sql and re-grant to the roles STEP A showed in relacl.

-- ===================================================================== STEP A -- before (note relacl and reloptions)
SELECT relacl::text AS relacl, reloptions::text AS reloptions
FROM pg_class WHERE oid = 'public.v_gex_greeks_l2_strike_1pct'::regclass;

-- ===================================================================== STEP B -- fail-closed, then replace
DO $$
DECLARE live text; expected text := 'symbol,ts,expiry_date,dte,spot,strike,is_trading_session,t_days,r_sess,n_r_rows,n_legs,'
  'delta_drift_iv_cr_per_volpt,delta_drift_time_cr_per_day,gex_drift_iv_cr_per_volpt,gex_drift_time_cr_per_day,'
  'gross_delta_drift_iv,gross_delta_drift_time,gross_gex_drift_iv,gross_gex_drift_time,status,'
  'gex_drift_time_cr_per_day_1pct,gex_drift_iv_cr_per_volpt_1pct';
BEGIN
  SELECT string_agg(column_name, ',' ORDER BY ordinal_position) INTO live
  FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'v_gex_greeks_l2_strike_1pct';
  IF live IS DISTINCT FROM expected THEN
    RAISE EXCEPTION 'ABORT: live columns differ from the 22 read at 11:45 IST: %', live;
  END IF;
END $$;

CREATE OR REPLACE VIEW public.v_gex_greeks_l2_strike_1pct WITH (security_invoker = true) AS
SELECT v.symbol, v.ts, v.expiry_date, v.dte, v.spot, v.strike, v.is_trading_session, v.t_days, v.r_sess, v.n_r_rows, v.n_legs,
       v.delta_drift_iv_cr_per_volpt, v.delta_drift_time_cr_per_day, v.gex_drift_iv_cr_per_volpt, v.gex_drift_time_cr_per_day,
       v.gross_delta_drift_iv, v.gross_delta_drift_time, v.gross_gex_drift_iv, v.gross_gex_drift_time, v.status,
       v.gex_drift_time_cr_per_day * 0.01::double precision AS gex_drift_time_cr_per_day_1pct,
       v.gex_drift_iv_cr_per_volpt * 0.01::double precision AS gex_drift_iv_cr_per_volpt_1pct,
       v.gross_gex_drift_iv * 0.01::double precision AS gross_gex_drift_iv_1pct,
       v.gross_gex_drift_time * 0.01::double precision AS gross_gex_drift_time_1pct
FROM public.v_gex_greeks_l2_strike v;

-- ===================================================================== STEP C -- T1 for the new pair
-- PASS: n_rows > 0, bad = 0, same_as_x1 = 0, same_as_x01 = 0, null_mismatch = 0 for both rows.
WITH u AS (SELECT 'gross_gex_drift_iv' w, gross_gex_drift_iv x, gross_gex_drift_iv_1pct y FROM public.v_gex_greeks_l2_strike_1pct
           UNION ALL SELECT 'gross_gex_drift_time', gross_gex_drift_time, gross_gex_drift_time_1pct FROM public.v_gex_greeks_l2_strike_1pct)
SELECT w, count(*) FILTER (WHERE x IS NOT NULL AND x <> 0) AS n_rows,
       count(*) FILTER (WHERE x IS NOT NULL AND abs(y - 0.01 * x) > 1e-9 * abs(x)) AS bad,
       count(*) FILTER (WHERE x IS NOT NULL AND x <> 0 AND abs(y - x) <= 1e-9 * abs(x)) AS same_as_x1,
       count(*) FILTER (WHERE x IS NOT NULL AND x <> 0 AND abs(y - 0.1 * x) <= 1e-9 * abs(x)) AS same_as_x01,
       count(*) FILTER (WHERE (x IS NULL) <> (y IS NULL)) AS null_mismatch
FROM u GROUP BY w ORDER BY w;

-- ===================================================================== STEP D -- after (relacl and reloptions must equal STEP A)
SELECT relacl::text AS relacl, reloptions::text AS reloptions,
       (SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'v_gex_greeks_l2_strike_1pct') AS n_cols
FROM pg_class WHERE oid = 'public.v_gex_greeks_l2_strike_1pct'::regclass;
