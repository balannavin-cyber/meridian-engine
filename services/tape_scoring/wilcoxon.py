"""One-sided Wilcoxon signed-rank test, standard library only (tape scoring, docs/tape/scoring_plan.md section 1.3).

Convention, stated once and pinned by hand-computed cases in tests/test_tape_scoring.py:
  * Differences equal to 0 are DROPPED before ranking (Wilcoxon 1945 convention); the count is reported.
  * Ties in |d| get AVERAGE ranks (midranks).
  * W+ = sum of the ranks of the positive differences.
  * One-sided p = P(W+ >= w+) under H0 (each nonzero sign +/- with probability 1/2, independently); the alternative
    is "the median difference is > 0".
  * Exact for n_eff <= NORMAL_ABOVE: the permutation distribution of W+ given the observed midranked |d| (ties
    included exactly, not approximated), by dynamic programming over DOUBLED ranks, which are integers.
    Reference: Hollander, Wolfe & Chicken, Nonparametric Statistical Methods, 3rd ed., section 3.1.
  * Normal approximation only above NORMAL_ABOVE: mean n(n+1)/4, variance n(n+1)(2n+1)/24 - sum(t^3 - t)/48
    (tie correction), continuity correction 1/2. The method used is returned, so it is in the output.
No scipy. Exact arithmetic (fractions) throughout the exact branch.
"""
import math
from collections import Counter
from fractions import Fraction

NORMAL_ABOVE = 60


def midranks(abs_vals):
    order = sorted(range(len(abs_vals)), key=lambda i: abs_vals[i])
    ranks = [None] * len(abs_vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and abs_vals[order[j + 1]] == abs_vals[order[i]]:
            j += 1
        r = Fraction(i + j + 2, 2)
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def _exact_ge(ranks, w_plus):
    doubled = [int(2 * r) for r in ranks]
    total = sum(doubled)
    dp = [0] * (total + 1)
    dp[0] = 1
    for v in doubled:
        for s in range(total, v - 1, -1):
            dp[s] += dp[s - v]
    cnt = sum(dp[s] for s in range(int(2 * w_plus), total + 1))
    n = len(ranks)
    return Fraction(cnt, 2 ** n)


def _normal_ge(ranks, w_plus):
    n = len(ranks)
    mean = Fraction(n * (n + 1), 4)
    var = Fraction(n * (n + 1) * (2 * n + 1), 24) - sum(Fraction(t ** 3 - t, 48) for t in Counter(ranks).values())
    z = (float(w_plus - mean) - 0.5) / math.sqrt(float(var))
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def signed_rank_greater(diffs):
    d = [Fraction(x) for x in diffs if x != 0]
    zeros = len(diffs) - len(d)
    base = {"zeros_dropped": zeros, "normal_above": NORMAL_ABOVE}
    if not d:
        return dict(base, p=Fraction(1), method="none", n_eff=0, w_plus=Fraction(0))
    ranks = midranks([abs(x) for x in d])
    w = sum((r for r, x in zip(ranks, d) if x > 0), Fraction(0))
    if len(d) <= NORMAL_ABOVE:
        return dict(base, p=_exact_ge(ranks, w), method="exact", n_eff=len(d), w_plus=w)
    return dict(base, p=_normal_ge(ranks, w), method="normal", n_eff=len(d), w_plus=w)


def signed_rank_less(diffs):
    """Alternative 'the median difference is < 0': the same test on the negated differences."""
    return signed_rank_greater([-Fraction(x) for x in diffs])
