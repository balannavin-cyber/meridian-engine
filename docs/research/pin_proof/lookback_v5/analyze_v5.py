#!/usr/bin/env python3
"""lookback_v5 MEASURES -- disk-only analysis of the qD pull. No database, no vendor
call, no write outside lookback_v5/.

This is a DESCRIPTION. No measure here carries a pass or fail. The only stops are the
precondition (exit 2) and the self-tests (exit 3).

ORDER, which is itself load-bearing: the self-tests run BEFORE any data is touched, so
a broken solver cannot be discovered after it has already produced numbers; then the
precondition on out/_pull_run.log; then the data.

WHAT WOULD MAKE EACH GUARD FAIL (Rule 0):
  * precondition -- the pull log's last line is not exactly 'ALL <n> DONE' for
    n = |sessions_NIFTY| + |sessions_SENSEX|, or any STOP line exists. A partial pull
    would otherwise be analysed as though it were complete, and every share below
    would silently have a smaller denominator than it claims.
  * per-file -- R1 row count != sum of R0.n_legs. Both come from one CTE in the
    template, so a disagreement means the result set was truncated in transport. That
    is the one failure mode that is invisible in the data itself.
  * ST1 -- a round trip that does not invert to the vol it was priced at. If the
    bisection or the Black-76 form were wrong, every sigma_K and every gamma below
    would be wrong together and consistently, which is exactly the shape that survives
    review.
  * ST2 -- a planted chain whose pins are known by construction. Chosen so that T and
    N land on DIFFERENT strikes (25100 vs 25200) and neither is the ATM: a test where
    all three coincide would pass with the weights ignored.
  * ST3 -- the tie-break. Exercised against a synthetic score map, because two real
    strikes equidistant from S do not have equal gamma under a lognormal, so no real
    chain can test it.
  * ST4 -- a zero OTM price must take the fallback AND be counted. A fallback that is
    silently taken is the defect; counting is the test.

CONVENTIONS recorded because each could have gone another way:
  * 'the sampled minute' for T is the target minute (tname), e.g. 12:30:00, not the
    bar label 12:30:59.
  * sigma_atm is solved on the STRADDLE with forward = S; sigma_K on ONE leg with
    forward = F. The two use different forwards on purpose: sigma_atm is a spot-anchored
    reference, sigma_K is the smile at K.
  * one g_K per strike serves both legs, which is what Black-76 gives at a common vol.
  * expiry day is dte_cal == 0 (the run's own date is the expiry date). The DTE BUCKET
    is dte_sess, which counts sessions, so a bucket and 'expiry day' are not the same
    partition and are never mixed.
  * holds in M3 are cut at session ends: the first and last hold of every session is
    censored (its true length is unobserved), and both are included as observed. This
    biases hold length DOWNWARD and is reported, not corrected.
  * M4 windows overlap (every run i with i+4 present), so its n is windows, not
    independent observations.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SYMS = ("NIFTY", "SENSEX")
STEP = {"NIFTY": 50.0, "SENSEX": 100.0}
TNAMES = [f"{9 + (30 + 15 * i) // 60:02d}:{(30 + 15 * i) % 60:02d}" for i in range(24)]
SIG_LO, SIG_HI, SIG_TOL = 0.01, 5.0, 1e-6
MIN_PER_YEAR = 525600.0
PINS = ("T", "PW1", "PW2", "N")
GAMMAS = ("g", "g_flat")
BUCKETS = ("0", "1", "2", "3+")


# ------------------------------------------------------------------ math
def ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def d1_of(fwd: float, K: float, sig: float, T: float) -> float:
    v = sig * math.sqrt(T)
    return (math.log(fwd / K) + 0.5 * sig * sig * T) / v


def price76(fwd: float, K: float, sig: float, T: float, is_call: bool) -> float:
    """Black-76 at r = 0: undiscounted, forward `fwd`."""
    d1 = d1_of(fwd, K, sig, T)
    d2 = d1 - sig * math.sqrt(T)
    if is_call:
        return fwd * ncdf(d1) - K * ncdf(d2)
    return K * ncdf(-d2) - fwd * ncdf(-d1)


def straddle(fwd: float, K: float, sig: float, T: float) -> float:
    return price76(fwd, K, sig, T, True) + price76(fwd, K, sig, T, False)


def bisect(f, target: float):
    """Bisection on sigma in [0.01, 5.0] to 1e-6 on the interval width.

    f is increasing in sigma. A target outside [f(lo), f(hi)] has no root in the
    bracket and is returned as a named status, never clamped: a clamped sigma still
    produces a gamma and a pin, and nothing downstream could tell it from a solved one.
    """
    if f(SIG_LO) - target > 0:
        return SIG_LO, "BELOW_LO"
    if f(SIG_HI) - target < 0:
        return SIG_HI, "ABOVE_HI"
    lo, hi = SIG_LO, SIG_HI
    while hi - lo > SIG_TOL:
        mid = 0.5 * (lo + hi)
        if f(mid) - target > 0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi), "OK"


def iv_straddle(S: float, K: float, T: float, px: float):
    return bisect(lambda s: straddle(S, K, s, T), px)


def iv_leg(F: float, K: float, T: float, px: float, is_call: bool):
    return bisect(lambda s: price76(F, K, s, T, is_call), px)


def nearest_mult(x: float, step: float) -> float:
    """Multiple of `step` nearest x; tie -> the LOWER multiple."""
    lo = math.floor(x / step) * step
    hi = lo + step
    return lo if (x - lo) <= (hi - x) else hi


# ------------------------------------------------------------------ pins
def pick(scores: dict, S: float):
    """argmax with the fixed tie order: higher score, then nearer S, then lower strike.

    Returns (strike, share, lead). share = top/sum, lead = (s1-s2)/s1.
    """
    if not scores:
        return None, float("nan"), float("nan")
    items = sorted(scores.items(), key=lambda kv: (kv[1], -abs(kv[0] - S), -kv[0]),
                   reverse=True)
    tot = sum(scores.values())
    top = items[0][1]
    share = top / tot if tot > 0 else float("nan")
    if len(items) < 2 or top <= 0:
        lead = float("nan")
    else:
        lead = (top - items[1][1]) / top
    return items[0][0], share, lead


def pin_scores(gmap: dict, rows: dict, S: float, sigma_rem: float, kind: str) -> dict:
    out = {}
    for K, g in gmap.items():
        oc, op = rows[K]["c_oi"], rows[K]["p_oi"]
        if kind == "T":
            w = oc + op
        elif kind == "N":
            w = abs(oc - op)
        elif kind in ("PW1", "PW2"):
            mult = 1.0 if kind == "PW1" else 0.5
            sd = mult * sigma_rem
            if sd <= 0:
                return {}
            w = (oc + op) * math.exp(-((K - S) ** 2) / (2.0 * sd * sd))
        else:
            raise ValueError(kind)
        out[K] = g * w
    return out


# ------------------------------------------------------------------ per run
def compute_run(sym, day, tname, S, expiry, rows, sess_after):
    """-> dict. 'valid' False carries 'reason'. rows: K -> c_px/c_oi/p_px/p_oi."""
    step = STEP[sym]
    d0 = datetime.strptime(day, "%Y-%m-%d").date()
    e0 = datetime.strptime(expiry, "%Y-%m-%d").date()
    hh, mm = (int(x) for x in tname.split(":"))
    dte_cal = (e0 - d0).days
    t_min = dte_cal * 1440 + ((15 * 60 + 30) - (hh * 60 + mm))
    T = t_min / MIN_PER_YEAR
    dte_sess = sum(1 for s in sess_after if d0 < s <= e0)
    bucket = str(dte_sess) if dte_sess <= 2 else "3+"
    r = {"sym": sym, "day": day, "tname": tname, "S": S, "expiry": expiry,
         "dte_cal": dte_cal, "dte_sess": dte_sess, "bucket": bucket,
         "t_min": t_min, "T": T, "atm": nearest_mult(S, step),
         "valid": False, "reason": "", "sigma_atm_further": 0, "n_fallback": 0,
         "n_strikes": 0}
    if T <= 0:
        r["reason"] = "T_nonpositive"
        return r

    strikes = sorted(K for K, v in rows.items()
                     if v["c_oi"] > 0 or v["p_oi"] > 0)
    r["n_strikes"] = len(strikes)
    if not strikes:
        r["reason"] = "no_strikes"
        return r

    # ---- sigma_atm: nearest strike with BOTH prices > 0, up to 3 candidates ----
    cands = [K for K in sorted(rows, key=lambda k: (abs(k - S), k))
             if rows[K]["c_px"] > 0 and rows[K]["p_px"] > 0]
    sigma_atm, atm_k = None, None
    for i, K in enumerate(cands[:3]):
        s, st = iv_straddle(S, K, T, rows[K]["c_px"] + rows[K]["p_px"])
        if st == "OK":
            sigma_atm, atm_k, r["sigma_atm_further"] = s, K, 1 if i > 0 else 0
            break
    if sigma_atm is None:
        r["reason"] = "sigma_atm"
        return r
    r["sigma_atm"], r["atm_k"] = sigma_atm, atm_k
    r["sigma_rem"] = S * sigma_atm * math.sqrt(T)

    # ---- F: median of (K + call - put) over the three nearest strikes with both px ----
    if not cands:
        r["reason"] = "forward"
        return r
    par = [K + rows[K]["c_px"] - rows[K]["p_px"] for K in cands[:3]]
    if not par:
        r["reason"] = "forward"
        return r
    F = statistics.median(par)
    r["F"] = F
    if F <= 0:
        r["reason"] = "forward"
        return r

    # ---- gammas ----
    g, g_flat, sk = {}, {}, {}
    for K in strikes:
        is_call = K >= F
        px = rows[K]["c_px"] if is_call else rows[K]["p_px"]
        sig_k, st = (None, "NOPX")
        if px > 0:
            sig_k, st = iv_leg(F, K, T, px, is_call)
        if st != "OK":
            sig_k = sigma_atm
            r["n_fallback"] += 1
        sk[K] = sig_k
        g[K] = npdf(d1_of(F, K, sig_k, T)) / (F * sig_k * math.sqrt(T))
        g_flat[K] = (npdf(d1_of(S, K, sigma_atm, T))
                     / (S * sigma_atm * math.sqrt(T)))
    r["sigma_k"], r["g"], r["g_flat"] = sk, g, g_flat
    r["fallback_share"] = r["n_fallback"] / len(strikes)

    # ---- pins ----
    for gname, gmap in (("g", g), ("g_flat", g_flat)):
        for kind in PINS:
            sc = pin_scores(gmap, rows, S, r["sigma_rem"], kind)
            k, share, lead = pick(sc, S)
            r[f"{kind}_{gname}"] = k
            r[f"{kind}_{gname}_share"] = share
            r[f"{kind}_{gname}_lead"] = lead

    # ---- walls (the Board's rule, reconstructed) ----
    sigma_wall = S * sigma_atm * math.sqrt(max(dte_cal, 1) / 252.0)
    r["sigma_wall"] = sigma_wall
    elig = [K for K in strikes if abs(K - S) <= 1.5 * sigma_wall]
    cw = pw = None
    if elig:
        cc = {K: rows[K]["c_oi"] for K in elig if rows[K]["c_oi"] > 0}
        pp = {K: rows[K]["p_oi"] for K in elig if rows[K]["p_oi"] > 0}
        if cc:
            cw = sorted(cc.items(),
                        key=lambda kv: (kv[1], -abs(kv[0] - S), -kv[0]),
                        reverse=True)[0][0]
        if pp:
            pw = sorted(pp.items(),
                        key=lambda kv: (kv[1], -abs(kv[0] - S), -kv[0]),
                        reverse=True)[0][0]
    r["call_wall"], r["put_wall"], r["n_eligible"] = cw, pw, len(elig)
    r["wall_defined"] = cw is not None and pw is not None
    r["wall_inverted"] = bool(r["wall_defined"] and pw > cw)
    r["_rows"] = rows
    r["valid"] = True
    return r


# ------------------------------------------------------------------ self tests
def self_tests() -> tuple[bool, str]:
    L, ok = [], True

    def chk(name, cond, detail=""):
        nonlocal ok
        ok = ok and bool(cond)
        L.append(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))

    L.append("lookback_v5 SELF-TESTS (run before any data is read)")
    L.append("=" * 74)
    L.append("")
    T3 = 3.0 / 365.0

    # ST1
    L.append("ST1 -- solver round trips (tolerance 1e-5 on sigma)")
    p = straddle(25000.0, 25000.0, 0.15, T3)
    s, st = iv_straddle(25000.0, 25000.0, T3, p)
    chk("ST1a straddle S=K=25000 sigma=0.15", st == "OK" and abs(s - 0.15) < 1e-5,
        f"px={p:.6f} recovered={s:.8f} status={st}")
    p = price76(25010.0, 25500.0, 0.18, T3, True)
    s, st = iv_leg(25010.0, 25500.0, T3, p, True)
    chk("ST1b B76 call F=25010 K=25500 sigma=0.18", st == "OK" and abs(s - 0.18) < 1e-5,
        f"px={p:.6f} recovered={s:.8f} status={st}")
    p = price76(25010.0, 24500.0, 0.18, T3, False)
    s, st = iv_leg(25010.0, 24500.0, T3, p, False)
    chk("ST1c B76 put  F=25010 K=24500 sigma=0.18", st == "OK" and abs(s - 0.18) < 1e-5,
        f"px={p:.6f} recovered={s:.8f} status={st}")
    L.append("")

    # ST2 planted chain
    L.append("ST2 -- planted chain, pins known by construction")
    S = 25010.0
    rows = {}
    for K in [24800.0 + 50.0 * i for i in range(9)]:
        rows[K] = {"c_px": price76(S, K, 0.15, T3, True),
                   "p_px": price76(S, K, 0.15, T3, False),
                   "c_oi": 100.0, "p_oi": 100.0}
    rows[25100.0]["c_oi"], rows[25100.0]["p_oi"] = 1000.0, 1000.0
    rows[24900.0]["c_oi"], rows[24900.0]["p_oi"] = 0.0, 600.0
    rows[25200.0]["c_oi"], rows[25200.0]["p_oi"] = 900.0, 100.0
    # a synthetic session list giving dte_cal = 3
    d0 = date(2025, 4, 1)
    e0 = date(2025, 4, 4)
    rr = compute_run("NIFTY", d0.isoformat(), "15:30", S, e0.isoformat(), rows, [e0])
    # tname 15:30 -> t_min = 3*1440 + 0; dte_cal 3 as required
    chk("ST2 run valid", rr["valid"], rr.get("reason", ""))
    if rr["valid"]:
        chk("ST2 dte_cal == 3", rr["dte_cal"] == 3, f"got {rr['dte_cal']}")
        chk("ST2 ATM == 25000", rr["atm"] == 25000.0, f"got {rr['atm']}")
        for gname in GAMMAS:
            chk(f"ST2 pin T == 25100 under {gname}", rr[f"T_{gname}"] == 25100.0,
                f"got {rr[f'T_{gname}']}")
            chk(f"ST2 pin N == 25200 under {gname}", rr[f"N_{gname}"] == 25200.0,
                f"got {rr[f'N_{gname}']}")
        chk("ST2 call_wall == 25100", rr["call_wall"] == 25100.0,
            f"got {rr['call_wall']}")
        chk("ST2 put_wall == 25100", rr["put_wall"] == 25100.0,
            f"got {rr['put_wall']}")
        worst = max(abs(v - 0.15) for v in rr["sigma_k"].values())
        chk("ST2 every sigma_K within 1e-4 of 0.15", worst < 1e-4,
            f"worst deviation {worst:.3e}")
        chk("ST2 no fallback", rr["n_fallback"] == 0, f"got {rr['n_fallback']}")
    L.append("")

    # ST3 tie -> lower strike
    L.append("ST3 -- tie at equal distance resolves to the LOWER strike")
    k, _, lead = pick({24950.0: 7.0, 25050.0: 7.0}, 25000.0)
    chk("ST3 tie -> 24950", k == 24950.0, f"got {k}, lead={lead}")
    L.append("")

    # ST4 zero OTM px -> fallback, counted
    L.append("ST4 -- a zero OTM price takes the fallback and is counted")
    rows2 = {K: dict(v) for K, v in rows.items()}
    rows2[25200.0]["c_px"] = 0.0          # 25200 >= F so the call is the OTM leg
    r2 = compute_run("NIFTY", d0.isoformat(), "15:30", S, e0.isoformat(), rows2, [e0])
    chk("ST4 run valid", r2["valid"], r2.get("reason", ""))
    if r2["valid"]:
        chk("ST4 fallback counted == 1", r2["n_fallback"] == 1,
            f"got {r2['n_fallback']}")
        chk("ST4 fallback strike used sigma_atm",
            abs(r2["sigma_k"][25200.0] - r2["sigma_atm"]) < 1e-12,
            f"sigma_K={r2['sigma_k'][25200.0]:.8f} sigma_atm={r2['sigma_atm']:.8f}")
    L.append("")
    L.append("=" * 74)
    L.append(f"SELF-TESTS {'ALL PASS' if ok else 'FAILED'} "
             f"({sum(1 for x in L if x.startswith('PASS'))} pass, "
             f"{sum(1 for x in L if x.startswith('FAIL'))} fail)")
    return ok, "\n".join(L) + "\n"


# ------------------------------------------------------------------ loading
def precondition() -> tuple[bool, str]:
    log = OUT / "_pull_run.log"
    if not log.exists():
        return False, f"{log} does not exist"
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return False, "pull log is empty"
    n_exp = sum(len([x for x in (HERE / f"sessions_{s}.txt")
                     .read_text(encoding="utf-8").splitlines() if x.strip()])
                for s in SYMS)
    want = f"ALL {n_exp} DONE"
    stops = [l for l in lines if l.startswith("STOP")]
    if stops:
        return False, f"pull log carries {len(stops)} STOP line(s); first: {stops[0]}"
    if lines[-1] != want:
        return False, f"last log line is {lines[-1]!r}, expected {want!r}"
    return True, f"{want}; no STOP line; {n_exp} days"


def load_runs():
    """-> (runs, r2map, quality). Asserts R1 count == sum(n_legs) per file."""
    runs, r2map = [], {}
    q = {s: Counter() for s in SYMS}
    sess = {}
    for sym in SYMS:
        ds = [x for x in (HERE / f"sessions_{sym}.txt")
              .read_text(encoding="utf-8").splitlines() if x.strip()]
        sess[sym] = [datetime.strptime(d, "%Y-%m-%d").date() for d in ds]
        q[sym]["sessions"] = len(ds)
        q[sym]["runs_expected"] = 24 * len(ds)
    empties = Counter()
    for l in (OUT / "_pull_run.log").read_text(encoding="utf-8").splitlines():
        f = l.split()
        if f and f[0] == "OK_EMPTY":
            empties[f[1]] += 1
    for sym in SYMS:
        q[sym]["ok_empty_days"] = empties[sym]
        for d in [x for x in (HERE / f"sessions_{sym}.txt")
                  .read_text(encoding="utf-8").splitlines() if x.strip()]:
            fp = OUT / f"_qD_{sym}_{d}.txt"
            if not fp.exists():
                raise SystemExit(f"exit 2: missing pull output {fp}")
            r0, legs, r2 = {}, defaultdict(dict), None
            n_r1 = 0
            for raw in fp.read_text(encoding="utf-8").splitlines():
                if not raw or "|" not in raw:
                    continue
                tag, pay = raw.split("|", 1)
                j = json.loads(pay)
                if tag == "R0":
                    r0[j["tname"]] = j
                elif tag == "R1":
                    n_r1 += 1
                    K = float(j["strike"])
                    e = legs[j["tname"]].setdefault(
                        K, {"c_px": 0.0, "c_oi": 0.0, "p_px": 0.0, "p_oi": 0.0})
                    px = float(j["px"]) if j.get("px") not in (None, "") else 0.0
                    oi = float(j["oi"]) if j.get("oi") not in (None, "") else 0.0
                    if j["ot"] == "CE":
                        e["c_px"], e["c_oi"] = px, oi
                    elif j["ot"] == "PE":
                        e["p_px"], e["p_oi"] = px, oi
                    else:
                        raise SystemExit(f"exit 2: unknown ot {j['ot']!r} in {fp}")
                elif tag == "R2":
                    r2 = j
            legs_sum = sum(v["n_legs"] for v in r0.values())
            if n_r1 != legs_sum:
                raise SystemExit(f"exit 2: {fp} R1={n_r1} != sum(n_legs)={legs_sum}")
            if r2:
                r2map[(sym, d)] = r2
            q[sym]["runs_present"] += len(r0)
            for tname in TNAMES:
                if tname not in r0:
                    continue
                j = r0[tname]
                if not j.get("front_expiry"):
                    q[sym]["no_front_expiry"] += 1
                    continue
                for K in legs[tname]:
                    if abs(K / STEP[sym] - round(K / STEP[sym])) > 1e-9:
                        raise SystemExit(
                            f"exit 2: strike {K} not a multiple of {STEP[sym]} in {fp}")
                r = compute_run(sym, d, tname, float(j["spot"]), j["front_expiry"],
                                legs[tname], sess[sym])
                # PRUNE IMMEDIATELY. compute_run returns a per-strike map for _rows,
                # g, g_flat and sigma_k; holding those for ~11,700 runs exceeds the
                # Rule 23 ulimit -v 700000 and the process is killed. Only the
                # (oi_call, oi_put) pair AT EACH PIN STRIKE is needed downstream (M5),
                # plus the full maps for the four worked-example runs.
                if r["valid"]:
                    pins = {r[f"{p}_{g}"] for g in GAMMAS for p in PINS
                            if r.get(f"{p}_{g}") is not None}
                    r["_oi"] = {K: (r["_rows"][K]["c_oi"], r["_rows"][K]["p_oi"])
                                for K in pins}
                    if (sym, d, tname) not in {(a, b, c) for a, b, c in EXAMPLES}:
                        for k in ("_rows", "g", "g_flat", "sigma_k"):
                            r.pop(k, None)
                if r["valid"]:
                    q[sym]["valid"] += 1
                    q[sym]["sigma_atm_further"] += r["sigma_atm_further"]
                    if datetime.strptime(r["expiry"], "%Y-%m-%d").date() not in sess[sym]:
                        q[sym]["expiry_not_a_session"] += 1
                else:
                    q[sym][f"invalid_{r['reason']}"] += 1
                runs.append(r)
    return runs, r2map, q, sess


# ------------------------------------------------------------------ stats helpers
def q_at(vals, p):
    if not vals:
        return float("nan")
    v = sorted(vals)
    return v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))]


def fmt_m(vals, nd=2):
    if not vals:
        return "n/a (n=0)"
    return (f"{statistics.median(vals):.{nd}f} "
            f"[{q_at(vals, .10):.{nd}f},{q_at(vals, .90):.{nd}f}] n={len(vals)}")


def fmt_s(num, den, nd=1):
    if not den:
        return "n/a (n=0)"
    return f"{100.0 * num / den:.{nd}f}% n={den}"


def pct(num, den):
    return float("nan") if not den else 100.0 * num / den


def sessions_of(runs):
    """-> {(sym, day): [valid runs in tname order]}"""
    g = defaultdict(list)
    for r in runs:
        if r["valid"]:
            g[(r["sym"], r["day"])].append(r)
    for k in g:
        g[k].sort(key=lambda r: r["tname"])
    return g


# ------------------------------------------------------------------ measures
def measures(runs, r2map, q):
    L, screen = [], {}
    L.append("# lookback_v5 — MEASURES")
    L.append("")
    L.append("Disk-only description of the qD pull. **No measure here is a pass or a "
             "fail.** Every cell carries its own n. Symbols are never pooled. Primary "
             "gamma `g` (OTM leg against F, per-strike Black-76 vol) unless stated; "
             "`g_flat` is the single-sigma spot-anchored gamma.")
    L.append("")
    L.append("DTE bucket is **dte_sess** (sessions strictly after the run's day, up to "
             "and including the expiry date), bucketed 0 / 1 / 2 / 3+. "
             "'Expiry day' in M7 is **dte_cal == 0**. These are different partitions "
             "and are not mixed.")
    L.append("")

    # ---------------- data quality ----------------
    L.append("## Data quality")
    L.append("")
    L.append("| symbol | sessions | OK_EMPTY days | runs expected | runs present | "
             "valid | invalid | sigma_atm from a further strike | expiry not a session |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for s in SYMS:
        c = q[s]
        inv = {k[len("invalid_"):]: v for k, v in c.items()
               if k.startswith("invalid_")}
        L.append(f"| {s} | {c['sessions']} | {c['ok_empty_days']} | "
                 f"{c['runs_expected']} | {c['runs_present']} | {c['valid']} | "
                 f"{sum(inv.values())} {inv if inv else ''} | "
                 f"{c['sigma_atm_further']} | {c['expiry_not_a_session']} |")
        screen[f"dq_{s}"] = (f"{s}: sessions {c['sessions']}, OK_EMPTY {c['ok_empty_days']}, "
                             f"runs {c['runs_present']}/{c['runs_expected']} present, "
                             f"valid {c['valid']}, invalid {sum(inv.values())}"
                             + (f" {dict(inv)}" if inv else "")
                             + f", sigma_atm further-strike {c['sigma_atm_further']}, "
                             f"expiry-not-a-session {c['expiry_not_a_session']}")
    L.append("")
    L.append("`runs expected` is 24 per session. The shortfall is every target minute "
             "with no spot bar at exactly HH:MM:59 — recorded, not filled.")
    L.append("")

    by = {s: [r for r in runs if r["sym"] == s and r["valid"]] for s in SYMS}
    sess = sessions_of(runs)

    def subset(s, bkt):
        return [r for r in by[s] if bkt == "ALL" or r["bucket"] == bkt]

    # ---------------- M1 ----------------
    L.append("## M1 — where the pin sits")
    L.append("")
    for s in SYMS:
        L.append(f"### {s}")
        L.append("")
        L.append("| pin | bucket | runs | signed (pin−S)/step | abs (pin−S)/step | "
                 "abs (pin−S)/sigma_rem | share abs≤1 step | share pin=ATM |")
        L.append("|---|---|---|---|---|---|---|---|")
        for pin in PINS + ("ATM",):
            for bkt in BUCKETS + ("ALL",):
                rs = subset(s, bkt)
                key = "atm" if pin == "ATM" else f"{pin}_g"
                vals = [(r[key] - r["S"]) / STEP[s] for r in rs if r.get(key)]
                av = [abs(v) for v in vals]
                sg = [abs(r[key] - r["S"]) / r["sigma_rem"]
                      for r in rs if r.get(key) and r["sigma_rem"] > 0]
                n1 = sum(1 for r in rs if r.get(key)
                         and abs(r[key] - r["S"]) <= STEP[s])
                na = sum(1 for r in rs if r.get(key) and r[key] == r["atm"])
                L.append(f"| {pin} | {bkt} | {len(rs)} | {fmt_m(vals)} | "
                         f"{fmt_m(av)} | {fmt_m(sg, 3)} | {fmt_s(n1, len(rs))} | "
                         f"{fmt_s(na, len(rs))} |")
        L.append("")

    # ---------------- M2 ----------------
    L.append("## M2 — the pin against the Board's walls")
    L.append("")
    L.append("Undefined-wall runs are EXCLUDED from the shares and counted separately. "
             "Inverted walls (put_wall > call_wall) are counted too: on those runs "
             "`[put_wall, call_wall]` is empty, so every pin reads as outside.")
    L.append("")
    for s in SYMS:
        L.append(f"### {s}")
        L.append("")
        L.append("| pin | bucket | runs with walls | share pin outside corridor | "
                 "share pin = a wall | share S outside corridor | undefined | inverted |")
        L.append("|---|---|---|---|---|---|---|---|")
        for pin in PINS + ("ATM",):
            for bkt in BUCKETS + ("ALL",):
                rs = subset(s, bkt)
                wd = [r for r in rs if r["wall_defined"]]
                key = "atm" if pin == "ATM" else f"{pin}_g"
                out = sum(1 for r in wd if r.get(key) is not None
                          and not (r["put_wall"] <= r[key] <= r["call_wall"]))
                onw = sum(1 for r in wd if r.get(key) in (r["put_wall"], r["call_wall"]))
                sout = sum(1 for r in wd
                           if not (r["put_wall"] <= r["S"] <= r["call_wall"]))
                L.append(f"| {pin} | {bkt} | {len(wd)} | {fmt_s(out, len(wd))} | "
                         f"{fmt_s(onw, len(wd))} | {fmt_s(sout, len(wd))} | "
                         f"{len(rs) - len(wd)} | "
                         f"{sum(1 for r in rs if r['wall_inverted'])} |")
        L.append("")

    # ---------------- M3 ----------------
    def m3(gname):
        rows = []
        for s in SYMS:
            for pin in PINS:
                ch_per, holds, lead_lt5, tab = [], [], [0, 0], [0, 0]
                for (sy, _d), rs in sess.items():
                    if sy != s:
                        continue
                    seq = [r[f"{pin}_{gname}"] for r in rs]
                    if not seq:
                        continue
                    ch = 0
                    cur = 1
                    for i in range(len(seq) - 1):
                        if seq[i] != seq[i + 1]:
                            ch += 1
                            holds.append(cur)
                            cur = 1
                            ld = rs[i][f"{pin}_{gname}_lead"]
                            if ld == ld:
                                lead_lt5[1] += 1
                                if ld < 0.05:
                                    lead_lt5[0] += 1
                            back = (i + 2 < len(seq) and seq[i + 2] == seq[i]) or \
                                   (i + 3 < len(seq) and seq[i + 3] == seq[i])
                            tab[1] += 1
                            tab[0] += 1 if back else 0
                        else:
                            cur += 1
                    holds.append(cur)
                    ch_per.append(ch)
                rows.append((s, pin, fmt_m(ch_per, 1), fmt_m(holds, 1),
                             fmt_s(*lead_lt5), fmt_s(*tab)))
        return rows

    for gname in GAMMAS:
        L.append(f"## M3 — changes within a session ({'primary g' if gname == 'g' else 'g_flat'})")
        L.append("")
        L.append("Consecutive VALID runs in time order. **Holds are cut at the "
                 "session's ends**: the first and last hold of every session is "
                 "censored, so hold length is biased DOWNWARD. Not corrected.")
        L.append("")
        L.append("| symbol | pin | changes per session | hold length (runs) | "
                 "share of changes with prior lead <5% | share there-and-back |")
        L.append("|---|---|---|---|---|---|")
        for r in m3(gname):
            L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
        L.append("")

    # ---------------- M4 ----------------
    L.append("## M4 — does the pin follow spot?")
    L.append("")
    L.append("For every valid run i whose run i+4 is in the same session: "
             "dATM = (ATM[i+4] − ATM[i])/step, restricted to |dATM| ≥ 2. "
             "**Windows OVERLAP** (i and i+1 share three runs), so n is windows, "
             "not independent observations. Pins are multiples of step, so "
             "'moved under 1 step' can only be 0 and is shown to prove it.")
    L.append("")
    L.append("| symbol | pin | windows | moved same way ≥1 step | did not move | "
             "moved opposite ≥1 step | moved <1 step |")
    L.append("|---|---|---|---|---|---|---|")
    for s in SYMS:
        for pin in PINS:
            same = stay = opp = under = tot = 0
            for (sy, _d), rs in sess.items():
                if sy != s:
                    continue
                for i in range(len(rs) - 4):
                    da = (rs[i + 4]["atm"] - rs[i]["atm"]) / STEP[s]
                    if abs(da) < 2:
                        continue
                    a, b = rs[i][f"{pin}_g"], rs[i + 4][f"{pin}_g"]
                    if a is None or b is None:
                        continue
                    dp = (b - a) / STEP[s]
                    tot += 1
                    if dp == 0:
                        stay += 1
                    elif abs(dp) < 1:
                        under += 1
                    elif (dp > 0) == (da > 0):
                        same += 1
                    else:
                        opp += 1
            L.append(f"| {s} | {pin} | {tot} | {fmt_s(same, tot)} | "
                     f"{fmt_s(stay, tot)} | {fmt_s(opp, tot)} | {fmt_s(under, tot)} |")
            screen[f"m4_{s}_{pin}"] = (f"same {pct(same, tot):.1f}% / stayed "
                                       f"{pct(stay, tot):.1f}% / opposite "
                                       f"{pct(opp, tot):.1f}% (n={tot})")
    L.append("")

    # ---------------- M5 / M6 ----------------
    L.append("## M5 — sign at the pin, and M6 — concentration")
    L.append("")
    L.append("M5 is the share of runs where oi_put > oi_call at the pin's own strike "
             "(what the Board would call amplifying).")
    L.append("")
    for gname in GAMMAS:
        L.append(f"### gamma = {gname}")
        L.append("")
        L.append("| symbol | pin | bucket | runs | share amplifying (M5) | "
                 "score share (M6) | lead (M6) | share lead <5% |")
        L.append("|---|---|---|---|---|---|---|---|")
        for s in SYMS:
            for pin in PINS:
                for bkt in BUCKETS + ("ALL",):
                    rs = subset(s, bkt)
                    key = f"{pin}_{gname}"
                    amp = tot = 0
                    shs, lds, l5 = [], [], [0, 0]
                    for r in rs:
                        k = r.get(key)
                        if k is None:
                            continue
                        tot += 1
                        shs.append(r[f"{key}_share"])
                        ld = r[f"{key}_lead"]
                        if ld == ld:
                            lds.append(ld)
                            l5[1] += 1
                            if ld < 0.05:
                                l5[0] += 1
                        amp += 1 if r["_oi"][k][1] > r["_oi"][k][0] else 0
                    L.append(f"| {s} | {pin} | {bkt} | {tot} | {fmt_s(amp, tot)} | "
                             f"{fmt_m(shs, 4)} | {fmt_m(lds, 4)} | {fmt_s(*l5)} |")
        L.append("")

    # ---------------- M7 ----------------
    L.append("## M7 — closing in on the settle strike")
    L.append("")
    L.append("Settle strike = multiple of step nearest `last_close` of the EXPIRY "
             "DATE's own session, used only when that session is in the pull and its "
             "`last_clock` is 15:29:59 or later. Everything else is excluded and "
             "counted — a settle taken from a session that ended at 09:59 would be a "
             "mid-morning price called a settle.")
    L.append("")
    for s in SYMS:
        excl = 0
        settle = {}
        for r in by[s]:
            key = (s, r["expiry"])
            j = r2map.get(key)
            if not j or not j.get("last_clock") or j["last_clock"] < "15:29:59":
                excl += 1
                continue
            settle[id(r)] = nearest_mult(float(j["last_close"]), STEP[s])
        L.append(f"### {s} — excluded for want of a usable settle: {excl} of "
                 f"{len(by[s])} runs")
        L.append("")
        L.append("| pin | bucket | runs | abs(pin−settle)/step |")
        L.append("|---|---|---|---|")
        for pin in PINS + ("ATM",):
            for bkt in BUCKETS + ("ALL",):
                rs = [r for r in subset(s, bkt) if id(r) in settle]
                key = "atm" if pin == "ATM" else f"{pin}_g"
                v = [abs(r[key] - settle[id(r)]) / STEP[s] for r in rs if r.get(key)]
                L.append(f"| {pin} | {bkt} | {len(v)} | {fmt_m(v)} |")
        L.append("")
        L.append(f"#### {s} — expiry day (dte_cal = 0) by clock hour")
        L.append("")
        hours = sorted({r["tname"][:2] for r in by[s] if r["dte_cal"] == 0})
        L.append("| pin | " + " | ".join(f"{h}:xx" for h in hours) + " |")
        L.append("|---" * (len(hours) + 1) + "|")
        for pin in PINS + ("ATM",):
            cells = []
            for h in hours:
                rs = [r for r in by[s] if r["dte_cal"] == 0
                      and r["tname"][:2] == h and id(r) in settle]
                key = "atm" if pin == "ATM" else f"{pin}_g"
                v = [abs(r[key] - settle[id(r)]) / STEP[s] for r in rs if r.get(key)]
                cells.append(fmt_m(v, 1))
            L.append(f"| {pin} | " + " | ".join(cells) + " |")
            if pin in PINS or pin == "ATM":
                rs = [r for r in by[s] if r["dte_cal"] == 0 and id(r) in settle]
                key = "atm" if pin == "ATM" else f"{pin}_g"
                v = [abs(r[key] - settle[id(r)]) / STEP[s] for r in rs if r.get(key)]
                screen[f"m7_{s}_{pin}"] = (f"{statistics.median(v):.1f}"
                                           if v else "n/a")
                screen[f"m7n_{s}"] = len(rs)
        L.append("")

    # ---------------- M8 ----------------
    L.append("## M8 — agreement between the pins")
    L.append("")
    L.append("| symbol | pair | runs | share same strike |")
    L.append("|---|---|---|---|")
    names = list(PINS) + ["ATM"]
    for s in SYMS:
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = "atm" if names[i] == "ATM" else f"{names[i]}_g"
                b = "atm" if names[j] == "ATM" else f"{names[j]}_g"
                rs = [r for r in by[s] if r.get(a) is not None
                      and r.get(b) is not None]
                eq = sum(1 for r in rs if r[a] == r[b])
                L.append(f"| {s} | {names[i]} vs {names[j]} | {len(rs)} | "
                         f"{fmt_s(eq, len(rs))} |")
                screen[f"m8_{s}_{names[i]}_{names[j]}"] = pct(eq, len(rs))
    L.append("")

    # ---------------- M9 ----------------
    L.append("## M9 — how much the pin depends on the gamma")
    L.append("")
    L.append("`g` vs `g_flat`, split by the PRIMARY lead, because a disagreement at a "
             "near-tie and one at a wide lead are different findings: the first is "
             "argmax noise, the second says the two gammas rank the chain differently.")
    L.append("")
    L.append("| symbol | pin | split | runs | share pin differs | "
             "median diff (steps) | p90 diff (steps) |")
    L.append("|---|---|---|---|---|---|---|")
    for s in SYMS:
        for pin in PINS:
            for lab, test in (("ALL", lambda ld: True),
                              ("lead <5%", lambda ld: ld == ld and ld < 0.05),
                              ("lead ≥5%", lambda ld: ld == ld and ld >= 0.05)):
                rs = [r for r in by[s]
                      if r.get(f"{pin}_g") is not None
                      and r.get(f"{pin}_g_flat") is not None
                      and test(r[f"{pin}_g_lead"])]
                dif = [abs(r[f"{pin}_g"] - r[f"{pin}_g_flat"]) / STEP[s] for r in rs]
                nd = sum(1 for d in dif if d > 0)
                nz = [d for d in dif if d > 0]
                L.append(f"| {s} | {pin} | {lab} | {len(rs)} | "
                         f"{fmt_s(nd, len(rs))} | {fmt_m(nz, 1)} | "
                         f"{q_at(nz, .90):.1f} |" if nz else
                         f"| {s} | {pin} | {lab} | {len(rs)} | "
                         f"{fmt_s(nd, len(rs))} | n/a (n=0) | n/a |")
                if lab == "ALL":
                    screen[f"m9_{s}_{pin}"] = pct(nd, len(rs))
    L.append("")
    L.append("### Fallback (sigma_K could not be solved, sigma_atm used)")
    L.append("")
    L.append("| symbol | runs | median share of strikes on fallback | p90 | "
             "share of runs with >20% of strikes on fallback |")
    L.append("|---|---|---|---|---|")
    for s in SYMS:
        fs = [r["fallback_share"] for r in by[s]]
        hi = sum(1 for v in fs if v > 0.20)
        L.append(f"| {s} | {len(fs)} | {statistics.median(fs):.4f} | "
                 f"{q_at(fs, .90):.4f} | {fmt_s(hi, len(fs))} |")
        screen[f"fb_{s}"] = f"{statistics.median(fs):.4f}"
    L.append("")

    # ---------------- what this cannot say ----------------
    L.append("## What this cannot say")
    L.append("")
    L.append("- **Nothing after 2026-03-30.** The pull stops there because option "
             "bars stop there (lookback_v4 Part 0a). No statement here extends to the "
             "live board or to any date in the last eight months of the v4 window.")
    L.append("- **OI is not dealer inventory.** `oi_call` / `oi_put` are total open "
             "interest. Who is long or short, and therefore which way anyone must "
             "hedge, is not in this data. 'Amplifying' in M5 is a label for "
             "oi_put > oi_call, not a measured dealer position.")
    L.append("- **An OTM close can be an old print.** `px` is the 1-minute bar close; "
             "an illiquid far strike may not have traded in that minute, or that hour. "
             "Its sigma_K is then solved from a stale price, and the fallback count "
             "only catches the prices that are zero or unsolvable, not the stale ones.")
    L.append("- **The walls here use the study's sigma, not the vendor's.** "
             "`sigma_wall = S·sigma_atm·sqrt(max(dte_cal,1)/252)` reconstructs the "
             "Board's rule with sigma_atm solved from the straddle, where the live "
             "view uses `volatility_snapshots.atm_iv_avg`. The band shape is the "
             "same; the number is not the Board's. M2 is therefore about the rule, "
             "not about what the Board drew on any given day.")
    L.append("- Pins are computed on bars at 24 fixed minutes, not continuously, so "
             "M3 change counts and M4 windows are a 15-minute sampling of the path.")
    L.append("")
    return "\n".join(L) + "\n", screen


# ------------------------------------------------------------------ worked examples
EXAMPLES = [("NIFTY", "2025-04-01", "12:30"), ("NIFTY", "2025-04-03", "14:30"),
            ("SENSEX", "2026-03-02", "12:30"), ("SENSEX", "2025-04-08", "14:30")]


def worked(runs) -> str:
    idx = {(r["sym"], r["day"], r["tname"]): r for r in runs}
    L = ["lookback_v5 WORKED EXAMPLES", "=" * 74, ""]
    for sym, day, tn in EXAMPLES:
        r = idx.get((sym, day, tn))
        L.append(f"--- {sym} {day} {tn} " + "-" * 40)
        if r is None:
            L.append("  NOT PRESENT in the pull")
            L.append("")
            continue
        if not r["valid"]:
            L.append(f"  INVALID: {r['reason']}")
            L.append("")
            continue
        L.append(f"  S           = {r['S']:.2f}")
        L.append(f"  F           = {r['F']:.4f}")
        L.append(f"  ATM         = {r['atm']:.0f}   (sigma_atm solved at "
                 f"K={r['atm_k']:.0f})")
        L.append(f"  sigma_atm   = {r['sigma_atm']:.6f}")
        L.append(f"  T           = {r['t_min']} minutes  ({r['T']:.8f} yr)")
        L.append(f"  sigma_rem   = {r['sigma_rem']:.2f}  (points)")
        L.append(f"  dte_cal     = {r['dte_cal']}    dte_sess = {r['dte_sess']} "
                 f"(bucket {r['bucket']})   expiry {r['expiry']}")
        L.append(f"  sigma_wall  = {r['sigma_wall']:.2f}   band +/-"
                 f"{1.5 * r['sigma_wall']:.2f}   eligible strikes {r['n_eligible']}")
        L.append(f"  put_wall    = {r['put_wall']}   call_wall = {r['call_wall']}"
                 + ("   (UNDEFINED)" if not r["wall_defined"] else "")
                 + ("   (INVERTED)" if r["wall_inverted"] else ""))
        L.append(f"  strikes     = {r['n_strikes']}   fallback legs = "
                 f"{r['n_fallback']} ({100 * r['fallback_share']:.1f} %)")
        L.append("")
        L.append(f"  {'pin':<5}{'g: strike':>12}{'share':>9}{'lead':>9}"
                 f"{'g_flat: strike':>17}{'share':>9}{'lead':>9}")
        for pin in PINS:
            L.append(f"  {pin:<5}{r[f'{pin}_g']:>12.0f}"
                     f"{r[f'{pin}_g_share']:>9.4f}{r[f'{pin}_g_lead']:>9.4f}"
                     f"{r[f'{pin}_g_flat']:>17.0f}"
                     f"{r[f'{pin}_g_flat_share']:>9.4f}"
                     f"{r[f'{pin}_g_flat_lead']:>9.4f}")
        L.append("")
        sc = pin_scores(r["g"], r["_rows"], r["S"], r["sigma_rem"], "T")
        tot = sum(sc.values())
        top = sorted(sc.items(), key=lambda kv: (kv[1], -abs(kv[0] - r["S"]), -kv[0]),
                     reverse=True)[:5]
        L.append("  top 5 strikes by T score under the primary gamma:")
        L.append(f"    {'K':>9}{'oi_call':>12}{'oi_put':>12}{'sigma_K':>10}"
                 f"{'g_K':>12}{'g_flat_K':>12}{'score_share':>13}")
        for K, v in top:
            L.append(f"    {K:>9.0f}{r['_rows'][K]['c_oi']:>12.0f}"
                     f"{r['_rows'][K]['p_oi']:>12.0f}{r['sigma_k'][K]:>10.4f}"
                     f"{r['g'][K]:>12.4e}{r['g_flat'][K]:>12.4e}"
                     f"{v / tot * 100:>12.2f}%")
        L.append("")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ csv
def write_csv(runs) -> None:
    cols = ["symbol", "day", "tname", "valid", "reason", "S", "F", "ATM",
            "sigma_atm", "T_minutes", "dte_cal", "dte_sess", "bucket",
            "sigma_wall", "put_wall", "call_wall", "wall_defined", "wall_inverted",
            "n_strikes", "n_fallback", "fallback_share", "sigma_atm_further"]
    for g in GAMMAS:
        for p in PINS:
            cols += [f"{p}_{g}", f"{p}_{g}_share", f"{p}_{g}_lead"]
    with (HERE / "runs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in runs:
            row = [r["sym"], r["day"], r["tname"], int(r["valid"]), r["reason"],
                   f"{r['S']:.2f}",
                   f"{r['F']:.4f}" if r.get("F") else "",
                   f"{r['atm']:.0f}",
                   f"{r['sigma_atm']:.6f}" if r.get("sigma_atm") else "",
                   r["t_min"], r["dte_cal"], r["dte_sess"], r["bucket"],
                   f"{r['sigma_wall']:.4f}" if r.get("sigma_wall") else "",
                   r.get("put_wall") or "", r.get("call_wall") or "",
                   int(bool(r.get("wall_defined"))), int(bool(r.get("wall_inverted"))),
                   r["n_strikes"], r["n_fallback"],
                   f"{r.get('fallback_share', 0):.6f}", r["sigma_atm_further"]]
            for g in GAMMAS:
                for p in PINS:
                    k = r.get(f"{p}_{g}")
                    row += [f"{k:.0f}" if k else "",
                            f"{r.get(f'{p}_{g}_share', float('nan')):.6f}",
                            f"{r.get(f'{p}_{g}_lead', float('nan')):.6f}"]
            w.writerow(row)


# ------------------------------------------------------------------ main
def main(argv) -> int:
    phase = "full"
    if len(argv) > 1 and argv[1] in ("selftest", "full"):
        phase = argv[1]

    ok, txt = self_tests()
    (HERE / "self_test.txt").write_text(txt, encoding="utf-8")
    if not ok:
        sys.stdout.write(txt)
        print("exit 3: self-tests failed; nothing else ran")
        return 3

    good, why = precondition()
    if not good:
        print(f"exit 2: precondition failed -- {why}")
        return 2
    print(f"precondition OK: {why}")

    runs, r2map, q, _sess = load_runs()
    print(f"runs loaded: {len(runs)} ({sum(1 for r in runs if r['valid'])} valid)")

    (HERE / "worked_examples.txt").write_text(worked(runs), encoding="utf-8")
    if phase == "selftest":
        print("phase=selftest: self_test.txt and worked_examples.txt written; "
              "stopping before the measures")
        return 0

    write_csv(runs)
    md, screen = measures(runs, r2map, q)
    (HERE / "results.md").write_text(md, encoding="utf-8")
    (OUT / "_screen.json").write_text(json.dumps(screen, indent=1, default=str),
                                      encoding="utf-8")
    print("results.md, runs.csv written")
    print("ANALYSIS DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
