-- =====================================================================
-- 2026-09-22_s81_v_gex_strike_rank.sql
-- S81 / ENH-125 -- L12 pin conviction, RANKED leg (v_gex_strike_rank)
-- =====================================================================
--
-- WHAT THIS IS
--   Strikes of the latest run, ranked by gamma MAGNITUDE, with the sign
--   carried as an attribute rather than as the sort order. The HHI leg of
--   L12 already exists (ENH-122, v_gex_concentration); this is the other
--   half -- the distribution behind that single number. 20 output columns.
--
--   It is a READ over gex_strike_snapshots, not a new compute. Same
--   recursive symbol skip-scan and same CROSS JOIN LATERAL latest-run
--   probe as the three S79 views (ADR-021, S72 FIX 2).
--
-- WHY abs(gex_cr) AND NOT SIGNED
--   ADR-024 Amendment A: gex_cr is a per-strike NET (CE contribution minus
--   PE contribution). Its sign is driven by OI imbalance, and which side is
--   OTM flips at spot. Measured over 1,515,008 rows, call-OI-heaviness runs
--   0.34 pct at-or-below spot against 99.5 pct above on NIFTY (0.39 / 99.1
--   on SENSEX). A positive-only ranking is therefore STRUCTURALLY incapable
--   of selecting a strike below spot: "the top candidates are all above
--   spot" would merely restate "OTM calls are above spot". That is the
--   tautology Amendment A exists to record, and ranking on signed gex_cr
--   would rebuild it.
--
-- WHY THE TIE-BREAK IS NOT A FREE CHOICE
--   v_gex_concentration computes top_strike_net as
--     (array_agg(strike ORDER BY abs(gex_cr) DESC, strike))[1]
--   For strike_rank = 1 here to name the SAME strike, the tie-break must be
--   identical. Any other tie-break would let two live views disagree about
--   one strike on a tie -- a fresh TD-S79-NEW-13, manufactured by the build
--   meant to be consistent with it.
--
--   And to say it once: strike_rank = 1 EQUALS top_strike_net, and
--   share_of_abs at strike_rank = 1 EQUALS hhi_net, BY CONSTRUCTION. Same
--   table, same formula, same tie-break. A query comparing them passes
--   because it is the same arithmetic, not because either is right --
--   ADR-014 s2.5, Rule 0 clause 1. This is the fifth rediscovery of that
--   shape in this family of views (net_gex_cr in ENH-121 was the third,
--   hhi_net in ENH-122 the fourth). It is a design CONSTRAINT imposed here,
--   never a verification claimed here.
--
-- WHY NO N
--   No LIMIT, no depth constant. Depth is a display decision with no scan
--   consequence: the view is latest-run scoped, so the working set is one
--   run per symbol -- 96 rows NIFTY and 154 SENSEX on 2026-09-22, the same
--   set the sibling views already read. A constant here would be an
--   unmeasured literal; if a depth is ever wanted it belongs in
--   merdian_parameters (ADR-016), applied at the consumer.
--
--   The gex_cr <> 0 filter is NOT a bound of convenience. It keeps the
--   partial-chain hole visible (TD-S79-NEW-8): padding the tail with
--   zero-gamma strikes would produce a long run of exact ties, which is
--   worse than absent. It moves neither the share nor the HHI denominator,
--   because a zero contributes nothing to a sum or to a max.
--
-- SIGMA, AND WHAT IT INHERITS
--   Self-contained sig CTE -- the same LEFT JOIN LATERAL on
--   volatility_snapshots and the same
--     spot * atm_iv/100 * sqrt(GREATEST(dte,1)/252)
--   that v_gex_strike_walls uses. NOT a join to that view, because walls
--   applies a +/-band*sigma filter this view must not inherit: the ranking
--   has to see the whole chain, not the corridor.
--
--   Three inheritances, all deliberate, all surfaced rather than fixed
--   here, so that the two views degrade IDENTICALLY:
--
--   (a) TD-S79-NEW-1. On expiry day GREATEST(dte,1) prices a full trading
--       day, so dist_sigma is UNDERSTATED -- about 1.9x on NIFTY at 13:45
--       IST on 2026-09-22, where sigma read 215.51 with roughly 105 of 375
--       session minutes remaining. Re-deriving sigma here would put this
--       view out of step with the band that scopes v_gex_strike_walls, and
--       the fix is an ADR-009 recalibration, not a render change.
--
--   (b) TD-S78-NEW-6. volatility_snapshots silently switches expiry class
--       mid-history -- expiry_type MONTHLY on 560 NIFTY timestamps
--       2026-03-25 to 2026-04-13 and 674 SENSEX 2026-03-20 to 2026-05-27,
--       both sitting inside otherwise-weekly history. Any sigma read
--       across those windows blends two instruments.
--
--   (c) No age bound on the lateral. It takes the newest atm_iv_avg at or
--       before ts, however old that is, so dist_sigma can rest on hours- or
--       days-old IV. Staleness is SURFACED (atm_iv_used, atm_iv_age_min,
--       iv_fresh against get_parameter_num('wall.iv_floor_min'), default
--       120 minutes) but NOT enforced to absent. That is the ADR-023
--       deviation v_gex_strike_walls already records; it is carried rather
--       than silently dropped, because fail-soft must be visible in the
--       artefact it degrades.
--
--   LEFT JOIN, so a run with no resolvable ATM IV still ranks and
--   sigma / dist_sigma are NULL. NULL is a gap, never a zero.
--
-- ORDERING
--   A view body carries no ordering guarantee. Consumers MUST ORDER BY
--   strike_rank. No ORDER BY in the body, matching the S79 siblings.
--
-- COLUMN NAMED strike_rank, NOT rank
--   rank is a reserved word in SQL:2011 and shadows the rank() window
--   function this view is built with.
--
-- APPLY ORDER: Section 1 -> Section 2 -> Section 3 -> verify with Section 4.
-- RUN ONE STATEMENT AT A TIME. The Supabase SQL editor wraps a pasted
--   script in one transaction, so the weakest statement in a bundle gates
--   the strongest (S72 Section 5 took Sections 2 and 3 down with it).
--
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS, NOT COMMENTED OUT, AND THE REASON
-- IS A MEASUREMENT TAKEN AT S81 ON THE THREE S79 GEX VIEWS. sql/ and the
-- database diverged in BOTH directions at once:
--
--     layer             in sql/               in the database
--     view bodies       present               present, semantically MATCH
--     COMMENT ON VIEW   LIVE (all three)      ABSENT (all three)
--     GRANT SELECT anon COMMENTED OUT (all 3) PRESENT (all 3, exactly SELECT)
--
--   So the comments were written as runnable statements and never run,
--   while the grants were never runnable from the repo yet exist live from
--   some other path. sql/ was therefore neither a subset nor a superset of
--   live, and a rebuild from it would have produced views that are correct
--   in body, better documented than live, and ANON-INACCESSIBLE: three
--   panels at HTTP 200 with zero rows, which is the TD-S37-03 silent-
--   empty-dataset shape. ADR-025 D2 clause 4 relies on sql/ being the true
--   rebuild source. Do not comment these out, and run the whole file.
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_rank AS
WITH RECURSIVE symbols AS (
        -- Loose index scan ("skip scan") over ix_gex_strike_snap_sym_ts
        -- (symbol, ts DESC). Symbols are DERIVED, not a literal list: the
        -- shipped pin/accel views carry VALUES ('NIFTY'),('SENSEX') in the
        -- body, so a third symbol renders nothing, silently (TD-S72-NEW-3).
        -- This view does not inherit that hazard and does not pay for it:
        -- SELECT DISTINCT symbol is a full scan, the same cost shape S72
        -- FIX 2 removed. O(distinct symbols) index seeks instead.
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
     ), scoped AS (
        SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte,
               g.strike, g.spot, g.gex_cr
          FROM gex_strike_snapshots g
          JOIN latest_run lr
            ON g.symbol = lr.symbol AND g.run_id = lr.run_id
     ), run_hdr AS (
        -- n_strikes counts everything stored for the run; n_ranked counts
        -- what actually contributes. The gap IS the TD-S79-NEW-8 hole and
        -- is carried on every row rather than left to be inferred.
        SELECT run_id, symbol, expiry_date,
               max(ts)   AS ts,
               max(dte)  AS dte,
               max(spot) AS spot,
               count(*)                            AS n_strikes,
               count(*) FILTER (WHERE gex_cr <> 0) AS n_ranked,
               COALESCE(get_parameter_num('wall.iv_floor_min'), 120) AS iv_floor_min
          FROM scoped
         GROUP BY run_id, symbol, expiry_date
     ), sig AS (
        -- LEFT JOIN LATERAL, not CROSS: a run with no resolvable ATM IV
        -- must still rank, with NULL sigma and NULL dist_sigma. A CROSS
        -- JOIN would drop it and the view would go quietly empty.
        SELECT h.run_id, h.symbol, h.expiry_date, h.ts, h.dte, h.spot,
               h.n_strikes, h.n_ranked, h.iv_floor_min,
               v.atm_iv_avg AS atm_iv,
               (h.spot * v.atm_iv_avg::numeric / 100.0
                       * sqrt(GREATEST(h.dte, 1)::numeric / 252.0))::numeric AS sigma,
               (EXTRACT(epoch FROM (h.ts - v.ts)) / 60.0)::numeric           AS atm_iv_age_min
          FROM run_hdr h
          LEFT JOIN LATERAL (
               SELECT vs.ts, vs.atm_iv_avg
                 FROM volatility_snapshots vs
                WHERE vs.symbol = h.symbol
                  AND vs.ts <= h.ts
                  AND vs.atm_iv_avg IS NOT NULL
                ORDER BY vs.ts DESC
                LIMIT 1
          ) v ON true
     ), ranked AS (
        SELECT sc.run_id, sc.symbol, sc.expiry_date, sc.strike, sc.gex_cr,
               abs(sc.gex_cr) AS abs_gex_cr,
               row_number() OVER (
                   PARTITION BY sc.run_id, sc.symbol, sc.expiry_date
                   ORDER BY abs(sc.gex_cr) DESC, sc.strike
               ) AS strike_rank,
               abs(sc.gex_cr)
                 / NULLIF(sum(abs(sc.gex_cr)) OVER (
                       PARTITION BY sc.run_id, sc.symbol, sc.expiry_date), 0)
                 AS share_of_abs,
               sum(abs(sc.gex_cr)) OVER (
                   PARTITION BY sc.run_id, sc.symbol, sc.expiry_date
                   ORDER BY abs(sc.gex_cr) DESC, sc.strike
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                 / NULLIF(sum(abs(sc.gex_cr)) OVER (
                       PARTITION BY sc.run_id, sc.symbol, sc.expiry_date), 0)
                 AS cum_share_of_abs
          FROM scoped sc
         WHERE sc.gex_cr <> 0
     )
SELECT
    r.run_id,
    r.symbol,
    r.expiry_date,
    g.ts,
    g.dte,
    g.spot,
    g.sigma,
    g.atm_iv                                  AS atm_iv_used,
    round(g.atm_iv_age_min, 1)                AS atm_iv_age_min,
    (g.atm_iv_age_min IS NOT NULL
     AND g.atm_iv_age_min <= g.iv_floor_min)   AS iv_fresh,
    r.strike_rank,
    r.strike,
    r.gex_cr,
    r.abs_gex_cr,
    -- Two explicit branches, no ELSE. gex_cr <> 0 is guaranteed upstream,
    -- so this cannot return NULL today; written this way so that if the
    -- filter is ever relaxed a zero becomes NULL rather than mislabelled
    -- AMPLIFYING. Naming the sign is the ADR-024 Amendment A remedy.
    CASE WHEN r.gex_cr > 0 THEN 'DAMPENING'
         WHEN r.gex_cr < 0 THEN 'AMPLIFYING'
    END AS side,
    r.share_of_abs,
    r.cum_share_of_abs,
    (r.strike - g.spot) / NULLIF(g.sigma, 0) AS dist_sigma,
    g.n_ranked,
    g.n_strikes
  FROM ranked r
  JOIN sig g
    ON g.run_id = r.run_id
   AND g.symbol = r.symbol
   AND g.expiry_date = r.expiry_date;


-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE, not commented out -- see header)
-- =====================================================================

COMMENT ON VIEW public.v_gex_strike_rank IS
  'S81 / ENH-125 -- L12 pin conviction, ranked leg. One row per contributing strike of the latest run per symbol (ADR-021, S72 FIX 2 lateral form), grain (run_id, symbol, expiry_date, strike). The siblings v_gex_strike_walls / v_gex_abs_exposure / v_gex_concentration are one row per RUN; this one is per STRIKE. Consumers MUST ORDER BY strike_rank -- a view body carries no ordering guarantee. No LIMIT and no depth constant: every strike with gex_cr <> 0 is ranked and the consumer chooses depth, because a depth constant here would be an unmeasured literal and belongs in merdian_parameters (ADR-016) at the consumer. RANK BASIS IS abs(gex_cr), NOT SIGNED, AND THAT IS LOAD-BEARING: per ADR-024 Amendment A gex_cr is a per-strike NET (CE contribution minus PE contribution) whose sign is driven by OI imbalance, and which side is OTM flips at spot -- measured over 1,515,008 rows, call-OI-heaviness runs 0.34 pct at-or-below spot against 99.5 pct above on NIFTY (0.39 / 99.1 SENSEX), so a positive-only ranking CANNOT select a strike below spot and would restate -OTM calls are above spot- as a finding. The sign is carried as side (DAMPENING / AMPLIFYING) instead of being smuggled into the sort order. TIE-BREAK abs(gex_cr) DESC, strike ASC IS FORCED, NOT CHOSEN: it is identical to the array_agg ordering inside v_gex_concentration.top_strike_net, so that strike_rank = 1 names the same strike. strike_rank = 1 EQUALS v_gex_concentration.top_strike_net, and share_of_abs at strike_rank = 1 EQUALS v_gex_concentration.hhi_net -- BY CONSTRUCTION, same table and same formula, so comparing them passes for the reason that it is the same arithmetic and verifies nothing (ADR-014 s2.5, Rule 0 clause 1). The gex_cr <> 0 filter moves neither denominator: a zero contributes nothing to a sum or to a max. THREE DIFFERENT STRIKE SCALARS EXIST AND THIS VIEW IS NEITHER OF THE OTHER TWO: v_gex_strike_walls.call_wall / put_wall are RAW-OI argmaxes inside a +/-band*sigma window, and gamma_metrics.max_gamma_strike is the argmax of POSITIVE gex_cr (ADR-024 Amendment A); this view ranks on gamma MAGNITUDE across the whole chain, unbanded. dist_sigma is the only distance measure -- points and percent are deliberately absent, because a board read in percent manufactures findings of one shape (TD-S79-NEW-11, ADR-024 sA4). dist_sigma INHERITS THE GREATEST(dte,1) FLOOR from the same sigma formula v_gex_strike_walls uses, so on expiry day sigma prices a full trading day and every dist_sigma is UNDERSTATED -- approximately 1.9x on NIFTY at 13:45 IST on 2026-09-22 (TD-S79-NEW-1). SIGMA ALSO INHERITS THE volatility_snapshots CAVEATS: the source is single-expiry and silently switches expiry class mid-history (TD-S78-NEW-6 -- expiry_type MONTHLY on 560 NIFTY timestamps 2026-03-25 to 2026-04-13 and 674 SENSEX 2026-03-20 to 2026-05-27, both inside otherwise-weekly history), and the lateral takes the newest row at or before ts with NO age bound. Staleness is therefore SURFACED (atm_iv_used / atm_iv_age_min / iv_fresh against get_parameter_num (-wall.iv_floor_min-), default 120 minutes) but NOT enforced to absent -- the same ADR-023 deviation v_gex_strike_walls records, carried here deliberately so the two views degrade identically. sigma resolves through a LEFT JOIN LATERAL, so a run with no resolvable ATM IV still ranks and sigma / dist_sigma are NULL: a gap, never a zero. n_ranked / n_strikes are the partial-chain denominator (TD-S79-NEW-8) and repeat down the rows, which is the cost of a per-strike grain. Also satisfies parity spec 2.5 L15 Absolute Gamma Strike (strike_rank = 1) and Large Gamma Strike ranked (strike_rank 1..N); per ADR-025 D5 that is an extension and does not count toward parity, so this object counts as L12 only. Display-only per the S37 GEX-as-context-not-gate ruling; it routes nothing.';


-- =====================================================================
-- SECTION 3 of 4 -- anon grants, security-first sequence (D.21.1)
-- Lovable grants anon ALL by default; the canonical sequence is
-- REVOKE ALL then GRANT SELECT, never policy + grant alone.
-- TWO STATEMENTS. Run them separately, in this order.
-- =====================================================================

REVOKE ALL ON public.v_gex_strike_rank FROM anon;

GRANT SELECT ON public.v_gex_strike_rank TO anon;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run separately, after 1-3)
-- =====================================================================

-- 4a -- ADR-025 D2 clause 2: run-scoped and EXPLAIN-verified.
--       Expect the recursive skip scan plus one index probe per symbol
--       under the lateral, NO Seq Scan on gex_strike_snapshots, and rows
--       read in the low hundreds rather than the low millions.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_rank;

-- 4b -- D2 clause 1: read the output. Top 5 per symbol.
--
-- SELECT symbol, strike_rank, strike, side,
--        round(gex_cr, 1)           AS gex_cr,
--        round(share_of_abs, 4)     AS share_of_abs,
--        round(cum_share_of_abs, 4) AS cum_share,
--        round(dist_sigma, 3)       AS dist_sigma,
--        round(sigma, 2)            AS sigma,
--        atm_iv_age_min, iv_fresh, n_ranked, n_strikes
--   FROM public.v_gex_strike_rank
--  WHERE strike_rank <= 5
--  ORDER BY symbol, strike_rank;

-- 4c -- anon privilege audit. Expect 7 rows, anon_has true on SELECT only.
--
-- SELECT p.privilege_type,
--        has_table_privilege('anon', 'public.v_gex_strike_rank', p.privilege_type) AS anon_has
--   FROM (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),
--                ('TRUNCATE'),('REFERENCES'),('TRIGGER')) AS p(privilege_type)
--  ORDER BY 1;

-- 4d -- comment landed. Expect one row, non-null, starting 'S81 / ENH-125'.
--
-- SELECT length(obj_description('public.v_gex_strike_rank'::regclass, 'pg_class')) AS comment_len,
--        left(obj_description('public.v_gex_strike_rank'::regclass, 'pg_class'), 30) AS starts_with;
