<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/cc_prompt_pin_live_replay.md -->
# CC prompt: pin live replay (16–19 Nov 2026)

Box: MERIDIAN engine EC2, tmux session `0`, Claude Code in `~/meridian-cc`, manual mode. Design: `claude/pin/pin_live_replay_prereg_FROZEN_2026-11-21.md`, sha256 `cbad76e1c7377a33d78fed12a943103c2e4f0e589800414f10c0869d17f91139` (approved 2026-11-21 17:57 IST). The design text is carried inside the prompt because the box cannot read PK.

Paste:

```
Pin live replay, read-only. Frozen design sha256 cbad76e1c7377a33d78fed12a943103c2e4f0e589800414f10c0869d17f91139 (approved by the operator 2026-11-21 17:57 IST). Follow it exactly; where it and you disagree, stop and say so. Do not add measures, do not change a threshold, do not drop a run without counting it.

RULES, all binding:
- No database write. No vendor call. No edit to any tracked file. No git write of any kind; git reads only as git --no-optional-locks.
- Never read .env or any file whose name contains .env. Never print a secret.
- Database only through bin/roq.sh as merdian_ro, one statement per file, each run under ( ulimit -v 700000; ... ). Catalog first: read information_schema.columns and pg_indexes for every relation before querying it, and filter on indexed columns.
- EXPLAIN gate: for each query shape run plain EXPLAIN (no ANALYZE) once with literal bounds; stop if it shows a Seq Scan, any scan estimated over 20,000 rows, or an empty or errored plan. Show me the plan.
- One symbol-day per query, sleep 5 between queries, stop at the first failure or any query over 10 s, no retry. statement_timeout is 30 s.
- Python only as PYTHONDONTWRITEBYTECODE=1 python3 -B under ( ulimit -v 700000; ... ). The box has 1,910 MB and no swap and hung today from memory exhaustion: hold one symbol-day in memory at a time, keep no per-strike maps after a run is scored, and do not call load_runs, measures or main from analyze_v5.py.
- Write only under docs/research/pin_proof/fix/replay/ (create it). First line of every .md you write: <!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/replay/<file name> -->
- Any long loop is started detached (nohup bash -c '( ulimit -v 700000; ... )' > log 2>&1 < /dev/null &), with < /dev/null on every child inside a while-read loop, and writes a final line ALL 8 DONE into the log the analysis checks. Never pipe a run into head.
- If the IST clock is between 08:30 and 15:40 on a weekday, do not start.

DATA
- Days 2026-11-16, 2026-11-17, 2026-11-18, 2026-11-19. NIFTY and SENSEX separately, never pooled. Every front-expiry run of each day.
- Runs: gamma_metrics (one row per front-expiry run_id) joined to option_chain_snapshots on run_id and expiry_date, as Part A did (gamma_inputs/queries/ has that join; read it, do not guess column names).
- Per leg: strike, option_type, ltp, oi, gamma (vendor), spot, ts. Spot of a run = the first positive per-leg spot.
- Strike set for every construction: abs(K/S - 1) <= 0.05 with oi > 0 on at least one leg.
- Board pin per run: gex_cycle_history.pin_leader_strike for the same run_id.
- Walls per run, in this order of preference, decided from the catalog before any data is read, and stated in the result: (i) wall columns stored in gex_cycle_history, if it has them; (ii) the Board's rule recomputed with volatility_snapshots.atm_iv_avg for that run (rule: among strikes with abs(K - S) <= 1.5 * sigma, call wall = strike with the largest call OI, put wall = strike with the largest put OI, oi > 0; sigma = S * atm_iv/100 * sqrt(max(dte,1)/252)); (iii) the same rule with the study's straddle volatility.
- Time to expiry: minutes from the run's ts on the IST clock to 15:30 IST on the expiry date, divided by 525600. A run with T <= 0 gets no pin and is counted. State how you converted ts to IST and show one example run.
- For the frozen-run test also pull, per run, total call OI and total put OI over the whole front-expiry chain (aggregated in SQL).

CONSTRUCTIONS (pin = highest score; ties: nearer to spot, then lower strike)
- B: the Board's stored pin, not recomputed.
- V2: vendor gamma_call * oi_call + vendor gamma_put * oi_put. A blank or zero vendor gamma counts as zero.
- V1: one vendor gamma per strike * (oi_call + oi_put). The gamma is the out-of-the-money leg's (call if K >= S, put if K < S), or the other leg's if that is zero; a strike with both zero scores zero.
- F: flat own gamma * (oi_call + oi_put), g_flat of the v5 study.
- K: per-strike own gamma * (oi_call + oi_put), g of the v5 study.
F and K come from docs/research/pin_proof/lookback_v5/analyze_v5.py compute_run, imported unchanged; record that file's sha256. Its pins T_g_flat and T_g are F and K. Before any data is read, call its self_tests() and require all-pass; otherwise stop. Pass the run's IST HH:MM as tname and check on one run, by hand arithmetic shown to me, that compute_run's minutes to expiry equal the T defined above; if they differ by more than 1 minute, stop.
Add three self-tests of your own for V2 and V1 on a planted chain (a strike where V2 and V1 must differ because one leg's vendor gamma is zero; a tie; a strike with both gammas zero) and show them.

MEASURES (every figure with its n; per symbol and per symbol-day)
- M-a. For B, V2, V1, F, K: median abs(pin - S) in strike steps (NIFTY 50, SENSEX 100); share of runs with pin = at-the-money strike; share of wall-defined runs with the pin outside [put wall, call wall]; pin changes per day; distinct pin strikes per day.
- M-b. Agreement with K: share of runs on the same strike for V2, V1 and F, over all valid runs and split by K's lead (< 5 %, >= 5 %; lead = (top score - second score) / top score). Where they differ: median difference in steps.
- M-c. NIFTY 2026-11-18: the strikes K took, with run counts, and K's median distance from spot against B's. SENSEX 2026-11-19: share of runs outside the corridor for B and for K.
- M-d. Frozen runs: a run is frozen if its total call OI and total put OI over the whole front-expiry chain both equal those of the day's first run at or after 09:15 IST, and it is not that run. Count per symbol-day. For K: share of pin changes where the run before or the run after the change is frozen.
- M-e. Data quality: runs with no Board pin row, runs invalid in compute_run by reason, fallback strikes, runs with T <= 0, legs with oi > 0 and ltp <= 0.

DECISION RULE (fixed; apply it, do not reinterpret it)
- "V2 is enough" if, on each symbol separately, V2 = K on at least 95 % of runs where K's lead is >= 5 % and on at least 85 % of all valid runs. The same test separately for V1 and for F. Print each of the six verdicts PASS or FAIL with its two figures and denominators.

ORDER OF WORK, with two stops
1. Catalog reads, the query template, its EXPLAIN, self-tests, and ONE symbol-day pulled and scored (NIFTY 2026-11-18). Show me in your reply text: the EXPLAIN plan, the self-test lines, which wall source is used and why, the T check, and for three runs of that day (first, middle, last) one line each with ts IST, S, B, V2, V1, F, K, walls, K's lead. STOP and wait for "continue".
2. On "continue": the remaining seven symbol-days detached, then the analysis.
3. Write fix/replay/results.md (all tables), fix/replay/runs.csv (one row per run), and a SHA256SUMS for the folder. Print to the screen in your reply text inside one code block, under 80 lines: the six verdicts; M-a as one table per symbol; M-b; M-c; M-d; M-e; the sha256 of results.md and runs.csv; confirmation that no tracked file changed. Then stop. No interpretation beyond one line per measure.
```
