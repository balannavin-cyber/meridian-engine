-- ADR-032 F0 / K2 -- definitions snapshot of every Gamma object, taken BEFORE any D2-D4 change.
-- Source: operator read in the Supabase SQL editor, 2026-10-31 ~08:35 IST (pg_get_viewdef / pg_get_functiondef,
-- reloptions, relacl/proacl). Engine commit at the time: c11b564 (tag adr032-pre). Board live: 6f14a92.
-- USE: restoring an object = run its block. PROOF of restore: md5(pg_get_viewdef(oid)) / md5(prosrc) equals the
-- value on that block's 'md5' line (= study section 4, claude/adr032_s5_s6_impact_study_S103.md).
-- Views: CREATE OR REPLACE works only while the column list is unchanged or only appended to; if a later stage added
-- a column, DROP VIEW + CREATE VIEW in one BEGIN..COMMIT instead (two _1pct wrappers are SELECT t.* over tables).
-- Grants shown are SELECT only; the full relacl is in each block's comment (service_role and postgres hold all privileges).
-- Table column lists at the time are in the F0 record (claude/adr032_f0_k1_k3_records_2026-10-31.md source: information_schema read 08:3x IST).

-- ===== view: public.v_close_print | md5 92a4eac45d64017649504a05913f12d9 | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_close_print AS
 SELECT symbol,
    ts,
    spot,
    source_table,
        CASE
            WHEN (source_table = 'dhan_idx_i'::text) THEN 1
            ELSE 2
        END AS close_rank
   FROM market_spot_snapshots m
  WHERE (((source_table = 'dhan_idx_i'::text) AND (((ts AT TIME ZONE 'Asia/Kolkata'::text))::time without time zone >= '16:00:00'::time without time zone) AND (((ts AT TIME ZONE 'Asia/Kolkata'::text))::time without time zone < '16:10:00'::time without time zone)) OR ((source_table = 'dhan_charts_historical'::text) AND (((ts AT TIME ZONE 'Asia/Kolkata'::text))::time without time zone >= '15:29:00'::time without time zone) AND (((ts AT TIME ZONE 'Asia/Kolkata'::text))::time without time zone < '15:31:00'::time without time zone)));
ALTER VIEW public.v_close_print SET (security_invoker=true);
GRANT SELECT ON public.v_close_print TO anon;
GRANT SELECT ON public.v_close_print TO merdian_ro;

-- ===== view: public.v_dealer_flow_sim | md5 166948d6c7429d5c8765bf48c8f58d3d | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_dealer_flow_sim AS
 WITH scenarios AS (
         SELECT s_1.pct,
            s_1.label
           FROM ( VALUES ((- 0.02),'-2.0%'::text), ('-0.01'::numeric,'-1.0%'::text), ('-0.005'::numeric,'-0.5%'::text), (0.005,'+0.5%'::text), (0.01,'+1.0%'::text), (0.02,'+2.0%'::text)) s_1(pct, label)
        ), latest_per_symbol AS (
         SELECT DISTINCT ON (gex_strike_snapshots.symbol) gex_strike_snapshots.run_id,
            gex_strike_snapshots.symbol,
            gex_strike_snapshots.expiry_date,
            gex_strike_snapshots.ts,
            gex_strike_snapshots.spot
           FROM gex_strike_snapshots
          ORDER BY gex_strike_snapshots.symbol, gex_strike_snapshots.ts DESC
        ), ctx AS (
         SELECT l.symbol,
            l.run_id,
            l.expiry_date,
            l.ts,
            l.spot,
            gm.net_gex,
            gm.flip_level
           FROM (latest_per_symbol l
             JOIN gamma_metrics gm ON (((gm.run_id = l.run_id) AND (gm.symbol = l.symbol))))
        )
 SELECT c.run_id,
    c.symbol,
    c.expiry_date,
    c.ts,
    s.label AS scenario,
    s.pct AS spot_pct,
    round((c.spot * ((1)::numeric + s.pct)), 2) AS perturbed_spot,
    c.net_gex,
    round(((- c.net_gex) * s.pct), 2) AS flow_cr,
        CASE
            WHEN (((- c.net_gex) * s.pct) < (0)::numeric) THEN 'SELL'::text
            ELSE 'BUY'::text
        END AS direction,
        CASE
            WHEN (c.flip_level IS NULL) THEN false
            WHEN ((s.pct < (0)::numeric) AND (c.spot > c.flip_level) AND ((c.spot * ((1)::numeric + s.pct)) <= c.flip_level)) THEN true
            WHEN ((s.pct > (0)::numeric) AND (c.spot < c.flip_level) AND ((c.spot * ((1)::numeric + s.pct)) >= c.flip_level)) THEN true
            ELSE false
        END AS crosses_flip
   FROM (ctx c
     CROSS JOIN scenarios s)
  ORDER BY c.symbol, s.pct;
GRANT SELECT ON public.v_dealer_flow_sim TO authenticated;
GRANT SELECT ON public.v_dealer_flow_sim TO anon;
GRANT SELECT ON public.v_dealer_flow_sim TO merdian_ro;

-- ===== view: public.v_gamma_metrics_1pct | md5 ed2e9a53c32a683ecf60f5dd8d27a359 | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gamma_metrics_1pct AS
 SELECT id,
    ts,
    symbol,
    expiry_date,
    spot,
    net_gex,
    gamma_concentration,
    flip_level,
    flip_distance,
    straddle_atm,
    straddle_slope,
    vix,
    breadth_regime,
    expansion_probability,
    regime,
    created_at,
    run_id,
    flip_distance_pct,
    gamma_zone,
    raw,
    straddle_velocity,
    otm_oi_velocity,
    spot_vs_range,
    run_type,
    dte,
    max_gamma_strike,
    pin_risk_score,
    (net_gex * 0.01) AS net_gex_1pct
   FROM gamma_metrics t;
ALTER VIEW public.v_gamma_metrics_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gamma_metrics_1pct TO anon;
GRANT SELECT ON public.v_gamma_metrics_1pct TO merdian_ro;

-- ===== view: public.v_gex_abs_exposure | md5 3ae144c73e4191f4c906709aa7b5d5a0 | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_abs_exposure AS
 WITH RECURSIVE symbols AS (
         SELECT ( SELECT min(g.symbol) AS min
                   FROM gex_strike_snapshots g) AS symbol
        UNION ALL
         SELECT ( SELECT min(g.symbol) AS min
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol > s.symbol)) AS min
           FROM symbols s
          WHERE (s.symbol IS NOT NULL)
        ), latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM (symbols s
             CROSS JOIN LATERAL ( SELECT g.run_id,
                    g.ts
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol = s.symbol)
                  ORDER BY g.ts DESC
                 LIMIT 1) lr)
          WHERE (s.symbol IS NOT NULL)
        ), scoped AS (
         SELECT g.run_id,
            g.symbol,
            g.ts,
            g.expiry_date,
            g.dte,
            g.spot,
            g.gex_cr
           FROM (gex_strike_snapshots g
             JOIN latest_run lr ON (((g.symbol = lr.symbol) AND (g.run_id = lr.run_id))))
        )
 SELECT run_id,
    symbol,
    expiry_date,
    max(ts) AS ts,
    max(dte) AS dte,
    max(spot) AS spot,
    sum(gex_cr) AS net_gex_cr,
    sum(abs(gex_cr)) AS abs_gex_cr,
    count(*) AS n_strikes,
    count(*) FILTER (WHERE (gex_cr <> (0)::numeric)) AS n_contributing
   FROM scoped
  GROUP BY run_id, symbol, expiry_date;
GRANT SELECT ON public.v_gex_abs_exposure TO authenticated;
GRANT SELECT ON public.v_gex_abs_exposure TO anon;
GRANT SELECT ON public.v_gex_abs_exposure TO merdian_ro;

-- ===== view: public.v_gex_abs_exposure_1pct | md5 c0c59ecf0921f50ee245311bb8abe966 | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_abs_exposure_1pct AS
 SELECT run_id,
    symbol,
    expiry_date,
    ts,
    dte,
    spot,
    net_gex_cr,
    abs_gex_cr,
    n_strikes,
    n_contributing,
    (net_gex_cr * 0.01) AS net_gex_cr_1pct,
    (abs_gex_cr * 0.01) AS abs_gex_cr_1pct
   FROM v_gex_abs_exposure v;
ALTER VIEW public.v_gex_abs_exposure_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gex_abs_exposure_1pct TO anon;
GRANT SELECT ON public.v_gex_abs_exposure_1pct TO merdian_ro;

-- ===== view: public.v_gex_concentration | md5 5c075092325391d869b3397bcdca832a | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_concentration AS
 WITH RECURSIVE symbols AS (
         SELECT ( SELECT min(g.symbol) AS min
                   FROM gex_strike_snapshots g) AS symbol
        UNION ALL
         SELECT ( SELECT min(g.symbol) AS min
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol > s.symbol)) AS min
           FROM symbols s
          WHERE (s.symbol IS NOT NULL)
        ), latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM (symbols s
             CROSS JOIN LATERAL ( SELECT g.run_id,
                    g.ts
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol = s.symbol)
                  ORDER BY g.ts DESC
                 LIMIT 1) lr)
          WHERE (s.symbol IS NOT NULL)
        ), scoped AS (
         SELECT g.run_id,
            g.symbol,
            g.ts,
            g.expiry_date,
            g.dte,
            g.spot,
            g.strike,
            g.gex_cr,
            abs((g.gamma_call * (g.oi_call)::double precision)) AS leg_call,
            abs((g.gamma_put * (g.oi_put)::double precision)) AS leg_put
           FROM (gex_strike_snapshots g
             JOIN latest_run lr ON (((g.symbol = lr.symbol) AND (g.run_id = lr.run_id))))
        )
 SELECT run_id,
    symbol,
    expiry_date,
    max(ts) AS ts,
    max(dte) AS dte,
    max(spot) AS spot,
        CASE
            WHEN (max(dte) IS NULL) THEN NULL::text
            WHEN (max(dte) < 0) THEN NULL::text
            WHEN (max(dte) = 0) THEN '0'::text
            WHEN (max(dte) <= 2) THEN '1-2'::text
            ELSE '3+'::text
        END AS dte_bucket,
    (max(abs(gex_cr)) / NULLIF(sum(abs(gex_cr)), (0)::numeric)) AS hhi_net,
    (max(leg_call) / NULLIF(sum(leg_call), (0)::double precision)) AS hhi_call,
    (max(leg_put) / NULLIF(sum(leg_put), (0)::double precision)) AS hhi_put,
        CASE
            WHEN (max(abs(gex_cr)) > (0)::numeric) THEN (array_agg(strike ORDER BY (abs(gex_cr)) DESC, strike))[1]
            ELSE NULL::numeric
        END AS top_strike_net,
    count(*) AS n_strikes,
    count(*) FILTER (WHERE (gex_cr <> (0)::numeric)) AS n_contributing
   FROM scoped
  GROUP BY run_id, symbol, expiry_date;
GRANT SELECT ON public.v_gex_concentration TO authenticated;
GRANT SELECT ON public.v_gex_concentration TO anon;
GRANT SELECT ON public.v_gex_concentration TO merdian_ro;

-- ===== view: public.v_gex_greeks_l2_leg | md5 e66be9f4aee80c6e981ba1774f6d0228 | options: security_invoker=false
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_greeks_l2_leg AS
 WITH RECURSIVE symbols AS (
         SELECT ( SELECT min(o.symbol) AS min
                   FROM option_chain_snapshots o) AS symbol
        UNION ALL
         SELECT ( SELECT min(o.symbol) AS min
                   FROM option_chain_snapshots o
                  WHERE (o.symbol > s.symbol)) AS min
           FROM symbols s
          WHERE (s.symbol IS NOT NULL)
        ), latest AS (
         SELECT s.symbol,
            lt.ts AS latest_ts
           FROM (symbols s
             CROSS JOIN LATERAL ( SELECT o.ts
                   FROM option_chain_snapshots o
                  WHERE (o.symbol = s.symbol)
                  ORDER BY o.ts DESC
                 LIMIT 1) lt)
          WHERE (s.symbol IS NOT NULL)
        ), scoped AS (
         SELECT l.symbol,
            l.latest_ts AS ts,
            o.expiry_date,
            o.strike,
            o.option_type,
            o.iv,
            o.oi,
            o.gamma,
            o.spot
           FROM (latest l
             JOIN option_chain_snapshots o ON (((o.symbol = l.symbol) AND (o.ts = l.latest_ts))))
        ), hdr AS (
         SELECT s.symbol,
            s.ts,
            s.expiry_date,
            max(s.spot) AS spot,
            (s.expiry_date - ((s.ts AT TIME ZONE 'Asia/Kolkata'::text))::date) AS dte,
            ((EXTRACT(epoch FROM (((s.expiry_date + '15:30:00'::time without time zone) AT TIME ZONE 'Asia/Kolkata'::text) - s.ts)) / (365.0 * 86400.0)))::double precision AS t_years
           FROM scoped s
          GROUP BY s.symbol, s.ts, s.expiry_date
        ), gate AS MATERIALIZED (
         SELECT h.symbol,
            h.ts,
            ( SELECT (count(DISTINCT o2.spot) > 1)
                   FROM option_chain_snapshots o2
                  WHERE ((o2.symbol = h.symbol) AND (o2.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata'::text))::date)::timestamp without time zone AT TIME ZONE 'Asia/Kolkata'::text)) AND (o2.ts <= h.ts))) AS is_trading_session
           FROM ( SELECT DISTINCT hdr.symbol,
                    hdr.ts
                   FROM hdr) h
        ), futwin AS (
         SELECT DISTINCT h.symbol,
            h.ts,
            i.ts AS fut_ts,
            i.expiry_date,
            i.futures_price,
            i.spot_price
           FROM (( SELECT DISTINCT hdr.symbol,
                    hdr.ts
                   FROM hdr) h
             JOIN index_futures_snapshots i ON (((i.symbol = h.symbol) AND (i.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata'::text))::date + '09:20:00'::time without time zone) AT TIME ZONE 'Asia/Kolkata'::text)) AND (i.ts <= h.ts))))
          WHERE ((i.futures_price > (0)::numeric) AND (i.spot_price > (0)::numeric))
        ), futfront AS (
         SELECT futwin.symbol,
            futwin.ts,
            min(futwin.expiry_date) AS fut_expiry
           FROM futwin
          WHERE (futwin.expiry_date >= ((futwin.ts AT TIME ZONE 'Asia/Kolkata'::text))::date)
          GROUP BY futwin.symbol, futwin.ts
        ), rrows AS (
         SELECT w.symbol,
            w.ts,
            ((ln((w.futures_price / w.spot_price)) / (EXTRACT(epoch FROM (((w.expiry_date + '15:30:00'::time without time zone) AT TIME ZONE 'Asia/Kolkata'::text) - w.fut_ts)) / (365.0 * 86400.0))))::double precision AS r_fut
           FROM (futwin w
             JOIN futfront f ON (((f.symbol = w.symbol) AND (f.ts = w.ts) AND (f.fut_expiry = w.expiry_date))))
          WHERE (w.fut_ts < ((w.expiry_date + '15:30:00'::time without time zone) AT TIME ZONE 'Asia/Kolkata'::text))
        ), rstats AS (
         SELECT rrows.symbol,
            rrows.ts,
            (count(*))::integer AS n_r_rows,
            percentile_cont((0.50)::double precision) WITHIN GROUP (ORDER BY rrows.r_fut) AS r_sess
           FROM rrows
          GROUP BY rrows.symbol, rrows.ts
        ), hx AS MATERIALIZED (
         SELECT h.symbol,
            h.ts,
            h.expiry_date,
            h.spot,
            h.dte,
            h.t_years,
            r.r_sess,
            COALESCE(r.n_r_rows, 0) AS n_r_rows,
            g.is_trading_session
           FROM ((hdr h
             LEFT JOIN rstats r ON (((r.symbol = h.symbol) AND (r.ts = h.ts))))
             LEFT JOIN gate g ON (((g.symbol = h.symbol) AND (g.ts = h.ts))))
        ), leg AS (
         SELECT s.symbol,
            s.ts,
            s.expiry_date,
            s.strike,
            s.option_type,
            x.spot,
            x.dte,
            x.t_years,
            x.r_sess,
            x.n_r_rows,
            x.is_trading_session,
            s.oi AS oi_qty,
            s.iv,
            s.gamma,
            (s.strike)::double precision AS k,
                CASE
                    WHEN (s.option_type = 'PE'::text) THEN '-1.0'::numeric
                    ELSE 1.0
                END AS sgn,
            ((s.iv / 100.0))::double precision AS sigma,
            (s.oi)::double precision AS oi,
            COALESCE(((s.oi > (0)::numeric) AND (s.gamma IS NOT NULL) AND (s.gamma <> (0)::numeric) AND (s.iv > (0)::numeric) AND (NOT (((abs((s.strike - x.spot)) / x.spot) > 0.05) AND (abs(s.gamma) > 0.00005)))), false) AS in_leg_set,
            COALESCE(((s.gamma IS NOT NULL) AND (s.gamma <> (0)::numeric) AND (s.iv > (0)::numeric) AND (NOT (((abs((s.strike - x.spot)) / x.spot) > 0.05) AND (abs(s.gamma) > 0.00005)))), false) AS priceable,
            COALESCE(((x.dte > 0) AND (x.t_years > (0)::double precision) AND (x.n_r_rows >= 6) AND (x.r_sess IS NOT NULL)), false) AS evaluable
           FROM (scoped s
             JOIN hx x ON (((x.symbol = s.symbol) AND (x.ts = s.ts) AND (x.expiry_date = s.expiry_date))))
        ), bs AS (
         SELECT b_1.symbol,
            b_1.ts,
            b_1.expiry_date,
            b_1.strike,
            b_1.option_type,
            b_1.spot,
            b_1.dte,
            b_1.t_years,
            b_1.r_sess,
            b_1.n_r_rows,
            b_1.is_trading_session,
            b_1.oi_qty,
            b_1.iv,
            b_1.gamma,
            b_1.k,
            b_1.sgn,
            b_1.sigma,
            b_1.oi,
            b_1.in_leg_set,
            b_1.priceable,
            b_1.evaluable,
                CASE
                    WHEN (b_1.priceable AND b_1.evaluable) THEN ((ln(((b_1.spot)::double precision / b_1.k)) + ((b_1.r_sess + ((0.5)::double precision * power(b_1.sigma, (2)::double precision))) * b_1.t_years)) / (b_1.sigma * sqrt(b_1.t_years)))
                    ELSE NULL::double precision
                END AS d1
           FROM leg b_1
        ), bs2 AS (
         SELECT b_1.symbol,
            b_1.ts,
            b_1.expiry_date,
            b_1.strike,
            b_1.option_type,
            b_1.spot,
            b_1.dte,
            b_1.t_years,
            b_1.r_sess,
            b_1.n_r_rows,
            b_1.is_trading_session,
            b_1.oi_qty,
            b_1.iv,
            b_1.gamma,
            b_1.k,
            b_1.sgn,
            b_1.sigma,
            b_1.oi,
            b_1.in_leg_set,
            b_1.priceable,
            b_1.evaluable,
            b_1.d1,
                CASE
                    WHEN (b_1.priceable AND b_1.evaluable) THEN (b_1.d1 - (b_1.sigma * sqrt(b_1.t_years)))
                    ELSE NULL::double precision
                END AS d2,
                CASE
                    WHEN (b_1.priceable AND b_1.evaluable) THEN (exp((('-0.5'::numeric)::double precision * power(b_1.d1, (2)::double precision))) / sqrt(((2.0)::double precision * pi())))
                    ELSE NULL::double precision
                END AS nd1,
                CASE
                    WHEN (b_1.priceable AND b_1.evaluable) THEN (((b_1.r_sess + ((0.5)::double precision * power(b_1.sigma, (2)::double precision))) / (b_1.sigma * sqrt(b_1.t_years))) - (b_1.d1 / ((2.0)::double precision * b_1.t_years)))
                    ELSE NULL::double precision
                END AS dd1_dt
           FROM bs b_1
        ), bs3 AS (
         SELECT b_1.symbol,
            b_1.ts,
            b_1.expiry_date,
            b_1.strike,
            b_1.option_type,
            b_1.spot,
            b_1.dte,
            b_1.t_years,
            b_1.r_sess,
            b_1.n_r_rows,
            b_1.is_trading_session,
            b_1.oi_qty,
            b_1.iv,
            b_1.gamma,
            b_1.k,
            b_1.sgn,
            b_1.sigma,
            b_1.oi,
            b_1.in_leg_set,
            b_1.priceable,
            b_1.evaluable,
            b_1.d1,
            b_1.d2,
            b_1.nd1,
            b_1.dd1_dt,
                CASE
                    WHEN (b_1.priceable AND b_1.evaluable) THEN (b_1.nd1 / (((b_1.spot)::double precision * b_1.sigma) * sqrt(b_1.t_years)))
                    ELSE NULL::double precision
                END AS bs_gamma
           FROM bs2 b_1
        )
 SELECT symbol,
    ts,
    expiry_date,
    strike,
    option_type,
    spot,
    dte,
    t_years,
    r_sess,
    n_r_rows,
    is_trading_session,
    oi_qty,
    iv,
    gamma,
    k,
    sgn,
    sigma,
    oi,
    in_leg_set,
    priceable,
    evaluable,
    d1,
    d2,
        CASE
            WHEN (priceable AND evaluable) THEN ((((- nd1) * d2) / sigma) / (100.0)::double precision)
            ELSE NULL::double precision
        END AS u_delta_drift_iv,
        CASE
            WHEN (priceable AND evaluable) THEN (((- nd1) * dd1_dt) / (365.0)::double precision)
            ELSE NULL::double precision
        END AS u_delta_drift_time,
        CASE
            WHEN (priceable AND evaluable) THEN (((bs_gamma * ((d1 * d2) - (1.0)::double precision)) / sigma) / (100.0)::double precision)
            ELSE NULL::double precision
        END AS u_gex_drift_iv,
        CASE
            WHEN (priceable AND evaluable) THEN ((bs_gamma * ((d1 * dd1_dt) + ((1.0)::double precision / ((2.0)::double precision * t_years)))) / (365.0)::double precision)
            ELSE NULL::double precision
        END AS u_gex_drift_time
   FROM bs3 b;
ALTER VIEW public.v_gex_greeks_l2_leg SET (security_invoker=false);
GRANT SELECT ON public.v_gex_greeks_l2_leg TO merdian_ro;

-- ===== view: public.v_gex_greeks_l2_net | md5 dd74b2b79d6ed46fd259e8e55059697f | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_greeks_l2_net AS
 SELECT symbol,
    ts,
    expiry_date,
    max(dte) AS dte,
    max(spot) AS spot,
    bool_and(is_trading_session) AS is_trading_session,
    max(t_days) AS t_days,
    max(r_sess) AS r_sess,
    max(n_r_rows) AS n_r_rows,
    (count(strike))::integer AS n_strikes,
    (COALESCE(sum(n_legs), (0)::bigint))::integer AS n_legs,
    sum(delta_drift_iv_cr_per_volpt) AS net_delta_drift_iv_cr_per_volpt,
    sum(delta_drift_time_cr_per_day) AS net_delta_drift_time_cr_per_day,
    sum(gex_drift_iv_cr_per_volpt) AS net_gex_drift_iv_cr_per_volpt,
    sum(gex_drift_time_cr_per_day) AS net_gex_drift_time_cr_per_day,
    sum(abs(delta_drift_iv_cr_per_volpt)) AS gross_strike_delta_drift_iv,
    sum(abs(delta_drift_time_cr_per_day)) AS gross_strike_delta_drift_time,
    sum(abs(gex_drift_iv_cr_per_volpt)) AS gross_strike_gex_drift_iv,
    sum(abs(gex_drift_time_cr_per_day)) AS gross_strike_gex_drift_time,
    (sum(delta_drift_iv_cr_per_volpt) / NULLIF(sum(abs(delta_drift_iv_cr_per_volpt)), (0)::double precision)) AS net_over_gross_delta_drift_iv,
    (sum(delta_drift_time_cr_per_day) / NULLIF(sum(abs(delta_drift_time_cr_per_day)), (0)::double precision)) AS net_over_gross_delta_drift_time,
    (sum(gex_drift_iv_cr_per_volpt) / NULLIF(sum(abs(gex_drift_iv_cr_per_volpt)), (0)::double precision)) AS net_over_gross_gex_drift_iv,
    (sum(gex_drift_time_cr_per_day) / NULLIF(sum(abs(gex_drift_time_cr_per_day)), (0)::double precision)) AS net_over_gross_gex_drift_time,
    max(status) AS status
   FROM v_gex_greeks_l2_strike s
  GROUP BY symbol, ts, expiry_date;
GRANT SELECT ON public.v_gex_greeks_l2_net TO authenticated;
GRANT SELECT ON public.v_gex_greeks_l2_net TO anon;
GRANT SELECT ON public.v_gex_greeks_l2_net TO merdian_ro;

-- ===== view: public.v_gex_greeks_l2_net_1pct | md5 528ee96cced70676c522252c7a16e463 | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_greeks_l2_net_1pct AS
 SELECT symbol,
    ts,
    expiry_date,
    dte,
    spot,
    is_trading_session,
    t_days,
    r_sess,
    n_r_rows,
    n_strikes,
    n_legs,
    net_delta_drift_iv_cr_per_volpt,
    net_delta_drift_time_cr_per_day,
    net_gex_drift_iv_cr_per_volpt,
    net_gex_drift_time_cr_per_day,
    gross_strike_delta_drift_iv,
    gross_strike_delta_drift_time,
    gross_strike_gex_drift_iv,
    gross_strike_gex_drift_time,
    net_over_gross_delta_drift_iv,
    net_over_gross_delta_drift_time,
    net_over_gross_gex_drift_iv,
    net_over_gross_gex_drift_time,
    status,
    (net_gex_drift_time_cr_per_day * (0.01)::double precision) AS net_gex_drift_time_cr_per_day_1pct,
    (net_gex_drift_iv_cr_per_volpt * (0.01)::double precision) AS net_gex_drift_iv_cr_per_volpt_1pct,
    (gross_strike_gex_drift_time * (0.01)::double precision) AS gross_strike_gex_drift_time_1pct,
    (gross_strike_gex_drift_iv * (0.01)::double precision) AS gross_strike_gex_drift_iv_1pct
   FROM v_gex_greeks_l2_net v;
ALTER VIEW public.v_gex_greeks_l2_net_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gex_greeks_l2_net_1pct TO anon;
GRANT SELECT ON public.v_gex_greeks_l2_net_1pct TO merdian_ro;

-- ===== view: public.v_gex_greeks_l2_strike | md5 8cbd78e543e8eb77eaf4ef87bb5d758b | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_greeks_l2_strike AS
 WITH b AS (
         SELECT v_gex_greeks_l2_leg.symbol,
            v_gex_greeks_l2_leg.ts,
            v_gex_greeks_l2_leg.expiry_date,
            v_gex_greeks_l2_leg.strike,
            v_gex_greeks_l2_leg.option_type,
            v_gex_greeks_l2_leg.spot,
            v_gex_greeks_l2_leg.dte,
            v_gex_greeks_l2_leg.t_years,
            v_gex_greeks_l2_leg.r_sess,
            v_gex_greeks_l2_leg.n_r_rows,
            v_gex_greeks_l2_leg.is_trading_session,
            v_gex_greeks_l2_leg.oi_qty,
            v_gex_greeks_l2_leg.iv,
            v_gex_greeks_l2_leg.gamma,
            v_gex_greeks_l2_leg.k,
            v_gex_greeks_l2_leg.sgn,
            v_gex_greeks_l2_leg.sigma,
            v_gex_greeks_l2_leg.oi,
            v_gex_greeks_l2_leg.in_leg_set,
            v_gex_greeks_l2_leg.priceable,
            v_gex_greeks_l2_leg.evaluable,
            v_gex_greeks_l2_leg.d1,
            v_gex_greeks_l2_leg.d2,
            v_gex_greeks_l2_leg.u_delta_drift_iv,
            v_gex_greeks_l2_leg.u_delta_drift_time,
            v_gex_greeks_l2_leg.u_gex_drift_iv,
            v_gex_greeks_l2_leg.u_gex_drift_time
           FROM v_gex_greeks_l2_leg
        ), hdr AS (
         SELECT DISTINCT b.symbol,
            b.ts,
            b.expiry_date,
            b.spot,
            b.dte,
            b.t_years,
            b.r_sess,
            b.n_r_rows,
            b.is_trading_session
           FROM b
        ), perleg AS (
         SELECT b.symbol,
            b.ts,
            b.expiry_date,
            b.dte,
            b.spot,
            b.k,
            (((((b.sgn)::double precision * b.u_delta_drift_iv) * b.oi) * (b.spot)::double precision) / ('10000000'::numeric)::double precision) AS leg_delta_drift_iv,
            (((((b.sgn)::double precision * b.u_delta_drift_time) * b.oi) * (b.spot)::double precision) / ('10000000'::numeric)::double precision) AS leg_delta_drift_time,
            (((((b.sgn)::double precision * b.u_gex_drift_iv) * b.oi) * (power(b.spot, (2)::numeric))::double precision) / ('10000000'::numeric)::double precision) AS leg_gex_drift_iv,
            (((((b.sgn)::double precision * b.u_gex_drift_time) * b.oi) * (power(b.spot, (2)::numeric))::double precision) / ('10000000'::numeric)::double precision) AS leg_gex_drift_time
           FROM b
          WHERE (b.in_leg_set AND b.evaluable)
        ), agg AS (
         SELECT perleg.symbol,
            perleg.ts,
            perleg.expiry_date,
            perleg.dte,
            perleg.spot,
            perleg.k,
            (count(*))::integer AS n_legs,
            sum(perleg.leg_delta_drift_iv) AS delta_drift_iv_cr_per_volpt,
            sum(perleg.leg_delta_drift_time) AS delta_drift_time_cr_per_day,
            sum(perleg.leg_gex_drift_iv) AS gex_drift_iv_cr_per_volpt,
            sum(perleg.leg_gex_drift_time) AS gex_drift_time_cr_per_day,
            sum(abs(perleg.leg_delta_drift_iv)) AS gross_delta_drift_iv,
            sum(abs(perleg.leg_delta_drift_time)) AS gross_delta_drift_time,
            sum(abs(perleg.leg_gex_drift_iv)) AS gross_gex_drift_iv,
            sum(abs(perleg.leg_gex_drift_time)) AS gross_gex_drift_time
           FROM perleg
          GROUP BY perleg.symbol, perleg.ts, perleg.expiry_date, perleg.dte, perleg.spot, perleg.k
        )
 SELECT h.symbol,
    h.ts,
    h.expiry_date,
    h.dte,
    h.spot,
    a.k AS strike,
    h.is_trading_session,
    (h.t_years * (365.0)::double precision) AS t_days,
    h.r_sess,
    h.n_r_rows,
    a.n_legs,
    a.delta_drift_iv_cr_per_volpt,
    a.delta_drift_time_cr_per_day,
    a.gex_drift_iv_cr_per_volpt,
    a.gex_drift_time_cr_per_day,
    a.gross_delta_drift_iv,
    a.gross_delta_drift_time,
    a.gross_gex_drift_iv,
    a.gross_gex_drift_time,
        CASE
            WHEN (h.dte = 0) THEN 'SKIPPED_EXPIRY'::text
            WHEN (h.n_r_rows < 6) THEN 'UNMEASURABLE_R'::text
            WHEN (a.k IS NULL) THEN 'NO_LEGS'::text
            ELSE 'OK'::text
        END AS status
   FROM (hdr h
     LEFT JOIN agg a ON (((a.symbol = h.symbol) AND (a.ts = h.ts) AND (a.expiry_date = h.expiry_date))));
GRANT SELECT ON public.v_gex_greeks_l2_strike TO authenticated;
GRANT SELECT ON public.v_gex_greeks_l2_strike TO anon;
GRANT SELECT ON public.v_gex_greeks_l2_strike TO merdian_ro;

-- ===== view: public.v_gex_greeks_l2_strike_1pct | md5 bbf3f693d3e3e6d8256de9878ac0e798 | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_greeks_l2_strike_1pct AS
 SELECT symbol,
    ts,
    expiry_date,
    dte,
    spot,
    strike,
    is_trading_session,
    t_days,
    r_sess,
    n_r_rows,
    n_legs,
    delta_drift_iv_cr_per_volpt,
    delta_drift_time_cr_per_day,
    gex_drift_iv_cr_per_volpt,
    gex_drift_time_cr_per_day,
    gross_delta_drift_iv,
    gross_delta_drift_time,
    gross_gex_drift_iv,
    gross_gex_drift_time,
    status,
    (gex_drift_time_cr_per_day * (0.01)::double precision) AS gex_drift_time_cr_per_day_1pct,
    (gex_drift_iv_cr_per_volpt * (0.01)::double precision) AS gex_drift_iv_cr_per_volpt_1pct
   FROM v_gex_greeks_l2_strike v;
ALTER VIEW public.v_gex_greeks_l2_strike_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gex_greeks_l2_strike_1pct TO anon;
GRANT SELECT ON public.v_gex_greeks_l2_strike_1pct TO merdian_ro;

-- ===== view: public.v_gex_net_gamma_river | md5 8f7bb678085c9a2c41d7b37ee8937204 | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_net_gamma_river AS
 WITH bounded AS (
         SELECT gamma_metrics.symbol,
            gamma_metrics.ts,
            (gamma_metrics.ts AT TIME ZONE 'Asia/Kolkata'::text) AS ts_ist,
            ((gamma_metrics.ts AT TIME ZONE 'Asia/Kolkata'::text))::date AS session_date,
            gamma_metrics.net_gex,
            gamma_metrics.spot,
            gamma_metrics.expiry_date,
            gamma_metrics.dte
           FROM gamma_metrics
          WHERE ((gamma_metrics.ts >= (now() - '90 days'::interval)) AND (gamma_metrics.net_gex IS NOT NULL))
        ), sess AS (
         SELECT bounded.symbol,
            bounded.session_date,
            count(*) AS n_runs,
            min(bounded.net_gex) AS session_min_net_gex_cr,
            max(bounded.net_gex) AS session_max_net_gex_cr,
            max(bounded.ts_ist) AS last_ts_ist_any
           FROM bounded
          GROUP BY bounded.symbol, bounded.session_date
        ), pick AS (
         SELECT DISTINCT ON (bounded.symbol, bounded.session_date) bounded.symbol,
            bounded.session_date,
            bounded.ts,
            bounded.net_gex,
            bounded.spot,
            bounded.expiry_date,
            bounded.dte
           FROM bounded
          WHERE ((bounded.ts_ist)::time without time zone <= '15:15:00'::time without time zone)
          ORDER BY bounded.symbol, bounded.session_date, bounded.ts DESC
        ), ranked AS (
         SELECT p.symbol,
            p.session_date,
            p.ts,
            p.net_gex,
            p.spot,
            p.expiry_date,
            p.dte,
            s.n_runs,
            s.session_min_net_gex_cr,
            s.session_max_net_gex_cr,
            s.last_ts_ist_any,
            row_number() OVER (PARTITION BY p.symbol ORDER BY p.session_date DESC) AS session_rank
           FROM (pick p
             JOIN sess s ON (((s.symbol = p.symbol) AND (s.session_date = p.session_date))))
        )
 SELECT symbol,
    session_date,
    ts,
    session_rank,
    net_gex AS net_gex_cr,
        CASE
            WHEN (net_gex > (0)::numeric) THEN 'DAMPENING'::text
            WHEN (net_gex < (0)::numeric) THEN 'AMPLIFYING'::text
            ELSE NULL::text
        END AS gamma_side,
    spot,
    session_min_net_gex_cr,
    session_max_net_gex_cr,
    n_runs,
    (last_ts_ist_any >= (session_date + '15:10:00'::time without time zone)) AS session_complete,
    expiry_date,
    dte
   FROM ranked
  WHERE (session_rank <= 30);
GRANT SELECT ON public.v_gex_net_gamma_river TO authenticated;
GRANT SELECT ON public.v_gex_net_gamma_river TO anon;
GRANT SELECT ON public.v_gex_net_gamma_river TO merdian_ro;

-- ===== view: public.v_gex_net_gamma_river_1pct | md5 44813e088b92024e01a4b08d223e5745 | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_net_gamma_river_1pct AS
 SELECT symbol,
    session_date,
    ts,
    session_rank,
    net_gex_cr,
    gamma_side,
    spot,
    session_min_net_gex_cr,
    session_max_net_gex_cr,
    n_runs,
    session_complete,
    expiry_date,
    dte,
    (net_gex_cr * 0.01) AS net_gex_cr_1pct,
    (session_min_net_gex_cr * 0.01) AS session_min_net_gex_cr_1pct,
    (session_max_net_gex_cr * 0.01) AS session_max_net_gex_cr_1pct
   FROM v_gex_net_gamma_river v;
ALTER VIEW public.v_gex_net_gamma_river_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gex_net_gamma_river_1pct TO anon;
GRANT SELECT ON public.v_gex_net_gamma_river_1pct TO merdian_ro;

-- ===== view: public.v_gex_strike_accel_zone | md5 c34bc2a228d615bc63080425805ff69a | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_strike_accel_zone AS
 WITH RECURSIVE latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM (( VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol)
             CROSS JOIN LATERAL ( SELECT g.run_id,
                    g.ts
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol = s.symbol)
                  ORDER BY g.ts DESC
                 LIMIT 1) lr)
        ), scoped AS (
         SELECT g.id,
            g.run_id,
            g.symbol,
            g.ts,
            g.expiry_date,
            g.dte,
            g.strike,
            g.spot,
            g.oi_call,
            g.oi_put,
            g.gex_cr,
            g.created_at,
            g.gamma_call,
            g.gamma_put
           FROM (gex_strike_snapshots g
             JOIN latest_run lr ON (((g.symbol = lr.symbol) AND (g.run_id = lr.run_id))))
        ), strike_step AS (
         SELECT x.run_id,
            x.symbol,
            x.expiry_date,
            min(x.diff) AS step
           FROM ( SELECT scoped.run_id,
                    scoped.symbol,
                    scoped.expiry_date,
                    (scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.run_id, scoped.symbol, scoped.expiry_date ORDER BY scoped.strike)) AS diff
                   FROM scoped) x
          WHERE (x.diff > (0)::numeric)
          GROUP BY x.run_id, x.symbol, x.expiry_date
        ), trough AS (
         SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date) scoped.run_id,
            scoped.symbol,
            scoped.expiry_date,
            scoped.ts,
            scoped.spot,
            scoped.strike AS trough_strike,
            scoped.gex_cr AS trough_gex_cr,
            COALESCE(get_parameter_num(('accel.tau.'::text || scoped.symbol)), 0.3) AS tau
           FROM scoped
          WHERE (scoped.gex_cr < (0)::numeric)
          ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr, (abs((scoped.strike - scoped.spot)))
        ), walk AS (
         SELECT t.run_id,
            t.symbol,
            t.expiry_date,
            t.ts,
            t.trough_strike AS strike,
            t.trough_gex_cr AS gex_cr,
            t.trough_gex_cr,
            t.tau,
            s.step,
            0 AS direction
           FROM (trough t
             JOIN strike_step s USING (run_id, symbol, expiry_date))
        UNION ALL
         SELECT g.run_id,
            g.symbol,
            g.expiry_date,
            g.ts,
            g.strike,
            g.gex_cr,
            w_1.trough_gex_cr,
            w_1.tau,
            w_1.step,
                CASE
                    WHEN (g.strike < w_1.strike) THEN '-1'::integer
                    ELSE 1
                END AS direction
           FROM (walk w_1
             JOIN scoped g ON (((g.run_id = w_1.run_id) AND (g.symbol = w_1.symbol) AND (g.expiry_date = w_1.expiry_date) AND (((w_1.direction = ANY (ARRAY[0, '-1'::integer])) AND (abs((g.strike - (w_1.strike - w_1.step))) < 0.0001)) OR ((w_1.direction = ANY (ARRAY[0, 1])) AND (abs((g.strike - (w_1.strike + w_1.step))) < 0.0001))))))
          WHERE ((g.gex_cr < (0)::numeric) AND (abs(g.gex_cr) >= (w_1.tau * abs(w_1.trough_gex_cr))))
        )
 SELECT run_id,
    symbol,
    expiry_date,
    max(ts) AS ts,
    min(strike) AS accel_lower,
    max(strike) AS accel_upper,
    count(*) AS n_strikes,
    sum(gex_cr) AS total_accel_gex_cr,
    min(trough_gex_cr) AS trough_gex_cr,
    (array_agg(strike ORDER BY gex_cr))[1] AS trough_strike,
    max(tau) AS tau_used
   FROM walk w
  GROUP BY run_id, symbol, expiry_date;
GRANT SELECT ON public.v_gex_strike_accel_zone TO authenticated;
GRANT SELECT ON public.v_gex_strike_accel_zone TO anon;
GRANT SELECT ON public.v_gex_strike_accel_zone TO merdian_ro;

-- ===== view: public.v_gex_strike_pin_zone | md5 2503e61efde43af0f5f747339087deca | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_strike_pin_zone AS
 WITH RECURSIVE latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM (( VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol)
             CROSS JOIN LATERAL ( SELECT g.run_id,
                    g.ts
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol = s.symbol)
                  ORDER BY g.ts DESC
                 LIMIT 1) lr)
        ), scoped AS (
         SELECT g.id,
            g.run_id,
            g.symbol,
            g.ts,
            g.expiry_date,
            g.dte,
            g.strike,
            g.spot,
            g.oi_call,
            g.oi_put,
            g.gex_cr,
            g.created_at,
            g.gamma_call,
            g.gamma_put
           FROM (gex_strike_snapshots g
             JOIN latest_run lr ON (((g.symbol = lr.symbol) AND (g.run_id = lr.run_id))))
        ), strike_step AS (
         SELECT x.run_id,
            x.symbol,
            x.expiry_date,
            min(x.diff) AS step
           FROM ( SELECT scoped.run_id,
                    scoped.symbol,
                    scoped.expiry_date,
                    (scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.run_id, scoped.symbol, scoped.expiry_date ORDER BY scoped.strike)) AS diff
                   FROM scoped) x
          WHERE (x.diff > (0)::numeric)
          GROUP BY x.run_id, x.symbol, x.expiry_date
        ), peak AS (
         SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date) scoped.run_id,
            scoped.symbol,
            scoped.expiry_date,
            scoped.ts,
            scoped.spot,
            scoped.strike AS peak_strike,
            scoped.gex_cr AS peak_gex_cr,
            COALESCE(get_parameter_num(('pin.tau.'::text || scoped.symbol)), 0.3) AS tau
           FROM scoped
          WHERE (scoped.gex_cr > (0)::numeric)
          ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr DESC, (abs((scoped.strike - scoped.spot)))
        ), walk AS (
         SELECT p.run_id,
            p.symbol,
            p.expiry_date,
            p.ts,
            p.peak_strike AS strike,
            p.peak_gex_cr AS gex_cr,
            p.peak_gex_cr,
            p.tau,
            s.step,
            0 AS direction
           FROM (peak p
             JOIN strike_step s USING (run_id, symbol, expiry_date))
        UNION ALL
         SELECT g.run_id,
            g.symbol,
            g.expiry_date,
            g.ts,
            g.strike,
            g.gex_cr,
            w_1.peak_gex_cr,
            w_1.tau,
            w_1.step,
                CASE
                    WHEN (g.strike < w_1.strike) THEN '-1'::integer
                    ELSE 1
                END AS direction
           FROM (walk w_1
             JOIN scoped g ON (((g.run_id = w_1.run_id) AND (g.symbol = w_1.symbol) AND (g.expiry_date = w_1.expiry_date) AND (((w_1.direction = ANY (ARRAY[0, '-1'::integer])) AND (abs((g.strike - (w_1.strike - w_1.step))) < 0.0001)) OR ((w_1.direction = ANY (ARRAY[0, 1])) AND (abs((g.strike - (w_1.strike + w_1.step))) < 0.0001))))))
          WHERE ((g.gex_cr > (0)::numeric) AND (g.gex_cr >= (w_1.tau * w_1.peak_gex_cr)))
        )
 SELECT run_id,
    symbol,
    expiry_date,
    max(ts) AS ts,
    min(strike) AS pin_lower,
    max(strike) AS pin_upper,
    count(*) AS n_strikes,
    sum(gex_cr) AS total_pin_gex_cr,
    max(peak_gex_cr) AS peak_pin_gex_cr,
    (array_agg(strike ORDER BY gex_cr DESC))[1] AS peak_pin_strike,
    max(tau) AS tau_used
   FROM walk w
  GROUP BY run_id, symbol, expiry_date;
GRANT SELECT ON public.v_gex_strike_pin_zone TO authenticated;
GRANT SELECT ON public.v_gex_strike_pin_zone TO anon;
GRANT SELECT ON public.v_gex_strike_pin_zone TO merdian_ro;

-- ===== view: public.v_gex_strike_rank | md5 9cc07f97e0b7862e265d5422439d304c | options: -
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_strike_rank AS
 WITH RECURSIVE symbols AS (
         SELECT ( SELECT min(g_1.symbol) AS min
                   FROM gex_strike_snapshots g_1) AS symbol
        UNION ALL
         SELECT ( SELECT min(g_1.symbol) AS min
                   FROM gex_strike_snapshots g_1
                  WHERE (g_1.symbol > s.symbol)) AS min
           FROM symbols s
          WHERE (s.symbol IS NOT NULL)
        ), latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM (symbols s
             CROSS JOIN LATERAL ( SELECT g_1.run_id,
                    g_1.ts
                   FROM gex_strike_snapshots g_1
                  WHERE (g_1.symbol = s.symbol)
                  ORDER BY g_1.ts DESC
                 LIMIT 1) lr)
          WHERE (s.symbol IS NOT NULL)
        ), scoped AS (
         SELECT g_1.run_id,
            g_1.symbol,
            g_1.ts,
            g_1.expiry_date,
            g_1.dte,
            g_1.strike,
            g_1.spot,
            g_1.gex_cr
           FROM (gex_strike_snapshots g_1
             JOIN latest_run lr ON (((g_1.symbol = lr.symbol) AND (g_1.run_id = lr.run_id))))
        ), run_hdr AS (
         SELECT scoped.run_id,
            scoped.symbol,
            scoped.expiry_date,
            max(scoped.ts) AS ts,
            max(scoped.dte) AS dte,
            max(scoped.spot) AS spot,
            count(*) AS n_strikes,
            count(*) FILTER (WHERE (scoped.gex_cr <> (0)::numeric)) AS n_ranked,
            COALESCE(get_parameter_num('wall.iv_floor_min'::text), (120)::numeric) AS iv_floor_min
           FROM scoped
          GROUP BY scoped.run_id, scoped.symbol, scoped.expiry_date
        ), sig AS (
         SELECT h.run_id,
            h.symbol,
            h.expiry_date,
            h.ts,
            h.dte,
            h.spot,
            h.n_strikes,
            h.n_ranked,
            h.iv_floor_min,
            v.atm_iv_avg AS atm_iv,
            (((h.spot * v.atm_iv_avg) / 100.0) * sqrt(((GREATEST(h.dte, 1))::numeric / 252.0))) AS sigma,
            (EXTRACT(epoch FROM (h.ts - v.ts)) / 60.0) AS atm_iv_age_min
           FROM (run_hdr h
             LEFT JOIN LATERAL ( SELECT vs.ts,
                    vs.atm_iv_avg
                   FROM volatility_snapshots vs
                  WHERE ((vs.symbol = h.symbol) AND (vs.ts <= h.ts) AND (vs.atm_iv_avg IS NOT NULL))
                  ORDER BY vs.ts DESC
                 LIMIT 1) v ON (true))
        ), ranked AS (
         SELECT sc.run_id,
            sc.symbol,
            sc.expiry_date,
            sc.strike,
            sc.gex_cr,
            abs(sc.gex_cr) AS abs_gex_cr,
            row_number() OVER (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date ORDER BY (abs(sc.gex_cr)) DESC, sc.strike) AS strike_rank,
            (abs(sc.gex_cr) / NULLIF(sum(abs(sc.gex_cr)) OVER (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date), (0)::numeric)) AS share_of_abs,
            (sum(abs(sc.gex_cr)) OVER (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date ORDER BY (abs(sc.gex_cr)) DESC, sc.strike ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) / NULLIF(sum(abs(sc.gex_cr)) OVER (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date), (0)::numeric)) AS cum_share_of_abs
           FROM scoped sc
          WHERE (sc.gex_cr <> (0)::numeric)
        )
 SELECT r.run_id,
    r.symbol,
    r.expiry_date,
    g.ts,
    g.dte,
    g.spot,
    g.sigma,
    g.atm_iv AS atm_iv_used,
    round(g.atm_iv_age_min, 1) AS atm_iv_age_min,
    ((g.atm_iv_age_min IS NOT NULL) AND (g.atm_iv_age_min <= g.iv_floor_min)) AS iv_fresh,
    r.strike_rank,
    r.strike,
    r.gex_cr,
    r.abs_gex_cr,
        CASE
            WHEN (r.gex_cr > (0)::numeric) THEN 'DAMPENING'::text
            WHEN (r.gex_cr < (0)::numeric) THEN 'AMPLIFYING'::text
            ELSE NULL::text
        END AS side,
    r.share_of_abs,
    r.cum_share_of_abs,
    ((r.strike - g.spot) / NULLIF(g.sigma, (0)::numeric)) AS dist_sigma,
    g.n_ranked,
    g.n_strikes
   FROM (ranked r
     JOIN sig g ON (((g.run_id = r.run_id) AND (g.symbol = r.symbol) AND (g.expiry_date = r.expiry_date))));
GRANT SELECT ON public.v_gex_strike_rank TO authenticated;
GRANT SELECT ON public.v_gex_strike_rank TO anon;
GRANT SELECT ON public.v_gex_strike_rank TO merdian_ro;

-- ===== view: public.v_gex_strike_snapshots_1pct | md5 d45a16a29eb2c3ab5f5ebf45382cb3da | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_strike_snapshots_1pct AS
 SELECT id,
    run_id,
    symbol,
    ts,
    expiry_date,
    dte,
    strike,
    spot,
    oi_call,
    oi_put,
    gex_cr,
    created_at,
    gamma_call,
    gamma_put,
    (gex_cr * 0.01) AS gex_cr_1pct
   FROM gex_strike_snapshots t;
ALTER VIEW public.v_gex_strike_snapshots_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gex_strike_snapshots_1pct TO anon;
GRANT SELECT ON public.v_gex_strike_snapshots_1pct TO merdian_ro;

-- ===== view: public.v_gex_strike_terrain | md5 25f0fd7d088426b8458a8e3f0e2fddcb | options: -
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_strike_terrain AS
 WITH RECURSIVE syms AS (
         SELECT s.symbol
           FROM ( VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol)
        ), back AS (
         SELECT s.symbol,
            1 AS step_n,
            ( SELECT ((max(g.ts) AT TIME ZONE 'Asia/Kolkata'::text))::date AS timezone
                   FROM gex_strike_snapshots g
                  WHERE (g.symbol = s.symbol)) AS d
           FROM syms s
        UNION ALL
         SELECT b.symbol,
            (b.step_n + 1),
            ( SELECT ((max(g.ts) AT TIME ZONE 'Asia/Kolkata'::text))::date AS timezone
                   FROM gex_strike_snapshots g
                  WHERE ((g.symbol = b.symbol) AND (g.ts < ((b.d)::timestamp without time zone AT TIME ZONE 'Asia/Kolkata'::text)))) AS timezone
           FROM back b
          WHERE ((b.step_n < 20) AND (b.d IS NOT NULL))
        ), candidates AS (
         SELECT b.symbol,
            b.d AS session_date
           FROM back b
          WHERE ((b.d IS NOT NULL) AND (NOT (EXISTS ( SELECT 1
                   FROM trading_calendar tc
                  WHERE ((tc.trade_date = b.d) AND (tc.is_open = false))))))
        ), settled_all AS MATERIALIZED (
         SELECT c.symbol,
            c.session_date,
            r.run_id,
            r.ts,
            (EXISTS ( SELECT 1
                   FROM gex_strike_snapshots g2
                  WHERE ((g2.symbol = c.symbol) AND (g2.ts >= ((c.session_date + '15:10:00'::time without time zone) AT TIME ZONE 'Asia/Kolkata'::text)) AND (g2.ts < (((c.session_date + 1))::timestamp without time zone AT TIME ZONE 'Asia/Kolkata'::text))))) AS session_complete
           FROM (candidates c
             CROSS JOIN LATERAL ( SELECT g.run_id,
                    g.ts
                   FROM gex_strike_snapshots g
                  WHERE ((g.symbol = c.symbol) AND (g.ts >= ((c.session_date)::timestamp without time zone AT TIME ZONE 'Asia/Kolkata'::text)) AND (g.ts <= ((c.session_date + '15:15:00'::time without time zone) AT TIME ZONE 'Asia/Kolkata'::text)))
                  ORDER BY g.ts DESC
                 LIMIT 1) r)
        ), settled AS MATERIALIZED (
         SELECT x.symbol,
            x.session_date,
            x.run_id,
            x.ts,
            x.session_complete,
            x.session_rank
           FROM ( SELECT sa.symbol,
                    sa.session_date,
                    sa.run_id,
                    sa.ts,
                    sa.session_complete,
                    row_number() OVER (PARTITION BY sa.symbol ORDER BY sa.session_date DESC) AS session_rank
                   FROM settled_all sa) x
          WHERE (x.session_rank <= 14)
        ), runrows AS (
         SELECT st.symbol,
            st.session_date,
            st.session_rank,
            st.run_id,
            st.ts,
            st.session_complete,
            g.expiry_date,
            g.dte,
            g.strike,
            g.spot,
                CASE
                    WHEN ((g.gamma_call IS NULL) AND (g.gamma_put IS NULL)) THEN NULL::numeric
                    ELSE g.gex_cr
                END AS gex_cr,
            g.oi_call,
            g.oi_put
           FROM (settled st
             JOIN gex_strike_snapshots g ON (((g.symbol = st.symbol) AND (g.run_id = st.run_id) AND (g.ts >= st.ts) AND (g.ts < (st.ts + '00:05:00'::interval)))))
        ), fexp AS (
         SELECT runrows.symbol,
            runrows.session_date,
            min(runrows.expiry_date) AS front_expiry
           FROM runrows
          WHERE (runrows.expiry_date >= runrows.session_date)
          GROUP BY runrows.symbol, runrows.session_date
        ), front AS (
         SELECT r.symbol,
            r.session_date,
            r.session_rank,
            r.run_id,
            r.ts,
            r.session_complete,
            r.expiry_date,
            r.dte,
            r.strike,
            r.spot,
            r.gex_cr,
            r.oi_call,
            r.oi_put
           FROM (runrows r
             JOIN fexp e ON (((e.symbol = r.symbol) AND (e.session_date = r.session_date))))
          WHERE (r.expiry_date = e.front_expiry)
        ), pain AS (
         SELECT q.symbol,
            q.session_date,
            q.session_rank,
            q.run_id,
            q.ts,
            q.session_complete,
            q.expiry_date,
            q.dte,
            q.strike,
            q.spot,
            q.gex_cr,
            q.oi_call,
            q.oi_put,
            q.oc,
            q.op,
            ((((q.strike * COALESCE(sum(q.oc) OVER wlt, (0)::numeric)) - COALESCE(sum((q.strike * q.oc)) OVER wlt, (0)::numeric)) + COALESCE(sum((q.strike * q.op)) OVER wgt, (0)::numeric)) - (q.strike * COALESCE(sum(q.op) OVER wgt, (0)::numeric))) AS writer_pain
           FROM ( SELECT f.symbol,
                    f.session_date,
                    f.session_rank,
                    f.run_id,
                    f.ts,
                    f.session_complete,
                    f.expiry_date,
                    f.dte,
                    f.strike,
                    f.spot,
                    f.gex_cr,
                    f.oi_call,
                    f.oi_put,
                    (COALESCE(f.oi_call, (0)::bigint))::numeric AS oc,
                    (COALESCE(f.oi_put, (0)::bigint))::numeric AS op
                   FROM front f) q
          WINDOW wlt AS (PARTITION BY q.symbol, q.session_date ORDER BY q.strike ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), wgt AS (PARTITION BY q.symbol, q.session_date ORDER BY q.strike ROWS BETWEEN 1 FOLLOWING AND UNBOUNDED FOLLOWING)
        ), marked AS (
         SELECT p.symbol,
            p.session_date,
            p.session_rank,
            p.run_id,
            p.ts,
            p.session_complete,
            p.expiry_date,
            p.dte,
            p.strike,
            p.spot,
            p.gex_cr,
            p.oi_call,
            p.oi_put,
            p.oc,
            p.op,
            p.writer_pain,
            first_value(p.strike) OVER (PARTITION BY p.symbol, p.session_date ORDER BY p.writer_pain, p.strike) AS max_pain_strike,
            max(p.spot) FILTER (WHERE (p.session_rank = 1)) OVER (PARTITION BY p.symbol) AS axis_spot
           FROM pain p
        )
 SELECT symbol,
    session_date,
    (session_rank)::integer AS session_rank,
    session_complete,
    run_id,
    ts,
    spot,
    expiry_date,
    dte,
    strike,
    gex_cr,
    oi_call,
    oi_put,
    writer_pain,
    max_pain_strike,
    (strike = max_pain_strike) AS is_max_pain
   FROM marked m
  WHERE (abs((strike - axis_spot)) <= (0.06 * axis_spot));
GRANT SELECT ON public.v_gex_strike_terrain TO anon;
GRANT SELECT ON public.v_gex_strike_terrain TO merdian_ro;

-- ===== view: public.v_gex_strike_terrain_1pct | md5 c8a5624e1dffa0309f3b55499de99c4f | options: security_invoker=true
-- acl: {postgres=arwdDxtm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_gex_strike_terrain_1pct AS
 SELECT symbol,
    session_date,
    session_rank,
    session_complete,
    run_id,
    ts,
    spot,
    expiry_date,
    dte,
    strike,
    gex_cr,
    oi_call,
    oi_put,
    writer_pain,
    max_pain_strike,
    is_max_pain,
    (gex_cr * 0.01) AS gex_cr_1pct
   FROM v_gex_strike_terrain v;
ALTER VIEW public.v_gex_strike_terrain_1pct SET (security_invoker=true);
GRANT SELECT ON public.v_gex_strike_terrain_1pct TO anon;
GRANT SELECT ON public.v_gex_strike_terrain_1pct TO merdian_ro;

-- ===== view: public.v_pin_board | md5 0cf9c82f1ad5090dd3bc615e8fe42004 | options: security_invoker=false
-- acl: {postgres=arwdDxtm/postgres,authenticated=rm/postgres,service_role=arwdDxtm/postgres,anon=r/postgres,merdian_ro=r/postgres}
CREATE OR REPLACE VIEW public.v_pin_board AS
 WITH RECURSIVE symbols AS (
         SELECT ( SELECT min(h_1.symbol) AS min
                   FROM gex_cycle_history h_1) AS symbol
        UNION ALL
         SELECT ( SELECT min(h_1.symbol) AS min
                   FROM gex_cycle_history h_1
                  WHERE (h_1.symbol > s.symbol)) AS min
           FROM symbols s
          WHERE (s.symbol IS NOT NULL)
        ), last_open AS MATERIALIZED (
         SELECT s.symbol,
            lo.ts AS last_ts,
            lo.expiry_date AS front_expiry,
            ((lo.ts AT TIME ZONE 'Asia/Kolkata'::text))::date AS session_date_ist
           FROM (symbols s
             CROSS JOIN LATERAL ( SELECT h_1.ts,
                    h_1.expiry_date
                   FROM gex_cycle_history h_1
                  WHERE ((h_1.symbol = s.symbol) AND (h_1.session_gate_state = 'OPEN'::text))
                  ORDER BY h_1.ts DESC, h_1.expiry_date
                 LIMIT 1) lo)
          WHERE (s.symbol IS NOT NULL)
        )
 SELECT h.symbol,
    h.expiry_date,
    l.session_date_ist,
    h.ts,
    (h.ts = l.last_ts) AS is_latest,
    h.run_id,
    h.dte,
    h.spot,
    h.pin_leader_strike,
    h.gamma_at_pin,
    h.runnerup_share_ratio,
    h.top5_share,
    h.top5_share_n_ranks,
    h.conc_top1_share,
    h.conc_hhi,
    h.max_pain_strike,
    h.call_wall_strike,
    h.put_wall_strike,
    h.pin_state,
    h.pin_state_reason,
    h.held_for_cycles,
    h.conviction,
    h.conviction_reason,
    h.is_fresh,
    h.reconciled_at
   FROM (last_open l
     CROSS JOIN LATERAL ( SELECT x.symbol,
            x.expiry_date,
            x.ts,
            x.run_id,
            x.session_gate_state,
            x.session_gate_ticks,
            x.chain_ts,
            x.dte,
            x.spot,
            x.atm_iv,
            x.net_gex,
            x.gamma_regime,
            x.flip_level,
            x.repriced_flip_level,
            x.repriced_flip_ts,
            x.repriced_flip_source,
            x.pin_leader_strike,
            x.gamma_at_pin,
            x.runnerup_share_ratio,
            x.top5_share,
            x.top5_share_n_ranks,
            x.conc_top1_share,
            x.conc_top1_share_call,
            x.conc_top1_share_put,
            x.conc_hhi,
            x.max_pain_strike,
            x.pin_state,
            x.pin_state_reason,
            x.held_for_cycles,
            x.conviction,
            x.conviction_reason,
            x.call_wall_strike,
            x.put_wall_strike,
            x.is_fresh,
            x.snapshot_age_min,
            x.writer,
            x.writer_version,
            x.reconciled_at,
            x.reconciler_version,
            x.created_at
           FROM gex_cycle_history x
          WHERE ((x.symbol = l.symbol) AND (x.session_gate_state = 'OPEN'::text) AND (x.ts >= ((l.session_date_ist)::timestamp without time zone AT TIME ZONE 'Asia/Kolkata'::text)) AND (x.ts <= l.last_ts) AND (x.expiry_date = l.front_expiry))) h);
ALTER VIEW public.v_pin_board SET (security_invoker=false);
GRANT SELECT ON public.v_pin_board TO authenticated;
GRANT SELECT ON public.v_pin_board TO anon;
GRANT SELECT ON public.v_pin_board TO merdian_ro;

-- ===== function: public.backfill_pin_maxpain_runs | md5 df1ffdf9d64f67ae371b15d05e09cd89 | options: -
-- acl: {=X/postgres,postgres=X/postgres,anon=X/postgres,authenticated=X/postgres,service_role=X/postgres}
CREATE OR REPLACE FUNCTION public.backfill_pin_maxpain_runs(p_symbol text, p_ts_from timestamp with time zone, p_ts_to timestamp with time zone, p_limit integer DEFAULT 20)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE n integer; v_runs uuid[];
BEGIN
  SELECT array_agg(run_id) INTO v_runs FROM (
    SELECT DISTINCT g.run_id
    FROM public.gex_strike_snapshots g
    WHERE g.symbol = p_symbol AND g.ts >= p_ts_from AND g.ts < p_ts_to
      AND NOT EXISTS (SELECT 1 FROM public.gex_pin_maxpain_history h
                      WHERE h.symbol = g.symbol AND h.run_id = g.run_id)
    LIMIT p_limit) x;
  IF v_runs IS NULL THEN RETURN 0; END IF;

  WITH RECURSIVE scoped AS (
    SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte, g.strike,
           g.spot, g.oi_call, g.oi_put, g.gex_cr
    FROM public.gex_strike_snapshots g
    WHERE g.symbol = p_symbol AND g.ts >= p_ts_from AND g.ts < p_ts_to
      AND g.run_id = ANY(v_runs)
  ),
  strike_step AS (
    SELECT x.run_id, x.symbol, x.expiry_date, min(x.diff) AS step
    FROM (SELECT run_id, symbol, expiry_date,
                 strike - lag(strike) OVER (PARTITION BY run_id, symbol, expiry_date ORDER BY strike) AS diff
          FROM scoped) x
    WHERE x.diff > 0::numeric
    GROUP BY x.run_id, x.symbol, x.expiry_date
  ),
  peak AS (
    SELECT DISTINCT ON (run_id, symbol, expiry_date)
           run_id, symbol, expiry_date, ts, spot,
           strike AS peak_strike, gex_cr AS peak_gex_cr,
           COALESCE(get_parameter_num('pin.tau.'::text || symbol), 0.3) AS tau
    FROM scoped WHERE gex_cr > 0::numeric
    ORDER BY run_id, symbol, expiry_date, gex_cr DESC, (abs(strike - spot))
  ),
  walk AS (
    SELECT p.run_id, p.symbol, p.expiry_date, p.ts, p.peak_strike AS strike,
           p.peak_gex_cr AS gex_cr, p.peak_gex_cr, p.tau, s.step, 0 AS direction
    FROM peak p JOIN strike_step s USING (run_id, symbol, expiry_date)
    UNION ALL
    SELECT g.run_id, g.symbol, g.expiry_date, g.ts, g.strike, g.gex_cr,
           w.peak_gex_cr, w.tau, w.step,
           CASE WHEN g.strike < w.strike THEN -1 ELSE 1 END
    FROM walk w
    JOIN scoped g
      ON g.run_id = w.run_id AND g.symbol = w.symbol AND g.expiry_date = w.expiry_date
     AND ((w.direction = ANY (ARRAY[0,-1])) AND abs(g.strike - (w.strike - w.step)) < 0.0001
       OR (w.direction = ANY (ARRAY[0, 1])) AND abs(g.strike - (w.strike + w.step)) < 0.0001)
    WHERE g.gex_cr > 0::numeric AND g.gex_cr >= (w.tau * w.peak_gex_cr)
  ),
  pin AS (
    SELECT run_id, symbol, expiry_date, max(ts) AS ts,
           min(strike) AS pin_lower, max(strike) AS pin_upper,
           count(*) AS pin_n_strikes, max(peak_gex_cr) AS peak_pin_gex_cr,
           (array_agg(strike ORDER BY gex_cr DESC))[1] AS peak_pin_strike,
           max(tau) AS tau_used
    FROM walk GROUP BY run_id, symbol, expiry_date
  ),
  pain AS (
    SELECT k.run_id, k.symbol, k.expiry_date, k.strike AS cand,
           SUM(GREATEST(k.strike - c.strike, 0) * COALESCE(c.oi_call,0))
         + SUM(GREATEST(c.strike - k.strike, 0) * COALESCE(c.oi_put,0)) AS tp
    FROM scoped k JOIN scoped c
      ON c.run_id = k.run_id AND c.symbol = k.symbol AND c.expiry_date = k.expiry_date
    GROUP BY k.run_id, k.symbol, k.expiry_date, k.strike
  ),
  mp AS (
    SELECT DISTINCT ON (run_id, symbol, expiry_date)
           run_id, symbol, expiry_date, cand AS max_pain_strike
    FROM pain ORDER BY run_id, symbol, expiry_date, tp ASC, cand ASC
  ),
  meta AS (
    SELECT run_id, symbol, expiry_date, max(ts) AS ts, max(dte) AS dte,
           max(spot) AS spot, count(*) AS chain_n_strikes
    FROM scoped GROUP BY run_id, symbol, expiry_date
  )
  INSERT INTO public.gex_pin_maxpain_history
    (symbol, run_id, ts, expiry_date, dte, spot, peak_pin_strike, pin_lower, pin_upper,
     pin_n_strikes, peak_pin_gex_cr, tau_used, max_pain_strike, chain_n_strikes)
  SELECT m.symbol, m.run_id, m.ts, m.expiry_date, m.dte, m.spot,
         p.peak_pin_strike, p.pin_lower, p.pin_upper, p.pin_n_strikes,
         p.peak_pin_gex_cr, p.tau_used, mp.max_pain_strike, m.chain_n_strikes
  FROM meta m
  JOIN pin p USING (run_id, symbol, expiry_date)
  JOIN mp    USING (run_id, symbol, expiry_date)
  ON CONFLICT (symbol, run_id, expiry_date) DO NOTHING;

  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $function$;

-- ===== function: public.p3b_sweep | md5 af57a99c11fb83cf43872721c71b3ff9 | options: -
-- acl: {postgres=X/postgres,service_role=X/postgres}
CREATE OR REPLACE FUNCTION public.p3b_sweep(p_now timestamp with time zone DEFAULT now(), p_window interval DEFAULT '01:00:00'::interval, p_min_age interval DEFAULT '00:03:00'::interval)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'pg_temp'
 SET enable_nestloop TO 'off'
AS $function$
DECLARE
  v_ver  constant text := 'p3b-v1.2';
  v_runs integer := 0;
  v_lo   timestamptz;
  v_hi   timestamptz;
BEGIN
  CREATE TEMP TABLE IF NOT EXISTS p3b_cand (symbol text, expiry_date date, run_id uuid, ts timestamptz) ON COMMIT DROP;
  TRUNCATE p3b_cand;
  -- A run is a candidate once it is >= p_min_age old (never checked half-written) and has no check rows yet.
  INSERT INTO p3b_cand
  SELECT g.symbol, g.expiry_date, g.run_id, min(g.ts)
  FROM gex_strike_snapshots g
  WHERE g.ts >= p_now - p_window AND g.ts <= p_now - p_min_age
    AND NOT EXISTS (SELECT 1 FROM p3b_invariant_checks c
                    WHERE c.kind = 'check' AND c.symbol = g.symbol AND c.expiry_date = g.expiry_date AND c.run_id = g.run_id)
  GROUP BY g.symbol, g.expiry_date, g.run_id;
  GET DIAGNOSTICS v_runs = ROW_COUNT;
  -- bounds as plain values, and stats on the temp table: measured 55 s -> see header with subquery bounds and no ANALYZE
  SELECT min(ts), max(ts) INTO v_lo, v_hi FROM p3b_cand;
  ANALYZE p3b_cand;

  WITH
  gs AS (
    SELECT g.symbol, g.expiry_date, g.run_id, c.ts, g.strike::float8 AS k, g.spot::float8 AS s,
           g.gex_cr::float8 AS gex, g.oi_call::numeric AS oi_call, g.oi_put::numeric AS oi_put
    FROM gex_strike_snapshots g JOIN p3b_cand c USING (symbol, expiry_date, run_id)
    -- ts bounds let the planner use the ts index instead of scanning the table for run_id
    WHERE g.ts BETWEEN v_lo AND v_hi + interval '15 minutes'),
  leg AS (
    SELECT o.symbol, o.expiry_date, o.run_id, o.strike::float8 AS k, upper(o.option_type) AS ot,
           coalesce(o.gamma::float8, 0) AS gamma, coalesce(o.oi::numeric, 0) AS oi,
           o.bid::float8 AS bid, o.ask::float8 AS ask, o.spot::float8 AS s
    FROM option_chain_snapshots o JOIN p3b_cand c USING (symbol, expiry_date, run_id)
    WHERE o.ts BETWEEN v_lo - interval '15 minutes' AND v_hi + interval '15 minutes'),
  -- I2 / I3 per strike
  st AS (
    SELECT gs.symbol, gs.expiry_date, gs.run_id, gs.ts, gs.k, gs.gex, gs.oi_call, gs.oi_put,
           count(l.k) AS n_legs,
           coalesce(sum(CASE
             WHEN l.gamma = 0 OR l.oi <= 0 OR gs.s <= 0 THEN 0
             WHEN gs.k > 0 AND abs(gs.k - gs.s) / gs.s > 0.05 AND abs(l.gamma) > 5e-5 THEN 0
             ELSE l.gamma * l.oi::float8 * gs.s * gs.s / 1e7 * CASE WHEN l.ot = 'PE' THEN -1 ELSE 1 END END), 0) AS rc,
           coalesce(sum(trunc(l.oi)) FILTER (WHERE l.ot = 'CE'), 0) AS oc,
           coalesce(sum(trunc(l.oi)) FILTER (WHERE l.ot = 'PE'), 0) AS op
    FROM gs LEFT JOIN leg l ON l.symbol = gs.symbol AND l.expiry_date = gs.expiry_date AND l.run_id = gs.run_id AND l.k = gs.k
    GROUP BY gs.symbol, gs.expiry_date, gs.run_id, gs.ts, gs.k, gs.gex, gs.oi_call, gs.oi_put),
  st2 AS (
    SELECT *, abs(rc - gex) AS d2, (abs(rc - gex) > 1e-6 + 1e-9 * abs(gex)) AS f2,
           greatest(abs(oc - trunc(oi_call)), abs(op - trunc(oi_put)))::float8 AS d3,
           (oc <> trunc(oi_call) OR op <> trunc(oi_put)) AS f3
    FROM st WHERE n_legs > 0),
  -- per run aggregates for I1 / I4 / I5
  -- (S96-H rev 2: the per-run correlated subqueries and the gamma_metrics lateral were O(runs x rows) and timed out
  --  at real volume on 10-09; each is now one GROUP BY, joined by key. gamma_metrics.ts = the run's ts on all 313 fixture runs)
  gagg AS (
    SELECT symbol, expiry_date, run_id, sum(gex) AS tot, max(abs(gex)) / nullif(sum(abs(gex)), 0) AS top1
    FROM gs GROUP BY symbol, expiry_date, run_id),
  gm AS (
    SELECT DISTINCT ON (x.symbol, x.expiry_date, x.run_id) x.symbol, x.expiry_date, x.run_id,
           x.net_gex::float8 AS net_gex, x.gamma_concentration::float8 AS conc, x.flip_level::float8 AS fl
    FROM gamma_metrics x JOIN p3b_cand c USING (symbol, expiry_date, run_id)
    WHERE x.ts BETWEEN v_lo - interval '15 minutes' AND v_hi + interval '15 minutes'
    ORDER BY x.symbol, x.expiry_date, x.run_id, x.ts DESC),
  run AS (
    SELECT c.symbol, c.expiry_date, c.run_id, c.ts, a.tot, a.top1, m.net_gex, m.conc, m.fl, (m.run_id IS NOT NULL) AS has_gm
    FROM p3b_cand c
    LEFT JOIN gagg a USING (symbol, expiry_date, run_id)
    LEFT JOIN gm m USING (symbol, expiry_date, run_id)),
  sagg AS (
    SELECT symbol, expiry_date, run_id, count(*) AS n,
           count(*) FILTER (WHERE f2) AS f2, count(*) FILTER (WHERE f3) AS f3, max(d2) AS d2, max(d3) AS d3,
           to_jsonb((array_agg(jsonb_build_object('k', k, 'stored', gex, 'recompute', rc) ORDER BY d2 DESC) FILTER (WHERE f2))[1:5]) AS ff2,
           to_jsonb((array_agg(jsonb_build_object('k', k, 'oi_call', oi_call, 'chain_ce', oc, 'oi_put', oi_put, 'chain_pe', op) ORDER BY d3 DESC) FILTER (WHERE f3))[1:5]) AS ff3
    FROM st2 GROUP BY symbol, expiry_date, run_id),
  nochain AS (
    SELECT symbol, expiry_date, run_id, count(*) AS no_chain FROM st WHERE n_legs = 0 GROUP BY symbol, expiry_date, run_id),
  cum AS (
    SELECT symbol, expiry_date, run_id, k,
           sum(gex) OVER w_up AS up, sum(gex) OVER w_dn AS dn
    FROM gs
    WINDOW w_up AS (PARTITION BY symbol, expiry_date, run_id ORDER BY k ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
           w_dn AS (PARTITION BY symbol, expiry_date, run_id ORDER BY k ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING)),
  cum2 AS (
    SELECT *, lead(k) OVER p AS k1, lead(up) OVER p AS up1, lead(dn) OVER p AS dn1
    FROM cum WINDOW p AS (PARTITION BY symbol, expiry_date, run_id ORDER BY k)),
  i5 AS (
    SELECT r.symbol, r.expiry_date, r.run_id,
           coalesce(bool_or(c.k <= r.fl AND r.fl <= c.k1 AND (c.up > 0) <> (c.up1 > 0)), false) AS asc_ok,
           coalesce(bool_or(c.k <= r.fl AND r.fl <= c.k1 AND (c.dn > 0) <> (c.dn1 > 0)), false) AS desc_ok
    FROM run r JOIN cum2 c USING (symbol, expiry_date, run_id)
    WHERE r.fl IS NOT NULL AND c.k1 IS NOT NULL
    GROUP BY r.symbol, r.expiry_date, r.run_id),
  -- I6 per strike: exactly one CE and one PE, all of bid/ask/spot > 0
  pc AS (
    SELECT symbol, expiry_date, run_id, k,
           count(*) FILTER (WHERE ot = 'CE') AS nce, count(*) FILTER (WHERE ot = 'PE') AS npe,
           max(bid) FILTER (WHERE ot = 'CE') AS cb, max(ask) FILTER (WHERE ot = 'CE') AS ca,
           max(bid) FILTER (WHERE ot = 'PE') AS pb, max(ask) FILTER (WHERE ot = 'PE') AS pa,
           max(s)   FILTER (WHERE ot = 'CE') AS s
    FROM leg GROUP BY symbol, expiry_date, run_id, k),
  pc2 AS (
    SELECT symbol, expiry_date, run_id,
           count(*) AS n, count(*) FILTER (WHERE abs((cb + ca) / 2 - (pb + pa) / 2 - (s - k)) > (ca - cb) / 2 + (pa - pb) / 2) AS outside
    FROM pc WHERE nce = 1 AND npe = 1 AND cb > 0 AND ca > 0 AND pb > 0 AND pa > 0 AND s > 0
    GROUP BY symbol, expiry_date, run_id),
  out AS (
    -- I1
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I1' AS check_id,
           CASE WHEN NOT r.has_gm THEN 'NOT_COMPUTED' WHEN abs(r.tot - r.net_gex) > 0.01 THEN 'FAIL' ELSE 'OK' END AS status,
           CASE WHEN r.has_gm THEN 1 ELSE 0 END AS n_checked,
           CASE WHEN r.has_gm AND abs(r.tot - r.net_gex) > 0.01 THEN 1 ELSE 0 END AS n_fail,
           CASE WHEN r.has_gm THEN abs(r.tot - r.net_gex) END AS max_abs_diff,
           CASE WHEN r.has_gm THEN jsonb_build_object('sum_gex_cr', r.tot, 'net_gex', r.net_gex)
                ELSE jsonb_build_object('reason', 'no gamma_metrics row') END AS detail
    FROM run r
    UNION ALL
    -- I4
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I4',
           CASE WHEN NOT r.has_gm OR r.conc IS NULL OR r.top1 IS NULL THEN 'NOT_COMPUTED'
                WHEN abs(r.top1 - r.conc) > 1e-6 THEN 'FAIL' ELSE 'OK' END,
           CASE WHEN r.has_gm AND r.conc IS NOT NULL AND r.top1 IS NOT NULL THEN 1 ELSE 0 END,
           CASE WHEN r.has_gm AND r.conc IS NOT NULL AND r.top1 IS NOT NULL AND abs(r.top1 - r.conc) > 1e-6 THEN 1 ELSE 0 END,
           abs(r.top1 - r.conc),
           CASE WHEN NOT r.has_gm THEN jsonb_build_object('reason', 'no gamma_metrics row')
                WHEN r.conc IS NULL THEN jsonb_build_object('reason', 'gamma_concentration null')
                WHEN r.top1 IS NULL THEN jsonb_build_object('reason', 'sum |gex| = 0')
                ELSE jsonb_build_object('top1_share', r.top1, 'gamma_concentration', r.conc) END
    FROM run r
    UNION ALL
    -- I2 and I3
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, x.check_id,
           CASE WHEN coalesce(a.n, 0) = 0 THEN 'NOT_COMPUTED'
                WHEN (CASE x.check_id WHEN 'I2' THEN a.f2 ELSE a.f3 END) > 0 THEN 'FAIL' ELSE 'OK' END,
           coalesce(a.n, 0),
           coalesce(CASE x.check_id WHEN 'I2' THEN a.f2 ELSE a.f3 END, 0),
           CASE x.check_id WHEN 'I2' THEN a.d2 ELSE a.d3 END,
           CASE WHEN coalesce(a.n, 0) = 0 THEN jsonb_build_object('reason', 'no chain rows at any strike')
                ELSE jsonb_build_object('strikes_without_chain', coalesce(nc.no_chain, 0),
                       'first_fails', CASE x.check_id WHEN 'I2' THEN a.ff2 ELSE a.ff3 END) END
    FROM run r
    CROSS JOIN (VALUES ('I2'), ('I3')) x(check_id)
    LEFT JOIN sagg a ON a.symbol = r.symbol AND a.expiry_date = r.expiry_date AND a.run_id = r.run_id
    LEFT JOIN nochain nc ON nc.symbol = r.symbol AND nc.expiry_date = r.expiry_date AND nc.run_id = r.run_id
    UNION ALL
    -- I5 descriptive
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I5',
           CASE WHEN r.fl IS NULL THEN 'NOT_COMPUTED' ELSE 'INFO' END,
           CASE WHEN r.fl IS NULL THEN 0 ELSE 1 END, NULL, NULL,
           CASE WHEN r.fl IS NULL THEN jsonb_build_object('reason', 'flip_level null')
                ELSE jsonb_build_object('flip_level', r.fl, 'ascending_ok', coalesce(i.asc_ok, false), 'descending_ok', coalesce(i.desc_ok, false)) END
    FROM run r LEFT JOIN i5 i USING (symbol, expiry_date, run_id)
    UNION ALL
    -- I6 descriptive
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I6',
           CASE WHEN coalesce(p.n, 0) = 0 THEN 'NOT_COMPUTED' ELSE 'INFO' END,
           coalesce(p.n, 0), coalesce(p.outside, 0), NULL,
           CASE WHEN coalesce(p.n, 0) = 0 THEN jsonb_build_object('reason', 'no strike with one CE and one PE with bid, ask and spot > 0')
                ELSE jsonb_build_object('outside_spreads', p.outside) END
    FROM run r LEFT JOIN pc2 p USING (symbol, expiry_date, run_id))
  INSERT INTO p3b_invariant_checks (kind, symbol, expiry_date, run_id, ts, check_id, status, n_checked, n_fail, max_abs_diff, detail, fn_version)
  SELECT 'check', symbol, expiry_date, run_id, ts, check_id, status, n_checked, n_fail, max_abs_diff, detail, v_ver FROM out;

  INSERT INTO p3b_invariant_checks (kind, status, n_checked, detail, fn_version)
  VALUES ('sweep', 'SWEEP_OK', v_runs, jsonb_build_object('p_now', p_now, 'window', p_window::text, 'min_age', p_min_age::text), v_ver);
  RETURN v_runs;
EXCEPTION WHEN OTHERS THEN
  -- the failed sweep's check rows roll back with this block; the error is recorded so the heartbeat shows it
  INSERT INTO p3b_invariant_checks (kind, status, n_checked, detail, fn_version)
  VALUES ('sweep', 'SWEEP_ERROR', NULL, jsonb_build_object('sqlstate', SQLSTATE, 'error', SQLERRM, 'p_now', p_now), v_ver);
  RETURN -1;
END
$function$;

