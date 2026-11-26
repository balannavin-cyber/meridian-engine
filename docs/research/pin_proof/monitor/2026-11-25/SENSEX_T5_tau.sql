\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
\pset null ''
SELECT COALESCE(public.get_parameter_num('pin.tau.' || 'SENSEX'), 0.3)::text;
