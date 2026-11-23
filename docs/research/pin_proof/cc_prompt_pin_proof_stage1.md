# CC prompt: pin proof, Stage 1 (preconditions + P-A, P-B, P-C; no outcomes)

Box: MERIDIAN engine EC2, SSM shell, user ssm-user. Run after 15:40 IST on a trading day, or any time on a weekend.

Start:

```
cd ~/meridian-cc && git pull --ff-only && claude
```

Paste:

```
Read-only research task: Stage 1 of the pin proof, pre-registration claude/pin/pin_proof_prereg_DRAFT_2026-11-19.md, sha256 02f7dfd2af3ef1807299e4cc0a00fc4dd42b1b5ff0f74445cfe210be9b75fb17. You do not have that file; everything you need is below. Do not read any outcome (no spot path after a run, no settle). Do not write to the database. Do not edit any tracked file. Do not commit.

Rules: read the database only through bin/roq.sh as merdian_ro (read bin/roq.sh first to see how it takes SQL and how it pages; Supabase caps 1000 rows per request, so aggregate in SQL and page by day). Every python or roq run under ( ulimit -v 700000; ... ). Never cat, grep or source .env. Write all output under docs/research/pin_proof/stage1/ (create it). If merdian_ro cannot read a relation, stop that test, write the relation name and the error to docs/research/pin_proof/stage1/BLOCKED.txt, and carry on with the tests that do not need it.

Cohort: gex_strike_snapshots, columns id, run_id, symbol, ts, expiry_date, dte, strike, spot, oi_call, oi_put, gex_cr, created_at, gamma_call, gamma_put. Every run with ts from 2026-05-25 00:00 IST to now, NIFTY and SENSEX separately, never pooled. DTE buckets 0, 1-2, 3+ from the dte column. Strike step = smallest positive difference between distinct strikes in the run. sigma = spot * atm_iv/100 * sqrt(greatest(dte,1)/252); take atm_iv from gamma_metrics or volatility_snapshots on the same run_id (check which has it; say which you used); if neither has it for a run, report distance in steps only for that run and count such runs.

Step 0, preconditions. Write each result to stage1/preconditions.md with a one-line PASS or FAIL and the numbers.
C0. Read public.data_contamination_ranges; list any range overlapping the cohort for gex_strike_snapshots, gex_cycle_history or option_chain_snapshots; exclude those runs and count them.
C1. Find the SQL that defines v_gex_strike_rank in sql/ and confirm it is the live one: compute length and md5 of pg_get_viewdef('public.v_gex_strike_rank'::regclass, true) through roq and of the body the file reproduces (Rule 25). Write down its ordering and tie-break. Then recompute N = rank-1 strike per run by that ordering from gex_strike_snapshots, and compare with gex_cycle_history.pin_leader_strike on the same run_id (gex_cycle_history exists from 2026-10-06). PASS if equal on at least 99% of joined runs per symbol. If it FAILS, stop the whole task after writing the mismatching runs (first 20) and the count; do not run P-A to P-C.
C2. Runs with a non-uniform strike grid: count, list first 10, exclude.
C3. Runs carrying more than one expiry_date: count; must be 0.
C5. Any query that times out or errors is written as UNMEASURED, never as zero.

Definitions per run (front expiry, after exclusions):
N = argmax abs(gex_cr) by the live view's tie-break.
A = argmax (gamma_call*oi_call + gamma_put*oi_put)*spot^2/1e7 on raw columns; tie-break nearer to spot, then lower strike.
N_sym = N recomputed with one gamma per strike: where gamma_call > 0 and gamma_put > 0, both legs use (gamma_call+gamma_put)/2 and gex is (g*oi_call - g*oi_put)*spot^2/1e7; where either is 0, use the stored gex_cr. Apply the same deep-ITM handling as stored: if stored gex_cr is 0 while both gammas are > 0, keep it 0.
Also count runs where A's strike has stored gex_cr = 0 while both gammas > 0 (the deep-ITM guard), per symbol.

P-A. Per symbol and DTE bucket: runs, share N = A, median and p90 of |N - A| in steps and in sigma, median signed distance from spot of N and of A in sigma. Also read the source of v_gex_concentration and write in one line what the denominator of the Board's share is (sum of abs(gex_cr), or sum of both sides). Verdict line per symbol: "P-A pin meets definition" if share N = A >= 95% in every DTE bucket, otherwise "P-A FAILS" with the worst bucket.
P-B. Per symbol and DTE bucket: share of runs with gex_cr at N < 0; share of runs where N and the rank-2 strike have opposite gex_cr signs. Verdict "P-B FAILS" if gex_cr at N < 0 on 5% or more of runs in any bucket.
P-C1. Per symbol and DTE bucket: share of runs where N_sym differs from N; median signed (N_sym - N) in steps; and the same share per trading day (one line per day). Verdict "P-C1 FAILS" if N_sym differs from N on 5% or more of runs in any bucket.
P-C2 (descriptive, no verdict). For each symbol and trading day, take the first run with ts at or after 09:15 IST as the anchor. Flag a later run frozen when its sum(oi_call) and sum(oi_put) both equal the anchor's exactly and its spot differs from the anchor's spot by more than one step. Report frozen runs per day (only days with at least one), and on frozen runs the share where N differs from N on the nearest earlier non-frozen run.

Output: stage1/results.md with one table per test and the verdict lines; stage1/per_day_pc1.csv; stage1/frozen_runs.csv (symbol, ts, run_id). At the very end print to the screen only: the precondition lines, the six verdict lines (three tests x two symbols), and the three largest DTE-bucket cells of P-A, P-B and P-C1 by share. Keep the screen print under 40 lines. Then print the sha256 of every file you wrote.
```
