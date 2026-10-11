-- S95 / P5 follow-up -- how much of each front book sits on legs with NO volume all session, and
-- how far the vendor OI on those legs moves within the session. Read-only. Measures; decides nothing.
-- Per (symbol, session) for the last 10 sessions: legs whose last snapshot of the day shows volume 0,
-- their share of front-expiry OI and of gross |vendor delta x oi x spot / 1e7| at that snapshot,
-- and how many of them changed OI during the session (OI cannot change without a trade).
WITH syms(symbol) AS (VALUES ('NIFTY'::text), ('SENSEX'::text)
), sess AS MATERIALIZED (
  SELECT tc.trade_date AS d
    FROM trading_calendar tc
   WHERE tc.is_open AND tc.trade_date BETWEEN DATE '2026-09-24' AND DATE '2026-10-09'
), k AS MATERIALIZED (
  SELECT s.symbol, x.d,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = s.symbol
        AND o.ts >= ((x.d + time '09:15') AT TIME ZONE 'Asia/Kolkata')
        AND o.ts <  (((x.d + 1) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts LIMIT 1) AS t0915,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = s.symbol
        AND o.ts >= ((x.d + time '00:00') AT TIME ZONE 'Asia/Kolkata')
        AND o.ts <  (((x.d + 1) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts DESC LIMIT 1) AS last_ts
  FROM syms s CROSS JOIN sess x
), kf AS MATERIALIZED (
  SELECT k.*,
    (SELECT min(o.expiry_date) FROM option_chain_snapshots o
      WHERE o.symbol = k.symbol AND o.ts = k.t0915 AND o.expiry_date >= k.d) AS expiry_date
  FROM k
), l AS MATERIALIZED (
  SELECT kf.symbol, kf.d, o.strike, o.option_type, o.oi, o.volume,
         abs(o.delta * o.oi * o.spot / 1e7) AS dex_abs
    FROM kf JOIN option_chain_snapshots o
      ON o.symbol = kf.symbol AND o.ts = kf.last_ts AND o.expiry_date = kf.expiry_date
), a AS MATERIALIZED (
  SELECT kf.symbol, kf.d, o.strike, o.option_type, o.oi
    FROM kf JOIN option_chain_snapshots o
      ON o.symbol = kf.symbol AND o.ts = kf.t0915 AND o.expiry_date = kf.expiry_date
)
SELECT l.symbol, l.d,
       count(*)                                                        AS n_legs,
       count(*) FILTER (WHERE l.volume = 0)                            AS n_vol0,
       count(*) FILTER (WHERE l.volume = 0 AND l.oi > 0)               AS n_vol0_oi,
       count(*) FILTER (WHERE l.volume = 0 AND a.oi IS DISTINCT FROM l.oi) AS n_vol0_oi_moved,
       round(100.0 * sum(l.oi) FILTER (WHERE l.volume = 0) / nullif(sum(l.oi), 0), 2)       AS pct_oi_vol0,
       round(100.0 * sum(l.dex_abs) FILTER (WHERE l.volume = 0) / nullif(sum(l.dex_abs), 0), 2) AS pct_dex_gross_vol0,
       max(l.oi) FILTER (WHERE l.volume = 0)                           AS max_oi_vol0
  FROM l
  LEFT JOIN a ON a.symbol = l.symbol AND a.d = l.d AND a.strike = l.strike AND a.option_type = l.option_type
 GROUP BY l.symbol, l.d
 ORDER BY l.symbol, l.d;
