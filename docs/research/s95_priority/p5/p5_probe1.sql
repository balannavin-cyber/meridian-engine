-- S95 / P5 (PPC-1) probe 1 -- read-only, merdian_ro via bin/roq.sh. MEASURES; decides nothing.
WITH sess AS MATERIALIZED (
  SELECT tc.trade_date AS d
    FROM trading_calendar tc
   WHERE tc.is_open
     AND tc.trade_date BETWEEN DATE '2026-08-25' AND DATE '2026-10-09'
), syms(symbol) AS (VALUES ('NIFTY'::text), ('SENSEX'::text)
), k AS MATERIALIZED (
  SELECT s.symbol, x.d,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = s.symbol
        AND o.ts >= ((x.d + time '00:00') AT TIME ZONE 'Asia/Kolkata')
        AND o.ts <  (((x.d + 1) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts LIMIT 1) AS first_ts,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = s.symbol
        AND o.ts >= ((x.d + time '09:15') AT TIME ZONE 'Asia/Kolkata')
        AND o.ts <  (((x.d + 1) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts LIMIT 1) AS t0915,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = s.symbol
        AND o.ts < ((x.d + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts DESC LIMIT 1) AS prev_naive,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = s.symbol
        AND o.ts < ((x.d + time '00:00') AT TIME ZONE 'Asia/Kolkata')
        AND NOT EXISTS (SELECT 1 FROM trading_calendar c
                         WHERE c.trade_date = (o.ts AT TIME ZONE 'Asia/Kolkata')::date
                           AND NOT c.is_open)
      ORDER BY o.ts DESC LIMIT 1) AS prev_open
  FROM syms s CROSS JOIN sess x
), kf AS MATERIALIZED (
  SELECT k.*,
    (SELECT min(o.expiry_date) FROM option_chain_snapshots o
      WHERE o.symbol = k.symbol AND o.ts = k.t0915 AND o.expiry_date >= k.d) AS expiry_date
  FROM k
), p AS MATERIALIZED (
  SELECT kf.symbol, kf.d, o.strike, o.option_type, o.oi
    FROM kf JOIN option_chain_snapshots o
      ON o.symbol = kf.symbol AND o.ts = kf.prev_open AND o.expiry_date = kf.expiry_date
), f AS MATERIALIZED (
  SELECT kf.symbol, kf.d, o.strike, o.option_type, o.oi
    FROM kf JOIN option_chain_snapshots o
      ON o.symbol = kf.symbol AND o.ts = kf.first_ts AND o.expiry_date = kf.expiry_date
), n AS MATERIALIZED (
  SELECT kf.symbol, kf.d, o.strike, o.option_type, o.oi
    FROM kf JOIN option_chain_snapshots o
      ON o.symbol = kf.symbol AND o.ts = kf.t0915 AND o.expiry_date = kf.expiry_date
), cmp AS (
  SELECT p.symbol, p.d,
         count(*)                                                  AS n_prev,
         count(f.oi)                                               AS n_pf,
         count(*) FILTER (WHERE f.oi IS NOT NULL AND f.oi <> p.oi) AS n_pf_ne,
         max(abs(f.oi - p.oi))                                     AS max_pf,
         count(n.oi)                                               AS n_pn,
         count(*) FILTER (WHERE n.oi IS NOT NULL AND n.oi <> p.oi) AS n_pn_ne,
         max(abs(n.oi - p.oi))                                     AS max_pn
    FROM p
    LEFT JOIN f ON f.symbol = p.symbol AND f.d = p.d AND f.strike = p.strike AND f.option_type = p.option_type
    LEFT JOIN n ON n.symbol = p.symbol AND n.d = p.d AND n.strike = p.strike AND n.option_type = p.option_type
   GROUP BY p.symbol, p.d
), nn AS (
  SELECT symbol, d, count(*) AS n_0915 FROM n GROUP BY symbol, d
)
SELECT kf.symbol,
       kf.d,
       to_char(kf.first_ts   AT TIME ZONE 'Asia/Kolkata', 'MM-DD HH24:MI') AS first_ist,
       to_char(kf.t0915      AT TIME ZONE 'Asia/Kolkata', 'MM-DD HH24:MI') AS t0915_ist,
       to_char(kf.prev_naive AT TIME ZONE 'Asia/Kolkata', 'MM-DD HH24:MI') AS prev_naive_ist,
       to_char(kf.prev_open  AT TIME ZONE 'Asia/Kolkata', 'MM-DD HH24:MI') AS prev_open_ist,
       kf.expiry_date,
       c.n_prev, nn.n_0915, c.n_pf, c.n_pf_ne, c.max_pf, c.n_pn, c.n_pn_ne, c.max_pn
  FROM kf
  LEFT JOIN cmp c ON c.symbol = kf.symbol AND c.d = kf.d
  LEFT JOIN nn    ON nn.symbol = kf.symbol AND nn.d = kf.d
 ORDER BY kf.symbol, kf.d;
