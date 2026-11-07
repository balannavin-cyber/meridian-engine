# Tape live L0: snapshot `ts` width fix at the writer boundary (plan)

Sat 2026-11-07. Branch `tape/live-l0`, base `0a1c681`. Plan only: written on Opus, nothing built yet. The build follows
section 4, tests first.

## 0. The defect

On the box (Python 3.10.12), `cli replay --day 2026-11-06` exited 2 on its first real chain export:
`ValueError: Invalid isoformat string: '2026-11-06T03:10:06.43966+00:00'`. Postgres drops trailing zeros from the
`timestamptz` fraction, so a value can carry 1 to 6 digits. Python 3.10 `fromisoformat` accepts only 0, 3 or 6; Python
3.11 and later accept every width. The call path is `cli.cmd_replay` -> `wall_source.runs_from_snapshot_csv` ->
`chain_events.build_runs` -> `chain_events.parse_ts:32`.

**Counted again on this machine, from the same export files** (`C:\tape_data\chain_*`, read-only):

| day | NIFTY widths | SENSEX widths |
|---|---|---|
| 11-02 | 5: 728, 6: 8,326 | 5: 1,172, 6: 13,384 |
| 11-03 | 4: 114, 5: 1,129, 6: 8,632 | 4: 168, 5: 1,199, 6: 13,465 |
| 11-04 | 4: 123, 5: 615, 6: 9,873 | 5: 905, 6: 14,864 |
| 11-05 | 5: 1,203, 6: 10,411 | 4: 197, 5: 965, 6: 15,431 |
| 11-06 | 5: **675**, 6: 11,114 (of **11,789**) | 4: 181, 5: 753 (= **934**), 6: 15,327 (of **16,261**) |

These 11-06 counts match the box's 675 / 11,789 and 934 / 16,261 exactly. Across all ten files (130,954 values), every
`ts` has the form `YYYY-MM-DDTHH:MM:SS[.f]+00:00`: separator `T`, offset `+00:00`. No `Z`, no `+00`, no space separator.
No width 1, 2 or 3 was observed. Those widths are still possible (a fraction of 0.1 s is stored as `.1`), so the fix
handles them.

## 1A. Inventory: every place a timestamp string becomes a number or a datetime

Scope: `services/tape_live/*.py` and everything they import from `merdian_compute/tape/`: `chain_events`, `cycle`,
`events`, `minute`, `replay`, `special` and `classify` (through `replay`). `services/tape_offline/cycle_day` (`peak_mb`)
is included too. Method: `grep -n "fromisoformat|strptime|strftime|datetime.|fromtimestamp|timedelta"`, then reading
the string-slicing parsers (`[11:13]` and similar), which a grep for `datetime` cannot find.

| # | site | string comes from | 3.10-safe for widths 1-6? | evidence |
|---|---|---|---|---|
| 1 | `merdian_compute/tape/chain_events.py:32` `parse_ts`: `datetime.fromisoformat(s.strip())` | `ts` column of the `gex_strike_snapshots` export CSV (written by the database, so Postgres trims the fraction) | **NO.** This is the defect. | Box traceback above; widths 4 and 5 counted in the table above. |
| 2 | `merdian_compute/tape/replay.py:88` `_epoch` <- `parse_line:146`, `exchange_timestamp` | raw tape segments, written by `services/tape_runner/serialize.py:15-18` `to_ist_iso` -> `datetime.isoformat()` | **Yes, because of the writer.** `datetime.isoformat()` with no `timespec` emits no fraction when `microsecond == 0` and exactly 6 digits otherwise. It never trims. | Measured over every segment of 11-06 (162 files): **5,032,225** `exchange_timestamp` values, **all width 0**. Kite stamps whole seconds. |
| 3 | `replay.py:233` `end_group`: `_epoch("%sT%s:%s:00+05:30" % ...)` | a string the code builds itself, with no fraction | Yes | Format literal at `:233` |
| 4 | `replay.py:116` `_recv_bucket`: `recv_ist[11:16]` | raw segments (`serialize.ist_iso`) | Yes: sliced, never parsed | Measured on `seg_1000` NIFTY: all 6 digits. Width does not matter to a slice of positions 11-16. |
| 5 | `replay.py:153` `mn = exts[11:16]` | raw segments | Yes: slice | `:153` |
| 6 | `chain_events.py:100` `dt.strftime(...)` -> `ts_ist` | output of site 1 | Yes: formatting, not parsing | Fixed format `%Y-%m-%dT%H:%M:%S+05:30` |
| 7 | `wall_source.py:59-61` `_floor5`, `:66` `wall_row`: `ts[11:13]`, `ts[14:16]`, `hhmm[:2]` | `ts_ist` from site 6, or from `chain_runs.csv` | Yes: slice of a fixed-width string the code wrote itself | `:60` |
| 8 | `wall_source.py:46` `runs_from_chain_runs_csv` (used by `verify_day`) | `chain_runs.csv`, written by `chain_events.render_runs_csv` (site 6 format) | Yes: not parsed at all | `:50-52` copies strings |
| 9 | `rules.py:37-39` `_min`: `ts[11:13]`, `ts[14:16]` | cycle `T` / event `ts_ist`, built by `cycle.ts_of` / `events._ts` | Yes: slice | `rules.py:39` |
| 10 | `cli.py:85` `as_of`: `datetime.strptime(day, "%Y-%m-%d")` | the `--day` argument, regex-checked at `cli.py:269` | Yes: no time part | `:269`, `:85` |
| 11 | `cli.py:111, 120` minute arithmetic on segment and subscription names | file names matched by `SEG_RE` / `SUB_RE` | Yes: fixed-width digits | `replay.py:28-29` |
| 12 | `writer.py:49` `added_minute` ("HH:MM") -> `cycle.build_cycle` | subscriptions json, written by the recorder | Yes: compared as `HH:MM` text, never parsed as a datetime | `writer.py:48-49` |

**Conclusion.** Site 1 is the only place where a database-written fraction reaches `fromisoformat`. The raw side is
safe because of how its strings are produced. `isoformat()` never emits widths 1-5, and all 5,032,225 measured values
are width 0. Nothing in the parser makes it safe.

**One risk I am not fixing here, stated so it is a decision:** if a future raw writer ever trimmed the fraction, site 2
on 3.10 would **not crash**. `parse_line:145-148` catches the `ValueError` and counts the packet under `no_exchange_ts`,
so packets would be dropped silently and counted under the wrong reason. Fixing that means editing `replay.py`, which is
outside my scope (§3).

## 1B. Fix design

One normaliser in `services/tape_live/wall_source.py`, applied to every snapshot row before `chain_events.build_runs`
sees it. Every call to `build_runs` from `services/tape_live/` goes through one wrapper, so a later live-path reader
(an L2 SELECT) inherits the normaliser instead of having to remember it:

```python
import re
SNAP_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:\d{2})$")

def norm_snapshot_ts(s):
    """One gex_strike_snapshots ts -> the same instant with a fraction of 0 or 6 digits (Python 3.10 fromisoformat
    accepts only 0, 3 or 6; Postgres trims trailing zeros, so 1-6 arrive). Pads right with zeros; never truncates or rounds.
    Raises ValueError on a fraction wider than 6 and on any other shape (Z, +00, a space separator, whitespace)."""
    m = SNAP_TS_RE.match(s)
    if m is None:
        raise ValueError("snapshot ts %r: not YYYY-MM-DDTHH:MM:SS[.f]+HH:MM" % (s,))
    frac = m.group(2)
    if frac is None:
        return s
    if len(frac) > 6:
        raise ValueError("snapshot ts %r: fraction wider than 6 digits (never rounded)" % (s,))
    return "%s.%s%s" % (m.group(1), frac.ljust(6, "0"), m.group(3))

def build_runs(rows, day):
    """The ONLY call of chain_events.build_runs in services/tape_live/."""
    for r in rows:
        r["ts"] = norm_snapshot_ts(r["ts"])
    return chain_events.build_runs(rows, day)
```

`runs_from_snapshot_csv` calls `build_runs(rows, day)` instead of `chain_events.build_runs(rows, day)`. Nothing else
changes. The output is width 0 or 6, never 3, which falls inside the {0, 3, 6} the guard accepts.

**Strict full-match grammar, not a fraction-only substitution.** The goal is that every string `build_runs` receives
matches a grammar that 3.10's `fromisoformat` accepts. That claim is about strings, so it holds on any interpreter.
Padding the fraction alone would let `Z` or psql's `+00` through, and both also fail on 3.10. The strict grammar fits
130,954 of 130,954 measured values, so it rejects nothing we have seen. Rejecting a form we have not seen (with a
`ValueError`, which `cli` turns into exit 2) is better than accepting a form that would crash on the box. This is
narrower than 3.12's current behaviour (3.12 accepts `Z`). See §3.

**Why not `core.ts_parse.norm_frac`:**
1. A fraction wider than 6 passes through unchanged and is not rejected (`core/ts_parse.py:63-67`). The prompt requires a raise.
2. `norm_frac` leaves the offset to the caller, and `parse_pg_ts` converts to UTC and returns `None` on failure. The
   module documents that silence as its contract (`:150-155`). A silent `None` is the wrong failure mode for a writer.
3. `live-isolated` (`tests/test_tape_live.py`) allows `services/tape_live` to import only `merdian_compute.tape`,
   `services.tape_live`, `services.tape_offline` and `services.tape_db`. Importing `core` would widen the isolation
   boundary the L0 plan pinned, and would tie the tape writer to the engine's `core/` package.

The pad rule is the same as `norm_frac`'s (right-pad with `0` to 6). I make no parity claim, so no parity test is owed
(Rule 0, fourth clause).

**Why not monkeypatch `chain_events.parse_ts`:** that would edit a shared T1b module at runtime, in every process that
imports `services.tape_live`. The test process imports both `chain_events` and the scoring chain, so the scorer's
behaviour would depend on import order. The scope line forbids editing `chain_events`, and a runtime patch is an edit
that does not appear in the diff.

## 1C. Guard and mutants

New guard **`live-ts-width`** in `tests/test_tape_live.py`. Guards go from 12 to 13; `run_offline.sh` stays at
**42 steps**, because the guard runs inside step 41.

Fixture: a CSV generated in-test under `_TMP`. It is not added to `gen_live`, so the existing fixture bytes, the guards
that use them and the determinism hashes do not move. One symbol (NIFTY), front expiry plus one back-expiry row per run
(to show a back row is still ignored), 3 strikes per run. The guard installs a spy around `chain_events.build_runs` for
the duration of the call and restores it in a `finally`. Runs and their `ts` strings:

| run | `ts` as planted | width | note |
|---|---|---|---|
| r0 | `2026-11-06T03:10:06.43966+00:00` | 5 | the box's failing string |
| r1 | `2026-11-06T04:30:21+00:00` | 0 | must pass through **byte-identical** |
| r2 | `2026-11-06T04:35:21.5+00:00` | 1 | |
| r3 | `2026-11-06T04:40:21.25+00:00` | 2 | |
| r4 | `2026-11-06T04:45:21.125+00:00` | 3 | |
| r5 | `2026-11-06T04:50:21.4396+00:00` | 4 | the stored `.439600`, trailing zeros dropped |
| r6 | `2026-11-06T04:55:21.43966+00:00` | 5 | |
| r7 | `2026-11-06T05:00:21.439660+00:00` | 6 | already canonical |

The generator records, for every run, the integer instant in microseconds, computed from the integers it chose
(`h, m, s`, the digits as an int, offset 0). It does not parse the strings.

Cells (each states what makes it FAIL):
1. **Rows reach the spy.** The spy saw exactly 8 × 4 = 32 rows (an exact count, never a floor). *Fails* if
   `runs_from_snapshot_csv` stops calling `chain_events.build_runs` through the module attribute (for example a
   `from … import build_runs`), because the spy would then see 0 rows and every other cell would pass vacuously.
2. **Width.** For every spied row, `ts` matches `\.(\d+)` with width in {0, 3, 6}, or has no fraction. This is a
   **string property**, independent of the interpreter. *Fails* on today's code on 3.12 (shown below), and fails under
   M-L-TS-NOT-NORMALISED.
3. **Same instant.** For every spied row, a test-local integer parser (regex plus `int()`, no `datetime`) gives the
   generator's microsecond value. *Fails* under M-L-TS-TRUNCATES: `.43966` -> `.439` moves the instant by 660 µs, and
   the width check cannot see that, because 3 is an allowed width.
4. **No fraction passes through.** r1's spied `ts` is byte-identical to the planted string.
5. **Runs, walls and wall OI.** `wall_source.wall_row` at grid points 08:40, 10:00, 10:05 … 10:30 gives `chain_run_ts`,
   `call_wall`, `put_wall`, `call_wall_oi_call` and `put_wall_oi_put` equal to a table **written by hand in the test**.
   OI values differ per run, so a run merged, dropped or misordered changes a cell.
6. **Too wide raises.** A CSV whose one row has `.4396601` makes `runs_from_snapshot_csv` raise `ValueError` with
   `"wider than 6"` in the message. It must not round and must not pass through.
7. **One entry point.** An AST check over `services/tape_live/*.py`: exactly one reference to `chain_events.build_runs`,
   inside `wall_source.build_runs`. *Fails* if a later reader calls `chain_events.build_runs` directly, bypassing the
   normaliser.

Mutants (in `tests/tape_live_mutants.py`, guard `live-ts-width`, target `services/tape_live/wall_source.py`):

| mutant | exact patch (must match once) | caught by |
|---|---|---|
| M-L-TS-NOT-NORMALISED | `    return "%s.%s%s" % (m.group(1), frac.ljust(6, "0"), m.group(3))\n` -> `    return s\n` | cell 2 |
| M-L-TS-TRUNCATES | `frac.ljust(6, "0")` -> `frac[:3].ljust(3, "0")` | cell 3 (width 3 is allowed, the instant is not) |

**The mutant count.** The prompt says the mutant count goes "from 22 to 23", but its table names two mutants.
**Default: build both, so 22 -> 24.** Each mutant is caught by a different cell, so dropping either one leaves a cell
that no mutant tests. The harness docstring and `run_offline.sh` comment/label text change to "24 x5" and the guard
text to "(13)". The step count stays at 42.

**Shown failing on 3.12 before relying on it.** Today's code is equivalent to M-L-TS-NOT-NORMALISED, because there is no
normaliser. A scratch script (`C:\Users\balan\AppData\Local\Temp\claude\430d01f022e91de2\a247325b-1038-450d-84cd-99e34c4db4f3\scratchpad\ts_demo.py`)
installed the same spy, ran the current `runs_from_snapshot_csv` on one row with the box's string, and applied the
cell-2 and cell-3 predicates:

```
3.12.10 widths handed to build_runs: {5} -> width assertion FAIL
pad6 same instant: True | trunc3 same instant: False
```

So cell 2 fails on this interpreter against the unfixed code, and the integer instant check tells pad-to-6 apart from
truncate-to-3. **I have not run Python 3.10.** It is installed only on the box, and the scope line forbids the box. The
first 3.10 run is the operator's re-run of the 11-06 replay there (§3).

## 2. Build order (Sonnet), tests first

1. Add `live-ts-width` (cells 1-7) to `GUARDS` and the two mutants to `M`, then run against the unfixed tree:
   `--only live-ts-width` must FAIL on cell 2. Record that output.
2. Add `norm_snapshot_ts` and `build_runs` to `wall_source.py`, and switch `runs_from_snapshot_csv` to the wrapper.
   Update the module docstring.
3. `python tests/test_tape_live.py` 13/13 PASS. Then `python tests/tape_live_mutants.py --repeat 5`: 24/24 caught x5
   and 13/13 controls x5. Run with `TAPE_RULE23_OVERRIDE_R1=1` only if inside the weekday window; Saturday is outside
   it, so the override is not needed today.
4. Every other Python step of `run_offline.sh` on Windows, in order, with exit codes. Steps that need bash, Linux or a
   golden day are reported as not run, with the reason. No `ulimit` on Windows (Rule 23's `ulimit -v` half cannot be
   enforced here, as in S105).
5. Update the counts in the `run_offline.sh` comments and labels, the harness and test docstrings, and the evidence
   section of `docs/tape/L0_plan.md`.
6. Commit by explicit path. Push `tape/live-l0` to `tape-staging` only.

Files touched: `services/tape_live/wall_source.py`, `tests/test_tape_live.py`, `tests/tape_live_mutants.py`,
`tests/run_offline.sh` (comment and label text only), `docs/tape/L0_plan.md`, `docs/tape/L0_ts_width_plan.md`,
`docs/tape/L2_rebuild_options.md`. Nothing under `merdian_compute/`, `services/tape_offline/`, `services/tape_scoring/`
or `services/tape_runner/`.

## 3. Not settled by the prompt (proposed defaults)

1. **Mutant total 23 vs 24.** Default **24** (§1C).
2. **The T1b chain step has the same defect on the box.** `services/tape_chain` -> `chain_events.process` ->
   `parse_ts` reads the same exports. If the engine stream ever runs it on 3.10, it will exit the same way. This plan
   does not fix it (scope). Default: report it to the engine stream as a TD candidate; the fix belongs in `chain_events`.
3. **Silent raw-side drop (§1A, site 2).** Safe today because of how the recorder writes timestamps. A future writer
   that trimmed the fraction would turn the failure into wrongly reasoned `no_exchange_ts` drops on 3.10. Default:
   engine-stream TD candidate, no change here.
4. **Strict grammar rejects `Z`, `+00` and a space separator.** None of them appears in 130,954 measured values.
   Default: reject loudly (exit 2). An L2 reader whose client renders a different form must be widened by a decision,
   not by drift.
5. **Python 3.10 verification.** Not possible from here. Default: after the push, the operator re-runs the 11-06
   recorded-day replay on the box. The first result to read is whether the run gets past `build_runs`.
