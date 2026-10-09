# P1 level test — RESULT

| Field | Value |
|---|---|
| **Pre-registration** | `docs/research/s92_priority/P1_level_test_prereg_2026-10-09.md`, `git hash-object` **`7a708a64c4bb73f0712a6d6e78f92a5d411a8ece`** |
| **Input** | `docs/research/s92_priority/p1/part2_extract_2026-10-09.json`, md5 **`70be3c5218e497b8e1e583beba055de8`** (137,375 bytes, **338 rows**). Provenance: the Supabase SQL editor's JSON export, **re-serialised compact** (`json.dumps`, `separators=(',',':')`) for transfer to the box — same 338 rows and values. **The md5 is of this committed file, not of the editor download**, so it does not verify against the editor's own output. |
| **Scorer** | `docs/research/s92_priority/p1/p1_score.py`, run as `python3 -I p1_score.py part2_extract_2026-10-09.json`, exit 0 |
| **Seed** | **20261009**, 10,000 resamples, percentile, 97.5 % interval (two primary tests, Bonferroni — §5.8) |
| **Scored** | 2026-10-09 ~19:50 IST (Session S93) |

**Preconditions — only what is sourced.** §6.2 NIFTY N 85 / SENSEX N 84 and calibration
56 / 56, **asserted by `p1_score.py` against Part 1b before scoring** (it exits non-zero on a
mismatch) and recorded in `p1/part1b_result_2026-10-09_0923.json`. §6.1 Rule 13 no overlap —
`p1/README.md:7`, run 09:32 IST, no rows. §6.3 grid, §6.4 one spot, §6.5 front expiry —
`p1/part1b_result_2026-10-09_0923.json`: `grid_failures: null`, `multi_spot_runs: 0`,
`multi_expiry_runs: 0`, both symbols. §6.6 Part 3 replay check returned zero rows before
Part 2 ran — **operator-reported 2026-10-09 after 15:40 IST: Supabase SQL editor returned
"Success. No rows returned"**, now recorded in `p1/README.md` (step 3 row). That editor
message is the whole of the evidence for this precondition; no result file was exported.

**Verdict (§5.8): A-NIFTY NO, B-NIFTY NO — the levels do not beat the null.**

---

## Scorer output, verbatim

# P1 level test — results

Input `part2_extract_2026-10-09.json` · seed 20261009 · 10,000 resamples · 97.5% interval · pre-registration `7a708a64c4bb73f0`


## NIFTY · levels at t0 (first run ≥ 09:15) — PRIMARY

Sessions scored: 85 · calibration 56 · holdout 29 · arm A excluded (NULL wall at the anchor): 0 · exact ties at leader rank 3: 0

| arm | half | n | mean real (σ) | mean null (σ) | mean e = null − real | interval |
|---|---|---:|---:|---:|---:|---|
| dA | cal | 56 | 0.892 | 0.964 | 0.0719 |  |
| dA | hold | 29 | 1.07 | 0.956 | -0.116 | [-0.365, 0.102] |
| dB | cal | 56 | 0.397 | 0.483 | 0.0858 |  |
| dB | hold | 29 | 0.613 | 0.526 | -0.0867 | [-0.282, 0.0902] |
| dA_high | cal | 56 | 0.863 | 0.973 | 0.11 |  |
| dA_high | hold | 29 | 1.13 | 1 | -0.131 | [-0.429, 0.14] |
| dA_low | cal | 56 | 0.921 | 0.954 | 0.0335 |  |
| dA_low | hold | 29 | 1.01 | 0.91 | -0.101 | [-0.466, 0.229] |

Hit and break-through rates, arm A (all sessions, real vs null):

| statistic | X | real | null |
|---|---|---:|---:|
| hitA_both | halfstep | 1.2% | 1.4% |
| hitA_both | 0.10sig | 1.2% | 0.8% |
| hitA_high | halfstep | 11.8% | 9.1% |
| hitA_high | 0.10sig | 11.8% | 6.5% |
| hitA_low | halfstep | 5.9% | 11.6% |
| hitA_low | 0.10sig | 7.1% | 8.9% |
| breakA_high | halfstep | 14.1% | 17.0% |
| breakA_high | 0.10sig | 14.1% | 18.3% |
| breakA_low | halfstep | 35.3% | 31.9% |
| breakA_low | 0.10sig | 35.3% | 33.8% |

By DTE bucket (mean e, all sessions):

| DTE | n | e_dA | e_dB |
|---|---:|---:|---:|
| 0 | 19 | 0.422 | 0.232 |
| 1 | 17 | 0.458 | 0.195 |
| 4+ | 49 | -0.309 | -0.111 |

## SENSEX · levels at t0 (first run ≥ 09:15) — descriptive

Sessions scored: 84 · calibration 56 · holdout 28 · arm A excluded (NULL wall at the anchor): 0 · exact ties at leader rank 3: 0

| arm | half | n | mean real (σ) | mean null (σ) | mean e = null − real | interval |
|---|---|---:|---:|---:|---:|---|
| dA | cal | 56 | 0.694 | 0.742 | 0.048 |  |
| dA | hold | 28 | 0.73 | 0.738 | 0.00797 | [-0.335, 0.247] |
| dB | cal | 56 | 0.385 | 0.455 | 0.0705 |  |
| dB | hold | 28 | 0.553 | 0.447 | -0.106 | [-0.414, 0.108] |
| dA_high | cal | 56 | 0.658 | 0.732 | 0.0741 |  |
| dA_high | hold | 28 | 0.811 | 0.743 | -0.0685 | [-0.46, 0.226] |
| dA_low | cal | 56 | 0.73 | 0.752 | 0.0219 |  |
| dA_low | hold | 28 | 0.648 | 0.732 | 0.0844 | [-0.267, 0.354] |

Hit and break-through rates, arm A (all sessions, real vs null):

| statistic | X | real | null |
|---|---|---:|---:|
| hitA_both | halfstep | 0.0% | 0.4% |
| hitA_both | 0.10sig | 0.0% | 0.8% |
| hitA_high | halfstep | 7.1% | 7.2% |
| hitA_high | 0.10sig | 8.3% | 9.9% |
| hitA_low | halfstep | 7.1% | 7.7% |
| hitA_low | 0.10sig | 9.5% | 10.0% |
| breakA_high | halfstep | 27.4% | 28.7% |
| breakA_high | 0.10sig | 26.2% | 27.6% |
| breakA_low | halfstep | 38.1% | 38.3% |
| breakA_low | 0.10sig | 36.9% | 37.3% |

By DTE bucket (mean e, all sessions):

| DTE | n | e_dA | e_dB |
|---|---:|---:|---:|
| 0 | 18 | 0.065 | 0.172 |
| 1 | 17 | 0.196 | 0.127 |
| 2–3 | 34 | 0.155 | -0.0301 |
| 4+ | 15 | -0.458 | -0.216 |

## NIFTY · levels at the 10:15 run — descriptive

Sessions scored: 85 · calibration 56 · holdout 29 · arm A excluded (NULL wall at the anchor): 0 · exact ties at leader rank 3: 0

| arm | half | n | mean real (σ) | mean null (σ) | mean e = null − real | interval |
|---|---|---:|---:|---:|---:|---|
| dA | cal | 56 | 0.48 | 0.513 | 0.0334 |  |
| dA | hold | 29 | 0.583 | 0.524 | -0.0585 | [-0.23, 0.0881] |
| dB | cal | 56 | 0.416 | 0.425 | 0.00946 |  |
| dB | hold | 29 | 0.44 | 0.436 | -0.00421 | [-0.121, 0.098] |
| dA_high | cal | 56 | 0.514 | 0.551 | 0.0369 |  |
| dA_high | hold | 29 | 0.613 | 0.551 | -0.062 | [-0.31, 0.145] |
| dA_low | cal | 56 | 0.446 | 0.476 | 0.0299 |  |
| dA_low | hold | 29 | 0.553 | 0.498 | -0.055 | [-0.35, 0.158] |

Hit and break-through rates, arm A (all sessions, real vs null):

| statistic | X | real | null |
|---|---|---:|---:|
| hitA_both | halfstep | 4.7% | 6.4% |
| hitA_both | 0.10sig | 4.7% | 3.6% |
| hitA_high | halfstep | 21.2% | 23.3% |
| hitA_high | 0.10sig | 20.0% | 17.7% |
| hitA_low | halfstep | 22.4% | 26.5% |
| hitA_low | 0.10sig | 18.8% | 18.1% |
| breakA_high | halfstep | 30.6% | 29.1% |
| breakA_high | 0.10sig | 30.6% | 31.3% |
| breakA_low | halfstep | 48.2% | 46.0% |
| breakA_low | 0.10sig | 49.4% | 51.8% |

By DTE bucket (mean e, all sessions):

| DTE | n | e_dA | e_dB |
|---|---:|---:|---:|
| 0 | 19 | 0.212 | 0.219 |
| 1 | 17 | 0.185 | 0.096 |
| 4+ | 49 | -0.143 | -0.11 |

## SENSEX · levels at the 10:15 run — descriptive

Sessions scored: 84 · calibration 56 · holdout 28 · arm A excluded (NULL wall at the anchor): 0 · exact ties at leader rank 3: 0

| arm | half | n | mean real (σ) | mean null (σ) | mean e = null − real | interval |
|---|---|---:|---:|---:|---:|---|
| dA | cal | 56 | 0.403 | 0.465 | 0.0626 |  |
| dA | hold | 28 | 0.528 | 0.454 | -0.0745 | [-0.277, 0.0839] |
| dB | cal | 56 | 0.328 | 0.396 | 0.0683 |  |
| dB | hold | 28 | 0.452 | 0.379 | -0.0732 | [-0.411, 0.139] |
| dA_high | cal | 56 | 0.335 | 0.436 | 0.101 |  |
| dA_high | hold | 28 | 0.579 | 0.418 | -0.16 | [-0.545, 0.112] |
| dA_low | cal | 56 | 0.47 | 0.495 | 0.0244 |  |
| dA_low | hold | 28 | 0.478 | 0.489 | 0.0114 | [-0.153, 0.138] |

Hit and break-through rates, arm A (all sessions, real vs null):

| statistic | X | real | null |
|---|---|---:|---:|
| hitA_both | halfstep | 2.4% | 1.7% |
| hitA_both | 0.10sig | 2.4% | 2.5% |
| hitA_high | halfstep | 11.9% | 13.0% |
| hitA_high | 0.10sig | 14.3% | 16.8% |
| hitA_low | halfstep | 11.9% | 13.2% |
| hitA_low | 0.10sig | 14.3% | 16.4% |
| breakA_high | halfstep | 38.1% | 36.9% |
| breakA_high | 0.10sig | 35.7% | 34.8% |
| breakA_low | halfstep | 45.2% | 47.5% |
| breakA_low | 0.10sig | 44.0% | 45.8% |

By DTE bucket (mean e, all sessions):

| DTE | n | e_dA | e_dB |
|---|---:|---:|---:|
| 0 | 18 | 0.116 | 0.189 |
| 1 | 17 | 0.134 | 0.166 |
| 2–3 | 34 | -0.0714 | -0.0303 |
| 4+ | 15 | -0.0353 | -0.228 |

## Verdict (§5.8) — the only two tests that can produce one

- **A-NIFTY · corridor: NO** — holdout -0.116 97.5% [-0.365, 0.102] includes 0; calibration 0.0719 · holdout < half calibration
- **B-NIFTY · leader set: NO** — holdout -0.0867 97.5% [-0.282, 0.0902] includes 0; calibration 0.0858 · holdout < half calibration

---

## Descriptive observations — post hoc, NOT findings, not claimable from this data

These are **not** results. §5.8 admits exactly two tests and both returned NO; nothing below
was pre-registered, and §5.9's descriptive items cannot produce a verdict. They are recorded
only so that a future pre-registration, if one is written, starts from something stated
rather than remembered.

**(a) Calibration `e` positive while holdout `e` is negative, in 7 of the 8 primary rows
across the four cells.** The primary rows are the `dA` and `dB` rows (two per cell, four
cells: NIFTY t0, SENSEX t0, NIFTY 10:15, SENSEX 10:15). Seven show a positive calibration
mean and a negative holdout mean. The single exception is **SENSEX t0 `dA`**, whose holdout
mean is +0.00797.

**(b) `e_dA` is positive at DTE 0 and DTE 1 and negative at DTE 4+, in all four cells.**
NIFTY t0 +0.422 / +0.458 → −0.309 · SENSEX t0 +0.065 / +0.196 → −0.458 · NIFTY 10:15
+0.212 / +0.185 → −0.143 · SENSEX 10:15 +0.116 / +0.134 → −0.0353.

**What these are not.** Both patterns are read off the same data that produced the NO, after
seeing it. (a) is the shape a calibration-fitted effect leaves when it does not transfer, and
is consistent with there being no effect at all. (b) is a split the pre-registration lists as
reporting-only (§5.1: DTE is a reporting stratum, never a selection), on buckets as small as
n = 15 (SENSEX DTE 4+, both SENSEX cells). **Neither is evidence for anything, and neither
authorises a gate, a trade rule, a display change or a build.** A DTE-conditioned level test
is **a candidate for a NEW pre-registration only** — which, per §1, is a new
pre-registration and not an amendment to this one.
