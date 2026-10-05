\pset pager off
\pset format csv
\pset footer off
SELECT * FROM public.option_chain_snapshots WHERE symbol = 'NIFTY' AND expiry_date = (SELECT min(expiry_date) FROM public.option_chain_snapshots WHERE symbol = 'NIFTY' AND expiry_date >= '2026-10-02' AND ts >= '2026-10-02 03:30+00' AND ts < '2026-10-02 10:30+00') AND ts >= '2026-10-02 03:30+00' AND ts < '2026-10-02 10:30+00' ORDER BY ts, strike, option_type;
