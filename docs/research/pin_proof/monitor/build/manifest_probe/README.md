# manifest_probe — SYNTHETIC. Nothing here is a reading of any trading day.

Built 2026-11-24 to exercise `run_day.sh`'s SHA256SUMS step. **The folders named
`2026-11-21`, `2026-11-22` and `2026-11-23` are not monitor days.** They exist
only because the probe had to pass a date to the script, and the dates were
chosen to be ones the relaxed probe copy would accept. Every
`*_T1_strikes.txt` in them contains the literal text `fake|raw|read` and no
database was opened: the stub reader imports `pathlib`, `subprocess` and `sys`
only. No line was produced in `pin_monitor.csv` for any of them — the file does
not exist.

| file | what it is |
|---|---|
| `run_day.sh` | a copy of `../../run_day.sh` differing in **exactly two lines** (`FIRST_DAY="2026-11-01"`, `NOT_BEFORE="00:00:00"`), so the manifest step is reachable before 2026-11-25 |
| `selftest_pin_monitor.py` | a stub that passes |
| `pin_monitor_day.py` | a stub reader, left in its case-(b) form: it writes one fake raw read and leaves a detached writer appending to it for ~3 s |

## What it showed

| case | result |
|---|---|
| normal | `SHA256SUMS 3 OK, 0 FAILED`, exit 0. The **completed** log is in the manifest and verifies. |
| control A — one byte appended after hashing | `run_day_*.log: FAILED`, `sha256sum -c` rc 1. The verify can fire. |
| control B — the old placement | log hashed mid-write `6617a3ab…` vs complete `5c1be756…`, and the manifest records the complete one. The two differ, which is why building the manifest inside the reader failed on the log every day. |
| (b) a file still being written | `SHA256SUMS 1 OK, 1 FAILED`, the offending name on stderr, `MANIFEST VERIFY FAILED`, exit **4** |
| (c) reader exits 7, manifest clean | `SHA256SUMS 2 OK, 0 FAILED`, exit **7** — the reader's code is kept, not overwritten by 4, and the final `run_day: exit` line is printed |

The manifest lines themselves are not in the log: they are printed after `tee`
has closed, which is unavoidable — a log cannot contain its own hash.
