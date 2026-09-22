-- =====================================================================
-- 2026-09-22_s81_v_oi_rotation_since_open.sql
-- S81 / ENH-127 -- L13 OI rotation since open, LIVE (v_oi_rotation_since_open)
-- =====================================================================
--
-- WHAT THIS IS
--   Parity spec L13, live leg: per front-expiry strike, open interest
--   added or unwound since the 09:15 IST anchor of the session. CE and PE
--   side by side. 17 columns, grain (symbol, expiry_date, strike).
--
--   HISTORICAL ROTATION IS OUT OF SCOPE and deferred. jobid 19 (disabled,
--   TD-S76-NEW-2) thins option_chain_snapshots beyond 14 days to one
--   10:00 UTC row per day, so any historical rotation is capped at 14
--   days by construction if it is re-enabled.
--
-- SESSION FOLLOWS THE DATA, NOT THE CLOCK
--   session_date is the IST date of the LATEST front-expiry snapshot.
--   Keying it to now() would blank the panel overnight, every weekend and
--   every holiday. One rule, no special cases, three consequences:
--     08:35-09:15 on a trading day -> latest is the pre-open row, that
--       date has no 09:15 anchor yet -> NO ROWS. Correct.
--     after 15:40 / overnight / weekend / holiday -> the last completed
--       session, with latest_ts emitted. The data-s actual state, not a
--       stale value dressed as current.
--     mid-session stall -> a partial rotation WOULD read as complete,
--       which is why the ADR-023 freshness columns are here.
--
-- MEASURED S81, and each number changed the design
--   * First row of the day lands 08:35-08:40 IST, pre-open (TD-S80-NEW-9).
--   * NIFTY pre-open OI == previous close on 472/472, max diff 0. A
--     first-row anchor would measure overnight NOTHING. Hence 09:15.
--   * SENSEX differs on 134/392, max abs diff 8,180 -- something revises
--     BSE OI between close and pre-open. Observation only; nothing here
--     depends on it.
--   * A 09:15:0x snapshot exists on every measured session. The
--     at-or-after test INCLUDES it. Contrast ENH-126, where the same ~7s
--     stamp offset put 15:15:07 OUTSIDE an at-or-before-15:15 test: same
--     offset, opposite comparison, opposite effect.
--   * Vendor oi_change, n=472 at the 15:40 snapshot: 343 match
--     latest-minus-session-first, 343 match latest-minus-previous-close
--     (indistinguishable for NIFTY, those anchors coincide), 317 match
--     latest-minus-previous-snapshot but only degenerately (post-close OI
--     is static, so those are the zero rows), and 129 -- 27 pct -- match
--     NOTHING. Not a definition. The delta is computed here.
--   * Units: NIFTY oi divisible by 65 on 13,090/13,090 and by 75 on only
--     729; SENSEX by 20 on 18,037/18,037. oi is shares-equivalent at the
--     CURRENT lot size, and those 729 rows are the fingerprint of a
--     lot-size change. Columns carry _qty. DO NOT divide by a constant --
--     lots need an instrument master with effective dates. Deferred.
--
-- WHAT IS DELIBERATELY ABSENT
--   * No ADDED/UNWOUND enum. The sign carries it, and a label would
--     restate sign(delta) while implying agency the number cannot
--     support: an OI delta cannot distinguish writing from buying.
--   * No n_strikes_anchor / n_strikes_latest. Every strike is a row with
--     a presence flag, so the counts are one aggregate away. They earn
--     their place in the GEX views only because rows are filtered out
--     there; here nothing is.
--
-- APPLY ORDER: Section 1 -> 2 -> 3 -> verify with Section 4.
-- RUN ONE STATEMENT AT A TIME (S72 Section 5).
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS so sql/ matches the database.
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_oi_rotation_since_open AS
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
        -- Index seek per symbol. NOT max(ts) GROUP BY symbol: that shape
        -- measures 3,260 ms over 1,336,714 rows inside
        -- v_max_pain_by_strike and is filed with a clock on it.
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
     ), front AS (
        -- Front expiry from the LATEST snapshot, no fallback (ADR-023 D1).
        -- Resolving this BEFORE the anchor is what keeps the delta inside
        -- one contract once stage 1 puts two ladders at one ts.
        SELECT l.symbol,
               l.latest_ts,
               (l.latest_ts AT TIME ZONE 'Asia/Kolkata')::date AS session_date,
               min(o.expiry_date) AS expiry_date
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol
           AND o.ts = l.latest_ts
           AND o.expiry_date >= (l.latest_ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY l.symbol, l.latest_ts
     ), anchored AS (
        -- First snapshot at or after 09:15 IST on the SESSION date, in the
        -- front expiry. CROSS JOIN LATERAL, so a session with no 09:15
        -- snapshot yet yields no row for that symbol: absence, never a
        -- fallback to the pre-open row.
        SELECT f.symbol, f.latest_ts, f.session_date, f.expiry_date,
               a.ts AS anchor_ts
          FROM front f
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = f.symbol
                  AND o.expiry_date = f.expiry_date
                  AND o.ts >= ((f.session_date + time '09:15') AT TIME ZONE 'Asia/Kolkata')
                  AND o.ts <= f.latest_ts
                ORDER BY o.ts
                LIMIT 1
          ) a
     ), a_rows AS (
        SELECT k.symbol, k.expiry_date, o.strike, o.option_type, o.oi
          FROM anchored k
          JOIN option_chain_snapshots o
            ON o.symbol = k.symbol AND o.ts = k.anchor_ts
           AND o.expiry_date = k.expiry_date
     ), l_rows AS (
        SELECT k.symbol, k.expiry_date, o.strike, o.option_type, o.oi
          FROM anchored k
          JOIN option_chain_snapshots o
            ON o.symbol = k.symbol AND o.ts = k.latest_ts
           AND o.expiry_date = k.expiry_date
     ), joined AS (
        -- FULL OUTER: a strike on one side only survives, with a NULL oi
        -- on the missing side. NULL propagates to a NULL delta. Never 0.
        SELECT COALESCE(a.symbol, l.symbol)           AS symbol,
               COALESCE(a.expiry_date, l.expiry_date) AS expiry_date,
               COALESCE(a.strike, l.strike)           AS strike,
               COALESCE(a.option_type, l.option_type) AS option_type,
               a.oi AS oi_anchor,
               l.oi AS oi_latest
          FROM a_rows a
          FULL OUTER JOIN l_rows l
            ON l.symbol      = a.symbol
           AND l.expiry_date = a.expiry_date
           AND l.strike      = a.strike
           AND l.option_type = a.option_type
     ), pivoted AS (
        SELECT symbol, expiry_date, strike,
               max(oi_anchor) FILTER (WHERE option_type = 'CE') AS ce_oi_anchor_qty,
               max(oi_latest) FILTER (WHERE option_type = 'CE') AS ce_oi_latest_qty,
               max(oi_anchor) FILTER (WHERE option_type = 'PE') AS pe_oi_anchor_qty,
               max(oi_latest) FILTER (WHERE option_type = 'PE') AS pe_oi_latest_qty,
               bool_or(option_type = 'CE') AS has_ce,
               bool_or(option_type = 'PE') AS has_pe
          FROM joined
         GROUP BY symbol, expiry_date, strike
     )
SELECT
    p.symbol,
    p.expiry_date,
    p.expiry_date - k.session_date AS dte,
    k.anchor_ts,
    k.latest_ts,
    p.strike,

    p.ce_oi_anchor_qty,
    p.ce_oi_latest_qty,
    p.ce_oi_latest_qty - p.ce_oi_anchor_qty AS ce_oi_delta_qty,
    -- Fully enumerated, no ELSE. has_ce false means no CE row on either
    -- side; has_ce true with both values NULL means a CE row existed but
    -- carried no oi -- both are NULL presence, which is honest.
    CASE WHEN NOT p.has_ce THEN NULL
         WHEN p.ce_oi_anchor_qty IS NULL AND p.ce_oi_latest_qty IS NOT NULL THEN 'LATEST_ONLY'
         WHEN p.ce_oi_latest_qty IS NULL AND p.ce_oi_anchor_qty IS NOT NULL THEN 'ANCHOR_ONLY'
         WHEN p.ce_oi_anchor_qty IS NOT NULL AND p.ce_oi_latest_qty IS NOT NULL THEN 'BOTH'
    END AS ce_presence,

    p.pe_oi_anchor_qty,
    p.pe_oi_latest_qty,
    p.pe_oi_latest_qty - p.pe_oi_anchor_qty AS pe_oi_delta_qty,
    CASE WHEN NOT p.has_pe THEN NULL
         WHEN p.pe_oi_anchor_qty IS NULL AND p.pe_oi_latest_qty IS NOT NULL THEN 'LATEST_ONLY'
         WHEN p.pe_oi_latest_qty IS NULL AND p.pe_oi_anchor_qty IS NOT NULL THEN 'ANCHOR_ONLY'
         WHEN p.pe_oi_anchor_qty IS NOT NULL AND p.pe_oi_latest_qty IS NOT NULL THEN 'BOTH'
    END AS pe_presence,

    round(EXTRACT(epoch FROM (now() - k.latest_ts)) / 60.0, 1) AS snapshot_age_min,
    COALESCE(get_parameter_num('rotation.stale_floor_min'), 30)  AS stale_floor_min_used,
    (EXTRACT(epoch FROM (now() - k.latest_ts)) / 60.0)
        <= COALESCE(get_parameter_num('rotation.stale_floor_min'), 30) AS is_fresh
  FROM pivoted p
  JOIN anchored k
    ON k.symbol = p.symbol AND k.expiry_date = p.expiry_date;


-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE)
-- =====================================================================

COMMENT ON VIEW public.v_oi_rotation_since_open IS
  'S81 / ENH-127 -- L13 OI rotation since open, LIVE ONLY. One row per symbol per front-expiry strike, CE and PE side by side: open interest at the session anchor, at the latest snapshot, and the delta between them. Grain (symbol, expiry_date, strike). Historical rotation is OUT OF SCOPE and deferred; note that pg_cron jobid 19, currently disabled (TD-S76-NEW-2), thins option_chain_snapshots beyond 14 days to one 10:00 UTC row per day, which would cap any historical rotation at 14 days by construction. SESSION IS THE IST DATE OF THE LATEST FRONT-EXPIRY SNAPSHOT, NOT today. Keying it to now() would blank the panel overnight, every weekend and every holiday. Keying it to the data means: between 08:35 and 09:15 on a trading day the latest snapshot is the pre-open row, that date has no 09:15 anchor yet, and the view returns NO ROWS -- correct; after 15:40, overnight, at weekends and on holidays it shows the last completed session with latest_ts emitted -- the data-s actual state, not a stale value dressed as current. One rule, no special cases. ANCHOR IS THE FIRST SNAPSHOT AT OR AFTER 09:15 IST ON THAT SESSION DATE, resolved WITHIN the front expiry. Measured S81: the first row of the day lands 08:35-08:40 IST, pre-open, and NIFTY pre-open OI equals the previous close on 472 of 472 strikes with max diff 0 -- so anchoring on the first row would measure overnight nothing. SENSEX differs on 134 of 392 with max abs diff 8,180, so something revises BSE OI between close and pre-open; that is recorded as an observation and this view does not depend on it. A 09:15:0x snapshot exists on every measured session, and the at-or-after test includes it -- note the contrast with ENH-126, where cycles stamping ~7s past the mark put 15:15:07 OUTSIDE an at-or-before-15:15 test. Same offset, opposite comparison, opposite effect. FRONT EXPIRY IS RESOLVED FIRST, from the latest snapshot: min(expiry_date) restricted to expiry_date >= the IST date of that snapshot, with NO FALLBACK, exactly as v_max_pain_by_strike does and for the same ADR-023 D1 reason -- fail to absent, never to stale. The anchor lookup then filters on that same expiry_date. When TD-S80-NEW-1 stage 1 raises ingest depth to two expiries, a cycle will carry two expiry ladders at one ts under two run_ids; resolving front expiry BEFORE selecting the anchor is what keeps the delta inside one contract. Inert today, correct after. VENDOR oi_change IS DELIBERATELY IGNORED AND THE DELTA IS COMPUTED HERE. Measured S81 on the 15:40 NIFTY snapshot, n=472: 343 rows match latest-minus-session-first, 343 match latest-minus-previous- close (indistinguishable, because for NIFTY those anchors coincide), 317 match latest-minus- previous-snapshot but only degenerately since post-close OI is static and those are the zero rows, and 129 rows -- 27 pct -- match NO candidate definition at all. A column that fits no definition on a quarter of strikes is not a definition. AN OI DELTA CANNOT DISTINGUISH WRITING FROM BUYING. Positive means open interest rose; it does not mean anyone was short. There is deliberately no ADDED/UNWOUND enum -- the sign carries it, and a label column would restate sign(delta) while implying an agency the number does not support. That is the ADR-024 Amendment A discipline: name the arithmetic, never assert the behaviour. UNITS ARE NATIVE QUANTITY, hence the _qty suffix on every OI column. Measured S81: NIFTY oi divides by 65 on 13,090 of 13,090 rows and by 75 on only 729; SENSEX by 20 on 18,037 of 18,037. So oi is shares-equivalent at the CURRENT lot size, and the 729 rows divisible by 75 are the fingerprint of a lot-size change during the data-s life. Any conversion to lots or contracts needs an instrument master with effective dates, never a literal, and is DEFERRED. Do not divide these columns by a constant. STRIKE CHURN IS CARRIED, NOT HIDDEN. Anchor and latest are FULL OUTER JOINed, so a strike present on one side only yields a NULL delta and a presence flag of ANCHOR_ONLY or LATEST_ONLY -- NEVER 0, which would assert no rotation where the truth is not comparable. Presence is per side because a strike can carry CE without PE. A single expiry-day sample showed 472 in both and no churn either way; that is n=1 and is not evidence the chain window is stable. FRESHNESS IS SURFACED, NOT SUPPRESSED. Because the session follows the data rather than the clock, a mid-session ingest stall would otherwise present a partial rotation as a complete one. snapshot_age_min, stale_floor_min_used and is_fresh are emitted and rows are NOT dropped -- ADR-023 D3, the same call ENH-123 and the S81 max-pain fix made, and for the same reason: under ADR-025 Amendment B the presentation layer is frozen, so a blanked panel could not explain itself. The parameter is get_parameter_num(-rotation.stale_floor_min-), default 30 minutes. It is a SEPARATE key from maxpain.stale_floor_min, with the same default: same writer and same cadence justify the same number, but ADR-023 A1.2 is explicit that a floor binds the CONSUMER, and a shared key would let a max-pain tuning silently retune rotation. PERFORMANCE: symbols via the S72 FIX 2 recursive skip-scan, latest via CROSS JOIN LATERAL ORDER BY ts DESC LIMIT 1, anchor via CROSS JOIN LATERAL ORDER BY ts LIMIT 1 under a ts floor derived from the session date. There is NO max(ts) GROUP BY over option_chain_snapshots -- that is the shape measured at 3,260 ms over 1,336,714 rows inside v_max_pain_by_strike and filed with a clock on it. Working set here is two snapshots per symbol, a few hundred rows each. Display-only per the S37 GEX-as-context-not-gate ruling; it routes nothing.';


-- =====================================================================
-- SECTION 3 of 4 -- anon grants (LIVE). TWO STATEMENTS, run separately.
-- =====================================================================

REVOKE ALL ON public.v_oi_rotation_since_open FROM anon;

GRANT SELECT ON public.v_oi_rotation_since_open TO anon;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run separately, after 1-3)
-- =====================================================================

-- 4a -- EXPLAIN. Expect index seeks under both laterals, NO seq scan and
--       NO full-index scan of option_chain_snapshots.
--
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_oi_rotation_since_open;

-- 4b -- read: top 10 strikes by |CE delta| and by |PE delta|, per symbol.
--
-- WITH v AS (SELECT * FROM public.v_oi_rotation_since_open),
--      legs AS (
--        SELECT symbol, 'CE' AS leg, strike,
--               ce_oi_anchor_qty AS anchor_qty, ce_oi_latest_qty AS latest_qty,
--               ce_oi_delta_qty  AS delta_qty,  ce_presence      AS presence
--          FROM v
--        UNION ALL
--        SELECT symbol, 'PE', strike,
--               pe_oi_anchor_qty, pe_oi_latest_qty, pe_oi_delta_qty, pe_presence
--          FROM v
--      ), r AS (
--        SELECT legs.*,
--               row_number() OVER (PARTITION BY symbol, leg
--                                  ORDER BY abs(delta_qty) DESC NULLS LAST) AS rn
--          FROM legs
--      )
-- SELECT symbol, leg, rn, strike, anchor_qty, latest_qty, delta_qty, presence
--   FROM r
--  WHERE rn <= 10
--  ORDER BY symbol, leg, rn;

-- 4c -- invariants, one statement. Every count MUST be 0.
--
-- SELECT 'zero_delta_without_both_ce' AS chk, count(*) FROM public.v_oi_rotation_since_open
--   WHERE ce_oi_delta_qty = 0 AND ce_presence IS DISTINCT FROM 'BOTH'
-- UNION ALL
-- SELECT 'zero_delta_without_both_pe', count(*) FROM public.v_oi_rotation_since_open
--   WHERE pe_oi_delta_qty = 0 AND pe_presence IS DISTINCT FROM 'BOTH'
-- UNION ALL
-- SELECT 'latest_not_after_anchor', count(*) FROM public.v_oi_rotation_since_open
--   WHERE latest_ts <= anchor_ts
-- UNION ALL
-- SELECT 'duplicate_symbol_strike', count(*) FROM (
--   SELECT symbol, strike FROM public.v_oi_rotation_since_open
--    GROUP BY symbol, strike HAVING count(*) > 1) d
-- UNION ALL
-- SELECT 'multiple_expiries_per_symbol', count(*) FROM (
--   SELECT symbol FROM public.v_oi_rotation_since_open
--    GROUP BY symbol HAVING count(DISTINCT expiry_date) > 1) e;

-- 4d -- does it return rows now, and what does it say about freshness?
--       After the close, expect latest_ts = today 15:40 IST and is_fresh
--       false once more than stale_floor_min_used minutes have passed.
--
-- SELECT symbol, expiry_date, dte,
--        (anchor_ts AT TIME ZONE 'Asia/Kolkata') AS anchor_ist,
--        (latest_ts AT TIME ZONE 'Asia/Kolkata') AS latest_ist,
--        count(*) AS n_strikes,
--        count(*) FILTER (WHERE ce_presence = 'BOTH') AS ce_both,
--        count(*) FILTER (WHERE pe_presence = 'BOTH') AS pe_both,
--        count(*) FILTER (WHERE ce_presence <> 'BOTH' OR pe_presence <> 'BOTH') AS churned,
--        max(snapshot_age_min) AS age_min,
--        max(stale_floor_min_used) AS floor_min,
--        bool_and(is_fresh) AS is_fresh
--   FROM public.v_oi_rotation_since_open
--  GROUP BY symbol, expiry_date, dte, anchor_ts, latest_ts
--  ORDER BY symbol;

-- 4e -- anon privilege audit (expect SELECT only) and comment length.
--
-- SELECT p.privilege_type,
--        has_table_privilege('anon', 'public.v_oi_rotation_since_open', p.privilege_type) AS anon_has
--   FROM (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),
--                ('TRUNCATE'),('REFERENCES'),('TRIGGER')) AS p(privilege_type)
--  ORDER BY 1;
--
-- SELECT length(obj_description('public.v_oi_rotation_since_open'::regclass, 'pg_class')) AS comment_len,
--        left(obj_description('public.v_oi_rotation_since_open'::regclass, 'pg_class'), 30) AS starts_with;
