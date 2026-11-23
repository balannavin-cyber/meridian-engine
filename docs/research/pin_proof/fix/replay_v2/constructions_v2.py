#!/usr/bin/env python3
"""Pin live replay v2 -- the two NEW constructions, VS and FV, plus their self-tests.

Read-only. No database, no vendor call. Writes nothing.

V2, F, K and the tie order are NOT reimplemented here: V2 comes from
fix/replay/score_replay.py and F/K from lookback_v5/analyze_v5.py's compute_run, both
imported unchanged. Only VS and FV are new.

VS -- one vendor gamma per strike * (oi_call + oi_put). The gamma is:
        the MEAN of the two legs when BOTH are > 0,
        the non-zero one when one is blank or zero,
        zero when both are blank or zero.
      (This is what makes VS differ from V2: V2 weights each leg by its OWN OI, VS
      applies one gamma to the COMBINED OI.)

FV -- phi(d1) * (oi_call + oi_put), with
        sigma = atm_iv_avg / 100
        T     = minutes from the run's IST ts to 15:30 IST on the expiry date / 525600
        d1    = ln(S/K)/(sigma*sqrt(T)) + sigma*sqrt(T)/2
        phi   = standard normal density
      No vendor per-leg gamma is used at all. A run with no atm_iv_avg, or T <= 0,
      gets NO FV pin and is counted -- never a silent zero.
      NOTE the d1 here is the design's, written exactly as given; it is the
      Black-76-style d1 with the +sigma*sqrt(T)/2 term, not analyze_v5's
      (ln(S/K) + sigma^2 T/2)/(sigma sqrt(T)). The two are algebraically the same
      expression; it is transcribed in the design's form so the code reads as ruled.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "replay"))
sys.path.insert(0, str(HERE.parent.parent / "lookback_v5"))

from score_replay import _g, v2_scores            # noqa: E402  V2, unchanged
from analyze_v5 import pick                        # noqa: E402  the tie order

MIN_PER_YEAR = 525600.0


def vs_scores(rows: dict) -> dict:
    """VS: one vendor gamma per strike (mean of both legs when both > 0)."""
    out = {}
    for K, r in rows.items():
        gc, gp = _g(r["c_gamma"]), _g(r["p_gamma"])
        if gc > 0 and gp > 0:
            g = 0.5 * (gc + gp)
        elif gc > 0:
            g = gc
        elif gp > 0:
            g = gp
        else:
            g = 0.0
        out[K] = g * (r["c_oi"] + r["p_oi"])
    return out


def npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def fv_scores(rows: dict, S: float, atm_iv_avg, t_min):
    """FV: phi(d1) * (oi_call + oi_put). -> (scores, status).

    status 'OK', or 'NO_ATM_IV' / 'T_NONPOSITIVE' / 'BAD_SIGMA' with scores {} so the
    caller must count the run rather than read a pin off an empty dict.
    """
    if atm_iv_avg is None:
        return {}, "NO_ATM_IV"
    if t_min is None or t_min <= 0:
        return {}, "T_NONPOSITIVE"
    sigma = float(atm_iv_avg) / 100.0
    if sigma <= 0 or S <= 0:
        return {}, "BAD_SIGMA"
    T = t_min / MIN_PER_YEAR
    v = sigma * math.sqrt(T)
    out = {}
    for K, r in rows.items():
        if K <= 0:
            continue
        d1 = math.log(S / K) / v + v / 2.0
        out[K] = npdf(d1) * (r["c_oi"] + r["p_oi"])
    return out, "OK"


# ------------------------------------------------------------------ self-tests
def self_tests() -> tuple[bool, str]:
    L, ok = [], True

    def chk(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        L.append(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))

    L.append("replay_v2 -- VS and FV planted-chain self-tests")
    L.append("-" * 70)

    # ---- VS vs V2 must differ. 25100 has gamma_call = 0, so V2 keeps only the put
    # leg's own OI while VS applies the surviving put gamma to the COMBINED OI.
    S = 25000.0
    rows = {
        25000.0: {"c_gamma": "0.001", "p_gamma": "0.001", "c_oi": 1500.0, "p_oi": 1500.0},
        25100.0: {"c_gamma": "0",     "p_gamma": "0.002", "c_oi": 1000.0, "p_oi": 1000.0},
    }
    s2, sv = v2_scores(rows), vs_scores(rows)
    p2, _, _ = pick(s2, S)
    pv, _, _ = pick(sv, S)
    chk("VS1 V2 at 25100 = 2.0 (put leg's own OI only)",
        abs(s2[25100.0] - 2.0) < 1e-12, f"got {s2[25100.0]}")
    chk("VS1 VS at 25100 = 4.0 (put gamma on combined OI)",
        abs(sv[25100.0] - 4.0) < 1e-12, f"got {sv[25100.0]}")
    chk("VS1 V2 at 25000 = 3.0", abs(s2[25000.0] - 3.0) < 1e-12, f"got {s2[25000.0]}")
    chk("VS1 VS at 25000 = 3.0 (mean of two equal gammas)",
        abs(sv[25000.0] - 3.0) < 1e-12, f"got {sv[25000.0]}")
    chk("VS1 V2 pin == 25000", p2 == 25000.0, f"got {p2}")
    chk("VS1 VS pin == 25100", pv == 25100.0, f"got {pv}")
    chk("VS1 VS and V2 DISAGREE on this strike set", p2 != pv, f"V2={p2} VS={pv}")
    # mean branch, explicitly
    one = {25050.0: {"c_gamma": "0.002", "p_gamma": "0.004", "c_oi": 10.0, "p_oi": 0.0}}
    chk("VS2 both legs > 0 -> MEAN is used (0.003 * 10 = 0.03)",
        abs(vs_scores(one)[25050.0] - 0.03) < 1e-15, f"got {vs_scores(one)[25050.0]}")
    zero = {25050.0: {"c_gamma": None, "p_gamma": "0", "c_oi": 1e6, "p_oi": 1e6}}
    chk("VS3 both blank/zero -> score 0 on 1e6/1e6 OI",
        vs_scores(zero)[25050.0] == 0.0, f"got {vs_scores(zero)[25050.0]}")
    L.append("")

    # ---- FV on analyze_v5's ST2 planted chain; FV must return 25100.
    Sp, T3 = 25010.0, 3.0 / 365.0
    t_min = T3 * MIN_PER_YEAR
    pc = {}
    for K in [24800.0 + 50.0 * i for i in range(9)]:
        pc[K] = {"c_gamma": "0", "p_gamma": "0", "c_oi": 100.0, "p_oi": 100.0}
    pc[25100.0]["c_oi"], pc[25100.0]["p_oi"] = 1000.0, 1000.0
    pc[24900.0]["c_oi"], pc[24900.0]["p_oi"] = 0.0, 600.0
    pc[25200.0]["c_oi"], pc[25200.0]["p_oi"] = 900.0, 100.0
    sf, st = fv_scores(pc, Sp, 15.0, t_min)          # sigma 0.15 -> atm_iv_avg 15.0
    chk("FV1 status OK", st == "OK", st)
    pf, _, _ = pick(sf, Sp)
    chk("FV1 pin == 25100 on the ST2 chain at sigma 0.15", pf == 25100.0,
        f"got {pf}; top3 "
        f"{sorted(sf.items(), key=lambda kv: kv[1], reverse=True)[:3]}")
    chk("FV1 uses NO vendor gamma (every planted gamma is '0')",
        all(r["c_gamma"] == "0" and r["p_gamma"] == "0" for r in pc.values())
        and pf == 25100.0)
    L.append("")

    # ---- a run with no atm_iv_avg yields NO FV pin, and is reportable.
    sn, stn = fv_scores(pc, Sp, None, t_min)
    chk("FV2 no atm_iv_avg -> status NO_ATM_IV", stn == "NO_ATM_IV", stn)
    chk("FV2 no atm_iv_avg -> empty scores", sn == {}, f"got {sn}")
    chk("FV2 no atm_iv_avg -> pick returns no pin", pick(sn, Sp)[0] is None,
        f"got {pick(sn, Sp)[0]}")
    s0, st0 = fv_scores(pc, Sp, 15.0, 0)
    chk("FV3 T <= 0 -> status T_NONPOSITIVE and no pin",
        st0 == "T_NONPOSITIVE" and pick(s0, Sp)[0] is None, st0)
    L.append("")
    L.append(f"VS/FV SELF-TESTS {'ALL PASS' if ok else 'FAILED'} "
             f"({sum(1 for x in L if x.startswith('PASS'))} pass, "
             f"{sum(1 for x in L if x.startswith('FAIL'))} fail)")
    return ok, "\n".join(L) + "\n"


if __name__ == "__main__":
    ok, txt = self_tests()
    sys.stdout.write(txt)
    raise SystemExit(0 if ok else 3)
