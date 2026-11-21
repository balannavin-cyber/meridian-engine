-- Study D2: OI at the WALL STRIKE over the 30 minutes before the approach.
--
-- One session per run. hist_option_bars_1m is 54.8M rows / 19 GB and roq.sh
-- pins statement_timeout=30s, so the query is scoped to a single trade_date
-- with an explicit bar_ts range and an explicit strike list.
--
-- Parameters, all supplied by the driver from data/approaches_<band>.csv:
--   :nifty    instrument
--   :d        the approach session
--   :expiry   the front expiry the walls were taken from (prior session close)
--   :kcall    the call wall strike   (-1 if that side did not approach)
--   :kput     the put wall strike    (-1 if that side did not approach)
--   :t0       the first minute of the 30-minute pre-approach window
--   :t1       the approach minute itself
--
-- The window is (t0, t1] in vendor-clock minutes, i.e. the 30 bars ENDING at
-- the approach minute. t1 is the approach minute, so every row read is at or
-- before the minute the outcome starts from: no lookahead.
--
-- Two instruments per session at most: the call wall's CE leg and the put
-- wall's PE leg. The wall is a strike on ONE side, so only that side's option
-- type is read -- a call wall is a CE OI concentration, a put wall a PE one.
--
-- Returns the first and last OI in the window per leg, plus the bar count, so
-- the driver computes the change without transferring 30 rows per leg.
\pset format csv

WITH legs AS (
  SELECT b.option_type,
         b.strike,
         b.bar_ts,
         b.oi,
         first_value(b.oi) OVER w AS oi_first,
         last_value(b.oi)  OVER w AS oi_last,
         count(*)          OVER (PARTITION BY b.option_type, b.strike) AS bars,
         row_number()      OVER (PARTITION BY b.option_type, b.strike
                                 ORDER BY b.bar_ts DESC) AS rn
  FROM hist_option_bars_1m b
  WHERE b.instrument_id = :'nifty'
    AND b.trade_date    = :'d'
    AND b.expiry_date   = :'expiry'
    AND b.bar_ts >  (:'d'::date + :'t0'::time) AT TIME ZONE 'UTC'
    AND b.bar_ts <= (:'d'::date + :'t1'::time) AT TIME ZONE 'UTC'
    AND (   (b.option_type = 'CE' AND b.strike = :'kcall'::numeric)
         OR (b.option_type = 'PE' AND b.strike = :'kput'::numeric))
  WINDOW w AS (PARTITION BY b.option_type, b.strike
               ORDER BY b.bar_ts
               ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
)
SELECT :'d'          AS trade_date,
       :'t0'         AS win_from,
       :'t1'         AS approach_min,
       :'expiry'     AS expiry,
       option_type,
       strike,
       bars,
       oi_first,
       oi_last,
       (oi_last - oi_first) AS d_oi_wall_30
FROM legs
WHERE rn = 1
ORDER BY option_type, strike;
