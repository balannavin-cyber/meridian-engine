-- P2 Part 1, v2. Same SELECT as part1_extract.sql (v1), whose COPY was refused by bin/roq.sh's
-- write-verb guard on 2026-10-10 08:40 IST before execution (exit 2, no values read).
-- Formatting moved to psql's csv output mode; definitions (§4/§5) unchanged.
\set QUIET on
\pset format csv
SELECT trade_date, participant,
       opt_idx_call_long, opt_idx_call_short, opt_idx_put_long, opt_idx_put_short
FROM public.participant_oi_daily
WHERE exchange = 'NSE' AND trade_date <= DATE '2026-10-09'
ORDER BY trade_date, participant;
