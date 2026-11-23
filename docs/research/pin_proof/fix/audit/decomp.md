<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/audit/decomp.md -->

# POST-HOC decomposition — B1 / B2 between P and N

**POST-HOC. Not part of the frozen rule.** E_raw, E_shape, T error, the N5 peaks and the lead ≥ 5 % classification are used exactly as defined; no new normalisation and no exclusion. Source `runs_decomp.csv` (8,595 rows) and `extra.csv`; `results.md` and `runs.csv` are unchanged.

## Item 0 — how the vendor gamma field is represented

Counted from the chain files over legs with OI > 0 in the strike set, market runs. **The field is never missing.** The only zero rendering is the JSON string `"0.0"`; there is no `null` and no absent key anywhere.

| symbol | side | legs | missing | present and exactly 0 | present and > 0 |
|---|---|---|---|---|---|
| NIFTY | ALL | 399422 | 0 = 0.000% (OI 0.000%) | 61452 = 15.385% (OI 1.951%) | 337970 = 84.615% (OI 98.049%) |
| NIFTY | ITM | 196804 | 0 = 0.000% (OI 0.000%) | 61439 = 31.218% (OI 12.354%) | 135365 = 68.782% (OI 87.646%) |
| NIFTY | OTM | 202618 | 0 = 0.000% (OI 0.000%) | 13 = 0.006% (OI 0.001%) | 202605 = 99.994% (OI 99.999%) |
| SENSEX | ALL | 581573 | 0 = 0.000% (OI 0.000%) | 87104 = 14.977% (OI 1.504%) | 494469 = 85.023% (OI 98.496%) |
| SENSEX | ITM | 256600 | 0 = 0.000% (OI 0.000%) | 82716 = 32.235% (OI 3.511%) | 173884 = 67.765% (OI 96.489%) |
| SENSEX | OTM | 324973 | 0 = 0.000% (OI 0.000%) | 4388 = 1.350% (OI 0.905%) | 320585 = 98.650% (OI 99.095%) |

**Consequence, stated before the numbers below: B1 (missing filled only) must equal P exactly on every real run, and (P−B1)/(P−N) must be 0.** B1 is exercised only by the planted self-test, where the missing fields are real.

## NIFTY — 4301 valid market runs, 58 days

### Error means and medians

| error | P mean | P median | B1 mean | B1 median | B2 mean | B2 median | N mean | N median |
|---|---|---|---|---|---|---|---|---|
| E_raw | 0.075396 | 0.0666447 | 0.075396 | 0.0666447 | 0.0756706 | 0.0637018 | 0.0385672 | 0.0355861 |
| E_shape | 0.0770432 | 0.0675368 | 0.0770432 | 0.0675368 | 0.0745093 | 0.0632442 | 0.038588 | 0.0361982 |
| T error | 0.0623073 | 0.0515087 | 0.0623073 | 0.0515087 | 0.0716052 | 0.0599138 | 0.0351221 | 0.0336193 |

### Attribution on the means (no clipping)

| error | P − B1 | P − B2 | P − N | (P−B1)/(P−N) | (P−B2)/(P−N) |
|---|---|---|---|---|---|
| E_raw | 0 | -0.000274572 | 0.0368288 | 0.00% | -0.75% |
| E_shape | 0 | 0.00253388 | 0.0384552 | 0.00% | 6.59% |
| T error | 0 | -0.00929793 | 0.0271852 | 0.00% | -34.20% |

### N5 agreement with R, clear-lead runs (R lead ≥ 5 %)

| peak | runs | P | B1 | B2 | N |
|---|---|---|---|---|---|
| pos | 3764 | 90.49% (3406/3764) | 90.49% (3406/3764) | 92.85% (3495/3764) | 97.10% (3655/3764) |
| abs | 3617 | 77.08% (2788/3617) | 77.08% (2788/3617) | 76.64% (2772/3617) | 96.07% (3475/3617) |

### Error means, expiry day vs other days

| scope | runs | E_raw P | E_raw B2 | E_raw N | E_shape P | E_shape B2 | E_shape N | T err P | T err B2 | T err N |
|---|---|---|---|---|---|---|---|---|---|---|
| expiry day | 884 | 0.0653254 | 0.0652987 | 0.0417857 | 0.0671395 | 0.064629 | 0.0419025 | 0.0510366 | 0.0603459 | 0.0377584 |
| other days | 3417 | 0.0780014 | 0.0783539 | 0.0377346 | 0.0796053 | 0.0770654 | 0.0377305 | 0.0652231 | 0.074518 | 0.03444 |

### By day: days on which N's mean is LOWER than P's

N lower than P on: E_raw 57/58 | E_shape 57/58 | T error 55/58.

## SENSEX — 4294 valid market runs, 58 days

### Error means and medians

| error | P mean | P median | B1 mean | B1 median | B2 mean | B2 median | N mean | N median |
|---|---|---|---|---|---|---|---|---|
| E_raw | 0.0858688 | 0.0634512 | 0.0858688 | 0.0634512 | 0.0868177 | 0.0631686 | 0.0467881 | 0.037738 |
| E_shape | 0.0804073 | 0.0635324 | 0.0804073 | 0.0635324 | 0.079841 | 0.0624997 | 0.0427712 | 0.0387086 |
| T error | 0.0653539 | 0.0548001 | 0.0653539 | 0.0548001 | 0.0710827 | 0.0587515 | 0.0303208 | 0.0282075 |

### Attribution on the means (no clipping)

| error | P − B1 | P − B2 | P − N | (P−B1)/(P−N) | (P−B2)/(P−N) |
|---|---|---|---|---|---|
| E_raw | 0 | -0.000948925 | 0.0390807 | 0.00% | -2.43% |
| E_shape | 0 | 0.000566244 | 0.0376361 | 0.00% | 1.50% |
| T error | 0 | -0.00572878 | 0.0350332 | 0.00% | -16.35% |

### N5 agreement with R, clear-lead runs (R lead ≥ 5 %)

| peak | runs | P | B1 | B2 | N |
|---|---|---|---|---|---|
| pos | 3875 | 88.10% (3414/3875) | 88.10% (3414/3875) | 90.40% (3503/3875) | 98.17% (3804/3875) |
| abs | 3601 | 81.01% (2917/3601) | 81.01% (2917/3601) | 81.39% (2931/3601) | 97.56% (3513/3601) |

### Error means, expiry day vs other days

| scope | runs | E_raw P | E_raw B2 | E_raw N | E_shape P | E_shape B2 | E_shape N | T err P | T err B2 | T err N |
|---|---|---|---|---|---|---|---|---|---|---|
| expiry day | 964 | 0.0583598 | 0.0604443 | 0.0461633 | 0.0593817 | 0.0599072 | 0.0474638 | 0.0495355 | 0.0548088 | 0.0362036 |
| other days | 3330 | 0.0938324 | 0.0944525 | 0.0469689 | 0.0864939 | 0.0856117 | 0.0414127 | 0.0699332 | 0.0757938 | 0.0286177 |

### By day: days on which N's mean is LOWER than P's

N lower than P on: E_raw 53/58 | E_shape 52/58 | T error 58/58.

## Item 4 — the days where N's mean E_shape exceeds P's

Frozen flag in `fix/replay_v2/runs.csv`: column `frozen`.

| symbol | day | runs | dte | E_sh P | E_sh B1 | E_sh B2 | E_sh N | mean abs(T_R) | mean fwd gap | zero rate OI-wt | missing rate OI-wt | fallback share GR | mean sigma_atm | gamma<1e-4 OI-wt | top strike share gross_R | frozen runs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-10-09 | 74 | 4 | 0.021738 | 0.021738 | 0.0217 | 0.023519 | 0.04251 | 0.425 | 0.097% | 0.000% | 0 | 0.1263 | 9.904% | 0.1457 | 0 |
| NIFTY | ALL OTHER DAYS | 4227 | 3.18 | 0.078011 | 0.078011 | 0.075434 | 0.038852 | 0.09141 | 0.355 | 1.983% | 0.000% | 0.000172 | 0.1719 | 15.319% | 0.1662 | 0 |
| SENSEX | 2026-10-27 | 75 | 2 | 0.024999 | 0.024999 | 0.024951 | 0.025104 | 0.03913 | 0.396 | 0.125% | 0.000% | 0.000742 | 0.2042 | 32.828% | 0.1036 | 0 |
| SENSEX | 2026-10-28 | 75 | 1 | 0.030888 | 0.030888 | 0.030978 | 0.034743 | 0.08589 | 0.0968 | 0.076% | 0.000% | 0 | 0.2209 | 36.866% | 0.1054 | 0 |
| SENSEX | 2026-10-29 | 75 | 0 | 0.037119 | 0.037119 | 0.036028 | 0.038979 | 0.0563 | 0.105 | 2.087% | 0.000% | 0 | 0.3258 | 41.089% | 0.1515 | 0 |
| SENSEX | 2026-11-11 | 75 | 1 | 0.034484 | 0.034484 | 0.033029 | 0.055755 | 0.2123 | 0.146 | 1.187% | 0.000% | 0 | 0.2408 | 42.207% | 0.0859 | 0 |
| SENSEX | 2026-11-17 | 75 | 2 | 0.035039 | 0.035039 | 0.033736 | 0.041744 | 0.115 | 0.24 | 0.657% | 0.000% | 0.00024 | 0.172 | 37.739% | 0.09398 | 22 |
| SENSEX | 2026-11-19 | 75 | 0 | 0.042643 | 0.042643 | 0.04482 | 0.051499 | 0.1497 | 0.1 | 2.868% | 0.000% | 0 | 0.2681 | 42.398% | 0.1594 | 17 |
| SENSEX | ALL OTHER DAYS | 3844 | 2.52 | 0.085817 | 0.085817 | 0.085216 | 0.042943 | 0.118 | 0.465 | 1.485% | 0.000% | 0.000192 | 0.192 | 44.364% | 0.1268 | 39 |

