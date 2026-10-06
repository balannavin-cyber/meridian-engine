-- S90 / AM-1 — per-product session end on data_contracts (operator ruling 2026-10-06 20:05 IST).
--
-- Why: capture_spot_1m_v2.py stops at 15:14 IST by design (MARKET_CLOSE_GUARD, ADR-022: the
-- index freezes 15:15-15:29 during the closing auction and the vendor returns nothing), so the
-- spot contract read MISSING at the 15:20 and 15:25 cycles every trading day. The runner
-- (check_contracts_shadow.py, S90_SESSION_END) judges freshness AS OF session_end_ist once that
-- time has passed; a feed that died before it still reads MISSING. NULL keeps the 15:30 session.
-- If SEBI moves the cash close, this is a one-row UPDATE, not a deploy.
--
-- Apply in the Supabase SQL editor (postgres), as ONE execution. Rollback at the bottom.
-- The column inherits data_contracts' table grants (merdian_ro SELECT); no new grant needed.

ALTER TABLE public.data_contracts ADD COLUMN IF NOT EXISTS session_end_ist time;

COMMENT ON COLUMN public.data_contracts.session_end_ist IS
  'S90. Intraday product whose writer stops before the market closes: freshness is judged as of this IST time once it has passed. NULL = the 15:30 session. Spot = 15:15 (capture ends 15:14 under CAS, ADR-022).';

DO $$
DECLARE n int;
BEGIN
  UPDATE public.data_contracts
     SET session_end_ist = time '15:15',
         valid_from      = now(),
         change_reason   = change_reason || ' | S90 2026-10-06: session_end_ist 15:15 (capture ends 15:14 under CAS; operator ruling)'
   WHERE product IN ('market_spot_snapshots:NIFTY', 'market_spot_snapshots:SENSEX')
     AND valid_to IS NULL
     AND session_end_ist IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 2 THEN
    RAISE EXCEPTION 'S90 session end: expected 2 spot contracts, updated %', n;
  END IF;
END $$;

SELECT product, session_end_ist, valid_from, right(change_reason, 90) AS change_reason_tail
  FROM public.data_contracts
 WHERE session_end_ist IS NOT NULL
 ORDER BY product;

-- ROLLBACK (only if needed):
-- UPDATE public.data_contracts SET session_end_ist = NULL
--  WHERE product IN ('market_spot_snapshots:NIFTY', 'market_spot_snapshots:SENSEX');
-- (the runner treats NULL exactly as before this change; the column can stay)
