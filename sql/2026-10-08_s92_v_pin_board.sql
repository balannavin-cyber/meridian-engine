-- =====================================================================
-- 2026-10-08_s92_v_pin_board.sql
-- S92 / ENH-133 + ENH-122/125 -- ADR-025 parity L12 (pin conviction) read
-- surface for the Marketview Pin tab.
--   public.v_pin_board   grain (symbol, ts) for the latest OPEN session,
--                        front expiry only
-- =====================================================================
--
-- AUTHORED 2026-10-08 (S92), ruling S92-D (docs/research/s92_parity/
-- rulings_s92.md). Read-only view; S90-J class "anything else" -- deploys
-- any time. Nothing in this file has been run against the database.
--
-- WHY A VIEW AND NOT A GRANT
--   gex_cycle_history deliberately withholds anon (its own DDL:
--   "anon is deliberately NOT granted ... supply the key -- never restore
--   the grant"; RLS is off, so a table grant would be the whole boundary,
--   TD-S81-NEW-2). This view exposes ONE session of ONE expiry and only the
--   pin / concentration columns. The table's ACL is not touched.
--
--   The view runs with its OWNER's privileges (security_invoker = false,
--   set explicitly below) -- that is how anon reads through it without a
--   table grant. It is the intended boundary, and it is the reason the
--   column list is closed: adding a column here publishes it to anon.
--
-- WHAT IT RETURNS
--   For each symbol: every session_gate_state = 'OPEN' row of the latest
--   IST date that has an OPEN row, restricted to the expiry_date of the
--   latest OPEN row (the front leg; S90-B writes W1 only, and this keeps the
--   view one-leg if a W2 compute path is ever ruled in). is_latest marks the
--   newest row per symbol.
--
--   On a holiday or before the first OPEN cycle of a day it returns the
--   previous session -- the consumer decides whether that is shown, using
--   session_date_ist against trading_calendar, exactly as the board's gate
--   already does for every sibling view. FROZEN and PRE_TICK rows are never
--   returned (ADR-030: written, filtered on read).
--
-- NOTHING IS DERIVED HERE. Every column is a stored column of
--   gex_cycle_history (pin_state, held_for_cycles and conviction are
--   computed by core/pin_state.py at write time and finalised by the EOD
--   reconciler). The lead in share points is NOT derivable from these
--   columns without top-2 shares; the board already computes it from
--   v_gex_strike_rank (ENH-125) and must keep doing so.
--
-- BANDS. pin_state thresholds come from merdian_parameters (pin_state.*,
--   seeded S90). conviction is D-5c stage 1 and carries NO measured band
--   (D-6): a consumer shows the number, never a word for it.
--
-- APPLY ORDER: Section 1 -> 2 -> 3, verify with Section 4.
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS (TD-S81-NEW-5).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_pin_board
WITH (security_invoker = false) AS
WITH RECURSIVE symbols AS (
        -- Loose index scan over the PK (symbol, expiry_date, ts): symbol is
        -- the LEADING column, so min(symbol) and min(symbol) WHERE symbol > s
        -- are index seeks. Symbols are DERIVED, never a literal list
        -- (TD-S72-NEW-3). O(distinct symbols) seeks; SELECT DISTINCT would
        -- be a full scan of a table kept indefinitely (ADR-030 D2).
        SELECT (SELECT min(h.symbol) FROM public.gex_cycle_history h) AS symbol
        UNION ALL
        SELECT (SELECT min(h.symbol)
                  FROM public.gex_cycle_history h
                 WHERE h.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), last_open AS MATERIALIZED (
        -- MATERIALIZED so the lateral below runs ONCE PER SYMBOL. Without it
        -- PostgreSQL inlines the CTE and may put the lateral on the inner side
        -- of the join, re-running it for every OPEN row of the symbol --
        -- measured S92 on a synthetic load (loops = rows), and this table is
        -- kept indefinitely (ADR-030 D2). Verify loops=1 per symbol in V6.
        -- Newest OPEN row per symbol. Served by the partial index
        -- ix_gex_cycle_history_sym_ts_session (symbol, ts DESC)
        -- WHERE session_gate_state = 'OPEN' -- the predicate below must stay
        -- textually identical to the index predicate or the planner cannot
        -- use it.
        SELECT s.symbol, lo.ts AS last_ts, lo.expiry_date AS front_expiry,
               (lo.ts AT TIME ZONE 'Asia/Kolkata')::date AS session_date_ist
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT h.ts, h.expiry_date
                 FROM public.gex_cycle_history h
                WHERE h.symbol = s.symbol
                  AND h.session_gate_state = 'OPEN'
                -- expiry_date ASC breaks the tie when two legs share the
                -- newest ts: without it LIMIT 1 returns an arbitrary leg
                -- (measured on a synthetic W1+W2 cycle, S92). Same canonical
                -- form as the runner's latest-snapshot selector (89ad2bb).
                ORDER BY h.ts DESC, h.expiry_date ASC
                LIMIT 1
          ) lo
         WHERE s.symbol IS NOT NULL
     )
SELECT h.symbol,
       h.expiry_date,
       l.session_date_ist,
       h.ts,
       (h.ts = l.last_ts)            AS is_latest,
       h.run_id,
       h.dte,
       h.spot,
       h.pin_leader_strike,
       h.gamma_at_pin,
       h.runnerup_share_ratio,
       h.top5_share,
       h.top5_share_n_ranks,
       h.conc_top1_share,
       h.conc_hhi,
       h.max_pain_strike,
       h.call_wall_strike,
       h.put_wall_strike,
       h.pin_state,
       h.pin_state_reason,
       h.held_for_cycles,
       h.conviction,
       h.conviction_reason,
       h.is_fresh,
       h.reconciled_at
  FROM last_open l
  -- LATERAL, not a plain JOIN: it makes the session window a parameterized
  -- range on the partial index (symbol, ts DESC) WHERE OPEN. As a plain join
  -- the planner hashed last_open and SEQ-SCANNED the whole table -- measured
  -- S92 on a 10,508-row synthetic load. The predicate must stay textually
  -- identical to the index predicate (session_gate_state = 'OPEN').
  CROSS JOIN LATERAL (
       SELECT x.*
         FROM public.gex_cycle_history x
        WHERE x.symbol = l.symbol
          AND x.session_gate_state = 'OPEN'
          -- the IST day of the newest OPEN row, as a ts range so the index
          -- serves it without a cast on x.ts
          AND x.ts >= (l.session_date_ist::timestamp AT TIME ZONE 'Asia/Kolkata')
          AND x.ts <= l.last_ts
          AND x.expiry_date = l.front_expiry
  ) h;


-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE, not commented out -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_pin_board IS
  'S92 / ADR-025 parity L12 read surface for the Marketview Pin tab (ruling S92-D). Grain (symbol, ts): every session_gate_state = OPEN row of gex_cycle_history for the latest IST date that has an OPEN row, restricted to the expiry_date of the newest OPEN row (front leg). is_latest marks the newest row per symbol. On a holiday or before the first OPEN cycle it returns the PREVIOUS session; compare session_date_ist with trading_calendar before showing it as today. FROZEN and PRE_TICK rows are never returned (ADR-030: written and flagged, filtered on read). Nothing is derived here: pin_state (NO PIN | SHIFTING | STABLE | LOCKED), held_for_cycles and conviction are stored by core/pin_state.py at write time and finalised by the EOD reconciler (reconciled_at NULL until then). pin_state thresholds are merdian_parameters pin_state.*. conviction = (1 - runnerup_share_ratio) * boost(T), boost(T) = 2.53 * T^(-0.5), D-5c STAGE 1 ONLY, NO MEASURED BAND (D-6): show the number, never a word. conc_top1_share is a TOP-1 SHARE, not a Herfindahl; conc_hhi is the true Herfindahl. The lead in share points is not derivable here; read it from v_gex_strike_rank. Runs with the owner''s privileges (security_invoker = false) so anon reads it without a grant on gex_cycle_history, which deliberately has none; adding a column here publishes it to anon.';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- TD-S81-NEW-5, CASE-2026-09-22)
-- REVOKE FIRST, then GRANT. Supabase DEFAULT PRIVILEGES hand new objects
-- ALL; the REVOKE is what prevents that, not belt-and-braces. Target ACL:
-- anon=r, merdian_ro=r -- SELECT alone, matching the ten clean siblings
-- measured 2026-10-03 (the L7/L8 file, Section 4), NOT the two anon=rm
-- views.
-- =====================================================================

REVOKE ALL ON public.v_pin_board FROM anon;

GRANT SELECT ON public.v_pin_board TO anon;

GRANT SELECT ON public.v_pin_board TO merdian_ro;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run after 1-3; each is a real check)
-- Each states what makes it fail. A check that cannot fail for the reason
-- it names is documentation, not verification (CLAUDE.md rule 0).
-- =====================================================================

-- V1  Grain. FAILS IF: any symbol has more than one expiry_date, more than
--     one session_date_ist, other than exactly one is_latest row, or a row
--     whose IST date differs from session_date_ist (the range predicate
--     admitted the previous day).
--     EXPECTED: per symbol n_exp = 1, n_day = 1, n_latest = 1, n_offday = 0,
--     and n_rows > 0.
-- SELECT symbol,
--        count(*)                                   AS n_rows,
--        count(DISTINCT expiry_date)                AS n_exp,
--        count(DISTINCT session_date_ist)           AS n_day,
--        count(*) FILTER (WHERE is_latest)          AS n_latest,
--        count(*) FILTER (WHERE (ts AT TIME ZONE 'Asia/Kolkata')::date
--                                <> session_date_ist) AS n_offday,
--        min(ts) AS first_ts, max(ts) AS last_ts
--   FROM public.v_pin_board
--  GROUP BY symbol ORDER BY symbol;

-- V2  The view returns exactly what the table holds for that session, and
--     nothing gated out. Run as postgres. FAILS IF: n_view <> n_table for a
--     symbol, or n_view_not_open > 0. The table side is computed
--     independently (no lateral, no recursive CTE), so a wrong range
--     predicate or a dropped gate in the view shows here.
--     EXPECTED: n_view = n_table, n_view_not_open = 0.
-- WITH t AS (
--   SELECT symbol, max(ts) AS last_ts
--     FROM public.gex_cycle_history
--    WHERE session_gate_state = 'OPEN'
--    GROUP BY symbol
-- ), te AS (
--   -- min(): if two legs share the newest ts, the front is the earlier
--   -- expiry -- the same tie-break as the view (S92 synthetic W1+W2 test).
--   SELECT t.symbol, t.last_ts, min(h.expiry_date) AS expiry_date
--     FROM t JOIN public.gex_cycle_history h
--       ON h.symbol = t.symbol AND h.ts = t.last_ts
--      AND h.session_gate_state = 'OPEN'
--    GROUP BY t.symbol, t.last_ts
-- )
-- SELECT te.symbol,
--        (SELECT count(*) FROM public.gex_cycle_history h
--          WHERE h.symbol = te.symbol AND h.session_gate_state = 'OPEN'
--            AND h.expiry_date = te.expiry_date
--            AND (h.ts AT TIME ZONE 'Asia/Kolkata')::date
--                = (te.last_ts AT TIME ZONE 'Asia/Kolkata')::date)  AS n_table,
--        (SELECT count(*) FROM public.v_pin_board v
--          WHERE v.symbol = te.symbol)                               AS n_view,
--        (SELECT count(*) FROM public.v_pin_board v
--           JOIN public.gex_cycle_history h
--             ON h.symbol = v.symbol AND h.expiry_date = v.expiry_date AND h.ts = v.ts
--          WHERE v.symbol = te.symbol
--            AND h.session_gate_state <> 'OPEN')                    AS n_view_not_open
--   FROM te ORDER BY te.symbol;

-- V3  ANON PATH, and the BOUNDARY. ONE EXECUTION each, current_user beside
--     the result (S84 §D.40.1: the SQL editor opens a new session per run).
--   V3a FAILS IF: role_now is not anon, or n is 0 for either symbol.
--       EXPECTED: role_now = anon, two rows, n > 0.
-- BEGIN;
--   SET LOCAL ROLE anon;
--   SELECT current_user AS role_now, symbol, count(*) AS n
--     FROM public.v_pin_board GROUP BY symbol ORDER BY symbol;
-- COMMIT;
--   V3b THE CONTROL: anon must still NOT read the base table. This is the
--       check that proves the view did not open the table. FAILS IF it
--       returns rows. EXPECTED: ERROR 42501 permission denied for table
--       gex_cycle_history. (Run it as its own execution; the error aborts
--       the transaction, which is the pass.)
-- BEGIN;
--   SET LOCAL ROLE anon;
--   SELECT current_user AS role_now, count(*) FROM public.gex_cycle_history;
-- COMMIT;

-- V4  The COMMENT actually landed. FAILS IF: comment_len is NULL or differs
--     from the file literal.
--     EXPECTED, COMPUTED FROM THIS FILE'S LITERAL before any apply, never
--     read back off the database:
--       v_pin_board  comment_len = 1341   comment_md5 = 19d0c5a08c36cdcca8cecabeb244c36b
--     If the literal is edited before the apply, RECOMPUTE from the file.
-- SELECT c.relname,
--        length(obj_description(c.oid,'pg_class')) AS comment_len,
--        md5(obj_description(c.oid,'pg_class'))    AS comment_md5
--   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND c.relname = 'v_pin_board';

-- V5  ACL and invoker mode. FAILS IF: relacl carries anything for anon
--     beyond r, or reloptions does not show security_invoker=false.
--     EXPECTED: relacl contains anon=r/postgres and merdian_ro=r/postgres
--     and no other anon entry; reloptions = {security_invoker=false}.
-- SELECT c.relacl, c.reloptions
--   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND c.relname = 'v_pin_board';

-- V6  Latency and access path (ADR-021). Two things to read in the plan:
--     (a) the last_open lateral (Index Scan using
--         ix_gex_cycle_history_sym_ts_session) shows loops = the number of
--         symbols (2), and (b) execution time.
--     FAILS IF: execution exceeds 3,000 ms -- anon's statement_timeout is
--     3 s (MV-6, S90), the ceiling that actually binds this consumer, not
--     PostgREST's 8 s -- or the last_open lateral's loops exceed the symbol
--     count (the CTE was inlined and the lateral re-runs per row).
--     A Seq Scan on gex_cycle_history for the session window is NOT a fail
--     while the table is small: MEASURED S92 on PostgreSQL 16 with ANALYZE,
--     the planner seq-scanned at 10,508 rows (2.8 ms) and switched to a PK
--     range scan at 88,811 rows (0.99 ms, loops = 2). Live at ~150 rows per
--     trading day it crosses that size in roughly two years; from then on a
--     Seq Scan here IS a fail.
--     EXPECTED today: execution well under 100 ms; last_open loops = 2.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_pin_board;

-- =====================================================================
-- NOT INCLUDED, DELIBERATELY
--   * No history beyond one session. The 30-session HHI percentile
--     (D-5c stage 2) needs ~6 weeks of gex_cycle_history and a ruling on
--     its read surface; it is not added here.
--   * No flip, regime or IV columns. The Pin tab does not need them, and
--     every column here is published to anon.
--   * No change to gex_cycle_history's ACL.
-- =====================================================================
