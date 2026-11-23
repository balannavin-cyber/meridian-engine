\pset format unaligned
\pset tuples_only on
EXPLAIN
-- Literal NIFTY substituted by the caller.
SELECT DISTINCT 'REFREEZE', v.symbol, v.run_id::text,
       to_char(v.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS')
  FROM public.v_gex_strike_rank_gross v
 WHERE v.symbol = 'NIFTY';
