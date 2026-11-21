-- Part 0 step 2: information_schema for the five tables the pre-registration names.
-- Read-only. Run through bin/roq.sh as merdian_ro.
\pset format csv
SELECT table_name, ordinal_position, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('hist_future_bars_1m','hist_option_bars_1m',
                     'hist_option_greeks_1m','hist_spot_bars_1m','hist_gamma_metrics')
ORDER BY table_name, ordinal_position;
