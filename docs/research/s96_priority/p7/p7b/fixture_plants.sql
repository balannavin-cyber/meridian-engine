-- plants at the latest ts, NIFTY front leg (2026-10-13): copy the ATM CE/PE rows of that ts to new strikes
WITH lt AS (SELECT max(ts) AS ts FROM option_chain_snapshots WHERE symbol = 'NIFTY'),
     atm AS (SELECT o.* FROM option_chain_snapshots o, lt
              WHERE o.symbol = 'NIFTY' AND o.ts = lt.ts AND o.expiry_date = '2026-10-13'
                AND o.strike = (SELECT strike FROM option_chain_snapshots o2, lt l2
                                 WHERE o2.symbol='NIFTY' AND o2.ts=l2.ts AND o2.expiry_date='2026-10-13'
                                 ORDER BY abs(o2.strike - o2.spot) LIMIT 1))
INSERT INTO option_chain_snapshots (ts, symbol, expiry_date, spot, strike, option_type, ltp, oi, delta, iv, gamma, volume, run_id, oi_change)
SELECT ts, symbol, expiry_date, spot, round(spot * 1.08 / 50) * 50, option_type, ltp, oi, delta, iv, 1e-4, volume, run_id, oi_change FROM atm   -- guarded: far, gamma 1e-4
UNION ALL
SELECT ts, symbol, expiry_date, spot, round(spot * 0.92 / 50) * 50, option_type, ltp, oi, delta, iv, 1e-6, volume, run_id, oi_change FROM atm   -- far, small gamma: kept
UNION ALL
SELECT ts, symbol, expiry_date, spot, strike + 25, option_type, ltp, 0, delta, iv, gamma, volume, run_id, 0 FROM atm;                            -- oi 0: priceable, not in leg set
