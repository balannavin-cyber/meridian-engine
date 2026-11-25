#!/usr/bin/env python3
"""V-2 comparison: engine gamma_v2.py against the pin lane's frozen implementation.

Pre-registration: claude/pin/v2_rule_conformance_prereg_FROZEN_2026-11-25.md
                  sha256 b1a156a8722da1700d22f4fbaf1a27dc116bdf3841075bf85e5cedd34ad7361d
Addendum (rule v1.2): claude/pin/v2_rule_conformance_addendum_v12_FROZEN_2026-11-25.md
This copy of the harness differs from the v1.1 harness (sha256 346bc4bd...b1d187) only in
the two frozen hashes below and in the banner line.

  python3 -B compare_v2.py --repo <engine worktree> --engine-commit <hash>
  python3 -B compare_v2.py --test-mode <fake golden root> --repo <dir holding merdian_compute/gamma_v2.py>

Exit 0 = PASS, 1 = FAIL, 2 = STOPPED before any comparison (a precondition failed).
Standard library only. Reads fixture files; no database, no network.
--test-mode is for checking this harness on invented data. Its output is NOT a result.
"""
import csv
import gzip
import hashlib
import importlib.util
import os
import subprocess
import sys
from decimal import Decimal, InvalidOperation

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_COMMIT = "934fe44"
FROZEN = {
    "v2_indep.py": "27acea7164c6032f10d790b991ebf26219ead6c027461226cde64e745c95ae16",
    "selftest_v2_indep.py": "0aa88ef6a441e54a79c89ffc5abb77781326272f0395d9c8288388b29b23b921",
}
# fixture, chain runs, stored per-strike runs, runs in both (pre-registration section 4)
FIXTURES = [
    ("2026-08-27_NIFTY", 81, 78, 78),
    ("2026-08-27_SENSEX", 81, 78, 78),
    ("2026-09-29_NIFTY", 81, 78, 78),
    ("2026-10-01_SENSEX", 81, 77, 77),
    ("2026-10-02_NIFTY", 81, 1, 1),
    ("2026-10-02_SENSEX", 81, 1, 1),
]
CHAIN_COLS = ("run_id", "expiry_date", "spot", "strike", "option_type", "oi", "gamma")
GSS_COLS = ("run_id", "expiry_date", "spot", "strike", "oi_call", "oi_put", "gamma_call", "gamma_put")
ROW_KEYS = ("oi_call", "oi_put", "gamma_strike", "gamma_legs", "in_map", "in_band", "net_cr", "gross_cr")
MAX_LIST = 25
csv.field_size_limit(2 ** 31 - 1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stop(msg):
    print("STOPPED:", msg)
    print("OVERALL: STOPPED (no comparison was made)")
    sys.exit(2)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dec(x):
    try:
        d = Decimal(str(x).strip())
    except (InvalidOperation, AttributeError):
        return None
    return d if d.is_finite() else None


def read_grouped(path, cols):
    """rows grouped by run_id, in file order, only the columns the rule uses."""
    runs = {}
    with gzip.open(path, "rt", newline="") as f:
        for r in csv.DictReader(f):
            runs.setdefault(r["run_id"], []).append({c: r.get(c) for c in cols})
    return runs


def verify_manifest(fix_dir, names):
    want = {}
    with open(os.path.join(fix_dir, "MANIFEST.sha256")) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                want[parts[1].lstrip("./")] = parts[0]
    for n in names:
        rel = "inputs/" + n
        if rel not in want:
            return f"{rel} not listed in MANIFEST.sha256"
        if sha256(os.path.join(fix_dir, rel)) != want[rel]:
            return f"{rel} does not match MANIFEST.sha256"
    return None


def same_num(a, b, abs_tol, rel_tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= abs_tol + rel_tol * abs(b)


def diff_rows(a, b):
    """a against reference b. Returns list of (strike, field, a, b)."""
    out = []
    ka, kb = [r["strike"] for r in a], [r["strike"] for r in b]
    if ka != kb:
        only_a = sorted(set(ka) - set(kb))[:5]
        only_b = sorted(set(kb) - set(ka))[:5]
        out.append(("-", "strike set", f"n={len(ka)} extra={only_a}", f"n={len(kb)} extra={only_b}"))
        return out
    for x, y in zip(a, b):
        for k in ROW_KEYS:
            if k in ("oi_call", "oi_put", "gamma_legs", "in_map", "in_band"):
                ok = x[k] == y[k]
            elif k == "gamma_strike":
                ok = same_num(x[k], y[k], 0.0, 1e-12)
            else:
                ok = same_num(x[k], y[k], 1e-6, 1e-9)
            if not ok:
                out.append((x["strike"], k, x[k], y[k]))
    return out


def diff_summary(a, b):
    out = []
    for k in ("net_cr", "gross_band_cr"):
        if not same_num(a[k], b[k], 0.01, 0.0):
            out.append(("run", k, a[k], b[k]))
    for k in ("net_top_share", "gross_top_share", "gross_hhi"):
        if not same_num(a[k], b[k], 1e-9, 0.0):
            out.append(("run", k, a[k], b[k]))
    for k in ("n_map", "n_zero"):
        if a[k] != b[k]:
            out.append(("run", k, a[k], b[k]))
    return out


def run_spot(rows):
    spots = []
    for r in rows:
        d = dec(r.get("spot"))
        if d is not None and d > 0 and d not in [dec(s) for s in spots]:
            spots.append(r.get("spot"))
    return spots[0] if spots else None


def guard_and_edge_counts(rows, spot_raw):
    """Independent count of legs the guard removes and strikes exactly on the edge."""
    s = dec(spot_raw)
    best = {}
    for r in rows:
        k = dec(r.get("strike"))
        ot = str(r.get("option_type", "")).strip().upper()
        if k is None or k <= 0 or ot not in ("CE", "PE"):
            continue
        try:
            g = float(r.get("gamma"))
        except (TypeError, ValueError):
            continue
        if g > 0 and g > best.get((k, ot), 0.0):
            best[(k, ot)] = g
    removed = sum(1 for (k, _), g in best.items() if abs(k - s) > Decimal("0.05") * s and g > 5e-5)
    return removed


def main():
    args = sys.argv[1:]

    def opt(name):
        return args[args.index(name) + 1] if name in args else None

    repo = opt("--repo")
    test_root = opt("--test-mode")
    engine_commit = opt("--engine-commit")
    if not repo:
        stop("--repo is required")
    test_mode = test_root is not None
    golden = test_root if test_mode else os.path.join(repo, "tests", "golden")

    print("V-2 comparison, rule v1.2" + ("   *** HARNESS TEST MODE: NOT A RESULT ***" if test_mode else ""))
    print("python", sys.version.split()[0])
    for name, want in FROZEN.items():
        got = sha256(os.path.join(HERE, name))
        print(f"frozen {name}: {got} {'OK' if got == want else 'MISMATCH'}")
        if got != want:
            stop(f"{name} is not the frozen file")
    print("harness compare_v2.py:", sha256(os.path.abspath(__file__)))
    eng_path = os.path.join(repo, "merdian_compute", "gamma_v2.py")
    if not os.path.isfile(eng_path):
        stop("merdian_compute/gamma_v2.py not found under --repo")
    print("engine gamma_v2.py sha256:", sha256(eng_path))

    # ------------------------------------------------------------------ V-2a
    v2a_ok = True
    if test_mode:
        print("V-2a: skipped in test mode")
    else:
        def git(*a):
            p = subprocess.run(["git", "-C", repo] + list(a), capture_output=True, text=True)
            return p.returncode, p.stdout.strip()
        rc, head = git("rev-parse", "HEAD")
        print("worktree HEAD:", head)
        if not engine_commit:
            stop("--engine-commit is required")
        rc, full = git("rev-parse", engine_commit)
        if rc != 0:
            stop("engine commit not found in the repo")
        print("engine commit:", full)
        rc, blob_engine = git("rev-parse", f"{full}:merdian_compute/gamma_v2.py")
        rc2, blob_head = git("rev-parse", "HEAD:merdian_compute/gamma_v2.py")
        if rc != 0 or rc2 != 0 or blob_engine != blob_head:
            stop("gamma_v2.py in the worktree is not the file at the engine commit")
        rc, st = git("status", "--porcelain", "--", "merdian_compute", "tests/golden")
        if st:
            stop("uncommitted changes under merdian_compute or tests/golden")
        rc, names = git("diff", "--name-status", BASE_COMMIT, "HEAD", "--", "merdian_compute")
        lines = [l for l in names.splitlines() if l.strip()]
        print("V-2a merdian_compute changes vs", BASE_COMMIT + ":", lines)
        if lines != ["A\tmerdian_compute/gamma_v2.py"]:
            v2a_ok = False
        rc, gold = git("diff", "--name-status", BASE_COMMIT, "HEAD", "--", "tests/golden")
        print("V-2a tests/golden changes vs", BASE_COMMIT + ":", gold.splitlines() or "none")
        if gold.strip():
            v2a_ok = False
        p = subprocess.run([sys.executable, "-B", "tests/test_merdian_compute_contract.py"],
                           cwd=repo, capture_output=True, text=True)
        tail = (p.stdout.strip().splitlines() or [""])[-1]
        print(f"V-2a contract test exit {p.returncode}: {tail[:160]}")
        if p.returncode != 0:
            v2a_ok = False
        print("V-2a:", "PASS" if v2a_ok else "FAIL")

    # ------------------------------------------------------------ load code
    sys.path.insert(0, HERE)
    import v2_indep as mine
    eng = load_module("gamma_v2_engine", eng_path)

    # -------------------------------------------------- manifests and counts
    # Pass 1 reads run ids only, so every precondition is checked before any comparison.
    def run_ids(path):
        ids = []
        seen = set()
        with gzip.open(path, "rt", newline="") as f:
            for r in csv.DictReader(f):
                if r["run_id"] not in seen:
                    seen.add(r["run_id"])
                    ids.append(r["run_id"])
        return ids

    for fix, n_chain, n_gss, n_both in FIXTURES:
        d = os.path.join(golden, fix)
        if not os.path.isdir(d):
            stop(f"fixture folder missing: {fix}")
        if not test_mode:
            err = verify_manifest(d, ("ocs.csv.gz", "gex_strike.csv.gz"))
            if err:
                stop(f"{fix}: {err}")
        c_ids = run_ids(os.path.join(d, "inputs", "ocs.csv.gz"))
        g_ids = run_ids(os.path.join(d, "inputs", "gex_strike.csv.gz"))
        n_b = len(set(c_ids) & set(g_ids))
        print(f"{fix}: manifest {'n/a' if test_mode else 'OK'}; chain runs {len(c_ids)}, stored runs {len(g_ids)}, in both {n_b}")
        if not test_mode and (len(c_ids), len(g_ids), n_b) != (n_chain, n_gss, n_both):
            stop(f"{fix}: run counts differ from the pre-registered {n_chain}/{n_gss}/{n_both}")

    def fixtures():
        """Pass 2: one fixture in memory at a time."""
        for fix, _a, _b, _c in FIXTURES:
            d = os.path.join(golden, fix)
            chain = read_grouped(os.path.join(d, "inputs", "ocs.csv.gz"), CHAIN_COLS)
            gss = read_grouped(os.path.join(d, "inputs", "gex_strike.csv.gz"), GSS_COLS)
            yield fix, chain, gss

    # ------------------------------------------------------------- compare
    cnt = {"both": 0, "call_only": 0, "put_only": 0, "none_in_map": 0, "none_not_in_map": 0,
           "guard_legs": 0, "zero_in_map": 0, "dup_legs": 0, "edge": 0, "err_runs": 0,
           "oi_counts_on_no_gamma_leg": 0, "rows": 0}
    b_fail, c_fail = [], []
    b_runs = c_runs = 0
    max_abs = {"net_cr": 0.0, "gross_cr": 0.0}
    for fix, chain, gss in fixtures():
        for run_id, rows in chain.items():
            b_runs += 1
            spot = run_spot(rows)
            try:
                e_rows, e_err = eng.build_v2_strike_rows(rows, spot), None
            except eng.V2InputError as ex:
                e_rows, e_err = None, str(ex)
            try:
                m_rows, m_err = mine.build_from_chain(rows), None
            except mine.V2RunError as ex:
                m_rows, m_err = None, str(ex)
            if (e_rows is None) != (m_rows is None):
                b_fail.append((fix, run_id, "-", "error run", e_err, m_err))
                continue
            if m_rows is None:
                cnt["err_runs"] += 1
                continue
            for d_ in diff_rows(e_rows, m_rows):
                b_fail.append((fix, run_id) + d_)
            if [r["strike"] for r in e_rows] == [r["strike"] for r in m_rows]:
                for x, y in zip(e_rows, m_rows):
                    for k in max_abs:
                        max_abs[k] = max(max_abs[k], abs(x[k] - y[k]))
            for d_ in diff_summary(eng.summarise_v2_run(e_rows), mine.summarise(m_rows)):
                b_fail.append((fix, run_id) + d_)
            # branch counts, from the independent rows and the raw legs
            s_dec = dec(spot)
            cnt["rows"] += len(m_rows)
            for r in m_rows:
                legs = r["gamma_legs"]
                if legs in ("both", "call_only", "put_only"):
                    cnt[legs] += 1
                    if (legs == "call_only" and r["oi_put"] > 0) or (legs == "put_only" and r["oi_call"] > 0):
                        cnt["oi_counts_on_no_gamma_leg"] += 1
                elif r["in_map"]:
                    cnt["none_in_map"] += 1
                else:
                    cnt["none_not_in_map"] += 1
                if r["in_map"] and r["net_cr"] == 0.0:
                    cnt["zero_in_map"] += 1
                if abs(dec(repr(r["strike"])) - s_dec) == Decimal("0.05") * s_dec:
                    cnt["edge"] += 1
            cnt["guard_legs"] += guard_and_edge_counts(rows, spot)
            cnt["dup_legs"] += mine.count_duplicate_legs(rows)

            if run_id in gss:
                c_runs += 1
                for label, build_gss, chain_rows, summ, exc in (
                        ("engine", eng.build_v2_strike_rows_from_gss, e_rows, eng.summarise_v2_run, eng.V2InputError),
                        ("indep", mine.build_from_gss, m_rows, mine.summarise, mine.V2RunError)):
                    try:
                        g_rows = build_gss(gss[run_id])
                    except exc as ex:
                        c_fail.append((fix, run_id, "-", f"{label} stored-row build error", str(ex), "-"))
                        continue
                    for d_ in diff_rows(chain_rows, g_rows):
                        c_fail.append((fix, run_id, f"{label} {d_[0]}") + d_[1:])
                    for d_ in diff_summary(summ(chain_rows), summ(g_rows)):
                        c_fail.append((fix, run_id, f"{label} {d_[0]}") + d_[1:])

    # -------------------------------------------------------------- report
    def show(name, fails):
        for f in fails[:MAX_LIST]:
            print(f"  {name} MISMATCH fixture={f[0]} run={f[1]} strike={f[2]} field={f[3]} engine/chain={f[4]!r} reference={f[5]!r}")
        if len(fails) > MAX_LIST:
            print(f"  ... {len(fails) - MAX_LIST} more")

    print(f"V-2b: {b_runs} chain runs compared; mismatches {len(b_fail)}; "
          f"max |engine - independent| net_cr {max_abs['net_cr']:.3e}, gross_cr {max_abs['gross_cr']:.3e}")
    show("V-2b", b_fail)
    print("V-2b:", "PASS" if not b_fail else "FAIL")
    print(f"V-2c: {c_runs} runs present in both files compared (engine pair and independent pair); mismatches {len(c_fail)}")
    show("V-2c", c_fail)
    print("V-2c:", "PASS" if not c_fail else "FAIL")

    print("COVERAGE over the chain runs (independent rows):")
    print(f"  output rows {cnt['rows']}; gamma_legs both {cnt['both']}, call_only {cnt['call_only']}, put_only {cnt['put_only']}, "
          f"none in map (guard removed both) {cnt['none_in_map']}, none not in map {cnt['none_not_in_map']}")
    print(f"  one-leg strikes where the other leg's OI now counts {cnt['oi_counts_on_no_gamma_leg']}")
    print(f"  legs removed by the guard {cnt['guard_legs']}; in-map strikes with net exactly 0 {cnt['zero_in_map']}")
    print(f"  legs with more than one row {cnt['dup_legs']}; strikes exactly on the 5% edge {cnt['edge']}; error runs {cnt['err_runs']}")
    zero = [k for k in ("both", "call_only", "put_only", "none_in_map", "none_not_in_map", "guard_legs",
                        "zero_in_map", "dup_legs", "edge", "err_runs") if cnt[k] == 0]
    print("  branches with a count of zero (covered by the self-tests only):", zero or "none")
    print("  fixtures: 3 of 6 are expiry days; 233 of the 313 V-2c runs are on an expiry day; no fixture has dte 1, 2 or 3")

    ok = v2a_ok and not b_fail and not c_fail
    if test_mode:
        print("HARNESS TEST MODE: NOT A RESULT")
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
