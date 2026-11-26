\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
\pset null ''
SELECT run_id::text,
       to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS ts_utc,
       expiry_date::text, dte::text, strike::text, spot::text,
       oi_call::text, oi_put::text, gamma_call::text, gamma_put::text,
       gex_cr::text
  FROM public.gex_strike_snapshots
 WHERE symbol = 'NIFTY'
   AND ts >= timestamptz '2026-11-26 00:00:00+05:30'
   AND ts <  timestamptz '2026-11-27 00:00:00+05:30'
 ORDER BY ts, expiry_date, strike;
