-- S100-J (2026-10-24, applied by the operator in the Supabase SQL editor ~09:59 IST): R23 / TD-S97-NEW-15.
-- data_contamination_ranges.symbols text[], NULL = all symbols; CHECK NULL or a non-empty subset of {NIFTY,SENSEX}.
-- Backfill: SENSEX-CHAIN-OI-VOL0-2026-09-25 = {SENSEX}; the other 3 rows NULL. The DO block is a must-fail probe:
-- the CHECK must refuse {Sensex}, else the batch raises and rolls back. Result: 4 rows as designed; via merdian_ro
-- n 4 / scoped 1 / matches_nifty 3 / matches_sensex 4. Rule 13: symbols IS NULL OR <study symbol> = ANY(symbols).
BEGIN;
ALTER TABLE public.data_contamination_ranges ADD COLUMN IF NOT EXISTS symbols text[];
ALTER TABLE public.data_contamination_ranges
  ADD CONSTRAINT data_contamination_ranges_symbols_chk
  CHECK (symbols IS NULL OR (cardinality(symbols) > 0 AND symbols <@ ARRAY['NIFTY','SENSEX']::text[]));
COMMENT ON COLUMN public.data_contamination_ranges.symbols IS
  'S100-J: symbols the range applies to; NULL = all. Rule 13: symbols IS NULL OR <study symbol> = ANY(symbols).';
UPDATE public.data_contamination_ranges SET symbols = ARRAY['SENSEX']
 WHERE contamination_id = 'SENSEX-CHAIN-OI-VOL0-2026-09-25' AND symbols IS NULL;
DO $$
BEGIN
  BEGIN
    UPDATE public.data_contamination_ranges SET symbols = ARRAY['Sensex']
     WHERE contamination_id = 'SENSEX-CHAIN-OI-VOL0-2026-09-25';
    RAISE EXCEPTION 'S100-J PROBE FAIL: CHECK accepted {Sensex}';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'S100-J probe: {Sensex} refused by the CHECK';
  END;
END $$;
COMMIT;
NOTIFY pgrst, 'reload schema';
SELECT contamination_id, symbols FROM public.data_contamination_ranges ORDER BY contamination_start;
