-- S97 applies (rulings S97-F, S97-G, S97-H, S97-M, S97-L) — applied by the operator in the
-- SQL editor 2026-10-12 / 10-22; reconstructed from the catalog 2026-10-23 (S98 C2) and
-- checked against it. Re-runnable: every statement is idempotent.
--
-- Reconstructed, NOT the original apply text. Every value below was read back out of the
-- live catalog, so this file reproduces the observed end state; it is not a transcript of
-- what was typed. The prose columns in section 3 were emitted by quote_nullable() from the
-- live rows rather than retyped, so they are exact including escaping.
--
-- Sections:
--   1. idx_gss_ts on gex_strike_snapshots            (S97-F; TD-S96-NEW-2)
--   2. gex_strike_snapshots.ts SET STATISTICS 1000   (S97-G; TD-S96-NEW-2)
--   3. two data_contamination_ranges rows            (S97-H, S97-M; Rule 13)
--   4. the two S90-H backup drops                    (S97-L; TD-S90-NEW-11)
--   5. closing verification SELECT

-- ---------------------------------------------------------------------------
-- 1. Planner fix: a ts-leading index. Both pre-existing indexes lead on symbol
--    ((symbol, ts DESC)), so a ts-only day predicate estimated rows=1 against an
--    actual 19,198 (TD-S96-NEW-2). TD-S72-NEW-4 re-observed 2026-10-12.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_gss_ts
    ON public.gex_strike_snapshots USING btree (ts);

-- ---------------------------------------------------------------------------
-- 2. Statistics target on the same column. ANALYZE is required for the new
--    target to take effect; it is idempotent and safe to re-run.
-- ---------------------------------------------------------------------------
ALTER TABLE public.gex_strike_snapshots ALTER COLUMN ts SET STATISTICS 1000;

ANALYZE public.gex_strike_snapshots;

-- ---------------------------------------------------------------------------
-- 3. Rule 13 contamination rows. id and created_at are deliberately NOT written:
--    id is the table's own sequence and created_at is the original filing time,
--    which a reconstruction must not forge. Guarded on contamination_id so a
--    re-run adds nothing and never overwrites a row the operator has since edited.
-- ---------------------------------------------------------------------------
INSERT INTO public.data_contamination_ranges
    (contamination_id, field_scope, contamination_start, contamination_end,
     affected_tables, root_cause, remediation, created_session, notes)
SELECT
  'ORCH-LEDGER-FALSE-SUCCESS-2026-10-21',
  'status, exit_code, exit_reason, contract_met of script_name = run_merdian_shadow_runner_aws.py (83 rows read SUCCESS / contract_met true with actual_writes {})',
  '2026-10-20 18:30:00+00'::timestamptz,
  '2026-10-21 18:29:59+00'::timestamptz,
  '{script_execution_log}'::text[],
  'Dhan Data API subscription lapsed between the 2026-10-19 close and the 2026-10-21 open (HTTP 401: 806 "Data APIs not Subscribed" on optionchain and marketfeed; DH-902 "requires a PLUS subscription. Current plan: FREE" on charts/intraday), so no option_chain_snapshots / market_spot_snapshots / index_futures_snapshots rows were written all session. The orchestrator does not ingest: it picked up the latest existing run_ids (2026-10-19 15:40, NIFTY 1bfd5d97, SENSEX 4e81958a), re-ran its compute stages on them, wrote nothing, and logged SUCCESS / contract met on every cycle. Every market-data table is a GAP for 10-21 (0 rows), not wrong data; WCB was computed from live Zerodha ticks and is genuine.',
  'Subscription renewed 2026-10-22 ~05:06 IST; probes 05:07 IST returned 200 on optionchain/expirylist, charts/intraday and marketfeed/ltp. The false-success shape (contract met with zero writes) is filed as its own TD. Exclude or flag these ledger rows in any run-success, contract-met or provenance figure.',
  'Session 97',
  'Gap, not contamination, for every market-data table on 2026-10-21; this row covers only the false ledger outcome. The 11:00 IST row (status MISSING, exit_code 1) is correct and is not part of the 83. Ruling S97-M.'
WHERE NOT EXISTS (
    SELECT 1 FROM public.data_contamination_ranges
    WHERE contamination_id = 'ORCH-LEDGER-FALSE-SUCCESS-2026-10-21'
);

INSERT INTO public.data_contamination_ranges
    (contamination_id, field_scope, contamination_start, contamination_end,
     affected_tables, root_cause, remediation, created_session, notes)
SELECT
  'SENSEX-CHAIN-OI-VOL0-2026-09-25',
  'oi (SENSEX only, front-expiry legs with zero session volume); oi_call, oi_put; any OI-weighted aggregate incl. DEX notional',
  '2026-09-24 18:30:00+00'::timestamptz,
  '2026-09-29 18:29:59+00'::timestamptz,
  '{option_chain_snapshots,gex_strike_snapshots}'::text[],
  'Vendor OI on SENSEX front-expiry legs with zero session volume is implausibly large and flat all session: max zero-volume leg OI 48,868,660 on 09-25 and 09-28, 1,844,600 on 09-29 (next largest in 34 sessions 08-24..10-12: 60,500); share of front-expiry OI on zero-volume legs 94.37 / 85.45 / 33.27 % (other 31 SENSEX sessions <= 0.58 %, NIFTY <= 0.02 %); share of gross vendor-delta notional 98.21 / 95.58 / 72.87 %; n_vol0_oi_moved 0 on all 68 rows (the OI never moves without a trade). Upstream cause not established.',
  'None at source. The S96-D untraded-leg guard (G1-G3) covers the DEX flow badge only. Registered so research reading SENSEX OI on these dates excludes or flags them.',
  'Session 97',
  'SENSEX only: this table has no symbol column, so a Rule 13 window check also matches NIFTY on these dates; NIFTY is clean there (survey max 0.02 %). Effect on gex_cr / gamma_metrics not measured. Evidence: docs/research/s95_priority/p5/p5_untraded.sql over 2026-08-24..2026-10-12 via roq.sh, 68 rows, 2026-10-12 17:59 IST. TD-S95-NEW-1 (a)/(b); ruling S97-H.'
WHERE NOT EXISTS (
    SELECT 1 FROM public.data_contamination_ranges
    WHERE contamination_id = 'SENSEX-CHAIN-OI-VOL0-2026-09-25'
);

-- ---------------------------------------------------------------------------
-- 4. S90-H backup drops (TD-S90-NEW-11, CLOSED by S97-L: backups_left 0, live
--    tables unchanged, 46 MB freed). Source: sql/2026-10-05_s90H_eod_date_shift_migration.sql.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS public.equity_eod_bak_s90_20261005;
DROP TABLE IF EXISTS public.breadth_indicators_daily_bak_s90_20261005;

-- ---------------------------------------------------------------------------
-- 5. Closing verification. Expected: 1, 1000, 2, 0.
--    Each column fails for the reason it names: the index count goes to 0 if the
--    CREATE did not land, attstattarget reverts to -1 (the default) if the ALTER
--    did not, the contamination count drops below 2 if either INSERT was skipped
--    AND the row was absent, and backups_left rises above 0 if either DROP failed.
-- ---------------------------------------------------------------------------
SELECT
    (SELECT count(*) FROM pg_indexes
      WHERE schemaname = 'public' AND indexname = 'idx_gss_ts')          AS idx_gss_ts_present,
    (SELECT a.attstattarget
       FROM pg_attribute a
       JOIN pg_class     c ON c.oid = a.attrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relname = 'gex_strike_snapshots'
        AND a.attname = 'ts')                                           AS ts_attstattarget,
    (SELECT count(*) FROM public.data_contamination_ranges
      WHERE contamination_id IN ('SENSEX-CHAIN-OI-VOL0-2026-09-25',
                                 'ORCH-LEDGER-FALSE-SUCCESS-2026-10-21')) AS contamination_rows,
    (SELECT count(*) FROM pg_tables
      WHERE schemaname = 'public'
        AND tablename IN ('equity_eod_bak_s90_20261005',
                          'breadth_indicators_daily_bak_s90_20261005')) AS backups_left;
