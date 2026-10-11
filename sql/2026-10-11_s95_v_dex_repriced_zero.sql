-- =====================================================================
-- 2026-10-11_s95_v_dex_repriced_zero.sql
-- S95 / roadmap P6 / ruling S94-H -- S*, the re-priced zero-delta level
-- (v_dex_repriced_zero). Companion to v_dex_standing_book (ENH-140).
-- =====================================================================
--
-- PRE-REGISTERED, then gated: docs/research/s95_priority/sstar/
--   sstar_prereg_2026-10-11.md (git hash-object 7bfafb49, commit 90c8c50).
--   Result: docs/research/s95_priority/sstar/sstar_result_2026-10-11.md.
--   Verdict APPLY: G1 G3 G4 G5 PASS on 7 scorable arms, all mutants caught.
--
-- SECTION 1 IS BYTE-IDENTICAL to docs/research/s95_priority/sstar/
--   sstar_view_body.sql (git hash-object 0a8b12db) -- the body the gates
--   ran on. Its one inert comment line `-- @ASOF@` is where the gate harness
--   added `AND o.ts <= <arm ts>`; in the view it does nothing.
--
-- APPLY: Sections 1 -> 3 in ONE execution. The batch ENDS with its own
-- verification SELECT (TD-S94-NEW-3: an editor `Success` is not evidence of
-- a full apply). Then Section 4, one statement per execution.
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS (TD-S81-NEW-5).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_dex_repriced_zero AS
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
        -- NOT max(ts) GROUP BY symbol. NEVER created_at: ingest reuses
        -- one snapshot_ts per cycle but created_at is a DB-side default
        -- and is later for the extra expiry pass, so ordering by it
        -- hands back W2 (S81, 89bc83e).
        SELECT s.symbol, lt.ts AS latest_ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = s.symbol
                -- @ASOF@ (gate harness only; inert comment in the view)
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), front AS (
        -- Front expiry = the nearest listed expiry IN THAT SNAPSHOT.
        -- Capture stage 1 holds W1 and W2; only W1 is repriced, so the
        -- comparison is like-for-like against a front-expiry net.
        SELECT l.symbol, l.latest_ts AS ts,
               min(o.expiry_date) AS front_expiry
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
         GROUP BY l.symbol, l.latest_ts
     ), scoped AS (
        SELECT f.symbol, f.ts, f.front_expiry,
               o.strike, o.option_type, o.iv, o.oi, o.gamma, o.spot
          FROM front f
          JOIN option_chain_snapshots o
            ON o.symbol = f.symbol AND o.ts = f.ts
           AND o.expiry_date = f.front_expiry
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the front expiry, over a
        -- 365-day year. This is Gate 5 convention (b). dte 0 is NOT
        -- floored: S62 settled that expiry-day 0-DTE gamma exposure is
        -- numerically unreconstructible, so it is marked and skipped.
        SELECT s.symbol, s.ts, s.front_expiry,
               max(s.spot) AS spot,
               (s.front_expiry
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.front_expiry + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.front_expiry
     ), legs AS (
        -- R1 FROZEN LEG SET, evaluated once at the OBSERVED spot.
        -- iv > 0 is required because sigma is a divisor; it removed no
        -- leg on any of the five gate arms.
        SELECT s.symbol, s.ts,
               s.strike::double precision       AS k,
               s.option_type,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h ON h.symbol = s.symbol AND h.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), dropped AS (
        -- P6 note section 5.3: the R1 filter is inherited UNCHANGED, but the
        -- legs it drops are COUNTED and their OI published, never assumed 0.
        -- On 2026-10-08 the iv exclusion alone removed 117 of 234 SENSEX W1
        -- positive-OI legs (6.19 pct of OI); L3's gate arms saw none.
        SELECT s.symbol, s.ts,
               count(*) FILTER (WHERE s.oi > 0)::integer           AS n_legs_oi,
               count(*) FILTER (WHERE s.oi > 0 AND NOT (s.iv > 0))::integer
                                                                   AS n_dropped_no_iv,
               COALESCE(sum(s.oi) FILTER (WHERE s.oi > 0 AND NOT (s.iv > 0)), 0)
                                                                   AS oi_dropped_no_iv,
               COALESCE(sum(s.oi) FILTER (WHERE s.oi > 0), 0)      AS oi_total
          FROM scoped s
         GROUP BY s.symbol, s.ts
     ), legcount AS (
        SELECT l.symbol, l.ts, count(*)::integer AS n_legs_used,
               sum(l.oi) AS oi_used
          FROM legs l
         GROUP BY l.symbol, l.ts
     ), futwin AS (
        -- NO LOOK-AHEAD. Futures rows for this symbol from 09:20 IST on
        -- the ts date through ts INCLUSIVE. One index range scan per
        -- symbol through idx_index_futures_snapshots_symbol_ts.
        SELECT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM hdr h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE at ts, which is not always the option
        -- front expiry: min expiry on or after the IST date of ts.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry r_fut(t) = ln(F/S) / T_f, with T_f taken from
        -- THAT ROW OWN ts, not from the snapshot ts. F and S come from
        -- the same row, so the two are contemporaneous by construction.
        SELECT w.symbol, w.ts,
               ( ln(w.futures_price / w.spot_price)
                 / (EXTRACT(epoch FROM
                      (((w.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                       - w.fut_ts)) / (365.0 * 86400.0))
               )::double precision AS r_fut
          FROM futwin w
          JOIN futfront f
            ON f.symbol = w.symbol AND f.ts = w.ts
           AND f.fut_expiry = w.expiry_date
         WHERE w.fut_ts < ((w.expiry_date + time '15:30')
                           AT TIME ZONE 'Asia/Kolkata')
     ), rstats AS (
        -- r_sess is the MEDIAN, and the p10-p90 band is published beside
        -- it because Gate 5 clause (i) is a sweep over that band, not a
        -- point estimate. Fewer than 6 rows is UNMEASURABLE, never
        -- substituted with a default.
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess,
               percentile_cont(0.10) WITHIN GROUP (ORDER BY r_fut) AS r_p10,
               percentile_cont(0.90) WITHIN GROUP (ORDER BY r_fut) AS r_p90
          FROM rrows
         GROUP BY symbol, ts
     ), atm AS (
        -- House ATM grid: round(spot / step) * step, step 50 for NIFTY
        -- and 100 for SENSEX, matching
        -- compute_volatility_metrics_local.py:86-88 and :624. This is a
        -- GRID strike and may not be listed; when it is not, atm_iv is
        -- NULL and sigma_1d is NULL rather than sliding to a neighbour.
        SELECT h.symbol, h.ts,
               round(h.spot
                     / (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END))
                 * (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END)
                 AS atm_strike
          FROM hdr h
     ), atmiv AS (
        -- NULLIF(iv, 0): a zero iv abstains. Same deviation recorded in
        -- the L9 view, for the same reason.
        SELECT q.symbol, q.ts, q.atm_strike,
               CASE WHEN q.ce_iv > 0 AND q.pe_iv > 0
                    THEN (q.ce_iv + q.pe_iv) / 2.0
               END AS atm_iv
          FROM (
            SELECT a.symbol, a.ts, a.atm_strike,
                   NULLIF(max(CASE WHEN s.option_type = 'CE' THEN s.iv END), 0)
                     AS ce_iv,
                   NULLIF(max(CASE WHEN s.option_type = 'PE' THEN s.iv END), 0)
                     AS pe_iv
              FROM atm a
              LEFT JOIN scoped s
                ON s.symbol = a.symbol AND s.ts = a.ts
               AND s.strike = a.atm_strike
             GROUP BY a.symbol, a.ts, a.atm_strike
          ) q
     ), base AS (
        SELECT h.symbol, h.ts, h.front_expiry, h.spot, h.dte, h.t_years,
               r.n_r_rows, r.r_sess, r.r_p10, r.r_p90,
               v.atm_iv,
               (h.spot * v.atm_iv / 100.0 * sqrt(1.0 / 365.0))::double precision
                 AS sigma_1d
          FROM hdr h
          LEFT JOIN rstats r ON r.symbol = h.symbol AND r.ts = h.ts
          LEFT JOIN atmiv  v ON v.symbol = h.symbol AND v.ts = h.ts
     ), evalset AS (
        -- Only rows that can carry a number reach the sweep. dte 0 and a
        -- thin r window drop out here and are labelled in status.
        SELECT b.symbol, b.ts, b.spot::double precision AS spot,
               b.t_years, b.r_sess
          FROM base b
         WHERE b.dte > 0 AND b.t_years > 0
           AND b.n_r_rows >= 6 AND b.r_sess IS NOT NULL
     ), grid AS (
        -- 201 points, 0.1 pct steps, plus or minus 10 pct of spot.
        SELECT e.symbol, e.ts, g.i,
               e.spot * (1.0 + (g.i - 100) * 0.001) AS s_grid
          FROM evalset e
          CROSS JOIN generate_series(0, 200) AS g(i)
     ), dexcurve AS (
        -- S95 / S94-H: TotalDEX(S). The ONLY two changes from ENH-131's
        -- gexcurve (P6 design note section 5.2):
        --   1. the greek: BS delta, Phi(d1) for a call and Phi(d1) - 1 for a
        --      put, Phi(x) = 0.5 * erfc(-x / sqrt(2)), d1 IDENTICAL to L3;
        --   2. ONE power of S (delta x oi x S / 1e7), and NO PE -> -1 factor:
        --      Phi(d1) - 1 is already negative, so L3's
        --      CASE WHEN option_type = 'PE' THEN -1.0 ... is DELETED, not
        --      copied. Copying it would turn every put positive and the sum
        --      would have no zero at all.
        -- Every BS delta increases in S, so sum(delta x oi) is strictly
        -- increasing: at most ONE crossing, always neg->pos (S95 gate G3).
        SELECT gr.symbol, gr.ts, gr.i, gr.s_grid,
               sum(
                 ( 0.5 * erfc( - ( ln(gr.s_grid / l.k)
                                   + (e.r_sess + 0.5 * power(l.sigma, 2)) * e.t_years )
                                 / (l.sigma * sqrt(e.t_years)) / sqrt(2.0) )
                   - (CASE WHEN l.option_type = 'PE' THEN 1.0 ELSE 0.0 END) )
                 * l.oi * gr.s_grid / 1e7
               ) AS total_dex,
               sum(abs(
                 ( 0.5 * erfc( - ( ln(gr.s_grid / l.k)
                                   + (e.r_sess + 0.5 * power(l.sigma, 2)) * e.t_years )
                                 / (l.sigma * sqrt(e.t_years)) / sqrt(2.0) )
                   - (CASE WHEN l.option_type = 'PE' THEN 1.0 ELSE 0.0 END) )
                 * l.oi * gr.s_grid / 1e7
               )) AS gross_dex
          FROM grid gr
          JOIN evalset e ON e.symbol = gr.symbol AND e.ts = gr.ts
          JOIN legs   l  ON l.symbol = gr.symbol AND l.ts = gr.ts
         GROUP BY gr.symbol, gr.ts, gr.i, gr.s_grid
     ), adj AS (
        SELECT c.symbol, c.ts, c.s_grid, c.total_dex AS total_gex,
               lag(c.s_grid)    OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_s,
               lag(c.total_dex) OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_g
          FROM dexcurve c
     ), crossings AS (
        -- Linear interpolation between adjacent grid points, exactly as
        -- the gate script computed it.
        SELECT a.symbol, a.ts,
               a.prev_s + (a.s_grid - a.prev_s)
                        * (0.0 - a.prev_g) / (a.total_gex - a.prev_g)
                 AS s_star,
               CASE WHEN a.prev_g < 0 THEN 'neg->pos' ELSE 'pos->neg' END
                 AS flip_direction
          FROM adj a
         WHERE a.prev_g IS NOT NULL
           AND ((a.prev_g < 0) <> (a.total_gex < 0))
           AND a.total_gex <> a.prev_g
     ), counted AS (
        SELECT b.symbol, b.ts,
               count(x.s_star)::integer AS n_cross_full_grid,
               CASE WHEN b.sigma_1d IS NULL THEN NULL
                    ELSE count(x.s_star) FILTER (
                           WHERE abs(x.s_star - b.spot) <= 2.0 * b.sigma_1d
                         )::integer
               END AS n_cross_within_2sigma
          FROM base b
          LEFT JOIN crossings x ON x.symbol = b.symbol AND x.ts = b.ts
         GROUP BY b.symbol, b.ts, b.sigma_1d
     ), atspot AS (
        -- grid point i = 100 is s_grid = spot exactly: the repriced book at
        -- the observed spot, published for the descriptive gate G2.
        SELECT c.symbol, c.ts, c.total_dex AS net_dex_at_spot_cr,
               c.gross_dex AS gross_dex_at_spot_cr
          FROM dexcurve c
         WHERE c.i = 100
     ), nearest AS (
        SELECT DISTINCT ON (x.symbol, x.ts)
               x.symbol, x.ts, x.s_star, x.flip_direction
          FROM crossings x
          JOIN base b ON b.symbol = x.symbol AND b.ts = x.ts
         ORDER BY x.symbol, x.ts, abs(x.s_star - b.spot)
     )
SELECT
    b.symbol,
    b.ts,
    b.spot,
    b.front_expiry,
    (b.t_years * 365.0)                          AS t_days,
    b.r_sess,
    b.r_p10,
    b.r_p90,
    COALESCE(b.n_r_rows, 0)                      AS n_r_rows,
    b.atm_iv,
    b.sigma_1d,
    n.s_star                                     AS zero_delta,
    n.flip_direction                             AS cross_direction,
    (n.s_star - b.spot)                          AS zero_minus_spot,
    CASE WHEN b.sigma_1d IS NULL OR b.sigma_1d = 0 THEN NULL
         ELSE (n.s_star - b.spot) / b.sigma_1d
    END                                          AS zero_sigma,
    c.n_cross_within_2sigma,
    c.n_cross_full_grid,
    p.net_dex_at_spot_cr,
    p.gross_dex_at_spot_cr,
    COALESCE(lc.n_legs_used, 0)                  AS n_legs_used,
    d.n_legs_oi,
    d.n_dropped_no_iv,
    d.oi_dropped_no_iv,
    (d.n_legs_oi - d.n_dropped_no_iv - COALESCE(lc.n_legs_used, 0))
                                                 AS n_dropped_other,
    (d.oi_total - d.oi_dropped_no_iv - COALESCE(lc.oi_used, 0))
                                                 AS oi_dropped_other,
    d.oi_total,
    -- Precedence is ENH-131's, unchanged. S62 first.
    CASE WHEN b.dte = 0                 THEN 'SKIPPED_EXPIRY'
         WHEN COALESCE(b.n_r_rows, 0) < 6 THEN 'UNMEASURABLE_R'
         WHEN n.s_star IS NULL          THEN 'NO_CROSSING'
         ELSE 'OK'
    END                                          AS status
  FROM base b
  LEFT JOIN nearest  n  ON n.symbol  = b.symbol AND n.ts  = b.ts
  LEFT JOIN counted  c  ON c.symbol  = b.symbol AND c.ts  = b.ts
  LEFT JOIN atspot   p  ON p.symbol  = b.symbol AND p.ts  = b.ts
  LEFT JOIN dropped  d  ON d.symbol  = b.symbol AND d.ts  = b.ts
  LEFT JOIN legcount lc ON lc.symbol = b.symbol AND lc.ts = b.ts;


-- =====================================================================
-- SECTION 2 of 4 -- COMMENT (LIVE statement -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_dex_repriced_zero IS
  'S95 / roadmap P6 / ruling S94-H -- S*, the RE-PRICED zero-delta level of the open-interest delta book. Companion to v_dex_standing_book (ENH-140). NOT a parity layer; display-only (S37). Grain (symbol), latest chain cycle, front expiry. WHAT IT IS: the spot level S* at which sum_i Delta_i(S*) x OI_i = 0, Delta from Black-Scholes at each leg own iv held fixed (sticky strike), swept over 201 points at +/-10 pct of spot, linear interpolation, the crossing nearest spot. IT IS ENH-131 (v_gex_repriced_flip) WITH EXACTLY TWO CHANGES: the greek is Phi(d1) for a call and Phi(d1) - 1 for a put, Phi(x) = 0.5 erfc(-x/sqrt 2), d1 identical to L3; and each leg contributes Delta x oi x S / 1e7, ONE power of S, with NO PE sign flip (Phi(d1) - 1 is already negative; copying the L3 flip would turn every put positive and remove the zero). Every other CTE is L3 unchanged: R1 frozen leg set (oi > 0, vendor gamma non-zero, iv > 0, deep-ITM guard), r = session-median futures carry 09:20 IST to ts with p10/p90 published and fewer than 6 rows UNMEASURABLE_R, T exact seconds to 15:30 IST on expiry over 365 d, dte 0 SKIPPED_EXPIRY never floored (S62). UNIQUE BY CONSTRUCTION: every BS delta increases in S, so sum Delta x OI is strictly increasing and there is at most one crossing, always neg->pos. A crossing beyond +/-10 pct is NO_CROSSING, a statement about the book. DROPPED LEGS ARE PUBLISHED, never assumed zero (P6 note 5.3): n_dropped_no_iv / oi_dropped_no_iv, n_dropped_other / oi_dropped_other, oi_total. GATE RECORD (pre-registration docs/research/s95_priority/sstar/sstar_prereg_2026-10-11.md, git hash-object 7bfafb49, commit 90c8c50, committed before the first real export). Arms: L3 five gate arms, five out-of-sample arms (2026-10-07/08/09 12:00) and one dte-0 control (SENSEX 2026-10-08). G1 PASS on all 11 arms: the view body run as-of equals an independent Python recompute (S* within 1e-6 x spot, net at spot within 1e-6 x gross, leg and drop counts exact), and the control was refused on both sides. G3 PASS: strictly increasing, at most one neg->pos crossing, on every scorable arm under all nine r x T variants. G4 PASS: S* across the r p10-p90 band moved 0.005 to 0.164 sigma_1d. G5 PASS (L3 Gate 5 re-run, r band x T conventions (a) dte/365, (b) exact seconds, (c) sessions/252, tolerance 0.25 sigma_1d inherited unchanged): spreads 0.027 to 0.239 sigma_1d. MARGIN, MEASURED: the 1-dte SENSEX L3 arm (2026-09-23 15:40) spread 0.2386 sigma_1d, 95 pct of the tolerance, with an r band of -0.113 to 0.222 and T(c)/T(b) = 1.46. On 1-dte SENSEX this is the least stable reading the view publishes. SCORABLE ARMS 7 of 10: the three NIFTY L3 arms span September weekends that hold no trading_calendar row, so T(c) was unmeasurable and they were not scored (ADR-020: absence is not a verdict). Only two of the five L3 arms were re-scored. L3 Gate 4 (single-cycle carry band) was NOT re-run: S83 recorded it as mis-specified. Mutants M1 (L3 PE flip copied) G1, M2 (two powers of S) G1, M3 (r x 100) G1 and G4, M4 (dte 0 floored) G1, M5 (d1 negated) G3: all caught. G2, DESCRIPTIVE ONLY: on every scorable arm S* sat ABOVE spot, +0.009 to +0.456 sigma_1d, with the repriced net at spot negative. The repriced book and the VENDOR-delta book (what v_dex_standing_book shows) DISAGREED IN SIGN at spot on 2 of 7 arms (SENSEX 2026-09-22: -477 vs +2,069 Cr; NIFTY 2026-10-07: -4,046 vs +621 Cr). Vendor delta fails put-call parity (P6 note 4.1); this view does not use it. A reader may therefore see the standing-book Net DEX and the side of S* point opposite ways; neither is a dealer claim. NO DEALER CLAIM: open-interest delta; dealer side regime-dependent (P2). The magnitude of the curve is indicative only; the LEVEL is what is published. Never label second-order terms vanna or charm (L78-1). Runs with owner privileges (security_invoker false); adding a column here publishes it to anon.';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- CASE-2026-09-22, ADR-031 D6)
-- =====================================================================

REVOKE ALL ON public.v_dex_repriced_zero FROM anon, authenticated;
GRANT SELECT ON public.v_dex_repriced_zero TO anon, merdian_ro;

-- end-of-batch verification (TD-S94-NEW-3) -- must return ONE row:
--   has_view t | comment_len 3897 | comment_md5 0a78d9e8d0de8be13a2b7ed8253a027a
--   anon_r t | anon_write f | merdian_ro_r t | authenticated_r f
SELECT to_regclass('public.v_dex_repriced_zero') IS NOT NULL                              AS has_view,
       length(obj_description('public.v_dex_repriced_zero'::regclass, 'pg_class'))         AS comment_len,
       md5(obj_description('public.v_dex_repriced_zero'::regclass, 'pg_class'))            AS comment_md5,
       has_table_privilege('anon', 'public.v_dex_repriced_zero', 'SELECT')                 AS anon_r,
       has_table_privilege('anon', 'public.v_dex_repriced_zero', 'INSERT,UPDATE,DELETE,TRUNCATE') AS anon_write,
       has_table_privilege('merdian_ro', 'public.v_dex_repriced_zero', 'SELECT')           AS merdian_ro_r,
       has_table_privilege('authenticated', 'public.v_dex_repriced_zero', 'SELECT')        AS authenticated_r;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run after 1-3, one statement at a time)
-- =====================================================================

-- 4a  the anon path, in ONE execution with current_user beside the rows
--     (S84 settled form). PASS: role_now = anon, exactly 2 rows (NIFTY,
--     SENSEX), status OK / NO_CROSSING / UNMEASURABLE_R / SKIPPED_EXPIRY,
--     never NULL; when OK, cross_direction = neg->pos and n_cross_full_grid = 1.
BEGIN; SET LOCAL ROLE anon;
SELECT current_user AS role_now, symbol,
       to_char(ts AT TIME ZONE 'Asia/Kolkata', 'MM-DD HH24:MI') AS ts_ist,
       front_expiry, round(spot::numeric, 1) AS spot, status,
       round(zero_delta::numeric, 1) AS zero_delta, cross_direction,
       round(zero_sigma::numeric, 3) AS zero_sigma, n_cross_full_grid,
       round(net_dex_at_spot_cr::numeric, 1) AS net_at_spot_cr,
       n_legs_used, n_dropped_no_iv, n_dropped_other
  FROM public.v_dex_repriced_zero ORDER BY symbol;
COMMIT;

-- 4b  security_invoker not set (owner privileges, as v_dex_standing_book 4h).
--     PASS: reloptions NULL or without security_invoker=true.
SELECT c.relname, c.reloptions FROM pg_class c
 WHERE c.oid = 'public.v_dex_repriced_zero'::regclass;

-- 4c  cost. PASS: completes, no Seq Scan on option_chain_snapshots.
--     Recorded, not gated (ENH-131 measured 122.9 ms).
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_dex_repriced_zero;
