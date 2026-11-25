"""Self-test for v2_indep.py (pre-registration section 6).

Every expected value below is written out by hand from rule v1.1.
With spot 20000 the factor S^2 / 1e7 is exactly 40.
Run:  python3 -B -I selftest_v2_indep.py     (exit 0 = all pass, all mutants caught)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v2_indep as v  # noqa: E402

EXP = "2026-12-01"
TOL = 1e-12


def leg(strike, ot, oi, gamma, spot="20000", expiry=EXP):
    return {"strike": strike, "option_type": ot, "oi": oi, "gamma": gamma,
            "spot": spot, "expiry_date": expiry, "run_id": "r1", "symbol": "TEST"}


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (bool, str)) or isinstance(b, (bool, str)):
        return a == b
    return abs(a - b) <= TOL + TOL * abs(b)


# ---------------------------------------------------------------- case A
CHAIN_A = [
    # 20000: both legs, in band
    leg("20000", "CE", "1000", "0.0004"), leg("20000", "PE", "400", "0.0006"),
    # 20100: put gamma is 0 -> call_only; put OI still counts
    leg("20100", "CE", "500", "0.0003"), leg("20100", "PE", "300", "0"),
    # 19900: call gamma missing -> put_only
    leg("19900", "CE", "200", ""), leg("19900", "PE", "700", "0.0005"),
    # 20200: call gamma negative, put gamma 0 -> no gamma, not in map
    leg("20200", "CE", "100", "-0.0004"), leg("20200", "PE", "100", "0"),
    # 20300: equal OI -> net exactly 0, stays in map
    leg("20300", "CE", "300", "0.0002"), leg("20300", "PE", "300", "0.0004"),
    # 20400: no OI on either leg -> no output row
    leg("20400", "CE", "0", "0.0003"), leg("20400", "PE", "0", "0.0003"),
    # 21000: exactly on the 5% edge -> in band, guard does not act
    leg("21000", "CE", "100", "0.00009"), leg("21000", "PE", "50", "0.00003"),
    # 21000.05: one tick beyond -> guard removes the call leg only
    leg("21000.05", "CE", "100", "0.00009"), leg("21000.05", "PE", "50", "0.00003"),
    # 22000: guard removes both legs -> in map at exactly 0
    leg("22000", "CE", "80", "0.00008"), leg("22000", "PE", "20", "0.00007"),
    # 18000: gamma exactly 5e-5 is kept; 0.000051 is removed
    leg("18000", "CE", "10", "0.00005"), leg("18000", "PE", "30", "0.000051"),
    # 19800: two call rows -> OI summed, largest gamma
    leg("19800", "CE", "100", "0.0002"), leg("19800", "CE", "150", "0.0005"),
    leg("19800", "PE", "50", "0.0003"),
    # 19700: non-positive and missing OI count as 0; the gamma still counts
    leg("19700", "CE", "-5", "0.0003"), leg("19700", "CE", "NULL", "0.0001"),
    leg("19700", "PE", "40", "0.0002"),
    # unknown option type is ignored
    leg("20000", "XX", "999", "0.0009"),
]

# strike: (oi_call, oi_put, gamma_strike, gamma_legs, in_map, in_band, net_cr, gross_cr)
EXPECT_A = {
    18000.0:    (10.0, 30.0, 0.00005, "call_only", True, False, 0.00005 * (10 - 30) * 40, 0.00005 * 40 * 40),
    19700.0:    (0.0, 40.0, 0.00025, "both", True, True, 0.00025 * (0 - 40) * 40, 0.00025 * 40 * 40),
    19800.0:    (250.0, 50.0, 0.0004, "both", True, True, 0.0004 * 200 * 40, 0.0004 * 300 * 40),
    19900.0:    (200.0, 700.0, 0.0005, "put_only", True, True, 0.0005 * (200 - 700) * 40, 0.0005 * 900 * 40),
    20000.0:    (1000.0, 400.0, 0.0005, "both", True, True, 0.0005 * 600 * 40, 0.0005 * 1400 * 40),
    20100.0:    (500.0, 300.0, 0.0003, "call_only", True, True, 0.0003 * 200 * 40, 0.0003 * 800 * 40),
    20200.0:    (100.0, 100.0, None, None, False, True, 0.0, 0.0),
    20300.0:    (300.0, 300.0, 0.0003, "both", True, True, 0.0, 0.0003 * 600 * 40),
    21000.0:    (100.0, 50.0, 0.00006, "both", True, True, 0.00006 * 50 * 40, 0.00006 * 150 * 40),
    21000.05:   (100.0, 50.0, 0.00003, "put_only", True, False, 0.00003 * 50 * 40, 0.00003 * 150 * 40),
    22000.0:    (80.0, 20.0, None, None, True, False, 0.0, 0.0),
}
_NET_A = [12.0, 2.4, -10.0, 0.0, 0.12, 0.06, 0.0, -0.04, 3.2, -0.4]          # the ten in-map strikes
_BAND_A = [28.0, 9.6, 18.0, 7.2, 0.36, 4.8, 0.4]                              # in band and gross > 0
SUM_A = {
    "net_cr": 7.34,
    "net_top_share": 12.0 / 28.22,
    "gross_band_cr": 68.36,
    "gross_top_share": 28.0 / 68.36,
    "gross_hhi": 1275.3296 / (68.36 * 68.36),
    "n_map": 10,
    "n_zero": 2,
}
assert abs(sum(_NET_A) - 7.34) < 1e-9 and abs(sum(abs(x) for x in _NET_A) - 28.22) < 1e-9
assert abs(sum(_BAND_A) - 68.36) < 1e-9 and abs(sum(x * x for x in _BAND_A) - 1275.3296) < 1e-9

# The same book as stored per-strike rows (leg sums; non-positive gamma stored as given)
GSS_A = [
    {"strike": "18000", "spot": "20000", "oi_call": "10", "oi_put": "30", "gamma_call": "0.00005", "gamma_put": "0.000051", "expiry_date": EXP},
    {"strike": "19700", "spot": "20000", "oi_call": "0", "oi_put": "40", "gamma_call": "0.0003", "gamma_put": "0.0002", "expiry_date": EXP},
    {"strike": "19800", "spot": "20000", "oi_call": "250", "oi_put": "50", "gamma_call": "0.0005", "gamma_put": "0.0003", "expiry_date": EXP},
    {"strike": "19900", "spot": "20000", "oi_call": "200", "oi_put": "700", "gamma_call": "", "gamma_put": "0.0005", "expiry_date": EXP},
    {"strike": "20000", "spot": "20000", "oi_call": "1000", "oi_put": "400", "gamma_call": "0.0004", "gamma_put": "0.0006", "expiry_date": EXP},
    {"strike": "20100", "spot": "20000", "oi_call": "500", "oi_put": "300", "gamma_call": "0.0003", "gamma_put": "NULL", "expiry_date": EXP},
    {"strike": "20200", "spot": "20000", "oi_call": "100", "oi_put": "100", "gamma_call": "-0.0004", "gamma_put": "0", "expiry_date": EXP},
    {"strike": "20300", "spot": "20000", "oi_call": "300", "oi_put": "300", "gamma_call": "0.0002", "gamma_put": "0.0004", "expiry_date": EXP},
    {"strike": "20400", "spot": "20000", "oi_call": "0", "oi_put": "", "gamma_call": "0.0003", "gamma_put": "0.0003", "expiry_date": EXP},
    {"strike": "21000", "spot": "20000", "oi_call": "100", "oi_put": "50", "gamma_call": "0.00009", "gamma_put": "0.00003", "expiry_date": EXP},
    {"strike": "21000.05", "spot": "20000", "oi_call": "100", "oi_put": "50", "gamma_call": "0.00009", "gamma_put": "0.00003", "expiry_date": EXP},
    {"strike": "22000", "spot": "20000", "oi_call": "80", "oi_put": "20", "gamma_call": "0.00008", "gamma_put": "0.00007", "expiry_date": EXP},
]

# ---------------------------------------------------------------- case B
# Spot 19000.6, strike 19950.63 is EXACTLY 5% away (19000.6 * 1.05 = 19950.63).
# Floating point puts it beyond; exact decimal puts it on the edge, in band.
S_B = 19000.6
CHAIN_B = [leg("19950.63", "CE", "10", "0.0001", spot="19000.6"),
           leg("19950.63", "PE", "10", "0.00002", spot="19000.6")]
EXPECT_B = {19950.63: (10.0, 10.0, 0.00006, "both", True, True, 0.0, 0.00006 * 20 * S_B * S_B / 1e7)}

KEYS = ("oi_call", "oi_put", "gamma_strike", "gamma_legs", "in_map", "in_band", "net_cr", "gross_cr")


def check_rows(name, rows, expect, fails):
    got = {r["strike"]: r for r in rows}
    if sorted(got) != sorted(expect):
        fails.append(f"{name}: strike set {sorted(got)} != {sorted(expect)}")
        return
    for k, tup in expect.items():
        for key, want in zip(KEYS, tup):
            if not close(got[k][key], want):
                fails.append(f"{name}: strike {k} {key} got {got[k][key]!r} want {want!r}")


def check_summary(name, got, want, fails):
    for key, w in want.items():
        if not close(got[key], w):
            fails.append(f"{name}: {key} got {got[key]!r} want {w!r}")


def expect_error(name, fn, rows, mut, fails):
    try:
        fn(rows, _mut=mut)
    except v.V2RunError:
        return
    fails.append(f"{name}: expected V2RunError, got output")


def run_all(mut=None):
    fails = []
    # 1-10, 13: the main book, chain build
    rows_a = v.build_from_chain(CHAIN_A, _mut=mut)
    check_rows("A chain", rows_a, EXPECT_A, fails)
    check_summary("A summary", v.summarise(rows_a, _mut=mut), SUM_A, fails)
    # 14: the stored-row build gives the same rows and figures
    rows_g = v.build_from_gss(GSS_A, _mut=mut)
    check_rows("A stored", rows_g, EXPECT_A, fails)
    check_summary("A stored summary", v.summarise(rows_g, _mut=mut), SUM_A, fails)
    # 7: the exact-decimal edge
    check_rows("B edge", v.build_from_chain(CHAIN_B, _mut=mut), EXPECT_B, fails)
    # 11: error runs
    expect_error("two expiries", v.build_from_chain,
                 [leg("20000", "CE", "1", "0.0001"), leg("20000", "PE", "1", "0.0001", expiry="2026-12-08")], mut, fails)
    expect_error("two spots", v.build_from_chain,
                 [leg("20000", "CE", "1", "0.0001"), leg("20000", "PE", "1", "0.0001", spot="20000.05")], mut, fails)
    expect_error("no spot", v.build_from_chain,
                 [leg("20000", "CE", "1", "0.0001", spot="0"), leg("20000", "PE", "1", "0.0001", spot="")], mut, fails)
    expect_error("stored two expiries", v.build_from_gss,
                 [dict(GSS_A[0]), dict(GSS_A[1], expiry_date="2026-12-08")], mut, fails)
    # the same spot written two ways is one spot
    same = v.build_from_chain([leg("20000", "CE", "1", "0.0002"), leg("20000", "PE", "1", "0.0002", spot="20000.00")], _mut=mut)
    if len(same) != 1:
        fails.append("same spot written two ways: expected one row")
    # 12: empty map and empty band
    empty = v.build_from_chain([leg("20000", "CE", "0", "0.0002"), leg("20000", "PE", "0", "0.0002")], _mut=mut)
    if empty != []:
        fails.append("no OI anywhere: expected no rows")
    check_summary("empty summary", v.summarise(empty, _mut=mut),
                  {"net_cr": 0.0, "net_top_share": None, "gross_band_cr": 0.0, "gross_top_share": None,
                   "gross_hhi": None, "n_map": 0, "n_zero": 0}, fails)
    far = v.build_from_chain([leg("23000", "CE", "10", "0.00002"), leg("23000", "PE", "30", "0.00004")], _mut=mut)
    check_summary("map without band", v.summarise(far, _mut=mut),
                  {"net_cr": 0.00003 * (10 - 30) * 40, "net_top_share": 1.0, "gross_band_cr": 0.0,
                   "gross_top_share": None, "gross_hhi": None, "n_map": 1, "n_zero": 0}, fails)
    nomap = v.build_from_chain([leg("20000", "CE", "10", "0"), leg("20000", "PE", "30", "")], _mut=mut)
    check_summary("rows but no map", v.summarise(nomap, _mut=mut),
                  {"net_cr": 0.0, "net_top_share": None, "gross_band_cr": 0.0, "gross_top_share": None,
                   "gross_hhi": None, "n_map": 0, "n_zero": 0}, fails)
    if len(nomap) != 1 or nomap[0]["in_map"]:
        fails.append("rows but no map: expected one row with in_map False")
    if mut is None and v.count_duplicate_legs(CHAIN_A) != 2:
        fails.append("duplicate leg count: expected 2")
    return fails


MUTANTS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11"]

if __name__ == "__main__":
    base = run_all(None)
    for f in base:
        print("FAIL", f)
    print(f"self-test: {'PASS' if not base else 'FAIL'} ({len(base)} failures)")
    missed = []
    for m in MUTANTS:
        n = len(run_all(m))
        print(f"mutant {m}: {'caught' if n else 'NOT CAUGHT'} ({n} failing checks)")
        if not n:
            missed.append(m)
    ok = (not base) and (not missed)
    print("RESULT:", "OK" if ok else "NOT OK")
    sys.exit(0 if ok else 1)
