-- =====================================================================
-- 2026-10-11_s95_v_oi_since_preopen.sql
-- S95 / roadmap P5 (PPC-1) / ruling S95-B -- open interest since the
-- pre-open row, per front-expiry strike (v_oi_since_preopen).
-- =====================================================================
--
-- RULING S95-B (2026-10-11): the baseline is the session's PRE-OPEN row
--   (first snapshot of the session date, refused if stamped at or after
--   09:15 IST); a view, not a table; front expiry only.
-- MEASUREMENTS behind it: docs/research/s95_priority/p5/
--   P5_preopen_baseline_note_2026-10-11.md (probes 1-3, drill, untraded).
--
-- SECTION 1 IS v_oi_rotation_since_open (L13, sql/2026-09-22_s81_...)
--   WITH EXACTLY THESE CHANGES, and no others (diff in the note):
--   1. the view name;
--   2. the anchored CTE: ts floor 00:00 IST instead of 09:15, and
--      WHERE a.ts < 09:15 IST on the session date (refuse, never fall back);
--   3. the freshness key oi_preopen.stale_floor_min (2 occurrences).
--
-- APPLY: Sections 1 -> 3 in ONE execution. The batch ENDS with its own
-- verification SELECT (TD-S94-NEW-3). Then Section 4, one statement
-- (4e: one execution) at a time.
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS (TD-S81-NEW-5).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_oi_since_preopen AS
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
        -- S95-B: the FIRST snapshot of the SESSION date in the front expiry --
        -- the pre-open row, 08:30-08:40 IST -- and it must be stamped BEFORE
        -- 09:15 IST. A session whose first row is at or after 09:15 (a late
        -- start, a thinned retention day) has no pre-open anchor and yields NO
        -- ROW for that symbol: absence, never a fallback to a later row.
        SELECT f.symbol, f.latest_ts, f.session_date, f.expiry_date,
               a.ts AS anchor_ts
          FROM front f
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = f.symbol
                  AND o.expiry_date = f.expiry_date
                  AND o.ts >= ((f.session_date + time '00:00') AT TIME ZONE 'Asia/Kolkata')
                  AND o.ts <= f.latest_ts
                ORDER BY o.ts
                LIMIT 1
          ) a
         WHERE a.ts < ((f.session_date + time '09:15') AT TIME ZONE 'Asia/Kolkata')
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
    COALESCE(get_parameter_num('oi_preopen.stale_floor_min'), 30)  AS stale_floor_min_used,
    (EXTRACT(epoch FROM (now() - k.latest_ts)) / 60.0)
        <= COALESCE(get_parameter_num('oi_preopen.stale_floor_min'), 30) AS is_fresh
  FROM pivoted p
  JOIN anchored k
    ON k.symbol = p.symbol AND k.expiry_date = p.expiry_date;


-- =====================================================================
-- SECTION 2 of 4 -- COMMENT (LIVE statement -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_oi_since_preopen IS
  'S95 / roadmap P5 (PPC-1) / ruling S95-B -- open interest since the PRE-OPEN row, per front-expiry strike. The previous-close baseline the flow leg (P7, ENH-98 D-4) needs. NOT a parity layer; display-only (S37); routes nothing. Grain (symbol, expiry_date, strike), CE and PE side by side: OI at the anchor, at the latest snapshot, and the delta. IT IS v_oi_rotation_since_open (L13, ENH-127) WITH EXACTLY ONE CHANGE, THE ANCHOR: the first snapshot of the session date in the front expiry, which must be stamped before 09:15 IST, instead of the first snapshot at or after 09:15. Every other line of L13 is unchanged: session = IST date of the latest snapshot (follows the data, not the clock); front expiry from the latest snapshot, no fallback (ADR-023 D1); FULL OUTER JOIN with per-side presence (LATEST_ONLY / ANCHOR_ONLY / BOTH), a strike on one side only has a NULL delta, never 0; vendor oi_change ignored; native quantity (_qty), never divided by a lot constant; freshness surfaced, rows never dropped, floor key oi_preopen.stale_floor_min (default 30, a separate key from L13 rotation.stale_floor_min). WHY THE PRE-OPEN ROW (S95-B, measured S95 over 26 session changeovers per symbol, 2026-08-27 to 2026-10-09): on NIFTY the pre-open row equals the previous session 15:40 close on every leg of every changeover, so it IS the previous close; on SENSEX it differs from the 15:40 close on 23 to 41 pct of legs every night (BSE revises OI after the close; S81 saw 134 of 392 on 09-22, reproduced exactly), and anchoring on it keeps that overnight revision out of the day flow. It reads only the session own rows, so a closed day that carries rows (2026-10-02 has none in trading_calendar and wrote a full day) cannot become the baseline. Between the pre-open and 09:15 NIFTY OI changes on 111 to 190 legs a day and that change IS counted here; L13 excludes it. ABSENCE: a session whose first front-expiry row is at or after 09:15 IST (late start, thinned retention day) returns NO ROWS for that symbol. From 08:30 to 09:15 on a trading day the latest row is itself a pre-open row, so a delta then is a change in vendor-reported OI before any trade. VENDOR OI ON UNTRADED LEGS IS NOT A MEASUREMENT (S95): deep in-the-money SENSEX calls with volume 0 and a frozen ltp carried OI that jumped between 0, about 1.84 million and 48.8 million from one session to the next (2026-09-25, 09-28, 09-29, front expiry 2026-10-01); on those three days legs with no volume held 33 to 94 pct of front SENSEX OI. No untraded leg changed OI between 09:15 and the close on any of 22 symbol-sessions measured (2026-09-24 to 10-09), so from 09:15 on it does not move this view delta; it does inflate every reader of OI LEVELS (the DEX book, GEX, max pain) for the whole session. Read a large delta on a leg with no volume as a vendor value, not flow. AN OI DELTA CANNOT DISTINGUISH WRITING FROM BUYING; no dealer claim (P2: dealer side regime-dependent). Anchor seek measured 0.18 ms (index-only scan, idx_ocs_ts_symbol_expiry) against 25,117 ms for v_oi_prev_close_snapshots (S89). Never label second-order terms vanna or charm (L78-1).';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- CASE-2026-09-22, ADR-031 D6)
-- =====================================================================

REVOKE ALL ON public.v_oi_since_preopen FROM anon, authenticated;
GRANT SELECT ON public.v_oi_since_preopen TO anon, merdian_ro;

-- end-of-batch verification (TD-S94-NEW-3) -- must return ONE row:
--   has_view t | comment_len 3118 | comment_md5 0b0676edfb6b0086ff328e5438312112
--   anon_r t | anon_write f | merdian_ro_r t | authenticated_r f
SELECT to_regclass('public.v_oi_since_preopen') IS NOT NULL                              AS has_view,
       length(obj_description('public.v_oi_since_preopen'::regclass, 'pg_class'))         AS comment_len,
       md5(obj_description('public.v_oi_since_preopen'::regclass, 'pg_class'))            AS comment_md5,
       has_table_privilege('anon', 'public.v_oi_since_preopen', 'SELECT')                 AS anon_r,
       has_table_privilege('anon', 'public.v_oi_since_preopen', 'INSERT,UPDATE,DELETE,TRUNCATE') AS anon_write,
       has_table_privilege('merdian_ro', 'public.v_oi_since_preopen', 'SELECT')           AS merdian_ro_r,
       has_table_privilege('authenticated', 'public.v_oi_since_preopen', 'SELECT')        AS authenticated_r;


-- =====================================================================
-- SECTION 4 of 4 -- verification (after 1-3; one statement per execution)
-- =====================================================================

-- 4a -- plan. Expect Index (Only) Scan on option_chain_snapshots under every lateral,
--       NO Seq Scan of option_chain_snapshots, Execution Time in milliseconds.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_oi_since_preopen;

-- 4b -- independent recompute, every leg. Written without the view's CTEs: latest by
--       max(ts) per symbol, anchor by min(ts) over the session date, presence and delta
--       recomputed. It fails if any anchor, latest, OI, delta or presence differs.
--       PASS: view_minus_ind 0 | ind_minus_view 0 | n_view = n_ind, per symbol.
--       S95 correction: the first form (max(ts) GROUP BY over 10 days; anchor by an
--       IST-date equality; legs by ts IN (..)) hit roq's 30 s statement timeout on the
--       live table. Every lookup is now a ts equality or a ts range; the logic compared
--       is unchanged.
WITH lt AS (
  SELECT s.symbol,
         (SELECT max(o.ts) FROM option_chain_snapshots o WHERE o.symbol = s.symbol) AS latest_ts
    FROM (VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol)
), fe AS (
  SELECT lt.symbol, lt.latest_ts, (lt.latest_ts AT TIME ZONE 'Asia/Kolkata')::date AS d,
         (SELECT min(o.expiry_date) FROM option_chain_snapshots o
           WHERE o.symbol = lt.symbol AND o.ts = lt.latest_ts
             AND o.expiry_date >= (lt.latest_ts AT TIME ZONE 'Asia/Kolkata')::date) AS e
    FROM lt
), an AS (
  SELECT fe.*,
         (SELECT min(o.ts) FROM option_chain_snapshots o
           WHERE o.symbol = fe.symbol AND o.expiry_date = fe.e
             AND o.ts >= ((fe.d + time '00:00') AT TIME ZONE 'Asia/Kolkata')
             AND o.ts <  (((fe.d + 1) + time '00:00') AT TIME ZONE 'Asia/Kolkata')) AS a
    FROM fe
), ok AS MATERIALIZED (
  SELECT * FROM an WHERE (a AT TIME ZONE 'Asia/Kolkata')::time < time '09:15'
), u AS (
  SELECT ok.symbol, ok.e, o.strike, o.option_type, o.oi AS oi_a, NULL::numeric AS oi_l,
         (o.oi IS NOT NULL) AS a_has, false AS l_has
    FROM ok JOIN option_chain_snapshots o
      ON o.ts = ok.a AND o.symbol = ok.symbol AND o.expiry_date = ok.e
  UNION ALL
  SELECT ok.symbol, ok.e, o.strike, o.option_type, NULL::numeric, o.oi,
         false, (o.oi IS NOT NULL)
    FROM ok JOIN option_chain_snapshots o
      ON o.ts = ok.latest_ts AND o.symbol = ok.symbol AND o.expiry_date = ok.e
), legs AS (
  SELECT symbol, e, strike, option_type,
         max(oi_a) AS oi_a, max(oi_l) AS oi_l, bool_or(a_has) AS a_has, bool_or(l_has) AS l_has
    FROM u GROUP BY symbol, e, strike, option_type
), ind AS (
  SELECT symbol, e AS expiry_date, strike,
         max(oi_a) FILTER (WHERE option_type = 'CE') AS ce_a,
         max(oi_l) FILTER (WHERE option_type = 'CE') AS ce_l,
         max(oi_l) FILTER (WHERE option_type = 'CE') - max(oi_a) FILTER (WHERE option_type = 'CE') AS ce_d,
         CASE WHEN NOT bool_or(option_type = 'CE') THEN NULL
              WHEN bool_or(option_type = 'CE' AND a_has) AND bool_or(option_type = 'CE' AND l_has) THEN 'BOTH'
              WHEN bool_or(option_type = 'CE' AND l_has) THEN 'LATEST_ONLY'
              WHEN bool_or(option_type = 'CE' AND a_has) THEN 'ANCHOR_ONLY' END AS ce_p,
         max(oi_a) FILTER (WHERE option_type = 'PE') AS pe_a,
         max(oi_l) FILTER (WHERE option_type = 'PE') AS pe_l,
         max(oi_l) FILTER (WHERE option_type = 'PE') - max(oi_a) FILTER (WHERE option_type = 'PE') AS pe_d,
         CASE WHEN NOT bool_or(option_type = 'PE') THEN NULL
              WHEN bool_or(option_type = 'PE' AND a_has) AND bool_or(option_type = 'PE' AND l_has) THEN 'BOTH'
              WHEN bool_or(option_type = 'PE' AND l_has) THEN 'LATEST_ONLY'
              WHEN bool_or(option_type = 'PE' AND a_has) THEN 'ANCHOR_ONLY' END AS pe_p
    FROM legs GROUP BY symbol, e, strike
), v AS (
  SELECT symbol, expiry_date, strike,
         ce_oi_anchor_qty, ce_oi_latest_qty, ce_oi_delta_qty, ce_presence,
         pe_oi_anchor_qty, pe_oi_latest_qty, pe_oi_delta_qty, pe_presence
    FROM public.v_oi_since_preopen
)
SELECT lt.symbol,
       (SELECT count(*) FROM (SELECT * FROM v WHERE symbol = lt.symbol
                              EXCEPT SELECT * FROM ind WHERE symbol = lt.symbol) x) AS view_minus_ind,
       (SELECT count(*) FROM (SELECT * FROM ind WHERE symbol = lt.symbol
                              EXCEPT SELECT * FROM v WHERE symbol = lt.symbol) x) AS ind_minus_view,
       (SELECT count(*) FROM v   WHERE symbol = lt.symbol) AS n_view,
       (SELECT count(*) FROM ind WHERE symbol = lt.symbol) AS n_ind
  FROM lt ORDER BY 1;

-- 4c -- invariants, one statement. Every count MUST be 0.
SELECT 'zero_delta_without_both_ce' AS chk, count(*) FROM public.v_oi_since_preopen
  WHERE ce_oi_delta_qty = 0 AND ce_presence IS DISTINCT FROM 'BOTH'
UNION ALL
SELECT 'zero_delta_without_both_pe', count(*) FROM public.v_oi_since_preopen
  WHERE pe_oi_delta_qty = 0 AND pe_presence IS DISTINCT FROM 'BOTH'
UNION ALL
SELECT 'latest_before_anchor', count(*) FROM public.v_oi_since_preopen WHERE latest_ts < anchor_ts
UNION ALL
SELECT 'anchor_at_or_after_0915', count(*) FROM public.v_oi_since_preopen
  WHERE (anchor_ts AT TIME ZONE 'Asia/Kolkata')::time >= time '09:15'
UNION ALL
SELECT 'anchor_not_on_session_date', count(*) FROM public.v_oi_since_preopen
  WHERE (anchor_ts AT TIME ZONE 'Asia/Kolkata')::date <> (latest_ts AT TIME ZONE 'Asia/Kolkata')::date
UNION ALL
SELECT 'duplicate_symbol_strike', count(*) FROM (
  SELECT symbol, strike FROM public.v_oi_since_preopen GROUP BY symbol, strike HAVING count(*) > 1) d
UNION ALL
SELECT 'multiple_expiries_per_symbol', count(*) FROM (
  SELECT symbol FROM public.v_oi_since_preopen GROUP BY symbol HAVING count(DISTINCT expiry_date) > 1) e;

-- 4d -- what the anchor IS: the view's anchor OI against the PREVIOUS session's last row,
--       front expiry, legs present on both. Expected values were MEASURED BEFORE this
--       view existed (S95 probe 1, session 2026-10-09, prev 10-08 15:40), so they apply
--       only while the view's session is 2026-10-09 -- run before 08:30 IST Mon 10-12:
--       NIFTY  compared 472 | differ 0   | max_abs 0
--       SENSEX compared 390 | differ 102 | max_abs 8420
WITH v AS (
  SELECT DISTINCT symbol, expiry_date, anchor_ts FROM public.v_oi_since_preopen
), pv AS (
  SELECT v.*, (SELECT o.ts FROM option_chain_snapshots o
                WHERE o.symbol = v.symbol
                  AND o.ts < ((((v.anchor_ts AT TIME ZONE 'Asia/Kolkata')::date) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
                ORDER BY o.ts DESC LIMIT 1) AS prev_ts
    FROM v
), vl AS (
  SELECT symbol, strike, 'CE' AS option_type, ce_oi_anchor_qty AS oi FROM public.v_oi_since_preopen WHERE ce_oi_anchor_qty IS NOT NULL
  UNION ALL
  SELECT symbol, strike, 'PE', pe_oi_anchor_qty FROM public.v_oi_since_preopen WHERE pe_oi_anchor_qty IS NOT NULL
)
SELECT pv.symbol,
       to_char(pv.anchor_ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS anchor_ist,
       to_char(pv.prev_ts   AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS prev_ist,
       count(*)                                  AS compared,
       count(*) FILTER (WHERE vl.oi <> o.oi)     AS differ,
       max(abs(vl.oi - o.oi))                    AS max_abs
  FROM pv
  JOIN option_chain_snapshots o ON o.symbol = pv.symbol AND o.ts = pv.prev_ts AND o.expiry_date = pv.expiry_date
  JOIN vl ON vl.symbol = o.symbol AND vl.strike = o.strike AND vl.option_type = o.option_type
 GROUP BY pv.symbol, pv.anchor_ts, pv.prev_ts
 ORDER BY 1;

-- 4e -- the anon path, S84 form, ONE execution. PASS: role_now anon, n per symbol = 4b n_view.
BEGIN;
SET LOCAL ROLE anon;
SELECT current_user AS role_now, symbol, count(*) AS n
  FROM public.v_oi_since_preopen GROUP BY symbol ORDER BY symbol;
COMMIT;
