-- guard_cycles.sql -- S96 / TD-S95-NEW-1 (c): how much of the front DEX book sits on suspect legs, per cycle.
-- READ-ONLY, descriptive. Reads no price outcome; decides nothing. One row per (symbol, cycle ts) of the
-- front expiry in [09:15, 15:15] IST on a session where the tape moved (ENH-140 clause 2) and no explicit
-- trading_calendar closure (clause 1). Date :'d'.
-- Signatures, evaluated AT THE CYCLE (what a live guard could see then):
--   S1 = volume = 0 so far (or NULL volume) on a leg with oi > 0
--   S2 = S1 AND oi_change = oi   (the vendor says all of today's OI is new, yet nothing traded: impossible)
-- Gross = |delta x oi x spot / 1e7| over legs with a usable delta (ENH-140 gap rule), so a share is a share of
-- the book the board actually draws. oi totals are over all legs.
-- Run: { printf "\\set d '%s'\n" 2026-09-25; cat guard_cycles.sql; } | bin/roq.sh
\set QUIET on
\pset format csv
WITH RECURSIVE syms AS (
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c) AS symbol
        UNION ALL
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c WHERE c.symbol > s.symbol)
          FROM syms s WHERE s.symbol IS NOT NULL
     ), sess AS MATERIALIZED (
        SELECT s.symbol, (:'d')::date AS session_date
          FROM syms s
         WHERE s.symbol IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM public.trading_calendar tc
                            WHERE tc.trade_date = (:'d')::date AND tc.is_open = false)
           AND (SELECT count(DISTINCT m.spot) FROM public.market_spot_snapshots m
                 WHERE m.symbol = s.symbol
                   AND m.ts >= ((:'d')::date::timestamp AT TIME ZONE 'Asia/Kolkata')
                   AND m.ts <= (((:'d')::date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')) > 1
     ), fr AS MATERIALIZED (
        SELECT x.symbol, x.session_date,
               (SELECT min(e.expiry_date)
                  FROM (SELECT DISTINCT c.expiry_date FROM public.option_chain_snapshots c
                         WHERE c.symbol = x.symbol
                           AND c.ts >= (x.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                           AND c.ts <= ((x.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
                           AND c.expiry_date >= x.session_date) e) AS expiry_date
          FROM sess x
     ), cycles AS MATERIALIZED (
        SELECT f.symbol, f.session_date, f.expiry_date, t.ts
          FROM fr f
          CROSS JOIN LATERAL (
               SELECT DISTINCT c.ts FROM public.option_chain_snapshots c
                WHERE c.symbol = f.symbol AND c.expiry_date = f.expiry_date
                  AND c.ts >= ((f.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
                  AND c.ts <= ((f.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
          ) t
         WHERE f.expiry_date IS NOT NULL
     ), px AS (
        SELECT y.symbol, y.session_date, y.expiry_date, y.ts,
               c.oi, c.oi_change, c.volume, c.delta, c.iv, c.spot,
               (c.delta IS NULL OR (c.delta = 0 AND COALESCE(c.iv, 0) = 0)) AS gap,
               (COALESCE(c.oi, 0) > 0 AND COALESCE(c.volume, 0) = 0)        AS s1
          FROM cycles y
          JOIN public.option_chain_snapshots c
            ON c.symbol = y.symbol AND c.expiry_date = y.expiry_date AND c.ts = y.ts
     ), q AS (
        SELECT p.*, (p.s1 AND p.oi_change = p.oi) AS s2,
               CASE WHEN p.gap OR COALESCE(p.oi, 0) = 0 THEN 0 ELSE abs(p.delta * p.oi * p.spot / 1e7) END AS g
          FROM px p
     )
SELECT symbol, session_date, expiry_date, (expiry_date - session_date) AS dte,
       to_char(ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS cycle_ist,
       count(*)                                   AS n_legs,
       count(*) FILTER (WHERE volume IS NULL)     AS n_vol_null,
       count(*) FILTER (WHERE s1)                 AS n_s1,
       count(*) FILTER (WHERE s2)                 AS n_s2,
       sum(COALESCE(oi, 0))                       AS oi_all,
       sum(COALESCE(oi, 0)) FILTER (WHERE s1)     AS oi_s1,
       sum(COALESCE(oi, 0)) FILTER (WHERE s2)     AS oi_s2,
       sum(g)                                     AS gross_all,
       sum(g) FILTER (WHERE s1)                   AS gross_s1,
       sum(g) FILTER (WHERE s2)                   AS gross_s2
  FROM q
 GROUP BY symbol, session_date, expiry_date, ts
 ORDER BY symbol, ts;
