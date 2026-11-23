\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- MR-PIN2 step 3, STEP 0c. Read-only metadata + Rule 13 preflight.
-- Columns and indexes for the three relations the sensitivity reads, the
-- instrument ids the per-day template needs, and the contamination registry.
SELECT tag, payload FROM (
  SELECT 'C0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT table_name, ordinal_position, column_name, data_type,
           numeric_precision, numeric_scale, is_nullable
      FROM information_schema.columns
     WHERE table_schema = 'public'
       AND table_name IN ('hist_option_greeks_1m', 'hist_option_bars_1m',
                          'hist_spot_bars_1m')
  ) t
  UNION ALL
  SELECT 'C1', row_to_json(t)::text FROM (
    SELECT tablename, indexname, indexdef
      FROM pg_indexes
     WHERE schemaname = 'public'
       AND tablename IN ('hist_option_greeks_1m', 'hist_option_bars_1m',
                         'hist_spot_bars_1m')
  ) t
  UNION ALL
  SELECT 'C2', row_to_json(t)::text FROM (
    SELECT id, symbol FROM instruments WHERE symbol IN ('NIFTY', 'SENSEX')
  ) t
  UNION ALL
  SELECT 'C3', row_to_json(t)::text FROM (
    SELECT contamination_id, field_scope, contamination_start, contamination_end,
           affected_tables, symbols
      FROM public.data_contamination_ranges
  ) t
) u ORDER BY tag, payload;
