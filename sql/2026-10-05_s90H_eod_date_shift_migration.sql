-- S90-H — move every equity_eod / breadth_indicators_daily trade_date forward one day.
-- SQL editor, postgres, ONE execution. Run ONLY after:
--   (a) the catch-up sweep has finished (no run_equity_eod_until_done process), and
--   (b) the ingest IST-date patch is deployed (S90_EOD_IST_DATE), so no new shifted rows arrive.
-- Every gate RAISEs, so any failure rolls the whole transaction back (backups included).
BEGIN;
SET LOCAL statement_timeout = 0;

-- Pre-gate: the tables must be uniformly shifted (no Friday rows anywhere).
DO $pre$
DECLARE fri_e bigint; fri_b bigint;
BEGIN
  SELECT count(*) INTO fri_e FROM public.equity_eod WHERE extract(isodow FROM trade_date) = 5;
  SELECT count(*) INTO fri_b FROM public.breadth_indicators_daily WHERE extract(isodow FROM trade_date) = 5;
  IF fri_e > 0 OR fri_b > 0 THEN
    RAISE EXCEPTION 'S90-H pre-gate: Friday rows exist (equity_eod %, breadth %) - not uniformly shifted', fri_e, fri_b;
  END IF;
END
$pre$;

-- Backups (same transaction: they exist only if the migration commits).
CREATE TABLE public.equity_eod_bak_s90_20261005 AS SELECT * FROM public.equity_eod;
CREATE TABLE public.breadth_indicators_daily_bak_s90_20261005 AS SELECT * FROM public.breadth_indicators_daily;
REVOKE ALL ON public.equity_eod_bak_s90_20261005, public.breadth_indicators_daily_bak_s90_20261005 FROM anon, authenticated;
COMMENT ON TABLE public.equity_eod_bak_s90_20261005 IS 'S90-H backup before trade_date +1 (R01-F10). Drop after one clean week.';
COMMENT ON TABLE public.breadth_indicators_daily_bak_s90_20261005 IS 'S90-H backup before trade_date +1 (R01-F10). Drop after one clean week.';

-- Shift in two steps so no intermediate row collides with the primary/unique key.
UPDATE public.equity_eod               SET trade_date = trade_date + 100000;
UPDATE public.equity_eod               SET trade_date = trade_date - 99999;
UPDATE public.breadth_indicators_daily SET trade_date = trade_date + 100000;
UPDATE public.breadth_indicators_daily SET trade_date = trade_date - 99999;

-- Post-gates.
DO $post$
DECLARE n_e bigint; n_eb bigint; n_b bigint; n_bb bigint;
        sun bigint; sat bigint; fri bigint; mism bigint;
BEGIN
  SELECT count(*) INTO n_e  FROM public.equity_eod;
  SELECT count(*) INTO n_eb FROM public.equity_eod_bak_s90_20261005;
  SELECT count(*) INTO n_b  FROM public.breadth_indicators_daily;
  SELECT count(*) INTO n_bb FROM public.breadth_indicators_daily_bak_s90_20261005;
  IF n_e <> n_eb OR n_b <> n_bb THEN
    RAISE EXCEPTION 'S90-H: row counts changed (eod % vs %, breadth % vs %)', n_e, n_eb, n_b, n_bb;
  END IF;
  SELECT count(*) FILTER (WHERE extract(isodow FROM trade_date) = 7 AND trade_date <> '2026-02-01'),
         count(*) FILTER (WHERE extract(isodow FROM trade_date) = 6),
         count(*) FILTER (WHERE extract(isodow FROM trade_date) = 5)
    INTO sun, sat, fri FROM public.equity_eod;
  IF sun > 0 OR sat > 0 OR fri = 0 THEN
    RAISE EXCEPTION 'S90-H: weekday shape wrong after shift (Sun % excl 02-01, Sat %, Fri %)', sun, sat, fri;
  END IF;
  SELECT count(*) INTO mism
  FROM public.equity_eod_bak_s90_20261005 b
  LEFT JOIN public.equity_eod e ON e.ticker = b.ticker AND e.trade_date = b.trade_date + 1
  WHERE e.ticker IS NULL OR e.close IS DISTINCT FROM b.close;
  IF mism > 0 THEN
    RAISE EXCEPTION 'S90-H: % backup rows do not map to (+1 day, same close)', mism;
  END IF;
END
$post$;

COMMIT;

-- Evidence (last result shown).
SELECT 'equity_eod' AS rel, to_char(trade_date,'Dy') AS dow, count(*) AS n, min(trade_date) AS first, max(trade_date) AS last
FROM public.equity_eod GROUP BY 2
UNION ALL
SELECT 'breadth_daily', to_char(trade_date,'Dy'), count(*), min(trade_date), max(trade_date)
FROM public.breadth_indicators_daily GROUP BY 2
ORDER BY 1, 3 DESC;
