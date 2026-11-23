\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- The near-ATM blackout legs and their SIBLING at the same strike and run.
-- A blackout leg = oi > 0, ltp > 0, chain gamma = 0, and raw.greeks delta, vega and
-- theta ALL zero. Scope reproduces _q04.txt exactly: SENSEX, last 10 front-expiry runs
-- of 2026-11-19, ITM depth 0-1% (the "2_ITM_0_1" bucket, 61 legs).
-- The question: can a look-back borrow the other leg's gamma at that strike?
-- ONE statement: shared CTEs once, result sets UNION ALL'd as (tag, payload).
WITH r AS (
  SELECT symbol, run_id, expiry_date, ts,
         row_number() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-19 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
), pick AS (
  SELECT * FROM r WHERE rn <= 10 AND symbol = 'SENSEX'
), lg AS (
  SELECT p.run_id, p.ts, o.strike::float8 AS strike, upper(o.option_type) AS ot,
         o.spot::float8 AS spot, o.oi::float8 AS oi, o.ltp::float8 AS ltp,
         o.gamma::float8 AS gamma, o.iv::float8 AS iv,
         ((o.raw -> 'greeks') ->> 'delta')::float8 AS rd,
         ((o.raw -> 'greeks') ->> 'vega')::float8  AS rv,
         ((o.raw -> 'greeks') ->> 'theta')::float8 AS rt,
         CASE WHEN upper(o.option_type) = 'CE'
              THEN (o.spot::float8 - o.strike::float8) / o.spot::float8
              ELSE (o.strike::float8 - o.spot::float8) / o.spot::float8 END AS m
    FROM pick p
    JOIN option_chain_snapshots o
      ON o.run_id = p.run_id AND o.expiry_date = p.expiry_date
   WHERE o.spot IS NOT NULL AND o.spot > 0 AND o.strike > 0
), blackout AS (
  SELECT * FROM lg
   WHERE oi > 0 AND ltp > 0 AND gamma = 0
     AND rd = 0 AND rv = 0 AND rt = 0
     AND m >= 0 AND m < 0.01
), paired AS (
  SELECT b.run_id, b.ts, b.strike, b.ot AS blackout_ot, b.spot, b.m,
         b.oi AS b_oi, b.ltp AS b_ltp, b.iv AS b_iv,
         s.ot AS sib_ot, s.gamma AS sib_gamma, s.iv AS sib_iv,
         s.rd AS sib_delta, s.rv AS sib_vega, s.rt AS sib_theta,
         s.oi AS sib_oi, s.ltp AS sib_ltp,
         s.run_id IS NULL AS sib_missing
    FROM blackout b
    LEFT JOIN lg s
      ON s.run_id = b.run_id AND s.strike = b.strike AND s.ot <> b.ot
)
SELECT tag, payload FROM (
  -- AGG: the decisive counts
  SELECT 'AGG' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT count(*) AS blackout_legs,
           count(*) FILTER (WHERE sib_missing) AS sibling_absent,
           count(*) FILTER (WHERE sib_gamma > 0) AS sibling_gamma_pos,
           count(*) FILTER (WHERE sib_gamma = 0) AS sibling_gamma_zero,
           count(*) FILTER (WHERE sib_gamma = 0 AND sib_delta = 0 AND sib_vega = 0
                              AND sib_theta = 0) AS sibling_also_blackout,
           count(*) FILTER (WHERE sib_gamma = 0 AND NOT (sib_delta = 0 AND sib_vega = 0
                              AND sib_theta = 0)) AS sibling_gamma_only_zero,
           count(*) FILTER (WHERE sib_iv > 0) AS sibling_iv_pos,
           count(DISTINCT strike) AS distinct_strikes,
           count(DISTINCT run_id) AS distinct_runs,
           sum(b_oi) AS blackout_oi,
           coalesce(sum(b_oi) FILTER (WHERE sib_gamma > 0), 0) AS oi_rescuable_by_sibling
      FROM paired
  ) t
  UNION ALL
  -- DET: every blackout leg with its sibling's greeks
  SELECT 'DET', row_to_json(t)::text FROM (
    SELECT to_char(ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS ist,
           strike, blackout_ot, spot, round(m::numeric * 100, 4) AS itm_pct,
           b_oi, b_ltp, b_iv,
           sib_ot, sib_gamma, sib_iv, sib_delta, sib_vega, sib_theta, sib_oi, sib_ltp
      FROM paired
  ) t
) u ORDER BY tag, payload;
