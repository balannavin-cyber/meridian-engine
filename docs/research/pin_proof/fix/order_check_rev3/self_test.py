#!/usr/bin/env python3
"""Self-test and mutation controls for the rev-3 order check. Runs BEFORE any
live read (task condition 6). If any named mutant fails to make a clause FAIL,
this exits non-zero and the check is void.

The expected values below are HAND-COMPUTED from the fixture as exact rationals
and written as literals. They were NOT obtained by running measure() and reading
its output -- per CLAUDE.md Rule 0 clause 3, an expected value obtained by
running the thing is not an assertion.

  scale           = 1000^2/1e7 = 1/10
  K=1000  gamma_s = (4/10000 + 6/10000)/2 = 1/2000
          gross   = (1/2000)*200*(1/10)   = 1/100  = 0.01
  K=1010  gamma_s = 8/10000 = 1/1250   (call_only: no mean taken)
          gross   = (1/1250)*50*(1/10)    = 1/250  = 0.004
  K=980   gamma_s = 8/10000 = 1/1250   (put_only: no mean taken)
          gross   = (1/1250)*50*(1/10)    = 1/250  = 0.004   <- ties 1010
  K=1055  gamma_s = 20/10000 = 1/500
          gross   = (1/500)*1000*(1/10)   = 1/5    = 0.2
  lead_rel        = (1/100 - 1/250)/(1/100) = 3/5  = 0.6

The fixture tests the independent Python and the clause evaluator. It does NOT
test the view (PREREG "Stated limit").
"""
from __future__ import annotations

import sys
from fractions import Fraction

from clauses import compare
from indep import measure

SPOT = 1000.0
PAIR = ("NIFTY", "2026-11-26")

# ---------------------------------------------------------------- fixture ----
# 960  in-set, no gamma AND no OI       -> 'none', NOT in n_oi_no_gamma
# 980  put_only, dist 20, LOWER         -> ties 1010 at 0.004
# 1000 both, the clear rank 1           -> 0.01
# 1010 call_only, dist 10, HIGHER       -> ties 980 at 0.004
# 1030 OI > 0, no gamma                 -> 'none', IS in n_oi_no_gamma
# 1040 gamma > 0, ZERO OI on both legs   -> gross_cr = 0, NOT ranked
#      (added 2026-11-23 20:00 IST under the operator's ranking-condition
#       ruling, so that condition has a fixture case that exercises it)
# 1055 outside 5 % (0.055000000000000004), inside 6 % -> enters only under M3
LEGS = {
     960.0: {"c_gamma": 0.0,    "p_gamma": 0.0,    "c_oi":   0.0, "p_oi":   0.0},
     980.0: {"c_gamma": 0.0,    "p_gamma": 0.0008, "c_oi":  25.0, "p_oi":  25.0},
    1000.0: {"c_gamma": 0.0004, "p_gamma": 0.0006, "c_oi": 100.0, "p_oi": 100.0},
    1010.0: {"c_gamma": 0.0008, "p_gamma": 0.0,    "c_oi":  25.0, "p_oi":  25.0},
    1030.0: {"c_gamma": 0.0,    "p_gamma": 0.0,    "c_oi":  50.0, "p_oi":  50.0},
    1040.0: {"c_gamma": 0.0012, "p_gamma": 0.0012, "c_oi":   0.0, "p_oi":   0.0},
    1055.0: {"c_gamma": 0.0020, "p_gamma": 0.0020, "c_oi": 500.0, "p_oi": 500.0},
}

# ------------------------------------------- hand-stated expectations, 5 % ----
# In-set: 960, 980, 1000, 1010, 1030, 1040 (1055 is outside) -> 6
# Gamma present: 980, 1000, 1010, 1040. Of those, 1040 has oi_tot = 0 so
#   gross = 0.0012 * 0 * (1/10) = 0 and is NOT ranked -> n_ranked = 3
# n_oi_no_gamma: 1030 only (oi_tot 100 > 0). 960 has no OI; 1040 has gamma.
EXP_N_IN_SET        = 6
EXP_N_RANKED        = 3
EXP_N_OI_NO_GAMMA   = 1
EXP_N_CALL_ONLY     = 1
EXP_N_PUT_ONLY      = 1
EXP_N_GAMMA_ZERO_OI = 1
EXP_SEQUENCE        = [1000.0, 1010.0, 980.0]
EXP_LEAD_REL        = float(Fraction(3, 5))
EXP_LEGS_MAP        = {960.0: "none", 980.0: "put_only", 1000.0: "both",
                       1010.0: "call_only", 1030.0: "none", 1040.0: "both"}
EXP_GROSS           = {980.0:  float(Fraction(1, 250)),
                       1000.0: float(Fraction(1, 100)),
                       1010.0: float(Fraction(1, 250))}

# Expectations under each mutant, also hand-stated.
EXP_M1_SEQUENCE      = [1000.0, 980.0, 1010.0]
EXP_M2_N_OI_NO_GAMMA = 2
EXP_M3_N_IN_SET      = 7
EXP_M3_N_RANKED      = 4
EXP_M3_SEQUENCE      = [1055.0, 1000.0, 1010.0, 980.0]
EXP_M3_LEAD_REL      = float(Fraction(19, 20))

TOL = 1e-12
fails: list[str] = []
checks = 0


def ck(name: str, got, want, tol: float | None = None) -> None:
    global checks
    checks += 1
    if tol is None:
        ok = (got == want)
    elif got is None or want is None:
        ok = (got is want)
    else:
        d = max(abs(got), abs(want))
        ok = (got == want) if d == 0 else (abs(got - want) / d <= tol)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got!r} want {want!r}")
    if not ok:
        fails.append(name)


def view_from_hand() -> dict:
    """The 'view' side of the self-test, built from the HAND literals only.

    measure() is never consulted here. If it were, compare() would be checking
    measure() against itself and every clause would pass by construction.
    """
    return {PAIR: {"sequence": list(EXP_SEQUENCE),
                   "n_ranked": EXP_N_RANKED,
                   "n_in_set": EXP_N_IN_SET,
                   "n_oi_no_gamma": EXP_N_OI_NO_GAMMA,
                   "legs_map": dict(EXP_LEGS_MAP),
                   "lead_rel": EXP_LEAD_REL,
                   "gross": dict(EXP_GROSS)}}


def main() -> int:
    print("=" * 72)
    print("PART 1 - baseline: indep.measure() against the hand literals")
    print("=" * 72)
    m = measure(LEGS, SPOT)
    ck("n_in_set", m["n_in_set"], EXP_N_IN_SET)
    ck("n_ranked", m["n_ranked"], EXP_N_RANKED)
    ck("n_oi_no_gamma", m["n_oi_no_gamma"], EXP_N_OI_NO_GAMMA)
    ck("n_call_only", m["n_call_only"], EXP_N_CALL_ONLY)
    ck("n_put_only", m["n_put_only"], EXP_N_PUT_ONLY)
    ck("sequence", m["sequence"], EXP_SEQUENCE)
    ck("legs_map", m["legs_map"], EXP_LEGS_MAP)
    ck("lead_rel", m["lead_rel"], EXP_LEAD_REL, TOL)
    for K in sorted(EXP_GROSS):
        ck(f"gross[{K:.0f}]", m["gross"].get(K), EXP_GROSS[K], TOL)
    ck("1010 ties 980 bit-identically",
       m["gross"][1010.0] == m["gross"][980.0], True)
    # The ranking condition's own control. If the gross_cr > 0 filter were
    # dropped, 1040 would be ranked, n_ranked would read 4 and 1040 would
    # appear in gross -- so these three assertions ARE the control and no
    # fourth mutant is required.
    ck("n_gamma_zero_oi", m["n_gamma_zero_oi"], EXP_N_GAMMA_ZERO_OI)
    ck("1040 in-set and tagged both", m["legs_map"].get(1040.0), "both")
    ck("1040 NOT ranked (gross_cr = 0)", 1040.0 in m["gross"], False)
    ck("1055 excluded at 5 %", 1055.0 in m["legs_map"], False)
    ck("band arithmetic for 1055", abs(1055.0 / SPOT - 1.0) > 0.05, True)
    ck("1055 admitted at 6 %", abs(1055.0 / SPOT - 1.0) <= 0.06, True)

    print()
    print("=" * 72)
    print("PART 2 - clause evaluator on a clean pair: all four must PASS")
    print("=" * 72)
    base = compare(view_from_hand(), {PAIR: m})
    for c in ("clause1", "clause2", "clause3", "clause4"):
        ck(f"baseline {c}", base[c], True)
    ck("baseline overall", base["overall"], True)
    row = base["per_pair"][PAIR]
    print(f"    rows_compared={row['rows_compared']} "
          f"legs_rows_compared={row['legs_rows_compared']} "
          f"gross_rows_compared={row['gross_rows_compared']} "
          f"max_rel_gross_diff={row['max_rel_gross_diff']!r}")

    print()
    print("=" * 72)
    print("PART 3 - the three named mutation controls")
    print("  Each must make at least one clause FAIL, or the check is VOID.")
    print("=" * 72)
    mutants = [
        ("M1 swap the tie-break",
         dict(tiebreak="lower_then_nearer"),
         [("sequence", EXP_M1_SEQUENCE)]),
        ("M2 drop the OI filter in n_oi_no_gamma",
         dict(oi_filter=False),
         [("n_oi_no_gamma", EXP_M2_N_OI_NO_GAMMA)]),
        ("M3 widen the band to 6 %",
         dict(band=0.06),
         [("n_in_set", EXP_M3_N_IN_SET), ("n_ranked", EXP_M3_N_RANKED),
          ("sequence", EXP_M3_SEQUENCE)]),
    ]
    for label, knob, side_effects in mutants:
        print(f"\n-- {label}  knob={knob}")
        mm = measure(LEGS, SPOT, **knob)
        for field, want in side_effects:
            ck(f"{label}: mutated {field}", mm[field], want)
        if label.startswith("M3"):
            ck(f"{label}: mutated lead_rel", mm["lead_rel"],
               EXP_M3_LEAD_REL, TOL)
        r = compare(view_from_hand(), {PAIR: mm})
        broke = [c for c in ("clause1", "clause2", "clause3", "clause4")
                 if not r[c]]
        print(f"   clauses FAILED by this mutant: {broke or 'NONE'}")
        ck(f"{label}: at least one clause FAILS", bool(broke), True)
        ck(f"{label}: overall FAILS", r["overall"], False)

    print()
    print("=" * 72)
    print("PART 4 - additional control (NOT one of the three named mutants)")
    print("  Clause 4 is untouched by M1-M3, so it needs its own control.")
    print("=" * 72)
    r4 = compare(view_from_hand(), {})
    ck("dropped pair on INDEP side: clause4 FAILS", r4["clause4"], False)
    ck("dropped pair on INDEP side: overall FAILS", r4["overall"], False)
    r5 = compare({}, {PAIR: m})
    ck("dropped pair on VIEW side: clause4 FAILS", r5["clause4"], False)

    print()
    print("=" * 72)
    if fails:
        print(f"SELF-TEST FAILED: {len(fails)} of {checks} checks failed")
        for f in fails:
            print(f"  - {f}")
        print("CHECK IS VOID - do not proceed to any live read.")
        return 1
    print(f"SELF-TEST ALL PASS: {checks}/{checks} checks")
    print("All three named mutants made at least one clause FAIL.")
    print("Clauses 1, 2, 3 shown failable by M1/M2/M3; clause 4 by PART 4.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
