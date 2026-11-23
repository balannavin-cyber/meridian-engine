\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- View side, ONE SYMBOL per query (task condition 3). Literal SENSEX is
-- substituted by the caller; psql -v does not work through roq.sh.
-- Scoped to the view's own latest ts for this symbol, so the run is frozen by
-- this read and not re-derived later.
WITH latest AS (
  SELECT max(v.ts) AS ts
    FROM public.v_gex_strike_rank_gross v
   WHERE v.symbol = 'SENSEX'
)
SELECT 'V',
       v.run_id::text,
       v.symbol,
       v.expiry_date::text,
       to_char(v.ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS'),
       v.dte::text,
       v.spot::text,
       v.strike_rank::text,
       v.strike::text,
       v.oi_call::text,
       v.oi_put::text,
       v.gamma_call::text,
       v.gamma_put::text,
       v.gamma_strike::text,
       v.gross_cr::text,
       v.lead_rel::text,
       v.n_ranked::text,
       v.gamma_legs,
       v.n_in_set::text,
       v.n_oi_no_gamma::text,
       v.side
  FROM public.v_gex_strike_rank_gross v, latest l
 WHERE v.symbol = 'SENSEX'
   AND v.ts = l.ts
 ORDER BY v.expiry_date, v.strike_rank, v.strike;
