\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
\pset null ''
SELECT run_id::text,
       to_char(ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS') AS ts_utc,
       expiry_date::text, dte::text, spot::text,
       pin_leader_strike::text, session_gate_state
  FROM public.gex_cycle_history
 WHERE symbol = 'SENSEX'
   AND ts >= timestamptz '2026-11-26 00:00:00+05:30'
   AND ts <  timestamptz '2026-11-27 00:00:00+05:30'
 ORDER BY ts, expiry_date;
