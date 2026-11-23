# CC prompt A: pin behaviour study v4, Step 0 (checks before the run)

Box: MERIDIAN engine EC2, SSM shell, user ssm-user. Manual mode. After 15:40 IST on a trading day, or a weekend.
Study: `claude/pin/pin_behaviour_study_v4_FROZEN_2026-11-20.md`, sha256 69ca96868709df554ea42eb632e44903a0b83b56e9d38c08c682929974c41338. Claude Code does not have that file; everything it needs is in the paste.

If the pin Claude Code session is still open (tmux session 0), paste into it. Otherwise start one:

```
cd ~/meridian-cc && claude
```

Paste:

```
Read-only research task: pin behaviour study v4, Step 0 (checks before the main run). Study file sha256 69ca96868709df554ea42eb632e44903a0b83b56e9d38c08c682929974c41338 (you do not have it; everything needed is below; change no rule). No pass or fail here except where stated: report what is measured.

Hard limits. Another session (e1-e3-e10) is working in this same tree: do not run any git command that writes (no add, commit, stash, restore, clean, switch, checkout, pull), and do not touch refresh_dhan_token.py, dhan_drop.py or anything outside the folder named next. Write new files only, all under docs/research/pin_proof/lookback_v4/ (create it). Do not edit or delete anything under docs/research/pin_proof/gamma_inputs/ (read only). Do not write to the database. Do not call any vendor API. Read the database only through bin/roq.sh as merdian_ro (roq takes a SQL file; substitute literals, psql -v does not work; statement_timeout 30 s). Every python or roq run under ( ulimit -v 700000; ... ). Python only as python3 -B with PYTHONDONTWRITEBYTECODE=1; never py_compile; no .pyc or __pycache__. Never cat, grep or source .env. Never pipe a run into head. A query that errors or times out is written as UNMEASURED with the error, never as zero. EXPLAIN gate before every query on a hist_* relation: plain EXPLAIN (never ANALYZE), fail on any Seq Scan or any scan node estimated over 20000 rows, and fail if the plan is empty, has ERROR, or has no scan node (reuse gamma_inputs/sens/gate_explain.py by path, do not copy or edit it). 5 s sleep between queries. Stop that part at the first gate failure, error or any query over 10 s; no retry; say which.

Conventions. hist bar_ts is IST clock time labelled +00 at second :59: read as IST, never convert. Instrument ids: NIFTY 9992f600-51b3-4009-b487-f878692a0bc5, SENSEX 73a1390a-30c9-46d6-9d3f-5f03c3f5ad71. Window 2025-04-01 to 2026-11-19. Symbols never pooled.

PART 0a. Coverage (new queries, small). Design the queries so each passes the gate (one symbol-month per query is expected; the Part B qB5_month template in gamma_inputs/queries/ shows a pattern that passed). Per symbol and month report:
(1) sessions with any hist_spot_bars_1m bar between 09:15 and 15:30;
(2) for each such session, the clock time of its last spot bar; report per month the min, median and max of that time, and the count of sessions whose last bar is before 15:25;
(3) sessions that have a hist_option_bars_1m bar at 12:30:59 (probe with LIMIT 1 per session on the (instrument_id, trade_date, bar_ts) index; say if a session resolves only within +/-120 s);
(4) for each such session the front expiry = smallest expiry_date >= trade date among bars at that minute; list the distinct front expiry dates per symbol (one line per month);
(5) for each expiry date that is itself a session: does the expiring contract have bars on that day at 10:00:59 and at 15:00:59 (yes/no counts).
Write coverage.md with one table per symbol and the list of sessions missing option bars.

PART 0b. Rule 13: read public.data_contamination_ranges; list any range naming hist_option_bars_1m or hist_spot_bars_1m or overlapping the window with symbols NULL; say what would be excluded.

PART 0c, 0d use only files already on disk: docs/research/pin_proof/gamma_inputs/sens/_qS_<SYM>_<day>.txt (24 files; S0 rows = minute, spot, expiry, dte_opt; S1 rows = legs within 3 % of spot with strike, ot, px = bar close, oi, iv_txt, gamma_txt). No database query.

PART 0c. Does stored OI move intraday? Per symbol and day: total call OI and total put OI over the S1 legs at 10:00, 12:30, 15:00, and the number of strikes whose OI differs between 10:00 and 15:00. Report per symbol: days where total OI is identical at all three minutes (count of 12), and the median absolute change 10:00 to 15:00 as a share of the 10:00 total.

PART 0d. Gamma robustness of the pin strike. For each of the 72 minutes:
- In-study gamma: sigma = the volatility pricing the ATM straddle (call px + put px at the strike nearest spot; Black-Scholes with forward = spot, r = 0; bisection on sigma in [0.01, 5.0] to 1e-6). T = calendar minutes from the sampled minute to 15:30 IST on the expiry date, divided by 525600. g_K = phi(d1) / (S * sigma * sqrt(T)), d1 = (ln(S/K) + sigma^2 * T / 2) / (sigma * sqrt(T)). One g_K per strike, used for both legs. If the ATM strike lacks a call or put px > 0, use the next nearest strike that has both and count it.
- Stored gammas from gamma_txt: (ii) OTM leg (K > S the call's, K < S the put's, K = S the call's), (iii) call leg, (iv) put leg. Under (iii) and (iv) a strike with that leg's gamma NULL is left out.
- Pins: T = argmax g_K * (oi_call + oi_put). N = argmax g_K * abs(oi_call - oi_put). Ties: nearer to spot, then lower strike. Strike set: strikes in the file with oi > 0 on at least one leg.
Report per symbol: share of the 36 minutes where T is the same strike under (i) and (ii); under (i) and (iii); (i) and (iv); (iii) and (iv); the same four for N; for every disagreement the minute and the size in strike steps. Then one line per symbol: "0d T in-study vs stored-OTM agreement x of 36 = y %" and whether it is at least 95 %. Also report the strike step seen per symbol, and the median ratio of in-study g to stored OTM-leg g at the ATM strike.
Write the script as lookback_v4/step0_disk_checks.py and its output to lookback_v4/step0_disk_checks.txt.

PART 0e. Wall rule. In sql/ (and sql/snapshots/) find the view(s) that give the Board's call OI wall and put OI wall / corridor (search for wall, corridor). Read only; no database call needed. Write walls.md: file and line, the exact rule for call wall and put wall in plain words (which strikes are eligible, which column is maximised, tie-break, any distance limit), and at most 12 quoted lines. If you cannot find it, say so.

At the very end print to the screen only (under 45 lines): per symbol the first and last month with option bars, total sessions with spot, with option bars, and missing; whether sessions after 2026-03-30 have option bars (count); last-spot-bar median time and how many sessions end before 15:25; expiry dates count and how many expiry days have the expiring contract's bars; Rule 13 result; 0c lines; the 0d lines; the wall rule in two lines; every UNMEASURED item; confirmation that nothing outside lookback_v4/ was created or changed and no git write was run. Then print sha256sum of every file you wrote.
```
