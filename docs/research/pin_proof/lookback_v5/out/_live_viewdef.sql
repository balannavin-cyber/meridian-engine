 WITH RECURSIVE symbols AS (
         SELECT ( SELECT min(g_1.symbol) AS min
                   FROM gex_strike_snapshots g_1) AS symbol
        UNION ALL
         SELECT ( SELECT min(g_1.symbol) AS min
                   FROM gex_strike_snapshots g_1
                  WHERE g_1.symbol > s.symbol) AS min
           FROM symbols s
          WHERE s.symbol IS NOT NULL
        ), latest_run AS (
         SELECT s.symbol,
            lr.run_id,
            lr.ts
           FROM symbols s
             CROSS JOIN LATERAL ( SELECT g_1.run_id,
                    g_1.ts
                   FROM gex_strike_snapshots g_1
                  WHERE g_1.symbol = s.symbol
                  ORDER BY g_1.ts DESC
                 LIMIT 1) lr
          WHERE s.symbol IS NOT NULL
        ), scoped AS (
         SELECT g_1.run_id,
            g_1.symbol,
            g_1.ts,
            g_1.expiry_date,
            g_1.dte,
            g_1.strike,
            g_1.spot,
            g_1.oi_call,
            g_1.oi_put
           FROM gex_strike_snapshots g_1
             JOIN latest_run lr ON g_1.symbol = lr.symbol AND g_1.run_id = lr.run_id
        ), run_hdr AS (
         SELECT scoped.run_id,
            scoped.symbol,
            scoped.expiry_date,
            max(scoped.ts) AS ts,
            max(scoped.dte) AS dte,
            max(scoped.spot) AS spot,
            COALESCE(get_parameter_num('wall.band.'::text || scoped.symbol), 1.5) AS band,
            COALESCE(get_parameter_num('wall.iv_floor_min'::text), 120::numeric) AS iv_floor_min
           FROM scoped
          GROUP BY scoped.run_id, scoped.symbol, scoped.expiry_date
        ), sig AS (
         SELECT h.run_id,
            h.symbol,
            h.expiry_date,
            h.ts,
            h.dte,
            h.spot,
            h.band,
            h.iv_floor_min,
            v.ts AS atm_iv_ts,
            v.atm_iv_avg AS atm_iv,
            h.spot * v.atm_iv_avg / 100.0 * sqrt(GREATEST(h.dte, 1)::numeric / 252.0) AS sigma,
            EXTRACT(epoch FROM h.ts - v.ts) / 60.0 AS atm_iv_age_min
           FROM run_hdr h
             LEFT JOIN LATERAL ( SELECT vs.ts,
                    vs.atm_iv_avg
                   FROM volatility_snapshots vs
                  WHERE vs.symbol = h.symbol AND vs.ts <= h.ts AND vs.atm_iv_avg IS NOT NULL
                  ORDER BY vs.ts DESC
                 LIMIT 1) v ON true
        ), eligible AS (
         SELECT sc.run_id,
            sc.symbol,
            sc.expiry_date,
            sc.strike,
            sc.oi_call,
            sc.oi_put
           FROM scoped sc
             JOIN sig g_1 ON g_1.run_id = sc.run_id AND g_1.symbol = sc.symbol AND g_1.expiry_date = sc.expiry_date
          WHERE g_1.sigma IS NOT NULL AND g_1.sigma > 0::numeric AND abs(sc.strike - g_1.spot) <= (g_1.band * g_1.sigma)
        ), walls AS (
         SELECT eligible.run_id,
            eligible.symbol,
            eligible.expiry_date,
            (array_agg(eligible.strike ORDER BY eligible.oi_put DESC) FILTER (WHERE eligible.oi_put > 0))[1] AS put_wall,
            (array_agg(eligible.strike ORDER BY eligible.oi_call DESC) FILTER (WHERE eligible.oi_call > 0))[1] AS call_wall,
            max(eligible.oi_put) FILTER (WHERE eligible.oi_put > 0) AS put_wall_oi,
            max(eligible.oi_call) FILTER (WHERE eligible.oi_call > 0) AS call_wall_oi,
            count(*) AS n_eligible_strikes
           FROM eligible
          GROUP BY eligible.run_id, eligible.symbol, eligible.expiry_date
        )
 SELECT g.run_id,
    g.symbol,
    g.expiry_date,
    g.ts,
    g.dte,
    g.spot,
    g.sigma,
    g.band AS band_used,
    g.atm_iv AS atm_iv_used,
    g.atm_iv_ts,
    round(g.atm_iv_age_min, 1) AS atm_iv_age_min,
    g.iv_floor_min AS iv_floor_min_used,
    g.atm_iv_age_min IS NOT NULL AND g.atm_iv_age_min <= g.iv_floor_min AS iv_fresh,
    w.put_wall,
    w.call_wall,
    w.put_wall_oi,
    w.call_wall_oi,
    (w.put_wall - g.spot) / NULLIF(g.sigma, 0::numeric) AS put_wall_sigma,
    (w.call_wall - g.spot) / NULLIF(g.sigma, 0::numeric) AS call_wall_sigma,
    (w.call_wall - w.put_wall) / NULLIF(g.sigma, 0::numeric) AS corridor_width_sigma,
        CASE
            WHEN w.put_wall IS NULL OR w.call_wall IS NULL THEN 'UNDEFINED'::text
            WHEN g.spot >= w.put_wall AND g.spot <= w.call_wall THEN 'INSIDE'::text
            WHEN g.spot > w.call_wall THEN 'ABOVE_CEILING'::text
            ELSE 'BELOW_FLOOR'::text
        END AS corridor_state,
    COALESCE(w.n_eligible_strikes, 0::bigint) AS n_eligible_strikes
   FROM sig g
     LEFT JOIN walls w ON w.run_id = g.run_id AND w.symbol = g.symbol AND w.expiry_date = g.expiry_date;
