\pset format unaligned
\pset fieldsep '|'
-- lookback_v5 PART 2: Rule 25 identity for public.v_gex_strike_walls, plus the band
-- parameters. Catalog + parameter reads only -- no hist_* relation, so no EXPLAIN gate.
--
-- W1 is the Rule 25 measurement verbatim: the length and md5 of the FULL
-- pg_get_viewdef(..., true). This is the identity; everything else is commentary.
-- W2 emits the viewdef text itself so the comparison against the sql/ file can be
-- made on disk rather than asserted.
-- W3 reads the two band parameters through get_parameter_num, the same function the
-- view itself calls (sql/2026-09-15_s79_v_gex_strike_walls.sql:114), so a NULL here is
-- the same NULL the view would see and fall back from.
SELECT 'W1' AS k, length(d)::text AS a, md5(d) AS b
  FROM (SELECT pg_get_viewdef('public.v_gex_strike_walls'::regclass, true) AS d) v;
SELECT 'W2' AS k, d AS a, '' AS b
  FROM (SELECT pg_get_viewdef('public.v_gex_strike_walls'::regclass, true) AS d) v;
SELECT 'W3' AS k,
       coalesce(get_parameter_num('wall.band.NIFTY')::text,  'NULL') AS a,
       coalesce(get_parameter_num('wall.band.SENSEX')::text, 'NULL') AS b;
