\pset pager off
\pset format csv
\pset footer off
SELECT * FROM public.gamma_metrics WHERE symbol = 'SENSEX' AND ts >= '2026-08-27 03:30+00' AND ts < '2026-08-27 10:30+00' ORDER BY ts;
