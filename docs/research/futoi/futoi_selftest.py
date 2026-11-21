"""Part 0 step 5: brute-force validation of every statistic written for this run.

Each check computes the expected value INDEPENDENTLY -- by full enumeration, by
exact rational arithmetic, or by numerical differentiation -- and compares. No
expected value here is recalled or copied from the implementation under test.
The scorer refuses to run with --score unless main() returns 0.

What this does NOT check: the imported wilcoxon.py is validated here against an
independent enumeration written from the Wilcoxon definition, not merely called.
"""
import itertools
import math
import os
import sys
from fractions import Fraction

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import futoi_stats as S
from core.bs_engine import bs_price

FAILED = []


def check(name, got, want, tol=1e-9, note=""):
    ok = (abs(got - want) <= tol) if isinstance(want, float) else (got == want)
    print("  %-56s %-14s %-14s %s%s" % (
        name,
        ("%.10g" % got) if isinstance(got, float) else str(got),
        ("%.10g" % want) if isinstance(want, float) else str(want),
        "PASS" if ok else "FAIL",
        ("   " + note) if note else ""))
    if not ok:
        FAILED.append(name)
    return ok


# ---------------------------------------------------------------- Wilcoxon
def brute_wilcoxon_less(diffs):
    """P(W+ <= observed) under H0, by enumerating all 2^n sign assignments.

    Written from the definition, independently of wilcoxon.py: drop zeros, take
    midranks of |d|, W+ = sum of ranks of positive d. The one-sided alternative
    'median < 0' is 'W+ small', so p = P(W+ <= w_obs)."""
    d = [x for x in diffs if x != 0]
    n = len(d)
    a = [abs(x) for x in d]
    order = sorted(range(n), key=lambda i: a[i])
    rank = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and a[order[j + 1]] == a[order[i]]:
            j += 1
        r = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            rank[order[k]] = r
        i = j + 1
    w_obs = sum(rank[i] for i in range(n) if d[i] > 0)
    le = 0
    for signs in itertools.product((-1, 1), repeat=n):
        w = sum(rank[i] for i in range(n) if signs[i] > 0)
        if w <= w_obs + 1e-12:
            le += 1
    return le / 2 ** n


def test_wilcoxon():
    print("\n[1] Wilcoxon signed-rank, one-sided H: median < 0")
    print("  %-56s %-14s %-14s %s" % ("case", "implementation", "brute force", ""))
    cases = [
        [-3.0, -1.0, 2.0, -4.0, -5.0, 1.5, -2.5],
        [-1.0, -2.0, -3.0, -4.0, -5.0],
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [-2.0, 2.0, -2.0, 2.0, -3.0],            # ties in |d|
        [0.0, -1.0, -2.0, 3.0, 0.0, -4.0],       # zeros dropped
        [-1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0, 2.0, -2.0, 0.5],
    ]
    for c in cases:
        got = S.wilcoxon_less(c)
        check("p  %s" % (c,), got["p"], brute_wilcoxon_less(c), 1e-12,
              "n_eff=%d %s" % (got["n_eff"], got["method"]))
    z = S.wilcoxon_less([0.0, -1.0, -2.0, 3.0, 0.0, -4.0])
    check("zeros dropped counted", z["zeros_dropped"], 2)


# ---------------------------------------------------------------- Spearman
def brute_spearman_rho(x, y):
    """rho from the rank definition, computed with exact rationals."""
    def rk(v):
        n = len(v)
        order = sorted(range(n), key=lambda i: v[i])
        r = [None] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            rr = Fraction(i + j + 2, 2)
            for k in range(i, j + 1):
                r[order[k]] = rr
            i = j + 1
        return r
    rx, ry = rk(x), rk(y)
    n = len(x)
    mx, my = Fraction(sum(rx), n), Fraction(sum(ry), n)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx)
    dy = sum((b - my) ** 2 for b in ry)
    return float(num) / math.sqrt(float(dx) * float(dy))


def brute_spearman_p(x, y):
    """Exact one-sided p = P(rho_perm >= rho_obs) over all n! relabellings."""
    rho = brute_spearman_rho(x, y)
    n = len(x)
    ge = tot = 0
    for perm in itertools.permutations(range(n)):
        yp = [y[i] for i in perm]
        tot += 1
        if brute_spearman_rho(x, yp) >= rho - 1e-12:
            ge += 1
    return ge / tot


def test_spearman():
    print("\n[2] Spearman rho, one-sided H: rho > 0")
    cases = [
        ([1, 2, 3, 4, 5, 6], [2, 1, 4, 3, 6, 5]),
        ([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]),
        ([1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5, 6, 7]),
        ([10, 20, 20, 30, 40, 50], [1, 3, 2, 5, 4, 6]),      # ties in x
        ([3, 1, 4, 1, 5, 9, 2], [2, 7, 1, 8, 2, 8, 1]),      # ties in both
    ]
    for x, y in cases:
        check("rho %s" % (x,), S.spearman_rho(x, y), brute_spearman_rho(x, y), 1e-12)
    for x, y in cases:
        r = S.spearman_greater(x, y)
        check("p   %s" % (x,), r["p"], brute_spearman_p(x, y), 1e-12, r["method"])
    # Monte-Carlo branch: must land near the exact answer on a case big enough
    # to take it. 9 points -> exact is 362,880 permutations, computed here once.
    x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    y = [2, 1, 4, 3, 6, 5, 8, 9, 7]
    exact = brute_spearman_p(x, y)
    mc = S.spearman_greater(x, y, n_mc=20000)["p"]
    check("p   monte-carlo vs exact (n=9, 20k draws)", mc, exact, 0.01,
          "tolerance is MC error, not an identity")


# ---------------------------------------------------------------- OLS
def test_ols():
    print("\n[3] OLS against the normal equations in exact rationals")
    rng = np.random.default_rng(7)
    X = rng.normal(size=(40, 2))
    y = 1.3 - 0.7 * X[:, 0] + 2.1 * X[:, 1] + rng.normal(scale=0.05, size=40)
    beta = S.ols(X, y)
    A = [[Fraction(1)] + [Fraction(float(v)) for v in row] for row in X]
    yy = [Fraction(float(v)) for v in y]
    k = 3
    AtA = [[sum(A[i][a] * A[i][b] for i in range(len(A))) for b in range(k)] for a in range(k)]
    Aty = [sum(A[i][a] * yy[i] for i in range(len(A))) for a in range(k)]
    # Gaussian elimination in exact rationals
    M = [row[:] + [Aty[r]] for r, row in enumerate(AtA)]
    for c in range(k):
        piv = next(r for r in range(c, k) if M[r][c] != 0)
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        M[c] = [v / pv for v in M[c]]
        for r in range(k):
            if r != c and M[r][c] != 0:
                f = M[r][c]
                M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    exact = [float(M[r][k]) for r in range(k)]
    for i, nm in enumerate(["a (intercept)", "beta0", "beta1"]):
        check("ols %s" % nm, float(beta[i]), exact[i], 1e-9)


# ---------------------------------------------------------------- BS delta
def test_delta():
    print("\n[4] bs_delta against a central difference of bs_price")
    for S0, K, T, r, sig, ot in [
        (25000.0, 25000.0, 5 / 365, 0.065, 0.12, "CE"),
        (25000.0, 25000.0, 5 / 365, 0.065, 0.12, "PE"),
        (25000.0, 24000.0, 20 / 365, 0.065, 0.18, "CE"),
        (25000.0, 26500.0, 2 / 365, 0.065, 0.25, "PE"),
    ]:
        h = S0 * 1e-5
        fd = (bs_price(S0 + h, K, T, r, sig, ot) - bs_price(S0 - h, K, T, r, sig, ot)) / (2 * h)
        check("delta K=%g %s" % (K, ot), S.bs_delta(S0, K, T, r, sig, ot), fd, 1e-6)
    check("call delta - put delta == 1 (ATM)",
          S.bs_delta(25000., 25000., 5 / 365, .065, .12, "CE")
          - S.bs_delta(25000., 25000., 5 / 365, .065, .12, "PE"), 1.0, 1e-12)


# ---------------------------------------------------------------- percentile
def test_percentile_and_median():
    print("\n[5] percentile / median against numpy")
    v = sorted(float(x) for x in np.random.default_rng(3).normal(size=37))
    for q in (2.5, 25, 50, 75, 97.5):
        check("pct %.1f" % q, S._pct(v, q), float(np.percentile(v, q, method="linear")), 1e-12)
    check("median odd n", S.median([3, 1, 2]), 2.0)
    check("median even n", S.median([4, 1, 2, 3]), 2.5)


# ---------------------------------------------------------------- bootstrap
def test_bootstrap_determinism():
    print("\n[6] bootstrap: seeded determinism and cluster structure")
    vals = [float(x) for x in np.random.default_rng(11).normal(size=50)]
    a = S.boot_percentile(vals, S.median, n=500)
    b = S.boot_percentile(vals, S.median, n=500)
    check("same seed -> same lo", a["lo"], b["lo"], 0.0)
    check("same seed -> same hi", a["hi"], b["hi"], 0.0)
    c = S.boot_percentile(vals, S.median, n=500, seed=S.SEED + 1)
    check("different seed -> different lo", c["lo"] != a["lo"], True)
    check("point estimate is the statistic itself", a["point"], S.median(vals), 0.0)
    clusters = {i: [float(x) for x in np.random.default_rng(i).normal(size=8)] for i in range(12)}
    cb = S.boot_cluster(clusters, lambda rows: S.median(rows), n=500)
    check("cluster count", cb["clusters"], 12)
    allrows = [r for k in clusters for r in clusters[k]]
    check("cluster point == stat(all rows)", cb["point"], S.median(allrows), 0.0)


def main():
    print("=" * 96)
    print("Part 0 step 5 -- brute-force self-test of every statistic used in this run")
    print("scipy installed: NO.  Wilcoxon imported from services/tape_scoring/wilcoxon.py (unmodified).")
    print("=" * 96)
    test_wilcoxon()
    test_spearman()
    test_ols()
    test_delta()
    test_percentile_and_median()
    test_bootstrap_determinism()
    print("\n" + "=" * 96)
    if FAILED:
        print("SELFTEST FAILED: %d check(s): %s" % (len(FAILED), FAILED))
        return 1
    print("SELFTEST PASSED -- all checks agree with an independent computation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
