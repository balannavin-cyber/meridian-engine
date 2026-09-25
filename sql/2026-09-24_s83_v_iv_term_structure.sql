-- =====================================================================
-- 2026-09-24_s83_v_iv_term_structure.sql
-- S83 / ENH-130 -- L9 IV term structure, LIVE (v_iv_term_structure)
-- =====================================================================
--
-- WHAT THIS IS
--   Parity spec L9. One row per (symbol, leg) at the LATEST ts per
--   symbol: the ATM implied volatility of each listed expiry in that
--   snapshot, the spread of each leg against the front, the forward
--   volatility implied between adjacent legs, and the term slope.
--   17 columns, grain (symbol, leg).
--
-- NO FALLBACK TO AN EARLIER ts
--   The latest cycle is read as it is. A cycle carrying one expiry
--   yields ONE row, with term_slope NULL. Reaching back for a second
--   leg would manufacture a slope between two different market moments
--   and present it as one observation. ADR-023 D1: fail to absent,
--   never to stale.
--
-- MEASURED S83 (scope ts >= 2026-09-23 03:00:00+00, stage 1 live), and
-- each number shaped the design
--   * 341 cycles, 169,396 NIFTY / 128,156 SENSEX rows. Exactly one
--     run_id per (ts, expiry) on all 679 pairs -- no double writes.
--   * THREE cycles carry ONE expiry, not two: NIFTY 09-23 08:35,
--     NIFTY 09-24 08:45, SENSEX 09-24 08:45. The single-leg path is
--     not hypothetical; it fires roughly once per hundred cycles.
--   * The house ATM strike is present with a non-null iv on 100 pct of
--     cycles on both legs of both symbols. The ONLY losses are a single
--     iv = 0 on three of the four symbol-leg pairs.
--   * W2 is NOT thinner than W1: 99.4 / 99.4 / 99.4 / 100.0 pct of
--     cycles have both ATM legs quoted above zero.
--   * CE minus PE at ATM is negative on all four legs (median -0.589 to
--     -2.502), so the average is not a neutral choice -- see parity_gap.
--   * The term structure is INVERTED on 93.5 pct of NIFTY cycles and
--     97.6 pct of SENSEX cycles, in EVERY dte bucket present, including
--     NIFTY front-dte 5 and 6. Inversion here is the normal state of the
--     measured window, not an event.
--   * Forward variance was negative in 0 of 336 paired cycles.
--   * trading_calendar holds 218 rows, 2026-03-25 to 2027-01-29, of
--     which 208 are open and 10 are closed. Weekends and most holidays
--     are ABSENT ROWS, not is_open=false rows -- so the is_open filter
--     is load-bearing on those 10, not redundant.
--
-- THREE DELIBERATE DEVIATIONS, each recorded rather than absorbed
--   1. ZERO MAPS TO NULL. compute_volatility_metrics_local.py:670-686
--      guards None but NOT zero, so an iv of 0 is averaged in as a real
--      volatility. Here 0 becomes NULL and the leg abstains.
--   2. T = dte/365 IS A STATED CONVENTION, NOT A MODEL. The house file
--      has no T at all -- grep 365/252/sqrt returns only an unrelated
--      252-row history window -- and its dte at :690 is anchored on
--      datetime.now() rather than on ts. This view anchors on ts.
--   3. THE BACK LEG IS W2, NOT THE FURTHEST LISTED EXPIRY. See the
--      COMMENT: this is an ADR-025 D3 deviation pending an operator
--      decision. The two slopes may differ in sign as well as
--      magnitude; a W1-to-furthest slope has not been measured because
--      capture does not hold that leg.
--
-- APPLY ORDER: Section 1 -> 2 -> 3 -> verify with Section 4.
-- RUN ONE STATEMENT AT A TIME (S72 Section 5).
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS so sql/ matches the database
-- (TD-S81-NEW-5: a body-only file is not a rebuild source).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_iv_term_structure AS
WITH RECURSIVE symbols AS (
        -- S72 FIX 2 skip scan. Symbols derived, never a literal list.
        SELECT (SELECT min(o.symbol) FROM option_chain_snapshots o) AS symbol
        UNION ALL
        SELECT (SELECT min(o.symbol)
                  FROM option_chain_snapshots o
                 WHERE o.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest AS (
        -- ADR-021 run scoping: one index seek per symbol through
        -- idx_ocs_ts_symbol_expiry (ts DESC, symbol, expiry_date).
        -- NOT max(ts) GROUP BY symbol, which measured 3,260 ms over
        -- 1,336,714 rows inside v_max_pain_by_strike. NEVER created_at:
        -- ingest computes one snapshot_ts per cycle and reuses it, but
        -- created_at is a DB-side default and is later for the extra
        -- expiry pass, so ordering by it hands back W2 (S81, 89bc83e).
        SELECT s.symbol, lt.ts AS latest_ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = s.symbol
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), scoped AS (
        SELECT o.symbol, o.ts, o.expiry_date, o.strike, o.option_type,
               o.iv, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol
           AND o.ts     = l.latest_ts
     ), legs AS (
        -- leg 1 is the front. dense_rank, so leg numbering is gapless
        -- and max(leg) is the leg count.
        SELECT DISTINCT symbol, ts, expiry_date,
               dense_rank() OVER (PARTITION BY symbol, ts
                                  ORDER BY expiry_date) AS leg
          FROM scoped
     ), anchored AS (
        -- House ATM: round(spot / step) * step on ocs.spot, step 50 for
        -- NIFTY and 100 for SENSEX. This is the GRID strike, which may
        -- not be a listed strike; when it is not, ce_iv and pe_iv come
        -- back NULL and the leg abstains rather than sliding to a
        -- neighbour. compute_volatility_metrics_local.py:86-88, :624.
        SELECT g.symbol, g.ts, g.expiry_date, g.leg,
               max(s.spot) AS spot,
               round(max(s.spot)
                     / (CASE WHEN g.symbol = 'NIFTY' THEN 50 ELSE 100 END))
                 * (CASE WHEN g.symbol = 'NIFTY' THEN 50 ELSE 100 END)
                 AS atm_strike
          FROM legs g
          JOIN scoped s
            ON s.symbol = g.symbol AND s.ts = g.ts
           AND s.expiry_date = g.expiry_date
         GROUP BY g.symbol, g.ts, g.expiry_date, g.leg
     ), quoted AS (
        -- NULLIF(x, 0) is deviation 1: a zero iv abstains.
        SELECT a.symbol, a.ts, a.leg, a.expiry_date, a.atm_strike,
               NULLIF(max(CASE WHEN s.option_type = 'CE' THEN s.iv END), 0)
                 AS ce_iv,
               NULLIF(max(CASE WHEN s.option_type = 'PE' THEN s.iv END), 0)
                 AS pe_iv
          FROM anchored a
          LEFT JOIN scoped s
            ON s.symbol = a.symbol AND s.ts = a.ts
           AND s.expiry_date = a.expiry_date
           AND s.strike = a.atm_strike
         GROUP BY a.symbol, a.ts, a.leg, a.expiry_date, a.atm_strike
     ), horizon AS (
        SELECT max(trade_date) AS max_cal FROM trading_calendar
     ), enriched AS (
        SELECT q.symbol, q.ts, q.leg, q.expiry_date, q.atm_strike,
               q.ce_iv, q.pe_iv,
               (q.expiry_date - (q.ts AT TIME ZONE 'Asia/Kolkata')::date)
                 AS dte,
               -- ADR-020: an absent trading_calendar row is not a
               -- verdict. Beyond the seeded horizon the answer is
               -- UNKNOWN, and NULL says so; counting rows there would
               -- silently return a short count and read as a fact.
               CASE WHEN q.expiry_date > h.max_cal THEN NULL
                    ELSE (SELECT count(*)
                            FROM trading_calendar tc
                           WHERE tc.trade_date
                                 > (q.ts AT TIME ZONE 'Asia/Kolkata')::date
                             AND tc.trade_date <= q.expiry_date
                             AND tc.is_open)
               END AS dte_sessions,
               CASE WHEN q.ce_iv > 0 AND q.pe_iv > 0
                    THEN (q.ce_iv + q.pe_iv) / 2.0
               END AS atm_iv
          FROM quoted q
          CROSS JOIN horizon h
     ), framed AS (
        SELECT e.*,
               (e.dte::numeric / 365.0) AS t_years,
               max(e.leg) OVER (PARTITION BY e.symbol, e.ts) AS max_leg,
               max(CASE WHEN e.leg = 1 THEN e.atm_iv END)
                 OVER (PARTITION BY e.symbol, e.ts) AS front_iv,
               max(CASE WHEN e.leg = 1 THEN e.dte END)
                 OVER (PARTITION BY e.symbol, e.ts) AS front_dte,
               lag(e.atm_iv) OVER (PARTITION BY e.symbol, e.ts
                                   ORDER BY e.leg) AS prev_iv,
               lag(e.dte)    OVER (PARTITION BY e.symbol, e.ts
                                   ORDER BY e.leg) AS prev_dte
          FROM enriched e
     ), backed AS (
        SELECT f.*,
               max(CASE WHEN f.leg = f.max_leg THEN f.atm_iv END)
                 OVER (PARTITION BY f.symbol, f.ts) AS back_iv
          FROM framed f
     )
SELECT
    b.symbol,
    b.ts,
    b.leg,
    b.expiry_date,
    b.dte,
    b.dte_sessions,
    b.t_years,
    b.atm_strike,
    b.ce_iv,
    b.pe_iv,
    b.atm_iv,
    -- Quality column, not a signal. A spread narrower than the CE/PE
    -- disagreement at the same strike is inside measurement noise.
    (b.ce_iv - b.pe_iv) AS parity_gap,
    CASE WHEN b.atm_iv IS NULL OR b.front_iv IS NULL THEN NULL
         ELSE b.atm_iv - b.front_iv
    END AS spread_vs_front,
    -- Forward vol between this leg and the PREVIOUS LEG at the SAME ts.
    -- NEVER CLAMPED: a negative variance means the two legs disagree,
    -- and NULL reports that rather than flooring it at zero and
    -- presenting a disagreement as a small positive number.
    CASE
      WHEN b.leg = 1                                    THEN NULL
      WHEN b.atm_iv IS NULL OR b.prev_iv IS NULL        THEN NULL
      WHEN b.prev_dte IS NULL                           THEN NULL
      WHEN (b.dte::numeric / 365.0)
           <= (b.prev_dte::numeric / 365.0)             THEN NULL
      WHEN ((b.atm_iv / 100.0) ^ 2 * (b.dte::numeric / 365.0)
          - (b.prev_iv / 100.0) ^ 2 * (b.prev_dte::numeric / 365.0)) < 0
                                                        THEN NULL
      ELSE sqrt(
             ((b.atm_iv  / 100.0) ^ 2 * (b.dte::numeric      / 365.0)
            - (b.prev_iv / 100.0) ^ 2 * (b.prev_dte::numeric / 365.0))
             / ((b.dte::numeric / 365.0) - (b.prev_dte::numeric / 365.0))
           ) * 100.0
    END AS fwd_vol_from_prev,
    (b.leg = b.max_leg) AS is_back,
    CASE WHEN b.max_leg = 1                            THEN NULL
         WHEN b.back_iv IS NULL OR b.front_iv IS NULL  THEN NULL
         ELSE b.back_iv - b.front_iv
    END AS term_slope,
    -- Display flag only. No rows are dropped and there is no fallback.
    (b.front_dte = 0) AS front_is_0dte
  FROM backed b;


-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE, not commented out -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_iv_term_structure IS
  'S83 / ENH-130 -- ADR-025 parity spec L9, IV term structure. One row per (symbol, leg) at the LATEST ts per symbol. Grain (symbol, leg). Consumers MUST ORDER BY symbol, leg -- a view body carries no ordering guarantee. DISPLAY ONLY per the S37 GEX-as-context-not-gate ruling; it routes nothing and makes no predictive claim. ATM IS THE HOUSE SPOT GRID, round(spot / step) * step on option_chain_snapshots.spot with step 50 for NIFTY and 100 for SENSEX, matching compute_volatility_metrics_local.py:86-88 and :624. That is the GRID strike and may not be a listed strike; when it is not, ce_iv and pe_iv are NULL and the leg abstains rather than sliding to a neighbouring strike. ZERO MAPS TO NULL, AND THAT IS A DELIBERATE DEVIATION FROM THE HOUSE CODE. compute_volatility_metrics_local.py:670-686 guards None but not zero, so an iv of 0 is averaged into atm_iv_avg there as though it were a real volatility. Here NULLIF(iv, 0) makes the leg abstain. Measured S83: the house ATM strike is quoted with a non-null iv on 100 pct of cycles on both legs of both symbols, and the ONLY availability losses are a single iv = 0 on three of four symbol-leg pairs -- so this deviation is the entire difference between the two definitions on the measured window. T = dte / 365 IS A STATED CONVENTION, NOT A MODEL. The house file carries no T at all (grep for 365, 252 and sqrt returns only an unrelated 252-row history window) and its dte at :690 is anchored on datetime.now() rather than on the row ts, which is the TD-NEW-4 wall-clock shape. This view anchors dte on ts. ENH-98 measured that calendar-year time fits the vendor greeks better than trading-day time and that dte/365 and exact/365 separate only at low DTE; neither is adopted as truth here, and t_years is published so a consumer can substitute its own. dte_sessions COUNTS OPEN trading_calendar ROWS in (IST date of ts, expiry_date]. The is_open filter is NOT redundant: measured S83 the table holds 218 rows of which 208 are open and 10 are closed, and weekends and most holidays are ABSENT rows rather than is_open=false rows. BEYOND THE SEEDED HORIZON dte_sessions IS NULL, because an absent row is not a verdict (ADR-020): counting rows past max(trade_date) would return a short count and present it as a fact. parity_gap = ce_iv - pe_iv IS THE QUALITY COLUMN. A spread_vs_front or term_slope smaller in magnitude than the parity_gap at the same strike is inside measurement noise and must not be read as structure. Measured S83, CE minus PE at ATM is negative on all four symbol-leg pairs, median -0.589 to -2.502 vol points, so averaging CE and PE is not a neutral operation. THERE IS NO FALLBACK TO AN EARLIER ts. A latest cycle carrying one expiry yields ONE row with term_slope NULL and is_back true on that single leg. Measured S83: three of 341 cycles in the stage 1 window carried one expiry, so this path fires roughly once per hundred cycles and is not hypothetical. Reaching back for a second leg would compute a slope between two different market moments and present it as one observation. fwd_vol_from_prev IS NEVER CLAMPED: a negative forward variance means the two legs disagree, and NULL reports that rather than flooring at zero and dressing a disagreement as a small positive number. Measured S83: forward variance was negative in 0 of 336 paired cycles. PARITY-TARGET COMPARABILITY, AND WHERE THIS VIEW DEPARTS. The ADR-025 L9 target defines BACK ATM IV as the FURTHEST LISTED expiry, TERM SLOPE as back minus front with inverted read below -1 point, and DTE as trading sessions. At capture stage 1 this view sees only W1 and W2, so its back leg is W2 and term_slope is a SHORT-END SLOPE that is NOT comparable to the L9 target figure until capture includes the furthest listed expiry. That is an ADR-025 D3 deviation and is PENDING AN OPERATOR DECISION. The two slopes may differ in sign as well as magnitude; a W1-to-furthest slope has not been measured because capture does not hold that leg. term_slope is not comparable to a normal-day reading when front_is_0dte is true: front ATM IV on expiry day is dominated by expiry mechanics. The L9 target keeps 0DTE and weekly chains separate. front_is_0dte is a DISPLAY FLAG ONLY: no rows are dropped and there is no fallback. dte_sessions is published precisely so the trading-session convention is available when the comparison becomes possible. The L9 target does not state whether its ATM IV is the call, the put, or the average; THE AVERAGE IS A MERDIAN CHOICE, and parity_gap is published so the choice can be audited per row. fwd_vol_from_prev has no L9 target counterpart and is a MERDIAN addition. READ THE INVERSION WITH THE MEASUREMENT IN MIND: over the stage 1 window term structure was inverted on 93.5 pct of NIFTY cycles and 97.6 pct of SENSEX cycles, in every dte bucket present including NIFTY front-dte 5 and 6, so inversion is the normal state of this window rather than an event.';


-- =====================================================================
-- SECTION 3 of 4 -- anon grants, security-first sequence (D.21.1).
-- TWO STATEMENTS, run separately.
-- =====================================================================

REVOKE ALL ON public.v_iv_term_structure FROM anon;

GRANT SELECT ON public.v_iv_term_structure TO anon;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run separately, after 1-3)
-- =====================================================================

-- 4a -- ADR-025 D2 clause 2. Expect index access only, no Seq Scan on
--       option_chain_snapshots, and an execution time in single-digit ms.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_iv_term_structure;

-- 4b -- D2 clause 1: read the output. Expect 2 rows per symbol on a
--       normal cycle, leg 1 with spread_vs_front = 0 and
--       fwd_vol_from_prev NULL, the highest leg with is_back true, and
--       term_slope identical on every row of a symbol.
--
-- SELECT symbol, leg, expiry_date, dte, dte_sessions,
--        round(t_years, 6) AS t_years, atm_strike,
--        ce_iv, pe_iv, round(atm_iv, 4) AS atm_iv,
--        round(parity_gap, 4) AS parity_gap,
--        round(spread_vs_front, 4) AS spread_vs_front,
--        round(fwd_vol_from_prev, 4) AS fwd_vol_from_prev,
--        is_back, round(term_slope, 4) AS term_slope, front_is_0dte,
--        (ts AT TIME ZONE 'Asia/Kolkata') AS ts_ist
--   FROM public.v_iv_term_structure
--  ORDER BY symbol, leg;

-- 4c -- the quality gate parity_gap exists for. Expect this to flag the
--       rows where the term read is inside CE/PE disagreement.
--
-- SELECT symbol, leg, round(spread_vs_front, 4) AS spread,
--        round(parity_gap, 4) AS parity_gap,
--        (abs(spread_vs_front) < abs(parity_gap)) AS inside_noise
--   FROM public.v_iv_term_structure
--  WHERE spread_vs_front IS NOT NULL AND parity_gap IS NOT NULL
--  ORDER BY symbol, leg;

-- 4d -- anon path, not object existence (TD-S81-NEW-5). Run as anon.
--       Expect a non-zero row count, not merely HTTP 200.
--
-- SELECT count(*) FROM public.v_iv_term_structure;
