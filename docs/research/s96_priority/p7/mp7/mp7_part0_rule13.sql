-- mp7_part0_rule13.sql -- M-P7 Part 0a: Rule 13 check over the sample window. READ-ONLY.
-- Form copied from P1 (docs/research/s92_priority/p1/p1_part1_eligibility.sql 1a): affected_tables
-- cast to text, open-ended ranges kept. Every range overlapping 2026-08-24 .. 2026-10-09 IST is
-- printed; the prereg (section 3) excludes a session only when hits_study_tables is true and the
-- range overlaps that session's date. Second statement: the control that merdian_ro sees the
-- table at all (S94 measured 1 row; TD-S94-NEW-1) -- it must print a count >= 1.
\set QUIET on
\pset format csv
SELECT contamination_id, field_scope, contamination_start, contamination_end,
       affected_tables::text AS affected_tables,
       (affected_tables::text ~* '(option_chain_snapshots|market_spot_snapshots|trading_calendar)')
         AS hits_study_tables
  FROM public.data_contamination_ranges
 WHERE contamination_start < TIMESTAMPTZ '2026-10-10 00:00:00+05:30'
   AND COALESCE(contamination_end, 'infinity'::timestamptz) >= TIMESTAMPTZ '2026-08-24 00:00:00+05:30'
 ORDER BY contamination_start;
SELECT count(*) AS total_rows_visible FROM public.data_contamination_ranges;
