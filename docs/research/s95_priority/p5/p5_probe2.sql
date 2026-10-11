-- S95 / P5 probe 2 -- cost of the prev-close anchor seek for the CURRENT session.
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
WITH latest AS (
  SELECT (SELECT o.ts FROM option_chain_snapshots o WHERE o.symbol = 'SENSEX' ORDER BY o.ts DESC LIMIT 1) AS ts
)
SELECT (SELECT o.ts FROM option_chain_snapshots o, latest l
         WHERE o.symbol = 'SENSEX'
           AND o.ts < ((((l.ts AT TIME ZONE 'Asia/Kolkata')::date) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
           AND NOT EXISTS (SELECT 1 FROM trading_calendar c
                            WHERE c.trade_date = (o.ts AT TIME ZONE 'Asia/Kolkata')::date
                              AND NOT c.is_open)
         ORDER BY o.ts DESC LIMIT 1) AS prev_open;
