\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Independent check for the draft view: the replay's qR_day.sql.tpl shape, RESTRICTED
-- TO ONE run_id instead of a symbol-day. Every emitted field and tag is unchanged, so
-- fix/replay/score_replay.py scores it unmodified.
-- Literal __RID__ substituted by the caller.
WITH r AS (
  SELECT g.run_id, g.expiry_date, g.ts, g.dte, g.symbol
    FROM gamma_metrics g
   WHERE g.run_id = '__RID__'
), agg AS (
  SELECT r.run_id,
         sum(o.oi) FILTER (WHERE upper(o.option_type) = 'CE') AS tot_oi_call,
         sum(o.oi) FILTER (WHERE upper(o.option_type) = 'PE') AS tot_oi_put,
         count(*) AS n_legs_chain,
         min(o.spot) FILTER (WHERE o.spot > 0) AS spot_min,
         max(o.spot) FILTER (WHERE o.spot > 0) AS spot_max
    FROM r
    JOIN option_chain_snapshots o
      ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
   GROUP BY r.run_id
)
SELECT tag, payload FROM (
  SELECT 'R0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT r.symbol AS sym,
           to_char(r.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD') AS d,
           r.run_id::text AS run_id,
           to_char(r.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS ts_ist,
           r.expiry_date::text AS expiry,
           r.dte,
           a.spot_min::text AS spot_min,
           a.spot_max::text AS spot_max,
           a.tot_oi_call::text AS tot_oi_call,
           a.tot_oi_put::text AS tot_oi_put,
           a.n_legs_chain,
           h.pin_leader_strike::text AS board_pin,
           h.call_wall_strike::text AS call_wall,
           h.put_wall_strike::text AS put_wall,
           (h.run_id IS NOT NULL) AS has_board_row
      FROM r
      JOIN agg a ON a.run_id = r.run_id
      LEFT JOIN gex_cycle_history h ON h.run_id = r.run_id
  ) t
  UNION ALL
  SELECT 'R1', row_to_json(t)::text FROM (
    SELECT r.symbol AS sym,
           to_char(r.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD') AS d,
           r.run_id::text AS run_id,
           o.strike::text AS strike,
           upper(o.option_type) AS ot,
           o.ltp::text AS ltp,
           o.oi::text AS oi,
           o.gamma::text AS gamma
      FROM r
      JOIN agg a ON a.run_id = r.run_id
      JOIN option_chain_snapshots o
        ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
     WHERE a.spot_min > 0
       AND abs(o.strike::float8 / a.spot_min::float8 - 1.0) <= 0.05
  ) t
) u;
