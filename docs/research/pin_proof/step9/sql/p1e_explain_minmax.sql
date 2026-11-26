EXPLAIN SELECT
  (SELECT min(ts) FROM public.gamma_metrics WHERE symbol='NIFTY')  AS n_mn,
  (SELECT max(ts) FROM public.gamma_metrics WHERE symbol='NIFTY')  AS n_mx,
  (SELECT min(ts) FROM public.gamma_metrics WHERE symbol='SENSEX') AS s_mn,
  (SELECT max(ts) FROM public.gamma_metrics WHERE symbol='SENSEX') AS s_mx;
