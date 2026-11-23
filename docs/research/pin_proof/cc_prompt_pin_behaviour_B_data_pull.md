# CC prompt B: pin behaviour study v5, data pull

Box: MERIDIAN engine EC2, SSM shell, inside tmux session 0, manual mode. After 15:40 IST on a trading day, or a weekend.
Study: `claude/pin/pin_behaviour_study_v5_FROZEN_2026-11-21.md`, sha256 8fcb30ca95bc685a6e1d2cf495687ce8cca59fe690f277ef677722c9e2c0108b. Claude Code does not have that file; everything it needs is in the paste.
This prompt only pulls the data to disk and starts the loop detached. The measures are a separate, disk-only prompt (C) after the loop's finish line.

Paste into the pin Claude Code session (tmux 0, "Pin behaviour study"):

```
Read-only research task: pin behaviour study v5, DATA PULL only (study sha256 8fcb30ca95bc685a6e1d2cf495687ce8cca59fe690f277ef677722c9e2c0108b; you do not have the file; everything needed is below). No analysis, no pins, no gamma in this task: pull the inputs to disk, start the loop detached, report, and end your turn.

Hard limits (unchanged from Step 0). The e1-e3-e10 session shares this tree: no git command that writes; git status only as git --no-optional-locks. Write new files only, all under docs/research/pin_proof/lookback_v5/ (create it). Read lookback_v4/ and gamma_inputs/ only; change nothing there. No database write. No vendor API. Database only through bin/roq.sh as merdian_ro (SQL file, literals substituted, statement_timeout 30 s). Every python and roq run under ( ulimit -v 700000; ... ), python as PYTHONDONTWRITEBYTECODE=1 python3 -B, also for inline one-liners. Never cat, grep or source .env. Never pipe a run into head. stdin from /dev/null for anything inside a while-read loop. EXPLAIN gate before every query on a hist_* relation, using docs/research/pin_proof/gamma_inputs/sens/gate_explain.py by path: plain EXPLAIN, fail on Seq Scan, on any scan node estimated over 20000 rows, or on an empty/ERROR/no-scan plan. 5 s sleep between database calls. Stop at the first gate failure, roq error, non-empty stderr or query over 10 s; no retry. An error is UNMEASURED, never zero.

Conventions. hist bar_ts is IST clock time labelled +00 at second :59; never convert. NIFTY 9992f600-51b3-4009-b487-f878692a0bc5, SENSEX 73a1390a-30c9-46d6-9d3f-5f03c3f5ad71.

PART 1. Session list, from disk. From lookback_v4/out/_qB_<SYM>_<month>.txt (B1 rows) take every cal_day with has_opt_bar = true and cal_day <= 2026-03-30, per symbol. Write lookback_v5/sessions_<SYM>.txt, one date per line, sorted. Print the counts (Step 0 measured 247 and 247) and the first and last date. Do not hand-list dates.

PART 2. Wall view identity and band (catalog reads, no hist relation, no gate needed). (a) Rule 25 for public.v_gex_strike_walls against sql/2026-09-15_s79_v_gex_strike_walls.sql, done the way the project's Rule 25 specifies (length and md5 of pg_get_viewdef(..., true) against the body the file reproduces). Report MATCH, NO MATCH or NOT VERIFIED with the reason. (b) select get_parameter_num('wall.band.NIFTY'), get_parameter_num('wall.band.SENSEX'); report the values or that they are NULL / not readable. Whatever the result, carry on; write it to lookback_v5/walls_identity.md.

PART 3. The per-day query template lookback_v5/sql/qD_day.sql.tpl, one symbol-day per query, one statement, read-only, no temp table. Targets: the 24 minutes 09:30, 09:45, ... 15:15, each at second :59, exact bar only (no nearest-bar fallback). It returns three row kinds as tag|json:
 R0, one per target minute that has a spot bar: tname (HH:MM), spot = hist_spot_bars_1m.close at that bar_ts, front_expiry = smallest expiry_date >= trade date among option bars at that bar_ts (one-row ordered lookup on hist_option_bars_unique, as in lookback_v4/sql/qB_opt_month.sql.tpl), n_legs = count of front-expiry legs at that bar_ts with strike between spot*0.95 and spot*1.05.
 R1, one per such leg: tname, strike, ot (option_type), px = close, oi. Emit strike, px and oi as text so nothing is rounded.
 R2, one row for the day: clock time and close of the first and of the last hist_spot_bars_1m bar with bar_ts >= day 09:15:00+00 and < day 15:31:00+00.
Filter on indexed columns only (instrument_id, bar_ts, expiry_date, strike). No outer ORDER BY.

PART 4. Trials before the loop. EXPLAIN-gate and run the template once each on: NIFTY 2025-04-01; SENSEX 2026-03-02; and one NIFTY expiry day and one SENSEX expiry day taken from the front expiries in the Step 0 output. For each print: GATE line, elapsed seconds, R0 rows, R1 rows, and whether sum(n_legs over R0) equals the R1 row count. If any gate fails, any trial takes 5 s or more, or any R1 count differs from sum(n_legs) (a row cap), stop and tell me the numbers; do not write the loop.

PART 5. The loop lookback_v5/run_pull.sh, modelled on lookback_v4/run_part0a.sh (same stop rules, same stdin handling, same computed finish marker): for each symbol (NIFTY then SENSEX) and each date in sessions_<SYM>.txt: substitute, EXPLAIN, gate, sleep 5, query to out/_qD_<SYM>_<day>.txt, sleep 5. Log one line per day to out/_pull_run.log: OK|STOP sym day elapsed_s r0=<n> r1=<n> legs_sum=<n>. STOP (and end the loop) on gate fail, roq rc, stderr, over 10 s, or r1 != legs_sum. A day with r0 = 0 is logged OK_EMPTY and the loop continues (it is a finding, not an error). The finish marker is ALL <n> DONE only if every day logged OK or OK_EMPTY, else INCOMPLETE with counts. The script must refuse to start if out/_pull_run.log already exists, unless called with RESUME=1, in which case it skips days already logged OK or OK_EMPTY and appends.

PART 6. Start it detached, once: check pgrep -f 'run_pul[l].sh' shows 0, then from lookback_v5: nohup bash -c '( ulimit -v 700000; bash run_pull.sh )' > out/_pull_stdout.log 2>&1 < /dev/null & . Wait 90 seconds, print the first lines of out/_pull_run.log to confirm days are logging OK, then END YOUR TURN. Do not poll after that; I will ask for a status check.

Final print (under 25 lines): Part 1 counts; Part 2 results; the four trial lines; the loop's pid and its first logged lines; the expected finish time (days x measured seconds per day); confirmation that nothing outside lookback_v5/ was written and no git write was run.
```

Status check, to paste later (any time):

```
Status of the v5 data pull, read-only: print pgrep -f 'run_pul[l].sh' | wc -l ; wc -l out/_pull_run.log ; the count of lines by first word (OK, OK_EMPTY, STOP, ALL, INCOMPLETE) ; tail -n 3 out/_pull_run.log. If it has stopped with STOP or INCOMPLETE, show that line and do nothing else.
```
