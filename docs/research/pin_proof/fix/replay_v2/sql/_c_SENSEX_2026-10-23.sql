\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Pin live replay -- one SYMBOL-DAY per query, ONE statement, read-only, no temp table.
-- Literals SENSEX 2026-10-23 (IST date) 2026-10-24 (next IST date) substituted by the runner.
--
-- RUN SET: gamma_metrics is one row per front-expiry run_id (the S80 extra-expiry legs
-- carry their own run_id and have NO gamma_metrics row), so this join IS the
-- front-expiry filter -- the same construction Part A used
-- (gamma_inputs/queries/qA_day.sql.tpl:21-37), read not guessed.
-- Filter is on (ts, symbol) which is the leading pair of idx_gm_ts_symbol_expiry.
--
-- ts is a true timestamptz here (NOT the hist bar_ts IST-labelled-+00 family), so it IS
-- converted: `ts AT TIME ZONE 'Asia/Kolkata'` gives the IST wall clock, and the day
-- bounds are written +05:30.
--
-- SPOT: the design says spot = the first positive per-leg spot. SQL has no "first", so
-- both min and max over positive per-leg spots are returned per run; the scorer uses
-- min and reports any run where they differ, which is the control that "first" is
-- unambiguous rather than an assumption.
--
-- WALLS: taken from gex_cycle_history.call_wall_strike / put_wall_strike -- preference
-- (i), chosen from the catalog before any data was read because those columns exist
-- (ordinal 32 / 33). volatility_snapshots is therefore NOT read.
--
-- R0 one row per run: identity, spot bounds, Board pin, stored walls, and the
-- WHOLE-CHAIN OI totals the frozen-run test needs (aggregated in SQL, no strike band).
-- R1 one row per leg within +/-5 % of spot: the scoring input. strike/ltp/oi/gamma are
-- emitted as TEXT so nothing is rounded by a float8 cast.
WITH r AS (
  SELECT g.run_id, g.expiry_date, g.ts, g.dte
    FROM gamma_metrics g
   WHERE g.symbol = 'SENSEX'
     AND g.ts >= timestamptz '2026-10-23 00:00:00+05:30'
     AND g.ts <  timestamptz '2026-10-24 00:00:00+05:30'
     AND g.run_id IS NOT NULL
), agg AS (
  -- whole front-expiry chain, no strike band
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
    SELECT 'SENSEX' AS sym, '2026-10-23' AS d,
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
    SELECT 'SENSEX' AS sym, '2026-10-23' AS d,
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
