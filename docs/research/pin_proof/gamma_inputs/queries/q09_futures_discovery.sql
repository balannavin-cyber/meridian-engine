\pset format unaligned
\pset fieldsep '|'
-- Discovery only: which relations could supply a futures price F for
-- basis_implied_r(F, S, T). Catalog read, no data read.
SELECT 'REL' AS k, c.relkind, n.nspname, c.relname
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'public'
   AND c.relkind IN ('r','v','m','p')
   AND (c.relname ~* 'fut' OR c.relname ~* 'basis')
 ORDER BY c.relname;
-- Any column anywhere in public that smells like a futures price or a basis.
SELECT 'COL' AS k, table_name, column_name, data_type
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND (column_name ~* 'fut' OR column_name ~* 'basis')
 ORDER BY table_name, ordinal_position;
