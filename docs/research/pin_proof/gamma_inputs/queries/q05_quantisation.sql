\pset format unaligned
\pset fieldsep '|'
-- Quantisation test, widened from one run to all front-expiry runs of
-- 2026-11-16..19. option_chain_snapshots.gamma is NUMERIC (information_schema,
-- _q00.txt), so the exact test is sound; the 1e-6 tolerance form is run beside
-- it as a control. If the two disagree the exact form was a float artefact.
-- A single leg whose gamma is not a multiple of 1e-5 refutes the reading that
-- the vendor rounds gamma to 5 decimal places.
WITH r AS (
  SELECT symbol, run_id, expiry_date
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-16 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
), lg AS (
  SELECT r.symbol, o.gamma, o.iv, o.delta, o.vega, o.theta
    FROM r
    JOIN option_chain_snapshots o
      ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
   WHERE o.gamma > 0
)
SELECT symbol,
       count(*) AS legs_gamma_pos,
       count(DISTINCT gamma) AS distinct_gamma,
       count(*) FILTER (WHERE (gamma * 100000) <> round(gamma * 100000)) AS fail_exact,
       count(*) FILTER (WHERE abs(gamma * 100000 - round(gamma * 100000)) > 1e-6) AS fail_tolerance,
       min(gamma) AS min_pos_gamma,
       max(gamma) AS max_gamma,
       count(*) FILTER (WHERE gamma = 0.00001) AS at_floor_1e5,
       count(DISTINCT delta) AS distinct_delta,
       count(*) FILTER (WHERE (delta * 100000) <> round(delta * 100000)) AS delta_fail_exact,
       count(*) FILTER (WHERE (vega * 100000) <> round(vega * 100000)) AS vega_fail_exact,
       count(*) FILTER (WHERE (theta * 100000) <> round(theta * 100000)) AS theta_fail_exact
  FROM lg GROUP BY 1 ORDER BY 1;
-- Control that the test CAN fail: iv on the same legs is NOT quantised to 5 dp
-- (ingest stores the vendor's full-precision implied_volatility). A non-zero
-- count here is what proves the test above is discriminating rather than vacuous.
WITH r AS (
  SELECT symbol, run_id, expiry_date
    FROM gamma_metrics
   WHERE ts >= timestamptz '2026-11-16 00:00+05:30'
     AND ts <  timestamptz '2026-11-20 00:00+05:30'
     AND run_id IS NOT NULL
)
SELECT r.symbol, count(*) AS legs_iv_pos,
       count(*) FILTER (WHERE (o.iv * 100000) <> round(o.iv * 100000)) AS iv_fail_exact
  FROM r
  JOIN option_chain_snapshots o
    ON o.run_id = r.run_id AND o.expiry_date = r.expiry_date
 WHERE o.iv > 0
 GROUP BY 1 ORDER BY 1;
