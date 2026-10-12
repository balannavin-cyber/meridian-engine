-- =====================================================================
-- 2026-10-12_s96_v_delta_drift_flow_vs_book.sql
-- S96 / roadmap P7b (rulings S96-F, S96-G) -- d(delta)/d(sigma) and d(delta)/dt FLOW since the
-- pre-open row beside the L7/L8 BOOK, per front-expiry strike.
--   public.v_delta_drift_flow_vs_book   grain (symbol, expiry_date, strike)
-- =====================================================================
--
-- APPLIED 2026-10-12 ~06:08 IST (S96), Sections 1-3 in ONE execution from 2fa5bab via Notepad, on the
-- 2026-10-09 15:40 run. Pre-apply body cost through roq 309.2 / 274.7 ms, gate and hx at loops=1.
--   End-of-batch row: has_view t | comment_len 2698 | anon_r t | anon_write f | merdian_ro_r t |
--   authenticated_r f.
--   K1 (roq): 426 / 364 strike-sides, max side diff 1.4e-13, leg diffs <= 2.5e-12.
--   K2 (roq): leg book = v_gex_greeks_l2_net front-leg net to 3.6e-12 -- NIFTY iv +6,089.82 / t -9,796.95,
--      SENSEX +1,086.93 / -1,259.07 Cr: the board's own L7/L8 sensitivity-tile figures (read 04:40).
--   K3 (roq): 239 / 198 strikes, 0 mismatches, d_noanc 0, d_gap 0.
--   First flow (front leg, 10-09): NIFTY iv +1,761.07 / t -1,919.44; SENSEX +729.56 / -795.65 Cr.
--   K5 (anon): 239 / 198 rows, one ts / expiry / anchor each, SESSION, OK.
--   K6 (anon): 295.0 / 327.2 ms, gate and hx loops=1. Cost shape: the strike join to P5 plans as a
--      437 x 437 nested loop (190,532 rows removed by join filter, ~50 ms) -- the P7a `agree` shape;
--      cheap at this size, changes no result. NOT on the board (P7b board round owed).
-- The AUTHORED paragraph below is the record as written before the apply.
--
-- AUTHORED 2026-10-12 (S96). NOTHING IN THIS FILE HAS BEEN RUN AGAINST THE DATABASE.
-- Read-only view; S90-J class "anything else". Proposed register id ENH-144 (filed at doc-close).
-- Rulings S96-G: F1 the delta pair only; F2 the L7/L8 latest ts and OI, anchor from P5, join guard on
-- session date and front expiry, else no rows; F3 gaps as stated in the COMMENT; F4 flow / book /
-- pre-open per side and net, leg totals, status, flow_window; no badge, no untraded guard; F5 checks
-- K1-K5 below.
--
-- READS: v_gex_greeks_l2_leg (S96-F, applied 2026-10-12, C5 bit-for-bit), v_oi_since_preopen (ENH-142).
-- The base is read ONCE (`l AS MATERIALIZED`).
--
-- FIXTURE (S96, local Postgres 16, the p7b fixture of S96-F with Sections A and B applied;
-- docs/research/s96_priority/p7/p7b/): NIFTY 28 / SENSEX 25 rows, SESSION, OK.
--   K1 identity: 45 / 45 strike-sides, max side diff 2.9e-15, leg diffs <= 8.2e-13 (iv and t).
--   K2 clock / leg set: leg book = v_gex_greeks_l2_net front-leg net, d <= 4.5e-13 (NIFTY iv 25.8195,
--      SENSEX iv -3,469.011).
--   K3 independent dOI: 28 / 25 strikes, 0 mismatches, d_noanc 0, d_gap 0.
--   Branches, each in a rolled-back transaction: a PE side closed to zero OI is priced (removal flow
--   non-NULL, K1-K3 PASS); a CE side made unpriceable moves its dOI into the gap (SENSEX gap 19,280 ->
--   23,320, K1-K3 PASS); next-day pre-open rows -> rows with flow_window PRE_OPEN and dOI 0; the day's
--   pre-open rows deleted -> NO ROWS (join guard).
--   Mutants: P5 joined one strike off -> K3 25 / 24 mismatches; PE flow sign flipped -> K1 side diff
--   3.48 / 2.46; call gap term dropped (with the unpriceable CE plant) -> K3 d_gap -4,040.
--   NOT a mutant: book on `unit IS NOT NULL` instead of the leg set -- identical, because the two
--   differ only by oi > 0 and an oi-0 side contributes 0 either way; F5's list was wrong to name it.
--
-- APPLY: Sections 1 -> 3 in ONE execution; the batch ENDS with its own verification SELECT
-- (TD-S94-NEW-3). Then Section 4, one statement at a time. SECTIONS 2 AND 3 ARE LIVE STATEMENTS.
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_delta_drift_flow_vs_book
WITH (security_invoker = false) AS
WITH l AS MATERIALIZED (
        -- one read of the S96-F base: the L7/L8 latest ts, both legs, per chain row
        SELECT * FROM public.v_gex_greeks_l2_leg
     ), fr AS (
        -- the front leg at that ts
        SELECT symbol, ts, min(expiry_date) AS expiry_date
          FROM l
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), p AS (
        SELECT symbol, expiry_date, strike, anchor_ts,
               (anchor_ts AT TIME ZONE 'Asia/Kolkata')::date AS p_session_date,
               ce_oi_anchor_qty, pe_oi_anchor_qty
          FROM public.v_oi_since_preopen
     ), agree AS (
        -- JOIN GUARD: the base's session date and front expiry must equal P5's, else no rows
        SELECT DISTINCT f.symbol, f.ts, f.expiry_date, pp.anchor_ts
          FROM fr f
          JOIN p pp
            ON pp.symbol = f.symbol
           AND pp.expiry_date = f.expiry_date
           AND pp.p_session_date = (f.ts AT TIME ZONE 'Asia/Kolkata')::date
     ), k AS (
        -- pivot the front leg's chain rows to one row per strike (one CE and one PE row per strike)
        SELECT l.symbol, l.ts, l.expiry_date, g.anchor_ts, l.strike,
               max(l.spot) AS spot, max(l.dte) AS dte, max(l.n_r_rows) AS n_r_rows,
               max(l.oi_qty) FILTER (WHERE l.option_type = 'CE')               AS oi_call,
               max(l.oi_qty) FILTER (WHERE l.option_type = 'PE')               AS oi_put,
               max(l.oi)     FILTER (WHERE l.option_type = 'CE')               AS oi_call_d,
               max(l.oi)     FILTER (WHERE l.option_type = 'PE')               AS oi_put_d,
               bool_or(l.option_type = 'CE' AND l.in_leg_set AND l.evaluable)  AS call_in_book,
               bool_or(l.option_type = 'PE' AND l.in_leg_set AND l.evaluable)  AS put_in_book,
               max(l.u_delta_drift_iv)   FILTER (WHERE l.option_type = 'CE')   AS u_iv_call,
               max(l.u_delta_drift_iv)   FILTER (WHERE l.option_type = 'PE')   AS u_iv_put,
               max(l.u_delta_drift_time) FILTER (WHERE l.option_type = 'CE')   AS u_t_call,
               max(l.u_delta_drift_time) FILTER (WHERE l.option_type = 'PE')   AS u_t_put
          FROM l
          JOIN agree g ON g.symbol = l.symbol AND g.ts = l.ts AND g.expiry_date = l.expiry_date
         GROUP BY l.symbol, l.ts, l.expiry_date, g.anchor_ts, l.strike
     ), j AS (
        SELECT k.*, pp.ce_oi_anchor_qty, pp.pe_oi_anchor_qty,
               k.oi_call - pp.ce_oi_anchor_qty AS d_oi_call,
               k.oi_put  - pp.pe_oi_anchor_qty AS d_oi_put
          FROM k
          LEFT JOIN p pp
            ON pp.symbol = k.symbol AND pp.expiry_date = k.expiry_date AND pp.strike = k.strike
     ), f AS (
        -- sgn x unit x quantity x spot / 1e7, the L7/L8 expression (CE +1.0, PE -1.0). BOOK sums the
        -- leg set exactly as v_gex_greeks_l2_strike does; a side with OI that the leg set excludes is
        -- a gap (NULL), a side with no OI a true 0. FLOW and PRE-OPEN price on `priceable` (S96-F E2),
        -- i.e. wherever the unit column is not NULL; a non-zero dOI with no unit is a gap.
        SELECT j.*,
               CASE WHEN j.call_in_book THEN 1.0 * j.u_iv_call * j.oi_call_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_call, 0) = 0 THEN 0 END                     AS call_iv_book_cr,
               CASE WHEN j.put_in_book  THEN -1.0 * j.u_iv_put * j.oi_put_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_put, 0) = 0 THEN 0 END                      AS put_iv_book_cr,
               CASE WHEN j.call_in_book THEN 1.0 * j.u_t_call * j.oi_call_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_call, 0) = 0 THEN 0 END                     AS call_t_book_cr,
               CASE WHEN j.put_in_book  THEN -1.0 * j.u_t_put * j.oi_put_d * j.spot / 1e7
                    WHEN COALESCE(j.oi_put, 0) = 0 THEN 0 END                      AS put_t_book_cr,
               CASE WHEN j.d_oi_call IS NULL THEN NULL WHEN j.d_oi_call = 0 THEN 0
                    WHEN j.u_iv_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_iv_call * j.d_oi_call::double precision * j.spot / 1e7 END  AS call_iv_flow_cr,
               CASE WHEN j.d_oi_put IS NULL THEN NULL WHEN j.d_oi_put = 0 THEN 0
                    WHEN j.u_iv_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_iv_put * j.d_oi_put::double precision * j.spot / 1e7 END   AS put_iv_flow_cr,
               CASE WHEN j.d_oi_call IS NULL THEN NULL WHEN j.d_oi_call = 0 THEN 0
                    WHEN j.u_t_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_t_call * j.d_oi_call::double precision * j.spot / 1e7 END   AS call_t_flow_cr,
               CASE WHEN j.d_oi_put IS NULL THEN NULL WHEN j.d_oi_put = 0 THEN 0
                    WHEN j.u_t_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_t_put * j.d_oi_put::double precision * j.spot / 1e7 END    AS put_t_flow_cr,
               CASE WHEN j.ce_oi_anchor_qty IS NULL THEN NULL WHEN j.ce_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_iv_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_iv_call * j.ce_oi_anchor_qty::double precision * j.spot / 1e7 END AS call_iv_preopen_cr,
               CASE WHEN j.pe_oi_anchor_qty IS NULL THEN NULL WHEN j.pe_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_iv_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_iv_put * j.pe_oi_anchor_qty::double precision * j.spot / 1e7 END AS put_iv_preopen_cr,
               CASE WHEN j.ce_oi_anchor_qty IS NULL THEN NULL WHEN j.ce_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_t_call IS NULL THEN NULL
                    ELSE 1.0 * j.u_t_call * j.ce_oi_anchor_qty::double precision * j.spot / 1e7 END  AS call_t_preopen_cr,
               CASE WHEN j.pe_oi_anchor_qty IS NULL THEN NULL WHEN j.pe_oi_anchor_qty = 0 THEN 0
                    WHEN j.u_t_put IS NULL THEN NULL
                    ELSE -1.0 * j.u_t_put * j.pe_oi_anchor_qty::double precision * j.spot / 1e7 END  AS put_t_preopen_cr,
               CASE WHEN j.d_oi_call IS NOT NULL AND j.d_oi_call <> 0 AND j.u_iv_call IS NULL
                    THEN abs(j.d_oi_call) ELSE 0 END
             + CASE WHEN j.d_oi_put IS NOT NULL AND j.d_oi_put <> 0 AND j.u_iv_put IS NULL
                    THEN abs(j.d_oi_put) ELSE 0 END                                            AS gap_d_oi_qty,
               CASE WHEN j.d_oi_call IS NULL THEN COALESCE(j.oi_call, 0) ELSE 0 END
             + CASE WHEN j.d_oi_put  IS NULL THEN COALESCE(j.oi_put,  0) ELSE 0 END            AS no_anchor_oi_qty
          FROM j
     ), g2 AS (
        SELECT f.*,
               -- the book on sides with NO anchor OI: the one term outside pre-open + flow
               CASE WHEN f.ce_oi_anchor_qty IS NULL THEN COALESCE(f.call_iv_book_cr, 0) ELSE 0 END
             + CASE WHEN f.pe_oi_anchor_qty IS NULL THEN COALESCE(f.put_iv_book_cr,  0) ELSE 0 END AS iv_no_anchor_cr,
               CASE WHEN f.ce_oi_anchor_qty IS NULL THEN COALESCE(f.call_t_book_cr, 0) ELSE 0 END
             + CASE WHEN f.pe_oi_anchor_qty IS NULL THEN COALESCE(f.put_t_book_cr,  0) ELSE 0 END  AS t_no_anchor_cr
          FROM f
     )
SELECT g2.symbol,
       g2.expiry_date,
       g2.dte,
       g2.ts,
       g2.anchor_ts,
       CASE WHEN g2.ts < (((g2.ts AT TIME ZONE 'Asia/Kolkata')::date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
            THEN 'PRE_OPEN' ELSE 'SESSION' END                                      AS flow_window,
       CASE WHEN g2.dte = 0 THEN 'SKIPPED_EXPIRY'
            WHEN g2.n_r_rows < 6 THEN 'UNMEASURABLE_R'
            ELSE 'OK' END                                                          AS status,
       g2.spot,
       g2.strike,
       g2.oi_call, g2.oi_put, g2.ce_oi_anchor_qty, g2.pe_oi_anchor_qty, g2.d_oi_call, g2.d_oi_put,
       -- d(delta)/d(sigma), Rs crore of delta-notional per +1 IV point
       g2.call_iv_flow_cr, g2.put_iv_flow_cr,
       CASE WHEN g2.call_iv_flow_cr IS NULL OR g2.put_iv_flow_cr IS NULL THEN NULL
            ELSE g2.call_iv_flow_cr + g2.put_iv_flow_cr END                         AS net_iv_flow_cr,
       g2.call_iv_book_cr, g2.put_iv_book_cr,
       CASE WHEN g2.call_iv_book_cr IS NULL OR g2.put_iv_book_cr IS NULL THEN NULL
            ELSE g2.call_iv_book_cr + g2.put_iv_book_cr END                         AS net_iv_book_cr,
       g2.call_iv_preopen_cr, g2.put_iv_preopen_cr,
       CASE WHEN g2.call_iv_preopen_cr IS NULL OR g2.put_iv_preopen_cr IS NULL THEN NULL
            ELSE g2.call_iv_preopen_cr + g2.put_iv_preopen_cr END                   AS net_iv_preopen_cr,
       -- d(delta)/dt, Rs crore of delta-notional per calendar day
       g2.call_t_flow_cr, g2.put_t_flow_cr,
       CASE WHEN g2.call_t_flow_cr IS NULL OR g2.put_t_flow_cr IS NULL THEN NULL
            ELSE g2.call_t_flow_cr + g2.put_t_flow_cr END                           AS net_t_flow_cr,
       g2.call_t_book_cr, g2.put_t_book_cr,
       CASE WHEN g2.call_t_book_cr IS NULL OR g2.put_t_book_cr IS NULL THEN NULL
            ELSE g2.call_t_book_cr + g2.put_t_book_cr END                           AS net_t_book_cr,
       g2.call_t_preopen_cr, g2.put_t_preopen_cr,
       CASE WHEN g2.call_t_preopen_cr IS NULL OR g2.put_t_preopen_cr IS NULL THEN NULL
            ELSE g2.call_t_preopen_cr + g2.put_t_preopen_cr END                     AS net_t_preopen_cr,
       g2.gap_d_oi_qty,
       g2.no_anchor_oi_qty,
       -- LEG TOTALS: each side's MEASURED contribution (COALESCE 0), read with the gap and no-anchor
       -- quantities beside them or not at all (the ENH-140 rule).
       sum(COALESCE(g2.call_iv_flow_cr, 0) + COALESCE(g2.put_iv_flow_cr, 0)) OVER w        AS leg_iv_flow_cr,
       sum(abs(COALESCE(g2.call_iv_flow_cr, 0)) + abs(COALESCE(g2.put_iv_flow_cr, 0))) OVER w AS leg_iv_gross_flow_cr,
       sum(COALESCE(g2.call_iv_book_cr, 0) + COALESCE(g2.put_iv_book_cr, 0)) OVER w        AS leg_iv_book_cr,
       sum(COALESCE(g2.call_iv_preopen_cr, 0) + COALESCE(g2.put_iv_preopen_cr, 0)) OVER w  AS leg_iv_preopen_cr,
       sum(g2.iv_no_anchor_cr) OVER w                                                     AS leg_iv_no_anchor_cr,
       sum(COALESCE(g2.call_t_flow_cr, 0) + COALESCE(g2.put_t_flow_cr, 0)) OVER w          AS leg_t_flow_cr,
       sum(abs(COALESCE(g2.call_t_flow_cr, 0)) + abs(COALESCE(g2.put_t_flow_cr, 0))) OVER w AS leg_t_gross_flow_cr,
       sum(COALESCE(g2.call_t_book_cr, 0) + COALESCE(g2.put_t_book_cr, 0)) OVER w          AS leg_t_book_cr,
       sum(COALESCE(g2.call_t_preopen_cr, 0) + COALESCE(g2.put_t_preopen_cr, 0)) OVER w    AS leg_t_preopen_cr,
       sum(g2.t_no_anchor_cr) OVER w                                                      AS leg_t_no_anchor_cr,
       sum(abs(COALESCE(g2.d_oi_call, 0)) + abs(COALESCE(g2.d_oi_put, 0))) OVER w          AS leg_abs_d_oi_qty,
       sum(g2.gap_d_oi_qty) OVER w                                                        AS leg_gap_d_oi_qty,
       sum(g2.no_anchor_oi_qty) OVER w                                                    AS leg_no_anchor_oi_qty
  FROM g2
WINDOW w AS (PARTITION BY g2.symbol, g2.expiry_date);


-- =====================================================================
-- SECTION 2 of 4 -- COMMENT (LIVE statement -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_delta_drift_flow_vs_book IS
  'S96 / roadmap P7b / rulings S96-F, S96-G -- d(delta)/d(sigma) and d(delta)/dt FLOW since the pre-open row beside the BOOK of ENH-98 L7/L8, per FRONT-expiry strike, in Rs crore of delta-notional (per +1 IV point; per calendar day). NOT a parity layer; display-only (S37); routes nothing; makes NO PREDICTIVE CLAIM. NO BADGE COLUMN. Grain (symbol, expiry_date, strike); consumers MUST ORDER BY symbol, strike. ONE IMPLEMENTATION OF THE GREEKS: every value is sgn x unit x quantity x spot / 1e7 with the unit read from v_gex_greeks_l2_leg (the S89 Black-Scholes chain, gate C5 bit-for-bit) and sgn the L7/L8 dealer assumption (CE +1, PE -1). book uses oi at the L7/L8 latest ts over the L7/L8 leg set, so leg book equals v_gex_greeks_l2_net front-leg net; flow uses dOI = oi(latest) - oi(anchor); pre-open uses the anchor OI valued at TODAY''S greeks (not the book at 08:30), so book = pre-open + flow exactly, the change being open interest only, never repricing; leg_*_no_anchor_cr is the book on sides with no anchor OI, the one term outside that split. CLOCK: the L7/L8 latest chain ts and its OI; the anchor (anchor_ts, anchor OI) from v_oi_since_preopen (ENH-142, S95-B). JOIN GUARD: rows appear only when the base ts IST date equals the P5 session date and the front expiry equals P5''s; otherwise NO ROWS, never a fallback. After 15:15 this view sits on the latest run (to 15:40) while v_dex_flow_vs_book holds at the settled run -- the D5 split, recorded, not fixed. flow_window PRE_OPEN before 09:15 IST, where a non-zero dOI is a vendor revision, not flow; consumers draw flow only in SESSION. NULL IS A GAP, NEVER A ZERO: a leg is priced wherever the base''s unit is not NULL (priceable and evaluable; a leg closed to zero OI is priced, S96-F E2); a non-zero dOI on an unpriced side publishes NULL flow and its |dOI| in gap_d_oi_qty; a side with no anchor publishes NULL dOI and its OI in no_anchor_oi_qty; a book side with OI outside the leg set is NULL; nets are NULL when either side is. dte 0 is SKIPPED in L7/L8 (status SKIPPED_EXPIRY), so on the front leg''s expiry day every non-zero dOI is a gap. Strikes absent from the latest run are not drawn (as in v_dex_flow_vs_book). LEG TOTALS are window sums of each side''s MEASURED contribution, read with leg_gap_d_oi_qty and leg_no_anchor_oi_qty or not at all. AN OI CHANGE CANNOT DISTINGUISH WRITING FROM BUYING; NO DEALER CLAIM (P2: dealer side regime-dependent). Flow is unclassified (D-4 not built) and valued at the latest greeks, not at the greeks when each contract was added. Runs with the owner privileges (security_invoker = false); adding a column here publishes it to anon. Never label second-order terms vanna or charm (L78-1).';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- CASE-2026-09-22, ADR-031 D6)
-- =====================================================================

REVOKE ALL ON public.v_delta_drift_flow_vs_book FROM anon, authenticated;
GRANT SELECT ON public.v_delta_drift_flow_vs_book TO anon, merdian_ro;

-- end-of-batch verification (TD-S94-NEW-3) -- must return ONE row:
--   has_view t | comment_len 2698 (computed from the literal in this file, '' unescaped) |
--   anon_r t | anon_write f | merdian_ro_r t | authenticated_r f
SELECT to_regclass('public.v_delta_drift_flow_vs_book') IS NOT NULL                        AS has_view,
       length(obj_description('public.v_delta_drift_flow_vs_book'::regclass, 'pg_class'))   AS comment_len,
       has_table_privilege('anon', 'public.v_delta_drift_flow_vs_book', 'SELECT')           AS anon_r,
       (has_table_privilege('anon', 'public.v_delta_drift_flow_vs_book', 'INSERT')
        OR has_table_privilege('anon', 'public.v_delta_drift_flow_vs_book', 'UPDATE')
        OR has_table_privilege('anon', 'public.v_delta_drift_flow_vs_book', 'DELETE'))      AS anon_write,
       has_table_privilege('merdian_ro', 'public.v_delta_drift_flow_vs_book', 'SELECT')     AS merdian_ro_r,
       has_table_privilege('authenticated', 'public.v_delta_drift_flow_vs_book', 'SELECT')  AS authenticated_r;


-- =====================================================================
-- SECTION 4 of 4 -- checks. ONE STATEMENT PER RUN. Each states what fails it.
-- K1-K3 also run through bin/roq.sh (merdian_ro). K4 (join guard) is fixture-only (above).
-- =====================================================================

-- K1  IDENTITY book = pre-open + flow, per strike-side (where all three are non-NULL) and per leg
--     (with the no-anchor term). Fails if pre-open, flow or book use a different clock, unit, sign,
--     leg set or anchor. PASS per symbol: n_sides > 0 | max_side_diff <= 1e-9 | leg_iv_diff, leg_t_diff <= 1e-9.
SELECT symbol,
       count(*) FILTER (WHERE call_iv_book_cr IS NOT NULL AND call_iv_preopen_cr IS NOT NULL AND call_iv_flow_cr IS NOT NULL)
     + count(*) FILTER (WHERE put_iv_book_cr  IS NOT NULL AND put_iv_preopen_cr  IS NOT NULL AND put_iv_flow_cr  IS NOT NULL) AS n_sides,
       greatest(max(abs(call_iv_book_cr - call_iv_preopen_cr - call_iv_flow_cr)),
                max(abs(put_iv_book_cr  - put_iv_preopen_cr  - put_iv_flow_cr)),
                max(abs(call_t_book_cr  - call_t_preopen_cr  - call_t_flow_cr)),
                max(abs(put_t_book_cr   - put_t_preopen_cr   - put_t_flow_cr)))                AS max_side_diff,
       max(abs(leg_iv_book_cr - leg_iv_preopen_cr - leg_iv_flow_cr - leg_iv_no_anchor_cr))     AS leg_iv_diff,
       max(abs(leg_t_book_cr  - leg_t_preopen_cr  - leg_t_flow_cr  - leg_t_no_anchor_cr))      AS leg_t_diff,
       max(leg_iv_flow_cr) AS leg_iv_flow, max(leg_t_flow_cr) AS leg_t_flow
  FROM public.v_delta_drift_flow_vs_book GROUP BY symbol ORDER BY 1;

-- K2  CLOCK AND LEG SET: this view's leg book equals v_gex_greeks_l2_net's net for the same symbol,
--     ts and expiry, both constructs, read in ONE statement. Fails if the view sits on another ts,
--     another expiry, or sums a different leg set (e.g. priceable instead of in_leg_set).
--     PASS per symbol: matched t | d_iv <= 1e-9 | d_t <= 1e-9.
WITH v AS (SELECT DISTINCT symbol, ts, expiry_date, leg_iv_book_cr, leg_t_book_cr FROM public.v_delta_drift_flow_vs_book)
SELECT v.symbol, n.symbol IS NOT NULL AS matched,
       abs(v.leg_iv_book_cr - COALESCE(n.net_delta_drift_iv_cr_per_volpt, 0)) AS d_iv,
       abs(v.leg_t_book_cr  - COALESCE(n.net_delta_drift_time_cr_per_day, 0)) AS d_t,
       v.leg_iv_book_cr, n.net_delta_drift_iv_cr_per_volpt, v.leg_t_book_cr, n.net_delta_drift_time_cr_per_day
  FROM v LEFT JOIN public.v_gex_greeks_l2_net n
    ON n.symbol = v.symbol AND n.ts = v.ts AND n.expiry_date = v.expiry_date
 ORDER BY 1;

-- K3  INDEPENDENT dOI from option_chain_snapshots at the view's anchor_ts and ts (no P5): per strike
--     and side. Fails on a wrong-strike or wrong-side join, or an anchor read off another clock.
--     Also the gap quantity, recomputed from the base view's unit columns: d_gap fails if a non-zero dOI
--     on an unpriced side is dropped or counted twice.
--     PASS per symbol: n_strikes = the view's row count | mismatches 0 | d_noanc 0 | d_gap 0.
WITH v AS (SELECT * FROM public.v_delta_drift_flow_vs_book),
     a AS (SELECT o.symbol, o.strike,
                  max(o.oi) FILTER (WHERE o.option_type = 'CE') AS a_c,
                  max(o.oi) FILTER (WHERE o.option_type = 'PE') AS a_p
             FROM (SELECT DISTINCT symbol, expiry_date, anchor_ts FROM v) x
             JOIN public.option_chain_snapshots o
               ON o.symbol = x.symbol AND o.expiry_date = x.expiry_date AND o.ts = x.anchor_ts
            GROUP BY o.symbol, o.strike),
     s AS (SELECT o.symbol, o.strike,
                  max(o.oi) FILTER (WHERE o.option_type = 'CE') AS s_c,
                  max(o.oi) FILTER (WHERE o.option_type = 'PE') AS s_p
             FROM (SELECT DISTINCT symbol, expiry_date, ts FROM v) x
             JOIN public.option_chain_snapshots o
               ON o.symbol = x.symbol AND o.expiry_date = x.expiry_date AND o.ts = x.ts
            GROUP BY o.symbol, o.strike),
     u AS (SELECT b.symbol, b.strike,
                  bool_or(b.option_type = 'CE' AND b.u_delta_drift_iv IS NULL) AS nu_c,
                  bool_or(b.option_type = 'PE' AND b.u_delta_drift_iv IS NULL) AS nu_p
             FROM public.v_gex_greeks_l2_leg b
             JOIN (SELECT DISTINCT symbol, expiry_date, ts FROM v) x
               ON x.symbol = b.symbol AND x.expiry_date = b.expiry_date AND x.ts = b.ts
            GROUP BY b.symbol, b.strike)
SELECT v.symbol, count(*) AS n_strikes,
       count(*) FILTER (WHERE v.d_oi_call IS DISTINCT FROM s.s_c - a.a_c
                           OR v.d_oi_put  IS DISTINCT FROM s.s_p - a.a_p) AS mismatches,
       max(v.leg_no_anchor_oi_qty) - sum(CASE WHEN s.s_c - a.a_c IS NULL THEN COALESCE(s.s_c, 0) ELSE 0 END
                                       + CASE WHEN s.s_p - a.a_p IS NULL THEN COALESCE(s.s_p, 0) ELSE 0 END) AS d_noanc,
       max(v.leg_gap_d_oi_qty) - sum(CASE WHEN u.nu_c AND s.s_c - a.a_c <> 0 THEN abs(s.s_c - a.a_c) ELSE 0 END
                                   + CASE WHEN u.nu_p AND s.s_p - a.a_p <> 0 THEN abs(s.s_p - a.a_p) ELSE 0 END) AS d_gap
  FROM v
  LEFT JOIN s ON s.symbol = v.symbol AND s.strike = v.strike
  LEFT JOIN a ON a.symbol = v.symbol AND a.strike = v.strike
  LEFT JOIN u ON u.symbol = v.symbol AND u.strike = v.strike
 GROUP BY v.symbol ORDER BY 1;

-- K5  anon reads it, in ONE execution (S84). Fails if role_now is not anon or the count is 0 while the
--     symbols agree. PASS: role_now anon | n per symbol > 0 | one ts, one expiry, one anchor per symbol.
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now, symbol, count(*) AS n, count(DISTINCT ts) AS n_ts,
       count(DISTINCT expiry_date) AS n_exp, count(DISTINCT anchor_ts) AS n_anchor,
       min(flow_window) AS fw, min(status) AS status
  FROM public.v_delta_drift_flow_vs_book GROUP BY symbol ORDER BY symbol;
COMMIT;

-- K6  cost, as anon, TWICE. Fails if Execution Time >= 3000 ms (MV-6) or `CTE Scan on gate` /
--     `CTE Scan on hx` show loops > 1. PASS: < 3000 ms on both runs, loops=1.
BEGIN;
SET LOCAL ROLE anon;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_delta_drift_flow_vs_book;
COMMIT;
