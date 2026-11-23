# CC prompt C: pin behaviour study v5, measures (disk only)

Box: MERIDIAN engine EC2, tmux session 0, the pin Claude Code session ("Pin behaviour study"), manual mode.
Study: `claude/pin/pin_behaviour_study_v5_FROZEN_2026-11-21.md`, sha256 8fcb30ca95bc685a6e1d2cf495687ce8cca59fe690f277ef677722c9e2c0108b.
Run only after the data pull's log ends with `ALL 491 DONE` (status check in `cc_prompt_pin_behaviour_B_data_pull.md`).
No database access at all in this prompt.

Paste:

```
Disk-only analysis task: pin behaviour study v5, MEASURES (study sha256 8fcb30ca95bc685a6e1d2cf495687ce8cca59fe690f277ef677722c9e2c0108b; you do not have the file; every definition is below; change none). NO database access, no roq, no vendor call. Same hard limits as the pull: write only under docs/research/pin_proof/lookback_v5/; no git write (git status only with --no-optional-locks); every python under ( ulimit -v 700000; PYTHONDONTWRITEBYTECODE=1 python3 -B ... ), inline one-liners included; never pipe a run into head. This is a description: no pass or fail on the results. The only stops are the precondition and the self-tests.

PRECONDITION, asserted in code as the first statement of the analysis: the last line of out/_pull_run.log is exactly ALL <n> DONE with n = lines in sessions_NIFTY.txt + sessions_SENSEX.txt, and there is no STOP line. Otherwise exit 2 with the reason.

INPUT: out/_qD_<SYM>_<day>.txt. R0 rows (tname HH:MM, spot, front_expiry, n_legs), R1 rows (tname, strike, ot, px, oi; text fields), R2 row (first_clock, first_close, last_clock, last_close). Assert per file that the R1 count equals the sum of n_legs. Symbols never pooled.

PER RUN (symbol, day, tname). step = 50 for NIFTY, 100 for SENSEX (assert every strike is a multiple).
- S = spot. A strike row = (K, call px, call oi, put px, put oi); missing px or oi counts as 0. Strike set = strikes with oi > 0 on at least one leg.
- T = ((expiry_date - day) in days * 1440 + minutes from HH:MM to 15:30) / 525600. dte_cal = (expiry_date - day) in days. dte_sess = number of dates in sessions_<SYM>.txt that are > day and <= expiry_date. DTE bucket: 0, 1, 2, 3+ by dte_sess. Count runs whose expiry_date is not itself in the session list.
- ATM = the multiple of step nearest S (tie: lower).
- sigma_atm: at the strike nearest S that has call px > 0 and put px > 0 (tie: lower): solve straddle(sigma) = call px + put px, with call = S*N(d1) - K*N(d2), put = K*N(-d2) - S*N(-d1), d1 = (ln(S/K) + sigma^2*T/2)/(sigma*sqrt(T)), d2 = d1 - sigma*sqrt(T) (forward = S, r = 0). Bisection on sigma in [0.01, 5.0] to 1e-6. If the price is outside the bracket, try the next nearest strike with both prices, up to 3 strikes; count how often a further strike was used. If all 3 fail the run is INVALID (reason sigma_atm) and counted.
- sigma_rem = S * sigma_atm * sqrt(T).
- F = median of (K + call px - put px) over the three strikes nearest S that have both px > 0 (fewer than three available: use what there is; none: run INVALID, reason forward).
- Primary gamma g_K: OTM leg against F (K >= F the call px, K < F the put px). sigma_K = Black-76 implied vol of that leg (r = 0): call = F*N(d1) - K*N(d2), put = K*N(-d2) - F*N(-d1), d1 = (ln(F/K) + sigma_K^2*T/2)/(sigma_K*sqrt(T)); same bisection. If that px is <= 0 or outside the bracket, FALLBACK sigma_K = sigma_atm (count per run). g_K = phi(d1)/(F*sigma_K*sqrt(T)). One g_K per strike, used for both legs.
- Second gamma g_flat_K = phi(d1f)/(S*sigma_atm*sqrt(T)), d1f = (ln(S/K) + sigma_atm^2*T/2)/(sigma_atm*sqrt(T)).
- Pins, each under both gammas, over the strike set. Tie-break always: higher score, then nearer to S, then lower strike.
  T   = argmax g*(oi_call + oi_put)
  N   = argmax g*abs(oi_call - oi_put)
  PW1 = argmax g*(oi_call + oi_put)*exp(-(K - S)^2/(2*(1.0*sigma_rem)^2))
  PW2 = the same with 0.5*sigma_rem
  For each: score share = top score / sum of scores; lead = (s1 - s2)/s1.
- Walls (the Board's rule, reconstructed): sigma_wall = S*sigma_atm*sqrt(max(dte_cal, 1)/252). Eligible strikes: abs(K - S) <= 1.5*sigma_wall. call_wall = eligible strike with the largest oi_call among oi_call > 0; put_wall likewise with oi_put (ties: nearer to S, then lower). None eligible: wall undefined. A pin is INSIDE if put_wall <= pin <= call_wall. Count runs with a wall undefined and runs with put_wall > call_wall.

MEASURES. Per symbol, per pin (T, PW1, PW2, N, and ATM as a reference line where it applies), per DTE bucket and overall; medians with p10 and p90, or shares; n (runs, sessions or windows) on every cell. Primary gamma unless stated.
- M1 where it sits: signed and absolute (pin - S)/step; absolute (pin - S)/sigma_rem; share of runs with abs(pin - S) <= step; share with pin = ATM.
- M2 walls: share of runs with the pin outside [put_wall, call_wall]; share with the pin equal to a wall; share of runs with S outside the corridor. Undefined-wall runs excluded and counted.
- M3 changes, within a session, over consecutive valid runs in time order: changes per session; hold length in runs (holds are cut at the session's ends; say so); share of changes where the lead at the run before the change was under 5 %; share of there-and-back changes (pin goes A to B and is A again one or two runs later).
- M4 following spot: for every run i with run i+4 in the same session: dATM = (ATM[i+4] - ATM[i])/step. Over windows with abs(dATM) >= 2: share where the pin moved the same way by at least 1 step, did not move, or moved the other way by at least 1 step (the remainder is "moved under 1 step"). State that windows overlap.
- M5 sign: share of runs where oi_put > oi_call at the pin's strike (the Board would call it amplifying).
- M6 concentration: score share of the pin; lead; share of runs with lead under 5 %.
- M7 closing in on the settle strike: settle strike = multiple of step nearest R2 last_close on the expiry date's own session, used only if that session exists and its last_clock is 15:29:59 or later (count exclusions). abs(pin - settle)/step by DTE bucket, and on expiry day by clock hour of the run; the same for ATM beside it.
- M8 agreement: pairwise share of runs where two of T, PW1, PW2, N, ATM are the same strike.
- M9 dependence on the gamma: per pin, share of runs where the pin under g differs from the pin under g_flat; median and p90 of the difference in steps; split by primary lead under 5 % and 5 % or more. Fallback: median and p90 of the share of strikes per run on fallback; share of runs with over 20 % of strikes on fallback.
- Repeat M1, M3 and M6 under g_flat.
- Data quality: sessions per symbol, OK_EMPTY days, runs expected (24 per session), runs present, valid, invalid by reason, sigma_atm taken from a further strike.

SELF-TESTS, run before any data and written to self_test.txt; any failure exits 3 and nothing else runs.
- ST1 round trips: straddle priced at S = 25000, K = 25000, sigma = 0.15, T = 3/365 inverts to 0.15 within 1e-5; Black-76 call at F = 25010, K = 25500, sigma = 0.18, same T, inverts within 1e-5; the same for a put at K = 24500.
- ST2 planted chain: S = 25010, T = 3/365 with dte_cal = 3, strikes 24800 to 25200 step 50, every px generated from the formulas above at sigma = 0.15 with F = S; oi_call = oi_put = 100 everywhere except 25100 (call 1000, put 1000), 24900 (call 0, put 600), 25200 (call 900, put 100). Expected under both gammas: ATM 25000; T 25100; N 25200; call_wall 25100; put_wall 25100; every recovered sigma_K within 1e-4 of 0.15; no fallback.
- ST3 tie: two strikes with identical score at equal distance from S resolve to the lower strike.
- ST4 a strike whose OTM px is 0 takes the fallback and is counted.

WORKED EXAMPLES, to worked_examples.txt: NIFTY 2025-04-01 12:30 and NIFTY 2025-04-03 14:30 (an expiry day), and the same two for SENSEX using 2026-03-02 12:30 and 2025-04-08 14:30. For each: S, F, ATM, sigma_atm, T in minutes, sigma_rem, dte_cal, dte_sess, the walls, the four pins under each gamma with lead, and the top 5 strikes by T score under the primary gamma with K, oi_call, oi_put, sigma_K, g_K, g_flat_K, score share; fallback count.

OUTPUT under lookback_v5/: analyze_v5.py; self_test.txt; worked_examples.txt; runs.csv (one row per run: symbol, day, tname, S, F, ATM, sigma_atm, T minutes, dte_cal, dte_sess, walls, and for each pin under each gamma the strike, share and lead; validity and reason; fallback count); results.md (every table, with n; a short "what this cannot say" section: nothing after 2026-03-30, OI is not dealer inventory, an OTM close can be an old print, walls use the study's sigma not the vendor's); and a refreshed SHA256SUMS for lookback_v5.

HOW TO RUN: first run only the self-tests and the worked examples in the foreground and show me self_test.txt in full and the NIFTY 2025-04-01 12:30 example. STOP there and wait for me to say continue. On "continue", start the full analysis detached (nohup, ulimit, output to out/_analyze_v5.log, finish marker ANALYSIS DONE as the log's last line), check it with pgrep -f 'analyze_v[5].py', and when it has finished give the screen print.

SCREEN PRINT (under 90 lines): data-quality line per symbol; then per symbol one table with rows = pin x DTE bucket (T, PW1, PW2, N; buckets 0, 1, 2, 3+) and columns: runs, median abs distance in steps, share pin = ATM, share outside walls, changes per session, share of changes on lead < 5 %, share lead < 5 %, share amplifying; then per symbol one line each for M4 (same / stayed / opposite per pin), M7 on expiry day (median distance per pin and for ATM), M8 (T vs N, T vs PW1, T vs ATM, PW2 vs ATM), M9 (share differing per pin, fallback median); then the sha256 of results.md and runs.csv; confirmation of no database access, no git write, nothing written outside lookback_v5/.
```
