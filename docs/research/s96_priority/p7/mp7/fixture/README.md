# M-P7 fixture test (synthetic data, local Postgres only — never the production database)

What it proves: the SQL arithmetic of `mp7_cycles.sql` equals an independent Python implementation
(`recompute.py`) on every column of every cycle, and three mutants are each caught. It does **not**
prove the live control: that is Part 0b on the box, at real volume (§D.49.7).

Recorded 2026-10-11 (S96), PostgreSQL 16.15 local, views loaded from the committed
`sql/2026-10-09_s93_v_dex_standing_book.sql` and `sql/2026-10-11_s95_v_oi_since_preopen.sql` bodies:

| run | result |
|---|---|
| clean, 2026-10-09, 146 cycles × 2 symbols | max abs diff **0** on all columns |
| mut1 parity put delta `Δ_C + 1` | 146 mismatches |
| mut2 PE gap not tested in flow | 144 mismatches |
| mut3 anchor moved to the first ≥ 09:15 row | 798 mismatches |
| scorer, live control perturbed by 1e-6 Cr / anchor by 5 min | STOP, exit 3 |
| scorer, Rule 13 visible rows 0 | STOP, exit 3 |
| status: frozen 10-02 / closed 10-03 / 09:20 first row 10-07 / normal 10-09 | NOT_SESSION / NOT_SESSION / NO_PREOPEN / ANCHORED |

The fixture's flow and badge numbers are synthetic and mean nothing about the market.

Reproduce (needs a local Postgres superuser): `psql -d mp7 -f schema.sql`, load the two view bodies,
`python3 gen.py` then load `data.sql`, run `mp7_run.sh` with `ROQ=fakeroq.sh OUT=out`, then
`python3 recompute.py out/cycles/2026-10-09.csv` and `python3 -I ../mp7_score.py out`.
