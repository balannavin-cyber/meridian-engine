-- TD-S103-NEW-6 (final): drop the UNUSED twin idx_gss_symbol_ts (0 scans, 28 MB); keep ix_gex_strike_snap_sym_ts (62,319 scans, 15 MB).
-- Applied by the operator in the Supabase SQL editor, Tue 2026-11-03 ~11:1x IST (market open; lock_timeout 5s, fail-closed).
-- Before: 8 indexes. After: 7 (read back). EXPLAIN of v_gex_max_pain after: Index Only Scan using ix_gex_strike_snap_sym_ts, 83.7 ms.
-- Why this one: scan counts read 2026-11-03 08:59 IST (pg_stat_user_indexes). The 2026-11-01 drop of ix_gex_strike_snap_sym_ts was undone
-- by the rollback statement being run (see the correction note in sql/2026-11-01_s104_td_s103_new_6_drop_dup_index.sql). No rollback is
-- provided on purpose; if ever needed: CREATE INDEX idx_gss_symbol_ts ON public.gex_strike_snapshots USING btree (symbol, ts DESC);
-- Open (TD-S72-NEW-4): ix_gex_strike_snap_sym_ts is a leading prefix of idx_gss_symbol_ts_strike (idx_scan 294); read before any drop.

DO $$
DECLARE keep_def text; drop_def text; v_keep_ok boolean; v_drop_con int;
BEGIN
  SET LOCAL lock_timeout = '5s';
  SELECT replace(indexdef,'ix_gex_strike_snap_sym_ts','X') INTO keep_def
    FROM pg_indexes WHERE schemaname='public' AND indexname='ix_gex_strike_snap_sym_ts';
  SELECT replace(indexdef,'idx_gss_symbol_ts','X') INTO drop_def
    FROM pg_indexes WHERE schemaname='public' AND indexname='idx_gss_symbol_ts';
  IF keep_def IS NULL OR drop_def IS NULL THEN
    RAISE EXCEPTION 'ABORT: one of the pair is missing (keep=%, drop=%)', keep_def, drop_def;
  END IF;
  IF keep_def <> drop_def THEN
    RAISE EXCEPTION 'ABORT: definitions differ: % vs %', keep_def, drop_def;
  END IF;
  SELECT (i.indisvalid AND NOT i.indisunique AND NOT i.indisprimary) INTO v_keep_ok
    FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
    WHERE c.relname='ix_gex_strike_snap_sym_ts' AND c.relnamespace='public'::regnamespace;
  IF v_keep_ok IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'ABORT: keeper is not valid / non-unique / non-PK';
  END IF;
  SELECT count(*) INTO v_drop_con FROM pg_constraint
    WHERE conindid = 'public.idx_gss_symbol_ts'::regclass;
  IF v_drop_con <> 0 THEN
    RAISE EXCEPTION 'ABORT: drop target backs a constraint';
  END IF;
  DROP INDEX public.idx_gss_symbol_ts;
END $$;

SELECT indexname FROM pg_indexes
 WHERE schemaname='public' AND tablename='gex_strike_snapshots' ORDER BY indexname;
