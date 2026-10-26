-- =====================================================================================================
-- S101 C7 -- v_gex_strike_accel_zone: the LIVE production definition, registered (ADR-025 D2 clause 4).
--
-- REGISTRATION ONLY. This is what production already runs; nothing here needs applying. Captured 2026-10-26 by the
-- operator with pg_get_viewdef('public.v_gex_strike_accel_zone'::regclass, true) on production: length 3547,
-- md5 87a0691ef33ef5e08cbf315fd6511064. The text after "AS" below, up to and including the final semicolon and
-- WITHOUT a trailing newline, reproduces both exactly (checked S101 by script).
--
-- WHY: the sibling of v_gex_strike_pin_zone (C6), with the same unregistered change. Live vs the only file that
-- defines it, sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql:
--   1. walk threshold: live walks on abs(gex_cr) >= tau * abs(trough_gex_cr) with
--      tau = COALESCE(get_parameter_num('accel.tau.'||symbol), 0.3); the s69 file hard-codes 0.3 and only REPORTS the
--      parameter as tau_used.
--   2. tau_used: live = max(tau), never NULL.
--   3. latest_run: live = CROSS JOIN LATERAL ... LIMIT 1 skip-scan over VALUES ('NIFTY'), ('SENSEX'); the s69 file =
--      DISTINCT ON (symbol).
-- Same output as the s69 file only while accel.tau = 0.30. No file in sql/ carries the COALESCE(accel.tau, 0.3)
-- pattern: the same S80 change as the pin zone, never registered. TD filed at the S101 close.
--
-- SUPERSEDES (as the record of what is live): the accel-zone part of sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql,
-- sql/2026-05-25_enh81_v_gex_strike_accel_zone.sql, sql/2026-05-25_enh81_v_gex_strike_accel_zone_PRE_S40.sql.
--
-- Verification (read-only; expected: 3547 | 87a0691ef33ef5e08cbf315fd6511064):
--   SELECT length(d), md5(d) FROM (SELECT pg_get_viewdef('public.v_gex_strike_accel_zone'::regclass, true) AS d) v;
-- =====================================================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_accel_zone AS
 WITH RECURSIVE latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM ( VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol)
             CROSS JOIN LATERAL ( SELECT g.run_id,
                    g.ts
                   FROM gex_strike_snapshots g
                  WHERE g.symbol = s.symbol
                  ORDER BY g.ts DESC
                 LIMIT 1) lr
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
           FROM gex_strike_snapshots g
             JOIN latest_run lr ON g.symbol = lr.symbol AND g.run_id = lr.run_id
        ), strike_step AS (
         SELECT x.run_id,
            x.symbol,
            x.expiry_date,
            min(x.diff) AS step
           FROM ( SELECT scoped.run_id,
                    scoped.symbol,
                    scoped.expiry_date,
                    scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.run_id, scoped.symbol, scoped.expiry_date ORDER BY scoped.strike) AS diff
                   FROM scoped) x
          WHERE x.diff > 0::numeric
          GROUP BY x.run_id, x.symbol, x.expiry_date
        ), trough AS (
         SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date) scoped.run_id,
            scoped.symbol,
            scoped.expiry_date,
            scoped.ts,
            scoped.spot,
            scoped.strike AS trough_strike,
            scoped.gex_cr AS trough_gex_cr,
            COALESCE(get_parameter_num('accel.tau.'::text || scoped.symbol), 0.3) AS tau
           FROM scoped
          WHERE scoped.gex_cr < 0::numeric
          ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr, (abs(scoped.strike - scoped.spot))
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
           FROM trough t
             JOIN strike_step s USING (run_id, symbol, expiry_date)
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
                    WHEN g.strike < w_1.strike THEN '-1'::integer
                    ELSE 1
                END AS direction
           FROM walk w_1
             JOIN scoped g ON g.run_id = w_1.run_id AND g.symbol = w_1.symbol AND g.expiry_date = w_1.expiry_date AND ((w_1.direction = ANY (ARRAY[0, '-1'::integer])) AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001 OR (w_1.direction = ANY (ARRAY[0, 1])) AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001)
          WHERE g.gex_cr < 0::numeric AND abs(g.gex_cr) >= (w_1.tau * abs(w_1.trough_gex_cr))
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