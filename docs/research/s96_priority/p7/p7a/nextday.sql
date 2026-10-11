INSERT INTO option_chain_snapshots (ts,symbol,expiry_date,spot,strike,option_type,oi,delta,iv)
SELECT '2026-10-12 08:35:00+05:30', symbol, expiry_date, spot, strike, option_type, oi, delta, iv
  FROM option_chain_snapshots WHERE ts = '2026-10-09 15:40:00+05:30' AND expiry_date >= '2026-10-12';
