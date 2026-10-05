\pset pager off
\pset format csv
\pset footer off
SELECT * FROM public.gex_strike_snapshots WHERE symbol = 'NIFTY' AND ts >= '2026-10-02 03:30+00' AND ts < '2026-10-02 10:30+00' ORDER BY ts, strike;
