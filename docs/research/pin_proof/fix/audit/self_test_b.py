#!/usr/bin/env python3
'''POST-HOC self-test for the B1 / B2 constructions in audit.measure_run.

No measure arithmetic in this file: it builds the planted inputs and calls the same
measure_run that audit_run calls. The hand answers below are the ones stated in the
task BEFORE the code was run; if the code disagrees the test stops and shows both,
and the hand answers are NOT changed.

THE PLANTED RUN -- the six strikes of self_test.py, with the missing/zero pattern the
task names: 25000 put MISSING, 25050 call PRESENT ZERO, 25150 call MISSING.
S = 25000, step 50, gK = 0.0010 everywhere.

  K      OIc    OIp    gc              gp
  24900  1000   2000   0.0020          0.0010
  24950  1000   1000   0.0010          0.0010
  25000  2000   1000   0.0010          MISSING
  25050  1000   3000   PRESENT ZERO    0.0020
  25100  1000   2000   0.0010          0.0010
  25150  3000   1000   MISSING         0.0010

B1 -- missing filled only; a PRESENT ZERO stays 0:
  24900 nothing missing            -> 0.0020*1000 - 0.0010*2000 =  0 ; gross 4
  24950 nothing missing            -> 1.0 - 1.0                 =  0 ; gross 2
  25000 gp missing -> gp' = 0.0010 -> 2.0 - 1.0                 =  1 ; gross 3
  25050 gc present ZERO, stays 0   -> 0   - 6.0                 = -6 ; gross 6
  25100 nothing missing            -> 1.0 - 2.0                 = -1 ; gross 3
  25150 gc missing -> gc' = 0.0010 -> 3.0 - 1.0                 =  2 ; gross 4
  net = 0, 0, 1, -6, -1, 2 ; sum net = -4 ; sum gross = 22
  net_R = -1, 0, 1, -2, -1, 2 ; GR = 19
  E_raw(B1) = (|0+1| + 0 + |1-1| + |-6+2| + |-1+1| + |2-2|) / 19 = 5/19

B2 -- missing OR zero filled:
  24900 both > 0                   ->  0 ; gross 4
  24950 both > 0                   ->  0 ; gross 2
  25000 gp = 0 -> gp' = 0.0010     ->  2.0 - 1.0  =  1 ; gross 3
  25050 gc = 0 -> gc' = 0.0020     ->  2.0 - 6.0  = -4 ; gross 8
  25100 both > 0                   -> -1 ; gross 3
  25150 gc = 0 -> gc' = 0.0010     ->  3.0 - 1.0  =  2 ; gross 4
  net = 0, 0, 1, -4, -1, 2 ; sum net = -2 ; sum gross = 24
  E_raw(B2) = (1 + 0 + 0 + |-4+2| + 0 + 0) / 19 = 3/19
'''
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from audit import measure_run  # noqa: E402

S, STEP_, GK = 25000.0, 50.0, 0.0010
PLANT = {
    24900.0: dict(gc=0.0020, gp=0.0010, oic=1000.0, oip=2000.0, gk=GK, fallback=False,
                  gc_missing=False, gp_missing=False),
    24950.0: dict(gc=0.0010, gp=0.0010, oic=1000.0, oip=1000.0, gk=GK, fallback=False,
                  gc_missing=False, gp_missing=False),
    25000.0: dict(gc=0.0010, gp=0.0,    oic=2000.0, oip=1000.0, gk=GK, fallback=False,
                  gc_missing=False, gp_missing=True),    # put MISSING
    25050.0: dict(gc=0.0,    gp=0.0020, oic=1000.0, oip=3000.0, gk=GK, fallback=False,
                  gc_missing=False, gp_missing=False),   # call PRESENT ZERO
    25100.0: dict(gc=0.0010, gp=0.0010, oic=1000.0, oip=2000.0, gk=GK, fallback=False,
                  gc_missing=False, gp_missing=False),
    25150.0: dict(gc=0.0,    gp=0.0010, oic=3000.0, oip=1000.0, gk=GK, fallback=True,
                  gc_missing=True,  gp_missing=False),   # call MISSING
}

WANT_B1_NET = [0.0, 0.0, 1.0, -6.0, -1.0, 2.0]
WANT_B2_NET = [0.0, 0.0, 1.0, -4.0, -1.0, 2.0]
TOL = 1e-12
lines, ok = [], True


def chk(name, got, want, tol=TOL):
    global ok
    good = (got == want) if isinstance(want, (bool, str)) else abs(got - want) <= tol
    ok = ok and good
    lines.append(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r}, want {want!r}")


m = measure_run(PLANT, S, STEP_)
per, A = m["per"], m["ALL"]
ks = sorted(per)
lines.append("POST-HOC B1/B2 self-test -- hand answers fixed before the run")
lines.append("-" * 74)
for K, w in zip(ks, WANT_B1_NET):
    chk(f"B1 net {K:.0f}", per[K]["net_B1"], w)
lines.append("")
for K, w in zip(ks, WANT_B2_NET):
    chk(f"B2 net {K:.0f}", per[K]["net_B2"], w)
lines.append("")
chk("B1 sum net", A["NB1"], -4.0)
chk("B1 sum gross", A["GB1"], 22.0)
chk("B2 sum net", A["NB2"], -2.0)
chk("B2 sum gross", A["GB2"], 24.0)
chk("B1 E_raw", A["E_raw_B1"], 5.0 / 19.0)
chk("B2 E_raw", A["E_raw_B2"], 3.0 / 19.0)
lines.append("")
# control: with NO missing flags at all, B1 must equal P exactly -- the real-data case
noflag = {k: {kk: vv for kk, vv in v.items()
              if kk not in ("gc_missing", "gp_missing")} for k, v in PLANT.items()}
m2 = measure_run(noflag, S, STEP_)
same = all(abs(m2["per"][k]["net_B1"] - m2["per"][k]["net_P"]) <= TOL for k in ks)
chk("control: no missing flags -> B1 == P on every strike", same, True)
chk("control: no missing flags -> E_raw(B1) == E_raw(P)",
    abs(m2["ALL"]["E_raw_B1"] - m2["ALL"]["E_raw_P"]) <= TOL, True)
lines.append("")
lines.append("-" * 74)
lines.append(f"B1/B2 SELF-TEST {'ALL PASS' if ok else 'FAILED'} "
             f"({sum(1 for x in lines if x.startswith('PASS'))} pass, "
             f"{sum(1 for x in lines if x.startswith('FAIL'))} fail)")
print("\n".join(lines))
raise SystemExit(0 if ok else 3)
