# P1 level test — working folder

Pre-registration: `../P1_level_test_prereg_2026-10-09.md` (git hash-object `7a708a64c4bb73f0712a6d6e78f92a5d411a8ece`).

| step | file | reveals outcome? | state |
|---|---|---|---|
| 1a Rule 13 | `p1_part1_eligibility.sql` (1a) | no | result owed |
| 1b eligibility, grid, one spot, front expiry, split | `p1_part1_eligibility.sql` (1b) | no | **run 2026-10-09 09:23 IST** → `part1b_result_2026-10-09_0923.json`: NIFTY N 85 (cal 56 to 08-26), SENSEX N 84 (cal 56 to 08-27); grid failures none; multi-spot 0; multi-expiry 0 |
| 3 replay check (§6.6) | `p1_part3_replay_check.sql` | no | run after 15:40 IST; expect zero rows |
| 2 extract | `p1_part2_extract.sql` | **yes** (hi, lo) | run only after 1a and 3 pass; export JSON |
| score | `p1_score.py <extract.json>` | — | stdlib; asserts N and n_cal against 1b before scoring |

This folder (SQL and scorer) is committed **before** Part 2 is run, so the code that reads the outcome is
fixed before the outcome exists. The scorer was exercised only on synthetic data (`synth/` is not committed).

Implementation notes, stated against the pre-registration:
- Walls: exact OI ties are broken by lower strike (the live view leaves them to the planner). The leader
  set uses the pre-registered tie-break (|gex_cr| desc, nearer spot, lower strike); the live view uses
  |gex_cr| desc, lower strike. Both differ from the views **only on exact ties**; Part 2 reports
  `ties_at_rank3`, and Part 3 would show any difference on the latest run.
- t1015 (§5.9, descriptive) = first run in [10:15, 11:15) IST; its path starts after that run.
