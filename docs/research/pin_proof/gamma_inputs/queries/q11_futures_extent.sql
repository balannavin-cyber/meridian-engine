\pset format aligned
-- Is the zero from historical_index_futures_1m real absence, or a wrong key?
-- Checked BEFORE any absence is claimed: planner row estimates (catalog, no scan) for
-- every futures candidate, so a small table can then be enumerated safely and a large
-- one is not scanned by accident.
SELECT c.relname,
       c.relkind,
       c.reltuples::bigint AS est_rows,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       (SELECT string_agg(a.attname, ',' ORDER BY a.attnum)
          FROM pg_attribute a
         WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
           AND a.attname IN ('symbol','underlying','contract_code','security_id',
                             'instrument_id','ts','bar_ts','expiry_date')
       ) AS key_columns
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
   AND c.relname IN ('hist_future_bars_1m','historical_index_futures_1m',
                     'fyers_futures_bars_1m','hist_basis_context',
                     'index_futures_snapshots')
 ORDER BY c.reltuples DESC;
