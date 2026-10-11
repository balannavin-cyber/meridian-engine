-- =====================================================================
-- 2026-10-12_s96_v_gex_greeks_l2_leg.sql
-- S96 / roadmap P7b step 1 (ruling S96-F) -- the per-leg base of ENH-98 L7/L8,
-- and v_gex_greeks_l2_strike re-pointed at it.
--   public.v_gex_greeks_l2_leg      NEW   grain (symbol, ts, expiry_date, strike, option_type)
--   public.v_gex_greeks_l2_strike   BODY REPLACED, columns / comment / grants unchanged
--   public.v_gex_greeks_l2_net      untouched (reads the strike view)
-- =====================================================================
--
-- AUTHORED 2026-10-12 (S96). NOTHING IN THIS FILE HAS BEEN RUN AGAINST THE DATABASE.
-- Maintenance on a BUILT layer (S95-D: parity not reopened). Design: P7 design note section 4,
-- option B1; ruling S96-F (E1 one base view with header columns and three flags; E2 price on
-- `priceable`; E3 gate C5; E4 base view first, flow view after).
--
-- WHY: L7/L8 publishes strike aggregates already multiplied by OI. Flow needs the per-contract
-- derivative times dOI, so the leg arithmetic must be readable on its own -- one implementation,
-- read by the strike view (x oi) and later by the flow view (x dOI).
--
-- THE SOURCE IS THE S89 FILE: sql/2026-10-03_s89_v_gex_greeks_l2.sql Section 1. The base view's
-- CTEs symbols .. rstats are that body VERBATIM; leg / bs / bs2 / bs3 / unit replace legs / evalleg /
-- bs / bs2 / bs3 / perleg; the strike view keeps the S89 agg and final SELECT. The S89 evaluation
-- order (sgn x unit x oi x spot / 1e7) is kept so the published numbers are bit-for-bit the S89
-- numbers, not merely within tolerance. C5-0 (below) first proves the S89 file IS the live body.
--
-- FIXTURE (S96, local Postgres 16, copy of the mp7 fixture + index_futures_snapshots at r = 6.5 %,
-- vendor gamma = Black-Scholes gamma at the vendor iv, plants at the NIFTY latest ts: a deep-ITM
-- guarded strike, a far small-gamma strike, a zero-OI strike; docs/research/s96_priority/p7/p7b/):
-- C5-0, C5-pre, C5-post all n 76 / 76, unmatched 0, mismatches 0, max_abs_diff 0, not-bitwise-equal 0.
-- Status branches, each in a rolled-back transaction, C5-post bit-for-bit: UNMEASURABLE_R (NIFTY
-- futures deleted, 27 rows), SKIPPED_EXPIRY (NIFTY front moved to dte 0, 51 rows), NO_LEGS (SENSEX
-- iv 0, 52 rows). Mutants, each caught by C5-post: sum over priceable instead of in_leg_set -> 1
-- unmatched (the zero-OI strike appears); deep-ITM guard dropped from in_leg_set -> 1 unmatched;
-- /100 written /10 -> max_abs_diff 31,358.55 on 76 rows; rstats join lost -> 79 unmatched.
-- NOT a mutant: multiplying oi before the unit (sgn x oi x unit) gave bit-for-bit equal output on
-- the fixture, so C5 does not -- and need not -- police the multiplication order; it polices values.
-- Not exercised on the fixture: the AS MATERIALIZED gate (cost only) -- measured live in Section C.
--
-- REVISED 2026-10-12 ~05:35 IST BEFORE ANY APPLY (committed f684f10 was never applied). The first
-- body joined rstats and gate to EVERY chain row inside `leg` and joined the unit CTE back to `leg`;
-- through roq on live data (2026-10-09 15:40 run, 398 strike rows) it ran 2,260.6 / 2,276.6 ms with
-- `CTE Scan on gate g ... loops=1724` -- rstats, referenced once, was inlined and recomputed per row,
-- and the unit join-back was a nested loop on a rows=1 estimate (the S83 shape, sql-views rule).
-- C5-0 on the same run PASSED (398 / 398, bit-for-bit), so the S89 file is the live body. Fix: a
-- header CTE `hx AS MATERIALIZED` (hdr + rstats + gate, one row per symbol / ts / expiry, as the S89
-- final SELECT joins them) and the Black-Scholes chain computed in place under CASE WHEN priceable
-- AND evaluable, with no join-back. Fixture after the fix: `CTE Scan on gate` and `CTE Scan on hx`
-- both loops=1; C5-pre / C5-post, all three status branches and all four mutants give the same
-- results as before (bit-for-bit PASS; mutants 1 / 1 / 76-row 31,358.55 / 79 unmatched).
--
-- APPLY ORDER (each its own execution, each batch ending with its own verification SELECT,
-- TD-S94-NEW-3):  C5-0 (read-only)  ->  Section A  ->  C5-pre  ->  Section B  ->  C5-post, C1-C3.
-- SECTIONS A AND B ARE LIVE STATEMENTS (TD-S81-NEW-5).
-- =====================================================================


-- =====================================================================
-- SECTION A -- the base view (new object)
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_greeks_l2_leg
WITH (security_invoker = false) AS
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
        -- idx_ocs_ts_symbol_expiry. NOT max(ts) GROUP BY symbol.
        -- NEVER created_at (S81, 89bc83e -- it hands back W2).
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
        -- BOTH expiry legs, unlike ENH-131 which keeps the front only.
        -- L78-3 requires W2 to compute as normal on expiry day. Capture
        -- stage 1 holds exactly W1 and W2; the MONTHLIES L78-3 also names
        -- ARE NOT CAPTURED (measured: n_expiry = 2 on every session
        -- 09-28..10-02, both symbols) and therefore cannot appear here.
        SELECT l.symbol, l.latest_ts AS ts,
               o.expiry_date, o.strike, o.option_type,
               o.iv, o.oi, o.gamma, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the expiry over a 365-day
        -- year -- ENH-131's convention, Gate 5 convention (b).
        SELECT s.symbol, s.ts, s.expiry_date,
               max(s.spot) AS spot,
               (s.expiry_date
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.expiry_date
     ), gate AS MATERIALIZED (
        -- ENH-133 D-3 clause 3, cut off at ts so there is no look-ahead.
        -- AS MATERIALIZED is load-bearing: see the header, 164 ms vs
        -- 26,424 ms on the two-construct precursor. Join is on
        -- (symbol, ts). This body measures 210.280 / 186.476 ms pre-apply,
        -- with `CTE Scan on gate g` at loops=1 in both plans.
        SELECT h.symbol, h.ts,
               (SELECT count(DISTINCT o2.spot) > 1
                  FROM option_chain_snapshots o2
                 WHERE o2.symbol = h.symbol
                   AND o2.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata')::date)
                                  ::timestamp) AT TIME ZONE 'Asia/Kolkata')
                   AND o2.ts <= h.ts) AS is_trading_session
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
     ), futwin AS (
        -- NO LOOK-AHEAD. 09:20 IST on the ts date through ts INCLUSIVE.
        SELECT DISTINCT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE, which is not always the option front.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry, T_f from THAT ROW's own ts. F and S are from
        -- the same row, so they are contemporaneous by construction.
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
        -- Fewer than 6 rows is UNMEASURABLE, never a substituted default
        -- (ADR-023 D1: fail to absent, never to stale).
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess
          FROM rrows
         GROUP BY symbol, ts
     ), hx AS MATERIALIZED (
        -- S96-F: the header joined ONCE to its rate and session gate (4 rows), as the S89 final
        -- SELECT does. MATERIALIZED so rstats (referenced only here) is computed once, not once per
        -- chain row -- measured S96: joining rstats and gate per chain row ran 2,261 ms with the gate
        -- scanned 1,724 times (the S83 inlining shape, sql-views rule).
        SELECT h.symbol, h.ts, h.expiry_date, h.spot, h.dte, h.t_years,
               r.r_sess, COALESCE(r.n_r_rows, 0) AS n_r_rows,
               g.is_trading_session
          FROM hdr h
          LEFT JOIN rstats r ON r.symbol = h.symbol AND r.ts = h.ts
          LEFT JOIN gate   g ON g.symbol = h.symbol AND g.ts = h.ts
     ), leg AS (
        -- S96-F: EVERY chain row at the latest ts, both legs, with three flags. in_leg_set is
        -- ENH-131's leg set byte-for-byte (the predicates the strike view sums over); priceable is
        -- the same predicates WITHOUT oi > 0 (S96-F E2: a leg whose OI went to zero can still be
        -- valued for flow); evaluable is the S89 evalleg filter. COALESCE(.., false) because a WHERE
        -- treats NULL as false and these flags must say the same.
        SELECT s.symbol, s.ts, s.expiry_date, s.strike, s.option_type,
               x.spot, x.dte, x.t_years, x.r_sess, x.n_r_rows, x.is_trading_session,
               s.oi AS oi_qty, s.iv, s.gamma,
               s.strike::double precision       AS k,
               (CASE WHEN s.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                                                AS sgn,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi,
               COALESCE(s.oi > 0
                    AND s.gamma IS NOT NULL AND s.gamma <> 0
                    AND s.iv > 0
                    AND NOT (abs(s.strike - x.spot) / x.spot > 0.05
                             AND abs(s.gamma) > 5e-5), false) AS in_leg_set,
               COALESCE(s.gamma IS NOT NULL AND s.gamma <> 0
                    AND s.iv > 0
                    AND NOT (abs(s.strike - x.spot) / x.spot > 0.05
                             AND abs(s.gamma) > 5e-5), false) AS priceable,
               COALESCE(x.dte > 0 AND x.t_years > 0
                    AND x.n_r_rows >= 6
                    AND x.r_sess IS NOT NULL, false)          AS evaluable
          FROM scoped s
          JOIN hx x
            ON x.symbol = s.symbol AND x.ts = s.ts
           AND x.expiry_date = s.expiry_date
     ), bs AS (
        -- The S89 Black-Scholes chain, each expression verbatim inside CASE WHEN priceable AND
        -- evaluable (a CASE is evaluated lazily, so sqrt / ln never see a row that would raise).
        SELECT b.*,
               CASE WHEN b.priceable AND b.evaluable THEN
               ( ln(b.spot / b.k)
                 + (b.r_sess + 0.5 * power(b.sigma, 2)) * b.t_years )
               / (b.sigma * sqrt(b.t_years)) END               AS d1
          FROM leg b
     ), bs2 AS (
        SELECT b.*,
               CASE WHEN b.priceable AND b.evaluable THEN b.d1 - b.sigma * sqrt(b.t_years) END   AS d2,
               CASE WHEN b.priceable AND b.evaluable THEN exp(-0.5 * power(b.d1, 2)) / sqrt(2.0 * pi()) END AS nd1,
               CASE WHEN b.priceable AND b.evaluable THEN
               (b.r_sess + 0.5 * power(b.sigma, 2))
                 / (b.sigma * sqrt(b.t_years))
                 - b.d1 / (2.0 * b.t_years) END                AS dd1_dt
          FROM bs b
     ), bs3 AS (
        SELECT b.*,
               CASE WHEN b.priceable AND b.evaluable THEN b.nd1 / (b.spot * b.sigma * sqrt(b.t_years)) END AS bs_gamma
          FROM bs2 b
     )
-- The four per-CONTRACT derivatives, unsigned and unscaled: exactly the sub-expressions the S89
-- perleg CTE multiplied by sgn, oi and spot. /100 = per IV point, /365 = per calendar day.
SELECT b.symbol, b.ts, b.expiry_date, b.strike, b.option_type,
       b.spot, b.dte, b.t_years, b.r_sess, b.n_r_rows, b.is_trading_session,
       b.oi_qty, b.iv, b.gamma, b.k, b.sgn, b.sigma, b.oi,
       b.in_leg_set, b.priceable, b.evaluable,
       b.d1, b.d2,
       CASE WHEN b.priceable AND b.evaluable THEN ((-b.nd1 * b.d2 / b.sigma) / 100.0) END                    AS u_delta_drift_iv,
       CASE WHEN b.priceable AND b.evaluable THEN ((-b.nd1 * b.dd1_dt) / 365.0) END                          AS u_delta_drift_time,
       CASE WHEN b.priceable AND b.evaluable THEN ((b.bs_gamma * (b.d1 * b.d2 - 1.0) / b.sigma) / 100.0) END AS u_gex_drift_iv,
       CASE WHEN b.priceable AND b.evaluable THEN ((b.bs_gamma * (b.d1 * b.dd1_dt
                                    + 1.0 / (2.0 * b.t_years))) / 365.0) END        AS u_gex_drift_time
  FROM bs3 b;

COMMENT ON VIEW public.v_gex_greeks_l2_leg IS
  'S96 / roadmap P7b step 1 / ruling S96-F -- the PER-LEG base of ENH-98 L7/L8. One row per option_chain_snapshots row at the LATEST chain ts per symbol, BOTH captured expiry legs, grain (symbol, ts, expiry_date, strike, option_type). NOT a parity layer; display-only (S37); routes nothing; makes NO PREDICTIVE CLAIM. It carries the S89 v_gex_greeks_l2_strike scoping, header (spot, dte, t_years exact/365), session gate (AS MATERIALIZED, load-bearing), futures-implied r_sess (median, UNMEASURABLE below 6 rows) and Black-Scholes chain VERBATIM, so v_gex_greeks_l2_strike now reads this view and multiplies by sgn x oi x spot / 1e7 (x spot again for the gamma pair) in the S89 evaluation order: gate C5 compared the two bodies column by column and found them bit-for-bit equal. FLAGS: in_leg_set is the ENH-131 leg set (oi > 0, vendor gamma non-zero, iv > 0, TD-NEW-2 deep-ITM guard) -- the legs the strike view sums; priceable is the same predicates WITHOUT oi > 0, so a leg whose OI went to zero can still be valued for flow (S96-F E2); evaluable is dte > 0, T > 0 and r measurable. A NULL flag input reads false, as a WHERE would. UNIT COLUMNS u_delta_drift_iv, u_delta_drift_time, u_gex_drift_iv, u_gex_drift_time are PER-CONTRACT derivatives, UNSIGNED and UNSCALED: d(delta)/d(sigma)/100 (per IV point), d(delta)/dt/365 (per calendar day), d(gamma)/d(sigma)/100, d(gamma)/dt/365 -- no sgn, no oi, no spot. NULL unless priceable and evaluable; a NULL is a gap, never a zero. With q = 0 they are identical for CE and PE at equal sigma, but each leg carries its own vendor iv, so CE and PE differ in practice. sgn is -1 on PE (the S89 dealer assumption) and is NOT applied here. No OI arithmetic is done in this view beyond carrying oi; consumers multiply. Runs with the owner privileges (security_invoker = false); anon reads it only through views built on it. Never label second-order terms vanna or charm (L78-1).';

REVOKE ALL ON public.v_gex_greeks_l2_leg FROM anon, authenticated;
GRANT SELECT ON public.v_gex_greeks_l2_leg TO merdian_ro;

-- end-of-batch verification (TD-S94-NEW-3) -- must return ONE row:
--   has_view t | comment_len 1916 (computed from the literal in this file, '' unescaped) |
--   anon_r f | anon_write f | merdian_ro_r t | authenticated_r f
SELECT to_regclass('public.v_gex_greeks_l2_leg') IS NOT NULL                          AS has_view,
       length(obj_description('public.v_gex_greeks_l2_leg'::regclass, 'pg_class'))     AS comment_len,
       has_table_privilege('anon', 'public.v_gex_greeks_l2_leg', 'SELECT')             AS anon_r,
       (has_table_privilege('anon', 'public.v_gex_greeks_l2_leg', 'INSERT')
        OR has_table_privilege('anon', 'public.v_gex_greeks_l2_leg', 'UPDATE')
        OR has_table_privilege('anon', 'public.v_gex_greeks_l2_leg', 'DELETE'))        AS anon_write,
       has_table_privilege('merdian_ro', 'public.v_gex_greeks_l2_leg', 'SELECT')       AS merdian_ro_r,
       has_table_privilege('authenticated', 'public.v_gex_greeks_l2_leg', 'SELECT')    AS authenticated_r;


-- =====================================================================
-- SECTION B -- v_gex_greeks_l2_strike re-pointed at the base (same columns)
-- CREATE OR REPLACE keeps the object, its COMMENT and its GRANTs; the batch verifies all three
-- against the S89 values (comment_len 8642 / md5 3d96fcaf... are the S89 file's V4 figures,
-- computed there from its literal).
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_greeks_l2_strike AS
WITH b AS (
        -- S96-F: the leg arithmetic lives in v_gex_greeks_l2_leg; this view
        -- multiplies by sgn, oi and spot in the S89 evaluation order, so the
        -- published numbers are the S89 numbers (gate C5).
        SELECT * FROM public.v_gex_greeks_l2_leg
     ), hdr AS (
        SELECT DISTINCT symbol, ts, expiry_date, spot, dte, t_years,
                        r_sess, n_r_rows, is_trading_session
          FROM b
     ), perleg AS (
        SELECT b.symbol, b.ts, b.expiry_date, b.dte, b.spot, b.k,
               b.sgn * b.u_delta_drift_iv
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_iv,
               b.sgn * b.u_delta_drift_time
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_time,
               b.sgn * b.u_gex_drift_iv
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_iv,
               b.sgn * b.u_gex_drift_time
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_time
          FROM b
         WHERE b.in_leg_set AND b.evaluable
     ), agg AS (
        SELECT symbol, ts, expiry_date, dte, spot, k,
               count(*)::integer           AS n_legs,
               sum(leg_delta_drift_iv)     AS delta_drift_iv_cr_per_volpt,
               sum(leg_delta_drift_time)   AS delta_drift_time_cr_per_day,
               sum(leg_gex_drift_iv)       AS gex_drift_iv_cr_per_volpt,
               sum(leg_gex_drift_time)     AS gex_drift_time_cr_per_day,
               sum(abs(leg_delta_drift_iv))   AS gross_delta_drift_iv,
               sum(abs(leg_delta_drift_time)) AS gross_delta_drift_time,
               sum(abs(leg_gex_drift_iv))     AS gross_gex_drift_iv,
               sum(abs(leg_gex_drift_time))   AS gross_gex_drift_time
          FROM perleg
         GROUP BY symbol, ts, expiry_date, dte, spot, k
     )
SELECT
    h.symbol,
    h.ts,
    h.expiry_date,
    h.dte,
    h.spot,
    a.k                                          AS strike,
    h.is_trading_session,
    (h.t_years * 365.0)                          AS t_days,
    h.r_sess,
    h.n_r_rows,
    a.n_legs,
    a.delta_drift_iv_cr_per_volpt,
    a.delta_drift_time_cr_per_day,
    a.gex_drift_iv_cr_per_volpt,
    a.gex_drift_time_cr_per_day,
    a.gross_delta_drift_iv,
    a.gross_delta_drift_time,
    a.gross_gex_drift_iv,
    a.gross_gex_drift_time,
    CASE WHEN h.dte = 0                       THEN 'SKIPPED_EXPIRY'
         WHEN h.n_r_rows < 6                  THEN 'UNMEASURABLE_R'
         WHEN a.k IS NULL                     THEN 'NO_LEGS'
         ELSE 'OK'
    END                                          AS status
  FROM hdr h
  LEFT JOIN agg    a  ON a.symbol  = h.symbol AND a.ts  = h.ts
                     AND a.expiry_date = h.expiry_date;

-- end-of-batch verification -- must return ONE row:
--   comment_len 8642 | comment_md5 3d96fcaf21b19318a8305a1b12f2d262 | anon_r t | anon_write f |
--   merdian_ro_r t | reads_leg t
SELECT length(obj_description('public.v_gex_greeks_l2_strike'::regclass, 'pg_class'))  AS comment_len,
       md5(obj_description('public.v_gex_greeks_l2_strike'::regclass, 'pg_class'))     AS comment_md5,
       has_table_privilege('anon', 'public.v_gex_greeks_l2_strike', 'SELECT')          AS anon_r,
       (has_table_privilege('anon', 'public.v_gex_greeks_l2_strike', 'INSERT')
        OR has_table_privilege('anon', 'public.v_gex_greeks_l2_strike', 'UPDATE')
        OR has_table_privilege('anon', 'public.v_gex_greeks_l2_strike', 'DELETE'))     AS anon_write,
       has_table_privilege('merdian_ro', 'public.v_gex_greeks_l2_strike', 'SELECT')    AS merdian_ro_r,
       pg_get_viewdef('public.v_gex_greeks_l2_strike'::regclass) LIKE '%v_gex_greeks_l2_leg%' AS reads_leg;


-- =====================================================================
-- SECTION C -- checks. ONE STATEMENT PER RUN. Each states what fails it.
-- C5 statements compare two bodies IN ONE STATEMENT, so both read one snapshot: they are valid
-- in market hours, when the latest ts moves between runs.
-- C5 fails if: the row sets differ (n, unmatched), any text / boolean / integer column differs,
-- a NULL appears on one side only, or any numeric column differs. PASS: n equal, n_unmatched 0,
-- n_exact_mismatch 0, n_null_mismatch 0, max_abs_diff 0 (gate <= 1e-9 Cr; 0 expected),
-- n_not_bitwise_equal 0, n_ok_rows > 0.
-- =====================================================================

-- C5-0  live v_gex_greeks_l2_strike vs the S89 file body inline. PASS: n equal, unmatched 0, mismatches 0, max_abs_diff 0.
WITH live AS (
SELECT * FROM public.v_gex_greeks_l2_strike
), file AS (
SELECT * FROM (
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
        -- idx_ocs_ts_symbol_expiry. NOT max(ts) GROUP BY symbol.
        -- NEVER created_at (S81, 89bc83e -- it hands back W2).
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
        -- BOTH expiry legs, unlike ENH-131 which keeps the front only.
        -- L78-3 requires W2 to compute as normal on expiry day. Capture
        -- stage 1 holds exactly W1 and W2; the MONTHLIES L78-3 also names
        -- ARE NOT CAPTURED (measured: n_expiry = 2 on every session
        -- 09-28..10-02, both symbols) and therefore cannot appear here.
        SELECT l.symbol, l.latest_ts AS ts,
               o.expiry_date, o.strike, o.option_type,
               o.iv, o.oi, o.gamma, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the expiry over a 365-day
        -- year -- ENH-131's convention, Gate 5 convention (b).
        SELECT s.symbol, s.ts, s.expiry_date,
               max(s.spot) AS spot,
               (s.expiry_date
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.expiry_date
     ), gate AS MATERIALIZED (
        -- ENH-133 D-3 clause 3, cut off at ts so there is no look-ahead.
        -- AS MATERIALIZED is load-bearing: see the header, 164 ms vs
        -- 26,424 ms on the two-construct precursor. Join is on
        -- (symbol, ts). This body measures 210.280 / 186.476 ms pre-apply,
        -- with `CTE Scan on gate g` at loops=1 in both plans.
        SELECT h.symbol, h.ts,
               (SELECT count(DISTINCT o2.spot) > 1
                  FROM option_chain_snapshots o2
                 WHERE o2.symbol = h.symbol
                   AND o2.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata')::date)
                                  ::timestamp) AT TIME ZONE 'Asia/Kolkata')
                   AND o2.ts <= h.ts) AS is_trading_session
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
     ), futwin AS (
        -- NO LOOK-AHEAD. 09:20 IST on the ts date through ts INCLUSIVE.
        SELECT DISTINCT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE, which is not always the option front.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry, T_f from THAT ROW's own ts. F and S are from
        -- the same row, so they are contemporaneous by construction.
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
        -- Fewer than 6 rows is UNMEASURABLE, never a substituted default
        -- (ADR-023 D1: fail to absent, never to stale).
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess
          FROM rrows
         GROUP BY symbol, ts
     ), legs AS (
        -- ENH-131's leg set, byte-for-byte in its predicates: oi above
        -- zero, vendor gamma non-zero, iv above zero, and the TD-NEW-2
        -- deep-ITM guard. The guard rejects spurious VENDOR gamma; it is
        -- kept so L3 and L7/L8 price the SAME legs and remain reconcilable.
        SELECT s.symbol, s.ts, s.expiry_date,
               h.spot, h.dte, h.t_years,
               r.r_sess, COALESCE(r.n_r_rows, 0) AS n_r_rows,
               s.strike::double precision       AS k,
               (CASE WHEN s.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                                                AS sgn,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h
            ON h.symbol = s.symbol AND h.ts = s.ts
           AND h.expiry_date = s.expiry_date
          LEFT JOIN rstats r ON r.symbol = s.symbol AND r.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), evalleg AS (
        -- Only legs that can carry a number reach the arithmetic. dte 0
        -- and a thin r window drop out here and are labelled in status.
        SELECT l.*
          FROM legs l
         WHERE l.dte > 0 AND l.t_years > 0
           AND l.n_r_rows >= 6 AND l.r_sess IS NOT NULL
     ), bs AS (
        SELECT e.*,
               ( ln(e.spot / e.k)
                 + (e.r_sess + 0.5 * power(e.sigma, 2)) * e.t_years )
               / (e.sigma * sqrt(e.t_years))                   AS d1
          FROM evalleg e
     ), bs2 AS (
        SELECT b.*,
               b.d1 - b.sigma * sqrt(b.t_years)                AS d2,
               exp(-0.5 * power(b.d1, 2)) / sqrt(2.0 * pi())   AS nd1,
               (b.r_sess + 0.5 * power(b.sigma, 2))
                 / (b.sigma * sqrt(b.t_years))
                 - b.d1 / (2.0 * b.t_years)                    AS dd1_dt
          FROM bs b
     ), bs3 AS (
        SELECT b.*,
               b.nd1 / (b.spot * b.sigma * sqrt(b.t_years))    AS bs_gamma
          FROM bs2 b
     ), perleg AS (
        -- The four constructs, scaled to their stated units. /100 is the
        -- per-IV-POINT step; /365 is the per-CALENDAR-DAY step; /1e7 is
        -- the Crore convention (TD-NEW-3). The delta pair carries one
        -- power of spot, the gamma pair two -- matching gex_cr.
        SELECT b.symbol, b.ts, b.expiry_date, b.dte, b.spot, b.k,
               b.sgn * ((-b.nd1 * b.d2 / b.sigma) / 100.0)
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_iv,
               b.sgn * ((-b.nd1 * b.dd1_dt) / 365.0)
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_time,
               b.sgn * ((b.bs_gamma * (b.d1 * b.d2 - 1.0) / b.sigma) / 100.0)
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_iv,
               b.sgn * ((b.bs_gamma * (b.d1 * b.dd1_dt
                                       + 1.0 / (2.0 * b.t_years))) / 365.0)
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_time
          FROM bs3 b
     ), agg AS (
        SELECT symbol, ts, expiry_date, dte, spot, k,
               count(*)::integer           AS n_legs,
               sum(leg_delta_drift_iv)     AS delta_drift_iv_cr_per_volpt,
               sum(leg_delta_drift_time)   AS delta_drift_time_cr_per_day,
               sum(leg_gex_drift_iv)       AS gex_drift_iv_cr_per_volpt,
               sum(leg_gex_drift_time)     AS gex_drift_time_cr_per_day,
               sum(abs(leg_delta_drift_iv))   AS gross_delta_drift_iv,
               sum(abs(leg_delta_drift_time)) AS gross_delta_drift_time,
               sum(abs(leg_gex_drift_iv))     AS gross_gex_drift_iv,
               sum(abs(leg_gex_drift_time))   AS gross_gex_drift_time
          FROM perleg
         GROUP BY symbol, ts, expiry_date, dte, spot, k
     )
SELECT
    h.symbol,
    h.ts,
    h.expiry_date,
    h.dte,
    h.spot,
    a.k                                          AS strike,
    g.is_trading_session,
    (h.t_years * 365.0)                          AS t_days,
    rr.r_sess,
    COALESCE(rr.n_r_rows, 0)                     AS n_r_rows,
    a.n_legs,
    a.delta_drift_iv_cr_per_volpt,
    a.delta_drift_time_cr_per_day,
    a.gex_drift_iv_cr_per_volpt,
    a.gex_drift_time_cr_per_day,
    a.gross_delta_drift_iv,
    a.gross_delta_drift_time,
    a.gross_gex_drift_iv,
    a.gross_gex_drift_time,
    -- Precedence is deliberate and matches ENH-131: an expiry-day cycle
    -- is skipped whatever else is true of it.
    CASE WHEN h.dte = 0                       THEN 'SKIPPED_EXPIRY'
         WHEN COALESCE(rr.n_r_rows, 0) < 6    THEN 'UNMEASURABLE_R'
         WHEN a.k IS NULL                     THEN 'NO_LEGS'
         ELSE 'OK'
    END                                          AS status
  FROM hdr h
  LEFT JOIN rstats rr ON rr.symbol = h.symbol AND rr.ts = h.ts
  LEFT JOIN gate   g  ON g.symbol  = h.symbol AND g.ts  = h.ts
  LEFT JOIN agg    a  ON a.symbol  = h.symbol AND a.ts  = h.ts
                     AND a.expiry_date = h.expiry_date
) f
), j AS (
SELECT o.*, n.symbol AS n_symbol, n.spot AS n_spot, n.t_days AS n_t_days, n.r_sess AS n_r_sess, n.delta_drift_iv_cr_per_volpt AS n_delta_drift_iv_cr_per_volpt, n.delta_drift_time_cr_per_day AS n_delta_drift_time_cr_per_day, n.gex_drift_iv_cr_per_volpt AS n_gex_drift_iv_cr_per_volpt, n.gex_drift_time_cr_per_day AS n_gex_drift_time_cr_per_day, n.gross_delta_drift_iv AS n_gross_delta_drift_iv, n.gross_delta_drift_time AS n_gross_delta_drift_time, n.gross_gex_drift_iv AS n_gross_gex_drift_iv, n.gross_gex_drift_time AS n_gross_gex_drift_time, n.dte AS n_dte, n.is_trading_session AS n_is_trading_session, n.n_r_rows AS n_n_r_rows, n.n_legs AS n_n_legs, n.status AS n_status
  FROM live o
  FULL OUTER JOIN file n
    ON n.symbol = o.symbol AND n.ts = o.ts AND n.expiry_date = o.expiry_date
   AND n.strike IS NOT DISTINCT FROM o.strike
)
SELECT (SELECT count(*) FROM live) AS n_live, (SELECT count(*) FROM file) AS n_file,
       count(*) FILTER (WHERE symbol IS NULL OR n_symbol IS NULL) AS n_unmatched,
       count(*) FILTER (WHERE (dte) IS DISTINCT FROM (n_dte) OR (is_trading_session) IS DISTINCT FROM (n_is_trading_session) OR (n_r_rows) IS DISTINCT FROM (n_n_r_rows) OR (n_legs) IS DISTINCT FROM (n_n_legs) OR (status) IS DISTINCT FROM (n_status)) AS n_exact_mismatch,
       count(*) FILTER (WHERE ((spot) IS NULL) <> ((n_spot) IS NULL) OR ((t_days) IS NULL) <> ((n_t_days) IS NULL) OR ((r_sess) IS NULL) <> ((n_r_sess) IS NULL) OR ((delta_drift_iv_cr_per_volpt) IS NULL) <> ((n_delta_drift_iv_cr_per_volpt) IS NULL) OR ((delta_drift_time_cr_per_day) IS NULL) <> ((n_delta_drift_time_cr_per_day) IS NULL) OR ((gex_drift_iv_cr_per_volpt) IS NULL) <> ((n_gex_drift_iv_cr_per_volpt) IS NULL) OR ((gex_drift_time_cr_per_day) IS NULL) <> ((n_gex_drift_time_cr_per_day) IS NULL) OR ((gross_delta_drift_iv) IS NULL) <> ((n_gross_delta_drift_iv) IS NULL) OR ((gross_delta_drift_time) IS NULL) <> ((n_gross_delta_drift_time) IS NULL) OR ((gross_gex_drift_iv) IS NULL) <> ((n_gross_gex_drift_iv) IS NULL) OR ((gross_gex_drift_time) IS NULL) <> ((n_gross_gex_drift_time) IS NULL)) AS n_null_mismatch,
       greatest(max(abs((spot)::float8 - (n_spot)::float8)), max(abs((t_days)::float8 - (n_t_days)::float8)), max(abs((r_sess)::float8 - (n_r_sess)::float8)), max(abs((delta_drift_iv_cr_per_volpt)::float8 - (n_delta_drift_iv_cr_per_volpt)::float8)), max(abs((delta_drift_time_cr_per_day)::float8 - (n_delta_drift_time_cr_per_day)::float8)), max(abs((gex_drift_iv_cr_per_volpt)::float8 - (n_gex_drift_iv_cr_per_volpt)::float8)), max(abs((gex_drift_time_cr_per_day)::float8 - (n_gex_drift_time_cr_per_day)::float8)), max(abs((gross_delta_drift_iv)::float8 - (n_gross_delta_drift_iv)::float8)), max(abs((gross_delta_drift_time)::float8 - (n_gross_delta_drift_time)::float8)), max(abs((gross_gex_drift_iv)::float8 - (n_gross_gex_drift_iv)::float8)), max(abs((gross_gex_drift_time)::float8 - (n_gross_gex_drift_time)::float8))) AS max_abs_diff,
       count(*) FILTER (WHERE (spot) IS DISTINCT FROM (n_spot) OR (t_days) IS DISTINCT FROM (n_t_days) OR (r_sess) IS DISTINCT FROM (n_r_sess) OR (delta_drift_iv_cr_per_volpt) IS DISTINCT FROM (n_delta_drift_iv_cr_per_volpt) OR (delta_drift_time_cr_per_day) IS DISTINCT FROM (n_delta_drift_time_cr_per_day) OR (gex_drift_iv_cr_per_volpt) IS DISTINCT FROM (n_gex_drift_iv_cr_per_volpt) OR (gex_drift_time_cr_per_day) IS DISTINCT FROM (n_gex_drift_time_cr_per_day) OR (gross_delta_drift_iv) IS DISTINCT FROM (n_gross_delta_drift_iv) OR (gross_delta_drift_time) IS DISTINCT FROM (n_gross_delta_drift_time) OR (gross_gex_drift_iv) IS DISTINCT FROM (n_gross_gex_drift_iv) OR (gross_gex_drift_time) IS DISTINCT FROM (n_gross_gex_drift_time)) AS n_not_bitwise_equal,
       count(*) FILTER (WHERE status = 'OK') AS n_ok_rows
  FROM j;

-- C5-pre  live (S89) strike view vs the S96-F strike body inline (reads v_gex_greeks_l2_leg). PASS as C5-0.
WITH live AS (
SELECT * FROM public.v_gex_greeks_l2_strike
), newbody AS (
SELECT * FROM (
WITH b AS (
        -- S96-F: the leg arithmetic lives in v_gex_greeks_l2_leg; this view
        -- multiplies by sgn, oi and spot in the S89 evaluation order, so the
        -- published numbers are the S89 numbers (gate C5).
        SELECT * FROM public.v_gex_greeks_l2_leg
     ), hdr AS (
        SELECT DISTINCT symbol, ts, expiry_date, spot, dte, t_years,
                        r_sess, n_r_rows, is_trading_session
          FROM b
     ), perleg AS (
        SELECT b.symbol, b.ts, b.expiry_date, b.dte, b.spot, b.k,
               b.sgn * b.u_delta_drift_iv
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_iv,
               b.sgn * b.u_delta_drift_time
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_time,
               b.sgn * b.u_gex_drift_iv
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_iv,
               b.sgn * b.u_gex_drift_time
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_time
          FROM b
         WHERE b.in_leg_set AND b.evaluable
     ), agg AS (
        SELECT symbol, ts, expiry_date, dte, spot, k,
               count(*)::integer           AS n_legs,
               sum(leg_delta_drift_iv)     AS delta_drift_iv_cr_per_volpt,
               sum(leg_delta_drift_time)   AS delta_drift_time_cr_per_day,
               sum(leg_gex_drift_iv)       AS gex_drift_iv_cr_per_volpt,
               sum(leg_gex_drift_time)     AS gex_drift_time_cr_per_day,
               sum(abs(leg_delta_drift_iv))   AS gross_delta_drift_iv,
               sum(abs(leg_delta_drift_time)) AS gross_delta_drift_time,
               sum(abs(leg_gex_drift_iv))     AS gross_gex_drift_iv,
               sum(abs(leg_gex_drift_time))   AS gross_gex_drift_time
          FROM perleg
         GROUP BY symbol, ts, expiry_date, dte, spot, k
     )
SELECT
    h.symbol,
    h.ts,
    h.expiry_date,
    h.dte,
    h.spot,
    a.k                                          AS strike,
    h.is_trading_session,
    (h.t_years * 365.0)                          AS t_days,
    h.r_sess,
    h.n_r_rows,
    a.n_legs,
    a.delta_drift_iv_cr_per_volpt,
    a.delta_drift_time_cr_per_day,
    a.gex_drift_iv_cr_per_volpt,
    a.gex_drift_time_cr_per_day,
    a.gross_delta_drift_iv,
    a.gross_delta_drift_time,
    a.gross_gex_drift_iv,
    a.gross_gex_drift_time,
    CASE WHEN h.dte = 0                       THEN 'SKIPPED_EXPIRY'
         WHEN h.n_r_rows < 6                  THEN 'UNMEASURABLE_R'
         WHEN a.k IS NULL                     THEN 'NO_LEGS'
         ELSE 'OK'
    END                                          AS status
  FROM hdr h
  LEFT JOIN agg    a  ON a.symbol  = h.symbol AND a.ts  = h.ts
                     AND a.expiry_date = h.expiry_date
) f
), j AS (
SELECT o.*, n.symbol AS n_symbol, n.spot AS n_spot, n.t_days AS n_t_days, n.r_sess AS n_r_sess, n.delta_drift_iv_cr_per_volpt AS n_delta_drift_iv_cr_per_volpt, n.delta_drift_time_cr_per_day AS n_delta_drift_time_cr_per_day, n.gex_drift_iv_cr_per_volpt AS n_gex_drift_iv_cr_per_volpt, n.gex_drift_time_cr_per_day AS n_gex_drift_time_cr_per_day, n.gross_delta_drift_iv AS n_gross_delta_drift_iv, n.gross_delta_drift_time AS n_gross_delta_drift_time, n.gross_gex_drift_iv AS n_gross_gex_drift_iv, n.gross_gex_drift_time AS n_gross_gex_drift_time, n.dte AS n_dte, n.is_trading_session AS n_is_trading_session, n.n_r_rows AS n_n_r_rows, n.n_legs AS n_n_legs, n.status AS n_status
  FROM live o
  FULL OUTER JOIN newbody n
    ON n.symbol = o.symbol AND n.ts = o.ts AND n.expiry_date = o.expiry_date
   AND n.strike IS NOT DISTINCT FROM o.strike
)
SELECT (SELECT count(*) FROM live) AS n_live, (SELECT count(*) FROM newbody) AS n_newbody,
       count(*) FILTER (WHERE symbol IS NULL OR n_symbol IS NULL) AS n_unmatched,
       count(*) FILTER (WHERE (dte) IS DISTINCT FROM (n_dte) OR (is_trading_session) IS DISTINCT FROM (n_is_trading_session) OR (n_r_rows) IS DISTINCT FROM (n_n_r_rows) OR (n_legs) IS DISTINCT FROM (n_n_legs) OR (status) IS DISTINCT FROM (n_status)) AS n_exact_mismatch,
       count(*) FILTER (WHERE ((spot) IS NULL) <> ((n_spot) IS NULL) OR ((t_days) IS NULL) <> ((n_t_days) IS NULL) OR ((r_sess) IS NULL) <> ((n_r_sess) IS NULL) OR ((delta_drift_iv_cr_per_volpt) IS NULL) <> ((n_delta_drift_iv_cr_per_volpt) IS NULL) OR ((delta_drift_time_cr_per_day) IS NULL) <> ((n_delta_drift_time_cr_per_day) IS NULL) OR ((gex_drift_iv_cr_per_volpt) IS NULL) <> ((n_gex_drift_iv_cr_per_volpt) IS NULL) OR ((gex_drift_time_cr_per_day) IS NULL) <> ((n_gex_drift_time_cr_per_day) IS NULL) OR ((gross_delta_drift_iv) IS NULL) <> ((n_gross_delta_drift_iv) IS NULL) OR ((gross_delta_drift_time) IS NULL) <> ((n_gross_delta_drift_time) IS NULL) OR ((gross_gex_drift_iv) IS NULL) <> ((n_gross_gex_drift_iv) IS NULL) OR ((gross_gex_drift_time) IS NULL) <> ((n_gross_gex_drift_time) IS NULL)) AS n_null_mismatch,
       greatest(max(abs((spot)::float8 - (n_spot)::float8)), max(abs((t_days)::float8 - (n_t_days)::float8)), max(abs((r_sess)::float8 - (n_r_sess)::float8)), max(abs((delta_drift_iv_cr_per_volpt)::float8 - (n_delta_drift_iv_cr_per_volpt)::float8)), max(abs((delta_drift_time_cr_per_day)::float8 - (n_delta_drift_time_cr_per_day)::float8)), max(abs((gex_drift_iv_cr_per_volpt)::float8 - (n_gex_drift_iv_cr_per_volpt)::float8)), max(abs((gex_drift_time_cr_per_day)::float8 - (n_gex_drift_time_cr_per_day)::float8)), max(abs((gross_delta_drift_iv)::float8 - (n_gross_delta_drift_iv)::float8)), max(abs((gross_delta_drift_time)::float8 - (n_gross_delta_drift_time)::float8)), max(abs((gross_gex_drift_iv)::float8 - (n_gross_gex_drift_iv)::float8)), max(abs((gross_gex_drift_time)::float8 - (n_gross_gex_drift_time)::float8))) AS max_abs_diff,
       count(*) FILTER (WHERE (spot) IS DISTINCT FROM (n_spot) OR (t_days) IS DISTINCT FROM (n_t_days) OR (r_sess) IS DISTINCT FROM (n_r_sess) OR (delta_drift_iv_cr_per_volpt) IS DISTINCT FROM (n_delta_drift_iv_cr_per_volpt) OR (delta_drift_time_cr_per_day) IS DISTINCT FROM (n_delta_drift_time_cr_per_day) OR (gex_drift_iv_cr_per_volpt) IS DISTINCT FROM (n_gex_drift_iv_cr_per_volpt) OR (gex_drift_time_cr_per_day) IS DISTINCT FROM (n_gex_drift_time_cr_per_day) OR (gross_delta_drift_iv) IS DISTINCT FROM (n_gross_delta_drift_iv) OR (gross_delta_drift_time) IS DISTINCT FROM (n_gross_delta_drift_time) OR (gross_gex_drift_iv) IS DISTINCT FROM (n_gross_gex_drift_iv) OR (gross_gex_drift_time) IS DISTINCT FROM (n_gross_gex_drift_time)) AS n_not_bitwise_equal,
       count(*) FILTER (WHERE status = 'OK') AS n_ok_rows
  FROM j;

-- C5-post  the S89 file body inline vs live (S96-F) strike view. PASS as C5-0.
WITH s89 AS (
SELECT * FROM (
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
        -- idx_ocs_ts_symbol_expiry. NOT max(ts) GROUP BY symbol.
        -- NEVER created_at (S81, 89bc83e -- it hands back W2).
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
        -- BOTH expiry legs, unlike ENH-131 which keeps the front only.
        -- L78-3 requires W2 to compute as normal on expiry day. Capture
        -- stage 1 holds exactly W1 and W2; the MONTHLIES L78-3 also names
        -- ARE NOT CAPTURED (measured: n_expiry = 2 on every session
        -- 09-28..10-02, both symbols) and therefore cannot appear here.
        SELECT l.symbol, l.latest_ts AS ts,
               o.expiry_date, o.strike, o.option_type,
               o.iv, o.oi, o.gamma, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the expiry over a 365-day
        -- year -- ENH-131's convention, Gate 5 convention (b).
        SELECT s.symbol, s.ts, s.expiry_date,
               max(s.spot) AS spot,
               (s.expiry_date
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.expiry_date
     ), gate AS MATERIALIZED (
        -- ENH-133 D-3 clause 3, cut off at ts so there is no look-ahead.
        -- AS MATERIALIZED is load-bearing: see the header, 164 ms vs
        -- 26,424 ms on the two-construct precursor. Join is on
        -- (symbol, ts). This body measures 210.280 / 186.476 ms pre-apply,
        -- with `CTE Scan on gate g` at loops=1 in both plans.
        SELECT h.symbol, h.ts,
               (SELECT count(DISTINCT o2.spot) > 1
                  FROM option_chain_snapshots o2
                 WHERE o2.symbol = h.symbol
                   AND o2.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata')::date)
                                  ::timestamp) AT TIME ZONE 'Asia/Kolkata')
                   AND o2.ts <= h.ts) AS is_trading_session
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
     ), futwin AS (
        -- NO LOOK-AHEAD. 09:20 IST on the ts date through ts INCLUSIVE.
        SELECT DISTINCT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE, which is not always the option front.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry, T_f from THAT ROW's own ts. F and S are from
        -- the same row, so they are contemporaneous by construction.
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
        -- Fewer than 6 rows is UNMEASURABLE, never a substituted default
        -- (ADR-023 D1: fail to absent, never to stale).
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess
          FROM rrows
         GROUP BY symbol, ts
     ), legs AS (
        -- ENH-131's leg set, byte-for-byte in its predicates: oi above
        -- zero, vendor gamma non-zero, iv above zero, and the TD-NEW-2
        -- deep-ITM guard. The guard rejects spurious VENDOR gamma; it is
        -- kept so L3 and L7/L8 price the SAME legs and remain reconcilable.
        SELECT s.symbol, s.ts, s.expiry_date,
               h.spot, h.dte, h.t_years,
               r.r_sess, COALESCE(r.n_r_rows, 0) AS n_r_rows,
               s.strike::double precision       AS k,
               (CASE WHEN s.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                                                AS sgn,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h
            ON h.symbol = s.symbol AND h.ts = s.ts
           AND h.expiry_date = s.expiry_date
          LEFT JOIN rstats r ON r.symbol = s.symbol AND r.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), evalleg AS (
        -- Only legs that can carry a number reach the arithmetic. dte 0
        -- and a thin r window drop out here and are labelled in status.
        SELECT l.*
          FROM legs l
         WHERE l.dte > 0 AND l.t_years > 0
           AND l.n_r_rows >= 6 AND l.r_sess IS NOT NULL
     ), bs AS (
        SELECT e.*,
               ( ln(e.spot / e.k)
                 + (e.r_sess + 0.5 * power(e.sigma, 2)) * e.t_years )
               / (e.sigma * sqrt(e.t_years))                   AS d1
          FROM evalleg e
     ), bs2 AS (
        SELECT b.*,
               b.d1 - b.sigma * sqrt(b.t_years)                AS d2,
               exp(-0.5 * power(b.d1, 2)) / sqrt(2.0 * pi())   AS nd1,
               (b.r_sess + 0.5 * power(b.sigma, 2))
                 / (b.sigma * sqrt(b.t_years))
                 - b.d1 / (2.0 * b.t_years)                    AS dd1_dt
          FROM bs b
     ), bs3 AS (
        SELECT b.*,
               b.nd1 / (b.spot * b.sigma * sqrt(b.t_years))    AS bs_gamma
          FROM bs2 b
     ), perleg AS (
        -- The four constructs, scaled to their stated units. /100 is the
        -- per-IV-POINT step; /365 is the per-CALENDAR-DAY step; /1e7 is
        -- the Crore convention (TD-NEW-3). The delta pair carries one
        -- power of spot, the gamma pair two -- matching gex_cr.
        SELECT b.symbol, b.ts, b.expiry_date, b.dte, b.spot, b.k,
               b.sgn * ((-b.nd1 * b.d2 / b.sigma) / 100.0)
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_iv,
               b.sgn * ((-b.nd1 * b.dd1_dt) / 365.0)
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_time,
               b.sgn * ((b.bs_gamma * (b.d1 * b.d2 - 1.0) / b.sigma) / 100.0)
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_iv,
               b.sgn * ((b.bs_gamma * (b.d1 * b.dd1_dt
                                       + 1.0 / (2.0 * b.t_years))) / 365.0)
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_time
          FROM bs3 b
     ), agg AS (
        SELECT symbol, ts, expiry_date, dte, spot, k,
               count(*)::integer           AS n_legs,
               sum(leg_delta_drift_iv)     AS delta_drift_iv_cr_per_volpt,
               sum(leg_delta_drift_time)   AS delta_drift_time_cr_per_day,
               sum(leg_gex_drift_iv)       AS gex_drift_iv_cr_per_volpt,
               sum(leg_gex_drift_time)     AS gex_drift_time_cr_per_day,
               sum(abs(leg_delta_drift_iv))   AS gross_delta_drift_iv,
               sum(abs(leg_delta_drift_time)) AS gross_delta_drift_time,
               sum(abs(leg_gex_drift_iv))     AS gross_gex_drift_iv,
               sum(abs(leg_gex_drift_time))   AS gross_gex_drift_time
          FROM perleg
         GROUP BY symbol, ts, expiry_date, dte, spot, k
     )
SELECT
    h.symbol,
    h.ts,
    h.expiry_date,
    h.dte,
    h.spot,
    a.k                                          AS strike,
    g.is_trading_session,
    (h.t_years * 365.0)                          AS t_days,
    rr.r_sess,
    COALESCE(rr.n_r_rows, 0)                     AS n_r_rows,
    a.n_legs,
    a.delta_drift_iv_cr_per_volpt,
    a.delta_drift_time_cr_per_day,
    a.gex_drift_iv_cr_per_volpt,
    a.gex_drift_time_cr_per_day,
    a.gross_delta_drift_iv,
    a.gross_delta_drift_time,
    a.gross_gex_drift_iv,
    a.gross_gex_drift_time,
    -- Precedence is deliberate and matches ENH-131: an expiry-day cycle
    -- is skipped whatever else is true of it.
    CASE WHEN h.dte = 0                       THEN 'SKIPPED_EXPIRY'
         WHEN COALESCE(rr.n_r_rows, 0) < 6    THEN 'UNMEASURABLE_R'
         WHEN a.k IS NULL                     THEN 'NO_LEGS'
         ELSE 'OK'
    END                                          AS status
  FROM hdr h
  LEFT JOIN rstats rr ON rr.symbol = h.symbol AND rr.ts = h.ts
  LEFT JOIN gate   g  ON g.symbol  = h.symbol AND g.ts  = h.ts
  LEFT JOIN agg    a  ON a.symbol  = h.symbol AND a.ts  = h.ts
                     AND a.expiry_date = h.expiry_date
) f
), live AS (
SELECT * FROM public.v_gex_greeks_l2_strike
), j AS (
SELECT o.*, n.symbol AS n_symbol, n.spot AS n_spot, n.t_days AS n_t_days, n.r_sess AS n_r_sess, n.delta_drift_iv_cr_per_volpt AS n_delta_drift_iv_cr_per_volpt, n.delta_drift_time_cr_per_day AS n_delta_drift_time_cr_per_day, n.gex_drift_iv_cr_per_volpt AS n_gex_drift_iv_cr_per_volpt, n.gex_drift_time_cr_per_day AS n_gex_drift_time_cr_per_day, n.gross_delta_drift_iv AS n_gross_delta_drift_iv, n.gross_delta_drift_time AS n_gross_delta_drift_time, n.gross_gex_drift_iv AS n_gross_gex_drift_iv, n.gross_gex_drift_time AS n_gross_gex_drift_time, n.dte AS n_dte, n.is_trading_session AS n_is_trading_session, n.n_r_rows AS n_n_r_rows, n.n_legs AS n_n_legs, n.status AS n_status
  FROM s89 o
  FULL OUTER JOIN live n
    ON n.symbol = o.symbol AND n.ts = o.ts AND n.expiry_date = o.expiry_date
   AND n.strike IS NOT DISTINCT FROM o.strike
)
SELECT (SELECT count(*) FROM s89) AS n_s89, (SELECT count(*) FROM live) AS n_live,
       count(*) FILTER (WHERE symbol IS NULL OR n_symbol IS NULL) AS n_unmatched,
       count(*) FILTER (WHERE (dte) IS DISTINCT FROM (n_dte) OR (is_trading_session) IS DISTINCT FROM (n_is_trading_session) OR (n_r_rows) IS DISTINCT FROM (n_n_r_rows) OR (n_legs) IS DISTINCT FROM (n_n_legs) OR (status) IS DISTINCT FROM (n_status)) AS n_exact_mismatch,
       count(*) FILTER (WHERE ((spot) IS NULL) <> ((n_spot) IS NULL) OR ((t_days) IS NULL) <> ((n_t_days) IS NULL) OR ((r_sess) IS NULL) <> ((n_r_sess) IS NULL) OR ((delta_drift_iv_cr_per_volpt) IS NULL) <> ((n_delta_drift_iv_cr_per_volpt) IS NULL) OR ((delta_drift_time_cr_per_day) IS NULL) <> ((n_delta_drift_time_cr_per_day) IS NULL) OR ((gex_drift_iv_cr_per_volpt) IS NULL) <> ((n_gex_drift_iv_cr_per_volpt) IS NULL) OR ((gex_drift_time_cr_per_day) IS NULL) <> ((n_gex_drift_time_cr_per_day) IS NULL) OR ((gross_delta_drift_iv) IS NULL) <> ((n_gross_delta_drift_iv) IS NULL) OR ((gross_delta_drift_time) IS NULL) <> ((n_gross_delta_drift_time) IS NULL) OR ((gross_gex_drift_iv) IS NULL) <> ((n_gross_gex_drift_iv) IS NULL) OR ((gross_gex_drift_time) IS NULL) <> ((n_gross_gex_drift_time) IS NULL)) AS n_null_mismatch,
       greatest(max(abs((spot)::float8 - (n_spot)::float8)), max(abs((t_days)::float8 - (n_t_days)::float8)), max(abs((r_sess)::float8 - (n_r_sess)::float8)), max(abs((delta_drift_iv_cr_per_volpt)::float8 - (n_delta_drift_iv_cr_per_volpt)::float8)), max(abs((delta_drift_time_cr_per_day)::float8 - (n_delta_drift_time_cr_per_day)::float8)), max(abs((gex_drift_iv_cr_per_volpt)::float8 - (n_gex_drift_iv_cr_per_volpt)::float8)), max(abs((gex_drift_time_cr_per_day)::float8 - (n_gex_drift_time_cr_per_day)::float8)), max(abs((gross_delta_drift_iv)::float8 - (n_gross_delta_drift_iv)::float8)), max(abs((gross_delta_drift_time)::float8 - (n_gross_delta_drift_time)::float8)), max(abs((gross_gex_drift_iv)::float8 - (n_gross_gex_drift_iv)::float8)), max(abs((gross_gex_drift_time)::float8 - (n_gross_gex_drift_time)::float8))) AS max_abs_diff,
       count(*) FILTER (WHERE (spot) IS DISTINCT FROM (n_spot) OR (t_days) IS DISTINCT FROM (n_t_days) OR (r_sess) IS DISTINCT FROM (n_r_sess) OR (delta_drift_iv_cr_per_volpt) IS DISTINCT FROM (n_delta_drift_iv_cr_per_volpt) OR (delta_drift_time_cr_per_day) IS DISTINCT FROM (n_delta_drift_time_cr_per_day) OR (gex_drift_iv_cr_per_volpt) IS DISTINCT FROM (n_gex_drift_iv_cr_per_volpt) OR (gex_drift_time_cr_per_day) IS DISTINCT FROM (n_gex_drift_time_cr_per_day) OR (gross_delta_drift_iv) IS DISTINCT FROM (n_gross_delta_drift_iv) OR (gross_delta_drift_time) IS DISTINCT FROM (n_gross_delta_drift_time) OR (gross_gex_drift_iv) IS DISTINCT FROM (n_gross_gex_drift_iv) OR (gross_gex_drift_time) IS DISTINCT FROM (n_gross_gex_drift_time)) AS n_not_bitwise_equal,
       count(*) FILTER (WHERE status = 'OK') AS n_ok_rows
  FROM j;

-- C1  anon reads the strike and net views in ONE execution (S84). Fails if role_now is not anon or
--     a count is 0. PASS: role_now anon | n_strike = C5's n | n_net 4 (2 symbols x 2 legs).
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now,
       (SELECT count(*) FROM public.v_gex_greeks_l2_strike) AS n_strike,
       (SELECT count(*) FROM public.v_gex_greeks_l2_net)    AS n_net;
COMMIT;

-- C2  cost, as anon, TWICE, strike then net. Fails if Execution Time >= 3000 ms (MV-6) or the plan
--     shows the gate CTE scanned more than once. PASS: < 3000 ms on both runs, `CTE Scan on gate`
--     loops=1.
BEGIN;
SET LOCAL ROLE anon;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_greeks_l2_strike;
COMMIT;

BEGIN;
SET LOCAL ROLE anon;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_greeks_l2_net;
COMMIT;

-- C3  the base view's own grain and flags. Fails if a chain row is missing or duplicated, if a unit
--     column is non-NULL on a row that is not priceable and evaluable, or if in_leg_set is true where
--     priceable is false. PASS: dup 0 | bad_unit 0 | bad_flag 0 | n_legset = sum of the strike
--     view's n_legs per (symbol, expiry_date).
SELECT symbol, expiry_date, count(*) AS n_rows,
       count(*) - count(DISTINCT (strike, option_type)) AS dup,
       count(*) FILTER (WHERE u_delta_drift_iv IS NOT NULL AND NOT (priceable AND evaluable)) AS bad_unit,
       count(*) FILTER (WHERE in_leg_set AND NOT priceable) AS bad_flag,
       count(*) FILTER (WHERE in_leg_set AND evaluable) AS n_legset,
       (SELECT COALESCE(sum(s.n_legs), 0) FROM public.v_gex_greeks_l2_strike s
         WHERE s.symbol = l.symbol AND s.expiry_date = l.expiry_date) AS strike_n_legs,
       count(*) FILTER (WHERE priceable AND NOT in_leg_set) AS n_priced_not_in_book
  FROM public.v_gex_greeks_l2_leg l GROUP BY symbol, expiry_date ORDER BY 1, 2;
