#!/usr/bin/env python3
'''Self-test for audit.measure_run on a hand-made run of SIX strikes.

No measure arithmetic lives in this file. It builds the planted per-strike inputs,
calls audit.measure_run -- the same function audit_run calls -- and compares the
returned record with answers computed BY HAND below. A bug inside measure_run must
therefore make this fail; that is the point.

THE PLANTED RUN.  S = 25000, step 50, gK = 0.0010 at every strike.

  K      OIc    OIp    gc       gp       fallback  note
  24900  1000   2000   0.0020   0.0010   False     both present, gc != gp
  24950  1000   1000   0.0010   0.0010   False     OIc == OIp  (N1 excludes it)
  25000  2000   1000   0.0010   blank    False     BLANK PUT gamma
  25050  1000   3000   blank    0.0020   False     BLANK CALL gamma
  25100  1000   2000   0.0010   0.0010   False     both present, gc == gp
  25150  3000   1000   blank    0.0010   True      BLANK CALL; wanted sign +,
                                                   production sign -  (N1 wrong-sign)
  25150 is also the one fallback strike, so ALL and NOFB differ.

gVS (mean when both > 0; the positive one when only one is; else 0)
  24900 (0.0020+0.0010)/2 = 0.0015 | 24950 0.0010 | 25000 0.0010 (put blank)
  25050 0.0020 (call blank)        | 25100 0.0010 | 25150 0.0010 (call blank)

net_P = gc*OIc - gp*OIp ; gross_P = gc*OIc + gp*OIp
  24900 2.0-2.0 =  0.0 ; 4.0      25050 0-6.0 = -6.0 ; 6.0
  24950 1.0-1.0 =  0.0 ; 2.0      25100 1.0-2.0 = -1.0 ; 3.0
  25000 2.0-0   =  2.0 ; 2.0      25150 0-1.0 = -1.0 ; 1.0
  sum net_P = 0+0+2-6-1-1 = -6.0 ; GP = 4+2+2+6+3+1 = 18.0

net_N = gVS*(OIc-OIp) ; gross_N = gVS*(OIc+OIp)
  24900 0.0015*(-1000) = -1.5 ; 4.5     25050 0.0020*(-2000) = -4.0 ; 8.0
  24950 0.0010*0       =  0.0 ; 2.0     25100 0.0010*(-1000) = -1.0 ; 3.0
  25000 0.0010*1000    =  1.0 ; 3.0     25150 0.0010*(2000)  =  2.0 ; 4.0
  sum net_N = -1.5+0+1-4-1+2 = -3.5 ; GN = 4.5+2+3+8+3+4 = 24.5

net_R = 0.0010*(OIc-OIp) ; gross_R = 0.0010*(OIc+OIp)
  -1.0, 0.0, 1.0, -2.0, -1.0, 2.0   ; 3.0, 2.0, 3.0, 4.0, 3.0, 4.0
  sum net_R = -1.0 ; GR = 19.0

N1 (OIc != OIp -> 24950 excluded, n = 5: 24900, 25000, 25050, 25100, 25150)
  want sign(OIc-OIp):  -1 , +1 , -1 , -1 , +1
  got  sign(net_P)  :   0 , +1 , -1 , -1 , -1
  24900 -> ZERO (net_P == 0 while OIc != OIp), cause both gammas present
  25150 -> WRONG SIGN, cause blank leg
  zero = 1, wrong = 1, cause_both = 1, cause_blank = 1
  w_gross   = 3+3+4+3+4 = 17.0 ; zero_gross = 3.0 ; wrong_gross = 4.0

E_raw(X) = sum|net_X - net_R| / GR            (GR = 19)
  P: 1+0+1+4+0+3 = 9.0  -> 9/19  = 0.473684210526315789
  N: 0.5+0+0+2+0+0 = 2.5 -> 2.5/19 = 0.131578947368421053

E_shape(X) = sum|net_X/GX - net_R/GR|
  P (GP=18): |0+1/19| = .052631578947368
             |0-0| = 0
             |2/18-1/19| = .058479532163743
             |-6/18+2/19| = .228070175438596
             |-1/18+1/19| = .002923976608187
             |-1/18-2/19| = .160818713450292
             sum E_shape_P = 0.502923976608187
  N (GN=24.5): |-1.5/24.5+1/19| = .008592910848550
             0
             |1/24.5-1/19| = .011815252416756
             |-4/24.5+2/19| = .058002148227712
             |-1/24.5+1/19| = .011815252416756
             |2/24.5-2/19| = .023630504833512
             sum E_shape_N = 0.113856068743287

T_X = sum net_X / GX
  T_P = -6.0/18.0 = -0.333333333333333
  T_N = -3.5/24.5 = -0.142857142857143
  T_R = -1.0/19.0 = -0.052631578947368
  |T_P-T_R| = 0.280701754385965 ; |T_N-T_R| = 0.090225563909774
  no sign flip (all negative) ; |T_R| = 0.0526... >= 0.05 -> T_R_big True

L1(X) = sum|gross_X/GX - gross_R/GR|
  P: .064327485380117 + .005847953216374 + .046783625730994
     + .122807017543860 + .008771929824561 + .154970760233918 = 0.403508771929825
  N: .025778732545650 + .023630504833512 + .035445757250269
     + .116004296455424 + .035445757250269 + .047261009667025 = 0.283566058002148

N5 peaks (tie: higher value, then nearer spot, then lower strike)
  largest POSITIVE net: P -> 25000 (only +2.0) ; N -> 25150 (+2.0) ; R -> 25150 (+2.0)
    same_P_pos False, gap |25000-25150|/50 = 3.0 ; same_N_pos True, gap 0.0
  largest |net|: P -> 25050 (6.0) ; N -> 25050 (4.0) ; R -> tie 2.0 at 25050 and 25150,
    25050 is nearer spot so R_abs = 25050 ; same_P_abs True, same_N_abs True, gaps 0.0
  lead_R_pos: positives [2.0, 1.0] -> (2-1)/2 = 0.5
  lead_R_abs: |net_R| sorted [2,2,1,1,1,0] -> (2-2)/2 = 0.0

K1: 6 strikes, 1 fallback (25150) -> share_strikes = 1/6 = 0.166666666666667
    share_GR = 4.0/19.0 = 0.210526315789474

NOFB subset (25150 dropped -> 5 strikes): GR 15.0, GP 17.0, GN 20.5,
  sum net_P -5.0, sum net_N -5.5, sum net_R -3.0
  E_raw_P = 6/15 = 0.4 ; E_raw_N = 2.5/15 = 0.166666666666667
  E_shape_P: terms 1/15 + 0 + 13/255 + 56/255 + 2/255 = 88/255 = 0.345098039215686
             (an earlier draft of this docstring summed these five terms to
              0.345196078431373, which is a transposition error in MY addition; the
              exact rational sum is 88/255. Re-derived with fractions.Fraction. The
              code was not changed.)
  E_shape_N = 0.104065040650407
  T_P = -5/17 = -0.294117647058824 ; T_N = -5.5/20.5 = -0.268292682926829 ; T_R = -0.2
  L1_P = 0.243137254901961 ; L1_N = 0.286178861788618
'''
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit  # noqa: E402
from audit import measure_run  # noqa: E402

S, STEP_ = 25000.0, 50.0
GK = 0.0010
PLANT = {
    24900.0: dict(gc=0.0020, gp=0.0010, oic=1000.0, oip=2000.0, gk=GK, fallback=False),
    24950.0: dict(gc=0.0010, gp=0.0010, oic=1000.0, oip=1000.0, gk=GK, fallback=False),
    25000.0: dict(gc=0.0010, gp=0.0,    oic=2000.0, oip=1000.0, gk=GK, fallback=False),
    25050.0: dict(gc=0.0,    gp=0.0020, oic=1000.0, oip=3000.0, gk=GK, fallback=False),
    25100.0: dict(gc=0.0010, gp=0.0010, oic=1000.0, oip=2000.0, gk=GK, fallback=False),
    25150.0: dict(gc=0.0,    gp=0.0010, oic=3000.0, oip=1000.0, gk=GK, fallback=True),
}

TOL = 1e-12
lines, ok = [], True


def chk(name, got, want, tol=TOL):
    global ok
    if want is None or isinstance(want, bool) or isinstance(got, bool) \
            or got is None or isinstance(want, str):
        good = (got == want)
    else:
        good = abs(got - want) <= tol
    ok = ok and good
    lines.append(f"{'PASS' if good else 'FAIL'}  {name}: got {got!r}, want {want!r}")


m = measure_run(PLANT, S, STEP_)
per, n1, A, NB, n5, k1 = m["per"], m["N1"], m["ALL"], m["NOFB"], m["N5"], m["K1"]

lines.append("audit.measure_run self-test -- 6 planted strikes, hand answers in the docstring")
lines.append("-" * 78)
for K, w in ((24900.0, 0.0015), (24950.0, 0.0010), (25000.0, 0.0010),
             (25050.0, 0.0020), (25100.0, 0.0010), (25150.0, 0.0010)):
    chk(f"gVS {K:.0f}", per[K]["gvs"], w)
lines.append("")
for K, wn, wg in ((24900.0, 0.0, 4.0), (24950.0, 0.0, 2.0), (25000.0, 2.0, 2.0),
                  (25050.0, -6.0, 6.0), (25100.0, -1.0, 3.0), (25150.0, -1.0, 1.0)):
    chk(f"net_P {K:.0f}", per[K]["net_P"], wn)
    chk(f"gross_P {K:.0f}", per[K]["gross_P"], wg)
lines.append("")
for K, wn, wg in ((24900.0, -1.5, 4.5), (24950.0, 0.0, 2.0), (25000.0, 1.0, 3.0),
                  (25050.0, -4.0, 8.0), (25100.0, -1.0, 3.0), (25150.0, 2.0, 4.0)):
    chk(f"net_N {K:.0f}", per[K]["net_N"], wn)
    chk(f"gross_N {K:.0f}", per[K]["gross_N"], wg)
lines.append("")
chk("GR", A["GR"], 19.0)
chk("GP", A["GP"], 18.0)
chk("GN", A["GN"], 24.5)
chk("sum net_P", A["NP"], -6.0)
chk("sum net_N", A["NN"], -3.5)
chk("sum net_R", A["NR"], -1.0)
lines.append("")
chk("N1 n", n1["n"], 5)
chk("N1 wrong", n1["wrong"], 1)
chk("N1 zero", n1["zero"], 1)
chk("N1 wrong_gross", n1["wrong_gross"], 4.0)
chk("N1 zero_gross", n1["zero_gross"], 3.0)
chk("N1 w_gross", n1["w_gross"], 17.0)
chk("N1 cause_both", n1["cause_both"], 1)
chk("N1 cause_blank", n1["cause_blank"], 1)
lines.append("")
chk("E_raw_P  (all)", A["E_raw_P"], 9.0 / 19.0)
chk("E_raw_N  (all)", A["E_raw_N"], 2.5 / 19.0)
chk("E_shape_P (all)", A["E_shape_P"], 0.5029239766081871, 1e-12)
chk("E_shape_N (all)", A["E_shape_N"], 0.1138560687432868, 1e-12)
chk("T_P (all)", A["T_P"], -6.0 / 18.0)
chk("T_N (all)", A["T_N"], -3.5 / 24.5)
chk("T_R (all)", A["T_R"], -1.0 / 19.0)
chk("T_err_P (all)", A["T_err_P"], abs(-6.0 / 18.0 + 1.0 / 19.0))
chk("T_err_N (all)", A["T_err_N"], abs(-3.5 / 24.5 + 1.0 / 19.0))
chk("T_signflip_P", A["T_signflip_P"], False)
chk("T_signflip_N", A["T_signflip_N"], False)
chk("T_R_big", A["T_R_big"], True)
chk("L1_P (all)", A["L1_P"], 0.4035087719298245, 1e-12)
chk("L1_N (all)", A["L1_N"], 0.2835660580021483, 1e-12)
lines.append("")
chk("NOFB n", NB["n"], 5)
chk("NOFB GR", NB["GR"], 15.0)
chk("NOFB E_raw_P", NB["E_raw_P"], 0.4)
chk("NOFB E_raw_N", NB["E_raw_N"], 2.5 / 15.0)
chk("NOFB E_shape_P", NB["E_shape_P"], 88.0 / 255.0, 1e-12)
chk("NOFB E_shape_N", NB["E_shape_N"], 0.1040650406504065, 1e-12)
chk("NOFB T_P", NB["T_P"], -5.0 / 17.0)
chk("NOFB T_N", NB["T_N"], -5.5 / 20.5)
chk("NOFB T_R", NB["T_R"], -0.2)
chk("NOFB L1_P", NB["L1_P"], 0.2431372549019608, 1e-12)
chk("NOFB L1_N", NB["L1_N"], 0.2861788617886179, 1e-12)
lines.append("")
chk("N5 R_pos", n5["R_pos"], 25150.0)
chk("N5 P_pos", n5["P_pos"], 25000.0)
chk("N5 N_pos", n5["N_pos"], 25150.0)
chk("N5 same_P_pos", n5["same_P_pos"], False)
chk("N5 gap_P_pos", n5["gap_P_pos"], 3.0)
chk("N5 same_N_pos", n5["same_N_pos"], True)
chk("N5 R_abs (tie -> nearer spot)", n5["R_abs"], 25050.0)
chk("N5 P_abs", n5["P_abs"], 25050.0)
chk("N5 N_abs", n5["N_abs"], 25050.0)
chk("N5 lead_R_pos", n5["lead_R_pos"], 0.5)
chk("N5 lead_R_abs", n5["lead_R_abs"], 0.0)
lines.append("")
chk("K1 n_strikes", k1["n_strikes"], 6)
chk("K1 n_fallback", k1["n_fallback"], 1)
chk("K1 share_strikes", k1["share_strikes"], 1.0 / 6.0)
chk("K1 share_GR", k1["share_GR"], 4.0 / 19.0)
lines.append("")

# ---- MUTATION CHECK -------------------------------------------------------
# Replace audit._net_P with a version that ADDS the put term instead of subtracting,
# re-run the SAME measure_run, and require the hand answers to stop matching. If they
# still matched, these assertions would not be testing production's sign at all.
lines.append("MUTATION CHECK -- audit._net_P with the put term ADDED instead of subtracted")
_orig = audit._net_P


def _mutant(gc, gp, oic, oip):
    c = gc * oic if (gc > 0 and oic > 0) else 0.0
    p = gp * oip if (gp > 0 and oip > 0) else 0.0
    return c + p                      # BUG on purpose


audit._net_P = _mutant
mm = measure_run(PLANT, S, STEP_)
audit._net_P = _orig

mut_fail = []
if abs(mm["per"][24900.0]["net_P"] - 0.0) > TOL:
    mut_fail.append(f"net_P 24900 {mm['per'][24900.0]['net_P']} != 0.0")
if abs(mm["ALL"]["NP"] - (-6.0)) > TOL:
    mut_fail.append(f"sum net_P {mm['ALL']['NP']} != -6.0")
if abs(mm["ALL"]["T_P"] - (-6.0 / 18.0)) > TOL:
    mut_fail.append(f"T_P {mm['ALL']['T_P']} != {-6.0/18.0}")
if mm["N1"]["wrong"] != 1 or mm["N1"]["zero"] != 1:
    mut_fail.append(f"N1 wrong/zero {mm['N1']['wrong']}/{mm['N1']['zero']} != 1/1")

if mut_fail:
    lines.append(f"PASS  mutation is DETECTED -- {len(mut_fail)} hand answer(s) now differ:")
    for x in mut_fail:
        lines.append(f"        {x}")
else:
    ok = False
    lines.append("FAIL  mutation NOT detected -- the assertions do not test net_P's sign")
lines.append("")
lines.append("-" * 78)
lines.append(f"SELF-TEST {'ALL PASS' if ok else 'FAILED'} "
             f"({sum(1 for x in lines if x.startswith('PASS'))} pass, "
             f"{sum(1 for x in lines if x.startswith('FAIL'))} fail)")
print("\n".join(lines))
raise SystemExit(0 if ok else 3)
