-- S95 / P5 drill -- the two SENSEX outliers from probe 1 (09-25->09-28 max 48,846,700; 09-29->09-30 max 1,844,600).
-- For each changeover: the 3 legs with the largest |pre-open oi - previous 15:40 oi| on the front expiry,
-- then every snapshot of those legs from 15:00 on the previous session to 10:00 on the next.
-- Read-only. Decides nothing; shows which side carries the odd value.
WITH ch(prev_d, next_d, expiry_date) AS (VALUES
  (DATE '2026-09-25', DATE '2026-09-28', DATE '2026-10-01'),
  (DATE '2026-09-29', DATE '2026-09-30', DATE '2026-10-01')
), k AS MATERIALIZED (
  SELECT ch.*,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = 'SENSEX'
        AND o.ts <  (((ch.prev_d + 1) + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts DESC LIMIT 1) AS prev_ts,
    (SELECT o.ts FROM option_chain_snapshots o
      WHERE o.symbol = 'SENSEX'
        AND o.ts >= ((ch.next_d + time '00:00') AT TIME ZONE 'Asia/Kolkata')
      ORDER BY o.ts LIMIT 1) AS first_ts
  FROM ch
), legs AS (
  SELECT * FROM (
    SELECT k.prev_d, k.next_d, k.expiry_date, p.strike, p.option_type,
           f.oi - p.oi AS jump,
           row_number() OVER (PARTITION BY k.prev_d ORDER BY abs(f.oi - p.oi) DESC NULLS LAST) AS rk
      FROM k
      JOIN option_chain_snapshots p
        ON p.symbol = 'SENSEX' AND p.ts = k.prev_ts AND p.expiry_date = k.expiry_date
      JOIN option_chain_snapshots f
        ON f.symbol = 'SENSEX' AND f.ts = k.first_ts AND f.expiry_date = k.expiry_date
       AND f.strike = p.strike AND f.option_type = p.option_type
  ) x WHERE rk <= 3
)
SELECT l.prev_d, l.rk, l.strike, l.option_type, l.jump,
       to_char(o.ts AT TIME ZONE 'Asia/Kolkata', 'MM-DD HH24:MI') AS ts_ist,
       o.oi, o.oi_change, o.volume, o.ltp, o.spot
  FROM legs l
  JOIN option_chain_snapshots o
    ON o.symbol = 'SENSEX'
   AND o.expiry_date = l.expiry_date
   AND o.strike = l.strike
   AND o.option_type = l.option_type
   AND o.ts >= ((l.prev_d + time '15:00') AT TIME ZONE 'Asia/Kolkata')
   AND o.ts <  ((l.next_d + time '10:00') AT TIME ZONE 'Asia/Kolkata')
 ORDER BY l.prev_d, l.rk, o.ts;
