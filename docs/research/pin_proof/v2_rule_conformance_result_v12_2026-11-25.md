# V2 rule conformance check, rule v1.2: result

**Verdict: PASS.** Run Wed 2026-11-25, about 18:55 IST, once, in the pin lane's workspace, on the operator's word ("I agree. Lets go", 18:50 IST).
**Addendum:** `claude/pin/v2_rule_conformance_addendum_v12_FROZEN_2026-11-25.md`, sha256 `90f491e1ef4d3bc0b7a4576c709862125575f9f803ce2807c08a36ef57881bd2`. **Parent result (v1.1):** `claude/pin/v2_rule_conformance_result_2026-11-25.md`.
**Authorises nothing.**

## What was tested

- Engine `merdian_compute/gamma_v2.py` at `a9b38bcbead78b855ae23a0f83902b1ad9b728af` (branch `pin/v2-check`), sha256 `e71f4d73a2d71b9dbdf352e65a4db1f597c48d4cd9411f775c49fa073bb7617d`.
- Against the pin lane's v1.2 implementation: `v2_indep.py` `27acea7164c6032f10d790b991ebf26219ead6c027461226cde64e745c95ae16`; self-test `0aa88ef6a441e54a79c89ffc5abb77781326272f0395d9c8288388b29b23b921`; harness `08db6bf88f3730f09a634c7f39d7c5c588694ba31aa08d286bda0aa5ecbca5b2`.
- Fresh clone of the public repository at that commit. Python 3.10.20 (the box runs 3.10.12).

## Gates

| Gate | Result |
|---|---|
| Frozen files against `FREEZE_SHA256SUMS` | all OK |
| Pin lane self-test on 3.10 | `RESULT: OK`, 13 of 13 broken versions caught |
| Engine self-test on 3.10 | `SELFTEST PASS -- 26 mutants` |
| Six fixture manifests; run counts | OK; as registered |

## Results

| Part | Result |
|---|---|
| V-2a: only `gamma_v2.py` added under `merdian_compute` against `934fe44`; `tests/golden` unchanged; contract test | PASS (`CONTRACT ALL PASS`) |
| V-2b: engine against independent, 486 chain runs | PASS, 0 mismatches, largest difference 0 |
| V-2c: chain build against stored-row build, 313 runs, both implementations | PASS, 0 mismatches |
| **Overall** | **PASS** |

Coverage counts are identical to the v1.1 run, as expected with unchanged arithmetic: 65,721 rows; both 20,227; call_only 17,424; put_only 6,803; in map with both legs guarded 282; not in map 20,985; other leg's OI now counts 16,695; legs removed by the guard 4,289; in-map net exactly 0: 363; duplicate legs 0; edge strikes 0; error runs 0.

## What it establishes and what it does not

- The v1.2 code computes the same arithmetic as the rule on the same 486 and 313 runs, and the old code is untouched.
- It establishes nothing about the two new error cases (repeated strike, bad spot in stored rows) on real data: the fixtures contain no such rows. Those rest on the two self-tests.
- Independence limit as stated in the addendum: the pin lane had read the engine's v1.1 code, which already held both checks, before writing its own.
- Everything in the parent result's section 7 still applies.

## Evidence

Log `run_v12_2026-11-25.log`, sha256 `1fcf1ee519d090e0281653683d497f160408478b5c73d2ec1fbf70b4dee41e64`. One command, run once:
`python3.10 -B compare_v2.py --repo <clone at a9b38bc> --engine-commit a9b38bcbead78b855ae23a0f83902b1ad9b728af`
Repeatable by anyone from the public repository and the frozen files. A box rerun is the same command.

## Owed

Git copies of the five v1.2 files, this result and the log, in `docs/research/pin_proof/v2_check_v12/`, at the next commit from the pin lane.
