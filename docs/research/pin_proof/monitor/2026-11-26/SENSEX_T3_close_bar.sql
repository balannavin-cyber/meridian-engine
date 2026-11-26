\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
\pset null ''
SELECT to_char(bar_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS bar_ts_utc,
       close::text
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = (SELECT id FROM public.instruments WHERE symbol = 'SENSEX')
   AND bar_ts = timestamptz '2026-11-26 09:59:00+00';
