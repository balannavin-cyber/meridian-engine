-- fixture case for the oi(settled) = 0 gap branch: one deep-ITM NIFTY PE (vendor greeks dropped) whose OI went to 0 by 15:15
UPDATE option_chain_snapshots SET oi = 0
 WHERE symbol='NIFTY' AND ts='2026-10-09 15:15:00+05:30' AND option_type='PE' AND strike=25500 AND expiry_date='2026-10-13';
SELECT strike, oi, delta, iv FROM option_chain_snapshots WHERE symbol='NIFTY' AND option_type='PE' AND strike=25500 AND expiry_date='2026-10-13'
   AND ts IN ('2026-10-09 08:35:00+05:30','2026-10-09 15:15:00+05:30') ORDER BY ts;
