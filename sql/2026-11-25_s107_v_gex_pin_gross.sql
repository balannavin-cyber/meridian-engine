-- =====================================================================
-- 2026-11-25_s107_v_gex_pin_gross.sql
-- S107, operator rulings of 2026-11-25 (R2, R3): the Board's Pin tile shows the gross pin.
--
-- AUTHORED, NOT APPLIED. The operator applies it in the SQL editor, one section at a time.
-- Not a capture-path change. Apply outside 08:30-15:40 IST.
--
-- WHAT. One row per symbol (per expiry of the latest run): rank 1 of
-- public.v_gex_strike_rank_gross with its share, the rank 2 strike and share, and the
-- lead in share points. It carries symbol, run_id and ts so the Board keeps its time gate.
--
-- UNITS. No Crore column is exposed, so ADR-032 needs no _1pct form.
--   pin_share, runnerup_share : fraction 0..1 of the SUM of gross_cr over strikes within
--                               5 % of spot that have gross_cr > 0, same run, symbol, expiry.
--   lead_share_pts            : (pin_share - runnerup_share) * 100. NULL when only one strike ranks.
--   These are NOT comparable with v_gex_strike_rank.share_of_abs (net, every strike of the run).
--
-- SECURITY. Owner-rights view (no security_invoker option), on purpose: the Board roles
-- (authenticated, marketview_ro) hold no grant on v_gex_strike_rank_gross or on
-- gex_strike_snapshots through it, so an invoker-rights wrapper would fail for them.
-- The wrapper exposes only the columns listed here. v_gex_strike_rank_gross keeps its own
-- grants (merdian_ro only). No grant to anon.
--
-- NOT CHANGED. v_gex_strike_rank, v_gex_strike_rank_gross, gex_cycle_history.pin_leader_strike.
--
-- ROLLBACK (one statement):  DROP VIEW public.v_gex_pin_gross;
-- =====================================================================

-- SECTION 1 of 4 -- the view (one statement)

CREATE VIEW public.v_gex_pin_gross AS
SELECT g.symbol,
       g.run_id,
       max(g.ts)             AS ts,
       g.expiry_date,
       max(g.dte)            AS dte,
       max(g.spot)           AS spot,
       max(g.strike)         FILTER (WHERE g.strike_rank = 1) AS pin_strike,
       max(g.share_of_gross) FILTER (WHERE g.strike_rank = 1) AS pin_share,
       max(g.gamma_legs)     FILTER (WHERE g.strike_rank = 1) AS pin_gamma_legs,
       max(g.strike)         FILTER (WHERE g.strike_rank = 2) AS runnerup_strike,
       max(g.share_of_gross) FILTER (WHERE g.strike_rank = 2) AS runnerup_share,
       (max(g.share_of_gross) FILTER (WHERE g.strike_rank = 1)
        - max(g.share_of_gross) FILTER (WHERE g.strike_rank = 2)) * 100 AS lead_share_pts,
       max(g.n_ranked)       AS n_ranked,
       max(g.n_in_set)       AS n_in_set,
       max(g.n_oi_no_gamma)  AS n_oi_no_gamma
  FROM public.v_gex_strike_rank_gross g
 WHERE g.strike_rank <= 2
 GROUP BY g.symbol, g.run_id, g.expiry_date;


-- SECTION 2 of 4 -- comment (one statement)

COMMENT ON VIEW public.v_gex_pin_gross IS
'S107 2026-11-25, operator rulings R2/R3 -- Board Pin = gross pin. One row per symbol (per expiry of the latest run): rank 1 of v_gex_strike_rank_gross (pin_strike, pin_share), rank 2 (runnerup_strike, runnerup_share) and lead_share_pts = (pin_share - runnerup_share) * 100, NULL when one strike ranks. Shares are fractions of the sum of gross_cr over strikes within 5 % of spot with gross_cr > 0, same run/symbol/expiry; not comparable with v_gex_strike_rank.share_of_abs. No Crore column, so no _1pct form (ADR-032). Owner-rights view by design: Board roles have no grant on the gross view underneath. Net peak, pin state and conviction are NOT here; they stay in gex_cycle_history / v_pin_board.';


-- SECTION 3 of 4 -- grants (four statements, run one at a time)

REVOKE ALL ON public.v_gex_pin_gross FROM anon;

REVOKE ALL ON public.v_gex_pin_gross FROM authenticated;

REVOKE ALL ON public.v_gex_pin_gross FROM PUBLIC;

GRANT SELECT ON public.v_gex_pin_gross TO authenticated, marketview_ro, merdian_ro;


-- SECTION 4 of 4 -- verification. Read-only. Run separately, after 1-3.
-- They are commented so that pasting the whole file runs nothing extra.

-- 4a -- rows: expect one row per symbol (NIFTY, SENSEX), pin_share in (0, 1],
--       lead_share_pts >= 0 or NULL, n_ranked >= 1.
-- SELECT symbol, run_id, ts, expiry_date, pin_strike, round(pin_share::numeric, 4) AS pin_share,
--        runnerup_strike, round(lead_share_pts::numeric, 2) AS lead_share_pts, pin_gamma_legs, n_ranked
--   FROM public.v_gex_pin_gross ORDER BY symbol;

-- 4b -- the wrapper is the gross view's rank 1, nothing else: expect 0 rows.
-- SELECT w.symbol FROM public.v_gex_pin_gross w
--   JOIN public.v_gex_strike_rank_gross g
--     ON g.symbol = w.symbol AND g.run_id = w.run_id AND g.expiry_date = w.expiry_date AND g.strike_rank = 1
--  WHERE g.strike IS DISTINCT FROM w.pin_strike OR g.share_of_gross IS DISTINCT FROM w.pin_share;

-- 4c -- grants: expect authenticated=r, marketview_ro=r, merdian_ro=r, no anon entry, reloptions NULL.
-- SELECT relname, reloptions, relacl::text FROM pg_class WHERE oid = 'public.v_gex_pin_gross'::regclass;

-- 4d -- registration read (rule 25): record all five values.
-- SELECT length(pg_get_viewdef('public.v_gex_pin_gross'::regclass)) AS len_plain,
--        md5(pg_get_viewdef('public.v_gex_pin_gross'::regclass)) AS md5_plain,
--        length(pg_get_viewdef('public.v_gex_pin_gross'::regclass, true)) AS len_pretty,
--        md5(pg_get_viewdef('public.v_gex_pin_gross'::regclass, true)) AS md5_pretty,
--        current_setting('server_version') AS pg_version;

-- 4e -- plan: expect index probes, no Seq Scan on gex_strike_snapshots.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_pin_gross;
