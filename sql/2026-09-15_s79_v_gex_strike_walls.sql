-- =====================================================================
-- 2026-09-15_s79_v_gex_strike_walls.sql
-- S79 / ENH-120 — OI wall layer (v_gex_strike_walls)
-- =====================================================================
--
-- WHAT THIS IS
--   Put wall / call wall as raw-OI argmax within a moneyness band, per
--   symbol, on the latest run. Sibling of v_gex_strike_pin_zone and
--   v_gex_strike_accel_zone; same latest-run scoping (ADR-021 + S72 FIX 2),
--   same get_parameter_num wiring (ADR-016 / S72 FIX 1).
--
-- CALIBRATION PROVENANCE (measured over gex_strike_snapshots,
-- ts >= 2026-05-25, ~5,670 runs/symbol):
--   - Walls are RAW-OI argmax. Gamma-weighting was tested and REJECTED:
--     argmax(gamma x oi) collapses to ATM (put wall -0.09 sigma, call wall
--     +0.19 sigma, both symbols) because gamma is maximal at the money.
--     It finds the money, not the wall.
--   - Band = 1.5 sigma, sigma = spot * atm_iv/100 * sqrt(GREATEST(dte,1)/252).
--     Swept at 1.0 / 1.5 / 2.0 / 3.0 / unbounded. 1.5 -> unbounded buys 2.9
--     points of containment on NIFTY and costs 1.20 sigma of p90 corridor
--     width. The trade turns between 1.0 and 1.5.
--   - The band is a TAIL CONTROL ONLY. Median width moves 0.48 -> 0.58 sigma
--     across the entire sweep. On a typical run the restriction changes
--     nothing; it removes the occasional stale far-OTM round strike that
--     wins an unbounded argmax.
--   - The corridor is ASYMMETRIC: call wall sits ~2x further above spot than
--     the put wall sits below (NIFTY +0.30 / -0.15; SENSEX +0.33 / -0.27).
--     Consistent with call-heavy OI.
--   - ~30% of runs have spot OUTSIDE the corridor. That is a state to
--     render, not an error. Hence corridor_state.
--
-- NOT THIS OBJECT: the 299-day history this layer supports is a SEPARATE
-- object. Widening this view into an unbounded ordered scan is the exact
-- shape S72 FIX 2 removed.
--
-- APPLY ORDER: Section 1 -> verify with Section 3 -> Section 2 (grants).
-- Run sections SEPARATELY. The Supabase SQL editor wraps a pasted script in
-- one transaction, so the weakest statement in a bundle gates the strongest
-- (S72 Section 5 took Sections 2 and 3 down with it).
-- =====================================================================


-- =====================================================================
-- SECTION 1 — the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_walls AS
WITH RECURSIVE symbols AS (
        -- Loose index scan ("skip scan") over idx_gss_symbol_ts (symbol, ts DESC).
        -- Symbols are DERIVED, not a literal list: the shipped pin/accel views
        -- carry VALUES ('NIFTY'),('SENSEX') in the view body, so a third symbol
        -- renders nothing, silently (TD-S72-NEW-3 exists to guard exactly that).
        -- This view does not inherit that hazard. It also does not pay for it:
        -- SELECT DISTINCT symbol is a full scan, which is the SAME cost shape
        -- S72 FIX 2 removed (1,317,355 rows read to return two; 346.7ms of a
        -- 489.9ms warm execution; cold calls landed either side of the 8s
        -- statement_timeout at random). The skip scan is O(distinct symbols)
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
               g.strike, g.spot, g.oi_call, g.oi_put
          FROM gex_strike_snapshots g
          JOIN latest_run lr
            ON g.symbol = lr.symbol AND g.run_id = lr.run_id
     ), run_hdr AS (
        -- One row per (run_id, symbol, expiry_date). expiry_date is in the
        -- grain deliberately. MEASURED: build_gss_rows() in
        -- compute_gamma_metrics_local.py takes a single expiry_date scalar and
        -- stamps every row of the run with it, so one run == one expiry TODAY
        -- and this is a no-op. It matches the sibling views' grain, hands the
        -- panel the expiry it needs to label the walls, and keeps the view
        -- correct if the writer ever emits a second expiry per run.
        SELECT run_id, symbol, expiry_date,
               max(ts)   AS ts,
               max(dte)  AS dte,
               max(spot) AS spot,
               COALESCE(get_parameter_num('wall.band.' || symbol), 1.5)  AS band,
               COALESCE(get_parameter_num('wall.iv_floor_min'), 120)     AS iv_floor_min
          FROM scoped
         GROUP BY run_id, symbol, expiry_date
     ), sig AS (
        -- LEFT JOIN LATERAL, not CROSS: a run with no resolvable ATM IV must
        -- still appear, with NULL sigma and corridor_state UNDEFINED. A CROSS
        -- JOIN would drop it and the view would go quietly empty.
        SELECT h.run_id, h.symbol, h.expiry_date, h.ts, h.dte, h.spot,
               h.band, h.iv_floor_min,
               v.ts          AS atm_iv_ts,
               v.atm_iv_avg  AS atm_iv,
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
     ), eligible AS (
        SELECT sc.run_id, sc.symbol, sc.expiry_date,
               sc.strike, sc.oi_call, sc.oi_put
          FROM scoped sc
          JOIN sig g
            ON g.run_id = sc.run_id
           AND g.symbol = sc.symbol
           AND g.expiry_date = sc.expiry_date
         WHERE g.sigma IS NOT NULL
           AND g.sigma > 0
           AND abs(sc.strike - g.spot) <= g.band * g.sigma
     ), walls AS (
        -- FILTER (WHERE oi > 0) is load-bearing. Without it, a band in which
        -- every oi_put is NULL still returns a strike -- array_agg ordering
        -- among all-NULL keys is arbitrary, so the view would emit a wall it
        -- has no evidence for. With it, no evidence produces NULL.
        SELECT run_id, symbol, expiry_date,
               (array_agg(strike ORDER BY oi_put  DESC)
                    FILTER (WHERE oi_put  > 0))[1] AS put_wall,
               (array_agg(strike ORDER BY oi_call DESC)
                    FILTER (WHERE oi_call > 0))[1] AS call_wall,
               max(oi_put)  FILTER (WHERE oi_put  > 0) AS put_wall_oi,
               max(oi_call) FILTER (WHERE oi_call > 0) AS call_wall_oi,
               count(*) AS n_eligible_strikes
          FROM eligible
         GROUP BY run_id, symbol, expiry_date
     )
SELECT
    g.run_id,
    g.symbol,
    g.expiry_date,
    g.ts,
    g.dte,
    g.spot,
    g.sigma,
    g.band                                   AS band_used,
    g.atm_iv                                 AS atm_iv_used,
    g.atm_iv_ts,
    round(g.atm_iv_age_min, 1)               AS atm_iv_age_min,
    g.iv_floor_min                           AS iv_floor_min_used,
    (g.atm_iv_age_min IS NOT NULL
     AND g.atm_iv_age_min <= g.iv_floor_min)  AS iv_fresh,
    w.put_wall,
    w.call_wall,
    w.put_wall_oi,
    w.call_wall_oi,
    (w.put_wall  - g.spot) / NULLIF(g.sigma, 0) AS put_wall_sigma,
    (w.call_wall - g.spot) / NULLIF(g.sigma, 0) AS call_wall_sigma,
    (w.call_wall - w.put_wall) / NULLIF(g.sigma, 0) AS corridor_width_sigma,
    CASE
        WHEN w.put_wall IS NULL OR w.call_wall IS NULL THEN 'UNDEFINED'
        WHEN g.spot BETWEEN w.put_wall AND w.call_wall THEN 'INSIDE'
        WHEN g.spot > w.call_wall                      THEN 'ABOVE_CEILING'
        ELSE 'BELOW_FLOOR'
    END AS corridor_state,
    COALESCE(w.n_eligible_strikes, 0) AS n_eligible_strikes
  FROM sig g
  LEFT JOIN walls w
    ON w.run_id = g.run_id
   AND w.symbol = g.symbol
   AND w.expiry_date = g.expiry_date;

COMMENT ON VIEW public.v_gex_strike_walls IS
  'S79 / ENH-120 -- OI walls: put/call wall as raw-OI argmax within a +/-band*sigma moneyness window, scoped to the latest run per symbol (ADR-021, S72 FIX 2 lateral form). Band via get_parameter_num(''wall.band.<symbol>''), default 1.5. Gamma-weighted argmax was tested and rejected (collapses to ATM). Sigma columns are the distance measure; raw strikes exist for labelling only. corridor_state is four-valued: ~30% of runs sit outside the corridor, and a NULL wall is UNDEFINED, not BELOW_FLOOR. atm_iv is sourced from volatility_snapshots, which is single-expiry and silently switches expiry class -- staleness is surfaced (atm_iv_age_min / iv_fresh) but NOT enforced to absent; see ADR-023 deviation noted in sql/2026-09-15_s79_v_gex_strike_walls.sql.';


-- =====================================================================
-- SECTION 2 — anon grants (security-first sequence, D.21.1)
-- Run SEPARATELY, after Section 3 verifies.
-- Lovable grants anon ALL privileges by default; the canonical sequence is
-- REVOKE ALL then GRANT SELECT, not policy + grant alone.
-- =====================================================================

-- REVOKE ALL ON public.v_gex_strike_walls FROM anon;
-- GRANT SELECT ON public.v_gex_strike_walls TO anon;


-- =====================================================================
-- SECTION 3 — verification
-- =====================================================================

-- 3a. EQUIVALENCE GATE. The view must reproduce the measurement it was built
--     from. A single run is not a median, but a wildly different sign or
--     magnitude means the view is not computing what was measured.
--     Expect, roughly: NIFTY put -0.15 / call +0.30; SENSEX put -0.27 / call +0.33.
--
-- SELECT symbol, ts, dte, spot, round(sigma,1) AS sigma, band_used,
--        put_wall, call_wall,
--        round(put_wall_sigma,3)       AS put_sig,
--        round(call_wall_sigma,3)      AS call_sig,
--        round(corridor_width_sigma,3) AS width_sig,
--        corridor_state, n_eligible_strikes,
--        atm_iv_used, atm_iv_age_min, iv_fresh
--   FROM public.v_gex_strike_walls
--  ORDER BY symbol;
--
-- 3b. THREE-STATE CHECK. corridor_state must return a value on both symbols
--     and n_eligible_strikes must be plausible -- TENS, not hundreds and not
--     one. Hundreds means the band is not binding; one means sigma is wrong.
--
-- 3c. COST. Expect an index seek per symbol, NOT a scan of the base table.
--     If a sequential scan or a large ordered scan of gex_strike_snapshots
--     appears here, the skip scan is not being used and this view has
--     inherited the ADR-021 A1.1 defect.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_walls;
--
-- 3d. PARAMETER LIVENESS. After the wall.band.* rows land, changing one must
--     move the walls, not just band_used. That is the S72 FIX 1 lesson: a knob
--     wired to the label and not to the computation is decorative, and stayed
--     decorative for three sessions without anyone noticing.

-- =====================================================================
-- END
-- =====================================================================
