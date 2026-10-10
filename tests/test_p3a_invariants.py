"""P3a — compute invariants and an independent recompute, on the frozen golden days (OFFLINE).

Roadmap §2.1 P3 (= R2.2 + R2.3), phase a. Ruling S94-A. Risk class OFF: reads tests/golden/*/inputs only,
no database, no network. Rule 23: never 08:30-15:40 IST; run under `ulimit -v`.

Beliefs stated before the first run (Rule 0: an expected value obtained by running the thing asserts nothing):
  I1  sum(gex_strike.gex_cr) per (run_id, expiry) == gamma_metrics.net_gex          abs <= 0.01 Cr (ADR-014 §2.5)
  I2  gex_strike.gex_cr == independent recompute from the raw chain (ocs), per strike  abs <= 1e-6 Cr + 1e-9 rel
      recompute: gamma*oi*S^2/1e7, PE negative, 0 if gamma==0 or oi<=0, 0 if |K-S|/S>0.05 and |gamma|>5e-5
      (spec: compute_gamma_metrics_local.py:114-133, re-implemented here, NOT imported)
  I3  gex_strike.oi_call / oi_put == sum of chain oi by type at the strike               exact
  I4  gamma_metrics.gamma_concentration == max|gex_cr| / sum|gex_cr| (top-1 share)       abs <= 1e-6
  I5  descriptive: flip_level lies in an interval where the cumulative sum changes sign (both directions)
  I6  descriptive: put-call parity on mids vs (S - K), share of strikes outside the summed half-spreads
Every asserted check has a seeded mutant that must make it FAIL (bottom of file).
Usage: ( ulimit -v 700000; python3 -I tests/test_p3a_invariants.py ) — exit 0 = all asserted checks pass.
"""
import csv, gzip, math, os, sys, copy
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")


def rd(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    return None if x in (None, "", "NULL") else float(x)


def recompute(gamma, oi, opt, strike, spot):
    if not gamma or oi <= 0 or spot <= 0:
        return 0.0
    if strike > 0 and abs(strike - spot) / spot > 0.05 and abs(gamma) > 5e-5:
        return 0.0
    b = gamma * oi * spot * spot / 1e7
    return -b if opt == "PE" else b


def load(day):
    d = os.path.join(ROOT, day, "inputs")
    return {k: rd(os.path.join(d, f"{k}.csv.gz")) for k in ("gamma_metrics", "gex_strike", "ocs")}


def check_day(data):
    """Returns (fails, info). fails: list of strings naming every asserted-check failure."""
    fails, info = [], defaultdict(int)
    gs = defaultdict(list)
    for r in data["gex_strike"]:
        gs[(r["run_id"], r["expiry_date"])].append(r)
    chain = defaultdict(list)
    for r in data["ocs"]:
        chain[(r["run_id"], r["expiry_date"], float(r["strike"]))].append(r)
    gm = {(r["run_id"], r["expiry_date"]): r for r in data["gamma_metrics"]}
    info["runs_gex"] = len(gs); info["runs_gm"] = len(gm)

    for key, rows in gs.items():
        # I1
        g = gm.get(key)
        tot = sum(float(r["gex_cr"]) for r in rows)
        if g is None:
            info["I1_no_gm_row"] += 1
        else:
            info["I1_checked"] += 1
            if abs(tot - float(g["net_gex"])) > 0.01:
                fails.append(f"I1 {key}: sum gex {tot:.4f} != net_gex {float(g['net_gex']):.4f}")
            # I4
            ab = [abs(float(r["gex_cr"])) for r in rows]
            if fnum(g.get("gamma_concentration")) is not None and sum(ab) > 0:
                info["I4_checked"] += 1
                top1 = max(ab) / sum(ab)
                if abs(top1 - float(g["gamma_concentration"])) > 1e-6:
                    fails.append(f"I4 {key}: top1 {top1:.6f} != gamma_concentration {float(g['gamma_concentration']):.6f}")
        # I2, I3
        for r in rows:
            k = float(r["strike"]); spot = float(r["spot"])
            legs = chain.get((key[0], key[1], k), [])
            if not legs:
                info["I2_no_chain_rows"] += 1
                continue
            info["I2_checked"] += 1
            rc = sum(recompute(fnum(l["gamma"]) or 0.0, fnum(l["oi"]) or 0.0, l["option_type"].upper(), k, spot) for l in legs)
            st = float(r["gex_cr"])
            if abs(rc - st) > 1e-6 + 1e-9 * abs(st):
                fails.append(f"I2 {key} K={k}: recompute {rc:.6f} != stored {st:.6f}")
            oc = sum(int(fnum(l["oi"]) or 0) for l in legs if l["option_type"].upper() == "CE")
            op = sum(int(fnum(l["oi"]) or 0) for l in legs if l["option_type"].upper() == "PE")
            if oc != int(float(r["oi_call"])) or op != int(float(r["oi_put"])):
                fails.append(f"I3 {key} K={k}: chain oi CE {oc}/PE {op} != stored {r['oi_call']}/{r['oi_put']}")
            info["I3_checked"] += 1

        # I5 descriptive
        if g is not None and fnum(g.get("flip_level")) is not None:
            fl = float(g["flip_level"])
            srt = sorted(rows, key=lambda r: float(r["strike"]))
            ks = [float(r["strike"]) for r in srt]; gx = [float(r["gex_cr"]) for r in srt]
            up = [sum(gx[: i + 1]) for i in range(len(gx))]
            dn = [sum(gx[i:]) for i in range(len(gx))]
            def brackets(cum):
                return any(ks[i] <= fl <= ks[i + 1] and (cum[i] > 0) != (cum[i + 1] > 0) for i in range(len(ks) - 1))
            info["I5_flips"] += 1
            info["I5_ascending_ok"] += brackets(up)
            info["I5_descending_ok"] += brackets(dn)

    # I6 descriptive: parity on mids, CE and PE at the same (run, expiry, strike)
    for (run, exp, k), legs in chain.items():
        ce = [l for l in legs if l["option_type"].upper() == "CE"]; pe = [l for l in legs if l["option_type"].upper() == "PE"]
        if len(ce) != 1 or len(pe) != 1:
            continue
        c, p = ce[0], pe[0]
        vals = [fnum(c["bid"]), fnum(c["ask"]), fnum(p["bid"]), fnum(p["ask"]), fnum(c["spot"])]
        if any(v is None or v <= 0 for v in vals):
            continue
        cb, ca, pb, pa, s = vals
        lhs = (cb + ca) / 2 - (pb + pa) / 2
        info["I6_checked"] += 1
        if abs(lhs - (s - k)) > (ca - cb) / 2 + (pa - pb) / 2:
            info["I6_outside_spreads"] += 1
    return fails, info


def mutants(data):
    """Each mutant must produce at least one failure naming its check. Returns list of mutant failures."""
    out = []
    rows = data["gex_strike"]
    if not rows:
        return out
    i = max(range(len(rows)), key=lambda j: abs(float(rows[j]["gex_cr"])))   # the largest strike, never a zero row
    cases = []
    m = copy.deepcopy(data); m["gex_strike"][i]["gex_cr"] = str(float(m["gex_strike"][i]["gex_cr"]) + 0.05); cases.append(("I1/I2 gex nudged +0.05", m, ("I1", "I2")))
    m = copy.deepcopy(data); m["gex_strike"][i]["oi_call"] = str(int(float(m["gex_strike"][i]["oi_call"])) + 1); cases.append(("I3 oi_call +1", m, ("I3",)))
    m = copy.deepcopy(data)
    run, exp = m["gex_strike"][i]["run_id"], m["gex_strike"][i]["expiry_date"]
    for g in m["gamma_metrics"]:
        if g["run_id"] == run and g["expiry_date"] == exp and fnum(g.get("gamma_concentration")) is not None:
            g["gamma_concentration"] = str(float(g["gamma_concentration"]) + 0.01)
    cases.append(("I4 concentration +0.01", m, ("I4",)))
    m = copy.deepcopy(data)
    # S95: the PE-sign mutant needs a strike whose PE leg has gamma and OI -- the largest strike's PE can be a
    # vendor greek gap (2026-08-27 NIFTY 24400: PE gamma 0), and negating a zero changes nothing.
    pe_live = {(l["run_id"], l["expiry_date"], float(l["strike"])) for l in data["ocs"]
               if l["option_type"].upper() == "PE" and fnum(l["gamma"]) and (fnum(l["oi"]) or 0) > 0}
    cand = [j for j in range(len(rows)) if (rows[j]["run_id"], rows[j]["expiry_date"], float(rows[j]["strike"])) in pe_live]
    j = max(cand, key=lambda j: abs(float(rows[j]["gex_cr"]))) if cand else i
    run, exp = m["gex_strike"][j]["run_id"], m["gex_strike"][j]["expiry_date"]
    k = float(m["gex_strike"][j]["strike"])   # S95: compare as numbers -- gex_strike has '72000.0', ocs has '72000'
    for l in m["ocs"]:
        if l["run_id"] == run and l["expiry_date"] == exp and float(l["strike"]) == k and l["option_type"].upper() == "PE" and fnum(l["gamma"]):
            l["option_type"] = "CE_FLIP"   # the PE leg's sign is lost: recompute treats it as positive
            break
    cases.append(("I2 PE sign lost", m, ("I2",)))
    for name, m, must in cases:
        if m == data:   # S95: a mutant that changed nothing cannot fail, so it proves nothing (Rule 0)
            out.append(f"MUTANT NOT APPLIED: {name}")
            continue
        f, _ = check_day(m)
        if not any(x.split(" ")[0] in must for x in f):
            out.append(f"MUTANT NOT CAUGHT: {name}")
    return out


def main():
    days = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d, "inputs")))
    assert days, "no golden days found"
    bad = 0
    for day in days:
        data = load(day)
        fails, info = check_day(data)
        print(f"== {day}  gex rows {len(data['gex_strike'])}  " + "  ".join(f"{k}={v}" for k, v in sorted(info.items())))
        if not data["gex_strike"]:
            print("   (no gex rows: closed day; nothing to assert)")
            continue
        for f in fails[:10]:
            print("   FAIL", f)
        if len(fails) > 10:
            print(f"   ... {len(fails) - 10} more")
        mf = mutants(data)
        for x in mf:
            print("  ", x)
        print(f"   asserted: {'PASS' if not fails else f'FAIL ({len(fails)})'}   mutants: {'all caught' if not mf else f'{len(mf)} NOT caught'}")
        bad += bool(fails) + bool(mf)
    print("P3A PASS" if not bad else "P3A FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
