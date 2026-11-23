\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- B3: stored pin band per run_id, ONE SYMBOL-DAY. __SYM__ __D__ __D1__.
-- gex_pin_maxpain_history is keyed (symbol, run_id, expiry_date); the filter is on
-- symbol (the unique index's leading column) plus the ts window.
SELECT 'P0' AS tag, row_to_json(t)::text AS payload FROM (
  SELECT h.symbol AS sym,
         '__D__' AS d,
         h.run_id::text AS run_id,
         h.expiry_date::text AS expiry,
         h.pin_lower::text  AS pin_lower,
         h.pin_upper::text  AS pin_upper,
         h.peak_pin_strike::text AS peak_pin_strike,
         h.pin_n_strikes,
         h.tau_used::text AS tau_used
    FROM gex_pin_maxpain_history h
   WHERE h.symbol = '__SYM__'
     AND h.ts >= timestamptz '__D__ 00:00:00+05:30'
     AND h.ts <  timestamptz '__D1__ 00:00:00+05:30'
) t;
