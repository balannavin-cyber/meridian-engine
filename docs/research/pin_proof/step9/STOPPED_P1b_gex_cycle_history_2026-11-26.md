# STOPPED at P1b: `gex_cycle_history` holds no row before 2026-10-05

**When:** Thu 2026-11-26, 06:50 IST. MR-PIN4 step 9, preparation session.
**Where:** P1b, the zero-count gate. P1c, P1d, P2 and P3 were not started.
**One look: UNUSED.** No `per_run.jsonl`, no `run.log`, no outcome figure read.

## The measurement

`symbol = 'NIFTY'`, `ts` in `[2026-08-27 00:00+05:30, 2026-08-28 00:00+05:30)`:

| Relation | rows |
|---|---|
| `gex_run_v2` | 83 |
| `gex_strike_v2` | 8,715 |
| `gex_strike_snapshots` | 8,715 |
| `p3b2_invariant_checks` | 498 |
| **`gex_cycle_history`** | **0** |

Extent of `gex_cycle_history`, whole table, per symbol:

| symbol | rows | min ts (IST) | max ts (IST) | distinct days |
|---|---|---|---|---|
| NIFTY | 2,772 | 2026-10-05 15:20:06 | 2026-11-25 15:40:06 | 34 |
| SENSEX | 2,771 | 2026-10-05 15:20:06 | 2026-11-25 15:40:06 | 34 |

On a day it does hold (`2026-11-25`, NIFTY): 87 rows, 87 distinct `run_id`, 1 distinct
`expiry_date` — so where rows exist the design's `(run_id, symbol)` join is 1:1, and only
one expiry leg is stored per run.

## The zero is the data, not the reader

`has_table_privilege('merdian_ro', 'public.gex_cycle_history', 'SELECT')` = **true**;
`relrowsecurity` = **false**; **0** policies, so there is no policy that could filter.
Adding a grant or a policy would change nothing. A timezone mislabel is also excluded: it
would move the boundary by 5:30, not by five months, and the table's own minimum `ts` is
2026-10-05.

## Why this stops the task

1. **P1b's literal gate.** `gex_cycle_history` must hold rows for 2026-08-27 — it is the
   V1 source for F1, F3, F4, F5 and for the `dte` stratum (`PREREG.md` §4, §5) — and it
   returns 0.
2. **Condition 9: a catalog fact contradicts the design.** `PREREG.md` §2 defines the
   population as *"Runs present in both `gex_run_v2` (stamp `v2-1.2-gss`) and
   `gex_cycle_history`, joined on `run_id` and symbol"* and then states 19,050 runs over
   2026-05-25 to 2026-11-25, 123/124 days per symbol. `gex_cycle_history` can supply a V1
   run-level figure on **34 days**, 2026-10-05 to 2026-11-25, about **5,543 of 19,050
   runs** (2,772 + 2,771). For the other ~13,500 runs the design's V1 side does not exist
   in the table it names. §2's "runs in one table and not the other are counted and listed
   by date" was written for a residue, not for 71 % of the population.
3. The gate is not a grant problem, so P1b's remedy ("the operator must add the grant or
   policy") does not apply, and condition 3 forbids another route.

## The exact question for the operator

**On which population does step 9 run, and from which relation is the V1 run-level figure
read?** Three things follow from the answer and none of them is mine to decide:

- **(a) Population.** Restrict §2 to 2026-10-05 … 2026-11-25 (34 days, ~5,543 runs) and
  re-freeze §2, §5 and the C4 day? C4 names **2026-08-27**, which is outside that window —
  C4 compares V2 against `b2_expected_2026-08-27.json` and needs no V1 row, so it can
  stand as written, but §2's population sentence cannot.
- **(b) Another V1 source.** Is there a V1 run-level relation that covers 2026-05-25
  onward (the S28 bullet in `CLAUDE.md` names `gamma_metrics` as carrying `net_gex`), and
  if so does `PREREG.md` §4's "V1 read from V1's own tables" mean that one for F1/F4/F5?
  I did not look: condition 3's "do not try another route". Note that even with such a
  source, F4 and F5 need V1's own `conc_top1_share` / `conc_hhi` equivalents, and F3 needs
  `pin_leader_strike`.
- **(c) Split the figure set.** F6, F3b, F7, and C1's strike side read
  `gex_strike_snapshots`, which **does** cover 2026-08-27 (8,715 rows). Those could run on
  the full 19,050 runs while F1, F3, F4, F5, C1's run side and C2 run on the 34 days. That
  is a change to §4 and §5 and so is a new pre-registration, not a run-time choice.

## What exists on the box after this stop

`docs/research/pin_proof/step9/`:

- `PREREG.md` — sha256 `eef1981480b8cfb7b92e7396c50cb9ceae9e70f655557a0a33c8f7efbb4a73f0`,
  equal to the expected value.
- `b2_expected_2026-08-27.json` — sha256 `d99aa037…7dffa`, equal to the expected value.
- `PROVENANCE.md` — the facts fixed before the run, as given.
- `CATALOG.md` — P1a and P1b, marked incomplete.
- `sql/`, `out/` — the catalog queries and their raw output.
- **No** `step9_lib.py`, `selftest_step9.py`, `step9_pull.py`, `step9_summary.py`,
  `CODE_SHA256SUMS`, `explain.txt`, `per_run.jsonl`, `run.log`, `RESULT.md`.

Nothing was left running. No branch was created, nothing was committed, nothing was
pushed.
