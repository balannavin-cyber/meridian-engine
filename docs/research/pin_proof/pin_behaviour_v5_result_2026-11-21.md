# Pin behaviour study v5 — result, 2026-11-21

Session MR-PIN2. Design: `claude/pin/pin_behaviour_study_v5_FROZEN_2026-11-21.md` (sha256 8fcb30ca…c0108b). Prompt: `claude/pin/cc_prompt_pin_behaviour_C_measures.md`.
Status: descriptive study, no pass/fail. Nothing here is authorised for the Board or production.

Source of every figure below: the Claude Code screen prints of 21 Nov 2026 (~11:13, ~11:20 IST) and the full `results.md` (435 lines) printed verbatim in six pieces at 11:30–11:42 IST and read in full by the reviewing session. The files are on the engine box only:
`~/meridian-cc/docs/research/pin_proof/lookback_v5/results.md` sha256 `9f0c4e755f7e2911419f24aec914b3f6820868067dafb59563a0429ec8769fe9`
`…/lookback_v5/runs.csv` sha256 `305dc48d561112906352fa3a3e90832a8cc409118fb6c368ebf5b7f698d7cd9f`
`…/lookback_v5/SHA256SUMS` refreshed, 2985 files.

## 1. Checks before the run

- Precondition: pull log last line `ALL 491 DONE`, no STOP, 491 days.
- Self-tests 18 pass, 0 fail (ST1 round trips; ST2 planted chain: ATM 25000, T 25100, N 25200, call wall 25100, put wall 25100 under both gammas, worst sigma_K deviation 1.353e-07, no fallback; ST3 tie → 24950; ST4 zero OTM price → fallback counted 1).
- Worked example NIFTY 2025-04-01 12:30 recomputed by hand by the reviewing session from the printed inputs: T = 3060 minutes, sigma_rem 278.97 points, sigma_wall 325.72 / band ±488.58 points, 20 eligible strikes, flat gamma at 23200 = 1.4235e-03 (printed 1.4236e-03), per-strike gamma at 23500 = 9.659e-04 (printed 9.6588e-04), T lead 0.1012, PW1 lead 0.1713. All agree.
- Implementation note: per-strike maps are pruned at load time (kept only OI at the pin strikes, full maps for the four worked examples) because holding them for ~11,760 runs exceeded `ulimit -v 700000`. No measure's inputs changed.

## 2. Data quality

| Symbol | Sessions | OK_EMPTY days | Runs present / expected | Valid | Invalid | sigma_atm from a further strike | Runs whose front expiry is not a session |
|---|---|---|---|---|---|---|---|
| NIFTY | 246 | 0 | 5904 / 5904 | 5904 | 0 | 19 | 0 |
| SENSEX | 245 | 1 | 5856 / 5880 | 5854 | 2 | 11 | 96 |

- The 24 absent SENSEX runs are the one OK_EMPTY day, 2025-04-28 (no spot bar).
- Invalid runs: SENSEX 2025-08-06 14:45 (5 strikes with OI) and SENSEX 2025-08-28 14:30 (6 strikes with OI), reason `sigma_atm`.
- Fallback legs: median share 0.0000, p90 0.0000, 0.0 % of runs with > 20 % of strikes on fallback, both symbols.

## 3. Screen table (primary gamma; buckets = sessions to expiry)

Columns: med|d| = median |pin − spot| in strike steps; ATM = share of runs where pin = ATM strike; outW = share of wall-defined runs with the pin outside [put wall, call wall]; chg = median changes per session (15-minute sampling); ld<5 = % of changes whose prior lead was < 5 %; l<5 = % of runs with lead < 5 %; amp = % of runs with put OI > call OI at the pin strike.
chg and ld<5 per bucket were computed for the screen from runs.csv, not written by analyze_v5.py (results.md reports them per symbol × pin; see §4).

```
NIFTY  (step 50)                                   SENSEX (step 100)
pin bkt  runs med|d| ATM  outW chg ld<5 l<5 amp   pin bkt  runs med|d| ATM  outW chg ld<5 l<5 amp
T   0    1272  0.4 59.1%  0.2%  4.0 23.3 8.6 44.6 T   0    1272  0.6 45.6%  0.0%  6.0 30.1 12.9 47.7
T   1    1272  0.6 40.9%  0.0%  1.0 50.0 8.3 41.5 T   1    1224  1.3 22.0%  0.0%  1.0 57.1 10.5 40.1
T   2    1272  0.7 36.8%  0.0%  1.0 65.9 12.0 42.3 T   2    1224  1.8 17.2%  0.0%  1.0 69.5 12.6 38.6
T   3+   2088  0.9 29.1%  0.0%  1.0 73.3 12.4 39.6 T   3+   2134  1.6 16.6%  0.0%  0.0 67.1  9.1 45.5
PW1 0    1272  0.3 66.8%  0.3%  5.0 13.4 5.4 46.3 PW1 0    1272  0.4 55.0%  0.0%  7.0 25.4 11.6 48.9
PW1 1    1272  0.6 43.0%  0.0%  1.0 43.8 7.0 41.8 PW1 1    1224  1.1 24.4%  0.3%  2.0 50.9 10.9 41.1
PW1 2    1272  0.6 39.5%  0.0%  1.0 49.5 10.3 44.5 PW1 2    1224  1.5 19.9%  0.0%  1.0 57.3 12.0 42.5
PW1 3+   2088  0.8 32.1%  0.2%  1.0 60.2 10.3 40.9 PW1 3+   2134  1.5 18.2%  0.3%  0.0 65.9  9.6 46.0
PW2 0    1272  0.3 77.6%  0.5%  6.0  8.1 4.7 47.2 PW2 0    1272  0.3 67.5%  0.2%  8.0 14.5  8.3 48.9
PW2 1    1272  0.5 48.7%  0.0%  2.0 21.5 5.3 43.6 PW2 1    1224  0.8 33.3%  1.7%  3.0 28.3 10.5 46.1
PW2 2    1272  0.6 43.9%  0.1%  2.0 23.8 6.5 46.5 PW2 2    1224  1.1 24.7%  0.0%  2.0 40.9  8.1 47.8
PW2 3+   2088  0.7 36.6%  0.6%  1.0 38.8 8.1 42.2 PW2 3+   2134  1.2 21.5%  0.5%  1.0 49.4  8.5 47.4
N   0    1272  1.0 22.2%  7.9%  7.0 20.2 10.5 38.4 N   0    1272  1.6 13.1%  7.0%  8.0 25.4 14.5 39.9
N   1    1272  2.1  1.8% 19.3%  4.0 43.6 15.1 32.8 N   1    1224  4.6  0.3% 13.6%  3.0 39.7 14.1 26.5
N   2    1272  2.7  0.8% 16.7%  2.0 45.0 13.8 25.6 N   2    1224  5.7  0.3% 13.6%  2.0 50.3 12.0 20.1
N   3+   2088  3.4  1.1% 22.5%  3.0 50.9 17.2 23.9 N   3+   2134  5.0  0.4% 39.1%  3.0 43.0 15.7 32.6
```

## 4. Further figures from the full results.md (ALL buckets unless stated)

| Measure | Symbol | T | PW1 | PW2 | N | ATM |
|---|---|---|---|---|---|---|
| M1 signed (pin − S)/step, median | NIFTY | +0.22 | +0.17 | +0.13 | +1.72 | 0.00 |
| M1 signed (pin − S)/step, median | SENSEX | +0.37 | +0.28 | +0.17 | +3.25 | −0.01 |
| M2 pin outside corridor | NIFTY (n = 5904) | 0.0 % | 0.1 % | 0.3 % | 17.4 % | 8.9 % |
| M2 pin outside corridor | SENSEX (n = 5854) | 0.0 % | 0.2 % | 0.6 % | 21.5 % | 17.6 % |
| M2 pin = a wall | NIFTY | 66.1 % | 63.1 % | 59.4 % | 67.5 % | 31.9 % |
| M2 pin = a wall | SENSEX | 64.5 % | 60.7 % | 55.2 % | 59.3 % | 17.4 % |
| M3 changes per session, median | NIFTY (n = 246) | 1.0 | 1.0 | 2.0 | 4.0 | |
| M3 changes per session, median | SENSEX (n = 244) | 1.0 | 2.0 | 3.0 | 4.0 | |
| M3 changes with prior lead < 5 % | NIFTY | 45.2 % (n = 500) | 33.4 % (583) | 19.1 % (764) | 36.8 % (1036) | |
| M3 changes with prior lead < 5 % | SENSEX | 45.5 % (n = 539) | 41.2 % (711) | 27.5 % (877) | 36.7 % (1126) | |
| M3 there-and-back | NIFTY | 23.2 % | 26.9 % | 30.8 % | 28.0 % | |
| M3 there-and-back | SENSEX | 24.3 % | 28.6 % | 27.6 % | 30.6 % | |
| M3 hold length, median runs | NIFTY / SENSEX | 4.0 / 3.0 | 4.0 / 3.0 | 3.0 / 2.0 | 2.0 / 2.0 | |
| M5 put OI > call OI at pin | NIFTY | 41.7 % | 43.0 % | 44.5 % | 29.3 % | |
| M5 put OI > call OI at pin | SENSEX | 43.4 % | 44.9 % | 47.5 % | 30.3 % | |
| M6 score share, median | NIFTY | 0.1761 | 0.2285 | 0.3016 | 0.1269 | |
| M6 score share, median | SENSEX | 0.1350 | 0.1716 | 0.2226 | 0.0924 | |
| M6 lead, median | NIFTY | 0.2359 | 0.2749 | 0.3413 | 0.1884 | |
| M6 lead, median | SENSEX | 0.2494 | 0.2680 | 0.3034 | 0.1888 | |
| M6 runs with lead < 5 % | NIFTY | 10.6 % | 8.5 % | 6.4 % | 14.6 % | |
| M6 runs with lead < 5 % | SENSEX | 10.9 % | 10.8 % | 8.8 % | 14.3 % | |
| M7 abs(pin − settle)/step, bucket 0 | NIFTY (n = 1272) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| M7 abs(pin − settle)/step, bucket 1 | NIFTY (n = 1272) | 3.00 | 3.00 | 3.00 | 3.00 | 2.00 |
| M7 abs(pin − settle)/step, bucket 0 | SENSEX (n = 1248) | 2.00 | 2.00 | 2.00 | 2.00 | 1.00 |
| M7 abs(pin − settle)/step, bucket 3+ | SENSEX (n = 2110) | 7.00 | 7.00 | 7.00 | 8.00 | 7.00 |
| M9 pin differs g vs g_flat, lead < 5 % | NIFTY | 34.8 % (n = 627) | 37.3 % (504) | 33.4 % (380) | 34.7 % (860) | |
| M9 pin differs g vs g_flat, lead ≥ 5 % | NIFTY | 2.1 % (n = 5277) | 1.4 % (5400) | 0.9 % (5524) | 5.8 % (5044) | |
| M9 pin differs g vs g_flat, lead < 5 % | SENSEX | 37.6 % (n = 641) | 38.9 % (632) | 30.5 % (515) | 43.3 % (839) | |
| M9 pin differs g vs g_flat, lead ≥ 5 % | SENSEX | 2.1 % (n = 5213) | 1.6 % (5222) | 0.8 % (5339) | 7.2 % (5015) | |

Other:

- M2, spot itself outside the corridor: NIFTY 22.9 % (bucket 0: 16.6 %, 3+: 27.3 %); SENSEX 26.9 % (bucket 0: 9.5 %, 3+: 43.3 %). Inverted walls: NIFTY 1 run, SENSEX 0. Undefined: 0. SENSEX 3+: T = a wall on 86.3 % of runs.
- M3 under g_flat is near-identical to the primary (T: 1.0 change per session; 44.7 % / 43.9 % of changes on thin leads; 23.1 % / 27.6 % there-and-back).
- M4, 60-minute windows where the ATM strike moved ≥ 2 steps (windows overlap), same way / stayed / opposite, %: NIFTY (n = 685) T 42.3 / 56.6 / 1.0; PW1 48.9 / 50.5 / 0.6; PW2 60.6 / 39.3 / 0.1; N 42.5 / 46.4 / 11.1. SENSEX (n = 1452) T 29.2 / 69.4 / 1.4; PW1 38.8 / 60.5 / 0.6; PW2 49.9 / 50.0 / 0.1; N 36.8 / 51.4 / 11.7.
- M7 by clock hour on expiry day: ATM is never further from settle than any pin in any hour, on either symbol. SENSEX: 96 of 5854 runs excluded for want of a usable settle.
- M8, same strike: NIFTY T–PW1 93.1 %, T–PW2 84.1 %, T–N 22.2 %, T–ATM 39.8 %, PW1–PW2 90.5 %, PW2–ATM 49.6 %, N–ATM 5.7 %. SENSEX T–PW1 91.1 %, T–PW2 78.9 %, T–N 24.1 %, T–ATM 24.2 %, PW1–PW2 87.0 %, PW2–ATM 34.6 %, N–ATM 3.1 %.
- M9 ALL: NIFTY T 5.6 %, PW1 4.5 %, PW2 3.0 %, N 10.0 %; SENSEX T 6.0 %, PW1 5.6 %, PW2 3.5 %, N 12.4 %.

## 5. Reading

1. The Board's rule (N, netted call − put) misbehaves on clean inputs. It sits a median 1.7 (NIFTY) and 3.3 (SENSEX) steps above spot, is almost never the ATM strike off expiry day, is outside the wall corridor on 17.4 % / 21.5 % of runs (gross pins ≤ 0.6 %), picks a call-heavy strike about 70 % of the time, agrees with the textbook pin on only 22–24 % of runs, changes about four times a session, and is the only pin that moves against spot in a material share of M4 windows (~11 %). The outside-corridor behaviour seen live is a property of the rule, not only of the data.
2. Textbook (T) and the wide pressure pin (PW1) are nearly the same object: same strike on 91–93 % of runs.
3. The tight pressure pin (PW2) is close to an ATM tracker on expiry day (pin = ATM on 67.5–77.6 % of runs), follows spot most readily, and has the highest concentration and lead and the fewest thin-lead runs.
4. T is the stickiest: a median of one change per session; when spot moves two steps it stays put more often than it follows; lowest there-and-back share. About 45 % of its changes come when the lead was under 5 %.
5. The textbook pin is one of the two walls on about two-thirds of runs (66.1 % / 64.5 %). Most of the time it is not a third level; it repeats the larger wall.
6. Spot is outside the Board-rule corridor on about a quarter of runs, because the rule does not force the put wall below spot and the call wall above it. "Pin inside the corridor" is therefore a weaker statement than it sounds, and for T/PW it is partly built in (those pins weight gross OI by a gamma that peaks near spot; the walls are OI maxima within 1.5 σ of spot).
7. The pin strike is a modest concentration: T holds a median 17.6 % (NIFTY) / 13.5 % (SENSEX) of the total score.
8. No pin is nearer the settle strike than the ATM strike in any bucket or expiry-day hour. On SENSEX expiry day ATM is nearer (1 step against 2); on NIFTY one session out ATM is nearer (2 against 3). Consistent with P1 (S94). The pin describes where positioning is concentrated; it is not shown to forecast.
9. Put OI exceeds call OI at the pin strike on 42–48 % of runs for the gross pins: no stable sign at the pin.
10. The two gammas disagree almost only at near-ties (30–39 % of runs with lead < 5 %; 0.8–2.1 % otherwise for the gross pins).

Limits stated by results.md itself: nothing after 2026-03-30; OI is not dealer inventory; an OTM close can be a stale print; the walls use the study's sigma (from the straddle), not the vendor's `atm_iv_avg`, so M2 is about the rule, not about what the Board drew on a given day; 15-minute sampling.

## 6. Post-hoc diagnostics (not study measures; run after the results were seen, 21 Nov ~11:20 IST, from runs.csv)

Forward quality, F − S in strike steps, valid runs:

| Symbol | Bucket | n | p5 | median | p95 | Runs with abs(F − S) > 1 step |
|---|---|---|---|---|---|---|
| NIFTY | 0 | 1272 | −0.29 | 0.03 | 0.29 | 0 of 1272 = 0.0 % |
| NIFTY | 1 | 1272 | −0.36 | 0.19 | 0.74 | 19 of 1272 = 1.5 % |
| NIFTY | 2 | 1272 | −0.12 | 0.40 | 0.99 | 63 of 1272 = 5.0 % |
| NIFTY | 3+ | 2088 | −0.12 | 0.53 | 1.14 | 167 of 2088 = 8.0 % |
| SENSEX | 0 | 1272 | −0.51 | 0.05 | 0.48 | 0 of 1272 = 0.0 % |
| SENSEX | 1 | 1224 | −0.37 | 0.34 | 1.04 | 70 of 1224 = 5.7 % |
| SENSEX | 2 | 1224 | −0.52 | 0.59 | 1.50 | 279 of 1224 = 22.8 % |
| SENSEX | 3+ | 2134 | −0.01 | 0.79 | 1.70 | 681 of 2134 = 31.9 % |

The forward is orderly: basis near zero on expiry day and growing with time to expiry, in line with carry. The earlier annualised figures ((F − S)/S ÷ T: NIFTY min −2031.33 %, p5 −67.07 %, median 8.07 %, p95 93.56 %, max 3434.64 %, beyond ±15 % on 2116 / 5904; SENSEX min −1993.20 %, p5 −68.15 %, median 7.58 %, p95 85.91 %, max 4104.96 %, beyond ±15 % on 2139 / 5854) were an artefact of dividing a small basis by a very small T. That metric was the reviewing session's choice and was a poor one; the claim that a third of forwards are stale or crossed is withdrawn.

Textbook pin differing between per-strike and flat gamma, split on the basis:

| Symbol | Split | n | Pin differs |
|---|---|---|---|
| NIFTY | abs(F − S) > 1 step | 249 | 24 = 9.6 % |
| NIFTY | abs(F − S) ≤ 1 step | 5655 | 307 = 5.4 % |
| SENSEX | abs(F − S) > 1 step | 1030 | 93 = 9.0 % |
| SENSEX | abs(F − S) ≤ 1 step | 4824 | 259 = 5.4 % |

SENSEX runs whose front expiry is not a session (96 = 4 days × 24; expiry reconstructed as day + dte_cal):

| Day | Expiry | Runs |
|---|---|---|
| 2026-01-09 | 2026-01-15 | 24 |
| 2026-01-12 | 2026-01-15 | 24 |
| 2026-03-27 | 2026-04-02 | 24 |
| 2026-03-30 | 2026-04-02 | 24 |

2026-01-15 is the Step 0 oddity (a front expiry with no session). 2026-04-02 lies beyond the last session in the window (2026-03-30).

Git: `git --no-optional-locks status --porcelain` outside `docs/research/pin_proof/` = 105 lines, all `??` (untracked), none modified or staged; first ten are under `docs/research/futoi/`. The pin session made no git write.

## 7. Open items

- Operator's choice of pin definition: pending.
- Board discrepancy list additions from this study: the wall rule lets spot sit outside the corridor on about a quarter of runs; `v_gex_strike_walls` has no tie-break; `latest_gamma_walls` has no definition in `sql/`.
- Parked, separate pre-registrations: predictive test on the chosen pin (no holdout in this history); P1c; production gamma fix.
