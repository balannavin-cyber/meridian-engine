
SELECT row_to_json(t)::text AS j FROM (
  SELECT r.run_id,
         h.net_gex AS gch_net_gex,
         h.pin_leader_strike AS gch_pin_leader_strike,
         h.conc_top1_share AS gch_conc_top1_share,
         h.conc_hhi AS gch_conc_hhi,
         h.dte AS gch_dte,
         m.net_gex AS gm_net_gex,
         p.status AS v1_chain_status
  FROM public.gex_run_v2 r
  LEFT JOIN public.gex_cycle_history h
         ON h.run_id = r.run_id AND h.symbol = r.symbol
  LEFT JOIN public.gamma_metrics m
         ON m.run_id = r.run_id
  LEFT JOIN public.p3b2_invariant_checks p
         ON p.kind = 'check' AND p.check_id = 'V1'
        AND p.symbol = r.symbol AND p.expiry_date = r.expiry_date
        AND p.run_id = r.run_id
  WHERE r.symbol = 'SENSEX'
    AND r.ts >= '2026-11-03 00:00:00+05:30'::timestamptz AND r.ts < '2026-11-04 00:00:00+05:30'::timestamptz
) t;
