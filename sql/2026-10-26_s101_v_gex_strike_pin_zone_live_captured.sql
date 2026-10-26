-- =====================================================================================================
-- S101 C6 -- v_gex_strike_pin_zone: the LIVE production definition, registered (ADR-025 D2 clause 4).
--
-- REGISTRATION ONLY. This is what production already runs; nothing here needs applying. It is committed so that
-- sql/ holds the definition that is live. Captured 2026-10-26 by the operator with
--   pg_get_viewdef('public.v_gex_strike_pin_zone'::regclass, true)
-- on production: length 3523, md5 89c9ac6aef9eb332ddd28f9062d0e21e. The text after "AS" below, up to and including
-- the final semicolon and WITHOUT a trailing newline, reproduces both exactly (checked S101 by script).
--
-- WHY: no earlier file defines the live view. It differs from the newest one,
-- sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql, in three ways (MR-S1 finding O1, verified S101):
--   1. walk threshold: live walks on tau * peak_gex_cr with tau = COALESCE(get_parameter_num('pin.tau.'||symbol),
--      0.3); the s69 file hard-codes 0.3 * peak_gex_cr and only REPORTS the parameter as tau_used.
--   2. tau_used: live = max(tau), never NULL; the s69 file's can be NULL (no default).
--   3. latest_run: live = CROSS JOIN LATERAL ... LIMIT 1 skip-scan over VALUES ('NIFTY'), ('SENSEX');
--      the s69 file = DISTINCT ON (symbol) over the whole table. Same rows for those two symbols.
-- Same output as the s69 file only while pin.tau = 0.30. The COALESCE(..., 0.3) AS tau pattern appears in exactly
-- one other file, sql/2026-09-22_s80_backfill_pin_maxpain_runs.sql (committed 85dfad2, S80): most likely the live
-- view was changed in S80 and its DDL never registered. TD filed at the S101 close.
--
-- SUPERSEDES (as the record of what is live): sql/2026-08-13_s69_gex_pin_accel_latest_run_scope.sql (pin-zone
-- part only), sql/2026-05-25_enh81_v_gex_strike_pin_zone.sql, sql/2026-05-25_enh81_v_gex_strike_pin_zone_PRE_S40.sql.
-- NOT CHECKED: the s69 file's sibling, v_gex_strike_accel_zone (hard-coded 0.3, reports accel.tau) -- its live
-- definition may have drifted the same way; compare its pg_get_viewdef md5 before relying on any file.
--
-- Verification (read-only; expected: 3523 | 89c9ac6aef9eb332ddd28f9062d0e21e):
--   SELECT length(d), md5(d) FROM (SELECT pg_get_viewdef('public.v_gex_strike_pin_zone'::regclass, true) AS d) v;
-- =====================================================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_pin_zone AS
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
        ), peak AS (
         SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date) scoped.run_id,
            scoped.symbol,
            scoped.expiry_date,
            scoped.ts,
            scoped.spot,
            scoped.strike AS peak_strike,
            scoped.gex_cr AS peak_gex_cr,
            COALESCE(get_parameter_num('pin.tau.'::text || scoped.symbol), 0.3) AS tau
           FROM scoped
          WHERE scoped.gex_cr > 0::numeric
          ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr DESC, (abs(scoped.strike - scoped.spot))
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
           FROM peak p
             JOIN strike_step s USING (run_id, symbol, expiry_date)
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
                    WHEN g.strike < w_1.strike THEN '-1'::integer
                    ELSE 1
                END AS direction
           FROM walk w_1
             JOIN scoped g ON g.run_id = w_1.run_id AND g.symbol = w_1.symbol AND g.expiry_date = w_1.expiry_date AND ((w_1.direction = ANY (ARRAY[0, '-1'::integer])) AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001 OR (w_1.direction = ANY (ARRAY[0, 1])) AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001)
          WHERE g.gex_cr > 0::numeric AND g.gex_cr >= (w_1.tau * w_1.peak_gex_cr)
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