-- S90 R2.1 golden day 2026-10-01 SENSEX — frozen input: spot. Read-only.
\pset pager off
\pset format csv
\pset footer off
SELECT * FROM public.market_spot_snapshots WHERE symbol = 'SENSEX' AND ts >= '2026-10-01 03:30+00' AND ts < '2026-10-01 10:30+00' ORDER BY ts, source_table;
