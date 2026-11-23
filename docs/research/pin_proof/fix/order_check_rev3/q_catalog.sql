\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Catalog first (task condition 3): the columns of revision 3 of the view, in
-- ordinal order, plus the view's own definition length and md5 so the object
-- being checked is identified by what it IS, not by a file name (CLAUDE.md
-- Rule 25). No data is read by this query.
SELECT 'COL', a.attnum::text, a.attname,
       format_type(a.atttypid, a.atttypmod)
  FROM pg_attribute a
 WHERE a.attrelid = 'public.v_gex_strike_rank_gross'::regclass
   AND a.attnum > 0
   AND NOT a.attisdropped
 ORDER BY a.attnum;
SELECT 'DEF', length(d)::text, md5(d)
  FROM (SELECT pg_get_viewdef('public.v_gex_strike_rank_gross'::regclass, true) AS d) v;
