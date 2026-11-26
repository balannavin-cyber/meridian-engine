#!/usr/bin/env python3
"""Self-test for merdian_compute/gamma_v2.py (rule v1.2). Synthetic cases only: reads no
fixture, no database, no network. Expected values are hand-computed in this file.

  python3 -B tests/test_gamma_v2_selftest.py            -> cases, then mutants
  python3 -B tests/test_gamma_v2_selftest.py --cases    -> cases only (used by the mutant runs)
  python3 -B tests/test_gamma_v2_selftest.py --module P -> test the module file at path P

WHAT MAKES IT FAIL: every mutant below is one text edit of gamma_v2.py that breaks one
clause of the rule. Each must apply exactly once and must make --cases fail. A mutant
that survives is a FAIL of this self-test.
"""
import importlib.util, math, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODULE = os.path.join(os.path.dirname(HERE), "merdian_compute", "gamma_v2.py")


def load(path):
    spec = importlib.util.spec_from_file_location("gamma_v2_under_test", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def close(a, b, tol=1e-12):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


S = 20000.0              # 5 % of spot = 1000 exactly
F = S * S / 1e7          # 40.0


def leg(strike, typ, oi, gamma, spot=S, expiry="2026-12-01"):
    return {"strike": strike, "option_type": typ, "oi": oi, "gamma": gamma, "spot": spot, "expiry_date": expiry}


def run_cases(m):
    errs = []

    def check(name, cond):
        if not cond:
            errs.append(name)

    rows = [
        # A 20000: both legs. gamma (0.0004+0.0002)/2 = 0.0003; net 0.0003*(1000-400)*40 = 7.2; gross 0.0003*1400*40 = 16.8
        leg(20000, "CE", 1000, 0.0004), leg(20000, "PE", 400, 0.0002),
        # B 20100: put gamma 0 -> call_only 0.0003; put OI counts. net 0.0003*(100-500)*40 = -4.8; gross 0.0003*600*40 = 7.2
        leg(20100, "CE", 100, 0.0003), leg(20100, "PE", 500, 0.0),
        # C 19900: only leg with gamma has zero OI; other leg has OI -> in map, net 0.0002*(0-300)*40 = -2.4; gross 2.4
        leg(19900, "CE", 0, 0.0002), leg(19900, "PE", 300, None),
        # D 21000: exactly on the 5 % edge. In band; guard does NOT act although both gammas > 5e-5.
        #   gamma 0.0001; net 0.0001*(200-100)*40 = 0.4; gross 0.0001*300*40 = 1.2
        leg(21000, "CE", 200, 0.0001), leg(21000, "PE", 100, 0.0001),
        # E 21000.05: just beyond the edge. Call 9e-5 removed by guard, put 4e-5 kept -> put_only.
        #   mean-then-guard would give 6.5e-5 -> removed entirely. net 4e-5*(50-150)*40 = -0.16; gross 4e-5*200*40 = 0.32 (out of band)
        leg(21000.05, "CE", 50, 9e-5), leg(21000.05, "PE", 150, 4e-5),
        # F 22000: both legs removed by guard -> in map, gamma none, net exactly 0, gross 0.
        leg(22000, "CE", 10, 0.0002), leg(22000, "PE", 30, 0.0003),
        # G 18000: negative vendor gamma is no gamma; no other gamma -> not in map; row present (OI > 0).
        leg(18000, "CE", 70, -0.0003), leg(18000, "PE", 20, 0.0),
        # H 19000: exactly on the lower edge, equal OI -> in map, net exactly 0, gross 0.0002*800*40 = 6.4 in band.
        leg(19000, "CE", 400, 0.0002), leg(19000, "PE", 400, 0.0002),
        # I 20200: duplicate call rows -> OI summed (300), largest gamma (0.0005); put 100 @ 0.0001.
        #   gamma 0.0003; net 0.0003*(300-100)*40 = 2.4; gross 0.0003*400*40 = 4.8
        leg(20200, "CE", 100, 0.0001), leg(20200, "CE", 200, 0.0005), leg(20200, "PE", 100, 0.0001),
        # J 20300: no OI on either leg -> no row at all.
        leg(20300, "CE", 0, 0.0004), leg(20300, "PE", None, 0.0004),
        # K 17000: beyond guard, gamma exactly 5e-5 is NOT removed (strictly greater). net 5e-5*(0-1000)*40 = -2.0
        leg(17000, "PE", 1000, 5e-5),
        # L 20400: negative OI on the call counts as 0. put_only-by-OI: gamma 0.0002 both; net 0.0002*(0-50)*40 = -0.4; gross 0.4
        leg(20400, "CE", -25, 0.0002), leg(20400, "PE", 50, 0.0002),
    ]
    out = m.build_v2_strike_rows(rows, S)
    by = {r["strike"]: r for r in out}
    exp = {
        20000.0: (0.0003, "both", True, True, 7.2, 16.8),
        20100.0: (0.0003, "call_only", True, True, -4.8, 7.2),
        19900.0: (0.0002, "call_only", True, True, -2.4, 2.4),
        21000.0: (0.0001, "both", True, True, 0.4, 1.2),
        21000.05: (4e-5, "put_only", True, False, -0.16, 0.32),
        22000.0: (None, None, True, False, 0.0, 0.0),
        18000.0: (None, None, False, False, 0.0, 0.0),
        19000.0: (0.0002, "both", True, True, 0.0, 6.4),
        20200.0: (0.0003, "both", True, True, 2.4, 4.8),
        17000.0: (5e-5, "put_only", True, False, -2.0, 2.0),
        20400.0: (0.0002, "both", True, True, -0.4, 0.4),
    }
    check("row set (strikes present)", sorted(by) == sorted(exp))
    check("rows sorted by strike", [r["strike"] for r in out] == sorted(r["strike"] for r in out))
    for k, (g, legs, in_map, in_band, net, gross) in exp.items():
        r = by.get(k)
        if r is None:
            continue
        check(f"{k} gamma_strike", close(r["gamma_strike"], g))
        check(f"{k} gamma_legs", r["gamma_legs"] == legs)
        check(f"{k} in_map", r["in_map"] is in_map)
        check(f"{k} in_band", r["in_band"] is in_band)
        check(f"{k} net_cr", close(r["net_cr"], net))
        check(f"{k} gross_cr", close(r["gross_cr"], gross))
    check("22000 net exactly 0", by.get(22000.0, {}).get("net_cr") == 0.0)
    check("19000 net exactly 0", by.get(19000.0, {}).get("net_cr") == 0.0)
    check("20200 oi_call summed", by.get(20200.0, {}).get("oi_call") == 300.0)
    check("20400 oi_call non-positive -> 0", by.get(20400.0, {}).get("oi_call") == 0.0)

    summ = m.summarise_v2_run(out)
    net_vals = [7.2, -4.8, -2.4, 0.4, -0.16, 0.0, 0.0, 2.4, -2.0, -0.4]            # in_map strikes
    band = [16.8, 7.2, 2.4, 1.2, 6.4, 4.8, 0.4]                                     # in_band and gross > 0
    check("run net_cr", close(summ["net_cr"], sum(net_vals)))
    check("run net_top_share", close(summ["net_top_share"], 7.2 / sum(abs(v) for v in net_vals)))
    check("run gross_band_cr", close(summ["gross_band_cr"], sum(band)))
    check("run gross_top_share", close(summ["gross_top_share"], 16.8 / sum(band)))
    check("run gross_hhi", close(summ["gross_hhi"], sum((v / sum(band)) ** 2 for v in band)))
    check("run n_map", summ["n_map"] == 10)
    check("run n_zero", summ["n_zero"] == 2)
    check("duplicate legs counted", m.count_duplicate_legs(rows) == 1)

    # Decimal edge where floating point misplaces the strike: S = 24212.35, K = 1.05*S exactly.
    s2 = "24212.35"; k2 = "25422.9675"
    r2 = m.build_v2_strike_rows([leg(k2, "CE", 10, 0.0002, spot=s2), leg(k2, "PE", 10, 0.0002, spot=s2)], s2)
    check("decimal edge: in band", len(r2) == 1 and r2[0]["in_band"] is True)
    check("decimal edge: guard not applied", len(r2) == 1 and r2[0]["gamma_legs"] == "both")
    k3 = "25422.9676"
    r3 = m.build_v2_strike_rows([leg(k3, "CE", 10, 0.0002, spot=s2), leg(k3, "PE", 10, 0.0002, spot=s2)], s2)
    check("just past edge: out of band, guard applied", len(r3) == 1 and r3[0]["in_band"] is False and r3[0]["gamma_strike"] is None)

    # strike_gamma_v2 directly
    check("strike_gamma both", m.strike_gamma_v2(0.0004, 0.0002, 20000, S) == (0.00030000000000000003, "both") or close(m.strike_gamma_v2(0.0004, 0.0002, 20000, S)[0], 0.0003))
    check("strike_gamma none", m.strike_gamma_v2(None, 0, 20000, S) == (None, None))

    # Empty cases
    e = m.summarise_v2_run([])
    check("empty run", e == {"net_cr": 0.0, "net_top_share": None, "gross_band_cr": 0.0, "gross_top_share": None, "gross_hhi": None, "n_map": 0, "n_zero": 0})
    z = m.summarise_v2_run(m.build_v2_strike_rows([leg(22000, "CE", 10, 0.0002), leg(22000, "PE", 30, 0.0003)], S))
    check("all-zero map: net_top_share None", z["net_top_share"] is None and z["n_map"] == 1 and z["n_zero"] == 1 and z["gross_top_share"] is None and z["gross_hhi"] is None and z["gross_band_cr"] == 0.0)

    # Errors: no V2 output
    for name, bad in (
        ("multi-expiry is an error", [leg(20000, "CE", 1, 0.0001), leg(20000, "PE", 1, 0.0001, expiry="2026-12-08")]),
        ("multi-spot is an error", [leg(20000, "CE", 1, 0.0001), leg(20000, "PE", 1, 0.0001, spot=20001.0)]),
    ):
        try:
            m.build_v2_strike_rows(bad, S)
            errs.append(name)
        except m.V2InputError:
            pass
    try:
        m.build_v2_strike_rows([leg(20000, "CE", 1, 0.0001)], 20001.0)
        errs.append("spot argument differing from rows is an error")
    except m.V2InputError:
        pass

    # Stored-row build equals the chain build on the same run (stored legs as V1 writes them:
    # first non-zero gamma, summed OI). Uses a run without duplicate legs and with a negative stored gamma.
    chain = [r for r in rows if r["strike"] != 20200]
    gss = {}
    for r in chain:
        b = gss.setdefault(r["strike"], {"strike": r["strike"], "spot": S, "oi_call": 0, "oi_put": 0, "gamma_call": None, "gamma_put": None, "expiry_date": "2026-12-01"})
        key = "call" if r["option_type"] == "CE" else "put"
        b["oi_" + key] += int(r["oi"] or 0)
        if b["gamma_" + key] is None and (r["gamma"] or 0) != 0:
            b["gamma_" + key] = r["gamma"]
    gss_rows = [g for g in gss.values() if not (g["oi_call"] == 0 and g["oi_put"] == 0)]
    a = m.build_v2_strike_rows(chain, S)
    b2 = m.build_v2_strike_rows_from_gss(gss_rows)
    check("gss build: same strikes", [r["strike"] for r in a] == [r["strike"] for r in b2])
    for ra, rb in zip(a, b2):
        for f in ("gamma_strike", "net_cr", "gross_cr"):
            check(f"gss build {ra['strike']} {f}", close(ra[f], rb[f]))
        for f in ("gamma_legs", "in_map", "in_band"):
            check(f"gss build {ra['strike']} {f}", ra[f] == rb[f])
    try:
        m.build_v2_strike_rows_from_gss([gss_rows[0], dict(gss_rows[0])])
        errs.append("stored rows repeating a strike is an error")
    except m.V2InputError:
        pass
    for name, bad_spot in (("stored row with missing spot is an error", None), ("stored row with non-positive spot is an error", 0)):
        try:
            m.build_v2_strike_rows_from_gss([dict(gss_rows[0], spot=bad_spot)])
            errs.append(name)
        except m.V2InputError:
            pass
    try:  # a bad spot errors the run even on a row that has no valid strike and no OI
        m.build_v2_strike_rows_from_gss([gss_rows[0], {"strike": None, "spot": 0, "oi_call": 0, "oi_put": 0, "gamma_call": None, "gamma_put": None, "expiry_date": "2026-12-01"}])
        errs.append("stored row with bad spot and no valid strike is an error")
    except m.V2InputError:
        pass
    try:  # the same strike written two ways is a repeat (decimal value)
        m.build_v2_strike_rows_from_gss([dict(gss_rows[0], strike="20000"), dict(gss_rows[0], strike="20000.0")])
        errs.append("repeat judged on decimal value")
    except m.V2InputError:
        pass
    ok_rows = m.build_v2_strike_rows_from_gss([gss_rows[0], {"strike": None, "spot": S, "oi_call": 5, "oi_put": 5, "expiry_date": "2026-12-01"}, {"strike": None, "spot": S, "oi_call": 5, "oi_put": 5, "expiry_date": "2026-12-01"}])
    check("rows with no valid strike are skipped and are not repeats", len(ok_rows) == 1)
    try:
        m.build_v2_strike_rows_from_gss([gss_rows[0], dict(gss_rows[1], expiry_date="2026-12-08")])
        errs.append("stored rows with two expiries is an error")
    except m.V2InputError:
        pass
    check("rule version stamps", m.RULE_VERSION == "v2-1.2" and m.RULE_VERSION_GSS == "v2-1.2-gss")
    return errs


MUTANTS = [
    ("M01 mean -> sum", "return (gc + gp) / 2.0, \"both\"", "return (gc + gp), \"both\""),
    ("M02 guard gamma threshold", "GUARD_GAMMA = 5e-5", "GUARD_GAMMA = 5e-4"),
    ("M03 guard strict -> inclusive", "return abs(strike - spot) > GUARD_DISTANCE * spot", "return abs(strike - spot) >= GUARD_DISTANCE * spot"),
    ("M04 band inclusive -> strict", "return abs(strike - spot) <= GUARD_DISTANCE * spot", "return abs(strike - spot) < GUARD_DISTANCE * spot"),
    ("M05 net uses OI sum", "net = gamma_strike * (oi_call - oi_put)", "net = gamma_strike * (oi_call + oi_put)"),
    ("M06 gross uses OI difference", "gross = gamma_strike * (oi_call + oi_put)", "gross = gamma_strike * (oi_call - oi_put)"),
    ("M07 duplicate rows: smallest gamma", "g > b[\"g\"][leg]):", "g < b[\"g\"][leg]):"),
    ("M08 negative gamma accepted", "return g if g is not None and g > 0 else None", "return g if g is not None and g != 0 else None"),
    ("M09 in_map judged after guard", "in_map = _pos(gamma_call) is not None or _pos(gamma_put) is not None", "in_map = gamma_strike is not None"),
    ("M10 Crore divisor", "CR_DIVISOR = 1e7", "CR_DIVISOR = 1e6"),
    ("M11 HHI not squared", "(r[\"gross_cr\"] / gross_band_cr) ** 2", "(r[\"gross_cr\"] / gross_band_cr)"),
    ("M12 band filter dropped from run figures", "if r[\"in_band\"] and r[\"gross_cr\"] > 0]", "if r[\"gross_cr\"] > 0]"),
    ("M13 multi-spot not an error", "if len(row_spots) > 1:", "if len(row_spots) > 99:"),
    ("M14 multi-expiry not an error", "if len(expiries) > 1:", "if len(expiries) > 99:"),
    ("M15 guard distance 5 % -> 6 %", "GUARD_DISTANCE = Decimal(\"0.05\")", "GUARD_DISTANCE = Decimal(\"0.06\")"),
    ("M16 non-positive OI counted", "if oi is not None and oi > 0:", "if oi is not None:"),
    ("M17 OI-less strikes kept", "if oi_call + oi_put <= 0:\n        return None", "if False:\n        return None"),
    ("M18 guard removes gamma at exactly 5e-5", "if gp is not None and gp > GUARD_GAMMA:", "if gp is not None and gp >= GUARD_GAMMA:"),
    ("M19 float distance test", "return abs(strike - spot) <= GUARD_DISTANCE * spot", "return abs(float(strike) / float(spot) - 1) <= 0.05"),
    ("M20 net top share over all rows' gross", "net_top_share = (max(abs(r[\"net_cr\"]) for r in in_map) / abs_sum)", "net_top_share = (max(abs(r[\"gross_cr\"]) for r in in_map) / abs_sum)"),
    ("M21 n_zero counts nothing", "sum(1 for r in in_map if r[\"net_cr\"] == 0.0)", "sum(1 for r in in_map if r[\"net_cr\"] != r[\"net_cr\"])"),
    ("M22 stored put gamma dropped", "_pos(r.get(\"gamma_call\")), _pos(r.get(\"gamma_put\")))", "_pos(r.get(\"gamma_call\")), None)"),
    ("M23 spot argument not checked against rows", "if row_spots and next(iter(row_spots)) != s:", "if False:"),
    ("M24 stored repeated strike not an error", "if k in seen:", "if False:"),
    ("M26 stored bad spot not an error", "raise V2InputError(\"stored row has a missing or non-positive spot\")", "continue"),
    ("M27 stored bad spot ignored on a row without a valid strike", "if s is None or s <= 0:  # rule v1.2 (e)", "if (s is None or s <= 0) and _d(r.get(\"strike\")) is not None:  # rule v1.2 (e)"),
    ("M28 repeated strike judged on text, not value", "if k in seen:  # rule v1.2 (d)", "if str(r.get(\"strike\")) in {str(x) for x in seen}:  # rule v1.2 (d)"),
    ("M25 call guard skipped", "if gc is not None and gc > GUARD_GAMMA:\n            gc = None", "if gc is not None and gc > GUARD_GAMMA:\n            pass"),
]


def main():
    args = sys.argv[1:]
    path = DEFAULT_MODULE
    if "--module" in args:
        path = args[args.index("--module") + 1]
    errs = run_cases(load(path))
    if "--cases" in args:
        for e in errs:
            print("FAIL case:", e)
        print("CASES", "PASS" if not errs else f"FAIL ({len(errs)})")
        sys.exit(0 if not errs else 1)
    for e in errs:
        print("FAIL case:", e)
    print("control (unmutated):", "PASS" if not errs else f"FAIL ({len(errs)})")
    src = open(path).read()
    bad = 0 if not errs else 1
    with tempfile.TemporaryDirectory() as td:
        for name, old, new in MUTANTS:
            n = src.count(old)
            if n != 1:
                print(f"FAIL {name}: target text found {n} times (must be 1)"); bad += 1; continue
            mp = os.path.join(td, "mut.py")
            open(mp, "w").write(src.replace(old, new))
            p = subprocess.run([sys.executable, "-B", os.path.abspath(__file__), "--cases", "--module", mp], capture_output=True, text=True)
            caught = p.returncode != 0
            first = next((l for l in p.stdout.splitlines() if l.startswith("FAIL case:")), (p.stderr.strip().splitlines() or [""])[-1])
            print(f"{'caught  ' if caught else 'SURVIVED'} {name}  [{first[:70]}]")
            bad += 0 if caught else 1
    print("SELFTEST", "PASS" if bad == 0 else f"FAIL ({bad})", f"-- {len(MUTANTS)} mutants")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
