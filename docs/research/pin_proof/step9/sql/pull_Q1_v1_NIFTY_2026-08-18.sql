
WITH g AS (
  SELECT run_id, strike, gex_cr, spot, dte, ts, symbol, expiry_date,
         gamma_call, gamma_put
  FROM public.gex_strike_snapshots
  WHERE symbol = 'NIFTY'
    AND ts >= '2026-08-18 00:00:00+05:30'::timestamptz AND ts < '2026-08-19 00:00:00+05:30'::timestamptz
), ag AS (
  SELECT run_id,
    count(*) AS v1_n,
    sum(gex_cr) AS v1_net,
    sum(abs(gex_cr)) AS v1_abs,
    sum(gex_cr * gex_cr) AS v1_sq,
    max(abs(gex_cr)) AS v1_maxabs,
    min(dte) AS v1_dte, count(DISTINCT dte) AS v1_dte_n,
    min(symbol) AS v1_symbol, count(DISTINCT symbol) AS v1_symbol_n,
    min(expiry_date)::text AS v1_expiry_date, count(DISTINCT expiry_date) AS v1_expiry_n,
    min(ts) AS v1_ts, count(DISTINCT ts) AS v1_ts_n,
    min(ts AT TIME ZONE 'Asia/Kolkata') AS v1_ts_ist,
    min(spot) AS v1_spot, count(DISTINCT spot) AS v1_spot_n,
    coalesce(sum(gex_cr) FILTER (WHERE abs(strike - spot) <= 0.05 * spot), 0) AS v1_net_in5,
    coalesce(sum(abs(gex_cr)) FILTER (WHERE abs(strike - spot) <= 0.05 * spot), 0) AS v1_abs_in5,
    count(*) FILTER (WHERE gamma_call IS NOT NULL)
      + count(*) FILTER (WHERE gamma_put IS NOT NULL) AS legs_with_gamma,
    count(*) FILTER (WHERE gamma_call > 5e-5 AND abs(strike - spot) > 0.05 * spot)
      + count(*) FILTER (WHERE gamma_put > 5e-5 AND abs(strike - spot) > 0.05 * spot) AS legs_removed,
    coalesce(sum(abs(gex_cr)) FILTER (
        WHERE abs(strike - spot) > 0.05 * spot
          AND (gamma_call > 5e-5 OR gamma_put > 5e-5)), 0) AS v1_abs_at_removed
  FROM g GROUP BY run_id
), rk AS (
  SELECT run_id, strike, gex_cr,
    row_number() OVER (PARTITION BY run_id
        ORDER BY abs(gex_cr) DESC, abs(strike - spot), strike) AS rn_abs,
    rank() OVER (PARTITION BY run_id ORDER BY abs(gex_cr) DESC) AS rk_abs,
    row_number() OVER (PARTITION BY run_id
        ORDER BY gex_cr DESC, abs(strike - spot), strike) AS rn_pos,
    rank() OVER (PARTITION BY run_id ORDER BY gex_cr DESC) AS rk_pos
  FROM g
), pk AS (
  SELECT run_id, strike AS v1_peak_strike FROM rk WHERE rn_abs = 1
), pkt AS (
  SELECT run_id, count(*) AS v1_peak_ties FROM rk WHERE rk_abs = 1 GROUP BY run_id
), ps AS (
  SELECT run_id, strike AS v1_pos_strike FROM rk WHERE rn_pos = 1 AND gex_cr > 0
), pst AS (
  SELECT run_id, count(*) AS v1_pos_ties FROM rk
  WHERE rk_pos = 1 AND gex_cr > 0 GROUP BY run_id
)
SELECT row_to_json(t)::text AS j FROM (
  SELECT ag.run_id, ag.v1_n, ag.v1_net, ag.v1_abs, ag.v1_sq, ag.v1_maxabs,
         ag.v1_dte, ag.v1_dte_n, ag.v1_symbol, ag.v1_symbol_n,
         ag.v1_expiry_date, ag.v1_expiry_n, ag.v1_ts, ag.v1_ts_n, ag.v1_ts_ist,
         ag.v1_spot, ag.v1_spot_n, ag.v1_net_in5, ag.v1_abs_in5,
         ag.legs_with_gamma, ag.legs_removed, ag.v1_abs_at_removed,
         pk.v1_peak_strike, coalesce(pkt.v1_peak_ties, 0) AS v1_peak_ties,
         ps.v1_pos_strike, coalesce(pst.v1_pos_ties, 0) AS v1_pos_ties
  FROM ag
  LEFT JOIN pk ON pk.run_id = ag.run_id
  LEFT JOIN pkt ON pkt.run_id = ag.run_id
  LEFT JOIN ps ON ps.run_id = ag.run_id
  LEFT JOIN pst ON pst.run_id = ag.run_id
) t;
