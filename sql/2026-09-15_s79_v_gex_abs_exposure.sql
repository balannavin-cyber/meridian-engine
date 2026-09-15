-- =====================================================================
-- 2026-09-15_s79_v_gex_abs_exposure.sql
-- S79 / ENH-121 — L6 absolute GEX (v_gex_abs_exposure)
-- =====================================================================
--
-- WHAT THIS IS
--   sum(abs(gex_cr)) per run, beside the existing signed sum. The signed sum
--   says WHICH WAY hedging pushes; the absolute sum says HOW MUCH gamma is on
--   the board at all. A net near zero on a huge gross book is a different
--   market from a net near zero on an empty one, and the sign cannot
--   distinguish them.
--
--   Parity: optionsflow.in carries "Total Abs GEX" as a named value. This is
--   L6 in docs/registers/MERDIAN_Hedgewall_Parity_Spec.md.
--
--   Sibling of v_gex_strike_walls (ENH-120) and the ENH-81 pin/accel views:
--   same recursive skip scan for symbols, same bounded lateral for latest run
--   (ADR-021 + S72 FIX 2), same (run_id, symbol, expiry_date) grain.
--
-- MEASURED 2026-05-25 -> present, ~5,650 runs/symbol
--
--                              NIFTY            SENSEX
--   abs_gex p10           4,123,267         1,101,101
--   abs_gex median        7,509,653         2,520,880
--   abs_gex p90          25,245,720        28,632,751
--   net_gex median          948,535           157,115
--   contributing (avg)         93.9             106.9
--
--   Two observations carried here to be recorded, NOT acted on:
--
--   (a) SENSEX's gross book varies 26x p10->p90 against NIFTY's 6x, on a
--       median a third the size. UNEXPLAINED. Expiry cycle is the obvious
--       candidate and is UNMEASURED. Do not infer a cause from this file.
--
--   (b) avg contributing 106.9 against ~166 stored rows per SENSEX run means
--       ~36% of stored strikes contribute nothing -- independently
--       reproducing TD-S79-NEW-8's 35.1% zeroed figure from a different
--       query. The two are comparable because both are computed over STORED
--       rows. Both UNDERSTATE the fraction against the full vendor chain:
--       build_gss_rows() drops fully-noise strikes (no OI either side AND no
--       GEX contribution) before insert, so entirely-empty strikes never
--       reach this table and are invisible to both figures.
--
-- EXPLICITLY NOT IN SCOPE: a |net| / abs ratio.
--   It was specced, measured, and DROPPED. It is a gamma-weighted
--   restatement of PCR, which Hedgewall already carries twice, and the
--   argument for it -- that the spread carries information -- is the ENH-97
--   mistake (chi-square 1.56, p ~ 0.30 on 1,968 signals; shipped as
--   logging-only after a definitive FAIL). It is derivable from two columns
--   at render time if anything ever wants it. DO NOT ADD IT.
--
-- net_gex_cr IS NOT AN INDEPENDENT CHECK.
--   gamma_metrics.net_gex already holds this value, and comparing the two
--   proves nothing: both sides are produced by signed_gamma_exposure(), so
--   the comparison passes BY CONSTRUCTION. That is ADR-014 section 2.5's
--   falsification rule and Rule 0 clause 1 -- a check that cannot fail for
--   the reason it names is not a check. It has been rediscovered
--   independently three times. net_gex_cr is here so a consumer can compute
--   net-against-gross without a second query. It verifies nothing.
--
-- APPLY ORDER: Section 1 -> verify with Section 3 -> Section 2 (grants).
-- Run sections SEPARATELY: the Supabase SQL editor wraps a pasted script in
-- one transaction, so the weakest statement gates the strongest (S72
-- Section 5 took Sections 2 and 3 down with it).
-- =====================================================================


-- =====================================================================
-- SECTION 1 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_abs_exposure AS
WITH RECURSIVE symbols AS (
        -- Loose index scan ("skip scan") over idx_gss_symbol_ts (symbol, ts DESC).
        -- Symbols are DERIVED, not a literal list: the shipped pin/accel views
        -- carry VALUES ('NIFTY'),('SENSEX') in the view body, so a third symbol
        -- renders nothing, silently (TD-S72-NEW-3 guards exactly that). This
        -- view does not inherit the hazard and does not pay for it either:
        -- SELECT DISTINCT symbol is a full scan, the same cost shape S72 FIX 2
        -- removed (1,317,355 rows read to return two). O(distinct symbols)
        -- index seeks instead.
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
               g.spot, g.gex_cr
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
    sum(gex_cr)                             AS net_gex_cr,
    sum(abs(gex_cr))                        AS abs_gex_cr,
    count(*)                                AS n_strikes,
    count(*) FILTER (WHERE gex_cr <> 0)     AS n_contributing
  FROM scoped
 GROUP BY run_id, symbol, expiry_date;

COMMENT ON VIEW public.v_gex_abs_exposure IS
  'S79 / ENH-121 -- L6 absolute GEX. sum(abs(gex_cr)) beside sum(gex_cr), scoped to the latest run per symbol (ADR-021, S72 FIX 2 lateral form), grain (run_id, symbol, expiry_date). The signed sum says which way hedging pushes; the absolute sum says how much gamma is on the board. n_contributing is not decoration -- it is the denominator the gross figure is computed over, and on SENSEX that is ~64% of stored strikes (TD-S79-NEW-8). net_gex_cr duplicates gamma_metrics.net_gex and is NOT an independent check: both come from signed_gamma_exposure(), so any comparison passes by construction (ADR-014 s2.5, Rule 0 clause 1). A |net|/abs ratio is deliberately absent -- it restates PCR and is the ENH-97 mistake; derive it at render time if ever needed.';


-- =====================================================================
-- SECTION 2 -- anon grants (security-first sequence, D.21.1)
-- Run SEPARATELY, after Section 3 verifies.
-- Lovable grants anon ALL privileges by default; the canonical sequence is
-- REVOKE ALL then GRANT SELECT, not policy + grant alone.
-- =====================================================================

-- REVOKE ALL ON public.v_gex_abs_exposure FROM anon;
-- GRANT SELECT ON public.v_gex_abs_exposure TO anon;


-- =====================================================================
-- SECTION 3 -- verification
-- =====================================================================

-- 3a. ONE ROW PER SYMBOL, and the figures in the measured range.
--     Expect abs_gex_cr near the medians above (NIFTY ~7.5M, SENSEX ~2.5M),
--     though p10-p90 is wide on SENSEX (26x) so a single run proves little.
--
-- SELECT symbol, expiry_date, ts, dte, spot,
--        net_gex_cr, abs_gex_cr, n_strikes, n_contributing,
--        round(100.0 * n_contributing / NULLIF(n_strikes,0), 1) AS pct_contributing
--   FROM public.v_gex_abs_exposure
--  ORDER BY symbol;
--
-- 3b. IDENTITY: abs_gex_cr >= abs(net_gex_cr) on EVERY row. This is the
--     triangle inequality and cannot fail unless the sum is wrong. Expect
--     ZERO rows. It is the one assertion in this file that could actually
--     fire, which is why it is here and why the net-vs-gamma_metrics
--     comparison is not.
--
-- SELECT symbol, net_gex_cr, abs_gex_cr
--   FROM public.v_gex_abs_exposure
--  WHERE abs_gex_cr < abs(net_gex_cr);
--
-- 3c. n_contributing <= n_strikes on every row. Expect ZERO rows.
--     (Note: gex_cr is declared NOT NULL in the ENH-80 DDL, so the FILTER
--     predicate is total. If it were ever made nullable, NULL rows would
--     count toward n_strikes and not n_contributing -- which is the correct
--     reading anyway, since a NULL contributes nothing to the sum.)
--
-- SELECT symbol, n_strikes, n_contributing
--   FROM public.v_gex_abs_exposure
--  WHERE n_contributing > n_strikes;
--
-- 3d. COST. Expect an index seek per symbol against idx_gss_symbol_ts, NOT a
--     sequential or large ordered scan of gex_strike_snapshots. If a base
--     table scan appears, the skip scan is not being used and this view has
--     inherited the ADR-021 A1.1 defect.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_abs_exposure;

-- =====================================================================
-- END
-- =====================================================================
