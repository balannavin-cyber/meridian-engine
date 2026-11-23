<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/gamma_pipeline_audit_result_2026-11-22.md -->
# Gamma pipeline audit: result, 2026-11-22

Session MR-PIN2. Design: `gamma_pipeline_audit_prereg_FROZEN_2026-11-22.md` (sha256 `93ab228f…d49269`), approved by the operator ("go", 08:24 IST) before any net figure was seen. Run 09:51–09:53 IST, offline, one look. Full text on the engine box: `~/meridian-cc/docs/research/pin_proof/fix/audit/results.md` (212 lines, sha256 `024562bb0c15223255dce712e7b79d1b78d5b13865db99bb0c08c83c426b3bc3`), `runs.csv` (8,595 rows, sha256 `8363b69c…5a76f100`), prompts `PROMPT.md` (sha256 `dd08b496…f6002d19` after the post-hoc message was appended). Nothing here is authorised for the Board or production.

In the engine note's terms (`claude/engine_note_pin_basis_and_vendor_greeks_2026-11-18.md` §6): P = production as is; N = option G2 with the mean gamma; R = a G1-style own solve used as reference.

## Verdict (frozen rule, section 6): BETTER, both symbols, all four clauses

Market runs 09:15–15:29 IST, 58 days, 2026-08-25 to 2026-11-20. Valid runs: NIFTY 4,301 of 4,301; SENSEX 4,294 of 4,294. Lower is better for errors.

| Clause | NIFTY P | NIFTY N | SENSEX P | SENSEX N |
|---|---|---|---|---|
| 1. E_raw, mean / median | 0.0754 / 0.0666 | 0.0386 / 0.0356 | 0.0859 / 0.0635 | 0.0468 / 0.0377 |
| 2. E_shape, mean / median | 0.0770 / 0.0675 | 0.0386 / 0.0362 | 0.0804 / 0.0635 | 0.0428 / 0.0387 |
| 3. abs(T − T_R), mean / median | 0.0623 / 0.0515 | 0.0351 / 0.0336 | 0.0654 / 0.0548 | 0.0303 / 0.0282 |
| 4a. largest positive net = R's, lead ≥ 5 % | 90.49 % (3406/3764) | 97.10 % (3655/3764) | 88.10 % (3414/3875) | 98.17 % (3804/3875) |
| 4b. largest abs net = R's, lead ≥ 5 % | 77.08 % (2788/3617) | 96.07 % (3475/3617) | 81.01 % (2917/3601) | 97.56 % (3513/3601) |

The reference shares N's structure (one gamma × (OIc − OIp)); the test shows the vendor's mean gamma is closer to an own-solve gamma than two separate vendor gammas are. NIFTY and SENSEX are the same days and the same vendor, not two independent tests.

## Descriptive (not part of the rule)

- **Production sign per strike (N1)**, strikes with OIc ≠ OIp: NIFTY wrong 0.943 % by count (1,911/202,613), 4.213 % weighted by reference gross; SENSEX wrong 0.962 % (3,126/324,987), 2.891 % weighted, plus zero 0.977 % by count, 0.005 % weighted. Cause of the bad strikes: NIFTY zero-gamma leg 21, both gammas present 1,898; SENSEX zero-gamma leg 4,423, both present 1,879.
- **Total-net sign against R (N4)**: all runs P 21.83 % / N 15.00 % (NIFTY, n 4,301), P 16.51 % / N 7.96 % (SENSEX, n 4,294). Runs with abs(T_R) ≥ 0.05: P 9.87 % / N 1.72 % (n 2,797), P 8.57 % / N 0.67 % (n 2,836).
- **Call/put ratio (I2)**: median of run medians 1.0000 both symbols; 51.866 % and 50.910 % of pairs outside [0.8, 1.25]. Unweighted, and vendor gammas carry five decimals, so this measure is coarse at small gammas and is not clean evidence of the size of the asymmetry.
- **Gross shape (L1)**: N lower than P on the mean (0.0533 vs 0.0599; 0.0543 vs 0.0651), higher on the median (0.0483 vs 0.0463; 0.0485 vs 0.0425).
- **Reference quality (K1)**: fallback strikes carry 0.017 % (NIFTY) and 0.019 % (SENSEX) of reference gross on average; no strike without a reference gamma.
- **Grain**: G1 single expiry by construction of the pull (not a measurement); G2 NOT MEASURABLE (no per-leg timestamp in the files); G3 0 duplicates.
- **Checks**: the audit's gross peaks equal the replay v2 K and VS pins on 4,301/4,301 and 4,294/4,294 runs. Every market run in the chain files has a row. On the latest stored run, stored `gex_cr` equals the replica on 51/51 and 84/84 strikes.

## POST-HOC decomposition (11:07–11:31 IST; not part of the rule)

Box: `fix/audit/decomp.md` sha256 `046ad0df…71df3301`, `runs_decomp.csv` sha256 `81d0abeb…616bf847`; P and N columns identical to `runs.csv` on 8,595 of 8,595 runs.

- **The gamma field is never missing in the chain files.** Every "blank" is a present `0.0`. Legs with OI and gamma 0: NIFTY 15.385 % by count (61,452/399,422), 1.951 % OI-weighted; in-the-money legs 31.218 % / 12.354 %, out-of-the-money 0.006 % / 0.001 %. SENSEX 14.977 % (87,104/581,573), 1.504 %; in-the-money 32.235 % / 3.511 %, out-of-the-money 1.350 % / 0.905 %.
- **Filling zeros alone does not help.** B2 = a zero gamma taken from the other leg, two gammas kept otherwise. Share of the P-to-N improvement that B2 delivers, on the means: E_raw −0.75 % (NIFTY) and −2.43 % (SENSEX); E_shape +6.59 % and +1.50 %; total-net error −34.20 % and −16.35 % (B2 is worse than P). Clear-lead abs peak: B2 76.64 % vs P 77.08 % (NIFTY), 81.39 % vs 81.01 % (SENSEX). B1 (missing-only fill) equals P exactly, as it must when nothing is missing.
- **By day**, N's mean lower than P's: E_raw 57/58 and 53/58; E_shape 57/58 and 52/58; total-net error 55/58 and 58/58.
- **Expiry day vs other days**, mean E_raw P → N: NIFTY 0.0653 → 0.0418 (n 884) and 0.0780 → 0.0377 (n 3,417); SENSEX 0.0584 → 0.0462 (n 964) and 0.0938 → 0.0470 (n 3,330).
- **The seven days where N's mean E_shape exceeds P's** (NIFTY 2026-10-09; SENSEX 2026-10-27, 10-28, 10-29, 11-11, 11-17, 11-19) are days where P is unusually low (0.0217–0.0426 against 0.0780 / 0.0858 on the other days) while N stays near its usual level (0.0235–0.0558 against 0.0389 / 0.0429). Forward gap, zero rate, fallback share, at-the-money vol, small-gamma share and top-strike share do not separate them; frozen runs are 0 on five of the seven (22 on 11-17, 17 on 11-19). No mechanism is established. SENSEX 2026-11-17 is also a day the engine note records with a vendor call/put IV ratio of 0.96.
- **Small vendor gammas**: OI-weighted share of legs with gamma below 0.00010 is about 15 % on NIFTY and 33–44 % on SENSEX. At five decimals these carry one significant digit. Whether the stored column or the vendor payload sets that precision is not verified.

## What it does not show

- Layer 3: nothing here tests whether the sign convention describes dealer positioning.
- The reference uses last-traded prices; N's remaining error against it (about 0.04) is not attributed between the vendor's mean gamma and the reference.
- Whether another one-gamma rule (the out-of-the-money leg, an OI-weighted mean, an own solve) is closer than the mean. Not tested.
- Whether `gamma_metrics` regime, flip level or zone gate any decision (`fix/audit/consumers.md` §6).

## VS view dry run (same session, 08:36–08:43 IST)

The draft view's SELECT (`2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql`, revision 2) on the latest run of each symbol: plan with no sequential scan, 2.93 s, 135 rows; strike order identical to `vs_scores` over all 51 (NIFTY) and 84 (SENSEX) strikes. Not created; nothing reads it.
