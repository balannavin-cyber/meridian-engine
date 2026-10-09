-- =====================================================================
-- 2026-10-09_s93_v_dex_standing_book.sql
-- S93 / ENH-140 -- P6 of the S92-I post-parity track: the DEX standing
-- book, the delta exposure standing in the open interest, per strike.
--   public.v_dex_standing_book   grain (symbol, expiry_date, strike)
-- =====================================================================
--
-- AUTHORED 2026-10-09 (S93). Read-only view; S90-J class "anything else"
-- -- deploys any time. NOTHING IN THIS FILE HAS BEEN RUN AGAINST THE
-- DATABASE. The body below was costed through bin/roq.sh as a plain
-- SELECT (EXPLAIN ANALYZE, numbers in Section 4 note 4b), but no CREATE,
-- COMMENT or GRANT has been issued.
--
-- Design note: docs/research/s93_priority/p6/P6_dex_design_note.md.
-- Every measurement cited here is recorded there with its probe SQL.
-- NOT A PARITY LAYER. ADR-025 is closed (Amendment D); this adds no
-- layer and amends no disposition. Display-only (S37).
--
-- WHAT IT RETURNS
--   Per symbol, the newest IST date that is a SESSION, and per leg of
--   that session the SETTLED run, and per strike of that run the delta
--   exposure in Rs crore.
--
--   SESSION is decided HERE, not by the consumer. Two clauses, stepping
--   back up to 5 dates from the symbol's newest chain run:
--     1. trading_calendar holds no explicit is_open = false row. A
--        MISSING row is not a verdict (ADR-020) and does not drop a
--        date -- which is why clause 2 is not redundant.
--     2. THE TAPE MOVED: count(DISTINCT spot) > 1 over
--        market_spot_snapshots for that symbol and date up to 15:15 IST
--        -- the house liveness rule, ADR-030 / ENH-133 section 3.6.
--   Clause 2 is the one that catches 2026-10-02: 77 frozen chain cycles,
--   ~143k rows, and NO trading_calendar row at all (TD-S92-NEW-5), so a
--   consumer-side calendar gate would have drawn a holiday's frozen book
--   as the standing book. Measured: 10-02 reads 1 tick / distinct_spot 1
--   on both symbols; 10-08 reads 360 / 349 and 360 / 359.
--   Clause 2 also subsumes ENH-133's PRE_TICK state -- 0 or 1 tick
--   cannot produce 2 distinct values.
--
--   WHY market_spot_snapshots AND NOT THE CHAIN'S OWN spot. The chain's
--   spot is in no index (idx_ocs_ts_symbol_expiry carries ts, symbol,
--   expiry_date), so count(DISTINCT spot) there is a heap scan: measured
--   899 ms for ONE symbol-day (59,100 rows, 5,554 buffer reads) against
--   0.578 ms on market_spot_snapshots. Five candidate dates x two
--   symbols would exceed anon's 3 s ceiling (MV-6) on that clause alone.
--   The two are the same event -- the chain copies spot from that feed at
--   capture time, and on 2026-10-02 both are frozen at the identical
--   value (NIFTY 22421.95, SENSEX 71909.7). THE CHAIN-SIDE TEST IS KEPT
--   AS CHECK 4f so the claim that they agree is a test, not a comment.
--
--   SETTLED RUN = the last run at or before 15:15 IST of the session,
--   per (symbol, expiry_date). The ENH-126 / v_gex_net_gamma_river rule
--   verbatim: after 15:15 the index is frozen through the closing
--   auction (ADR-022), so a later run threads an auction-frozen spot
--   into the book. Mid-session the settled run IS the latest run, so the
--   board is live; after 15:15 it holds at the 15:10 cycle.
--
--   BOTH LEGS, and leg_n ranks them by expiry_date. Measured: run_id is
--   per (symbol, ts, expiry_date), NOT per cycle -- at one ts the chain
--   carries a different run_id for each leg (SENSEX 2026-10-08
--   09:40:07: exp 10-08 -> 543bbd01..., exp 10-15 -> e7c6f394...), and
--   gex_strike_snapshots holds the W1 leg only, so W2's run is not
--   discoverable from it. Consumers filter leg_n = 1 for the front leg.
--
-- THE SIGN, AND THE ONE PLACE THIS MUST NOT COPY GEX
--   gex_cr carries an EXPLICIT PE -> negative flip because vendor gamma
--   is positive on both sides and the sign has to come from somewhere
--   (signed_gamma_exposure: "return -base if option_type == PE").
--   DELTA ALREADY CARRIES ITS OWN SIGN -- measured, PE delta is stored
--   negative (min -0.99341 on the SENSEX settled run, 56 negative / 0
--   positive). So there is NO second flip here. Copying GEX's
--   "CASE WHEN option_type = 'PE' THEN -1.0" would double the negation,
--   turn put_dex positive, destroy the netting, and still look
--   plausible because both sides would simply be positive. That is the
--   most likely transcription defect in this build, so it is ASSERTED,
--   not left to this comment: in the Python by the offline test's A3, in
--   this SQL by check 4c, and between the two by check 4i -- which was
--   exercised against a deliberately double-flipped view and caught it
--   (put_dex_cr off by 1.440e+03 Cr).
--
-- NO DEALER COLUMN, AND NO DEALER CLAIM
--   ADR-014 section 2.3 -- which ADR-015 says it carries unchanged --
--   reads positive gex_cr as DEALER LONG, with calls the positive term:
--   the convention is calls dealer-long, puts dealer-short. ADR-015's
--   own gloss says it coincides with "dealers short calls and long
--   puts", the exact inverse on both legs. The CODE is not in doubt
--   (the reconstruction matched the stored column to 1.17e-9 Cr); the
--   ENGLISH in ADR-015 is inverted. Design note section 3.1.
--   The two readings differ in SIZE always and in SIGN conditionally:
--     GEX convention      -> dealer delta = call_dex_cr - put_dex_cr
--     dealers short all   -> dealer delta = -net_dex_cr
--   On NIFTY W1 2026-10-08 those are +129,272.61 and +11,878.01 Cr --
--   the same sign on that leg, an order of magnitude apart. They differ
--   in SIGN whenever net_dex_cr > 0, which was NOT observed on the four
--   legs measured (all four were negative, so both readings came out
--   positive); four legs of one run says nothing about how often that
--   holds.
--   Choosing between them is P2's question (S92-I item 2). So this view
--   publishes the OI-SIGNED columns ONLY. There is no dealer column, no
--   negation, and NOTHING here asserts that any dealer number is
--   -net_dex_cr. Every surface rendering these columns reads
--     "open-interest delta -- dealer side unruled (P2)".
--
-- NULL IS A GAP, NEVER A ZERO
--   The vendor drops the whole greeks block together: measured over the
--   whole 2026-10-08 session, 55,228 positive-OI rows, EVERY delta = 0
--   row also carries gamma = 0 AND iv = 0 (2,321/2,321 NIFTY,
--   7,053/7,053 SENSEX), with ZERO rows at delta = 0 with iv > 0 and
--   ZERO at delta <> 0 with iv = 0. delta is NEVER NULL in the data but
--   IS nullable in the schema, so both branches are handled.
--   The gap is ITM-concentrated and put-asymmetric: at the SENSEX
--   settled run the ITM subset is 3 CE rows / 4,100 units against 51 PE
--   rows / 7,722,860 units. An ITM option cannot have zero delta.
--   So: a side with OI and no delta publishes NULL, never 0. A side with
--   no OI publishes 0, which is a TRUE zero. The un-deltaed OI rides
--   along in oi_call_no_delta / oi_put_no_delta, so the defect travels
--   inside the artefact it degrades.
--
-- WHY THE LEG TOTALS ARE COLUMNS (and not the consumer's sum)
--   Because net_dex_cr is NULL on one-sided-gap strikes,
--   sum(net_dex_cr) <> sum(call_dex_cr) + sum(put_dex_cr). Measured on
--   the 2026-10-09 13:20 IST run, NIFTY W1: 103,096.29 - 107,932.77 =
--   -4,836.48 against a sum(net_dex_cr) of -3,446.47 -- a 1,390.01 Cr
--   discrepancy that is exactly the good half of the one-sided-gap
--   strikes. A consumer adding the per-strike column would silently drop
--   it. leg_*_dex_cr are window sums over each side's MEASURED
--   contribution, so the client never sums and never computes the wrong
--   one (S92-G: one rule, one implementation, in the database).
--   THEY ARE THE MEASURED PART OF THE LEG, NOT A COMPLETE TOTAL:
--   leg_gap_oi_qty is the OI they do not cover, and the two are read
--   together or not at all.
--   NO cum_net_dex_cr. Its only consumer was the cumulative zero-delta
--   candidate, withdrawn as degenerate; a running sum over
--   COALESCE(.., 0) walks past gap strikes as if they were zero with no
--   flag that it did.
--
-- NO ZERO-DELTA COLUMN. The two candidates in the P6 brief were measured
--   and are withdrawn: the cumulative has NO zero crossing on any of 4
--   legs under either of two delta sets, and "nearest strike to zero net
--   DEX" lands on the chain's lowest strike, where net is 0 because
--   there is no OI. Their replacement -- S*, the RE-PRICED zero-delta
--   level, Sum_i delta_i(S*) x OI_i = 0, specified to reuse the ENH-131
--   / v_gex_repriced_flip code path with gamma replaced by delta -- is
--   specified in the design note section 5.2 and is PENDING OPERATOR
--   RULING. An absent column, not a provisional one.
--
-- ROW COUNT. Measured live on the 2026-10-09 13:20 IST settled runs:
--   NIFTY 239 + 235, SENSEX 198 + 190 = 862 rows -- under PostgREST's
--   1,000-row cap (rule 15) but NOT BY MUCH, and SENSEX chains lengthen.
--   Consumers filter leg_n = 1 (437 rows) and page with .range()
--   otherwise. Stated so a truncation is never discovered as missing
--   strikes. Zero-OI strikes are deliberately KEPT (net_dex_cr = 0 is a
--   true zero there) so the book shares one strike axis with the chain;
--   gex_strike_snapshots drops them, which is why it reads 159 rows
--   where the chain holds 199 strikes.
--
-- APPLY ORDER: Section 1 -> 2 -> 3, verify with Section 4.
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS (TD-S81-NEW-5: a body-only file
-- is not a rebuild source).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_dex_standing_book
WITH (security_invoker = false) AS
WITH RECURSIVE syms AS (
        -- Loose index scan: symbol is the leading column of
        -- idx_ocs_symbol_expiry_strike_type, so min(symbol) and
        -- min(symbol) WHERE symbol > s are index seeks. Symbols are
        -- DERIVED, never a literal list (TD-S72-NEW-3).
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c) AS symbol
        UNION ALL
        SELECT (SELECT min(c.symbol)
                  FROM public.option_chain_snapshots c
                 WHERE c.symbol > s.symbol)
          FROM syms s
         WHERE s.symbol IS NOT NULL
     ), back AS (
        -- Step back one IST date at a time from the newest run: one
        -- backward index seek per step. max(ts) WHERE symbol = s is
        -- served by idx_ocs_ts_symbol_expiry (ts DESC, symbol, ...) --
        -- the planner rewrites it to ORDER BY ts DESC LIMIT 1 and the
        -- symbol filter is checked IN the index, so it stops at the
        -- first match. NEVER created_at: the ingest reuses one
        -- snapshot_ts per cycle but created_at is a DB-side default and
        -- is later for the extra-expiry pass, so ordering by it hands
        -- back W2 (research.md; S81 89bc83e).
        -- 5 steps: enough for a long weekend plus a holiday cluster.
        SELECT s.symbol, 1 AS step_n,
               (SELECT (max(c.ts) AT TIME ZONE 'Asia/Kolkata')::date
                  FROM public.option_chain_snapshots c
                 WHERE c.symbol = s.symbol) AS d
          FROM syms s
         WHERE s.symbol IS NOT NULL
        UNION ALL
        SELECT b.symbol, b.step_n + 1,
               (SELECT (max(c.ts) AT TIME ZONE 'Asia/Kolkata')::date
                  FROM public.option_chain_snapshots c
                 WHERE c.symbol = b.symbol
                   AND c.ts < (b.d::timestamp AT TIME ZONE 'Asia/Kolkata'))
          FROM back b
         WHERE b.step_n < 5 AND b.d IS NOT NULL
     ), candidates AS (
        -- Clause 1. An EXPLICIT closure drops the date; a missing row
        -- does not (ADR-020).
        SELECT DISTINCT b.symbol, b.d AS session_date
          FROM back b
         WHERE b.d IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM public.trading_calendar tc
                            WHERE tc.trade_date = b.d AND tc.is_open = false)
     ), live AS MATERIALIZED (
        -- Clause 2, the house liveness rule (ADR-030 / ENH-133 3.6).
        -- Dates that did not move drop out HERE, BEFORE ranking, so a
        -- frozen day cannot use up the slot a real session needs -- the
        -- same ordering v_gex_strike_terrain had to adopt when a
        -- 15:40-only holiday took a ranking slot.
        SELECT c.symbol, c.session_date
          FROM candidates c
         WHERE (SELECT count(DISTINCT m.spot)
                  FROM public.market_spot_snapshots m
                 WHERE m.symbol = c.symbol
                   AND m.ts >= (c.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                   AND m.ts <= ((c.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
               ) > 1
     ), sess AS MATERIALIZED (
        SELECT x.symbol, x.session_date
          FROM (SELECT l.*,
                       row_number() OVER (PARTITION BY l.symbol
                                          ORDER BY l.session_date DESC) AS rn
                  FROM live l) x
         WHERE x.rn = 1
     ), legs AS MATERIALIZED (
        -- LATERAL, not a plain join. As a plain join the planner hashed
        -- sess and scanned 3.2M index entries, removing 3,113,638 rows
        -- by join filter -- MEASURED 8,095 ms. As a LATERAL the ts
        -- window is a parameterised index range: 61 ms. This is the
        -- ADR-021 shape and it was found by measuring, not by reading.
        SELECT sx.symbol, sx.session_date, e.expiry_date,
               row_number() OVER (PARTITION BY sx.symbol
                                  ORDER BY e.expiry_date) AS leg_n
          FROM sess sx
          CROSS JOIN LATERAL (
               SELECT DISTINCT c.expiry_date
                 FROM public.option_chain_snapshots c
                WHERE c.symbol = sx.symbol
                  AND c.ts >= (sx.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                  AND c.ts <= ((sx.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
                  -- a past expiry is never written by the ingest; the
                  -- guard is here so a backfill cannot introduce one as
                  -- a phantom front leg
                  AND c.expiry_date >= sx.session_date
          ) e
     ), settled AS MATERIALIZED (
        -- Per LEG, independently: the brief's grain is (symbol,
        -- expiry_date). In practice both legs share one snapshot_ts
        -- (measured 2026-10-08, both symbols) because the ingest
        -- computes it once per symbol pass, but a leg captured in a
        -- separate pass is then scoped to ITS OWN settled run rather
        -- than silently inheriting the other leg's.
        SELECT l.symbol, l.session_date, l.expiry_date, l.leg_n,
               r.ts AS settled_ts, r.run_id
          FROM legs l
          CROSS JOIN LATERAL (
               SELECT c.ts, c.run_id
                 FROM public.option_chain_snapshots c
                WHERE c.symbol = l.symbol
                  AND c.expiry_date = l.expiry_date
                  AND c.ts >= (l.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                  AND c.ts <= ((l.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
                ORDER BY c.ts DESC
                LIMIT 1
          ) r
     ), px AS (
        -- ts equality + symbol + expiry_date is an exact three-column
        -- seek on idx_ocs_ts_symbol_expiry. ~431 rows per leg.
        SELECT st.symbol, st.session_date, st.leg_n, st.expiry_date,
               st.settled_ts, st.run_id,
               c.strike, c.option_type, c.oi, c.delta, c.iv, c.spot
          FROM settled st
          JOIN public.option_chain_snapshots c
            ON c.symbol = st.symbol
           AND c.expiry_date = st.expiry_date
           AND c.ts = st.settled_ts
     ), k AS (
        -- One CE and one PE row per strike per leg, so the FILTER
        -- aggregates are a pivot, not a reduction. The gap marker is
        -- "delta IS NULL OR (delta = 0 AND COALESCE(iv, 0) = 0)" -- see
        -- the header: a zero delta beside a LIVE iv is read as a true
        -- zero, which is the safe degradation if the vendor ever emits
        -- one. COALESCE on iv because iv is nullable too, and a NULL iv
        -- beside a zero delta is a GAP, not a live iv -- bare "iv = 0"
        -- is NULL there, so the bool_or would read false and publish a
        -- fabricated 0 exposure. This matches the Python recompute,
        -- which coerces a missing iv to 0.0 before the same test.
        SELECT p.symbol, p.session_date, p.leg_n, p.expiry_date,
               p.settled_ts, p.run_id, p.strike,
               max(p.spot)                                      AS spot,
               max(p.oi)    FILTER (WHERE p.option_type = 'CE')  AS oi_call,
               max(p.oi)    FILTER (WHERE p.option_type = 'PE')  AS oi_put,
               max(p.delta) FILTER (WHERE p.option_type = 'CE')  AS delta_call,
               min(p.delta) FILTER (WHERE p.option_type = 'PE')  AS delta_put,
               bool_or(p.option_type = 'CE'
                       AND (p.delta IS NULL
                            OR (p.delta = 0 AND COALESCE(p.iv, 0) = 0)))
                                                                 AS call_gap,
               bool_or(p.option_type = 'PE'
                       AND (p.delta IS NULL
                            OR (p.delta = 0 AND COALESCE(p.iv, 0) = 0)))
                                                                 AS put_gap
          FROM px p
         GROUP BY p.symbol, p.session_date, p.leg_n, p.expiry_date,
                  p.settled_ts, p.run_id, p.strike
     ), dex AS (
        -- delta x oi x spot / 1e7. ONE power of spot (GEX uses two) and
        -- NO PE sign flip (delta supplies its own). oi is a QUANTITY --
        -- contracts x lot, lot already inside it -- so no multiplier:
        -- measured 100 % divisibility at 20 (SENSEX) and 65 (NIFTY),
        -- min positive oi equal to the lot, corroborated by
        -- public.instruments.lot_size and by ADR-014 2.3's S75
        -- correction ("Dhan reports oi already lot-multiplied").
        -- Order of the CASE arms matters: no OI is tested BEFORE the
        -- gap, so a strike with neither OI nor greeks reads 0 (a true
        -- zero) rather than NULL (a gap that is not there).
        SELECT k.*,
               CASE WHEN COALESCE(k.oi_call, 0) = 0 THEN 0
                    WHEN k.call_gap                 THEN NULL
                    ELSE k.delta_call * k.oi_call * k.spot / 1e7
               END                                              AS call_dex_cr,
               CASE WHEN COALESCE(k.oi_put, 0) = 0  THEN 0
                    WHEN k.put_gap                  THEN NULL
                    ELSE k.delta_put * k.oi_put * k.spot / 1e7
               END                                              AS put_dex_cr,
               CASE WHEN k.call_gap THEN COALESCE(k.oi_call, 0) ELSE 0 END
                                                                AS oi_call_no_delta,
               CASE WHEN k.put_gap  THEN COALESCE(k.oi_put , 0) ELSE 0 END
                                                                AS oi_put_no_delta
          FROM k
     ), agg AS (
        -- The leg totals are each side's MEASURED contribution -- its
        -- number where it exists, 0 where it does not. They are the
        -- measured PART of the leg, and leg_gap_oi_qty is the OI they do
        -- not cover; they are not a complete total and must not be read
        -- as one. That is also why they are NOT net_dex_cr, which
        -- NULL-propagates on purpose.
        -- NO cum_net_dex_cr: its only consumer was the cumulative
        -- zero-delta candidate, which was measured degenerate and
        -- withdrawn. A running sum over COALESCE(.., 0) walks past gap
        -- strikes as if they were zero and carries no flag saying it
        -- did, so publishing one would assert a curve that was never
        -- measured. If S* or any successor needs a cumulative, it is
        -- added with its own gap disclosure at that point.
        SELECT d.*,
               sum(COALESCE(d.call_dex_cr, 0)) OVER wleg         AS leg_call_dex_cr,
               sum(COALESCE(d.put_dex_cr , 0)) OVER wleg         AS leg_put_dex_cr,
               sum(COALESCE(d.call_dex_cr, 0) + COALESCE(d.put_dex_cr, 0))
                 OVER wleg                                      AS leg_net_dex_cr,
               sum(COALESCE(d.oi_call, 0) + COALESCE(d.oi_put, 0))
                 OVER wleg                                      AS leg_oi_qty,
               sum(d.oi_call_no_delta + d.oi_put_no_delta)
                 OVER wleg                                      AS leg_gap_oi_qty,
               count(*) FILTER (WHERE d.call_dex_cr IS NULL OR d.put_dex_cr IS NULL)
                 OVER wleg                                      AS leg_n_gap_strikes
          FROM dex d
        WINDOW wleg AS (PARTITION BY d.symbol, d.expiry_date)
     )
SELECT a.symbol,
       a.session_date,
       a.leg_n::int                              AS leg_n,
       a.expiry_date,
       (a.expiry_date - a.session_date)::int      AS dte,
       a.run_id,
       a.settled_ts,
       a.spot,
       a.strike,
       a.delta_call,
       a.delta_put,
       a.oi_call,
       a.oi_put,
       a.call_dex_cr,
       a.put_dex_cr,
       -- NULL when either side is unknown: an unknown cannot be netted.
       CASE WHEN a.call_dex_cr IS NULL OR a.put_dex_cr IS NULL THEN NULL
            ELSE a.call_dex_cr + a.put_dex_cr
       END                                        AS net_dex_cr,
       a.oi_call_no_delta,
       a.oi_put_no_delta,
       a.leg_call_dex_cr,
       a.leg_put_dex_cr,
       a.leg_net_dex_cr,
       a.leg_oi_qty,
       a.leg_gap_oi_qty,
       a.leg_n_gap_strikes::int                   AS leg_n_gap_strikes
  FROM agg a;


-- =====================================================================
-- SECTION 2 of 4 -- COMMENT (LIVE statement -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_dex_standing_book IS
  'S93 / ENH-140 -- P6 of the S92-I post-parity track. The DEX standing book: the delta exposure standing in the open interest, per strike, in Rs crore. NOT a parity layer (ADR-025 closed, Amendment D); display-only per S37. Grain (symbol, expiry_date, strike). Consumers MUST ORDER BY symbol, expiry_date, strike -- a view body carries no ordering guarantee -- and filter leg_n = 1 for the front leg. NO DEALER COLUMN AND NO DEALER CLAIM. call_dex_cr, put_dex_cr and net_dex_cr are signed by each option OWN delta, so they are the OPEN INTEREST delta. ADR-014 section 2.3, which ADR-015 says it carries unchanged, reads positive gex_cr as DEALER LONG with calls the positive term -- calls dealer-long, puts dealer-short -- while ADR-015 own gloss says the convention coincides with dealers short calls and long puts, the exact inverse on both legs. The code is not in doubt; the English in ADR-015 is inverted. The two readings give dealer delta = call_dex_cr - put_dex_cr and dealer delta = -net_dex_cr respectively, which on NIFTY W1 2026-10-08 are +129,272.61 and +11,878.01 Cr -- the same sign on that leg but an order of magnitude apart. They differ in SIGN whenever net_dex_cr is above zero, which was NOT observed on the four legs measured (all four were below zero, so both readings came out positive); four legs of one run says nothing about how often that holds. Choosing between them is P2 (S92-I item 2). NOTHING HERE ASSERTS THAT ANY DEALER NUMBER IS -net_dex_cr. Every surface rendering these columns reads "open-interest delta -- dealer side unruled (P2)". FORMULA delta x oi x spot / 1e7: ONE power of spot where gex_cr uses two, and NO PE sign flip, because delta already carries its own sign (PE delta is stored negative, measured min -0.99341) whereas vendor gamma is positive on both sides and gex_cr must negate PE explicitly. Copying that flip would double the negation and destroy the netting. oi is a QUANTITY, contracts times lot with the lot already inside it, so there is no multiplier: measured 100 pct divisibility at 20 for SENSEX and 65 for NIFTY with min positive oi equal to the lot, corroborated by public.instruments.lot_size and by ADR-014 section 2.3 S75 correction. SESSION IS DECIDED HERE, NOT BY THE CONSUMER. Stepping back up to 5 dates from the newest chain run, a date is a session only if trading_calendar holds no explicit is_open = false row for it AND the tape moved -- count(DISTINCT spot) greater than 1 over market_spot_snapshots for that symbol and date to 15:15 IST, the house liveness rule of ADR-030 / ENH-133 section 3.6. The liveness clause is what catches 2026-10-02: 77 frozen chain cycles, about 143k rows, and no trading_calendar row at all (TD-S92-NEW-5), so a consumer-side calendar gate would have drawn a holiday frozen book as the standing book. Measured 10-02 reads 1 tick and distinct_spot 1 on both symbols against 360 and 349 / 359 on 10-08. market_spot_snapshots rather than the chain own spot because the chain spot is in no index and that form measured 899 ms per symbol-day against 0.578 ms; they are the same event and check 4f asserts they agree. A missing calendar row is still not a verdict (ADR-020). SETTLED RUN is the last run at or before 15:15 IST of the session, per (symbol, expiry_date) -- the ENH-126 river rule, because after 15:15 the index is auction-frozen (ADR-022). Mid-session the settled run IS the latest run; after 15:15 it holds at the 15:10 cycle. run_id is per (symbol, ts, expiry_date) and NOT per cycle: at one ts the chain carries a different run_id per leg, and gex_strike_snapshots holds the W1 leg only, so W2 run is not discoverable from it. NULL IS A GAP, NEVER A ZERO. A side with OI and no delta publishes NULL; a side with no OI publishes 0, a true zero; net_dex_cr is NULL when either side is NULL. The vendor drops the whole greeks block together -- over the 2026-10-08 session, 55,228 positive-OI rows, every delta = 0 row also carries gamma = 0 and iv = 0 (2,321 of 2,321 NIFTY, 7,053 of 7,053 SENSEX), with zero rows at delta = 0 with iv above 0 -- so the marker is delta IS NULL OR (delta = 0 AND COALESCE(iv, 0) = 0), and a zero delta beside a live iv would be read as a true zero. iv is nullable too, which is why the marker coalesces it: a NULL iv beside a zero delta is a GAP, and a bare iv = 0 is NULL there and would publish a fabricated zero exposure. The gap is ITM-concentrated and put-asymmetric: at the SENSEX settled run the ITM subset is 3 CE rows carrying 4,100 units against 51 PE rows carrying 7,722,860 units, and an ITM option cannot have zero delta. Un-deltaed OI rides in oi_call_no_delta and oi_put_no_delta. BECAUSE net_dex_cr NULL-PROPAGATES, sum(net_dex_cr) does not equal sum(call_dex_cr) + sum(put_dex_cr) -- measured on the 2026-10-09 13:20 IST run, NIFTY W1, 103,096.29 minus 107,932.77 is -4,836.48 against a sum(net_dex_cr) of -3,446.47, a 1,390.01 Cr discrepancy that is exactly the good half of the one-sided-gap strikes. THAT IS WHY THE LEG TOTALS ARE COLUMNS: leg_call_dex_cr, leg_put_dex_cr and leg_net_dex_cr are window sums over each side MEASURED contribution, so the client never sums and never computes the wrong total (S92-G, one rule one implementation in the database). THEY ARE THE MEASURED PART OF THE LEG, NOT A COMPLETE TOTAL: leg_gap_oi_qty is the OI they do not cover, leg_oi_qty is the leg total OI, and the leg total is read together with those or not at all. THERE IS NO cum_net_dex_cr: its only consumer was the cumulative zero-delta candidate, which was measured degenerate and withdrawn, and a running sum over COALESCE(.., 0) walks past gap strikes as if they were zero while carrying no flag that it did. THE MAGNITUDE IS INDICATIVE, NOT MEASURED, AND NO GATE IS BUILT ON IT. net_dex is a difference of nearly-cancelling terms: measured absolute net over gross is 9.2 pct NIFTY W1, 21.4 pct SENSEX W1. Put-call delta parity fails in the vendor data -- delta_CE minus delta_PE measured 0.577 to 1.281 with a mean of 0.816 to 0.882 against a theoretical 1, outside a 0.998 to 1.002 band on essentially every strike -- so a parity gate is recorded as MIS-SPECIFIED FOR THIS DATA AND DROPPED, never widened until it passes (S83). Substituting the parity-implied put delta moves net_dex by 1.6 to 2.9 times on the same run, sign unchanged on all four legs; four legs of one run is not a measurement of sign stability. Whether the book should read the vendor delta or an in-house Black-Scholes delta is an OPEN OPERATOR RULING. NO ZERO-DELTA COLUMN. The two candidates briefed for P6 were measured and withdrawn: the cumulative has no zero crossing on any of four legs under either of two delta sets, and nearest-strike-to-zero lands on the chain lowest strike where net is zero because there is no OI. Their replacement, S* the RE-PRICED zero-delta level where the sum of delta_i(S*) times OI_i is zero, is specified to reuse the ENH-131 v_gex_repriced_flip code path with gamma replaced by delta and is PENDING OPERATOR RULING -- an absent column, not a provisional one. ROW COUNT 862 measured across both symbols and both legs on 2026-10-09, under the PostgREST 1,000-row cap (rule 15) but not by much; filter leg_n = 1 or page with range. Zero-OI strikes are kept so the book shares one strike axis with the chain, which is why it carries more strikes than gex_strike_snapshots. Runs with the owner privileges (security_invoker = false); adding a column here publishes it to anon. Design note docs/research/s93_priority/p6/P6_dex_design_note.md carries every measurement with its probe SQL. Never label second-order terms vanna or charm (L78-1).';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE statements)
-- REVOKE FIRST, then GRANT. Supabase DEFAULT PRIVILEGES hand new objects
-- ALL (CASE-2026-09-22); the REVOKE is what prevents that, not
-- belt-and-braces. authenticated is revoked too -- the S92 views left it
-- with ALL (TD-S92-NEW-4) and this one does not repeat that.
-- Target ACL: anon=r, merdian_ro=r -- SELECT alone.
-- =====================================================================

REVOKE ALL ON public.v_dex_standing_book FROM anon, authenticated;

GRANT SELECT ON public.v_dex_standing_book TO anon;

GRANT SELECT ON public.v_dex_standing_book TO merdian_ro;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run after 1-3; run each block ALONE)
-- Each states what makes it fail. A check that cannot fail for the
-- reason it names is documentation, not verification (CLAUDE.md rule 0).
-- =====================================================================

-- 4a  ANON PATH and GRAIN, in ONE execution, with the acting role in the
--     same result set (S84 D.40.1: the SQL editor opens a new session per
--     run, so a SET ROLE in one run does not survive into the next).
--     FAILS IF: role_now is not anon; n_rows is 0 for either symbol;
--     n_sessions <> 1 per symbol; n_legs is not 2 (or 1 on a day the
--     ingest captured one leg); any duplicate (expiry_date, strike);
--     or n_offday > 0, which would mean the settled-ts range admitted a
--     neighbouring day.
--     EXPECTED: role_now = anon, 2 symbols, n_sessions = 1,
--     n_legs = 2, n_dupes = 0, n_offday = 0, n_rows ~ 400-480 per leg.
-- BEGIN;
--   SET LOCAL ROLE anon;
--   SELECT current_user                                   AS role_now,
--          symbol,
--          count(*)                                       AS n_rows,
--          count(DISTINCT session_date)                    AS n_sessions,
--          count(DISTINCT expiry_date)                     AS n_legs,
--          count(*) - count(DISTINCT (expiry_date, strike)) AS n_dupes,
--          count(*) FILTER (WHERE (settled_ts AT TIME ZONE 'Asia/Kolkata')::date
--                                   <> session_date)       AS n_offday,
--          min(session_date) AS session_date, max(settled_ts) AS settled_ts
--     FROM public.v_dex_standing_book
--    GROUP BY symbol ORDER BY symbol;
-- COMMIT;

-- 4b  COST (ADR-021: the whole point of run scoping). Read two things:
--     execution time, and that the legs/settled laterals show
--     loops = the number of legs rather than one loop per output row.
--     FAILS IF: execution exceeds 3,000 ms -- anon's statement_timeout
--     is 3 s (MV-6), the ceiling that actually binds this consumer, not
--     PostgREST's 8 s -- or a Seq Scan appears on
--     option_chain_snapshots (3.2M+ rows; a seq scan here is never
--     right), or the legs lateral's loops exceed the symbol count.
--     MEASURED on THIS body, verbatim, as a plain SELECT through
--     bin/roq.sh (2026-10-09, 862 rows out every time):
--       COLD (first run after a re-plan; market_spot_snapshots and the
--             back-steps read from disk):  1,322.7 / 1,445.0 / 1,934.3 ms
--                                          (three cold runs)
--       WARM (nine runs):                  81.6 - 103.4 ms
--     Both are stated because both are real: the warm number is what a
--     5-minute-cadence board read normally sees, the cold number is what
--     the first read after a cache eviction sees, and it is the cold one
--     that has to clear the 3 s ceiling.
--     IT CLEARS IT BY 1.55x AT THE WORST COLD RUN MEASURED, NOT 2x --
--     and the cold figure is the variable one (1.3 s to 1.9 s across
--     three runs), so that margin is the thing to watch as the chain
--     grows, never the warm number. If a cold run is ever seen above
--     ~2.4 s, the liveness clause is the first thing to move off the hot
--     path (it is the only part that touches a second relation).
--     Node detail, warm: CTE live 4.8 ms (10 candidate dates, 0.44 ms
--     each); CTE back 0.26 ms for 10 backward seeks; legs lateral
--     loops = 2; px seek loops = 4 at 431 rows each.
--     The FIRST DRAFT of the legs CTE was a plain join and measured
--     8,095 ms (3.2M index entries scanned, 3,113,638 rows removed by
--     join filter); the LATERAL rewrite took it to 61 ms. That is the
--     ADR-021 shape, and it was found by measuring, not by reading --
--     the plain-join form would have shipped, worked at today's table
--     size, and crossed the ceiling silently later.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_dex_standing_book;

-- 4c  THE SCALE AND SIGN ANCHOR -- an INDEPENDENT recompute, in SQL,
--     with different algebra from the view (a direct aggregate over the
--     chain, no pivot, no window functions). This is the check that
--     catches a wrong /1e7, a wrong power of spot, or the doubled PE
--     flip. FAILS IF: max_abs_diff exceeds 1e-6 Cr on either side, or
--     n_strike_mismatch > 0.
--     EXPECTED: 0 and 0 on both symbols and both legs.
-- WITH v AS (
--   SELECT symbol, expiry_date, strike, settled_ts,
--          call_dex_cr, put_dex_cr
--     FROM public.v_dex_standing_book
-- ), r AS (
--   SELECT c.symbol, c.expiry_date, c.strike,
--          sum(CASE WHEN c.option_type = 'CE'
--                    AND c.oi > 0
--                    AND NOT (c.delta IS NULL OR (c.delta = 0 AND c.iv = 0))
--                   THEN c.delta * c.oi * c.spot / 1e7 END)  AS call_recon,
--          sum(CASE WHEN c.option_type = 'PE'
--                    AND c.oi > 0
--                    AND NOT (c.delta IS NULL OR (c.delta = 0 AND c.iv = 0))
--                   THEN c.delta * c.oi * c.spot / 1e7 END)  AS put_recon
--     FROM public.option_chain_snapshots c
--     JOIN (SELECT DISTINCT symbol, expiry_date, settled_ts
--             FROM public.v_dex_standing_book) s
--       ON s.symbol = c.symbol AND s.expiry_date = c.expiry_date
--      AND c.ts = s.settled_ts
--    GROUP BY c.symbol, c.expiry_date, c.strike
-- )
-- SELECT v.symbol, v.expiry_date,
--        count(*)                                                     AS strikes,
--        count(*) FILTER (WHERE r.strike IS NULL)                      AS n_strike_mismatch,
--        max(abs(COALESCE(v.call_dex_cr,0) - COALESCE(r.call_recon,0))) AS max_abs_diff_call,
--        max(abs(COALESCE(v.put_dex_cr ,0) - COALESCE(r.put_recon ,0))) AS max_abs_diff_put,
--        -- the sign assertion, stated as a count so it cannot pass vacuously
--        count(*) FILTER (WHERE v.put_dex_cr  > 0)                     AS n_put_dex_positive,
--        count(*) FILTER (WHERE v.call_dex_cr < 0)                     AS n_call_dex_negative
--   FROM v LEFT JOIN r
--     ON r.symbol = v.symbol AND r.expiry_date = v.expiry_date AND r.strike = v.strike
--  GROUP BY v.symbol, v.expiry_date ORDER BY v.symbol, v.expiry_date;
--     n_put_dex_positive and n_call_dex_negative MUST both be 0. If
--     n_put_dex_positive equals the put strike count, the PE flip was
--     copied from GEX and the negation is doubled.

-- 4d  THE GAP IS A GAP (NULL is never rendered as 0), the leg totals are
--     internally consistent, and the gap OI they do NOT cover is
--     reported beside them.
--     FAILS IF: n_zero_where_gap_c or _p > 0 (a gap published as 0); or
--     gap_oi_unaccounted <> 0 (the leg's gap OI does not equal the sum
--     of the per-strike gap OI); or leg_net_dex_cr differs from
--     leg_call_dex_cr + leg_put_dex_cr by more than 1e-6.
--     EXPECTED: n_zero_where_gap_c = 0, n_zero_where_gap_p = 0,
--     gap_oi_unaccounted = 0, leg_total_mismatch = 0.
--     ALSO EXPECTED, and NOT a failure: sum_net_dex <> leg_net_dex_cr
--     whenever n_gap_strikes > 0 -- the 1,390.01 Cr NIFTY W1 case. The
--     columns report it so the discrepancy is visible rather than
--     discovered, and leg_gap_oi_qty says how much OI the leg totals
--     leave out. Read the two together; the leg total alone is the
--     measured PART of the leg, not a complete total.
-- SELECT symbol, expiry_date,
--        max(leg_n_gap_strikes)                                  AS n_gap_strikes,
--        count(*) FILTER (WHERE oi_call_no_delta > 0 AND call_dex_cr = 0)  AS n_zero_where_gap_c,
--        count(*) FILTER (WHERE oi_put_no_delta  > 0 AND put_dex_cr  = 0)  AS n_zero_where_gap_p,
--        max(leg_gap_oi_qty) - sum(oi_call_no_delta + oi_put_no_delta)     AS gap_oi_unaccounted,
--        max(abs(leg_net_dex_cr - (leg_call_dex_cr + leg_put_dex_cr)))     AS leg_total_mismatch,
--        sum(net_dex_cr)                                                   AS sum_net_dex,
--        max(leg_net_dex_cr)                                               AS leg_net_dex_cr,
--        max(leg_gap_oi_qty)                                               AS leg_gap_oi_qty,
--        max(leg_oi_qty)                                                   AS leg_oi_qty
--   FROM public.v_dex_standing_book
--  GROUP BY symbol, expiry_date ORDER BY symbol, expiry_date;

-- 4e  WITHDRAWN. It asserted that cum_net_dex_cr ends at the leg total.
--     That column no longer exists: its only consumer was the cumulative
--     zero-delta candidate, which was measured degenerate (no crossing
--     on any of 4 legs) and withdrawn, and a running sum over
--     COALESCE(.., 0) walks past gap strikes as if they were zero
--     without saying so. Nothing replaces it. The check number is left
--     in place so 4f..4i keep their identities in every citation.

-- 4f  THE LIVENESS CLAUSE AGREES WITH THE CHAIN. The view gates on
--     market_spot_snapshots for cost (0.578 ms vs 899 ms per
--     symbol-day); this asserts the chain's OWN spot moved on the
--     session that was selected, so "they are the same event" is a test
--     and not a comment. Run OUT OF HOURS: it is the 899 ms form.
--     FAILS IF: chain_distinct_spot = 1 for a selected session -- which
--     is the 2026-10-02 signature and would mean a frozen day was
--     selected after all.
--     EXPECTED: chain_distinct_spot > 1 on every row (measured 75 / 76
--     on 2026-10-08).
-- SELECT s.symbol, s.session_date,
--        (SELECT count(DISTINCT c.spot)
--           FROM public.option_chain_snapshots c
--          WHERE c.symbol = s.symbol
--            AND c.ts >= (s.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
--            AND c.ts <= ((s.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
--        ) AS chain_distinct_spot,
--        (SELECT count(DISTINCT m.spot)
--           FROM public.market_spot_snapshots m
--          WHERE m.symbol = s.symbol
--            AND m.ts >= (s.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
--            AND m.ts <= ((s.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
--        ) AS tape_distinct_spot
--   FROM (SELECT DISTINCT symbol, session_date
--           FROM public.v_dex_standing_book) s
--  ORDER BY s.symbol;

-- 4g  THE COMMENT ACTUALLY LANDED (a part-run apply is the S79 failure
--     mode: body applied, COMMENT and GRANT skipped -- TD-S81-NEW-5).
--     FAILS IF: comment_len is NULL, or differs from the file literal.
--     EXPECTED, COMPUTED FROM THIS FILE'S LITERAL before any apply and
--     never read back off the database (S81):
--       comment_len = 7614
--       comment_md5 = 634428a33305107247c43910c3729669
--     If the literal is edited before the apply, RECOMPUTE from the file.
-- SELECT c.relname,
--        length(obj_description(c.oid,'pg_class')) AS comment_len,
--        md5(obj_description(c.oid,'pg_class'))    AS comment_md5
--   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND c.relname = 'v_dex_standing_book';

-- 4h  ACL and invoker mode. FAILS IF: relacl carries anything for anon
--     beyond r, carries an authenticated entry at all, or reloptions
--     does not show security_invoker=false.
--     EXPECTED: relacl contains anon=r/postgres and merdian_ro=r/postgres
--     and NO authenticated entry; reloptions = {security_invoker=false}.
-- SELECT c.relacl, c.reloptions
--   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public' AND c.relname = 'v_dex_standing_book';

-- 4i  THE OFFLINE EXPECTED TABLE, and THE CHECK THAT CATCHES A DOUBLED
--     PE FLIP IN THIS SQL. tests/test_dex_recompute.py recomputes DEX in
--     Python from the frozen golden day, independently of this file, and
--     writes
--       docs/research/s93_priority/p6/expected/dex_standing_book_1001_SENSEX.csv
--     (NOT into tests/golden/2026-10-01_SENSEX/, which is frozen --
--     R2.1, MANIFEST.sha256). The expected values are computed offline
--     and never read back off the view (S81).
--     The golden day is 2026-10-01 and this view is scoped to the newest
--     session, so the comparison is NOT a query against the view for a
--     historical date. It is run by exporting this view's output AND the
--     chain rows for the same run_ids, then diffing:
--
--       bash bin/roq.sh <<'SQL' > /tmp/dex_view.csv
--       \pset format csv
--       SELECT symbol, expiry_date, strike, call_dex_cr, put_dex_cr,
--              net_dex_cr, run_id
--         FROM public.v_dex_standing_book
--        ORDER BY symbol, expiry_date, strike;
--       SQL
--       -- then, with the run_ids that returned:
--       bash bin/roq.sh <<'SQL' > /tmp/dex_chain.csv
--       \pset format csv
--       SELECT symbol, expiry_date, strike, option_type, oi, delta, iv,
--              spot, run_id
--         FROM public.option_chain_snapshots
--        WHERE run_id IN ('<...>');
--       SQL
--       python3 tests/test_dex_recompute.py --compare \
--         --view /tmp/dex_view.csv --chain /tmp/dex_chain.csv
--
--     FAILS IF: any strike's call_dex_cr, put_dex_cr or net_dex_cr
--     differs by more than 1e-6 Cr; a value is NULL on one side and a
--     number on the other; either side holds a strike the other does
--     not; or the two exports cover different run_ids -- which means a
--     new run landed between the reads and is the S81 false-alarm shape,
--     not a defect. Re-export both together in that case.
--     EXERCISED 2026-10-09 on synthetic inputs, four arms: agreeing
--     (PASS, 2 strikes, 0.000e+00 Cr), a doubled PE flip (CAUGHT,
--     put_dex_cr off by 1.440e+03 Cr), a gap published as 0 instead of
--     NULL (CAUGHT, NULL-ness differs), and a run_id drift between the
--     two exports (CAUGHT). So the check can fail for each reason it
--     names.
--     This is the check that proves the SQL and an independent Python
--     implementation agree. The offline test's own A3/A4 assert the
--     PYTHON side only; nothing offline can speak for this file.

-- =====================================================================
-- NOT INCLUDED, DELIBERATELY
--   * NO dealer column. Section 3.2 of the design note: the two
--     readings differ in sign and size and P2 rules. A column named
--     dealer_* would settle by construction what is not settled.
--   * NO zero-delta column. Both briefed candidates measured
--     degenerate; S* is specified and pending ruling.
--   * NO history. One session, like every sibling read surface. A
--     DEX time series needs its own ruling on a read surface.
--   * NO second-order terms, and no column named vanna or charm
--     (L78-1). Those are P7's.
--   * NO change to option_chain_snapshots' ACL. It already carries
--     anon=rm (R01-F8 / TD-S81-NEW-2); this file neither widens it nor
--     depends on it.
-- =====================================================================
