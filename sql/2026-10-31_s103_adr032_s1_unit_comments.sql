-- ADR-032 S1 (D4): unit COMMENTs on the Gamma columns. Metadata only: no data, no view, no function, no writer changes.
-- S103, 2026-10-31. APPLIED 2026-10-31 ~09:00 IST (rehearsed first with the final line ROLLBACK; same text, final line COMMIT).
-- Verified after: 8 ADR-032 comments, gex_cr keeps its sign note, gex_strike_snapshots rows for 2026-10-30 unchanged (23,080).
-- Re-running this file refuses by design (the seven targets now carry comments).
-- Fail-closed: aborts if any of the 7 comment-free targets already has a comment, or if gex_strike_snapshots.gex_cr no longer
-- carries exactly its pre-existing sign note (the only comment on the 8 targets at the 2026-10-31 08:57 read; kept verbatim inside the new text).
-- Undo: NULL the 7; restore gex_cr to its old sign-note text (see the rollback block, issued separately).

BEGIN;
SET LOCAL lock_timeout = '3s';

DO $$
DECLARE n int; old_gex text;
BEGIN
  -- the seven other targets must carry no comment
  SELECT count(*) INTO n
  FROM pg_description d
  JOIN pg_class c ON c.oid = d.objoid AND d.classoid = 'pg_class'::regclass
  JOIN pg_namespace s ON s.oid = c.relnamespace AND s.nspname = 'public'
  JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.objsubid
  WHERE (c.relname, a.attname) IN (
    ('gamma_metrics','net_gex'),
    ('gex_cycle_history','net_gex'), ('gex_cycle_history','gamma_at_pin'),
    ('gex_pin_maxpain_history','peak_pin_gex_cr'),
    ('signal_snapshots','net_gex'), ('structural_divergence_snapshots','net_gex'),
    ('hist_gamma_metrics','net_gex'));
  IF n <> 0 THEN RAISE EXCEPTION 'REFUSE: % of the 7 comment-free targets already carry a comment', n; END IF;
  -- gex_strike_snapshots.gex_cr carries the sign note (read 2026-10-31 08:57 IST); it must still be exactly that text
  SELECT col_description('public.gex_strike_snapshots'::regclass, a.attnum) INTO old_gex
  FROM pg_attribute a WHERE a.attrelid = 'public.gex_strike_snapshots'::regclass AND a.attname = 'gex_cr';
  IF old_gex IS DISTINCT FROM 'Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).'
  THEN RAISE EXCEPTION 'REFUSE: gex_cr comment changed since the read: %', old_gex; END IF;
END $$;

COMMENT ON COLUMN public.gex_strike_snapshots.gex_cr IS
 'ADR-032: per-strike dealer gamma exposure, INR crore for a 100% spot move (gamma*OI*S^2/1e7). Per-1% figure = x0.01, served by the *_1pct views. Stored unit; no per-1% column exists yet (ADR-032 D2 not built). Sign note (pre-existing text, kept verbatim): Signed Cr. Positive=dampening (dealer long). Negative=amplifying (dealer short).';
COMMENT ON COLUMN public.gamma_metrics.net_gex IS
 'ADR-032: net gamma exposure over all strikes of the run, INR crore for a 100% spot move (gamma*OI*S^2/1e7), signed. Per-1% figure = x0.01, served by v_gamma_metrics_1pct.net_gex_1pct. Stored unit; D2 not built.';
COMMENT ON COLUMN public.gex_cycle_history.net_gex IS
 'ADR-032: copy of gamma_metrics.net_gex for the cycle: INR crore for a 100% spot move (gamma*OI*S^2/1e7). Per-1% = x0.01. Stored unit; D2 not built.';
COMMENT ON COLUMN public.gex_cycle_history.gamma_at_pin IS
 'ADR-032: gex_cr of the rank-1 (pin leader) strike, copied: INR crore for a 100% spot move (gamma*OI*S^2/1e7). Per-1% = x0.01. Stored unit; D2 not built.';
COMMENT ON COLUMN public.gex_pin_maxpain_history.peak_pin_gex_cr IS
 'ADR-032: gex_cr at the pin peak strike, INR crore for a 100% spot move (gamma*OI*S^2/1e7). Per-1% = x0.01. Static backfill 2026-05-25..2026-09-18 (S80); no live writer.';
COMMENT ON COLUMN public.signal_snapshots.net_gex IS
 'ADR-032: copy of gamma_metrics.net_gex at signal time: INR crore for a 100% spot move (gamma*OI*S^2/1e7). Per-1% = x0.01. Stored unit; D2 not built.';
COMMENT ON COLUMN public.structural_divergence_snapshots.net_gex IS
 'ADR-032: copy of gamma_metrics.net_gex at snapshot time: INR crore for a 100% spot move (gamma*OI*S^2/1e7). Per-1% = x0.01. Stored unit; D2 not built.';
COMMENT ON COLUMN public.hist_gamma_metrics.net_gex IS
 'ADR-032: RAW scale, about 1e7 x the live gamma_metrics unit (gamma*OI*S^2, no /1e7). INR crore per 1% = value/1e9. Measured 2026-10-31: 182,430 of 182,461 non-null rows >= 1e9, one scale throughout (2025-04..2026-03).';

-- verification (inside the same transaction): expect 8 rows, comment_ok = true on all
SELECT c.relname AS tbl, a.attname AS col,
       (col_description(c.oid, a.attnum) LIKE 'ADR-032:%') AS comment_ok,
       length(col_description(c.oid, a.attnum)) AS len
FROM pg_class c
JOIN pg_namespace s ON s.oid = c.relnamespace AND s.nspname = 'public'
JOIN pg_attribute a ON a.attrelid = c.oid AND NOT a.attisdropped
WHERE (c.relname, a.attname) IN (
    ('gex_strike_snapshots','gex_cr'), ('gamma_metrics','net_gex'),
    ('gex_cycle_history','net_gex'), ('gex_cycle_history','gamma_at_pin'),
    ('gex_pin_maxpain_history','peak_pin_gex_cr'),
    ('signal_snapshots','net_gex'), ('structural_divergence_snapshots','net_gex'),
    ('hist_gamma_metrics','net_gex'))
ORDER BY 1, 2;

COMMIT;
