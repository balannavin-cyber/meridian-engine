# C1 result — NOT CONFIRMED (underpowered against -20 bp)

One look, run once. The pre-registration `futoi_C1_oi_sign_prereg_2026-11-19.md` is binding; where it and the run prompt differ, the pre-registration governs. No database was accessed: every figure comes from the two hashed export files and the closed run's design-period CSVs.

## Design-period values, computed before the test file was read

| quantity | value |
|---|---|
| mean absolute daily return, series-1 close | **65.3852 bp** |
| design sessions / daily returns | 246 / 245 |
| sessions with a trailing value / day-row subset | 235 / 234 |

### Tercile cut points — two versions, and which was used

| quantity | recomputed here | **used (atlas_readout2.py day-row)** | difference |
|---|---|---|---|
| trailing vol, lower cut | 0.005945 | **0.005946** | 8.71e-07 |
| trailing vol, upper cut | 0.006923 | **0.006921** | 1.90e-06 |
| trailing return, lower cut | -0.000282 | **-0.000266** | 1.62e-05 |
| trailing return, upper cut | 0.016437 | **0.015791** | 6.46e-04 |

**Which was used, and why.** The **day-row cut points as `atlas_readout2.py` computed them** are used for section 7's bucketing, by operator ruling 2026-11-19: the run prompt says "exactly as atlas_readout2.py defines them", and section 7 of the pre-registration says the cut points are **fixed from the design period**, which is where the atlas fixed them. They are constants in the code (`ATLAS_CUTS`), not recomputed at scoring time.

**They do NOT match the recomputation exactly, and the difference is stated rather than reconciled by adjustment.** Both use the same definition — the slice `sessions[max(0,i-20):i]`, ending at the prior close, cut over the day-row subset (`build_days` drops the first and last session) — on the same design period 2025-04-01..2026-03-30. The residual comes from two extractions of the same series: `atlas/data/fut_bars_hl.csv` carries a 15:29:59 series-1 close on **247** sessions, `data/futures_bars.csv` on **246**, so the trailing sets are 236 and 235 and the day-row subsets 235 and 234. One session's close is in one extraction and not the other. Vol cuts agree to 1.9e−06; return cuts differ by up to 6.5e−04.

A first pass cut the terciles over **all** sessions with a trailing value rather than the day-row subset, and used a "last bar at or before 15:29:59" scan rather than the exact bar; it matched neither. **All of this was settled on design-period data, before `--score` ran and before any test-period outcome existed.**

## Recorded about K4, before the verdict

**(1) K4's planted half cannot fail for a data reason.** Adding −20 bp to every `dF > 0` row shifts `mean(pos)` by exactly −20 and leaves `mean(neg)` untouched, so E shifts by exactly −20 as an **arithmetic identity, for any data**. The measured recovery was exactly −20.000 bp and the tolerance is 0.01. It checks that the grouping and the aggregation are wired to the same rows — a real wiring check — but it tests nothing about the data. **Planting on the week-shuffled copy would have been the stronger check**, showing a known effect recovered against a null background. It was **not changed**, by operator ruling, because the outcome had already been seen: changing a control after seeing the result it gates is the defect the one-look rule exists to prevent. K4 stands exactly as pre-registered.

**(2) The Part 0 K4 line printed the observed E before `--score` ran.** K4's output includes the line `observed: E = −7.192 bp`, so the main test's point estimate was visible to the operator and to the drafting assistant at Part 0, before the scoring step. **Nothing was changed after it** — no definition, window, exclusion, control or threshold. Recorded so a reader can weigh it, in the same spirit as the pre-registration's own exposure note.

## 1. The one test (section 4)

| quantity | value |
|---|---|
| sessions with dF > 0 | **45** of 90 used |
| sessions with dF < 0 | **45** of 90 used |
| mean r, dF > 0 | +0.247 bp |
| mean r, dF < 0 | +7.438 bp |
| **E** | **-7.192 bp** |
| E in NIFTY points | **-17.707 points** |
| bootstrap 5th percentile | -36.025 bp |
| bootstrap 95th percentile | **+27.505 bp** |
| ISO weeks resampled | 22 |
| resamples / seed | 10,000 / 20261119 |
| H1 (E < 0), one-sided α 0.05 | 95th percentile below 0: **False** |
| **VERDICT** | **NOT CONFIRMED (underpowered against -20 bp)** |
| E ÷ design mean absolute daily return | **-0.1100** |

Window: first session 2026-04-02, last session 2026-08-24, last d+1 2026-08-25. Sessions used **90**; excluded **10**:

| excluded, reason | n |
|---|---|
| session after a futures expiry | 5 |
| futures expiry session | 4 |
| d+1 missing or after 2026-08-25 | 1 |

**Exposure note, repeated from the pre-registration.** A trial export pasted into the drafting chat contained raw daily closes and OI for 11 test sessions, **2026-04-01..2026-04-20**. The drafting assistant saw them. No statistic was computed from them, and nothing in the pre-registration was changed because of them — the claim, test, window and controls were fixed in v2 before the file was seen. Recorded so a reader can weigh it.

**Size, no threshold (section 4).** A SIGN CONFIRMED verdict does not say the effect is worth trading; cost is assessed separately, later, before any use.

## 2. Section 7 reads — no verdict

Each is its own table and is never pooled into the main number.

### 7.1 Near contract (F1) alone, 2026-04-01..2026-10-29

| n dF1>0 | n dF1<0 | weeks | E (bp) | 5th–95th |
|---|---|---|---|---|
| 45 | 83 | 31 | +7.89 | [-18.03, +40.67] |

Sessions used 128; excluded: d+1 missing or after 2026-10-29 1, expiry session or the session after 13.

### 7.2 Regime — terciles of trailing 20-session vol and return

Cut points are **fixed from the design period** (section 7): vol 0.005946 / 0.006921, return -0.000266 / 0.015791. Trailing values use data up to the prior close only.


**Terciles of trailing realised volatility**

| tercile | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |
|---|---|---|---|---|---|
| T1 | — | — | — | — | — |
| T2 | 3 | 1 | 2 | +10.83 | [+10.83, +38.30] |
| T3 | 33 | 44 | 19 | -4.10 | [-40.58, +39.62] |

Sessions without a trailing value (fewer than 10 prior returns): 0 of 90.


**Terciles of trailing return**

| tercile | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |
|---|---|---|---|---|---|
| T1 | 12 | 19 | 12 | +36.49 | [-30.46, +120.79] |
| T2 | 14 | 11 | 11 | -46.86 | [-86.96, -3.31] |
| T3 | 19 | 15 | 13 | +3.12 | [-26.87, +37.87] |

Sessions without a trailing value (fewer than 10 prior returns): 0 of 90.

### 7.3 Per calendar month

| month | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |
|---|---|---|---|---|---|
| 2026-04 | 8 | 9 | 5 | +38.30 | [-60.03, +184.34] |
| 2026-05 | 12 | 5 | 4 | -21.24 | [-74.68, +41.89] |
| 2026-06 | 8 | 12 | 5 | -7.30 | [-56.07, +63.75] |
| 2026-07 | 4 | 16 | 5 | -31.35 | [-80.77, +55.17] |
| 2026-08 | 13 | 3 | 4 | +3.08 | [-4.52, +39.39] |

### Side by side — for reading only, no verdict

| read | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |
|---|---|---|---|---|---|
| **main test (section 4)** | 45 | 45 | 22 | -7.19 | [-36.02, +27.51] |
| 7.1 near contract F1 to 2026-10-29 | 45 | 83 | 31 | +7.89 | [-18.03, +40.67] |
| 7.2 vol tercile T1 | — | — | — | — | — |
| 7.2 vol tercile T2 | 3 | 1 | 2 | +10.83 | [+10.83, +38.30] |
| 7.2 vol tercile T3 | 33 | 44 | 19 | -4.10 | [-40.58, +39.62] |
| 7.2 ret tercile T1 | 12 | 19 | 12 | +36.49 | [-30.46, +120.79] |
| 7.2 ret tercile T2 | 14 | 11 | 11 | -46.86 | [-86.96, -3.31] |
| 7.2 ret tercile T3 | 19 | 15 | 13 | +3.12 | [-26.87, +37.87] |
| 7.3 2026-04 | 8 | 9 | 5 | +38.30 | [-60.03, +184.34] |
| 7.3 2026-05 | 12 | 5 | 4 | -21.24 | [-74.68, +41.89] |
| 7.3 2026-06 | 8 | 12 | 5 | -7.30 | [-56.07, +63.75] |
| 7.3 2026-07 | 4 | 16 | 5 | -31.35 | [-80.77, +55.17] |
| 7.3 2026-08 | 13 | 3 | 4 | +3.08 | [-4.52, +39.39] |

## 3. What was not tested

- **No cost threshold.** The verdict is about the sign only; size is reported against the typical daily move and nothing else.
- **No session after 2026-08-25** enters the main test. The near-contract read reaches 2026-10-29 and carries no verdict.
- **No price-direction conditioning.** Section 3 fixes the sign of dF as the only conditioning variable in the main test.
- **No live path.** The engine has no futures OI capture after 2026-10-29 (section 8); live use would need one.
- **No re-run.** One look. A defect found after scoring is reported, not rescored, without an operator ruling.
- **Not a holdout for anything else.** This spends 2026-04..2026-08 (and, for F1, to 2026-10) of the futures holdout for this claim alone.

*Read-only. No database access, no commit, no branch, no push. Produced 2026-11-19T02:30:57+00:00 UTC.*
