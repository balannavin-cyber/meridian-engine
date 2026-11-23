\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- Task condition 1: the view's latest run_id must not have changed between the
-- view read and the independent read. ONE SYMBOL per query (condition 3).
-- Each symbol's run_id is compared with its OWN frozen run_id, so the two
-- symbols need not come from one execution. More than one row for a symbol =
-- stop and report.
-- Literal __SYM__ substituted by the caller.
SELECT DISTINCT 'REFREEZE', v.symbol, v.run_id::text,
       to_char(v.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS')
  FROM public.v_gex_strike_rank_gross v
 WHERE v.symbol = '__SYM__';
