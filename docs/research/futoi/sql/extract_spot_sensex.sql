-- SENSEX spot 1-minute bars, needed only for the section 7 "SENSEX -> NIFTY"
-- item (SENSEX G(E) needs a SENSEX spot to price its deltas against).
-- Same session clock and same window as the NIFTY pull. hist_spot_bars_1m runs
-- past the window to 2026-11-17, so the upper bound is enforced here: nothing
-- after 2026-03-30 is read (section 8 -- the Stage 1 holdout stays sealed).
\pset format csv
SELECT trade_date::text AS trade_date,
       to_char(bar_ts, 'HH24:MI:SS') AS hhmmss,
       close
FROM hist_spot_bars_1m
WHERE instrument_id = :'sensex'
  AND trade_date BETWEEN :'lo' AND :'hi'
  AND bar_ts::time BETWEEN '09:15:59' AND '15:29:59'
ORDER BY trade_date, bar_ts;
