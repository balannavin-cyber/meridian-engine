\pset format aligned
-- q10 returned NO rows from information_schema.columns for fyers_futures_bars_1m while
-- pg_indexes returned its indexes. information_schema.columns is filtered to relations
-- the current role holds a privilege on; pg_indexes is not. So the asymmetry suggests
-- merdian_ro cannot read this table -- MEASURE it rather than infer it.
--
-- pg_attribute is not privilege-filtered, so the column list comes from there. No data
-- row of fyers_futures_bars_1m is read by this query.
SELECT current_user AS role_now,
       has_table_privilege('public.fyers_futures_bars_1m', 'SELECT') AS can_select_now,
       has_table_privilege('merdian_ro', 'public.fyers_futures_bars_1m', 'SELECT') AS merdian_ro_select,
       has_table_privilege('public.hist_basis_context', 'SELECT') AS can_select_basis_ctx;
SELECT a.attname AS column_name,
       format_type(a.atttypid, a.atttypmod) AS data_type,
       a.attnotnull AS not_null,
       a.attnum
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public' AND c.relname = 'fyers_futures_bars_1m'
   AND a.attnum > 0 AND NOT a.attisdropped
 ORDER BY a.attnum;
