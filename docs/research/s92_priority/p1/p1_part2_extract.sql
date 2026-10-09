-- P1 level test — Part 2: per-session extract. READ-ONLY. THIS QUERY RETURNS OUTCOMES (hi, lo).
-- Run only after Part 3 (the replay check) has returned zero rows, and only once this file and
-- p1_score.py are committed. Pre-registration: docs/research/s92_priority/P1_level_test_prereg_2026-10-09.md
-- (git hash-object 7a708a64c4bb73f0712a6d6e78f92a5d411a8ece). Eligibility CTEs are Part 1b verbatim
-- (plus run_id carried in cls). Output: one row per (symbol, session, anchor); export as JSON.
WITH cal AS (
    SELECT tc.trade_date AS session_date
      FROM trading_calendar tc
     WHERE tc.trade_date BETWEEN DATE '2026-05-25' AND DATE '2026-10-08'
       AND tc.is_open
), grid AS (
    SELECT s.symbol, c.session_date
      FROM (VALUES ('NIFTY'), ('SENSEX')) s(symbol) CROSS JOIN cal c
), t0 AS (                       -- first run with ts in [09:15, 10:15) IST  (§3, §4.2)
    SELECT g.symbol, g.session_date, r.run_id, r.ts AS t0
      FROM grid g
      LEFT JOIN LATERAL (
           SELECT x.run_id, x.ts
             FROM gex_strike_snapshots x
            WHERE x.symbol = g.symbol
              AND x.ts >= (g.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata'
              AND x.ts <  (g.session_date + TIME '10:15') AT TIME ZONE 'Asia/Kolkata'
            ORDER BY x.ts
            LIMIT 1) r ON true
), runrows AS (
    SELECT t.symbol, t.session_date, x.expiry_date, x.strike, x.spot
      FROM t0 t
      JOIN gex_strike_snapshots x
        ON x.symbol = t.symbol AND x.run_id = t.run_id
       AND x.ts >= t.t0 AND x.ts < t.t0 + interval '5 minutes'
), hdr AS (
    SELECT symbol, session_date,
           count(DISTINCT spot)        AS n_spot,      -- §6.4
           count(DISTINCT expiry_date) AS n_expiry     -- §6.5
      FROM runrows GROUP BY 1, 2
), stp AS (                      -- §6.3 grid step, front expiry
    SELECT symbol, session_date, min(d) AS step
      FROM (SELECT r.symbol, r.session_date,
                   r.strike - lag(r.strike) OVER (PARTITION BY r.symbol, r.session_date ORDER BY r.strike) AS d
              FROM runrows r
             WHERE r.expiry_date = (SELECT min(r2.expiry_date) FROM runrows r2
                                     WHERE r2.symbol = r.symbol AND r2.session_date = r.session_date
                                       AND r2.expiry_date >= r.session_date)) q
     WHERE d > 0 GROUP BY 1, 2
), iv AS (                       -- §4.3 latest atm_iv_avg <= t0
    SELECT t.symbol, t.session_date, v.ts AS iv_ts
      FROM t0 t
      LEFT JOIN LATERAL (
           SELECT vs.ts FROM volatility_snapshots vs
            WHERE vs.symbol = t.symbol AND vs.ts <= t.t0 AND vs.atm_iv_avg IS NOT NULL
            ORDER BY vs.ts DESC LIMIT 1) v ON true
), mins AS (                     -- §4.4 minute COUNT only, (t0, 15:15) IST
    SELECT t.symbol, t.session_date, count(DISTINCT date_trunc('minute', m.ts)) AS n_minutes
      FROM t0 t
      JOIN market_spot_snapshots m
        ON m.symbol = t.symbol AND m.spot IS NOT NULL
       AND m.ts > t.t0
       AND m.ts < (t.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata'
     GROUP BY 1, 2
), cls AS (
    SELECT t.symbol, t.session_date, t.run_id, t.t0, h.n_spot, h.n_expiry, s.step,
           round((EXTRACT(epoch FROM (t.t0 - i.iv_ts)) / 60.0)::numeric, 1) AS iv_age_min,
           COALESCE(mn.n_minutes, 0) AS n_minutes,
           CASE WHEN t.run_id IS NULL THEN 'no_t0_run'
                WHEN i.iv_ts IS NULL
                  OR (i.iv_ts AT TIME ZONE 'Asia/Kolkata')::date <> t.session_date THEN 'no_same_day_iv'
                WHEN COALESCE(mn.n_minutes, 0) < 300 THEN 'lt_300_min'
           END AS drop_reason
      FROM t0 t
      LEFT JOIN hdr  h  USING (symbol, session_date)
      LEFT JOIN stp  s  USING (symbol, session_date)
      LEFT JOIN iv   i  USING (symbol, session_date)
      LEFT JOIN mins mn USING (symbol, session_date)
), el AS (
    SELECT c.*,
           CASE WHEN c.drop_reason IS NULL THEN
                row_number() OVER (PARTITION BY c.symbol, (c.drop_reason IS NULL) ORDER BY c.session_date) END AS sess_ix,
           floor(0.67 * count(*) FILTER (WHERE c.drop_reason IS NULL) OVER (PARTITION BY c.symbol))::int AS n_cal
      FROM cls c
)
, anchors AS (                   -- t0 (primary) and the 10:15 run (§5.9, descriptive)
    SELECT e.symbol, e.session_date, e.sess_ix, e.n_cal, 't0'::text AS anchor, e.run_id, e.t0 AS ats
      FROM el e WHERE e.drop_reason IS NULL
    UNION ALL
    SELECT e.symbol, e.session_date, e.sess_ix, e.n_cal, 't1015', r.run_id, r.ts
      FROM el e
      CROSS JOIN LATERAL (
           SELECT x.run_id, x.ts FROM gex_strike_snapshots x
            WHERE x.symbol = e.symbol
              AND x.ts >= (e.session_date + TIME '10:15') AT TIME ZONE 'Asia/Kolkata'
              AND x.ts <  (e.session_date + TIME '11:15') AT TIME ZONE 'Asia/Kolkata'
            ORDER BY x.ts LIMIT 1) r
     WHERE e.drop_reason IS NULL
), arows AS (                    -- the anchor run's rows, front expiry
    SELECT a.symbol, a.session_date, a.anchor, x.expiry_date, x.dte, x.strike, x.spot,
           x.oi_call, x.oi_put, x.gex_cr
      FROM anchors a
      JOIN gex_strike_snapshots x
        ON x.symbol = a.symbol AND x.run_id = a.run_id
       AND x.ts >= a.ats AND x.ts < a.ats + interval '5 minutes'
     WHERE x.expiry_date = (SELECT min(x2.expiry_date) FROM gex_strike_snapshots x2
                             WHERE x2.symbol = a.symbol AND x2.run_id = a.run_id
                               AND x2.ts >= a.ats AND x2.ts < a.ats + interval '5 minutes'
                               AND x2.expiry_date >= a.session_date)
), ahdr AS (
    SELECT a.symbol, a.session_date, a.anchor, a.sess_ix, a.n_cal, a.ats,
           max(r.spot) AS s0, max(r.dte) AS dte, max(r.expiry_date) AS expiry_date
      FROM anchors a JOIN arows r USING (symbol, session_date, anchor)
     GROUP BY 1, 2, 3, 4, 5, 6
), astep AS (
    SELECT symbol, session_date, anchor, min(d) AS step
      FROM (SELECT symbol, session_date, anchor,
                   strike - lag(strike) OVER (PARTITION BY symbol, session_date, anchor ORDER BY strike) AS d
              FROM arows) q
     WHERE d > 0 GROUP BY 1, 2, 3
), asig AS (                     -- §3 walls rule as of the anchor; §5.3 one-day sigma
    SELECT h.*, st.step, v.atm_iv_avg AS iv0,
           round((EXTRACT(epoch FROM (h.ats - v.ts)) / 60.0)::numeric, 1) AS iv_age_min,
           COALESCE(get_parameter_num('wall.band.' || h.symbol, h.ats), 1.5) AS band,
           h.s0 * v.atm_iv_avg::numeric / 100.0 * sqrt(GREATEST(h.dte, 1)::numeric / 252.0) AS sigma_w,
           h.s0 * v.atm_iv_avg::numeric / 100.0 / sqrt(252.0)                             AS sigma_d
      FROM ahdr h
      JOIN astep st USING (symbol, session_date, anchor)
      LEFT JOIN LATERAL (
           SELECT vs.ts, vs.atm_iv_avg FROM volatility_snapshots vs
            WHERE vs.symbol = h.symbol AND vs.ts <= h.ats AND vs.atm_iv_avg IS NOT NULL
            ORDER BY vs.ts DESC LIMIT 1) v ON true
), walls AS (                    -- raw-OI argmax inside band*sigma_w (ENH-120); strike breaks exact ties
    SELECT g.symbol, g.session_date, g.anchor,
           (array_agg(r.strike ORDER BY r.oi_call DESC, r.strike) FILTER (WHERE r.oi_call > 0))[1] AS cw,
           (array_agg(r.strike ORDER BY r.oi_put  DESC, r.strike) FILTER (WHERE r.oi_put  > 0))[1] AS pw
      FROM asig g JOIN arows r USING (symbol, session_date, anchor)
     WHERE g.sigma_w > 0 AND abs(r.strike - g.s0) <= g.band * g.sigma_w
     GROUP BY 1, 2, 3
), ldr AS (                     -- top 3 by |gex_cr|; ties: nearer spot, then lower strike (§3)
    SELECT symbol, session_date, anchor,
           (array_agg(strike ORDER BY rk))[1] AS l1,
           (array_agg(strike ORDER BY rk))[2] AS l2,
           (array_agg(strike ORDER BY rk))[3] AS l3,
           count(*) FILTER (WHERE tie_at_3) AS ties_at_rank3
      FROM (SELECT r.symbol, r.session_date, r.anchor, r.strike,
                   row_number() OVER w AS rk,
                   (abs(r.gex_cr) = lead(abs(r.gex_cr)) OVER w AND row_number() OVER w = 3) AS tie_at_3
              FROM arows r JOIN asig g USING (symbol, session_date, anchor)
             WHERE r.gex_cr <> 0
            WINDOW w AS (PARTITION BY r.symbol, r.session_date, r.anchor
                         ORDER BY abs(r.gex_cr) DESC, abs(r.strike - g.s0), r.strike)) q
     WHERE rk <= 4
     GROUP BY 1, 2, 3
), path AS (                     -- §5.2 deduped minute path, (anchor, 15:15) IST
    SELECT a.symbol, a.session_date, a.anchor, m.spot,
           row_number() OVER (
               PARTITION BY a.symbol, a.session_date, a.anchor, date_trunc('minute', m.ts)
               ORDER BY CASE m.source_table WHEN 'dhan_charts_intraday' THEN 0
                                            WHEN 'dhan_idx_i'           THEN 1 ELSE 2 END,
                        m.ts DESC) AS rk
      FROM anchors a
      JOIN market_spot_snapshots m
        ON m.symbol = a.symbol AND m.spot IS NOT NULL
       AND m.ts > a.ats
       AND m.ts < (a.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata'
), hl AS (
    SELECT symbol, session_date, anchor, max(spot) AS hi, min(spot) AS lo, count(*) AS n_min
      FROM path WHERE rk = 1 GROUP BY 1, 2, 3
)
SELECT g.symbol, g.session_date, g.anchor, g.sess_ix, g.n_cal,
       to_char(g.ats AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ats_ist,
       g.expiry_date, g.dte, g.step, g.s0, g.iv0, g.iv_age_min, g.band,
       round(g.sigma_w, 2) AS sigma_w, round(g.sigma_d, 2) AS sigma_d,
       w.cw, w.pw, l.l1, l.l2, l.l3, l.ties_at_rank3,
       h.hi, h.lo, h.n_min
  FROM asig g
  LEFT JOIN walls w USING (symbol, session_date, anchor)
  LEFT JOIN ldr   l USING (symbol, session_date, anchor)
  LEFT JOIN hl    h USING (symbol, session_date, anchor)
 ORDER BY g.symbol, g.anchor, g.session_date;
