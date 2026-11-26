# Step 9: old against new gamma figures on stored history -- RESULT

Date line (Asia/Kolkata): `Thu Nov 26 21:36:08 IST 2026`

Design: `PREREG.md` as amended by `PREREG_A1.md`. Read-only, through
`bin/roq.sh` as `merdian_ro`. One look: this is it.

Unit for every exposure below: **crore per 100 % move**, the stored unit
(ADR-032). The Board's per-1 % figure is 0.01 times it. Shares and HHI have
no unit. Every count is k of n.

## Code hashes

```
646c26087c6d027af7782c361a6ea5c1191f8a0517c24aa9cd4bcd9d848c6642  step9_lib.py
e9f0340a9192b4951c95b59c8bb1e12b8f342809de4b046bacf2ff7c5aa4f3a3  selftest_step9.py
811758bdceb0de4a176345bdeae2774938646c563cb128533aae8ed913f71618  step9_pull.py
44f0576f388d7e213a39877e11f0f770e7589d087bd27518be746e8802bd45db  step9_summary.py
eef1981480b8cfb7b92e7396c50cb9ceae9e70f655557a0a33c8f7efbb4a73f0  PREREG.md
792b1fb342172caee297e275da66906dadd74163af9758c31e6947a0413557cb  PREREG_A1.md
150db6db5c35528702a31412c8579112ea6db2aa830cf7e0099ec4d1890bc81e  PREREG_A2.md
```

Runs in `per_run.jsonl`: **19050**.

## Population (A1.1)

| quantity | count |
|---|---|
| `gex_run_v2` runs with stamp `v2-1.2-gss` | 19050 |
| runs with rows in `gex_strike_snapshots` | 19050 |
| **in both (the population)** | **19050** |
| in `gex_run_v2` only | 0 |
| in `gex_strike_snapshots` only | 0 |
| `gex_run_v2` runs carrying another `rule_version` | 0 |
| of those, on 2026-08-27 | 0 |

### In `gex_run_v2` only, by date

None.

### In `gex_strike_snapshots` only, by date

None.

### Carrying another `rule_version`, by date

None.

## Controls

A1.3: C1a, C1b, C2 and C7 are **reported**, none is a stop. C3, C4 and C6
are **stops** -- the pull ends at the first failure, so a finished pull
means every run passed them.

| control | pass | fail | abstained (no row to compare) | denominator |
|---|---|---|---|---|
| C1a: V1 net vs `gex_cycle_history.net_gex` (+/-0.01 Cr) | 5543 of 5543 | 0 | 13507 | 19050 |
| C1b: V1 net vs `gamma_metrics.net_gex` (+/-0.01 Cr) | 18223 of 18223 | 0 | 827 | 19050 |
| C2: V1 net peak vs `pin_leader_strike` | 5543 of 5543 | 0 | 13507 | 19050 |
| C7 top share vs `conc_top1_share` (abs diff <= 1e-6) | 5543 of 5543 | 0 | 13507 | 19050 |
| C7 HHI vs `conc_hhi` (abs diff <= 1e-6) | 5543 of 5543 | 0 | 13507 | 19050 |
| C3 (stop): run `net_cr` vs sum of `net_cr(K)` | 19050 of 19050 | 0 | 0 | 19050 |
| C6 (stop): run identity, and dte single and equal | 19050 of 19050 | 0 | 0 | 19050 |

C7 differences (V1 computed from the strike rows minus the stored column):

| quantity | n | median | max abs |
|---|---|---|---|
| top share | 5543 | 0 | 1.11022e-16 |
| HHI | 5543 | 0 | 5.55112e-16 |

C4 (stop), the known day 2026-08-27 against `b2_expected_2026-08-27.json`
(sha256 `d99aa037...7dffa`), within the B2 limits of
`v2_check_v12/b2_compare.py`:

| quantity | value |
|---|---|
| fixture runs | 156 |
| compared | 156 of 156 |
| missing from the database | 0 |
| runs with a failing field | 0 |
| failing fields | 0 |
| runs in the database not in the fixture (listed, not compared) | 10 |

## Provenance (PREREG.md §5, inputs from PROVENANCE.md)

One writer period. The engine compared the row-building code of
`gex_strike_snapshots` as syntax trees at every commit that touched the
writer from 2026-05-25 to 2026-11-25 and found no change; the pin lane
checked it independently from the public repository (114 logged HEADs, 8
versions of the writer file, 8 functions identical as syntax trees in all 8).

| period | runs | chain check OK | NOT_COMPUTED |
|---|---|---|---|
| period_1 (2026-05-25 to 2026-11-25) | 19050 | 10067 of 19050 | 8983 of 19050 |

### Stated limit, not a stratum: dates holding a logged run whose HEAD is not vouched

Six of 19,608 logged writer runs sit at a HEAD that could not be vouched:
five at `a5163c4` on 2026-05-25 and 2026-05-26 (that commit does not descend
from `a776d8a`, which introduced the writer) and one with a blank HEAD on
2026-06-01. All six on the Windows host. A logged HEAD says nothing about
uncommitted edits in the working tree that day; the log holds 19,608 writer
runs against 19,050 stored runs and the reason for the 558 extra is not
known; the log does not tie a logged run to a `run_id`.

| date | symbol | runs | chain OK | NOT_COMPUTED |
|---|---|---|---|---|
| 2026-05-25 | NIFTY | 1 | 0 of 1 | 1 of 1 |
| 2026-05-25 | SENSEX | 1 | 0 of 1 | 1 of 1 |
| 2026-05-26 | NIFTY | 71 | 0 of 71 | 71 of 71 |
| 2026-05-26 | SENSEX | 73 | 0 of 73 | 73 of 73 |
| 2026-06-01 | NIFTY | 72 | 0 of 72 | 72 of 72 |
| 2026-06-01 | SENSEX | 74 | 0 of 74 | 74 of 74 |

## Figures of section 4, as amended by A1

F1 net exposure, F2 sign of net, F3 net peak strike, F3b largest positive
net strike, F4 net top share, F5 net HHI, F6 strike level and W, F7 the
guard beyond 5 %. V1 from the stored strike rows of
`gex_strike_snapshots` (A1.2); V2 from `gex_strike_v2` and `gex_run_v2`.
Differences are V2 minus V1.

### All runs

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| all | 19050 | 124 | -35082.4 | 754505 | 5.17832e+06 | 1.44671e+08 | 199490 | 0.158673 | 5.71158 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| all | 652 of 19050 | 4140 of 19050 | 7862 of 19050 | 6396 of 19050 | 0 of 19050 | 14378 of 19050 | 15577 of 19050 | 0 of 19050 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| all | -0.371525 | 57.4799 | -0.00190284 | 0.550271 | 13722 of 19050 | 0 of 19050 | 13464 of 19050 | 204646 / 3181290 |

### By symbol

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 9553 | 123 | -57381.5 | 1.01881e+06 | 4.69684e+06 | 1.44671e+08 | 316520 | 0.177992 | 5.71158 |
| SENSEX | 9497 | 124 | -25075.1 | 503154 | 6.14782e+06 | 1.15601e+08 | 133693 | 0.145035 | 2.85121 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 379 of 9553 | 2161 of 9553 | 4014 of 9553 | 2999 of 9553 | 0 of 9553 | 7049 of 9553 | 7701 of 9553 | 0 of 9553 |
| SENSEX | 273 of 9497 | 1979 of 9497 | 3848 of 9497 | 3397 of 9497 | 0 of 9497 | 7329 of 9497 | 7876 of 9497 | 0 of 9497 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| NIFTY | -0.533044 | 45.4488 | -0.00262312 | 0.513836 | 4799 of 9553 | 0 of 9553 | 9455 of 9553 | 193623 / 1450463 |
| SENSEX | -0.271844 | 57.4799 | -0.00160673 | 0.550271 | 8923 of 9497 | 0 of 9497 | 4009 of 9497 | 11023 / 1730827 |

### By set

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| main | 17136 | 123 | -41150.3 | 785873 | 4.88816e+06 | 1.44671e+08 | 206243 | 0.155268 | 5.71158 |
| post_close | 172 | 64 | -2791.79 | 1.68142e+07 | 1.09898e+08 | 1.11338e+08 | 250168 | 0.240323 | 3.7744 |
| pre_open | 1742 | 109 | 4080.43 | 459131 | 2.22056e+06 | 1.21156e+07 | 129120 | 0.190098 | 1.13386 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| main | 617 of 17136 | 3787 of 17136 | 6911 of 17136 | 5821 of 17136 | 0 of 17136 | 12988 of 17136 | 14162 of 17136 | 0 of 17136 |
| post_close | 2 of 172 | 30 of 172 | 73 of 172 | 67 of 172 | 0 of 172 | 131 of 172 | 118 of 172 | 0 of 172 |
| pre_open | 33 of 1742 | 323 of 1742 | 878 of 1742 | 508 of 1742 | 0 of 1742 | 1259 of 1742 | 1297 of 1742 | 0 of 1742 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| main | -0.348285 | 57.4799 | -0.00183371 | 0.550271 | 12227 of 17136 | 0 of 17136 | 12059 of 17136 | 182102 / 2857531 |
| post_close | -0.934862 | 48.0153 | -0.00361134 | 0.515828 | 144 of 172 | 0 of 172 | 111 of 172 | 1529 / 26442 |
| pre_open | -0.551656 | 12.0344 | -0.00263367 | 0.100334 | 1351 of 1742 | 0 of 1742 | 1294 of 1742 | 21015 / 297317 |

### By main-set window

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| (not main) | 1914 | 114 | 3297.5 | 555881 | 1.59195e+07 | 1.11338e+08 | 143360 | 0.193429 | 3.7744 |
| w1_0915_1059 | 4769 | 121 | -47408 | 393391 | 3.41137e+06 | 1.22684e+07 | 167628 | 0.146833 | 1.82862 |
| w2_1100_1359 | 8295 | 119 | -49753.6 | 749754 | 3.77474e+06 | 9.11209e+06 | 219245 | 0.152467 | 0.979339 |
| w3_1400_1530 | 4072 | 120 | -9172.82 | 1.5665e+06 | 1.43315e+07 | 1.44671e+08 | 247049 | 0.174887 | 5.71158 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| (not main) | 35 of 1914 | 353 of 1914 | 951 of 1914 | 575 of 1914 | 0 of 1914 | 1390 of 1914 | 1415 of 1914 | 0 of 1914 |
| w1_0915_1059 | 170 of 4769 | 1062 of 4769 | 1995 of 4769 | 1542 of 4769 | 0 of 4769 | 3601 of 4769 | 3937 of 4769 | 0 of 4769 |
| w2_1100_1359 | 318 of 8295 | 1889 of 8295 | 3305 of 8295 | 2783 of 8295 | 0 of 8295 | 6396 of 8295 | 6958 of 8295 | 0 of 8295 |
| w3_1400_1530 | 129 of 4072 | 836 of 4072 | 1611 of 4072 | 1496 of 4072 | 0 of 4072 | 2991 of 4072 | 3267 of 4072 | 0 of 4072 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| (not main) | -0.570747 | 48.0153 | -0.00268665 | 0.515828 | 1495 of 1914 | 0 of 1914 | 1405 of 1914 | 22544 / 323759 |
| w1_0915_1059 | -0.339039 | 19.9512 | -0.00180732 | 0.225342 | 3306 of 4769 | 0 of 4769 | 3481 of 4769 | 52106 / 811251 |
| w2_1100_1359 | -0.329709 | 16.0364 | -0.00169039 | 0.0851843 | 5821 of 8295 | 0 of 8295 | 5825 of 8295 | 88074 / 1388325 |
| w3_1400_1530 | -0.415433 | 57.4799 | -0.00237751 | 0.550271 | 3100 of 4072 | 0 of 4072 | 2753 of 4072 | 41922 / 657955 |

### By dte

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 4124 | 52 | 7215.13 | 2.20394e+06 | 2.12195e+07 | 1.44671e+08 | 454471 | 0.152857 | 5.71158 |
| 1_to_2 | 5423 | 70 | -8050.32 | 916698 | 3.53705e+06 | 6.86231e+06 | 202867 | 0.155763 | 1.82862 |
| 3_or_more | 9503 | 98 | -54202.5 | 298065 | 3.36668e+06 | 1.22684e+07 | 140736 | 0.163377 | 1.17956 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| 0 | 189 of 4124 | 1225 of 4124 | 1507 of 4124 | 1203 of 4124 | 0 of 4124 | 3187 of 4124 | 3448 of 4124 | 0 of 4124 |
| 1_to_2 | 225 of 5423 | 1247 of 5423 | 2248 of 5423 | 1703 of 5423 | 0 of 5423 | 4183 of 5423 | 4461 of 5423 | 0 of 5423 |
| 3_or_more | 238 of 9503 | 1668 of 9503 | 4107 of 9503 | 3490 of 9503 | 0 of 9503 | 7008 of 9503 | 7668 of 9503 | 0 of 9503 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| 0 | -0.354197 | 57.4799 | -0.00395265 | 0.550271 | 2549 of 4124 | 0 of 4124 | 2500 of 4124 | 11614 / 478538 |
| 1_to_2 | -0.237485 | 19.9512 | -0.00174534 | 0.225342 | 4381 of 5423 | 0 of 5423 | 3347 of 5423 | 33120 / 944587 |
| 3_or_more | -0.461025 | 11.2927 | -0.00146252 | 0.102208 | 6792 of 9503 | 0 of 9503 | 7617 of 9503 | 159912 / 1758165 |

### By V1 chain-check status

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| NOT_COMPUTED | 8983 | 63 | -43946.8 | 614156 | 4.75248e+06 | 1.44671e+08 | 237100 | 0.165123 | 5.71158 |
| OK | 10067 | 61 | -29525.1 | 999456 | 5.54185e+06 | 1.29153e+08 | 177737 | 0.154366 | 3.7744 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| NOT_COMPUTED | 317 of 8983 | 2005 of 8983 | 3755 of 8983 | 2906 of 8983 | 0 of 8983 | 6798 of 8983 | 7416 of 8983 | 0 of 8983 |
| OK | 335 of 10067 | 2135 of 10067 | 4107 of 10067 | 3490 of 10067 | 0 of 10067 | 7580 of 10067 | 8161 of 10067 | 0 of 10067 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| NOT_COMPUTED | -0.400954 | 57.4799 | -0.00228725 | 0.550271 | 6583 of 8983 | 0 of 8983 | 6657 of 8983 | 97835 / 1496212 |
| OK | -0.347804 | 49.9729 | -0.00165232 | 0.526895 | 7139 of 10067 | 0 of 10067 | 6807 of 10067 | 106811 / 1685078 |

### By schedule period

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| before_2026_10_26 | 15414 | 103 | -26679.5 | 889598 | 5.29676e+06 | 1.44671e+08 | 230402 | 0.16352 | 5.71158 |
| from_2026_10_26 | 3636 | 21 | -65708.7 | 294714 | 4.3383e+06 | 1.29153e+08 | 131355 | 0.143539 | 2.85121 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| before_2026_10_26 | 510 of 15414 | 3220 of 15414 | 6285 of 15414 | 5399 of 15414 | 0 of 15414 | 11487 of 15414 | 12467 of 15414 | 0 of 15414 |
| from_2026_10_26 | 142 of 3636 | 920 of 3636 | 1577 of 3636 | 997 of 3636 | 0 of 3636 | 2891 of 3636 | 3110 of 3636 | 0 of 3636 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| before_2026_10_26 | -0.364939 | 57.4799 | -0.00203958 | 0.550271 | 10916 of 15414 | 0 of 15414 | 11134 of 15414 | 168974 / 2531374 |
| from_2026_10_26 | -0.38741 | 49.9729 | -0.00156105 | 0.526895 | 2806 of 3636 | 0 of 3636 | 2330 of 3636 | 35672 / 649916 |

### By provenance period

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| period_1 | 19050 | 124 | -35082.4 | 754505 | 5.17832e+06 | 1.44671e+08 | 199490 | 0.158673 | 5.71158 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| period_1 | 652 of 19050 | 4140 of 19050 | 7862 of 19050 | 6396 of 19050 | 0 of 19050 | 14378 of 19050 | 15577 of 19050 | 0 of 19050 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| period_1 | -0.371525 | 57.4799 | -0.00190284 | 0.550271 | 13722 of 19050 | 0 of 19050 | 13464 of 19050 | 204646 / 3181290 |

### By symbol x set x dte

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | main | 0 | 1924 | 27 | -313.826 | 2.3437e+06 | 1.55783e+07 | 1.44671e+08 | 522275 | 0.175643 | 5.71158 |
| NIFTY | main | 1_to_2 | 1521 | 22 | 80937.9 | 1.94923e+06 | 4.4384e+06 | 5.35443e+06 | 643348 | 0.198208 | 0.571515 |
| NIFTY | main | 3_or_more | 5149 | 73 | -109508 | 368372 | 1.53075e+06 | 2.90348e+06 | 247202 | 0.170303 | 0.487851 |
| NIFTY | post_close | 0 | 24 | 15 | 1.56029e+07 | 1.08172e+08 | 1.11142e+08 | 1.11338e+08 | 1.56029e+07 | 1.37401 | 3.7744 |
| NIFTY | post_close | 1_to_2 | 13 | 10 | 14539.9 | 231232 | 1.32355e+06 | 1.47219e+06 | 221778 | 0.176237 | 0.417125 |
| NIFTY | post_close | 3_or_more | 50 | 37 | -164138 | 240273 | 1.00663e+06 | 1.11265e+06 | 210373 | 0.184066 | 0.406987 |
| NIFTY | pre_open | 0 | 181 | 23 | 105821 | 1.20554e+06 | 2.21795e+06 | 2.22237e+06 | 443539 | 0.234812 | 0.550964 |
| NIFTY | pre_open | 1_to_2 | 138 | 19 | 181251 | 1.22876e+06 | 1.69351e+06 | 1.76614e+06 | 335928 | 0.213872 | 0.367293 |
| NIFTY | pre_open | 3_or_more | 553 | 67 | -57513 | 190173 | 1.00322e+06 | 1.43048e+06 | 175522 | 0.184722 | 0.463305 |
| SENSEX | main | 0 | 1790 | 25 | 587.154 | 1.97831e+06 | 1.55006e+07 | 1.15601e+08 | 428387 | 0.12097 | 2.79233 |
| SENSEX | main | 1_to_2 | 3379 | 49 | -32279.9 | 446430 | 2.31441e+06 | 6.86231e+06 | 145009 | 0.140673 | 1.82862 |
| SENSEX | main | 3_or_more | 3373 | 48 | -32045.2 | 212211 | 4.16196e+06 | 1.22684e+07 | 85905.8 | 0.149925 | 1.17956 |
| SENSEX | post_close | 0 | 16 | 12 | 1.58494e+07 | 2.31503e+07 | 5.0874e+07 | 5.56598e+07 | 1.71891e+07 | 1.29164 | 2.85121 |
| SENSEX | post_close | 1_to_2 | 34 | 26 | -93396.6 | 298019 | 918791 | 945818 | 187267 | 0.201145 | 0.381405 |
| SENSEX | post_close | 3_or_more | 35 | 26 | -28668.3 | 232554 | 3.0855e+06 | 3.82171e+06 | 93148.7 | 0.186082 | 0.91532 |
| SENSEX | pre_open | 0 | 189 | 23 | -38817.1 | 323412 | 1.56443e+06 | 1.58691e+06 | 159057 | 0.189567 | 0.378247 |
| SENSEX | pre_open | 1_to_2 | 338 | 42 | 39202.8 | 428970 | 4.02945e+06 | 4.21807e+06 | 113008 | 0.189681 | 0.974554 |
| SENSEX | pre_open | 3_or_more | 343 | 44 | -13107.6 | 225902 | 1.1931e+07 | 1.21156e+07 | 42193.8 | 0.177569 | 1.13386 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| NIFTY | main | 0 | 113 of 1924 | 614 of 1924 | 639 of 1924 | 558 of 1924 | 0 of 1924 | 1441 of 1924 | 1610 of 1924 | 0 of 1924 |
| NIFTY | main | 1_to_2 | 65 of 1521 | 287 of 1521 | 572 of 1521 | 597 of 1521 | 0 of 1521 | 1022 of 1521 | 1147 of 1521 | 0 of 1521 |
| NIFTY | main | 3_or_more | 180 of 5149 | 1079 of 5149 | 2281 of 5149 | 1609 of 5149 | 0 of 5149 | 3867 of 5149 | 4246 of 5149 | 0 of 5149 |
| NIFTY | post_close | 0 | 0 of 24 | 0 of 24 | 2 of 24 | 22 of 24 | 0 of 24 | 19 of 24 | 8 of 24 | 0 of 24 |
| NIFTY | post_close | 1_to_2 | 0 of 13 | 4 of 13 | 9 of 13 | 0 of 13 | 0 of 13 | 12 of 13 | 11 of 13 | 0 of 13 |
| NIFTY | post_close | 3_or_more | 0 of 50 | 10 of 50 | 33 of 50 | 7 of 50 | 0 of 50 | 42 of 50 | 41 of 50 | 0 of 50 |
| NIFTY | pre_open | 0 | 5 of 181 | 39 of 181 | 91 of 181 | 46 of 181 | 0 of 181 | 149 of 181 | 135 of 181 | 0 of 181 |
| NIFTY | pre_open | 1_to_2 | 3 of 138 | 19 of 138 | 53 of 138 | 63 of 138 | 0 of 138 | 92 of 138 | 78 of 138 | 0 of 138 |
| NIFTY | pre_open | 3_or_more | 13 of 553 | 109 of 553 | 334 of 553 | 97 of 553 | 0 of 553 | 405 of 553 | 425 of 553 | 0 of 553 |
| SENSEX | main | 0 | 67 of 1790 | 501 of 1790 | 688 of 1790 | 534 of 1790 | 0 of 1790 | 1409 of 1790 | 1530 of 1790 | 0 of 1790 |
| SENSEX | main | 1_to_2 | 147 of 3379 | 875 of 3379 | 1437 of 3379 | 920 of 3379 | 0 of 3379 | 2794 of 3379 | 2949 of 3379 | 0 of 3379 |
| SENSEX | main | 3_or_more | 45 of 3373 | 431 of 3373 | 1294 of 3373 | 1603 of 3373 | 0 of 3373 | 2455 of 3373 | 2680 of 3373 | 0 of 3373 |
| SENSEX | post_close | 0 | 0 of 16 | 0 of 16 | 0 of 16 | 16 of 16 | 0 of 16 | 8 of 16 | 3 of 16 | 0 of 16 |
| SENSEX | post_close | 1_to_2 | 2 of 34 | 6 of 34 | 19 of 34 | 7 of 34 | 0 of 34 | 23 of 34 | 26 of 34 | 0 of 34 |
| SENSEX | post_close | 3_or_more | 0 of 35 | 10 of 35 | 10 of 35 | 15 of 35 | 0 of 35 | 27 of 35 | 29 of 35 | 0 of 35 |
| SENSEX | pre_open | 0 | 4 of 189 | 71 of 189 | 87 of 189 | 27 of 189 | 0 of 189 | 161 of 189 | 162 of 189 | 0 of 189 |
| SENSEX | pre_open | 1_to_2 | 8 of 338 | 56 of 338 | 158 of 338 | 116 of 338 | 0 of 338 | 240 of 338 | 250 of 338 | 0 of 338 |
| SENSEX | pre_open | 3_or_more | 0 of 343 | 29 of 343 | 155 of 343 | 159 of 343 | 0 of 343 | 212 of 343 | 247 of 343 | 0 of 343 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| NIFTY | main | 0 | -0.414046 | 45.4488 | -0.00529437 | 0.496024 | 621 of 1924 | 0 of 1924 | 1832 of 1924 | 9366 / 202520 |
| NIFTY | main | 1_to_2 | -0.168078 | 9.25981 | -0.00171136 | 0.0321033 | 694 of 1521 | 0 of 1521 | 1521 of 1521 | 26085 / 232775 |
| NIFTY | main | 3_or_more | -0.594645 | 6.66538 | -0.00205371 | 0.024295 | 2890 of 5149 | 0 of 5149 | 5149 of 5149 | 136949 / 867007 |
| NIFTY | post_close | 0 | -23.3415 | 43.4021 | -0.249072 | 0.513836 | 24 of 24 | 0 of 24 | 20 of 24 | 64 / 1906 |
| NIFTY | post_close | 1_to_2 | -1.37562 | 5.34576 | -0.00645292 | 0.029222 | 4 of 13 | 0 of 13 | 13 of 13 | 220 / 1975 |
| NIFTY | post_close | 3_or_more | -0.925757 | 5.75849 | -0.00298554 | 0.0169013 | 35 of 50 | 0 of 50 | 50 of 50 | 1183 / 8530 |
| NIFTY | pre_open | 0 | -1.23251 | 12.0344 | -0.00729916 | 0.100334 | 69 of 181 | 0 of 181 | 179 of 181 | 1201 / 20945 |
| NIFTY | pre_open | 1_to_2 | -0.430706 | 5.05285 | -0.00235852 | 0.0131596 | 85 of 138 | 0 of 138 | 138 of 138 | 2906 / 21997 |
| NIFTY | pre_open | 3_or_more | -0.754292 | 6.42231 | -0.0030994 | 0.022507 | 377 of 553 | 0 of 553 | 553 of 553 | 15649 / 92808 |
| SENSEX | main | 0 | -0.254738 | 57.4799 | -0.00304504 | 0.550271 | 1644 of 1790 | 0 of 1790 | 376 of 1790 | 731 / 224548 |
| SENSEX | main | 1_to_2 | -0.235242 | 19.9512 | -0.00168765 | 0.225342 | 3242 of 3379 | 0 of 3379 | 1515 of 3379 | 3517 / 617928 |
| SENSEX | main | 3_or_more | -0.287856 | 11.2927 | -0.000916846 | 0.102208 | 3136 of 3373 | 0 of 3373 | 1666 of 3373 | 5454 / 712753 |
| SENSEX | post_close | 0 | -22.8774 | 48.0153 | -0.276684 | 0.515828 | 16 of 16 | 0 of 16 | 0 of 16 | 0 / 1001 |
| SENSEX | post_close | 1_to_2 | -0.651088 | 4.56869 | -0.00351505 | 0.018488 | 34 of 34 | 0 of 34 | 13 of 34 | 17 / 5778 |
| SENSEX | post_close | 3_or_more | -0.321419 | 7.84185 | -0.00196667 | 0.09042 | 31 of 35 | 0 of 35 | 15 of 35 | 45 / 7252 |
| SENSEX | pre_open | 0 | -0.651346 | 2.75937 | -0.00384268 | 0.012135 | 175 of 189 | 0 of 189 | 93 of 189 | 252 / 27618 |
| SENSEX | pre_open | 1_to_2 | -0.285853 | 8.09854 | -0.00214752 | 0.0942722 | 322 of 338 | 0 of 338 | 147 of 338 | 375 / 64134 |
| SENSEX | pre_open | 3_or_more | -0.490965 | 5.8802 | -0.00137864 | 0.0189367 | 323 of 343 | 0 of 343 | 184 of 343 | 632 / 69815 |

### The 09:15 run, on its own line (also kept in the main set)

| stratum | runs | days | F1 diff median | F1 diff p90 | F1 diff p99 | F1 diff max | F1 abs median | W median | W max |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 114 | 114 | -111054 | 428500 | 730364 | 1.49177e+06 | 238136 | 0.177055 | 0.481501 |
| SENSEX | 108 | 108 | -21035.5 | 398755 | 4.9441e+06 | 1.22684e+07 | 113239 | 0.210695 | 1.27738 |

| stratum | F1 rel <1% | 1-10% | 10-50% | >=50% | V1 net zero | F3 same | F3b same | F3b one side none |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 4 of 114 | 27 of 114 | 56 of 114 | 27 of 114 | 0 of 114 | 83 of 114 | 89 of 114 | 0 of 114 |
| SENSEX | 2 of 108 | 12 of 108 | 52 of 108 | 42 of 108 | 0 of 108 | 81 of 108 | 89 of 108 | 0 of 108 |

| stratum | F4 diff pp median | F4 diff pp max abs | F5 diff median | F5 diff max abs | F6 sign-change runs | F6 V2-only runs | F7 runs with a removal | F7 legs removed / legs with gamma |
|---|---|---|---|---|---|---|---|---|
| NIFTY | -0.641888 | 5.38264 | -0.00411546 | 0.0304206 | 61 of 114 | 0 of 114 | 113 of 114 | 2397 / 17520 |
| SENSEX | -0.556525 | 7.13296 | -0.00318714 | 0.11235 | 100 of 108 | 0 of 108 | 60 of 108 | 171 / 19439 |

### F2, the 3 x 3 sign table (V1 sign down, V2 sign across)

NIFTY:

| V1 \ V2 | negative | zero | positive |
|---|---|---|---|
| negative | 2206 | 0 | 350 |
| zero | 0 | 0 | 0 |
| positive | 469 | 0 | 6528 |

SENSEX:

| V1 \ V2 | negative | zero | positive |
|---|---|---|---|
| negative | 3066 | 0 | 357 |
| zero | 0 | 0 | 0 |
| positive | 525 | 0 | 5549 |

### F2, r by fixed bin (r = abs(net) / sum of abs strike net)

| symbol | side | r <1% | 1-5% | >=5% | none (sum 0) |
|---|---|---|---|---|---|
| NIFTY | V1 | 294 of 9553 | 1154 of 9553 | 8105 of 9553 | 0 of 9553 |
| NIFTY | V2 | 325 of 9553 | 1206 of 9553 | 8022 of 9553 | 0 of 9553 |
| SENSEX | V1 | 308 of 9497 | 1243 of 9497 | 7946 of 9497 | 0 of 9497 |
| SENSEX | V2 | 329 of 9497 | 1278 of 9497 | 7890 of 9497 | 0 of 9497 |

### F6 strike-level counts, summed over runs

| quantity | strikes |
|---|---|
| n_union | 2679771 |
| n_both | 2044541 |
| n_v1_only | 635230 |
| n_v2_only | 0 |
| n_sign_change | 98241 |
| n_sign_change_both_nonzero | 40372 |
| n_v1_zero_v2_nonzero | 57696 |
| n_v1_nonzero_v2_zero | 173 |

### F7, the guard beyond 5 %

| quantity | value |
|---|---|
| legs removed, of legs with a stored gamma | 204646 of 3181290 |
| runs with at least one leg removed | 13464 of 19050 |
| share of the run's sum of abs `gex_cr` at strikes where a leg was removed: median | 0.0005813 |
| the same, maximum | 0.0480305 |
| F1 relative change over strikes within 5 % only: median | 0.30215 |
| W over strikes within 5 % only: median | 0.155552 |

## Day level (PREREG.md §5, ruling 4)

| scope | days | median over days of the day's median F1 relative change | maximum over days |
|---|---|---|---|
| all days | 244 | 0.292547 | 12.1967 |
| days with >= 37 main-set runs | 230 | 0.297908 | 5.46522 |

### The 10 days with the largest median F1 relative change (description only)

| date | symbol | main-set runs | median F1 relative change |
|---|---|---|---|
| 2026-06-11 | SENSEX | 1 | 12.1967 |
| 2026-07-17 | NIFTY | 75 | 5.46522 |
| 2026-07-17 | SENSEX | 75 | 5.40989 |
| 2026-10-30 | SENSEX | 76 | 3.28528 |
| 2026-09-21 | SENSEX | 74 | 3.23047 |
| 2026-07-10 | SENSEX | 75 | 1.96611 |
| 2026-09-08 | NIFTY | 74 | 1.71791 |
| 2026-08-26 | SENSEX | 74 | 1.61684 |
| 2026-07-14 | NIFTY | 75 | 1.52981 |
| 2026-09-16 | NIFTY | 74 | 1.51159 |

### Days with fewer than 37 main-set runs

| date | symbol | main-set runs |
|---|---|---|
| 2026-05-25 | NIFTY | 1 |
| 2026-05-25 | SENSEX | 1 |
| 2026-06-05 | NIFTY | 1 |
| 2026-06-09 | NIFTY | 23 |
| 2026-06-09 | SENSEX | 16 |
| 2026-06-10 | NIFTY | 12 |
| 2026-06-10 | SENSEX | 8 |
| 2026-06-11 | SENSEX | 1 |
| 2026-06-12 | NIFTY | 16 |
| 2026-06-12 | SENSEX | 16 |
| 2026-06-15 | SENSEX | 23 |
| 2026-06-16 | SENSEX | 33 |
| 2026-06-26 | NIFTY | 7 |
| 2026-06-26 | SENSEX | 7 |

