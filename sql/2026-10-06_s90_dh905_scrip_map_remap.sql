-- S90 (AM-1) DH-905 — dhan_scrip_map stale security IDs. RECORD OF WHAT RAN, 2026-10-06 05:05–05:16 IST.
-- Supabase SQL editor, as postgres. Finding and evidence: docs/research/s90_agentic/DH-905_scrip_map_remap_S90.md
--
-- How it actually landed (recorded because the first attempt is the lesson, §D.46.8):
--  1. A BEGIN / CREATE TEMP TABLE ... ON COMMIT DROP / INSERT / DO-gate / UPDATE / DO-post / COMMIT script was run.
--     The editor returned `42P01 relation "dh905_remap" does not exist`. The 18 remaps below had nevertheless
--     LANDED (verified row by row with merdian_ro: every symbol on its new id, is_active = true).
--     The editor does not run such a script as one transaction with one session; do not rely on it.
--  2. A single-DO-block retry then failed its first gate (0 of 18 rows on the old ids) — because step 1 had applied.
--  3. The three deactivations ran as the single DO block below. Post-check (merdian_ro, 05:16 IST):
--     active NSE map rows whose id is not an NSE segment-E row in dhan_scripmaster = 0.
--
-- Remaps applied in step 1 (symbol, old id -> new id; master series in brackets):
--   ABINFRA 27020->27016 [BE] · AIMTRON 23987->23984 [SM] · ANURAS 23687->2829 [EQ] · BESTAGRO 2311->2306 [EQ]
--   BFUTILITIE 25879->14567 [EQ] · BGRENERGY 15189->15193 [BE] · BLISSGVS 19265->19269 [BE] · CHOLAFIN 19257->685 [EQ]
--   DIACABS 18543->18545 [BE] · E2E 8937->8940 [BE] · EMBDL 14453->14450 [EQ] · ESAFSFB 19878->19884 [BE]
--   HFCL 21951->21954 [BE] · LOTUSDEV 758145->758147 [BE] · MICEL 7169->7165 [BE] · RAJOOENG 757049->757052 [BE]
--   RMDRIP 757834->757836 [BE] · RNBDENIMS 758981->758984 [BE]
-- Earlier, 2026-10-05 (the 11 that failed the EOD ingest; SQL not preserved in the tree, recorded by result):
--   MTARTECH->2715 · RAMASTEEL->10304 · SPECTRUM->30457 · STALLION->29205 · STLTECH->9313 · SYSTMTXC->759358
--   TAC->23441 · TBZ->27041 · TIL->9802 · WAAREEINDO->19955 · SANGHIIND deactivated.
--
-- The pattern for gated multi-step writes in the editor is ONE DO block (one statement):

DO $dh905b$
DECLARE n int;
BEGIN
  UPDATE public.dhan_scrip_map SET is_active = false
  WHERE is_active
    AND (trading_symbol, dhan_security_id) IN
        (('GSPL','13197'),('JBCHEPHARM','1726'),('CIGNITITEC','5142'));
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 3 THEN
    RAISE EXCEPTION 'DH-905 deactivate: % rows (want 3)', n;
  END IF;
END
$dh905b$;

-- Evidence (merdian_ro):
-- SELECT count(*) AS still_unmapped FROM public.dhan_scrip_map m
-- WHERE m.is_active AND m.exchange = 'NSE' AND m.dhan_security_id IS NOT NULL
--   AND NOT EXISTS (SELECT 1 FROM public.dhan_scripmaster s
--                   WHERE s."EXCH_ID" = 'NSE' AND s."SEGMENT" = 'E'
--                     AND s."SECURITY_ID"::text = m.dhan_security_id);
-- => 0
