# Step 9 files over 40,960 bytes, not committed

Files over 40,960 bytes stay on the box in `~/meridian-cc/docs/research/pin_proof/step9/`.
Their content is fixed by the sha256 below, recorded in this commit.

Written 2026-11-26, MR-PIN4 step 9, after the pull finished (`PULL FINISHED
runs=19050`). Threshold 40,960 bytes (40 KiB); 1,066 of the folder's 1,071 files are
committed and these five are not.

| relative path | bytes | sha256 |
|---|---|---|
| `per_run.jsonl` | 39867891 | `1e7e43742103d06b7ab7f02f0ec719121475edcca21601eb11e3f635a6b07ea8` |
| `population.json` | 800388 | `7cb02771ceca02c7c8930486233e40f33f4ac8e7dff23afa58e115b364c63888` |
| `SHA256SUMS` | 109596 | `59d8617f4a5070f5f7c13dbdc49f54e5bf879adba04de67612ba6c3bc120dc87` |
| `b2_expected_2026-08-27.json` | 90539 | `d99aa037b56426a679192480aaf277950c409a736ca4beba115b1712df37dffa` |
| `aborted_attempt_A2_1/per_run.jsonl` | 52181 | `404601b96bbf278cd9ef32ed1db7dd82fc6f3ec6afae390c262f4ad50ff6630c` |

What each one is:

- **`per_run.jsonl`** — one JSON record per run, 19,050 lines: the figures F1 to F7 and
  the controls for every run of the population. `RESULT.md`, which **is** committed, is
  computed from it by `step9_summary.py`, also committed.
- **`population.json`** — the A1.1 population split, including the run-id lists.
  Its counts are reproduced in `RESULT.md` (both 19,050; `v2_only` 0, `v1_only` 0,
  `not_stamp` 0).
- **`SHA256SUMS`** — the folder-wide manifest written in P5 and verified `rc=0` there.
  It crosses the threshold only because the pull writes one `sql/pull_*.sql` per query
  (988 of them), and those 988 files are themselves committed, so their content is in
  git and needs no manifest. This file's own hash is in the table above, so nothing in
  the folder is left unverifiable: every file is either committed in full or hashed here.
- **`b2_expected_2026-08-27.json`** — the C4 fixture, extracted unchanged from
  `origin/main:docs/research/pin_proof/v2_check_v12/b2_expected_2026-08-27.json`, so it
  is already in git at that path with this same hash.
- **`aborted_attempt_A2_1/per_run.jsonl`** — the 25 records written by attempt A2-1
  before it crashed (see `PREREG_A2.md`). Never used for any figure. Its `run.log` and
  `pull.out` are small and are committed.
