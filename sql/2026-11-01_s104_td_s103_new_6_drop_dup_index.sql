-- CORRECTION 2026-11-03: the Rollback statement below was run in the editor right after this block (Sun 2026-11-01 ~10:23 IST),
-- so ix_gex_strike_snap_sym_ts was recreated (confirmed: pg_stat_statements, role postgres, 1 call, same text). Net effect of
-- this file: none. The real drop is sql/2026-11-03_s104_td_s103_new_6_drop_idx_gss_symbol_ts.sql (the unused twin).
-- TD-S103-NEW-6: drop the duplicate (symbol, ts DESC) index on public.gex_strike_snapshots.
-- Applied by the operator in the Supabase SQL editor, Sun 2026-11-01 ~10:23 IST (market shut).
-- Before: 8 indexes (pg_indexes read 10:21 IST via bin/roq.sh). After: 7 (read back, PASS).
-- Kept: idx_gss_symbol_ts. Dropped: ix_gex_strike_snap_sym_ts. Fail-closed DO block.
-- Rollback: CREATE INDEX ix_gex_strike_snap_sym_ts ON public.gex_strike_snapshots USING btree (symbol, ts DESC);
-- Open (TD-S72-NEW-4): idx_gss_symbol_ts is a leading prefix of idx_gss_symbol_ts_strike; read before any drop.

DO $$
DECLARE
  keep_def text; drop_def text; v_keep_ok boolean; v_drop_con int;
BEGIN
  SET LOCAL lock_timeout = '5s';

  SELECT replace(indexdef,'idx_gss_symbol_ts','X') INTO keep_def
    FROM pg_indexes WHERE schemaname='public' AND indexname='idx_gss_symbol_ts';
  SELECT replace(indexdef,'ix_gex_strike_snap_sym_ts','X') INTO drop_def
    FROM pg_indexes WHERE schemaname='public' AND indexname='ix_gex_strike_snap_sym_ts';

  IF keep_def IS NULL OR drop_def IS NULL THEN
    RAISE EXCEPTION 'ABORT: one of the pair is missing (keep=%, drop=%)', keep_def, drop_def;
  END IF;
  IF keep_def <> drop_def THEN
    RAISE EXCEPTION 'ABORT: definitions differ: % vs %', keep_def, drop_def;
  END IF;

  SELECT (i.indisvalid AND NOT i.indisunique AND NOT i.indisprimary) INTO v_keep_ok
    FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
    WHERE c.relname='idx_gss_symbol_ts' AND c.relnamespace='public'::regnamespace;
  IF v_keep_ok IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'ABORT: keeper is not valid / non-unique / non-PK';
  END IF;

  SELECT count(*) INTO v_drop_con FROM pg_constraint
    WHERE conindid = 'public.ix_gex_strike_snap_sym_ts'::regclass;
  IF v_drop_con <> 0 THEN
    RAISE EXCEPTION 'ABORT: drop target backs a constraint';
  END IF;

  DROP INDEX public.ix_gex_strike_snap_sym_ts;
END $$;

SELECT indexname FROM pg_indexes
 WHERE schemaname='public' AND tablename='gex_strike_snapshots' ORDER BY indexname;
