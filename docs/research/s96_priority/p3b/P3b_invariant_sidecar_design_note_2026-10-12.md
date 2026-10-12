# P3b — per-cycle invariants and independent recompute, as a sidecar (DESIGN NOTE, DRAFT)

**Status: RULED S96-H (2026-10-12 ~07:05 IST): H1–H8 as recommended.** The DDL apply is an operator action after the close. Roadmap §2.1 P3 (= R2.2 + R2.3), phase b.
Risk class **SC**. Operator approval to start: 2026-10-12 06:50 IST ("Note now, build to 08:30").

## 1. What it is

P3a (`tests/test_p3a_invariants.py`, `882df80`) checks the stored γ numbers against the raw chain on six frozen days,
offline. P3b runs **the same checks on every live cycle** and writes the result to its own table, so a broken writer
shows up the same day rather than at the next golden-day run.

Exit evidence (R2.2 / R2.3): an invariant table populated per cycle; an agreement report per cycle.

## 2. Checks — identical definitions and tolerances to P3a (not re-tuned)

| ID | Check | Asserted? | Tolerance |
|---|---|---|---|
| I1 | Σ `gex_strike_snapshots.gex_cr` per (run, expiry) = `gamma_metrics.net_gex` | yes | abs ≤ 0.01 Cr |
| I2 | per strike, `gex_cr` = recompute from the raw chain: γ·OI·S²/1e7, PE negative, 0 if γ = 0 or OI ≤ 0, 0 if \|K−S\|/S > 0.05 and \|γ\| > 5e-5 | yes | abs ≤ 1e-6 Cr + 1e-9 rel |
| I3 | `oi_call` / `oi_put` = Σ chain OI by type at the strike | yes | exact |
| I4 | `gamma_concentration` = max\|gex\| / Σ\|gex\| | yes | abs ≤ 1e-6 |
| I5 | flip lies in an interval where the cumulative sum changes sign (ascending, descending) | descriptive | — |
| I6 | put-call parity on mids vs (S − K): share of strikes outside the summed half-spreads | descriptive | — |

I2 is the R2.3 independent recompute: the writer is Python (`compute_gamma_metrics_local.py`), P3a is a second Python
implementation, and P3b's SQL is a third. Nothing is imported from the writer.

## 3. Proposed rulings

| # | Decision | Recommendation | Alternative |
|---|---|---|---|
| **H1** | Where it runs | **In the database:** a SQL function `p3b_check_runs()` called by `pg_cron`. No new process or credential on the box (RAM is the tight resource, R1.9), and no `.env` | Python on the box via cron, reusing P3a's code. Needs a write credential, and loads the t3.small at cycle time |
| **H2** | Table | `public.p3b_invariant_checks`: one row per (symbol, expiry_date, run_id, check_id). Columns: ts, status (OK / FAIL / NOT_COMPUTED), n_checked, n_fail, max_abs_diff, detail jsonb (first 5 failing strikes), checked_at, fn_version | One wide row per run |
| **H3** | Schedule and which runs | `*/5 3-10 * * 1-5` (UTC). Each sweep checks every run from the last 60 min that has no rows yet **and** is ≥ 3 min old, so a run being written is never checked half-done. Idempotent; a missed tick catches up | Fire after each cycle from the runner (that touches the live path, so it's LIVE, not SC) |
| **H4** | Access | RLS on + a `merdian_ro` SELECT policy in the same migration; no anon or authenticated grant; the function is SECURITY DEFINER with EXECUTE revoked from PUBLIC, anon and authenticated (§11.1 #3) | — |
| **H5** | Off switch | `SELECT cron.unschedule('p3b_invariants');`, named in the DDL header | A `merdian_parameters` flag (a parameter read can fail open, §11.1 #14) |
| **H6** | Heartbeat | One `kind = 'sweep'` row per run of the sweep, even when it finds no runs, plus a `data_contracts` row so the contract runner (R1.2) marks it STALE/MISSING | — |
| **H7** | Consumers | **None in v1.** Shadow only: no board tile, no alert. An alert or tile later needs its own ruling | Telegram on FAIL now |
| **H8** | Retention | Keep (≈ 6 checks × ≤ 2 expiries × 2 symbols × ~80 runs ≈ 1,900 rows/day; under 1 MB/month) | Prune at 90 days |

## 4. Tests (Rule 0: every check must be able to fail for the reason it names)

Run on local Postgres 16 with the six golden days loaded, never against live:

- **T1 — agreement with P3a.** Per run and per check, the SQL function's n_checked / n_fail equal P3a's counts. Expected values come from running P3a, not from memory.
- **T2 — mutants.** P3a's four mutants (gex +0.05; oi_call +1; concentration +0.01; PE sign lost), each planted inside a rolled-back transaction, must each produce a FAIL row for the named check. A mutant that changes nothing reports NOT APPLIED, not caught.
- **T3 — states.**
  - A run with no `gamma_metrics` row → I1/I4 NOT_COMPUTED.
  - A run younger than 3 min → not checked.
  - A second sweep → 0 new rows.
  - ~~The 10-02 holiday → a sweep row with no checks.~~ **Corrected before the run:** the 10-02 golden days each hold one
    γ run (the writer ran once on the holiday; P3a checks it), so 10-02 is checked like any day. The empty case is tested
    on a window with no runs (2026-10-03) instead.
  - A sweep that errors → one SWEEP_ERROR row, no check rows.
- **T4 — real volume.** The function's read body as a plain query through `bin/roq.sh` over the whole 10-09 session (both symbols, every run): cost and counts. A FAIL there is a finding about the writer, not a test failure.

Rule 23: T1–T3 finish before 08:30 IST, under `ulimit -v`. T4 is a bounded read and may run any time.

## 5. Not in scope

- No board change.
- No change to the writer or to the cycle.
- No backfill of past days. P3a covers the golden days; a historical sweep would be a separate RO item.

## 6. Fixture result (2026-10-12 07:24–07:25 IST, local Postgres 16, `ulimit -v 700000`, 35 s) — P3B FIXTURE PASS

- **T1:** on all six golden days, every check's n_checked and n_fail equal P3a's, run on the same files in the same run
  (0 mismatches). Totals: I2 = I3 = 45,549 strikes, 0 fails. I5 ascending 75/57/11/43/1/1, descending 0 on every day. I6 counts
  equal P3a's restricted to γ runs. P3a re-run on the staged files: P3A PASS.
- **T2:** 24 of 24 mutants (4 × 6 days) each changed exactly one row and were caught on the named check, with no FAIL rows on any
  other run. "PE sign lost" also fails I3, as it should: the flipped leg leaves the PE OI sum.
- **T3:**
  - no γ-metrics row → I1 and I4 NOT_COMPUTED, I2 and I3 OK;
  - the youngest run is skipped under the 3-min age rule (76 of 77);
  - a second sweep → 0 runs, +1 sweep row (463 → 464);
  - an empty window → one SWEEP_OK with n = 0;
  - a forced error → one SWEEP_ERROR row, returns −1.
- **Two corrections found by the run, both in my test, not in the function:**
  - I expected I6 = INFO on the 09:00 pre-open run. That run has 0 quoted legs, so NOT_COMPUTED is right. The test now derives that
    expectation from the run's own quotes.
  - The harness compared one sweep call's run count per symbol-day, but a sweep takes every symbol in its window. It now compares
    the runs that have check rows.
- **A cost defect found and fixed before any live use:** ts bounds written as subqueries over the temp candidate table took
  **55 s** for one day. Bounds as variables, plus `ANALYZE` on the temp table, gave **0.69 s**.
- **T4, first attempt (07:43 IST): the 10-09 body hit roq's 30 s statement timeout at real volume.** The cause was the per-run
  correlated subqueries (sum and top-1 over `gs`, the I2/I3 lateral over `st2`, the no-chain count) and the `gamma_metrics` lateral.
  Each scanned the whole day once per run, which is O(runs × rows). The fixture day was too small to show it. This is the
  D.49.7 class: a check is tested at real volume, not only on local fixtures.
- **Rev 2 (`p3b-v1.1`, 07:44 IST):**
  - each of those is now one GROUP BY, joined by key;
  - `gamma_metrics` is read once, bounded by ts (gm.ts = the run's ts on all 313 fixture runs).
  - The fixture test was re-run from scratch at 07:44:06–07:44:27 IST: **P3B FIXTURE PASS** (0 mismatches, 24/24 mutants).
  - The body over all six fixture days in one query (313 runs, 45,549 strikes, 216,270 chain rows): 1,008 ms.
- **T4, second attempt (07:48): timed out again.** The plan (07:49) showed why:
  - the planner estimates **1 candidate run** (the actual number is 154);
  - every CTE downstream inherits that estimate;
  - so strikes × chain legs are joined as a **nested loop with a join filter**.
- **Rev 3 (`p3b-v1.2`): `SET enable_nestloop = off` as the function's own SET clause**, scoped to `p3b_sweep` only.
  - The whole 10-09 day under hash joins took **1,902 ms**, with no Seq Scan on the three tables. The candidate query alone took 38 ms.
  - The fixture test was re-run at 07:55:19–07:57:02: **P3B FIXTURE PASS**. The fixture run is slower under the setting
    (1 min 43 s), but stays inside the 08:30 rule.
- **T4c, real volume, 10-09 (07:54), 154 runs:**
  - I1–I4 have **n_fail 0** on both symbols, so the live writer met every invariant that day.
  - I2/I3 strikes: NIFTY 8,316, SENSEX 10,882. Together that is 19,198, equal to the candidate scan's actual row count.
  - I6 outside the summed half-spreads: NIFTY 5,128 of 7,917, SENSEX 3,982 of 12,361. This is descriptive only.
- **DDL dry run** (`sql/2026-10-12_s96_p3b_invariant_checks.sql`, on a fixture copy with `run_id` as uuid, `cron` stubbed):
  - Section A's verification SELECT returned exactly its stated PASS row.
  - The uuid-typed sweep on 10-01 gave the same counts as T1.
