#!/usr/bin/env python3
"""P1 level test — scoring. Implements the pre-registration verbatim:
docs/research/s92_priority/P1_level_test_prereg_2026-10-09.md
(git hash-object 7a708a64c4bb73f0712a6d6e78f92a5d411a8ece).

Input : the Part 2 extract as JSON (an array of row objects), path as argv[1].
Output: a markdown report on stdout and p1_scores.csv beside the input.
Stdlib only, deterministic: the null is a mean over every donor (no sampling); the bootstrap
uses random.Random(20261009).

Split boundaries recorded from Part 1b BEFORE any outcome was read (2026-10-09 09:23 IST):
NIFTY  N=85, calibration 56 (to 2026-08-26), holdout from 2026-08-27
SENSEX N=84, calibration 56 (to 2026-08-27), holdout from 2026-08-28
"""
import csv, json, math, os, random, sys
from statistics import mean

SEED = 20261009
RESAMPLES = 10_000
CI = 0.975                      # §5.8, two primary tests, Bonferroni
DONOR_GAP = 4                   # §5.5
EXPECTED = {"NIFTY": (85, 56), "SENSEX": (84, 56)}
STEP = {"NIFTY": 50.0, "SENSEX": 100.0}

NUM = ("sess_ix", "n_cal", "dte", "step", "s0", "iv0", "iv_age_min", "band", "sigma_w", "sigma_d",
       "cw", "pw", "l1", "l2", "l3", "ties_at_rank3", "hi", "lo", "n_min")


def f(v):
    return None if v is None or v == "" else float(v)


def load(path):
    rows = json.load(open(path))
    out = []
    for r in rows:
        r = dict(r)
        for k in NUM:
            r[k] = f(r.get(k))
        out.append(r)
    return out


def snap(x, s0, step):
    """§5.5.3: nearest multiple of step; an exact half rounds away from spot."""
    q = x / step
    lo, hi = math.floor(q), math.ceil(q)
    if hi - q < q - lo:
        return hi * step
    if q - lo < hi - q:
        return lo * step
    return (hi if x > s0 else lo) * step


def place(level, d, r):
    """Donor d's level as a sigma offset from d's spot, placed on r and snapped to r's grid."""
    k = (level - d["s0"]) / d["sigma_d"]
    return snap(r["s0"] + k * r["sigma_d"], r["s0"], r["step"])


def dist_A(hi, lo, cw, pw, sig):
    return (abs(hi - cw) + abs(lo - pw)) / (2 * sig)


def dist_B(hi, lo, lv, sig):
    return (min(abs(hi - l) for l in lv) + min(abs(lo - l) for l in lv)) / (2 * sig)


def leaders(r):
    return [x for x in (r["l1"], r["l2"], r["l3"]) if x is not None]


def score_session(r, donors):
    """Real and null (mean over donors) values for every statistic on session r."""
    hi, lo, sig = r["hi"], r["lo"], r["sigma_d"]
    X = {"halfstep": r["step"] / 2, "0.10sig": 0.10 * sig}
    out = {"symbol": r["symbol"], "session_date": r["session_date"], "anchor": r["anchor"],
           "sess_ix": int(r["sess_ix"]), "dte": r["dte"], "sigma_d": sig}

    def collect(fn_real, fn_null, key):
        real = fn_real()
        nulls = [v for v in (fn_null(d) for d in donors) if v is not None]
        out[key + "_real"] = real
        out[key + "_null"] = mean(nulls) if (real is not None and nulls) else None
        out[key + "_ndonor"] = len(nulls)

    hasA = r["cw"] is not None and r["pw"] is not None
    okA = lambda d: d["cw"] is not None and d["pw"] is not None
    lv = leaders(r)

    # primary statistics (§5.4)
    collect(lambda: dist_A(hi, lo, r["cw"], r["pw"], sig) if hasA else None,
            lambda d: dist_A(hi, lo, place(d["cw"], d, r), place(d["pw"], d, r), sig) if okA(d) else None, "dA")
    collect(lambda: dist_B(hi, lo, lv, sig) if len(lv) == 3 else None,
            lambda d: dist_B(hi, lo, [place(l, d, r) for l in leaders(d)], sig) if len(leaders(d)) == 3 else None,
            "dB")
    # arm A halves (§5.9)
    collect(lambda: abs(hi - r["cw"]) / sig if hasA else None,
            lambda d: abs(hi - place(d["cw"], d, r)) / sig if okA(d) else None, "dA_high")
    collect(lambda: abs(lo - r["pw"]) / sig if hasA else None,
            lambda d: abs(lo - place(d["pw"], d, r)) / sig if okA(d) else None, "dA_low")
    # hit and break-through rates (§5.9)
    for name, x in X.items():
        collect(lambda: float(abs(hi - r["cw"]) <= x and abs(lo - r["pw"]) <= x) if hasA else None,
                lambda d: float(abs(hi - place(d["cw"], d, r)) <= x and abs(lo - place(d["pw"], d, r)) <= x)
                if okA(d) else None, f"hitA_both_{name}")
        collect(lambda: float(abs(hi - r["cw"]) <= x) if hasA else None,
                lambda d: float(abs(hi - place(d["cw"], d, r)) <= x) if okA(d) else None, f"hitA_high_{name}")
        collect(lambda: float(abs(lo - r["pw"]) <= x) if hasA else None,
                lambda d: float(abs(lo - place(d["pw"], d, r)) <= x) if okA(d) else None, f"hitA_low_{name}")
        collect(lambda: float(hi > r["cw"] + x) if hasA else None,
                lambda d: float(hi > place(d["cw"], d, r) + x) if okA(d) else None, f"breakA_high_{name}")
        collect(lambda: float(lo < r["pw"] - x) if hasA else None,
                lambda d: float(lo < place(d["pw"], d, r) - x) if okA(d) else None, f"breakA_low_{name}")
    for k in ("dA", "dB", "dA_high", "dA_low"):
        rv, nv = out[k + "_real"], out[k + "_null"]
        out["e_" + k] = (nv - rv) if (rv is not None and nv is not None) else None
    return out


def bootstrap_ci(vals, seed=SEED, n=RESAMPLES, level=CI):
    rng = random.Random(seed)
    m = len(vals)
    means = sorted(mean(rng.choice(vals) for _ in range(m)) for _ in range(n))
    a = (1 - level) / 2
    return means[int(math.floor(a * n))], means[int(math.ceil((1 - a) * n)) - 1]


def sig3(x):
    return "—" if x is None else f"{x:.3g}"


def dte_bucket(d):
    if d is None:
        return "?"
    d = int(d)
    return "0" if d == 0 else "1" if d == 1 else "2–3" if d <= 3 else "4+"


def main(path):
    rows = load(path)
    scored, report = [], []
    P = report.append
    P("# P1 level test — results\n")
    P(f"Input `{os.path.basename(path)}` · seed {SEED} · {RESAMPLES:,} resamples · {CI:.1%} interval · "
      "pre-registration `7a708a64c4bb73f0`\n")

    verdicts = {}
    for anchor in ("t0", "t1015"):
        for sym in ("NIFTY", "SENSEX"):
            S = sorted([r for r in rows if r["symbol"] == sym and r["anchor"] == anchor],
                       key=lambda r: r["sess_ix"])
            if not S:
                continue
            if anchor == "t0":
                n_exp, cal_exp = EXPECTED[sym]
                assert len(S) == n_exp, f"{sym}: {len(S)} t0 rows, Part 1b said {n_exp}"
                assert int(S[0]["n_cal"]) == cal_exp, f"{sym}: n_cal {S[0]['n_cal']} != {cal_exp}"
                bad = [r["session_date"] for r in S if r["step"] != STEP[sym]]
                assert not bad, f"{sym}: grid failure {bad}"
                assert all(r["hi"] is not None and r["lo"] is not None for r in S), f"{sym}: missing hi/lo"
            n_cal = int(S[0]["n_cal"])
            res = []
            for r in S:
                if r["sigma_d"] is None or r["hi"] is None:
                    continue
                donors = [d for d in S if abs(d["sess_ix"] - r["sess_ix"]) >= DONOR_GAP
                          and d["sigma_d"] is not None]
                o = score_session(r, donors)
                o["half"] = "cal" if r["sess_ix"] <= n_cal else "hold"
                o["ties_at_rank3"] = r["ties_at_rank3"]
                res.append(o)
            scored += res

            primary = anchor == "t0" and sym == "NIFTY"
            P(f"\n## {sym} · levels at {'t0 (first run ≥ 09:15)' if anchor == 't0' else 'the 10:15 run'}"
              f"{' — PRIMARY' if primary else ' — descriptive'}\n")
            P(f"Sessions scored: {len(res)} · calibration {sum(o['half']=='cal' for o in res)} · "
              f"holdout {sum(o['half']=='hold' for o in res)} · arm A excluded (NULL wall at the anchor): "
              f"{sum(o['dA_real'] is None for o in res)} · exact ties at leader rank 3: "
              f"{int(sum((o['ties_at_rank3'] or 0) for o in res))}\n")
            P("| arm | half | n | mean real (σ) | mean null (σ) | mean e = null − real | interval |")
            P("|---|---|---:|---:|---:|---:|---|")
            for arm in ("dA", "dB", "dA_high", "dA_low"):
                cm = {}
                for half in ("cal", "hold"):
                    E = [o for o in res if o["half"] == half and o["e_" + arm] is not None]
                    if not E:
                        continue
                    e = [o["e_" + arm] for o in E]
                    cm[half] = mean(e)
                    ci = bootstrap_ci(e) if half == "hold" else None
                    P(f"| {arm} | {half} | {len(E)} | {sig3(mean(o[arm+'_real'] for o in E))} | "
                      f"{sig3(mean(o[arm+'_null'] for o in E))} | {sig3(mean(e))} | "
                      f"{'[' + sig3(ci[0]) + ', ' + sig3(ci[1]) + ']' if ci else ''} |")
                    if half == "hold" and primary and arm in ("dA", "dB"):
                        cm["ci"] = ci
                if primary and arm in ("dA", "dB") and "hold" in cm and "cal" in cm:
                    lo_, hi_ = cm["ci"]
                    no1 = lo_ <= 0 <= hi_
                    no2 = cm["hold"] < 0.5 * cm["cal"]
                    verdicts[arm] = ("NO" if (no1 or no2) else "YES",
                                     f"holdout {sig3(cm['hold'])} {CI:.1%} [{sig3(lo_)}, {sig3(hi_)}]"
                                     f"{' includes 0' if no1 else ''}; calibration {sig3(cm['cal'])}"
                                     f"{' · holdout < half calibration' if no2 else ''}")

            P("\nHit and break-through rates, arm A (all sessions, real vs null):\n")
            P("| statistic | X | real | null |")
            P("|---|---|---:|---:|")
            for stat in ("hitA_both", "hitA_high", "hitA_low", "breakA_high", "breakA_low"):
                for name in ("halfstep", "0.10sig"):
                    k = f"{stat}_{name}"
                    E = [o for o in res if o[k + "_real"] is not None and o[k + "_null"] is not None]
                    if E:
                        P(f"| {stat} | {name} | {mean(o[k+'_real'] for o in E):.1%} | "
                          f"{mean(o[k+'_null'] for o in E):.1%} |")
            P("\nBy DTE bucket (mean e, all sessions):\n")
            P("| DTE | n | e_dA | e_dB |")
            P("|---|---:|---:|---:|")
            for b in ("0", "1", "2–3", "4+"):
                E = [o for o in res if dte_bucket(o["dte"]) == b]
                if E:
                    a = [o["e_dA"] for o in E if o["e_dA"] is not None]
                    bb = [o["e_dB"] for o in E if o["e_dB"] is not None]
                    P(f"| {b} | {len(E)} | {sig3(mean(a)) if a else '—'} | {sig3(mean(bb)) if bb else '—'} |")

    P("\n## Verdict (§5.8) — the only two tests that can produce one\n")
    for arm, name in (("dA", "A-NIFTY · corridor"), ("dB", "B-NIFTY · leader set")):
        v = verdicts.get(arm)
        P(f"- **{name}: {v[0] if v else 'NOT COMPUTED'}** — {v[1] if v else ''}")

    out_csv = os.path.join(os.path.dirname(os.path.abspath(path)), "p1_scores.csv")
    keys = sorted({k for o in scored for k in o})
    lead = ["symbol", "anchor", "session_date", "sess_ix", "half", "dte", "sigma_d"]
    keys = lead + [k for k in keys if k not in lead]
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for o in scored:
            w.writerow(o)
    print("\n".join(report))


if __name__ == "__main__":
    main(sys.argv[1])
