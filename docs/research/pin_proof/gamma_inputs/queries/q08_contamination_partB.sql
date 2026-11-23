\pset format aligned
-- Rule 13 preflight for Part B. Part B reads hist_option_greeks_1m,
-- hist_option_bars_1m and hist_spot_bars_1m over 2025-04-01..2026-03-30 for
-- NIFTY and SENSEX. Symbol scope per S100-J: symbols NULL = every symbol.
--
-- Column names read from information_schema, not assumed: the timestamp columns
-- are contamination_start / contamination_end (an earlier draft of this query
-- said start_ts / end_ts and would have errored). field_scope is text, not an
-- array. affected_tables is text[] NOT NULL and contamination_end is NOT NULL,
-- so the two NULL branches below are guards against a schema change, NOT live
-- logic -- they cannot fire against the current definition.
SELECT contamination_id,
       affected_tables::text   AS affected_tables_raw,
       symbols::text           AS symbols_raw,
       field_scope,
       contamination_start AT TIME ZONE 'Asia/Kolkata' AS start_ist,
       contamination_end   AT TIME ZONE 'Asia/Kolkata' AS end_ist,
       CASE WHEN affected_tables IS NULL
                 THEN 'NULL = ALL RELATIONS (check the table definition)'
            WHEN affected_tables && ARRAY['hist_option_greeks_1m','hist_option_bars_1m',
                                          'hist_spot_bars_1m']::text[]
                 THEN 'NAMES A PART B RELATION'
            ELSE 'other relations' END AS relation_scope,
       CASE WHEN contamination_start < timestamptz '2026-03-31 00:00+05:30'
             AND coalesce(contamination_end, 'infinity'::timestamptz)
                 > timestamptz '2025-04-01 00:00+05:30'
                 THEN 'OVERLAPS B WINDOW' ELSE 'outside B window' END AS window_scope
  FROM public.data_contamination_ranges
 ORDER BY contamination_start;
