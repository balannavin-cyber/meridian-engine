-- s89_1001 / ladder_replay_1001.sql
-- EXPLORATORY, NOT A TEST. Descriptive replay of 2026-10-01 SENSEX 0DTE, every capture cycle,
-- rebuilding the parity target's 11:51 ladder (leader + next four, % of leader, net-gamma LONG/SHORT)
-- plus the turn signals a call seller in a falling market would watch.
-- Read-only. Run via bin/roq.sh, out of market hours. Source: option_chain_snapshots (RLS off).
--
-- Definitions (this script's, named as ours):
--   gamma_load(strike) = sum over CE+PE of gamma * oi * lot * spot^2 * 0.01 / 1e7   (MERDIAN units;
--                        absolute scale unverified, ratios are scale-free)
--   pct_of_leader      = gamma_load / leader gamma_load  (matches the target's 11:51 "pressure" column
--                        on all 12 visible rows within display rounding)
--   net_g(strike)      = CE leg - PE leg  (calls dealer-long +, puts dealer-short -; the target's convention)
--   window             = strikes within +/-1500 pts of that cycle's spot
--   flip               = zero-crossing of strike-ordered cumulative net_g nearest spot (this script's definition,
--                        NOT MERDIAN's compute_flip_level)
--   flow_delta         = sum (oi - oi_at_first_cycle) * delta * lot * spot / 1e7   (OI change since the day's first
--                        cycle, delta-weighted; the target's "today's flow")
--   book_delta         = sum oi * delta * lot * spot / 1e7
--   per-cycle classes  = OI change vs price change against the PREVIOUS cycle (5-min), in OI units:
--                        short build = OI up, price down; short cover = OI down, price up;
--                        long build = OI up, price up;   long unwind = OI down, price down.
\pset format csv
\pset footer off
WITH params AS (
  SELECT 'SENSEX'::text                              AS sym,
         DATE '2026-10-01'                           AS expiry,
         TIMESTAMPTZ '2026-10-01 09:14:00+05:30'     AS t0,
         TIMESTAMPTZ '2026-10-01 15:31:00+05:30'     AS t1,
         20::numeric                                 AS lot,
         1500::numeric                               AS win_pts
),
raw AS (   -- one row per (ts, strike, side); newest id wins if a cycle was written twice
  SELECT DISTINCT ON (o.ts, o.strike, o.option_type)
         o.ts, o.strike::numeric AS strike, o.option_type,
         o.oi::numeric AS oi, o.gamma::numeric AS g, o.delta::numeric AS d,
         o.ltp::numeric AS ltp, o.spot::numeric AS spot
  FROM option_chain_snapshots o
  CROSS JOIN params p
  WHERE o.symbol = p.sym AND o.expiry_date = p.expiry
    AND o.ts >= p.t0 AND o.ts < p.t1
  ORDER BY o.ts, o.strike, o.option_type, o.id DESC
),
full_ts AS ( -- FULL-chain cycles only; ATM_ONLY tape rows (~10 per ts) are excluded
  SELECT ts FROM raw GROUP BY ts HAVING count(*) >= 200
),
chain AS (
  SELECT r.* FROM raw r JOIN full_ts USING (ts)
),
leg AS (
  SELECT c.ts, c.strike, c.option_type, c.oi, c.g, c.d, c.ltp,
         max(c.spot) OVER (PARTITION BY c.ts)                                        AS spot,
         first_value(c.oi)  OVER (PARTITION BY c.strike, c.option_type ORDER BY c.ts) AS oi_open,
         lag(c.oi)          OVER (PARTITION BY c.strike, c.option_type ORDER BY c.ts) AS oi_prev,
         lag(c.ltp)         OVER (PARTITION BY c.strike, c.option_type ORDER BY c.ts) AS ltp_prev,
         p.lot
  FROM chain c CROSS JOIN params p
),
leg2 AS (
  SELECT l.*, l.g * l.oi * l.lot * l.spot * l.spot * 0.01 / 1e7 AS gex_abs FROM leg l
),
strk AS (
  SELECT ts, strike, max(spot) AS spot,
         sum(gex_abs)                                                          AS gamma_load,
         sum(CASE WHEN option_type = 'CE' THEN gex_abs ELSE -gex_abs END)      AS net_g
  FROM leg2 GROUP BY ts, strike
),
win AS (
  SELECT s.* FROM strk s CROSS JOIN params p WHERE abs(s.strike - s.spot) <= p.win_pts
),
ranked AS (
  SELECT w.*,
         row_number() OVER (PARTITION BY ts ORDER BY gamma_load DESC)  AS rk,
         gamma_load / nullif(max(gamma_load) OVER (PARTITION BY ts), 0) AS pct_of_leader,
         gamma_load / nullif(sum(gamma_load) OVER (PARTITION BY ts), 0) AS share
  FROM win w
),
cyc AS (
  SELECT ts, max(spot) AS spot,
         max(strike) FILTER (WHERE rk = 1)                         AS leader,
         max(net_g)  FILTER (WHERE rk = 1)                         AS leader_net,
         round(100 * max(pct_of_leader) FILTER (WHERE rk = 2))     AS runner_pct,
         string_agg(strike::int || ':' || round(100 * pct_of_leader) || '%' ||
                    CASE WHEN net_g >= 0 THEN 'L' ELSE 'S' END, ' ' ORDER BY rk)
                    FILTER (WHERE rk <= 5)                         AS top5,
         round(sum(share * share), 3)                              AS hhi,
         round(sum(net_g) FILTER (WHERE strike <  spot AND strike >= spot - 500), 1) AS netg_500_below,
         round(sum(net_g) FILTER (WHERE strike >  spot AND strike <= spot + 500), 1) AS netg_500_above
  FROM ranked GROUP BY ts
),
cum AS (
  SELECT ts, strike, spot, sum(net_g) OVER (PARTITION BY ts ORDER BY strike) AS cg FROM win
),
cross_pts AS (
  SELECT ts, spot,
         lag(strike) OVER w AS ps, lag(cg) OVER w AS pcg, strike, cg
  FROM cum WINDOW w AS (PARTITION BY ts ORDER BY strike)
),
flip AS (
  SELECT DISTINCT ON (ts) ts,
         round(ps + (strike - ps) * (-pcg) / (cg - pcg)) AS flip
  FROM cross_pts
  WHERE pcg IS NOT NULL AND sign(pcg) <> sign(cg) AND cg <> pcg
  ORDER BY ts, abs(ps + (strike - ps) * (-pcg) / (cg - pcg) - spot)
),
flow AS (
  SELECT ts,
    round(sum(oi * d * lot * spot / 1e7), 1)                       AS book_delta,
    round(sum((oi - oi_open) * d * lot * spot / 1e7), 1)           AS flow_delta,
    sum(CASE WHEN option_type='CE' AND oi > oi_prev AND ltp < ltp_prev THEN oi - oi_prev ELSE 0 END) AS ce_short_build,
    sum(CASE WHEN option_type='CE' AND oi < oi_prev AND ltp > ltp_prev THEN oi_prev - oi ELSE 0 END) AS ce_short_cover,
    sum(CASE WHEN option_type='PE' AND oi > oi_prev AND ltp < ltp_prev THEN oi - oi_prev ELSE 0 END) AS pe_short_build,
    sum(CASE WHEN option_type='PE' AND oi > oi_prev AND ltp > ltp_prev THEN oi - oi_prev ELSE 0 END) AS pe_long_build,
    sum(CASE WHEN option_type='PE' AND oi < oi_prev AND ltp < ltp_prev THEN oi_prev - oi ELSE 0 END) AS pe_long_unwind
  FROM leg2 l2
  WHERE abs(l2.strike - l2.spot) <= (SELECT win_pts FROM params)
  GROUP BY ts
)
SELECT to_char(c.ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI')   AS ist,
       round(c.spot, 1)                                        AS spot,
       round(c.spot - lag(c.spot) OVER (ORDER BY c.ts), 1)     AS d_spot,
       c.leader::int                                           AS leader,
       round(c.spot - c.leader)                                AS spot_minus_leader,
       CASE WHEN c.leader_net >= 0 THEN 'LONG' ELSE 'SHORT' END AS leader_net,
       c.runner_pct,
       c.top5,
       c.hhi,
       f.flip,
       round(c.spot - f.flip)                                  AS spot_minus_flip,
       c.netg_500_below, c.netg_500_above,
       w.book_delta, w.flow_delta,
       CASE WHEN w.flow_delta = 0 THEN 'n/a' WHEN sign(w.book_delta) = sign(w.flow_delta) THEN 'SAME' ELSE 'OPPOSITE' END AS flow_vs_book,
       w.ce_short_build, w.ce_short_cover, w.pe_short_build, w.pe_long_build, w.pe_long_unwind
FROM cyc c
LEFT JOIN flip f USING (ts)
LEFT JOIN flow w USING (ts)
ORDER BY c.ts;
