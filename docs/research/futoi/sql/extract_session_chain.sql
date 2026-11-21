-- Per-session chain extraction. ONE session per run: hist_option_bars_1m is
-- 54.8M rows / 19 GB and roq.sh pins statement_timeout=30s, so anything scoped
-- wider than a single trade_date with an explicit bar_ts predicate times out
-- (measured 2026-11-17: month scope = timeout, session scope = 2.5-3.7 s).
--
-- Emits two tagged result sets:
--   A  one row per M2 window-start boundary: net and gross gamma*OI, front expiry
--   B  one row per strike of the front expiry at the session close (M1 G(E), C4)
--
-- Clock: vendor clock, IST written as UTC, :59 seconds. No conversion (section 2).
-- Close: the last bar at or before 15:29:59; the 15:30 bar is never used.
-- gamma, iv and r_used come from hist_option_greeks_1m; OI from hist_option_bars_1m.
-- The vendor iv/delta/gamma columns on hist_option_bars_1m are NOT used -- measured
-- 0 of 433 populated (Part 0 step 2), so section 2's "vendor delta is not used" is
-- moot: it does not exist for this era.
\pset format csv

-- the session's close bar, and the two expiry scopes
WITH close_ts AS (
  SELECT max(bar_ts) AS t FROM hist_option_bars_1m
  WHERE instrument_id = :'nifty' AND trade_date = :'d'
    AND bar_ts <= (:'d'::date + time '15:29:59') AT TIME ZONE 'UTC'
),
exps AS (
  SELECT min(expiry_date) FILTER (WHERE expiry_date >= :'d'::date) AS exp_on_or_after,
         min(expiry_date) FILTER (WHERE expiry_date >  :'d'::date) AS front_after
  FROM hist_option_bars_1m, close_ts
  WHERE instrument_id = :'nifty' AND trade_date = :'d' AND bar_ts = close_ts.t
),
bounds AS (
  SELECT generate_series((:'d'::date + time '09:20:59') AT TIME ZONE 'UTC',
                         (:'d'::date + time '15:00:59') AT TIME ZONE 'UTC',
                         interval '5 min') AS t
)
SELECT 'A' AS tag, :'d' AS trade_date,
       to_char(b.bar_ts,'HH24:MI:SS') AS hhmmss,
       (SELECT front_after FROM exps)::text AS expiry,
       (SELECT exp_on_or_after FROM exps)::text AS exp_on_or_after,
       count(*) AS legs,
       count(g.gamma) AS legs_solved,
       sum(CASE WHEN b.option_type='CE' THEN 1 ELSE -1 END * g.gamma * b.oi) AS net_gamma_oi,
       sum(g.gamma * b.oi) AS gross_gamma_oi,
       NULL::numeric AS strike, NULL::text AS option_type, NULL::numeric AS oi,
       NULL::numeric AS iv, NULL::numeric AS r_used
FROM hist_option_bars_1m b
JOIN bounds ON b.bar_ts = bounds.t
LEFT JOIN hist_option_greeks_1m g
  ON g.instrument_id=b.instrument_id AND g.bar_ts=b.bar_ts AND g.expiry_date=b.expiry_date
 AND g.strike=b.strike AND g.option_type=b.option_type
WHERE b.instrument_id = :'nifty' AND b.trade_date = :'d'
  AND b.expiry_date = (SELECT front_after FROM exps)
GROUP BY b.bar_ts

UNION ALL

SELECT 'B', :'d', to_char(b.bar_ts,'HH24:MI:SS'),
       b.expiry_date::text, (SELECT exp_on_or_after FROM exps)::text,
       1, (g.gamma IS NOT NULL)::int,
       NULL, NULL,
       b.strike, b.option_type, b.oi, g.iv, g.r_used
FROM hist_option_bars_1m b
JOIN close_ts ON b.bar_ts = close_ts.t
LEFT JOIN hist_option_greeks_1m g
  ON g.instrument_id=b.instrument_id AND g.bar_ts=b.bar_ts AND g.expiry_date=b.expiry_date
 AND g.strike=b.strike AND g.option_type=b.option_type
WHERE b.instrument_id = :'nifty' AND b.trade_date = :'d'
  AND b.expiry_date = (SELECT front_after FROM exps)

ORDER BY 1, 3, 10, 11;
