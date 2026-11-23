\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- B3: stored pin band per run_id, ONE SYMBOL-DAY. NIFTY 2026-11-16 2026-11-17.
-- gex_pin_maxpain_history is keyed (symbol, run_id, expiry_date); the filter is on
-- symbol (the unique index's leading column) plus the ts window.
SELECT 'P0' AS tag, row_to_json(t)::text AS payload FROM (
  SELECT h.symbol AS sym,
         '2026-11-16' AS d,
         h.run_id::text AS run_id,
         h.expiry_date::text AS expiry,
         h.pin_lower::text  AS pin_lower,
         h.pin_upper::text  AS pin_upper,
         h.peak_pin_strike::text AS peak_pin_strike,
         h.pin_n_strikes,
         h.tau_used::text AS tau_used
    FROM gex_pin_maxpain_history h
   WHERE h.symbol = 'NIFTY'
     AND h.ts >= timestamptz '2026-11-16 00:00:00+05:30'
     AND h.ts <  timestamptz '2026-11-17 00:00:00+05:30'
) t;
