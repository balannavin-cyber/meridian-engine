\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Futures probe on fyers_futures_bars_1m. __SYM__ underlying (NIFTY|SENSEX),
-- __D__ IST trade date. ONE statement, (tag, payload) UNION ALL, tagged like qG.
-- Readable by merdian_ro only because of the operator's 2026-11-20 grant + policy.
--
-- THE ALIGNMENT IS NOT ASSUMED. q14 measured this table's session running 03:45 to
-- 09:59 in the stored clock, which READS LIKE true UTC (09:15-15:29 IST) and so differs
-- from the IST-clock-labelled-as-+00:00 convention of the hist_* tables. Bars here are
-- labelled at second :00, not :59. Rather than pick a reading, this probe returns the
-- +/-120 s neighbourhood of BOTH candidate instants for each sampled IST minute:
--     reading 'UTC'       -- IST minus 5h30m: 10:00->04:30, 12:30->07:00, 15:00->09:30
--     reading 'IST_LABEL' -- the stored clock read as IST: 10:00, 12:30, 15:00
-- Both are reported side by side with their signed offsets, so whichever reading is
-- correct shows up as the one carrying bars, and a reading that carries none is a
-- measured absence rather than an assumption.
--
-- NOTHING FROM THIS TABLE IS USED until the alignment is settled offline, by comparing
-- the Fyers close against hist_future_bars_1m close for NIFTY on the same minutes at
-- shifts of 0, +5h30m and one minute either side. This probe only supplies the rows for
-- that comparison.
--
-- EVERY TIMESTAMP BOUND IS A LITERAL. An earlier draft derived the window bounds from a
-- VALUES CTE; the planner then could not use the ts histogram and fell back to
-- DEFAULT_INEQ_SEL, reporting 48,628 rows for a 4-minute window (and 2,188 for the same
-- predicate elsewhere in the same plan -- two inconsistent guesses for one window, which
-- is what showed neither was a real selectivity). With literals the planner estimates
-- from statistics, as it already did for H3's literal-bounded window.
--
-- Several contracts exist at each minute, so EVERY row in each window is returned, never
-- one per minute, and expiry_date is carried on each so the contracts can be told apart.
-- fut_dte is expiry_date minus the IST trade date __D__ -- the FUTURES time to expiry,
-- which is the denominator basis_implied_r needs, never the option's.
--
-- Keyed on (underlying, ts) throughout, the leading pair of
-- fyers_futures_bars_1m_underlying_ts_idx.
SELECT tag, payload FROM (
  -- ---------- H1: every row within +/-120 s of each candidate instant ----------
  SELECT 'H1' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '10:00' AS tname, 'UTC' AS reading,
           extract(epoch FROM (f.ts - timestamptz '__D__ 04:30:00+00')) AS off_sec,
           to_char(f.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS ts_stored_clock,
           f.symbol, f.expiry_date::text AS expiry_date,
           (f.expiry_date - date '__D__') AS fut_dte,
           f.close::float8 AS close, f.volume, f.oi
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = '__SYM__'
       AND f.ts >= timestamptz '__D__ 04:28:00+00'
       AND f.ts <= timestamptz '__D__ 04:32:00+00'
  ) t
  UNION ALL
  SELECT 'H1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '12:30' AS tname, 'UTC' AS reading,
           extract(epoch FROM (f.ts - timestamptz '__D__ 07:00:00+00')) AS off_sec,
           to_char(f.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS ts_stored_clock,
           f.symbol, f.expiry_date::text AS expiry_date,
           (f.expiry_date - date '__D__') AS fut_dte,
           f.close::float8 AS close, f.volume, f.oi
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = '__SYM__'
       AND f.ts >= timestamptz '__D__ 06:58:00+00'
       AND f.ts <= timestamptz '__D__ 07:02:00+00'
  ) t
  UNION ALL
  SELECT 'H1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '15:00' AS tname, 'UTC' AS reading,
           extract(epoch FROM (f.ts - timestamptz '__D__ 09:30:00+00')) AS off_sec,
           to_char(f.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS ts_stored_clock,
           f.symbol, f.expiry_date::text AS expiry_date,
           (f.expiry_date - date '__D__') AS fut_dte,
           f.close::float8 AS close, f.volume, f.oi
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = '__SYM__'
       AND f.ts >= timestamptz '__D__ 09:28:00+00'
       AND f.ts <= timestamptz '__D__ 09:32:00+00'
  ) t
  UNION ALL
  SELECT 'H1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '10:00' AS tname, 'IST_LABEL' AS reading,
           extract(epoch FROM (f.ts - timestamptz '__D__ 10:00:00+00')) AS off_sec,
           to_char(f.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS ts_stored_clock,
           f.symbol, f.expiry_date::text AS expiry_date,
           (f.expiry_date - date '__D__') AS fut_dte,
           f.close::float8 AS close, f.volume, f.oi
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = '__SYM__'
       AND f.ts >= timestamptz '__D__ 09:58:00+00'
       AND f.ts <= timestamptz '__D__ 10:02:00+00'
  ) t
  UNION ALL
  SELECT 'H1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '12:30' AS tname, 'IST_LABEL' AS reading,
           extract(epoch FROM (f.ts - timestamptz '__D__ 12:30:00+00')) AS off_sec,
           to_char(f.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS ts_stored_clock,
           f.symbol, f.expiry_date::text AS expiry_date,
           (f.expiry_date - date '__D__') AS fut_dte,
           f.close::float8 AS close, f.volume, f.oi
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = '__SYM__'
       AND f.ts >= timestamptz '__D__ 12:28:00+00'
       AND f.ts <= timestamptz '__D__ 12:32:00+00'
  ) t
  UNION ALL
  SELECT 'H1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '15:00' AS tname, 'IST_LABEL' AS reading,
           extract(epoch FROM (f.ts - timestamptz '__D__ 15:00:00+00')) AS off_sec,
           to_char(f.ts AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS ts_stored_clock,
           f.symbol, f.expiry_date::text AS expiry_date,
           (f.expiry_date - date '__D__') AS fut_dte,
           f.close::float8 AS close, f.volume, f.oi
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = '__SYM__'
       AND f.ts >= timestamptz '__D__ 14:58:00+00'
       AND f.ts <= timestamptz '__D__ 15:02:00+00'
  ) t
  UNION ALL
  -- ---------- H2: did each candidate instant carry rows at all ----------
  -- One aggregate row per instant, so an empty window is an explicit 0 rather than
  -- inferred from H1's silence.
  SELECT 'H2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '10:00' AS tname, 'UTC' AS reading,
           count(*) AS rows_in_window, count(DISTINCT symbol) AS contracts_in_window
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 04:28:00+00'
       AND ts <= timestamptz '__D__ 04:32:00+00'
  ) t
  UNION ALL
  SELECT 'H2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '12:30' AS tname, 'UTC' AS reading,
           count(*) AS rows_in_window, count(DISTINCT symbol) AS contracts_in_window
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 06:58:00+00'
       AND ts <= timestamptz '__D__ 07:02:00+00'
  ) t
  UNION ALL
  SELECT 'H2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '15:00' AS tname, 'UTC' AS reading,
           count(*) AS rows_in_window, count(DISTINCT symbol) AS contracts_in_window
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 09:28:00+00'
       AND ts <= timestamptz '__D__ 09:32:00+00'
  ) t
  UNION ALL
  SELECT 'H2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '10:00' AS tname, 'IST_LABEL' AS reading,
           count(*) AS rows_in_window, count(DISTINCT symbol) AS contracts_in_window
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 09:58:00+00'
       AND ts <= timestamptz '__D__ 10:02:00+00'
  ) t
  UNION ALL
  SELECT 'H2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '12:30' AS tname, 'IST_LABEL' AS reading,
           count(*) AS rows_in_window, count(DISTINCT symbol) AS contracts_in_window
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 12:28:00+00'
       AND ts <= timestamptz '__D__ 12:32:00+00'
  ) t
  UNION ALL
  SELECT 'H2', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d, '15:00' AS tname, 'IST_LABEL' AS reading,
           count(*) AS rows_in_window, count(DISTINCT symbol) AS contracts_in_window
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 14:58:00+00'
       AND ts <= timestamptz '__D__ 15:02:00+00'
  ) t
  UNION ALL
  -- ---------- H3: whole-day summary, 00:00:00 to 23:59:59 UTC of __D__ ----------
  -- Full 24 h, so an IST-labelled afternoon session (which would sit at 12:00-15:30 in
  -- the stored clock) is not cut off by the window itself.
  SELECT 'H3', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS und, '__D__' AS d,
           count(*) AS rows_in_day,
           count(DISTINCT symbol) AS distinct_symbols,
           count(DISTINCT expiry_date) AS distinct_expiries,
           to_char(min(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS first_ts,
           to_char(max(ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS last_ts
      FROM fyers_futures_bars_1m
     WHERE underlying = '__SYM__'
       AND ts >= timestamptz '__D__ 00:00:00+00'
       AND ts <= timestamptz '__D__ 23:59:59+00'
  ) t
) u ORDER BY tag, payload;
