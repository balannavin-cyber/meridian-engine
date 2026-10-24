
WITH latest AS (
  SELECT 'NIFTY'::text AS symbol, (SELECT max(ts) FROM option_chain_snapshots WHERE symbol='NIFTY' AND ts >= TIMESTAMPTZ '2026-10-14 08:15:00+00' AND ts <= TIMESTAMPTZ '2026-10-14 08:26:59+00') AS latest_ts
  UNION ALL
  SELECT 'SENSEX', (SELECT max(ts) FROM option_chain_snapshots WHERE symbol='SENSEX' AND ts >= TIMESTAMPTZ '2026-10-14 08:50:00+00' AND ts <= TIMESTAMPTZ '2026-10-14 09:01:59+00')
), front AS (
        SELECT l.symbol, l.latest_ts AS ts,
               min(o.expiry_date) AS front_expiry
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
         GROUP BY l.symbol, l.latest_ts
     ), scoped AS (
        SELECT f.symbol, f.ts, f.front_expiry,
               o.strike, o.option_type, o.iv, o.oi, o.gamma, o.spot
          FROM front f
          JOIN option_chain_snapshots o
            ON o.symbol = f.symbol AND o.ts = f.ts
           AND o.expiry_date = f.front_expiry
     ), hdr AS (
        SELECT s.symbol, s.ts, s.front_expiry,
               max(s.spot) AS spot,
               (s.front_expiry
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.front_expiry + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.front_expiry
     ), legs AS (
        SELECT s.symbol, s.ts,
               s.strike::double precision       AS k,
               s.option_type,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h ON h.symbol = s.symbol AND h.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), futwin AS (
        SELECT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM hdr h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
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
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess,
               percentile_cont(0.10) WITHIN GROUP (ORDER BY r_fut) AS r_p10,
               percentile_cont(0.90) WITHIN GROUP (ORDER BY r_fut) AS r_p90
          FROM rrows
         GROUP BY symbol, ts
     ), atm AS (
        SELECT h.symbol, h.ts,
               round(h.spot
                     / (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END))
                 * (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END)
                 AS atm_strike
          FROM hdr h
     ), atmiv AS (
        SELECT q.symbol, q.ts, q.atm_strike,
               CASE WHEN q.ce_iv > 0 AND q.pe_iv > 0
                    THEN (q.ce_iv + q.pe_iv) / 2.0
               END AS atm_iv
          FROM (
            SELECT a.symbol, a.ts, a.atm_strike,
                   NULLIF(max(CASE WHEN s.option_type = 'CE' THEN s.iv END), 0)
                     AS ce_iv,
                   NULLIF(max(CASE WHEN s.option_type = 'PE' THEN s.iv END), 0)
                     AS pe_iv
              FROM atm a
              LEFT JOIN scoped s
                ON s.symbol = a.symbol AND s.ts = a.ts
               AND s.strike = a.atm_strike
             GROUP BY a.symbol, a.ts, a.atm_strike
          ) q
     ), base AS (
        SELECT h.symbol, h.ts, h.front_expiry, h.spot, h.dte, h.t_years,
               r.n_r_rows, r.r_sess, r.r_p10, r.r_p90,
               v.atm_iv,
               (h.spot * v.atm_iv / 100.0 * sqrt(1.0 / 365.0))::double precision
                 AS sigma_1d
          FROM hdr h
          LEFT JOIN rstats r ON r.symbol = h.symbol AND r.ts = h.ts
          LEFT JOIN atmiv  v ON v.symbol = h.symbol AND v.ts = h.ts
     ), evalset AS (
        SELECT b.symbol, b.ts, b.spot::double precision AS spot,
               b.t_years, b.r_sess
          FROM base b
         WHERE b.dte > 0 AND b.t_years > 0
           AND b.n_r_rows >= 6 AND b.r_sess IS NOT NULL
     ), grid AS (
        SELECT e.symbol, e.ts, g.i,
               e.spot * (1.0 + (g.i - 100) * 0.001) AS s_grid
          FROM evalset e
          CROSS JOIN generate_series(0, 200) AS g(i)
     ), gexcurve AS (
        SELECT gr.symbol, gr.ts, gr.i, gr.s_grid,
               sum(
                 (CASE WHEN l.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                 * ( exp(-0.5 * power(
                       ( ln(gr.s_grid / l.k)
                         + (e.r_sess + 0.5 * power(l.sigma, 2)) * e.t_years )
                       / (l.sigma * sqrt(e.t_years)), 2))
                     / sqrt(2.0 * pi()) )
                   / (gr.s_grid * l.sigma * sqrt(e.t_years))
                 * l.oi * power(gr.s_grid, 2) / 1e7
               ) AS total_gex
          FROM grid gr
          JOIN evalset e ON e.symbol = gr.symbol AND e.ts = gr.ts
          JOIN legs   l  ON l.symbol = gr.symbol AND l.ts = gr.ts
         GROUP BY gr.symbol, gr.ts, gr.i, gr.s_grid
     ), adj AS (
        SELECT c.symbol, c.ts, c.s_grid, c.total_gex,
               lag(c.s_grid)    OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_s,
               lag(c.total_gex) OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_g
          FROM gexcurve c
     ), crossings AS (
        SELECT a.symbol, a.ts,
               a.prev_s + (a.s_grid - a.prev_s)
                        * (0.0 - a.prev_g) / (a.total_gex - a.prev_g)
                 AS s_star,
               CASE WHEN a.prev_g < 0 THEN 'neg->pos' ELSE 'pos->neg' END
                 AS flip_direction
          FROM adj a
         WHERE a.prev_g IS NOT NULL
           AND ((a.prev_g < 0) <> (a.total_gex < 0))
           AND a.total_gex <> a.prev_g
     ), counted AS (
        SELECT b.symbol, b.ts,
               count(x.s_star)::integer AS n_cross_full_grid,
               CASE WHEN b.sigma_1d IS NULL THEN NULL
                    ELSE count(x.s_star) FILTER (
                           WHERE abs(x.s_star - b.spot) <= 2.0 * b.sigma_1d
                         )::integer
               END AS n_cross_within_2sigma
          FROM base b
          LEFT JOIN crossings x ON x.symbol = b.symbol AND x.ts = b.ts
         GROUP BY b.symbol, b.ts, b.sigma_1d
     ), nearest AS (
        SELECT DISTINCT ON (x.symbol, x.ts)
               x.symbol, x.ts, x.s_star, x.flip_direction
          FROM crossings x
          JOIN base b ON b.symbol = x.symbol AND b.ts = x.ts
         ORDER BY x.symbol, x.ts, abs(x.s_star - b.spot)
     )
SELECT b.symbol, to_char(b.ts AT TIME ZONE 'Asia/Kolkata','HH24:MI:SS') AS ts_ist, round(b.spot::numeric,2) AS spot, b.front_expiry,
       round(n.s_star::numeric,1) AS flip, n.flip_direction, c.n_cross_within_2sigma, c.n_cross_full_grid,
       round(b.r_sess::numeric,4) AS r_sess, b.n_r_rows
  FROM base b LEFT JOIN nearest n ON n.symbol=b.symbol AND n.ts=b.ts LEFT JOIN counted c ON c.symbol=b.symbol AND c.ts=b.ts
 ORDER BY 1;
