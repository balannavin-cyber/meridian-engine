-- =====================================================================
-- 2026-09-25_s83_v_iv_surface.sql
-- S83 / ENH-132 -- L10 IV surface, LIVE (v_iv_surface)
-- =====================================================================
--
-- WHAT THIS IS
--   Parity spec L10. A strike x expiry mesh of implied volatility at the
--   LATEST option_chain_snapshots ts per symbol, with the companion
--   SKEW published per leg. No fitting, no interpolation, no moneyness
--   cut. 21 columns, grain (symbol, ts, expiry_date, strike).
--
-- THE OTM CONVENTION IS THE MEASURED CHOICE, NOT A PREFERENCE
--   iv is the OTM side: the PUT below spot, the CALL above it. Measured
--   S83 at the latest cycle:
--     * Inside +/-2% the CE/PE disagreement is negligible -- median
--       CE minus PE of -0.064, -0.079 and -0.065 vol points across the
--       three central buckets on NIFTY leg 1. Averaging is harmless there.
--     * Outside +/-2% it is not. On SENSEX leg 1 the -5..-2% bucket reads
--       a median AVERAGE of 369.99 vol points where the OTM side reads
--       40.30, on the same strikes. On NIFTY leg 2 the -5..-2% bucket
--       reads an average of 51.29 against an OTM side of 14.98.
--     * 789 of 876 mesh rows carry a quoted OTM side, and that is EXACTLY
--       the count that carries any quote at all. There is no strike where
--       averaging recovers a value the OTM convention loses.
--   Both raw sides stay published as ce_iv and pe_iv, and parity_gap
--   exposes the disagreement per row, so the choice is auditable.
--
-- ZERO MEANS ABSENT
--   Measured S83: iv IS NULL on 0 of 1,752 legs, while iv = 0 appears on
--   20 to 134 legs PER SIDE PER LEG (8 side-leg pairs). The feed encodes
--   absence as zero, not
--   as NULL. Every iv read here is NULLIF(iv, 0). The L9 view records
--   the same deviation for the same reason; what is new here is the
--   scale -- L9 measured only the ATM strike and found a single zero per
--   leg, which does NOT generalise to the surface.
--
-- MEASURED S83, and each number shaped the design
--   * Latest cycle 876 mesh rows: NIFTY 268 + 230, SENSEX 196 + 182.
--   * Only 282 of 876 rows quote BOTH sides. A both-sides rule would
--     discard 68 pct of the surface.
--   * Strike range is far wider than the eye expects: NIFTY leg 1 spans
--     -93.5 pct to +114.6 pct of spot with a maximum step of 1500. No
--     moneyness cut is applied here; moneyness_pct is published so a
--     consumer can cut its own.
--   * Wing quality is poor and near-money quality is perfect. The three
--     central buckets carry 0 pct absent and 0 outliers on TWO of four
--     legs (both NIFTY legs); SENSEX leg 2 shows 3 over-3x-ATM and 2
--     jumps in -2..-0.5%, and SENSEX leg 1 fails all three buckets.
--     The wings run 33 to 89 pct absent.
--   * 14 of the 20 worst outliers by iv over ATM carry oi = 0 (NIFTY
--     leg 1 three, NIFTY leg 2 five, SENSEX leg 1 five, SENSEX leg 2
--     one). The six with real open interest are NIFTY leg 1 26300 PE
--     (61,620) and 28500 PE (337,155) plus SENSEX leg 2 72100-72400 CE.
--     ALL TWENTY ARE ON THE ITM SIDE, so the OTM convention excludes
--     every one of them -- that is the argument, not the oi count.
--     The high-oi case: SENSEX leg 2 at 72100-72400 CE, 1.6 to 2.0 pct
--     in the money, reads iv 110 to 117 against an ATM of 13.1 while
--     holding 48.7 million open interest, including a 92.14 point jump
--     between adjacent strikes. oi_otm and iv_over_atm are published so
--     that row is visible rather than silently rendered.
--
-- CTEs px, hdr, k98r, legmeta are MATERIALIZED: with inlining the
-- planner evaluated k98r once per output row (loops=876, 2715 ms at
-- S83 V6).
--
-- APPLY ORDER: Section 1 -> 2 -> 3 -> verify with Section 4.
-- RUN ONE STATEMENT AT A TIME (S72 Section 5).
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS so sql/ matches the database
-- (TD-S81-NEW-5: a body-only file is not a rebuild source).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_iv_surface AS
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
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), scoped AS (
        SELECT o.symbol, o.ts, o.expiry_date, o.strike, o.option_type,
               o.iv, o.oi, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
     ), legs AS (
        -- leg 1 is the front. dense_rank, so numbering is gapless.
        SELECT DISTINCT symbol, ts, expiry_date,
               dense_rank() OVER (PARTITION BY symbol, ts
                                  ORDER BY expiry_date) AS leg
          FROM scoped
     ), px AS MATERIALIZED (
        -- One row per (symbol, ts, expiry, strike). All iv reads are
        -- NULLIF(iv, 0): zero is absence, not a volatility.
        SELECT s.symbol, s.ts, s.expiry_date, g.leg, s.strike,
               max(s.spot) AS spot,
               NULLIF(max(CASE WHEN s.option_type = 'CE' THEN s.iv END), 0) AS ce_iv,
               NULLIF(max(CASE WHEN s.option_type = 'PE' THEN s.iv END), 0) AS pe_iv,
               max(CASE WHEN s.option_type = 'CE' THEN s.oi END) AS ce_oi,
               max(CASE WHEN s.option_type = 'PE' THEN s.oi END) AS pe_oi
          FROM scoped s
          JOIN legs g
            ON g.symbol = s.symbol AND g.ts = s.ts
           AND g.expiry_date = s.expiry_date
         GROUP BY s.symbol, s.ts, s.expiry_date, g.leg, s.strike
     ), hdr AS MATERIALIZED (
        -- Per-leg header. House ATM grid: round(spot / step) * step,
        -- step 50 for NIFTY and 100 for SENSEX, matching
        -- compute_volatility_metrics_local.py:86-88 and :624.
        SELECT p.symbol, p.ts, p.expiry_date, p.leg,
               max(p.spot) AS spot,
               (p.expiry_date
                - (p.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               round(max(p.spot)
                     / (CASE WHEN p.symbol = 'NIFTY' THEN 50 ELSE 100 END))
                 * (CASE WHEN p.symbol = 'NIFTY' THEN 50 ELSE 100 END)
                 AS atm_k
          FROM px p
         GROUP BY p.symbol, p.ts, p.expiry_date, p.leg
     ), atm AS (
        -- leg_atm_iv EXACTLY as v_iv_term_structure computes atm_iv:
        -- both sides must be quoted above zero, else the leg abstains.
        -- A one-sided ATM is not averaged into a number.
        SELECT h.symbol, h.ts, h.expiry_date, h.leg,
               CASE WHEN p.ce_iv > 0 AND p.pe_iv > 0
                    THEN (p.ce_iv + p.pe_iv) / 2.0
               END AS atm_iv
          FROM hdr h
          LEFT JOIN px p
            ON p.symbol = h.symbol AND p.ts = h.ts
           AND p.expiry_date = h.expiry_date AND p.strike = h.atm_k
     ), k98r AS MATERIALIZED (
        -- leg_k98 = the LISTED strike nearest 0.98 * leg_atm_strike.
        -- Ties resolve to the LOWER strike (strike ASC). Measured S83
        -- over 170 SENSEX leg-1 cycles this lands within 0.013 pct of
        -- the -2.000 pct target, and 0 cycles land more than 0.25 pct
        -- off, so the anchor is not a source of error.
        SELECT p.symbol, p.ts, p.expiry_date, p.leg, p.strike,
               row_number() OVER (PARTITION BY p.symbol, p.ts, p.expiry_date
                                  ORDER BY abs(p.strike - 0.98 * h.atm_k),
                                           p.strike ASC) AS rn
          FROM px p
          JOIN hdr h
            ON h.symbol = p.symbol AND h.ts = p.ts
           AND h.expiry_date = p.expiry_date
     ), k98 AS (
        SELECT symbol, ts, expiry_date, leg, strike AS k98
          FROM k98r WHERE rn = 1
     ), k98iv AS (
        -- The OTM put AT leg_k98. NO SEARCH: if that strike has no
        -- quoted put, leg_skew_98 is NULL. Sliding to a neighbour would
        -- move the moneyness and silently change what is measured.
        SELECT k.symbol, k.ts, k.expiry_date, k.leg, k.k98, p.pe_iv AS k98_pe_iv
          FROM k98 k
          LEFT JOIN px p
            ON p.symbol = k.symbol AND p.ts = k.ts
           AND p.expiry_date = k.expiry_date AND p.strike = k.k98
     ), legmeta AS MATERIALIZED (
        -- S62: a dte-0 leg is SKIPPED_EXPIRY. Raw ce_iv and pe_iv are
        -- KEPT so the degradation is inspectable; every derived value
        -- is withheld.
        SELECT h.symbol, h.ts, h.expiry_date, h.leg, h.spot, h.dte, h.atm_k,
               CASE WHEN h.dte = 0 THEN 'SKIPPED_EXPIRY' ELSE 'OK' END AS leg_status,
               CASE WHEN h.dte = 0 THEN NULL ELSE a.atm_iv END AS leg_atm_iv,
               i.k98 AS leg_k98,
               CASE WHEN h.dte = 0 THEN NULL
                    ELSE i.k98_pe_iv - a.atm_iv
               END AS leg_skew_98
          FROM hdr h
          LEFT JOIN atm   a ON a.symbol = h.symbol AND a.ts = h.ts
                           AND a.expiry_date = h.expiry_date
          LEFT JOIN k98iv i ON i.symbol = h.symbol AND i.ts = h.ts
                           AND i.expiry_date = h.expiry_date
     )
SELECT
    p.symbol,
    p.ts,
    p.expiry_date,
    p.leg,
    m.dte,
    m.spot,
    p.strike,
    (100.0 * (p.strike / m.spot - 1.0))          AS moneyness_pct,
    CASE WHEN p.strike < m.spot THEN 'PE' ELSE 'CE' END AS side_used,
    p.ce_iv,
    p.pe_iv,
    -- The published surface value. OTM side, withheld on a skipped leg.
    CASE WHEN m.leg_status <> 'OK' THEN NULL
         WHEN p.strike < m.spot   THEN p.pe_iv
         ELSE p.ce_iv
    END                                          AS iv,
    (p.ce_iv - p.pe_iv)                          AS parity_gap,
    CASE WHEN p.strike < m.spot THEN p.pe_oi ELSE p.ce_oi END AS oi_otm,
    CASE WHEN m.leg_status <> 'OK' OR m.leg_atm_iv IS NULL THEN NULL
         ELSE (CASE WHEN p.strike < m.spot THEN p.pe_iv ELSE p.ce_iv END)
              / m.leg_atm_iv
    END                                          AS iv_over_atm,
    -- Describes the DATA, not the mask: a skipped leg still reports
    -- whether its OTM side was quoted.
    CASE WHEN (CASE WHEN p.strike < m.spot THEN p.pe_iv ELSE p.ce_iv END) IS NULL
         THEN 'OTM_ABSENT' ELSE 'OTM_QUOTED'
    END                                          AS quote_state,
    m.atm_k                                      AS leg_atm_strike,
    m.leg_atm_iv,
    m.leg_k98,
    m.leg_skew_98,
    m.leg_status
  FROM px p
  JOIN legmeta m
    ON m.symbol = p.symbol AND m.ts = p.ts AND m.expiry_date = p.expiry_date;

-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE, not commented out -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_iv_surface IS
  'S83 / ENH-132 -- ADR-025 parity spec L10, the IV SURFACE: a strike by expiry mesh of implied '
  'volatility at the LATEST option_chain_snapshots ts per symbol, with a companion SKEW per leg. Grain '
  '(symbol, ts, expiry_date, strike). Consumers MUST ORDER BY symbol, leg, strike -- a view body '
  'carries no ordering guarantee. DISPLAY ONLY per the S37 GEX-as-context-not-gate ruling: it routes '
  'nothing, gates nothing, and makes no predictive claim. NO FITTING, NO INTERPOLATION, NO MONEYNESS '
  'CUT -- the mesh is published as quoted, and moneyness_pct is carried so a consumer can cut its own. '
  'THE OTM CONVENTION IS MEASURED, NOT PREFERRED. iv is the OTM side: the PUT below spot, the CALL '
  'above it. Inside plus or minus 2 pct the CE minus PE disagreement is negligible -- medians of '
  '-0.064, -0.079 and -0.065 vol points across the three central buckets on the NIFTY front leg -- so '
  'averaging would be harmless there. Outside that band it is not: on the SENSEX front leg the -5 to -2'
  ' pct bucket reads a median AVERAGE of 369.99 vol points where the OTM side reads 40.30 on the same '
  'strikes, and on the NIFTY back leg the -5 to -2 pct bucket reads an average of 51.29 against an OTM '
  'side of 14.98. 789 of 876 mesh rows carry a quoted OTM side, which is EXACTLY the number carrying '
  'any quote at all, so there is no strike where averaging recovers a value the OTM convention loses. '
  'ce_iv, pe_iv and parity_gap are all published so the choice is auditable per row. ZERO MEANS ABSENT.'
  ' Measured S83: iv IS NULL on 0 of 1752 legs while iv = 0 appears on 20 to 134 legs PER SIDE PER LEG '
  'across 8 side-leg pairs -- the feed encodes absence as zero. Every iv read here is NULLIF(iv, 0), '
  'and quote_state reports OTM_QUOTED or OTM_ABSENT per row. The L9 view records the same deviation, '
  'but L9 measured only the ATM strike and found a single zero per leg; that does NOT generalise to the'
  ' surface. LEG_SKEW_98 IS NOT COMPARABLE ACROSS EXPIRIES. It is defined as the OTM PUT at leg_k98 '
  'minus leg_atm_iv, where leg_k98 is the LISTED strike nearest 0.98 times leg_atm_strike with ties '
  'resolved to the lower strike, and no search: if that strike has no quoted put the value is NULL '
  'rather than sliding to a neighbour, because sliding would move the moneyness and silently change '
  'what is measured. A FIXED 2 PCT BELOW-ATM STRIKE SITS AT A DIFFERENT POINT ON THE SMILE AT EACH '
  'TENOR, so a single level threshold applied across tenors is not a valid test, and comparing this '
  'column between legs is not a valid reading. It is a per-leg quantity. This is recorded because an '
  'S83 gate did exactly that and was withdrawn as MIS-SPECIFIED rather than loosened; the strike anchor'
  ' was separately measured and cleared, landing within 0.013 pct of the -2.000 pct target over 170 '
  'cycles with 0 cycles more than 0.25 pct off. DTE-0 LEGS ARE SKIPPED_EXPIRY per the S62 house rule: '
  'leg_atm_iv, leg_skew_98, iv and iv_over_atm are withheld while ce_iv and pe_iv are KEPT so the '
  'degradation stays inspectable. Measured S83, ATM iv on the front leg averages 17.07 across dte-0 '
  'session cycles but collapses to 0.89 at the post-expiry 15:40 cycle, so the collapse is an '
  'end-of-session event rather than a property of the whole expiry day -- the rule is right, for a '
  'narrower reason than it first appears. WING QUALITY IS POOR AND NEAR-MONEY QUALITY IS PERFECT ON '
  'NIFTY ONLY: the three central buckets carry 0 pct absent and 0 outliers on TWO of four legs, both of'
  ' them NIFTY; the SENSEX back leg shows 3 over-3x-ATM and 2 adjacent jumps in the -2 to -0.5 pct '
  'bucket, and the SENSEX front leg fails all three central buckets. The wings run 33 to 89 pct absent,'
  ' and the strike range is far wider than the eye expects -- the NIFTY front leg spans -93.5 pct to '
  '+114.6 pct of spot with a maximum step of 1500. OUTLIERS ARE NOT ALL DEAD STRIKES: 14 of the 20 '
  'worst by iv over ATM carry oi = 0, and the six with real open interest are the NIFTY front leg at '
  '26300 PE and 28500 PE plus the SENSEX back leg at 72100 to 72400 CE. ALL TWENTY SIT ON THE ITM SIDE,'
  ' so the OTM convention excludes every one of them; that, not the open-interest count, is why they do'
  ' not reach iv. The high open-interest case is the SENSEX back leg at 72100 to 72400 CE, 1.6 to 2.0 '
  'pct in the money, reading iv 110 to 117 against an ATM of 13.1 while holding 48.7 million open '
  'interest, including a 92.14 point jump between adjacent strikes. oi_otm and iv_over_atm are '
  'published so that row is visible rather than silently rendered. THIS VIEW IS LIVE-ONLY: it reads one'
  ' cycle per symbol and holds no history, so the parity target history horizon, including any gap that'
  ' must render as absence rather than being interpolated, is NOT addressed here and no claim about it '
  'is made by this view.';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- TD-S81-NEW-5, CASE-2026-09-22)
-- REVOKE FIRST, then GRANT. S39 revoked instances and left Supabase
-- DEFAULT PRIVILEGES untouched, so every object created afterwards came
-- up with ALL again. Order matters.
-- =====================================================================

REVOKE ALL ON public.v_iv_surface FROM anon;

GRANT SELECT ON public.v_iv_surface TO anon;

GRANT SELECT ON public.v_iv_surface TO merdian_ro;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run after 1-3; each is a real check)
-- =====================================================================

-- V1  Mesh size. Expected 876 rows: NIFTY 268 + 230, SENSEX 196 + 182.
-- SELECT symbol, leg, expiry_date, dte, count(*) AS n
--   FROM public.v_iv_surface GROUP BY symbol, leg, expiry_date, dte
--  ORDER BY symbol, leg;

-- V2  Non-null iv. Expected 674 (789 OTM-quoted, less the dte-0 leg).
-- SELECT count(*) FILTER (WHERE iv IS NOT NULL) AS iv_not_null,
--        count(*) FILTER (WHERE quote_state = 'OTM_QUOTED') AS otm_quoted,
--        count(*) AS total FROM public.v_iv_surface;

-- V3  leg_atm_iv must equal v_iv_term_structure.atm_iv per leg, |d| < 1e-9.
-- SELECT s.symbol, s.leg, max(s.leg_atm_iv) AS surface, max(t.atm_iv) AS term,
--        abs(max(s.leg_atm_iv) - max(t.atm_iv)) AS d
--   FROM public.v_iv_surface s
--   LEFT JOIN public.v_iv_term_structure t
--     ON t.symbol = s.symbol AND t.ts = s.ts AND t.leg = s.leg
--  GROUP BY s.symbol, s.leg ORDER BY s.symbol, s.leg;

-- V4  side_used must be PE below spot and CE at or above. Expected 0 rows.
-- SELECT count(*) FROM public.v_iv_surface
--  WHERE (strike <  spot AND side_used <> 'PE')
--     OR (strike >= spot AND side_used <> 'CE');

-- V5  ANON PATH, not object existence. TD-S81-NEW-5: a GRANT skipped at
--     apply time leaves the view live and anon-unreadable, which returns
--     HTTP 200 with zero rows and is indistinguishable from no data.
-- SET ROLE anon; SELECT count(*) FROM public.v_iv_surface; RESET ROLE;

-- V6  COMMENT actually landed (a part-run apply is the S79 failure).
-- SELECT length(obj_description('public.v_iv_surface'::regclass,'pg_class')) AS comment_len,
--        md5(obj_description('public.v_iv_surface'::regclass,'pg_class'))    AS comment_md5;

-- V7  Latency. ADR-021. Expected well under the PostgREST 8 s ceiling.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_iv_surface;
