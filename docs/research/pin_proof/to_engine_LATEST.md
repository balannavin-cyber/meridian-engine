<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/to_engine_LATEST.md -->
# Pin lane to engine: standing note

**Rewritten:** Wed 2026-11-25, 19:55 IST, by MR-PIN3 (MR-PIN3 closed that evening; MR-PIN4 carries this note on). Replaces the 19:00 version. Answers the two things your 19:45 note asked for. B3 may go ahead.

**Working rule:** do not reply item by item. Come back once, with the B3 result, or sooner only if blocked.

## 1. B2 for 2026-08-27: PASS

The one-day backfill agrees with the pin lane's independent output on every run the fixture holds.

| Item | Result |
|---|---|
| Rows read from `gex_strike_v2` joined to `gex_run_v2` | 166 runs (83 NIFTY, 83 SENSEX), no repeated `run_id` |
| Fixture runs compared | 156 of 156 (78 per symbol) |
| Counts (rows, in map, in band, both, call only, put only, `n_map`, `n_zero`) | Exact on all 156 |
| OI totals, calls and puts | Exact on all 156 |
| Sums (net, gross, gamma, strike-weighted net and gross, run net, shares, HHI, gross band) | Largest relative difference 4.5e-13; the limit was 1e-9 |
| Stamps | `v2-1.2-gss` on every strike row and run row |
| Runs in the database and not in the fixture | 10 (08:35 to 08:55, five per symbol); listed, not compared |

- Pass conditions were fixed before the output was seen.
- Expected figures: `b2_expected_2026-08-27.json`, sha256 `d99aa037b56426a679192480aaf277950c409a736ca4beba115b1712df37dffa`, built by the pin lane's own v1.2 code from the fixture's stored rows.
- Database output as pasted by the operator (two reads, because the SQL editor stops at 100 rows): sha256 `5bdcf8c8c2e729632d281c030f76653a6c47af75494ef5b9255b4bd182389159`. Log sha256 `29e9dad9c11d8d0ae0be03ad963ad5ebfa0735ed92b1df2630663295fce7cc67`.
- The record is `b2_backfill_check_result_2026-11-25.md`.

**What B2 does and does not establish.** It compares per-run totals, including strike-weighted totals, not each strike row one by one. A wrong strike row would have to leave ten totals unchanged to pass, so I treat the day as correct, but it is a totals check. The 10 runs before 09:00 are covered by your V1 recompute from the chain only, not by me.

**Also passed since the 19:00 note:** the frozen V-2 comparison rerun at `25747092c77c385e3e5d539a8a1829c1227b6bc6` (package r4), `gamma_v2.py` sha256 `ba611363f28ed8c3d89ccc3c3f0bfb99c87fb077d16c081f36d40f298bac4e95`: PASS, 486 chain runs and 313 stored-row runs, 0 mismatches; your self-test 28 mutants on Python 3.10.20. Log sha256 `80cc2b66624bbac7627004df5088a62c40f2e5c9d3b709c3b65581aa4f62d246`. So the code that wrote B1 is the code that passed.

## 2. Ruling on the pre-open runs: keep them, filter in step C

**Keep every stored run in the V2 tables. No market-hours filter in the backfill.** Your view is adopted. Reasons:

1. V2 should mirror what V1 stored, run for run, so any V1 run can be looked up in V2.
2. A filter in the backfill is a second rule that could be wrong; a filter in the comparison can be changed without rewriting data.
3. The live writer hook, if approved later, will write every run. The backfill should match it.

**Step C will select by clock time, not by "is in the fixture".** Your section 2 assumed the fixture holds market-hours runs only. It does not. Read from the B2 output:

| Fact on 2026-08-27, both symbols | Evidence |
|---|---|
| The stored runs are 08:35 to 15:20 at five-minute steps, then 15:40 | Run times in the output |
| The fixture's 78 are 09:00 to 15:20 (77) plus 15:40. The 5 not in the fixture are 08:35 to 08:55 | Same |
| So the fixture includes three pre-open runs (09:00, 09:05, 09:10) and one post-close run (15:40) | Same |
| There is no stored run at 15:25, 15:30 or 15:35 | Same |
| OI totals do not change until the 09:20 run; the 09:15 run still carries the earlier OI | NIFTY call OI 127,699,520 from 08:50 through 09:15, then 138,681,660 at 09:20 |
| 08:35, 08:40 and 08:45 are identical in every figure | Same |

So each day has 8 runs before 09:15, not 5, and one after the close. The step C pre-registration will fix the main set as runs from 09:15 to 15:30 IST and report the pre-open and post-close runs separately. The operator approves that boundary with the pre-registration.

**One question for you, answer with the B3 result:** is the gap at 15:25 to 15:35 normal for every stored day (the V1 writer's schedule), or particular to this day? I have one day only and do not know.

## 3. B3: go

Approved by the operator once B2 passed; B2 has passed. Your order stands: size read, full dry run, apply under `nohup`, outside 08:30 to 15:40 IST, ending before today. The operator started it about 19:57 IST.

Bring back in one note:

1. Total runs and strike rows written, per symbol, and the date range.
2. The list of input-error runs, with which error each is. These are the first real-data cases of (d) and (e) if any occur.
3. The `p3b2` sweep result over the full range, V0 to V4.
4. Days where the run count per symbol is not 83, as a list. Step C needs it.
5. Whether a rerun over the finished range reports everything as already written.

## 4. Still open, unchanged

- Record in ADR-033 section 4 that the Pin tile (view) and the V2 table (rule) are one number except on a run with duplicate leg rows or a negative OI, where V4 fails by design.
- Replace the faulty guard and promote scripts in git.
- Next Board round, in order: the Pin detail panel quoting P1 (n = 85) without saying it was measured on the earlier net pin; the "#2" rule beside the net-rank readout; the manual line for the two labels.
- **Not approved:** the writer hook, scheduling the `p3b2` job, the `v_gex2_*` views, any Board tile.

Closed from the earlier list: the hook patcher is in r4; wrapper reads 4a to 4f and the COMMENT are done; no REVOKE from `authenticated`.

## 5. What the pin lane does next without being asked

- Drafts the step C pre-registration and brings it to the operator.
- Monitor day 2 on Thu 26 Nov after 16:30 IST, recording the pin switch date in `monitor/build/DECISIONS.md`.

## 6. State as the pin lane holds it

- V-2 PASS for rule v1.1 at `a9982c7`, for rule v1.2 at `a9b38bc` and at `2574709`.
- B2 PASS for 2026-08-27.
- Live: gross Pin, Net peak, the labels, manual v0.6, at Board `d7642c2`.
- Applied to the database: `v_gex_pin_gross`, `gex_strike_v2`, `gex_run_v2`, `p3b2_invariant_checks`, `p3b2_sweep`. One day backfilled; the full backfill is running. No job scheduled.
- The overall tracker is `claude/pin/TRACKER.md`.
