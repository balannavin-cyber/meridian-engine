#!/usr/bin/env python3
"""MR-PIN2 step 3 -- gamma rate sensitivity. Gates G0/G1, then the r_m sensitivity.

READ-ONLY on everything except the files it writes under sens/:
  gates.md, results.md, per_minute.csv, per_day.csv, _sens_analysis.txt (stdout tee).

INPUTS (no database access in this script):
  _qS_<sym>_<day>.txt   24 files, written by run_sens.sh through bin/roq.sh
  _partH_rerun.txt      the Part H selection, byte-identical to the sealed
                        _partH_analysis.txt, for F / volume / fut_dte per minute
  bs_backfill_copy.py   the backfill's OWN solver, extracted verbatim by
                        extract_bs_copy.py -- NOT core/bs_engine.py (conventions.md)

ORDER IS LOAD-BEARING: G0 and G1 are computed and gates.md is written BEFORE any
futures price is read from _partH_rerun.txt. The Part H loader is not called until after
the gate verdict, so a gate failure cannot be followed by a rate computation.
"""
import json
import math
import statistics as st
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from bs_backfill_copy import (  # noqa: E402  the backfill's own solver, verbatim
    IV_HI, IV_LO, IV_MX, IV_TOL, R_FLAT, bs_gamma_vec, bs_price_vec, implied_vol_vec,
    norm_pdf,
)

DAYS = {
    "NIFTY": ["2025-04-01", "2025-05-02", "2025-06-02", "2025-07-01", "2025-08-01",
              "2025-09-01", "2025-10-01", "2025-11-03", "2025-12-01", "2026-01-01",
              "2026-02-01", "2026-03-04"],
    "SENSEX": ["2025-04-02", "2025-05-02", "2025-06-02", "2025-07-02", "2025-08-01",
               "2025-09-01", "2025-10-03", "2025-11-03", "2025-12-01", "2026-01-02",
               "2026-02-01", "2026-03-02"],
}
SYMS = ("NIFTY", "SENSEX")
MINUTES = ("10:00", "12:30", "15:00")
BAND_LO, BAND_HI = 0.95, 1.05

# Part B's published per-day W1 medians (partB_results.md:99-114). An expected value
# read from the sealed document, not from re-running the thing -- so comparing to it is
# an assertion. G0 is judged on the in-band COUNT; this is the stronger side-check.
PARTB_MEDIAN = {
    "NIFTY": {"2025-04-01": 0.8976, "2025-05-02": 1.1066, "2025-06-02": 0.9641,
              "2025-07-01": 0.9428, "2025-08-01": 1.0883, "2025-09-01": 0.8817,
              "2025-10-01": 0.9090, "2025-11-03": 0.8116, "2025-12-01": 0.9898,
              "2026-01-01": 1.0427, "2026-02-01": 1.0203, "2026-03-04": 1.0094},
    "SENSEX": {"2025-04-02": 0.9819, "2025-05-02": 1.1340, "2025-06-02": 1.0030,
               "2025-07-02": 1.0613, "2025-08-01": 1.0830, "2025-09-01": 0.8380,
               "2025-10-03": 0.9564, "2025-11-03": 0.7816, "2025-12-01": 0.8966,
               "2026-01-02": 0.9883, "2026-02-01": 1.0025, "2026-03-02": 0.9827},
}
PARTB_INBAND = {"NIFTY": 5, "SENSEX": 6}

OUT = []


def say(s=""):
    print(s)
    OUT.append(s)


def pct(x, q):
    return float(np.percentile(np.asarray(x, dtype=float), q)) if len(x) else float("nan")


# ---------------------------------------------------------------- load the 24 payloads
def load_minutes():
    """-> {(sym, day, minute): {spot, expiry, dte, legs:{(strike,ot): leg}}}"""
    m = {}
    for sym in SYMS:
        for day in DAYS[sym]:
            p = HERE / f"_qS_{sym}_{day}.txt"
            s0 = s1 = 0
            for line in p.read_text().splitlines():
                if not line or "|" not in line:
                    continue
                tag, payload = line.split("|", 1)
                r = json.loads(payload)
                k = (sym, day, r["tname"])
                if tag == "S0":
                    s0 += 1
                    m[k] = {"spot": float(r["spot"]), "expiry": r["expiry"],
                            "dte": int(r["dte_opt"]), "legs": {}}
                elif tag == "S1":
                    s1 += 1
                    iv = None if r["iv_txt"] is None else float(r["iv_txt"])
                    ga = None if r["gamma_txt"] is None else float(r["gamma_txt"])
                    m[k]["legs"][(float(r["strike"]), r["ot"])] = {
                        "strike": float(r["strike"]), "ot": r["ot"],
                        "px": float(r["px"]), "oi": float(r["oi"]),
                        "iv": iv, "gamma": ga, "dte": int(r["dte_opt"])}
            assert s0 == 3, f"{sym} {day}: S0 rows {s0} != 3"
            assert s1 > 0, f"{sym} {day}: no S1 rows"
    assert len(m) == 72, f"minutes loaded {len(m)} != 72"
    return m


def build_pairs(mins, lo, hi):
    """Pair set: front-expiry strikes with |K/S-1| in (lo, hi], stored CE gamma > 0 AND
    stored PE gamma > 0. Part B B3 definition (conventions.md). FIXED here and reused
    unchanged by every later step."""
    out = {}
    for k, v in mins.items():
        S = v["spot"]
        got = []
        strikes = sorted({s for s, _ in v["legs"]})
        for K in strikes:
            mny = abs(K / S - 1.0)
            if not (lo < mny <= hi):
                continue
            c = v["legs"].get((K, "CE"))
            p = v["legs"].get((K, "PE"))
            if not c or not p:
                continue
            if c["gamma"] is None or p["gamma"] is None:
                continue
            if not (c["gamma"] > 0 and p["gamma"] > 0):
                continue
            got.append((K, c, p))
        out[k] = got
    return out


def day_median_ratio(pairs, sym, day, minutes, key_c="gamma", key_p="gamma"):
    """Part B pooling: the day's minutes pooled into ONE list of per-strike ratios."""
    vals = []
    for mn in minutes:
        for K, c, p in pairs.get((sym, day, mn), []):
            a, b = c[key_c], p[key_p]
            if a is None or b is None or b == 0:
                continue
            vals.append(a / b)
    return (st.median(vals) if vals else None), len(vals)


def in_band(x):
    return x is not None and BAND_LO <= x <= BAND_HI


# ------------------------------------------------------------------------- the re-solve
def resolve(S, T, r, legs):
    """One vector call per minute, exactly as backfill_hist_greeks.solve_bar:301-303.
    Returns (sig, gamma, resid, vega) arrays aligned with `legs`."""
    K = np.array([l["strike"] for l in legs], dtype=float)
    P = np.array([l["px"] for l in legs], dtype=float)
    is_call = np.array([l["ot"].upper().startswith("C") for l in legs])
    sig = implied_vol_vec(P, S, K, T, r, is_call)
    gam = bs_gamma_vec(S, K, T, r, sig)
    gam = np.where(np.isnan(sig), np.nan, gam)
    # residual: < IV_TOL means the bisection returned on the tolerance, not on budget
    px = bs_price_vec(S, K, T, r, np.where(np.isnan(sig), 1.0, sig), is_call)
    resid = np.where(np.isnan(sig), np.nan, np.abs(px - P))
    # vega per UNIT sigma, for the IV_TOL noise floor: S*sqrt(T)*phi(d1)
    with np.errstate(all="ignore"):
        sq = math.sqrt(T)
        s_ok = np.where(np.isnan(sig) | (sig <= 0), np.nan, sig)
        d1 = (np.log(S / K) + (r + 0.5 * s_ok * s_ok) * T) / (s_ok * sq)
        vega = S * sq * norm_pdf(d1)
    return sig, gam, resid, vega


def resolve_pairs(pairs, keys, r):
    """Re-solve every leg of the pair set at rate r (scalar) or per-minute r (dict).
    Returns {key: [(K, c_sig, c_gam, p_sig, p_gam)]}, plus counters."""
    res, n_legs, n_fail, noise, budget = {}, 0, 0, [], 0
    for k in keys:
        prs = pairs.get(k, [])
        if not prs:
            res[k] = []
            continue
        sym, day, mn = k
        rr = r if isinstance(r, float) else r.get(k)
        if rr is None:
            res[k] = []
            continue
        legs = []
        for K, c, p in prs:
            legs.append(c)
            legs.append(p)
        S = MINS[k]["spot"]
        T = MINS[k]["dte"] / 365.0
        sig, gam, resid, vega = resolve(S, T, rr, legs)
        n_legs += len(legs)
        n_fail += int(np.sum(np.isnan(sig)))
        budget += int(np.sum(~np.isnan(sig) & ~(resid < IV_TOL)))
        with np.errstate(all="ignore"):
            nf = 100.0 * IV_TOL / vega
        noise += [float(x) for x in nf if np.isfinite(x)]
        row = []
        for i, (K, c, p) in enumerate(prs):
            ci, pi = 2 * i, 2 * i + 1
            row.append((K, float(sig[ci]), float(gam[ci]),
                        float(sig[pi]), float(gam[pi])))
        res[k] = row
    return res, n_legs, n_fail, noise, budget


def day_median_resolved(res, sym, day, minutes, which):
    """which='gamma' -> call gamma / put gamma; 'iv' -> call sigma / put sigma."""
    vals = []
    for mn in minutes:
        for K, cs, cg, ps, pg in res.get((sym, day, mn), []):
            a, b = (cg, pg) if which == "gamma" else (cs, ps)
            if not (np.isfinite(a) and np.isfinite(b)) or b == 0:
                continue
            vals.append(a / b)
    return (st.median(vals) if vals else None), len(vals)


# ------------------------------------------------- STEP 1d precondition on the run log
def check_run_log():
    """Assert STEP 1d's precondition in code instead of by hand.

    Aborts with exit 2 unless BOTH hold:
      (a) the last line of _sens_run.log is exactly 'ALL 24 DONE';
      (b) the log holds exactly 24 OK lines whose (symbol, day) pairs equal the 24 days
          of run_sens.sh, NIFTY by date then SENSEX by date, each with s0=3 and s1>0.

    WHAT MAKES IT FAIL (so this is a check, not documentation -- Rule 0): a loop that
    stopped early writes INCOMPLETE as its last line and fails (a); a log left over from
    a shorter or differently-ordered run fails (b) on the count or the pair list; a day
    that resolved only two minutes fails on s0 != 3; a day whose +/-3 % band came back
    empty fails on s1 == 0. A stale set of 24 _qS_*.txt files on disk from an earlier
    run would satisfy load_minutes() and is caught only here, by the log.
    """
    p = HERE / "_sens_run.log"
    if not p.exists():
        print(f"ABORT: {p} does not exist")
        sys.exit(2)
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    last = lines[-1] if lines else "<empty>"
    if last != "ALL 24 DONE":
        print(f"ABORT: last log line is {last!r}, expected 'ALL 24 DONE'")
        sys.exit(2)
    expected = [(s, d) for s in SYMS for d in DAYS[s]]
    got, bad = [], []
    for l in lines:
        f = l.split()
        if not f or f[0] != "OK":
            continue
        if len(f) < 7:
            bad.append(f"malformed OK line: {l!r}")
            continue
        got.append((f[1], f[2]))
        s0 = f[5].split("=", 1)[1] if "=" in f[5] else "?"
        s1 = f[6].split("=", 1)[1] if "=" in f[6] else "?"
        if s0 != "3":
            bad.append(f"{f[1]} {f[2]}: s0={s0}, expected 3")
        if not (s1.isdigit() and int(s1) > 0):
            bad.append(f"{f[1]} {f[2]}: s1={s1}, expected > 0")
    if len(got) != 24:
        bad.append(f"OK lines {len(got)}, expected 24")
    if got != expected:
        missing = [x for x in expected if x not in got]
        extra = [x for x in got if x not in expected]
        bad.append(f"(symbol, day) pairs do not match run_sens.sh in order; "
                   f"missing {missing}, unexpected {extra}")
    if bad:
        print("ABORT: _sens_run.log precondition failed:")
        for b in bad:
            print("  " + b)
        sys.exit(2)
    print(f"precondition OK: last line 'ALL 24 DONE'; 24 OK lines, pairs match "
          f"run_sens.sh in order, every day s0=3 and s1>0")


# ================================================================== load, pairs, gates
check_run_log()          # first executable statement: before any other read
MINS = load_minutes()
PAIRS_W1 = build_pairs(MINS, -1.0, 0.01)      # within 1 % of spot  -- the gate input
PAIRS_W13 = build_pairs(MINS, 0.01, 0.03)     # 1-3 % band          -- descriptive only
ALL_KEYS = [(s, d, m) for s in SYMS for d in DAYS[s] for m in MINUTES]

say("=" * 78)
say("MR-PIN2 step 3 -- gamma rate sensitivity")
say("=" * 78)
say(f"minutes loaded: {len(MINS)}; solver: bs_backfill_copy (backfill's own), "
    f"R_FLAT={R_FLAT}, IV_LO={IV_LO}, IV_HI={IV_HI}, IV_TOL={IV_TOL}, IV_MX={IV_MX}")
say()

# ---- G0: reproduce Part B from STORED gamma ----
say("### G0 -- reproduce Part B B3 per-day median from STORED gamma")
say("sym|day|median_stored|pairs|in_band|partB_published|abs_diff")
g0 = {}
g0_match = {}
for sym in SYMS:
    nb = 0
    mism = 0
    for day in DAYS[sym]:
        med, n = day_median_ratio(PAIRS_W1, sym, day, MINUTES)
        g0[(sym, day)] = (med, n)
        ib = in_band(med)
        nb += int(ib)
        pub = PARTB_MEDIAN[sym][day]
        dif = abs(med - pub) if med is not None else float("nan")
        if not (dif <= 1e-4):
            mism += 1
        say(f"{sym}|{day}|{med:.4f}|{n}|{'YES' if ib else 'NO'}|{pub:.4f}|{dif:.6f}")
    g0_match[sym] = (nb, mism)

g0_pass = True
for sym in SYMS:
    nb, mism = g0_match[sym]
    ok = (nb == PARTB_INBAND[sym]) and (mism == 0)
    g0_pass = g0_pass and ok
    say(f"G0 {'PASS' if ok else 'FAIL'} {sym}: in-band {nb} of 12 "
        f"(Part B {PARTB_INBAND[sym]} of 12); per-day medians differing from the "
        f"published value by > 1e-4: {mism}")
say(f"G0 {'PASS' if g0_pass else 'FAIL'} (both symbols)")
say()

# ---- G1: replicate the stored solve at r = 0.065 ----
say("### G1 -- re-solve the pair set at r = 0.065 and compare with what is stored")
R1, g1_legs, g1_fail, g1_noise, g1_budget = resolve_pairs(PAIRS_W1, ALL_KEYS, float(R_FLAT))
g1_rows, worst = [], []
per_sym = {s: {"n": 0, "ok": 0, "gmiss": [], "ivmiss": [], "noise": [], "bud": 0,
               "fail": 0} for s in SYMS}
for k in ALL_KEYS:
    sym, day, mn = k
    stored = {K: (c, p) for K, c, p in PAIRS_W1.get(k, [])}
    for K, cs, cg, ps, pg in R1.get(k, []):
        c, p = stored[K]
        for side, (sig_r, gam_r, leg) in (("CE", (cs, cg, c)), ("PE", (ps, pg, p))):
            per_sym[sym]["n"] += 1
            if not np.isfinite(gam_r) or not np.isfinite(sig_r):
                per_sym[sym]["fail"] += 1
                worst.append((9e9, sym, day, mn, K, side, leg["gamma"], gam_r,
                              leg["iv"], sig_r))
                continue
            gm = abs(gam_r / leg["gamma"] - 1.0) if leg["gamma"] else float("inf")
            im = abs(100.0 * (sig_r - leg["iv"])) if leg["iv"] is not None else float("inf")
            per_sym[sym]["gmiss"].append(gm)
            per_sym[sym]["ivmiss"].append(im)
            if gm <= 0.005 and im <= 0.05:
                per_sym[sym]["ok"] += 1
            worst.append((gm, sym, day, mn, K, side, leg["gamma"], gam_r, leg["iv"], sig_r))

# noise floor and budget-exhaust, per symbol
NOISE, BUDGET = {}, {}
for sym in SYMS:
    keys = [(sym, d, m) for d in DAYS[sym] for m in MINUTES]
    _, nl, nf, noise, bud = resolve_pairs(PAIRS_W1, keys, float(R_FLAT))
    NOISE[sym] = noise
    BUDGET[sym] = (bud, nl)

say("sym|legs|inside_tol|share|gamma_miss_p50|p90|max|iv_miss_vp_p50|p90|max|solver_fail")
g1a = {}
for sym in SYMS:
    d = per_sym[sym]
    share = d["ok"] / d["n"] if d["n"] else 0.0
    g1a[sym] = share >= 0.99
    say(f"{sym}|{d['n']}|{d['ok']}|{share*100:.3f}%|"
        f"{pct(d['gmiss'],50):.3e}|{pct(d['gmiss'],90):.3e}|{max(d['gmiss']):.3e}|"
        f"{pct(d['ivmiss'],50):.3e}|{pct(d['ivmiss'],90):.3e}|{max(d['ivmiss']):.3e}|"
        f"{d['fail']}")

say()
say("### G1(b) -- per-day median ratio, stored vs re-solved at r = 0.065")
say("sym|day|median_stored|median_resolved|abs_diff|within_0.005")
g1b = {}
for sym in SYMS:
    bad = 0
    for day in DAYS[sym]:
        ms, _ = g0[(sym, day)]
        mr, _ = day_median_resolved(R1, sym, day, MINUTES, "gamma")
        dif = abs(mr - ms) if (mr is not None and ms is not None) else float("nan")
        okd = dif <= 0.005
        bad += int(not okd)
        say(f"{sym}|{day}|{ms:.6f}|{mr:.6f}|{dif:.2e}|{'YES' if okd else 'NO'}")
    g1b[sym] = (bad == 0)

say()
say("### G1 -- 10 worst legs by |gamma_resolved/gamma_stored - 1|")
say("rank|sym|day|minute|strike|side|gamma_stored|gamma_resolved|iv_stored|iv_resolved|rel")
for i, w in enumerate(sorted(worst, key=lambda x: -x[0])[:10], 1):
    gm, sym, day, mn, K, side, gs, gr, ivs, ivr = w
    say(f"{i}|{sym}|{day}|{mn}|{K:.0f}|{side}|{gs!r}|{gr:.12g}|{ivs!r}|{ivr:.12g}|"
        f"{'SOLVER FAIL' if gm >= 9e9 else f'{gm:.3e}'}")

say()
say("### G1 -- IV_TOL noise floor, 100*IV_TOL/vega in vol points, pair-set legs at r=0.065")
say("sym|legs|vp_p50|vp_p90|vp_max|returned_on_budget_not_tolerance")
for sym in SYMS:
    nz = NOISE[sym]
    bud, nl = BUDGET[sym]
    say(f"{sym}|{len(nz)}|{pct(nz,50):.4f}|{pct(nz,90):.4f}|{max(nz):.4f}|{bud} of {nl}")

g1_pass = all(g1a[s] and g1b[s] for s in SYMS)
say()
for sym in SYMS:
    ok = g1a[sym] and g1b[sym]
    say(f"G1 {'PASS' if ok else 'FAIL'} {sym}: (a) share inside tolerance "
        f"{per_sym[sym]['ok']/per_sym[sym]['n']*100:.3f}% (need >= 99%), "
        f"(b) all 12 per-day medians within 0.005: "
        f"{'yes' if g1b[sym] else 'no'}")

# the clause that fires on a convention mismatch regardless of verdict
CONV_NOTE = ""
near_half_pct = {s: sum(1 for g in per_sym[s]["gmiss"] if 0.002 <= g <= 0.02)
                 for s in SYMS}
if any(near_half_pct[s] > 0 for s in SYMS):
    CONV_NOTE = ("convention mismatch suspected -- iv and gamma are stored at full "
                 f"precision (0c) yet legs miss by ~0.5%: counts in [0.2%, 2%] "
                 f"NIFTY {near_half_pct['NIFTY']}, SENSEX {near_half_pct['SENSEX']}")
    say(CONV_NOTE)

# --------------------------------------------------------------------- write gates.md
gl = []
gl.append("# MR-PIN2 step 3 — gates G0 and G1\n")
gl.append("Pair set, **fixed here and reused unchanged in step 3**: front-expiry strikes "
          "within 1 % of spot (Part B B3 band and definition) carrying stored call "
          "gamma > 0 **and** put gamma > 0. Per-day median pools the day's three "
          "minutes' per-strike ratios into one list (conventions.md).\n")
gl.append("Solver: the backfill's own `implied_vol_vec` / `bs_gamma_vec`, extracted "
          "verbatim by `extract_bs_copy.py` into `bs_backfill_copy.py` — **not** "
          "`core/bs_engine.py`, which the backfill never calls.\n")
gl.append("## G0 — reproduce Part B from stored gamma\n")
gl.append("| sym | day | median stored | pairs | in band | Part B published | abs diff |")
gl.append("|---|---|---|---|---|---|---|")
for sym in SYMS:
    for day in DAYS[sym]:
        med, n = g0[(sym, day)]
        pub = PARTB_MEDIAN[sym][day]
        gl.append(f"| {sym} | {day} | {med:.4f} | {n} | "
                  f"{'YES' if in_band(med) else 'NO'} | {pub:.4f} | "
                  f"{abs(med-pub):.6f} |")
gl.append("")
for sym in SYMS:
    nb, mism = g0_match[sym]
    gl.append(f"**G0 {'PASS' if (nb == PARTB_INBAND[sym] and mism == 0) else 'FAIL'} "
              f"{sym}** — in-band {nb} of 12, Part B {PARTB_INBAND[sym]} of 12; "
              f"per-day medians off the published value by > 1e-4: {mism}.")
gl.append("")
gl.append("## G1 — replicate the stored solve at r = 0.065\n")
gl.append("| sym | legs | inside tol | share | γ miss p50 | p90 | max | "
          "IV miss (vp) p50 | p90 | max | solver fail |")
gl.append("|---|---|---|---|---|---|---|---|---|---|---|")
for sym in SYMS:
    d = per_sym[sym]
    gl.append(f"| {sym} | {d['n']} | {d['ok']} | {d['ok']/d['n']*100:.3f} % | "
              f"{pct(d['gmiss'],50):.2e} | {pct(d['gmiss'],90):.2e} | "
              f"{max(d['gmiss']):.2e} | {pct(d['ivmiss'],50):.2e} | "
              f"{pct(d['ivmiss'],90):.2e} | {max(d['ivmiss']):.2e} | {d['fail']} |")
gl.append("")
gl.append("| sym | day | median stored | median re-solved | abs diff | within 0.005 |")
gl.append("|---|---|---|---|---|---|")
for sym in SYMS:
    for day in DAYS[sym]:
        ms, _ = g0[(sym, day)]
        mr, _ = day_median_resolved(R1, sym, day, MINUTES, "gamma")
        gl.append(f"| {sym} | {day} | {ms:.6f} | {mr:.6f} | {abs(mr-ms):.2e} | "
                  f"{'YES' if abs(mr-ms) <= 0.005 else 'NO'} |")
gl.append("")
gl.append("### IV_TOL noise floor (conventions.md)\n")
gl.append("`100 * IV_TOL / vega` in vol points, every pair-set leg at r = 0.065. "
          "No figure is asserted a priori; these are measured.\n")
gl.append("| sym | legs | vp p50 | vp p90 | vp max | returned on budget, not tolerance |")
gl.append("|---|---|---|---|---|---|")
for sym in SYMS:
    bud, nl = BUDGET[sym]
    gl.append(f"| {sym} | {len(NOISE[sym])} | {pct(NOISE[sym],50):.4f} | "
              f"{pct(NOISE[sym],90):.4f} | {max(NOISE[sym]):.4f} | {bud} of {nl} |")
gl.append("")
for sym in SYMS:
    gl.append(f"**G1 {'PASS' if (g1a[sym] and g1b[sym]) else 'FAIL'} {sym}** — "
              f"(a) {per_sym[sym]['ok']/per_sym[sym]['n']*100:.3f} % of legs inside "
              f"|Δγ/γ| ≤ 0.005 and |ΔIV| ≤ 0.05 vol points (need ≥ 99 %); "
              f"(b) all 12 per-day medians within 0.005: "
              f"{'yes' if g1b[sym] else 'no'}.")
if CONV_NOTE:
    gl.append("")
    gl.append("**" + CONV_NOTE + "**")
gl.append("")
gl.append(f"**Gate outcome: G0 {'PASS' if g0_pass else 'FAIL'}, "
          f"G1 {'PASS' if g1_pass else 'FAIL'}.** "
          + ("Step 3 proceeds." if (g0_pass and g1_pass) else
             "Step 3 does NOT run; the task stops here by design."))
(HERE / "gates.md").write_text("\n".join(gl) + "\n", encoding="utf-8")

if not (g0_pass and g1_pass):
    say()
    say("STOP: a gate failed. gates.md written; no futures price read, no r_m computed.")
    (HERE / "_sens_analysis.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
    sys.exit(1)

# =================================================================== STEP 3 -- the rate
# Only now is a futures price read.
def load_partH():
    """F, volume, fut_dte and the ZERO_VOLUME flag per (sym, day, minute)."""
    out = {}
    for line in (HERE / "_partH_rerun.txt").read_text().splitlines():
        f = line.split("|")
        if len(f) != 10 or f[3] != "present":
            continue
        sym, day, mn, _, contract, expiry, fut_dte, close, vol, flags = f
        out[(sym, day, mn)] = {
            "contract": contract, "fut_expiry": expiry, "fut_dte": int(fut_dte),
            "F": float(close), "vol": int(vol),
            "zero_vol": "ZERO_VOLUME" in flags}
    return out


PH = load_partH()
assert len(PH) == 72, f"Part H minutes {len(PH)} != 72"

# ---- 3a: r_m = ln(F/S) / T_fut ----
RM, FLAGGED = {}, []
for k, h in PH.items():
    S = MINS[k]["spot"]
    t_fut = h["fut_dte"] / 365.0
    r_m = math.log(h["F"] / S) / t_fut
    RM[k] = r_m
    if not (-0.05 <= r_m <= 0.20):
        FLAGGED.append((k, r_m))

say()
say("### 3a -- r_m = ln(F/S)/T_fut, in % a year")
say("sym|minutes|r_m_median_pct|min_pct|max_pct|flagged_outside_-5_to_+20")
RM_STATS = {}
for sym in SYMS:
    v = [RM[(sym, d, m)] for d in DAYS[sym] for m in MINUTES]
    RM_STATS[sym] = (st.median(v), min(v), max(v))
    nfl = sum(1 for (k, _) in FLAGGED if k[0] == sym)
    say(f"{sym}|{len(v)}|{st.median(v)*100:.4f}|{min(v)*100:.4f}|{max(v)*100:.4f}|{nfl}")
if FLAGGED:
    for (k, r) in FLAGGED:
        say(f"FLAG r_m outside [-5%, +20%]: {k[0]} {k[1]} {k[2]} r_m={r*100:.4f}%")
else:
    say("no r_m outside [-5 %, +20 %]")

# ---- 3b: re-solve at r = r_m ----
R3, n3_legs, n3_fail, _, _ = resolve_pairs(PAIRS_W1, ALL_KEYS, RM)
FAIL_SYM = {s: [0, 0] for s in SYMS}
for k in ALL_KEYS:
    sym = k[0]
    for K, cs, cg, ps, pg in R3.get(k, []):
        for sig in (cs, ps):
            FAIL_SYM[sym][1] += 1
            if not np.isfinite(sig):
                FAIL_SYM[sym][0] += 1

# ---- 3c: verdict minutes = futures bar volume > 0 ----
VMIN = {s: [k for k in ALL_KEYS if k[0] == s and PH[k]["vol"] > 0] for s in SYMS}
say()
say("### 3c -- verdict minutes (futures bar volume > 0)")
VDAYS = {}
for sym in SYMS:
    keep = VMIN[sym]
    VDAYS[sym] = [d for d in DAYS[sym] if any(k[1] == d for k in keep)]
    say(f"{sym}: verdict minutes {len(keep)} of 36; days with >= 1 verdict minute "
        f"{len(VDAYS[sym])} of 12")
SENSEX_UNMEASURED = len(VDAYS["SENSEX"]) < 10
if SENSEX_UNMEASURED:
    say("SENSEX UNMEASURED: fewer than 10 days have a verdict minute")

# ---- 3d: before/after per day, on verdict minutes ----
def minutes_of(sym, day, keys):
    return [k[2] for k in keys if k[0] == sym and k[1] == day]


say()
say("### 3d -- per day on verdict minutes: median call/put gamma and call/put IV")
say("sym|day|vmins|pairs|gamma_before|gamma_after|ib_before|ib_after|"
    "iv_before|iv_after")
D3 = {}
for sym in SYMS:
    for day in VDAYS[sym]:
        mns = minutes_of(sym, day, VMIN[sym])
        gb, npairs = day_median_ratio(PAIRS_W1, sym, day, mns)
        ga, _ = day_median_resolved(R3, sym, day, mns, "gamma")
        ivb, _ = day_median_ratio(PAIRS_W1, sym, day, mns, "iv", "iv")
        iva, _ = day_median_resolved(R3, sym, day, mns, "iv")
        D3[(sym, day)] = (gb, ga, ivb, iva, npairs, len(mns))
        say(f"{sym}|{day}|{len(mns)}|{npairs}|{gb:.4f}|{ga:.4f}|"
            f"{'Y' if in_band(gb) else 'N'}|{'Y' if in_band(ga) else 'N'}|"
            f"{ivb:.4f}|{iva:.4f}")

# ---- 3e: the verdict ----
say()
say("### 3e -- verdict per symbol")
VERDICT = {}
for sym in SYMS:
    n = len(VDAYS[sym])
    before_ib = [d for d in VDAYS[sym] if in_band(D3[(sym, d)][0])]
    after_ib = [d for d in VDAYS[sym] if in_band(D3[(sym, d)][1])]
    left = [d for d in before_ib if d not in after_ib]
    out_after = n - len(after_ib)
    allow = (2 * n) // 12
    f, legs = FAIL_SYM[sym]
    fail_share = f / legs if legs else 1.0
    if sym == "SENSEX" and SENSEX_UNMEASURED:
        v = "UNMEASURED"
    elif fail_share > 0.05:
        v = "UNMEASURED"
    elif out_after <= allow and not left:
        v = "PASS"
    else:
        v = "FAIL"
    VERDICT[sym] = (v, len(before_ib), len(after_ib), left, out_after, allow, f, legs)
    say(f"SENS {sym} {v}: in-band before {len(before_ib)}/{n}, after "
        f"{len(after_ib)}/{n}, left band {len(left)}, solver failures {f}/{legs}")
    if v == "FAIL":
        why = []
        if out_after > allow:
            why.append(f"out-of-band after {out_after} > floor(2n/12) = {allow}")
        if left:
            why.append(f"days leaving the band: {', '.join(left)}")
        say(f"  FAIL because: {'; '.join(why)}")

# ---- 3f: all-72, no verdict ----
say()
say("### 3f -- all 72 minutes, DESCRIPTIVE, no verdict")
say("sym|day|gamma_before|gamma_after|ib_before|ib_after|iv_before|iv_after")
A72 = {}
for sym in SYMS:
    for day in DAYS[sym]:
        gb, _ = day_median_ratio(PAIRS_W1, sym, day, MINUTES)
        ga, _ = day_median_resolved(R3, sym, day, MINUTES, "gamma")
        ivb, _ = day_median_ratio(PAIRS_W1, sym, day, MINUTES, "iv", "iv")
        iva, _ = day_median_resolved(R3, sym, day, MINUTES, "iv")
        A72[(sym, day)] = (gb, ga, ivb, iva)
        say(f"{sym}|{day}|{gb:.4f}|{ga:.4f}|{'Y' if in_band(gb) else 'N'}|"
            f"{'Y' if in_band(ga) else 'N'}|{ivb:.4f}|{iva:.4f}")
A72_IB = {s: (sum(1 for d in DAYS[s] if in_band(A72[(s, d)][0])),
              sum(1 for d in DAYS[s] if in_band(A72[(s, d)][1]))) for s in SYMS}
for sym in SYMS:
    say(f"{sym} all-72: in-band before {A72_IB[sym][0]}/12, after {A72_IB[sym][1]}/12")

SENSEX_ZV_NOTE = ""
if not SENSEX_UNMEASURED:
    v_after = VERDICT["SENSEX"][2]
    n_v = len(VDAYS["SENSEX"])
    met_verdict = (n_v - v_after) <= ((2 * n_v) // 12)
    met_all72 = A72_IB["SENSEX"][1] >= 10
    if met_verdict != met_all72:
        SENSEX_ZV_NOTE = "SENSEX: zero-volume minutes change the result"
        say(SENSEX_ZV_NOTE)
    else:
        say("SENSEX: verdict-minute and all-72 readings agree on the 10-of-12 bar")

# ---- 3g: control C-flat ----
say()
say("### 3g -- control C-flat: one flat rate per symbol = median r_m over verdict minutes")
CFLAT, CF_IB = {}, {}
for sym in SYMS:
    rs = [RM[k] for k in VMIN[sym]]
    rf = st.median(rs)
    CFLAT[sym] = rf
    keys = VMIN[sym]
    rc, _, _, _, _ = resolve_pairs(PAIRS_W1, keys, float(rf))
    nb = 0
    for day in VDAYS[sym]:
        mns = minutes_of(sym, day, keys)
        m, _ = day_median_resolved(rc, sym, day, mns, "gamma")
        nb += int(in_band(m))
    CF_IB[sym] = nb
    say(f"{sym}: C-flat r = {rf*100:.4f}% a year; in-band days on verdict minutes "
        f"{nb} of {len(VDAYS[sym])}")

# ---- 3h: descriptive 1-3 % band ----
say()
say("### 3h -- descriptive: the 1-3 % band, before and after (no verdict)")
R3B, _, _, _, _ = resolve_pairs(PAIRS_W13, ALL_KEYS, RM)
say("sym|pairs|gamma_before_pooled|gamma_after_pooled|ib_days_before|ib_days_after")
W13 = {}
for sym in SYMS:
    pb, pa, nb, na, npr = [], [], 0, 0, 0
    for day in DAYS[sym]:
        gb, n = day_median_ratio(PAIRS_W13, sym, day, MINUTES)
        ga, _ = day_median_resolved(R3B, sym, day, MINUTES, "gamma")
        npr += n
        if gb is not None:
            pb.append(gb)
            nb += int(in_band(gb))
        if ga is not None:
            pa.append(ga)
            na += int(in_band(ga))
    W13[sym] = (st.median(pb), st.median(pa), nb, na, npr)
    say(f"{sym}|{npr}|{st.median(pb):.4f}|{st.median(pa):.4f}|{nb}/12|{na}/12")

# ---- per_minute.csv (72 rows) and per_day.csv ----
pm = ["sym,day,minute,r_m_pct,F,S,fut_volume,zero_volume,fut_dte,T_fut,T_opt,"
      "dte_opt,pairs_w1,legs_w1,solver_fail_rm,verdict_minute,"
      "median_gamma_ratio_before,median_gamma_ratio_after,"
      "median_iv_ratio_before,median_iv_ratio_after"]
for k in ALL_KEYS:
    sym, day, mn = k
    h, S = PH[k], MINS[k]["spot"]
    prs = PAIRS_W1.get(k, [])
    rr = R3.get(k, [])
    nf = sum(1 for _, cs, _, ps, _ in rr
             for s in (cs, ps) if not np.isfinite(s))
    gb, _ = day_median_ratio(PAIRS_W1, sym, day, [mn])
    ga, _ = day_median_resolved(R3, sym, day, [mn], "gamma")
    ivb, _ = day_median_ratio(PAIRS_W1, sym, day, [mn], "iv", "iv")
    iva, _ = day_median_resolved(R3, sym, day, [mn], "iv")
    f = lambda x: "" if x is None or not np.isfinite(x) else f"{x:.6f}"
    pm.append(f"{sym},{day},{mn},{RM[k]*100:.6f},{h['F']:.2f},{S:.2f},{h['vol']},"
              f"{int(h['zero_vol'])},{h['fut_dte']},{h['fut_dte']/365.0:.8f},"
              f"{MINS[k]['dte']/365.0:.8f},{MINS[k]['dte']},{len(prs)},"
              f"{2*len(prs)},{nf},{int(PH[k]['vol'] > 0)},"
              f"{f(gb)},{f(ga)},{f(ivb)},{f(iva)}")
(HERE / "per_minute.csv").write_text("\n".join(pm) + "\n", encoding="utf-8")

pd_ = ["sym,day,verdict_minutes,pairs_verdict,gamma_before_verdict,gamma_after_verdict,"
       "ib_before_verdict,ib_after_verdict,iv_before_verdict,iv_after_verdict,"
       "gamma_before_all72,gamma_after_all72,ib_before_all72,ib_after_all72,"
       "median_stored_g0,partB_published"]
for sym in SYMS:
    for day in DAYS[sym]:
        gb72, ga72, ivb72, iva72 = A72[(sym, day)]
        if (sym, day) in D3:
            gb, ga, ivb, iva, npairs, nm = D3[(sym, day)]
            row = (f"{nm},{npairs},{gb:.6f},{ga:.6f},{int(in_band(gb))},"
                   f"{int(in_band(ga))},{ivb:.6f},{iva:.6f}")
        else:
            row = "0,0,,,,,,"
        pd_.append(f"{sym},{day},{row},{gb72:.6f},{ga72:.6f},"
                   f"{int(in_band(gb72))},{int(in_band(ga72))},"
                   f"{g0[(sym, day)][0]:.6f},{PARTB_MEDIAN[sym][day]:.4f}")
(HERE / "per_day.csv").write_text("\n".join(pd_) + "\n", encoding="utf-8")

# ------------------------------------------------------------------- results.md
rl = []
rl.append("# MR-PIN2 step 3 — results: does a futures-implied rate bring call and put "
          "gamma together?\n")
rl.append("Claim tested: the flat `r = 6.5 %` is the main cause of Part B's call/put "
          "gamma disagreement, and re-solving each leg at a rate implied by the Fyers "
          "near-month futures should bring the two together at one strike.\n")
rl.append("Read-only. No database write, no vendor call, no outcome computed — nothing "
          "here reads a price after a sampled minute. Gates in `gates.md`, conventions "
          "and the solver provenance in `conventions.md`, per-minute inputs in "
          "`per_minute.csv`, per-day numbers in `per_day.csv`.\n")
rl.append("## Verdicts\n")
for sym in SYMS:
    v, b, a, left, oa, allow, f, legs = VERDICT[sym]
    n = len(VDAYS[sym])
    rl.append(f"**SENS {sym} {v}: in-band before {b}/{n}, after {a}/{n}, left band "
              f"{len(left)}, solver failures {f}/{legs}.**")
rl.append("")
rl.append("r_m per symbol (% a year): " + "; ".join(
    f"{s} median {RM_STATS[s][0]*100:.4f}, min {RM_STATS[s][1]*100:.4f}, "
    f"max {RM_STATS[s][2]*100:.4f}" for s in SYMS) + ".")
rl.append("")
rl.append(f"Flagged r_m outside [-5 %, +20 %]: "
          f"{len(FLAGGED) if FLAGGED else 'none'}.")
rl.append("")
rl.append("## Per day, verdict minutes (futures bar volume > 0)\n")
for sym in SYMS:
    rl.append(f"### {sym} — {len(VMIN[sym])} of 36 minutes, {len(VDAYS[sym])} of 12 days\n")
    rl.append("| day | v-mins | pairs | γ ratio before | γ ratio after | in band "
              "before | after | IV ratio before | IV ratio after |")
    rl.append("|---|---|---|---|---|---|---|---|---|")
    for day in VDAYS[sym]:
        gb, ga, ivb, iva, npairs, nm = D3[(sym, day)]
        rl.append(f"| {day} | {nm} | {npairs} | {gb:.4f} | {ga:.4f} | "
                  f"{'YES' if in_band(gb) else 'NO'} | "
                  f"{'YES' if in_band(ga) else 'NO'} | {ivb:.4f} | {iva:.4f} |")
    rl.append("")
rl.append("## All 72 minutes — descriptive, no verdict\n")
rl.append("| sym | in band before | in band after |")
rl.append("|---|---|---|")
for sym in SYMS:
    rl.append(f"| {sym} | {A72_IB[sym][0]}/12 | {A72_IB[sym][1]}/12 |")
rl.append("")
if SENSEX_ZV_NOTE:
    rl.append(f"**{SENSEX_ZV_NOTE}**\n")
else:
    rl.append("SENSEX verdict-minute and all-72 readings agree on whether the 10-of-12 "
              "bar is met.\n")
rl.append("## Control C-flat — one flat rate per symbol, no verdict\n")
rl.append("| sym | C-flat r (% a year) | in-band days on verdict minutes |")
rl.append("|---|---|---|")
for sym in SYMS:
    rl.append(f"| {sym} | {CFLAT[sym]*100:.4f} | {CF_IB[sym]}/{len(VDAYS[sym])} |")
rl.append("")
rl.append("C-flat separates *having a market-derived level* from *having it per minute*: "
          "if C-flat scores like r_m, the per-minute basis carried no information the "
          "single median level did not.\n")
rl.append("## The 1–3 % band — descriptive, no verdict\n")
rl.append("| sym | pairs | pooled γ ratio before | after | in-band days before | after |")
rl.append("|---|---|---|---|---|---|")
for sym in SYMS:
    mb, ma, nb, na, npr = W13[sym]
    rl.append(f"| {sym} | {npr} | {mb:.4f} | {ma:.4f} | {nb}/12 | {na}/12 |")
rl.append("")
rl.append("## IV_TOL noise floor\n")
rl.append("| sym | pair-set legs | vol points p50 | p90 | max | returned on budget "
          "rather than tolerance |")
rl.append("|---|---|---|---|---|---|")
for sym in SYMS:
    bud, nl = BUDGET[sym]
    rl.append(f"| {sym} | {len(NOISE[sym])} | {pct(NOISE[sym],50):.4f} | "
              f"{pct(NOISE[sym],90):.4f} | {max(NOISE[sym]):.4f} | {bud} of {nl} |")
rl.append("")
rl.append("## What this test could not see\n")
rl.append("- **OTM-leg truth.** The pair set conditions on **both** legs having solved, "
          "so it measures agreement only where both worked — never on the ITM legs that "
          "returned NULL (Part B B2: every NULL is ITM, 0.0 % of OTM legs are NULL). "
          "Bringing a call and a put together says nothing about which of the two is "
          "right; Part B's verdict (take the OTM leg's gamma) chose that leg because it "
          "is the leg that solves, not because it was shown to be more accurate. This "
          "test does not change that.")
rl.append("- **Lumpy dividends.** `r_m = ln(F/S)/T_fut` is a **net carry** figure with "
          "dividends inside it (`core/bs_engine.py:77-84`; FUTURES CONTRACT RULE, "
          "`BLOCKED.txt:235-237`). It is not a risk-free rate. Index dividends arrive in "
          "lumps, so a single `r_m` spreads a discrete ex-dividend step evenly across "
          "`T_fut`; near-month futures over an ex-dividend-heavy stretch carry a basis "
          "this model cannot decompose into rate and yield.")
rl.append("- **SENSEX alignment.** Per the PART H section (`BLOCKED.txt:280-283`), the "
          "offset-0 rule stands by operator decision, but SENSEX 2026-03-02 10:00 is "
          "**not independently confirmed** (SENSEX26MARFUT is 80880.50 at both offset 0 "
          "and +60, so that minute's F is the same either way, and the alignment "
          "re-check was INCONCLUSIVE on it). SENSEX alignment rests on the 2025-05-02 "
          "two-day test plus two unambiguous minutes. Every SENSEX number above carries "
          "that caveat.")
rl.append("- **Stale bar closes.** F is a one-minute bar close, and a zero-volume bar is "
          f"a stale print carrying a stale basis — {sum(1 for k in ALL_KEYS if PH[k]['zero_vol'])} "
          "of the 72 minutes, all SENSEX. Those minutes are excluded from the verdict "
          "but reported in 3f. The option legs have the same exposure and no volume "
          "filter at all: `hist_option_bars_1m` carries no bid/ask, so a thin strike's "
          "`close` may be an old print, and the solve cannot tell that from a quote.")
rl.append("- **`T` does not decay intraday** (`backfill_hist_greeks.py:289-290`), so "
          "10:00 and 15:00 on one day share a `T_opt`. Any error that induces is common "
          "to the three sampled minutes and invisible to a within-day comparison.")
rl.append("- **Solver resolution.** `IV_TOL = 1e-3` is a tolerance on the price residual, "
          "so the σ it resolves to is `≈ IV_TOL / vega` and varies by leg; the measured "
          "distribution is in the table above. This noise is present identically in the "
          "before and after numbers, so it does not bias the comparison, but it bounds "
          "how small a real change the test can distinguish.")
rl.append("- **72 minutes of ~90,000.** Three minutes on the first available `DONE` day "
          "of each month, no expiry day at all (`SKIP_EXPIRY`), nothing about the open, "
          "the close after 15:00, or intraday drift.")
rl.append("- **One rate per minute, applied to every leg.** A single `r_m` cannot "
          "represent a term structure or a strike-dependent funding effect, and the "
          "re-solve changes `r` only — spot, price, `T` and the band are held fixed by "
          "construction, which is the point, but it also means any residual "
          "disagreement is attributed to 'not the rate' without identifying what it is.")
rl.append("")
rl.append("## UNMEASURED\n")
un = []
if SENSEX_UNMEASURED:
    un.append("SENSEX verdict (fewer than 10 days with a verdict minute).")
for sym in SYMS:
    f, legs = FAIL_SYM[sym]
    if legs and f / legs > 0.05:
        un.append(f"{sym}: solver failures {f}/{legs} exceed 5 % of legs.")
un.append("The `fut_dte < 3` exclusion never fired on this sample (Part H: fut_dte "
          "22–30), so it is untested by this data.")
un.append("`next contract used` is judged only inside the six sampled windows, so its "
          "zero is not independent evidence that the nearer contract always had a bar "
          "(`BLOCKED.txt:259-261`).")
for u in un:
    rl.append(f"- {u}")
(HERE / "results.md").write_text("\n".join(rl) + "\n", encoding="utf-8")

say()
say("written: gates.md, results.md, per_minute.csv, per_day.csv, _sens_analysis.txt")
(HERE / "_sens_analysis.txt").write_text("\n".join(OUT) + "\n", encoding="utf-8")
