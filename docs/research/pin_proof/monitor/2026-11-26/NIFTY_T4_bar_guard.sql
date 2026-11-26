\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
\pset null ''
SELECT to_char(min(bar_ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS first_bar,
       to_char(max(bar_ts) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS last_bar,
       count(*)::text AS n_bars
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = (SELECT id FROM public.instruments WHERE symbol = 'NIFTY')
   AND bar_ts >= timestamptz '2026-11-26 00:00:00+00'
   AND bar_ts <  timestamptz '2026-11-27 00:00:00+00';
