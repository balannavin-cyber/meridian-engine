<!-- pk: lane=engine; git=meridian-engine:docs/research/s107/engine_to_pin_LATEST.md -->
# Engine to pin lane: standing note

**Rewritten:** Thu 2026-11-26, 10:30 IST, by the engine stream at the S107 close. Replaces the 06:35 version. Two
changes: section 4 gains the dates of the runs with no chain check (derived, not read), and the note now has a git
home (`docs/research/s107/`, byte for byte). Section 1.4 is still waiting on one read.

## 1. Writer-change dates, 2026-05-25 to 2026-11-25

### The answer

**No change, in git.** The code that produces `oi_call`, `oi_put`, `gamma_call`, `gamma_put`, `spot` and `gex_cr` in a `gex_strike_snapshots` row is identical at every commit that touched the writer in the period, from the commit that introduced the table's writer to `origin/main` today.

**What I cannot state from git:** what the production host actually ran on each date. Section 1.4 has the one read that settles it. Until that read is in, treat the answer as "no change in the committed code", not "no change in production".

### 1.1 How it was checked

I parsed `compute_gamma_metrics_local.py` and (from 25 Oct) `merdian_compute/gamma.py` at each of the ten commits below and compared every function as a syntax tree, so comments and layout do not count and any change to logic does.

Identical at all ten commits:

| Function | What it decides |
|---|---|
| `build_gss_rows` | The row itself: sums OI per leg, takes the first non-zero gamma per leg, sums `gex_cr`, stamps `spot` |
| `signed_gamma_exposure` | Each leg's `gex_cr` contribution, including the 5 % / 5e-5 guard and the 1e7 divisor |
| `to_float` | Number parsing for every field |
| `infer_spot` | Which spot the run uses (first positive spot in the chain rows) |
| `fetch_option_chain_rows` | Which chain rows are read for a `run_id` |
| `filter_usable_option_rows` | The usable-row filter (not applied to the per-strike rows, which use the raw rows) |
| `upsert_gex_strike_snapshots` | The write, upsert on `run_id, strike, expiry_date` |
| `_dte_from_ts` | `dte` |

The call is also unchanged in substance: `build_gss_rows(option_rows_raw, spot, symbol, ts, expiry_date, run_id)` with `spot = infer_spot(option_rows_raw)`, before and after the 25 Oct refactor.

### 1.2 Every commit that touched the writer in the period

Commit dates are from git. Deploy dates are stated only where a record gives one.

| Commit date | Commit | What changed | Effect on the six fields |
|---|---|---|---|
| 2026-05-25 | (SQL) `2026-05-25_enh80_schema_v2_migration.sql` | Table truncated and moved to schema v2 (`gamma_call` / `gamma_put` split) | Start of the stored history. Nothing older exists |
| 2026-05-26 | `a776d8a` | S37: `build_gss_rows` and the upsert added | Introduces the code |
| 2026-06-01 | `4044410` | S41: VIX, `max_gamma_strike`, pin risk score added to `gamma_metrics` | None |
| 2026-06-21 | `963b062` | Three lines: strip a stray `--shadow` argument. Commit message says it records working-tree changes already in production | None |
| 2026-07-02 | `dc63bb3` | `compute_flip_level` made regime-conditional | None (flip level is a `gamma_metrics` column) |
| 2026-09-22 | `b094fa2` | S80: `infer_expiry_date` returns the earliest expiry and raises if a run holds more than one | None on the six fields. It can change `expiry_date` / `dte` only on a run with two expiries, and the backfill found no such stored run |
| 2026-10-05 | `ca79717` | One line: ledger arguments on the execution log | None |
| 2026-10-25 | `11f2cbe` | S101: math moved to `merdian_compute/gamma.py`; writer imports it | None. Functions identical before and after |
| 2026-10-25 | `4ed5671` | S101: `compute_gamma_core` composed in the package; writer calls it | None. Same call, same arguments |
| 2026-10-31 | `c11b564` | S103: the prior-row read for straddle velocity bounded to the session | None |

**The one deploy with a record:** S101 (`11f2cbe`, `4ed5671`) went live on the box on **2026-10-26 at 17:08 IST** at `4a1d8e1`, with a golden replay of 486 of 486 runs equal before and after, and the first unattended run on 27 Oct (System Map, S101 section; session log). For the other rows I have the commit date only.

### 1.3 Three things beside the writer that you should weigh

1. **The production host changed during the period.** The Deployment Topology records the Windows machine as the primary writer of `gamma_metrics` earlier in the year and, measured on 2026-09-10, as running nothing, with the AWS box as the writer. The same repository runs on both (Python 3.12 on Windows, 3.10 on the box). I have not found the cut-over date in the documents. The read in 1.4 gives it. The early short and broken days (25 May to 17 Jun) may belong to this; that is a guess.
2. **What reaches the writer changed on 2026-09-22.** Ingest began capturing two expiries per symbol (`8d51cce`, S81), each under its own `run_id`, and the runner was changed to hand the gamma writer the front expiry's `run_id` (`89ad2bb`). This changes which chain run is processed, not how a row is computed.
3. **Ingest's field mapping.** I looked at the diff of every commit to `ingest_option_chain_local.py` in the period for lines touching `gamma`, `oi`, `spot`, `strike` or `option_type` and found none changed. That is a search of diffs, not a syntax-tree comparison, so it is weaker than 1.1.

Other writers: none. In git, `compute_gamma_metrics_local.py` is the only code that writes `gex_strike_snapshots`. The older gamma backfill scripts write `gamma_metrics` and predate the table. No SQL in `sql/` updates or deletes its rows after the 25 May truncate.

### 1.4 The read that turns "no change in git" into "no change in production"

Every writer run logs its host and the repository HEAD in `script_execution_log`. Asked of the operator on 26 Nov; **not yet returned**:

```sql
SELECT count(*) AS n_groups, json_agg(json_build_object('host', host, 'git_sha', git_sha, 'first_day', first_day, 'last_day', last_day, 'days', days, 'runs', runs) ORDER BY first_day, host) AS writers FROM (SELECT host, git_sha, min(trade_date) AS first_day, max(trade_date) AS last_day, count(DISTINCT trade_date) AS days, count(*) AS runs FROM public.script_execution_log WHERE script_name = 'compute_gamma_metrics_local.py' AND trade_date BETWEEN '2026-05-25' AND '2026-11-25' AND actual_writes ? 'gex_strike_snapshots' GROUP BY host, git_sha) x;
```

How to read it: any `git_sha` that is a commit at or after `a776d8a` ran the code in 1.1. A blank `git_sha`, or one not in the repository, is a run whose code I cannot vouch for. Two limits that the read cannot remove: the HEAD says nothing about uncommitted edits in the working tree on that day (`963b062` shows that has happened), and the log may not reach back to May.

### 1.5 What this means for step 9

- On the committed code, the 8,983 unchecked runs and the 10,067 checked runs were written by the same row-building code. There is no writer period without a checked run, because there is one writer period.
- If you want the stricter statement, wait for 1.4 and mark as "unverified provenance" only the dates whose logged HEAD is blank, unknown, or missing from the log.

## 2. Why 240 sweep calls for 185 calendar days

The monthly statements started on 1 May, not 25 May, and September was run twice by mistake. Calls: May 31, June 30, July 31, August 31, September 30 twice, October 31, November 25, which is 239, plus the single B1 call on 27 Aug. A call on a day with nothing left to check writes one `SWEEP_OK` row with 0 runs, so the extra calls added no check rows: every check has exactly 19,050.

## 3. Your rulings of 05:45, taken for planning

- `v_gex2_*` views will be planned as one family release on one method version (net gamma, strike exposure, concentration, Net peak, net river). Nothing built until approved.
- The eight isolation and recovery checks will be shown with evidence before the writer hook is put up for approval. Two of them (interrupted write, a second `--apply` over written days) need an operator run; I will bring those as one list when you ask for the gate.
- No Pin Band rebuild, no label changes.

## 4. B3, as accepted

- Range 2026-05-25 to 2026-11-25. NIFTY 9,553 runs, 1,078,346 strike rows, 123 days. SENSEX 9,497 runs, 1,601,425 strike rows, 124 days. Total 19,050 runs, 2,679,771 strike rows. Equal to the stored V1 counts. Stamp `v2-1.2-gss`, code `25747092c77c385e3e5d539a8a1829c1227b6bc6`.
- How it was written: 27 Aug as B1 (166 runs, 23,323 rows); the main apply 2026-01-01 to 2026-11-24 (`built=18710 strike_rows=2624986 written_runs=18710`, 8,409 s, `already=166`); 25 Nov alone (174 runs, 31,462 rows, 94 s).
- Input errors: 0. Rerun (dry): `runs=19050 already=19050 input_error=0 built=0 strike_rows=0 written_runs=0 read_rows=2679771 elapsed_s=2611`.
- Sweep (240 calls, all `SWEEP_OK`): V0, V2, V3, V4 OK on 19,050; V1 OK on 10,067 and NOT_COMPUTED on 8,983; largest differences 7.5e-9 (V2), 4.4e-16 (V3), 6.7e-16 (V4); V1 largest difference 0.
- **Which runs have no chain check (new, derived).** Summing the per-day run counts the sweeps printed, the stored runs from 2026-08-26 onward number exactly 10,067. So the 8,983 runs with V1 NOT_COMPUTED are those of **2026-05-25 → 2026-08-25**, and every run from 2026-08-26 is checked against the chain. This is arithmetic on counts, not a read per date; your step 9 reads the V1 status per run and will confirm or correct it.
- 161 of 247 day-symbols are not 83 runs; 87 per symbol on every day from 26 Oct except 17 Nov (78). A run between 15:21 and 15:39 IST exists on 75 of 123 NIFTY days and 74 of 124 SENSEX days. Weekdays with no stored run: 28 May, 3, 4 and 8 Jun, 14 Sep, 20 and 21 Oct, 10 and 24 Nov (not checked against the holiday list).

## 5. Where S107's engine records are

- Registers: ENH-149 (gross pin, Board Pin), ENH-150 (gamma V2), ADR-033 §9, Assumption Register §D.61 and §D.62, Data Inventory §13, TD-PIN2-NEW-1…13, TD-PIN3-NEW-1…3. Your MR-PIN3 intake rows are taken in `docs/registers/intake/I003.md`.
- The engine's package files (code, SQL, Board prompts and scripts, the manual source) move from `pin/v2-check` to `main` by path in the engine's close branch. Your check files on that branch are not touched.

## 6. State

- Applied to the database: `v_gex_strike_rank_gross`, `v_gex_pin_gross`, `gex_strike_v2`, `gex_run_v2`, `p3b2_invariant_checks`, `p3b2_sweep`. Full history backfilled to 25 Nov. No job scheduled.
- Live: Board `d7642c2`.
- Not approved: writer hook, the `p3b2` job, `v_gex2_*` views, any Board tile.
- Step 9 is yours.
