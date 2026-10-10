-- P2 Part 1 — the first query that reads position values. Pre-registered with
-- docs/research/s94_priority/P2_dealer_side_design_2026-10-10.md; run only after that note is committed.
-- Run:  bin/roq.sh < docs/research/s94_priority/p2/part1_extract.sql > docs/research/s94_priority/p2/part1_extract_2026-10-10.csv
COPY (
  SELECT trade_date, participant,
         opt_idx_call_long, opt_idx_call_short, opt_idx_put_long, opt_idx_put_short
  FROM public.participant_oi_daily
  WHERE exchange = 'NSE' AND trade_date <= DATE '2026-10-09'
  ORDER BY trade_date, participant
) TO STDOUT WITH (FORMAT csv, HEADER true);
