# CC prompt: MR-PIN2 step 3, gamma rate sensitivity run

Box: MERIDIAN engine EC2, SSM shell, user ssm-user. Plain shell, no tmux, manual mode. Run after 15:40 IST on a trading day, or on a weekend.
Design: `claude/pin/gamma_rate_sensitivity_design_v2_FROZEN_2026-11-20.md`, sha256 a9d0b7c5c3dbfbd1739096a81c138cc7caefc5c094d454d28c3fd9d6ffad612e. Claude Code does not have that file; everything it needs is in the paste.

Start (only if no Claude Code session is open on ~/meridian-cc):

```
cd ~/meridian-cc && git pull --ff-only && claude
```

Paste:

```
Read-only research run: gamma rate sensitivity, MR-PIN2 step 3, design v2 FROZEN sha256 a9d0b7c5c3dbfbd1739096a81c138cc7caefc5c094d454d28c3fd9d6ffad612e (you do not have that file; everything you need is below, and you must not change any rule in it). Do not write to the database. Do not edit any tracked file. Do not commit. Do not call any vendor API. Do not edit or delete any existing file in docs/research/pin_proof/gamma_inputs/; write new files only, all under docs/research/pin_proof/gamma_inputs/sens/ (create it). Do not rebuild SHA256SUMS. Do not read any spot or price after a sampled minute (no outcomes).

Rules: read the database only through bin/roq.sh as merdian_ro (as in Part B: roq takes a SQL file, substitute literals, psql -v variables do not work, statement_timeout 30 s, unaligned output has a "(N rows)" footer). Every python or roq run under ( ulimit -v 700000; ... ). Python only as python3 -B; never py_compile; never create .pyc or __pycache__ anywhere. Never cat, grep or source .env; use no credential other than what bin/roq.sh uses. A query that times out or errors is written as UNMEASURED with the error, never as zero.

QUESTION. Part B found the own-solved history hist_option_greeks_1m (flat r = 6.5 %) fails the call/put gamma ratio test: per-day median ratio within 1 % of spot inside [0.95, 1.05] on NIFTY 5 of 12 days and SENSEX 6 of 12. Claim tested: the flat rate is the main cause; re-solving each leg with a rate implied by the Fyers near-month futures should bring call and put gamma at one strike together.

STEP 0. Preconditions. Stop at the first failure and say which.
0a. In gamma_inputs/, sha256sum must equal: _partH_raw.txt ba52678f0d90667ce261b8c562dd08e02ca20253575d63f4083279d672323ac0; _partH_analysis.txt 83a5bf8e7cd411b9e3222a5ebc1c68d131055037dfe6448a87a2b9de0abdc5ee; partB_code.md d02077fc0b50450d5375e6d3717d240edce2e502046172599dbacb00094c201a; BLOCKED.txt 7da800ef48c4916f2ab1015cdf088e0ecf001be2d5719062c6b5ac55eddec24c.
0b. Read partB_code.md, partB_results.md, the B3 query under gamma_inputs/queries/, the FUTURES CONTRACT RULE and the PART H section (line 248) of BLOCKED.txt, analyze_partH.py, and backfill_hist_greeks.py with core/bs_engine.py. Write sens/conventions.md (at most 40 lines, with file:line references): which bs_engine functions the backfill calls for IV and gamma and with which arguments; that spot is hist_spot_bars_1m.close at the same bar_ts, R_FLAT = 0.065, T = calendar days / 365 whole days, solved price = bar close; and Part B's exact B3 definition (band, pairing, how the per-day median pools minutes). If the code contradicts any of those four conventions, stop.
0c. Read information_schema.columns for hist_option_greeks_1m, hist_option_bars_1m and hist_spot_bars_1m, and pg_indexes for the three. Record the numeric type of iv and gamma in sens/conventions.md.

STEP 1. Inputs per minute.
1a. F: rebuild the selected futures bar per minute from _partH_raw.txt by the FUTURES CONTRACT RULE (use analyze_partH.py's selection logic; import it or re-run its function, without editing it). The 72 selected (minute, contract, expiry_date, close, volume) rows must equal the selection in _partH_analysis.txt. Any difference: stop. Keep volume and the ZERO_VOLUME flag. Counts: F missing, fut_dte < 3, next contract used (expected 0, 0, 0).
1b. Write a template sens/queries/qS_day.sql.tpl, one symbol-day per query, literal bounds: for the three sampled minutes of that day (10:00, 12:30, 15:00 IST, bar_ts at :59 of the minute, read as IST clock time, exactly as Part B B1 picked them) return: bar_ts; spot = hist_spot_bars_1m.close at the same bar_ts; and for the front expiry (Part B B1 rule) every leg with |strike/spot - 1| <= 0.03: strike, option_type, expiry_date, the bar close, oi, and stored iv and gamma from hist_option_greeks_1m (join key instrument_id, bar_ts, expiry_date, strike, option_type). Filter on indexed columns.
1c. EXPLAIN gate before every query: plain EXPLAIN (never ANALYZE); write the plan to sens/queries/explain_<symbol>_<day>.txt; fail on any Seq Scan node or any scan node with estimated rows over 20000.
1d. Loop over the 24 Part B sample symbol-days (same days as Part H) in this order: NIFTY by date, then SENSEX by date. Per day: EXPLAIN gate, then the query, output to sens/_qS_<symbol>_<day>.txt, then sleep 5 s. Time each query. Stop the loop at the first gate failure, error, timeout or any query over 10 s; no retry; write STOP with the reason. Append one line per day to sens/_sens_run.log: OK|FAIL|STOP symbol day elapsed_s rows. After the last day append exactly ALL 24 DONE to sens/_sens_run.log itself (not to stdout). Step 2 may start only if the last line of sens/_sens_run.log is ALL 24 DONE.

STEP 2. Gates. Write sens/gates.md and print the gate lines before computing any futures-implied rate. If either gate fails, stop the whole task after writing gates.md.
Pair set: strikes within 1 % of spot (Part B B3 band and definition) carrying stored call gamma > 0 and put gamma > 0, front expiry. This set is fixed now and reused unchanged in step 3.
G0 (reproduce Part B): from stored gamma, per symbol and day, median call gamma / put gamma over the day's pairs by Part B's B3 definition. In-band days ([0.95, 1.05]) must equal NIFTY 5 of 12 and SENSEX 6 of 12 exactly. Print "G0 PASS" or "G0 FAIL" with the per-day medians.
G1 (replicate at r = 0.065): re-solve every leg in the pair set with the backfill's own bs_engine calls and conventions (bar close, hist spot at the same bar_ts, T = calendar days / 365, r = 0.065). Per symbol both must hold: (a) on at least 99 % of legs |gamma_resolved / gamma_stored - 1| <= 0.005 and |IV_resolved - IV_stored| <= 0.05 vol points; (b) on every one of the 12 days the per-day median call/put gamma ratio from the re-solve is within 0.005 of the stored one. Report the 10 worst legs, solver failures, and the share of legs inside the tolerance. If iv and gamma are stored at full precision and legs still miss by about 0.5 %, write "convention mismatch suspected" whatever the verdict. Print "G1 PASS" or "G1 FAIL" per symbol.

STEP 3. Sensitivity (only if G0 and G1 passed for both symbols).
3a. Rate per minute: r_m = ln(F / S) / T_fut, T_fut = (futures expiry_date - IST trade date) / 365, S = hist_spot_bars_1m close at the same bar_ts. In % a year. Flag (do not exclude) any r_m outside -5 % to +20 %.
3b. Re-solve every leg of each minute with r = r_m, the same bar close, same S, same T_opt (calendar days / 365 to the option expiry), same bs_engine calls. A leg that fails to solve drops its pair; count failures per minute and per symbol.
3c. Verdict minutes: futures bar volume > 0. NIFTY expected 36 of 36, SENSEX 26 of 36 (10 ZERO_VOLUME). A day keeps the minutes it has left; a day with none left drops out. If fewer than 10 SENSEX days have a verdict minute, SENSEX is UNMEASURED.
3d. Per symbol, on verdict minutes, per day: median call/put gamma ratio over the same pairs, before (stored) and after (r_m), and median call IV / put IV before and after.
3e. Verdict per symbol, fixed now. PASS if all three hold: (1) out-of-band days after <= floor(2n/12), where n is the number of days with a verdict minute (n = 12: at least 10 of 12 in [0.95, 1.05]); (2) no day in band before (same minutes) is out of band after; (3) solver failures <= 5 % of the symbol's legs, otherwise UNMEASURED. Otherwise FAIL with the failing number. Print one line per symbol: "SENS <symbol> PASS|FAIL|UNMEASURED: in-band before x/n, after y/n, left band z, solver failures f/legs".
3f. All-72 report: repeat 3d and the in-band counts on all 72 minutes, no verdict. If SENSEX all-72 and verdict-minute results disagree on whether the 10 of 12 bar is met, write "SENSEX: zero-volume minutes change the result" in results.md.
3g. Control C-flat (no verdict): per symbol one flat rate = median r_m over its verdict minutes; re-solve with it and report in-band days on verdict minutes.
3h. Descriptive, no verdict: the 1-3 % band before and after; per-minute medians (72 rows) to sens/per_minute.csv with r_m, F, S, futures volume, zero-volume flag, fut_dte, pairs, failures; r_m median, min, max per symbol.

OUTPUT: sens/conventions.md, sens/gates.md, sens/results.md (tables per symbol, the verdict lines, what the test could not see: OTM-leg truth, lumpy dividends, SENSEX alignment caveat from the PART H section, stale bar closes), sens/per_minute.csv, sens/per_day.csv, the analysis script sens/analyze_sens.py, sens/queries/, sens/_qS_*.txt, sens/_sens_run.log. No other file anywhere is created or changed.

At the very end print to the screen only: step 0 result; 1a counts and match; the run log summary (OK/FAIL/STOP counts, min and max elapsed, last line); G0 and G1 lines per symbol; the two SENS verdict lines; the in-band counts before/after per symbol for verdict minutes, all-72 and C-flat; r_m median/min/max per symbol; any flagged r_m; every UNMEASURED item; confirmation that no tracked file changed and no .pyc or __pycache__ exists under docs/research/pin_proof/. Keep the screen print under 40 lines.
```
