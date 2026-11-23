<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/pin_live_replay_v2_result_2026-11-21.md -->
# Pin live replay v2: result, 2026-11-21

Session MR-PIN2. Design: `pin_live_replay_prereg_v2_FROZEN_2026-11-21.md` (sha256 d2d87a85…e4b19a14). Prompt: `cc_prompt_pin_live_replay_v2.md`. Run 2026-11-21 21:00–21:55 IST, read-only. Supersedes `pin_live_replay_result_2026-11-21.md` (v1, four days) for the choice of construction. Nothing here is authorised for the Board or production.

Source: the Claude Code end-of-task screen print. Full tables on the engine box, `~/meridian-cc/docs/research/pin_proof/fix/replay_v2/`: `results.md` sha256 `69d0a1a3f272ffe448cde96c1aebc473d711f1ca4147410074987136097cd8c1` (180 lines), `runs.csv` sha256 `bf64d23ceecd684db4fde26f7f4a52a60035912673ac103c110f19779a056f11` (9,719 rows), `SHA256SUMS` 1,002 files. `results.md` not read in full by the reviewing session.

## 1. Conduct

- 64 weekdays 2026-08-25 to 2026-11-20, both symbols: 118 symbol-days with data, 10 empty, 0 stops (`ALL 128 DONE`); slowest chain query 5.8 s, volatility 3.1 s. Chain pulls for 16–20 Nov reused from v1.
- Empty weekdays: 2026-08-25 (run table has 83 runs, chain join returns no legs), 2026-09-14, 2026-10-20, 2026-10-21, 2026-11-10 (no runs). 2026-10-21 is in the contamination registry as a data gap. So 58 symbol-days per symbol are counted, 53 UNSEEN and 5 SEEN; no short days.
- `analyze_v5.py` hash as designed, 18 self-tests pass; VS and FV planted-chain tests 16 pass. No tracked file changed.
- 9,719 runs; 20 per symbol invalid (T ≤ 0). `atm_iv_avg` present on every run, age under 10 minutes on every market run. Fallback strikes NIFTY 8, SENSEX 0. No leg with oi > 0 and ltp ≤ 0; no ambiguous spot.
- The Board's stored pin (B) exists for 32 of 58 days per symbol (no `gex_cycle_history` row on 2,266 NIFTY and 2,258 SENSEX runs); B figures are on those days only.

## 2. Decision (rule fixed in the design; market runs, UNSEEN days)

| Construction | NIFTY pooled, clear lead | NIFTY days meeting both marks | SENSEX pooled, clear lead | SENSEX days meeting both marks | Result |
|---|---|---|---|---|---|
| V2 (vendor γ, two legs) | 98.74 % (3358/3401) | 47/53 = 88.7 % | 93.52 % (3177/3397) | 41/53 = 77.4 % | NOT ENOUGH |
| **VS (one vendor γ per strike)** | **99.65 % (3389/3401)** | **50/53 = 94.3 %** | **98.88 % (3359/3397)** | **51/53 = 96.2 %** | **ENOUGH** |
| FV (flat γ, stored ATM vol) | 95.15 % (3236/3401) | 37/53 = 69.8 % | 94.50 % (3210/3397) | 35/53 = 66.0 % | NOT ENOUGH |
| F (flat own γ) | 97.35 % (3311/3401) | 44/53 = 83.0 % | 98.38 % (3342/3397) | 48/53 = 90.6 % | NOT ENOUGH |

VS is the only construction that is enough on both symbols. It can be built as a view on stored columns.

## 3. Measures

M1, UNSEEN days, clear-lead agreement with K across days (median / 10th percentile / minimum):
- NIFTY: V2 100.0 / 95.7 / 86.8; VS 100.0 / 100.0 / 89.5; FV 100.0 / 84.2 / 62.1; F 100.0 / 90.8 / 59.1.
- SENSEX: V2 100.0 / 80.3 / 26.0; VS 100.0 / 98.6 / 64.9; FV 100.0 / 77.9 / 45.7; F 100.0 / 95.9 / 77.9.

M2, pooled over UNSEEN days, same strike as K on all valid runs | on clear-lead runs:
- NIFTY market (n = 3926): V2 94.1 | 98.7; VS 98.0 | 99.6; FV 90.5 | 95.1; F 92.9 | 97.4. Pre-open (n = 432): VS 94.9 | 96.9. Post-close (n = 62): VS 95.2 | 94.9.
- SENSEX market (n = 3919): V2 89.7 | 93.5; VS 97.8 | 98.9; FV 90.9 | 94.5; F 95.5 | 98.4. Pre-open (n = 430): VS 90.2 | 90.8. Post-close (n = 62): VS 95.2 | 96.5.

M3, market runs:

| Symbol | Pin | Median abs(pin − S), steps | Pin = ATM | Outside stored corridor | Median changes per day |
|---|---|---|---|---|---|
| NIFTY | B | 2.69 (n = 2278) | 2.9 % | 13.0 % (296/2278) | 5.5 (32 days) |
| NIFTY | VS | 0.74 (n = 4301) | 34.8 % | 0.0 % | 3.0 |
| NIFTY | K | 0.75 | 34.3 % | 0.0 % | 3.0 |
| SENSEX | B | 4.47 (n = 2280) | 1.7 % | 10.6 % (241/2280) | 7.0 (32 days) |
| SENSEX | VS | 1.49 (n = 4294) | 20.7 % | 0.1 % | 3.0 |
| SENSEX | K | 1.52 | 20.4 % | 0.1 % | 3.0 |

(V2, FV, F sit within 0.2 steps of VS and K on distance; V2 changes 3.0 / 4.5 times a day, FV 3.0 / 4.0, F 3.0 / 3.5.)

M5, agreement with K on clear-lead market runs, V2 | VS | FV | F:
- Vendor call/put gamma ratio, abs(ln R) ≥ 0.3: NIFTY (n = 452) 93.6 | 98.2 | 90.0 | 90.5; SENSEX (n = 360) 81.4 | 92.5 | 96.7 | 98.1. Below 0.1: NIFTY (n = 1502) 99.6 | 99.7 | 94.7 | 98.2; SENSEX (n = 1676) 96.3 | 99.9 | 92.5 | 98.3.
- Blank-leg share of OI ≥ 5 %: NIFTY (n = 243) 94.2 | 96.7 | 89.3 | 93.4; SENSEX (n = 155) 91.0 | 96.8 | 77.4 | 95.5. Under 2 %: NIFTY 99.6 | 100.0 | 96.3 | 98.0; SENSEX 95.8 | 99.8 | 96.4 | 98.7.
- Forward − spot, abs ≥ 1 step: NIFTY (n = 492) 97.0 | 99.6 | 89.4 | 89.6; SENSEX (n = 949) 86.6 | 96.7 | 95.3 | 95.9.
- Days to expiry 0: NIFTY (n = 776) 97.6 | 98.7 | 88.3 | 97.6; SENSEX (n = 746) 96.5 | 98.9 | 80.7 | 98.1. 3+: NIFTY (n = 2371) 99.7 | 100.0 | 98.1 | 98.4; SENSEX (n = 1536) 90.5 | 99.9 | 98.1 | 98.2.

M6, lowest V2 days (clear-lead, market): SENSEX 2026-09-25 26.0 % (VS, FV, F all 100), SENSEX 2026-10-16 35.6 % (all 100), SENSEX 2026-09-28 58.1 % (VS 98.6), SENSEX 2026-08-27 63.0 % (VS 87.0, FV 45.7, F 78.3), SENSEX 2026-08-26 64.9 % (VS 64.9, FV 90.5, F 97.3). 2026-11-20 ranks 23rd of the counted days for NIFTY (97.0 %) and 33rd for SENSEX (98.4 %), with VS, FV and F at 100 % on both.

M7, frozen runs (counted after the 09:15 reference run): NIFTY 0 of 58 days. SENSEX 4 of 58 days, 1.8 % of market runs (78/4294), next to 20.3 % of K's pin changes (66/325). Which four days is in `results.md`, not in the screen print.

## 4. Reading

1. The fix is VS: gross ranking with one vendor gamma per strike (the mean of the two legs, or the one that is not blank) times total open interest. It lands on the ruled pin's strike on 99.65 % (NIFTY) and 98.88 % (SENSEX) of clear-lead market runs over 53 unseen days.
2. V2 fails because it keeps the vendor's two gammas apart. Its agreement falls as the vendor's call/put gamma ratio moves away from 1, as the forward moves away from spot and as blank legs carry more open interest; on its worst days (26 %, 36 %) VS, FV and F all read 100 %. Averaging the legs removes most of that.
3. The flat-gamma versions are not better than VS. FV is weakest on expiry day (88.3 % NIFTY, 80.7 % SENSEX) and F fails the day condition on NIFTY.
4. 20 November was not unusual in market hours: V2 97.0 % / 98.4 %. What looked different that day was its pre-open and post-close runs, which the v1 rule counted and v2 reports apart. Every construction is weakest pre-open.
5. Against the Board's pin, on the 32 days it exists: the Board sits 2.7 (NIFTY) and 4.5 (SENSEX) strikes from spot and is outside its own corridor on 13.0 % and 10.6 % of market runs; the gross pins sit 0.7 and 1.5 strikes away and are outside on at most 0.1 %. The gross pins change about 3 times a day against 5.5 and 7.
6. Correction to the v1 result: frozen-OI runs are not a daily SENSEX condition. With pre-open runs excluded they occur on 4 of 58 days. v1's "about 30 % of SENSEX runs frozen, 83 % of pin changes" described the four days it looked at.

## 5. Limits

- K is the ruled construction, not a truth; this measures closeness to the ruling.
- VS still fails the day marks on 3 NIFTY and 2 SENSEX unseen days (minimum clear-lead agreement 89.5 % and 64.9 %), and is weaker pre-open (96.9 % / 90.8 % clear-lead).
- The M5 splits show what goes with a disagreement, not its cause.
- About three months; the 90 %-of-days threshold was the reviewing session's choice.
