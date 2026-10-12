# P3b — per-cycle invariants sidecar (S96-H)

Design and rulings: `P3b_invariant_sidecar_design_note_2026-10-12.md` (H1–H8; fixture result in §6).

| file | what |
|---|---|
| `p3b_core.sql` | table `p3b_invariant_checks` + function `p3b_sweep(p_now, p_window, p_min_age)`; `RUN_ID_TYPE` substituted at build (text on the fixture, the live type on apply) |
| `fixture_load.sh` | the six golden days into local Postgres 16 (database `p3b`) under the live table names |
| `test_p3b_fixture.py` | T1 agreement with P3a (run, not recalled) · T2 P3a's four mutants × six days · T3 states |
| `run.log` | the run of record, 2026-10-12 07:24:47–07:25:22 IST: P3B FIXTURE PASS |
| `p3b_t4_fixture_1001.sql` | T4 body on the fixture (10-01 SENSEX); its counts equal the function's |
| `p3b_t4_live_1009.sql` | T4 body over every run of 2026-10-09, both symbols, for `bin/roq.sh` (read-only) |

Run: `./fixture_load.sh; sed 's/RUN_ID_TYPE/text/g' p3b_core.sql | psql -d p3b; ( ulimit -v 700000; python3 -I test_p3b_fixture.py )`
Never 08:30–15:40 IST on a trading day.
