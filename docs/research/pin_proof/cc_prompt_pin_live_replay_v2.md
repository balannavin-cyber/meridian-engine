<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/cc_prompt_pin_live_replay_v2.md -->
# CC prompt: pin live replay v2 (25 Aug – 20 Nov 2026)

Box: MERIDIAN engine EC2, tmux session `0`, Claude Code in `~/meridian-cc`, manual mode. Design: `claude/pin/pin_live_replay_prereg_v2_FROZEN_2026-11-21.md`, sha256 `d2d87a85d2854dc19feb762344e266277d27d7dfde2b7fb6a88484e6e4b19a14` (approved 2026-11-21 20:57 IST). The design is carried inside the prompt because the box cannot read PK.

Paste:

```
Pin live replay v2, read-only. Frozen design sha256 d2d87a85d2854dc19feb762344e266277d27d7dfde2b7fb6a88484e6e4b19a14 (approved by the operator 2026-11-21 20:57 IST). Follow it exactly; where it and you disagree, stop and say so. Do not add measures, change a threshold or a bin, or drop a run without counting it.

RULES, all binding:
- No database write. No vendor call. No edit to any tracked file. No git write; git reads only as git --no-optional-locks. Never read .env or any file whose name contains .env. Never print a secret.
- Database only through bin/roq.sh as merdian_ro, one statement per file, under ( ulimit -v 700000; ... ). Catalog first for any relation not yet read in this session (volatility_snapshots: information_schema.columns and pg_indexes), and filter on indexed columns.
- EXPLAIN gate for each NEW query shape: plain EXPLAIN with literal bounds; stop on a Seq Scan, a scan estimated over 20,000 rows that is not directly under a Limit of 1, or an empty or errored plan. Show me the plan.
- One symbol-day per query, sleep 5 between queries, stop at the first error or any query over 10 s, no retry. A weekday with zero runs is logged OK_EMPTY and does NOT stop the loop.
- Python only as PYTHONDONTWRITEBYTECODE=1 python3 -B under ( ulimit -v 700000; ... ). The box has 1,910 MB and no swap and hung today from memory exhaustion: one symbol-day in memory at a time, no per-strike maps kept after a run is scored, never call load_runs, measures or main of analyze_v5.py. The analysis reads the per-run scored records only.
- Before anything: df -h on the output filesystem; stop if under 1 GB free. If the IST clock is between 08:30 and 15:40 on a weekday, do not start.
- Write only under docs/research/pin_proof/fix/replay_v2/ (create it). First line of every .md you write: <!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/replay_v2/<file name> -->
- The pull loop is started detached (nohup bash -c '( ulimit -v 700000; ... )' > log 2>&1 < /dev/null &), with < /dev/null on every child, and writes a last line ALL <n> DONE (n = weekdays x 2) or INCOMPLETE into the log; the analysis asserts that line in code. Never pipe a run into head. Check the relative path to bin/roq.sh from the script's own folder before starting.

DATA
- Every weekday from 2026-08-25 to 2026-11-20 inclusive, NIFTY and SENSEX separately, never pooled across symbols. A symbol-day with fewer than 60 valid market-hours runs is reported and left out of the day counts.
- Runs, legs, spot, Board pin, stored walls, strike set, time to expiry: exactly as replay v1. Reuse fix/replay/sql/qR_day.sql.tpl unchanged for the chain pull (its shape is already gated) and fix/replay/score_replay.py unchanged for V2 and for calling compute_run. Days already pulled for v1 and the added day (16-20 Nov) may be reused from disk; say which.
- Added per run: volatility_snapshots.atm_iv_avg, the newest row at or before the run's ts for the same symbol with atm_iv_avg not null (the rule v_gex_strike_rank uses), and its age in minutes. One query per symbol-day in its own file, catalog-checked and EXPLAIN-gated.
- Days 2026-11-16 to 2026-11-20 are marked SEEN; all others UNSEEN.
- Clock segments on the IST clock: pre-open (before 09:15), market (09:15 to 15:29), post-close (15:30 and after).

CONSTRUCTIONS (pin = highest score; ties: nearer to spot, then lower strike)
- B: the Board's stored pin (gex_cycle_history.pin_leader_strike), not recomputed.
- V2: vendor gamma_call*oi_call + vendor gamma_put*oi_put, blank or zero gamma = 0.
- VS: one vendor gamma per strike * (oi_call + oi_put); the gamma is the mean of the two legs when both are > 0, the non-zero one when one is blank or zero, zero when both are.
- FV: phi(d1) * (oi_call + oi_put), d1 = ln(S/K)/(sigma*sqrt(T)) + sigma*sqrt(T)/2, sigma = atm_iv_avg/100, T = minutes from the run's IST ts to 15:30 IST on the expiry date / 525600, phi = standard normal density. No vendor per-leg gamma. A run with no atm_iv_avg or T <= 0 gets no FV pin and is counted.
- F: flat own gamma * (oi_call + oi_put) = compute_run's T_g_flat.
- K: per-strike own gamma * (oi_call + oi_put) = compute_run's T_g. The ruled construction.
analyze_v5.py must hash to 4958435201740e86acb9791781abe764a4df42d09eefab987e7bcbd805086979 and its self_tests() must all pass before any data is read; otherwise stop. VS and FV are new code in a new file under replay_v2/ and need planted-chain self-tests shown to me before any data is scored: VS, a strike where VS and V2 must differ; FV, the planted chain of analyze_v5's ST2 (S 25010, T 3/365, strikes 24800-25200 step 50, OI 100/100 except 25100 1000/1000, 24900 0/600, 25200 900/100) with sigma 0.15, where FV must return 25100; and a run with no atm_iv_avg returning no FV pin.

MEASURES (every figure with its n)
- M1. Per symbol-day, market runs: for V2, VS, FV, F the share of runs on K's strike, over runs with K's lead >= 5 % and over all valid runs (lead = (top - second)/top). Then across days per symbol: median, 10th percentile, minimum, and the number of days meeting both marks (95 % clear-lead, 85 % all valid), for UNSEEN days and for all days.
- M2. The same shares pooled over all market runs of the UNSEEN days per symbol; and separately for pre-open and post-close runs.
- M3. For B, V2, VS, FV, F, K, market runs, per symbol: median abs(pin - S) in steps (NIFTY 50, SENSEX 100); share with pin = at-the-money strike; share outside the stored corridor [put wall, call wall]; median pin changes per day.
- M4. Diagnostics per run, market runs, stored in the per-run record: R = median over strikes within 1 % of spot with both vendor gammas > 0 of (vendor gamma_call / vendor gamma_put); BL = share of open interest in the strike set on legs with oi > 0 and a blank or zero vendor gamma; FB = (compute_run's forward - S) in strike steps; DTE = calendar days to expiry bucketed 0, 1, 2, 3+; IVA = age of atm_iv_avg in minutes.
- M5. Agreement with K for V2, VS, FV, F, market runs with K's lead >= 5 %, per symbol, split by: abs(ln R) in [0,0.1), [0.1,0.3), [0.3,inf); BL in [0,2%), [2%,5%), [5%,inf); abs(FB) in [0,0.5), [0.5,1), [1,inf); DTE bucket; and for FV only IVA in [0,10), [10,60), [60,inf).
- M6. The ten symbol-days with the lowest V2 agreement (market, K lead >= 5 %): date, DTE at the open, median R, median BL, median FB, and the agreement of VS, FV and F that day. Show 2026-11-20 for both symbols beside them whatever its rank.
- M7. Frozen runs: a run after the day's first run at or after 09:15 IST whose whole-chain call OI and put OI both equal that run's. Per symbol: days with any, share of market runs frozen, and the share of K's pin changes with a frozen run before or after.
- M8. Data quality: empty weekdays, short days, runs with no Board row, invalid runs by reason, runs with no atm_iv_avg, fallback strikes, legs with oi > 0 and ltp <= 0, runs with ambiguous spot.

DECISION RULE (fixed; apply it, do not reinterpret it)
On market runs of UNSEEN days, per symbol, a construction is enough if both hold: (1) pooled over those days it is on K's strike on at least 95 % of runs with K's lead >= 5 %; (2) on at least 90 % of those days it meets both day marks (95 % of clear-lead runs and 85 % of all valid runs). It must hold on both symbols. Print for V2, VS, FV, F and each symbol: the pooled figure, the days meeting both marks over the days counted, and PASS or FAIL; then the overall result per construction.

ORDER OF WORK, with two stops
1. Disk and clock checks, hashes, self-tests (analyze_v5, VS, FV), the volatility_snapshots catalog read, its query and EXPLAIN, and ONE symbol-day scored end to end (SENSEX 2026-11-20, reusing the chain pull on disk). Show me in your reply text: the plan, the self-test lines, and for three market runs of that day (first, middle, last) one line each with ts IST, S, B, V2, VS, FV, F, K, K lead, R, BL, FB, atm_iv_avg and IVA. STOP and wait for "continue".
2. On "continue": the full pull detached (chain and volatility), then report the log's last line and the counts OK / OK_EMPTY / STOP. STOP and wait for "analyse".
3. On "analyse": score every day, run the analysis, write replay_v2/results.md, replay_v2/runs.csv (one row per run with every pin, lead and diagnostic) and SHA256SUMS. Print in your reply text inside one code block, under 90 lines: the decision table; M1 across-day summary; M2; M3 as one table per symbol; M5; M6; M7; M8; the sha256 of results.md and runs.csv; confirmation that no tracked file changed. One line per measure, no further interpretation. Then stop.
```
