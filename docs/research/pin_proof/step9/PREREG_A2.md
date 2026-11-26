# Step 9: amendment A2 (operator ruling, Thu 2026-11-26)

Parent: `PREREG.md` (sha256 `eef1981480b8cfb7b92e7396c50cb9ceae9e70f655557a0a33c8f7efbb4a73f0`)
as amended by `PREREG_A1.md`
(sha256 `792b1fb342172caee297e275da66906dadd74163af9758c31e6947a0413557cb`).
A2 changes no figure, no stop's test, no set, no window and no stratum. It records
an infrastructure fault and the one conversion fixed because of it.

**no figure of any kind was read or shown before this amendment**

## 1. The crash

Attempt **A2-1** started 2026-11-26 18:15 IST and died 35 s in, on the 26th run of
the first symbol-day (2026-08-27 NIFTY), having written 25 records. It raised an
unhandled exception, so it printed neither `PULL FINISHED` nor `PULL STOPPED`:

```
Traceback (most recent call last):
  File ".../step9_pull.py", line 686, in <module>
    sys.exit(main(sys.argv[1:]))
  File ".../step9_pull.py", line 641, in main
    pull_symbol_day(p["symbol"], p["day"], p["n_runs"], out, state)
  File ".../step9_pull.py", line 572, in pull_symbol_day
    a = build_agg(q1[rid], q2[rid], q3[rid], q4.get(rid, {}))
  File ".../step9_pull.py", line 511, in build_agg
    a["ts"] = parse_ist(q1["v1_ts_ist"])
  File ".../step9_pull.py", line 495, in parse_ist
    return dt.datetime.fromisoformat(s)
ValueError: Invalid isoformat string: '2026-08-27T14:40:06.50508'
```

Cause: this box runs **Python 3.10.12**, whose `datetime.fromisoformat` accepts a
fractional second of exactly 0, 3 or 6 digits. Postgres strips **trailing** zeros
from the fraction, so `min(ts AT TIME ZONE 'Asia/Kolkata')` renders through
`row_to_json` with 0 to 6 digits. The first 25 runs all carried 6-digit fractions;
the 26th carried five. Python 3.11 would have accepted it.

The self-test could not have caught it: it constructs `datetime` objects directly
and never parsed a Postgres-rendered string. That seam was the one untested step in
the pipeline, and it is where the pull broke.

## 2. The ruling (operator, verbatim in substance)

1. The crash is an **infrastructure fault, not a look at results**. A change that
   only converts a database text value to a datetime or a number, and cannot change
   any figure's arithmetic, a stop's test, a set, a window or a stratum, may be made
   after a crash that happened before `RESULT.md` existed. Any other change after
   data has been read stays forbidden; task condition 7 stands.
2. Archive, do not delete, the aborted attempt. It is never used for any figure.
3. Fix `parse_ist` by padding the fraction to exactly 6 digits on the **right**, and
   accept no fraction. Then audit every other place a database text value is parsed,
   converted or compared, and fix only conversions.
4. Add a seam test over 0 to 6 fraction digits through the same parse path, and an
   additional mutant: a parser that pads on the left, or does not pad, must be caught.
5. Write this file; rewrite `CODE_SHA256SUMS`; rerun the EXPLAIN gate once.
6. Continue from P4 and start the pull once. A second crash before `RESULT.md`
   exists stops the task for a further ruling. **At most two amendments of this kind
   in total; this is the first.**

## 3. The archived attempt (A2.2)

Moved to `step9/aborted_attempt_A2_1/`, never read for any figure:

| file | sha256 |
|---|---|
| `per_run.jsonl` (25 records, 2026-08-27 NIFTY only) | `404601b96bbf278cd9ef32ed1db7dd82fc6f3ec6afae390c262f4ad50ff6630c` |
| `run.log` (2 lines: start, plan) | `27d783d7b7f64c035e2bd24257365dee9c18d8e3ae7a04586ca3d3060df637a3` |
| `pull.out` (the traceback above) | `2236eee7157b9d34c047feccad6c381eed9569f9b27145f80044131a1fad072b` |

Nothing else of the attempt holds a figure. `population.json`, `c4_result.json` and
`RESULT.md` were never written — the crash preceded all three, so C4 never ran. The
attempt's only other writes were `sql/pull_Q{1,2,3,4}_*_NIFTY_2026-08-27.sql` and
`sql/pull_plan_*.sql` (rendered query **text**, no data) and `plan.json` (the run
count per symbol-day, produced by `--plan` before the pull and printed in P4). Those
stay in place: they are inputs, reproduced identically by the next run.

Of the 25 archived records, C3 held 25 of 25 and C6 held 25 of 25. Those counts are
recorded here as evidence that the two stops were exercised, and are **not** carried
into the result.

## 4. The conversion fixed (A2.3)

`step9_pull.parse_ist` normalises the fraction to exactly six digits by padding on
the **right** (`'.50508'` -> 505080 us), truncates beyond six, preserves any trailing
text, and passes a value with no fraction through unchanged. A left pad would read
`'.50508'` as 50508 us, 0.45 s early.

## 5. Parse, convert and compare sites audited (A2.3)

Sites that consume a value rendered by the database:

| site | can it fail on a Postgres-rendered value? |
|---|---|
| `step9_pull.py:516` `parse_ist` | **This was the fault.** Fixed: right-pad to 6 digits, no fraction accepted. |
| `step9_pull.py:391` `json.loads(s)` on the `row_to_json` line | No. Every selected column is a number, date, timestamp, uuid or short text; none can contain a newline, so one row is always one line. |
| `step9_pull.py:479` `DAY_FROM.isoformat() <= r["day"] <= DAY_TO.isoformat()` | No. `(ts AT TIME ZONE 'Asia/Kolkata')::date::text` is always `YYYY-MM-DD`, where lexicographic order is date order. |
| `step9_pull.py:481` `int(r["n_runs"])` | No. `count(*)` renders as a JSON integer. |
| `step9_pull.py:103` `dt.date.fromisoformat(day)` | No. `day` comes from the plan as `YYYY-MM-DD`, with no fraction. |
| `step9_pull.py:417` `int(line.split("rows=")...)` | Not data: it parses EXPLAIN plan text in the gate, and a malformed node is already skipped by its `except`. |
| `step9_pull.py:614`, `:654` `json.loads` of the fixture and `plan.json` | No. Local files this code wrote or that ship with the repo. |
| `step9_lib.py:560` `_eq_ts`, used by C6 | **Rendering-dependent, and left alone.** It compares the `timestamptz` text of `v1_ts`, `v2_ts` and `r_ts` from three separate statements. Equal instants render equal text because all four statements run through the same `bin/roq.sh` with the same `PGOPTIONS`, so the same session `TimeZone`, and the trailing-zero stripping is a function of the value alone. Changing it would change a stop's test, which A2.1 forbids. |
| `step9_lib.py:571` expiry comparison | No. Both sides are `::text` cast in SQL, so `YYYY-MM-DD` on both. |
| `step9_lib.py:577` `int(a["v1_dte"]) == int(a["r_dte"])` | No. Both are `integer` columns. |
| `step9_lib.py:145` `_f` and every `float(...)` in the figures | No. `json.loads` has already typed these as int or float. A `numeric` beyond ~15 significant digits would lose precision in a double, but the quantities here are exposures near 1e6, open-interest sums near 1e8 and shares below 1 — all exact or near-exact in a double. |
| `step9_lib.py:802`, `:830` `float(...)` in `b2_close` and `c4_compare` | No. Both sides are JSON numbers; a field that is absent or None is already a recorded failure, not a skip. |
| `step9_lib.py:612` `str(status).upper()` | No. `p3b2_invariant_checks.status` is text, and None is handled before the call. |
| `step9_lib.py:634` `a["ts"].isoformat()` | No. It writes a `datetime` out, so 0 or 6 fraction digits, which is what the summary reads back. |

One fault, one fix. Nothing else was changed.

## 6. Hashes before and after A2

| file | before A2 | after A2 |
|---|---|---|
| `step9_lib.py` | `646c26087c6d027af7782c361a6ea5c1191f8a0517c24aa9cd4bcd9d848c6642` | `646c26087c6d027af7782c361a6ea5c1191f8a0517c24aa9cd4bcd9d848c6642` (unchanged) |
| `step9_pull.py` | `d45cee23c058305290f80b16646ddaeb2d381b0a71e297150701e16d127c71e6` | `811758bdceb0de4a176345bdeae2774938646c563cb128533aae8ed913f71618` |
| `selftest_step9.py` | `92002bdcf6949fe7b7abca3e5955f9b34e8d71345535fd42d57683abe1d000cd` | `e9f0340a9192b4951c95b59c8bb1e12b8f342809de4b046bacf2ff7c5aa4f3a3` |
| `step9_summary.py` | `44f0576f388d7e213a39877e11f0f770e7589d087bd27518be746e8802bd45db` | `44f0576f388d7e213a39877e11f0f770e7589d087bd27518be746e8802bd45db` (unchanged) |

`step9_lib.py` and `step9_summary.py` are byte-identical before and after: the fault
and the fix are confined to the pull's parser and the self-test that now covers it.

## 7. The seam test and the mutants (A2.4)

`selftest_step9.check_parse_seam` feeds eight Postgres-rendered forms through
`step9_pull.parse_ist` — 0, 1, 2, 3, 4, 5 and 6 fraction digits plus the
space-separated form — including `'2026-08-27T14:40:06.50508'`, which must give
14:40:06.505080, and then checks that the §3 set and window derived from the parsed
value are the expected ones. Any exception is turned into a failure, so a parser
that refuses to parse fails the test exactly as one that parses wrongly.

Three additional mutants, reported beside the nine of design C5 and not counted in
them: **M10** removes a field from the database row, **M11** pads the fraction on
the left, **M12** does not pad at all. The ruling asks that a left-padding *or*
non-padding parser be caught; both are included because one mutant could only show
one of them.
