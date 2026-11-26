\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
\pset null ''
SELECT id::text, symbol, strike_step::text, timezone
  FROM public.instruments
 WHERE symbol = 'SENSEX';
