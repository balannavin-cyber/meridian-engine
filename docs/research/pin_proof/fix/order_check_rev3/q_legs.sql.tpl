\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Independent side (task condition 8): option_chain_snapshots legs for ONE
-- frozen run_id, in the shape of fix/view/qR_run.sql.tpl. gamma_metrics supplies
-- the run header. gex_strike_snapshots is NOT read here -- that is the view's
-- own source, and reading it would make this a copy rather than a check.
-- Literal __RID__ substituted by the caller.
--
-- ONE DELIBERATE DIFFERENCE from qR_run.sql.tpl, stated before the run:
-- that template applies the 5 % band in SQL (WHERE abs(o.strike/a.spot_min - 1)
-- <= 0.05). Here the band is NOT applied in SQL. The PREREG assigns the band to
-- the independent Python ("the 5 % band abs(strike/spot - 1) <= 0.05" is listed
-- among the quantities the Python rebuilds), and applying it in two places
-- invites the two from disagreeing at the boundary. Every leg of the run is
-- returned and indep.measure() makes the single cut. Nothing else in the shape
-- changes: same R0/R1 tags, same fields, same source tables.
WITH r AS (
  SELECT g.run_id, g.expiry_date, g.ts, g.dte, g.symbol
    FROM gamma_metrics g
   WHERE g.run_id = '__RID__'
), agg AS (
  SELECT r.run_id,
         count(*) AS n_legs_chain,
         min(o.spot) FILTER (WHERE o.spot > 0) AS spot_min,
         max(o.spot) FILTER (WHERE o.spot > 0) AS spot_max,
         count(DISTINCT o.spot) AS n_distinct_spot
    FROM r
    JOIN option_chain_snapshots o
      ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
   GROUP BY r.run_id
)
SELECT tag, payload FROM (
  SELECT 'R0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT r.symbol AS sym,
           r.run_id::text AS run_id,
           to_char(r.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS ts_ist,
           r.expiry_date::text AS expiry,
           r.dte,
           a.spot_min::text AS spot_min,
           a.spot_max::text AS spot_max,
           a.n_distinct_spot,
           a.n_legs_chain
      FROM r
      JOIN agg a ON a.run_id = r.run_id
  ) t
  UNION ALL
  SELECT 'R1', row_to_json(t)::text FROM (
    SELECT o.strike::text AS strike,
           upper(o.option_type) AS ot,
           o.oi::text AS oi,
           o.gamma::text AS gamma
      FROM r
      JOIN option_chain_snapshots o
        ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
  ) t
) u;
