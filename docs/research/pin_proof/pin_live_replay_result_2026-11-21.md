<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_live_replay_result_2026-11-21.md -->
# Pin live replay: result, 2026-11-21

Session MR-PIN2. Design: `pin_live_replay_prereg_FROZEN_2026-11-21.md` (sha256 cbad76e1…f91139). Prompt: `cc_prompt_pin_live_replay.md`. Run 2026-11-21 18:04–18:34 IST, read-only. Nothing here is authorised for the Board or production.

Source of every figure: the Claude Code end-of-task screen print. Full tables on the engine box, `~/meridian-cc/docs/research/pin_proof/fix/replay/`: `results.md` sha256 `794360e2254e76691b67737e244bebb62b343f6a668d2c31fa618046646a2eeb` (156 lines), `runs.csv` sha256 `52c5f48b347640bfb19cea0b0f607da7fbdef730fc96223d41904b804288dbe8` (678 rows), `SHA256SUMS` 50 files. `results.md` has not been read in full by the reviewing session.

## 1. Conduct

- Days 2026-11-16 to 11-19, NIFTY and SENSEX; 339 front-expiry runs per symbol (87, 78, 87, 87), 336 valid each. The 3 invalid per symbol are runs with T ≤ 0. The runs include pre-open (from 08:30 IST) and post-close (to 15:40 IST) runs.
- Query: index scans only, plan gate passed; first day 5.28 s; all eight symbol-days pulled without a stop. First start of the seven-day loop failed on a wrong relative path to `bin/roq.sh` before any query reached the database; path corrected and restarted.
- `analyze_v5.py` sha256 `4958435201740e86acb9791781abe764a4df42d09eefab987e7bcbd805086979`, imported unchanged; its self-tests 18 pass. V2/V1 planted-chain tests 13 pass. T check by hand on the first run: 7,620 minutes, equal to the code's.
- Walls: preference (i), `gex_cycle_history.call_wall_strike` / `put_wall_strike` (the Board's own stored walls).
- Spot: the design says the first positive per-leg spot; the query returned the minimum and the maximum per run and they were equal on every run (0 ambiguous).
- One analysis defect caught before any figure was reported: the Board's pin was aliased only in the CSV writer, so B read n = 0 in M-a and M-c on the first pass; fixed and re-run. The verdicts do not use B.
- No tracked file changed.

## 2. Verdicts (rule fixed in the design: same strike as K on ≥ 95 % of runs with K's lead ≥ 5 %, and on ≥ 85 % of all valid runs, per symbol)

| Symbol | Construction | Lead ≥ 5 % | All valid | Verdict |
|---|---|---|---|---|
| NIFTY | V2 (vendor γ, two legs) | 98.9 % (280/283) | 93.8 % (315/336) | PASS |
| NIFTY | V1 (one vendor γ per strike) | 92.6 % (262/283) | 89.6 % (301/336) | FAIL |
| NIFTY | F (flat own γ) | 98.6 % (279/283) | 94.9 % (319/336) | PASS |
| SENSEX | V2 | 98.3 % (290/295) | 93.5 % (314/336) | PASS |
| SENSEX | V1 | 94.6 % (279/295) | 89.0 % (299/336) | FAIL |
| SENSEX | F | 99.7 % (294/295) | 96.1 % (323/336) | PASS |

By the design's order of preference (V2, V1, F): **V2 is enough.** The fix can be a gross-ranking view on stored columns, with no new job and no own solve.

Agreement when K's lead is under 5 %: NIFTY V2 66.0 % (35/53), V1 73.6 %, F 75.5 %; SENSEX V2 58.5 % (24/41), V1 48.8 %, F 70.7 %.

## 3. Measures

M-a, all four days:

| Symbol | Pin | Runs | Median abs(pin − S), steps | Pin = ATM | Outside stored corridor | Changes per day (median) | Distinct strikes per day (median) |
|---|---|---|---|---|---|---|---|
| NIFTY | B | 335 | 3.17 | 2.7 % | 3.3 % | 12.0 | 4.5 |
| NIFTY | V2 | 336 | 0.86 | 32.1 % | 0.3 % | 5.5 | 3.0 |
| NIFTY | V1 | 336 | 0.85 | 33.6 % | 0.3 % | 7.5 | 3.0 |
| NIFTY | F | 336 | 0.85 | 32.7 % | 0.0 % | 8.0 | 3.5 |
| NIFTY | K | 336 | 0.85 | 31.0 % | 0.3 % | 6.5 | 3.5 |
| SENSEX | B | 335 | 4.41 | 5.1 % | 24.8 % | 32.0 | 4.5 |
| SENSEX | V2 | 336 | 1.21 | 23.2 % | 0.0 % | 20.5 | 2.5 |
| SENSEX | V1 | 336 | 1.38 | 23.5 % | 0.0 % | 20.0 | 2.5 |
| SENSEX | F | 336 | 1.23 | 22.0 % | 0.0 % | 20.0 | 2.5 |
| SENSEX | K | 336 | 1.19 | 22.9 % | 0.0 % | 19.5 | 2.5 |

M-c:
- NIFTY 2026-11-18 (87 runs): K took 25,300 on 50 runs, 25,500 on 28 and 25,200 on 9; median distance from spot K 1.37 steps against B 5.37 steps.
- SENSEX 2026-11-19: outside the stored corridor B 2.4 % (2/84), K 0.0 % (0/84). The 19 Nov board log's "pin outside its band" (K3) refers to the pin band, a different measure from the wall corridor tested here.

M-d, frozen runs (whole-chain call OI and put OI both equal to the day's first run at or after 09:15 IST):
- NIFTY: 0/87, 0/78, 0/87, 6/87 (6.9 %).
- SENSEX: 31/87 (35.6 %), 23/78 (29.5 %), 24/87 (27.6 %), 26/87 (29.9 %).
- K pin changes with a frozen run before or after: NIFTY 1 of 30 (3.3 %); SENSEX 70 of 84 (83.3 %).
- Not broken down: how many frozen runs are pre-open runs (before 09:15), which can carry the anchor's OI legitimately.

M-e: 1 run per symbol with no Board pin row; fallback strikes NIFTY 2, SENSEX 0; legs with oi > 0 and ltp ≤ 0: 0.

## 4. Reading

1. On the live chain the gross pin sits near spot (about 1 step) where the Board's pin sits 3–4 steps away, and it is inside the Board's own corridor on essentially every run where the Board's pin is outside on 3.3 % (NIFTY) and 24.8 % (SENSEX).
2. On the day that started this (NIFTY 18 Nov) the gross pin was on 25,300 for most of the session, not 25,500. It was on 25,500 for 28 of 87 runs.
3. The vendor's stored gammas are good enough for the pin: V2 lands on the ruled construction's strike on 98–99 % of clear-lead runs. The own-solve job scoped earlier is not needed for the pin.
4. SENSEX pin churn is mostly a data problem: about 20 changes a day under every gross construction, and 83 % of them sit next to a frozen-OI run. No pin definition removes that; it belongs to the frozen-run item of the board list (D6).
5. NIFTY changes fall from 12 a day (Board) to 5.5–8 (gross).

## 5. Limits

- Four days, one cycle each; the thresholds (95 %, 85 %) were the reviewing session's choice, approved before the run.
- Agreement with K shows V2 reproduces the ruled construction; it does not show either is right.
- V2 counts a blank vendor gamma as zero. It passed on these days; a day with a vendor blackout near the money could behave differently.
- The frozen-run definition may include pre-open runs.
