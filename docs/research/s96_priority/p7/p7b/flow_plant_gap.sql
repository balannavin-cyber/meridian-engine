-- a side whose OI moved but whose iv is 0 at the latest ts (unpriceable): its dOI must land in the gap
UPDATE option_chain_snapshots SET iv = 0 WHERE symbol='SENSEX' AND expiry_date='2026-10-15' AND option_type='CE'
   AND ts=(SELECT max(ts) FROM option_chain_snapshots WHERE symbol='SENSEX')
   AND strike=(SELECT strike FROM option_chain_snapshots WHERE symbol='SENSEX' AND expiry_date='2026-10-15'
                 AND ts=(SELECT max(ts) FROM option_chain_snapshots WHERE symbol='SENSEX') AND option_type='CE' AND iv > 0
               ORDER BY abs(strike-spot) LIMIT 1);
