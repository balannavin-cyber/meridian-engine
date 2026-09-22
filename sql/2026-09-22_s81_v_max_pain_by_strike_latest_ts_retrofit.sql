-- =====================================================================
-- 2026-09-22_s81_v_max_pain_by_strike_latest_ts_retrofit.sql
-- S81 -- latest_ts retrofit: full-index scan -> skip-scan + lateral
--
-- SUPERSEDES 2026-09-22_s81_v_max_pain_by_strike_expiry_filter.sql.
-- ONE CTE CHANGES. Everything else in that file is carried byte-identical
-- and the header below is its header, amended only where latest_ts is
-- described. Read the two as a pair: the expiry fix is WHY the view looks
-- like this, and this file is WHY it is fast.
-- =====================================================================
--
-- SUPERSEDES the captured baseline in
--   sql/2026-09-22_s81_v_max_pain_by_strike_CAPTURED_BASELINE.sql
-- which is the pre-change body, committed verbatim so this lands as a
-- reviewable diff rather than an assertion. No DDL for this object
-- existed in the repository before S81; the S40 register footer naming
-- sql/v_max_pain_by_strike.sql is false and git has no history for it.
--
-- WHAT CHANGES
--   1. EXPIRY FILTER (the fix). The baseline grouped by (symbol, strike)
--      with no expiry in the grain, so two expiries in one snapshot
--      collapse into a per-strike max() MIXTURE of two contracts. Not
--      firing today -- one expiry per cycle across 2,923 cycles -- and
--      armed the moment TD-S80-NEW-1 raises ingest depth. Fixed BEFORE
--      that, so the ladder lands in a table that already scopes.
--   2. ts, expiry_date, dte, n_strikes emitted.
--   3. ADR-023 recency floor surfaced: snapshot_age_min,
--      stale_floor_min_used, is_fresh.
--   4. anon grants corrected (see below).
--
-- HOW INERTNESS IS ESTABLISHED -- Section 4b, and it is a real check.
--   4b runs the CAPTURED BASELINE body and this view inside ONE statement
--   and takes EXCEPT in both directions. One statement matters: both
--   sides then derive latest_ts from the same transaction snapshot, so a
--   mid-comparison ingest cycle cannot manufacture a difference. Expect
--   old_minus_new = 0 and new_minus_old = 0, with equal per-symbol row
--   counts. Anything non-zero means the filter is not inert, which is
--   exactly what the check must be able to show.
--
--   An earlier draft compared against a reading taken through the anon
--   path at 09:18 UTC -- NIFTY 236 rows / max_pain 23350, SENSEX 196 /
--   74700. That comparison CANNOT FIRE CORRECTLY and was replaced: the
--   baseline emits no ts, ingest writes a new snapshot every ~5 minutes
--   until 15:40 IST, so the two sides would read different snapshots and
--   a mismatch would prove nothing. Those numbers survive here as
--   CONTEXT ONLY. (The same trap is recorded as an S81 method note: on a
--   latest-scoped view, counts are comparable only when ts matches.)
--
--   WHAT 4b DOES NOT PROVE. It establishes NO REGRESSION on data where
--   one expiry per cycle holds. It cannot exercise the multi-expiry path,
--   which is the only condition the filter exists for and is unobservable
--   until ingest depth rises. That test is OWNED BY TD-S80-NEW-1 STAGE 1:
--   on the first stage-1 day carrying two expiries, (a) compare this
--   view against the same computation restricted by hand to W1 -- expect
--   identical rows -- and (b) run the captured baseline body against that
--   same snapshot -- expect it to DIFFER. (b) is the load-bearing half:
--   without it, (a) passes even if the filter does nothing.
--
-- WHAT DOES NOT CHANGE, AND WHY
--   * latest_ts IS THE ONE THING THAT CHANGES in this file. Everything
--     else -- front_expiry, chain, cohort, strikes, pain, max_pain, all
--     twelve output columns, their order, the side strings and the
--     freshness columns -- is byte-identical to the S81 expiry fix.
--   * max_pain tie-break stays NON-DETERMINISTIC. The partition widens to
--     (symbol, expiry_date), but ORDER BY remains total_pain with no
--     tie-break column, as in the baseline. ENH-123 orders by
--     (total_pain, candidate_strike). The correction is one line and was
--     OUT OF THE APPROVED SCOPE; it is reported for a TD rather than
--     changed silently in a view the frozen frontend reads.
--   * `strikes` remains a structural no-op (chain is already distinct on
--     its grain). Kept to hold the diff against the baseline small.
--
-- ts IS timestamptz -- measured via information_schema at S81, not
--   assumed. AT TIME ZONE therefore converts UTC to IST wall-clock, which
--   is the intended direction. Had it been `timestamp without time zone`
--   the conversion would run backwards and shift the >= guard by up to
--   5h30 around midnight, so this was confirmed before the file was
--   written rather than after.
--
-- BACKWARD COMPATIBILITY IS A HARD CONSTRAINT.
--   Marketview is frozen under ADR-025 Amendment B. Verified in source:
--     queries.ts:453  selects candidate_strike, total_pain,
--                     max_pain_strike, side; filters symbol; orders by
--                     candidate_strike
--     state.ts:93     reads maxPain.data[0].max_pain_strike -- a
--                     broadcast scalar, so it must stay constant per
--                     symbol
--     ui.tsx:392      branches on side === MAX_PAIN and side === PE_SIDE,
--                     everything else falling through to the CE colour
--   The five original columns keep their names, ORDER, types and
--   semantics; the seven new columns follow them. The frontend select
--   list is explicit, so added columns are simply not fetched.
--   NEVER rename or drop a column here while that page is frozen.
--
-- ANON GRANTS WERE WRONG. Measured 2026-09-22: anon held ALL SEVEN
--   privileges (SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES,
--   TRIGGER) and has_comment was false. This is the S39 Lovable
--   ALL-grants shape on an S40 object created AFTER the S39 13-surface
--   REVOKE cleanup -- so that cleanup did not hold for objects added
--   later. This object was one of 211 such relations; all were remediated
--   schema-wide the same day, together with ALTER DEFAULT PRIVILEGES so
--   the condition cannot regress. Section 3 below is the object-local
--   form of that correction and is idempotent against it.
--
--   STATE THE EXPOSURE ACCURATELY: on THIS object it was LOW. The view is
--   not auto-updatable (GROUP BY, aggregates, joins), so INSERT / UPDATE
--   / DELETE fail with a cannot-update-view error; TRUNCATE does not
--   apply to views; REFERENCES and TRIGGER require DDL, which PostgREST
--   does not issue. The grant set was wrong; on this object it was not an
--   open door. Elsewhere in the same sweep it was.
--
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS, NOT COMMENTED OUT. Run the whole
--   file, one statement at a time, so sql/ matches the database.
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_max_pain_by_strike AS
WITH RECURSIVE symbols AS (
        -- S72 FIX 2 skip scan. Symbols DERIVED, never a literal list.
        SELECT (SELECT min(o.symbol) FROM option_chain_snapshots o) AS symbol
        UNION ALL
        SELECT (SELECT min(o.symbol)
                  FROM option_chain_snapshots o
                 WHERE o.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest_ts AS (
        -- RETROFITTED S81. Was max(ts) GROUP BY symbol over the whole
        -- table: a full-index scan of 1,336,714 rows, 3,260 ms of a
        -- 3,396 ms view, on a ~4-week trajectory to the PostgREST 8 s
        -- ceiling. Now an index seek per symbol -- measured 0.288 ms,
        -- 22 shared hits, 0 reads, rows=1 per symbol with NOTHING
        -- discarded to find each match. Equivalence proven in one
        -- statement against the old aggregate: identical on both symbols.
        --
        -- KNOWN DEGRADATION MODE, accepted deliberately. The only ts DESC
        -- index is idx_ocs_ts_symbol_expiry (ts DESC, symbol,
        -- expiry_date), where symbol is the SECOND column, so this probe
        -- walks in ts order and filters on symbol. Both symbols write
        -- every cycle, so the match is the first row. If ONE symbol-s
        -- ingest stalls, its probe walks back through the other symbol-s
        -- newer entries -- about 34k index entries per stalled day,
        -- index-only, so milliseconds rather than seconds. A dedicated
        -- (symbol, ts DESC) index would remove it entirely; that is a
        -- SEPARATE decision and is deliberately not taken here.
        SELECT s.symbol, lt.ts AS max_ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = s.symbol
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), front_expiry AS (
        -- NEAREST expiry = min(expiry_date) among the latest snapshot's
        -- rows, restricted to expiries that have not already passed.
        -- min() picks the front contract; the >= guard stops a stale past
        -- expiry lingering in the chain from winning the min and silently
        -- becoming the pinned one. NO FALLBACK when the set is empty: the
        -- symbol returns no rows. A fallback to plain min() would
        -- reinstate the hazard, and ADR-023 D1 is explicit -- fail to
        -- absent, never to stale.
        SELECT ocs.symbol, min(ocs.expiry_date) AS expiry_date
          FROM option_chain_snapshots ocs
          JOIN latest_ts lt
            ON lt.symbol = ocs.symbol AND lt.max_ts = ocs.ts
         WHERE ocs.expiry_date >= (ocs.ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY ocs.symbol
     ), chain AS (
        -- THE FIX: expiry_date is in the grain and the cohort is bound to
        -- the front expiry. The baseline had neither.
        SELECT ocs.symbol, ocs.ts, ocs.expiry_date, ocs.strike,
               max(CASE WHEN ocs.option_type = 'CE' THEN ocs.oi END) AS ce_oi,
               max(CASE WHEN ocs.option_type = 'PE' THEN ocs.oi END) AS pe_oi
          FROM option_chain_snapshots ocs
          JOIN latest_ts lt
            ON lt.symbol = ocs.symbol AND lt.max_ts = ocs.ts
          JOIN front_expiry fe
            ON fe.symbol = ocs.symbol AND fe.expiry_date = ocs.expiry_date
         GROUP BY ocs.symbol, ocs.ts, ocs.expiry_date, ocs.strike
     ), cohort AS (
        SELECT symbol, expiry_date, count(*) AS n_strikes
          FROM chain
         GROUP BY symbol, expiry_date
     ), strikes AS (
        SELECT DISTINCT symbol, ts, expiry_date, strike
          FROM chain
     ), pain AS (
        SELECT s.symbol, s.ts, s.expiry_date,
               s.strike AS candidate_strike,
               COALESCE(sum(GREATEST(s.strike - c.strike, 0::numeric) * c.ce_oi), 0::numeric)
             + COALESCE(sum(GREATEST(c.strike - s.strike, 0::numeric) * c.pe_oi), 0::numeric)
                 AS total_pain
          FROM strikes s
          LEFT JOIN chain c
            ON c.symbol = s.symbol AND c.expiry_date = s.expiry_date
         GROUP BY s.symbol, s.ts, s.expiry_date, s.strike
     ), max_pain AS (
        -- Partition widened to (symbol, expiry_date). ORDER BY unchanged
        -- from the baseline -- no tie-break column. See header.
        SELECT ranked.symbol, ranked.expiry_date,
               ranked.candidate_strike AS max_pain_strike
          FROM (SELECT pain.symbol, pain.expiry_date, pain.candidate_strike,
                       row_number() OVER (PARTITION BY pain.symbol, pain.expiry_date
                                          ORDER BY pain.total_pain) AS rn
                  FROM pain) ranked
         WHERE ranked.rn = 1
     )
SELECT
    -- ---- the five original columns, same names, same order ----------
    p.symbol,
    p.candidate_strike,
    p.total_pain,
    mp.max_pain_strike,
    CASE
        WHEN p.candidate_strike < mp.max_pain_strike THEN 'PE_SIDE'
        WHEN p.candidate_strike > mp.max_pain_strike THEN 'CE_SIDE'
        ELSE 'MAX_PAIN'
    END AS side,
    -- ---- added at S81 ------------------------------------------------
    p.ts,
    p.expiry_date,
    p.expiry_date - (p.ts AT TIME ZONE 'Asia/Kolkata')::date AS dte,
    ch.n_strikes,
    round(EXTRACT(epoch FROM (now() - p.ts)) / 60.0, 1) AS snapshot_age_min,
    COALESCE(get_parameter_num('maxpain.stale_floor_min'), 30) AS stale_floor_min_used,
    (EXTRACT(epoch FROM (now() - p.ts)) / 60.0)
        <= COALESCE(get_parameter_num('maxpain.stale_floor_min'), 30) AS is_fresh
  FROM pain p
  JOIN max_pain mp
    ON mp.symbol = p.symbol AND mp.expiry_date = p.expiry_date
  JOIN cohort ch
    ON ch.symbol = p.symbol AND ch.expiry_date = p.expiry_date;


-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE)
-- =====================================================================

COMMENT ON VIEW public.v_max_pain_by_strike IS
  'S81 / TD-S80-NEW-10 -- max pain per candidate strike, scoped to the LATEST snapshot and its FRONT expiry. Grain (symbol, expiry_date, candidate_strike). THE EXPIRY FILTER IS THE FIX: the S40 baseline grouped by (symbol, strike) with no expiry in the grain, so a snapshot carrying two expiries collapsed into a per-strike max() MIXTURE of two different contracts. It was not firing -- one expiry per cycle measured across 2,923 cycles -- and becomes live the moment TD-S80-NEW-1 raises ingest depth and the ladder lands in this table. It is therefore fixed BEFORE that depth change, not after. NEAREST EXPIRY = min(expiry_date) among the latest snapshot rows, RESTRICTED to expiry_date >= the IST date of ts. Both clauses are load-bearing: min() picks the front contract, and the >= guard stops a past expiry lingering in the chain from winning the min and silently becoming the pinned one. There is NO FALLBACK when that set is empty -- the symbol returns no rows, because a fallback to plain min() would reinstate the hazard and ADR-023 D1 is explicit: fail to absent, never to stale. ts is timestamptz (measured via information_schema, S81), so AT TIME ZONE converts UTC to IST wall-clock, which is the intended direction. FRESHNESS IS SURFACED, NOT SUPPRESSED. ts, snapshot_age_min, stale_floor_min_used and is_fresh are emitted; rows are NOT dropped when stale. ADR-023 D1 prefers suppression, but D3 requires the operator to be able to tell a stall from an empty result, and under ADR-025 Amendment B the Marketview presentation layer is frozen, so the panel cannot be given that message. Blanking the page would be a silent state change, which is what D3 forbids. ENH-123 v_gex_max_pain made the same call for the same reason, and shares this parameter: get_parameter_num (-maxpain.stale_floor_min-), default 30 minutes. THE SUPPRESSION HALF IS OWED to the Marketview change Amendment B defers; it is deferred, not skipped. BACKWARD COMPATIBILITY IS A HARD CONSTRAINT here. The live Marketview Max Pain page selects candidate_strike, total_pain, max_pain_strike and side, filters on symbol, orders by candidate_strike, reads max_pain_strike from row [0] as a broadcast scalar, and branches on the exact strings MAX_PAIN and PE_SIDE. Those five columns keep their names, order, types and semantics; the seven added columns follow them. Never rename or drop a column here while that page is frozen. NOT CORRECTED, AND DELIBERATELY SO: max_pain ties break NON-DETERMINISTICALLY. The partition is widened to (symbol, expiry_date) but the ORDER BY is unchanged from the baseline -- total_pain with no tie-break column -- so equal total_pain yields an arbitrary winner. ENH-123 orders by (total_pain, candidate_strike). Correcting it is one line and was OUT OF THE APPROVED SCOPE of this change; it is reported for a TD rather than altered silently in a view the frozen frontend reads. latest_ts WAS RETROFITTED S81 and is now the S72 FIX 2 skip-scan plus CROSS JOIN LATERAL probe. It was max(ts) GROUP BY symbol over the whole table -- a full-index scan of 1,336,714 rows costing 3,260 ms of a 3,396 ms view, on a roughly four-week trajectory to the PostgREST 8 second ceiling, at which point this view would have emptied the live Max Pain page silently. Measured after: 0.288 ms, 22 shared hits, 0 reads, one row per symbol with nothing discarded to find each match. Equivalence was proven in a single statement against the old aggregate and was identical on both symbols. KNOWN DEGRADATION MODE, accepted deliberately: the only ts DESC index is idx_ocs_ts_symbol_expiry (ts DESC, symbol, expiry_date), in which symbol is the SECOND column, so the probe walks in ts order and filters on symbol. Both symbols write every cycle, so the match is the first row; if one symbol-s ingest stalls, its probe walks back through the other symbol-s newer entries, about 34,000 index entries per stalled day, index-only, so milliseconds rather than seconds. A dedicated (symbol, ts DESC) index would remove it; that is a separate decision and is deliberately NOT taken here. ANON GRANTS WERE WRONG AND ARE CORRECTED HERE. Measured 2026-09-22: anon held ALL SEVEN privileges on this object -- the S39 Lovable ALL-grants shape on an S40 object created AFTER the S39 13-surface REVOKE cleanup, so that cleanup did not hold for objects added later. It was one of 211 such relations, remediated schema-wide the same day together with ALTER DEFAULT PRIVILEGES so it cannot regress. Practical exposure on THIS object was LOW: it is not auto-updatable (GROUP BY, aggregates, joins), so INSERT / UPDATE / DELETE fail; TRUNCATE does not apply to views; REFERENCES and TRIGGER need DDL, which PostgREST does not issue. PROVENANCE: no DDL for this object existed in the repository before S81 -- the S40 register footer naming sql/v_max_pain_by_strike.sql is false and git has no history for that path. The pre-change body is committed verbatim as sql/2026-09-22_s81_v_max_pain_by_strike_CAPTURED_BASELINE.sql. Display-only per the S37 GEX-as-context-not-gate ruling; it routes nothing.';


-- =====================================================================
-- SECTION 3 of 4 -- anon grants (LIVE). TWO STATEMENTS, run separately.
-- Object-local form of the S81 schema-wide remediation; idempotent
-- against it. Keeps sql/ a true rebuild source: without these two lines
-- a rebuild from this file would produce an anon-inaccessible view and
-- three panels at HTTP 200 with zero rows (TD-S37-03 shape).
-- =====================================================================

REVOKE ALL ON public.v_max_pain_by_strike FROM anon;

GRANT SELECT ON public.v_max_pain_by_strike TO anon;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run separately, after 1-3)
-- =====================================================================

-- 4a -- latest_ts cost shape. Report whether option_chain_snapshots is
--       seq-scanned and at what row count. Do NOT restructure on the
--       strength of this without a separate decision.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_max_pain_by_strike;

-- 4b -- INERTNESS, as ONE statement so both bodies read the same
--       transaction snapshot. Expect old_minus_new = 0, new_minus_old = 0,
--       and equal per-symbol counts on both sides.
--
-- WITH old_latest_ts AS (
--         SELECT symbol, max(ts) AS max_ts FROM option_chain_snapshots GROUP BY symbol
--      ), old_chain AS (
--         SELECT ocs.symbol, ocs.strike,
--                max(CASE WHEN ocs.option_type = 'CE' THEN ocs.oi ELSE NULL::numeric END) AS ce_oi,
--                max(CASE WHEN ocs.option_type = 'PE' THEN ocs.oi ELSE NULL::numeric END) AS pe_oi
--           FROM option_chain_snapshots ocs
--           JOIN old_latest_ts lt ON lt.symbol = ocs.symbol AND lt.max_ts = ocs.ts
--          GROUP BY ocs.symbol, ocs.strike
--      ), old_strikes AS (
--         SELECT DISTINCT symbol, strike FROM old_chain
--      ), old_pain AS (
--         SELECT s.symbol, s.strike AS candidate_strike,
--                COALESCE(sum(GREATEST(s.strike - c.strike, 0::numeric) * c.ce_oi), 0::numeric)
--              + COALESCE(sum(GREATEST(c.strike - s.strike, 0::numeric) * c.pe_oi), 0::numeric) AS total_pain
--           FROM old_strikes s
--           LEFT JOIN old_chain c ON c.symbol = s.symbol
--          GROUP BY s.symbol, s.strike
--      ), old_max_pain AS (
--         SELECT ranked.symbol, ranked.candidate_strike AS max_pain_strike
--           FROM (SELECT old_pain.symbol, old_pain.candidate_strike,
--                        row_number() OVER (PARTITION BY old_pain.symbol ORDER BY old_pain.total_pain) AS rn
--                   FROM old_pain) ranked
--          WHERE ranked.rn = 1
--      ), old AS (
--         SELECT p.symbol, p.candidate_strike, p.total_pain, mp.max_pain_strike,
--                CASE WHEN p.candidate_strike < mp.max_pain_strike THEN 'PE_SIDE'::text
--                     WHEN p.candidate_strike > mp.max_pain_strike THEN 'CE_SIDE'::text
--                     ELSE 'MAX_PAIN'::text END AS side
--           FROM old_pain p JOIN old_max_pain mp ON mp.symbol = p.symbol
--      ), new AS (
--         SELECT symbol, candidate_strike, total_pain, max_pain_strike, side
--           FROM public.v_max_pain_by_strike
--      )
-- SELECT 'old_minus_new' AS dir, count(*)::bigint AS n
--   FROM (SELECT * FROM old EXCEPT SELECT * FROM new) x
-- UNION ALL
-- SELECT 'new_minus_old', count(*)::bigint
--   FROM (SELECT * FROM new EXCEPT SELECT * FROM old) y
-- UNION ALL
-- SELECT 'old_rows_' || symbol, count(*)::bigint FROM old GROUP BY symbol
-- UNION ALL
-- SELECT 'new_rows_' || symbol, count(*)::bigint FROM new GROUP BY symbol
-- ORDER BY 1;

-- 4c -- anon privilege audit. Expect 7 rows, true on SELECT only.
--
-- SELECT p.privilege_type,
--        has_table_privilege('anon', 'public.v_max_pain_by_strike', p.privilege_type) AS anon_has
--   FROM (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),
--                ('TRUNCATE'),('REFERENCES'),('TRIGGER')) AS p(privilege_type)
--  ORDER BY 1;

-- 4d -- comment landed.
--
-- SELECT length(obj_description('public.v_max_pain_by_strike'::regclass, 'pg_class')) AS comment_len,
--        left(obj_description('public.v_max_pain_by_strike'::regclass, 'pg_class'), 30) AS starts_with;
