
WITH r AS (
  SELECT run_id, symbol, ts, expiry_date, dte, spot, net_cr, net_top_share,
         gross_band_cr, gross_top_share, gross_hhi, n_map, n_zero, n_dup_legs,
         rule_version
  FROM public.gex_run_v2
  WHERE symbol = 'NIFTY'
    AND ts >= '2026-09-30 00:00:00+05:30'::timestamptz AND ts < '2026-10-01 00:00:00+05:30'::timestamptz
), v AS (
  SELECT run_id, strike, net_cr, gross_cr, spot, in_map, in_band, gamma_strike,
         gamma_legs, oi_call, oi_put, symbol, expiry_date, ts, rule_version
  FROM public.gex_strike_v2
  WHERE symbol = 'NIFTY'
    AND ts >= '2026-09-30 00:00:00+05:30'::timestamptz AND ts < '2026-10-01 00:00:00+05:30'::timestamptz
), va AS (
  SELECT run_id,
    count(*) AS v2_n_map,
    sum(net_cr) AS v2_strike_sum,
    sum(abs(net_cr)) AS v2_abs,
    sum(net_cr * net_cr) AS v2_sq,
    max(abs(net_cr)) AS v2_maxabs,
    coalesce(sum(net_cr) FILTER (WHERE abs(strike - spot) <= 0.05 * spot), 0) AS v2_net_in5
  FROM v WHERE in_map GROUP BY run_id
), vall AS (
  SELECT run_id,
    count(*) AS n,
    count(*) FILTER (WHERE in_map) AS n_map,
    count(*) FILTER (WHERE in_band) AS n_band,
    count(*) FILTER (WHERE gamma_legs = 'both') AS n_both,
    count(*) FILTER (WHERE gamma_legs = 'call_only') AS n_call,
    count(*) FILTER (WHERE gamma_legs = 'put_only') AS n_put,
    sum(oi_call) AS s_oic, sum(oi_put) AS s_oip,
    sum(net_cr) AS s_net, sum(gross_cr) AS s_gross,
    sum(gamma_strike) AS s_gamma,
    sum(strike * net_cr) AS sk_net, sum(strike * gross_cr) AS sk_gross,
    min(symbol) AS v2_symbol, count(DISTINCT symbol) AS v2_symbol_n,
    min(expiry_date)::text AS v2_expiry_date, count(DISTINCT expiry_date) AS v2_expiry_n,
    min(ts) AS v2_ts, count(DISTINCT ts) AS v2_ts_n,
    min(rule_version) AS rv_strike, count(DISTINCT rule_version) AS rv_strike_n
  FROM v GROUP BY run_id
), rk AS (
  SELECT run_id, strike, net_cr,
    row_number() OVER (PARTITION BY run_id
        ORDER BY abs(net_cr) DESC, abs(strike - spot), strike) AS rn_abs,
    rank() OVER (PARTITION BY run_id ORDER BY abs(net_cr) DESC) AS rk_abs,
    row_number() OVER (PARTITION BY run_id
        ORDER BY net_cr DESC, abs(strike - spot), strike) AS rn_pos,
    rank() OVER (PARTITION BY run_id ORDER BY net_cr DESC) AS rk_pos
  FROM v WHERE in_map
), pk AS (
  SELECT run_id, strike AS v2_peak_strike FROM rk WHERE rn_abs = 1
), pkt AS (
  SELECT run_id, count(*) AS v2_peak_ties FROM rk WHERE rk_abs = 1 GROUP BY run_id
), ps AS (
  SELECT run_id, strike AS v2_pos_strike FROM rk WHERE rn_pos = 1 AND net_cr > 0
), pst AS (
  SELECT run_id, count(*) AS v2_pos_ties FROM rk
  WHERE rk_pos = 1 AND net_cr > 0 GROUP BY run_id
)
SELECT row_to_json(t)::text AS j FROM (
  SELECT r.run_id, r.symbol, r.ts AS r_ts,
         (r.ts AT TIME ZONE 'Asia/Kolkata') AS r_ts_ist,
         r.expiry_date::text AS r_expiry_date, r.dte AS r_dte, r.spot,
         r.net_cr AS r_net_cr, r.net_top_share AS r_net_top_share,
         r.gross_band_cr AS r_gross_band_cr,
         r.gross_top_share AS r_gross_top_share, r.gross_hhi AS r_gross_hhi,
         r.n_map AS r_n_map, r.n_zero AS r_n_zero, r.n_dup_legs,
         r.rule_version AS rv_run,
         va.v2_n_map, va.v2_strike_sum, va.v2_abs, va.v2_sq, va.v2_maxabs,
         va.v2_net_in5,
         vall.n, vall.n_map, vall.n_band, vall.n_both, vall.n_call, vall.n_put,
         vall.s_oic, vall.s_oip, vall.s_net, vall.s_gross, vall.s_gamma,
         vall.sk_net, vall.sk_gross,
         vall.v2_symbol, vall.v2_symbol_n, vall.v2_expiry_date,
         vall.v2_expiry_n, vall.v2_ts, vall.v2_ts_n,
         vall.rv_strike, vall.rv_strike_n,
         pk.v2_peak_strike, coalesce(pkt.v2_peak_ties, 0) AS v2_peak_ties,
         ps.v2_pos_strike, coalesce(pst.v2_pos_ties, 0) AS v2_pos_ties
  FROM r
  LEFT JOIN va ON va.run_id = r.run_id
  LEFT JOIN vall ON vall.run_id = r.run_id
  LEFT JOIN pk ON pk.run_id = r.run_id
  LEFT JOIN pkt ON pkt.run_id = r.run_id
  LEFT JOIN ps ON ps.run_id = r.run_id
  LEFT JOIN pst ON pst.run_id = r.run_id
) t;
