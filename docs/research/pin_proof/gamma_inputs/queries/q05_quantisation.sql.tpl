\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Quantisation test, per (__SYM__, __D__). ONE statement, (tag, payload) UNION ALL.
-- option_chain_snapshots.gamma is NUMERIC (information_schema, _q00.txt), so the
-- exact test gamma*1e5 <> round(gamma*1e5) carries no binary-rounding artefact;
-- the 1e-6 tolerance form runs beside it as a control on that specific risk.
-- A single leg whose gamma is not a multiple of 1e-5 refutes the reading that
-- the vendor rounds gamma to 5 decimal places.
WITH r AS (
  SELECT run_id, expiry_date
    FROM gamma_metrics
   WHERE symbol = '__SYM__'
     AND ts >= timestamptz '__D__ 00:00+05:30'
     AND ts <  timestamptz '__D1__ 00:00+05:30'
     AND run_id IS NOT NULL
), lg AS (
  SELECT o.gamma, o.iv, o.delta, o.vega, o.theta
    FROM r
    JOIN option_chain_snapshots o
      ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
   WHERE o.gamma > 0
), iv AS (
  SELECT o.iv
    FROM r
    JOIN option_chain_snapshots o
      ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
   WHERE o.iv > 0
)
SELECT tag, payload FROM (
  SELECT 'Q1' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d,
           count(*) AS legs_gamma_pos,
           count(DISTINCT gamma) AS distinct_gamma_day,
           count(*) FILTER (WHERE (gamma * 100000) <> round(gamma * 100000)) AS fail_exact_1e5,
           count(*) FILTER (WHERE abs(gamma * 100000 - round(gamma * 100000)) > 1e-6) AS fail_tol_1e5,
           -- resolution report, NOT a firing control: a vendor quantising to 6 dp
           -- would put its 5-dp-failing values here. Zero in both means the data
           -- is consistent with 5 dp and carries no 6-dp detail to find.
           count(*) FILTER (WHERE (gamma * 1000000) = round(gamma * 1000000)
                              AND (gamma * 100000) <> round(gamma * 100000)) AS mult_1e6_not_1e5,
           min(gamma)::text AS min_pos_gamma,
           max(gamma)::text AS max_gamma,
           count(*) FILTER (WHERE gamma = 0.00001) AS at_floor_1e5,
           count(*) FILTER (WHERE (delta * 100000) <> round(delta * 100000)) AS delta_fail_1e5,
           count(*) FILTER (WHERE (vega  * 100000) <> round(vega  * 100000)) AS vega_fail_1e5,
           count(*) FILTER (WHERE (theta * 100000) <> round(theta * 100000)) AS theta_fail_1e5
      FROM lg
  ) t
  UNION ALL
  -- Q2: the control. iv on the same runs, tested at 1e-5 and at 1e-2. A non-zero
  -- iv_fail_1e5 with the gamma count at zero is what makes the gamma test
  -- discriminating rather than vacuous; iv_fail_1e2 says whether iv is 2-dp.
  SELECT 'Q2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d,
           count(*) AS legs_iv_pos,
           count(*) FILTER (WHERE (iv * 100000) <> round(iv * 100000)) AS iv_fail_1e5,
           count(*) FILTER (WHERE (iv * 100) <> round(iv * 100)) AS iv_fail_1e2,
           count(DISTINCT iv) AS distinct_iv_day
      FROM iv
  ) t
  UNION ALL
  -- Q3: the distinct gamma values themselves, pooled and re-tested in python's
  -- Decimal so the verdict does not rest on one engine's arithmetic.
  SELECT 'Q3', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d,
           (SELECT json_agg(DISTINCT g.gamma::text) FROM lg g) AS distinct_gammas
  ) t
) u ORDER BY tag;
