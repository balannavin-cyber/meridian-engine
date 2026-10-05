\pset pager off
\pset format csv
\pset footer off
SELECT * FROM public.option_chain_snapshots WHERE symbol = 'SENSEX' AND expiry_date = (SELECT min(expiry_date) FROM public.option_chain_snapshots WHERE symbol = 'SENSEX' AND expiry_date >= '2026-08-27' AND ts >= '2026-08-27 03:30+00' AND ts < '2026-08-27 10:30+00') AND ts >= '2026-08-27 03:30+00' AND ts < '2026-08-27 10:30+00' ORDER BY ts, strike, option_type;
