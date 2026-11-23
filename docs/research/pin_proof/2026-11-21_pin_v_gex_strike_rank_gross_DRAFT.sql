-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql
-- =====================================================================
-- v_gex_strike_rank_gross -- the textbook (gross) pin, as a view. DRAFT.
-- Session MR-PIN2, 2026-11-21. NOT RUN. Not authorised until the operator
-- approves it; the operator runs it in the SQL editor, one statement at a
-- time. Claude does not run SQL on production.
--
-- REVISION 2 (2026-11-21, after replay v2): construction VS, not V2.
--   pin_live_replay_v2_result_2026-11-21.md: over 53 unseen days VS is on
--   the ruled pin's strike on 99.65 % (NIFTY) and 98.88 % (SENSEX) of
--   clear-lead market runs and is the only construction that met the
--   frozen rule. V2 (two vendor gammas kept apart) did not.
--
-- WHAT IT IS
--   Strikes of the latest run per symbol, within 5 % of spot, ranked on
--     gross_cr = gamma_strike * (oi_call + oi_put) * spot^2 / 1e7
--   where gamma_strike is ONE vendor gamma per strike: the mean of
--   gamma_call and gamma_put when both are > 0, the one that is > 0 when
--   the other is blank, 0 when both are blank. strike_rank = 1 is the pin
--   ruled on 2026-11-21 (ruling_pin_definition_2026-11-21.md).
--
-- WHAT IT IS NOT
--   It does not replace v_gex_strike_rank (netted, ENH-125) and nothing
--   reads it yet. The Board is unchanged. Additive; rollback is
--   DROP VIEW public.v_gex_strike_rank_gross;
--
-- CHOICES, each from the frozen replay designs
--   - Band: abs(strike/spot - 1) <= 0.05. The deep-ITM guard in gex_cr
--     acts only beyond 5 % from spot, so it never meets this band.
--   - Tie-break: larger gross_cr, then nearer to spot, then lower strike.
--   - lead_rel = (top - second) / top, the study's definition. It is NOT
--     the Board's "lead" (share points); do not mix the two.
--   - side is the strike's NET sign from gex_cr, with the existing words.
--   - Same recursive symbol skip-scan and latest-run probe as
--     sql/2026-09-22_s81_v_gex_strike_rank.sql.
--
-- KNOWN LIMITS
--   - Latest run only, like its sibling; no history.
--   - Weaker on pre-open runs (clear-lead agreement 96.9 % NIFTY, 90.8 %
--     SENSEX) and when the vendor's call/put gamma ratio is far from 1.
--   - A frozen-OI run is ranked like any other.
-- =====================================================================

-- SECTION 1 of 4 -- the view (one statement)

CREATE OR REPLACE VIEW public.v_gex_strike_rank_gross AS
WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol)
                  FROM gex_strike_snapshots g
                 WHERE g.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.run_id, lr.ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts
                 FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol
                ORDER BY g.ts DESC
                LIMIT 1
          ) lr
         WHERE s.symbol IS NOT NULL
     ), base AS (
        SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte,
               g.strike, g.spot, g.oi_call, g.oi_put,
               g.gamma_call, g.gamma_put, g.gex_cr,
               CASE WHEN COALESCE(g.gamma_call, 0) > 0 AND COALESCE(g.gamma_put, 0) > 0
                         THEN (g.gamma_call + g.gamma_put) / 2.0
                    WHEN COALESCE(g.gamma_call, 0) > 0 THEN g.gamma_call
                    WHEN COALESCE(g.gamma_put,  0) > 0 THEN g.gamma_put
                    ELSE 0
               END AS gamma_strike
          FROM gex_strike_snapshots g
          JOIN latest_run lr
            ON g.symbol = lr.symbol AND g.run_id = lr.run_id
         WHERE g.spot > 0
           AND abs(g.strike / g.spot - 1) <= 0.05
     ), scoped AS (
        SELECT b.*,
               b.gamma_strike * (COALESCE(b.oi_call, 0) + COALESCE(b.oi_put, 0))
               * (b.spot::double precision ^ 2) / 1e7 AS gross_cr
          FROM base b
     ), ranked AS (
        SELECT sc.run_id, sc.symbol, sc.ts, sc.expiry_date, sc.dte,
               sc.strike, sc.spot, sc.oi_call, sc.oi_put,
               sc.gamma_call, sc.gamma_put, sc.gamma_strike, sc.gex_cr, sc.gross_cr,
               row_number() OVER w AS strike_rank,
               sc.gross_cr / NULLIF(sum(sc.gross_cr) OVER p, 0) AS share_of_gross,
               count(*) OVER p AS n_ranked
          FROM scoped sc
         WHERE sc.gross_cr > 0
        WINDOW p AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date),
               w AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date
                     ORDER BY sc.gross_cr DESC, abs(sc.strike - sc.spot), sc.strike)
     ), hdr AS (
        SELECT run_id, symbol, expiry_date,
               max(gross_cr) FILTER (WHERE strike_rank = 1) AS top_cr,
               max(gross_cr) FILTER (WHERE strike_rank = 2) AS second_cr
          FROM ranked
         GROUP BY run_id, symbol, expiry_date
     )
SELECT r.run_id,
       r.symbol,
       r.expiry_date,
       r.ts,
       r.dte,
       r.spot,
       r.strike_rank,
       r.strike,
       r.oi_call,
       r.oi_put,
       r.gamma_call,
       r.gamma_put,
       r.gamma_strike,
       r.gross_cr,
       r.share_of_gross,
       r.gex_cr,
       CASE WHEN r.gex_cr > 0 THEN 'DAMPENING'
            WHEN r.gex_cr < 0 THEN 'AMPLIFYING'
       END AS side,
       (h.top_cr - h.second_cr) / NULLIF(h.top_cr, 0) AS lead_rel,
       r.n_ranked
  FROM ranked r
  JOIN hdr h
    ON h.run_id = r.run_id AND h.symbol = r.symbol AND h.expiry_date = r.expiry_date;


-- SECTION 2 of 4 -- comment (one statement)

COMMENT ON VIEW public.v_gex_strike_rank_gross IS
'MR-PIN2 2026-11-21 -- textbook (gross) pin, shadow. Strikes of the latest run per symbol within 5 % of spot, ranked on gross_cr = gamma_strike*(oi_call+oi_put)*spot^2/1e7, gamma_strike = mean of gamma_call and gamma_put when both > 0, else the one that is > 0, else 0; tie-break nearer to spot then lower strike. strike_rank = 1 is the pin ruled 2026-11-21 (construction VS of replay v2). lead_rel = (top - second)/top, NOT the Board lead in share points. side is the NET sign from gex_cr. Does not replace v_gex_strike_rank; nothing reads it; display-only (S37). Consumers must ORDER BY strike_rank.';


-- SECTION 3 of 4 -- privileges. THREE statements, run separately, in order.
-- New objects in public can inherit default grants; remove them first.
-- Shadow stage: the read-only research role only. marketview_ro is NOT
-- granted until a Board switch is approved.

REVOKE ALL ON public.v_gex_strike_rank_gross FROM anon;

REVOKE ALL ON public.v_gex_strike_rank_gross FROM authenticated;

GRANT SELECT ON public.v_gex_strike_rank_gross TO merdian_ro;


-- SECTION 4 of 4 -- verification (run separately, after 1-3)

-- 4a -- plan: expect index probes, no Seq Scan on gex_strike_snapshots.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_rank_gross;

-- 4b -- top 3 per symbol beside the current (netted) leader.
-- SELECT g.symbol, g.strike_rank, g.strike, g.side,
--        round(g.share_of_gross::numeric, 4) AS share_of_gross,
--        round(g.lead_rel::numeric, 4)       AS lead_rel,
--        g.oi_call, g.oi_put, g.spot, g.n_ranked,
--        (SELECT n.strike FROM public.v_gex_strike_rank n
--          WHERE n.symbol = g.symbol AND n.strike_rank = 1) AS netted_leader
--   FROM public.v_gex_strike_rank_gross g
--  WHERE g.strike_rank <= 3
--  ORDER BY g.symbol, g.strike_rank;

-- 4c -- privilege audit: expect SELECT true for merdian_ro only.
-- SELECT r.rolname,
--        has_table_privilege(r.rolname, 'public.v_gex_strike_rank_gross', 'SELECT') AS can_select
--   FROM pg_roles r
--  WHERE r.rolname IN ('anon', 'authenticated', 'marketview_ro', 'merdian_ro')
--  ORDER BY 1;

-- ROLLBACK
-- DROP VIEW public.v_gex_strike_rank_gross;
