\pset format aligned
-- Visibility check on public.fyers_futures_bars_1m after the 2026-11-20 grant + policy.
--
-- WHAT THIS MUST DISTINGUISH: an empty result from row security hiding every row. Those
-- are identical in a result set alone, so the catalog estimate -- which is NOT privilege-
-- or policy-filtered -- is carried in the SAME result set as the visible count. Reading
-- them from two separate queries would not settle it (S84: a role-scoped check runs in
-- ONE execution).
--
-- WHAT THIS QUERY GUARANTEES: it returns AT LEAST ONE ROW in every case, because the
-- final SELECT is driven from a one-row source and every other relation is LEFT JOINed
-- to it. So the three outcomes are distinguishable on the face of the output:
--   underlying NULL, visible_underlyings 0, catalog_est_rows_unfiltered > 0
--       -> row security (or the grant) is hiding every row from this role
--   underlying NULL, visible_underlyings 0, catalog_est_rows_unfiltered 0
--       -> the relation is genuinely empty
--   one row per underlying with first/last ts, visible_underlyings > 0
--       -> rows are visible; the ts range is the answer
-- An earlier draft drove the final SELECT from the underlying list itself, so an RLS
-- blackout returned zero rows and suppressed the catalog column -- destroying exactly the
-- comparison the query exists to make.
--
-- NO TABLE SCAN. Both existing indexes lead with `underlying` (from the IDX lines of
-- _q10.txt: (underlying, expiry_date, ts) and (underlying, ts)), so the distinct
-- underlyings are walked by a recursive loose index scan -- one index probe per distinct
-- value, never a scan of the 795,544 rows -- and each value's first and last ts come from
-- ORDER BY ts LIMIT 1 on the (underlying, ts) index, forward and backward.
WITH RECURSIVE u AS (
    SELECT (SELECT f.underlying
              FROM fyers_futures_bars_1m f
             ORDER BY f.underlying
             LIMIT 1) AS underlying
  UNION ALL
    SELECT (SELECT f.underlying
              FROM fyers_futures_bars_1m f
             WHERE f.underlying > u.underlying
             ORDER BY f.underlying
             LIMIT 1)
      FROM u
     WHERE u.underlying IS NOT NULL
), uu AS (
  SELECT underlying FROM u WHERE underlying IS NOT NULL
)
SELECT uu.underlying,
       lo.ts AT TIME ZONE 'UTC' AS first_ts_stored_clock,
       hi.ts AT TIME ZONE 'UTC' AS last_ts_stored_clock,
       lo.symbol      AS first_contract_symbol,
       lo.expiry_date AS first_expiry,
       hi.expiry_date AS last_expiry,
       (SELECT count(*) FROM uu) AS visible_underlyings,
       (SELECT c.reltuples::bigint
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relname = 'fyers_futures_bars_1m'
       ) AS catalog_est_rows_unfiltered
  FROM (SELECT 1) one
  LEFT JOIN uu ON true
  LEFT JOIN LATERAL (
    SELECT f.ts, f.symbol, f.expiry_date
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = uu.underlying
     ORDER BY f.ts
     LIMIT 1
  ) lo ON true
  LEFT JOIN LATERAL (
    SELECT f.ts, f.expiry_date
      FROM fyers_futures_bars_1m f
     WHERE f.underlying = uu.underlying
     ORDER BY f.ts DESC
     LIMIT 1
  ) hi ON true
 ORDER BY uu.underlying NULLS LAST;
