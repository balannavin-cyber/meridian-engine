-- base_body_cost.sql -- the v_gex_greeks_l2_leg body (sql/2026-10-12_s96_v_gex_greeks_l2_leg.sql Section A) as a
-- plain query, for costing through bin/roq.sh BEFORE the apply. Read-only; creates nothing. Run TWICE:
--   { printf 'EXPLAIN (ANALYZE, BUFFERS)\n'; cat base_body_cost.sql; } | bin/roq.sh | grep -E 'Execution Time|CTE Scan on gate|Seq Scan on option_chain'
-- PASS: Execution Time < 3000 ms both runs; `CTE Scan on gate` shows loops=1; no Seq Scan on option_chain_snapshots.
-- (roq runs as merdian_ro, not anon; the anon timing is Section C2 after apply.)
WITH RECURSIVE symbols AS (
        -- S72 FIX 2 skip scan. Symbols derived, never a literal list.
        SELECT (SELECT min(o.symbol) FROM option_chain_snapshots o) AS symbol
        UNION ALL
        SELECT (SELECT min(o.symbol)
                  FROM option_chain_snapshots o
                 WHERE o.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest AS (
        -- ADR-021 run scoping: one index seek per symbol through
        -- idx_ocs_ts_symbol_expiry. NOT max(ts) GROUP BY symbol.
        -- NEVER created_at (S81, 89bc83e -- it hands back W2).
        SELECT s.symbol, lt.ts AS latest_ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = s.symbol
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), scoped AS (
        -- BOTH expiry legs, unlike ENH-131 which keeps the front only.
        -- L78-3 requires W2 to compute as normal on expiry day. Capture
        -- stage 1 holds exactly W1 and W2; the MONTHLIES L78-3 also names
        -- ARE NOT CAPTURED (measured: n_expiry = 2 on every session
        -- 09-28..10-02, both symbols) and therefore cannot appear here.
        SELECT l.symbol, l.latest_ts AS ts,
               o.expiry_date, o.strike, o.option_type,
               o.iv, o.oi, o.gamma, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the expiry over a 365-day
        -- year -- ENH-131's convention, Gate 5 convention (b).
        SELECT s.symbol, s.ts, s.expiry_date,
               max(s.spot) AS spot,
               (s.expiry_date
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.expiry_date
     ), gate AS MATERIALIZED (
        -- ENH-133 D-3 clause 3, cut off at ts so there is no look-ahead.
        -- AS MATERIALIZED is load-bearing: see the header, 164 ms vs
        -- 26,424 ms on the two-construct precursor. Join is on
        -- (symbol, ts). This body measures 210.280 / 186.476 ms pre-apply,
        -- with `CTE Scan on gate g` at loops=1 in both plans.
        SELECT h.symbol, h.ts,
               (SELECT count(DISTINCT o2.spot) > 1
                  FROM option_chain_snapshots o2
                 WHERE o2.symbol = h.symbol
                   AND o2.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata')::date)
                                  ::timestamp) AT TIME ZONE 'Asia/Kolkata')
                   AND o2.ts <= h.ts) AS is_trading_session
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
     ), futwin AS (
        -- NO LOOK-AHEAD. 09:20 IST on the ts date through ts INCLUSIVE.
        SELECT DISTINCT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE, which is not always the option front.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry, T_f from THAT ROW's own ts. F and S are from
        -- the same row, so they are contemporaneous by construction.
        SELECT w.symbol, w.ts,
               ( ln(w.futures_price / w.spot_price)
                 / (EXTRACT(epoch FROM
                      (((w.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                       - w.fut_ts)) / (365.0 * 86400.0))
               )::double precision AS r_fut
          FROM futwin w
          JOIN futfront f
            ON f.symbol = w.symbol AND f.ts = w.ts
           AND f.fut_expiry = w.expiry_date
         WHERE w.fut_ts < ((w.expiry_date + time '15:30')
                           AT TIME ZONE 'Asia/Kolkata')
     ), rstats AS (
        -- Fewer than 6 rows is UNMEASURABLE, never a substituted default
        -- (ADR-023 D1: fail to absent, never to stale).
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess
          FROM rrows
         GROUP BY symbol, ts
     ), leg AS (
        -- S96-F: EVERY chain row at the latest ts, both legs, with the header
        -- columns and three flags. in_leg_set is ENH-131's leg set
        -- byte-for-byte (the predicates the strike view sums over);
        -- priceable is the same predicates WITHOUT oi > 0 (ruling S96-F E2:
        -- a leg whose OI went to zero can still be valued for flow);
        -- evaluable is the old evalleg filter. COALESCE(.., false) because a
        -- WHERE treats NULL as false and these flags must say the same.
        SELECT s.symbol, s.ts, s.expiry_date, s.strike, s.option_type,
               h.spot, h.dte, h.t_years,
               r.r_sess, COALESCE(r.n_r_rows, 0) AS n_r_rows,
               g.is_trading_session,
               s.oi AS oi_qty, s.iv, s.gamma,
               s.strike::double precision       AS k,
               (CASE WHEN s.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                                                AS sgn,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi,
               COALESCE(s.oi > 0
                    AND s.gamma IS NOT NULL AND s.gamma <> 0
                    AND s.iv > 0
                    AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                             AND abs(s.gamma) > 5e-5), false) AS in_leg_set,
               COALESCE(s.gamma IS NOT NULL AND s.gamma <> 0
                    AND s.iv > 0
                    AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                             AND abs(s.gamma) > 5e-5), false) AS priceable,
               COALESCE(h.dte > 0 AND h.t_years > 0
                    AND COALESCE(r.n_r_rows, 0) >= 6
                    AND r.r_sess IS NOT NULL, false)          AS evaluable
          FROM scoped s
          JOIN hdr h
            ON h.symbol = s.symbol AND h.ts = s.ts
           AND h.expiry_date = s.expiry_date
          LEFT JOIN rstats r ON r.symbol = s.symbol AND r.ts = s.ts
          LEFT JOIN gate   g ON g.symbol = s.symbol AND g.ts = s.ts
     ), bs AS (
        -- The Black-Scholes chain of the S89 body, verbatim, on priceable and
        -- evaluable legs only.
        SELECT e.*,
               ( ln(e.spot / e.k)
                 + (e.r_sess + 0.5 * power(e.sigma, 2)) * e.t_years )
               / (e.sigma * sqrt(e.t_years))                   AS d1
          FROM leg e
         WHERE e.priceable AND e.evaluable
     ), bs2 AS (
        SELECT b.*,
               b.d1 - b.sigma * sqrt(b.t_years)                AS d2,
               exp(-0.5 * power(b.d1, 2)) / sqrt(2.0 * pi())   AS nd1,
               (b.r_sess + 0.5 * power(b.sigma, 2))
                 / (b.sigma * sqrt(b.t_years))
                 - b.d1 / (2.0 * b.t_years)                    AS dd1_dt
          FROM bs b
     ), bs3 AS (
        SELECT b.*,
               b.nd1 / (b.spot * b.sigma * sqrt(b.t_years))    AS bs_gamma
          FROM bs2 b
     ), unit AS (
        -- The four per-CONTRACT derivatives, unsigned and unscaled: exactly
        -- the sub-expressions the S89 perleg CTE multiplied by sgn, oi and
        -- spot. /100 = per IV point, /365 = per calendar day.
        SELECT b.symbol, b.ts, b.expiry_date, b.strike, b.option_type,
               b.d1, b.d2,
               ((-b.nd1 * b.d2 / b.sigma) / 100.0)                          AS u_delta_drift_iv,
               ((-b.nd1 * b.dd1_dt) / 365.0)                                AS u_delta_drift_time,
               ((b.bs_gamma * (b.d1 * b.d2 - 1.0) / b.sigma) / 100.0)       AS u_gex_drift_iv,
               ((b.bs_gamma * (b.d1 * b.dd1_dt
                               + 1.0 / (2.0 * b.t_years))) / 365.0)         AS u_gex_drift_time
          FROM bs3 b
     )
SELECT l.symbol, l.ts, l.expiry_date, l.strike, l.option_type,
       l.spot, l.dte, l.t_years, l.r_sess, l.n_r_rows, l.is_trading_session,
       l.oi_qty, l.iv, l.gamma, l.k, l.sgn, l.sigma, l.oi,
       l.in_leg_set, l.priceable, l.evaluable,
       u.d1, u.d2,
       u.u_delta_drift_iv, u.u_delta_drift_time, u.u_gex_drift_iv, u.u_gex_drift_time
  FROM leg l
  LEFT JOIN unit u
    ON u.symbol = l.symbol AND u.ts = l.ts AND u.expiry_date = l.expiry_date
   AND u.strike = l.strike AND u.option_type = l.option_type;
