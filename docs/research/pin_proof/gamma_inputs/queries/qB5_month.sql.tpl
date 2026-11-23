\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- B5: which calendar days of one month carry any front-expiry greeks row.
-- __IID__ instrument_id, __SYM__ symbol, __M0__ month start, __M1__ next month start.
--
-- DAY-EXISTENCE PROBE, not an aggregate: generate_series over the month's calendar
-- days, and one LATERAL ... ORDER BY bar_ts LIMIT 1 per day, so at most ONE row is
-- read per day (31 rows per month worst case). An earlier draft of this query
-- aggregated a whole month of hist_option_greeks_1m per instrument -- roughly 700k
-- rows -- which violates the EXPLAIN gate.
--
-- "front-expiry" needs no predicate: backfill_hist_greeks.py:277-286 solves ONLY
-- min(expiry_date >= trade_date) and writes nothing for any other expiry, so every
-- row in hist_option_greeks_1m is a front-expiry row by construction. A filter on
-- expiry_date would be documentation, not a restriction.
--
-- bar_ts is IST clock labelled +00:00 and is NOT converted. Both the stored
-- trade_date and the clock date of bar_ts are returned for the probed row, so a
-- disagreement between them surfaces as two different values instead of being
-- hidden by whichever column was chosen. Gamma-null counts are deliberately absent:
-- B2 covers them.
WITH d AS (
  SELECT generate_series(timestamptz '__M0__ 00:00:00+00',
                         timestamptz '__M1__ 00:00:00+00' - interval '1 day',
                         interval '1 day') AS day0
)
SELECT '__SYM__' AS sym,
       to_char(d.day0 AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS cal_day,
       (p.bar_ts IS NOT NULL) AS has_rows,
       to_char(p.bar_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS first_bar_ts,
       p.trade_date::text AS trade_date_of_row,
       to_char(p.bar_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS bar_clock_date
  FROM d
  LEFT JOIN LATERAL (
    SELECT g.trade_date, g.bar_ts
      FROM hist_option_greeks_1m g
     WHERE g.instrument_id = '__IID__'
       AND g.bar_ts >= d.day0
       AND g.bar_ts <  d.day0 + interval '1 day'
     ORDER BY g.bar_ts
     LIMIT 1
  ) p ON true;
-- No outer ORDER BY: it added a Sort node over the 31 generated days, which failed the
-- plan condition "no Sort and no Bitmap node" as literally stated. Day ordering is done
-- in analyze_partB5.py instead. The ORDER BY g.bar_ts INSIDE the LATERAL stays -- it is
-- what the index supplies for free and what makes LIMIT 1 return the day's FIRST bar.
