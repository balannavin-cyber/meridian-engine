WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol)
                  FROM gex_strike_snapshots g
                 WHERE g.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.run_id, lr.ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts
                 FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol
                ORDER BY g.ts DESC
                LIMIT 1
          ) lr
         WHERE s.symbol IS NOT NULL
     ), scoped AS (
        SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte,
               g.strike, g.spot, g.oi_call, g.oi_put,
               g.gamma_call, g.gamma_put, g.gex_cr,
               ( COALESCE(g.gamma_call, 0) * COALESCE(g.oi_call, 0)
               + COALESCE(g.gamma_put,  0) * COALESCE(g.oi_put,  0) )
               * (g.spot::double precision ^ 2) / 1e7 AS gross_cr
          FROM gex_strike_snapshots g
          JOIN latest_run lr
            ON g.symbol = lr.symbol AND g.run_id = lr.run_id
         WHERE g.spot > 0
           AND abs(g.strike / g.spot - 1) <= 0.05
     ), ranked AS (
        SELECT sc.run_id, sc.symbol, sc.ts, sc.expiry_date, sc.dte,
               sc.strike, sc.spot, sc.oi_call, sc.oi_put,
               sc.gamma_call, sc.gamma_put, sc.gex_cr, sc.gross_cr,
               row_number() OVER w AS strike_rank,
               sc.gross_cr / NULLIF(sum(sc.gross_cr) OVER p, 0) AS share_of_gross,
               count(*) OVER p AS n_ranked
          FROM scoped sc
         WHERE sc.gross_cr > 0
        WINDOW p AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date),
               w AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date
                     ORDER BY sc.gross_cr DESC, abs(sc.strike - sc.spot), sc.strike)
     ), hdr AS (
        SELECT run_id, symbol, expiry_date,
               max(gross_cr) FILTER (WHERE strike_rank = 1) AS top_cr,
               max(gross_cr) FILTER (WHERE strike_rank = 2) AS second_cr
          FROM ranked
         GROUP BY run_id, symbol, expiry_date
     )
SELECT r.run_id, r.symbol, r.expiry_date, r.ts, r.dte, r.spot,
       r.strike_rank, r.strike, r.oi_call, r.oi_put,
       r.gamma_call, r.gamma_put, r.gross_cr, r.share_of_gross, r.gex_cr,
       CASE WHEN r.gex_cr > 0 THEN 'DAMPENING'
            WHEN r.gex_cr < 0 THEN 'AMPLIFYING'
       END AS side,
       (h.top_cr - h.second_cr) / NULLIF(h.top_cr, 0) AS lead_rel,
       r.n_ranked
  FROM ranked r
  JOIN hdr h
    ON h.run_id = r.run_id AND h.symbol = r.symbol AND h.expiry_date = r.expiry_date;
