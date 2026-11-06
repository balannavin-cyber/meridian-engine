# Tape live flow-vs-book, phase L0: plan (Opus, Fri 2026-11-06)

Binding spec: `docs/tape/tape_live_flow_vs_book_spec_v0.1.md`, sha256
`d9e8222838bcd53c7336109273de1f3cf87972767471d56b34eafa5d9e8493e1` (**SPEC HASH OK**, checked at session start).
Branch `tape/live-l0` at `79efb0b`, worktree `C:\wt-tape-live`. Display only, never scored (pre-registration v0.4).
This plan is written before any code. The build step is held until the operator switches `/model`.

## 0. Housekeeping as found

| Check | Result |
|---|---|
| `git status --porcelain` | `?? docs/tape/tape_live_flow_vs_book_spec_v0.1.md` only: the spec the operator copied in (expected, will be committed by explicit path). `.env` excluded via the main checkout's `.git/info/exclude`. **PASS** |
| `git rev-parse --short HEAD` | `79efb0b` **PASS** |
| `git remote -v` | `origin https://github.com/balannavin-cyber/meridian-engine.git` (engine, never pushed); `tape-staging https://github.com/balannavin-cyber/meridian-tape-staging.git` (only `tape/*`, no force). **PASS** |
| Spec sha256 | `d9e82228…e8493e1` **SPEC HASH OK** |
| Offline references valid for the gate | `out_`/`cyc_` manifests: 11-04 `be197b3`, 11-05 `7c64e7d`, 11-06 `79efb0b`, all `dirty: False`; `git diff --stat be197b3 79efb0b -- merdian_compute/tape services/tape_offline` is **empty**, so all three were made by the tape code now at HEAD. |

## 1. What the code says (quoted from the reads)

- `services/tape_offline/process_day.py` `process_symbol` (l.68-92): for each segment in `replay.order_segments` order it calls
  `rp.end_group(cur)` **only when the HHMM changes, before feeding the new group**, then `rp.feed(raw)` per line; at the end
  `end_group(cur)` and `rp.finish()`. Token map: `read_token_map` over **all** `subscriptions_*.json` (first file naming a token wins).
- `merdian_compute/tape/replay.py` `SymbolReplay`: already an incremental object. `feed()` pushes packets onto a heap; `end_group(hhmm)`
  releases packets with exchange epoch `< slot start − 600 s` (`WATERMARK_S = 600`); `finish()` releases everything and renders rows.
  Per-token state (`state`, `last_key`), the `MinuteBook`, the G3 book and the control-event list all live on the object.
  **So T1a carries state across segments today; only the final release is end-of-day.** A packet released after a later one of the
  same token is dropped as `late_beyond_watermark`.
- `merdian_compute/tape/minute.py` `MinuteBook.rows()` (pure) renders the whole book; `render_csv` is the `tape_minute.csv` text.
- `merdian_compute/tape/cycle.py` `build_cycle(rows, added)` takes **dicts of strings** (the CSV) and emits, per strike-leg, a row for
  **every** T from `first_T` to `LAST_T` = 15:30 (l.112 `for T in range(first_T, LAST_T + 1, STEP)`), zero-filled where there is no data.
  Rolling 15/30 sums, `*_cum` and `oi_delta_5` read only earlier bins: causal.
- `events.py`: CONC at bin T from bins strictly before T (`MIN_PRIOR = 12`, l.22), stamped T (l.108). THIN from minutes `[m−30, m)`
  (`THIN_WINDOW = 30`, `THIN_MIN_WINDOW = 20`, l.23-24, l.80), two consecutive minutes, stamped `m + 1` (l.113). Onset only (armed flag):
  causal.
- `chain_events.py` `build_runs` (l.68-105): front expiry = min `expiry_date` at the run's `ts`; `call_wall` = argmax `oi_call`,
  `put_wall` = argmax `oi_put` (l.94-95), ties to the lowest strike, `None` when max ≤ 0. Input columns
  `run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr` (l.6). `chain_runs.csv` (`RUN_COLS`) carries the walls but **not**
  the walls' OI.
- `services/tape_offline/cycle_day.py`: reads `tape_minute.csv` with `csv.DictReader`, `read_added` (first `added_minute` per token,
  files in `sub_sort_key` order), `build_cycle`, `events.candidates`, `render_cycle_csv`, `render_events_csv`.
- `services/tape_db/tape_schema.py`: column authority (section 3 below). `load_day.py`: refuses an existing day unless `--replace`; writes
  only `tape_schema.ORDER`.
- Tests: `test_tape_t1b.py` pattern = argparse `--root`/`--only`, `rule23()` with the R-1 override `TAPE_RULE23_OVERRIDE_R1=1`, generators
  under `tests/tape_t1b/` whose planted truth is computed independently (`gen_cycle.py` `truth_cycle`, `ref_conc`, `ref_thin`); mutants in
  `tests/tape_t1b_mutants.py` = copy tree, one exact-string patch that must match once, run the named guard with `--root`, require exit 1,
  control must pass.
- `tests/run_offline.sh`: **40 steps** (l.3 header; steps 31-40 are the tape suites). `services/tape_runner/install.sh` l.69 ships only
  `services/__init__.py services/tape_runner` (`git archive`), so nothing under `services/tape_live/` can be shipped by it.
- Raw layout: `C:\tape_data\<day>\{NIFTY,SENSEX}\<day>\seg_HHMM[_cN][_rN].ndjson.gz` (segment = floor(recv, 5 min), box clock);
  `session\<day>\subscriptions_HHMMSS.json` (11-06 has `085501`, `090000`, **`143300`**: the token map grows mid-day).

## 2. Decision 1: incremental processing — **B, hybrid**, with A kept as a rebuild path

### Measurements (this machine: Local Windows 11, 8 logical CPUs, Python 3.12.10, single-threaded code; **this is not the production box**,
which is a t3.small with 2 burstable vCPUs and must be measured in L2)

| What | Measured on 2026-11-06 |
|---|---|
| **Option A at the 14:00 mark** (all segments with HHMM < 1400, both symbols, T1a + minute CSV + `build_cycle` + `candidates`) | **144.7 s** wall; T1a NIFTY 66.7 s, SENSEX 76.6 s; render 0.30 s; `build_cycle` 0.47 s; events 0.54 s; 3,628,920 lines, 53,873 minute rows; peak working set 221 MB |
| T1b share | ~1.3 s of 144.7 s: **T1a parsing is 99 % of the cost** |
| Provisional flush on a copy (NIFTY, fed to 14:00) | `copy.deepcopy(SymbolReplay)` **2.28 s** (heap 122,805 packets, 22,169 minute cells) + `finish()` on the copy **0.83 s** |
| Data that reaches the writer after its cycle | 1,156 of 1,715,526 in-session NIFTY packets (**0.067 %**, ~20 per segment, worst 39) sit in segment X with an exchange minute before X |

A is 145 s at 14:00 and grows to ~200 s by 15:30 on a faster machine than production: that is half to two-thirds of the 5-minute cycle,
not "well under". **A is rejected as the per-cycle path.**

### What B is

1. **T1a carried** (one `SymbolReplay` per symbol for the day), fed with exactly `process_symbol`'s call sequence: segments in
   `order_segments` order, `end_group(prev_hhmm)` only when a new HHMM group arrives, `feed()` per line, same gzip error handling.
   Nothing in `replay.py` changes and nothing reaches into its internals except `copy.deepcopy` of the whole object.
2. **Provisional view at cycle T** = `copy.deepcopy(rp).finish()["rows"]` (the real `rp` keeps its heap and watermark). Cost ≈ 3.1 s per
   symbol at 14:00.
3. **T1b re-run over the day so far** each cycle (1.3 s): `minute.render_csv(rows)` → `csv.DictReader(io.StringIO(...))` →
   `build_cycle(…, added)` → `events.candidates`, i.e. the same string round trip `cycle_day` makes, so formatting cannot drift.
   Rows kept: `T <= cycle T`; events kept: `ts_ist <= cycle T`. (Causality makes these equal to the final rows when the same packets
   are present; that is what the guards check, not what this sentence asserts.)
4. **Rebuild (A, once)** — re-create the replay from all segments received so far — on exactly two triggers:
   (a) a segment arrives whose `(HHMM, c, r)` sorts **before** the last group already fed (a late segment, or a `_cN`/`_rN` variant
   of a closed group); (b) a new `subscriptions_*.json` appears (the token map is fixed at `SymbolReplay` construction; extending it in
   place would mean touching `replay.py` internals). Both make the carried state exactly the batch state again. Each rebuild is recorded
   in the manifest with its trigger. Expected ≤ 1-2 per day (11-06: the 14:33 subscription).
5. Estimated per-cycle cost at 14:00 on this machine: feed one segment pair ~2.4 s + flush 6.2 s + T1b 1.3 s ≈ **10 s**; a rebuild
   ≈ 145 s. Both are L2 measurements on the production box.

**Guard (the spec's B condition):** `live-equal-offline` — the accumulated live state after the final cycle equals `cyc_<day>`
`tape_strike_cycle.csv` and `tape_events.csv` byte for byte on 11-04, 11-05, 11-06; plus on fixtures, every cycle's rows at
`T' <= T` equal the batch rows at T' whenever no packet crosses the boundary.

Rejected: B without the rebuild path (a late segment or the 14:33 map change would make the live state diverge from batch for the
rest of the day, silently). Rejected: emitting only watermark-final rows (no provisional flush): a cycle would appear ~15 minutes
after T, against the spec's 1-2 minutes.

## 3. Decision 2: column map (authority `services/tape_db/tape_schema.py`)

Bin endpoints: **[T−5, T)** in minute-start labels — `cycle.py` l.7 *"the bin T with T-5 <= m < T"*, `bin_of` l.36-37
`return 555 + 5 * ((m - 555) // 5 + 1)`. The scoring prompt's convention is the one the code uses; the T1b prompt's (T−5, T] is not.

| Spec name | Exists as | Proof |
|---|---|---|
| `oi_last` | `tape_strike_cycle.oi_last` bigint | `tape_schema.py:57` |
| OI build = Σ `oi_delta_5` | `oi_delta_5` bigint | `tape_schema.py:57` |
| `resting_imb` | double precision | `tape_schema.py:55` |
| `balance_5` | double precision | `tape_schema.py:54` |
| `classified_share_5` | double precision | `tape_schema.py:55` |
| `buy_5`, `sell_5`, (`trades_5`) | bigint | `tape_schema.py:52` |
| `ts_ist` (cycle) | CSV `T` renamed | `tape_schema.py:48` |
| events `kind`, `side`, `ts_ist` | text / timestamptz | `tape_schema.py:67` |
| `chain_run_id`, `call_wall`, `put_wall` | `tape_chain_runs` (`run_id` renamed) | `tape_schema.py:81`, `:83` |
| `tape_live_cycle` key | `tape_strike_cycle` **UNIQUE** (symbol, trading_day, expiry, strike, leg, ts_ist); its PK is (symbol, trading_day, instrument_token, ts_ist) | `tape_schema.py:60-61` |
| `tape_live_events` key | `tape_events` UNIQUE (…, kind, ts_ist, side), no PK | `tape_schema.py:70` |

**Missing, with the proposed substitute (nothing invented in a final table):**

1. **"trades since open"** — no `trades_cum` column. Substitute: derived in `rules.py` as Σ `trades_5` over the strike-leg's rows with
   `ts_ist <= T`, carried in `tape_live_label.flags` as `trades_cum`; `tape_live_cycle` keeps exactly the `tape_strike_cycle` columns.
2. **the two walls' `oi_call` / `oi_put` at the run** — not in `tape_chain_runs`; present in the chain export input
   (`chain_events.py:6`). Substitute: `tape_live_wall.call_wall_oi_call` (oi_call at K_c) and `put_wall_oi_put` (oi_put at K_p), read by
   `wall_source.py` from the same run. Two values, not four (see open item O-3).
3. **`chain_run_ts`** — `tape_chain_runs.ts_ist` (`tape_schema.py:74` style); kept under the spec's name `chain_run_ts`.
4. **Spec PK of `tape_live_cycle` includes `strike`, `expiry`**, which are NULL on FUT rows. Substitute: mirror `tape_strike_cycle`
   exactly — PK (symbol, trading_day, instrument_token, ts_ist) + `UNIQUE NULLS NOT DISTINCT` on the spec's key. Same for events
   (UNIQUE NULLS NOT DISTINCT, as `tape_events`). FUT rows stay in, so the byte comparison is on whole files.
5. Provenance per the spec: `as_of` timestamptz, `live_run_id` uuid, `code_sha` text — not `tape_schema.PROVENANCE` (`run_id`,
   `source`, `loaded_at`…), because these rows are not loads. Data columns are generated from `tape_schema.db_columns()` /
   `db_types()` minus the provenance block, never retyped.

## 4. Decision 3: module layout (`services/tape_live/`, stdlib only, nothing imports it)

| File | Contents | Purity |
|---|---|---|
| `__init__.py` | empty | — |
| `rules.py` | `RULE_VERSION = "v1"`; `derive_flags(cycle_rows, events, wall_row, T, wall)` → dict of `wall_known, in_window, untraded, conc_evaluable, thin_evaluable, C, N, trades_cum, n_prior_bins, minutes_present_30, oi_build_15`; `label_wall(flags)` → `(label, partial, reason)`, first match wins, spec s4 verbatim | pure: no clock, randomness, I/O, imports only stdlib |
| `tapeLabels.vectors.json` | the 11 spec vectors + derivation vectors (real-precision rows) | data |
| `writer.py` | `LiveDay`: holds the two `SymbolReplay`s, `add_segment(sym, key, lines)`, `add_subscriptions(name, doc)`, `cycle(T, walls)` → `CycleOutput(upserts, deletes, wall_rows, label_rows)`; first-wins label store; diff against last emitted state | pure (bytes in, rows out); imports `merdian_compute.tape.{replay,minute,cycle,events}` and `services.tape_live.rules` |
| `wall_source.py` | **the only chain access**: `runs_from_snapshot_csv(paths, day)` (via `chain_events.build_runs`), `runs_from_chain_runs_csv(path)` (verify's final walls), `wall_for(runs, sym, T)` = latest run with floor5(ts) ≤ T | L0: CSV; L2: one SELECT on `gex_strike_snapshots`, front expiry |
| `verify_day.py` | recompute labels from final rows + final chain runs, compare with stored as-seen labels, cause per difference | pure core + thin `main` |
| `cli.py` | `replay` subcommand: lists/reads segments and subscriptions in time order, drives `LiveDay`, writes CSVs + `run_manifest.json`; `verify` subcommand | the only file I/O |

Chain access is only in `wall_source.py` (guard `live-no-outcomes`). `cli.py` reuses `process_day.read_token_map`-equivalent logic by
calling `replay.build_token_map` and `cycle_day.read_added` rather than retyping them.

### Derivation details the spec leaves to the code (each is a guard row)

- Window **(T−15, T]**: events with `T−15 < ts_ist <= T` → CONC at bins T−10, T−5, T; THIN stamped at minute closes T−14…T.
- `in_window`: a cycle row with (symbol, expiry = the wall row's front expiry, strike = K numerically, leg) at T.
- `C`: kind `CONC` at (K, leg) in the window (either side). `N`: kind `THIN`, `side = "ask"`, at (K, leg) in the window — on both legs (R-3).
- `conc_evaluable`: the strike-leg's rows with `ts_ist < T` number **≥ 12** (= `MIN_PRIOR`, the history CONC at T would use).
- `thin_evaluable` (**operator ruling on O-5, 2026-11-06**): Σ `minutes_present_5` over the strike-leg's cycle rows with
  `T−25 <= ts_ist <= T` (six bins = the 30 minutes `[T−30, T)`) is **≥ 20**. Cycle-table columns only, so the page and the writer
  compute it identically. `derive_flags(cycle_rows, events, wall_row, T, wall)` takes **only** cycle rows, events and the wall row (plus
  the grid point and which wall); no minute-level depth map. Guard `live-rule-inputs` asserts that signature and that `rules.py`
  names no minute-level depth field; mutant M-L-READS-DEPTH adds one.
- `untraded`: `trades_cum == 0` and `T >= 10:00`.
- `OI build` = Σ `oi_delta_5` over the three window rows (NULLs skipped; all NULL → NULL, never 0).

## 5. Decision 4: SQL file `sql/2026-11-06_tape_live_tables.sql` (written, **never applied**)

- Four `CREATE TABLE IF NOT EXISTS public.tape_live_{cycle,events,wall,label}`; `tape_live_cycle`/`_events` data columns generated
  from `tape_schema` (a generator function in `tests/` or `services/tape_live/` renders the DDL; guard `live-sql` asserts the file
  equals the render, so it is never hand-retyped).
- `ALTER TABLE … ENABLE ROW LEVEL SECURITY`; `REVOKE ALL … FROM anon, authenticated`; `GRANT SELECT … TO tape_ro, merdian_ro`;
  exactly two policies per table, `FOR SELECT TO tape_ro USING (true)` and `… TO merdian_ro …`, created idempotently (`DO` block
  checking `pg_policies`, since `CREATE POLICY` has no `IF NOT EXISTS`).
- `COMMENT ON TABLE` each: *"writer services/tape_live (W), owner tape, tier research — display only, never scored"* — live statements,
  not commentary (CLAUDE.md, S81).
- `tape_live_label.label` CHECK in {HIT, ABSORBED, THINNING, QUIET, NO_READ}; `wall` CHECK in {call, put}.
- No reference to the six `tape_*` table names (guard asserts by text scan with word boundaries).
- Rendered by `services/tape_live/ddl.py`, which finds the source column sets in `tape_schema.TABLES` by the identity of the imported
  `cycle.CYCLE_COLS` / `events.EVENT_COLS` tuples (so neither the six names nor any column is typed in `services/tape_live/`).
- **Postgres version.** `UNIQUE NULLS NOT DISTINCT` needs PostgreSQL ≥ 15. Evidence in the repo, not re-measured this session (no
  database access in L0): `docs/research/s104/sweep_engine/40_db_findings.md:3` reads *"PostgreSQL 17.6 on aarch64"* (as `merdian_ro`),
  and the applied `sql/2026-11-03_tape_t1db_sidecar.sql` already carries `UNIQUE NULLS NOT DISTINCT` (loads of 11-02..11-04 succeeded
  against it). The file opens with the same guard T1-db uses: `RAISE EXCEPTION` if `server_version_num < 150000`, so a wrong
  belief fails the apply instead of creating a table without the constraint. **Fallback** if the server is ever < 15: drop the
  `UNIQUE NULLS NOT DISTINCT` constraints and create `UNIQUE INDEX … (symbol, trading_day, COALESCE(expiry, DATE '1900-01-01'),
  COALESCE(strike, -1), leg, ts_ist)` (and the same shape for events); the PK on `instrument_token` is unaffected.
- The file also refuses to run if role `tape_ro` does not exist (a `GRANT` to a missing role would abort mid-file).

## 6. Decision 5: replay-mode contract

`python -m services.tape_live.cli replay --day 2026-11-06 --raw C:\tape_data\2026-11-06 --chain-runs C:\tape_data\chain_2026-11-06\gex_strike_snapshots_NIFTY.csv --chain-runs …SENSEX.csv --out <dir> [--arrival <json>]`

- `--chain-runs` takes the **gex_strike_snapshots export** (repeatable), not `chain_runs.csv`, because the wall OI is only there.
- Arrival model: segment `seg_HHMM*` becomes available at cycle T = HHMM + 5 (its recv window has closed). Subscriptions file
  `subscriptions_HHMMSS` at the first cycle T ≥ HHMMSS. `--arrival` (tests only) overrides availability per file, to plant a late segment.
- Cycle grid: one cycle per T from 09:20 to 15:30 (label written for that T only), then post-close cycles until the last segment
  (rows may still update, no labels), then a **final** cycle.
- Outputs in `<dir>`: `cycles/<HHMM>.csv` (per-cycle upserts and deletes, keyed), `tape_live_cycle.csv` and `tape_live_events.csv`
  (accumulated final state, rendered with `cycle.render_cycle_csv` / `events.render_events_csv` so they are comparable byte for byte
  with `cyc_<day>`), `tape_live_wall.csv`, `tape_live_label.csv`, `run_manifest.json` (inputs and outputs sha256, code sha, rebuilds
  with triggers, per-cycle elapsed only on stderr).
- Deterministic: replay `as_of` = the simulated cycle time (no writer clock in replay); `live_run_id` = uuid5 of (day, code_sha,
  sha of the input manifest). Two runs byte-identical (guard `live-deterministic`).
- Real-day runtime estimate: ~200 s T1a + ~80 cycles × ~8 s ≈ 12 min per day on this machine; the three-day gate runs once,
  outside `run_offline.sh`, as `tests/tape_live_equal_offline.py --data C:\tape_data` (Tee-Object log), because `run_offline.sh`
  steps must be fixture-only.

## 7. Tests (build phase, tester-first)

`tests/test_tape_live.py` (11 guards from the prompt's table, R-1 override as in `test_tape_t1b.py`) with generators in
`tests/tape_live/` that compute planted truth independently (reference CONC/THIN from `gen_cycle.py`'s `ref_conc`/`ref_thin` shape,
labels from a hand table, never from `rules.py`); `tests/tape_live_mutants.py` (every mutant ×5, each run beside an unpatched control).
`run_offline.sh`: **40 → 42 steps** (guards, mutants), appended after step 40. On Windows the Python tests are run directly.

The plan's earlier "19" was a miscount: the prompt's table names **20**. All 20, plus the two the spec s4 and the O-5 ruling add (22):

| # | Mutant | Guard | What it does |
|---|---|---|---|
| 1 | M-L-HIT-ABSORBED-SWAPPED | live-vectors | C∧N → ABSORBED, C∧¬N → HIT |
| 2 | M-L-NOREAD-AS-QUIET | live-vectors | "flow not yet evaluable" returns QUIET |
| 3 | M-L-C-WHEN-NOT-EVALUABLE | live-vectors | C read in the thin-only branch |
| 4 | M-L-ORDER-CHANGED | live-vectors | untraded tested before in_window |
| 5 | M-L-UNTRADED-REMOVED (spec s4) | live-vectors | rule 3 deleted |
| 6 | M-L-LOOKBACK-10 | live-derive | window (T−10, T] |
| 7 | M-L-LOOKBACK-20 | live-derive | window (T−20, T] |
| 8 | M-L-BID-COUNTED | live-derive | N counts THIN on either side |
| 9 | M-L-EVAL-11 | live-derive | conc_evaluable at 11 prior bins |
| 10 | M-L-UNTRADED-ALWAYS | live-derive | untraded ignores the 10:00 condition |
| 11 | M-L-READS-DEPTH (O-5 ruling) | live-rule-inputs | `derive_flags` grows a depth parameter and reads it |
| 12 | M-L-WALL-NEXT-RUN | live-wall-floor | picks a run whose floor is after T |
| 13 | M-L-LABEL-OVERWRITE | live-first-wins | a later label replaces the stored one |
| 14 | M-L-DROPS-LATE-SEGMENT | live-equal-offline | a late segment is ignored instead of triggering a rebuild |
| 15 | M-L-CUM-RESET-AT-SEGMENT | live-equal-offline | the carried replay is re-created at each segment |
| 16 | M-L-USES-FUTURE-BIN | live-causal | the window's upper bound is T+5 |
| 17 | M-L-VERIFY-IGNORES-DIFF | live-verify | verify never records a difference |
| 18 | M-L-NONDETERMINISTIC | live-deterministic | `live_run_id` from `uuid4()` |
| 19 | M-L-JOINS-OUTCOMES | live-no-outcomes | an outcome / spot identifier appears in `verify_day.py` |
| 20 | M-L-WRITES-SIX-TABLES | live-isolated | a six-table name appears in the writer |
| 21 | M-L-IMPORTS-SUPABASE | live-isolated | a non-stdlib import appears |
| 22 | M-L-SQL-ANON-GRANT | live-sql | a `GRANT … TO anon` line in the SQL file |

Guards: the prompt's 11 plus `live-rule-inputs` = **12**.

## 8. Open items the spec does not settle (proposed default in bold; applied unless ruled otherwise)

- **O-1. "label rows equal the labels recomputed from the final rows" on real days.** A label at T is computed from what had arrived by
  T; 0.067 % of packets (≈20 per NIFTY segment) arrive in the next segment with an exchange minute before it, and these can change bin T's
  volume or minute T−1's depth snapshot. So as-seen = final cannot be guaranteed byte-for-byte on real data. **Default:** the byte gate
  is on the final `tape_live_cycle`/`tape_live_events` state (spec s8); for labels the real-day run reports agreement % and lists every
  difference with its cause, and **fails only on a cause other than `partial_cycle`**. The 100 %-agreement guard runs on fixtures with no
  packet crossing a boundary.
- **O-2. Missed cycles.** **Default:** a label is written only for the cycle's own T; a grid point the writer missed (e.g. during a
  rebuild) stays absent, never back-filled, and verify counts it as `missing`.
- **O-3. Wall OI.** **Default:** two columns, `call_wall_oi_call` and `put_wall_oi_put`.
- **O-4. Tape expiry vs chain front expiry.** If they differ (expiry morning), `in_window` is false → NO_READ "wall outside subscribed
  window". **Default:** accept; report the count.
- **O-5. `thin_evaluable` window. RULED (operator, 2026-11-06):** Σ `minutes_present_5` over rows `T−25..T` ≥ 20, cycle columns only
  (section 4). The proposed minute-depth reading is withdrawn.
- **O-6. Verify cause order** (first that applies): `rule_drift` (stored flags re-labelled ≠ stored label), `chain_run_differs` (live
  run id or walls ≠ final run for that grid point), `late_segment` (a segment with HHMM < T arrived after cycle T: from the manifest),
  `partial_cycle` (flags differ, none of the above), `other`.
- **O-7. Pre-10:00 walls.** Walls are labelled from 09:20 using runs before 10:00 (the 10:00 window in `chain_events` governs E-events,
  not walls). **Default** as stated.
- **O-8. The spec's "PK" for the two copied tables** is implemented as UNIQUE NULLS NOT DISTINCT + the `tape_schema` PK (section 3 #4).
- **O-9. `services/tape_live/__init__.py` is not committed.** `.gitignore:107` (`_*.py`) ignores it (`git check-ignore -v`); the repo
  rule is a negation, never `git add -f`, and `.gitignore` is outside L0's write scope. `services.tape_live` therefore loads as a
  namespace package inside the regular `services` package; the guards pass 12/12 on a tree copy without the file. **Proposed:** add
  `!__init__.py` after `.gitignore:107` in a session whose scope includes `.gitignore`, then commit the empty file.

## 9. Not in L0

No page, S3 poller, Supabase client, production install, or market-hours run (L1-L3). No change to `merdian_compute/tape/`,
`services/tape_offline/`, `services/tape_runner/`, `services/tape_scoring/`. No push to `origin`.

## 10. Build results (2026-11-06; built on Opus, the `/model` switch to Sonnet did not happen)

- Guards `tests/test_tape_live.py`: **12/12 PASS** (57 s on this machine). Mutants `tests/tape_live_mutants.py --repeat 5`:
  **22/22 caught x5 (110/110), 12/12 controls x5 (60/60)**; log `_l0_logs/` (git-excluded).
- `tests/run_offline.sh`: **40 -> 42 steps** (41 guards, 42 mutants x5). Not run as a whole suite on Windows (Rule 23's `ulimit -v`
  half cannot be enforced here); owed on Linux after 15:45 IST.
- Real-day gate `tests/tape_live_equal_offline.py`:
  - **2026-11-04 PASS**: `tape_live_cycle.csv` == `cyc_2026-11-04/tape_strike_cycle.csv` (10,950 rows) and `tape_live_events.csv` ==
    `tape_events.csv` (599 rows) byte for byte, as written and as rebuilt from the per-cycle deltas; labels 150/150 NIFTY and
    150/150 SENSEX match the labels recomputed from the final rows (0 differences, 0 missing); no rebuild, no late segment;
    77 cycles, median 12.3 s, max 17.4 s per cycle (measured while the mutant run shared the machine).
  - A first three-day run was stopped by the host for low system memory during 11-05 (it shared the machine with the mutant run).
    Per the operator (2026-11-06), 11-05 and 11-06 were re-run one day per process with nothing else running, peak working set logged:
  - **2026-11-05 PASS**: 13,800 cycle rows and 1,278 event rows byte-equal (written and from deltas); labels 150/150 + 150/150 match,
    0 differences, 0 missing; rebuilds: subscriptions at 09:05 (both symbols); 77 cycles, median 19.0 s, max 39.8 s; replay 1,738 s;
    **peak working set 425.2 MB**.
  - **2026-11-06 PASS**: 14,262 cycle rows and 1,263 event rows byte-equal (written and from deltas); labels 150/150 + 150/150 match,
    0 differences, 0 missing; rebuilds: subscriptions at 14:35 (the 14:33 file, both symbols); 77 cycles, median 14.2 s, **max 239.3 s
    (the 14:35 rebuild cycle)**; replay 1,316 s; **peak working set 450.8 MB**.
  - 11-04's peak was not recorded (the per-stage peak logging was added for the re-run).
  - O-1 in practice: no `partial_cycle` difference on any of the three days, although 0.067 % of packets cross a segment boundary.
- Not settled by L0 (for L2): a 239 s rebuild cycle on this machine means the 14:33-type map change costs most of a cycle; on the
  t3.small it may exceed one. Options for L2 (not built): extend the token map in place (needs a `replay.py` change and its own
  equality guard) or label from the pre-rebuild state for that one cycle. Per-cycle cost and ~450 MB peak are measured here, not on
  the production box.
