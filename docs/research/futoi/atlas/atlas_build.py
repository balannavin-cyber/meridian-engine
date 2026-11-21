"""Atlas row builders. READ-ONLY. Exploration, not a test.

Every builder records, for each row, the two timestamps K3 reports:
  cond_ts  the LAST minute any conditioning value is read at
  out_ts   the minute the outcome starts from
and the invariant is cond_ts <= out_ts, asserted in build_windows().
"""
import csv
import math
import os

import atlas_lib as L

OUTCOMES = ["ret30", "ret60", "retclose", "retnext", "rng60", "rngclose"]
CONT = ["cont30", "cont60", "contclose", "contnext"]


# ------------------------------------------------------------------ windows
def build_windows(D, step, oi_key="F"):
    """Non-overlapping `step`-minute windows from 09:15, full grid windows only.

    dP and dOI are measured start->end. The outcome starts AT end, so the first
    forward increment is end -> end+1 and no conditioning minute is inside any
    outcome (K3)."""
    P, S, PH, PL = D["P"], D["S"], D["PH"], D["PL"]
    OI = D[oi_key]
    sessions = D["sessions"]
    nxt = {d: sessions[i + 1] for i, d in enumerate(sessions[:-1])}
    bnds = L.boundaries(step)
    rows = []
    for d in sessions:
        for k in range(len(bnds) - 1):
            a, b = bnds[k], bnds[k + 1]
            Pa, Pb = L.series_at(P, d, a), L.series_at(P, d, b)
            Oa, Ob = L.series_at(OI, d, a), L.series_at(OI, d, b)
            dP = None if (Pa is None or Pb is None) else Pb - Pa
            dOI = None if (Oa is None or Ob is None) else Ob - Oa
            cls = L.classify(dP, dOI)
            r = {"trade_date": d, "step": step, "oi_key": oi_key,
                 "win_start": L.lbl(a), "win_end": L.lbl(b),
                 "cond_ts": L.lbl(b), "out_ts": L.lbl(b),
                 "slot": a, "end_min": b, "tod": L.tod(b),
                 "P_start": Pa, "P_end": Pb, "dP": dP, "dOI": dOI, "cls": cls,
                 "expiry_flag": D["expiry_flag"].get(d, "")}
            r["ret30"] = L.ret_bp(Pb, L.series_at(P, d, b + 30))
            r["ret60"] = L.ret_bp(Pb, L.series_at(P, d, b + 60))
            r["retclose"] = L.ret_bp(Pb, L.series_at(P, d, L.CLOSE_MIN))
            nd = nxt.get(d)
            r["retnext"] = L.ret_bp(Pb, L.series_at(P, nd, L.CLOSE_MIN)) if nd else None
            r["rng60"] = L.fwd_range_bp(PH, PL, d, b, b + 60, Pb)
            r["rngclose"] = L.fwd_range_bp(PH, PL, d, b, L.CLOSE_MIN, Pb)
            sgn = 0 if dP is None else (1 if dP > 0 else (-1 if dP < 0 else 0))
            for c, o in zip(CONT, ["ret30", "ret60", "retclose", "retnext"]):
                r[c] = None if (sgn == 0 or r[o] is None) else sgn * r[o]
            assert r["cond_ts"] <= r["out_ts"]
            rows.append(r)
    _mark_strong(rows)
    return rows


def _mark_strong(rows):
    """'Strong' = |dP| and |dOI| both above that time slot's median, the median
    taken across sessions within the slot (and within this step and oi_key)."""
    by = {}
    for r in rows:
        by.setdefault(r["slot"], []).append(r)
    for slot, rs in by.items():
        dp = sorted(abs(r["dP"]) for r in rs if r["dP"] is not None)
        do = sorted(abs(r["dOI"]) for r in rs if r["dOI"] is not None)
        mp = dp[len(dp) // 2] if dp else None
        mo = do[len(do) // 2] if do else None
        for r in rs:
            r["slot_med_absdP"] = mp
            r["slot_med_absdOI"] = mo
            r["strong"] = (r["dP"] is not None and r["dOI"] is not None
                           and mp is not None and mo is not None
                           and abs(r["dP"]) > mp and abs(r["dOI"]) > mo)


# ------------------------------------------------------------------ day level
def build_days(D, oi_key="F"):
    """A3: class from close-to-close dP and dOI; outcome is the NEXT session."""
    P, PH, PL = D["P"], D["PH"], D["PL"]
    OI = D[oi_key]
    sessions = D["sessions"]
    rows = []
    for i in range(1, len(sessions) - 1):
        p, d, n = sessions[i - 1], sessions[i], sessions[i + 1]
        Pp, Pd, Pn = (L.series_at(P, p, L.CLOSE_MIN), L.series_at(P, d, L.CLOSE_MIN),
                      L.series_at(P, n, L.CLOSE_MIN))
        Op, Od = L.series_at(OI, p, L.CLOSE_MIN), L.series_at(OI, d, L.CLOSE_MIN)
        dP = None if (Pp is None or Pd is None) else Pd - Pp
        dOI = None if (Op is None or Od is None) else Od - Op
        cls = L.classify(dP, dOI)
        hs = [v for m, v in PH.get(n, {}).items() if v is not None]
        ls = [v for m, v in PL.get(n, {}).items() if v is not None]
        rng = 1e4 * (max(hs) - min(ls)) / Pd if hs and ls and Pd else None
        ret = L.ret_bp(Pd, Pn)
        sgn = 0 if dP is None else (1 if dP > 0 else (-1 if dP < 0 else 0))
        rows.append({"trade_date": d, "prev": p, "next": n, "oi_key": oi_key,
                     "cond_ts": "%s 15:29:59" % d, "out_ts": "%s 15:29:59" % d,
                     "dP": dP, "dOI": dOI, "cls": cls,
                     "retnext": ret, "rngnext": rng,
                     "contnext": None if (sgn == 0 or ret is None) else sgn * ret,
                     "expiry_flag": D["expiry_flag"].get(d, "")})
    # runs of the same day class
    run = 0
    prev = None
    for r in rows:
        if r["cls"] in L.REAL_CLASSES and r["cls"] == prev:
            run += 1
        else:
            run = 1
        r["run_len"] = run if r["cls"] in L.REAL_CLASSES else 0
        r["run_bucket"] = ("1" if run == 1 else "2" if run == 2 else "3+") \
            if r["cls"] in L.REAL_CLASSES else "n/a"
        prev = r["cls"]
    return rows


# ------------------------------------------------------------------ study B
CLOCKS = [10 * 60, 12 * 60, 14 * 60, L.CLOSE_MIN]


def days_to_expiry(D):
    """Trading sessions from each session to the next futures expiry >= it, plus
    the cycle id (which expiry). Uses the 12 expiry dates of the M1/M2 run."""
    sessions = D["sessions"]
    exps = [e for e in D["fut_expiries"]]
    out = {}
    for d in sessions:
        nxt = [e for e in exps if e >= d]
        if not nxt:
            out[d] = (None, None)
            continue
        e = nxt[0]
        i, j = sessions.index(d), sessions.index(e) if e in sessions else None
        out[d] = ((j - i) if j is not None else None, e)
    return out


def build_basis(D):
    """b = (P - S)/S in bp at four clock times; norm = median b at the same
    days-to-expiry and clock time, computed LEAVING OUT the session's own
    expiry cycle; dev = b - norm."""
    P, S, PH, PL = D["P"], D["S"], D["PH"], D["PL"]
    sessions = D["sessions"]
    nxt = {d: sessions[i + 1] for i, d in enumerate(sessions[:-1])}
    dte = days_to_expiry(D)
    raw = []
    for d in sessions:
        k, cyc = dte.get(d, (None, None))
        for m in CLOCKS:
            Pm, Sm = L.series_at(P, d, m), L.series_at(S, d, m)
            b = None if (Pm is None or Sm in (None, 0)) else 1e4 * (Pm - Sm) / Sm
            raw.append({"trade_date": d, "clock": L.lbl(m), "clock_min": m,
                        "dte": k, "cycle": cyc, "b": b, "P": Pm,
                        "expiry_flag": D["expiry_flag"].get(d, "")})
    groups = {}
    for r in raw:
        if r["b"] is not None and r["dte"] is not None:
            groups.setdefault((r["dte"], r["clock_min"]), []).append((r["cycle"], r["b"]))
    for r in raw:
        key = (r["dte"], r["clock_min"])
        pool = [v for cyc, v in groups.get(key, []) if cyc != r["cycle"]]
        r["norm"] = L.np.median(pool) if pool else None
        r["norm_n"] = len(pool)
        r["dev"] = None if (r["b"] is None or r["norm"] is None) else r["b"] - r["norm"]
        d, m = r["trade_date"], r["clock_min"]
        r["cond_ts"] = "%s %s" % (d, L.lbl(m))
        r["out_ts"] = "%s %s" % (d, L.lbl(m))
        r["ret_to_close"] = L.ret_bp(r["P"], L.series_at(P, d, L.CLOSE_MIN))
        nd = nxt.get(d)
        r["ret_next"] = L.ret_bp(L.series_at(P, d, L.CLOSE_MIN),
                                 L.series_at(P, nd, L.CLOSE_MIN)) if nd else None
        if nd:
            hs = [v for mm, v in PH.get(nd, {}).items() if v is not None]
            ls = [v for mm, v in PL.get(nd, {}).items() if v is not None]
            base = L.series_at(P, d, L.CLOSE_MIN)
            r["rng_next"] = 1e4 * (max(hs) - min(ls)) / base if hs and ls and base else None
        else:
            r["rng_next"] = None
    return raw


# ------------------------------------------------------------------ study D
def build_walls(D, chain, spot_close):
    """Walls fixed from the PRIOR session's close, front expiry.
    call wall = strike with the largest CE OI at or above the prior spot close;
    put wall  = largest PE OI at or below.

    Flags (operator ruling, 2026-11-18):
      edge_call / edge_put  the arg-max sits at the highest / lowest strike the
                            vendor lists, so the true maximum may lie outside
      bar_not_close         the prior session's tag-B bar is not 15:29:59
    2025-10-21 is EXCLUDED from walls and counted (its tag-B bar is 14:45:59)."""
    sessions = D["sessions"]
    out = {}
    excluded = []
    for i in range(1, len(sessions)):
        p, d = sessions[i - 1], sessions[i]
        rows = chain.get(p) or []
        s = spot_close.get(p)
        if not rows or s is None:
            excluded.append((d, p, "no prior chain or prior spot close"))
            continue
        bars = {r.get("hhmmss") for r in rows if r.get("hhmmss")}
        if bars and bars != {"15:29:59"}:
            excluded.append((d, p, "prior tag-B bar is %s, not 15:29:59" % sorted(bars)[0]))
            continue
        ks = [r["strike"] for r in rows if r["strike"] is not None]
        if not ks:
            excluded.append((d, p, "no strikes"))
            continue
        kmin, kmax = min(ks), max(ks)
        ce = [r for r in rows if r["option_type"] == "CE" and r["strike"] >= s and r["oi"]]
        pe = [r for r in rows if r["option_type"] == "PE" and r["strike"] <= s and r["oi"]]
        if not ce or not pe:
            excluded.append((d, p, "no CE at/above or no PE at/below prior spot"))
            continue
        cw = max(ce, key=lambda r: r["oi"])
        pw = max(pe, key=lambda r: r["oi"])
        out[d] = {"prior": p, "expiry": rows[0]["expiry"], "prior_spot": s,
                  "call_wall": cw["strike"], "call_oi": cw["oi"],
                  "put_wall": pw["strike"], "put_oi": pw["oi"],
                  "edge_call": cw["strike"] == kmax, "edge_put": pw["strike"] == kmin,
                  "call_dist_pct": 100.0 * (cw["strike"] - s) / s,
                  "put_dist_pct": 100.0 * (pw["strike"] - s) / s}
    return out, excluded


def build_approaches(D, walls, band_pct):
    """First minute S comes within band_pct of a wall FROM THE INSIDE.

    Outcome at 15:29:59: BREAK if S is beyond the wall by >= 0.10 %, else HOLD.
    Conditioning (dF, dF1 over the 30 minutes BEFORE the approach) is read at
    the approach minute; the outcome runs from the approach minute onward."""
    S = D["S"]
    rows = []
    for d, w in sorted(walls.items()):
        Sd = S.get(d) or {}
        sclose = Sd.get(L.CLOSE_MIN)
        for side, wall in (("call", w["call_wall"]), ("put", w["put_wall"])):
            hit = None
            for m in sorted(Sd):
                v = Sd[m]
                if v is None:
                    continue
                inside = (v < wall) if side == "call" else (v > wall)
                near = abs(v - wall) / wall <= band_pct / 100.0
                if inside and near:
                    hit = m
                    break
            if hit is None:
                rows.append({"trade_date": d, "side": side, "band_pct": band_pct,
                             "approached": False, "wall": wall,
                             "wall_dist_pct": w["call_dist_pct"] if side == "call"
                             else w["put_dist_pct"],
                             "edge": w["edge_call"] if side == "call" else w["edge_put"],
                             "expiry_flag": D["expiry_flag"].get(d, "")})
                continue
            beyond = []
            for m in sorted(Sd):
                if m < hit or Sd[m] is None:
                    continue
                e = (Sd[m] - wall) / wall if side == "call" else (wall - Sd[m]) / wall
                beyond.append(e)
            maxexc = 100.0 * max(beyond) if beyond else None
            fin = None
            if sclose is not None:
                fin = 100.0 * ((sclose - wall) / wall if side == "call"
                               else (wall - sclose) / wall)
            r = {"trade_date": d, "side": side, "band_pct": band_pct,
                 "approached": True, "wall": wall, "approach_min": hit,
                 "approach_ts": "%s %s" % (d, L.lbl(hit)),
                 "cond_ts": "%s %s" % (d, L.lbl(hit)),
                 "out_ts": "%s %s" % (d, L.lbl(hit)),
                 "wall_dist_pct": w["call_dist_pct"] if side == "call" else w["put_dist_pct"],
                 "edge": w["edge_call"] if side == "call" else w["edge_put"],
                 "max_excursion_pct": maxexc,
                 "final_beyond_pct": fin,
                 "outcome": None if fin is None else ("BREAK" if fin >= 0.10 else "HOLD"),
                 "expiry_flag": D["expiry_flag"].get(d, "")}
            for key in ("F", "F1"):
                a = L.series_at(D[key], d, hit - 30)
                b = L.series_at(D[key], d, hit)
                r["d" + key + "_30"] = None if (a is None or b is None) else b - a
            rows.append(r)
    return rows


def wall_distance_bucket(p):
    a = abs(p)
    return "<=2%" if a <= 2 else ("2-4%" if a <= 4 else ">4%")
