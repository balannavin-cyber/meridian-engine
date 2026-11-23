\pset format unaligned
\pset fieldsep '|'
-- Schema + indexes for the candidate futures price sources, before any data read.
SELECT 'COL' AS k, table_name, ordinal_position, column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name IN ('hist_future_bars_1m','historical_index_futures_1m',
                      'fyers_futures_bars_1m','hist_basis_context',
                      'index_futures_snapshots')
 ORDER BY table_name, ordinal_position;
SELECT 'IDX' AS k, tablename, indexdef
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND tablename IN ('hist_future_bars_1m','historical_index_futures_1m',
                     'fyers_futures_bars_1m','hist_basis_context',
                     'index_futures_snapshots')
 ORDER BY tablename, indexname;
