-- Section 7, item "SENSEX -> NIFTY": the per-strike SENSEX chain at the close,
-- for the series expiring next after the session date. ONE session per run --
-- hist_option_bars_1m is 54.8M rows / 19 GB and roq.sh pins
-- statement_timeout=30s, so anything wider than a single trade_date with an
-- explicit bar_ts predicate times out (measured 2026-11-17).
--
-- Mirrors tag B of extract_session_chain.sql, with instrument_id = SENSEX.
-- SENSEX's own futures are NOT used anywhere (section 7: vendor series unusable,
-- OI a few thousand). Only SENSEX G(E) is taken from here; F(d) stays NIFTY.
--
-- Clock: vendor clock, IST written as UTC, :59 seconds. No conversion.
-- Close: the last bar at or before 15:29:59. The 15:30 bar is never used.
-- OI from hist_option_bars_1m; iv and r_used from hist_option_greeks_1m.
\pset format csv

WITH close_ts AS (
  SELECT max(bar_ts) AS t FROM hist_option_bars_1m
  WHERE instrument_id = :'sensex' AND trade_date = :'d'
    AND bar_ts <= (:'d'::date + time '15:29:59') AT TIME ZONE 'UTC'
),
exps AS (
  SELECT min(expiry_date) FILTER (WHERE expiry_date >= :'d'::date) AS exp_on_or_after,
         min(expiry_date) FILTER (WHERE expiry_date >  :'d'::date) AS front_after
  FROM hist_option_bars_1m, close_ts
  WHERE instrument_id = :'sensex' AND trade_date = :'d' AND bar_ts = close_ts.t
)
SELECT :'d' AS trade_date,
       to_char(b.bar_ts, 'HH24:MI:SS') AS hhmmss,
       b.expiry_date::text AS expiry,
       (SELECT exp_on_or_after FROM exps)::text AS exp_on_or_after,
       b.strike,
       b.option_type,
       b.oi,
       g.iv,
       g.r_used
FROM hist_option_bars_1m b
JOIN close_ts ON b.bar_ts = close_ts.t
LEFT JOIN hist_option_greeks_1m g
  ON  g.instrument_id = b.instrument_id AND g.bar_ts = b.bar_ts
  AND g.expiry_date   = b.expiry_date   AND g.strike  = b.strike
  AND g.option_type   = b.option_type
WHERE b.instrument_id = :'sensex' AND b.trade_date = :'d'
  AND b.expiry_date = (SELECT front_after FROM exps)
ORDER BY b.strike, b.option_type;
