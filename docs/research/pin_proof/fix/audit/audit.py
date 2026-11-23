#!/usr/bin/env python3
"""Gamma pipeline audit -- per-run measures. Disk only: fix/replay_v2/chain/*.txt.

No database. The reference gamma gK is NOT re-derived here: it comes from
lookback_v5/analyze_v5.py compute_run, the same function fix/replay_v2/score_v2.py
uses. gVS is recovered from fix/replay_v2/constructions_v2.py vs_scores, so the VS
rule has exactly ONE definition in the tree.

MEMORY: one symbol-day is read at a time and every per-strike map is dropped as soon
as the run's record is emitted (box 1,910 MB, no swap). load_runs / measures / main of
analyze_v5.py are never called.

UNITS: P, N and R are raw gamma x OI sums. NO spot^2/1e7 factor anywhere, by spec, so
these numbers are not Crore and are not comparable with stored gex_cr.

STRUCTURE, and why: ALL measure arithmetic (per-strike net/gross for P, N and R, then
N1..N5, L1, K1, over all strikes and over no-fallback strikes) lives in ONE pure
function, measure_run(). audit_run() calls it and does no measure arithmetic of its
own, and self_test.py calls the SAME function. A test that re-implemented these sums
could not fail on a bug in this file, which is the whole point of having it.

DEFINITIONS (spec, transcribed)
  gc, gp  vendor call/put gamma; blank or <= 0 counts as 0
  gVS     mean of gc,gp when both > 0; the positive one when only one is; else 0
  gK      reference per-strike own gamma, exactly replay v2
  P  net_P = gc*OIc - gp*OIp        gross_P = gc*OIc + gp*OIp   (a leg contributes 0
                                     when its gamma is 0 or its OI <= 0)
  N  net_N = gVS*(OIc - OIp)        gross_N = gVS*(OIc + OIp)
  R  net_R = gK *(OIc - OIp)        gross_R = gK *(OIc + OIp)    GR = sum gross_R
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent / "replay_v2"
sys.path.insert(0, str(V2))
sys.path.insert(0, str(HERE.parent / "replay"))
sys.path.insert(0, str(HERE.parent.parent / "lookback_v5"))

from score_replay import _g                      # noqa: E402  vendor-gamma reader
from constructions_v2 import vs_scores           # noqa: E402  the VS rule
from analyze_v5 import compute_run               # noqa: E402  gK

STEP = {"NIFTY": 50.0, "SENSEX": 100.0}

# ADDITION (b): the replay v2 per-run record, keyed by run_id, loaded ONCE and read
# only for the K / VS cross-check. Absence of a run_id is reported as "absent", never
# silently treated as agreement.
_RV2 = None


def _rv2():
    global _RV2
    if _RV2 is None:
        import csv as _csv
        _RV2 = {}
        p = V2 / "runs.csv"
        if p.exists():
            with p.open(encoding="utf-8") as fh:
                for r in _csv.DictReader(fh):
                    _RV2[r["run_id"]] = r
    return _RV2


# ------------------------------------------------------------------ small helpers
def gvs_of(e) -> float:
    """gVS for one strike, RECOVERED FROM constructions_v2.vs_scores rather than
    restated: vs_scores returns gVS * (OIc + OIp), so dividing by that OI gives gVS
    back. Every strike in the set has OI > 0 on at least one leg, so the divisor is
    positive."""
    oi = e["c_oi"] + e["p_oi"]
    if oi <= 0:
        return 0.0
    return vs_scores({1.0: e})[1.0] / oi


def _net_P(gc, gp, oic, oip):
    """Production's per-strike net. Isolated so the self-test can mutate exactly this
    one expression (put term added instead of subtracted) and prove the suite notices."""
    c = gc * oic if (gc > 0 and oic > 0) else 0.0
    p = gp * oip if (gp > 0 and oip > 0) else 0.0
    return c - p


def _gross_P(gc, gp, oic, oip):
    c = gc * oic if (gc > 0 and oic > 0) else 0.0
    p = gp * oip if (gp > 0 and oip > 0) else 0.0
    return c + p


def _q(v, p):
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]


def _pick(d, S):
    """argmax with the project's tie order: value, then nearer spot, then lower strike."""
    if not d:
        return None
    return max(d.items(), key=lambda kv: (kv[1], -abs(kv[0] - S), -kv[0]))[0]


def _lead(vals):
    """(top - second)/top; None when fewer than two values or the top is <= 0."""
    if len(vals) < 2:
        return None
    s = sorted(vals, reverse=True)
    return None if s[0] <= 0 else (s[0] - s[1]) / s[0]


def moneyness_bucket(K, S):
    a = abs(K / S - 1.0) * 100.0
    return "0-1" if a <= 1 else ("1-2" if a <= 2 else ("2-3" if a <= 3 else "3-5"))


def time_bucket(hhmm):
    return "0915-1000" if hhmm < "10:00" else ("1000-1400" if hhmm < "14:00"
                                               else "1400-1529")


def leg_side(K, S, which):
    """ITM / OTM for one leg. A call is ITM below spot, a put ITM above."""
    if which == "C":
        return "ITM" if K < S else "OTM"
    return "ITM" if K > S else "OTM"


def fb_bucket(fb):
    if fb is None:
        return None
    return "<-1" if fb < -1 else ("-1..1" if fb <= 1 else ">1")


# ============================================================ THE MEASURE FUNCTION
def measure_run(per_in: dict, S: float, step: float) -> dict:
    """The ONLY place N1..N5, L1, K1 and the per-strike P/N/R arithmetic exist.

    per_in: {strike: {"gc","gp","oic","oip","gk","fallback"}}, all floats except
    fallback (bool). Returns the measure record. Pure: no I/O, no globals touched.
    """
    per = {}
    for K, e in per_in.items():
        gc, gp, oic, oip, gk = e["gc"], e["gp"], e["oic"], e["oip"], e["gk"]
        gv = e["gvs"] if "gvs" in e else gvs_of(
            {"c_gamma": gc or None, "p_gamma": gp or None, "c_oi": oic, "p_oi": oip})
        # POST-HOC additions B1 / B2. gc_missing is TRUE ONLY when the raw field was
        # absent/null/empty -- a PRESENT ZERO is not missing. Default False, so a
        # caller that does not supply them gets B1 == P, which is the correct
        # degenerate case rather than a silent guess.
        gcm, gpm = bool(e.get("gc_missing", False)), bool(e.get("gp_missing", False))
        b1c = gp if gcm else gc
        b1p = gc if gpm else gp
        b2c = gc if gc > 0 else gp
        b2p = gp if gp > 0 else gc
        per[K] = {
            "gc": gc, "gp": gp, "oic": oic, "oip": oip, "gvs": gv, "gk": gk,
            "gc_missing": gcm, "gp_missing": gpm,
            "fallback": bool(e["fallback"]),
            "net_P": _net_P(gc, gp, oic, oip), "gross_P": _gross_P(gc, gp, oic, oip),
            "net_N": gv * (oic - oip), "gross_N": gv * (oic + oip),
            "net_R": gk * (oic - oip), "gross_R": gk * (oic + oip),
            "net_B1": b1c * oic - b1p * oip, "gross_B1": b1c * oic + b1p * oip,
            "net_B2": b2c * oic - b2p * oip, "gross_B2": b2c * oic + b2p * oip,
        }

    # ---- N1: production sign error over strikes with OIc != OIp ----
    n1 = {"n": 0, "wrong": 0, "zero": 0, "w_gross": 0.0, "wrong_gross": 0.0,
          "zero_gross": 0.0, "cause_blank": 0, "cause_both": 0}
    for v in per.values():
        if v["oic"] == v["oip"]:
            continue
        n1["n"] += 1
        n1["w_gross"] += v["gross_R"]
        want = 1 if (v["oic"] - v["oip"]) > 0 else -1
        got = 0 if v["net_P"] == 0 else (1 if v["net_P"] > 0 else -1)
        bad = False
        if got == 0:
            n1["zero"] += 1
            n1["zero_gross"] += v["gross_R"]
            bad = True
        elif got != want:
            n1["wrong"] += 1
            n1["wrong_gross"] += v["gross_R"]
            bad = True
        if bad:
            if v["gc"] <= 0 or v["gp"] <= 0:
                n1["cause_blank"] += 1
            else:
                n1["cause_both"] += 1

    # ---- N2 / N3 / N4 / L1 over a strike subset ----
    def errs(keys):
        sub = [per[k] for k in keys]
        gr = sum(v["gross_R"] for v in sub)
        nr = sum(v["net_R"] for v in sub)
        o = {"n": len(sub), "GR": gr, "NR": nr,
             "T_R": (nr / gr) if gr > 0 else None}
        for lab, nk, gk_key in (("P", "net_P", "gross_P"), ("N", "net_N", "gross_N"),
                                ("B1", "net_B1", "gross_B1"),
                                ("B2", "net_B2", "gross_B2")):
            gx = sum(v[gk_key] for v in sub)
            nx = sum(v[nk] for v in sub)
            o[f"G{lab}"] = gx
            o[f"N{lab}"] = nx
            o[f"E_raw_{lab}"] = (sum(abs(v[nk] - v["net_R"]) for v in sub) / gr) \
                if gr > 0 else None
            o[f"E_shape_{lab}"] = sum(abs(v[nk] / gx - v["net_R"] / gr) for v in sub) \
                if (gr > 0 and gx > 0) else None
            tx = (nx / gx) if gx > 0 else None
            o[f"T_{lab}"] = tx
            o[f"T_err_{lab}"] = (abs(tx - o["T_R"])
                                 if (tx is not None and o["T_R"] is not None) else None)
            o[f"T_signflip_{lab}"] = (None if (tx is None or o["T_R"] is None)
                                      else ((tx > 0) != (o["T_R"] > 0)))
            o[f"L1_{lab}"] = sum(abs(v[gk_key] / gx - v["gross_R"] / gr) for v in sub) \
                if (gr > 0 and gx > 0) else None
        o["T_R_big"] = (abs(o["T_R"]) >= 0.05) if o["T_R"] is not None else None
        return o

    allk = list(per)
    nofb = [k for k in per if not per[k]["fallback"]]

    # ---- N5 peaks ----
    n5 = {}
    for lab, key in (("P", "net_P"), ("N", "net_N"), ("R", "net_R"),
                     ("B1", "net_B1"), ("B2", "net_B2")):
        n5[f"{lab}_pos"] = _pick({k: per[k][key] for k in per if per[k][key] > 0}, S)
        n5[f"{lab}_abs"] = _pick({k: abs(per[k][key]) for k in per}, S)
    n5["lead_R_pos"] = _lead([per[k]["net_R"] for k in per if per[k]["net_R"] > 0])
    n5["lead_R_abs"] = _lead([abs(per[k]["net_R"]) for k in per])
    for lab in ("P", "N", "B1", "B2"):
        for mode in ("pos", "abs"):
            a, b = n5[f"{lab}_{mode}"], n5[f"R_{mode}"]
            n5[f"same_{lab}_{mode}"] = None if (a is None or b is None) else (a == b)
            n5[f"gap_{lab}_{mode}"] = None if (a is None or b is None) \
                else abs(a - b) / step

    # ---- K1 ----
    GR = sum(v["gross_R"] for v in per.values())
    GN = sum(v["gross_N"] for v in per.values())
    nfb = sum(1 for v in per.values() if v["fallback"])
    gfb = sum(v["gross_R"] for v in per.values() if v["fallback"])
    # ADDITION (a): strikes whose REFERENCE gamma is missing or <= 0. These are NOT
    # fallback -- a fallback strike has a gK solved at the at-the-money vol, this one
    # has no usable gK at all, so it contributes 0 to every R quantity while still
    # carrying OI into gross_N. Counted and weighted separately, never merged with
    # the fallback count.
    nz = [k for k in per if not (per[k]["gk"] > 0)]
    gnz = sum(per[k]["gross_N"] for k in nz)

    return {
        "per": per,
        "N1": n1,
        "ALL": errs(allk),
        "NOFB": errs(nofb) if nofb else {"n": 0},
        "N5": n5,
        # ADDITION (b): the gross peaks, so the run can be checked against the K / VS
        # pins recorded for the same run_id in fix/replay_v2/runs.csv.
        "gR_peak": _pick({k: per[k]["gross_R"] for k in per}, S),
        "gN_peak": _pick({k: per[k]["gross_N"] for k in per}, S),
        "K1": {"n_strikes": len(per), "n_fallback": nfb,
               "share_strikes": (nfb / len(per)) if per else None,
               "share_GR": (gfb / GR) if GR > 0 else None,
               "n_gk_zero": len(nz),
               "share_strikes_gk_zero": (len(nz) / len(per)) if per else None,
               "share_GN_gk_zero": (gnz / GN) if GN > 0 else None},
    }


# ------------------------------------------------------------------ one run
def audit_run(sym, day, meta, rows):
    """Build per-strike inputs, call measure_run for every measure, add I1/I2/G1-G3."""
    S = float(meta["spot_min"]) if meta.get("spot_min") else 0.0
    ts = meta["ts_ist"]
    hhmm = ts[11:16]
    if S <= 0 or not rows:
        return None
    step = STEP[sym]

    cr = compute_run(sym, ts[:10], hhmm, S, meta["expiry"], rows, [])
    if not cr.get("valid"):
        out = {"sym": sym, "day": day, "ts_ist": ts, "run_id": meta["run_id"],
               "valid": False, "reason": cr.get("reason")}
        for k in ("_rows", "g", "g_flat", "sigma_k"):
            cr.pop(k, None)
        return out

    gK, sk, sigma_atm = cr["g"], cr["sigma_k"], cr["sigma_atm"]
    per_in = {}
    for K, e in rows.items():
        per_in[K] = {
            "gc": _g(e["c_gamma"]), "gp": _g(e["p_gamma"]),
            "oic": e["c_oi"], "oip": e["p_oi"],
            # MISSING means the raw field was absent/null/empty. A present "0.0" is
            # NOT missing. Measured over all 128 files: 0 missing legs on both
            # symbols, so on this data B1 degenerates to P exactly.
            "gc_missing": e["c_gamma"] in (None, ""),
            "gp_missing": e["p_gamma"] in (None, ""),
            "gvs": gvs_of(e), "gk": gK.get(K, 0.0),
            # fallback: compute_run could not solve this strike's own vol, so the
            # at-the-money vol was used.
            "fallback": (K in sk) and (abs(sk[K] - sigma_atm) < 1e-15),
        }

    m = measure_run(per_in, S, step)
    per = m["per"]

    rec = {"sym": sym, "day": day, "run_id": meta["run_id"], "ts_ist": ts,
           "hhmm": hhmm, "expiry": meta["expiry"], "dte_cal": cr["dte_cal"],
           "DTE": str(cr["dte_cal"]) if cr["dte_cal"] <= 2 else "3+",
           "expiry_day": (cr["dte_cal"] == 0), "S": S, "F": cr["F"],
           "FB": (cr["F"] - S) / step, "fb_bucket": fb_bucket((cr["F"] - S) / step),
           "sigma_atm": sigma_atm, "n_strikes": len(per),
           "time_bucket": time_bucket(hhmm), "valid": True, "reason": "",
           "GR": m["ALL"]["GR"], "N1": m["N1"], "ALL": m["ALL"], "NOFB": m["NOFB"],
           "N5": m["N5"], "K1": m["K1"],
           "gR_peak": m["gR_peak"], "gN_peak": m["gN_peak"]}

    # ---- ADDITION (b): cross-check the gross peaks against replay v2's K / VS ----
    rv = _rv2().get(meta["run_id"])
    if rv is None:
        rec["rv2_K"] = rec["rv2_VS"] = None
        rec["K_flag"] = rec["VS_flag"] = "run_id absent"
    else:
        def _f(x):
            return None if x in (None, "", "None") else float(x)
        rec["rv2_K"], rec["rv2_VS"] = _f(rv.get("K")), _f(rv.get("VS"))
        rec["rv2_K_lead"] = _f(rv.get("K_lead"))
        rec["K_flag"] = ("run_id absent" if rec["rv2_K"] is None
                         else ("same" if rec["rv2_K"] == m["gR_peak"] else "differs"))
        rec["VS_flag"] = ("run_id absent" if rec["rv2_VS"] is None
                          else ("same" if rec["rv2_VS"] == m["gN_peak"] else "differs"))

    # ---- I1 blank rate, by count and OI-weighted, with the spec's splits ----
    def acc():
        return {"n": 0, "blank": 0, "oi": 0.0, "oi_blank": 0.0}

    tot, byleg, bymny, bytime, byexp = acc(), {}, {}, {}, {}
    for K, v in per.items():
        for which, gx, oi in (("C", v["gc"], v["oic"]), ("P", v["gp"], v["oip"])):
            if oi <= 0:
                continue
            isb = gx <= 0
            for d, key in ((tot, None), (byleg, leg_side(K, S, which)),
                           (bymny, moneyness_bucket(K, S)),
                           (bytime, rec["time_bucket"]),
                           (byexp, "expiry_day" if rec["expiry_day"] else "other_day")):
                a = d if key is None else d.setdefault(key, acc())
                a["n"] += 1
                a["oi"] += oi
                if isb:
                    a["blank"] += 1
                    a["oi_blank"] += oi
    rec["I1"] = {"all": tot, "by_leg": byleg, "by_moneyness": bymny,
                 "by_time": bytime, "by_expiry": byexp}

    # ---- I2 gc/gp where both > 0 ----
    def ratio_acc(vals):
        if not vals:
            return {"n": 0}
        return {"n": len(vals), "median": statistics.median(vals),
                "p10": _q(vals, 0.10), "p90": _q(vals, 0.90),
                "share_outside": sum(1 for r in vals if r < 0.8 or r > 1.25) / len(vals)}

    allr, rleg, rmny, rtime, rexp = [], {}, {}, {}, {}
    for K, v in per.items():
        if v["gc"] > 0 and v["gp"] > 0:
            r = v["gc"] / v["gp"]
            allr.append(r)
            rleg.setdefault(leg_side(K, S, "C"), []).append(r)
            rmny.setdefault(moneyness_bucket(K, S), []).append(r)
            rtime.setdefault(rec["time_bucket"], []).append(r)
            rexp.setdefault("expiry_day" if rec["expiry_day"] else "other_day",
                            []).append(r)
    rec["I2"] = {"all": ratio_acc(allr),
                 "by_leg": {k: ratio_acc(v) for k, v in rleg.items()},
                 "by_moneyness": {k: ratio_acc(v) for k, v in rmny.items()},
                 "by_time": {k: ratio_acc(v) for k, v in rtime.items()},
                 "by_expiry": {k: ratio_acc(v) for k, v in rexp.items()},
                 "by_fb_bucket": {rec["fb_bucket"]: ratio_acc(allr)}}

    rec["G1"] = meta.get("_n_expiries", "NOT MEASURABLE")
    rec["G1_note"] = meta.get("_n_expiries_note", "")
    rec["G2"] = meta.get("_ts_spread", "NOT MEASURABLE")
    rec["G3"] = meta.get("_dupes", "NOT MEASURABLE")
    rec["_per"] = per
    for k in ("_rows", "g", "g_flat", "sigma_k"):
        cr.pop(k, None)
    return rec


# ------------------------------------------------------------------ one file
def audit_day(chain: Path, only_run=None, keep_per=False):
    """Read ONE symbol-day file, return per-run records. Drops maps as it goes."""
    sym, day = chain.name[len("out_"):-len(".txt")].split("_", 1)
    r0, legs, extra = {}, {}, {}
    for raw in chain.read_text(encoding="utf-8").splitlines():
        if not raw or "|" not in raw:
            continue
        tag, pay = raw.split("|", 1)
        j = json.loads(pay)
        rid = j["run_id"]
        if only_run and rid != only_run:
            continue
        if tag == "R0":
            r0[rid] = j
        elif tag == "R1":
            m = extra.setdefault(rid, {"keys": set(), "dupes": 0})
            kk = (j.get("expiry", ""), j["strike"], j["ot"])
            if kk in m["keys"]:
                m["dupes"] += 1
            m["keys"].add(kk)
            e = legs.setdefault(rid, {}).setdefault(
                float(j["strike"]),
                {"c_gamma": None, "p_gamma": None, "c_oi": 0.0, "p_oi": 0.0,
                 "c_px": 0.0, "p_px": 0.0})
            oi = float(j["oi"]) if j.get("oi") not in (None, "") else 0.0
            # c_px / p_px are REQUIRED: compute_run solves sigma from the leg prices.
            # Omitting them raised KeyError('c_px') on the first real run.
            px = float(j["ltp"]) if j.get("ltp") not in (None, "") else 0.0
            if j["ot"] == "CE":
                e["c_gamma"], e["c_oi"], e["c_px"] = j.get("gamma"), oi, px
            else:
                e["p_gamma"], e["p_oi"], e["p_px"] = j.get("gamma"), oi, px

    out = []
    for rid, meta in r0.items():
        if not ("09:15" <= meta["ts_ist"][11:16] <= "15:29"):
            continue
        rows = {k: v for k, v in legs.get(rid, {}).items()
                if v["c_oi"] > 0 or v["p_oi"] > 0}
        # G1: the chain pull joins option_chain_snapshots on the RUN'S OWN
        # expiry_date, so it is single-expiry BY CONSTRUCTION; a count from these
        # files can only ever be 1 and is reported as such, not as a measurement
        # of the chain.
        meta["_n_expiries"] = 1
        meta["_n_expiries_note"] = "single-expiry by construction of the chain pull"
        # G2: the files carry no per-leg snapshot timestamp, only the run's ts.
        meta["_ts_spread"] = "NOT MEASURABLE"
        meta["_dupes"] = extra.get(rid, {}).get("dupes", 0)
        rec = audit_run(sym, day, meta, rows)
        if rec is None:
            continue
        if not keep_per:
            rec.pop("_per", None)
        out.append(rec)
        rows.clear()
    r0.clear(); legs.clear(); extra.clear()
    return out


if __name__ == "__main__":
    raise SystemExit("audit.py: STAGE B runner not released; import audit_day instead")
