-- =====================================================================
-- 2026-09-22_s81_v_gex_net_gamma_river.sql
-- S81 / ENH-126 -- L14 net-gamma river, 30 sessions (v_gex_net_gamma_river)
-- =====================================================================
--
-- WHAT THIS IS
--   Parity spec L14: daily net GEX with dampening/amplifying sign, price
--   threaded, over the last 30 sessions per symbol. 13 columns, grain
--   (symbol, session_date).
--
-- WHY gamma_metrics ONLY -- measured, not assumed (S81)
--   hist_gamma_metrics  2025-04-01 -> 2026-03-30   244 days/symbol
--   gamma_metrics       2026-06-10/12 -> present   72-74 days
--   gex_strike_snapshots 2026-05-25 -> present     81-82 days
--
--   The overlap query between hist_gamma_metrics and gamma_metrics
--   returned ZERO ROWS. They do not share a single day, so the x1e7 unit
--   bridge between the unscaled historical era and the Cr live era is
--   UNVERIFIED and cannot be verified from those two tables. Stitching
--   across 2026-03-30 without establishing that ratio empirically is the
--   TD-S30-CANDIDATE-1 trap, which cost seven sessions.
--
--   gamma_metrics also has NO REAL HOLES across its span: its only gap,
--   2026-09-11 -> 09-15, has exactly one missing weekday (09-14) and the
--   calendar marks it closed. gex_strike_snapshots by contrast has four
--   confirmed holes on trading days (06-03, 06-04, 06-08, 06-11), where
--   market_spot_session_markers shows capture ran and the gamma chain did
--   not.
--
--   The stretch 2026-03-31 -> 2026-05-24 is covered by NO source and is
--   fillable only by recompute from historical_option_chain_snapshots --
--   which, because it overlaps BOTH eras, is also the unit bridge. That
--   extension is DEFERRED and is a prerequisite for any 299-day river.
--
-- THE 15:15 IST CUT
--   ADR-022: continuous trading for F and O names ends 15:15; the index
--   is then frozen through the closing auction until 15:28. The shadow
--   runner (*/5 03-09 UTC) lands its final cycle around 15:25 IST, inside
--   that window, carrying a frozen spot. That run restates 15:14 rather
--   than observing anything new, so the daily value is the last run AT OR
--   BEFORE 15:15 and the later run is discarded.
--
-- session_complete
--   True when the session reached its final pre-auction cycle: any run at
--   or after 15:10 IST. NO date clause.
--
--   THE DATE CLAUSE WAS A DEFECT AND IS RECORDED AS ONE. The first draft
--   read "session_date before today OR a run at/after 15:15", which made
--   every past session complete BY CONSTRUCTION -- the column could not
--   fail for the reason it existed. 2026-08-17 is the counter-example it
--   missed: 64 runs on both symbols, last run at 14:10, writer stopped
--   about an hour early, and the old rule called the day finished.
--   Today mid-session now reads false under the same rule, no special
--   case.
--
--   15:10 rather than 15:15 because cycles stamp about seven seconds past
--   the five-minute mark: the 15:15 cycle lands at 15:15:07, outside the
--   at-or-before-15:15 test in `pick`. The last cycle that qualifies is
--   15:10:07, so THE DAILY VALUE IS EFFECTIVELY THE 15:10 CYCLE. That is
--   intended -- inside continuous trading, clear of the auction boundary
--   -- but the window is named 15:15 and the value taken is the 15:10
--   cycle, and those are not the same sentence.
--
-- gamma_side, AND WHY IT IS NOT regime
--   Derived from sign(net_gex) per ADR-015. gamma_metrics.regime is NOT
--   the sign: parity spec section 4 decision 2 records that dropping
--   flip_level from determine_regime moves ~3% of cycles and the
--   net_gex >= 0 suppression moves ~70%, and that decision is OPEN.
--   Consuming regime would import an unresolved question into a display
--   layer. Named gamma_side so the two cannot be confused (the
--   TD-S79-NEW-13 discipline). Two branches, no ELSE: exactly zero
--   yields NULL rather than a silent AMPLIFYING.
--
-- HOLES AND THE CALENDAR
--   A session with no data emits no row. Nothing interpolated, nothing
--   zero-filled. trading_calendar is NOT joined: measured S81, the table
--   is missing the 2026-05-28 Bakri Id closure row that
--   trading_calendar.json carries, so it would assert holiday where the
--   truth is unknown.
--
-- RETENTION
--   30 sessions is ~42 calendar days and fits inside the 90-day
--   gamma_metrics horizon jobid 19 enforces, so this panel does not block
--   re-enabling it (TD-S76-NEW-2). gamma_metrics starting 2026-06-10/12
--   is itself a retention artefact -- 90 days before 2026-09-09, when
--   jobid 19 was disabled.
--
-- VIEW, NOT A TABLE. gamma_metrics already persists every run, so the
--   history exists and only needs selecting. ADR-021 does not bite and no
--   Rule 10 ADR is triggered. The 90-day predicate is still deliberate:
--   it bounds the scan as the table grows unattended.
--
-- APPLY ORDER: Section 1 -> 2 -> 3 -> verify with Section 4.
-- RUN ONE STATEMENT AT A TIME (S72 Section 5).
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS so sql/ matches the database.
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_net_gamma_river AS
WITH bounded AS (
        -- 90 days is nearly the whole table today; it becomes the only
        -- thing bounding the scan while jobid 19 stays disabled.
        SELECT symbol,
               ts,
               (ts AT TIME ZONE 'Asia/Kolkata')       AS ts_ist,
               (ts AT TIME ZONE 'Asia/Kolkata')::date AS session_date,
               net_gex, spot, expiry_date, dte
          FROM gamma_metrics
         WHERE ts >= now() - interval '90 days'
           AND net_gex IS NOT NULL
     ), sess AS (
        -- Session aggregates over ALL runs, including those after 15:15:
        -- the intraday range is a property of the whole session, and
        -- last_ts_ist_any is what session_complete tests.
        SELECT symbol, session_date,
               count(*)     AS n_runs,
               min(net_gex) AS session_min_net_gex_cr,
               max(net_gex) AS session_max_net_gex_cr,
               max(ts_ist)  AS last_ts_ist_any
          FROM bounded
         GROUP BY symbol, session_date
     ), pick AS (
        -- The daily value: last run at or before 15:15 IST. DISTINCT ON
        -- is the argmax. A session whose only runs fall after 15:15 -- a
        -- late start, say -- yields NO ROW here rather than an
        -- auction-frozen one. Absence, not a stale value.
        SELECT DISTINCT ON (symbol, session_date)
               symbol, session_date, ts, net_gex, spot, expiry_date, dte
          FROM bounded
         WHERE ts_ist::time <= time '15:15'
         ORDER BY symbol, session_date, ts DESC
     ), ranked AS (
        SELECT p.symbol, p.session_date, p.ts, p.net_gex, p.spot,
               p.expiry_date, p.dte,
               s.n_runs, s.session_min_net_gex_cr, s.session_max_net_gex_cr,
               s.last_ts_ist_any,
               row_number() OVER (PARTITION BY p.symbol
                                  ORDER BY p.session_date DESC) AS session_rank
          FROM pick p
          JOIN sess s
            ON s.symbol = p.symbol AND s.session_date = p.session_date
     )
SELECT
    symbol,
    session_date,
    ts,
    session_rank,
    net_gex AS net_gex_cr,
    -- Two branches, no ELSE. Exactly zero yields NULL, which is honest;
    -- an ELSE would label it AMPLIFYING on no evidence. ADR-015 sign
    -- convention: positive = dampening.
    CASE WHEN net_gex > 0 THEN 'DAMPENING'
         WHEN net_gex < 0 THEN 'AMPLIFYING'
    END AS gamma_side,
    spot,
    session_min_net_gex_cr,
    session_max_net_gex_cr,
    n_runs,
    -- NO date clause. An earlier version had one -- session_date before
    -- today counts as complete -- and it was WRONG: it declared every past
    -- session complete BY CONSTRUCTION, so it could not detect a partial
    -- day. 2026-08-17 is the case it missed: 64 runs on both symbols, last
    -- run 14:10, writer stopped ~1h early, old rule said complete. 15:10
    -- because cycles stamp ~:07s past the mark, so the 15:15 cycle lands
    -- at 15:15:07 and the last qualifying one is 15:10:07.
    (last_ts_ist_any >= (session_date + time '15:10')) AS session_complete,
    expiry_date,
    dte
  FROM ranked
 WHERE session_rank <= 30;


-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE)
-- =====================================================================

COMMENT ON VIEW public.v_gex_net_gamma_river IS
  'S81 / ENH-126 -- L14 net-gamma river, 30 sessions. One row per symbol per session, the settled daily net dealer gamma with its sign and the spot it was observed at. Grain (symbol, session_date). Consumers MUST ORDER BY session_rank or session_date -- a view body carries no ordering guarantee. session_rank 1 is the most recent session. SOURCE IS gamma_metrics ONLY, AND THAT IS A DECISION, NOT A CONVENIENCE. Measured S81: hist_gamma_metrics spans 2025-04-01 to 2026-03-30 and gamma_metrics starts 2026-06-10/12, so the two DO NOT OVERLAP AT ALL and the x1e7 unit bridge between the eras is UNVERIFIED and not verifiable from those two tables. Stitching them would be the TD-S30-CANDIDATE-1 trap, which cost seven sessions. One source means one writer, one unit (Cr, per TD-NEW-3), and no bridge. EXPIRY DAYS NEED NO SPECIAL HANDLING, by construction rather than by omission: S62 rules that 0-DTE flat-vol net_gex is numerically unreconstructible and must be live-sourced, and gamma_metrics IS the live source, so every session here including expiry days is already S62-compliant. THE DAILY VALUE IS THE LAST RUN AT OR BEFORE 15:15 IST, not the last run of the session. Per ADR-022 continuous trading for F and O names ends at 15:15 and the index is then FROZEN through the closing auction until 15:28, so the shadow runner cycle that lands around 15:25 restates the 15:14 value rather than observing a new one. Taking it would thread an auction-frozen spot into every session of the river. session_complete is true when the session reached its final pre-auction cycle: any run at or after 15:10 IST. THERE IS NO DATE CLAUSE. An earlier version read -session_date before today OR a run at or after 15:15- and that was a DEFECT: it declared every past session complete BY CONSTRUCTION, so the column could not fail for the reason it existed. 2026-08-17 is the counter-example it missed -- 64 runs on both symbols, last run 14:10, the writer stopped about an hour early, and the old rule called the day finished. Today mid-session now reads false under the same rule, with no special case. THE DAILY VALUE IS EFFECTIVELY THE 15:10 CYCLE. Runs stamp about seven seconds past the five-minute mark, so the 15:15 cycle lands at 15:15:07 and falls outside the at-or-before-15:15 test. The last qualifying cycle is 15:10:07. That is intended -- inside continuous trading and clear of the auction boundary -- but the window is named 15:15 while the value taken is the 15:10 cycle, and those are not the same sentence. gamma_side IS DERIVED FROM sign(net_gex) PER ADR-015 AND IS DELIBERATELY NOT gamma_metrics.regime. regime is not the sign: parity spec section 4 decision 2 records that dropping flip_level from determine_regime moves ~3 pct of cycles and the net_gex >= 0 suppression moves ~70 pct, and that decision is OPEN. Consuming regime here would import an unresolved question into a display layer. The column is named gamma_side rather than regime so the two cannot be confused. Two explicit branches and no ELSE: a net_gex of exactly zero yields NULL, which is honest, rather than being silently labelled AMPLIFYING. READ THE SIGN WITH ADR-024 AMENDMENT A IN MIND. At per-strike level the sign of gex_cr is driven by OI imbalance rather than by positioning. At this aggregate level the sign is the conventional dealer-gamma regime read, but it is still arithmetic over a book, not an observation of dealer behaviour. HOLES RENDER AS ABSENCE. A session with no data emits no row; nothing is interpolated and nothing is zero-filled. trading_calendar is deliberately NOT joined: it was measured S81 to be missing the 2026-05-28 Bakri Id closure row that trading_calendar.json carries, so labelling holidays from it would assert holiday where the truth is unknown. This view states only what gamma_metrics holds. WINDOW AND RETENTION ARE COUPLED. 30 sessions is about 42 calendar days and fits inside the 90-day gamma_metrics horizon that pg_cron jobid 19 enforces, so this panel does NOT block re-enabling it (TD-S76-NEW-2). Note that gamma_metrics starting 2026-06-10/12 is a RETENTION ARTEFACT -- 90 days before 2026-09-09, when jobid 19 was disabled -- so the available span records when the janitor stopped, not when data began, and it will snap back to 90 days on re-enable. A 299-day river would not survive that. NO HISTORY TABLE IS NEEDED and ADR-021 does not bite: gamma_metrics already persists every run, unlike the latest-run-scoped views that forced gex_pin_maxpain_history at S80. The 90-day predicate is nevertheless deliberate -- it is nearly the whole table today, and becomes the only thing bounding the scan as the table grows while jobid 19 is off. Display-only per the S37 GEX-as-context-not-gate ruling; it routes nothing.';


-- =====================================================================
-- SECTION 3 of 4 -- anon grants (LIVE). TWO STATEMENTS, run separately.
-- =====================================================================

REVOKE ALL ON public.v_gex_net_gamma_river FROM anon;

GRANT SELECT ON public.v_gex_net_gamma_river TO anon;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run separately, after 1-3)
-- =====================================================================

-- 4a -- ADR-025 D2 clause 2. Expect the 90-day predicate to bound the
--       scan and NO unbounded read of gamma_metrics.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_net_gamma_river;

-- 4b -- D2 clause 1: read the output. Expect 30 rows per symbol, ts
--       always at or before 15:15 IST, session_complete true on every
--       row except possibly rank 1 during market hours, and
--       net_gex_cr between session_min and session_max on every row.
--
-- SELECT symbol, session_rank, session_date,
--        (ts AT TIME ZONE 'Asia/Kolkata')::time AS ts_ist,
--        round(net_gex_cr, 1) AS net_gex_cr, gamma_side, round(spot, 2) AS spot,
--        round(session_min_net_gex_cr, 1) AS sess_min,
--        round(session_max_net_gex_cr, 1) AS sess_max,
--        n_runs, session_complete, expiry_date, dte
--   FROM public.v_gex_net_gamma_river
--  ORDER BY symbol, session_rank;

-- 4c -- invariants, as one statement. Every count must be 0.
--
-- SELECT 'rows_after_1515'        AS chk, count(*) FROM public.v_gex_net_gamma_river
--   WHERE (ts AT TIME ZONE 'Asia/Kolkata')::time > time '15:15'
-- UNION ALL
-- SELECT 'value_outside_session_range', count(*) FROM public.v_gex_net_gamma_river
--   WHERE net_gex_cr < session_min_net_gex_cr OR net_gex_cr > session_max_net_gex_cr
-- UNION ALL
-- SELECT 'gamma_side_null_on_nonzero', count(*) FROM public.v_gex_net_gamma_river
--   WHERE gamma_side IS NULL AND net_gex_cr <> 0
-- UNION ALL
-- SELECT 'rank_gt_30', count(*) FROM public.v_gex_net_gamma_river WHERE session_rank > 30
-- UNION ALL
-- SELECT 'duplicate_symbol_session', count(*) FROM (
--   SELECT symbol, session_date FROM public.v_gex_net_gamma_river
--    GROUP BY symbol, session_date HAVING count(*) > 1) d
-- UNION ALL
-- -- The regression this column exists for. MUST be 0: 2026-08-17 is a
-- -- partial compute day (writer stopped ~14:10) and must read false.
-- SELECT 'aug17_wrongly_complete', count(*) FROM public.v_gex_net_gamma_river
--   WHERE session_date = DATE '2026-08-17' AND session_complete
-- UNION ALL
-- -- Its mirror: every OTHER listed session must read true, except the
-- -- current IST date while the session is still running.
-- SELECT 'other_sessions_wrongly_incomplete', count(*) FROM public.v_gex_net_gamma_river
--   WHERE NOT session_complete
--     AND session_date <> DATE '2026-08-17'
--     AND session_date <> (now() AT TIME ZONE 'Asia/Kolkata')::date;

-- 4d -- anon privilege audit (expect SELECT only) and comment length.
--
-- SELECT p.privilege_type,
--        has_table_privilege('anon', 'public.v_gex_net_gamma_river', p.privilege_type) AS anon_has
--   FROM (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),
--                ('TRUNCATE'),('REFERENCES'),('TRIGGER')) AS p(privilege_type)
--  ORDER BY 1;
--
-- SELECT length(obj_description('public.v_gex_net_gamma_river'::regclass, 'pg_class')) AS comment_len,
--        left(obj_description('public.v_gex_net_gamma_river'::regclass, 'pg_class'), 30) AS starts_with;
