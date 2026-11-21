-- Section 7, item "synthetic forward": the put-call-parity legs needed to build
-- the forward at each M2 window boundary.
--
-- Section 7 asks for "the median over the three strikes nearest spot with both
-- legs in that minute, front expiry". The three-nearest selection is done HERE,
-- in SQL, so the per-session result is 3 rows per boundary minute (~207 rows)
-- rather than the whole front-expiry chain at 69 minutes (~8,700 rows). The
-- forward itself is computed in Python from K, C, P and r_used.
--
-- ONE session per run, for the same timeout reason as the other chain pulls.
-- Clock: vendor clock, IST written as UTC, :59 seconds. No conversion is made
-- between hist_option_bars_1m and hist_spot_bars_1m -- they are joined on
-- bar_ts directly (codified zero shift, .claude/rules/data-access.md, S61).
\pset format csv

WITH bounds AS (
  SELECT generate_series((:'d'::date + time '09:20:59') AT TIME ZONE 'UTC',
                         (:'d'::date + time '15:00:59') AT TIME ZONE 'UTC',
                         interval '5 min') AS t
),
close_ts AS (
  SELECT max(bar_ts) AS t FROM hist_option_bars_1m
  WHERE instrument_id = :'nifty' AND trade_date = :'d'
    AND bar_ts <= (:'d'::date + time '15:29:59') AT TIME ZONE 'UTC'
),
exps AS (
  SELECT min(expiry_date) FILTER (WHERE expiry_date > :'d'::date) AS front_after
  FROM hist_option_bars_1m, close_ts
  WHERE instrument_id = :'nifty' AND trade_date = :'d' AND bar_ts = close_ts.t
),
sp AS (
  SELECT bar_ts, close AS spot
  FROM hist_spot_bars_1m
  WHERE instrument_id = :'nifty' AND trade_date = :'d'
),
legs AS (
  -- one row per (minute, strike) carrying both legs, where both exist
  SELECT b.bar_ts,
         b.strike,
         max(b.close) FILTER (WHERE b.option_type = 'CE') AS c,
         max(b.close) FILTER (WHERE b.option_type = 'PE') AS p,
         max(g.r_used)                                     AS r_used
  FROM hist_option_bars_1m b
  JOIN bounds ON b.bar_ts = bounds.t
  LEFT JOIN hist_option_greeks_1m g
    ON  g.instrument_id = b.instrument_id AND g.bar_ts = b.bar_ts
    AND g.expiry_date   = b.expiry_date   AND g.strike  = b.strike
    AND g.option_type   = b.option_type
  WHERE b.instrument_id = :'nifty' AND b.trade_date = :'d'
    AND b.expiry_date = (SELECT front_after FROM exps)
  GROUP BY b.bar_ts, b.strike
),
ranked AS (
  SELECT l.bar_ts, l.strike, l.c, l.p, l.r_used, sp.spot,
         row_number() OVER (PARTITION BY l.bar_ts
                            ORDER BY abs(l.strike - sp.spot), l.strike) AS rk
  FROM legs l
  JOIN sp ON sp.bar_ts = l.bar_ts
  WHERE l.c IS NOT NULL AND l.p IS NOT NULL
)
SELECT :'d' AS trade_date,
       to_char(bar_ts, 'HH24:MI:SS') AS hhmmss,
       (SELECT front_after FROM exps)::text AS expiry,
       strike, c, p, r_used, spot, rk
FROM ranked
WHERE rk <= 3
ORDER BY bar_ts, rk;
