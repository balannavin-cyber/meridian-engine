SELECT
  (SELECT min(ts) FROM public.gamma_metrics WHERE symbol='NIFTY')  AT TIME ZONE 'Asia/Kolkata' AS n_mn,
  (SELECT max(ts) FROM public.gamma_metrics WHERE symbol='NIFTY')  AT TIME ZONE 'Asia/Kolkata' AS n_mx,
  (SELECT min(ts) FROM public.gamma_metrics WHERE symbol='SENSEX') AT TIME ZONE 'Asia/Kolkata' AS s_mn,
  (SELECT max(ts) FROM public.gamma_metrics WHERE symbol='SENSEX') AT TIME ZONE 'Asia/Kolkata' AS s_mx;
