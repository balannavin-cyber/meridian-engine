# P1 level test — working folder

Pre-registration: `../P1_level_test_prereg_2026-10-09.md` (git hash-object `7a708a64c4bb73f0712a6d6e78f92a5d411a8ece`).

| step | file | reveals outcome? | state |
|---|---|---|---|
| 1a Rule 13 | `p1_part1_eligibility.sql` (1a) | no | **run 2026-10-09 09:32 IST: no rows** — no contamination range overlaps the study window |
| 1b eligibility, grid, one spot, front expiry, split | `p1_part1_eligibility.sql` (1b) | no | **run 2026-10-09 09:23 IST** → `part1b_result_2026-10-09_0923.json`: NIFTY N 85 (cal 56 to 08-26), SENSEX N 84 (cal 56 to 08-27); grid failures none; multi-spot 0; multi-expiry 0 |
| 3 replay check (§6.6) | `p1_part3_replay_check.sql` | no | **PASS — operator-reported 2026-10-09 after 15:40 IST: Supabase SQL editor returned "Success. No rows returned"**, i.e. the zero-row symmetric difference §6.6 requires. The editor message is the whole of the evidence; no result file was exported |
| 2 extract | `p1_part2_extract.sql` | **yes** (hi, lo) | **run 2026-10-09, after 1a and 3 passed**, whole file as one execution → `part2_extract_2026-10-09.json`, md5 `70be3c5218e497b8e1e583beba055de8`, 137,375 bytes, **338 rows**, **committed**. Provenance: the editor's JSON export, **re-serialised compact** (`json.dumps`, `separators=(',',':')`) for transfer to the box; same 338 rows and values — **the md5 is of this committed file, not of the editor download** |
| score | `p1_score.py <extract.json>` | — | **run 2026-10-09 ~19:50 IST, exit 0** → result doc `../P1_level_test_result_2026-10-09.md`. **Verdict (§5.8): A-NIFTY NO, B-NIFTY NO — the levels do not beat the null.** The N / n_cal assertion against 1b passed (NIFTY 85 / 56, SENSEX 84 / 56) |

This folder (SQL and scorer) is committed **before** Part 2 is run, so the code that reads the outcome is
fixed before the outcome exists. The scorer was exercised only on synthetic data (`synth/` is not committed).

Implementation notes, stated against the pre-registration:
- Walls: exact OI ties are broken by lower strike (the live view leaves them to the planner). The leader
  set uses the pre-registered tie-break (|gex_cr| desc, nearer spot, lower strike); the live view uses
  |gex_cr| desc, lower strike. Both differ from the views **only on exact ties**; Part 2 reports
  `ties_at_rank3`, and Part 3 would show any difference on the latest run.
- t1015 (§5.9, descriptive) = first run in [10:15, 11:15) IST; its path starts after that run.

**Part 2 revised 2026-10-09, before any run against the database (cost only).** The committed single-statement
form took ~49 s on a synthetic fixture (97 sessions, 330k strike rows): correlated front-expiry subqueries and
CTE row estimates of 1 driving 380 x 45,980 nested loops. It is now three TEMP tables (session-scoped, nothing
persistent) plus the final SELECT: ~3 s on the same fixture, and its JSON output was asserted **identical** to the
committed form's. Rules and columns unchanged. Fixture checks also run: Part 1 and Part 3 execute; Part 3 **fails
when it should** (a band parameter changed after the run produces a `walls` row) and returns zero rows otherwise;
the scorer's N / n_cal assertion fires on a fixture whose N differs from Part 1b.
