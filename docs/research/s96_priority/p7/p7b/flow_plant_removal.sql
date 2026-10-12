-- a side with anchor OI closed to zero at the latest ts (gamma and iv kept: priceable, not in the leg set)
UPDATE option_chain_snapshots SET oi = 0 WHERE symbol='NIFTY' AND expiry_date='2026-10-13' AND option_type='PE'
   AND ts=(SELECT max(ts) FROM option_chain_snapshots WHERE symbol='NIFTY')
   AND strike=(SELECT strike FROM option_chain_snapshots WHERE symbol='NIFTY' AND expiry_date='2026-10-13'
                 AND ts=(SELECT max(ts) FROM option_chain_snapshots WHERE symbol='NIFTY') AND option_type='PE' AND oi > 0 AND iv > 0
               ORDER BY abs(strike-spot) LIMIT 1);
