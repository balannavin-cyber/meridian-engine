
WITH a AS (
  SELECT run_id, strike, gex_cr::double precision AS x, spot
  FROM public.gex_strike_snapshots
  WHERE symbol = 'NIFTY'
    AND ts >= '2026-10-28 00:00:00+05:30'::timestamptz AND ts < '2026-10-29 00:00:00+05:30'::timestamptz
), b AS (
  SELECT run_id, strike, net_cr AS y, spot
  FROM public.gex_strike_v2
  WHERE symbol = 'NIFTY'
    AND ts >= '2026-10-28 00:00:00+05:30'::timestamptz AND ts < '2026-10-29 00:00:00+05:30'::timestamptz
    AND in_map
), u AS (
  SELECT coalesce(a.run_id, b.run_id) AS run_id,
         coalesce(a.strike, b.strike) AS strike,
         coalesce(a.spot, b.spot) AS spot,
         a.x AS x, b.y AS y,
         coalesce(a.x, 0::double precision) AS xv,
         coalesce(b.y, 0::double precision) AS yv
  FROM a FULL OUTER JOIN b ON a.run_id = b.run_id AND a.strike = b.strike
)
SELECT row_to_json(t)::text AS j FROM (
  SELECT run_id,
    count(*) AS x_n_union,
    count(*) FILTER (WHERE x IS NOT NULL AND y IS NOT NULL) AS x_n_both,
    count(*) FILTER (WHERE y IS NULL) AS x_n_v1_only,
    count(*) FILTER (WHERE x IS NULL) AS x_n_v2_only,
    count(*) FILTER (WHERE sign(xv) <> sign(yv)) AS x_n_sign,
    count(*) FILTER (WHERE xv <> 0 AND yv <> 0 AND sign(xv) <> sign(yv)) AS x_n_sign_nz,
    count(*) FILTER (WHERE xv = 0 AND yv <> 0) AS x_n_v1z_v2nz,
    count(*) FILTER (WHERE xv <> 0 AND yv = 0) AS x_n_v1nz_v2z,
    sum(abs(yv - xv)) AS x_w_num,
    sum(abs(xv)) AS x_w_den,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot) AS x5_n_union,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND x IS NOT NULL AND y IS NOT NULL) AS x5_n_both,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot AND y IS NULL) AS x5_n_v1_only,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot AND x IS NULL) AS x5_n_v2_only,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND sign(xv) <> sign(yv)) AS x5_n_sign,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND xv <> 0 AND yv <> 0 AND sign(xv) <> sign(yv)) AS x5_n_sign_nz,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND xv = 0 AND yv <> 0) AS x5_n_v1z_v2nz,
    count(*) FILTER (WHERE abs(strike - spot) <= 0.05 * spot
                       AND xv <> 0 AND yv = 0) AS x5_n_v1nz_v2z,
    coalesce(sum(abs(yv - xv)) FILTER (
        WHERE abs(strike - spot) <= 0.05 * spot), 0) AS x5_w_num,
    coalesce(sum(abs(xv)) FILTER (
        WHERE abs(strike - spot) <= 0.05 * spot), 0) AS x5_w_den
  FROM u GROUP BY run_id
) t;
