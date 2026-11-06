# Tape live flow-vs-book: spec v0.1 (MR-OFL4, Fri 2026-11-06, evening IST)

**Status: DRAFT for operator rulings (section 9). Nothing here is built.** Read with `anon_plug_RESULT_S104.md` s5 (database access), `tape_preregistration_v0.4.md` (binding), `rulings_mr_ofl2.md` (R-3 passive side, R-8 package layout), `cc_prompt_tape_t1b.md` (cycle and event definitions), `muhurat_2026-11-08_checklist.md`.

**Purpose.** One `/tape` page that (a) shows, per wall, what the flow did against the book, at 5-minute cycle cadence while the session runs, (b) replays the same view for any loaded day, and (c) leaves a time-stamped record of what the page said, so EOD can check it against the finished offline data. The page is **display only, not evidence**: nothing it shows or stores is an input to the pre-registered scoring.

**How fresh "live" is.** The recorder closes a segment on each 5-minute boundary and uploads it (rehearsal: PutObject p50 2.4 s, max 4.5 s). Cycle T covers the 5-minute bin ending at T (the scoring prompt states [T-5, T); the T1b prompt writes the endpoints the other way, so CC confirms from `cycle.py`). So the label for cycle T can appear roughly 1-2 minutes after T, on the same cadence as the board's chain run. It is not tick-live.

## 1. What is shown, per symbol and cycle

Two walls: the **call wall** K_c (largest `oi_call`, CE leg) and the **put wall** K_p (largest `oi_put`, PE leg), the pre-registered definitions. For each wall at cycle T, one label from {HIT, ABSORBED, THINNING, QUIET, NO_READ} plus display values: `oi_last`, OI build over the lookback (sum of `oi_delta_5`), `resting_imb`, `balance_5`, `classified_share_5`, `buy_5`, `sell_5`, trades since open.

## 2. Architecture

| Part | Where | Does |
|---|---|---|
| **W: live writer** `services/tape_live/` (own package, R-8 precedent) | production box (see 8) | Each cycle: fetch the new segments from S3, run the existing T1a/T1b logic unchanged, read the latest chain run for the walls, write the four `tape_live_*` tables |
| **Tables** `tape_live_cycle`, `tape_live_events`, `tape_live_wall`, `tape_live_label` | engine Supabase | Provisional rows; as-seen label record |
| **Page** `/tape` (Lovable, existing `tape_ro` path) | Marketview | Reads the live tables for today and the six final tables for past days; computes labels with the rules in section 4; read-only |
| **V: verify** `services/tape_live/verify_day.py` | after `load_day` | Recomputes labels from the final rows with the same `rule_version`; reports agreement and every difference with a cause |

**Correction to what I said earlier.** Provisional rows do **not** go into the six `tape_*` tables. `load_day` refuses a day that already has rows unless `--replace`, and the scorer reads `tape_strike_cycle`, `tape_events` and `tape_chain_runs`; mixing provisional rows in would risk contaminating scoring. Provisional rows live in separate `tape_live_*` tables that the scorer never reads (the hashed `scoring_extract.sql` names only the relations in its s1.1, so this holds by construction; a guard asserts it).

**Why the page does not store snapshots.** The browser is read-only: no write credential in a bundle (the 3 Nov anon-key case), and it records only while a tab is open. The record is `tape_live_label`, written by W. The page may keep a UI-only cache in the browser, never as a record.

**Why the production box.** The retail box cannot read S3 (its key is write-only; GetObject denied) and holds no engine database credential by design, and it must not take load 08:30-15:45. The production box can read S3 through its instance role (**UNVERIFIED**: the bucket policy may deny it; check with a single `aws s3 ls`) and already holds the service-role client. The tape code is stdlib and pure, so it runs there unchanged.

**Processing.** Reuse `process_day`, `cycle.py` and `events.py` logic without changing their outputs. Two ways, CC decides from a measurement:
- **B (recommended): carry state per token across segments**, with a guard that incremental output equals batch output byte for byte on 2026-11-04, 11-05, 11-06.
- **A (fallback): re-run the day so far each cycle.** Deterministic and identical by construction; usable only if the measured runtime at 14:00 load is well under the 5-minute cycle and the box has headroom.

**I could not read `process_day.py` or `tape_schema.py` in this session (no repository access).** The column names below come from the T1b prompt; CC asserts them against `services/tape_db/tape_schema.py` and never retypes them. Whether T1a can carry state across segments is for CC's plan to settle from the code.

**Causality.** CONC uses only bins strictly before T; THIN uses only minutes strictly before. Both are causal, so a cycle's live events equal its final events when the same data is present. That is what makes live and offline comparable at all.

## 3. Tables (CC generates the DDL; PKs and intent)

All: RLS on; `SELECT` to `tape_ro` and `merdian_ro` only; no anon; DDL comment naming writer, owner, tier `research`, "display only, never scored". Provenance on every row: `as_of` (writer clock, UTC), `live_run_id`, `code_sha`.

- `tape_live_cycle`: PK `(symbol, trading_day, expiry, strike, leg, ts_ist)`; the `tape_strike_cycle` columns.
- `tape_live_events`: PK as `tape_events`; same columns.
- `tape_live_wall`: PK `(symbol, trading_day, expiry, ts_ist)`; `chain_run_id`, `chain_run_ts`, `call_wall`, `put_wall`, and the two walls' `oi_call`/`oi_put` at that run. The chain run for grid point T is the latest run whose timestamp floored to the 5-minute grid is <= T (the scorer's reconciliation rule). The chain read is a SELECT on `gex_strike_snapshots`, front expiry, in one place.
- `tape_live_label`: PK `(symbol, trading_day, ts_ist, wall, rule_version)`; `strike`, `leg`, `label`, `partial`, `reason`, `flags` jsonb (the derived inputs in section 4). **Insert-only, first label wins** (`ON CONFLICT DO NOTHING`): this is the as-seen record. If a late segment later changes the data, the live-cycle rows are upserted but the label row stays as first written; the verify step reports the difference.

Row volume is small (about 15,000 live-cycle rows a day, a few hundred label rows), so no pruning is planned.

## 4. Rules v1 (pure functions; the page and W implement them separately and both must pass the shared vectors)

**Derivation, per wall at cycle T** (K = the wall strike, leg = CE for the call wall, PE for the put wall; window = (T - 15 min, T], i.e. cycles T-10, T-5, T):
- `wall_known`: a `tape_live_wall` row exists for T.
- `in_window`: `(K, leg)` has a cycle row at T.
- `conc_evaluable`: the strike-leg has >= 12 session bins before T. `thin_evaluable`: >= 20 minutes present in the trailing 30.
- `C` = a `CONC` event at `(K, leg)` with `ts_ist` in the window. `N` = a `THIN` event with `side = ask` at `(K, leg)` in the window (ask on both legs per R-3).
- `untraded`: no trades at `(K, leg)` since the open and T >= 10:00 (the vendor OI artefact, TD-S95-NEW-1: legs with volume 0 have held most of SENSEX OI on some days).

**Label, first match wins:**

1. not `wall_known` -> NO_READ, reason "no chain run"
2. not `in_window` -> NO_READ, "wall outside subscribed window"
3. `untraded` -> NO_READ, "untraded wall (vendor OI)"
4. `conc_evaluable` and `thin_evaluable`: C and N -> **HIT**; C and not N -> **ABSORBED**; not C and N -> **THINNING**; neither -> **QUIET**
5. only `thin_evaluable`: N -> THINNING with `partial = true` ("flow n/a"); not N -> NO_READ, "flow not yet evaluable"
6. otherwise -> NO_READ, "insufficient history"

In words: HIT = flow concentrated at the wall and the offers gave way; ABSORBED = flow concentrated and the book held; THINNING = offers thinning with no concentrated flow; QUIET = neither, and both were measured. **Gaps are never drawn as QUIET** (the board's gap rule): before about 10:20 (12 bins of history) the flow test cannot be evaluated, so early-session walls read THINNING-partial or NO_READ, not QUIET.

Mapping to the pre-registration: C at the wall leg is T1, N is T3. The label is the 2x2 of two pre-registered events, with **no new thresholds**; the only added parameter is the 15-minute lookback (display only). T1 and T3 stay visible as raw flags beside the label. OI build and depth are shown but are not part of the label.

**Shared vectors** (synthetic fixtures, stored as `tapeLabels.vectors.json` for the page and read by the Python tests; CC adds derivation vectors from real-precision rows):

| # | wall_known | in_window | untraded | conc_eval | thin_eval | C | N | expected | partial |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | HIT | 0 |
| 2 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | ABSORBED | 0 |
| 3 | 1 | 1 | 0 | 1 | 1 | 0 | 1 | THINNING | 0 |
| 4 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | QUIET | 0 |
| 5 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | NO_READ | 0 |
| 6 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | NO_READ | 0 |
| 7 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | NO_READ | 0 |
| 8 | 1 | 1 | 0 | 0 | 1 | 0 | 1 | THINNING | 1 |
| 9 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | NO_READ | 0 |
| 10 | 1 | 1 | 0 | 1 | 0 | 1 | 0 | NO_READ | 0 |
| 11 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | NO_READ | 0 |

Mutants the guards must catch: HIT/ABSORBED swapped; NO_READ drawn as QUIET; C counted when not evaluable; lookback 10 or 20 minutes; bid side counted for N; untraded check removed; first-match order changed.

## 5. Verify step (EOD)

After `load_day`, for each `(symbol, trading_day, ts_ist, wall)`: recompute the label from the final `tape_strike_cycle`, `tape_events` and `tape_chain_runs` with the same `rule_version` and compare with the stored as-seen label. Output a summary row per symbol-day (cycles, agreement %) and a list of every difference with a cause: `late_segment`, `partial_cycle`, `chain_run_differs` (live run vs the final run for that grid point), `rule_drift` (page vs Python; should be zero), `other`. Because live and offline run the same causal code, tape-side agreement should be about 100%; the value is in finding lateness, chain-timing and rule-drift. It checks consistency only. Whether a wall held or broke needs spot and chain outcomes and stays with the scorer.

## 6. Improving it, without breaking the pre-registration

- Every label carries `rule_version`. A change is a new version that applies from that day on; old labels are never recomputed into `tape_live_label`. The page may replay an old day under a newer version, labelled "replay", without storing it.
- For the month, what you can improve on is **definition and legibility**: label stability, NO_READ share, agreement with final data, whether the labels read sensibly against your own session notes.
- **Do not tune rules by what price did afterwards on days from 2026-11-05.** Those are the confirmatory days; a tape-vs-outcome look before the one December scoring run is what v0.4 forbids. Outcome-based improvement is a v0.5 matter, tested on days after the scored sample.

## 7. Page (details in the Lovable prompt)

Same page for live and replay: symbol and day selector; LIVE badge only when the day is today and the newest `as_of` is under about 7 minutes old, otherwise a stale banner; one card per wall (label chip, strike, raw T1/T3 flags, the display values), a full-day strip of labels by cycle with NO_READ drawn as a gap; the notice "display only, not evidence"; a diff marker where the stored as-seen label differs from the recomputed one. Polls every 30 s through the `tape_ro` path; GET only; no new key; no outcome, spot or chain overlays.

## 8. Build order and gates

1. **L0, Local, any hour (CC, one session):** plan (Opus), then tester-first rules + vectors + guards + mutants, then W in **replay mode** (feed recorded segments one at a time). **Gate:** replay output equals the offline output byte for byte on 11-04, 11-05, 11-06.
2. **L1, page on staging, EOD mode** (can run in parallel with L0): reads the six final tables for past days, so the review page exists as soon as it is staged. Staging with `--base=/staging/`, guard scan before the rsync, promote after 15:45.
3. **L2, production box:** DDL + access check (`ACCESS PASS` lines extended to the four tables), then W run on a recorded day outside market hours, then one live day in shadow. **Gates:** S3 read from the instance role verified; measured CPU and memory with W niced and `MemoryMax` set; engine cycle latency unchanged. The production-box rule (no test runs 08:30-15:40) needs an explicit ruling for W (R-D).
4. **L3:** promote the live mode on the page; verify step runs after each `load_day`.

Sun 8 Nov (Muhurat) is untouched by any of this. The earliest live day for W is Mon 9 Nov, and only if the L0 and L2 gates have passed.

## 9. Rulings needed (defaults applied until you say otherwise)

- **R-A.** The live labeller joins tape rows to the live chain run, for display. Default: allowed, display only, recorded in `rulings_mr_ofl4.md`; the scorer never reads `tape_live_*`. The v0.4 "scorer is the only join" rule governs evidence.
- **R-B.** Label meaning. Default: HIT = CONC and THIN-ask; ABSORBED = CONC without THIN-ask. If you meant HIT = CONC alone, ABSORBED then needs a different test (for example OI build with the book held); say so before v1 is frozen.
- **R-C.** Lookback 15 minutes (three cycles).
- **R-D.** Writer host = production box, niced and memory-capped, running during market hours.

## 10. Unverified (CC settles from the code or one measurement)

1. Whether T1a/T1b carry state across segments, and the runtime of re-running the day so far.
2. Production instance role and bucket policy for `s3://meridian-tape-raw` reads.
3. Production-box headroom during 09:15-15:30 with the engine running.
4. How long a chain run takes to become readable after its timestamp (listed unverified in MR-OFL3 s5); it sets how stale the wall can be at T.
5. Column names against `tape_schema.py`.
