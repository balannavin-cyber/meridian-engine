-- =====================================================================
-- 2026-09-15_s79_v_gex_concentration.sql
-- S79 / ENH-122 — L12 gamma concentration (v_gex_concentration)
-- =====================================================================
--
-- WHAT THIS IS
--   Herfindahl concentration on the gamma book: how much of the total sits
--   on the single largest strike. THREE values, not one -- net, call, put.
--
--   Parity: Hedgewall carries HHI in the header beside net gamma and regime
--   ("0.412 COMPRESSED"), plus HHI CALL, HHI PUT, PERCENTILE, d1D HHI and
--   d vs MEAN in its "How sharp are the levels?" group. This is L12 in
--   docs/registers/MERDIAN_Hedgewall_Parity_Spec.md, which specs the net
--   leg only as max(abs(gex))/sum(abs(gex)). The call/put split is an
--   ADDITION, and it is justified by measurement, not by copying -- see
--   FINDING 1.
--
--   Sibling of v_gex_abs_exposure (ENH-121) and v_gex_strike_walls
--   (ENH-120): same recursive skip scan for symbols, same bounded lateral
--   for latest run (ADR-021 + S72 FIX 2), same (run_id, symbol,
--   expiry_date) grain.
--
-- =====================================================================
-- hhi_net IS gamma_metrics.gamma_concentration. IT IS NOT A SECOND NUMBER,
-- AND COMPARING THE TWO IS NOT A CHECK.
-- =====================================================================
--   compute_gamma_metrics_local.py builds strike_map via
--   build_strike_exposure_map() -- per-strike sum of signed_gamma_exposure(),
--   CE positive, PE negative -- then compute_gamma_concentration() returns
--   max(|v|)/sum(|v|) over it. build_gss_rows() writes gex_cr as THAT SAME
--   per-strike sum of THAT SAME function. So this view recomputes the stored
--   scalar by the identical formula. The three candidate divergences all
--   close to zero:
--
--     (a) the live path iterates filter_usable_option_rows (gamma != 0 and
--         oi > 0); build_gss_rows iterates raw rows. Those predicates are
--         exactly when signed_gamma_exposure returns 0.0, so the extra rows
--         add +0.0 and the per-strike totals are IDENTICAL, not merely close.
--     (b) build_gss_rows drops zero-noise strikes (no OI either side AND
--         gex_cr = 0). A zero contributes to neither max nor sum.
--     (c) build_gss_rows buckets by strike alone and stamps one scalar
--         expiry_date per run, so the table is single-expiry-per-run by
--         construction and GROUP BY expiry_date yields one group.
--
--   Therefore hhi_net = gamma_metrics.gamma_concentration BY CONSTRUCTION.
--   A query comparing them passes for the reason it is the same arithmetic,
--   not because either is right -- ADR-014 s2.5, Rule 0 clause 1. This is
--   the fourth rediscovery of that shape (net_gex in ENH-121 was the third).
--   hhi_net is carried here so a consumer gets all three legs plus the
--   bucket from one query. It verifies nothing.
--
--   This is NOT the ADR-024 sA7 max_gamma_strike shape. There, two
--   implementations of one intent disagreed on semantics. Here there is one
--   implementation, read from two places.
--
-- =====================================================================
-- MEASURED 2026-05-25 -> present
-- =====================================================================
--
--   symbol   DTE   n_runs   hhi_net  hhi_call   hhi_put   corr(call,put)
--   NIFTY      0    1,296    0.2244    0.3189    0.3204            0.711
--   NIFTY    1-2    1,082    0.1438    0.2164    0.2280            0.149
--   NIFTY     3+    3,296    0.1102    0.1713    0.1792            0.052
--   SENSEX     0    1,153    0.1480    0.2146    0.2202            0.874
--   SENSEX   1-2    2,325    0.1025    0.1532    0.1430           -0.001
--   SENSEX    3+    2,145    0.0846    0.1387    0.1433            0.424
--
--   (medians by DTE bucket)
--
-- FINDING 1 -- THE SPLIT EARNS ITS PLACE.
--   At expiry the two sides move together (0.711 NIFTY, 0.874 SENSEX);
--   away from expiry they DECOUPLE ALMOST COMPLETELY (0.149, 0.052,
--   -0.001). On most days call concentration and put concentration are
--   independent quantities, and a single combined number averages two
--   unrelated signals. Hedgewall ships three; the measurement agrees
--   independently. The split is not decoration and is not imitation.
--
-- FINDING 2 -- CONCENTRATION FALLS ~2x ACROSS DTE, SO dte_bucket IS A
--   STORED COLUMN AND ANY PERCENTILE MUST BE COMPUTED WITHIN BUCKET.
--   NIFTY 0.2244 -> 0.1438 -> 0.1102; SENSEX 0.1480 -> 0.1025 -> 0.0846.
--   A reading of 0.22 is the MEDIAN at expiry and ABOVE THE 90TH PERCENTILE
--   at 3+ DTE. Percentiling across buckets is the same class of error as
--   reading distance in percent instead of sigma (TD-S79-NEW-11).
--   dte_bucket is stored rather than derived at render time precisely so a
--   consumer cannot pool buckets by accident.
--
-- FINDING 3 -- TIER COMPARABILITY, FOR WHOEVER BUILDS THE PERCENTILE.
--   hist_gamma_metrics (2025-04 -> 2026-03) and gamma_metrics (2026-06 ->
--   now) medians agree within 9.4% NIFTY and 19.5% SENSEX, so a percentile
--   across 259 trading days is defensible. BUT live p90 exceeds hist p90 by
--   42% / 36% while p10 barely moves: the live distribution is RIGHT-SKEWED
--   relative to history, so a high reading judged against a mostly-
--   historical tail reads as MORE EXTREME THAN IT IS. And NIFTY runs ~35%
--   more concentrated than SENSEX at every quantile in both tiers -- THE
--   PERCENTILE MUST BE PER-SYMBOL, NEVER POOLED.
--
-- =====================================================================
-- THE BASIS DIFFERENCE -- SETTLED BY MEASUREMENT, DO NOT ENGINEER AROUND IT
-- =====================================================================
--   hhi_net is computed from abs(gex_cr), which carries the TD-NEW-2 Part A
--   deep-ITM guard (reject |strike-spot|/spot > 5% with |gamma| > 5e-5).
--   The split legs are computed from gamma_call*oi_call and
--   gamma_put*oi_put, which BYPASS it -- signed netting destroys the
--   per-side view, so gex_cr cannot serve the split.
--
--   That inconsistency was MEASURED, not assumed. Applying the guard
--   predicate to the split legs and comparing, largest |filtered - raw| at
--   p90:
--
--     NIFTY    0 / 1-2 / 3+ DTE   0.0001 / 0.0005 / 0.0021
--     SENSEX   0 / 1-2 / 3+ DTE   0.0000 / 0.0001 / 0.0003
--
--   Worst cell 0.0021 -- 1.2% of that cell's HHI of 0.172 -- against a
--   criterion of 0.01 FIXED BEFORE THE QUERY WAS RUN. Five of twelve cells
--   are at or below 0.0001.
--
--   RULING: ship as-is, document the difference, DO NOT BUILD FILTERED
--   CALL/PUT LEGS. A filtered leg would exist nowhere else in the system
--   and would buy a correction two orders of magnitude below the value it
--   corrects.
--
--   And it settles something that had been hedged: hhi_call 0.32 against
--   hhi_net 0.22 on NIFTY at 0 DTE is ENTIRELY THE SIGN NETTING, not partly
--   the guard. The guard contributes 0.0001 there. This was carried as
--   "partly the guard" until it was measured.
--
-- SCALE INVARIANCE.
--   HHI is a ratio of like-dimensioned sums, so any positive constant
--   multiplier cancels. gex_cr carries spot^2/1e7 (TD-NEW-3 Crore
--   convention) and the split legs do not; this CANNOT affect any of the
--   three values. Same argument S62 used to fill hist_gamma_metrics's
--   gamma_concentration column despite its unscaled 1e7 convention.
--   abs() is applied to the split legs for definitional correctness
--   (HHI is over magnitudes), not because a negative vendor gamma is
--   expected.
--
-- TYPES -- THREE VALUES, TWO TYPES. THIS BITES CONSUMERS THAT ROUND.
--   hhi_net is NUMERIC: gex_cr is numeric, so max/sum and the division stay
--   exact. hhi_call and hhi_put are DOUBLE PRECISION: gamma_call/gamma_put are
--   double precision and the product with oi_* inherits that. A consumer that
--   rounds all three uniformly hits
--       function round(double precision, integer) does not exist
--   because Postgres has no two-argument round() for float8. Cast to numeric
--   before rounding, or round only hhi_net. The types are a consequence of the
--   basis difference above and are NOT a defect to normalise away: casting
--   gex_cr to float8 to make them uniform would discard exactness on the one
--   leg that has it.
--
-- EXPLICITLY NOT IN SCOPE: the PERCENTILE, d1D HHI, and d vs MEAN.
--   Those need the 259-day cross-tier series described in FINDING 3 and are
--   a SEPARATE OBJECT. This view is latest-run scoped per ADR-021. Building
--   a percentile inside a latest-run view would require it to read history
--   it deliberately does not scan.
--
-- SCHEMA NOTE -- oi_call / oi_put / dte ARE THE LIVE NAMES. SETTLED.
--   ADR-015's 12-column list (as quoted in CLAUDE.md) names
--   oi_total_calls / oi_total_puts / source_table and omits dte. That list
--   has DRIFTED from the shipped table, and the drift is settled rather
--   than suspected -- the writer's names are confirmed from three
--   independent places:
--     (1) build_gss_rows() writes keys oi_call / oi_put / dte and never
--         writes source_table, and it is live -- a PostgREST insert naming
--         an absent column returns PGRST204;
--     (2) v_gex_strike_walls (ENH-120) uses oi_call / oi_put and is live
--         and verified in the database, equivalence gate passed;
--     (3) merdian_reference.json columns_live_s75 records the 14 live
--         columns measured from the PostgREST OpenAPI document on
--         2026-09-08, which include oi_call, oi_put and dte, and no
--         source_table.
--   This view uses those names. A Section 1 failure on an unknown column
--   would therefore be a NEW schema change since 2026-09-08, not this
--   naming question.
--
-- APPLY ORDER: Section 1 -> verify with Section 3 -> Section 2 (grants).
-- Run sections SEPARATELY: the Supabase SQL editor wraps a pasted script in
-- one transaction, so the weakest statement gates the strongest (S72
-- Section 5 took Sections 2 and 3 down with it).
-- =====================================================================


-- =====================================================================
-- SECTION 1 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_concentration AS
WITH RECURSIVE symbols AS (
        -- Loose index scan ("skip scan") over ix_gex_strike_snap_sym_ts (symbol, ts DESC).
        -- NAME VERIFIED AGAINST THE LIVE PLAN (S79): EXPLAIN shows Index Only Scan
        -- using ix_gex_strike_snap_sym_ts, one row per probe, no base-table scan.
        --
        -- WHAT THIS VIEW NEEDS FROM THE INDEX, so a dedup pass cannot break it:
        --   * symbol LEADING -- the recursive min(symbol) and
        --     min(symbol) WHERE symbol > s.symbol probes are index SEEKS only if
        --     symbol is the first column; otherwise every step degrades to a scan.
        --   * ts DESC SECOND -- the latest_run lateral is WHERE symbol = ?
        --     ORDER BY ts DESC LIMIT 1, which reads the first row under the symbol
        --     prefix and needs NO SORT only if ts DESC immediately follows symbol.
        -- The requirement is therefore (symbol, ts DESC) AS A PREFIX. A wider
        -- composite satisfies it; a differently-ordered index does not.
        --
        -- THREE INDEXES, ONE ACCESS PATH (TD-S72-NEW-4): idx_gss_symbol_ts is
        -- BYTE-IDENTICAL to ix_gex_strike_snap_sym_ts and the planner does not
        -- choose it; idx_gss_symbol_ts_strike (symbol, ts DESC, strike) is
        -- redundant against both but does carry the required prefix. Whichever
        -- survives that cleanup MUST cover (symbol, ts DESC), and EXPLAIN must be
        -- RE-RUN after any drop -- do not assume the planner falls through.
        -- Symbols are DERIVED, not a literal list: the shipped pin/accel views
        -- carry VALUES ('NIFTY'),('SENSEX') in the view body, so a third symbol
        -- renders nothing, silently (TD-S72-NEW-3 guards exactly that). This
        -- view does not inherit the hazard and does not pay for it either:
        -- SELECT DISTINCT symbol is a full scan, the same cost shape S72 FIX 2
        -- removed. O(distinct symbols) index seeks instead.
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
               g.spot, g.strike, g.gex_cr,
               -- Split legs. NOT guard-filtered -- see THE BASIS DIFFERENCE.
               -- NULL gamma_call/gamma_put propagates to NULL and is skipped
               -- by both max() and sum(), which is the correct reading: a
               -- strike with no observed call gamma contributes nothing to
               -- call concentration.
               abs(g.gamma_call * g.oi_call) AS leg_call,
               abs(g.gamma_put  * g.oi_put ) AS leg_put
          FROM gex_strike_snapshots g
          JOIN latest_run lr
            ON g.symbol = lr.symbol AND g.run_id = lr.run_id
     )
SELECT
    run_id,
    symbol,
    expiry_date,
    max(ts)   AS ts,
    max(dte)  AS dte,
    max(spot) AS spot,

    -- dte_bucket is STORED, not derived at render time (FINDING 2).
    -- NULL when dte is NULL or NEGATIVE: a negative dte is the TD-NEW-4
    -- defect shape (as-of date taken from wall clock rather than the row's
    -- timestamp) and its bucket is genuinely undefined. NULL is a gap,
    -- never a zero, and never a magic string a consumer would filter away
    -- without noticing. Section 3e counts these.
    CASE
        WHEN max(dte) IS NULL THEN NULL
        WHEN max(dte) <  0    THEN NULL
        WHEN max(dte) =  0    THEN '0'
        WHEN max(dte) <= 2    THEN '1-2'
        ELSE                       '3+'
    END AS dte_bucket,

    -- NULLIF on every denominator: a run where one side carries no usable
    -- gamma/OI at all returns NULL for that leg, never a divide-by-zero and
    -- never a spurious value. Same reasoning as ENH-120's FILTER (oi > 0).
    max(abs(gex_cr)) / NULLIF(sum(abs(gex_cr)), 0) AS hhi_net,
    max(leg_call)    / NULLIF(sum(leg_call),    0) AS hhi_call,
    max(leg_put)     / NULLIF(sum(leg_put),     0) AS hhi_put,

    -- The strike carrying max(abs(gex_cr)). NULL when that max is 0, so it
    -- agrees with hhi_net's NULL rather than returning the lowest strike in
    -- the group. Deterministic tiebreak on strike ascending.
    CASE WHEN max(abs(gex_cr)) > 0
         THEN (array_agg(strike ORDER BY abs(gex_cr) DESC, strike))[1]
    END AS top_strike_net,

    count(*)                            AS n_strikes,
    count(*) FILTER (WHERE gex_cr <> 0) AS n_contributing
  FROM scoped
 GROUP BY run_id, symbol, expiry_date;

COMMENT ON VIEW public.v_gex_concentration IS
  'S79 / ENH-122 -- L12 gamma concentration. Herfindahl max/sum on the gamma book, three legs: hhi_net over abs(gex_cr), hhi_call over abs(gamma_call*oi_call), hhi_put over abs(gamma_put*oi_put). Latest-run scoped (ADR-021, S72 FIX 2 lateral form), grain (run_id, symbol, expiry_date). THE SPLIT IS LOAD-BEARING: call and put concentration correlate 0.71-0.87 at 0 DTE but -0.00 to 0.15 away from it, so a single combined number averages two independent signals on most days. CONCENTRATION FALLS ~2x ACROSS DTE, so dte_bucket is stored and any percentile MUST be computed within bucket and per symbol -- NIFTY runs ~35 pct more concentrated than SENSEX at every quantile, and live p90 exceeds historical p90 by 36-42 pct while p10 barely moves. hhi_net IS gamma_metrics.gamma_concentration recomputed by the identical formula from the same signed_gamma_exposure() output -- comparing them passes BY CONSTRUCTION and verifies nothing (ADR-014 s2.5, Rule 0 clause 1). The split legs bypass the TD-NEW-2 deep-ITM guard because signed netting destroys the per-side view; measured effect at p90 is at most 0.0021 (1.2 pct of that cell) against a 0.01 criterion fixed before the query, so filtered legs were considered and DELIBERATELY NOT BUILT. hhi_call 0.32 vs hhi_net 0.22 at 0 DTE is entirely sign netting, not the guard. Percentile, d1D and d-vs-mean are a separate historical object, not this one.';


-- =====================================================================
-- SECTION 2 -- anon grants (security-first sequence, D.21.1)
-- Run SEPARATELY, after Section 3 verifies.
-- Lovable grants anon ALL privileges by default; the canonical sequence is
-- REVOKE ALL then GRANT SELECT, not policy + grant alone.
-- =====================================================================

-- REVOKE ALL ON public.v_gex_concentration FROM anon;
-- GRANT SELECT ON public.v_gex_concentration TO anon;


-- =====================================================================
-- SECTION 3 -- verification
--
-- Each query below is labelled CAN FIRE or CANNOT FIRE. Rule 0 clause 0:
-- a check that cannot fail for the reason it names is documentation, not
-- verification. Both are worth running; only one kind is evidence.
-- =====================================================================

-- 3a. SHAPE. CAN FIRE.
--     Expect exactly one row per symbol. More than one means
--     gex_strike_snapshots holds two expiry_date values under one run_id --
--     which build_gss_rows cannot produce (it stamps a single scalar), so a
--     second row is a broken writer contract or a run_id collision. Values
--     should sit near the FINDING-2 medians for the reported bucket.
--
-- SELECT symbol, expiry_date, ts, dte, dte_bucket, spot,
--        hhi_net, hhi_call, hhi_put, top_strike_net,
--        n_strikes, n_contributing,
--        round(100.0 * n_contributing / NULLIF(n_strikes,0), 1) AS pct_contributing
--   FROM public.v_gex_concentration
--  ORDER BY symbol;

-- 3b. hhi_net BETWEEN 0 AND 1. CANNOT FIRE -- this is documentation.
--     max(abs(x)) <= sum(abs(x)) holds for any non-empty set of reals, and
--     NULL gex_cr values are skipped by max() and sum() alike, so there is
--     no input -- including a corrupted one -- that produces a value outside
--     (0, 1]. Recorded because the brief asked for it and because the
--     honest label is worth more than the query.
--
-- SELECT symbol, hhi_net, hhi_call, hhi_put
--   FROM public.v_gex_concentration
--  WHERE hhi_net NOT BETWEEN 0 AND 1
--     OR hhi_call NOT BETWEEN 0 AND 1
--     OR hhi_put  NOT BETWEEN 0 AND 1;

-- 3c. n_contributing <= n_strikes. CANNOT FIRE -- documentation.
--     A FILTER count over the same group is bounded by count(*) by
--     definition. Retained for parity with the ENH-121 file, which carries
--     the same query under the same limitation.
--
-- SELECT symbol, n_strikes, n_contributing
--   FROM public.v_gex_concentration
--  WHERE n_contributing > n_strikes;

-- 3d. LEG AVAILABILITY. CAN FIRE.
--     hhi_call or hhi_put NULL means that side carried no usable
--     gamma*OI anywhere in the run -- a real vendor-data defect (the whole
--     call or put side missing gamma), not a quiet zero. Expect ZERO rows
--     on a normal session; a hit is worth chasing upstream to
--     option_chain_snapshots before trusting hhi_net for that run.
--
-- SELECT symbol, dte, n_strikes, n_contributing, hhi_net, hhi_call, hhi_put
--   FROM public.v_gex_concentration
--  WHERE hhi_call IS NULL OR hhi_put IS NULL;

-- 3e. BUCKET DETERMINACY. CAN FIRE.
--     dte_bucket NULL means dte was NULL or NEGATIVE. Negative dte is the
--     TD-NEW-4 shape (as-of date from wall clock instead of the row's ts)
--     and it reached this table once before. Expect ZERO rows.
--
-- SELECT symbol, ts, expiry_date, dte, dte_bucket
--   FROM public.v_gex_concentration
--  WHERE dte_bucket IS NULL;

-- 3f. COST. CAN FIRE.
--     Expect an index seek per symbol against ix_gex_strike_snap_sym_ts, NOT a
--     sequential or large ordered scan of gex_strike_snapshots. A base table
--     scan means the skip scan is not being used and this view has inherited
--     the ADR-021 A1.1 defect.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_concentration;

-- 3g. NOT A CHECK, DELIBERATELY OMITTED.
--     Comparing hhi_net to gamma_metrics.gamma_concentration for the same
--     run. Both are max|v|/sum|v| over per-strike sums of the same
--     signed_gamma_exposure() output; the filtered-vs-raw row difference
--     contributes exactly +0.0 because filter_usable_option_rows drops
--     precisely the rows that function zeroes. It passes by construction.
--     Recorded here so the next session does not add it as the fourth
--     rediscovery of ADR-014 s2.5.

-- =====================================================================
-- END
-- =====================================================================
