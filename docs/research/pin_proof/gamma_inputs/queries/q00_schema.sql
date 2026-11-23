\pset format unaligned
\pset fieldsep '|'
SELECT 'COL' AS k, table_name, ordinal_position, column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema='public'
   AND table_name IN ('hist_option_greeks_1m','hist_option_bars_1m','hist_spot_bars_1m',
                      'option_chain_snapshots','gex_strike_snapshots','gamma_metrics',
                      'instruments','hist_greeks_backfill_log')
 ORDER BY table_name, ordinal_position;
SELECT 'IDX' AS k, tablename, indexname, indexdef
  FROM pg_indexes
 WHERE schemaname='public'
   AND tablename IN ('hist_option_greeks_1m','hist_option_bars_1m','hist_spot_bars_1m',
                     'option_chain_snapshots','gex_strike_snapshots','gamma_metrics',
                     'instruments')
 ORDER BY tablename, indexname;
