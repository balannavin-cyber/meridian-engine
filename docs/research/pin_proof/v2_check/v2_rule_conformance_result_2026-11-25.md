# V2 rule conformance check (V-2): result

**Verdict: PASS.** Recorded run Wed 2026-11-25, 15:58 IST, on the box, in the pin Claude Code session, once.
**Lane:** pin (MR-PIN3). **Pre-registration:** `claude/pin/v2_rule_conformance_prereg_FROZEN_2026-11-25.md`, sha256 `b1a156a8722da1700d22f4fbaf1a27dc116bdf3841075bf85e5cedd34ad7361d`.
**Authorises nothing.** A pass returns the next decisions to the operator.

## 1. What was tested

- Engine code `merdian_compute/gamma_v2.py` at commit `a9982c7a3ea438c72a012051ecd05b5f3e9c8dfa` (branch `engine/v2-gamma`), sha256 `05fa0cab9138db945a6a33b9cc648e10421f9334b648f9843efcf6640e35a5c7`.
- Against rule v1.1 as implemented independently by the pin lane.
- Worktree at `8adbeea038e83ab9c252473d522a48afbbc9caa0` (branch `pin/v2-check`, one commit on top of the engine commit). Python 3.10.12.

## 2. Order of events

1. Pre-registration frozen and filed, about 09:55 IST.
2. Independent implementation and self-test frozen and delivered to the operator, about 10:00 IST: `v2_indep.py` sha256 `fbf63b09bca727a4bad4fd0112abcf7f8e3e0939e0204a78d93295676c0fa783`; `selftest_v2_indep.py` sha256 `06e3b2ed58065b6fc252fddbc7cd068c83cfb70ca47a1175988a49aa8297f733`.
3. The engine's files reached the pin lane at 10:02 IST, after that freeze. The pin lane then read them.
4. Harness `compare_v2.py` written after reading the engine's interface, sha256 `346bc4bd480965fc14b5002bc73fd7635ce8a09d90c0694203faf8550bb1d187`. Tested on invented data only, including a deliberately broken engine file that it caught.
5. Neither side ran anything on the fixtures before the recorded run.

## 3. Gates before the comparison

| Gate | Result |
|---|---|
| Four frozen files against `FREEZE_SHA256SUMS` | all OK |
| Pin lane self-test on the box | `RESULT: OK`, 11 of 11 broken versions caught |
| Engine self-test on the box (first run on Python 3.10) | `SELFTEST PASS -- 25 mutants` |
| Fixture manifests | OK on all six |
| Run counts against the pre-registered table | 81/78/78, 81/78/78, 81/78/78, 81/77/77, 81/1/1, 81/1/1, as registered |

## 4. Results

| Part | What it tests | Result |
|---|---|---|
| V-2a | Under `merdian_compute`, only `gamma_v2.py` added against `934fe44`; `tests/golden` unchanged; the 313-row contract test | PASS (`CONTRACT ALL PASS`) |
| V-2b | Engine code against the independent implementation, 486 chain runs | PASS, 0 mismatches. Largest difference in per-strike net and gross: 0 |
| V-2c | Chain-built rows against stored-row-built rows, 313 runs, both implementations | PASS, 0 mismatches |
| **Overall** | | **PASS** |

## 5. Coverage, reported whatever the verdict

Over the 486 chain runs, 65,721 output rows (strikes with open interest):

| Count | Value |
|---|---:|
| Strikes with gamma on both legs | 20,227 |
| Call leg only | 17,424 |
| Put leg only | 6,803 |
| In the map, both legs removed by the guard | 282 |
| Not in the map (no vendor gamma on either leg) | 20,985 |
| One-leg strikes where the other leg's open interest now counts | 16,695 |
| Legs removed by the guard | 4,289 |
| In-map strikes with net exactly 0 | 363 |
| Legs with more than one row | 0 |
| Strikes exactly on the 5 % edge | 0 |
| Error runs | 0 |

**Branches never reached by the fixtures, covered by the two self-tests only:** duplicate leg rows, a strike exactly on the 5 % edge, error runs (more than one expiry, more than one spot).

**Fixture skew:** 3 of 6 days are expiry days; 233 of the 313 V-2c runs are on an expiry day; no fixture has dte 1, 2 or 3.

## 6. What this establishes

1. The engine's new code computes rule v1.1 exactly on these six days. The two implementations, written separately, give the same value at every strike of every run.
2. The old code is untouched: no V1 file changed, and the contract test that pins V1 outputs to production's stored values still passes.
3. On the 313 runs that have both, building from stored per-strike rows gives the same result as building from the raw chain. So on these days the stored leg gammas and open interest carry the same information as the chain for this rule. That bears on the open "precision provenance" item and supports a backfill from stored rows.

## 7. What it does not establish

- That the new figures are more accurate than the old.
- How much the new figures differ from the old on stored history. Not measured here.
- Agreement with the 60-day audit.
- Correct behaviour on duplicate leg rows, on a strike exactly at the edge, or on error runs, beyond the invented cases in the self-tests.
- Anything on days with dte 1 to 3 beyond what the rule's arithmetic implies.
- Anything about a flip, a regime label, dealer positioning or price behaviour.

## 8. Observations, not part of the verdict

- 16,695 of the 44,736 in-map strikes (37 %) are one-leg strikes where the leg without gamma holds open interest. These are the strikes where the old per-leg rule drops open interest and the new rule counts it. This is a count in the fixtures, not a measure of how far any Board figure moves.
- 20,985 of 65,721 rows (32 %) have open interest and no vendor gamma on either leg. Neither rule can give them an exposure.
- Call-only strikes outnumber put-only strikes about 2.6 to 1.
- Declared before the run and not exercised by it: the engine's code raises on a repeated strike or a bad spot in stored rows; the independent implementation does not. No fixture contains either.

## 9. Evidence

- Run log `run_2026-11-25.log`, sha256 `68a0638c2f5742a01714dd0861d273b8c1cbff85afb6776f4281188410359d30`, 30 lines. The copy committed with this result was rebuilt from the operator's paste and reproduces that hash exactly.
- Command 6 ran once. No file was edited, nothing was rerun.

## 10. Owed

- Git: this result and the log, in `docs/research/pin_proof/v2_check/` on `pin/v2-check`.
- ADR-033 section 6 to cite this result when the engine moves the ADR from draft to proposed.
- A second, separately pre-registered check: old against new on stored history, and reconciliation with the audit.
