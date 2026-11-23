<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/audit/PROMPT.md -->

# Task prompt as given — VS view dry run + gamma pipeline audit (STAGE A)

Verbatim record of the operator's instructions for this task: the original message,
the self-test correction that followed, and the STAGE A follow-up message. Kept so the
audit's scope and its stopping point are readable without the chat transcript.

---

## Message 1 — the task

TASK: (1) VS pin view dry run. (2) Gamma pipeline audit, STAGE A only, then STOP. Read-only.

CONDITIONS (all binding)
- Database reads only through bin/roq.sh as merdian_ro, and only in PART 1. Do not look for or use any other credential. Never cat, grep, head or source .env or any file with .env in its name.
- No git writes of any kind. git status only as: git --no-optional-locks status.
- Write only under docs/research/pin_proof/fix/view/ and docs/research/pin_proof/fix/audit/.
- Every run under ulimit -v 700000, python3 -B, no py_compile, no .pyc.
- Box has 1,910 MB RAM and no swap: one symbol-day in memory at a time, drop per-strike maps after scoring. Never call load_runs, measures or main of analyze_v5.py.
- Before any run, print the resolved absolute path of bin/roq.sh and confirm it exists.
- Each query: plain EXPLAIN first; stop if it shows a Seq Scan or any scan over 20,000 rows not directly under Limit 1. Stop at the first error or any query over 10 s. 5 s sleep between queries.
- Never pipe a run into head. If two sides of a check differ, report the difference as found; do not adjust either side.
- Type all results in your reply text, not collapsed tool output.
- Do NOT run the full audit in this task. Stop after STAGE A and wait for a message that says RELEASE.

PART 1 - VS view dry run
1. Write fix/view/dryrun_vs.sql containing exactly this SELECT (body of a draft view; do NOT create the view, do NOT run any DDL):

```sql
WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g WHERE g.symbol > s.symbol)
          FROM symbols s WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.run_id, lr.ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1
          ) lr
         WHERE s.symbol IS NOT NULL
     ), base AS (
        SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte,
               g.strike, g.spot, g.oi_call, g.oi_put,
               g.gamma_call, g.gamma_put, g.gex_cr,
               CASE WHEN COALESCE(g.gamma_call, 0) > 0 AND COALESCE(g.gamma_put, 0) > 0
                         THEN (g.gamma_call + g.gamma_put) / 2.0
                    WHEN COALESCE(g.gamma_call, 0) > 0 THEN g.gamma_call
                    WHEN COALESCE(g.gamma_put,  0) > 0 THEN g.gamma_put
                    ELSE 0
               END AS gamma_strike
          FROM gex_strike_snapshots g
          JOIN latest_run lr ON g.symbol = lr.symbol AND g.run_id = lr.run_id
         WHERE g.spot > 0 AND abs(g.strike / g.spot - 1) <= 0.05
     ), scoped AS (
        SELECT b.*,
               b.gamma_strike * (COALESCE(b.oi_call, 0) + COALESCE(b.oi_put, 0))
               * (b.spot::double precision ^ 2) / 1e7 AS gross_cr
          FROM base b
     ), ranked AS (
        SELECT sc.run_id, sc.symbol, sc.ts, sc.expiry_date, sc.dte,
               sc.strike, sc.spot, sc.oi_call, sc.oi_put,
               sc.gamma_call, sc.gamma_put, sc.gamma_strike, sc.gex_cr, sc.gross_cr,
               row_number() OVER w AS strike_rank,
               sc.gross_cr / NULLIF(sum(sc.gross_cr) OVER p, 0) AS share_of_gross,
               count(*) OVER p AS n_ranked
          FROM scoped sc
         WHERE sc.gross_cr > 0
        WINDOW p AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date),
               w AS (PARTITION BY sc.run_id, sc.symbol, sc.expiry_date
                     ORDER BY sc.gross_cr DESC, abs(sc.strike - sc.spot), sc.strike)
     ), hdr AS (
        SELECT run_id, symbol, expiry_date,
               max(gross_cr) FILTER (WHERE strike_rank = 1) AS top_cr,
               max(gross_cr) FILTER (WHERE strike_rank = 2) AS second_cr
          FROM ranked GROUP BY run_id, symbol, expiry_date
     )
SELECT r.run_id, r.symbol, r.expiry_date, r.ts, r.dte, r.spot, r.strike_rank, r.strike,
       r.oi_call, r.oi_put, r.gamma_call, r.gamma_put, r.gamma_strike, r.gross_cr,
       r.share_of_gross, r.gex_cr,
       CASE WHEN r.gex_cr > 0 THEN 'DAMPENING' WHEN r.gex_cr < 0 THEN 'AMPLIFYING' END AS side,
       (h.top_cr - h.second_cr) / NULLIF(h.top_cr, 0) AS lead_rel,
       r.n_ranked
  FROM ranked r
  JOIN hdr h ON h.run_id = r.run_id AND h.symbol = r.symbol AND h.expiry_date = r.expiry_date
 ORDER BY r.symbol, r.strike_rank;
```

2. EXPLAIN it (gate above), then run it once, saving the full output to fix/view/dryrun_vs_out.txt. Print the plan, the run time, and for each symbol: run_id, ts in IST, spot, n_ranked, lead_rel, and ranks 1-5 (strike, gamma_call, gamma_put, gamma_strike, oi_call, oi_put, gross_cr, share_of_gross, gex_cr, side).
3. Independent check, same method as the earlier V2 dry run in fix/view/: for each symbol's latest run pull that run's chain with fix/view/qR_run.sql.tpl and score it with vs_scores from fix/replay_v2/constructions_v2.py. Print side by side per symbol: rank 1-5 strikes from the SELECT and from vs_scores, the ratio second/top on each side, the count of scored strikes on each side. Units may differ, so compare order and ratios. State MATCH or DIFFERS per symbol and, if DIFFERS, exactly which strikes.
4. Stored-versus-replica check, from the rows already fetched in step 2 (no new query): for every returned strike compute replica = (gamma_call*oi_call - gamma_put*oi_put) * spot^2 / 1e7 with a blank gamma or oi <= 0 contributing 0, and compare with stored gex_cr. Print per symbol: number of strikes, number where they agree within 0.5 %, the largest relative difference and its strike with all its inputs.

PART 2 - Gamma pipeline audit, STAGE A

A1. Consumer list (code read only). Starting from docs/research/pin_proof/fix/stage0_code_read.md, list every place that reads gex_cr, gex_strike_snapshots, or a total/aggregate built from them, in ~/meridian-engine (sql/, merdian_compute/, writers, runners) and ~/meridian-connect/src. For each: file:line, what it computes, what reads it next, and one tag: GROSS, NET, or INTERPRETATION (a label or decision about dealer positioning). Include walls, the pin band, any total or regime label, hhi_net, and anything a signal or trade decision reads. Say plainly if something is referenced but its definition is not in the tree. Write to fix/audit/consumers.md and print it.

A2. Write fix/audit/audit.py implementing exactly the spec below, reusing the replay v2 code for the reference gamma (same functions score_v2.py uses; do not re-derive it). Data: only the files in fix/replay_v2/chain/. No database.

SPEC
Grain: one record per symbol, expiry, strike, run timestamp. Market runs 09:15-15:29 IST. Strike set: abs(K/S - 1) <= 0.05 with OI > 0 on at least one leg. Step 50 NIFTY, 100 SENSEX.
Per run and strike k:
  gc, gp = vendor gamma of call and put leg; blank or <= 0 counts as 0. OIc, OIp = open interest.
  gVS = mean of gc and gp when both > 0; the one that is > 0 when the other is not; 0 when neither.
  gK = reference per-strike own gamma exactly as replay v2. fallback = True where the solve fell back to at-the-money vol.
  P (production replica): net_P = gc*OIc - gp*OIp ; gross_P = gc*OIc + gp*OIp ; a leg with gamma 0 or OI <= 0 contributes 0.
  N (proposed): net_N = gVS*(OIc - OIp) ; gross_N = gVS*(OIc + OIp).
  R (reference): net_R = gK*(OIc - OIp) ; gross_R = gK*(OIc + OIp).
  Sums are over the run's strike set. GR = sum gross_R. No spot^2/1e7 factor.
Measures, each per run:
  I1 blank rate: share of legs with OI > 0 whose gamma is blank or <= 0; by count and OI-weighted; split by leg (ITM / OTM), by abs(K/S-1) bucket (0-1, 1-2, 2-3, 3-5 %), by time (09:15-10:00, 10:00-14:00, 14:00-15:29), by expiry day / other day.
  I2 ratio gc/gp where both > 0: median, p10, p90, share outside [0.8, 1.25]; same splits, plus by (forward - spot)/step bucket (< -1, -1 to 1, > 1).
  G1 distinct expiries per run. G2 distinct snapshot timestamps among a run's legs and their spread in seconds. G3 duplicate (expiry, strike, leg) records in a run. If the files lack what a check needs, report NOT MEASURABLE; do not estimate and do not query the database.
  N1 production sign error over strikes with OIc != OIp: share where sign(net_P) != sign(OIc - OIp), split "wrong sign" / "zero"; by count and weighted by gross_R; split by cause (a blank leg / both gammas present).
  N2 E_raw(X) = sum abs(net_X - net_R) / GR, X in {P, N}.
  N3 E_shape(X) = sum abs(net_X / sum gross_X - net_R / GR), X in {P, N}.
  N4 T_X = sum net_X / sum gross_X ; error abs(T_X - T_R) ; flag sign(T_X) != sign(T_R) ; flag abs(T_R) >= 0.05.
  N5 peaks: (a) strike with largest positive net, (b) strike with largest abs(net); tie-break nearer to spot then lower strike; X's strike = R's (yes/no) and abs gap in steps; R's lead (top - second)/top for each peak.
  L1 gross shape error: sum abs(gross_X / sum gross_X - gross_R / GR), X in {P, N}.
  K1 share of strikes and of GR with fallback. N2, N3, N4, L1 computed twice: all strikes, and strikes without fallback only.
Output of the full run (STAGE B, not now): one row per run to fix/audit/runs.csv; aggregation in a second script fix/audit/report.py reading only runs.csv.

A3. Self-test: fix/audit/self_test.py with a hand-made run of 5 strikes whose answers you compute by hand in comments, including one strike with a blank put gamma, one with a blank call gamma, one with gc != gp, one with OIc = OIp. It must check gVS, net_P, net_N, N1 flags, E_raw, E_shape and T for P and N. Run it, print the file and its output in full.

A4. Worked example on ONE real run only: NIFTY, 2026-11-18, the first market run at or after 11:00 IST. Print: run timestamp IST, spot, forward, expiry, number of strikes; then a table of EVERY strike in the set with strike, OIc, OIp, gc, gp, gVS, gK, fallback, net_P, net_N, net_R, gross_R (full precision, no rounding beyond 6 significant figures); then the run's N1, N2, N3, N4, N5, L1, K1 values for P and N. Print G1, G2, G3 for that run and say which fields in the chain files they came from. Do not open any other run.

Then print sha256 of audit.py and self_test.py, and STOP. Do not start the full run. Wait for RELEASE.

END: one line each - what ran, what did not, anything stopped by a gate.

---

## Message 2 — the self-test correction

Do not create self_test.py as written. It re-implements net_P, net_N, N1, E_raw, E_shape and T inside the test and imports only gvs_of, _pick and _lead from audit.py, so a bug in audit.py's own measure code could not make it fail.

Change it like this:
1. In audit.py, put ALL measure arithmetic (per-strike net/gross for P, N and R, then N1, N2, N3, N4, N5, L1, K1, for all strikes and for no-fallback strikes) into one pure function that takes the per-strike inputs (gc, gp, OIc, OIp, gK, fallback), spot and step, and returns the record. audit_run must call that function and nothing else for the measures.
2. self_test.py builds the planted per-strike inputs and calls that same function, then compares its output with hand answers written in the docstring. No measure arithmetic inside the test.
3. Keep the five planted strikes and add a sixth where production's sign is wrong because of a blank leg: call gamma blank, put gamma 0.0010, OIc 3000, OIp 1000, gK 0.0010 (wanted sign +, production sign -). Redo every hand answer for six strikes and show the working in the docstring.
4. Add one mutation check: run the same function with net_P's put term added instead of subtracted and confirm the test FAILS; print that it did.
5. With the Stage A output, also print audit.py lines 1 to 230 in full in your reply text.

Everything else in the task stands, including STOP after Stage A.

---

## Message 3 — the STAGE A follow-up

Still STAGE A. Do not start the full run.

Type the following in your reply text itself, not as tool output:
1. The full 50-strike A4 table exactly as it was printed (all columns, all rows).
2. audit.py lines 116 to 260.
3. For the A4 run only (run_id 8549f30e-345c-468a-95ac-9c758952d366): the K pin, the VS pin and K's lead recorded for that run_id in fix/replay_v2/runs.csv, beside the strike with the largest gross_R and the strike with the largest gross_N from the audit record, and the audit's own (top - second)/top on gross_R. Say MATCH or DIFFERS for each of the three. Do not open any other run.
4. Save the full text of the task prompt you were given for this audit (PART 1 and PART 2, plus the self-test correction and this message) to fix/audit/PROMPT.md, with first line `<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/audit/PROMPT.md -->`, and print its sha256.

Then STOP and wait for RELEASE.

---

## Message 5 - post-hoc decomposition

POST-HOC follow-up to the audit. Not part of the frozen rule; label every output POST-HOC. Conditions as Stage B: no database, no git writes, write only under fix/audit/, ulimit -v 700000, python3 -B, one symbol-day in memory at a time, detached if over 2 minutes, never pipe a run into head or tail. Do not change results.md, runs.csv or any existing measure. E_raw, E_shape, T error, the N5 peaks and the lead >= 5 % classification are used exactly as defined; no new normalisation or exclusion.

0. Count first, from the chain files, per symbol, over legs with OI > 0 in the strike set on market runs: gamma field missing (null or empty) ; present and exactly 0 ; present and > 0. By count and OI-weighted, and split in-the-money / out-of-the-money. Say how each is represented in the files.

1. Add two constructions to the measure function. The per-strike input gains two booleans, gc_missing and gp_missing (true only when the raw field is missing, false when it is present, including a present 0).
   B1 (missing filled only): gc' = gp if gc_missing else gc ; gp' = gc if gp_missing else gp ; a present 0 stays 0. If both are missing both stay 0.
   B2 (missing or zero filled): gc' = gc if gc > 0 else gp ; gp' = gp if gp > 0 else gc.
   For each: net = gc'*OIc - gp'*OIp ; gross = gc'*OIc + gp'*OIp ; then E_raw, E_shape, T error and both N5 peaks exactly as for P and N.
   Self-test first, on the six planted strikes with 25000 put MISSING, 25050 call PRESENT ZERO, 25150 call MISSING. Hand answers, stated before you run:
     B1: net = 0, 0, 1, -6, -1, 2 ; sum net = -4 ; sum gross = 22 ; E_raw = 5/19
     B2: net = 0, 0, 1, -4, -1, 2 ; sum net = -2 ; sum gross = 24 ; E_raw = 3/19
   If the code disagrees, stop and show both; do not change the hand answers.

2. Re-run all files to fix/audit/runs_decomp.csv. Check the P and N columns are identical to runs.csv on every run and print the number that differ.

3. Write fix/audit/decomp.md and type in your reply text, per symbol:
   - mean and median of E_raw, E_shape and T error for P, B1, B2, N
   - attribution on the means, for each error: P - B1, P - B2, P - N, and the shares (P - B1)/(P - N) and (P - B2)/(P - N). Print NA if the denominator is 0. Do not clip values above 100 % or below 0.
   - N5 agreement with R on clear-lead runs for P, B1, B2, N, both peaks, with denominators
   - the same error means for expiry-day runs and for other days
   - by DAY: number of days on which N's mean is lower than P's, for E_raw, E_shape and T error, out of 58

4. The days where N's mean E_shape is higher than P's (NIFTY 2026-10-09; SENSEX 2026-10-27, 10-28, 10-29, 11-11, 11-17, 11-19). For each day, and then for the pooled other days of that symbol as a comparison line:
   runs ; days to expiry ; mean E_shape for P, B1, B2, N ; mean abs(T_R) ; mean forward gap in steps ; missing rate and zero rate OI-weighted ; mean K1 fallback share of GR ; mean sigma_atm ; OI-weighted share of legs whose gamma is below 0.00010 (two significant digits or fewer) ; share of total gross_R on the top strike ; number of frozen runs if fix/replay_v2/runs.csv carries a frozen flag (name the column, or say there is none).
   Do not offer an explanation unless a column separates these days from the comparison line; say plainly if none does.

5. Rebuild SHA256SUMS and print sha256 of decomp.md and runs_decomp.csv. Append this prompt to fix/audit/PROMPT.md under a heading "Message 5 - post-hoc decomposition".

END: one line each - what ran, what did not, anything that stopped.
