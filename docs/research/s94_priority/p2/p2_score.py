"""P2 dealer-side check — scorer. Pre-registered with
docs/research/s94_priority/P2_dealer_side_design_2026-10-10.md (§3a, §4, §5).

Usage: python3 -I p2_score.py part1_extract_2026-10-10.csv
Standard library only. Exits non-zero on any failed assertion; never drops a date.
"""
import csv, math, sys
from collections import defaultdict

N_DATES = 340                                   # §5, measured in Part 0
CATS = ("Client", "DII", "FII", "Pro")          # §4; TOTAL is the integrity row
LEGS = ("opt_idx_call_long", "opt_idx_call_short", "opt_idx_put_long", "opt_idx_put_short")
LAST = "2026-10-09"
CUT = 0.80                                      # §5, fixed from use, not data


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def classify(nc, np_):
    if nc > 0 and np_ < 0:
        return "holds"
    if nc < 0 and np_ > 0:
        return "inverted"
    return "mixed"


def verdict(h, inv, n):
    hl, _ = wilson(h, n)
    il, _ = wilson(inv, n)
    if hl >= CUT:
        return "CONSISTENT"
    if il >= CUT:
        return "INVERTED"
    return "REGIME-DEPENDENT"


def main(path):
    rows = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["trade_date"]][r["participant"]] = {k: int(r[k]) for k in LEGS}

    dates = sorted(rows)
    assert len(dates) == N_DATES, f"dates {len(dates)} != {N_DATES}"
    assert dates[-1] == LAST, f"last date {dates[-1]} != {LAST}"
    for d in dates:
        got = set(rows[d])
        assert got == set(CATS) | {"TOTAL"}, f"{d}: categories {sorted(got)}"
        t = rows[d]["TOTAL"]
        assert t["opt_idx_call_long"] == t["opt_idx_call_short"], f"{d}: TOTAL calls long != short"
        assert t["opt_idx_put_long"] == t["opt_idx_put_short"], f"{d}: TOTAL puts long != short"
        for leg in LEGS:
            s = sum(rows[d][c][leg] for c in CATS)
            assert s == t[leg], f"{d}: sum of categories {leg} {s} != TOTAL {t[leg]}"

    def net(d, cats):
        nc = sum(rows[d][c]["opt_idx_call_long"] - rows[d][c]["opt_idx_call_short"] for c in cats)
        np_ = sum(rows[d][c]["opt_idx_put_long"] - rows[d][c]["opt_idx_put_short"] for c in cats)
        return nc, np_

    groups = [("Pro (PRIMARY)", ("Pro",)), ("Pro+FII (SECONDARY)", ("Pro", "FII")),
              ("Client (descriptive)", ("Client",)), ("DII (descriptive)", ("DII",)),
              ("FII (descriptive)", ("FII",))]

    print(f"# P2 dealer-side check\n\nInput `{path}` · dates {dates[0]} → {dates[-1]} · n = {len(dates)} · integrity OK\n")
    print("| group | holds | inverted | mixed | holds 95% (Wilson) | inverted 95% | verdict |")
    print("|---|---:|---:|---:|---|---|---|")
    res = {}
    for name, cats in groups:
        c = {"holds": 0, "inverted": 0, "mixed": 0}
        for d in dates:
            c[classify(*net(d, cats))] += 1
        n = len(dates)
        v = verdict(c["holds"], c["inverted"], n)
        res[name] = v
        hl, hu = wilson(c["holds"], n); il, iu = wilson(c["inverted"], n)
        print(f"| {name} | {c['holds']} | {c['inverted']} | {c['mixed']} | [{hl:.3f}, {hu:.3f}] | [{il:.3f}, {iu:.3f}] | {v if '(descriptive)' not in name else '—'} |")

    p, s = res["Pro (PRIMARY)"], res["Pro+FII (SECONDARY)"]
    final = p if p == s else "REGIME-DEPENDENT"
    print(f"\n**Verdict (§5): {final}**" + ("" if p == s else f" — primary {p}, secondary {s} disagree"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
