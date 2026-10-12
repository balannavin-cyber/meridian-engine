-- P3b T4 (S96-H): the p3b_sweep read body as a plain query over every run of 2026-10-09 (), for costing and
-- real-volume counts through bin/roq.sh. Read-only: no p3b table is read or written. Generated from p3b_core.sql.
WITH p3b_cand AS MATERIALIZED (
    SELECT g.symbol, g.expiry_date, g.run_id, min(g.ts) AS ts
    FROM public.gex_strike_snapshots g
    WHERE g.ts >= '2026-10-09 03:30+00'::timestamptz AND g.ts < '2026-10-09 10:30+00'::timestamptz
    GROUP BY g.symbol, g.expiry_date, g.run_id),
  gs AS (
    SELECT g.symbol, g.expiry_date, g.run_id, c.ts, g.strike::float8 AS k, g.spot::float8 AS s,
           g.gex_cr::float8 AS gex, g.oi_call::numeric AS oi_call, g.oi_put::numeric AS oi_put
    FROM gex_strike_snapshots g JOIN p3b_cand c USING (symbol, expiry_date, run_id)
    -- ts bounds let the planner use the ts index instead of scanning the table for run_id
    WHERE g.ts BETWEEN '2026-10-09 03:30+00'::timestamptz AND '2026-10-09 10:30+00'::timestamptz + interval '15 minutes'),
  leg AS (
    SELECT o.symbol, o.expiry_date, o.run_id, o.strike::float8 AS k, upper(o.option_type) AS ot,
           coalesce(o.gamma::float8, 0) AS gamma, coalesce(o.oi::numeric, 0) AS oi,
           o.bid::float8 AS bid, o.ask::float8 AS ask, o.spot::float8 AS s
    FROM option_chain_snapshots o JOIN p3b_cand c USING (symbol, expiry_date, run_id)
    WHERE o.ts BETWEEN '2026-10-09 03:30+00'::timestamptz - interval '15 minutes' AND '2026-10-09 10:30+00'::timestamptz + interval '15 minutes'),
  -- I2 / I3 per strike
  st AS (
    SELECT gs.symbol, gs.expiry_date, gs.run_id, gs.ts, gs.k, gs.gex, gs.oi_call, gs.oi_put,
           count(l.k) AS n_legs,
           coalesce(sum(CASE
             WHEN l.gamma = 0 OR l.oi <= 0 OR gs.s <= 0 THEN 0
             WHEN gs.k > 0 AND abs(gs.k - gs.s) / gs.s > 0.05 AND abs(l.gamma) > 5e-5 THEN 0
             ELSE l.gamma * l.oi::float8 * gs.s * gs.s / 1e7 * CASE WHEN l.ot = 'PE' THEN -1 ELSE 1 END END), 0) AS rc,
           coalesce(sum(trunc(l.oi)) FILTER (WHERE l.ot = 'CE'), 0) AS oc,
           coalesce(sum(trunc(l.oi)) FILTER (WHERE l.ot = 'PE'), 0) AS op
    FROM gs LEFT JOIN leg l ON l.symbol = gs.symbol AND l.expiry_date = gs.expiry_date AND l.run_id = gs.run_id AND l.k = gs.k
    GROUP BY gs.symbol, gs.expiry_date, gs.run_id, gs.ts, gs.k, gs.gex, gs.oi_call, gs.oi_put),
  st2 AS (
    SELECT *, abs(rc - gex) AS d2, (abs(rc - gex) > 1e-6 + 1e-9 * abs(gex)) AS f2,
           greatest(abs(oc - trunc(oi_call)), abs(op - trunc(oi_put)))::float8 AS d3,
           (oc <> trunc(oi_call) OR op <> trunc(oi_put)) AS f3
    FROM st WHERE n_legs > 0),
  -- per run aggregates for I1 / I4 / I5
  run AS (
    SELECT c.symbol, c.expiry_date, c.run_id, c.ts,
           (SELECT sum(gex) FROM gs WHERE gs.symbol = c.symbol AND gs.expiry_date = c.expiry_date AND gs.run_id = c.run_id) AS tot,
           (SELECT max(abs(gex)) / nullif(sum(abs(gex)), 0) FROM gs WHERE gs.symbol = c.symbol AND gs.expiry_date = c.expiry_date AND gs.run_id = c.run_id) AS top1,
           m.net_gex::float8 AS net_gex, m.gamma_concentration::float8 AS conc, m.flip_level::float8 AS fl,
           (m.run_id IS NOT NULL) AS has_gm
    FROM p3b_cand c
    LEFT JOIN LATERAL (SELECT * FROM gamma_metrics x
                       WHERE x.symbol = c.symbol AND x.expiry_date = c.expiry_date AND x.run_id = c.run_id
                       ORDER BY x.ts DESC LIMIT 1) m ON true),
  cum AS (
    SELECT symbol, expiry_date, run_id, k,
           sum(gex) OVER w_up AS up, sum(gex) OVER w_dn AS dn
    FROM gs
    WINDOW w_up AS (PARTITION BY symbol, expiry_date, run_id ORDER BY k ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
           w_dn AS (PARTITION BY symbol, expiry_date, run_id ORDER BY k ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING)),
  cum2 AS (
    SELECT *, lead(k) OVER p AS k1, lead(up) OVER p AS up1, lead(dn) OVER p AS dn1
    FROM cum WINDOW p AS (PARTITION BY symbol, expiry_date, run_id ORDER BY k)),
  i5 AS (
    SELECT r.symbol, r.expiry_date, r.run_id,
           coalesce(bool_or(c.k <= r.fl AND r.fl <= c.k1 AND (c.up > 0) <> (c.up1 > 0)), false) AS asc_ok,
           coalesce(bool_or(c.k <= r.fl AND r.fl <= c.k1 AND (c.dn > 0) <> (c.dn1 > 0)), false) AS desc_ok
    FROM run r JOIN cum2 c USING (symbol, expiry_date, run_id)
    WHERE r.fl IS NOT NULL AND c.k1 IS NOT NULL
    GROUP BY r.symbol, r.expiry_date, r.run_id),
  -- I6 per strike: exactly one CE and one PE, all of bid/ask/spot > 0
  pc AS (
    SELECT symbol, expiry_date, run_id, k,
           count(*) FILTER (WHERE ot = 'CE') AS nce, count(*) FILTER (WHERE ot = 'PE') AS npe,
           max(bid) FILTER (WHERE ot = 'CE') AS cb, max(ask) FILTER (WHERE ot = 'CE') AS ca,
           max(bid) FILTER (WHERE ot = 'PE') AS pb, max(ask) FILTER (WHERE ot = 'PE') AS pa,
           max(s)   FILTER (WHERE ot = 'CE') AS s
    FROM leg GROUP BY symbol, expiry_date, run_id, k),
  pc2 AS (
    SELECT symbol, expiry_date, run_id,
           count(*) AS n, count(*) FILTER (WHERE abs((cb + ca) / 2 - (pb + pa) / 2 - (s - k)) > (ca - cb) / 2 + (pa - pb) / 2) AS outside
    FROM pc WHERE nce = 1 AND npe = 1 AND cb > 0 AND ca > 0 AND pb > 0 AND pa > 0 AND s > 0
    GROUP BY symbol, expiry_date, run_id),
  out AS (
    -- I1
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I1' AS check_id,
           CASE WHEN NOT r.has_gm THEN 'NOT_COMPUTED' WHEN abs(r.tot - r.net_gex) > 0.01 THEN 'FAIL' ELSE 'OK' END AS status,
           CASE WHEN r.has_gm THEN 1 ELSE 0 END AS n_checked,
           CASE WHEN r.has_gm AND abs(r.tot - r.net_gex) > 0.01 THEN 1 ELSE 0 END AS n_fail,
           CASE WHEN r.has_gm THEN abs(r.tot - r.net_gex) END AS max_abs_diff,
           CASE WHEN r.has_gm THEN jsonb_build_object('sum_gex_cr', r.tot, 'net_gex', r.net_gex)
                ELSE jsonb_build_object('reason', 'no gamma_metrics row') END AS detail
    FROM run r
    UNION ALL
    -- I4
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I4',
           CASE WHEN NOT r.has_gm OR r.conc IS NULL OR r.top1 IS NULL THEN 'NOT_COMPUTED'
                WHEN abs(r.top1 - r.conc) > 1e-6 THEN 'FAIL' ELSE 'OK' END,
           CASE WHEN r.has_gm AND r.conc IS NOT NULL AND r.top1 IS NOT NULL THEN 1 ELSE 0 END,
           CASE WHEN r.has_gm AND r.conc IS NOT NULL AND r.top1 IS NOT NULL AND abs(r.top1 - r.conc) > 1e-6 THEN 1 ELSE 0 END,
           abs(r.top1 - r.conc),
           CASE WHEN NOT r.has_gm THEN jsonb_build_object('reason', 'no gamma_metrics row')
                WHEN r.conc IS NULL THEN jsonb_build_object('reason', 'gamma_concentration null')
                WHEN r.top1 IS NULL THEN jsonb_build_object('reason', 'sum |gex| = 0')
                ELSE jsonb_build_object('top1_share', r.top1, 'gamma_concentration', r.conc) END
    FROM run r
    UNION ALL
    -- I2 and I3
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, x.check_id,
           CASE WHEN coalesce(a.n, 0) = 0 THEN 'NOT_COMPUTED'
                WHEN (CASE x.check_id WHEN 'I2' THEN a.f2 ELSE a.f3 END) > 0 THEN 'FAIL' ELSE 'OK' END,
           coalesce(a.n, 0),
           coalesce(CASE x.check_id WHEN 'I2' THEN a.f2 ELSE a.f3 END, 0),
           CASE x.check_id WHEN 'I2' THEN a.d2 ELSE a.d3 END,
           CASE WHEN coalesce(a.n, 0) = 0 THEN jsonb_build_object('reason', 'no chain rows at any strike')
                ELSE jsonb_build_object('strikes_without_chain', a.no_chain,
                       'first_fails', CASE x.check_id WHEN 'I2' THEN a.ff2 ELSE a.ff3 END) END
    FROM run r
    CROSS JOIN (VALUES ('I2'), ('I3')) x(check_id)
    LEFT JOIN LATERAL (
      SELECT count(*) AS n,
             count(*) FILTER (WHERE f2) AS f2, count(*) FILTER (WHERE f3) AS f3,
             max(d2) AS d2, max(d3) AS d3,
             (SELECT count(*) FROM st s0 WHERE s0.symbol = r.symbol AND s0.expiry_date = r.expiry_date AND s0.run_id = r.run_id AND s0.n_legs = 0) AS no_chain,
             to_jsonb((array_agg(jsonb_build_object('k', k, 'stored', gex, 'recompute', rc) ORDER BY d2 DESC) FILTER (WHERE f2))[1:5]) AS ff2,
             to_jsonb((array_agg(jsonb_build_object('k', k, 'oi_call', oi_call, 'chain_ce', oc, 'oi_put', oi_put, 'chain_pe', op) ORDER BY d3 DESC) FILTER (WHERE f3))[1:5]) AS ff3
      FROM st2 WHERE st2.symbol = r.symbol AND st2.expiry_date = r.expiry_date AND st2.run_id = r.run_id) a ON true
    UNION ALL
    -- I5 descriptive
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I5',
           CASE WHEN r.fl IS NULL THEN 'NOT_COMPUTED' ELSE 'INFO' END,
           CASE WHEN r.fl IS NULL THEN 0 ELSE 1 END, NULL, NULL,
           CASE WHEN r.fl IS NULL THEN jsonb_build_object('reason', 'flip_level null')
                ELSE jsonb_build_object('flip_level', r.fl, 'ascending_ok', coalesce(i.asc_ok, false), 'descending_ok', coalesce(i.desc_ok, false)) END
    FROM run r LEFT JOIN i5 i USING (symbol, expiry_date, run_id)
    UNION ALL
    -- I6 descriptive
    SELECT r.symbol, r.expiry_date, r.run_id, r.ts, 'I6',
           CASE WHEN coalesce(p.n, 0) = 0 THEN 'NOT_COMPUTED' ELSE 'INFO' END,
           coalesce(p.n, 0), coalesce(p.outside, 0), NULL,
           CASE WHEN coalesce(p.n, 0) = 0 THEN jsonb_build_object('reason', 'no strike with one CE and one PE with bid, ask and spot > 0')
                ELSE jsonb_build_object('outside_spreads', p.outside) END
    FROM run r LEFT JOIN pc2 p USING (symbol, expiry_date, run_id))
SELECT symbol, check_id, count(DISTINCT run_id) AS runs, sum(n_checked) AS n_checked, coalesce(sum(n_fail), 0) AS n_fail,
       count(*) FILTER (WHERE status = 'OK') AS ok, count(*) FILTER (WHERE status = 'FAIL') AS fail,
       count(*) FILTER (WHERE status = 'NOT_COMPUTED') AS not_computed, count(*) FILTER (WHERE status = 'INFO') AS info,
       max(max_abs_diff) AS max_abs_diff
FROM out GROUP BY symbol, check_id ORDER BY symbol, check_id;
