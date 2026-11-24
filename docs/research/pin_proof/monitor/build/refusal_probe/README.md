# refusal_probe — what this folder is, and what it is not

A probe, built 2026-11-24, to show that `run_day.sh`'s refusals actually fire.
Nothing here measures anything, and nothing here is part of the daily run.

| file | what it is |
|---|---|
| `run_day.sh` | a copy of `../../run_day.sh` differing in **exactly two lines**: `FIRST_DAY="2026-11-01"` and `NOT_BEFORE="00:00:00"`. Relaxing those two is what makes refusal R-d reachable on 2026-11-24; otherwise R-a or R-c refuses first and R-d is never evaluated. |
| `selftest_pin_monitor.py` | a stub. Left in its **failing** state (`sys.exit(3)`). |
| `pin_monitor_day.py` | a stub reader that writes `MEASURED_MARKER` and nothing else. It imports `pathlib` and `sys` only — no `roq.sh`, no `psql`, no socket, no database. Its only job is to prove, by its own absence of output, that the gate stopped before the reader. |
| `test_csv_seeded.csv` | holds `2026-11-25` so refusal R-b can be exercised. |
| `test_csv_empty.csv` | header only, so R-b passes and R-c is the one that fires. |
| `MEASURED_MARKER` | written by the control run (self-test passing). Its **presence** after the control and its **absence** after the failing run are the two halves of the test. |
| `2026-11-20/`, `run_day_*.log` | artefacts of the control run. |

## What it showed

- self-test exits 3 → `run_day: REFUSED -- self-test FAILED`, rc 2, **no** `MEASURED_MARKER`.
- same script, self-test exits 0 → proceeds, reader runs, `MEASURED_MARKER` written.

The second half is the control. Without it, the first half would equally be
explained by a gate that refuses everything.
