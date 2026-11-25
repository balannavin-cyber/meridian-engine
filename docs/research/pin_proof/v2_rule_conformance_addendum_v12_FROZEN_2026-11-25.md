# V2 rule conformance check: addendum for rule v1.2

**Status:** FROZEN, Wed 2026-11-25, about 18:40 IST. **Not yet run.** The comparison is run only on the operator's word.
**Parent:** `claude/pin/v2_rule_conformance_prereg_FROZEN_2026-11-25.md`, sha256 `b1a156a8722da1700d22f4fbaf1a27dc116bdf3841075bf85e5cedd34ad7361d`. Everything in the parent stands except what this addendum changes.
**Lane:** pin (MR-PIN3). **Authorises:** one rerun of the comparison on saved fixture data. Nothing in production.

## 1. Why

The V-2 check passed for rule v1.1 at engine commit `a9982c7`. The engine's code refuses two kinds of bad stored row that rule v1.1 did not mention. The backfill reads stored rows, so the rule now states them. The operator approved making this rule v1.2 with one rerun (25 Nov).

## 2. What changed in the rule (v1.1 to v1.2)

Text taken from ADR-033 section 3 at commit `a9b38bcbead78b855ae23a0f83902b1ad9b728af`:

> **Input errors, no V2 output.** (a) From chain rows: more than one expiry in the run. (b) From chain rows: more than one distinct positive spot in the run. (c) From stored rows: more than one expiry in the run's rows. (d) From stored rows: a strike that appears more than once in the run's rows. (e) From stored rows: a row with a missing or non-positive spot. (d) and (e) are new in v1.2; (a) to (c) restate v1.1.

> **Stored** … Live rows carry `rule_version` `v2-1.2`; rows backfilled from stored rows carry `v2-1.2-gss`.

Steps 1 to 10 are word for word as in v1.1. No arithmetic changed. The pin lane accepts (c): its v1.1 implementation already treated it as an error.

## 3. What is under test

- Engine code `merdian_compute/gamma_v2.py` at `a9b38bcbead78b855ae23a0f83902b1ad9b728af`, on branch `pin/v2-check` (the engine's package was committed there by mistake; it is not on `engine/v2-gamma`). The file's sha256 is recorded in the result before the comparison.
- Against the pin lane's implementation updated to v1.2.

## 4. The independent implementation, v1.2

- `v2_indep.py` sha256 `27acea7164c6032f10d790b991ebf26219ead6c027461226cde64e745c95ae16`.
- `selftest_v2_indep.py` sha256 `0aa88ef6a441e54a79c89ffc5abb77781326272f0395d9c8288388b29b23b921`. Passes; 13 of 13 broken versions caught (the 11 from v1.1 plus M12 "repeated strike not an error" and M13 "bad stored spot not an error").
- Changed from the v1.1 implementation only in the stored-row build: it now raises on (d) and (e).
- Written from the v1.2 rule text. Frozen before the pin lane opened the engine's v1.2 code or self-test.

**Limit on independence, stated plainly.** The pin lane read the engine's v1.1 code after the v1.1 freeze, and that code already contained both checks. So for (d) and (e) the pin lane knew how the engine does it before writing its own. The arithmetic, which is everything the v1.1 result established, was written blind.

**Two readings where the v1.2 text is silent:**
- I7: any stored row of the run with a missing or non-positive spot makes the run an error, whatever its strike or open interest.
- I8: "the same strike" is judged on the decimal value; rows with a missing strike or a strike ≤ 0 are not counted as repeats.

A different reading in the engine's code can only show on malformed stored rows. The v1.1 run found none in the fixtures.

## 5. Harness

`compare_v2.py` sha256 recorded in `FREEZE_SHA256SUMS`. It differs from the v1.1 harness (`346bc4bd…b1d187`) only in the two frozen hashes and the banner line. Tested on invented data only.

## 6. Comparison, tolerances and verdict

As the parent's sections 7 and 8, unchanged: V-2a (only `gamma_v2.py` added under `merdian_compute` against `934fe44`, `tests/golden` unchanged, contract test passes), V-2b on 486 chain runs, V-2c on 313 runs. PASS only if all three hold with no exception.

Gates before the comparison: the frozen hashes; the pin lane's self-test; the engine's self-test on Python 3.10, which must end `SELFTEST PASS -- 26 mutants`. If a gate fails, the comparison is not run.

## 7. Conduct: one change from the parent

The parent set the recorded run on the box. For this rerun the recorded run is in the pin lane's own workspace:

- from a fresh clone of the public repository at the commit above,
- on Python 3.10 (3.10.20 here; the box runs 3.10.12),
- one command, once, output saved as the log and hashed,
- no database, no production tree, no secret.

Reason: every input is public and fixed by hash, so anyone can repeat it with one command, and it removes two errands from the operator (a commit from Windows and a run on the box). The operator can ask for a box rerun at any time; it is the same command.

One look. Neither side edits its implementation after the comparison is seen, except under a new version and a new freeze.

## 8. What a pass will and will not establish

A pass extends the v1.1 result to the v1.2 code: same arithmetic on the same 486 and 313 runs, old code untouched. It establishes nothing about (d) and (e) on real data, because the fixtures contain no such rows; those rest on the two self-tests. Everything in the parent's section 11 still applies.
