-- P1 level test — Part 3: replay check (§6.6). READ-ONLY. Reveals no outcome.
-- Run OUTSIDE 08:30–15:40 IST (GEX writer idle), so the replay and the live views read the same run.
-- Replays the §3 rules on the LATEST run per symbol and diffs them against the live views.
-- EXPECT ZERO ROWS. Any row = the replay is not the shipped rule: stop, do not reason about which side is right.
WITH lr AS (
    SELECT s.symbol, r.run_id, r.ts
      FROM (VALUES ('NIFTY'), ('SENSEX')) s(symbol)
      CROSS JOIN LATERAL (SELECT g.run_id, g.ts FROM gex_strike_snapshots g
                           WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1) r
), rows_ AS (
    SELECT g.* FROM gex_strike_snapshots g JOIN lr ON g.symbol = lr.symbol AND g.run_id = lr.run_id
), hdr AS (
    SELECT symbol, max(ts) AS ts, max(spot) AS s0, max(dte) AS dte FROM rows_ GROUP BY 1
), sig AS (
    SELECT h.*, COALESCE(get_parameter_num('wall.band.' || h.symbol, h.ts), 1.5) AS band,
           h.s0 * v.atm_iv_avg::numeric / 100.0 * sqrt(GREATEST(h.dte, 1)::numeric / 252.0) AS sigma_w
      FROM hdr h
      LEFT JOIN LATERAL (SELECT vs.atm_iv_avg FROM volatility_snapshots vs
                          WHERE vs.symbol = h.symbol AND vs.ts <= h.ts AND vs.atm_iv_avg IS NOT NULL
                          ORDER BY vs.ts DESC LIMIT 1) v ON true
), rep_walls AS (
    SELECT r.symbol,
           (array_agg(r.strike ORDER BY r.oi_call DESC, r.strike) FILTER (WHERE r.oi_call > 0))[1] AS cw,
           (array_agg(r.strike ORDER BY r.oi_put  DESC, r.strike) FILTER (WHERE r.oi_put  > 0))[1] AS pw
      FROM rows_ r JOIN sig g USING (symbol)
     WHERE g.sigma_w > 0 AND abs(r.strike - g.s0) <= g.band * g.sigma_w
     GROUP BY 1
), rep_top AS (
    SELECT symbol, array_agg(strike ORDER BY rk) AS top3
      FROM (SELECT r.symbol, r.strike,
                   row_number() OVER (PARTITION BY r.symbol
                                      ORDER BY abs(r.gex_cr) DESC, abs(r.strike - g.s0), r.strike) AS rk
              FROM rows_ r JOIN sig g USING (symbol) WHERE r.gex_cr <> 0) q
     WHERE rk <= 3 GROUP BY 1
), live_walls AS (
    SELECT symbol, call_wall AS cw, put_wall AS pw FROM public.v_gex_strike_walls
), live_top AS (
    SELECT symbol, array_agg(strike ORDER BY strike_rank) AS top3
      FROM public.v_gex_strike_rank WHERE strike_rank <= 3 GROUP BY 1
)
SELECT 'walls' AS check_, lr.symbol, lr.ts,
       rw.cw::text || ' / ' || rw.pw::text AS replay, lw.cw::text || ' / ' || lw.pw::text AS live
  FROM lr LEFT JOIN rep_walls rw USING (symbol) LEFT JOIN live_walls lw USING (symbol)
 WHERE rw.cw IS DISTINCT FROM lw.cw OR rw.pw IS DISTINCT FROM lw.pw
UNION ALL
SELECT 'top3', lr.symbol, lr.ts, rt.top3::text, lt.top3::text
  FROM lr LEFT JOIN rep_top rt USING (symbol) LEFT JOIN live_top lt USING (symbol)
 WHERE rt.top3 IS DISTINCT FROM lt.top3;
