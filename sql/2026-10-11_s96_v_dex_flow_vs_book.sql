-- =====================================================================
-- 2026-10-11_s96_v_dex_flow_vs_book.sql
-- S96 / roadmap P7a (ruling S96-A) -- DEX FLOW since the pre-open row,
-- beside the DEX standing BOOK, per front-expiry strike.
--   public.v_dex_flow_vs_book   grain (symbol, expiry_date, strike)
-- =====================================================================
--
-- AUTHORED 2026-10-11 (S96). NOTHING IN THIS FILE HAS BEEN RUN AGAINST THE
-- DATABASE. Read-only view; S90-J class "anything else" -- deploys any time.
-- Design: docs/research/s96_priority/p7/P7_flow_vs_book_design_note_2026-10-11.md
-- (sections 1-3, 6a). M-P7 (result 7faa9fb) scored the SAME / OPPOSITE badge
-- BUILD with a condition (untraded-leg guard, TD-S95-NEW-1 c): THIS VIEW
-- CARRIES NO BADGE COLUMN. It publishes the flow numbers only.
-- NOT A PARITY LAYER (ADR-025 closed); display-only (S37); routes nothing.
--
-- WHAT IT IS -- two live views joined, no rule re-implemented:
--   v_dex_standing_book (ENH-140)  session, front leg (leg_n = 1), settled run,
--                                  OI / delta / spot at it, gap rule, the book
--   v_oi_since_preopen  (ENH-142)  the anchor (S95-B): anchor_ts and anchor OI
--   flow  = delta(settled) x (oi(settled) - oi(anchor)) x spot / 1e7
--   ONE CLOCK: everything is valued at the book's SETTLED run. P5's
--   oi_latest / *_oi_delta_qty are NOT used: after 15:15 P5's latest moves to
--   15:40 while the book holds at the last run <= 15:15 (design note section 2).
--   IDENTITY, exact by construction where both sides are measured:
--   book - flow = delta x oi(anchor) x spot / 1e7 (check 4c).
--
-- JOIN GUARD (design note 2, check 4b): the view returns rows for a symbol
-- only when the book's session date and front expiry equal P5's (P5 session =
-- IST date of anchor_ts). Otherwise NO ROWS for that symbol -- absence, never
-- a fallback (ADR-023 D1). Cases that hit it, by design: 08:30-09:15 on a
-- trading day (P5 already on today's pre-open, the book still on yesterday
-- because today's tape has not moved), and a frozen closed day that wrote
-- chain rows (P5 anchors on it, the book steps back past it).
--
-- GAP RULE (ENH-140, verbatim in effect). A side whose delta is a gap
-- publishes NULL flow and its |dOI| rides in d_oi_*_no_delta. Where oi(settled)
-- > 0 the gap is read from the book itself: call_dex_cr IS NULL. Where
-- oi(settled) = 0 the book publishes a true 0 and no gap flag, so the gap is
-- read from the published delta: delta IS NULL OR delta = 0. ENH-140's marker
-- is delta IS NULL OR (delta = 0 AND COALESCE(iv,0) = 0); the two differ only
-- on a zero delta beside a live iv, which ENH-140 measured at ZERO rows over a
-- full session (55,228 positive-OI rows). Check 4d recomputes from the chain
-- with the iv form and fails on any difference, so this is tested, not assumed.
--
-- A strike with no anchor OI on a side (P5 LATEST_ONLY, or absent from P5)
-- has NULL dOI and NULL flow on that side -- never 0; its settled OI rides in
-- leg_no_anchor_oi_qty.
--
-- flow_window: PRE_OPEN when the settled run is stamped before 09:15 IST (a
-- non-zero flow is then a vendor OI revision before any trade, not flow);
-- SESSION otherwise. Consumers draw flow only in SESSION (design note 5.1).
--
-- S96-C APPLIED 2026-10-11 ~19:52 IST, Sections 1-3 in ONE execution from a728052 via Notepad.
-- End-of-batch row: has_view t | comment_len 3959 | anon_r t | anon_write f | merdian_ro_r t |
-- authenticated_r f. Pre-apply cost through roq 253.7 / 261.1 ms, no Seq Scan. 4f on the
-- 2026-10-09 settled session: n 453 NIFTY / 387 SENSEX strike-sides, strike diff 0, leg diff 0;
-- leg pre-open net NIFTY +79,275.2739515727 / SENSEX +5,323.5008406174 Cr, equal to the values
-- computed beforehand from the afternoon's book and flow (no-anchor 0); leg flow unchanged to
-- every digit. 4e anon 252.0 / 253.4 ms.
--
-- S96-C AMENDMENT (authored 2026-10-11 ~19:50 IST, NOT YET APPLIED when written): appends
-- seven pre-open columns (per strike call/put/net_preopen_dex_cr; leg totals; leg_no_anchor_dex_cr)
-- so a board drawing held / added / removed since the pre-open reads the remembered value from
-- the database (ruling S96-C). Columns are APPENDED, so CREATE OR REPLACE keeps the existing ones;
-- COMMENT and GRANTs are re-run in the same batch. New check 4f. Fixture (S96): applied over
-- the first version as CREATE OR REPLACE, comment_len 3959, 4a-4d unchanged, 4f n 44 per symbol,
-- strike diff 0, leg diff 0 with the no-anchor term exercised (fixture strike absent at the
-- anchor, +4.68 Cr NIFTY); mutants: pre-open valued on settled OI -> 4f strike diff 61.6;
-- no-anchor term dropped -> 4f leg diff 4.68 / 25.51. Everything above this paragraph
-- describes the first apply and is left as written.
--
-- APPLIED 2026-10-11 ~19:00 IST (S96), Sections 1-3 in ONE execution from the committed
-- file (36af1e9), copied via Notepad, not the terminal. End-of-batch row: has_view t |
-- comment_len 3284 | anon_r t | anon_write f | merdian_ro_r t | authenticated_r f.
-- Section 4 PASSED on the 2026-10-09 settled session (15:10:07): 4a anon NIFTY 239 / SENSEX 198
-- rows, one session / expiry / settled run, SESSION; 4b agrees t, n_view = n_book (239, 198);
-- 4c max diff 0 on 78 / 88 / 93 / 113 strike-sides; 4d d_call = d_put = 0, d_gap = 0,
-- d_noanc = 0 (NIFTY call -31,440.47 / put -56,124.13 Cr; SENSEX +6,478.92 / -15,002.91);
-- 4e anon 252.1 / 255.1 ms. Third implementation: the M-P7 extract's 2026-10-09 15:10:07 row
-- (~/mp7_out, SHA256SUMS 32a091fd) gives the identical flow to every printed digit.
-- Pre-apply real-volume cost through roq (merdian_ro): 279.1 / 257.7 ms, no Seq Scan.
-- Cost shape (4e plan): ~95 ms is ENH-140's legs CTE, ~6 ms ENH-142; the agree CTE is a
-- 437 x 437 nested loop (~65 ms) -- cheap at this size; collapsing each side to one row per
-- symbol first would remove it without changing any result. Proposed register id ENH-143
-- (next free after ENH-142; filed at doc-close). NOT on the board. The AUTHORED paragraph
-- above is the record as written before the apply and is left as it was.
--
-- FIXTURE TEST (S96, local Postgres 16.15, synthetic data, the committed ENH-140 and
-- ENH-142 bodies; docs/research/s96_priority/p7/p7a/): Sections 1-3 then 4a-4e all PASS
-- (comment_len 3284; 4c max diff 0; 4d d_call/d_put 0, d_gap 0, d_noanc 0; 19.5 ms), and
-- the leg flow equals the M-P7 extract's 15:15 row exactly (SENSEX 631.7563954062240 /
-- -584.5299156260190). Mutants: A dOI joined one strike off -> 4d fails (4c passes, see
-- 4c); B PE sign flipped -> 4c and 4d fail; C zero-OI gap branch dropped -> 4d d_gap
-- -260000. Join guard: next-day pre-open rows inserted -> 4b agrees f, n_view 0 both
-- symbols. Real-volume cost is measured through roq BEFORE apply (not yet done).
--
-- APPLY: Sections 1 -> 3 in ONE execution; the batch ENDS with its own
-- verification SELECT (TD-S94-NEW-3). Then Section 4, one statement at a time.
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS (TD-S81-NEW-5).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_dex_flow_vs_book
WITH (security_invoker = false) AS
WITH b AS (
        SELECT * FROM public.v_dex_standing_book WHERE leg_n = 1
     ), p AS (
        SELECT symbol, expiry_date, strike, anchor_ts,
               (anchor_ts AT TIME ZONE 'Asia/Kolkata')::date AS p_session_date,
               ce_oi_anchor_qty, pe_oi_anchor_qty
          FROM public.v_oi_since_preopen
     ), agree AS (
        -- one row per symbol whose book session + front expiry equal P5's
        SELECT DISTINCT bb.symbol, pp.anchor_ts
          FROM b bb
          JOIN p pp
            ON pp.symbol = bb.symbol
           AND pp.expiry_date = bb.expiry_date
           AND pp.p_session_date = bb.session_date
     ), j AS (
        SELECT bb.*,
               g.anchor_ts,
               pp.ce_oi_anchor_qty,
               pp.pe_oi_anchor_qty,
               CASE WHEN COALESCE(bb.oi_call, 0) > 0 THEN bb.call_dex_cr IS NULL
                    ELSE (bb.delta_call IS NULL OR bb.delta_call = 0) END AS call_gap,
               CASE WHEN COALESCE(bb.oi_put, 0) > 0 THEN bb.put_dex_cr IS NULL
                    ELSE (bb.delta_put IS NULL OR bb.delta_put = 0) END AS put_gap,
               bb.oi_call - pp.ce_oi_anchor_qty AS d_oi_call,
               bb.oi_put  - pp.pe_oi_anchor_qty AS d_oi_put
          FROM b bb
          JOIN agree g ON g.symbol = bb.symbol
          LEFT JOIN p pp
            ON pp.symbol = bb.symbol
           AND pp.expiry_date = bb.expiry_date
           AND pp.strike = bb.strike
     ), f AS (
        SELECT j.*,
               CASE WHEN d_oi_call IS NULL THEN NULL
                    WHEN d_oi_call = 0     THEN 0
                    WHEN call_gap          THEN NULL
                    ELSE delta_call * d_oi_call * spot / 1e7 END AS call_flow_cr,
               CASE WHEN d_oi_put IS NULL THEN NULL
                    WHEN d_oi_put = 0     THEN 0
                    WHEN put_gap          THEN NULL
                    ELSE delta_put * d_oi_put * spot / 1e7 END   AS put_flow_cr,
               CASE WHEN d_oi_call IS NOT NULL AND d_oi_call <> 0 AND call_gap
                    THEN abs(d_oi_call) ELSE 0 END               AS d_oi_call_no_delta,
               CASE WHEN d_oi_put IS NOT NULL AND d_oi_put <> 0 AND put_gap
                    THEN abs(d_oi_put) ELSE 0 END                AS d_oi_put_no_delta,
               CASE WHEN d_oi_call IS NULL THEN COALESCE(oi_call, 0) ELSE 0 END
             + CASE WHEN d_oi_put  IS NULL THEN COALESCE(oi_put,  0) ELSE 0 END AS no_anchor_oi_qty,
               -- S96-C: the pre-open OI valued at the SETTLED delta (not the 08:30 book).
               CASE WHEN ce_oi_anchor_qty IS NULL THEN NULL
                    WHEN ce_oi_anchor_qty = 0     THEN 0
                    WHEN call_gap                 THEN NULL
                    ELSE delta_call * ce_oi_anchor_qty * spot / 1e7 END AS call_preopen_dex_cr,
               CASE WHEN pe_oi_anchor_qty IS NULL THEN NULL
                    WHEN pe_oi_anchor_qty = 0     THEN 0
                    WHEN put_gap                  THEN NULL
                    ELSE delta_put * pe_oi_anchor_qty * spot / 1e7 END  AS put_preopen_dex_cr,
               -- book OI on a side with NO anchor OI, valued as the book values it: the one
               -- term outside preopen + flow, so the leg identity can be stated exactly.
               CASE WHEN ce_oi_anchor_qty IS NULL AND COALESCE(oi_call, 0) > 0 AND NOT call_gap
                    THEN delta_call * oi_call * spot / 1e7 ELSE 0 END
             + CASE WHEN pe_oi_anchor_qty IS NULL AND COALESCE(oi_put, 0) > 0 AND NOT put_gap
                    THEN delta_put * oi_put * spot / 1e7 ELSE 0 END    AS no_anchor_dex_cr
          FROM j
     )
SELECT f.symbol,
       f.session_date,
       f.expiry_date,
       f.dte,
       f.anchor_ts,
       f.settled_ts,
       CASE WHEN f.settled_ts < ((f.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
            THEN 'PRE_OPEN' ELSE 'SESSION' END                            AS flow_window,
       f.spot,
       f.strike,
       f.delta_call,
       f.delta_put,
       f.oi_call,
       f.oi_put,
       f.ce_oi_anchor_qty,
       f.pe_oi_anchor_qty,
       f.d_oi_call,
       f.d_oi_put,
       f.call_flow_cr,
       f.put_flow_cr,
       -- NULL when either side is unknown: an unknown cannot be netted (ENH-140).
       CASE WHEN f.call_flow_cr IS NULL OR f.put_flow_cr IS NULL THEN NULL
            ELSE f.call_flow_cr + f.put_flow_cr END                       AS net_flow_cr,
       f.d_oi_call_no_delta,
       f.d_oi_put_no_delta,
       f.call_dex_cr,
       f.put_dex_cr,
       f.net_dex_cr,
       -- Leg totals: each side's MEASURED contribution (COALESCE 0), with what
       -- they do not cover beside them -- the ENH-140 rule. Read together or not at all.
       sum(COALESCE(f.call_flow_cr, 0)) OVER wleg                          AS leg_call_flow_cr,
       sum(COALESCE(f.put_flow_cr , 0)) OVER wleg                          AS leg_put_flow_cr,
       sum(COALESCE(f.call_flow_cr, 0) + COALESCE(f.put_flow_cr, 0)) OVER wleg AS leg_net_flow_cr,
       sum(abs(COALESCE(f.call_flow_cr, 0)) + abs(COALESCE(f.put_flow_cr, 0))) OVER wleg AS leg_gross_flow_cr,
       sum(abs(COALESCE(f.d_oi_call, 0)) + abs(COALESCE(f.d_oi_put, 0))) OVER wleg AS leg_abs_d_oi_qty,
       sum(f.d_oi_call_no_delta + f.d_oi_put_no_delta) OVER wleg           AS leg_gap_d_oi_qty,
       sum(f.no_anchor_oi_qty) OVER wleg                                   AS leg_no_anchor_oi_qty,
       f.leg_call_dex_cr,
       f.leg_put_dex_cr,
       f.leg_net_dex_cr,
       f.leg_oi_qty,
       f.leg_gap_oi_qty,
       -- S96-C (appended, so CREATE OR REPLACE keeps the existing columns in place)
       f.call_preopen_dex_cr,
       f.put_preopen_dex_cr,
       CASE WHEN f.call_preopen_dex_cr IS NULL OR f.put_preopen_dex_cr IS NULL THEN NULL
            ELSE f.call_preopen_dex_cr + f.put_preopen_dex_cr END             AS net_preopen_dex_cr,
       sum(COALESCE(f.call_preopen_dex_cr, 0)) OVER wleg                       AS leg_call_preopen_dex_cr,
       sum(COALESCE(f.put_preopen_dex_cr , 0)) OVER wleg                       AS leg_put_preopen_dex_cr,
       sum(COALESCE(f.call_preopen_dex_cr, 0) + COALESCE(f.put_preopen_dex_cr, 0)) OVER wleg AS leg_net_preopen_dex_cr,
       sum(f.no_anchor_dex_cr) OVER wleg                                       AS leg_no_anchor_dex_cr
  FROM f
WINDOW wleg AS (PARTITION BY f.symbol, f.expiry_date);


-- =====================================================================
-- SECTION 2 of 4 -- COMMENT (LIVE statement -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_dex_flow_vs_book IS
  'S96 / roadmap P7a / ruling S96-A -- DEX FLOW since the pre-open row beside the DEX standing BOOK, per front-expiry strike, in Rs crore. NOT a parity layer; display-only (S37); routes nothing; makes NO PREDICTIVE CLAIM. Grain (symbol, expiry_date, strike), front leg only; consumers MUST ORDER BY symbol, strike. NO BADGE COLUMN: M-P7 (docs/research/s96_priority/p7/MP7_flow_badge_result_2026-10-11.md) scored a SAME/OPPOSITE badge BUILD on condition of an untraded-leg guard (TD-S95-NEW-1 c), not yet ruled, so only the numbers are published. JOINS TWO LIVE VIEWS AND RE-IMPLEMENTS NO RULE: v_dex_standing_book (ENH-140) gives the session, the front leg, the settled run (last run at or before 15:15 IST), OI, vendor delta and spot at it, the gap rule and the book; v_oi_since_preopen (ENH-142, S95-B) gives the anchor, the session first front-expiry row stamped before 09:15 IST, and the anchor OI. flow = delta(settled) x (oi(settled) - oi(anchor)) x spot / 1e7, no PE flip (delta carries its sign), oi a quantity with the lot inside it. ONE CLOCK: everything is valued at the book settled run; P5 own latest snapshot and delta columns are not used, because after 15:15 P5 latest moves to 15:40 while the book holds. book minus flow equals delta x oi(anchor) x spot / 1e7 wherever both sides are measured. JOIN GUARD: rows appear for a symbol only when the book session date and front expiry equal P5 (P5 session = IST date of anchor_ts); otherwise NO ROWS for that symbol, never a fallback (ADR-023 D1) -- expected from the pre-open rows (~08:30) until the tape moves after 09:15, and on a frozen closed day that wrote chain rows. NULL IS A GAP, NEVER A ZERO: a side whose delta is a gap publishes NULL flow and its |dOI| in d_oi_call_no_delta / d_oi_put_no_delta; a side with no anchor OI has NULL dOI and NULL flow, its settled OI in leg_no_anchor_oi_qty; net_flow_cr is NULL when either side is NULL. Gap detection: where settled OI is above 0, the book own NULL call_dex_cr / put_dex_cr; where it is 0, delta IS NULL OR delta = 0 (ENH-140 marker differs only on a zero delta beside a live iv, measured at zero rows; Section 4d recomputes with the iv form). LEG TOTALS are window sums of each side MEASURED contribution, read with leg_gap_d_oi_qty and leg_no_anchor_oi_qty or not at all; the book leg totals ride beside them unchanged. flow_window is PRE_OPEN when the settled run is stamped before 09:15 IST -- a non-zero flow then is a vendor OI revision before any trade -- and SESSION otherwise; consumers draw flow only in SESSION. AN OI DELTA CANNOT DISTINGUISH WRITING FROM BUYING; NO DEALER CLAIM (P2: dealer side regime-dependent). Flow is unclassified (no long/short build-up, covering or unwinding) and is valued at the settled run delta, not at the delta when each contract was added. FLOW NET IS ITSELF A PARTIAL CANCELLATION: M-P7 measured flow |net|/gross median 0.27 NIFTY, 0.19 SENSEX over 31 and 28 sessions. VENDOR OI ON UNTRADED LEGS (TD-S95-NEW-1) does not move flow after 09:15 on any of 22 symbol-sessions measured, but it inflates the BOOK beside it on days like SENSEX 2026-09-25 / 09-28 / 09-29. Runs with the owner privileges (security_invoker = false); adding a column here publishes it to anon. PRE-OPEN COLUMNS (S96-C, appended): call_preopen_dex_cr / put_preopen_dex_cr / net_preopen_dex_cr and their leg totals are the PRE-OPEN OI VALUED AT THE SETTLED DELTA x spot / 1e7 -- not the book as it stood at 08:30 -- so book = pre-open + flow splits the change into OI change only, never repricing; a surface labels it from x at pre-open OI. Same gap rule as flow. leg_no_anchor_dex_cr is the book DEX on sides with no anchor OI, the one term outside the split: leg book = leg pre-open + leg flow + leg_no_anchor_dex_cr exactly. These exist so a surface that draws held / added / removed since the pre-open reads the remembered value from here, never from its own memory. Never label second-order terms vanna or charm (L78-1).';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- CASE-2026-09-22, ADR-031 D6)
-- =====================================================================

REVOKE ALL ON public.v_dex_flow_vs_book FROM anon, authenticated;
GRANT SELECT ON public.v_dex_flow_vs_book TO anon, merdian_ro;

-- end-of-batch verification (TD-S94-NEW-3) -- must return ONE row:
--   has_view t | comment_len 3959 (computed from the literal in this file, '' unescaped; was 3284 before S96-C) |
--   anon_r t | anon_write f | merdian_ro_r t | authenticated_r f
SELECT to_regclass('public.v_dex_flow_vs_book') IS NOT NULL                         AS has_view,
       length(obj_description('public.v_dex_flow_vs_book'::regclass, 'pg_class'))    AS comment_len,
       has_table_privilege('anon', 'public.v_dex_flow_vs_book', 'SELECT')            AS anon_r,
       (has_table_privilege('anon', 'public.v_dex_flow_vs_book', 'INSERT')
        OR has_table_privilege('anon', 'public.v_dex_flow_vs_book', 'UPDATE')
        OR has_table_privilege('anon', 'public.v_dex_flow_vs_book', 'DELETE'))       AS anon_write,
       has_table_privilege('merdian_ro', 'public.v_dex_flow_vs_book', 'SELECT')      AS merdian_ro_r,
       has_table_privilege('authenticated', 'public.v_dex_flow_vs_book', 'SELECT')   AS authenticated_r;


-- =====================================================================
-- SECTION 4 of 4 -- checks. ONE STATEMENT PER RUN. Each states what fails it.
-- =====================================================================

-- 4a  anon reads it, in ONE execution with the acting role in the same result
--     (S84 settled form). Fails if anon cannot read, or reads zero rows while
--     4b says the symbols agree.
--     PASS: role_now anon | n per symbol = the book's leg_n = 1 row count for that
--     symbol (4b prints it) | one session, one expiry, one settled_ts per symbol.
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now, symbol, count(*) AS n,
       count(DISTINCT session_date) AS n_sess, count(DISTINCT expiry_date) AS n_exp,
       count(DISTINCT settled_ts) AS n_settled, min(flow_window) AS fw
  FROM public.v_dex_flow_vs_book GROUP BY symbol ORDER BY symbol;
COMMIT;

-- 4b  the join guard. Per symbol: the book's session/front vs P5's, the book's
--     front-leg row count, and the view's row count. Fails if a symbol that
--     agrees has n_view <> n_book, or a symbol that disagrees has n_view > 0.
--     PASS: agrees t -> n_view = n_book; agrees f -> n_view 0.
WITH b AS (SELECT symbol, min(session_date) AS s, min(expiry_date) AS e, count(*) AS n_book
             FROM public.v_dex_standing_book WHERE leg_n = 1 GROUP BY symbol),
     p AS (SELECT symbol, min((anchor_ts AT TIME ZONE 'Asia/Kolkata')::date) AS s,
                  min(expiry_date) AS e FROM public.v_oi_since_preopen GROUP BY symbol),
     v AS (SELECT symbol, count(*) AS n_view FROM public.v_dex_flow_vs_book GROUP BY symbol)
SELECT b.symbol, b.s AS book_session, p.s AS p5_session, b.e AS book_front, p.e AS p5_front,
       (b.s = p.s AND b.e = p.e) AS agrees, b.n_book, COALESCE(v.n_view, 0) AS n_view
  FROM b LEFT JOIN p USING (symbol) LEFT JOIN v USING (symbol) ORDER BY 1;

-- 4c  the identity book - flow = delta x oi(anchor) x spot / 1e7, per side, on
--     every strike where book, flow and anchor are all non-NULL. Fails if flow
--     and book sit on different clocks. It reads the view's own anchor column, so it
--     CANNOT see dOI joined to the wrong strike (fixture mutant A passed it); 4d does.
--     PASS: n_checked > 0 per side | max_abs_diff <= 1e-9.
SELECT symbol, 'CE' AS side, count(*) AS n_checked,
       max(abs((call_dex_cr - call_flow_cr) - delta_call * ce_oi_anchor_qty * spot / 1e7)) AS max_abs_diff
  FROM public.v_dex_flow_vs_book
 WHERE call_dex_cr IS NOT NULL AND call_flow_cr IS NOT NULL AND ce_oi_anchor_qty IS NOT NULL
   AND COALESCE(oi_call, 0) > 0
 GROUP BY symbol
UNION ALL
SELECT symbol, 'PE', count(*),
       max(abs((put_dex_cr - put_flow_cr) - delta_put * pe_oi_anchor_qty * spot / 1e7))
  FROM public.v_dex_flow_vs_book
 WHERE put_dex_cr IS NOT NULL AND put_flow_cr IS NOT NULL AND pe_oi_anchor_qty IS NOT NULL
   AND COALESCE(oi_put, 0) > 0
 GROUP BY symbol
 ORDER BY 1, 2;

-- 4d  INDEPENDENT RECOMPUTE from option_chain_snapshots (Rule 0, fourth clause):
--     anchor and settled rows read by ts equality, gap by the ENH-140 iv form,
--     flow re-derived without either view. Same arithmetic as the M-P7 extract,
--     whose replay equalled the live views 8/8 on 2026-10-09. Fails on any
--     difference in a leg flow total, the gap quantity or the no-anchor quantity.
--     PASS per symbol: d_call, d_put <= 1e-9 | d_gap = 0 | d_noanc = 0.
WITH v AS (SELECT DISTINCT symbol, expiry_date, anchor_ts, settled_ts,
                  leg_call_flow_cr, leg_put_flow_cr, leg_gap_d_oi_qty, leg_no_anchor_oi_qty
             FROM public.v_dex_flow_vs_book),
     a AS (SELECT v.symbol, c.strike,
                  max(c.oi) FILTER (WHERE c.option_type = 'CE') AS a_c,
                  max(c.oi) FILTER (WHERE c.option_type = 'PE') AS a_p
             FROM v JOIN public.option_chain_snapshots c
               ON c.ts = v.anchor_ts AND c.symbol = v.symbol AND c.expiry_date = v.expiry_date
            GROUP BY v.symbol, c.strike),
     s AS (SELECT v.symbol, c.strike, max(c.spot) AS spot,
                  max(c.oi)    FILTER (WHERE c.option_type = 'CE') AS oi_c,
                  max(c.oi)    FILTER (WHERE c.option_type = 'PE') AS oi_p,
                  max(c.delta) FILTER (WHERE c.option_type = 'CE') AS dl_c,
                  min(c.delta) FILTER (WHERE c.option_type = 'PE') AS dl_p,
                  bool_or(c.option_type = 'CE' AND (c.delta IS NULL OR (c.delta = 0 AND COALESCE(c.iv, 0) = 0))) AS g_c,
                  bool_or(c.option_type = 'PE' AND (c.delta IS NULL OR (c.delta = 0 AND COALESCE(c.iv, 0) = 0))) AS g_p
             FROM v JOIN public.option_chain_snapshots c
               ON c.ts = v.settled_ts AND c.symbol = v.symbol AND c.expiry_date = v.expiry_date
            GROUP BY v.symbol, c.strike),
     k AS (SELECT s.*, s.oi_c - a.a_c AS d_c, s.oi_p - a.a_p AS d_p
             FROM s LEFT JOIN a ON a.symbol = s.symbol AND a.strike = s.strike),
     r AS (SELECT symbol,
                  sum(CASE WHEN d_c IS NULL OR d_c = 0 OR g_c THEN 0 ELSE dl_c * d_c * spot / 1e7 END) AS call_f,
                  sum(CASE WHEN d_p IS NULL OR d_p = 0 OR g_p THEN 0 ELSE dl_p * d_p * spot / 1e7 END) AS put_f,
                  sum(CASE WHEN d_c IS NOT NULL AND d_c <> 0 AND g_c THEN abs(d_c) ELSE 0 END
                    + CASE WHEN d_p IS NOT NULL AND d_p <> 0 AND g_p THEN abs(d_p) ELSE 0 END) AS gap,
                  sum(CASE WHEN d_c IS NULL THEN COALESCE(oi_c, 0) ELSE 0 END
                    + CASE WHEN d_p IS NULL THEN COALESCE(oi_p, 0) ELSE 0 END) AS noanc
             FROM k GROUP BY symbol)
SELECT v.symbol,
       abs(v.leg_call_flow_cr - r.call_f) AS d_call,
       abs(v.leg_put_flow_cr  - r.put_f)  AS d_put,
       v.leg_gap_d_oi_qty - r.gap         AS d_gap,
       v.leg_no_anchor_oi_qty - r.noanc   AS d_noanc,
       r.call_f, r.put_f
  FROM v JOIN r USING (symbol) ORDER BY 1;

-- 4f  S96-C split. Per strike where book, pre-open and flow are all non-NULL, per side:
--     book = pre-open + flow. Per leg: book = pre-open + flow + no-anchor. Fails if the pre-open
--     columns use a different clock, gap rule or anchor than flow and book.
--     PASS: n_strike_sides > 0 | max_strike_diff <= 1e-9 | leg_diff <= 1e-9, per symbol.
SELECT symbol,
       count(*) FILTER (WHERE call_dex_cr IS NOT NULL AND call_preopen_dex_cr IS NOT NULL AND call_flow_cr IS NOT NULL)
     + count(*) FILTER (WHERE put_dex_cr IS NOT NULL AND put_preopen_dex_cr IS NOT NULL AND put_flow_cr IS NOT NULL) AS n_strike_sides,
       greatest(max(abs(call_dex_cr - call_preopen_dex_cr - call_flow_cr)),
                max(abs(put_dex_cr  - put_preopen_dex_cr  - put_flow_cr)))                AS max_strike_diff,
       max(abs(leg_net_dex_cr - leg_net_preopen_dex_cr - leg_net_flow_cr - leg_no_anchor_dex_cr)) AS leg_diff,
       max(leg_net_preopen_dex_cr) AS leg_net_preopen, max(leg_net_dex_cr) AS leg_net_book,
       max(leg_net_flow_cr) AS leg_net_flow
  FROM public.v_dex_flow_vs_book GROUP BY symbol ORDER BY 1;

-- 4e  cost, as anon, TWICE (one timing on a shared instance is a sample).
--     Fails if either run exceeds anon's 3 s ceiling (MV-6).
--     PASS: Execution Time < 3000 ms on both runs.
BEGIN;
SET LOCAL ROLE anon;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_dex_flow_vs_book;
COMMIT;
